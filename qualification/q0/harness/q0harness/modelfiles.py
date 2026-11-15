"""Exact model-directory, notice and dynamic-module-cache verification against the pinned HF tree.

Runtime set: the 18 objects needed to load the checkpoint (16 non-LFS files verified by Git
blob SHA-1 + size, 2 safetensors shards verified by LFS SHA-256 + size). The model card
README.md is a separate NOTICE (license declaration), not a runtime object, and is kept
outside the runtime directory (WP-0005 /003 phase A Q0R-09; Astra /007 sources/model-card.md).
Verification is transport-independent: xetHash and Git pointer OIDs of LFS files are never
used as payload digests.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path, PurePosixPath

from .hashing import file_digests, is_hex
from .outcome import Q0Failure
from .protocol import MODEL_REVISION

REQUIRED_FILES = (
    "_sparse_base_impl.py",
    "config.json",
    "configuration_deepseek_v2.py",
    "conversation.py",
    "dash_attention.py",
    "deepencoder.py",
    "generation_config.json",
    "model-00001-of-00002.safetensors",
    "model-00002-of-00002.safetensors",
    "model.safetensors.index.json",
    "modeling_deepseekv2.py",
    "modeling_unlimitedocr.py",
    "packing_patch.py",
    "sparse_gather_e2e_triton.py",
    "sparse_gather_triton.py",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
)
NOTICE_FILES = ("README.md",)
EXCLUDED_UPSTREAM = [".gitattributes", "README.md (separate notice, not a runtime object)",
                     "Unlimited-OCR-2.pdf", "assets/**", "wheel/**"]
# Download-tool metadata directory tolerated inside the local model directory. It may not
# contain Python and is never on the import path.
TOLERATED_METADATA_DIR = ".cache/huggingface"
_REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def _entry(e: dict) -> dict:
    entry = {"path": e["path"], "size": e["size"]}
    if "lfs" in e:
        if e["lfs"]["size"] != e["size"]:
            raise ValueError(f"LFS size disagreement for {e['path']}")
        entry["sha256"] = e["lfs"]["oid"]
        entry["digest_kind"] = "lfs_sha256"
    else:
        entry["git_blob_sha1"] = e["oid"]
        entry["digest_kind"] = "git_blob_sha1"
    return entry


def build_manifest_from_tree(tree: list[dict]) -> dict:
    by_path = {e["path"]: e for e in tree if e.get("type") == "file"}
    files = [_entry(by_path[p]) for p in REQUIRED_FILES]
    notices = [dict(_entry(by_path[p]), role="model card / license notice; not a runtime object")
               for p in NOTICE_FILES]
    weights = sum(f["size"] for f in files if f["path"].endswith(".safetensors"))
    return {
        "schema": "eldq0-model-files/2",
        "repo_id": "baidu/Unlimited-OCR-2",
        "revision": MODEL_REVISION,
        "source": "research/astra/sources/hf-tree.json (HF API tree at the pinned revision)",
        "excluded_upstream_files": EXCLUDED_UPSTREAM,
        "runtime_object_count": len(files),
        "weight_bytes": weights,
        "total_bytes": sum(f["size"] for f in files),
        "files": files,
        "notices": notices,
    }


def _check_digest_fields(f: dict, what: str):
    ok = is_hex(f.get("sha256"), 64) if f["digest_kind"] == "lfs_sha256" else is_hex(f.get("git_blob_sha1"), 40)
    if not ok:
        raise Q0Failure("HASH_MISMATCH", f"{what} digest malformed for {f['path']}")


def load_manifest(path: Path) -> dict:
    import json
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    if manifest.get("revision") != MODEL_REVISION or [f["path"] for f in manifest["files"]] != list(REQUIRED_FILES) \
            or manifest.get("runtime_object_count") != len(REQUIRED_FILES) \
            or [n["path"] for n in manifest.get("notices", [])] != list(NOTICE_FILES):
        raise Q0Failure("HASH_MISMATCH", "model manifest is not the frozen pinned 18-object runtime set plus notice")
    for f in manifest["files"]:
        _check_digest_fields(f, "manifest")
    for n in manifest["notices"]:
        _check_digest_fields(n, "notice")
    return manifest


def is_reparse_or_link(p: Path) -> bool:
    try:
        st = os.lstat(p)
    except OSError:
        return False
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & _REPARSE)


def normalize_model_dir(path, expected) -> Path:
    """Q0R-06: an absolute, normalized, existing, non-reparse directory with no trailing
    separator, whose basename is a valid Python identifier (it becomes the
    transformers_modules package name), equal to the protocol-selected path. Never
    falls through to repo-ID resolution."""
    raw = str(path)
    if raw != raw.rstrip("\\/"):
        raise Q0Failure("UNSUPPORTED_PLATFORM", f"model directory has a trailing separator: {raw!r}")
    if not os.path.isabs(raw):
        raise Q0Failure("UNSUPPORTED_PLATFORM", f"model directory is not absolute: {raw!r}")
    norm = os.path.normpath(raw)
    if os.path.normcase(norm) != os.path.normcase(os.path.normpath(str(expected))):
        raise Q0Failure("STORAGE_NOT_OWNED", f"model directory {norm} is not the protocol-selected {expected}")
    name = os.path.basename(norm)
    if not name or not name.isidentifier():
        raise Q0Failure("UNSUPPORTED_PLATFORM", f"model directory basename {name!r} is not a Python identifier")
    p = Path(norm)
    if not p.is_dir() or is_reparse_or_link(p):
        raise Q0Failure("HASH_MISMATCH", f"model directory absent or a reparse point: {norm}")
    return p


def _rel_files(root: Path) -> tuple[list[str], list[str]]:
    out, links = [], []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in list(dirnames):
            if is_reparse_or_link(Path(dirpath, name)):
                links.append(Path(dirpath, name).relative_to(root).as_posix())
                dirnames.remove(name)
        for name in filenames:
            rel = PurePosixPath(Path(dirpath, name).relative_to(root).as_posix()).as_posix()
            out.append(rel)
            if is_reparse_or_link(Path(dirpath, name)):
                links.append(rel)
    return sorted(out), sorted(links)


def _verify_one(base: Path, f: dict) -> dict:
    d = file_digests(base / f["path"], git_blob=f["digest_kind"] == "git_blob_sha1")
    ok = d["size"] == f["size"] and (
        d["sha256"] == f["sha256"] if f["digest_kind"] == "lfs_sha256" else d["git_blob_sha1"] == f["git_blob_sha1"])
    return {"path": f["path"], "ok": ok, **d}


def verify_model_dir(model_dir: Path, manifest: dict) -> dict:
    """Fail closed unless the directory holds exactly the 18 pinned runtime objects with matching
    digests (plus tolerated download metadata), with no links/reparse points."""
    model_dir = Path(model_dir)
    if not model_dir.is_dir() or is_reparse_or_link(model_dir):
        raise Q0Failure("HASH_MISMATCH", f"model directory absent or a reparse point: {model_dir}")
    present, links = _rel_files(model_dir)
    if links:
        raise Q0Failure("UNEXPECTED_ARTIFACT", "symbolic links / reparse points in the model directory", links)
    required = {f["path"] for f in manifest["files"]}
    extras = [p for p in present if p not in required]
    bad_extras = [p for p in extras if not p.startswith(TOLERATED_METADATA_DIR + "/") or p.endswith((".py", ".pyc"))]
    missing = sorted(required - set(present))
    if missing:
        raise Q0Failure("HASH_MISMATCH", "pinned model files missing", missing)
    if bad_extras:
        raise Q0Failure("UNEXPECTED_ARTIFACT", "unexpected files in the model directory", bad_extras)
    report = []
    for f in manifest["files"]:
        report.append(_verify_one(model_dir, f))
        if not report[-1]["ok"]:
            raise Q0Failure("HASH_MISMATCH", f"model file digest mismatch: {f['path']}", report[-1])
    return {"model_dir": str(model_dir), "runtime_objects": len(report), "files": report, "tolerated_metadata": extras}


def verify_notices(notice_dir: Path, manifest: dict) -> dict:
    notice_dir = Path(notice_dir)
    rows = []
    for n in manifest["notices"]:
        if is_reparse_or_link(notice_dir / n["path"]):
            raise Q0Failure("UNEXPECTED_ARTIFACT", f"notice is a link/reparse point: {n['path']}")
        if not (notice_dir / n["path"]).is_file():
            raise Q0Failure("HASH_MISMATCH", f"notice missing: {n['path']}")
        rows.append(_verify_one(notice_dir, n))
        if not rows[-1]["ok"]:
            raise Q0Failure("HASH_MISMATCH", f"notice digest mismatch: {n['path']}", rows[-1])
    return {"notice_dir": str(notice_dir), "notices": rows}


def verify_module_cache(modules_cache: Path, model_dir: Path, loaded_modules: dict[str, str]) -> dict:
    """After the native dynamic-module load, prove every executed custom-code file is
    byte-identical to the verified model directory and lives inside the owned modules cache.

    loaded_modules maps module name -> __file__ for every sys.modules entry under
    'transformers_modules.'. Returns the comparison report; raises on any difference.
    """
    modules_cache = Path(modules_cache).resolve()
    model_dir = Path(model_dir).resolve()
    rows = []
    for name, file in sorted(loaded_modules.items()):
        if file is None:
            continue  # namespace/package placeholders created by the loader
        fp = Path(file).resolve()
        if modules_cache not in fp.parents:
            raise Q0Failure("SAFETY_VIOLATION", f"remote-code module loaded outside owned modules cache: {name} {fp}")
        if fp.name == "__init__.py":
            if fp.stat().st_size != 0:
                raise Q0Failure("UNEXPECTED_ARTIFACT", f"non-empty loader package init: {fp}")
            continue
        src = model_dir / fp.name
        if not src.is_file():
            raise Q0Failure("UNEXPECTED_ARTIFACT", f"loaded module has no verified source: {fp.name}")
        a, b = file_digests(fp, git_blob=False), file_digests(src, git_blob=False)
        rows.append({"module": name, "file": fp.name, "cache_sha256": a["sha256"], "model_sha256": b["sha256"],
                     "identical": a == b})
        if a != b:
            raise Q0Failure("HASH_MISMATCH", f"module-cache copy differs from verified source: {fp.name}", rows[-1])
    if not any(r["file"] == "modeling_unlimitedocr.py" for r in rows):
        raise Q0Failure("IMPORT_FAILURE", "entry module modeling_unlimitedocr not found among loaded modules")
    # Every .py copied into the cache must also be identical, imported or not.
    for py in sorted(modules_cache.rglob("*.py")):
        if py.name == "__init__.py":
            continue
        src = model_dir / py.name
        if not src.is_file() or file_digests(py, git_blob=False) != file_digests(src, git_blob=False):
            raise Q0Failure("HASH_MISMATCH", f"modules cache contains a non-identical file: {py}")
    return {"modules_cache": str(modules_cache), "modules": rows}
