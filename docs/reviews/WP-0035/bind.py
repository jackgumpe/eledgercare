"""Authenticate development and exposed calibration streams. No model import or score computation."""
import io
import json
import re
import subprocess
import sys
import types
from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = "d8db225dae2c2ea4d70896c1936a1e1e22a104e2"
SCRATCH = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0035/review")
ARCHIVE = "1f246c71378e973e23ebeabfeb7fda56a8ccca2b"
FIT = "6d79c24364ba10a1d9bfa4c72c837e2f216cf4bc"
BLOBS = {}


def sha(data):
    return sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def blob(rev, path, expected=None):
    assert "private" not in path and "blind" not in path
    spec = rev + ":" + path
    data = git("cat-file", "blob", spec)
    BLOBS[spec] = sha(data)
    assert expected is None or BLOBS[spec] == expected, spec
    return data


def save(path, data):
    path.write_bytes((json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())


def acquire(work):
    path = "docs/reviews/WP-0030/inputs.py"
    loader = types.ModuleType("development_archive_loader")
    loader.__file__ = str(ROOT / path)
    exec(compile(blob(BASE, path), path, "exec"), loader.__dict__)
    fixtures, development, fit, weights, catalog = loader.prepare(work)
    BLOBS.update(loader.RECEIPTS)
    archive_steps = [json.loads(line) for line in blob(BASE, "docs/reviews/WP-0030/evidence/steps.jsonl",
        "cd1bc86b9e4b1e8e9c49d1c1ba86f96586afb33336741580746ab938f1e3600c").splitlines()]
    blob(BASE, "docs/reviews/WP-0033/evidence/parity.json")
    controls = json.loads(blob(BASE, "docs/coordination/WP-0033/reconciliation.json"))["rows"]
    ranks = json.loads(blob(BASE, "docs/research/WP-0027/owners/owner-rankings.json"))
    ref = ranks["input_sha256"]

    def pinned(rev, path):
        return blob(rev, path, ref[rev + ":" + path])

    route = json.loads(pinned(FIT, "docs/research/WP-0026/fit/cal-transport.json"))
    assert fit["input_hashes"]["cal"] == ref[FIT + ":docs/research/WP-0026/fit/cal-transport.json"]
    prefix = "docs/reviews/WP-0026/cal-features-primary/"
    inventory = json.loads(pinned(ARCHIVE, prefix + "inventory.json"))
    packed = pinned(ARCHIVE, prefix + "primary-001.zip")
    assert sha(packed) == inventory["parts"]["primary-001.zip"]["sha256"]
    physical = {}
    with ZipFile(io.BytesIO(packed)) as z:
        assert len(z.namelist()) == len(set(z.namelist()))
        for tag, old in sorted(ranks["physical_windows"].items()):
            assert re.fullmatch(r"k\d{4}", tag)
            address = "runs/cal-features-r1/sensor/" + tag + "/"
            def member(name):
                data = z.read(address + name)
                assert sha(data) == inventory["members"][address + name]["sha256"]
                return data
            rec = member("receipt.json")
            receipt = json.loads(rec)
            assert receipt["verified"] and (receipt["split"], receipt["tag"]) == ("cal", tag)
            assert sha(rec) == old["receipt_sha256"]
            assert old["ordered_rgb_sha256"] == [p["rgb_sha256"] for p in receipt["pages"]]
            dest = work / "cal" / tag
            dest.mkdir(parents=True)
            for name in ("metadata.json", "pooled.f32"):
                data = member(name)
                assert sha(data) == old[name] == receipt["artifacts"][name]
                (dest / name).write_bytes(data)
            physical[tag] = dict(old, archive_prefix=address)
    assert len(physical) == 29
    arms = ranks["arms"]
    cases, custody = [], []
    original = arms["M1"]["by_binder"]
    for group in route["pairs"]:
        members = {}
        for twin in group["twins"]:
            binder = twin["binder"]
            first = original[binder]
            tags = [Path(p).name for p in twin["windows"]]
            assert tags == first["physical_tags"] and twin["target"] == first["target"]
            pair = first["pair"]
            for info in arms.values():
                p, b = info["by_pair"][pair], info["by_binder"][binder]
                assert b["expected"] == first["expected"] and b["ambiguous"] == first["ambiguous"]
                assert b["binder"] == binder and b["pair"] == pair and b["target"] == p["targets"][binder] == twin["target"]
                assert b["twin_binder"] in p["binders"] and sorted(p["binders"]) == sorted(x["binder"] for x in group["twins"])
                expected = b["expected"]["owner"]
                assert (expected.casefold() if expected else None) == p["true_owner_keys"][binder]
            members[binder] = dict(target=twin["target"], keys=tags, expected=first["expected"],
                                   stratum=first["stratum"], answerable=not first["ambiguous"])
        assert len(members) == 2
        length, = {len(v["keys"])*3 for v in members.values()}
        answerable, = {v["answerable"] for v in members.values()}
        identity = dict(task="B", pair=pair, horizon=length)
        cases.append(dict(**identity, members=members))
        hashes = {b:[[physical[k][f] for f in ("receipt_sha256","metadata.json","pooled.f32")]
                     for k in item["keys"]] for b,item in members.items()}
        custody.append(dict(pair=pair, horizon=length, answerable=answerable, tier=1, members=hashes))
    assert sum(c["answerable"] for c in custody) == 8 and len(custody) == 10
    assert len({c["pair"] for c in custody}) == 10
    assert sum(len(w) for p in custody for w in p["members"].values()) == 140
    for pair in fixtures["pairs"]:
        base_binder = original[pair["base_binder"]]
        assert base_binder["pair"] == pair["base_pair"] and base_binder["target"] == pair["base_target"]
        members = {m["binder"]:dict(target=m["target"], keys=[w["rgb_key"] for w in m["windows"]],
                   answerable=True, expected=dict(base_binder["expected"], owner=m["owner"]),
                   base_binder=pair["base_binder"], base_target=pair["base_target"]) for m in pair["members"]}
        cases.append(dict(task="A", pair=pair["pair"], horizon=pair["horizon"], members=members))
    compact = {k:{f:v for f,v in item.items() if f in ("source","prefix","pages","members")}
               for k,item in catalog["captures"].items()}
    bindings = dict(git_blobs=BLOBS.copy(), calibration_windows=physical, development_windows=compact,
                    cases=cases, custody=custody, thresholds=fit["thresholds"],
                    capture_tier_counts={"1":len(custody),"2":0,"3":0})
    return bindings, weights, archive_steps, controls, arms, development


if __name__ == "__main__":
    dest = SCRATCH / sys.argv[1]
    dest.mkdir(exist_ok=False)
    result = acquire(dest)[0]
    save(HERE / "bindings.json", result)
