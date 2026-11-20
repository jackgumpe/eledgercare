"""Post-freeze review only. Score three predictions and independently attribute all truth locations."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
ASTRA = ROOT / "docs/research/WP-0015/astra"
SCORER = ROOT / "docs/evaluation/WP-0015/score.py"
assert hashlib.sha256(SCORER.read_bytes()).hexdigest() == "1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7"
assert hashlib.sha256((ASTRA/"formats.py").read_bytes()).hexdigest() == "b832a7ee452f807a01a4acaa4d63fed927241f73b75fc1a47c7ae830ce28c0a6"
assert hashlib.sha256((ASTRA/"sensitivity-title-level/rescore.py").read_bytes()).hexdigest() == "86b9606468d12afff952b0b24dc7fcd1de932aa9c18400c966a3789e1609b700"
sys.path[:0] = [str(SCORER.parent), str(ASTRA), str(ASTRA/"sensitivity-title-level")]
from formats import native_page
from rescore import TITLE
from score import score


def load(path):
    return json.loads(path.read_bytes())


def by_key(scored, field):
    out = {r["at"]: r for page in scored["pages"] for r in page[field]}
    assert len(out) == sum(len(p[field]) for p in scored["pages"])
    return out


def transitions(w, r):
    assert w.keys() == r.keys()
    keys = ("right_right", "wrong_right", "right_wrong", "wrong_wrong")
    result = dict.fromkeys(keys, 0)
    for at in w:
        w_ok, r_ok = w[at]["correct"], r[at]["correct"]
        result[("right" if w_ok else "wrong") + "_" + ("right" if r_ok else "wrong")] += 1
    return result


def link_routes(rows, doc, win_scores):
    # Link against the scorer's actual matched table and observed Windows spans.
    links = {}
    unmatched, partial = [], []
    for row in rows:
        page = doc["pages"][row["page"]-1]
        scored = win_scores["pages"][row["page"]-1]
        if row["kind"] == "cell":
            box = page["tables"][row["table"]-1]["bbox"]
            suffix = f"/row/{row['row']}/col/{row['col']}"
            found = [c["at"] for c in scored["cells"] if c["at"].endswith(suffix) and c["reported_table_bbox"] == box]
        else:
            boxes = {tuple(page["spans"][idx]["bbox"]) for idx in row["spans"]}
            found = []
            for line in scored["lines"]:
                attributed = {tuple(b) for b in line["reported_span_boxes"]}
                common = attributed.intersection(boxes)
                if common:
                    found.append(line["at"])
                    if common != boxes or common != attributed:
                        partial.append([row["page"], row["raw_line"], line["at"], len(common), len(boxes), len(attributed)])
        if not found:
            unmatched.append(row)
        for at in found:
            assert at not in links, ("multiple selected regions at one truth location", at)
            links[at] = row
    return links, unmatched, partial


def evaluate(family, archive, windows, manifest, routed):
    order = {"H":"h-r1-ab", "A":"a-recovery-ab"}[family]
    run = archive/"runs"/order
    wfolder = run/f"04-{family.lower()}-windows"
    nfolder = run/f"03-{family.lower()}-native"
    truth_path = archive/f"scoring-{family}"/"truth.json"
    truth = load(truth_path)
    pred = load(windows/"prediction.json")
    assert (windows/"prediction.json").read_bytes() == (wfolder/"prediction.json").read_bytes()
    records = manifest["candidates"]
    requested = {c["window"] for c in records}
    assert requested == {1+3*(i//3) for i in range(len(pred["pages"]))}, "full replay requires every window to have been selected"
    native = load(nfolder/"prediction.json")
    assert native["source_sha256"] == routed["source_sha256"] == pred["source_sha256"] == truth["source_sha256"]
    title_count = 0
    for p in native["pages"]:
        raw = load(nfolder/f"raw-{p['page']:03d}.json")
        assert p["page"] == raw["page"] and p["source_sha256"] == raw["source_sha256"]
        original = native_page(raw["raw_output"], raw["points"])
        assert all(p[key] == val for key, val in original.items())
        text, count = TITLE.subn(r"\1", raw["raw_output"])
        title_count += count
        p.update(native_page(text, raw["points"]))
    baseline, ordinary, replay = (score(truth, x) for x in (pred, native, routed))
    links, unmatched, partial = link_routes(records, pred, baseline)
    critical = by_key(baseline,"critical")
    joined = []
    for field in ("critical","cells","lines"):
        w, n, r = (by_key(s,field) for s in (baseline,ordinary,replay))
        assert w.keys() == n.keys() == r.keys()
        for at, a in w.items():
            b, c = n[at], r[at]
            assert a["expected"] == b["expected"] == c["expected"]
            joined.append(dict(category=field, at=at, expected=a["expected"], critical=at in critical,
                               win=a["observed"], native=b["observed"], routed=c["observed"],
                               win_ok=a["correct"], native_ok=b["correct"], routed_ok=c["correct"],
                               selected=at in links, win_flag=a.get("flagged"), routed_flag=c.get("flagged")))
    by_category = {k: transitions(by_key(baseline,k), by_key(replay,k)) for k in ("critical","cells","lines")}
    durations = []
    for first in sorted(requested):
        window = load(nfolder/f"window-{first:03d}.json")
        assert window["first_page"] == first and window["source_sha256"] == truth["source_sha256"]
        durations.append(dict(first=first, pages=window["pages"], engine_ns=window["engine_end_ns"]-window["engine_begin_ns"],
                              native_infer_ms=window["native_infer_ms"]))
    timing = load(wfolder/"timing.json")
    assert timing["prediction_sha256"] == hashlib.sha256((windows/"prediction.json").read_bytes()).hexdigest()
    win_ns = timing["document_committed_ns"] - timing["accepted_ns"]
    return dict(family=family, archive_order=order, truth_sha256=hashlib.sha256(truth_path.read_bytes()).hexdigest(),
                corrected_title_headers=title_count, chosen_windows=durations, windows_ns=win_ns,
                serial_seconds_lower=(win_ns+sum(row["engine_ns"] for row in durations))/1e9,
                score_counts=[s["counts"] for s in (baseline,ordinary,replay)], transitions=by_category,
                unlinked_routes=unmatched, partial_line_links=partial, fields=joined)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family", choices=["H","A"])
    for item in ("archive","windows","manifest","routed","out"):
        parser.add_argument(item, type=Path)
    a = parser.parse_args()
    result = evaluate(a.family, a.archive, a.windows, load(a.manifest), load(a.routed))
    a.out.write_text(json.dumps(result, ensure_ascii=True, indent=1)+"\n", encoding="utf-8")
