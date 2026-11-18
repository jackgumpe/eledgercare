"""Build per-family development comparisons from the two ordered runs and the frozen common scorer."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVAL = ROOT / "docs/evaluation/WP-0015"
sys.path.insert(0, str(EVAL))
import score as evaluator


def load_pass(run):
    out = {}
    session = evaluator.read(run / "session.json")
    for i, receipt in enumerate(session, 1):
        request = receipt["request"]
        if request["warmup"]:
            continue
        family, mode = request["label"], request["mode"]
        pred = run / f"{i:02d}-{family}-{mode}" / "prediction.json"
        truth = evaluator.read(EVAL / "dev" / family / "truth.json")
        sc = evaluator.score(truth, evaluator.read(pred))
        assert sc["source_sha256"] == request["sha256"]
        out.setdefault(family, {})[mode] = (receipt["elapsed_s"], sc)
    return out


def comparisons(runs):
    all_rows = [load_pass(r) for r in runs]
    entries = []
    for family in ("short", "dense", "boundary"):
        pairs = []
        for run, results in zip(runs, all_rows):
            base_s, base = results[family]["native"]
            trial_s, trial = results[family]["windows"]
            comp = evaluator.compare(base, trial)
            eligible = {"native": base_s} if base["packet_complete"] else {}
            complete = dict(eligible)
            if trial["packet_complete"]:
                complete["windows"] = trial_s
                if comp["inside_quality_budget"]:
                    eligible["windows"] = trial_s
            pairs.append({"run": run.name, "source_sha256": base["source_sha256"],
                "pages": base["expected_pages"], "native_s": base_s, "windows_s": trial_s,
                "saving_s": base_s-trial_s, "speedup": base_s/trial_s if comp["complete_matched_pair"] else None,
                "native_counts": base["counts"], "windows_counts": trial["counts"],
                "fastest_complete": min(complete,key=complete.get) if complete else None,
                "fastest_complete_within_quality": min(eligible,key=eligible.get) if eligible else None,
                "new_unflagged_critical_errors": [e for e in comp["new_or_changed_critical_errors"] if not e["flagged"]],
                "comparison": comp})
        noise = abs(pairs[0]["native_s"] - pairs[1]["native_s"])
        entries.append({"family": family, "baseline_repeat_spread_s": noise,
                        "both_savings_exceed_noise": all(p["comparison"]["complete_matched_pair"] and p["saving_s"]>noise for p in pairs),
                        "pairs": pairs})
    return entries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ab",type=Path)
    parser.add_argument("ba",type=Path)
    args = parser.parse_args()
    print(json.dumps(comparisons([args.ab,args.ba]), indent=2, ensure_ascii=True))
