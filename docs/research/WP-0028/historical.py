"""Historical, confounded twin replay. Only join labels after source-only observations."""
import json

import online
import run
from inputs import TRUTH, check, sha
from measurement import comparable, measure, query_context, zero_control
from score_math import NAMES, TIMES, derived, margin, trajectory


def history(model, cuts, routes, logical, physical, archive_scores, progression):
    observations, no_target, control = [], [], None
    for route in routes:
        twins = route["twins"]
        data = [[online.load_window(path) for path in twin["windows"]] for twin in twins]
        contexts = [query_context(model, ws) for ws in data]
        if all(reason == "target_count_0" for _,reason in contexts):
            no_target.append([twin["binder"] for twin in twins])
            continue
        check(comparable(contexts) is None, "historical target query/bindings differ")
        final = [physical[logical[twin["binder"]][-1]] for twin in twins]
        check(final[0] == final[1], "historical final whole-window identity differs")
        members = []
        for twin in twins:
            rows, parity, snaps = measure(model,twin["windows"],cuts)
            members.append({"binder": twin["binder"], "target": twin["target"],
                            "window_tags": logical[twin["binder"]], "parity": parity,
                            "checkpoints": rows, "_snapshots": snaps})
        observations.append(members)
        if control is None:
            control = zero_control(model, data[0], cuts)
    check(len(observations) == 8 and len(no_target) == 2, "historical denominator changed")

    # The immutable truth sidecar identifies roles after all numerical probe calls.
    truth = run.labels(TRUTH, "cal", routes)
    output = []
    for members in observations:
        pair, = {truth[m["binder"]]["pair"] for m in members}
        template, = {truth[m["binder"]]["stratum"] for m in members}
        for m in members:
            b = m["binder"]
            tr = truth[b]
            m["owner"] = tr["owner"]
            ref = archive_scores["by_binder"][b]
            check((m["owner"], pair, m["target"]) == (ref["expected"]["owner"],ref["pair"],ref["target"])
                  and tr["target"] == m["target"] and not tr["ambiguous"], "historical identity mismatch")
            checkpoints = json.loads(json.dumps(m.pop("_snapshots")))
            check(checkpoints == progression[pair]["by_binder"][b]["checkpoints"],
                  "WP-0027 snapshot mismatch")
            row = m["checkpoints"]["t3"]
            attempt, = ref["attempts_by_ptr"].values()
            check(row["typed"] == attempt["original_selected_typed"] == ref["selected_binder_decision"],
                  "original posting mismatch")
            for field, scores in (("owner", row["scores"]), *row["unit_column_controls"].items()):
                actual = {online.key(k): v for k,v in scores.items()}
                check(actual == attempt["fields"][field]["scores_by_key"], "WP-0027 final field mismatch")
            check(row["typed"] == {"type": "ABSTAIN", "reason": "below_threshold_owner"},
                  "frozen selected decision changed")
        metrics = trajectory(members)
        a,c = (metrics["t3"][key] for key in ("margin_Alder_input","margin_Cedar_input"))
        ref = archive_scores["by_pair"][pair]
        for m in members:
            signed = margin(m["checkpoints"]["t3"]["scores"])
            expected = signed if m["owner"] == "Alder" else -signed
            check(expected == ref["deltas"][m["binder"]], "true-owner vs fixed-axis sign mismatch")
        check(ref["outcome"] == "one_correct" and not metrics["t3"]["correct_paired_win"]
              and metrics["t3"]["delta"] > 0 and a*c > 0, "historical ranking mismatch")
        swapped = derived(c, a, -metrics["t1"]["delta"])
        check(swapped["delta"] == -metrics["t3"]["delta"] and swapped["mu"] == metrics["t3"]["mu"],
              "label exchange on fixed literal axis failed")
        output.append({"template": template, "horizon": 3*len(members[0]["window_tags"]),
                       "pair": pair, "members": members, "metrics": metrics, "label_swap_t3": swapped})
    check(all(truth[b]["ambiguous"] for members in no_target for b in members), "omitted historical target")
    return {"planned_answerable_pairs": 8, "completed_pairs": len(output),
            "t3_positive_response": sum(p["metrics"]["t3"]["positive_response"] for p in output),
            "t3_correct_paired_win": sum(p["metrics"]["t3"]["correct_paired_win"] for p in output),
            "no_target_pairs_excluded": no_target, "zero_state_control": control,
            "pairs": output}


def pdf_example(m3):
    pair, = [p for p in m3["pairs"] if p["pair"] == "03fe821e0efada96bdc61e31"]
    row = pair["metrics"]["t3"]
    expected = {"margin_Alder_input": "0.1030183", "margin_Cedar_input": "0.1028849",
                "mu": "0.1029516", "delta": "0.0001334"}
    for key, value in expected.items():
        check(format(row[key], ".7f") == value, "formula PDF rounding mismatch: " + key)
    return {"pair": pair["pair"], "arm": "M3", "checkpoint": "t3", "expected_decimal": expected,
            "full_precision": row, "winner_each": ["Alder","Alder"], "other_earlier_cues_varied": True}
