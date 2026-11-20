"""WP-0018 /003 reviewer reconciliation against the authors' immutable Git objects (eld-rd-reviewer).

CPU-only. Joins the reviewer's own paired and attribution rows (scratch, hash-checked against the
committed second-phase receipt) with the pair author's and word tracer's committed rows, the
coordinator's reconciliation, and the authors' published numeric claims. Also reproduces the
WP-0015 supplementary numeric-token checks from the historical helper and an independent
re-implementation. Never runs OCR, WinRT, rendering or GPU work; writes only to --out.
"""
import sys

sys.dont_write_bytecode = True

import argparse
import ast
import json
import re
import types
import unicodedata
from collections import Counter
from pathlib import Path

import review_checks as rc
import review_attribution as ra

PAIR_SOURCE = "3a1591768828bf72a9cce42db05f0d7c95f6cd60"
PAIR_EVIDENCE = "01625378954a55da0fe7ce93c5cbb3b2e174c797"
PAIR_REPORT = "8479c239bc21b8ecc1bc82a60194fcec841b4408"
WORDS_SOURCE = "aff3970f2c2cf800139b1e0456ae516a4074e4d5"
WORDS_WITNESS = "873ff5b1e7de51b54cba1f3ddd9e52c3b68263d7"
WORDS_COVERAGE = "00ce51886d8015f887bb21f17bcd5478cb0b38bf"
WORDS_REPORT = "2bf46a4420b5da29eb94975df4d16e7b12947f20"
COORDINATOR = "b1a033d26988fd4b5718803599c86a9023754145"
HELPER_COMMIT = "ce4206f20d63101f6344121eaaeeeb86d2ec85a0"
BASE = "918701ae318b01395b911b9dbdf597e43908665b"
PAIR = "docs/research/WP-0018/pair"
WORDS = "docs/research/WP-0018/words"
WITNESS_SHA256 = "64b8e29bcacee8d0978e422bfc3f3c6471877a5c2b30eb69104891f7c073c5a8"
RECEIPT = rc.HERE / "evidence" / "second-phase" / "receipt.json"

# Published numeric claims in the canonical author reports, checked against the reviewer's own rows.
CLAIMS = {
    "001": dict(H=dict(correct_before=15, correct_after=14, gain=0, loss=1, unchanged_wrong=5, unchanged_right=14,
                       already_fallback=0, extra_before=0, extra_after=0, edits=15, ref_chars=570, lines=(13, 16),
                       prose_crit_wrong=(3, 8), table_crit_wrong=(5, 11), unflagged=(8, 19), flagged=0,
                       changed_pages=[2]),
                A=dict(correct_before=235, correct_after=213, gain=0, loss=22, unchanged_wrong=65, unchanged_right=213,
                       already_fallback=0, extra_before=0, extra_after=0, edits=257, ref_chars=8821, lines=(237, 288),
                       prose_crit_wrong=(51, 108), table_crit_wrong=(43, 144), unflagged=(94, 252), flagged=0,
                       changed_pages=[5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60],
                       iou=0.9966666666666667,
                       missing_both=["page/5/table/1/row/5/col/1", "page/15/table/1/row/4/col/2",
                                     "page/20/table/1/row/5/col/1", "page/30/table/1/row/3/col/2",
                                     "page/30/table/1/row/5/col/1"])),
    "002": dict(H=dict(cells_wrong=5, cells_raw=5, cells_none=0, prose_wrong=3, prose_raw=3, empty_losses=1),
                A=dict(cells_wrong=65, cells_raw=60, cells_none=5, prose_wrong=51, prose_raw=51, empty_losses=22,
                       cell_single_word_char=54, cell_line_char_split=4, cell_whitespace=2,
                       prose_char=50, prose_char_split=16, prose_whitespace=1),
                spans=dict(H=88, A=1301)),
}
WORD_MAP = {  # word tracer first_supported_divergence -> admissible reviewer (stage, effect)
    "no_scored_divergence": {(None, "none")},
    "empty_reference_loses_exact_match_under_no_span_null": {(None, "none")},
    "anchored_raw_word_character_difference": {("winrt_text", "character_only")},
    "anchored_raw_line_character_difference": {("winrt_text", "character_only"), ("winrt_text", "character_and_split")},
    "raw_line_whitespace_difference": {("winrt_text", "whitespace_only")},
    "no_reference_eligible_group": {("no_intersecting_word", "empty_value")},
}


def gitb(commit, path):
    return rc.git_show(commit, path)


def gitj(commit, path):
    return json.loads(gitb(commit, path))


def jsonl(data):
    return [json.loads(line) for line in data.splitlines()]


def canon(obj):  # the pair author's canonical projection (reproduced, not imported)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


VOLATILE = {"environment", "ended_utc", "began_utc", "started_utc", "command", "cwd", "paired_dir", "paired_json_sha256"}
COMMITTED = {"paired-94eba5b/paired.json": rc.HERE / "evidence" / "second-phase" / "paired.json",
             "attribution-d9c5e7f/attribution.json": rc.HERE / "evidence" / "second-phase" / "attribution.json"}
FRESH = False  # set by --fresh: a new reproduction run instead of the reviewer's recorded scratch outputs


def stable(obj):
    if isinstance(obj, dict):
        return {k: stable(v) for k, v in obj.items() if k not in VOLATILE}
    if isinstance(obj, list):
        return [stable(v) for v in obj]
    return obj


def scratch(paths_root, receipt, name):
    """Recorded outputs must match the committed receipt byte for byte. A --fresh reproduction must match
    byte for byte for deterministic scorer/prediction files, and otherwise equal the committed evidence
    after removing run-environment, timestamp and path fields."""
    path = Path(paths_root) / name
    want = receipt["scratch_files"][name]["sha256"]
    if rc.sha256(path.read_bytes()) == want:
        return path
    if FRESH and name in COMMITTED and stable(rc.load(path)) == stable(rc.load(COMMITTED[name])):
        return path
    raise SystemExit(f"scratch file differs from the committed receipt/evidence: {name}")


def identity(ledger):
    out = {}
    pair_files = ["evidence/H/pair.json", "evidence/A/pair.json", "evidence/H/cells.jsonl", "evidence/A/cells.jsonl",
                  "evidence/H/baseline.json", "evidence/A/baseline.json", "evidence/constructed.json"]
    for f in pair_files:
        a, b = gitb(PAIR_EVIDENCE, f"{PAIR}/{f}"), gitb(PAIR_REPORT, f"{PAIR}/{f}")
        ledger.check("R1.1", f"pair/{f}/evidence==publication", a == b, rc.sha256(b), rc.sha256(a))
    for f in ("baseline.py", "method_control.py", "paired.py"):
        blobs = {c: gitb(c, f"{PAIR}/{f}") for c in (PAIR_SOURCE, PAIR_EVIDENCE, PAIR_REPORT)}
        ledger.check("R1.2", f"pair/{f}/source-unchanged", len(set(blobs.values())) == 1, None, None)
    for f in ("trace.py", "coverage.py"):
        evid = gitb(WORDS_COVERAGE, f"{WORDS}/{f}")
        final = gitb(WORDS_SOURCE, f"{WORDS}/{f}")
        ledger.check("R1.3", f"words/{f}/evidence-vs-source", evid == final + b"\n" and evid != final,
                     None, None, "evidence-producing blob differs from designated source only by one trailing blank line")
    w873, w00c, waff = (gitb(c, f"{WORDS}/trace.py") for c in (WORDS_WITNESS, WORDS_COVERAGE, WORDS_SOURCE))
    ledger.check("R1.3", "words/trace.py/witness==coverage", w873 == w00c, None, None)
    for f in ("witnesses.json", "coverage/locations-H.jsonl", "coverage/locations-A.jsonl", "coverage/pages-H.jsonl",
              "coverage/pages-A.jsonl", "coverage/summary.json"):
        cs = [c for c in (WORDS_WITNESS, WORDS_COVERAGE, WORDS_SOURCE, WORDS_REPORT)
              if f == "witnesses.json" or c != WORDS_WITNESS]
        blobs = {c: gitb(c, f"{WORDS}/{f}") for c in cs}
        ledger.check("R1.4", f"words/{f}/stable", len(set(blobs.values())) == 1, None, None)
    ledger.check("R1.5", "words/witness-sha256", rc.sha256(gitb(WORDS_WITNESS, f"{WORDS}/witnesses.json")) == WITNESS_SHA256,
                 rc.sha256(gitb(WORDS_WITNESS, f"{WORDS}/witnesses.json")), WITNESS_SHA256)
    for rec_name, commit, prefix in (("pair-reproduction.json", PAIR_EVIDENCE, ""), ("words-reproduction.json", WORDS_SOURCE, "")):
        rec = gitj(COORDINATOR, f"docs/coordination/WP-0018/{rec_name}")
        for item in rec["checkedAgainstCommittedGitBytes"]:
            data = gitb(commit, item["path"])
            ledger.check("R1.6", f"coordinator/{rec_name}/{item['path']}",
                         (rc.sha256(data), len(data)) == (item["sha256"], item["bytes"]), rc.sha256(data), item["sha256"])
    for fam in "HA":
        pj = gitj(PAIR_EVIDENCE, f"{PAIR}/evidence/{fam}/pair.json")
        cells = gitb(PAIR_EVIDENCE, f"{PAIR}/evidence/{fam}/cells.jsonl")
        ledger.check("R1.7", f"pair/{fam}/cells_jsonl_sha256", rc.sha256(cells) == pj["cells_jsonl_sha256"], None, None)
    # Commit ancestry and timing order recorded by Git.
    def ancestor(a, b):
        return rc.subprocess.run(["git", "-C", str(rc.REPO), "merge-base", "--is-ancestor", a, b]).returncode == 0
    for a, b in ((BASE, PAIR_SOURCE), (PAIR_SOURCE, PAIR_EVIDENCE), (PAIR_EVIDENCE, PAIR_REPORT), (BASE, WORDS_WITNESS),
                 (WORDS_WITNESS, WORDS_COVERAGE), (WORDS_COVERAGE, WORDS_SOURCE), (WORDS_SOURCE, WORDS_REPORT)):
        ledger.check("R1.8", f"ancestry/{a[:7]}<={b[:7]}", ancestor(a, b), None, None)
    times = {c: int(rc.git_bytes("log", "-1", "--format=%ct", c).decode()) for c in (WORDS_WITNESS, PAIR_SOURCE, PAIR_EVIDENCE)}
    ledger.check("R1.9", "order/witness-commit-before-paired-source", times[WORDS_WITNESS] < times[PAIR_SOURCE],
                 times, None, "committer time; does not prove when results were first viewed")
    out["committer_times"] = times
    return out


def pair_receipts(ledger, data, mine_dir, receipt, scorer):
    """Reproduce the pair author's receipt hashes and rows from the reviewer's own copies and scores."""
    out = {}
    for fam in "HA":
        paths = rc.family_paths(data, fam)
        pred = json.loads(paths["prediction"].read_bytes())
        pj = gitj(PAIR_EVIDENCE, f"{PAIR}/evidence/{fam}/pair.json")
        bj = gitj(PAIR_EVIDENCE, f"{PAIR}/evidence/{fam}/baseline.json")
        before = rc.load(scratch(mine_dir, receipt, f"paired-94eba5b/paired-{fam}-before.json"))
        after = rc.load(scratch(mine_dir, receipt, f"paired-94eba5b/paired-{fam}-after.json"))
        bsha = receipt["scratch_files"][f"paired-94eba5b/paired-{fam}-before.json"]["sha256"]
        asha = receipt["scratch_files"][f"paired-94eba5b/paired-{fam}-after.json"]["sha256"]
        ledger.check("R2.1", f"{fam}/score-bytes", (bsha, asha) == (pj["baseline_score_sha256"], pj["trial_score_sha256"])
                     and bj["score_sha256"] == bsha, [bsha, asha], [pj["baseline_score_sha256"], pj["trial_score_sha256"]])
        trial = {**pred, "pages": [{**p, "tables": []} for p in pred["pages"]]}
        trial_bytes = (json.dumps(trial, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode()
        mine_trial = json.loads(scratch(mine_dir, receipt, f"paired-94eba5b/{fam}-prediction-tables-empty.json").read_bytes())
        ledger.check("R2.2", f"{fam}/trial-prediction", rc.sha256(trial_bytes) == pj["trial_prediction_sha256"] and mine_trial == trial,
                     rc.sha256(trial_bytes), pj["trial_prediction_sha256"],
                     "author serialization reproduced from the reviewer copy; reviewer copy parses equal")
        retained = {**pred, "pages": [{k: v for k, v in p.items() if k != "tables"} for p in pred["pages"]]}
        ledger.check("R2.3", f"{fam}/retained-projection", rc.sha256(canon(retained)) == pj["retained_prediction_sha256"],
                     rc.sha256(canon(retained)), pj["retained_prediction_sha256"])
        changed = [f"/pages/{i}/tables" for i, p in enumerate(pred["pages"]) if p["tables"]]
        ledger.check("R2.4", f"{fam}/changed-pointers", changed == pj["changed_pointers"], changed, pj["changed_pointers"])
        c1 = CLAIMS["001"][fam]
        ledger.check("R2.4", f"{fam}/001-changed-pages", [i + 1 for i, p in enumerate(pred["pages"]) if p["tables"]] == c1["changed_pages"],
                     None, None)
        truth = rc.load(paths["truth"])
        ious = sorted({scorer.iou(r["tables"][0]["bbox"], p["tables"][0]["bbox"])
                       for r, p in zip(truth["pages"], pred["pages"]) if p["tables"]})
        out.setdefault("ious", {})[fam] = ious
        if "iou" in c1:
            ledger.check("R2.4", f"{fam}/001-iou", ious == [c1["iou"]], ious, [c1["iou"]])
        cb, ca = before["counts"], after["counts"]
        ledger.check("R2.4", f"{fam}/001-edits-extras-unflagged",
                     ((cb["edits"], cb["reference_chars"]), (ca["edits"], ca["reference_chars"]), cb["extra_cells"], ca["extra_cells"],
                      (cb["unflagged_critical_errors"], cb["critical_values"]), (ca["unflagged_critical_errors"], ca["critical_values"]),
                      cb["flagged_critical"] + ca["flagged_critical"]) ==
                     ((c1["edits"], c1["ref_chars"]), (c1["edits"], c1["ref_chars"]), c1["extra_before"], c1["extra_after"],
                      c1["unflagged"], c1["unflagged"], c1["flagged"]), None, None)
        keys = ("family", "source_sha256", "packet_complete", "expected_pages", "output_pages", "observed_order",
                "faults", "extra_page_outputs")
        ledger.check("R2.5", f"{fam}/packet-invariant", rc.sha256(canon({k: before[k] for k in keys})) == pj["packet_invariant_sha256"]
                     and canon({k: before[k] for k in keys}) == canon({k: after[k] for k in keys}), None, None)
        page_ok = True
        for b, a, rec in zip(before["pages"], after["pages"], pj["pages"], strict=True):
            ek = {k: b[k] for k in ("page", "state", "reference_chars", "edit_distance")}
            prose = [c for c in b["critical"] if "/line/" in c["at"]]
            page_ok &= (rc.sha256(canon(ek)) == rec["edits_sha256"] and rc.sha256(canon(b["lines"])) == rec["lines_sha256"]
                        and rc.sha256(canon(prose)) == rec["critical_lines_sha256"]
                        and (b["extra_cells"], a["extra_cells"]) == (rec["extra_cells_before"], rec["extra_cells_after"])
                        and all(rec[k] == ek[k] for k in ek))
        ledger.check("R2.6", f"{fam}/per-page-invariant-hashes", page_ok, None, None)
        ledger.check("R2.7", f"{fam}/counts", (before["counts"], after["counts"]) == (pj["counts_before"], pj["counts_after"]), None, None)
        adm = bj["admission"]["files"]
        bad = [k for k, v in adm.items() if rc.sha256((paths["root"] / k).read_bytes()) != v]
        ledger.check("R2.8", f"{fam}/author-admission-hashes-vs-reviewer-copy", not bad and len(adm) == {"H": 20, "A": 188}[fam],
                     bad, [], f"{len(adm)} files")
        crit = {c["at"]: c for p in before["pages"] for c in p["critical"]}
        ex_ok = all(crit[at]["expected"] == e["expected"] and crit[at]["observed"] == e["observed"] and
                    crit[at]["flagged"] == e["flagged"] and not crit[at]["correct"] for at, e in bj["checked_examples"].items())
        ledger.check("R2.9", f"{fam}/published-examples", ex_ok, len(bj["checked_examples"]), None)
        out[fam] = dict(examples=len(bj["checked_examples"]), admission_files=len(adm))
    con = gitj(PAIR_EVIDENCE, f"{PAIR}/evidence/constructed.json")
    ledger.check("R2.10", "constructed/gain-loss", (con["gains"], con["losses"], con["net"]) == (1, 1, 0), None, None)
    return out


def row_compare(ledger, data, mine_dir, receipt, scorer):
    attribution = rc.load(scratch(mine_dir, receipt, "attribution-d9c5e7f/attribution.json"))
    paired = rc.load(scratch(mine_dir, receipt, "paired-94eba5b/paired.json"))
    disagreements, report = [], {}
    for fam in "HA":
        paths = rc.family_paths(data, fam)
        truth = rc.load(paths["truth"])
        pred = json.loads(paths["prediction"].read_bytes())
        pair_rows = {r["at"]: r for r in jsonl(gitb(PAIR_EVIDENCE, f"{PAIR}/evidence/{fam}/cells.jsonl"))}
        word_rows = {r["at"]: r for r in jsonl(gitb(WORDS_COVERAGE, f"{WORDS}/coverage/locations-{fam}.jsonl"))}
        word_pages = {r["page"]: r for r in jsonl(gitb(WORDS_COVERAGE, f"{WORDS}/coverage/pages-{fam}.jsonl"))}
        my_cells = {c["at"]: c for c in attribution[fam]["cells"]}
        my_lines = {l["at"]: l for l in attribution[fam]["lines"]}
        my_acc = {c["at"]: c for c in paired[f"paired_{fam}"]["cells"]}
        ledger.check("R3.0", f"{fam}/populations", set(pair_rows) == set(my_cells) == {k for k in word_rows if "/table/" in k}
                     and set(my_lines) == {k for k in word_rows if "/line/" in k}, None, None)
        spans_total = 0
        for pi, ref in enumerate(truth["pages"]):
            num = ref["page"]
            raw, page, window, words, membership = ra.page_inputs(paths, num)
            spans_total += len(words)
            wp = word_pages[num]
            recon = [dict(text=w["text"], px=w["pixel_bbox"], box=w["projected_bbox"], line=w["raw_line"], word=w["raw_word"])
                     for w in wp["reconstructed_spans"]]
            mine_recon = [dict(text=w["text"], px=w["px"], box=w["bbox"], line=w["line"], word=w["word"]) for w in words]
            if recon != mine_recon:
                disagreements.append(dict(scope=f"{fam}/p{num}/reconstructed_spans"))
            if [g["emitted"] for g in wp["original_grids"]] != page["tables"] or wp["emitted_page_text"] != page["text"]:
                disagreements.append(dict(scope=f"{fam}/p{num}/grids-or-text"))
            owners = ra_owner_map(scorer, ref, page)
            if [w["reference_owner"] for w in wp["reconstructed_spans"]] != owners:
                disagreements.append(dict(scope=f"{fam}/p{num}/reference_owner", theirs=[w["reference_owner"] for w in wp["reconstructed_spans"]], mine=owners))
            cell_owner = rc.scorer_span_cells(scorer, ref, page, truth["source_sha256"])
            idx = 0
            for ti, table in enumerate(ref["tables"]):
                for ri, row in enumerate(table["rows"]):
                    for ci, cell in enumerate(row):
                        at = f"page/{num}/table/{ti+1}/row/{ri+1}/col/{ci+1}"
                        p, w, m, acc = pair_rows[at], word_rows[at], my_cells[at], my_acc[at]
                        region = cell["bbox"]
                        inter = [k for k, x in enumerate(words) if ra.overlap(x["bbox"], region) > 0]
                        cent = [k for k, x in enumerate(words) if ra.centred(x["bbox"], region)]
                        owned = cell_owner.get((ti, ri, ci), [])
                        join_order = sorted(owned, key=lambda k: (page["spans"][k]["bbox"][0], page["spans"][k]["bbox"][1]))
                        grid_ptr = acc["before"]["grid_pointer"][0]["pointer"] if acc["before"]["grid_pointer"] else None
                        grid_rel = grid_ptr.split(f"/pages/{pi}", 1)[1] if grid_ptr else None
                        gtab = int(grid_rel.split("/")[2]) if grid_rel else None
                        iou = scorer.iou(table["bbox"], page["tables"][gtab]["bbox"]) if gtab is not None else None
                        gmembers = [k for k, mem in membership.items() if gtab is not None and [gtab, ri, ci] in mem]
                        gmembers = sorted(gmembers, key=lambda k: (words[k]["line"], words[k]["bbox"][0]))
                        checks = {
                            "pair.expected/critical": (p["expected"], p["critical"]) == (m["expected"], cell["critical"]),
                            "pair.transition": p["transition"] == m["klass"] == acc["klass"] == w["outcome"],
                            "pair.before": all(p["before"][k] == m["before"][k] for k in ("observed", "correct", "flagged")),
                            "pair.after": all(p["after"][k] == m["after"][k] for k in ("observed", "correct", "flagged")),
                            "pair.mode": (p["before"]["mode"], p["after"]["mode"]) == ("matched_grid" if m["before"]["mode"] == "grid" else "?", "reference_box_fallback"),
                            "pair.before.selected": p["before"]["selected"] == ([grid_rel] if grid_rel else []),
                            "pair.after.selected": p["after"]["selected"] == [f"/spans/{k}" for k in join_order],
                            "pair.iou": p["before"]["matched_iou"] == iou and p["before"]["best_candidate_iou"] == iou,
                            "pair.pointers": (p["reference_pointer"], p["score_pointer"], p["reference_bbox"]) ==
                                             (f"/pages/{pi}/tables/{ti}/rows/{ri}/{ci}", f"/pages/{pi}/cells/{idx}", region),
                            "pair.bindings": (p["truth_sha256"], p["archive_page_sha256"]) ==
                                             (rc.sha256(paths["truth"].read_bytes()), rc.sha256(rc.page_file(paths, "page", num).read_bytes())),
                            "words.values": all(w[f"{pre}_{k}"] == m[arm][k] for pre, arm in (("original", "before"), ("without_grid", "after"))
                                                for k in ("observed", "correct", "flagged")),
                            "words.mode": w["original_mode"] == "matched_grid" and w["matched_predicted_table"] == gtab and w["matched_iou"] == iou,
                            "words.geometry": (set(w["reference_intersecting_or_line_eligible_spans"]), set(w["reference_center_spans"]),
                                               w["reference_eligible_spans_input_order"], w["reference_spans_join_order"]) ==
                                              (set(inter), set(cent), owned, join_order),
                            "words.grid_members": w["original_grid_spans"] == gmembers,
                            "words.critical": w["critical_reference"] == cell["critical"],
                            "words.stage": (m["earliest_stage"], m["text_effect"]) in WORD_MAP[w["first_supported_divergence"]],
                        }
                        if w["first_supported_divergence"] == "empty_reference_loses_exact_match_under_no_span_null":
                            checks["words.empty_loss"] = m["printed_empty"] and m["klass"] == "loss"
                        if w["first_supported_divergence"] == "no_scored_divergence":
                            checks["words.no_divergence"] = m["klass"] == "unchanged_right"
                        tok = w["anchored_token"]
                        if not m["before"]["correct"] and m["text_effect"] != "empty_value":
                            their_split = bool(tok and tok["split_in_raw_export"] and not tok["nonspace_characters_match"])
                            checks["split.char+split"] = their_split == (m["text_effect"] == "character_and_split")
                            checks["split.whitespace"] = bool(tok and tok["nonspace_characters_match"]) == (m["text_effect"] == "whitespace_only")
                        for name, ok in checks.items():
                            if not ok:
                                disagreements.append(dict(scope=f"{fam}/{at}", check=name))
                        idx += 1
            assigned = {}
            for k, s in enumerate(page["spans"]):
                if any(k in v for v in cell_owner.values()):
                    continue
                elig = [j for j, ln in enumerate(ref["lines"]) if scorer.on_line(s["bbox"], ln["bbox"])]
                if elig:
                    c = lambda bx: (bx[1] + bx[3]) / 2
                    assigned.setdefault(min(elig, key=lambda j: abs(c(ref["lines"][j]["bbox"]) - c(s["bbox"]))), []).append(k)
            for li, line in enumerate(ref["lines"]):
                at = f"page/{num}/line/{li+1}"
                w, m = word_rows[at], my_lines[at]
                owned = assigned.get(li, [])
                join_order = sorted(owned, key=lambda k: (page["spans"][k]["bbox"][0], page["spans"][k]["bbox"][1]))
                eligible = [k for k, s in enumerate(page["spans"]) if scorer.on_line(s["bbox"], line["bbox"])]
                checks = {
                    "words.line.values": (w["original_observed"], w["original_correct"], w["without_grid_observed"],
                                          w["without_grid_correct"]) == (m["observed"], m["correct"], m["observed"], m["correct"])
                                         and m["after_identical"],
                    "words.line.flags": (w["original_flagged"], w["without_grid_flagged"]) == (False, False),
                    "words.line.spans": (w["reference_eligible_spans_input_order"], w["reference_spans_join_order"]) == (owned, join_order),
                    "words.line.eligible": w["reference_intersecting_or_line_eligible_spans"] == eligible,
                    "words.line.raw_lines": w["selected_raw_lines"] == sorted({words[k]["line"] for k in owned}),
                    "words.line.critical": (w["original_critical_verdict"]["correct"] if w["original_critical_verdict"] else None) ==
                                           m["critical_correct"],
                    "words.line.stage": (m["earliest_stage"], m["text_effect"]) in WORD_MAP[w["first_supported_divergence"]],
                }
                tok = w["anchored_token"]
                if not m["correct"]:
                    their_split = bool(tok and tok["split_in_raw_export"] and not tok["nonspace_characters_match"])
                    checks["split.line.char+split"] = their_split == (m["text_effect"] == "character_and_split")
                    checks["split.line.whitespace"] = bool(tok and tok["nonspace_characters_match"]) == (m["text_effect"] == "whitespace_only")
                for name, ok in checks.items():
                    if not ok:
                        disagreements.append(dict(scope=f"{fam}/{at}", check=name, theirs=w["first_supported_divergence"],
                                                  token=tok, mine=[m["earliest_stage"], m["text_effect"]],
                                                  expected=m["expected"], observed=m["observed"]))
        report[fam] = dict(spans=spans_total, cells=len(my_cells), lines=len(my_lines))
        ledger.check("R3.1", f"{fam}/span-count-claim", spans_total == CLAIMS["002"]["spans"][fam], spans_total, CLAIMS["002"]["spans"][fam])
    ledger.check("R3.2", "row-level-disagreements", not disagreements, len(disagreements), 0)
    return report, disagreements


def ra_owner_map(scorer, ref, page):
    """Reference owner label per span in the word tracer's vocabulary, derived from frozen scorer predicates."""
    owners = []
    for s in page["spans"]:
        box = s["bbox"]
        if not scorer.valid_box(box, ref["width"], ref["height"]):
            owners.append(None)
            continue
        owner = None
        for ti, t in enumerate(ref["tables"]):
            for ri, row in enumerate(t["rows"]):
                for ci, c in enumerate(row):
                    if owner is None and scorer.in_cell(box, c["bbox"]):
                        owner = f"table/{ti+1}/row/{ri+1}/col/{ci+1}"
        if owner is None:
            elig = [j for j, ln in enumerate(ref["lines"]) if scorer.on_line(box, ln["bbox"])]
            if elig:
                c = lambda bx: (bx[1] + bx[3]) / 2
                owner = f"line/{min(elig, key=lambda j: abs(c(ref['lines'][j]['bbox']) - c(box))) + 1}"
        owners.append(owner)
    return owners


def count_audit(ledger, mine_dir, receipt):
    attribution = rc.load(scratch(mine_dir, receipt, "attribution-d9c5e7f/attribution.json"))
    summary = gitj(WORDS_COVERAGE, f"{WORDS}/coverage/summary.json")
    recon = gitj(COORDINATOR, "docs/coordination/WP-0018/reconciliation.json")
    out = {}
    for fam in "HA":
        cells, lines = attribution[fam]["cells"], attribution[fam]["lines"]
        t = attribution[fam]["tallies"]
        pj = gitj(PAIR_EVIDENCE, f"{PAIR}/evidence/{fam}/pair.json")
        pr = jsonl(gitb(PAIR_EVIDENCE, f"{PAIR}/evidence/{fam}/cells.jsonl"))
        wr = jsonl(gitb(WORDS_COVERAGE, f"{WORDS}/coverage/locations-{fam}.jsonl"))
        # Pair author's summary re-derived from their own rows.
        tr = Counter(r["transition"] for r in pr)
        derived = dict(rows=len(pr), gain=tr["gain"], loss=tr["loss"], unchanged_wrong=tr["unchanged_wrong"],
                       unchanged_right=tr["unchanged_right"], unavailable_score_rows=0,
                       wrong_both_observation_changed=sum(r["transition"] == "unchanged_wrong" and r["before"]["observed"] != r["after"]["observed"] for r in pr),
                       null_observed_before=sum(r["before"]["observed"] is None for r in pr),
                       null_observed_after=sum(r["after"]["observed"] is None for r in pr),
                       flagged_before=sum(r["before"]["flagged"] for r in pr), flagged_after=sum(r["after"]["flagged"] for r in pr),
                       flag_changes=sum(r["before"]["flagged"] != r["after"]["flagged"] for r in pr))
        ledger.check("R4.1", f"{fam}/pair-summary-from-rows", derived == pj["transitions"], derived, pj["transitions"])
        ledger.check("R4.1", f"{fam}/pair-unavailable-is-constant", True, None, None,
                     "pair paired.py summarize() hard-codes unavailable_score_rows=0; all rows have scores here")
        # Words summary re-derived from their own rows.
        for kind, token in (("cells", "/table/"), ("prose", "/line/")):
            sub = [r for r in wr if token in r["at"]]
            wrong = [r for r in sub if r["outcome"] in ("unchanged_wrong", "gain")]
            fd = dict(sorted(Counter(r["first_supported_divergence"] for r in wrong).items()))
            sp = sum(1 for r in wrong if r["anchored_token"] and r["anchored_token"]["split_in_raw_export"]
                     and not r["anchored_token"]["nonspace_characters_match"])
            s = summary[fam][kind]
            ledger.check("R4.2", f"{fam}/words-{kind}-summary-from-rows",
                         (len(wrong), fd, sp) == (s["originally_wrong"], s["original_wrong_first_divergence"],
                                                  s["original_wrong_split_tokens_with_nonspace_difference"]), [len(wrong), fd, sp], None)
        # Reviewer tallies vs words summary and reports.
        mine_cells = Counter((c["earliest_stage"], c["text_effect"]) for c in cells if not c["before"]["correct"])
        mine_lines = Counter((l["earliest_stage"], l["text_effect"]) for l in lines if not l["correct"])
        c2 = CLAIMS["002"][fam]
        ledger.check("R4.3", f"{fam}/002-cells", (t["cells_wrong_before"], sum(v for (s, _), v in mine_cells.items() if s == "winrt_text"),
                     mine_cells.get(("no_intersecting_word", "empty_value"), 0), t["printed_empty"]["losses"]) ==
                     (c2["cells_wrong"], c2["cells_raw"], c2["cells_none"], c2["empty_losses"]), {f"{a}|{b}": v for (a, b), v in mine_cells.items()}, c2)
        ledger.check("R4.3", f"{fam}/002-prose", (t["lines_wrong"], sum(v for (s, _), v in mine_lines.items() if s == "winrt_text")) ==
                     (c2["prose_wrong"], c2["prose_raw"]), {f"{a}|{b}": v for (a, b), v in mine_lines.items()}, c2)
        if fam == "A":
            single = sum(1 for c in cells if not c["before"]["correct"] and c["text_effect"] == "character_only")
            ledger.check("R4.3", "A/002-split-detail",
                         (single, mine_cells[("winrt_text", "character_and_split")], mine_cells[("winrt_text", "whitespace_only")],
                          mine_lines[("winrt_text", "character_only")] + mine_lines[("winrt_text", "character_and_split")],
                          mine_lines[("winrt_text", "character_and_split")], mine_lines[("winrt_text", "whitespace_only")]) ==
                         (c2["cell_single_word_char"], c2["cell_line_char_split"], c2["cell_whitespace"], c2["prose_char"],
                          c2["prose_char_split"], c2["prose_whitespace"]), None, None)
        c1 = CLAIMS["001"][fam]
        crit_cells = [c for c in cells if c["critical"]]
        crit_lines = [l for l in lines if l["critical_token"]]
        got = dict(correct_before=sum(c["before"]["correct"] for c in cells), correct_after=sum(c["after"]["correct"] for c in cells),
                   gain=t["gains"], loss=t["cell_classes"].get("loss", 0), unchanged_wrong=t["cell_classes"].get("unchanged_wrong", 0),
                   unchanged_right=t["cell_classes"].get("unchanged_right", 0),
                   already_fallback=sum(c["before"]["mode"] != "grid" for c in cells),
                   prose_crit_wrong=(sum(l["critical_correct"] is False for l in crit_lines), len(crit_lines)),
                   table_crit_wrong=(sum(not c["before"]["correct"] for c in crit_cells), len(crit_cells)),
                   lines=(sum(l["correct"] for l in lines), len(lines)),
                   flagged=t["flagged_any"])
        want = {k: c1[k] for k in got}
        ledger.check("R4.4", f"{fam}/001-claims", got == want, got, want)
        ledger.check("R4.4", f"{fam}/001-critical-loss-free", all(not c["critical"] for c in cells if c["klass"] == "loss"), None, None)
        if fam == "A":
            changed_wrong = [c["at"] for c in cells if c["klass"] == "unchanged_wrong" and c["before"]["observed"] != c["after"]["observed"]]
            ledger.check("R4.4", "A/001-missing-both", changed_wrong == c1["missing_both"], changed_wrong, c1["missing_both"])
        # Coordinator reconciliation.
        rf = recon["families"][fam]
        losses = [c["at"] for c in cells if c["klass"] == "loss"]
        changed_wrong = [c["at"] for c in cells if c["klass"] == "unchanged_wrong" and c["before"]["observed"] != c["after"]["observed"]]
        by_row, by_half = {}, {}
        for c in cells:
            parts = c["at"].split("/")
            half = "first" if int(parts[1]) <= (2 if fam == "H" else 30) else "second"
            for g, name in ((by_half, half), (by_row, parts[5])):
                x = g.setdefault(name, {"reference": 0, "original_wrong": 0})
                x["reference"] += 1
                x["original_wrong"] += int(not c["before"]["correct"])
        ledger.check("R4.5", f"{fam}/coordinator-reconciliation",
                     (sorted(rf["blankToAbsentLosses"]), rf["changedObservationStillWrong"], rf["positionByDocumentHalf"], rf["positionByTableRow"],
                      rf["transitions"]) == (sorted(losses), changed_wrong, by_half, by_row, pj["transitions"]), None, None)
        out[fam] = dict(cell_stage_effect={f"{k[0]}|{k[1]}": v for k, v in mine_cells.items()},
                        line_stage_effect={f"{k[0]}|{k[1]}": v for k, v in mine_lines.items()})
    return out


def witnesses(ledger, mine_dir):
    w = json.loads(gitb(WORDS_WITNESS, f"{WORDS}/witnesses.json"))
    mine = {}
    for wid in ("W1", "W2", "W3", "W4"):
        mine[wid] = rc.load(Path(rc.HERE) / "evidence" / "witnesses-ecbeb8b" / f"witness-{wid}.json")
    order = [("H", "page/2/table/1/row/2/col/1", "W1"), ("A", "page/60/table/1/row/2/col/2", "W2"),
             ("H", "page/1/line/2", "W3"), ("H", "page/2/line/2", "W4")]
    for (fam, at, wid), loc in zip(order, w["locations"], strict=True):
        m = mine[wid]
        my_spans = [int(x["span_pointer"].split("/")[-1]) for x in m["words"]]
        my_lines = sorted({x["winrt_line_ordinal"] for x in m["words"]})
        my_obs = m["scored_selection"]["record"]["observed"]
        ok = (loc["packet"], loc["at"]) == (fam, at) and loc["reference_spans_join_order"] == my_spans and \
             loc["selected_raw_lines"] == my_lines and loc["original_observed"] == my_obs == loc["without_grid_observed"] and \
             loc["truth_pointer"] == m["reference"]["truth_pointer"]
        if "/table/" in at:
            ok &= loc["matched_iou"] == m["table_match"]["matched"][0]["iou"] and loc["original_grid_spans"] == m["grid"][0]["adapter_words_in_cell"]
        page = w["pages"][f"{fam}-{int(at.split('/')[1]):03d}"]
        for x in m["words"]:
            k = int(x["span_pointer"].split("/")[-1])
            r = page["reconstructed_spans"][k]
            ok &= (r["pixel_bbox"], r["projected_bbox"], r["raw_line"], r["raw_word"], r["text"]) == \
                  (x["px_bbox"], x["projected"], x["winrt_line_ordinal"], x["winrt_word_ordinal"], x["text"])
        ledger.check("R5.1", f"witness/{wid}", ok, None, None, "author witness equals the reviewer's frozen trace")


def supplementary(ledger, data):
    """WP-0015 numeric-token checks: historical helper bytes at ce4206f and an independent re-implementation."""
    analyze_src = gitb(HELPER_COMMIT, "docs/reviews/WP-0015/analyze.py")
    summary_src = gitb(HELPER_COMMIT, "docs/reviews/WP-0015/scored_summary.py")
    mod = types.ModuleType("wp0015_analyze_historical")
    mod.__file__ = str(rc.REPO / "docs" / "reviews" / "WP-0015" / "analyze.py")  # path constants only; bytes come from Git
    exec(compile(analyze_src, f"{HELPER_COMMIT}:docs/reviews/WP-0015/analyze.py", "exec"), mod.__dict__)
    tree = ast.parse(summary_src)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "diag")
    ns = dict(diagnostics=mod.diagnostics)
    exec(compile(ast.Module(body=[node], type_ignores=[]), f"{HELPER_COMMIT}:scored_summary.py#diag", "exec"), ns)
    published = rc.load(Path(data) / "inputs" / "control" / "scored-H-A.json")
    num_re = re.compile(r"[+-]?[\w]+(?:[.,-][\w]+)*")

    def toks(text):
        return Counter(t for t in num_re.findall(" ".join(unicodedata.normalize("NFC", text).split())) if any(c.isdigit() for c in t))
    out = {}
    for fam, spec in rc.FAMILIES.items():
        paths = rc.family_paths(data, fam)
        truth, pred = rc.load(paths["truth"]), json.loads(paths["prediction"].read_bytes())
        hist = ns["diag"](truth, pred)
        want = published[fam]["runs"][spec["run"]]["windows"]["checks"]
        pages = {p["page"]: p for p in pred["pages"]}
        missing = sum(sum((toks(r["text"]) - toks(pages[r["page"]]["text"])).values()) for r in truth["pages"])
        surplus = sum(sum((toks(pages[r["page"]]["text"]) - toks(r["text"])).values()) for r in truth["pages"])
        stripped = {**pred, "pages": [{**p, "tables": []} for p in pred["pages"]]}
        ledger.check("S1", f"{fam}/historical-helper", hist == want, hist, want)
        ledger.check("S2", f"{fam}/independent-missing-surplus", (missing, surplus) == (want["missing_numeric_tokens"], want["surplus_numeric_tokens"]),
                     [missing, surplus], [want["missing_numeric_tokens"], want["surplus_numeric_tokens"]])
        ledger.check("S3", f"{fam}/archive-pins-supplementary", missing == rc.load(Path(data) / "inputs" / "control" / "archive-pins.json")["families"][fam]["published_windows"]["missing_numeric_tokens_supplementary"], missing, None)
        ledger.check("S4", f"{fam}/tables-removal-invariant", ns["diag"](truth, stripped) == hist, None, None,
                     "page-text numeric checks do not read tables")
        out[fam] = dict(historical=hist, independent=dict(missing=missing, surplus=surplus))
    out["helper"] = dict(commit=HELPER_COMMIT, analyze_sha256=rc.sha256(analyze_src), scored_summary_sha256=rc.sha256(summary_src))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=str(rc.DEFAULT_DATA))
    ap.add_argument("--scratch", default=str(rc.DEFAULT_DATA / "out"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--fresh", action="store_true", help="verify a new reproduction run of paired/attribution outputs")
    args = ap.parse_args()
    global FRESH
    FRESH = args.fresh
    out = rc.fresh_dir(args.out)
    env = rc.environment()
    env["compare_sha256"] = rc.sha256(Path(__file__).read_bytes())
    env["fresh"] = FRESH
    receipt = rc.load(RECEIPT)
    scorer = rc.load_scorer(Path(args.data) / "inputs" / "control" / "score.py")
    ra.norm = scorer.norm
    ledger = rc.Ledger()
    result = dict(kind="WP-0018/003 reviewer reconciliation with author objects", environment=env,
                  receipt_sha256=rc.sha256(RECEIPT.read_bytes()),
                  author_objects=dict(pair_source=PAIR_SOURCE, pair_evidence=PAIR_EVIDENCE, pair_report=PAIR_REPORT,
                                      words_source=WORDS_SOURCE, words_witness=WORDS_WITNESS, words_coverage=WORDS_COVERAGE,
                                      words_report=WORDS_REPORT, coordinator=COORDINATOR))
    result["identity"] = identity(ledger)
    result["pair_receipts"] = pair_receipts(ledger, args.data, args.scratch, receipt, scorer)
    result["rows"], result["disagreements"] = row_compare(ledger, args.data, args.scratch, receipt, scorer)
    result["counts"] = count_audit(ledger, args.scratch, receipt)
    witnesses(ledger, args.scratch)
    result["supplementary"] = supplementary(ledger, args.data)
    result["checks"] = ledger.checks
    result["summary"] = ledger.summary()
    result["ended_utc"] = rc.utc()
    digest = rc.dump(out / "compare.json", result)
    print(json.dumps(dict(out=str(out / "compare.json"), sha256=digest, disagreements=len(result["disagreements"]),
                          **result["summary"]), indent=1))
    return 0 if not result["summary"]["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
