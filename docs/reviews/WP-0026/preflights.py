"""Replay inherited independent mathematical, parser, scorer and attribution checks in packet scratch."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_common import BASE, HIST, ROOT, SCRATCH, blob, cpu, save, sha

PROBE = "7db67283a4ffd3e7a20bb8d80499572cc7118c71"
SCORER = "e6c1abaed36a379780084be826c5fd0afaf3132b"
CASES = ("matrix","calibration","w1","scorer","parser","probe")

def redirected(file):
    raw = blob(BASE,"docs/reviews/WP-0024/"+file)
    # Redirect the previous reviewer's *scratch* constant while preserving each check and reviewed source.
    old = b"C:/Users/jackg/eLedgerCare-Speed/WP-0024/review/cpu"
    src = raw.replace(old,SCRATCH.as_posix().encode("ascii"))
    scope = {"__file__":str(HIST/file),"__name__":"independent_replay"}
    exec(compile(src,file,"exec"),scope)
    if "isolated_environment" in scope:
        scope["isolated_environment"] = cpu
    return scope,sha(raw)

def run(case):
    cpu()
    workspace = SCRATCH/PROBE
    workspace.mkdir(exist_ok=True)
    for f in ("online","matrix","views","run","preflight"):
        raw = blob(PROBE,"docs/research/WP-0024/probe/"+f+".py")
        assert raw == blob(BASE,"docs/research/WP-0024/probe/"+f+".py")
        path = workspace/(f+".py")
        if not path.exists():
            path.write_bytes(raw)
        assert path.read_bytes() == raw
    for f in ("score","check_score"):
        assert blob(SCORER,"docs/fixtures/WP-0024/"+f+".py") == blob(BASE,"docs/fixtures/WP-0024/"+f+".py")
    if case == "probe":
        source = workspace/"preflight.py"
        output = json.loads(subprocess.check_output([sys.executable,"-I","-B",str(source)],cwd=ROOT))
        return {"check":case,"source_sha256":sha(source.read_bytes()),"result":output}
    file,fn,args = {"matrix":("matrix_audit.py","audit",[PROBE]),"w1":("w1_integration.py","run",[PROBE,SCORER]),
                    "calibration":("calibration_audit.py","test",[SCORER,PROBE]),
                    "scorer":("score_audit.py","source_test",[SCORER]),"parser":("stage_a.py","main",[])}[case]
    program,source_hash = redirected(file)
    return {"check":case,"historical_auditor_sha256":source_hash,"result":program[fn](*args)}

if __name__ == "__main__":
    cpu()
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output",type=Path)
    cli.add_argument("--case",choices=CASES)
    a = cli.parse_args()
    if a.case:
        save(a.output,run(a.case))
    else:
        import tempfile
        results = {}
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            for case in CASES:
                path = Path(tmp)/(case+".json")
                subprocess.run([sys.executable,"-I","-B",__file__,str(path),"--case",case],check=True,cwd=ROOT)
                results[case] = json.loads(path.read_bytes())
        save(a.output,{"probe_revision":PROBE,"scorer_revision":SCORER,"scratch":str(SCRATCH),
                       "synthetic_or_archived_inputs_only":True,"results":results})
