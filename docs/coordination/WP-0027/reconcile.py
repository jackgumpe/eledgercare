"""Recompute disposition counts from the two authors' archived result files and calibration truth."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

if os.environ.get("CUDA_VISIBLE_DEVICES") != "-1" or not sys.flags.isolated or not sys.dont_write_bytecode:
    raise SystemExit("Run with hidden CUDA and isolated, no-bytecode Python")

TRUTH = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0024/custody/v2/private/cal/truth.json")
GRID = "b0d2dc9efee1ef27cf47e2929c05e8fbfde2fde0"
FIELDS = ("owner", "unit", "column", "subtotal_status")


def blob(ref, path):
    return subprocess.check_output(["git", "show", f"{ref}:{path}"])


def digest(raw):
    return sha256(raw).hexdigest()


def owners(ref):
    result = json.loads(blob(ref, "docs/research/WP-0027/owners/owner-rankings.json"))
    reference = json.loads(blob(GRID, "docs/reviews/WP-0026/calibration-independent.json"))
    truth_raw = TRUTH.read_bytes()
    assert digest(truth_raw) == "a227da1293bcd6f8b0f636ce3349abd12d02a52361a46b47dbf34969cc773ff1"
    truth = {(t["binder"], t["target"]): t for t in json.loads(truth_raw)["binders"]}
    totals = {}
    for arm, data in result["arms"].items():
        assert data["official_grid"] == reference["actual_frozen_calibration"][arm]["full_grid"]
        selected_cell, = [r for r in data["official_grid"] if [r["tau"], r["margin"]] == data["selected"]]
        assert len(data["official_grid"]) == 24 and data["selected"] == [1.0, 0.1]
        by_binder = data["by_binder"]
        open_cell, = [c for c in data["posting_cells"] if (c["tau"], c["margin"]) == (-.25, 0)]
        assert {(b, row["target"]) for b, row in by_binder.items()} == set(truth)
        paired = defaultdict(dict)
        veto, leaders, other_errors, field_outcomes = Counter(), Counter(), Counter(), defaultdict(Counter)
        ambiguous_pairs = set()
        baseline_wrongs = 0
        for b, member in by_binder.items():
            t = truth[b, member["target"]]
            assert t["pair"] == member["pair"] and member["selected_binder_decision"]["type"] == "ABSTAIN"
            veto[member["selected_binder_decision"]["reason"]] += 1
            if t["ambiguous"]:
                assert member["attempt_count"] == 0
                ambiguous_pairs.add(t["pair"])
                continue
            attempt, = member["attempts_by_ptr"].values()
            scores = attempt["fields"]["owner"]["scores_by_key"]
            expected = t["owner"].casefold()
            assert scores.keys() == {"alder", "cedar"} and set(scores) == set(attempt["fields"]["owner"]["eligible_by_key"])
            delta = scores[expected] - max(s for name, s in scores.items() if name != expected)
            assert delta == data["by_pair"][t["pair"]]["deltas"][b] and delta != 0 and not attempt["fields"]["owner"]["zero_read"]
            assert data["by_pair"][t["pair"]]["same_final_input_bytes"] and data["by_pair"][t["pair"]]["same_owner_candidates_at_target"]
            assert expected not in paired[t["pair"]]
            paired[t["pair"]][expected] = delta
            leaders[max(scores, key=scores.get)] += 1
            post = open_cell["by_binder"][b]["decision"]
            assert post["type"] == "Posting"
            wrong = []
            for field in FIELDS:
                pred = post[field].casefold() if post[field] is not None else None
                true = t[field].casefold() if t[field] is not None else None
                if pred != true:
                    wrong.append(field)
                field_outcomes[field]["na" if true is None and pred is None else "correct" if pred == true else "wrong"] += 1
            baseline_wrongs += bool(wrong)
            if delta > 0:
                assert "owner" not in wrong
                for field in wrong:
                    other_errors[field] += 1
        assert all(set(p) == {"alder", "cedar"} for p in paired.values())
        joint = Counter(sum(d > 0 for d in p.values()) for p in paired.values())
        direction = [p["alder"] + p["cedar"] for p in paired.values()]
        totals[arm] = {"binders": len(by_binder), "verified_grid_cells": len(data["official_grid"]),
                       "selected_cell": selected_cell, "selected_abstention_reasons": dict(veto),
                       "ambiguous_pairs": len(ambiguous_pairs), "answerable_pairs": len(paired),
                       "both": joint[2], "one": joint[1], "neither": joint[0], "ties": 0,
                       "unscorable_pairs": 0, "reverse_flips": joint[0], "leader_by_binder": dict(leaders),
                       "positive_within_pair_shifts": sum(s > 0 for s in direction),
                       "min_max_Alder_minus_Cedar_shift": [min(direction), max(direction)],
                       "open_grid_point": [-0.25, 0], "open_wrong_postings": baseline_wrongs,
                       "open_errors_when_owner_right": dict(other_errors),
                       "open_fields": {f: dict(v) for f,v in field_outcomes.items()}}
    return totals


def reader(ref):
    prefix = "docs/research/WP-0027/reader/evidence/"
    def get(name):
        return blob(ref, prefix + name)
    cases = json.loads(get("parser-cases.json"))
    witness = json.loads(get("k0014.json"))
    source = json.loads(get("k0014-source.json"))
    native = json.loads(get("k0014-native.json"))
    assert digest(get("k0014-native.json")) == source["native_sha256"] and witness["original_decision"] == "rejected"
    raw = native["text"].encode("utf-8")
    prediction = witness["candidate"]
    obs = prediction["observation"]
    eos = native["terminal_observation"]["nxt"]
    ids = [*native["token_ids"], eos]
    assert eos == 1 and obs["ids_through_eos"] == ids and len(ids) == 123
    assert struct.pack("<" + "I" * len(ids), *ids) == get("k0014-ids-through-eos.u32le")
    assert digest(raw) == obs["raw_utf8_sha256"] and digest(get("k0014-ids-through-eos.u32le")) == obs["ids_through_eos_u32le_sha256"]
    assert [i for i, n in enumerate(ids) if n == 128827] == [s["marker_token"] for s in obs["sections"]] == [0, 42, 81, 121]
    unassigned = prediction["unused_delimiter"]
    lo, hi = unassigned["byte_range"]
    assert raw[lo:hi] == b"<PAGE>" and hi == len(raw) and unassigned["payload_byte_range"] == [hi, hi]
    assert unassigned["token_range"] == [len(ids)-2, len(ids)-1]
    spans = prediction["projection"]["spans"]
    assert all(max(span["token_indices"]) < unassigned["marker_token"] for span in spans)
    page_nums, literals = [], []
    for m, s in zip(prediction["source_to_section"], source["pages"], strict=True):
        page_nums.append(s["page_number"])
        texts = [g["text"] for g in s["source_lines"]]
        assert texts == [t["text"] for t in m["line_correspondences"]]
        assert m["source"]["png_sha256"] == s["png_sha256"] and m["source"]["rgb_sha256"] == s["rgb_sha256"]
        assert m["source"]["ink_outside_source_lines"] == 0
        literals.extend(texts)
    assert page_nums == [16, 17, 18] and literals == [r["text"] for r in spans]
    assert len({r["case"] for r in cases["cases"]}) == len(cases["cases"])
    assert all(r["expected"] == r["actual"] for r in cases["cases"])
    negative = [r for r in cases["cases"] if r["expected"]["decision"] == "unresolved"]
    controls = []
    for name in ("b01w01H", "b01w02H"):
        record = json.loads(get(name + ".json"))
        assert record["full_projection_exact"]
        positions = record["feature_position_selections"]
        controls.append({"call": name,"grounded_spans": len(positions),
                         "position_selections": sum(len(row["absolute_positions"]) for row in positions)})
    return {"author_cases": len(cases["cases"]), "author_positive": len(cases["cases"]) - len(negative),
            "author_negative": len(negative), "author_false_acceptances": 0, "original_error": witness["original_exception"],
            "physical_pages": page_nums, "lines": len(literals), "grounded_spans": len(spans),
            "marker_indices": [s["marker_token"] for s in obs["sections"]], "unassigned_bytes": [lo,hi],
            "unassigned_tokens": unassigned["token_range"], "eos_token_index": obs["observed_eos"]["token_index"],
            "native_sha256": digest(get("k0014-native.json")), "through_eos_u32le_sha256": digest(get("k0014-ids-through-eos.u32le")),
            "raw_utf8_sha256": digest(raw), "ordinary_saved_controls": controls}


if __name__ == "__main__":
    rank_ref, reader_ref = sys.argv[1:]
    print(json.dumps({"owner_evidence_commit": rank_ref, "reader_evidence_commit": reader_ref,
                      "owners": owners(rank_ref), "reader": reader(reader_ref)}, indent=2))
