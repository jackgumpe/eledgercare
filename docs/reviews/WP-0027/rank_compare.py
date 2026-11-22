"""Compare every field and posting-producing cell; sample the initial cue on original operations."""
from collections import Counter
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import SCRATCH,save,sha
from rank_review import prepare,FIELDS,TROOT

def check():
    start=time.perf_counter()
    prepare()
    import torch
    from matrix import Memory,NeuralState,advance,direction
    from online import load_window,key,identify
    from run import setup
    setup()
    original=json.loads((SCRATCH/"ranks-r1.json").read_bytes())
    independent=original["arms"]
    root=Path(next(iter(original["physical_inputs"]))).parent
    directory=SCRATCH/"rank-author-r1"
    ranked=json.loads((directory/"owner-rankings.json").read_bytes())["arms"]
    probes=json.loads((directory/"owner-progression.json").read_bytes())["arms"]
    results={}
    for a,ours in independent.items():
        author=ranked[a]
        assert ours["grid"]==author["official_grid"]
        by_id={r["binder"]:r for r in ours["rows"]}
        assert by_id.keys()==author["by_binder"].keys()
        model=Memory(flat=a=="M1").eval()
        model.load_state_dict(torch.load(TROOT/(a+".pt"),weights_only=True,map_location="cpu"))
        initial,counts={},Counter()
        for b,r in by_id.items():
            ar=author["by_binder"][b]
            assert (r["target"],r["pair"],r["decision"])==(ar["target"],ar["pair"],ar["selected_binder_decision"])
            assert ar["attempt_count"]==len(r["attempts"])
            for orig,other in zip(r["attempts"],ar["attempts_by_ptr"].values(),strict=True):
                for f in FIELDS:
                    of=orig["fields"][f]
                    theirs=other["fields"][f]
                    assert of["expected"]==theirs["expected"] and of["scores"]==theirs["scores_by_key"]
                    assert of["delta"]==theirs["true_minus_best_other"]
                    counts["fields"]+=1
                owner_read=next(d for d in r["reads"] if d["field"]=="owner")
                owner_at=other["actual_reads"]["owner"]
                assert owner_read["response_sha"]==owner_at["read_sha256"] and owner_read["norm"]==owner_at["read_norm"]
            ap=author["by_pair"][r["pair"]]
            op=ours["pairs"][r["pair"]]
            assert ap["deltas"]==op["deltas"]
            assert ap["outcome"]=={"one":"one_correct","ambiguous":"ambiguous_control"}[op["category"]]
            assert not any(ap[k] for k in ("wrong_way_flip","any_exact_tie","any_zero_read"))
            if r["ambiguous"]:
                continue
            first,last=(load_window(root/ar["physical_tags"][j]) for j in (0,-1))
            target,=[e for s in last.spans for e in identify(s,len(ar["physical_tags"])) if e.kind=="TARGET"]
            assert "/".join(map(str,target.ptr)) in ar["attempts_by_ptr"]
            with torch.inference_mode():
                query=model.project(last)[2][target.ptr[-1]]
                state=NeuralState(model.zero())
                span_index=0
                saved={}
                actual_write=model.write
                refs=probes[a][r["pair"]]["by_binder"][b]["checkpoints"]
                def at(name,matrices):
                    response=model.read(matrices,state.controller.depth,query,"owner")
                    choices=state.registry.choices()["owner"]
                    logits=model.anchors("owner",choices)@direction(response)
                    scores={key(c):float(v) for c,v in zip(choices,logits,strict=True)}
                    assert scores==refs[name]["owner_scores"]
                    raw=sha(torch.stack(matrices).contiguous().numpy().tobytes())
                    assert raw==refs[name]["matrix_sha256"]
                    leaders=[c for c in scores if scores[c]==max(scores.values())]
                    saved[name]={"scores":scores,"leaders":leaders}
                def observe(ms,depth,k,v,alpha,beta):
                    nonlocal span_index
                    kinds={e.kind for e in identify(first.spans[span_index],1)}
                    if "OPEN_LEDGER" in kinds:
                        at("before-open-ledger/w1/depth0/1",ms)
                    updated=actual_write(ms,depth,k,v,alpha,beta)
                    if "OPEN_LEDGER" in kinds:
                        at("after-open-ledger/w1/depth0/1",updated)
                    if "DIRECTORY_OWNERS" in kinds:
                        at("after-owner-directory/w1/1",updated)
                    span_index+=1
                    if span_index==len(first.spans):
                        at("end/w1",updated)
                    return updated
                model.write=observe
                advance(model,state,first,1)
                model.write=actual_write
                assert len(saved)==4
                initial[b]={"pair":r["pair"],"true_owner":r["attempts"][0]["fields"]["owner"]["expected"],
                            "observations":saved}
        posting=[]
        for cell in author["posting_cells"]:
            count=Counter()
            owner_right=Counter()
            n=0
            for b,orig in by_id.items():
                answer=cell["by_binder"][b]
                assert answer["target"]==orig["target"] and answer["pair"]==orig["pair"]
                if len(orig["attempts"])!=1:
                    assert not answer["posted"] and answer["wrong_fields"] is None
                    continue
                fields=orig["attempts"][0]["fields"]
                eligible={f:x for f,x in fields.items() if x["scores"]}
                predicted={f:max(v["scores"],key=v["scores"].get) for f,v in eligible.items()}
                admit=all(v["scores"][predicted[f]]>=cell["tau"] for f,v in eligible.items())
                assert cell["margin"]==0 and admit==answer["posted"]
                if admit:
                    wrong=[]
                    for f,x in fields.items():
                        actual=answer["decision"][f]
                        assert (key(actual) if actual is not None else None)==predicted.get(f)
                        if (key(x["expected"]) if x["expected"] is not None else None)!=predicted.get(f):
                            wrong.append(f)
                    assert set(wrong)==set(answer["wrong_fields"]) and answer["silent"]==bool(wrong)
                    if "owner" not in wrong:
                        owner_right["+ ".join(wrong) or "all_correct"]+=1
                    count.update(wrong)
                    n+=1
            assert all(cell["wrong_field_postings"][f]==count[f] for f in FIELDS)
            posting.append(dict(tau=cell["tau"],margin=cell["margin"],postings=n,wrong=dict(count),
                                errors_when_owner_right=dict(owner_right)))
        shifts={}
        for pair in ours["pairs"]:
            twins=[r for r in by_id.values() if r["pair"]==pair and not r["ambiguous"]]
            if twins:
                gaps={}
                for twin in twins:
                    field=twin["attempts"][0]["fields"]["owner"]
                    gaps[key(field["expected"])]=field["scores"]["alder"]-field["scores"]["cedar"]
                shifts[pair]=gaps["alder"]-gaps["cedar"]
        checkpoints={}
        for name in next(iter(initial.values()))["observations"]:
            frequencies=Counter()
            both_correct=0
            for p in {r["pair"] for r in initial.values()}:
                twins=[r for r in initial.values() if r["pair"]==p]
                lead=[r["observations"][name]["leaders"] for r in twins]
                frequencies["same" if lead[0]==lead[1] else "different"]+=1
                both_correct+=all(w==[key(r["true_owner"])] for w,r in zip(lead,twins,strict=True))
            checkpoints[name]={**frequencies,"both_correct":both_correct}
        results[a]={"field_comparisons":counts["fields"],"pair_delta_tables_equal":10,
                    "ald_minus_ced_gap_true_alder_minus_true_cedar":shifts,
                    "three_extra_posting_cells_across_arms":posting,"early_source_checks":initial,"pair_leads":checkpoints}
    return {"arms":results,"seconds":time.perf_counter()-start,
            "candidate":"aa3ecc3b04dada439529621cdfa93f8f8cf581e5",
            "candidate_outputs":{name:sha((directory/name).read_bytes()) for name in ("owner-rankings.json","owner-progression.json")}}

if __name__=="__main__":
    save(SCRATCH/sys.argv[1],check())

