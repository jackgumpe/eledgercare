"""Small Win32 bindings for locally created, explicitly owned fixture resources (x64)."""
import ctypes as ct
from ctypes import wintypes as wt
import hashlib
import os

k = ct.WinDLL('kernel32', use_last_error=True)
DWORD, H, PTR, U64, BOOL = wt.DWORD, wt.HANDLE, ct.c_void_p, ct.c_uint64, wt.BOOL
ref = ct.byref

def fn(name, result, *args):
    f = getattr(k, name)
    f.restype, f.argtypes = result, list(args)
    return f

def checked(value):
    if not value:
        raise ct.WinError(ct.get_last_error())
    return value

close = fn('CloseHandle', BOOL, H)
open_file = fn('CreateFileW', H, wt.LPCWSTR, DWORD, DWORD, PTR, DWORD, DWORD, H)
read_file = fn('ReadFile', BOOL, H, PTR, DWORD, ct.POINTER(DWORD), PTR)
write_file = fn('WriteFile', BOOL, H, PTR, DWORD, ct.POINTER(DWORD), PTR)
seek = fn('SetFilePointerEx', BOOL, H, ct.c_int64, ct.POINTER(ct.c_int64), DWORD)
flush = fn('FlushFileBuffers', BOOL, H)
get_info = fn('GetFileInformationByHandle', BOOL, H, PTR)
open_process = fn('OpenProcess', H, DWORD, BOOL, DWORD)
process = fn('GetCurrentProcess', H)
duplicate = fn('DuplicateHandle', BOOL, H, H, H, ct.POINTER(H), DWORD, BOOL, DWORD)
times = fn('GetProcessTimes', BOOL, H, PTR, PTR, PTR, PTR)
create_job = fn('CreateJobObjectW', H, PTR, wt.LPCWSTR)
assign = fn('AssignProcessToJobObject', BOOL, H, H)
in_job = fn('IsProcessInJob', BOOL, H, H, ct.POINTER(BOOL))
query_job = fn('QueryInformationJobObject', BOOL, H, DWORD, PTR, DWORD, PTR)
end_job = fn('TerminateJobObject', BOOL, H, DWORD)
cont = fn('ContinueDebugEvent', BOOL, DWORD, DWORD, DWORD)
wait_debug = fn('WaitForDebugEvent', BOOL, PTR, DWORD)
clock = fn('GetSystemTimePreciseAsFileTime', None, PTR)
INVALID = ct.c_void_p(-1).value
READ, WRITE = 0x80000000, 0x40000000

class FileInfo(ct.Structure):
    _fields_ = [(name, DWORD) for name in
                'attributes c0 c1 a0 a1 w0 w1 volume sizeHi sizeLo links indexHi indexLo'.split()]

class CreateEvent(ct.Structure):
    _fields_ = [(name,H) for name in ['file','proc','thread','base']] + [
        ('symbolOffset',DWORD),('symbolLength',DWORD)] + [
        (name,PTR) for name in ['threadBase','start','imageName']] + [('unicode', wt.WORD)]

class Data(ct.Union):
    _fields_ = [('create',CreateEvent), ('raw',ct.c_ubyte*160), ('align',U64)]
class Event(ct.Structure):
    _fields_ = [('kind',DWORD),('pid',DWORD),('tid',DWORD),('data',Data)]

def file(path, access, sharing, disposition=3):
    handle = open_file(str(path), access, sharing, None, disposition, 0x80, None)
    if handle == INVALID:
        raise ct.WinError(ct.get_last_error())
    return handle

def ident(handle):
    st = FileInfo()
    checked(get_info(handle, ref(st)))
    return [st.volume, st.indexHi << 32 | st.indexLo]

def chunks(handle):
    checked(seek(handle, 0, None, 0))
    buf, got = ct.create_string_buffer(65536), DWORD()
    while True:
        checked(read_file(handle, buf, len(buf), ref(got), None))
        if not got.value:
            break
        yield buf.raw[:got.value]

def digest(handle):
    h = hashlib.sha256()
    for chunk in chunks(handle):
        h.update(chunk)
    return h.hexdigest()

def moment():
    value=U64()
    clock(ref(value))
    return value.value

def birth(handle):
    ts=[U64() for _ in range(4)]
    checked(times(handle, *(ref(t) for t in ts)))
    return ts[0].value

def member(handle, job):
    b=BOOL()
    checked(in_job(handle, job, ref(b)))
    return bool(b.value)

def give_read_view(handle, supervisor):
    # Cooperative export of this process's freshly created file into its own study supervisor.
    # No handle originating in another process is opened or duplicated.
    target=checked(open_process(0x40, False, supervisor))
    try:
        out=H()
        checked(duplicate(process(), handle, target, ref(out), 0x120089, False, 0))
        return out.value
    finally:
        close(target)

def denied(path):
    try:
        h=file(path, WRITE, 1|2|4)
    except OSError as e:
        return e.winerror
    close(h)
    return 0
