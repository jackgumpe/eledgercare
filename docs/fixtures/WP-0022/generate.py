"""Generate WP-0022 from fixed synthetic case definitions. This program performs no recognition."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform

from PIL import Image, ImageDraw, ImageFont, __version__ as pillow_version, features


PX = (2550, 3300)
PT = (612, 792)
SCALE = PX[0] / PT[0]
FONTS = {
    "arial.ttf": "edfbd22a3d088fc2f5d7c79b8c9c732df6dc878a60f0a80be0f92a3c7a634404",
    "arialbd.ttf": "4d59199834e7439c67ea4949407639961060b21b173833f566eb60ac6fd8f5af",
}
P_SMALL = (39, 67, 128, 151, 220)
C_SMALL = (83, 111, 172, 195, 264)
P_WIDE = (39, 113, 292, 352, 475)
C_WIDE = (67, 147, 318, 380, 499)
HEADER = ("Date", "Description", "Ref", "Amount")
PROPERTIES = ("Rowan Quay", "Ember Mill", "Juniper Gate", "Silver Grove",
              "Copper Walk", "Cobalt Reach", "Mallow Court", "Mallow Court")
UNITS = ("Elm", "Ash", "Bay", "Pine", "Yew", "Oak", "Lime", "Lime")
CREWS = ("Bramble", "Gannet", "Sparrow", "Beryl", "Saffron", "Alder", "Fennel", "Fennel")
CLERKS = ("Oriole", "Laurel")
MONTHS = ("May", "Jan", "Mar", "Oct", "Jun", "Feb", "Jul", "Jul")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def px(pt):
    return round(pt * SCALE)


def box_pt(box):
    return [round(v / SCALE, 5) for v in box]


def union(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def word_at(text, x, right=False):
    return (text, x, right)


class Page:
    def __init__(self, number, fonts):
        self.number = number
        self.fonts = fonts
        self.image = Image.new("RGB", PX, "white")
        self.draw = ImageDraw.Draw(self.image)
        self.lines = []

    def line(self, baseline, tokens, font="text"):
        words = []
        typeface = self.fonts[font]
        for text, x, right in tokens:
            l, t, r, b = typeface.getbbox(text, anchor="ls")
            mask = Image.new("L", (r - l, b - t))
            ImageDraw.Draw(mask).text((-l, -t), text, font=typeface, anchor="ls", fill=255)
            ink = mask.getbbox()
            tight = mask.crop(ink)
            x0 = px(x) - (tight.width if right else 0)
            y0 = px(baseline) + t + ink[1]
            xy = (x0, y0, x0 + tight.width, y0 + tight.height)
            self.image.paste((18, 18, 18), xy, tight)
            words.append(dict(text=text, bbox=box_pt(xy),
                              ref=f"p{self.number}:L{len(self.lines)+1}:W{len(words)+1}"))
        self.lines.append({"words": words})
        return words

    def phrase(self, text, x, font="text"):
        tokens = []
        for word in text.split():
            tokens.append(word_at(word, x))
            x += self.fonts[font].getlength(word + " ") / SCALE
        return tokens

    def grid(self, cols, ys):
        for y in ys:
            self.draw.line((px(cols[0]), px(y), px(cols[-1]), px(y)),
                           fill=(145, 145, 145), width=4)
        for x in cols:
            self.draw.line((px(x), px(ys[0]), px(x), px(ys[-1])),
                           fill=(145, 145, 145), width=4)

    def save(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.image.save(path, dpi=(300, 300), compress_level=6)
        self.image.close()
        return dict(page=self.number, width_pt=PT[0], height_pt=PT[1], lines=self.lines)


def region(page, words):
    return dict(page=page.number, bbox=union([w["bbox"] for w in words]))


def data(day, desc, ref, literal, *tags, note=None, right=False, ambiguous=False):
    return dict(day=day, desc=desc, ref=ref, literal=literal, tags=list(tags),
                note=note, right=right, ambiguous=ambiguous)


class Form:
    def __init__(self, index, fonts):
        self.index = index
        self.doc = f"N{index+1:02d}"
        self.pages = [Page(n, fonts) for n in (1, 2)]
        self.headings = {}
        self.amount_headers = {}
        self.targets = []
        self.month = MONTHS[index]
        self.crew = CREWS[index]
        self.compact = index not in (2, 3)
        self.parent = P_SMALL if self.compact else P_WIDE
        self.child = C_SMALL if self.compact else C_WIDE
        if index in (6, 7):
            self.child = self.parent

    def preamble(self):
        page = self.pages[0]
        values = [("Property:", PROPERTIES[self.index]), ("Unit:", UNITS[self.index])]
        for n, (label, value) in enumerate(values):
            words = page.line(61 + 21*n, page.phrase(label + " " + value, 39))
            setattr(self, ("property_region", "unit_region")[n], region(page, words[1:]))

    def heading(self, page, y, phase, crew=None):
        if crew:
            # Job names are real captions. The schema heading itself stays literal.
            page.line(y-23, page.phrase(crew + " Services", 39, "caption"), "caption")
        text = "Ledger" if phase == "parent" else "Contractor detail"
        self.headings[phase] = region(page, page.line(y, page.phrase(text, 39, "title"), "title"))

    def table(self, page, top, cols, phase, rows, style):
        # An unheaded continuation has a double top rule. The narrow first band holds no text.
        # The headed and visibly damaged variants instead have a conventional header band.
        first = top + (5 if style == "missing" else 26)
        ys = [top, first]
        for row in rows:
            ys.append(ys[-1] + 32 + 16 * (len(row["desc"]) - 1))
        page.grid(cols, ys)
        anchors = [x+4 for x in cols[:4]]
        if style != "missing":
            header = HEADER if style == "header" else ("Dte", "Descript", "Rcf", "Amnt")
            header_tokens = [word_at(word, x) for word, x in zip(header, anchors)]
            if not self.compact:
                header_tokens[-1] = word_at(header[-1], cols[-1]-6, True)
            header_words = page.line(top+18, header_tokens)
            if style == "header":
                self.amount_headers[phase] = region(page, header_words[-1:])
        for j, d in enumerate(rows):
            y0, y1 = ys[j+1:j+3]
            baseline = y0 + 20
            tokens = [word_at(d["day"], anchors[0])]
            tokens.extend(page.phrase(d["desc"][0], anchors[1]))
            if d["ref"]:
                tokens.append(word_at(d["ref"], anchors[2]))
            if d["literal"]:
                tokens.append(word_at(d["literal"], cols[-1]-6 if d["right"] else anchors[3], d["right"]))
            if d["note"]:
                tokens.append(word_at(d["note"], 533))
            page.line(baseline, tokens)
            for k, words in enumerate(d["desc"][1:], 1):
                page.line(baseline + 16*k, page.phrase(words, anchors[1]))
            scope = "parent" if phase == "parent" else "child"
            kind = "ambiguous" if d["ambiguous"] else ("value" if d["literal"] else "blank")
            tags = list(d["tags"])
            if len(d["desc"]) > 1:
                tags.append("wrapped-" + str(len(d["desc"])))
            if d["note"]:
                tags.append("note-opposite-" + kind)
                if d["note"] == d["literal"]:
                    tags.append("equal-note-literal")
            if style == "damaged":
                tags.append("damaged-header")
            if style == "missing":
                tags.append("missing-header")
            if d["right"]:
                tags.append("right-aligned")
            if d["literal"].startswith("-"):
                tags.append("negative-sign")
            if d["literal"].startswith("("):
                tags.append("parentheses")
            target = dict(id=f"{self.doc}-T{len(self.targets)+1:02d}", doc=self.doc,
                          page=page.number, kind=kind, scope=scope, literal=d["literal"],
                          row_box=[cols[0]+1, y0+1, 594, y1-1],
                          amount_box=[cols[-2]+1, y0+1, cols[-1]-1, y1-1],
                          note_boxes=[[516, y0+1, 594, y1-1]] if d["note"] else [],
                          heading=self.headings[phase], amount_header=self.amount_headers[phase],
                          property_region=self.property_region,
                          unit_region=self.unit_region, tags=tags)
            self.targets.append(target)

    def setup(self):
        self.preamble()
        p = self.pages[0]
        self.heading(p, 139, "parent")
        self.table(p, 157, self.parent, "parent", [
            data(self.month, ["Inspection"], "J24", "58.40", "setup", "headed-control", right=not self.compact)
        ], "header")
        self.heading(p, 348, "a", self.crew)
        self.table(p, 367, self.child, "a", [
            data(self.month, ["Restoration"], "G12", "65.20", "setup", "headed-control", right=not self.compact)
        ], "header")

    def continuation(self):
        p = self.pages[1]
        idx = self.index
        if idx < 2:
            # Compact, single-line, left-anchored controls. One true continuation and one true return.
            self.table(p, 89, self.child, "a", [
                data(self.month, ["Rekeying"], "T38", ["43.20", "67.10"][idx], "compact-control")
            ], "missing")
            self.table(p, 278, self.parent, "parent", [
                data(self.month, ["Inspection"], "R52", ["71.50", "85.30"][idx], "compact-control", "return")
            ], "missing")
        elif idx < 4:
            # Rotate which scope carries the damaged label and the two- versus three-line work.
            for phase, top, grid in [("a", 87, self.child), ("parent", 373, self.parent)]:
                ret = ("return",) if phase == "parent" else ()
                odd = (phase == "a") == (idx == 2)
                wrap = ["Replace", "valve packing"] if odd else ["Inspect", "upper flue", "and renew seal"]
                long_value, short_value = ("12,450.00", "9.00") if odd else ("(7,814.60)", "-8.75")
                note = short_value if odd else "214.75"
                self.table(p, top, grid, phase, [
                    data(self.month, wrap, "K6", long_value, *ret, "wide-value", right=True),
                    data(self.month, ["Delivery"], "D9", short_value, *ret, "narrow-value", right=True, note=note),
                    data(self.month, ["Allowance"], "M1", "", *ret, note=note)
                ], "damaged" if odd else "missing")
        elif idx < 6:
            self.table(p, 50, self.child, "a", [
                data(self.month, ["Lamps"], "H2", "63.80", "rapid", "child-a")
            ], "missing")
            self.table(p, 201, self.parent, "parent", [
                data(self.month, ["Fees"], "E3", "82.10", "rapid", "return", "single-row-return")
            ], "missing")
            self.heading(p, 365, "b", CLERKS[idx-4])
            self.table(p, 381, self.child, "b", [
                data(self.month, ["Glaze"], "B6", "37.40", "rapid", "child-b")
            ], "header")
            self.table(p, 551, self.parent, "parent", [
                data(self.month, ["Rent"], "R7", "54.30", "rapid", "return", "after-sibling")
            ], "missing")
        else:
            # The complete arm input (all pages, including references) is identical across twins.
            # Only the hidden generating transaction owner changes; no return cue is visible.
            phase = "parent" if idx == 6 else "a"
            self.table(p, 97, self.parent, phase, [
                data(self.month, ["Locks"], "V2", "41.60", "ambiguous-twin",
                     *(["return"] if phase == "parent" else []), ambiguous=True)
            ], "missing")


def generate(out, font_dir):
    if out.exists() and any(out.iterdir()):
        raise ValueError("output directory must be empty")
    for name, digest in FONTS.items():
        if sha(font_dir / name) != digest:
            raise ValueError(f"font digest mismatch: {name}")
    fonts = {role: ImageFont.truetype(str(font_dir / name), px(size), layout_engine=ImageFont.Layout.BASIC)
             for role, name, size in [("text", "arial.ttf", 10.5), ("title", "arialbd.ttf", 14),
                                      ("caption", "arial.ttf", 10)]}
    public = out / "public"
    documents, targets = [], []
    for idx in range(8):
        form = Form(idx, fonts)
        form.setup()
        form.continuation()
        observations, pages = [], []
        for page in form.pages:
            rel = f"rasters/{form.doc}-p{page.number}.png"
            observations.append(page.save(public / rel))
            pages.append(dict(page=page.number, raster=rel, sha256=sha(public / rel)))
        documents.append(dict(id=form.doc, pages=pages))
        dump(public / "rendered" / f"{form.doc}.json", {"pages": observations})
        targets.extend(form.targets)
    dump(public / "manifest.json", {"documents": documents})
    dump(out / "truth.json", {"targets": targets})
    tags = Counter(tag for target in targets for tag in target["tags"])
    def stats(rows):
        return dict(total=len(rows), kind=dict(Counter(t["kind"] for t in rows)),
                    scope=dict(Counter(t["scope"] for t in rows)))
    raster_digests = [page["sha256"] for doc in documents for page in doc["pages"]]
    rendered_digests = {doc["id"]: sha(public / "rendered" / (doc["id"] + ".json")) for doc in documents}
    counts = dict(documents=len(documents), page_appearances=len(raster_digests),
                  distinct_rasters=len(set(raster_digests)), all_rows=stats(targets),
                  setup=stats([t for t in targets if "setup" in t["tags"]]),
                  post_break=stats([t for t in targets if "setup" not in t["tags"]]),
                  tags=dict(sorted(tags.items())), notes="Tag counts overlap. Setup means page-one body row.")
    dump(out / "precounts.json", counts)
    commitments = dict(algorithm="SHA-256", truth_sha256=sha(out / "truth.json"),
                       generator_sha256=sha(Path(__file__)), manifest_sha256=sha(public / "manifest.json"),
                       precounts_sha256=sha(out / "precounts.json"), rendered_sha256=rendered_digests,
                       raster_hashes="public/manifest.json binds each logical page to its PNG file bytes.",
                       projection="2550 by 3300 RGB, 300 DPI. Black-on-white antialiased glyph masks with "
                       "tight nonzero-alpha bounds before compositing. Integer pixel edges (half-open) times "
                       "612/2550 or 792/3300 yield top-left PDF point extents, rounded to five places.",
                       dependencies=dict(python=platform.python_version(), pillow=pillow_version,
                           freetype=features.version("freetype2"), zlib=features.version("zlib"),
                           fonts=FONTS))
    dump(out / "commitments.json", commitments)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--fonts", type=Path, default=Path("C:/Windows/Fonts"))
    args = parser.parse_args()
    generate(args.output, args.fonts)

