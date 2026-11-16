"""Single-read hash-verified 300-DPI PDFium RGB rendering for F2."""

from __future__ import annotations

from pathlib import Path

from .protocol import (
    MAX_PAGES_PROFILE,
    MAX_RASTER_AXIS_PX,
    RENDER_DPI,
    RENDER_SCALE,
    WorkerError,
    sha256_bytes,
)
from .verify_runtime import is_reparse_or_link


def verify_renderer_identity(pdfium_module, dist_version_fn, lock_doc: dict) -> str:
    want = lock_doc["renderer"]
    dist_ver = dist_version_fn("pypdfium2")
    if dist_ver != want["version"]:
        raise WorkerError("dependency_lock_mismatch", f"pypdfium2 version {dist_ver} != {want['version']}")
    ver_obj = getattr(pdfium_module, "version", None)
    pdfium_info = str(getattr(ver_obj, "PDFIUM_INFO", "") or "")
    if want["pdfium_version"] not in pdfium_info:
        raise WorkerError("dependency_lock_mismatch", "Bundled PDFium build does not match pinned version.")
    return f"pypdfium2=={dist_ver};pdfium={want['pdfium_version']};dpi={RENDER_DPI};rgb"


def read_and_render_pdf(
    pdfium_module,
    pdf_path: Path,
    *,
    expected_sha256: str,
    expected_byte_length: int,
    expected_page_count: int,
) -> tuple[list, list[dict]]:
    if expected_page_count < 1 or expected_page_count > MAX_PAGES_PROFILE:
        raise WorkerError("input_integrity_failed", f"Expected page count {expected_page_count} outside 1..3.")
    if not pdf_path.is_file() or is_reparse_or_link(pdf_path):
        raise WorkerError("input_integrity_failed", "Materialized input PDF is missing or symlinked.")

    pdf_bytes = pdf_path.read_bytes()
    actual_sha = sha256_bytes(pdf_bytes)
    if len(pdf_bytes) != expected_byte_length or actual_sha != expected_sha256.lower():
        raise WorkerError("input_integrity_failed", "Materialized PDF length or SHA-256 disagreed with request.")

    try:
        doc = pdfium_module.PdfDocument(pdf_bytes)
    except Exception as exc:
        raise WorkerError("render_failed", f"PDFium failed to open PDF: {type(exc).__name__}") from exc

    images = []
    page_summaries: list[dict] = []
    try:
        actual_pages = len(doc)
        if actual_pages != expected_page_count:
            raise WorkerError(
                "input_integrity_failed",
                f"PDFium page count {actual_pages} disagreed with admitted page count {expected_page_count}.",
            )
        for idx in range(actual_pages):
            page = doc[idx]
            try:
                pil_img = page.render(scale=RENDER_SCALE).to_pil().convert("RGB")
            except Exception as exc:
                raise WorkerError(
                    "render_failed",
                    f"PDFium failed rendering page {idx + 1}: {type(exc).__name__}",
                ) from exc
            finally:
                page.close()

            if pil_img.mode != "RGB":
                raise WorkerError("render_failed", f"Rendered page {idx + 1} mode {pil_img.mode} != RGB.")
            w, h = pil_img.width, pil_img.height
            if w < 1 or h < 1 or w > MAX_RASTER_AXIS_PX or h > MAX_RASTER_AXIS_PX:
                raise WorkerError(
                    "render_failed",
                    f"Rendered page {idx + 1} dimensions {w}x{h} outside safe 1..{MAX_RASTER_AXIS_PX} bounds.",
                )
            images.append(pil_img)
            page_summaries.append({
                "page_number": idx + 1,
                "width_px": w,
                "height_px": h,
                "rgb_sha256": sha256_bytes(pil_img.tobytes()),
            })
    finally:
        doc.close()

    return images, page_summaries
