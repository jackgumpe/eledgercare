"""Build synthetic development packets. No paper/OCR-derived answers are used."""
import argparse
import hashlib
import json
import zlib
from pathlib import Path
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

DIR = Path(__file__).resolve().parent
W, H, SCALE = 612, 792, 2


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=True, indent=2) + "\n").encode())


@lru_cache
def font(size, bold):
    return ImageFont.truetype("C:/Windows/Fonts/" + ("arialbd.ttf" if bold else "arial.ttf"), size * SCALE)


class Sheet:
    def __init__(self):
        self.image = Image.new("L", (W * SCALE, H * SCALE), 252)
        self.ink = ImageDraw.Draw(self.image)
        self.lines, self.tables, self.reading = [], [], []

    def rule(self, rect, gray=95, fill=None):
        self.ink.rectangle(tuple(int(v * SCALE) for v in rect), fill=fill, outline=gray, width=1)

    def print_at(self, text, x, y, size, bold):
        at = (x * SCALE, y * SCALE)
        face = font(size, bold)
        bbox = self.ink.textbbox(at, text, font=face, anchor="lt")
        assert 0 <= bbox[0] <= bbox[2] < W*SCALE and 0 <= bbox[1] <= bbox[3] < H*SCALE
        self.ink.text(at, text, font=face, anchor="lt", fill=29, stroke_width=0)
        return [v / SCALE for v in bbox]

    def line(self, text, x, y, size=13, bold=False, critical=None):
        bbox = self.print_at(text, x, y, size, bold)
        self.lines.append(dict(text=text, bbox=bbox, critical=critical))
        self.reading.append(text)

    def table(self, x, y, widths, data, critical_columns=(), row_h=30, size=11):
        rows = []
        for r, values in enumerate(data):
            assert len(values) == len(widths)
            left, top, cells = x, y + r * row_h, []
            for c, (value, width) in enumerate(zip(values, widths)):
                bbox = [left, top, left + width, top + row_h]
                self.rule(bbox, fill=231 if r == 0 else None)
                if value:
                    ink = self.print_at(value, left + 5, top + 8, size, r == 0)
                    assert ink[2] < bbox[2]-2 and ink[3] < bbox[3]-1, (value, bbox, ink)
                cells.append(dict(text=value, bbox=bbox, critical=r > 0 and c in critical_columns and bool(value)))
                left += width
            rows.append(cells)
            self.reading.append(" ".join(values))
        self.tables.append(dict(bbox=[x, y, x + sum(widths), y + len(data)*row_h], rows=rows))

    def truth(self, page):
        return dict(page=page, width=W, height=H, text="\n".join(self.reading), lines=self.lines, tables=self.tables)


def pdf(images):
    # Fixed PDF objects emit one lossless gray image per page, with no font, text or metadata.
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    objects.append(("<< /Type /Pages /Count %d /Kids [%s] >>" %
                    (len(images), " ".join(f"{3+3*i} 0 R" for i in range(len(images))))).encode())
    for i, image in enumerate(images):
        n = 3+3*i
        objects.append((f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W} {H}] "
                        f"/Resources << /XObject << /Scan {n+1} 0 R >> >> /Contents {n+2} 0 R >>").encode())
        data = zlib.compress(image.tobytes(), 6)
        objects.append((f"<< /Type /XObject /Subtype /Image /Width {image.width} /Height {image.height} "
                        f"/ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /FlateDecode /Length {len(data)} >>"
                        "\nstream\n").encode() + data + b"\nendstream")
        stream = f"q {W} 0 0 {H} 0 0 cm /Scan Do Q\n".encode()
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode()+stream+b"endstream")
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for n, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{n} 0 obj\n".encode()+obj+b"\nendobj\n")
    start = len(output)
    output.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for offset in offsets:
        output.extend(f"{offset:010} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Root 1 0 R /Size {len(objects)+1} >>\nstartxref\n{start}\n%%EOF\n".encode())
    return bytes(output)


def packet(folder, family, pages):
    folder.mkdir(exist_ok=True, parents=True)
    body = pdf([p.image for p in pages])
    sha = digest(body)
    (folder / "source.pdf").write_bytes(body)
    truth = dict(family=family, source_sha256=sha, pages=[p.truth(i) for i, p in enumerate(pages, 1)])
    write_json(folder / "truth.json", truth)
    return truth


def development(folder):
    brief = Sheet()
    brief.line("Cooling loop service", 55, 70, 21, True)
    brief.line("Ticket CL-I0O7", 55, 116, critical="CL-I0O7")
    brief.line("At the east riser, the seal was dry after the pump restarted.", 55, 152)
    brief.line("Gauge reading 0.81 bar.", 55, 184, critical="0.81")
    packet(folder/"short", "short", [brief])

    dense = Sheet()
    dense.line("Workshop maintenance order", 38, 52, 24, True)
    dense.line("Order WO-O1I8", 39, 101, 15, critical="WO-O1I8")
    dense.line("Bay 04     Technician R. Vale     Shift B", 39, 138)
    dense.line("Release the replacement stock against the quantities below.", 39, 179)
    dense.table(38, 228, [80, 165, 50, 69, 75, 93],
        [["Stock ID", "Service item", "Qty", "Unit", "Net USD", "Batch"],
         ["I0-701", "Seal, low pressure", "2", "4.05", "8.10", "O18"],
         ["10-7O1", "Seal, high pressure", "1", "40.50", "40.50", "018"],
         ["BF-081", "Flange washer", "6", "0.81", "4.86", ""],
         ["BF-081", "Flange washer", "6", "0.81", "4.86", ""],
         ["PX-110", "Test coupling", "1", "18.90", "18.90", "L11"],
         ["PX-I10", "Return coupling", "1", "-1.89", "-1.89", "L1I"]],
        critical_columns=(0, 3, 4, 5))
    dense.line("Net total USD 75.33", 375, 489, 16, True, critical="75.33")
    dense.line("Install after isolation. Retain both washer lots on the record.", 39, 572)
    packet(folder/"dense", "dense", [dense])

    first, second, blank, final = [Sheet() for _ in range(4)]
    first.line("Meter inspection | dispatch", 57, 71, 20, True)
    first.line("Route MR-I1O", 57, 124, critical="MR-I1O")
    first.line("Carry the red meter to the west riser.", 57, 159)
    second.line("Meter inspection | readings", 57, 71, 20, True)
    second.line("West riser", 57, 124)
    second.table(57, 180, [148, 148, 132], [["Meter", "Before (bar)", "After (bar)"],
                        ["M-1O8", "1.09", "1.90"], ["M-108", "1.90", "1.09"]], (0, 1, 2))
    second.line("Return tag on the final sheet.", 57, 680)
    final.line("Meter inspection | release", 57, 71, 20, True)
    final.line("Return tag RT-0O1", 57, 124, critical="RT-0O1")
    final.line("Witness recorded 0.19 bar.", 57, 159, critical="0.19")
    final.line("Release signed after the second vent.", 57, 207)
    packet(folder/"boundary", "boundary", [first, second, blank, final])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path, help="new/empty directory for regenerated development files")
    destination = parser.parse_args().destination
    if destination.exists() and any(destination.iterdir()):
        parser.error("destination must be empty")
    development(destination)
