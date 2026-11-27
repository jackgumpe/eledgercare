"""Read-only observations of newly launched owned fixtures on 64-bit Windows."""
import ctypes as ct
from ctypes import wintypes as wt
from contextlib import contextmanager
import hashlib
import msvcrt
import os

K = ct.WinDLL("kernel32", use_last_error=True)
HANDLE, DWORD, PTR = wt.HANDLE, wt.DWORD, ct.c_void_p
READ, WRITE, SHARE_READ, SHARE_WRITE = 0x80000000, 0x40000000, 1, 2
INVALID = ct.c_void_p(-1).value


def api(name, result, *args):
    call = getattr(K, name)
    call.restype, call.argtypes = result, args
    return call


close = api("CloseHandle", wt.BOOL, HANDLE)
create_file = api("CreateFileW", HANDLE, wt.LPCWSTR, DWORD, DWORD, PTR, DWORD, DWORD, HANDLE)
get_info = api("GetFileInformationByHandle", wt.BOOL, HANDLE, PTR)
volume_info = api("GetVolumeInformationByHandleW", wt.BOOL, HANDLE, wt.LPWSTR, DWORD,
                  PTR, PTR, PTR, wt.LPWSTR, DWORD)
times = api("GetProcessTimes", wt.BOOL, HANDLE, PTR, PTR, PTR, PTR)
wait = api("WaitForSingleObject", DWORD, HANDLE, DWORD)
resume = api("ResumeThread", DWORD, HANDLE)
create_job = api("CreateJobObjectW", HANDLE, PTR, wt.LPCWSTR)
set_job = api("SetInformationJobObject", wt.BOOL, HANDLE, ct.c_int, PTR, DWORD)
query_job = api("QueryInformationJobObject", wt.BOOL, HANDLE, ct.c_int, PTR, DWORD, PTR)
assign = api("AssignProcessToJobObject", wt.BOOL, HANDLE, HANDLE)
is_in_job = api("IsProcessInJob", wt.BOOL, HANDLE, HANDLE, PTR)
query_path = api("QueryFullProcessImageNameW", wt.BOOL, HANDLE, DWORD, wt.LPWSTR, PTR)
get_pid = api("GetProcessId", DWORD, HANDLE)
exit_code = api("GetExitCodeProcess", wt.BOOL, HANDLE, PTR)
wait_event = api("WaitForDebugEvent", wt.BOOL, PTR, DWORD)
ack = api("ContinueDebugEvent", wt.BOOL, DWORD, DWORD, DWORD)


def check(value):
    if not value:
        raise ct.WinError(ct.get_last_error())
    return value


def open_file(path, access, sharing, disposition=3):
    h = create_file(str(path), access, sharing, None, disposition, 0x80, None)
    if h == INVALID:
        raise ct.WinError(ct.get_last_error())
    return h


def object_id(handle):
    # BY_HANDLE_FILE_INFORMATION contains 13 DWORDs including three FILETIMEs.
    info = (DWORD * 13)()
    check(get_info(handle, info))
    return [info[7], (info[11] << 32) + info[12]]


def filesystem(handle):
    name = ct.create_unicode_buffer(64)
    check(volume_info(handle, None, 0, None, None, None, name, len(name)))
    return name.value


def raw_reader(handle):
    # CRT descriptor takes ownership; callers transfer their own reader handle.
    return os.fdopen(msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY), "rb")


def read_member(path):
    with raw_reader(open_file(path, READ, SHARE_READ | SHARE_WRITE)) as stream:
        identity = object_id(msvcrt.get_osfhandle(stream.fileno()))
        data = stream.read(5)
        if len(data) != 4 or stream.read(1):
            raise ValueError("expected one four-byte member")
        return identity, data


def process_key(handle):
    readings = [ct.c_ulonglong() for _ in range(4)]
    check(times(handle, *(ct.byref(item) for item in readings)))
    return [check(get_pid(handle)), readings[0].value]


def image_path(handle):
    target, size = ct.create_unicode_buffer(32768), DWORD(32768)
    check(query_path(handle, 0, target, ct.byref(size)))
    return target.value


@contextmanager
def owned_job():
    job = check(create_job(None, None))
    try:
        # Windows x64 JOBOBJECT_EXTENDED_LIMIT_INFORMATION: BasicLimitInformation
        # starts with two LARGE_INTEGERs, then LimitFlags. Both breakaway bits zero.
        buf = ct.create_string_buffer(144)
        DWORD.from_buffer(buf, 16).value = 0x2000  # KILL_ON_JOB_CLOSE
        check(set_job(job, 9, buf, len(buf)))
        view = ct.create_string_buffer(144)
        check(query_job(job, 9, view, len(view), None))
        yield job, DWORD.from_buffer(view, 16).value
    finally:
        close(job)


def member(process, job):
    result = wt.BOOL()
    check(is_in_job(process, job, ct.byref(result)))
    return bool(result.value)


class EventData(ct.Union):
    _fields_ = [("words", HANDLE * 20), ("dwords", DWORD * 40)]


class DebugEvent(ct.Structure):
    _fields_ = [("code", DWORD), ("pid", DWORD), ("tid", DWORD), ("data", EventData)]


def next_event():
    event = DebugEvent()
    if wait_event(ct.byref(event), 20):
        return event
    code = ct.get_last_error()
    if code != 121:  # ERROR_SEM_TIMEOUT
        raise ct.WinError(code)
    return None


def sample_image(event, job, approved_paths):
    file_handle, process = event.data.words[:2]
    item = {"instance": process_key(process), "job_member": member(process, job),
            "reported_path": image_path(process)}
    if file_handle and os.path.normcase(item["reported_path"]) not in approved_paths:
        close(file_handle)  # auxiliary console host; read no image bytes
    elif file_handle:
        try:
            with raw_reader(file_handle) as stream:
                item["file_id"] = object_id(msvcrt.get_osfhandle(stream.fileno()))
                item["sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
        except OSError as exc:
            item["file_read_error"] = exc.winerror or exc.errno
    return item
