"""Deterministic source-first synthetic corpus generator for eLedgerCare WP-0004 / 004.

Reads static declarative JSON specs from evaluation/synthetic/sources/, computes exact
Decimal (ROUND_HALF_UP) expected values, writes separable expected JSONs, renders
8 clean vector PDFs (12p), 8 300-DPI image-only PDFs (12p), 8 signed-skew 300-DPI
image-only PDFs (12p), and 2 <8%-area hybrid vector+raster negative controls (4p)
for an exact total of 26 PDFs / 40 pages, plus evaluation/manifests/corpus-manifest.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from PIL import Image, ImageDraw, ImageFont
import pypdfium2 as pdfium

THIS_DIR = pathlib.Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from pdf_writer import (  # noqa: E402
    LETTER_HEIGHT_PT,
    LETTER_WIDTH_PT,
    PdfPageCanvas,
    build_image_only_pdf,
    serialize_pdf,
    wrap_text_deterministic,
)

CENTS = Decimal("0.01")
RATE_PREC = Decimal("0.0001")
ROUND_MODE = ROUND_HALF_UP
RASTER_DPI = 300


def fmt_usd(val: Decimal) -> str:
    q = val.quantize(CENTS, rounding=ROUND_MODE)
    if q == Decimal("0.00"):
        q = Decimal("0.00")
    if q < Decimal("0.00"):
        return f"-${abs(q):,.2f}"
    return f"${q:,.2f}"


def fmt_dec2(val: Decimal) -> str:
    q = val.quantize(CENTS, rounding=ROUND_MODE)
    if q == Decimal("0.00"):
        q = Decimal("0.00")
    return f"{q:.2f}"


def fmt_pct(rate: Decimal) -> str:
    pct = (rate * Decimal("100")).quantize(CENTS, rounding=ROUND_MODE)
    return f"{pct:.2f}%"


def git_blob_oid(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_hybrid_stamp_rgb(label: str, text: str, width_px: int, height_px: int) -> bytes:
    """Create a deterministic 300-DPI RGB stamp bitmap using Pillow's bundled font."""
    img = Image.new("RGB", (width_px, height_px), (255, 250, 240))
    draw = ImageDraw.Draw(img)
    # Crisp double border in dark crimson/amber so human & VLM reviewers see a distinct stamp box
    draw.rectangle([2, 2, width_px - 3, height_px - 3], outline=(150, 28, 28), width=4)
    draw.rectangle([10, 10, width_px - 11, height_px - 11], outline=(150, 28, 28), width=2)
    font_hdr = ImageFont.load_default(size=24)
    font_body = ImageFont.load_default(size=25)
    draw.text((22, 20), f"[{label}]", fill=(150, 28, 28), font=font_hdr)
    draw.text((22, 62), text, fill=(20, 20, 25), font=font_body)
    return img.tobytes()


def compute_invoice_accounting(spec: dict[str, Any]) -> dict[str, Any]:
    tax_rate = Decimal(spec["tax_rate"]).quantize(RATE_PREC, rounding=ROUND_MODE)
    prev_bal = Decimal(spec["previous_balance"]).quantize(CENTS, rounding=ROUND_MODE)
    payments = Decimal(spec["payments_credits_applied"]).quantize(CENTS, rounding=ROUND_MODE)

    computed_rows: list[dict[str, Any]] = []
    for item in spec["line_items"]:
        qty = Decimal(item["quantity"]).quantize(CENTS, rounding=ROUND_MODE)
        uprice = Decimal(item["unit_price"]).quantize(CENTS, rounding=ROUND_MODE)
        drate = Decimal(item["discount_rate"]).quantize(RATE_PREC, rounding=ROUND_MODE)
        if drate < Decimal("0") or drate >= Decimal("1"):
            raise ValueError(f"Invalid discount_rate {drate} on {item['row_id']}")
        if uprice < Decimal("0") and (drate != Decimal("0") or item["is_taxable"]):
            raise ValueError(f"Credit row {item['row_id']} must have 0 discount and is_taxable=False")

        gross = (qty * uprice).quantize(CENTS, rounding=ROUND_MODE)
        disc_amt = (gross * drate).quantize(CENTS, rounding=ROUND_MODE)
        net = (gross - disc_amt).quantize(CENTS, rounding=ROUND_MODE)
        tax_flag = "T" if item["is_taxable"] else "N"
        qty_unit_printed = f"{fmt_dec2(qty)} {item['unit']}"

        computed_rows.append(
            {
                "row_id": item["row_id"],
                "page_number": item["page_number"],
                "sku": item["sku"],
                "description": item["description"],
                "quantity_norm": fmt_dec2(qty),
                "unit": item["unit"],
                "qty_unit_printed": qty_unit_printed,
                "unit_price_norm": fmt_dec2(uprice),
                "unit_price_printed": fmt_usd(uprice),
                "discount_rate_norm": f"{drate:.4f}",
                "discount_rate_printed": fmt_pct(drate),
                "gross_line_norm": fmt_dec2(gross),
                "gross_line_printed": fmt_usd(gross),
                "line_discount_norm": fmt_dec2(disc_amt),
                "line_discount_printed": fmt_usd(disc_amt),
                "is_taxable": bool(item["is_taxable"]),
                "tax_flag_printed": tax_flag,
                "net_line_norm": fmt_dec2(net),
                "net_line_printed": fmt_usd(net),
            }
        )

    subtotal = sum((Decimal(r["net_line_norm"]) for r in computed_rows), Decimal("0.00"))
    taxable_subtotal = sum(
        (Decimal(r["net_line_norm"]) for r in computed_rows if r["is_taxable"]), Decimal("0.00")
    )
    if taxable_subtotal < Decimal("0.00"):
        raise ValueError(f"Negative taxable_subtotal: {taxable_subtotal}")

    tax_amount = (taxable_subtotal * tax_rate).quantize(CENTS, rounding=ROUND_MODE)
    computed_fees: list[dict[str, Any]] = []
    non_taxable_fees = Decimal("0.00")
    for fee in spec.get("fees", []):
        if fee.get("is_taxable", False):
            raise ValueError("Declared post-tax fees must be non-taxable")
        f_amt = Decimal(fee["amount"]).quantize(CENTS, rounding=ROUND_MODE)
        non_taxable_fees += f_amt
        computed_fees.append(
            {
                "fee_id": fee["fee_id"],
                "label": fee["label"],
                "amount_norm": fmt_dec2(f_amt),
                "amount_printed": fmt_usd(f_amt),
            }
        )

    invoice_total = (subtotal + tax_amount + non_taxable_fees).quantize(CENTS, rounding=ROUND_MODE)
    amount_due = (invoice_total + prev_bal - payments).quantize(CENTS, rounding=ROUND_MODE)

    return {
        "convention": spec["convention"],
        "currency": spec["currency"],
        "printed_rule_notice": spec["printed_rule_notice"],
        "rows": computed_rows,
        "fees": computed_fees,
        "summary": {
            "subtotal": {"normalized_value": fmt_dec2(subtotal), "printed_text": fmt_usd(subtotal)},
            "taxable_subtotal": {
                "normalized_value": fmt_dec2(taxable_subtotal),
                "printed_text": fmt_usd(taxable_subtotal),
            },
            "tax_rate": {"normalized_value": f"{tax_rate:.4f}", "printed_text": spec["tax_rate_printed"]},
            "tax_amount": {"normalized_value": fmt_dec2(tax_amount), "printed_text": fmt_usd(tax_amount)},
            "non_taxable_fees": {
                "normalized_value": fmt_dec2(non_taxable_fees),
                "printed_text": fmt_usd(non_taxable_fees),
            },
            "invoice_total": {"normalized_value": fmt_dec2(invoice_total), "printed_text": fmt_usd(invoice_total)},
            "previous_balance": {"normalized_value": fmt_dec2(prev_bal), "printed_text": fmt_usd(prev_bal)},
            "payments_credits_applied": {
                "normalized_value": fmt_dec2(payments),
                "printed_text": fmt_usd(payments),
            },
            "amount_due": {"normalized_value": fmt_dec2(amount_due), "printed_text": fmt_usd(amount_due)},
        },
    }


def draw_work_order_or_packet(
    src: dict[str, Any],
    include_hybrid: bool = False,
) -> tuple[list[PdfPageCanvas], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Render F01, F02, F03 (1p work orders) or F08 (3p mitigation packet)."""
    page_count = src["page_count"]
    canvases = [PdfPageCanvas() for _ in range(page_count)]
    expected_fields: list[dict[str, Any]] = []
    expected_absences: list[dict[str, Any]] = []
    expected_tables: list[dict[str, Any]] = []

    sentinels_by_page = {s["page_number"]: s for s in src.get("page_sentinels", [])}

    # Page 1 top banner
    c1 = canvases[0]
    b = src["banner"]
    c1.rect_fill_stroke(40, 712, 532, 50, fill_rgb=(0.93, 0.95, 0.98), stroke_rgb=(0.18, 0.24, 0.34), line_width=0.8)
    c1.draw_text(b["organization"], 48, 747, font_key="bold", size_pt=9.5, max_width_pt=360)
    c1.draw_text(b["document_title"], 48, 732, font_key="bold", size_pt=11.5, max_width_pt=400)
    c1.draw_text(b["subtitle"].strip(), 48, 718, font_key="regular", size_pt=8.0, max_width_pt=516)
    c1.draw_text(b["contact_line"], 40, 26, font_key="regular", size_pt=7.2, max_width_pt=532, align="center")

    y_cursor_by_page = {p: 702.0 for p in range(1, page_count + 1)}

    # Multi-page sentinel ribbon on every page if multi-page
    if sentinels_by_page:
        for p_idx in range(1, page_count + 1):
            cp = canvases[p_idx - 1]
            s = sentinels_by_page[p_idx]
            if p_idx > 1:
                cp.rect_fill_stroke(
                    40, 734, 532, 28, fill_rgb=(0.93, 0.95, 0.98), stroke_rgb=(0.18, 0.24, 0.34), line_width=0.7
                )
                cp.draw_text(b["organization"], 48, 749, font_key="bold", size_pt=8.5, max_width_pt=270)
                cp.draw_text(b["document_title"], 48, 738, font_key="regular", size_pt=8.0, max_width_pt=270)
                cp.draw_text(b["contact_line"], 40, 26, font_key="regular", size_pt=7.2, max_width_pt=532, align="center")
                y_top = 726.0
            else:
                y_top = y_cursor_by_page[1]

            cp.rect_fill_stroke(40, y_top - 18, 532, 18, fill_rgb=(0.88, 0.91, 0.95), stroke_rgb=(0.20, 0.25, 0.32))
            ribbon = (
                f"Packet ID: {s['repeated_doc_id']}   |   Auth Ref: {s['repeated_auth_id']}   |   "
                f"{s['page_label']}   |   PG-ANCHOR: {s['sentinel_id']}"
            )
            cp.draw_text(ribbon, 46, y_top - 13, font_key="mono_bold", size_pt=8.0, max_width_pt=520)
            y_cursor_by_page[p_idx] = y_top - 26.0

    # Two-column metadata header on Page 1
    y1 = y_cursor_by_page[1]
    cols = src["header_columns"]
    max_rows = max(len(col["fields"]) for col in cols)
    box_h = 18.0 + max_rows * 17.0 + 4.0
    col_positions = [(40.0, 260.0), (312.0, 260.0)]
    for col, (cx, cw) in zip(cols, col_positions):
        c1.rect_fill_stroke(cx, y1 - box_h, cw, box_h, fill_rgb=(0.99, 0.99, 1.0), stroke_rgb=(0.22, 0.26, 0.32))
        c1.rect_fill_stroke(cx, y1 - 16, cw, 16, fill_rgb=(0.87, 0.90, 0.94), stroke_rgb=(0.22, 0.26, 0.32))
        c1.draw_text(col["group_title"], cx + 6, y1 - 12, font_key="bold", size_pt=8.0, max_width_pt=cw - 12)
        fy = y1 - 30.0
        for fld in col["fields"]:
            lbl = f"{fld['label']}:"
            c1.draw_text(lbl, cx + 6, fy, font_key="bold", size_pt=7.8, max_width_pt=108)
            val_x = cx + 114
            val_w = cw - 120
            c1.line(val_x, fy - 2, val_x + val_w, fy - 2, stroke_rgb=(0.65, 0.68, 0.74), line_width=0.4)
            if fld["is_absent"]:
                expected_absences.append(
                    {
                        "field_id": fld["field_id"],
                        "label_printed": fld["label"],
                        "page_number": 1,
                        "expected_state": "absent_blank",
                    }
                )
            else:
                bbox = c1.draw_text(fld["printed_text"], val_x, fy, font_key="regular", size_pt=8.0, max_width_pt=val_w)
                expected_fields.append(
                    {
                        "field_id": fld["field_id"],
                        "label_printed": fld["label"],
                        "page_number": 1,
                        "value_type": fld["value_type"],
                        "printed_text": fld["printed_text"],
                        "normalized_value": fld["normalized_value"],
                        "bbox_pt": list(bbox),
                    }
                )
            fy -= 17.0
    y1 -= box_h + 8.0

    # Optional checkbox strip on Page 1
    if src.get("checkbox_strip"):
        c1.rect_fill_stroke(40, y1 - 20, 532, 20, fill_rgb=(0.96, 0.97, 0.99), stroke_rgb=(0.25, 0.28, 0.34))
        items = src["checkbox_strip"]
        slot_w = 524.0 / len(items)
        for idx, cb in enumerate(items):
            sx = 45.0 + idx * slot_w
            disp = f"{cb['label']} {cb['printed_text']}"
            bbox = c1.draw_text(disp, sx, y1 - 13.5, font_key="mono_bold", size_pt=6.8, max_width_pt=slot_w - 3)
            expected_fields.append(
                {
                    "field_id": cb["field_id"],
                    "label_printed": cb["label"],
                    "page_number": 1,
                    "value_type": "boolean_mark",
                    "printed_text": cb["printed_text"],
                    "normalized_value": cb["normalized_value"],
                    "bbox_pt": list(bbox),
                }
            )
        y1 -= 28.0

    y_cursor_by_page[1] = y1

    # Prose blocks
    for pb in src.get("prose_blocks", []):
        pno = pb["page_number"]
        cp = canvases[pno - 1]
        yp = y_cursor_by_page[pno]
        lines = wrap_text_deterministic(pb["printed_text"], "regular", 8.0, 516.0)
        pb_h = 16.0 + len(lines) * 11.0 + 6.0
        cp.rect_fill_stroke(40, yp - pb_h, 532, pb_h, fill_rgb=(1.0, 1.0, 1.0), stroke_rgb=(0.25, 0.28, 0.34))
        cp.rect_fill_stroke(40, yp - 15, 532, 15, fill_rgb=(0.90, 0.92, 0.96), stroke_rgb=(0.25, 0.28, 0.34))
        cp.draw_text(pb["label"], 46, yp - 11, font_key="bold", size_pt=7.8, max_width_pt=520)
        ly = yp - 26.0
        first_bbox = None
        last_bbox = None
        for ln in lines:
            bb = cp.draw_text(ln, 48, ly, font_key="regular", size_pt=8.0, max_width_pt=516)
            if first_bbox is None:
                first_bbox = bb
            last_bbox = bb
            ly -= 11.0
        assert first_bbox is not None and last_bbox is not None
        expected_fields.append(
            {
                "field_id": pb["field_id"],
                "label_printed": pb["label"],
                "page_number": pno,
                "value_type": "text",
                "printed_text": pb["printed_text"],
                "normalized_value": pb["normalized_value"],
                "bbox_pt": [48.0, last_bbox[1], 564.0, first_bbox[3]],
            }
        )
        y_cursor_by_page[pno] = yp - pb_h - 8.0

    # Tables (supports multi-page tables!)
    for tbl in src.get("tables", []):
        col_defs = tbl["columns"]
        total_w = sum(c["width_pt"] for c in col_defs)
        if abs(total_w - 532.0) > 0.01:
            raise ValueError(f"Table {tbl['table_id']} width={total_w} != 532.0")

        rows_by_page: dict[int, list[dict[str, Any]]] = {}
        for r in tbl["rows"]:
            rows_by_page.setdefault(r["page_number"], []).append(r)

        exp_rows: list[dict[str, Any]] = []
        for pno in tbl["page_numbers"]:
            cp = canvases[pno - 1]
            yp = y_cursor_by_page[pno]
            title_suffix = " (CONTINUED)" if pno in tbl.get("repeated_header_pages", []) else ""
            cp.draw_text(tbl["title"] + title_suffix, 40, yp - 10, font_key="bold", size_pt=8.3, max_width_pt=532)
            yp -= 14.0

            # Header row
            hdr_h = 16.0
            cp.rect_fill_stroke(40, yp - hdr_h, 532, hdr_h, fill_rgb=(0.85, 0.89, 0.94), stroke_rgb=(0.20, 0.24, 0.30))
            cx = 40.0
            for cdef in col_defs:
                cw = cdef["width_pt"]
                cp.line(cx, yp, cx, yp - hdr_h, stroke_rgb=(0.20, 0.24, 0.30))
                cp.draw_text(
                    cdef["header"], cx + 4, yp - 11.5, font_key="bold", size_pt=7.6, max_width_pt=cw - 8, align=cdef["align"]
                )
                cx += cw
            yp -= hdr_h

            for r in rows_by_page.get(pno, []):
                cell_wrapped: dict[str, list[str]] = {}
                max_ln = 1
                for cdef in col_defs:
                    cid = cdef["col_id"]
                    cw = cdef["width_pt"]
                    ptxt = r["cells"][cid]["printed_text"]
                    wlines = wrap_text_deterministic(ptxt, "regular", 7.4, cw - 8.0)
                    cell_wrapped[cid] = wlines
                    if len(wlines) > max_ln:
                        max_ln = len(wlines)
                row_h = max(16.5, 6.0 + max_ln * 9.5)
                cp.rect_fill_stroke(40, yp - row_h, 532, row_h, fill_rgb=(1.0, 1.0, 1.0), stroke_rgb=(0.35, 0.38, 0.44), line_width=0.45)
                cx = 40.0
                exp_cells: dict[str, Any] = {}
                for cdef in col_defs:
                    cid = cdef["col_id"]
                    cw = cdef["width_pt"]
                    cp.line(cx, yp, cx, yp - row_h, stroke_rgb=(0.35, 0.38, 0.44), line_width=0.45)
                    cell = r["cells"][cid]
                    wlines = cell_wrapped[cid]
                    cly = yp - 11.0
                    for wln in wlines:
                        cp.draw_text(
                            wln,
                            cx + 4,
                            cly,
                            font_key="regular",
                            size_pt=7.4,
                            max_width_pt=cw - 8,
                            align=cdef["align"],
                        )
                        cly -= 9.5
                    exp_cells[cid] = {
                        "printed_text": cell["printed_text"],
                        "normalized_value": cell["normalized_value"],
                        "value_type": cdef["value_type"],
                    }
                    cx += cw
                exp_rows.append({"row_id": r["row_id"], "page_number": pno, "cells": exp_cells})
                yp -= row_h

            if pno < max(tbl["page_numbers"]):
                cp.draw_text(
                    f"[Table {tbl['table_id']} continues on Page {pno + 1}]",
                    40,
                    yp - 12,
                    font_key="mono",
                    size_pt=7.5,
                    max_width_pt=532,
                )
                yp -= 18.0
            y_cursor_by_page[pno] = yp - 10.0

        expected_tables.append(
            {
                "table_id": tbl["table_id"],
                "page_numbers": tbl["page_numbers"],
                "repeated_header_pages": tbl.get("repeated_header_pages", []),
                "column_ids": [c["col_id"] for c in col_defs],
                "rows": exp_rows,
            }
        )

    # Sign-off block on final page
    last_p = page_count
    clast = canvases[last_p - 1]
    yl = y_cursor_by_page[last_p]
    sfields = src.get("signoff_fields", [])
    if sfields:
        sw = 520.0 / len(sfields)
        wrapped_sf = [wrap_text_deterministic(sf["printed_text"], "regular", 7.3, sw - 8.0) for sf in sfields]
        max_sf_lines = max(len(w) for w in wrapped_sf)
        sh = max(34.0, 16.0 + max_sf_lines * 10.0 + 4.0)
        clast.rect_fill_stroke(40, yl - sh, 532, sh, fill_rgb=(0.95, 0.97, 0.99), stroke_rgb=(0.20, 0.24, 0.30))
        for idx, (sf, wlines) in enumerate(zip(sfields, wrapped_sf)):
            sx = 46.0 + idx * sw
            clast.draw_text(sf["label"] + ":", sx, yl - 11.5, font_key="bold", size_pt=7.2, max_width_pt=sw - 8)
            sly = yl - 23.0
            first_bb = None
            last_bb = None
            for wln in wlines:
                bb = clast.draw_text(wln, sx, sly, font_key="regular", size_pt=7.3, max_width_pt=sw - 8)
                if first_bb is None:
                    first_bb = bb
                last_bb = bb
                sly -= 9.8
            assert first_bb is not None and last_bb is not None
            expected_fields.append(
                {
                    "field_id": sf["field_id"],
                    "label_printed": sf["label"],
                    "page_number": last_p,
                    "value_type": sf["value_type"],
                    "printed_text": sf["printed_text"],
                    "normalized_value": sf["normalized_value"],
                    "bbox_pt": [first_bb[0], last_bb[1], max(first_bb[2], last_bb[2]), first_bb[3]],
                }
            )
        y_cursor_by_page[last_p] = yl - sh - 8.0

    # Ensure ample clearance above hybrid stamp zone (y=62..108) and footer (y=26)
    for pno, y_end in y_cursor_by_page.items():
        if y_end < 116.0:
            raise ValueError(f"{src['family_id']} page {pno} content descends too low: y_end={y_end:.1f} < 116.0")

    if include_hybrid and src.get("hybrid_control"):
        hc = src["hybrid_control"]
        tp = hc["target_page"]
        x0, y0, x1, y1 = hc["box_pt"]
        w_pt = x1 - x0
        h_pt = y1 - y0
        w_px = int(round(w_pt * hc["raster_dpi"] / 72.0))
        h_px = int(round(h_pt * hc["raster_dpi"] / 72.0))
        rgb = make_hybrid_stamp_rgb(hc["label"], hc["printed_text"], w_px, h_px)
        canvases[tp - 1].draw_image_rgb(rgb, w_px, h_px, x0, y0, w_pt, h_pt)
        area_ratio = round((w_pt * h_pt) / (LETTER_WIDTH_PT * LETTER_HEIGHT_PT), 5)
        expected_fields.append(
            {
                "field_id": hc["field_id"],
                "label_printed": hc["label"],
                "page_number": tp,
                "value_type": "text",
                "modality": "embedded_raster_only",
                "page_area_ratio": area_ratio,
                "printed_text": hc["printed_text"],
                "normalized_value": hc["normalized_value"],
                "bbox_pt": [float(x0), float(y0), float(x1), float(y1)],
            }
        )

    return canvases, expected_fields, expected_absences, expected_tables


def draw_invoice(
    src: dict[str, Any],
) -> tuple[list[PdfPageCanvas], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Render single-page (F04, F05, F06) or 3-page continued (F07) maintenance invoices."""
    page_count = src["page_count"]
    canvases = [PdfPageCanvas() for _ in range(page_count)]
    acct = compute_invoice_accounting(src["accounting_spec"])
    expected_fields: list[dict[str, Any]] = []
    expected_absences: list[dict[str, Any]] = []
    sentinels_by_page = {s["page_number"]: s for s in src.get("page_sentinels", [])}

    b = src["banner"]
    y_cursor_by_page: dict[int, float] = {}

    for pno in range(1, page_count + 1):
        cp = canvases[pno - 1]
        cp.draw_text(b["vendor_contact"], 40, 26, font_key="regular", size_pt=7.2, max_width_pt=532, align="center")
        if pno == 1:
            cp.rect_fill_stroke(40, 718, 532, 44, fill_rgb=(0.92, 0.95, 0.98), stroke_rgb=(0.16, 0.22, 0.32), line_width=0.8)
            cp.draw_text(b["vendor_name"], 48, 746, font_key="bold", size_pt=10.5, max_width_pt=516)
            cp.draw_text(b["document_title"], 48, 728, font_key="bold", size_pt=11.0, max_width_pt=516)
            y_top = 710.0
        else:
            cp.rect_fill_stroke(40, 734, 532, 28, fill_rgb=(0.92, 0.95, 0.98), stroke_rgb=(0.16, 0.22, 0.32), line_width=0.7)
            cp.draw_text(b["vendor_name"], 48, 749, font_key="bold", size_pt=8.8, max_width_pt=320)
            cp.draw_text(b["document_title"] + " (CONTINUED)", 48, 738, font_key="regular", size_pt=8.0, max_width_pt=340)
            y_top = 726.0

        if pno in sentinels_by_page:
            s = sentinels_by_page[pno]
            cp.rect_fill_stroke(40, y_top - 17, 532, 17, fill_rgb=(0.87, 0.90, 0.95), stroke_rgb=(0.20, 0.24, 0.30))
            rib = (
                f"Invoice No: {s['repeated_doc_id']}   |   Contract ID: {s['repeated_contract_id']}   |   "
                f"{s['page_label']}   |   PG-ANCHOR: {s['sentinel_id']}"
            )
            cp.draw_text(rib, 46, y_top - 12, font_key="mono_bold", size_pt=7.8, max_width_pt=520)
            y_top -= 23.0

        y_cursor_by_page[pno] = y_top

    # Page 1 address blocks & header metadata
    c1 = canvases[0]
    y1 = y_cursor_by_page[1]
    ablocks = src["address_blocks"]
    aw = (532.0 - 6.0 * (len(ablocks) - 1)) / len(ablocks)
    ah = 54.0
    for idx, ab in enumerate(ablocks):
        ax = 40.0 + idx * (aw + 6.0)
        c1.rect_fill_stroke(ax, y1 - ah, aw, ah, fill_rgb=(0.99, 0.99, 1.0), stroke_rgb=(0.24, 0.28, 0.34))
        c1.draw_text(ab["title"], ax + 4, y1 - 11, font_key="bold", size_pt=7.3, max_width_pt=aw - 8)
        ly = y1 - 21.5
        for ln in ab["lines"]:
            c1.draw_text(ln, ax + 4, ly, font_key="regular", size_pt=6.8, max_width_pt=aw - 8)
            ly -= 9.8
        joined = ", ".join(ab["lines"])
        expected_fields.append(
            {
                "field_id": f"address_{ab['block_id']}",
                "label_printed": ab["title"],
                "page_number": 1,
                "value_type": "text",
                "printed_text": joined,
                "normalized_value": joined,
                "bbox_pt": [round(ax, 2), round(y1 - ah, 2), round(ax + aw, 2), round(y1, 2)],
            }
        )
    y1 -= ah + 6.0

    # Header metadata grid (2 rows x 3 columns = 6 stacked label/value cells)
    hfields = src["header_fields"]
    gh = 46.0
    row_cell_h = gh / 2.0
    c1.rect_fill_stroke(40, y1 - gh, 532, gh, fill_rgb=(0.96, 0.98, 1.0), stroke_rgb=(0.22, 0.26, 0.32))
    cell_w = 532.0 / 3.0
    c1.line(40, y1 - row_cell_h, 572, y1 - row_cell_h, stroke_rgb=(0.55, 0.60, 0.68), line_width=0.45)
    c1.line(40 + cell_w, y1, 40 + cell_w, y1 - gh, stroke_rgb=(0.55, 0.60, 0.68), line_width=0.45)
    c1.line(40 + 2.0 * cell_w, y1, 40 + 2.0 * cell_w, y1 - gh, stroke_rgb=(0.55, 0.60, 0.68), line_width=0.45)
    for idx, hf in enumerate(hfields):
        r_idx = idx // 3
        c_idx = idx % 3
        hx = 40.0 + c_idx * cell_w
        cell_top = y1 - r_idx * row_cell_h
        c1.draw_text(hf["label"] + ":", hx + 5, cell_top - 8.5, font_key="bold", size_pt=6.9, max_width_pt=cell_w - 10.0)
        vx = hx + 5.0
        vw = cell_w - 10.0
        hy_val = cell_top - 18.5
        if hf["is_absent"]:
            c1.line(vx, hy_val - 1.5, vx + vw - 6.0, hy_val - 1.5, stroke_rgb=(0.65, 0.68, 0.74), line_width=0.4)
            expected_absences.append(
                {
                    "field_id": hf["field_id"],
                    "label_printed": hf["label"],
                    "page_number": 1,
                    "expected_state": "absent_blank",
                }
            )
        else:
            bb = c1.draw_text(hf["printed_text"], vx, hy_val, font_key="regular", size_pt=7.8, max_width_pt=vw)
            expected_fields.append(
                {
                    "field_id": hf["field_id"],
                    "label_printed": hf["label"],
                    "page_number": 1,
                    "value_type": hf["value_type"],
                    "printed_text": hf["printed_text"],
                    "normalized_value": hf["normalized_value"],
                    "bbox_pt": list(bb),
                }
            )
    y1 -= gh + 5.0

    # Printed explicit accounting convention box on Page 1
    rule_lines = wrap_text_deterministic(acct["printed_rule_notice"], "regular", 7.1, 520.0)
    rh = 6.0 + len(rule_lines) * 9.5
    c1.rect_fill_stroke(40, y1 - rh, 532, rh, fill_rgb=(0.98, 0.97, 0.92), stroke_rgb=(0.45, 0.40, 0.25), line_width=0.4)
    ry = y1 - 10.0
    for rl in rule_lines:
        c1.draw_text(rl, 46, ry, font_key="regular", size_pt=7.1, max_width_pt=520)
        ry -= 9.5
    y_cursor_by_page[1] = y1 - rh - 6.0

    # Line-item table across pages
    inv_cols = [
        ("row_id", "Row", 26.0, "left", "identifier"),
        ("sku", "SKU / Ref", 68.0, "left", "identifier"),
        ("description", "Description", 164.0, "left", "text"),
        ("qty_unit", "Qty", 46.0, "right", "text"),
        ("unit_price", "Unit Price", 54.0, "right", "currency_usd"),
        ("discount_rate", "Disc%", 38.0, "right", "rate_percent"),
        ("line_discount", "Disc Amt", 46.0, "right", "currency_usd"),
        ("tax_flag", "Tax", 26.0, "center", "identifier"),
        ("net_line", "Net Line", 64.0, "right", "currency_usd"),
    ]
    assert abs(sum(c[2] for c in inv_cols) - 532.0) < 0.01

    dense = bool(src.get("dense_table_mode", False))
    body_pt = 6.9 if dense else 7.3
    base_row_h = 14.5 if dense else 16.5

    rows_by_page: dict[int, list[dict[str, Any]]] = {}
    for r in acct["rows"]:
        rows_by_page.setdefault(r["page_number"], []).append(r)

    exp_table_rows: list[dict[str, Any]] = []
    for pno in range(1, page_count + 1):
        cp = canvases[pno - 1]
        yp = y_cursor_by_page[pno]
        hdr_h = 15.5
        cp.rect_fill_stroke(40, yp - hdr_h, 532, hdr_h, fill_rgb=(0.85, 0.89, 0.94), stroke_rgb=(0.20, 0.24, 0.30))
        cx = 40.0
        for _, htext, cw, calign, _ in inv_cols:
            cp.line(cx, yp, cx, yp - hdr_h, stroke_rgb=(0.20, 0.24, 0.30))
            cp.draw_text(htext, cx + 3.5, yp - 11.0, font_key="bold", size_pt=7.1, max_width_pt=cw - 7.0, align=calign)
            cx += cw
        yp -= hdr_h

        for r in rows_by_page.get(pno, []):
            desc_lines = wrap_text_deterministic(r["description"], "regular", body_pt, 156.0)
            row_h = max(base_row_h, 6.0 + len(desc_lines) * (body_pt + 2.2))
            cp.rect_fill_stroke(40, yp - row_h, 532, row_h, fill_rgb=(1.0, 1.0, 1.0), stroke_rgb=(0.35, 0.38, 0.44), line_width=0.4)

            cell_map = {
                "row_id": (r["row_id"], r["row_id"], "identifier"),
                "sku": (r["sku"], r["sku"], "identifier"),
                "description": (r["description"], r["description"], "text"),
                "qty_unit": (r["qty_unit_printed"], r["quantity_norm"], "decimal_2"),
                "unit_price": (r["unit_price_printed"], r["unit_price_norm"], "currency_usd"),
                "discount_rate": (r["discount_rate_printed"], r["discount_rate_norm"], "rate_percent"),
                "line_discount": (r["line_discount_printed"], r["line_discount_norm"], "currency_usd"),
                "tax_flag": (r["tax_flag_printed"], r["tax_flag_printed"], "identifier"),
                "net_line": (r["net_line_printed"], r["net_line_norm"], "currency_usd"),
            }

            cx = 40.0
            exp_cells: dict[str, Any] = {}
            for cid, _, cw, calign, _ in inv_cols:
                cp.line(cx, yp, cx, yp - row_h, stroke_rgb=(0.35, 0.38, 0.44), line_width=0.4)
                ptxt, nval, vtype = cell_map[cid]
                if cid == "description" and len(desc_lines) > 1:
                    dly = yp - 10.0
                    for dln in desc_lines:
                        cp.draw_text(dln, cx + 4.0, dly, font_key="regular", size_pt=body_pt, max_width_pt=cw - 8.0)
                        dly -= body_pt + 2.2
                else:
                    cp.draw_text(ptxt, cx + 4.0, yp - 10.5, font_key="regular", size_pt=body_pt, max_width_pt=cw - 8.0, align=calign)
                exp_cells[cid] = {"printed_text": ptxt, "normalized_value": nval, "value_type": vtype}
                cx += cw

            exp_table_rows.append({"row_id": r["row_id"], "page_number": pno, "cells": exp_cells})
            yp -= row_h

        if pno < page_count:
            cp.draw_text(
                f"[Line items continue on Page {pno + 1}; Invoice Summary Totals appear ONLY on Page {page_count}]",
                40,
                yp - 13,
                font_key="mono",
                size_pt=7.3,
                max_width_pt=532,
            )
            yp -= 20.0
        y_cursor_by_page[pno] = yp - 8.0

    # Authoritative Summary Totals block ONLY on final page
    clast = canvases[page_count - 1]
    yl = y_cursor_by_page[page_count]
    summ = acct["summary"]

    summary_rows: list[tuple[str, str, dict[str, str], bool]] = [
        ("subtotal", "Line Net Subtotal", summ["subtotal"], False),
        ("taxable_subtotal", "Taxable Subtotal (Tax=T Rows)", summ["taxable_subtotal"], False),
        (
            "tax_amount",
            f"Sales Tax ({summ['tax_rate']['printed_text']} on Taxable Subtotal)",
            summ["tax_amount"],
            False,
        ),
    ]
    for fee in acct["fees"]:
        summary_rows.append(
            (
                f"fee_{fee['fee_id'].lower().replace('-', '_')}",
                fee["label"],
                {"printed_text": fee["amount_printed"], "normalized_value": fee["amount_norm"]},
                False,
            )
        )
    if not acct["fees"]:
        summary_rows.append(("non_taxable_fees", "Non-Taxable Fees", summ["non_taxable_fees"], False))

    summary_rows.extend(
        [
            ("invoice_total", "CURRENT INVOICE TOTAL", summ["invoice_total"], True),
            ("previous_balance", "Prior Unpaid Balance", summ["previous_balance"], False),
            ("payments_credits_applied", "Payments / Credits Applied", summ["payments_credits_applied"], False),
            ("amount_due", "TOTAL AMOUNT DUE", summ["amount_due"], True),
        ]
    )

    tot_h = 8.0 + len(summary_rows) * 14.5
    # Remittance box on left (246pt), Totals box on right (278pt)
    rem_lines = wrap_text_deterministic(src["remittance_note"], "regular", 7.4, 234.0)
    clast.rect_fill_stroke(40, yl - tot_h, 246, tot_h, fill_rgb=(0.97, 0.98, 1.0), stroke_rgb=(0.24, 0.28, 0.34))
    clast.draw_text("REMITTANCE & ACCOUNT NOTES", 46, yl - 12, font_key="bold", size_pt=7.6, max_width_pt=234)
    rly = yl - 24.5
    for rln in rem_lines:
        clast.draw_text(rln, 46, rly, font_key="regular", size_pt=7.4, max_width_pt=234)
        rly -= 10.2

    clast.rect_fill_stroke(294, yl - tot_h, 278, tot_h, fill_rgb=(0.98, 0.99, 1.0), stroke_rgb=(0.18, 0.22, 0.30), line_width=0.7)
    sy = yl - 13.5
    for fid, flabel, fdict, is_bold in summary_rows:
        fkey = "bold" if is_bold else "regular"
        clast.draw_text(flabel + ":", 300, sy, font_key=fkey, size_pt=7.1, max_width_pt=194)
        bb = clast.draw_text(fdict["printed_text"], 498, sy, font_key=fkey, size_pt=7.8, max_width_pt=68, align="right")
        expected_fields.append(
            {
                "field_id": fid,
                "label_printed": flabel,
                "page_number": page_count,
                "value_type": "currency_usd",
                "printed_text": fdict["printed_text"],
                "normalized_value": fdict["normalized_value"],
                "bbox_pt": list(bb),
            }
        )
        sy -= 14.5

    if yl - tot_h < 48.0:
        raise ValueError(f"{src['family_id']} final page totals descend too low: {yl - tot_h:.1f}")

    expected_tables = [
        {
            "table_id": "line_items",
            "page_numbers": list(range(1, page_count + 1)),
            "repeated_header_pages": list(range(2, page_count + 1)),
            "column_ids": [c[0] for c in inv_cols],
            "rows": exp_table_rows,
        }
    ]
    return canvases, expected_fields, expected_absences, expected_tables, acct


def rasterize_pdf_300dpi(pdf_bytes: bytes) -> list[Image.Image]:
    doc = pdfium.PdfDocument(pdf_bytes)
    scale = RASTER_DPI / 72.0
    images: list[Image.Image] = []
    for i in range(len(doc)):
        page = doc[i]
        bmp = page.render(scale=scale)
        pil_img = bmp.to_pil().convert("RGB")
        images.append(pil_img)
        page.close()
    doc.close()
    return images


def build_expected_payload(
    *,
    fixture_id: str,
    src: dict[str, Any],
    variant_kind: str,
    expected_routing: str,
    fields: list[dict[str, Any]],
    absences: list[dict[str, Any]],
    tables: list[dict[str, Any]],
    accounting: dict[str, Any] | None,
    parent_fixture_id: str | None,
    transform_params: dict[str, Any],
) -> dict[str, Any]:
    # Strip vector point bboxes on pure raster/skew variants where page coordinates are pixel-transformed
    out_fields = []
    for f in fields:
        fc = dict(f)
        if variant_kind in ("v1_raster300", "v2_skew"):
            fc["bbox_pt"] = None
        out_fields.append(fc)

    page_count = src["page_count"]
    adjacent_pairs = [[p, p + 1] for p in range(1, page_count)]
    return {
        "schema_version": "1.0.0",
        "fixture_id": fixture_id,
        "family_id": src["family_id"],
        "doc_kind": src["doc_kind"],
        "split": src["split"],
        "split_disclosure": "fixed_test_partition_not_blind_to_corpus_author",
        "variant_kind": variant_kind,
        "parent_fixture_id": parent_fixture_id,
        "page_count": page_count,
        "expected_adjacent_page_pairs": adjacent_pairs,
        "page_sentinels": src.get("page_sentinels", []),
        "cross_page_links": src.get("cross_page_links", []),
        "expected_routing_for_e3": expected_routing,
        "transform_params": transform_params,
        "expected_fields": out_fields,
        "expected_absences": absences,
        "expected_tables": tables,
        "invoice_accounting": accounting,
    }


def generate_all(sources_dir: pathlib.Path, out_eval_root: pathlib.Path, preview_png_dir: pathlib.Path | None = None) -> dict[str, Any]:
    pdfs_root = out_eval_root / "synthetic" / "pdfs"
    exp_root = out_eval_root / "synthetic" / "expected"
    man_root = out_eval_root / "manifests"
    pdfs_root.mkdir(parents=True, exist_ok=True)
    exp_root.mkdir(parents=True, exist_ok=True)
    man_root.mkdir(parents=True, exist_ok=True)
    if preview_png_dir is not None:
        preview_png_dir.mkdir(parents=True, exist_ok=True)

    source_files = sorted(sources_dir.glob("F*_source.json"))
    if len(source_files) != 8:
        raise ValueError(f"Expected 8 source files in {sources_dir}, found {len(source_files)}")

    manifest_items: list[dict[str, Any]] = []
    source_records_meta: list[dict[str, Any]] = []

    for sf in source_files:
        s_bytes = sf.read_bytes()
        src = json.loads(s_bytes.decode("utf-8"))
        fam_id = src["family_id"]
        prefix = src["fixture_prefix"]
        split = src["split"]
        fam_pdf_dir = pdfs_root / fam_id
        fam_pdf_dir.mkdir(parents=True, exist_ok=True)

        source_records_meta.append(
            {
                "family_id": fam_id,
                "fixture_prefix": prefix,
                "split": split,
                "source_path": f"evaluation/synthetic/sources/{sf.name}",
                "size_bytes": len(s_bytes),
                "sha256": sha256_hex(s_bytes),
                "git_blob_oid": git_blob_oid(s_bytes),
            }
        )

        if src["doc_kind"] == "invoice":
            canvases, fields, absences, tables, acct = draw_invoice(src)
        else:
            canvases, fields, absences, tables = draw_work_order_or_packet(src, include_hybrid=False)
            acct = None

        # 1. v0-clean vector original
        v0_id = f"{prefix}-v0-clean"
        v0_pdf_bytes = serialize_pdf(canvases, title=f"{v0_id} ({fam_id})")
        v0_rel = f"evaluation/synthetic/pdfs/{fam_id}/{v0_id}.pdf"
        (fam_pdf_dir / f"{v0_id}.pdf").write_bytes(v0_pdf_bytes)

        v0_exp = build_expected_payload(
            fixture_id=v0_id,
            src=src,
            variant_kind="v0_clean",
            expected_routing="eligible_digital_text_layer",
            fields=fields,
            absences=absences,
            tables=tables,
            accounting=acct,
            parent_fixture_id=None,
            transform_params={"renderer": "pdf_writer.py PDF 1.4 Base-14 Type1 vector", "dpi": None, "rotation_deg": 0.0},
        )
        v0_exp_bytes = (json.dumps(v0_exp, indent=2) + "\n").encode("utf-8")
        (exp_root / f"{v0_id}_expected.json").write_bytes(v0_exp_bytes)

        # Render 300-DPI RGB pages once via PDFium
        pil_pages_v1 = rasterize_pdf_300dpi(v0_pdf_bytes)
        if preview_png_dir is not None:
            for p_i, im in enumerate(pil_pages_v1, start=1):
                im.save(preview_png_dir / f"{v0_id}_p{p_i}.png")

        # 2. v1-raster300 image-only unrotated PDF
        v1_id = f"{prefix}-v1-raster300"
        v1_rgb_tuples = [(im.tobytes(), im.width, im.height) for im in pil_pages_v1]
        v1_pdf_bytes = build_image_only_pdf(v1_rgb_tuples, dpi=RASTER_DPI, title=f"{v1_id} ({fam_id})")
        v1_rel = f"evaluation/synthetic/pdfs/{fam_id}/{v1_id}.pdf"
        (fam_pdf_dir / f"{v1_id}.pdf").write_bytes(v1_pdf_bytes)
        if preview_png_dir is not None:
            for p_i, im in enumerate(rasterize_pdf_300dpi(v1_pdf_bytes), start=1):
                im.save(preview_png_dir / f"{v1_id}_p{p_i}.png")

        v1_exp = build_expected_payload(
            fixture_id=v1_id,
            src=src,
            variant_kind="v1_raster300",
            expected_routing="must_route_to_ocr",
            fields=fields,
            absences=absences,
            tables=tables,
            accounting=acct,
            parent_fixture_id=v0_id,
            transform_params={
                "rasterizer": f"pypdfium2 {pdfium.version.PYPDFIUM_INFO} ({pdfium.version.PDFIUM_INFO})",
                "dpi": RASTER_DPI,
                "pixel_size_per_page": [pil_pages_v1[0].width, pil_pages_v1[0].height],
                "text_layer": False,
                "rotation_deg": 0.0,
            },
        )
        v1_exp_bytes = (json.dumps(v1_exp, indent=2) + "\n").encode("utf-8")
        (exp_root / f"{v1_id}_expected.json").write_bytes(v1_exp_bytes)

        # 3. v2-skew signed-skew image-only PDF (+4.0 odd families, -3.0 even families)
        skew_deg = float(src["signed_skew_degrees"])
        skew_tag = f"pos{int(abs(skew_deg))}deg" if skew_deg > 0 else f"neg{int(abs(skew_deg))}deg"
        v2_id = f"{prefix}-v2-skew-{skew_tag}"
        pil_pages_v2 = [
            im.rotate(skew_deg, resample=Image.Resampling.BILINEAR, expand=True, fillcolor=(255, 255, 255))
            for im in pil_pages_v1
        ]
        v2_rgb_tuples = [(im.tobytes(), im.width, im.height) for im in pil_pages_v2]
        v2_pdf_bytes = build_image_only_pdf(v2_rgb_tuples, dpi=RASTER_DPI, title=f"{v2_id} ({fam_id})")
        v2_rel = f"evaluation/synthetic/pdfs/{fam_id}/{v2_id}.pdf"
        (fam_pdf_dir / f"{v2_id}.pdf").write_bytes(v2_pdf_bytes)
        if preview_png_dir is not None:
            for p_i, im in enumerate(rasterize_pdf_300dpi(v2_pdf_bytes), start=1):
                im.save(preview_png_dir / f"{v2_id}_p{p_i}.png")

        v2_exp = build_expected_payload(
            fixture_id=v2_id,
            src=src,
            variant_kind="v2_skew",
            expected_routing="must_route_to_ocr",
            fields=fields,
            absences=absences,
            tables=tables,
            accounting=acct,
            parent_fixture_id=v1_id,
            transform_params={
                "source_raster_fixture": v1_id,
                "pillow_version": Image.__version__,
                "method": "PIL.Image.Image.rotate(angle, resample=BILINEAR, expand=True, fillcolor=(255,255,255))",
                "signed_angle_degrees_ccw": skew_deg,
                "dpi": RASTER_DPI,
                "expanded_pixel_size_per_page": [pil_pages_v2[0].width, pil_pages_v2[0].height],
                "text_layer": False,
            },
        )
        v2_exp_bytes = (json.dumps(v2_exp, indent=2) + "\n").encode("utf-8")
        (exp_root / f"{v2_id}_expected.json").write_bytes(v2_exp_bytes)

        def register_item(
            fid: str,
            vkind: str,
            rel_pdf: str,
            pdf_b: bytes,
            exp_b: bytes,
            parent_id: str | None,
            parent_sha: str | None,
            tparams: dict[str, Any],
        ) -> None:
            manifest_items.append(
                {
                    "fixture_id": fid,
                    "family_id": fam_id,
                    "classification": "synthetic",
                    "variant_kind": vkind,
                    "admission_status": "author_checked_pending_opus_wp0004_005",
                    "split": split,
                    "origin_url": None,
                    "origin_revision": None,
                    "source_record_path": f"evaluation/synthetic/sources/{sf.name}",
                    "source_record_sha256": sha256_hex(s_bytes),
                    "file_path": rel_pdf,
                    "sha256": sha256_hex(pdf_b),
                    "git_blob_oid": git_blob_oid(pdf_b),
                    "size_bytes": len(pdf_b),
                    "page_count": src["page_count"],
                    "parent_fixture_id": parent_id,
                    "parent_pdf_sha256": parent_sha,
                    "expected_ground_truth_path": f"evaluation/synthetic/expected/{fid}_expected.json",
                    "expected_ground_truth_sha256": sha256_hex(exp_b),
                    "expected_ground_truth_git_blob_oid": git_blob_oid(exp_b),
                    "source_license_and_notices": "Repository-authored fictional synthetic fixture; standard PDF Base-14 Type1 font names (/Helvetica, /Courier) without embedded third-party font binaries.",
                    "generation_or_transform_params": tparams,
                    "author": "eld-rd-carbon",
                    "author_checkers": [
                        "evaluation/generation/verify_arithmetic_independent.py",
                        "evaluation/generation/verify_corpus_integrity.py",
                    ],
                    "independent_checker": None,
                    "independent_checker_note": "Unresolved pending non-author verification by eld-rd-reviewer (uninvolved Opus) in WP-0004 / 005.",
                }
            )

        v0_sha = sha256_hex(v0_pdf_bytes)
        v1_sha = sha256_hex(v1_pdf_bytes)
        register_item(v0_id, "v0_clean", v0_rel, v0_pdf_bytes, v0_exp_bytes, None, None, v0_exp["transform_params"])
        register_item(v1_id, "v1_raster300", v1_rel, v1_pdf_bytes, v1_exp_bytes, v0_id, v0_sha, v1_exp["transform_params"])
        register_item(v2_id, "v2_skew", v2_rel, v2_pdf_bytes, v2_exp_bytes, v1_id, v1_sha, v2_exp["transform_params"])

        # 4. Optional linked hybrid negative controls (F02 in dev, F08 in eval_holdout)
        if src.get("hybrid_control"):
            hc = src["hybrid_control"]
            v3_id = hc["fixture_id"]
            h_canvases, h_fields, h_absences, h_tables = draw_work_order_or_packet(src, include_hybrid=True)
            v3_pdf_bytes = serialize_pdf(h_canvases, title=f"{v3_id} ({fam_id})")
            v3_rel = f"evaluation/synthetic/pdfs/{fam_id}/{v3_id}.pdf"
            (fam_pdf_dir / f"{v3_id}.pdf").write_bytes(v3_pdf_bytes)

            if preview_png_dir is not None:
                pil_pages_v3 = rasterize_pdf_300dpi(v3_pdf_bytes)
                for p_i, im in enumerate(pil_pages_v3, start=1):
                    im.save(preview_png_dir / f"{v3_id}_p{p_i}.png")

            v3_tparams = {
                "parent_vector_fixture": v0_id,
                "hybrid_target_page": hc["target_page"],
                "embedded_raster_box_pt": hc["box_pt"],
                "embedded_raster_dpi": hc["raster_dpi"],
                "stamp_font": f"Pillow {Image.__version__} ImageFont.load_default",
                "vector_text_layer_present": True,
                "embedded_image_xobject_present": True,
            }
            v3_exp = build_expected_payload(
                fixture_id=v3_id,
                src=src,
                variant_kind="v3_hybrid",
                expected_routing="must_route_to_ocr",
                fields=h_fields,
                absences=h_absences,
                tables=h_tables,
                accounting=None,
                parent_fixture_id=v0_id,
                transform_params=v3_tparams,
            )
            v3_exp_bytes = (json.dumps(v3_exp, indent=2) + "\n").encode("utf-8")
            (exp_root / f"{v3_id}_expected.json").write_bytes(v3_exp_bytes)
            register_item(v3_id, "v3_hybrid", v3_rel, v3_pdf_bytes, v3_exp_bytes, v0_id, v0_sha, v3_tparams)

    total_pdfs = len(manifest_items)
    total_pages = sum(it["page_count"] for it in manifest_items)
    assert total_pdfs == 26 and total_pages == 40, f"Expected 26 PDFs / 40 pages, got {total_pdfs} / {total_pages}"

    manifest = {
        "schema_version": "1.0.0",
        "packet": "WP-0004 / 004",
        "corpus_status": "author_prepared_candidate_pending_opus_wp0004_005_review",
        "disclaimer": (
            "Bounded 8-family synthetic property-maintenance starter set (26 PDFs / 40 pages total). "
            "Not a representative population benchmark, not real handwriting or physical scanner output, "
            "and eval_holdout is a fixed test partition rather than blind validation to its author. "
            "Invoice Decimal ROUND_HALF_UP rules are this synthetic corpus's explicit convention, not universal tax/GAAP law."
        ),
        "counts": {
            "families": 8,
            "dev_families": ["F01", "F02", "F04", "F07"],
            "eval_holdout_families": ["F03", "F05", "F06", "F08"],
            "v0_clean_originals": {"pdfs": 8, "pages": 12},
            "v1_raster300_variants": {"pdfs": 8, "pages": 12},
            "v2_skew_variants": {"pdfs": 8, "pages": 12},
            "v3_hybrid_negative_controls": {"pdfs": 2, "pages": 4},
            "total_pdfs": total_pdfs,
            "total_pages": total_pages,
            "admitted_public_pdfs": 0,
        },
        "generator_and_tooling": {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "vector_pdf_writer": "evaluation/generation/pdf_writer.py (PDF 1.4, Base-14 Type1 /Helvetica & /Courier)",
            "rasterizer": f"pypdfium2 {pdfium.version.PYPDFIUM_INFO} ({pdfium.version.PDFIUM_INFO})",
            "image_transform": f"Pillow {Image.__version__} (BILINEAR signed skew, white RGB fill)",
            "seed": None,
            "determinism_mode": "declarative_literal_v1 (zero RNG state; fixed metadata date D:20261114000000Z)",
        },
        "source_records": source_records_meta,
        "fixtures": manifest_items,
    }
    man_bytes = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    (man_root / "corpus-manifest.json").write_bytes(man_bytes)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic WP-0004/004 synthetic corpus.")
    parser.add_argument(
        "--sources-dir",
        type=pathlib.Path,
        default=THIS_DIR.parent / "synthetic" / "sources",
        help="Path to declarative F01..F08 source JSON directory.",
    )
    parser.add_argument(
        "--output-eval-root",
        type=pathlib.Path,
        default=THIS_DIR.parent,
        help="Target evaluation/ root directory where synthetic/{pdfs,expected} and manifests/ are written.",
    )
    parser.add_argument(
        "--preview-png-dir",
        type=pathlib.Path,
        default=None,
        help="Optional scratch directory to export 300-DPI PNG page previews for visual inspection.",
    )
    args = parser.parse_args()
    manifest = generate_all(args.sources_dir.resolve(), args.output_eval_root.resolve(), args.preview_png_dir)
    print(
        f"GENERATED_OK: families={manifest['counts']['families']} "
        f"pdfs={manifest['counts']['total_pdfs']} pages={manifest['counts']['total_pages']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
