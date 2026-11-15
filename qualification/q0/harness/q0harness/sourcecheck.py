"""Static, read-only analysis of the pinned model source (no import, no execution).

Used twice: on the committed upstream snapshots in research/astra/sources (CPU stage) and
on the hash-verified local model directory before load (released stage).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from .hashing import file_digests
from .outcome import Q0Failure
from .protocol import REPO_ROOT

SNAPSHOT_DIR = REPO_ROOT / "research" / "astra" / "sources"
SNAPSHOT_MANIFEST = REPO_ROOT / "research" / "astra" / "source-manifest.json"
HF_TREE = SNAPSHOT_DIR / "hf-tree.json"

NATIVE_RETURN_KEYS = {"text", "token_ids", "prompt_token_ids", "finish_reason", "num_pages_out",
                      "expected_pages", "time", "prefill_time"}
# Functions that lie on the eval-containing save path, in call order.
SAVE_PATH_CHAIN = ("_uocr_save_results", "process_image_with_refs", "draw_bounding_boxes",
                   "extract_coordinates_and_label")


def verify_snapshots(repo_root: Path = REPO_ROOT) -> list[dict]:
    """Each hf-* snapshot must match its manifest SHA-256 AND the pinned HF tree git-blob oid."""
    manifest = json.loads((repo_root / "research/astra/source-manifest.json").read_text(encoding="utf-8"))
    tree = {e["path"]: e for e in json.loads((repo_root / "research/astra/sources/hf-tree.json").read_text(encoding="utf-8"))}
    rows = []
    for m in manifest:
        if not m["path"].startswith("research/astra/sources/hf-") or m["path"].endswith("hf-tree.json"):
            continue
        upstream = m["origin"].rsplit("/", 1)[-1]
        d = file_digests(repo_root / m["path"])
        t = tree[upstream]
        row = {"snapshot": m["path"], "upstream_path": upstream, "revision": m["revision"], **d,
               "manifest_sha256_ok": d["sha256"] == m["sha256"] and d["size"] == m["bytes"],
               "tree_oid": t["oid"], "tree_oid_ok": d["git_blob_sha1"] == t["oid"] and d["size"] == t["size"]}
        rows.append(row)
        if not (row["manifest_sha256_ok"] and row["tree_oid_ok"]):
            raise Q0Failure("HASH_MISMATCH", f"snapshot is not the pinned upstream blob: {m['path']}", row)
    return rows


def _calls_in(node: ast.AST) -> list[ast.Call]:
    return [n for n in ast.walk(node) if isinstance(n, ast.Call)]


def _callee(call: ast.Call) -> str | None:
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def _functions(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(node.name, node)
    return out


def eval_exec_sites(source: str, filename: str) -> list[dict]:
    tree = ast.parse(source, filename)
    return [{"file": filename, "line": c.lineno, "builtin": c.func.id}
            for c in _calls_in(tree) if isinstance(c.func, ast.Name) and c.func.id in ("eval", "exec", "compile")]


def analyze_entry_module(source: str) -> dict:
    """Prove from the AST that builtin eval in modeling_unlimitedocr is reachable only through
    `if save_results and output_path: self._uocr_save_results(...)` inside `infer`, and extract
    the infer_multi/_uocr_generate facts the harness relies on."""
    tree = ast.parse(source, "modeling_unlimitedocr.py")
    funcs = _functions(tree)
    facts: dict = {}

    evals = eval_exec_sites(source, "modeling_unlimitedocr.py")
    owners = []
    for name, fn in funcs.items():
        for c in _calls_in(fn):
            if isinstance(c.func, ast.Name) and c.func.id in ("eval", "exec", "compile"):
                owners.append((name, c.lineno))
    facts["eval_sites"] = evals
    if sorted(o[0] for o in owners) != ["extract_coordinates_and_label"] or len(evals) != 1:
        raise Q0Failure("SAFETY_VIOLATION", "unexpected eval/exec/compile sites", evals)

    # Caller graph for the save-path chain: each link must have exactly one caller, the previous link.
    callers: dict[str, list[str]] = {n: [] for n in SAVE_PATH_CHAIN}
    for name, fn in funcs.items():
        for c in _calls_in(fn):
            cal = _callee(c)
            if cal in callers and cal != name:
                callers[cal].append(name)
    expected = {"process_image_with_refs": ["_uocr_save_results"], "draw_bounding_boxes": ["process_image_with_refs"],
                "extract_coordinates_and_label": ["draw_bounding_boxes"], "_uocr_save_results": ["infer"]}
    facts["save_path_callers"] = callers
    if {k: sorted(v) for k, v in callers.items()} != expected:
        raise Q0Failure("SAFETY_VIOLATION", "save-path call graph differs from the analyzed pin", callers)

    # The single call to _uocr_save_results must be guarded by `if save_results and output_path:`.
    infer = funcs["infer"]
    guarded = []
    for node in ast.walk(infer):
        if isinstance(node, ast.If):
            t = node.test
            if (isinstance(t, ast.BoolOp) and isinstance(t.op, ast.And)
                    and [getattr(v, "id", None) for v in t.values] == ["save_results", "output_path"]):
                for c in _calls_in(ast.Module(body=node.body, type_ignores=[])):
                    if _callee(c) == "_uocr_save_results":
                        guarded.append(node.lineno)
    facts["save_guard_lines"] = guarded
    if len(guarded) != 1:
        raise Q0Failure("SAFETY_VIOLATION", "save call is not uniquely guarded by `save_results and output_path`")

    # infer_multi: must forward save_results and default crop_mode to False via setdefault.
    im = funcs["infer_multi"]
    setdefaults = [c for c in _calls_in(im) if _callee(c) == "setdefault"
                   and len(c.args) == 2 and isinstance(c.args[0], ast.Constant) and c.args[0].value == "crop_mode"]
    facts["infer_multi_crop_default"] = [getattr(c.args[1], "value", None) for c in setdefaults]
    if facts["infer_multi_crop_default"] != [False]:
        raise Q0Failure("SAFETY_VIOLATION", "infer_multi crop_mode default is not setdefault(False)")
    inner = [c for c in _calls_in(im) if _callee(c) == "infer"]
    kw = {k.arg for k in inner[0].keywords} if len(inner) == 1 else set()
    facts["infer_multi_forwards"] = sorted(a for a in kw if a)
    if not {"save_results", "output_path", "temperature", "return_dict"} <= kw or None not in kw:
        raise Q0Failure("SAFETY_VIOLATION", "infer_multi no longer forwards the frozen arguments/**kwargs to infer")

    # infer signature must accept every frozen kwarg we pass through **kwargs.
    infer_args = {a.arg for a in infer.args.args}
    facts["infer_parameters"] = sorted(infer_args)
    needed = {"crop_mode", "save_results", "output_path", "base_size", "image_size", "max_length", "max_new_tokens",
              "no_repeat_ngram_size", "ngram_window", "ngram_whitelist_token_ids", "temperature", "page_count_guard",
              "max_page_tokens", "dash_topm", "max_crops", "tps_interval", "test_compress", "eval_mode", "return_dict"}
    if not needed <= infer_args:
        raise Q0Failure("SAFETY_VIOLATION", "infer() lacks a frozen parameter", sorted(needed - infer_args))

    # _uocr_generate must return the native dict whose fields the harness records.
    gen = funcs["_uocr_generate"]
    keys = set()
    for node in ast.walk(gen):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
            keys |= {k.value for k in node.value.keys if isinstance(k, ast.Constant)}
    facts["native_return_keys"] = sorted(keys)
    if not NATIVE_RETURN_KEYS <= keys:
        raise Q0Failure("SAFETY_VIOLATION", "native return dict lacks recorded fields", sorted(NATIVE_RETURN_KEYS - keys))

    # Ring-buffer SWA is disabled for decode inside _uocr_generate (source inference, observed at runtime).
    assigns = [ast.unparse(n) for n in ast.walk(gen) if isinstance(n, ast.Assign)]
    facts["decode_disables_ring_window"] = "cfg._ring_window = None" in assigns and "cfg.sliding_window = None" in assigns
    facts["uses_dynamic_cache"] = any(isinstance(n, ast.Call) and _callee(n) == "DynamicCache" for n in ast.walk(gen))
    return facts


def analyze_model_sources(source_dir: Path, names: dict[str, str]) -> dict:
    """names maps logical module -> filename inside source_dir. Returns facts; raises on violations."""
    facts = {"entry": analyze_entry_module((source_dir / names["modeling_unlimitedocr"]).read_text(encoding="utf-8"))}
    sites = []
    for logical, fname in sorted(names.items()):
        sites += eval_exec_sites((source_dir / fname).read_text(encoding="utf-8"), fname)
    facts["eval_exec_compile_sites_all_modules"] = sites
    non_entry = [s for s in sites if s["file"] != names["modeling_unlimitedocr"]]
    if non_entry:
        raise Q0Failure("SAFETY_VIOLATION", "eval/exec/compile outside the analyzed entry-module site", non_entry)
    return facts


SNAPSHOT_NAMES = {
    "modeling_unlimitedocr": "hf-modeling_unlimitedocr.py.txt",
    "modeling_deepseekv2": "hf-modeling_deepseekv2.py.txt",
    "_sparse_base_impl": "hf-_sparse_base_impl.py.txt",
    "dash_attention": "hf-dash_attention.py.txt",
    "deepencoder": "hf-deepencoder.py.txt",
    "sparse_gather_triton": "hf-sparse_gather_triton.py.txt",
    "sparse_gather_e2e_triton": "hf-sparse_gather_e2e_triton.py.txt",
}
MODEL_DIR_NAMES = {k: k + ".py" for k in (
    "modeling_unlimitedocr", "modeling_deepseekv2", "_sparse_base_impl", "dash_attention", "deepencoder",
    "sparse_gather_triton", "sparse_gather_e2e_triton", "configuration_deepseek_v2", "conversation", "packing_patch")}
