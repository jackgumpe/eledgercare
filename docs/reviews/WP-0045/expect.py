"""Pre-exposure full-field reference, analytical and separate from all executable evaluators."""
import json
from collections import Counter
from fractions import Fraction as R
from pathlib import Path

HERE=Path(__file__).resolve().parent
S=json.loads((HERE.parents[1]/"coordination"/"WP-0045"/"schedule.json").read_bytes())


def reference_q(case):
    mismatches={"Q.other_caller":["E.caller"],"Q.other_writer":["B.writer"],
                "Q.mixed":["E.caller"],"Q.other_original":["B.origin"],
                "Q.bad_seal":["B.seal"],"Q.unordered":["B.writer"]}.get(case,[])
    absences={"Q.no_caller":["E.caller"],"Q.no_writer":["B.writer"],"Q.mixed":["B.writer"],
              "Q.detached":["B.direct","B.origin"],"Q.bad_seal":["B.direct","B.origin"],
              "Q.unordered":["E.caller"]}.get(case,[])
    atoms=S["atoms"]
    source={k:meta["source"] for k,meta in atoms.items()}
    diagnoses={k:"unresolved" for k in absences}
    for k in mismatches:
        diagnoses[k]={"E.caller":"wrong_origin","B.writer":"unauthorized_writer","B.origin":"wrong_origin",
                      "B.seal":"integrity"}[k]
    values={k:("M" if k in mismatches else "U" if k in absences else "P") for k in atoms}
    groups={g:("M" if any(k.startswith(g+".") for k in mismatches) else
               "U" if any(k.startswith(g+".") for k in absences) else "P") for g in "LIEACB"}
    first=None
    if diagnoses:
        t=min(atoms[k]["at"] for k in diagnoses)
        first={"at":t,"keys":sorted(k for k in diagnoses if atoms[k]["at"]==t)}
    if case=="Q.unordered":
        source["E.caller"]="unobserved"
        first={"at":None,"keys":sorted(diagnoses)}
    result="M" if mismatches else "U" if absences else "P"
    return dict(status=result,values=values,coordinates=groups,custody=result,content="P",
                conflicts=sorted(mismatches),missing=sorted(absences),reason=diagnoses,first=first,source=source)


def predicted(case,x):
    if case=="H.old":
        return {"old_joint":"U","author_genuine_P":0,"reviewer_genuine_P":0,
                "genuine_per_route":2,"direct_edge":"unobserved"}
    if case.startswith(("N.","Q.")):
        return reference_q(case)
    if x["clause"]=="A1":
        k,selected,a=x["k"],x["select"],x["a"]
        if x["mode"]=="literal":
            labels=["stock"]+[f"k{i}" for i in range(1,k+1)]
            inputs=list(range(a,a+k+1))
            readouts=[(labels[-1],inputs[-1]+1)]
        else:
            labels=["stock"]+(["duplicate"] if x["mode"]=="duplicate" else [])
            inputs=[a]*len(labels)
            readouts=[(label,a+1) for label in labels]
        if selected not in dict(readouts):
            return {"status":"M","reason":"invalid_selection","commits":0,"history":[]}
        transition=["u:"+selected,dict(readouts)[selected],"g:"+selected]
        return dict(status="P",calls=[[label,v,v+1] for label,v in zip(labels,inputs)],
                    decoded=[list(e) for e in readouts],selected=selected,transition=transition,
                    commits=int(x["commit"]),history=[transition] if x["commit"] else [])
    if x["clause"]=="A2":
        phases=["raw","repeat","page"]
        n=len(x["raw"])
        bad=[]
        for j,step in enumerate(phases):
            for i,word in enumerate(x[step]):
                if j==0:
                    fault=(int(word,16)&0x7f800000)==0x7f800000
                else:
                    expected="ff800000" if i in x[step+"_block"] else x[phases[j-1]][i]
                    fault=expected!=word
                if fault:
                    bad.append([step,i])
        allowed=sorted(set(range(n))-set(x["page_block"])-set(x["repeat_block"]))
        if not allowed:
            bad.append(["support",-1])
        def ordered(i):
            # Normalise signed zeros, then map IEEE sign/magnitude to ascending integer order.
            word=int(x["page"][i],16)
            if word==0x80000000:
                word=0
            return (~word & 0xffffffff) if word>>31 else word|0x80000000
        return dict(status="M" if bad else "P",first=bad[0] if bad else None,conflicts=bad,allowed=allowed,
                    winner=None if bad else max(allowed,key=ordered),**{s:x[s] for s in phases})
    if x["mode"]=="exact":
        F=set(map(tuple,x["F"]))
        pairs=[(sum(u[j]==v[j] for u in F for v in F),j) for j in range(len(next(iter(F),())))
               if len({u[j] for u in F})>1]
        return dict(status="QUERY" if pairs else "IDENTIFIED" if F else "CONFLICT",
                    action=min(pairs)[1] if pairs else None)
    p=list(map(R,x["p"]))
    used=set(x["used"])
    budget=x["budget"]
    actions={a["id"]:a for a in x["actions"]}
    obs=x["observation"]
    if obs is not None and budget and actions[obs["action"]]["source"] not in used:
        a=actions[obs["action"]]
        probs=[v*R(law[obs["outcome"]]) for v,law in zip(p,a["law"])]
        mass=sum(probs)
        if not mass:
            return dict(status="MODEL_CONFLICT",posterior=None,action=None,gain=None)
        p=[v/mass for v in probs]
        used.add(a["source"])
        budget-=1
    eligible=[]
    if budget:
        for a in actions.values():
            if a["source"] in used:
                continue
            gain=-sum(v*v for v in p)
            for col in zip(*a["law"]):
                masses=[v*R(l) for v,l in zip(p,col)]
                if sum(masses):
                    gain+=sum(m*m for m in masses)/sum(masses)
            if gain>0:
                eligible.append((-gain,a["id"]))
    accept=max(p)>=R(x["threshold"])
    query=eligible and not accept
    return dict(status="ACCEPT" if accept else "QUERY" if query else "UNRESOLVED",posterior=list(map(str,p)),
                action=min(eligible)[1] if query else None,gain=str(-min(eligible)[0]) if query else None)


def compare(expected, rows, official_digests, hashes):
    typed=lambda x:json.dumps(x,sort_keys=True,allow_nan=False,separators=(",",":"))
    assert set(expected)==set(official_digests)=={k for ids in S["rows"].values() for k in ids}
    all_ids=sorted(set(expected)|set(rows)|set(hashes))
    return {k:dict(input_digest=k in hashes and k in official_digests and hashes[k]==official_digests[k],
                   full_row=k in rows and k in expected and typed(rows[k])==typed(expected[k]),
                   differing_fields=sorted(f for f in set(rows.get(k,{}))|set(expected.get(k,{}))
                       if f not in rows.get(k,{}) or f not in expected.get(k,{})
                       or typed(rows[k][f])!=typed(expected[k][f]))) for k in all_ids}

