"""Supervisor for WP-0015 Carbon Baidu BF16 trials.

Enforces exact frozen Git source, plan SHA-256, >=20 GiB free disk, <=3.5 GiB owned
runtime ceiling, >=12,000 MiB free VRAM admission, and serialized 1-child-at-a-time
process isolation across contiguous mode segments.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ASTRA = ROOT / "docs/research/WP-0015/astra"
WP14 = ROOT / "docs/research/WP-0014/eld-latency-author"
WORKER = ROOT / "workers/local_ocr"
sys.path[:0] = [str(HERE), str(ASTRA), str(WP14), str(WORKER)]

from cases import GPU, PYTHON
from engine import MODES
from formats import digest, publish
from local_ocr.env_guard import verify_storage_guards
from probe import isolated_env

PACKET = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0015")
MIN_FREE_DISK_BYTES = 20 * 2**30
MAX_OWNER_RUNTIME_BYTES = int(3.5 * 2**30)
SCOPES = (
    "docs/research/WP-0015/carbon",
    "docs/research/WP-0015/astra",
    "docs/research/WP-0014/eld-latency-author",
    "workers/local_ocr",
    "docs/evaluation/WP-0015",
)
SMI = Path(os.environ["SystemRoot"]) / "System32/nvidia-smi.exe"


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], encoding="utf-8").strip()


def gpu_observation() -> dict:
    cmd = [
        str(SMI),
        "--query-gpu=uuid,memory.free,memory.used,temperature.gpu,utilization.gpu,driver_version",
        "--format=csv,noheader,nounits",
        "--id=" + GPU,
    ]
    row = subprocess.check_output(cmd, encoding="utf-8", timeout=10).strip().split(", ")
    if row[0] != GPU:
        raise ValueError(f"wrong GPU UUID: {row[0]}")
    return dict(
        uuid=row[0],
        free_mib=int(row[1]),
        used_mib=int(row[2]),
        temperature_c=int(row[3]),
        utilization_percent=int(row[4]),
        driver=row[5],
    )


def split_contiguous_segments(requests: list[dict]) -> list[tuple[str, list[dict]]]:
    segments: list[tuple[str, list[dict]]] = []
    for req in requests:
        mode = req["mode"]
        if not segments or segments[-1][0] != mode:
            segments.append((mode, [req]))
        else:
            segments[-1][1].append(req)
    return segments


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True, help="Exact 40-hex frozen commit SHA")
    p.add_argument("--plan", type=Path, required=True, help="Absolute path to frozen plan JSON")
    p.add_argument("--sha256", required=True, help="Expected SHA-256 of plan JSON bytes")
    p.add_argument("--owner", choices=["carbon", "review"], required=True)
    p.add_argument("--run", required=True, help="New unique run label")
    p.add_argument("--seconds", type=int, required=True, help="Total wall-clock timeout in seconds (1..10800)")
    p.add_argument("--lease", required=True, help="Coordinator-supplied GPU lease ID")
    p.add_argument("--min-vram-mib", type=int, default=12000)
    args = p.parse_args()

    if not re.fullmatch(r"[\w-]{1,64}", args.run) or not 1 <= args.seconds <= 10800:
        p.error("invalid run name or time budget")
    if not re.fullmatch(r"[a-f0-9]{40}", args.source):
        p.error("source must be a full 40-hex commit SHA")
    if not args.plan.is_absolute():
        p.error("plan path must be absolute")

    for scope in SCOPES:
        if git("rev-parse", f"{args.source}:{scope}") != git("rev-parse", f"HEAD:{scope}") or git(
            "status", "--porcelain", "--", scope
        ):
            raise ValueError("source differs from frozen clean revision: " + scope)

    data = args.plan.read_bytes()
    if digest(data) != args.sha256:
        raise ValueError("plan SHA-256 mismatch")
    plan_obj = json.loads(data)
    requests = plan_obj.get("requests") or []
    if not requests:
        raise ValueError("empty request list")

    for r in requests:
        if (
            not re.fullmatch(r"[a-z0-9-]{1,28}", r["label"])
            or r["mode"] not in MODES
            or not isinstance(r["warmup"], bool)
            or not 1 <= r["pages"] <= 60
            or not re.fullmatch(r"[a-f0-9]{64}", r["sha256"])
            or not Path(r["pdf"]).is_absolute()
            or (r.get("rgb_sha256") and len(r["rgb_sha256"]) != r["pages"])
        ):
            raise ValueError(f"invalid request entry: {r!r}")

    owner_root = PACKET / args.owner
    owner_root.mkdir(parents=True, exist_ok=True)
    storage_before = verify_storage_guards(
        owner_root, min_free_bytes=MIN_FREE_DISK_BYTES, max_root_bytes=MAX_OWNER_RUNTIME_BYTES
    )

    run = owner_root / "runs" / args.run
    run.mkdir(parents=True, exist_ok=False)
    publish(run / "plan.json", data)

    start_gpu = gpu_observation()
    if start_gpu["free_mib"] < args.min_vram_mib:
        raise ValueError(f"admission VRAM floor not met: free={start_gpu['free_mib']} MiB < {args.min_vram_mib} MiB")

    segments = split_contiguous_segments(requests)
    begin = time.perf_counter()
    publish(
        run / "launch.json",
        dict(
            source=args.source,
            head=git("rev-parse", "HEAD"),
            lease=args.lease,
            seconds=args.seconds,
            min_vram_mib=args.min_vram_mib,
            max_owner_runtime_bytes=MAX_OWNER_RUNTIME_BYTES,
            min_free_disk_bytes=MIN_FREE_DISK_BYTES,
            storage_before=storage_before,
            plan_path=str(args.plan),
            plan_sha256=args.sha256,
            segment_count=len(segments),
            segment_modes=[m for m, _ in segments],
            initial_gpu=start_gpu,
            supervisor_pid=os.getpid(),
            start_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        ),
    )

    samples = []
    segment_receipts = []
    overall_reason = None

    for seg_idx, (mode, seg_reqs) in enumerate(segments, 1):
        elapsed_before_seg = time.perf_counter() - begin
        if elapsed_before_seg >= args.seconds:
            overall_reason = "time_budget_exhausted_before_segment"
            break
        seg_storage = verify_storage_guards(
            owner_root, min_free_bytes=MIN_FREE_DISK_BYTES, max_root_bytes=MAX_OWNER_RUNTIME_BYTES
        )
        seg_gpu_pre = gpu_observation()
        if seg_gpu_pre["free_mib"] < args.min_vram_mib:
            overall_reason = f"segment_{seg_idx}_vram_floor_failed:{seg_gpu_pre['free_mib']}"
            break

        seg_dir = run / f"segment-{seg_idx:02d}-{mode}"
        seg_dir.mkdir(parents=True, exist_ok=False)
        publish(seg_dir / "plan.json", dict(mode=mode, requests=seg_reqs))
        env = isolated_env(seg_dir)
        cmd = [str(PYTHON), "-I", "-B", str(HERE / "trial.py"), str(seg_dir)]

        seg_begin = time.perf_counter()
        seg_reason = None
        with (seg_dir / "stdout.txt").open("xb") as out, (seg_dir / "stderr.txt").open("xb") as err:
            child = subprocess.Popen(cmd, cwd=seg_dir, env=env, stdout=out, stderr=err, stdin=subprocess.DEVNULL)
            try:
                while child.poll() is None:
                    observed = time.perf_counter() - begin
                    if observed >= args.seconds:
                        seg_reason = "time_budget_exceeded"
                        break
                    if shutil.disk_usage(run).free < MIN_FREE_DISK_BYTES:
                        seg_reason = "free_disk_floor_violated"
                        break
                    if not samples or observed - samples[-1]["s"] >= 5.0:
                        samples.append(dict(s=round(observed, 3), segment=seg_idx, mode=mode, **gpu_observation()))
                    time.sleep(0.15)
            finally:
                if child.poll() is None:
                    subprocess.run(
                        [str(Path(env["SystemRoot"]) / "System32/taskkill.exe"), "/PID", str(child.pid), "/T", "/F"],
                        capture_output=True,
                    )
                    child.wait(timeout=10)
        child_meta = json.loads((seg_dir / "child.json").read_bytes()) if (seg_dir / "child.json").exists() else None
        rec = dict(
            segment=seg_idx,
            mode=mode,
            cmd=cmd,
            pid=child.pid,
            child_meta=child_meta,
            returncode=child.returncode,
            elapsed_s=time.perf_counter() - seg_begin,
            reason=seg_reason,
            storage_before_segment=seg_storage,
            gpu_before_segment=seg_gpu_pre,
            gpu_after_segment=gpu_observation(),
        )
        publish(seg_dir / "segment-process.json", rec)
        segment_receipts.append(rec)
        if seg_reason is not None or child.returncode != 0:
            overall_reason = seg_reason or f"segment_{seg_idx}_nonzero_exit_{child.returncode}"
            break

    final_gpu = gpu_observation()
    storage_after = verify_storage_guards(
        owner_root, min_free_bytes=MIN_FREE_DISK_BYTES, max_root_bytes=MAX_OWNER_RUNTIME_BYTES
    )
    publish(
        run / "process.json",
        dict(
            segments=segment_receipts,
            all_segments_completed=(overall_reason is None and len(segment_receipts) == len(segments)),
            overall_reason=overall_reason,
            elapsed_s=time.perf_counter() - begin,
            gpu_samples=samples,
            final_gpu=final_gpu,
            storage_after=storage_after,
            end_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        ),
    )
    return 0 if (overall_reason is None and len(segment_receipts) == len(segments)) else 1


if __name__ == "__main__":
    sys.exit(main())
