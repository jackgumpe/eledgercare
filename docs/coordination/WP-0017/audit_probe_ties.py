"""Compare the saved greedy token with the first top-five entry in inventoried A1 probes."""
import argparse
import hashlib
import json
from pathlib import Path


def audit(inventory):
    data = inventory.read_bytes()
    rows = []
    total = 0
    tied = 0
    for run in json.loads(data)["runs"]:
        for name, digest in run["files"].items():
            if not name.endswith("-probe.json"):
                continue
            raw = (Path(run["path"]) / name).read_bytes()
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError("probe digest differs: " + name)
            probe = json.loads(raw)
            passes = list(probe["forced_native_passes"])
            if probe.get("free_running_probe") is not None:
                passes.append(probe["free_running_probe"])
            for item in passes:
                div = item["divergence_step_summary"]
                top = div["guarded_top5"]
                selected = div["guarded_greedy_argmax_token_id"]
                total += 1
                tie = top[0]["logit_fp32"] == top[1]["logit_fp32"]
                tied += int(tie)
                if selected != top[0]["token_id"]:
                    scores = {x["token_id"]: x["logit_fp32"] for x in top}
                    if not tie or scores.get(selected) != top[0]["logit_fp32"]:
                        raise ValueError("non-tie disagreement in " + name)
                    rows.append(dict(run=run["run"], path=name, mode=probe["mode"], first_page=probe["first_page"],
                                     prefix=item["prefix_mode"], top_five_first=top[0]["token_id"],
                                     actual_argmax=selected, tied_logit=top[0]["logit_fp32"]))
    if not total:
        raise ValueError("no probe passes found")
    return dict(inventory_sha256=hashlib.sha256(data).hexdigest(), probe_passes=total,
                tied_passes=tied, differing_passes=len(rows), differences=rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = audit(args.inventory)
    with args.output.open("x", encoding="utf8", newline="\n") as out:
        json.dump(result, out, indent=2)
        out.write("\n")
    print(result["probe_passes"], result["tied_passes"], result["differing_passes"])
