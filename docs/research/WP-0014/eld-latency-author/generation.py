"""Windows process-lifetime pin for the model and notice previously verified by production."""
from contextlib import ExitStack
import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import stat

KERNEL = ctypes.WinDLL("kernel32", use_last_error=True)
OPEN = KERNEL.CreateFileW
OPEN.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                 wintypes.DWORD, wintypes.HANDLE)
OPEN.restype = wintypes.HANDLE
CLOSE = KERNEL.CloseHandle
CLOSE.argtypes = (wintypes.HANDLE,)
CLOSE.restype = wintypes.BOOL


class Generation:
    def __init__(self, model_dir, notice_dir, manifest, full_verify):
        self.stack = ExitStack()
        self.roots = (Path(model_dir), Path(notice_dir))
        self.manifest = manifest
        try:
            paths = list(self.roots)
            paths += [self.roots[0] / x["path"] for x in manifest["files"]]
            paths += [self.roots[1] / x["path"] for x in manifest["notices"]]
            for path in paths:
                # GENERIC_READ, FILE_SHARE_READ only, OPEN_EXISTING. Deny write and delete access.
                handle = OPEN(str(path), 0x80000000, 1, None, 3, 0x02200000, None)
                if handle == ctypes.c_void_p(-1).value:
                    raise ctypes.WinError(ctypes.get_last_error())
                self.stack.callback(CLOSE, handle)
            self.snapshot = self.scan()
            self.model_dir = full_verify(model_dir, notice_dir, manifest)
            self.verify(model_dir, notice_dir, manifest)
        except BaseException:
            self.close()
            raise

    def scan(self):
        entries = {}
        def fail(error):
            raise error
        for root in self.roots:
            paths = [root]
            for parent, directories, files in os.walk(root, followlinks=False, onerror=fail):
                paths.extend(Path(parent, name) for name in directories + files)
            for path in paths:
                s = os.lstat(path)
                if s.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT or not s.st_ino:
                    raise ValueError("Unstable model namespace: reparse point or missing Windows file ID")
                entries[str(path)] = (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_file_attributes)
        return entries

    def verify(self, model_dir, notice_dir, manifest):
        if (Path(model_dir), Path(notice_dir)) != self.roots or manifest != self.manifest:
            raise ValueError("Resident model generation or manifest changed")
        if self.scan() != self.snapshot:
            raise ValueError("Resident model namespace changed")
        return self.model_dir

    def close(self):
        self.stack.close()


def test_generation(root):
    model, notice = root / "model", root / "notice"
    model.mkdir(parents=True)
    notice.mkdir()
    leaf = model / "weights.bin"
    leaf.write_bytes(b"frozen")
    (notice / "notice.txt").write_bytes(b"test notice")
    manifest = {"files": [{"path": leaf.name}], "notices": [{"path": "notice.txt"}]}
    expected = hashlib.sha256(b"frozen").digest()
    def full_check(m, n, obj):
        if hashlib.sha256(leaf.read_bytes()).digest() != expected:
            raise ValueError("fixture verification mismatch")
        return m
    def refused(name, action, kinds):
        try:
            action()
        except kinds as exc:
            return {"case": name, "outcome": "refused", "error": type(exc).__name__, "winerror": getattr(exc, "winerror", None)}
        raise AssertionError("Expected refusal for " + name)

    pin = Generation(model, notice, manifest, full_check)
    try:
        results = [refused("write held same-size artifact", lambda: leaf.write_bytes(b"drifts"), PermissionError),
                   refused("unlink held artifact", leaf.unlink, PermissionError)]
        extra = model / "unexpected.py"
        try:
            extra.write_bytes(b"fixture")
        except PermissionError as exc:
            results.append({"case": "introduce extra artifact", "outcome": "write refused", "winerror": exc.winerror})
        else:
            results.append(refused("extra artifact during residency", lambda: pin.verify(model, notice, manifest), ValueError))
    finally:
        pin.close()
    leaf.write_bytes(b"drifts")
    results.append(refused("changed contents before verification", lambda: Generation(model, notice, manifest, full_check), ValueError))
    leaf.unlink()
    results.append(refused("missing artifact at startup", lambda: Generation(model, notice, manifest, full_check), FileNotFoundError))
    return results
