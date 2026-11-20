"""WP-0019 reviewer shared helpers (eld-rd-reviewer). Independent of every WP-0019 author source.

No function here calls WinRT, OCR, a GPU or the network. Rendering uses the read-only WP-0005
environment (pypdfium2/Pillow/numpy) only for independent input verification.
"""
import hashlib
import json
import math
import os
import struct
import subprocess
import sys
import types
from pathlib import Path

FROZEN_SCORER_SHA256 = "1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7"
ADAPTER_COMMIT = "a0e738bc03e515999659dda09c5ee76d08fb37df"
# Historical pins from a0e738bc:docs/research/WP-0015/astra/visual.py
HISTORICAL_ASSETS = {
    "System32/Windows.Media.Ocr.dll": "0db8e48e4f27055f7b7e45412761839b492f5b120b6245edadae61f3fe357ea1",
    "OCR/en-us/MsOcrRes.orp": "81771d772d77d541e33f3b37e94c81f8a6f87e0b75e933a2389dbcc55715b908",
}
HISTORICAL_ENGINE_VERSION = "10.0.26100.9278"
FAMILY_PINS = {
    "H": dict(source_sha256="e5270d9eca7bb902f692795949bfe718240bc0e3733d0a02508fef850497eca7",
              truth_sha256="91fd9ebc9cc5ae32cf4d66f4d139544fe7b6eec52a070803fa4208e7eb67e8ac",
              rasters_sha256="b6342013caf84cb3a0842834b36fd06ca870683b0e1f3c30f9239367562c3e39",
              pages=4, criticals=19, critical_lines=8, critical_cells=11, cells=20, lines=16, blanks=1,
              archive=dict(correct_cells=15, reference_cells=20, critical_values=19,
                           unflagged_critical_errors=8, correct_lines=13, reference_lines=16)),
    "A": dict(source_sha256="671e8e18d6cf84db671ea0487be8b197e535753dabac6c1561e169654d113c5b",
              truth_sha256="0ec7d6a7be2446409568d68d733636ba7de92e3a59fb40a6dde47fa581f99e6d",
              rasters_sha256="0559c970998d06575db35f51a073317a7e55308119b6e0c2433381bdacfde336",
              pages=60, criticals=252, critical_lines=108, critical_cells=144, cells=300, lines=288, blanks=22,
              archive=dict(correct_cells=235, reference_cells=300, critical_values=252,
                           unflagged_critical_errors=94, correct_lines=237, reference_lines=288)),
}
# Preregistered individual-evidence locations (family, scorer "at" key).
WITNESSES = {
    "W1": ("H", "page/2/table/1/row/2/col/1"),
    "W2": ("A", "page/60/table/1/row/2/col/2"),
    "W3": ("H", "page/1/line/2"),
    "W4": ("H", "page/2/line/2"),
}
ZERO_WORD_CELLS = {
    "Z1": ("A", "page/5/table/1/row/5/col/1"),
    "Z2": ("A", "page/15/table/1/row/4/col/2"),
    "Z3": ("A", "page/20/table/1/row/5/col/1"),
    "Z4": ("A", "page/30/table/1/row/3/col/2"),
    "Z5": ("A", "page/30/table/1/row/5/col/1"),
}
def load_pins(path=None):
    """H/A pins are built in; a coordinator-committed JSON adds fresh families (Stage 2) without code changes.
    Each added family needs truth_sha256 (the committed key digest), source_sha256, pages, criticals, cells, lines."""
    pins = {k: dict(v) for k, v in FAMILY_PINS.items()}
    if path:
        extra = read_json(path)
        for fam, v in extra.items():
            if fam in FAMILY_PINS:
                raise ValueError("historical H/A pins cannot be overridden")
            missing = {"truth_sha256", "source_sha256", "pages", "criticals", "cells", "lines"} - set(v)
            if missing:
                raise ValueError(f"pins for {fam} lack {sorted(missing)}")
            pins[fam] = dict(v)
    return pins


def pairs(specs):
    out = {}
    for spec in specs or []:
        k, v = spec.split("=", 1)
        if k in out:
            raise ValueError(f"duplicate {k}")
        out[k] = v
    return out


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def write_new(path, obj):
    """Exclusive-create JSON evidence write with fsync; never overwrites."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(obj, indent=1, ensure_ascii=True, allow_nan=False) + "\n").encode()
    with open(path, "xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    return sha256_bytes(data)


class Checks:
    """Ordered PASS/FAIL/NOT_RUN ledger. Every check keeps its observed value."""

    def __init__(self):
        self.rows = []

    def add(self, cid, ok, what, observed=None, scope=None, gating=True):
        state = "NOT_RUN" if ok is None else ("PASS" if ok else "FAIL")
        self.rows.append(dict(id=cid, state=state, gating=gating, check=what, observed=observed, scope=scope))
        return ok

    def summary(self):
        out = {}
        for r in self.rows:
            key = r["state"] if r["gating"] else "observation_" + r["state"]
            out[key] = out.get(key, 0) + 1
        return out

    def failed(self, gating_only=True):
        return [r["id"] for r in self.rows if r["state"] == "FAIL" and (r["gating"] or not gating_only)]


# ---------------------------------------------------------------- frozen scorer
class FrozenScorer:
    def __init__(self, path, python=sys.executable):
        self.path = Path(path).resolve()
        self.bytes = self.path.read_bytes()
        self.sha256 = sha256_bytes(self.bytes)
        if self.sha256 != FROZEN_SCORER_SHA256:
            raise ValueError(f"scorer SHA-256 {self.sha256} is not the frozen {FROZEN_SCORER_SHA256}")
        self.python = python
        self._module = None

    def run(self, truth, prediction, out, baseline=None):
        """Separate isolated process, exactly the frozen CLI. Returns (returncode, stderr, out sha)."""
        cmd = [self.python, "-I", "-B", str(self.path), str(truth), str(prediction), "--out", str(out)]
        if baseline is not None:
            cmd += ["--baseline", str(baseline)]
        if Path(out).exists():
            raise FileExistsError(out)
        p = subprocess.run(cmd, capture_output=True, text=True)
        sha = sha256_file(out) if Path(out).exists() else None
        return dict(cmd=cmd, returncode=p.returncode, stderr=p.stderr[-4000:], out=str(out), out_sha256=sha)

    def module(self):
        """In-process predicates (in_cell/on_line/layout/norm) from the hash-verified bytes, no bytecode."""
        if self._module is None:
            if sha256_bytes(self.bytes) != FROZEN_SCORER_SHA256:
                raise ValueError("scorer bytes changed")
            m = types.ModuleType("frozen_score")
            m.__file__ = str(self.path)
            prev = sys.dont_write_bytecode
            sys.dont_write_bytecode = True
            try:
                exec(compile(self.bytes, str(self.path), "exec"), m.__dict__)
            finally:
                sys.dont_write_bytecode = prev
            self._module = m
        return self._module


# ---------------------------------------------------------------- BMP (independent parser)
def read_bmp(path_or_bytes):
    """Return dict(width, height, bgra=opaque top-to-bottom BGRA bytes, meta). No Pillow involvement."""
    data = path_or_bytes if isinstance(path_or_bytes, (bytes, bytearray)) else Path(path_or_bytes).read_bytes()
    if data[:2] != b"BM":
        raise ValueError("not a BMP")
    file_size = struct.unpack_from("<I", data, 2)[0]
    offset = struct.unpack_from("<I", data, 10)[0]
    header = struct.unpack_from("<I", data, 14)[0]
    if header not in (40, 52, 56, 108, 124):
        raise ValueError(f"unsupported DIB header {header}")
    width, height, planes, bpp, compression, image_size = struct.unpack_from("<iiHHII", data, 18)
    if planes != 1 or width <= 0 or height == 0:
        raise ValueError("invalid BMP geometry")
    top_down = height < 0
    h = abs(height)
    masks = None
    if compression == 3:  # BI_BITFIELDS: RGB masks follow the 40-byte core (inside V2+ headers too)
        masks = struct.unpack_from("<III", data, 54)
        if bpp != 32 or masks != (0x00FF0000, 0x0000FF00, 0x000000FF):
            raise ValueError(f"unsupported bitfields {bpp} {masks}")
    elif compression != 0:
        raise ValueError(f"unsupported compression {compression}")
    if bpp not in (24, 32):
        raise ValueError(f"unsupported bpp {bpp}")
    bpp_bytes = bpp // 8
    stride = (width * bpp_bytes + 3) & ~3
    need = offset + stride * h
    if len(data) < need:
        raise ValueError("truncated BMP")
    rows = []
    alpha_values = set()
    for y in range(h):
        src_row = y if top_down else h - 1 - y
        row = data[offset + src_row * stride: offset + src_row * stride + width * bpp_bytes]
        if bpp == 24:
            out = bytearray(width * 4)
            out[0::4] = row[0::3]
            out[1::4] = row[1::3]
            out[2::4] = row[2::3]
            out[3::4] = b"\xff" * width
        else:
            out = bytearray(row)
            if len(alpha_values) < 3:
                alpha_values.update(set(row[3::4]))
            out[3::4] = b"\xff" * width
        rows.append(bytes(out))
    bgra = b"".join(rows)
    return dict(width=width, height=h, bgra=bgra,
                meta=dict(file_bytes=len(data), declared_size=file_size, offset=offset, dib_header=header,
                          bpp=bpp, compression=compression, top_down=top_down, stride=stride,
                          stored_alpha_sample=sorted(alpha_values)[:8]))


def write_bmp24(width, height, bgra, top_down=False):
    """Test-only constructed BMP writer (24-bit BI_RGB)."""
    stride = (width * 3 + 3) & ~3
    body = bytearray()
    order = range(height) if top_down else range(height - 1, -1, -1)
    for y in order:
        row = bgra[y * width * 4:(y + 1) * width * 4]
        packed = bytearray(width * 3)
        packed[0::3] = row[0::4]
        packed[1::3] = row[1::4]
        packed[2::3] = row[2::4]
        body += packed + b"\0" * (stride - width * 3)
    header = struct.pack("<2sIHHI", b"BM", 54 + len(body), 0, 0, 54)
    dib = struct.pack("<IiiHHIIiiII", 40, width, -height if top_down else height, 1, 24, 0, len(body), 2835, 2835, 0, 0)
    return header + dib + bytes(body)


def bgra_to_rgb(bgra):
    out = bytearray(len(bgra) // 4 * 3)
    out[0::3] = bgra[2::4]
    out[1::3] = bgra[1::4]
    out[2::3] = bgra[0::4]
    return bytes(out)


def slice_bgra(bgra, width, height, rect):
    """Independent half-open [l,t,r,b) slice of packed top-to-bottom BGRA; returns packed bytes."""
    l, t, r, b = rect
    if not all(type(v) is int for v in rect):
        raise ValueError("non-integer rectangle")
    if not (0 <= l < r <= width and 0 <= t < b <= height):
        raise ValueError("rectangle outside page")
    row_bytes = width * 4
    return b"".join(bgra[y * row_bytes + l * 4: y * row_bytes + r * 4] for y in range(t, b))


# ---------------------------------------------------------------- geometry
def project_pinned(box_px, width, height, points):
    """a0e738bc visual.layout projection: round(px*pt/size, 3), x with width, y with height."""
    return [round(x * points[i % 2] / (width, height)[i % 2], 3) for i, x in enumerate(box_px)]


def project_float(box_px, width, height, points):
    return [x * points[i % 2] / (width, height)[i % 2] for i, x in enumerate(box_px)]


def pt_rect_to_px(rect_pt, width, height, points):
    return [rect_pt[0] * width / points[0], rect_pt[1] * height / points[1],
            rect_pt[2] * width / points[0], rect_pt[3] * height / points[1]]


def centre(box):
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)


def contains_point(rect, pt):
    return rect[0] <= pt[0] < rect[2] and rect[1] <= pt[1] < rect[3]


def overlap_area(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def finite_box(b):
    return isinstance(b, list) and len(b) == 4 and all(type(v) in (int, float) and math.isfinite(v) for v in b)


# ---------------------------------------------------------------- rendering (independent input check)
def render_rgb_pages(pdf_bytes):
    """Generator: one 300-DPI PDFium RGB page at a time (pinned WP-0015 recipe, scale 300/72, to_pil RGB)."""
    import pypdfium2
    doc = pypdfium2.PdfDocument(pdf_bytes)
    try:
        for i in range(len(doc)):
            page = doc[i]
            try:
                points = list(page.get_size())
                bitmap = page.render(scale=300.0 / 72.0)
                try:
                    image = bitmap.to_pil().convert("RGB")
                finally:
                    bitmap.close()
            finally:
                page.close()
            row = dict(page=i + 1, width=image.width, height=image.height, points=points, rgb=image.tobytes())
            image.close()
            yield row
    finally:
        doc.close()


def page_count(pdf_bytes):
    import pypdfium2
    doc = pypdfium2.PdfDocument(pdf_bytes)
    try:
        return len(doc)
    finally:
        doc.close()


def file_version(path):
    """Fixed file version via version.dll (read-only)."""
    import ctypes
    from ctypes import wintypes
    ver = ctypes.WinDLL("version")
    size = ver.GetFileVersionInfoSizeW(str(path), None)
    if not size:
        return None
    buf = ctypes.create_string_buffer(size)
    if not ver.GetFileVersionInfoW(str(path), 0, size, buf):
        return None
    ptr, ln = ctypes.c_void_p(), wintypes.UINT()
    if not ver.VerQueryValueW(buf, "\\", ctypes.byref(ptr), ctypes.byref(ln)):
        return None
    ms, ls = struct.unpack_from("<II", ctypes.string_at(ptr.value, ln.value), 8)
    return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
