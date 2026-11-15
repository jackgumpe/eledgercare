"""Dependency-lock validation. A lock that is not final blocks execution (fail closed)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .hashing import is_hex
from .outcome import Q0Failure

# Distributions the pinned source imports at module scope (see PROTOCOL.md section 5),
# plus the renderer and loader stack. Their exact versions/hashes come from /001 + review.
REQUIRED_DISTRIBUTIONS = ("torch", "torchvision", "transformers", "tokenizers", "huggingface-hub", "safetensors",
                          "pypdfium2", "pillow", "numpy", "einops", "addict", "easydict", "requests", "tqdm")
FIXED_VERSIONS = {"transformers": "4.52.1", "pypdfium2": "5.15.2"}
# Optional backends whose mere importability changes the pinned source's code paths.
ALWAYS_FORBIDDEN_IMPORTABLE = ("flash_attn", "xformers")
_EXACT = re.compile(r"^[0-9][0-9A-Za-z.+!_-]*$")


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def load_lock(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_lock(lock: dict) -> dict:
    if lock.get("schema") != "eldq0-lock/1":
        raise Q0Failure("DEPENDENCY_LOCK_PENDING", "lock schema unknown")
    if lock.get("status") != "final":
        raise Q0Failure("DEPENDENCY_LOCK_PENDING", f"dependency lock status is {lock.get('status')!r}, not 'final'",
                        lock.get("unresolved"))
    for key in ("astra_001", "review_003"):
        ref = (lock.get("provenance") or {}).get(key) or {}
        if not (is_hex(ref.get("deliverable"), 40) and is_hex(ref.get("report"), 40)):
            raise Q0Failure("DEPENDENCY_LOCK_PENDING", f"lock provenance {key} lacks exact deliverable/report SHAs")
    plat = lock.get("platform") or {}
    if plat.get("os") != "Windows" or plat.get("machine") != "AMD64" or not re.fullmatch(r"3\.\d+\.\d+", str(plat.get("python"))):
        raise Q0Failure("DEPENDENCY_LOCK_PENDING", "lock platform must pin Windows/AMD64 and an exact Python version")
    pkgs = {}
    for p in lock.get("packages") or []:
        name = canonical(p["name"])
        if name in pkgs:
            raise Q0Failure("DEPENDENCY_LOCK_PENDING", f"duplicate lock entry {name}")
        if not _EXACT.match(str(p.get("version"))) or not str(p.get("filename", "")).endswith(".whl") \
                or not is_hex(p.get("sha256"), 64) or not str(p.get("index_url", "")).startswith("https://"):
            raise Q0Failure("DEPENDENCY_LOCK_PENDING", f"lock entry {name} lacks exact version/wheel/sha256/https index")
        pkgs[name] = p
    missing = [d for d in REQUIRED_DISTRIBUTIONS if canonical(d) not in pkgs]
    if missing:
        raise Q0Failure("DEPENDENCY_LOCK_PENDING", "lock lacks required distributions", missing)
    for name, version in FIXED_VERSIONS.items():
        if pkgs[canonical(name)]["version"] != version:
            raise Q0Failure("DEPENDENCY_LOCK_PENDING", f"{name} must be {version}")
    cuda = lock.get("cuda") or {}
    if cuda.get("device_capability") != [12, 0] or cuda.get("required_arch") != "sm_120" or not cuda.get("torch_cuda_version"):
        raise Q0Failure("DEPENDENCY_LOCK_PENDING", "lock must pin the torch CUDA runtime and sm_120 support")
    triton = lock.get("triton_policy")
    if triton not in ("absent", "present"):
        raise Q0Failure("DEPENDENCY_LOCK_PENDING", "lock must state triton_policy absent|present")
    if triton == "present" and "triton" not in pkgs and "triton-windows" not in pkgs:
        raise Q0Failure("DEPENDENCY_LOCK_PENDING", "triton_policy present requires a locked triton wheel")
    return pkgs


def requirements_text(lock: dict) -> str:
    """pip requirements with one exact pin and one sha256 per wheel, for
    `pip install --no-index --no-deps --require-hashes --find-links <wheelhouse> -r <file>`."""
    pkgs = validate_lock(lock)
    lines = [f"{p['name']}=={p['version']} --hash=sha256:{p['sha256']}" for _, p in sorted(pkgs.items())]
    return "\n".join(lines) + "\n"


def verify_wheelhouse(lock: dict, wheelhouse: Path) -> dict:
    """The wheelhouse must hold exactly the locked wheel files with matching SHA-256 (plus the generated requirements file)."""
    from .hashing import file_digests
    pkgs = validate_lock(lock)
    want = {p["filename"]: p["sha256"] for p in pkgs.values()}
    present = sorted(p.name for p in Path(wheelhouse).iterdir() if p.is_file())
    extra = [n for n in present if n not in want and n != "requirements.lock.txt"]
    missing = sorted(set(want) - set(present))
    if missing or extra:
        raise Q0Failure("HASH_MISMATCH", "wheelhouse differs from the lock", {"missing": missing, "extra": extra})
    rows = []
    for name, sha in sorted(want.items()):
        d = file_digests(Path(wheelhouse) / name, git_blob=False)
        rows.append({"wheel": name, "size": d["size"], "sha256": d["sha256"], "ok": d["sha256"] == sha})
        if d["sha256"] != sha:
            raise Q0Failure("HASH_MISMATCH", f"wheel digest mismatch: {name}", rows[-1])
    return {"wheels": rows}


def verify_installed(lock: dict, installed: dict[str, str], importable) -> dict:
    """installed: canonical distribution name -> version for the whole venv.
    importable: callable(module_name) -> bool (find_spec based; does not import)."""
    pkgs = validate_lock(lock)
    allowed_tooling = {canonical(n) for n in lock.get("allowed_unlocked_tooling", ["pip"])}
    want = {n: p["version"] for n, p in pkgs.items()}
    have = {canonical(k): v for k, v in installed.items()}
    wrong = {n: {"locked": v, "installed": have.get(n)} for n, v in want.items() if have.get(n) != v}
    extra = sorted(n for n in have if n not in want and n not in allowed_tooling)
    if wrong or extra:
        raise Q0Failure("DEPENDENCY_MISMATCH", "installed distributions differ from the lock", {"wrong": wrong, "extra": extra})
    forbidden = list(ALWAYS_FORBIDDEN_IMPORTABLE) + (["triton"] if lock["triton_policy"] == "absent" else [])
    present = [m for m in forbidden if importable(m)]
    if present:
        raise Q0Failure("DEPENDENCY_MISMATCH", "forbidden optional backends are importable", present)
    if lock["triton_policy"] == "present" and not importable("triton"):
        raise Q0Failure("DEPENDENCY_MISMATCH", "lock requires triton but it is not importable")
    return {"distributions": len(have), "triton_policy": lock["triton_policy"], "forbidden_absent": forbidden}
