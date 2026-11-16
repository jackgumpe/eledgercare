"""Deterministic stdlib PDF 1.4 writer using standard Base-14 fonts and lossless Flate images.

Zero third-party libraries are imported here so vector PDF byte layout, object numbering,
metadata timestamps, and trailer /ID digests remain 100% deterministic across runs.
"""

from __future__ import annotations

import hashlib
import zlib
from dataclasses import dataclass, field
from typing import Iterable

LETTER_WIDTH_PT = 612.0
LETTER_HEIGHT_PT = 792.0
FIXED_PDF_DATE = "D:20261114000000Z"
PRODUCER_TAG = "eLedgerCare Deterministic Synthetic Generator v1.0"

FONT_MAP = {
    "regular": ("F1", "Helvetica"),
    "bold": ("F2", "Helvetica-Bold"),
    "mono": ("F3", "Courier"),
    "mono_bold": ("F4", "Courier-Bold"),
}

# Conservative per-character AFM width ratios (in em units) for Helvetica / Helvetica-Bold / Courier
# used strictly to assert that rendered strings never overflow or clip inside cells/boxes.
_HELV_NARROW = set("ilI.,:;|!'` ")
_HELV_MED_NARROW = set("fjrt-()[]{}/\\")
_HELV_WIDE = set("mwMWGOQCDHNU&@")


def estimate_text_width_pt(text: str, font_key: str, size_pt: float) -> float:
    if not text:
        return 0.0
    if font_key in ("mono", "mono_bold"):
        return len(text) * size_pt * 0.602
    bold_factor = 1.06 if font_key == "bold" else 1.00
    total_em = 0.0
    for ch in text:
        if ch in _HELV_NARROW:
            total_em += 0.29
        elif ch in _HELV_MED_NARROW:
            total_em += 0.35
        elif ch == "%":
            total_em += 0.90
        elif ch in _HELV_WIDE:
            total_em += 0.78
        elif ch.isupper():
            total_em += 0.68
        elif ch.isdigit() or ch in "$+-=":
            total_em += 0.56
        else:
            total_em += 0.54
    return total_em * size_pt * bold_factor


def wrap_text_deterministic(text: str, font_key: str, size_pt: float, max_width_pt: float) -> list[str]:
    words = text.split(" ")
    lines: list[str] = []
    cur = ""
    for w in words:
        cand = w if not cur else f"{cur} {w}"
        if estimate_text_width_pt(cand, font_key, size_pt) <= max_width_pt:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            if estimate_text_width_pt(w, font_key, size_pt) > max_width_pt:
                raise ValueError(f"Single token '{w}' exceeds max_width_pt={max_width_pt:.1f} at {size_pt}pt")
            cur = w
    if cur:
        lines.append(cur)
    return lines


def pdf_escape(text: str) -> str:
    # Ensure pure printable ASCII / WinAnsi safe text for deterministic rendering
    for ch in text:
        code = ord(ch)
        if code < 32 or code > 126:
            raise ValueError(f"Non-ASCII character U+{code:04X} in '{text}'; keep synthetic literals ASCII-clean.")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


@dataclass
class EmbeddedRgbImage:
    name: str
    width_px: int
    height_px: int
    rgb_bytes: bytes
    compressed_bytes: bytes = field(init=False)

    def __post_init__(self) -> None:
        expected_len = self.width_px * self.height_px * 3
        if len(self.rgb_bytes) != expected_len:
            raise ValueError(f"RGB byte length mismatch: got {len(self.rgb_bytes)}, expected {expected_len}")
        self.compressed_bytes = zlib.compress(self.rgb_bytes, level=9)


class PdfPageCanvas:
    """Collects deterministic PDF content-stream operators for a single page (origin bottom-left)."""

    def __init__(self, width_pt: float = LETTER_WIDTH_PT, height_pt: float = LETTER_HEIGHT_PT) -> None:
        self.width_pt = width_pt
        self.height_pt = height_pt
        self.ops: list[str] = []
        self.images: list[EmbeddedRgbImage] = []
        self.uses_fonts: bool = False

    def rect_fill_stroke(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        fill_rgb: tuple[float, float, float] | None = None,
        stroke_rgb: tuple[float, float, float] | None = (0.15, 0.18, 0.22),
        line_width: float = 0.6,
    ) -> None:
        self.ops.append("q")
        if stroke_rgb is not None:
            self.ops.append(f"{line_width:.2f} w {stroke_rgb[0]:.3f} {stroke_rgb[1]:.3f} {stroke_rgb[2]:.3f} RG")
        if fill_rgb is not None:
            self.ops.append(f"{fill_rgb[0]:.3f} {fill_rgb[1]:.3f} {fill_rgb[2]:.3f} rg")
        self.ops.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re")
        if fill_rgb is not None and stroke_rgb is not None:
            self.ops.append("B")
        elif fill_rgb is not None:
            self.ops.append("f")
        elif stroke_rgb is not None:
            self.ops.append("S")
        self.ops.append("Q")

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        stroke_rgb: tuple[float, float, float] = (0.20, 0.23, 0.28),
        line_width: float = 0.5,
    ) -> None:
        self.ops.append(
            f"q {line_width:.2f} w {stroke_rgb[0]:.3f} {stroke_rgb[1]:.3f} {stroke_rgb[2]:.3f} RG "
            f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S Q"
        )

    def draw_text(
        self,
        text: str,
        x: float,
        y: float,
        font_key: str = "regular",
        size_pt: float = 9.0,
        color_rgb: tuple[float, float, float] = (0.05, 0.06, 0.08),
        max_width_pt: float | None = None,
        align: str = "left",
    ) -> tuple[float, float, float, float]:
        if not text:
            return (x, y, x, y + size_pt)
        self.uses_fonts = True
        font_alias, _ = FONT_MAP[font_key]
        est_w = estimate_text_width_pt(text, font_key, size_pt)
        if max_width_pt is not None and est_w > max_width_pt + 0.5:
            raise ValueError(
                f"Text overflow: '{text}' ({est_w:.1f}pt at {font_key}/{size_pt}pt) > max_width_pt={max_width_pt:.1f}pt"
            )
        draw_x = x
        if max_width_pt is not None:
            if align == "right":
                draw_x = x + max_width_pt - est_w
            elif align == "center":
                draw_x = x + (max_width_pt - est_w) / 2.0
        if draw_x < 12.0 or (draw_x + est_w) > (self.width_pt - 12.0):
            raise ValueError(
                f"Page margin violation for '{text}': x_span=[{draw_x:.1f}, {draw_x + est_w:.1f}] on width={self.width_pt:.1f}"
            )
        if y < 12.0 or (y + size_pt) > (self.height_pt - 10.0):
            raise ValueError(
                f"Vertical page margin violation for '{text}': y={y:.1f} on height={self.height_pt:.1f}"
            )
        escaped = pdf_escape(text)
        self.ops.append(
            f"BT /{font_alias} {size_pt:.2f} Tf {color_rgb[0]:.3f} {color_rgb[1]:.3f} {color_rgb[2]:.3f} rg "
            f"1 0 0 1 {draw_x:.2f} {y:.2f} Tm ({escaped}) Tj ET"
        )
        return (round(draw_x, 2), round(y, 2), round(draw_x + est_w, 2), round(y + size_pt, 2))

    def draw_image_rgb(
        self,
        rgb_bytes: bytes,
        width_px: int,
        height_px: int,
        x_pt: float,
        y_pt: float,
        w_pt: float,
        h_pt: float,
    ) -> str:
        name = f"Im{len(self.images) + 1}"
        self.images.append(EmbeddedRgbImage(name=name, width_px=width_px, height_px=height_px, rgb_bytes=rgb_bytes))
        self.ops.append(f"q {w_pt:.2f} 0 0 {h_pt:.2f} {x_pt:.2f} {y_pt:.2f} cm /{name} Do Q")
        return name

    def content_bytes(self) -> bytes:
        raw = ("\n".join(self.ops) + "\n").encode("ascii")
        return zlib.compress(raw, level=9)


def serialize_pdf(pages: Iterable[PdfPageCanvas], title: str) -> bytes:
    page_list = list(pages)
    if not page_list:
        raise ValueError("Cannot serialize empty PDF")

    any_fonts = any(p.uses_fonts for p in page_list)
    objects: list[bytes] = []

    def add_obj(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    # 1: Catalog, 2: Pages placeholder
    catalog_id = add_obj(b"<< /Type /Catalog /Pages 2 0 R >>")
    pages_id = add_obj(b"")  # filled after page IDs are allocated
    assert catalog_id == 1 and pages_id == 2

    font_obj_ids: dict[str, int] = {}
    if any_fonts:
        for _, (alias, base_font) in FONT_MAP.items():
            fid = add_obj(
                f"<< /Type /Font /Subtype /Type1 /BaseFont /{base_font} /Encoding /WinAnsiEncoding >>".encode("ascii")
            )
            font_obj_ids[alias] = fid

    page_ids: list[int] = []
    for p in page_list:
        c_bytes = p.content_bytes()
        content_id = add_obj(
            f"<< /Length {len(c_bytes)} /Filter /FlateDecode >>\nstream\n".encode("ascii")
            + c_bytes
            + b"\nendstream"
        )

        xobj_entries: list[str] = []
        for img in p.images:
            im_hdr = (
                f"<< /Type /XObject /Subtype /Image /Width {img.width_px} /Height {img.height_px} "
                f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode "
                f"/Length {len(img.compressed_bytes)} >>\nstream\n"
            ).encode("ascii")
            im_id = add_obj(im_hdr + img.compressed_bytes + b"\nendstream")
            xobj_entries.append(f"/{img.name} {im_id} 0 R")

        res_parts: list[str] = []
        if p.uses_fonts:
            f_map_str = " ".join(f"/{alias} {fid} 0 R" for alias, fid in font_obj_ids.items())
            res_parts.append(f"/Font << {f_map_str} >>")
        if xobj_entries:
            res_parts.append(f"/XObject << {' '.join(xobj_entries)} >>")
        res_dict = f"<< {' '.join(res_parts)} >>"

        page_dict = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {p.width_pt:.2f} {p.height_pt:.2f}] "
            f"/Resources {res_dict} /Contents {content_id} 0 R >>"
        ).encode("ascii")
        page_ids.append(add_obj(page_dict))

    kids_str = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[pages_id - 1] = f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids_str}] >>".encode("ascii")

    info_id = add_obj(
        (
            f"<< /Title ({pdf_escape(title)}) /Producer ({pdf_escape(PRODUCER_TAG)}) "
            f"/CreationDate ({FIXED_PDF_DATE}) /ModDate ({FIXED_PDF_DATE}) >>"
        ).encode("ascii")
    )

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: list[int] = []
    for idx, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{idx} 0 obj\n".encode("ascii"))
        out.extend(body)
        out.extend(b"\nendobj\n")

    file_id_hex = hashlib.sha256(bytes(out)).hexdigest()[:32]
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R /Info {info_id} 0 R "
        f"/ID [<{file_id_hex}> <{file_id_hex}>] >>\nstartxref\n{xref_pos}\n%%EOF\n"
    ).encode("ascii")
    out.extend(trailer)
    return bytes(out)


def build_image_only_pdf(
    rgb_pages: Iterable[tuple[bytes, int, int]],
    dpi: float = 300.0,
    title: str = "Image-Only Raster Variant",
) -> bytes:
    """Wrap RGB page bitmaps into a pure image-only PDF with zero /Font objects and zero BT..ET text."""
    canvases: list[PdfPageCanvas] = []
    for rgb_bytes, w_px, h_px in rgb_pages:
        w_pt = round(w_px * 72.0 / dpi, 2)
        h_pt = round(h_px * 72.0 / dpi, 2)
        c = PdfPageCanvas(width_pt=w_pt, height_pt=h_pt)
        c.draw_image_rgb(rgb_bytes=rgb_bytes, width_px=w_px, height_px=h_px, x_pt=0.0, y_pt=0.0, w_pt=w_pt, h_pt=h_pt)
        assert not c.uses_fonts
        canvases.append(c)
    return serialize_pdf(canvases, title=title)
