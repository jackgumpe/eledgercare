"""Independent reconstruction using only the admitted Windows projection and public schedule."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import sys


# Literal token set/rule verified against the public d62a96f WP-0019 policy.
LABELS = set("id identifier code docket serial tag ref reference asset batch lot inspection".split())


def matches(text):
    return bool(LABELS.intersection(re.findall(r"[a-z]+", text.lower())))


def read(path):
    return json.loads(path.read_bytes())


def union(boxes):
    return [fn(b[i] for b in boxes) for i, fn in enumerate((min, min, max, max))]


def derive(page, grids, counts):
    number = page["page"]
    spans = page["spans"]
    assert sum(counts) == len(spans)
    candidates = []
    table_regions = []
    assert len(grids) == len(page["tables"])
    for ti, (grid, table) in enumerate(zip(grids, page["tables"]), 1):
        xs, ys = grid["xs"], grid["ys"]
        assert xs == sorted(set(xs)) and ys == sorted(set(ys))
        assert table["bbox"] == [xs[0], ys[0], xs[-1], ys[-1]]
        table_regions.append(table["bbox"])
        rows = table["rows"]
        assert len(rows) + 1 == len(ys) and all(len(r) + 1 == len(xs) for r in rows)
        for ci, header in enumerate(rows[0]):
            if matches(header):
                for ri in range(1, len(rows)):
                    candidates.append(dict(page=number, kind="cell", table=ti, row=ri+1, col=ci+1,
                                           bbox=[xs[ci], ys[ri], xs[ci+1], ys[ri+1]], label=header,
                                           value=rows[ri][ci]))
    offset = 0
    for line, n in enumerate(counts, 1):
        members = []
        for i in range(offset, offset+n):
            left, top, right, bottom = spans[i]["bbox"]
            x, y = (left+right)/2, (top+bottom)/2
            if not any(x0 <= x < x1 and y0 <= y < y1 for x0, y0, x1, y1 in table_regions):
                members.append(i)
        offset += n
        words = " ".join(spans[i]["text"] for i in members)
        if matches(words):
            candidates.append(dict(page=number, kind="line", raw_line=line, spans=members,
                                   bbox=union([spans[i]["bbox"] for i in members]), value=words))
    return candidates

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    folder = parser.parse_args().input.resolve()
    names = ("prediction.json", "layout.json", "windows.json")
    allowed = {(folder / name).resolve() for name in names}
    reads = []

    def audit(event, args):
        if event == "open":
            if Path(args[0]).absolute() not in allowed or args[1] != "r":
                raise PermissionError(f"Input outside Windows allowlist: {args[0]}")
            reads.append(Path(args[0]).name)
        if event in {"os.listdir","os.scandir","subprocess.Popen","socket.connect"}:
            raise PermissionError(event)
    sys.addaudithook(audit)
    data = {name: (folder/name).read_bytes() for name in names}
    assert sorted(reads) == sorted(names)
    pred, layout, schedule = (json.loads(data[n]) for n in names)
    assert set(pred) == {"pages","source_sha256"} and set(layout) == {"pages"} and set(schedule) == {"windows"}
    pages = list(range(1, len(pred["pages"])+1))
    assert schedule["windows"] == [dict(start=p, pages=pages[p-1:p+2]) for p in pages[::3]]
    owners = {p: w["start"] for w in schedule["windows"] for p in w["pages"]}
    rows = []
    for i, (page, geometry) in enumerate(zip(pred["pages"], layout["pages"], strict=True), 1):
        assert set(page) == {"page","source_sha256","text","spans","tables","state"}
        assert set(geometry) == {"page","line_word_counts","rule_tables","span_sha256"}
        assert page["page"] == geometry["page"] == i and page["source_sha256"] == pred["source_sha256"]
        assert all(set(s) == {"text","flagged","bbox"} for s in page["spans"])
        assert all(set(t) == {"rows","bbox"} for t in page["tables"])
        assert all(set(g) == {"xs","ys"} for g in geometry["rule_tables"])
        raw = [[s["text"],s["bbox"]] for s in page["spans"]]
        assert sha256(json.dumps(raw, separators=(",",":"), ensure_ascii=True).encode()).hexdigest() == geometry["span_sha256"]
        for row in derive(page, geometry["rule_tables"], geometry["line_word_counts"]):
            rows.append(dict(row, window=owners[i]))
    result = dict(source_sha256=pred["source_sha256"], inputs={name:sha256(data[name]).hexdigest() for name in names},
                  opened=reads, pages=len(pages), selected_pages=sorted({r["page"] for r in rows}),
                  windows=dict(sorted(Counter(r["window"] for r in rows).items())), candidates=rows)
    print(json.dumps(result, indent=1, ensure_ascii=True))


if __name__ == "__main__":
    main()
