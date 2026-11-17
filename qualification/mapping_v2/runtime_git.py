"""Snapshot guard for Windows CreateProcess bare 'git' lookup; no executable launch.

The frozen verifier uses shell=False and no extension, so Windows searches for
git.exe, not PATHEXT/App Paths. Check in the actual worker before those calls.
This is not an atomic filesystem lock or a claim about other shell APIs.
"""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path


def verify_bare_git_lookup(env):
    if os.name != 'nt':
        raise PermissionError('Qualified Windows Git lookup required')
    pinned = Path(env['Q0_GIT_EXECUTABLE'])
    if not pinned.is_absolute() or pinned.name.lower() != 'git.exe' or not pinned.is_file():
        raise PermissionError('Explicit absolute git.exe required for bare Windows lookup')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    def location(name, module=False):
        fn = getattr(kernel, name); buffer = ctypes.create_unicode_buffer(32768)
        fn.argtypes = ([wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD] if module
                       else [wintypes.LPWSTR, wintypes.UINT])
        fn.restype = wintypes.DWORD if module else wintypes.UINT
        count = fn(None, buffer, len(buffer)) if module else fn(buffer, len(buffer))
        if not count or count >= len(buffer):
            raise PermissionError('Windows Git search location unavailable: ' + name)
        return Path(buffer.value)
    application = location('GetModuleFileNameW', True).parent
    windows = location('GetWindowsDirectoryW')
    paths = env.get('PATH', '').split(os.pathsep)
    if any(not value or '"' in value or not Path(value).is_absolute() for value in paths):
        raise PermissionError('Ambiguous or relative child PATH entry')
    directories = [application, Path.cwd(), location('GetSystemDirectoryW'), windows/'System', windows]
    directories.extend(Path(value) for value in paths)
    for directory in directories:
        candidate = directory/'git.exe'
        try:
            candidate.stat()  # Access/other failures reject; only genuine absence continues.
        except FileNotFoundError:
            continue
        if os.path.normcase(os.path.abspath(candidate)) != os.path.normcase(os.path.abspath(pinned)):
            raise PermissionError('Bare Git is shadowed before the validated executable: ' + str(candidate))
        return str(candidate)
    raise PermissionError('Validated Git is unavailable to bare Windows lookup')
