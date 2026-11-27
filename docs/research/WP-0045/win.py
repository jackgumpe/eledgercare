"""Ordinary-user, own-child observation. ABI and file helpers adapted from
eld-owner-probe WP-0044 win_observer.py at 8e78cc23abbc796b846ce59284ff46f66fde866b.
64-bit Windows only. The only process handles are self and returned new-child handles.
"""
import _winapi
import ctypes as ct
from ctypes import wintypes as wt
from contextlib import contextmanager
import hashlib
import msvcrt
import os
from pathlib import Path
import subprocess
import sys
import time

K = ct.WinDLL("kernel32", use_last_error=True)
ADV = ct.WinDLL("advapi32", use_last_error=True)
H, D, P, B, W = wt.HANDLE, wt.DWORD, ct.c_void_p, wt.BOOL, wt.LPCWSTR
READ, WRITE, SHARE_R, SHARE_W = 0x80000000, 0x40000000, 1, 2
SELF = -1
BASE = Path(sys.base_prefix) / "python.exe"
clock = time.perf_counter_ns

def bind(lib, name, result, *params):
    fn = getattr(lib, name)
    fn.restype, fn.argtypes = result, params
    return fn

close = bind(K, "CloseHandle", B, H)
open_file = bind(K, "CreateFileW", H, W, D, D, P, D, D, H)
info = bind(K, "GetFileInformationByHandle", B, H, P)
volume = bind(K, "GetVolumeInformationByHandleW", B, H, wt.LPWSTR, D, P, P, P, wt.LPWSTR, D)
write = bind(K, "WriteFile", B, H, P, D, P, P)
flush = bind(K, "FlushFileBuffers", B, H)
clock_process = bind(K, "GetProcessTimes", B, H, P, P, P, P)
pid = bind(K, "GetProcessId", D, H)
tid = bind(K, "GetCurrentThreadId", D)
same = bind(ct.WinDLL("kernelbase", use_last_error=True), "CompareObjectHandles", B, H, H)
wait = bind(K, "WaitForSingleObject", D, H, D)
resume = bind(K, "ResumeThread", D, H)
make_job = bind(K, "CreateJobObjectW", H, P, W)
set_job = bind(K, "SetInformationJobObject", B, H, ct.c_int, P, D)
query_job = bind(K, "QueryInformationJobObject", B, H, ct.c_int, P, D, P)
assign = bind(K, "AssignProcessToJobObject", B, H, H)
in_job = bind(K, "IsProcessInJob", B, H, H, P)
query_image = bind(K, "QueryFullProcessImageNameW", B, H, D, wt.LPWSTR, P)
debug_wait = bind(K, "WaitForDebugEvent", B, P, D)
debug_continue = bind(K, "ContinueDebugEvent", B, D, D, D)
open_token = bind(ADV, "OpenProcessToken", B, H, D, P)
token_info = bind(ADV, "GetTokenInformation", B, H, D, P, D, P)
sub_count = bind(ADV, "GetSidSubAuthorityCount", ct.POINTER(ct.c_ubyte), P)
sub_value = bind(ADV, "GetSidSubAuthority", ct.POINTER(D), P, D)

def checked(value):
    if not value:
        raise ct.WinError(ct.get_last_error())
    return value

def ordinary():
    token, needed, elevated = H(), D(), D()
    checked(open_token(SELF, 8, ct.byref(token)))
    try:
        checked(token_info(token, 20, ct.byref(elevated), 4, ct.byref(needed)))
        label = ct.create_string_buffer(256)
        checked(token_info(token, 25, label, len(label), ct.byref(needed)))
        sid = P.from_buffer(label).value
        rid = sub_value(sid, sub_count(sid)[0] - 1)[0]
        effective_admin = bool(ct.WinDLL("shell32").IsUserAnAdmin())
        if elevated.value or effective_admin or rid != 8192:
            raise PermissionError(f"requires medium non-elevated token; elevated={elevated.value}, RID={rid}")
        return {"elevated": elevated.value, "effective_admin": effective_admin, "integrity_rid": rid}
    finally:
        checked(close(token))

def file(path, rights, share, disposition=3):
    handle = open_file(str(path), rights, share, None, disposition, 0x80, None)
    if handle == P(-1).value:
        raise ct.WinError(ct.get_last_error())
    return handle

def identity(handle):
    fields = (D * 13)()
    checked(info(handle, fields))
    return [fields[7], (fields[11] << 32) + fields[12]]

def fs(handle):
    name = ct.create_unicode_buffer(64)
    checked(volume(handle, None, 0, None, None, None, name, len(name)))
    return name.value

def process(handle):
    values = [ct.c_ulonglong() for _ in range(4)]
    checked(clock_process(handle, *(ct.byref(x) for x in values)))
    return [checked(pid(handle)), values[0].value]

def current():
    return process(SELF)

def read_view(process_handle, handle):
    return _winapi.DuplicateHandle(process_handle, handle, SELF, READ, False, 0)

def as_stream(handle):
    return os.fdopen(msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY), "rb")

def fresh_read(path):
    handle = file(path, READ, SHARE_R | SHARE_W)
    with as_stream(handle) as stream:
        return {"object": identity(handle), "filesystem": fs(handle), "bytes": stream.read(5).hex(),
                "eof": stream.read(1) == b"", "at": clock()}

class Data(ct.Union):
    _fields_ = [("h", H * 20), ("dw", D * 40)]

class Event(ct.Structure):
    _fields_ = [("kind", D), ("pid", D), ("tid", D), ("body", Data)]

def image(event, job, returned):
    hfile, hprocess, hthread = event.body.h[:3]
    path, length = ct.create_unicode_buffer(32768), D(32768)
    checked(query_image(hprocess, 0, path, ct.byref(length)))
    member = B()
    checked(in_job(hprocess, job, ct.byref(member)))
    record = {"event_instance": process(hprocess), "returned_same_object": bool(same(hprocess, returned)),
              "image_path": path.value, "member": bool(member.value), "event_tid": event.tid,
              "event_pid": event.pid, "event_file": hfile, "event_process": hprocess,
              "event_thread": hthread, "at": clock()}
    if hfile:
        with as_stream(hfile) as stream:
            record["object"] = identity(hfile)
            record["sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
    return record

@contextmanager
def job_scope():
    job = checked(make_job(None, None))
    try:
        buf = ct.create_string_buffer(144)
        D.from_buffer(buf, 16).value = 0x2000
        checked(set_job(job, 9, buf, len(buf)))
        checked(query_job(job, 9, buf, len(buf), None))
        yield job, D.from_buffer(buf, 16).value
    finally:
        checked(close(job))

def launch(argv, directory, env, tick, trace):
    """Exactly one direct CPython CreateProcessW call, no inherited handles.
    DEBUG_ONLY_THIS_PROCESS delivers only the new immediate child's creation events.
    """
    ordinary()
    if Path(argv[0]) != BASE or ct.sizeof(H) != 8 or sys.version_info[:3] != (3, 12, 10):
        raise ValueError("requires absolute approved CPython 3.12.10 x64 base")
    with job_scope() as (job, policy):
        trace.update(policy=policy, argv=argv, cwd=str(directory), environment=env,
                     flags=0x08000006, inherit_handles=False, caller=current(), caller_tid=tid(),
                     command_line=subprocess.list2cmdline(argv), application=str(BASE), call=clock())
        handle, thread, child_pid, child_tid = _winapi.CreateProcess(
            str(BASE), trace["command_line"], None, None, False, 0x08000006, env,
            str(directory), subprocess.STARTUPINFO())
        try:
            trace.update(returned=clock(), handle=handle, child_tid=child_tid, child_pid=child_pid,
                         returned_instance=process(handle), caller_after=current(), caller_tid_after=tid())
            try:
                checked(assign(job, handle))
            except OSError:
                _winapi.TerminateProcess(handle, 1)  # only this newly created suspended child
                raise
            trace["assigned"] = clock()
            if resume(thread) == 0xffffffff:
                raise ct.WinError(ct.get_last_error())
            trace.update(resumed=clock(), events=[])
            stop = time.monotonic() + 24
            initial_break = False
            while time.monotonic() < stop:
                e = Event()
                if debug_wait(ct.byref(e), 5):
                    disposition = 0x00010002
                    try:
                        if e.pid != child_pid:
                            raise RuntimeError("unexpected debug notification")
                        trace["events"].append([e.kind, e.pid, e.tid, clock()])
                        if e.kind == 3:
                            trace["image"] = image(e, job, handle)
                            trace["creation_continue"] = clock()
                        elif e.kind == 6 and e.body.h[0]:
                            checked(close(e.body.h[0]))
                        elif e.kind == 5:
                            trace["exit"] = [e.body.dw[0], clock()]
                        elif e.kind == 1:
                            if e.body.dw[0] == 0x80000003 and not initial_break:
                                initial_break = True
                            else:
                                disposition = 0x80010001
                    finally:
                        checked(debug_continue(e.pid, e.tid, disposition))
                elif ct.get_last_error() != 121:
                    raise ct.WinError(ct.get_last_error())
                if "exit" in trace:
                    if trace["exit"][0] != 0:
                        raise RuntimeError(f"child exit {trace['exit'][0]}")
                    accounting = ct.create_string_buffer(48)
                    checked(query_job(job, 1, accounting, len(accounting), None))
                    trace["job_total_processes"] = D.from_buffer(accounting, 36).value
                    return
                tick(handle, trace)
            raise TimeoutError("owned child exceeded 24s")
        finally:
            close(thread)
            close(handle)
