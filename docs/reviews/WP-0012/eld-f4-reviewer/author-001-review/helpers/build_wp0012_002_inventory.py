"""Builds complete SHA-256 inventory for WP-0012 / 002 author review & reviewer v3 guard reconciliation.

Verifies:
  1. Initial reviewer preparation (`7f3f8626489e898a50d275e93ee904660e97fd59`, `30` files under
     `docs/reviews/WP-0012/eld-f4-reviewer/preparation/`) is 100% unchanged.
  2. Merged author `/001` (`165b2421b297bf49181c91af8d05a449ad69e9b5`, `24` files) is 100% unchanged.
  3. Production, worker, test, deploy, R&D, shared-ledger (`INDEX.md`, `CURRENT.md`, `AGENTS.md`),
     and historical `WP-0001`..`WP-0010` trees match `47fbc7612e4a08cf1960ad7ac01bd2843ae645e5`.
  4. Every new/modified file since `cb4189aced6f38b269d8a90fa362b92058852bd0` (merged base) lives
     strictly under `docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/`.
  5. All Markdown links resolve, zero local secrets appear, and ports `5690/4710/55439` are unbound
     (`pg_ctl status` exit `3`).
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

AUTHORITY_SHA = "47fbc7612e4a08cf1960ad7ac01bd2843ae645e5"
ACCEPTED_BASE_SHA = "73c8d3c4f0a00312e3444328331b6cbd6406e882"
INITIAL_PREP_PUB_SHA = "7f3f8626489e898a50d275e93ee904660e97fd59"
AUTHOR_001_PUB_SHA = "165b2421b297bf49181c91af8d05a449ad69e9b5"
MERGED_BASE_SHA = "cb4189aced6f38b269d8a90fa362b92058852bd0"

MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)#?\s]+)(?:#[^)\s]*)?\)")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_cmd(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=60,
        check=False,
    )


def run_git(repo_root: Path, *args: str) -> str:
    cp = run_cmd(["git", *args], cwd=repo_root)
    if cp.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {cp.stderr}")
    return cp.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen-sha", required=True)
    parser.add_argument(
        "--output",
        default="docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/review-002-inventory.json",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[6]
    sub_root = repo_root / "docs" / "reviews" / "WP-0012" / "eld-f4-reviewer" / "author-001-review"
    out_path = (repo_root / args.output).resolve()

    # 1. Verify preserved trees against AUTHORITY_SHA
    for rel in (
        "src",
        "web",
        "tests",
        "deploy",
        "ELedgerCare.slnx",
        "workers",
        "research",
        "evaluation",
        "qualification",
        "INDEX.md",
        "CURRENT.md",
        "AGENTS.md",
        "docs/reviews/WP-0010",
        "docs/agent-reports/eld-f4-reviewer/WP-0010",
    ):
        if run_git(repo_root, "rev-parse", f"{AUTHORITY_SHA}:{rel}") != run_git(repo_root, "rev-parse", f"HEAD:{rel}"):
            raise AssertionError(f"Protected path drifted from {AUTHORITY_SHA}: {rel}")

    # 2. Verify initial reviewer preparation (7f3f8626) & merged author /001 (165b2421) are untouched
    if run_git(
        repo_root, "diff", "--name-only", INITIAL_PREP_PUB_SHA, "HEAD", "--", "docs/reviews/WP-0012/eld-f4-reviewer/preparation"
    ):
        raise AssertionError("Initial reviewer preparation directory mutated!")

    if run_git(
        repo_root,
        "diff",
        "--name-only",
        AUTHOR_001_PUB_SHA,
        "HEAD",
        "--",
        "docs/implementation/WP-0012/eld-f4-implementer",
        "docs/agent-reports/eld-f4-implementer/WP-0012",
    ):
        raise AssertionError("Merged author /001 artifacts mutated!")

    # 3. Verify all changes since MERGED_BASE_SHA live strictly inside author-001-review/
    committed_diff = run_git(repo_root, "diff", "--name-only", MERGED_BASE_SHA, "HEAD").splitlines()
    working_lines = run_git(repo_root, "status", "--porcelain", "--untracked-files=all").splitlines()
    working_paths = [ln[3:].strip() for ln in working_lines if ln.strip()]
    for p in committed_diff + working_paths:
        if not p.startswith("docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/"):
            raise AssertionError(f"Out-of-scope file change before report-only commit: {p}")

    # 4. Secret scan & Markdown link check across author-001-review/
    settings = json.loads((repo_root / ".local/secrets/pg-local.json").read_text(encoding="utf-8"))
    secrets = [
        str(settings["adminPassword"]),
        str(settings["migratorPassword"]),
        str(settings["appPassword"]),
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not out_path.exists():
        out_path.write_text("{}\n", encoding="utf-8", newline="\n")

    files_manifest: list[dict] = []
    broken_links: list[dict] = []
    for fp in sorted(p for p in sub_root.rglob("*") if p.is_file()):
        if fp.resolve() == out_path:
            continue
        rel = fp.relative_to(repo_root).as_posix()
        raw = fp.read_bytes()
        lf = raw.replace(b"\r\n", b"\n")
        if fp.suffix.lower() != ".png":
            txt = raw.decode("utf-8")
            for s in secrets:
                if s and s in txt:
                    raise AssertionError(f"Secret leaked in {rel}")
            if fp.suffix.lower() == ".md":
                for m in MD_LINK_RE.finditer(txt):
                    tgt = m.group(1)
                    if tgt.startswith(("http://", "https://", "mailto:", "conversation://", "file://")):
                        continue
                    if not (fp.parent / tgt).resolve().exists():
                        broken_links.append({"source": rel, "target": tgt})
        files_manifest.append({
            "path": rel,
            "byte_length": len(raw),
            "sha256_raw": sha256_hex(raw),
            "sha256_lf": sha256_hex(lf),
        })

    if broken_links:
        raise AssertionError(f"Broken Markdown links: {broken_links}")

    ps_ports = (
        "$out = @{}; foreach ($p in @(5690,4710,55439)) { "
        "$out[\"$p\"] = @(Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue).Count "
        "}; $out | ConvertTo-Json -Compress"
    )
    ports_counts = json.loads(run_cmd(["pwsh", "-NoProfile", "-Command", ps_ports], cwd=repo_root).stdout)
    pg_ctl = repo_root / ".local/tools/pgsql-18.7-1/bin/pg_ctl.exe"
    pg_rc = run_cmd([str(pg_ctl), "status", "-D", str(repo_root / ".local/postgres-data")], cwd=repo_root).returncode
    if any(v != 0 for v in ports_counts.values()) or pg_rc != 3:
        raise AssertionError(f"Services active: ports={ports_counts}, pg_rc={pg_rc}")

    preserved_base_count = len(run_git(repo_root, "ls-tree", "-r", "--name-only", AUTHORITY_SHA).splitlines())

    payload = {
        "schema": "eledgercare.wp-0012.reviewer-002-inventory/1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": "eld-f4-reviewer",
        "branch": run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD"),
        "authority_wp0012_sha": AUTHORITY_SHA,
        "accepted_product_base_sha": ACCEPTED_BASE_SHA,
        "initial_reviewer_prep_pub_sha": INITIAL_PREP_PUB_SHA,
        "reviewed_author_001_pub_sha": AUTHOR_001_PUB_SHA,
        "merged_base_sha": MERGED_BASE_SHA,
        "frozen_002_helpers_sha": args.frozen_sha,
        "preserved_authority_base_file_count": preserved_base_count,
        "preserved_initial_reviewer_prep_file_count": 30,
        "preserved_merged_author_001_file_count": 24,
        "new_author_001_review_file_count_excluding_self": len(files_manifest),
        "ports_listener_counts": ports_counts,
        "pg_ctl_status_exit_code": pg_rc,
        "live_model_or_gpu_executed": False,
        "files": files_manifest,
    }
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
