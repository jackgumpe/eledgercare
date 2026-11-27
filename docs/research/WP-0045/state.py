"""Fixed-cut process configuration and private atomic sidecar messages."""
import hashlib
import json
import os
from pathlib import Path
import sys

import win

HERE = Path(__file__).resolve().parent
STAGE = HERE / "stage.py"
FLAGS = ["-I", "-S", "-B"]
def role_root():
    return Path.home() / "eLedgerCare-Speed/WP-0045/eld-owner-probe"
ENV_NAMES = ["SystemRoot", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
             "PYTHONHOME", "PYTHONPATH", "PYTHONSAFEPATH", "PYTHONUSERBASE", "PYTHONNOUSERSITE",
             "PYTHONDONTWRITEBYTECODE", "PYTHONUTF8", "PYTHONHASHSEED", "VIRTUAL_ENV",
             "CUDA_VISIBLE_DEVICES", "CUBLAS_WORKSPACE_CONFIG", "PATH"]
MODULES = ["__main__", "state", "win", "ctypes", "_ctypes", "_winapi", "os", "sys",
           "hashlib", "_hashlib", "json", "subprocess", "pathlib", "sitecustomize", "usercustomize"]
ORIGINAL = "original.bin"

def encode(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")

def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def read(path):
    return json.loads(Path(path).read_bytes())

def save(path, data):
    path = Path(path)
    with path.open("x", encoding="utf-8", newline="\n") as out:
        json.dump(data, out, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False)
        out.write("\n")

def publish(path, data):
    path = Path(path)
    temp = path.with_suffix(".pending")
    save(temp, data)
    temp.rename(path)

def env():
    return {"SystemRoot": os.environ["SystemRoot"], "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}

def argv(role, selection):
    return [str(win.BASE), *FLAGS, str(STAGE), role, str(selection)]

def path_label(value, arm):
    path = Path(value).absolute()
    for root, label in [(arm, "@arm"), (HERE, "@source"), (Path(sys.base_prefix), "@base"),
                        (Path(sys.base_prefix).parent, "@base-parent")]:
        if path.is_relative_to(root):
            suffix = path.relative_to(root).as_posix()
            return label if suffix == "." else label + "/" + suffix
    return str(path)

def command(values, arm):
    return [path_label(x, arm) if Path(x).is_absolute() else x for x in values]

def snapshot(arm):
    """After deterministic imports, before opening any original or creating the worker."""
    script = {"path": path_label(sys.argv[0], arm), "sha256": sha(sys.argv[0])}
    actual = {"cwd": os.getcwd(), "argv": sys.argv, "orig_argv": sys.orig_argv,
              "path": sys.path, "exe": sys.executable, "base_exe": sys._base_executable,
              "prefix": sys.prefix, "base_prefix": sys.base_prefix}
    cmd = {"cwd": path_label(os.getcwd(), arm), "argv": command(sys.argv, arm),
           "orig_argv": command(sys.orig_argv, arm), "script": script}
    cmd_at = win.clock()
    import ctypes
    import _hashlib
    mods = {}
    for key in MODULES:
        module = sys.modules.get(key)
        if module is None:
            mods[key] = {"loaded": False}
            continue
        origin = getattr(getattr(module, "__spec__", None), "origin", None)
        if origin in ("built-in", "frozen"):
            mods[key] = {"kind": origin}
        else:
            f = Path(module.__file__)
            mods[key] = {"path": path_label(f, arm), "sha256": sha(f)}
    flags = {k: getattr(sys.flags, k) for k in dir(sys.flags)
             if not k.startswith("_") and k not in ("n_fields", "n_sequence_fields", "n_unnamed_fields")
             and isinstance(getattr(sys.flags, k), (int, bool))}
    configs = {}
    for f in [Path(sys.executable).parent / "pyvenv.cfg", Path(sys.executable).parent.parent / "pyvenv.cfg"]:
        configs[path_label(f, arm)] = sha(f) if f.is_file() else None
    # -S suppresses site processing. Document any visible customization and
    # all effective pth files; with site imported, this coverage is undefined.
    if not sys.flags.no_site or "site" in sys.modules:
        raise ValueError("site processing outside frozen direct route")
    runtime = {"flags": flags, "version": sys.version, "exe": path_label(sys.executable, arm),
               "base_exe": path_label(sys._base_executable, arm), "prefix": path_label(sys.prefix, arm),
               "base_prefix": path_label(sys.base_prefix, arm), "sys_path": [path_label(p, arm) for p in sys.path],
               "pyvenv_cfg": configs, "effective_pth": [], "site_loaded": "site" in sys.modules,
               "sitecustomize": [path_label(f, arm) for p in sys.path
                                 if (f := Path(p) / "sitecustomize.py").is_file()],
               "environment": {k: os.environ.get(k) for k in ENV_NAMES},
               "environment_names": sorted(os.environ), "modules": mods,
               "image_sha256": sha(sys.executable)}
    return {"command": cmd, "runtime": runtime, "raw_paths": actual, "cut": win.clock(), "command_start": cmd_at}

def wait_for(path):
    import time
    end = time.monotonic() + 16
    while not path.is_file():
        if time.monotonic() >= end:
            raise TimeoutError(f"timeout waiting for {path.name}")
        time.sleep(.005)
