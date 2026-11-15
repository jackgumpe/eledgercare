"""Read-only diagnostic across all 32 acquired wheels in C:\\Users\\jackg\\eLedgerCare-Q0\\WP-0005\\wheelhouse.

Does NOT modify any wheel, harness source, venv, or runtime-root file, and performs NO install
or import. Calls the accepted `q0harness.locks` functions (`file_digests`, `inspect_wheel_metadata`,
`verify_wheel_metadata`) on every one of the 32 wheels individually so all METADATA formatting
differences beyond the first fail-closed stop (`fsspec`) are visible at once for coordinator
disposition.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import zipfile

REPO_ROOT = Path(r"C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-harness")
HARNESS_DIR = REPO_ROOT / "qualification" / "q0" / "harness"
WHEELHOUSE = Path(r"C:\Users\jackg\eLedgerCare-Q0\WP-0005\wheelhouse")
sys.path.insert(0, str(HARNESS_DIR))

from q0harness import locks  # noqa: E402
from q0harness.hashing import file_digests  # noqa: E402
from q0harness.outcome import Q0Failure  # noqa: E402


def main() -> int:
    lock = locks.load_lock(HARNESS_DIR / "locks" / "dependency-lock.json")
    pkgs = locks.validate_lock(lock, locks.git_blob_reader(REPO_ROOT))
    want = {a["filename"]: a for a in pkgs.values()}
    present = sorted(p.name for p in WHEELHOUSE.iterdir() if p.is_file())

    passed = []
    failed = []
    for filename, art in sorted(want.items()):
        wpath = WHEELHOUSE / filename
        d = file_digests(wpath, git_blob=False)
        payload_ok = (d["size"] == art["size"] and d["sha256"] == art["effective_sha256"])
        raw_meta = locks.inspect_wheel_metadata(wpath, art["name"], art["version"])
        try:
            mrow = locks.verify_wheel_metadata(wpath, art)
            passed.append({
                "wheel": filename,
                "name": art["name"],
                "version": art["version"],
                "size": d["size"],
                "sha256": d["sha256"],
                "effective_kind": art["effective_kind"],
                "payload_ok": payload_ok,
                "metadata_sha256": mrow["metadata_sha256"],
                "published_metadata_sha256_match": mrow["published_metadata_sha256_match"],
                "requires_dist_count": mrow["requires_dist"],
            })
        except Q0Failure as exc:
            # Also collect the exact raw lines that differed for coordinator clarity.
            failed.append({
                "wheel": filename,
                "name": art["name"],
                "version": art["version"],
                "size": d["size"],
                "sha256": d["sha256"],
                "effective_kind": art["effective_kind"],
                "payload_ok": payload_ok,
                "failure_class": exc.failure_class,
                "detail": exc.detail,
                "evidence": exc.evidence,
                "raw_wheel_requires_dist": raw_meta["requires_dist"],
                "raw_graph_requires_dist": art.get("graph_requires", []),
            })

    report = {
        "schema": "eldq0-readonly-32-wheel-audit/1",
        "present_wheel_count": len(present),
        "expected_wheel_count": len(want),
        "exact_32_filenames_match": present == sorted(want),
        "all_32_payload_sizes_and_sha256_match_lock": all(
            r["payload_ok"] for r in passed + failed
        ),
        "verify_wheel_metadata_passed_count": len(passed),
        "verify_wheel_metadata_failed_count": len(failed),
        "failed_wheels": failed,
        "passed_wheels": passed,
    }
    out = Path(r"C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-harness\.scratch\004-staging\outputs\08b-readonly-32-wheel-audit.json")
    out.write_bytes((json.dumps(report, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({
        "exact_32_filenames_match": report["exact_32_filenames_match"],
        "all_32_payload_sizes_and_sha256_match_lock": report["all_32_payload_sizes_and_sha256_match_lock"],
        "passed": len(passed),
        "failed": [
            {
                "wheel": f["wheel"],
                "only_in_graph": f["evidence"].get("only_in_graph"),
                "only_in_wheel": f["evidence"].get("only_in_wheel"),
                "published_metadata_sha256_match": f["evidence"].get("published_metadata_sha256_match"),
            }
            for f in failed
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
