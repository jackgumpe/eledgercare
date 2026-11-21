"""Recompute the coordinator's gate and performance tables directly from the reviewer's archived bytes."""
import argparse
from itertools import zip_longest
import json
from pathlib import Path
from zipfile import ZipFile


def stop_stream(row):
    return [*row["token_ids"], *([row["eos_id"]] if row["eos_observed"] else [])]


def comparison(control, other):
    left = stop_stream(control)
    right = stop_stream(other)
    difference = next(({"zero_based_step": i, "b1_id": a, "candidate_id": b}
                       for i, (a, b) in enumerate(zip_longest(left, right)) if a != b), None)
    keys = ("expected_pages", "num_pages_out", "eos_id", "eos_observed", "finish_reason", "stop_cause",
            "prompt_token_ids", "text")
    unequal = [key for key in keys if control[key] != other[key]]
    valid = all(r["expected_pages"] == r["num_pages_out"] == 3 and r["eos_observed"] and
                r["stop_cause"] == "eos" and r["finish_reason"] == "stop" and
                r["token_ids"].count(128827) == 3 and r["token_ids"][0] == 128827
                for r in (control, other))
    return {"parity_through_stop": valid and difference is None and not unequal, "first": difference,
            "unequal_fields": unequal, "candidate_emitted_excluding_eos": len(other["token_ids"]),
            "terminal": other["stop_cause"]}


def summarize(path, inventory_path, tokenizer):
    from tokenizers import Tokenizer
    vocab = Tokenizer.from_file(str(tokenizer))
    inv = json.loads(inventory_path.read_bytes())
    with ZipFile(path) as arc:
        import hashlib
        assert not arc.testzip()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == inv["archive_sha256"]
        assert set(arc.namelist()) == set(inv["files"])
        for name, item in inv["files"].items():
            raw = arc.read(name)
            assert len(raw) == item["bytes"] and hashlib.sha256(raw).hexdigest() == item["sha256"]
        def j(key):
            return json.loads(arc.read("run/trial/" + key + ".json"))
        def result(key):
            return j(key)["result"]
        def tok(idx):
            return {"id": idx, "token": vocab.id_to_token(idx), "decoded": vocab.decode([idx], skip_special_tokens=False)}
        keys = ("short", "long")
        stock = {k: result("g1-stock-" + k) for k in keys}
        cold = j("cold")
        gates = j("decision")
        obj = {"packet": "WP-0023", "candidate": inv["candidate"], "run": inv["lease"],
               "gpu": cold["model"]["platform"], "archive_sha256": inv["archive_sha256"], "status": gates["status"],
               "cold": {"model_load_s": cold["model"]["load_ms"] / 1000,
                        "verified_native_initialization_s": (cold["end_utc_ns"] - cold["start_utc_ns"])/1e9,
                        "board_observed": inv["stages"]["run/trial/cold.json"]},
               "whole_lease_board_observed": inv["board"], "control": {}, "G1": {}, "G2": {}, "first_divergences": []}
        for k, row in stock.items():
            assert row["terminal_observation"]["nxt"] == row["eos_id"]
            obj["control"][k] = {"pages": row["num_pages_out"], "emitted_excluding_eos": len(row["token_ids"]),
                                 "eos_id": row["eos_id"], "stock_stop": row["stop_cause"]}
            obj["G1"][k] = comparison(row, result("g1-wrapper-" + k)["lanes"][0])
        pass1 = all(v["parity_through_stop"] for v in obj["G1"].values()) and len(stock["short"]["token_ids"]) < len(stock["long"]["token_ids"])
        assert pass1 == (gates["status"] not in ("g1-failed", "g1-ineligible-window-lengths"))
        for order in (keys, keys[::-1]) if pass1 else ():
            label = "-".join(order)
            rows = result("g2-" + label)["lanes"]
            obj["G2"][label] = {k: comparison(stock[k], rows[slot]) for slot, k in enumerate(order)}
            for slot, k in enumerate(order):
                first = obj["G2"][label][k]["first"]
                if not first or None in first.values():
                    continue
                tag = "diag-" + label + "-" + k
                d = j(tag + "-compare")
                ref = d["source_files"]
                s, b = result(ref["stock"]), result(ref["wrapper_b2"])["probe"]
                candidates = [first["b1_id"], first["candidate_id"]]
                obj["first_divergences"].append({
                    "order": label, "slot_zero_based": slot, "window": k, "step_zero_based": first["zero_based_step"],
                    "stock_winner": tok(candidates[0]), "batch_winner": tok(candidates[1]),
                    "prior_context": vocab.decode(stock[k]["token_ids"][max(0,first["zero_based_step"]-12):first["zero_based_step"]], skip_special_tokens=False),
                    "raw_top2": {"stock": s["raw"]["top2"], "batch": b["raw"]["top2"]},
                    "processed_top2": {"stock": s["processed"]["top2"], "batch": b["processed"]["top2"]},
                    "stock_to_b2": d["stock_to_b2"], "replay": d["replay"],
                    "peer_already_stopped": d["peer_already_stopped"], "guard": d["target_history"]["candidate_restrictions"]})
        pass2 = pass1 and all(row["parity_through_stop"] for rows in obj["G2"].values() for row in rows.values())
        timed = [n for n in arc.namelist() if n.startswith("run/trial/g3-")]
        if not pass2:
            assert not timed
            obj["warm_ab_ba"] = "not released"
            obj["replay_60_pages"] = "held for failed exact parity or ineligible windows"
            if pass1:
                assert gates["status"] == "g2-failed"
                fp = j("diagnostic-fp32")
                obj["fp32_prefix"] = fp
                if fp["status"] == "completed":
                    for mode in ("b1", "b2"):
                        pr = result(fp["representative"] + "-fp32-" + mode)["probe"]
                        obj["fp32_prefix"][mode + "_top2"] = pr["processed"]["top2"]
                        obj["fp32_prefix"][mode + "_scope"] = pr["precision_scope"]
        elif gates["status"] == "timing-completed":
            measured = {label: j("g3-" + label)["metrics"]["wall_ns"]/1e9
                        for label in ("ab-native", "ab-batch", "ba-batch", "ba-native")}
            obj["warm_ab_ba"] = {"seconds": measured, "native_over_batch": gates["native_over_batch_speedup"]}
        else:
            obj["warm_ab_ba"] = {"status": gates["status"], "completed_arms": [a["name"] for a in gates.get("arms", [])]}
        return obj


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("tokenizer", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    decision = summarize(args.archive, args.inventory, args.tokenizer)
    with args.out.open("x", encoding="utf8", newline="\n") as f:
        json.dump(decision, f, indent=2, ensure_ascii=True)
        f.write("\n")
