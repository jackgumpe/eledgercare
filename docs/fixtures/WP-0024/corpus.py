"""Build opaque WP-0024 sensor plans. CLI permits blind generation only with a root release."""
import argparse
import hashlib
import hmac
import io
import json
from pathlib import Path
import secrets

import pypdfium2 as pdfium


def digest(data):
    return hashlib.sha256(data).hexdigest()


def enc(obj):
    return (json.dumps(obj, indent=2, ensure_ascii=True) + "\n").encode("ascii")


def keep(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"immutable file differs: {path}")
    else:
        with path.open("xb") as handle:
            handle.write(data)


def pdf(streams, fonts):
    """Write self-contained US-letter vector pages with PDF core fonts and no metadata."""
    objects = []
    def add(data):
        objects.append(data)
        return len(objects)
    add(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{5+2*i} 0 R" for i in range(len(streams)))
    add(f"<< /Type /Pages /Kids [{kids}] /Count {len(streams)} >>".encode())
    for font in fonts:
        add(f"<< /Type /Font /Subtype /Type1 /BaseFont /{font} >>".encode())
    for stream in streams:
        content = len(objects) + 2
        add(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content} 0 R >>".encode())
        add(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    pos = out.tell()
    out.write(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        out.write(f"{offset:010} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{pos}\n%%EOF\n".encode())
    return out.getvalue()


# Families have separate vocabulary, type, table geometry, directory and body layout.
FAMILIES = {
    "h0": (("Helvetica","Helvetica-Bold"), 43, (0,188,312,463), 0,
           ("Oak","Palm"), ("Unit4","Unit7"), "Maintenance register"),
    "train": (("Times-Roman","Times-Bold"), 62, (0,162,301,471), 1,
              ("Acorn","Birch"), ("Unit2","Unit8"), "Service journal"),
    "cal": (("Courier","Courier-Bold"), 35, (0,202,363,521), 2,
            ("Alder","Cedar"), ("Unit3","Unit9"), "Repair accounts"),
    "blind": (("Helvetica","Times-Bold"), 51, (0,179,299,483), 3,
              ("Elm","Pine"), ("Unit5","Unit6"), "Works ledger"),
}
SCHEMAS = (("Item","Amount","Ref"), ("Item","Ref","Amount"))


class Sheet:
    def __init__(self, family):
        self.ops = []
        self.fonts, self.x, self.cols, self.style, *_ = family

    def text(self, y, literal, x=None, size=15, bold=False):
        x = self.x if x is None else x
        if x < 0 or y > 780:
            raise ValueError("text outside page")
        literal = literal.replace("\\","\\\\").replace("(","\\(").replace(")","\\)")
        self.ops.append(f"BT /F{2 if bold else 1} {size} Tf {x} {792-y} Td ({literal}) Tj ET")

    def line(self, x1, y1, x2, y2, width=.7):
        self.ops.append(f"{width} w {x1} {792-y1} m {x2} {792-y2} l S")

    def table(self, top, rows, *, broken=False):
        xs = [self.x + c for c in self.cols]
        step = (34,36,32,39)[self.style]
        for r, cells in enumerate(rows):
            y = top + r*step
            self.line(xs[0],y,xs[-1],y)
            for i, cell in enumerate(cells):
                self.text(y + step - 10, str(cell), xs[i]+8, size=14)
        bottom = top + len(rows)*step
        self.line(xs[0],bottom,xs[-1],bottom)
        for i, x in enumerate(xs):
            if broken and i == 2:
                self.line(x,top,x,top+step*.6)
            else:
                self.line(x,top,x,bottom)

    def finish(self):
        return ("\n".join(self.ops)+"\n").encode("ascii")


def make_case(family, stratum, variation, side, horizon, balanced):
    fonts, x, cols, style, owners, units, title = family
    reverse_order = variation & 1
    reverse_schema = (variation >> 1) & 1
    schema = SCHEMAS[side ^ reverse_schema]
    active = owners[side]
    unit = units[side]
    total = 420 + 20*variation + 10*style
    second = total if balanced else total + 40
    summary = stratum == "T3"
    ambiguous = stratum == "T4"
    target = ("MAINT-SUMMARY" if summary else "Posting", str(second if summary else 240+variation), str(second if summary else 850+variation))
    sheets = []
    def sheet():
        p = Sheet(family)
        sheets.append(p)
        return p
    def memo(heading, body):
        p = sheet()
        p.text(112 + 9*style, heading, size=21, bold=True)
        p.text(162 + 13*style, body)
        return p

    p = sheet()
    p.text(72, "Portfolio directory", size=23, bold=True)
    directory = [
        "Owners: " + " / ".join(owners[::(-1 if reverse_order else 1)]),
        "Units: " + " / ".join(units[::(-1 if reverse_order ^ reverse_schema else 1)]),
    ]
    schemas = SCHEMAS[::(-1 if reverse_schema ^ reverse_order else 1)]
    schema_lines = ["Schema: " + " / ".join(s) for s in schemas]
    if style == 1:
        fields = [directory[1], *schema_lines, directory[0]]
    elif style == 2:
        fields = [schema_lines[0], directory[0], schema_lines[1], directory[1]]
    elif style == 3:
        fields = [directory[0], schema_lines[0], directory[1], schema_lines[1]]
    else:
        fields = [*directory, *schema_lines]
    for i, label in enumerate(fields):
        p.text(118 + (27+style*2)*i, label, x=x+(style*7 if i%2 else 0))
    top = 282 + 14*style
    p.line(x, top-27, x+cols[-1], top-27)
    p.text(top+6, "Ledger: " + active, size=22, bold=True)
    p.text(top+42, "Unit: " + unit, size=17)
    p.table(top+69, [schema, ("Service", "180", "103")])
    memo(title, "Account activity carried forward.")
    if ambiguous:
        p = sheet()
        p.text(113,"Supporting schedule",size=21,bold=True)
        p.table(168, [schema, ("Service","140","210")])
    else:
        memo("Work record", "Materials checked and recorded.")

    if stratum == "T2":
        memo("Unit amendment: " + units[1-side], "Applies to subsequent entries.")
        p = sheet()
        p.text(118, "Supporting schedule", size=21, bold=True)
        p.table(167,[SCHEMAS[0], ("Service", str(total-100), "231")])
    elif ambiguous:
        memo("Schedule detail", "Work completed on site.")
        memo("Materials record", "Quantities checked on receipt.")
    else:
        p = sheet()
        p.text(118, "Supporting schedule", size=21, bold=True)
        p.table(167, [SCHEMAS[0], ("Service",str(total-100),"231")], broken=summary)
        memo("Materials record", "Quantities checked on receipt.")
    memo("Service note", "Entries continue on the following sheet.")

    # Only the six inserted interruption windows change between matched horizons.
    for index in range((horizon-12)//3):
        a, b, c = (
            ("Labor record","Time sheet","Delivery entry"),
            ("Inspection note","Supply record","Work log"),
            ("Requisition","Receipt record","Materials note"),
            ("Field record","Stock check","Inspection log"),
            ("Time record","Labor note","Service record"),
            ("Progress report","Work receipt","Visit record"),
        )[index]
        memo(a, "Field work on record.")
        memo(b, "Records checked on receipt.")
        memo(c, "Continuation attached.")
    p = sheet()
    p.text(110,"Schedule detail",size=21,bold=True)
    if ambiguous:
        # The child inherited this twin's full schema and x-bounds on page three.
        # Its open frame and parent are both consistent with this unheaded row.
        p.table(165,[("Materials","100","235")])
        memo("Work record","Further entries follow.")
        memo("Delivery record","Materials checked on receipt.")
    else:
        p.table(165,[SCHEMAS[0], ("Materials","100","235")], broken=summary)
        memo(f"Schedule subtotal: {total}", "Supporting figures checked.")
        memo("Schedule closed", "File with maintenance accounts.")
    memo("Continuation","Record carried forward.")
    p = sheet()
    p.table(158 + 7*style, [target])
    memo("Filing copy","End of current record.")
    assert len(sheets) == horizon
    truth = dict(owner=None if ambiguous else active,
                 unit=None if ambiguous else (units[1-side] if stratum == "T2" else unit),
                 column=None if ambiguous else schema[1],
                 subtotal_status=("BALANCED" if balanced else "UNBALANCED") if summary else None,
                 ambiguous=ambiguous, stratum=stratum,
                 window1=dict(owner=active,unit=unit,schema=list(schema)),
                 child_subtotal=total if summary else None, literal=target[1])
    return [s.finish() for s in sheets], truth


def page_receipt(stream, fonts, store, memory):
    data = pdf([stream],fonts)
    key = digest(data)
    if key in memory:
        return memory[key]
    with pdfium.PdfDocument(data) as doc:
        with doc[0] as page:
            if page.get_size() != (612.,792.):
                raise ValueError("unexpected source size")
            bitmap = page.render(scale=300/72)
            try:
                image = bitmap.to_pil().convert("RGB")
                if image.size != (2550,3300):
                    raise ValueError("unexpected raster size")
                raw = digest(image.tobytes())
                out = io.BytesIO()
                image.save(out,format="PNG",dpi=(300,300),compress_level=3)
                image.close()
            finally:
                bitmap.close()
    png = out.getvalue()
    sha = digest(png)
    path = store / f"{sha}.png"
    keep(path,png)
    result = dict(image=str(path.resolve()), sha256=sha, rgb_sha256=raw)
    memory[key] = result
    return result


def handle(key, kind, *parts):
    return hmac.new(key, json.dumps([kind,*parts]).encode(), hashlib.sha256).hexdigest()[:24]


def build(root, split, release=None):
    root = root.resolve()
    if split == "blind":
        if release is None:
            raise ValueError("blind materialization requires explicit release")
        approved = json.loads(Path(release).read_text())
        if approved.get("authority") != "eld-coordinator" or approved.get("action") != "materialize-wp0024-blind" or approved.get("corpus_sha256") != digest(Path(__file__).read_bytes()):
            raise ValueError("unbound blind release")
    public = root / "public" / split
    private = root / "private" / split
    public.mkdir(parents=True,exist_ok=True)
    private.mkdir(parents=True,exist_ok=True)
    if split == "h0":
        key = hashlib.sha256(b"WP-0024 public H0 demonstration seed v1").digest()
    else:
        secret = private/"id-key.bin"
        if not secret.exists():
            keep(secret,secrets.token_bytes(32))
        key = secret.read_bytes()
    family = FAMILIES[split]
    strata = ["T1"] if split == "h0" else ["T1","T2","T3","T4"]
    horizons = [12] if split == "h0" else [12,30]
    memory, binders, pairs, truths, details, signatures = {}, [], [], [], [], {}
    for stratum in strata:
        levels = range(4) if split == "blind" else range(2 if stratum == "T3" else 1)
        for level in levels:
            # A private rotation masks which blinded case receives each combination.
            rotation = 0 if split=="h0" else int(handle(key,"axes",stratum)[:2],16)%4
            variation = (level + rotation) % 4
            balanced = variation in (0,3)
            if split in ("train","cal") and stratum=="T3":
                balanced = level == 0
            for horizon in horizons:
                pair = handle(key,"pair",stratum,level,horizon)
                members = []
                for side in range(2):
                    binder = handle(key,"binder",stratum,level,horizon,side)
                    target = handle(key,"target",binder)
                    streams,truth = make_case(family,stratum,variation,side,horizon,balanced)
                    pages = [page_receipt(stream,family[0],public/"rasters",memory) for stream in streams]
                    windows = []
                    for i in range(0,horizon,3):
                        group = pages[i:i+3]
                        windows.append(dict(window=i//3+1,pages=group))
                        source = digest(enc([p["rgb_sha256"] for p in group]))
                        signatures.setdefault(source,[]).append(dict(pair=pair,binder=binder,window=i//3+1))
                    binders.append(dict(binder=binder,windows=windows))
                    keep(public/"pdf"/(binder+".pdf"),pdf(streams,family[0]))
                    members.append(dict(binder=binder,target=target))
                    truths.append(dict(pair=pair,binder=binder,target=target,**truth))
                members.sort(key=lambda m:m["binder"])
                pairs.append(dict(pair=pair,members=members))
                details.append(dict(pair=pair,match=handle(key,"match",stratum,level),
                                    stratum=stratum,horizon=horizon,variation=variation,balanced=balanced))
    binders.sort(key=lambda b:b["binder"])
    pairs.sort(key=lambda p:p["pair"])
    keys=enc(dict(binders=sorted(truths,key=lambda b:b["binder"]),pairs=sorted(details,key=lambda p:p["pair"])))
    keep(private/"truth.json",keys)
    plan = enc(dict(binders=binders))
    keep(public/"manifest.json",plan)
    keep(public/"pairs.json",enc(dict(pairs=pairs)))
    permitted = {k:sorted(v,key=lambda item:(item["binder"],item["window"])) for k,v in sorted(signatures.items())
                 if len({r["pair"] for r in v})>1}
    cross = enc(dict(method="sha256(pretty JSON plus LF of three ordered RGB SHA-256 strings)",groups=permitted))
    keep(public/"cross-pair.json",cross)
    receipt=dict(manifest_sha256=digest(plan),cross_pair_sha256=digest(cross),
                 pairs_sha256=digest((public/"pairs.json").read_bytes()),truth_sha256=digest(keys),
                 generator_sha256=digest(Path(__file__).read_bytes()), distinct_pngs=len(memory),
                 appearances=sum(len(b["windows"])*3 for b in binders),pairs=len(pairs),binders=len(binders),
                 source_pdfs={b["binder"]:digest((public/"pdf"/(b["binder"]+".pdf")).read_bytes()) for b in binders})
    keep(public/"receipt.json",enc(receipt))
    print(json.dumps(receipt|{"source_pdfs":len(binders)}))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split",choices=FAMILIES)
    parser.add_argument("root",type=Path)
    parser.add_argument("--release",type=Path)
    args=parser.parse_args()
    build(args.root,args.split,args.release)
