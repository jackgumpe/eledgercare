"""Bounded stdlib evidence writer. Never overwrites, never truncates silently.

Raw model output is persisted here instead of through the model's save_results path.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .hashing import sha256_bytes

_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")


class CapExceeded(Exception):
    pass


class BoundedWriter:
    def __init__(self, directory: Path, *, total_cap_bytes: int):
        self.dir = Path(directory)
        self.total_cap = int(total_cap_bytes)
        self.written = 0
        self.index: list[dict] = []
        self.dir.mkdir(parents=True, exist_ok=True)

    def _target(self, name: str) -> Path:
        reserved = name.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(10)),
                                                  *(f"LPT{i}" for i in range(10))}
        if not _NAME.match(name) or name.endswith(".partial") or reserved:
            raise ValueError(f"unsafe evidence file name {name!r}")
        return self.dir / name

    def write_bytes(self, name: str, data: bytes, *, cap_bytes: int) -> dict:
        """Write `data` exclusively. If it exceeds cap_bytes, write only the first cap_bytes
        and report truncated_by_writer=True plus the full digest/length (never silent)."""
        target = self._target(name)
        if target.exists():
            raise FileExistsError(f"refusing to overwrite evidence {target}")
        full_len, full_sha = len(data), sha256_bytes(data)
        body = data[:cap_bytes]
        if self.written + len(body) > self.total_cap:
            raise CapExceeded(f"evidence total cap {self.total_cap} would be exceeded by {name}")
        partial = target.with_name(target.name + ".partial")
        with open(partial, "xb") as f:
            f.write(body)
            f.flush()
            os.fsync(f.fileno())
        os.rename(partial, target)  # fails on Windows if target appeared meanwhile
        self.written += len(body)
        rec = {"name": name, "bytes_written": len(body), "sha256_written": sha256_bytes(body),
               "full_bytes": full_len, "full_sha256": full_sha, "truncated_by_writer": len(body) < full_len}
        self.index.append(rec)
        return rec

    def write_text(self, name: str, text: str, *, cap_bytes: int) -> dict:
        try:
            data = text.encode("utf-8", "strict")
            lossless = True
        except UnicodeEncodeError:
            data = text.encode("utf-8", "backslashreplace")
            lossless = False
        rec = self.write_bytes(name, data, cap_bytes=cap_bytes)
        rec["utf8_lossless"] = lossless
        return rec

    def write_json(self, name: str, obj, *, cap_bytes: int) -> dict:
        data = (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
        if len(data) > cap_bytes:
            raise CapExceeded(f"JSON evidence {name} is {len(data)} bytes > cap {cap_bytes}; refusing partial JSON")
        return self.write_bytes(name, data, cap_bytes=cap_bytes)


class BoundedJsonl:
    """Append-only JSON-lines event log with a hard byte cap; overflow is recorded once, then dropped and counted."""

    def __init__(self, path: Path, *, cap_bytes: int):
        self.path = Path(path)
        self.cap = int(cap_bytes)
        self.size = 0
        self.dropped = 0
        self._f = open(self.path, "xb")

    _MARKER = b'{"event": "log_cap_reached"}\n'

    def append(self, event: dict) -> bool:
        line = (json.dumps(event, sort_keys=True, ensure_ascii=False, default=str) + "\n").encode("utf-8")
        # Space for the overflow marker is always reserved so truncation is visible in the file itself.
        if self.size + len(line) > self.cap - len(self._MARKER):
            if self.dropped == 0:
                self._f.write(self._MARKER)
                self.size += len(self._MARKER)
            self.dropped += 1
            self._f.flush()
            return False
        self._f.write(line)
        self._f.flush()
        self.size += len(line)
        return True

    def close(self) -> dict:
        self._f.close()
        return {"path": str(self.path), "bytes": self.size, "dropped_events": self.dropped}
