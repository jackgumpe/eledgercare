"""Lossless evidence writes and source-coordinate projections for the common scorer."""
import ctypes
import hashlib
import json
import os
import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def publish(path, data):
    """Close/fsync temporary bytes, then write-through rename to the unique destination."""
    if not isinstance(data, bytes):
        data = (json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode()
    path = Path(path)
    temp = path.with_name(path.name + ".pending")
    with temp.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    move = ctypes.WinDLL("kernel32", use_last_error=True).MoveFileExW
    move.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
    if not move(str(temp), str(path), 8):
        raise ctypes.WinError(ctypes.get_last_error())
    return digest(data)


def bbox_union(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


class TableReader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append("".join(self.cell).strip())
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


BLOCK = re.compile(r"<BLOCK>([\w-]+)\s*\[\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\]<FORK>")
TABLE = re.compile(r"<table\b[^>]*>.*?</table>", re.S | re.I)


def native_page(raw, pts):
    """Only upstream block boxes provide geometry; never synthesize individual cell locations."""
    body = raw.removeprefix("<PAGE>")
    blocks = list(BLOCK.finditer(body))
    parts = [body[:blocks[0].start()] if blocks else body]
    spans, tables = [], []
    for i, block in enumerate(blocks):
        content = body[block.end():blocks[i + 1].start() if i + 1 < len(blocks) else len(body)]
        values = [int(v) for v in block.groups()[1:]]
        box = [round(v * pts[j % 2] / 999, 3) for j, v in enumerate(values)]
        good_box = max(values) <= 999 and values[0] < values[2] and values[1] < values[3]
        def read_table(match):
            reader = TableReader()
            reader.feed(match.group(0))
            reader.close()
            if good_box and reader.rows:
                tables.append({"bbox": box, "rows": reader.rows})
            return " ".join(v for row in reader.rows for v in row)
        content = TABLE.sub(read_table, content)
        visible = unescape(content).strip()
        if good_box and visible:
            spans.append(dict(text=visible, bbox=box, flagged=False))
        parts.append(visible)
    return {"text": " ".join(" ".join(parts).split()), "spans": spans, "tables": tables}


def token_classes(ids, tokenizer):
    """Disjoint token ID accounting. Box metadata includes delimiters and coordinate digits."""
    block, fork = tokenizer.convert_tokens_to_ids(["<BLOCK>", "<FORK>"])
    counts = dict(page=0, block_geometry=0, table_syntax=0, content=0)
    in_box = False
    for tok in ids:
        in_box |= tok == block
        piece = tokenizer.decode([tok], skip_special_tokens=False)
        key = ("page" if piece == "<PAGE>" else "block_geometry" if in_box
               else "table_syntax" if re.fullmatch(r"\s*</?(?:tr|td|th|table)>\s*", piece, re.I) else "content")
        counts[key] += 1
        if tok == fork:
            in_box = False
    return counts
