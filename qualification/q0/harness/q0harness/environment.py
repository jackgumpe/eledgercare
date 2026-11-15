"""Owned storage-root checks and construction of the execution child's environment.

The child environment is built from an explicit allowlist, never inherited wholesale, so
credentials and model behaviour switches present in the operator's shell cannot leak in.
Nothing here changes user/global configuration; it only shapes the child's environment.
"""

from __future__ import annotations

from collections.abc import Sequence
import os
import re
import shutil
import subprocess
from pathlib import Path, PureWindowsPath

from .outcome import Q0Failure

GIT_EXECUTABLE_VAR = "Q0_GIT_EXECUTABLE"
GIT_ISOLATION_ENV = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "NUL" if os.name == "nt" else os.devnull,
    "GIT_TERMINAL_PROMPT": "0",
}

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


def validate_git_executable(path: str | os.PathLike) -> str:
    """Require an existing absolute git(.exe) binary; reject relative paths or non-git tools."""
    raw = str(path or "").strip()
    if not raw or not os.path.isabs(raw):
        raise Q0Failure("HOST_PRECHECK_FAILED", f"Git executable must be an absolute path, got {path!r}")
    p = Path(raw)
    if p.name.lower() not in ("git.exe", "git") or not p.is_file():
        raise Q0Failure("HOST_PRECHECK_FAILED", f"Git executable is missing or not a git binary: {raw}")
    return os.path.abspath(str(p))


def resolve_host_git(parent_env: dict | None = None) -> str:
    """Resolve and validate the host Git binary for explicit stage/child pinning without widening PATH."""
    env = os.environ if parent_env is None else parent_env
    if GIT_EXECUTABLE_VAR in env:
        return validate_git_executable(env[GIT_EXECUTABLE_VAR])
    candidates: list[Path] = []
    if os.name == "nt":
        for key in ("ProgramW6432", "ProgramFiles"):
            base = env.get(key)
            if base:
                candidates.append(Path(base) / "Git" / "cmd" / "git.exe")
        candidates.append(Path(r"C:\Program Files\Git\cmd\git.exe"))
    for cand in candidates:
        if os.path.isabs(str(cand)) and cand.is_file():
            return validate_git_executable(cand)
    path_val = env.get("PATH")
    if path_val:
        found = shutil.which("git", path=path_val)
        if found:
            return validate_git_executable(found)
    raise Q0Failure("HOST_PRECHECK_FAILED", "Git executable not found for isolated Q0 environment")


def resolve_runtime_git(environ: dict | None = None) -> str:
    """Resolve Git strictly from the active process environment (Q0_GIT_EXECUTABLE, else PATH)."""
    env = os.environ if environ is None else environ
    if GIT_EXECUTABLE_VAR in env:
        return validate_git_executable(env[GIT_EXECUTABLE_VAR])
    path_val = env.get("PATH")
    if path_val:
        found = shutil.which("git", path=path_val)
        if found:
            return validate_git_executable(found)
    raise Q0Failure("HOST_PRECHECK_FAILED",
                    f"Git executable unavailable ({GIT_EXECUTABLE_VAR} unset and git not on PATH)")


def run_git(args: Sequence[str], *, cwd: Path, environ: dict | None = None,
            text: bool = False, timeout_s: int = 60) -> subprocess.CompletedProcess:
    """Execute a read-only Git plumbing command with --no-optional-locks and scrubbed Git config."""
    env = dict(os.environ if environ is None else environ)
    git_exe = resolve_runtime_git(env)
    env.update(GIT_ISOLATION_ENV)
    try:
        return subprocess.run([git_exe, "--no-optional-locks", *args], cwd=str(cwd), env=env,
                              stdin=subprocess.DEVNULL, capture_output=True, text=text, timeout=timeout_s)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Q0Failure("HOST_PRECHECK_FAILED", f"Git invocation failed ({list(args[:1])}): {exc}") from exc


def build_child_env(parent_env: dict, *, root: Path, owner: str, run_dir: Path, gpu_uuid: str,
                    git_executable: str | None = None) -> dict:
    p = layout(root, owner)
    check_run_dir(run_dir, root, owner)
    git_exe = validate_git_executable(git_executable) if git_executable is not None else resolve_host_git(parent_env)
    system_root = parent_env.get("SystemRoot") or parent_env.get("SYSTEMROOT") or r"C:\Windows"
    env = {k: parent_env[k] for k in PASSTHROUGH if k in parent_env}
    tmp = Path(run_dir) / "tmp"
    scripts = p["venv"] / "Scripts"
    env.update({
        "PATH": os.pathsep.join([str(scripts), str(PureWindowsPath(system_root) / "System32"), system_root]),
        GIT_EXECUTABLE_VAR: git_exe,
        **GIT_ISOLATION_ENV,
        "VIRTUAL_ENV": str(p["venv"]),
        "TEMP": str(tmp), "TMP": str(tmp),
        "USERPROFILE": str(Path(run_dir) / "home"), "HOME": str(Path(run_dir) / "home"),
        "TMPDIR": str(tmp),
        "HF_HOME": str(p["hf_home"]),
        "HF_HUB_CACHE": str(p["hf_home"] / "hub"), "HUGGINGFACE_HUB_CACHE": str(p["hf_home"] / "hub"),
        "TRANSFORMERS_CACHE": str(p["hf_home"] / "transformers"),
        "HF_MODULES_CACHE": str(Path(run_dir) / "hf-modules"),
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_HUB_DISABLE_XET": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1", "HF_HUB_DISABLE_PROGRESS_BARS": "1",
        "TORCH_HOME": str(Path(run_dir) / "torch-home"),
        "TRITON_CACHE_DIR": str(Path(run_dir) / "triton-cache"),
        "TORCHINDUCTOR_CACHE_DIR": str(Path(run_dir) / "inductor-cache"),
        "CUDA_CACHE_PATH": str(Path(run_dir) / "cuda-cache"),
        "XDG_CACHE_HOME": str(Path(run_dir) / "xdg-cache"),
        "PIP_NO_INDEX": "1", "PIP_CONFIG_FILE": "NUL",
        "PIP_CACHE_DIR": str(Path(run_dir) / "pip-cache"), "UV_CACHE_DIR": str(Path(run_dir) / "uv-cache"),
        "CUDA_DEVICE_ORDER": "PCI_BUS_ID",
        "CUDA_VISIBLE_DEVICES": gpu_uuid,
        "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0", "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",
    })
    audit_child_env(env, root=root, owner=owner, run_dir=run_dir)
    return env


def _audit_git_pin(env: dict, *, root: Path, run_dir: Path | None = None) -> None:
    git_exe = validate_git_executable(env.get(GIT_EXECUTABLE_VAR, ""))
    if _inside(git_exe, root) or (run_dir is not None and _inside(git_exe, run_dir)):
        raise Q0Failure("SAFETY_VIOLATION", f"{GIT_EXECUTABLE_VAR} must not lie inside the mutable task root")
    for k, want in GIT_ISOLATION_ENV.items():
        if env.get(k) != want:
            raise Q0Failure("SAFETY_VIOLATION", f"{k} must be {want!r} in isolated environment")


def audit_child_env(env: dict, *, root: Path, owner: str, run_dir: Path) -> None:
    violations = []
    for k in env:
        if k in FORBIDDEN_EXACT or any(rx.search(k) for rx in FORBIDDEN_PATTERNS):
            violations.append(k)
    if violations:
        raise Q0Failure("SAFETY_VIOLATION", "forbidden variables in child environment", sorted(violations))
    _audit_git_pin(env, root=root, run_dir=run_dir)
    for k in RUN_LOCAL_VARS:
        if k not in env or not _inside(env[k], run_dir):
            raise Q0Failure("STORAGE_NOT_OWNED", f"{k} missing or not inside the owned run directory")
    for k in ("HF_HOME", "HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE", "TRANSFORMERS_CACHE"):
        if k not in env or not _inside(env[k], root):
            raise Q0Failure("STORAGE_NOT_OWNED", f"{k} missing or outside the owned root")
    if env.get("HF_HUB_OFFLINE") != "1" or env.get("TRANSFORMERS_OFFLINE") != "1":
        raise Q0Failure("SAFETY_VIOLATION", "child must be offline (no Hub requests at runtime)")


RUN_LOCAL_VARS = ("TEMP", "TMP", "TMPDIR", "HF_MODULES_CACHE", "TORCH_HOME", "TRITON_CACHE_DIR",
                  "TORCHINDUCTOR_CACHE_DIR", "CUDA_CACHE_PATH", "XDG_CACHE_HOME", "PIP_CACHE_DIR", "UV_CACHE_DIR",
                  "USERPROFILE", "HOME")
STAGE_DIRS = ("stage_temp", "pip_cache", "uv_cache")
STAGE_ROOT_VARS = ("TEMP", "TMP", "TMPDIR", "PIP_CACHE_DIR", "UV_CACHE_DIR", "HF_HOME", "HF_HUB_CACHE",
                   "HUGGINGFACE_HUB_CACHE")


def audit_stage_env(env: dict, *, root: Path, network: bool) -> None:
    bad = [k for k in env if k in FORBIDDEN_EXACT or any(rx.search(k) for rx in FORBIDDEN_PATTERNS)]
    if bad:
        raise Q0Failure("SAFETY_VIOLATION", "forbidden variables in stage environment", sorted(bad))
    _audit_git_pin(env, root=root)
    for k in STAGE_ROOT_VARS:
        if k not in env or not _inside(env[k], root):
            raise Q0Failure("STORAGE_NOT_OWNED", f"{k} missing or outside the owned root")
    if not network and (env.get("PIP_NO_INDEX") != "1" or env.get("HF_HUB_OFFLINE") != "1"
                        or env.get("TRANSFORMERS_OFFLINE") != "1"):
        raise Q0Failure("SAFETY_VIOLATION", "offline stage environment lacks offline guards")


def build_stage_env(parent_env: dict, *, root: Path, protocol: dict, network: bool,
                    git_executable: str | None = None) -> dict:
    """Environment for an acquisition (network=True) or offline installation (network=False)
    process: explicit allowlist, every cache/temp under the task root, no inherited
    credentials or pip/HF/Git configuration. Used only in separately released stages."""
    root = Path(root)
    sd = protocol["storage"]["subdirs"]
    git_exe = validate_git_executable(git_executable) if git_executable is not None else resolve_host_git(parent_env)
    system_root = parent_env.get("SystemRoot") or parent_env.get("SYSTEMROOT") or r"C:\Windows"
    env = {k: parent_env[k] for k in PASSTHROUGH if k in parent_env}
    temp = root / sd["stage_temp"]
    env.update({
        "PATH": os.pathsep.join([str(root / sd["venv"] / "Scripts"), str(PureWindowsPath(system_root) / "System32"),
                                 system_root]),
        GIT_EXECUTABLE_VAR: git_exe,
        **GIT_ISOLATION_ENV,
        "TEMP": str(temp), "TMP": str(temp), "TMPDIR": str(temp),
        "PIP_CACHE_DIR": str(root / sd["pip_cache"]), "UV_CACHE_DIR": str(root / sd["uv_cache"]),
        "PIP_CONFIG_FILE": "NUL", "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_INPUT": "1",
        "HF_HOME": str(root / sd["hf_home"]), "HF_HUB_CACHE": str(root / sd["hf_home"] / "hub"),
        "HUGGINGFACE_HUB_CACHE": str(root / sd["hf_home"] / "hub"),
        "HF_HUB_DISABLE_TELEMETRY": "1", "HF_HUB_DISABLE_XET": "1", "HF_HUB_DISABLE_PROGRESS_BARS": "1",
        "PYTHONNOUSERSITE": "1", "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1",
    })
    if not network:
        env.update({"PIP_NO_INDEX": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
    audit_stage_env(env, root=root, network=network)
    return env
