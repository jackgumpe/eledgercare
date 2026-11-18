"""WP-0017 Stage A1 decision procedure (eld-rd-reviewer). Stdlib only, CPU only, no truth keys.

Pure functions over a normalized A1 result set, plus a CLI that first proves the actual A1 run tree is
unchanged since its committed blind inventory and then loads it through an adapter. The rules are frozen
in decision_procedure.md before any A1 output exists. They use exact equalities and signs only: no tuned
threshold enters any outcome.

Normalized result (one per configuration; the adapter builds it from the actual artifacts):
  {"id": "native" | "carbon_bf16" | "add:S1a" | "drop:S2" | "drop:S1a+S2",
   "switches": {"S0": bool, "S1a": bool, "S1b": bool, "S1c": bool, "S2": bool, "S3": bool},
   "windows": {"window-019": {"free": FREE, "probes": {"common": PROBE}},
               "window-037": {"free": FREE, "probes": {"forced_native": PROBE, "free": PROBE}}}}
  FREE  = {"token_ids": [int], "time_s": float, "prefill_ms": float|null, "decode_ms_per_token": float|null,
           "instrumented": false}
  PROBE = {"prefix_sha256": str, "prefix_tokens": int, "t_star_top5": [[id, fp32 logit], ...5],
           "margin": fp32 z1 - z2, "logprob": {"native": fp32 sum, "carbon_bf16": fp32 sum},
           "span_ids": {"native": [int], "carbon_bf16": [int]}}
"""
import argparse
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FORK_ID, PAGE_ID, Check, Vocab, disk, ids_sha, load, sha, sha_file, utc, write_new  # noqa: E402

SWITCHES = ("S0", "S1a", "S1b", "S1c", "S2", "S3")
WINDOWS = ("window-019", "window-037")
SITE_PAGE_INDEX = {"window-019": 2, "window-037": 0}  # page 21 is the third page of 019; page 37 the first of 037
STRINGS = {"window-019": {"native": "I08O1-388", "carbon_bf16": "108O1-388"},
           "window-037": {"native": "8OI10-774", "carbon_bf16": "80I10-774"}}
PROBES = {"window-019": ("common",), "window-037": ("forced_native", "free")}


def matrix():
    """The 14 predeclared single-factor configurations, with their switch vectors."""
    cfg = {"native": {s: False for s in SWITCHES}, "carbon_bf16": {s: True for s in SWITCHES}}
    for s in SWITCHES:
        cfg[f"add:{s}"] = {t: t == s for t in SWITCHES}
        cfg[f"drop:{s}"] = {t: t != s for t in SWITCHES}
    return cfg


def pair_id(pair):
    return "drop:" + "+".join(sorted(pair, key=SWITCHES.index))


def pair_vector(pair):
    return {t: t not in pair for t in SWITCHES}


def pages(ids):
    starts = [i for i, t in enumerate(ids) if t == PAGE_ID]
    return [ids[s:e] for s, e in zip(starts, starts[1:] + [len(ids)])], starts


def reading(vocab, ids, window):
    """Which public string the site page emits: 'native', 'carbon_bf16', 'both', or 'neither'."""
    pg, _ = pages(ids)
    k = SITE_PAGE_INDEX[window]
    if len(pg) <= k:
        return "neither"
    text = b"".join(vocab.piece(t) for t in pg[k])
    hit = {who for who, s in STRINGS[window].items() if s.encode() in text}
    return "both" if len(hit) == 2 else (hit.pop() if hit else "neither")


def boundary(vocab, ids, window, audit):
    """Window index right after the audited shared line prefix of the identifier line on the site page
    (the audited divergence boundary); None if the page emits neither public string there."""
    pg, starts = pages(ids)
    k = SITE_PAGE_INDEX[window]
    if len(pg) <= k:
        return None
    page = pg[k]
    common = [t["id"] for t in audit["windows"][window]["divergence"]["common_line_prefix"]]
    pieces = [vocab.piece(t) for t in page]
    offs, pos = [], 0
    for p in pieces:
        offs.append(pos)
        pos += len(p)
    data = b"".join(pieces)
    for s in STRINGS[window].values():
        at = data.find(s.encode())
        if at < 0:
            continue
        i = max(j for j in range(len(page)) if offs[j] <= at)
        forks = [j for j in range(i) if page[j] == FORK_ID]
        if forks and page[forks[-1] + 1:forks[-1] + 1 + len(common)] == common:
            return starts[k] + forks[-1] + 1 + len(common)
    return None


def gap(probe):
    return probe["logprob"]["native"] - probe["logprob"]["carbon_bf16"]


def favors(probe):
    g = gap(probe)
    return "native" if g > 0 else ("carbon_bf16" if g < 0 else "tie")


def argmax_reading(probe):
    top = probe["t_star_top5"][0][0]
    if top == probe["span_ids"]["native"][0]:
        return "native"
    if top == probe["span_ids"]["carbon_bf16"][0]:
        return "carbon_bf16"
    return "other"


def bind(results, audit, vocab, check):
    """Shape, switch-vector, prefix and span bindings of the normalized results against the frozen audit."""
    want = matrix()
    by = {}
    for r in results:
        check(r["id"] not in by, f"duplicate configuration {r['id']}")
        by[r["id"]] = r
    for cid, vec in want.items():
        check(cid in by, f"missing configuration {cid}")
    for cid, r in by.items():
        if cid in want:
            check(r["switches"] == want[cid], f"{cid}: switch vector differs from its id")
        elif cid.startswith("drop:") and "+" in cid:
            pair = tuple(cid[5:].split("+"))
            check(r["switches"] == pair_vector(pair), f"{cid}: switch vector differs from its id")
        else:
            check(False, f"unexpected configuration {cid}")
        for w in WINDOWS:
            aw = audit["windows"][w]
            win = r["windows"][w]
            check(win["free"].get("instrumented") is False, f"{cid}/{w}: free-window timing must be uninstrumented")
            for name in PROBES[w]:
                p = win["probes"][name]
                check(len(p["t_star_top5"]) == 5, f"{cid}/{w}/{name}: top-5 present")
                check(p["span_ids"]["native"] == [t["id"] for t in aw["divergence"]["span_to_identifier_end"]["native"]]
                      and p["span_ids"]["carbon_bf16"] == [t["id"] for t in aw["divergence"]["span_to_identifier_end"]["carbon_bf16"]],
                      f"{cid}/{w}/{name}: teacher-forced spans = audited spans")
                z = [x[1] for x in p["t_star_top5"]]
                check(z == sorted(z, reverse=True), f"{cid}/{w}/{name}: top-5 logits are sorted")
            if w == "window-019":
                p = win["probes"]["common"]
                check(p["prefix_sha256"] == aw["a1_prefixes"]["common_window_prefix"]["sha256"]
                      and p["prefix_tokens"] == aw["a1_prefixes"]["common_window_prefix"]["tokens"],
                      f"{cid}/019: common prefix = audited 417-token prefix")
            else:
                p = win["probes"]["forced_native"]
                check(p["prefix_sha256"] == aw["a1_prefixes"]["native_prefix_to_boundary"]["sha256"]
                      and p["prefix_tokens"] == aw["a1_prefixes"]["native_prefix_to_boundary"]["tokens"],
                      f"{cid}/037: forced prefix = audited native 41-token prefix")
                ids = win["free"]["token_ids"]
                b = boundary(vocab, ids, w, audit)
                p = win["probes"]["free"]
                if b is None:
                    check(p is None, f"{cid}/037: free probe must be absent when no identifier is emitted")
                else:
                    check(p["prefix_tokens"] == b and p["prefix_sha256"] == ids_sha(ids[:b]),
                          f"{cid}/037: free probe prefix = this configuration's own emitted prefix")
    return by


def decide(by, audit, vocab):
    out = {}
    missing = [cid for cid in matrix() if cid not in by]
    if missing:
        return dict(outcome="INCOMPLETE_MATRIX", missing=missing,
                    attribution="withheld: the predeclared 14-configuration matrix is incomplete")
    # Step 1: replay gate.
    replay = {}
    for cid, arm in (("native", "native"), ("carbon_bf16", "carbon_bf16")):
        for w in WINDOWS:
            got = ids_sha(by[cid]["windows"][w]["free"]["token_ids"])
            replay[f"{cid}:{w}"] = dict(got=got, want=audit["windows"][w]["a1_prefixes"]["full_window"][arm]["sha256"])
            replay[f"{cid}:{w}"]["equal"] = replay[f"{cid}:{w}"]["got"] == replay[f"{cid}:{w}"]["want"]
    replay_ok = all(v["equal"] for v in replay.values())
    out["replay"] = dict(ok=replay_ok, detail=replay)
    # Step 2: readings, probe telemetry, local timing (reported whatever the replay outcome).
    table = {}
    for cid, r in by.items():
        row = {}
        for w in WINDOWS:
            win = r["windows"][w]
            row[w] = dict(reading=reading(vocab, win["free"]["token_ids"], w),
                          free_tokens_sha256=ids_sha(win["free"]["token_ids"]),
                          equals_native=ids_sha(win["free"]["token_ids"]) == replay[f"native:{w}"]["want"],
                          equals_carbon=ids_sha(win["free"]["token_ids"]) == replay[f"carbon_bf16:{w}"]["want"],
                          time_s=win["free"]["time_s"], prefill_ms=win["free"].get("prefill_ms"),
                          decode_ms_per_token=win["free"].get("decode_ms_per_token"),
                          probes={n: (None if p is None else dict(
                              gap_native_minus_carbon=gap(p), favors=favors(p), argmax=argmax_reading(p),
                              margin_reported=p.get("margin"),
                              margin_recomputed=p["t_star_top5"][0][1] - p["t_star_top5"][1][1],
                              top5=p["t_star_top5"], logprob=p["logprob"]))
                              for n, p in win["probes"].items()})
        row["restores_both"] = all(row[w]["reading"] == "native" for w in WINDOWS)
        row["flips_any"] = any(row[w]["reading"] == "carbon_bf16" for w in WINDOWS)
        table[cid] = row
    out["configurations"] = table
    # Step 3: attribution (withheld unless replay passes).
    if not replay_ok:
        out["outcome"] = "REPLAY_FAILED"
        out["attribution"] = "withheld: all-off/all-on did not replay the WP-0016 token sequences"
        return out
    base = table["native"]
    restorers = [s for s in SWITCHES if table[f"drop:{s}"]["restores_both"]]
    per_site = {w: [s for s in SWITCHES if table[f"drop:{s}"][w]["reading"] == "native"] for w in WINDOWS}
    sufficient = [s for s in SWITCHES if table[f"add:{s}"]["flips_any"]]

    def shifted(s):
        a = table[f"add:{s}"]
        if any(a[w]["reading"] != base[w]["reading"] for w in WINDOWS):
            return True
        return any(a[w]["probes"][n]["gap_native_minus_carbon"] != base[w]["probes"][n]["gap_native_minus_carbon"]
                   for w in WINDOWS for n in ("common", "forced_native") if n in a[w]["probes"])
    qualifying = [s for s in SWITCHES if shifted(s)]
    pairs = [pair_id(p) for p in itertools.combinations(qualifying, 2)]
    pair_rows = {p: table[p] for p in pairs if p in table}
    pair_restorers = [p for p, row in pair_rows.items() if row["restores_both"]]
    out.update(single_removal_restorers=restorers, single_removal_restorers_per_site=per_site,
               single_addition_sufficient=sufficient, qualifying_shift_switches=qualifying,
               requested_pair_removals=pairs if not restorers else [],
               pair_removals_run=sorted(pair_rows), pair_removal_restorers=pair_restorers)
    if restorers:
        out["outcome"] = "SINGLE_CULPRIT" if len(restorers) == 1 else "MULTIPLE_SINGLE_REMOVALS"
    elif pairs and not all(p in table for p in pairs):
        out["outcome"] = "PAIR_REMOVALS_REQUIRED"
    elif pair_restorers:
        out["outcome"] = "PAIR_CULPRIT" if len(pair_restorers) == 1 else "MULTIPLE_PAIR_REMOVALS"
    elif base["restores_both"]:
        out["outcome"] = "INTERACTION_ONLY"
    else:
        out["outcome"] = "UNRESOLVED"
    # Candidate ranking (advisory; root freezes at most one carbon_surgical before any A2 output).
    def cost(cid):
        return sum(table[cid][w]["time_s"] for w in WINDOWS) - sum(table["carbon_bf16"][w]["time_s"] for w in WINDOWS)
    cands = [f"drop:{s}" for s in restorers] or pair_restorers
    out["candidates_by_local_time_cost"] = sorted(
        [dict(config=c, two_window_cost_s_vs_carbon=cost(c)) for c in cands],
        key=lambda d: (d["two_window_cost_s_vs_carbon"], [SWITCHES.index(x) for x in d["config"][5:].split("+")]))
    # Step 4: window-037 cascade separation for the full-carbon arm and each restorer.
    def cascade(cid):
        pr = table[cid]["window-037"]["probes"]
        f, fr = pr["forced_native"]["favors"], (pr["free"] or {}).get("favors")
        if f == "carbon_bf16":
            return "direct_at_identifier"
        if f == "native" and fr == "carbon_bf16":
            return "upstream_prefix_cascade"
        return "no_flip_under_either_prefix" if fr in ("native", None) and f == "native" else "tie_or_mixed"
    out["window_037_cascade"] = {cid: cascade(cid) for cid in table}
    # Step 5: local speed effects (single observations, two windows only).
    T = {cid: sum(table[cid][w]["time_s"] for w in WINDOWS) for cid in table}
    out["local_speed_s"] = dict(
        native=T["native"], carbon_bf16=T["carbon_bf16"],
        addition_saving={s: T["native"] - T[f"add:{s}"] for s in SWITCHES},
        removal_cost={s: T[f"drop:{s}"] - T["carbon_bf16"] for s in SWITCHES},
        note="free uninstrumented windows only; one observation per configuration; local two-window effects")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--audit", type=Path, required=True, help="frozen A1-prefix-audit.json")
    ap.add_argument("--audit-sha256", required=True)
    ap.add_argument("--inventory", type=Path, required=True, help="committed A1 blind inventory")
    ap.add_argument("--results", type=Path, required=True, help="normalized results built by the bound adapter")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    check = Check()
    check(sha_file(a.audit) == a.audit_sha256, "audit digest")
    audit, inv, norm = load(a.audit), load(a.inventory), load(a.results)
    from escrow import verify_unchanged  # noqa: PLC0415
    check(not verify_unchanged(inv), "A1 run tree changed since the blind inventory")
    files = {f"{r['run']}/{k}": v for r in inv["runs"] for k, v in r["files"].items()}
    for rel, digest in norm["source_files"].items():
        check(files.get(rel) == digest, f"normalized result cites {rel} not matching the inventory")
    vocab = Vocab(disk("tokenizer.json"))
    by = bind(norm["configurations"], audit, vocab, check)
    res = decide(by, audit, vocab)
    rec = dict(kind="WP-0017 A1 reviewer decision", reviewer="eld-rd-reviewer", created_utc=utc(),
               audit_sha256=a.audit_sha256, inventory_sha256=sha_file(a.inventory), results_sha256=sha_file(a.results),
               checks_run=check.count, failures=check.failures,
               outcome=res["outcome"] if not check.failures else "BINDING_FAILED", decision=res)
    digest = write_new(a.out, rec)
    print(json.dumps(dict(out=str(a.out), sha256=digest, outcome=rec["outcome"], failures=check.failures[:20]), indent=1))
    return 0 if not check.failures else 1


if __name__ == "__main__":
    sys.exit(main())
