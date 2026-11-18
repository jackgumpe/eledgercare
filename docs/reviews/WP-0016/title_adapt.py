"""Isolated title<LEVELn> view of one native-format document folder (own OS process). Stdlib only.

Applies exactly the committed public rule (rescore.py at 0186467; TITLE and its "\\1" template extracted by
AST, never executed) and otherwise the pinned frozen adapter formats.native_page, as rescore.py did:
every raw page must first re-project to the stored page, then the corrected page replaces only text, spans
and tables. Writes a corrected prediction and a receipt; both files must be new.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import TITLE_TEMPLATE, load, load_formats, sha, sha_file, title_rule, write_new  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pins", type=Path, required=True)
    ap.add_argument("--doc", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, required=True)
    a = ap.parse_args()
    fmt, rule = load_formats(a.pins), title_rule(a.pins)
    pred_path = a.doc / "prediction.json"
    pred = load(pred_path)
    pages, receipt = [], []
    for p in pred["pages"]:
        raw = load(a.doc / f"raw-{p['page']:03d}.json")
        if raw["page"] != p["page"] or raw["source_sha256"] != pred["source_sha256"]:
            raise SystemExit(f"raw page {p['page']} is not bound to the prediction")
        if fmt.native_page(raw["raw_output"], raw["points"]) != {k: p[k] for k in ("text", "spans", "tables")}:
            raise SystemExit(f"page {p['page']}: stored page is not the frozen projection of its raw output")
        adapted = rule.sub(TITLE_TEMPLATE, raw["raw_output"])
        fixed = dict(p, **fmt.native_page(adapted, raw["points"]))
        pages.append(fixed)
        receipt.append(dict(page=p["page"], recognized_headers=len(rule.findall(raw["raw_output"])),
                            added_spans=len(fixed["spans"]) - len(p["spans"]),
                            original_raw_sha256=sha(raw["raw_output"].encode("utf-8")),
                            adapted_raw_sha256=sha(adapted.encode("utf-8"))))
    out_sha = write_new(a.out, dict(pred, pages=pages))
    write_new(a.receipt, dict(view="title_level", rule_pattern=rule.pattern, template=TITLE_TEMPLATE,
                              source_prediction=str(pred_path), source_prediction_sha256=sha_file(pred_path),
                              corrected_prediction_sha256=out_sha, pages=receipt,
                              recognized_headers=sum(r["recognized_headers"] for r in receipt)))


if __name__ == "__main__":
    main()
