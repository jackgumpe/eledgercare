"""Inert CPython fixture. Hold the observation cut before emitting four bytes."""
import hashlib
import json
import os
from pathlib import Path
import site
import sys
import time

MODULE_CUT = sorted(sys.modules.items())
ROOTS = [(Path(sys.prefix), "@venv"), (Path(sys.base_prefix), "@base"),
         (Path(__file__).resolve().parent, "@source")]
ENV_KEYS = ("PYTHONHOME", "PYTHONPATH", "PYTHONSAFEPATH",
            "CUBLAS_WORKSPACE_CONFIG", "CUDA_VISIBLE_DEVICES")


def label(path):
    absolute = Path(path).resolve()
    for root, token in ROOTS:
        if absolute.is_relative_to(root):
            relative = absolute.relative_to(root).as_posix()
            return token if relative == "." else token + "/" + relative
    raise ValueError("effective path outside declared roots")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def file_info(path):
    return {"path": label(path), "sha256": digest(path)}


def observe():
    modules = []
    for name, module in MODULE_CUT:
        spec = getattr(module, "__spec__", None)
        origin = getattr(spec, "origin", None)
        if origin in ("built-in", "frozen"):
            record = {"kind": origin}
        else:
            record = file_info(getattr(module, "__file__"))
        modules.append([name, record])
    cfg = Path(sys.prefix, "pyvenv.cfg")
    entries = dict(line.split(" = ", 1) for line in cfg.read_text("utf-8").splitlines())
    pth = sorted({p.resolve() for directory in site.getsitepackages()
                  for p in Path(directory).glob("*.pth")}, key=label)
    custom = sorted({p.resolve() for entry in sys.path
                     if (p := Path(entry, "sitecustomize.py")).is_file()}, key=label)
    fields = {"A.script": digest(__file__),
              "A.args": [*sys.orig_argv[1:3], label(sys.orig_argv[3]), *sys.orig_argv[4:]],
              "C.pyvenv": digest(cfg), "C.include_system": entries["include-system-site-packages"],
              "C.pth": [file_info(p) for p in pth],
              "C.sitecustomize": [file_info(p) for p in custom], "C.prefix": label(sys.prefix),
              "C.modules": modules}
    fields.update({"C." + key: os.environ.get(key) for key in ENV_KEYS})
    # The cut above precedes observation-only native imports. Each value below
    # comes from the fixture's own process or stdout handle.
    import ctypes as ct
    import msvcrt
    from ctypes import wintypes as wt
    kernel = ct.WinDLL("kernel32", use_last_error=True)
    clocks = [ct.c_ulonglong() for _ in range(4)]
    if not kernel.GetProcessTimes(ct.c_void_p(-1), *(ct.byref(t) for t in clocks)):
        raise ct.WinError(ct.get_last_error())
    stdout_id = None
    if os.environ.get("ELD44_MANIFEST") != "1":
        info = (wt.DWORD * 13)()
        if not kernel.GetFileInformationByHandle(ct.c_void_p(msvcrt.get_osfhandle(1)), info):
            raise ct.WinError(ct.get_last_error())
        stdout_id = [info[7], (info[11] << 32) + info[12]]
    return {"fields": fields, "self_instance": [os.getpid(), clocks[0].value],
            "stdout_id": stdout_id, "orig_argv0": label(sys.orig_argv[0]),
            "executable": label(sys.executable), "pid": os.getpid(), "parent_pid": os.getppid()}


if __name__ == "__main__":
    observation = observe()
    if os.environ.get("ELD44_MANIFEST") == "1":
        print(json.dumps(observation, ensure_ascii=True))
    else:
        directory = Path(os.environ["ELD44_ARM"])
        temporary = directory / "worker.tmp"
        temporary.write_text(json.dumps(observation, ensure_ascii=True), encoding="utf-8")
        temporary.rename(directory / "worker.json")
        start = time.monotonic()
        while not (directory / "release").exists():
            if time.monotonic() - start > 15:
                raise TimeoutError("fixture observation gate")
            time.sleep(.01)
        os.write(1, b"F07\n")
