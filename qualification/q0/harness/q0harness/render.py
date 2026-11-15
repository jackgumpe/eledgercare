"""Frozen PDF-to-RGB contract: pypdfium2==5.15.2 / PDFium 159.0.8149.0,
page.render(scale=300.0 / 72.0).to_pil().convert('RGB') on verified PDF bytes."""

from __future__ import annotations

from .outcome import Q0Failure

SCALE = 300.0 / 72.0


def renderer_identity(pdfium, dist_version) -> dict:
    """pdfium: the imported pypdfium2 module. dist_version: importlib.metadata.version."""
    ident = {"distribution_version": dist_version("pypdfium2")}
    ver = getattr(pdfium, "version", None)
    for attr in ("PYPDFIUM_INFO", "PDFIUM_INFO"):
        info = getattr(ver, attr, None)
        ident[attr] = None if info is None else str(info)
    ident["api_version_attr"] = getattr(pdfium, "V_PYPDFIUM2", None) or getattr(pdfium, "__version__", None)
    return ident


def check_renderer(ident: dict, protocol: dict) -> None:
    r = protocol["renderer"]
    if ident["distribution_version"] != r["version"]:
        raise Q0Failure("RENDER_CONTRACT_MISMATCH", f"pypdfium2 {ident['distribution_version']} != {r['version']}")
    pdfium_info = ident.get("PDFIUM_INFO") or ""
    # The exact string form of PDFIUM_INFO in 5.15.2 is unverified on this host (not installed);
    # the released CPU preflight records it and fails closed if the pinned version is absent.
    if r["pdfium_version"] not in pdfium_info:
        raise Q0Failure("RENDER_CONTRACT_MISMATCH", "bundled PDFium identity not verifiable as the pinned build", ident)


def render_pdf_bytes(pdfium, pdf_bytes: bytes) -> list:
    """Return PIL RGB images in page order. The PIL objects are handed to infer_multi unchanged."""
    doc = pdfium.PdfDocument(pdf_bytes)
    images = []
    try:
        for i in range(len(doc)):
            page = doc[i]
            try:
                img = page.render(scale=SCALE).to_pil().convert("RGB")
            finally:
                page.close()
            if img.mode != "RGB":
                raise Q0Failure("RENDER_CONTRACT_MISMATCH", f"page {i + 1} mode {img.mode}")
            images.append(img)
    finally:
        doc.close()
    return images


def raster_tuples(images) -> list[tuple[int, int, bytes]]:
    return [(im.width, im.height, im.tobytes()) for im in images]
