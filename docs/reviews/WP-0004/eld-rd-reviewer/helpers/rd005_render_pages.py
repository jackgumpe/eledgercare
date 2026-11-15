#!/usr/bin/env python3
"""Render every page of every corpus PDF for reviewer visual inspection (reviewer-authored).

v0/v3 text-layer pages: rendered with pinned pypdfium2 at 200 DPI and split into top/bottom halves
(plus an extra 300-DPI crop of the embedded raster region on hybrid target pages).
v1/v2 image-only pages: the embedded 300-DPI raster is decoded directly (no re-sampling by a viewer),
downsampled 2:1 with BOX (150 DPI) and split into top/bottom halves.
Writes PNGs plus render-index.json (page -> image files, sha256) to the output directory.
"""
import hashlib, json, pathlib, sys, zlib

import pypdfium2 as pdfium
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from rd005_verify import MiniPdf  # noqa: E402

repo, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
man = json.loads((repo / "evaluation/manifests/corpus-manifest.json").read_text(encoding="utf-8"))
index = []
for f in sorted(man["fixtures"], key=lambda z: z["fixture_id"]):
    data = (repo / f["file_path"]).read_bytes()
    pages = MiniPdf(data).pages()
    doc = pdfium.PdfDocument(data)
    for pi in range(len(doc)):
        if f["variant_kind"] in ("v0_clean", "v3_hybrid"):
            im = doc[pi].render(scale=200 / 72).to_pil().convert("RGB")
            dpi = 200
        else:
            x = next(iter(pages[pi]["images"].values()))
            im = Image.frombytes("RGB", (x["w"], x["h"]), zlib.decompress(x["raw"]))
            im = im.resize((im.width // 2, im.height // 2), Image.Resampling.BOX)
            dpi = 150
        h = im.height
        parts = {"top": im.crop((0, 0, im.width, h // 2 + 40)), "bottom": im.crop((0, h // 2 - 40, im.width, h))}
        files = []
        for nm, part in parts.items():
            fn = out / f"{f['fixture_id']}_p{pi+1}_{nm}.png"
            part.save(fn)
            files.append({"file": fn.name, "sha256": hashlib.sha256(fn.read_bytes()).hexdigest(), "size_px": list(part.size)})
        if f["variant_kind"] == "v3_hybrid":
            for x in pages[pi]["images"].values():
                st = Image.frombytes("RGB", (x["w"], x["h"]), zlib.decompress(x["raw"]))
                fn = out / f"{f['fixture_id']}_p{pi+1}_embedded_raster_native.png"
                st.save(fn)
                files.append({"file": fn.name, "sha256": hashlib.sha256(fn.read_bytes()).hexdigest(), "size_px": list(st.size)})
        index.append({"fixture_id": f["fixture_id"], "family": f["family_id"], "split": f["split"], "variant": f["variant_kind"],
                      "page": pi + 1, "render_dpi": dpi, "full_size_px": [im.width, im.height], "images": files})
    doc.close()
(out / "render-index.json").write_text(json.dumps(index, indent=0) + "\n", encoding="utf-8")
print(len(index), "pages rendered")
