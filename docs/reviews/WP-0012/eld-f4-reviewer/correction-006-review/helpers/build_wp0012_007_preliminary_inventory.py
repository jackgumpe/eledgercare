"""Builds complete SHA-256 inventory for WP-0012 / 007 preliminary probe checkpoint (`eld-f4-reviewer`).

Verifies:
  1. All `3,682` files in `379d8c5d607fd248d7f272e412b4ed4a97bc64f6` (`3,615` authority-base +
     `30` initial `preparation/` + `24` merged `/001` + `12` `author-001-review/` + `1` immutable `/002`
     report) are 100% preserved untouched.
  2. Every added file since `379d8c5d607fd248d7f272e412b4ed4a97bc64f6` resides strictly under
     `docs/reviews/WP-0012/eld-f4-reviewer/correction-006-review/`.
  3. Canonical `docs/agent-reports/eld-f4-reviewer/WP-0012/007_2026-11-17_review_eld-f4-reviewer.md`
     does NOT exist yet (strictly held until exact frozen `/006` binding).
  4. All Markdown links resolve, zero local secrets appear, and reviewer ports `5690/4710/55439`
     have `0` active listeners (`pg_ctl status` exit `3`).
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
OVERLAP_AUTHORITY_SHA = "bf14c91b2b1e0b282018f36702ea41c45bba1045"
PRIOR_002_PUB_SHA = "379d8c5d607fd248d7f272e412b4ed4a97bc64f6"

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
        default="docs/reviews/WP-0012/eld-f4-reviewer/correction-006-review/preliminary/preliminary-inventory.json",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[6]
    sub_root = repo_root / "docs" / "reviews" / "WP-0012" / "eld-f4-reviewer" / "correction-006-review"
    out_path = (repo_root / args.output).resolve()

    # 1. Verify canonical /007 is strictly HELD (not yet created)
    held_007 = repo_root / "docs/agent-reports/eld-f4-reviewer/WP-0012/007_2026-11-17_review_eld-f4-reviewer.md"
    if held_007.exists():
        raise AssertionError(f"Canonical /007 must remain HELD during preliminary overlap: {held_007}")

    # 2. Verify zero modifications or deletions to any pre-existing file in PRIOR_002_PUB_SHA
    modified_or_deleted = run_git(repo_root, "diff", "--diff-filter=MD", "--name-only", PRIOR_002_PUB_SHA, "HEAD")
    if modified_or_deleted != "":
        raise AssertionError(f"Immutable pre-007 branch files modified/deleted:\n{modified_or_deleted}")

    committed_added = run_git(repo_root, "diff", "--name-only", PRIOR_002_PUB_SHA, "HEAD").splitlines()
    working_lines = run_git(repo_root, "status", "--porcelain", "--untracked-files=all").splitlines()
    working_paths = [ln[3:].strip() for ln in working_lines if ln.strip()]
    for p in committed_added + working_paths:
        if not p.startswith("docs/reviews/WP-0012/eld-f4-reviewer/correction-006-review/"):
            raise AssertionError(f"Out-of-scope file change: {p}")

    # 3. Secret & Markdown link verification
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

    preserved_total = len(run_git(repo_root, "ls-tree", "-r", "--name-only", PRIOR_002_PUB_SHA).splitlines())

    payload = {
        "schema": "eledgercare.wp-0012.reviewer-007-preliminary-inventory/1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": "eld-f4-reviewer",
        "branch": run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD"),
        "overlap_authority_sha": OVERLAP_AUTHORITY_SHA,
        "prior_002_publication_sha": PRIOR_002_PUB_SHA,
        "frozen_preliminary_helpers_sha": args.frozen_sha,
        "canonical_007_published": False,
        "preserved_branch_file_count": preserved_total,
        "new_correction_006_review_file_count_excluding_self": len(files_manifest),
        "ports_listener_counts": ports_counts,
        "pg_ctl_status_exit_code": pg_rc,
        "live_model_or_gpu_executed": False,
        "files": files_manifest,
    }
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
