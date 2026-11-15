"""Streaming digests: SHA-256 and Git blob SHA-1 (the Hugging Face tree `oid` of non-LFS files)."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

CHUNK = 1 << 20


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1_bytes(data: bytes) -> str:
    h = hashlib.sha1(usedforsecurity=False)
    h.update(b"blob %d\x00" % len(data))
    h.update(data)
    return h.hexdigest()


def file_digests(path: str | os.PathLike, *, git_blob: bool = True) -> dict:
    """Return size, sha256 and (optionally) git blob sha1 of a file in one streaming pass."""
    p = Path(path)
    size = p.stat().st_size
    s256 = hashlib.sha256()
    s1 = hashlib.sha1(usedforsecurity=False) if git_blob else None
    if s1 is not None:
        s1.update(b"blob %d\x00" % size)
    read = 0
    with open(p, "rb") as f:
        while True:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            read += len(chunk)
            s256.update(chunk)
            if s1 is not None:
                s1.update(chunk)
    if read != size:
        raise OSError(f"file changed size while hashing: {p} ({size} -> {read})")
    out = {"size": size, "sha256": s256.hexdigest()}
    if s1 is not None:
        out["git_blob_sha1"] = s1.hexdigest()
    return out


def is_hex(value: object, length: int) -> bool:
    return isinstance(value, str) and len(value) == length and all(c in "0123456789abcdef" for c in value)
