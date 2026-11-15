"""Stage B.2 worker: fetch the exact 32 locked wheel URLs into the task wheelhouse.

Executed inside the task venv interpreter (`-s -P -X utf8`) under `build_stage_env(..., network=True)`.
Uses direct HTTPS requests (`urllib.request`) to the exact locked URLs only: no dependency
resolver, no package index query, no sdist, no extras, no silent retries, and no cookies,
tokens or authorization headers sent or recorded. Authoritative payload/METADATA verification
is performed immediately afterward by `q0.py verify-wheelhouse`.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import ssl
import sys
import urllib.error
import urllib.request

SAFE_RESPONSE_HEADERS = (
    "date",
    "content-length",
    "content-type",
    "etag",
    "last-modified",
    "cf-cache-status",
    "server",
)
DURING_FLOOR_BYTES = 21_474_836_480


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class RedirectRecorder(urllib.request.HTTPRedirectHandler):
    def __init__(self) -> None:
        super().__init__()
        self.hops: list[dict] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.hops.append({"status": int(code), "url": str(newurl).split("?", 1)[0]})
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def main() -> int:
    harness_dir = Path(sys.argv[1]).resolve()
    repo_root = Path(sys.argv[2]).resolve()
    wheelhouse = Path(sys.argv[3]).resolve()
    sys.path.insert(0, str(harness_dir))

    from q0harness import locks  # noqa: E402
    from q0harness.environment import audit_stage_env  # noqa: E402

    audit_stage_env(dict(os.environ), root=wheelhouse.parent, network=True)
    lock = locks.load_lock(harness_dir / "locks" / "dependency-lock.json")
    pkgs = locks.validate_lock(lock, locks.git_blob_reader(repo_root))
    if len(pkgs) != 32:
        raise RuntimeError(f"expected 32 locked artifacts, got {len(pkgs)}")

    existing = [p.name for p in wheelhouse.iterdir()]
    if existing:
        raise RuntimeError(f"wheelhouse not empty before Stage B.2: {existing}")

    ssl_ctx = ssl.create_default_context()
    receipts: list[dict] = []
    total_bytes = 0
    items = sorted(pkgs.items())

    for idx, (_, art) in enumerate(items, start=1):
        name = art["name"]
        version = art["version"]
        filename = art["filename"]
        url = art["url"]
        expected_size = int(art["size"])
        dest = wheelhouse / filename
        part = wheelhouse / f"{filename}.part"

        recorder = RedirectRecorder()
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl_ctx),
            recorder,
        )
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "eledgercare-q0-stage-b/1.0", "Accept": "*/*"},
            method="GET",
        )
        started = utc()
        sys.stderr.write(f"[{started}] [{idx:02d}/32] GET {filename} ({expected_size:,} B)\n")
        sys.stderr.flush()

        h = hashlib.sha256()
        written = 0
        with opener.open(req, timeout=900) as resp:
            status = int(getattr(resp, "status", resp.getcode()))
            final_url = str(resp.geturl()).split("?", 1)[0]
            raw_headers = {k.lower(): v for k, v in resp.headers.items()}
            safe_headers = {k: raw_headers[k] for k in SAFE_RESPONSE_HEADERS if k in raw_headers}
            if status != 200:
                raise RuntimeError(f"{filename}: unexpected HTTP status {status}")
            with open(part, "xb") as out_f:
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    out_f.write(chunk)
                    h.update(chunk)
                    written += len(chunk)

        if written != expected_size:
            raise RuntimeError(f"{filename}: wrote {written} B, expected {expected_size} B")
        os.replace(part, dest)
        finished = utc()
        free_after = shutil.disk_usage(wheelhouse.anchor).free
        if free_after < DURING_FLOOR_BYTES:
            raise RuntimeError(f"free space {free_after} fell below during floor {DURING_FLOOR_BYTES}")

        total_bytes += written
        receipts.append({
            "index": idx,
            "name": name,
            "version": version,
            "filename": filename,
            "effective_kind": art["effective_kind"],
            "requested_url": url,
            "final_url": final_url,
            "redirects": recorder.hops,
            "http_status": status,
            "safe_response_headers": safe_headers,
            "expected_size": expected_size,
            "actual_size": written,
            "local_sha256": h.hexdigest(),
            "matches_effective_sha256": h.hexdigest() == art["effective_sha256"],
            "started_utc": started,
            "finished_utc": finished,
            "free_bytes_after": free_after,
        })

    assert "torch" not in sys.modules and "transformers" not in sys.modules
    summary = {
        "schema": "eldq0-wheel-acquisition-receipts/1",
        "wheel_count": len(receipts),
        "total_bytes_written": total_bytes,
        "all_sizes_and_hashes_match_lock": all(
            r["actual_size"] == r["expected_size"] and r["matches_effective_sha256"] for r in receipts
        ),
        "cookies_or_auth_headers_sent_or_stored": False,
        "torch_or_transformers_imported": False,
        "receipts": receipts,
    }
    sys.stdout.write(json.dumps(summary, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
