"""Read the two approved development archives, authenticate the rows and stage parser inputs."""
import hashlib
import io
import json
import struct
import subprocess
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
BASE = "f19d7fdca840af7b81e6a0bb1edd062d690898de"
FIX = "ee8e96afcbd7a3c1f3eaa8125c05e68003c4a893"
PROBE = "7db67283a4ffd3e7a20bb8d80499572cc7118c71"
FIT = "6d79c24364ba10a1d9bfa4c72c837e2f216cf4bc"
HISTORY = ("841233517b4694d18d144f6d2d2b17e0d0a8b444", "docs/research/WP-0029/scoring/evidence/result.json",
           "93a6054a9f8b4db7a9e231e843ee6681cf55968e85e6adde5d31959c2cdeae1e")
GATE = ("f51fa1dadec3e3f0e61b1d3ddade1891e24779e2", "docs/reviews/WP-0029/capture-gate.json",
        "03e7eb07feae1f25c8db1fb4a7141820f0bda8497ab1b539bb4dbe169c51f870")
OLD = ("c000c0299619345c887859b95c45befbb0c68987", "docs/reviews/WP-0026/cal-features-primary/primary-001.zip",
       "e708b33aa56fbcb78ceae2e3c59a795482d9a8f09bd6796b5d5291969540b46d")
NEW = ("48016df280f8f0c2f4a807955d9f431744347ecc", "docs/research/WP-0029/acquisition/native-return.zip",
       "0346091957994fcfc5c12d8d87e40ce177bb0c1ff0cc376b5ba8f4fb7cb2522f")
MEMBERS = {"metadata.json": "metadata_sha256", "pooled.f32": "pooled_sha256",
           "through-eos.u32le": "through_eos_sha256", "capture.json": "capture_sha256",
           "native.json": "native_sha256", "receipt.json": "receipt_sha256"}
NAMES = ("Alder", "Cedar")
RECEIPTS = {}


def sha(value):
    return hashlib.sha256(value).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def blob(revision, path, expected=None):
    ref = f"{revision}:{path}"
    raw = subprocess.check_output(["git", "cat-file", "blob", ref], cwd=ROOT)
    digest = sha(raw)
    assert expected is None or digest == expected, ref
    RECEIPTS[ref] = digest
    return raw


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def prepare(work):
    manifest = json.loads(blob(FIX, "docs/fixtures/WP-0028/manifest.json"))
    baseline = json.loads(blob(*HISTORY))
    gate = json.loads(blob(*GATE))
    fit = json.loads(blob(FIT, "docs/research/WP-0026/fit/fit.json"))
    assert gate["authenticated"] and gate["eligible_owner_cue"] and gate["archive_revision"] == NEW[0]
    assert gate["archive_sha256"] == NEW[2] and gate["parents"][0]["literal"] == "Ledger: Cedar"
    assert baseline["arm_pair_counts"] == {"planned": 4, "completed": 4, "admitted": 4}
    assert baseline["gate"]["sha256"] == GATE[2] and baseline["weights_sha256"] == fit["weights"]
    assert baseline["thresholds"] == fit["thresholds"] == {arm: [1.0, 0.1] for arm in ("M1", "M3")}
    for filename in ("matrix.py", "online.py"):
        write(work / "library" / filename, blob(PROBE, "docs/research/WP-0024/probe/" + filename))
    weights = {arm: blob(FIT, f"docs/research/WP-0026/fit/{arm}.pt", fit["weights"][arm])
               for arm in ("M1", "M3")}
    unique = {}
    uses = []
    with ZipFile(io.BytesIO(blob(*OLD))) as old, ZipFile(io.BytesIO(blob(*NEW))) as new:
        for archive in (old, new):
            assert len(archive.namelist()) == len(set(archive.namelist()))
        for pair in manifest["pairs"]:
            for member in pair["members"]:
                blob(FIX, member["source_pdf"], member["source_pdf_sha256"])
                for ordinal, window in enumerate(member["windows"], 1):
                    key = window["rgb_key"]
                    assert ordinal == window["window"] and len(window["pages"]) == 3
                    rgb = [p["rgb_sha256"] for p in window["pages"]]
                    assert sha((json.dumps(rgb, indent=2) + "\n").encode()) == key
                    uses.append([pair["horizon"], member["owner"], ordinal, key])
                    hist = baseline["capture_inventory"][key]
                    assert hist["pages"] == window["pages"]
                    f = window["feature"]
                    if f is None:
                        assert key == gate["rgb_key"] and member["owner"] == "Cedar" and ordinal == 1
                        archive, source, prefix = new, NEW, "sensor/k0001/"
                        expect = {name: gate["members_sha256"][prefix + name] for name in MEMBERS}
                    else:
                        archive, source, prefix = old, OLD, f["prefix"]
                        assert (f["archive_revision"], f["archive"]) == OLD[:2]
                        assert prefix == f"runs/cal-features-r1/sensor/{f['tag']}/"
                        expect = {name: f[prop] for name, prop in MEMBERS.items()}
                    assert hist["source"] == ":".join(source[:2]) and prefix == hist["prefix"]
                    assert expect == hist["members_sha256"]
                    if key in unique:
                        assert unique[key]["prefix"] == prefix
                        continue
                    data = {name: archive.read(prefix + name) for name in MEMBERS}
                    assert {name: sha(raw) for name, raw in data.items()} == expect
                    dest = work / "captures" / key
                    for name in ("metadata.json", "pooled.f32"):
                        write(dest / name, data[name])
                    receipt = json.loads(data["receipt.json"])
                    capture = json.loads(data["capture.json"])
                    assert receipt["verified"] and all(receipt["artifacts"][k] == v for k, v in expect.items()
                                                       if k != "receipt.json")
                    assert [(p["sha256"], p["rgb_sha256"]) for p in receipt["pages"]] == [
                        (p["sha256"], p["rgb_sha256"]) for p in window["pages"]]
                    meta = json.loads(data["metadata.json"])
                    ids = meta["token_ids"] + [meta["eos_id"]]
                    assert data["through-eos.u32le"] == struct.pack(f"<{len(ids)}I", *ids)
                    pool = data["pooled.f32"]
                    assert capture["pool_shape"] == [len(meta["spans"]), 1280] and len(pool) == len(meta["spans"]) * 5120
                    assert sha(pool) == capture["pooled_sha256"]
                    spans = []
                    for idx, row in enumerate(meta["spans"]):
                        assert row["index"] == idx and idx * 5120 < len(pool)
                        positions = row["token_indices"]
                        assert positions and positions == sorted(set(positions)) and positions[-1] < len(ids)-1
                        start, stop = row["byte_range"]
                        native_slice = meta["raw"].encode("utf-8")[start:stop]
                        spans.append({"raw_record": row, "metadata_sha256": sha(encoded(row)),
                                      "text_sha256": sha(row["text"].encode()), "raw_slice_sha256": sha(native_slice),
                                      "token_ids": [ids[i] for i in positions],
                                      "feature_f32le_sha256": sha(pool[idx*5120:(idx+1)*5120])})
                    unique[key] = {"source": list(source), "prefix": prefix, "pages": window["pages"],
                                   "members": expect, "capture": capture, "spans": spans}
    assert len(unique) == 11 and len(uses) == 28
    return manifest, baseline, fit, weights, {"uses": uses, "captures": unique}
