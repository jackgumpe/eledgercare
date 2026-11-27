#!/usr/bin/env python3
"""WP-0043 CPU challenge-suite generator and reference recorder.

Author: eld-fixture-claude (Claude Code, claude-opus-5-5).  Standard library only.

This program writes the frozen challenge inputs:

* generated/cases.jsonl        one scenario + injection schedule per case (no answers)
* generated/contracts/*.json   scorer contract per opaque run id (no case names, no faults)
* generated/evidence/*.json    reference evidence produced by this file's own recorder
* generated/inputs/*.bin       raw FP32 score vectors (ground truth; never a scorer input)
* generated/blobs/*.bin        captured FP32 bytes referenced by evidence
* generated/manifest.json      byte counts and SHA-256 of every generated file

The stock analogue below mirrors the pinned native generator control flow of
modeling_unlimitedocr.py (SHA-256 f6df813c...f39f1f): lines 1166-1182 (head result,
no-repeat guard, page guard, greedy argmax, EOS-before-append), 583-605
(_uocr_page_count_guard) and 608-623 (_uocr_no_repeat_ngram).  It operates in place on
one little-endian FP32 byte buffer per step, so r, zN and z are three versions of one
physical buffer exactly as in stock.  The recorder copies bytes according to an explicit
read/write schedule.  Injections are applied either to the observed arm's execution or to
the recorder's output.  No model, tensor library, network or device is used.

The independent expected-result oracle is oracle.py.  It shares no code with this file.
"""

import argparse
import copy
import hashlib
import json
import os
import struct
import sys

EOS = 1
PAGE = 128827
NEG_INF = bytes.fromhex("000080ff")
PHASES = ("C0_raw", "C1_post_rep", "C2_post_page")
PHASE_CUT = {"C0_raw": "PRE_REP", "C1_post_rep": "POST_REP", "C2_post_page": "POST_PAGE"}
DEFAULT_SCHEDULE = ["R C0_raw *", "W_N", "R C1_post_rep *", "W_P", "R C2_post_page *"]
SCHEMA = {
    "case": "wp0043.case.v1",
    "contract": "wp0043.contract.v1",
    "evidence": "wp0043.evidence.v1",
    "manifest": "wp0043.manifest.v1",
}


# ----------------------------------------------------------------------------- FP32 words

_SPECIAL = {
    "+inf": "0000807f", "inf": "0000807f", "-inf": "000080ff",
    "+0.0": "00000000", "0.0": "00000000", "-0.0": "00000080",
    "nan": "0000c07f",
}


def fp32(spec):
    s = str(spec)
    if s in _SPECIAL:
        return bytes.fromhex(_SPECIAL[s])
    if s.startswith("hex:"):
        b = bytes.fromhex(s[4:])
        if len(b) != 4:
            raise ValueError(s)
        return b
    v = float(s)
    b = struct.pack("<f", v)
    if struct.unpack("<f", b)[0] != v:
        raise ValueError("value is not exactly representable in FP32: %s" % s)
    return b


class Vocab:
    def __init__(self, spec):
        self.spec = spec
        if spec["kind"] == "dense":
            self.n = int(spec["size"])
            self._pos = None
            self._ids = None
        elif spec["kind"] == "sparse":
            ids = list(spec["ids"])
            if ids != sorted(set(ids)):
                raise ValueError("sparse ids must be sorted and unique")
            self.n = len(ids)
            self._ids = ids
            self._pos = {t: i for i, t in enumerate(ids)}
        else:
            raise ValueError(spec["kind"])

    def __len__(self):
        return self.n

    def pos(self, tok):
        if self._pos is None:
            if not 0 <= tok < self.n:
                raise KeyError(tok)
            return tok
        return self._pos[tok]

    def id_at(self, i):
        return i if self._ids is None else self._ids[i]

    def ids(self):
        return range(self.n) if self._ids is None else list(self._ids)


def raw_bytes(vocab, spec):
    buf = bytearray(fp32(spec.get("default", "0.0")) * len(vocab))
    for k, v in spec.get("values", {}).items():
        p = vocab.pos(int(k))
        buf[4 * p:4 * p + 4] = fp32(v)
    return bytes(buf)


# ----------------------------------------------------------------- native-mirroring guards

def page_scan(st, gen, page_id):
    # modeling_unlimitedocr.py 587-596
    n = len(gen)
    if n > st["scanned"]:
        tail = gen[st["scanned"]:n]
        m = tail.count(page_id)
        if m:
            st["marker_cum"] += m
            st["page_len"] = tail[::-1].index(page_id)
        else:
            st["page_len"] += len(tail)
        st["scanned"] = n


def _keep_only(buf, vocab, tid):
    p = vocab.pos(tid)
    keep = bytes(buf[4 * p:4 * p + 4])
    buf[:] = NEG_INF * len(vocab)
    buf[4 * p:4 * p + 4] = keep


def page_guard(buf, vocab, gen, expected_pages, page_id, eos_id, max_page_tokens, st):
    # modeling_unlimitedocr.py 583-605 (in place)
    if expected_pages <= 0:
        return "not_invoked"
    page_scan(st, gen, page_id)
    mc = st["marker_cum"]
    if mc > expected_pages:
        _keep_only(buf, vocab, eos_id)
        return "force_eos_overflow"
    elif 0 < max_page_tokens <= st["page_len"]:
        tid = page_id if mc < expected_pages else eos_id
        _keep_only(buf, vocab, tid)
        return "force_page" if tid == page_id else "force_eos_cap"
    elif mc < expected_pages:
        p = vocab.pos(eos_id)
        buf[4 * p:4 * p + 4] = NEG_INF
        return "ban_eos"
    return "none"


def no_repeat(buf, vocab, seq, order, window, whitelist, start_delta=0):
    # modeling_unlimitedocr.py 608-623 (in place); start_delta != 0 only for injected bugs
    if order <= 0 or len(seq) < order:
        return []
    prefix = tuple(seq[-(order - 1):]) if order > 1 else tuple()
    start = max(0, len(seq) - window + start_delta)
    end = len(seq) - order + 1
    banned = set()
    for i in range(start, end):
        ng = tuple(seq[i:i + order])
        if ng[:-1] == prefix:
            banned.add(ng[-1])
    banned -= set(whitelist)
    for t in banned:
        p = vocab.pos(t)
        buf[4 * p:4 * p + 4] = NEG_INF
    return sorted(banned)


def select(buf, vocab, rule):
    vals = struct.unpack("<%df" % len(vocab), bytes(buf))
    for v in vals:
        if v != v:
            raise ValueError("NaN reached greedy selection; native torch semantics not modelled")
    best = max(vals)
    idx = [i for i, v in enumerate(vals) if v == best]
    i = idx[0] if rule == "first" else idx[-1]
    return vocab.id_at(i)


# ------------------------------------------------------------------------- arm execution

def initial_guard_state(prefix, expected_pages, page_id):
    """Native page-guard state before the first analogue step: the guard ran once at each
    earlier native step j with gen = prefix[:j] (j = 0 .. len(prefix)-1)."""
    st = {"marker_cum": 0, "scanned": 0, "page_len": 0}
    if expected_pages > 0:
        for j in range(len(prefix)):
            page_scan(st, prefix[:j], page_id)
    return st


def _ops(injection, name):
    return [op for op in injection if op["op"] == name]


def run_arm(sc, raws, injection, observe):
    vocab = Vocab(sc["vocab"])
    e = sc["prompt_ids"].count(sc["page_id"]) if sc.get("page_count_guard", True) else 0
    order = sc["ngram"]["order"]
    window = sc["ngram"]["window"]
    wl = sc["ngram"]["whitelist"]
    delta = sum(op["delta"] for op in _ops(injection, "ngram_window_delta"))
    include_prompt = bool(_ops(injection, "ngram_include_prompt"))
    max_new = sc["max_new_tokens"]
    for op in _ops(injection, "max_new_tokens"):
        max_new = op["value"]
    interrupt = None
    for op in _ops(injection, "interrupt"):
        interrupt = op["after_step"]
    sel_steps = {}
    for op in _ops(injection, "select_rule"):
        for s in op["steps"]:
            sel_steps[s] = op["rule"]
    reinvoke = {op["step"] for op in _ops(injection, "guard_reinvoke") if op["guard"] == "page"}
    perturb = {}
    for op in _ops(injection, "perturb_raw"):
        perturb.setdefault(op["step"], {}).update(op["values"])
    overrides = {op["step"]: op for op in _ops(injection, "guard_state_override")}
    schedules = {}
    for op in _ops(injection, "copy_schedule"):
        for k in op["rows"]:
            schedules[k] = op["events"]

    gen = list(sc["generated_prefix"])
    st = initial_guard_state(gen, e, sc["page_id"])
    rows = []
    ctx = []
    finish, terminal = "length", True
    row_of_step = {s: k for k, s in enumerate(sc["rows"])}
    for s in range(max_new):
        buf = bytearray(raws[s])
        for k, v in perturb.get(s, {}).items():
            p = vocab.pos(int(k))
            buf[4 * p:4 * p + 4] = fp32(v)
        n = len(gen)
        is_row = observe and s in row_of_step
        k = row_of_step.get(s)
        omit = []
        if s in overrides:
            st.update(overrides[s]["set"])
            if overrides[s].get("record") == "omit_fields":
                omit = list(overrides[s]["set"].keys())
        entry_state = dict(st)
        entry_gen = list(gen)
        events = (schedules.get(k, DEFAULT_SCHEDULE) if is_row else ["W_N", "W_P"])
        dest = {q: bytearray(4 * len(vocab)) for q in PHASES}
        unread = {q: set(range(len(vocab))) for q in PHASES}
        calls = {"ngram": 0, "page": 0}
        for ev in events:
            if ev == "W_N":
                if order > 0:
                    seq = (list(sc["prompt_ids"]) + gen) if include_prompt else gen
                    no_repeat(buf, vocab, seq, order, window, wl, delta)
                    calls["ngram"] += 1
            elif ev == "W_P":
                if e > 0:
                    page_guard(buf, vocab, gen, e, sc["page_id"], sc["eos_id"], sc["max_page_tokens"], st)
                    calls["page"] += 1
                    if s in reinvoke:
                        page_guard(buf, vocab, gen, e, sc["page_id"], sc["eos_id"], sc["max_page_tokens"], st)
                        calls["page"] += 1
            else:
                _, q, which = ev.split(" ", 2)
                if which == "*":
                    slots = sorted(unread[q])
                else:
                    slots = sorted(vocab.pos(int(t)) for t in json.loads(which))
                for p in slots:
                    if p not in unread[q]:
                        raise ValueError("slot read twice: %s %s" % (q, p))
                    dest[q][4 * p:4 * p + 4] = buf[4 * p:4 * p + 4]
                    unread[q].discard(p)
        if is_row:
            for q in PHASES:
                if unread[q]:
                    raise ValueError("schedule leaves unread slots for %s" % q)
        y = select(buf, vocab, sel_steps.get(s, "first"))
        exit_state = dict(st)
        if is_row:
            caps = {}
            for qi, q in enumerate(PHASES):
                seqno = 3 * k + qi + 1
                caps[q] = {
                    "bc_offset": PHASE_CUT[q], "event_seq": seqno, "copy_id": "ev_%d" % seqno,
                    "origin": "native_copy", "dtype": "float32", "byteorder": "little",
                    "declared_len": len(vocab), "complete": True, "_bytes": bytes(dest[q]),
                }
            ent = {"guard_state": {f: v for f, v in entry_state.items() if f not in omit}}
            rows.append({
                "row": k, "step": s, "history_len": n,
                "consumed_id": (gen[-1] if gen else None),
                "entry": ent, "captures": caps, "guard_calls": calls, "selected_id": y,
                "exit": {"guard_state": exit_state, "appended": y != sc["eos_id"],
                         "gen_len_after": n + (0 if y == sc["eos_id"] else 1),
                         "finish": "stop" if y == sc["eos_id"] else None},
            })
            ctx.append({"gen": entry_gen, "state": entry_state})
        if y == sc["eos_id"]:
            finish = "stop"
            break
        gen.append(y)
        if interrupt is not None and s == interrupt:
            finish, terminal = None, False
            break
    public = {"token_ids": gen, "finish_reason": finish, "terminal_observed": terminal}
    return public, rows, ctx


def _strip(rec):
    for f in ("bc_offset", "event_seq", "copy_id"):
        rec.pop(f, None)


def apply_record_ops(sc, rows, ctx, injection):
    vocab = Vocab(sc["vocab"])
    e = sc["prompt_ids"].count(sc["page_id"]) if sc.get("page_count_guard", True) else 0
    by_row = {r["row"]: (r, c) for r, c in zip(rows, ctx)}
    for op in injection:
        name = op["op"]
        if name not in ("drop", "truncate", "set_word", "strip_provenance", "label", "swap",
                        "duplicate", "recompute"):
            continue
        row, c = by_row[op.get("row", 0)]
        caps = row["captures"]
        if name == "drop":
            del caps[op["phase"]]
        elif name == "truncate":
            rec = caps[op["phase"]]
            rec["_bytes"] = rec["_bytes"][:4 * op["keep_words"]]
            rec["complete"] = bool(op["declare_complete"])
        elif name == "set_word":
            rec = caps[op["phase"]]
            b = bytearray(rec["_bytes"])
            p = vocab.pos(op["slot_id"])
            b[4 * p:4 * p + 4] = bytes.fromhex(op["word_le"])
            rec["_bytes"] = bytes(b)
        elif name == "strip_provenance":
            _strip(caps[op["phase"]])
        elif name == "label":
            caps[op["phase"]].update(op["set"])
        elif name == "swap":
            a, b = op["phases"]
            if op["labels"] == "move_with_bytes":
                caps[a], caps[b] = caps[b], caps[a]
            else:
                caps[a]["_bytes"], caps[b]["_bytes"] = caps[b]["_bytes"], caps[a]["_bytes"]
                if op["labels"] == "strip":
                    _strip(caps[a])
                    _strip(caps[b])
        elif name == "duplicate":
            caps[op["to"]] = copy.deepcopy(caps[op["from"]])
        elif name == "recompute":
            # The recorder keeps only its C0 copy and synthesises later phases with its own
            # (correct) mask code on a private buffer, re-running the guards on a copied state.
            buf = bytearray(caps["C0_raw"]["_bytes"])
            st = dict(c["state"])
            gen = c["gen"]
            no_repeat(buf, vocab, gen, sc["ngram"]["order"], sc["ngram"]["window"], sc["ngram"]["whitelist"])
            zn = bytes(buf)
            page_guard(buf, vocab, gen, e, sc["page_id"], sc["eos_id"], sc["max_page_tokens"], st)
            z = bytes(buf)
            for q, val in (("C1_post_rep", zn), ("C2_post_page", z)):
                rec = caps[q]
                rec["_bytes"] = val
                if op["labels"] == "honest":
                    rec["origin"] = "offline_recompute"
                    _strip(rec)


# -------------------------------------------------------------------------- case catalogue

P34 = list(range(100, 134))          # 34 distinct ordinary IDs (companion p. 6)
Q34 = list(range(200, 234))          # a second disjoint run


def _active_base(vocab_kind="sparse"):
    """Companion p. 6 active history H = (PAGE) || p || (7) || p, |H| = 70."""
    H0 = [PAGE] + P34 + [7] + P34
    ids = sorted(set([0, EOS, 7, 8, PAGE] + P34))
    vocab = {"kind": "dense", "size": 129280} if vocab_kind == "dense" else {"kind": "sparse", "ids": ids}
    return {
        "vocab": vocab, "eos_id": EOS, "page_id": PAGE,
        "prompt_ids": [PAGE, 9001, PAGE, 9002, PAGE, 9003], "page_count_guard": True,
        "max_page_tokens": 20000, "ngram": {"order": 35, "window": 1024, "whitelist": []},
        "generated_prefix": H0, "max_new_tokens": 1, "rows": [0],
        "raw": [{"step": 0, "default": "0.0", "values": {"1": "8.0", "7": "9.0", "8": "4.0"}}],
    }


def _f4_base():
    return {
        "vocab": {"kind": "sparse", "ids": [0, 1, 6, 7, 8]}, "eos_id": EOS, "page_id": PAGE,
        "prompt_ids": [PAGE, PAGE, PAGE], "page_count_guard": True, "max_page_tokens": 20000,
        "ngram": {"order": 35, "window": 1024, "whitelist": []},
        "generated_prefix": [], "max_new_tokens": 1, "rows": [0],
        "raw": [{"step": 0, "default": "0.0", "values": {"1": "8.0", "6": "5.0", "7": "9.0", "8": "4.0"}}],
    }


def _f3_base():
    return {
        "vocab": {"kind": "sparse", "ids": [0, 1, 6, 7, 8]}, "eos_id": EOS, "page_id": PAGE,
        "prompt_ids": [], "page_count_guard": True, "max_page_tokens": 20000,
        "ngram": {"order": 35, "window": 1024, "whitelist": []},
        "generated_prefix": [], "max_new_tokens": 1, "rows": [0],
        "raw": [{"step": 0, "default": "0.0", "values": {"6": "5.0", "8": "5.0"}}],
    }


def _f2_base(second):
    H0 = P34 + [PAGE] + second
    ids = sorted(set([0, EOS, PAGE, 900] + P34 + second))
    return {
        "vocab": {"kind": "sparse", "ids": ids}, "eos_id": EOS, "page_id": PAGE,
        "prompt_ids": [PAGE, PAGE, PAGE], "page_count_guard": True, "max_page_tokens": 34,
        "ngram": {"order": 35, "window": 1024, "whitelist": []},
        "generated_prefix": H0, "max_new_tokens": 1, "rows": [0],
        "raw": [{"step": 0, "default": "0.0", "values": {str(PAGE): "7.0", "900": "3.0", "1": "2.0"}}],
    }


def _f5_base():
    fill = list(range(2001, 2011))
    H0 = [PAGE] + fill[:8] + [128821]
    ids = sorted(set([0, EOS, 6, 16, 1328, 1449, 128821, 128822, PAGE] + fill))
    plan = [
        {"1": "12.0", "6": "5.0"},
        {"1": "12.0", "1449": "5.0"},
        {"1": "12.0", "16": "5.0"},
        {"1": "12.0", "1328": "5.0"},
        {"1": "12.0", "128822": "5.0"},
        {"2009": "6.0", "1": "3.0"},
        {str(PAGE): "6.0", "1": "3.0"},
        {"2010": "6.0", "1": "3.0"},
        {str(PAGE): "6.0", "1": "3.0"},
        {"2002": "6.0", "1": "3.0"},
        {"1": "6.0", "2003": "3.0"},
    ]
    return {
        "vocab": {"kind": "sparse", "ids": ids}, "eos_id": EOS, "page_id": PAGE,
        "prompt_ids": [PAGE, PAGE, PAGE], "page_count_guard": True, "max_page_tokens": 20000,
        "ngram": {"order": 35, "window": 1024, "whitelist": []},
        "generated_prefix": H0, "max_new_tokens": len(plan), "rows": [0, 1, 2, 3, 4],
        "raw": [{"step": s, "default": "0.0", "values": v} for s, v in enumerate(plan)],
    }


def _f7a_base():
    return {
        "vocab": {"kind": "sparse", "ids": [1, 10, 11, 12, 13, 14, PAGE]}, "eos_id": EOS, "page_id": PAGE,
        "prompt_ids": [PAGE, PAGE], "page_count_guard": True, "max_page_tokens": 4,
        "ngram": {"order": 35, "window": 1024, "whitelist": []},
        "generated_prefix": [PAGE, 10, 11, 12], "max_new_tokens": 3, "rows": [0, 1],
        "raw": [
            {"step": 0, "default": "0.0", "values": {"1": "10.0", "13": "5.0"}},
            {"step": 1, "default": "0.0", "values": {str(PAGE): "4.0", "1": "9.0", "14": "6.0"}},
            {"step": 2, "default": "0.0", "values": {"1": "7.0"}},
        ],
    }


def _f7b_base(kind):
    fill = iter(range(3000, 5000))
    if kind == "prompt":
        prompt = [next(fill) for _ in range(10)] + P34 + [7] + [next(fill) for _ in range(5)]
        H0 = [next(fill) for _ in range(16)] + P34
    else:
        lead = 35 if kind == "out" else 36
        H0 = [next(fill) for _ in range(lead)] + P34 + [7]
        H0 += [next(fill) for _ in range(1026 - len(H0))] + P34
        prompt = []
    ids = sorted(set([0, EOS, 7, 8] + H0 + prompt))
    return {
        "vocab": {"kind": "sparse", "ids": ids}, "eos_id": EOS, "page_id": PAGE,
        "prompt_ids": prompt, "page_count_guard": True, "max_page_tokens": 20000,
        "ngram": {"order": 35, "window": 1024, "whitelist": []},
        "generated_prefix": H0, "max_new_tokens": 1, "rows": [0],
        "raw": [{"step": 0, "default": "0.0", "values": {"7": "9.0", "8": "4.0"}}],
    }


def _f7c_base(values):
    return {
        "vocab": {"kind": "sparse", "ids": [0, 1, 2]}, "eos_id": EOS, "page_id": PAGE,
        "prompt_ids": [PAGE], "page_count_guard": True, "max_page_tokens": 20000,
        "ngram": {"order": 35, "window": 1024, "whitelist": []},
        "generated_prefix": [], "max_new_tokens": 1, "rows": [0],
        "raw": [{"step": 0, "default": "0.0", "values": values}],
    }


def catalogue():
    C = []

    def add(case_id, title, scenario, injection=()):
        fixture, sub = case_id.split(".", 1)
        C.append({"case_id": case_id, "fixture": fixture, "subcase": sub, "title": title,
                  "scenario": scenario, "injection": list(injection)})

    # F0 pristine controls -------------------------------------------------------------
    add("F0.active_sparse", "Pristine owned copies on the companion p.6 active history (compact vocabulary)",
        _active_base())
    add("F0.active_dense", "Pristine owned copies on the same history at native vocabulary size 129280",
        _active_base("dense"))
    add("F1.dense_late_raw", "Native-size vector; raw copy taken after the no-repeat write",
        _active_base("dense"),
        [{"op": "copy_schedule", "rows": [0], "events": ["W_N", "R C0_raw *", "R C1_post_rep *", "W_P", "R C2_post_page *"]}])

    # F1 active first guard ------------------------------------------------------------
    add("F1.pristine", "Active repetition guard, owned copies at all three cuts", _active_base())
    add("F1.late_raw", "Raw hook moved one phase late (after the no-repeat write)", _active_base(),
        [{"op": "copy_schedule", "rows": [0], "events": ["W_N", "R C0_raw *", "R C1_post_rep *", "W_P", "R C2_post_page *"]}])
    add("F1.all_late", "Every hook moved one phase late", _active_base(),
        [{"op": "copy_schedule", "rows": [0], "events": ["W_N", "R C0_raw *", "W_P", "R C1_post_rep *", "R C2_post_page *"]}])
    add("F1.recompute_honest", "Raw copied once; later phases synthesised offline and labelled as such",
        _active_base(), [{"op": "recompute", "row": 0, "labels": "honest"}])
    add("F1.recompute_forged", "Raw copied once; later phases synthesised offline with native-looking labels",
        _active_base(), [{"op": "recompute", "row": 0, "labels": "forged"}])

    # F2 forced but forbidden ----------------------------------------------------------
    add("F2.valid_force", "Page cap forces PAGE; the repetition guard does not ban it", _f2_base(Q34))
    add("F2.forced_banned", "Page cap forces PAGE which the repetition guard already banned", _f2_base(P34))

    # F3 ties, signed zero, NaN --------------------------------------------------------
    add("F3.tie_pass", "Two tied finite maxima; native first-index selection", _f3_base())
    add("F3.tie_last", "Two tied maxima; observed arm selects the last maximum", _f3_base(),
        [{"op": "select_rule", "rule": "last_max", "steps": [0]}])
    add("F3.zero_flip", "Sign bit of a preserved losing +0.0 flipped in the final capture", _f3_base(),
        [{"op": "set_word", "row": 0, "phase": "C2_post_page", "slot_id": 7, "word_le": "00000080"}])
    nan_base = _active_base()
    nan_base["raw"][0]["values"]["7"] = "nan"
    add("F3.nan_masked", "Raw NaN at a slot the repetition guard bans; faithful capture", nan_base)

    # F4 phase and completeness on equal bytes (memo Fixture 4-Amended) -----------------
    add("F4.pristine", "Equal-byte r and zN, owned copies with native ancestry", _f4_base())
    add("F4.a_inverted_ancestry", "r and zN records swapped together with their ancestry metadata", _f4_base(),
        [{"op": "swap", "row": 0, "phases": ["C0_raw", "C1_post_rep"], "labels": "move_with_bytes"}])
    add("F4.b_duplicate_copy", "One pre-repetition copy recorded under both r and zN labels", _f4_base(),
        [{"op": "duplicate", "row": 0, "from": "C0_raw", "to": "C1_post_rep"},
         {"op": "label", "row": 0, "phase": "C2_post_page", "set": {"event_seq": 2, "copy_id": "ev_2"}}])
    add("F4.c_late_hook_inactive", "Raw hook one phase late where the repetition guard writes nothing", _f4_base(),
        [{"op": "copy_schedule", "rows": [0], "events": ["W_N", "R C0_raw *", "R C1_post_rep *", "W_P", "R C2_post_page *"]}])
    add("F4.c_swap_labels_stay", "r and zN bytes swapped, labels left with their phase", _f4_base(),
        [{"op": "swap", "row": 0, "phases": ["C0_raw", "C1_post_rep"], "labels": "stay_with_phase"}])
    add("F4.d_swap_unverifiable", "r and zN bytes swapped with all ancestry absent", _f4_base(),
        [{"op": "swap", "row": 0, "phases": ["C0_raw", "C1_post_rep"], "labels": "strip"}])
    add("F4.e_drop_zN", "After-repetition capture absent", _f4_base(),
        [{"op": "drop", "row": 0, "phase": "C1_post_rep"}])
    add("F4.f_interrupted_write", "Raw capture write interrupted after three words, declared incomplete", _f4_base(),
        [{"op": "truncate", "row": 0, "phase": "C0_raw", "keep_words": 3, "declare_complete": False}])
    add("F4.g_interrupt_after_differing", "Raw slot 1 read after the page write, then the write is interrupted",
        _f4_base(),
        [{"op": "copy_schedule", "rows": [0], "events": ["R C0_raw [0, 6, 7, 8]", "W_N", "R C1_post_rep *", "W_P", "R C0_raw *", "R C2_post_page *"]},
         {"op": "truncate", "row": 0, "phase": "C0_raw", "keep_words": 3, "declare_complete": False}])
    add("F4.h_false_complete", "Raw capture of three words declared complete", _f4_base(),
        [{"op": "truncate", "row": 0, "phase": "C0_raw", "keep_words": 3, "declare_complete": True}])
    add("F4.i_missing_and_short", "zN absent and final vector short but declared complete", _f4_base(),
        [{"op": "drop", "row": 0, "phase": "C1_post_rep"},
         {"op": "truncate", "row": 0, "phase": "C2_post_page", "keep_words": 4, "declare_complete": True}])
    add("F4.j_missing_and_changed", "zN absent and a preserved allowed word changed in the final vector", _f4_base(),
        [{"op": "drop", "row": 0, "phase": "C1_post_rep"},
         {"op": "set_word", "row": 0, "phase": "C2_post_page", "slot_id": 6, "word_le": "0000b040"}])

    # F5 continuation (F07-shaped: five field rows, two later markers, EOS) -------------
    add("F5.pristine", "Five field rows, continuation to native EOS stop", _f5_base())
    add("F5.later_id", "Observed arm raw perturbed at a post-field step", _f5_base(),
        [{"op": "perturb_raw", "step": 7, "values": {"2003": "7.0"}}])
    add("F5.terminal_reason", "Observed arm generation budget one step shorter", _f5_base(),
        [{"op": "max_new_tokens", "value": 10}])
    add("F5.interrupt_after_field", "Observed run interrupted after step 6, before terminal", _f5_base(),
        [{"op": "interrupt", "after_step": 6}])
    add("F5.interrupt_with_conflict", "Raw perturbed at step 5, then interrupted after step 6", _f5_base(),
        [{"op": "perturb_raw", "step": 5, "values": {"2004": "7.0"}}, {"op": "interrupt", "after_step": 6}])
    add("F5.interrupt_in_field", "Observed run interrupted after field row 2", _f5_base(),
        [{"op": "interrupt", "after_step": 2}])

    # F6 ordering and ownership on one in-place buffer ------------------------------------
    add("F6.owned", "Owned copies, each completed before the next native writer", _active_base(),
        [{"op": "copy_schedule", "rows": [0], "events": list(DEFAULT_SCHEDULE)}])
    add("F6.alias_end", "All three captures alias the live buffer and materialise after both writers",
        _active_base(),
        [{"op": "copy_schedule", "rows": [0], "events": ["W_N", "W_P", "R C0_raw *", "R C1_post_rep *", "R C2_post_page *"]}])
    add("F6.zN_alias_late", "zN capture aliases the buffer and materialises after the page write", _active_base(),
        [{"op": "copy_schedule", "rows": [0], "events": ["R C0_raw *", "W_N", "W_P", "R C1_post_rep *", "R C2_post_page *"]}])
    add("F6.torn_raw", "Raw copy reads ID 7 early and the rest after both writers", _active_base(),
        [{"op": "copy_schedule", "rows": [0], "events": ["R C0_raw [7]", "W_N", "R C1_post_rep *", "W_P", "R C0_raw *", "R C2_post_page *"]}])

    # F7a stateful page cursor ---------------------------------------------------------
    add("F7a.valid", "Two observed steps through a cap-forced PAGE, then EOS", _f7a_base())
    add("F7a.reset_recorded", "Cursor reset to 0 at row-1 entry; the entry record shows it", _f7a_base(),
        [{"op": "guard_state_override", "step": 1, "set": {"scanned": 0}, "record": "actual"}])
    add("F7a.reset_unrecorded", "Cursor reset to 0 at row-1 entry; the entry record omits the cursor", _f7a_base(),
        [{"op": "guard_state_override", "step": 1, "set": {"scanned": 0}, "record": "omit_fields"}])
    add("F7a.reinvoke_idempotent", "Page guard invoked twice at row 1 on the same history", _f7a_base(),
        [{"op": "guard_reinvoke", "guard": "page", "step": 1}])

    # F7b window edges and prompt exclusion ----------------------------------------------
    add("F7b.out", "Matching 35-gram starts at i=35 = a-1 (outside window)", _f7b_base("out"))
    add("F7b.in", "Matching 35-gram starts at i=36 = a (inside window)", _f7b_base("in"))
    add("F7b.prompt", "Matching 35-gram only inside the prompt", _f7b_base("prompt"))
    add("F7b.out_window_minus1", "Observed guard window start one earlier", _f7b_base("out"),
        [{"op": "ngram_window_delta", "delta": -1}])
    add("F7b.in_window_plus1", "Observed guard window start one later", _f7b_base("in"),
        [{"op": "ngram_window_delta", "delta": 1}])
    add("F7b.prompt_included", "Observed guard scans prompt plus generated IDs", _f7b_base("prompt"),
        [{"op": "ngram_include_prompt"}])

    # F7c +inf and winning negative zero ---------------------------------------------------
    add("F7c.pos_inf_raw", "Raw +inf at slot 0, captured faithfully", _f7c_base({"0": "+inf", "1": "0.0", "2": "5.0"}))
    zero = {"0": "-0.0", "1": "0.0", "2": "+0.0"}
    add("F7c.neg_zero_pass", "Winning -0.0 tied with +0.0, faithful capture", _f7c_base(zero))
    add("F7c.neg_zero_canonicalised", "Winning -0.0 canonicalised to +0.0 in the final capture", _f7c_base(zero),
        [{"op": "set_word", "row": 0, "phase": "C2_post_page", "slot_id": 0, "word_le": "00000000"}])
    add("F7c.neg_zero_pick_last", "Observed arm selects the later tied zero", _f7c_base(zero),
        [{"op": "select_rule", "rule": "last_max", "steps": [0]}])
    return C


# ------------------------------------------------------------------------------- writing

def canon(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run_id_of(case_id):
    return "r" + sha(("wp0043-fixture-run:" + case_id).encode("utf-8"))[:12]


def contract_of(sc, run_id):
    return {
        "schema": SCHEMA["contract"], "run_id": run_id,
        "vocab": sc["vocab"], "dtype": "float32", "byteorder": "little", "sentinel_le": NEG_INF.hex(),
        "eos_id": sc["eos_id"], "page_id": sc["page_id"], "prompt_ids": sc["prompt_ids"],
        "page_count_guard": sc.get("page_count_guard", True), "max_page_tokens": sc["max_page_tokens"],
        "ngram": sc["ngram"], "generated_prefix": sc["generated_prefix"],
        "max_new_tokens": sc["max_new_tokens"], "rows": sc["rows"],
        "phase_map": dict(PHASE_CUT), "required_origin": "native_copy",
    }


def build(out_dir):
    files = {}

    def put(rel, data):
        path = os.path.join(out_dir, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
        files[rel] = data

    lines = []
    for case in catalogue():
        sc = case["scenario"]
        vocab = Vocab(sc["vocab"])
        e = sc["prompt_ids"].count(sc["page_id"]) if sc.get("page_count_guard", True) else 0
        sc["initial_guard_state"] = initial_guard_state(sc["generated_prefix"], e, sc["page_id"])
        raws = []
        for spec in sc["raw"]:
            b = raw_bytes(vocab, spec)
            spec["input"] = "inputs/%s.bin" % sha(b)
            spec["sha256"] = sha(b)
            spec["nbytes"] = len(b)
            put(spec["input"], b)
            raws.append(b)
        rid = run_id_of(case["case_id"])
        contract = contract_of(sc, rid)
        cbytes = canon(contract)
        put("contracts/%s.json" % rid, cbytes)
        untouched, _, _ = run_arm(sc, raws, [], observe=False)
        observed, rows, ctx = run_arm(sc, raws, case["injection"], observe=True)
        apply_record_ops(sc, rows, ctx, case["injection"])
        for row in rows:
            for q in list(row["captures"]):
                rec = row["captures"][q]
                b = rec.pop("_bytes")
                rec["blob"] = sha(b)
                rec["nbytes"] = len(b)
                put("blobs/%s.bin" % rec["blob"], b)
        evidence = {
            "schema": SCHEMA["evidence"], "run_id": rid, "contract_sha256": sha(cbytes),
            "arms": {"untouched": {"public": untouched},
                     "observed": {"public": observed, "rows": rows}},
        }
        put("evidence/%s.json" % rid, canon(evidence))
        line = dict(case)
        line["schema"] = SCHEMA["case"]
        line["run_id"] = rid
        line["contract_path"] = "contracts/%s.json" % rid
        line["reference_evidence_path"] = "evidence/%s.json" % rid
        lines.append(canon(line))
    put("cases.jsonl", b"".join(lines))
    src = open(os.path.abspath(__file__), "rb").read()
    manifest = {
        "schema": SCHEMA["manifest"],
        "generator": {"path": "build_fixtures.py", "sha256": sha(src), "bytes": len(src),
                      "python": sys.version.split()[0]},
        "case_count": len(lines),
        "files": {rel: {"bytes": len(b), "sha256": sha(b)} for rel, b in sorted(files.items())},
    }
    with open(os.path.join(out_dir, "manifest.json"), "wb") as fh:
        fh.write(json.dumps(manifest, sort_keys=True, indent=1).encode("ascii") + b"\n")
    return manifest


def check(out_dir):
    with open(os.path.join(out_dir, "manifest.json"), "rb") as fh:
        manifest = json.loads(fh.read())
    bad = []
    for rel, meta in manifest["files"].items():
        path = os.path.join(out_dir, *rel.split("/"))
        try:
            b = open(path, "rb").read()
        except OSError:
            bad.append((rel, "missing"))
            continue
        if len(b) != meta["bytes"] or sha(b) != meta["sha256"]:
            bad.append((rel, "differs"))
    return manifest, bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated"))
    ap.add_argument("--check", action="store_true", help="verify files against manifest.json only")
    a = ap.parse_args(argv)
    if a.check:
        manifest, bad = check(a.out)
        for rel, why in bad:
            print("MANIFEST %s %s" % (why, rel))
        print("checked %d files, %d problems" % (len(manifest["files"]), len(bad)))
        return 1 if bad else 0
    m = build(a.out)
    print("wrote %d cases, %d files" % (m["case_count"], len(m["files"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
