"""Cross-run agreement for the same released input. Stdlib only; prints booleans, counts and hashes.

native: for every page published by BOTH runs, compare token IDs, raw text, RGB pin and source, and
for every window published by both, the stop/page state and window tokens. windows: compare the
complete predictions and per-page raw reader results. The earlier failure record is never altered.
"""
import argparse
import hashlib
import json
from pathlib import Path


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pages(folder):
    return sorted(int(p.stem[-3:]) for p in folder.glob("page-*.json"))


def native(a, b):
    common = sorted(set(pages(a)) & set(pages(b)))
    diff = []
    for i in common:
        ra, rb = load(a / f"raw-{i:03d}.json"), load(b / f"raw-{i:03d}.json")
        for k in ("token_ids", "raw_output", "rgb_sha256", "source_sha256"):
            if ra[k] != rb[k]:
                diff.append(f"p{i}:{k}")
        if load(a / f"page-{i:03d}.json") != load(b / f"page-{i:03d}.json"):
            diff.append(f"p{i}:projected_page")
    wins = sorted({w.name for w in a.glob("window-*.json")} & {w.name for w in b.glob("window-*.json")})
    for w in wins:
        wa, wb = load(a / w), load(b / w)
        for k in ("first_page", "pages", "finish_reason", "num_pages_out", "expected_pages", "window_token_ids", "raw_output"):
            if wa[k] != wb[k]:
                diff.append(f"{w}:{k}")
    return dict(common_pages=len(common), first=common[0] if common else None, last=common[-1] if common else None,
                common_windows=len(wins), differences=diff, identical=not diff)


def windows(a, b):
    diff = [f"p{i}:reader_result" for i in sorted(set(pages(a)) & set(pages(b)))
            if load(a / f"raw-{i:03d}.json")["reader_result"] != load(b / f"raw-{i:03d}.json")["reader_result"]]
    pa, pb = a / "prediction.json", b / "prediction.json"
    same = pa.exists() and pb.exists() and sha(pa) == sha(pb)
    return dict(pages_a=len(pages(a)), pages_b=len(pages(b)), prediction_identical=same,
                prediction_sha256=[sha(pa) if pa.exists() else None, sha(pb) if pb.exists() else None],
                raw_differences=diff)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--native", type=Path, nargs=2, required=True)
    ap.add_argument("--windows", type=Path, nargs=2, required=True)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    out = dict(native=dict(folders=list(map(str, a.native)), **native(*a.native)),
               windows=dict(folders=list(map(str, a.windows)), **windows(*a.windows)))
    text = json.dumps(out, indent=1) + "\n"
    if a.out:
        with a.out.open("x", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    print(text, end="")


if __name__ == "__main__":
    main()
