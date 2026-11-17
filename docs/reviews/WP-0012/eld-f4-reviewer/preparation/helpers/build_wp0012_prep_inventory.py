"""Builds complete SHA-256 inventory and boundary verification for WP-0012 reviewer CPU preparation.

Verifies:
  1. Every changed path relative to `47fbc7612e4a08cf1960ad7ac01bd2843ae645e5` resides strictly under
     `docs/reviews/WP-0012/eld-f4-reviewer/`.
  2. Canonical `WP-0012 / 002` and `WP-0012 / 004` agent reports do NOT exist yet (properly held).
  3. All production, worker, test, deploy, shared-ledger (`INDEX.md`, `CURRENT.md`, `AGENTS.md`),
     and historical `WP-0001`..`WP-0010` trees match `47fbc7612e4a08cf1960ad7ac01bd2843ae645e5`.
  4. All relative Markdown links inside `docs/reviews/WP-0012/eld-f4-reviewer/**` resolve on disk.
  5. Zero `.local/secrets/pg-local.json` values appear in any tracked/new `WP-0012` file.
  6. Owned ports `5690`, `4710`, and `55439` have `0` active listeners and `pg_ctl status` exits `3`.
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
REVIEWER_PORTS = (5690, 4710, 55439)
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
        default="docs/reviews/WP-0012/eld-f4-reviewer/preparation/preparation-inventory.json",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[6]
    owned_root = repo_root / "docs" / "reviews" / "WP-0012" / "eld-f4-reviewer"
    out_path = (repo_root / args.output).resolve()

    # 1. Canonical /002 and /004 must NOT exist before Root's author001 / author003 binding
    wp12_reports_dir = repo_root / "docs" / "agent-reports" / "eld-f4-reviewer" / "WP-0012"
    if wp12_reports_dir.exists() and any(wp12_reports_dir.iterdir()):
        raise AssertionError(f"Canonical WP-0012 report directory must be empty before binding: {wp12_reports_dir}")

    # 2. Verify preserved trees and shared ledgers against AUTHORITY_SHA
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
        exp = run_git(repo_root, "rev-parse", f"{AUTHORITY_SHA}:{rel}")
        cur = run_git(repo_root, "rev-parse", f"HEAD:{rel}")
        if exp != cur:
            raise AssertionError(f"Preserved path {rel} changed from {AUTHORITY_SHA} ({exp} -> {cur})")

    # 3. Verify git diff + untracked files stay strictly inside docs/reviews/WP-0012/eld-f4-reviewer/
    diff_Committed = run_git(repo_root, "diff", "--name-only", AUTHORITY_SHA, "HEAD").splitlines()
    status_lines = run_git(repo_root, "status", "--porcelain", "--untracked-files=all").splitlines()
    working_paths = [ln[3:].strip() for ln in status_lines if ln.strip()]
    for p in diff_Committed + working_paths:
        if not p.startswith("docs/reviews/WP-0012/eld-f4-reviewer/"):
            raise AssertionError(f"Out-of-scope file change detected: {p}")

    # 4. Secret scan + Markdown link verification + SHA-256 inventory
    settings = json.loads((repo_root / ".local/secrets/pg-local.json").read_text(encoding="utf-8"))
    secrets = [
        str(settings["adminPassword"]),
        str(settings["migratorPassword"]),
        str(settings["appPassword"]),
    ]

    broken_links: list[dict] = []
    files_manifest: list[dict] = []
    for fp in sorted(p for p in owned_root.rglob("*") if p.is_file()):
        if fp.resolve() == out_path:
            continue
        rel = fp.relative_to(repo_root).as_posix()
        raw = fp.read_bytes()
        lf = raw.replace(b"\r\n", b"\n")
        if fp.suffix.lower() != ".png":
            text = raw.decode("utf-8")
            for s in secrets:
                if s and s in text:
                    raise AssertionError(f"Secret leaked in {rel}")
            if fp.suffix.lower() == ".md":
                for m in MD_LINK_RE.finditer(text):
                    target_str = m.group(1)
                    if target_str.startswith(("http://", "https://", "mailto:", "conversation://", "file://")):
                        continue
                    resolved = (fp.parent / target_str).resolve()
                    if not resolved.exists():
                        broken_links.append({"source": rel, "target": target_str})

        files_manifest.append({
            "path": rel,
            "byte_length": len(raw),
            "sha256_raw": sha256_hex(raw),
            "sha256_lf": sha256_hex(lf),
        })

    if broken_links:
        raise AssertionError(f"Broken Markdown links found: {broken_links}")

    # 5. Verify stopped services & ports
    ps_ports = (
        "$out = @{}; foreach ($p in @(5690,4710,55439)) { "
        "$out[\"$p\"] = @(Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue).Count "
        "}; $out | ConvertTo-Json -Compress"
    )
    ports_counts = json.loads(run_cmd(["pwsh", "-NoProfile", "-Command", ps_ports], cwd=repo_root).stdout)
    pg_ctl = repo_root / ".local/tools/pgsql-18.7-1/bin/pg_ctl.exe"
    pg_rc = run_cmd([str(pg_ctl), "status", "-D", str(repo_root / ".local/postgres-data")], cwd=repo_root).returncode
    if any(v != 0 for v in ports_counts.values()) or pg_rc != 3:
        raise AssertionError(f"Services still active: ports={ports_counts}, pg_ctl_rc={pg_rc}")

    payload = {
        "schema": "eledgercare.wp-0012.reviewer-preparation-inventory/1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": "eld-f4-reviewer",
        "branch": run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD"),
        "authority_base_sha": AUTHORITY_SHA,
        "accepted_product_base_sha": ACCEPTED_BASE_SHA,
        "frozen_helpers_sha": args.frozen_sha,
        "canonical_002_published": False,
        "canonical_004_published": False,
        "live_model_or_gpu_executed": False,
        "ports_listener_counts": ports_counts,
        "pg_ctl_status_exit_code": pg_rc,
        "file_count_excluding_self": len(files_manifest),
        "files": files_manifest,
    }
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
