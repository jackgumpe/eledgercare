"""Final r2 stdlib offline control evaluator for WP-0046 Stage 0 reconciliation.

Standard library only. Operates strictly on inert constructed JSON records.
Zero model/torch/stock imports, zero subprocess launches, zero host probes,
zero device access, and zero network I/O.

Fixes ALL FOUR Turn-1 controls.py defects identified by eld-rd-reviewer
(commit ee07ca660286927ba5017a5592d2f8bed3a8d702, exchange/exchange.md §4):
  - XC1: eval_startup enforces closed-world environment closure on both e_launch
         and e_child (any unlisted present/non-absent key emits M conflict).
  - XC2: eval_inventory evaluates per-member custody and physical uniqueness
         even when expected_keys (schema) is unobserved (None), over sealed_keys.
  - XC3: eval_assess defaults required_binding_stages to list(range(0, stage + 1))
         so due stage-1 unbound atoms are never dropped at stage >= 2.
  - XC4: eval_inventory enforces ordered read projection when inp.get("ordered")
         is True (emitting M conflict inventory.read_order on reversed reads).

Also adds:
  - Stage-1->2 explicit Delta(e1, e2) bridge evaluator (`kind == "bridge_delta"`).
  - Direct verification adapters for:
      * Owner's 16 frozen Turn-1 cases (`--cases control_cases.json`),
      * Peer's 27 peer-schema cases (`--cases peer-schema-cases.json`),
      * Peer's 49 Turn-1 challenges (`--claude-cases cases.json`),
      * Peer's 3 R-01 order-integrity cases (`--claude-r1-cases cases-r1.json`).
"""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
from struct import pack, unpack
import sys
from typing import Any

HERE = Path(__file__).resolve().parent
NINF = 0xFF800000
STAGE0_SOURCE_PIN = "e43af2e263f55478d1d551a5a095536b042589c2"


def strict_equal(a: Any, b: Any) -> bool:
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
    adj: dict[str, set[str]] = {n: set() for n in nodes}
    for pair in edges:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2 or not all(isinstance(x, str) for x in pair):
            return False, "malformed_order_edge"
        u, v = pair
        if u == v:
            return False, f"reflexive_order_edge:{u}"
        adj.setdefault(u, set()).add(v)
        adj.setdefault(v, set())
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
    if not events:
        return []
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
    return sorted(e for e in events if not (ancestors.get(e, set()) & events))


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


def eval_startup_r2(case: dict[str, Any]) -> dict[str, Any]:
    """T2a amended startup control: strict int!=bool AND closed-world env closure (fixes XC1)."""
    inp = case["input"]
    expected = inp["expected"]
    observed = inp["observed"]
    conflicts: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    # 1. Closed-world tagged launch vs child environment checks (fixes XC1!)
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
        # Closed-world check: any key present in obs_env but NOT listed in exp_env MUST be absent!
        for k in sorted(set(obs_env) - set(exp_env)):
            obs_tag = obs_env[k]
            fkey = f"{scope_name}.{k}"
            if not is_tagged(obs_tag) or obs_tag["state"] == "unobserved":
                missing.append({"key": fkey, "reason": "unlisted_env_key_unobserved"})
            elif obs_tag["state"] != "absent":
                conflicts.append(
                    {
                        "key": fkey,
                        "class": "M_field",
                        "reason": "unlisted_env_key_present_violates_closure",
                        "expected": {"state": "absent"},
                        "observed": obs_tag,
                    }
                )

    # 2. Strict typed sys.flags checks (int != bool)
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


def eval_inventory_r2(case: dict[str, Any]) -> dict[str, Any]:
    """T3/T3a amended M3 control: evaluates custody without schema (fixes XC2) and ordered projection (fixes XC4)."""
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
        if isinstance(sealed, list) and inp.get("ordered") and Counter(read) == Counter(sealed) and list(read) != list(sealed):
            # Fixes XC4: order-sensitive projection check
            conflicts.append(
                {
                    "key": "inventory.read_order",
                    "class": "M_field",
                    "reason": "ordered_read_sequence_differs_from_sealed",
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

    # Per-member keyed custody and physical-object uniqueness:
    # Evaluates over schema when schema is observed, OR over sealed when schema is missing (fixes XC2!)
    member_scope: list[str] = []
    if isinstance(schema, list):
        member_scope = list(dict.fromkeys(schema))
    elif isinstance(sealed, list):
        member_scope = list(dict.fromkeys(sealed))

    seen_physical: dict[str, str] = {}
    for k in member_scope:
        mrec = members.get(k)
        if not isinstance(mrec, dict):
            missing.append({"key": f"member.{k}.record", "reason": "member_custody_unobserved"})
            continue
        for field in (
            "writer_ok", "bound_write", "seal_ok", "handle_covers_interval",
            "share_excludes_write_delete", "scorer_share_read_only", "object_id_match", "digest_match",
        ):
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


def eval_assess_r2(case: dict[str, Any]) -> dict[str, Any]:
    """T8 amended ASSESS(): static conflicts before deferral, default scope 0..s (fixes XC3)."""
    inp = case["input"]
    stage = inp["stage"]
    # Fixes XC3: default required_binding_stages covers ALL stages 0..stage!
    scope_stages = set(inp.get("required_binding_stages", list(range(0, stage + 1))))
    conflicts: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    deferred: list[str] = []

    for atom in inp["atoms"]:
        key = atom["key"]
        due = atom["due_stage"]
        prescriptions = atom["prescriptions"]
        observed = atom.get("observed", {"state": "unobserved"})

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
            inter = list(known_sets[0])
            for nxt in known_sets[1:]:
                inter = [v for v in inter if any(strict_equal(v, w) for w in nxt)]
            intersection = inter
            if len(intersection) == 0:
                conflicts.append({"key": key, "class": "M_static_plan", "reason": "incompatible_static_prescriptions"})

        if due > stage:
            deferred.append(key)
            continue

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


def eval_bridge_delta(case: dict[str, Any]) -> dict[str, Any]:
    """T8a Eq. (12) Stage-1->2 explicit Delta(e1, e2) bridge control (Peer Request 3; G1, G2, E-I5)."""
    inp = case["input"]
    pre = inp["preflight"]
    s2 = inp["stage2"]
    declared_deltas = set(inp.get("declared_deltas", []))
    conflicts: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    if pre.get("verdict") != "P":
        conflicts.append({"key": "bridge.preflight_verdict", "class": "M_field", "reason": f"preflight_not_P:{pre.get('verdict')}"})
    if inp.get("Plan_2") is not True:
        conflicts.append({"key": "bridge.Plan_2", "class": "M_static_plan", "reason": "stage2_plan_incomplete"})
    if inp.get("Rev_2") is not True:
        conflicts.append({"key": "bridge.Rev_2", "class": "M_field", "reason": "stage2_unreviewed"})

    all_keys = sorted(set(pre.get("projection", {})) | set(s2.get("projection", {})))
    for k in all_keys:
        v1 = pre.get("projection", {}).get(k, {"state": "unobserved"})
        v2 = s2.get("projection", {}).get(k, {"state": "unobserved"})
        if v1 == {"state": "unobserved"} or v2 == {"state": "unobserved"}:
            missing.append({"key": f"bridge.{k}", "reason": "projection_field_unobserved"})
        elif not strict_equal(v1, v2) and k not in declared_deltas:
            conflicts.append(
                {
                    "key": f"bridge.{k}",
                    "class": "M_field",
                    "reason": "undeclared_stage1_to_stage2_delta",
                    "stage1": v1,
                    "stage2": v2,
                }
            )
    return make_return(
        case_id=case["case_id"],
        subject="Stage-1 to Stage-2 Delta(e1, e2) bridge",
        run=case.get("run", "constructed"),
        arm="bridge",
        stage=2,
        clause="T8a Eq. (12) M2 Delta(e1, e2)",
        cut="stage2.pre_admission_bridge",
        conflicts=conflicts,
        missing=missing,
        deferred=[],
        order_edges=[],
        details={"joined": len(conflicts) == 0 and len(missing) == 0, "declared_deltas": sorted(declared_deltas)},
    )


def _load_mod(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def evaluate_owner_or_peer_schema_case(case: dict[str, Any], turn1_mod: Any) -> dict[str, Any]:
    kind = case["kind"]
    if kind == "startup":
        return eval_startup_r2(case)
    if kind == "inventory":
        return eval_inventory_r2(case)
    if kind == "assess":
        return eval_assess_r2(case)
    if kind == "bridge_delta":
        return eval_bridge_delta(case)
    if kind in ("score_phase", "crosswalk_diagnostics", "replay_gate"):
        return turn1_mod.evaluate_case(case)
    raise ValueError(f"Unknown case kind: {kind}")


def eval_claude_r1_minimal(inp: dict[str, Any]) -> dict[str, Any]:
    """Independent verification of Claude's R-01 order-integrity cases (D6r1, D7, D8)."""
    events = set(inp["events"])
    edges = [list(p) for p in inp["precedes"]]
    if any(a == b for a, b in edges):
        return {"minimal": None, "order_integrity": "reflexive"}
    ok, err = check_strict_partial_order(events, edges)
    if not ok:
        return {"minimal": None, "order_integrity": "cyclic" if err == "cyclic_order_relation" else err}
    return {"minimal": strict_minimal(events, edges), "order_integrity": None}


def main() -> int:
    parser = argparse.ArgumentParser(description="WP-0046 final r2 offline controls evaluator.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--cases", type=Path, help="Batch JSON in owner/peer-schema format (control_cases.json or peer-schema-cases.json).")
    group.add_argument("--claude-r1-cases", type=Path, help="Claude exchange/corrections/cases-r1.json.")
    group.add_argument("--claude-cases", type=Path, help="Claude challenges/cases.json (49 cases).")
    parser.add_argument("--claude-expected", type=Path, default=None, help="Optional expected JSON for --claude-cases or --claude-r1-cases.")
    parser.add_argument("--out", type=Path, default=None, help="Optional output JSON path.")
    args = parser.parse_args()

    if args.cases is not None:
        turn1 = _load_mod("_wp46_t1_ctrl", "controls.py")
        bundle = json.loads(args.cases.read_text(encoding="utf-8"))
        results = []
        mismatches = []
        for c in bundle["cases"]:
            actual = evaluate_owner_or_peer_schema_case(c, turn1)
            expected = c.get("expected_return")
            matched = strict_equal(actual, expected) if expected is not None else None
            if matched is False:
                mismatches.append(c["case_id"])
            results.append(
                {
                    "case_id": c["case_id"],
                    "kind": c["kind"],
                    "verdict": actual["verdict"],
                    "matched_expected": matched,
                    "result": actual,
                }
            )
        payload: dict[str, Any] = {
            "schema": "wp0046-control-r2-results/1",
            "source_revision": STAGE0_SOURCE_PIN,
            "cases_total": len(results),
            "verdict_counts": dict(sorted(Counter(r["verdict"] for r in results).items())),
            "expected_matches": sum(1 for r in results if r["matched_expected"] is True),
            "expected_mismatches": len(mismatches),
            "mismatch_ids": mismatches,
            "results": results,
        }
        exit_code = 0 if not mismatches else 1
    elif args.claude_r1_cases is not None:
        cases = json.loads(args.claude_r1_cases.read_text(encoding="utf-8"))["cases"]
        exp = json.loads(args.claude_expected.read_text(encoding="utf-8"))["cases"] if args.claude_expected else None
        out_map = {c["id"]: eval_claude_r1_minimal(c["input"]) for c in cases}
        agree = sum(1 for cid, val in out_map.items() if exp is not None and strict_equal(val, exp[cid])) if exp else None
        payload = {
            "schema": "wp0046-control-r2-claude-r1/1",
            "source_revision": STAGE0_SOURCE_PIN,
            "cases_total": len(cases),
            "agreements_vs_expected_r1": agree,
            "cases": out_map,
        }
        exit_code = 0 if (exp is None or agree == len(cases)) else 1
    else:
        r1_ctrl = _load_mod("_wp46_r1_ctrl", "controls_r1.py")
        payload = r1_ctrl.run_claude_suite(args.claude_cases, args.claude_expected)
        strict = payload["modes"]["paper-r1-strict"]
        exit_code = 0 if (
            strict["full_record_agreements_vs_peer_expected"] is None
            or strict["full_record_agreements_vs_peer_expected"] == payload["cases_total"]
        ) else 1

    rendered = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if args.out is not None:
        args.out.write_text(rendered, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(rendered)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
