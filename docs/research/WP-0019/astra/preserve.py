"""Package author accounting and verify the coordinator's immutable output receipts."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile


def read(path):
    return json.loads(path.read_bytes())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def stable(obj):
    # These are the only per-recognition fields allowed to differ across the two real executions.
    if isinstance(obj, list):
        return [stable(i) for i in obj]
    if isinstance(obj, dict):
        return {k: stable(v) for k, v in obj.items() if k not in {"pid", "recognize_ms", "call_ms"}}
    return obj


def write(path, obj):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, allow_nan=False, indent=2)
        f.write("\n")


def preserve(stage, scratch, out):
    release = stage / "return.json"
    ledger = read(release)
    out.mkdir(parents=True, exist_ok=False)
    results = {}
    members = {}
    evidence_zip = out / "post-score-files.zip"
    with zipfile.ZipFile(evidence_zip, "x", compression=zipfile.ZIP_DEFLATED) as z:
        for ret in ledger["runs"]:
            family, order = ret["family"], ret["order"]
            code = family + "-" + order
            official = stage / code
            assert ret["exit"] == 0
            for name, want in ret["outputs"].items():
                assert digest(official / name) == want, (code, name)
            scored = scratch / ("scored-"+code)
            for path in sorted(scored.iterdir()):
                member = code+"/"+path.name
                info = zipfile.ZipInfo(member)
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, path.read_bytes())
                members[member] = digest(path)
            results[code] = dict(coordinator_files_verified=len(ret["outputs"]),
                                 prediction_sha256={a: digest(official / a / "prediction.json") for a in "AB"},
                                 **read(scored/"summary.json"))
    with zipfile.ZipFile(evidence_zip) as z:
        assert z.testzip() is None and set(z.namelist()) == set(members)
        assert all(sha256(z.read(name)).hexdigest() == value for name, value in members.items())
    for family in ("H", "A"):
        pair = [stage / (family+"-"+order) for order in ("AB", "BA")]
        assert results[pair[0].name]["prediction_sha256"] == results[pair[1].name]["prediction_sha256"]
        for arm in ("A", "B"):
            paths = sorted((pair[0]/arm).glob("page-*.json"))
            assert len(paths) == len(sorted((pair[1]/arm).glob("page-*.json")))
            for p in paths:
                assert stable(read(p)) == stable(read(pair[1]/arm/p.name)), (family, arm, p.name)
        sa, sb = [scratch / ("scored-"+p.name) for p in pair]
        for arm in "AB":
            name = "score-"+arm+".json"
            assert digest(sa/name) == digest(sb/name)
        assert stable(read(sa/"all-fields.json")) == stable(read(sb/"all-fields.json"))
    witnesses = {f: read(scratch/f"scored-{f}-AB/nine-witness-subset.json") for f in ("H", "A")}
    assert sum(r["witness"] for rows in witnesses.values() for r in rows) == 4
    assert sum(r["nonempty_cell_no_full_word_intersection"] for rows in witnesses.values() for r in rows) == 5
    write(out/"nine-fields.json", witnesses)
    write(out/"summary.json", dict(trial_candidate=ledger["candidate"], return_sha256=digest(release),
                                  archive_sha256=digest(evidence_zip), member_sha256=members, runs=results,
                                  stable_outputs_equal_ignoring=["pid", "recognize_ms", "call_ms"]))
    print("Verified", sum(r["coordinator_files_verified"] for r in results.values()),
          "frozen coordinator files and", len(members), "post-score archive members")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("stage", "scratch", "out"):
        p.add_argument("--"+name, required=True, type=Path)
    a = p.parse_args()
    preserve(a.stage.resolve(), a.scratch.resolve(), a.out.resolve())
