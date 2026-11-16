"""Self-contained runtime lock, model-file, module-cache, and static AST safety verifiers."""

from __future__ import annotations

import ast
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath

from .env_guard import is_inside
from .protocol import MODEL_REPO_ID, MODEL_REVISION, WorkerError, file_digests

TOLERATED_METADATA_PREFIX = ".cache/huggingface/"
_REPARSE_ATTR = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)

MODEL_PY_MODULES = (
    "_sparse_base_impl.py",
    "configuration_deepseek_v2.py",
    "conversation.py",
    "dash_attention.py",
    "deepencoder.py",
    "modeling_deepseekv2.py",
    "modeling_unlimitedocr.py",
    "packing_patch.py",
    "sparse_gather_e2e_triton.py",
    "sparse_gather_triton.py",
)

SAVE_PATH_CHAIN = (
    "_uocr_save_results",
    "process_image_with_refs",
    "draw_bounding_boxes",
    "extract_coordinates_and_label",
)


def canonical_dist_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def is_reparse_or_link(path: Path) -> bool:
    try:
        st = os.lstat(path)
    except OSError:
        return False
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & _REPARSE_ATTR)


def load_json_checked(path: Path, expected_sha256: str | None, label: str) -> tuple[dict, str]:
    if not path.is_file() or is_reparse_or_link(path):
        raise WorkerError("invalid_request", f"Missing or symlinked {label}: {path}")
    d = file_digests(path)
    if expected_sha256 is not None and d["sha256"] != expected_sha256.lower():
        raise WorkerError(
            "invalid_request",
            f"{label} digest {d['sha256']} disagreed with expected {expected_sha256}.",
        )
    return json.loads(path.read_text(encoding="utf-8")), d["sha256"]


def verify_dependency_lock(
    lock_doc: dict,
    *,
    accepted_provenance_exceptions: list[str],
    installed_distributions: dict[str, str],
    is_importable_fn,
) -> dict:
    if lock_doc.get("schema") != "eledgercare.local-ocr-dependency-lock/1":
        raise WorkerError("dependency_lock_mismatch", "Unknown dependency-lock schema.")
    required_exc = list(lock_doc.get("required_provenance_exceptions") or [])
    missing_exc = [e for e in required_exc if e not in set(accepted_provenance_exceptions)]
    if missing_exc:
        raise WorkerError(
            "dependency_lock_mismatch",
            f"Required provenance exceptions not accepted: {', '.join(missing_exc)}",
        )
    dists = lock_doc.get("distributions") or []
    if len(dists) != 32 or lock_doc.get("distribution_count") != 32:
        raise WorkerError("dependency_lock_mismatch", "Expected exactly 32 locked distributions.")

    want = {canonical_dist_name(d["name"]): d["version"] for d in dists}
    allowed_extra = {canonical_dist_name(x) for x in lock_doc.get("allowed_unlocked_tooling", ["pip"])}
    have = {canonical_dist_name(k): v for k, v in installed_distributions.items()}

    mismatched = {k: (want[k], have.get(k)) for k in want if have.get(k) != want[k]}
    unexpected = sorted(k for k in have if k not in want and k not in allowed_extra)
    if mismatched or unexpected:
        raise WorkerError(
            "dependency_lock_mismatch",
            f"Installed distributions differ from 32-package lock (mismatch={len(mismatched)}, extra={len(unexpected)}).",
        )

    forbidden = list(lock_doc.get("forbidden_importable_modules") or ["flash_attn", "xformers", "triton"])
    present_forbidden = [m for m in forbidden if is_importable_fn(m)]
    if present_forbidden:
        raise WorkerError(
            "dependency_lock_mismatch",
            f"Forbidden optional backends are importable: {', '.join(present_forbidden)}",
        )

    return {
        "verified_distribution_count": len(want),
        "forbidden_absent": forbidden,
        "provenance_exceptions": required_exc,
    }


def verify_platform_and_gpu(lock_doc: dict, platform_info: dict, leased_gpu_uuid: str) -> None:
    want_plat = lock_doc["platform"]
    want_cuda = lock_doc["cuda"]
    problems: list[str] = []
    if platform_info.get("os") != want_plat["os"] or platform_info.get("machine") != want_plat["machine"]:
        problems.append("os_or_machine")
    if platform_info.get("python") != want_plat["python"]:
        problems.append("python_version")
    if not platform_info.get("cuda_available"):
        problems.append("cuda_unavailable")
    if platform_info.get("torch_cuda_version") != want_cuda["torch_cuda_version_expected"]:
        problems.append("torch_cuda_version")
    if platform_info.get("device_count") != 1:
        problems.append("device_count_not_one")
    if list(platform_info.get("device_capability") or []) != list(want_cuda["device_capability"]):
        problems.append("device_capability")
    if want_cuda["required_arch"] not in (platform_info.get("arch_list") or []):
        problems.append("missing_sm_120")
    obs_uuid = str(platform_info.get("device_uuid") or "")
    if obs_uuid not in (leased_gpu_uuid, leased_gpu_uuid.removeprefix("GPU-")):
        problems.append("device_uuid_mismatch")
    if problems:
        raise WorkerError("platform_mismatch", f"Platform/CUDA validation failed: {', '.join(problems)}")


def normalize_and_verify_model_dir(model_dir_raw: str, notice_dir_raw: str, manifest: dict) -> Path:
    if manifest.get("schema") != "eledgercare.local-ocr-model-manifest/1":
        raise WorkerError("model_integrity_failed", "Unknown model manifest schema.")
    if manifest.get("repo_id") != MODEL_REPO_ID or manifest.get("revision") != MODEL_REVISION:
        raise WorkerError("model_integrity_failed", "Model manifest repo/revision mismatch.")

    if model_dir_raw != model_dir_raw.rstrip("\\/") or not os.path.isabs(model_dir_raw):
        raise WorkerError("model_integrity_failed", "Model directory must be absolute without trailing slash.")
    model_dir = Path(os.path.normpath(model_dir_raw))
    if model_dir.name != manifest.get("model_dir_basename") or not model_dir.name.isidentifier():
        raise WorkerError("model_integrity_failed", "Model directory basename must match identifier-safe pin.")
    if not model_dir.is_dir() or is_reparse_or_link(model_dir):
        raise WorkerError("model_integrity_failed", "Model directory is missing or a symlink/reparse point.")

    present: list[str] = []
    links: list[str] = []
    for dirpath, dirnames, filenames in os.walk(model_dir, followlinks=False):
        for dn in list(dirnames):
            dp = Path(dirpath, dn)
            if is_reparse_or_link(dp):
                links.append(dp.relative_to(model_dir).as_posix())
                dirnames.remove(dn)
        for fn in filenames:
            fp = Path(dirpath, fn)
            rel = PurePosixPath(fp.relative_to(model_dir).as_posix()).as_posix()
            present.append(rel)
            if is_reparse_or_link(fp):
                links.append(rel)
    if links:
        raise WorkerError("model_integrity_failed", "Symlinks or reparse points found in model directory.")

    files = manifest.get("files") or []
    if len(files) != 18:
        raise WorkerError("model_integrity_failed", "Expected 18 runtime model objects.")
    required = {f["path"] for f in files}
    missing = sorted(required - set(present))
    extras = [p for p in present if p not in required]
    bad_extras = [p for p in extras if not p.startswith(TOLERATED_METADATA_PREFIX) or p.endswith((".py", ".pyc"))]
    if missing or bad_extras:
        raise WorkerError(
            "model_integrity_failed",
            f"Model directory contents mismatch (missing={len(missing)}, bad_extras={len(bad_extras)}).",
        )

    for entry in files:
        fp = model_dir / entry["path"]
        want_git = entry["digest_kind"] == "git_blob_sha1"
        d = file_digests(fp, include_git_blob=want_git)
        ok = d["size"] == entry["size"] and (
            d["git_blob_sha1"] == entry["git_blob_sha1"] if want_git else d["sha256"] == entry["sha256"]
        )
        if not ok:
            raise WorkerError("model_integrity_failed", f"Model runtime object digest mismatch: {entry['path']}")

    notice_dir = Path(os.path.normpath(notice_dir_raw))
    if not notice_dir.is_dir() or is_reparse_or_link(notice_dir):
        raise WorkerError("model_integrity_failed", "Model notice directory missing or symlinked.")
    for notice in manifest.get("notices") or []:
        np = notice_dir / notice["path"]
        if not np.is_file() or is_reparse_or_link(np):
            raise WorkerError("model_integrity_failed", f"Model notice missing or symlinked: {notice['path']}")
        d = file_digests(np, include_git_blob=(notice["digest_kind"] == "git_blob_sha1"))
        ok = d["size"] == notice["size"] and (
            d["git_blob_sha1"] == notice["git_blob_sha1"]
            if notice["digest_kind"] == "git_blob_sha1"
            else d["sha256"] == notice["sha256"]
        )
        if not ok:
            raise WorkerError("model_integrity_failed", f"Model notice digest mismatch: {notice['path']}")

    return model_dir


def _callee(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def verify_model_sources_ast_safety(model_dir: Path) -> None:
    """Prove statically before import that builtin eval is confined to unreachable save_results path."""
    for fname in MODEL_PY_MODULES:
        source = (model_dir / fname).read_text(encoding="utf-8")
        tree = ast.parse(source, fname)
        eval_calls = [
            c for c in ast.walk(tree)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id in ("eval", "exec", "compile")
        ]
        if fname != "modeling_unlimitedocr.py":
            if eval_calls:
                raise WorkerError("safety_violation", f"Unexpected eval/exec/compile in {fname}.")
            continue

        funcs = {
            n.name: n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        owners = [
            fn_name for fn_name, fn_node in funcs.items()
            for c in ast.walk(fn_node)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id in ("eval", "exec", "compile")
        ]
        if owners != ["extract_coordinates_and_label"] or len(eval_calls) != 1:
            raise WorkerError("safety_violation", "Unexpected eval/exec/compile site in entry module.")

        callers: dict[str, list[str]] = {name: [] for name in SAVE_PATH_CHAIN}
        for fn_name, fn_node in funcs.items():
            for c in ast.walk(fn_node):
                if isinstance(c, ast.Call):
                    cal = _callee(c)
                    if cal in callers and cal != fn_name:
                        callers[cal].append(fn_name)
        expected_callers = {
            "_uocr_save_results": ["infer"],
            "process_image_with_refs": ["_uocr_save_results"],
            "draw_bounding_boxes": ["process_image_with_refs"],
            "extract_coordinates_and_label": ["draw_bounding_boxes"],
        }
        if {k: sorted(v) for k, v in callers.items()} != expected_callers:
            raise WorkerError("safety_violation", "Save-path caller chain differs from verified pin.")

        infer_fn = funcs["infer"]
        guarded = 0
        for node in ast.walk(infer_fn):
            if isinstance(node, ast.If) and isinstance(node.test, ast.BoolOp) and isinstance(node.test.op, ast.And):
                names = [getattr(v, "id", None) for v in node.test.values]
                if names == ["save_results", "output_path"]:
                    body_mod = ast.Module(body=node.body, type_ignores=[])
                    if any(isinstance(c, ast.Call) and _callee(c) == "_uocr_save_results" for c in ast.walk(body_mod)):
                        guarded += 1
        if guarded != 1:
            raise WorkerError("safety_violation", "Save call is not uniquely guarded by `save_results and output_path`.")


def verify_loaded_module_cache(modules_cache: Path, model_dir: Path, sys_modules: dict) -> int:
    """Prove every dynamically imported custom module lies inside run-local HF_MODULES_CACHE and matches model_dir."""
    modules_cache_res = modules_cache.resolve()
    model_dir_res = model_dir.resolve()
    checked = 0
    saw_entry = False

    for name, mod in sorted(sys_modules.items()):
        if not (name == "transformers_modules" or name.startswith("transformers_modules.")):
            continue
        mod_file = getattr(mod, "__file__", None)
        if mod_file is None:
            continue
        fp = Path(mod_file).resolve()
        if not is_inside(fp, modules_cache_res):
            raise WorkerError("safety_violation", f"Dynamic module loaded outside HF_MODULES_CACHE: {name}")
        if fp.name == "__init__.py":
            if fp.stat().st_size != 0:
                raise WorkerError("model_integrity_failed", "Non-empty __init__.py in dynamic modules cache.")
            continue
        src = model_dir_res / fp.name
        if not src.is_file() or file_digests(fp) != file_digests(src):
            raise WorkerError("model_integrity_failed", f"Cached custom module differs from verified source: {fp.name}")
        if fp.name == "modeling_unlimitedocr.py":
            saw_entry = True
        checked += 1

    if not saw_entry:
        raise WorkerError("model_integrity_failed", "Entry module modeling_unlimitedocr.py was not verified in cache.")

    for py in sorted(modules_cache_res.rglob("*.py")):
        if py.name == "__init__.py":
            continue
        src = model_dir_res / py.name
        if not src.is_file() or file_digests(py) != file_digests(src):
            raise WorkerError("model_integrity_failed", f"Unverified .py file in HF_MODULES_CACHE: {py.name}")

    return checked
