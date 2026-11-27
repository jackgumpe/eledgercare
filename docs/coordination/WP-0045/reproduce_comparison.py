"""Reproduce complete WP-0045 comparisons from the pre-opening Git objects."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from compare_rows import compare, read

BASE = "365f619dd273a517736a76f4f028256355003a65"
FIXTURE = "c9a0402fe815441169eb5bfe2331be7b170526fa"
SEAL = "261f36893db27ee5ad8627366c3842fa140c8383"
ROUTES = {
    "direct": ("2514ca6c7d31f417b0617ec230037c688c610e52", "docs/research/WP-0045", "results.json", ["live","constructed","archive"]),
    "edition": ("2c9637e465ed0ca6e9ce4d023aba3e5c2be548bf", "docs/editions/WP-0045/evidence/blind", "returns.json", ["A1","A2","C1"]),
    "review": ("5f1ce93dc933a52fe8dd5d6c8668b9aa34a374e6", "docs/reviews/WP-0045/blind", "rows.json", ["live","constructed","archive","A1","A2","C1"]),
}


def blob(rev, path):
    return subprocess.check_output(["git","show",rev+":"+path])


def digest(b):
    return hashlib.sha256(b).hexdigest()


def run(opened):
    raw = blob(SEAL, "docs/fixtures/WP-0045/oracle-commitment.json")
    committed = json.loads(raw)["sealed_files"]
    for name, item in committed.items():
        assert digest((opened/name).read_bytes()) == item["sha256"]
    manifest = read(opened/"expected-manifest.json")
    expected = {}
    for key,item in manifest["rows"].items():
        path = opened/item["path"]
        assert len(path.read_bytes()) == item["bytes"] and digest(path.read_bytes()) == item["sha256"]
        expected[key] = read(path)
    manifest_raw = blob(FIXTURE,"docs/fixtures/WP-0045/manifest.json")
    assert digest(manifest_raw) == manifest["fixture_manifest_sha256"]
    observed_inputs = {}
    for row in json.loads(manifest_raw)["rows"]:
        item = row["input"]
        b = blob(FIXTURE,"docs/fixtures/WP-0045/"+item["path"])
        assert digest(b) == item["sha256"] and len(b) == item["bytes"]
        observed_inputs[row["id"]] = digest(b)
    freeze = json.loads(blob(BASE,"docs/coordination/WP-0045/execution-freeze.json"))
    schedule = json.loads(blob(BASE,"docs/coordination/WP-0045/schedule.json"))
    assert freeze["input_hashes"] == observed_inputs and observed_inputs.keys() == expected.keys()
    records = {}
    actual_rows = {}
    for name,(rev,prefix,path,groups) in ROUTES.items():
        actual = json.loads(blob(rev,prefix+"/"+path))
        seen = json.loads(blob(rev,prefix+"/input-sha256.json"))
        actual_rows[name] = actual
        records[name] = compare(expected,actual,observed_inputs,seen,schedule,groups)
    pairs = {k: actual_rows[role].get(k)==actual_rows["review"].get(k) for role in ("direct","edition") for k in actual_rows[role]}
    return {"oracle_manifest_sha256":committed["expected-manifest.json"]["sha256"], "frozen_inputs":FIXTURE,
            "routes":records, "cross_route_equality_by_id":pairs, "distinct_cases":len(expected)}


if __name__ == "__main__":
    result = run(Path(sys.argv[1]))
    with Path(sys.argv[2]).open("x",encoding="utf8",newline="\n") as out:
        json.dump(result,out,indent=2)
        out.write("\n")
    print(json.dumps({k:v["matches_and_scheduled"] for k,v in result["routes"].items()}))
