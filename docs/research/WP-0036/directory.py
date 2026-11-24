"""Distance arithmetic uses half edit units, so comparisons are exact."""
import math
import string
import unicodedata
from itertools import combinations


def normalize(txt):
    return " ".join(unicodedata.normalize("NFKC",txt).casefold().translate(str.maketrans("","",string.punctuation)).split())


GROUPS = ("0oqd","1il7","5s","6gb8")  # normalized B/b merges the last two example groups


assert len(set("".join(GROUPS))) == sum(map(len,GROUPS))


def confusable(a,b):
    return a!=b and any(a in group and b in group for group in GROUPS)


def distance(a,b,eta):
    a,b=normalize(a),normalize(b)
    prev=list(range(0,2*(len(b)+1),2))
    for i,x in enumerate(a,1):
        row=[2*i]
        for j,y in enumerate(b,1):
            sub=0 if x==y else 1 if eta and confusable(x,y) else 2
            row.append(min(prev[j]+2,row[-1]+2,prev[j-1]+sub))
        prev=row
    return prev[-1]/2


def decode(value,choices,eta,scope=""):
    ranking=sorted(((v,distance(value,v,eta)) for v in choices),key=lambda t:(t[1],t[0])) if value is not None else []
    dmin=min((distance(a,b,eta) for a,b in combinations(choices,2)),default=None)
    ell=ranking[0][1] if ranking else None
    margin=ranking[1][1]-ell if len(ranking)>1 else None
    g1=bool(value is not None and not scope)
    g2=ell is not None and dmin is not None and ell<dmin/2
    g3=margin is not None and margin>=0.5
    reasons=[]
    if scope: reasons.append(scope)
    if value is None: reasons.append("missing_declaration")
    if len(choices)<2: reasons.append("insufficient_directory")
    if ell is not None and dmin is not None and not g2: reasons.append("distance")
    if margin is not None and not g3: reasons.append("margin")
    return dict(raw=value,directory=list(choices),ranking=ranking,nearest=[c for c,d in ranking if d==ell],dmin=dmin,ell=ell,
                margin=margin,G1=g1,G2=g2,G3=g3,reasons=reasons,decision=ranking[0][0] if g1 and g2 and g3 else None)


def perturb(record,truth,eta):
    rival,=[c for c in record["directory"] if c!=truth]
    before,other=normalize(record["raw"]),normalize(rival)
    assert len(before)==len(other)
    rows=[]
    for path in ("within","outside"):
        positions=[i for i,(a,b) in enumerate(zip(before,other,strict=True)) if a!=b and confusable(a,b)==(path=="within")]
        for k in range(math.floor(record["dmin"])+1):
            row=dict(path=path,k=k,source=before,rival=rival,truth=truth,eligible_positions=positions,attainable=k<=len(positions))
            if row["attainable"]:
                s=list(before)
                for i in positions[:k]: s[i]=other[i]
                string_value="".join(s)
                res=decode(string_value,record["directory"],eta)
                e=distance(string_value,truth,eta)
                row.update(changed=positions[:k],literal=string_value,actual_cost=distance(before,string_value,eta),
                           error=e,progress=distance(before,other,eta)-distance(string_value,other,eta),
                           nearest_correct=res["nearest"]==[truth],accepted_correct=res["decision"]==truth,
                           under_half=e<res["dmin"]/2,**{k:res[k] for k in ("ranking","ell","margin","G1","G2","G3","decision","reasons")})
            else:
                row.update(changed=None,literal=None,reason="insufficient_direct_rival_positions")
            rows.append(row)
    return rows


def twin(left,right,eta):
    choices=left["directory"]
    assert set(choices)=={"Alder","Cedar"} and choices==right["directory"]
    g=distance("Alder","Cedar",eta)
    ds=[dict(r["ranking"]) for r in (left,right)]
    a,b=[d["Cedar"]-d["Alder"] for d in ds]
    ea,eb=ds[0]["Alder"],ds[1]["Cedar"]
    mu,delta=(a+b)/2,a-b
    return dict(g=g,e_alpha=ea,e_beta=eb,Delta_alpha=a,Delta_beta=b,mu=mu,delta=delta,
                alpha_bounds=[g-2*ea,g],beta_bounds=[-g,-g+2*eb],mu_bound=max(ea,eb),delta_lower=2*g-2*(ea+eb),
                checks=[g-2*ea<=a<=g,-g<=b<=-g+2*eb,abs(mu)<=max(ea,eb),delta>=2*g-2*(ea+eb)])
