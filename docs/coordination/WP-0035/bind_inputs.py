"""Authenticate exposed routes, feature triplets and score references before evaluating an arm."""
import hashlib
import io
import json
from pathlib import Path, PureWindowsPath
import subprocess
import sys
import zipfile

BASE = "d9741d6e880d06192b9f3e56ab8056d391da1b9e"
CAL = "1f246c71378e973e23ebeabfeb7fda56a8ccca2b"
FIT = "6d79c24364ba10a1d9bfa4c72c837e2f216cf4bc"
NATIVE = "7db67283a4ffd3e7a20bb8d80499572cc7118c71"
FIXTURE = "ee8e96afcbd7a3c1f3eaa8125c05e68003c4a893"
GATE = "f51fa1dadec3e3f0e61b1d3ddade1891e24779e2"
CALDIR = "docs/reviews/WP-0026/cal-features-primary/"
CAL_ZIP = CALDIR + "primary-001.zip"
ITEMS = ("receipt.json", "metadata.json", "pooled.f32")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(ok, message):
    if not ok:
        raise ValueError(message)


def inventory():
    references = {}

    def read(rev, path, expected=None):
        key = rev + ":" + path
        raw = subprocess.check_output(["git", "cat-file", "blob", key])
        references[key] = sha(raw)
        if expected is not None:
            check(references[key] == expected, key)
        return raw

    routes = json.loads(read(FIT, "docs/research/WP-0026/fit/cal-transport.json"))
    historic = json.loads(read(BASE, "docs/research/WP-0027/owners/owner-rankings.json"))
    fit = json.loads(read(FIT, "docs/research/WP-0026/fit/fit.json"))
    for arm in ("M1", "M3"):
        read(FIT, "docs/research/WP-0026/fit/" + arm + ".pt", fit["weights"][arm])
        check(fit["thresholds"][arm] == [1.0, 0.1], "Native thresholds")
    for name in ("online.py", "matrix.py", "run.py"):
        read(NATIVE, "docs/research/WP-0024/probe/" + name)
    read("6e0f1cd046ddc3683e8e9c532f75380e8d6cef29", "docs/research/WP-0033/erasure.py")
    read(BASE, "docs/coordination/WP-0033/reconciliation.json")
    steps = [json.loads(s) for s in read(BASE, "docs/reviews/WP-0030/evidence/steps.jsonl").splitlines()]
    check(len(steps) == 224, "Native archive length")
    runtime = json.loads(read(BASE, "docs/coordination/WP-0030/runtime.json"))
    check(sha(Path(runtime["executable"]).read_bytes()) == runtime["python_sha256"], "Runtime executable")
    arch_inv = json.loads(read(CAL, CALDIR + "inventory.json"))
    cal_raw = read(CAL, CAL_ZIP, arch_inv["parts"]["primary-001.zip"]["sha256"])
    record = historic["arms"]["M1"]
    paired = {frozenset(p["binders"]): key for key,p in record["by_pair"].items()}
    by_binder = record["by_binder"]
    windows, cal_pairs = {}, {}
    with zipfile.ZipFile(io.BytesIO(cal_raw)) as archive:
        for route in routes["pairs"]:
            key = paired[frozenset(b["binder"] for b in route["twins"])]
            prior_pair = record["by_pair"][key]
            pair = {"tier": 1, "members": {}, "answerable": not bool(prior_pair["exceptions"])}
            for binder in route["twins"]:
                bid = binder["binder"]
                archived = by_binder[bid]
                check(pair["answerable"] == (not archived["ambiguous"]), "Exposed target stratum")
                tags = [PureWindowsPath(p).name for p in binder["windows"]]
                pair.setdefault("horizon", 3 * len(tags))
                check(3 * len(tags) == pair["horizon"], "Mixed horizon")
                for tag in tags:
                    if tag in windows:
                        continue
                    prefix = f"runs/cal-features-r1/sensor/{tag}/"
                    rows = {n: archive.read(prefix + n) for n in ITEMS}
                    digests = [sha(rows[n]) for n in ITEMS]
                    receipt = json.loads(rows["receipt.json"])
                    frozen = historic["physical_windows"][tag]
                    check(receipt["tag"] == tag and receipt["verified"] and receipt["split"] == "cal", prefix)
                    check(digests == [arch_inv["members"][prefix+n]["sha256"] for n in ITEMS], prefix)
                    check(digests == [frozen["receipt_sha256"], frozen["metadata.json"], frozen["pooled.f32"]], prefix)
                    check(digests[1:] == [receipt["artifacts"][n] for n in ITEMS[1:]], prefix)
                    check(len(rows["pooled.f32"]) == len(json.loads(rows["metadata.json"])["spans"]) * 5120, prefix)
                    windows[tag] = digests
                pair["members"][bid] = {"windows": tags, "target": binder["target"], "expected": archived["expected"],
                                       "attempt_count": archived["attempt_count"], "stratum": archived["stratum"]}
            cal_pairs[key] = pair
    check(len(cal_pairs) == 10 and sum(p["answerable"] for p in cal_pairs.values()) == 8 and len(windows) == 29,
          "Archived calibration population")
    fixture = json.loads(read(FIXTURE, "docs/fixtures/WP-0028/manifest.json"))
    gate = json.loads(read(GATE, "docs/reviews/WP-0029/capture-gate.json"))
    check(gate["authenticated"] and gate["eligible_owner_cue"], "Cedar release")
    new_raw = read(gate["archive_revision"], "docs/research/WP-0029/acquisition/native-return.zip", gate["archive_sha256"])
    with zipfile.ZipFile(io.BytesIO(new_raw)) as archive:
        cedar = [sha(archive.read("sensor/k0001/" + n)) for n in ITEMS]
    check(cedar == [gate["members_sha256"]["sensor/k0001/" + n] for n in ITEMS], "Cedar triplet")
    historical_a = "c000c0299619345c887859b95c45befbb0c68987"
    read(historical_a, CAL_ZIP, sha(cal_raw))
    task_a = {}
    for pair in fixture["pairs"]:
        result = {"horizon": pair["horizon"], "base_pair": pair["base_pair"], "base_binder": pair["base_binder"], "members": {}}
        for member in pair["members"]:
            ordered = []
            for window in member["windows"]:
                f = window["feature"]
                if f is None:
                    check(window["rgb_key"] == gate["rgb_key"] and window["window"] == 1 and member["owner"] == "Cedar", "Unbound feature")
                    ordered.append({"rgb_key": window["rgb_key"], "capture": "cedar", "hashes": cedar})
                else:
                    hashes = [f[k] for k in ("receipt_sha256", "metadata_sha256", "pooled_sha256")]
                    check(f["archive"] == CAL_ZIP and f["archive_revision"] == historical_a and hashes == windows[f["tag"]], "Task A historical input")
                    ordered.append({"rgb_key": window["rgb_key"], "capture": f["tag"], "hashes": hashes})
            expected = {**by_binder[pair["base_binder"]]["expected"], "owner": member["owner"]}
            result["members"][member["binder"]] = {"owner": member["owner"], "expected": expected, "windows": ordered}
        task_a[pair["pair"]] = result
    check(len({w["rgb_key"] for p in task_a.values() for m in p["members"].values() for w in m["windows"]}) == 11, "Task A coverage")
    return {"base": BASE, "references_sha256": references, "calibration_archive": CAL+":"+CAL_ZIP,
            "cal_windows_receipt_metadata_pooled": windows, "B": cal_pairs, "A": task_a,
            "runtime": {k: runtime[k] for k in ("executable", "python_sha256", "torch", "numpy", "threads", "interop_threads")}}


if __name__ == "__main__":
    result = inventory()
    with Path(sys.argv[1]).open("x", encoding="utf8", newline="\n") as out:
        json.dump(result, out, indent=2, sort_keys=True)
        out.write("\n")
    print("Task A horizons",len(result["A"]), "Task B calibration pairs",len(result["B"]), "authenticated calibration captures",len(result["cal_windows_receipt_metadata_pooled"]))
