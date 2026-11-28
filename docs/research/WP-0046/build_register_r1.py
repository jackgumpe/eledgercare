"""Deterministic stdlib generator and verifier for docs/research/WP-0046/register-r1.json.

Post-opening r1 revision incorporating peer exchange (eld-rd-reviewer / Claude)
and read-only Git archive verifications at e43af2e263f55478d1d551a5a095536b042589c2.

Preserves all 118 original keys 1-to-1 in `entries` AND adds 44 explicit
`extended_obligations` closing O4 (31-key closed child env + ABSENT closure +
cpu.env.*), O5 (base Python, venv launcher, 5 runtime files, 3 forbidden absent
modules, closed 33-dist set, 32 wheels, 6 Git-verified WP-0043 local closure
modules, unpinned pyvenv.cfg/.pth), O6 (Stage 1a vs Stage 1b split + 3 live
controls), O8 (5 per-row native.{1445..1449}.support_choice sub-atoms), and
M1/M2 (scoped plan counts Pi_0..Pi_3 and Stage 1->2 projection bridge).

No private input, host path, model/torch import, device access, or network I/O.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_PATH = Path(__file__).resolve().parent / "register-r1.json"
REF_COMMIT = "e43af2e263f55478d1d551a5a095536b042589c2"
PROPOSAL_ID = "wp0046-direct-stock-r1"
PEER_EXCHANGE_TIP = "1c9690b9eab22dfdf0c943815f5440e6563f2350"
TURN1_FREEZE = "6fa242950ffd4dfd1d19accc9271e88aada2d552"

SYMBOLIC_ROOTS = {
    "@base": "Pinned CPython 3.12.10 x64 base directory (python.exe sha256 4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a)",
    "@venv": "Pinned Q0 virtual environment root (pyvenv.cfg include-system-site-packages=false; Lib/site-packages holds closed 33 distributions = 32 pinned + pip 25.0.1)",
    "@q0_root": "Pinned Q0 read-only storage root containing @venv, @model, and @wheelhouse",
    "@model": "Pinned unmodified Unlimited-OCR-2 revision 0480966938291445591f69f08a13b041c073a96a directory (18 verified files)",
    "@wheelhouse": "Pinned Q0 offline wheelhouse directory (32 verified wheels)",
    "@repo": "Public repository jackgumpe/eledgercare at bound commit",
    "@worktree": "Assigned isolated role worktree root for the released stage",
    "@source": "Directory containing pinned frozen Python probe or worker scripts under @worktree",
    "@speed_root": "Private local-only per-packet output root outside Git",
    "@run_root": "Fresh exclusive-create per-run directory under @speed_root",
    "@arm": "Fresh exclusive-create per-unit / per-arm directory under @run_root for a single cold launch",
}

BASE_PYTHON_SHA256 = "4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a"
VENV_LAUNCHER_SHA256 = "0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14"
ACTIVE_RUNTIME_SHA256 = {
    "torch/lib/cudart64_13.dll": "58c509047f9dd1879cf82c6d5375a95c02c7bd295ae6c8362c745c936e2afc31",
    "torch/cuda/streams.py": "44762c1ec5b741b6430812e37fcc7364c6a5556834caa6ba2f15b1154fad699d",
}
LOCAL_CLOSURE_MODULES = [
    "timing.py",
    "bindings.py",
    "capture.py",
    "transfer.py",
    "native_observer.py",
    "limits.py",
]
# Exact 31-key closed child allowlist verified by AST from worker43.py L189-199.
WORKER43_OS_PASSTHROUGH_7 = [
    "SystemRoot",
    "windir",
    "OS",
    "ComSpec",
    "NUMBER_OF_PROCESSORS",
    "PROCESSOR_ARCHITECTURE",
    "PATHEXT",
]
WORKER43_EXPLICIT_24 = [
    "CUDA_CACHE_PATH",
    "CUDA_DEVICE_ORDER",
    "CUDA_VISIBLE_DEVICES",
    "HF_HOME",
    "HF_HUB_DISABLE_TELEMETRY",
    "HF_HUB_DISABLE_XET",
    "HF_HUB_OFFLINE",
    "HF_MODULES_CACHE",
    "HOME",
    "PATH",
    "PIP_NO_INDEX",
    "PYTHONDONTWRITEBYTECODE",
    "PYTHONHASHSEED",
    "PYTHONIOENCODING",
    "PYTHONNOUSERSITE",
    "PYTHONUNBUFFERED",
    "PYTHONUTF8",
    "TEMP",
    "TMP",
    "TORCHINDUCTOR_CACHE_DIR",
    "TORCH_HOME",
    "TRANSFORMERS_OFFLINE",
    "USERPROFILE",
    "XDG_CACHE_HOME",
]
FORBIDDEN_ABSENT_ENV_SENTINELS = [
    "__PYVENV_LAUNCHER__",
    "PYTHONPATH",
    "PYTHONHOME",
    "PYTHONSAFEPATH",
    "PYTHONCASEOK",
    "PYTHONWARNINGS",
    "PYTHONUSERBASE",
    "PYTHONSTARTUP",
    "VIRTUAL_ENV",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "CUBLAS_WORKSPACE_CONFIG",
]
STAGE_ORDER = ["0", "1a", "1b", "2", "3"]
HOST_PATH_RE = re.compile(
    r"(?i)(?:[A-Z]:[/\\]|[/\\]Users[/\\]|AppData[/\\]Local|Asp\.net Projects|eLedgerCare-(?:Speed|Q0)|w04[0-9]-)"
)


def load_repo_json(rel_path: str) -> dict[str, Any]:
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


def sha256_repo_file(rel_path: str) -> str:
    return hashlib.sha256((REPO_ROOT / rel_path).read_bytes()).hexdigest()


def normalize_pep503(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def wheel_map(wheel_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for entry in wheel_doc["wheels"]:
        whl = entry["wheel"]
        dist_prefix = whl.split("-", 1)[0]
        mapping[normalize_pep503(dist_prefix)] = {
            "wheel": whl,
            "sha256": entry["sha256"],
            "size": entry["size"],
            "kind": entry["kind"],
            "metadata_sha256": entry["metadata"]["metadata_sha256"],
        }
    return mapping


def build_manifest() -> dict[str, Any]:
    plan43 = load_repo_json("docs/coordination/WP-0043/plan-canonical.json")
    inputs43 = load_repo_json("docs/coordination/WP-0043/native-inputs.json")
    native43 = load_repo_json("docs/coordination/WP-0043/native-evidence.json")
    device43 = load_repo_json("docs/coordination/WP-0043/device-release.json")
    source41 = load_repo_json("docs/research/WP-0041/source.json")
    wheels05 = load_repo_json(
        "docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/checks/02-verify-wheelhouse.json"
    )
    venv33 = load_repo_json(
        "docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/checks/03-pip-check-and-venv-inventory.json"
    )
    preflight05 = load_repo_json(
        "docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/checks/05-preflight-cpu.json"
    )
    wmap = wheel_map(wheels05)
    retained_by_pos = {r["position"]: r for r in native43["retained_rows"]}

    # Verify exact 33 distributions = 32 pinned + pip 25.0.1 under PEP 503 normalization.
    inv33_norm = {
        normalize_pep503(d["name"]): {"name": d["name"], "version": d["version"]}
        for d in venv33["installed_distributions"]
    }
    assert len(inv33_norm) == 33, f"Expected 33 installed dists, got {len(inv33_norm)}"
    assert inv33_norm["pip"]["version"] == "25.0.1"
    for dn, dv in source41["versions"]["verified_pinned_distributions"].items():
        assert inv33_norm[normalize_pep503(dn)]["version"] == dv

    # Verify exact 31 child env keys bijection.
    all_31 = set(WORKER43_OS_PASSTHROUGH_7) | set(WORKER43_EXPLICIT_24)
    assert len(all_31) == 31
    assert len(set(WORKER43_OS_PASSTHROUGH_7) & set(WORKER43_EXPLICIT_24)) == 0

    entries: list[dict[str, Any]] = []
    extended: list[dict[str, Any]] = []

    def add_entry(
        target: list[dict[str, Any]],
        *,
        key: str,
        paper_clauses: list[str],
        earliest_stage: int | None,
        direct_stock_stage: str,
        subject: str,
        cut: str,
        typ: str,
        expected: object,
        comparator: str,
        evidence_source: str,
        evidence_locator: str,
        historical_reference: str,
        binding_status: str,
        status: str,
        missing_precondition: list[str] | None,
        alternatives_or_notes: str,
    ) -> None:
        assert direct_stock_stage in STAGE_ORDER, f"Invalid stage {direct_stock_stage}"
        assert binding_status in {
            "bound",
            "unbound_pre_stage1a",
            "unbound_stage1b",
            "unbound_stage2",
            "unbound_stage3",
        }, f"Invalid binding_status {binding_status}"
        target.append(
            {
                "index": len(target),
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
                "binding_status": binding_status,
                "status": status,
                "missing_precondition": missing_precondition,
                "alternatives_or_notes": alternatives_or_notes,
            }
        )

    def add(**kw: Any) -> None:
        add_entry(entries, **kw)

    def add_ext(**kw: Any) -> None:
        add_entry(extended, earliest_stage=None, **kw)

    # =========================================================================
    # PART A: Exact 118 Original Register Keys (1-to-1 key bijection preserved)
    # =========================================================================

    # --- 0..3: Stage-0 plan freeze obligations ---
    add(
        key="route.design",
        paper_clauses=["T2a", "T3", "Eq. (4)"],
        earliest_stage=0,
        direct_stock_stage="0",
        subject="WP-0046 direct-stock route specification (Stage 1a pure-stdlib, Stage 1b CPU torch, Stage 2 stock)",
        cut="stage0.plan_freeze",
        typ="structured_route_binding",
        expected={
            "route": "direct-stock",
            "creation_edge": "E_direct = J(e, S, i_base)",
            "application_image": "@base/python.exe",
            "application_image_sha256": BASE_PYTHON_SHA256,
            "interpreter_flags": ["-s", "-P", "-B", "-u"],
            "sibling_import_resolution_O2": {
                "stage1a": "Self-contained single-file stage1a_worker.py (zero sibling imports; checks 6 WP-0043 sibling files on disk by SHA-256 only)",
                "stage2": "Keep -P (safe_path=True) and hash-verify bound sibling modules before explicit loading via spec_from_file_location; documented alternative drops -P (-s -B -u) with explicit sys.path[0] == @source",
            },
            "venv_binding_mechanism_O3": {
                "primary": "e_launch.__PYVENV_LAUNCHER__ = '@venv/Scripts/python.exe' with pre-launch FILE_SHARE_READ guards on @venv/pyvenv.cfg and *.pth; e_child.__PYVENV_LAUNCHER__ == ABSENT",
                "verification_status": "prospective_stage1a_unverified_on_actual_stock_venv (Turn-1 synthetic stdlib check does not transfer under T1 Corollary)",
                "documented_fallback": "direct-stock-nosite: (-s, -P, -B, -u, -S) + validated explicit bootstrap inside worker",
                "rejected_option": "PYTHONPATH to @venv/Lib/site-packages (skips .pth, leaves sys.prefix=@base)",
            },
            "supervision_layer_O1": "New separately authored, frozen, independently reviewed Stage-1a/1b/2 supervision and worker layer (worker43.py is NOT executed unchanged; model/OCR code remains untouched)",
            "intentional_differences_from_wp0043_venv": [
                "No venv redirector hop (direct CreateProcessW to @base/python.exe)",
                "New supervision/worker entries replacing worker43.py (admission/stdin/PPID/hardcoded paths)",
                "Explicit -s and -P flags added to (-B, -u) with explicit O2 sibling handling",
                "Supervisor uses _winapi.CreateProcess(0x08000006) + Job(0x2000|0x0200)",
                "sys.orig_argv[0] == @base/python.exe matches CreateProcessW argv[0] while sys.executable == @venv/Scripts/python.exe via __PYVENV_LAUNCHER__",
                "Stage 1a/1b set CUDA_VISIBLE_DEVICES='' and PATH='%SystemRoot%/System32;%SystemRoot%' (omitting @venv/Scripts)",
            ],
        },
        comparator="strict_typed_exact_plus_reviewed_mapping",
        evidence_source="eld-owner-probe Stage-0 proposal-r1 + eld-rd-reviewer independent audit",
        evidence_locator="docs/research/WP-0046/proposal-r1.md#route-selection",
        historical_reference="docs/coordination/WP-0043/plan-canonical.json; docs/agent-reports/eld-owner-probe/WP-0045/002_2026-11-27_research_eld-owner-probe.md",
        binding_status="bound",
        status="bound_stage0_r1_pending_review",
        missing_precondition=[
            "Independent eld-rd-reviewer review (Rev_0/Rev_1a) of r1 proposal and O2/O3 primary vs alternative choices"
        ],
        alternatives_or_notes="Incorporates Claude O1, O2, O3 and T3 sharpening witness (reported orig_argv[0] cannot separate venv from direct-stock; only Eq. 4 creation join can).",
    )
    add(
        key="writer.scope",
        paper_clauses=["T3", "T3a", "Eq. (5)"],
        earliest_stage=0,
        direct_stock_stage="0",
        subject="Cooperative ordinary-user trust model, allowed writers, outer handle-holder placement (O7), and T3a evaluation (M3)",
        cut="stage0.plan_freeze",
        typ="trust_and_writer_set",
        expected={
            "privilege_model": {"integrity_rid": 8192, "elevated": 0, "effective_admin": False},
            "trusted_roles": ["outer_recorder_scorer", "direct_supervisor", "stock_or_rehearsal_worker"],
            "allowed_writers_per_member_role": {
                "worker_produced_members": ["bound_worker_instance_only"],
                "supervisor_receipts": ["bound_supervisor_instance_only"],
            },
            "handle_holder_placement_O7": "Cooperative worker creates each protected output with CREATE_NEW|FILE_SHARE_READ, flushes, duplicates a FILE_GENERIC_READ view before closing the sole writer handle, and hands off to outer direct_supervisor (DuplicateHandle pull before HMAC seal), which holds read views until outer_recorder_scorer pulls read views and verifies fresh OPEN_EXISTING|FILE_SHARE_READ-only opens.",
            "t3a_evaluation_M3": "Evaluate conjuncts [b(I)=b(E)], [b(R)=b(I)], ordered projection (when order-sensitive), unique physical objects, and per-member custody over I intersect E three-valuedly under M < U < P so detectable conflicts never hide behind U.",
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
        evidence_source="eld-owner-probe proposal-r1 + Stage-1a/1b/2 Win32 handle/token receipts",
        evidence_locator="docs/research/WP-0046/proposal-r1.md#trust-writer-and-continuity",
        historical_reference="docs/coordination/WP-0045/disposition.json#/direct_launch",
        binding_status="bound",
        status="bound_stage0_r1_pending_review",
        missing_precondition=["Independent eld-rd-reviewer review of r1 custody design"],
        alternatives_or_notes="Resolves O7 (worker43.py closes files before path-hashing, leaving continuity structurally U) and adopts M3 conjunct-wise evaluation including I3, I5, I6a/b.",
    )
    add(
        key="module.coverage",
        paper_clauses=["T2", "T2a", "T8"],
        earliest_stage=0,
        direct_stock_stage="0",
        subject="Declared Python module and Windows DLL import coverage partitioned across Stage 1a, Stage 1b, and Stage 2",
        cut="stage0.plan_freeze",
        typ="typed_coverage_schema",
        expected={
            "stage1a_pure_stdlib_pre_torch": {
                "torch_imported": False,
                "allowed_python_roots": ["@base/Lib", "@base/DLLs", "@source", "built-in", "frozen"],
                "sys_path_must_contain": ["@venv/Lib/site-packages"],
                "sys_path_must_exclude": ["@base/Lib/site-packages", "user_site"],
                "closed_distribution_count": 33,
                "required_absent_specs": preflight05["installed"]["forbidden_absent_find_spec_none"],
                "disk_verified_runtime_files_5": {
                    **source41["versions"]["runtime_source_sha256"],
                    **ACTIVE_RUNTIME_SHA256,
                },
                "disk_verified_local_closure_6": {
                    m: device43["worktree_executables"][m]["git_source_sha256"]
                    for m in LOCAL_CLOSURE_MODULES
                },
            },
            "stage1b_cpu_torch_and_dlls": {
                "gated_on": "Stage 1a pass (V^(1a) = P) + independent review + separate release",
                "explicit_packages": [
                    "numpy", "PIL", "pypdfium2", "psutil", "safetensors",
                    "tokenizers", "huggingface_hub", "transformers", "torch", "torchvision",
                ],
                "allowed_python_roots": ["@venv/Lib/site-packages", "@base/Lib", "@base/DLLs", "@source", "built-in", "frozen"],
                "forbidden_python_roots": ["@base/Lib/site-packages", "user_site"],
                "dll_coverage": "all LOAD_DLL_DEBUG_EVENT modules under @venv or @base (including python312.dll, c10.dll, torch_cpu.dll, cudart64_13.dll if loaded)",
                "cuda_calls_allowed": 0,
            },
            "stage2_additional_dynamic_modules": sorted(
                source41["historical_q0_imported_module_receipt_and_disk"].keys()
            ),
            "declared_unobservable_backend_properties": [
                "proprietary_cuda_cublas_cudnn_internal_kernel_dispatch_and_sass",
                "wddm_per_process_vram_attribution",
            ],
        },
        comparator="typed_schema_and_root_containment",
        evidence_source="Stage-0 r1 coverage manifest + Stage-1a metadata/path receipts + Stage-1b sys.modules/LOAD_DLL_DEBUG_EVENT receipts",
        evidence_locator="docs/research/WP-0046/proposal-r1.md#site-pth-and-dll-origin-mapping",
        historical_reference="docs/research/WP-0041/source.json; docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/checks/03-pip-check-and-venv-inventory.json; docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/checks/05-preflight-cpu.json; docs/research/WP-0043/native.py",
        binding_status="bound",
        status="bound_stage0_r1_pending_review",
        missing_precondition=["Independent eld-rd-reviewer review of Stage 1a / Stage 1b split"],
        alternatives_or_notes="Adopts Claude O6 Stage-1a pre-torch boundary and enriches with Git-verified Q0 3-module forbidden list (flash_attn, xformers, triton), 33-dist closed inventory, and 6-module AST-verified local closure (including transfer.py).",
    )
    add(
        key="limits",
        paper_clauses=["T8", "T8a", "Eq. (12)"],
        earliest_stage=0,
        direct_stock_stage="0",
        subject="Per-stage resource ceilings, units, timeouts, and release ownership (Stage 1a, Stage 1b, Stage 2)",
        cut="stage0.pre_admission",
        typ="resource_plan",
        expected={
            "release_owner": "eld-coordinator (01a20a53-eec1-72c1-864c-9f8be8f4aff5)",
            "stage1a_pure_stdlib_ceilings": {
                "scheduled_units": 5,
                "decisive_units": 2,
                "control_units": 3,
                "retries": 0,
                "wall_s": 300,
                "preflight_hash_s": 240,
                "per_unit_s": 60,
                "host_job_commit_bytes": 512 * (1 << 20),
                "output_bytes": 32 * (1 << 20),
                "log_bytes": 4 * (1 << 20),
                "files": 128,
                "disk_free_initial_bytes": 2 * (1 << 30),
                "disk_free_during_bytes": 1 * (1 << 30),
                "gpu_leases": 0,
                "cuda_calls": 0,
                "torch_imports": 0,
            },
            "stage1b_cpu_torch_ceilings": {
                "scheduled_units": 2,
                "retries": 0,
                "wall_s": 360,
                "per_unit_s": 120,
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
        evidence_source="Stage-0 proposal-r1 ceilings + future coordinator release records",
        evidence_locator="docs/research/WP-0046/proposal-r1.md#resource-ceilings-and-scheduling",
        historical_reference="docs/coordination/WP-0043/plan-canonical.json#/limits",
        binding_status="bound",
        status="bound_stage0_r1_pending_review",
        missing_precondition=[
            "Separate coordinator release required before Stage-1a execution",
            "Separate coordinator release required before Stage-1b execution",
            "Fresh host headroom and Stage-2 GPU lease/ceilings must be bound separately before Stage-2 admission",
        ],
        alternatives_or_notes="Splits Turn-1 single Stage-1 ceilings into 512 MiB Stage 1a (5 units, 0 torch) and 4 GiB Stage 1b (2 units, CPU torch). Preserves Git plan-canonical.json (6573 B) vs bundle plan43.json (6574 B) distinction.",
    )

    # --- 4: Stage-1a CPU route rehearsal ---
    add(
        key="cpu.route_rehearsal",
        paper_clauses=["T2a", "T3", "T3a", "Eq. (4)", "Eq. (5)"],
        earliest_stage=1,
        direct_stock_stage="1a",
        subject="Stage-1a 5-unit pure-stdlib direct-stock rehearsal (2 decisive arms + 3 live controls)",
        cut="stage1a.process_creation_and_direct_read",
        typ="joined_event_and_custody",
        expected={
            "decisive_units": ["u01-direct-stock", "u02-direct-stock"],
            "control_units": [
                {"id": "c01-isolated-start", "expected_verdict": "M", "challenge_ref": "S1"},
                {"id": "c02-dropped-flags", "expected_verdict": "U", "challenge_ref": "S3"},
                {"id": "c03-omitted-member", "expected_verdict": "M", "challenge_ref": "I1"},
            ],
            "distinct_process_instances": True,
            "distinct_original_objects": True,
            "creation_predicate": "E_direct = J(e, S, i_base) with CompareObjectHandles(hProcess_returned, hProcess_event) == True",
            "image_sha256": BASE_PYTHON_SHA256,
            "job_flags_required": ["JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE (0x2000)", "JOB_OBJECT_LIMIT_JOB_MEMORY (0x0200)"],
            "member_custody": "B_m (Eq. 5) with FILE_SHARE_READ-only continuous read-view chain worker -> supervisor -> scorer",
            "zero_torch_cuda_or_model_load": True,
            "reporting_rule": "Report P, M, U counts over 5 scheduled units and list unattempted units separately.",
        },
        comparator="event_join_plus_continuous_handle_custody",
        evidence_source="Future Stage-1a outer recorder, direct supervisor, pure-stdlib worker, and independent offline scorer",
        evidence_locator="prospective:@arm/child-call.json; prospective:@arm/scorer.json",
        historical_reference="docs/coordination/WP-0045/windows-check.json",
        binding_status="bound",
        status="prospective_stage1a_bound",
        missing_precondition=[
            "Stage-1a probe source must be implemented, frozen, hashed (cpu.entry.stage1a_source_pin), and independently reviewed (Rev_1a)",
            "Separate coordinator Stage-1a release required",
        ],
        alternatives_or_notes="Adopts Claude §7 5-unit discriminating design (2 decisive + 3 live controls) stopping strictly before import torch.",
    )

    # --- 5: static.model_revision ---
    add(
        key="static.model_revision",
        paper_clauses=["T1", "T2"],
        earliest_stage=1,
        direct_stock_stage="1a",
        subject="Pinned unmodified Q0 model revision identifier",
        cut="stage1a.cut1s_static_preflight",
        typ="str",
        expected={
            "value": inputs43["pinned_model_revision"],
            "reference_locator": "docs/coordination/WP-0043/native-inputs.json#/pinned_model_revision",
        },
        comparator="strict_typed_exact",
        evidence_source="Stage-1a read-only supervisor preflight manifest check",
        evidence_locator="prospective:@run_root/preflight.json#/pinned_model_revision",
        historical_reference="docs/coordination/WP-0043/native-inputs.json#/pinned_model_revision",
        binding_status="bound",
        status="prospective_stage1a_bound",
        missing_precondition=["Stage-1a preflight execution against local @model directory"],
        alternatives_or_notes="Matches source41.json#/model (0480966938291445591f69f08a13b041c073a96a) and plan-canonical.json#/model_revision.",
    )

    # --- 6..23: 18 static.model.* digests ---
    for fname, rec in inputs43["model_objects_read_via_sha256"].items():
        add(
            key=f"static.model.{fname}",
            paper_clauses=["T1", "T2"],
            earliest_stage=1,
            direct_stock_stage="1a",
            subject=f"Static disk artifact @model/{fname}",
            cut="stage1a.cut1s_static_preflight",
            typ="sha256_and_byte_length",
            expected={
                "sha256": rec["sha256"],
                "bytes": rec["bytes"],
                "reference_locator": f"docs/coordination/WP-0043/native-inputs.json#/model_objects_read_via_sha256/{fname}",
            },
            comparator="sha256_and_exact_byte_length",
            evidence_source="Stage-1a supervisor read-only streaming 8 MiB SHA-256 preflight (no model import/load)",
            evidence_locator=f"prospective:@run_root/preflight.json#/model_files/{fname}",
            historical_reference=f"docs/coordination/WP-0043/native-inputs.json#/model_objects_read_via_sha256/{fname}",
            binding_status="bound",
            status="prospective_stage1a_bound",
            missing_precondition=["Stage-1a read-only preflight execution on local @model directory"],
            alternatives_or_notes="Static byte equality on disk establishes immutable file bytes only (Theorem 1 H1/H2); live loaded identity is exec.loaded at Stage 2.",
        )

    # --- 24..55: 32 static.dist.* versions + exact wheel SHA-256 pins ---
    for dist_name, version in source41["versions"]["verified_pinned_distributions"].items():
        wrec = wmap[normalize_pep503(dist_name)]
        add(
            key=f"static.dist.{dist_name}",
            paper_clauses=["T1", "T2", "T2a"],
            earliest_stage=1,
            direct_stock_stage="1a",
            subject=f"Pinned distribution {dist_name} in @venv and @wheelhouse",
            cut="stage1a.cut1s_wheel_and_cut1a_metadata",
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
            evidence_source="Stage-1a Cut 1S wheelhouse SHA-256 check + Stage-1a pure-stdlib child importlib.metadata.version() inside direct-stock @venv",
            evidence_locator=f"prospective:@arm/cut1a-metadata.json#/distributions/{dist_name}",
            historical_reference="docs/research/WP-0041/source.json#/versions/verified_pinned_distributions; docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/checks/02-verify-wheelhouse.json",
            binding_status="bound",
            status="prospective_stage1a_bound",
            missing_precondition=["Stage-1a preflight and pure-stdlib child metadata check"],
            alternatives_or_notes="Paired with extended obligations static.dist.pip (25.0.1), static.dist.closed_set_33, and static.dist.{triton,flash_attn,xformers}=ABSENT (closing O5).",
        )

    # --- 56..57: 2 static.input.* development PDFs ---
    for fam, entry in inputs43["development_inputs"].items():
        add(
            key=f"static.input.{fam}",
            paper_clauses=["T1", "T2"],
            earliest_stage=1,
            direct_stock_stage="1a",
            subject=f"Pinned development PDF fixture {fam} ({entry['path']})",
            cut="stage1a.cut1s_static_preflight",
            typ="pdf_sha256_and_git_blob",
            expected={
                "path": entry["path"],
                "git_blob": entry["git_blob"],
                "sha256": entry["verified_pdf_sha256"],
                "historical_rgb_pins_reference": entry["historical_rgb_pins"],
                "reference_locator": f"docs/coordination/WP-0043/native-inputs.json#/development_inputs/{fam}",
            },
            comparator="sha256_and_git_blob_exact",
            evidence_source="Stage-1a supervisor read-only Git blob / PDF digest verification",
            evidence_locator=f"prospective:@run_root/preflight.json#/development_inputs/{fam}",
            historical_reference=f"docs/coordination/WP-0043/native-inputs.json#/development_inputs/{fam}",
            binding_status="bound",
            status="prospective_stage1a_bound",
            missing_precondition=["Stage-1a read-only preflight execution"],
            alternatives_or_notes="Live RGB rendering with pypdfium2 + pillow stays at Stage 2 (exec.inputs).",
        )

    # --- 58..69: Stage-2 execution creation, config, env, loaded, backend, device, inputs ---
    add(
        key="exec.creator",
        paper_clauses=["T3", "Eq. (4)"],
        earliest_stage=2,
        direct_stock_stage="2",
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
        binding_status="unbound_stage2",
        status="prospective_stage2_requires_decision",
        missing_precondition=[
            "Passing Stage-1a and Stage-1b CPU qualification (V_preflight = P) and [proj(Pi_1) = proj(P_2)] bridge",
            "Decision on keeping DEBUG_ONLY_THIS_PROCESS attached vs clean DebugActiveProcessStop after startup/import cut during CUDA execution",
            "Freeze Stage-2 supervisor/worker entry source pin",
            "Separate Stage-2 coordinator release and sole GPU lease",
        ],
        alternatives_or_notes="Replaces worker43.py subprocess.Popen + Toolhelp snapshot; resolves WP-0043 historical M on argv[0] and T3 reported-argv ambiguity.",
    )
    add(
        key="exec.configuration",
        paper_clauses=["T2", "T2a", "T4"],
        earliest_stage=2,
        direct_stock_stage="2",
        subject="Stage-2 stock worker startup configuration (untouched and observed arms)",
        cut="stage2.before_model_imports",
        typ="typed_startup_vector",
        expected={
            "python_version": source41["python"],
            "orig_argv_prefix": ["@base/python.exe", "-s", "-P", "-B", "-u", "@source/stage2_stock_worker.py", "_worker"],
            "sys_executable": "@venv/Scripts/python.exe",
            "sys_base_executable": "@base/python.exe",
            "sys_prefix": "@venv",
            "sys_exec_prefix": "@venv",
            "sys_base_prefix": "@base",
            "sys_flags_derived_absolute": {
                "isolated": 0,
                "ignore_environment": 0,
                "hash_randomization": 0,
                "no_site": 0,
                "no_user_site": 1,
                "dont_write_bytecode": 1,
                "safe_path": True,
                "utf8_mode": 1,
            },
            "comparator_provenance": "derived_absolute_expectation_not_historically_observed",
            "site_loaded": True,
            "base_site_packages_in_sys_path": False,
            "venv_site_packages_in_sys_path": True,
            "sitecustomize_present": False,
            "usercustomize_present": False,
            "pyvenv_cfg_include_system_site_packages": "false",
        },
        comparator="strict_typed_ordered_equality",
        evidence_source="Stage-2 stock worker startup receipt before model/torch import",
        evidence_locator="prospective:@arm/runtime-startup.json",
        historical_reference="docs/coordination/WP-0043/plan-canonical.json; docs/reviews/WP-0045/blind/prior-0.json",
        binding_status="unbound_stage2",
        status="prospective_stage2_requires_decision",
        missing_precondition=[
            "Stage-1a verification of venv selection mechanism (O3), exact pyvenv.cfg digest, and .pth list on host @venv",
            "Freeze exact Stage-2 worker entry filename, O2 sibling policy, and digest before Stage-2 admission",
        ],
        alternatives_or_notes="Explicitly labels sys.flags expectation as derived (from worker43.py L86-87 & L199), not historically observed (adopting Claude §3 T2a).",
    )

    # 60..65: 6 exec.env.* keys
    env_specs = [
        (
            "CUDA_VISIBLE_DEVICES",
            2,
            "2",
            {"state": "present", "value": plan43["uuid"]},
            "unbound_stage2",
            "prospective_stage2_requires_decision",
            ["Confirm live target GPU UUID at Stage-2 lease issue"],
            "Stage 1a/1b intentionally bind cpu.env.CUDA_VISIBLE_DEVICES = present('') to hide CUDA devices; Stage 2 binds the coordinator-leased GPU UUID.",
        ),
        (
            "CUDA_DEVICE_ORDER",
            2,
            "2",
            {"state": "present", "value": "PCI_BUS_ID"},
            "bound",
            "prospective_stage2_bound",
            ["Stage-2 coordinator release"],
            "Also checked identically as cpu.env.CUDA_DEVICE_ORDER = present('PCI_BUS_ID') at Stage 1a.",
        ),
        (
            "HF_HUB_OFFLINE",
            2,
            "1a",
            {"state": "present", "value": "1"},
            "bound",
            "prospective_stage1a_bound",
            ["Stage-1a startup receipt and Stage-2 worker startup receipt"],
            "Reconciled to Stage 1a (Q_offline) and re-verified at Stage 1b/2; part of the closed 31-key child allowlist (cpu.env.closed_allowlist_31).",
        ),
        (
            "TRANSFORMERS_OFFLINE",
            2,
            "1a",
            {"state": "present", "value": "1"},
            "bound",
            "prospective_stage1a_bound",
            ["Stage-1a startup receipt and Stage-2 worker startup receipt"],
            "Reconciled to Stage 1a (Q_offline) and re-verified at Stage 1b/2; part of the closed 31-key child allowlist.",
        ),
        (
            "PYTHONHASHSEED",
            2,
            "1a",
            {"state": "present", "value": "0"},
            "bound",
            "prospective_stage1a_bound",
            ["Stage-1a startup receipt and Stage-2 worker startup receipt"],
            "Reconciled to Stage 1a (Q_hash) and re-verified at Stage 1b/2; string alone is insufficient without sys.flags.ignore_environment==0 and hash_randomization==0.",
        ),
        (
            "PYTHONNOUSERSITE",
            2,
            "1a",
            {"state": "present", "value": "1"},
            "bound",
            "prospective_stage1a_bound",
            ["Stage-1a startup receipt and Stage-2 worker startup receipt"],
            "Reconciled to Stage 1a (paired with -s -> no_user_site==1) and re-verified at Stage 1b/2.",
        ),
    ]
    for env_key, orig_s, ds_s, exp_val, bstat, st, precond, note in env_specs:
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
                "closed_allowlist_ref": "extended:cpu.env.closed_allowlist_31 (exact 31 child keys; all unlisted keys ABSENT)",
            },
            comparator="tagged_presence_and_exact_string",
            evidence_source="Supervisor CreateProcessW lpEnvironment trace + child os.environ snapshot before imports",
            evidence_locator=f"prospective:@arm/runtime-startup.json#/environment/{env_key}",
            historical_reference="docs/research/WP-0043/native.py#L189-L202",
            binding_status=bstat,
            status=st,
            missing_precondition=precond,
            alternatives_or_notes=note,
        )

    add(
        key="exec.loaded",
        paper_clauses=["T1", "T2", "T2a"],
        earliest_stage=2,
        direct_stock_stage="2",
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
            "forbidden_specs_absent": preflight05["installed"]["forbidden_absent_find_spec_none"],
        },
        comparator="live_instance_origin_root_and_sha256",
        evidence_source="Stage-2 worker post-load runtime.json + sys.modules + LOAD_DLL_DEBUG_EVENT receipts",
        evidence_locator="prospective:@arm/runtime.json#/modules",
        historical_reference="docs/coordination/WP-0043/native-inputs.json; docs/research/WP-0041/source.json#/historical_q0_imported_module_receipt_and_disk; docs/research/WP-0043/native.py#L347-L366",
        binding_status="bound",
        status="prospective_stage2_bound",
        missing_precondition=["Stage-2 execution and live loaded-object/DLL verification"],
        alternatives_or_notes="Joins live sys.modules[name].__file__ and OS DLL handles rather than pre-import disk paths alone.",
    )
    add(
        key="exec.backend",
        paper_clauses=["T2", "T6", "T8"],
        earliest_stage=2,
        direct_stock_stage="2",
        subject="Stage-2 stock PyTorch/CUDA numerical, determinism (M4), and execution backend state",
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
            "unbound_globally_in_public_git_e43af2e2": {
                "driver_version": {"historical_reference": device43["driver_version"], "status": "reobserve_and_freeze_pre_stage2"},
                "deterministic_algorithms": {"public_git_e43af2e2_value": "absent_globally", "status": "bind_before_stage2_review_M4"},
                "matmul_allow_tf32": {"public_git_e43af2e2_value": "absent_globally", "status": "bind_before_stage2_review"},
                "cudnn_allow_tf32": {"public_git_e43af2e2_value": "absent_globally", "status": "bind_before_stage2_review"},
            },
            "unobservable_declared": ["low_level_cublas_cudnn_kernel_selection", "unverified_bitwise_kernel_determinism_without_repeat_runs"],
        },
        comparator="typed_field_equality_plus_arm_parity",
        evidence_source="Stage-2 worker runtime.json (both arms) + nvidia-smi driver query (+ optional Stage-1b CPU readability probe)",
        evidence_locator="prospective:@arm/runtime.json",
        historical_reference="docs/coordination/WP-0043/device-release.json#/driver_version; docs/research/WP-0043/native.py#L362-L366; docs/research/WP-0043/native_validation.py#L148",
        binding_status="unbound_stage2",
        status="prospective_stage2_requires_decision",
        missing_precondition=[
            "Verified globally absent from public Git e43af2e2: coordinator/reviewer must inspect private WP-0043 runtime.json or explicitly freeze deterministic/tf32/cudnn_tf32 values before Stage-2 admission",
            "Re-observe and freeze live NVIDIA driver_version at Stage-2 lease issue",
            "Bind determinism assumption/policy per M4 before Stage-3 H3 claims",
        ],
        alternatives_or_notes="Read-only Git grep at e43af2e2 confirmed no public artifact records WP-0043's historical deterministic/tf32/cudnn_tf32 booleans (native_validation.py L148 checked key presence only; native_score.py L88 checked arm-to-arm equality only).",
    )
    add(
        key="exec.device",
        paper_clauses=["T2", "T8"],
        earliest_stage=2,
        direct_stock_stage="2",
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
        binding_status="unbound_stage2",
        status="prospective_stage2_requires_decision",
        missing_precondition=[
            "Fresh sole GPU lease, live UUID confirmation, and allowed_resident_pids census from eld-coordinator",
        ],
        alternatives_or_notes="Stage 1a and Stage 1b explicitly prohibit any CUDA device query or GPU lease.",
    )
    add(
        key="exec.inputs",
        paper_clauses=["T2", "T3"],
        earliest_stage=2,
        direct_stock_stage="2",
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
        binding_status="bound",
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
            direct_stock_stage="2",
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
            binding_status="bound",
            status="prospective_stage2_bound",
            missing_precondition=["Stage-2 execution and independent agreement on model.infer vs infer_multi cut reconciliation (S-04)"],
            alternatives_or_notes=(
                "RECONCILES STATIC CONFLICT (S-04): plan43.json and bundle/register.json name cut 'native infer_multi argument binding', whereas actual worker43.py L377 invokes model.infer(..., image_file=list(pages), return_dict=True, **kwargs) directly because infer_multi discards token_ids and finish_reason (per WP-0042/source-cuts.md L20)."
                + (" JSON null is a concrete present typed value, distinct from ABSENT or unobserved." if opt_val is None else "")
            ),
        )

    # --- 86..88: exec.fixture_options, exec.schedule, exec.original ---
    add(
        key="exec.fixture_options",
        paper_clauses=["T2"],
        earliest_stage=2,
        direct_stock_stage="2",
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
        binding_status="bound",
        status="prospective_stage2_bound",
        missing_precondition=["Stage-2 execution"],
        alternatives_or_notes="Exact match to worker43.py L373-L374 and Q0 protocol rules.",
    )
    add(
        key="exec.schedule",
        paper_clauses=["T2", "T6", "T8a"],
        earliest_stage=2,
        direct_stock_stage="2",
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
        binding_status="bound",
        status="prospective_stage2_bound",
        missing_precondition=["Stage-2 execution under sole GPU lease"],
        alternatives_or_notes="Historical F07.warm1 content matched 1/1 in WP-0043, while formal pair qualification remained 0/1 due to runtime argv[0] M.",
    )
    add(
        key="exec.original",
        paper_clauses=["T3", "T3a", "Eq. (5)"],
        earliest_stage=2,
        direct_stock_stage="2",
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
        evidence_source="Stage-2 cooperative worker/supervisor/scorer custody receipts (O7; partitioned from continuity and inventory completeness per O8)",
        evidence_locator="prospective:@run_root/custody-receipt.json",
        historical_reference="docs/coordination/WP-0045/windows-check.json; docs/coordination/WP-0045/disposition.json",
        binding_status="bound",
        status="prospective_stage2_bound",
        missing_precondition=["Implement multi-member cooperative handle-guard writer/supervisor/scorer before Stage-2 freeze"],
        alternatives_or_notes="Non-overlapping partition (O8): exec.original owns W_m/boundWrite/seal/endpoint-join; exec.original_continuity owns continuous(m) handle-interval; exec.stock_inventory owns B_arm multiset/uniqueness/order completeness.",
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
                direct_stock_stage="2",
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
                    "expected_masks_on_f07_prefix": {
                        "D1_rep_banned": [],
                        "D1_derivation_scope": "Not derivable from standalone ZIP alone (no-repeat history omitted); independently verified D1=[] across 2935 34-gram starts in pinned Git e43af2e2 F07.warm1.token_ids.json (sha256 532ffea05870c45189f473d1cb16ded1d26c583f07737e1462ac325ecdae5982)",
                        "D2_page_banned": [1],
                    },
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
                binding_status="bound",
                status="prospective_stage2_bound",
                missing_precondition=[
                    "Fix WP-0043/scorer.py L304 cumulative-mask bug (must use phase-local D_2 against supplied C1_post_rep, per Theorem 3)",
                    "Stage-2 observed stock execution",
                ],
                alternatives_or_notes="Offset 1174/1238/1282 binds strictly to CPython 3.12.10 + modeling_unlimitedocr.py sha256 f6df813c.... Archive SHA-256 is reference only.",
            )

    # --- 104: native.snapshot ---
    add(
        key="native.snapshot",
        paper_clauses=["T6", "T8a", "Eq. (9)"],
        earliest_stage=2,
        direct_stock_stage="2",
        subject="Five F07.warm1 observed stock rows (positions 1445..1449) at declared B and D cuts",
        cut="stage2.declared_B_and_D_cuts",
        typ="restorable_state_snapshot_schema",
        expected={
            "rows": [0, 1, 2, 3, 4],
            "positions": [1445, 1446, 1447, 1448, 1449],
            "entry_layer11_cache_lengths": [1445, 1446, 1447, 1448, 1449],
            "exit_layer11_cache_lengths": [1446, 1447, 1448, 1449, 1450],
            "determinism_premise_M4": "Eq. (9) factorization requires deterministic F given s (or trace-indexed Y_F(s, omega)); bitwise run-to-run determinism is unmeasured historically",
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
        binding_status="bound",
        status="prospective_stage2_bound",
        missing_precondition=[
            "Add attention_result, pre-sanitization router x, and valid bias to Stage-2 scorer finiteness list (omitted in WP-0043 native_score.py L532-533)",
            "Stage-2 execution and independent schema/restorability verification",
        ],
        alternatives_or_notes="Checking finiteness and schema establishes restorable(t) only; actual replay parity Y_F(R(C(s))) = Y_F(s) remains Stage 3 (private.parity).",
    )

    # --- 105: private.parity ---
    add(
        key="private.parity",
        paper_clauses=["T6", "T8a", "Eq. (9)", "Eq. (12)"],
        earliest_stage=3,
        direct_stock_stage="3",
        subject="Stage-3 anchored and linked private replay branches on F07.warm1 positions 1445..1449",
        cut="stage3.anchored_trials_and_linked_bridges",
        typ="private_replay_trace_equivalence",
        expected={
            "equivalence_predicate": "forall s in S_test: Y_F(R(C(s))) == Y_F(s) under explicit determinism premise M4",
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
        binding_status="unbound_stage3",
        status="prospective_stage3_deferred",
        missing_precondition=[
            "Passing Stage-2 stock run r with V_stock(r) == P and J_5(r, R_cand) == True",
            "Complete Stage-3 private plan Plan_3 and independent review Rev_3",
            "Separate Stage-3 coordinator release",
        ],
        alternatives_or_notes="Deferred visibly in deferred_unbound (B_T \\ Pi_s) at Stages 0, 1a, 1b, 2 per amended Eq. (11) (M1 / M-08).",
    )

    # --- 106..117: 12 Revision-1 amendment obligations ---
    add(
        key="plan.static_consistency",
        paper_clauses=["T8", "Eq. (11)", "ASSESS()"],
        earliest_stage=0,
        direct_stock_stage="0",
        subject="Complete Stage-0/1a/1b/2/3 proposal manifest under scoped plan Pi_s (M1 / M-08)",
        cut="stage0.static_manifest_validation",
        typ="static_intersection_consistency",
        expected={
            "amended_eq11": "V^(s) = V(X_static(all) union X_due^(s), (B_T intersect Pi_s) union U_due^(s)); report Def_s = {k: d_k > s} and deferred_unbound = B_T \\ Pi_s visibly",
            "prose_relation_audit": "Original bundle/register.json had 5 bind_before_review + 36 prose relation rows = 41 rows lacking typed machine-checkable bindings; r1 replaces all prose stubs with typed predicates and tracks B_T intersect Pi_s explicitly per stage.",
            "reconciled_conflicts": [
                "plan43 infer_multi vs worker43 model.infer resolved to model.infer(..., image_file=list(pages), return_dict=True)",
                "plan43 venv argv[0] vs direct-stock @base/python.exe argv[0] resolved via direct-stock route contract",
                "WP-0045 OMP/MKL/OPENBLAS_NUM_THREADS='1' vs worker43 ABSENT resolved to ABSENT",
            ],
        },
        comparator="static_intersection_nonempty_before_deferral",
        evidence_source="Offline Stage-0 static consistency checker (controls_r1.py) + independent review",
        evidence_locator="docs/research/WP-0046/controls_r1.py#eval_record_claude",
        historical_reference="Paper I T8 p. 11 (reviewed revision 1); docs/research/WP-0046/corrigenda-r1.md#M1",
        binding_status="bound",
        status="bound_stage0_r1_pending_review",
        missing_precondition=["Independent eld-rd-reviewer verification of scoped counts Pi_0..Pi_3"],
        alternatives_or_notes="Resolves both Claude M1 (A2a/A2b) and Gemini M-08 (Eq. 11 vs ASSESS contradiction).",
    )
    add(
        key="cpu.hash_effective",
        paper_clauses=["T2a", "Eq. (7)"],
        earliest_stage=1,
        direct_stock_stage="1a",
        subject="Stage-1a direct-stock pure-stdlib worker effective startup flags and hash seed (derived absolute comparator)",
        cut="stage1a.cut1a_startup",
        typ="effective_startup_flags_tuple",
        expected={
            "comparator_provenance": "derived_absolute_expectation_not_historically_observed (derived from worker43.py L86-87 -B -u and L199 PYTHONHASHSEED=0, PYTHONUTF8=1; historical flags were unobserved in prior0.json and worker43.py L362)",
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
        evidence_source="Stage-1a worker startup receipt (sys.flags + os.environ) joined to supervisor lpEnvironment",
        evidence_locator="prospective:@arm/cut1a-startup.json#/flags",
        historical_reference="Paper I T2a p. 4 (reviewed revision 1); docs/reviews/WP-0045/blind/prior-0.json; docs/research/WP-0043/native.py#L86-L87,L199",
        binding_status="bound",
        status="prospective_stage1a_bound",
        missing_precondition=["Stage-1a execution"],
        alternatives_or_notes="Adopts Claude §3 T2a derived-expectation correction (relational comparison against unobserved historical flags would return unobserved under Eq. 6).",
    )
    add(
        key="cpu.import_resolution",
        paper_clauses=["T2a", "T1"],
        earliest_stage=1,
        direct_stock_stage="1a",
        subject="Stage-1a pure-stdlib venv selection, sys.path, .pth, sitecustomize, 33 distributions, 3 forbidden absent modules, and 5 runtime file digests",
        cut="stage1a.cut1a_startup_and_metadata",
        typ="import_and_path_resolution_map",
        expected={
            "venv_activation_hypothesis_O3": "e_launch.__PYVENV_LAUNCHER__ == present('@venv/Scripts/python.exe') and e_child.__PYVENV_LAUNCHER__ == absent (prospective_stage1a_unverified_on_actual_stock_venv)",
            "sys_executable": "@venv/Scripts/python.exe",
            "sys_orig_argv0": "@base/python.exe",
            "sys_prefix_and_exec_prefix": "@venv",
            "sys_base_prefix": "@base",
            "pyvenv_cfg_include_system_site_packages": "false",
            "base_site_packages_excluded": True,
            "venv_site_packages_included": True,
            "sitecustomize_and_usercustomize_absent": True,
            "closed_33_distributions_verified": True,
            "forbidden_specs_absent": preflight05["installed"]["forbidden_absent_find_spec_none"],
            "pinned_runtime_files_5_sha256": {
                **source41["versions"]["runtime_source_sha256"],
                **ACTIVE_RUNTIME_SHA256,
            },
            "torch_imported_in_stage1a": False,
            "stage1b_torch_and_dlls_ref": "extended:cpu.stage1b.torch_import_and_dlls",
        },
        comparator="ordered_path_root_containment_and_sha256",
        evidence_source="Stage-1a pure-stdlib child receipt + supervisor pre-launch pyvenv.cfg/.pth read-guards",
        evidence_locator="prospective:@arm/cut1a-metadata.json",
        historical_reference="Paper I T2a p. 4 (reviewed revision 1); docs/research/WP-0046/proposal-r1.md#site-pth-and-dll-origin-mapping",
        binding_status="bound",
        status="prospective_stage1a_bound",
        missing_precondition=[
            "Resolve static.venv.pyvenv_cfg & static.venv.pth_inventory policy before Stage-1a release",
            "Stage-1a execution; live torch/DLL loading deferred separately to Stage 1b (cpu.stage1b.torch_import_and_dlls)",
        ],
        alternatives_or_notes="Splits Turn-1 combined Cut 1A+1B cleanly into pure-stdlib Stage 1a (here) and CPU-only torch/DLL Stage 1b (extended:cpu.stage1b.torch_import_and_dlls).",
    )
    add(
        key="cpu.original_inventory",
        paper_clauses=["T3a", "Eq. (5)"],
        earliest_stage=1,
        direct_stock_stage="1a",
        subject="Stage-1a expected, sealed, and scorer-read member inventory per unit under M3 conjunct-wise evaluation",
        cut="stage1a.seal_through_scorer_read",
        typ="inventory_bijection_and_keyed_custody",
        expected={
            "expected_member_keys_per_unit": ["cut1a-startup.json", "cut1a-metadata.json", "rehearsal-payload.bin"],
            "unique_logical_keys": True,
            "unique_physical_objects": True,
            "ordered_projection_required": False,
            "auth_qr_required": True,
            "multiset_relations": "b(I_r) == b(E_r) and b(R_r) == b(I_r)",
            "keyed_member_custody": "forall k in (I_r intersect E_r): B_{m(k)} == P with FILE_SHARE_READ continuous handle overlap; evaluate conjuncts three-valuedly (M3)",
        },
        comparator="unique_key_multiset_equality_plus_keyed_Bm",
        evidence_source="Stage-1a frozen expected schema E_r, supervisor HMAC-sealed inventory I_r, and scorer fresh read list R_r",
        evidence_locator="prospective:@arm/scorer.json#/inventory",
        historical_reference="Paper I T3a p. 6 (reviewed revision 1); docs/research/WP-0046/controls_r1.py",
        binding_status="bound",
        status="prospective_stage1a_bound",
        missing_precondition=["Stage-1a probe implementation, freeze, review, and release"],
        alternatives_or_notes="Adopts M3 conjunct-wise evaluation fixing I3, I5, I6a/b, and ctrl_06 (M dominates U whenever any conjunct is demonstrably false).",
    )
    add(
        key="exec.original_continuity",
        paper_clauses=["T3", "T3a", "Eq. (5)"],
        earliest_stage=2,
        direct_stock_stage="2",
        subject="Continuous Windows NTFS read-only handle protection over every Stage-2 stock member (O7)",
        cut="stage2.seal_through_scorer_read",
        typ="handle_interval_continuity",
        expected={
            "interval_cover": "I_handle superset [t_seal, t_read] with overlapping worker -> supervisor -> scorer DuplicateHandle(FILE_GENERIC_READ) handoff before writer close",
            "writer_open": "CREATE_NEW, GENERIC_READ|GENERIC_WRITE, FILE_SHARE_READ, inherit=False",
            "scorer_open": "OPEN_EXISTING, GENERIC_READ, FILE_SHARE_READ (excludes FILE_SHARE_WRITE and FILE_SHARE_DELETE)",
            "corroborating_metadata": "volume_serial, file_index_or_file_id_128, nNumberOfLinks == 1, NTFS filesystem, unchanged byte length/sha256",
        },
        comparator="interval_cover_share_policy_and_object_id_exact",
        evidence_source="Stage-2 cooperative worker/supervisor/scorer Win32 handle lifecycle and QPC timestamps",
        evidence_locator="prospective:@run_root/continuity-trace.json",
        historical_reference="Paper I T3a p. 6 (reviewed revision 1); docs/research/WP-0045/stage.py; docs/research/WP-0045/win.py",
        binding_status="bound",
        status="prospective_stage2_bound",
        missing_precondition=["Multi-member cooperative handle-guard harness implementation for Stage-2 stock outputs (O7)"],
        alternatives_or_notes="Endpoint volume/file-ID equality alone without held-handle overlap leaves [t_seal, t_read] unobserved (U).",
    )
    add(
        key="exec.stock_inventory",
        paper_clauses=["T3a"],
        earliest_stage=2,
        direct_stock_stage="2",
        subject="Stage-2 stock arm expected vs sealed vs scorer-read member inventory (M3, O8)",
        cut="stage2.output_finalization_and_scoring",
        typ="inventory_bijection_and_keyed_custody",
        expected={
            "independent_schema_Fr": "Deterministic expansion E_r = F_r(q_r) over authenticated Stage-2 arms and 4-call schedule",
            "unique_logical_keys": True,
            "unique_physical_objects": True,
            "multiset_relations": "b(I_r) == b(E_r) and b(R_r) == b(I_r)",
            "ordering_check_projections": ["call_schedule_order (ordered=True -> I6a)", "append_journal_seq_order (ordered=True -> I6a)"],
            "keyed_member_custody": "forall k in (I_r intersect E_r): B_{m(k)} == P; evaluated three-valuedly (M3)",
        },
        comparator="unique_key_multiset_and_projection_order_exact",
        evidence_source="Stage-2 frozen schema E_r, HMAC-sealed inventory I_r, and read-only offline scorer read set R_r",
        evidence_locator="prospective:@run_root/outcome-inventory.json",
        historical_reference="Paper I T3a p. 6 (reviewed revision 1); docs/research/WP-0043/native_score.py#L393-L408",
        binding_status="bound",
        status="prospective_stage2_bound",
        missing_precondition=["Stage-2 execution and independent scorer verification"],
        alternatives_or_notes="Explicitly includes ordered-projection check (I6a/I6b) where order affects computation.",
    )
    add(
        key="native.support_choice",
        paper_clauses=["T5", "Eq. (8)", "Eq. (7)"],
        earliest_stage=2,
        direct_stock_stage="2",
        subject="Aggregate reference for Stage-2 F07.warm1 decoded score rows (positions 1445..1449); decomposed into 5 per-row keys (O8)",
        cut="stage2.decoded_score_row",
        typ="support_oob_and_winner_fault_sets",
        expected={
            "per_row_sub_atoms_O8": [f"native.{p}.support_choice" for p in range(1445, 1450)],
            "X_supp": "{supp : A == empty}",
            "X_oob_amended_vs_literal_P3": "Amended r1 evaluates X_oob = {emitted_outside_support : y_obs observed and y_obs not in A} unconditionally (per WP-0043/README.md L69); Paper I rev. 1 literal gates emission checks on clean = (X_0..2 union X_supp == empty). Both produce verdict M on P3; explicit mode flag preserves both readings.",
            "X_choice": "{choice : A nonempty and X_0..2 empty and y_obs observed and y_obs != min argmax_{j in A} value(z^2_j)}",
            "P7_resolved_reading_B": "Missing y_obs ALWAYS enters U = {emission} regardless of raw/rep/page/supp faults (convergent Reading B across both providers).",
            "signed_zero_rule": "-0.0 and +0.0 tie numerically (smallest ID wins) while bitwise word equality distinguishes 0x80000000 from 0x00000000",
        },
        comparator="fault_and_missing_set_exact_with_M_dominance",
        evidence_source="Stage-2 independent Phase-Local Eq. (8) scorer on observed F07.warm1 score triples",
        evidence_locator="prospective:@run_root/score-native.json#/rows",
        historical_reference="Paper I T5 p. 8 (reviewed revision 1); docs/research/WP-0046/controls_r1.py",
        binding_status="bound",
        status="prospective_stage2_bound",
        missing_precondition=["Update WP-0043 scorer to amended Eq. (8) + settle P3 X_oob reporting convention before Stage-2 freeze"],
        alternatives_or_notes="Resolves Claude O8 (5 per-row keys native.1445..1449.support_choice added in extended_obligations so minimal diagnostics retain row identity) and converges on P7 Reading B.",
    )
    add(
        key="native.storage",
        paper_clauses=["T6"],
        earliest_stage=2,
        direct_stock_stage="2",
        subject="Every captured tensor node in Stage-2 observed F07.warm1 snapshots",
        cut="stage2.stock_capture_tensor_serialization",
        typ="tensor_layout_capacity_and_device_bounds",
        expected={
            "required_metadata": [
                "dtype", "shape", "strides", "storage_offset", "storage_bytes",
                "element_size", "bytes", "device_index", "run_bound_device_uuid", "alias_class",
            ],
            "nonempty_bound": "all(n_i > 0) and all(s_i >= 0) and o >= 0 and b*(1 + o + sum((n_i - 1)*s_i)) <= B_storage (L1/L2)",
            "empty_view_convention_L3": "Outside Paper I rev. 1 nonempty domain (outside_domain in strict Paper I rev. 1); Stage-2/3 validator extends with 0 <= b * o <= B_storage when prod(n_i) == 0 (fixing WP-0043/transfer.py L15-16).",
            "writable_view_non_aliasing": "distinguish read-bound containment from intra-tensor write non-aliasing (zero/overlapping strides)",
        },
        comparator="exact_integer_bounds_and_device_join",
        evidence_source="Stage-2 observed arm tensors.bin node metadata + offline scorer",
        evidence_locator="prospective:@arm/observations.jsonl#tensor_nodes",
        historical_reference="Paper I T6 p. 9 (reviewed revision 1); docs/research/WP-0043/transfer.py#L11-L29",
        binding_status="bound",
        status="prospective_stage2_bound",
        missing_precondition=["Add empty-view offset check 0 <= b*o <= B_storage and run-bound device UUID to tensor validator before Stage-2 freeze"],
        alternatives_or_notes="Preserves both Paper I rev. 1 nonempty domain (Claude L3 -> outside_domain) and the Stage-2/3 empty-view offset extension (M-06).",
    )
    add(
        key="plan.loss_model",
        paper_clauses=["T7", "Eq. (10)"],
        earliest_stage=0,
        direct_stock_stage="0",
        subject="WP-0046 measurement-selection channel and erasure/loss assumptions (incorporating K3)",
        cut="stage0.measurement_design",
        typ="channel_and_loss_budget_declaration",
        expected={
            "stage1_channel_model": "non-informative identifiable erasures (missing witnesses -> U) over independent observation sources; coordinate erasure budget f = 0 (fail-closed: any missing mandatory receipt yields U)",
            "correlated_source_infeasibility_K3": "If one source carries both u and w on the p. 10 table, f=1 source failure is infeasible for every selection (erasing {u,w} leaves h0 and h3 indistinguishable on {v}). Correlated source-group constraints replace scalar 1+f coordinate counts whenever sources carry multiple coordinates.",
            "deterministic_loss_histories_distinguished": True,
            "infeasibility_rule": "Return explicit infeasible=True, min_cost=null, argmin=[] rather than crashing on min([])",
        },
        comparator="explicit_channel_and_budget_binding",
        evidence_source="Stage-0 proposal-r1 measurement-design declaration + offline T7 checks (controls_r1.py)",
        evidence_locator="docs/research/WP-0046/proposal-r1.md#measurement-and-loss-model",
        historical_reference="Paper I T7 p. 10 (reviewed revision 1); docs/research/WP-0046/corrigenda-r1.md#T7",
        binding_status="bound",
        status="bound_stage0_r1_pending_review",
        missing_precondition=None,
        alternatives_or_notes="Adopts Claude K3 correlated source-loss infeasibility witness explicitly.",
    )
    add(
        key="plan.diagnostics",
        paper_clauses=["T1", "T4", "Eq. (2)", "Eq. (6)", "Eq. (7)"],
        earliest_stage=0,
        direct_stock_stage="0",
        subject="Crosswalk comparator and full-record diagnostic aggregator across all WP-0046 stages (D1-D6, M-02, M-04)",
        cut="stage0.crosswalk_and_scorer_contract",
        typ="diagnostic_contract",
        expected={
            "eq6_precedence_first_matching_case": ["J_k == 0 -> incomparable", "J_k == ? or x == ? or y == ? -> unobserved", "type_error -> schema_mismatch", "eta_k(x) == eta_k(y) -> same", "otherwise -> different"],
            "tagged_values": "explicit state in {'present','absent','unobserved'}; JSON null is state='present', value=null; bool != int",
            "conflict_classes_preserved": ["M_field", "M_integrity", "M_static_plan"],
            "both_minimal_sets_returned": ["first_conflict = min_strict_prec(X)", "first_finding = min_strict_prec(X union U)"],
            "order_closure_and_integrity_D6": "Compute Warshall/DFS transitive closure over direct edges (fixing amendments.minimal on D6); reject reflexive or cyclic edges as M_integrity (order.integrity) rather than returning empty set.",
        },
        comparator="exact_precedence_and_minimal_set_equality",
        evidence_source="Stage-0 controls_r1.py + control_cases.json + peer challenges",
        evidence_locator="docs/research/WP-0046/controls_r1.py",
        historical_reference="Paper I T4 p. 7 (reviewed revision 1); docs/research/WP-0046/corrigenda-r1.md#T4",
        binding_status="bound",
        status="bound_stage0_r1_pending_review",
        missing_precondition=None,
        alternatives_or_notes="Incorporates Claude Eq. (6) 'first matching case' wording and D6 transitive closure alongside Gemini cycle M_integrity rejection and M_field/M_integrity separation.",
    )
    add(
        key="private.plan",
        paper_clauses=["T8", "T8a", "Eq. (12)"],
        earliest_stage=0,
        direct_stock_stage="3",
        subject="Stage-3 private replay specification Plan_3 (deferred out of Stage-0/1a/1b/2 scope Pi_s)",
        cut="stage3.pre_proposal_admission",
        typ="stage3_plan_gate",
        expected={
            "required_when_stage3_proposed": [
                "A1 branch selection and single atomic commit semantics",
                "eight keyed linked bridges",
                "expanded finiteness domain (attention_result, active pre-sanitization router x, valid bias)",
                "private alias isolation and pause-resume fencing",
                "protected source continuation to native EOS",
                "determinism premise M4 bound",
            ],
            "scoped_plan_status_M1": "Member of B_T \\ Pi_s (reported visibly in deferred_unbound) for s in {0, 1a, 1b, 2}; enters B_T intersect Pi_3 only when Stage 3 is proposed.",
        },
        comparator="stage_scoped_plan_completeness_and_static_consistency",
        evidence_source="Future Stage-3 proposal manifest Plan_3 and independent review Rev_3",
        evidence_locator="prospective:stage3_unreleased",
        historical_reference="Paper I T8a p. 12 (reviewed revision 1); docs/coordination/WP-0042/disposition.json",
        binding_status="unbound_stage3",
        status="prospective_stage3_deferred",
        missing_precondition=[
            "Not required for Stage-1a/1b CPU qualification or Stage-2 stock capture",
            "Required completely before Stage-3 proposal admission (considerPrivateReplay)",
        ],
        alternatives_or_notes="Resolves A2a/A2b contradiction between whole-plan ASSESS and Eq. (12).",
    )
    add(
        key="private.origin",
        paper_clauses=["T8a", "Eq. (12)"],
        earliest_stage=2,
        direct_stock_stage="2",
        subject="Qualification of five same-run restorable stock rows as candidate Stage-3 replay inputs (J1-J6)",
        cut="stage2.post_stock_qualification_gate",
        typ="same_run_five_row_bijection_gate",
        expected={
            "required_keys": [
                {"label": "F07.warm1", "arm": "observed", "position": p}
                for p in range(1445, 1450)
            ],
            "predicate": "exists r: V_stock(r) == 'P' and J_5(r, R_cand)",
            "J_5_clauses": [
                "unique 5-key bijection b(keys(R_cand)) == b(K) keyed on full 3-tuple (label, arm, position) — fixes amendments.eligible on J3/J4",
                "forall t in R_cand: run(t) == r",
                "forall t in R_cand: originalBound(r, t) == True",
                "forall t in R_cand: restorable(t) == True",
            ],
            "historical_wp0043_excluded": "WP-0043 joint M (0/1 pairs, 0/5 rows) cannot satisfy V_stock(r) == 'P'",
        },
        comparator="same_run_bijection_and_boolean_gate",
        evidence_source="Stage-2 passing stock run verdict V_stock(r) + offline replay-gate check (controls_r1.py)",
        evidence_locator="docs/research/WP-0046/controls_r1.py",
        historical_reference="Paper I T8a p. 12 (reviewed revision 1); docs/coordination/WP-0043/native-evidence.json",
        binding_status="bound",
        status="prospective_stage2_bound",
        missing_precondition=[
            "Completed Stage-2 stock run achieving V_stock(r) == 'P' on both untouched and observed arms",
        ],
        alternatives_or_notes="Rejects cross-run (J1), duplicate position (J2), wrong call label F07.warmup (J3), wrong arm untouched (J4), and unresolved Plan_3 (J6).",
    )

    # =========================================================================
    # PART B: 44 Extended Obligations Closing O4, O5, O6, O8, M1, M2
    # =========================================================================

    # --- O5: Static interpreter, venv config, runtime files, closed 33 dists, 3 forbidden absent, 32 wheels, 6 local closure ---
    add_ext(
        key="static.python.base_exe",
        paper_clauses=["T1", "T2", "T2a", "T3"],
        direct_stock_stage="1a",
        subject="Base CPython 3.12.10 interpreter executable @base/python.exe (central subject of direct-stock)",
        cut="stage1a.cut1s_static_preflight_and_creation",
        typ="sha256",
        expected={
            "sha256": BASE_PYTHON_SHA256,
            "cross_source_anchor": "source41.json#/python_sha256 == windows45.json#/observed_images_sha256",
        },
        comparator="sha256_exact",
        evidence_source="Stage-1a preflight read-guard hash + CREATE_PROCESS_DEBUG_EVENT hFile hash",
        evidence_locator="prospective:@run_root/preflight.json#/python/base_exe_sha256",
        historical_reference="docs/research/WP-0041/source.json#/python_sha256; docs/coordination/WP-0045/windows-check.json#/observed_images_sha256",
        binding_status="bound",
        status="prospective_stage1a_bound",
        missing_precondition=["Stage-1a execution"],
        alternatives_or_notes="Closes O5 gap: base Python digest was absent from bundle/register.json.",
    )
    add_ext(
        key="static.python.venv_launcher",
        paper_clauses=["T1", "T2", "T3"],
        direct_stock_stage="1a",
        subject="Q0 venv launcher executable @venv/Scripts/python.exe (verified on disk, NOT executed as redirector)",
        cut="stage1a.cut1s_static_preflight",
        typ="sha256",
        expected={"sha256": VENV_LAUNCHER_SHA256, "executed_as_redirector": False},
        comparator="sha256_exact",
        evidence_source="Stage-1a supervisor read-only file hash",
        evidence_locator="prospective:@run_root/preflight.json#/python/venv_launcher_sha256",
        historical_reference="docs/research/WP-0043/native.py#L125",
        binding_status="bound",
        status="prospective_stage1a_bound",
        missing_precondition=["Stage-1a execution"],
        alternatives_or_notes="Closes O5 gap: worker43.py L125 hardcoded digest was absent from bundle/register.json.",
    )
    add_ext(
        key="static.venv.pyvenv_cfg",
        paper_clauses=["T2a", "T8"],
        direct_stock_stage="1a",
        subject="Pinned Q0 @venv/pyvenv.cfg configuration file (semantic rule bound; exact byte digest unarchived in public Git e43af2e2)",
        cut="stage1a.cut1s_pre_launch_guard",
        typ="pyvenv_cfg_semantic_and_digest",
        expected={
            "semantic_bound": {"include-system-site-packages": "false", "version_prefix": "3.12.10"},
            "exact_byte_sha256": "UNBOUND_PRE_STAGE1A (absent from public Git e43af2e2; prior0.json L949 hash was WP-0044 synthetic runtime-v1, not Q0 @venv)",
        },
        comparator="semantic_parse_plus_pre_launch_read_guard_and_sha256",
        evidence_source="Stage-1a supervisor FILE_SHARE_READ pre-launch guard + coordinator pre-Stage-1a read-only pin or semantic binding decision",
        evidence_locator="prospective:@run_root/preflight.json#/venv/pyvenv_cfg",
        historical_reference="docs/reviews/WP-0045/blind/prior-0.json (non-Q0 synthetic contrast); qualification/q0/harness/evidence/004-gpu-trial/9e73ef86/07-runtime-root-inventory.json (no pyvenv.cfg hash archived)",
        binding_status="unbound_pre_stage1a",
        status="unbound_pre_stage1a_hold_item",
        missing_precondition=[
            "Coordinator must either pin Q0 @venv/pyvenv.cfg SHA-256 in the Stage-1a release manifest OR accept semantic validation (include-system-site-packages=false) at Stage 1a and freeze observed digest for Stage 1b/2"
        ],
        alternatives_or_notes="Verified globally absent from public Git e43af2e2; enters B_T intersect Pi_1a until dispositioned.",
    )
    add_ext(
        key="static.venv.pth_inventory",
        paper_clauses=["T2a", "T8"],
        direct_stock_stage="1a",
        subject="Exact set and SHA-256 digests of *.pth files under @venv/Lib/site-packages (unarchived in public Git e43af2e2)",
        cut="stage1a.cut1s_pre_launch_guard",
        typ="pth_inventory_and_read_guard",
        expected={
            "policy_bound": "Pre-launch FILE_SHARE_READ handles on every *.pth in @venv/Lib/site-packages; sitecustomize.py and usercustomize.py ABSENT in @venv and @base; zero unexpected executable .pth lines adding @base/Lib/site-packages or user-site",
            "expected_pth_list_sha256": "UNBOUND_PRE_STAGE1A (not archived in public Git e43af2e2)",
        },
        comparator="exact_inventory_and_sha256",
        evidence_source="Stage-1a supervisor pre-launch directory inventory + child effective_pth observation",
        evidence_locator="prospective:@run_root/preflight.json#/venv/pth_files",
        historical_reference="docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/checks/03-pip-check-and-venv-inventory.json (distributions only; no .pth manifest)",
        binding_status="unbound_pre_stage1a",
        status="unbound_pre_stage1a_hold_item",
        missing_precondition=[
            "Coordinator must either pin Q0 @venv/Lib/site-packages/*.pth inventory pre-Stage-1a OR authorize Stage-1a semantic audit + digest freeze for Stage 1b/2"
        ],
        alternatives_or_notes="Enters B_T intersect Pi_1a until dispositioned; alternatively eliminated from pre-script startup under documented -S fallback.",
    )

    runtime_5 = [
        ("static.runtime.transformers_cache_utils", "transformers/cache_utils.py", source41["versions"]["runtime_source_sha256"]["transformers/cache_utils.py"], "docs/research/WP-0041/source.json#/versions/runtime_source_sha256/transformers/cache_utils.py"),
        ("static.runtime.torch_docs", "torch/_torch_docs.py", source41["versions"]["runtime_source_sha256"]["torch/_torch_docs.py"], "docs/research/WP-0041/source.json#/versions/runtime_source_sha256/torch/_torch_docs.py"),
        ("static.runtime.torch_version", "torch/version.py", source41["versions"]["runtime_source_sha256"]["torch/version.py"], "docs/research/WP-0041/source.json#/versions/runtime_source_sha256/torch/version.py"),
        ("static.runtime.cudart64_13", "torch/lib/cudart64_13.dll", ACTIVE_RUNTIME_SHA256["torch/lib/cudart64_13.dll"], "docs/research/WP-0043/native.py#L42"),
        ("static.runtime.torch_cuda_streams", "torch/cuda/streams.py", ACTIVE_RUNTIME_SHA256["torch/cuda/streams.py"], "docs/research/WP-0043/native.py#L43"),
    ]
    for rkey, rrel, rsha, rref in runtime_5:
        add_ext(
            key=rkey,
            paper_clauses=["T1", "T2", "T2a"],
            direct_stock_stage="1a",
            subject=f"Pinned runtime file @venv/Lib/site-packages/{rrel}",
            cut="stage1a.cut1a_disk_hash_and_stage1b_loaded_origin",
            typ="sha256",
            expected={"relative_path": rrel, "sha256": rsha},
            comparator="sha256_exact",
            evidence_source="Stage-1a pure-stdlib worker hash under @venv/Lib/site-packages (re-joined to loaded module/DLL handle in Stage 1b/2)",
            evidence_locator=f"prospective:@arm/cut1a-metadata.json#/runtime_files/{rrel}",
            historical_reference=rref,
            binding_status="bound",
            status="prospective_stage1a_bound",
            missing_precondition=["Stage-1a execution"],
            alternatives_or_notes="Closes O5 gap: all 3 runtime_source_sha256 + 2 ACTIVE_RUNTIME digests were absent from bundle/register.json.",
        )

    add_ext(
        key="static.dist.pip",
        paper_clauses=["T2", "T2a"],
        direct_stock_stage="1a",
        subject="33rd installed distribution pip in Q0 @venv (installed_extra_names)",
        cut="stage1a.cut1a_metadata",
        typ="distribution_version",
        expected={"distribution": "pip", "version": "25.0.1"},
        comparator="strict_typed_exact",
        evidence_source="Stage-1a pure-stdlib child importlib.metadata.version('pip')",
        evidence_locator="prospective:@arm/cut1a-metadata.json#/distributions/pip",
        historical_reference="docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/checks/03-pip-check-and-venv-inventory.json; docs/research/WP-0041/source.json#/versions/installed_extra_names",
        binding_status="bound",
        status="prospective_stage1a_bound",
        missing_precondition=["Stage-1a execution"],
        alternatives_or_notes="Pinned from Git e43af2e2 03-pip-check-and-venv-inventory.json (sha256 503dd28f...); resolves O5.",
    )
    add_ext(
        key="static.dist.closed_set_33",
        paper_clauses=["T1", "T2", "T2a"],
        direct_stock_stage="1a",
        subject="Closed-world set of all importlib.metadata.distributions() visible to direct-stock @venv",
        cut="stage1a.cut1a_metadata",
        typ="closed_distribution_set",
        expected={
            "exact_count": 33,
            "normalized_map_pep503": {k: v["version"] for k, v in sorted(inv33_norm.items())},
            "unexpected_extra_distributions_allowed": 0,
            "source_archive_sha256": sha256_repo_file(
                "docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/checks/03-pip-check-and-venv-inventory.json"
            ),
        },
        comparator="closed_set_exact_pep503",
        evidence_source="Stage-1a pure-stdlib child enumeration of importlib.metadata.distributions()",
        evidence_locator="prospective:@arm/cut1a-metadata.json#/closed_distribution_set",
        historical_reference="docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/checks/03-pip-check-and-venv-inventory.json",
        binding_status="bound",
        status="prospective_stage1a_bound",
        missing_precondition=["Stage-1a execution"],
        alternatives_or_notes="Closes O5 closed-world distribution gap: catches any leaked base package (e.g. pypdf 6.16.2) or extra wheel.",
    )

    for forbidden_mod, reason in [
        ("triton", "config.json sets dash_use_triton=true; worker43.py L334 and Q0 05-preflight-cpu.json require find_spec('triton') is None"),
        ("flash_attn", "Q0 05-preflight-cpu.json requires find_spec('flash_attn') is None"),
        ("xformers", "Q0 05-preflight-cpu.json requires find_spec('xformers') is None"),
    ]:
        add_ext(
            key=f"static.dist.{forbidden_mod}",
            paper_clauses=["T1", "T2", "T2a"],
            direct_stock_stage="1a",
            subject=f"Forbidden optional acceleration package {forbidden_mod} must be ABSENT in direct-stock @venv",
            cut="stage1a.cut1a_metadata",
            typ="typed_absent_module_spec",
            expected={"state": "absent", "find_spec_result": None},
            comparator="typed_absent_exact",
            evidence_source=f"Stage-1a pure-stdlib child importlib.util.find_spec('{forbidden_mod}')",
            evidence_locator=f"prospective:@arm/cut1a-metadata.json#/forbidden_absent/{forbidden_mod}",
            historical_reference="docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/checks/05-preflight-cpu.json#/installed/forbidden_absent_find_spec_none; docs/research/WP-0043/native.py#L334",
            binding_status="bound",
            status="prospective_stage1a_bound",
            missing_precondition=["Stage-1a execution"],
            alternatives_or_notes=f"Closes O5 triton-ABSENT gap and extends to all 3 Q0-verified absent modules ({reason}).",
        )

    add_ext(
        key="static.wheelhouse.32_wheels",
        paper_clauses=["T1", "T2"],
        direct_stock_stage="1a",
        subject="Complete 32-wheel offline wheelhouse SHA-256 verification under @wheelhouse",
        cut="stage1a.cut1s_static_preflight",
        typ="wheelhouse_digest_manifest",
        expected={
            "wheel_count": len(wheels05["wheels"]),
            "manifest_archive_path": "docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/checks/02-verify-wheelhouse.json",
            "manifest_archive_sha256": sha256_repo_file(
                "docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/checks/02-verify-wheelhouse.json"
            ),
        },
        comparator="exact_32_wheel_sha256_and_size",
        evidence_source="Stage-1a supervisor read-only streaming SHA-256 verification of @wheelhouse/*.whl",
        evidence_locator="prospective:@run_root/preflight.json#/wheelhouse",
        historical_reference="docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/checks/02-verify-wheelhouse.json; docs/research/WP-0043/native.py#L44,L130-L133",
        binding_status="bound",
        status="prospective_stage1a_bound",
        missing_precondition=["Stage-1a execution"],
        alternatives_or_notes="Absent from standalone ZIP bundle (noted by Claude O5); confirmed present and pinned in Git e43af2e2.",
    )

    for mfile in LOCAL_CLOSURE_MODULES:
        mstem = mfile[:-3]
        gsha = device43["worktree_executables"][mfile]["git_source_sha256"]
        actual_git_sha = sha256_repo_file(f"docs/research/WP-0043/{mfile}")
        assert gsha == actual_git_sha, f"Mismatch for {mfile}: {gsha} != {actual_git_sha}"
        add_ext(
            key=f"static.local_closure.{mstem}",
            paper_clauses=["T2", "T2a", "T8"],
            direct_stock_stage="1a",
            subject=f"Pinned WP-0043 local closure module docs/research/WP-0043/{mfile} (pure stdlib/ctypes AST closure; static hash in Stage 1a, active only if reused in Stage 2)",
            cut="stage1a.cut1s_static_preflight",
            typ="sha256",
            expected={
                "repo_path": f"docs/research/WP-0043/{mfile}",
                "git_source_sha256": gsha,
                "module_scope_third_party_imports": [],
                "imported_in_stage1a": False,
            },
            comparator="sha256_exact",
            evidence_source="Stage-1a read-only Git/worktree digest check (NOT imported by Stage-1a self-contained worker)",
            evidence_locator=f"prospective:@run_root/preflight.json#/wp0043_local_closure/{mfile}",
            historical_reference=f"docs/coordination/WP-0043/device-release.json#/worktree_executables/{mfile}; docs/research/WP-0043/{mfile}",
            binding_status="bound",
            status="prospective_stage1a_bound",
            missing_precondition=["Stage-1a read-only check; Stage-2 O2 sibling-loading review"],
            alternatives_or_notes="Git e43af2e2 AST audit verified 0 third-party top-level imports across all 6 modules (including transitive 6th sibling transfer.py imported by native_observer.py L7).",
        )

    # --- Pre-Stage-1a unbound entry & coordinator root pins ---
    add_ext(
        key="cpu.entry.stage1a_source_pin",
        paper_clauses=["T2a", "T8", "Eq. (11)", "Eq. (12)"],
        direct_stock_stage="1a",
        subject="Frozen Stage-1a direct-stock supervisor, pure-stdlib worker, and offline scorer source files",
        cut="stage1a.pre_execution_freeze",
        typ="source_commit_and_file_sha256",
        expected={
            "required_files": ["stage1a_supervisor.py", "stage1a_worker.py", "stage1a_scorer.py"],
            "source_commit_and_digests": "UNBOUND_PRE_STAGE1A (unimplemented in Stage 0)",
        },
        comparator="git_commit_and_sha256_exact",
        evidence_source="Future Stage-1a frozen source commit + independent eld-rd-reviewer code review (Rev_1a)",
        evidence_locator="prospective:docs/research/WP-0046/stage1a_*",
        historical_reference="docs/research/WP-0046/proposal-r1.md#future-entries",
        binding_status="unbound_pre_stage1a",
        status="unbound_pre_stage1a_hold_item",
        missing_precondition=[
            "Stage-0 r1 independent review acceptance",
            "Authoring, freezing, hashing, and independent non-author review of Stage-1a supervisor/worker/scorer source",
        ],
        alternatives_or_notes="Mandatory Stage-1a prerequisite in B_T intersect Pi_1a (holds Stage 1).",
    )
    add_ext(
        key="cpu.entry.coordinator_roots_manifest",
        paper_clauses=["T3", "T8", "Eq. (12)"],
        direct_stock_stage="1a",
        subject="Coordinator-published private local release manifest binding symbolic roots (@base, @venv, @q0_root, @model, @wheelhouse, @worktree, @speed_root, @run_root)",
        cut="stage1a.coordinator_release",
        typ="local_root_binding_manifest",
        expected={
            "required_symbolic_roots": sorted(SYMBOLIC_ROOTS.keys()),
            "manifest_sha256": "UNBOUND_PRE_STAGE1A (issued only by eld-coordinator on separate Stage-1a local release)",
        },
        comparator="manifest_sha256_and_root_containment",
        evidence_source="Future coordinator local Stage-1a release manifest",
        evidence_locator="prospective:@run_root/release-manifest.json",
        historical_reference="docs/coordination/WP-0046/assignment.md",
        binding_status="unbound_pre_stage1a",
        status="unbound_pre_stage1a_hold_item",
        missing_precondition=["Separate local coordinator release for Stage 1a"],
        alternatives_or_notes="Mandatory Stage-1a prerequisite in B_T intersect Pi_1a (holds Stage 1).",
    )

    # --- O4: Exact 31-key closed child env allowlist + cpu.env.* + forbidden ABSENT sentinels ---
    add_ext(
        key="cpu.env.closed_allowlist_31",
        paper_clauses=["T1", "T2a", "T4"],
        direct_stock_stage="1a",
        subject="Closed-world child environment allowlist (exact 31 keys in e_child; 32 keys in e_launch with __PYVENV_LAUNCHER__; all unlisted keys ABSENT)",
        cut="stage1a.cut1a_startup",
        typ="closed_tagged_env_schema",
        expected={
            "launch_extra_key": {"__PYVENV_LAUNCHER__": {"e_launch": {"state": "present", "value": "@venv/Scripts/python.exe"}, "e_child": {"state": "absent"}}},
            "exact_child_allowlist_31": sorted(all_31),
            "unlisted_key_policy": "ABSENT (any key in e_child not in exact_child_allowlist_31 yields M conflict)",
            "key_partition_check": {
                "already_in_exec_env_4": ["HF_HUB_OFFLINE", "PYTHONHASHSEED", "PYTHONNOUSERSITE", "TRANSFORMERS_OFFLINE"],
                "named_cpu_env_9": [
                    "CUDA_DEVICE_ORDER", "CUDA_VISIBLE_DEVICES", "HF_HOME", "HF_MODULES_CACHE",
                    "PATH", "PYTHONDONTWRITEBYTECODE", "PYTHONIOENCODING", "PYTHONUNBUFFERED", "PYTHONUTF8",
                ],
                "grouped_cache_and_os_18": sorted(
                    all_31
                    - {"HF_HUB_OFFLINE", "PYTHONHASHSEED", "PYTHONNOUSERSITE", "TRANSFORMERS_OFFLINE"}
                    - {
                        "CUDA_DEVICE_ORDER", "CUDA_VISIBLE_DEVICES", "HF_HOME", "HF_MODULES_CACHE",
                        "PATH", "PYTHONDONTWRITEBYTECODE", "PYTHONIOENCODING", "PYTHONUNBUFFERED", "PYTHONUTF8",
                    }
                ),
            },
        },
        comparator="closed_keyset_and_typed_presence_exact",
        evidence_source="Supervisor lpEnvironment record + child full os.environ dump at startup",
        evidence_locator="prospective:@arm/cut1a-startup.json#/environment",
        historical_reference="docs/research/WP-0043/native.py#L189-L199",
        binding_status="bound",
        status="prospective_stage1a_bound",
        missing_precondition=["Stage-1a execution"],
        alternatives_or_notes="Closes O4 (reconciles 6-of-31 register gap; catches S4b and S6).",
    )

    named_cpu_env_specs = [
        ("PYTHONUTF8", {"state": "present", "value": "1"}, "Verified jointly with sys.flags.utf8_mode == 1 (S4b)."),
        ("PYTHONIOENCODING", {"state": "present", "value": "utf-8"}, "Matches worker43.py L199."),
        ("PYTHONDONTWRITEBYTECODE", {"state": "present", "value": "1"}, "Paired with -B (dont_write_bytecode == 1)."),
        ("PYTHONUNBUFFERED", {"state": "present", "value": "1"}, "Paired with -u."),
        ("HF_HOME", {"state": "present", "value": "@arm/hf"}, "Per-unit isolated cache dir."),
        ("HF_MODULES_CACHE", {"state": "present", "value": "@arm/modules"}, "Dynamic HF modules root required by worker43.py L359."),
        ("CUDA_VISIBLE_DEVICES", {"state": "present", "value": ""}, "Intentional Stage-1a/1b difference (empty string hides GPUs; Stage 2 binds leased UUID)."),
        ("CUDA_DEVICE_ORDER", {"state": "present", "value": "PCI_BUS_ID"}, "Matches worker43.py L196 identically across stages."),
        ("PATH", {"state": "present", "value": "%SystemRoot%/System32;%SystemRoot%"}, "Intentional Stage-1a/1b difference omitting @venv/Scripts; verified in Stage 1b against torch os.add_dll_directory()."),
    ]
    for ekey, eval_tag, enote in named_cpu_env_specs:
        add_ext(
            key=f"cpu.env.{ekey}",
            paper_clauses=["T2a", "T4"],
            direct_stock_stage="1a",
            subject=f"Stage-1a worker environment key {ekey} (e_launch and e_child)",
            cut="stage1a.cut1a_startup",
            typ="tagged_env_presence_string",
            expected={"e_launch": eval_tag, "e_child": eval_tag},
            comparator="tagged_presence_and_exact_string",
            evidence_source="Supervisor lpEnvironment + child os.environ snapshot",
            evidence_locator=f"prospective:@arm/cut1a-startup.json#/environment/{ekey}",
            historical_reference="docs/research/WP-0043/native.py#L192-L199",
            binding_status="bound",
            status="prospective_stage1a_bound",
            missing_precondition=["Stage-1a execution"],
            alternatives_or_notes=enote,
        )

    add_ext(
        key="cpu.env.cache_and_os_keys_18",
        paper_clauses=["T2a", "T4"],
        direct_stock_stage="1a",
        subject="Remaining 18 of 31 allowlisted worker43.py child environment keys (3 offline flags, 8 per-unit cache/temp/home paths, 7 Windows OS pass-through keys)",
        cut="stage1a.cut1a_startup",
        typ="tagged_env_map_18",
        expected={
            "offline_flags_3": {
                "HF_HUB_DISABLE_TELEMETRY": {"state": "present", "value": "1"},
                "HF_HUB_DISABLE_XET": {"state": "present", "value": "1"},
                "PIP_NO_INDEX": {"state": "present", "value": "1"},
            },
            "per_unit_paths_8": {
                "TEMP": {"state": "present", "value": "@arm/tmp"},
                "TMP": {"state": "present", "value": "@arm/tmp"},
                "HOME": {"state": "present", "value": "@arm/home"},
                "USERPROFILE": {"state": "present", "value": "@arm/home"},
                "CUDA_CACHE_PATH": {"state": "present", "value": "@arm/cuda"},
                "TORCH_HOME": {"state": "present", "value": "@arm/torch"},
                "TORCHINDUCTOR_CACHE_DIR": {"state": "present", "value": "@arm/inductor"},
                "XDG_CACHE_HOME": {"state": "present", "value": "@arm/xdg"},
            },
            "os_passthrough_7": {k: "exact_supervisor_os_value_if_present_else_absent" for k in WORKER43_OS_PASSTHROUGH_7},
            "directory_creation_rule": "Supervisor creates @arm/tmp and @arm/home OUTSIDE env_for() (eliminating worker43.py L200 hidden mkdir side effect).",
        },
        comparator="tagged_presence_and_exact_string",
        evidence_source="Supervisor lpEnvironment + child os.environ snapshot",
        evidence_locator="prospective:@arm/cut1a-startup.json#/environment",
        historical_reference="docs/research/WP-0043/native.py#L190-L201",
        binding_status="bound",
        status="prospective_stage1a_bound",
        missing_precondition=["Stage-1a execution"],
        alternatives_or_notes="Completes exact 4 + 9 + 18 = 31 bijection with worker43.py env_for() allowlist.",
    )
    add_ext(
        key="cpu.env.forbidden_absent_sentinels",
        paper_clauses=["T1", "T2a", "T4"],
        direct_stock_stage="1a",
        subject="Explicit typed-ABSENT environment sentinels in e_child (and e_launch except __PYVENV_LAUNCHER__)",
        cut="stage1a.cut1a_startup",
        typ="typed_absent_env_sentinels",
        expected={
            "e_child_must_be_absent": FORBIDDEN_ABSENT_ENV_SENTINELS,
            "e_launch_must_be_absent": [k for k in FORBIDDEN_ABSENT_ENV_SENTINELS if k != "__PYVENV_LAUNCHER__"],
            "note_empty_string_rejected": "present('') != absent (D4 / S6)",
        },
        comparator="typed_absent_exact",
        evidence_source="Supervisor lpEnvironment + child os.environ snapshot",
        evidence_locator="prospective:@arm/cut1a-startup.json#/environment_absent_sentinels",
        historical_reference="docs/research/WP-0043/native.py#L189-L199; Paper I T1/T4",
        binding_status="bound",
        status="prospective_stage1a_bound",
        missing_precondition=["Stage-1a execution"],
        alternatives_or_notes="Explicitly covers PYTHONPATH, PYTHONHOME, PYTHONSAFEPATH, PYTHONCASEOK, PYTHONWARNINGS (Claude O4/S6), OMP/MKL/OPENBLAS_NUM_THREADS, CUBLAS_WORKSPACE_CONFIG, and child __PYVENV_LAUNCHER__ consumption.",
    )

    # --- O6: Stage-1a 3 live control units + Stage-1b separate CPU-torch obligations ---
    add_ext(
        key="cpu.controls.stage1a_3_live_controls",
        paper_clauses=["T2a", "T3a", "T4", "T8"],
        direct_stock_stage="1a",
        subject="Three Stage-1a live negative/missingness control units paired with the 2 decisive direct-stock units",
        cut="stage1a.live_controls",
        typ="live_control_schedule",
        expected={
            "controls": [
                {"id": "c01-isolated-start", "perturbation": "launch with -I despite PYTHONHASHSEED=0", "expected_verdict": "M", "expected_conflict_keys": ["flags.ignore_environment", "flags.hash_randomization", "flags.utf8_mode"]},
                {"id": "c02-dropped-flags", "perturbation": "observer omits sys.flags from startup receipt", "expected_verdict": "U", "expected_missing_keys": ["flags"]},
                {"id": "c03-omitted-member", "perturbation": "drop rehearsal-payload.bin from both I_r and R_r", "expected_verdict": "M", "expected_conflict_keys": ["omit:rehearsal-payload.bin"]},
            ],
        },
        comparator="full_record_control_match",
        evidence_source="Stage-1a offline scorer applied to 3 isolated control units",
        evidence_locator="prospective:@run_root/controls-summary.json",
        historical_reference="docs/reviews/WP-0046/first.md#§7; docs/research/WP-0046/proposal-r1.md#stage1a-schedule",
        binding_status="bound",
        status="prospective_stage1a_bound",
        missing_precondition=["Stage-1a control entry implementation and release"],
        alternatives_or_notes="Adopts Claude §7 smallest discriminating experiment (5 total units: 2 decisive + 3 live controls).",
    )
    add_ext(
        key="cpu.stage1b.entry_source_pin",
        paper_clauses=["T2a", "T8", "Eq. (12)"],
        direct_stock_stage="1b",
        subject="Frozen Stage-1b CPU-only torch/DLL observer entry source (authored/released ONLY after Stage 1a passes)",
        cut="stage1b.pre_execution_freeze",
        typ="source_commit_and_file_sha256",
        expected={
            "required_files": ["stage1b_supervisor.py", "stage1b_worker.py", "stage1b_scorer.py"],
            "source_commit_and_digests": "UNBOUND_STAGE1B (held behind Stage 1a pass and separate decision on importing torch 2.13 on Windows CPU)",
        },
        comparator="git_commit_and_sha256_exact",
        evidence_source="Future Stage-1b frozen source commit + independent review (Rev_1b)",
        evidence_locator="prospective:docs/research/WP-0046/stage1b_*",
        historical_reference="docs/research/WP-0046/proposal-r1.md#stage1b-boundary",
        binding_status="unbound_stage1b",
        status="prospective_stage1b_deferred",
        missing_precondition=["Passing Stage-1a qualification (V^(1a) = P)", "Separate Stage-1b source freeze, review, and coordinator release"],
        alternatives_or_notes="Enters deferred_unbound during Stage 0/1a; enters Pi_1b only when Stage 1b is proposed.",
    )
    add_ext(
        key="cpu.stage1b.torch_import_and_dlls",
        paper_clauses=["T1", "T2a"],
        direct_stock_stage="1b",
        subject="Stage-1b CPU-only import of declared packages including torch 2.13.0+cu130 with CUDA_VISIBLE_DEVICES='', zero torch.cuda.* calls, and LOAD_DLL_DEBUG_EVENT origin hashing",
        cut="stage1b.cut1b_cpu_torch_import",
        typ="module_and_dll_origin_map",
        expected={
            "cuda_visible_devices": {"state": "present", "value": ""},
            "zero_torch_cuda_calls": True,
            "zero_model_load_or_safetensors_reads": True,
            "packages_imported": [
                "numpy", "PIL", "pypdfium2", "psutil", "safetensors",
                "tokenizers", "huggingface_hub", "transformers", "torch", "torchvision",
            ],
            "versions_checked": {"torch": "2.13.0+cu130", "torch_cuda": "13.0", "transformers": "4.52.1"},
            "dll_origins_via_debug_load_event": "Every LOAD_DLL_DEBUG_EVENT under @venv or @base hashed and verified; zero DLLs from @base/Lib/site-packages or user-site",
            "optional_backend_flag_readability_question": "Record whether torch.are_deterministic_algorithms_enabled(), torch.backends.cuda.matmul.allow_tf32, torch.backends.cudnn.allow_tf32, torch.is_autocast_enabled() can be queried without triggering CUDA context initialization (prospective unverified hypothesis).",
        },
        comparator="root_containment_and_sha256",
        evidence_source="Stage-1b child sys.modules receipt + supervisor LOAD_DLL_DEBUG_EVENT trace",
        evidence_locator="prospective:@arm/cut1b-imports.json",
        historical_reference="docs/research/WP-0043/native.py#L339; docs/reviews/WP-0046/first.md#O6",
        binding_status="bound",
        status="prospective_stage1b_bound",
        missing_precondition=["Passing Stage-1a qualification", "Separate Stage-1b code freeze, review, and coordinator release"],
        alternatives_or_notes="Isolates the unverified Windows torch-2.13 CUDA DLL loading risk out of Stage 1a (adopting Claude O6 / §7).",
    )

    # --- M2: Stage-1 to Stage-2 projection bridge ---
    add_ext(
        key="gate.stage1_to_stage2_bridge",
        paper_clauses=["T8", "T8a", "Eq. (12)"],
        direct_stock_stage="2",
        subject="Stage-1 preflight to Stage-2 stock plan projection join [proj(Pi_1) = proj(Plan_2)] (M2; G1, G2)",
        cut="stage2.pre_admission_bridge",
        typ="preflight_to_stage2_projection_join",
        expected={
            "preflight_verdict": "V_preflight := V^(1a)(Pi_1a) == 'P' and V^(1b)(Pi_1b) == 'P'",
            "projected_fields_must_match": ["route", "env_schema (except explicitly reviewed Stage-1 CUDA_VISIBLE_DEVICES='' -> Stage-2 leased UUID delta)", "source_pin_or_reviewed_bridge", "static_manifest_digest"],
            "blocks_g1_env_drift": True,
            "blocks_g2_route_drift": True,
        },
        comparator="projection_equality_plus_reviewed_delta",
        evidence_source="Stage-2 admission gate joining frozen Stage-1a/1b passing receipts to Stage-2 plan manifest (controls_r1.py:eval_gate12)",
        evidence_locator="docs/research/WP-0046/controls_r1.py",
        historical_reference="Paper I T8a Eq. (12); docs/research/WP-0046/corrigenda-r1.md#M2",
        binding_status="bound",
        status="prospective_stage2_bound",
        missing_precondition=["Passing Stage-1a and Stage-1b receipts + Stage-2 plan freeze"],
        alternatives_or_notes="Adopts Claude M2 (G1/G2) and Gemini M-09 preflight subject binding.",
    )

    # --- O8: 5 per-row native.{1445..1449}.support_choice sub-atoms ---
    for pos in range(1445, 1450):
        rrec = retained_by_pos[pos]
        row_idx = rrec["row"]
        add_ext(
            key=f"native.{pos}.support_choice",
            paper_clauses=["T5", "Eq. (8)", "Eq. (7)"],
            direct_stock_stage="2",
            subject=f"F07.warm1 observed stock row {row_idx} (position {pos}) support nonemptiness, emission membership, winner optimality, and emission presence",
            cut=f"stage2.decoded_score_row.{pos}",
            typ="per_row_support_choice_predicate",
            expected={
                "position": pos,
                "row_index": row_idx,
                "D1_expected_on_f07": [],
                "D2_expected_on_f07": [1],
                "historical_reference_emission": rrec["actual_emission"],
                "historical_reference_margin": rrec["final_top_two"]["difference"],
                "P7_missing_emission_rule": "Reading B: missing y_obs always enters U = {emission}",
                "P3_oob_rule": "Amended r1 checks X_oob unconditionally whenever A and y_obs are observed; strict Paper I rev. 1 mode checks choice only when clean",
            },
            comparator="per_row_eq8_support_choice_and_P7_reading_B",
            evidence_source="Stage-2 independent Phase-Local Eq. (8) scorer",
            evidence_locator=f"prospective:@run_root/score-native.json#/rows/{row_idx}/support_choice",
            historical_reference=f"docs/coordination/WP-0043/native-evidence.json#/retained_rows/{row_idx}",
            binding_status="bound",
            status="prospective_stage2_bound",
            missing_precondition=["Stage-2 scorer update and observed stock execution"],
            alternatives_or_notes="Closes Claude O8: per-row keys preserve row identity in firstConflict and firstFinding.",
        )

    assert len(entries) == 118, f"Expected 118 original entries, got {len(entries)}"
    assert len({e["key"] for e in entries}) == 118, "Duplicate keys in original 118 entries"
    assert len(extended) == 44, f"Expected 44 extended obligations, got {len(extended)}"
    all_items = entries + extended
    assert len({e["key"] for e in all_items}) == len(all_items), "Key collision between original and extended obligations"

    # Compute exact scoped plan Pi_s counts for s in {0, 1a, 1b, 2, 3}
    scoped_summary: dict[str, Any] = {}
    for idx, st in enumerate(STAGE_ORDER):
        in_stages = set(STAGE_ORDER[: idx + 1])
        pi_s = [e for e in all_items if e["direct_stock_stage"] in in_stages]
        outside_s = [e for e in all_items if e["direct_stock_stage"] not in in_stages]
        unbound_in_scope = sorted(e["key"] for e in pi_s if e["binding_status"] != "bound")
        unbound_outside_scope = sorted(e["key"] for e in outside_s if e["binding_status"] != "bound")
        scoped_summary[f"Pi_{st}"] = {
            "included_stages": sorted(in_stages, key=STAGE_ORDER.index),
            "total_obligations": len(pi_s),
            "original_118_count": sum(1 for e in entries if e["direct_stock_stage"] in in_stages),
            "extended_44_count": sum(1 for e in extended if e["direct_stock_stage"] in in_stages),
            "bound_in_scope": len(pi_s) - len(unbound_in_scope),
            "unbound_in_scope_BT_cap_Pi": unbound_in_scope,
            "unbound_in_scope_count": len(unbound_in_scope),
            "deferred_unbound_BT_minus_Pi": unbound_outside_scope,
            "deferred_unbound_count": len(unbound_outside_scope),
        }

    return {
        "schema": "wp0046-direct-stock-register/2",
        "proposal_id": PROPOSAL_ID,
        "author": "eld-owner-probe",
        "provenance": {
            "turn1_independent_freeze": TURN1_FREEZE,
            "peer_exchange_tip": PEER_EXCHANGE_TIP,
            "reference_commit": REF_COMMIT,
            "attribution_note": "Post-opening r1 revision authored by eld-owner-probe incorporating peer criticisms (eld-rd-reviewer) and Git e43af2e2 verifications; requires fresh independent non-author review before acceptance.",
        },
        "status": "Stage 0 post-opening r1 proposal register; 0 prospective target executions; Stage 1 HELD",
        "symbolic_roots": SYMBOLIC_ROOTS,
        "unknown_semantics": "Explicit tagged values distinguish state='present' (including JSON null or empty string ''), state='absent' (measured absent key/attribute), and state='unobserved' (missing observation ?).",
        "original_118_count": len(entries),
        "extended_obligations_count": len(extended),
        "total_obligations_count": len(all_items),
        "stage_counts_original_118": {
            str(s): sum(1 for e in entries if e["earliest_stage"] == s) for s in range(4)
        },
        "stage_counts_r1_original_118": {
            st: sum(1 for e in entries if e["direct_stock_stage"] == st) for st in STAGE_ORDER
        },
        "stage_counts_r1_extended_44": {
            st: sum(1 for e in extended if e["direct_stock_stage"] == st) for st in STAGE_ORDER
        },
        "stage_counts_r1_total_162": {
            st: sum(1 for e in all_items if e["direct_stock_stage"] == st) for st in STAGE_ORDER
        },
        "binding_status_counts_total_162": {
            bs: sum(1 for e in all_items if e["binding_status"] == bs)
            for bs in sorted({e["binding_status"] for e in all_items})
        },
        "scoped_plan_summary": scoped_summary,
        "entries": entries,
        "extended_obligations": extended,
    }


def serialize(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, indent=2, ensure_ascii=True) + "\n"


def check_hygiene(text: str) -> None:
    m = HOST_PATH_RE.search(text)
    if m:
        raise ValueError(f"Host path or username leaked into public register-r1: {m.group(0)!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify WP-0046 r1 direct-stock register.")
    parser.add_argument("--verify", action="store_true", help="Verify committed register-r1.json matches generator output.")
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
            raise SystemExit("register-r1.json differs from deterministic generator output")
        sha = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
        print(
            json.dumps(
                {
                    "verified": True,
                    "original_118_count": manifest["original_118_count"],
                    "extended_obligations_count": manifest["extended_obligations_count"],
                    "total_obligations_count": manifest["total_obligations_count"],
                    "stage_counts_r1_total_162": manifest["stage_counts_r1_total_162"],
                    "binding_status_counts_total_162": manifest["binding_status_counts_total_162"],
                    "Pi_1a_unbound": manifest["scoped_plan_summary"]["Pi_1a"]["unbound_in_scope_BT_cap_Pi"],
                    "sha256": sha,
                },
                sort_keys=True,
            )
        )
        return 0

    OUT_PATH.write_text(rendered, encoding="utf-8", newline="\n")
    sha = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    print(
        f"Wrote {OUT_PATH.name}: {manifest['original_118_count']}+{manifest['extended_obligations_count']}"
        f"={manifest['total_obligations_count']} obligations, sha256={sha}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
