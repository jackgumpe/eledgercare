"""Inventory, boundary, preservation, secret-redaction, and Markdown-link verifier for WP-0010 / 007.

Generates `docs/reviews/WP-0010/eld-f4-reviewer/search-navigation/final/final-007-inventory.json`
and enforces:
  1. Changes since merged base `b9bf6f1d99617445b7b1b91c09088c8ecac70f1c` stay strictly under
     `docs/reviews/WP-0010/eld-f4-reviewer/search-navigation/final/**` (before single-file `/007` commit).
  2. Every prepared file in `search-navigation/` outside `final/`, plus `/002`, `design/**`,
     `preparation/**`, `runtime/**`, `/004`, `/003`, `/006`, `src`, `web`, `tests`, `deploy`,
     `workers`, and shared ledgers, remains 100% byte-identical.
  3. All local Markdown links across `search-navigation/final/**/*.md` resolve inside the repository.
  4. Zero credentials from `.local/secrets/pg-local.json` appear in `search-navigation/final/**`.
  5. All owned ports (`5690`, `4710`, `55439`) have `0` listeners and `pg_ctl status` exits `3`.
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

sys.dont_write_bytecode = True

REVIEWER_PORTS = (5690, 4710, 55439)
MERGED_FINAL_007_BASE_SHA = "b9bf6f1d99617445b7b1b91c09088c8ecac70f1c"
PRIOR_002_SHA = "85d879a1adc0ee62090f4c6a5c9a7fb8eb5f3a96"
PRIOR_PREP_SHA = "349c29773009abdf1bc228d01696d58a83d3eaa2"
PRIOR_004_SHA = "324f09934b0aa2ee8e7bed7e8118c6109effb918"
PRIOR_SN_PREP_PUB_SHA = "b12664dfbfd533f177a4e1089c983952d485b8c2"
ROOT_FINAL_AUTHORITY_SHA = "deba1aeba80967ca6d0bce2f14da09716118ba44"
AUTHOR_006_CANDIDATE_SHA = "c1fed68020ae67e8b4763bc6ea5473adaa86de2b"
AUTHOR_006_EVIDENCE_SHA = "9e1d6c4211daadfb82f67911ece04568ed8610fe"
AUTHOR_006_PUB_SHA = "0f689d9b6eaf415d17095f14ad57dff2d716bac5"

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
    "docs/design",
    "docs/reviews/WP-0010/eld-f4-reviewer/design",
    "docs/reviews/WP-0010/eld-f4-reviewer/preparation",
    "docs/reviews/WP-0010/eld-f4-reviewer/runtime",
    "docs/reviews/WP-0010/eld-f4-reviewer/search-navigation/.gitattributes",
    "docs/reviews/WP-0010/eld-f4-reviewer/search-navigation/README.md",
    "docs/reviews/WP-0010/eld-f4-reviewer/search-navigation/EVIDENCE-RECONCILIATION.md",
    "docs/reviews/WP-0010/eld-f4-reviewer/search-navigation/helpers",
    "docs/reviews/WP-0010/eld-f4-reviewer/search-navigation/observations",
    "docs/reviews/WP-0010/eld-f4-reviewer/search-navigation/resource-return.json",
    "docs/reviews/WP-0010/eld-f4-reviewer/search-navigation/search-navigation-prep-inventory.json",
    "docs/implementation/WP-0010/eld-f4-implementer",
    "docs/agent-reports/eld-f4-implementer/WP-0010",
    "docs/agent-reports/eld-f4-reviewer/WP-0010/002_2026-11-17_review_eld-f4-reviewer.md",
    "docs/agent-reports/eld-f4-reviewer/WP-0010/004_2026-11-17_review_eld-f4-reviewer.md",
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


def run_git_raw(repo_root: Path, *args: str) -> str:
    cp = run_cmd(["git", *args], cwd=repo_root)
    if cp.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {cp.stderr}")
    return cp.stdout


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


def verify_markdown_links(repo_root: Path, final_dir: Path, out_path: Path) -> list[dict]:
    checked: list[dict] = []
    for md_path in sorted(final_dir.rglob("*.md")):
        content = md_path.read_text(encoding="utf-8")
        for match in MD_LINK_RE.finditer(content):
            raw_target = match.group(1).strip()
            if raw_target.startswith(("http://", "https://", "conversation://", "mailto:")):
                continue
            target_no_frag = raw_target.split("#", 1)[0]
            if not target_no_frag:
                continue
            resolved = (
                Path(target_no_frag[len("file:///") :]).resolve()
                if target_no_frag.startswith("file:///")
                else (md_path.parent / target_no_frag).resolve()
            )
            resolved.relative_to(repo_root.resolve())
            if resolved != out_path and not resolved.exists():
                raise FileNotFoundError(f"Broken Markdown link in {md_path}: {raw_target} -> {resolved}")
            checked.append({
                "source": md_path.relative_to(repo_root).as_posix(),
                "target": raw_target,
                "resolved": resolved.relative_to(repo_root).as_posix(),
            })
    return checked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build WP-0010 / 007 final review inventory.")
    parser.add_argument("--frozen-sha", required=True, help="Exact frozen helper commit SHA")
    parser.add_argument(
        "--output",
        default="docs/reviews/WP-0010/eld-f4-reviewer/search-navigation/final/final-007-inventory.json",
        help="Output inventory JSON path relative to repo root",
    )
    args = parser.parse_args(argv)

    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[7]
    if not (repo_root / "ELedgerCare.slnx").exists():
        raise RuntimeError(f"Unexpected repo_root: {repo_root}")

    final_dir = repo_root / "docs/reviews/WP-0010/eld-f4-reviewer/search-navigation/final"
    out_path = (repo_root / args.output).resolve()

    branch = run_git_raw(repo_root, "rev-parse", "--abbrev-ref", "HEAD").strip()
    if branch != "review/wp-0010-f4":
        raise AssertionError(f"Expected branch review/wp-0010-f4, got {branch}")

    head_sha = run_git_raw(repo_root, "rev-parse", "HEAD").strip()
    frozen_sha = run_git_raw(repo_root, "rev-parse", f"{args.frozen_sha}^{{commit}}").strip()

    for req_anc in (
        PRIOR_002_SHA,
        PRIOR_PREP_SHA,
        PRIOR_004_SHA,
        PRIOR_SN_PREP_PUB_SHA,
        ROOT_FINAL_AUTHORITY_SHA,
        AUTHOR_006_PUB_SHA,
        MERGED_FINAL_007_BASE_SHA,
        frozen_sha,
    ):
        if run_cmd(["git", "merge-base", "--is-ancestor", req_anc, head_sha], cwd=repo_root).returncode != 0:
            raise AssertionError(f"Required ancestor {req_anc} is not an ancestor of HEAD {head_sha}")

    preserved_oids: dict[str, str] = {}
    for rel in PRESERVED_PATHS:
        base_oid = run_git_raw(repo_root, "rev-parse", f"{MERGED_FINAL_007_BASE_SHA}:{rel}").strip()
        head_oid = run_git_raw(repo_root, "rev-parse", f"{head_sha}:{rel}").strip()
        if base_oid != head_oid:
            raise AssertionError(f"Preserved path {rel} changed! {base_oid} != {head_oid}")
        preserved_oids[rel] = head_oid

    committed_diff = [
        ln.strip()
        for ln in run_git_raw(repo_root, "diff", "--name-only", MERGED_FINAL_007_BASE_SHA, head_sha).splitlines()
        if ln.strip()
    ]
    wt_status = [
        ln[3:].strip()
        for ln in run_git_raw(repo_root, "status", "--porcelain", "--untracked-files=all").splitlines()
        if len(ln) > 3
    ]
    allowed_prefix = "docs/reviews/WP-0010/eld-f4-reviewer/search-navigation/final/"
    for changed in committed_diff + wt_status:
        norm = changed.strip('"')
        if not norm.startswith(allowed_prefix):
            raise AssertionError(f"Out-of-scope path modified outside {allowed_prefix}: {norm}")

    pg_settings = json.loads((repo_root / ".local/secrets/pg-local.json").read_text(encoding="utf-8"))
    secrets = [str(pg_settings["adminPassword"]), str(pg_settings["migratorPassword"]), str(pg_settings["appPassword"])]

    frozen_ls = run_git_raw(repo_root, "ls-tree", "-r", frozen_sha, "--", allowed_prefix)
    frozen_blobs: dict[str, str] = {}
    for line in frozen_ls.splitlines():
        if line.strip():
            meta, fpath = line.split("\t", 1)
            frozen_blobs[fpath] = meta.split()[2]

    files_inventory: list[dict] = []
    for fpath in sorted(p for p in final_dir.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        if fpath.resolve() == out_path:
            continue
        rel_posix = fpath.relative_to(repo_root).as_posix()
        raw = fpath.read_bytes()
        if fpath.suffix.lower() not in (".png",):
            raw_text = raw.decode("utf-8", errors="replace")
            for s in secrets:
                if s and s in raw_text:
                    raise AssertionError(f"Secret value leaked into {rel_posix}!")
            lf = raw.replace(b"\r\n", b"\n")
            files_inventory.append({
                "path": rel_posix,
                "is_binary": False,
                "bytes_raw": len(raw),
                "bytes_lf": len(lf),
                "sha256_raw": sha256_hex(raw),
                "sha256_lf": sha256_hex(lf),
                "in_frozen_deliverable": rel_posix in frozen_blobs,
                "frozen_git_blob_oid": frozen_blobs.get(rel_posix),
            })
        else:
            files_inventory.append({
                "path": rel_posix,
                "is_binary": True,
                "bytes_raw": len(raw),
                "sha256_raw": sha256_hex(raw),
                "in_frozen_deliverable": rel_posix in frozen_blobs,
                "frozen_git_blob_oid": frozen_blobs.get(rel_posix),
            })

    checked_links = verify_markdown_links(repo_root, final_dir, out_path)

    ports_now = observe_ports(REVIEWER_PORTS, repo_root)
    if any(len(ports_now[str(p)]) != 0 for p in REVIEWER_PORTS):
        raise AssertionError(f"Owned reviewer ports still have active listeners: {ports_now}")

    pg_ctl = repo_root / ".local/tools/pgsql-18.7-1/bin/pg_ctl.exe"
    pg_data = repo_root / ".local/postgres-data"
    pg_status_cp = run_cmd([str(pg_ctl), "status", "-D", str(pg_data)], cwd=repo_root)
    if pg_status_cp.returncode != 3 or not (pg_data / "PG_VERSION").exists():
        raise AssertionError(f"Expected stopped PG cluster (exit 3); got {pg_status_cp.returncode}")

    summary = json.loads((final_dir / "observations/verification-summary.json").read_text(encoding="utf-8"))

    reused_inputs = [
        {
            "path": "docs/reviews/WP-0010/eld-f4-reviewer/search-navigation/helpers/probe_f4_search_navigation.mjs",
            "sha256_lf": summary["helpers"]["reused_prepared_probe_mjs_sha256"],
        },
        {
            "path": "docs/reviews/WP-0010/eld-f4-reviewer/search-navigation/observations/c383-reproduction-probe-receipt.json",
            "sha256_raw": sha256_hex(
                (repo_root / "docs/reviews/WP-0010/eld-f4-reviewer/search-navigation/observations/c383-reproduction-probe-receipt.json").read_bytes()
            ),
        },
        {
            "path": "docs/reviews/WP-0010/eld-f4-reviewer/runtime/helpers/verify_f4_independent_edge.mjs",
            "sha256_lf": summary["helpers"]["reused_runtime_edge_helper_mjs_sha256"],
        },
        {
            "path": "docs/reviews/WP-0010/eld-f4-reviewer/runtime/observations/verification-summary.json",
            "sha256_raw": sha256_hex(
                (repo_root / "docs/reviews/WP-0010/eld-f4-reviewer/runtime/observations/verification-summary.json").read_bytes()
            ),
        },
    ]

    payload = {
        "schema": "eledgercare.wp-0010.reviewer-final-007-inventory/1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": "eld-f4-reviewer",
        "conversation_id": "61105d43-7706-45f2-9176-69d3256248e0",
        "branch": branch,
        "merged_final_007_base_sha": MERGED_FINAL_007_BASE_SHA,
        "root_final_authority_sha": ROOT_FINAL_AUTHORITY_SHA,
        "author_006_candidate_sha": AUTHOR_006_CANDIDATE_SHA,
        "author_006_evidence_sha": AUTHOR_006_EVIDENCE_SHA,
        "author_006_publication_sha": AUTHOR_006_PUB_SHA,
        "frozen_final_007_helpers_sha": frozen_sha,
        "preserved_tree_oids": preserved_oids,
        "reused_readonly_inputs": reused_inputs,
        "decisive_summary": {
            "logged_step_count": len(summary["logged_steps"]),
            "assertion_count": summary["assertion_count"],
            "before_vs_after_6scenario_probe": summary["before_vs_after_6scenario_probe"],
            "retained_databases_verified_unchanged": summary["retained_databases_verified_unchanged"],
        },
        "service_state_verified": {
            "ports_listening": ports_now,
            "pg_ctl_status_exit_code": pg_status_cp.returncode,
            "postgres_data_retained": True,
        },
        "markdown_links_verified_count": len(checked_links),
        "sibling_file_count": len(files_inventory),
        "files": files_inventory,
    }

    out_str = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    for s in secrets:
        if s and s in out_str:
            raise AssertionError("Secret leaked into final-007-inventory.json!")
    out_path.write_text(out_str, encoding="utf-8", newline="\n")
    print(
        f"PASS: Built {out_path.relative_to(repo_root).as_posix()} "
        f"({len(files_inventory)} sibling files, {len(checked_links)} Markdown links verified, 0 secrets, 0 listeners)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
