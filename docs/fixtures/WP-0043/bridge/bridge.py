#!/usr/bin/env python3
"""WP-0043 transport bridge: frozen fixture scenarios -> candidate CPU wire v1 -> normal CLI.

Author: eld-fixture-claude (Claude Code, claude-opus-5-5).  Standard library only.

  plan      convert every frozen case (generated/cases.jsonl) into a wire-v1 CASE and CONTRACT,
            or an explicit rejection naming the missing neutral operation.  Needs no candidate.
  run       for each planned case, serially invoke the candidate's normal entries
                python -B <candidate>/stock.py capture CASE.json        > evidence.json
                python -B <candidate>/stock.py score EVIDENCE CONTRACT  > result.json
            recording argv, exit status, stdout/stderr bytes and digests.
  fidelity  compare captured candidate records with the frozen reference evidence (bytes per
            row/phase, selected ID, page states, documents) to show what the transport delivered.

Inputs used: generated/cases.jsonl (scenario + injection), generated/inputs (raw words),
generated/evidence (frozen reference trajectories: histories and public documents are fixture
stimulation; record bytes are used only by `fidelity`), and the frozen generator
build_fixtures.py to compute live-buffer words per stage for the copy-schedule mapping.
Never read: expected/ (oracle rows).  Never passed to the scorer: case names, injections, fault
labels or verdicts; the scorer receives only CONTRACT (= CASE.contract) and candidate evidence.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.dirname(HERE)
GEN = os.path.join(FIX, "generated")
PHASES = ("C0_raw", "C1_post_rep", "C2_post_page")
BRIDGE_VERSION = "wp0043.bridge.v1"
EXEC_OPS = {"guard_state_override", "guard_reinvoke", "ngram_window_delta", "ngram_include_prompt",
            "select_rule", "perturb_raw", "max_new_tokens", "interrupt"}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load_generator():
    spec = importlib.util.spec_from_file_location("wp0043_frozen_generator", os.path.join(FIX, "build_fixtures.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Unsupported(Exception):
    def __init__(self, reason, needed):
        super().__init__(reason)
        self.reason = reason
        self.needed = needed


def words_le(data):
    return list(struct.unpack("<%dI" % (len(data) // 4), data))


def f32(w):
    return struct.unpack("<f", struct.pack("<I", w))[0]


def first_max_slot(words):
    vals = [f32(w) for w in words]
    best = max(vals)
    return next(i for i, v in enumerate(vals) if v == best)


# --------------------------------------------------------------------- schedule mapping

def parse_schedule(events, vocab_ids, index):
    """Stage (0 raw, 1 post-rep, 2 post-page) at which each compact slot of each phase is read."""
    stage, got = 0, {q: [None] * len(vocab_ids) for q in PHASES}
    for ev in events:
        if ev == "W_N":
            stage = 1
        elif ev == "W_P":
            stage = 2
        else:
            _, q, which = ev.split(" ", 2)
            slots = [i for i in range(len(vocab_ids)) if got[q][i] is None] if which == "*" \
                else [index[int(t)] for t in json.loads(which)]
            for i in slots:
                got[q][i] = stage
    return got


def map_phase(q, st, words):
    """Wire ops reproducing a phase read schedule.  Returns (ops, deviations, kind)."""
    n = len(st)
    intended = PHASES.index(q)
    if len(set(st)) == 1:
        u = st[0]
        return ([] if u == intended else [{"op": "capture_at", "phase": q, "at": PHASES[u]}]), 0, "exact"
    for b in range(1, n):
        c, t = st[0], st[b]
        if all(x == c for x in st[:b]) and all(x == t for x in st[b:]) and t > c:
            ops = [] if c == intended else [{"op": "capture_at", "phase": q, "at": PHASES[c]}]
            return ops + [{"op": "torn", "phase": q, "at": PHASES[t], "bytes": 4 * b}], 0, "exact"
    # byte-equivalent substitution: same recorded words, fewest slots read at a different stage
    want = [words[st[i]][i] for i in range(n)]
    best = None
    for u in range(3):
        if all(words[u][i] == want[i] for i in range(n)):
            dev = sum(1 for i in range(n) if st[i] != u)
            cand = (dev, 0, [] if u == intended else [{"op": "capture_at", "phase": q, "at": PHASES[u]}])
            best = cand if best is None or cand[:2] < best[:2] else best
    for c in range(3):
        for t in range(c + 1, 3):
            okp = [words[c][i] == want[i] for i in range(n)]
            oks = [words[t][i] == want[i] for i in range(n)]
            for b in range(1, n):
                if all(okp[:b]) and all(oks[b:]):
                    dev = sum(1 for i in range(b) if st[i] != c) + sum(1 for i in range(b, n) if st[i] != t)
                    ops = ([] if c == intended else [{"op": "capture_at", "phase": q, "at": PHASES[c]}]) + \
                          [{"op": "torn", "phase": q, "at": PHASES[t], "bytes": 4 * b}]
                    cand = (dev, 1, ops)
                    if best is None or cand[:2] < best[:2]:
                        best = cand
    if best is None:
        raise Unsupported("phase %s read schedule (stages by slot) is neither uniform nor a later-suffix split "
                          "and has no byte-equivalent prefix/suffix representation" % q,
                          "torn read with an explicit token-ID set or multiple byte ranges per cut")
    return best[2], best[0], "byte_equivalent_substitution"


# ------------------------------------------------------------------------------ planning

def plan_case(case, G):
    sc = case["scenario"]
    inj = case["injection"]
    vocab = G.Vocab(sc["vocab"])
    vocab_ids = list(vocab.ids())
    index = {t: i for i, t in enumerate(vocab_ids)}
    rows = sc["rows"]
    row_of_step = {s: k for k, s in enumerate(rows)}
    if sc["ngram"]["whitelist"]:
        raise Unsupported("non-empty n-gram whitelist", "contract whitelist field")
    if not sc.get("page_count_guard", True):
        raise Unsupported("page_count_guard disabled", "contract page_count_guard field")
    ref = json.load(open(os.path.join(GEN, case["reference_evidence_path"]), "rb"))
    pub_u = ref["arms"]["untouched"]["public"]
    pub_o = ref["arms"]["observed"]["public"]
    H0 = sc["generated_prefix"]
    raws = [open(os.path.join(GEN, spec["input"]), "rb").read() for spec in sc["raw"]]
    # per-stage live words of the observed execution, from the frozen generator
    exec_only = [op for op in inj if op["op"] in EXEC_OPS]
    _, stage_rows, _ = G.run_arm(sc, raws, exec_only, observe=True)
    stage_words = {r["row"]: [words_le(r["captures"][q]["_bytes"]) for q in PHASES] for r in stage_rows}
    notes, ops, deviations = [], [], []
    last_row_step = rows[-1]
    for op in inj:
        kind = op["op"]
        if kind in ("perturb_raw",):
            if op["step"] in row_of_step:
                raise Unsupported("raw perturbation at an observed row", "raw override op for the observed arm")
            notes.append("perturb_raw at non-row step %d is represented only by the observed public document" % op["step"])
        elif kind == "max_new_tokens":
            if op["value"] <= last_row_step:
                raise Unsupported("budget ends before a scheduled row", "omit_row / withheld-row op")
            notes.append("max_new_tokens=%d is represented only by the observed document terminal" % op["value"])
        elif kind == "interrupt":
            if op["after_step"] < last_row_step:
                raise Unsupported("observed run interrupted before scheduled row(s) %s" %
                                  [s for s in rows if s > op["after_step"]],
                                  "omit_row (withhold a scheduled row's capture and selection) op")
            notes.append("interrupt after step %d is represented by a shorter observed document without terminal" % op["after_step"])
    for k, s in enumerate(rows):
        if k not in stage_words:
            raise Unsupported("observed execution never reaches scheduled row %d" % k, "omit_row op")
    sched = {}
    for op in inj:
        if op["op"] == "copy_schedule":
            for k in op["rows"]:
                sched[k] = op["events"]
    rec_bytes = {}
    for k in range(len(rows)):
        st = parse_schedule(sched.get(k, ["R C0_raw *", "W_N", "R C1_post_rep *", "W_P", "R C2_post_page *"]),
                            vocab_ids, index)
        rec_bytes[k] = {}
        for q in PHASES:
            m, dev, how = map_phase(q, st[q], stage_words[k])
            for x in m:
                x["row"] = k
            ops += m
            if dev or how != "exact":
                deviations.append({"row": k, "phase": q, "kind": how, "slots_read_at_other_stage": dev})
            rec_bytes[k][q] = [stage_words[k][st[q][i]][i] for i in range(len(vocab_ids))]
    touched = set()
    genuine = {}
    for op in inj:
        kind = op["op"]
        k = op.get("row", 0)
        if kind == "copy_schedule" or kind in ("perturb_raw", "max_new_tokens", "interrupt"):
            continue
        if kind == "guard_state_override":
            k = row_of_step.get(op["step"])
            if k is None or set(op["set"]) != {"scanned"}:
                raise Unsupported("state override outside a row or of fields other than the cursor",
                                  "general typed page-state override op")
            ops.append({"row": k, "op": "cursor", "value": op["set"]["scanned"]})
            if op.get("record") == "omit_fields":
                for f in op["set"]:
                    ops.append({"row": k, "op": "omit_state", "when": "before", "field": f})
        elif kind == "guard_reinvoke":
            k = row_of_step.get(op["step"])
            if k is None or op["guard"] != "page":
                raise Unsupported("re-invocation outside a row or of another guard", "general reenter op")
            ops.append({"row": k, "op": "reenter_page"})
        elif kind == "ngram_window_delta":
            ops += [{"row": kk, "op": "ngram_start", "delta": op["delta"]} for kk in range(len(rows))]
        elif kind == "ngram_include_prompt":
            ops += [{"row": kk, "op": "include_prompt"} for kk in range(len(rows))]
        elif kind == "select_rule":
            if op["rule"] != "last_max":
                raise Unsupported("selection rule " + op["rule"], "general selection-rule op")
            for s in op["steps"]:
                if s not in row_of_step:
                    raise Unsupported("selection change at a non-row step", "document-only selection change")
                ops.append({"row": row_of_step[s], "op": "lastmax"})
        elif kind == "drop":
            ops.append({"row": k, "op": "drop", "phase": op["phase"]})
            touched.add((k, op["phase"]))
            genuine.setdefault(k, set()).add(op["phase"])
        elif kind == "truncate":
            ops.append({"row": k, "op": "truncate", "phase": op["phase"], "bytes": 4 * op["keep_words"],
                        "complete": bool(op["declare_complete"])})
            touched.add((k, op["phase"]))
        elif kind == "set_word":
            if op["phase"] != "C2_post_page":
                raise Unsupported("post-capture edit of %s; a live write would also reach later phases" % op["phase"],
                                  "recorder-side word edit op (after copy, live buffer untouched)")
            w = int.from_bytes(bytes.fromhex(op["word_le"]), "little")
            live = list(rec_bytes[k]["C2_post_page"])
            before = first_max_slot(live)
            live[index[op["slot_id"]]] = w
            if first_max_slot(live) != before:
                raise Unsupported("live write before the final capture would change selection",
                                  "recorder-side word edit op (after copy, live buffer untouched)")
            ops.append({"row": k, "op": "write", "phase": "C2_post_page", "id": op["slot_id"], "value": "%08x" % w})
            deviations.append({"row": k, "phase": "C2_post_page", "kind": "live_write_for_recorder_edit",
                               "note": "word written in the live buffer immediately before the final copy; selection verified unchanged"})
            touched.add((k, "C2_post_page"))
        elif kind == "strip_provenance":
            ops.append({"row": k, "op": "unwitness", "phase": op["phase"]})
        elif kind == "swap":
            a, b = op["phases"]
            if (k, a) in touched or (k, b) in touched:
                raise Unsupported("swap after another edit", "ordered recorder-op composition")
            if op["labels"] == "move_with_bytes":
                ops.append({"row": k, "op": "swap", "a": a, "b": b})
            elif rec_bytes[k][a] == rec_bytes[k][b]:
                deviations.append({"row": k, "phase": a + "," + b, "kind": "identity_byte_swap",
                                   "note": "swapping byte-identical records with labels kept is the identity on bytes"})
                if op["labels"] == "strip":
                    ops += [{"row": k, "op": "unwitness", "phase": a}, {"row": k, "op": "unwitness", "phase": b}]
            else:
                raise Unsupported("byte swap with labels left in place on different bytes",
                                  "swap_bytes op (exchange payloads, keep copy receipts)")
        elif kind == "duplicate":
            ops.append({"row": k, "op": "duplicate", "from": op["from"], "to": op["to"]})
            genuine.setdefault(k, set()).add(op["to"])
        elif kind == "label":
            # identity only if it restates what a genuine copy ledger records anyway
            q = op["phase"]
            seq, found = 0, False
            for kk in range(k + 1):
                for qq in PHASES:
                    if qq in genuine.get(kk, set()):
                        continue
                    seq += 1
                    if kk == k and qq == q:
                        found = True
                        break
                if found:
                    break
            if set(op["set"]) <= {"event_seq", "copy_id"} and op["set"].get("event_seq", seq) == seq \
                    and op["set"].get("copy_id", "ev_%d" % seq) == "ev_%d" % seq:
                deviations.append({"row": k, "phase": q, "kind": "label_restates_genuine_ledger",
                                   "note": "event_seq=%d equals the genuine copy count; no op needed" % seq})
            else:
                raise Unsupported("label rewrite that a genuine copy ledger would not produce",
                                  "none by design: forged receipts are outside the candidate's genuine-event model")
        elif kind == "recompute":
            if op["labels"] != "honest":
                raise Unsupported("offline synthesis with native-looking distinct copy receipts",
                                  "none by design: the candidate ledger emits receipts only for genuine copies")
            ops += [{"row": k, "op": "recompute", "phase": "C1_post_rep", "ancestry": "absent"},
                    {"row": k, "op": "recompute", "phase": "C2_post_page", "ancestry": "absent"}]
        else:
            raise Unsupported("injection " + kind, kind)
    histories = []
    for s in rows:
        n = len(H0) + s
        histories.append(pub_o["token_ids"][:n])
        if pub_o["token_ids"][:n] != pub_u["token_ids"][:n]:
            notes.append("row at step %d: observed history differs from untouched" % s)
    raw_words = [["%08x" % w for w in words_le(raws[s])] for s in rows]
    doc_u = {"ids": pub_u["token_ids"], "terminal": pub_u["finish_reason"]}
    doc_o = {"ids": pub_o["token_ids"]}
    if pub_o["terminal_observed"]:
        doc_o["terminal"] = pub_o["finish_reason"]
    contract = {"vocab": vocab_ids, "page": sc["page_id"], "eos": sc["eos_id"], "order": sc["ngram"]["order"],
                "window": sc["ngram"]["window"], "cap": sc["max_page_tokens"], "prompt": sc["prompt_ids"],
                "histories": histories, "raw_words": raw_words, "document": doc_u}
    wire_case = {"contract": contract, "injections": ops, "document": doc_o}
    notes.append("public documents are fixture-supplied trajectories (frozen reference recorder), not executed by the candidate CPU capture")
    return wire_case, ops, deviations, notes


EXTRAS = [
    ("X.F6.alias_end.view", "F6.alias_end",
     [{"row": 0, "op": "alias", "phase": q} for q in PHASES],
     "same scenario with the candidate's live-view transport instead of moved owned copies"),
    ("X.F6.zN_alias_late.view", "F6.zN_alias_late",
     [{"row": 0, "op": "alias", "phase": "C1_post_rep"}],
     "same scenario with the candidate's live-view transport for zN"),
    ("X.F1.recompute_raw_ancestry", "F1.recompute_forged",
     [{"row": 0, "op": "recompute", "phase": "C1_post_rep", "ancestry": "raw"},
      {"row": 0, "op": "recompute", "phase": "C2_post_page", "ancestry": "raw"}],
     "nearest genuine-ledger analogue of the rejected forged case: synthesised bytes claim the original C0 copy receipt"),
]


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def cmd_plan(a):
    G = load_generator()
    os.makedirs(a.out, exist_ok=False)
    records = []
    for line in open(os.path.join(GEN, "cases.jsonl"), "rb").read().decode("ascii").splitlines():
        case = json.loads(line)
        rec = {"schema": "wp0043.transport.v1", "bridge": BRIDGE_VERSION, "case_id": case["case_id"],
               "run_id": case["run_id"]}
        try:
            wire, ops, dev, notes = plan_case(case, G)
            d = os.path.join(a.out, "cases", case["case_id"])
            os.makedirs(d)
            cb, kb = canon(wire), canon(wire["contract"])
            open(os.path.join(d, "case.json"), "wb").write(cb)
            open(os.path.join(d, "contract.json"), "wb").write(kb)
            rec.update({"status": "planned", "wire_ops": ops, "deviations": dev, "notes": notes,
                        "case_sha256": sha(cb), "contract_sha256": sha(kb), "case_bytes": len(cb)})
        except Unsupported as exc:
            rec.update({"status": "rejected_unsupported", "reason": exc.reason, "needed_neutral_op": exc.needed})
        records.append(rec)
        print("%-34s %-20s %s" % (case["case_id"], rec["status"],
                                  json.dumps([o["op"] for o in rec.get("wire_ops", [])]) if rec["status"] == "planned" else rec["reason"]))
    # Disclosed extra variants: alternative wire transports of frozen scenarios.  Not frozen
    # cases; never compared to expected rows; reported separately.
    cases = {json.loads(l)["case_id"]: json.loads(l) for l in open(os.path.join(GEN, "cases.jsonl"), "rb").read().decode("ascii").splitlines()}
    for xid, parent, ops, why in EXTRAS:
        case = dict(cases[parent])
        case["injection"] = []
        wire, _, _, notes = plan_case(case, G)
        wire["injections"] = ops
        d = os.path.join(a.out, "cases", xid)
        os.makedirs(d)
        cb, kb = canon(wire), canon(wire["contract"])
        open(os.path.join(d, "case.json"), "wb").write(cb)
        open(os.path.join(d, "contract.json"), "wb").write(kb)
        records.append({"schema": "wp0043.transport.v1", "bridge": BRIDGE_VERSION, "case_id": xid, "run_id": None,
                        "parent": parent, "status": "extra_planned", "wire_ops": ops, "why": why, "notes": notes,
                        "case_sha256": sha(cb), "contract_sha256": sha(kb)})
        print("%-34s %-20s %s" % (xid, "extra_planned", json.dumps([o["op"] for o in ops])))
    open(os.path.join(a.out, "transport.jsonl"), "wb").write(b"".join(canon(r) + b"\n" for r in records))
    print("planned=%d rejected=%d extras=%d" % (sum(r["status"] == "planned" for r in records),
                                                sum(r["status"] == "rejected_unsupported" for r in records),
                                                sum(r["status"] == "extra_planned" for r in records)))
    return 0


def run_cli(argv, cwd, stdout_path, stderr_path):
    t0 = time.time()
    with open(stdout_path, "wb") as so, open(stderr_path, "wb") as se:
        p = subprocess.run(argv, cwd=cwd, stdout=so, stderr=se)
    out, err = open(stdout_path, "rb").read(), open(stderr_path, "rb").read()
    return {"argv": argv, "cwd": cwd, "exit": p.returncode, "seconds": round(time.time() - t0, 3),
            "stdout_bytes": len(out), "stdout_sha256": sha(out), "stderr_bytes": len(err), "stderr_sha256": sha(err),
            "stderr_tail": err[-600:].decode("utf-8", "replace")}


def cmd_run(a):
    cand = os.path.abspath(a.candidate_dir)
    stock = os.path.join(cand, "stock.py")
    lines = []
    for line in open(os.path.join(a.plan, "transport.jsonl"), "rb").read().decode("ascii").splitlines():
        rec = json.loads(line)
        if rec["status"] not in ("planned", "extra_planned"):
            lines.append({"case_id": rec["case_id"], "run_id": rec["run_id"], "status": rec["status"]})
            continue
        d = os.path.join(a.plan, "cases", rec["case_id"])
        cap = run_cli([sys.executable, "-B", stock, "capture", os.path.join(d, "case.json")], cand,
                      os.path.join(d, "evidence.json"), os.path.join(d, "capture.stderr"))
        out = {"case_id": rec["case_id"], "run_id": rec["run_id"], "capture": cap}
        if cap["exit"] == 0:
            sc = run_cli([sys.executable, "-B", stock, "score", os.path.join(d, "evidence.json"),
                          os.path.join(d, "contract.json")], cand,
                         os.path.join(d, "result.json"), os.path.join(d, "score.stderr"))
            out["score"] = sc
            out["status"] = "scored" if sc["exit"] == 0 else "score_failed"
            if sc["exit"] == 0:
                res = json.loads(open(os.path.join(d, "result.json"), "rb").read())
                out["verdict"] = res.get("verdict")
                out["first_divergent_phase"] = res.get("first_divergent_phase")
        else:
            out["status"] = "capture_failed"
        lines.append(out)
        print("%-34s %-14s %s %s" % (rec["case_id"], out["status"], out.get("verdict", "-"), out.get("first_divergent_phase")))
    open(os.path.join(a.plan, "run.jsonl"), "wb").write(b"".join(canon(x) + b"\n" for x in lines))
    meta = {"python": sys.version.split()[0], "executable": sys.executable, "candidate_dir": cand,
            "bridge": BRIDGE_VERSION, "serial": True}
    open(os.path.join(a.plan, "run-meta.json"), "wb").write(canon(meta))
    bad = [x for x in lines if x["status"] not in ("scored", "rejected_unsupported")]
    print("scored=%d rejected=%d failed=%d" % (sum(x["status"] == "scored" for x in lines),
                                               sum(x["status"] == "rejected_unsupported" for x in lines), len(bad)))
    return 0 if not bad else 1


def cmd_fidelity(a):
    out = []
    cases = {json.loads(l)["case_id"]: json.loads(l) for l in open(os.path.join(GEN, "cases.jsonl"), "rb").read().decode("ascii").splitlines()}
    for line in open(os.path.join(a.plan, "run.jsonl"), "rb").read().decode("ascii").splitlines():
        r = json.loads(line)
        if r["status"] != "scored" or r["case_id"] not in cases:
            continue
        case = cases[r["case_id"]]
        ref = json.load(open(os.path.join(GEN, case["reference_evidence_path"]), "rb"))
        ev = json.load(open(os.path.join(a.plan, "cases", r["case_id"], "evidence.json"), "rb"))
        diffs = []
        rrows = {x["row"]: x for x in ref["arms"]["observed"]["rows"]}
        for row in ev["rows"]:
            k = row["index"]
            rr = rrows.get(k)
            if rr is None:
                diffs.append({"row": k, "field": "row", "reference": None})
                continue
            for q in PHASES:
                cr, fr = row["phases"].get(q), rr["captures"].get(q)
                cb = bytes.fromhex(cr["hex"]) if cr and "hex" in cr else None
                fb = open(os.path.join(GEN, "blobs", fr["blob"] + ".bin"), "rb").read() if fr else None
                if cb != fb:
                    diffs.append({"row": k, "phase": q, "field": "bytes",
                                  "candidate_bytes": None if cb is None else len(cb), "reference_bytes": None if fb is None else len(fb)})
                if cr is not None and fr is not None and cr.get("complete") != fr.get("complete"):
                    diffs.append({"row": k, "phase": q, "field": "complete"})
            if row.get("y") != rr.get("selected_id"):
                diffs.append({"row": k, "field": "y", "candidate": row.get("y"), "reference": rr.get("selected_id")})
            for mine, theirs in (("before", "entry"), ("after", "exit")):
                if row.get(mine) != rr[theirs]["guard_state"]:
                    diffs.append({"row": k, "field": mine + "_state", "candidate": row.get(mine), "reference": rr[theirs]["guard_state"]})
        out.append({"case_id": r["case_id"], "transport_exact": not diffs, "differences": diffs})
        print("%-34s %s" % (r["case_id"], "exact" if not diffs else json.dumps(diffs)[:200]))
    open(os.path.join(a.plan, "fidelity.jsonl"), "wb").write(b"".join(canon(x) + b"\n" for x in out))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="WP-0043 transport bridge")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--out", required=True)
    r = sub.add_parser("run")
    r.add_argument("--plan", required=True)
    r.add_argument("--candidate-dir", required=True)
    f = sub.add_parser("fidelity")
    f.add_argument("--plan", required=True)
    a = ap.parse_args(argv)
    return {"plan": cmd_plan, "run": cmd_run, "fidelity": cmd_fidelity}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
