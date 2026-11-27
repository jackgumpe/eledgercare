"""Deterministic, searchable US-letter notes using the PDF standard 14 fonts."""
from io import BytesIO

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


# Adobe standard Times-Roman advance widths for ASCII 32..126, in 1/1000 em.
TIMES = [250,333,408,500,500,833,778,180,333,333,500,564,250,333,250,278,
         *([500]*10),278,278,564,564,564,444,921,722,667,667,722,611,556,722,
         722,333,389,722,611,889,722,722,556,722,667,556,611,722,722,944,722,
         722,611,333,278,333,469,500,333,444,500,444,500,444,333,500,500,278,
         278,500,278,778,500,500,500,500,333,389,278,500,500,722,500,500,444,
         480,200,480,541]


def wrap(value, limit, unit):
    current = ""
    for word in value.split():
        proposed = (current + " " + word).strip()
        if current and sum(unit(c) for c in proposed) > limit:
            yield current
            current = word
        else:
            current = proposed
    if current:
        yield current


def pdf(roman, title, sections, attachments):
    writer = PdfWriter()
    writer.add_metadata({"/Title": f"Targeted recurrent depth {roman} - {title} (02.1)",
                         "/Author": "eld-depth-author (local operative amendment)",
                         "/Subject": "WP-0045; research edition 02.1"})
    fonts = DictionaryObject()
    for code, name in [("body", "Times-Roman"), ("heading", "Helvetica-Bold"),
                       ("label", "Helvetica"), ("eq", "Courier")]:
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                 NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/" + name)})
        fonts[NameObject("/" + code)] = writer._add_object(font)
    pages = []
    for header, paragraphs in sections:
        page = []
        pages.append(page)
        y = 712
        for ln in wrap(header, 505, lambda c: 13 if c.isupper() else 10.4):
            page.append(("heading", 21, 48, y, ln))
            y -= 26
        y -= 9
        for block in paragraphs:
            formula = block.startswith("> ")
            lines = []
            for part in block.splitlines():
                if formula:
                    lines.extend(wrap(part.removeprefix("> "), 500, lambda c: 5.64))
                else:
                    lines.extend(wrap(part, 508, lambda c: TIMES[ord(c)-32]*0.011))
            for ln in lines:
                if y < 64:
                    page = [("heading", 16, 48, 712, header + " (continued)")]
                    pages.append(page)
                    y = 683
                page.append(("eq" if formula else "body", 9.4 if formula else 11,
                             54 if formula else 48, y, ln))
                y -= 13.4 if formula else 14.15
            y -= 6.5
    for index, content in enumerate(pages):
        page = writer.add_blank_page(612, 792)
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): fonts})
        operators = ["0.07 0.36 0.37 RG 1 w 48 739 m 564 739 l S"]
        labels = [("label", 9, 48, 751, f"TARGETED RECURRENT DEPTH    /    PAPER {roman}"),
                  ("label", 9, 481, 751, "EDITION  02.1"),
                  ("label", 8.5, 48, 36, "eLedgerCare    /    Research amendment    /    27 November 2026"),
                  ("label", 8.5, 520, 36, f"{index+1} of {len(pages)}")]
        for font, size, x, y, label in labels + content:
            color = "0.07 0.36 0.37" if font in {"heading", "label"} else "0.09 0.12 0.16"
            escaped = label.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            operators.append(f"BT {color} rg /{font} {size} Tf 1 0 0 1 {x} {y:.2f} Tm ({escaped}) Tj ET")
        stream = DecodedStreamObject()
        stream.set_data("\n".join(operators).encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    for name, data in sorted(attachments.items()):
        writer.add_attachment(name, data)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def sections(text):
    grouped = []
    for block in text.strip().split("\n\n"):
        if block.startswith("# "):
            continue
        if block.startswith("## "):
            grouped.append((block[3:], []))
        else:
            grouped[-1][1].append(block)
    return grouped
