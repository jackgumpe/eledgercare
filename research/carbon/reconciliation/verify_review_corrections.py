#!/usr/bin/env python3
"""CPU-only specification, input-path, and Git-invariance diagnostic for WP-0004 / 008.

Scope & Attribution Disclosure:
- Author-owned diagnostic helper (`eld-rd-carbon`), NOT a production extractor, NOT OCR inference,
  and NOT a completed E2 benchmark experiment (zero model weights, zero GPU, zero quality claims).
- Exercises ONLY `dev` families `F01, F02, F04, F07` page 1 (`v1-raster300` and `v2-skew`; 8 pages total;
  zero `eval_holdout` fixtures are read).
- Attributes the positive/negative skew residual diagnostic structure to `eld-rd-reviewer`'s independent
  review helper `1787e942412f7a6981c7a6d730c44a83034ad0ef:docs/reviews/WP-0004/eld-rd-reviewer/helpers/e2_sign_diagnostic.py`
  without importing or modifying any reviewer file, and executes on the newly frozen `pypdfium2==5.15.2`
  (`PDFium 159.0.8149.0`, `scale = 300.0 / 72.0`) RGB input contract (`RV-01` + `RV-02`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone

import pypdfium2 as pdfium
from PIL import Image
from pypdf import PdfReader, __version__ as PYPDF_VERSION

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
BASE_SHA = "068f3f83bb532160b56e00f071f8badd8d3f51b0"
CORPUS_CANDIDATE_SHA = "29b2000265ae6068d9c86818622c81a40cadd961"
REVIEW_DELIVERABLE_SHA = "1787e942412f7a6981c7a6d730c44a83034ad0ef"
REVIEW_REPORT_SHA = "8f9a3281fa223d25447677b8ed8b873bf9e5cd01"
COORD_INITIAL_RELEASE_SHA = "d216bdcd9aa65632ed1556899fda191c56cc2800"
COORD_AMENDED_RELEASE_SHA = "7a21fdbb154f735656bbfc7602ad84e8d05b17ab"

CANDIDATE_GRID_CCW_DEG = [round((k - 50) / 10.0, 1) for k in range(101)]  # -5.0 .. +5.0 step 0.1
DEV_CASES = [
    ("F01", "SYN-WO-01", 4.0),
    ("F02", "SYN-WO-02", -3.0),
    ("F04", "SYN-INV-01", -3.0),
    ("F07", "SYN-MP-01", 4.0),
]
ALLOWED_CANDIDATE_PATHS = [
    "evaluation/README.md",
    "research/carbon/reconciliation/02-ranked-experiment-backlog.md",
    "research/carbon/reconciliation/03-review-response.md",
    "research/carbon/reconciliation/verify_review_corrections.py",
]
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def otsu_foreground_mask(rgb: Image.Image) -> tuple[Image.Image, int]:
    """Compute binary foreground mask M in {0, 1} (`1` iff gray <= T_otsu) from 24-bit RGB buffer."""
    gray = rgb.convert("L")
    hist = gray.histogram()
    total = sum(hist)
    sum_all = sum(i * h for i, h in enumerate(hist))
    w_b = 0
    sum_b = 0
    best_var = -1.0
    threshold = 0
    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * hist[t]
        mean_b = sum_b / w_b
        mean_f = (sum_all - sum_b) / w_f
        between = w_b * w_f * (mean_b - mean_f) ** 2
        if between > best_var:
            best_var = between
            threshold = t
    lut = [1 if v <= threshold else 0 for v in range(256)]
    return gray.point(lut, mode="L"), threshold


def row_projection_variance_leveling(mask_01: Image.Image, hypothesized_ccw_skew_deg: float) -> float:
    """Compute V(theta) on M_theta = M.rotate(-theta, NEAREST, expand=True, fillcolor=0)."""
    m_theta = mask_01.rotate(
        -hypothesized_ccw_skew_deg,
        resample=Image.Resampling.NEAREST,
        expand=True,
        fillcolor=0,
    )
    w, h = m_theta.size
    raw = m_theta.tobytes()
    row_sums = [raw[y * w : (y + 1) * w].count(1) for y in range(h)]
    mu = sum(row_sums) / h
    return sum((s - mu) ** 2 for s in row_sums) / h


def run_frozen_e2_gate(input_rgb: Image.Image) -> tuple[Image.Image, dict[str, object]]:
    """Estimate CCW skew and conditionally deskew `input_rgb` WITHOUT access to ground-truth angle."""
    mask_01, otsu_t = otsu_foreground_mask(input_rgb)
    scores = {theta: row_projection_variance_leveling(mask_01, theta) for theta in CANDIDATE_GRID_CCW_DEG}
    max_score = max(scores.values())
    tied = [theta for theta, sc in scores.items() if sc == max_score]
    theta_hat = sorted(tied, key=lambda theta: (abs(theta), -theta))[0]
    v_zero = scores[0.0]
    gain_ratio = scores[theta_hat] / v_zero
    triggered = (abs(theta_hat) >= 1.0) and (scores[theta_hat] >= 1.10 * v_zero)

    if not triggered:
        applied_ccw_deg = 0.0
        output_rgb = input_rgb
    else:
        applied_ccw_deg = round(-theta_hat, 4)
        output_rgb = input_rgb.rotate(
            applied_ccw_deg,
            resample=Image.Resampling.BILINEAR,
            expand=True,
            fillcolor=(255, 255, 255),
        )

    return output_rgb, {
        "otsu_threshold": otsu_t,
        "theta_hat_ccw_deg": theta_hat,
        "v_theta_hat_over_v_zero": round(gain_ratio, 4),
        "triggered": triggered,
        "applied_ccw_deg": applied_ccw_deg,
    }


def measure_empirical_residual_ccw_deg(rgb: Image.Image) -> float:
    """Re-estimate remaining CCW skew over [-10.0, +10.0] step 0.1 on half-scale mask."""
    mask_01, _ = otsu_foreground_mask(rgb)
    small = mask_01.resize((mask_01.width // 2, mask_01.height // 2), Image.Resampling.NEAREST)
    wide_grid = [round((k - 100) / 10.0, 1) for k in range(201)]
    scores = {theta: row_projection_variance_leveling(small, theta) for theta in wide_grid}
    max_score = max(scores.values())
    tied = [theta for theta, sc in scores.items() if sc == max_score]
    return sorted(tied, key=lambda theta: (abs(theta), -theta))[0]


def render_frozen_pdfium_rgb(pdf_path: pathlib.Path, page_index: int = 0) -> Image.Image:
    """Frozen VLM / E2 PDF-to-RGB input contract: pypdfium2 5.15.2 at scale = 300.0 / 72.0."""
    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        page = doc[page_index]
        try:
            bitmap = page.render(scale=300.0 / 72.0)
            return bitmap.to_pil().convert("RGB")
        finally:
            page.close()
    finally:
        doc.close()


def extract_stored_xobject_info(pdf_path: pathlib.Path, page_index: int = 0) -> tuple[list[float], list[int], bytes]:
    reader = PdfReader(str(pdf_path))
    pg = reader.pages[page_index]
    mediabox = [round(float(x), 2) for x in pg.mediabox]
    xobjs = pg["/Resources"]["/XObject"].get_object()
    assert len(xobjs) == 1
    im_obj = next(iter(xobjs.values())).get_object()
    w_px = int(im_obj["/Width"])
    h_px = int(im_obj["/Height"])
    raw_rgb = im_obj.get_data()
    assert len(raw_rgb) == w_px * h_px * 3
    return mediabox, [w_px, h_px], raw_rgb


def run_dev_e2_and_doc_checks(repo_root: pathlib.Path) -> dict[str, object]:
    results: list[dict[str, object]] = []
    for fam, prefix, skew_deg in DEV_CASES:
        assert fam in {"F01", "F02", "F04", "F07"}, "Diagnostic restricted strictly to dev families"
        skew_tag = ("pos" if skew_deg > 0 else "neg") + f"{int(abs(skew_deg))}deg"
        variants = [
            ("v1_raster300", f"{prefix}-v1-raster300.pdf", 0.0),
            ("v2_skew", f"{prefix}-v2-skew-{skew_tag}.pdf", skew_deg),
        ]
        for variant_kind, pdf_name, known_test_skew_ccw in variants:
            pdf_path = repo_root / "evaluation" / "synthetic" / "pdfs" / fam / pdf_name
            mediabox_pt, stored_px, stored_rgb_bytes = extract_stored_xobject_info(pdf_path, 0)
            input_rgb = render_frozen_pdfium_rgb(pdf_path, 0)
            in_bytes = input_rgb.tobytes()

            # Run E2 gate blindly on rendered input_rgb without passing known_test_skew_ccw
            output_rgb, est = run_frozen_e2_gate(input_rgb)
            out_bytes = output_rgb.tobytes()

            theta_hat = float(est["theta_hat_ccw_deg"])
            applied = float(est["applied_ccw_deg"])
            triggered = bool(est["triggered"])
            est_abs_err = round(abs(theta_hat - known_test_skew_ccw), 4)
            analytic_res = round(known_test_skew_ccw + applied, 4)
            emp_res = 0.0 if not triggered else measure_empirical_residual_ccw_deg(output_rgb)
            rendered_matches_stored = (list(input_rgb.size) == stored_px) and (in_bytes == stored_rgb_bytes)

            if variant_kind == "v1_raster300":
                assert list(input_rgb.size) == [2550, 3301]
                assert rendered_matches_stored is True
                assert triggered is False and theta_hat == 0.0 and applied == 0.0
                assert out_bytes == in_bytes
            else:
                assert rendered_matches_stored is False  # PDFium resamples all v2-skew pages (RV-02)
                if known_test_skew_ccw == 4.0:
                    assert stored_px == [2776, 3471] and list(input_rgb.size) == [2776, 3471]
                else:
                    assert stored_px == [2720, 3431] and list(input_rgb.size) == [2720, 3432]
                assert triggered is True
                assert est_abs_err == 0.0
                assert analytic_res == 0.0
                assert abs(emp_res) <= 0.1

            results.append(
                {
                    "family_id": fam,
                    "fixture_page": f"{pdf_name}#p1",
                    "variant_kind": variant_kind,
                    "mediabox_pt": mediabox_pt,
                    "stored_xobject_px": stored_px,
                    "stored_xobject_rgb_sha256": sha256_bytes(stored_rgb_bytes),
                    "rendered_pdfium_300dpi_px": list(input_rgb.size),
                    "rendered_input_rgb_sha256": sha256_bytes(in_bytes),
                    "rendered_vs_stored_xobject_pixel_exact": rendered_matches_stored,
                    "known_test_ccw_skew_deg_checked_after_estimation": known_test_skew_ccw,
                    "otsu_threshold": est["otsu_threshold"],
                    "theta_hat_ccw_deg": theta_hat,
                    "v_theta_hat_over_v_zero": est["v_theta_hat_over_v_zero"],
                    "triggered": triggered,
                    "applied_ccw_deg": applied,
                    "output_px": list(output_rgb.size),
                    "output_rgb_sha256": sha256_bytes(out_bytes),
                    "byte_identical_noop": (out_bytes == in_bytes),
                    "estimation_abs_error_deg": est_abs_err,
                    "analytic_residual_ccw_deg": analytic_res,
                    "empirical_residual_ccw_deg": emp_res,
                }
            )

    # Verify RV-03 README & hybrid area alignment + relative Markdown links
    readme_text = (repo_root / "evaluation" / "README.md").read_text(encoding="utf-8")
    assert "2550 x 3301" in readme_text and "2550 x 3300" not in readme_text
    assert "2.847%" in readme_text and "2.989%" in readme_text

    f02_area_pct = round((300 * 46) / (612 * 792) * 100.0, 3)
    f08_area_pct = round((315 * 46) / (612 * 792) * 100.0, 3)
    assert f02_area_pct == 2.847 and f08_area_pct == 2.989

    # Verify pypdfium2 render bitmap-sizing arithmetic (math.ceil(c_float_extent * binary64_scale))
    scale_f64 = 300.0 / 72.0
    assert repr(scale_f64) == "4.166666666666667"
    assert repr(792.0 * scale_f64) == "3300.0000000000005" and math.ceil(792.0 * scale_f64) == 3301
    sizing_checks: dict[str, dict[str, object]] = {}
    for label, rel_pdf, expected_ceil_h in [
        ("v0_clean_792pt", "evaluation/synthetic/pdfs/F01/SYN-WO-01-v0-clean.pdf", 3301),
        ("v1_raster_792_24pt", "evaluation/synthetic/pdfs/F01/SYN-WO-01-v1-raster300.pdf", 3301),
        ("v2_pos4_833_04pt", "evaluation/synthetic/pdfs/F01/SYN-WO-01-v2-skew-pos4deg.pdf", 3471),
        ("v2_neg3_823_44pt", "evaluation/synthetic/pdfs/F02/SYN-WO-02-v2-skew-neg3deg.pdf", 3432),
    ]:
        d_sz = pdfium.PdfDocument(str(repo_root / rel_pdf))
        try:
            pg_sz = d_sz[0]
            try:
                h_cfloat = pg_sz.get_height()
                prod = h_cfloat * scale_f64
                ceil_h = math.ceil(prod)
                assert ceil_h == expected_ceil_h
                sizing_checks[label] = {
                    "get_height_c_float_repr": repr(h_cfloat),
                    "product_with_binary64_scale_repr": repr(prod),
                    "math_ceil_height_px": ceil_h,
                }
            finally:
                pg_sz.close()
        finally:
            d_sz.close()

    md_targets = [
        repo_root / "evaluation" / "README.md",
        repo_root / "research" / "carbon" / "reconciliation" / "README.md",
        repo_root / "research" / "carbon" / "reconciliation" / "01-exchange-disposition.md",
        repo_root / "research" / "carbon" / "reconciliation" / "02-ranked-experiment-backlog.md",
        repo_root / "research" / "carbon" / "reconciliation" / "03-review-response.md",
    ]
    links_checked = 0
    for md in md_targets:
        raw = md.read_bytes()
        assert b"\r\n" not in raw, f"CRLF detected in {md}"
        txt = raw.decode("utf-8")
        assert "float32" not in txt, f"Imprecise float32 wording found in {md}"
        for match in LINK_RE.finditer(txt):
            href = match.group(2)
            if href.startswith(("http://", "https://", "#")):
                continue
            target_file = (md.parent / href.split("#")[0]).resolve()
            assert target_file.exists(), f"Broken link in {md}: {href} -> {target_file}"
            links_checked += 1

    return {
        "input_contract": "pypdfium2==5.15.2 (PDFium 159.0.8149.0) page.render(scale=300.0/72.0).to_pil().convert('RGB')",
        "dev_pages_tested": len(results),
        "eval_holdout_pages_read": 0,
        "clean_v1_byte_identical_noops": sum(1 for r in results if r["variant_kind"] == "v1_raster300" and r["byte_identical_noop"]),
        "skew_v2_exact_zero_residuals": sum(
            1 for r in results if r["variant_kind"] == "v2_skew" and r["analytic_residual_ccw_deg"] == 0.0 and abs(float(r["empirical_residual_ccw_deg"])) <= 0.1
        ),
        "pypdfium2_ceil_sizing_verification": sizing_checks,
        "hybrid_stamp_page_area_pct": {
            "SYN-WO-02-v3-hybrid-note_F02_p1": f02_area_pct,
            "SYN-MP-02-v3-hybrid-stamp_F08_p3": f08_area_pct,
        },
        "markdown_relative_links_verified": links_checked,
        "dev_e2_diagnostic_results": results,
    }


def run_git(repo_root: pathlib.Path, args: list[str]) -> str:
    return subprocess.run(["git", *args], cwd=repo_root, text=True, capture_output=True, check=True).stdout.strip()


def parse_tree(repo_root: pathlib.Path, rev: str) -> dict[str, tuple[str, str]]:
    out = run_git(repo_root, ["ls-tree", "-r", rev])
    res: dict[str, tuple[str, str]] = {}
    for line in out.splitlines():
        meta, path = line.split("\t", 1)
        mode, _, oid = meta.split()
        res[path] = (mode, oid)
    return res


def get_software_versions() -> dict[str, str]:
    return {
        "python": sys.version.split()[0],
        "pypdfium2": str(pdfium.PYPDFIUM_INFO.version),
        "pdfium_native": str(pdfium.PDFIUM_INFO),
        "pillow": str(Image.__version__),
        "pypdf": str(PYPDF_VERSION),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify WP-0004/008 RV-01..04 corrections on dev controls.")
    parser.add_argument("--write-manifest", type=pathlib.Path, default=None, help="Write frozen-candidate verification JSON.")
    args = parser.parse_args()

    sw_versions = get_software_versions()
    diag = run_dev_e2_and_doc_checks(REPO_ROOT)

    if args.write_manifest is None:
        tree_base_pre = parse_tree(REPO_ROOT, BASE_SHA)
        tree_corpus_pre = parse_tree(REPO_ROOT, CORPUS_CANDIDATE_SHA)
        assert sum(1 for p in tree_base_pre if p.startswith("evaluation/synthetic/pdfs/") and tree_base_pre[p] == tree_corpus_pre[p]) == 26
        assert sum(1 for p in tree_base_pre if p.startswith("evaluation/synthetic/sources/") and tree_base_pre[p] == tree_corpus_pre[p]) == 8
        assert sum(1 for p in tree_base_pre if p.startswith("evaluation/synthetic/expected/") and tree_base_pre[p] == tree_corpus_pre[p]) == 26
        assert sum(1 for p in tree_base_pre if p.startswith("evaluation/generation/") and tree_base_pre[p] == tree_corpus_pre[p]) == 4
        assert sum(1 for p in tree_base_pre if p.startswith("evaluation/manifests/")) == 5
        assert sum(1 for p in tree_base_pre if p.startswith("docs/agent-reports/eld-rd-carbon/")) == 3
        print(
            json.dumps(
                {
                    "status": "DEV_DIAGNOSTIC_PASS",
                    "software_versions": sw_versions,
                    "dev_pages_tested": diag["dev_pages_tested"],
                    "clean_v1_byte_identical_noops": diag["clean_v1_byte_identical_noops"],
                    "skew_v2_exact_zero_residuals": diag["skew_v2_exact_zero_residuals"],
                    "markdown_relative_links_verified": diag["markdown_relative_links_verified"],
                }
            )
        )
        return 0

    # Decisive frozen-candidate mode: require clean working tree at frozen candidate commit
    assert run_git(REPO_ROOT, ["status", "--porcelain"]) == "", "Working tree must be clean at frozen candidate"
    cand_sha = run_git(REPO_ROOT, ["rev-parse", "HEAD"])
    parent_sha = run_git(REPO_ROOT, ["rev-parse", "HEAD^"])
    branch = run_git(REPO_ROOT, ["branch", "--show-current"])
    assert branch == "research/wp-0004-carbon-recovery"
    assert parent_sha == BASE_SHA, f"Expected parent {BASE_SHA}, got {parent_sha}"

    diff_lines = run_git(REPO_ROOT, ["diff", "--name-status", f"{BASE_SHA}..{cand_sha}"]).splitlines()
    changed_paths = sorted(ln.split("\t", 1)[1] for ln in diff_lines)
    assert changed_paths == ALLOWED_CANDIDATE_PATHS, f"Unexpected candidate paths: {changed_paths}"

    tree_base = parse_tree(REPO_ROOT, BASE_SHA)
    tree_corpus = parse_tree(REPO_ROOT, CORPUS_CANDIDATE_SHA)
    tree_cand = parse_tree(REPO_ROOT, cand_sha)

    unchanged_from_base = [p for p in tree_base if p not in set(ALLOWED_CANDIDATE_PATHS)]
    assert len(unchanged_from_base) == len(tree_base) - 2  # 2 modified, 2 newly added in candidate
    for p in unchanged_from_base:
        assert tree_cand[p] == tree_base[p], f"Unexpected blob change on {p}"

    candidate_inventory = []
    for ln in sorted(diff_lines, key=lambda s: s.split("\t", 1)[1]):
        st_code, rel_p = ln.split("\t", 1)
        fb = (REPO_ROOT / rel_p).read_bytes()
        assert b"\r\n" not in fb, f"CRLF in candidate file {rel_p}"
        candidate_inventory.append(
            {
                "status": st_code,
                "path": rel_p,
                "size_bytes": len(fb),
                "sha256": sha256_bytes(fb),
                "git_blob_oid": tree_cand[rel_p][1],
            }
        )

    receipt = {
        "schema_version": "1.0.0",
        "packet": "WP-0004 / 008",
        "recorded_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "author_id": "eld-rd-carbon",
        "session_id": "993d4f08-72d0-479c-9e6c-047280cedf95",
        "prior_stalled_session_id": "74513d00-ee88-4e85-a554-120908615b21",
        "independence_status": "author_correction_only_ready_for_review (not self-acceptance; uninvolved Opus eld-rd-reviewer /009 closure follows)",
        "revisions": {
            "coordinator_initial_release_sha": COORD_INITIAL_RELEASE_SHA,
            "coordinator_amended_release_sha": COORD_AMENDED_RELEASE_SHA,
            "execution_base_and_007_report_sha": BASE_SHA,
            "unchanged_corpus_candidate_sha": CORPUS_CANDIDATE_SHA,
            "addressed_opus_005_deliverable_sha": REVIEW_DELIVERABLE_SHA,
            "addressed_opus_005_report_sha": REVIEW_REPORT_SHA,
            "frozen_008_candidate_sha": cand_sha,
            "owned_branch": branch,
        },
        "software_versions": sw_versions,
        "candidate_changed_files": candidate_inventory,
        "git_object_invariance_checks": {
            "base_tracked_files_total": len(tree_base),
            "candidate_tracked_files_total": len(tree_cand),
            "unchanged_base_files_verified_identical_mode_and_blob": len(unchanged_from_base),
            "corpus_pdfs_identical_to_29b2000": sum(
                1 for p in tree_cand if p.startswith("evaluation/synthetic/pdfs/") and tree_cand[p] == tree_corpus[p]
            ),
            "corpus_sources_identical_to_29b2000": sum(
                1 for p in tree_cand if p.startswith("evaluation/synthetic/sources/") and tree_cand[p] == tree_corpus[p]
            ),
            "corpus_expected_identical_to_29b2000": sum(
                1 for p in tree_cand if p.startswith("evaluation/synthetic/expected/") and tree_cand[p] == tree_corpus[p]
            ),
            "generation_scripts_identical_to_29b2000": sum(
                1 for p in tree_cand if p.startswith("evaluation/generation/") and tree_cand[p] == tree_corpus[p]
            ),
            "existing_manifests_and_prior_evidence_identical_to_068f3f8": sum(
                1 for p in tree_base if p.startswith("evaluation/manifests/") and tree_cand[p] == tree_base[p]
            ),
            "historical_carbon_reports_identical_to_068f3f8": sum(
                1 for p in tree_base if p.startswith("docs/agent-reports/eld-rd-carbon/") and tree_cand[p] == tree_base[p]
            ),
        },
        "attributed_unchanged_opus_005_corpus_checks": {
            "note": "40/40 page visual inspection, 3,756+ independent arithmetic assertions, and two-run 53/53 deterministic regeneration were independently verified by eld-rd-reviewer in WP-0004 / 005 on 29b2000265ae6068d9c86818622c81a40cadd961 and were not repeated because all corpus/source/expected/generator blobs are 100% unchanged.",
            "reviewer_evidence_sha": REVIEW_DELIVERABLE_SHA,
            "reviewer_report_sha": REVIEW_REPORT_SHA,
        },
        "executed_dev_diagnostic": diag,
    }
    assert receipt["git_object_invariance_checks"]["corpus_pdfs_identical_to_29b2000"] == 26
    assert receipt["git_object_invariance_checks"]["corpus_sources_identical_to_29b2000"] == 8
    assert receipt["git_object_invariance_checks"]["corpus_expected_identical_to_29b2000"] == 26
    assert receipt["git_object_invariance_checks"]["generation_scripts_identical_to_29b2000"] == 4
    assert receipt["git_object_invariance_checks"]["existing_manifests_and_prior_evidence_identical_to_068f3f8"] == 5
    assert receipt["git_object_invariance_checks"]["historical_carbon_reports_identical_to_068f3f8"] == 3

    out_bytes = (json.dumps(receipt, indent=2) + "\n").encode("utf-8")
    assert b"\r\n" not in out_bytes
    args.write_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.write_manifest.write_bytes(out_bytes)
    print(f"DECISIVE_008_VERIFICATION_PASS: candidate={cand_sha} evidence={args.write_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
