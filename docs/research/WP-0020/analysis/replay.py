"""Read-only H/A retrospective replay. All outputs are written to fresh directories."""
import argparse
import ast
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
EVALUATION = REPO / "docs/evaluation/WP-0015"
ASTRA = REPO / "docs/research/WP-0015/astra"
TITLE_DIR = ASTRA / "sensitivity-title-level"
POLICY = REPO / "docs/research/WP-0019/astra/policy.py"
sys.path[:0] = [str(EVALUATION), str(ASTRA), str(TITLE_DIR), str(HERE)]

from fields import evaluate, require
from formats import native_page
from rescore import TITLE
from score import score

PINS = {
    EVALUATION/"score.py": "1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7",
    ASTRA/"formats.py": "b832a7ee452f807a01a4acaa4d63fed927241f73b75fc1a47c7ae830ce28c0a6",
    TITLE_DIR/"rescore.py": "86b9606468d12afff952b0b24dc7fcd1de932aa9c18400c966a3789e1609b700",
    POLICY: "5deb0a825bb0cbfbeff64bd6fd2f9433073248df56e099c91a8924b3b45c863d",
}
FAMILIES = {"H": ("h-r1-ab", "H-blind-inventory.json"), "A": ("a-recovery-ab", "A-recovery-blind-inventory.json")}
ARMS = ("windows", "native", "routed")
SCORE_NAMES = {key: "score-" + key + ".json" for key in ARMS}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def save(path, obj):
    with path.open("xb") as stream:
        stream.write((json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode())


def label_predicate():
    """Import just the frozen label vocabulary and function. No adapter or recognition library is needed."""
    for path, expected in PINS.items():
        require(digest(path.read_bytes()) == expected, f"source pin {path}")
    tree = ast.parse(POLICY.read_text(encoding="utf-8"))
    nodes = [node for node in tree.body if
             (isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "LABELS")
             or (isinstance(node, ast.FunctionDef) and node.name == "label")]
    require(len(nodes) == 2, "label source declarations")
    names = {"re": re}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(POLICY), "exec"), names)
    return names["label"]


def git_blob(revision, path):
    require(re.fullmatch("[0-9a-f]{40}", revision), "full Git revision required")
    return subprocess.check_output(["git", "-C", str(REPO), "show", revision + ":" + path])


def measured_cost(windows_time, native_time, native_windows, fields):
    """Matched Windows end-to-end and selected native engine/clock segments. No combined run was measured."""
    selected = Counter(f["window_start"] for f in fields)
    touched = defaultdict(set)
    for field in fields:
        touched[field["window_start"]].add(field["page"])
    complete = windows_time["complete_pages"]
    require(complete == native_time["complete_pages"], "unmatched page counts")
    available = list(range(1, complete+1, 3))
    require(list(native_windows) == available and set(selected) <= set(available), "native windows coverage")
    for clock in (windows_time, native_time):
        require(clock["status"] == "completed" and not clock["request"]["warmup"], "primary document clock")
        require(clock["request"]["pages"] == len(clock["page_committed_ns"]) == complete, "timing page count")
        require(clock["accepted_ns"] < clock["first_page_committed_ns"] == clock["page_committed_ns"][0], "first commit clock")
        require(clock["page_committed_ns"] == sorted(clock["page_committed_ns"]), "commit order")
        require(clock["page_committed_ns"][-1] <= clock["document_committed_ns"], "terminal commit order")
        require(abs(clock["elapsed_s"] - (clock["document_committed_ns"] - clock["accepted_ns"])/1e9) < 1e-8,
                "elapsed clock mismatch")
    rows = []
    for first in available:
        w = native_windows[first]
        count = min(3, complete + 1 - first)
        last = first + count - 1
        require(w["first_page"] == first and w["pages"] == count, "window span")
        require(all(first <= p <= last for p in touched[first]), "field/window discrepancy")
        begin = native_time["page_committed_ns"][first-2] if first > 1 else native_time["accepted_ns"]
        end = native_time["document_committed_ns"] if last == complete else native_time["page_committed_ns"][last-1]
        require(begin <= w["engine_begin_ns"] < w["engine_end_ns"] <= end, "engine outside window segment")
        rows.append(dict(first=first, last=last, actual_pages=count, selected_fields=selected[first],
                         selected_pages=sorted(touched[first]), segment_begin_ns=begin, segment_end_ns=end,
                         engine_begin_ns=w["engine_begin_ns"], engine_end_ns=w["engine_end_ns"],
                         engine_s=(w["engine_end_ns"]-w["engine_begin_ns"])/1e9, segment_s=(end-begin)/1e9))
    require(abs(sum(w["segment_s"] for w in rows) - native_time["elapsed_s"]) < 1e-6, "segment sum")
    bought = [w for w in rows if w["selected_fields"]]
    engine = sum(w["engine_s"] for w in bought)
    segments = sum(w["segment_s"] for w in bought)
    windows_s = windows_time["elapsed_s"]
    floor = windows_s + engine
    modeled = windows_s + segments
    budget = complete * 60 / 30
    return dict(pages=complete, available_windows=len(rows), routed_pages=sum(len(w["selected_pages"]) for w in bought),
                selected_windows=len(bought), purchased_pages=sum(w["actual_pages"] for w in bought),
                windows_with_one_field=[w["first"] for w in bought if w["selected_fields"] == 1],
                windows_full_document_observed_s=windows_s, native_full_document_observed_s=native_time["elapsed_s"],
                selected_native_engine_observed_s=engine, selected_native_segments_observed_s=segments,
                modeled_serial_engine_floor_s=floor, modeled_serial_segment_s=modeled,
                target_s=budget, remaining_after_windows_s=budget-windows_s, engine_floor_over_budget_s=max(0, floor-budget),
                verdict="over budget" if floor > budget else "within modeled budget" if modeled <= budget else "cost unknown",
                windows=rows)


def run_family(family, archive, route_commit, scratch, output, label):
    run_name, inventory_name = FAMILIES[family]
    run = archive/"runs"/run_name
    win = run/("04-" + family.lower() + "-windows")
    native = run/("03-" + family.lower() + "-native")
    inventory_path = REPO/"docs/reviews/WP-0015/evidence"/inventory_name
    inv, = [r["files"] for r in read(inventory_path)["runs"] if r["run"] == run_name]
    commitment = read(EVALUATION/"commitments.json")["packets"][family]
    inputs = {}
    def checked(path, expected):
        data = path.read_bytes()
        require(digest(data) == expected, "archive hash mismatch: " + str(path))
        inputs[path.relative_to(archive).as_posix()] = expected
        return json.loads(data)
    def archived(folder, name):
        return checked(folder/name, inv[f"{folder.name}/{name}"])

    route_inputs, route_pins = {}, {}
    for name in ("manifest", "decisions", "prediction"):
        path = f"docs/research/WP-0020/route/evidence/{family}/{name}.json"
        data = git_blob(route_commit, path)
        route_inputs[name] = json.loads(data)
        route_pins[path] = digest(data)
    manifest = route_inputs["manifest"]
    decisions = route_inputs["decisions"]
    manifest_path = f"docs/research/WP-0020/route/evidence/{family}/manifest.json"
    require(decisions["manifest_sha256"] == route_pins[manifest_path], "decisions/manifest digest")
    require(manifest["family"] == decisions["family"] == family, "route family")
    require(manifest["input_sha256"]["prediction.json"] == inv[f"{win.name}/prediction.json"], "selector input digest")
    truth = checked(archive/f"scoring-{family}/truth.json", commitment["files"]["truth.json"])
    rasters = checked(archive/f"scoring-{family}/rasters.json", commitment["files"]["rasters.json"])
    sha = commitment["files"]["source.pdf"]
    require(truth["source_sha256"] == manifest["source_sha256"] == sha and len(truth["pages"]) == commitment["pages"], "reference source/pages")
    windows_pred, original_native = (archived(arm, "prediction.json") for arm in (win, native))
    windows_time, native_time = (archived(arm, "timing.json") for arm in (win, native))
    for mode, clock, folder in (("native", native_time, native), ("windows", windows_time, win)):
        r = clock["request"]
        require(r["label"] == family.lower() and r["mode"] == mode and r["sha256"] == sha, "matched request")
        require(r["rgb_sha256"] == [p["rgb_sha256"] for p in rasters["pages"]], "matched rasters")
        require(clock["prediction_sha256"] == inv[f"{folder.name}/prediction.json"], "prediction commitment")
    adapted = []
    title_headers = 0
    for index, page in enumerate(original_native["pages"], 1):
        raw = archived(native, f"raw-{index:03d}.json")
        require(page["page"] == raw["page"] == index and raw["source_sha256"] == page["source_sha256"] == sha,
                "native raw identity")
        require(raw["rgb_sha256"] == native_time["request"]["rgb_sha256"][index-1], "native raster")
        require(native_page(raw["raw_output"], raw["points"]) == {k:page[k] for k in ("text", "spans", "tables")},
                "original native parse mismatch")
        corrected, count = TITLE.subn(r"\1", raw["raw_output"])
        title_headers += count
        adapted.append(dict(page, **native_page(corrected, raw["points"])))
    controls = dict(windows=windows_pred, native=dict(original_native, pages=adapted), routed=route_inputs["prediction"])
    scores = {}
    scratch.mkdir()
    save(scratch/"corrected-native-prediction.json", controls["native"])
    for key, pred in controls.items():
        require(pred["source_sha256"] == sha and [p["page"] for p in pred["pages"]] ==
                list(range(1, commitment["pages"]+1)), "scoring input identity")
        scores[key] = score(truth, pred)
        save(scratch/SCORE_NAMES[key], scores[key])
    summary, fields = evaluate(truth, windows_pred, manifest, route_inputs["decisions"], scores, label)
    windows = {first:archived(native, f"window-{first:03d}.json") for first in range(1, commitment["pages"]+1, 3)}
    require(all(w["source_sha256"] == sha for w in windows.values()), "window source")
    timing = measured_cost(windows_time, native_time, windows, manifest["fields"])
    require(manifest["selected_windows"] == [w["first"] for w in timing["windows"] if w["selected_fields"]],
            "manifest windows differ from field windows")
    summary.update(family=family, run=run_name, source_sha256=sha, corrected_title_headers=title_headers,
                   scorer={k:dict(counts=s["counts"], faults=s["faults"], complete=s["packet_complete"])
                           for k,s in scores.items()}, timing=timing)
    output.mkdir()
    save(output/"fields.json", fields)
    save(output/"summary.json", summary)
    for rel, expected in inputs.items():
        require(digest((archive/rel).read_bytes()) == expected, "archive changed during analysis " + rel)
    save(output/"inputs.json", dict(common_sources={p.relative_to(REPO).as_posix():h for p,h in PINS.items()},
                                   archive=inputs, archive_verified_after=True, route_commit=route_commit,
                                   route=route_pins, blind_inventory_sha256=digest(inventory_path.read_bytes()),
                                   local_scorer_artifacts={f.name:digest(f.read_bytes()) for f in sorted(scratch.iterdir())}))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True, help="WP-0015/review")
    parser.add_argument("--route-commit", required=True)
    parser.add_argument("--scratch", type=Path, required=True, help="new private score directory")
    parser.add_argument("--out", type=Path, required=True, help="new publishable evidence directory")
    args = parser.parse_args()
    label = label_predicate()
    args.scratch.mkdir(parents=True, exist_ok=False)
    args.out.mkdir(parents=True, exist_ok=False)
    for family in FAMILIES:
        summary = run_family(family, args.archive.resolve(), args.route_commit, args.scratch/family, args.out/family, label)
        print(family, json.dumps(summary["metrics"]["critical"]["windows_to_routed"]), summary["timing"]["verdict"])


if __name__ == "__main__":
    main()
