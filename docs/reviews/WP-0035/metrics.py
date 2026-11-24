"""Pair and count exposed results independently of state transitions."""
from collections import Counter, defaultdict
from math import prod
from struct import pack


def key(row, *fields):
    return tuple(row[f] for f in fields)


def contrast(scores, cases):
    pairs = defaultdict(dict)
    index = {p["pair"]:p for p in cases}
    for row in scores:
        group = key(row, "task","pair","horizon","model","write","read","phase","step")
        member = index[row["pair"]]["members"][row["binder"]]
        owner = member["expected"]["owner"]
        assert owner not in pairs[group]
        pairs[group][owner]=row
    output = []
    for group, members in pairs.items():
        aa,cc=(members[o] for o in ("Alder","Cedar"))
        a,b=aa["margin"],cc["margin"]
        assert a is not None and b is not None
        d=a-b
        mu=(a+b)/2
        gamma=d-2*abs(mu)
        wins=int(a>0)+int(b<0)
        assert (wins==2)==(gamma>0)
        output.append(dict(zip(("task","pair","horizon","model","write","read","phase","step"),group,strict=True),
                           alpha=a,beta=b,delta=d,mu=mu,gamma=gamma,wins=wins,
                           f64le={k:pack("<d",v).hex() for k,v in zip(("alpha","beta","delta","mu","gamma"),(a,b,d,mu,gamma))},
                           full_directory_wins=sum(r["leaders"]==[owner] for owner,r in members.items()),
                           checkpoint=aa["checkpoint"], actual_steps=[aa["actual_step"],cc["actual_step"]],
                           alpha_binder=aa["binder"],beta_binder=cc["binder"]))
    return output


def comparisons(rows):
    indexed={key(r,"task","pair","model","phase","step","write","read"):r for r in rows}
    result=[]
    for identity, row in indexed.items():
        *location,write,read=identity
        previous = {"W1":"W0","W2a":"W1","W2b":"W2a"}.get(write)
        contrasts=[]
        if previous:
            contrasts.append((previous,read,write+"-"+previous))
        if read=="R1":
            contrasts.append((write,"R0","R1-R0"))
        for w,r,label in contrasts:
            ref=indexed[(*location,w,r)]
            result.append(dict(task=row["task"],pair=row["pair"],horizon=row["horizon"],model=row["model"],
                        write=write,read=read,phase=row["phase"],step=row["step"],contrast=label,
                        **{k:row[k]-ref[k] for k in ("alpha","beta","delta","mu","gamma","wins")}))
    return result


def outcome(typed, expected, answerable):
    if typed["type"]=="ABSTAIN":
        return "A"
    assert typed["type"]=="Posting"
    return "C" if answerable and all(typed[k]==v for k,v in expected.items()) else "W"


def metrics(terminal, pairs):
    summaries=[]
    for scope in ("A/12","A/30","A","B/12","B/30","B"):
        task=scope[0]
        use=lambda v:v["task"]==task and (len(scope)==1 or v["horizon"]==int(scope[2:]))
        groups=defaultdict(list)
        for t in terminal:
            if use(t): groups[key(t,"model","write","read")].append(t)
        for group,terms in groups.items():
            cells=[r for r in pairs if use(r) and r["phase"]=="native_pre" and key(r,"model","write","read")==group]
            answer=[t for t in terms if t["answerable"]]
            safety=[t for t in terms if not t["answerable"]]
            if group[0]!="M2":
                assert len(cells)*2==len(answer)
            owner_counts=Counter(t["owner_status"] for t in answer)
            typed=Counter(t["typed_status"] for t in answer)
            breakdown=Counter(t["cutoff_failure"] for t in answer)
            s=Counter(t["typed_status"] for t in safety)
            reasons=Counter(t["typed"].get("reason","posting") for t in terms)
            summaries.append(dict(scope=scope,model=group[0],write=group[1],read=group[2],
                answerable_binders=len(answer),answerable_pairs=len(answer)//2,missing_typed=0,ranked_pairs=len(cells),
                both_ranked=sum(r["wins"]==2 for r in cells) if cells else None,
                full_directory_both_ranked=sum(r["full_directory_wins"]==2 for r in cells) if cells else None,
                rank_rate=(sum(r["wins"]==2 for r in cells)/len(cells)) if cells else None,
                typed={k:typed[k] for k in "CWA"},owner={k:owner_counts[k] for k in "CWA"} if cells else None,
                cutoff_breakdown=dict(breakdown) if cells else None,safety_binders=len(safety),
                safety={k:s[k] for k in "CWA"},safety_no_target=sum(t["typed"].get("reason")=="no_target" for t in safety),
                typed_reasons=dict(reasons)))
    return summaries


def attenuation(rows, updates):
    groups=defaultdict(list)
    for r in rows:
        if r["task"]=="A":
            groups[key(r,"pair","model","write","read")].append(r)
    result=[]
    for (pair,m,w,r), group in groups.items():
        d={v["step"]:v for v in group if v["phase"]=="post"}
        pre,=[v for v in group if v["phase"]=="native_pre"]
        by_binder={}
        for name in (pre["alpha_binder"],pre["beta_binder"]):
            rec=updates[(pair,name,m,w)]
            relevant=[v for v in rec if v["downstream_root"] and v["step"]<=pre["step"]]
            by_binder[name]=dict(downstream_root_count=len(relevant),retention_product=prod(x["retention"] for x in relevant),
                                 native_alpha_product=prod(x["alpha"] for x in relevant),alpha_beta_gt1=sum(x["alpha_beta"]>1 for x in relevant),
                                 alpha_beta_range=[min(x["alpha_beta"] for x in relevant),max(x["alpha_beta"] for x in relevant)] if relevant else None)
        result.append(dict(pair=pair,horizon=pre["horizon"],model=m,write=w,read=r,
             delta8=d[8]["delta"],delta11=d[11]["delta"],delta_tpost=pre["delta"],gamma_tpost=pre["gamma"],
             abs_delta_loss_fraction_8_to_11=1-abs(d[11]["delta"]/d[8]["delta"]) if d[8]["delta"] else None,
             first_postdecl_positive_delta=next((i for i in range(9,pre["step"]+1) if d[i]["delta"]>0),None),
             both_wins_steps=[v["step"] for v in group if v["phase"]=="post" and v["step"]<=pre["step"] and v["wins"]==2],
             downstream=by_binder))
    return result
