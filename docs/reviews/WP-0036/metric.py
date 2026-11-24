"""Independent text, lifted-token and exact-rank calculations."""
from fractions import Fraction
from itertools import combinations
from math import ceil, exp, inf, log
import string
import struct
import unicodedata


def norm(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(text.translate(str.maketrans("", "", string.punctuation)).split())


# Closure after folding merges the classes containing B and b.
FAMILIES = ["0oqd", "1il7", "5s", "6gb8"]
CLASS = {c: group for group in FAMILIES for c in group}


def alike(a, b):
    return CLASS.get(a,a) == CLASS.get(b,b)


def edit(x, y, eta):
    """Minimum half-edit units on normalized strings, converted to exact binary fractions."""
    prev = list(range(0, 2*len(y)+1, 2))
    for i, a in enumerate(x, 1):
        row = [2*i]
        for j, b in enumerate(y, 1):
            subst = 0 if a == b else 2 - int(2*eta) * int(alike(a,b))
            row.append(min(prev[j]+2, row[-1]+2, prev[j-1]+subst))
        prev = row
    return prev[-1] / 2


def rank(text, candidates, eta, scope=""):
    ranks = sorted((edit(norm(text),norm(c),eta),c) for c in candidates) if text is not None else []
    separations = [edit(norm(a),norm(b),eta) for a,b in combinations(candidates,2)]
    dmin = min(separations,default=None)
    margin = ranks[1][0]-ranks[0][0] if len(ranks)>=2 else None
    g1 = bool(text is not None and not scope)
    g2 = bool(ranks and dmin is not None and 2*ranks[0][0] < dmin)
    g3 = margin is not None and margin >= 0.5
    reasons = [r for r,on in (("unresolved_scope",bool(scope)),("missing_declaration",text is None),
                               ("insufficient_directory",dmin is None),("distance",not g2),("margin",not g3)) if on]
    return dict(text=text,candidates=sorted(candidates),ranks=ranks,dmin=dmin,margin=margin,
                g1=g1,g2=g2,g3=g3,reason=reasons,choice=ranks[0][1] if g1 and g2 and g3 else None)


def twin_sweep(binder, field, truth, eta):
    x = norm(field["text"])
    true = norm(truth)
    [rival_name] = [v for v in field["candidates"] if v != truth]
    alt = norm(rival_name)
    assert len(x) == len(alt)
    for path in ("within","outside"):
        sites = [i for i,(a,b) in enumerate(zip(x,alt)) if a!=b and alike(a,b)==(path=="within")]
        for k in range(int(field["dmin"])+1):
            entry = dict(binder=binder,eta=eta,path=path,k=k,positions=sites,eligible=len(sites),
                         observed=x,rival=alt,truth=truth)
            if k > len(sites):
                yield {**entry,"attainable":False,"reason":"insufficient eligible differing positions"}
                continue
            chars = list(x)
            for i in sites[:k]:
                chars[i] = alt[i]
            s = "".join(chars)
            r = rank(s,field["candidates"],eta)
            e = edit(s,true,eta)
            nearest = [c for cost,c in r["ranks"] if cost == r["ranks"][0][0]]
            if e < field["dmin"]/2:
                assert nearest == [truth]
            if e <= (field["dmin"]-0.5)/2:
                assert r["choice"] == truth
            yield {**entry,"attainable":True,"modified":s,"actual_edits":k,"cost":edit(x,s,eta),
                   "error":e,"progress":edit(x,alt,eta)-edit(s,alt,eta),
                   "nearest":nearest,"nearest_correct":nearest==[truth],"accepted_correct":r["choice"]==truth,
                   "field":r}


CASES = {
    "included":(["0","O","Q","zz"],[5,4,3,0]),
    "excluded":(["0","zz","O","Q"],[5,4,2,1]),
    "singleton":(["cat","zzzz","moon"],[4,3,1]),
    "subword":(["100","1OO","1O0",".50","50"],[5,1,4,3,2]),
    "alias":([".50","50","5O","xx"],[5,4,3,-1]),
    "tie":(["D","0","Q","abc"],[3,3,1,0]),
    "rounded":(["0","O","Q","zz"],[1,0,-1000,-1100])
}


def binary(x):
    return "+infinity" if x == inf else struct.pack("<d",x).hex()


def token_checks():
    rows = []
    for name,(tokens,z) in CASES.items():
        ids = sorted(range(len(tokens)),key=lambda i:(-z[i],i))
        top, second = ids[:2]
        for eta in (0.0,0.5):
            rivals = [i for i,t in enumerate(tokens) if i!=top and edit(norm(tokens[top]),norm(t),eta)<=1-eta]
            m = float(z[top] - z[second])
            mc = inf
            if rivals:
                peak = max(z[i] for i in rivals)
                lse = peak + log(sum(exp(z[i]-peak) for i in rivals))
                mc = z[top] - lse
            assert second not in rivals or mc<=m
            rows.append(dict(case=name,eta=eta,tokens=tokens,logits=z,top=top,second=second,rivals=rivals,
                             m=binary(m),conf=binary(mc),sigma=binary(min(m,mc)),
                             strict_real=second in rivals and len(rivals)>1,strict_fp=mc<m))
    docs = [[1,4],[2,2],[3,5],[2,4]]
    conformal = []
    for rule, values in (("one_possible_draw",[r[0] for r in docs]),("document_max",list(map(max,docs)))):
        for alpha in (Fraction(1,5),Fraction(2,5),Fraction(1,10)):
            n = len(values)
            k = ceil((n+1)*(1-alpha))
            cut = sorted(values)[k-1] if k<=n else inf
            conformal.append(dict(rule=rule, alpha=str(alpha), values=values,n=n,k=k,cut=binary(cut),
                                  strict_escapes=[v>cut for v in values],
                                  tie_escapes=(cut>cut),bound=str(Fraction(n+1-k,n+1))))
    return {"token_cases":rows,"conformal":conformal,"error_scores_synthetic":docs,
            "controls":[rank("AB",["ab","a.b"],.5),rank("Alder",["Alder","Cedar"],.5,"open_child"),
                        rank(None,["Alder","Cedar"],.5),rank("aaaa",["bbbb","cccx"],.5)]}
