"""Replay the candidate runner's archival CPU cases in reviewer-owned scratch and check the real Windows child environment."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

REPO=Path(__file__).resolve().parents[3]
OWNED=Path("C:/Users/jackg/eLedgerCare-Speed/WP-0025/review")


def check(tree,expected):
    sys.path.insert(0,str(tree/"docs/research/WP-0025/runner"))
    import preflight
    import process
    process.clean_source(expected)
    archive=REPO/"docs/reviews/WP-0024/h0-r1.zip"
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==process.ARCHIVE_SHA
    with TemporaryDirectory(dir=OWNED) as tmp, ZipFile(archive) as z:
        tmp=Path(tmp)
        cases=[(p,None) for p in ["P1","P2"]]+[("P1",f) for f in ("wrong_order","wrong_prompt","wrong_environment",
            "unverified_eos","guard_mismatch","missing_hidden")]
        results=[preflight.exercise(z,tmp,p,f) for p,f in cases]
        sys.path.insert(0,str(tree/"docs/coordination/WP-0025"))
        from supervise import environment
        target=tmp/"empty-worker"
        env=environment(target)
        pin=hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()
        plan=dict(environment=env,q0_python=sys.executable,executable_sha256=pin,interpreter_flags=["-I","-B"])
        plan_file=tmp/"cpu-plan.json"
        plan_file.write_text(json.dumps(plan),encoding="utf8")
        program=("import sys,json; from pathlib import Path; sys.path.insert(0,sys.argv[1]); import process as p; "
                 "print(len(p.check_environment(Path(sys.argv[2]),json.loads(Path(sys.argv[3]).read_bytes())))); "
                 "assert 'torch' not in sys.modules")
        attrs=subprocess.check_output([sys.executable,"-I","-B","-c",program,str(tree/"docs/research/WP-0025/runner"),
                                      str(target),str(plan_file)],cwd=target,env=env,text=True)
        assert int(attrs)>30 and "torch" not in sys.modules
    return {"candidate":expected,"real_child_environment_fields":int(attrs),"archival_cpu_cases":results,
            "torch_imported":False,"runtime_model_calls":0,"board_use":False}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("candidate_tree",type=Path)
    p.add_argument("candidate_sha")
    p.add_argument("output",type=Path)
    a=p.parse_args()
    result=check(a.candidate_tree.resolve(),a.candidate_sha)
    with a.output.open("x",encoding="utf8",newline="\n") as f:
        f.write(json.dumps(result,indent=2)+"\n")
