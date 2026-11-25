"""Retain the original helper discrepancy and check the corrected route and scorer in serial."""
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from fixtures import digest, pack, schedule
from score import fetch, validate

AUTHOR = "9502f458a89f48523714cf03ac3d4c7d9cdc69f0"
REVIEW = "9db73813285931ad456c4a83b0a5ec8b99b0b06a"
ORIGINAL_AUTHOR_RAW = "aecab0939edf1945221a0614f0d558131a7556f6"
ORIGINAL_REVIEW_RAW = "e1dbf675b74c22ae616f8b3ae397413fffdf89f9"


def source(rev,area):
    name=f"docs/{area}/WP-0040/policy.py"
    raw=subprocess.check_output(["git","cat-file","blob",rev+":"+name])
    namespace={"__name__":"candidate"}
    exec(compile(raw,name,"exec"),namespace)
    return namespace["evaluate"]


def check(revised,out):
    original=source(REVIEW,"reviews")
    author=source(AUTHOR,"research")
    corrected=source(revised,"reviews")
    rows=[]
    base=dict(status="ADMITTED",names=["A","B"],areas=[1,2],points=[[3,5],[3,5]],
              line=None,dist=[None]*4,read_status="OK",arm="H")
    for q,radius,y,read_status,expected in (
        (0,0,[33,55],"OK","RESOLVED"),(3,0,[3,5],"OK","RESOLVED"),
        (1,0,[4,5],"OK","INCONSISTENT"),(3,1,[4,5],"OK","RESOLVED"),
        (3,1,[4,6],"OK","INCONSISTENT"),(2,1,[None,None],"FAILED","FAILED")):
        v=dict(base,q=q,radius=radius,y=y,read_status=read_status)
        before,reference,after=original(v),author(v),corrected(v)
        assert before["status"]=="FIRST_PASS_SINGLETON" and before["q"]==0
        assert after==reference and after["q"]==q and after["status"]==expected
        validate(["regression","helper_singleton","constructed","H"],[3,5],v,after)
        rows.append(dict(input=v,original_reviewer=before,unchanged_author=reference,revised_reviewer=after))
    saved_a,_=fetch(ORIGINAL_AUTHOR_RAW,"research")
    saved_r,_=fetch(ORIGINAL_REVIEW_RAW,"reviews")
    scheduled,_,_=schedule()
    count=0
    for (label,truth,v),a,b in zip(scheduled,saved_a,saved_r,strict=True):
        fresh=corrected(v)
        assert a["exception"] is None and b["exception"] is None
        assert fresh==a["answer"]==b["answer"],label
        validate(label,truth,v,fresh)
        count+=1
    assert count==1623
    doc=dict(kind="post-review constructed regressions; no physical observations",author=AUTHOR,
             original_reviewer=REVIEW,corrected_reviewer=revised,original_author_raw=ORIGINAL_AUTHOR_RAW,
             original_reviewer_raw=ORIGINAL_REVIEW_RAW,original_cases_rechecked=count,cases=rows)
    data=json.dumps(doc,indent=2,sort_keys=True).encode()+b"\n"
    with Path(out).open("xb") as stream:
        stream.write(data)
    print("Reproduced six original helper discrepancies; corrected six; preserved",count,
          "original semantic results per route; evidence",digest(data))


if __name__=="__main__":
    check(*sys.argv[1:])
