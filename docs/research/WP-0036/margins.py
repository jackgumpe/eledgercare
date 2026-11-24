"""Module A synthetic checks with finite binary64 logits and exact conformal rank."""
import math
import struct
from fractions import Fraction
from directory import distance

CASES={
    "included":(["0","O","Q","zz"],[5,4,3,0]),
    "excluded":(["0","zz","O","Q"],[5,4,2,1]),
    "singleton":(["cat","zzzz","moon"],[4,3,1]),
    "subword":(["100","1OO","1O0",".50","50"],[5,1,4,3,2]),
    "alias":([".50","50","5O","xx"],[5,4,3,-1]),
    "tie":(["D","0","Q","abc"],[3,3,1,0]),
    "rounded":(["0","O","Q","zz"],[1,0,-1000,-1100])
}


def f64(x):
    return "+inf" if x==math.inf else struct.pack("<d",x).hex()


def score(tokens,z,eta):
    assert len(tokens)==len(z) and len(z)>=2 and all(map(math.isfinite,z))
    top,second,*_=sorted(range(len(z)),key=lambda i:(-z[i],i))
    rivals=[i for i,v in enumerate(tokens) if i!=top and distance(v,tokens[top],eta)<=1-eta]
    ordinary=z[top]-z[second]
    conf=math.inf
    if rivals:
        m=max(z[i] for i in rivals)
        conf=z[top]-(m+math.log(sum(math.exp(z[i]-m) for i in rivals)))
    result=min(ordinary,conf)
    return dict(vocab=tokens,logits=z,top=top,runner=second,rivals=rivals,included=second in rivals,
                ordinary_f64le=f64(ordinary),conf_f64le=f64(conf),score_f64le=f64(result),
                ordinary=ordinary,conf=conf if math.isfinite(conf) else "+inf",score=result,
                observed_strict=conf<ordinary,theoretical_strict=second in rivals and len(rivals)>=2)


def index(vals,alpha):
    k=math.ceil((len(vals)+1)*(1-alpha))
    return k, sorted(vals)[k-1] if k<=len(vals) else math.inf


def exercise():
    out=[dict(case=n,eta=e,**score(*value,e)) for n,value in CASES.items() for e in (0,.5)]
    docs=[[1,4],[2,2],[3,5],[2,4]]
    ranks=[]
    for mode in ("selected","max"):
        vals=[d[0] if mode=="selected" else max(d) for d in docs]
        for alpha in map(Fraction,["1/5","2/5","1/10"]):
            k,v=index(vals,alpha)
            ranks.append(dict(mode=mode,alpha=str(alpha),documents=docs,values=vals,n=len(vals),k=k,
                              threshold=v if math.isfinite(v) else "+inf",threshold_f64le=f64(v),strict_escape=[x>v for x in vals],
                              ties_escape=False,scope="illustrative synthetic index only"))
    return out,ranks
