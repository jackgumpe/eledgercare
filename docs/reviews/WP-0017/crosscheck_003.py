"""Independent publication cross-check of the terminal WP-0017 A1 result for canonical report 003 (eld-rd-reviewer).

Stdlib only, CPU only, no key, no model, no new inference. Author: eld-rd-reviewer, native Claude Code session
e2d32880-3555-4a4d-b695-b7963a903c2c (claude-opus-5-5, requested effort xhigh). It reads only the six immutable A1
run trees, after proving them unchanged against the combined blind inventory (e6738a7), plus published Git blobs
and the coordinator's guard/carrier receipts.

1. Frozen normalizer (a1_normalize.py, unchanged since 62f4ce4) on the pair tree as published -> its failures are
   recorded (adapter diagnosis). 2. The only correction, applied in-process and reversed afterwards: a1_decide's
   removal_of also accepts the engine's '_' pair naming (remove_S1b_S1c == remove_S1b+S1c). 3. Frozen a1_decide on
   all 19 configurations with Astra's pinned design/rules.py cross-check. 4. Field-by-field comparison with the
   independent pair reviewer's combined decision (e479b8c) and the coordinator's decision.json (b95e329).
5. Raw probe audit: ties at the divergence step, top-five-first versus the engine's guarded argmax, and whether a
   probe's guarded argmax equals the token the free run emitted on the same history. 6. 037 t=7 coordinate step.
7. One-per-mode ordinary engine.read seconds, instrumented probe time kept separate. 8. Board peaks from the
   launcher samples and the executor's device logs. 9. Carrier/lease receipts and command-to-release matching.
"""
import argparse
import json
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a1_decide as A1  # noqa: E402
import a1_normalize as N  # noqa: E402
import escrow  # noqa: E402
from common import REPO, WP17, Check, Vocab, blob_module, disk, load, sha, sha_file, utc, write_new  # noqa: E402

RUNS = WP17 / "review/runs"
GROUPS = dict(endpoints=RUNS / "a1-r1-endpoints", switches=RUNS / "a1-r1-switches", pairs=RUNS / "a1-p1-pairs")
COORD = "origin/coordination/bootstrap"


def gblob(ref, path):
    return subprocess.run(["git", "-C", str(REPO), "cat-file", "blob", f"{ref}:{path}"], check=True,
                          capture_output=True).stdout


def underscore_removal_of(cid):
    return tuple(cid[len("remove_"):].replace("_", "+").split("+")) if cid.startswith("remove_") else None


def normalize_all(inv):
    c0 = Check()
    n0 = N.normalize(inv, {"pairs": GROUPS["pairs"]}, check=c0)
    frozen_pairs = dict(adapter_status=n0["adapter_status"], failures=c0.failures[:12], failure_count=len(c0.failures))
    orig = A1.removal_of
    A1.removal_of = underscore_removal_of
    try:
        c1 = Check()
        norm = N.normalize(inv, GROUPS, check=c1)
    finally:
        A1.removal_of = orig
    for r in norm["configurations"]:
        if r["id"].startswith("remove_") and "_" in r["id"][len("remove_"):]:
            r["raw_mode"] = r["id"]
            r["id"] = A1.removal_id(r["id"][len("remove_"):].split("_"))
    return frozen_pairs, norm, c1


def probe_audit(free_ids):
    """Every forced and free probe pass of all 19 segments, straight from the raw probe records."""
    rows = []
    for group, run in GROUPS.items():
        for mode, seg in N.segments(run):
            cid = A1.removal_id(mode[len("remove_"):].split("_")) if mode.startswith("remove_") else mode
            for w in A1.WINDOWS:
                doc = load(seg / "probe" / f"window-{w}-probe.json")
                passes = [("native_prefix", k, p) for k, p in enumerate(doc["forced_native_passes"], 1)]
                if doc.get("free_running_probe"):
                    passes.append(("free_prefix", 1, doc["free_running_probe"]))
                for view, k, p in passes:
                    ds = p["divergence_step_summary"]
                    t5 = ds["guarded_top5"]
                    tied = bool(ds.get("guarded_tie_at_top1")) or t5[0]["logit_fp32"] == t5[1]["logit_fp32"]
                    step = p["prefix_token_len"] + p["lcp_offset_from_pre_space"]
                    hist = free_ids[cid][w]
                    emitted = hist[step] if step < len(hist) else None
                    P = p["prefix_token_len"]
                    shared = p["branches"][0]["pre_space_token_ids"][:p["lcp_offset_from_pre_space"]]
                    same_history = p["prefix_sha256"] == A1.ids_sha(hist[:P]) and hist[P:step] == shared
                    e = p.get("early_pre_id_divergence_telemetry") or {}
                    g7 = (e.get("guarded") or {})
                    rows.append(dict(config=cid, window=w, view=view, pass_number=k, tied=tied,
                                     margin=ds.get("guarded_margin_top1_top2_fp32"),
                                     topk_first=t5[0]["token_id"], argmax=ds.get("guarded_greedy_argmax_token_id"),
                                     differs=t5[0]["token_id"] != ds.get("guarded_greedy_argmax_token_id"),
                                     free_emitted_at_divergence=emitted if same_history else None,
                                     guard=(ds.get("guard_meta") or {}).get("implementation"),
                                     t7=dict(replayed=e.get("replayed_token_id"), argmax=g7.get("greedy_argmax_token_id"),
                                             margin=g7.get("margin_top1_top2_fp32"),
                                             top2=[(t["token_id"], t["logit_fp32"]) for t in (g7.get("top5") or [])[:2]])
                                     if e else None,
                                     timing=dict(prefill_ms=p["probe_timing"].get("prefill_ms"),
                                                 decode_ms_per_token=p["probe_timing"].get("decode_ms_per_forwarded_token"),
                                                 tokens=p["probe_timing"].get("total_forwarded_decode_tokens"))))
    return rows


def peaks():
    out = {}
    for run in ("a1-r1-endpoints", "a1-r1-switches", "a1-p1-pairs"):
        s = load(RUNS / run / "process.json").get("gpu_samples") or []
        out[f"launcher:{run}"] = dict(samples=len(s), used_mib_max=max((x["used_mib"] for x in s), default=None))
    for lease in ("a1-r1", "a1-p1"):
        for f in sorted((WP17 / "coordination/leases" / lease).glob("*-device.jsonl")):
            v = [json.loads(x)["used_mib"] for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
            out[f"executor:{lease}/{f.name}"] = dict(samples=len(v), used_mib_max=max(v) if v else None)
        r = WP17 / "coordination/leases" / lease / "returned.json"
        out[f"lease:{lease}"] = load(r) if r.is_file() else None
    return out


def receipts():
    out = {}
    for name, ref in (("a1-r1", "62f4ce4407b3ef6093a412d0504408c500a42c92"), ("a1-p1", "188e6818d72095241b163991d7648925b15a3fd9")):
        rel = gblob(COORD, f"docs/coordination/WP-0017/{name}-release.json")
        lease = json.loads(rel)
        cmd = json.loads(gblob(ref, f"docs/reviews/WP-0017/commands/{name}.json"))
        exp = dict(release_name=lease["name"], release_sha256=sha(rel), candidate=lease["review_worktree_head"],
                   operator="eld-rd-reviewer", action="execute once", stage=lease["gate"])
        car = WP17 / "coordination/carrier" / name
        ret = load(car / "return.json") if (car / "return.json").is_file() else None
        rec = load(car / "received.json") if (car / "received.json").is_file() else None
        out[name] = dict(command_commit=ref, release_sha256=sha(rel), candidate=lease["review_worktree_head"],
                         command_matches_release=[k for k, v in exp.items() if cmd.get(k) != v] == [],
                         executor_sha256=cmd.get("executor_sha256"), reviewer_session=cmd.get("reviewer_session"),
                         orders=[o["run"] for o in lease["orders"]], seconds=[o["seconds"] for o in lease["orders"]],
                         carrier_received_operator_commit=(rec or {}).get("operator_commit"),
                         carrier_exit=(ret or {}).get("exit"))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--audit-sha256", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    check = Check()
    inv_bytes = gblob("e6738a7ad3b8cd25c6a903af3239e01e2ea843df", "docs/reviews/WP-0017/evidence/A1-combined-blind-inventory.json")
    inv = json.loads(inv_bytes)
    check(not escrow.verify_unchanged(inv), "six A1 run trees unchanged since the combined blind inventory")
    nfiles = sum(len(r["files"]) + len(r["runtime_cache_files"]) for r in inv["runs"])
    check(sha_file(a.audit) == a.audit_sha256, "frozen 180-check prefix audit digest")
    frozen_pairs, norm, cnorm = normalize_all(inv)
    check(not cnorm.failures and norm["adapter_status"] == "BOUND" and len(norm["configurations"]) == 19,
          f"normalizer (pair naming corrected in-process) binds 19 configurations {cnorm.failures[:3]}")
    audit = load(a.audit)
    vocab = Vocab(disk("tokenizer.json"))
    manifest = A1.load_manifest()
    by, locs, bb = A1.bind(norm, audit, manifest, vocab, check)
    dec = A1.decide(by, audit, manifest, vocab, locs, bb, rules=blob_module("design/rules.py", "astra_rules"),
                    coordinator_check=norm.get("coordinator_endpoint_check"))
    theirs = load(REPO / "docs/reviews/WP-0017/evidence/A1-combined-decision.json")
    coord = json.loads(gblob(COORD, "docs/coordination/WP-0017/decision.json"))
    T = dec["configurations"]
    mism = []
    for cid, row in T.items():
        t = theirs["configurations"].get(cid)
        if t is None:
            mism.append(f"{cid}: absent in e479b8c")
            continue
        mine = dict(free_ids=[row["fields"][w]["value"] for w in A1.WINDOWS],
                    status=[row["fields"][w]["status"] for w in A1.WINDOWS], restores=row["restores_both"],
                    s=[row["free"][w]["seconds"] for w in A1.WINDOWS],
                    D=[row["probes"][f"{w}:native_prefix"][0]["D"] for w in A1.WINDOWS])
        if mine["free_ids"] != t["free_ids"] or mine["status"] != t["field_status"] or mine["restores"] != t["restores_both"]:
            mism.append(f"{cid}: emitted fields differ")
        if any(abs(x - t["ordinary_seconds"][w]) > 1e-6 for x, w in zip(mine["s"], A1.WINDOWS)):
            mism.append(f"{cid}: ordinary seconds differ")
        if any(abs(x - y) > 1e-12 for x, y in zip(mine["D"], (t["native_prefix_D_019"], t["native_prefix_D_037"]))):
            mism.append(f"{cid}: native-prefix D differs")
    check(not mism, f"per-configuration fields, seconds and D equal the independent combined decision {mism[:4]}")
    check(dec["outcome"] == theirs["outcome"] == "UNRESOLVED_NO_RESTORATION", f"outcome {dec['outcome']} = e479b8c")
    check(dec.get("eligible_pairs") == theirs["eligible_pairs"], "eligible pairs equal")
    check(all(v.get("agree") for v in dec.get("astra_rules_cross_check", {}).values()), "reviewer and Astra rules agree")
    free = {cid: {w: by[cid]["windows"][w]["free"]["token_ids"] for w in A1.WINDOWS} for cid in by}
    pa = probe_audit(free)
    agree = [r for r in pa if r["free_emitted_at_divergence"] is not None]
    summary = dict(passes=len(pa), tied=sum(r["tied"] for r in pa), topk_first_differs_from_argmax=sum(r["differs"] for r in pa),
                   argmax_equals_free_emission=sum(r["argmax"] == r["free_emitted_at_divergence"] for r in agree),
                   comparable_with_free_emission=len(agree),
                   s3_on_device_guards=sorted({(r["guard"]) for r in pa if by[r["config"]]["bits"][5] == "1"}),
                   s3_off_guards=sorted({(r["guard"]) for r in pa if by[r["config"]]["bits"][5] == "0"}))
    check(summary["passes"] == theirs["probe_counts"]["passes"] and summary["tied"] == theirs["probe_counts"]["tied"]
          and summary["topk_first_differs_from_argmax"] == theirs["probe_counts"]["differing"],
          f"probe counts {summary['passes']}/{summary['tied']}/{summary['topk_first_differs_from_argmax']} = e479b8c")
    my_greedy_wrong = sum(1 for r in pa if r["differs"])
    table = {}
    for cid, row in T.items():
        p = {w: row["probes"][f"{w}:native_prefix"] for w in A1.WINDOWS}
        fr = row["probes"].get("037:free_prefix") or [None]
        t7 = next((r["t7"] for r in pa if r["config"] == cid and r["window"] == "037" and r["view"] == "native_prefix"), None)
        table[cid] = dict(
            bits=row["bits"], free_ids={w: row["fields"][w]["value"] for w in A1.WINDOWS},
            status={w: row["fields"][w]["status"] for w in A1.WINDOWS},
            D_native_prefix={w: [x["D"] for x in p[w]] for w in A1.WINDOWS},
            D_own_history_037=fr[0]["D"] if fr[0] else None,
            path_effect_vs_all_off=dec["path_effect_at_native_history"][cid],
            margin_divergence={w: [x["margin"] for x in p[w]] for w in A1.WINDOWS},
            free_037_token_7=free[cid]["037"][7], t7_probe=t7,
            seconds={w: row["free"][w]["seconds"] for w in A1.WINDOWS},
            probe_ms=dict(prefill_ms_median=statistics.median([r["timing"]["prefill_ms"] for r in pa if r["config"] == cid]),
                          decode_ms_per_token_median=statistics.median(
                              [r["timing"]["decode_ms_per_token"] for r in pa if r["config"] == cid])))
    rec = dict(kind="WP-0017 A1 canonical-publication cross-check (reviewer 003)", reviewer="eld-rd-reviewer",
               session="e2d32880-3555-4a4d-b695-b7963a903c2c", created_utc=utc(),
               combined_inventory=dict(commit="e6738a7ad3b8cd25c6a903af3239e01e2ea843df", sha256=sha(inv_bytes),
                                       runs=len(inv["runs"]), files=nfiles),
               frozen_normalizer_on_pairs=frozen_pairs, correction="a1_decide.removal_of accepts '_' (in-process, reversed)",
               normalizer=dict(checks=cnorm.count, failures=cnorm.failures, run_sources=norm["run_sources"],
                               coordinator_endpoint_check=norm["coordinator_endpoint_check"]),
               decision=dict(outcome=dec["outcome"], single_removal_restorers=dec.get("single_removal_restorers"),
                             anchored_flip_switches=dec.get("anchored_flip_switches"), noise_floor_E=dec.get("noise_floor_E"),
                             qualifying_switches=dec.get("qualifying_switches"), eligible_pairs=dec.get("eligible_pairs"),
                             sufficiency_add_on_native=dec["sufficiency_add_on_native"],
                             necessity_remove_from_full=dec["necessity_remove_from_full"],
                             noise_floor_sensitivity=dec.get("noise_floor_sensitivity"),
                             astra=dec.get("astra_rules_cross_check"), endpoint_parity_all_equal=all(
                                 v["equal"] for v in dec["endpoint_parity"].values()),
                             harness_vs_genuine_probe_gap_nats=dec["harness_vs_genuine_probe_gap_nats"],
                             ordinary_speed_s=dec["ordinary_speed_s"]),
               comparison=dict(e479b8c_mismatches=mism, coordinator_decision=dict(
                   commit="b95e329f54ecbb389c2db65a7dbe7d825874a234",
                   **{k: coord.get(k) for k in ("outcome", "selected_removal", "selected_bits", "status", "disposition")
                      if k in coord})),
               probe_audit=dict(summary, reviewer_a1_decide_greedy_label_wrong_on=my_greedy_wrong,
                                tied_passes=[{k: r[k] for k in ("config", "window", "view", "pass_number", "topk_first",
                                                                "argmax", "free_emitted_at_divergence")}
                                             for r in pa if r["tied"]]),
               table=table, peaks=peaks(), receipts=receipts(), checks_run=check.count, failures=check.failures)
    digest = write_new(a.out, rec)
    print(json.dumps(dict(out=str(a.out), sha256=digest, checks=check.count, failures=check.failures,
                          outcome=dec["outcome"], mismatches=len(mism), probes=summary,
                          frozen_pairs=frozen_pairs["failure_count"]), indent=1))
    return 0 if not check.failures else 1


if __name__ == "__main__":
    sys.exit(main())
