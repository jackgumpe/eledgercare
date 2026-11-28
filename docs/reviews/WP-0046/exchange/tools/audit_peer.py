"""Non-author audit of the peer's frozen register.json against pinned archive bytes.

Data comparison only. Never executes peer code. Reads pinned files with read-only
`git show` at e43af2e2 (and the peer tip for its own WP-0046 files), and parses
WP-0043 closure modules with ast. Prints keys, counts and booleans; no host paths.
Usage: python -I audit_peer.py PEER_REGISTER BUNDLE_DIR REPO_DIR
"""
import ast
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

BASE = "e43af2e263f55478d1d551a5a095536b042589c2"
PEER = "84d6934d96c69fd37d6fe2afde2d24dd1c431a24"


def main(peer_path, bundle, repo):
    show = lambda rev, p: subprocess.run(["git", "-C", repo, "show", rev + ":" + p], capture_output=True)
    exists = lambda rev, p: show(rev, p).returncode == 0
    gj = lambda p: json.loads(show(BASE, p).stdout)
    g = json.load(open(peer_path, encoding="utf-8"))
    E = g["entries"]
    by = {e["key"]: e for e in E}
    B = json.loads((Path(bundle) / "register.json").read_text(encoding="utf-8"))["groups"]
    src = json.loads((Path(bundle) / "sources/source41.json").read_text(encoding="utf-8"))
    out = {}

    # 1. Keys, stages, status classes.
    cls = Counter()
    for e in E:
        st, pre = e["status"], e["missing_precondition"]
        c = ("deferred" if st.endswith("deferred") else "unbound_requires_decision" if st.endswith("requires_decision")
             else "bound_unconditional" if not pre else "bound_conditional")
        cls[(c, e["direct_stock_stage"])] += 1
    out["keys"] = {"n": len(E), "same_order_as_bundle": [e["key"] for e in E] == [b["key"] for b in B],
                   "earliest_stage_preserved": sum(e["earliest_stage"] == b["earliest_stage"] for e, b in zip(E, B)),
                   "direct_stage_moves": sorted([e["key"], e["earliest_stage"], e["direct_stock_stage"]] for e in E if e["earliest_stage"] != e["direct_stock_stage"]),
                   "class_by_direct_stage": {f"{c}@{s}": n for (c, s), n in sorted(cls.items())},
                   "header_counts_match": g["status_counts"] == dict(Counter(e["status"] for e in E))}

    # 2. Literal values against pinned archive bytes.
    wh = {w["wheel"]: w for w in gj("docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/checks/02-verify-wheelhouse.json")["wheels"]}
    ver = src["versions"]["verified_pinned_distributions"]
    d_ok = []
    for k, e in by.items():
        if k.startswith("static.dist."):
            x, w = e["expected"], wh.get(e["expected"].get("wheel"))
            d_ok.append(bool(w) and x["version"] == ver.get(x["distribution"]) and x["wheel_sha256"] == w["sha256"]
                        and x["wheel_size_bytes"] == w["size"] and x["wheel_metadata_sha256"] == w["metadata"]["metadata_sha256"])
    inp = gj("docs/coordination/WP-0043/native-inputs.json")
    m_ok = [by["static.model." + k]["expected"]["sha256"] == v["sha256"] and by["static.model." + k]["expected"]["bytes"] == v["bytes"]
            for k, v in inp["model_objects_read_via_sha256"].items()]
    plan = gj("docs/coordination/WP-0043/plan-canonical.json")
    fixed = plan["input_options"]["fixed_kwargs"]
    o_ok = [type(by["exec.options." + k]["expected"]["value"]) is type(v) and by["exec.options." + k]["expected"]["value"] == v for k, v in fixed.items()]
    fx = {f["family_id"]: f for f in plan["fixtures"]}
    i_ok = [by["static.input." + k]["expected"].get("sha256", by["static.input." + k]["expected"].get("verified_pdf_sha256")) == f["sha256"]
            and by["static.input." + k]["expected"].get("git_blob") == f["git_blob_oid"] for k, f in fx.items()]
    h43 = gj("docs/coordination/WP-0043/native-evidence.json")["retained_rows"]
    n_ok = []
    for ri, r in enumerate(h43):
        for ci, (ph, off) in enumerate([("C0_raw", 1174), ("C1_post_rep", 1238), ("C2_post_page", 1282)]):
            x = by["native.%d.%s" % (r["position"], ph)]["expected"]
            hr, c = x["historical_reference_distinct_from_pass_rule"], r["copies"][ci]
            n_ok.append(x["generator_offset_cpython_3_12_10"] == off and hr["archive_vector_sha256"] == c["vector_sha256"]
                        and hr["archive_copy_id"] == c["copy_id"] and hr["archive_journal_serial"] == c["journal_serial"]
                        and hr["archive_actual_emission"] == r["actual_emission"] and hr["archive_final_gap"] == r["final_top_two"]["difference"])
    w43 = (Path(bundle) / "sources/worker43.py").read_text(encoding="utf-8")
    active = {}
    for node in ast.walk(ast.parse(w43)):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "ACTIVE_RUNTIME" for t in node.targets):
            active = ast.literal_eval(node.value)
    runtime_ref = {**src["versions"]["runtime_source_sha256"], **active}
    rt = {k: by[k]["expected"].get("stage1_cpu_pinned_runtime_files_sha256") or by[k]["expected"].get("pinned_runtime_files_sha256")
          or by[k]["expected"].get("runtime_files_live_origin_sha256") for k in ("module.coverage", "cpu.import_resolution", "exec.loaded")}
    dyn_ref = {k: v["sha256"] for k, v in src["historical_q0_imported_module_receipt_and_disk"].items()}
    out["literals"] = {
        "dist_wheel_version_sha_size_metadata": [sum(d_ok), len(d_ok)],
        "model_sha_and_bytes": [sum(m_ok), len(m_ok)],
        "options_typed": [sum(o_ok), len(o_ok)],
        "inputs_sha_and_blob": [sum(i_ok), len(i_ok)],
        "native_rows_offset_digest_copy_serial_emission_gap": [sum(n_ok), len(n_ok)],
        "runtime_file_digests": {k: (v == runtime_ref) if v else None for k, v in rt.items()},
        "runtime_reference_n": len(runtime_ref),
        "dynamic_module_digests_equal": by["exec.loaded"]["expected"]["dynamic_hf_modules_sha256"] == dyn_ref,
        "route_image_sha_equals_source41": by["route.design"]["expected"]["application_image_sha256"] == src["python_sha256"],
        "device_uuid_equals_plan43": by["exec.device"]["expected"]["historical_reference_uuid"] == plan["uuid"],
    }

    # 3. Environment rows against the worker literals.
    env_lit = {}
    for node in ast.walk(ast.parse(w43)):
        if isinstance(node, ast.FunctionDef) and node.name == "env_for":
            for n in ast.walk(node):
                if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "update":
                    env_lit = {k.arg: (k.value.value if isinstance(k.value, ast.Constant) else ast.unparse(k.value)) for k in n.keywords}
    er = {}
    for k, e in by.items():
        if k.startswith("exec.env."):
            name = k[len("exec.env."):]
            lit = env_lit.get(name)
            lit = plan["uuid"] if lit == "UUID" else lit
            er[name] = {"e_child_equals_worker_literal": e["expected"]["e_child"].get("value") == lit, "stage": e["direct_stock_stage"]}
    out["env_rows"] = er
    out["register_rows_with_machine_closed_env_rule"] = sum(1 for e in E if "closed" in json.dumps(e["expected"]).lower() and "env" in e["key"])
    out["stage1_cuda_visible_devices_row"] = any(e["direct_stock_stage"] == 1 and "CUDA_VISIBLE_DEVICES" in json.dumps(e["expected"]) and '""' in json.dumps(e["expected"]) for e in E)

    # 4. Literal references: historical_reference and evidence_locator.
    tally = Counter()
    bad = []
    for e in E:
        for field in ("historical_reference", "evidence_locator"):
            for tok in [t.strip() for t in str(e[field]).split(";") if t.strip()]:
                if tok.startswith("prospective:"):
                    tally[field + ".prospective"] += 1; continue
                m = re.fullmatch(r"((?:docs|qualification|evaluation|AGENTS)[\w./-]*?\.(?:json|md|py|txt))(#(.*))?", tok)
                if not m:
                    tally[field + ".label"] += 1; continue
                path, frag = m.group(1), m.group(3)
                rev = PEER if path.startswith("docs/research/WP-0046/") else BASE
                if not exists(rev, path):
                    bad.append([e["key"], field, tok]); tally[field + ".unresolved"] += 1; continue
                ok = True
                if frag and frag.startswith("/") and path.endswith(".json"):
                    node = json.loads(show(rev, path).stdout)
                    try:
                        for part in frag.strip("/").split("/"):
                            node = node[int(part)] if isinstance(node, list) else node[part]
                    except (KeyError, IndexError, ValueError, TypeError):
                        ok = False
                elif frag and re.fullmatch(r"L(\d+)(?:-L(\d+))?", frag):
                    n = len(show(rev, path).stdout.decode("utf-8", "replace").splitlines())
                    ok = all(1 <= int(x) <= n for x in re.findall(r"\d+", frag))
                tally[field + (".resolved" if ok else ".fragment_unresolved")] += 1
                if not ok:
                    bad.append([e["key"], field, tok])
    out["references"] = {"tally": dict(sorted(tally.items())), "unresolved": bad}

    # 5. Module scope of the WP-0043 import closure (ast; no import).
    scope = {}
    for name in ("stock.py", "timing.py", "bindings.py", "capture.py", "native_observer.py", "limits.py", "transfer.py"):
        tree = ast.parse(show(BASE, "docs/research/WP-0043/" + name).stdout)
        calls = []
        for n in tree.body:
            if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef)):
                continue
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant):
                continue
            if isinstance(n, ast.If) and "__name__" in ast.unparse(n.test):
                continue
            if isinstance(n, (ast.Assign, ast.AnnAssign)) and not any(isinstance(x, ast.Call) for x in ast.walk(n)):
                continue
            calls.append([n.lineno, type(n).__name__])
        scope[name] = calls
    out["closure_module_scope_effects"] = scope
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main(*sys.argv[1:4])
