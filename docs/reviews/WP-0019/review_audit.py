"""WP-0019 reviewer audit wrapper (eld-rd-reviewer). Runs an author Python entry point unchanged under a
sys.addaudithook observer, so the replay records every file open, directory listing, subprocess and socket
event. Opens below any --deny prefix (ground truth, scores, keys, archive references) raise PermissionError
and are recorded as violations. The log is written once at exit; no event changes recognition inputs.

usage: python -I review_audit.py --log LOG [--deny DIR ...] [--add-script-dir] -- script.py [args...]
"""
import atexit
import json
import os
import runpy
import sys
import time

argv = sys.argv[1:]
if "--" not in argv:
    raise SystemExit(__doc__)
cut = argv.index("--")
opts, target = argv[:cut], argv[cut + 1:]
log_path, deny, add_dir = None, [], False
i = 0
while i < len(opts):
    if opts[i] == "--log":
        log_path = opts[i + 1]; i += 2
    elif opts[i] == "--deny":
        deny.append(os.path.normcase(os.path.abspath(opts[i + 1]))); i += 2
    elif opts[i] == "--add-script-dir":
        add_dir = True; i += 1
    else:
        raise SystemExit(f"unknown option {opts[i]}")
if not log_path or not target:
    raise SystemExit(__doc__)

events, violations = [], []
counts = {}
WATCH = {"open", "os.listdir", "os.scandir", "os.remove", "os.rename", "shutil.rmtree", "subprocess.Popen", "os.system",
         "os.startfile", "socket.connect", "socket.getaddrinfo", "socket.bind", "urllib.Request", "ctypes.dlopen", "os.exec",
         "os.spawn", "os.posix_spawn", "_winapi.CreateProcess", "winreg.OpenKey"}
_inside = [False]


def _path_of(arg):
    try:
        if isinstance(arg, int):
            return None
        return os.path.normcase(os.path.abspath(os.fsdecode(arg)))
    except Exception:
        return None


def hook(event, args):
    if event not in WATCH or _inside[0]:
        return
    _inside[0] = True
    try:
        counts[event] = counts.get(event, 0) + 1
        rec = dict(t=time.perf_counter_ns(), event=event)
        if event in ("open", "os.listdir", "os.scandir", "os.remove", "os.rename", "shutil.rmtree", "os.startfile"):
            p = _path_of(args[0]) if args else None
            rec["path"] = p
            if event == "open" and len(args) > 1:
                rec["mode"] = str(args[1])
            if p and any(p == d or p.startswith(d + os.sep) for d in deny):
                violations.append(rec)
                raise PermissionError(f"WP-0019 reviewer audit: denied {p}")
        elif event == "subprocess.Popen":
            exe, argv_ = args[0], args[1]
            rec["executable"] = None if exe is None else os.fsdecode(exe)
            rec["argv"] = ([os.fsdecode(a) if isinstance(a, (str, bytes, os.PathLike)) else str(a) for a in argv_]
                           if isinstance(argv_, (list, tuple)) else str(argv_))
            rec["cwd"] = None if len(args) < 3 or args[2] is None else str(args[2])
        elif event in ("_winapi.CreateProcess", "os.system", "os.exec", "os.spawn", "os.posix_spawn"):
            rec["args"] = [str(a)[:600] for a in args]
        elif event.startswith("socket") or event == "urllib.Request":
            rec["args"] = [str(a)[:200] for a in args]
            violations.append(dict(rec, note="network event"))
        else:
            rec["args"] = [str(a)[:300] for a in args]
        if len(events) < 200000:
            events.append(rec)
    finally:
        _inside[0] = False


def write_log():
    _inside[0] = True
    data = dict(kind="wp0019-review-audit", target=target, deny=deny, python=sys.version, executable=sys.executable,
                flags=str(sys.flags), counts=counts, violations=violations, events=events,
                truncated=len(events) >= 200000)
    with open(log_path, "x", encoding="utf-8") as f:
        json.dump(data, f, indent=0)
        f.flush()
        os.fsync(f.fileno())


atexit.register(write_log)
sys.addaudithook(hook)
script = os.path.abspath(target[0])
sys.argv = [script] + target[1:]
if add_dir:
    sys.path.insert(0, os.path.dirname(script))
runpy.run_path(script, run_name="__main__")
