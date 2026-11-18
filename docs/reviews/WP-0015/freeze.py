"""Blind pre-key hash inventory of reviewer run captures. Stdlib only.

Records the SHA-256 of every captured file (runtime cache directories excluded), the plan,
source and lease bindings, process outcome and the stage-1 verifier verdict. It deliberately omits
timings, text, token values and any other H observation, so it can be published as a hash receipt.
"""
import argparse
import hashlib
import json
from pathlib import Path


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=Path, nargs="+", required=True)
    ap.add_argument("--input", type=Path, required=True, help="released input directory")
    ap.add_argument("--analysis", type=Path, required=True, help="private stage-1 analysis.json")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    analysis = json.loads(a.analysis.read_text(encoding="utf-8"))
    runs = []
    for run in a.runs:
        launch = json.loads((run / "launch.json").read_text())
        process = json.loads((run / "process.json").read_text())
        files = {}
        for f in sorted(run.rglob("*")):
            rel = f.relative_to(run).as_posix()
            if f.is_file() and not rel.startswith("cache/"):
                files[rel] = sha(f)  # sizes omitted: they could reveal H content length
        preds = {rel: v for rel, v in files.items() if rel.endswith("/prediction.json")}
        runs.append(dict(run=run.name, source=launch["source"], head=launch["head"], lease=launch["lease"],
                         plan_sha256=launch["plan_sha256"], returncode=process["returncode"],
                         guard_reason=process["reason"], predictions=preds, files=files))
    inv = dict(kind="WP-0015 reviewer blind pre-key inventory", reviewer="eld-rd-reviewer",
               input={f.name: sha(f) for f in sorted(a.input.iterdir()) if f.is_file()},
               stage1_analysis_sha256=sha(a.analysis), stage1_failures=len(analysis["failures"]),
               stage1_failure_messages=[m.split(" {")[0] for m in analysis["failures"]], runs=runs)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("x", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(inv, indent=2) + "\n")
    print(json.dumps(dict(stage1_failures=inv["stage1_failures"],
                          predictions={r["run"]: r["predictions"] for r in runs}), indent=2))


if __name__ == "__main__":
    main()
