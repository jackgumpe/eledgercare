"""Compare the two frozen CPU returns and recompute contrasts from raw scores."""
import argparse
import hashlib
import json
import struct
import subprocess
from fractions import Fraction
from pathlib import Path

NAMES = ("Alder", "Cedar")
BASE = "40fa358cd3c94efbf8fe9df93f188e7c02e1c6e4"
READ_KEYS = ("scores", "score_f32le", "margin_f64le", "top", "controller", "registry",
             "owner_eligible", "native_scope_clear", "zero_read", "query_sha256",
             "read_sha256", "read_f32le", "matrix_sha256", "owner_columns_sha256")


def blob(revision, path):
    return subprocess.check_output(["git", "cat-file", "blob", f"{revision}:{path}"])


def record(revision, path):
    return json.loads(blob(revision, path))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def compare_read(a, r):
    for key in READ_KEYS:
        assert a[key] == r[key], key
    assert a["ordered_anchor_sha256"] == r["anchor_sha256"]
    assert sha(bytes.fromhex(a["read_f32le"])) == a["read_sha256"]
    scores = dict(zip(NAMES, struct.unpack("<ff", bytes.fromhex(a["score_f32le"])), strict=True))
    assert scores == a["scores"]
    exact = Fraction(scores["Alder"]) - Fraction(scores["Cedar"])
    assert exact == a["margin"] == r["margin"]
    return exact


def reconcile(arm, author, review, archive, binding, prefix_blobs):
    assert author["status"] == "completed" and review["native_gate"]
    assert all(g["pass"] for g in author["gates"].values())
    assert author["owner_order"] == list(NAMES)
    baselines = {}
    for name in NAMES:
        source = author["sources"][name]
        old = source["write7_read"]
        rb = review["write7"][name]
        baselines[name[0]] = compare_read(old, rb)
        assert sha(prefix_blobs[name]) == old["matrix_sha256"] == source["snapshot"]["matrix_sha256"]
        assert source["snapshot"]["discrete"]["registry"] == rb["full_registry"]
        assert sha(bytes.fromhex(source["frozen_query_f32le"])) == old["query_sha256"]
        assert sha(bytes.fromhex(source["ordered_anchors_f32le"])) == old["ordered_anchor_sha256"]
        for horizon in (12, 30):
            run = f"{arm}/{horizon}"
            assert old["ordered_anchor_sha256"] == binding[run]["anchor_sha256"]
            assert old["query_sha256"] == binding[run][name]["query_sha256"]
            for key in ("score_f32le", "matrix_sha256", "read_sha256", "query_sha256", "registry", "controller"):
                assert old[key] == archive[run, 7][name]["read"][key]
        donor = source["donor"]
        assert donor["projection_sha256"] == review["donor"][name]["k_v_a_b_sha256"]
        assert donor["literal"] == "Ledger: " + name and donor["pointer"] == [1, 1, 7]
    exact_margins = {}
    table = {}

    def check_cell(label, a, row):
        r = review["cells"][label]
        post = a["read"]
        m = compare_read(post, r["post"])
        assert a["recipient_before_event"] == a["after_donor_hook"]
        assert a["recipient_before_event"]["matrix_sha256"] == r["recipient_matrix_sha256"]
        assert a["donor_input_sha256"] == author["sources"][r["donor"]]["donor_input_sha256"]
        assert a["fresh_residual_sha256"] == r["residual_sha256"]
        assert a["source_states_before"] == a["source_states_after"]
        assert all(v["matrix_sha256"] == r["source_snapshot_sha256_before_and_after"][k]
                   for k, v in a["source_states_before"].items())
        assert r["registry_controller_unchanged"]
        increment = m - row
        assert increment == a["increment"] == r["increment"]
        assert row == a["baseline_margin"] == r["row_baseline"]
        if label in ("AA", "CC"):
            for horizon in (12, 30):
                archived = archive[f"{arm}/{horizon}", 8][r["donor"]]["read"]
                for key in archived:
                    observed = [post["scores"][n] for n in NAMES] if key == "scores" else post[key]
                    assert observed == archived[key], key
        table[label] = {"baseline_margin": float(row), "score_f32le": post["score_f32le"],
                        "scores": post["scores"], "margin": float(m), "increment": float(increment),
                        "winner": post["top"], "eligible": post["owner_eligible"], "depth": post["controller"]["depth"]}
        return m

    for label in ("AA", "AC", "CA", "CC"):
        exact_margins[label] = check_cell(label, author["cells"][label], baselines[label[0]])
    aa, ac, ca, cc = (exact_margins[p] for p in ("AA", "AC", "CA", "CC"))
    da, dc = aa-ac, ca-cc
    pa, pc = aa-ca, ac-cc
    i, native = da-dc, aa-cc
    assert i == pa-pc and native == da+pc == pa+dc
    contrasts = dict(DA=da, DC=dc, PA=pa, PC=pc, I=i, delta_native=native)
    assert contrasts == author["contrasts"] == review["contrasts"]
    threshold = max(abs(da), abs(dc)) / 20
    trigger = da < 0 and dc < 0 and abs(i) <= threshold
    assert trigger == author["trigger"]["run"] == review["zero"]["trigger"]
    assert float(threshold) == author["trigger"]["five_percent_limit"] == review["zero"]["limit"]
    d0 = None
    if trigger:
        za, zc = (check_cell(label, author["empty_cells"][label], Fraction(0)) for label in ("0A", "0C"))
        d0 = za-zc
        assert d0 == author["empty_cells"]["D0"] == review["zero"]["D0"]
    else:
        assert author["empty_cells"] is None and review["zero"]["D0"] is None
    assert set(table) == set(review["cells"])
    return {"cells": table, "contrasts": {k:float(v) for k,v in contrasts.items()},
            "zero_triggered": trigger, "five_percent_limit": float(threshold),
            "D0": float(d0) if d0 is not None else None,
            "exact_interaction_and_native_identities": True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("author_revision")
    p.add_argument("author_evidence_dir")
    p.add_argument("review_revision")
    p.add_argument("review_replay_json")
    p.add_argument("output", type=Path)
    args = p.parse_args()
    revs = [args.author_revision, args.review_revision]
    review = record(revs[1], args.review_replay_json)
    path = args.author_evidence_dir.rstrip("/")
    steps = "docs/reviews/WP-0030/evidence/steps.jsonl"
    rows = [json.loads(line) for line in blob(BASE, steps).splitlines()]
    archive = {(r["run"],r["step"]):r for r in rows if r["phase"]=="post" and r["step"] in (7,8)}
    bindings = record(BASE, "docs/reviews/WP-0030/evidence/bindings.json")
    results = {}
    for arm in ("M1", "M3"):
        author = record(revs[0], f"{path}/{arm}.json")
        matrices = {n:blob(revs[0], f"{path}/{arm}-{n}-write7.f32") for n in NAMES}
        results[arm] = reconcile(arm, author, review["probes"][arm], archive, bindings, matrices)
    result = {"author_revision":revs[0], "review_revision":revs[1],
              "archived_control_revision":BASE, "probes":results}
    with args.output.open("x",encoding="utf-8",newline="\n") as stream:
        json.dump(result,stream,indent=2,allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
