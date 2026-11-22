"""Rebuild the exact old reader's source map and average the original BF16 positions."""
import io
import json
import struct
import sys
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit import BASE, KEY, PROPOSAL, Q0, ROOT, SENSOR, WORKER, ZIP, blob, canon, initialize, pin, save, sha

def authenticate(rev):
    import numpy as np
    from PIL import Image
    from tokenizers import Tokenizer
    prop = json.loads(pin(PROPOSAL,"docs/coordination/WP-0028/acquisition-scope.json"))
    ref = json.loads(pin(WORKER,"docs/coordination/WP-0025/p1-plan.json"))
    w0 = json.loads(pin(BASE,"docs/fixtures/WP-0026/w0/receipt.json"))
    for path in ("capture.py","spans.py","run_sensor.py"):
        pin(SENSOR,"docs/research/WP-0024/sensor/"+path)
    pin(WORKER,"docs/research/WP-0026/worker.py")
    pin(SENSOR,"docs/research/WP-0023/trial/stock.py")
    sys.path[:0]=[str(ROOT/p) for p in ("docs/research/WP-0024/sensor","docs/research/WP-0024/probe")]
    import spans
    import online
    spans.verify_parsers()
    buf=(Q0/"models/Unlimited_OCR_2_04809669/tokenizer.json").read_bytes()
    assert sha(buf)==ref["tokenizer_sha256"]
    tokenizer=Tokenizer.from_buffer(buf)
    added={r["id"]:r["content"] for r in json.loads(buf)["added_tokens"]}
    packed=blob(rev,ZIP)
    with ZipFile(io.BytesIO(packed)) as z:
        names=z.namelist()
        assert len(names)==len(set(names)) and z.testzip() is None
        members={p:sha(z.read(p)) for p in names}
        def read(p): return json.loads(z.read("sensor/"+p+".json"))
        def sample(p): return z.read("sensor/k0001/"+p)
        warm=read("warmup")
        bind=read("binding")
        cold=read("cold")
        receipt=read("k0001/receipt")
        begin=read("k0001-begin")
        out=read("outcome")
        assert out["status"]=="complete" and out["all_equal"] and out["checks"]==[]
        assert out["started_tags"]==out["verified_tags"]==["k0001"]
        assert (cold["loads"],out["warmup_calls"],out["real_inference_calls"],out["total_inference_calls"])==(1,1,1,2)
        for key in ("candidate","plan_sha256","gpu_uuid","pid","parent_pid","process_create_filetime","model_load_id"):
            assert all(b[key]==bind[key] for b in (warm,cold,receipt,begin,out)), key
        assert bind["model_load_id"]==f"{bind['pid']}-{bind['process_create_filetime']}-1"
        assert cold["model"]["model_revision"]==ref["model_revision"]
        for k,rk in (("target_dtype","target_dtype"),("platform","historical_platform"),("manifest_sha256","model_manifest_sha256"),
                     ("dependency_lock_sha256","environment_lock_sha256"),("tokenizer_sha256","tokenizer_sha256")):
            assert cold["model"][k]==ref[rk]
        assert bind["sensor_candidate"]==receipt["sensor_candidate"]==SENSOR
        assert bind["order"]==["k0001"] and warm["mode"]=="S" and warm["ordinal"]==1
        assert warm["scored"] is False and warm["success"] is True and warm["eos_observed"] is True
        assert warm["observed_prompt"]==ref["prompt"] and warm["observed_prompt_token_ids"]==ref["prompt_token_ids"]
        assert warm["emitted"]==62 and warm["eos_id"]==1 and warm["through_eos_sha256"]=="837b21829d99ee47d583039651628cf6c7f6e796bd71ee8b5490c21d0c3a52d4"
        assert warm["fixture_sha256"]==sha(pin(BASE,"docs/fixtures/WP-0026/w0/receipt.json"))
        assert warm["request"]["sha256"]==w0["pdf"]["sha256"]
        assert cold["ready_utc_ns"]<=warm["start_utc_ns"]<warm["end_utc_ns"]<=begin["utc_ns"]<=receipt["utc_ns"]
        assert receipt["verified"] is True and receipt["mode"]=="H" and receipt["ordinal"]==2
        assert receipt["warmup_sha256"]==members["sensor/warmup.json"]
        assert begin["pages"]==receipt["pages"] and begin["window"]==receipt["window"]==1
        pages=prop["missing"][0]["ordered_pages"]
        rgbs=[p["rgb_sha256"] for p in pages]
        assert sha((json.dumps(rgbs,indent=2)+"\n").encode())==KEY
        def physical(png,expected):
            raw=pin(BASE,png)
            assert sha(raw)==expected["sha256"]
            with Image.open(io.BytesIO(raw)) as im:
                assert im.size==(2550,3300) and sha(im.convert("RGB").tobytes())==expected["rgb_sha256"]
        for original,call in zip(pages,receipt["pages"],strict=True):
            assert (call["sha256"],call["rgb_sha256"])==(original["png_sha256"],original["rgb_sha256"])
            physical("docs/fixtures/WP-0028/rasters/"+call["sha256"]+".png",call)
        for original,call in zip(w0["pages"],warm["pages"],strict=True):
            assert (call["sha256"],call["rgb_sha256"])==(original["sha256"],original["rgb_sha256"])
            physical("docs/fixtures/WP-0026/w0/"+original["image"],call)
        assert not set(rgbs).intersection(p["rgb_sha256"] for p in warm["pages"])
        for name,h in receipt["artifacts"].items():
            assert sha(sample(name))==h
        assert set(receipt["artifacts"])=={"native.json","metadata.json","duration.json","capture.json","token_hidden.bf16",
                                               "pooled.f32","observed-positions.json","through-eos.u32le"}
        nat,meta,cap,dur,obs=(read("k0001/"+k) for k in ("native","metadata","capture","duration","observed-positions"))
        ids=nat["token_ids"]
        assert nat["prompt"]==ref["prompt"] and nat["prompt_token_ids"]==ref["prompt_token_ids"]
        assert nat["stop_cause"]=="eos" and nat["finish_reason"]=="stop" and nat["eos_observed"] is True
        assert all(type(i) is int and i>=0 for i in ids) and 1 not in ids
        assert ids[0]==128827 and ids.count(128827)==3 and nat["num_pages_out"]==nat["expected_pages"]==3
        assert nat["terminal_observation"]=={"nxt":1,"step":len(ids),"prompt_length":827,
            "max_length":ref["settings"]["max_length"],"max_new_tokens":ref["settings"]["max_new_tokens"],
            "guard":{"scanned":len(ids),"marker_cum":3,"page_len":ids[::-1].index(128827)}}
        assert nat["eos_id"]==1 and struct.pack("<"+"I"*(len(ids)+1),*ids,1)==sample("through-eos.u32le")
        assert len(ids)<ref["settings"]["max_new_tokens"] and len(ids)+827<ref["settings"]["max_length"]
        raw=tokenizer.decode(ids,skip_special_tokens=False)
        assert raw==nat["text"]==meta["raw"] and raw.startswith("<PAGE>") and raw.count("<PAGE>")==3
        for k in ("token_ids","prompt_token_ids","eos_id","stop_cause","eos_observed","expected_pages","num_pages_out","terminal_observation"):
            assert meta[k]==nat[k],k
        for k,value in spans.map_window(raw,ids,lambda seq:[tokenizer.id_to_token(i) for i in seq],added).items():
            assert value==meta[k], k
        assert obs=={"ids":ids,"absolute_positions":list(range(827,827+len(ids)))}
        assert dur["capture"]==cap and cap["native_dtype"]=="bfloat16" and cap["pool_dtype"]=="little-endian float32"
        assert cap["capture_layer"]=="native model.model final normalized decoder state, lm_head input, after consuming emitted token"
        assert [cap["position_start"],cap["position_stop_exclusive"]]==[827,827+len(ids)]
        assert cap["consumed_id_sha256"]==sha(canon(ids))==dur["token_sha256"]
        assert cap["hidden_shape"]==[len(ids),1280] and cap["pool_shape"]==[len(meta["spans"]),1280]
        hidden=sample("token_hidden.bf16")
        assert sha(hidden)==cap["hidden_sha256"]
        states=(np.frombuffer(hidden,"<u2").astype("<u4")*65536).view("<f4").reshape(len(ids),1280)
        assert np.isfinite(states).all()
        results=[]
        events=[]
        registry=online.Registry()
        scope=online.Controller()
        parents=[]
        for idx,row in enumerate(meta["spans"]):
            lo,hi=row["byte_range"]
            i,j=row["char_range"]
            assert raw.encode()[lo:hi]==raw[i:j].encode() and row["index"]==idx
            edges=meta["token_byte_edges"]
            pos=[n for n,(l,h) in enumerate(zip(edges,edges[1:])) if l<hi and h>lo]
            assert pos==row["token_indices"] and pos
            value=np.zeros(1280,dtype="<f4")
            for p in pos: np.add(value,states[p],out=value)
            np.divide(value,np.float32(len(pos)),out=value)
            results.append(value)
            span=online.Span(idx,row["page"],row["kind"],row["block_kind"],row["text"],
                             tuple(online.clean(c if isinstance(c,str) else c["text"]) for c in row["cells"]),tuple(row["bbox999"]))
            for e in online.identify(span,1):
                registry.update(e)
                scope.apply(e)
                if e.kind=="OPEN_LEDGER" and scope.depth==0 and row["page"]==1:
                    parents.append({"ptr":list(e.ptr),"literal":e.literal,"value":e.value,"owners_at_write":list(registry.choices()["owner"])})
                events.append([e.kind,list(e.ptr),e.literal,scope.depth])
        assert np.stack(results).tobytes()==sample("pooled.f32") and sha(sample("pooled.f32"))==cap["pooled_sha256"]
        eligible=(len(parents)==1 and online.key(parents[0]["value"])=="cedar" and parents[0]["owners_at_write"]==["Alder","Cedar"])
        return {"archive_revision":rev,"archive_sha256":sha(packed),"rgb_key":KEY,"members_sha256":members,
                "eligible_owner_cue":eligible,"reason":None if eligible else "actual_parent_or_candidates_missing",
                "parents":parents,"owners_end_opening":list(registry.choices()["owner"]),"observed_events":events,
                "verified":{"generated_tokens":len(ids),"consumed_positions":[827,827+len(ids)],
                            "hidden_shape":cap["hidden_shape"],"pooled_shape":cap["pool_shape"],
                            "span_position_selections":sum(len(r["token_indices"]) for r in meta["spans"]),
                            "warmup_calls":1,"loads":1,"scored_calls":1,"model_load_id":bind["model_load_id"],
                            "candidate":bind["candidate"],"plan_sha256":bind["plan_sha256"]}}

if __name__=="__main__":
    initialize()
    save(sys.argv[2],authenticate(sys.argv[1]))
