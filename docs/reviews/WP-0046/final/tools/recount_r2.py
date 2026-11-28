"""Independent recount of the peer's final register-r2.json from its named fields (data only).

Recomputes stage, binding_status and observation_status counts, the scoped-plan summaries
(Pi_s = rows whose direct_stock_stage is in the included stages), and placeholder-bearing
'bound_static_rule' rows. It cross-checks the 31-key allowlist against the worker43 env_for AST
and the 18 sys.flags names against prior0. Never executes peer code.
Usage: python -I recount_r2.py REGISTER_R2 BUNDLE_DIR
"""
import ast
import json
import re
import sys
from collections import Counter
from pathlib import Path

PLACEHOLDER = re.compile(r"<[a-z_]+>|exact_supervisor_os_value|MUST be bound|%SystemRoot%|TBD|to be bound", re.I)


def main(reg_path, bundle):
    r = json.load(open(reg_path, encoding="utf-8"))
    O, X = r["entries"], r["extended_obligations"]
    E = O + X
    out = {"n_original": len(O), "n_extended": len(X), "n_total": len(E), "unique_keys": len({e["key"] for e in E}) == len(E)}
    bundle_keys = [g["key"] for g in json.loads((Path(bundle) / "register.json").read_text(encoding="utf-8"))["groups"]]
    out["original_keys_equal_bundle_order"] = [e["key"] for e in O] == bundle_keys
    sc = lambda rows: dict(sorted(Counter(str(e["direct_stock_stage"]) for e in rows).items()))
    out["stage_counts"] = {"original": sc(O), "extended": sc(X), "total": sc(E)}
    out["binding_status"] = dict(sorted(Counter(e["binding_status"] for e in E).items()))
    out["observation_status"] = dict(sorted(Counter(e["observation_status"] for e in E).items()))
    out["observed_rows"] = sum(1 for e in E if not str(e["observation_status"]).startswith(("unobserved", "pending")))
    summ = r["scoped_plan_summary"]
    scopes = {}
    for name, s in summ.items():
        inc = set(s["included_stages"])
        ins = [e for e in E if str(e["direct_stock_stage"]) in inc]
        pend = sorted(e["key"] for e in ins if e["binding_status"] != "bound_static_rule")
        hard = sorted(e["key"] for e in ins if e["binding_status"].startswith("unbound"))
        outside = [e for e in E if str(e["direct_stock_stage"]) not in inc and e["binding_status"] != "bound_static_rule"]
        mine = {"total": len(ins), "bound_static_rule": len(ins) - len(pend), "pending_or_unbound": pend,
                "hard_unbound": hard, "deferred_non_bound_outside": len(outside)}
        claimed = {"total": s["total_obligations"], "bound_static_rule": s["bound_static_rule_count"],
                   "pending_or_unbound": sorted(s["all_pending_or_unbound_in_scope"]), "hard_unbound": sorted(s["hard_unbound_in_scope"]),
                   "deferred_non_bound_outside": s["deferred_pending_or_unbound_count"]}
        scopes[name] = {"recomputed": mine, "matches_claim": {k: mine[k] == claimed[k] for k in mine}}
    out["scopes"] = scopes
    ph = sorted(e["key"] for e in E if e["binding_status"] == "bound_static_rule" and PLACEHOLDER.search(json.dumps(e["expected"])))
    out["bound_rows_with_placeholder_text"] = ph
    by = {e["key"]: e for e in E}
    w = ast.parse((Path(bundle) / "sources/worker43.py").read_text(encoding="utf-8"))
    keys = set()
    for node in ast.walk(w):
        if isinstance(node, ast.FunctionDef) and node.name == "env_for":
            for n in ast.walk(node):
                if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "update":
                    keys |= {k.arg for k in n.keywords}
                if isinstance(n, ast.Tuple) and len(n.elts) > 3 and all(isinstance(x, ast.Constant) for x in n.elts):
                    keys |= {x.value for x in n.elts}
    allow = set(by["cpu.env.closed_allowlist_31"]["expected"]["exact_child_allowlist_31"])
    out["allowlist_equals_worker_env_for"] = allow == keys
    out["allowlist_n"] = len(allow)
    prior = json.loads((Path(bundle) / "sources/prior0.json").read_text(encoding="utf-8"))
    flags = by["cpu.hash_effective"]["expected"]["sys_flags_18_exact_typed"]
    out["flags_keys_equal_prior0"] = set(flags) == set(prior["reviewer"]["flags"]["direct"])
    out["flags_types"] = {k: type(v).__name__ for k, v in flags.items() if isinstance(v, bool)}
    out["exec_env_stage2"] = sum(1 for k, e in by.items() if k.startswith("exec.env.") and str(e["direct_stock_stage"]) == "2")
    out["cpu_env_rows"] = sorted(k for k in by if k.startswith("cpu.env."))
    nat = [e for e in O if e["key"].startswith("native.14")]
    out["native_masks_top_level_removed"] = sum(1 for e in nat if "expected_masks_on_f07_prefix" not in e["expected"])
    out["native_rows"] = len(nat)
    imp = json.dumps(by["cpu.import_resolution"]["expected"])
    out["import_resolution_still_has_aggregate_booleans"] = bool(re.search(r'"(base_site_packages_excluded|venv_site_packages_included|closed_33_distributions_verified)": true', imp))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:3])
