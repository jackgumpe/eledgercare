"""Authenticate the two opening windows, shared eventual-query window and WP-0030 controls."""
import hashlib
import io
import json
import struct
import subprocess
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
RESERVATION = "74f23b10d428acc3477db6ce4af7eb663e28d9f4"
SOURCE = "7db67283a4ffd3e7a20bb8d80499572cc7118c71"
FIT = "6d79c24364ba10a1d9bfa4c72c837e2f216cf4bc"
FIXTURES = "ee8e96afcbd7a3c1f3eaa8125c05e68003c4a893"
TRACE = "7d65875a1ff2d7ad8a008ea83f5484507dbd5db3"
HISTORY = "841233517b4694d18d144f6d2d2b17e0d0a8b444"
GATE = "f51fa1dadec3e3f0e61b1d3ddade1891e24779e2"
SENSORS = {
    "original": ("c000c0299619345c887859b95c45befbb0c68987",
                 "docs/reviews/WP-0026/cal-features-primary/primary-001.zip",
                 "e708b33aa56fbcb78ceae2e3c59a795482d9a8f09bd6796b5d5291969540b46d"),
    "cedar": ("48016df280f8f0c2f4a807955d9f431744347ecc",
              "docs/research/WP-0029/acquisition/native-return.zip",
              "0346091957994fcfc5c12d8d87e40ce177bb0c1ff0cc376b5ba8f4fb7cb2522f"),
}
NAMES = ("Alder", "Cedar")
ACCESSED = {}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(rev, path, expected=None):
    ref = f"{rev}:{path}"
    data = subprocess.check_output(["git", "cat-file", "blob", ref], cwd=ROOT)
    digest = sha(data)
    assert expected is None or expected == digest, ref
    ACCESSED[ref] = digest
    return data


def read_archive(work):
    manifest = json.loads(blob(FIXTURES, "docs/fixtures/WP-0028/manifest.json"))
    history = json.loads(blob(HISTORY, "docs/research/WP-0029/scoring/evidence/result.json",
                              "93a6054a9f8b4db7a9e231e843ee6681cf55968e85e6adde5d31959c2cdeae1e"))
    gate = json.loads(blob(GATE, "docs/reviews/WP-0029/capture-gate.json",
                           "03e7eb07feae1f25c8db1fb4a7141820f0bda8497ab1b539bb4dbe169c51f870"))
    assert gate["authenticated"] and gate["eligible_owner_cue"]
    assert (gate["archive_revision"], gate["archive_sha256"]) == SENSORS["cedar"][::2]
    bindings = json.loads(blob(TRACE, "docs/reviews/WP-0030/evidence/bindings.json"))
    rows = {}
    for line in blob(TRACE, "docs/reviews/WP-0030/evidence/steps.jsonl").splitlines():
        r = json.loads(line)
        if r["phase"] == "post" and 1 <= r["step"] <= 8:
            rows[r["run"], r["step"]] = r
    fit = json.loads(blob(FIT, "docs/research/WP-0026/fit/fit.json"))
    assert fit["thresholds"] == history["thresholds"] == {p: [1., .1] for p in ("M1", "M3")}
    assert fit["weights"] == history["weights_sha256"]
    weights = {p: blob(FIT, f"docs/research/WP-0026/fit/{p}.pt", fit["weights"][p]) for p in ("M1", "M3")}
    for name in ("matrix", "online"):
        (work / f"{name}.py").write_bytes(blob(SOURCE, f"docs/research/WP-0024/probe/{name}.py"))
    by_horizon = {p["horizon"]: p for p in manifest["pairs"]}
    assert set(by_horizon) == {12, 30}
    windows = {}
    occurrences = {}
    for horizon, pair in by_horizon.items():
        assert pair["admitted"]
        for m in pair["members"]:
            recording = m["windows"]
            owner = m["owner"]
            assert owner in NAMES
            for label, w in ((owner, recording[0]), ("posting_query", recording[-1])):
                key = w["rgb_key"]
                assert key == sha((json.dumps([p["rgb_sha256"] for p in w["pages"]], indent=2) + "\n").encode())
                if label in windows:
                    assert windows[label]["rgb_key"] == key
                windows[label] = w
                for probe in weights:
                    binding = bindings[f"{probe}/{horizon}"][owner]
                    assert binding["binder"] == m["binder"]
                    assert binding["keys"][w["window"] - 1] == key
                occurrences[f"{horizon}/{owner}/{label}"] = key
    library = {k: ZipFile(io.BytesIO(blob(*spec))) for k, spec in SENSORS.items()}
    members = {}
    for name, w in windows.items():
        key = w["rgb_key"]
        inventory = history["capture_inventory"][key]
        assert inventory["pages"] == w["pages"]
        if name == "Cedar":
            assert w["feature"] is None and key == gate["rgb_key"]
            archive_tag, prefix = "cedar", "sensor/k0001/"
        else:
            f = w["feature"]
            assert (f["archive_revision"], f["archive"]) == SENSORS["original"][:2]
            archive_tag, prefix = "original", f["prefix"]
        assert inventory["source"] == ":".join(SENSORS[archive_tag][:2])
        assert inventory["prefix"] == prefix
        z = library[archive_tag]
        expected = inventory["members_sha256"]
        data = {}
        for fname, digest in expected.items():
            assert z.namelist().count(prefix + fname) == 1
            data[fname] = z.read(prefix + fname)
            assert sha(data[fname]) == digest
            if name == "Cedar":
                assert gate["members_sha256"][prefix + fname] == digest
        assert len(data) == 6
        receipt = json.loads(data["receipt.json"])
        assert receipt["verified"] and all(receipt["artifacts"][f] == s for f,s in expected.items() if f != "receipt.json")
        assert [p["rgb_sha256"] for p in receipt["pages"]] == [p["rgb_sha256"] for p in w["pages"]]
        meta = json.loads(data["metadata.json"])
        tokens = meta["token_ids"] + [meta["eos_id"]]
        assert data["through-eos.u32le"] == struct.pack(f"<{len(tokens)}I", *tokens)
        capture = json.loads(data["capture.json"])
        assert capture["pool_shape"] == [len(meta["spans"]), 1280]
        assert capture["pooled_sha256"] == expected["pooled.f32"]
        dest = work / name
        dest.mkdir()
        for file in ("pooled.f32", "metadata.json"):
            (dest / file).write_bytes(data[file])
        members[name] = {"rgb_key": key, "prefix": prefix, "members_sha256": expected}
    for z in library.values():
        z.close()
    return weights, bindings, rows, history["owner_anchor_sha256"], {"occurrences": occurrences, "windows": members}
