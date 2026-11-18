"""CPU-only negative controls and test of the actual browser success path using archived synthetic output."""
import argparse
import json
import shutil
import time
from pathlib import Path
from tempfile import TemporaryDirectory
import campaign as c
from pins import ReadOnlyGeneration


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("identifier")
    ident=parser.parse_args().identifier
    assert ident.isalnum()
    session=c.WORK / ident
    session.mkdir(parents=True)
    check=session/"pin-fixture"
    check.mkdir()
    (check/"entry").write_text("immutable")
    guard=ReadOnlyGeneration(check)
    blocked={}
    for name, action in (("write",lambda:(check/"entry").write_text("new")),("delete",lambda:(check/"entry").unlink())):
        try:action()
        except PermissionError:blocked[name]=True
        else:raise AssertionError(name)
    (check/"added").touch()
    try:guard.check()
    except RuntimeError:blocked["membership"]=True
    else:raise AssertionError("new file not detected")
    (session/"pin-controls.json").write_text(json.dumps(blocked))
    c.check_ports([4814,5814])
    worker=session/"worker"
    c.prepare_worker(worker)
    old=c.ROOT/"docs/implementation/WP-0012/eld-f4-implementer/rehearsal-003/evidence/attempts/attempt-01a1ea6a-6642-7939-8407-e2aba617b795/output"
    s=c.ROOT/"tests/fixtures/SYN-WO-01-v1-raster300.pdf"
    c.HASH["A"]=c.hashlib.sha256(s.read_bytes()).hexdigest()
    for name in ["envelope.json","raw_output.utf8.bin"]:
        shutil.copyfile(old/name,worker/name)
    (worker/"run_worker.py").write_text("""
import json, shutil, sys
from pathlib import Path
req=Path(sys.argv[-1])
d=json.loads(req.read_bytes())
src=Path(__file__).parent
out=req.parent/"output"
e=json.loads((src/"envelope.json").read_bytes())
assert e["input"]["sha256"]==d["expected_input_sha256"]
e.update({k:d[k] for k in ["document_id","attempt_id","job_id","fencing_token"]})
e["provenance"]["worker_source_sha256"]=d["expected_worker_source_sha256"]
e["diagnostics"]={"cpu_fixture_replay":True}
shutil.copyfile(src/"raw_output.utf8.bin",out/"raw_output.utf8.bin")
(out/"envelope.json").write_text(json.dumps(e))
""")
    ui=c.begin(["node",c.HERE/"ui.mjs"],session,"ui",c.os.environ)
    try:
        c.run_phase(session,worker,{"A":s},"stock",False,time.monotonic()+65,replay=True)
    finally:
        c.end(ui)
        c.check_ports([4814,5814])

if __name__=="__main__":
    main()
