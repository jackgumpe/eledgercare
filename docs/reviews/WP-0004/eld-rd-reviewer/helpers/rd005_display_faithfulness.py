#!/usr/bin/env python3
"""Display-faithfulness check for image-bearing pages (reviewer-authored, CPU-only).

Audit question: rd005_render_pages.py shows v1/v2 pages by decoding the embedded RGB XObject.
This proves those decoded views are what a PDF viewer displays, by asserting for every page:
  * page dict has no /CropBox, /Rotate, /UserUnit, /Annots, /Group or extra /Resources entries;
  * the whole decompressed content stream is exactly `q W 0 0 H 0 0 cm /Im1 Do Q` (W,H == MediaBox),
    i.e. one full-page placement, identity orientation, no clip (W/W*), no other drawing;
  * a direct PDFium page render at 300/72 scale has the image's pixel size and is compared pixel-wise
    with the decoded raster (exact-equality count and max channel delta reported).
For v3 hybrids: content == parent v0 content + exactly one `q w 0 0 h x y cm /Im1 Do Q` op whose
matrix equals the declared hybrid box; non-target pages are byte-identical to v0 content.
"""
import json, pathlib, re, sys, zlib

import pypdfium2 as pdfium
from PIL import Image, ImageChops

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from rd005_verify import MiniPdf  # noqa: E402

repo, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
man = json.loads((repo / "evaluation/manifests/corpus-manifest.json").read_text(encoding="utf-8"))
fx = {f["fixture_id"]: f for f in man["fixtures"]}
rows, fails = [], []
for f in sorted(man["fixtures"], key=lambda z: z["fixture_id"]):
    vk = f["variant_kind"]
    if vk == "v0_clean":
        continue
    data = (repo / f["file_path"]).read_bytes()
    pages = MiniPdf(data).pages()
    doc = pdfium.PdfDocument(data)
    if vk in ("v1_raster300", "v2_skew"):
        for pi, pg in enumerate(pages):
            d = pg["dict"]
            im = pg["images"]["Im1"]
            W, H = pg["mediabox"][2], pg["mediabox"][3]
            want = f"q {W:.2f} 0 0 {H:.2f} 0.00 0.00 cm /Im1 Do Q\n".encode()
            content_exact = pg["content"] == want
            dict_clean = not re.search(r"/(CropBox|Rotate|UserUnit|Annots|Group|ArtBox|TrimBox|BleedBox)", d) and list(pg["images"]) == ["Im1"] and not pg["fonts"]
            no_clip = not re.search(rb"\bW\*?\s", pg["content"])
            raster = Image.frombytes("RGB", (im["w"], im["h"]), zlib.decompress(im["raw"]))
            rend = doc[pi].render(scale=300 / 72).to_pil().convert("RGB")
            size_ok = rend.size == raster.size
            if size_ok:
                diff = ImageChops.difference(rend, raster)
                maxd = max(hi for _, hi in diff.getextrema())
                bbox = diff.getbbox()
                hist = diff.convert("L").histogram()
                nz = sum(hist[1:])
            else:
                maxd, bbox, nz = None, None, None
            structural = content_exact and dict_clean and no_clip
            render_exact = size_ok and maxd == 0
            aligned = None
            if not render_exact:
                # Quantify renderer resampling: best integer offset in [-1,1]^2 on the common area (grayscale)
                a0, b0 = rend.convert("L"), raster.convert("L")
                best = None
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        w = min(a0.width - max(dx, 0), b0.width - max(-dx, 0)) - 1
                        h = min(a0.height - max(dy, 0), b0.height - max(-dy, 0)) - 1
                        a = a0.crop((max(dx, 0), max(dy, 0), max(dx, 0) + w, max(dy, 0) + h))
                        b = b0.crop((max(-dx, 0), max(-dy, 0), max(-dx, 0) + w, max(-dy, 0) + h))
                        hist = ImageChops.difference(a, b).histogram()
                        n = sum(hist)
                        mean = sum(i * c for i, c in enumerate(hist)) / n
                        if best is None or mean < best["mean_abs_gray"]:
                            best = {"dx": dx, "dy": dy, "mean_abs_gray": round(mean, 4), "frac_pixels_delta_gt_32": round(sum(hist[33:]) / n, 5),
                                    "frac_pixels_delta_gt_128": round(sum(hist[129:]) / n, 6)}
                aligned = best
            ok = structural and (render_exact or (aligned["mean_abs_gray"] < 2.0 and aligned["frac_pixels_delta_gt_128"] < 0.005))
            r = {"fixture_id": f["fixture_id"], "page": pi + 1, "mediabox": pg["mediabox"], "image_px": [im["w"], im["h"]],
                 "content_exact_full_page_placement": content_exact, "page_dict_clean": dict_clean, "no_clip_ops": no_clip,
                 "structural_exact": structural, "pdfium_render_px": list(rend.size), "render_size_equal": size_ok,
                 "render_pixel_exact": render_exact, "render_vs_decoded_max_channel_delta": maxd, "render_vs_decoded_nonzero_pixels": nz,
                 "render_best_alignment": aligned, "faithful_exact": structural and render_exact, "faithful_content_geometry": ok}
            rows.append(r)
            if not ok:
                fails.append(r)
    else:
        src = json.loads((repo / f["source_record_path"]).read_text(encoding="utf-8"))
        hc = src["hybrid_control"]
        v0 = MiniPdf((repo / fx[f["parent_fixture_id"]]["file_path"]).read_bytes()).pages()
        for pi, pg in enumerate(pages):
            if pi + 1 == hc["target_page"]:
                x0, y0, x1, y1 = hc["box_pt"]
                extra = f"q {x1-x0:.2f} 0 0 {y1-y0:.2f} {x0:.2f} {y0:.2f} cm /Im1 Do Q\n".encode()
                ok = pg["content"] == v0[pi]["content"] + extra and list(pg["images"]) == ["Im1"]
                im = pg["images"]["Im1"]
                ok = ok and (im["w"], im["h"]) == (round((x1 - x0) * 300 / 72), round((y1 - y0) * 300 / 72))
                r = {"fixture_id": f["fixture_id"], "page": pi + 1, "content_equals_v0_plus_one_image_op": ok, "image_px": [im["w"], im["h"]],
                     "placement_pt": [x0, y0, x1, y1], "no_clip_ops": not re.search(rb"\bW\*?\s", pg["content"])}
            else:
                ok = pg["content"] == v0[pi]["content"] and not pg["images"]
                r = {"fixture_id": f["fixture_id"], "page": pi + 1, "content_identical_to_v0": ok}
            r["faithful_exact"] = ok and r.get("no_clip_ops", True)
            r["faithful_content_geometry"] = r["faithful_exact"]
            rows.append(r)
            if not r["faithful_exact"]:
                fails.append(r)
    doc.close()
res = {"tool": "docs/reviews/WP-0004/eld-rd-reviewer/helpers/rd005_display_faithfulness.py", "pages_checked": len(rows),
       "image_only_pages": sum(1 for r in rows if "render_size_equal" in r), "hybrid_pages": sum(1 for r in rows if "render_size_equal" not in r),
       "structural_exact_pages": sum(1 for r in rows if r.get("structural_exact", r["faithful_exact"])),
       "render_pixel_exact_pages": sum(1 for r in rows if r.get("render_pixel_exact")),
       "render_resampled_pages": [f"{r['fixture_id']}#p{r['page']}" for r in rows if "render_pixel_exact" in r and not r["render_pixel_exact"]],
       "all_faithful_content_geometry": not fails, "failures": fails, "pages": rows}
out.write_text(json.dumps(res, indent=0) + "\n", encoding="utf-8")
print(json.dumps({k: res[k] for k in ("pages_checked", "image_only_pages", "hybrid_pages", "structural_exact_pages", "render_pixel_exact_pages", "all_faithful_content_geometry")}), len(fails))
for r in rows:
    if r.get("render_best_alignment"):
        print(r["fixture_id"], r["page"], r["pdfium_render_px"], r["image_px"], r["render_best_alignment"])
for r in fails[:10]:
    print(r)
