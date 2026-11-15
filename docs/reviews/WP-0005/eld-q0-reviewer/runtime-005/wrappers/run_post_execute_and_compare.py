"""WP-0005 /005 post-execution worker-exit / lease-return verification, model/module-cache
reverification, full run-directory inventory, and author-vs-reviewer comparison.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REVIEWER_WT = Path(r"C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-reviewer-carbon")
HARNESS_DIR = REVIEWER_WT / "qualification" / "q0" / "harness"
Q0_PY = HARNESS_DIR / "q0.py"
MAIN_REPO = Path(r"C:\Users\jackg\Asp.net Projects\eledgercare")
AUTHOR_SNAPSHOT = MAIN_REPO / "docs" / "coordination" / "WP-0005" / "gpu-reviewer-release" / "author-run-snapshot"

TASK_ROOT = Path(r"C:\Users\jackg\eLedgerCare-Q0\WP-0005")
VENV_PY = TASK_ROOT / "venv" / "Scripts" / "python.exe"
MODEL_DIR = TASK_ROOT / "models" / "Unlimited_OCR_2_04809669"
NOTICE_DIR = TASK_ROOT / "notices" / "Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a"
AUTHOR_RUN_DIR = TASK_ROOT / "runs" / "author" / "20261115T202627Z-eb5bf7da"
REVIEWER_RUNS_ROOT = TASK_ROOT / "runs" / "reviewer"

OUT_DIR = Path(__file__).resolve().parent / "post-execute"
OUTSIDE_CWD = Path(__file__).resolve().parent / "cwd"

sys.path.insert(0, str(HARNESS_DIR))
from q0harness.environment import build_stage_env  # noqa: E402
from q0harness.modelfiles import verify_module_cache  # noqa: E402
from q0harness.protocol import load_protocol  # noqa: E402


def sha256_b(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> tuple[int, str]:
    h = hashlib.sha256()
    total = 0
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
            total += len(chunk)
    return total, h.hexdigest()


def observe_worker_exit_and_gpu(run_dir: Path, sup_pid: int | None, hb_pid: int | None) -> dict:
    ps_cmd = (
        "$procs = Get-CimInstance Win32_Process -Filter \"Name = 'python.exe' OR Name = 'pythonw.exe'\" | "
        "Select-Object ProcessId, ParentProcessId, Name, ExecutablePath, CommandLine; "
        "ConvertTo-Json -InputObject @($procs) -Compress"
    )
    cp_p = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30, check=True,
    )
    all_py = json.loads(cp_p.stdout or "[]")
    if isinstance(all_py, dict):
        all_py = [all_py]
    self_pid = os.getpid()
    other_py = [p for p in all_py if p.get("ProcessId") != self_pid]

    tracked_pids = sorted({p for p in (sup_pid, hb_pid) if isinstance(p, int)})
    tracked_still_alive = [p for p in other_py if p.get("ProcessId") in tracked_pids]
    q0_matching = [
        p for p in other_py
        if (
            str(run_dir) in (p.get("CommandLine") or "")
            or "q0.py" in (p.get("CommandLine") or "")
            or "eLedgerCare-Q0\\WP-0005" in (p.get("CommandLine") or "")
            or "eLedgerCare-Q0\\WP-0005" in (p.get("ExecutablePath") or "")
        )
    ]

    gpu_q = subprocess.run(
        [
            "nvidia-smi",
            "--id=GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d",
            "--query-gpu=timestamp,uuid,name,driver_version,compute_cap,memory.total,memory.used,memory.free,utilization.gpu,pstate",
            "--format=csv,noheader,nounits",
        ],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30, check=True,
    ).stdout.strip()
    gpu_apps = subprocess.run(
        [
            "nvidia-smi",
            "--id=GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d",
            "--query-compute-apps=pid,process_name,used_gpu_memory",
            "--format=csv,noheader,nounits",
        ],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30, check=True,
    ).stdout.strip()

    all_absent = (len(tracked_still_alive) == 0 and len(q0_matching) == 0)
    observed_utc = datetime.now(timezone.utc).isoformat()
    return {
        "schema": "eld-q0-reviewer-005-lease-return/1",
        "observed_utc": observed_utc,
        "lease_id": "WP-0005-reviewer-005-20261115T205527Z",
        "gpu_uuid": "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d",
        "owner": "eld-q0-reviewer",
        "reviewer_session": "0815536f-045a-4112-8a89-ebf0e0cc782f",
        "reviewer_run_dir": str(run_dir),
        "observer_python_pid": self_pid,
        "supervisor_child_pid": sup_pid,
        "heartbeat_worker_pid": hb_pid,
        "tracked_worker_pids_checked": tracked_pids,
        "tracked_worker_pids_still_alive": tracked_still_alive,
        "active_q0_worker_processes": q0_matching,
        "all_owned_workers_absent": all_absent,
        "lease_status": "RETURNED" if all_absent else "ACTIVE_UNRETURNED",
        "nvidia_smi_gpu": gpu_q,
        "nvidia_smi_compute_apps": gpu_apps.splitlines() if gpu_apps else [],
    }


def inventory_run_dir(run_dir: Path) -> dict:
    entries = []
    total_bytes = 0
    for fp in sorted(run_dir.rglob("*")):
        if fp.is_file():
            rel = fp.relative_to(run_dir).as_posix()
            sz, digest = sha256_file(fp)
            total_bytes += sz
            entries.append({"path": rel, "bytes": sz, "sha256": digest})
    return {
        "run_dir": str(run_dir),
        "run_id": run_dir.name,
        "file_count": len(entries),
        "total_bytes": total_bytes,
        "files": entries,
    }


def strip_boxes(text: str) -> tuple[str, list[tuple[int, int, int, int]]]:
    box_re = re.compile(r"\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]")
    coords = [(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))) for m in box_re.finditer(text)]
    stripped = box_re.sub("[]", text)
    return stripped, coords


def compare_runs(rev_dir: Path, auth_snap_dir: Path) -> dict:
    rev_sup = json.loads((rev_dir / "supervisor.json").read_text(encoding="utf-8"))
    auth_sup = json.loads((auth_snap_dir / "supervisor.json").read_text(encoding="utf-8"))
    rev_out = json.loads((rev_dir / "evidence" / "outcome.json").read_text(encoding="utf-8"))
    auth_out = json.loads((auth_snap_dir / "evidence" / "outcome.json").read_text(encoding="utf-8"))

    labels = ["F01.warmup", "F07.warmup", "F01.warm1", "F07.warm1", "F01.warm2", "F07.warm2"]
    rev_obs_by_label = {o["label"]: o for o in rev_out["observations"]}
    auth_obs_by_label = {o["label"]: o for o in auth_out["observations"]}

    per_call = []
    for lbl in labels:
        ro = rev_obs_by_label[lbl]
        ao = auth_obs_by_label[lbl]
        r_toks = json.loads((rev_dir / "evidence" / f"{lbl}.token_ids.json").read_text(encoding="utf-8"))
        a_toks = json.loads((auth_snap_dir / "evidence" / f"{lbl}.token_ids.json").read_text(encoding="utf-8"))
        r_raw = (rev_dir / "evidence" / f"{lbl}.raw.txt").read_text(encoding="utf-8")
        a_raw = (auth_snap_dir / "evidence" / f"{lbl}.raw.txt").read_text(encoding="utf-8")

        diff_positions = [
            {"index": i, "author_token": a, "reviewer_token": b}
            for i, (a, b) in enumerate(zip(a_toks, r_toks))
            if a != b
        ]
        r_stripped, r_boxes = strip_boxes(r_raw)
        a_stripped, a_boxes = strip_boxes(a_raw)
        max_box_delta = None
        if len(r_boxes) == len(a_boxes) and r_boxes:
            max_box_delta = max(
                abs(rv - av)
                for rb, ab in zip(r_boxes, a_boxes)
                for rv, av in zip(rb, ab)
            )

        per_call.append({
            "label": lbl,
            "fixture_id": ro["fixture_id"],
            "kind": ro["kind"],
            "author_output_tokens": ao["native"]["output_tokens"],
            "reviewer_output_tokens": ro["native"]["output_tokens"],
            "token_length_equal": len(a_toks) == len(r_toks),
            "tokens_exact_match": a_toks == r_toks,
            "differing_token_count": len(diff_positions) + abs(len(a_toks) - len(r_toks)),
            "differing_positions_sample": diff_positions[:25],
            "author_token_ids_sha256": ao["native"]["token_ids_sha256"],
            "reviewer_token_ids_sha256": ro["native"]["token_ids_sha256"],
            "author_raw_sha256": ao["raw_output"]["full_sha256"],
            "reviewer_raw_sha256": ro["raw_output"]["full_sha256"],
            "raw_bytes_author": ao["raw_output"]["full_bytes"],
            "raw_bytes_reviewer": ro["raw_output"]["full_bytes"],
            "raw_exact_match": a_raw == r_raw,
            "non_coordinate_text_exact_match": a_stripped == r_stripped,
            "box_tuple_count_author": len(a_boxes),
            "box_tuple_count_reviewer": len(r_boxes),
            "max_coordinate_unit_delta_author_vs_reviewer": max_box_delta,
            "author_finish_reason": ao["native"]["finish_reason"],
            "reviewer_finish_reason": ro["native"]["finish_reason"],
            "author_num_pages_out": ao["native"]["num_pages_out"],
            "reviewer_num_pages_out": ro["native"]["num_pages_out"],
            "author_page_marker_positions": ao["page_markers"]["marker_token_positions"],
            "reviewer_page_marker_positions": ro["page_markers"]["marker_token_positions"],
            "author_kernel_label": ao["kernel_path"]["label"],
            "reviewer_kernel_label": ro["kernel_path"]["label"],
            "author_cache_final_seq_len": ao["cache"]["final_seq_len"],
            "reviewer_cache_final_seq_len": ro["cache"]["final_seq_len"],
            "author_kv_bytes_final": ao["cache"]["kv_bytes_final"],
            "reviewer_kv_bytes_final": ro["cache"]["kv_bytes_final"],
            "author_wall_s": ao["timing"]["external_synchronized_wall_s"]["value"],
            "reviewer_wall_s": ro["timing"]["external_synchronized_wall_s"]["value"],
            "author_prefill_s": ao["timing"]["native_prefill_to_first_token_s"]["value"],
            "reviewer_prefill_s": ro["timing"]["native_prefill_to_first_token_s"]["value"],
            "author_decode_s": ao["timing"]["decode_s"]["value"],
            "reviewer_decode_s": ro["timing"]["decode_s"]["value"],
            "author_cuda_max_allocated": ao["cuda_memory"]["max_allocated"],
            "reviewer_cuda_max_allocated": ro["cuda_memory"]["max_allocated"],
            "author_cuda_max_reserved": ao["cuda_memory"]["max_reserved"],
            "reviewer_cuda_max_reserved": ro["cuda_memory"]["max_reserved"],
            "author_host_peak_private_lb": ao["host_memory"]["window_peak_private_bytes_lower_bound"],
            "reviewer_host_peak_private_lb": ro["host_memory"]["window_peak_private_bytes_lower_bound"],
            "author_host_peak_ws_lb": ao["host_memory"]["window_peak_working_set_lower_bound"],
            "reviewer_host_peak_ws_lb": ro["host_memory"]["window_peak_working_set_lower_bound"],
        })

    # Also inspect intra-reviewer warmup vs warm1 for F01 & F07
    rev_f01_wu_raw = (rev_dir / "evidence" / "F01.warmup.raw.txt").read_text(encoding="utf-8")
    rev_f01_w1_raw = (rev_dir / "evidence" / "F01.warm1.raw.txt").read_text(encoding="utf-8")
    rev_f01_wu_toks = json.loads((rev_dir / "evidence" / "F01.warmup.token_ids.json").read_text(encoding="utf-8"))
    rev_f01_w1_toks = json.loads((rev_dir / "evidence" / "F01.warm1.token_ids.json").read_text(encoding="utf-8"))
    wu_str, wu_b = strip_boxes(rev_f01_wu_raw)
    w1_str, w1_b = strip_boxes(rev_f01_w1_raw)
    intra_f01_wu_vs_w1 = {
        "token_len_warmup": len(rev_f01_wu_toks),
        "token_len_warm1": len(rev_f01_w1_toks),
        "differing_token_positions": sum(1 for a, b in zip(rev_f01_wu_toks, rev_f01_w1_toks) if a != b)
        + abs(len(rev_f01_wu_toks) - len(rev_f01_w1_toks)),
        "non_coordinate_text_identical": wu_str == w1_str,
        "max_coordinate_unit_delta": (
            max(abs(a - b) for ba, bb in zip(wu_b, w1_b) for a, b in zip(ba, bb))
            if len(wu_b) == len(w1_b) and wu_b else None
        ),
    }

    return {
        "schema": "eld-q0-reviewer-005-author-vs-reviewer/1",
        "author_run_id": "20261115T202627Z-eb5bf7da",
        "reviewer_run_id": rev_dir.name,
        "author_executing_head": auth_out["context"]["code_identity"]["head"],
        "reviewer_executing_head": rev_out["context"]["code_identity"]["head"],
        "author_status": auth_out["status"],
        "reviewer_status": rev_out["status"],
        "author_accuracy_score": auth_out["accuracy_score"],
        "reviewer_accuracy_score": rev_out["accuracy_score"],
        "author_failures": auth_out["failures"],
        "reviewer_failures": rev_out["failures"],
        "author_supervisor_elapsed_s": auth_sup["elapsed_s"],
        "reviewer_supervisor_elapsed_s": rev_sup["elapsed_s"],
        "author_free_space": auth_sup["free_space"],
        "reviewer_free_space": rev_sup["free_space"],
        "author_cold_load": auth_out["context"]["cold_load"],
        "reviewer_cold_load": rev_out["context"]["cold_load"],
        "author_repeatability": auth_out["checks"]["5_smoke_execution"]["repeatability"],
        "reviewer_repeatability": rev_out["checks"]["5_smoke_execution"]["repeatability"],
        "reviewer_intra_f01_warmup_vs_warm1": intra_f01_wu_vs_w1,
        "rendered_pages_identical": (
            auth_out["checks"]["2_artifact_dependency_lock"]["rendered_pages"]
            == rev_out["checks"]["2_artifact_dependency_lock"]["rendered_pages"]
        ),
        "per_call_comparison": per_call,
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTSIDE_CWD.mkdir(parents=True, exist_ok=True)

    run_dirs = sorted([d for d in REVIEWER_RUNS_ROOT.iterdir() if d.is_dir()])
    assert len(run_dirs) == 1, f"Expected exactly 1 reviewer run dir, found: {run_dirs}"
    rev_dir = run_dirs[0]

    sup = json.loads((rev_dir / "supervisor.json").read_text(encoding="utf-8"))
    hb = json.loads((rev_dir / "heartbeat.json").read_text(encoding="utf-8"))
    outcome = json.loads((rev_dir / "evidence" / "outcome.json").read_text(encoding="utf-8"))

    # 08. Observe worker exit & explicit lease return (preserve immediate post-exit observation if already captured)
    f08 = OUT_DIR / "08-post-run-worker-exit-and-lease-return.json"
    if f08.is_file():
        lease_ret = json.loads(f08.read_text(encoding="utf-8"))
    else:
        lease_ret = observe_worker_exit_and_gpu(rev_dir, sup.get("child_pid"), hb.get("pid"))
        f08.write_bytes((json.dumps(lease_ret, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    assert lease_ret["all_owned_workers_absent"] is True, f"Workers still alive: {lease_ret}"
    assert lease_ret["lease_status"] == "RETURNED"

    # 09. Post-run host-precheck --stage during
    f09 = OUT_DIR / "09-post-run-host-precheck-during.json"
    if not f09.is_file():
        cp_hp = subprocess.run(
            [sys.executable, "-I", "-B", str(Q0_PY), "host-precheck", "--stage", "during"],
            cwd=str(OUTSIDE_CWD), env=dict(os.environ),
            stdin=subprocess.DEVNULL, capture_output=True, timeout=60, check=True,
        )
        f09.write_bytes(cp_hp.stdout)

    # 10. Post-run verify-model (confirm all 18 original runtime objects + notice untouched)
    f10 = OUT_DIR / "10-verify-model-after.json"
    if not f10.is_file():
        protocol, _ = load_protocol()
        stage_offline_env = build_stage_env(os.environ, root=TASK_ROOT, protocol=protocol, network=False)
        cp_vm = subprocess.run(
            [str(VENV_PY), "-s", "-B", "-P", "-X", "utf8", str(Q0_PY),
             "verify-model", str(MODEL_DIR), "--notices", str(NOTICE_DIR)],
            cwd=str(OUTSIDE_CWD), env=stage_offline_env,
            stdin=subprocess.DEVNULL, capture_output=True, timeout=300, check=True,
        )
        f10.write_bytes(cp_vm.stdout)
    vm_after = json.loads(f10.read_text(encoding="utf-8"))

    # 11. Independent module-cache verification against MODEL_DIR
    mc_recorded = json.loads((rev_dir / "evidence" / "module-cache.json").read_text(encoding="utf-8"))
    mc_pkg = rev_dir / "hf-modules" / "transformers_modules" / "Unlimited_OCR_2_04809669"
    loaded_map = {r["module"]: str(mc_pkg / r["file"]) for r in mc_recorded["modules"]}
    mc_report = verify_module_cache(rev_dir / "hf-modules", MODEL_DIR, loaded_map)
    assert all(r["identical"] for r in mc_report["modules"]), f"Module cache drift: {mc_report}"
    (OUT_DIR / "11-module-cache-verification.json").write_bytes(
        (json.dumps(mc_report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )

    # 12. Full reviewer run directory inventory (every file + byte count + SHA-256)
    rev_inv = inventory_run_dir(rev_dir)
    (OUT_DIR / "12-reviewer-run-inventory.json").write_bytes(
        (json.dumps(rev_inv, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )

    # 13. Author vs reviewer comparison + verify frozen snapshot matches external author run dir
    auth_ext_inv = inventory_run_dir(AUTHOR_RUN_DIR)
    auth_snap_inv = json.loads((AUTHOR_SNAPSHOT / "inventory.json").read_text(encoding="utf-8"))
    ext_by_path = {f["path"]: f for f in auth_ext_inv["files"]}
    for sf in auth_snap_inv["files"]:
        assert ext_by_path.get(sf["path"]) == sf, f"Author snapshot mismatch on {sf['path']}: {ext_by_path.get(sf['path'])}"
    author_ext_extra_files = sorted(set(ext_by_path) - {sf["path"] for sf in auth_snap_inv["files"]})

    comp = compare_runs(rev_dir, AUTHOR_SNAPSHOT)
    comp["author_external_matches_coordinator_snapshot_72_files"] = True
    comp["author_external_total_files"] = auth_ext_inv["file_count"]
    comp["author_external_unfrozen_cache_files"] = author_ext_extra_files
    comp["reviewer_run_file_count"] = rev_inv["file_count"]
    comp["reviewer_run_total_bytes"] = rev_inv["total_bytes"]
    comp["reviewer_checks_summary"] = {k: v.get("status") for k, v in outcome["checks"].items()}
    (OUT_DIR / "13-author-vs-reviewer-comparison.json").write_bytes(
        (json.dumps(comp, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )

    summary = {
        "reviewer_run_id": rev_dir.name,
        "supervisor_verdict": sup["verdict"],
        "supervisor_elapsed_s": sup["elapsed_s"],
        "outcome_status": outcome["status"],
        "accuracy_score": outcome["accuracy_score"],
        "failures": outcome["failures"],
        "checks": comp["reviewer_checks_summary"],
        "lease_return": {
            "lease_id": lease_ret["lease_id"],
            "supervisor_child_pid": lease_ret["supervisor_child_pid"],
            "heartbeat_worker_pid": lease_ret["heartbeat_worker_pid"],
            "all_owned_workers_absent": lease_ret["all_owned_workers_absent"],
            "lease_status": lease_ret["lease_status"],
            "observed_utc": lease_ret["observed_utc"],
        },
        "model_after_runtime_objects": vm_after["runtime_objects_verified"],
        "module_cache_identical": all(r["identical"] for r in mc_report["modules"]),
        "reviewer_run_files": rev_inv["file_count"],
        "reviewer_run_bytes": rev_inv["total_bytes"],
        "repeatability": comp["reviewer_repeatability"],
        "per_call_token_matches_author": {
            c["label"]: {
                "tokens_exact_match": c["tokens_exact_match"],
                "differing_token_count": c["differing_token_count"],
                "non_coordinate_text_exact_match": c["non_coordinate_text_exact_match"],
                "reviewer_wall_s": round(c["reviewer_wall_s"], 3),
                "author_wall_s": round(c["author_wall_s"], 3),
            }
            for c in comp["per_call_comparison"]
        },
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
