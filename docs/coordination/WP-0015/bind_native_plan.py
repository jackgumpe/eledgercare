"""Bind one finite Astra-harness plan to Git source, input bytes and a fresh host observation."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from observe_host import PACKET_ROOT, snapshot

HERE = Path(__file__).resolve().parent


def bind(args):
    state = snapshot()
    if state["free_mib"] < 12000 or state["volume_free_bytes"] < 20 * 2**30 or state["ollama_loaded_model_count"]:
        raise ValueError("Workstation capacity or model ownership requires a new observation")
    worktree = args.worktree.resolve(strict=True)
    plan = args.plan.resolve(strict=True)
    sha = lambda d: hashlib.sha256(d).hexdigest()
    plan_bytes = plan.read_bytes()
    if sha(plan_bytes) != args.digest:
        raise ValueError("Plan digest mismatch")
    src = subprocess.check_output(["git", "-C", worktree, "rev-parse", args.source + "^{commit}"], text=True).strip()
    if src != args.source:
        raise ValueError("Full source revision required")
    requests = json.loads(plan_bytes)["requests"]
    inputs = []
    for r in requests:
        file = Path(r["pdf"])
        if sha(file.read_bytes()) != r["sha256"] or len(r["rgb_sha256"]) != r["pages"]:
            raise ValueError("PDF or rendered manifest mismatch")
        inputs.append({k: r[k] for k in ("label", "mode", "pages", "warmup", "sha256", "rgb_sha256")})
    windows = sum((r["pages"] + 2) // 3 for r in requests if r["mode"] == "native")
    if not 0 < args.seconds <= 10800:
        raise ValueError("Lease duration outside per-session ceiling")
    dest = HERE / (args.lease + "-release.json")
    run = PACKET_ROOT / args.owner / "runs" / args.run
    if run.exists() or dest.exists():
        raise FileExistsError("Lease and output directory must be fresh")
    app = ["python", "-I", "-B", "docs/research/WP-0015/astra/launch.py", "--source", src,
           "--plan", str(plan), "--sha256", args.digest, "--owner", args.owner,
           "--run", args.run, "--seconds", str(args.seconds), "--lease", args.lease]
    receipt = {"issued_utc": datetime.now(timezone.utc).isoformat(), "lease": args.lease,
               "owner": args.owner, "source": src, "custody": args.custody, "plan_sha256": args.digest,
               "worktree": str(worktree), "expected_output": str(run), "seconds": args.seconds,
               "maximum_native_window_calls": windows, "ordered_requests": inputs,
               "ready_waits": "excluded warm-up and process load, followed by complete accepted-input to durable result",
               "observed_host": state, "argv": app}
    with dest.open("x", encoding="utf8", newline="\n") as file:
        json.dump(receipt, file, indent=2)
        file.write("\n")
    print(str(dest), len(requests), "requests,", windows, "native windows,", args.seconds, "seconds")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--owner", choices=["astra", "review"], required=True)
    for name in ("source", "custody", "digest", "run", "lease"):
        p.add_argument("--" + name, required=True)
    for name in ("worktree", "plan"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--seconds", required=True, type=int)
    bind(p.parse_args())
