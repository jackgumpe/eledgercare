"""Read-only 32-wheel verification calling accepted q0harness.locks.verify_wheelhouse directly.

Runs in either the task venv (`-s -P -X utf8`) under `build_stage_env(..., network=False)` or
stdlib bootstrap Python (`-I -B`). Performs zero writes, zero installs, and zero third-party imports.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys


def main() -> int:
    harness_dir = Path(sys.argv[1]).resolve()
    repo_root = Path(sys.argv[2]).resolve()
    wheelhouse = Path(sys.argv[3]).resolve()
    mode = sys.argv[4]
    sys.path.insert(0, str(harness_dir))

    from q0harness import locks  # noqa: E402
    from q0harness.environment import audit_stage_env  # noqa: E402
    from q0harness.hashing import sha256_bytes  # noqa: E402
    from q0harness.protocol import load_protocol  # noqa: E402
    from q0harness.release import code_identity  # noqa: E402

    if mode == "stage_offline":
        audit_stage_env(dict(os.environ), root=wheelhouse.parent, network=False)

    _, protocol_sha = load_protocol()
    lock_path = harness_dir / "locks" / "dependency-lock.json"
    lock_raw = lock_path.read_bytes()
    lock = json.loads(lock_raw)
    pkgs = locks.validate_lock(lock, locks.git_blob_reader(repo_root))
    code = code_identity(repo_root)
    report = locks.verify_wheelhouse(pkgs, wheelhouse, lock)
    assert "torch" not in sys.modules and "transformers" not in sys.modules

    out = {
        "schema": "eldq0-readonly-wheelhouse-verification/1",
        "mode": mode,
        "python": sys.version,
        "executable": sys.executable,
        "code_identity": code,
        "protocol_sha256": protocol_sha,
        "lock_sha256": sha256_bytes(lock_raw),
        "wheelhouse": str(wheelhouse),
        "metadata_checked": report["metadata_checked"],
        "total_payload_bytes": sum(r["size"] for r in report["wheels"]),
        "all_payloads_ok": all(r["payload_ok"] for r in report["wheels"]),
        "all_metadata_ok": all(r["metadata"]["ok"] for r in report["wheels"]),
        "pep658_matches": {
            r["wheel"]: r["metadata"]["published_metadata_sha256_match"]
            for r in report["wheels"]
            if r["metadata"]["published_metadata_sha256_match"] is not None
        },
        "wheels": report["wheels"],
    }
    sys.stdout.write(json.dumps(out, indent=2) + "\n")
    return 0 if out["code_identity"]["harness_clean"] and out["all_payloads_ok"] and out["all_metadata_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
