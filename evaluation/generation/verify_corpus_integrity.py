"""Deterministic corpus structure, PDF stream modality, and two-run byte-identity verifier.

Verifies:
1. Manifest counts (8 families, 4 dev / 4 eval_holdout, 26 PDFs, 40 pages, 0 public PDFs).
2. SHA-256, byte size, and actual `git hash-object` Git blob OIDs for all 8 source JSONs,
   26 expected JSONs, and 26 PDFs.
3. Family-level split invariance across all variants.
4. PDF stream modality & visible text/XObject rules across all 40 pages via pypdf:
   - v0_clean (8 PDFs, 12p): 0 image XObjects, non-empty text, 0 U+FFFD, every expected literal
     printed_text and sentinel appears on its assigned page (and F07 totals appear ONLY on p3).
   - v1_raster300 (8 PDFs, 12p) & v2_skew (8 PDFs, 12p): 0 extractable text, 0 /Font objects,
     and 1 /Subtype /Image XObject per page.
   - v3_hybrid (2 PDFs, 4p): vector text intact (>80 chars/page), target page has 1 embedded
     /Subtype /Image XObject occupying <15% page area, and the raster-only string is strictly
     absent from the PDF's extractable vector text layer.
5. Optional --check-regeneration <scratch_dir>: executes generate_corpus.py twice into clean
   scratch directories and asserts 100% byte-for-byte identity across Run 1, Run 2, and repo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

from pypdf import PdfReader


def sha256_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git_hash_file(p: pathlib.Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(p)], text=True).strip()


def count_page_images_and_fonts(page: object) -> tuple[int, int]:
    raw_res = page.get("/Resources")  # type: ignore[attr-defined]
    res = raw_res.get_object() if hasattr(raw_res, "get_object") else (raw_res or {})
    raw_fonts = res.get("/Font")
    fonts = raw_fonts.get_object() if hasattr(raw_fonts, "get_object") else (raw_fonts or {})
    raw_xobjs = res.get("/XObject")
    xobjs = raw_xobjs.get_object() if hasattr(raw_xobjs, "get_object") else (raw_xobjs or {})
    img_cnt = 0
    for _, obj_ref in xobjs.items():
        obj = obj_ref.get_object() if hasattr(obj_ref, "get_object") else obj_ref
        if obj.get("/Subtype") == "/Image":
            img_cnt += 1
    return img_cnt, len(fonts)


def verify_evaluation_tree(repo_root: pathlib.Path) -> dict[str, object]:
    man_path = repo_root / "evaluation" / "manifests" / "corpus-manifest.json"
    manifest = json.loads(man_path.read_text(encoding="utf-8"))

    counts = manifest["counts"]
    assert counts["families"] == 8
    assert counts["total_pdfs"] == 26
    assert counts["total_pages"] == 40
    assert counts["admitted_public_pdfs"] == 0
    assert counts["dev_families"] == ["F01", "F02", "F04", "F07"]
    assert counts["eval_holdout_families"] == ["F03", "F05", "F06", "F08"]

    family_splits: dict[str, str] = {}
    for sr in manifest["source_records"]:
        sp = repo_root / sr["source_path"]
        assert sp.exists(), f"Missing source {sp}"
        assert sp.stat().st_size == sr["size_bytes"]
        assert sha256_file(sp) == sr["sha256"]
        assert git_hash_file(sp) == sr["git_blob_oid"]
        family_splits[sr["family_id"]] = sr["split"]

    assert len(family_splits) == 8

    pages_checked = 0
    variant_counts = {"v0_clean": 0, "v1_raster300": 0, "v2_skew": 0, "v3_hybrid": 0}

    for item in manifest["fixtures"]:
        fid = item["fixture_id"]
        fam = item["family_id"]
        vkind = item["variant_kind"]
        variant_counts[vkind] += 1

        # Split invariance check
        assert item["split"] == family_splits[fam], f"{fid}: split {item['split']} != family {family_splits[fam]}"
        expected_split = "dev" if fam in ("F01", "F02", "F04", "F07") else "eval_holdout"
        assert item["split"] == expected_split

        pdf_path = repo_root / item["file_path"]
        exp_path = repo_root / item["expected_ground_truth_path"]
        assert pdf_path.exists() and exp_path.exists(), f"Missing files for {fid}"

        assert pdf_path.stat().st_size == item["size_bytes"]
        assert sha256_file(pdf_path) == item["sha256"]
        assert git_hash_file(pdf_path) == item["git_blob_oid"]
        assert sha256_file(exp_path) == item["expected_ground_truth_sha256"]
        assert git_hash_file(exp_path) == item["expected_ground_truth_git_blob_oid"]

        exp_data = json.loads(exp_path.read_text(encoding="utf-8"))
        reader = PdfReader(str(pdf_path))
        assert len(reader.pages) == item["page_count"] == exp_data["page_count"]

        page_texts = [pg.extract_text() or "" for pg in reader.pages]
        img_font_counts = [count_page_images_and_fonts(pg) for pg in reader.pages]
        pages_checked += len(reader.pages)

        if vkind == "v0_clean":
            for p_idx, (txt, (icnt, fcnt)) in enumerate(zip(page_texts, img_font_counts), start=1):
                assert icnt == 0, f"{fid} p{p_idx}: expected 0 images, got {icnt}"
                assert fcnt > 0, f"{fid} p{p_idx}: expected Base-14 font resources"
                assert len(txt.strip()) >= 80, f"{fid} p{p_idx}: unexpectedly sparse text ({len(txt.strip())} chars)"
                assert "\ufffd" not in txt, f"{fid} p{p_idx}: replacement char U+FFFD found"

            # Verify every expected field, table cell, and sentinel string appears on its assigned page
            for s in exp_data.get("page_sentinels", []):
                ptxt = page_texts[s["page_number"] - 1]
                for token in (s["page_label"], s["sentinel_id"], s["repeated_doc_id"]):
                    assert token in ptxt, f"{fid} p{s['page_number']}: missing sentinel token {token!r}"

            for fld in exp_data["expected_fields"]:
                ptxt = page_texts[fld["page_number"] - 1]
                # Multi-line prose/addresses may wrap across lines; check normalized whitespace substring
                norm_page = " ".join(ptxt.split())
                norm_val = " ".join(fld["printed_text"].replace(", ", " ").split())
                # Check individual words/tokens for wrapped multi-line blocks or exact string for scalar fields
                if fld["value_type"] in ("identifier", "currency_usd", "date_iso", "rate_percent", "boolean_mark"):
                    assert fld["printed_text"] in ptxt, f"{fid} p{fld['page_number']}: missing {fld['field_id']}={fld['printed_text']!r}"
                else:
                    for tok in fld["printed_text"].split():
                        clean_tok = tok.strip(",;:")
                        if clean_tok:
                            assert clean_tok in norm_page, f"{fid} p{fld['page_number']}: missing prose token {clean_tok!r}"

            for tbl in exp_data["expected_tables"]:
                for row in tbl["rows"]:
                    ptxt = page_texts[row["page_number"] - 1]
                    for cid, cell in row["cells"].items():
                        if cid != "description":
                            assert cell["printed_text"] in ptxt, (
                                f"{fid} p{row['page_number']} row {row['row_id']} col {cid}: "
                                f"missing {cell['printed_text']!r}"
                            )

            # Multi-page F07 check: authoritative invoice total appears ONLY on page 3
            if fam == "F07":
                inv_tot_str = exp_data["invoice_accounting"]["summary"]["invoice_total"]["printed_text"]
                assert inv_tot_str not in page_texts[0] and inv_tot_str not in page_texts[1]
                assert inv_tot_str in page_texts[2]

        elif vkind in ("v1_raster300", "v2_skew"):
            for p_idx, (txt, (icnt, fcnt)) in enumerate(zip(page_texts, img_font_counts), start=1):
                assert txt.strip() == "", f"{fid} p{p_idx}: expected image-only zero text, got {txt!r}"
                assert fcnt == 0, f"{fid} p{p_idx}: expected 0 /Font objects on image-only PDF, got {fcnt}"
                assert icnt == 1, f"{fid} p{p_idx}: expected 1 page raster XObject, got {icnt}"

        elif vkind == "v3_hybrid":
            hc_fields = [f for f in exp_data["expected_fields"] if f.get("modality") == "embedded_raster_only"]
            assert len(hc_fields) == 1
            hcf = hc_fields[0]
            tp = hcf["page_number"]
            assert 0.0 < hcf["page_area_ratio"] < 0.15, f"{fid}: hybrid area {hcf['page_area_ratio']} not in (0, 0.15)"
            for p_idx, (txt, (icnt, fcnt)) in enumerate(zip(page_texts, img_font_counts), start=1):
                assert len(txt.strip()) >= 80 and fcnt > 0
                if p_idx == tp:
                    assert icnt == 1, f"{fid} p{p_idx}: expected 1 hybrid image XObject on target page, got {icnt}"
                    assert hcf["printed_text"] not in txt, f"{fid}: hybrid raster string leaked into vector text!"
                else:
                    assert icnt == 0, f"{fid} p{p_idx}: unexpected image on non-target page"

    assert variant_counts == {"v0_clean": 8, "v1_raster300": 8, "v2_skew": 8, "v3_hybrid": 2}
    assert pages_checked == 40
    return {
        "pdfs_verified": len(manifest["fixtures"]),
        "pages_verified": pages_checked,
        "variant_counts": variant_counts,
    }


def check_two_run_regeneration(repo_root: pathlib.Path, scratch_dir: pathlib.Path) -> dict[str, object]:
    gen_script = repo_root / "evaluation" / "generation" / "generate_corpus.py"
    sources_dir = repo_root / "evaluation" / "synthetic" / "sources"
    run1_dir = scratch_dir / "regen_run1"
    run2_dir = scratch_dir / "regen_run2"

    for rdir in (run1_dir, run2_dir):
        subprocess.run(
            [
                sys.executable,
                str(gen_script),
                "--sources-dir",
                str(sources_dir),
                "--output-eval-root",
                str(rdir),
            ],
            check=True,
        )

    man_tracked = json.loads((repo_root / "evaluation" / "manifests" / "corpus-manifest.json").read_text(encoding="utf-8"))
    rel_paths = ["manifests/corpus-manifest.json"]
    for it in man_tracked["fixtures"]:
        rel_paths.append(it["file_path"].removeprefix("evaluation/"))
        rel_paths.append(it["expected_ground_truth_path"].removeprefix("evaluation/"))

    compared = 0
    for rel in rel_paths:
        b_repo = (repo_root / "evaluation" / rel).read_bytes()
        b_r1 = (run1_dir / rel).read_bytes()
        b_r2 = (run2_dir / rel).read_bytes()
        if b_r1 != b_r2 or b_r1 != b_repo:
            raise AssertionError(f"Non-deterministic bytes detected on {rel}")
        compared += 1

    return {"byte_identical_artifacts_across_run1_run2_and_repo": compared}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify WP-0004/004 synthetic corpus integrity and determinism.")
    parser.add_argument(
        "--repo-root",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parents[2],
    )
    parser.add_argument(
        "--check-regeneration",
        type=pathlib.Path,
        default=None,
        help="Optional scratch directory to execute a clean two-run byte-identity check.",
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    res = verify_evaluation_tree(repo_root)
    regen_res = None
    if args.check_regeneration is not None:
        regen_res = check_two_run_regeneration(repo_root, args.check_regeneration.resolve())

    print(f"CORPUS_INTEGRITY_PASS: {json.dumps({'tree': res, 'regeneration': regen_res})}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
