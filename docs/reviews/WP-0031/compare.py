"""Compare the frozen author's Git blobs with the independent replay, its matrices, and the archive."""
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent / "evidence"
TRACE = "7d65875a1ff2d7ad8a008ea83f5484507dbd5db3"
AUTHOR = "5e1a464a38ad4213b94b3b25695bd70d9054a6a3"
DATA = "8f31cc66c4878ca086fa5da1498c4a73ed6a6306"
REVIEW = "6260131f85ec3844acb54326799c7f6d48115323"
OWNERS = ["Alder", "Cedar"]


def blob(ref):
    return subprocess.check_output(["git", "cat-file", "blob", ref], cwd=ROOT)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))+"\n").encode()


def fingerprint(state):
    control = state["controller"].copy()
    del control["ambiguous_reason"]
    discrete = {"controller": control, "registry": state["full_registry"],
                "attempts": [], "trace": [], "growth": [], "lookup_ns": 0}
    return discrete, {"matrix_sha256": state["matrix_sha256"], "discrete_sha256": digest(canonical(discrete))}


def compare_read(observed, independent):
    ordered = sorted(independent["scores"].values(), reverse=True)
    gap32, = struct.unpack("<f",struct.pack("<f", ordered[0] - ordered[1]))
    expected = dict(independent, ordered_anchor_sha256=independent["anchor_sha256"],
                    top_score_pass=ordered[0] >= 1., top_gap_pass=gap32 >= struct.unpack("<f",struct.pack("<f",.1))[0],
                    discrete_sha256=fingerprint(independent)[1]["discrete_sha256"])
    for key,value in observed.items():
        assert value == expected[key], (key,value,expected[key])
        if type(value) == float:
            assert struct.pack("<d",value) == struct.pack("<d",expected[key])


def main(candidate):
    assert sys.flags.dont_write_bytecode and not sys.flags.optimize and ROOT == Path.cwd()
    assert candidate == subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    assert blob(candidate+":docs/reviews/WP-0031/compare.py") == Path(__file__).read_bytes().replace(b"\r\n",b"\n")
    assert subprocess.check_output(["git","rev-parse",DATA+"^"],text=True).strip() == AUTHOR
    data_prefix = DATA+":docs/research/WP-0031/evidence/"
    local = json.loads((EVIDENCE/"replay.json").read_bytes())
    assert local["candidate"] == REVIEW
    receipt = json.loads(blob(data_prefix+"runtime.json"))
    assert (receipt["candidate"],receipt["git_head"]) == (AUTHOR,AUTHOR)
    assert (receipt["intraop_threads"],receipt["interop_threads"]) == tuple(local["threads"]) == (1,1)
    assert receipt["torch_build_cuda"] == local["cuda_build"] is None
    for k in ("python","python_sha256","torch","numpy","deterministic","base"):
        assert receipt[k] == local[k]
    files = {name:blob(data_prefix+name) for name in receipt["evidence_sha256"]}
    assert {n:digest(v) for n,v in files.items()} == receipt["evidence_sha256"]
    both_inputs = json.loads(files["inputs.json"])
    for ref,sha in both_inputs["blobs_sha256"].items():
        assert digest(blob(ref)) == sha
        if ref in local["blobs_sha256"]:
            assert local["blobs_sha256"][ref] == sha
    for name in OWNERS:
        cat = both_inputs["captures"][name]
        independent = local["sources"]["windows"][name]
        assert (cat["rgb_key"],cat["prefix"],cat["members"]) == (
            independent["rgb_key"],independent["prefix"],independent["members_sha256"])
    rows = {(r["run"],r["step"]): r for r in map(json.loads,blob(
        TRACE+":docs/reviews/WP-0030/evidence/steps.jsonl").splitlines()) if r["phase"]=="post" and r["step"]<=8}
    checks = {}
    with ZipFile(EVIDENCE/"prefixes.zip") as matrices:
        for probe in ("M1","M3"):
            a = json.loads(files[probe+".json"])
            r = local["probes"][probe]
            assert a["status"] == "completed" and r["native_gate"] and all(g["pass"] for g in a["gates"].values())
            assert a["owner_order"] == OWNERS and a["thresholds"] == [1.,.1]
            source_ids, donor_ids, check = {}, {}, {"prefix": {}, "cells": {}}
            for n in OWNERS:
                src = a["sources"][n]
                independent = r["write7"][n]
                dstate, sid = fingerprint(independent)
                source_ids[n] = sid
                snap = src["snapshot"]
                fname = f"{probe}-{n}-write7.f32"
                ours = matrices.read(fname)
                assert snap["matrices_file"] == fname and snap["dtype"] == "float32-le"
                assert snap["shape"] == [1 if probe == "M1" else 8,128,128] and files[fname] == ours
                assert snap["discrete"] == dstate and digest(ours) == sid["matrix_sha256"]
                assert all(snap[k] == v for k,v in sid.items())
                compare_read(src["write7_read"],independent)
                assert digest(bytes.fromhex(src["frozen_query_f32le"])) == independent["query_sha256"]
                assert digest(bytes.fromhex(src["ordered_anchors_f32le"])) == independent["anchor_sha256"]
                srows = r["rows"][n]
                for idx,t in enumerate(src["prefix_writes"]):
                    row = srows[idx]
                    old = rows[f"{probe}/12",idx+1][n]
                    assert t["write"] == idx+1 and t["matrix_sha256"] == old["read"]["matrix_sha256"]
                    assert t["feature_sha256"] == row["feature_f32le_sha256"]
                    assert t["owners_before"] == (OWNERS if idx>=3 else [])
                    assert t["owners_after"] == (OWNERS if idx>=2 else [])
                    assert t["events"] == [dict(e,ptr=row["ptr"]) for e in row["events"]]
                assert len(src["prefix_writes"]) == 7
                row = srows[7]
                numerics = r["donor"][n]
                proj = numerics["fields_f32le"]
                bundle = {"owner": n, "full_window_shape": [16,1280], "pointer": row["ptr"],
                          "window_rgb_key": row["key"], "bbox": row["bbox"], "literal": row["text"],
                          "events": [dict(e,ptr=row["ptr"]) for e in row["events"]],
                          "feature_sha256": row["feature_f32le_sha256"],
                          "projected_f32le": dict(key=proj["k"],value=proj["v"],alpha=proj["a"],beta=proj["b"]),
                          "projection_sha256": numerics["k_v_a_b_sha256"]}
                assert bundle == src["donor"]
                assert src["donor_input_sha256"] == digest(canonical(bundle))
                donor_ids[n] = src["donor_input_sha256"]
                check["prefix"][n] = dict(bytes_equal=len(ours), **sid, donor_input_sha256=donor_ids[n],
                                         k_v_a_b_sha256=bundle["projection_sha256"],
                                         ordered_anchor_sha256=independent["anchor_sha256"], query_sha256=independent["query_sha256"])
            assert all(a["contrasts"][k] == v and a["contrasts_f64le"][k] == struct.pack("<d",v).hex()
                       for k,v in r["contrasts"].items())
            trigger = r["zero"]
            expected = dict(DA=trigger["DA"],DC=trigger["DC"],abs_I=trigger["abs_I"],
                            five_percent_limit=trigger["limit"],run=trigger["trigger"])
            assert expected == a["trigger"] and trigger["trigger"] == (a["empty_cells"] is not None)
            source_cells = a["cells"].copy()
            if trigger["trigger"]:
                assert struct.pack("<d",a["empty_cells"]["D0"]) == struct.pack("<d",trigger["D0"])
                source_cells.update({k:a["empty_cells"][k] for k in ("0A","0C")})
            assert set(source_cells) == set(r["cells"])
            for label,c in source_cells.items():
                i = r["cells"][label]
                src = "Alder" if i["recipient"] == "0" else i["recipient"]
                assert c["recipient"] == ("zero" if i["recipient"] == "0" else i["recipient"])
                assert c["control_registry_from"] == src and c["donor"] == i["donor"]
                assert c["donor_input_sha256"] == donor_ids[c["donor"]]
                assert c["fresh_residual_sha256"] == i["residual_sha256"]
                assert c["source_states_before"] == c["source_states_after"] == source_ids
                assert i["source_snapshot_sha256_before_and_after"] == {x:y["matrix_sha256"] for x,y in source_ids.items()}
                incoming = dict(source_ids[src], matrix_sha256=i["recipient_matrix_sha256"])
                assert c["recipient_before_event"] == c["after_donor_hook"] == incoming and i["registry_controller_unchanged"]
                assert struct.pack("<dd",c["baseline_margin"],c["increment"]) == struct.pack("<dd",i["row_baseline"],i["increment"])
                compare_read(c["read"],i["post"])
                check["cells"][label] = dict(recipient=c["recipient"],donor=c["donor"], donor_input_sha256=c["donor_input_sha256"],
                                             recipient_matrix_sha256=incoming["matrix_sha256"], residual_sha256=i["residual_sha256"],
                                             **{k:i["post"][k] for k in ("matrix_sha256","read_sha256","score_f32le","margin_f64le")})
            for step in (7,8):
                g = a["gates"][f"step_{step}_12_30"]
                for h in (12,30):
                    archived = dict(rows[f"{probe}/{h}",step])
                    del archived["run"]
                    assert digest(canonical(archived)) == g[f"{h}_sha256"]
            checks[probe] = dict(**check, contrasts_f64le=a["contrasts_f64le"], trigger=expected, D0=trigger["D0"])
    output = {"status":"all compared equal", "source":candidate, "author_source": AUTHOR, "author_data":DATA,
              "independent_source":REVIEW, "author_files_sha256":receipt["evidence_sha256"],
              "independent_replay_sha256":digest((EVIDENCE/"replay.json").read_bytes()),
              "independent_prefix_zip_sha256":digest((EVIDENCE/"prefixes.zip").read_bytes()),"checks":checks}
    path = EVIDENCE / "comparison.json"
    with path.open("xb") as f:
        f.write((json.dumps(output,indent=2)+"\n").encode())
    print("All agreed:",sum(len(c["cells"]) for c in checks.values()),"cells;",
          sum(p["bytes_equal"] for c in checks.values() for p in c["prefix"].values()),"prefix matrix bytes")


if __name__ == "__main__":
    main(*sys.argv[1:])
