"""Owned storage-root checks and construction of the execution child's environment.

The child environment is built from an explicit allowlist, never inherited wholesale, so
credentials and model behaviour switches present in the operator's shell cannot leak in.
Nothing here changes user/global configuration; it only shapes the child's environment.
"""

from __future__ import annotations

import os
import re
from pathlib import Path, PureWindowsPath

from .outcome import Q0Failure

SUBDIRS = {
    "hf_home": "hf-home",
    "models": "models",
    "wheelhouse": "wheelhouse",
    "venv": "venv",
    "runs": "runs",
}
OWNERS = ("author", "reviewer")

# Inherited verbatim only if present (Windows process essentials; no user data).
PASSTHROUGH = ("SystemRoot", "SYSTEMROOT", "windir", "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE",
               "PROCESSOR_IDENTIFIER", "PROCESSOR_LEVEL", "PROCESSOR_REVISION", "OS", "PATHEXT", "ComSpec")

# Names that alter the pinned model code's behaviour (grepped from the pinned sources) or
# Hugging Face / CUDA / Python behaviour, plus anything credential-shaped. None may reach
# the child; the allowlist construction guarantees it and audit_child_env re-checks.
FORBIDDEN_EXACT = {
    "TIME_DIAG", "TIME_DIAG_INTERVAL", "WARMUP_MAIN_LOCAL_WINDOW", "PAGE_SCOPE_PREFILL", "CODE_STAMP_LOG",
    "INDEXER_SCORE_TRITON", "FUSED_CHUNK_CE", "CE_CHUNK_SIZE", "KL_QUERY_STRIDE", "KL_CHUNK_RECOMPUTE",
    "PYTORCH_CUDA_ALLOC_CONF", "CUBLAS_WORKSPACE_CONFIG", "CUDA_LAUNCH_BLOCKING", "HF_ENDPOINT",
    "PYTHONPATH", "PYTHONSTARTUP", "PYTHONHOME", "PYTHONUSERBASE", "PYTHONINSPECT", "PYTHONBREAKPOINT",
}
FORBIDDEN_PATTERNS = (
    re.compile(r"^DASH_"), re.compile(r"^KL_"), re.compile(r"^SGLANG_"), re.compile(r"^TORCHDYNAMO_"),
    re.compile(r"^TORCH_COMPILE"), re.compile(r"TOKEN", re.I), re.compile(r"SECRET", re.I),
    re.compile(r"PASSWORD", re.I), re.compile(r"API_?KEY", re.I), re.compile(r"CREDENTIAL", re.I),
    re.compile(r"^AWS_"), re.compile(r"^AZURE_"), re.compile(r"^ANTHROPIC"), re.compile(r"^OPENAI"),
    re.compile(r"^GH_|^GITHUB_"),
)


def layout(root: Path, owner: str) -> dict[str, Path]:
    if owner not in OWNERS:
        raise Q0Failure("STORAGE_NOT_OWNED", f"unknown run owner {owner!r}")
    root = Path(root)
    p = {k: root / v for k, v in SUBDIRS.items()}
    p["modules_cache"] = p["hf_home"] / "modules"
    p["run_owner"] = p["runs"] / owner
    return p


def _norm(p) -> str:
    return os.path.normcase(os.path.abspath(str(p))).rstrip("\\/")


def _inside(child, parent) -> bool:
    c, pa = _norm(child), _norm(parent)
    return c == pa or c.startswith(pa + os.sep)


def check_storage_root(root: Path, *, expected_root: str, forbidden_parents: list[str]) -> None:
    """The root must equal the coordinator-selected task root and lie outside every
    forbidden parent (repository worktrees, shared temp, user caches)."""
    if _norm(root) != _norm(expected_root):
        raise Q0Failure("STORAGE_NOT_OWNED", f"storage root {root} is not the selected task root {expected_root}")
    for parent in forbidden_parents:
        if parent and (_inside(root, parent) or _inside(parent, root)):
            raise Q0Failure("STORAGE_NOT_OWNED", f"storage root overlaps forbidden location {parent}")


def default_forbidden_parents(repo_root: Path, environ: dict) -> list[str]:
    out = [str(repo_root), str(Path(repo_root).parent)]
    for key in ("TEMP", "TMP", "LOCALAPPDATA", "APPDATA"):
        if environ.get(key):
            out.append(environ[key])
    home = environ.get("USERPROFILE")
    if home:
        out += [str(Path(home) / ".cache"), str(Path(home) / ".cache" / "huggingface")]
    return out


def check_run_dir(run_dir: Path, root: Path, owner: str) -> None:
    if not _inside(run_dir, layout(root, owner)["run_owner"]) or _norm(run_dir) == _norm(layout(root, owner)["run_owner"]):
        raise Q0Failure("STORAGE_NOT_OWNED", f"run directory {run_dir} is not a new subdirectory of runs/{owner}")


def build_child_env(parent_env: dict, *, root: Path, owner: str, run_dir: Path, gpu_uuid: str) -> dict:
    p = layout(root, owner)
    check_run_dir(run_dir, root, owner)
    system_root = parent_env.get("SystemRoot") or parent_env.get("SYSTEMROOT") or r"C:\Windows"
    env = {k: parent_env[k] for k in PASSTHROUGH if k in parent_env}
    tmp = Path(run_dir) / "tmp"
    scripts = p["venv"] / "Scripts"
    env.update({
        "PATH": os.pathsep.join([str(scripts), str(PureWindowsPath(system_root) / "System32"), system_root]),
        "VIRTUAL_ENV": str(p["venv"]),
        "TEMP": str(tmp), "TMP": str(tmp),
        "USERPROFILE": str(Path(run_dir) / "home"), "HOME": str(Path(run_dir) / "home"),
        "HF_HOME": str(p["hf_home"]),
        "HF_MODULES_CACHE": str(Path(run_dir) / "hf-modules"),
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1", "HF_HUB_DISABLE_PROGRESS_BARS": "1",
        "TORCH_HOME": str(Path(run_dir) / "torch-home"),
        "TRITON_CACHE_DIR": str(Path(run_dir) / "triton-cache"),
        "TORCHINDUCTOR_CACHE_DIR": str(Path(run_dir) / "inductor-cache"),
        "XDG_CACHE_HOME": str(Path(run_dir) / "xdg-cache"),
        "CUDA_DEVICE_ORDER": "PCI_BUS_ID",
        "CUDA_VISIBLE_DEVICES": gpu_uuid,
        "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0", "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",
    })
    audit_child_env(env, root=root, owner=owner, run_dir=run_dir)
    return env


def audit_child_env(env: dict, *, root: Path, owner: str, run_dir: Path) -> None:
    violations = []
    for k in env:
        if k in FORBIDDEN_EXACT or any(rx.search(k) for rx in FORBIDDEN_PATTERNS):
            violations.append(k)
    if violations:
        raise Q0Failure("SAFETY_VIOLATION", "forbidden variables in child environment", sorted(violations))
    for k in ("TEMP", "TMP", "HF_MODULES_CACHE", "TORCH_HOME", "TRITON_CACHE_DIR", "TORCHINDUCTOR_CACHE_DIR",
              "XDG_CACHE_HOME", "USERPROFILE", "HOME"):
        if not _inside(env[k], run_dir):
            raise Q0Failure("STORAGE_NOT_OWNED", f"{k} not inside the owned run directory")
    if not _inside(env["HF_HOME"], root):
        raise Q0Failure("STORAGE_NOT_OWNED", "HF_HOME outside the owned root")
    if env.get("HF_HUB_OFFLINE") != "1" or env.get("TRANSFORMERS_OFFLINE") != "1":
        raise Q0Failure("SAFETY_VIOLATION", "child must be offline (no Hub requests at runtime)")
