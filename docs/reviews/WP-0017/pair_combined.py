"""Freeze A1 pair artifacts before analysis and adjudicate them using the original decision rules.

Usage: pair_combined.py inventory | decide | verify-initial
The inventory must be pushed on the independent reviewer branch before 'decide' can read any pair observation.
"""
import argparse
import json
import math
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a1_decide as rules_reviewer
import a1_normalize as adapter
import common
import escrow
import pair_command as issuance

HERE = common.HERE
COORD = issuance.COORD
RUNS = issuance.RUNS
PRIOR = COORD / "a1-r1-blind-inventory.json"
INV = HERE / "evidence/A1-combined-blind-inventory.json"
DECISION = HERE / "evidence/A1-combined-decision.json"
COMMAND_COMMIT = "188e6818d72095241b163991d7648925b15a3fd9"
BRANCH = "review/wp-0017-pair-codex"
LEASE = common.WP17 / "coordination/leases/a1-p1"
CARRIER = common.WP17 / "coordination/carrier/a1-p1"
PAIR_RUN = RUNS / "a1-p1-pairs"
MAP = {mode: rules_reviewer.removal_id(mode.split("_")[1:]) for mode in issuance.MODES}
ORIGINAL_REMOVAL = rules_reviewer.removal_of
ORIGINAL_PROBE = adapter.map_probe


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inventory():
    original = common.load(PRIOR)
    require(common.sha_file(PRIOR) == issuance.INVENTORY, "initial inventory digest differs")
    receipt = common.load(CARRIER / "received.json")
    require(receipt["operator_commit"] == COMMAND_COMMIT
            and receipt["operator_command_sha256"] == common.sha_file(HERE / "commands/a1-p1.json"),
            "carrier received another command")
    require(common.load(LEASE / "returned.json")["release_sha256"] == issuance.RELEASE, "lease did not return")
    require((CARRIER / "return.json").is_file(), "carrier has not returned")
    runs = [Path(r["path"]) for r in original["runs"]]
    runs += [p for p in (PAIR_RUN, PAIR_RUN.with_name(PAIR_RUN.name + "-order")) if p.is_dir()]
    records = [Path(k) for k in original["records"]]
    records += [PRIOR, COORD/"a1-r1-machine-decision.json", COORD/"a1-p1-release.json",
                COORD/"a1-plans/a1-p1-pairs.json", HERE/"commands/a1-p1.json"]
    receipts = [Path(k) for k in original["operator_receipts"]]
    receipts += [p for p in sorted(LEASE.iterdir()) if p.is_file()] + [CARRIER/"received.json", CARRIER/"return.json"]
    inv = escrow.build("A1", runs, records, receipts)
    require(inv["runs"][:4] == original["runs"], "an initial run entry differs from the published blind inventory")
    inv.update(reviewer_identity=issuance.IDENTITY, pair_command_commit=COMMAND_COMMIT)
    print(common.write_new(INV, inv))


def removal_for_raw(mode):
    """Decode only the three authorized underscore spellings. The frozen decider accepts plus IDs."""
    return ORIGINAL_REMOVAL(MAP.get(mode, mode))


def checked_winner(top, selected, margin, tied):
    require(len(top) == 5 and len({t[0] for t in top}) == 5, "five distinct guarded token IDs required")
    scores = [v for _, v in top]
    require(all(math.isfinite(v) for v in scores) and sorted(scores, reverse=True) == scores, "invalid guarded logits")
    require(margin == scores[0] - scores[1] and tied is (scores[0] == scores[1]), "guarded margin/tie differs")
    require(type(selected) is int and dict(top).get(selected) == scores[0], "captured argmax is not a recorded maximum")
    require(selected == top[0][0] or tied, "argmax differs from first topk entry without a real tied logit")
    return dict(token_id=selected, topk_first=top[0][0], top_logit=scores[0], tied=tied, margin=margin)


def map_probe(raw, history):
    rec = ORIGINAL_PROBE(raw, history)
    if rec is None:
        return None
    div = raw["divergence_step_summary"]
    winner = checked_winner(rec["top5"], div["guarded_greedy_argmax_token_id"],
                            div["guarded_margin_top1_top2_fp32"], div["guarded_tie_at_top1"])
    rec["winner"] = winner
    early = raw.get("early_pre_id_divergence_telemetry")
    if early is not None:
        idx = early["step_index"]
        require(idx == 7 and early["replayed_token_id"] == history[idx], "037 early replay differs from its own history")
        g = early["guarded"]
        w = checked_winner([[t["token_id"], t["logit_fp32"]] for t in g["top5"]], g["greedy_argmax_token_id"],
                           g["margin_top1_top2_fp32"], g["tie_at_top1"])
        rec["early"] = dict(zero_based_index=idx, replayed=early["replayed_token_id"], guarded_winner=w)
    return rec


def captured_greedy(rec):
    token = rec["winner"]["token_id"]
    idx = rec["first_divergence"]
    for arm, branch in rec["branches"].items():
        if branch["ids"][idx] == token:
            return arm
    return "other"


def normalization(inv, include_pairs):
    runs = dict(endpoints=RUNS / "a1-r1-endpoints", switches=RUNS / "a1-r1-switches")
    if include_pairs:
        runs["pairs"] = PAIR_RUN
    # Keep original child, timing, window and probe field comparisons in each
    # capture's RAW spelling. Switch the decision ID only after binding the bits.
    with patch.object(rules_reviewer, "removal_of", removal_for_raw), patch.object(adapter, "map_probe", map_probe):
        norm = adapter.normalize(inv, runs)
    require(norm["adapter_status"] == "BOUND" and norm["failures"] == [] and norm["infrastructure_errors"] == [],
            f"failed normalization: {norm['failures']}, {norm['infrastructure_errors']}")
    require(norm["run_sources"] == [issuance.CANDIDATE], "combined source differs")
    initial = rules_reviewer.initial_wave()
    expected = {**initial, **(issuance.MODES if include_pairs else {})}
    require(len(norm["configurations"]) == len(expected), "incorrect number of normalized configurations")
    require({r["id"]: r["bits"] for r in norm["configurations"]} == expected, "raw ID to mask mapping differs")
    for row in norm["configurations"]:
        row["raw_mode"] = row["id"]
        row["id"] = MAP.get(row["id"], row["id"])
    return norm


def judge(inv, norm):
    check = common.Check()
    check(common.sha_file(issuance.AUDIT) == issuance.AUDIT_SHA, "audited prefix file")
    files = {f"{r['run']}/{k}": v for r in inv["runs"] for k, v in r["files"].items()}
    for rel, digest in norm["source_files"].items():
        check(files.get(rel) == digest, f"cited source {rel}")
    audit = common.load(issuance.AUDIT)
    manifest = rules_reviewer.load_manifest()
    vocab = common.Vocab(common.disk("tokenizer.json"))
    mine, locs, bbytes = rules_reviewer.bind(norm, audit, manifest, vocab, check)
    design = common.blob_module("design/rules.py", "astra_pair_arithmetic")
    with patch.object(rules_reviewer, "greedy", captured_greedy):
        decision = rules_reviewer.decide(mine, audit, manifest, vocab, locs, bbytes, rules=design,
                                          coordinator_check=norm["coordinator_endpoint_check"])
    check(all(v["agree"] for v in decision["astra_rules_cross_check"].values()), "original design and review rules agree")
    check(decision["coordinator_endpoint_check"]["agrees"] and
          all(v["equal"] for v in decision["endpoint_parity"].values()), "exact endpoint parity")
    require(not check.failures, str(check.failures))
    return decision, mine, design, vocab, check.count


def compact(d, by, vocab):
    rows, ties = {}, []
    totals = dict(passes=0, tied=0, differing=0)
    for cid, row in by.items():
        out = d["configurations"][cid]
        capture = {}
        for key, passes in out["probes"].items():
            w, prefix = key.split(":")
            mapped = row["windows"][w]["probes"][prefix]
            summaries = []
            for idx, (item, pp) in enumerate(zip(passes, mapped, strict=True)):
                if pp is None:
                    summaries.append(None)
                    continue
                winner = pp["winner"]
                require(item["greedy"] == captured_greedy(pp), "incorrect greedy decision label")
                totals["passes"] += 1
                totals["tied"] += int(winner["tied"])
                if winner["tied"]:
                    tied_tokens = [token for token, logit in pp["top5"] if logit == winner["top_logit"]]
                    ties.append(dict(config=cid, view=key, pass_number=idx+1, tied_top5_tokens=tied_tokens, **winner))
                if winner["token_id"] != winner["topk_first"]:
                    totals["differing"] += 1
                summaries.append(dict(D=item["D"], greedy=item["greedy"], **winner,
                                      **({"early_037":pp["early"]} if "early" in pp else {})))
            capture[key] = summaries
        early = row["windows"]["037"]["free"]["token_ids"][7]
        rows[cid] = dict(raw_mode=row["raw_mode"], bits=row["bits"],
                         free_ids=[out["fields"][w]["value"] for w in rules_reviewer.WINDOWS],
                         field_status=[out["fields"][w]["status"] for w in rules_reviewer.WINDOWS],
                         ordinary_seconds=d["ordinary_speed_s"]["per_config"][cid], restores_both=out["restores_both"],
                         free_037_token_7=dict(id=early, piece=vocab.text(early)),
                         native_prefix_D_019=capture["019:native_prefix"][0]["D"],
                         native_prefix_D_037=capture["037:native_prefix"][0]["D"],
                         free_prefix_D_037=capture["037:free_prefix"][0]["D"] if capture["037:free_prefix"][0] else None,
                         history_shift_D_037=d["history_shift_effect_037"][cid])
        if row["raw_mode"] in issuance.MODES:
            rows[cid]["probe_passes"] = capture
    return rows, totals, ties


def pair_execution(inv):
    inv_by = {r["run"]: r for r in inv["runs"]}
    outer = PAIR_RUN.with_name(PAIR_RUN.name+"-order")
    check = common.Check()
    def read(path):
        path = Path(path)
        root = PAIR_RUN if path.is_relative_to(PAIR_RUN) else outer
        rel = path.relative_to(root).as_posix()
        require(common.sha_file(path) == inv_by[root.name]["files"][rel], f"unbound extra receipt {path}")
        return common.load(path)
    launch = read(PAIR_RUN/"launch.json")
    check(launch["lease"] == "a1-p1" and launch["planned_configs"] == list(issuance.MODES) and
          launch["auto_pair_removals"] is False and launch["warmup_count"] == 3 and launch["seconds"] == 1800,
          "actual three ordered configs, warm-up count and clock bound")
    proc = read(PAIR_RUN/"process.json")
    outer_proc = read(outer/"process.json")
    plan = common.load(COORD/"a1-plans/a1-p1-pairs.json")
    check(outer_proc["plan_sha256"] == issuance.PLAN and len(outer_proc["segments"]) == 1
          and outer_proc["segments"][0]["argv"] == plan["commands"][0]["argv"]
          and outer_proc["all_segments_completed"] is True and outer_proc["segments"][0]["returncode"] == 0,
          "outer supervisor completion and exact launch arguments")
    check(proc["all_segments_completed"] and proc["overall_reason"] is None and len(proc["segments"]) == 3,
          "three successful child segments")
    children = []
    for n,(s,(raw,bits)) in enumerate(zip(proc["segments"],issuance.MODES.items(),strict=True),1):
        seg = PAIR_RUN / f"segment-{n:02d}-{raw}"
        child = read(seg/"child.json")
        seg_plan = read(seg/"segment-plan.json")
        check(child == s["child_meta"] and child["switch_bits"] == bits and child["canonical_mode"] == raw and
              s["mode"] == raw and child["mode"] == raw and child["implementation"] == "ablation_engine"
              and s["segment"] == n and s["returncode"] == 0 and s["reason"] is None, f"{raw}: actual child")
        check(read(seg/"segment-process.json") == s, f"{raw}: child receipt agrees with supervisor")
        check(seg_plan == dict(stage="A1", mode=raw, surgical_override=None, a1_manifest=str(common.A1_MANIFEST[0]),
              a1_manifest_sha256=common.A1_MANIFEST[1], forced_native_probe_repeats=1,
              warmups=[dict(label=f"warm-{i}",warmup=True,**plan["requests"][1]) for i in (1,2,3)]),
              f"{raw}: warmup and input manifest")
        warm = read(seg/"warmups/warmups-summary.json")
        check(warm["count"] == 3 and [w["label"] for w in warm["records"]] == ["warm-1","warm-2","warm-3"],
              f"{raw}: three warmups completed")
        for i,warm_record in enumerate(warm["records"],1):
            folder = seg/"warmups"/f"{i:02d}-warm-{i}-{raw}"
            check(read(folder/"raw-001.json")["rgb_sha256"] == plan["requests"][1]["rgb_sha256"][0] and
                  inv_by[PAIR_RUN.name]["files"][(folder/"prediction.json").relative_to(PAIR_RUN).as_posix()]
                  == warm_record["prediction_sha256"], f"{raw}: warm-up {i} RGB and prediction")
        timing = read(seg/"free/ordinary-timing.json")
        check([w["first_page"] for w in timing["windows"]] == [19,37] and
              sum(timing["ordinary_window_seconds"]) == timing["ordinary_two_window_sum_s"], f"{raw}: scored windows")
        children.append(dict(mode=raw,bits=bits,worker_pid=child["pid"],creation_filetime=child["creation_filetime"],
                             excluded_warmups=warm["count"],process_seconds=s["elapsed_s"]))
    check(len({(r["worker_pid"],r["creation_filetime"]) for r in children}) == 3, "three distinct worker processes")
    lease = common.load(LEASE/"a1-p1-pairs-order-returned.json")
    observations = [json.loads(line) for line in (LEASE/"a1-p1-pairs-order-device.jsonl").read_bytes().splitlines()]
    peak = max(r["used_mib"] for r in observations)
    check(lease["exit"] == 0 and lease["guard"] is None and lease["wall_s"] <= 1890 and peak <= 14500,
          "successful actual return within the signed time and memory limits")
    require(not check.failures, str(check.failures))
    return dict(checks=check.count, children=children, order_seconds=lease["wall_s"],
                peak_sampled_board_mib=peak, board_samples=len(observations), guard=lease["guard"])


def decide():
    ref = f"refs/heads/{BRANCH}"
    remote = issuance.command.git(common.REPO,"ls-remote","--heads","origin",ref).decode().split()[0]
    relative = INV.relative_to(common.REPO).as_posix()
    require(issuance.command.git(common.REPO,"cat-file","blob",f"{remote}:{relative}") == INV.read_bytes(),
            "publish exact combined blind inventory on reviewer branch first")
    inv = common.load(INV)
    require(not escrow.verify_unchanged(inv), "raw tree changed after inventory")
    for path,digest in {**inv["records"],**inv["operator_receipts"]}.items():
        require(common.sha_file(path) == digest, f"record changed after inventory: {path}")
    base = dict(reviewer_identity=issuance.IDENTITY, issued_command_commit=COMMAND_COMMIT,
                blind_inventory_sha256=common.sha_file(INV), blind_inventory_published_at=remote,
                run_sources=[issuance.CANDIDATE], selected_removal=None, created_utc=common.utc())
    if (len(inv["runs"]) != 6 or any(r["pending_files"] or r["failure_files"] or not r["all_segments_completed"]
                                    for r in inv["runs"]) or common.load(CARRIER/"return.json")["exit"] != 0
            or common.load(LEASE/"returned.json")["error"] is not None):
        base.update(outcome="INFRASTRUCTURE_ERROR",
                    run_completions={r["run"]:r["all_segments_completed"] for r in inv["runs"]},
                    carrier_return=common.load(CARRIER/"return.json"),lease_return=common.load(LEASE/"returned.json"))
        print(common.write_new(DECISION, base))
        return
    execution = pair_execution(inv)
    norm = normalization(inv, True)
    d,by,design,vocab,n = judge(inv,norm)
    rows,totals,ties = compact(d,by,vocab)
    pairs = [tuple(raw.split("_")[1:]) for raw in issuance.MODES]
    require(d["eligible_pairs"] == [list(p) for p in pairs], "pair eligibility changed")
    ranking_rows = {}
    for p in pairs:
        row = rows[rules_reviewer.removal_id(p)]
        # The validated structural locator can return a missing/malformed field.
        # Preserve that as a non-restoration in the frozen author ranker.
        fields = [value if status == "ok" else None for value, status in zip(row["free_ids"], row["field_status"], strict=True)]
        ranking_rows[p] = dict(free_ids=fields, ordinary_window_seconds=[row["ordinary_seconds"][w]
                               for w in rules_reviewer.WINDOWS], probe_and_bindings_verified=True)
    author = design.rank_restorations(pairs,ranking_rows)
    rank = sorted((p for p in pairs if tuple(ranking_rows[p]["free_ids"]) == tuple(design.IDS)),
                  key=lambda p:(len(p),sum(ranking_rows[p]["ordinary_window_seconds"]),tuple(design.SWITCHES.index(s) for s in p)))
    winner = list(rank[0]) if rank else None
    require(d.get("selected_removal") == winner == (list(author) if author else None), "pair ranking disagreement")
    require(d["outcome"] == ("PAIR_REMOVAL_RESTORES_BOTH" if winner else "UNRESOLVED_NO_RESTORATION"), "wrong terminal gate")
    require(not escrow.verify_unchanged(inv), "tree changed during analysis")
    base.update(outcome=d["outcome"], selected_removal=winner, selected_bits=rows[rules_reviewer.removal_id(winner)]["bits"] if winner else None,
                native_ids=[rules_reviewer.NATIVE_IDS[w] for w in rules_reviewer.WINDOWS], windows=list(rules_reviewer.WINDOWS),
                configurations=rows, eligible_pairs=d["eligible_pairs"], restoring_pairs_in_rank_order=rank,
                frozen_design_rank=list(author) if author else None, frozen_reviewer_rank=d.get("selected_removal"),
                initial_rules_cross_check=d["astra_rules_cross_check"], noise_floor_nats=d["noise_floor_E"],
                endpoint_parity=d["endpoint_parity"], adapter_checks=norm["checks_run"], machine_checks=n,
                execution=execution, probe_counts=totals, tied_identifier_passes=ties,
                D_definition="Sum of conditional guarded FP32 log-probabilities over the complete native ID span minus the corresponding Carbon span, in nats.",
                clock_definition="Ordinary free engine.read seconds for each three-page window. Setup, all three warm-ups and all forced probes are excluded.",
                interpretation=d.get("causal_label","No eligible removal restored both free identifiers on the two windows."))
    print(common.write_new(DECISION, base),d["outcome"],winner)


def verify_initial():
    inv = common.load(PRIOR)
    norm = normalization(inv,False)
    d,by,_,vocab,_ = judge(inv,norm)
    _, totals, ties = compact(d,by,vocab)
    require(totals == dict(passes=73,tied=35,differing=14), "initial captured argmax audit")
    previous = common.load(COORD/"a1-r1-machine-decision.json")["decision"]
    for f in ties:
        if f["token_id"] == f["topk_first"]:
            continue
        probe = previous["configurations"][f["config"]]["probes"][f["view"]][f["pass_number"]-1]
        new = d["configurations"][f["config"]]["probes"][f["view"]][f["pass_number"]-1]
        probe["greedy"] = new["greedy"]
    require(previous == d, "initial decision changed beyond the documented greedy labels")
    print("Original decision reproduced with captured argmax for all 73 probe passes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("inventory","decide","verify-initial"))
    arg = parser.parse_args()
    {"inventory":inventory,"decide":decide,"verify-initial":verify_initial}[arg.action]()
