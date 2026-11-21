"""Verify 28 uncached singleton calls at two horizons, including feature-only prediction replay."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from matrix_audit import isolated_environment, materialize
from span_audit import snapshot


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def inspect(plan_file,pin):
    assert digest(plan_file)==pin
    plan=read(plan_file)
    root=Path(plan["output"])/"sensor"
    assert plan["phase"]=="c1"
    assert len(plan["calls"])==28 and len(plan["check_groups"])==12
    assert read(root/"binding.json")["plan_sha256"]==pin
    result={}
    by_doc={}
    per_sample={}
    for call in plan["calls"]:
        assert call["retain_hidden"] and call["hooked"]
        tag=call["tag"]
        folder=root/tag
        assert tag not in result
        result[tag]=snapshot(folder)
        key=tuple(p["rgb_sha256"] for p in call["pages"])
        assert len(key)==3
        per_sample[tag]=(key,folder)
        by_doc.setdefault(call["binder"],{})[call["window"]]=(key,folder)
    possible=set()
    pairs=[]
    for pair in plan["delivery"]["pairs"]:
        twins=pair["twins"]
        a,b=[by_doc[t["binder"]] for t in twins]
        assert len(a)==len(b)
        keys_a, keys_b=[[w[i][0] for i in range(1,len(w)+1)] for w in (a,b)]
        assert keys_a[0]!=keys_b[0] and keys_a[1:]==keys_b[1:]
        for i in range(2,len(a)+1):
            possible.add(frozenset((a[i][1].name,b[i][1].name)))
        pairs.append([[v[i] for i in range(1,len(v)+1)] for v in (a,b)])
    assert sorted(len(v[0]) for v in pairs)==[4,10]
    checked=set()
    for check in plan["check_groups"]:
        i,j=check["left"],check["right"]
        (rgb0,d0),(rgb1,d1)=per_sample[i],per_sample[j]
        assert rgb0==rgb1 and d0!=d1 and check["mode"]=="duplicate"
        # The metadata reproducer already rebuilt every original page, UTF8 offset and token pool.
        # Compare the actual bytes and stop event directly again for these distinct executions.
        for name in ("metadata.json","observed-positions.json","token_hidden.bf16","pooled.f32"):
            assert (d0/name).read_bytes()==(d1/name).read_bytes(),(i,j,name)
        a,b=read(d0/"native.json"),read(d1/"native.json")
        for k in ("prompt","prompt_token_ids","token_ids","text","finish_reason","terminal_observation","eos_id"):
            assert a[k]==b[k]
        checked.add(frozenset((i,j)))
    assert checked==possible and len(checked)==12
    return dict(source=plan["candidate"],model=plan["model_revision"],plan_sha256=pin,
                calls=len(result),complete_pairs=[12,30],duplicates_verified=12,
                emitted=sum(v["emitted"] for v in result.values()),
                pools_reconstructed=sum(v["pooled_bit_exact"] for v in result.values()),slots=result),pairs


def decisions(pairs,weights,fit_digest,probe_revision):
    isolated_environment()
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    materialize(probe_revision)
    from matrix import Memory
    from online import load_window
    from views import predict_pair
    assert digest(weights/"fit.json")==fit_digest
    fit=read(weights/"fit.json")
    models=[]
    for name in ("M1","M3"):
        f=weights/(name+".pt")
        assert digest(f)==fit["weights"][name]
        model=Memory(flat=name=="M1").eval()
        model.load_state_dict(torch.load(f, map_location="cpu", weights_only=True))
        models.append(model)
    keep={"decision","trace","target_scores","final_entry","binding_diagnostic","subtotal_diagnostic",
          "candidate_receipt","window1_audit"}
    def results(twins):
        predictions=predict_pair(*models, fit["thresholds"], *twins)
        return [{arm:{k:v for k,v in row.items() if k in keep} for arm,row in twin.items()} for twin in predictions]
    summary=[]
    for pair in pairs:
        uncached=[[load_window(path) for _,path in t] for t in pair]
        primary=results(uncached)
        cache={}
        reused=[]
        for t in pair:
            windows=[]
            for key,path in t:
                if key not in cache:
                    cache[key]=load_window(path)
                windows.append(cache[key])
            reused.append(windows)
        replay=results(reused)
        assert primary==replay
        serial=json.dumps(primary,sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(",",":")).encode()
        summary.append({"pages":3*len(pair[0]),"six_views_both_twins_equal":True,
                        "feature_objects":len(cache),"semantic_provenance_sha256":hashlib.sha256(serial).hexdigest()})
    return summary


if __name__=="__main__":
    assert sys.flags.isolated and sys.dont_write_bytecode
    p=argparse.ArgumentParser()
    p.add_argument("plan",type=Path)
    p.add_argument("pin")
    p.add_argument("--weights",type=Path)
    p.add_argument("--fit-pin")
    p.add_argument("--probe-revision")
    a=p.parse_args()
    receipt,pairs=inspect(a.plan,a.pin)
    if a.weights:
        assert a.fit_pin and a.probe_revision
        receipt["fit_sha256"]=a.fit_pin
        receipt["probe_revision"]=a.probe_revision
        receipt["decision_replay"]=decisions(pairs,a.weights,a.fit_pin,a.probe_revision)
    print(json.dumps(receipt,indent=2))

