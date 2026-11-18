"""WP-0017 Stage A1 normalization and decision (eld-rd-reviewer), synchronized with Astra design 1fad21c.

Stdlib only, CPU only, no truth keys. Pure functions over a normalized A1 result set, plus a CLI that first
proves the actual A1 run tree is unchanged since its committed blind inventory, then loads the normalized
results built by a bound adapter, which cites every source file by its inventory digest.

Independent implementation of design/PROTOCOL.md (fe915bba...). design/rules.py (678f27d5...) is loaded
from its pinned blob ONLY to cross-check restoration ranking and pair eligibility: any disagreement is a
reported failure, never silently resolved.

Revision by the continuation session (common.OPERATOR), before any A1 output existed, to the coordinator's
actual initial wave (prepare_a1.py 74b24a1f, check_endpoints.py edcb4184): SIXTEEN configurations, i.e. the
design's fourteen unique bit vectors plus two extra endpoint controls. 000000 is run twice (genuine `native`
and switch-harness `all_off`), 111111 twice (genuine `carbon_bf16` and harness `all_on`), then the twelve
one-factor harness rows. All four endpoints must reproduce their complete frozen arrays before any
attribution. One-factor contrasts are instrument-matched (additions against `all_off`, removals against
`all_on`, as the coordinator's joint design read requires); genuine-endpoint contrasts, harness overheads and
harness-versus-genuine probe gaps are reported alongside. The pair noise floor E_w follows design/rules.py
with native := all_off and full := all_on; a conservative floor that also includes genuine-endpoint repeat
and harness gaps is reported as a sensitivity and never changes the rule.

Normalized result (configuration ids and bit order follow design/rules.py:matrix plus the two controls):
 {"configurations": [CONF, ...], "source_files": {rel: sha256}, "infrastructure_errors": [str, ...],
  "coordinator_endpoint_check": null|{"passed": bool, "checks": [...]}}
 CONF  = {"id": "native"|"all_off"|"carbon_bf16"|"all_on"|"add_S1a"|"remove_S2"|"remove_S1a+S2", "bits": "010000",
          "implementation": "genuine_native"|"genuine_carbon"|"switch_harness", "aliases": null|"native"|"carbon_bf16",
          "stream_cadence_label": str|null,          # required when S3 on and S0 off
          "windows": {"019": WIN, "037": WIN}}
 WIN   = {"free": {"token_ids": [int], "seconds": float, "output_tokens": int, "forwards": int,
                   "counters": {str: int}, "instrumented": false},
          "probes": {"native_prefix": [PROBE, ...passes], "free_prefix": [PROBE or null, ...]}}  # free_prefix on 037
 PROBE = {"prefix_sha256": str, "prefix_tokens": int,
          "branches": {"native": {"ids": [int], "logprobs": [fp32]}, "carbon_bf16": {...}},
          "first_divergence": int, "top5": [[id, fp32 logit], ...5], "competing_logits": {"native": x, "carbon_bf16": y},
          "guard_status": "finite"|"masked"|"nonfinite",
          "timing": {"prefill_ms": x, "decode_ms_per_token": y, "decode_tokens": n, "interval": str}}
"""
import argparse
import itertools
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (BLOCK_ID, FORK_ID, NUMERIC_FLOOR_NATS, PAGE_ID, Check, Vocab, blob_module, disk, ids_sha,  # noqa
                    load, sha_file, utc, write_new)

SWITCHES = ("S0", "S1a", "S1b", "S1c", "S2", "S3")
WINDOWS = ("019", "037")
NATIVE_IDS = {"019": "I08O1-388", "037": "8OI10-774"}
CARBON_IDS = {"019": "108O1-388", "037": "80I10-774"}
AUDIT_KEY = {"019": "window-019", "037": "window-037"}
SITE_PAGE_INDEX = {"019": 2, "037": 0}  # page 21 is the third page of window 019; page 37 the first of 037
LABEL = b"Inspection "                  # fixed prose text immediately preceding the ID in the frozen block
LINE_ORDINAL = 1                        # public paths page/21/line/2 and page/37/line/2: second raw block


def bits(enabled):
    return "".join("1" if s in enabled else "0" for s in SWITCHES)


def matrix():
    """The design's fourteen unique bit vectors (design/rules.py:matrix ids)."""
    rows = {"native": bits(()), "carbon_bf16": bits(SWITCHES)}
    rows.update(("add_" + s, bits((s,))) for s in SWITCHES)
    rows.update(("remove_" + s, bits(set(SWITCHES) - {s})) for s in SWITCHES)
    return rows


GENUINE = {"native": "genuine_native", "carbon_bf16": "genuine_carbon"}
HARNESS_ENDPOINTS = {"all_off": "native", "all_on": "carbon_bf16"}   # harness control -> genuine counterpart
ENDPOINTS = ("native", "all_off", "carbon_bf16", "all_on")
FROZEN_ARM = {"native": "native", "all_off": "native", "carbon_bf16": "carbon_bf16", "all_on": "carbon_bf16"}
BASE_ADD, BASE_REMOVE = "all_off", "all_on"                           # instrument-matched contrast bases


def initial_wave():
    """Sixteen configurations of the coordinator's initial wave: 14 unique bit vectors + 2 endpoint controls."""
    rows = dict(matrix())
    rows.update(all_off=bits(()), all_on=bits(SWITCHES))
    return rows


def expected_implementation(cid, r):
    if cid in GENUINE:
        return r.get("implementation") == GENUINE[cid] and r.get("aliases") is None
    if cid in HARNESS_ENDPOINTS:   # a harness control may alias its genuine counterpart, which must then be recorded
        return (r.get("implementation") == "switch_harness" and r.get("aliases") is None) or \
               (r.get("implementation") == GENUINE[HARNESS_ENDPOINTS[cid]] and r.get("aliases") == HARNESS_ENDPOINTS[cid])
    return r.get("implementation") == "switch_harness"


def removal_of(cid):
    return tuple(cid[len("remove_"):].split("+")) if cid.startswith("remove_") else None


def removal_id(switches):
    return "remove_" + "+".join(sorted(switches, key=SWITCHES.index))


# ---- structural field locator (never searches for either competing value) -----------------------------

def pages(ids):
    starts = [i for i, t in enumerate(ids) if t == PAGE_ID]
    return [ids[s:e] for s, e in zip(starts, starts[1:] + [len(ids)])], starts


def blocks(vocab, page):
    """[(ordinal, header_bytes, content_bytes|None, content_token_start, content_token_ids)] of one page."""
    out = []
    starts = [k for k, t in enumerate(page) if t == BLOCK_ID]
    for n, s in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(page)
        seg = page[s:end]
        if FORK_ID in seg:
            f = seg.index(FORK_ID)
            head, body = seg[1:f], seg[f + 1:]
            out.append((n, b"".join(vocab.piece(t) for t in head), b"".join(vocab.piece(t) for t in body), s + f + 1, body))
        else:
            out.append((n, b"".join(vocab.piece(t) for t in seg[1:]), None, None, []))
    return out


def header_type(head):
    return head.split(b"[")[0].decode("utf-8", errors="backslashreplace")


def freeze_locator(vocab, native_ids, w):
    """Unique structural locator from the ORIGINAL native history: site page, raw block ordinal from the public
    path line/2 (ordinal 1), the block's header type, the fixed prose label and its byte offset. The page header
    ('Inspection register') also begins with the label, so the ordinal and header type are part of the locator."""
    pg, starts = pages(native_ids)
    page = pg[SITE_PAGE_INDEX[w]]
    bl = blocks(vocab, page)
    n, head, body, cstart, _ = bl[LINE_ORDINAL]
    if body is None or not body.startswith(LABEL):
        raise SystemExit(f"{w}: frozen native block {LINE_ORDINAL} does not carry the label")
    return dict(window=w, site_page_index=SITE_PAGE_INDEX[w], block_ordinal=n, header_type=header_type(head),
                label=LABEL.decode(), byte_offset=len(LABEL), content_window_start=starts[SITE_PAGE_INDEX[w]] + cstart,
                frozen_value=body[len(LABEL):].split(b"\n")[0].decode(), delimiter="\\n or end of block",
                labelled_ordinals_in_frozen_page=[b[0] for b in bl if b[2] is not None and b[2].startswith(LABEL)])


def field(vocab, ids, loc):
    """Ordinary free ID at the frozen site: (status, value, info).
    status: ok / missing (page or block absent) / malformed (no fork) / moved (label or header type not at the
    frozen ordinal) / abstention (empty value). Never searches for either competing value."""
    pg, starts = pages(ids)
    k = loc["site_page_index"]
    if len(pg) <= k:
        return "missing", None, dict(reason="site page absent")
    bl = blocks(vocab, pg[k])
    if len(bl) <= loc["block_ordinal"]:
        return "missing", None, dict(reason=f"only {len(bl)} blocks on the site page")
    n, head, body, cstart, ctoks = bl[loc["block_ordinal"]]
    if body is None:
        return "malformed", None, dict(reason="field block has no <FORK>")
    labelled = [b[0] for b in bl if b[2] is not None and b[2].startswith(LABEL)]
    if not body.startswith(LABEL) or header_type(head) != loc["header_type"]:
        return "moved", None, dict(reason=f"block {n} header {header_type(head)!r} / label present "
                                          f"{body.startswith(LABEL)}; labelled ordinals {labelled}")
    value = body[len(LABEL):].split(b"\n")[0]
    info = dict(block_ordinal=n, content_window_start=starts[k] + cstart, content_tokens=ctoks, labelled_ordinals=labelled)
    if not value.strip():
        return "abstention", "", dict(info, reason="empty field")
    return "ok", value.decode("utf-8", errors="backslashreplace"), info


def free_boundary(vocab, ids, loc, boundary_bytes):
    """Window index of the token boundary inside the anchored block whose decoded content length equals the
    audited common-prefix byte length (019: 'Inspection' = 10, 037: 'Inspection ' = 11); None if unalignable."""
    status, _, info = field(vocab, ids, loc)
    if status not in ("ok", "abstention"):
        return None
    pos = 0
    for j, t in enumerate(info["content_tokens"]):
        if pos == boundary_bytes:
            return info["content_window_start"] + j
        pos += len(vocab.piece(t))
        if pos > boundary_bytes:
            return None
    return None


# ---- probe arithmetic ----------------------------------------------------------------------------------

def ell(branch):
    return math.fsum(branch["logprobs"])


def D(probe):
    """D = ell(native ID) - ell(Carbon ID) in nats, no length normalization; None if guard/coverage not finite."""
    if probe is None or probe.get("guard_status") != "finite":
        return None
    v = ell(probe["branches"]["native"]) - ell(probe["branches"]["carbon_bf16"])
    return v if math.isfinite(v) else None


def greedy(probe):
    top, fd = probe["top5"][0][0], probe["first_divergence"]
    n, c = probe["branches"]["native"]["ids"], probe["branches"]["carbon_bf16"]["ids"]
    return "native" if top == n[fd] else ("carbon_bf16" if top == c[fd] else "other")


def probe_D(table, cid, key, k=0):
    passes = table[cid]["probes"].get(key) or []
    return passes[k]["D"] if len(passes) > k and passes[k] is not None else None


# ---- binding -------------------------------------------------------------------------------------------

def anchors(audit, manifest, vocab):
    locs = {w: freeze_locator(vocab, manifest[w]["native"], w) for w in WINDOWS}
    spans = {w: {m: [t["id"] for t in audit["windows"][AUDIT_KEY[w]]["divergence"]["span_to_identifier_end"][m]]
                 for m in ("native", "carbon_bf16")} for w in WINDOWS}
    pref = {w: audit["windows"][AUDIT_KEY[w]]["a1_prefixes"]["native_prefix_to_boundary"] for w in WINDOWS}
    bbytes = {w: len(b"".join(vocab.piece(t["id"]) for t in
                             audit["windows"][AUDIT_KEY[w]]["divergence"]["common_line_prefix"])) for w in WINDOWS}
    return locs, spans, pref, bbytes


def bind(norm, audit, manifest, vocab, check):
    want = initial_wave()
    by = {}
    for r in norm["configurations"]:
        check(r["id"] not in by, f"duplicate configuration {r['id']}")
        by[r["id"]] = r
    locs, spans, pref, bbytes = anchors(audit, manifest, vocab)
    for cid, r in by.items():
        rem = removal_of(cid)
        expect = want.get(cid) or (bits(set(SWITCHES) - set(rem)) if rem and len(rem) == 2 else None)
        check(expect is not None and r["bits"] == expect, f"{cid}: bit vector differs from its id")
        check(expected_implementation(cid, r), f"{cid}: implementation/alias label {r.get('implementation')!r}/"
                                               f"{r.get('aliases')!r} does not fit its role")
        on = {s for s, b in zip(SWITCHES, r["bits"]) if b == "1"}
        if "S3" in on and "S0" not in on:
            check(bool(r.get("stream_cadence_label")), f"{cid}: S3 with S0 off must label deferred ordered callbacks")
        for w in WINDOWS:
            win = r["windows"][w]
            check(win["free"].get("instrumented") is False, f"{cid}/{w}: ordinary free timing must be uninstrumented")
            check(isinstance(win["free"].get("counters"), dict), f"{cid}/{w}: implementation counters present")
            if cid in GENUINE:   # genuine controls: probes optional (the matrix's 000000/111111 rows are the harness)
                win["probes"].setdefault("native_prefix", [])
                continue
            check(len(win["probes"].get("native_prefix") or []) >= 1, f"{cid}/{w}: native-prefix probe present")
            if w == "037":
                check("free_prefix" in win["probes"], f"{cid}/037: free-prefix probe present (or explicit null)")
            for name, passes in win["probes"].items():
                for p in passes:
                    if p is None:
                        continue
                    check(p["branches"]["native"]["ids"] == spans[w]["native"]
                          and p["branches"]["carbon_bf16"]["ids"] == spans[w]["carbon_bf16"],
                          f"{cid}/{w}/{name}: branch spans = audited spans")
                    check(all(len(p["branches"][m]["logprobs"]) == len(spans[w][m]) for m in spans[w]),
                          f"{cid}/{w}/{name}: one conditional log probability per span token")
                    check(p["first_divergence"] == 0, f"{cid}/{w}/{name}: first divergence at span token 0")
                    z = [x[1] for x in p["top5"]]
                    fin = p.get("guard_status") == "finite"
                    check(len(z) == 5 and (not fin or z == sorted(z, reverse=True)), f"{cid}/{w}/{name}: sorted top five")
                    cl = p.get("competing_logits") or {}
                    check(set(cl) == {"native", "carbon_bf16"} and
                          all(isinstance(v, (int, float)) or (v is None and not fin) for v in cl.values()),
                          f"{cid}/{w}/{name}: both competing first-divergence logits recorded, even below rank 5 "
                          "(null only with a non-finite guard status)")
                    check(p.get("guard_status") in ("finite", "masked", "nonfinite"), f"{cid}/{w}/{name}: guard status")
                    if name == "native_prefix":
                        check(p["prefix_sha256"] == pref[w]["sha256"] and p["prefix_tokens"] == pref[w]["tokens"],
                              f"{cid}/{w}: native-prefix probe uses the frozen native prefix")
                    else:
                        b = free_boundary(vocab, win["free"]["token_ids"], locs[w], bbytes[w])
                        check(b is not None and p["prefix_tokens"] == b
                              and p["prefix_sha256"] == ids_sha(win["free"]["token_ids"][:b]),
                              f"{cid}/{w}: free-prefix probe uses this configuration's own aligned prefix")
    return by, locs, bbytes


# ---- decision ------------------------------------------------------------------------------------------

def decide(by, audit, manifest, vocab, locs, bbytes, rules=None, coordinator_check=None):
    out = dict(locators=locs, contrast_bases=dict(
        additions=BASE_ADD, removals=BASE_REMOVE, genuine_reference=["native", "carbon_bf16"],
        note="instrument-matched switch-harness endpoints; genuine-endpoint contrasts reported separately"))
    wave = initial_wave()
    out["initial_wave"] = dict(configurations=len(wave), unique_bit_vectors=len(set(wave.values())),
                               endpoint_controls=list(ENDPOINTS))
    if not all(c in by for c in wave):
        out.update(outcome="INCOMPLETE_MATRIX", missing=[c for c in wave if c not in by])
        return out
    parity = {}
    for cid in ENDPOINTS:
        arm = FROZEN_ARM[cid]
        for w in WINDOWS:
            got, exp = by[cid]["windows"][w]["free"]["token_ids"], manifest[w][arm]
            first = next((i for i, (x, y) in enumerate(zip(got, exp)) if x != y), None)
            if first is None and len(got) != len(exp):
                first = min(len(got), len(exp))
            parity[f"{cid}:{w}"] = dict(equal=got == exp, frozen_arm=arm, implementation=by[cid]["implementation"],
                                        aliases=by[cid].get("aliases"), tokens=[len(got), len(exp)], first_mismatch=first)
    out["endpoint_parity"] = parity
    if coordinator_check is not None:
        mine = {(k.split(":")[0], int(k.split(":")[1])): v["equal"] for k, v in parity.items()}
        theirs = {(c["mode"], c["first_page"]): not c["errors"] for c in coordinator_check.get("checks", [])}
        out["coordinator_endpoint_check"] = dict(passed=coordinator_check.get("passed"), windows=len(theirs),
                                                 agrees=theirs == mine and coordinator_check.get("passed") == all(mine.values()))
    if not all(v["equal"] for v in parity.values()):
        out.update(outcome="ENDPOINT_PARITY_FAILED", attribution="withheld until a harness fix has a new source binding")
        return out
    table = {}
    for cid, r in by.items():
        row = dict(bits=r["bits"], fields={}, probes={}, free={}, probe_timing={},
                   stream_cadence_label=r.get("stream_cadence_label"))
        for w in WINDOWS:
            win = r["windows"][w]
            st, val, info = field(vocab, win["free"]["token_ids"], locs[w])
            b = free_boundary(vocab, win["free"]["token_ids"], locs[w], bbytes[w])
            nat = audit["windows"][AUDIT_KEY[w]]["a1_prefixes"]["native_prefix_to_boundary"]["sha256"]
            row["fields"][w] = dict(status=st, value=val, reason=info.get("reason"),
                                    free_prefix_sha256=ids_sha(win["free"]["token_ids"][:b]) if b is not None else None,
                                    upstream_history_changed=None if b is None else ids_sha(win["free"]["token_ids"][:b]) != nat)
            row["free"][w] = dict(seconds=win["free"]["seconds"], output_tokens=win["free"]["output_tokens"],
                                  forwards=win["free"]["forwards"], counters=win["free"]["counters"])
            for name, passes in win["probes"].items():
                row["probes"][f"{w}:{name}"] = [None if p is None else dict(
                    D=D(p), ell=dict(native=ell(p["branches"]["native"]), carbon_bf16=ell(p["branches"]["carbon_bf16"])),
                    greedy=greedy(p), top5=p["top5"],
                    margin=(p["top5"][0][1] - p["top5"][1][1]) if all(isinstance(x[1], (int, float)) for x in p["top5"][:2])
                    else None,
                    competing_logits=p.get("competing_logits"), guard_status=p["guard_status"]) for p in passes]
                row["probe_timing"][f"{w}:{name}"] = [None if p is None else p.get("timing") for p in passes]
        f = row["fields"]
        row["restores_both"] = all(f[w]["status"] == "ok" and f[w]["value"] == NATIVE_IDS[w] for w in WINDOWS)
        row["anchored_id_flip"] = any(f[w]["status"] == "ok" and f[w]["value"] != NATIVE_IDS[w] for w in WINDOWS)
        row["field_failures"] = {w: f[w]["status"] for w in WINDOWS if f[w]["status"] != "ok"}
        table[cid] = row
    out["configurations"] = table

    def at(cid, w, val):
        return table[cid]["fields"][w]["status"] == "ok" and table[cid]["fields"][w]["value"] == val
    suff = {s: [w for w in WINDOWS if at(f"add_{s}", w, CARBON_IDS[w])] for s in SWITCHES}
    nec = {s: [w for w in WINDOWS if at(f"remove_{s}", w, NATIVE_IDS[w])] for s in SWITCHES}
    out["sufficiency_add_on_native"] = suff
    out["necessity_remove_from_full"] = nec

    def effect(base, k=0):
        b = {w: probe_D(table, base, f"{w}:native_prefix", k) for w in WINDOWS}
        return {cid: {w: (None if probe_D(table, cid, f"{w}:native_prefix") is None or b[w] is None
                          else probe_D(table, cid, f"{w}:native_prefix") - b[w]) for w in WINDOWS} for cid in table}
    dn = {w: probe_D(table, BASE_ADD, f"{w}:native_prefix") for w in WINDOWS}
    out["path_effect_at_native_history"] = effect(BASE_ADD)
    out["path_effect_vs_genuine_native"] = effect("native") if any(probe_D(table, "native", f"{w}:native_prefix")
                                                                     is not None for w in WINDOWS) else "genuine native not probed"
    gaps = {}
    for h, g in HARNESS_ENDPOINTS.items():
        for w in WINDOWS:
            a, b = probe_D(table, h, f"{w}:native_prefix"), probe_D(table, g, f"{w}:native_prefix")
            gaps[f"{h}-{g}:{w}"] = None if a is None or b is None else a - b
    out["harness_vs_genuine_probe_gap_nats"] = gaps
    out["history_shift_effect_037"] = {
        cid: (None if probe_D(table, cid, "037:free_prefix") is None or probe_D(table, cid, "037:native_prefix") is None
              else probe_D(table, cid, "037:free_prefix") - probe_D(table, cid, "037:native_prefix")) for cid in table}
    T = {cid: {w: table[cid]["free"][w]["seconds"] for w in WINDOWS} for cid in table}

    def diff(a, b):   # T[a] - T[b] per window and summed
        return dict({w: T[a][w] - T[b][w] for w in WINDOWS}, sum=sum(T[a][w] - T[b][w] for w in WINDOWS))
    out["ordinary_speed_s"] = dict(
        per_config={cid: dict(T[cid], sum=T[cid]["019"] + T[cid]["037"]) for cid in T},
        addition_saving={s: diff(BASE_ADD, f"add_{s}") for s in SWITCHES},
        removal_cost={s: diff(f"remove_{s}", BASE_REMOVE) for s in SWITCHES},
        addition_saving_vs_genuine_native={s: diff("native", f"add_{s}") for s in SWITCHES},
        removal_cost_vs_genuine_carbon={s: diff(f"remove_{s}", "carbon_bf16") for s in SWITCHES},
        harness_overhead=dict(all_off_minus_native=diff("all_off", "native"),
                              all_on_minus_carbon_bf16=diff("all_on", "carbon_bf16")),
        note="ordinary uninstrumented free windows; primary contrasts are instrument-matched (all_off / all_on); "
             "local marginal effects conditional on the other five settings; not additive; not a 60-page forecast")
    out["probe_speed"] = {cid: table[cid]["probe_timing"] for cid in table}
    out["stream_cadence_labels"] = {cid: table[cid]["stream_cadence_label"] for cid in table if table[cid]["stream_cadence_label"]}
    winners = [(s,) for s in SWITCHES if table[removal_id((s,))]["restores_both"]]
    out["single_removal_restorers"] = [w[0] for w in winners]
    if winners:
        sel = min(winners, key=lambda rm: (len(rm), T[removal_id(rm)]["019"] + T[removal_id(rm)]["037"],
                                           tuple(SWITCHES.index(s) for s in rm)))
        s = sel[0]
        measured = [abs(v) for v in gaps.values() if v is not None]
        coupled = any(v > NUMERIC_FLOOR_NATS for v in measured)
        unique = (len(winners) == 1 and suff[s] == list(WINDOWS) and not any(suff[t] for t in SWITCHES if t != s)
                  and not coupled)
        out.update(outcome="SINGLE_REMOVAL_RESTORES_BOTH", selected_removal=list(sel),
                   pair_screening="omitted: a single removal restores both fields",
                   causal_label=dict(
                       necessity=f"removing {s} from full restores both fields",
                       sufficiency=f"adding {s} to native flips {suff[s] or 'neither site'}",
                       other_restorers=[w[0] for w in winners if w != sel],
                       other_sufficient_additions=[t for t in SWITCHES if t != s and suff[t]],
                       unique_cause_pattern=unique,
                       backend_coupling=dict(harness_vs_genuine_gap_measured=bool(measured),
                                             gap_exceeds_floor_1e_5_nats=coupled),
                       caveat="within two fixed windows only; a cascade-confined effect or backend coupling "
                              "precludes calling a unique causal kernel"))
    else:
        out.update(screen_pairs(table, dn))
    if rules is not None:
        out["astra_rules_cross_check"] = cross_check(rules, table, out, T)
    return out


def screen_pairs(table, dn):
    """Pair eligibility per design: anchored ID flip, or repeated same-sign forced-native D change > E_w."""
    res = {}
    flipped = [s for s in SWITCHES if table[f"add_{s}"]["anchored_id_flip"]]
    d1 = {s: {w: (None if probe_D(table, f"add_{s}", f"{w}:native_prefix") is None or dn[w] is None
                  else probe_D(table, f"add_{s}", f"{w}:native_prefix") - dn[w]) for w in WINDOWS} for s in SWITCHES}
    res.update(anchored_flip_switches=flipped, first_pass_displacement_d1=d1,
               missing_or_malformed_fields={s: table[f"add_{s}"]["field_failures"] for s in SWITCHES
                                            if table[f"add_{s}"]["field_failures"]})
    n2 = {w: probe_D(table, BASE_ADD, f"{w}:native_prefix", 1) for w in WINDOWS}
    f1 = {w: probe_D(table, BASE_REMOVE, f"{w}:native_prefix", 0) for w in WINDOWS}
    f2 = {w: probe_D(table, BASE_REMOVE, f"{w}:native_prefix", 1) for w in WINDOWS}
    if any(v is None for v in list(n2.values()) + list(f2.values())):
        need = [s for s in SWITCHES if s not in flipped and any(x is not None and abs(x) > NUMERIC_FLOOR_NATS
                                                                 for x in d1[s].values())]
        res.update(outcome="PAIR_SCREENING_REPROBE_REQUIRED",
                   reprobe=dict(endpoint_repeat=[BASE_ADD, BASE_REMOVE], additions=need, windows=list(WINDOWS),
                                probe="native_prefix, fresh prefill/cache state, original inputs",
                                optional_reference=["native", "carbon_bf16"],
                                reason="no single removal restores both; additions with |d1| <= 1e-5 nats cannot qualify"))
        return res
    E = {w: max(NUMERIC_FLOOR_NATS, abs(dn[w] - n2[w]), abs(f1[w] - f2[w])) for w in WINDOWS}
    res["noise_floor_E"] = E
    res["noise_floor_rule"] = ("E_w = max(1e-5 nats, |D_all_off,1 - D_all_off,2|, |D_all_on,1 - D_all_on,2|) "
                               "(design/rules.py with native := all_off, full := all_on)")

    def qualify(floor):
        qual, reasons, missing = [], {}, []
        for s in SWITCHES:
            if s in flipped:
                qual.append(s)
                reasons[s] = "anchored free-ID flip"
                continue
            if not any(d1[s][w] is not None and abs(d1[s][w]) > floor[w] for w in WINDOWS):
                reasons[s] = "first-pass displacement within E_w on both windows"
                continue
            r2 = {w: probe_D(table, f"add_{s}", f"{w}:native_prefix", 1) for w in WINDOWS}
            if None in r2.values():
                missing.append(s)
                reasons[s] = "repeat probe missing"
                continue
            d2 = {w: r2[w] - n2[w] for w in WINDOWS}
            ok = [w for w in WINDOWS if d1[s][w] is not None and min(abs(d1[s][w]), abs(d2[w])) > floor[w]
                  and d1[s][w] * d2[w] > 0]
            reasons[s] = (f"repeated same-sign change above E_w on {ok}" if ok
                          else "repeat did not confirm a same-sign change above E_w")
            if ok:
                qual.append(s)
        return qual, reasons, missing
    qual, reasons, missing = qualify(E)
    res.update(qualifying_switches=qual, qualification_reasons=reasons)
    # Sensitivity only (never changes the rule): genuine-endpoint repeat spreads and harness-vs-genuine gaps.
    terms = {w: [] for w in WINDOWS}
    for w in WINDOWS:
        for g, h in (("native", BASE_ADD), ("carbon_bf16", BASE_REMOVE)):
            g1, g2 = (probe_D(table, g, f"{w}:native_prefix", k) for k in (0, 1))
            h1 = probe_D(table, h, f"{w}:native_prefix", 0)
            if g1 is not None and g2 is not None:
                terms[w].append(abs(g1 - g2))
            if g1 is not None and h1 is not None:
                terms[w].append(abs(g1 - h1))
    if any(terms.values()):
        Ec = {w: max([E[w]] + terms[w]) for w in WINDOWS}
        qc, _, mc = qualify(Ec)
        res["noise_floor_sensitivity"] = dict(conservative_E=Ec, qualifying_switches=qc, missing=mc,
                                              changes_qualification=qc != qual,
                                              note="reported only; the predeclared rule decides")
    else:
        res["noise_floor_sensitivity"] = "not computable: genuine endpoints were not probed"
    if missing:
        res.update(outcome="PAIR_SCREENING_REPROBE_REQUIRED",
                   reprobe=dict(additions=missing, windows=list(WINDOWS), probe="native_prefix"))
        return res
    pairs = list(itertools.combinations(qual, 2))
    res["eligible_pairs"] = [list(p) for p in pairs]
    if not pairs:
        res["outcome"] = "UNRESOLVED_NO_ELIGIBLE_PAIR"
        return res
    missing_runs = [removal_id(p) for p in pairs if removal_id(p) not in table]
    if missing_runs:
        res.update(outcome="PAIR_RUNS_REQUIRED", pair_runs=missing_runs)
        return res
    win = [p for p in pairs if table[removal_id(p)]["restores_both"]]
    if win:
        sel = min(win, key=lambda rm: (len(rm), sum(table[removal_id(rm)]["free"][w]["seconds"] for w in WINDOWS),
                                       tuple(SWITCHES.index(s) for s in rm)))
        res.update(outcome="PAIR_REMOVAL_RESTORES_BOTH", selected_removal=list(sel),
                   causal_label="interaction-compatible recovery; not a unique pairwise mechanism")
    else:
        res["outcome"] = "UNRESOLVED_NO_RESTORATION"
    return res


def cross_check(rules, table, out, T):
    """Run Astra's pinned arithmetic on the same inputs; report agreement (never overrides)."""
    cc = {}
    singles = [(s,) for s in SWITCHES]
    rows = {rm: dict(ordinary_window_seconds=[T[removal_id(rm)][w] for w in WINDOWS],
                     free_ids=[table[removal_id(rm)]["fields"][w]["value"] for w in WINDOWS],
                     probe_and_bindings_verified=True) for rm in singles}
    astra = rules.rank_restorations(singles, rows)
    mine = tuple(out["selected_removal"]) if out.get("outcome") == "SINGLE_REMOVAL_RESTORES_BOTH" else None
    cc["single_rank"] = dict(astra=list(astra) if astra else None, reviewer=list(mine) if mine else None, agree=astra == mine)
    if "noise_floor_E" in out and "qualifying_switches" in out:
        def passes(cid):
            return [[probe_D(table, cid, f"{w}:native_prefix", k) for w in WINDOWS] for k in (0, 1)]
        adds = {}
        for s in SWITCHES:
            rep = [probe_D(table, f"add_{s}", f"{w}:native_prefix", 1) for w in WINDOWS]
            adds[s] = dict(d=[probe_D(table, f"add_{s}", f"{w}:native_prefix") for w in WINDOWS],
                           anchored_id_flip=table[f"add_{s}"]["anchored_id_flip"], repeat_d=None if None in rep else rep)
        try:
            ap = [list(p) for p in rules.qualifying_pairs(passes(BASE_ADD), passes(BASE_REMOVE), adds)]
            cc["pairs"] = dict(astra=ap, reviewer=out.get("eligible_pairs"), agree=ap == out.get("eligible_pairs"))
        except (ValueError, TypeError) as exc:
            cc["pairs"] = dict(astra_error=repr(exc), reviewer=out.get("eligible_pairs"), agree=False)
    return cc


def load_manifest():
    from common import A1_MANIFEST  # noqa: PLC0415
    if sha_file(A1_MANIFEST[0]) != A1_MANIFEST[1]:
        raise SystemExit("A1 manifest digest mismatch")
    man = load(A1_MANIFEST[0])
    return {f"{w['first_page']:03d}": {m: v["token_ids"] for m, v in w["by_mode"].items()} for w in man["windows"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--audit-sha256", required=True)
    ap.add_argument("--inventory", type=Path, required=True, help="committed A1 blind inventory")
    ap.add_argument("--results", type=Path, required=True, help="normalized results built by the bound adapter")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    check = Check()
    check(sha_file(a.audit) == a.audit_sha256, "audit digest")
    audit, inv, norm = load(a.audit), load(a.inventory), load(a.results)
    from escrow import verify_unchanged  # noqa: PLC0415
    check(not verify_unchanged(inv), "A1 run tree changed since the blind inventory")
    files = {f"{r['run']}/{k}": v for r in inv["runs"] for k, v in r["files"].items()}
    for rel, digest in norm["source_files"].items():
        check(files.get(rel) == digest, f"normalized result cites {rel} not matching the inventory")
    manifest = load_manifest()
    vocab = Vocab(disk("tokenizer.json"))
    if norm.get("infrastructure_errors"):
        res = dict(outcome="INFRASTRUCTURE_ERROR", errors=norm["infrastructure_errors"],
                   attribution="no engine outcome; cause inspection and a new source binding are required")
    else:
        by, locs, bb = bind(norm, audit, manifest, vocab, check)
        res = decide(by, audit, manifest, vocab, locs, bb, rules=blob_module("design/rules.py", "astra_rules"),
                     coordinator_check=norm.get("coordinator_endpoint_check"))
        check(all(v.get("agree") for v in res.get("astra_rules_cross_check", {}).values()),
              "reviewer and Astra arithmetic agree")
        if "coordinator_endpoint_check" in res:
            check(res["coordinator_endpoint_check"]["agrees"],
                  "reviewer endpoint parity agrees with the coordinator's eight-window endpoint check")
    rec = dict(kind="WP-0017 A1 reviewer decision (synchronized with design 1fad21c)", reviewer="eld-rd-reviewer",
               created_utc=utc(), audit_sha256=a.audit_sha256, inventory_sha256=sha_file(a.inventory),
               results_sha256=sha_file(a.results), checks_run=check.count, failures=check.failures,
               outcome=res["outcome"] if not check.failures else "BINDING_FAILED", decision=res)
    digest = write_new(a.out, rec)
    print(json.dumps(dict(out=str(a.out), sha256=digest, outcome=rec["outcome"], failures=check.failures[:20]), indent=1))
    return 0 if not check.failures else 1


if __name__ == "__main__":
    sys.exit(main())
