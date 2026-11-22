"""Independent observer of the unchanged recurrent transition and reconstruction on the literal axis."""
import ast
import io
import json
from pathlib import Path
import struct
import sys
from zipfile import ZipFile

sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit import BASE, GATE, KEY, ROOT, SCRATCH, ZIP, blob, initialize, pin, save, sha

PROBE="7db67283a4ffd3e7a20bb8d80499572cc7118c71"
FIT="6d79c24364ba10a1d9bfa4c72c837e2f216cf4bc"
FIXTURE="ee8e96afcbd7a3c1f3eaa8125c05e68003c4a893"
OBSERVER="46d544f1b2e729408dc1f9eb0e35161de14df41c"

def observer():
    # Use only the non-author's archived observer and arithmetic. Its historical
    # entry point targets a different scratch tree and never runs here.
    raw=pin(OBSERVER,"docs/reviews/WP-0028/historical.py")
    tree=ast.parse(raw)
    funcs=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in {"measure","arr","replay"}]
    assert len(funcs)==3
    ns={"sha":sha}
    exec(compile(ast.Module(body=funcs,type_ignores=[]),"<pinned independent WP-0028 observer>","exec"),ns)
    return ns["replay"],ns["measure"]

def verify(gate_rev):
    import torch
    from contextlib import ExitStack
    for name in ("online","matrix","views","run"):
        pin(PROBE,"docs/research/WP-0024/probe/"+name+".py")
    sys.path.insert(0,str(ROOT/"docs/research/WP-0024/probe"))
    import matrix, online, run
    run.setup()
    assert not torch.cuda.is_available() and torch.get_num_threads()==1 and torch.are_deterministic_algorithms_enabled()
    replay,measure=observer()
    gate=json.loads(blob(gate_rev,GATE))
    manifest=json.loads(pin(FIXTURE,"docs/fixtures/WP-0028/manifest.json"))
    fit=json.loads(pin(FIT,"docs/research/WP-0026/fit/fit.json"))
    phases=("t1","t2","t3")
    owners=("Alder","Cedar")
    result={"gate_revision":gate_rev,"arms":{},"archive_uses":{},"cross_horizon":{}}
    if not gate["authenticated"] or not gate["eligible_owner_cue"]:
        result["counts"]={"planned_physical_pairs":2,"planned_arm_pairs":4,"admitted":0,"completed":0}
        return result
    data=blob(gate["archive_revision"],ZIP)
    assert sha(data)==gate["archive_sha256"]
    with ExitStack() as stack:
        native=stack.enter_context(ZipFile(io.BytesIO(data)))
        sources={}
        for pair in manifest["pairs"]:
            for member in pair["members"]:
                for w in member["windows"]:
                    key=w["rgb_key"]
                    assert sha((json.dumps([p["rgb_sha256"] for p in w["pages"]],indent=2)+"\n").encode())==key
                    result["archive_uses"].setdefault(key,[]).append([pair["horizon"],member["owner"],w["window"]])
                    if key==KEY:
                        assert w["feature"] is None and member["owner"]=="Cedar" and w["window"]==1
                        prefix="sensor/k0001/"
                        z=native
                        hashes={f:gate["members_sha256"][prefix+f] for f in ("metadata.json","pooled.f32","through-eos.u32le")}
                    else:
                        f=w["feature"]
                        assert f["archive"]=="docs/reviews/WP-0026/cal-features-primary/primary-001.zip"
                        if f["archive"] not in sources:
                            raw=blob(f["archive_revision"],f["archive"])
                            sources[f["archive"]]=stack.enter_context(ZipFile(io.BytesIO(raw)))
                        z=sources[f["archive"]]
                        prefix=f["prefix"]
                        hashes={n:f[k] for n,k in (("metadata.json","metadata_sha256"),("pooled.f32","pooled_sha256"),("through-eos.u32le","through_eos_sha256"))}
                    receipt=json.loads(z.read(prefix+"receipt.json"))
                    assert [p["rgb_sha256"] for p in receipt["pages"]]==[p["rgb_sha256"] for p in w["pages"]]
                    dest=SCRATCH/"checked-windows"/key
                    dest.mkdir(parents=True,exist_ok=True)
                    for name,h in hashes.items():
                        raw=z.read(prefix+name)
                        assert sha(raw)==h==receipt["artifacts"][name]
                        path=dest/name
                        if path.exists(): assert path.read_bytes()==raw
                        else: path.write_bytes(raw)
    assert len(result["archive_uses"])==11 and sum(map(len,result["archive_uses"].values()))==28
    assert len(result["archive_uses"][KEY])==2
    with torch.inference_mode():
        for arm in ("M1","M3"):
            raw=pin(FIT,"docs/research/WP-0026/fit/"+arm+".pt")
            assert sha(raw)==fit["weights"][arm] and fit["thresholds"][arm]==[1.0,0.1]
            model=matrix.Memory(flat=arm=="M1").eval()
            model.load_state_dict(torch.load(io.BytesIO(raw),map_location="cpu",weights_only=True))
            tables={}
            for pair in manifest["pairs"]:
                t=pair["horizon"]
                ends=[]
                tables[t]={"binders":{},"trajectory":{},"source_target":pair["base_target"]}
                for m in pair["members"]:
                    paths=[SCRATCH/"checked-windows"/w["rgb_key"] for w in m["windows"]]
                    def load(): return [online.load_window(p) for p in paths]
                    windows=load()
                    registry,controller=online.Registry(),online.Controller()
                    parents,targets=[],[]
                    for n,w in enumerate(windows,1):
                        for s in w.spans:
                            for e in online.identify(s,n):
                                controller.apply(e)
                                registry.update(e)
                                if e.kind=="OPEN_LEDGER" and n==1 and controller.depth==0:
                                    parents.append((e.ptr,e.literal,e.value,registry.choices()["owner"]))
                                if e.kind=="TARGET":
                                    targets.append((e.ptr,e.literal,e.value,controller.ambiguous(),registry.choices()["owner"]))
                    parent,=parents
                    target,=targets
                    assert parent[0][:2]==(1,1) and parent[2]==m["owner"] and parent[3]==owners
                    assert target[0][:2]==(t//3,2) and target[3:]==("",owners)
                    ends.append((target,paths[-1]))
                    arguments=(matrix,online,run,torch)
                    state,records=replay(model,windows,True,arguments)
                    plain,_=replay(model,load(),False,arguments)
                    again,duplicate=replay(model,load(),True,arguments)
                    assert state==plain==again and records==duplicate
                    assert records["t1"]["ptr"]==list(parent[0]) and records["t3"]["ptr"]==list(target[0])
                    assert len({r["query"] for r in records.values()})==1
                    # Run the frozen public entry point with audit=False as well.
                    direct=run.state_for(model,load())
                    assert state["typed"]==matrix.result(direct,fit["thresholds"][arm])
                    assert sha(torch.stack(direct.matrices).contiguous().numpy().tobytes())==state["final_matrix"]
                    att,=direct.attempts
                    assert {f:v.contiguous().numpy().tobytes().hex() for f,v in att.scores.items()}==state["field_bytes"]
                    tables[t]["binders"][m["owner"]]={"binder":m["binder"],"target":m["target"],"parent":parent,"posting":target,
                        "typed":state["typed"],"fields":state["fields"],"field_bytes":state["field_bytes"],
                        "final_matrix":state["final_matrix"],"checkpoints":records,"fresh_duplicate_plain_agreement":True}
                assert ends[0]==ends[1]
                inputs=tables[t]["binders"]
                initial=None
                for step in phases:
                    a,b=[inputs[o]["checkpoints"][step] for o in owners]
                    assert a["query"]==b["query"]
                    scores={o:x["scores"] for o,x in zip(owners,(a,b),strict=True)}
                    if initial is None: initial=measure(scores)["delta"]
                    tables[t]["trajectory"][step]=measure(scores,initial)
            result["arms"][arm]=tables
            result["cross_horizon"][arm]={step:{owner:{
                k:tables[12]["binders"][owner]["checkpoints"][step][k]==tables[30]["binders"][owner]["checkpoints"][step][k]
                for k in ("query","scores","read","matrix")} for owner in owners} for step in phases}
    result["counts"]={"planned_physical_pairs":2,"planned_arm_pairs":4,"admitted":4,"completed":4,
                      "member_checkpoints":24,"native_target_attempts":8,"logical_windows":28,"unique_features":11}
    return result

if __name__=="__main__":
    initialize()
    save(sys.argv[2],verify(sys.argv[1]))
