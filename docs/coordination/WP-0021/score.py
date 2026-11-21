"""Score source-backed scope bindings after immutable predictions are committed."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

def read(path):return json.loads(path.read_bytes())
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def score(inputs,answers,predictions):
    scores={}
    for mode in ("grid","words"):
        cases={}
        combined=Counter()
        for case,key in answers["cases"].items():
            source=inputs/(case+".json")
            assert digest(source)==key["observationSha256"]
            pages=read(source)["pages"]
            tokens={w["ref"]:w for page in pages for line in page["lines"] for w in line["words"]}
            pred=read(predictions/mode/(case+".json"))
            rows={(row["page"],row["line"]):row for row in pred["rows"]}
            targets={(t["page"],t["line"]):t for t in key["targets"]}
            if len(rows)!=len(pred["rows"]):raise ValueError("duplicate predicted rows")
            extras=sorted(set(rows)-set(targets));counts=Counter();witnesses=[]
            for loc,t in targets.items():
                row=rows.get(loc)
                group="primary" if loc[0]==2 else "initial"
                counts[group+"_targets"]+=1
                if row is None:
                    counts[group+"_missing"]+=1
                    witnesses.append(dict(page=loc[0],line=loc[1],outcome="missing_row"))
                    continue
                scope=row["scope"]; flag=row["flagged"]
                correct_literal=row["literal"]==t["literal"] and row["word_ref"]==t["word_ref"] and tokens[t["word_ref"]]["text"]==t["literal"]
                correct_context=all(row.get(k)==key[k] for k in ("property","unit","property_refs","unit_refs"))
                role=row.get("column_role")
                if not correct_literal:counts[group+"_literal_errors"]+=1
                if group=="primary" and t['missing_third']:counts["rows_with_omitted_third"]+=1
                if scope is None:
                    outcome="abstained" if flag is True else "unflagged_null"
                    if role is not None:counts[group+"_assigned_role_while_abstained"]+=1
                elif scope==t["actual_scope"] and correct_context and correct_literal and role=="Amount" and not flag:
                    outcome="exact"
                else:
                    outcome="flagged_binding" if flag else "silent_wrong"
                counts[group+"_"+outcome]+=1
                if group=="primary":
                    kind="ambiguous" if t["ambiguous"] else "identifiable"
                    counts[kind+"_targets"]+=1
                    counts[kind+"_"+outcome]+=1
                    if t["ambiguous"] and (scope is not None or flag is not True):
                        counts['ambiguous_guesses']+=1
                    if t['actual_scope']=='parent' and not t['ambiguous']:
                        counts['resumed_parent_targets']+=1
                        if outcome=='exact':counts['resumed_parent_exact']+=1
                witnesses.append(dict(page=loc[0],line=loc[1],sourceWord=t["word_ref"],literal=t["literal"],hiddenScope=t["actual_scope"],
                    ambiguous=t["ambiguous"],returnedScope=scope,flagged=flag,columnRole=role,reason=row.get("reason"),
                    literalAndPointerExact=correct_literal,contextAndPointersExact=correct_context,outcome=outcome))
            counts["extra_output_rows"]=len(extras);combined.update(counts)
            cases[case]=dict(counts=dict(counts),extra=extras,rows=witnesses)
        pair=[f for f,v in answers["cases"].items() if v["case"]=="ambiguous"]
        assert len(pair)==2
        left,right=pair
        assert (inputs/(left+".json")).read_bytes()==(inputs/(right+".json")).read_bytes()
        same=read(predictions/mode/(left+".json"))==read(predictions/mode/(right+".json"))
        scores[mode]=dict(totals=dict(combined),cases=cases,identicalPairPredictions=same)
    return scores

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    for p in ("inputs","key","predictions","out"):parser.add_argument("--"+p,type=Path,required=True)
    args=parser.parse_args()
    result=score(args.inputs,read(args.key),args.predictions)
    args.out.write_bytes((json.dumps(result,indent=2)+"\n").encode())
    for m,rec in result.items():print(m,rec["totals"])
