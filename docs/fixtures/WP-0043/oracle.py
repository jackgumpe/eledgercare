#!/usr/bin/env python3
"""WP-0043 independent expected-result oracle and reference scorer.

Author: eld-fixture-claude (Claude Code, claude-opus-5-5).  Standard library only.
Shares no code with build_fixtures.py and imports no candidate, native or tensor code.

Method.  Score words are unsigned 32-bit IEEE-754 bit patterns.  Guard supports are
computed from the written contract (docs/research/WP-0042/scoring.md, "Derive the guards
without trusting the observed scores") as sets, and every phase vector is a mask
M_S(v) of its predecessor (companion Eq. 4.2).  For each case the oracle

  1. recomputes the true untouched and observed executions from scenario + injection;
  2. predicts the evidence a recorder following the injection schedule would emit;
  3. scores that predicted evidence with an evidence-only reference scorer (RefScorer),
     which reads only the contract, the evidence and the captured bytes;
  4. analyses ground truth separately (what actually differed from the native
     execution, byte lanes from exact little-endian words, execution deltas);
  5. checks the generator's frozen inputs, contract and reference evidence against its
     own prediction and rescoring, reporting any disagreement as a fixture defect.

Commands
  python oracle.py expect  --generated generated --out expected/expected.jsonl --facts expected/facts.json
  python oracle.py score   --contract C.json --evidence E.json --blobs DIR   (observation JSON on stdout)
"""

import argparse
import hashlib
import itertools
import json
import os
import struct
import sys

SENT = 0xFF800000
PHASES = ("C0_raw", "C1_post_rep", "C2_post_page")
OBJ = {"C0_raw": "r", "C1_post_rep": "zN", "C2_post_page": "z"}
REQUIRED_CUT = {"C0_raw": "PRE_REP", "C1_post_rep": "POST_REP", "C2_post_page": "POST_PAGE"}
CUT_OF_VERSION = {0: "PRE_REP", 1: "POST_REP", 2: "POST_PAGE"}
INTENDED_VERSION = {"C0_raw": 0, "C1_post_rep": 1, "C2_post_page": 2}
RANK = {"CFG": 0, "ROW": 1, "B_entry": 2, "C0_raw": 3, "C1_post_rep": 4, "C2_post_page": 5,
        "Y_select": 6, "D_exit": 7, "PUB": 8, "TERM": 9}
STATE_FIELDS = ("marker_cum", "scanned", "page_len")
DEFAULT_EVENTS = ("R C0_raw *", "W_N", "R C1_post_rep *", "W_P", "R C2_post_page *")


class Unsupported(Exception):
    pass


# ----------------------------------------------------------------------------- words

_NAMED = {"+inf": 0x7F800000, "inf": 0x7F800000, "-inf": 0xFF800000, "+0.0": 0x00000000,
          "0.0": 0x00000000, "-0.0": 0x80000000, "nan": 0x7FC00000}


def bits_of(spec):
    s = str(spec)
    if s in _NAMED:
        return _NAMED[s]
    if s.startswith("hex:"):
        return int.from_bytes(bytes.fromhex(s[4:]), "little")
    v = float(s)
    be = struct.pack(">f", v)
    if struct.unpack(">f", be)[0] != v:
        raise ValueError("inexact FP32 literal " + s)
    return int.from_bytes(be, "big")


def le_hex(b):
    return b.to_bytes(4, "little").hex()


def is_finite(b):
    return ((b >> 23) & 0xFF) != 0xFF


def is_nan(b):
    return ((b >> 23) & 0xFF) == 0xFF and (b & 0x7FFFFF) != 0


def as_float(b):
    return struct.unpack(">f", b.to_bytes(4, "big"))[0]


def lane_diff(a, b):
    for lane in range(4):
        if ((a >> (8 * lane)) & 0xFF) != ((b >> (8 * lane)) & 0xFF):
            return lane
    return None


def guaranteed_lanes_vs_finite(b):
    """Lanes in which every finite FP32 word must differ from non-finite word b in at least
    one: the exponent occupies bit 23 (lane 2) and bits 24-30 (lane 3).  Either lane alone
    can coincide with some finite word and lanes 0-1 can coincide, so the exact first
    differing lane requires the actual other word."""
    return [2, 3] if not is_finite(b) else []


def decode(data):
    n, rem = divmod(len(data), 4)
    return list(struct.unpack("<%dI" % n, data[:4 * n])), rem


def encode(v):
    return struct.pack("<%dI" % len(v), *v)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def canon(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


# ----------------------------------------------------------------- contract semantics

class Vocab:
    def __init__(self, spec):
        if spec["kind"] == "dense":
            self.ids = list(range(int(spec["size"])))
        elif spec["kind"] == "sparse":
            self.ids = list(spec["ids"])
            if self.ids != sorted(set(self.ids)):
                raise ValueError("sparse vocabulary not sorted/unique")
        else:
            raise ValueError("vocab kind")
        self.index = {t: i for i, t in enumerate(self.ids)}
        self.n = len(self.ids)

    def offsets(self, tok, lane):
        return {"dense_token_offset": 4 * tok + lane, "compact_offset": 4 * self.index[tok] + lane}


def ban_set(H, order, window, whitelist, start_shift=0):
    """B(H) of scoring.md: H[i+34] for max(0,n-w) <= i <= n-35 with H[i:i+34] = H[n-34:n]."""
    n = len(H)
    if order <= 0 or n < order:
        return frozenset()
    m = order - 1
    suffix = H[n - m:]
    lo = max(0, n - window + start_shift)
    hi = n - order
    hits = set()
    for i in range(lo, hi + 1):
        if H[i:i + m] == suffix:
            hits.add(H[i + m])
    return frozenset(hits - set(whitelist))


def page_step(state, H, page):
    """One native guard scan over the new tail H[scanned:n] (scoring.md wording)."""
    m, sc, pl = state["marker_cum"], state["scanned"], state["page_len"]
    n = len(H)
    if n > sc:
        tail = H[sc:n]
        marks = [i for i, t in enumerate(tail) if t == page]
        if marks:
            m += len(marks)
            pl = len(tail) - 1 - marks[-1]
        else:
            pl += len(tail)
        sc = n
    return {"marker_cum": m, "scanned": sc, "page_len": pl}


def page_replay(H, e, page):
    """(entry, exit) state for the step whose generated history is H, replaying the guard
    once per native step j = 0..len(H) with history H[:j], starting from empty state."""
    st = {"marker_cum": 0, "scanned": 0, "page_len": 0}
    if e <= 0:
        return st, dict(st)
    for j in range(len(H)):
        st = page_step(st, H[:j], page)
    return st, page_step(st, H, page)


def page_support(st, e, c, eos, page):
    if e <= 0:
        return ("all", None)
    m, pl = st["marker_cum"], st["page_len"]
    if m > e:
        return ("only", eos)
    if 0 < c <= pl:
        return ("only", page if m < e else eos)
    if m < e:
        return ("all_but", eos)
    return ("all", None)


def in_support(sup, t):
    kind, x = sup
    return kind == "all" or (kind == "only" and t == x) or (kind == "all_but" and t != x)


def support_json(sup):
    kind, x = sup
    return {"kind": kind, "ids": [] if x is None else [x]}


def mask(v, ids, keep):
    return [w if keep(t) else SENT for w, t in zip(v, ids)]


def first_max(v, ids, rule="first"):
    vals = [as_float(w) for w in v]
    if any(x != x for x in vals):
        raise Unsupported("NaN reaches selection")
    best = max(vals)
    tie = [i for i, x in enumerate(vals) if x == best]
    return ids[tie[0] if rule == "first" else tie[-1]], [ids[i] for i in tie]


# --------------------------------------------------------------- truth simulation

def _ops(inj, name):
    return [op for op in inj if op["op"] == name]


def simulate(sc, raws, inj):
    V = Vocab(sc["vocab"])
    ids = V.ids
    eos, page = sc["eos_id"], sc["page_id"]
    e = sc["prompt_ids"].count(page) if sc.get("page_count_guard", True) else 0
    order, window, wl = sc["ngram"]["order"], sc["ngram"]["window"], sc["ngram"]["whitelist"]
    c = sc["max_page_tokens"]
    shift = sum(op["delta"] for op in _ops(inj, "ngram_window_delta"))
    with_prompt = bool(_ops(inj, "ngram_include_prompt"))
    max_new = sc["max_new_tokens"]
    for op in _ops(inj, "max_new_tokens"):
        max_new = op["value"]
    stop_after = None
    for op in _ops(inj, "interrupt"):
        stop_after = op["after_step"]
    rule = {}
    for op in _ops(inj, "select_rule"):
        for s in op["steps"]:
            rule[s] = op["rule"]
    again = {op["step"] for op in _ops(inj, "guard_reinvoke") if op["guard"] == "page"}
    bump = {}
    for op in _ops(inj, "perturb_raw"):
        bump.setdefault(op["step"], {}).update(op["values"])
    force_state = {op["step"]: op for op in _ops(inj, "guard_state_override")}

    gen = list(sc["generated_prefix"])
    st = page_replay(gen, e, page)[0]
    steps = []
    finish, terminal = "length", True
    for s in range(max_new):
        v0 = list(raws[s])
        for t, val in bump.get(s, {}).items():
            v0[V.index[int(t)]] = bits_of(val)
        n = len(gen)
        if s in force_state:
            st = dict(st)
            st.update(force_state[s]["set"])
        entry = dict(st)
        hist = list(gen)
        B = ban_set((list(sc["prompt_ids"]) + gen) if with_prompt else gen, order, window, wl, shift) \
            if order > 0 else frozenset()
        v1 = mask(v0, ids, lambda t: t not in B)
        reinv = None
        if e > 0:
            st = page_step(st, gen, page)
            sup = page_support(st, e, c, eos, page)
            v2 = mask(v1, ids, lambda t: in_support(sup, t))
            if s in again:
                st2 = page_step(st, gen, page)
                sup2 = page_support(st2, e, c, eos, page)
                v2b = mask(v2, ids, lambda t: in_support(sup2, t))
                reinv = {"state_after_second": st2, "support_after_second": support_json(sup2),
                         "state_unchanged": st2 == st, "bytes_unchanged": v2b == v2}
                st, sup, v2 = st2, sup2, v2b
        else:
            sup = ("all", None)
            v2 = list(v1)
        y, tie = first_max(v2, ids, rule.get(s, "first"))
        steps.append({"step": s, "n": n, "hist": hist, "entry": entry, "exit": dict(st), "ban": B,
                      "support_P": sup, "versions": (v0, v1, v2), "y": y, "tie": tie,
                      "calls": {"ngram": 1 if order > 0 else 0,
                                "page": (2 if s in again else 1) if e > 0 else 0},
                      "reinvocation": reinv})
        if y == eos:
            finish = "stop"
            break
        gen.append(y)
        if stop_after is not None and s == stop_after:
            finish, terminal = None, False
            break
    return {"tokens": gen, "finish": finish, "terminal": terminal, "steps": steps, "e": e}


# ------------------------------------------------------------- predicted evidence

def predict(sc, sim, inj):
    """Records a recorder following the case schedule would write, plus truth tags."""
    V = Vocab(sc["vocab"])
    ids = V.ids
    eos, page = sc["eos_id"], sc["page_id"]
    by_step = {st["step"]: st for st in sim["steps"]}
    sched = {}
    for op in _ops(inj, "copy_schedule"):
        for k in op["rows"]:
            sched[k] = list(op["events"])
    rows, tags = [], []
    for k, s in enumerate(sc["rows"]):
        if s not in by_step:
            continue
        st = by_step[s]
        versions = st["versions"]
        stage = 0
        got = {q: [None] * V.n for q in PHASES}
        for ev in sched.get(k, DEFAULT_EVENTS):
            if ev == "W_N":
                if stage != 0:
                    raise ValueError("writer order")
                stage = 1
            elif ev == "W_P":
                if stage != 1:
                    raise ValueError("writer order")
                stage = 2
            else:
                _, q, which = ev.split(" ", 2)
                targets = [i for i in range(V.n) if got[q][i] is None] if which == "*" \
                    else [V.index[int(t)] for t in json.loads(which)]
                for i in targets:
                    if got[q][i] is not None:
                        raise ValueError("double read")
                    got[q][i] = stage
        caps, tg = {}, {}
        for j, q in enumerate(PHASES):
            if any(x is None for x in got[q]):
                raise ValueError("unread slot")
            seq = 3 * k + j + 1
            caps[q] = {"bc_offset": REQUIRED_CUT[q], "event_seq": seq, "copy_id": "ev_%d" % seq,
                       "origin": "native_copy", "dtype": "float32", "byteorder": "little",
                       "declared_len": V.n, "complete": True,
                       "bits": [versions[got[q][i]][i] for i in range(V.n)]}
            vs = sorted(set(got[q]))
            tg[q] = {"holds": q, "versions": vs,
                     "slot_versions": {str(x): [ids[i] for i in range(V.n) if got[q][i] == x][:12]
                                       for x in vs} if len(vs) > 1 else None,
                     "origin": "native_copy", "edited_slots": [], "truncated_to": None}
        row = {"row": k, "step": s, "history_len": st["n"],
               "consumed_id": st["hist"][-1] if st["hist"] else None,
               "entry": {"guard_state": dict(st["entry"])}, "captures": caps,
               "guard_calls": dict(st["calls"]), "selected_id": st["y"],
               "exit": {"guard_state": dict(st["exit"]), "appended": st["y"] != eos,
                        "gen_len_after": st["n"] + (0 if st["y"] == eos else 1),
                        "finish": "stop" if st["y"] == eos else None}}
        for op in _ops(inj, "guard_state_override"):
            if op["step"] == s and op.get("record") == "omit_fields":
                for f in op["set"]:
                    row["entry"]["guard_state"].pop(f, None)
        rows.append(row)
        tags.append(tg)
    rowmap = {r["row"]: (r, t) for r, t in zip(rows, tags)}
    for op in inj:
        kind = op["op"]
        if kind not in ("drop", "truncate", "set_word", "strip_provenance", "label", "swap",
                        "duplicate", "recompute"):
            continue
        r, t = rowmap[op.get("row", 0)]
        caps = r["captures"]
        if kind == "drop":
            caps.pop(op["phase"])
            t[op["phase"]] = {"holds": None, "dropped": True}
        elif kind == "truncate":
            caps[op["phase"]]["bits"] = caps[op["phase"]]["bits"][:op["keep_words"]]
            caps[op["phase"]]["complete"] = bool(op["declare_complete"])
            t[op["phase"]]["truncated_to"] = op["keep_words"]
        elif kind == "set_word":
            caps[op["phase"]]["bits"][V.index[op["slot_id"]]] = int.from_bytes(bytes.fromhex(op["word_le"]), "little")
            t[op["phase"]]["edited_slots"].append(op["slot_id"])
        elif kind == "strip_provenance":
            for f in ("bc_offset", "event_seq", "copy_id"):
                caps[op["phase"]].pop(f, None)
        elif kind == "label":
            caps[op["phase"]].update(op["set"])
        elif kind == "swap":
            a, b = op["phases"]
            if op["labels"] == "move_with_bytes":
                caps[a], caps[b] = caps[b], caps[a]
            else:
                caps[a]["bits"], caps[b]["bits"] = caps[b]["bits"], caps[a]["bits"]
                if op["labels"] == "strip":
                    for q in (a, b):
                        for f in ("bc_offset", "event_seq", "copy_id"):
                            caps[q].pop(f, None)
            t[a], t[b] = t[b], t[a]
        elif kind == "duplicate":
            src = caps[op["from"]]
            caps[op["to"]] = {kk: (list(vv) if kk == "bits" else vv) for kk, vv in src.items()}
            t[op["to"]] = json.loads(json.dumps(t[op["from"]]))
        elif kind == "recompute":
            st = by_step[r["step"]]
            B = ban_set(st["hist"], sc["ngram"]["order"], sc["ngram"]["window"], sc["ngram"]["whitelist"]) \
                if sc["ngram"]["order"] > 0 else frozenset()
            zn = mask(caps["C0_raw"]["bits"], ids, lambda x: x not in B)
            if sim["e"] > 0:
                sup = page_support(page_step(st["entry"], st["hist"], page), sim["e"], sc["max_page_tokens"], eos, page)
                z = mask(zn, ids, lambda x: in_support(sup, x))
            else:
                z = list(zn)
            for q, val in (("C1_post_rep", zn), ("C2_post_page", z)):
                caps[q]["bits"] = val
                t[q] = {"holds": q, "versions": None, "origin": "offline_recompute",
                        "edited_slots": [], "truncated_to": None, "labels": op["labels"]}
                if op["labels"] == "honest":
                    caps[q]["origin"] = "offline_recompute"
                    for f in ("bc_offset", "event_seq", "copy_id"):
                        caps[q].pop(f, None)
    return rows, tags


def evidence_json(run_id, contract_sha, unt, obs, rows):
    blobs = {}
    out_rows = []
    for r in rows:
        rr = json.loads(json.dumps({k: v for k, v in r.items() if k != "captures"}))
        rr["captures"] = {}
        for q, rec in r["captures"].items():
            data = encode(rec["bits"])
            h = sha(data)
            blobs[h] = data
            c = {k: v for k, v in rec.items() if k != "bits"}
            c["blob"] = h
            c["nbytes"] = len(data)
            rr["captures"][q] = c
        out_rows.append(rr)

    def pub(sim):
        return {"token_ids": sim["tokens"], "finish_reason": sim["finish"], "terminal_observed": sim["terminal"]}
    ev = {"schema": "wp0043.evidence.v1", "run_id": run_id, "contract_sha256": contract_sha,
          "arms": {"untouched": {"public": pub(unt)}, "observed": {"public": pub(obs), "rows": out_rows}}}
    return ev, blobs


# ------------------------------------------------------------------ reference scorer

class RefScorer:
    """Evidence-only scorer.  Inputs: contract bytes, evidence object, blob loader."""

    def __init__(self, contract_bytes, evidence, load_blob):
        self.cb = contract_bytes
        self.c = json.loads(contract_bytes.decode("utf-8"))
        self.ev = evidence
        self.load_blob = load_blob
        self.conf, self.miss = [], []
        self.V = Vocab(self.c["vocab"])
        self.e = self.c["prompt_ids"].count(self.c["page_id"]) if self.c.get("page_count_guard", True) else 0

    def _key(self, phase, obj, check, row=None, step=None, slot=None, detail=None, phase_from=None,
              row_from=None, step_from=None):
        return {"row": row, "step": step, "phase": phase, "object": obj, "check": check, "slot_id": slot,
                "phase_from": phase_from or phase, "row_from": row if row_from is None else row_from,
                "step_from": step if step_from is None else step_from, "detail": detail}

    def M(self, *a, **k):
        self.conf.append(self._key(*a, **k))

    def U(self, *a, **k):
        self.miss.append(self._key(*a, **k))

    def slot_detail(self, i, observed, reference=None, ref_kind=None):
        tok = self.V.ids[i]
        d = {"slot_id": tok, "compact_index": i, "observed_le": le_hex(observed)}
        if reference is not None:
            lane = lane_diff(observed, reference)
            d.update({"reference_le": le_hex(reference), "reference": ref_kind, "lane": lane})
            if lane is not None:
                d.update(self.V.offsets(tok, lane))
        else:
            g = guaranteed_lanes_vs_finite(observed)
            d.update({"reference": None, "lane": None, "guaranteed_lanes_vs_any_finite": g,
                      "dense_token_offset_candidates": [4 * tok + x for x in g],
                      "compact_offset_candidates": [4 * i + x for x in g]})
        return d

    def score(self):
        c, ev, V = self.c, self.ev, self.V
        H0 = c["generated_prefix"]
        if ev.get("schema") != "wp0043.evidence.v1":
            raise ValueError("unsupported evidence schema")
        if "contract_sha256" not in ev:
            self.U("CFG", "contract", "binding")
        elif ev["contract_sha256"] != sha(self.cb):
            self.M("CFG", "contract", "binding")
        if ev.get("run_id") != c.get("run_id"):
            self.M("CFG", "contract", "run_id")
        arms = ev.get("arms", {})
        obs = arms.get("observed")
        unt = arms.get("untouched")
        if obs is None:
            self.U("ROW", "observed_arm", "present")
            obs = {"public": None, "rows": []}
        pub = (obs.get("public") or {}).get("token_ids")
        if pub is not None and pub[:len(H0)] != H0[:len(pub)]:
            self.M("PUB", "token_ids", "prefix", step=-1)
        rows = {}
        for r in obs.get("rows", []):
            s = r.get("step")
            if s in rows:
                self.M("ROW", "row", "duplicate", step=s)
            elif s not in c["rows"]:
                self.M("ROW", "row", "unscheduled", step=s)
            else:
                rows[s] = r
        caps_in_order = []
        for k, s in enumerate(c["rows"]):
            r = rows.get(s)
            if r is None:
                self.U("ROW", "row", "present", row=k, step=s)
                continue
            if r.get("row") != k:
                self.M("ROW", "row", "index", row=k, step=s, detail={"observed": r.get("row")})
            self.score_row(k, s, r, pub, caps_in_order)
        self.score_order(caps_in_order)
        self.score_public(obs.get("public"), (unt or {}).get("public"), unt is not None, H0)
        return self.result()

    def load(self, k, s, q, rec):
        """Returns (bits_available, full) or None when no bytes can be used."""
        V = self.V
        obj = OBJ[q]
        if rec is None:
            self.U(q, obj, "present", row=k, step=s)
            return None
        for f, want in (("dtype", "float32"), ("byteorder", "little"), ("declared_len", V.n)):
            if f not in rec:
                self.U(q, obj, "meta_" + f, row=k, step=s)
            elif rec[f] != want:
                self.M(q, obj, "meta_" + f, row=k, step=s, detail={"observed": rec[f], "required": want})
        data = self.load_blob(rec.get("blob")) if rec.get("blob") else None
        if data is None:
            self.U(q, obj, "bytes", row=k, step=s)
            return None
        if data == "digest_mismatch":
            self.M(q, obj, "artifact_digest", row=k, step=s)
            return None
        if rec.get("nbytes") is not None and rec["nbytes"] != len(data):
            self.M(q, obj, "nbytes", row=k, step=s, detail={"declared": rec["nbytes"], "actual": len(data)})
        bits, rem = decode(data)
        if rem:
            self.M(q, obj, "word_alignment", row=k, step=s)
        complete = rec.get("complete")
        if len(bits) > V.n:
            self.M(q, obj, "length", row=k, step=s, detail={"words": len(bits), "vocab": V.n})
            bits = bits[:V.n]
        elif len(bits) < V.n:
            if complete is True:
                self.M(q, obj, "length_contradiction", row=k, step=s,
                       detail={"words": len(bits), "vocab": V.n, "declared_complete": True})
            else:
                self.U(q, obj, "truncated_tail", row=k, step=s,
                       detail={"words": len(bits), "vocab": V.n, "first_missing_slot_id": V.ids[len(bits)]})
        elif complete is not True:
            self.U(q, obj, "declared_incomplete", row=k, step=s)
        for f in ("bc_offset", "event_seq", "copy_id", "origin"):
            if f not in rec:
                self.U(q, obj, "provenance_" + f, row=k, step=s)
        if "bc_offset" in rec and rec["bc_offset"] != self.c["phase_map"][q]:
            self.M(q, obj, "phase_cut_binding", row=k, step=s,
                   detail={"observed": rec["bc_offset"], "required": self.c["phase_map"][q]})
        if "origin" in rec and rec["origin"] != self.c["required_origin"]:
            self.U(q, obj, "native_origin", row=k, step=s, detail={"observed": rec["origin"]})
        return bits, len(bits) == V.n

    def relation(self, k, s, q, check, ref, refkind, cur, keep, both_required=True):
        """keep(t): slot must preserve ref; else slot must hold the sentinel.  Atom is M if
        any covered slot conflicts, else U if coverage is partial, else P."""
        V = self.V
        bad = []
        covered = len(cur) if ref is None else min(len(cur), len(ref))
        for i in range(covered):
            t = V.ids[i]
            if keep(t) and ref is None:
                continue
            want = ref[i] if keep(t) else SENT
            if cur[i] != want:
                bad.append(self.slot_detail(i, cur[i], want, refkind if keep(t) else "sentinel"))
        if bad:
            self.M(q, OBJ[q], check, row=k, step=s, slot=bad[0]["slot_id"],
                   detail={"first": bad[0], "count": len(bad), "slot_ids": [b["slot_id"] for b in bad[:16]]})
        elif covered < V.n:
            self.U(q, OBJ[q], check, row=k, step=s, detail={"covered_words": covered})

    def score_row(self, k, s, r, pub, caps_in_order):
        c, V = self.c, self.V
        ids = V.ids
        H0 = c["generated_prefix"]
        n = len(H0) + s
        hist = pub[:n] if pub is not None and len(pub) >= n else None
        if r.get("history_len") is None:
            self.U("B_entry", "history", "length", row=k, step=s)
        elif r["history_len"] != n:
            self.M("B_entry", "history", "length", row=k, step=s, detail={"observed": r["history_len"], "required": n})
        if hist is None:
            self.U("B_entry", "history", "public_prefix", row=k, step=s)
        elif "consumed_id" not in r:
            self.U("B_entry", "history", "consumed_id", row=k, step=s)
        elif r["consumed_id"] != (hist[-1] if hist else None):
            self.M("B_entry", "history", "consumed_id", row=k, step=s)
        pre = post = None
        B = sup = A = None
        if hist is not None:
            pre, post = page_replay(hist, self.e, c["page_id"])
            B = ban_set(hist, c["ngram"]["order"], c["ngram"]["window"], c["ngram"]["whitelist"]) \
                if c["ngram"]["order"] > 0 else frozenset()
            sup = page_support(post, self.e, c["max_page_tokens"], c["eos_id"], c["page_id"])
            A = [t for t in ids if t not in B and in_support(sup, t)]
        gs = (r.get("entry") or {}).get("guard_state")
        for f in STATE_FIELDS:
            if gs is None or f not in gs:
                self.U("B_entry", "guard_state", f, row=k, step=s)
            elif pre is not None and gs[f] != pre[f]:
                self.M("B_entry", "guard_state", f, row=k, step=s, detail={"observed": gs[f], "replayed": pre[f]})
        caps = r.get("captures") or {}
        vec = {}
        for q in PHASES:
            got = self.load(k, s, q, caps.get(q))
            vec[q] = got
            if q in caps:
                caps_in_order.append((k, s, q, caps[q]))
        # raw validity
        if vec["C0_raw"] is not None:
            rv = vec["C0_raw"][0]
            bad = [self.slot_detail(i, w) for i, w in enumerate(rv) if not is_finite(w)]
            if bad:
                self.M("C0_raw", "r", "raw_finite", row=k, step=s, slot=bad[0]["slot_id"],
                       detail={"first": bad[0], "count": len(bad), "slot_ids": [b["slot_id"] for b in bad[:16]]})
            elif len(rv) < V.n:
                self.U("C0_raw", "r", "raw_finite", row=k, step=s, detail={"covered_words": len(rv)})
        r_bits = vec["C0_raw"][0] if vec["C0_raw"] else None
        zn_bits = vec["C1_post_rep"][0] if vec["C1_post_rep"] else None
        z_bits = vec["C2_post_page"][0] if vec["C2_post_page"] else None
        calls = r.get("guard_calls")
        for g, q, want in (("ngram", "C1_post_rep", 1 if c["ngram"]["order"] > 0 else 0),
                           ("page", "C2_post_page", 1 if self.e > 0 else 0)):
            if calls is None or g not in calls:
                self.U(q, "guard_calls", g, row=k, step=s)
            elif calls[g] != want:
                self.M(q, "guard_calls", g, row=k, step=s, detail={"observed": calls[g], "required": want})
        if hist is None:
            for q, chk in (("C1_post_rep", "support_N"), ("C2_post_page", "support_P")):
                self.U(q, "support", chk, row=k, step=s)
        else:
            if zn_bits is not None:
                self.relation(k, s, "C1_post_rep", "repetition_mask", r_bits, "r", zn_bits, lambda t: t not in B)
            if r_bits is None and zn_bits is not None:
                self.U("C1_post_rep", "zN", "repetition_mask_preserve", row=k, step=s, detail={"reason": "r unavailable"})
            if not A:
                self.M("C2_post_page", "support", "nonempty", row=k, step=s,
                       detail={"repetition_ban": sorted(B), "page_support": support_json(sup)})
            if z_bits is not None:
                Aset = set(A)
                self.relation(k, s, "C2_post_page", "page_mask", zn_bits, "zN", z_bits, lambda t: t in Aset)
                if zn_bits is None:
                    self.U("C2_post_page", "z", "page_mask_preserve", row=k, step=s, detail={"reason": "zN unavailable"})
                if r_bits is not None:
                    self.relation(k, s, "C2_post_page", "composed_mask", r_bits, "r", z_bits, lambda t: t in Aset)
                bad = [self.slot_detail(i, z_bits[i]) for i in range(len(z_bits))
                       if ids[i] in Aset and not is_finite(z_bits[i])]
                if bad:
                    self.M("C2_post_page", "z", "allowed_finite", row=k, step=s, slot=bad[0]["slot_id"],
                           detail={"first": bad[0], "count": len(bad)})
                elif len(z_bits) < V.n:
                    self.U("C2_post_page", "z", "allowed_finite", row=k, step=s, detail={"covered_words": len(z_bits)})
        # selection
        y = r.get("selected_id")
        if y is None:
            self.U("Y_select", "y", "present", row=k, step=s)
        else:
            if A is not None and y not in A:
                self.M("Y_select", "y", "in_support", row=k, step=s, slot=y, detail={"support_size": len(A)})
            if z_bits is None or len(z_bits) < V.n:
                self.U("Y_select", "y", "first_max", row=k, step=s, detail={"reason": "complete z unavailable"})
            elif any(is_nan(w) for w in z_bits):
                self.U("Y_select", "y", "first_max", row=k, step=s, detail={"reason": "NaN tie semantics unpinned"})
            else:
                want, tie = first_max(z_bits, ids)
                if y != want:
                    self.M("Y_select", "y", "first_max_tie" if y in tie else "first_max", row=k, step=s, slot=y,
                           detail={"first_max": want, "tie_set": tie[:16]})
            if pub is not None:
                if y != c["eos_id"]:
                    if len(pub) > n:
                        if pub[n] != y:
                            self.M("Y_select", "y", "public_agreement", row=k, step=s, detail={"public": pub[n]})
                    elif (self.ev["arms"]["observed"].get("public") or {}).get("terminal_observed"):
                        self.M("Y_select", "y", "public_agreement", row=k, step=s, detail={"public": None})
                    else:
                        self.U("Y_select", "y", "public_agreement", row=k, step=s)
                elif len(pub) != n:
                    self.M("Y_select", "y", "public_agreement", row=k, step=s, detail={"public_len": len(pub)})
        # exit
        ex = r.get("exit")
        if ex is None:
            self.U("D_exit", "exit", "present", row=k, step=s)
        else:
            gso = ex.get("guard_state")
            for f in STATE_FIELDS:
                if gso is None or f not in gso:
                    self.U("D_exit", "guard_state", f, row=k, step=s)
                elif post is not None and gso[f] != post[f]:
                    self.M("D_exit", "guard_state", f, row=k, step=s, detail={"observed": gso[f], "replayed": post[f]})
            if y is not None:
                is_eos = y == c["eos_id"]
                for f, want in (("appended", not is_eos), ("gen_len_after", n + (0 if is_eos else 1)),
                                ("finish", "stop" if is_eos else None)):
                    if f not in ex:
                        self.U("D_exit", "append", f, row=k, step=s)
                    elif ex[f] != want:
                        self.M("D_exit", "append", f, row=k, step=s, detail={"observed": ex[f], "required": want})

    def score_order(self, caps):
        last = None
        seen = {}
        for k, s, q, rec in caps:
            if "event_seq" in rec:
                if last is not None and not last[3] < rec["event_seq"]:
                    self.M(q, OBJ[q], "capture_seq_order", row=k, step=s, phase_from=last[2], row_from=last[0],
                           step_from=last[1], detail={"previous": last[3], "observed": rec["event_seq"]})
                last = (k, s, q, rec["event_seq"])
            cid = rec.get("copy_id")
            if cid is not None:
                if cid in seen:
                    pk, ps, pq = seen[cid]
                    self.M(q, OBJ[q], "duplicate_copy_id", row=k, step=s, phase_from=pq, row_from=pk, step_from=ps,
                           detail={"copy_id": cid})
                else:
                    seen[cid] = (k, s, q)

    def score_public(self, po, pu, have_u, H0):
        base = len(H0)
        if po is None:
            self.U("PUB", "observed_public", "present")
            return
        if not have_u or pu is None:
            self.U("PUB", "untouched_public", "present")
            return
        to, tu = po.get("token_ids") or [], pu.get("token_ids") or []
        fo, fu = po.get("terminal_observed"), pu.get("terminal_observed")
        diff = next((i for i in range(min(len(to), len(tu))) if to[i] != tu[i]), None)
        if diff is not None:
            self.M("PUB", "token_ids", "token", step=diff - base,
                   detail={"index": diff, "observed": to[diff], "untouched": tu[diff]})
        elif len(to) < len(tu):
            if fo:
                self.M("PUB", "token_ids", "length", step=len(to) - base, detail={"observed": len(to), "untouched": len(tu)})
            else:
                self.U("PUB", "token_ids", "tail", step=len(to) - base, detail={"observed": len(to), "untouched": len(tu)})
        elif len(to) > len(tu):
            if fu:
                self.M("PUB", "token_ids", "length", step=len(tu) - base, detail={"observed": len(to), "untouched": len(tu)})
            else:
                self.U("PUB", "untouched_token_ids", "tail", step=len(tu) - base)
        end = max(len(to), len(tu)) - base
        if not fo:
            self.U("TERM", "terminal", "observed_arm", step=end)
        if not fu:
            self.U("TERM", "terminal", "untouched_arm", step=end)
        if fo and fu and po.get("finish_reason") != pu.get("finish_reason"):
            self.M("TERM", "terminal", "finish_reason", step=end,
                   detail={"observed": po.get("finish_reason"), "untouched": pu.get("finish_reason")})

    @staticmethod
    def order_key(x):
        st = x["step"] if x["step"] is not None else -2
        sf = x["step_from"] if x["step_from"] is not None else -2
        # base-contract atoms before the composition extension (companion Eq. 4.2) at equal position
        return (st, RANK[x["phase"]], sf, RANK[x["phase_from"]], x["slot_id"] if x["slot_id"] is not None else -1,
                1 if x["check"] == "composed_mask" else 0, x["object"], x["check"])

    def result(self):
        conf = sorted(self.conf, key=self.order_key)
        miss = sorted(self.miss, key=self.order_key)
        verdict = "M" if conf else ("U" if miss else "P")
        lead = conf[0] if conf else (miss[0] if miss else None)
        # the earliest-starting member of the earliest witnessed group (simultaneous order is an interval)
        first = None
        if lead is not None:
            first = {"row": lead["row"], "step": lead["step"], "phase": lead["phase"],
                     "row_from": lead["row_from"], "step_from": lead["step_from"], "phase_from": lead["phase_from"],
                     "object": lead["object"], "check": lead["check"], "slot_id": lead["slot_id"]}
            d = lead.get("detail") or {}
            f = d.get("first") if isinstance(d.get("first"), dict) else None
            if f:
                for kk in ("lane", "dense_token_offset", "compact_offset", "observed_le", "reference_le",
                           "guaranteed_lanes_vs_any_finite", "dense_token_offset_candidates", "compact_offset_candidates"):
                    if kk in f:
                        first[kk] = f[kk]
        rows = {}
        for x in conf:
            if x["row"] is not None:
                rows[x["row"]] = "M"
        for x in miss:
            if x["row"] is not None and rows.get(x["row"]) != "M":
                rows[x["row"]] = "U"
        return {"schema": "wp0043.observation.v1", "run_id": self.c.get("run_id"), "verdict": verdict,
                "first": first, "conflicts": conf, "missing": miss,
                "row_verdicts": {str(k): rows.get(k, "P") for k in range(len(self.c["rows"]))},
                "counts": {"conflicts": len(conf), "missing": len(miss)},
                "scorer": {"name": "oracle.RefScorer", "contract": "wp0043.oracle-contract.v1"}}


def blob_loader(dirpath):
    def load(h):
        p = os.path.join(dirpath, "%s.bin" % h)
        if not os.path.exists(p):
            return None
        b = open(p, "rb").read()
        return b if sha(b) == h else "digest_mismatch"
    return load


# ------------------------------------------------------------------- ground analysis

def ground(sc, unt, obs, rows, tags, inj):
    V = Vocab(sc["vocab"])
    ids = V.ids
    by_step = {s["step"]: s for s in obs["steps"]}
    record_faults = []
    per_row = []
    for r, t in zip(rows, tags):
        s = r["step"]
        st = by_step[s]
        out = {"row": r["row"], "step": s, "phases": {}}
        for q in PHASES:
            tag = t.get(q)
            intended = st["versions"][INTENDED_VERSION[q]]
            rec = r["captures"].get(q)
            info = {"required_cut": REQUIRED_CUT[q]}
            if rec is None:
                info["status"] = "absent"
                record_faults.append((s, q, "absent", None))
                out["phases"][q] = info
                continue
            bits = rec["bits"]
            first = None
            for i in range(min(len(bits), len(intended))):
                if bits[i] != intended[i]:
                    tok = ids[i]
                    lane = lane_diff(intended[i], bits[i])
                    first = {"slot_id": tok, "true_le": le_hex(intended[i]), "recorded_le": le_hex(bits[i]),
                             "lane_from_word_pair": lane, **V.offsets(tok, lane),
                             "guaranteed_lanes_without_true_word":
                                 guaranteed_lanes_vs_finite(bits[i]) if is_finite(intended[i]) else None}
                    break
            if tag.get("origin") == "native_copy":
                vs = tag["versions"]
                true_cut = CUT_OF_VERSION[vs[0]] if len(vs) == 1 else "TORN"
            else:
                true_cut = None
            src = tag.get("holds")
            info.update({"true_source_phase": src, "true_cut": true_cut, "origin": tag.get("origin"),
                         "torn_slot_versions": tag.get("slot_versions"),
                         "recorded_bc_offset": rec.get("bc_offset"),
                         "label_matches_truth": (rec.get("bc_offset") == true_cut) if true_cut else None,
                         "first_byte_difference_vs_intended": first,
                         "truncated_to_words": tag.get("truncated_to"), "edited_slots": tag.get("edited_slots")})
            faults = []
            if first is not None:
                faults.append("bytes")
            if tag.get("truncated_to") is not None:
                faults.append("truncated")
            if tag.get("origin") != "native_copy":
                faults.append("not_native_copy")
            elif true_cut != REQUIRED_CUT[q]:
                faults.append("wrong_cut")
            if src != q:
                faults.append("record_from_other_phase")
            if rec.get("bc_offset") is not None and true_cut is not None and rec.get("bc_offset") != true_cut:
                faults.append("false_label")
            info["faults"] = faults
            if faults:
                record_faults.append((s, q, faults, first))
            out["phases"][q] = info
        per_row.append(out)
    record_faults.sort(key=lambda x: (x[0], RANK[x[1]]))

    def step_view(sim):
        return [{"step": x["step"], "n": x["n"], "entry_state": x["entry"], "exit_state": x["exit"],
                 "repetition_ban": sorted(x["ban"]), "page_support": support_json(x["support_P"]),
                 "allowed_size": sum(1 for tt in ids if tt not in x["ban"] and in_support(x["support_P"], tt)),
                 "y": x["y"], "final_tie_set": x["tie"][:16],
                 "diagnostic_first_max": [_diag_max(v, ids) for v in x["versions"]],
                 "guard_calls": x["calls"], "reinvocation": x["reinvocation"]}
                for x in sim["steps"]]
    uv, ov = step_view(unt), step_view(obs)
    exec_div = None
    for a, b in itertools.zip_longest(uv, ov):
        if a is None or b is None:
            exec_div = {"step": (a or b)["step"], "field": "step_count", "untouched": a is not None, "observed": b is not None}
            break
        fields = [f for f in ("entry_state", "repetition_ban", "page_support", "exit_state", "y") if a[f] != b[f]]
        if a["guard_calls"] != b["guard_calls"]:
            fields.append("guard_calls")
        ua = by_step_u = None
        if not fields:
            xs = unt["steps"][a["step"]]["versions"]
            ys = obs["steps"][b["step"]]["versions"]
            for name, p_, q_ in zip(("r", "zN", "z"), xs, ys):
                if p_ != q_:
                    i = next(i for i in range(len(p_)) if p_[i] != q_[i])
                    fields.append(name)
                    ua = {"slot_id": ids[i], "untouched_le": le_hex(p_[i]), "observed_le": le_hex(q_[i]),
                          "lane": lane_diff(p_[i], q_[i]), **V.offsets(ids[i], lane_diff(p_[i], q_[i]))}
                    break
        if fields:
            exec_div = {"step": a["step"], "fields": fields,
                        "untouched": {f: a[f] for f in ("entry_state", "exit_state", "repetition_ban", "page_support", "y", "guard_calls")},
                        "observed": {f: b[f] for f in ("entry_state", "exit_state", "repetition_ban", "page_support", "y", "guard_calls")},
                        "word": ua}
            break
    if exec_div is None and (unt["tokens"] != obs["tokens"] or unt["finish"] != obs["finish"] or unt["terminal"] != obs["terminal"]):
        exec_div = {"step": None, "fields": ["public_projection"],
                    "untouched": {"len": len(unt["tokens"]), "finish": unt["finish"], "terminal": unt["terminal"]},
                    "observed": {"len": len(obs["tokens"]), "finish": obs["finish"], "terminal": obs["terminal"]}}
    effective = [op for op in inj if not (op["op"] == "copy_schedule" and list(op["events"]) == list(DEFAULT_EVENTS))]
    return {
        "fault_injected": bool(effective),
        "injected_ops": [op["op"] for op in effective],
        "first_record_divergence": ({"step": record_faults[0][0], "phase": record_faults[0][1],
                                     "kinds": record_faults[0][2], "byte": record_faults[0][3]} if record_faults else None),
        "first_execution_divergence": exec_div,
        "rows": per_row,
        "untouched_execution": uv,
        "observed_execution": ov,
        "public": {"untouched": {"tokens": len(unt["tokens"]), "finish": unt["finish"], "terminal": unt["terminal"]},
                   "observed": {"tokens": len(obs["tokens"]), "finish": obs["finish"], "terminal": obs["terminal"]}},
    }


def _diag_max(v, ids):
    """Diagnostic first maximum; None when a NaN makes the torch tie rule unpinned here."""
    if any(is_nan(w) for w in v):
        return None
    return first_max(v, ids)[0]


def prefix_reachability(sc):
    """Is every prefix token admissible to stock at its own step (some raw vector could emit it)?"""
    H0 = sc["generated_prefix"]
    page, eos = sc["page_id"], sc["eos_id"]
    e = sc["prompt_ids"].count(page) if sc.get("page_count_guard", True) else 0
    o = sc["ngram"]
    st = {"marker_cum": 0, "scanned": 0, "page_len": 0}
    for j in range(len(H0)):
        hist = H0[:j]
        if e > 0:
            st = page_step(st, hist, page)
        sup = page_support(st, e, sc["max_page_tokens"], eos, page)
        B = ban_set(hist, o["order"], o["window"], o["whitelist"]) if o["order"] > 0 else frozenset()
        if H0[j] in B or not in_support(sup, H0[j]) or H0[j] == eos:
            return {"reachable": False, "first_violation_index": j, "token": H0[j],
                    "ban": sorted(B), "page_support": support_json(sup)}
    return {"reachable": True, "prefix_len": len(H0)}


# ------------------------------------------------------------------------ claims

def _conf_checks(exp):
    return {(x["row"], x["phase"], x["check"]) for x in exp["conflicts"]}


def claims_for(cid, exp, g, extra):
    C = []

    def claim(source, text, holds, note=None):
        C.append({"source": source, "claim": text, "holds": bool(holds), "note": note})
    first = exp["first"] or {}
    fr = g["first_record_divergence"] or {}
    frb = fr.get("byte") or {}
    ue = g["untouched_execution"]
    oe = g["observed_execution"]
    checks = {x[2] for x in _conf_checks(exp)}
    if cid in ("F0.active_sparse", "F0.active_dense", "F1.pristine"):
        claim("companion p.6/p.15", "diagnostic maxima of (r, zN, z) are (7, 1, 8); final ID 8",
              ue[0]["diagnostic_first_max"] == [7, 1, 8] and ue[0]["y"] == 8)
        claim("brief 1", "unmodified fixture passes", exp["verdict"] == "P")
    if cid in ("F1.late_raw", "F1.dense_late_raw"):
        claim("companion p.6, p.8 Eq.8.2; memo O1", "raw hook one phase late corrupts ID 7 from 00 00 10 41 to 00 00 80 FF; first differing byte at logical offset 4*7+2 = 30 (lane 2)",
              frb.get("slot_id") == 7 and frb.get("dense_token_offset") == 30 and frb.get("true_le") == "00001041"
              and frb.get("recorded_le") == "000080ff")
        claim("brief 1", "earliest raw discrepancy despite correct final ID", exp["verdict"] == "M" and first.get("phase") == "C0_raw"
              and oe[0]["y"] == ue[0]["y"])
    if cid == "F2.forced_banned":
        claim("brief 2; companion Eq.4.3", "independently reconstructed final support is empty; M although argmax returns an integer",
              exp["verdict"] == "M" and ("nonempty" in checks) and isinstance(ue[0]["y"], int) and ue[0]["allowed_size"] == 0)
    if cid == "F3.tie_last":
        claim("brief 3", "selection failure identified separately", "first_max_tie" in checks and "page_mask" not in checks)
    if cid == "F3.zero_flip":
        claim("brief 3", "byte-preservation failure identified separately from selection",
              "page_mask" in checks and "first_max_tie" not in checks and "first_max" not in checks)
    if cid == "F4.a_inverted_ancestry":
        claim("memo 4.1 sub-case 4a", "M, first_divergent_phase C0_raw, conflicts {phase_cut_binding_mismatch, non_monotonic_capture_seq}, missing []",
              exp["verdict"] == "M" and first.get("phase_from") == "C0_raw" and {"phase_cut_binding", "capture_seq_order"} <= checks
              and not exp["missing"])
    if cid == "F4.b_duplicate_copy":
        holds = (exp["verdict"] == "M" and first.get("phase") == "C0_raw" and checks == {"duplicate_copy_id", "phase_cut_binding"}
                 and not exp["missing"])
        claim("memo 4.1 sub-case 4b", "M, first_divergent_phase C0_raw, conflicts exactly {duplicate_copy_event_id, phase_cut_binding_mismatch}, missing []",
              holds, "Oracle: verdict M and missing [] agree.  The C0 record alone is self-consistent; the duplicate is first witnessed at C1, so the "
                     "first discrepancy is the interval C0_raw..C1_post_rep.  event_seq(C0)=event_seq(C1)=1 also violates the memo's own strict order "
                     "rule, adding capture_seq_order.")
    if cid in ("F4.c_late_hook_inactive", "F4.c_swap_labels_stay"):
        claim("memo 4.1 objection; handoff p.2 blind spot", "with byte-identical r and zN no score-byte comparison detects the change",
              exp["verdict"] == "P" and g["first_record_divergence"] is not None)
    if cid == "F4.d_swap_unverifiable":
        claim("handoff p.7 row 4", "an unverifiable cut remains U", exp["verdict"] == "U")
    if cid == "F4.e_drop_zN":
        claim("handoff p.7 row 4; companion p.12", "missing zN gives U", exp["verdict"] == "U")
    if cid == "F4.h_false_complete":
        claim("handoff p.5/p.7; companion p.12", "short vector falsely declared complete is M", exp["verdict"] == "M" and "length_contradiction" in checks)
    if cid in ("F4.g_interrupt_after_differing",):
        claim("companion p.12", "first differing captured word followed by truncation: M with missing tail retained",
              exp["verdict"] == "M" and any(m["check"] == "truncated_tail" for m in exp["missing"]))
    if cid in ("F4.i_missing_and_short", "F4.j_missing_and_changed"):
        claim("brief 4", "M takes precedence and the missing list is preserved",
              exp["verdict"] == "M" and any(m["phase"] == "C1_post_rep" and m["check"] == "present" for m in exp["missing"]))
    if cid == "F5.later_id":
        claim("brief 5", "five price IDs kept; later public divergence gives M", exp["verdict"] == "M" and first.get("phase") == "PUB"
              and all(v == "P" for v in exp["row_verdicts"].values()))
    if cid == "F5.terminal_reason":
        claim("brief 5", "changed terminal reason gives M", exp["verdict"] == "M" and first.get("phase") == "TERM")
    if cid == "F5.interrupt_after_field":
        claim("brief 5", "interrupted clean run before terminal gives U", exp["verdict"] == "U"
              and any(m["phase"] == "TERM" for m in exp["missing"]))
    if cid == "F6.alias_end":
        claim("memo O2(a)", "aliased raw capture fails finiteness first at EOS slot 1: 8.0 -> -inf, first differing lane 2, offset 4*1+2 = 6",
              first.get("slot_id") == 1 and frb.get("dense_token_offset") == 6 and frb.get("lane_from_word_pair") == 2)
        claim("memo O2(a)", "offsets 6 and 7 (lanes 2, 3) are the lanes any finite word must differ in",
              frb.get("guaranteed_lanes_without_true_word") == [2, 3])
    if cid == "F6.zN_alias_late":
        claim("memo O2(a)", "equivalently z_{N,0}[1] fails at C1 if the race occurs after the page guard",
              first.get("phase") == "C1_post_rep" and first.get("slot_id") == 1)
    if cid == "F7a.valid":
        u1 = ue[1]
        claim("memo 4.2 7a", "true stock advances cursor 4 -> 5 and (m, ell) (1,3) -> (1,4); A_P,1 = {PAGE}; y_1 = 128827",
              u1["entry_state"] == {"marker_cum": 1, "scanned": 4, "page_len": 3}
              and u1["exit_state"] == {"marker_cum": 1, "scanned": 5, "page_len": 4}
              and u1["page_support"] == {"kind": "only", "ids": [PAGE_ID]} and u1["y"] == PAGE_ID)
    if cid in ("F7a.reset_recorded", "F7a.reset_unrecorded"):
        o1 = oe[1]
        claim("memo 4.2 7a", "defective cursor reset gives (m, ell) = (2, 4), A_P,1 = {EOS}, y_1 = 1",
              o1["exit_state"]["marker_cum"] == 2 and o1["exit_state"]["page_len"] == 4
              and o1["page_support"] == {"kind": "only", "ids": [1]} and o1["y"] == 1)
        if cid == "F7a.reset_recorded":
            claim("memo 4.2 7a", "M with first_divergent_phase B1_entry_state and a C2_post_page support/y conflict",
                  exp["verdict"] == "M" and first.get("phase") == "B_entry" and first.get("row") == 1
                  and any(x["phase"] == "C2_post_page" and x["row"] == 1 for x in exp["conflicts"]))
        else:
            claim("memo 4.2 7a", "M with first_divergent_phase B1_entry_state",
                  exp["verdict"] == "M" and first.get("phase") == "B_entry" and first.get("row") == 1,
                  "When the record omits the cursor, B1 is missing (U) rather than conflicting; the first witnessed conflict is at C2 row 1.")
    if cid == "F7a.reinvoke_idempotent":
        o1 = oe[1]
        claim("this suite", "re-invoking the page guard with the same history and current cursor leaves state and bytes unchanged",
              o1["reinvocation"] and o1["reinvocation"]["state_unchanged"] and o1["reinvocation"]["bytes_unchanged"])
    if cid == "F7b.out":
        claim("memo 4.2 7b-out", "B(H) = {} , z_N[7] = 9.0, y = 7", ue[0]["repetition_ban"] == [] and ue[0]["y"] == 7)
    if cid == "F7b.in":
        claim("memo 4.2 7b-in", "B(H) = {7}, z_N[7] = -inf, y = 8", ue[0]["repetition_ban"] == [7] and ue[0]["y"] == 8)
    if cid == "F7b.prompt":
        claim("memo 4.2 7b-prompt", "B(H) = {}, z_N[7] = 9.0, y = 7", ue[0]["repetition_ban"] == [] and ue[0]["y"] == 7)
    if cid in ("F7b.out_window_minus1", "F7b.in_window_plus1", "F7b.prompt_included"):
        claim("memo 4.2 7b", "off-by-one window or prompt inclusion yields M at C1_post_rep, byte offset 30",
              exp["verdict"] == "M" and first.get("phase") == "C1_post_rep" and first.get("dense_token_offset") == 30)
    if cid == "F7c.pos_inf_raw":
        claim("memo 4.2 7c(i)", "M raw non-finite +inf at C0_raw slot 0 (00 00 80 7F) despite argmax = 0",
              exp["verdict"] == "M" and first.get("phase") == "C0_raw" and first.get("slot_id") == 0
              and first.get("observed_le") == "0000807f" and ue[0]["y"] == 0)
    if cid == "F7c.neg_zero_pass":
        claim("memo 4.2 7c(ii)", "valid pass requires y = 0 and z[0] == 00 00 00 80",
              exp["verdict"] == "P" and ue[0]["y"] == 0 and extra.get("z0_le") == "00000080")
    if cid == "F7c.neg_zero_canonicalised":
        claim("memo 4.2 7c(ii)", "canonicalising z[0] to +0.0 yields M at lane 3",
              exp["verdict"] == "M" and first.get("lane") == 3 and first.get("slot_id") == 0)
    if cid == "F7c.neg_zero_pick_last":
        claim("memo 4.2 7c(ii)", "picking y = 2 yields M firstmax_tie_violation", exp["verdict"] == "M" and "first_max_tie" in checks)
    return C


PAGE_ID = 128827


# ---------------------------------------------------------------------- facts

def global_facts(native_source=None):
    F = {}
    # page_len semantics (native lines 588-596)
    st = {"marker_cum": 1, "scanned": 4, "page_len": 3}
    H = [PAGE_ID, 10, 11, 12, 13, PAGE_ID, 14]
    after = page_step(st, H, PAGE_ID)
    F["page_len_suffix_semantics"] = {
        "state_before": st, "history": H, "new_tail": H[4:], "state_after": after,
        "additive_alternative_page_len": st["page_len"] + 3,
        "statement": "When the new tail contains PAGE, page_len becomes the number of tail tokens after the last PAGE (here 1), not the old value plus the tail length (6). Without a PAGE in the tail, the tail length is added.",
        "holds": after["page_len"] == 1 and after["marker_cum"] == 2 and after["scanned"] == 7}
    nomark = page_step({"marker_cum": 1, "scanned": 4, "page_len": 3}, [PAGE_ID, 10, 11, 12, 13, 14], PAGE_ID)
    F["page_len_additive_without_marker"] = {"state_after": nomark, "holds": nomark["page_len"] == 5}
    same = page_step(after, H, PAGE_ID)
    F["page_scan_idempotent_when_cursor_current"] = {"state": after, "rescanned": same, "holds": same == after}
    reset = page_step({"marker_cum": 1, "scanned": 0, "page_len": 3}, [PAGE_ID, 10, 11, 12, 13], PAGE_ID)
    F["page_scan_not_idempotent_after_cursor_reset"] = {
        "state_after_reset_scan": reset, "native_state_after": {"marker_cum": 1, "scanned": 5, "page_len": 4},
        "holds": reset == {"marker_cum": 2, "scanned": 5, "page_len": 4}}
    # word lanes
    pairs = [("9.0", "-inf"), ("8.0", "-inf"), ("4.0", "-inf"), ("+0.0", "-inf"), ("-0.0", "+0.0"),
             ("+inf", "-inf"), ("5.0", "5.5")]
    F["first_differing_lane_from_word_pairs"] = [
        {"a": a, "b": b, "a_le": le_hex(bits_of(a)), "b_le": le_hex(bits_of(b)), "lane": lane_diff(bits_of(a), bits_of(b))}
        for a, b in pairs]
    F["lanes_guaranteed_vs_any_finite"] = {
        "-inf": guaranteed_lanes_vs_finite(SENT), "+inf": guaranteed_lanes_vs_finite(0x7F800000),
        "nan": guaranteed_lanes_vs_finite(0x7FC00000),
        "statement": "A finite word must differ from a non-finite word in lane 2 (bit 23) or lane 3 (bits 24-30); either alone can coincide; lanes 0-1 can coincide or differ. Exact first lane requires the actual word."}
    # verdict lattice (companion Eq. 12.2)
    counts = {"M": 0, "U": 0, "P": 0}
    for combo in itertools.product("MUP", repeat=5):
        counts["M" if "M" in combo else ("U" if "U" in combo else "P")] += 1
    F["five_row_lattice"] = {"counts": counts, "holds": counts == {"M": 211, "U": 31, "P": 1}}
    if native_source:
        b = open(native_source, "rb").read()
        lines = b.split(b"\n")

        def seg(a, z):
            return sha(b"\n".join(lines[a - 1:z]))
        F["native_source"] = {
            "path_basename": os.path.basename(native_source), "sha256": sha(b), "bytes": len(b),
            "pinned_sha256": "f6df813cef23cc28b1daca40fd8cb20740d05a238e7b9dfa2334531fdcf39f1f",
            "matches_pin": sha(b) == "f6df813cef23cc28b1daca40fd8cb20740d05a238e7b9dfa2334531fdcf39f1f",
            "segments_sha256": {"583-605 _uocr_page_count_guard": seg(583, 605),
                                "608-623 _uocr_no_repeat_ngram": seg(608, 623),
                                "1166-1182 decode step": seg(1166, 1182)},
            "method": "bytes read and hashed only; module not imported or executed"}
    return F


# ---------------------------------------------------------------------- driver

def expected_contract(sc, run_id):
    return {"schema": "wp0043.contract.v1", "run_id": run_id, "vocab": sc["vocab"], "dtype": "float32",
            "byteorder": "little", "sentinel_le": "000080ff", "eos_id": sc["eos_id"], "page_id": sc["page_id"],
            "prompt_ids": sc["prompt_ids"], "page_count_guard": sc.get("page_count_guard", True),
            "max_page_tokens": sc["max_page_tokens"], "ngram": sc["ngram"],
            "generated_prefix": sc["generated_prefix"], "max_new_tokens": sc["max_new_tokens"],
            "rows": sc["rows"], "phase_map": dict(REQUIRED_CUT), "required_origin": "native_copy"}


def classify(exp, g):
    if not g["fault_injected"]:
        return "control_pass" if exp["verdict"] == "P" else ("faithful_record_invalid" if exp["verdict"] == "M" else "faithful_record_unmeasured")
    return {"M": "fault_detected", "U": "fault_unmeasured", "P": "blind_spot_false_pass"}[exp["verdict"]]


def expect_case(case, gen_dir):
    sc = case["scenario"]
    V = Vocab(sc["vocab"])
    problems = []
    raws = []
    for spec in sc["raw"]:
        v = [bits_of(spec.get("default", "0.0"))] * V.n
        for t, val in spec.get("values", {}).items():
            v[V.index[int(t)]] = bits_of(val)
        data = encode(v)
        if sha(data) != spec["sha256"]:
            problems.append("raw input digest differs at step %d" % spec["step"])
        p = os.path.join(gen_dir, *spec["input"].split("/"))
        if not os.path.exists(p) or open(p, "rb").read() != data:
            problems.append("raw input file differs at step %d" % spec["step"])
        raws.append(v)
    e = sc["prompt_ids"].count(sc["page_id"]) if sc.get("page_count_guard", True) else 0
    if sc.get("initial_guard_state") != page_replay(sc["generated_prefix"], e, sc["page_id"])[0]:
        problems.append("scenario initial_guard_state differs from native replay")
    cpath = os.path.join(gen_dir, *case["contract_path"].split("/"))
    cbytes = open(cpath, "rb").read()
    if json.loads(cbytes) != expected_contract(sc, case["run_id"]):
        problems.append("contract differs from scenario projection")
    unt = simulate(sc, raws, [])
    obs = simulate(sc, raws, case["injection"])
    rows, tags = predict(sc, obs, case["injection"])
    ev, blobs = evidence_json(case["run_id"], sha(cbytes), unt, obs, rows)
    exp = RefScorer(cbytes, ev, lambda h: blobs.get(h)).score()
    # cross-check the generator's reference evidence
    ref = json.loads(open(os.path.join(gen_dir, *case["reference_evidence_path"].split("/")), "rb").read())
    equal = ref == ev
    diffs = []
    if not equal:
        for arm in ("untouched", "observed"):
            if ref["arms"].get(arm, {}).get("public") != ev["arms"][arm]["public"]:
                diffs.append(arm + ".public")
        rr, er = ref["arms"]["observed"].get("rows", []), ev["arms"]["observed"]["rows"]
        if len(rr) != len(er):
            diffs.append("rows.count")
        for a, b in zip(rr, er):
            for kk in set(a) | set(b):
                if a.get(kk) != b.get(kk):
                    diffs.append("row%s.%s" % (b.get("row"), kk))
    for h in blobs:
        p = os.path.join(gen_dir, "blobs", h + ".bin")
        if not os.path.exists(p):
            diffs.append("blob missing " + h)
    rescored = RefScorer(cbytes, ref, blob_loader(os.path.join(gen_dir, "blobs"))).score()
    g = ground(sc, unt, obs, rows, tags, case["injection"])
    extra = {}
    if rows and "C2_post_page" in rows[0]["captures"]:
        extra["z0_le"] = le_hex(rows[0]["captures"]["C2_post_page"]["bits"][0])
    out = {
        "schema": "wp0043.expected.v1", "case_id": case["case_id"], "run_id": case["run_id"],
        "fixture": case["fixture"], "subcase": case["subcase"], "title": case["title"],
        "expected": exp,
        "classification": classify(exp, g),
        "ground": g,
        "prefix_reachability": prefix_reachability(sc),
        "consistency": {"inputs_and_contract_problems": problems, "reference_evidence_equal_prediction": equal,
                        "reference_evidence_differences": diffs, "reference_evidence_rescored_equal": rescored == exp},
    }
    out["claims"] = claims_for(case["case_id"], exp, g, extra)
    return out


def cmd_expect(a):
    cases = [json.loads(l) for l in open(os.path.join(a.generated, "cases.jsonl"), "rb").read().decode("ascii").splitlines() if l]
    lines = []
    summary = {"cases": 0, "verdicts": {"M": 0, "U": 0, "P": 0}, "classification": {}, "consistency_failures": [],
               "claims": {"held": 0, "not_held": []}}
    for case in cases:
        out = expect_case(case, a.generated)
        lines.append(canon(out))
        summary["cases"] += 1
        summary["verdicts"][out["expected"]["verdict"]] += 1
        summary["classification"][out["classification"]] = summary["classification"].get(out["classification"], 0) + 1
        con = out["consistency"]
        if con["inputs_and_contract_problems"] or not con["reference_evidence_equal_prediction"] \
                or con["reference_evidence_differences"] or not con["reference_evidence_rescored_equal"]:
            summary["consistency_failures"].append(case["case_id"])
        for cl in out["claims"]:
            if cl["holds"]:
                summary["claims"]["held"] += 1
            else:
                summary["claims"]["not_held"].append({"case_id": case["case_id"], "claim": cl["claim"], "note": cl["note"]})
        print("%-34s %s %-26s first=%s" % (case["case_id"], out["expected"]["verdict"], out["classification"],
                                          _fmt_first(out["expected"]["first"])))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "wb") as fh:
        fh.write(b"".join(lines))
    facts = global_facts(a.native_source)
    facts["summary"] = summary
    with open(a.facts, "wb") as fh:
        fh.write(json.dumps(facts, sort_keys=True, indent=1).encode("ascii") + b"\n")
    print("cases=%d M=%d U=%d P=%d consistency_failures=%d claims_held=%d claims_not_held=%d" % (
        summary["cases"], summary["verdicts"]["M"], summary["verdicts"]["U"], summary["verdicts"]["P"],
        len(summary["consistency_failures"]), summary["claims"]["held"], len(summary["claims"]["not_held"])))
    return 0 if not summary["consistency_failures"] else 3


def _fmt_first(f):
    if not f:
        return "-"
    span = f["phase"] if f["phase_from"] == f["phase"] and f["row_from"] == f["row"] else "%s..%s" % (f["phase_from"], f["phase"])
    return "row%s/step%s/%s/%s/%s%s" % (f["row"], f["step"], span, f["object"], f["check"],
                                        "" if f["slot_id"] is None else "@%s" % f["slot_id"])


def cmd_score(a):
    cb = open(a.contract, "rb").read()
    ev = json.loads(open(a.evidence, "rb").read())
    res = RefScorer(cb, ev, blob_loader(a.blobs)).score()
    sys.stdout.write(json.dumps(res, sort_keys=True) + "\n")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="WP-0043 independent oracle")
    sub = ap.add_subparsers(dest="cmd", required=True)
    here = os.path.dirname(os.path.abspath(__file__))
    e = sub.add_parser("expect")
    e.add_argument("--generated", default=os.path.join(here, "generated"))
    e.add_argument("--out", default=os.path.join(here, "expected", "expected.jsonl"))
    e.add_argument("--facts", default=os.path.join(here, "expected", "facts.json"))
    e.add_argument("--native-source", default=None)
    s = sub.add_parser("score")
    s.add_argument("--contract", required=True)
    s.add_argument("--evidence", required=True)
    s.add_argument("--blobs", required=True)
    a = ap.parse_args(argv)
    return cmd_expect(a) if a.cmd == "expect" else cmd_score(a)


if __name__ == "__main__":
    sys.exit(main())
