"""Missing-data and contradiction tests. All fixtures and outputs are review-local CPU data."""
import copy
import json
from pathlib import Path
import subprocess
import sys


def child(argv):
    p = subprocess.run([sys.executable, "-B", *map(str, argv)], capture_output=True, timeout=60)
    if p.returncode:
        return {"exit":p.returncode,"error":p.stderr.decode(errors="replace").splitlines()[-1]}
    return json.loads(p.stdout)


def main(src, work):
    work.mkdir(parents=True, exist_ok=True)
    stock = src / "stock.py"
    contract = {"vocab":[0,1,2],"page":2,"eos":1,"cap":4,"order":35,"window":1024,"prompt":[2],
                "histories":[[0]],"raw_words":[["40000000","00000000","3f800000"]],
                "document":{"ids":[0],"terminal":"stop"}}
    case = {"contract":contract,"document":contract["document"],"injections":[]}
    for name, value in (("case",case),("contract",contract)):
        (work/(name+".json")).write_text(json.dumps(value))
    e = child([stock,"capture",work/"case.json"])
    out = []
    def score(name, data):
        path = work/"probe.json"
        path.write_text(json.dumps(data))
        got=child([stock,"score",path,work/"contract.json"])
        out.append({"test":name,**{k:got.get(k) for k in ("verdict","first_divergent_phase","conflict_keys","missing_keys","exit","error") if k in got}})

    score("complete synthetic reference", e)
    for field, value in (("seq",None),("bytes",0),("receiver",None),("frame",None),("source",None)):
        changed=copy.deepcopy(e)
        for event in changed["events"]:
            if field=="receiver":
                event.pop(field,None)
            else:
                event[field]=value
        score("independent alteration " + field,changed)
    changed=copy.deepcopy(e)
    changed["rows"][0]["phases"]["C1_post_rep"]=None
    changed["rows"][0]["y"]=2
    score("missing intermediate and wrong selection",changed)
    changed=copy.deepcopy(e)
    changed["events"].append(dict(e["events"][0],id="extra"))
    score("extra unreferenced observed event",changed)
    # Test the same lower-level graph validator invoked by score-native. A missing
    # tensor extent must never earn complete evidence for that specific node.
    sys.path.insert(0,str(src))
    from native_score import Snapshot
    from scorer import Findings
    f=Findings()
    graph={"root":{"ref":0},"nodes":[{"entries":[["value",{"ref":1}]]},
           {"type":"Tensor","dtype":"torch.float32","shape":[2]}]}
    try:
        Snapshot(graph).check(None,0,"B",f)
        out.append({"test":"native tensor shape but no byte extent, backing or artifact",
                    "conflicts":f.conflicts,"missing":f.missing})
    except (TypeError,KeyError,ValueError) as ex:
        out.append({"test":"native tensor shape but no byte extent, backing or artifact","error":str(ex)})
    print(json.dumps(out,indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]),Path(sys.argv[2]))
