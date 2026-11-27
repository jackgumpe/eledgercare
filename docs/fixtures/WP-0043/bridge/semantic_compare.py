#!/usr/bin/env python3
"""WP-0043 semantic comparison v2: frozen oracle expectations vs actual candidate results.

Author: eld-fixture-claude (Claude Code, claude-opus-5-5).  Standard library only.
Run only after the bridge `run` and `fidelity` steps have written candidate outputs.

Supersedes nothing: expected/ (freeze B) and compare.py (v1) stay unchanged.  v2 differs
from v1 by (a) mapping phases/keys through crosswalk-v1.json, (b) matching individual
conflicts and missing atoms rather than coarse (step, phase) sets, (c) checking word
pairs, lanes and dense/compact offsets per matched conflict, and (d) correcting v1's
reading of `dense_token_offset_candidates`.  Those candidates are lanes where a
difference must exist; they do not bound the first differing lane, which against an
unknown finite word may be any of 0..3.

Per case it reports agreement and, separately, every difference with a class:
  visibility_event_receipt   candidate sees genuine copy events the frozen oracle could not
  visibility_raw_reference   candidate scorer receives the true raw words (contract.raw_words)
  derived_diagnostic         additional candidate finding at another position or key
  candidate_missed           oracle-measured conflict/missing atom with no candidate counterpart
  transport                  explained by a disclosed bridge substitution or fidelity deviation
  unchecked                  observable detail not reported by one side
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PHASE_ORDER = {"B": 0, "C0_raw": 1, "C1_post_rep": 2, "C2_post_page": 3, "D_selection": 4,
               "public_document": 5, "terminal": 6}


def jl(path):
    return [json.loads(l) for l in open(path, "rb").read().decode("utf-8").splitlines() if l.strip()]


def cpos(row, phase):
    p = "B" if phase.startswith("B") and phase.endswith("_entry_state") else phase
    return ((row if row is not None else 10 ** 8), PHASE_ORDER.get(p, -1))


def map_pos(cw, row, phase):
    m = cw["phase_map"].get(phase)
    if m is None:
        return None
    if m.startswith("B{row}"):
        return (row, "B%s_entry_state" % row)
    if m in ("public_document", "terminal"):
        return (None, m)
    return (row, m)


def key_of(x):
    return x.get("check")


def ckeys(cw, table, chk):
    v = cw[table].get(chk)
    return v


def classify_extra(cw, key):
    for cls in ("visibility_event_receipt", "visibility_raw_reference"):
        if key in cw["extra_classes"][cls]:
            return cls
    return "derived_diagnostic"


def compare_case(e, res, tr, fid, cw):
    ex = e["expected"]
    out = {"case_id": e["case_id"], "run_id": e["run_id"], "classification": e["classification"],
           "expected_verdict": ex["verdict"], "candidate_verdict": res["verdict"],
           "candidate_first_divergent_phase": res.get("first_divergent_phase"),
           "transport_deviations": tr.get("deviations", []), "transport_notes": tr.get("notes", []),
           "transport_fidelity_exact": fid.get("transport_exact") if fid else None,
           "transport_fidelity_differences": fid.get("differences") if fid else None}
    cconf, cmiss = res.get("conflicts", []), res.get("missing", [])
    # ---- first observable discrepancy (interval-aware)
    entries = cconf or cmiss
    cfirst = (entries[0].get("row"), entries[0]["phase"]) if entries else None
    out["candidate_first"] = {"row": cfirst[0], "phase": cfirst[1], "key": entries[0]["key"]} if entries else None
    f = ex["first"]
    if f is None:
        out["first_relation"] = "n/a" if cfirst is None else "candidate_only"
    elif cfirst is None:
        out["first_relation"] = "candidate_none"
    else:
        a = map_pos(cw, f["row_from"], f["phase_from"])
        b = map_pos(cw, f["row"], f["phase"])
        ends = sorted([x for x in (a, b) if x is not None], key=lambda p: cpos(*p))
        out["expected_first_mapped"] = {"from": a, "to": b}
        if not ends:
            out["first_relation"] = "unmappable"
        else:
            lo, hi, c = cpos(*ends[0]), cpos(*ends[-1]), cpos(*cfirst)
            if cfirst == b and a == b:
                out["first_relation"] = "exact"
            elif lo <= c <= hi:
                out["first_relation"] = "within_interval"
            else:
                out["first_relation"] = "earlier" if c < lo else "later"
    # ---- conflicts: atom-level matching
    used = set()
    atoms = []
    for x in ex["conflicts"]:
        pos = [p for p in {map_pos(cw, x["row_from"], x["phase_from"]), map_pos(cw, x["row"], x["phase"])} if p]
        keys = ckeys(cw, "conflict_keys", key_of(x))
        at_pos = [i for i, c in enumerate(cconf) if (c.get("row"), c["phase"]) in pos]
        with_key = [i for i in at_pos if keys and cconf[i]["key"] in keys]
        atom = {"row": x["row"], "phase": x["phase"], "phase_from": x["phase_from"], "check": x["check"],
                "slot_id": x["slot_id"], "mapped_positions": pos, "crosswalk_keys": keys,
                "position_covered": bool(at_pos), "key_covered": bool(with_key)}
        if keys is None:
            atom["status"] = "unchecked_no_crosswalk_entry"
        elif keys == []:
            atom["status"] = "unchecked_no_candidate_analogue"
        elif with_key:
            atom["status"] = "matched"
        elif at_pos:
            atom["status"] = "position_only"
        else:
            atom["status"] = "candidate_missed"
        used.update(at_pos)
        # word / lane / offset detail
        d = (x.get("detail") or {}).get("first") if isinstance((x.get("detail") or {}).get("first"), dict) else None
        if x["slot_id"] is not None and with_key:
            hit = next((cconf[i] for i in with_key if cconf[i].get("id") == x["slot_id"]), None)
            det = {}
            if hit is None:
                det["slot"] = "candidate_reports_other_slot:" + ",".join(str(cconf[i].get("id")) for i in with_key)
            else:
                det["slot"] = "equal"
                if d and d.get("lane") is not None:
                    for k_o, k_c in (("lane", "lane"), ("dense_token_offset", "dense_offset"), ("compact_offset", "compact_offset"),
                                     ("observed_le", "observed_le"), ("reference_le", "expected_le")):
                        if k_c in hit:
                            det[k_o] = "equal" if hit[k_c] == d.get(k_o) else "differ:%s/%s" % (d.get(k_o), hit[k_c])
                        else:
                            det[k_o] = "unchecked_candidate_absent"
                elif d:
                    det["observed_le"] = ("equal" if hit.get("observed_le") == d.get("observed_le") else
                                          "differ:%s/%s" % (d.get("observed_le"), hit.get("observed_le"))) \
                        if "observed_le" in hit else "unchecked_candidate_absent"
                    det["lane"] = "oracle_reference_unknown"
            atom["detail"] = det
        atoms.append(atom)
    extras = []
    for i, c in enumerate(cconf):
        if i in used:
            continue
        extras.append({"row": c.get("row"), "phase": c["phase"], "key": c["key"], "id": c.get("id"),
                       "lane": c.get("lane"), "dense_offset": c.get("dense_offset"),
                       "class": classify_extra(cw, c["key"])})
    matched_pos_extra_keys = []
    for i in used:
        c = cconf[i]
        if not any(c["key"] in (a["crosswalk_keys"] or []) for a in atoms if (c.get("row"), c["phase"]) in a["mapped_positions"]):
            matched_pos_extra_keys.append({"row": c.get("row"), "phase": c["phase"], "key": c["key"],
                                           "class": classify_extra(cw, c["key"])})
    # ground pair cross-check for candidate raw-reference lanes
    gb = (e["ground"].get("first_record_divergence") or {}).get("byte")
    gphase = (e["ground"].get("first_record_divergence") or {}).get("phase")
    ground_check = None
    if gb:
        hit = next((c for c in cconf if c["phase"] == gphase and c.get("id") == gb["slot_id"] and "lane" in c), None)
        if hit is None:
            ground_check = {"status": "unchecked_candidate_absent", "phase": gphase, "slot_id": gb["slot_id"]}
        else:
            ground_check = {"status": "checked", "phase": gphase, "slot_id": gb["slot_id"], "key": hit["key"],
                            "lane": hit["lane"] == gb["lane_from_word_pair"],
                            "dense_offset": hit.get("dense_offset") == gb["dense_token_offset"],
                            "compact_offset": hit.get("compact_offset") == gb["compact_offset"],
                            "observed_le": hit.get("observed_le") == gb["recorded_le"],
                            "expected_le": hit.get("expected_le") == gb["true_le"] if "expected_le" in hit else None}
    # ---- missing atoms
    mused = set()
    matoms = []
    for x in ex["missing"]:
        keys = ckeys(cw, "missing_keys", key_of(x))
        pos = map_pos(cw, x["row"], x["phase"])
        if keys is None:
            hits, status = [], "unchecked_no_crosswalk_entry"
        elif keys == "dependent":
            hits = [i for i, m in enumerate(cmiss) if m.get("row") == x["row"]]
            status = "matched_dependent" if hits else "candidate_missed"
        elif pos is None:
            hits, status = [], "unchecked_no_candidate_analogue"
        else:
            at = [i for i, m in enumerate(cmiss) if (m.get("row"), m["phase"]) == pos]
            hits = [i for i in at if keys and m_key(cmiss[i]) in keys]
            status = "matched" if hits else ("position_only" if at else "candidate_missed")
            hits = hits or at
        mused.update(hits)
        matoms.append({"row": x["row"], "phase": x["phase"], "check": x["check"], "status": status})
    mextras = [{"row": m.get("row"), "phase": m["phase"], "key": m["key"], "class": classify_extra(cw, m["key"])}
               for i, m in enumerate(cmiss) if i not in mused]
    out.update({"conflict_atoms": atoms, "candidate_extra_conflicts": extras,
                "candidate_extra_keys_at_matched_positions": matched_pos_extra_keys,
                "ground_pair_check": ground_check, "missing_atoms": matoms, "candidate_extra_missing": mextras,
                "candidate_conflict_keys": res.get("conflict_keys"), "candidate_missing_keys": res.get("missing_keys")})
    # ---- decision and difference classes
    missed = [a for a in atoms if a["status"] in ("candidate_missed", "position_only")] + \
             [m for m in matoms if m["status"] in ("candidate_missed", "position_only")]
    bad_detail = [a for a in atoms if any(str(v).startswith("differ") or str(v).startswith("candidate_reports_other")
                                           for v in (a.get("detail") or {}).values())]
    verdict_eq = ex["verdict"] == res["verdict"]
    first_ok = out["first_relation"] in ("exact", "within_interval", "n/a")
    out["semantic_agree"] = verdict_eq and first_ok and not missed and not bad_detail
    diffs = []
    if not verdict_eq:
        cls = "measured_disagreement"
        vis = [x for x in extras + matched_pos_extra_keys + mextras if x["class"].startswith("visibility")]
        if ex["verdict"] in ("P", "U") and res["verdict"] == "M" and vis and \
                all(x["class"].startswith("visibility") for x in extras + matched_pos_extra_keys):
            cls = "visibility"
        elif ex["verdict"] == "P" and res["verdict"] == "U" and mextras and all(x["class"].startswith("visibility") for x in mextras):
            cls = "visibility"
        elif fid and not fid.get("transport_exact"):
            cls = "transport"
        diffs.append({"what": "verdict", "expected": ex["verdict"], "candidate": res["verdict"], "class": cls})
    if not first_ok:
        diffs.append({"what": "first", "relation": out["first_relation"], "expected": f, "candidate": out["candidate_first"]})
    for a in missed:
        diffs.append({"what": "oracle_atom_without_candidate_counterpart", "atom": a, "class": "candidate_missed"})
    for a in bad_detail:
        diffs.append({"what": "byte_detail", "atom": {k: a[k] for k in ("row", "phase", "check", "slot_id", "detail")}})
    for x in extras:
        diffs.append({"what": "candidate_extra_conflict", "item": x, "class": x["class"]})
    for x in matched_pos_extra_keys:
        diffs.append({"what": "candidate_extra_key", "item": x, "class": x["class"]})
    for x in mextras:
        diffs.append({"what": "candidate_extra_missing", "item": x, "class": x["class"]})
    unchecked = [a for a in atoms if a["status"].startswith("unchecked")] + [m for m in matoms if m["status"].startswith("unchecked")]
    out["differences"] = diffs
    out["unchecked_observables"] = unchecked
    return out


def m_key(m):
    return m["key"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--expected", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--crosswalk", default=os.path.join(HERE, "crosswalk-v1.json"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--summary", required=True)
    a = ap.parse_args(argv)
    cw = json.load(open(a.crosswalk, "rb"))
    trs = {t["case_id"]: t for t in jl(os.path.join(a.plan, "transport.jsonl"))}
    runs = {r["case_id"]: r for r in jl(os.path.join(a.plan, "run.jsonl"))}
    fids = {f["case_id"]: f for f in jl(os.path.join(a.plan, "fidelity.jsonl"))} \
        if os.path.exists(os.path.join(a.plan, "fidelity.jsonl")) else {}
    lines = []
    S = {"schema": "wp0043.semantic-summary.v2", "cases": 0, "scored": 0, "rejected_unsupported": [], "failed": [],
         "verdict_equal": 0, "semantic_agree": 0, "first_relation": {}, "verdict_pairs": {},
         "difference_classes": {}, "cases_with_differences": [], "unchecked_observable_count": 0}
    for e in jl(a.expected):
        S["cases"] += 1
        cid = e["case_id"]
        tr, r = trs[cid], runs.get(cid, {})
        if tr["status"] != "planned":
            S["rejected_unsupported"].append({"case_id": cid, "reason": tr["reason"], "needed": tr["needed_neutral_op"],
                                              "expected_verdict": e["expected"]["verdict"]})
            lines.append({"case_id": cid, "status": "rejected_unsupported", "reason": tr["reason"],
                          "needed_neutral_op": tr["needed_neutral_op"], "expected_verdict": e["expected"]["verdict"]})
            continue
        if r.get("status") != "scored":
            S["failed"].append(cid)
            lines.append({"case_id": cid, "status": r.get("status", "not_run")})
            continue
        res = json.load(open(os.path.join(a.plan, "cases", cid, "result.json"), "rb"))
        c = compare_case(e, res, tr, fids.get(cid), cw)
        c["status"] = "compared"
        S["scored"] += 1
        S["verdict_equal"] += c["expected_verdict"] == c["candidate_verdict"]
        S["semantic_agree"] += c["semantic_agree"]
        S["first_relation"][c["first_relation"]] = S["first_relation"].get(c["first_relation"], 0) + 1
        pair = c["expected_verdict"] + "->" + c["candidate_verdict"]
        S["verdict_pairs"][pair] = S["verdict_pairs"].get(pair, 0) + 1
        for d in c["differences"]:
            k = d["what"] + ":" + d.get("class", "-")
            S["difference_classes"][k] = S["difference_classes"].get(k, 0) + 1
        if c["differences"]:
            S["cases_with_differences"].append(cid)
        S["unchecked_observable_count"] += len(c["unchecked_observables"])
        lines.append(c)
        print("%-34s %s->%s first=%-15s agree=%s diffs=%d" % (cid, c["expected_verdict"], c["candidate_verdict"],
                                                              c["first_relation"], c["semantic_agree"], len(c["differences"])))
    S["extras_not_scored_against_frozen_rows"] = []
    for cid, r in sorted(runs.items()):
        if cid.startswith("X.") and r.get("status") == "scored":
            res = json.load(open(os.path.join(a.plan, "cases", cid, "result.json"), "rb"))
            S["extras_not_scored_against_frozen_rows"].append({
                "case_id": cid, "parent": trs[cid].get("parent"), "wire_ops": trs[cid].get("wire_ops"),
                "verdict": res["verdict"], "first_divergent_phase": res.get("first_divergent_phase"),
                "conflict_keys": res.get("conflict_keys"), "missing_keys": res.get("missing_keys"),
                "first_conflict": (res.get("conflicts") or [None])[0]})
    open(a.out, "wb").write(b"".join((json.dumps(x, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii") for x in lines))
    open(a.summary, "wb").write(json.dumps(S, sort_keys=True, indent=1).encode("ascii") + b"\n")
    print("cases=%d scored=%d rejected=%d failed=%d verdict_equal=%d semantic_agree=%d" % (
        S["cases"], S["scored"], len(S["rejected_unsupported"]), len(S["failed"]), S["verdict_equal"], S["semantic_agree"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
