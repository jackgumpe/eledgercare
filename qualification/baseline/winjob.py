"""Windows kill-on-job-close ownership. Worker joins before any runtime imports."""
import ctypes,os
from ctypes import wintypes as W
class IO(ctypes.Structure):_fields_=[(x,ctypes.c_ulonglong) for x in ('ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
class Basic(ctypes.Structure):
    _fields_=[('PerProcessUserTimeLimit',ctypes.c_longlong),('PerJobUserTimeLimit',ctypes.c_longlong),('LimitFlags',W.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',W.DWORD),('Affinity',ctypes.c_size_t),('PriorityClass',W.DWORD),('SchedulingClass',W.DWORD)]
class Extended(ctypes.Structure):
    _fields_=[('BasicLimitInformation',Basic),('IoInfo',IO),('ProcessMemoryLimit',ctypes.c_size_t),('JobMemoryLimit',ctypes.c_size_t),('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]
def api():
    if os.name!='nt':raise RuntimeError('Baseline runtime requires Windows job ownership')
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.CreateJobObjectW.argtypes=[ctypes.c_void_p,W.LPCWSTR];k.CreateJobObjectW.restype=W.HANDLE
    k.OpenJobObjectW.argtypes=[W.DWORD,W.BOOL,W.LPCWSTR];k.OpenJobObjectW.restype=W.HANDLE
    k.SetInformationJobObject.argtypes=[W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD];k.SetInformationJobObject.restype=W.BOOL
    k.AssignProcessToJobObject.argtypes=[W.HANDLE,W.HANDLE];k.AssignProcessToJobObject.restype=W.BOOL
    k.GetCurrentProcess.restype=W.HANDLE;k.CloseHandle.argtypes=[W.HANDLE]
    return k
def create(name):
    k=api();h=k.CreateJobObjectW(None,name)
    if not h:raise ctypes.WinError(ctypes.get_last_error())
    info=Extended();info.BasicLimitInformation.LimitFlags=0x2000
    if not k.SetInformationJobObject(h,9,ctypes.byref(info),ctypes.sizeof(info)):
        k.CloseHandle(h);raise ctypes.WinError(ctypes.get_last_error())
    return h
def join(name):
    k=api();h=k.OpenJobObjectW(0x0001,False,name)
    if not h:raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not k.AssignProcessToJobObject(h,k.GetCurrentProcess()):raise ctypes.WinError(ctypes.get_last_error())
    finally:k.CloseHandle(h)
def close(handle):api().CloseHandle(handle)
