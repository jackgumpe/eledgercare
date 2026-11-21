"""Render two interior windows of a fixed twelve-page synthetic maintenance packet."""
import argparse
from contextlib import closing
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys

import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "docs/evaluation/WP-0015"))
from development import Sheet, pdf
sys.path.insert(0, str(ROOT / "workers/local_ocr"))
from local_ocr import protocol


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def make_pages():
    pages = []
    notes = ("Door latch repaired.", "Valve seal replaced.", "Pump test passed.")
    tasks = ("Drain vent", "Pilot valve", "Return flange")
    for number in range(1, 13):
        sheet = Sheet()
        if 4 <= number <= 6:
            sheet.line(notes[number - 4], 63, 117, 22)
        elif 7 <= number <= 9:
            title = tasks[number - 7]
            sheet.line(title + " maintenance order", 48, 64, 20, True)
            sheet.line(f"Service ticket S-{number}24. Bay {number}.", 48, 116)
            sheet.line("Parts used during the annual inspection", 48, 158)
            table = [["Part", "Item", "Count", "Price"]]
            for i, label in enumerate(("Seat ring", "Steel sleeve", "Clamp bolt", "Gasket", "Vent plug"), 1):
                table.append([f"V{number}{i}",label,str(i + number - 6),f"{number + 2 * i}.{i}0"])
            sheet.table(48,205,[86,185,82,95],table,row_h=34,size=13)
            sheet.line("Technician verified the installed quantities.", 48, 510)
        else:
            sheet.line(f"Service binder divider {number}", 70, 136, 18, True)
        pages.append(sheet.image)
    return pages


def build(out):
    out.mkdir(parents=True,exist_ok=True)
    (out / "images").mkdir(exist_ok=True)
    pdf_bytes = pdf(make_pages())
    (out / "development.pdf").write_bytes(pdf_bytes)
    windows = {}
    with pdfium.PdfDocument(pdf_bytes) as doc:
        assert len(doc)==12
        for label, numbers in (("short",range(4,7)),("long",range(7,10))):
            windows[label]=[]
            for n in numbers:
                with closing(doc[n-1]) as page, closing(page.render(scale=protocol.RENDER_SCALE)) as bmp:
                    img=bmp.to_pil().convert("RGB")
                    path=f"images/page-{n:02}.png"
                    img.save(out/path,"PNG")
                    windows[label].append(dict(page=n,image=path,width=img.width,height=img.height,
                        sha256=sha((out/path).read_bytes()),rgb_sha256=sha(img.tobytes())))
                    img.close()
    manifest=dict(packet="WP-0023",source="development.pdf",pages=12,sha256=sha(pdf_bytes),dpi=300,
              renderScale=protocol.RENDER_SCALE,renderer=version("pypdfium2"),windows=windows,
              choice="Two contiguous non-edge native windows, three pages each. Sparse one-line repairs and dense ruled materials orders were selected before any model output. Control token counts determine the measured length contrast.")
    (out/"manifest.json").write_bytes((json.dumps(manifest,indent=2)+"\n").encode())


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out",type=Path)
    build(ap.parse_args().out)
