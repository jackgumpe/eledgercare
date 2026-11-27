"""Reviewer helpers. WP-0044 reviewer's frozen x64 Win32 file/job/event ABI is reused."""
import ctypes as ct
from ctypes import wintypes as wt
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "WP-0044"
sys.path.append(str(OLD))
import win

HOME = Path.home() / "eLedgerCare-Speed" / "WP-0045" / "eld-rd-reviewer"
BASE = Path(sys._base_executable).resolve()
SCHEDULE = HERE.parents[1] / "coordination" / "WP-0045" / "schedule.json"
ENV_KEYS = "PYTHONHOME PYTHONPATH PYTHONSAFEPATH PYTHONNOUSERSITE PYTHONUSERBASE PYTHONHASHSEED PYTHONUTF8 PYTHONWARNINGS PYTHONIOENCODING VIRTUAL_ENV CUDA_VISIBLE_DEVICES CUBLAS_WORKSPACE_CONFIG OMP_NUM_THREADS MKL_NUM_THREADS OPENBLAS_NUM_THREADS".split()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False)+"\n",
                          encoding="utf8", newline="\n")


def ordinary():
    adv = ct.WinDLL("advapi32", use_last_error=True)
    query = adv.GetTokenInformation
    query.argtypes = [win.H, wt.DWORD, win.PTR, wt.DWORD, ct.POINTER(wt.DWORD)]
    open_token = adv.OpenProcessToken
    open_token.argtypes = [win.H, wt.DWORD, ct.POINTER(win.H)]
    token = win.H()
    win.checked(open_token(win.process(), 8, ct.byref(token)))
    try:
        elevation, size = wt.DWORD(), wt.DWORD()
        win.checked(query(token,20,ct.byref(elevation),ct.sizeof(elevation),ct.byref(size)))
        query(token,25,None,0,ct.byref(size))
        buf=ct.create_string_buffer(size.value)
        win.checked(query(token,25,buf,len(buf),ct.byref(size)))
        sid = ct.cast(buf, ct.POINTER(ct.c_void_p))[0]
        count=ct.c_ubyte.from_address(sid+1).value
        rid=wt.DWORD.from_address(sid+8+4*(count-1)).value
        admin=bool(ct.WinDLL("shell32").IsUserAnAdmin())
        facts = {"elevated": elevation.value, "integrity_rid": rid, "effective_admin":admin}
        if elevation.value or admin or rid != 8192:
            raise PermissionError(f"requires ordinary medium user: {facts}")
        return facts
    finally:
        win.close(token)


def runtime():
    cfg_paths = [BASE.parent/"pyvenv.cfg",BASE.parent.parent/"pyvenv.cfg"]
    assert sys.flags.no_site and sys.flags.isolated
    flags = {k:getattr(sys.flags,k) for k in dir(sys.flags)
             if not k.startswith("_") and k not in {"n_fields","n_sequence_fields","n_unnamed_fields"}
             and isinstance(getattr(sys.flags,k), int)}
    selected = {}
    for name in ("ctypes","os","sys","json","hashlib","pathlib","win","common"):
        spec = sys.modules[name].__spec__
        origin = spec.origin
        selected[name] = [origin,sha(origin)] if origin not in {"frozen","built-in"} else [origin]
    return {"version":sys.version, "executable":sys.executable, "base_executable":sys._base_executable,
            "prefix":sys.prefix, "base_prefix":sys.base_prefix, "exec_prefix":sys.exec_prefix,
            "base_exec_prefix":sys.base_exec_prefix, "flags":flags, "path":sys.path.copy(),
            "pyvenv_cfg":[[str(p),sha(p) if p.is_file() else None] for p in cfg_paths],
            "effective_pth":[], "sitecustomize": "sitecustomize" in sys.modules,
            "site_loaded": "site" in sys.modules, "modules":selected,
            "env":{k:os.environ.get(k) for k in ENV_KEYS},
            "coverage":"isolated -S startup (no site processing); selected origins at pre-original cut"}


def module_inventory():
    snapshot=list(sys.modules.items())
    result={}
    for name, module in snapshot:
        origin=getattr(getattr(module,"__spec__",None),"origin",None)
        file=getattr(module,"__file__",None)
        if origin in {"built-in","frozen"}:
            result[name]=[origin]
        elif file and Path(file).is_file():
            result[name]=[str(Path(file).resolve()),sha(file)]
        else:
            result[name]=[None]
    return result


def worker_command(work, selection):
    return [str(BASE), "-I","-S","-B",str(HERE/"worker.py"), str(selection)]


def clean_env():
    return {"SystemRoot":os.environ["SystemRoot"],"USERPROFILE":str(Path.home()),"OMP_NUM_THREADS":"1",
            "OPENBLAS_NUM_THREADS":"1","MKL_NUM_THREADS":"1"}


def image_id():
    handle=win.file(BASE,win.READ,1)
    try:
        return dict(id=win.ident(handle), sha256=win.digest(handle))
    finally:
        win.close(handle)


def stream_inventory(data):
    return [{"name":"original.bin","length":len(data),"sha256":hashlib.sha256(data).hexdigest()}]


def filesystem(handle):
    f=win.fn("GetVolumeInformationByHandleW",win.BOOL,win.H,wt.LPWSTR,wt.DWORD,win.PTR,
             win.PTR,win.PTR,wt.LPWSTR,wt.DWORD)
    buf=ct.create_unicode_buffer(32)
    win.checked(f(handle,None,0,None,None,None,buf,len(buf)))
    return buf.value
