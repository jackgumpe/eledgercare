#!/usr/bin/env python3
"""WP-0004 / 005 eld-rd-reviewer independent corpus verifier.

Reviewer-authored. It deliberately does NOT import evaluation/generation/* (author generator,
pdf_writer or author checkers). Arithmetic uses integer cents with an own half-away-from-zero
rounding helper; PDF structure is read with an own minimal object/xref/content-stream parser;
rendering/glyph geometry use the pinned pypdfium2 wheel; rotation reproduction uses the pinned
Pillow wheel exactly as declared in transform metadata.

Usage:
  python rd005_verify.py --repo <exported candidate root> --lstree <git ls-tree -r output>
                         --wheels <dir> --out <evidence dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
import zlib
from collections import defaultdict
from datetime import date, timedelta

import pypdfium2 as pdfium
from PIL import Image

FAMILIES = [f"F0{i}" for i in range(1, 9)]
FINDINGS: list[dict] = []


def finding(sev: str, fid: str, msg: str, **kw) -> None:
    FINDINGS.append({"severity": sev, "id": fid, "message": msg, **kw})


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def blob_oid(b: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


# ----------------------------------------------------------------------------------------------
# Own integer arithmetic
# ----------------------------------------------------------------------------------------------
def parse_fixed(s: str, places: int) -> int:
    """Parse a plain decimal string into an integer scaled by 10**places; refuse extra precision."""
    if not re.fullmatch(r"-?\d+(\.\d+)?", s):
        raise ValueError(f"not a plain decimal: {s!r}")
    neg = s.startswith("-")
    s = s.lstrip("-")
    whole, _, frac = s.partition(".")
    if len(frac) > places:
        raise ValueError(f"{s!r} exceeds {places} places")
    v = int(whole) * 10**places + int((frac + "0" * places)[:places] or "0")
    return -v if neg else v


TIES: list[dict] = []


def div_half_away(n: int, d: int, ctx: str) -> int:
    q, r = divmod(abs(n), d)
    if 2 * r == d:
        TIES.append({"context": ctx, "numerator": n, "denominator": d})
    if 2 * r >= d:
        q += 1
    return -q if n < 0 else q


def usd(c: int) -> str:
    a = abs(c)
    return ("-" if c < 0 else "") + f"${a // 100:,}.{a % 100:02d}"


def norm2(c: int) -> str:
    a = abs(c)
    return ("-" if c < 0 else "") + f"{a // 100}.{a % 100:02d}"


def pct(r4: int) -> str:
    return f"{r4 // 100}.{r4 % 100:02d}%"


def rate_norm(r4: int) -> str:
    return f"{r4 // 10000}.{r4 % 10000:04d}"


def compute_invoice(spec: dict, fam: str) -> dict:
    rows = []
    for it in spec["line_items"]:
        q = parse_fixed(it["quantity"], 2)
        p = parse_fixed(it["unit_price"], 2)
        r = parse_fixed(it["discount_rate"], 4)
        gross = div_half_away(q * p, 100, f"{fam} {it['row_id']} gross")
        disc = div_half_away(gross * r, 10000, f"{fam} {it['row_id']} discount")
        net = gross - disc
        rows.append({
            "row_id": it["row_id"], "page": it["page_number"], "sku": it["sku"],
            "description": it["description"], "qty_printed": f"{q // 100}.{q % 100:02d} {it['unit']}",
            "qty_norm": f"{q // 100}.{q % 100:02d}", "unit_price_c": p, "rate4": r,
            "gross_c": gross, "disc_c": disc, "net_c": net, "taxable": bool(it["is_taxable"]),
            "credit": p < 0,
        })
    subtotal = sum(x["net_c"] for x in rows)
    taxable = sum(x["net_c"] for x in rows if x["taxable"])
    tr = parse_fixed(spec["tax_rate"], 4)
    tax = div_half_away(taxable * tr, 10000, f"{fam} tax")
    fees = [(f["fee_id"], f["label"], parse_fixed(f["amount"], 2), bool(f.get("is_taxable"))) for f in spec.get("fees", [])]
    fee_sum = sum(f[2] for f in fees)
    total = subtotal + tax + fee_sum
    prev = parse_fixed(spec["previous_balance"], 2)
    pay = parse_fixed(spec["payments_credits_applied"], 2)
    due = total + prev - pay
    return {"rows": rows, "subtotal": subtotal, "taxable": taxable, "tax_rate4": tr, "tax": tax,
            "fees": fees, "fee_sum": fee_sum, "invoice_total": total, "previous_balance": prev,
            "payments": pay, "amount_due": due, "tax_rate_printed": spec["tax_rate_printed"]}


# ----------------------------------------------------------------------------------------------
# Own minimal PDF reader (for this repository's fixtures; validated against xref and pdfium)
# ----------------------------------------------------------------------------------------------
class MiniPdf:
    def __init__(self, data: bytes):
        self.data = data
        if not data.startswith(b"%PDF-1.4\n"):
            raise ValueError("header")
        sx = data.rindex(b"startxref")
        xref_pos = int(data[sx + 9:].split()[0])
        if data[xref_pos:xref_pos + 4] != b"xref":
            raise ValueError("startxref does not point at xref")
        lines = data[xref_pos:].split(b"\n")
        first, count = map(int, lines[1].split())
        self.offsets = {}
        for i in range(1, count):
            off = int(lines[2 + i][:10])
            self.offsets[first + i] = off
            if not data[off:].startswith(b"%d 0 obj\n" % (first + i)):
                raise ValueError(f"xref offset mismatch for obj {first + i}")
        tr = data[data.rindex(b"trailer"):]
        self.trailer = tr.decode("latin-1")
        self.size = int(re.search(r"/Size (\d+)", self.trailer).group(1))
        if self.size != count:
            raise ValueError("trailer /Size != xref count")
        self.root = int(re.search(r"/Root (\d+) 0 R", self.trailer).group(1))
        m = re.search(r"/ID \[<([0-9a-f]+)> <([0-9a-f]+)>\]", self.trailer)
        self.file_id = m.group(1) if m else None
        self.xref_pos = xref_pos

    def obj(self, n: int) -> tuple[str, bytes | None]:
        off = self.offsets[n]
        start = off + len(b"%d 0 obj\n" % n)
        si = self.data.find(b"stream\n", start)
        ei = self.data.find(b"\nendobj\n", start)
        if si != -1 and si < ei:
            head = self.data[start:si].decode("latin-1")
            length = int(re.search(r"/Length (\d+)", head).group(1))
            raw = self.data[si + 7: si + 7 + length]
            if self.data[si + 7 + length: si + 7 + length + 10] != b"\nendstream":
                raise ValueError(f"stream length mismatch obj {n}")
            return head, raw
        return self.data[start:ei].decode("latin-1"), None

    def pages(self) -> list[dict]:
        cat, _ = self.obj(self.root)
        pages_ref = int(re.search(r"/Pages (\d+) 0 R", cat).group(1))
        pdict, _ = self.obj(pages_ref)
        kids = [int(k) for k in re.findall(r"(\d+) 0 R", re.search(r"/Kids \[([^\]]*)\]", pdict).group(1))]
        cnt = int(re.search(r"/Count (\d+)", pdict).group(1))
        if cnt != len(kids):
            raise ValueError("/Count != len(/Kids)")
        out = []
        for k in kids:
            d, _ = self.obj(k)
            mb = [float(x) for x in re.search(r"/MediaBox \[([^\]]*)\]", d).group(1).split()]
            cref = int(re.search(r"/Contents (\d+) 0 R", d).group(1))
            chead, craw = self.obj(cref)
            content = zlib.decompress(craw) if "/FlateDecode" in chead else craw
            fonts = re.findall(r"/(F\d) (\d+) 0 R", re.search(r"/Font <<([^>]*)>>", d).group(1)) if "/Font" in d else []
            font_names = {}
            for alias, fref in fonts:
                fd, _ = self.obj(int(fref))
                font_names[alias] = {"BaseFont": re.search(r"/BaseFont /(\S+)", fd).group(1),
                                     "Subtype": re.search(r"/Subtype /(\S+)", fd).group(1),
                                     "embedded_FontFile": "/FontFile" in fd or "/FontDescriptor" in fd}
            images = {}
            if "/XObject" in d:
                for name, iref in re.findall(r"/(Im\d+) (\d+) 0 R", re.search(r"/XObject <<([^>]*)>>", d).group(1)):
                    ih, iraw = self.obj(int(iref))
                    images[name] = {
                        "subtype": re.search(r"/Subtype /(\S+)", ih).group(1),
                        "w": int(re.search(r"/Width (\d+)", ih).group(1)),
                        "h": int(re.search(r"/Height (\d+)", ih).group(1)),
                        "cs": re.search(r"/ColorSpace /(\S+)", ih).group(1),
                        "bpc": int(re.search(r"/BitsPerComponent (\d+)", ih).group(1)),
                        "filter": re.search(r"/Filter /(\S+)", ih).group(1),
                        "raw": iraw,
                    }
            out.append({"mediabox": mb, "content": content, "fonts": font_names, "images": images, "dict": d})
        return out


TOKEN_RE = re.compile(rb"\s*(\((?:\\.|[^\\)])*\)|/[^\s/\[\]()<>]+|[-+]?\d*\.?\d+|[A-Za-z*']+|\[|\])")


def unescape_pdf_string(tok: bytes) -> str:
    s = tok[1:-1]
    out = bytearray()
    i = 0
    while i < len(s):
        c = s[i]
        if c == 0x5C:
            i += 1
            out.append(s[i])
        else:
            out.append(c)
        i += 1
    return out.decode("latin-1")


def interpret(content: bytes) -> dict:
    """Tiny content interpreter: text runs with position/font, stroked edges, images."""
    texts, edges, images, fills = [], [], [], []
    stack: list = []
    font = None
    size = None
    tm = (0.0, 0.0)
    path_pts: list = []
    rects: list = []
    pos = 0
    n = len(content)
    while pos < n:
        m = TOKEN_RE.match(content, pos)
        if not m:
            if content[pos:].strip() == b"":
                break
            raise ValueError(f"tokenizer stuck at {content[pos:pos+30]!r}")
        pos = m.end()
        t = m.group(1)
        if t.startswith(b"("):
            stack.append(unescape_pdf_string(t))
            continue
        if t.startswith(b"/"):
            stack.append(t.decode())
            continue
        if re.fullmatch(rb"[-+]?\d*\.?\d+", t):
            stack.append(float(t))
            continue
        op = t.decode()
        if op == "Tf":
            font, size = stack[-2], stack[-1]
        elif op == "Tm":
            tm = (stack[-2], stack[-1])
        elif op == "Tj":
            texts.append({"text": stack[-1], "x": round(tm[0], 2), "y": round(tm[1], 2), "font": font, "size": size})
        elif op == "re":
            rects.append(tuple(stack[-4:]))
        elif op == "m":
            path_pts = [(stack[-2], stack[-1])]
        elif op == "l":
            path_pts.append((stack[-2], stack[-1]))
        elif op in ("S", "B", "f"):
            if op in ("S", "B"):
                for (x, y, w, h) in rects:
                    edges += [((x, y), (x + w, y)), ((x, y + h), (x + w, y + h)), ((x, y), (x, y + h)), ((x + w, y), (x + w, y + h))]
                for a, b in zip(path_pts, path_pts[1:]):
                    edges.append((a, b))
            fills += rects if op in ("B", "f") else []
            rects, path_pts = [], []
        elif op == "cm":
            cm = stack[-6:]
        elif op == "Do":
            images.append({"name": stack[-1], "cm": cm})
        stack = [] if op not in ("BT",) else stack
    return {"texts": texts, "edges": edges, "images": images, "fills": fills}


# ----------------------------------------------------------------------------------------------
def load_lstree(p: pathlib.Path) -> dict:
    out = {}
    for ln in p.read_text(encoding="ascii", errors="replace").splitlines():
        if not ln.strip():
            continue
        meta, path = ln.split("\t", 1)
        _, _, oid = meta.split()
        out[path] = oid
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=pathlib.Path, required=True)
    ap.add_argument("--lstree", type=pathlib.Path, required=True)
    ap.add_argument("--wheels", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    repo = a.repo.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    tree = load_lstree(a.lstree)
    counts = defaultdict(int)

    # ---------------- 1. inventory vs git tree ----------------
    inv = []
    for rel, oid in sorted(tree.items()):
        b = (repo / rel).read_bytes()
        ok = blob_oid(b) == oid
        counts["tree_files"] += 1
        counts["tree_blob_match"] += ok
        if rel.startswith(("evaluation/", "research/carbon/reconciliation/")) or rel == ".gitattributes":
            inv.append({"path": rel, "size": len(b), "sha256": sha256(b), "git_blob": oid})
        if not ok:
            finding("high", "INV-EXPORT", f"export bytes differ from git blob for {rel}")

    man = json.loads((repo / "evaluation/manifests/corpus-manifest.json").read_text(encoding="utf-8"))
    tool = json.loads((repo / "evaluation/manifests/tooling-provenance.json").read_text(encoding="utf-8"))
    pubc = json.loads((repo / "evaluation/manifests/public-candidates.json").read_text(encoding="utf-8"))

    # ---------------- 2. wheels and scripts provenance ----------------
    wheel_res = []
    for w in tool["installed_wheels"]:
        p = a.wheels / w["wheel_filename"]
        b = p.read_bytes()
        r = {"wheel": w["wheel_filename"], "manifest_size": w["size_bytes"], "measured_size": len(b),
             "manifest_sha256": w["sha256"], "manifest_sha256_len": len(w["sha256"]), "measured_sha256": sha256(b)}
        r["match"] = r["manifest_size"] == r["measured_size"] and r["manifest_sha256"] == r["measured_sha256"] and len(w["sha256"]) == 64
        wheel_res.append(r)
        counts["wheels_match"] += r["match"]
        if not r["match"]:
            finding("high", "PROV-WHEEL", f"wheel mismatch {w['wheel_filename']}")
    script_res = []
    for s in tool["generation_and_verification_scripts"]:
        b = (repo / s["path"]).read_bytes()
        ok = len(b) == s["size_bytes"] and sha256(b) == s["sha256"] and blob_oid(b) == s["git_blob_oid"] and b.count(b"\r\n") == 0
        script_res.append({"path": s["path"], "match": ok})
        counts["scripts_match"] += ok

    # ---------------- 3. manifest / split / provenance links ----------------
    srcs = {}
    for sr in man["source_records"]:
        b = (repo / sr["source_path"]).read_bytes()
        ok = len(b) == sr["size_bytes"] and sha256(b) == sr["sha256"] and blob_oid(b) == sr["git_blob_oid"]
        counts["source_records_match"] += ok
        s = json.loads(b.decode("utf-8"))
        srcs[s["family_id"]] = s
        if s["split"] != sr["split"] or s["fixture_prefix"] != sr["fixture_prefix"]:
            finding("high", "MAN-SRC", f"source record meta mismatch {sr['family_id']}")
    fx = {f["fixture_id"]: f for f in man["fixtures"]}
    if len(fx) != 26 or len(man["fixtures"]) != 26:
        finding("high", "MAN-COUNT", "fixture count != 26")
    split_pages = defaultdict(lambda: [0, 0])
    for f in man["fixtures"]:
        b = (repo / f["file_path"]).read_bytes()
        e = (repo / f["expected_ground_truth_path"]).read_bytes()
        ok = (len(b) == f["size_bytes"] and sha256(b) == f["sha256"] and blob_oid(b) == f["git_blob_oid"]
              and sha256(e) == f["expected_ground_truth_sha256"] and blob_oid(e) == f["expected_ground_truth_git_blob_oid"])
        counts["fixture_hash_match"] += ok
        if not ok:
            finding("high", "MAN-HASH", f"hash/size mismatch {f['fixture_id']}")
        s = srcs[f["family_id"]]
        if f["split"] != s["split"] or not f["file_path"].startswith(f"evaluation/synthetic/pdfs/{f['family_id']}/"):
            finding("high", "MAN-SPLIT", f"split/family path mismatch {f['fixture_id']}")
        if f["source_record_sha256"] != sha256((repo / f["source_record_path"]).read_bytes()):
            finding("high", "MAN-SRCSHA", f"source sha mismatch {f['fixture_id']}")
        if f["parent_fixture_id"]:
            par = fx[f["parent_fixture_id"]]
            if par["family_id"] != f["family_id"] or par["split"] != f["split"] or par["sha256"] != f["parent_pdf_sha256"]:
                finding("high", "MAN-PARENT", f"parent link broken {f['fixture_id']}")
            counts["parent_links_ok"] += 1
        split_pages[f["split"]][0] += 1
        split_pages[f["split"]][1] += f["page_count"]
        if f["admission_status"] != "author_checked_pending_opus_wp0004_005":
            finding("info", "MAN-STATUS", f"unexpected admission status {f['fixture_id']}")
    total_pages = sum(f["page_count"] for f in man["fixtures"])

    # ---------------- 4. per-fixture PDF structure, transforms, text binding ----------------
    pdf_results = []
    v1_pixels: dict[str, list[bytes]] = {}
    page_records = []
    expected_cache = {}
    arithmetic = {}

    # Invoice arithmetic from SOURCES
    for fam, s in srcs.items():
        if s["doc_kind"] == "invoice":
            arithmetic[fam] = compute_invoice(s["accounting_spec"], fam)

    order = ["v0_clean", "v1_raster300", "v2_skew", "v3_hybrid"]
    for f in sorted(man["fixtures"], key=lambda z: (z["family_id"], order.index(z["variant_kind"]))):
        fid, fam, vk = f["fixture_id"], f["family_id"], f["variant_kind"]
        s = srcs[fam]
        data = (repo / f["file_path"]).read_bytes()
        mp = MiniPdf(data)
        pages = mp.pages()
        doc = pdfium.PdfDocument(data)
        res = {"fixture_id": fid, "family": fam, "split": f["split"], "variant": vk, "pages_own_parser": len(pages),
               "pages_pdfium": len(doc), "pages_manifest": f["page_count"], "pages_source": s["page_count"],
               "file_id_is_sha256_prefix_of_body": mp.file_id == sha256(data[:mp.xref_pos])[:32]}
        if not (len(pages) == len(doc) == f["page_count"] == s["page_count"]):
            finding("high", "PDF-PAGES", f"page count mismatch {fid}")
        exp = json.loads((repo / f["expected_ground_truth_path"]).read_text(encoding="utf-8"))
        expected_cache[fid] = exp
        for k_e, k_m in (("fixture_id", "fixture_id"), ("family_id", "family_id"), ("split", "split"),
                         ("variant_kind", "variant_kind"), ("parent_fixture_id", "parent_fixture_id"), ("page_count", "page_count")):
            if exp[k_e] != f[k_m]:
                finding("high", "EXP-META", f"{fid} expected.{k_e}={exp[k_e]!r} manifest={f[k_m]!r}")
        if exp["transform_params"] != f["generation_or_transform_params"]:
            finding("medium", "EXP-TPARAM", f"{fid} transform params differ between expected and manifest")
        per_page = []
        for pi, pg in enumerate(pages, start=1):
            it = interpret(pg["content"])
            n_bt = len(re.findall(rb"\bBT\b", pg["content"]))
            rec = {"page": pi, "mediabox": pg["mediabox"], "fonts": sorted(v["BaseFont"] for v in pg["fonts"].values()),
                   "font_embedded": any(v["embedded_FontFile"] for v in pg["fonts"].values()),
                   "bt_ops": n_bt, "text_runs": len(it["texts"]), "images": [{k: v for k, v in im.items() if k != "raw"} for im in pg["images"].values()]}
            if vk in ("v0_clean", "v3_hybrid"):
                if pg["mediabox"] != [0.0, 0.0, 612.0, 792.0]:
                    finding("high", "PDF-MBOX", f"{fid} p{pi} mediabox {pg['mediabox']}")
                if rec["font_embedded"]:
                    finding("medium", "PDF-FONT", f"{fid} embeds font program")
            else:
                im = list(pg["images"].values())
                if pg["fonts"] or n_bt or len(im) != 1:
                    finding("high", "PDF-IMGONLY", f"{fid} p{pi} not image-only")
                im = im[0]
                px = zlib.decompress(im["raw"])
                if len(px) != im["w"] * im["h"] * 3 or im["cs"] != "DeviceRGB" or im["bpc"] != 8:
                    finding("high", "PDF-IMG", f"{fid} p{pi} image format")
                exp_w, exp_h = round(im["w"] * 72 / 300, 2), round(im["h"] * 72 / 300, 2)
                if abs(pg["mediabox"][2] - exp_w) > 0.006 or abs(pg["mediabox"][3] - exp_h) > 0.006:
                    finding("high", "PDF-DPI", f"{fid} p{pi} mediabox {pg['mediabox']} vs {exp_w}x{exp_h}")
                rec["pixel_size"] = [im["w"], im["h"]]
                if vk == "v1_raster300":
                    v1_pixels.setdefault(fam, []).append((px, im["w"], im["h"]))
                else:
                    src_px, sw, sh = v1_pixels[fam][pi - 1]
                    angle = float(s["signed_skew_degrees"])
                    rot = Image.frombytes("RGB", (sw, sh), src_px).rotate(angle, resample=Image.Resampling.BILINEAR, expand=True, fillcolor=(255, 255, 255))
                    rec["rotation_reproduced_exact"] = rot.size == (im["w"], im["h"]) and rot.tobytes() == px
                    counts["v2_pages_rotation_exact"] += rec["rotation_reproduced_exact"]
                    if not rec["rotation_reproduced_exact"]:
                        finding("high", "XFORM-V2", f"{fid} p{pi} rotation not reproduced")
                    if exp["transform_params"].get("signed_angle_degrees_ccw") != angle:
                        finding("high", "XFORM-META", f"{fid} angle metadata")
                    tag = ("pos" if angle > 0 else "neg") + f"{int(abs(angle))}deg"
                    if not fid.endswith(tag):
                        finding("medium", "XFORM-NAME", f"{fid} name vs angle")
            per_page.append(rec)
            page_records.append({"fixture_id": fid, "page": pi, **{k: rec[k] for k in ("mediabox",)}})
        # v1: reproduce from parent v0 via pdfium render
        if vk == "v1_raster300":
            pdata = (repo / fx[f["parent_fixture_id"]]["file_path"]).read_bytes()
            pdoc = pdfium.PdfDocument(pdata)
            for pi in range(len(pdoc)):
                pil = pdoc[pi].render(scale=300 / 72).to_pil().convert("RGB")
                px, w, h = v1_pixels[fam][pi]
                ok = pil.size == (w, h) and pil.tobytes() == px
                per_page[pi]["raster_reproduced_exact_from_v0"] = ok
                counts["v1_pages_raster_exact"] += ok
                if not ok:
                    finding("high", "XFORM-V1", f"{fid} p{pi+1} raster not reproduced")
            pdoc.close()
            tp = exp["transform_params"]
            if tp.get("pixel_size_per_page") != [v1_pixels[fam][0][1], v1_pixels[fam][0][2]]:
                finding("medium", "XFORM-V1META", f"{fid} pixel_size_per_page {tp.get('pixel_size_per_page')}")
        res["pages"] = per_page
        pdf_results.append(res)
        doc.close()

    # README / provenance claim on v1 pixel size
    v1_sizes = sorted({(w, h) for fam in v1_pixels for (_, w, h) in v1_pixels[fam]})
    readme = (repo / "evaluation/README.md").read_text(encoding="utf-8")
    if v1_sizes != [(2550, 3300)] and "2550 x 3300" in readme:
        finding("low", "DOC-PIXELS", f"README claims 2550 x 3300 RGB px/page but actual v1 page rasters are {v1_sizes}")

    # ---------------- 5. bind sources <-> expected <-> visible text layer (v0/v3) ----------------
    text_checks = defaultdict(int)
    text_fail = []

    def need(cond: bool, ctx: str):
        text_checks["assertions"] += 1
        if not cond:
            text_fail.append(ctx)

    def page_runs(fid: str, pno: int):
        data = (repo / fx[fid]["file_path"]).read_bytes()
        return interpret(MiniPdf(data).pages()[pno - 1]["content"])

    def runs_at_y(texts, y, tol=0.01):
        return sorted([t for t in texts if abs(t["y"] - y) <= tol], key=lambda t: t["x"])

    def joined(texts):
        return " ".join(t["text"] for t in texts)

    arith_out = {}
    for fam, s in sorted(srcs.items()):
        v0 = f"{s['fixture_prefix']}-v0-clean"
        variants = [x for x in fx.values() if x["family_id"] == fam]
        text_variants = [x["fixture_id"] for x in variants if x["variant_kind"] in ("v0_clean", "v3_hybrid")]
        P = s["page_count"]
        for tv in text_variants:
            pr = {p: page_runs(tv, p) for p in range(1, P + 1)}
            allt = {p: [t["text"] for t in pr[p]["texts"]] for p in pr}
            # sentinels / ribbons
            for sen in s.get("page_sentinels", []):
                rib = [t for t in allt[sen["page_number"]] if sen["sentinel_id"] in t]
                need(len(rib) == 1 and sen["repeated_doc_id"] in rib[0] and sen["page_label"] in rib[0]
                     and (sen.get("repeated_auth_id") or sen.get("repeated_contract_id")) in rib[0], f"{tv} sentinel {sen['sentinel_id']}")
                for other in range(1, P + 1):
                    if other != sen["page_number"]:
                        need(not any(sen["sentinel_id"] in t for t in allt[other]), f"{tv} sentinel {sen['sentinel_id']} leaked to p{other}")
            for lk in s.get("cross_page_links", []):
                if "value" in lk and "pages" in lk:
                    for p in lk["pages"]:
                        need(any(lk["value"] in t for t in allt[p]), f"{tv} link {lk['link_id']} p{p}")
            if s["doc_kind"] == "invoice":
                A = arithmetic[fam]
                b = s["banner"]
                need(b["vendor_name"] in allt[1] and b["document_title"] in allt[1], f"{tv} banner")
                for p in range(1, P + 1):
                    need(b["vendor_contact"] in allt[p], f"{tv} contact p{p}")
                    if p > 1:
                        need(b["document_title"] + " (CONTINUED)" in allt[p], f"{tv} continued title p{p}")
                for ab in s["address_blocks"]:
                    need(ab["title"] in allt[1] and all(l in allt[1] for l in ab["lines"]), f"{tv} address {ab['block_id']}")
                for hf in s["header_fields"]:
                    lab = [t for t in pr[1]["texts"] if t["text"] == hf["label"] + ":"]
                    need(len(lab) == 1, f"{tv} header label {hf['field_id']}")
                    if lab:
                        val = [t for t in pr[1]["texts"] if abs(t["x"] - lab[0]["x"]) < 0.01 and abs(t["y"] - (lab[0]["y"] - 10.0)) < 0.01]
                        if hf["is_absent"]:
                            need(len(val) == 0, f"{tv} absent {hf['field_id']} has text")
                        else:
                            need(len(val) == 1 and val[0]["text"] == hf["printed_text"], f"{tv} header value {hf['field_id']}")
                # rule notice wrapped text and literal amounts
                notice = s["accounting_spec"]["printed_rule_notice"]
                need(notice in joined(pr[1]["texts"]), f"{tv} printed rule notice")
                # line item rows bound by y to own arithmetic
                for r in A["rows"]:
                    texts = pr[r["page"]]["texts"]
                    rid = [t for t in texts if t["text"] == r["row_id"] and t["x"] < 50]
                    need(len(rid) == 1, f"{tv} row {r['row_id']} id on p{r['page']}")
                    if not rid:
                        continue
                    row = runs_at_y(texts, rid[0]["y"])
                    vals = [t["text"] for t in row]
                    want = [r["row_id"], r["sku"]]
                    tail = [r["qty_printed"], usd(r["unit_price_c"]), pct(r["rate4"]), usd(r["disc_c"]), "T" if r["taxable"] else "N", usd(r["net_c"])]
                    need(vals[:2] == want and vals[-6:] == tail, f"{tv} row {r['row_id']} visible={vals} own={want + tail}")
                    y0 = rid[0]["y"]
                    single = [t for t in texts if 134 <= t["x"] < 298 and abs(t["y"] - y0) < 0.01]
                    if single:
                        desc_lines = [single[0]["text"]]
                    else:
                        desc_lines, k = [], 0
                        while True:
                            ln = [t for t in texts if 134 <= t["x"] < 298 and abs(t["y"] - (y0 + 0.5 - k * (rid[0]["size"] + 2.2))) < 0.01]
                            if not ln:
                                break
                            desc_lines.append(ln[0]["text"])
                            k += 1
                    need(" ".join(desc_lines) == r["description"], f"{tv} row {r['row_id']} description visible={desc_lines}")
                    text_checks["invoice_rows_bound"] += 1
                # rows only on declared pages and in order
                for p in range(1, P + 1):
                    ids = [t["text"] for t in sorted(pr[p]["texts"], key=lambda t: -t["y"]) if re.fullmatch(r"L\d\d", t["text"]) and t["x"] < 50]
                    need(ids == [r["row_id"] for r in A["rows"] if r["page"] == p], f"{tv} row order p{p} {ids}")
                # summary on final page only
                last = pr[P]["texts"]
                summary = [("Line Net Subtotal:", A["subtotal"]), ("Taxable Subtotal (Tax=T Rows):", A["taxable"]),
                           (f"Sales Tax ({A['tax_rate_printed']} on Taxable Subtotal):", A["tax"])]
                summary += [(lbl + ":", amt) for (_, lbl, amt, _) in A["fees"]] or [("Non-Taxable Fees:", 0)]
                summary += [("CURRENT INVOICE TOTAL:", A["invoice_total"]), ("Prior Unpaid Balance:", A["previous_balance"]),
                            ("Payments / Credits Applied:", A["payments"]), ("TOTAL AMOUNT DUE:", A["amount_due"])]
                for lbl, amt in summary:
                    L = [t for t in last if t["text"] == lbl]
                    need(len(L) == 1, f"{tv} summary label {lbl}")
                    if L:
                        V = [t for t in runs_at_y(last, L[0]["y"]) if t["x"] > 450]
                        need(len(V) == 1 and V[0]["text"] == usd(amt), f"{tv} summary {lbl} visible={[v['text'] for v in V]} own={usd(amt)}")
                        text_checks["summary_values_bound"] += 1
                    for p in range(1, P):
                        need(lbl not in allt[p], f"{tv} summary {lbl} leaked to p{p}")
                need(A["tax_rate_printed"] == pct(A["tax_rate4"]), f"{fam} tax rate printed vs value")
                need(A["taxable"] >= 0, f"{fam} taxable >= 0")
                for r in A["rows"]:
                    if r["credit"]:
                        need(r["rate4"] == 0 and not r["taxable"], f"{fam} credit row rule {r['row_id']}")
                for p in range(1, P):
                    need(any(t.startswith(f"[Line items continue on Page {p+1};") for t in allt[p]), f"{tv} continuation marker p{p}")
                need(s["accounting_spec"]["fees"] == [] or all(not fz["is_taxable"] for fz in s["accounting_spec"]["fees"]), f"{fam} fees non-taxable")
                need(s["header_fields"][0]["printed_text"] in s["remittance_note"], f"{fam} remittance cites invoice number")
                need(s["remittance_note"] in joined(last) or all(w in joined(last) for w in s["remittance_note"].split()), f"{tv} remittance note")
            else:
                b = s["banner"]
                need(b["organization"] in allt[1] and b["document_title"] in allt[1] and b["subtitle"].strip() in allt[1], f"{tv} banner")
                for p in range(1, P + 1):
                    need(b["contact_line"] in allt[p], f"{tv} contact p{p}")
                for col in s["header_columns"]:
                    need(col["group_title"] in allt[1], f"{tv} group {col['group_title']}")
                    for fld in col["fields"]:
                        lab = [t for t in pr[1]["texts"] if t["text"] == fld["label"] + ":"]
                        need(len(lab) == 1, f"{tv} label {fld['field_id']}")
                        if lab:
                            val = [t for t in runs_at_y(pr[1]["texts"], lab[0]["y"]) if 0 < t["x"] - lab[0]["x"] < 200]
                            if fld["is_absent"]:
                                need(len(val) == 0, f"{tv} absent {fld['field_id']} has text {val}")
                            else:
                                need(len(val) == 1 and val[0]["text"] == fld["printed_text"], f"{tv} header {fld['field_id']}")
                for cb in s.get("checkbox_strip") or []:
                    need(f"{cb['label']} {cb['printed_text']}" in allt[1], f"{tv} checkbox {cb['field_id']}")
                    need((cb["printed_text"] == "[X]") == (cb["normalized_value"] == "true") and cb["printed_text"] in ("[X]", "[ ]"), f"{fam} checkbox norm {cb['field_id']}")
                for pb in s.get("prose_blocks", []):
                    need(pb["label"] in allt[pb["page_number"]], f"{tv} prose label {pb['field_id']}")
                    need(pb["printed_text"] in joined(pr[pb["page_number"]]["texts"]), f"{tv} prose {pb['field_id']}")
                for tb in s.get("tables", []):
                    first_col = tb["columns"][0]["col_id"]
                    for p in tb["page_numbers"]:
                        title = tb["title"] + (" (CONTINUED)" if p in tb.get("repeated_header_pages", []) else "")
                        need(title in allt[p], f"{tv} table title {tb['table_id']} p{p}")
                        need(all(c["header"] in allt[p] for c in tb["columns"]), f"{tv} headers {tb['table_id']} p{p}")
                        if p < max(tb["page_numbers"]):
                            need(f"[Table {tb['table_id']} continues on Page {p+1}]" in allt[p], f"{tv} continuation {tb['table_id']} p{p}")
                    for r in tb["rows"]:
                        texts = pr[r["page_number"]]["texts"]
                        key = r["cells"][first_col]["printed_text"]
                        anchors = [t for t in texts if t["text"] == key and abs(t["x"] - 44) < 0.01]
                        cand = None
                        for an in anchors:
                            row = runs_at_y(texts, an["y"])
                            if len(row) >= len(tb["columns"]) - 1:
                                cand = an
                        need(cand is not None, f"{tv} row anchor {tb['table_id']} {r['row_id']}")
                        if cand is None:
                            continue
                        x = 40.0
                        for c in tb["columns"]:
                            cell = [t for t in texts if x <= t["x"] < x + c["width_pt"] and cand["y"] - 60 < t["y"] <= cand["y"] + 0.01]
                            # take only lines belonging to this row: contiguous 9.5pt steps from the anchor line
                            lines, yy = [], cand["y"]
                            while True:
                                ln = [t for t in cell if abs(t["y"] - yy) < 0.01]
                                if not ln:
                                    break
                                lines.append(ln[0]["text"])
                                yy -= 9.5
                            need(" ".join(lines) == r["cells"][c["col_id"]]["printed_text"], f"{tv} cell {tb['table_id']} {r['row_id']} {c['col_id']} visible={lines}")
                            x += c["width_pt"]
                        text_checks["table_rows_bound"] += 1
                    # continuation rows/order
                for lk in s.get("cross_page_links", []):
                    if lk["link_type"] == "table_continuation":
                        tb = next(t for t in s["tables"] if t["table_id"] == lk["table_id"])
                        fp = [r["row_id"] for r in tb["rows"] if r["page_number"] == lk["from_page"]]
                        tp = [r["row_id"] for r in tb["rows"] if r["page_number"] == lk["to_page"]]
                        need(fp[-1] == lk["from_last_row"] and tp[0] == lk["to_first_row"], f"{fam} {lk['link_id']}")
                    if lk["link_type"] == "cross_table_serial_referential_integrity":
                        st = next(t for t in s["tables"] if t["table_id"] == lk["source_table"])
                        tt = next(t for t in s["tables"] if t["table_id"] == lk["target_table"])
                        a1 = [r["cells"]["serial_no"]["printed_text"] for r in st["rows"]]
                        a2 = [r["cells"]["serial_no"]["printed_text"] for r in tt["rows"]]
                        need(a1 == lk["serial_numbers"] and sorted(a2) == sorted(a1), f"{fam} serial integrity")
                for sf in s.get("signoff_fields", []):
                    need(sf["label"] + ":" in allt[P], f"{tv} signoff label {sf['field_id']}")
                    need(sf["printed_text"] in joined(pr[P]["texts"]), f"{tv} signoff {sf['field_id']}")
            # hybrid stamp text must be absent from the text layer
            if s.get("hybrid_control"):
                hc = s["hybrid_control"]
                for p in range(1, P + 1):
                    need(hc["printed_text"] not in joined(pr[p]["texts"]) and "RASTER" not in joined(pr[p]["texts"]), f"{tv} hybrid text absent from text layer p{p}")

        # ---- expected JSON vs sources and own arithmetic (all variants) ----
        for x in variants:
            e = expected_cache[x["fixture_id"]]
            ef = {d["field_id"]: d for d in e["expected_fields"]}
            ab = {d["field_id"] for d in e["expected_absences"]}
            src_fields, src_abs = {}, set()
            if s["doc_kind"] == "invoice":
                A = arithmetic[fam]
                for blk in s["address_blocks"]:
                    jj = ", ".join(blk["lines"])
                    src_fields[f"address_{blk['block_id']}"] = (jj, jj)
                for hf in s["header_fields"]:
                    if hf["is_absent"]:
                        src_abs.add(hf["field_id"])
                    else:
                        src_fields[hf["field_id"]] = (hf["printed_text"], hf["normalized_value"])
                own = {"subtotal": A["subtotal"], "taxable_subtotal": A["taxable"], "tax_amount": A["tax"],
                       "invoice_total": A["invoice_total"], "previous_balance": A["previous_balance"],
                       "payments_credits_applied": A["payments"], "amount_due": A["amount_due"]}
                for fid_, lbl, amt, _ in A["fees"]:
                    own["fee_" + fid_.lower().replace("-", "_")] = amt
                if not A["fees"]:
                    own["non_taxable_fees"] = 0
                for k, v in own.items():
                    src_fields[k] = (usd(v), norm2(v))
                # invoice_accounting block
                ia = e["invoice_accounting"]
                need(ia is not None, f"{x['fixture_id']} invoice_accounting present")
                if ia:
                    sm = ia["summary"]
                    for k, v in (("subtotal", A["subtotal"]), ("taxable_subtotal", A["taxable"]), ("tax_amount", A["tax"]),
                                 ("non_taxable_fees", A["fee_sum"]), ("invoice_total", A["invoice_total"]),
                                 ("previous_balance", A["previous_balance"]), ("payments_credits_applied", A["payments"]), ("amount_due", A["amount_due"])):
                        need(sm[k]["normalized_value"] == norm2(v) and sm[k]["printed_text"] == usd(v), f"{x['fixture_id']} accounting.summary.{k}")
                    need(sm["tax_rate"]["normalized_value"] == rate_norm(A["tax_rate4"]) and sm["tax_rate"]["printed_text"] == A["tax_rate_printed"], f"{x['fixture_id']} tax rate")
                    for er, r in zip(ia["rows"], A["rows"]):
                        need(er["row_id"] == r["row_id"] and er["gross_line_norm"] == norm2(r["gross_c"]) and er["gross_line_printed"] == usd(r["gross_c"])
                             and er["line_discount_norm"] == norm2(r["disc_c"]) and er["net_line_norm"] == norm2(r["net_c"]) and er["net_line_printed"] == usd(r["net_c"])
                             and er["unit_price_norm"] == norm2(r["unit_price_c"]) and er["discount_rate_norm"] == rate_norm(r["rate4"]) and er["discount_rate_printed"] == pct(r["rate4"])
                             and er["quantity_norm"] == r["qty_norm"] and er["qty_unit_printed"] == r["qty_printed"] and er["is_taxable"] == r["taxable"], f"{x['fixture_id']} accounting row {r['row_id']}")
                    need(len(ia["rows"]) == len(A["rows"]), f"{x['fixture_id']} accounting row count")
                # expected table
                tbl = e["expected_tables"]
                need(len(tbl) == 1 and tbl[0]["table_id"] == "line_items" and len(tbl[0]["rows"]) == len(A["rows"]), f"{x['fixture_id']} line table shape")
                if tbl:
                    for er, r in zip(tbl[0]["rows"], A["rows"]):
                        c = er["cells"]
                        want = {"row_id": (r["row_id"], r["row_id"]), "sku": (r["sku"], r["sku"]), "description": (r["description"], r["description"]),
                                "qty_unit": (r["qty_printed"], r["qty_norm"]), "unit_price": (usd(r["unit_price_c"]), norm2(r["unit_price_c"])),
                                "discount_rate": (pct(r["rate4"]), rate_norm(r["rate4"])), "line_discount": (usd(r["disc_c"]), norm2(r["disc_c"])),
                                "tax_flag": ("T" if r["taxable"] else "N",) * 2, "net_line": (usd(r["net_c"]), norm2(r["net_c"]))}
                        for k, (pt, nv) in want.items():
                            need(c[k]["printed_text"] == pt and c[k]["normalized_value"] == nv, f"{x['fixture_id']} cell {r['row_id']}.{k}")
                        need(er["page_number"] == r["page"], f"{x['fixture_id']} row page {r['row_id']}")
                        text_checks["expected_cells_checked"] += len(want)
            else:
                for col in s["header_columns"]:
                    for fld in col["fields"]:
                        if fld["is_absent"]:
                            src_abs.add(fld["field_id"])
                        else:
                            src_fields[fld["field_id"]] = (fld["printed_text"], fld["normalized_value"])
                for cb in s.get("checkbox_strip") or []:
                    src_fields[cb["field_id"]] = (cb["printed_text"], cb["normalized_value"])
                for pb in s.get("prose_blocks", []):
                    src_fields[pb["field_id"]] = (pb["printed_text"], pb["normalized_value"])
                for sf in s.get("signoff_fields", []):
                    src_fields[sf["field_id"]] = (sf["printed_text"], sf["normalized_value"])
                if x["variant_kind"] == "v3_hybrid":
                    hc = s["hybrid_control"]
                    src_fields[hc["field_id"]] = (hc["printed_text"], hc["normalized_value"])
                    hf = ef.get(hc["field_id"], {})
                    x0, y0, x1, y1 = hc["box_pt"]
                    area = (x1 - x0) * (y1 - y0) / (612 * 792)
                    need(hf.get("modality") == "embedded_raster_only" and hf.get("page_number") == hc["target_page"] and abs(hf.get("page_area_ratio", -1) - round(area, 5)) < 1e-9, f"{x['fixture_id']} hybrid field meta")
                    text_checks["hybrid_area_ratio_x1000"] = text_checks.get("hybrid_area_ratio_x1000", 0)
                    arith_out.setdefault("hybrid_area", {})[x["fixture_id"]] = round(area, 5)
                exp_tables = {t["table_id"]: t for t in e["expected_tables"]}
                for tb in s.get("tables", []):
                    et = exp_tables.get(tb["table_id"])
                    need(et is not None and len(et["rows"]) == len(tb["rows"]), f"{x['fixture_id']} table {tb['table_id']}")
                    if et:
                        for er, r in zip(et["rows"], tb["rows"]):
                            for cid, cv in r["cells"].items():
                                need(er["cells"][cid]["printed_text"] == cv["printed_text"] and er["cells"][cid]["normalized_value"] == cv["normalized_value"], f"{x['fixture_id']} {tb['table_id']} {r['row_id']} {cid}")
                                text_checks["expected_cells_checked"] += 1
                need(e["invoice_accounting"] is None, f"{x['fixture_id']} no accounting on non-invoice")
            need(set(ef) == set(src_fields), f"{x['fixture_id']} expected field set {sorted(set(ef) ^ set(src_fields))}")
            for k, (pt, nv) in src_fields.items():
                if k in ef:
                    need(ef[k]["printed_text"] == pt and ef[k]["normalized_value"] == nv, f"{x['fixture_id']} field {k} exp=({ef[k]['printed_text']!r},{ef[k]['normalized_value']!r}) own=({pt!r},{nv!r})")
                    text_checks["expected_fields_checked"] += 1
            need(ab == src_abs, f"{x['fixture_id']} absences")
            need(e["page_sentinels"] == s.get("page_sentinels", []) and e["cross_page_links"] == s.get("cross_page_links", []), f"{x['fixture_id']} sentinels/links")
            need(e["expected_adjacent_page_pairs"] == [[p, p + 1] for p in range(1, s["page_count"])], f"{x['fixture_id']} adjacent pairs")
            need(e["split_disclosure"] == "fixed_test_partition_not_blind_to_corpus_author", f"{x['fixture_id']} split disclosure")
            exp_route = "eligible_digital_text_layer" if x["variant_kind"] == "v0_clean" else "must_route_to_ocr"
            need(e["expected_routing_for_e3"] == exp_route, f"{x['fixture_id']} routing label")
            if x["variant_kind"] in ("v1_raster300", "v2_skew"):
                need(all(d["bbox_pt"] is None for d in e["expected_fields"]), f"{x['fixture_id']} bbox nulled")
        # variant invariance relative to v0 expected
        e0 = expected_cache[v0]
        for x in variants:
            if x["variant_kind"] in ("v1_raster300", "v2_skew"):
                e = expected_cache[x["fixture_id"]]
                strip = lambda fl: [{k: v for k, v in d.items() if k != "bbox_pt"} for d in fl]
                need(strip(e["expected_fields"]) == strip(e0["expected_fields"]) and e["expected_tables"] == e0["expected_tables"]
                     and e["expected_absences"] == e0["expected_absences"] and e["invoice_accounting"] == e0["invoice_accounting"], f"{x['fixture_id']} truth == v0 truth")

        if s["doc_kind"] == "invoice":
            A = arithmetic[fam]
            notice = s["accounting_spec"]["printed_rule_notice"]
            lits = re.findall(r"\$[\d,]+\.\d\d", notice)
            own_vals = {usd(v) for v in (A["subtotal"], A["taxable"], A["tax"], A["invoice_total"], A["amount_due"])} | {usd(f[2]) for f in A["fees"]}
            for lit in lits:
                need(lit in own_vals, f"{fam} notice literal {lit} not a computed value")
            rem_lits = re.findall(r"\$[\d,]+\.\d\d", s["remittance_note"])
            own_vals_rem = own_vals | {usd(A["previous_balance"]), usd(A["payments"])}
            for lit in rem_lits:
                need(lit in own_vals_rem, f"{fam} remittance literal {lit} not a computed/declared value")
            lits = lits + [f"remittance:{x}" for x in rem_lits]
            for pl in re.findall(r"\d+\.\d\d%", notice):
                need(pl == A["tax_rate_printed"], f"{fam} notice rate {pl}")
            arith_out[fam] = {
                "rows": [{"row": r["row_id"], "page": r["page"], "gross": norm2(r["gross_c"]), "disc_rate": rate_norm(r["rate4"]), "disc": norm2(r["disc_c"]),
                          "net": norm2(r["net_c"]), "tax": "T" if r["taxable"] else "N"} for r in A["rows"]],
                "subtotal": norm2(A["subtotal"]), "taxable_subtotal": norm2(A["taxable"]), "tax_rate": rate_norm(A["tax_rate4"]), "tax": norm2(A["tax"]),
                "fees": [[f[0], norm2(f[2])] for f in A["fees"]], "invoice_total": norm2(A["invoice_total"]),
                "previous_balance": norm2(A["previous_balance"]), "payments": norm2(A["payments"]), "amount_due": norm2(A["amount_due"]),
                "notice_literals_checked": lits, "taxable_rows": sum(r["taxable"] for r in A["rows"]), "discount_rows": sum(r["rate4"] > 0 for r in A["rows"]),
                "credit_rows": [r["row_id"] for r in A["rows"] if r["credit"]],
            }
            hf = {h["field_id"]: h for h in s["header_fields"]}
            mt = re.search(r"Net (\d+)", hf.get("payment_terms", {}).get("printed_text", ""))
            if mt and "due_date" in hf and "invoice_date" in hf:
                n = int(mt.group(1))
                d0 = date.fromisoformat(hf["invoice_date"]["printed_text"])
                need(date.fromisoformat(hf["due_date"]["printed_text"]) == d0 + timedelta(days=n), f"{fam} due date = invoice date + terms")
        if fam == "F01":
            r = s["tables"][0]["rows"][0]["cells"]
            h1, m1 = map(int, r["time_in"]["printed_text"].split(":"))
            h2, m2 = map(int, r["time_out"]["printed_text"].split(":"))
            need(((h2 * 60 + m2) - (h1 * 60 + m1)) == parse_fixed(r["hours"]["printed_text"], 2) * 60 // 100, "F01 labor hours = out - in")
        if fam == "F03":
            for r in s["tables"][0]["rows"]:
                marks = [r["cells"][k]["printed_text"] for k in ("pass_mark", "fail_mark", "na_mark")]
                need(marks.count("X") == 1 and marks.count("-") == 2, f"F03 {r['row_id']} exactly one mark")

    # cross-split entity leakage (identifiers shared between dev and eval_holdout sources)
    ident = defaultdict(set)
    for fam, s in srcs.items():
        for tok in set(re.findall(r"\b[A-Z]{2,5}-\d{3,6}\b", json.dumps(s))):
            ident[tok].add(s["split"])
    cross = sorted(k for k, v in ident.items() if len(v) > 1)

    # ---------------- 6. glyph geometry: clipping / overlap on text-layer pages ----------------
    geom = []
    for f in sorted(man["fixtures"], key=lambda z: z["fixture_id"]):
        if f["variant_kind"] not in ("v0_clean", "v3_hybrid"):
            continue
        data = (repo / f["file_path"]).read_bytes()
        doc = pdfium.PdfDocument(data)
        mp = MiniPdf(data).pages()
        for pi in range(len(doc)):
            page = doc[pi]
            W, H = page.get_size()
            tp = page.get_textpage()
            n = tp.count_chars()
            boxes = []
            for i in range(n):
                ch = tp.get_text_range(i, 1)
                if not ch.strip():
                    continue
                l, b_, r, t = tp.get_charbox(i, loose=False)
                if r - l <= 0 or t - b_ <= 0:
                    continue
                boxes.append((l, b_, r, t, ch, i))
            it = interpret(mp[pi]["content"])
            crossings, outside, overlaps, img_overlap = [], 0, [], 0
            tol = 0.10
            min_gap_v = 99.0
            for (l, b_, r, t, ch, i) in boxes:
                if l < 0 or b_ < 0 or r > W or t > H:
                    outside += 1
                for (x1, y1), (x2, y2) in it["edges"]:
                    if abs(x1 - x2) < 1e-6:  # vertical
                        if min(y1, y2) < t - tol and max(y1, y2) > b_ + tol:
                            if l + tol < x1 < r - tol:
                                crossings.append((ch, round(l, 2), round(b_, 2), "v", round(x1, 2)))
                            else:
                                min_gap_v = min(min_gap_v, abs(x1 - l), abs(x1 - r))
                    elif abs(y1 - y2) < 1e-6:
                        if min(x1, x2) < r - tol and max(x1, x2) > l + tol and b_ + tol < y1 < t - tol:
                            crossings.append((ch, round(l, 2), round(b_, 2), "h", round(y1, 2)))
                for im in it["images"]:
                    a_, _, _, d_, e_, f_ = im["cm"]
                    if l < e_ + a_ and r > e_ and b_ < f_ + d_ and t > f_:
                        img_overlap += 1
            grid = defaultdict(list)
            for k, bx in enumerate(boxes):
                grid[(int(bx[0] // 6), int(bx[1] // 6))].append(k)
            for k, (l, b_, r, t, ch, i) in enumerate(boxes):
                gx, gy = int(l // 6), int(b_ // 6)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        for k2 in grid.get((gx + dx, gy + dy), []):
                            if k2 <= k:
                                continue
                            l2, b2, r2, t2, ch2, i2 = boxes[k2]
                            iw, ih = min(r, r2) - max(l, l2), min(t, t2) - max(b_, b2)
                            if iw > 0 and ih > 0:
                                ar = min((r - l) * (t - b_), (r2 - l2) * (t2 - b2))
                                if iw * ih > 0.2 * ar:
                                    overlaps.append((ch, ch2, round(l, 2), round(b_, 2)))
            geom.append({"fixture_id": f["fixture_id"], "page": pi + 1, "glyphs": len(boxes), "edges": len(it["edges"]),
                         "rule_crossings": len(crossings), "crossing_samples": crossings[:5], "outside_page": outside,
                         "glyph_overlaps": len(overlaps), "overlap_samples": overlaps[:5], "glyphs_over_embedded_image": img_overlap,
                         "min_glyph_to_vertical_rule_gap_pt": round(min_gap_v, 2)})
            if crossings or outside or overlaps or img_overlap:
                finding("medium", "GEOM", f"{f['fixture_id']} p{pi+1}: crossings={len(crossings)} outside={outside} overlaps={len(overlaps)} over_image={img_overlap}")
            tp.close()
            page.close()
        doc.close()

    # ---------------- 7. public candidates ----------------
    pub = []
    for c in pubc.get("candidates", []):
        pub.append({k: c.get(k) for k in ("candidate_id", "filename", "admission_status", "bytes_copied_into_repository") if k in c} | {"keys": sorted(c.keys())})
    pdf_in_repo = sorted(str(p.relative_to(repo)).replace("\\", "/") for p in repo.rglob("*.pdf"))
    non_fixture_pdfs = [p for p in pdf_in_repo if p not in {f["file_path"] for f in man["fixtures"]}]

    # ---------------- outputs ----------------
    for t in text_fail:
        finding("high", "BIND", t)
    summary = {
        "tool": "docs/reviews/WP-0004/eld-rd-reviewer/helpers/rd005_verify.py",
        "python": sys.version.split()[0], "pypdfium2": pdfium.version.PYPDFIUM_INFO.__str__(), "pdfium": str(pdfium.version.PDFIUM_INFO),
        "pillow": Image.__version__,
        "counts": dict(counts), "total_pdfs": len(man["fixtures"]), "total_pages": total_pages,
        "split_pdfs_pages": {k: v for k, v in split_pages.items()}, "v1_pixel_sizes": v1_sizes,
        "binding_checks": dict(text_checks), "binding_failures": len(text_fail),
        "rounding_ties_exercised": TIES, "cross_split_shared_identifiers": cross,
        "wheels": wheel_res, "scripts": script_res, "public_candidates": pub, "pdfs_in_tree": len(pdf_in_repo),
        "non_fixture_pdfs_in_tree": non_fixture_pdfs, "findings": FINDINGS,
    }
    (a.out / "verify-summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    (a.out / "inventory.json").write_text(json.dumps(inv, indent=0) + "\n", encoding="utf-8")
    (a.out / "pdf-structure.json").write_text(json.dumps(pdf_results, indent=0) + "\n", encoding="utf-8")
    (a.out / "arithmetic.json").write_text(json.dumps(arith_out, indent=1) + "\n", encoding="utf-8")
    (a.out / "glyph-geometry.json").write_text(json.dumps(geom, indent=0) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("counts", "total_pdfs", "total_pages", "split_pdfs_pages", "v1_pixel_sizes", "binding_checks", "binding_failures", "cross_split_shared_identifiers")}, indent=1))
    print("TIES", TIES)
    print("FINDINGS", len(FINDINGS))
    for fd in FINDINGS[:80]:
        print(" ", fd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
