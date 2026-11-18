"""WP-0016 G0 publication cross-check (eld-rd-reviewer, publication-only continuation).

CPU only. Reads the frozen stage-2 output directory written by the original scoring session, the committed
stage-1/inventory evidence on this branch and pinned Git objects. It runs no model, opens no truth file,
runs no scorer and writes only the --out JSON. Every transition, four-way table, gate decision, timing
pair, recovery rate and malformed-header count is recomputed here by code written independently of
score_all.py, from the per-path rows that the frozen score.py emitted, and compared with the frozen summary.

python -I -B docs/reviews/WP-0016/publication_check.py --stage2 <dir> --out <json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXPECT_SUMMARY = "b5d711606b1a6e93ac26a5b69a1643c1565cf9178699c8dae04a5203e7a506bf"
MIRROR = ("c9bfa545069496bc7ab863aabeb7bf3e257b3c21", "docs/coordination/WP-0016/escrow-stage2.json")
QUALITY = ("2a5c0f0c83998e2ec7822115c80469acf553901e", "docs/coordination/WP-0016/g0-quality-return.json")
RELEASE = ("1c19444a4ea3aef4c766729780a2ca1637db934a", "docs/coordination/WP-0016/g0-scoring-release.json")
HWRETURN = ("07cbb881f214e32b4b2e6bc42da7572218ce63fd", "docs/coordination/WP-0016/g0-return.json")
INVENTORY = ("6f3273278215fd0ced7555a84e1e692f144b5b69", "docs/reviews/WP-0016/evidence/G0-blind-inventory.json")
STAGE1 = ("7b70d674457a23a9254756c958db87d68a81da23", "docs/reviews/WP-0016/evidence/G0-stage1.json")
SCORER = ("61bec47689dcdf272a525185013f2dce6335fa24", "docs/evaluation/WP-0015/score.py")
RULE = ("0186467670074761a777602d77b53deff3451300", "docs/research/WP-0015/astra/sensitivity-title-level/rescore.py")
TOOLS_FREEZE = "df07eea"
KEYS_RELEASED = "1c19444a4ea3aef4c766729780a2ca1637db934a"
ARMS = ("native-ab", "carbon-ab", "native-ba", "carbon-ba")
CEILING_MIB = 10000
CER_MAX, CELL_MIN = 0.01, -0.02

results: list[dict] = []


def check(ok, name, **detail):
    results.append(dict(check=name, ok=bool(ok), **detail))
    return bool(ok)


def git(*args) -> bytes:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True).stdout


def blob(commit, path) -> bytes:
    return git("show", f"{commit}:{path}")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def ancestor(a, b) -> bool:
    return subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", a, b]).returncode == 0


def arm_counts(s):
    """Recompute per-arm totals from per-page rows (not from s['counts'])."""
    pages = s["pages"]
    crit = [c for p in pages for c in p.get("critical", [])]
    cells = [c for p in pages for c in p.get("cells", [])]
    lines = [c for p in pages for c in p.get("lines", [])]
    ref = sum(p["reference_chars"] for p in pages)
    edits = sum(p["edit_distance"] for p in pages)
    extra = sum(p.get("extra_cells", 0) for p in pages)
    ok_cells = sum(bool(c["correct"]) for c in cells)
    return dict(edits=edits, reference_chars=ref, cer=edits / ref,
                correct_cells=ok_cells, reference_cells=len(cells), extra_cells=extra,
                cell_accuracy=ok_cells / (len(cells) + extra),
                correct_lines=sum(bool(c["correct"]) for c in lines), reference_lines=len(lines),
                critical_values=len(crit), critical_errors=sum(not c["correct"] for c in crit),
                unflagged_critical_errors=sum((not c["correct"]) and not c.get("flagged") for c in crit))


def rows(s, kind):
    return {c["at"]: c for p in s["pages"] for c in p.get(kind, [])}


def four_way(base, trial):
    b, t = base, trial
    out = dict(CC=0, CW=0, WC=0, WW=0)
    for at in b:
        out[("C" if b[at]["correct"] else "W") + ("C" if t[at]["correct"] else "W")] += 1
    return out


def classify(base_s, trial_s):
    b, t = rows(base_s, "critical"), rows(trial_s, "critical")
    k = dict(stable_correct=0, regress=0, abstain=0, repair=0, persist_same=0, persist_changed=0)
    new, per = [], {}
    for at in sorted(b):
        x, y = b[at], t.get(at)
        if y is None:
            per[at] = "unmatched"
            continue
        if x["correct"] and y["correct"]:
            c = "stable_correct"
        elif x["correct"]:
            c = "abstain" if y["observed"] is None else "regress"
        elif y["correct"]:
            c = "repair"
        else:
            same = (x["observed"], bool(x.get("flagged"))) == (y["observed"], bool(y.get("flagged")))
            c = "persist_same" if same else "persist_changed"
        k[c] += 1
        per[at] = c
        if (not y["correct"]) and not y.get("flagged") and (x["correct"] or x.get("flagged")):
            new.append(at)
    return dict(paths=len(b), matched_paths=set(b) == set(t), counts=k,
                four_way=dict(CC=k["stable_correct"], CW=k["regress"] + k["abstain"], WC=k["repair"],
                              WW=k["persist_same"] + k["persist_changed"]),
                net_recovery=k["repair"] - k["regress"] - k["abstain"],
                new_unflagged=len(new), new_unflagged_paths=new), per


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage2", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    d2 = a.stage2
    out: dict = dict(tool="publication_check.py", reviewer="eld-rd-reviewer",
                     scope="CPU only; no model, no truth file opened, no scorer executed",
                     tool_sha256=sha(Path(__file__).read_bytes()), head=git("rev-parse", "HEAD").decode().strip())

    # ---------- 1. provenance of the frozen summary ----------
    summary_b = (d2 / "summary.json").read_bytes()
    mirror_b = blob(*MIRROR)
    check(sha(summary_b) == EXPECT_SUMMARY, "summary.json sha256 equals the bound value", sha256=sha(summary_b))
    check(mirror_b == summary_b, "coordinator mirror c9bfa54 is byte-identical to the original summary.json",
          mirror_sha256=sha(mirror_b), bytes=len(mirror_b))
    S = json.loads(summary_b)
    check(S["failures"] == [] and S["checks_run"] == 145 and S["stage"] == 2, "summary: stage 2, 145 checks, 0 failures")
    files = json.loads((d2 / "files.json").read_bytes())
    bad = [k for k, v in files.items() if sha((d2 / k).read_bytes()) != v]
    check(not bad, "every file listed in files.json matches its sha256", listed=len(files), mismatched=bad)

    stage1_b = blob(*STAGE1)
    inv_b = blob(*INVENTORY)
    check(sha(stage1_b) == S["stage1_sha256"], "summary.stage1_sha256 = committed G0-stage1.json at 7b70d67",
          sha256=sha(stage1_b))
    check(sha(inv_b) == S["inventory_sha256"], "summary.inventory_sha256 = blind inventory committed at 6f32732",
          sha256=sha(inv_b))
    head_inv = (ROOT / INVENTORY[1]).read_bytes()
    head_s1 = (ROOT / STAGE1[1]).read_bytes()
    check(head_inv == inv_b and head_s1 == stage1_b, "working-tree inventory and stage-1 equal their pinned blobs")
    check(sha(blob(*SCORER)) == S["scorer_sha256"], "scorer sha256 = score.py at 61bec47", sha256=S["scorer_sha256"])
    check(sha(blob(*RULE)) == S["title_rule"]["sha256"] and S["title_rule"]["commit"] == RULE[0],
          "title rule sha256 = rescore.py at 0186467")
    for f in ("score_all.py", "title_adapt.py", "common.py", "grammar.py", "verify.py"):
        p = f"docs/reviews/WP-0016/{f}"
        check(blob(TOOLS_FREEZE, p) == (ROOT / p).read_bytes(), f"{f} unchanged since tool freeze df07eea")
    check(ancestor(TOOLS_FREEZE, INVENTORY[0]) and ancestor(INVENTORY[0], KEYS_RELEASED),
          "order: tool freeze df07eea -> blind inventory 6f32732 -> key release 1c19444")

    # ---------- 2. prediction binding ----------
    S1 = json.loads(stage1_b)
    inv_text = inv_b.decode("utf-8")
    pred = {}
    for run, order in (("g0-ab", "ab"), ("g0-ba", "ba")):
        r = S1["runs"][run]
        check(r["source"] == r["head"] == "c7b2ee3663317e42a0e9bdd7ff9e17f16747d2cf", f"{run}: source/head = c7b2ee3")
        for mode, arm in (("native", "native"), ("carbon_bf16", "carbon")):
            for fam in ("H", "A"):
                m = r["arms"][mode]["measured"][fam]
                pred[fam, f"{arm}-{order}"] = m
                check(m["prediction_sha256"] in inv_text,
                      f"{run}/{mode}/{fam}: frozen prediction sha256 present in blind inventory",
                      sha256=m["prediction_sha256"])
    determinism = {}
    for fam in ("H", "A"):
        for arm in ("native", "carbon"):
            same = pred[fam, f"{arm}-ab"]["prediction_sha256"] == pred[fam, f"{arm}-ba"]["prediction_sha256"]
            determinism[f"{fam}:{arm}"] = dict(identical_ab_ba=same, sha256=pred[fam, f"{arm}-ab"]["prediction_sha256"])
        determinism[f"{fam}:native_vs_carbon_identical"] = (
            pred[fam, "native-ab"]["prediction_sha256"] == pred[fam, "carbon-ab"]["prediction_sha256"])
    out["prediction_determinism"] = determinism
    title_receipts = {}
    for fam in ("H", "A"):
        for arm in ARMS:
            rc = json.loads((d2 / "title" / f"{fam}-{arm}.receipt.json").read_bytes())
            pb = (d2 / "title" / f"{fam}-{arm}.prediction.json").read_bytes()
            check(rc["source_prediction_sha256"] == pred[fam, arm]["prediction_sha256"],
                  f"title {fam}-{arm}: receipt source = stage-1 frozen prediction")
            check(rc["corrected_prediction_sha256"] == sha(pb), f"title {fam}-{arm}: corrected prediction file hash")
            title_receipts[f"{fam}:{arm}"] = rc["recognized_headers"]
    out["title_recognized_headers"] = title_receipts
    rel = json.loads(blob(*RELEASE))
    for fam in ("H", "A"):
        w = S["windows"][fam]
        check(w["primary"]["prediction_sha256"] == w["sensitivity"]["prediction_sha256"]
              == rel["keys_and_reference_predictions"][fam]["windows-ab"]["sha256"],
              f"{fam}: stored Windows prediction sha256 equals the key-release record")

    # ---------- 3. per-arm counts recomputed from rows ----------
    scores, per_arm = {}, {}
    for fam in ("H", "A"):
        for view in ("frozen", "title"):
            for arm in ARMS:
                scores[fam, arm, view] = json.loads((d2 / "scores" / f"{fam}-{arm}-{view}.json").read_bytes())
            scores[fam, "windows", view] = json.loads((d2 / "scores" / f"{fam}-windows-frozen.json").read_bytes())
        for arm in (*ARMS, "windows"):
            for view in (("frozen",) if arm == "windows" else ("frozen", "title")):
                mine = arm_counts(scores[fam, arm, view])
                frozen = S["per_arm"][f"{fam}:{arm}:{view}"]
                diff = {k: (v, frozen.get(k)) for k, v in mine.items()
                        if (abs(v - frozen[k]) > 1e-12 if isinstance(v, float) else v != frozen[k])}
                check(not diff, f"per-arm {fam}:{arm}:{view} recomputed from rows", diff=diff)
                per_arm[f"{fam}:{arm}:{view}"] = mine
    out["per_arm"] = per_arm

    # ---------- 4. coordinator title crosscheck ----------
    q = json.loads(blob(*QUALITY))
    for e in q["original_title_projection_full_score_equality"]:
        arm = f"{e['mode']}-{e['order']}"
        got = sha((d2 / "scores" / f"{e['document']}-{arm}-title.json").read_bytes())
        check(got == e["full_score_sha256"], f"coordinator full title score equality {e['document']}:{arm}", sha256=got)

    # ---------- 5. comparisons, transitions and gates ----------
    pairs = [("native-ab", "carbon-ab"), ("native-ba", "carbon-ba"), ("native-ab", "native-ba"),
             ("carbon-ab", "carbon-ba"), ("native-ab", "carbon-ba"), ("native-ba", "carbon-ab"),
             *[("windows", t) for t in ARMS]]
    comps, transitions = {}, {}
    for fam in ("H", "A"):
        for view in ("frozen", "title"):
            for base, trial in pairs:
                key = f"{fam}:{view}:{base}->{trial}"
                bs, ts = scores[fam, base, view], scores[fam, trial, view]
                tr, per = classify(bs, ts)
                fr = S["comparisons"][key]
                for f in ("counts", "four_way", "net_recovery", "new_unflagged", "new_unflagged_paths", "matched_paths"):
                    check(tr[f] == fr["critical"][f], f"{key}: critical {f} recomputed", mine=tr[f], frozen=fr["critical"][f])
                cw = four_way(rows(bs, "cells"), rows(ts, "cells"))
                lw = four_way(rows(bs, "lines"), rows(ts, "lines"))
                check(cw == fr["cells_four_way"] and lw == fr["lines_four_way"], f"{key}: cells/lines four-way recomputed")
                pb, pt = per_arm[f"{fam}:{base}:{'frozen' if base == 'windows' else view}"], \
                    per_arm[f"{fam}:{trial}:{view}"]
                dc, dl = pt["cer"] - pb["cer"], pt["cell_accuracy"] - pb["cell_accuracy"]
                check(abs(dc - fr["delta"]["cer"]) < 1e-12 and abs(dl - fr["delta"]["cell_accuracy"]) < 1e-12,
                      f"{key}: CER/cell deltas recomputed")
                budget = dc <= CER_MAX and dl >= CELL_MIN
                check(budget == fr["inside_quality_budget"], f"{key}: budget recomputed", budget=budget)
                cmpf = json.loads((d2 / "compare" / f"{fam}-{view}-{base}__{trial}.json").read_bytes())["comparison"]
                frozen_list = {e["at"] for e in cmpf["new_or_changed_critical_errors"]}
                mine_list = {at for at, c in per.items() if c in ("regress", "abstain", "persist_changed")}
                check(frozen_list == mine_list, f"{key}: regress+abstain+persist_changed = score.py compare() list",
                      n=len(mine_list))
                entry = dict(delta=dict(cer=dc, cell_accuracy=dl), budget=budget, critical=tr, cells_four_way=cw,
                             lines_four_way=lw, new_wrong_source_links=len(cmpf["new_wrong_source_links"]))
                if base.startswith("native") and trial.startswith("carbon") and base[-2:] == trial[-2:]:
                    g = bool(cmpf["complete_matched_pair"] and budget and not cmpf["new_wrong_source_links"]
                             and tr["matched_paths"] and tr["new_unflagged"] == 0)
                    entry["g0_pass"] = g
                    check(g == S["verdict"]["gate_comparisons"][key] == fr["g0_pass"], f"{key}: gate decision recomputed",
                          g0_pass=g)
                if base == "windows":
                    rec = {}
                    for role in ("primary", "sensitivity"):
                        ws = S["windows"][fam][role]["complete_s"]
                        ns = pred[fam, trial]["complete_s"]
                        x = ns - ws
                        rec[role] = dict(neural_s=ns, windows_s=ws, extra_neural_s=x,
                                         net_critical_per_extra_s=tr["net_recovery"] / x,
                                         cells_gained_per_extra_s=(pt["correct_cells"] - pb["correct_cells"]) / x,
                                         edits_saved_per_extra_s=(pb["edits"] - pt["edits"]) / x)
                        fz = fr["recovery"][role]
                        check(all(abs(rec[role][k] - fz[k]) < 1e-9 for k in rec[role]),
                              f"{key}: {role} recovery per extra second recomputed")
                    entry["recovery"] = rec
                comps[key] = entry
                transitions[key] = per
    out["comparisons"] = comps

    # ---------- 6. timing, memory, structure from stage 1 ----------
    timing = {}
    for fam in ("H", "A"):
        t = {}
        for order in ("ab", "ba"):
            n, c = pred[fam, f"native-{order}"]["complete_s"], pred[fam, f"carbon-{order}"]["complete_s"]
            t[order] = dict(native_s=n, carbon_s=c, saving_s=n - c, speedup=n / c)
            fz = S1["timing"][fam]["pairs"][order]
            check(all(abs(t[order][k] - fz[k]) < 1e-9 for k in fz), f"timing {fam}:{order} recomputed")
        spread_n = abs(t["ab"]["native_s"] - t["ba"]["native_s"])
        spread_c = abs(t["ab"]["carbon_s"] - t["ba"]["carbon_s"])
        t["repeat_spread_s"] = dict(native=spread_n, carbon_bf16=spread_c)
        t["min_saving_exceeds_max_spread"] = min(t["ab"]["saving_s"], t["ba"]["saving_s"]) > max(spread_n, spread_c)
        timing[fam] = t
    out["timing"] = timing
    mem = {}
    for k, v in S1["memory"].items():
        mem[k] = dict(device_used_peak_mib=v["device_used_peak_mib"], allocator_max_reserved_mib=v["allocator_max_reserved_mib"],
                      within=v["device_used_peak_mib"] <= CEILING_MIB and v["allocator_max_reserved_mib"] <= CEILING_MIB)
    check(mem["ab:carbon_bf16"]["within"] and mem["ba:carbon_bf16"]["within"], "carbon_bf16 memory <= 10,000 MiB both orders")
    hw = json.loads(blob(*HWRETURN))
    mem["coordinator_external_sampler"] = {o["order"]: dict(peak_mib=o["device_used_peak_mib"], samples=o["device_samples"],
                                                            exit=o["exit"]) for o in hw["orders"]}
    out["memory"] = mem
    struct = {}
    for run, order in (("g0-ab", "ab"), ("g0-ba", "ba")):
        for mode in ("native", "carbon_bf16"):
            arm = S1["runs"][run]["arms"][mode]
            for fam in ("H", "A"):
                gp = arm["grammar_pages"][fam]
                reasons: dict = {}
                for p in gp:
                    for rk, rv in p["malformed_reasons"].items():
                        reasons[rk] = reasons.get(rk, 0) + rv
                struct[f"{fam}:{mode}:{order}"] = dict(
                    pages=len(gp), malformed_pages=sorted(p["page"] for p in gp if not p["structurally_valid"]),
                    malformed_headers=sum(reasons.values()), by_reason=reasons,
                    title_level_headers=sum(p["classes"].get("title_level", 0) for p in gp))
            s = arm["summary"]
            struct[f"counters:{mode}:{order}"] = dict(counters=s["counters"], kernel_paths=s["kernel_paths"],
                                                      failed_or_fallback_windows=s["failed_or_fallback_windows"],
                                                      windows=(s["windows_warm"], s["windows_measured"]))
    out["structure"] = struct

    # ---------- 7. representative synthetic examples ----------
    ex = {}
    for key in ("A:title:native-ab->carbon-ab", "A:frozen:native-ab->carbon-ab"):
        fam, view, _ = key.split(":")
        for at, c in transitions[key].items():
            if c in ("regress", "abstain", "repair", "persist_changed"):
                b = rows(scores[fam, "native-ab", view], "critical")[at]
                t = rows(scores[fam, "carbon-ab", view], "critical")[at]
                ex.setdefault(key, []).append(dict(at=at, transition=c, expected=b["expected"],
                                                   native_observed=b["observed"], carbon_observed=t["observed"],
                                                   flagged=[bool(b.get("flagged")), bool(t.get("flagged"))]))
    out["gate_transition_examples"] = ex

    # ---------- verdict ----------
    gates = [v["g0_pass"] for k, v in comps.items() if "g0_pass" in v]
    out["recomputed_verdict"] = dict(gate_comparisons=len(gates), passing=sum(gates),
                                     g0_pass=all(gates) and mem["ab:carbon_bf16"]["within"] and mem["ba:carbon_bf16"]["within"])
    check(out["recomputed_verdict"]["g0_pass"] == S["verdict"]["g0_pass"] is False, "overall G0 = false recomputed")
    out["checks_run"] = len(results)
    out["failures"] = [r for r in results if not r["ok"]]
    out["checks"] = results
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(dict(checks_run=len(results), failures=len(out["failures"]),
                          recomputed_verdict=out["recomputed_verdict"]), indent=1))
    return 1 if out["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
