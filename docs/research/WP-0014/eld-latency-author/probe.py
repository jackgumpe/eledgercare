"""Serialized WP-0014 supervisor. Use CPU preparation before a coordinator-released GPU stage."""
import time
from time import perf_counter_ns as now
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cases import GPU, HERE, PAGES, PYTHON, Q0, WORKER, assess, dump, materialize, read

STAGES = ("cpu", "fresh-A", "fresh-B", "fresh-S", "resident", "resident-short")


def isolated_env(run):
    keep = ("SystemRoot", "windir", "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "PROCESSOR_IDENTIFIER",
            "PROCESSOR_LEVEL", "PROCESSOR_REVISION", "OS", "PATHEXT", "ComSpec")
    env = {k: os.environ[k] for k in keep if k in os.environ}
    windows = Path(env["SystemRoot"])
    env.update(PATH=os.pathsep.join(map(str, (PYTHON.parent, windows / "System32", windows))),
               VIRTUAL_ENV=str(Q0 / "venv"), CUDA_VISIBLE_DEVICES=GPU, CUDA_DEVICE_ORDER="PCI_BUS_ID",
               HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_XET="1", HF_HUB_DISABLE_TELEMETRY="1",
               HF_HUB_DISABLE_PROGRESS_BARS="1", PIP_NO_INDEX="1", PIP_CONFIG_FILE="NUL")
    for keys, sub in [
        ("TEMP TMP TMPDIR", "tmp"), ("HOME USERPROFILE", "home"), ("HF_HOME", "hf-home"),
        ("HF_HUB_CACHE HUGGINGFACE_HUB_CACHE", "hf-home/hub"), ("TRANSFORMERS_CACHE", "hf-home/transformers"),
        ("HF_MODULES_CACHE", "hf-modules"), ("TORCH_HOME", "torch-home"), ("TRITON_CACHE_DIR", "triton-cache"),
        ("TORCHINDUCTOR_CACHE_DIR", "inductor-cache"), ("CUDA_CACHE_PATH", "cuda-cache"),
        ("XDG_CACHE_HOME", "xdg-cache"), ("PIP_CACHE_DIR", "pip-cache"), ("UV_CACHE_DIR", "uv-cache"),
    ]:
        destination = run / "cache" / sub
        destination.mkdir(parents=True, exist_ok=True)
        env.update(dict.fromkeys(keys.split(), str(destination)))
    return env


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("stage", choices=STAGES)
    parser.add_argument("run_name", help="New owned run label, e.g. trial1")
    parser.add_argument("--gpu", choices=[GPU], help="Supply only under coordinator release")
    parser.add_argument("--owner", choices=("author", "reviewer"), default="author")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9-]{1,24}", args.run_name) or (args.stage != "cpu" and not args.gpu):
        parser.error("Expected a fresh run label and a GPU lease for model stages")
    run = Path("C:/Users/jackg/eLedgerCare-Latency/WP-0014") / args.owner / args.run_name / "runs" / args.stage
    run.mkdir(parents=True, exist_ok=False)
    env = isolated_env(run)
    fresh = args.stage.startswith("fresh-")
    key = args.stage[-1] if fresh else "A"
    materialize(run, key)
    cmd = [str(PYTHON), "-I", "-B"]
    if fresh:
        cmd += [str(WORKER / "run_worker.py"), "--request", str(run / "request.json")]
    else:
        cmd += [str(HERE / "instrument.py"), args.stage, str(run)]
    print(f"Starting {args.stage} under {run}", flush=True)
    published = None
    with (run / "stdout.txt").open("xb") as stdout, (run / "stderr.txt").open("xb") as stderr:
        t0 = now()
        proc = subprocess.Popen(cmd, cwd=run, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, env=env)
        try:
            while proc.poll() is None:
                if fresh and published is None and (run / "output/envelope.json").exists():
                    published = now()
                if now() - t0 > 1200 * 10**9:
                    raise TimeoutError("1200 s finite process budget")
                time.sleep(.04)
            end = now()
        finally:
            if proc.poll() is None:
                subprocess.run([str(Path(env["SystemRoot"]) / "System32/taskkill.exe"), "/PID", str(proc.pid),
                                "/T", "/F"], check=True, capture_output=True)
                proc.wait(timeout=10)
    receipt = dict(stage=args.stage, run=str(run), cmd=cmd, supervisor_pid=os.getpid(), launched_pid=proc.pid,
                   process_start_ns=t0, process_observed_exit_ns=end, exit_code=proc.returncode,
                   process_wait_s=(end-t0)/1e9, envelope_observed_ns=published,
                   envelope_wait_s=(published-t0)/1e9 if published else None, poll_s=.04)
    dump(run / "process.json", receipt)
    assert proc.returncode == 0, (run, proc.returncode)
    if fresh:
        dump(run / "score.json", assess(key, run / "output"))
    print(receipt, flush=True)


if __name__ == "__main__":
    main()
