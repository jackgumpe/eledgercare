"""Independent forward-image-binding controls, preserving the first source/checks."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, subprocess, sys, traceback
from unittest import mock
import check_v6 as prior
from probe_v5_controls import BASE, ROOT, load_source

CANDIDATE="6fe4a537eb94fb75776f772e3c37fd5a90101fed"


def modules():
    prior.bound_modules()
    for manifest in ("root-alias-input-identities.json", "v6-forward-input-identities.json"):
        for item in json.loads((BASE/manifest).read_text(encoding="utf-8")):
            raw=(BASE/item["copy"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==item["sha256"]
            assert raw==subprocess.check_output(["git","show",item["commit"]+":"+item["path"]],cwd=ROOT)
    guard=load_source((BASE/"inputs/ownership-v6-forward.py.txt").read_bytes(),BASE/"inputs/ownership-v6-forward.py.txt")
    with mock.patch.dict(sys.modules,{"ownership_v6":guard}):
        runner=load_source((BASE/"inputs/reviewer-v6-forward.py.txt").read_bytes(),BASE/"inputs/reviewer-v6-forward.py.txt")
    assert (BASE/"inputs/reviewer-v6-forward.py.txt").read_bytes()==(BASE/"inputs/reviewer-v6.py.txt").read_bytes(),"Forward source unexpectedly changes runner"
    return guard,runner


def alias_controls(guard,runner):
    old,_=prior.bound_modules()
    finding=json.loads((BASE/"inputs/root-alias-failure/actual-alias-finding.json").read_text(encoding="utf-8"))
    alias=finding["issued_app_alias"]
    actual=finding["actual_running_and_cim_executable"]
    results=[]
    for name,module,expected in (("original-root-alias-failure-reproduced",old,"reject"),
                                 ("alias-and-retained-image-match-cim",guard,"pass"),
                                 ("retained-image-mismatches-cim",guard,"reject"),
                                 ("retained-image-query-failure",guard,"reject")):
        snapshot,root=prior.synthetic(module,runner)
        obs=snapshot["observer"]
        command='"'+alias+'"'+obs["CommandLine"][obs["CommandLine"].index(" -NoProfile"):]
        for row in (obs,snapshot["candidate_and_gpu_processes"][1]):
            row.update(ExecutablePath=actual,CommandLine=command)
        class FakeProcess:
            pid=37576
            returncode=None
            killed=False
            waited=False
            def communicate(self,timeout):
                self.returncode=0
                return json.dumps(dict(observer_pid=self.pid,processes=snapshot["candidate_and_gpu_processes"])).encode(),b""
            def poll(self): return self.returncode
            def kill(self): self.killed=True; self.returncode=-1
            def wait(self,timeout): self.waited=True; return self.returncode
        proc=FakeProcess()
        def fake_run(argv,**kwargs):
            text="\n".join(root["ollama_ps"]) if argv[-1]=="ps" else ("\n".join(snapshot["gpu"]) if any("--query-gpu=" in x for x in argv) else "")
            return subprocess.CompletedProcess(argv,0,text,"")
        row=dict(control=name,expected=expected,issued_alias=alias,actual_cim_image=actual)
        image_mock=mock.patch.object(guard,"popen_image",return_value=r"C:\changed\pwsh.exe" if name=="retained-image-mismatches-cim" else actual,
                                     side_effect=guard.ObservationError("injected retained-image query failure") if name=="retained-image-query-failure" else None)
        with mock.patch.object(module.subprocess,"Popen",return_value=proc), mock.patch.object(module,"popen_creation_utc",return_value=prior.STAMP), mock.patch.object(module.shutil,"which",side_effect=lambda n: alias if n=="pwsh" else snapshot["ollama_executable"]),image_mock:
            try:
                observed=module.collect(ROOT,runner.EXPECTED_GPU_UUID,fake_run)
                if module is guard:
                    assert observed["observer"]["issued_executable"]==alias
                    assert observed["observer"]["retained_process_image"]==actual
                row.update(actual="pass",observer=observed["observer"])
            except module.ObservationError as exc:
                row.update(actual="reject",error=str(exc))
            except Exception:
                row.update(actual="unexpected-exception",error=traceback.format_exc())
        row.update(child_killed=proc.killed,child_waited=proc.waited)
        row["passed"]=row["actual"]==expected
        if name=="retained-image-query-failure": row["passed"]=row["passed"] and proc.killed and proc.waited
        results.append(row)
    return results


def actual(guard,runner,output):
    real_popen=subprocess.Popen
    def capture_popen(argv,*args,**kwargs):
        proc=real_popen(argv,*args,**kwargs)
        if "-EncodedCommand" in argv:
            communicate=proc.communicate
            def capture_communicate(*cargs,**ckwargs):
                stdout,stderr=communicate(*cargs,**ckwargs)
                (output/"observer.stdout.log").write_bytes(stdout)
                (output/"observer.stderr.log").write_bytes(stderr)
                (output/"observer-invocation.json").write_text(json.dumps(dict(argv=argv,pid=proc.pid,returncode=proc.returncode,
                    completed_utc=datetime.now(timezone.utc).isoformat()),indent=2)+"\n",encoding="utf-8")
                return stdout,stderr
            proc.communicate=capture_communicate
        return proc
    with mock.patch.object(guard.subprocess,"Popen",side_effect=capture_popen):
        return prior.observe(guard,runner,output)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    parser.add_argument("--observe",action="store_true")
    args=parser.parse_args()
    output=Path(args.output)
    assert not output.exists(),output
    assert not subprocess.check_output(["git","status","--porcelain"],cwd=ROOT).strip(),"Freeze/commit before execution"
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    guard,runner=modules()
    output.mkdir(parents=True)
    provenance=dict(candidate=CANDIDATE,check_source_commit=head,started_utc=datetime.now(timezone.utc).isoformat(),pid=os.getpid(),argv=sys.argv,actual_observation=args.observe)
    if args.observe:
        passed=actual(guard,runner,output)
    else:
        with mock.patch.object(guard,"popen_image",return_value=r"C:\Program Files\PowerShell\7\pwsh.exe"):
            faults=prior.collector_faults(guard,runner)
        result=dict(old_controls=prior.old_controls(),source_scope=prior.unchanged_checks(),controls=prior.controls(guard,runner),collector_faults=faults,alias_controls=alias_controls(guard,runner))
        passed=all(row["passed"] for key in ("controls","collector_faults","alias_controls") for row in result[key])
        (output/"controls.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
        for key in ("controls","collector_faults","alias_controls"):
            for row in result[key]: print("PASS" if row["passed"] else "FAIL",row["control"],row.get("error",""))
    provenance.update(completed_utc=datetime.now(timezone.utc).isoformat(),passed=passed,exit_code=0 if passed else 1)
    (output/"provenance.json").write_text(json.dumps(provenance,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(provenance))
    return provenance["exit_code"]


if __name__=="__main__": raise SystemExit(main())
