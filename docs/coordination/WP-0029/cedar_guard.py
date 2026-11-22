"""Issue the released job once; guard its wall independently of telemetry I/O."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cedar_plan as c

g = c.guard


def monitor(stop, fault, failures, log):
    try:
        with log.open("x", encoding="utf8", newline="\n") as stream:
            while not stop.is_set():
                sample = g.device()
                sample["mono_ns"] = time.monotonic_ns()
                stream.write(json.dumps(sample) + "\n")
                stream.flush()
                if sample["used_mib"] > 12500:
                    raise RuntimeError(f"Board used {sample['used_mib']} MiB")
                stop.wait(0.35)
    except BaseException as exc:
        failures.append(repr(exc))
        fault.set()


def run(release, release_path, digest):
    req = c.require
    req(Path(sys.executable).resolve() == c.QPY.resolve() and sys.flags.isolated and sys.flags.dont_write_bytecode,
        "Pinned guard interpreter required")
    req(release["packet"] == "WP-0029" and release["name"] == "cedar-r1" and
        (release["loads"],release["excluded_w0"],release["scored_calls"],release["retries"],
         release["seconds"],release["ceiling_mib"],release["free_floor_mib"]) == (1,1,1,0,180,12500,12000)
        and release["gpu_uuid"] == g.GPU and Path(release["worktree"]) == c.ROOT, "Release limits or worktree")
    with g.exclusive(g.LOCK):
        c.LEASE.mkdir(parents=True, exist_ok=False)
        end_error = None
        try:
            g.dump(c.LEASE/"acquired.json",dict(utc=g.utc(), guard_pid=os.getpid(), lock=str(g.LOCK),
                                               release=str(release_path), release_sha256=digest))
            req(release["source_files"] == c.source_pins() and c.git("rev-parse","HEAD") == release["candidate"]
                and not c.git("status","--porcelain","--untracked-files=all"), "Clean frozen checkout or bytes")
            path = Path(release["plan"]).resolve(strict=True)
            req(g.sha(path) == release["plan_sha256"] and Path(release["output"]) == c.OUTPUT, "Changed plan binding")
            plan = c.read(path)
            expected = c.execution_fields()
            req(set(plan) == set(expected) | {"candidate","environment"} and plan["candidate"] == release["candidate"]
                and all(plan[k] == v for k,v in expected.items()), "Plan diverges from the release")
            state = g.ownership()
            known = set(c.read(c.DESKTOP)["observed_desktop_images"])
            unknown = [x for x in state["processes"] if x["image"].casefold() not in known]
            g.dump(c.LEASE/"admission.json",dict(utc=g.utc(), observed=state, unknown=unknown))
            req(not unknown and state["device"]["free_mib"] >= 12000 and state["device"]["used_mib"] <= 12500,
                "GPU ownership or preflight floor/ceiling")
            c.OUTPUT.mkdir(parents=True, exist_ok=False)
            sensor = c.OUTPUT / "sensor"
            env = c.historical.environment(sensor)
            req(env == plan["environment"], "Worker environment differs from plan")
            job_name = "Local\\eLedgerCare-WP0029-" + uuid.uuid4().hex
            argv = [str(c.QPY), "-I", "-B", str(HERE/"cedar_worker.py"), str(path), release["plan_sha256"], job_name]
            stop, fault = threading.Event(), threading.Event()
            failures = []
            telemetry = threading.Thread(target=monitor, args=(stop,fault,failures,c.LEASE/"device.jsonl"), daemon=True)
            child = None
            elapsed = None
            reason = None
            with (c.OUTPUT/"stdout.txt").open("xb") as stdout, (c.OUTPUT/"stderr.txt").open("xb") as stderr:
                job = g.winjob.create(job_name)
                close_lock = threading.Lock()
                closed = threading.Event()
                expired = threading.Event()

                def close_job(timed_out=False):
                    with close_lock:
                        if not closed.is_set():
                            if timed_out:
                                expired.set()
                            g.winjob.close(job)
                            closed.set()

                timer = None
                try:
                    telemetry.start()
                    utc_start = time.time_ns()
                    start = time.monotonic_ns()
                    deadline = start + 180_000_000_000
                    timer = threading.Timer((deadline - time.monotonic_ns()) / 1e9, close_job, args=(True,))
                    timer.daemon = True
                    timer.start()
                    child = subprocess.Popen(argv, cwd=c.ROOT, env=env, stdout=stdout, stderr=stderr,
                                             stdin=subprocess.DEVNULL)
                    g.dump(c.LEASE/"issued.json", dict(utc_ns=utc_start, start_mono_ns=start, deadline_mono_ns=deadline,
                           launcher_pid=child.pid, guard_pid=os.getpid(), job=job_name, argv=argv, plan_sha256=g.sha(path)))
                    while True:
                        remaining = (deadline - time.monotonic_ns()) / 1e9
                        if remaining <= 0:
                            reason = "180-second wall deadline"
                            break
                        if fault.is_set():
                            reason = "Board memory or telemetry failure"
                            break
                        try:
                            child.wait(timeout=min(remaining, 0.05))
                        except subprocess.TimeoutExpired:
                            continue
                        if time.monotonic_ns() >= deadline:
                            reason = "Completion not observed within 180 seconds"
                        break
                finally:
                    close_job()
                    if timer is not None:
                        timer.cancel()
                    if child is not None:
                        elapsed = (time.monotonic_ns() - start) / 1e9
                    stop.set()
                    if child is not None:
                        child.wait(timeout=15)
                    telemetry.join(timeout=14)
            req(not telemetry.is_alive(), "Telemetry did not return")
            if expired.is_set():
                reason = "180-second job watchdog"
            if failures and not reason:
                reason = "Board memory or telemetry failure"
            g.dump(c.OUTPUT/"process.json",dict(guard_pid=os.getpid(), launcher_pid=child.pid, job=job_name,
                   native_job_wall_s=elapsed, returncode=child.returncode, stop_reason=reason,
                   telemetry_errors=failures, ended_utc=g.utc()))
            req(not reason and child.returncode == 0, f"Stopped job: {reason}, exit {child.returncode}")
            outcome = c.read(sensor/"outcome.json")
            req(outcome["status"] == "complete" and outcome["started_tags"] == outcome["verified_tags"] == ["k0001"]
                and outcome["total_inference_calls"] == 2 and outcome["warmup_calls"] == 1, "Incomplete sample")
        except BaseException as exc:
            end_error = repr(exc)
            raise
        finally:
            try:
                after = g.ownership()
            except BaseException as exc:
                after = {"unverified":repr(exc)}
            g.dump(c.LEASE/"returned.json",dict(utc=g.utc(), error=end_error, ownership_after_job_close=after,
                                               release_sha256=digest, retiring_pid=os.getpid()))
            if end_error is None:
                req("unverified" not in after, "Could not verify post-job ownership")


if __name__ == "__main__":
    release_path = Path(sys.argv[1]).resolve(strict=True)
    digest = sys.argv[2]
    c.require(g.sha(release_path) == digest, "Release digest mismatch")
    run(c.read(release_path), release_path, digest)
