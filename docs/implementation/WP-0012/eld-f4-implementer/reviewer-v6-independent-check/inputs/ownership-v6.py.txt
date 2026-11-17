"""Bounded reviewer ownership observation: exact idle identity and exact observer only.

No model/service launch. Read-only GPU/process/Ollama queries are called only by
the leased runtime or the separately authorized frozen CPU ownership probe.
"""
from __future__ import annotations
import base64
import ctypes
from ctypes import wintypes
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


class ObservationError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise ObservationError(message)


def utc(value):
    require(isinstance(value, str) and bool(value), "Missing process/observation creation timestamp")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ObservationError("Malformed creation/observation timestamp") from exc
    require(result.tzinfo is not None, "Creation/observation timestamp lacks timezone")
    return result.astimezone(timezone.utc)


def exe(value):
    require(isinstance(value, str) and bool(value.strip()), "Missing executable identity")
    return value.replace("/", "\\").casefold()


def identity(row):
    require(isinstance(row, dict), "Malformed process row")
    require(type(row.get("ProcessId")) is int and row["ProcessId"] > 0, "Malformed process PID")
    require(isinstance(row.get("Name"), str) and row["Name"], "Missing process name")
    return (row["ProcessId"], utc(row.get("CreationDate")), row["Name"].casefold(), exe(row.get("ExecutablePath")))


def processes(rows):
    require(isinstance(rows, list), "Process observation must be a list")
    result = {}
    for row in rows:
        key = identity(row)
        require(key[0] not in result, "Duplicate process PID in observation")
        require(row.get("CommandLine") is None or isinstance(row.get("CommandLine"), str), "Malformed process command line")
        result[key[0]] = row
    return result


def gpu_apps(snapshot):
    require(snapshot.get("apps_exit") == 0 and type(snapshot.get("apps_exit")) is int, "GPU apps observation failed or unknown")
    rows = snapshot.get("apps")
    require(isinstance(rows, list), "Malformed GPU process observation")
    parsed = []
    for line in rows:
        require(isinstance(line, str), "Malformed GPU row")
        if not line.strip():
            continue
        parts = [part.strip() for part in line.split(",", 2)]
        require(len(parts) == 3 and parts[0].isdigit() and int(parts[0]) > 0 and bool(parts[1]) and bool(parts[2]), "Unparsed GPU row")
        parsed.append((int(parts[0]), parts[1], parts[2]))
    require(len({p[0] for p in parsed}) == len(parsed), "Duplicate GPU PID")
    return parsed


def idle_ollama(snapshot):
    require(type(snapshot.get("ollama_ps_exit")) is int and snapshot["ollama_ps_exit"] == 0, "Ollama observation failed or unknown")
    rows = snapshot.get("ollama_ps")
    require(isinstance(rows, list) and all(isinstance(row, str) for row in rows), "Malformed Ollama observation")
    lines = [row.strip() for row in rows if row.strip()]
    headers = {("NAME", "ID", "SIZE", "PROCESSOR", "UNTIL"),
               ("NAME", "ID", "SIZE", "PROCESSOR", "CONTEXT", "RUNNER", "UNTIL")}
    require(bool(lines) and tuple(lines[0].split()) in headers, "Unrecognized Ollama ps header")
    require(len(lines) == 1, "Ollama has loaded models; idle exception forbidden")


def observer_query(gpu_pids):
    values = ",".join(str(pid) for pid in sorted(gpu_pids))
    return (
        "$ErrorActionPreference='Stop'; $gpuPids=@(" + values + "); "
        "$rows=@(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -eq $PID -or "
        "$gpuPids -contains $_.ProcessId -or "
        "$_.Name -match '^(python(w)?|ollama|llama(-server|-cli)?|vllm|lm.?studio|koboldcpp)\\.exe$' -or "
        "$_.CommandLine -match '(local_ocr|run_worker|q0harness|qualification[/\\\\.](coverage_v1|mapping_v1|mapping_v2|baseline|q0))' "
        "} | ForEach-Object { @{ ProcessId=[int]$_.ProcessId; Name=$_.Name; ExecutablePath=$_.ExecutablePath; "
        "CreationDate=$_.CreationDate.ToUniversalTime().ToString('o'); CommandLine=$_.CommandLine } }); "
        "@{ observer_pid=[int]$PID; processes=$rows } | ConvertTo-Json -Compress -Depth 5"
    )


def observer_identity(snapshot, by_pid, apps):
    observed = snapshot.get("observer")
    require(isinstance(observed, dict), "Missing exact observer identity")
    key = identity(observed)
    actual = by_pid.get(key[0])
    require(actual is not None and identity(actual) == key, "Observer PID/creation/executable mismatch")
    require(key[2] == "pwsh.exe" and key[3].endswith("\\pwsh.exe"), "Observer executable is not pwsh")
    script = observer_query([p[0] for p in apps])
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    require(observed.get("query_sha256") == hashlib.sha256(script.encode()).hexdigest(), "Observer query hash mismatch")
    command = actual.get("CommandLine")
    require(isinstance(command, str) and command == observed.get("CommandLine"), "Observer command identity mismatch")
    require(re.search(r"\s-NoProfile\s+-EncodedCommand\s+" + re.escape(encoded) + r"\s*$", command, re.I), "Observer command is not the exact issued query")
    require(key[0] not in {p[0] for p in apps}, "Observer unexpectedly appears in GPU apps")
    return key[0]


def evaluate(snapshot, *, pre_lease_blobs, self_pid, expected_gpu_uuid,
             model_server_re, python_re, workload_re, benign_names, now_utc=None):
    require(isinstance(snapshot, dict), "Malformed ownership snapshot")
    require(type(snapshot.get("gpu_exit")) is int and snapshot["gpu_exit"] == 0, "GPU observation failed or unknown")
    require(type(snapshot.get("processes_exit")) is int and snapshot["processes_exit"] == 0, "Process observation failed or unknown")
    gpu = snapshot.get("gpu")
    require(isinstance(gpu, list) and len(gpu) == 1 and isinstance(gpu[0], str), "Malformed GPU identity observation")
    parts = [p.strip() for p in gpu[0].split(",")]
    require(len(parts) == 8 and parts[1] == expected_gpu_uuid, "Observed GPU identity mismatch")
    now = now_utc or datetime.now(timezone.utc)
    stamp = utc(snapshot.get("observed_utc"))
    ollama_stamp = utc(snapshot.get("ollama_observed_utc"))
    require(timedelta(0) <= now - stamp <= timedelta(seconds=120), "Ownership snapshot is stale/future")
    require(timedelta(0) <= stamp - ollama_stamp <= timedelta(seconds=120), "Ollama observation is not fresh")
    apps = gpu_apps(snapshot)
    by_pid = processes(snapshot.get("candidate_and_gpu_processes"))
    observer_pid = observer_identity(snapshot, by_pid, apps)
    idle_ollama(snapshot)
    queried_ollama_exe = exe(snapshot.get("ollama_executable"))
    allowed_idle, accounted_desktop = set(), set()
    for blob in (pre_lease_blobs or {}).values():
        if not isinstance(blob, dict):
            continue
        rows = blob.get("candidate_and_gpu_processes")
        if rows is None:
            continue
        baseline = processes(rows)
        for row in baseline.values():
            key = identity(row)
            if not model_server_re.match(key[2]) and not python_re.match(key[2]) and not workload_re.search(key[3]) and not workload_re.search(row.get("CommandLine") or ""):
                accounted_desktop.add(key)
        explicit = blob.get("accounted_idle_ollama", [])
        require(isinstance(explicit, list), "Malformed coordinator idle Ollama declaration")
        if explicit:
            idle_ollama(blob)
            baseline_gpu = {p[0] for p in gpu_apps(blob)}
            for row in explicit:
                key = identity(row)
                require(key[2] == "ollama.exe" and key[3].endswith("\\ollama.exe"), "Idle exception is Ollama-only")
                require(key[0] in baseline and identity(baseline[key[0]]) == key, "Coordinator idle identity not present in baseline")
                require(key[0] not in baseline_gpu, "Coordinator idle Ollama appears in GPU apps")
                allowed_idle.add(key)
    violations, desktops, idle = [], [], []
    gpu_pids = {p[0] for p in apps}
    own_pid = os.getpid() if self_pid is None else self_pid
    for pid, path, memory in apps:
        if pid == own_pid:
            continue
        name = path.replace("\\", "/").split("/")[-1].casefold()
        row = by_pid.get(pid)
        command = (row or {}).get("CommandLine") or ""
        if model_server_re.match(name) or python_re.match(name) or workload_re.search(path) or workload_re.search(command):
            violations.append({"source": "gpu_model_process", "pid": pid, "name": name})
        elif name in benign_names or (row is not None and identity(row) in accounted_desktop and exe(path) == exe(row["ExecutablePath"])):
            desktops.append({"pid": pid, "name": name, "used_memory_mib": memory})
        else:
            violations.append({"source": "unknown_gpu_process", "pid": pid, "name": name})
    for pid, row in by_pid.items():
        if pid in (own_pid, observer_pid):
            continue
        key = identity(row)
        command = row.get("CommandLine")
        if model_server_re.match(key[2]):
            if key[2] == "ollama.exe" and key in allowed_idle and pid not in gpu_pids and key[3] == queried_ollama_exe:
                idle.append({"ProcessId": pid, "CreationDate": row["CreationDate"], "ExecutablePath": row["ExecutablePath"]})
            else:
                violations.append({"source": "unaccounted_model_server", "pid": pid, "name": key[2]})
        elif (python_re.match(key[2]) and command is None) or workload_re.search(key[3]) or workload_re.search(command or ""):
            violations.append({"source": "host_model_worker_or_unknown_command", "pid": pid, "name": key[2]})
    require(not violations, "Unaccounted competing model/GPU workload detected: " + json.dumps(violations))
    return {"sole_model_job_verified": True, "hardware_exclusivity_claimed": False,
            "wddm_desktop_sharing_observed": bool(desktops), "wddm_desktop_sharing_entries": desktops,
            "accounted_idle_ollama": idle, "exact_observer_excluded": snapshot["observer"], "competing_model_violations": []}


def popen_creation_utc(proc):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE, *([ctypes.POINTER(wintypes.FILETIME)] * 4)]
    kernel.GetProcessTimes.restype = wintypes.BOOL
    values = [wintypes.FILETIME() for _ in range(4)]
    require(kernel.GetProcessTimes(wintypes.HANDLE(int(proc._handle)), *(ctypes.byref(v) for v in values)), "Cannot record observer creation identity")
    ticks = (values[0].dwHighDateTime << 32) | values[0].dwLowDateTime
    return (datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=ticks // 10)).isoformat(timespec="microseconds")


def collect(repo_root, expected_gpu_uuid, run_cmd):
    result = {}
    for key, query in (("gpu", "--query-gpu=timestamp,uuid,name,driver_version,compute_cap,memory.total,memory.used,memory.free"),
                       ("apps", "--query-compute-apps=pid,process_name,used_memory")):
        cp = run_cmd(["nvidia-smi", f"--id={expected_gpu_uuid}", query, "--format=csv,noheader,nounits"], cwd=repo_root)
        result[key + "_exit"] = cp.returncode
        result[key] = cp.stdout.splitlines()
        require(cp.returncode == 0, f"{key} query failed: {cp.stderr}")
    apps = gpu_apps(result)
    script = observer_query([p[0] for p in apps])
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    powershell = shutil.which("pwsh")
    require(bool(powershell), "PowerShell observer unavailable")
    proc = subprocess.Popen([powershell, "-NoProfile", "-EncodedCommand", encoded], cwd=repo_root,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        creation = popen_creation_utc(proc)
        stdout, stderr = proc.communicate(timeout=60)
    except BaseException:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=10)
        raise
    require(proc.returncode == 0, "Process observation failed: " + stderr.decode("utf-8", errors="replace"))
    try:
        payload = json.loads(stdout)
    except (ValueError, UnicodeError) as exc:
        raise ObservationError("Malformed process-query JSON") from exc
    require(isinstance(payload, dict) and payload.get("observer_pid") == proc.pid, "Observer response PID mismatch")
    rows = payload.get("processes")
    by_pid = processes(rows)
    observer = dict(by_pid.get(proc.pid) or {})
    require(bool(observer) and utc(observer.get("CreationDate")) == utc(creation), "Observer creation identity differs from retained process handle")
    require(exe(observer.get("ExecutablePath")) == exe(str(Path(powershell).resolve())), "Observer executable differs from issued command")
    observer["query_sha256"] = hashlib.sha256(script.encode()).hexdigest()
    result.update(processes_exit=proc.returncode, observer=observer, candidate_and_gpu_processes=rows)
    ollama = shutil.which("ollama")
    require(bool(ollama), "Ollama ps executable unavailable; ownership unverified")
    cp = run_cmd([ollama, "ps"], cwd=repo_root)
    result.update(ollama_ps_exit=cp.returncode, ollama_ps=cp.stdout.splitlines(),
                  ollama_executable=str(Path(ollama).resolve()), ollama_observed_utc=datetime.now(timezone.utc).isoformat())
    idle_ollama(result)
    result["observed_utc"] = datetime.now(timezone.utc).isoformat()
    observer_identity(result, by_pid, apps)
    return result
