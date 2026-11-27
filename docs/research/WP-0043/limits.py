"""Windows hard process-commit ceiling and exclusive Windows file handle."""
import ctypes as C
from ctypes import wintypes as W
from contextlib import contextmanager

class Basic(C.Structure):
    _fields_=[("process_time",C.c_longlong),("job_time",C.c_longlong),("flags",W.DWORD),
              ("min_ws",C.c_size_t),("max_ws",C.c_size_t),("active",W.DWORD),("affinity",C.c_size_t),
              ("priority",W.DWORD),("schedule",W.DWORD)]

class Counters(C.Structure):
    _fields_=[(name,C.c_ulonglong) for name in ("reads","writes","other","read_bytes","write_bytes","other_bytes")]

class Extended(C.Structure):
    _fields_=[("basic",Basic),("io",Counters),("process_commit",C.c_size_t),("job_commit",C.c_size_t),
              ("peak_process",C.c_size_t),("peak_job",C.c_size_t)]


def winapi():
    k=C.WinDLL("kernel32",use_last_error=True)
    for name,params,result in (
        ("CreateFileW",[W.LPCWSTR,W.DWORD,W.DWORD,W.LPVOID,W.DWORD,W.DWORD,W.HANDLE],W.HANDLE),
        ("CreateJobObjectW",[W.LPVOID,W.LPCWSTR],W.HANDLE),
        ("SetInformationJobObject",[W.HANDLE,C.c_int,W.LPVOID,W.DWORD],W.BOOL),
        ("AssignProcessToJobObject",[W.HANDLE,W.HANDLE],W.BOOL),
        ("QueryInformationJobObject",[W.HANDLE,C.c_int,W.LPVOID,W.DWORD,W.LPVOID],W.BOOL),
        ("CloseHandle",[W.HANDLE],W.BOOL)):
        f=getattr(k,name)
        f.argtypes=params
        f.restype=result
    return k


@contextmanager
def device_lock(path):
    k=winapi()
    # OPEN_EXISTING; never replace, truncate, unlink or take ownership of another lock file.
    h=k.CreateFileW(str(path),0xC0000000,0,None,3,128,None)
    if h==W.HANDLE(-1).value:
        raise C.WinError(C.get_last_error())
    try:
        yield
    finally:
        k.CloseHandle(h)


class ThreadEntry(C.Structure):
    _fields_=[("size",W.DWORD),("usage",W.DWORD),("tid",W.DWORD),("pid",W.DWORD),
              ("base_priority",C.c_long),("delta_priority",C.c_long),("flags",W.DWORD)]


def resume_job_child(k,pid):
    # Popen closes the thread HANDLE. Enumerate the still-suspended initial thread.
    for name,params,result in (
        ("CreateToolhelp32Snapshot",[W.DWORD,W.DWORD],W.HANDLE),
        ("Thread32First",[W.HANDLE,C.POINTER(ThreadEntry)],W.BOOL),
        ("Thread32Next",[W.HANDLE,C.POINTER(ThreadEntry)],W.BOOL),
        ("OpenThread",[W.DWORD,W.BOOL,W.DWORD],W.HANDLE),("ResumeThread",[W.HANDLE],W.DWORD)):
        f=getattr(k,name)
        f.argtypes=params
        f.restype=result
    snapshot=k.CreateToolhelp32Snapshot(4,0)
    if snapshot==W.HANDLE(-1).value:
        raise C.WinError(C.get_last_error())
    entries=[]
    try:
        e=ThreadEntry()
        e.size=C.sizeof(e)
        found=k.Thread32First(snapshot,C.byref(e))
        while found:
            if e.pid==pid:
                entries.append(e.tid)
            found=k.Thread32Next(snapshot,C.byref(e))
    finally:
        k.CloseHandle(snapshot)
    if len(entries)!=1:
        raise RuntimeError("unbound suspended child threads")
    thread=k.OpenThread(2,False,entries[0])
    if not thread:
        raise C.WinError(C.get_last_error())
    try:
        if k.ResumeThread(thread)!=1:
            raise RuntimeError("unexpected suspension count")
    finally:
        k.CloseHandle(thread)


@contextmanager
def job(proc,limit):
    k=winapi()
    h=k.CreateJobObjectW(None,None)
    if not h:
        raise C.WinError(C.get_last_error())
    try:
        data=Extended()
        data.basic.flags=0x00002000|0x00000200  # kill job on handle close; aggregate committed memory
        data.job_commit=limit
        if not k.SetInformationJobObject(h,9,C.byref(data),C.sizeof(data)):
            raise C.WinError(C.get_last_error())
        if not k.AssignProcessToJobObject(h,int(proc._handle)):
            raise C.WinError(C.get_last_error())
        resume_job_child(k,proc.pid)
        yield h
    finally:
        k.CloseHandle(h)


def job_member(pid,handle):
    k=winapi()
    k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD]
    k.OpenProcess.restype=W.HANDLE
    k.IsProcessInJob.argtypes=[W.HANDLE,W.HANDLE,C.POINTER(W.BOOL)]
    k.IsProcessInJob.restype=W.BOOL
    process=k.OpenProcess(0x1000,False,pid)
    if not process:
        raise C.WinError(C.get_last_error())
    try:
        result=W.BOOL()
        if not k.IsProcessInJob(process,handle,C.byref(result)):
            raise C.WinError(C.get_last_error())
        return bool(result)
    finally:
        k.CloseHandle(process)
