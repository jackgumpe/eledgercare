"""Generate the WP-0017 synthetic ID packet from a separate 32-byte binary seed."""
import argparse
from contextlib import closing
from functools import lru_cache
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import random
import sys
from tempfile import TemporaryDirectory
import zlib

from PIL import Image, ImageDraw, ImageFont
import pypdfium2 as pdfium
import pypdfium2.raw as pdfraw

ROOT = Path(__file__).resolve().parents[4]
EVAL = ROOT / "docs/evaluation/WP-0015"
sys.path.insert(0, str(EVAL))
from development import SCALE, Sheet
from audit import crop_ink
from score import valid_box

FAMILY = "id_ablation"
W, H = 595, 842
FONT_DIR = Path("C:/Windows/Fonts")
FONTS = {
    "Arial": ("arial.ttf", "edfbd22a3d088fc2f5d7c79b8c9c732df6dc878a60f0a80be0f92a3c7a634404"),
    "Times New Roman": ("times.ttf", "0bf1b21b27b370039b60eca23d532c3fe3fb308750d8f13816db70a6cb666804"),
    "Courier New": ("cour.ttf", "e4a66a0259718d0c8f4b6e14319b4803ced45afbddf3abba8b8c3e2006856206"),
}
POSITIONS = ("header", "row1", "row2")
TITLES = ("Instrument service sheet", "Station inspection sheet", "Equipment service record")
NOTES = ("Check tags before release.", "Return the record to dispatch.", "Verify the assigned reading.")
SITES = ("North bay", "West bench", "East line", "South bay", "Test bench", "Spare rack")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(data):
    return (json.dumps(data, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode()


@lru_cache(maxsize=32)
def face(family, size):
    return ImageFont.truetype(str(FONT_DIR / FONTS[family][0]), size * SCALE)


class FixtureSheet(Sheet):
    def __init__(self, family):
        self.image = Image.new("L", (W * SCALE, H * SCALE), 252)
        self.ink = ImageDraw.Draw(self.image)
        self.lines, self.tables, self.reading = [], [], []
        self.family = family

    def print_at(self, text, x, y, size, bold):
        # The three pinned regular faces are used throughout, including table headers.
        at = (x * SCALE, y * SCALE)
        font = face(self.family, size)
        bounds = self.ink.textbbox(at, text, font=font, anchor="lt")
        if not valid_box(list(bounds), W * SCALE, H * SCALE):
            raise ValueError("printed text outside page")
        self.ink.text(at, text, font=font, anchor="lt", fill=29)
        return [coordinate / SCALE for coordinate in bounds]

    def truth(self, page):
        return dict(page=page, width=W, height=H, text="\n".join(self.reading),
                    lines=self.lines, tables=self.tables)


def pdf(images):
    """Deterministic PDF 1.4 image pages. Point geometry differs from every WP-0015 page."""
    kids = " ".join(f"{3+3*i} 0 R" for i in range(len(images)))
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>",
               f"<< /Type /Pages /Kids [{kids}] /Count {len(images)} >>".encode()]

    def stream(properties, data):
        return f"<< {properties} /Length {len(data)} >>\nstream\n".encode() + data + b"\nendstream"

    for image in images:
        n = len(objects) + 1
        page = (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W} {H}] "
                f"/Resources << /XObject << /Sheet {n+1} 0 R >> >> /Contents {n+2} 0 R >>")
        attrs = (f"/Subtype /Image /Type /XObject /Width {image.width} /Height {image.height} "
                 "/ColorSpace /DeviceGray /Filter /FlateDecode /BitsPerComponent 8")
        objects.extend([page.encode(), stream(attrs, zlib.compress(image.tobytes(), 6)),
                        stream("", f"q {W} 0 0 {H} 0 0 cm /Sheet Do Q".encode())])
    result = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for n, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(f"{n} 0 obj\n".encode() + obj + b"\nendobj\n")
    start = len(result)
    result.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for byte in offsets:
        result.extend(f"{byte:010d} 00000 n \n".encode())
    result.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode())
    return bytes(result)

def page_family(index):
    window, position = divmod(index, 3)
    return tuple(FONTS)[(window + position) % 3]


def identifiers(rng):
    # Each of the nine font/placement strata contains six IDs, 18 vertical and 12 round slots.
    result = {}
    tails = iter(rng.sample(range(200, 1000), 54))
    for family in FONTS:
        page_indices = [i for i in range(18) if page_family(i) == family]
        for place in POSITIONS:
            vertical = list("I1L" * 6)
            rounds = list("O0" * 6)
            rng.shuffle(vertical)
            rng.shuffle(rounds)
            for i in page_indices:
                chars = [vertical.pop() for _ in range(3)] + [rounds.pop() for _ in range(2)]
                rng.shuffle(chars)
                result[i, place] = "".join(chars) + "-R17" + str(next(tails))
    return result


def make_sheets(seed):
    rng = random.Random(int.from_bytes(seed, "big"))
    ids = identifiers(rng)
    sheets = []
    for i in range(18):
        sheet = FixtureSheet(page_family(i))
        header, row1, row2 = (ids[i, k] for k in POSITIONS)
        left = rng.choice((40, 46, 52))
        start = rng.choice((48, 56, 64))
        sheet.line(rng.choice(TITLES), left, start, 20)
        sheet.line("Inspection ID: " + header, left, start + 48, 15, critical=header)
        sheet.line(rng.choice(NOTES), left, start + 83, 13)
        site1, site2 = rng.sample(SITES, 2)
        columns = [["Asset ID", "Location", "Status"],
                   [row1, site1, rng.choice(("Open", "Ready"))],
                   [row2, site2, rng.choice(("Held", "Closed"))]]
        widths = [175, 160, 126]
        id_col = 0
        if i % 2:
            columns = [[row[1], row[0], row[2]] for row in columns]
            widths = [160, 175, 126]
            id_col = 1
        sheet.table(left, start + 153, widths, columns, (id_col,), row_h=36, size=13)
        sheets.append(sheet)
    return sheets


def rendered_manifest(public, references):
    source = public / "source.pdf"
    rows = []
    (public / "rgb").mkdir()
    with pdfium.PdfDocument(source) as document:
        if len(document) != len(references):
            raise ValueError("page count")
        for i, ref in enumerate(references):
            with closing(document[i]) as page, closing(page.get_textpage()) as layer:
                if (layer.count_chars() != 0 or [obj.type for obj in page.get_objects()] !=
                        [pdfraw.FPDF_PAGEOBJ_IMAGE] or page.get_size() != (W, H)):
                    raise ValueError("expected one raster object and zero text-layer characters")
                with closing(page.render(scale=300 / 72)) as bitmap:
                    rgb = bitmap.to_pil().convert("RGB")
                with closing(rgb), closing(rgb.convert("L")) as gray:
                    for line in ref["lines"]:
                        if not crop_ink(gray, line["bbox"], 0):
                            raise ValueError("unprinted line")
                    for table in ref["tables"]:
                        for row in table["rows"]:
                            for cell in row:
                                if not crop_ink(gray, cell["bbox"], 2):
                                    raise ValueError("unprinted cell")
                    relative = f"rgb/page-{i+1:03d}.png"
                    raster = public / relative
                    rgb.save(raster, format="PNG", compress_level=6)
                    rows.append(dict(page=i+1, page_number=i+1, width_px=rgb.width,
                                     height_px=rgb.height, rgb_sha256=digest(rgb.tobytes()),
                                     png=relative, png_sha256=digest(raster.read_bytes()),
                                     font_family=page_family(i), text_layer_chars=0, embedded_images=1))
    return dict(family=FAMILY, pdf_sha256=digest(source.read_bytes()), pdf_bytes=source.stat().st_size,
                renderer=dict(dpi=300, pixel_mode="RGB", pypdfium2=version("pypdfium2"),
                              pdfium=str(pdfium.PDFIUM_INFO), pillow=Image.__version__),
                windows=[list(range(i, i+3)) for i in range(1, 19, 3)], pages=rows)


def install(staged, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        staged.rename(target)
        return
    def hashes(folder):
        return {p.relative_to(folder): digest(p.read_bytes()) for p in folder.rglob("*") if p.is_file()}
    if hashes(target) != hashes(staged):
        raise FileExistsError(f"existing publication has different bytes: {target}")


def generate(seed_file, output):
    seed = seed_file.read_bytes()
    if len(seed) != 32:
        raise ValueError("expected 32-byte seed")
    for name, expected in FONTS.values():
        if digest((FONT_DIR / name).read_bytes()) != expected:
            raise ValueError(f"font identity differs: {name}")
    output.mkdir(parents=True, exist_ok=True)
    public_target = output / "public/dev" / FAMILY
    if seed_file.resolve().is_relative_to((output / "public").resolve()):
        raise ValueError("seed must be held outside the public directory")
    with TemporaryDirectory(dir=output, prefix=".building-") as tmp:
        public, custody = Path(tmp) / "public", Path(tmp) / "custody"
        public.mkdir()
        custody.mkdir()
        sheets = make_sheets(seed)
        try:
            source = pdf([p.image for p in sheets])
            refs = [p.truth(i) for i, p in enumerate(sheets, 1)]
        finally:
            for sheet in sheets:
                sheet.image.close()
        (public / "source.pdf").write_bytes(source)
        truth = dict(family=FAMILY, source_sha256=digest(source), pages=refs)
        (custody / "truth.json").write_bytes(json_bytes(truth))
        (custody / "seed.bin").write_bytes(seed)
        manifest = rendered_manifest(public, refs)
        (public / "rasters.json").write_bytes(json_bytes(manifest))
        install(custody, output / "custody/dev" / FAMILY)
        install(public, public_target)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = generate(args.seed_file, args.output)
    print(json.dumps(dict(pdf_sha256=result["pdf_sha256"], pages=len(result["pages"]))))
