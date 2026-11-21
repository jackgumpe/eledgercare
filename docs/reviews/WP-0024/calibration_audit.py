"""Compare published calibration classification with independent custody adjudication on identical inputs."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from matrix_audit import isolated_environment,materialize


PRIOR="ae5b78b99d85619e8faca4550ed2ed0ee2fd060d"
FIX="998e21e11257d26a868d54cf593cb56bcd18d4eb"


def blob_at(rev,path):
    return subprocess.check_output(["git","show",f"{rev}:{path}"])


def classify(rev):
    materialize(rev)
    path="docs/research/WP-0024/probe/run.py"
    code=blob_at(rev,path)
    module={"__name__":"reviewed_calibration","__file__":path}
    exec(compile(code,rev+":"+path,"exec"),module)
    return module["classification"], hashlib.sha256(code).hexdigest()


def test(scorer):
    isolated_environment()
    ns={}
    code=blob_at(scorer,"docs/fixtures/WP-0024/score.py")
    exec(compile(code,"custody/score.py","exec"),ns)
    a,ah=classify(PRIOR)
    b,bh=classify(FIX)
    truth=dict(ambiguous=False,stratum="T1",owner="Birch",unit="Unit8",column="Ref",subtotal_status=None)
    posting={k:v for k,v in truth.items() if k not in ("ambiguous","stratum")}|{"type":"Posting"}
    abstention={"type":"ABSTAIN","reason":"zero_state_tie"}
    cases=[
        ("exact_post",truth,posting),
        ("same_case",truth,posting|{"owner":"BIRCH"}),
        ("same_entity_and_spaces",truth|{"owner":"Birch & Creek"},posting|{"owner":"  BIRCH &amp;   Creek  "}),
        ("different_owner",truth,posting|{"owner":"Birch South"}),
        ("literal_markup_differs",truth,posting|{"owner":"<b>Birch</b>"}),
        ("nonempty_inapplicable_status",truth,posting|{"subtotal_status":"BALANCED"}),
        ("unobserved_required_status",truth|{"stratum":"T3","subtotal_status":"UNBALANCED"},posting),
        ("answerable_abstention",truth,abstention),
        ("undecidable_posting",truth|{"ambiguous":True,"stratum":"T4"},posting),
        ("undecidable_abstention",truth|{"ambiguous":True,"stratum":"T4"},abstention)]
    rows={}
    for label,k,p in cases:
        expected=ns["assessment"](p,k)
        target=(expected["full"],bool(expected["silent"]),p["type"]=="Posting")
        old,new=a(p,k),b(p,k)
        assert new==target,(label,new,target)
        rows[label]={"old":old,"new":new,"custody":target}
    different=[key for key,row in rows.items() if row["old"]!=row["custody"]]
    assert different==["same_case","same_entity_and_spaces"]
    return {"old_probe":PRIOR,"new_probe":FIX,"custody_scorer":scorer,"old_run_py_sha256":ah,
            "new_run_py_sha256":bh,"score_py_sha256":hashlib.sha256(code).hexdigest(),
            "triple_order":["full_correct","silent_error","posted"],"old_disagreements":different,"cases":rows}


if __name__=="__main__":
    assert sys.flags.isolated and sys.dont_write_bytecode
    print(json.dumps(test(sys.argv[1]),indent=2))

