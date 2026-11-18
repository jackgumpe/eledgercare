"""Score the frozen WP-0016 G0 reviewer forecast (f39c8c4) against the committed stage-1 evidence, the
coordinator hardware return and the publication cross-check output. CPU only; reads committed files.

python -I -B docs/reviews/WP-0016/forecast_check.py --out <json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EV = ROOT / "docs/reviews/WP-0016/evidence"


def load(p):
    return json.loads(Path(p).read_bytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    fc_b = subprocess.run(["git", "-C", str(ROOT), "show", "f39c8c4:docs/reviews/WP-0016/forecast-G0.json"],
                          check=True, capture_output=True).stdout
    fc = json.loads(fc_b)
    s1 = load(EV / "G0-stage1.json")
    pc = load(EV / "G0-publication-crosscheck.json")
    hw = json.loads(subprocess.run(["git", "-C", str(ROOT), "show", "07cbb88:docs/coordination/WP-0016/g0-return.json"],
                                   check=True, capture_output=True).stdout)
    T, C, M, ST, TP = pc["timing"], pc["comparisons"], pc["memory"], pc["structure"], s1["token_parity"]
    gates = {k: v for k, v in C.items() if "g0_pass" in v}
    nat_mean = (T["A"]["ab"]["native_s"] + T["A"]["ba"]["native_s"]) / 2

    def rate(fam, view, trial, role="primary"):
        return C[f"{fam}:{view}:windows->{trial}"]["recovery"][role]["net_critical_per_extra_s"]

    hdr = {arm: sum(ST[f"{f}:{arm}:{o}"]["title_level_headers"] for f in ("H", "A")) for arm in ("native", "carbon_bf16")
           for o in ("ab",)}
    observed = {
        "F01": all(o["exit"] == 0 for o in hw["orders"]) and not s1["failures"],
        "F02": [T["H"][o]["native_s"] for o in ("ab", "ba")],
        "F03": [T["H"][o]["carbon_s"] for o in ("ab", "ba")],
        "F04": [T["H"][o]["speedup"] for o in ("ab", "ba")],
        "F05": [T["A"][o]["native_s"] for o in ("ab", "ba")],
        "F06": [T["A"][o]["speedup"] for o in ("ab", "ba")],
        "F07": T["A"]["repeat_spread_s"]["native"] <= 0.03 * nat_mean,
        "F08": all(T["A"][o]["saving_s"] > T["A"]["repeat_spread_s"]["native"] for o in ("ab", "ba")),
        "F09": all(TP[f][f"{o}:carbon_vs_native"]["identical"] for f in ("H", "A") for o in ("ab", "ba")),
        "F10": all(sum(TP[f][f"{o}:carbon_vs_native"]["pages_text_outside_boxes_identical"] for f in ("H", "A"))
                   >= 0.9 * 64 for o in ("ab", "ba")),
        "F11": all(TP[f]["native:ab_vs_ba"]["identical"] for f in ("H", "A")),
        "F12": all(TP[f]["carbon:ab_vs_ba"]["identical"] for f in ("H", "A")),
        "F13": all(abs(v["delta"]["cer"]) <= 0.003 for v in gates.values()),
        "F14": all(-0.01 <= v["delta"]["cell_accuracy"] <= 0.01 for v in gates.values()),
        "F15": all(v["critical"]["new_unflagged"] == 0 for k, v in gates.items() if k.startswith("H")),
        "F16": all(v["critical"]["new_unflagged"] == 0 for k, v in gates.items() if k.startswith("A")),
        "F17": all(v["g0_pass"] for v in gates.values()),
        "F18": M["ab:carbon_bf16"]["device_used_peak_mib"] <= 10000 and M["ba:carbon_bf16"]["device_used_peak_mib"] <= 10000,
        "F19": [M["ab:carbon_bf16"]["allocator_max_reserved_mib"], M["ba:carbon_bf16"]["allocator_max_reserved_mib"]],
        "F20": [sum(ST[f"{f}:{m}:{o}"]["malformed_headers"] for f in ("H", "A")) for m in ("native", "carbon_bf16")
                for o in ("ab", "ba")],
        "F21": hdr["native"] == hdr["carbon_bf16"],
        "F22": [C["A:frozen:windows->native-ab"]["critical"]["net_recovery"], C["A:frozen:windows->native-ba"]["critical"]["net_recovery"]],
        "F23": [rate("A", "frozen", "native-ab"), rate("A", "frozen", "native-ba")],
        "F24": all(rate("A", v, f"carbon-{o}") >= rate("A", v, f"native-{o}") for v in ("frozen", "title") for o in ("ab", "ba")),
        "F25": [C["H:frozen:windows->native-ab"]["critical"]["net_recovery"], C["H:frozen:windows->native-ba"]["critical"]["net_recovery"]],
        "F26": pc["recomputed_verdict"]["g0_pass"],
    }
    items, brier, hits, n_int = [], [], 0, 0
    for it in fc["items"]:
        o = observed[it["id"]]
        e = dict(it, observed=o)
        if "probability" in it:
            e["outcome"] = bool(o)
            e["brier"] = (it["probability"] - float(bool(o))) ** 2
            brier.append(e["brier"])
        if "interval_80" in it:
            lo, hi = it["interval_80"]
            vals = o if isinstance(o, list) else [o]
            e["inside"] = [lo <= v <= hi for v in vals]
            hits += sum(e["inside"])
            n_int += len(vals)
        items.append(e)
    out = dict(tool="forecast_check.py", forecast_commit="f39c8c42303bf655e080491b9e88a05e5fc2f5b0",
               forecast_sha256=hashlib.sha256(fc_b).hexdigest(),
               tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               items=items, probability_items=len(brier), mean_brier=sum(brier) / len(brier),
               interval_values=n_int, interval_values_inside=hits,
               note="A calibration record, not a gate. title headers counted per arm over H+A in order ab (identical in ba).")
    a.out.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(dict(probability_items=len(brier), mean_brier=out["mean_brier"], interval_values=n_int,
                          inside=hits), indent=1))


if __name__ == "__main__":
    main()
