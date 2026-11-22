"""Inspect each physically recorded, warmed WP-0026 development window, including duplicate runs."""
from collections import defaultdict
from io import BytesIO
import json
from pathlib import Path
import struct
import subprocess
import sys
from zipfile import ZipFile

import numpy as np
from PIL import Image

from common import BASE, ROOT, checked_json, git_blob, identity, pinned, sha, triple

GROUPS = {
    "h0": ("h0", 16),
    "train-c1": ("train", 28),
    "train-features": ("train", 11),
    "cal-features": ("cal", 29),
}
MODEL = "0480966938291445591f69f08a13b041c073a96a"
WORKER = "9c02c9fae465dc1d1322a81c23eb3af45bbb0aff"
SENSOR = "1843cdb7b6279b84b539d3ca1ba7bd0affa1f7dd"
W0 = "7c509b3514daf75854b2b719cc7a94d44175c5af9fdcbae8ef4df0c68ec812e7"
LAYER = "native model.model final normalized decoder state, lm_head input, after consuming emitted token"

def signed_manifests():
    plans = {}
    for split in ("h0", "train", "cal"):
        directory = "docs/fixtures/WP-0024/" + ("h0/" if split=="h0" else f"v2/{split}/")
        receipt = json.loads(git_blob(directory+"receipt.json"))
        docs = checked_json(git_blob(directory+"manifest.json"), receipt["manifest_sha256"])
        pairs = checked_json(git_blob(directory+"pairs.json"), receipt["pairs_sha256"])
        owners = {m["binder"]:p["pair"] for p in pairs["pairs"] for m in p["members"]}
        sources = {b["binder"]:b["windows"] for b in docs["binders"]}
        uses = defaultdict(list)
        for binder, windows in sources.items():
            for w in windows:
                uses[triple(w["pages"])].append(dict(binder=binder, pair=owners[binder], window=w["window"]))
        cross = checked_json(git_blob(directory+"cross-pair.json"), receipt["cross_pair_sha256"])["groups"]
        for k, group in cross.items():
            assert sorted((i["pair"],i["binder"],i["window"]) for i in uses[k]) == sorted((i["pair"],i["binder"],i["window"]) for i in group)
        plans[split] = dict(docs=sources, uses=uses, receipt=receipt)
    return plans

def verify_png(z, page, cache):
    key = (page["sha256"],page["rgb_sha256"])
    if key in cache:
        return
    png = pinned(z.read("inputs/"+key[0]+".png"), key[0])
    with Image.open(BytesIO(png)) as im:
        assert im.size == (2550,3300) and im.mode == "RGB" and sha(im.tobytes()) == key[1]
    cache.add(key)

def capture(z, prefix, plan, call, receipt, run, archive_path, reconstructed):
    artifacts = {name:pinned(z.read(prefix+name), digest) for name,digest in receipt["artifacts"].items()}
    native, meta = [json.loads(artifacts[n+".json"]) for n in ("native","metadata")]
    ids, terminal = native["token_ids"], native["terminal_observation"]
    assert ids == meta["token_ids"] and native["prompt_token_ids"] == meta["prompt_token_ids"] == plan["prompt_token_ids"]
    assert native["text"] == meta["raw"] and terminal == meta["terminal_observation"]
    assert native["prompt"] == plan["prompt"] and native["eos_observed"] and meta["eos_observed"]
    assert native["stop_cause"] == meta["stop_cause"] == "eos" and native["finish_reason"] == "stop"
    assert native["expected_pages"] == native["num_pages_out"] == 3
    assert terminal["step"] == len(ids) and terminal["prompt_length"] == 827
    assert ids.count(128827) == 3 and ids[0] == 128827 and 1 not in ids
    assert terminal["nxt"] == meta["eos_id"] == native["eos_id"] == 1
    assert terminal["guard"] == {"marker_cum":3, "scanned":len(ids), "page_len":ids[::-1].index(128827)}
    packed = struct.pack(f"<{len(ids)+1}I", *ids, 1)
    assert packed == artifacts["through-eos.u32le"] and sha(packed) == receipt["through_eos_sha256"]
    assert len(ids)+1 == receipt["through_eos_length"]
    for field, value in reconstructed(native["text"], ids).items():
        assert meta[field] == value
    feature = None
    if call["hooked"]:
        pool = artifacts["pooled.f32"]
        cap = json.loads(artifacts["capture.json"])
        assert cap["pool_shape"] == [len(meta["spans"]),1280] and cap["hidden_shape"] == [len(ids),1280]
        assert cap["position_start"] == 827 and cap["position_stop_exclusive"] == 827+len(ids)
        assert cap["native_dtype"] == "bfloat16" and cap["pool_dtype"] == "little-endian float32" and cap["capture_layer"] == LAYER
        assert sha(pool) == cap["pooled_sha256"] and len(pool) == len(meta["spans"])*1280*4 and np.isfinite(np.frombuffer(pool,dtype="<f4")).all()
        assert cap["consumed_id_sha256"] == sha((json.dumps(ids,separators=(",",":"))+"\n").encode())
        feature = dict(run=run, tag=call["tag"], archive=archive_path, archive_revision=BASE, prefix=prefix,
                       receipt_sha256=sha(z.read(prefix+"receipt.json")), metadata_sha256=sha(artifacts["metadata.json"]),
                       pooled_sha256=sha(pool), through_eos_sha256=sha(packed), capture_sha256=sha(artifacts["capture.json"]),
                       native_sha256=sha(artifacts["native.json"]), pooled_shape=cap["pool_shape"])
    else:
        assert "pooled.f32" not in artifacts and "capture.json" not in artifacts
    return feature

def inspect_order(z, archive_path, order, release, source, split, w0, cache, reconstructed):
    run = order["run"]
    plan_bytes = z.read("binding/"+Path(order["plan"]).name)
    plan = checked_json(plan_bytes, order["plan_sha256"])
    plan_sha = sha(plan_bytes)
    assert plan["candidate"] == release["review_worktree_head"] == WORKER
    assert plan["model_revision"] == MODEL and plan["historical_sensor_revision"] == SENSOR
    assert plan["packet"] == "WP-0026" and plan["split"] == split and plan["target_dtype"] == "torch.bfloat16"
    assert plan["runner_sha256"] == sha(git_blob("docs/research/WP-0026/worker.py",WORKER))
    tree = subprocess.check_output(["git","rev-parse",SENSOR+":docs/research/WP-0024/sensor"],cwd=ROOT,text=True).strip()
    assert tree == plan["sensor_tree"]
    sensor = "runs/"+run+"/sensor/"
    record = lambda name: json.loads(z.read(sensor+name+".json"))
    bind, cold, warm, outcome = [record(k) for k in ("binding","cold","warmup","outcome")]
    relations = {k:bind[k] for k in ("candidate","model_revision","model_load_id","pid","process_id","lease","plan_sha256","split")}
    assert all(all(r[k] == v for k,v in relations.items()) for r in (cold,warm,outcome))
    assert bind["candidate"] == WORKER and bind["sensor_candidate"] == SENSOR and bind["model_revision"] == MODEL
    assert bind["plan_sha256"] == plan_sha and cold["loads"] == 1
    assert cold["model"]["manifest_sha256"] == plan["model_manifest_sha256"]
    assert cold["model"]["target_dtype"] == plan["target_dtype"] and cold["model"]["model_revision"] == MODEL
    assert cold["model"]["tokenizer_sha256"] == plan["tokenizer_sha256"]
    assert warm["fixture_sha256"] == bind["warmup_fixture_sha256"] == plan["warmup"]["fixture_sha256"] == W0
    assert warm["tag"] == "W0" and warm["mode"] == "S" and warm["ordinal"] == 1 and warm["scored"] is False
    assert warm["success"] and warm["eos_observed"] and warm["terminal_observation"]["nxt"] == 1
    assert warm["prompt"] == warm["observed_prompt"] == plan["prompt"] == bind["prompt"]
    assert warm["prompt_token_ids"] == warm["observed_prompt_token_ids"] == plan["prompt_token_ids"] == bind["prompt_token_ids"]
    assert warm["request"] == plan["requests"][0] == plan["warmup"]["request"]
    assert warm["request"]["sha256"] == w0["pdf"]["sha256"]
    assert warm["pages"] == plan["warmup"]["pages"] and identity(warm["pages"]) == identity(w0["pages"])
    assert cold["ready_utc_ns"] <= warm["start_utc_ns"] < warm["end_utc_ns"]
    for p in warm["pages"]:
        verify_png(z,p,cache)
    pinned(z.read("inputs/"+w0["pdf"]["sha256"]+".pdf"), w0["pdf"]["sha256"])
    requests = {Path(q["pdf"]).stem:q for q in plan["requests"][1:]}
    for binder, req in requests.items():
        assert req["sha256"] == source["receipt"]["source_pdfs"][binder]
        pinned(z.read("inputs/"+req["sha256"]+".pdf"), req["sha256"])
        assert req["rgb_sha256"] == [p["rgb_sha256"] for w in source["docs"][binder] for p in w["pages"]]
    tags = [c["tag"] for c in plan["calls"]]
    assert len(tags) == len(set(tags)) and tags == outcome["started_tags"] == outcome["verified_tags"] == bind["order"]
    assert outcome["status"] == "complete" and outcome["warmup_calls"] == 1 and outcome["total_inference_calls"] == 1+len(tags)
    assert set(tags) == {n[len(sensor):].split("/")[0] for n in z.namelist() if n.startswith(sensor) and n.endswith("/receipt.json")}
    warm_sha = sha(z.read(sensor+"warmup.json"))
    rows = []
    for ordinal, call in enumerate(plan["calls"],2):
        tag, window, binder = call["tag"], call["window"], call["binder"]
        pre = sensor+tag+"/"
        r, begin = record(tag+"/receipt"), record(tag+"-begin")
        for rec in (r,begin):
            assert all(rec[k]==v for k,v in relations.items())
            assert rec["sensor_candidate"] == SENSOR and rec["warmup_fixture_sha256"] == W0 and rec["warmup_sha256"] == warm_sha
            assert rec["pages"] == call["pages"] and rec["mode"] == call["mode"] and rec["ordinal"] == ordinal
            assert rec["binder"] == binder and rec["window"] == window
        assert warm["end_utc_ns"] <= begin["utc_ns"] < r["utc_ns"] and r["verified"] is True
        assert call["hooked"] == (r["mode"]=="H") and r["tag"] == tag and r["phase"] == plan["phase"]
        assert call["pages"] == source["docs"][binder][window-1]["pages"]
        assert requests[binder]["rgb_sha256"][3*(window-1):3*window] == [p["rgb_sha256"] for p in r["pages"]]
        assert not set(p["rgb_sha256"] for p in r["pages"]).intersection(p["rgb_sha256"] for p in w0["pages"])
        for p in r["pages"]:
            verify_png(z,p,cache)
        feature = capture(z,pre,plan,call,r,run,archive_path,reconstructed)
        rows.append(dict(run=run, tag=tag, historical_binder=binder, historical_window=window, split=split,
                         mode=r["mode"], ordered_png_rgb=identity(r["pages"]), rgb_key=triple(r["pages"]),
                         receipt_sha256=sha(z.read(pre+"receipt.json")), through_eos_sha256=r["through_eos_sha256"],
                         through_eos_length=r["through_eos_length"], feature=feature))
    binding = dict(run=run, archive=archive_path, split=split, plan_sha256=plan_sha,
                   historical_sensor_revision=SENSOR,sensor_tree=tree,worker_revision=WORKER,worker_sha256=plan["runner_sha256"],
                   model_revision=MODEL,model_manifest_sha256=plan["model_manifest_sha256"],module_sha256=plan["module_sha256"],
                   tokenizer_sha256=plan["tokenizer_sha256"],warmup_fixture_sha256=W0,warmup_sha256=warm_sha,
                   warmup_through_eos_sha256=warm["through_eos_sha256"],warmup_excluded=True,**{"load_id":bind["model_load_id"]})
    return rows,binding

def inventory():
    sys.path.insert(0,str(ROOT/"docs/reviews/WP-0024"))
    # Load the tokenizer only after its frozen bytes have been checked.
    from stage_a import TOKENIZER
    pinned(TOKENIZER.read_bytes(),"c55c165e32c5a67830362a53e1f548c8930dcc8469efa30ff3252a982799c589")
    from span_audit import reconstruct
    sources = signed_manifests()
    w0 = checked_json(git_blob("docs/fixtures/WP-0026/w0/receipt.json"), W0)
    captures, orders, primary = [],[],[]
    for group, (split, count) in GROUPS.items():
        root = "docs/reviews/WP-0026/"+group+"-primary/"
        inv_raw = git_blob(root+"inventory.json")
        inv = json.loads(inv_raw)
        assert inv["candidate"] == WORKER and not inv["input_discrepancies"] and len(inv["parts"]) == 1
        archive = root+"primary-001.zip"
        archive_pin = inv["parts"]["primary-001.zip"]["sha256"]
        raw = pinned((ROOT/archive).read_bytes(), archive_pin)
        with ZipFile(BytesIO(raw)) as z:
            assert len(z.namelist()) == len(set(z.namelist())) and set(z.namelist()) == set(inv["members"])
            release = checked_json(z.read("binding/"+inv["release"]+"-release.json"), inv["release_sha256"])
            assert len(release["orders"]) == len(inv["orders"])
            actual, cache = [], set()
            for order in release["orders"]:
                rows, binding = inspect_order(z,archive,order,release,sources[split],split,w0,cache,reconstruct)
                actual.extend(rows)
                orders.append(binding)
            assert len(actual) == count
        captures.extend(actual)
        primary.append(dict(archive=archive,sha256=archive_pin,inventory=root+"inventory.json",inventory_sha256=sha(inv_raw),
                            release_sha256=inv["release_sha256"],receipts=count,recorded=sum(x["mode"]=="H" for x in actual)))
    coverage = {}
    for split, source in sources.items():
        keys = {r["rgb_key"] for r in captures if r["mode"]=="H" and r["split"]==split}
        assert keys == set(source["uses"])
        coverage[split] = dict(unique_whole_windows=len(keys),logical_appearances=sum(map(len,source["uses"].values())))
    return dict(archive_revision=BASE, model_revision=MODEL, capture_layer=LAYER, archives=primary,
                orders=orders, logical_coverage=coverage, physical_captures=captures), sources
