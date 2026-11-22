"""CPU-only checks of the exact candidate; no device query, board lock or native worker call."""
import ast
import copy
import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit import BASE, KEY, Q0, ROOT, SCRATCH, SENSOR, WORKER, blob, initialize, save, sha

CANDIDATE="5014124e485d5ce89b9191e23458f12cc178bdcd"
BIND="fc42ba82075e10114855b3ac648cff7a5c562466"
P="docs/coordination/WP-0029/"
H="historical_w0_through_eos"

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def preflight():
    rb,pb=(blob(BIND,P+"cedar-r1-"+name+".json") for name in ("release","plan"))
    release,plan=map(json.loads,(rb,pb))
    assert sha(rb)=="3b1f724bfd356f03411430a7ad522b4d2f3b9459feb3b0ed26fd15f7c4945eec"
    assert sha(pb)==release["plan_sha256"]=="16ffe4a8b565a9920ebbb80cbca3876fb10c18cc4af3a4b323a189e571a495ca"
    assert Path(release["plan"]).read_bytes()==pb
    root=Path(release["worktree"])
    assert release["candidate"]==CANDIDATE and root==ROOT.parent/"w029-device"
    assert (release["worker_revision"],release["sensor_revision"])==(WORKER,SENSOR)
    assert subprocess.check_output(["git","-C",root,"rev-parse","HEAD"],text=True).strip()==CANDIDATE
    assert not subprocess.check_output(["git","-C",root,"status","--porcelain","--untracked-files=all"])
    for f,expected in release["source_files"].items():
        assert sha((root/f).read_bytes())==expected
    assert {(root/P/f).read_bytes() for f in ("cedar_guard.py","cedar_plan.py","cedar_worker.py")}=={
        blob(CANDIDATE,P+f) for f in ("cedar_guard.py","cedar_plan.py","cedar_worker.py")}
    sys.path.insert(0,str(root/P))
    import cedar_guard
    c=cedar_guard.c
    assert c.source_pins()==release["source_files"]
    actual=c.execution_fields()
    assert set(plan)==set(actual)|{"candidate","environment"} and all(plan[k]==v for k,v in actual.items())
    assert len(plan["calls"])==1 and plan["calls"][0]["ordinal"]==2 and plan["calls"][0]["retain_hidden"]
    assert plan["calls"][0]["mode"]=="H" and plan["ordered_rgb_key"]==KEY
    assert len(plan["prompt_token_ids"])==827 and plan[H]==c.WARM_TOKENS
    assert plan["runner_sha256"]==sha(blob(WORKER,"docs/research/WP-0026/worker.py"))
    assert plan["sensor_tree"]==subprocess.check_output(["git","rev-parse",SENSOR+":docs/research/WP-0024/sensor"],text=True).strip()
    # Exercise the exact closure guarding the gap between the stock warm-up and the sole scored read.
    src=blob(CANDIDATE,P+"cedar_worker.py")
    verify,=[node for node in ast.walk(ast.parse(src)) if isinstance(node,ast.FunctionDef) and node.name=="verify_w0"]
    wrapped={"c":c}
    exec(compile(ast.Module(body=[verify],type_ignores=[]),"<bound warmup guard>","exec"),wrapped)
    baseline={"success":True,"emitted":62,"through_eos_sha256":c.WARM_TOKENS}
    for field,value in (("success",False),("emitted",61),("through_eos_sha256","0"*64),(None,None)):
        row=dict(baseline)
        if field: row[field]=value
        wrapped["original_warmup"]=lambda:row
        try: assert wrapped["verify_w0"]()==baseline
        except ValueError: assert field
        else: assert field is None
    # The candidate monitor checks ceiling inclusively and fails closed on faulty telemetry.
    board={}
    with TemporaryDirectory(dir=SCRATCH) as directory:
        tmp=Path(directory)
        for used in (12500,12501,None):
            stop,fault=threading.Event(),threading.Event()
            failures=[]
            def sample():
                if used is None: raise OSError("simulated telemetry failure")
                stop.set()
                return {"used_mib":used}
            with patch.object(c.guard,"device",sample):
                cedar_guard.monitor(stop,fault,failures,tmp/(str(used)+".jsonl"))
            assert fault.is_set()==bool(failures)==(used!=12500)
            board[str(used)]={"stopped":fault.is_set(),"failures":failures}
        # A disposable named Windows job is real. Its only child goes to sleep
        # after joining; close the only handle and observe that same child exit.
        j=c.guard.winjob
        name="Local\\eLedgerCare-WP0029-CPU-review-"+uuid.uuid4().hex
        marker=tmp/"joined"
        code=("import sys,time;from pathlib import Path;sys.path.insert(0,sys.argv[1]);"
              "import winjob;winjob.join(sys.argv[2]);Path(sys.argv[3]).write_text('joined');time.sleep(30);Path(sys.argv[3]+'.natural').touch()")
        handle=j.create(name)
        with subprocess.Popen([sys.executable,"-I","-B","-c",code,str(root/"qualification/baseline"),name,str(marker)]) as child:
            try:
                end=time.monotonic()+6
                while not marker.exists() and child.poll() is None and time.monotonic()<end: time.sleep(.01)
                assert marker.is_file() and child.poll() is None
            finally:
                j.close(handle)
            rc=child.wait(timeout=5)
        assert not (tmp/'joined.natural').exists()
    # Inspect critical order in exact sources, using AST offsets independent of source formatting.
    guard_src=blob(CANDIDATE,P+"cedar_guard.py").decode()
    names=["with g.exclusive(g.LOCK)","c.LEASE.mkdir(","state = g.ownership()","c.OUTPUT.mkdir(","g.winjob.create(",
           "start = time.monotonic_ns()","deadline = start + 180_000_000_000","timer.start()","child = subprocess.Popen("]
    assert [guard_src.index(s) for s in names]==sorted(guard_src.index(s) for s in names)
    assert guard_src.count("subprocess.Popen(")==1 and "threading.Timer((deadline - time.monotonic_ns()) / 1e9, close_job" in guard_src
    assert "state[\"device\"][\"free_mib\"] >= 12000" in guard_src and "req(not unknown" in guard_src
    assert src.index(b"winjob.join(job_name)")<src.index(b"import cedar_plan as c")<src.index(b"import worker")<src.index(b"worker.conduct(")
    assert not c.LEASE.exists() and not c.OUTPUT.exists()
    assert not any(k in sys.modules for k in ("torch","native","worker"))
    return {"decision":"admit exact frozen launch subject to operator and coordinator's live checks",
            "candidate":CANDIDATE,"binding_revision":BIND,"release_sha256":sha(rb),"plan_sha256":sha(pb),
            "bound_source_files":len(release["source_files"]),"old_sensor_tree":plan["sensor_tree"],
            "worker_sha256":plan["runner_sha256"],"png_rgb_validation":"all six exact images",
            "warmup_tests":{"accepted":1,"rejected":3},"ceiling_and_failure_tests":board,
            "isolated_windows_job":{"joined_then_stopped_on_last_handle_close":True,"child_exit":rc},
            "timer_start_before_popen":True,"global_nonblocking_host_lock":str(c.guard.LOCK),
            "unissued_lease_and_run_dirs":True,"hardware_calls":0,
            "limits":{"seconds_from_launch":180,"free_mib_floor":12000,"used_mib_sample_ceiling":12500,
                      "native_loads":1,"native_calls":2,"retries":0}}

if __name__=="__main__":
    initialize()
    save(sys.argv[1],preflight())
