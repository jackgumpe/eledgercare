"""Reconcile the two immutable evidence freezes. This command never executes a model."""
import argparse
import gzip
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

AUTHOR = "c63d6f034209bac5b9b1b66488587e527aaa36f7"
REVIEW = "f8bda47a25d8c5170240a68ea5b72a11478b3d1b"
AREAS = {AUTHOR: "docs/research/WP-0036/evidence/attempt-02", REVIEW: "docs/reviews/WP-0036/evidence"}


def read(commit, name):
    path = f"{commit}:{AREAS[commit]}/{name}.json.gz"
    return json.loads(gzip.decompress(subprocess.check_output(["git", "cat-file", "blob", path])))


def index(rows, *fields):
    mapping = {tuple(r[f] for f in fields): r for r in rows}
    if len(mapping) != len(rows):
        raise ValueError(f"Duplicate key in {fields}")
    return mapping


def equal(label, x, y):
    if x != y:
        raise ValueError(f"{label}: {x!r} differs from {y!r}")


def finite_hex(x):
    return "+inf" if x in ("+infinity", "+inf") else x


def reconcile():
    art = lambda name: read(AUTHOR, name)
    rev = lambda name: read(REVIEW, name)
    result = {"author_evidence": AUTHOR, "independent_evidence": REVIEW}
    er = index(rev("archival-witnesses"), "binder", "model", "phase", "write")
    ea = index(art("E"), "binder", "model", "phase", "step")
    equal("historical member keys", er.keys(), ea.keys())
    roots = {}
    protected = 0
    for k, a in ea.items():
        b = er[k]
        equal(k, bool(a["excluded"]), b["reference_only"])
        if b["reference_only"]:
            equal(k, (a["witness"], b["witness"]), (None, None))
            continue
        av, bv = a["witness"], b["witness"]
        equal(k, [av["full_sha256"], av["vector_sha256"], av["valid"], av["text"] or "", av["confidence"]],
              [bv["slot"], bv["vector"], bv["valid"], bv["text"], bv["confidence"]])
        if a["subject_to_isolation"]:
            equal(k, av["full_sha256"], a["first_root_full_sha256"])
            equal(k, a["equal_since_declaration"], True)
            roots.setdefault(a["arm"], set()).add((av["full_sha256"], av["vector_sha256"]))
            protected += 1
    result["E"] = {"paired_references": len(ea)//2, "member_references": len(ea),
                   "reference_only_members": sum(b["reference_only"] for b in er.values()),
                   "protected_member_points": protected, "changed_protected_witnesses": 0,
                   "slot_and_vector_sha256": {arm: sorted(vals) for arm, vals in roots.items()}}

    terms = rev("terminal")
    fa = index(art("F"), "binder", "eta")
    equal("terminal keys", set(fa), {(bid, r["eta"]) for bid, term in terms.items() for r in term["eta"]})
    by_group = {}
    for (bid, eta), a in fa.items():
        t = terms[bid]
        b, = [v for v in t["eta"] if v["eta"] == eta]
        equal(bid, (a["typed"], a["native"], a["correct"], a["target"], a["pair"], a["horizon"]),
              (b["conditional"], t["native"], b["exact"], t["ptr"], t["pair"], t["horizon"]))
        for field, x in a["fields"].items():
            y = b["fields"][field]
            equal((bid, field), [x["raw"], x["directory"], x["decision"], x["dmin"], x["margin"], x["error"],
                                 x["ranking"], x["G1"], x["G2"], x["G3"]],
                  [y["text"], y["candidates"], y["choice"], y["dmin"], y["margin"], b[field+"_error"],
                   [[name, cost] for cost,name in y["ranks"]], y["g1"], y["g2"], y["g3"]])
        group = f"{a['task']}/{a['horizon']}/eta={float(eta)}"
        by_group.setdefault(group, Counter())[(a["typed"]["type"] if a["correct"] else "incorrect")] += 1
    fr = index(rev("twins"), "pair", "eta")
    ft = index(art("F3"), "pair", "eta")
    equal("twin keys", fr.keys(), ft.keys())
    for k, a in ft.items():
        b = fr[k]
        equal(k, [a["g"], a["mu"], a["delta"], a["Delta_alpha"], a["Delta_beta"], a["e_alpha"], a["e_beta"], a["checks"]],
              [b["g"], b["mu"], b["delta"], b["members"]["Alder"]["signed"], b["members"]["Cedar"]["signed"],
               b["members"]["Alder"]["error"], b["members"]["Cedar"]["error"], b["all_four_bounds"]])
    sw = index(art("F-sweep"), "binder", "eta", "path", "k")
    rw = index(rev("sweep"), "binder", "eta", "path", "k")
    equal("sweep keys", sw.keys(), rw.keys())
    counts = Counter()
    for k, a in sw.items():
        b = rw[k]
        equal(k, [a["attainable"], a["source"], a["truth"], a["rival"].casefold()],
              [b["attainable"], b["observed"], b["truth"], b["rival"]])
        if not a["attainable"]:
            counts["unattainable"] += 1
            continue
        f = b["field"]
        equal(k, [a["literal"], a["decision"], a["error"], a["actual_cost"], a["progress"], a["ranking"],
                  a["G1"], a["G2"], a["G3"], a["margin"], a["nearest_correct"], a["accepted_correct"]],
              [b["modified"], f["choice"], b["error"], b["cost"], b["progress"], [[s,d] for d,s in f["ranks"]],
               f["g1"], f["g2"], f["g3"], f["margin"], b["nearest_correct"], b["accepted_correct"]])
        counts["attainable"] += 1
        counts["under_half"] += int(a["under_half"])
        counts["under_half_correct"] += int(a["under_half"] and a["accepted_correct"])
        counts["rival_posted"] += int(a["decision"] == a["rival"])
    result["F"] = {"terminal_rows": len(fa), "paired_F3_rows": len(ft), "by_task_horizon_cost": by_group,
                   "perturbation_rows": len(sw), "perturbations": counts}

    da = index(art("D"), "binder")
    dr = index(rev("arithmetic"), "binder")
    equal("arithmetic keys", da.keys(), dr.keys())
    ledger = []
    for (bid,), a in da.items():
        b = dr[(bid,)]
        equal(bid, [t["raw_sha256"] for t in a["tables"]], [t[-1] for t in b["table_uses"]])
        equal(bid, a["grids"], b["grid"])
        closed = [s for s in b["schedules"] if s["subtotal"] is not None and s["close"] is not None]
        equal(bid, [(s["D"], s["literal"], s["body"]) for s in a["child_subtotals"]],
              [(s["D"], s["subtotal"]["literal"], [row["amount"] for row in s["body"]]) for s in closed])
        parent = terms[bid]["cross"]
        equal(bid, [(m["target_minor"], m["subtotal_minor"], m["residual"]) for m in a["maintenance"]],
              [(parent["left"], parent["right"], parent["diff"])] if parent else [])
        ledger.append({"binder": bid, "pair": a["pair"], "horizon": a["horizon"], "task": a["task"],
                       "physical_table_uses": len(b["table_uses"]), "observed_child_sums": [s["D"] for s in closed],
                       "open_or_unclosed_schedules": len(b["schedules"])-len(closed), "parent_difference_minor": parent["diff"] if parent else None,
                       "eligible_archive_stress_cells": len(b["grid"]), "native_outcome": terms[bid]["native"]})
    result["D_per_binder"] = sorted(ledger, key=lambda b:(b["task"],b["horizon"],b["pair"],b["binder"]))
    achecks = art("A")
    synthetic = rev("synthetic-A")
    ar = index(synthetic["token_cases"], "case", "eta")
    aa = index(achecks,"case","eta")
    equal("A keys", aa.keys(), ar.keys())
    for k, a in aa.items():
        b = ar[k]
        equal(k, [a["vocab"], a["logits"], a["rivals"], a["top"], a["runner"], a["theoretical_strict"],
                  a["observed_strict"], a["ordinary_f64le"], finite_hex(a["conf_f64le"]), a["score_f64le"]],
              [b["tokens"], b["logits"], b["rivals"], b["top"], b["second"], b["strict_real"],
               b["strict_fp"], b["m"], finite_hex(b["conf"]), b["sigma"]])
    qr = index(synthetic["conformal"], "alpha", "rule")
    qs = art("A-quantiles")
    for a in qs:
        k = (a["alpha"], "one_possible_draw" if a["mode"]=="selected" else "document_max")
        b = qr[k]
        equal(k, [a["k"], a["n"], a["values"], finite_hex(a["threshold_f64le"]), a["strict_escape"], a["ties_escape"]],
              [b["k"], b["n"], b["values"], finite_hex(b["cut"]), b["strict_escapes"], b["tie_escapes"]])
    result["A"] = {"synthetic_logit_rows": len(aa), "synthetic_conformal_rows": len(qs),
                   "archived_logit_rows": 0, "actual_error_document_count": None}
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = reconcile()
    payload = (json.dumps(result, indent=2, sort_keys=True)+"\n").encode("utf-8")
    with args.output.open("xb") as out:
        out.write(payload)
    print(hashlib.sha256(payload).hexdigest())
