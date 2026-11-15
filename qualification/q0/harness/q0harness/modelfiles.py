"""Exact model-directory and dynamic-module-cache verification against the pinned HF tree."""

from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath

from .hashing import file_digests, is_hex
from .outcome import Q0Failure
from .protocol import MODEL_REVISION

# Files required to load and run the checkpoint natively. Excluded upstream files (not
# needed, never copied): .gitattributes, Unlimited-OCR-2.pdf, assets/**, wheel/** (SGLang).
REQUIRED_FILES = (
    "README.md",
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
# Download-tool metadata directory tolerated inside the local model directory. It may not
# contain Python and is never on the import path.
TOLERATED_METADATA_DIR = ".cache/huggingface"


def build_manifest_from_tree(tree: list[dict]) -> dict:
    by_path = {e["path"]: e for e in tree if e.get("type") == "file"}
    files = []
    for path in REQUIRED_FILES:
        e = by_path[path]
        entry = {"path": path, "size": e["size"]}
        if "lfs" in e:
            if e["lfs"]["size"] != e["size"]:
                raise ValueError(f"LFS size disagreement for {path}")
            entry["sha256"] = e["lfs"]["oid"]
            entry["digest_kind"] = "lfs_sha256"
        else:
            entry["git_blob_sha1"] = e["oid"]
            entry["digest_kind"] = "git_blob_sha1"
        files.append(entry)
    weights = sum(f["size"] for f in files if f["path"].endswith(".safetensors"))
    return {
        "schema": "eldq0-model-files/1",
        "repo_id": "baidu/Unlimited-OCR-2",
        "revision": MODEL_REVISION,
        "source": "research/astra/sources/hf-tree.json (HF API tree at the pinned revision)",
        "excluded_upstream_files": [".gitattributes", "Unlimited-OCR-2.pdf", "assets/**", "wheel/**"],
        "weight_bytes": weights,
        "total_bytes": sum(f["size"] for f in files),
        "files": files,
    }


def load_manifest(path: Path) -> dict:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    if manifest.get("revision") != MODEL_REVISION or [f["path"] for f in manifest["files"]] != list(REQUIRED_FILES):
        raise Q0Failure("HASH_MISMATCH", "model manifest is not the frozen pinned file set")
    for f in manifest["files"]:
        ok = is_hex(f.get("sha256"), 64) if f["digest_kind"] == "lfs_sha256" else is_hex(f.get("git_blob_sha1"), 40)
        if not ok:
            raise Q0Failure("HASH_MISMATCH", f"manifest digest malformed for {f['path']}")
    return manifest


def _rel_files(root: Path) -> list[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        for name in filenames:
            out.append(PurePosixPath(Path(dirpath, name).relative_to(root).as_posix()).as_posix())
    return sorted(out)


def verify_model_dir(model_dir: Path, manifest: dict) -> dict:
    """Fail closed unless the directory holds exactly the pinned files with matching digests."""
    model_dir = Path(model_dir)
    if not model_dir.is_dir():
        raise Q0Failure("HASH_MISMATCH", f"model directory absent: {model_dir}")
    present = _rel_files(model_dir)
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
        d = file_digests(model_dir / f["path"], git_blob=f["digest_kind"] == "git_blob_sha1")
        ok = d["size"] == f["size"] and (
            d["sha256"] == f["sha256"] if f["digest_kind"] == "lfs_sha256" else d["git_blob_sha1"] == f["git_blob_sha1"])
        report.append({"path": f["path"], "ok": ok, **d})
        if not ok:
            raise Q0Failure("HASH_MISMATCH", f"model file digest mismatch: {f['path']}", report[-1])
    return {"model_dir": str(model_dir), "files": report, "tolerated_metadata": extras}


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
