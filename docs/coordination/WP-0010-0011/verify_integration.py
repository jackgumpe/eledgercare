"""Coordinator Git-object preservation audit; never imports application/model code."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = "956c056be2ec970340074871ecdd7e1a9855d944"
MUTABLE_BASE_FILES = {"AGENTS.md", "CURRENT.md", "INDEX.md"}
PRODUCT_PREFIXES = ("src/", "web/", "tests/", "deploy/dev/")


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def revision(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ValueError("A full 40-character commit is required")
    if git("rev-parse", value + "^{commit}").decode().strip() != value:
        raise ValueError("Commit identity mismatch")
    return value


def tree_files(commit: str) -> dict[str, dict[str, str]]:
    result = {}
    for entry in git("ls-tree", "-r", "-z", commit).split(b"\0"):
        if not entry:
            continue
        metadata, path = entry.split(b"\t", 1)
        mode, kind, oid = metadata.decode().split()
        if kind != "blob":
            raise ValueError("Unexpected non-blob tracked entry")
        result[path.decode()] = {"mode": mode, "blob": oid}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=revision)
    parser.add_argument("--product-source", required=True, type=revision)
    parser.add_argument("--coverage-source", required=True, type=revision)
    parser.add_argument("--corpus-source", required=True, type=revision)
    parser.add_argument("--publication", action="append", default=[], type=revision)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    output = (ROOT / args.out).resolve()
    if not output.is_relative_to(ROOT / "docs" / "coordination" / "WP-0010-0011"):
        raise ValueError("Output must stay in this coordinator evidence directory")
    if output.exists():
        raise FileExistsError("Preserve prior audit output")
    for commit in [BASE, args.product_source, args.coverage_source, args.corpus_source, *args.publication]:
        subprocess.run(["git", "merge-base", "--is-ancestor", commit, args.candidate], cwd=ROOT, check=True)
    before, after = tree_files(BASE), tree_files(args.candidate)
    protected = {}
    for path, identity in before.items():
        mutable = path in MUTABLE_BASE_FILES or path.startswith(PRODUCT_PREFIXES)
        # Actual old acceptance PDF bytes are preserved even though tests may evolve.
        if path.startswith("tests/fixtures/") and path.endswith(".pdf"):
            mutable = False
        if not mutable:
            if after.get(path) != identity:
                raise AssertionError("Protected base path changed: " + path)
            protected[path] = identity
    accepted_trees = {}
    for source, paths in [(args.product_source, ("src", "web", "tests", "deploy")),
                          (args.coverage_source, ("qualification/coverage_v1",)),
                          (args.corpus_source, ("evaluation/coverage_v1",))]:
        for path in paths:
            expected = git("rev-parse", source + ":" + path).decode().strip()
            observed = git("rev-parse", args.candidate + ":" + path).decode().strip()
            if expected != observed:
                raise AssertionError("Accepted source tree differs: " + path)
            accepted_trees[path] = {"source": source, "tree": observed}
    changed = []
    for path in sorted(before.keys() | after.keys()):
        if before.get(path) == after.get(path):
            continue
        item = {"path": path, "action": "A" if path not in before else "D" if path not in after else "M",
                "before": before.get(path), "after": after.get(path)}
        if path in after:
            blob = git("cat-file", "blob", after[path]["blob"])
            item.update(bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest())
        changed.append(item)
    result = {"schema": "eld-wp0010-wp0011-preservation/1", "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "audit_executing_head": git("rev-parse", "HEAD").decode().strip(),
              "audit_helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "base": BASE, "candidate": args.candidate, "accepted_trees": accepted_trees,
              "publication_ancestry_checked": args.publication, "protected_base_path_count": len(protected),
              "protected_base_paths": protected, "complete_changed_path_count": len(changed), "changed_paths": changed,
              "result": "PASS", "limits": "Git identity/inventory audit only; independent functional and runtime reports govern acceptance."}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"result": "PASS", "protected_base_paths": len(protected), "changed_paths": len(changed),
                      "accepted_trees": len(accepted_trees), "publications": len(args.publication)}))


if __name__ == "__main__":
    main()
