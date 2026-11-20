"""Independently check sanitized projections against the Windows archive only."""
from hashlib import sha256
import json
from pathlib import Path
import sys

archive, projections = map(Path, sys.argv[1:])
witness = {}
for family, run in (("H","h-r1-ab"),("A","a-recovery-ab")):
    src = archive/"runs"/run/f"04-{family.lower()}-windows"
    folder = projections/family
    def get(base, name):
        return json.loads((base/name).read_bytes())
    assert (src/"prediction.json").read_bytes() == (folder/"prediction.json").read_bytes()
    pred = get(folder, "prediction.json")
    geometry = get(folder, "layout.json")["pages"]
    counts = dict(table_grids=0, lines=0, words=0, pages=len(geometry))
    for p, g in zip(pred["pages"], geometry, strict=True):
        i = p["page"]
        raw = get(src, f"raw-{i:03d}.json")
        win = get(src, f"window-{i:03d}.json")
        assert win["source_sha256"] == raw["source_sha256"] == p["source_sha256"] == pred["source_sha256"]
        assert raw["page"] == g["page"] == i == win["first_page"] and win["pages"] == 1
        assert win["rule_tables"] == g["rule_tables"]
        rd = raw["reader_result"]
        lengths = [len(line["words"]) for line in rd["lines"]]
        assert lengths == g["line_word_counts"]
        words = [word for line in rd["lines"] for word in line["words"]]
        pairs = []
        for word, span in zip(words, p["spans"], strict=True):
            coords = [round(v*raw["points"][j%2] / (rd["width"],rd["height"])[j%2],3) for j,v in enumerate(word["bbox"])]
            assert span["bbox"] == coords and span["text"] == word["text"] and span["flagged"] is False
            pairs.append([word["text"],coords])
        assert sha256(json.dumps(pairs, separators=(",",":"), ensure_ascii=True).encode()).hexdigest() == g["span_sha256"]
        counts["table_grids"] += len(g["rule_tables"])
        counts["lines"] += len(lengths)
        counts["words"] += len(words)
    total = len(pred["pages"])
    # Ordinary native schedule is three successive pages starting at physical page one.
    schedule = [{"start": i, "pages": list(range(i,min(i+3,total+1)))} for i in range(1,total+1,3)]
    assert get(folder, "windows.json") == {"windows":schedule}
    witness[family] = dict(run=run, windows=len(schedule), **counts)
print(json.dumps(witness, indent=2))
