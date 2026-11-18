"""CPU-only verification for WP-0016 G0 wrapper, passive telemetry, and gate processor.

Enforces CUDA_VISIBLE_DEVICES='' and zero torch/nvidia-smi execution. Reads only public
WP-0015 development fixtures (dev/short, dev/dense, dev/boundary), WP-0014 A.pdf metadata,
and read-only Q0 config/tokenizer JSON files. Never accesses H, A, B, or inference runs,
and never touches C:/Users/jackg/eLedgerCare-Speed/WP-0016/review.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = ""

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EVAL_WP15 = ROOT / "docs/evaluation/WP-0015"
ASTRA_WP15 = ROOT / "docs/research/WP-0015/astra"
CARBON_WP15 = ROOT / "docs/research/WP-0015/carbon"
WP14 = ROOT / "docs/research/WP-0014/eld-latency-author"
WORKER = ROOT / "workers/local_ocr"
sys.path[:0] = [str(HERE), str(CARBON_WP15), str(EVAL_WP15), str(ASTRA_WP15), str(WP14), str(WORKER)]

import g0
import g0_telemetry as tel
from cases import GPU, PYTHON
from formats import digest, native_page, publish
import score as frozen_scorer

Q0_MODEL = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/models/Unlimited_OCR_2_04809669")
CARBON_RUNTIME_ROOT = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0016/carbon")
G0_FREEZE_COMMIT = "c7b2ee3663317e42a0e9bdd7ff9e17f16747d2cf"


@functools.lru_cache(maxsize=1)
def _gpt2_unicode_to_bytes() -> dict[str, int]:
    bs = (
        list(range(ord("!"), ord("~") + 1))
        + list(range(ord("¡"), ord("¬") + 1))
        + list(range(ord("®"), ord("ÿ") + 1))
    )
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return {chr(c): b for b, c in zip(bs, cs)}


def inspect_q0_tokenizer_composite_contracts() -> dict:
    """Pure-JSON CPU census of Unlimited-OCR-2 vocabulary for G1 composite/digit state analysis."""
    cfg = json.loads((Q0_MODEL / "config.json").read_bytes())
    tok_raw = json.loads((Q0_MODEL / "tokenizer.json").read_bytes())
    u2b = _gpt2_unicode_to_bytes()

    id_to_bytes: dict[int, bytes] = {}
    for piece, tid in tok_raw["model"]["vocab"].items():
        id_to_bytes[int(tid)] = (
            bytes(u2b[ch] for ch in piece) if all(ch in u2b for ch in piece) else piece.encode("utf-8")
        )
    added_special = {}
    for entry in tok_raw.get("added_tokens", []):
        tid = int(entry["id"])
        content = entry["content"]
        id_to_bytes[tid] = content.encode("utf-8")
        if tid >= 128815 or tid < 3:
            added_special[str(tid)] = content

    lm_head_vocab = int(cfg["vocab_size"])
    mapped_vocab = len(id_to_bytes)
    unmapped_tail_ids = lm_head_vocab - mapped_vocab

    ascii_1digit = 0
    ascii_2digit = 0
    ascii_3digit = 0
    ascii_4plus_digit = 0
    unicode_non_ascii_digit_tokens = 0
    label_plus_lbracket = []
    rbracket_composites = []
    comma_composites = []
    level_subtokens = []

    for tid in sorted(id_to_bytes):
        raw_b = id_to_bytes[tid]
        try:
            s = raw_b.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if re.fullmatch(r"[0-9]", s):
            ascii_1digit += 1
        elif re.fullmatch(r"[0-9]{2}", s):
            ascii_2digit += 1
        elif re.fullmatch(r"[0-9]{3}", s):
            ascii_3digit += 1
        elif re.search(r"[0-9]{4,}", s):
            ascii_4plus_digit += 1
        elif re.fullmatch(r"\d+", s):
            unicode_non_ascii_digit_tokens += 1

        if "[" in s and s != "[":
            if re.fullmatch(r"[\w-]+\s*\[", s):
                label_plus_lbracket.append((tid, s))
        if "]" in s and s != "]":
            if len(rbracket_composites) < 12 and re.fullmatch(r"[\s0-9,\[\]]*\[?[\s0-9,]*\][\s<>A-Za-z]*", s):
                rbracket_composites.append((tid, s))
        if "," in s and s != "," and re.fullmatch(r",\s*|\s*,", s):
            comma_composites.append((tid, s))
        if "LEVEL" in s.upper() and len(level_subtokens) < 12:
            level_subtokens.append((tid, s))

    assert ascii_1digit == 10 and ascii_2digit == 100 and ascii_3digit == 1000
    assert ascii_4plus_digit == 0
    return {
        "lm_head_vocab_size": lm_head_vocab,
        "tokenizer_mapped_vocab_size": mapped_vocab,
        "unmapped_lm_head_tail_count": unmapped_tail_ids,
        "unmapped_tail_range": [mapped_vocab, lm_head_vocab - 1],
        "key_added_tokens": added_special,
        "title_level_is_single_added_token": any("LEVEL" in v for v in added_special.values()),
        "ascii_pure_digit_token_counts": {
            "1_digit": ascii_1digit,
            "2_digit": ascii_2digit,
            "3_digit": ascii_3digit,
            "4_or_more_digits": ascii_4plus_digit,
        },
        "unicode_non_ascii_digit_only_tokens": unicode_non_ascii_digit_tokens,
        "label_plus_lbracket_token_count": len(label_plus_lbracket),
        "label_plus_lbracket_examples": label_plus_lbracket[:10],
        "comma_whitespace_token_count": len(comma_composites),
        "comma_whitespace_examples": comma_composites[:10],
        "rbracket_composite_examples": rbracket_composites[:10],
        "level_subtoken_examples": level_subtokens,
        "g1_dfa_implications": {
            "four_digit_termination": (
                "BPE contains all 10 1-digit, 100 2-digit, and 1,000 3-digit ASCII tokens ('0'..'999'), "
                "so a single token advances digit length by +1, +2, or +3. Logical phase 'inside coord_k' "
                "cannot be a single state: each of the 4 coordinates requires sub-states for 0, 1, 2, and 3 "
                "emitted ASCII digits (blocking 2-digit tokens at len=2, 3-digit tokens at len>=1, all digit "
                "tokens at len=3, and blocking non-ASCII Unicode \\d tokens that formats.BLOCK \\d+ would accept "
                "or misparse)."
            ),
            "composite_phase_crossing": (
                "Composite tokens such as ' [', ', ', 'text[' or ']]' cross logical phase boundaries in one "
                "decode step; token-level transitions must be induced by running the exact byte/character DFA "
                "over every UTF-8 token byte string in 0..128830 and masking unmapped rows 128831..129279."
            ),
        },
    }


def verify_utf8_child_stream_hunk(scratch_dir: Path) -> dict:
    """Verify 61bec476 UTF-8 stream reconfigure fires when carbon/trial.py imports astra/trial.py under -I."""
    out_file = scratch_dir / "utf8-child-stdout.txt"
    err_file = scratch_dir / "utf8-child-stderr.txt"
    code = (
        "import importlib.util, sys; "
        "from pathlib import Path; "
        f"p = Path({str(CARBON_WP15 / 'trial.py')!r}); "
        "spec = importlib.util.spec_from_file_location('c_trial', p); "
        "mod = importlib.util.module_from_spec(spec); "
        "spec.loader.exec_module(mod); "
        "assert 'torch' not in sys.modules; "
        "print('UTF8_OK:\\uff5c\\u2014\\u2500<PAGE><BLOCK>text[0, 0, 10, 10]<FORK>', flush=True)"
    )
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="")
    with out_file.open("wb") as out_h, err_file.open("wb") as err_h:
        proc = subprocess.run(
            [str(PYTHON), "-I", "-B", "-c", code],
            cwd=str(scratch_dir),
            env=env,
            stdout=out_h,
            stderr=err_h,
            check=False,
        )
    stdout_text = out_file.read_bytes().decode("utf-8")
    stderr_text = err_file.read_bytes().decode("utf-8")
    assert proc.returncode == 0, f"UTF-8 child check failed: rc={proc.returncode}, stderr={stderr_text}"
    assert "UTF8_OK:\uff5c\u2014\u2500<PAGE>" in stdout_text
    return {"returncode": proc.returncode, "stdout_utf8_verified": True}


def verify_g0_wrapper_cpu(scratch_dir: Path) -> dict:
    """Test g0.py CLI, source checks, mode gate, and simulated --owner review routing in scratch_dir."""
    launcher = g0.load_g0_launcher()
    assert "torch" not in sys.modules
    assert launcher.PACKET == Path("C:/Users/jackg/eLedgerCare-Speed/WP-0016")
    assert launcher.MODES == ("native", "carbon_bf16")
    assert launcher.SCOPES == (
        "docs/research/WP-0015/carbon",
        "docs/research/WP-0015/astra",
        "docs/research/WP-0014/eld-latency-author",
        "workers/local_ocr",
        "docs/evaluation/WP-0015",
        "docs/research/WP-0016/engine/g0.py",
    )

    # Verify G0_FREEZE_COMMIT matches HEAD across all 6 scopes even while new files exist in engine/
    for scope in launcher.SCOPES:
        src_obj = launcher.git("rev-parse", f"{G0_FREEZE_COMMIT}:{scope}")
        head_obj = launcher.git("rev-parse", f"HEAD:{scope}")
        dirty = launcher.git("status", "--porcelain", "--", scope)
        assert src_obj == head_obj and not dirty, f"Scope drift on {scope}: src={src_obj} head={head_obj} dirty={dirty}"

    warm_pdf = (WP14 / "A.pdf").resolve()
    warm_sha = digest(warm_pdf.read_bytes())

    # Negative 1: pre-g0 base SHA 61bec476 must be rejected because g0.py is absent there
    plan_valid = scratch_dir / "valid-plan.json"
    valid_sha = publish(
        plan_valid,
        {
            "requests": [
                {"label": "warm-1", "mode": "native", "warmup": True, "pages": 1, "sha256": warm_sha, "pdf": str(warm_pdf)},
                {
                    "label": "warm-1",
                    "mode": "carbon_bf16",
                    "warmup": True,
                    "pages": 1,
                    "sha256": warm_sha,
                    "pdf": str(warm_pdf),
                },
            ]
        },
    )

    neg_results = {}
    try:
        launcher_neg1 = g0.load_g0_launcher()
        launcher_neg1.PACKET = scratch_dir / "packet-neg1"
        saved = sys.argv
        try:
            sys.argv = [
                str(g0.__file__),
                "--owner",
                "review",
                "--source",
                "61bec47689dcdf272a525185013f2dce6335fa24",
                "--plan",
                str(plan_valid),
                "--sha256",
                valid_sha,
                "--run",
                "neg-base-sha",
                "--lease",
                "cpu-test-lease",
                "--seconds",
                "60",
            ]
            launcher_neg1.main()
        finally:
            sys.argv = saved
        raise AssertionError("Expected pre-g0 source SHA to fail g0.py scope check")
    except subprocess.CalledProcessError as exc:
        neg_results["reject_pre_g0_source_sha"] = f"rejected ({type(exc).__name__})"

    # Negative 2: non-G0 mode ('carbon_moe') rejected before any GPU query
    plan_bad_mode = scratch_dir / "bad-mode-plan.json"
    bad_mode_sha = publish(
        plan_bad_mode,
        {
            "requests": [
                {"label": "warm-1", "mode": "carbon_moe", "warmup": True, "pages": 1, "sha256": warm_sha, "pdf": str(warm_pdf)}
            ]
        },
    )
    try:
        launcher_neg2 = g0.load_g0_launcher()
        launcher_neg2.PACKET = scratch_dir / "packet-neg2"
        saved = sys.argv
        try:
            sys.argv = [
                str(g0.__file__),
                "--owner",
                "review",
                "--source",
                G0_FREEZE_COMMIT,
                "--plan",
                str(plan_bad_mode),
                "--sha256",
                bad_mode_sha,
                "--run",
                "neg-mode",
                "--lease",
                "cpu-test-lease",
                "--seconds",
                "60",
            ]
            launcher_neg2.main()
        finally:
            sys.argv = saved
        raise AssertionError("Expected non-G0 mode carbon_moe to be rejected")
    except ValueError as exc:
        assert "invalid request entry" in str(exc)
        neg_results["reject_non_g0_mode_carbon_moe"] = "rejected (ValueError)"

    # Positive CPU dry-run simulation: redirect PACKET to scratch_dir/sim-packet (leaving real WP-0016/review untouched!)
    # and stub gpu_observation + subprocess.Popen to verify exact child interpreter command & segment layout.
    sim_packet = scratch_dir / "sim-wp0016-packet"
    launcher_sim = g0.load_g0_launcher()
    assert launcher_sim.PACKET == Path("C:/Users/jackg/eLedgerCare-Speed/WP-0016")
    launcher_sim.PACKET = sim_packet
    launcher_sim.gpu_observation = lambda: {
        "uuid": GPU,
        "free_mib": 15200,
        "used_mib": 1103,
        "temperature_c": 38.0,
        "utilization_percent": 0,
        "driver": "cpu-stub",
    }
    spawned_cmds = []

    orig_popen = launcher_sim.subprocess.Popen

    class DummyChild:
        def __init__(self, cmd, cwd=None, env=None, stdout=None, stderr=None, stdin=None, **kw):
            spawned_cmds.append({"cmd": list(cmd), "cwd": str(cwd), "cuda_visible": (env or {}).get("CUDA_VISIBLE_DEVICES")})
            self.pid = 99999
            self.returncode = 0
            seg_d = Path(cwd)
            publish(seg_d / "child.json", {"pid": 99999, "creation_filetime": 123456789, "stub": True})

        def poll(self):
            return 0

        def wait(self, timeout=None):
            return 0

    def selective_popen(cmd, *a, **kw):
        exe = Path(cmd[0]).name.lower() if isinstance(cmd, (list, tuple)) and cmd else ""
        if "nvidia-smi" in exe:
            raise AssertionError(f"Forbidden nvidia-smi invocation during CPU verification: {cmd}")
        if isinstance(cmd, (list, tuple)) and len(cmd) >= 4 and str(cmd[3]).endswith("trial.py"):
            return DummyChild(cmd, *a, **kw)
        return orig_popen(cmd, *a, **kw)

    launcher_sim.subprocess.Popen = selective_popen
    saved_argv = sys.argv
    try:
        sys.argv = [
            str(g0.__file__),
            "--owner",
            "review",
            "--source",
            G0_FREEZE_COMMIT,
            "--plan",
            str(plan_valid),
            "--sha256",
            valid_sha,
            "--run",
            "sim-ab-01",
            "--lease",
            "sim-lease-01",
            "--seconds",
            "300",
        ]
        rc = launcher_sim.main()
    finally:
        sys.argv = saved_argv
        launcher_sim.subprocess.Popen = orig_popen

    assert rc == 0
    assert len(spawned_cmds) == 2
    expected_trial_py = str((CARBON_WP15 / "trial.py").resolve())
    for idx, mode_expected in enumerate(("native", "carbon_bf16"), 1):
        c = spawned_cmds[idx - 1]["cmd"]
        assert c[:4] == [str(PYTHON), "-I", "-B", expected_trial_py]
        assert Path(c[4]).name == f"segment-{idx:02d}-{mode_expected}"
    assert (sim_packet / "review" / "runs" / "sim-ab-01" / "process.json").is_file()
    return {
        "configured_packet_root": "C:/Users/jackg/eLedgerCare-Speed/WP-0016",
        "allowed_g0_modes": list(g0.G0_MODES),
        "verified_scopes_count": len(launcher.SCOPES),
        "negative_controls": neg_results,
        "simulated_segments_spawned": len(spawned_cmds),
        "unchanged_child_interpreter_verified": True,
    }


def verify_telemetry_and_gates_cpu(scratch_dir: Path) -> dict:
    """Verify static-KV reconstruction, malformed-header/invented-table checks, dual parsers, and G0/G1/G2 gates."""
    scorer_sha = tel.verify_scorer_pin()
    scorer_self = subprocess.run(
        [str(PYTHON), "-B", str(EVAL_WP15 / "check_score.py")],
        cwd=str(EVAL_WP15),
        env=dict(os.environ, CUDA_VISIBLE_DEVICES=""),
        capture_output=True,
        text=True,
        check=True,
    )
    scorer_26 = json.loads(scorer_self.stdout)
    assert len(scorer_26) == 26 and all(v == "pass" for v in scorer_26.values())

    # 1. Static KV reconstruction: no-reallocation (cap_tok=4096) vs 1-reallocation (cap_tok=8192)
    kv_no_grow = tel.reconstruct_window_static_kv(
        {
            "engine_mode": "carbon_bf16",
            "first_page": 1,
            "pages": 3,
            "prompt_len": 831,
            "forward_count": 1500,
            "burst_extra_forwards": 3,
            "static_cache_reallocations": 0,
            "window_token_ids": [128827] * 1496,
            "vram": {"cuda_max_allocated_bytes": 7_450_000_000, "cuda_max_reserved_bytes": 7_850_000_000},
        },
        load_obj={"weight_allocated_bytes_after_pack": 6_720_000_000, "weight_reserved_bytes_after_pack": 6_800_000_000},
    )
    assert kv_no_grow["init_static_cache_footprint"]["cap_tok"] == 4096
    assert kv_no_grow["final_static_cache_footprint"]["cap_tok"] == 4096
    assert kv_no_grow["final_static_cache_footprint"]["total_bytes"] == 277_610_496
    assert kv_no_grow["reallocation_formula_matches_logged"] is True

    kv_one_grow = tel.reconstruct_window_static_kv(
        {
            "engine_mode": "carbon_bf16",
            "first_page": 1,
            "pages": 3,
            "prompt_len": 831,
            "forward_count": 3500,  # 831 + 3499 = 4330 > 4096 -> 1 grow to 8192!
            "burst_extra_forwards": 0,
            "static_cache_reallocations": 1,
            "window_token_ids": [128827] * 3500,
            "vram": {"cuda_max_allocated_bytes": 7_800_000_000, "cuda_max_reserved_bytes": 8_300_000_000},
        }
    )
    assert kv_one_grow["final_static_cache_footprint"]["cap_tok"] == 8192
    assert kv_one_grow["final_static_cache_footprint"]["total_bytes"] == 555_220_992
    assert kv_one_grow["reallocation_formula_matches_logged"] is True

    # 2. Malformed headers & invented tables against public dev/short truth (table-free 1-page fixture)
    short_truth = frozen_scorer.read(EVAL_WP15 / "dev/short/truth.json")
    p1_ref = short_truth["pages"][0]
    pts1 = [p1_ref["width"], p1_ref["height"]]

    # Build a synthetic raw page 1 with <BLOCK>title<LEVEL1> + 4-digit box + corrupt 2-coord box + invented table
    raw1 = (
        "<PAGE><BLOCK>title<LEVEL1>[80, 50, 900, 120]<FORK>"
        + p1_ref["lines"][0]["text"]
        + "<BLOCK>text[80, 140, 1000, 200]<FORK>Dropped 4-digit box"
        + "<BLOCK>text[80, 210]<FORK>Corrupt 2-coord box"
        + "<BLOCK>table[80, 260, 900, 480]<FORK><table><tr><td>Invented</td><td>Cell</td></tr></table>"
    )
    raw_pages = [{"page": 1, "points": pts1, "raw_output": raw1}]
    pred_synth = {
        "source_sha256": short_truth["source_sha256"],
        "pages": [
            {"source_sha256": short_truth["source_sha256"], "page": 1, "state": "complete", **native_page(raw1, pts1)},
        ],
    }
    hdr_check = tel.inspect_raw_headers_and_tables(raw_pages, pred_synth, truth=short_truth)
    assert hdr_check["title_level_headers"] == 1
    assert hdr_check["out_of_bounds_or_inverted_boxes"] == 1
    assert hdr_check["corrupt_syntax_headers"] == 1
    assert hdr_check["strict_malformed_headers"] == 3
    assert hdr_check["adapted_malformed_headers"] == 2
    assert hdr_check["invented_tables"]["invented_tables_on_table_free_pages"] == 1

    # 3. Dual-parser exact match & G0/G1/G2 gate criteria positive/negative checks on public dev/dense truth
    dense_truth = frozen_scorer.read(EVAL_WP15 / "dev/dense/truth.json")
    clean_raws = []
    clean_pages = []
    for ref_p in dense_truth["pages"]:
        pts = [ref_p["width"], ref_p["height"]]
        # Construct exact synthetic raw blocks matching reference lines and tables in 0..999 coords
        chunks = ["<PAGE>"]
        for ln in ref_p["lines"]:
            b = ln["bbox"]
            q = [min(999, max(0, int(round(b[j] * 999 / pts[j % 2])))) for j in range(4)]
            if q[2] <= q[0]:
                q[2] = min(999, q[0] + 1)
            if q[3] <= q[1]:
                q[3] = min(999, q[1] + 1)
            chunks.append(f"<BLOCK>text[{q[0]}, {q[1]}, {q[2]}, {q[3]}]<FORK>{ln['text']}")
        for tb in ref_p["tables"]:
            b = tb["bbox"]
            q = [min(999, max(0, int(round(b[j] * 999 / pts[j % 2])))) for j in range(4)]
            html_rows = "".join("<tr>" + "".join(f"<td>{c['text']}</td>" for c in r) + "</tr>" for r in tb["rows"])
            chunks.append(f"<BLOCK>table[{q[0]}, {q[1]}, {q[2]}, {q[3]}]<FORK><table>{html_rows}</table>")
        raw_s = "".join(chunks)
        clean_raws.append({"page": ref_p["page"], "points": pts, "raw_output": raw_s})
        clean_pages.append(
            {
                "source_sha256": dense_truth["source_sha256"],
                "page": ref_p["page"],
                "state": "complete",
                **native_page(raw_s, pts),
            }
        )

    clean_pred = {"source_sha256": dense_truth["source_sha256"], "pages": clean_pages}
    dual_ctrl = tel.score_dual_parsers(dense_truth, clean_pred, clean_raws)
    dual_comp_identical = tel.compare_dual_parsers(dual_ctrl, dual_ctrl)

    g0_pass = tel.evaluate_gate_criteria(
        "G0", dual_comparison=dual_comp_identical, peak_allocator_mib=7480.0, peak_device_mib=8320.0
    )
    assert g0_pass["passed"] is True

    g0_fail_mem = tel.evaluate_gate_criteria(
        "G0", dual_comparison=dual_comp_identical, peak_allocator_mib=7480.0, peak_device_mib=10050.0
    )
    assert g0_fail_mem["passed"] is False and g0_fail_mem["checks"]["peak_memory_le_10000_mib"] is False

    g0_fail_missing_dev = tel.evaluate_gate_criteria(
        "G0", dual_comparison=dual_comp_identical, peak_allocator_mib=7480.0, peak_device_mib=None
    )
    assert g0_fail_missing_dev["passed"] is False

    g1_fail_hdr = tel.evaluate_gate_criteria(
        "G1",
        dual_comparison=dual_comp_identical,
        peak_allocator_mib=7600.0,
        peak_device_mib=8500.0,
        malformed_headers_strict=1,
        a_speedup_vs_g0=1.02,
    )
    assert g1_fail_hdr["passed"] is False and g1_fail_hdr["checks"]["zero_malformed_headers"] is False

    g2_pass = tel.evaluate_gate_criteria(
        "G2",
        dual_comparison=dual_comp_identical,
        peak_allocator_mib=11200.0,
        peak_device_mib=12400.0,
        a_speedup_vs_g0=2.85,
        a_time_savings_s=280.0,
        control_spread_s=4.5,
        grammar_failures=0,
        static_cache_reallocations=0,
        vs_g1_dual_comparison=dual_comp_identical,
        graph_replays_verified=True,
    )
    assert g2_pass["passed"] is True

    # 4. Windows crossover signed net critical recovery per extra neural second
    degraded_win = json.loads(json.dumps(clean_pred))
    degraded_win["pages"][0]["tables"] = []  # simulate missing table cells in Windows prediction
    crossover = tel.compute_windows_crossover(
        dense_truth,
        degraded_win,
        dual_ctrl,
        neural_elapsed_s=45.6546455,
        windows_elapsed_s=tel.WINDOWS_A_CLOCK_S,
    )
    strict_x = crossover["parsers"]["strict_native_page"]
    assert abs(crossover["extra_neural_seconds"] - 30.0) < 1e-9
    assert strict_x["signed_net_unflagged_recovery_per_extra_neural_s"] > 0

    assert "torch" not in sys.modules
    return {
        "frozen_scorer_sha256": scorer_sha,
        "scorer_26_controls_passed": True,
        "static_kv_4096_bytes": kv_no_grow["final_static_cache_footprint"]["total_bytes"],
        "static_kv_8192_bytes": kv_one_grow["final_static_cache_footprint"]["total_bytes"],
        "header_and_invented_table_controls_passed": True,
        "gate_g0_g1_g2_controls_passed": True,
        "windows_crossover_pinned_a_clock_s": tel.WINDOWS_A_CLOCK_S,
        "torch_imported": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--label", required=True, help="Unique CPU preflight label under WP-0016/carbon/cpu-preflight")
    p.add_argument("--receipt-out", type=Path, help="Optional repo path for deterministic CPU verification receipt")
    args = p.parse_args()

    scratch_dir = (CARBON_RUNTIME_ROOT / "cpu-preflight" / args.label).resolve()
    scratch_dir.mkdir(parents=True, exist_ok=False)

    utf8_res = verify_utf8_child_stream_hunk(scratch_dir)
    g0_res = verify_g0_wrapper_cpu(scratch_dir)
    tel_res = verify_telemetry_and_gates_cpu(scratch_dir)
    tok_res = inspect_q0_tokenizer_composite_contracts()

    assert "torch" not in sys.modules
    receipt = {
        "packet": "WP-0016",
        "role": "eld-rd-carbon",
        "branch": "research/wp-0016-engine",
        "engine_base_commit": "61bec47689dcdf272a525185013f2dce6335fa24",
        "g0_freeze_commit": G0_FREEZE_COMMIT,
        "cpu_only": True,
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "torch_imported": "torch" in sys.modules,
        "utf8_stream_hunk_check": utf8_res,
        "g0_wrapper_verification": g0_res,
        "passive_telemetry_and_gate_processor": tel_res,
        "q0_tokenizer_composite_census": tok_res,
    }
    publish(scratch_dir / "cpu-preflight-receipt.json", receipt)
    if args.receipt_out:
        publish(args.receipt_out.resolve(), receipt)
    print(json.dumps({"status": "ok", "g0_freeze_commit": G0_FREEZE_COMMIT, "label": args.label}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
