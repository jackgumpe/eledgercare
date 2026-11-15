"""Package and verify WP-0005 /005 safe reviewer evidence under
docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REVIEWER_WT = Path(r"C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-reviewer-carbon")
HARNESS_DIR = REVIEWER_WT / "qualification" / "q0" / "harness"
TASK_ROOT = Path(r"C:\Users\jackg\eLedgerCare-Q0\WP-0005")
AUTHOR_EXT_RUN = TASK_ROOT / "runs" / "author" / "20261115T202627Z-eb5bf7da"
REVIEWER_EXT_RUN = TASK_ROOT / "runs" / "reviewer" / "20261115T210422Z-565e2de9"

SCRATCH_DIR = Path(__file__).resolve().parent
PRE_DIR = SCRATCH_DIR / "pre-execute"
POST_DIR = SCRATCH_DIR / "post-execute"

DEST_DIR = REVIEWER_WT / "docs" / "reviews" / "WP-0005" / "eld-q0-reviewer" / "runtime-005"
GIT_EXE = r"C:\Program Files\Git\cmd\git.exe"

sys.path.insert(0, str(HARNESS_DIR))
from q0harness.outcome import assert_no_score  # noqa: E402


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git_out(*args: str) -> str:
    return subprocess.run(
        [GIT_EXE, "-C", str(REVIEWER_WT), *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout


def verify_author_004_publication() -> dict:
    # 1. Core & protected paths unchanged between accepted candidate 41d62046... and 72fffbcb... / current HEAD
    core_paths = [
        "qualification/q0/harness/q0.py",
        "qualification/q0/harness/q0harness",
        "qualification/q0/harness/protocol.json",
        "qualification/q0/harness/locks",
        "qualification/q0/harness/tests",
        "qualification/q0/harness/README.md",
        "qualification/q0/harness/ACQUISITION.md",
        "evaluation",
        "src",
        "tests",
        "ELedgerCare.slnx",
    ]
    core_diff_author = git_out(
        "diff", "--name-status",
        "41d6204648e4115ab197507d1a22f6d5c7f3e784",
        "72fffbcbfa47f3c93425d9de5f338e511df7da3e",
        "--", *core_paths,
    ).strip()
    core_diff_head = git_out(
        "diff", "--name-status",
        "41d6204648e4115ab197507d1a22f6d5c7f3e784",
        "HEAD",
        "--", *core_paths,
    ).strip()
    assert core_diff_author == "", f"Core drift in author 72fffbcb: {core_diff_author}"
    assert core_diff_head == "", f"Core drift in merged HEAD: {core_diff_head}"

    # 2. Verify exact file additions in 9e73ef86, 6e5f87fe, and 72fffbcb
    d_b3d = [
        ln.split("\t", 1) for ln in git_out(
            "diff", "--name-status",
            "099a2fa74cdc2df6068c437edf3971eb37e9f07d",
            "9e73ef86600b5e16f74b056676a6d3a4f1474058",
        ).splitlines() if ln.strip()
    ]
    d_e_ev = [
        ln.split("\t", 1) for ln in git_out(
            "diff", "--name-status",
            "9e73ef86600b5e16f74b056676a6d3a4f1474058",
            "6e5f87fe4d0e19338a387bb5870efd083b2b491c",
        ).splitlines() if ln.strip()
    ]
    d_e_rep = [
        ln.split("\t", 1) for ln in git_out(
            "diff", "--name-status",
            "6e5f87fe4d0e19338a387bb5870efd083b2b491c",
            "72fffbcbfa47f3c93425d9de5f338e511df7da3e",
        ).splitlines() if ln.strip()
    ]
    assert len(d_b3d) == 22 and all(st == "A" and p.startswith("qualification/q0/harness/evidence/004-stages-b3-to-d/") for st, p in d_b3d)
    assert len(d_e_ev) == 47 and all(st == "A" and p.startswith("qualification/q0/harness/evidence/004-gpu-trial/") for st, p in d_e_ev)
    assert d_e_rep == [["A", "docs/agent-reports/eld-q0-harness/WP-0005/004_2026-11-15_verification_eld-q0-harness.md"]]

    run_copy_paths = [
        p for _, p in d_e_ev
        if p.startswith("qualification/q0/harness/evidence/004-gpu-trial/9e73ef86/run-20261115T202627Z-eb5bf7da/")
    ]
    top_meta_paths = [
        p for _, p in d_e_ev
        if not p.startswith("qualification/q0/harness/evidence/004-gpu-trial/9e73ef86/run-20261115T202627Z-eb5bf7da/")
    ]
    assert len(top_meta_paths) == 13 and len(run_copy_paths) == 34

    # 3. Verify author manifest.json (43 records) against working-tree Git files & external author run
    auth_ev_root = REVIEWER_WT / "qualification" / "q0" / "harness" / "evidence" / "004-gpu-trial"
    auth_manifest = json.loads((auth_ev_root / "9e73ef86" / "manifest.json").read_text(encoding="utf-8"))
    manifest_rows = auth_manifest["packaged_files"]
    verified_manifest_count = 0
    verified_run_copy_count = 0
    for row in manifest_rows:
        rel_p = row["relpath"]
        fp = auth_ev_root / rel_p
        assert fp.is_file(), f"Missing author manifest file: {rel_p}"
        raw = fp.read_bytes()
        assert len(raw) == row["bytes"], f"Size mismatch on {rel_p}: {len(raw)} != {row['bytes']}"
        assert sha256_bytes(raw) == row["sha256"], f"SHA-256 mismatch on {rel_p}"
        blob_sha1 = hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()
        assert blob_sha1 == row["git_blob_sha1"], f"Git blob SHA-1 mismatch on {rel_p}"
        verified_manifest_count += 1

    prefix = "qualification/q0/harness/evidence/004-gpu-trial/9e73ef86/run-20261115T202627Z-eb5bf7da/"
    for p in run_copy_paths:
        sub = p[len(prefix):]
        git_bytes = (REVIEWER_WT / p).read_bytes()
        ext_bytes = (AUTHOR_EXT_RUN / sub).read_bytes()
        assert git_bytes == ext_bytes, f"Author run copy differs from external original: {sub}"
        verified_run_copy_count += 1

    # 4. Verify the 4 report-only reconciliations from actual author artifacts
    auth_out = json.loads(
        (auth_ev_root / "9e73ef86" / "run-20261115T202627Z-eb5bf7da" / "evidence" / "outcome.json").read_text(encoding="utf-8")
    )
    kernel_labels = [o["kernel_path"]["label"] for o in auth_out["observations"]]
    assert kernel_labels == ["triton_import_failed_dense_fallback"] * 6

    exec_meta = json.loads((auth_ev_root / "9e73ef86" / "03-execute-meta.json").read_text(encoding="utf-8"))
    box_re = re.compile(r"\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]")
    a_wu_txt = (AUTHOR_EXT_RUN / "evidence" / "F01.warmup.raw.txt").read_text(encoding="utf-8")
    a_w1_txt = (AUTHOR_EXT_RUN / "evidence" / "F01.warm1.raw.txt").read_text(encoding="utf-8")
    a_wu_tok = json.loads((AUTHOR_EXT_RUN / "evidence" / "F01.warmup.token_ids.json").read_text(encoding="utf-8"))
    a_w1_tok = json.loads((AUTHOR_EXT_RUN / "evidence" / "F01.warm1.token_ids.json").read_text(encoding="utf-8"))
    wu_boxes = [tuple(int(g) for g in m.groups()) for m in box_re.finditer(a_wu_txt)]
    w1_boxes = [tuple(int(g) for g in m.groups()) for m in box_re.finditer(a_w1_txt)]
    max_delta = max(abs(x - y) for bx, by in zip(wu_boxes, w1_boxes) for x, y in zip(bx, by))
    diff_tok_pos = sum(1 for x, y in zip(a_wu_tok, a_w1_tok) if x != y)
    assert box_re.sub("[]", a_wu_txt) == box_re.sub("[]", a_w1_txt)
    assert diff_tok_pos == 19 and max_delta == 10

    return {
        "schema": "eld-q0-reviewer-005-author-004-audit/1",
        "audited_utc": datetime.now(timezone.utc).isoformat(),
        "accepted_core_commit": "41d6204648e4115ab197507d1a22f6d5c7f3e784",
        "author_staging_b3_d_commit": "9e73ef86600b5e16f74b056676a6d3a4f1474058",
        "author_stage_e_evidence_commit": "6e5f87fe4d0e19338a387bb5870efd083b2b491c",
        "author_canonical_004_report_commit": "72fffbcbfa47f3c93425d9de5f338e511df7da3e",
        "core_and_evaluation_unchanged": True,
        "staging_b3_d_added_files": len(d_b3d),
        "stage_e_evidence_added_files_total": len(d_e_ev),
        "stage_e_top_level_and_metadata_files": len(top_meta_paths),
        "stage_e_run_copy_files": len(run_copy_paths),
        "canonical_report_only_addition": True,
        "manifest_records_verified": verified_manifest_count,
        "external_run_copies_byte_identical": verified_run_copy_count,
        "reconciled_report_only_items_verified": {
            "1_all_six_calls_used_native_dense_fallback": kernel_labels,
            "2_stage_e_file_split_13_plus_34_equals_47": {
                "top_level_and_metadata": len(top_meta_paths),
                "run_copies": len(run_copy_paths),
                "total": len(d_e_ev),
            },
            "3_f01_warmup_vs_warm1_coordinate_delta": {
                "differing_token_positions": diff_tok_pos,
                "paired_box_tuples": len(wu_boxes),
                "non_coordinate_text_identical": True,
                "max_native_coordinate_unit_delta": max_delta,
            },
            "4_execute_command_argv_recorded": exec_meta.get("argv") or exec_meta.get("command"),
        },
    }


def main() -> int:
    if DEST_DIR.exists():
        shutil.rmtree(DEST_DIR)
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    (DEST_DIR / ".gitattributes").write_bytes(b"* -text\n")

    # 14. Author /004 audit
    auth_audit = verify_author_004_publication()
    (POST_DIR / "14-author-004-publication-verification.json").write_bytes(
        (json.dumps(auth_audit, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )

    # Copy wrappers
    wrappers_dir = DEST_DIR / "wrappers"
    wrappers_dir.mkdir(parents=True, exist_ok=True)
    for wname in ("run_pre_execute_checks.py", "launch_reviewer_execute.py", "run_post_execute_and_compare.py", "package_005_evidence.py"):
        shutil.copyfile(SCRATCH_DIR / wname, wrappers_dir / wname)

    # Copy pre/post check outputs
    checks_dir = DEST_DIR / "checks"
    checks_dir.mkdir(parents=True, exist_ok=True)
    pre_files = [
        "pre-execute-summary.json",
        "01-host-precheck-during.json",
        "02-verify-wheelhouse.json",
        "03-pip-check-and-venv-inventory.json",
        "04-verify-model-before.json",
        "05-preflight-cpu.json",
        "06-pre-gpu-process-and-vram.json",
        "07-execute-reviewer-receipt.json",
        "07-execute-reviewer-stdout.json",
        "07-execute-reviewer-stderr.txt",
    ]
    for fn in pre_files:
        shutil.copyfile(PRE_DIR / fn, checks_dir / fn)

    post_files = [
        "08-post-run-worker-exit-and-lease-return.json",
        "09-post-run-host-precheck-during.json",
        "10-verify-model-after.json",
        "11-module-cache-verification.json",
        "12-reviewer-run-inventory.json",
        "13-author-vs-reviewer-comparison.json",
        "14-author-004-publication-verification.json",
    ]
    for fn in post_files:
        shutil.copyfile(POST_DIR / fn, checks_dir / fn)

    # Copy all non-binary-cache runtime files from runs\reviewer\20261115T210422Z-565e2de9
    run_copy_root = DEST_DIR / "run-20261115T210422Z-565e2de9"
    copied_external_map: dict[str, str] = {}
    for src_fp in sorted(REVIEWER_EXT_RUN.rglob("*")):
        if not src_fp.is_file():
            continue
        rel = src_fp.relative_to(REVIEWER_EXT_RUN).as_posix()
        if rel.startswith("cuda-cache/") or rel.startswith("hf-modules/"):
            continue
        dst_fp = run_copy_root / rel
        dst_fp.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_fp, dst_fp)
        assert dst_fp.read_bytes() == src_fp.read_bytes()
        copied_external_map[dst_fp.relative_to(DEST_DIR).as_posix()] = str(src_fp)

    # Safety & assert_no_score & max_path_len check across all staged files
    secret_patterns = [
        re.compile(r"hf_[A-Za-z0-9]{20,}"),
        re.compile(r"ghp_[A-Za-z0-9]{20,}"),
        re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
        re.compile(r"AIza[0-9A-Za-z\-_]{30,}"),
        re.compile(r"Authorization:\s*Bearer", re.IGNORECASE),
    ]
    manifest_entries = []
    max_repo_path_len = 0
    for fp in sorted(DEST_DIR.rglob("*")):
        if not fp.is_file():
            continue
        full_str = str(fp)
        max_repo_path_len = max(max_repo_path_len, len(full_str))
        assert len(full_str) < 240, f"Staged path >= 240 chars: {full_str} ({len(full_str)})"
        rel_dest = fp.relative_to(DEST_DIR).as_posix()
        raw = fp.read_bytes()
        txt = raw.decode("utf-8")
        for pat in secret_patterns:
            assert not pat.search(txt), f"Potential secret pattern {pat.pattern} in {rel_dest}"
        if fp.suffix == ".json":
            parsed = json.loads(txt)
            if rel_dest.startswith("run-20261115T210422Z-565e2de9/"):
                assert_no_score(parsed)
        manifest_entries.append({
            "path": rel_dest,
            "bytes": len(raw),
            "sha256": sha256_bytes(raw),
            "source_copy": copied_external_map.get(rel_dest),
        })

    # Write README.md
    readme_lines = [
        "# WP-0005 /005 Independent Runtime Verification & Reproduction Evidence (`eld-q0-reviewer`)",
        "",
        "Safe in-Git evidence for the independent WP-0005 `/005` pre-execution verification, single unmodified-model Q0 GPU reproduction trial (`20261115T210422Z-565e2de9`), observed dual-PID worker exit & explicit GPU lease return (`WP-0005-reviewer-005-20261115T205527Z`), and independent audit of author `/004` (`9e73ef86600b5e16f74b056676a6d3a4f1474058`, `6e5f87fe4d0e19338a387bb5870efd083b2b491c`, `72fffbcbfa47f3c93425d9de5f338e511df7da3e`).",
        "",
        "This directory sets `* -text` so every script, check output, and raw runtime artifact preserves exact bytes and SHA-256 digests. No wheels, model weights, binary `.pyc`/CUDA caches, credentials, cookies, or private transcripts are included. External reviewer artifacts remain untouched at `C:\\Users\\jackg\\eLedgerCare-Q0\\WP-0005\\runs\\reviewer\\20261115T210422Z-565e2de9` (`101` files, `65,853,464` B).",
        "",
        "| Field | Value |",
        "| --- | --- |",
        "| Reviewer / session | `eld-q0-reviewer` / Gemini 4 Carbon (High) (`gemini-4-carbon-high`, `high` effort), `0815536f-045a-4112-8a89-ebf0e0cc782f` |",
        "| Owned branch / worktree | `review/wp-0005-q0-carbon` / `C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\eld-q0-reviewer-carbon` |",
        "| Clean executing `HEAD` throughout verification & GPU trial | `c8daa97c5be6bc67931b215652a7a0f6ced621ef` (`harness_clean: true`, `dirty: []`) |",
        "| Accepted harness core (`0` core edits) | `41d6204648e4115ab197507d1a22f6d5c7f3e784` |",
        "| Bound coordinator releases | `reviewer-install.json` & `reviewer-execute.json` (`release_commit` `3a2906b1eb7f1873ae9129119d465ea0813d31f3`, dispatch `a3422609ff0afab5ca01c51be140e03a2066f6e9`) |",
        "| Sole reviewer GPU lease | `WP-0005-reviewer-005-20261115T205527Z` (**RETURNED** at `2026-11-15T21:25:47.167155+00:00` after `child_pid=30436` & `heartbeat.pid=30484` verified absent) |",
        "| Reviewer run ID & supervisor verdict | `20261115T210422Z-565e2de9` / `CHILD_COMPLETED` (`elapsed_s: 1266.187`, `child_returncode: 0`) |",
        "| Domain qualification outcome | `QUALIFIED_RUNTIME_OBSERVATION` (`6/6` checks pass, `failures: []`, `accuracy_score: null`) |",
        "| Cross-run reproduction vs author `20261115T202627Z-eb5bf7da` | **`6/6` calls (`11,040 / 11,040` generated tokens) match token-for-token and byte-for-byte** (`F01.warmup`, `F07.warmup`, `F01.warm1`, `F07.warm1`, `F01.warm2`, `F07.warm2`) |",
        "",
        "## Index of Evidence Files",
        "",
        "- [manifest.json](manifest.json): complete byte-size and SHA-256 manifest of this directory",
        "- Pre-execution verification (`checks/01..06`, `pre-execute-summary.json`):",
        "  - [checks/pre-execute-summary.json](checks/pre-execute-summary.json)",
        "  - [checks/01-host-precheck-during.json](checks/01-host-precheck-during.json)",
        "  - [checks/02-verify-wheelhouse.json](checks/02-verify-wheelhouse.json)",
        "  - [checks/03-pip-check-and-venv-inventory.json](checks/03-pip-check-and-venv-inventory.json)",
        "  - [checks/04-verify-model-before.json](checks/04-verify-model-before.json)",
        "  - [checks/05-preflight-cpu.json](checks/05-preflight-cpu.json)",
        "  - [checks/06-pre-gpu-process-and-vram.json](checks/06-pre-gpu-process-and-vram.json)",
        "- Single GPU trial invocation (`checks/07*`):",
        "  - [checks/07-execute-reviewer-receipt.json](checks/07-execute-reviewer-receipt.json)",
        "  - [checks/07-execute-reviewer-stdout.json](checks/07-execute-reviewer-stdout.json)",
        "  - [checks/07-execute-reviewer-stderr.txt](checks/07-execute-reviewer-stderr.txt)",
        "- Post-execution lease return, reverification, run inventory, comparison & `/004` audit (`checks/08..14`):",
        "  - [checks/08-post-run-worker-exit-and-lease-return.json](checks/08-post-run-worker-exit-and-lease-return.json)",
        "  - [checks/09-post-run-host-precheck-during.json](checks/09-post-run-host-precheck-during.json)",
        "  - [checks/10-verify-model-after.json](checks/10-verify-model-after.json)",
        "  - [checks/11-module-cache-verification.json](checks/11-module-cache-verification.json)",
        "  - [checks/12-reviewer-run-inventory.json](checks/12-reviewer-run-inventory.json)",
        "  - [checks/13-author-vs-reviewer-comparison.json](checks/13-author-vs-reviewer-comparison.json)",
        "  - [checks/14-author-004-publication-verification.json](checks/14-author-004-publication-verification.json)",
        "- Byte-identical reviewer runtime copies (`72` files under `run-20261115T210422Z-565e2de9/`):",
        "  - [run-20261115T210422Z-565e2de9/supervisor.json](run-20261115T210422Z-565e2de9/supervisor.json)",
        "  - [run-20261115T210422Z-565e2de9/heartbeat.json](run-20261115T210422Z-565e2de9/heartbeat.json)",
        "  - [run-20261115T210422Z-565e2de9/parent-context.json](run-20261115T210422Z-565e2de9/parent-context.json)",
        "  - [run-20261115T210422Z-565e2de9/child.stdout.txt](run-20261115T210422Z-565e2de9/child.stdout.txt)",
        "  - [run-20261115T210422Z-565e2de9/child.stderr.txt](run-20261115T210422Z-565e2de9/child.stderr.txt)",
        "  - [run-20261115T210422Z-565e2de9/evidence/outcome.json](run-20261115T210422Z-565e2de9/evidence/outcome.json) and all `22` sibling `evidence/*` files plus `44` `observer-*.txt` snapshots",
        "- Reviewer scratch wrappers (`wrappers/`): [run_pre_execute_checks.py](wrappers/run_pre_execute_checks.py), [launch_reviewer_execute.py](wrappers/launch_reviewer_execute.py), [run_post_execute_and_compare.py](wrappers/run_post_execute_and_compare.py), [package_005_evidence.py](wrappers/package_005_evidence.py)",
        "",
    ]
    readme_bytes = "\n".join(readme_lines).encode("utf-8")
    (DEST_DIR / "README.md").write_bytes(readme_bytes)
    manifest_entries.append({
        "path": "README.md",
        "bytes": len(readme_bytes),
        "sha256": sha256_bytes(readme_bytes),
        "source_copy": None,
    })
    manifest_entries.sort(key=lambda x: x["path"])

    manifest_doc = {
        "schema": "eld-q0-reviewer-005-evidence-manifest/1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "executing_head": "c8daa97c5be6bc67931b215652a7a0f6ced621ef",
        "merged_author_004_report_commit": "72fffbcbfa47f3c93425d9de5f338e511df7da3e",
        "reviewer_run_id": "20261115T210422Z-565e2de9",
        "lease_id": "WP-0005-reviewer-005-20261115T205527Z",
        "lease_status": "RETURNED",
        "file_count_excluding_manifest": len(manifest_entries),
        "total_bytes_excluding_manifest": sum(e["bytes"] for e in manifest_entries),
        "max_worktree_path_len": max_repo_path_len,
        "files": manifest_entries,
    }
    manifest_bytes = (json.dumps(manifest_doc, indent=2, sort_keys=True) + "\n").encode("utf-8")
    (DEST_DIR / "manifest.json").write_bytes(manifest_bytes)

    print(json.dumps({
        "staged_dir": str(DEST_DIR),
        "files_excluding_manifest": len(manifest_entries),
        "total_files_including_manifest": len(manifest_entries) + 1,
        "total_bytes_including_manifest": sum(e["bytes"] for e in manifest_entries) + len(manifest_bytes),
        "manifest_bytes": len(manifest_bytes),
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "readme_bytes": len(readme_bytes),
        "readme_sha256": sha256_bytes(readme_bytes),
        "max_worktree_path_len": max_repo_path_len,
        "copied_runtime_files": len(copied_external_map),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
