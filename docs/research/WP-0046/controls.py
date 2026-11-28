"""Finite executable stdlib controls for the WP-0046 direct-stock proposal.

Operates strictly on constructed JSON records. Performs no model/torch imports,
no subprocess launches, no filesystem attacks, no device access, and no network I/O.

Usage:
    python -I -B docs/research/WP-0046/controls.py --cases docs/research/WP-0046/control_cases.json
    python -I -B docs/research/WP-0046/controls.py --case path/to/single_case.json
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from struct import pack, unpack
import sys
from typing import Any

NINF = 0xFF800000
STAGE0_SOURCE_PIN = "e43af2e263f55478d1d551a5a095536b042589c2"


def strict_equal(a: Any, b: Any) -> bool:
    """Strict typed JSON equality: bool != int (False != 0, True != 1)."""
    if type(a) is not type(b):
        return False
    if isinstance(a, list):
        return len(a) == len(b) and all(strict_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(strict_equal(a[k], b[k]) for k in a)
    return a == b


def is_tagged(val: Any) -> bool:
    return isinstance(val, dict) and val.get("state") in ("present", "absent", "unobserved")


def check_strict_partial_order(nodes: set[str], edges: list[list[str]]) -> tuple[bool, str | None]:
    """Verify edges define an irreflexive, acyclic relation (returns ok, error_reason)."""
    adj: dict[str, set[str]] = {n: set() for n in nodes}
    for pair in edges:
        if not isinstance(pair, list) or len(pair) != 2 or not all(isinstance(x, str) for x in pair):
            return False, "malformed_order_edge"
        u, v = pair
        if u == v:
            return False, f"reflexive_order_edge:{u}"
        adj.setdefault(u, set()).add(v)
        adj.setdefault(v, set())
    # Kahn's algorithm for acyclicity over all referenced nodes
    indeg = {n: 0 for n in adj}
    for u, nbrs in adj.items():
        for v in nbrs:
            indeg[v] += 1
    queue = [n for n, d in indeg.items() if d == 0]
    visited = 0
    while queue:
        cur = queue.pop()
        visited += 1
        for nxt in adj[cur]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    if visited != len(adj):
        return False, "cyclic_order_relation"
    return True, None


def strict_minimal(events: set[str], edges: list[list[str]]) -> list[str]:
    """All minimal elements under transitive closure of strict order edges."""
    if not events:
        return []
    # Compute reachability to ensure transitivity on supplied Hasse/direct edges
    adj: dict[str, set[str]] = {}
    for u, v in edges:
        adj.setdefault(u, set()).add(v)
    ancestors: dict[str, set[str]] = {}
    for start in adj:
        seen: set[str] = set()
        stack = list(adj.get(start, ()))
        while stack:
            cur = stack.pop()
            if cur not in seen:
                seen.add(cur)
                stack.extend(adj.get(cur, ()))
        for target in seen:
            ancestors.setdefault(target, set()).add(start)
    mins = [e for e in events if not (ancestors.get(e, set()) & events)]
    return sorted(mins)


def make_return(
    *,
    case_id: str,
    subject: str,
    run: str,
    arm: str,
    stage: int,
    clause: str,
    cut: str,
    conflicts: list[dict[str, Any]],
    missing: list[dict[str, Any]],
    deferred: list[str],
    order_edges: list[list[str]],
    details: dict[str, Any],
) -> dict[str, Any]:
    conflict_keys = sorted({c["key"] for c in conflicts})
    missing_keys = sorted({m["key"] for m in missing})
    all_keys = set(conflict_keys) | set(missing_keys)
    ok_order, order_err = check_strict_partial_order(all_keys, order_edges)
    if not ok_order:
        conflicts = list(conflicts) + [
            {"key": "order.integrity", "class": "M_integrity", "reason": order_err}
        ]
        conflict_keys = sorted({c["key"] for c in conflicts})
        first_conflict = ["order.integrity"]
        first_finding = ["order.integrity"]
    else:
        first_conflict = strict_minimal(set(conflict_keys), order_edges)
        first_finding = strict_minimal(set(conflict_keys) | set(missing_keys), order_edges)

    classes = sorted({c.get("class", "M_field") for c in conflicts})
    verdict = "M" if conflicts else "U" if missing else "P"
    return {
        "case_id": case_id,
        "subject": subject,
        "run": run,
        "arm": arm,
        "stage": stage,
        "clause": clause,
        "cut": cut,
        "source_revision": STAGE0_SOURCE_PIN,
        "verdict": verdict,
        "conflict_classes": classes,
        "conflict_keys": conflict_keys,
        "missing_keys": missing_keys,
        "conflicts": sorted(conflicts, key=lambda x: (x["key"], x.get("reason", ""))),
        "missing": sorted(missing, key=lambda x: (x["key"], x.get("reason", ""))),
        "first_conflict": first_conflict,
        "first_finding": first_finding,
        "deferred": sorted(deferred),
        "details": details,
        "prospective_status": "constructed_offline_control_only",
    }


def eval_startup(case: dict[str, Any]) -> dict[str, Any]:
    """T2a amended startup/env/site/path control (strict int vs bool, e_launch vs e_child)."""
    inp = case["input"]
    expected = inp["expected"]
    observed = inp["observed"]
    conflicts: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    # 1. Tagged launch vs child environment checks
    for scope_name in ("e_launch", "e_child"):
        exp_env = expected.get(scope_name, {})
        obs_env = observed.get(scope_name)
        if not isinstance(obs_env, dict):
            missing.append({"key": f"env.{scope_name}", "reason": "environment_map_unobserved"})
            continue
        for k, exp_tag in sorted(exp_env.items()):
            obs_tag = obs_env.get(k)
            fkey = f"{scope_name}.{k}"
            if not is_tagged(obs_tag) or obs_tag["state"] == "unobserved":
                missing.append({"key": fkey, "reason": "env_key_unobserved"})
            elif not strict_equal(obs_tag, exp_tag):
                conflicts.append(
                    {"key": fkey, "class": "M_field", "reason": "env_mismatch", "expected": exp_tag, "observed": obs_tag}
                )

    # 2. Strict typed sys.flags checks (int vs bool preserved)
    exp_flags = expected.get("flags", {})
    obs_flags = observed.get("flags")
    if not isinstance(obs_flags, dict):
        missing.append({"key": "flags", "reason": "flags_unobserved"})
    else:
        for k, exp_v in sorted(exp_flags.items()):
            fkey = f"flags.{k}"
            obs_tag = obs_flags.get(k)
            if not is_tagged(obs_tag) or obs_tag["state"] == "unobserved":
                missing.append({"key": fkey, "reason": "flag_unobserved"})
            elif obs_tag["state"] != "present":
                conflicts.append({"key": fkey, "class": "M_field", "reason": "flag_absent", "expected": exp_v, "observed": obs_tag})
            elif not strict_equal(obs_tag.get("value"), exp_v):
                conflicts.append(
                    {"key": fkey, "class": "M_field", "reason": "flag_mismatch", "expected": exp_v, "observed": obs_tag.get("value")}
                )

    # 3. Prefix, executable, orig_argv0, site/path/root containment checks
    exp_paths = expected.get("resolution", {})
    obs_paths = observed.get("resolution")
    if not isinstance(obs_paths, dict):
        missing.append({"key": "resolution", "reason": "resolution_unobserved"})
    else:
        for k, exp_v in sorted(exp_paths.items()):
            fkey = f"resolution.{k}"
            obs_tag = obs_paths.get(k)
            if not is_tagged(obs_tag) or obs_tag["state"] == "unobserved":
                missing.append({"key": fkey, "reason": "resolution_field_unobserved"})
            elif obs_tag["state"] != "present":
                conflicts.append({"key": fkey, "class": "M_field", "reason": "resolution_field_absent", "expected": exp_v, "observed": obs_tag})
            elif not strict_equal(obs_tag.get("value"), exp_v):
                conflicts.append(
                    {"key": fkey, "class": "M_field", "reason": "resolution_mismatch", "expected": exp_v, "observed": obs_tag.get("value")}
                )

    return make_return(
        case_id=case["case_id"],
        subject=case.get("subject", "direct-stock CPU rehearsal child"),
        run=case.get("run", "constructed"),
        arm=case.get("arm", "arm-0"),
        stage=case.get("stage", 1),
        clause=case.get("clause", "T2a"),
        cut=case.get("cut", "stage1.cut1a_startup"),
        conflicts=conflicts,
        missing=missing,
        deferred=inp.get("deferred", []),
        order_edges=inp.get("order_edges", []),
        details={"checked_groups": ["e_launch", "e_child", "flags", "resolution"]},
    )


def eval_inventory(case: dict[str, Any]) -> dict[str, Any]:
    """T3/T3a amended inventory + continuity control: M dominates U even when read is missing."""
    inp = case["input"]
    conflicts: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    qr_auth = inp.get("qr_authenticated")
    if qr_auth is None:
        missing.append({"key": "inventory.qr_auth", "reason": "schedule_auth_unobserved"})
    elif qr_auth is not True:
        conflicts.append({"key": "inventory.qr_auth", "class": "M_integrity", "reason": "schedule_unauthenticated"})

    schema = inp.get("expected_keys")
    sealed = inp.get("sealed_keys")
    read = inp.get("read_keys")
    inv_custody = inp.get("inventory_custody")
    members = inp.get("members", {})

    if inv_custody is None:
        missing.append({"key": "inventory.custody", "reason": "inventory_custody_unobserved"})
    elif inv_custody is not True:
        conflicts.append({"key": "inventory.custody", "class": "M_integrity", "reason": "inventory_custody_failed"})

    if schema is None:
        missing.append({"key": "inventory.expected_keys", "reason": "expected_schema_unobserved"})
    elif not isinstance(schema, list) or len(set(schema)) != len(schema):
        conflicts.append({"key": "inventory.expected_keys", "class": "M_integrity", "reason": "duplicate_or_invalid_expected_keys"})

    if sealed is None:
        missing.append({"key": "inventory.sealed_keys", "reason": "sealed_inventory_unobserved"})
    elif not isinstance(sealed, list):
        conflicts.append({"key": "inventory.sealed_keys", "class": "M_integrity", "reason": "invalid_sealed_keys"})
    elif isinstance(schema, list) and Counter(schema) != Counter(sealed):
        conflicts.append(
            {
                "key": "inventory.sealed_membership",
                "class": "M_field",
                "reason": "sealed_inventory_mismatch_against_expected",
                "missing_from_sealed": sorted(set(schema) - set(sealed)),
                "extra_in_sealed": sorted(set(sealed) - set(schema)),
            }
        )

    if read is None:
        missing.append({"key": "inventory.read_keys", "reason": "scorer_read_sequence_unobserved"})
    elif not isinstance(read, list):
        conflicts.append({"key": "inventory.read_keys", "class": "M_integrity", "reason": "invalid_read_keys"})
    else:
        if isinstance(sealed, list) and Counter(read) != Counter(sealed):
            conflicts.append(
                {
                    "key": "inventory.read_vs_sealed",
                    "class": "M_field",
                    "reason": "read_multiset_differs_from_sealed",
                }
            )
        if isinstance(schema, list) and Counter(read) != Counter(schema):
            conflicts.append(
                {
                    "key": "inventory.read_vs_expected",
                    "class": "M_field",
                    "reason": "read_multiset_differs_from_expected",
                }
            )

    # Per-member keyed custody and physical-object uniqueness
    seen_physical: dict[str, str] = {}
    if isinstance(schema, list):
        for k in schema:
            mrec = members.get(k)
            if not isinstance(mrec, dict):
                missing.append({"key": f"member.{k}.record", "reason": "member_custody_unobserved"})
                continue
            for field in ("writer_ok", "bound_write", "seal_ok", "handle_covers_interval", "share_excludes_write_delete", "scorer_share_read_only", "object_id_match", "digest_match"):
                val = mrec.get(field)
                if val is None:
                    missing.append({"key": f"member.{k}.{field}", "reason": "custody_term_unobserved"})
                elif val is not True:
                    conflicts.append({"key": f"member.{k}.{field}", "class": "M_field", "reason": f"custody_failed:{field}"})
            phys = mrec.get("physical_object_id")
            if phys is None:
                missing.append({"key": f"member.{k}.physical_object_id", "reason": "physical_object_id_unobserved"})
            else:
                pkey = json.dumps(phys, sort_keys=True)
                if pkey in seen_physical:
                    conflicts.append(
                        {
                            "key": f"member.{k}.physical_uniqueness",
                            "class": "M_integrity",
                            "reason": f"shared_physical_object_with:{seen_physical[pkey]}",
                        }
                    )
                else:
                    seen_physical[pkey] = k

    return make_return(
        case_id=case["case_id"],
        subject=case.get("subject", "arm member inventory"),
        run=case.get("run", "constructed"),
        arm=case.get("arm", "arm-0"),
        stage=case.get("stage", 1),
        clause=case.get("clause", "T3/T3a"),
        cut=case.get("cut", "stage1.seal_through_scorer_read"),
        conflicts=conflicts,
        missing=missing,
        deferred=inp.get("deferred", []),
        order_edges=inp.get("order_edges", []),
        details={"expected_count": len(schema) if isinstance(schema, list) else None},
    )


def _valid_u32(w: Any) -> bool:
    return type(w) is int and 0 <= w <= 0xFFFFFFFF


def eval_score_phase(case: dict[str, Any]) -> dict[str, Any]:
    """T5 amended Eq. (8): phase-local supplied predecessor, X_oob decoupled, partial-phase missingness."""
    inp = case["input"]
    size = inp["vocab_size"]
    raw = inp.get("raw")
    rep = inp.get("rep")
    page = inp.get("page")
    mask1 = set(inp["mask1"]) if inp.get("mask1") is not None else None
    mask2 = set(inp["mask2"]) if inp.get("mask2") is not None else None
    emitted = inp.get("emitted")  # tagged {"state": ...}

    conflicts: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    def check_vec(name: str, vec: Any) -> list[int] | None:
        if vec is None:
            missing.append({"key": f"score.{name}", "reason": "phase_vector_unobserved"})
            return None
        if not isinstance(vec, list) or len(vec) != size or not all(_valid_u32(x) for x in vec):
            conflicts.append({"key": f"score.{name}", "class": "M_integrity", "reason": "invalid_vector_schema_or_word"})
            return None
        return vec

    raw_v = check_vec("raw", raw)
    rep_v = check_vec("rep", rep)
    page_v = check_vec("page", page)

    if mask1 is None:
        missing.append({"key": "score.mask1", "reason": "rep_mask_unobserved"})
    elif mask1 - set(range(size)):
        conflicts.append({"key": "score.mask1", "class": "M_integrity", "reason": "mask1_out_of_vocab"})
        mask1 = None

    if mask2 is None:
        missing.append({"key": "score.mask2", "reason": "page_mask_unobserved"})
    elif mask2 - set(range(size)):
        conflicts.append({"key": "score.mask2", "class": "M_integrity", "reason": "mask2_out_of_vocab"})
        mask2 = None

    score_phase_faults = False
    if raw_v is not None:
        for j, w in enumerate(raw_v):
            if (w & 0x7F800000) == 0x7F800000:
                score_phase_faults = True
                conflicts.append({"key": f"raw.{j}", "class": "M_field", "reason": "raw_nonfinite", "word_hex": f"{w:08x}"})

    if raw_v is not None and rep_v is not None and mask1 is not None:
        for j in range(size):
            want = NINF if j in mask1 else raw_v[j]
            if rep_v[j] != want:
                score_phase_faults = True
                conflicts.append(
                    {"key": f"rep.{j}", "class": "M_field", "reason": "phase_local_rep_mismatch", "expected_hex": f"{want:08x}", "observed_hex": f"{rep_v[j]:08x}"}
                )

    if rep_v is not None and page_v is not None and mask2 is not None:
        for j in range(size):
            want = NINF if j in mask2 else rep_v[j]
            if page_v[j] != want:
                score_phase_faults = True
                conflicts.append(
                    {"key": f"page.{j}", "class": "M_field", "reason": "phase_local_page_mismatch", "expected_hex": f"{want:08x}", "observed_hex": f"{page_v[j]:08x}"}
                )

    allowed: list[int] | None = None
    if mask1 is not None and mask2 is not None:
        allowed = sorted(set(range(size)) - mask1 - mask2)
        if not allowed:
            conflicts.append({"key": "score.support", "class": "M_field", "reason": "empty_support"})

    emitted_val: Any = None
    emitted_present = False
    if not is_tagged(emitted) or emitted["state"] == "unobserved":
        missing.append({"key": "score.emission", "reason": "emission_unobserved"})
    elif emitted["state"] != "present":
        conflicts.append({"key": "score.emission", "class": "M_field", "reason": "emission_absent"})
    else:
        emitted_present = True
        emitted_val = emitted.get("value")

    # X_oob: decidable whenever A and y_obs are observed, independent of empty support or score faults!
    if emitted_present and allowed is not None:
        if type(emitted_val) is not int or emitted_val not in allowed:
            conflicts.append(
                {"key": "score.oob", "class": "M_field", "reason": "emitted_outside_support", "observed": emitted_val}
            )

    qualified_winner: int | None = None
    if allowed and raw_v is not None and rep_v is not None and page_v is not None and not score_phase_faults:
        winner = max(allowed, key=lambda j: unpack(">f", pack(">I", page_v[j]))[0])
        if emitted_present:
            if emitted_val != winner:
                conflicts.append(
                    {"key": "score.winner", "class": "M_field", "reason": "winner_mismatch", "expected": winner, "observed": emitted_val}
                )
            elif not conflicts and not missing:
                qualified_winner = winner

    return make_return(
        case_id=case["case_id"],
        subject=case.get("subject", "F07.warm1 observed score row"),
        run=case.get("run", "constructed"),
        arm=case.get("arm", "observed"),
        stage=case.get("stage", 2),
        clause=case.get("clause", "T5 Eq. (8)"),
        cut=case.get("cut", "stage2.decoded_score_row"),
        conflicts=conflicts,
        missing=missing,
        deferred=inp.get("deferred", []),
        order_edges=inp.get("order_edges", []),
        details={"allowed": allowed, "qualified_winner": qualified_winner},
    )


def eval_crosswalk_and_diagnostics(case: dict[str, Any]) -> dict[str, Any]:
    """T4 amended Eq. (6) precedence + strict typing + strict partial-order minimal sets."""
    inp = case["input"]
    crosswalk_out: dict[str, str] = {}
    conflicts: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    for row in inp.get("comparisons", []):
        k = row["key"]
        jk = row["J_k"]  # 0, 1, or "unobserved"
        left = row["left"]
        right = row["right"]
        if jk == 0 and type(jk) is int:
            crosswalk_out[k] = "incomparable"
            continue
        if jk == "unobserved" or (not is_tagged(left) or left["state"] == "unobserved") or (not is_tagged(right) or right["state"] == "unobserved"):
            crosswalk_out[k] = "unobserved"
            if row.get("mandatory", False):
                missing.append({"key": k, "reason": "unobserved_comparison"})
            continue
        if strict_equal(left, right):
            crosswalk_out[k] = "same"
        else:
            crosswalk_out[k] = "different"
            if row.get("mandatory", False):
                conflicts.append({"key": k, "class": "M_field", "reason": "value_or_type_difference", "left": left, "right": right})

    for extra_c in inp.get("extra_conflicts", []):
        conflicts.append(extra_c)
    for extra_m in inp.get("extra_missing", []):
        missing.append(extra_m)

    return make_return(
        case_id=case["case_id"],
        subject=case.get("subject", "crosswalk and diagnostics"),
        run=case.get("run", "constructed"),
        arm=case.get("arm", "arm-0"),
        stage=case.get("stage", 0),
        clause=case.get("clause", "T4 Eqs. (6)-(7)"),
        cut=case.get("cut", "stage0.crosswalk_and_scorer"),
        conflicts=conflicts,
        missing=missing,
        deferred=inp.get("deferred", []),
        order_edges=inp.get("order_edges", []),
        details={"crosswalk": crosswalk_out},
    )


def eval_assess(case: dict[str, Any]) -> dict[str, Any]:
    """T8 amended ASSESS(): static conflicts before deferral, stage-scoped B_required, tagged origins."""
    inp = case["input"]
    stage = inp["stage"]
    scope_stages = set(inp.get("required_binding_stages", [0, stage]))
    conflicts: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    deferred: list[str] = []

    for atom in inp["atoms"]:
        key = atom["key"]
        due = atom["due_stage"]
        prescriptions = atom["prescriptions"]  # list of tagged {"state":"present","values":[...]} or {"state":"unobserved"}
        observed = atom.get("observed", {"state": "unobserved"})

        # Step 1: Static consistency runs at ALL stages BEFORE deferral!
        known_sets: list[list[Any]] = []
        has_missing_prescription = False
        for p in prescriptions:
            if not is_tagged(p) or p["state"] == "unobserved":
                has_missing_prescription = True
            elif p["state"] == "present":
                known_sets.append(p["values"])
        if not known_sets or has_missing_prescription:
            if due in scope_stages or atom.get("in_scope_binding", False):
                missing.append({"key": key, "reason": "missing_static_binding"})
        intersection: list[Any] | None = None
        if known_sets:
            # Strict typed intersection preserving int != bool
            inter = list(known_sets[0])
            for nxt in known_sets[1:]:
                inter = [v for v in inter if any(strict_equal(v, w) for w in nxt)]
            intersection = inter
            if len(intersection) == 0:
                conflicts.append({"key": key, "class": "M_static_plan", "reason": "incompatible_static_prescriptions"})

        # Step 2: Deferral check for runtime observation ONLY
        if due > stage:
            deferred.append(key)
            continue

        # Step 3: Due runtime observation check
        if not is_tagged(observed) or observed["state"] == "unobserved":
            missing.append({"key": key, "reason": "missing_due_receipt"})
        elif intersection is not None and not any(strict_equal(observed, allowed_v) for allowed_v in intersection):
            conflicts.append({"key": key, "class": "M_field", "reason": "runtime_value_mismatch", "observed": observed})

    return make_return(
        case_id=case["case_id"],
        subject=case.get("subject", "scoped plan assessment"),
        run=case.get("run", "constructed"),
        arm=case.get("arm", "plan"),
        stage=stage,
        clause=case.get("clause", "T8 Eq. (11) amended"),
        cut=case.get("cut", f"stage{stage}.assess"),
        conflicts=conflicts,
        missing=missing,
        deferred=deferred,
        order_edges=inp.get("order_edges", []),
        details={"scope_stages": sorted(scope_stages)},
    )


def eval_replay_gate(case: dict[str, Any]) -> dict[str, Any]:
    """T8a amended Eq. (12) and J_5(r, R_cand): same-run 5-row bijection + P_3 + Rev_3."""
    inp = case["input"]
    target_run = inp["run_id"]
    stock_verdicts = inp["stock_verdicts"]  # {run_id: "P"|"M"|"U"}
    rows = inp["candidate_rows"]
    required_keys = [
        ("observed", "F07.warm1", p) for p in range(1445, 1450)
    ]
    p3 = inp.get("P3_complete_and_consistent")
    rev3 = inp.get("Rev3_independently_reviewed")

    conflicts: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    if p3 is None:
        missing.append({"key": "gate.P3", "reason": "stage3_plan_status_unobserved"})
    elif p3 is not True:
        conflicts.append({"key": "gate.P3", "class": "M_static_plan", "reason": "stage3_plan_incomplete_or_inconsistent"})

    if rev3 is None:
        missing.append({"key": "gate.Rev3", "reason": "stage3_review_status_unobserved"})
    elif rev3 is not True:
        conflicts.append({"key": "gate.Rev3", "class": "M_field", "reason": "stage3_design_unreviewed"})

    sv = stock_verdicts.get(target_run)
    if sv is None:
        missing.append({"key": "gate.V_stock", "reason": "stock_run_verdict_unobserved"})
    elif sv == "U":
        missing.append({"key": "gate.V_stock", "reason": "stock_run_unresolved"})
    elif sv != "P":
        conflicts.append({"key": "gate.V_stock", "class": "M_field", "reason": f"stock_run_not_passing:{sv}"})

    observed_tuples: list[tuple[Any, Any, Any]] = []
    for idx, row in enumerate(rows):
        key_tuple = (row.get("arm"), row.get("call"), row.get("position"))
        observed_tuples.append(key_tuple)
        pos_label = row.get("position", f"idx{idx}")
        if row.get("run") != target_run:
            conflicts.append(
                {"key": f"row.{pos_label}.run_join", "class": "M_field", "reason": f"cross_run_row:{row.get('run')}!={target_run}"}
            )
        if row.get("original_bound") is None:
            missing.append({"key": f"row.{pos_label}.original_bound", "reason": "original_binding_unobserved"})
        elif row.get("original_bound") is not True:
            conflicts.append({"key": f"row.{pos_label}.original_bound", "class": "M_field", "reason": "original_not_bound"})
        if row.get("restorable") is None:
            missing.append({"key": f"row.{pos_label}.restorable", "reason": "restorability_unobserved"})
        elif row.get("restorable") is not True:
            conflicts.append({"key": f"row.{pos_label}.restorable", "class": "M_field", "reason": "snapshot_not_restorable"})

    if Counter(observed_tuples) != Counter(required_keys):
        conflicts.append(
            {
                "key": "gate.J5_multiplicity",
                "class": "M_field",
                "reason": "row_key_multiset_not_bijection_with_K",
                "observed_count": len(observed_tuples),
                "unique_observed_count": len(set(observed_tuples)),
            }
        )

    consider_private_replay = (len(conflicts) == 0 and len(missing) == 0)
    return make_return(
        case_id=case["case_id"],
        subject=case.get("subject", "Stage-2 to Stage-3 private replay eligibility gate"),
        run=target_run,
        arm="observed",
        stage=case.get("stage", 2),
        clause=case.get("clause", "T8a Eq. (12)"),
        cut=case.get("cut", "stage2.post_stock_qualification_gate"),
        conflicts=conflicts,
        missing=missing,
        deferred=inp.get("deferred", ["private.parity"]),
        order_edges=inp.get("order_edges", []),
        details={"consider_private_replay": consider_private_replay, "execute_stage3": False},
    )


DISPATCH = {
    "startup": eval_startup,
    "inventory": eval_inventory,
    "score_phase": eval_score_phase,
    "crosswalk_diagnostics": eval_crosswalk_and_diagnostics,
    "assess": eval_assess,
    "replay_gate": eval_replay_gate,
}


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    kind = case["kind"]
    if kind not in DISPATCH:
        raise ValueError(f"Unknown control kind: {kind}")
    return DISPATCH[kind](case)


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute WP-0046 constructed offline proposal controls.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--cases", type=Path, help="Path to batch constructed control cases JSON.")
    group.add_argument("--case", type=Path, help="Path to a single constructed control case JSON.")
    parser.add_argument("--out", type=Path, help="Optional output path for JSON results.")
    args = parser.parse_args()

    if args.case is not None:
        case = json.loads(args.case.read_text(encoding="utf-8"))
        actual = evaluate_case(case)
        text = json.dumps(actual, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
        if args.out is not None:
            args.out.write_text(text, encoding="utf-8", newline="\n")
        else:
            sys.stdout.write(text)
        return 0

    bundle = json.loads(args.cases.read_text(encoding="utf-8"))
    results = []
    mismatches = []
    for case in bundle["cases"]:
        actual = evaluate_case(case)
        expected = case.get("expected_return")
        matched = strict_equal(actual, expected) if expected is not None else None
        if matched is False:
            mismatches.append({"case_id": case["case_id"], "expected": expected, "actual": actual})
        results.append({"case_id": case["case_id"], "kind": case["kind"], "verdict": actual["verdict"], "matched_expected": matched, "result": actual})

    summary = {
        "schema": "wp0046-control-results/1",
        "source_revision": STAGE0_SOURCE_PIN,
        "cases_total": len(results),
        "verdict_counts": dict(sorted(Counter(r["verdict"] for r in results).items())),
        "expected_matches": sum(1 for r in results if r["matched_expected"] is True),
        "expected_mismatches": len(mismatches),
        "results": results,
    }
    text = json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if args.out is not None:
        args.out.write_text(text, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(text)
    if mismatches:
        sys.stderr.write(f"MISMATCHES: {[m['case_id'] for m in mismatches]}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
