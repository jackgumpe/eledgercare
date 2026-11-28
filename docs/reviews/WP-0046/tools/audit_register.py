"""Register and pinned-source audit for WP-0046 (reviewer tool).

Reads register.json and sources/ of an extracted bundle. Parses worker43.py with
ast only (never imports or executes it). Prints a JSON summary containing keys,
counts, booleans and source line numbers; no host paths or file contents.
Usage: python -I audit_register.py BUNDLE_DIR
"""
import ast
import json
import re
import sys
from collections import Counter
from pathlib import Path


def main(bundle):
    B = Path(bundle)
    load = lambda n: json.loads((B / "sources" / n).read_text(encoding="utf-8"))
    reg = json.loads((B / "register.json").read_text(encoding="utf-8"))["groups"]
    plan, inputs, src, win, dev = (load(n) for n in ("plan43.json", "inputs43.json", "source41.json", "windows45.json", "device43.json"))
    out = {"entries": len(reg), "by_stage": dict(sorted(Counter(r["earliest_stage"] for r in reg).items())),
           "unique_keys": len({r["key"] for r in reg}) == len(reg)}
    kinds = Counter()
    for r in reg:
        e = r["expected"]
        kinds["pointer" if isinstance(e, dict) and "pointer" in e else "relation_text" if isinstance(e, dict) and "relation" in e
              else "bind_placeholder" if isinstance(e, dict) and "bind_before_review" in e else "literal"] += 1
    out["expected_kinds"] = dict(kinds)
    out["bind_placeholders"] = sorted(r["key"] for r in reg if isinstance(r["expected"], dict) and "bind_before_review" in r["expected"])

    # Literal 'historical' references: file tokens and JSON pointers.
    files = {p.name for p in (B / "sources").iterdir()}
    tok_ok, tok_bad, nonfile, ptr_ok, ptr_bad = 0, [], Counter(), 0, []
    for r in reg:
        for tok in [t.strip() for t in r["historical"].split(";")]:
            m = re.fullmatch(r"([\w.]+\.(?:json|md|py))(#(/.*))?", tok)
            if not m:
                nonfile[tok] += 1
                continue
            if m.group(1) not in files:
                tok_bad.append((r["key"], tok)); continue
            tok_ok += 1
            if m.group(3):
                node = load(m.group(1))
                try:
                    for part in m.group(3).strip("/").split("/"):
                        node = node[part]
                    ptr_ok += 1
                except (KeyError, TypeError):
                    ptr_bad.append((r["key"], tok))
    out["historical_refs"] = {"file_tokens_resolved": tok_ok, "file_tokens_unresolved": tok_bad,
                              "json_pointers_resolved": ptr_ok, "json_pointers_unresolved": ptr_bad,
                              "non_file_tokens": dict(nonfile)}

    # Literal value cross-checks against the named sources.
    by = {r["key"]: r for r in reg}
    model = {k[len("static.model."):]: v["expected"] for k, v in by.items() if k.startswith("static.model.")}
    mi = {k: v["sha256"] for k, v in inputs["model_objects_read_via_sha256"].items()}
    ms = {k: v["sha256"] for k, v in src["files"].items()}
    dists = {k[len("static.dist."):]: v["expected"] for k, v in by.items() if k.startswith("static.dist.")}
    opts = {k[len("exec.options."):]: v["expected"] for k, v in by.items() if k.startswith("exec.options.")}
    fixed = plan["input_options"]["fixed_kwargs"]
    typed_eq = lambda a, b: type(a) is type(b) and a == b
    pin = by["static.model_revision"]["expected"]
    out["literal_checks"] = {
        "model_digests_equal_inputs43": sum(model[k] == mi.get(k) for k in model), "model_n": len(model),
        "model_digests_equal_source41_files": sum(model[k] == ms.get(k) for k in model),
        "inputs43_and_source41_model_keysets_equal": set(mi) == set(ms),
        "dist_versions_equal_source41": sum(v == src["versions"]["verified_pinned_distributions"].get(k) for k, v in dists.items()), "dist_n": len(dists),
        "inputs_equal_inputs43": sum(by["static.input." + k]["expected"] == v["verified_pdf_sha256"] for k, v in inputs["development_inputs"].items()),
        "inputs_equal_plan43_fixtures": sum(by["static.input." + f["family_id"]]["expected"] == f["sha256"] for f in plan["fixtures"]),
        "options_typed_equal_plan43": sum(typed_eq(v, fixed[k]) for k, v in opts.items()), "options_n": len(opts), "plan43_fixed_kwargs_n": len(fixed),
        "schedule_equal_plan43": by["exec.schedule"]["expected"] == plan["prehistory"],
        "device_uuid_equal_plan43_and_device43": by["exec.device"]["expected"][0] == plan["uuid"] == dev["uuid"],
        "model_revision_pointer_resolves": isinstance(pin, dict) and inputs.get(pin["pointer"].strip("/")) is not None,
        "model_revision_prefix_equals_plan43": str(inputs.get("pinned_model_revision", "")) == plan["model_revision"],
        "base_python_digest_equals_windows45_observed_image": src["python_sha256"] == win["observed_images_sha256"],
    }

    # Worker source: environment allowlist, hard bindings and stage cuts (ast only).
    wsrc = (B / "sources" / "worker43.py").read_text(encoding="utf-8")
    tree = ast.parse(wsrc)
    env_keys, passthrough, digests, active_runtime = set(), set(), set(), 0
    lines = {}
    local_mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "env_for":
            for n in ast.walk(node):
                if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "update":
                    env_keys |= {k.arg for k in n.keywords}
                if isinstance(n, ast.Tuple) and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in n.elts) and len(n.elts) > 3:
                    passthrough |= {e.value for e in n.elts}
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "ACTIVE_RUNTIME" for t in node.targets):
            active_runtime = len(node.value.keys)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and re.fullmatch(r"[0-9a-f]{64}", node.value):
            digests.add(node.value)
        if isinstance(node, ast.ImportFrom) and node.module and node.col_offset == 0 and node.module in {"timing", "bindings", "capture", "native_observer"}:
            local_mods.add(node.module); lines.setdefault("sibling_imports", []).append(node.lineno)
        if isinstance(node, ast.ImportFrom) and node.module == "limits":
            lines.setdefault("limits_imports", []).append(node.lineno); local_mods.add("limits")
        if isinstance(node, ast.Compare) and "sys.executable" in ast.unparse(node):
            lines["sys_executable_check"] = node.lineno
        if isinstance(node, ast.Compare) and "cmdline()" in ast.unparse(node):
            lines["parent_cmdline_handshake"] = node.lineno
        if isinstance(node, ast.Import) and any(a.name == "torch" for a in node.names):
            lines["import_torch"] = node.lineno
        if isinstance(node, ast.Call) and ast.unparse(node.func).startswith("torch.cuda."):
            lines["first_torch_cuda_call"] = min(node.lineno, lines.get("first_torch_cuda_call", node.lineno))
        if isinstance(node, ast.Call) and ast.unparse(node.func) == "admission":
            lines.setdefault("admission_calls", []).append(node.lineno)
        if isinstance(node, ast.Call) and ast.unparse(node.func) == "util.find_spec":
            lines["triton_absent_check"] = node.lineno
        if isinstance(node, ast.Compare) and "PYTHON" in ast.unparse(node) and "hash_file" in ast.unparse(node):
            lines["venv_launcher_digest_check"] = node.lineno
    for v in lines.values():
        if isinstance(v, list):
            v.sort()
    reg_env = {k[len("exec.env."):] for k in by if k.startswith("exec.env.")}
    allow = env_keys | passthrough
    reg_text = json.dumps(reg)
    out["worker43"] = {
        "child_env_allowlist_keys": len(allow), "register_exec_env_keys": len(reg_env),
        "allowlist_keys_absent_from_register": sorted(allow - reg_env),
        "register_env_values_equal_worker_literals": sorted(reg_env & env_keys),
        "python_star_keys_in_allowlist": sorted(k for k in allow if k.startswith("PYTHON")),
        "digest_literals": len(digests), "digest_literals_absent_from_register": sum(d not in reg_text for d in digests),
        "active_runtime_entries": active_runtime,
        "line_numbers": lines,
        "local_import_closure": sorted(local_mods),
        "local_closure_digest_pinned_in_device43": sorted(m for m in local_mods if m + ".py" in dev["worktree_executables"]),
        "local_closure_source_in_bundle": sorted(m for m in local_mods if m + ".py" in files),
    }
    rs = src["versions"]["runtime_source_sha256"]
    out["closed_world_and_identity_gaps"] = {
        "base_python_digest_in_register": src["python_sha256"] in reg_text,
        "runtime_source_sha256_entries": len(rs), "runtime_source_in_register": sum(v in reg_text for v in rs.values()),
        "triton_distribution_present_historically": src["versions"]["triton_distribution_present"],
        "config_dash_use_triton": src["configuration"]["sparse_config"].get("dash_use_triton"),
        "register_has_triton_absent_obligation": any(k.startswith(("static.dist.triton", "exec.dist.triton")) for k in by),
        "installed_extra_names": src["versions"]["installed_extra_names"],
        "register_has_closed_distribution_set": any("closed" in json.dumps(r["expected"]) for r in reg),
    }
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1])
