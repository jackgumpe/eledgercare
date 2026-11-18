"""Hold read-only Win32 handles across verification and reuse. Recheck tree membership each job."""
import ctypes
from ctypes import wintypes
from pathlib import Path


class ReadOnlyGeneration:
    def __init__(self, *roots):
        self.roots = tuple(Path(r).resolve(strict=True) for r in roots)
        self.paths = self.snapshot()
        api = ctypes.WinDLL("kernel32", use_last_error=True).CreateFileW
        api.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        api.restype = wintypes.HANDLE
        self.handles = []
        for path, *_ in self.paths:
            # Read access, share READ (no WRITE/DELETE); retained until process exits.
            handle = api(str(path), 0x80000000, 1, None, 3, 0x80, None)
            if handle == wintypes.HANDLE(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            self.handles.append(handle)
        self.check()

    def snapshot(self):
        files = []
        for root in self.roots:
            for p in (root.rglob("*") if root.is_dir() else [root]):
                if p.is_symlink() or p.is_junction():
                    raise ValueError("Link in pinned generation")
                if p.is_file():
                    s = p.stat()
                    files.append((p, s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns))
        return tuple(sorted(files))

    def check(self):
        if self.snapshot() != self.paths:
            raise RuntimeError("Pinned generation membership changed")
