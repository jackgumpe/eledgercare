"""Map title-projected native block and table rows back to bytes and emitted token positions."""
from bisect import bisect_left, bisect_right
from hashlib import sha256
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[4]
PARSER = ROOT / "docs/research/WP-0015/astra"
sys.path[:0] = [str(PARSER), str(PARSER / "sensitivity-title-level")]
from formats import BLOCK, TABLE, TableReader, native_page
from rescore import TITLE

PARSER_PINS = {PARSER / "formats.py": "b832a7ee452f807a01a4acaa4d63fed927241f73b75fc1a47c7ae830ce28c0a6",
               PARSER / "sensitivity-title-level/rescore.py": "86b9606468d12afff952b0b24dc7fcd1de932aa9c18400c966a3789e1609b700"}
POINTS = (612, 792)


def verify_parsers():
    for path, digest in PARSER_PINS.items():
        if sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Frozen parser changed: {path.name}")


def byte_alphabet():
    byte_values = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    characters = byte_values.copy()
    for b in range(256):
        if b not in byte_values:
            byte_values.append(b)
            characters.append(256 + len(characters) - 188)
    # There are 188 single-byte glyphs in the original ByteLevel alphabet.
    return dict(zip(map(chr, characters), byte_values, strict=True))


BYTE_VALUE = byte_alphabet()


def token_bytes(raw, ids, vocabulary, added):
    tokens = vocabulary(ids)
    out = bytearray()
    ends = [0]
    for idx, token in zip(ids, tokens, strict=True):
        value = added.get(idx)
        if value is None:
            value = bytes(BYTE_VALUE[c] for c in token)
        else:
            value = value.encode("utf8")
        out.extend(value)
        ends.append(len(out))
    if bytes(out) != raw.encode("utf8"):
        raise ValueError("Native decoded bytes cannot be reconciled to token boundaries")
    return ends


def title_projection(raw):
    """Return projected text and map each retained character to its original position."""
    kept = []
    positions = []
    start = 0
    for m in TITLE.finditer(raw):
        end = m.end(1)
        kept.append(raw[start:end])
        positions.extend(range(start, end))
        start = m.end()
    kept.append(raw[start:])
    positions.extend(range(start, len(raw)))
    projected = "".join(kept)
    if TITLE.sub(r"\1", raw) != projected:
        raise ValueError("Title projection differs from its pinned definition")
    return projected, positions


class LocatedRows(TableReader):
    """Use the upstream HTML parser and track the source of each row it actually returns."""

    def __init__(self, html):
        super().__init__()
        self.offsets = [0] + [m.end() for m in re.finditer("\n", html)]
        self.source = html
        self.intervals = []
        self.row_start = None

    def at(self):
        line, col = self.getpos()
        return self.offsets[line-1] + col

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)
        if tag == "tr":
            self.row_start = self.at()

    def handle_endtag(self, tag):
        before = len(self.rows)
        super().handle_endtag(tag)
        if len(self.rows) != before:
            end = self.source.index(">", self.at()) + 1
            self.intervals.append((self.row_start, end))


def map_window(raw, ids, vocabulary, added):
    ends = token_bytes(raw, ids, vocabulary, added)
    char_bytes = [0]
    for c in raw:
        char_bytes.append(char_bytes[-1] + len(c.encode("utf8")))
    pages = list(re.finditer(re.escape("<PAGE>"), raw))
    if len(pages) != 3 or pages[0].start() != 0:
        raise ValueError("Expected three grounded native pages")
    rows, official, diagnostics = [], [], []

    def keep(lo, hi, page, kind, block_kind, bbox, text, cells):
        lo_byte, hi_byte = char_bytes[lo], char_bytes[hi]
        start = bisect_right(ends, lo_byte) - 1
        stop = bisect_left(ends, hi_byte)
        if not (0 <= start < stop <= len(ids) and ends[start] <= lo_byte < hi_byte <= ends[stop]):
            raise ValueError("Invalid emitted-token/source-span overlap")
        rows.append(dict(index=len(rows), page=page, kind=kind, block_kind=block_kind, bbox999=bbox,
                         text=text, cells=cells, char_range=[lo,hi], byte_range=[lo_byte,hi_byte],
                         token_indices=list(range(start, stop))))

    for n, marker in enumerate(pages, 1):
        origin = marker.start()
        page = raw[origin:pages[n].start() if n < len(pages) else len(raw)]
        projected, indices = title_projection(page)
        parsed = native_page(projected, POINTS)
        official.append(parsed)
        heads = list(BLOCK.finditer(projected))
        mapped_tables, mapped_spans = [], []
        for j, head in enumerate(heads):
            stop = heads[j+1].start() if j+1<len(heads) else len(projected)
            isolated = native_page("<PAGE>" + projected[head.start():stop], POINTS)
            mapped_tables.extend(isolated["tables"])
            mapped_spans.extend(isolated["spans"])
            if not isolated["spans"]:
                continue
            visible, = isolated["spans"]
            box = list(map(int,head.groups()[1:]))
            body = projected[head.end():stop]
            left, right = len(body)-len(body.lstrip()), len(body.rstrip())
            if left >= right:
                raise ValueError("Native emitted a visible block with an empty raw body")
            def bounds(start, end):
                return origin+indices[start], origin+indices[end-1]+1
            keep(*bounds(head.end()+left, head.end()+right), n, "block", head[1], box, visible["text"], [])
            extracted = []
            for table in TABLE.finditer(body):
                html = table.group()
                reader = LocatedRows(html)
                reader.feed(html)
                reader.close()
                if not reader.rows:
                    continue
                extracted.append(reader.rows)
                for cells,(lo,hi) in zip(reader.rows,reader.intervals,strict=True):
                    offset = head.end()+table.start()
                    keep(*bounds(offset+lo,offset+hi), n, "row", head[1], box, " ".join(cells), cells)
            if extracted != [t["rows"] for t in isolated["tables"]]:
                raise ValueError("Source rows disagree with frozen table projection")
        if parsed["spans"] != mapped_spans or parsed["tables"] != mapped_tables:
            raise ValueError("Source blocks disagree with frozen native projection")
        diagnostics.append({"page":n, "recognized_blocks":len(heads), "mapped_spans":len(mapped_spans),
                            "unmapped_prefix":projected[len("<PAGE>"):heads[0].start() if heads else len(projected)].strip()})
    return {"spans":rows, "pages":official, "parser_diagnostics":diagnostics, "token_byte_edges":ends}
