"""Independent CPU original-refusal controls; no service, GPU command or model import."""
from pathlib import Path
import argparse, ast, copy, hashlib, json, subprocess, types
from unittest import mock
BASE=Path(__file__).resolve().parents[1]
ROOT=Path(subprocess.check_output(["git","rev-parse","--show-toplevel"],text=True).strip())

def load_source(raw,filename):
    tree=ast.parse(raw.decode("utf-8"))
    forbidden={"torch","transformers","safetensors","pypdfium2","PIL","qualification","research","evaluation"}
    for node in ast.walk(tree):
        if isinstance(node,ast.Import): names=[a.name for a in node.names]
        elif isinstance(node,ast.ImportFrom): names=[node.module or ""]
        else: continue
        assert not any(n.split(".")[0] in forbidden for n in names),names
    module=types.ModuleType("independent_bound_reviewer")
    module.__file__=str(filename)
    exec(compile(raw,str(filename),"exec"),module.__dict__)
    return module

def old_controls():
    raw=(BASE/"inputs/reviewer-v5.py.txt").read_bytes()
    old=load_source(raw,BASE/"inputs/reviewer-v5.py.txt")
    original=json.loads((BASE/"inputs/original-ownership-before.json").read_text(encoding="utf-8"))
    idle=next(row for row in original["candidate_and_gpu_processes"] if row["ProcessId"]==3892)
    tree=ast.parse(raw.decode("utf-8"))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="collect_live_ownership_snapshot")
    assignment=next(n for n in fn.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=="ps_procs")
    query=ast.literal_eval(assignment.value)
    observer={"ProcessId":37576,"Name":"pwsh.exe","ExecutablePath":"C:/Program Files/WindowsApps/Microsoft.PowerShell_7.7.0.0_x64__8wekyb3d8bbwe/pwsh.exe","CommandLine":"pwsh -NoProfile -Command "+query}
    results=[]
    for label,row in (("idle-server",idle),("own-query-observer",observer)):
        snapshot={"apps":[],"candidate_and_gpu_processes":[row],"ollama_ps":original["ollama_ps"]}
        try:
            decision=old.evaluate_gpu_and_model_ownership(snapshot,pre_lease_blobs={"root":original},self_pid=987654)
            raise AssertionError(f"Expected original {label} refusal, got {decision}")
        except old.CompetingModelOwnershipError as exc:
            results.append({"control":label,"reproduced":True,"error":str(exc),"snapshot":snapshot})
    def fake_run(argv,**kwargs):
        if argv[0]=="pwsh": return subprocess.CompletedProcess(argv,7,stdout="",stderr="injected observer failure")
        return subprocess.CompletedProcess(argv,0,stdout="",stderr="")
    with mock.patch.object(old,"run_cmd",side_effect=fake_run), mock.patch.object(old.shutil,"which",return_value=None):
        failed=old.collect_live_ownership_snapshot(ROOT)
    decision=old.evaluate_gpu_and_model_ownership(failed,self_pid=987654)
    assert decision["sole_model_job_verified"] is True
    results.append({"control":"failed-process-observation","original_fail_open_reproduced":True,"snapshot":failed,"decision":decision})
    return {"source_sha256":hashlib.sha256(raw).hexdigest(),"controls":results,"actual_process_observation":False,"gpu_commands":False,"model_imports":False}

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    output=Path(args.output)
    assert not output.exists(),output
    result=old_controls()
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("PASS: two original refusals and failed-observation fail-open reproduced on CPU")
