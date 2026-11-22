"""Reviewer-only observer of native write returns and native attempt inputs."""
from collections import Counter
from pathlib import Path
import io
import json
import struct
import sys
from zipfile import ZipFile
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BASE, DEV, FIT, HISTORY, PROBE, ROOT, WORK, blob, output, pinned, sha

def build():
    path = ROOT/"docs/research/WP-0024/probe"
    for name in ("matrix","online","run","views"):
        pinned(PROBE, f"docs/research/WP-0024/probe/{name}.py")
    sys.path.insert(0,str(path))
    import matrix
    import online
    import run
    import torch
    run.setup()
    assert not torch.cuda.is_available() and torch.get_num_threads()==1 and torch.are_deterministic_algorithms_enabled()
    return matrix,online,run,torch

def measure(scores, start=None):
    a,c=(scores[owner]["alder"]-scores[owner]["cedar"] for owner in ("Alder","Cedar"))
    delta,mu=a-c,(a+c)*0.5
    assert a==mu+delta/2 and c==mu-delta/2
    assert (a>0>c)==(delta>2*abs(mu))
    assert c-a==-delta
    return {"margin_alder":a,"margin_cedar":c,"delta":delta,"mu":mu,"win":a>0>c,
            "D":None if start is None else delta-start,
            "R":delta/start if start is not None and abs(start)>1e-6 else None}

def arr(t):
    return t.detach().contiguous().numpy().tobytes()

def replay(model, windows, active, modules):
    matrix,online,run,torch=modules
    state=matrix.NeuralState(model.zero())
    checkpoints={}
    final=windows[-1]
    target,=[e for s in final.spans for e in online.identify(s,len(windows)) if e.kind=="TARGET"]
    target_query=model.project(final)[2][target.ptr[-1]]
    native_attempt,native_write=matrix.attempt,model.write
    def snapshot(name, mats, ptr):
        choices=state.registry.choices()["owner"]
        assert sorted(map(online.key,choices))==["alder","cedar"]
        logits=model.read(mats,state.controller.depth,target_query,"owner")
        values=model.anchors("owner",choices) @ matrix.direction(logits)
        checkpoints[name]={"ptr":list(ptr),"depth":state.controller.depth,
            "matrix":sha(arr(torch.stack(mats))),"query":sha(arr(target_query)),"read":sha(arr(logits)),
            "scores":{online.key(k):float(v) for k,v in zip(choices,values,strict=True)}}
    def attempt(m,s,q,event):
        assert event.ptr==target.ptr and torch.equal(q,target_query)
        snapshot("t3",s.matrices,event.ptr)
        return native_attempt(m,s,q,event)
    def write(mats,depth,k,v,a,b):
        nonlocal count
        index=count
        count+=1
        span=window.spans[index]
        updated=native_write(mats,depth,k,v,a,b)
        if num==1 and any(e.kind=="OPEN_LEDGER" for e in online.identify(span,num)):
            assert state.controller.depth==0 and "t1" not in checkpoints
            snapshot("t1",updated,(num,span.page,index))
        return updated
    try:
        if active:
            matrix.attempt=attempt
            model.write=write
        for num,window in enumerate(windows,1):
            count=0
            matrix.advance(model,state,window,num)
            if active:
                assert count==len(window.spans)
                if num==1:
                    last=window.spans[-1]
                    snapshot("t2",state.matrices,(num,last.page,last.index))
    finally:
        matrix.attempt=native_attempt
        if active:
            del model.write
    attempt,=state.attempts
    fields={n:{online.key(k):float(v) for k,v in zip(attempt.choices[n],values,strict=True)}
            for n,values in attempt.scores.items()}
    if active:
        assert fields["owner"]==checkpoints["t3"]["scores"]
    return {"final_matrix":sha(arr(torch.stack(state.matrices))),"typed":matrix.result(state,(1.0,0.1)),
            "open":matrix.result(state,(-0.25,0.0)),"fields":fields,"trace":state.trace,
            "field_bytes":{n:arr(values).hex() for n,values in attempt.scores.items()},
            "registry":state.registry.choices(),"growth":state.growth},checkpoints

def main():
    modules=build()
    matrix,online,run,torch=modules
    rel="docs/research/WP-0026/fit/"
    fit=json.loads(pinned(FIT,rel+"fit.json"))
    routebytes=pinned(FIT,rel+"cal-transport.json")
    assert sha(routebytes)==fit["input_hashes"]["cal"]
    archive_rel="docs/reviews/WP-0026/cal-features-primary/primary-001.zip"
    archive_raw=pinned(BASE,archive_rel)
    routes=json.loads(routebytes)["pairs"]
    tags={Path(w).name for p in routes for t in p["twins"] for w in t["windows"]}
    assert len(tags)==29
    features={}
    with ZipFile(io.BytesIO(archive_raw)) as archive:
        for tag in tags:
            name="runs/cal-features-r1/sensor/"+tag+"/"
            receipt=json.loads(archive.read(name+"receipt.json"))
            work=WORK/"native-windows"/tag
            work.mkdir(parents=True,exist_ok=True)
            for f in ("metadata.json","pooled.f32"):
                raw=archive.read(name+f)
                assert sha(raw)==receipt["artifacts"][f]
                (work/f).write_bytes(raw)
            features[tag]=online.load_window(work)
    truth=(DEV/"private/cal/truth.json").read_bytes()
    assert sha(truth)==fit["input_hashes"]["cal_truth"]=="a227da1293bcd6f8b0f636ce3349abd12d02a52361a46b47dbf34969cc773ff1"
    labels={r["binder"]:r for r in json.loads(truth)["binders"]}
    history="docs/research/WP-0027/owners/"
    ranks=json.loads(pinned(HISTORY,history+"owner-rankings.json"))["arms"]
    progress=json.loads(pinned(HISTORY,history+"owner-progression.json"))["arms"]
    outcome={}
    with torch.inference_mode():
        for arm in ("M1","M3"):
            weights=blob(FIT,rel+arm+".pt")
            assert sha(weights)==fit["weights"][arm]
            model=matrix.Memory(flat=arm=="M1").eval()
            model.load_state_dict(torch.load(io.BytesIO(weights),map_location="cpu",weights_only=True))
            table={}
            native_tie=matrix.Attempt(scores={"owner":torch.tensor([0.125,0.125])},choices={"owner":["Alder","Cedar"]})
            assert native_tie.typed((-0.25,0.0))=={"type":"ABSTAIN","reason":"zero_state_tie"}
            zero_control=False
            for p in routes:
                binders={}
                for tr in p["twins"]:
                    binder=tr["binder"]
                    label=labels[binder]
                    if label["ambiguous"]:
                        continue
                    windows=[features[Path(w).name] for w in tr["windows"]]
                    if not zero_control:
                        zero_state=matrix.NeuralState(model.zero())
                        for ordinal,window in enumerate(windows,1):
                            matrix.advance(model,zero_state,window,ordinal,zero=True)
                        zero_attempt,=zero_state.attempts
                        assert zero_attempt.zero and torch.count_nonzero(zero_attempt.scores["owner"]).item()==0
                        assert matrix.result(zero_state,(-.25,0.))=={"type":"ABSTAIN","reason":"zero_state_tie"}
                        zero_control=True
                    recording,recs=replay(model,windows,True,modules)
                    baseline,_=replay(model,windows,False,modules)
                    again,repeat=replay(model,windows,True,modules)
                    assert recs==repeat and recording==baseline==again
                    assert recording["typed"]==ranks[arm]["by_binder"][binder]["selected_binder_decision"]
                    actual,=ranks[arm]["by_binder"][binder]["attempts_by_ptr"].values()
                    for f,scores in recording["fields"].items():
                        assert scores==actual["fields"][f]["scores_by_key"]
                    old=progress[arm][label["pair"]]["by_binder"][binder]["checkpoints"]
                    for step,pointer in (("t1","after-open-ledger/w1/depth0/1"),("t2","end/w1"),
                                         ("t3","before-target/"+"/".join(map(str,recs["t3"]["ptr"])))):
                        a,b=recs[step],old[pointer]
                        assert a["scores"]==b["owner_scores"] and a["depth"]==b["controller"]["depth"]
                        assert a["matrix"]==b["matrix_sha256"] and a["query"]==b["query_sha256"] and a["read"]==b["owner_read_sha256"]
                    binders[label["owner"]]={"binder":binder,"target":tr["target"],"checkpoints":recs,
                        "field_bits":{f:{k:struct.pack("<f",v).hex() for k,v in scores.items()} for f,scores in recording["fields"].items()},
                        "typed":recording["typed"],"open":recording["open"],"final_matrix":recording["final_matrix"]}
                if not binders:
                    continue
                assert set(binders)=={"Alder","Cedar"}
                assert len({v["checkpoints"][t]["query"] for v in binders.values() for t in ("t1","t2","t3")})==1
                steps={}
                for name in ("t1","t2","t3"):
                    scores={k:v["checkpoints"][name]["scores"] for k,v in binders.items()}
                    delta=measure(scores)["delta"]
                    if name=="t1":
                        start=delta
                    steps[name]=measure(scores,start)
                table[label["pair"]]={"binders":binders,"trajectory":steps}
            assert len(table)==8
            outcome[arm]=table
    controls={}
    for start in (None,0.,1e-7,1e-6,-1e-6,1.0001e-6,-0.1):
        scores={"Alder":{"alder":0.25,"cedar":0.25},"Cedar":{"alder":-0.25,"cedar":0.25}}
        result=measure(scores,start)
        assert not result["win"] and (result["R"] is None)==(start is None or abs(start)<=1e-6)
        controls[str(start)]=result
    return {"arms":outcome,"controls":controls,"fit":fit["weights"],"archive_sha256":sha(archive_raw)}

if __name__=="__main__":
    output(sys.argv[1],main())
