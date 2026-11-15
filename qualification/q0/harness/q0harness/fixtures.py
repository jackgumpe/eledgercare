"""Dev-only fixture access and stdlib derivation of predicted 300-DPI raster digests.

evaluation/generation/generate_corpus.py builds each v1-raster300 PDF by rendering the
v0-clean PDF bytes with pypdfium2 5.15.2 ``page.render(scale=300/72).to_pil().convert("RGB")``
and embedding ``img.tobytes()`` losslessly as one FlateDecode /DeviceRGB image XObject per
page (pdf_writer.serialize_pdf). Inflating those streams therefore yields the exact RGB
bytes the frozen Q0 render contract is predicted to produce for the v0-clean parent. This
is a corpus-derived PREDICTION; the released stage must render and match it or fail closed.
"""

from __future__ import annotations

import re
import zlib
from pathlib import Path

from .hashing import git_blob_sha1_bytes, sha256_bytes
from .outcome import Q0Failure
from .protocol import REPO_ROOT, check_repo_path_allowed

_OBJ = re.compile(rb"(?m)^(\d+) 0 obj\n")


def read_verified_fixture(fixture: dict, repo_root: Path = REPO_ROOT) -> bytes:
    """Read a frozen dev fixture once and verify size, SHA-256 and Git blob before any use."""
    rel = check_repo_path_allowed(fixture["path"])
    data = (repo_root / rel).read_bytes()
    got = {"size": len(data), "sha256": sha256_bytes(data), "git_blob_oid": git_blob_sha1_bytes(data)}
    want = {"size": fixture["size_bytes"], "sha256": fixture["sha256"], "git_blob_oid": fixture["git_blob_oid"]}
    if got != want:
        raise Q0Failure("HASH_MISMATCH", f"fixture {fixture['fixture_id']} digest mismatch", {"got": got, "want": want})
    return data


def _objects(pdf: bytes) -> dict[int, bytes]:
    starts = [(int(m.group(1)), m.end()) for m in _OBJ.finditer(pdf)]
    objs = {}
    for i, (num, start) in enumerate(starts):
        end = pdf.find(b"\nendobj\n", start)
        if end < 0:
            raise ValueError(f"object {num} not terminated")
        if num in objs:
            raise ValueError(f"duplicate object {num}")
        objs[num] = pdf[start:end]
    return objs


def extract_page_rgb_streams(pdf: bytes) -> list[dict]:
    """Return per-page (width, height, raw RGB) of the single image XObject on each page, in /Kids order."""
    objs = _objects(pdf)
    catalog = objs[1]
    m = re.search(rb"/Pages (\d+) 0 R", catalog)
    pages_obj = objs[int(m.group(1))]
    kids = [int(k) for k in re.findall(rb"(\d+) 0 R", re.search(rb"/Kids \[([^\]]*)\]", pages_obj).group(1))]
    count = int(re.search(rb"/Count (\d+)", pages_obj).group(1))
    if count != len(kids):
        raise ValueError("page count mismatch")
    out = []
    for page_no, kid in enumerate(kids, start=1):
        page = objs[kid]
        if not page.startswith(b"<< /Type /Page "):
            raise ValueError(f"page object {kid} malformed")
        xobjs = re.findall(rb"/(Im\d+) (\d+) 0 R", re.search(rb"/XObject << ([^>]*) >>", page).group(1))
        if len(xobjs) != 1:
            raise ValueError(f"page {page_no} has {len(xobjs)} image XObjects; expected exactly 1")
        img = objs[int(xobjs[0][1])]
        hdr = re.match(rb"<< /Type /XObject /Subtype /Image /Width (\d+) /Height (\d+) /ColorSpace /DeviceRGB "
                       rb"/BitsPerComponent 8 /Filter /FlateDecode /Length (\d+) >>\nstream\n", img)
        if not hdr:
            raise ValueError(f"page {page_no} image header not the pdf_writer RGB form")
        w, h, length = (int(x) for x in hdr.groups())
        body = img[hdr.end():hdr.end() + length]
        if len(body) != length or img[hdr.end() + length:] != b"\nendstream":
            raise ValueError(f"page {page_no} stream length mismatch")
        rgb = zlib.decompress(body)
        if len(rgb) != w * h * 3:
            raise ValueError(f"page {page_no} RGB length {len(rgb)} != {w}*{h}*3")
        out.append({"page": page_no, "width": w, "height": h, "rgb": rgb})
    return out


def derive_predicted_rasters(fixture: dict, repo_root: Path = REPO_ROOT) -> list[dict]:
    src = fixture["raster_derivation"]
    rel = check_repo_path_allowed(src["v1_raster300_path"])
    data = (repo_root / rel).read_bytes()
    if sha256_bytes(data) != src["v1_raster300_sha256"]:
        raise Q0Failure("HASH_MISMATCH", f"raster-derivation source digest mismatch: {rel}")
    pages = extract_page_rgb_streams(data)
    if len(pages) != fixture["page_count"]:
        raise Q0Failure("RENDER_CONTRACT_MISMATCH", "derivation page count differs from fixture page count")
    return [{"page": p["page"], "width": p["width"], "height": p["height"], "rgb_sha256": sha256_bytes(p["rgb"])}
            for p in pages]


def verify_rendered_pages(fixture: dict, rendered: list[tuple[int, int, bytes]]) -> list[dict]:
    """Compare actual rendered (width, height, RGB bytes) per page with the frozen raster contract."""
    want = fixture["raster"]
    got = [{"page": i, "width": w, "height": h, "rgb_sha256": sha256_bytes(b), "rgb_bytes": len(b)}
           for i, (w, h, b) in enumerate(rendered, start=1)]
    if len(got) != len(want):
        raise Q0Failure("RENDER_CONTRACT_MISMATCH", f"{fixture['fixture_id']}: {len(got)} pages rendered, {len(want)} frozen")
    for g, w in zip(got, want):
        if (g["width"], g["height"], g["rgb_sha256"]) != (w["width"], w["height"], w["rgb_sha256"]) \
                or g["rgb_bytes"] != w["width"] * w["height"] * 3:
            raise Q0Failure("RENDER_CONTRACT_MISMATCH", f"{fixture['fixture_id']} page {g['page']} differs",
                            {"got": g, "want": w})
    return got
