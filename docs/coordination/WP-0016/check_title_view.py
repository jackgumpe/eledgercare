"""Apply the original title rule imported directly from the published module, then spawn frozen score.py."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys

REPO = Path(__file__).resolve().parents[3]
REL = "docs/research/WP-0015/astra/sensitivity-title-level/rescore.py"
TITLE_REV = "0186467670074761a777602d77b53deff3451300"
EVAL = REPO / "docs/evaluation/WP-0015/score.py"
SCORER = "1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7"


def read(p):
    return json.loads(p.read_bytes())


def run(doc, truth, out):
    original = subprocess.check_output(["git","show",TITLE_REV+":"+REL],cwd=REPO)
    assert original == (REPO/REL).read_bytes()
    assert hashlib.sha256(EVAL.read_bytes()).hexdigest() == SCORER
    mod = runpy.run_path(str(REPO/REL))
    rule, project = mod["TITLE"], mod["native_page"]
    pred = read(doc/"prediction.json")
    result = []
    for i,p in enumerate(pred["pages"],1):
        raw = read(doc/f"raw-{i:03d}.json")
        assert raw["source_sha256"] == p["source_sha256"] == pred["source_sha256"]
        assert raw["page"] == p["page"] == i
        text, pts = raw["raw_output"], raw["points"]
        assert all(p[k] == v for k,v in project(text, pts).items())
        result.append(dict(p,**project(rule.sub(r"\1",text),pts)))
    out.mkdir(parents=True, exist_ok=False)
    fix = out/"prediction.json"
    fix.write_text(json.dumps(dict(pred,pages=result),ensure_ascii=False),encoding="utf8")
    subprocess.run([sys.executable,"-I","-B",str(EVAL),str(truth),str(fix),"--out",str(out/"score.json")],check=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    for arg in ("doc","truth","out"):
        ap.add_argument(arg,type=Path)
    args = ap.parse_args()
    run(args.doc,args.truth,args.out)
