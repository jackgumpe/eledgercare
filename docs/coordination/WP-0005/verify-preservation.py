"""Read-only final WP-0005 integration identity check; writes JSON to stdout only."""

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def git(*args):
    return subprocess.check_output(["git", *args])


def tree(revision):
    result = {}
    for row in git("ls-tree", "-rz", "--full-tree", revision).split(b"\0"):
        if row:
            metadata, name = row.split(b"\t", 1)
            result[name.decode("utf-8")] = metadata.decode("ascii")
    return result


def allowed_addition(path):
    return (path.startswith(("qualification/q0/", "docs/coordination/WP-0005/",
                             "docs/reviews/WP-0005/"))
            or path.startswith("docs/kickoffs/WP-0005-")
            or bool(re.fullmatch(r"docs/agent-reports/[^/]+/WP-0005/\d{3}_\d{4}-\d{2}-\d{2}_[a-z]+_[^/]+\.md", path)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="df9a2b50894f01987d779d7f9ae805794503ce6f")
    parser.add_argument("--target", default="HEAD")
    parser.add_argument("--accepted-harness", required=True)
    args = parser.parse_args()
    refs = {name: git("rev-parse", value + "^{commit}").decode().strip()
            for name, value in (("base", args.base), ("target", args.target),
                                ("accepted_harness", args.accepted_harness))}
    base, target, harness = (tree(refs[key]) for key in ("base", "target", "accepted_harness"))
    mutable_routing = {"AGENTS.md", "CURRENT.md", "INDEX.md"}
    protected = {p: identity for p, identity in base.items() if p not in mutable_routing}
    changed_protected = [p for p, identity in protected.items() if target.get(p) != identity]
    unexpected_added = [p for p in target if p not in base and not allowed_addition(p)]
    core_prefix = "qualification/q0/harness/"
    evidence_prefix = core_prefix + "evidence/"
    expected_core = {p: identity for p, identity in harness.items()
                     if p.startswith(core_prefix) and not p.startswith(evidence_prefix)}
    actual_core = {p: identity for p, identity in target.items()
                   if p.startswith(core_prefix) and not p.startswith(evidence_prefix)}
    changed_core = sorted(p for p in expected_core.keys() | actual_core.keys()
                          if expected_core.get(p) != actual_core.get(p))
    reports = [p for p in target if re.fullmatch(r"docs/agent-reports/[^/]+/WP-0005/\d{3}_[^/]+\.md", p)]
    by_sequence = {}
    for path in reports:
        by_sequence.setdefault(Path(path).name[:3], []).append(path)
    duplicate_sequences = {seq: paths for seq, paths in by_sequence.items() if len(paths) != 1}
    result = {
        "schema": "eldq0-integration-preservation/1",
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "revisions": refs,
        "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "protected_base_files": len(protected),
        "changed_or_missing_protected": changed_protected,
        "new_files": len(target.keys() - base.keys()),
        "unexpected_additions": unexpected_added,
        "accepted_harness_core_files": len(expected_core),
        "harness_core_differences": changed_core,
        "canonical_reports": sorted(reports),
        "duplicate_packet_sequences": duplicate_sequences,
        "scope": "Git mode/type/blob identities; no model execution or accuracy inference",
    }
    result["passed"] = bool(expected_core) and not any(
        (changed_protected, unexpected_added, changed_core, duplicate_sequences))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
