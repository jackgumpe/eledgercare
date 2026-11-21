"""Independent readback of the first three physical pages and all eight counterbalanced reads.

Run from the reviewer worktree using the read-only Q0 Python with -I -B.
Historical snapshot and source alignment are the WP-0024 independent review routines.
"""
import argparse
from contextlib import closing
from difflib import SequenceMatcher
from hashlib import sha256
from itertools import combinations, zip_longest
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import numpy as np
import pypdfium2 as pdfium
from PIL import Image

REPO = Path(__file__).resolve().parents[3]
PREV = REPO / "docs/reviews/WP-0024"
sys.path.insert(0, str(PREV))
from h0_audit import align
from span_audit import snapshot, T, TOKENIZER
from stage_a import differences

RESERVE = "842f587e8d223360aaa6058518d999964d304278"
SENSOR = "1843cdb7b6279b84b539d3ca1ba7bd0affa1f7dd"
PLAN_PIN = "0bf358c54fc97f32ca213d9a1dd10cfb2838f42f7c5dcded1625c0cca1fd2f89"
HISTORY_PIN = "37670af4116f543e2d0104b5d3599d88f2e2d06fc092418ee1cf839769430fc6"
DATA = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0025/review")
TAGS = [f"P{p}J{j}{mode}" for p,order in enumerate(("SHHS","HSSH"),1) for j,mode in enumerate(order,1)]
OLD = ["b01w01S","b01w01H"]


def sha(raw):
    return sha256(raw).hexdigest()


def blob(rev, path):
    return subprocess.check_output(["git","-C",str(REPO),"show",rev+":"+path])


def load(p):
    return json.loads(p.read_bytes())


def packed(value):
    return (json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(",",":"))+"\n").encode()


def ids_bytes(ids):
    return struct.pack("<"+"I"*len(ids), *ids)


def inputs():
    archive = PREV / "h0-r1.zip"
    assert sha(archive.read_bytes()) == HISTORY_PIN
    with ZipFile(archive) as z:
        raw_plan = z.read("binding/h0-r1-plan.json")
        assert sha(raw_plan) == PLAN_PIN
        assert raw_plan == blob(RESERVE,"docs/coordination/WP-0024/h0-r1-plan.json")
        plan = json.loads(raw_plan)
        assert plan["candidate"] == SENSOR
        release = json.loads(z.read("binding/h0-r1-release.json"))
        for path,pin in release["source_files"].items():
            assert sha(blob(SENSOR,path)) == pin and blob(SENSOR,path) == blob(RESERVE,path)
        pages = plan["calls"][0]["pages"]
        b = plan["calls"][0]["binder"]
        assert b=="34054347f091c087a39efe17" and plan["calls"][0]["tag"]==OLD[0]
        assert next(c["pages"] for c in plan["calls"] if c["tag"]==OLD[1]) == pages
        pdf = Path(plan["requests"][0]["pdf"])
        assert pdf.stem == b and sha(pdf.read_bytes()) == plan["requests"][0]["sha256"]
        assert [e["rgb_sha256"] for e in pages] == plan["requests"][0]["rgb_sha256"][:3]
        with pdfium.PdfDocument(pdf) as doc:
            for i,entry in enumerate(pages):
                image=Path(entry["image"])
                assert image.parent==Path(plan["raster_root"]) and sha(image.read_bytes())==entry["sha256"]
                with Image.open(image) as im:
                    assert im.size==(2550,3300) and sha(im.convert("RGB").tobytes())==entry["rgb_sha256"]
                with closing(doc[i]) as pg, closing(pg.render(scale=math.nextafter(300/72,0))) as bmp:
                    assert pg.get_size()==(612,792)
                    assert sha(bmp.to_pil().convert("RGB").tobytes()) == entry["rgb_sha256"]
        cold=json.loads(z.read("run/sensor/cold.json"))["model"]
        assert cold["tokenizer_sha256"]==sha(TOKENIZER.read_bytes())
        assert cold["model_revision"]==plan["model_revision"]
        assert sha((TOKENIZER.parent/"modeling_unlimitedocr.py").read_bytes()) == plan["module_sha256"]
        raw=blob(SENSOR,"docs/fixtures/WP-0024/h0/source-witness.json")
        assert sha(raw)==release["source_files"]["docs/fixtures/WP-0024/h0/source-witness.json"]
        evidence=json.loads(raw)
        assert evidence["documents"][b]==sha(pdf.read_bytes())
        witnesses=[i for i in evidence["witnesses"] if i["binder"]==b and i["window"]==1]
        assert len(witnesses)==4
        source={"ordered_physical_pages":[1,2,3],"pdf_sha256":sha(pdf.read_bytes()),"png_and_pdf_rgb_verified":pages,
                "history_plan_sha256":PLAN_PIN,"history_archive_sha256":HISTORY_PIN,"sensor":SENSOR,
                "history_source_files_verified":release["source_files"],"cold_identity":cold,
                "pdf":str(pdf),"witness_sha256":sha(raw)}
        return source,witnesses


def sample(directory, pdf, witnesses, historical=False, expected=None, plan=None, digest=None):
    receipt = snapshot(directory)
    native,meta,duration=[load(directory/n) for n in ("native.json","metadata.json","duration.json")]
    emitted = native["token_ids"]
    eos = native["terminal_observation"]["nxt"]
    assert eos==1 and native["finish_reason"]=="stop"
    assert native["expected_pages"]==native["num_pages_out"]==3
    terminal=native["terminal_observation"]
    assert terminal["guard"]["marker_cum"]==3 and terminal["guard"]["scanned"]==len(emitted)
    assert terminal["max_length"]==131072 and terminal["max_new_tokens"]==24000
    prompt = native["prompt_token_ids"]
    assert sha(packed(prompt))==duration["prompt_sha256"] and sha(packed(emitted))==duration["token_sha256"]
    assert sha((directory/"metadata.json").read_bytes())==duration["metadata_sha256"]
    if expected is not None:
        assert prompt == expected["prompt_token_ids"] and native["prompt"]==expected["prompt"]
    stream=emitted+[eos]
    h=directory.name.endswith("H")
    extras=["token_hidden.bf16","pooled.f32","observed-positions.json","capture.json"]
    assert all((directory/item).is_file()==h for item in extras)
    assert (duration["capture"] is not None)==h
    hidden=pool=None
    if h:
        cap=load(directory/"capture.json")
        assert cap==duration["capture"] and cap["consumed_id_sha256"]==sha(packed(emitted))
        assert cap["position_start"]==len(prompt) and cap["position_stop_exclusive"]==len(prompt)+len(emitted)
        assert cap["hidden_shape"]==[len(emitted),1280] and cap["pool_shape"]==[len(meta["spans"]),1280]
        bits=np.fromfile(directory/"token_hidden.bf16",dtype="<u2").astype("<u4")
        hidden=np.left_shift(bits,16).view("<f4").reshape(-1,1280)
        pool=np.fromfile(directory/"pooled.f32",dtype="<f4").reshape(-1,1280)
    if not historical:
        receipt_file=load(directory/"receipt.json")
        tag=directory.name
        order, = [c for c in plan["calls"] if c["tag"]==tag]
        identity=load(directory.parent/"binding.json")
        cold=load(directory.parent/"cold.json")
        begin=load(directory.parent/(tag+"-begin.json"))
        for record in [identity,cold,begin,receipt_file]:
            assert record["packet"]=="WP-0025" and record["candidate"]==plan["candidate"]
            assert record["plan_sha256"]==digest and record["process_id"]==tag[:2]
            assert record["process_ordinal"]==int(tag[1]) and record["pid"]==identity["pid"]
            assert record["process_create_filetime"]==identity["process_create_filetime"]
        assert identity["prompt_sha256"]==plan["prompt_sha256"]==duration["prompt_sha256"]
        assert identity["settings"]==plan["settings"] and identity["pages"]==order["pages"]
        assert all(plan["environment"][k]==v for k,v in identity["environment"].items())
        assert identity["order"]==[c["tag"] for c in plan["calls"]]
        for record in [begin,receipt_file]:
            assert record["tag"]==tag and record["ordinal"]==int(tag[3]) and record["mode"]==tag[-1]
        assert cold["loads"]==1 and cold["model"]["target_dtype"]=="torch.bfloat16"
        assert cold["model"]["model_revision"]==plan["model_revision"]
        assert cold["model"]["tokenizer_sha256"]==plan["tokenizer_sha256"]
        assert cold["start_utc_ns"]<=cold["ready_utc_ns"]<=begin["utc_ns"]<=duration["start_utc_ns"]
        assert duration["end_inference_utc_ns"]<=duration["end_capture_utc_ns"]<=receipt_file["utc_ns"]
        assert receipt_file["verified"] is True and receipt_file["through_eos_length"]==len(stream)
        hashes={p.name:sha(p.read_bytes()) for p in directory.iterdir() if p.name!="receipt.json"}
        assert hashes==receipt_file["artifacts"]
        assert (directory/"through-eos.u32le").read_bytes()==ids_bytes(stream)
        assert hashes["through-eos.u32le"]==receipt_file["through_eos_sha256"]==sha(ids_bytes(stream))
        receipt["observation"]={"pid":identity["pid"],"creation_filetime":identity["process_create_filetime"],
            "mode":tag[-1],"ordinal":int(tag[3]),"start_ns":duration["start_utc_ns"],
            "receipt_ns":receipt_file["utc_ns"],"cold_ready_ns":cold["ready_utc_ns"],
            "inference_s":duration["wall_inference_ns"]/1e9,"window_s":duration["complete_window_wall_ns"]/1e9}
    matches={}
    for w in witnesses:
        row=align(w,meta,pdf)
        matches[w["kind"]]={"unique":row["unique_literal_and_geometry"],
            "qualified":[r for r in row["candidate_rows"] if r["all_glyph_centers_inside"] and r["word_sequence_match"]],
            "expected_pdf_text":row["expected_pdf_text"]}
    receipt.update(processed_terminal=terminal,through_eos_le_u32_sha256=sha(ids_bytes(stream)),
        prompt_sha256=duration["prompt_sha256"],prompt_length=len(prompt),witnesses=matches)
    return dict(receipt=receipt,ids=stream,native=native,meta=meta,hidden=hidden,pool=pool)


def features(box):
    import torch
    b=torch.tensor(box,dtype=torch.float32,device="cpu")/999
    phase=b[:,None]*torch.tensor([1,2,4,8],dtype=torch.float32)*(2*math.pi)
    return torch.cat((phase.sin().flatten(),phase.cos().flatten())).numpy()


def fdelta(a,b):
    return float(np.max(np.abs(a-b)))


def compare(left,right):
    a,b=left["ids"],right["ids"]
    unequal=next((i for i,(x,y) in enumerate(zip_longest(a,b)) if x!=y),None)
    ops=[]
    if unequal is not None:
        for op,i,j,k,l in SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
            if op!="equal":
                ops.append(dict(op=op,at_left=[i,j],at_right=[k,l],ids_left=a[i:j],ids_right=b[k:l],
                    text_left=T.decode(a[i:j],skip_special_tokens=False),text_right=T.decode(b[k:l],skip_special_tokens=False)))
    am,bm=left["meta"],right["meta"]
    span_changes=[]
    for i,(x,y) in enumerate(zip_longest(am["spans"],bm["spans"])):
        if x is None or y is None:
            span_changes.append(dict(i=i,left=x,right=y))
            continue
        fields=differences({k:x[k] for k in ("page","kind","text","cells","bbox999")},
                           {k:y[k] for k in ("page","kind","text","cells","bbox999")})
        if fields:
            span_changes.append(dict(i=i,changes=fields,geometry_max_abs_fp32=fdelta(features(x["bbox999"]),features(y["bbox999"]))))
    return dict(equal=unequal is None,first_divergence=unequal,prefix_length=unequal,
        edits=ops,page_differences=differences(am["pages"],bm["pages"]),span_differences=span_changes)


def hh(left,right):
    a,b=left["ids"][:-1],right["ids"][:-1]
    pa,pb=(v["native"]["prompt_token_ids"] for v in (left,right))
    assert pa==pb
    def memberships(s):
        result=[[] for _ in s["ids"][:-1]]
        for span in s["meta"]["spans"]:
            sig=(span["page"],span["kind"],span["index"],span["text"],tuple(span["token_indices"]))
            for i in span["token_indices"]:
                result[i].append(sig)
        return result
    ma,mb=memberships(left),memberships(right)
    ai={i for i in range(min(len(a),len(b))) if a[i]==b[i] and ma[i]==mb[i]}
    # Align post-consumption rows only at matching IDs and absolute positions. Prefix
    # equality distinguishes same lexical position downstream from an identical history.
    div=next((i for i,(x,y) in enumerate(zip_longest(a,b)) if x!=y),None)
    rows=[dict(i=i,prefix_equal=div is None or i<div,
               byte_equal=left["hidden"][i].tobytes()==right["hidden"][i].tobytes(),
               max_abs_fp32=fdelta(left["hidden"][i],right["hidden"][i])) for i in sorted(ai)]
    spans=[]
    def signature(s):
        return (s["page"],s["kind"],s["block_kind"],s["text"],tuple(s["cells"]),tuple(s["token_indices"]))
    for s in left["meta"]["spans"]:
        matches=[v for v in right["meta"]["spans"] if signature(v)==signature(s)]
        if len(matches)!=1 or not set(s["token_indices"])<=ai:
            continue
        v,=matches
        i,j=s["index"],v["index"]
        x,y=left["pool"][i],right["pool"][j]
        ga,gb=features(s["bbox999"]),features(v["bbox999"])
        gdiff=fdelta(ga,gb)
        spans.append(dict(left=i,right=j,byte_equal=x.tobytes()==y.tobytes(),max_abs_fp32=fdelta(x,y),
            geometry_max_abs_fp32=gdiff,probe_vector_max_abs_fp32=max(fdelta(x,y),gdiff),
            prefix_equal=div is None or max(s["token_indices"])<div))
    return dict(aligned_rows=len(rows),aligned_spans=len(spans),
        first_different_row=next((r["i"] for r in rows if not r["byte_equal"]),None),
        first_different_pool=next((r["left"] for r in spans if not r["byte_equal"]),None),
        rows_max_abs_fp32=max((r["max_abs_fp32"] for r in rows),default=None),
        pools_max_abs_fp32=max((r["max_abs_fp32"] for r in spans),default=None),
        rows=rows,spans=spans)


def run(live_root=None, release_path=None, release_sha=None):
    sources,witnesses=inputs()
    pdf=Path(sources["pdf"])
    samples={}
    failures={}
    DATA.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(dir=DATA) as scratch, ZipFile(PREV/"h0-r1.zip") as hist:
        for tag in OLD:
            folder=Path(scratch)/tag
            folder.mkdir()
            prefix="run/sensor/"+tag+"/"
            for item in hist.namelist():
                if item.startswith(prefix):
                    (folder/Path(item).name).write_bytes(hist.read(item))
            samples[tag]=sample(folder,pdf,witnesses,historical=True,expected=None if tag==OLD[0] else samples[OLD[0]]["native"])
        original=compare(samples[OLD[0]],samples[OLD[1]])
        assert [e["at_left"][0] for e in original["edits"]]==[13,77,100,146]
        assert [e["text_left"] for e in original["edits"]]==["399","388","388","202"]
        assert [e["text_right"] for e in original["edits"]]==["395","387","387","201"]
        result=dict(sources=sources,original=original,historical_receipts={k:v["receipt"] for k,v in samples.items()})
        if live_root is None:
            return result
        release_raw=release_path.read_bytes()
        assert sha(release_raw)==release_sha
        rel=json.loads(release_raw)
        assert rel["name"]=="window-repeat-r1" and rel["operator"]=="eld-repeat-reviewer"
        orders={o["run"]:o for o in rel["orders"]}
        assert list(orders)==["p1","p2"]
        for t in TAGS:
            try:
                order=orders[t[:2].lower()]
                raw=Path(order["plan"]).read_bytes()
                assert sha(raw)==order["plan_sha256"]
                plan=json.loads(raw)
                assert plan["candidate"]==rel["review_worktree_head"] and plan["process_id"]==t[:2]
                assert plan["calls"][int(t[3])-1]["pages"]==sources["png_and_pdf_rgb_verified"]
                samples[t]=sample(live_root/t[:2].lower()/"sensor"/t,pdf,witnesses,expected=samples[OLD[0]]["native"],
                                  plan=plan,digest=order["plan_sha256"])
            except Exception as exc:
                failures[t]=f"{type(exc).__name__}: {exc}"
    pairs={}
    features_hh={}
    for l,r in [*combinations(TAGS,2),*((l,r) for l in TAGS for r in OLD)]:
        if l not in samples or r not in samples:
            pairs[l+"/"+r]=None
            continue
        pair=compare(samples[l],samples[r])
        if l[-1]!=r[-1]:
            s,h=(l,r) if l.endswith("S") else (r,l)
            oriented=compare(samples[s],samples[h])
            pair["historic_four_edits_with_orientation"]=oriented["edits"]==original["edits"]
        pairs[l+"/"+r]=pair
        if l[-1]==r[-1]=="H":
            features_hh[l+"/"+r]=hh(samples[l],samples[r])
    matrix={l:{r:(samples[l]["ids"]==samples[r]["ids"] if l in samples and r in samples else None)
               for r in TAGS} for l in TAGS}
    def distinct(mode):
        return len({tuple(samples[t]["ids"]) for t in TAGS if t in samples and t.endswith(mode)})
    verdict=("incomplete" if failures else "baseline variation observed" if distinct("S")>1 else
             "variation observed with capture enabled" if distinct("H")>1 else
             "mode-associated difference under both orders" if not all(matrix[TAGS[0]].values()) else "mismatch not reproduced")
    result.update(samples={t:samples[t]["receipt"] for t in TAGS if t in samples},failures=failures,agreement=matrix,
                  comparisons=pairs,hh=features_hh,verdict=verdict,
                  stock_hidden="unobserved for every S slot",pair_counts={"SS":6,"HH":6,"SH":16})
    return result


if __name__=="__main__":
    assert sys.flags.isolated and sys.dont_write_bytecode
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result",type=Path)
    parser.add_argument("--runs",type=Path)
    parser.add_argument("--release",type=Path)
    parser.add_argument("--release-sha")
    args=parser.parse_args()
    args.result.write_text(json.dumps(run(args.runs,args.release,args.release_sha),indent=2,ensure_ascii=True,allow_nan=False)+"\n",encoding="utf8")

