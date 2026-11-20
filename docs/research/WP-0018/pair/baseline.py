"""Verify one admitted WP-0015 Windows archive and reproduce its score in a new process."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PUBLIC = REPO / "docs/reviews/WP-0015"
sys.path.insert(0, str(PUBLIC))
from scored_summary import counts, diag, lookup  # Pure functions used by the prior publication.

PINS = {
    "score.py": "1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7",
    "constructed-scorer-control.json": "3455a09402b1ed3be58473892533c6f2f70d23f89496c86adda5b7095217d3ad",
    "archive-pins.json": "7705afb4c0090469b92feb790236dae745a5266b7e5d07793218729dff3ad3d4",
    "scored-H-A.json": "fabd3e2a4426dac276f37d1404fa134f1ac0823f9befc0afd0938cdafe1231ee",
}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_bytes())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def write(path, obj):
    with path.open("xb") as stream:
        stream.write((json.dumps(obj, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode())


def score_file(scorer, truth, prediction, result):
    check(digest(scorer.read_bytes()) == PINS["score.py"], "scorer SHA-256")
    subprocess.run([sys.executable, "-I", "-B", str(scorer), str(truth), str(prediction),
                    "--out", str(result)], check=True)
    return read(result)


def verify_archive(inputs, family):
    control = inputs / "control"
    for name, expected in PINS.items():
        check(digest((control / name).read_bytes()) == expected, name + " SHA-256")
    pins = read(control / "archive-pins.json")["families"][family]
    archive = inputs / family
    files = {}
    for name, expected in pins["source_commitments_sha256"].items():
        files[name] = digest((archive / name).read_bytes())
        check(files[name] == expected, name + " commitment")

    inventory = json.loads(subprocess.check_output([
        "git", "-C", str(REPO), "cat-file", "blob", pins["archive_inventory_git_blob"]]))
    run, = [r for r in inventory["runs"] if r["run"] == pins["run"]]
    for name, expected in run["files"].items():
        if name.startswith(pins["folder"] + "/"):
            dest = "windows/" + name.split("/", 1)[1]
            files[dest] = digest((archive / dest).read_bytes())
            check(files[dest] == expected, dest + " inventory")
    for name, expected in pins["relative_files_in_named_run_sha256"].items():
        check(run["files"][name] == expected, name + " witness pin")
    for name in ("plan.json", "rasters.input.json", "historical-score.json"):
        files[name] = digest((archive / name).read_bytes())
    check(files["plan.json"] == run["plan_sha256"], "plan SHA-256")

    truth = read(archive / "truth.json")
    pred = read(archive / "windows/prediction.json")
    timing = read(archive / "windows/timing.json")
    rasters = read(archive / "rasters.json")
    inference_pins = read(archive / "rasters.input.json")["pages"]
    r = timing["request"]
    plan = read(archive / "plan.json")
    expected_request = [p for i, p in enumerate(plan["requests"], 1)
                        if f"{i:02d}-{p['label']}-{p['mode']}" == pins["folder"]]
    check(expected_request == [r] and r["mode"] == "windows" and not r["warmup"], "request")
    source = files["source.pdf"]
    check(pred["source_sha256"] == truth["source_sha256"] == r["sha256"] == source, "source")
    check(timing["prediction_sha256"] == files["windows/prediction.json"], "timing prediction")
    pages = list(range(1, len(truth["pages"]) + 1))
    check([p["page"] for p in pred["pages"]] == [p["page"] for p in truth["pages"]] == pages,
          "page sequence")
    check(timing["complete_pages"] == r["pages"] == len(pages) and timing["status"] == "completed",
          "completion")
    check([p["page_number"] for p in rasters["pages"]] == pages, "raster page order")
    rgb = [p["rgb_sha256"] for p in rasters["pages"]]
    check(rgb == r["rgb_sha256"] == [p["rgb_sha256"] for p in inference_pins], "RGB pins")
    for idx, page in enumerate(pred["pages"]):
        n = idx + 1
        raw = read(archive / f"windows/raw-{n:03d}.json")
        window = read(archive / f"windows/window-{n:03d}.json")
        check(canon(read(archive / f"windows/page-{n:03d}.json")) == canon(page), f"page {n}")
        check(raw["source_sha256"] == page["source_sha256"] == window["source_sha256"] == source,
              f"source p{n}")
        check(raw["page"] == window["first_page"] == n and window["pages"] == 1
              and raw["rgb_sha256"] == rgb[idx], f"raw/window p{n}")

    return dict(run=pins["run"], folder=pins["folder"], inventory_blob=pins["archive_inventory_git_blob"],
                files=files, pages_verified=len(pages), source_sha256=source)


def baseline(inputs, family, out):
    admission = verify_archive(inputs, family)
    archive = inputs / family
    win = archive / "windows"
    truth, rasters = (read(archive / n) for n in ("truth.json", "rasters.json"))
    pred = read(win / "prediction.json")
    score = score_file(inputs / "control/score.py", archive / "truth.json", win / "prediction.json",
                       out / "score.json")
    historic = read(archive / "historical-score.json")
    # The original comparison field contains a different engine's control arm.
    historic.pop("comparison", None)
    check(canon(score) == canon(historic), "complete historical Windows score")
    publication = read(inputs / "control/scored-H-A.json")[family]
    published = publication["runs"][admission["run"]]["windows"]
    check(counts(score) == published["official"], "all published official counts/faults")
    check(diag(truth, pred) == published["checks"], "supplementary numeric/page/flag checks")

    looked = lookup(truth, rasters, {"windows": (win, score, pred)})
    expected = publication["source_linked_lookup"]
    for page in expected["pages"].values():
        page["arms"] = {"windows": page["arms"]["windows"]}
    check(canon(looked) == canon(expected), "source-linked Windows published page lookups")
    crit = {c["at"]: c for p in score["pages"] for c in p["critical"]}
    examples = {}
    for comparison in ("vs_official_native", "vs_corrected_native"):
        for case in published[comparison]["examples"]:
            at = case["at"]
            c = crit[at]
            check(c["expected"] == case["expected"] and c["observed"] == case["trial"]
                  and not c["correct"], "published Windows observation " + at)
            examples[at] = dict(expected=c["expected"], observed=c["observed"], flagged=c["flagged"])
    pins = read(inputs / "control/archive-pins.json")["families"][family]["published_windows"]
    c = score["counts"]
    observed_pins = dict(matching_reference_cells=c["correct_cells"], reference_cells=c["reference_cells"],
                         extra_cells=c["extra_cells"], matching_reference_lines=c["correct_lines"],
                         reference_lines=c["reference_lines"], unflagged_critical_errors=c["unflagged_critical_errors"],
                         reference_criticals=c["critical_values"],
                         ready_to_durable_prediction_seconds=round(read(win / "timing.json")["elapsed_s"], 3),
                         missing_numeric_tokens_supplementary=published["checks"]["missing_numeric_tokens"])
    check(observed_pins == pins, "brief baseline/calibration")
    receipt = dict(packet=family, profile="unmodified prior Windows prediction", admission=admission,
                   control_sha256=PINS, score_sha256=digest((out / "score.json").read_bytes()),
                   historical_score_equal_excluding_prior_native_comparison=True, official=counts(score),
                   supplementary=published["checks"], checked_published_lookups=looked, checked_examples=examples,
                   published_windows=observed_pins)
    write(out / "baseline.json", receipt)
    print(f"{family} historical score and published lookups reproduced; {c['correct_cells']}/{c['reference_cells']} cells")
    return receipt


def new_output(path, inputs):
    path, inputs = path.resolve(), inputs.resolve()
    check(not (path.is_relative_to(inputs) or inputs.is_relative_to(path)), "output overlaps inputs")
    path.mkdir(parents=True, exist_ok=False)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("packet", choices=("H", "A"))
    parser.add_argument("output", type=Path, help="fresh scratch directory")
    args = parser.parse_args()
    baseline(args.inputs.resolve(), args.packet, new_output(args.output, args.inputs))
