"""Coordinator release records (schema eldq0-release/2).

The release record is the only place that binds the ACCEPTED identities together: the
independent review that accepted the harness, the exact harness commit, the protocol and
lock SHA-256 values and any accepted provenance exceptions. This keeps the lock free of
the review that reviews it (the /002 checkpoint's circular requirement is removed).
"""

from __future__ import annotations

import os
from pathlib import Path

from .environment import run_git
from .hashing import is_hex
from .outcome import Q0Failure

STAGES = {"install": None, "execute": {"author": "004", "reviewer": "005"}}


def code_identity(repo_root: Path, *, environ: dict | None = None) -> dict:
    """HEAD commit and cleanliness of the harness subtree in the executing worktree."""
    def git(*a):
        cp = run_git(a, cwd=repo_root, environ=environ, text=True)
        return cp.returncode, cp.stdout.strip()
    rc, head = git("rev-parse", "HEAD")
    rc2, dirty = git("status", "--porcelain=v1", "-uall", "--", "qualification/q0/harness/q0harness",
                     "qualification/q0/harness/q0.py", "qualification/q0/harness/protocol.json",
                     "qualification/q0/harness/locks", "qualification/q0/harness/manifests")
    return {"head": head if rc == 0 else None, "harness_clean": rc2 == 0 and dirty == "", "dirty": dirty.splitlines()}


def validate_release(release: dict | None, *, stage: str, owner: str | None, protocol: dict, protocol_sha256: str,
                     lock_sha256: str, root: Path, code: dict) -> dict:
    if not release:
        raise Q0Failure("EXECUTION_NOT_RELEASED", f"no coordinator {stage} release record supplied")
    problems = []
    if release.get("schema") != "eldq0-release/2": problems.append("schema")
    if release.get("packet") != "WP-0005": problems.append("packet")
    if release.get("stage") != stage: problems.append("stage")
    if stage == "execute":
        want_seq = STAGES["execute"].get(owner or "")
        if release.get("sequence") != want_seq: problems.append("sequence")
        if release.get("gpu_uuid") != protocol["gpu"]["uuid"]: problems.append("gpu_uuid")
        if not release.get("lease_id"): problems.append("lease_id")
    if release.get("released_by") != "eld-coordinator": problems.append("released_by")
    if not is_hex(release.get("release_commit"), 40): problems.append("release_commit")
    review = release.get("accepted_review") or {}
    if review.get("reviewer") != "eld-q0-reviewer" or not is_hex(review.get("report_commit"), 40) \
            or not is_hex(review.get("evidence_commit"), 40):
        problems.append("accepted_review")
    if release.get("harness_commit") != code.get("head") or not code.get("harness_clean"):
        problems.append("harness_commit/clean")
    if release.get("protocol_sha256") != protocol_sha256: problems.append("protocol_sha256")
    if release.get("lock_sha256") != lock_sha256: problems.append("lock_sha256")
    if not isinstance(release.get("accepted_provenance_exceptions", []), list): problems.append("exceptions")
    if os.path.normcase(str(release.get("storage_root"))) != os.path.normcase(str(root)): problems.append("storage_root")
    if problems:
        raise Q0Failure("EXECUTION_NOT_RELEASED", f"{stage} release record does not bind this exact work", problems)
    return {k: release.get(k) for k in ("stage", "release_commit", "harness_commit", "sequence", "lease_id",
                                        "accepted_review", "accepted_provenance_exceptions")}
