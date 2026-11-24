"""Resolve immutable bytes, verified calibration transport and public exposed scoring labels."""
import hashlib
import io
import json
import re
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = "d9741d6e880d06192b9f3e56ab8056d391da1b9e"
FIT = "6d79c24364ba10a1d9bfa4c72c837e2f216cf4bc"
ARCH = "1f246c71378e973e23ebeabfeb7fda56a8ccca2b"
FIT_PATH = "docs/research/WP-0026/fit/"
ZIP_DIR = "docs/reviews/WP-0026/cal-features-primary/"
SENSOR = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0026/review/runs/cal-features-r1/sensor")
HASHES = {}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)

def blob(rev, path):
    data = git("cat-file", "blob", rev + ":" + path)
    HASHES[rev + ":" + path] = sha(data)
    return data

def document(rev, path):
    return json.loads(blob(rev, path))

def check_local(rev, path):
    assert blob(rev, path).replace(b"\r\n", b"\n") == (ROOT / path).read_bytes().replace(b"\r\n", b"\n"), path

def sources(work):
    for path in ("docs/research/WP-0030/trace/inputs30.py", "docs/research/WP-0029/scoring/admission.py"):
        check_local(BASE, path)
    sys.path.insert(0, str(ROOT / "docs/research/WP-0030/trace"))
    from inputs30 import admit
    development, inventory, ref, fit, hashes = admit(work)
    HASHES.update(hashes)
    assert fit["thresholds"] == {"M1": [1.0, 0.1], "M3": [1.0, 0.1]}
    rankings = document(BASE, "docs/research/WP-0027/owners/owner-rankings.json")
    arms = rankings["arms"]
    routed = blob(FIT, FIT_PATH + "cal-transport.json")
    assert sha(routed) == fit["input_hashes"]["cal"]
    cal = json.loads(routed)["pairs"]
    inv = document(ARCH, ZIP_DIR + "inventory.json")
    zipped = blob(ARCH, ZIP_DIR + "primary-001.zip")
    assert sha(zipped) == inv["parts"]["primary-001.zip"]["sha256"]
    physical, custody, pairs = {}, [], []
    binders = arms["M1"]["by_binder"]
    with ZipFile(io.BytesIO(zipped)) as archive:
        assert len(set(archive.namelist())) == len(archive.namelist())
        for route in cal:
            pids = {binders[m["binder"]]["pair"] for m in route["twins"]}
            assert len(pids) == 1
            pid, = pids
            pub = arms["M1"]["by_pair"][pid]
            members, ordered = [], {}
            for m in route["twins"]:
                b = m["binder"]
                truth = binders[b]
                assert truth["target"] == pub["targets"][b] == m["target"]
                seq = [Path(p) for p in m["windows"]]
                tags = [p.name for p in seq]
                assert tags == truth["physical_tags"] and all(p.parent == SENSOR and re.fullmatch(r"k\d{4}", p.name) for p in seq)
                for tag in tags:
                    if tag in physical:
                        continue
                    prefix = "runs/cal-features-r1/sensor/" + tag + "/"
                    def load(name):
                        data = archive.read(prefix + name)
                        assert sha(data) == inv["members"][prefix + name]["sha256"]
                        return data
                    receipt_bytes = load("receipt.json")
                    receipt = json.loads(receipt_bytes)
                    assert receipt["verified"] and receipt["tag"] == tag and receipt["split"] == "cal"
                    old = rankings["physical_windows"][tag]
                    assert sha(receipt_bytes) == old["receipt_sha256"]
                    assert [r["rgb_sha256"] for r in receipt["pages"]] == old["ordered_rgb_sha256"]
                    digests = {"receipt.json": sha(receipt_bytes)}
                    for n, expected in receipt["artifacts"].items():
                        raw = load(n)
                        assert sha(raw) == expected
                        digests[n] = expected
                        if n in ("pooled.f32", "metadata.json"):
                            assert expected == old[n]
                            path = work / "windows" / tag / n
                            path.parent.mkdir(exist_ok=True, parents=True)
                            with path.open("xb") as out:
                                out.write(raw)
                    physical[tag] = dict(prefix=prefix, hashes=digests, pages=receipt["pages"])
                ordered[b] = [[physical[t]["hashes"][n] for n in ("receipt.json", "metadata.json", "pooled.f32")] for t in tags]
                owner = truth["expected"]["owner"]
                assert pub["true_owner_keys"][b] == (owner.casefold() if owner else None)
                assert all(arms["M3"]["by_binder"][b][k] == truth[k] for k in ("expected","pair","target","ambiguous","physical_tags"))
                members.append(dict(binder=b, target=m["target"], expected=truth["expected"], tags=tags))
            assert sorted(ordered) == sorted(pub["binders"])
            horizon, = {len(m["tags"]) * 3 for m in members}
            answerable = pub["outcome"] != "ambiguous_control"
            assert all(binders[b]["ambiguous"] != answerable for b in ordered)
            custody.append(dict(pair=pid,horizon=horizon,tier=1,answerable=answerable,members=ordered))
            pairs.append(dict(task="B",pair=pid,horizon=horizon,answerable=answerable,members=members))
    assert len(physical) == 29 and sum(len(s) for p in custody for s in p["members"].values()) == 140
    assert len(custody) == len({p["pair"] for p in custody}) == 10 and sum(p["answerable"] for p in custody) == 8
    task_a = []
    for p in development:
        base = binders[p["base_binder"]]
        assert (base["pair"],base["target"]) == (p["base_pair"],p["base_target"])
        members = [dict(binder=m["binder"], target=m["target"], tags=[w["rgb_key"] for w in m["windows"]],
                        expected={**base["expected"], "owner":m["owner"]}) for m in p["members"]]
        task_a.append(dict(task="A",pair=p["pair"],horizon=p["horizon"],answerable=True,members=members,
                           base_binder=p["base_binder"],base_target=p["base_target"],base_pair=p["base_pair"]))
    steps = [json.loads(s) for s in blob(BASE,"docs/reviews/WP-0030/evidence/steps.jsonl").splitlines()]
    controls = document(BASE, "docs/coordination/WP-0033/reconciliation.json")["rows"]
    assert len(steps) == 224
    bindings = dict(calibration_archive=ARCH + ":" + ZIP_DIR + "primary-001.zip", physical=physical,
                    development_inventory=inventory,routes=task_a+pairs,weights=fit["weights"],cuts=fit["thresholds"])
    return task_a, pairs, custody, bindings, arms, steps, controls
