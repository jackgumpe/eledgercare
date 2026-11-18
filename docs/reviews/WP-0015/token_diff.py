"""Characterise token differences between two native-format page folders. Stdlib only.

Reports, per page, differing token positions, whether raw text outside box coordinates is identical,
how many box coordinate groups differ, and the largest coordinate change (0..999 model units).
"""
import json
import re
import sys
from pathlib import Path

BOX = re.compile(r"\[\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\]")


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main(a, b):
    a, b = Path(a), Path(b)
    pages, total = [], 0
    for f in sorted(a.glob("raw-*.json")):
        ra, rb = load(f), load(b / f.name)
        ta, tb = ra["token_ids"], rb["token_ids"]
        diff = [k for k, (x, y) in enumerate(zip(ta, tb)) if x != y] + list(range(min(len(ta), len(tb)), max(len(ta), len(tb))))
        total += len(diff)
        ba, bb = BOX.findall(ra["raw_output"]), BOX.findall(rb["raw_output"])
        deltas = [abs(int(p) - int(q)) for x, y in zip(ba, bb) for p, q in zip(x, y)]
        pages.append(dict(page=ra["page"], tokens=[len(ta), len(tb)], differing_positions=len(diff),
                          text_outside_boxes_identical=BOX.sub("[]", ra["raw_output"]) == BOX.sub("[]", rb["raw_output"]),
                          boxes=[len(ba), len(bb)], boxes_differing=sum(x != y for x, y in zip(ba, bb)),
                          coordinates_differing=sum(d > 0 for d in deltas), max_coordinate_delta=max(deltas or [0])))
    print(json.dumps(dict(total_differing_positions=total, pages=pages), indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:3])
