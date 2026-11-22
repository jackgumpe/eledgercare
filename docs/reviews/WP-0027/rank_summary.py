"""Reduce reviewer replay; never treat a silent posting as evidence of a wrong owner."""
from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import SCRATCH,save,sha

def summarize(source):
    result = {}
    for arm,a in source["arms"].items():
        fields = {f:Counter() for f in ("owner","unit","column","subtotal_status")}
        sample = {}
        same = Counter()
        ranking = Counter()
        for p,summary in a["pairs"].items():
            twins = sorted((r for r in a["rows"] if r["pair"]==p),key=lambda r:r["binder"])
            assert len(twins)==2
            ids = set(summary["deltas"])
            assert ids=={r["binder"] for r in twins}
            leaves = []
            for r in twins:
                attempts = r["attempts"]
                if not attempts:
                    leaves.append(None)
                    continue
                att, = attempts
                for f,value in att["fields"].items():
                    expected = value["expected"]
                    d = value["delta"]
                    metric = ("N/A" if expected is None else "unscorable" if d is None else
                              "correct" if d>0 else "tie" if d==0 else "wrong")
                    fields[f][metric]+=1
                owners = att["fields"]["owner"]["scores"]
                leaves.append(max(owners,key=owners.get))
            same["equal_final_inputs"] += twins[0]["final_inputs"]==twins[1]["final_inputs"]
            same["equal_registry"] += twins[0]["registry"]==twins[1]["registry"]
            same["unequal_final_entry_matrices"] += twins[0]["window_entry_matrix"][-1]!=twins[1]["window_entry_matrix"][-1]
            if all(leaves):
                reads = [next(d for d in r["reads"] if d["field"]=="owner") for r in twins]
                same["identical_owner_query"]+=reads[0]["query_sha"]==reads[1]["query_sha"]
                same["different_owner_responses"]+=reads[0]["response_sha"]!=reads[1]["response_sha"]
                same["same_owner_leader"]+=leaves[0]==leaves[1]
                ranking.update(leaves)
            stratum = twins[0]["stratum"]
            if stratum not in sample:
                sample[stratum]={"pair":p,"leads":leaves,"binders":ids and sorted(ids),
                                 "window1_ledger":[[e["literal"] for e in r["events"] if e["event"]=="OPEN_LEDGER" and e["ptr"][0]==1] for r in twins],
                                 "final_native_targets":[[e["literal"] for e in r["events"] if e["event"]=="TARGET"] for r in twins],
                                 "final_ordinal":len(twins[0]["window_entry_matrix"]),"deltas":summary["deltas"]}
        result[arm]={"fields_answerable":fields,"same_inputs_and_internal_signals":same,
                     "leaders":ranking,"selected_decisions":a["selected_decisions"],
                     "pair_counts":a["counts"],"representatives":sample}
    return result

if __name__=="__main__":
    source=(SCRATCH/sys.argv[1]).read_bytes()
    save(SCRATCH/sys.argv[2],{"input_sha256":sha(source),"arms":summarize(json.loads(source))})

