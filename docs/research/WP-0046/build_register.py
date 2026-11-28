"""Deterministic stdlib generator and verifier for docs/research/WP-0046/register.json.

Reads only pinned repository files at e43af2e263f55478d1d551a5a095536b042589c2.
No private input, host path, model/torch import, device access, or external network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_PATH = Path(__file__).resolve().parent / "register.json"
REF_COMMIT = "e43af2e263f55478d1d551a5a095536b042589c2"
PROPOSAL_ID = "wp0046-direct-stock-v1"

# Pinned host-path-free symbolic root tokens used throughout WP-0046 public artifacts.
SYMBOLIC_ROOTS = {
    "@base": "Pinned CPython 3.12.10 x64 base installation directory (python.exe sha256 4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a)",
    "@venv": "Pinned Q0 virtual environment root (pyvenv.cfg include-system-site-packages=false; Lib/site-packages holds 32 verified wheels)",
    "@q0_root": "Pinned Q0 read-only storage root containing @venv, @model, and @wheelhouse",
    "@model": "Pinned unmodified Unlimited-OCR-2 revision 0480966938291445591f69f08a13b041c073a96a directory (18 verified files)",
    "@wheelhouse": "Pinned Q0 offline wheelhouse directory (32 verified wheels)",
    "@repo": "Public repository jackgumpe/eledgercare at bound commit",
    "@worktree": "Assigned isolated role worktree root for the released stage",
    "@speed_root": "Private local-only per-packet output root outside Git",
    "@arm": "Fresh exclusive-create per-arm directory under @speed_root for a single cold launch",
}

BASE_PYTHON_SHA256 = "4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a"
VENV_LAUNCHER_SHA256 = "0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14"
ACTIVE_RUNTIME_SHA256 = {
    "torch/lib/cudart64_13.dll": "58c509047f9dd1879cf82c6d5375a95c02c7bd295ae6c8362c745c936e2afc31",
    "torch/cuda/streams.py": "44762c1ec5b741b6430812e37fcc7364c6a5556834caa6ba2f15b1154fad699d",
}
HOST_PATH_RE = re.compile(
    r"(?i)(?:[A-Z]:[/\\]|[/\\]Users[/\\]|AppData[/\\]Local|Asp\.net Projects|eLedgerCare-(?:Speed|Q0)|w04[0-9]-)"
)


def load_repo_json(rel_path: str) -> dict:
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


def normalize_dist(name: str) -> str:
    return re.sub(r"[-_.]+", "_", name).lower()


def wheel_map(wheel_doc: dict) -> dict[str, dict]:
    mapping: dict[str, dict] = {}
    for entry in wheel_doc["wheels"]:
        whl = entry["wheel"]
        dist_prefix = whl.split("-", 1)[0]
        mapping[normalize_dist(dist_prefix)] = {
            "wheel": whl,
            "sha256": entry["sha256"],
            "size": entry["size"],
            "kind": entry["kind"],
            "metadata_sha256": entry["metadata"]["metadata_sha256"],
        }
    return mapping


def build_manifest() -> dict:
    plan43 = load_repo_json("docs/coordination/WP-0043/plan-canonical.json")
    inputs43 = load_repo_json("docs/coordination/WP-0043/native-inputs.json")
    native43 = load_repo_json("docs/coordination/WP-0043/native-evidence.json")
    device43 = load_repo_json("docs/coordination/WP-0043/device-release.json")
    source41 = load_repo_json("docs/research/WP-0041/source.json")
    wheels05 = load_repo_json(
        "docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/checks/02-verify-wheelhouse.json"
    )
    wmap = wheel_map(wheels05)

    # Historical reference digests for the 5x3 retained score vectors.
    retained_by_pos = {r["position"]: r for r in native43["retained_rows"]}

    entries: list[dict] = []

    def add(
        *,
        key: str,
        paper_clauses: list[str],
        earliest_stage: int,
        direct_stock_stage: int,
        subject: str,
        cut: str,
        typ: str,
        expected: object,
        comparator: str,
        evidence_source: str,
        evidence_locator: str,
        historical_reference: str,
        status: str,
        missing_precondition: list[str] | None,
        alternatives_or_notes: str,
    ) -> None:
        entries.append(
            {
                "index": len(entries),
                "key": key,
                "paper_clauses": paper_clauses,
                "earliest_stage": earliest_stage,
                "direct_stock_stage": direct_stock_stage,
                "subject": subject,
                "cut": cut,
                "type": typ,
                "expected": expected,
                "comparator": comparator,
                "evidence_source": evidence_source,
                "evidence_locator": evidence_locator,
                "historical_reference": historical_reference,
                "status": status,
                "missing_precondition": missing_precondition,
                "alternatives_or_notes": alternatives_or_notes,
            }
        )

    # --- 0..3: Stage-0 plan freeze obligations ---
    add(
        key="route.design",
        paper_clauses=["T2a", "T3", "Eq. (4)"],
        earliest_stage=0,
        direct_stock_stage=0,
        subject="WP-0046 direct-stock route specification (Stage 1 CPU and Stage 2 stock)",
        cut="stage0.plan_freeze",
        typ="structured_route_binding",
        expected={
            "route": "direct-stock",
            "creation_edge": "E_direct = J(e, S, i_base)",
            "application_image": "@base/python.exe",
            "application_image_sha256": BASE_PYTHON_SHA256,
            "interpreter_flags": ["-s", "-P", "-B", "-u"],
            "venv_binding_mechanism": "launch_env.__PYVENV_LAUNCHER__=@venv/Scripts/python.exe with pre-launch read-guarded pyvenv.cfg and .pth verification",
            "intentional_differences_from_wp0043_venv": [
                "No venv redirector hop (direct CreateProcessW to @base/python.exe)",
                "Explicit -s and -P flags added to (-B, -u); script import root inserted only after digest check",
                "Supervisor uses direct _winapi.CreateProcess with DEBUG_ONLY_THIS_PROCESS|CREATE_SUSPENDED|CREATE_NO_WINDOW",
                "sys.orig_argv[0] == @base/python.exe matches CreateProcessW argv[0] while sys.executable == @venv/Scripts/python.exe via __PYVENV_LAUNCHER__",
            ],
        },
        comparator="strict_typed_exact_plus_reviewed_mapping",
        evidence_source="eld-owner-probe Stage-0 proposal + eld-rd-reviewer independent audit",
        evidence_locator="docs/research/WP-0046/proposal.md#route-selection",
        historical_reference="docs/coordination/WP-0043/plan-canonical.json; docs/agent-reports/eld-owner-probe/WP-0045/002_2026-11-27_research_eld-owner-probe.md",
        status="bound_stage0",
        missing_precondition=None,
        alternatives_or_notes="Alternative 1: direct-stock with -s -P -B -u -S and manual validated site/venv bootstrap (avoids pre-script .pth execution at the cost of diverging from T2a a_*). Alternative 2: tau=venv remains blocked under ordinary-user privileges by Theorem 2 unless elevated ETW/kernel creator tracing is separately authorized.",
    )
    add(
        key="writer.scope",
        paper_clauses=["T3", "T3a", "Eq. (5)"],
        earliest_stage=0,
        direct_stock_stage=0,
        subject="Cooperative ordinary-user trust model, allowed writers, and member inventory schema",
        cut="stage0.plan_freeze",
        typ="trust_and_writer_set",
        expected={
            "privilege_model": {"integrity_rid": 8192, "elevated": 0, "effective_admin": False},
            "trusted_roles": ["outer_recorder_scorer", "direct_supervisor", "stock_or_rehearsal_worker"],
            "allowed_writers_per_member_role": {
                "worker_produced_members": ["bound_worker_instance_only"],
                "supervisor_receipts": ["bound_supervisor_instance_only"],
            },
            "handle_inheritance": False,
            "creation_disposition": "CREATE_NEW",
            "writer_share_mode": "FILE_SHARE_READ",
            "scorer_read_share_mode": "FILE_SHARE_READ",
            "require_single_link": True,
            "excluded_threats": [
                "adversarial_same_user_process",
                "compromised_os_or_signing_key",
                "unobserved_external_ntfs_aliases_outside_cooperative_scope",
            ],
        },
        comparator="set_and_policy_exact",
        evidence_source="eld-owner-probe Stage-0 proposal + Stage-1/2 Win32 handle/token receipts",
        evidence_locator="docs/research/WP-0046/proposal.md#trust-writer-and-continuity",
        historical_reference="docs/coordination/WP-0045/disposition.json#/direct_launch",
        status="bound_stage0",
        missing_precondition=None,
        alternatives_or_notes="Tightens WP-0045 win.py:fresh_read by changing scorer share mode from FILE_SHARE_READ|FILE_SHARE_WRITE to FILE_SHARE_READ so any leaked writable handle fails open with Win32 ERROR_SHARING_VIOLATION (32).",
    )
    add(
        key="module.coverage",
        paper_clauses=["T2", "T2a", "T8"],
        earliest_stage=0,
        direct_stock_stage=0,
        subject="Declared Python module and Windows DLL import coverage across Stage 1 CPU and Stage 2 stock cuts",
        cut="stage0.plan_freeze",
        typ="typed_coverage_schema",
        expected={
            "stage1_cpu_python_roots_allowed": ["@venv/Lib/site-packages", "@base/Lib", "@base/DLLs", "@source", "built-in", "frozen"],
            "stage1_cpu_python_roots_forbidden": ["@base/Lib/site-packages", "user_site"],
            "stage1_cpu_explicit_packages": [
                "numpy", "PIL", "pypdfium2", "psutil", "safetensors",
                "tokenizers", "huggingface_hub", "transformers", "torch", "torchvision",
            ],
            "stage1_cpu_required_absent_specs": ["triton"],
            "stage1_cpu_pinned_runtime_files_sha256": {
                **source41["versions"]["runtime_source_sha256"],
                **ACTIVE_RUNTIME_SHA256,
            },
            "stage1_cpu_dll_coverage": [
                "@base/python312.dll",
                "@venv/Lib/site-packages/torch/lib/cudart64_13.dll",
                "@venv/Lib/site-packages/torch/lib/torch_cpu.dll",
                "@venv/Lib/site-packages/torch/lib/c10.dll",
                "all LOAD_DLL_DEBUG_EVENT modules under @venv or @base",
            ],
            "stage2_additional_dynamic_modules": sorted(
                source41["historical_q0_imported_module_receipt_and_disk"].keys()
            ),
            "declared_unobservable_backend_properties": [
                "proprietary_cuda_cublas_cudnn_internal_kernel_dispatch_and_sass",
                "wddm_per_process_vram_attribution",
            ],
        },
        comparator="typed_schema_and_root_containment",
        evidence_source="Stage-0 coverage manifest + Stage-1 sys.modules and LOAD_DLL_DEBUG_EVENT receipts",
        evidence_locator="docs/research/WP-0046/proposal.md#site-pth-and-dll-origin-mapping",
        historical_reference="docs/research/WP-0041/source.json; docs/research/WP-0043/native.py",
        status="bound_stage0",
        missing_precondition=None,
        alternatives_or_notes="GPU-only DLLs not loaded during CPU import stay explicitly deferred to Stage 2; internal vendor CUDA/cuBLAS/cuDNN kernel identities remain declared unobservable (yield U if any claim requires them).",
    )
    add(
        key="limits",
        paper_clauses=["T8", "T8a", "Eq. (12)"],
        earliest_stage=0,
        direct_stock_stage=0,
        subject="Per-stage resource ceilings, units, timeouts, and release ownership",
        cut="stage0.pre_admission",
        typ="resource_plan",
        expected={
            "release_owner": "eld-coordinator (01a20a53-eec1-72c1-864c-9f8be8f4aff5)",
            "stage1_cpu_proposed_ceilings": {
                "cold_arms": 2,
                "retries": 0,
                "wall_s": 600,
                "preflight_hash_s": 300,
                "per_arm_s": 120,
                "host_job_commit_bytes": 4 * (1 << 30),
                "output_bytes": 64 * (1 << 20),
                "log_bytes": 8 * (1 << 20),
                "files": 128,
                "disk_free_initial_bytes": 2 * (1 << 30),
                "disk_free_during_bytes": 1 * (1 << 30),
                "gpu_leases": 0,
                "cuda_calls": 0,
            },
            "stage2_stock_historical_reference_only": plan43["limits"],
        },
        comparator="formal_ceiling_and_release_binding",
        evidence_source="Stage-0 proposal ceilings + future coordinator release record",
        evidence_locator="docs/research/WP-0046/proposal.md#resource-ceilings-and-scheduling",
        historical_reference="docs/coordination/WP-0043/plan-canonical.json#/limits",
        status="bound_stage0",
        missing_precondition=[
            "Separate coordinator release required before Stage-1 execution",
            "Fresh host headroom and Stage-2 GPU lease/ceilings must be bound separately before Stage-2 admission",
        ],
        alternatives_or_notes="Historical WP-0043 limits are preserved strictly as reference data (not auto-released). Notice WP-0043 plan-canonical.json is 6573 bytes in Git (sha256 60318641...) vs 6574 bytes in bundle/sources/plan43.json (trailing LF, sha256 d6276504...).",
    )

    # --- 4: Stage-1 CPU route rehearsal ---
    add(
        key="cpu.route_rehearsal",
        paper_clauses=["T2a", "T3", "T3a", "Eq. (4)", "Eq. (5)"],
        earliest_stage=1,
        direct_stock_stage=1,
        subject="Two cold Stage-1 direct-stock CPU rehearsal arms (arm-0, arm-1)",
        cut="stage1.process_creation_and_direct_read",
        typ="joined_event_and_custody",
        expected={
            "arms": ["arm-0", "arm-1"],
            "distinct_process_instances": True,
            "distinct_original_objects": True,
            "creation_predicate": "E_direct = J(e, S, i_base) with CompareObjectHandles(hProcess_returned, hProcess_event) == True",
            "image_sha256": BASE_PYTHON_SHA256,
            "job_flags_required": ["JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE (0x2000)", "JOB_OBJECT_LIMIT_JOB_MEMORY (0x0200)"],
            "member_custody": "B_m (Eq. 5) with FILE_SHARE_READ-only continuous read-view chain worker -> supervisor -> scorer",
            "zero_cuda_or_model_load": True,
        },
        comparator="event_join_plus_continuous_handle_custody",
        evidence_source="Future Stage-1 outer recorder, direct supervisor, CPU worker, and independent offline scorer",
        evidence_locator="prospective:@arm/child-call.json; prospective:@arm/scorer.json",
        historical_reference="docs/coordination/WP-0045/windows-check.json",
        status="prospective_stage1_bound",
        missing_precondition=[
            "Stage-1 probe source must be implemented, frozen, and independently reviewed",
            "Separate coordinator Stage-1 release required",
        ],
        alternatives_or_notes="WP-0045 direct CPU passed 4/4 genuine launches on inert -I -S -B workers; by Theorem 1 Corollary, those runs cannot qualify the new -s -P -B -u stock-import rehearsal processes.",
    )

    # --- 5: static.model_revision ---
    add(
        key="static.model_revision",
        paper_clauses=["T1", "T2"],
        earliest_stage=1,
        direct_stock_stage=1,
        subject="Pinned unmodified Q0 model revision identifier",
        cut="stage1.cut1s_static_preflight",
        typ="str",
        expected={
            "value": inputs43["pinned_model_revision"],
            "reference_locator": "docs/coordination/WP-0043/native-inputs.json#/pinned_model_revision",
        },
        comparator="strict_typed_exact",
        evidence_source="Stage-1 read-only supervisor preflight manifest check",
        evidence_locator="prospective:@run_root/preflight.json#/pinned_model_revision",
        historical_reference="docs/coordination/WP-0043/native-inputs.json#/pinned_model_revision",
        status="prospective_stage1_bound",
        missing_precondition=["Stage-1 preflight execution against local @model directory"],
        alternatives_or_notes="Matches source41.json#/model (0480966938291445591f69f08a13b041c073a96a) and plan-canonical.json#/model_revision.",
    )

    # --- 6..23: 18 static.model.* digests ---
    for fname, rec in inputs43["model_objects_read_via_sha256"].items():
        add(
            key=f"static.model.{fname}",
            paper_clauses=["T1", "T2"],
            earliest_stage=1,
            direct_stock_stage=1,
            subject=f"Static disk artifact @model/{fname}",
            cut="stage1.cut1s_static_preflight",
            typ="sha256_and_byte_length",
            expected={
                "sha256": rec["sha256"],
                "bytes": rec["bytes"],
                "reference_locator": f"docs/coordination/WP-0043/native-inputs.json#/model_objects_read_via_sha256/{fname}",
            },
            comparator="sha256_and_exact_byte_length",
            evidence_source="Stage-1 supervisor read-only streaming 8 MiB SHA-256 preflight (no model import/load)",
            evidence_locator=f"prospective:@run_root/preflight.json#/model_files/{fname}",
            historical_reference=f"docs/coordination/WP-0043/native-inputs.json#/model_objects_read_via_sha256/{fname}",
            status="prospective_stage1_bound",
            missing_precondition=["Stage-1 read-only preflight execution on local @model directory"],
            alternatives_or_notes="By Theorem 1 (H1/H2), static byte equality on disk establishes immutable file bytes only; live loaded module/weight identity is a separate Stage-2 obligation (exec.loaded).",
        )

    # --- 24..55: 32 static.dist.* versions + exact wheel SHA-256 pins ---
    for dist_name, version in source41["versions"]["verified_pinned_distributions"].items():
        wrec = wmap[normalize_dist(dist_name)]
        add(
            key=f"static.dist.{dist_name}",
            paper_clauses=["T1", "T2", "T2a"],
            earliest_stage=1,
            direct_stock_stage=1,
            subject=f"Pinned distribution {dist_name} in @venv and @wheelhouse",
            cut="stage1.cut1s_wheel_and_cut1b_metadata",
            typ="distribution_version_and_wheel_sha256",
            expected={
                "distribution": dist_name,
                "version": version,
                "wheel": wrec["wheel"],
                "wheel_sha256": wrec["sha256"],
                "wheel_size_bytes": wrec["size"],
                "wheel_metadata_sha256": wrec["metadata_sha256"],
                "version_locator": f"docs/research/WP-0041/source.json#/versions/verified_pinned_distributions/{dist_name}",
                "wheel_locator": "docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/checks/02-verify-wheelhouse.json#/wheels",
            },
            comparator="exact_version_and_wheel_sha256",
            evidence_source="Stage-1 Cut 1S wheelhouse SHA-256 check + Cut 1B child importlib.metadata.version() inside direct-stock @venv",
            evidence_locator=f"prospective:@arm/cut1b-imports.json#/distributions/{dist_name}",
            historical_reference="docs/research/WP-0041/source.json#/versions/verified_pinned_distributions; docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/checks/02-verify-wheelhouse.json",
            status="prospective_stage1_bound",
            missing_precondition=["Stage-1 preflight and Cut 1B child metadata check"],
            alternatives_or_notes="Resolves bundle register.json gap that omitted explicit wheel filenames and SHA-256 digests; torchvision retains its documented local-sha256-TOFU provenance tag from WP-0005.",
        )

    # --- 56..57: 2 static.input.* development PDFs ---
    for fam, entry in inputs43["development_inputs"].items():
        add(
            key=f"static.input.{fam}",
            paper_clauses=["T1", "T2"],
            earliest_stage=1,
            direct_stock_stage=1,
            subject=f"Pinned development PDF fixture {fam} ({entry['path']})",
            cut="stage1.cut1s_static_preflight",
            typ="pdf_sha256_and_git_blob",
            expected={
                "path": entry["path"],
                "git_blob": entry["git_blob"],
                "sha256": entry["verified_pdf_sha256"],
                "historical_rgb_pins_reference": entry["historical_rgb_pins"],
                "reference_locator": f"docs/coordination/WP-0043/native-inputs.json#/development_inputs/{fam}",
            },
            comparator="sha256_and_git_blob_exact",
            evidence_source="Stage-1 supervisor read-only Git blob / PDF digest verification",
            evidence_locator=f"prospective:@run_root/preflight.json#/development_inputs/{fam}",
            historical_reference=f"docs/coordination/WP-0043/native-inputs.json#/development_inputs/{fam}",
            status="prospective_stage1_bound",
            missing_precondition=["Stage-1 read-only preflight execution"],
            alternatives_or_notes="Live RGB rendering with pypdfium2 + pillow is verified separately at Stage 2 (exec.inputs) so Stage 1 stays strictly focused on startup/import/custody.",
        )

    # --- 58..69: Stage-2 execution creation, config, env, loaded, backend, device, inputs ---
    add(
        key="exec.creator",
        paper_clauses=["T3", "Eq. (4)"],
        earliest_stage=2,
        direct_stock_stage=2,
        subject="Stage-2 cold stock arms (untouched and observed) on direct-stock route",
        cut="stage2.actual_stock_creation",
        typ="joined_creation_event",
        expected={
            "route": "direct-stock",
            "predicate": "E_direct = J(e, S, i_base) for both untouched and observed stock workers",
            "required_joins": [
                "supervisor_self_before == supervisor_self_after == outer_returned_instance",
                "CompareObjectHandles(returned_hProcess, event_hProcess) == True",
                "returned_instance == event_instance == worker_self_instance",
                "returned_tid == event_tid",
                "event_image_sha256 == 4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a",
                "both_in_bound_job_with_commit_limit",
            ],
            "distinct_cold_workers": True,
        },
        comparator="event_join_and_image_sha256",
        evidence_source="Stage-2 direct supervisor CreateProcessW + DEBUG_ONLY_THIS_PROCESS event trace",
        evidence_locator="prospective:@arm/child-call.json",
        historical_reference="docs/coordination/WP-0045/windows-check.json; docs/coordination/WP-0043/native-evidence.json",
        status="prospective_stage2_requires_decision",
        missing_precondition=[
            "Passing Stage-1 CPU qualification (V_preflight = P)",
            "Decision on keeping DEBUG_ONLY_THIS_PROCESS attached vs clean DebugActiveProcessStop after startup/import cut during CUDA execution",
            "Separate Stage-2 coordinator release and sole GPU lease",
        ],
        alternatives_or_notes="Replaces worker43.py subprocess.Popen(CREATE_SUSPENDED) + Toolhelp snapshot with direct _winapi.CreateProcess + DEBUG_ONLY_THIS_PROCESS; resolves WP-0043 historical M on argv[0].",
    )
    add(
        key="exec.configuration",
        paper_clauses=["T2", "T2a", "T4"],
        earliest_stage=2,
        direct_stock_stage=2,
        subject="Stage-2 stock worker startup configuration (untouched and observed arms)",
        cut="stage2.before_model_imports",
        typ="typed_startup_vector",
        expected={
            "python_version": source41["python"],
            "orig_argv_prefix": ["@base/python.exe", "-s", "-P", "-B", "-u", "@worktree/docs/research/WP-0046/stock_worker.py", "_worker"],
            "sys_executable": "@venv/Scripts/python.exe",
            "sys_base_executable": "@base/python.exe",
            "sys_prefix": "@venv",
            "sys_exec_prefix": "@venv",
            "sys_base_prefix": "@base",
            "sys_flags": {
                "isolated": 0,
                "ignore_environment": 0,
                "hash_randomization": 0,
                "no_site": 0,
                "no_user_site": 1,
                "dont_write_bytecode": 1,
                "safe_path": True,
                "utf8_mode": 1,
            },
            "site_loaded": True,
            "base_site_packages_in_sys_path": False,
            "venv_site_packages_in_sys_path": True,
            "sitecustomize_present": False,
            "usercustomize_present": False,
            "pyvenv_cfg_include_system_site_packages": "false",
        },
        comparator="strict_typed_ordered_equality",
        evidence_source="Stage-2 stock worker Cut 1A-equivalent startup receipt before model/torch import",
        evidence_locator="prospective:@arm/runtime-startup.json",
        historical_reference="docs/coordination/WP-0043/plan-canonical.json; docs/reviews/WP-0045/blind/prior-0.json",
        status="prospective_stage2_bound",
        missing_precondition=[
            "Stage-1 verification of exact pyvenv.cfg digest and .pth list on host @venv",
            "Freeze exact Stage-2 worker entry filename and digest before Stage-2 admission",
        ],
        alternatives_or_notes="Resolves WP-0043 argv[0] mismatch: orig_argv[0] is explicitly bound to @base/python.exe while sys.executable is bound to @venv/Scripts/python.exe via __PYVENV_LAUNCHER__.",
    )

    # 60..65: 6 exec.env.* keys
    env_specs = [
        (
            "CUDA_VISIBLE_DEVICES",
            2,
            2,
            {"state": "present", "value": plan43["uuid"]},
            "prospective_stage2_requires_decision",
            ["Confirm live target GPU UUID at Stage-2 lease issue"],
            "Stage 1 CPU intentionally sets CUDA_VISIBLE_DEVICES to empty string '' (state='present', value='') to hide GPU devices during CPU torch import; Stage 2 binds the coordinator-leased GPU UUID.",
        ),
        (
            "CUDA_DEVICE_ORDER",
            2,
            2,
            {"state": "present", "value": "PCI_BUS_ID"},
            "prospective_stage2_bound",
            ["Stage-2 coordinator release"],
            "Absent or PCI_BUS_ID at Stage 1 (proposed PCI_BUS_ID in both stages for parity); required PCI_BUS_ID before torch import in Stage 2.",
        ),
        (
            "HF_HUB_OFFLINE",
            2,
            1,
            {"state": "present", "value": "1"},
            "prospective_stage1_bound",
            ["Stage-1 Cut 1A receipt and Stage-2 worker startup receipt"],
            "Reconciled to earliest direct-stock check at Stage 1 (Q_offline in T2a) and re-verified at Stage 2.",
        ),
        (
            "TRANSFORMERS_OFFLINE",
            2,
            1,
            {"state": "present", "value": "1"},
            "prospective_stage1_bound",
            ["Stage-1 Cut 1A receipt and Stage-2 worker startup receipt"],
            "Reconciled to earliest direct-stock check at Stage 1 (Q_offline in T2a) and re-verified at Stage 2.",
        ),
        (
            "PYTHONHASHSEED",
            2,
            1,
            {"state": "present", "value": "0"},
            "prospective_stage1_bound",
            ["Stage-1 Cut 1A receipt and Stage-2 worker startup receipt"],
            "Reconciled to Stage 1 (Q_hash in T2a) and re-verified at Stage 2; string alone is insufficient without sys.flags.ignore_environment == 0 and sys.flags.hash_randomization == 0.",
        ),
        (
            "PYTHONNOUSERSITE",
            2,
            1,
            {"state": "present", "value": "1"},
            "prospective_stage1_bound",
            ["Stage-1 Cut 1A receipt and Stage-2 worker startup receipt"],
            "Reconciled to Stage 1 (paired with -s -> sys.flags.no_user_site == 1) and re-verified at Stage 2.",
        ),
    ]
    for env_key, orig_s, ds_s, exp_val, st, precond, note in env_specs:
        add(
            key=f"exec.env.{env_key}",
            paper_clauses=["T2", "T2a", "T4"],
            earliest_stage=orig_s,
            direct_stock_stage=ds_s,
            subject="Direct-stock worker process environment (e_launch and e_child)",
            cut="worker_before_imports",
            typ="tagged_env_presence_string",
            expected={
                "e_launch": exp_val,
                "e_child": exp_val,
                "allowlist_note": "Full scrubbed env schema (including PYTHONDONTWRITEBYTECODE=1, PYTHONUTF8=1, PYTHONIOENCODING=utf-8, PYTHONUNBUFFERED=1, HF_HOME, HF_MODULES_CACHE, HF_HUB_DISABLE_TELEMETRY=1, HF_HUB_DISABLE_XET=1, PIP_NO_INDEX=1, TORCH_HOME, XDG_CACHE_HOME, TEMP/TMP/HOME/USERPROFILE, and ABSENT OMP/MKL/OPENBLAS_NUM_THREADS and CUBLAS_WORKSPACE_CONFIG) is bound in proposal.md.",
            },
            comparator="tagged_presence_and_exact_string",
            evidence_source="Supervisor CreateProcessW lpEnvironment trace + child os.environ snapshot before imports",
            evidence_locator=f"prospective:@arm/runtime-startup.json#/environment/{env_key}",
            historical_reference="docs/research/WP-0043/native.py#L189-L202",
            status=st,
            missing_precondition=precond,
            alternatives_or_notes=note,
        )

    add(
        key="exec.loaded",
        paper_clauses=["T1", "T2", "T2a"],
        earliest_stage=2,
        direct_stock_stage=2,
        subject="Live loaded stock model, tokenizer, dynamic HF modules, and in-coverage runtime modules/DLLs",
        cut="stage2.immediately_after_model_load",
        typ="live_object_and_origin_bindings",
        expected={
            "dynamic_hf_modules_root": "@arm/modules",
            "dynamic_hf_modules_sha256": {
                k: v["sha256"]
                for k, v in source41["historical_q0_imported_module_receipt_and_disk"].items()
            },
            "runtime_files_live_origin_sha256": {
                **source41["versions"]["runtime_source_sha256"],
                **ACTIVE_RUNTIME_SHA256,
            },
            "receivers_bound": ["generator (UnlimitedOCRForCausalLM)", "decoder (DeepseekV2Model)", "layer11 (DeepseekV2DecoderLayer)"],
            "model_eval_and_single_rank": {"any_module_training": False, "all_ep_size_eq_1": True},
            "tokenizer_class": source41["configuration"]["tokenizer"]["class"],
            "triton_spec": None,
        },
        comparator="live_instance_origin_root_and_sha256",
        evidence_source="Stage-2 worker post-load runtime.json + sys.modules + LOAD_DLL_DEBUG_EVENT receipts",
        evidence_locator="prospective:@arm/runtime.json#/modules",
        historical_reference="docs/coordination/WP-0043/native-inputs.json; docs/research/WP-0041/source.json#/historical_q0_imported_module_receipt_and_disk; docs/research/WP-0043/native.py#L347-L366",
        status="prospective_stage2_bound",
        missing_precondition=["Stage-2 execution and live loaded-object/DLL verification"],
        alternatives_or_notes="Unlike worker43.py L337 (which hashed site-packages paths on disk before import), direct-stock joins actual sys.modules[name].__file__ and OS DLL load handles to the verified digests.",
    )
    add(
        key="exec.backend",
        paper_clauses=["T2", "T8"],
        earliest_stage=2,
        direct_stock_stage=2,
        subject="Stage-2 stock PyTorch/CUDA numerical and execution backend state",
        cut="stage2.after_load_and_at_use",
        typ="typed_backend_vector",
        expected={
            "bound_now": {
                "torch_version": "2.13.0+cu130",
                "torch_cuda_version": "13.0",
                "load_dtype": "torch.bfloat16",
                "eval_mode_module": True,
                "training_modules": [],
                "autocast_enabled": False,
                "triton_present": False,
                "stream_contract": "single_thread_default_stream_0",
            },
            "requires_stage2_binding_before_exposure": {
                "driver_version": {"historical_reference": device43["driver_version"], "status": "reobserve_and_freeze_pre_stage2"},
                "deterministic_algorithms": {"historical_public_value": "unobserved_in_public_bundle", "expected_pytorch_default": False, "status": "bind_before_stage2_review"},
                "matmul_allow_tf32": {"historical_public_value": "unobserved_in_public_bundle", "expected_pytorch_default": False, "status": "bind_before_stage2_review"},
                "cudnn_allow_tf32": {"historical_public_value": "unobserved_in_public_bundle", "expected_pytorch_default": True, "status": "bind_before_stage2_review"},
            },
            "unobservable_declared": ["low_level_cublas_cudnn_kernel_selection"],
        },
        comparator="typed_field_equality_plus_arm_parity",
        evidence_source="Stage-2 worker runtime.json (both arms) + nvidia-smi driver query",
        evidence_locator="prospective:@arm/runtime.json",
        historical_reference="docs/coordination/WP-0043/device-release.json#/driver_version; docs/research/WP-0043/native.py#L362-L366",
        status="prospective_stage2_requires_decision",
        missing_precondition=[
            "Coordinator/reviewer must inspect private WP-0043 runtime.json or explicitly freeze expected deterministic/tf32/cudnn_tf32 values before Stage-2 admission",
            "Re-observe and freeze live NVIDIA driver_version at Stage-2 lease issue",
        ],
        alternatives_or_notes="Historical WP-0043 native_validation.py L148 checked presence only for deterministic/tf32/cudnn_tf32/autocast and did not publish their concrete values in native43.json.",
    )
    add(
        key="exec.device",
        paper_clauses=["T2", "T8"],
        earliest_stage=2,
        direct_stock_stage=2,
        subject="Stage-2 CUDA worker visible physical device",
        cut="stage2.device_selection",
        typ="uuid_and_device_count",
        expected={
            "historical_reference_uuid": plan43["uuid"],
            "visible_device_count": 1,
            "allocator_limit_bytes": plan43["limits"]["allocator_bytes"],
            "env_to_cuda_join": "os.environ['CUDA_VISIBLE_DEVICES'] == 'GPU-' + str(torch.cuda.get_device_properties(0).uuid).removeprefix('GPU-')",
        },
        comparator="exact_uuid_count_and_env_join",
        evidence_source="Stage-2 worker torch.cuda.device_count/get_device_properties + supervisor nvidia-smi ownership census",
        evidence_locator="prospective:@arm/runtime.json#/uuid",
        historical_reference="docs/coordination/WP-0043/plan-canonical.json#/uuid; docs/coordination/WP-0043/device-release.json#/observed_ownership",
        status="prospective_stage2_requires_decision",
        missing_precondition=[
            "Fresh sole GPU lease, live UUID confirmation, and allowed_resident_pids census from eld-coordinator",
        ],
        alternatives_or_notes="Stage 1 CPU explicitly prohibits any CUDA device query or GPU lease.",
    )
    add(
        key="exec.inputs",
        paper_clauses=["T2", "T3"],
        earliest_stage=2,
        direct_stock_stage=2,
        subject="Stage-2 rendered RGB page sequences and native tokenizer/prompt IDs for F01 and F07",
        cut="stage2.render_and_native_entry",
        typ="ordered_image_and_prompt_binding",
        expected={
            "prompt": plan43["input_options"]["prompt"],
            "prompt_expansion": plan43["input_options"]["prompt_expansion"],
            "page_token_id": plan43["input_options"]["page_token_id"],
            "render_scale": "300.0/72.0",
            "fixtures": {
                f["family_id"]: {
                    "fixture_id": f["fixture_id"],
                    "pdf_sha256": f["sha256"],
                    "page_count": f["page_count"],
                    "raster": f["raster"],
                }
                for f in plan43["fixtures"]
            },
            "f07_expected_prompt_len": 827,
        },
        comparator="ordered_shape_rgb_sha256_and_prompt_ids_exact",
        evidence_source="Stage-2 worker render receipt + per-call prompt_token_ids receipt",
        evidence_locator="prospective:@arm/F07.warm1.json#/document/prompt_token_ids",
        historical_reference="docs/coordination/WP-0043/plan-canonical.json#/fixtures",
        status="prospective_stage2_bound",
        missing_precondition=["Stage-2 execution with live pypdfium2/PIL render confirmation"],
        alternatives_or_notes="Preserves Q0/WP-0043 exact RGB page digests (F01: 1 page; F07: 3 pages, all 2550x3301 RGB).",
    )

    # --- 70..85: 16 exec.options.* fixed_kwargs ---
    for opt_name, opt_val in plan43["input_options"]["fixed_kwargs"].items():
        add(
            key=f"exec.options.{opt_name}",
            paper_clauses=["T2", "T8"],
            earliest_stage=2,
            direct_stock_stage=2,
            subject=f"Stage-2 native reader fixed keyword argument {opt_name}",
            cut="stage2.native_infer_argument_binding",
            typ=f"typed_option ({type(opt_val).__name__})",
            expected={
                "state": "present",
                "value": opt_val,
                "json_type": "null" if opt_val is None else type(opt_val).__name__,
                "call_entry_reconciled": "model.infer(tokenizer, prompt=PROMPT, image_file=list(pages), return_dict=True, **kwargs)",
            },
            comparator="strict_typed_exact",
            evidence_source="Stage-2 per-call kwargs receipt bound to actual model.infer() call",
            evidence_locator=f"prospective:@arm/F07.warm1.json#/kwargs/{opt_name}",
            historical_reference=f"docs/coordination/WP-0043/plan-canonical.json#/input_options/fixed_kwargs/{opt_name}; docs/research/WP-0043/native.py#L373-L377",
            status="prospective_stage2_bound",
            missing_precondition=["Stage-2 execution and independent agreement on model.infer vs infer_multi cut reconciliation"],
            alternatives_or_notes=(
                "RECONCILES STATIC CONFLICT: plan43.json and bundle/register.json name cut 'native infer_multi argument binding', whereas actual worker43.py L377 invokes model.infer(..., image_file=list(pages), return_dict=True, **kwargs) directly because infer_multi discards token_ids and finish_reason (per WP-0042/source-cuts.md L20)."
                + (" Note: JSON null here is a concrete typed value, distinct from ABSENT or unobserved." if opt_val is None else "")
            ),
        )

    # --- 86..88: exec.fixture_options, exec.schedule, exec.original ---
    add(
        key="exec.fixture_options",
        paper_clauses=["T2"],
        earliest_stage=2,
        direct_stock_stage=2,
        subject="Stage-2 per-family dynamic kwargs and native stop/context-budget rule",
        cut="stage2.native_infer_call",
        typ="per_fixture_typed_options",
        expected={
            "F01": {"max_new_tokens": 8000, "ngram_window": 128},
            "F07": {"max_new_tokens": 24000, "ngram_window": 1024},
            "context_cap_rule": "prompt_len + max_new_tokens <= 131072 else CONTEXT_BUDGET_EXCEEDED (never truncate)",
            "terminal_rule": "finish_reason == 'stop' on native EOS; 'length' is failure",
        },
        comparator="strict_typed_exact_per_call",
        evidence_source="Stage-2 per-call kwargs and document terminal receipts",
        evidence_locator="prospective:@arm/<call_label>.json#/kwargs",
        historical_reference="docs/coordination/WP-0043/plan-canonical.json#/fixtures; docs/research/WP-0043/native.py#L373-L384",
        status="prospective_stage2_bound",
        missing_precondition=["Stage-2 execution"],
        alternatives_or_notes="Exact match to worker43.py L373-L374 and Q0 protocol rules.",
    )
    add(
        key="exec.schedule",
        paper_clauses=["T2", "T6", "T8a"],
        earliest_stage=2,
        direct_stock_stage=2,
        subject="Stage-2 two cold stock arms (untouched, observed) and 4-call prehistory per arm",
        cut="stage2.cold_load_through_eos",
        typ="ordered_call_schedule",
        expected={
            "arms": ["untouched", "observed"],
            "calls_per_arm": plan43["prehistory"],
            "total_cold_loads": 2,
            "total_calls": 8,
            "instrument_scope": "observed arm, 4th call (F07.warm1) only; untouched arm completely uninstrumented",
            "public_parity": "untouched == observed == historical Q0/WP-0043 archive across all 4 calls (F07.warm1: 2558 non-EOS IDs, 7617 UTF-8 bytes, markers [0,1145,1896], finish='stop')",
        },
        comparator="ordered_exact_per_arm_plus_whole_document_parity",
        evidence_source="Stage-2 timing journal (phase), per-call JSONs, observed append/EOS/cleanup records",
        evidence_locator="prospective:@arm/phase; prospective:@arm/F07.warm1.json",
        historical_reference="docs/coordination/WP-0043/plan-canonical.json#/prehistory; docs/coordination/WP-0043/native-evidence.json#/public_content",
        status="prospective_stage2_bound",
        missing_precondition=["Stage-2 execution under sole GPU lease"],
        alternatives_or_notes="Historical F07.warm1 content matched 1/1 in WP-0043, but formal pair qualification remained 0/1 due to runtime argv[0] M.",
    )
    add(
        key="exec.original",
        paper_clauses=["T3", "T3a", "Eq. (5)"],
        earliest_stage=2,
        direct_stock_stage=2,
        subject="Per-member writer ownership, seal, and direct read binding on Stage-2 stock arms",
        cut="stage2.member_finalization_through_scorer_read",
        typ="member_custody_binding",
        expected={
            "per_member_predicate": "W_m and boundWrite(i, m) and seal(m) and [kappa_read == kappa_seal] and [d(read) == d(seal)]",
            "members_covered": [
                "admission.json",
                "untouched/runtime.json", "untouched/phase", "untouched/stdout.log", "untouched/stderr.log",
                "untouched/F01.warmup.json", "untouched/F07.warmup.json", "untouched/F01.warm1.json", "untouched/F07.warm1.json",
                "observed/runtime.json", "observed/phase", "observed/stdout.log", "observed/stderr.log",
                "observed/F01.warmup.json", "observed/F07.warmup.json", "observed/F01.warm1.json", "observed/F07.warm1.json",
                "observed/observations.jsonl", "observed/tensors.bin",
            ],
            "authentication": "256-bit per-run HMAC-SHA256 over sealed member inventory + object identities + process instances + nonce",
        },
        comparator="event_join_hmac_and_sha256",
        evidence_source="Stage-2 worker/supervisor/scorer custody receipts (partitioned from continuity in exec.original_continuity and completeness in exec.stock_inventory)",
        evidence_locator="prospective:@run_root/custody-receipt.json",
        historical_reference="docs/coordination/WP-0045/windows-check.json; docs/coordination/WP-0045/disposition.json",
        status="prospective_stage2_bound",
        missing_precondition=["Extend WP-0045 single-member custody helper to multi-member stock output set before Stage-2 freeze"],
        alternatives_or_notes="Explicitly partitioned: exec.original owns W_m/boundWrite/seal/endpoint-join; exec.original_continuity owns continuous(m) handle-interval; exec.stock_inventory owns B_arm multiset/uniqueness completeness.",
    )

    # --- 89..103: 15 native.1445..1449.C0_raw/C1_post_rep/C2_post_page ---
    phase_meta = [
        ("C0_raw", 1174, 0, "Raw lm_head FP32 score vector: finite everywhere in V={0..129279} (X_0 empty)"),
        ("C1_post_rep", 1238, 1, "Post-repetition FP32 vector: phase-local Eq. (8) against C0_raw under independently derived D_1"),
        ("C2_post_page", 1282, 2, "Post-page FP32 vector: phase-local Eq. (8) against supplied C1_post_rep under independently derived D_2 (NOT cumulative D_1 union D_2)"),
    ]
    for pos in range(1445, 1450):
        rrec = retained_by_pos[pos]
        row_idx = rrec["row"]
        for phase_name, offset, p_idx, rule_desc in phase_meta:
            copy_rec = rrec["copies"][p_idx]
            add(
                key=f"native.{pos}.{phase_name}",
                paper_clauses=["T5", "Eq. (8)", "Theorem 3"],
                earliest_stage=2,
                direct_stock_stage=2,
                subject=f"F07.warm1 observed stock row {row_idx} (position {pos}), phase {phase_name}",
                cut=f"stage2.generator_offset_{offset}",
                typ="fp32_le_vector_129280",
                expected={
                    "vocab_size": 129280,
                    "byte_length": 517120,
                    "dtype": "f32le",
                    "neg_inf_word_be_hex": "ff800000",
                    "neg_inf_bytes_le_hex": "000080ff",
                    "generator_qualname": "UnlimitedOCRForCausalLM._uocr_generate",
                    "generator_offset_cpython_3_12_10": offset,
                    "phase_rule": rule_desc,
                    "expected_masks_on_f07_prefix": {"D1_rep_banned": [], "D2_page_banned": [1]},
                    "stream_and_lifetime_order": "producing_write < source_read <= copy_completion < host_consumption and copy_completion < next_conflicting_write_or_free",
                    "historical_reference_distinct_from_pass_rule": {
                        "archive_vector_sha256": copy_rec["vector_sha256"],
                        "archive_copy_id": copy_rec["copy_id"],
                        "archive_journal_serial": copy_rec["journal_serial"],
                        "archive_actual_emission": rrec["actual_emission"],
                        "archive_final_gap": rrec["final_top_two"]["difference"],
                    },
                },
                comparator="phase_local_fp32_eq8_bitwise_plus_copy_ancestry",
                evidence_source="Stage-2 observed arm PEP 669 instruction monitor + pinned D2H transport + independent Phase-Local Eq. (8) scorer",
                evidence_locator=f"prospective:@arm/observations.jsonl#row={row_idx},tag={phase_name}",
                historical_reference=f"docs/coordination/WP-0043/native-evidence.json#/retained_rows/{row_idx}/copies/{p_idx}",
                status="prospective_stage2_bound",
                missing_precondition=[
                    "Fix WP-0043/scorer.py L304 cumulative-mask bug (must use phase-local D_2 against supplied C1_post_rep, per Theorem 3)",
                    "Stage-2 observed stock execution",
                ],
                alternatives_or_notes="Offset 1174/1238/1282 binds strictly to CPython 3.12.10 + modeling_unlimitedocr.py sha256 f6df813c.... Archive SHA-256 is a reference comparison only, never a substitute for phase-local Eq. (8) verification.",
            )

    # --- 104: native.snapshot ---
    add(
        key="native.snapshot",
        paper_clauses=["T6", "T8a", "Eq. (9)"],
        earliest_stage=2,
        direct_stock_stage=2,
        subject="Five F07.warm1 observed stock rows (positions 1445..1449) at declared B and D cuts",
        cut="stage2.declared_B_and_D_cuts",
        typ="restorable_state_snapshot_schema",
        expected={
            "rows": [0, 1, 2, 3, 4],
            "positions": [1445, 1446, 1447, 1448, 1449],
            "entry_layer11_cache_lengths": [1445, 1446, 1447, 1448, 1449],
            "exit_layer11_cache_lengths": [1446, 1447, 1448, 1449, 1450],
            "required_field_groups": [
                "h10_and_layer11_args", "position_ids_and_masks", "per_layer_0_to_11_KV_and_dash_idx_k_with_lengths",
                "dash_router_tensors_and_valid_spans", "page_rope_state_and_uocr_pg",
                "pre_token_history_and_guard_cursors", "module_global_and_native_receiver_bindings",
            ],
            "expanded_finiteness_domain": [
                "all WP-0043 native_score.py L532-533 tensors",
                "attention_result (1280 BF16 per row)",
                "active pre-sanitization router x (scores_pre_clean)",
                "selected valid bias (route_final)",
            ],
            "storage_and_alias_metadata": "dtype, shape, strides, storage_offset, storage_bytes, device_index + run_device_uuid, alias_class, pre-sanitization values",
        },
        comparator="typed_byte_alias_expanded_finiteness_and_restorability_schema",
        evidence_source="Stage-2 observed arm observations.jsonl + tensors.bin + independent offline scorer",
        evidence_locator="prospective:@arm/observations.jsonl#tags=B,D; prospective:@arm/tensors.bin",
        historical_reference="docs/research/WP-0042/scoring.md; docs/agent-reports/eld-rd-reviewer/WP-0043/003_2026-11-27_review_eld-rd-reviewer.md#L48",
        status="prospective_stage2_bound",
        missing_precondition=[
            "Add attention_result, pre-sanitization router x, and valid bias to Stage-2 scorer finiteness list (omitted in WP-0043 native_score.py L532-533)",
            "Stage-2 execution and independent schema/restorability verification",
        ],
        alternatives_or_notes="Checking finiteness and schema establishes pre-replay restorability witness restorable(t) only; actual replay parity Y_F(R(C(s))) = Y_F(s) remains Stage 3 (private.parity).",
    )

    # --- 105: private.parity ---
    add(
        key="private.parity",
        paper_clauses=["T6", "T8a", "Eq. (9)", "Eq. (12)"],
        earliest_stage=3,
        direct_stock_stage=3,
        subject="Stage-3 anchored and linked private replay branches on F07.warm1 positions 1445..1449",
        cut="stage3.anchored_trials_and_linked_bridges",
        typ="private_replay_trace_equivalence",
        expected={
            "equivalence_predicate": "forall s in S_test: Y_F(R(C(s))) == Y_F(s)",
            "design_denominators": {
                "native_and_private_rows": 35,
                "private_block_calls": 30,
                "paired_comparisons": 40,
                "whole_survivor_selections": 10,
                "linked_bridges": 8,
                "protected_source_rows": 5,
                "source_continuation_to_eos": True,
            },
            "a1_transaction_rules": "private paths commit 0 to authoritative source; committing path publishes selected (u, y, g) atomically once",
        },
        comparator="trace_equivalence_plus_source_noninterference",
        evidence_source="Future Stage-3 separately authored, independently reviewed private replay runner and scorer",
        evidence_locator="prospective:stage3_unreleased",
        historical_reference="docs/coordination/WP-0042/disposition.json#/future_obligations; docs/research/WP-0042/scoring.md; docs/editions/WP-0045/shared.md",
        status="prospective_stage3_deferred",
        missing_precondition=[
            "Passing Stage-2 stock run r with V_stock(r) == P and J_5(r) == True",
            "Complete Stage-3 private plan P_3 and independent review Rev_3",
            "Separate Stage-3 coordinator release",
        ],
        alternatives_or_notes="Zero Stage-3 runs executed; F07 price ($28.50) was already correct historically; output-fed block-11 recurrence remains a separate unmeasured question.",
    )

    # --- 106..117: 12 Revision-1 amendment obligations (repaired from verbatim placeholders) ---
    add(
        key="plan.static_consistency",
        paper_clauses=["T8", "Eq. (11)", "ASSESS()"],
        earliest_stage=0,
        direct_stock_stage=0,
        subject="Complete Stage-0/1/2/3 proposal manifest across all declared cuts",
        cut="stage0.static_manifest_validation",
        typ="static_intersection_consistency",
        expected={
            "rule": "For every atom k in scoped plan, validate all frozen prescriptions L_{k,i} on same (subject, cut) BEFORE runtime deferral: empty intersection -> X_static (M); missing required binding in scope -> B_required (U)",
            "reconciled_conflicts": [
                "plan43 infer_multi vs worker43 model.infer resolved to model.infer(..., image_file=list(pages), return_dict=True)",
                "plan43 venv argv[0] vs direct-stock @base/python.exe argv[0] resolved via direct-stock route contract",
                "WP-0045 OMP/MKL/OPENBLAS_NUM_THREADS='1' vs worker43 ABSENT resolved to ABSENT",
            ],
        },
        comparator="static_intersection_nonempty_before_deferral",
        evidence_source="Offline Stage-0 static consistency checker (controls.py:eval_assess) + independent review",
        evidence_locator="docs/research/WP-0046/controls.py#eval_assess",
        historical_reference="Paper I T8 p. 11 (reviewed revision 1); docs/research/WP-0046/first.md#M-08",
        status="bound_stage0",
        missing_precondition=None,
        alternatives_or_notes="Fixes Paper I Eq. (11) vs ASSESS() contradiction: static conflicts and in-scope missing bindings enter X_T^(s)/W_T^(s) even when d_k > s.",
    )
    add(
        key="cpu.hash_effective",
        paper_clauses=["T2a", "Eq. (7)"],
        earliest_stage=1,
        direct_stock_stage=1,
        subject="Stage-1 direct-stock CPU worker effective startup flags and hash seed",
        cut="stage1.cut1a_startup",
        typ="effective_startup_flags_tuple",
        expected={
            "e_launch.PYTHONHASHSEED": {"state": "present", "value": "0"},
            "e_child.PYTHONHASHSEED": {"state": "present", "value": "0"},
            "sys.flags.ignore_environment": 0,
            "sys.flags.hash_randomization": 0,
            "sys.flags.isolated": 0,
            "sys.flags.no_site": 0,
            "sys.flags.no_user_site": 1,
            "sys.flags.dont_write_bytecode": 1,
            "sys.flags.safe_path": True,
            "sys.flags.utf8_mode": 1,
        },
        comparator="strict_typed_exact_int_vs_bool",
        evidence_source="Stage-1 worker Cut 1A startup receipt (sys.flags + os.environ) joined to supervisor lpEnvironment",
        evidence_locator="prospective:@arm/cut1a-startup.json#/flags",
        historical_reference="Paper I T2a p. 4 (reviewed revision 1); docs/research/WP-0046/controls.py#eval_startup",
        status="prospective_stage1_bound",
        missing_precondition=["Stage-1 CPU execution"],
        alternatives_or_notes="Extends Q_hash to include utf8_mode, safe_path, no_user_site, dont_write_bytecode, isolated, no_site with exact CPython 3.12.10 types (int vs bool).",
    )
    add(
        key="cpu.import_resolution",
        paper_clauses=["T2a", "T1"],
        earliest_stage=1,
        direct_stock_stage=1,
        subject="Stage-1 direct-stock CPU worker venv resolution, sys.path, .pth, and loaded module/DLL origins",
        cut="stage1.cut1a_and_cut1b_imports",
        typ="import_and_dll_origin_map",
        expected={
            "venv_activation": "e_launch.__PYVENV_LAUNCHER__ == @venv/Scripts/python.exe and e_child.__PYVENV_LAUNCHER__ == ABSENT",
            "sys_executable": "@venv/Scripts/python.exe",
            "sys_orig_argv0": "@base/python.exe",
            "sys_prefix_and_exec_prefix": "@venv",
            "pyvenv_cfg_include_system_site_packages": "false",
            "base_site_packages_excluded": True,
            "venv_site_packages_included": True,
            "sitecustomize_and_usercustomize_absent": True,
            "triton_spec": None,
            "all_loaded_modules_within_allowed_roots": True,
            "all_in_coverage_dlls_verified_via_debug_load_event": True,
            "pinned_runtime_files_sha256": {
                **source41["versions"]["runtime_source_sha256"],
                **ACTIVE_RUNTIME_SHA256,
            },
        },
        comparator="ordered_path_root_containment_and_sha256",
        evidence_source="Stage-1 Cut 1A/1B child receipts + supervisor pre-launch pyvenv.cfg/.pth guards + LOAD_DLL_DEBUG_EVENT hashes",
        evidence_locator="prospective:@arm/cut1b-imports.json",
        historical_reference="Paper I T2a p. 4 (reviewed revision 1); docs/research/WP-0046/proposal.md#site-pth-and-dll-origin-mapping",
        status="prospective_stage1_bound",
        missing_precondition=[
            "Stage-1 pre-launch measurement of @venv/pyvenv.cfg and @venv/Lib/site-packages/*.pth inventory on local host",
            "Stage-1 CPU execution",
        ],
        alternatives_or_notes="Resolves bare -s -P -B -u base site-packages leak verified on stdlib CPython 3.12.10; documents -S manual-bootstrap alternative in proposal.md.",
    )
    add(
        key="cpu.original_inventory",
        paper_clauses=["T3a", "Eq. (5)"],
        earliest_stage=1,
        direct_stock_stage=1,
        subject="Stage-1 CPU rehearsal expected, sealed, and scorer-read member inventory per arm",
        cut="stage1.seal_through_scorer_read",
        typ="inventory_bijection_and_keyed_custody",
        expected={
            "expected_member_keys_per_arm": ["cut1a-startup.json", "cut1b-imports.json", "rehearsal-payload.bin"],
            "unique_logical_keys": True,
            "unique_physical_objects": True,
            "auth_qr_required": True,
            "multiset_relations": "b(I_r) == b(E_r) and b(R_r) == b(I_r)",
            "keyed_member_custody": "forall k in E_r: B_{m(k)} == P including FILE_SHARE_READ continuous handle overlap",
        },
        comparator="unique_key_multiset_equality_plus_keyed_Bm",
        evidence_source="Stage-1 frozen expected schema E_r, supervisor HMAC-sealed inventory I_r, and scorer fresh read list R_r",
        evidence_locator="prospective:@arm/scorer.json#/inventory",
        historical_reference="Paper I T3a p. 6 (reviewed revision 1); docs/research/WP-0046/controls.py#eval_inventory",
        status="prospective_stage1_bound",
        missing_precondition=["Stage-1 probe implementation and release"],
        alternatives_or_notes="Corrects amendments.py:inventory() M-hidden-by-U bug: an omitted sealed member or failed custody yields M even when read receipt is missing.",
    )
    add(
        key="exec.original_continuity",
        paper_clauses=["T3", "T3a", "Eq. (5)"],
        earliest_stage=2,
        direct_stock_stage=2,
        subject="Continuous Windows NTFS read-only handle protection over every Stage-2 stock member",
        cut="stage2.seal_through_scorer_read",
        typ="handle_interval_continuity",
        expected={
            "interval_cover": "I_handle superset [t_seal, t_read] with overlapping worker -> supervisor -> scorer DuplicateHandle(FILE_GENERIC_READ) handoff before writer close",
            "writer_open": "CREATE_NEW, GENERIC_READ|GENERIC_WRITE, FILE_SHARE_READ, inherit=False",
            "scorer_open": "OPEN_EXISTING, GENERIC_READ, FILE_SHARE_READ (excludes FILE_SHARE_WRITE and FILE_SHARE_DELETE)",
            "corroborating_metadata": "volume_serial, file_index_or_file_id_128, nNumberOfLinks == 1, NTFS filesystem, unchanged byte length/sha256",
        },
        comparator="interval_cover_share_policy_and_object_id_exact",
        evidence_source="Stage-2 worker/supervisor/scorer Win32 handle lifecycle and QPC timestamps",
        evidence_locator="prospective:@run_root/continuity-trace.json",
        historical_reference="Paper I T3a p. 6 (reviewed revision 1); docs/research/WP-0045/stage.py; docs/research/WP-0045/win.py",
        status="prospective_stage2_bound",
        missing_precondition=["Multi-member handle-guard harness implementation for Stage-2 stock outputs"],
        alternatives_or_notes="Endpoint volume/file-ID equality alone without held-handle overlap leaves [t_seal, t_read] unobserved (U).",
    )
    add(
        key="exec.stock_inventory",
        paper_clauses=["T3a"],
        earliest_stage=2,
        direct_stock_stage=2,
        subject="Stage-2 stock arm expected vs sealed vs scorer-read member inventory",
        cut="stage2.output_finalization_and_scoring",
        typ="inventory_bijection_and_keyed_custody",
        expected={
            "independent_schema_Fr": "Deterministic expansion E_r = F_r(q_r) over authenticated Stage-2 arms and 4-call schedule",
            "unique_logical_keys": True,
            "unique_physical_objects": True,
            "multiset_relations": "b(I_r) == b(E_r) and b(R_r) == b(I_r)",
            "ordering_check_projections": ["call_schedule_order", "append_journal_seq_order"],
            "keyed_member_custody": "forall k in E_r: B_{m(k)} == P",
        },
        comparator="unique_key_multiset_and_projection_order_exact",
        evidence_source="Stage-2 frozen schema E_r, HMAC-sealed inventory I_r, and read-only offline scorer read set R_r",
        evidence_locator="prospective:@run_root/outcome-inventory.json",
        historical_reference="Paper I T3a p. 6 (reviewed revision 1); docs/research/WP-0043/native_score.py#L393-L408",
        status="prospective_stage2_bound",
        missing_precondition=["Stage-2 execution and independent scorer verification"],
        alternatives_or_notes="Upgrades WP-0043 native_score.py post-exit directory hash scan to independent E_r vs sealed I_r vs direct-read R_r under T3a.",
    )
    add(
        key="native.support_choice",
        paper_clauses=["T5", "Eq. (8)", "Eq. (7)"],
        earliest_stage=2,
        direct_stock_stage=2,
        subject="Stage-2 F07.warm1 decoded score rows (positions 1445..1449)",
        cut="stage2.decoded_score_row",
        typ="support_oob_and_winner_fault_sets",
        expected={
            "X_supp": "{empty_support : A == empty}",
            "X_oob": "{emitted_outside_support : y_obs is observed and y_obs not in A} (evaluated even if A == empty or X_0..2 nonempty)",
            "X_choice": "{winner_mismatch : A nonempty and X_0..2 empty and y_obs is observed and y_obs != min argmax_{j in A} value(z^2_j)}",
            "U_phase_and_emission": "missing vectors/masks/emission enter U while retaining all decidable faults in X",
            "signed_zero_rule": "-0.0 and +0.0 tie numerically (smallest ID wins) while bitwise word equality distinguishes 0x80000000 from 0x00000000",
        },
        comparator="fault_and_missing_set_exact_with_M_dominance",
        evidence_source="Stage-2 independent Phase-Local Eq. (8) scorer on observed F07.warm1 score triples",
        evidence_locator="prospective:@run_root/score-native.json#/rows",
        historical_reference="Paper I T5 p. 8 (reviewed revision 1); docs/research/WP-0046/controls.py#eval_score_phase",
        status="prospective_stage2_bound",
        missing_precondition=["Update WP-0043 scorer to amended Eq. (8) + X_oob before Stage-2 freeze"],
        alternatives_or_notes="Resolves fresh finding M-05: decouples emitted_outside_support from score-phase cleanliness and formalizes partial-phase missingness.",
    )
    add(
        key="native.storage",
        paper_clauses=["T6"],
        earliest_stage=2,
        direct_stock_stage=2,
        subject="Every captured tensor node in Stage-2 observed F07.warm1 snapshots",
        cut="stage2.stock_capture_tensor_serialization",
        typ="tensor_layout_capacity_and_device_bounds",
        expected={
            "required_metadata": [
                "dtype", "shape", "strides", "storage_offset", "storage_bytes",
                "element_size", "bytes", "device_index", "run_bound_device_uuid", "alias_class",
            ],
            "nonempty_bound": "all(n_i > 0) and all(s_i >= 0) and o >= 0 and b*(1 + o + sum((n_i - 1)*s_i)) <= B_storage",
            "empty_view_bound": "0 <= b * o <= B_storage when prod(n_i) == 0",
            "writable_view_non_aliasing": "distinguish read-bound containment from intra-tensor write non-aliasing (zero/overlapping strides)",
        },
        comparator="exact_integer_bounds_and_device_join",
        evidence_source="Stage-2 observed arm tensors.bin node metadata + offline scorer",
        evidence_locator="prospective:@arm/observations.jsonl#tensor_nodes",
        historical_reference="Paper I T6 p. 9 (reviewed revision 1); docs/research/WP-0043/transfer.py#L11-L29",
        status="prospective_stage2_bound",
        missing_precondition=["Add empty-view offset check 0 <= b*o <= B_storage and run-bound device UUID to tensor validator before Stage-2 freeze"],
        alternatives_or_notes="Fixes WP-0043/transfer.py L15-16 omitting storage_offset bound check on zero-numel views.",
    )
    add(
        key="plan.loss_model",
        paper_clauses=["T7", "Eq. (10)"],
        earliest_stage=0,
        direct_stock_stage=0,
        subject="WP-0046 measurement-selection channel and erasure/loss assumptions",
        cut="stage0.measurement_design",
        typ="channel_and_loss_budget_declaration",
        expected={
            "stage1_channel_model": "non-informative identifiable erasures (missing witnesses -> U) over independent observation sources; coordinate erasure budget f = 0 (no silent fallback; any missing mandatory Stage-1 receipt yields U)",
            "correlated_source_note": "Single failed supervisor/worker process erases multiple coordinates; robustness claims require source-group hitting constraints, not coordinate count alone",
            "deterministic_loss_histories_distinguished": True,
            "infeasibility_rule": "f >= min |S(h,h')| declared infeasible rather than silently dropped",
        },
        comparator="explicit_channel_and_budget_binding",
        evidence_source="Stage-0 proposal measurement-design declaration + offline T7 checks",
        evidence_locator="docs/research/WP-0046/proposal.md#measurement-and-loss-model",
        historical_reference="Paper I T7 p. 10 (reviewed revision 1); docs/research/WP-0046/first.md#M-07",
        status="bound_stage0",
        missing_precondition=None,
        alternatives_or_notes="Explicitly claims f=0 fail-closed identification (any missing witness returns U, never P) rather than claiming f>=1 erasure redundancy.",
    )
    add(
        key="plan.diagnostics",
        paper_clauses=["T1", "T4", "Eq. (2)", "Eq. (6)", "Eq. (7)"],
        earliest_stage=0,
        direct_stock_stage=0,
        subject="Crosswalk comparator and full-record diagnostic aggregator across all WP-0046 stages",
        cut="stage0.crosswalk_and_scorer_contract",
        typ="diagnostic_contract",
        expected={
            "eq6_precedence": ["J_k == 0 -> incomparable", "J_k == ? or x == ? or y == ? -> unobserved", "type_error -> schema_mismatch", "eta_k(x) == eta_k(y) -> same", "otherwise -> different"],
            "tagged_values": "explicit state in {'present','absent','unobserved'}; JSON null is state='present', value=null; bool != int",
            "conflict_classes_preserved": ["M_field", "M_integrity", "M_static_plan"],
            "both_minimal_sets_returned": ["first_conflict = min_strict_prec(X)", "first_finding = min_strict_prec(X union U)"],
            "order_integrity_check": "irreflexive acyclic strict partial order required; cycle emits M_integrity",
        },
        comparator="exact_precedence_and_minimal_set_equality",
        evidence_source="Stage-0 controls.py:eval_crosswalk_and_diagnostics + control_cases.json",
        evidence_locator="docs/research/WP-0046/controls.py#eval_crosswalk_and_diagnostics",
        historical_reference="Paper I T4 p. 7 (reviewed revision 1); docs/research/WP-0046/first.md#M-04",
        status="bound_stage0",
        missing_precondition=None,
        alternatives_or_notes="Resolves fresh findings M-02 and M-04 (strict < vs reflexive <=, cycle detection, tagged ABSENT vs null, bool != int, and dual minimal sets missing from WP-0043 native_score.py).",
    )
    add(
        key="private.plan",
        paper_clauses=["T8", "T8a", "Eq. (12)"],
        earliest_stage=0,
        direct_stock_stage=3,
        subject="Stage-3 private replay specification P_3 (deferred out of Stage-1 CPU scope)",
        cut="stage3.pre_proposal_admission",
        typ="stage3_plan_gate",
        expected={
            "required_when_stage3_proposed": [
                "A1 branch selection and single atomic commit semantics",
                "eight keyed linked bridges",
                "expanded finiteness domain (attention_result, active pre-sanitization router x, valid bias)",
                "private alias isolation and pause-resume fencing",
                "protected source continuation to native EOS",
            ],
            "stage0_for_stage1_status": "explicitly deferred until Stage-2 passes and Stage-3 is separately proposed",
        },
        comparator="stage_scoped_plan_completeness_and_static_consistency",
        evidence_source="Future Stage-3 proposal manifest P_3 and independent review Rev_3",
        evidence_locator="prospective:stage3_unreleased",
        historical_reference="Paper I T8a p. 12 (reviewed revision 1); docs/coordination/WP-0042/disposition.json",
        status="prospective_stage3_deferred",
        missing_precondition=[
            "Not required for Stage-1 CPU qualification",
            "Required completely before Stage-3 proposal admission (considerPrivateReplay)",
        ],
        alternatives_or_notes="Reconciles earliest_stage=0 in bundle/register.json with Stage-0 scoping (M-08): scoped Stage-1 planning does not fail on Stage-3 P_3 deferral.",
    )
    add(
        key="private.origin",
        paper_clauses=["T8a", "Eq. (12)"],
        earliest_stage=2,
        direct_stock_stage=2,
        subject="Qualification of five same-run restorable stock rows as candidate Stage-3 replay inputs",
        cut="stage2.post_stock_qualification_gate",
        typ="same_run_five_row_bijection_gate",
        expected={
            "required_keys": [
                {"arm": "observed", "call": "F07.warm1", "position": p}
                for p in range(1445, 1450)
            ],
            "predicate": "exists r: V_stock(r) == 'P' and J_5(r, R_cand)",
            "J_5_clauses": [
                "unique 5-key bijection b(keys(R_cand)) == b(K)",
                "forall t in R_cand: run(t) == r",
                "forall t in R_cand: originalBound(r, t) == True",
                "forall t in R_cand: restorable(t) == True",
            ],
            "historical_wp0043_excluded": "WP-0043 joint M (0/1 pairs, 0/5 rows) cannot satisfy V_stock(r) == 'P'",
        },
        comparator="same_run_bijection_and_boolean_gate",
        evidence_source="Stage-2 passing stock run verdict V_stock(r) + offline replay-gate check (controls.py:eval_replay_gate)",
        evidence_locator="docs/research/WP-0046/controls.py#eval_replay_gate",
        historical_reference="Paper I T8a p. 12 (reviewed revision 1); docs/coordination/WP-0043/native-evidence.json",
        status="prospective_stage2_bound",
        missing_precondition=[
            "Completed Stage-2 stock run achieving V_stock(r) == 'P' on both untouched and observed arms",
        ],
        alternatives_or_notes="Rejects mixed-run rows, duplicate positions, non-observed arms, unbound originals, unrestorable snapshots, and historical WP-0043 M.",
    )

    assert len(entries) == 118, f"Expected 118 entries, got {len(entries)}"
    assert len({e["key"] for e in entries}) == 118, "Duplicate keys detected"

    return {
        "schema": "wp0046-direct-stock-register/1",
        "proposal_id": PROPOSAL_ID,
        "author": "eld-owner-probe",
        "reference_commit": REF_COMMIT,
        "status": "Stage 0 proposal-only register; 0 prospective target executions; no stage released",
        "symbolic_roots": SYMBOLIC_ROOTS,
        "unknown_semantics": "Explicit tagged values distinguish state='present' (including JSON null or empty string ''), state='absent' (measured absent key/attribute), and state='unobserved' (missing observation ?).",
        "entry_count": len(entries),
        "stage_counts_original": {
            str(s): sum(1 for e in entries if e["earliest_stage"] == s) for s in range(4)
        },
        "stage_counts_direct_stock": {
            str(s): sum(1 for e in entries if e["direct_stock_stage"] == s) for s in range(4)
        },
        "status_counts": {
            st: sum(1 for e in entries if e["status"] == st)
            for st in sorted({e["status"] for e in entries})
        },
        "entries": entries,
    }


def serialize(manifest: dict) -> str:
    return json.dumps(manifest, indent=2, ensure_ascii=True) + "\n"


def check_hygiene(text: str) -> None:
    m = HOST_PATH_RE.search(text)
    if m:
        raise ValueError(f"Host path or username leaked into public register: {m.group(0)!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify WP-0046 118-row direct-stock register.")
    parser.add_argument("--verify", action="store_true", help="Verify committed register.json matches generator output.")
    args = parser.parse_args()

    manifest = build_manifest()
    rendered = serialize(manifest)
    check_hygiene(rendered)

    if args.verify:
        if not OUT_PATH.is_file():
            raise SystemExit(f"Missing {OUT_PATH}")
        actual = OUT_PATH.read_text(encoding="utf-8")
        check_hygiene(actual)
        if actual != rendered:
            raise SystemExit("register.json differs from deterministic generator output")
        sha = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
        print(
            json.dumps(
                {
                    "verified": True,
                    "entry_count": manifest["entry_count"],
                    "unique_keys": len({e["key"] for e in manifest["entries"]}),
                    "stage_counts_original": manifest["stage_counts_original"],
                    "stage_counts_direct_stock": manifest["stage_counts_direct_stock"],
                    "status_counts": manifest["status_counts"],
                    "sha256": sha,
                },
                sort_keys=True,
            )
        )
        return 0

    OUT_PATH.write_text(rendered, encoding="utf-8", newline="\n")
    sha = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    print(f"Wrote {OUT_PATH.name}: {manifest['entry_count']} entries, sha256={sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
