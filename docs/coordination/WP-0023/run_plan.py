"""Launch the frozen staged trial once and record the child exit separately from the gate verdict."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "docs/research/WP-0014/eld-latency-author"))
from probe import isolated_env


def main(plan_path, digest):
    raw = plan_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("Trial plan digest changed")
    plan = json.loads(raw)
    out = Path(plan["output"])
    if out.parent != Path("C:/Users/jackg/eLedgerCare-Speed/WP-0023/review/runs") or Path.cwd() != ROOT:
        raise ValueError("Unexpected output root or checkout")
    if subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() != plan["candidate"]:
        raise ValueError("Trial candidate changed")
    out.mkdir(parents=True, exist_ok=False)
    env = isolated_env(out)
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    argv = [sys.executable, "-I", "-B", str(ROOT / "docs/research/WP-0023/trial/run.py"),
            "--plan", str(plan_path), "--output", str(out)]
    start_utc = datetime.now(timezone.utc).isoformat()
    start = time.perf_counter()
    with (out / "stdout.txt").open("xb") as stdout, (out / "stderr.txt").open("xb") as stderr:
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, env=env, cwd=ROOT)
    record = {"all_segments_completed": result.returncode == 0, "segments": [
        {"label": "staged development pair", "returncode": result.returncode, "start_utc": start_utc,
         "end_utc": datetime.now(timezone.utc).isoformat(), "wall_s": time.perf_counter() - start,
         "argv": argv, "candidate": plan["candidate"], "plan_sha256": digest}]}
    with (out / "process.json").open("x", encoding="utf8", newline="\n") as f:
        json.dump(record, f, indent=2)
        f.write("\n")
    return result.returncode


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan", type=Path)
    p.add_argument("sha256")
    args = p.parse_args()
    sys.exit(main(args.plan, args.sha256))
