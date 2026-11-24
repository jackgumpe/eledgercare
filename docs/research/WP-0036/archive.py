"""Read only the released Git objects and verify raw, parsed and feature provenance."""
import gzip
import hashlib
import io
import json
import math
import re
import struct
import subprocess
from pathlib import Path, PureWindowsPath
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
BASE = "b72132c07444eda8abe94d004a6e7488cf4bec26"
SENSOR = PureWindowsPath("C:/Users/jackg/eLedgerCare-Speed/WP-0026/review/runs/cal-features-r1/sensor")
CUSTODY = "docs/coordination/WP-0035/input-custody.json"
NATIVE = "docs/research/WP-0024/probe/online.py"
TERMINALS = "docs/research/WP-0035/evidence/terminals.json.gz"
ITEMS = ("receipt.json", "metadata.json", "pooled.f32")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(key, digest=None):
    raw = subprocess.check_output(["git", "cat-file", "blob", key], cwd=ROOT)
    assert digest is None or sha(raw) == digest, key
    return raw


def admit(online):
    custody = json.loads(blob(BASE + ":" + CUSTODY, "216decb4492bb91c46536fb8f473788b4e4aa439563f992e75232da7aa8cccbf"))
    refs = custody["references_sha256"]
    def checked(suffix):
        key, = [k for k in refs if k.endswith(suffix) and not k.startswith("c000c029")]
        return blob(key, refs[key])
    assert (ROOT / NATIVE).read_bytes().replace(b"\r\n", b"\n") == checked(":" + NATIVE).replace(b"\r\n", b"\n")
    capture_inventory = json.loads(checked("cal-features-primary/inventory.json"))["members"]
    capture_gate = json.loads(checked("capture-gate.json"))
    assert capture_gate["authenticated"] and capture_gate["eligible_owner_cue"]
    physical = {}
    audit = []
    for archive_name, prefix, tags, inventory in (
        ("cal-features-primary/primary-001.zip", "runs/cal-features-r1/sensor/", custody["cal_windows_receipt_metadata_pooled"], capture_inventory),
        ("acquisition/native-return.zip", "sensor/", ["cedar"], capture_gate["members_sha256"])
    ):
        with ZipFile(io.BytesIO(checked(archive_name))) as z:
            names = z.namelist()
            assert len(set(names)) == len(names)
            for tag in tags:
                name = "k0001" if tag == "cedar" else tag
                folder = prefix + name + "/"
                artifacts = {}
                keys = {}
                raw_by_name = {}
                for path in sorted(n for n in names if n.startswith(folder) and not n.endswith("/")):
                    raw = z.read(path)
                    digest = sha(raw)
                    bound = inventory[path]
                    assert digest == (bound["sha256"] if isinstance(bound, dict) else bound)
                    leaf = path[len(folder):]
                    artifacts[leaf] = digest
                    if leaf.endswith(".json"):
                        parsed = json.loads(raw)
                        keys[leaf] = sorted(parsed) if isinstance(parsed, dict) else ["array"]
                    raw_by_name[leaf] = raw
                receipt = json.loads(raw_by_name["receipt.json"])
                assert receipt["verified"] and receipt["tag"] == name
                if tag != "cedar":
                    assert receipt["split"] == "cal"
                for n, h in receipt["artifacts"].items():
                    assert artifacts[n] == h
                triplet = [artifacts[n] for n in ITEMS]
                if tag != "cedar":
                    assert triplet == custody["cal_windows_receipt_metadata_pooled"][tag]
                meta = json.loads(raw_by_name["metadata.json"])
                native = json.loads(raw_by_name["native.json"])
                assert native["text"] == meta["raw"] and native["token_ids"] == meta["token_ids"]
                doc = meta["raw"].encode()
                pooled = raw_by_name["pooled.f32"]
                assert len(pooled) == len(meta["spans"]) * 5120
                spans = []
                for i, s in enumerate(meta["spans"]):
                    assert s["index"] == i
                    start, end = s["byte_range"]
                    first, last = s["char_range"]
                    observed = doc[start:end]
                    assert 0 <= start <= end <= len(doc) and meta["raw"][first:last].encode() == observed
                    canonical = online.Span(i,s["page"],s["kind"],s["block_kind"],s["text"],
                                            tuple(online.clean(t if isinstance(t,str) else t["text"]) for t in s["cells"]),tuple(s["bbox999"]))
                    feature = pooled[5120*i:5120*(i+1)]
                    assert all(math.isfinite(v[0]) for v in struct.iter_unpack("<f",feature))
                    spans.append(dict(canonical=canonical, observed=observed.decode(), byte_range=[start,end],
                                      sha256=sha(observed), projected=feature[:512], feature_sha256=sha(feature)))
                physical[tag] = dict(spans=spans, triplet=triplet, raw_sha256=sha(doc))
                audit.append(dict(tag=tag, archive=archive_name, prefix=folder, members=artifacts, json_keys=keys,
                                  n_emitted_ids=len(meta["token_ids"]), n_spans=len(spans), raw_sha256=sha(doc),
                                  model_revision=receipt["model_revision"], source_layer=json.loads(raw_by_name["capture.json"])["capture_layer"]))
    routes = []
    original = json.loads(checked("fit/cal-transport.json"))["pairs"]
    source_routes = {m["binder"]:m for p in original for m in p["twins"]}
    for task in ("A","B"):
        for pid,p in custody[task].items():
            for bid,m in p["members"].items():
                if task == "A":
                    tags = [w["capture"] for w in m["windows"]]
                    for tag,w in zip(tags,m["windows"],strict=True):
                        assert physical[tag]["triplet"] == w["hashes"]
                    keys = [w["rgb_key"] for w in m["windows"]]
                else:
                    tags = m["windows"]
                    seq = [PureWindowsPath(w) for w in source_routes[bid]["windows"]]
                    assert all(w.parent == SENSOR and re.fullmatch(r"k\d{4}",w.name) for w in seq)
                    assert [w.name for w in seq] == tags and source_routes[bid]["target"] == m["target"]
                    keys = [None] * len(tags)
                assert len(tags)*3 == p["horizon"]
                routes.append(dict(task=task,pair=pid,binder=bid,horizon=p["horizon"],tags=tags,keys=keys))
    assert len(routes) == 24 and len(physical)==30 and len(source_routes)==20
    refs_raw = checked("evidence/steps.jsonl")
    references = [(json.loads(line),sha(line)) for line in refs_raw.splitlines()]
    assert len(references)==224
    return physical,routes,audit,references,custody


def labels(custody):
    records = json.loads(gzip.decompress(blob(BASE+":"+TERMINALS,"4c05cace33f6cb8efb97441d6e9e07c685612830d71557454fb467fa572a29e6")))
    data = {r["binder"]:r for r in records if r["model"]=="M2"}
    for r in data.values():
        m=custody[r["task"]][r["pair"]]["members"][r["binder"]]
        assert r["expected"]==m["expected"]
    assert len(data)==24
    return data
