"""Read-only Phase 1 verification helper for WP-0006 /002 and provisional WP-0007 /001 design review.

Audits the root design candidate (efa9cb986711f82a886f917e68142a7a59319bba) and report tip
(c08d50e204395e60a88ce25f70e25bd29b97b8c6) against accepted F1 product source, accepted WP-0004
corpus metadata and DEV-only records, and accepted WP-0005 Q0 harness/runtime observations.

Hard holdout boundary: refuses to open any evaluation/synthetic/{pdfs,sources,expected} path
belonging to holdout families F03, F05, F06, or F08 (SYN-WO-03, SYN-INV-02, SYN-INV-03, SYN-MP-02).
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import pathlib
import re
import subprocess
import sys

PACKET_BASE = "8e80a42c29c0fc27a4af6348cfb1ec22cab3764d"
DESIGN_CANDIDATE = "efa9cb986711f82a886f917e68142a7a59319bba"
DISPATCH_REPORT_TIP = "c08d50e204395e60a88ce25f70e25bd29b97b8c6"
F1_CANDIDATE = "e3117ec2aa11a78359a754cfe52ef3ece6c1733f"
CORPUS_CANDIDATE = "29b2000265ae6068d9c86818622c81a40cadd961"
Q0_CORE_CANDIDATE = "41d6204648e4115ab197507d1a22f6d5c7f3e784"

DEV_FAMILIES = {"F01", "F02", "F04", "F07"}
HOLDOUT_FAMILIES = {"F03", "F05", "F06", "F08"}
HOLDOUT_PREFIXES = ("SYN-WO-03", "SYN-INV-02", "SYN-INV-03", "SYN-MP-02")

EXPECTED_DESIGN_BLOBS = {
    "AGENTS.md": "8219b77d8d69a90454703289b3f667fcc8bd39cb",
    "CURRENT.md": "0a0427b13fa8be14c01b581aae0eaa73a98ab229",
    "INDEX.md": "8efb26f947b9bedf8f44af864c8887cc223b56ce",
    "docs/design/B0-vanilla-accuracy-baseline.md": "05c9ff231ae250ca96488132c53bdaf218f200f6",
    "docs/design/F2-local-extraction.md": "8ce0c854baa889ea090d5b941d6aba0de34a5bde",
    "docs/kickoffs/WP-0006-0007-eld-next-reviewer.md": "8e7f252d8428956b2cd6cf5c60b00d612ed7733e",
    "docs/kickoffs/WP-0006-eld-f2-implementer.md": "918ff5e2f762fa4a9e114252bf1eb29e134106db",
    "docs/kickoffs/WP-0007-eld-rd-astra.md": "56757732e5c3ce2521c213b8496f7276d40e13ef",
}

EXPECTED_REPORT_BLOBS = {
    "docs/agent-reports/eld-coordinator/WP-0006/001_2026-11-16_design_eld-coordinator.md": "bfc16945d2ef9143b9961e1cc40941e665eb09c2",
    "docs/agent-reports/eld-coordinator/WP-0007/001_2026-11-16_design_eld-coordinator.md": "4b381ac64026139d645ab538e62f75e994e15b53",
}


class SafeRepoReader:
    """Tracks every repository file read and refuses holdout PDF/source/expected paths."""

    def __init__(self, repo_root: pathlib.Path) -> None:
        self.root = repo_root.resolve()
        self.opened_paths: list[str] = []

    def _guard(self, rel_posix: str) -> pathlib.Path:
        if ".." in pathlib.PurePosixPath(rel_posix).parts or rel_posix.startswith("/"):
            raise RuntimeError(f"Escaping path refused: {rel_posix}")
        if rel_posix.startswith("evaluation/synthetic/"):
            for fam in HOLDOUT_FAMILIES:
                if f"/{fam}/" in rel_posix or f"/{fam}_" in rel_posix:
                    raise RuntimeError(f"Holdout family access refused: {rel_posix}")
            for pfx in HOLDOUT_PREFIXES:
                if pfx in rel_posix:
                    raise RuntimeError(f"Holdout fixture access refused: {rel_posix}")
        if rel_posix.startswith("evaluation/generation/") and rel_posix.endswith(".py"):
            raise RuntimeError(f"Corpus generator script access refused (contains holdout literals): {rel_posix}")
        target = (self.root / rel_posix).resolve()
        if self.root not in target.parents and target != self.root:
            raise RuntimeError(f"Path outside repository refused: {rel_posix}")
        self.opened_paths.append(rel_posix)
        return target

    def read_bytes(self, rel_posix: str) -> bytes:
        return self._guard(rel_posix).read_bytes()

    def read_text(self, rel_posix: str) -> str:
        return self.read_bytes(rel_posix).decode("utf-8")

    def read_json(self, rel_posix: str) -> dict:
        return json.loads(self.read_text(rel_posix))


def run_git(repo_root: pathlib.Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "--no-optional-locks", "-C", str(repo_root), *args])


def git_tree(repo_root: pathlib.Path, rev: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for entry in run_git(repo_root, "ls-tree", "-rz", "--full-tree", rev).split(b"\0"):
        if entry:
            meta, path_bytes = entry.split(b"\t", 1)
            out[path_bytes.decode("utf-8")] = meta.decode("ascii").split()[2]
    return out


def git_changed_paths(repo_root: pathlib.Path, rev: str) -> dict[str, str]:
    rows = run_git(repo_root, "diff-tree", "--no-commit-id", "--name-status", "-r", rev).decode("utf-8").splitlines()
    out: dict[str, str] = {}
    for row in rows:
        if row.strip():
            status, path = row.split("\t", 1)
            out[path] = status
    return out


def check_f1_pdf_structural_profile(pdf_bytes: bytes) -> dict:
    has_header = (
        len(pdf_bytes) >= 9
        and pdf_bytes.startswith(b"%PDF-1.")
        and ord("0") <= pdf_bytes[7] <= ord("7")
        and pdf_bytes[8] in b"\x00\t\n\x0c\r "
    )
    trimmed = pdf_bytes.rstrip(b"\x00\t\n\x0c\r ")
    has_eof = trimmed.endswith(b"%%EOF")
    idx = pdf_bytes.rfind(b"startxref")
    valid_xref = False
    xref_offset = None
    if idx >= 0:
        rest = pdf_bytes[idx + 9 :].lstrip(b"\x00\t\n\x0c\r ")
        m = re.match(rb"(\d{1,10})", rest)
        if m:
            xref_offset = int(m.group(1))
            if 0 <= xref_offset < len(pdf_bytes):
                target = pdf_bytes[xref_offset : xref_offset + 32]
                valid_xref = target.startswith(b"xref") or bool(re.match(rb"\d+\s+\d+\s+obj", target))
    return {
        "byte_length": len(pdf_bytes),
        "within_10mib": 1 <= len(pdf_bytes) <= 10_485_760,
        "sha256": hashlib.sha256(pdf_bytes).hexdigest(),
        "has_supported_pdf1_header": has_header,
        "ends_with_eof": has_eof,
        "startxref_offset": xref_offset,
        "startxref_addresses_xref": valid_xref,
        "passes_structural_prechecks": bool(
            1 <= len(pdf_bytes) <= 10_485_760 and has_header and has_eof and valid_xref
        ),
    }


def check_markdown_links(repo_root: pathlib.Path, reader: SafeRepoReader, rel_paths: list[str]) -> list[dict]:
    results = []
    link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for rel in rel_paths:
        text = reader.read_text(rel)
        base_dir = (repo_root / rel).parent
        missing = []
        checked = 0
        for raw_target in link_re.findall(text):
            target = raw_target.strip()
            if target.startswith(("http://", "https://", "mailto:", "#", "conversation://", "file://")):
                continue
            path_part = target.split("#", 1)[0]
            if not path_part:
                continue
            checked += 1
            resolved = (base_dir / path_part).resolve()
            if not resolved.exists():
                missing.append(target)
        results.append({"file": rel, "local_links_checked": checked, "missing_targets": missing})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(pathlib.Path(__file__).resolve().parents[5]))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    repo_root = pathlib.Path(args.repo_root).resolve()
    reader = SafeRepoReader(repo_root)
    assertions: dict[str, bool] = {}

    head_sha = run_git(repo_root, "rev-parse", "HEAD").decode("ascii").strip()
    branch_name = run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD").decode("ascii").strip()

    # 1. Lineage & blob identity checks
    design_changed = git_changed_paths(repo_root, DESIGN_CANDIDATE)
    report_changed = git_changed_paths(repo_root, DISPATCH_REPORT_TIP)
    design_tree = git_tree(repo_root, DESIGN_CANDIDATE)
    dispatch_tree = git_tree(repo_root, DISPATCH_REPORT_TIP)
    base_tree = git_tree(repo_root, PACKET_BASE)
    f1_tree = git_tree(repo_root, F1_CANDIDATE)
    corpus_tree = git_tree(repo_root, CORPUS_CANDIDATE)
    q0_tree = git_tree(repo_root, Q0_CORE_CANDIDATE)

    design_parent = run_git(repo_root, "rev-parse", f"{DESIGN_CANDIDATE}^").decode("ascii").strip()
    dispatch_parent = run_git(repo_root, "rev-parse", f"{DISPATCH_REPORT_TIP}^").decode("ascii").strip()

    assertions["design_parent_equals_packet_base"] = design_parent == PACKET_BASE
    assertions["dispatch_parent_equals_design_candidate"] = dispatch_parent == DESIGN_CANDIDATE
    assertions["design_candidate_exact_8_paths"] = set(design_changed) == set(EXPECTED_DESIGN_BLOBS)
    assertions["design_candidate_exact_blobs"] = all(
        design_tree.get(k) == v for k, v in EXPECTED_DESIGN_BLOBS.items()
    )
    assertions["dispatch_report_exact_2_paths"] = set(report_changed) == set(EXPECTED_REPORT_BLOBS)
    assertions["dispatch_report_exact_blobs"] = all(
        dispatch_tree.get(k) == v for k, v in EXPECTED_REPORT_BLOBS.items()
    )

    # 2. Preservation of accepted F1, WP-0004 corpus, and WP-0005 Q0 core
    f1_prefixes = ("src/", "web/", "tests/", "deploy/", "workers/", "ELedgerCare.slnx", "Directory.", "global.json")
    f1_paths = {k: v for k, v in f1_tree.items() if k.startswith(f1_prefixes)}
    assertions["f1_product_preserved_at_dispatch"] = bool(f1_paths) and all(
        dispatch_tree.get(k) == v and base_tree.get(k) == v for k, v in f1_paths.items()
    )

    corpus_paths = {
        k: v
        for k, v in corpus_tree.items()
        if k.startswith("evaluation/synthetic/") or k == "evaluation/manifests/corpus-manifest.json"
    }
    assertions["wp0004_corpus_preserved_at_dispatch"] = len(corpus_paths) == 61 and all(
        dispatch_tree.get(k) == v for k, v in corpus_paths.items()
    )

    q0_core_paths = {
        k: v
        for k, v in q0_tree.items()
        if k.startswith("qualification/q0/harness/") and not k.startswith("qualification/q0/harness/evidence/")
    }
    assertions["wp0005_q0_core_preserved_at_dispatch"] = len(q0_core_paths) == 42 and all(
        dispatch_tree.get(k) == v for k, v in q0_core_paths.items()
    )

    # 3. F2 contract vs F1/Q0 actual source checks
    f2_doc = reader.read_text("docs/design/F2-local-extraction.md")
    f2_kickoff = reader.read_text("docs/kickoffs/WP-0006-eld-f2-implementer.md")
    grant_sql = reader.read_text("deploy/dev/database/grant-runtime.sql")
    pg_fixture = reader.read_text("tests/ELedgerCare.Acceptance.Tests/Harness/PostgresFixture.cs")
    prep_db = reader.read_text("deploy/dev/database/prepare-database.ps1")
    workers_ocr_readme = reader.read_text("workers/ocr/README.md")
    owned_api_ts = reader.read_text("web/e2e/owned-api.ts")

    pdf_checks = {
        "SYN-WO-01-v1-raster300": check_f1_pdf_structural_profile(
            reader.read_bytes("evaluation/synthetic/pdfs/F01/SYN-WO-01-v1-raster300.pdf")
        ),
        "SYN-MP-01-v0-clean": check_f1_pdf_structural_profile(
            reader.read_bytes("evaluation/synthetic/pdfs/F07/SYN-MP-01-v0-clean.pdf")
        ),
        "F1-SWO-001": check_f1_pdf_structural_profile(reader.read_bytes("tests/fixtures/F1-SWO-001.pdf")),
    }
    assertions["f2_target_dev_pdfs_pass_f1_structural_admission"] = all(
        v["passes_structural_prechecks"] for v in pdf_checks.values()
    )

    q0_protocol = reader.read_json("qualification/q0/harness/protocol.json")
    q0_lock = reader.read_json("qualification/q0/harness/locks/dependency-lock.json")
    q0_model_manifest = reader.read_json("qualification/q0/harness/manifests/model-files.json")
    uocr_src = reader.read_text("research/astra/sources/hf-modeling_unlimitedocr.py.txt")

    assertions["q0_pins_match_f2_contract"] = (
        q0_protocol["model"]["revision"] == "0480966938291445591f69f08a13b041c073a96a"
        and q0_model_manifest["runtime_object_count"] == 18
        and len(q0_model_manifest["notices"]) == 1
        and q0_lock["platform"]["python"] == "3.12.10"
        and q0_lock["expect"]["artifact_count"] == 32
        and q0_protocol["renderer"]["version"] == "5.15.2"
        and q0_protocol["renderer"]["pdfium_version"] == "159.0.8149.0"
        and "0480966938291445591f69f08a13b041c073a96a" in f2_doc
        and "torchvision-local-sha256-TOFU" in f2_doc
    )

    grant_sql_statements = "\n".join(
        line for line in grant_sql.splitlines() if not line.lstrip().startswith("--")
    )
    f2_observations = {
        "grant_sql_referenced_by_postgres_fixture_and_prepare_script": (
            '"deploy", "dev", "database", "grant-runtime.sql"' in pg_fixture and "grant-runtime.sql" in prep_db
        ),
        "grant_sql_currently_f1_select_insert_only": (
            "GRANT SELECT, INSERT ON TABLE" in grant_sql_statements
            and "UPDATE" not in grant_sql_statements
            and "DELETE" not in grant_sql_statements
        ),
        "f2_implementer_kickoff_omits_deploy_dev_and_workers_ocr": (
            "deploy/" not in f2_kickoff and "workers/ocr" not in f2_kickoff and "workers/local_ocr/" in f2_kickoff
        ),
        "legacy_workers_ocr_readme_claims_not_implemented": "not implemented" in workers_ocr_readme.lower(),
        "owned_api_ts_references_evaluation_product_smoke_and_5180": (
            "evaluation/product-smoke/run-browser-checks.ps1" in owned_api_ts and "5180" in owned_api_ts
        ),
        "q0_dependency_lock_uses_git_blob_indirection": (
            "artifacts" not in q0_lock and q0_lock["source"]["git_blob"] == "ec8c650ed5fbeb0a754e4daee53aad53753a57a3"
        ),
        "native_infer_multi_returns_2_tuple_only": "return res['text'], len(res['token_ids'])" in uocr_src,
        "q0_protocol_timeouts_omit_call_pages_2": (
            "call_pages_1" in q0_protocol["guards"]["timeouts_s"]
            and "call_pages_3" in q0_protocol["guards"]["timeouts_s"]
            and "call_pages_2" not in q0_protocol["guards"]["timeouts_s"]
        ),
    }

    # 4. B0 contract vs corpus manifest, Q0 timings, and DEV-only expected/source records
    b0_doc = reader.read_text("docs/design/B0-vanilla-accuracy-baseline.md")
    manifest = reader.read_json("evaluation/manifests/corpus-manifest.json")
    run_comp = reader.read_json("docs/coordination/WP-0005/final-runtime-observations/run-comparison.json")

    dev_fx = [f for f in manifest["fixtures"] if f["split"] == "dev"]
    holdout_fx = [f for f in manifest["fixtures"] if f["split"] == "eval_holdout"]
    page_counts = sorted({f["page_count"] for f in manifest["fixtures"]})

    assertions["b0_manifest_counts_match_contract"] = (
        len(manifest["fixtures"]) == 26
        and sum(f["page_count"] for f in manifest["fixtures"]) == 40
        and len(dev_fx) == 13
        and sum(f["page_count"] for f in dev_fx) == 19
        and {f["family_id"] for f in dev_fx} == DEV_FAMILIES
        and len(holdout_fx) == 13
        and sum(f["page_count"] for f in holdout_fx) == 21
        and {f["family_id"] for f in holdout_fx} == HOLDOUT_FAMILIES
        and page_counts == [1, 3]
        and "29b2000265ae6068d9c86818622c81a40cadd961" in b0_doc
    )

    warm_1p_max = max(
        c["seconds"]
        for r in run_comp["runs"].values()
        for c in r["calls"]
        if c["input_pages"] == 1 and not c["label"].endswith("warmup")
    )
    warm_3p_max = max(
        c["seconds"]
        for r in run_comp["runs"].values()
        for c in r["calls"]
        if c["input_pages"] == 3 and not c["label"].endswith("warmup")
    )
    projected_26doc_plus_2warmup_s = 19 * warm_1p_max + 7 * warm_3p_max + 150.0 + 290.0 + 20.0
    assertions["b0_projected_runtime_within_6h_session_cap"] = projected_26doc_plus_2warmup_s < 21600.0

    # Inspect all 13 DEV expected records and all 4 DEV source records (strictly 0 holdout files)
    dev_value_types: set[str] = set()
    printed_ne_norm_types: set[str] = set()
    labels_by_field_id: dict[str, set[str]] = {}
    has_top_level_doc_text = False
    multiline_comma_joined_addresses = 0

    for fx in dev_fx:
        exp = reader.read_json(fx["expected_ground_truth_path"])
        if "document_text" in exp or "reading_order_text" in exp:
            has_top_level_doc_text = True
        for fld in exp["expected_fields"]:
            vt = fld["value_type"]
            dev_value_types.add(vt)
            if fld["printed_text"] != fld["normalized_value"]:
                printed_ne_norm_types.add(vt)
            labels_by_field_id.setdefault(fld["field_id"], set()).add(fld["label_printed"])
            if fld["field_id"].startswith("address_") and ", " in fld["printed_text"]:
                multiline_comma_joined_addresses += 1
        for tbl in exp["expected_tables"]:
            for row in tbl["rows"]:
                for cell in row["cells"].values():
                    vt = cell["value_type"]
                    dev_value_types.add(vt)
                    if cell["printed_text"] != cell["normalized_value"]:
                        printed_ne_norm_types.add(vt)

    dev_source_summaries = {}
    for src_rec in manifest["source_records"]:
        if src_rec["split"] == "dev":
            src = reader.read_json(src_rec["source_path"])
            dev_source_summaries[src_rec["family_id"]] = {
                "doc_kind": src["doc_kind"],
                "has_banner": "banner" in src,
                "has_remittance_note": "remittance_note" in src,
            }

    q0_f07_raw = reader.read_text(
        "qualification/q0/harness/evidence/004-gpu-trial/9e73ef86/run-20261115T202627Z-eb5bf7da/evidence/F07.warm1.raw.txt"
    )
    varying_dev_labels = {k: sorted(v) for k, v in sorted(labels_by_field_id.items()) if len(v) > 1}

    b0_observations = {
        "dev_expected_files_inspected": len(dev_fx),
        "dev_source_files_inspected": len(dev_source_summaries),
        "holdout_files_opened": 0,
        "expected_json_has_top_level_document_text": has_top_level_doc_text,
        "dev_value_types": sorted(dev_value_types),
        "value_types_where_printed_differs_from_normalized": sorted(printed_ne_norm_types),
        "multiline_comma_joined_address_field_instances_in_dev": multiline_comma_joined_addresses,
        "field_ids_with_varying_printed_labels_across_dev_families": varying_dev_labels,
        "q0_f07_raw_contains_html_amp_and_colspan_and_merged_summary": (
            "&amp;" in q0_f07_raw and 'colspan="9"' in q0_f07_raw and "$562.19Sales Tax" in q0_f07_raw
        ),
        "projected_26doc_single_session_s": round(projected_26doc_plus_2warmup_s, 2),
    }

    # 5. Link checks
    md_to_check = [
        "CURRENT.md",
        "docs/design/F2-local-extraction.md",
        "docs/design/B0-vanilla-accuracy-baseline.md",
        "docs/kickoffs/WP-0006-eld-f2-implementer.md",
        "docs/kickoffs/WP-0007-eld-rd-astra.md",
        "docs/kickoffs/WP-0006-0007-eld-next-reviewer.md",
        "docs/agent-reports/eld-coordinator/WP-0006/001_2026-11-16_design_eld-coordinator.md",
        "docs/agent-reports/eld-coordinator/WP-0007/001_2026-11-16_design_eld-coordinator.md",
    ]
    review_readme = "docs/reviews/WP-0006/eld-next-reviewer/design/README.md"
    if (repo_root / review_readme).is_file():
        md_to_check.append(review_readme)
    link_checks = check_markdown_links(repo_root, reader, md_to_check)
    assertions["all_local_markdown_links_resolve"] = all(not item["missing_targets"] for item in link_checks)

    # Confirm zero holdout path was opened
    assertions["zero_holdout_paths_opened"] = not any(
        any(fam in p for fam in ("/F03/", "/F05/", "/F06/", "/F08/", "F03_", "F05_", "F06_", "F08_", *HOLDOUT_PREFIXES))
        for p in reader.opened_paths
    )

    helper_bytes = pathlib.Path(__file__).read_bytes()
    payload = {
        "schema": "eld-phase1-design-review-verification/1",
        "observed_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch": branch_name,
        "executing_head": head_sha,
        "reviewed_revisions": {
            "packet_base": PACKET_BASE,
            "design_candidate": DESIGN_CANDIDATE,
            "dispatch_report_tip": DISPATCH_REPORT_TIP,
            "accepted_f1_candidate": F1_CANDIDATE,
            "accepted_corpus_candidate": CORPUS_CANDIDATE,
            "accepted_q0_core_candidate": Q0_CORE_CANDIDATE,
        },
        "helper_path": "docs/reviews/WP-0006/eld-next-reviewer/design/verify_design_contracts.py",
        "helper_sha256": hashlib.sha256(helper_bytes).hexdigest(),
        "assertions": assertions,
        "all_assertions_passed": all(assertions.values()),
        "f2_pdf_admission_prechecks": pdf_checks,
        "f2_source_observations": f2_observations,
        "b0_source_observations": b0_observations,
        "markdown_link_checks": link_checks,
        "opened_repository_paths": reader.opened_paths,
    }

    out_path = pathlib.Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes((json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return 0 if payload["all_assertions_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
