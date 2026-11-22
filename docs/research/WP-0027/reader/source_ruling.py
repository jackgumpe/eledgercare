"""Verify structural ink on the two admitted ordinary H0 control pages directly from PDF paths."""
from contextlib import closing
import ctypes
import math
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
from PIL import ImageChops

from reader import check_hash, digest, require

PDF = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0024/custody/public/h0/pdf/34054347f091c087a39efe17.pdf")
PDF_SHA = "675367788d2b872511d05b704b98069e8b636d02d07d78095cc4bbeab3e63d5b"
# Each pin authenticates the archived native digest, complete ordered inputs, and glyph proof
# independently extracted from the pinned PDF. Only the named page of that exact control qualifies.
H0 = {
    "2cf08af63f9b8eed8db037ac4364298d3a4304c1c7715dc96731349ce6cafd8d": ("b01w01H", 1),
    "5a4002b63e3ce60323df8cd2c6999f99a696e64e4fdcbdb2f85c8dc873b0ff5d": ("b01w02H", 4),
}


def path_segment(obj):
    require(obj.type == pdfium_c.FPDF_PAGEOBJ_PATH and pdfium_c.FPDFPath_CountSegments(obj) == 2,
            "unknown_pdf_graphic")
    points = []
    for i, expected in enumerate((pdfium_c.FPDF_SEGMENT_MOVETO, pdfium_c.FPDF_SEGMENT_LINETO)):
        seg = pdfium_c.FPDFPath_GetPathSegment(obj, i)
        x, y = ctypes.c_float(), ctypes.c_float()
        require(pdfium_c.FPDFPathSegment_GetType(seg) == expected
                and pdfium_c.FPDFPathSegment_GetPoint(seg, ctypes.byref(x), ctypes.byref(y)), "unknown_pdf_path")
        points.append(obj.get_matrix().on_point(x.value, y.value))
    require(points[0] != points[1] and (points[0][0] == points[1][0] or points[0][1] == points[1][1]),
            "non_axis_aligned_pdf_path")
    return points


def render(page):
    with closing(page.render(scale=math.nextafter(300/72, 0))) as bitmap:
        return bitmap.to_pil().convert("RGB")


def verify_h0_ruling(binding, pin, record, image, glyph_clips):
    if binding["document_sha256"] != PDF_SHA or H0.get(pin) != (binding["call"], record["page"]):
        return None
    original = PDF.read_bytes()
    check_hash(original, PDF_SHA, "development_ruling_pdf")
    with pdfium.PdfDocument(original) as doc, closing(doc[record["page"]-1]) as page:
        whole = render(page)
        require(whole.size == image.size and ImageChops.difference(whole, image).getbbox() is None,
                "development_rerender_changed")
        paths = []
        text_objects = 0
        for obj in list(page.get_objects(max_depth=1)):
            if obj.type == pdfium_c.FPDF_PAGEOBJ_TEXT:
                page.remove_obj(obj)
                obj.close()
                text_objects += 1
            else:
                paths.append(path_segment(obj))
        require(paths and text_objects, "development_ruling_layers")
        only_paths = render(page)
    full_layer_hash = digest(only_paths.tobytes())
    observed = image.copy()
    for box in glyph_clips:
        observed.paste((255,255,255), box)
        only_paths.paste((255,255,255), box)
    require(ImageChops.difference(observed, only_paths).getbbox() is None, "unattributed_source_pixels")
    return dict(document_sha256=PDF_SHA, page=record["page"], full_rerender_rgb_sha256=digest(whole.tobytes()),
                source_text_objects_removed=text_objects, axis_aligned_segments_pt=paths,
                nontext_layer_rgb_sha256=full_layer_hash, actual_residual_rgb_sha256=digest(observed.tobytes()),
                path_residual_rgb_sha256=digest(only_paths.tobytes()), differing_residual_rgb_pixels=0)
