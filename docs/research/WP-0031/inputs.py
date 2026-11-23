"""Authenticate two development openings plus their archived query/anchor and parity records."""
import io
import json
import struct
import subprocess
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
TRACE_SOURCE = "603cfbc85c259112fb76ea7c1b9c514557149653"
TRACE_DATA = "7d65875a1ff2d7ad8a008ea83f5484507dbd5db3"


def archive_helpers(library):
    # Reuse the old authenticated blob reader and its immutable revision/hash constants.
    path = "docs/reviews/WP-0030/inputs.py"
    raw = subprocess.check_output(["git", "cat-file", "blob", f"{TRACE_SOURCE}:{path}"], cwd=ROOT)
    import types
    archive = types.ModuleType("wp0030_inputs")
    archive.__file__ = str(ROOT / path)
    exec(compile(raw, archive.__file__, "exec"), archive.__dict__)
    archive.blob(TRACE_SOURCE, path, archive.sha(raw))
    archive.blob(TRACE_SOURCE, "docs/reviews/WP-0030/replay.py")
    for name in ("matrix", "online"):
        archive.write(library / f"{name}.py", archive.blob(archive.PROBE, f"docs/research/WP-0024/probe/{name}.py"))
    return archive


def inputs(archive, work):
    def document(revision, path, *digest):
        return json.loads(archive.blob(revision, path, *digest))

    manifest = document(archive.FIX, "docs/fixtures/WP-0028/manifest.json")
    history = document(*archive.HISTORY)
    fit = document(archive.FIT, "docs/research/WP-0026/fit/fit.json")
    gate = document(*archive.GATE)
    assert gate["authenticated"] and gate["eligible_owner_cue"] and gate["archive_revision"] == archive.NEW[0]
    assert gate["archive_sha256"] == archive.NEW[2] and gate["parents"][0]["literal"] == "Ledger: Cedar"
    assert history["gate"]["sha256"] == archive.GATE[2]
    assert fit["weights"] == history["weights_sha256"]
    assert fit["thresholds"] == history["thresholds"] == {arm: [1.0, 0.1] for arm in ("M1", "M3")}
    weights = {arm: archive.blob(archive.FIT, f"docs/research/WP-0026/fit/{arm}.pt", fit["weights"][arm])
               for arm in ("M1", "M3")}
    bindings = document(TRACE_DATA, "docs/reviews/WP-0030/evidence/bindings.json")
    lines = archive.blob(TRACE_DATA, "docs/reviews/WP-0030/evidence/steps.jsonl")
    steps = {}
    for line in lines.splitlines():
        row = json.loads(line)
        if row["phase"] == "post" and 1 <= row["step"] <= 8:
            rows = steps.setdefault(row["run"], {})
            assert row["step"] not in rows
            rows[row["step"]] = row
    assert set(bindings) == set(steps) == {"M1/12", "M1/30", "M3/12", "M3/30"}
    assert all(set(rows) == set(range(1, 9)) for rows in steps.values())

    pairs = {p["horizon"]: {m["owner"]: m for m in p["members"]} for p in manifest["pairs"]}
    captures = {}
    for owner in archive.NAMES:
        first = pairs[12][owner]["windows"][0]
        assert first == pairs[30][owner]["windows"][0] and first["window"] == 1
        key = first["rgb_key"]
        ref = history["capture_inventory"][key]
        assert first["pages"] == ref["pages"]
        rgb = [page["rgb_sha256"] for page in first["pages"]]
        assert archive.sha((json.dumps(rgb, indent=2) + "\n").encode()) == key
        if owner == "Alder":
            source = archive.OLD
            feature = first["feature"]
            assert (feature["archive_revision"], feature["archive"]) == source[:2]
            prefix = feature["prefix"]
            expected = {name: feature[digest] for name, digest in archive.MEMBERS.items()}
        else:
            source = archive.NEW
            assert first["feature"] is None and key == gate["rgb_key"]
            prefix = "sensor/k0001/"
            expected = {name: gate["members_sha256"][prefix + name] for name in archive.MEMBERS}
        assert ref["source"] == ":".join(source[:2]) and ref["prefix"] == prefix
        assert expected == ref["members_sha256"]
        with ZipFile(io.BytesIO(archive.blob(*source))) as z:
            assert len(z.namelist()) == len(set(z.namelist()))
            members = {name: z.read(prefix + name) for name in expected}
        assert {k: archive.sha(v) for k, v in members.items()} == expected
        receipt = json.loads(members["receipt.json"])
        assert receipt["verified"] and [p["rgb_sha256"] for p in receipt["pages"]] == rgb
        assert all(receipt["artifacts"][name] == digest for name, digest in expected.items() if name != "receipt.json")
        meta = json.loads(members["metadata.json"])
        ids = meta["token_ids"] + [meta["eos_id"]]
        assert struct.pack(f"<{len(ids)}I", *ids) == members["through-eos.u32le"]
        assert len(meta["spans"]) == 16 and len(members["pooled.f32"]) == 16 * 1280 * 4
        for name in ("pooled.f32", "metadata.json"):
            archive.write(work / owner / name, members[name])
        captures[owner] = {"rgb_key": key, "prefix": prefix, "source": source, "members": expected,
                           "page_rgb_sha256": rgb, "binders": {h: p[owner]["binder"] for h, p in pairs.items()}}
    return captures, weights, fit["thresholds"], history["owner_anchor_sha256"], bindings, steps
