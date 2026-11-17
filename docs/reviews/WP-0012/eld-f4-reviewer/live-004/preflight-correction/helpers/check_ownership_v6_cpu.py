"""Focused synthetic controls and separately selected, read-only host observation.

No services, model imports, inference, or retry. Every output directory is new.
The real probe's coordinator fixture is CPU-only, derived from the original
root blob plus the root's explicit idle identity; it is not a runtime release.
"""
from __future__ import annotations
import argparse
import base64
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
from unittest.mock import patch

import ownership_v6 as guard
import run_wp0012_reviewer_rehearsal_v6 as runner

ROOT = Path(__file__).resolve().parents[7]
HERE = Path(__file__).resolve().parent.parent
SOURCE = "651146fa704fe0df262057540587399277ff6a23"
ROOT_BASE = "8c93a61635156105c8ecae60589ad31539782067"
ROOT_PATH = "docs/coordination/WP-0012/reviewer-004-release/ownership-before.json"
OLLAMA = r"C:\Users\jackg\AppData\Local\Programs\Ollama\ollama.exe"
PWSH = r"C:\synthetic\pwsh.exe"
HEADER = "NAME ID SIZE PROCESSOR CONTEXT RUNNER UNTIL"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def row(pid, name, executable, command="", creation="2026-11-12T16:09:34.549904+00:00"):
    return dict(ProcessId=pid, Name=name, ExecutablePath=executable,
                CommandLine=command, CreationDate=creation)


def bind_observer(snapshot):
    script = guard.observer_query([p[0] for p in guard.gpu_apps(snapshot)])
    encoded = base64.b64encode(script.encode("utf-16le")).decode()
    observer = row(37576, "pwsh.exe", PWSH, f'"{PWSH}" -NoProfile -EncodedCommand {encoded}')
    snapshot["candidate_and_gpu_processes"] = [p for p in snapshot["candidate_and_gpu_processes"] if p["ProcessId"] != 37576] + [observer]
    snapshot["observer"] = dict(observer, query_sha256=sha(script.encode()))


def fixture():
    now = datetime.now(timezone.utc)
    idle = row(3892, "ollama.exe", OLLAMA, '"' + OLLAMA + '" serve')
    snapshot = dict(gpu_exit=0, apps_exit=0, processes_exit=0,
                    gpu=[f"synthetic, {runner.EXPECTED_GPU_UUID}, synthetic, driver, 12, 16, 1, 15"],
                    apps=[], candidate_and_gpu_processes=[idle],
                    ollama_ps_exit=0, ollama_ps=[HEADER], ollama_executable=OLLAMA,
                    observed_utc=now.isoformat(), ollama_observed_utc=now.isoformat())
    baseline = dict(candidate_and_gpu_processes=[copy.deepcopy(idle)],
                    accounted_idle_ollama=[copy.deepcopy(idle)], apps_exit=0, apps=[],
                    ollama_ps_exit=0, ollama_ps=[HEADER])
    baseline["accounted_idle_ollama"][0]["CreationDate"] = "2026-11-12T11:09:34.549904-05:00"
    bind_observer(snapshot)
    return snapshot, {"synthetic_root": baseline}


def evaluate(snapshot, blobs):
    return runner.evaluate_gpu_and_model_ownership(snapshot, pre_lease_blobs=blobs, self_pid=999999)


def controls():
    results = []

    def case(name, change=None, reject=False):
        snapshot, blobs = fixture()
        if change:
            change(snapshot, blobs)
        try:
            result = evaluate(snapshot, blobs)
        except runner.CompetingModelOwnershipError as exc:
            results.append(dict(name=name, expected="refuse" if reject else "pass", passed=reject,
                                actual="refused", message=str(exc), snapshot=snapshot, root_fixture=blobs))
        else:
            results.append(dict(name=name, expected="refuse" if reject else "pass", passed=not reject,
                                actual="passed", result=result, snapshot=snapshot, root_fixture=blobs))

    def sset(key, value):
        return lambda s, b: s.update({key: value})

    def idle_set(key, value):
        return lambda s, b: s["candidate_and_gpu_processes"][0].update({key: value})

    case("exact_idle_identity_and_exact_observer")
    case("five_column_header", sset("ollama_ps", ["NAME ID SIZE PROCESSOR UNTIL"]))
    case("creation_equivalent_timezone", idle_set("CreationDate", "2026-11-12T11:09:34.549904-05:00"))
    case("loaded_model", sset("ollama_ps", [HEADER, "synthetic-model synthetic-id 8GB 100%GPU 4096 running 5minutes"]), True)
    case("failed_ollama_ps", sset("ollama_ps_exit", 1), True)
    case("missing_ollama_ps", sset("ollama_ps", []), True)
    case("malformed_ollama_header", sset("ollama_ps", ["unexpected output"]), True)
    case("ollama_string_exit", sset("ollama_ps_exit", "0"), True)
    case("unknown_model_server", lambda s, b: s["candidate_and_gpu_processes"].append(row(4000, "llama-server.exe", r"C:\synthetic\llama-server.exe")), True)
    case("ollama_reused_pid", idle_set("CreationDate", "2026-11-17T12:00:00+00:00"), True)
    case("ollama_changed_executable", idle_set("ExecutablePath", r"C:\other\ollama.exe"), True)
    case("ollama_changed_pid", idle_set("ProcessId", 3893), True)
    case("query_executable_differs", sset("ollama_executable", r"C:\other\ollama.exe"), True)
    case("root_has_no_explicit_idle", lambda s, b: b["synthetic_root"].pop("accounted_idle_ollama"), True)
    case("root_idle_absent_from_baseline", lambda s, b: b["synthetic_root"].update(candidate_and_gpu_processes=[]), True)
    case("root_loaded_model", lambda s, b: b["synthetic_root"]["ollama_ps"].append("synthetic loaded row"), True)
    case("root_idle_on_gpu", lambda s, b: b["synthetic_root"]["apps"].append(f"3892, {OLLAMA}, 1000"), True)

    def current_gpu(s, b):
        s["apps"] = [f"3892, {OLLAMA}, 1000"]
        bind_observer(s)
    case("current_idle_on_gpu", current_gpu, True)
    case("observer_pid_mismatch", lambda s, b: s["observer"].update(ProcessId=37577), True)
    case("observer_creation_mismatch", lambda s, b: s["observer"].update(CreationDate="2026-11-17T00:00:00Z"), True)
    case("observer_executable_mismatch", lambda s, b: s["observer"].update(ExecutablePath=r"C:\other\pwsh.exe"), True)
    case("observer_query_mismatch", lambda s, b: s["observer"].update(query_sha256="0" * 64), True)
    case("observer_command_mismatch", lambda s, b: s["observer"].update(CommandLine="pwsh -Command unknown"), True)

    def forged_command(s, b):
        s["observer"]["CommandLine"] = 'pwsh -NoProfile -EncodedCommand Zm9yZ2Vk'
        s["candidate_and_gpu_processes"][-1]["CommandLine"] = s["observer"]["CommandLine"]
    case("observer_matching_but_wrong_query", forged_command, True)
    case("other_powershell_worker_not_exempt", lambda s, b: s["candidate_and_gpu_processes"].append(row(4001, "pwsh.exe", PWSH, "pwsh local_ocr")), True)
    case("other_python_worker_not_exempt", lambda s, b: s["candidate_and_gpu_processes"].append(row(4002, "python.exe", r"C:\synthetic\python.exe", "python run_worker")), True)
    case("unknown_python_command", lambda s, b: s["candidate_and_gpu_processes"].append(row(4002, "python.exe", r"C:\synthetic\python.exe", None)), True)
    case("failed_process_observation", sset("processes_exit", 1), True)
    case("missing_process_observation", sset("candidate_and_gpu_processes", None), True)
    case("malformed_process_row", lambda s, b: s["candidate_and_gpu_processes"].append({"ProcessId": 6000}), True)
    case("duplicate_process_pid", lambda s, b: s["candidate_and_gpu_processes"].append(copy.deepcopy(s["candidate_and_gpu_processes"][0])), True)
    case("malformed_command_type", idle_set("CommandLine", []), True)
    case("failed_gpu_observation", sset("gpu_exit", 1), True)
    case("failed_apps_observation", sset("apps_exit", 1), True)
    case("malformed_gpu_row", sset("apps", ["unparsed row"]), True)
    case("wrong_gpu_uuid", sset("gpu", ["synthetic, GPU-wrong, synthetic, driver, 12, 16, 1, 15"]), True)
    case("stale_snapshot", sset("observed_utc", (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat()), True)
    case("future_snapshot", sset("observed_utc", (datetime.now(timezone.utc) + timedelta(minutes=3)).isoformat()), True)
    case("stale_ollama", sset("ollama_observed_utc", (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat()), True)

    def desktop(s, b):
        p = row(4003, "synthetic-desktop.exe", r"C:\synthetic\synthetic-desktop.exe")
        b["synthetic_root"]["candidate_and_gpu_processes"].append(copy.deepcopy(p))
        s["candidate_and_gpu_processes"].append(p)
        s["apps"] = [f"4003, {p['ExecutablePath']}, [N/A]"]
        bind_observer(s)
    case("exact_accounted_desktop", desktop)
    def desktop_reuse(s, b):
        desktop(s, b)
        next(p for p in s["candidate_and_gpu_processes"] if p["ProcessId"] == 4003)["CreationDate"] = "2026-11-17T12:00:00Z"
    case("accounted_desktop_pid_reuse", desktop_reuse, True)

    oldpath = ROOT / "docs/reviews/WP-0012/eld-f4-reviewer/correction-006-review/helpers/run_wp0012_reviewer_rehearsal_v5.py"
    spec = importlib.util.spec_from_file_location("retained_v5", oldpath)
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    s, b = fixture()
    s["candidate_and_gpu_processes"][-1]["CommandLine"] = "pwsh -Command " + guard.observer_query([])
    try:
        old.evaluate_gpu_and_model_ownership(s, pre_lease_blobs=b, self_pid=999999)
        results.append(dict(name="retained_v5_both_causes", passed=False, actual="unexpected_pass"))
    except old.CompetingModelOwnershipError as exc:
        message = str(exc)
        results.append(dict(name="retained_v5_both_causes", passed=all(t in message for t in ("3892", "37576", "host_model_server", "host_ocr_or_qualification_worker")), actual="refused", message=message,
                            limitation="Synthetic recreation of both retained stderr causes, not a live v5 rerun."))
    stderr = (HERE / "first-refusal/live-leased-rehearsal.stderr.log").read_bytes()
    results.append(dict(name="original_refusal_bytes_show_both_identities", passed=all(t in stderr for t in (b'3892', b'37576', b'host_model_server', b'host_ocr_or_qualification_worker')), sha256=sha(stderr)))

    class FakeProcess:
        pid = 37576
        def __init__(self, exitcode, payload):
            self.returncode, self.payload = exitcode, payload
        def communicate(self, timeout):
            return self.payload, b"synthetic process failure" if self.returncode else b""
        def poll(self):
            return self.returncode
    for label, exitcode, payload in (("collector_process_failure", 1, b""), ("collector_malformed_json", 0, b"not-json"), ("collector_observer_pid_mismatch", 0, b'{"observer_pid": 999}')):
        def fake_run(argv, **kwargs):
            if argv[0] != "nvidia-smi":
                raise AssertionError("Ollama query must not follow failed process observation")
            return subprocess.CompletedProcess(argv, 0, "" if "--query-compute-apps=pid,process_name,used_memory" in argv else fixture()[0]["gpu"][0], "")
        with patch.object(guard.shutil, "which", return_value=PWSH), patch.object(guard.subprocess, "Popen", return_value=FakeProcess(exitcode, payload)), patch.object(guard, "popen_creation_utc", return_value="2026-11-12T16:09:34.549904Z"):
            try:
                guard.collect(ROOT, runner.EXPECTED_GPU_UUID, fake_run)
                results.append(dict(name=label, passed=False, actual="unexpected_pass"))
            except guard.ObservationError as exc:
                results.append(dict(name=label, passed=True, actual="refused", message=str(exc)))
    return results


def public_snapshot(snapshot):
    """Preserve identity and classification input without unrelated command text."""
    out = copy.deepcopy(snapshot)
    observer_pid = snapshot["observer"]["ProcessId"]
    for p in out["candidate_and_gpu_processes"]:
        command = p.get("CommandLine")
        if p["ProcessId"] != observer_pid and command is not None:
            p["CommandLine_sha256"] = sha(command.encode())
            p["CommandLine"] = " ".join(m.group() for m in runner.MODEL_WORKLOAD_TOKEN_RE.finditer(command))
            p["command_disclosure"] = "classification tokens only; unrelated arguments omitted"
    return out


def actual_probe():
    raw = subprocess.run(["git", "show", f"{ROOT_BASE}:{ROOT_PATH}"], cwd=ROOT, capture_output=True, check=True).stdout
    baseline = json.loads(raw)
    idle = next(p for p in baseline["candidate_and_gpu_processes"] if p["ProcessId"] == 3892)
    assert guard.identity(idle) == guard.identity(row(3892, "ollama.exe", OLLAMA))
    baseline["accounted_idle_ollama"] = [copy.deepcopy(idle)]
    snapshot = runner.collect_live_ownership_snapshot(ROOT)
    result = runner.evaluate_gpu_and_model_ownership(snapshot, pre_lease_blobs={"cpu_only_root_fixture": baseline}, self_pid=os.getpid())
    published = public_snapshot(snapshot)
    assert runner.evaluate_gpu_and_model_ownership(published, pre_lease_blobs={"cpu_only_root_fixture": baseline}, self_pid=os.getpid()) == result
    return dict(actual_read_only_observation=published, result=result,
                cpu_only_root_fixture=baseline, root_blob_commit=ROOT_BASE, root_blob_path=ROOT_PATH,
                root_blob_sha256=sha(raw), root_explicit_idle_authority="8b6224a44ddbf4658abc5ae1fe3ac0cd2bb96938 plus exact root message",
                runtime_authorization=False, command_disclosure="Only exact observer command and matching workload tokens retained. Other command lines are hashed.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("cpu", "read-only"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    record = dict(mode=args.mode, started_utc=started, source_commit=SOURCE,
                  executing_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  source_files={str(p.relative_to(ROOT)).replace("\\", "/"):sha(p.read_bytes()) for p in (Path(__file__), Path(guard.__file__), Path(runner.__file__))},
                  no_model_or_service_started=True)
    exitcode = 0
    try:
        if args.mode == "cpu":
            record["cases"] = controls()
            record["passed"] = sum(c["passed"] for c in record["cases"])
            record["total"] = len(record["cases"])
            exitcode = 0 if record["passed"] == record["total"] else 1
        else:
            record.update(actual_probe())
    except BaseException as exc:
        record["error"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        exitcode = 1
    record.update(exit_code=exitcode, finished_utc=datetime.now(timezone.utc).isoformat())
    (args.output_dir / "result.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: record[k] for k in ("mode", "source_commit", "executing_head", "exit_code", "started_utc", "finished_utc")}))
    print(f"Result: {args.output_dir / 'result.json'}")
    return exitcode


if __name__ == "__main__":
    raise SystemExit(main())
