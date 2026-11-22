"""Field ranking and original Posting decisions have different denominators."""
from collections import Counter

import matrix
import online
import run
from inputs import check


def field_row(name, truth, item, context, cuts):
    expected = truth[name]
    truth_key = online.key(expected) if expected is not None else None
    eligible = context["registry"][name]
    logits = item.scores.get(name)
    applicable = name != "subtotal_status" or item.summary_target
    reasons = []
    scores, top = {}, []
    gap = delta = passes_sim = passes_margin = zero = None
    tie = unique_correct = None
    leaders = []
    if logits is None:
        if not applicable:
            reasons.append("not_applicable")
        elif context["controller"]["ambiguous_reason"]:
            reasons.append(context["controller"]["ambiguous_reason"])
        elif len(eligible) < 2:
            reasons.append("incomplete_candidates")
        else:
            reasons.append(item.reason or "no_readout")
    else:
        choices = item.choices[name]
        check(len(choices) == len(eligible) == len(logits), "duplicate normalized or missing candidate")
        scores = {online.key(v): float(x) for v,x in zip(choices, logits, strict=True)}
        check(scores.keys() == eligible.keys(), "candidate-value mismatch")
        ordered = sorted(scores, key=lambda k: (-scores[k], k))
        top = [{"key": k, "value": eligible[k], "score": scores[k]} for k in ordered[:2]]
        leaders = [k for k in ordered if scores[k] == top[0]["score"]]
        tie = len(leaders) > 1
        gap = top[0]["score"] - top[1]["score"]
        zero = context["actual_reads"][name]["read_norm"] <= matrix.EPS
        top_logits = logits.topk(2).values
        passes_sim = bool(top_logits[0] >= cuts[0])
        passes_margin = bool(top_logits[0] - top_logits[1] >= cuts[1])
        if zero:
            reasons.append("zero_readout")
        if tie:
            reasons.append("exact_top_tie")
        if truth_key in scores:
            delta = scores[truth_key] - max(v for k,v in scores.items() if k != truth_key)
            unique_correct = delta > 0
            if not tie and not unique_correct:
                reasons.append("wrong_unique_leader")
        if not passes_sim:
            reasons.append("below_similarity")
        if not passes_margin:
            reasons.append("below_margin")
    if truth_key is not None and truth_key not in eligible:
        reasons.append("expected_candidate_missing")
    return {"expected": expected, "expected_key": truth_key, "observed_field_applicable": applicable,
            "eligible_by_key": eligible, "expected_available": None if truth_key is None else truth_key in eligible,
            "scores_by_key": scores, "top_two": top, "leader_keys": leaders, "exact_top_tie": tie,
            "top_gap": gap, "true_minus_best_other": delta, "unique_leader_correct": unique_correct,
            "actual_read": context["actual_reads"].get(name), "zero_read": zero,
            "selected_similarity_pass": passes_sim, "selected_margin_pass": passes_margin, "flags": reasons}


def inspect_binder(state, contexts, truth, cuts):
    attempts = {}
    for item, ctx in zip(state.attempts, contexts, strict=True):
        ptr = "/".join(map(str, ctx["ptr"]))
        check(ptr not in attempts, "non-unique target event pointer")
        fields = {f:field_row(f, truth, item, ctx, cuts) for f in run.FIELDS}
        attempts[ptr] = {**ctx, "attempt_reason": item.reason, "zero": item.zero, "summary_target": item.summary_target,
                         "original_selected_typed": item.typed(cuts), "fields": fields}
    decision = matrix.result(state, cuts)
    ok, silent, posted = run.classification(decision, truth)
    return {"expected": {f:truth[f] for f in run.FIELDS}, "ambiguous": truth["ambiguous"], "stratum":truth["stratum"],
            "attempt_count": len(attempts), "attempts_by_ptr": attempts, "selected_binder_decision": decision,
            "selected_full_correct": ok, "selected_silent": silent, "selected_posted": posted}


def posting_cells(states, truth, grid):
    out = []
    for cell in grid:
        if not cell["answerable_postings"] and not cell["silent"]:
            continue
        counts = Counter()
        by_binder = {}
        for binder, state in sorted(states.items()):
            decision = matrix.result(state, (cell["tau"], cell["margin"]))
            t = truth[binder]
            wrong_fields = None
            if decision["type"] == "Posting":
                def normalized(v):
                    return None if v is None else online.key(v)
                wrong_fields = [f for f in run.FIELDS if normalized(decision[f]) != normalized(t[f])]
                counts.update(wrong_fields)
            ok,silent,posted = run.classification(decision,t)
            by_binder[binder] = {"pair": t["pair"], "target": t["target"], "decision": decision,
                                 "full_correct": ok, "silent": silent, "posted": posted, "wrong_fields": wrong_fields}
        out.append({**cell,"wrong_field_postings": {f:counts[f] for f in run.FIELDS},"by_binder": by_binder})
    return out


def owner_for(row):
    if row["attempt_count"] != 1:
        return None
    return next(iter(row["attempts_by_ptr"].values()))["fields"]["owner"]


def pair_row(members, same_suffix):
    ids = sorted(members)
    left,right = (members[k] for k in ids)
    check(left["ambiguous"] == right["ambiguous"], "mixed ambiguity")
    fields = {b:owner_for(r) for b,r in members.items()}
    registries = {b: r["final_registry"] for b,r in members.items()}
    same_keys = {f: set(registries[ids[0]][f]) == set(registries[ids[1]][f]) for f in run.FIELDS}
    fields_match = None
    if all(f is not None for f in fields.values()):
        fields_match = set(fields[ids[0]]["eligible_by_key"]) == set(fields[ids[1]]["eligible_by_key"])
    reasons = []
    delta = {b: f["true_minus_best_other"] if f else None for b,f in fields.items()}
    leaders = {b: f["leader_keys"] if f else [] for b,f in fields.items()}
    if not same_suffix:
        reasons.append("different_suffix")
    if not all(same_keys.values()) or fields_match is False:
        reasons.append("different_registry_candidates")
    for b,f in fields.items():
        if f is None:
            reasons.append(b + ":" + members[b]["selected_binder_decision"]["reason"])
        elif not f["scores_by_key"]:
            reasons.extend(b + ":" + flag for flag in f["flags"])
        elif f["expected_available"] is False:
            reasons.append(b + ":expected_candidate_missing")
    control = left["ambiguous"]
    true_keys = {b:online.key(r["expected"]["owner"]) if r["expected"]["owner"] is not None else None
                 for b,r in members.items()}
    if not control and len(set(true_keys.values())) != 2:
        reasons.append("same_expected_owner")
    tied = any(x is not None and x["exact_top_tie"] for x in fields.values())
    zero = any(x is not None and x["zero_read"] for x in fields.values())
    wrong_way = False
    if control:
        outcome = "ambiguous_control"
    elif reasons or any(v is None for v in delta.values()):
        outcome = "unscorable"
    else:
        n = sum(x > 0 for x in delta.values())
        outcome = ("neither_correct","one_correct","both_correct")[n]
        wrong_way = leaders[ids[0]] == [true_keys[ids[1]]] and leaders[ids[1]] == [true_keys[ids[0]]]
    return {"binders":ids,"targets":{b:r["target"] for b,r in members.items()}, "same_final_input_bytes":same_suffix,
            "same_final_candidate_keys":same_keys, "same_owner_candidates_at_target":fields_match, "true_owner_keys":true_keys,
            "deltas":delta, "leaders":leaders, "outcome":outcome,"wrong_way_flip":wrong_way,"any_exact_tie":bool(tied),
            "any_zero_read":bool(zero),"exceptions":reasons}


def summary(pairs, rows):
    answerable = [p for p in pairs.values() if p["outcome"] != "ambiguous_control"]
    controls = [p for p in pairs.values() if p["outcome"] == "ambiguous_control"]
    check((len(answerable), len(controls)) == (8,2), "unexpected pair denominator")
    counts = Counter(p["outcome"] for p in answerable)
    return {"answerable_pairs":len(answerable), "answerable_binders":2*len(answerable),
            "outcomes":{k:counts[k] for k in ("both_correct","one_correct","neither_correct","unscorable")},
            "wrong_way_flip_pairs":sum(p["wrong_way_flip"] for p in answerable),
            "exact_top_tie_pairs":sum(p["any_exact_tie"] for p in answerable),
            "zero_read_pairs":sum(p["any_zero_read"] for p in answerable),
            "ambiguous_pairs":len(controls),"ambiguous_binders":2*len(controls),
            "ambiguous_correctly_withheld":sum(r["selected_full_correct"] for r in rows.values() if r["ambiguous"]),
            "selected_raw_reasons":dict(Counter(r["selected_binder_decision"].get("reason","Posting") for r in rows.values()))}
