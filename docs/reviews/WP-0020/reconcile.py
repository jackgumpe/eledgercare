"""Compare independent joins to every published H/A field and verify replay artifact hashes."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import subprocess
import sys


ROUTE = "122652984a316c9b8963ec89cf1b61dd994aaf99"
ANALYSIS = "53098839e0d86a1db91bf015d2e97f55433365c8"
scratch, archive = map(Path,sys.argv[1:])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(rev, rel):
    return subprocess.check_output(["git","show", f"{rev}:{rel}"])


def get(path):
    return json.loads(path.read_bytes())


def kind_selected(group):
    return Counter("inside" if item["selected"] else "outside" for item in group)


results = {}
for family in ("H","A"):
    out = scratch/"analysis-evidence"/family
    independent_path = scratch/f"{family}-scores.json"
    ours = get(independent_path)
    cli = scratch/"cli"/family
    sources = {}
    for root, names, revision, at in (
        ("route", ("manifest","decisions","prediction"), ROUTE, cli),
        ("analysis", ("summary","fields","inputs"), ANALYSIS, out)):
        for name in names:
            partial = f"{root}/evidence/{family}/{name}.json"
            exact = blob(revision, "docs/research/WP-0020/"+partial)
            assert (at/(name+".json")).read_bytes() == exact
            sources[partial] = sha(exact)
    fields = get(out/"fields.json")
    reported = get(out/"summary.json")
    admitted = get(out/"inputs.json")
    for rel, digest in admitted["archive"].items():
        assert sha((archive/rel).read_bytes()) == digest
    for name, digest in admitted["local_scorer_artifacts"].items():
        assert sha((scratch/"analysis-score"/family/name).read_bytes()) == digest
    rows = ours["fields"]
    groups = {"critical":fields["critical"], "region":fields["regions"]}
    assert len(groups["critical"]) + len(groups["region"]) == len(rows)
    lookup = {name:{r["at"]:r for r in group} for name,group in groups.items()}
    for r in rows:
        match = lookup["critical" if r["category"] == "critical" else "region"][r["at"]]
        assert r["critical"] == match["critical_location"]
        assert r["selected"] == bool(match["selected_ids"])
        assert [r[k] for k in ("win_ok","native_ok","routed_ok")] == [match[k] for k in ("windows","native","routed")]
        assert r["win_flag"] == match["flags"]["windows"] and r["routed_flag"] == match["flags"]["routed"]
        assert r["win"] == r["routed"] or r["selected"]
        assert r["routed_flag"] == r["win_flag"]
        if "witness" in match:
            assert match["witness"] == dict(expected=r["expected"], windows=r["win"], native=r["native"], routed=r["routed"])
    assert not (ours["unlinked_routes"] or ours["partial_line_links"])
    assert ours["corrected_title_headers"] == reported["corrected_title_headers"]
    for key, counts in zip(("windows","native","routed"), ours["score_counts"]):
        assert counts == reported["scorer"][key]["counts"]
    windows = reported["timing"]["windows"]
    for a,b in zip(ours["chosen_windows"], windows, strict=True):
        assert (a["first"],a["pages"],a["engine_ns"]) == (b["first"],b["actual_pages"],b["engine_end_ns"]-b["engine_begin_ns"])
    critical = [r for r in rows if r["category"] == "critical"]
    opportunities = [r for r in critical if not r["win_ok"] and r["native_ok"]]
    risks = [r for r in critical if r["win_ok"] and not r["native_ok"]]
    selected = {r["at"]:r for r in fields["critical"] if r["selected_ids"]}
    missed = [r["at"] for r in opportunities if not r["routed_ok"]]
    protected = [r for r in rows if r["category"] != "critical" and (not r["expected"] or " " in " ".join(r["expected"].split()))]
    assert not [r for r in protected if r["win_ok"] and not r["routed_ok"]]
    floor = (ours["windows_ns"]+sum(r["engine_ns"] for r in ours["chosen_windows"]))/1e9
    native_folder=archive/"runs"/ours["archive_order"]/f"03-{family.lower()}-native"
    nt = get(native_folder/"timing.json")
    model = (ours["windows_ns"] + nt["document_committed_ns"] - nt["accepted_ns"])/1e9
    assert abs(floor - reported["timing"]["modeled_serial_engine_floor_s"]) < 1e-8
    assert abs(model - reported["timing"]["modeled_serial_segment_s"]) < 1e-8
    results[family] = dict(run=ours["archive_order"], reproduced_published_sha256=sources,
        independent_score_file_sha256=sha(independent_path.read_bytes()), private_scorer_artifact_sha256=admitted["local_scorer_artifacts"],
        archive_files_verified_after=len(admitted["archive"]), truth_sha256=ours["truth_sha256"],
        title_headers=ours["corrected_title_headers"], scored_rows_checked=len(rows), score_counts=ours["score_counts"],
        transitions=ours["transitions"], selected_observations=reported["selection"],
        critical_opportunities=dict(total=len(opportunities), selected=dict(kind_selected(opportunities)), unbound=[r["at"] for r in opportunities if r["at"] in selected and selected[r["at"]]["coverage"]=="unresolved"], missed=missed),
        critical_risks=[dict(at=r["at"], action=selected[r["at"]]["coverage"] if r["selected"] else "outside_trigger", correctly_retained=r["routed_ok"]) for r in risks],
        recovered_critical=[r["at"] for r in opportunities if r["routed_ok"]], newly_wrong_critical=[r["at"] for r in critical if r["win_ok"] and not r["routed_ok"]],
        protected_checks= {g:reported["metrics"][g]["windows_to_routed"] for g in ("noncritical_locations","printed_blank_cells","legitimately_spaced_lines","legitimately_spaced_cells")},
        native_window_observations=ours["chosen_windows"], windows_seconds=ours["windows_ns"]/1e9, serial_floor_seconds=floor,
        full_serial_model_seconds=model, available_windows=len(windows), single_field_windows=[w["first"] for w in windows if w["selected_fields"]==1])
print(json.dumps(results, indent=2))
