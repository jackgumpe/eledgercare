"""Evaluate frozen development predictions after inference; no access from engine."""
import argparse
import json
import hashlib
import sys
from pathlib import Path

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load(p):
    return json.loads(p.read_bytes())

def main():
    p=argparse.ArgumentParser()
    p.add_argument("run",type=Path)
    p.add_argument("custody",type=Path)
    p.add_argument("out",type=Path)
    a=p.parse_args()
    scorefile=a.custody/"score.py"
    assert sha(scorefile)=="1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7"
    sys.path.insert(0,str(a.custody.resolve()))
    from score import score,compare
    a.out.mkdir(exist_ok=True,parents=True)
    cases=[]
    by={}
    for folder in sorted(a.run.glob("[0-9][0-9]-*")):
        tm=folder/"timing.json"
        if not tm.exists():
            continue
        timing=load(tm)
        req=timing["request"]
        if req["warmup"]:
            continue
        pred=folder/"prediction.json"
        assert sha(pred)==timing["prediction_sha256"]
        manifest=load(a.custody/"dev"/req["label"]/"rasters.json")
        truthfile=a.custody/"dev"/req["label"]/"truth.json"
        assert sha(truthfile)==manifest["truth_sha256"]
        score_obj=score(load(truthfile),load(pred))
        summary=dict(label=req["label"],mode=req["mode"],elapsed_s=timing["elapsed_s"],
             first_page_s=timing["first_page_s"],complete=score_obj["packet_complete"],counts=score_obj["counts"],
             faults=score_obj["faults"],prediction_sha256=sha(pred),pages=[])
        by[(req["label"],req["mode"])]=score_obj
        for i, expect in enumerate(manifest["pages"],1):
            raw=load(folder/f"raw-{i:03d}.json")
            assert raw["rgb_sha256"]==expect["rgb_sha256"] and raw["source_sha256"]==req["sha256"] and raw["page"]==i
            projected=load(folder/f"page-{i:03d}.json")
            assert projected==load(pred)["pages"][i-1]
            summary["pages"].append(dict(page=i,native_tokens=raw.get("token_count"),words=raw.get("word_count"),
                    token_classes=raw.get("token_classes"),text_chars=len(projected["text"]),raster=raw["rgb_sha256"]))
        (a.out/(folder.name+"-score.json")).write_text(json.dumps(score_obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        cases.append(summary)
    comparisons={k:compare(base,by[k,"windows"]) for (k,m),base in by.items() if m=="native" and (k,"windows") in by}
    final=dict(scorer_sha256=sha(scorefile),cases=cases,comparisons=comparisons)
    (a.out/"summary.json").write_text(json.dumps(final,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps([dict(case=c["label"],mode=c["mode"],s=round(c["elapsed_s"],4),counts=c["counts"],faults=c["faults"]) for c in cases]))

if __name__=="__main__":
    main()
