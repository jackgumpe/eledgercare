"""Read only the immutable exposed captures nominated by the WP-0035 receipt."""
import hashlib
import io
import json
from pathlib import PureWindowsPath
import struct
import subprocess
from zipfile import ZipFile

BASE = "7643bb9b26d15c9d435234e9d3a5d11b742dc771"
CUSTODY = BASE + ":docs/coordination/WP-0035/input-custody.json"
CUSTODY_SHA = "216decb4492bb91c46536fb8f473788b4e4aa439563f992e75232da7aa8cccbf"
PARTS = ("receipt.json", "metadata.json", "pooled.f32")


def sha(buf):
    return hashlib.sha256(buf).hexdigest()


def packed(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def blob(ref, digest):
    b = subprocess.check_output(["git", "cat-file", "blob", ref])
    assert sha(b) == digest, ref
    return b


def read_inputs():
    book = json.loads(blob(CUSTODY, CUSTODY_SHA))
    refs = book["references_sha256"]
    used = {CUSTODY: CUSTODY_SHA}

    def load(suffix):
        ref, = [k for k in refs if k.endswith(suffix) and not k.startswith("c000c")]
        used[ref] = refs[ref]
        return blob(ref, refs[ref])

    inv = json.loads(load("/inventory.json"))
    historical = [json.loads(l) for l in load("/steps.jsonl").splitlines()]
    transit = json.loads(load("/cal-transport.json"))
    fixture = json.loads(load("/manifest.json"))
    gate = json.loads(load("/capture-gate.json"))
    assert gate["authenticated"] and gate["eligible_owner_cue"]
    captures, surfaces = {}, {}
    archives = (("cal", load("/primary-001.zip")), ("cedar", load("/native-return.zip")))
    for bank, buf in archives:
        with ZipFile(io.BytesIO(buf)) as z:
            assert len(z.namelist()) == len(set(z.namelist()))
            windows = book["cal_windows_receipt_metadata_pooled"] if bank == "cal" else {"cedar": None}
            for tag, hashes in windows.items():
                p = "runs/cal-features-r1/sensor/" + tag + "/" if bank == "cal" else "sensor/k0001/"
                names = [n[len(p):] for n in z.namelist() if n.startswith(p)]
                parts = {n: z.read(p+n) for n in PARTS}
                if bank == "cedar":
                    hashes = [gate["members_sha256"][p+n] for n in PARTS]
                assert [sha(parts[n]) for n in PARTS] == hashes
                if bank == "cal":
                    assert hashes == [inv["members"][p+n]["sha256"] for n in PARTS]
                receipt = json.loads(parts["receipt.json"])
                assert receipt["verified"] and receipt["artifacts"]["metadata.json"] == hashes[1]
                assert receipt["artifacts"]["pooled.f32"] == hashes[2]
                meta = json.loads(parts["metadata.json"])
                native_bytes = z.read(p + "native.json")
                capt_bytes = z.read(p + "capture.json")
                assert all(sha(b) == receipt["artifacts"][n] for n,b in
                           (("native.json", native_bytes), ("capture.json", capt_bytes)))
                native, capture = json.loads(native_bytes), json.loads(capt_bytes)
                assert meta["raw"] == native["text"] and meta["token_ids"] == native["token_ids"]
                raw, pool = meta["raw"].encode(), parts["pooled.f32"]
                spans = meta["spans"]
                assert len(pool) == 5120 * len(spans)
                data = []
                for i, s in enumerate(spans):
                    lo, hi = s["byte_range"]
                    assert 0 <= lo < hi <= len(raw) and s["index"] == i
                    source = raw[lo:hi]
                    vec = pool[5120*i:5120*(i+1)]
                    data.append(dict(record=s, raw=source.decode(), rawsha=sha(source), feature=vec))
                captures[tag] = dict(spans=data, hashes=hashes)
                fields = {key: sorted(v) for key,v in
                          (("native", native), ("metadata", meta), ("capture", capture), ("receipt", receipt))}
                fields["span"] = sorted(set().union(*(r.keys() for r in spans)))
                surfaces[tag] = dict(members=sorted(names), fields=fields, triplet=hashes,
                                     native_sha=sha(native_bytes), capture_sha=sha(capt_bytes),
                                     pooled_shape=[len(spans),1280], tokens=len(native["token_ids"]))
    assert len(captures) == 30
    routes, labels = [], {}
    cal_route = {b["binder"]:b for p in transit["pairs"] for b in p["twins"]}
    fix = {m["binder"]:m for p in fixture["pairs"] for m in p["members"]}
    for task in ("A", "B"):
        for pid,pair in book[task].items():
            ids = list(pair["members"])
            if task == "B":
                assert any(set(ids) == {b["binder"] for b in r["twins"]} for r in transit["pairs"])
            for bid, card in pair["members"].items():
                if task == "A":
                    tags = [w["capture"] for w in card["windows"]]
                    keys = [w["rgb_key"] for w in card["windows"]]
                    assert all(captures[t]["hashes"] == w["hashes"] for t,w in zip(tags,card["windows"]))
                    assert [w["rgb_key"] for w in fix[bid]["windows"]] == keys
                    target = fix[bid]["target"]
                else:
                    tags = card["windows"]
                    keys = [None] * len(tags)
                    assert tags == [PureWindowsPath(s).name for s in cal_route[bid]["windows"]]
                    target = card["target"]
                    assert target == cal_route[bid]["target"]
                assert 3 * len(tags) == pair["horizon"]
                routes.append(dict(task=task,pair=pid,binder=bid,horizon=pair["horizon"],tags=tags,
                                   keys=keys,target=target))
                labels[bid] = card["expected"]
    assert len(routes) == len(labels) == 24 and len(historical) == 224
    return routes, captures, historical, labels, dict(refs=used, surfaces=surfaces)
