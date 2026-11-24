"""Reconcile both WP-0033 operators using immutable published tables and WP-0032 vectors."""
import argparse
import hashlib
import json
import math
import re
import struct
import subprocess
from pathlib import Path

RESERVATION = "297f028350b1521096061cf27c7ce89702b73e54"
CELLS = ("AA", "AC", "CA", "CC")
NAMES = ("Alder", "Cedar")


def document(sha, path):
    assert re.fullmatch(r"[0-9a-f]{40}", sha)
    return json.loads(subprocess.check_output(["git", "cat-file", "blob", f"{sha}:{path}"]))


def unpack(data, fmt):
    raw = bytes.fromhex(data)
    return struct.unpack(f"<{len(raw) // struct.calcsize(fmt)}{fmt}", raw)


def dot(x, y):
    return math.fsum(a*b for a, b in zip(x, y, strict=True))


def budget(a, b):
    return 2e-5 * (1 + max(abs(a), abs(b)))


def signed(value, limit):
    return {"value": value, "zero_budget": limit, "sign": (
        "unresolved" if abs(value) <= limit else "positive" if value > 0 else "negative"
    )}


def effects(cells):
    """Positive differences consistently indicate a change from Cedar input to Alder input."""
    def contrast(plus, minus):
        return signed(math.fsum(cells[k] for k in plus) - math.fsum(cells[k] for k in minus),
                      sum(budget(cells[k], 0) for k in plus + minus))
    e = {name: contrast(pos, neg) for name, pos, neg in (
        ("feature_at_A_box", ["AA"], ["CA"]), ("feature_at_C_box", ["AC"], ["CC"]),
        ("box_at_A_feature", ["AA"], ["AC"]), ("box_at_C_feature", ["CA"], ["CC"]),
        ("interaction", ["AA","CC"], ["CA","AC"]), ("diagonal", ["AA"], ["CC"]))}
    for first, second in (("feature_at_A_box","box_at_C_feature"), ("box_at_A_feature","feature_at_C_box")):
        assert abs(e[first]["value"] + e[second]["value"] - e["diagonal"]["value"]) <= 1e-14
    return e


def gain_roots(components, terms):
    cells = {}
    for tag, reference in components.items():
        intercept = reference["omitted_numerator"]
        slope = reference["term_numerators"][2]
        beta = terms[tag]["beta"]
        assert intercept > 0 and slope < 0 and beta > 0
        root = -intercept / slope
        # Solves |P+rho L| <= 2e-5*(1+|P+rho L|) for the analytical zero check.
        width = 2e-5 / ((1-2e-5)*abs(slope))
        cells[tag] = {"P":intercept, "L":slope, "rho_root":root, "eta_root":beta*root,
                      "rho_zero_budget_band":[root-width,root+width]}
    contrast_roots = {}
    for prefix in "AC":
        a,c = (cells[prefix+d] for d in "AC")
        contrast_roots[prefix] = (a["P"]-c["P"]) / (c["L"]-a["L"])
    windows = {}
    for mode in ("rho", "eta"):
        key = mode+"_root"
        windows[mode] = {"all_four_open":[max(cells[tag][key] for tag in ("AC","CC")),
                                           min(cells[tag][key] for tag in ("AA","CA"))],
                         "original_twins_open":[cells["CC"][key],cells["AA"][key]]}
    return {"cells":cells,"raw_relative_donor_roots":contrast_roots,"correct_rank_intervals":windows}


def by_key(sha, area):
    records = document(sha, f"docs/{area}/WP-0033/evidence/parity.json")
    rows = {(r["arm"], r["mode"], str(r["point"]), r["cell"]): r for r in records}
    assert len(rows) == len(records) == 52
    return rows


def predictions(cases, tag, rho):
    c = cases[tag]
    terms = []
    for name in ("R","V","E"):
        vec = c["terms"][name]["vector"]
        assert hashlib.sha256(bytes.fromhex(vec["bytes_le"])).hexdigest() == vec["sha256"]
        terms.append(unpack(vec["bytes_le"], "d"))
    y = [r + v + rho*e for r, v, e in zip(*terms, strict=True)]
    length = math.sqrt(dot(y, y))
    anchors = unpack(c["binding"]["ordered_anchor_f32le"], "f")
    a, b = anchors[:128], anchors[128:]
    scores = [dot(g, y) / (length + 1e-8) for g in (a, b)]
    return {"numerator": dot([x-z for x,z in zip(a,b,strict=True)], y), "read_norm": length,
            "Alder": scores[0], "Cedar": scores[1], "margin": scores[0]-scores[1]}


def reconcile(author, reviewer):
    contract = document(RESERVATION, "docs/coordination/WP-0033/contract.json")
    old = contract["input_pins"]
    terms = document(old["WP32_author"], "docs/research/WP-0032/evidence/M1.json")["cells"]
    previous = document(old["WP32_reconciliation"], "docs/coordination/WP-0032/reconciliation.json")["root_scalar_tables"]
    rows = by_key(author, "research")
    independent = by_key(reviewer, "reviews")
    expected = {("M1", mode, point, tag) for mode in ("relative","absolute") for point in contract[mode] for tag in CELLS}
    expected.update(("M3","hybrid","empty",tag) for tag in CELLS)
    assert set(rows) == set(independent) == expected
    maxima = {}
    def check(group, location, a, b):
        error, limit = abs(a-b), budget(a,b)
        assert math.isfinite(error) and error <= limit, (group,location,a,b,limit)
        if group not in maxima or error > maxima[group]["residual"]:
            maxima[group] = {"location":location,"residual":error,"limit":limit}
    result = {}
    native_controls = 0
    for (arm,mode,point,tag), a in rows.items():
        loc = "/".join((arm,mode,point,tag))
        b = independent[arm,mode,point,tag]
        for field in ("score_f32le","read_sha256","matrix_sha256"):
            assert a[field] == b[field] and re.fullmatch(r"[0-9a-f]+",a[field]), (loc,field)
        scores = unpack(a["score_f32le"], "f")
        assert len(a["read_sha256"]) == len(a["matrix_sha256"]) == 64
        assert len(scores) == 2 and scores[0]-scores[1] == a["margin"] == b["margin"]
        for field in ("numerator","read_norm","margin"):
            check("operator_"+field,loc,a[field],b[field])
        obs = {**dict(zip(NAMES,scores,strict=True)), **{k:a[k] for k in ("numerator","read_norm","margin")}}
        rec = {"observed":obs, "score_f32le":a["score_f32le"],
               "signed_numerator":signed(a["numerator"],budget(a["numerator"],0)),
               "score_cutoff_pass":max(scores) >= 1.0,
               "gap_cutoff_pass":struct.unpack("<f", struct.pack("<f", abs(a["margin"])))[0] >= struct.unpack("<f",struct.pack("<f",0.1))[0]}
        if arm == "M1":
            gain = contract[mode][point]
            beta = terms[tag]["beta"]
            rho = gain if mode == "relative" else gain/beta
            predicted = predictions(terms,tag,rho)
            rec.update(requested=gain,rho=rho,eta=rho*beta,predicted=predicted)
            for field, value in predicted.items():
                check("M1_WP32_"+field,loc,obs[field],value)
        if (arm == "M1" and mode == "relative" and point=="1") or (arm=="M3" and tag in ("AA","CC")):
            historic = previous[arm][tag if arm=="M1" else "0"+tag[0]]
            assert a["score_f32le"] == historic["native_score_f32le"]
            native_controls += 1
        result[loc]=rec
    assert native_controls==6
    m1_contrasts = {}
    for mode in ("relative","absolute"):
        for point in contract[mode]:
            for prefix in "AC":
                left,right=(result[f"M1/{mode}/{point}/{prefix}{d}"]["observed"] for d in "AC")
                m1_contrasts[f"{mode}/{point}/{prefix}"]={
                    field:signed(left[field]-right[field],budget(left[field],0)+budget(right[field],0))
                    for field in ("margin","numerator")}
    m3 = {field:effects({tag:result[f"M3/hybrid/empty/{tag}"]["observed"][field] for tag in CELLS})
          for field in (*NAMES,"margin")}
    return {"reservation":RESERVATION,"author_evidence":author,"independent_evidence":reviewer,
            "exact_rows":len(result),"original_score_controls":native_controls,"residual_maxima":maxima,
            "rows":result,"M1_gain_roots":gain_roots(previous["M1"],terms),"M1_donor_contrasts":m1_contrasts,"M3_normalized_effects":m3}


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("author")
    parser.add_argument("reviewer")
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    report=reconcile(args.author,args.reviewer)
    with args.output.open("x",encoding="utf-8",newline="\n") as f:
        json.dump(report,f,indent=2,allow_nan=False)
        f.write("\n")
