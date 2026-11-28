"""Deterministic stdlib generator and verifier for docs/research/WP-0046/register-r2.json.

Minimal final Stage-0 supplement (`wp0046-direct-stock-r2`) addressing every
remaining numbered request from eld-rd-reviewer's exchange/exchange.md §4
(commit ee07ca660286927ba5017a5592d2f8bed3a8d702) while preserving register.json
and register-r1.json untouched.

Derives deterministically from build_register_r1.build_manifest() plus pinned
repo JSONs at e43af2e263f55478d1d551a5a095536b042589c2. Zero private input,
host path, model/torch import, device access, or network I/O.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
OUT_PATH = HERE / "register-r2.json"
REF_COMMIT = "e43af2e263f55478d1d551a5a095536b042589c2"
PROPOSAL_ID = "wp0046-direct-stock-r2"
TURN1_FREEZE = "6fa242950ffd4dfd1d19accc9271e88aada2d552"
TURN2_FREEZE = "7ededc5344d896ba82d7a8fa57e58eb7d1bd8652"
PEER_EXCHANGE_COMMIT = "ee07ca660286927ba5017a5592d2f8bed3a8d702"
STAGE_ORDER = ["0", "1a", "1b", "2", "3"]

HOST_PATH_RE = re.compile(
    r"(?i)(?:[A-Z]:[/\\]|[/\\]Users[/\\]|AppData[/\\]Local|Asp\.net Projects|eLedgerCare-(?:Speed|Q0)|w04[0-9]-)"
)

# Exact 18 CPython 3.12.10 sys.flags fields (matching docs/reviews/WP-0045/blind/prior-0.json)
# derived from a_* = (-s, -P, -B, -u) and closed 31-key e_launch (PYTHONHASHSEED="0", PYTHONUTF8="1",
# PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1", all other PYTHON* ABSENT).
DERIVED_SYS_FLAGS_18: dict[str, int | bool] = {
    "bytes_warning": 0,
    "debug": 0,
    "dev_mode": False,
    "dont_write_bytecode": 1,
    "hash_randomization": 0,
    "ignore_environment": 0,
    "inspect": 0,
    "int_max_str_digits": 4300,
    "interactive": 0,
    "isolated": 0,
    "no_site": 0,
    "no_user_site": 1,
    "optimize": 0,
    "quiet": 0,
    "safe_path": True,
    "utf8_mode": 1,
    "verbose": 0,
    "warn_default_encoding": 0,
}

# Closed Stage-1 -> Stage-2 bridge delta Delta(Pi_1, Plan_2) (Peer Request 3; E-M09, E-I5).
BRIDGE_DELTA_SCHEMA = {
    "permitted_deltas": {
        "CUDA_VISIBLE_DEVICES": {
            "stage1": {"state": "present", "value": ""},
            "stage2": {"state": "present", "value": "<coordinator_leased_gpu_uuid>"},
            "predicate": "Exact UUID from active sole GPU lease matching torch.cuda.get_device_properties(0).uuid",
        },
        "PATH": {
            "stage1": {"state": "present", "value": "%SystemRoot%/System32;%SystemRoot%"},
            "stage2": "Pinned from Stage-1b DLL audit (%SystemRoot%/System32;%SystemRoot% unless Stage-1b proves @venv/Scripts required)",
            "predicate": "Exact string frozen before Stage-2 admission",
        },
        "debugger_attachment_and_heap": {
            "stage1": {
                "creation_flags": "0x08000006 (CREATE_NO_WINDOW|CREATE_SUSPENDED|DEBUG_ONLY_THIS_PROCESS)",
                "peb_being_debugged": 1,
                "nt_debug_heap_policy": "explicitly_recorded_or_disabled_via_flag",
                "first_chance_exception_policy": "routed_to_supervisor_and_logged",
            },
            "stage2": "MUST be bound before Stage-2 review: either identical DEBUG_ONLY_THIS_PROCESS attachment OR reviewed DebugActiveProcessStop cut with explicit PEB/heap/exception equivalence statement",
            "predicate": "Reviewed Stage-2 decision record",
        },
        "entry_files": {
            "stage1a": ["@source/stage1a_supervisor.py", "@source/stage1a_worker.py", "@source/stage1a_scorer.py"],
            "stage1b": ["@source/stage1b_supervisor.py", "@source/stage1b_worker.py", "@source/stage1b_scorer.py"],
            "stage2": ["@source/stage2_stock_supervisor.py", "@source/stage2_stock_worker.py", "@source/stage2_stock_scorer.py"],
            "predicate": "Each frozen with exact Git commit + file SHA-256 and independent non-author review",
        },
    },
    "undeclared_difference_rule": "Any difference outside permitted_deltas between passing Stage-1a/1b receipt and Stage-2 plan returns verdict M (blocks G1 and G2).",
}

# Precondition keyword classifier aligned with eld-rd-reviewer classify_preconditions.py (Request 10).
BINDING_OR_DECISION_RE = re.compile(
    r"Fix |agreement|Freeze|Decision|implement|Extend|Add |Update|must inspect|bound separately|"
    r"Complete Stage-3|reviewed|Resolve static\.venv|settle P3|sign-off|disposition",
    re.I,
)


def _load_r1_module() -> Any:
    spec = importlib.util.spec_from_file_location("_wp46_build_r1", HERE / "build_register_r1.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _classify_statuses(item: dict[str, Any]) -> tuple[str, str]:
    """Explicitly separate binding_status from observation_status (Peer Request 10)."""
    st = item["direct_stock_stage"]
    orig_b = item["binding_status"]
    pre = item.get("missing_precondition") or []
    pre_text = " ; ".join(pre)

    if st == "0":
        obs = "pending_rev0_digest_receipt"
    elif st == "1a":
        obs = "unobserved_prospective_stage1a"
    elif st == "1b":
        obs = "unobserved_prospective_stage1b"
    elif st == "2":
        obs = "unobserved_prospective_stage2"
    else:
        obs = "unobserved_prospective_stage3"

    if orig_b == "unbound_stage3":
        return "deferred_stage3", obs
    if orig_b in ("unbound_pre_stage1a", "unbound_stage1b", "unbound_stage2"):
        return orig_b, obs

    # Even when r1 marked a row "bound", inspect missing_precondition honestly!
    if BINDING_OR_DECISION_RE.search(pre_text):
        if st == "0":
            return "pending_independent_review_rev0", obs
        if st == "1a":
            return "pending_stage1a_code_or_review_binding", obs
        if st == "1b":
            return "pending_stage1b_code_or_review_binding", obs
        if st == "2":
            return "pending_stage2_code_or_review_binding", obs
        return "deferred_stage3", obs

    return "bound_static_rule", obs


def build_manifest() -> dict[str, Any]:
    r1_mod = _load_r1_module()
    base = copy.deepcopy(r1_mod.build_manifest())
    entries: list[dict[str, Any]] = base["entries"]
    extended: list[dict[str, Any]] = base["extended_obligations"]
    by_orig = {e["key"]: e for e in entries}
    by_ext = {e["key"]: e for e in extended}

    # --- Request 11 & 12: route.design names new entries, freezes ordered sys.path, marks launcher peer-observed only ---
    rd = by_orig["route.design"]
    rd["expected"]["proposed_entry_files_replacing_worker43"] = {
        "stage1a": ["@source/stage1a_supervisor.py", "@source/stage1a_worker.py", "@source/stage1a_scorer.py"],
        "stage1b": ["@source/stage1b_supervisor.py", "@source/stage1b_worker.py", "@source/stage1b_scorer.py"],
        "stage2": ["@source/stage2_stock_supervisor.py", "@source/stage2_stock_worker.py", "@source/stage2_stock_scorer.py"],
    }
    rd["expected"]["ordered_sys_path_relation_O2"] = {
        "stage1a_and_1b_under_dash_P": [
            "@base/python312.zip",
            "@base/DLLs",
            "@base/Lib",
            "@base",
            "@venv",
            "@venv/Lib/site-packages",
        ],
        "stage1a_and_1b_source_dir_policy": "Self-contained single-file worker: @source is NOT in sys.path under -P.",
        "stage2_under_dash_P_primary": "Load digest-verified WP-0043 sibling files via importlib.util.spec_from_file_location without mutating sys.path; OR if explicit insertion is chosen, freeze @source at exact ordered index 0 after startup cut and verify in ordered sys.path.",
        "stage2_alternative_no_dash_P": "Drop -P (-s -B -u) and freeze ordered sys.path[0] == @source with audited directory contents.",
    }
    rd["expected"]["venv_binding_mechanism_O3"]["verification_status"] = (
        "peer_observed_synthetic_only_requires_stage1a_reobservation_on_real_q0_venv"
    )
    rd["expected"]["stage0_receipt_contract"] = (
        "Receipt for d_k=0 design atom is the independently reviewed frozen plan artifact digest (plan_commit_sha, review_commit_sha, artifact_sha256)."
    )
    rd["alternatives_or_notes"] += " Updated in r2 per Peer Requests 4, 11, 12 (named new entries, ordered sys.path, peer-observed-only launcher status)."

    # --- Request 4: Stage-0 receipt contract in plan.static_consistency ---
    psc = by_orig["plan.static_consistency"]
    psc["expected"]["stage0_dk0_receipt_rule"] = (
        "A Stage-0 (d_k=0) atom's receipt is the independently reviewed frozen plan digest (plan_commit_sha, review_commit_sha, artifact_sha256). Without Rev_0 it evaluates U; once Rev_0 is recorded with empty X_static(all) and empty B_T cap Pi_0, ASSESS(s=0) returns P."
    )
    psc["expected"]["controls_r2_scope_fix_XC3"] = (
        "Default required_binding_stages is range(0, stage + 1) (all stages 0..s), fixing Turn-1 controls.py [0, stage] defect caught by XC3."
    )

    # --- Request 2: Keep ALL 6 exec.env.* rows strictly at Stage 2 (no subject conflation!) ---
    for env_key in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "PYTHONHASHSEED", "PYTHONNOUSERSITE"):
        row = by_orig[f"exec.env.{env_key}"]
        row["direct_stock_stage"] = "2"
        row["subject"] = "Stage-2 stock worker process environment (e_launch and e_child; distinct from Stage-1a cpu.env.*)"
        row["status"] = "prospective_stage2_bound"
        row["missing_precondition"] = ["Stage-2 stock worker execution and startup receipt"]
        row["alternatives_or_notes"] = (
            f"Restored to direct_stock_stage='2' in r2 per Peer Request 2 (E-I3): Stage-1a rehearsal owns dedicated key cpu.env.{env_key} so Stage-1 rehearsal never conflates with Stage-2 stock worker."
        )

    # --- Request 8: Bind ALL 18 CPython 3.12.10 sys.flags fields in cpu.hash_effective & exec.configuration ---
    che = by_orig["cpu.hash_effective"]
    che["expected"] = {
        "comparator_provenance": "derived_from_argv_and_closed_31_env_not_historically_observed (all 18 CPython 3.12.10 sys.flags fields matching prior0.json schema)",
        "e_launch.PYTHONHASHSEED": {"state": "present", "value": "0"},
        "e_child.PYTHONHASHSEED": {"state": "present", "value": "0"},
        "sys_flags_18_exact_typed": DERIVED_SYS_FLAGS_18,
    }
    che["alternatives_or_notes"] = "Expanded from 8 to all 18 sys.flags fields in r2 per Peer Request 8 (E-M01), derived from a_*=(-s,-P,-B,-u) and closed 31-key e_launch."

    ec = by_orig["exec.configuration"]
    ec["expected"]["orig_argv_prefix"] = [
        "@base/python.exe", "-s", "-P", "-B", "-u", "@source/stage2_stock_worker.py", "_worker",
    ]
    ec["expected"]["sys_flags_derived_absolute"] = DERIVED_SYS_FLAGS_18
    ec["alternatives_or_notes"] += " Expanded to all 18 sys.flags fields in r2 (Peer Request 8) and aligned entry filename to stage2_stock_worker.py (Peer Request 11)."

    # --- Request 7 & 9: cpu.import_resolution per-module/per-DLL atoms & base site-packages inventory ---
    cir = by_orig["cpu.import_resolution"]
    cir["expected"]["venv_activation_hypothesis_O3"] = (
        "e_launch.__PYVENV_LAUNCHER__ == present('@venv/Scripts/python.exe') and e_child.__PYVENV_LAUNCHER__ == absent "
        "(peer_observed_synthetic_only_requires_stage1a_reobservation_on_real_q0_venv)"
    )
    cir["expected"]["per_origin_atom_reporting_req9"] = (
        "Emit one keyed atom per loaded module (module.<name>.origin) and per observed site/base path entry (sys_path.<idx>, base_site_dist.<name>) rather than aggregate booleans, so firstConflict preserves exact failing identity."
    )
    cir["expected"]["base_site_packages_inventory_ref_req7"] = "extended:static.venv.base_site_packages_inventory"
    cir["alternatives_or_notes"] = (
        "Updated in r2 per Peer Requests 7, 9, 12: retracts Turn-1 review43 L62 pypdf base-site inference (under -I, base site-packages stays on sys.path so failure indicated user-site), binds explicit Stage-1a inventory of @base/Lib/site-packages, and replaces aggregate booleans with per-origin atoms."
    )

    # --- Request 6: Derive native.* D1/D2 strictly from live bound guard state; archive masks are reference only ---
    for pos in range(1445, 1450):
        for ph in ("C0_raw", "C1_post_rep", "C2_post_page"):
            nrow = by_orig[f"native.{pos}.{ph}"]
            old_masks = nrow["expected"].pop("expected_masks_on_f07_prefix")
            nrow["expected"]["live_mask_derivation_rule_req6"] = {
                "Ban_1_rep": "Derived at Stage 2 strictly from the live run's own bound token history via support(live_history, order=35, window=1024) — NEVER inferred from score vector effects or hardcoded from archive.",
                "Ban_2_page": "Derived at Stage 2 strictly from the live run's own bound page-guard state (marker_cum, page_len, expected_pages, max_page_tokens) via Edition A2 page_support().",
            }
            nrow["expected"]["historical_reference_distinct_from_pass_rule"]["archive_masks_reference_only"] = old_masks
            nrow["expected"]["historical_reference_distinct_from_pass_rule"]["archive_D1_scope_note"] = (
                "Standalone ZIP lacks F07.warm1.token_ids.json (effect-inferred only there); pinned Git e43af2e2 contains F07.warm1.token_ids.json (sha256 532ffea0...) yielding D1=[] across 2935 34-gram starts."
            )

    # Also update per-row native.{1445..1449}.support_choice for Request 6 & Claude's XP3 acceptance!
    for pos in range(1445, 1450):
        sc = by_ext[f"native.{pos}.support_choice"]
        sc["expected"].pop("D1_expected_on_f07", None)
        sc["expected"].pop("D2_expected_on_f07", None)
        sc["expected"]["live_mask_derivation_rule_req6"] = (
            "Ban_1 and Ban_2 derived strictly from live bound token history and live bound page-guard state; archive masks (D1=[], D2=[1]) are reference only."
        )
        sc["expected"]["P3_oob_status"] = (
            "X_oob (emitted not in Allow) accepted post-opening by eld-rd-reviewer (XP3) as peer-originated amendment; strict Paper I rev. 1 mode preserved separately in controls_r2.py."
        )

    # Update native.support_choice aggregate row similarly
    nsc = by_orig["native.support_choice"]
    nsc["expected"]["X_oob_status_post_opening"] = (
        "Accepted post-opening by eld-rd-reviewer as peer-originated amendment (XP3 = {score.oob, score.support}); strict rev. 1 P3 answer remains archived for rev. 1 text."
    )

    # --- Request 3: Update gate.stage1_to_stage2_bridge with explicit closed Delta(Pi_1, Plan_2) ---
    g12 = by_ext["gate.stage1_to_stage2_bridge"]
    g12["expected"]["bridge_delta_Delta_e1_e2"] = BRIDGE_DELTA_SCHEMA
    g12["alternatives_or_notes"] = (
        "Updated in r2 per Peer Request 3 (E-M09, E-I5): enumerates exact permitted Stage-1->2 deltas (CUDA_VISIBLE_DEVICES, PATH, debugger/PEB/heap/exception policy, entry files); any undeclared delta returns M."
    )

    # --- Request 9: Update cpu.stage1b.torch_import_and_dlls to emit per-module & per-DLL atoms ---
    s1b = by_ext["cpu.stage1b.torch_import_and_dlls"]
    s1b["expected"]["per_origin_atom_reporting_req9"] = (
        "Emit one keyed atom per imported module (module.<name>.origin) and per loaded DLL (dll.<name>.origin via LOAD_DLL_DEBUG_EVENT) rather than aggregate booleans."
    )

    # --- Update cpu.env.closed_allowlist_31 partition after Request 2 (13 named cpu.env.* + 18 grouped = 31) ---
    c31 = by_ext["cpu.env.closed_allowlist_31"]
    c31["expected"]["key_partition_check"] = {
        "named_cpu_env_13": sorted([
            "CUDA_DEVICE_ORDER", "CUDA_VISIBLE_DEVICES", "HF_HOME", "HF_HUB_OFFLINE",
            "HF_MODULES_CACHE", "PATH", "PYTHONDONTWRITEBYTECODE", "PYTHONHASHSEED",
            "PYTHONIOENCODING", "PYTHONNOUSERSITE", "PYTHONUNBUFFERED", "PYTHONUTF8",
            "TRANSFORMERS_OFFLINE",
        ]),
        "grouped_cache_and_os_18": c31["expected"]["key_partition_check"]["grouped_cache_and_os_18"],
    }
    assert len(c31["expected"]["key_partition_check"]["named_cpu_env_13"]) + len(
        c31["expected"]["key_partition_check"]["grouped_cache_and_os_18"]
    ) == 31

    # --- Add 8 NEW surgical extended obligations closing Requests 2, 7, and 10 (44 + 8 = 52 extended; 118 + 52 = 170 total) ---
    def append_ext(**kw: Any) -> None:
        item = {
            "index": len(extended),
            "earliest_stage": None,
            **kw,
        }
        extended.append(item)

    # 4 dedicated Stage-1a cpu.env.* rows (Request 2: split from Stage-2 exec.env.*)
    for ekey, eval_str, note in [
        ("HF_HUB_OFFLINE", "1", "Stage-1a rehearsal offline flag (distinct from Stage-2 exec.env.HF_HUB_OFFLINE)."),
        ("TRANSFORMERS_OFFLINE", "1", "Stage-1a rehearsal offline flag (distinct from Stage-2 exec.env.TRANSFORMERS_OFFLINE)."),
        ("PYTHONHASHSEED", "0", "Stage-1a rehearsal hash seed (paired with derived 18 sys.flags; distinct from Stage-2 exec.env.PYTHONHASHSEED)."),
        ("PYTHONNOUSERSITE", "1", "Stage-1a rehearsal user-site guard (paired with -s; distinct from Stage-2 exec.env.PYTHONNOUSERSITE)."),
    ]:
        append_ext(
            key=f"cpu.env.{ekey}",
            paper_clauses=["T2a", "T4", "T8"],
            direct_stock_stage="1a",
            subject=f"Stage-1a CPU rehearsal worker environment key {ekey} (e_launch and e_child)",
            cut="stage1a.cut1a_startup",
            type="tagged_env_presence_string",
            expected={"e_launch": {"state": "present", "value": eval_str}, "e_child": {"state": "present", "value": eval_str}},
            comparator="tagged_presence_and_exact_string",
            evidence_source="Stage-1a supervisor lpEnvironment + child os.environ snapshot",
            evidence_locator=f"prospective:@arm/cut1a-startup.json#/environment/{ekey}",
            historical_reference="docs/research/WP-0043/native.py#L194-L199",
            binding_status="bound",
            status="prospective_stage1a_bound",
            missing_precondition=["Stage-1a execution"],
            alternatives_or_notes=note,
        )

    # 1 Stage-1a @base/Lib/site-packages inventory obligation (Request 7)
    append_ext(
        key="static.venv.base_site_packages_inventory",
        paper_clauses=["T2a", "T1"],
        direct_stock_stage="1a",
        subject="Typed inventory of distributions in @base/Lib/site-packages (ABSENT if empty), verified excluded from direct-stock sys.path",
        cut="stage1a.cut1s_pre_launch_guard",
        type="typed_distribution_inventory_or_absent",
        expected={
            "record_all_distributions_in_base_site_packages": True,
            "typed_absent_if_empty": True,
            "must_be_excluded_from_child_sys_path": True,
        },
        comparator="typed_inventory_and_path_exclusion",
        evidence_source="Stage-1a supervisor read-only scan of @base/Lib/site-packages + child sys.path verification",
        evidence_locator="prospective:@run_root/preflight.json#/python/base_site_packages_inventory",
        historical_reference="docs/reviews/WP-0046/exchange/exchange.md#E-M01 (retracts mistaken review43 L62 base-site inference)",
        binding_status="bound",
        status="prospective_stage1a_bound",
        missing_precondition=["Stage-1a execution"],
        alternatives_or_notes="Added in r2 per Peer Request 7 (E-M01): replaces retracted review43 L62 witness with direct Stage-1a measurement.",
    )

    # 3 explicit named Stage-2 binding obligations (Request 10)
    for bkey, bsubj, bref, bdesc in [
        (
            "stage2.binding.infer_entry_resolution",
            "Formal Stage-2 binding resolving plan43 infer_multi vs worker43 L377 model.infer static conflict (S-04 / E-I4)",
            "docs/research/WP-0043/native.py#L377; docs/research/WP-0042/source-cuts.md#L20",
            "Preserves plan43 oplus worker43 M_static_plan on historical reference profile while binding target Stage-2 calls to model.infer(..., image_file=list(pages), return_dict=True, **kwargs).",
        ),
        (
            "stage2.binding.scorer_phase_local_fix",
            "Formal Stage-2 scorer binding replacing WP-0043/scorer.py L304 cumulative mask with phase-local D_2 + X_oob (S-08 / E-M05)",
            "docs/research/WP-0043/scorer.py#L243,L304",
            "Replaces `token not in allowed` at C2_post_page with phase-local `token not in page_allowed`, plus unconditional X_oob (XP3) and P7 Reading B.",
        ),
        (
            "stage2.binding.scorer_finiteness_fix",
            "Formal Stage-2 scorer binding adding attention_result, pre-sanitization router x, and valid bias to check_finite + empty-view offset bound 0<=b*o<=B_storage (S-08 / E-I8 / E-M06)",
            "docs/research/WP-0043/native_score.py#L532-L533; docs/research/WP-0043/transfer.py#L15-L16",
            "Fixes omissions verified independently by both providers at e43af2e2.",
        ),
    ]:
        append_ext(
            key=bkey,
            paper_clauses=["T5", "T6", "T8"],
            direct_stock_stage="2",
            subject=bsubj,
            cut="stage2.pre_admission_code_freeze",
            type="stage2_code_and_review_binding",
            expected={"requirement": bdesc, "frozen_commit_and_review": "UNBOUND_STAGE2"},
            comparator="frozen_source_sha256_and_rev2_signoff",
            evidence_source="Future Stage-2 frozen scorer/worker source commit + Rev_2 non-author review",
            evidence_locator=f"prospective:stage2_freeze#{bkey}",
            historical_reference=bref,
            binding_status="unbound_stage2",
            status="unbound_stage2_binding_obligation",
            missing_precondition=["Author, freeze, and independently review Stage-2 worker/scorer before Stage-2 admission"],
            alternatives_or_notes="Explicitly named Stage-2 binding obligation per Peer Request 10.",
        )

    # --- Apply Request 10 clean split of binding_status vs observation_status to ALL 170 obligations ---
    all_items = entries + extended
    assert len(entries) == 118
    assert len(extended) == 52
    assert len(all_items) == 170
    assert len({e["key"] for e in all_items}) == 170

    for item in all_items:
        b_st, o_st = _classify_statuses(item)
        item["binding_status"] = b_st
        item["observation_status"] = o_st

    # Compute exact scoped plan Pi_s counts using strict binding_status == "bound_static_rule"
    scoped_summary: dict[str, Any] = {}
    for idx, st in enumerate(STAGE_ORDER):
        in_stages = set(STAGE_ORDER[: idx + 1])
        pi_s = [e for e in all_items if e["direct_stock_stage"] in in_stages]
        outside_s = [e for e in all_items if e["direct_stock_stage"] not in in_stages]
        fully_bound = [e["key"] for e in pi_s if e["binding_status"] == "bound_static_rule"]
        pending_or_unbound_in_scope = sorted(e["key"] for e in pi_s if e["binding_status"] != "bound_static_rule")
        hard_unbound_in_scope = sorted(
            e["key"] for e in pi_s if e["binding_status"].startswith(("unbound_", "deferred_"))
        )
        deferred_pending_or_unbound = sorted(
            e["key"] for e in outside_s if e["binding_status"] != "bound_static_rule"
        )
        scoped_summary[f"Pi_{st}"] = {
            "included_stages": sorted(in_stages, key=STAGE_ORDER.index),
            "total_obligations": len(pi_s),
            "original_118_count": sum(1 for e in entries if e["direct_stock_stage"] in in_stages),
            "extended_52_count": sum(1 for e in extended if e["direct_stock_stage"] in in_stages),
            "bound_static_rule_count": len(fully_bound),
            "all_pending_or_unbound_in_scope_count": len(pending_or_unbound_in_scope),
            "all_pending_or_unbound_in_scope": pending_or_unbound_in_scope,
            "hard_unbound_in_scope_count": len(hard_unbound_in_scope),
            "hard_unbound_in_scope": hard_unbound_in_scope,
            "deferred_pending_or_unbound_count": len(deferred_pending_or_unbound),
        }

    return {
        "schema": "wp0046-direct-stock-register/3",
        "proposal_id": PROPOSAL_ID,
        "author": "eld-owner-probe",
        "provenance": {
            "turn1_independent_freeze": TURN1_FREEZE,
            "turn2_r1_freeze": TURN2_FREEZE,
            "peer_exchange_commit_verified": PEER_EXCHANGE_COMMIT,
            "reference_commit": REF_COMMIT,
            "attribution_note": "Minimal final Stage-0 supplement (r2) addressing all 12 numbered requests in peer exchange/exchange.md §4. Newly changed substantive r2 items require targeted non-author verification by eld-rd-reviewer.",
        },
        "status": "Stage 0 final supplement register (r2); 0 prospective target executions; Stage 1 HELD",
        "symbolic_roots": base["symbolic_roots"],
        "unknown_semantics": base["unknown_semantics"],
        "original_118_count": len(entries),
        "extended_obligations_count": len(extended),
        "total_obligations_count": len(all_items),
        "stage_counts_original_118": base["stage_counts_original_118"],
        "stage_counts_r2_original_118": {
            st: sum(1 for e in entries if e["direct_stock_stage"] == st) for st in STAGE_ORDER
        },
        "stage_counts_r2_extended_52": {
            st: sum(1 for e in extended if e["direct_stock_stage"] == st) for st in STAGE_ORDER
        },
        "stage_counts_r2_total_170": {
            st: sum(1 for e in all_items if e["direct_stock_stage"] == st) for st in STAGE_ORDER
        },
        "binding_status_counts_total_170": {
            bs: sum(1 for e in all_items if e["binding_status"] == bs)
            for bs in sorted({e["binding_status"] for e in all_items})
        },
        "observation_status_counts_total_170": {
            os_: sum(1 for e in all_items if e["observation_status"] == os_)
            for os_ in sorted({e["observation_status"] for e in all_items})
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
        raise ValueError(f"Host path leaked into register-r2: {m.group(0)!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify WP-0046 r2 direct-stock register.")
    parser.add_argument("--verify", action="store_true", help="Verify committed register-r2.json matches generator.")
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
            raise SystemExit("register-r2.json differs from deterministic generator output")
        sha = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
        print(
            json.dumps(
                {
                    "verified": True,
                    "original_118_count": manifest["original_118_count"],
                    "extended_obligations_count": manifest["extended_obligations_count"],
                    "total_obligations_count": manifest["total_obligations_count"],
                    "stage_counts_r2_total_170": manifest["stage_counts_r2_total_170"],
                    "binding_status_counts_total_170": manifest["binding_status_counts_total_170"],
                    "Pi_1a_hard_unbound": manifest["scoped_plan_summary"]["Pi_1a"]["hard_unbound_in_scope"],
                    "Pi_1a_all_pending_or_unbound": manifest["scoped_plan_summary"]["Pi_1a"]["all_pending_or_unbound_in_scope"],
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
