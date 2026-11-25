"""Paired pilot decision rules and box audit. Controls use constructed counts/rectangles only."""
from fractions import Fraction


def decision(rows, eligible, costs, *, leak=False, controls_ok=True):
    """rows carry common family keys by construction, B/E/R/F/T dispositions C, W or A."""
    assert len(rows)==len(eligible)
    arms="BERFT"
    counts={a:{k:sum(r[a]==k for r in rows) for k in "CWA"} for a in arms}
    transitions={a:{before+after:sum(r["B"]==before and r[a]==after for r in rows)
                    for before in "CWA" for after in "CWA"} for a in arms}
    amb=sum(r["ambiguous"] for r in rows)
    def new_wrong(a):
        return transitions[a]["AW"]+transitions[a]["CW"]
    h1={a:(None if not amb else any(r["ambiguous"] and r["B"]=="A" and r[a]=="C" for r in rows)
                      and new_wrong(a)==0 and transitions[a]["CA"]+transitions[a]["CW"]==0) for a in "RT"}
    target=[i for i,yes in enumerate(eligible) if yes and rows[i]["ambiguous"]]
    def complete():
        return costs is not None and all(costs[i][a] is not None for i in target for a in "ERFT")
    comparable=bool(target) and complete()
    totals={a:([sum(costs[i][a][j] for i in target) for j in range(3)] if comparable else None) for a in "ERFT"}
    def paired(a,k):
        return sum(rows[i][a]==k for i in target)
    h2=(totals["R"][0]<totals["F"][0] and paired("R","C")>=paired("F","C")
        and paired("R","W")<=paired("F","W")) if comparable else None
    # All eligible ambiguous rows must have complete costs to compare R versus T.
    if leak or not controls_ok or any(new_wrong(a) for a in "RFT"):
        verdict="HOLD_COMPARISON"
    elif len(rows)<24 or not amb or not comparable or len(target)!=amb:
        verdict="FEASIBILITY"
    elif (h1["R"] and h2 and counts["R"]["C"]>=counts["T"]["C"] and counts["R"]["W"]<=counts["T"]["W"]
          and totals["R"][2]<totals["T"][2]):
        verdict="CONSIDER_R"
    elif (h1["T"] and counts["T"]["C"]>=counts["R"]["C"] and counts["T"]["W"]<=counts["R"]["W"]
          and totals["T"][2]<=totals["R"][2]):
        verdict="PREFER_T"
    else:
        verdict="NO_WINNER"
    return dict(counts=counts,transitions=transitions,h1=h1,h2=h2,verdict=verdict,
                ambiguous=amb,paired_cost_n=len(target),cost_totals=totals,new_wrong_E=new_wrong("E"),
                equal_performance=bool(comparable and counts["R"]==counts["T"] and totals["R"][2]==totals["T"][2]))


def overlap(a,b):
    if a is None or b is None:
        return None
    def area(rect):
        x,y,X,Y=rect
        return max(0,X-x)*max(0,Y-y)
    if not area(a) or not area(b):
        return None
    inter=area((max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])))
    return Fraction(inter,area(a)+area(b)-inter)


def box_audit(chosen,ties,box,reference):
    vals=[overlap(a,b) for a,b in zip(box,reference,strict=True)]
    def mean(mask):
        cells=[v for j,v in enumerate(vals) if mask>>j&1]
        return sum(cells)/len(cells) if cells and None not in cells else None
    other=[mean(q) for q in ties if q!=chosen]
    selected=mean(chosen)
    return dict(selected=str(selected) if selected is not None else None,
                other_mean=str(sum(other)/len(other)) if other and None not in other else None,
                alternatives=len(other),missing=sum(a is None or b is None for a,b in zip(box,reference)),
                degenerate=sum(v is None and a is not None and b is not None for v,a,b in zip(vals,box,reference)))


def audit_protocol():
    fixtures={}
    def run(name,n=24,r="C",t="C",e="W",f="C",latency=(2,3),goal="CONSIDER_R",**kw):
        row=dict(B="A",E=e,R=r,F=f,T=t,ambiguous=True)
        costs=dict(E=(1,100,1),R=(2,200,latency[0]),F=(4,400,4),T=(1,400,latency[1]))
        result=decision([row]*n,[True]*n,[costs]*n,**kw)
        assert result["verdict"]==goal,(name,result)
        fixtures[name]=result
    run("literal_only")
    run("global_R",r="W",goal="HOLD_COMPARISON")
    run("global_F",f="W",goal="HOLD_COMPARISON")
    run("global_T",t="W",goal="HOLD_COMPARISON")
    run("leak",leak=True,goal="HOLD_COMPARISON")
    run("failed_control",controls_ok=False,goal="HOLD_COMPARISON")
    run("too_few",n=23,goal="FEASIBILITY")
    run("whole_table_tie",latency=(2,2),goal="PREFER_T")
    run("no_recovery",r="A",t="A",goal="NO_WINNER")
    inherited=decision([dict(B="W",E="W",R="W",F="W",T="W",ambiguous=False)],[False],None)
    assert inherited["transitions"]["R"]["WW"]==1 and not inherited["new_wrong_E"] and inherited["h1"]["R"] is None
    boxes=[(0,0,2,2),(0,0,2,1),(0,0,1,2),(0,0,2,2)]
    refs=[(0,0,2,2)]*4
    iou=box_audit(7,[7,14],boxes,refs)
    assert iou["selected"]==iou["other_mean"]=="2/3"
    unequal=box_audit(7,[7,14],boxes,[*refs[:3],(4,4,6,6)])
    assert unequal["selected"]=="2/3" and unequal["other_mean"]=="1/3"
    invalid=box_audit(7,[7],boxes,[None,(1,1,1,2),*refs[2:]])
    assert invalid==dict(selected=None,other_mean=None,alternatives=0,missing=1,degenerate=1)
    return dict(source="constructed protocol controls",priority_examples=fixtures,inherited=inherited,
                constructed_box_examples=[iou,unequal,invalid],
                iid_model_only={m:round(0.9**m+m*0.1*0.9**(m-1),10) for m in (3,4,8)},
                zero_events_illustrative_upper95={n:1-0.05**(1/n) for n in (24,10)},
                zero_n_upper95=None)
