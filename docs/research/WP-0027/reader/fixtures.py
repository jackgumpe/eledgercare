"""Independent source fixtures and native-record constructors for bounded CPU controls."""
from contextlib import closing
import json
from io import BytesIO
from pathlib import Path
import re
from zipfile import ZipFile

from PIL import Image, ImageDraw
import pypdfium2 as pdfium

from reader import EOS, MARKER, PAGE, ROOT, check_hash, digest, packed, require

ARCHIVE = ROOT / "docs/reviews/WP-0024/h0-r1.zip"
ARCHIVE_SHA = "37670af4116f543e2d0104b5d3599d88f2e2d06fc092418ee1cf839769430fc6"
PLAN = ROOT / "docs/coordination/WP-0024/h0-r1-plan.json"
PLAN_SHA = "0bf358c54fc97f32ca213d9a1dd10cfb2838f42f7c5dcded1625c0cca1fd2f89"


def bound(call, doc_sha, native_sha, pages):
    return packed(dict(schema="wp0027-reader-binding-v1", call=call, document_sha256=doc_sha,
                       native_sha256=native_sha, pages=pages))


def pdf_lines(page):
    width, height = page.get_size()
    with closing(page.get_textpage()) as layer:
        literal = layer.get_text_range()
        lines = []
        for m in re.finditer(r"[^\r\n]+", literal):
            boxes = [layer.get_charbox(i) for i in range(m.start(), m.end()) if not literal[i].isspace()]
            left, bottom = min(b[0] for b in boxes), min(b[1] for b in boxes)
            right, top = max(b[2] for b in boxes), max(b[3] for b in boxes)
            box = [left*999/width, (height-top)*999/height, right*999/width, (height-bottom)*999/height]
            lines.append(dict(text=m.group(), bbox999=box))
        return lines


def development():
    plan_raw, archive_raw = PLAN.read_bytes(), ARCHIVE.read_bytes()
    check_hash(plan_raw, PLAN_SHA, "development_plan")
    check_hash(archive_raw, ARCHIVE_SHA, "development_archive")
    plan = json.loads(plan_raw)
    request = plan["requests"][0]
    pdf = Path(request["pdf"]).read_bytes()
    check_hash(pdf, request["sha256"], "development_pdf")
    with ZipFile(BytesIO(archive_raw)) as z, pdfium.PdfDocument(pdf) as doc:
        for window, tag in enumerate(("b01w01H", "b01w02H"), 1):
            call, = [c for c in plan["calls"] if c["tag"] == tag]
            prefix = f"run/sensor/{tag}/"
            native = z.read(prefix + "native.json")
            meta = z.read(prefix + "metadata.json")
            positions = z.read(prefix + "observed-positions.json")
            pages, images = [], []
            for slot, record in enumerate(call["pages"], 1):
                number = 3*(window-1)+slot
                png = Path(record["image"]).read_bytes()
                check_hash(png, record["sha256"], "development_png")
                require(request["rgb_sha256"][number-1] == record["rgb_sha256"], "development_order")
                with closing(doc[number-1]) as page:
                    lines = pdf_lines(page)
                pages.append(dict(page=number, png_sha256=record["sha256"], rgb_sha256=record["rgb_sha256"],
                                  size=[2550, 3300], lines=lines))
                images.append(png)
            yield tag, native, bound(tag, request["sha256"], digest(native), pages), images, meta, positions


SYNTHETIC = [["Météo sheet", "Room 16"], ["Service copy", "Room 17"], ["Filing note", "Room 18"]]


def printed_fixture(contents):
    pages, images = [], []
    for n, texts in enumerate(contents, 1):
        img = Image.new("RGB", (360, 200), "white")
        draw = ImageDraw.Draw(img)
        lines = []
        for i, text in enumerate(texts):
            point = (20, 18 + i*40)
            draw.text(point, text, fill="black")
            box = draw.textbbox(point, text)
            lines.append(dict(text=text, bbox999=[v*999/(360 if j%2 == 0 else 200) for j, v in enumerate(box)]))
        out = BytesIO()
        img.save(out, format="PNG")
        encoded = out.getvalue()
        pages.append(dict(page=n, png_sha256=digest(encoded), rgb_sha256=digest(img.tobytes()),
                          size=[360, 200], lines=lines))
        images.append(encoded)
    return pages, images


def synthetic_sections(contents):
    return [MARKER + "".join(f"<BLOCK>text[20, {50+200*i}, 700, {190+200*i}]<FORK>{line}\n"
                            for i, line in enumerate(lines)) for lines in contents]


def synthetic_native(reader, sections, prompt):
    text = "".join(sections)
    ids = reader.tokenizer.encode(text, add_special_tokens=False).ids
    starts = [i for i, k in enumerate(ids) if k == PAGE]
    return dict(text=text, token_ids=ids, prompt_token_ids=prompt, expected_pages=3, num_pages_out=len(starts),
                finish_reason="stop", eos_observed=True, stop_cause="eos", eos_id=EOS,
                terminal_observation=dict(nxt=EOS, step=len(ids), prompt_length=len(prompt),
                                          guard=dict(marker_cum=len(starts), scanned=len(ids),
                                                     page_len=len(ids)-starts[-1]-1)))
