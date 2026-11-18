"""CPU sensitivity for the documented title<LEVELn> header only. Never runs an OCR engine."""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASTRA = HERE.parent
sys.path.insert(0, str(ASTRA))
from formats import native_page

TITLE = re.compile(r"(<BLOCK>title)<LEVEL(\d+)>(?=\s*\[\s*\d+,\s*\d+,\s*\d+,\s*\d+\s*\]<FORK>)")
SCORER = "1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7"


def hash_bytes(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def store(path, obj):
    path.write_bytes((json.dumps(obj, ensure_ascii=False, indent=2)+"\n").encode())


def critical_transitions(control, trial):
    a = {v["at"]:v for p in control["pages"] for v in p["critical"]}
    changes = []
    for page in trial["pages"]:
        for v in page["critical"]:
            prev = a[v["at"]]
            kind = None
            if prev["correct"] and not v["correct"]:
                kind = "new_error"
            elif not prev["correct"] and v["correct"]:
                kind = "repaired"
            elif not v["correct"]:
                kind = "same_error" if (prev["observed"],prev["flagged"]) == (v["observed"],v["flagged"]) else "changed_error"
            if kind:
                changes.append(dict(kind=kind, at=v["at"], expected=v["expected"], control=prev["observed"],
                                    trial=v["observed"], control_flagged=prev["flagged"], trial_flagged=v["flagged"]))
    return changes


def main(custody, output):
    assert hash_bytes((custody/"score.py").read_bytes()) == SCORER
    sys.path.insert(0,str(custody))
    from score import compare, score
    output.mkdir(parents=True,exist_ok=False)
    summary={}
    for order in ("dev-ab-01","dev-ba-01"):
        root=ASTRA/"evidence"/order
        results = summary[order] = {}
        for case in ("short","dense","boundary"):
            native_folder,=root.glob("[0-9][0-9]-"+case+"-native")
            win_folder,=root.glob("[0-9][0-9]-"+case+"-windows")
            native=read(native_folder/"prediction.json")
            win=read(win_folder/"prediction.json")
            truthpath=custody/"dev"/case/"truth.json"
            manifest=read(truthpath.with_name("rasters.json"))
            assert hash_bytes(truthpath.read_bytes()) == manifest["truth_sha256"]
            truth=read(truthpath)
            assert native["source_sha256"] == win["source_sha256"] == manifest["pdf_sha256"]
            official_native=score(truth,native)
            official_win=score(truth,win)
            assert official_native==read(root/"scores"/(native_folder.name+"-score.json"))
            assert official_win==read(root/"scores"/(win_folder.name+"-score.json"))
            revised=[]
            changes=[]
            for i,page in enumerate(native["pages"],1):
                raw=read(native_folder/f"raw-{i:03d}.json")
                assert page["page"] == raw["page"] == i
                assert raw["rgb_sha256"] == manifest["pages"][i-1]["rgb_sha256"]
                assert raw["source_sha256"] == native["source_sha256"]
                assert native_page(raw["raw_output"],raw["points"]) == {k:page[k] for k in ("text","spans","tables")}
                headers=[x.group(0) for x in TITLE.finditer(raw["raw_output"])]
                adapted=TITLE.sub(r"\1",raw["raw_output"])
                revised_page=dict(page,**native_page(adapted,raw["points"]))
                revised.append(revised_page)
                changes.append(dict(page=i,recognized_headers=headers,added_spans=len(revised_page["spans"])-len(page["spans"]),
                                    original_raw_sha256=hash_bytes(raw["raw_output"].encode()),
                                    official_visible_chars=len(page["text"]),corrected_visible_chars=len(revised_page["text"])))
            prediction=dict(native,pages=revised)
            scored=score(truth,prediction)
            proposed=compare(scored,official_win)
            old=compare(official_native,official_win)
            assert old==read(root/"scores"/"summary.json")["comparisons"][case]
            data=dict(corrected_native_prediction=prediction,corrected_native_score=scored,corrected_comparison=proposed,
                      native_sensitivity_critical_changes=critical_transitions(official_native,scored),
                      windows_vs_official_critical=critical_transitions(official_native,official_win),
                      windows_vs_corrected_critical=critical_transitions(scored,official_win))
            store(output/f"{order}-{case}.json",data)
            results[case]=dict(pages=changes,native_official=official_native["counts"],native_corrected=scored["counts"],
                               windows=official_win["counts"],comparison_official=old,comparison_corrected=proposed,
                               corrected_faults=scored["faults"])
    store(output/"summary.json",summary)


if __name__=="__main__":
    main(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
