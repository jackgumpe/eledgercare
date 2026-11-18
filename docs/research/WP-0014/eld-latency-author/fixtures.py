"""Fixed WP-0014 image-only synthetic controls and their source truth."""
from pathlib import Path
import hashlib
import textwrap
import zlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TEXT = {
    "A": "The garden crew left a clean watering can beside the greenhouse door. A gray rabbit crossed the gravel path before the morning bell. When the sun reached the bench, two sparrows landed near the empty basket.",
    "B": "The print shop set a blue notebook on the counter near the window. A bicycle courier rang the silver bell just before lunch. After the rain passed, the clerk carried the parcels to the yellow van.",
}
PAGES = {"A": HERE / "A.pdf", "B": HERE / "B.pdf", "S": ROOT / "tests/fixtures/SYN-WO-01-v1-raster300.pdf"}
TRUTH = ROOT / "evaluation/synthetic/expected/SYN-WO-01-v1-raster300_expected.json"


def scan_pdf(sentence_text):
    from PIL import Image, ImageDraw, ImageFont

    font_path = Path("C:/Windows/Fonts/arial.ttf")
    assert hashlib.sha256(font_path.read_bytes()).hexdigest() == "edfbd22a3d088fc2f5d7c79b8c9c732df6dc878a60f0a80be0f92a3c7a634404"
    scan = Image.new("L", (1275, 1650), 255)
    draw = ImageDraw.Draw(scan)
    font = ImageFont.truetype(str(font_path), 30)
    for line_no, line in enumerate(textwrap.wrap(sentence_text, width=64)):
        draw.text((100, 170 + line_no * 42), line, fill=0, font=font)
    pixels = zlib.compress(scan.tobytes(), 9)
    def stream(meta, data):
        return b"<< " + meta + b" /Length " + str(len(data)).encode() + b" >>\nstream\n" + data + b"\nendstream"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /XObject << /Im 4 0 R >> >> /Contents 5 0 R >>",
        stream(b"/Type /XObject /Subtype /Image /Width 1275 /Height 1650 /ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /FlateDecode", pixels),
        stream(b"", b"q 612 0 0 792 0 0 cm /Im Do Q"),
    ]
    result = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(result)
    result.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        result.extend(f"{offset:010d} 00000 n \n".encode())
    result.extend(f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(result)


if __name__ == "__main__":
    for key, passage in TEXT.items():
        data = scan_pdf(passage)
        if PAGES[key].exists():
            assert PAGES[key].read_bytes() == data
        else:
            PAGES[key].write_bytes(data)
        print(key, len(data), hashlib.sha256(data).hexdigest())
