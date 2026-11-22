"""Build all four PDFs and compare every full-page render with its archived source."""
from contextlib import closing
from io import BytesIO
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image
import pypdfium2 as pdfium

from common import CASES, CUSTODY, DEST, TRUTH, TRUTH_PIN, case_id, checked_json, git_blob, keep, pinned, sha

POINT_ROI = [138, 376, 210, 409]
PIXEL_ROI = [math.floor(x * 300 / 72) for x in POINT_ROI[:2]] + [math.ceil(x * 300 / 72) for x in POINT_ROI[2:]]
OLD_OP = b"BT /F2 22 Tf 35 390 Td (Ledger: Alder) Tj ET"
NEW_OP = OLD_OP.replace(b"Alder", b"Cedar")
PUBLIC = CUSTODY / "public/cal"
PREFIX = "docs/fixtures/WP-0024/v2/cal/"

def load_sources():
    receipt_bytes = git_blob(PREFIX + "receipt.json")
    receipt = checked_json(receipt_bytes, "c698da52adb55a5611d5aae8749259eac97f371623aac574e880cecb2ecd32a9")
    assert (PUBLIC / "receipt.json").read_bytes() == receipt_bytes
    tables = {}
    for name, field in (("manifest", "manifest"), ("pairs", "pairs"), ("cross-pair", "cross_pair")):
        raw = (PUBLIC / (name + ".json")).read_bytes()
        assert raw == git_blob(PREFIX + name + ".json")
        tables[name] = checked_json(raw, receipt[field + "_sha256"])
    assert receipt["truth_sha256"] == TRUTH_PIN
    truth = checked_json(TRUTH.read_bytes(), TRUTH_PIN)
    docs = {b["binder"]: b["windows"] for b in tables["manifest"]["binders"]}
    keys = {b["binder"]: b for b in truth["binders"] if b["binder"] in {v[0] for v in CASES.values()}}
    routes = {q["pair"]: q["members"] for q in tables["pairs"]["pairs"]}
    return receipt, docs, keys, routes

def render(page):
    assert page.get_size() == (612., 792.)
    with closing(page.render(scale=math.nextafter(300 / 72, 0))) as bitmap:
        with bitmap.to_pil().convert("RGB") as image:
            assert image.size == (2550, 3300)
            buf = BytesIO()
            image.save(buf, format="PNG", dpi=(300, 300), compress_level=3)
            return image.tobytes(), buf.getvalue()

def text(page):
    with closing(page.get_textpage()) as t:
        return t.get_text_bounded()

def page_diff(a, b):
    arr_a = np.frombuffer(a, np.uint8).reshape(3300, 2550, 3)
    arr_b = np.frombuffer(b, np.uint8).reshape(3300, 2550, 3)
    mask = (arr_a != arr_b).any(axis=2)
    ys, xs = np.nonzero(mask)
    x0, y0, x1, y1 = PIXEL_ROI
    count = int(mask.sum())
    inside = int(mask[y0:y1, x0:x1].sum())
    assert count == inside > 0
    return dict(changed_pixels=count, inside=inside, outside=count-inside,
                bbox_xyxy_exclusive=[int(xs.min()), int(ys.min()), int(xs.max()+1), int(ys.max()+1)])

def save_page(out, rgb, png):
    png_hash = sha(png)
    rel = Path("rasters") / (png_hash + ".png")
    keep(out / rel, png)
    return dict(image=(DEST / rel).as_posix(), sha256=png_hash, rgb_sha256=sha(rgb))

def build(out):
    receipt, docs, keys, routes = load_sources()
    pairs, evidence = [], []
    for horizon, (base, base_pair, base_target) in CASES.items():
        template = f"T1-{horizon}"
        base_pdf = pinned((PUBLIC / "pdf" / (base + ".pdf")).read_bytes(), receipt["source_pdfs"][base])
        assert {"binder":base, "target":base_target} in routes[base_pair]
        truth = keys[base]
        assert (truth["pair"], truth["target"], truth["owner"], truth["stratum"], truth["literal"]) == (base_pair, base_target, "Alder", "T1", "241")
        assert truth["window1"] == {"owner":"Alder", "unit":"Unit3", "schema":["Item", "Amount", "Ref"]}
        assert b"/BaseFont /Courier-Bold" in base_pdf and base_pdf.count(OLD_OP) == 1 and NEW_OP not in base_pdf
        edited_pdf = base_pdf.replace(OLD_OP, NEW_OP)
        offset = base_pdf.index(OLD_OP) + OLD_OP.index(b"Alder")
        assert base_pdf[:offset] == edited_pdf[:offset] and base_pdf[offset+5:] == edited_pdf[offset+5:]
        members = []
        for ordinal, (owner, raw) in enumerate((("Alder", base_pdf), ("Cedar", edited_pdf))):
            binder = case_id(template, f"member/{ordinal}")
            rel = Path("pdf") / (binder + ".pdf")
            keep(out / rel, raw)
            members.append(dict(binder=binder, target=case_id(template, f"target/{ordinal}"), owner=owner,
                                source_pdf=(DEST / rel).as_posix(), source_pdf_sha256=sha(raw), windows=[]))
        rows = []
        with pdfium.PdfDocument(base_pdf) as left, pdfium.PdfDocument(edited_pdf) as right:
            assert len(left) == len(right) == horizon == 3 * len(docs[base])
            for i in range(horizon):
                window, page = divmod(i, 3)
                old = docs[base][window]["pages"][page]
                archived_png = pinned(Path(old["image"]).read_bytes(), old["sha256"])
                with closing(left[i]) as a, closing(right[i]) as b:
                    a_rgb, a_png = render(a)
                    b_rgb, b_png = render(b)
                    a_text, b_text = text(a), text(b)
                assert a_png == archived_png and sha(a_rgb) == old["rgb_sha256"]
                if i == 0:
                    assert a_text.count("Ledger: Alder") == 1
                    assert b_text == a_text.replace("Ledger: Alder", "Ledger: Cedar")
                    diff = page_diff(a_rgb, b_rgb)
                else:
                    assert (a_rgb, a_png, a_text) == (b_rgb, b_png, b_text)
                    diff = dict(changed_pixels=0, inside=0, outside=0, bbox_xyxy_exclusive=None)
                if i == horizon - 2:
                    assert a_text.split() == ["Posting", "241", "851"]
                rows.append(dict(page=i+1, archived_png_sha256=old["sha256"], archived_rgb_sha256=old["rgb_sha256"],
                                 base_encoded_equal_archived=True, base_decoded_equal_archived=True,
                                 twins_encoded_identical=a_png==b_png, twins_decoded_identical=a_rgb==b_rgb, **diff))
                for m, rgb, png in zip(members, (a_rgb,b_rgb), (a_png,b_png), strict=True):
                    if page == 0:
                        m["windows"].append(dict(window=window+1, pages=[]))
                    m["windows"][-1]["pages"].append(save_page(out, rgb, png))
        pair = dict(template=template, horizon=horizon, pair=case_id(template, "pair"), base_pair=base_pair,
                    base_binder=base, base_target=base_target, target_page=horizon-1, target_window=horizon//3,
                    target_page_in_window=2, members=members)
        pairs.append(pair)
        evidence.append(dict(template=template, source_pair=base_pair, source_binder=base, original_pdf_sha256=sha(base_pdf),
                             edited_pdf_sha256=sha(edited_pdf), source_pdf_bytes=len(base_pdf), operation_before=OLD_OP.decode(),
                             operation_after=NEW_OP.decode(), literal_byte_interval=[offset,offset+5],
                             edited_offsets=[i for i,(u,v) in enumerate(zip(base_pdf,edited_pdf,strict=True)) if u!=v],
                             source_page=1, font_resource="F2/Courier-Bold", declared_roi_top_left_pt=POINT_ROI,
                             roi_pixels_xyxy_exclusive=PIXEL_ROI, page_points=[612,792], raster_size=[2550,3300],
                             page_evidence=rows))
    for i in range(2):
        short, long = [p["members"][i]["windows"] for p in pairs]
        assert [w["pages"] for w in short] == [w["pages"] for w in long[:2]+long[-2:]]
    return pairs, evidence
