"""Self-contained WP-0017 supervisor launcher for Stage A1 window forensics and Stage A2/A3 trials.

Enforces:
  - Exact 40-hex frozen Git commit SHA and clean working tree across all runtime scopes
  - Plan JSON SHA-256 verification (accepts direct a1-inputs.json, bound A1 plan JSON, or A2/A3 requests plan JSON)
  - >=20 GiB free disk floor, <=3.5 GiB owner runtime ceiling, >=12,000 MiB free VRAM admission
  - Serialized 1-child-at-a-time fresh process isolation (python.exe -I -B)
  - Direct process exit code + run/process.json compatible with coordinator device_lease.py
  - Post-run Stage A1 endpoint token-hash verification before any attribution summary

No torch or CUDA module is imported in the supervisor process.
"""
from __future__ import annotations

import argparse
from io import TextIOWrapper
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if isinstance(_stream, TextIOWrapper):
        _stream.reconfigure(encoding="utf-8", errors=_stream.errors)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WP15_CARBON = ROOT / "docs/research/WP-0015/carbon"
WP15_ASTRA = ROOT / "docs/research/WP-0015/astra"
WP14 = ROOT / "docs/research/WP-0014/eld-latency-author"
WORKER = ROOT / "workers/local_ocr"
for _p in reversed((str(HERE), str(WP15_CARBON), str(WP15_ASTRA), str(WP14), str(WORKER))):
    if _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

from a1_analyze import analyze_a1_segments
from cases import GPU, PYTHON
from formats import digest, publish
from local_ocr.env_guard import verify_storage_guards
from probe import isolated_env
from switches import CANONICAL_A1_CONFIGS, resolve_mode

DEFAULT_PACKET_ROOT = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0017")
DEFAULT_A1_MANIFEST = DEFAULT_PACKET_ROOT / "coordination/a1-inputs.json"
DEFAULT_WARM_PDF = WP14 / "A.pdf"
DEFAULT_WARM_SHA256 = "25c14530845cad96329b528f860032c27a1259ed46de3ccb56f0e57730aa0858"
DEFAULT_WARM_RGB_SHA256 = "a189916661ad64469762ea65a693b49c0d59ca2508df2742cc5d92b60f7dd18d"

MIN_FREE_DISK_BYTES = 20 * 2**30
MAX_OWNER_RUNTIME_BYTES = int(3.5 * 2**30)
SCOPES = (
    "docs/research/WP-0017/engine",
    "docs/research/WP-0015/carbon",
    "docs/research/WP-0015/astra",
    "docs/research/WP-0014/eld-latency-author",
    "workers/local_ocr",
    "docs/evaluation/WP-0015",
)
SMI = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/nvidia-smi.exe"


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], encoding="utf-8").strip()


def verify_git_scopes(source_sha: str, scopes: tuple[str, ...] = SCOPES) -> None:
    for scope in scopes:
        if git("rev-parse", f"{source_sha}:{scope}") != git("rev-parse", f"HEAD:{scope}") or git(
            "status", "--porcelain", "--", scope
        ):
            raise ValueError("source differs from frozen clean revision: " + scope)


def parse_gpu_observation(line: str) -> dict:
    row = line.strip().split(", ")
    if row[0] != GPU:
        raise ValueError(f"wrong GPU UUID: {row[0]}")
    return dict(
        uuid=row[0],
        free_mib=int(row[1]),
        used_mib=int(row[2]),
        temperature_c=float(row[3]),
        utilization_percent=int(row[4]),
        driver=row[5],
    )


def gpu_observation() -> dict:
    cmd = [
        str(SMI),
        "--query-gpu=uuid,memory.free,memory.used,temperature.gpu,utilization.gpu,driver_version",
        "--format=csv,noheader,nounits",
        "--id=" + GPU,
    ]
    return parse_gpu_observation(subprocess.check_output(cmd, encoding="utf-8", timeout=10))


def build_default_warmups(count: int) -> list[dict]:
    if not 0 <= count <= 5:
        raise ValueError(f"warmup_count must be in 0..5, got {count}")
    return [
        {
            "label": f"warm-{i}",
            "warmup": True,
            "pages": 1,
            "pdf": str(DEFAULT_WARM_PDF),
            "sha256": DEFAULT_WARM_SHA256,
            "rgb_sha256": [DEFAULT_WARM_RGB_SHA256],
        }
        for i in range(1, count + 1)
    ]


def build_canonical_a1_plan(
    *,
    a1_manifest_path: Path = DEFAULT_A1_MANIFEST,
    configs: list[str] | tuple[str, ...] = CANONICAL_A1_CONFIGS,
    warmup_count: int = 3,
    endpoint_probe_repeats: int = 2,
    addition_probe_repeats: int = 2,
    removal_probe_repeats: int = 1,
    auto_pair_removals: bool = False,
) -> dict:
    manifest_bytes = a1_manifest_path.read_bytes()
    manifest_sha = digest(manifest_bytes)
    manifest_obj = json.loads(manifest_bytes)
    if manifest_obj.get("stage") != "A1" or not manifest_obj.get("windows"):
        raise ValueError(f"Invalid A1 manifest at {a1_manifest_path}")
    for c in configs:
        resolve_mode(c)
    return {
        "schema": "eledgercare.wp0017.a1-plan/1",
        "stage": "A1",
        "a1_manifest": str(a1_manifest_path.resolve()),
        "a1_manifest_sha256": manifest_sha,
        "configs": list(configs),
        "warmups": build_default_warmups(warmup_count),
        "endpoint_probe_repeats": int(endpoint_probe_repeats),
        "addition_probe_repeats": int(addition_probe_repeats),
        "removal_probe_repeats": int(removal_probe_repeats),
        "auto_pair_removals": bool(auto_pair_removals),
    }


def split_contiguous_segments(requests: list[dict]) -> list[tuple[str, list[dict]]]:
    segments: list[tuple[str, list[dict]]] = []
    for req in requests:
        mode = req["mode"]
        if not segments or segments[-1][0] != mode:
            segments.append((mode, [req]))
        else:
            segments[-1][1].append(req)
    return segments


def _probe_repeats_for_mode(mode: str, *, endpoint_rep: int, add_rep: int, rem_rep: int) -> int:
    res = resolve_mode(mode)
    if res.family in ("genuine_endpoint", "endpoint_proof"):
        return endpoint_rep
    if res.family == "single_add":
        return add_rep
    return rem_rep


def _run_child_segment(
    *,
    seg_idx: int,
    mode: str,
    seg_dir: Path,
    child_script: Path,
    begin_perf: float,
    total_seconds: int,
    min_vram_mib: int,
    owner_root: Path,
    samples: list[dict],
) -> tuple[dict, str | None]:
    elapsed_before = time.perf_counter() - begin_perf
    if elapsed_before >= total_seconds:
        return {}, "time_budget_exhausted_before_segment"

    seg_storage = verify_storage_guards(
        owner_root, min_free_bytes=MIN_FREE_DISK_BYTES, max_root_bytes=MAX_OWNER_RUNTIME_BYTES
    )
    seg_gpu_pre = gpu_observation()
    if seg_gpu_pre["free_mib"] < min_vram_mib:
        return {}, f"segment_{seg_idx}_vram_floor_failed:{seg_gpu_pre['free_mib']}"

    env = isolated_env(seg_dir)
    cmd = [str(PYTHON), "-I", "-B", str(child_script), str(seg_dir)]

    seg_begin = time.perf_counter()
    seg_reason = None
    with (seg_dir / "stdout.txt").open("xb") as out, (seg_dir / "stderr.txt").open("xb") as err:
        child = subprocess.Popen(cmd, cwd=seg_dir, env=env, stdout=out, stderr=err, stdin=subprocess.DEVNULL)
        try:
            while child.poll() is None:
                observed = time.perf_counter() - begin_perf
                if observed >= total_seconds:
                    seg_reason = "time_budget_exceeded"
                    break
                if shutil.disk_usage(seg_dir).free < MIN_FREE_DISK_BYTES:
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
    if seg_reason is not None or child.returncode != 0:
        return rec, (seg_reason or f"segment_{seg_idx}_nonzero_exit_{child.returncode}")
    return rec, None


def _validate_doc_request(r: dict, *, surgical_override: str | None = None) -> None:
    resolve_mode(str(r.get("mode", "")), surgical_override=surgical_override)
    if (
        not re.fullmatch(r"[a-z0-9_-]{1,28}", str(r.get("label", "")))
        or not isinstance(r.get("warmup"), bool)
        or not (isinstance(r.get("pages"), int) and 1 <= r["pages"] <= 60)
        or not re.fullmatch(r"[a-f0-9]{64}", str(r.get("sha256", "")))
        or not Path(str(r.get("pdf", ""))).is_absolute()
        or (r.get("rgb_sha256") and len(r["rgb_sha256"]) != r["pages"])
    ):
        raise ValueError(f"invalid request entry: {r!r}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--emit-a1-plan", type=Path, help="CPU-only helper: write canonical Stage A1 plan JSON and print SHA-256")
    p.add_argument("--a1-manifest", type=Path, default=DEFAULT_A1_MANIFEST, help="Path to a1-inputs.json for --emit-a1-plan")
    p.add_argument("--source", help="Exact 40-hex frozen commit SHA")
    p.add_argument("--plan", type=Path, help="Absolute path to frozen plan JSON (or a1-inputs.json directly)")
    p.add_argument("--sha256", help="Expected 64-hex SHA-256 of --plan bytes")
    p.add_argument("--owner", choices=["carbon", "review"], help="Runtime owner directory")
    p.add_argument("--run", help="New unique run label")
    p.add_argument("--seconds", type=int, help="Total wall-clock timeout in seconds (1..14400)")
    p.add_argument("--lease", help="Coordinator-supplied GPU lease ID")
    p.add_argument("--min-vram-mib", type=int, default=12000)
    p.add_argument("--packet-root", type=Path, default=DEFAULT_PACKET_ROOT)
    p.add_argument("--configs", help="Optional comma-separated config list when --plan points directly to a1-inputs.json")
    p.add_argument("--warmup-count", type=int, default=3, help="Settling 1-page warmups per child when --plan is a1-inputs.json")
    p.add_argument("--auto-pair-removals", action="store_true", help="Automatically run eligible pair removals if singles do not restore both IDs")
    args = p.parse_args(argv)

    if args.emit_a1_plan is not None:
        cfg_list = [c.strip() for c in args.configs.split(",") if c.strip()] if args.configs else list(CANONICAL_A1_CONFIGS)
        plan_doc = build_canonical_a1_plan(
            a1_manifest_path=args.a1_manifest,
            configs=cfg_list,
            warmup_count=args.warmup_count,
            auto_pair_removals=args.auto_pair_removals,
        )
        encoded = (json.dumps(plan_doc, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
        args.emit_a1_plan.parent.mkdir(parents=True, exist_ok=True)
        sha = publish(args.emit_a1_plan, encoded)
        print(json.dumps({"plan_path": str(args.emit_a1_plan.resolve()), "plan_sha256": sha, "configs": cfg_list}))
        return 0

    for req_arg in ("source", "plan", "sha256", "owner", "run", "seconds", "lease"):
        if getattr(args, req_arg) is None:
            p.error(f"--{req_arg.replace('_', '-')} is required")

    if not re.fullmatch(r"[\w-]{1,64}", args.run) or not 1 <= args.seconds <= 14400:
        p.error("invalid run name or time budget (expected 1..14400 seconds)")
    if not re.fullmatch(r"[a-f0-9]{40}", args.source):
        p.error("source must be a full 40-hex commit SHA")
    if not args.plan.is_absolute():
        p.error("plan path must be absolute")

    verify_git_scopes(args.source)

    plan_bytes = args.plan.read_bytes()
    if digest(plan_bytes) != args.sha256.lower():
        raise ValueError("plan SHA-256 mismatch")
    plan_obj = json.loads(plan_bytes)

    is_a1 = (plan_obj.get("stage") == "A1") and ("windows" in plan_obj or "a1_manifest" in plan_obj)
    if not is_a1 and "requests" not in plan_obj:
        raise ValueError("Unsupported plan JSON: expected stage=='A1' or 'requests' list")

    # Pre-validate plan structure BEFORE creating run directory or touching GPU.
    if is_a1:
        if "windows" in plan_obj:
            a1_manifest_path = args.plan.resolve()
            a1_manifest_sha = args.sha256.lower()
            a1_manifest_obj = plan_obj
            configs = (
                [c.strip() for c in args.configs.split(",") if c.strip()]
                if args.configs
                else list(CANONICAL_A1_CONFIGS)
            )
            warmups = build_default_warmups(args.warmup_count)
            endpoint_rep, add_rep, rem_rep = 2, 2, 1
            auto_pairs = bool(args.auto_pair_removals)
        else:
            a1_manifest_path = Path(plan_obj["a1_manifest"]).resolve()
            a1_manifest_sha = str(plan_obj["a1_manifest_sha256"]).lower()
            m_bytes = a1_manifest_path.read_bytes()
            if digest(m_bytes) != a1_manifest_sha:
                raise ValueError("Referenced a1_manifest SHA-256 mismatch")
            a1_manifest_obj = json.loads(m_bytes)
            configs = list(plan_obj.get("configs") or CANONICAL_A1_CONFIGS)
            warmups = (
                list(plan_obj["warmups"])
                if "warmups" in plan_obj
                else build_default_warmups(int(plan_obj.get("warmup_count", args.warmup_count)))
            )
            endpoint_rep = int(plan_obj.get("endpoint_probe_repeats", 2))
            add_rep = int(plan_obj.get("addition_probe_repeats", 2))
            rem_rep = int(plan_obj.get("removal_probe_repeats", 1))
            auto_pairs = bool(plan_obj.get("auto_pair_removals", args.auto_pair_removals))

        if not configs:
            raise ValueError("Empty Stage A1 config list")
        surgical_override = plan_obj.get("surgical_override")
        for c in configs:
            resolve_mode(c, surgical_override=surgical_override)
        for w in warmups:
            _validate_doc_request({**w, "mode": "native"})
        req_a = a1_manifest_obj["request"]
        _validate_doc_request({**req_a, "mode": "native", "warmup": False})
    else:
        requests = plan_obj.get("requests") or []
        if not requests:
            raise ValueError("empty request list")
        surgical_override = plan_obj.get("surgical_override")
        for r in requests:
            _validate_doc_request(r, surgical_override=surgical_override)

    owner_root = args.packet_root / args.owner
    owner_root.mkdir(parents=True, exist_ok=True)
    storage_before = verify_storage_guards(
        owner_root, min_free_bytes=MIN_FREE_DISK_BYTES, max_root_bytes=MAX_OWNER_RUNTIME_BYTES
    )

    run_dir = owner_root / "runs" / args.run
    run_dir.mkdir(parents=True, exist_ok=False)
    publish(run_dir / "plan.json", plan_bytes)

    start_gpu = gpu_observation()
    if start_gpu["free_mib"] < args.min_vram_mib:
        raise ValueError(f"admission VRAM floor not met: free={start_gpu['free_mib']} MiB < {args.min_vram_mib} MiB")

    begin = time.perf_counter()
    samples: list[dict] = []
    segment_receipts: list[dict] = []
    overall_reason: str | None = None
    expected_segment_count: int = 0
    a1_summary_meta: dict | None = None

    if is_a1:
        expected_segment_count = len(configs)
        publish(
            run_dir / "launch.json",
            dict(
                stage="A1",
                source=args.source,
                head=git("rev-parse", "HEAD"),
                lease=args.lease,
                seconds=args.seconds,
                min_vram_mib=args.min_vram_mib,
                max_owner_runtime_bytes=MAX_OWNER_RUNTIME_BYTES,
                min_free_disk_bytes=MIN_FREE_DISK_BYTES,
                storage_before=storage_before,
                plan_path=str(args.plan),
                plan_sha256=args.sha256.lower(),
                a1_manifest=str(a1_manifest_path),
                a1_manifest_sha256=a1_manifest_sha,
                planned_configs=configs,
                warmup_count=len(warmups),
                auto_pair_removals=auto_pairs,
                initial_gpu=start_gpu,
                supervisor_pid=os.getpid(),
                start_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            ),
        )

        seg_summaries: list[dict] = []
        child_script = HERE / "a1_trial.py"

        for seg_idx, mode in enumerate(configs, 1):
            seg_dir = run_dir / f"segment-{seg_idx:02d}-{mode}"
            seg_dir.mkdir(parents=True, exist_ok=False)
            p_reps = _probe_repeats_for_mode(
                mode, endpoint_rep=endpoint_rep, add_rep=add_rep, rem_rep=rem_rep
            )
            publish(
                seg_dir / "segment-plan.json",
                dict(
                    stage="A1",
                    mode=mode,
                    surgical_override=surgical_override,
                    a1_manifest=str(a1_manifest_path),
                    a1_manifest_sha256=a1_manifest_sha,
                    warmups=warmups,
                    forced_native_probe_repeats=p_reps,
                ),
            )
            rec, err = _run_child_segment(
                seg_idx=seg_idx,
                mode=mode,
                seg_dir=seg_dir,
                child_script=child_script,
                begin_perf=begin,
                total_seconds=args.seconds,
                min_vram_mib=args.min_vram_mib,
                owner_root=owner_root,
                samples=samples,
            )
            if rec:
                segment_receipts.append(rec)
            if err is not None:
                overall_reason = err
                break
            seg_summaries.append(json.loads((seg_dir / "segment-summary.json").read_bytes()))

        # Optional dynamic Stage-A1b pair-removal continuation if enabled and needed.
        if overall_reason is None and auto_pairs:
            interim = analyze_a1_segments(seg_summaries, a1_manifest_obj)
            missing_pairs = list(interim.get("missing_pair_removals") or [])
            if interim.get("pair_removals_needed") and missing_pairs:
                expected_segment_count += len(missing_pairs)
                base_idx = len(segment_receipts)
                for offset, pmode in enumerate(missing_pairs, 1):
                    seg_idx = base_idx + offset
                    seg_dir = run_dir / f"segment-{seg_idx:02d}-{pmode}"
                    seg_dir.mkdir(parents=True, exist_ok=False)
                    publish(
                        seg_dir / "segment-plan.json",
                        dict(
                            stage="A1",
                            mode=pmode,
                            surgical_override=surgical_override,
                            a1_manifest=str(a1_manifest_path),
                            a1_manifest_sha256=a1_manifest_sha,
                            warmups=warmups,
                            forced_native_probe_repeats=rem_rep,
                        ),
                    )
                    rec, err = _run_child_segment(
                        seg_idx=seg_idx,
                        mode=pmode,
                        seg_dir=seg_dir,
                        child_script=child_script,
                        begin_perf=begin,
                        total_seconds=args.seconds,
                        min_vram_mib=args.min_vram_mib,
                        owner_root=owner_root,
                        samples=samples,
                    )
                    if rec:
                        segment_receipts.append(rec)
                    if err is not None:
                        overall_reason = err
                        break
                    seg_summaries.append(json.loads((seg_dir / "segment-summary.json").read_bytes()))

        if seg_summaries:
            a1_summary = analyze_a1_segments(seg_summaries, a1_manifest_obj)
            summary_sha = publish(run_dir / "a1-summary.json", a1_summary)
            a1_summary_meta = {
                "a1_summary_sha256": summary_sha,
                "anchor_gate_passed": a1_summary["anchor_verification"]["anchor_gate_passed"],
                "attribution_status": a1_summary["attribution_status"],
                "surgical_selection_status": a1_summary["surgical_selection_status"],
                "recommended_surgical_mode": a1_summary.get("recommended_surgical_mode"),
                "recommended_surgical_bits": a1_summary.get("recommended_surgical_bits"),
            }
    else:
        segments = split_contiguous_segments(requests)
        expected_segment_count = len(segments)
        publish(
            run_dir / "launch.json",
            dict(
                stage=plan_obj.get("stage", "DOC"),
                source=args.source,
                head=git("rev-parse", "HEAD"),
                lease=args.lease,
                seconds=args.seconds,
                min_vram_mib=args.min_vram_mib,
                max_owner_runtime_bytes=MAX_OWNER_RUNTIME_BYTES,
                min_free_disk_bytes=MIN_FREE_DISK_BYTES,
                storage_before=storage_before,
                plan_path=str(args.plan),
                plan_sha256=args.sha256.lower(),
                segment_count=len(segments),
                segment_modes=[m for m, _ in segments],
                initial_gpu=start_gpu,
                supervisor_pid=os.getpid(),
                start_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            ),
        )
        child_script = HERE / "doc_trial.py"
        for seg_idx, (mode, seg_reqs) in enumerate(segments, 1):
            seg_dir = run_dir / f"segment-{seg_idx:02d}-{mode}"
            seg_dir.mkdir(parents=True, exist_ok=False)
            publish(
                seg_dir / "plan.json",
                dict(mode=mode, surgical_override=surgical_override, requests=seg_reqs),
            )
            rec, err = _run_child_segment(
                seg_idx=seg_idx,
                mode=mode,
                seg_dir=seg_dir,
                child_script=child_script,
                begin_perf=begin,
                total_seconds=args.seconds,
                min_vram_mib=args.min_vram_mib,
                owner_root=owner_root,
                samples=samples,
            )
            if rec:
                segment_receipts.append(rec)
            if err is not None:
                overall_reason = err
                break

    final_gpu = gpu_observation()
    storage_after = verify_storage_guards(
        owner_root, min_free_bytes=MIN_FREE_DISK_BYTES, max_root_bytes=MAX_OWNER_RUNTIME_BYTES
    )
    all_done = (overall_reason is None and len(segment_receipts) == expected_segment_count)
    proc_doc = dict(
        segments=segment_receipts,
        all_segments_completed=all_done,
        overall_reason=overall_reason,
        elapsed_s=time.perf_counter() - begin,
        gpu_samples=samples,
        final_gpu=final_gpu,
        storage_after=storage_after,
        end_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
    if a1_summary_meta is not None:
        proc_doc["a1_summary"] = a1_summary_meta
    publish(run_dir / "process.json", proc_doc)
    return 0 if all_done else 1


if __name__ == "__main__":
    sys.exit(main())
