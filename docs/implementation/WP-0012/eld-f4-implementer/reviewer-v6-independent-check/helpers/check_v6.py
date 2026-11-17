"""Independent source-bound v6 controls; only --observe issues read-only queries."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, ast, base64, copy, hashlib, json, os, subprocess, sys, traceback
from unittest import mock
from probe_v5_controls import BASE, ROOT, load_source, old_controls

CANDIDATE = "651146fa704fe0df262057540587399277ff6a23"
NOW = datetime(2026, 11, 17, 18, 0, tzinfo=timezone.utc)
STAMP = NOW.isoformat()


def bound_modules():
    for manifest in ("input-identities.json", "v6-input-identities.json"):
        for item in json.loads((BASE / manifest).read_text(encoding="utf-8")):
            raw = (BASE / item["copy"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == item["sha256"]
            assert raw == subprocess.check_output(["git", "show", item["commit"] + ":" + item["path"]], cwd=ROOT)
    guard = load_source((BASE / "inputs/ownership-v6.py.txt").read_bytes(), BASE / "inputs/ownership-v6.py.txt")
    with mock.patch.dict(sys.modules, {"ownership_v6": guard}):
        runner = load_source((BASE / "inputs/reviewer-v6.py.txt").read_bytes(), BASE / "inputs/reviewer-v6.py.txt")
    return guard, runner


def root_input():
    original = json.loads((BASE / "inputs/original-ownership-before.json").read_text(encoding="utf-8"))
    idle = copy.deepcopy(next(r for r in original["candidate_and_gpu_processes"] if r["ProcessId"] == 3892))
    original["accounted_idle_ollama"] = [{k: idle[k] for k in ("ProcessId", "CreationDate", "Name", "ExecutablePath")}]
    return original, idle


def synthetic(guard, runner):
    root, idle = root_input()
    script = guard.observer_query([])
    command = '"C:\\Program Files\\PowerShell\\7\\pwsh.exe" -NoProfile -EncodedCommand ' + base64.b64encode(script.encode("utf-16le")).decode()
    observer = dict(ProcessId=37576, Name="pwsh.exe", ExecutablePath=r"C:\Program Files\PowerShell\7\pwsh.exe",
                    CreationDate=STAMP, CommandLine=command, query_sha256=hashlib.sha256(script.encode()).hexdigest())
    snapshot = dict(gpu_exit=0, gpu=[f"2026/11/17 13:00:00, {runner.EXPECTED_GPU_UUID}, NVIDIA GeForce RTX 5070 Ti, 621.01, 12.0, 16303, 1000, 15303"],
                    apps_exit=0, apps=[], processes_exit=0, candidate_and_gpu_processes=[idle, copy.deepcopy(observer)],
                    observer=observer, ollama_ps_exit=0, ollama_ps=root["ollama_ps"], ollama_executable=idle["ExecutablePath"],
                    observed_utc=STAMP, ollama_observed_utc=STAMP)
    return snapshot, root


def evaluate(guard, runner, snapshot, root):
    return guard.evaluate(snapshot, pre_lease_blobs={"root": root}, self_pid=987654,
                          expected_gpu_uuid=runner.EXPECTED_GPU_UUID, model_server_re=runner.MODEL_SERVER_BASENAME_RE,
                          python_re=runner.PYTHON_BASENAME_RE, workload_re=runner.MODEL_WORKLOAD_TOKEN_RE,
                          benign_names=runner.BENIGN_WDDM_DESKTOP_BASENAMES, now_utc=NOW)


def controls(guard, runner):
    results = []
    def case(name, change, expect_pass=False):
        snapshot, root = synthetic(guard, runner)
        change(snapshot, root)
        row = dict(control=name, expected="pass" if expect_pass else "reject", snapshot=snapshot, root=root)
        try:
            row["decision"] = evaluate(guard, runner, snapshot, root)
            row["actual"] = "pass"
        except guard.ObservationError as exc:
            row.update(actual="reject", error=str(exc))
        except Exception:
            row.update(actual="unexpected-exception", error=traceback.format_exc())
        row["passed"] = row["actual"] == row["expected"]
        results.append(row)
    def current(s): return s["candidate_and_gpu_processes"][0]
    def observer(s): return s["candidate_and_gpu_processes"][1]
    def set_current(key, value): return lambda s, r: current(s).__setitem__(key, value)
    def set_snapshot(key, value): return lambda s, r: s.__setitem__(key, value)
    def add_process(name, command, pid=42000):
        return lambda s, r: s["candidate_and_gpu_processes"].append(dict(ProcessId=pid, Name=name,
            ExecutablePath="C:\\tools\\"+name, CreationDate=STAMP, CommandLine=command))
    def gpu(s, r, pid, path):
        s["apps"] = [f"{pid}, {path}, [N/A]"]
        script = guard.observer_query([pid])
        command = '"C:\\Program Files\\PowerShell\\7\\pwsh.exe" -NoProfile -EncodedCommand ' + base64.b64encode(script.encode("utf-16le")).decode()
        for row in (s["observer"], observer(s)):
            row["CommandLine"] = command
            row["query_sha256"] = hashlib.sha256(script.encode()).hexdigest()
    case("exact-accounted-idle-and-exact-observer", lambda s,r: None, True)
    case("creation-offset-equivalent-instant", set_current("CreationDate", "2026-11-12T16:09:34.549904+00:00"), True)
    case("same-wall-time-changed-offset", set_current("CreationDate", "2026-11-12T11:09:34.549904+00:00"))
    case("idle-unknown", lambda s,r: r.pop("accounted_idle_ollama"))
    case("idle-pid-reused", set_current("CreationDate", "2026-11-17T16:09:34.549904+00:00"))
    case("idle-executable-changed", set_current("ExecutablePath", r"C:\changed\ollama.exe"))
    case("idle-pid-changed", set_current("ProcessId", 3893))
    case("current-ollama-loaded", set_snapshot("ollama_ps", ["NAME ID SIZE PROCESSOR UNTIL", "model deadbeef 1GB 100%GPU forever"]))
    case("idle-ollama-has-gpu-row", lambda s,r: gpu(s,r,3892,current(s)["ExecutablePath"]))
    case("root-idle-row-mismatch", lambda s,r: r["accounted_idle_ollama"][0].__setitem__("CreationDate", STAMP))
    case("root-idle-row-missing", lambda s,r: r.__setitem__("candidate_and_gpu_processes", []))
    case("root-ollama-loaded", lambda s,r: r.__setitem__("ollama_ps", ["NAME ID SIZE PROCESSOR UNTIL", "loaded model"]))
    case("root-idle-on-gpu", lambda s,r: r["apps"].append("3892, C:\\tools\\ollama.exe, 10"))
    case("observer-reused-pid", lambda s,r: observer(s).__setitem__("CreationDate", "2026-11-17T17:59:59+00:00"))
    case("observer-changed-executable", lambda s,r: observer(s).__setitem__("ExecutablePath", r"C:\changed\pwsh.exe"))
    case("observer-query-hash-mismatch", lambda s,r: s["observer"].__setitem__("query_sha256", "0"*64))
    case("observer-command-mismatch", lambda s,r: observer(s).__setitem__("CommandLine", "pwsh -Command local_ocr"))
    def both_commands(s,r):
        for row in (s["observer"], observer(s)): row["CommandLine"] = "pwsh -NoProfile -EncodedCommand YQ=="
    case("observer-both-commands-wrong", both_commands)
    case("unrelated-powershell-worker", add_process("pwsh.exe", "pwsh -Command local_ocr run_worker"))
    case("unrelated-python-worker", add_process("python.exe", "python -m local_ocr.run_worker"))
    case("python-command-unobservable", add_process("python.exe", None))
    case("unknown-model-server", add_process("vllm.exe", "vllm serve"))
    case("unknown-gpu-process", lambda s,r: gpu(s,r,44444,r"C:\unknown\compute.exe"))
    case("process-query-failed", set_snapshot("processes_exit", 7))
    case("process-query-exit-unknown", lambda s,r: s.pop("processes_exit"))
    case("malformed-process-list", set_snapshot("candidate_and_gpu_processes", {}))
    case("malformed-process-row", set_current("ProcessId", "3892"))
    case("duplicate-process-pid", lambda s,r: s["candidate_and_gpu_processes"].append(copy.deepcopy(current(s))))
    case("ollama-query-failed", set_snapshot("ollama_ps_exit", 9))
    case("ollama-query-malformed", set_snapshot("ollama_ps", ["not a header"]))
    case("ollama-query-empty", set_snapshot("ollama_ps", []))
    case("ollama-queried-other-executable", set_snapshot("ollama_executable", r"C:\changed\ollama.exe"))
    case("root-ollama-query-failed", lambda s,r: r.__setitem__("ollama_ps_exit", 9))
    case("root-app-query-failed", lambda s,r: r.__setitem__("apps_exit", 9))
    case("gpu-query-failed", set_snapshot("gpu_exit", 9))
    case("gpu-app-query-failed", set_snapshot("apps_exit", 9))
    case("malformed-gpu-app-row", set_snapshot("apps", ["unknown-data"]))
    case("snapshot-stale", set_snapshot("observed_utc", "2026-11-17T17:57:59+00:00"))
    case("snapshot-future", set_snapshot("observed_utc", "2026-11-17T18:00:01+00:00"))
    case("ollama-observation-stale", set_snapshot("ollama_observed_utc", "2026-11-17T17:57:59+00:00"))
    case("exact-observer-alone", lambda s,r: s["candidate_and_gpu_processes"].pop(0), True)
    return results


def collector_faults(guard, runner):
    results=[]
    for label in ("process-nonzero", "process-malformed-json", "process-malformed-rows", "ollama-nonzero", "ollama-malformed", "ollama-loaded"):
        snapshot, root = synthetic(guard, runner)
        observer = snapshot["observer"]
        class FakeProcess:
            pid=37576
            returncode=7 if label == "process-nonzero" else 0
            def communicate(self, timeout):
                if label == "process-malformed-json": return b"{", b""
                payload = {"observer_pid":37576, "processes": {} if label == "process-malformed-rows" else snapshot["candidate_and_gpu_processes"]}
                return json.dumps(payload).encode(), b"injected observer failure" if self.returncode else b""
            def poll(self): return self.returncode
        def fake_run(argv, **kwargs):
            if argv[-1] == "ps":
                rows = ["invalid"] if label=="ollama-malformed" else root["ollama_ps"] + (["loaded model"] if label=="ollama-loaded" else [])
                return subprocess.CompletedProcess(argv, 7 if label=="ollama-nonzero" else 0, "\n".join(rows), "injected Ollama error")
            text = "\n".join(snapshot["gpu"]) if any("--query-gpu=" in x for x in argv) else ""
            return subprocess.CompletedProcess(argv, 0, text, "")
        row=dict(control="collector-"+label, expected="reject")
        with mock.patch.object(guard.subprocess,"Popen",return_value=FakeProcess()), mock.patch.object(guard,"popen_creation_utc",return_value=STAMP), mock.patch.object(guard.shutil,"which",side_effect=lambda name: observer["ExecutablePath"] if name=="pwsh" else snapshot["ollama_executable"]):
            try:
                guard.collect(ROOT,runner.EXPECTED_GPU_UUID,fake_run)
                row["actual"]="pass"
            except guard.ObservationError as exc:
                row.update(actual="reject",error=str(exc))
            except Exception:
                row.update(actual="unexpected-exception",error=traceback.format_exc())
        row["passed"]=row["actual"]==row["expected"]
        results.append(row)
    return results


def unchanged_checks():
    old=ast.parse((BASE/"inputs/reviewer-v5.py.txt").read_text(encoding="utf-8"))
    new=ast.parse((BASE/"inputs/reviewer-v6.py.txt").read_text(encoding="utf-8"))
    functions=lambda tree:{n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    a,b=functions(old),functions(new)
    expected={"evaluate_gpu_and_model_ownership","collect_live_ownership_snapshot","main"}
    changed={k for k in a.keys()|b.keys() if a.get(k)!=b.get(k)}
    assert changed==expected,changed
    return dict(unchanged_functions=sorted(a.keys()-expected),changed_functions=sorted(changed),runner_diff="inputs/v5-to-v6-runner.diff")


def observe(guard, runner, output):
    calls=[]
    def retained(argv, **kwargs):
        start=datetime.now(timezone.utc).isoformat()
        cp=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding="utf-8",timeout=60,**kwargs)
        calls.append(dict(argv=argv,started_utc=start,completed_utc=datetime.now(timezone.utc).isoformat(),returncode=cp.returncode,stdout=cp.stdout,stderr=cp.stderr))
        return cp
    result=dict(read_only=True,model_imports=False,service_starts=False,calls=calls)
    try:
        snapshot=guard.collect(ROOT,runner.EXPECTED_GPU_UUID,retained)
        result["snapshot"]=snapshot
        root,_=root_input()
        result["root_input_note"]="Original root 8b6224a ownership observation plus the explicit idle record authorized in bdd7174/parent messages; this independent declaration is not a runtime release."
        result["root_input"]=root
        result["decision"]=runner.evaluate_gpu_and_model_ownership(snapshot,pre_lease_blobs={"root":root},self_pid=os.getpid())
        result["passed"]=True
    except Exception:
        result.update(passed=False,error=traceback.format_exc())
    (output/"actual-observation.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    return result["passed"]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    parser.add_argument("--observe",action="store_true")
    args=parser.parse_args()
    output=Path(args.output)
    assert not output.exists(),output
    assert not subprocess.check_output(["git","status","--porcelain"],cwd=ROOT).strip(), "Freeze/commit before decisive execution"
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    guard,runner=bound_modules()
    output.mkdir(parents=True)
    provenance=dict(candidate=CANDIDATE,check_source_commit=head,started_utc=datetime.now(timezone.utc).isoformat(),pid=os.getpid(),argv=sys.argv,actual_observation=args.observe)
    if args.observe:
        passed=observe(guard,runner,output)
    else:
        result=dict(old_controls=old_controls(),source_scope=unchanged_checks(),controls=controls(guard,runner),collector_faults=collector_faults(guard,runner))
        passed=all(row["passed"] for row in result["controls"]+result["collector_faults"])
        (output/"controls.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
        for row in result["controls"]+result["collector_faults"]:
            print(("PASS" if row["passed"] else "FAIL"),row["control"],row.get("error",""))
    provenance.update(completed_utc=datetime.now(timezone.utc).isoformat(),passed=passed,exit_code=0 if passed else 1)
    (output/"provenance.json").write_text(json.dumps(provenance,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(provenance))
    return provenance["exit_code"]


if __name__=="__main__":
    raise SystemExit(main())
