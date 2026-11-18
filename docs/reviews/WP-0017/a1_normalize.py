"""WP-0017 A1: independently normalize the combined endpoint and switch run directories (eld-rd-reviewer).

Stdlib only, CPU only, no truth. Written by the continuation session (common.OPERATOR) before any A1 output or
frozen engine candidate existed. It reads ONLY files listed in the committed A1 blind inventory, after proving
the trees unchanged, and cites every file it uses by its inventory digest (a1_decide.py re-checks them).

Inputs, as published by the coordinator (prepare_a1.py 74b24a1f, check_endpoints.py edcb4184):
  <runs>/a1-<tag>-endpoints/            launch.py inner run, --configs native,all_off,carbon_bf16,all_on
  <runs>/a1-<tag>-endpoints-order/      run_order.py receipts + endpoint-check.json (coordinator's 8-window gate)
  <runs>/a1-<tag>-switches/             launch.py inner run, --configs add_S0..add_S3,remove_S0..remove_S3
  <runs>/a1-<tag>-switches-order/       run_order.py receipts
  optional later runs (separately released): endpoint/addition re-probes, pair removals.
Per configuration the inner run holds segment-NN-<mode>/child.json and segment-NN-<mode>/free/{window-019,
window-037,raw-0NN}.json (the layout check_endpoints.py reads). Re-probe runs append probe passes to the same
configuration id; a configuration may otherwise appear in exactly one run.

FREE PATH (implemented and self-tested now): for each configuration and window the reviewer derives the free
token history from the window record, proves it equals the concatenation of the three raw page records, that
every raw page carries the A source digest, its page number and the pinned ordered RGB digest, that each page
starts with <PAGE>, the window stopped with three pages out and no EOS id inside the history. The ordinary
clock is engine_end_ns - engine_begin_ns (the engine.read span the prefix audit used for the 87.30-106.26 s
figures). The configuration's bit vector is derived from its id, independently of the engine, and compared with
any vector the engine reports.

ENGINE-SPECIFIC FIELDS are bound (map_probe, BOUND) to the PUBLISHED schema of the listed candidate SHA only,
read from its Git blobs (CONTRACT.md, a1_trial.py, span_probe.py, launch.py, ablation_engine.py): launch.json
source/head/planned configs/auto-pair flag, child.json mode/bits/implementation, free/ordinary-timing.json,
probe/window-NNN-probe.json forced_native_passes and free_running_probe. A run from any other source SHA is
reported UNBOUND (CLI exit non-zero) until a reviewed re-bind commit lists it, so a1_decide.py never runs on a
guessed schema. D is RECOMPUTED from per-token guarded FP32 log-probabilities (math.fsum) and must equal the
engine's D within 1e-9; the shared pre-divergence tokens (037: ' ') are moved into the prefix so it equals the
frozen 41-token prefix; S3-on probes must record the configuration's device guards; the S3-on/S0-off
deferred-callback label is attached from the bound contract plus nonzero counters, never invented.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a1_decide as A1  # noqa: E402
from common import A1_MANIFEST, EOS_ID, PAGE_ID, Check, load, sha_file, utc, write_new  # noqa: E402

WINDOW_PAGES = 3
INITIAL = {"endpoints": A1.ENDPOINTS,
           "switches": tuple(f"{k}_{s}" for k in ("add", "remove") for s in A1.SWITCHES)}
# Probe/label mapping bound to the PUBLISHED engine schema (read from Git blobs of these commits only; the author's
# working tree was never read). A run whose launch.json source is not listed here is refused until a reviewed
# re-bind commit adds it (the corrected post-peer-review candidate is expected to need exactly that).
BOUND = {
    "eb16708886226436de85abe0e224391a88537a72": dict(
        contract="docs/research/WP-0017/engine/CONTRACT.md 5a0f2b65 (schemas ablation-engine/1, span-logit-probe/1)",
        s3_probe_guards="host only (span_probe.apply_pure_host_guards); S3-on probes are therefore rejected, "
                        "as in the joint design read, until a candidate records device guards in guard_meta",
        s3_device_guards=False),
}
BOUND_CANDIDATE = sorted(BOUND)
IMPLEMENTATION = {"ablation_engine": "switch_harness", "genuine_native": "genuine_native",
                  "genuine_carbon_bf16": "genuine_carbon"}
COUNTER_KEYS = ("forward_count", "burst_extra_forwards", "static_cache_reallocations", "prefill_grouped_mm_layer_calls",
                "prefill_moe_fallback_layer_calls", "triton_starts", "dense_starts")
CADENCE = ("ordered TextStreamer callbacks deferred to burst return (S3 on, S0 off; CONTRACT.md section 1 of the "
           "bound candidate), evidenced by nonzero s0_streamer_put_calls and s3_burst_chunks")


class ProbeError(ValueError):
    pass


def map_probe(p, history, vocab_unused=None):
    """Engine span-logit probe -> a1_decide PROBE. `history` is the token history the probe claims to condition
    on (frozen native for forced passes, this configuration's own free window for free_running). The common
    pre-divergence tokens of the two branches (e.g. the shared ' ' on 037) are moved into the prefix, so the
    branches start at the first unequal token, and D is RECOMPUTED here from per-token guarded FP32 log-probs."""
    if p is None:
        return None
    if p.get("serial_single_token_decode_enforced") is not True:
        raise ProbeError("probe was not serial single-token decode")
    P, lcp = p["prefix_token_len"], p["lcp_offset_from_pre_space"]
    if A1.ids_sha(history[:P]) != p["prefix_sha256"]:
        raise ProbeError("engine prefix digest is not the claimed history prefix")
    br = {b["role"]: b for b in p["branches"]}
    if set(br) != {"native_id", "carbon_id"}:
        raise ProbeError("expected native_id and carbon_id branches")
    shared = br["native_id"]["pre_space_token_ids"][:lcp]
    if br["carbon_id"]["pre_space_token_ids"][:lcp] != shared or history[P:P + lcp] != shared:
        raise ProbeError("shared pre-divergence tokens are not the history continuation")
    out_br, finite = {}, True
    for role, name in (("native_id", "native"), ("carbon_id", "carbon_bf16")):
        b = br[role]
        steps = [s for s in b["steps"] if s["in_common_boundary_suffix"]]
        ids = [s["guarded"]["target_token_id"] for s in steps]
        if ids != b["common_boundary_token_ids"] or b["pre_space_token_ids"][lcp:] != ids:
            raise ProbeError(f"{role}: step targets differ from the published branch ids")
        lps = [s["guarded"]["target_logprob_fp32"] for s in steps]
        finite &= all(isinstance(x, float) for x in lps) and bool(b["all_targets_finite_guarded"])
        out_br[name] = dict(ids=ids, logprobs=[x if isinstance(x, float) else float("-inf") for x in lps])
    if out_br["native"]["ids"][:1] == out_br["carbon_bf16"]["ids"][:1]:
        raise ProbeError("branches do not diverge at their first common-boundary token")
    div = p["divergence_step_summary"]
    top5 = [[t["token_id"], t["logit_fp32"]] for t in div["guarded_top5"]]
    comp = {c["token_id"]: c.get("logit_fp32") for c in (div.get("guarded_competing_candidates") or [])}
    if len(top5) != 5 or any(out_br[m]["ids"][0] not in comp for m in out_br):
        raise ProbeError("top five or a competing first-divergence candidate record is missing")
    competing = {"native": comp[out_br["native"]["ids"][0]], "carbon_bf16": comp[out_br["carbon_bf16"]["ids"][0]]}
    finite &= all(isinstance(v, (int, float)) for v in competing.values()) and all(isinstance(z, float) for _, z in top5)
    status = "finite" if finite else ("masked" if p.get("both_branches_finite_raw") else "nonfinite")
    t = p.get("probe_timing") or {}
    rec = dict(prefix_sha256=A1.ids_sha(history[:P + lcp]), prefix_tokens=P + lcp, branches=out_br, first_divergence=0,
               top5=top5, competing_logits=competing, guard_status=status,
               guard_implementation=(div.get("guard_meta") or {}).get("implementation", "host"),
               timing=dict(prefill_ms=t.get("prefill_ms"), decode_ms_per_token=t.get("decode_ms_per_forwarded_token"),
                           decode_tokens=t.get("total_forwarded_decode_tokens"), interval=t.get("denominator_note"),
                           device_synchronized=t.get("device_synchronized")),
               engine_D=p.get("D_native_minus_carbon_guarded_nats"))
    if status == "finite":
        import math  # noqa: PLC0415
        mine = math.fsum(out_br["native"]["logprobs"]) - math.fsum(out_br["carbon_bf16"]["logprobs"])
        if rec["engine_D"] is None or abs(mine - rec["engine_D"]) > 1e-9:
            raise ProbeError(f"recomputed D {mine!r} differs from the engine's {rec['engine_D']!r}")
    return rec


def segments(run):
    out = []
    for seg in sorted(Path(run).glob("segment-[0-9][0-9]-*")):
        if seg.is_dir():
            out.append((seg.name.split("-", 2)[2], seg))
    return out


def free_window(seg, first, request, cite, check):
    """Return the independently validated free window or None; every file read is cited."""
    tag = f"{seg.parent.name}/{seg.name}/window-{first:03d}"
    wf = seg / "free" / f"window-{first:03d}.json"
    if not check(wf.is_file(), f"{tag}: window record present"):
        return None
    w = load(cite(wf))
    ids = w.get("window_token_ids") or []
    check(w.get("source_sha256") == request["sha256"] and w.get("first_page") == first, f"{tag}: source link")
    check(w.get("pages") == WINDOW_PAGES and w.get("num_pages_out") == WINDOW_PAGES and w.get("finish_reason") == "stop",
          f"{tag}: three pages out and stop")
    check(EOS_ID not in ids and w.get("eos_id", EOS_ID) == EOS_ID, f"{tag}: EOS excluded from the history")
    check(ids.count(PAGE_ID) == WINDOW_PAGES and ids[:1] == [PAGE_ID], f"{tag}: three <PAGE> starts")
    joined = []
    for page in range(first, first + WINDOW_PAGES):
        rf = seg / "free" / f"raw-{page:03d}.json"
        if not check(rf.is_file(), f"{tag}: raw page {page} present"):
            return None
        raw = load(cite(rf))
        check(raw.get("source_sha256") == request["sha256"] and raw.get("page") == page, f"{tag}: raw {page} link")
        check(raw.get("rgb_sha256") == request["rgb_sha256"][page - 1], f"{tag}: raw {page} RGB = pinned page RGB")
        check((raw.get("token_ids") or [None])[0] == PAGE_ID, f"{tag}: raw {page} starts with <PAGE>")
        joined += raw.get("token_ids") or []
    check(joined == ids, f"{tag}: window history = concatenated raw pages")
    b, e = w.get("engine_begin_ns"), w.get("engine_end_ns")
    seconds = (e - b) / 1e9 if isinstance(b, int) and isinstance(e, int) and e > b else None
    check(seconds is not None, f"{tag}: engine.read span present")
    counters = {k: w[k] for k in COUNTER_KEYS if isinstance(w.get(k), int)}
    counters.update({k: v for k, v in (w.get("switch_counter_delta") or {}).items() if isinstance(v, int)})
    return dict(token_ids=ids, seconds=seconds, clock="engine_end_ns - engine_begin_ns", output_tokens=len(ids),
                forwards=w.get("forward_count"), counters=counters, engine_reported_bits=w.get("switch_bits"))


def normalize(inv, runs, manifest_path=A1_MANIFEST[0], check=None):
    check = check or Check()
    from escrow import verify_unchanged  # noqa: PLC0415
    check(not verify_unchanged(inv), "A1 run trees unchanged since the blind inventory")
    request = load(manifest_path)["request"]
    files = {Path(r["path"]).resolve(): (r["run"], r["files"]) for r in inv["runs"]}
    cited, errors = {}, []

    def cite(path):
        path = Path(path).resolve()
        for root, (name, table) in files.items():
            if path.is_relative_to(root):
                rel = path.relative_to(root).as_posix()
                check(rel in table and table[rel] == sha_file(path), f"{name}/{rel} is inventoried with this digest")
                cited[f"{name}/{rel}"] = table.get(rel)
                return path
        check(False, f"{path} is outside every inventoried run")
        return path
    wave, seen = A1.initial_wave(), {}
    manifest = A1.load_manifest() if Path(manifest_path) == A1_MANIFEST[0] else {
        f"{w['first_page']:03d}": {m: v["token_ids"] for m, v in w["by_mode"].items()} for w in load(manifest_path)["windows"]}
    sources, unbound = set(), []
    for group, run in runs.items():
        run = Path(run)
        check(run.resolve() in files, f"{group}: run {run.name} is in the inventory")
        modes = [m for m, _ in segments(run)]
        launch = load(cite(run / "launch.json")) if (run / "launch.json").is_file() else {}
        src = launch.get("source")
        sources.add(src)
        check(src is not None and launch.get("head") == src and launch.get("stage") == "A1",
              f"{group}: launch record source = head (A1)")
        if src not in BOUND:
            unbound.append(f"{run.name}: source {src} has no reviewed probe/label binding")
        check(launch.get("a1_manifest_sha256") == A1_MANIFEST[1], f"{group}: launch used the frozen A1 manifest")
        check(launch.get("planned_configs") == modes, f"{group}: planned configs = segment order")
        if group in INITIAL:
            check(modes == list(INITIAL[group]), f"{group}: segments {modes} = released configs {list(INITIAL[group])}")
            check(launch.get("auto_pair_removals") is False, f"{group}: no automatic pair runs in the initial wave")
        outer = run.parent / (run.name + "-order")
        if (outer / "process.json").is_file() and outer.resolve() in files:
            proc = load(cite(outer / "process.json"))
            if not proc.get("all_segments_completed") or any(s.get("returncode") for s in proc.get("segments", [])):
                errors.append(f"{outer.name}: run_order reports incomplete or nonzero segments")
        if (run / "process.json").is_file():
            inner = load(cite(run / "process.json"))
            if not inner.get("all_segments_completed") or inner.get("overall_reason"):
                errors.append(f"{run.name}: launch.py reports {inner.get('overall_reason') or 'incomplete segments'}")
        for mode, seg in segments(run):
            if mode in seen and group in INITIAL:
                check(False, f"{mode}: configuration appears in two initial runs")
            if (seg / "failure.json").is_file():
                errors.append(f"{run.name}/{seg.name}: failure.json present")
            bits = wave.get(mode) or (A1.bits(set(A1.SWITCHES) - set(A1.removal_of(mode)))
                                      if A1.removal_of(mode) else None)
            check(bits is not None, f"{mode}: known configuration id")
            on = {s for s, b in zip(A1.SWITCHES, bits or "") if b == "1"}
            child = load(cite(seg / "child.json")) if check((seg / "child.json").is_file(), f"{seg.name}: child") else {}
            check(child.get("mode") == mode and child.get("switch_bits") == bits, f"{run.name}/{seg.name}: child mode/bits")
            impl = IMPLEMENTATION.get(child.get("implementation"))
            check(impl is not None, f"{mode}: known implementation label {child.get('implementation')!r}")
            row = seen.setdefault(mode, dict(id=mode, bits=bits, implementation=impl, aliases=None,
                                            stream_cadence_label=None, windows={}, runs=[]))
            row["runs"].append(run.name)
            ot = seg / "free" / "ordinary-timing.json"
            timing = load(cite(ot)) if check(ot.is_file(), f"{seg.name}: phase-1 ordinary timing frozen") else {}
            check(timing.get("switch_bits") == bits and timing.get("mode") == mode, f"{seg.name}: ordinary timing mode/bits")
            put = burst = 0
            for k, wd in enumerate(manifest_windows(manifest_path)):
                w = f"{wd:03d}"
                fw = free_window(seg, wd, request, cite, check)
                if fw is None:
                    errors.append(f"{run.name}/{seg.name}: window {w} free record missing")
                    continue
                if fw["engine_reported_bits"] is not None:
                    check(fw["engine_reported_bits"] == bits, f"{mode}/{w}: engine bits = id-derived bits")
                secs = (timing.get("ordinary_window_seconds") or [None, None])[k]
                check(isinstance(secs, float) and abs(secs - fw["seconds"]) < 1e-6,
                      f"{mode}/{w}: ordinary-timing seconds = engine.read span")
                put += fw["counters"].get("s0_streamer_put_calls", 0)
                burst += fw["counters"].get("s3_burst_chunks", 0)
                win = row["windows"].setdefault(w, dict(free=dict(
                    token_ids=fw["token_ids"], seconds=fw["seconds"], output_tokens=fw["output_tokens"],
                    forwards=fw["forwards"], counters=fw["counters"], instrumented=False,
                    instrumented_basis="phase 1 free run with zero probe hooks (bound contract); probes in probe/"),
                    probes={"native_prefix": []}))
                pf = seg / "probe" / f"window-{w}-probe.json"
                if not (check(pf.is_file(), f"{mode}/{w}: probe record") and src in BOUND):
                    continue
                pd = load(cite(pf))
                check(pd.get("mode") == mode and pd.get("switch_bits") == bits and pd.get("first_page") == wd,
                      f"{mode}/{w}: probe record identity")
                try:
                    win["probes"]["native_prefix"] += [map_probe(p, manifest[w]["native"]) for p in pd["forced_native_passes"]]
                    if wd == 37 or pd.get("free_running_probe") is not None:
                        win["probes"]["free_prefix"] = [map_probe(pd.get("free_running_probe"), fw["token_ids"])]
                except (ProbeError, KeyError, TypeError) as exc:
                    check(False, f"{mode}/{w}: probe mapping failed: {exc!r}")
                    continue
                if "S3" in on:
                    gi = {p["guard_implementation"] for ps in win["probes"].values() for p in ps if p}
                    check(gi == {"device"}, f"{mode}/{w}: S3-on probe must use the configuration's device guards ({gi})")
            if "S3" in on and "S0" not in on and put > 0 and burst > 0:
                row["stream_cadence_label"] = CADENCE
    coord = None
    ep = runs.get("endpoints")
    if ep is not None:
        f = Path(ep).parent / (Path(ep).name + "-order") / "endpoint-check.json"
        if f.is_file():
            coord = load(cite(f))
    status = "BOUND" if not unbound and len(sources) == 1 else "UNBOUND"
    return dict(kind="WP-0017 A1 reviewer normalized results", adapter_status=status,
                bound_candidates=BOUND_CANDIDATE, run_sources=sorted(s for s in sources if s), unbound=unbound,
                configurations=list(seen.values()), source_files=cited, infrastructure_errors=errors,
                coordinator_endpoint_check=coord, checks_run=check.count, failures=check.failures)


def manifest_windows(manifest_path):
    return [w["first_page"] for w in load(manifest_path)["windows"]]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inventory", type=Path, required=True, help="committed A1 blind inventory")
    ap.add_argument("--endpoints", type=Path, required=True)
    ap.add_argument("--switches", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if sha_file(A1_MANIFEST[0]) != A1_MANIFEST[1]:
        raise SystemExit("A1 manifest digest mismatch")
    rec = normalize(load(a.inventory), dict(endpoints=a.endpoints, switches=a.switches))
    rec.update(created_utc=utc(), inventory_sha256=sha_file(a.inventory))
    digest = write_new(a.out, rec)
    print(json.dumps(dict(out=str(a.out), sha256=digest, adapter_status=rec["adapter_status"],
                          failures=rec["failures"][:20]), indent=1))
    return 0 if rec["adapter_status"] == "BOUND" and not rec["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
