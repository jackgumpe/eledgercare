"""Inventory, boundary, secret-redaction, and Markdown-link verifier for WP-0010 reviewer preparation.

Generates `docs/reviews/WP-0010/eld-f4-reviewer/preparation/preparation-inventory.json` and enforces:
  1. Only `docs/reviews/WP-0010/eld-f4-reviewer/preparation/**` differs from coordinator authority
     `7345ef03dfa4d5f039259d0b8b9505685112469d`; prior `/002` design review (`85d879a1...`) and all
     product/test/deploy/shared-routing/R&D trees remain 100% untouched; no `/004` report exists yet.
  2. All local Markdown links across `preparation/**/*.md` resolve inside the owned worktree without
     referencing any forbidden author (`eld-f4-implementer`) or sealed (`WP-0009`/`WP-0011`) paths.
  3. Zero local database credentials from `.local/secrets/pg-local.json` appear in any file under
     `docs/reviews/WP-0010/eld-f4-reviewer/preparation/**`.
  4. All owned ports (`5690`, `4710`, `55439`) have `0` listeners and `pg_ctl status` exits `3` while
     `.local/postgres-data` (`eledgercare_f4_reviewer_seed_f3`) remains retained on disk.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

API_PORT = 5690
UI_PORT = 4710
PG_PORT = 55439
REVIEWER_PORTS = (API_PORT, UI_PORT, PG_PORT)

PRIOR_DESIGN_002_SHA = "85d879a1adc0ee62090f4c6a5c9a7fb8eb5f3a96"
AUTHORITY_PREP_SHA = "7345ef03dfa4d5f039259d0b8b9505685112469d"

PRESERVED_PATHS = (
    "AGENTS.md",
    "START_HERE.md",
    "CURRENT.md",
    "INDEX.md",
    "ELedgerCare.slnx",
    "src",
    "tests",
    "web",
    "deploy",
    "workers",
    "evaluation",
    "qualification",
    "research",
    "docs/agent-reports",
    "docs/reviews/WP-0010/eld-f4-reviewer/design",
)

FORBIDDEN_PATH_TOKENS = (
    "eld-f4-implementer",
    "eledgercare-mapping",
    "eledgercare-coverage",
    "wp-0009/sealed",
    "wp-0009\\sealed",
    "wp-0009-fresh-families",
    "wp-0011-diagnostic-families",
    "eld-coverage-custodian",
    "eld-coverage-author",
    "eld-coverage-reviewer",
    "docs/evaluation/wp-0011",
    "docs\\evaluation\\wp-0011",
    "docs/reviews/wp-0011",
    "docs\\reviews\\wp-0011",
    "docs/kickoffs/wp-0011",
    "docs\\kickoffs\\wp-0011",
    "eledgercare-f2",
)

MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


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


def observe_ports(ports: tuple[int, ...], cwd: Path) -> dict[str, list[dict]]:
    ps_script = (
        "$out = @{}; "
        f"foreach ($p in @({','.join(str(p) for p in ports)})) {{ "
        "$conns = @(Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue | "
        "ForEach-Object { @{ localAddress = $_.LocalAddress; localPort = [int]$_.LocalPort; owningPid = [int]$_.OwningProcess } }); "
        "$out[\"$p\"] = $conns "
        "}; "
        "$out | ConvertTo-Json -Compress -Depth 4"
    )
    cp = run_cmd(["pwsh", "-NoProfile", "-Command", ps_script], cwd=cwd)
    if cp.returncode != 0:
        raise RuntimeError(f"Port observation failed: {cp.stderr}")
    return json.loads(cp.stdout)


def verify_markdown_links(repo_root: Path, prep_dir: Path) -> list[dict]:
    checked: list[dict] = []
    for md_path in sorted(prep_dir.rglob("*.md")):
        content = md_path.read_text(encoding="utf-8")
        for match in MD_LINK_RE.finditer(content):
            raw_target = match.group(1).strip()
            if raw_target.startswith(("http://", "https://", "conversation://", "mailto:")):
                continue
            target_no_frag = raw_target.split("#", 1)[0]
            if not target_no_frag:
                continue
            if target_no_frag.startswith("file:///"):
                resolved = Path(target_no_frag[len("file:///") :]).resolve()
            else:
                resolved = (md_path.parent / target_no_frag).resolve()
            norm = str(resolved).lower()
            for bad in FORBIDDEN_PATH_TOKENS:
                if bad in norm:
                    raise PermissionError(f"Forbidden link target in {md_path}: {raw_target}")
            resolved.relative_to(repo_root.resolve())
            if not resolved.exists():
                raise FileNotFoundError(f"Broken Markdown link in {md_path}: {raw_target} -> {resolved}")
            checked.append({
                "source": md_path.relative_to(repo_root).as_posix(),
                "target": raw_target,
                "resolved": resolved.relative_to(repo_root).as_posix(),
            })
    return checked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build WP-0010 reviewer preparation inventory and verify boundaries.")
    parser.add_argument("--frozen-sha", required=True, help="Exact frozen helper deliverable commit SHA")
    parser.add_argument(
        "--output",
        default="docs/reviews/WP-0010/eld-f4-reviewer/preparation/preparation-inventory.json",
        help="Output inventory JSON path relative to repo root",
    )
    args = parser.parse_args(argv)

    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[6]
    prep_dir = repo_root / "docs" / "reviews" / "WP-0010" / "eld-f4-reviewer" / "preparation"
    out_path = (repo_root / args.output).resolve()

    branch = run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    if branch != "review/wp-0010-f4":
        raise AssertionError(f"Expected branch review/wp-0010-f4, got {branch}")

    head_sha = run_git(repo_root, "rev-parse", "HEAD")
    frozen_sha = run_git(repo_root, "rev-parse", f"{args.frozen_sha}^{{commit}}")

    for req_anc in (PRIOR_DESIGN_002_SHA, AUTHORITY_PREP_SHA, frozen_sha):
        cp = run_cmd(["git", "merge-base", "--is-ancestor", req_anc, head_sha], cwd=repo_root)
        if cp.returncode != 0:
            raise AssertionError(f"Required ancestor {req_anc} is not an ancestor of HEAD {head_sha}")

    # Verify preserved OIDs match coordinator authority identically
    preserved_oids: dict[str, str] = {}
    for rel in PRESERVED_PATHS:
        auth_oid = run_git(repo_root, "rev-parse", f"{AUTHORITY_PREP_SHA}:{rel}")
        head_oid = run_git(repo_root, "rev-parse", f"{head_sha}:{rel}")
        if auth_oid != head_oid:
            raise AssertionError(f"Preserved path {rel} changed! {auth_oid} != {head_oid}")
        preserved_oids[rel] = head_oid

    # Ensure zero canonical /004 report exists yet
    reports_dir = repo_root / "docs" / "agent-reports" / "eld-f4-reviewer" / "WP-0010"
    existing_reports = sorted(p.name for p in reports_dir.glob("*.md"))
    if existing_reports != ["002_2026-11-17_review_eld-f4-reviewer.md"]:
        raise AssertionError(f"Unexpected canonical reports in {reports_dir}: {existing_reports}")

    # Verify git diff vs authority + working tree changes stay strictly inside preparation/
    committed_diff = [
        ln for ln in run_git(repo_root, "diff", "--name-only", AUTHORITY_PREP_SHA, head_sha).splitlines() if ln.strip()
    ]
    wt_status = [
        ln[3:].strip()
        for ln in run_git(repo_root, "status", "--porcelain", "--untracked-files=all").splitlines()
        if ln.strip()
    ]
    allowed_prefix = "docs/reviews/WP-0010/eld-f4-reviewer/preparation/"
    for changed in committed_diff + wt_status:
        norm_changed = changed.strip('"')
        if not norm_changed.startswith(allowed_prefix):
            raise AssertionError(f"Out-of-scope path modified outside {allowed_prefix}: {norm_changed}")

    # Verify secrets redaction across all preparation files
    pg_settings = json.loads((repo_root / ".local" / "secrets" / "pg-local.json").read_text(encoding="utf-8"))
    secrets = [
        str(pg_settings["adminPassword"]),
        str(pg_settings["migratorPassword"]),
        str(pg_settings["appPassword"]),
    ]

    # Collect frozen tree blobs for attribution
    frozen_ls = run_git(repo_root, "ls-tree", "-r", frozen_sha, "--", allowed_prefix)
    frozen_blobs: dict[str, str] = {}
    for line in frozen_ls.splitlines():
        if not line.strip():
            continue
        meta, fpath = line.split("\t", 1)
        frozen_blobs[fpath] = meta.split()[2]

    files_inventory: list[dict] = []
    for fpath in sorted(p for p in prep_dir.rglob("*") if p.is_file()):
        if fpath.resolve() == out_path:
            continue
        rel_posix = fpath.relative_to(repo_root).as_posix()
        raw = fpath.read_bytes()
        raw_text = raw.decode("utf-8", errors="replace")
        for s in secrets:
            if s and s in raw_text:
                raise AssertionError(f"Secret value leaked into {rel_posix}!")
        lf = raw.replace(b"\r\n", b"\n")
        files_inventory.append({
            "path": rel_posix,
            "bytes_raw": len(raw),
            "bytes_lf": len(lf),
            "sha256_raw": sha256_hex(raw),
            "sha256_lf": sha256_hex(lf),
            "in_frozen_deliverable": rel_posix in frozen_blobs,
            "frozen_git_blob_oid": frozen_blobs.get(rel_posix),
        })

    checked_links = verify_markdown_links(repo_root, prep_dir)

    # Verify services stopped and seed DB retained
    ports_now = observe_ports(REVIEWER_PORTS, repo_root)
    if any(len(ports_now[str(p)]) != 0 for p in REVIEWER_PORTS):
        raise AssertionError(f"Owned reviewer ports still have active listeners: {ports_now}")

    pg_ctl = repo_root / ".local" / "tools" / "pgsql-18.7-1" / "bin" / "pg_ctl.exe"
    pg_data = repo_root / ".local" / "postgres-data"
    pg_status_cp = run_cmd([str(pg_ctl), "status", "-D", str(pg_data)], cwd=repo_root)
    if pg_status_cp.returncode != 3 or not (pg_data / "PG_VERSION").exists():
        raise AssertionError(
            f"Expected stopped PostgreSQL cluster (exit 3) with retained PG_VERSION; got exit={pg_status_cp.returncode}"
        )

    seed_receipt = json.loads((prep_dir / "observations" / "preparation-seed-receipt.json").read_text(encoding="utf-8"))
    edge_receipt = json.loads((prep_dir / "observations" / "edge-ui-smoke-receipt.json").read_text(encoding="utf-8"))

    inventory_payload = {
        "schema": "eledgercare.wp-0010.reviewer-preparation-inventory/1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": "eld-f4-reviewer",
        "conversation_id": "61105d43-7706-45f2-9176-69d3256248e0",
        "model_disclosure": {
            "platform": "Antigravity CLI",
            "model": "Gemini 4 Carbon (High)",
            "effort": "high",
            "backend_checkpoint_exposed": False,
            "prior_design_turn_note": "WP-0010 /002 immutable publication 85d879a1adc0ee62090f4c6a5c9a7fb8eb5f3a96 completed before transient post-publication provider DNS resultERROR (OS wrapper 0); never claimed as CLI SUCCESS.",
        },
        "branch": branch,
        "prior_design_002_sha": PRIOR_DESIGN_002_SHA,
        "authority_prep_sha": AUTHORITY_PREP_SHA,
        "frozen_helpers_sha": frozen_sha,
        "canonical_004_published": False,
        "preserved_tree_oids": preserved_oids,
        "retained_seed_summary": {
            "database": seed_receipt["retained_database"],
            "postgres_port": PG_PORT,
            "api_port": API_PORT,
            "ui_port": UI_PORT,
            "canonical_8table_sha256": seed_receipt["canonical_8table_sha256"],
            "table_counts": seed_receipt["table_counts"],
            "fencing_sequence": seed_receipt["fencing_sequence"],
            "decisive_assertion_count": seed_receipt["assertion_count"],
            "edge_browser_version": edge_receipt["browser_version"],
            "edge_smoke_all_passed": edge_receipt["all_passed"],
        },
        "service_state_verified": {
            "ports_listening": ports_now,
            "pg_ctl_status_exit_code": pg_status_cp.returncode,
            "postgres_data_retained": True,
        },
        "markdown_links_verified_count": len(checked_links),
        "secret_redaction_checked_files": len(files_inventory),
        "sibling_file_count": len(files_inventory),
        "files": files_inventory,
    }

    out_str = json.dumps(inventory_payload, indent=2, ensure_ascii=False) + "\n"
    for s in secrets:
        if s and s in out_str:
            raise AssertionError("Secret leaked into preparation-inventory.json!")
    out_path.write_text(out_str, encoding="utf-8", newline="\n")
    print(
        f"PASS: Built {out_path.relative_to(repo_root).as_posix()} "
        f"({len(files_inventory)} sibling files, {len(checked_links)} Markdown links verified, 0 secrets, 0 listeners)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
