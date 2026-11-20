"""WP-0019 reviewer adapter (post-freeze, PREREGISTRATION section 4 / Addendum 1). Rename/restructure only.

Maps the frozen candidate's execute.py/run.py output folders (<family>-<order>/{receipt.json, A/, B/}) to canonical
wp0019-review-run/1 bundles. Arm A = baseline (full only), arm B = treatment (full plus crops); arms are listed in
execution order. Nothing is synthesized: fields the candidate does not record (absolute arm/page clocks, per-arm
PIDs) stay null, and the projected words (page pixels, not points) are carried in author_* fields for the
supplementary pixel-level check instead of the frozen point-based G4.

usage: python -I -B adapt_wp0019.py --root <stage dir> --prefix replay --families H A --out <new dir>
writes <out>/<prefix>-AB.json and <prefix>-BA.json (all families, scoring/identity/geometry views)
"""
import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_common import read_json, sha256_file, write_new

ARM = {"A": "baseline", "B": "treatment"}
KIND = {"cell": "cell", "prose": "line"}


def page_record(ev, arm):
    full = ev["full"]
    rec = dict(page=ev["page"], start_ns=None, durable_ns=None,
               full=dict(width=full["width"], height=full["height"], bgra_sha256=full["bgra_sha256"],
                         pixel_format=full["pixel_format"], text=full["text"], lines=full["lines"], pid=full.get("pid")),
               grids=ev["grids"], crops=[], author_regions=[])
    for r in ev.get("regions") or []:
        rec["author_regions"].append({k: r.get(k) for k in ("id", "kind", "grid_index", "line_index", "bbox_points", "rect_px",
                                                          "full_word_refs", "full_value", "eligible", "selected", "reason",
                                                          "decision", "disagreement", "flagged", "crop_value", "emitted_value",
                                                          "expected_bgra_sha256", "observed_source_sha256")})
        if not r.get("selected"):
            continue
        c = r["crop"]
        rec["crops"].append(dict(
            id=r["id"], rect=r["rect_px"], kind=KIND[r["kind"]],
            region=r.get("grid_index") if r["kind"] == "cell" else r.get("line_index"),
            width=c["width"], height=c["height"], bgra_sha256=c["bgra_sha256"],
            source_rect_sha256=c["source_rectangle_sha256"], full_sha256=c["full_bgra_sha256"],
            pixel_format=c["pixel_format"], text=c["text"], lines=c["lines"], projected_words=None,
            decision=r["decision"], flagged=r["flagged"], pid=c.get("pid"),
            author_projected_px=r["projected_words"], author_crop_value=r["crop_value"],
            author_emitted_value=r["emitted_value"], author_disagreement=r["disagreement"],
            author_expected_bgra_sha256=r.get("expected_bgra_sha256"), author_observed_source_sha256=r.get("observed_source_sha256")))
    if arm == "A" and rec["author_regions"]:
        raise ValueError("baseline arm carries regions")
    return rec


def family_run(folder, family):
    receipt = read_json(folder / "receipt.json")
    if receipt["family"] != family:
        raise ValueError("family mismatch")
    order = receipt["order"]
    arms = []
    for arm in list(receipt["arms"]):  # JSON key order = execution order
        pages = sorted((folder / arm).glob("page-*.json"))
        recs = [page_record(read_json(p), arm) for p in pages]
        arms.append(dict(arm=ARM[arm], pid=None, start_ns=None, end_ns=None, setup_ns=None,
                         family=dict(family=family, prediction=str((folder / arm / "prediction.json").resolve()),
                                     prediction_sha256=sha256_file(folder / arm / "prediction.json"),
                                     start_ns=None, end_ns=None, pages=recs,
                                     author_arm=arm, author_elapsed_ns=receipt["arms"][arm]["elapsed_ns"])))
    return order, receipt, arms


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True)
    p.add_argument("--prefix", required=True)
    p.add_argument("--families", nargs="+", default=["H", "A"])
    p.add_argument("--out", required=True)
    a = p.parse_args()
    root, out = Path(a.root).resolve(), Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    index = {}
    for order in ("AB", "BA"):
        bundle = dict(schema="wp0019-review-run/1", run=f"{a.prefix}-{order}", order=order, clock=None,
                      worker=dict(pid=None, info=None, startup_ns=None), warmup=None, arms=[],
                      author_receipts={}, note="combined family view for scoring/identity/geometry; one worker per family run")
        arm_lists = {}
        for fam in a.families:
            folder = root / f"{fam}-{order}"
            got, receipt, arms = family_run(folder, fam)
            if got != order:
                raise ValueError("order mismatch")
            bundle["author_receipts"][fam] = dict(path=str(folder / "receipt.json"), sha256=sha256_file(folder / "receipt.json"),
                                                  engine_pid=receipt["engine"]["pid"], python_pid=receipt["engine"]["python_pid"])
            if bundle["worker"]["info"] is None:
                bundle["worker"]["info"] = receipt["engine"]
            bundle["worker"].setdefault("per_family_info", {})[fam] = receipt["engine"]
            for arm in arms:
                arm_lists.setdefault(arm["arm"], []).append(arm["family"])
            first = [x["arm"] for x in arms]
            bundle.setdefault("_seq", first)
            if bundle["_seq"] != first:
                raise ValueError("families ran arms in different orders")
        for arm_name in bundle.pop("_seq"):
            bundle["arms"].append(dict(arm=arm_name, pid=None, start_ns=None, end_ns=None, setup_ns=None, families=arm_lists[arm_name]))
        path = out / f"{a.prefix}-{order}.json"
        index[bundle["run"]] = dict(path=str(path), sha256=write_new(path, bundle))
    write_new(out / "index.json", dict(root=str(root), prefix=a.prefix, bundles=index))
    print(json.dumps(index, indent=1))


if __name__ == "__main__":
    main()
