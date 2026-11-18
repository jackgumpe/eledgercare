"""Comprehensive CPU-only verification suite for WP-0017 ablation engine, probe, and launcher.

Strictly enforces CUDA_VISIBLE_DEVICES='-1' and installs hard runtime tripwires on all
torch.cuda entry points so zero GPU calls can occur during author verification.
"""
from __future__ import annotations

import os

# Must precede any torch import (note: '-1' disables CUDA on Windows; '' unsets env vars on Win32).
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import argparse
from io import TextIOWrapper
import importlib.util
import json
import math
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if isinstance(_stream, TextIOWrapper):
        _stream.reconfigure(encoding="utf-8", errors=_stream.errors)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WP15_CARBON = ROOT / "docs/research/WP-0015/carbon"
WP15_ASTRA = ROOT / "docs/research/WP-0015/astra"
WP14 = ROOT / "docs/research/WP-0014/eld-latency-author"
WORKER = ROOT / "workers/local_ocr"
for _p in reversed((str(HERE), str(WP15_CARBON), str(WP15_ASTRA), str(WP14), str(WORKER))):
    if _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

from cases import PYTHON
from formats import digest, publish
from local_ocr import protocol
from native import MODEL


def _run_import_and_utf8_hygiene_checks(tmp_root: Path) -> dict:
    # 1. Verify zero torch import at module import time across supervisor/analyzer modules.
    code_no_torch = (
        "import sys; sys.path[:0] = ["
        + ", ".join(repr(str(p)) for p in (HERE, WP15_CARBON, WP15_ASTRA, WP14, WORKER))
        + "]; "
        "import switches, ablation_engine, span_probe, a1_analyze, launch; "
        "assert 'torch' not in sys.modules, 'torch imported prematurely!'; "
        "print('OK_NO_TORCH')"
    )
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="-1")
    out1 = subprocess.check_output([str(PYTHON), "-I", "-B", "-c", code_no_torch], env=env, encoding="utf-8")
    assert "OK_NO_TORCH" in out1

    # 2. Verify redirected stdout/stderr UTF-8 safety under -I -B with CJK and math glyphs.
    code_utf8 = (
        "import sys; sys.path[:0] = ["
        + ", ".join(repr(str(p)) for p in (HERE, WP15_CARBON, WP15_ASTRA, WP14, WORKER))
        + "]; "
        "import a1_trial, doc_trial; "
        "sys.stdout.write('UTF8_STDOUT_OK: I08O1-388 \\u5c0f \\u0394z\\n'); "
        "sys.stderr.write('UTF8_STDERR_OK: 8OI10-774 \\u5c0f\\n')"
    )
    proc_utf8 = subprocess.run(
        [str(PYTHON), "-I", "-B", "-c", code_utf8],
        env=env,
        capture_output=True,
        check=True,
    )
    assert "UTF8_STDOUT_OK: I08O1-388 \u5c0f \u0394z" in proc_utf8.stdout.decode("utf-8")
    assert "UTF8_STDERR_OK: 8OI10-774 \u5c0f" in proc_utf8.stderr.decode("utf-8")

    # 3. Verify --emit-a1-plan against real coordination a1-inputs.json without importing torch.
    a1_manifest = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0017/coordination/a1-inputs.json")
    emitted_plan = tmp_root / "emitted-a1-plan.json"
    out_plan = subprocess.check_output(
        [
            str(PYTHON),
            "-I",
            "-B",
            str(HERE / "launch.py"),
            "--emit-a1-plan",
            str(emitted_plan),
            "--a1-manifest",
            str(a1_manifest),
        ],
        env=env,
        encoding="utf-8",
    )
    meta = json.loads(out_plan.strip())
    assert digest(emitted_plan.read_bytes()) == meta["plan_sha256"]
    assert len(meta["configs"]) == 16
    return {
        "import_torch_absent": True,
        "redirected_utf8_under_isolated_flag": True,
        "emitted_a1_plan_sha256": meta["plan_sha256"],
        "emitted_a1_config_count": len(meta["configs"]),
    }


def _install_cuda_tripwires():
    import torch

    tripwire_hits = []

    def _forbid(*_a, **_kw):
        tripwire_hits.append(True)
        raise AssertionError("Forbidden CUDA call attempted during CPU-only verification!")

    torch.cuda.is_available = lambda: False
    torch.cuda.init = _forbid
    torch.cuda.synchronize = _forbid
    torch.Tensor.cuda = _forbid
    torch.nn.Module.cuda = _forbid
    return tripwire_hits


def _run_real_tokenizer_and_a1_locator_checks() -> dict:
    from tokenizers import Tokenizer
    from span_probe import (
        build_frozen_field_locator,
        extract_free_field_at_locator,
        token_ids_sha256,
    )

    class _FastTokAdapter:
        def __init__(self, tk: Tokenizer):
            self._tk = tk
            self.eos_token_id = 1

        def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
            return list(self._tk.encode(text, add_special_tokens=add_special_tokens).ids)

        def decode(self, ids: list[int], skip_special_tokens: bool = False) -> str:
            return self._tk.decode(ids, skip_special_tokens=skip_special_tokens)

    tok = _FastTokAdapter(Tokenizer.from_file(str(MODEL / "tokenizer.json")))
    a1_path = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0017/coordination/a1-inputs.json")
    a1_bytes = a1_path.read_bytes()
    a1_sha = digest(a1_bytes)
    assert a1_sha == "e7f47d141972d0e32c53d16e090fcddc237c453ecfc2eaf5d494c6d3426bc8ef"
    a1 = json.loads(a1_bytes)

    w019, w037 = a1["windows"][0], a1["windows"][1]
    loc019 = build_frozen_field_locator(
        first_page=w019["first_page"],
        identifier_page=w019["identifier_page"],
        alternatives=w019["alternatives"],
        native_token_ids=w019["by_mode"]["native"]["token_ids"],
        carbon_token_ids=w019["by_mode"]["carbon_bf16"]["token_ids"],
        tokenizer=tok,
    )
    assert loc019["native_prefix_end_index"] == 417
    assert loc019["early_pre_id_divergence"] is None
    assert loc019["competing_spans"]["lcp_offset_from_pre_space"] == 0
    assert loc019["competing_spans"]["entries"][0]["pre_space_token_ids"] == [342, 3019, 49, 19, 15, 21895]
    assert loc019["competing_spans"]["entries"][1]["pre_space_token_ids"] == [223, 6924, 49, 19, 15, 21895]

    loc037 = build_frozen_field_locator(
        first_page=w037["first_page"],
        identifier_page=w037["identifier_page"],
        alternatives=w037["alternatives"],
        native_token_ids=w037["by_mode"]["native"]["token_ids"],
        carbon_token_ids=w037["by_mode"]["carbon_bf16"]["token_ids"],
        tokenizer=tok,
    )
    assert loc037["native_prefix_end_index"] == 40
    assert loc037["early_pre_id_divergence"]["step_index"] == 7
    assert loc037["early_pre_id_divergence"]["native_token_id"] == 17979
    assert loc037["early_pre_id_divergence"]["carbon_token_id"] == 16234
    assert loc037["competing_spans"]["lcp_offset_from_pre_space"] == 1
    assert loc037["competing_spans"]["entries"][0]["common_boundary_token_ids"] == [26, 90169, 553, 15, 30591]
    assert loc037["competing_spans"]["entries"][1]["common_boundary_token_ids"] == [1892, 43, 553, 15, 30591]

    # Verify structural free extraction on both anchored streams + synthetic 3rd-reading + malformed block.
    f019_nat = extract_free_field_at_locator(w019["by_mode"]["native"]["token_ids"], tok, loc019)
    f019_car = extract_free_field_at_locator(w019["by_mode"]["carbon_bf16"]["token_ids"], tok, loc019)
    assert f019_nat["observed_id"] == "I08O1-388" and f019_nat["prefix_identical_to_native"] is True
    assert f019_car["observed_id"] == "108O1-388" and f019_car["prefix_identical_to_native"] is True

    f037_nat = extract_free_field_at_locator(w037["by_mode"]["native"]["token_ids"], tok, loc037)
    f037_car = extract_free_field_at_locator(w037["by_mode"]["carbon_bf16"]["token_ids"], tok, loc037)
    assert f037_nat["observed_id"] == "8OI10-774" and f037_nat["prefix_identical_to_native"] is True
    assert f037_car["observed_id"] == "80I10-774" and f037_car["prefix_identical_to_native"] is False
    assert f037_car["first_prefix_diff_vs_native"]["step_index"] == 7

    # Synthetic 3rd reading ("80110-774") at the same structural site without target-string search:
    third_ids = (
        w037["by_mode"]["native"]["token_ids"][:40]
        + tok.encode(" 80110-774", add_special_tokens=False)
        + w037["by_mode"]["native"]["token_ids"][46:]
    )
    f037_third = extract_free_field_at_locator(third_ids, tok, loc037)
    assert f037_third["aligned"] is True
    assert f037_third["observed_id"] == "80110-774"
    assert f037_third["matched_probed_branch_role"] is None

    # Malformed block (missing <FORK> 128829):
    broken_ids = [t for t in w037["by_mode"]["native"]["token_ids"] if t != 128829]
    f037_broken = extract_free_field_at_locator(broken_ids, tok, loc037)
    assert f037_broken["aligned"] is False

    return {
        "a1_manifest_sha256": a1_sha,
        "window_019_native_sha256": token_ids_sha256(w019["by_mode"]["native"]["token_ids"]),
        "window_019_carbon_sha256": token_ids_sha256(w019["by_mode"]["carbon_bf16"]["token_ids"]),
        "window_037_native_sha256": token_ids_sha256(w037["by_mode"]["native"]["token_ids"]),
        "window_037_carbon_sha256": token_ids_sha256(w037["by_mode"]["carbon_bf16"]["token_ids"]),
        "window_019_divergence_step": 417,
        "window_037_divergence_step": 41,
        "window_037_early_coord_step": 7,
        "structural_locator_third_reading_and_malformed_controls": True,
    }


def _load_real_model_python_modules():
    """Load real Unlimited-OCR-2 Python modules into a synthetic package namespace on CPU."""
    pkg_name = "_wp0017_uocr_cpu_pkg"
    if pkg_name in sys.modules:
        return (
            sys.modules[f"{pkg_name}.configuration_deepseek_v2"],
            sys.modules[f"{pkg_name}.modeling_deepseekv2"],
            sys.modules[f"{pkg_name}.modeling_unlimitedocr"],
        )

    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = [str(MODEL)]
    pkg.__package__ = pkg_name
    sys.modules[pkg_name] = pkg

    mod_order = (
        "configuration_deepseek_v2",
        "packing_patch",
        "_sparse_base_impl",
        "dash_attention",
        "modeling_deepseekv2",
        "conversation",
        "deepencoder",
        "modeling_unlimitedocr",
    )
    for mname in mod_order:
        full_name = f"{pkg_name}.{mname}"
        spec = importlib.util.spec_from_file_location(full_name, MODEL / f"{mname}.py")
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = pkg_name
        sys.modules[full_name] = mod
        spec.loader.exec_module(mod)

    return (
        sys.modules[f"{pkg_name}.configuration_deepseek_v2"],
        sys.modules[f"{pkg_name}.modeling_deepseekv2"],
        sys.modules[f"{pkg_name}.modeling_unlimitedocr"],
    )


def _build_mini_uocr_model(
    cfg_mod,
    dsv2_mod,
    uocr_mod,
    *,
    dtype,
    seed: int = 17,
    vocab_size: int = 256,
    image_token_id: int = 240,
    page_token_id: int = 241,
):
    """Build a miniature UnlimitedOCRForCausalLM-compatible instance using real DeepseekV2MoE & DashAttention."""
    import torch
    import torch.nn as nn
    from transformers.modeling_outputs import BaseModelOutputWithPast

    torch.manual_seed(seed)
    cfg = cfg_mod.DeepseekV2Config(
        vocab_size=vocab_size,
        hidden_size=64,
        intermediate_size=128,
        moe_intermediate_size=32,
        num_hidden_layers=2,
        num_attention_heads=2,
        num_key_value_heads=2,
        n_routed_experts=4,
        num_experts_per_tok=2,
        n_shared_experts=1,
        first_k_dense_replace=1,
        moe_layer_freq=1,
        topk_method="greedy",
        scoring_func="softmax",
        norm_topk_prob=False,
        routed_scaling_factor=1.0,
        aux_loss_alpha=0.0,
        seq_aux=False,
        q_lora_rank=None,
        kv_lora_rank=None,
        qk_nope_head_dim=0,
        qk_rope_head_dim=0,
        v_head_dim=32,
        use_mla=False,
        max_position_embeddings=2048,
        rms_norm_eps=1e-6,
        bos_token_id=0,
        eos_token_id=1,
        pad_token_id=2,
        tie_word_embeddings=False,
    )
    cfg._attn_implementation = "eager"
    cfg._ring_window = 32
    cfg.sliding_window = None
    cfg.sparse_attention_config = {
        "training_stage": "dash",
        "use_sparse_attention": True,
        "sparse_attention_freq": [1, 1],
        "sparse_block_size": 16,
        "sparse_local_block": 2,
        "sparse_init_block": 1,
        "sparse_topk_blocks": 4,
        "sparse_index_dim": 32,
        "sparse_num_index_heads": 1,
        "sparse_main_rope_mode": "page2d",
        "sparse_main_rope_tok_freq_mode": "resample",
        "sparse_rope_mode": "page2d",
        "sparse_rope_page_mod": 2,
        "sparse_rope_page_pairs": 1,
        "sparse_rope_page_span": 0,
        "sparse_rope_page_theta": 256.0,
        "sparse_rope_theta": 500000.0,
        "sparse_rope_tok_freq_mode": "resample",
        "sparse_rope_tok_theta": 10000.0,
        "image_bucket_constraint": True,
        "image_token_id": image_token_id,
        "page_token_id": page_token_id,
        "per_page_image_tokens": 8,
        "dash_router": "entmax_topk_perlayer",
        "dash_stage0": "head_cls",
        "dash_topk_blocks": 2,
        "dash_query_chunk": 128,
        "dash_scaling_factor": 64.0,
        "dash_prior_floor": 1e-4,
        "dash_sigma": 1.0,
        "dash_image_only": True,
        "dash_use_triton": False,
        "dash_scale_per_layer": [64.0, 64.0],
        "dash_floor_per_layer": [1e-4, 1e-4],
    }

    class MiniDecoder(dsv2_mod.DeepseekV2Model):
        def __init__(self, c):
            super().__init__(c)
            self.sam_model = nn.Linear(8, 8, bias=False)
            self.projector = nn.Linear(8, c.hidden_size, bias=False)

        def forward(
            self,
            input_ids=None,
            attention_mask=None,
            position_ids=None,
            past_key_values=None,
            inputs_embeds=None,
            use_cache=None,
            output_attentions=None,
            output_hidden_states=None,
            images=None,
            images_seq_mask=None,
            images_spatial_crop=None,
            return_dict=True,
        ):
            if input_ids is not None and getattr(input_ids, "ndim", 0) == 2:
                _rope2d = None
                _layers = list(self.layers)
                _first = _layers[0].self_attn
                if input_ids.shape[-1] > 1 and getattr(_first, "main_rope_mode", "1d") == "page2d":
                    _rope2d = _first.indexer._build_page_rope_pos(input_ids, input_ids.shape[-1])
                _meta = getattr(_first.indexer, "_page_rope_meta", None) if _rope2d is not None else None
                _dec_allow = None
                if dsv2_mod._INFER["on"] and past_key_values is not None:
                    _dec_allow = uocr_mod._uocr_dash_decode_allow(_first.indexer, input_ids, past_key_values)
                for _lyr in _layers:
                    _attn = _lyr.self_attn
                    _attn._sparse_source_input_ids = input_ids
                    _attn._main_rope_pos_2d = _rope2d
                    if _meta is not None:
                        _attn.indexer._page_rope_meta = _meta
                    _attn._dash_dec_allow = _dec_allow

            if inputs_embeds is None:
                inputs_embeds = self.get_input_embeddings()(input_ids)

            if images is not None and input_ids is not None and input_ids.shape[1] != 1:
                vis_raw = images[0][1]
                vis_feat = self.projector(self.sam_model(vis_raw)).reshape(-1, self.config.hidden_size)
                mask = images_seq_mask[0].unsqueeze(-1).to(inputs_embeds.device)
                inputs_embeds[0].masked_scatter_(mask, vis_feat.to(inputs_embeds.dtype))

            return super().forward(
                input_ids=None,
                attention_mask=attention_mask,
                past_key_values=past_key_values,
                inputs_embeds=inputs_embeds,
                use_cache=use_cache,
                position_ids=position_ids,
                output_attentions=output_attentions,
                output_hidden_states=output_hidden_states,
                return_dict=return_dict,
            )

    class MiniCausalLM(nn.Module):
        def __init__(self, c):
            super().__init__()
            self.config = c
            self.model = MiniDecoder(c)
            self.lm_head = nn.Linear(c.hidden_size, c.vocab_size, bias=False)

        _uocr_generate = uocr_mod.UnlimitedOCRForCausalLM._uocr_generate

    MiniCausalLM.__module__ = uocr_mod.__name__
    m = MiniCausalLM(cfg).to(dtype).eval()
    # Non-zero head_cls so stage0 == 'head_cls' exercises block-summary weighted softmax.
    for lyr in m.model.layers:
        torch.manual_seed(seed + 100 + lyr.self_attn.layer_idx)
        lyr.self_attn.dash_router.head_cls.data.normal_(0.0, 0.2)
    return m


class _MiniTokenizer:
    eos_token_id = 1

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        out: list[int] = []
        i = 0
        while i < len(text):
            if text.startswith("<PAGE>", i):
                out.append(241)
                i += 6
            elif text.startswith("<BLOCK>", i):
                out.append(242)
                i += 7
            elif text.startswith("<FORK>", i):
                out.append(243)
                i += 6
            else:
                out.append(10 + (ord(text[i]) % 200))
                i += 1
        return out

    def decode(self, ids: list[int], skip_special_tokens: bool = False) -> str:
        pieces = []
        for raw_id in ids:
            t = int(raw_id)
            if t == 1:
                if not skip_special_tokens:
                    pieces.append("<EOS>")
            elif t == 240:
                pieces.append("<image>")
            elif t == 241:
                pieces.append("<PAGE>")
            elif t == 242:
                pieces.append("<BLOCK>")
            elif t == 243:
                pieces.append("<FORK>")
            else:
                pieces.append(f"t{t}")
        return "".join(pieces)

    def convert_tokens_to_ids(self, toks: list[str]) -> list[int]:
        m = {"<PAGE>": 241, "<BLOCK>": 242, "<FORK>": 243}
        return [m[t] for t in toks]


def _make_mini_inputs(dtype, *, n_pages: int = 3):
    import torch

    torch.manual_seed(99)
    # 3 pages, each <PAGE> (241) + 8 image tokens (240) + 4 prompt tokens -> s_prefill = 1 + 3*9 + 4 = 32
    ids = [0]
    seq_mask = [False]
    for _ in range(n_pages):
        ids.append(241)
        seq_mask.append(False)
        ids.extend([240] * 8)
        seq_mask.extend([True] * 8)
    ids.extend([21, 22, 23, 24])
    seq_mask.extend([False] * 4)

    input_ids = torch.tensor(ids, dtype=torch.long)
    mask_t = torch.tensor(seq_mask, dtype=torch.bool)
    vis_ori = torch.randn(n_pages * 8, 8, dtype=dtype)
    vis_crop = torch.zeros(1, 8, dtype=dtype)
    spatial = torch.ones((n_pages, 2), dtype=torch.long)
    return input_ids, (vis_crop, vis_ori), mask_t, spatial


def _run_six_switch_and_probe_checks() -> dict:
    import copy
    import torch
    from engine import apply_carbon_patches
    from ablation_engine import extract_engine_runtime_hooks
    from switches import (
        DESIGN_14_NAMES,
        SwitchConfig,
        apply_ablation_patches,
        build_static_dash_cache_cls,
        resolve_mode,
    )
    from span_probe import clone_kv_cache, run_teacher_forced_window_probe

    cfg_mod, dsv2_mod, uocr_mod = _load_real_model_python_modules()
    tok = _MiniTokenizer()

    # Make EOS fire deterministically after ~14 decode steps (after 3 <PAGE> tokens emitted).
    base_fp32 = _build_mini_uocr_model(cfg_mod, dsv2_mod, uocr_mod, dtype=torch.float32, seed=42)
    with torch.no_grad():
        base_fp32.lm_head.weight.mul_(0.5)
        base_fp32.lm_head.weight[241].mul_(1.8)  # encourage <PAGE> early so PageCountGuard reaches 3 pages
        base_fp32.lm_head.weight[1].mul_(1.65)   # encourage EOS once marker_cum >= 3

    input_ids, imgs, seq_mask, spatial = _make_mini_inputs(torch.float32, n_pages=3)

    # 1. Run genuine unmodified upstream _uocr_generate in FP32.
    ref_model_fp32 = copy.deepcopy(base_fp32)
    ref_res_fp32 = ref_model_fp32._uocr_generate(
        tok,
        input_ids,
        imgs,
        seq_mask,
        spatial,
        max_new_tokens=20,
        max_length=512,
        temperature=0.0,
        page_count_guard=True,
        max_page_tokens=200,
        ngram_size=4,
        ngram_window=32,
        ngram_whitelist=set(),
        dash_topm=4,
        stream=False,
    )
    ref_tokens_fp32 = list(ref_res_fp32["token_ids"])
    assert len(ref_tokens_fp32) >= 3

    # 2. Run genuine WP-0015 apply_carbon_patches(mode='carbon_bf16') on FP32 copy and test closure extraction.
    wp15_car_fp32 = copy.deepcopy(base_fp32)
    wp15_spec = apply_carbon_patches(wp15_car_fp32, mode="carbon_bf16")
    wp15_res_fp32 = wp15_car_fp32._uocr_generate(
        tok,
        input_ids,
        imgs,
        seq_mask,
        spatial,
        max_new_tokens=20,
        max_length=512,
        temperature=0.0,
        page_count_guard=True,
        max_page_tokens=200,
        ngram_size=4,
        ngram_window=32,
        ngram_whitelist=set(),
        dash_topm=4,
        stream=True,
    )
    assert wp15_res_fp32["token_ids"] == ref_tokens_fp32

    class CarbonEngine:
        def __init__(self, mdl, sp):
            self.model = mdl
            self.tokenizer = tok
            self.spec = sp

    fake_car = CarbonEngine(wp15_car_fp32, wp15_spec)
    car_hooks = extract_engine_runtime_hooks(fake_car)
    assert car_hooks["use_gather_decode"] is True and car_hooks["static_cache_cls"] is not None

    # 3. Exercise all 14 design switch vectors + pair removals in FP32 and verify BOTH token parity AND op counters!
    checked_modes = [
        "all_off",
        "all_on",
        *[n for n in DESIGN_14_NAMES if n not in ("native", "carbon_bf16")],
        "remove_S1a_S1c",
        "remove_S1b_S2",
    ]
    counter_audit = {}
    for mname in checked_modes:
        rm = resolve_mode(mname)
        sc = rm.switch_config
        mdl = copy.deepcopy(base_fp32)
        cnt, s_cls = apply_ablation_patches(mdl, switch_cfg=sc)

        # Capture stdout during generation to verify S0 streamer behavior cleanly without polluting console.
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            res = mdl._uocr_generate(
                tok,
                input_ids,
                imgs,
                seq_mask,
                spatial,
                max_new_tokens=20,
                max_length=512,
                temperature=0.0,
                page_count_guard=True,
                max_page_tokens=200,
                ngram_size=4,
                ngram_window=32,
                ngram_whitelist=set(),
                dash_topm=4,
                stream=True,
            )
        assert res["token_ids"] == ref_tokens_fp32, f"FP32 token parity failed on {mname}: {res['token_ids']} vs {ref_tokens_fp32}"
        snap = cnt.snapshot()
        n_gen = len(res["token_ids"])

        # S0 assertions (ignore upstream [PageRope]/[PageAwareKL]/[debug] one-time prefill prints)
        non_diag_lines = [ln for ln in buf.getvalue().splitlines() if ln.strip() and not ln.startswith("[")]
        if sc.no_text_streamer:
            assert snap["s0_streamer_put_calls"] == 0 and snap["s0_streamer_end_calls"] == 0
            assert snap["s0_silent_accum_tokens"] == n_gen
            assert len(non_diag_lines) == 0
        else:
            assert snap["s0_streamer_put_calls"] == n_gen and snap["s0_streamer_end_calls"] == 1
            assert snap["s0_silent_accum_tokens"] == 0
            assert len(non_diag_lines) > 0

        # S1a assertions (on CPU, _grouped_mm is CUDA-only so S1a=True increments fallback_calls; we test mocked CUDA _grouped_mm below too)
        if sc.packed_moe_prefill:
            assert snap["s1a_prefill_fallback_calls"] == 1 and snap["s1a_prefill_linear_loop_calls"] == 0
        else:
            assert snap["s1a_prefill_linear_loop_calls"] == 1 and snap["s1a_prefill_fallback_calls"] == 0

        # S1b assertions
        if sc.packed_moe_decode_bmm:
            assert snap["s1b_decode_bmm_calls"] > 0 and snap["s1b_decode_linear_loop_calls"] == 0
        else:
            assert snap["s1b_decode_linear_loop_calls"] > 0 and snap["s1b_decode_bmm_calls"] == 0

        # S1c assertions (Layer 0 dense + Layer 1 shared + Layer 1 routed)
        if sc.fused_gate_up_proj:
            assert snap["s1c_dense_fused_calls"] > 0 and snap["s1c_dense_unfused_calls"] == 0
            assert snap["s1c_shared_fused_calls"] > 0 and snap["s1c_shared_unfused_calls"] == 0
            assert snap["s1c_routed_fused_op_calls"] > 0 and snap["s1c_routed_unfused_op_calls"] == 0
        else:
            assert snap["s1c_dense_unfused_calls"] > 0 and snap["s1c_dense_fused_calls"] == 0
            assert snap["s1c_shared_unfused_calls"] > 0 and snap["s1c_shared_fused_calls"] == 0
            assert snap["s1c_routed_unfused_op_calls"] > 0 and snap["s1c_routed_fused_op_calls"] == 0

        # S2 assertions (with max_new_tokens=20, s_prefill=32, block_size=16: max_cap=84 clamps requested 4096 -> 96)
        if sc.gather_sparse_decode:
            assert snap["s2_static_gather_decode_calls"] > 0 and snap["s2_dynamic_masked_decode_calls"] == 0
            assert res["cache_telemetry"]["cache_type"] == "StaticDashCache"
            assert res["cache_telemetry"]["requested_init_cap"] == 4096
            assert res["cache_telemetry"]["init_cap_tok"] == 96
            assert res["cache_telemetry"]["reallocations"] == 0
        else:
            assert snap["s2_dynamic_masked_decode_calls"] > 0 and snap["s2_static_gather_decode_calls"] == 0
            assert res["cache_telemetry"]["cache_type"] == "DynamicCache"

        # S3 assertions
        if sc.gpu_burst_stride_8:
            assert snap["s3_burst_chunks"] > 0 and snap["s3_single_step_iters"] == 0
        else:
            assert snap["s3_single_step_iters"] > 0 and snap["s3_burst_chunks"] == 0

        counter_audit[mname] = sc.bits

    # 4. Verify BF16 bit-exactness of all_off vs genuine Native AND all_on vs genuine WP-0015 CarbonEngine('carbon_bf16')!
    base_bf16 = copy.deepcopy(base_fp32).to(torch.bfloat16)
    in_ids_bf, imgs_bf, mask_bf, spat_bf = _make_mini_inputs(torch.bfloat16, n_pages=3)

    nat_bf16 = copy.deepcopy(base_bf16)
    off_bf16 = copy.deepcopy(base_bf16)
    apply_ablation_patches(off_bf16, switch_cfg=SwitchConfig.from_bits("000000"))

    car_bf16 = copy.deepcopy(base_bf16)
    apply_carbon_patches(car_bf16, mode="carbon_bf16")
    on_bf16 = copy.deepcopy(base_bf16)
    apply_ablation_patches(on_bf16, switch_cfg=SwitchConfig.from_bits("111111"))

    import io
    from contextlib import redirect_stdout

    with redirect_stdout(io.StringIO()):
        r_nat = nat_bf16._uocr_generate(
            tok, in_ids_bf, imgs_bf, mask_bf, spat_bf, max_new_tokens=16, page_count_guard=True, ngram_size=4, stream=True
        )
        r_off = off_bf16._uocr_generate(
            tok, in_ids_bf, imgs_bf, mask_bf, spat_bf, max_new_tokens=16, page_count_guard=True, ngram_size=4, stream=True
        )
        r_car = car_bf16._uocr_generate(
            tok, in_ids_bf, imgs_bf, mask_bf, spat_bf, max_new_tokens=16, page_count_guard=True, ngram_size=4, stream=True
        )
        r_on = on_bf16._uocr_generate(
            tok, in_ids_bf, imgs_bf, mask_bf, spat_bf, max_new_tokens=16, page_count_guard=True, ngram_size=4, stream=True
        )
    assert r_nat["token_ids"] == r_off["token_ids"], "BF16 all_off must match genuine native bit-for-bit"
    assert r_car["token_ids"] == r_on["token_ids"], "BF16 all_on must match genuine carbon_bf16 bit-for-bit"

    # 4b. Explicitly exercise the S1a=True grouped_mm branch for BOTH S1c=False (unfused) and S1c=True (fused),
    #     verifying exact tensor shapes, column-majormat_b strides, int32 offs, and 0.0 FP32 drift vs native!
    orig_grouped_mm = getattr(torch, "_grouped_mm", None)
    gmm_calls = []

    def _ref_grouped_mm(mat_a, mat_b, *, offs):
        assert mat_a.ndim == 2 and mat_b.ndim == 3
        assert mat_b.stride(1) == 1, f"Expected column-major per-group mat_b stride(1)==1, got {mat_b.stride()}"
        assert offs.dtype == torch.int32 and offs.ndim == 1 and offs.shape[0] == mat_b.shape[0]
        gmm_calls.append((tuple(mat_a.shape), tuple(mat_b.shape), offs.tolist()))
        pieces = []
        prev = 0
        for g_idx, end in enumerate(offs.tolist()):
            if end > prev:
                pieces.append(mat_a[prev:end] @ mat_b[g_idx])
            prev = end
        return torch.cat(pieces, dim=0) if pieces else mat_a.new_empty((0, mat_b.shape[2]))

    torch._grouped_mm = _ref_grouped_mm
    try:
        for s1c_flag in (False, True):
            gmm_calls.clear()
            g_mdl = copy.deepcopy(base_fp32)
            g_cnt, _ = apply_ablation_patches(
                g_mdl,
                switch_cfg=SwitchConfig(
                    no_text_streamer=True,
                    packed_moe_prefill=True,
                    packed_moe_decode_bmm=False,
                    fused_gate_up_proj=s1c_flag,
                    gather_sparse_decode=False,
                    gpu_burst_stride_8=False,
                ),
            )
            g_mdl.model.layers[1].mlp._force_grouped_mm_for_test = True
            with redirect_stdout(io.StringIO()):
                g_res = g_mdl._uocr_generate(
                    tok, input_ids, imgs, seq_mask, spatial, max_new_tokens=6, page_count_guard=True, ngram_size=4, stream=False
                )
            assert g_res["token_ids"] == ref_tokens_fp32[: len(g_res["token_ids"])]
            gs = g_cnt.snapshot()
            assert gs["s1a_prefill_grouped_mm_calls"] == 1 and gs["s1a_prefill_fallback_calls"] == 0
            # Unfused makes 3 _grouped_mm calls (gate, up, down); fused makes 2 ([gate;up], down)!
            assert len(gmm_calls) == (2 if s1c_flag else 3)
    finally:
        if orig_grouped_mm is not None:
            torch._grouped_mm = orig_grouped_mm

    # 5. Verify StaticDashCache _grow reallocation path produces 0.0 drift vs large initial capacity.
    static_cls = build_static_dash_cache_cls()
    from transformers.cache_utils import DynamicCache

    dsv2_mod.configure_dash_inference(base_fp32.model, True, topm=4)
    try:
        dc1 = DynamicCache()
        out_p = base_fp32.model(
            input_ids=input_ids.unsqueeze(0),
            past_key_values=dc1,
            use_cache=True,
            position_ids=torch.arange(input_ids.shape[0])[None],
            images=[(imgs[0], imgs[1], spatial)],
            images_seq_mask=seq_mask.unsqueeze(0),
            images_spatial_crop=spatial,
            return_dict=True,
        )
        sc_small = static_cls(out_p.past_key_values, base_fp32.model, init_cap=32, max_cap=32, act_clamp=dsv2_mod._ACT_CLAMP)
        sc_large = static_cls(out_p.past_key_values, base_fp32.model, init_cap=256, max_cap=256, act_clamp=dsv2_mod._ACT_CLAMP)
        assert sc_small.init_cap_tok == 48 and sc_large.init_cap_tok == 256
        # Step 17 tokens (seq_len 32 -> 49 > 48) across layer 0 to trigger _grow on sc_small:
        from switches import gather_sparse_decode_step

        h_step = out_p.last_hidden_state[:, -1:]
        base_fp32.model.layers[0].self_attn._sparse_source_input_ids = torch.tensor([[35]], dtype=torch.long)
        for step_off in range(17):
            pos_step = torch.tensor([[32 + step_off]], dtype=torch.long)
            o_small, _, _, _ = gather_sparse_decode_step(base_fp32.model.layers[0].self_attn, h_step, pos_step, sc_small, dsv2_mod)
            o_large, _, _, _ = gather_sparse_decode_step(base_fp32.model.layers[0].self_attn, h_step, pos_step, sc_large, dsv2_mod)
        assert sc_small.reallocations == 1 and sc_large.reallocations == 0
        assert float((o_small - o_large).abs().max().item()) == 0.0
    finally:
        dsv2_mod.configure_dash_inference(base_fp32.model, False)

    # 6. Verify Teacher-Forced Span-Logit Probe:
    #    (a) q_len > 1 occurs ONLY once (prompt prefill); all prefix & branch decode steps have q_len == 1!
    #    (b) clone_kv_cache branched evaluation matches full from-scratch serial replay with 0.0 diff!
    orig_build = uocr_mod._uocr_build_inputs

    def _mini_build_inputs(_tok, _prompt, _images, **_kw):
        return _make_mini_inputs(torch.float32, n_pages=len(_images))

    uocr_mod._uocr_build_inputs = _mini_build_inputs
    try:
        for s2_flag in (False, True):
            probe_mdl = copy.deepcopy(base_fp32)
            p_cnt, p_scls = apply_ablation_patches(
                probe_mdl,
                switch_cfg=SwitchConfig(
                    no_text_streamer=True,
                    packed_moe_prefill=False,
                    packed_moe_decode_bmm=s2_flag,
                    fused_gate_up_proj=s2_flag,
                    gather_sparse_decode=s2_flag,
                    gpu_burst_stride_8=False,
                ),
            )
            q_lens = []
            orig_m_fwd = probe_mdl.model.forward

            def _track_qlen(*a, **kw):
                inp = kw.get("input_ids", a[0] if a else None)
                if inp is not None:
                    q_lens.append(int(inp.shape[1]))
                return orig_m_fwd(*a, **kw)

            probe_mdl.model.forward = _track_qlen

            synth_locator = {
                "window_label": "037",
                "first_page": 37,
                "identifier_page": 37,
                "early_pre_id_divergence": {
                    "step_index": 2,
                    "native_token_id": 30,
                    "carbon_token_id": 31,
                },
                "competing_spans": {
                    "lcp_offset_from_pre_space": 1,
                    "entries": [
                        {
                            "role": "native_id",
                            "identifier": "8OI10-774",
                            "text_from_pre_space": " 8OI10-774",
                            "pre_space_token_ids": [20, 41, 42, 43],
                            "pre_space_token_pieces": [" ", "8", "OI", "10"],
                            "common_boundary_token_ids": [41, 42, 43],
                            "common_boundary_token_pieces": ["8", "OI", "10"],
                        },
                        {
                            "role": "carbon_id",
                            "identifier": "80I10-774",
                            "text_from_pre_space": " 80I10-774",
                            "pre_space_token_ids": [20, 51, 52, 43],
                            "pre_space_token_pieces": [" ", "80", "I", "10"],
                            "common_boundary_token_ids": [51, 52, 43],
                            "common_boundary_token_pieces": ["80", "I", "10"],
                        },
                    ],
                },
            }
            prefix_ids = [241, 242, 30, 243, 35, 36]
            p_hooks = {
                "model": probe_mdl,
                "tokenizer": tok,
                "use_gather_decode": s2_flag,
                "static_cache_cls": p_scls,
            }
            call_kw = protocol.build_call_kwargs(3)
            res_branched = run_teacher_forced_window_probe(
                engine_hooks=p_hooks,
                images=[object(), object(), object()],
                locator=synth_locator,
                prefix_tokens=prefix_ids,
                prefix_label="forced_native",
                call_kwargs=call_kw,
            )
            # Assert exactly ONE prefill (q_len == 32) and every subsequent forward has q_len == 1!
            assert q_lens[0] == 32 and all(q == 1 for q in q_lens[1:])
            assert res_branched["early_pre_id_divergence_telemetry"]["step_index"] == 2
            assert len(res_branched["divergence_step_summary"]["guarded_competing_candidates"]) == 2
            # Because only 1 <PAGE> (241) is in prefix_ids and expected_pages == 3, EOS (1) is banned by PageCountGuard!
            assert res_branched["divergence_step_summary"]["guard_meta"]["eos_banned_by_page_guard"] is True
            assert abs(
                res_branched["D_native_minus_carbon_guarded_nats"]
                - res_branched["D_native_minus_carbon_with_space_guarded_nats"]
            ) < 1e-12

            # Verify branch-1 (carbon_id, which ran AFTER branch-0 mutated its cloned cache!) matches
            # running carbon_id FIRST as the sole/primary sequence from scratch with 0.0 numerical drift!
            swapped_locator = copy.deepcopy(synth_locator)
            swapped_locator["competing_spans"]["entries"] = list(reversed(synth_locator["competing_spans"]["entries"]))
            res_swapped = run_teacher_forced_window_probe(
                engine_hooks=p_hooks,
                images=[object(), object(), object()],
                locator=swapped_locator,
                prefix_tokens=prefix_ids,
                prefix_label="forced_native",
                call_kwargs=call_kw,
            )
            b1_from_branched = res_branched["branches"][1]["ell_full_with_space_guarded_nats"]
            b1_from_scratch = res_swapped["branches"][0]["ell_full_with_space_guarded_nats"]
            assert abs(b1_from_branched - b1_from_scratch) == 0.0
    finally:
        uocr_mod._uocr_build_inputs = orig_build

    return {
        "modes_verified_fp32": len(checked_modes),
        "bf16_all_off_matches_native": True,
        "bf16_all_on_matches_carbon_bf16": True,
        "static_cache_grow_zero_drift": True,
        "serial_qlen1_and_cache_clone_zero_drift": True,
    }


def _run_a1_analyzer_and_doc_harness_checks(tmp_root: Path) -> dict:
    from PIL import Image
    import pypdfium2
    from a1_analyze import analyze_a1_segments
    from doc_trial import execute_doc_segment
    from switches import CANONICAL_A1_CONFIGS, resolve_mode
    from span_probe import token_ids_sha256

    a1_manifest = json.loads(
        Path("C:/Users/jackg/eLedgerCare-Speed/WP-0017/coordination/a1-inputs.json").read_bytes()
    )
    nat_019 = a1_manifest["windows"][0]["by_mode"]["native"]["token_ids"]
    car_019 = a1_manifest["windows"][0]["by_mode"]["carbon_bf16"]["token_ids"]
    nat_037 = a1_manifest["windows"][1]["by_mode"]["native"]["token_ids"]
    car_037 = a1_manifest["windows"][1]["by_mode"]["carbon_bf16"]["token_ids"]

    def _make_seg(mode_name: str, *, culprit_mode: str = "single_s1c") -> dict:
        rm = resolve_mode(mode_name)
        sc = rm.switch_config
        if culprit_mode == "single_s1c":
            flips = sc.fused_gate_up_proj
        else:
            # Pair interaction: flips whenever EITHER S1b or S1c is active!
            flips = (sc.packed_moe_decode_bmm or sc.fused_gate_up_proj)

        w0_ids = car_019 if flips else nat_019
        w1_ids = car_037 if flips else nat_037
        id0 = "108O1-388" if flips else "I08O1-388"
        id1 = "80I10-774" if flips else "8OI10-774"
        d_val = [-0.45, -0.35] if flips else [0.45, 0.35]
        t_win = [44.0 + (0.0 if sc.gather_sparse_decode else 6.0), 43.0 + (0.0 if sc.packed_moe_decode_bmm else 5.0)]

        free_wins = []
        for w_idx, (lbl, ids) in enumerate((("019", w0_ids), ("037", w1_ids))):
            ep = None
            if rm.switch_config.bits in ("000000", "111111"):
                ref = "native" if rm.switch_config.bits == "000000" else "carbon_bf16"
                exp_ids = (nat_019 if w_idx == 0 else nat_037) if ref == "native" else (car_019 if w_idx == 0 else car_037)
                ep = {
                    "reference_anchor": ref,
                    "exact_token_array_match": (ids == exp_ids),
                    "observed_token_ids_sha256": token_ids_sha256(ids),
                    "expected_token_ids_sha256": token_ids_sha256(exp_ids),
                    "eos_excluded_verified": True,
                    "finish_reason_stop": True,
                    "first_diff": None,
                }
            free_wins.append(
                {
                    "window_label": lbl,
                    "finish_reason": "stop",
                    "eos_excluded_verified": True,
                    "window_token_ids_sha256": token_ids_sha256(ids),
                    "endpoint_parity": ep,
                    "effective_prefill_dispatch": "grouped_mm" if sc.packed_moe_prefill else "native_linear_loop",
                }
            )

        return {
            "mode": mode_name,
            "canonical_mode": rm.canonical_name,
            "implementation": rm.implementation,
            "observer_kind": "test_observer",
            "switch_bits": sc.bits,
            "ordinary_window_seconds": t_win,
            "ordinary_two_window_sum_s": sum(t_win),
            "free_ids": [id0, id1],
            "all_free_fields_aligned": True,
            "all_windows_finished_stop": True,
            "all_windows_eos_excluded": True,
            "free_windows": free_wins,
            "probe_windows": [
                {
                    "window_label": "019",
                    "forced_native_D_passes_guarded_nats": [d_val[0], d_val[0]],
                    "history_shift_D_free_minus_D_native_guarded_nats": 0.0,
                },
                {
                    "window_label": "037",
                    "forced_native_D_passes_guarded_nats": [d_val[1], d_val[1]],
                    "history_shift_D_free_minus_D_native_guarded_nats": (-0.05 if flips else 0.0),
                },
            ],
        }

    # Case A: Single removal (remove_S1c) restores both IDs.
    segs_single = [_make_seg(m, culprit_mode="single_s1c") for m in CANONICAL_A1_CONFIGS]
    res_single = analyze_a1_segments(segs_single, a1_manifest)
    assert res_single["anchor_verification"]["anchor_gate_passed"] is True
    assert res_single["surgical_selection_status"] == "selected_single_removal"
    assert res_single["recommended_surgical_mode"] == "remove_S1c"
    assert res_single["recommended_surgical_bits"] == "111011"
    assert res_single["pair_removals_needed"] is False

    # Case B: Pair interaction (S1b + S1c) -> singles require pair -> pair restores both IDs.
    segs_pair = [_make_seg(m, culprit_mode="pair_s1b_s1c") for m in CANONICAL_A1_CONFIGS]
    res_pair_interim = analyze_a1_segments(segs_pair, a1_manifest)
    assert res_pair_interim["surgical_selection_status"] == "awaiting_eligible_pair_removals"
    assert res_pair_interim["eligible_pair_removals"] == ["remove_S1b_S1c"]
    segs_pair.append(_make_seg("remove_S1b_S1c", culprit_mode="pair_s1b_s1c"))
    res_pair_done = analyze_a1_segments(segs_pair, a1_manifest)
    assert res_pair_done["surgical_selection_status"] == "selected_pair_removal"
    assert res_pair_done["recommended_surgical_mode"] == "remove_S1b_S1c"
    assert res_pair_done["recommended_surgical_bits"] == "110011"

    # Case C: Endpoint parity failure blocks attribution!
    import copy

    segs_bad = copy.deepcopy(segs_single)
    segs_bad[1]["free_windows"][0]["window_token_ids_sha256"] = "0" * 64
    res_bad = analyze_a1_segments(segs_bad, a1_manifest)
    assert res_bad["anchor_verification"]["anchor_gate_passed"] is False
    assert res_bad["attribution_status"] == "blocked_endpoint_parity_mismatch"
    assert res_bad["recommended_surgical_mode"] is None

    # Case D: Stage A2/A3 doc_trial.py reusing Astra trial.document persisted schema on a 3-page synthetic PDF!
    pdf_path = tmp_root / "synth-3p.pdf"
    imgs = [Image.new("RGB", (600, 800), color=(240 - i * 10, 245, 250)) for i in range(3)]
    imgs[0].save(pdf_path, "PDF", resolution=72.0, save_all=True, append_images=imgs[1:])
    pdf_bytes = pdf_path.read_bytes()
    pdf_sha = digest(pdf_bytes)

    rgb_shas = []
    with pypdfium2.PdfDocument(pdf_bytes) as doc:
        for i in range(3):
            bm = doc[i].render(scale=protocol.RENDER_SCALE)
            pil_im = bm.to_pil().convert("RGB")
            rgb_shas.append(digest(pil_im.tobytes()))
            pil_im.close()
            bm.close()

    class _StubDocEngine:
        window = 3
        info = {"engine_mode": "carbon_surgical", "switch_bits": "111011"}

        def close(self):
            pass

        def read(self, pages, _folder):
            from formats import native_page

            out = []
            for p in pages:
                raw = f"<PAGE><BLOCK>text[60, 120, 300, 150]<FORK>Inspection R17-P{p['page']:02d}\n"
                out.append(
                    (
                        native_page(raw, p["points"]),
                        {"raw_output": raw, "token_ids": [128827, 128828, 128829], "token_classes": {"page": 1}, "token_count": 3},
                    )
                )
            return out, {"finish_reason": "stop", "window_token_ids": [128827] * len(pages)}

    seg_doc_dir = tmp_root / "segment-01-carbon_surgical"
    seg_doc_dir.mkdir(parents=True, exist_ok=True)
    publish(
        seg_doc_dir / "plan.json",
        {
            "mode": "carbon_surgical",
            "surgical_override": "remove_S1c",
            "requests": [
                {
                    "label": "id-ablation",
                    "mode": "carbon_surgical",
                    "warmup": False,
                    "pages": 3,
                    "pdf": str(pdf_path),
                    "sha256": pdf_sha,
                    "rgb_sha256": rgb_shas,
                }
            ],
        },
    )
    doc_res = execute_doc_segment(
        seg_doc_dir,
        engine_factory=lambda _m, _r, surgical_override=None: _StubDocEngine(),
        skip_env_and_lock_audit=True,
    )
    assert len(doc_res) == 1 and doc_res[0]["complete_pages"] == 3
    pred_doc = json.loads((seg_doc_dir / "01-id-ablation-carbon_surgical/prediction.json").read_bytes())
    assert len(pred_doc["pages"]) == 3
    assert all(sp["flagged"] is False for pg in pred_doc["pages"] for sp in pg["spans"])

    # Case E: Launcher negative controls (locked surgical, bad plan sha, dirty/mismatched git commit).
    _l_spec = importlib.util.spec_from_file_location("wp0017_launch", HERE / "launch.py")
    launch = importlib.util.module_from_spec(_l_spec)
    _l_spec.loader.exec_module(launch)

    neg_controls = {}
    try:
        resolve_mode("carbon_surgical")
    except ValueError as exc:
        neg_controls["locked_surgical_refused"] = str(exc)
    assert "locked_surgical_refused" in neg_controls

    bad_sha_plan = tmp_root / "bad-sha-plan.json"
    publish(bad_sha_plan, {"stage": "A1", "windows": []})
    # Dirty/mismatched --source commit SHA must fail verify_git_scopes immediately:
    try:
        launch.verify_git_scopes("0" * 40)
    except Exception as exc:
        neg_controls["bad_git_source_refused"] = type(exc).__name__
    assert "bad_git_source_refused" in neg_controls

    # Wrong --sha256 on launch.main (with verify_git_scopes bypassed to isolate the plan digest check):
    orig_vgs = launch.verify_git_scopes
    launch.verify_git_scopes = lambda *_a, **_kw: None
    try:
        try:
            launch.main(
                [
                    "--source",
                    "c7b2ee3663317e42a0e9bdd7ff9e17f16747d2cf",
                    "--plan",
                    str(bad_sha_plan),
                    "--sha256",
                    "f" * 64,
                    "--owner",
                    "carbon",
                    "--run",
                    "neg-bad-sha",
                    "--seconds",
                    "60",
                    "--lease",
                    "test-lease",
                    "--packet-root",
                    str(tmp_root / "pkt"),
                ]
            )
        except ValueError as exc:
            neg_controls["bad_plan_sha_refused"] = str(exc)
    finally:
        launch.verify_git_scopes = orig_vgs
    assert neg_controls.get("bad_plan_sha_refused") == "plan SHA-256 mismatch"

    # Case F: End-to-end execute_a1_segment CPU run over a 60-page PDF (exact windows 019 & 037) with AblationEngine!
    import io
    from contextlib import redirect_stdout
    import torch
    from tokenizers import Tokenizer
    from a1_trial import execute_a1_segment
    from ablation_engine import AblationEngine

    cfg_mod, dsv2_mod, uocr_mod = _load_real_model_python_modules()
    raw_tk = Tokenizer.from_file(str(MODEL / "tokenizer.json"))

    class _RealBpeMiniTok:
        eos_token_id = 1

        def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
            return list(raw_tk.encode(text, add_special_tokens=add_special_tokens).ids)

        def decode(self, ids: list[int], skip_special_tokens: bool = False) -> str:
            return raw_tk.decode([int(i) for i in ids], skip_special_tokens=skip_special_tokens)

        def convert_tokens_to_ids(self, toks: list[str]) -> list[int]:
            m = {"<PAGE>": 128827, "<BLOCK>": 128828, "<FORK>": 128829}
            return [m[t] for t in toks]

    bpe_tok = _RealBpeMiniTok()
    pdf60_path = tmp_root / "synth-60p.pdf"
    p60_imgs = [Image.new("RGB", (180, 240), color=(200 + (i % 40), 210, 220)) for i in range(60)]
    p60_imgs[0].save(pdf60_path, "PDF", resolution=72.0, save_all=True, append_images=p60_imgs[1:])
    p60_bytes = pdf60_path.read_bytes()
    p60_sha = digest(p60_bytes)
    p60_rgbs = []
    with pypdfium2.PdfDocument(p60_bytes) as d60:
        for i in range(60):
            bm = d60[i].render(scale=protocol.RENDER_SCALE)
            im = bm.to_pil().convert("RGB")
            p60_rgbs.append(digest(im.tobytes()))
            im.close()
            bm.close()

    # Build miniature valid 3-page token histories with real BPE token IDs for windows 019 and 037.
    def _encode_synth_win(id_str_p1: str, id_str_p3: str, coord_tok: int) -> list[int]:
        p1 = [128827, 128828, 10212, 30, 114086, 19, 86594, coord_tok, 63, 128829] + bpe_tok.encode(
            f"Inspection {id_str_p1}\n", add_special_tokens=False
        )
        p2 = [128827, 128828, 2067, 61, 2574, 14, 223, 9679, 14, 223, 15525, 14, 223, 10862, 63, 128829] + bpe_tok.encode(
            "Service log\n", add_special_tokens=False
        )
        p3 = [128827, 128828, 16771, 61, 18307, 14, 223, 4364, 14, 223, 27772, 14, 223, 5926, 63, 128829] + bpe_tok.encode(
            "Inspection register\n", add_special_tokens=False
        ) + [128828, 2067, 61, 2574, 14, 223, 9679, 14, 223, 15525, 14, 223, 10862, 63, 128829] + bpe_tok.encode(
            f"Inspection {id_str_p3}\n", add_special_tokens=False
        )
        return p1 + p2 + p3

    w019_short = _encode_synth_win("R00-100", "I08O1-388", 17979)
    w019_short_car = _encode_synth_win("R00-100", "108O1-388", 17979)
    w037_short = _encode_synth_win("8OI10-774", "R00-200", 17979)
    w037_short_car = _encode_synth_win("80I10-774", "R00-200", 16234)

    synth_a1_path = tmp_root / "synth-a1-inputs.json"
    synth_a1_obj = {
        "stage": "A1",
        "request": {
            "label": "a",
            "pdf": str(pdf60_path),
            "sha256": p60_sha,
            "pages": 60,
            "rgb_sha256": p60_rgbs,
        },
        "windows": [
            {
                "first_page": 19,
                "identifier_page": 21,
                "alternatives": ["I08O1-388", "108O1-388"],
                "by_mode": {
                    "native": {"token_ids": w019_short},
                    "carbon_bf16": {"token_ids": w019_short_car},
                },
            },
            {
                "first_page": 37,
                "identifier_page": 37,
                "alternatives": ["8OI10-774", "80I10-774"],
                "by_mode": {
                    "native": {"token_ids": w037_short},
                    "carbon_bf16": {"token_ids": w037_short_car},
                },
            },
        ],
    }
    synth_a1_sha = publish(synth_a1_path, synth_a1_obj)

    # Build a miniature vocab=129280 CPU model for the end-to-end AblationEngine + execute_a1_segment test.
    e2e_mdl = _build_mini_uocr_model(
        cfg_mod,
        dsv2_mod,
        uocr_mod,
        dtype=torch.float32,
        seed=7,
        vocab_size=129280,
        image_token_id=128815,
        page_token_id=128827,
    )

    orig_lm_head_fwd = e2e_mdl.lm_head.forward
    scripted_step_state = {"active": False, "seq": [], "pos": 0}

    def _scripted_lm_head(x):
        out = orig_lm_head_fwd(x)
        if scripted_step_state["active"]:
            idx = scripted_step_state["pos"]
            seq = scripted_step_state["seq"]
            tok_target = seq[idx] if idx < len(seq) else 1  # EOS == 1
            scripted_step_state["pos"] = idx + 1
            out = out.clone()
            out[..., tok_target] = out.max() + 50.0
        return out

    e2e_mdl.lm_head.forward = _scripted_lm_head

    class _MiniRuntime:
        def __init__(self, scripted_windows: list[list[int]]):
            self._scripted = list(scripted_windows)
            self._call_idx = 0

        def load_model(self, _model_dir):
            return bpe_tok, e2e_mdl, 5

        def run_infer_multi(self, model, tokenizer, images, call_kwargs):
            seq = self._scripted[self._call_idx]
            self._call_idx += 1
            in_ids, im_t, m_t, sp_t = _e2e_build_inputs(tokenizer, "", images)
            scripted_step_state["active"] = True
            scripted_step_state["seq"] = seq
            scripted_step_state["pos"] = 0
            try:
                res = model._uocr_generate(
                    tokenizer,
                    in_ids,
                    im_t,
                    m_t,
                    sp_t,
                    max_new_tokens=int(call_kwargs["max_new_tokens"]),
                    max_length=int(call_kwargs["max_length"]),
                    temperature=0.0,
                    page_count_guard=True,
                    max_page_tokens=int(call_kwargs["max_page_tokens"]),
                    ngram_size=int(call_kwargs["no_repeat_ngram_size"]),
                    ngram_window=int(call_kwargs["ngram_window"]),
                    ngram_whitelist=set(),
                    dash_topm=4,
                    stream=True,
                )
            finally:
                scripted_step_state["active"] = False
            return res["text"], len(res["token_ids"]), 12, {"cuda_max_allocated_bytes": 0, "cuda_max_reserved_bytes": 0}

    orig_build_e2e = uocr_mod._uocr_build_inputs

    def _e2e_build_inputs(_tok, _prompt, images, **_kw):
        in_ids, im_t, m_t, sp_t = _make_mini_inputs(torch.float32, n_pages=len(images))
        in_ids = in_ids.clone()
        in_ids[in_ids == 241] = 128827
        in_ids[in_ids == 240] = 128815
        return in_ids, im_t, m_t, sp_t

    uocr_mod._uocr_build_inputs = _e2e_build_inputs
    try:
        a1_seg_dir = tmp_root / "segment-01-all_off"
        a1_seg_dir.mkdir(parents=True, exist_ok=True)
        publish(
            a1_seg_dir / "segment-plan.json",
            {
                "stage": "A1",
                "mode": "all_off",
                "a1_manifest": str(synth_a1_path),
                "a1_manifest_sha256": synth_a1_sha,
                "warmups": [],
                "forced_native_probe_repeats": 2,
            },
        )
        rt_inst = _MiniRuntime([w019_short, w037_short])
        with redirect_stdout(io.StringIO()):
            e2e_seg_sum = execute_a1_segment(
                a1_seg_dir,
                engine_factory=lambda m, r, surgical_override=None: AblationEngine(
                    r, m, surgical_override=surgical_override, runtime=rt_inst, skip_lock_and_pin=True
                ),
                skip_env_and_lock_audit=True,
            )
        assert e2e_seg_sum["free_ids"] == ["I08O1-388", "8OI10-774"]
        assert all(w["endpoint_parity"]["exact_token_array_match"] for w in e2e_seg_sum["free_windows"])
        assert len(e2e_seg_sum["probe_windows"][0]["forced_native_D_passes_guarded_nats"]) == 2
        assert e2e_seg_sum["probe_windows"][1]["free_running_probe_executed_separately"] is True
        # Verify repeat determinism across pass 1 and pass 2 on real PyTorch forward passes:
        p019_passes = e2e_seg_sum["probe_windows"][0]["forced_native_D_passes_guarded_nats"]
        assert abs(p019_passes[0] - p019_passes[1]) == 0.0
    finally:
        uocr_mod._uocr_build_inputs = orig_build_e2e

    # Case G: Public A2 dev/id_ablation raster check (read-only public PDF/rasters only, zero custody access).
    pub_dev = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0017/design/public/dev/id_ablation")
    dev_fixture_verified = False
    if (pub_dev / "source.pdf").is_file() and (pub_dev / "rasters.json").is_file():
        r_meta = json.loads((pub_dev / "rasters.json").read_bytes())
        d_bytes = (pub_dev / "source.pdf").read_bytes()
        assert digest(d_bytes) == r_meta["pdf_sha256"]
        with pypdfium2.PdfDocument(d_bytes) as d_doc:
            assert len(d_doc) == 18
            bm0 = d_doc[0].render(scale=protocol.RENDER_SCALE)
            im0 = bm0.to_pil().convert("RGB")
            assert digest(im0.tobytes()) == r_meta["pages"][0]["rgb_sha256"]
            im0.close()
            bm0.close()
        dev_fixture_verified = True

    return {
        "a1_single_restoration_selected": res_single["recommended_surgical_mode"],
        "a1_pair_restoration_selected": res_pair_done["recommended_surgical_mode"],
        "a1_tampered_endpoint_blocked": True,
        "a1_e2e_60page_segment_and_dual_prefix_probe_verified": True,
        "a2_a3_trial_document_schema_verified": True,
        "locked_carbon_surgical_refused": True,
        "public_dev_id_ablation_raster_page1_verified": dev_fixture_verified,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--label", default="wp0017-cpu-01")
    p.add_argument("--source-candidate", help="Optional 40-hex commit SHA of the frozen source candidate")
    p.add_argument("--receipt-out", type=Path, help="Optional path to write JSON verification receipt")
    args = p.parse_args()

    with tempfile.TemporaryDirectory(prefix="wp0017-cpu-") as tmp:
        tmp_root = Path(tmp)
        phase1 = _run_import_and_utf8_hygiene_checks(tmp_root)
        tripwires = _install_cuda_tripwires()
        phase2 = _run_real_tokenizer_and_a1_locator_checks()
        phase3 = _run_six_switch_and_probe_checks()
        phase4 = _run_a1_analyzer_and_doc_harness_checks(tmp_root)
        assert len(tripwires) == 0, f"CUDA tripwire triggered: {tripwires}"

    import torch

    receipt = {
        "schema": "eledgercare.wp0017.cpu-preflight-receipt/1",
        "label": args.label,
        "source_candidate_sha": args.source_candidate,
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "torch_cuda_is_available": bool(torch.cuda.is_available()),
        "cuda_tripwire_hits": len(tripwires),
        "phase1_import_and_utf8_hygiene": phase1,
        "phase2_tokenizer_and_a1_locators": phase2,
        "phase3_six_switches_and_serial_probe": phase3,
        "phase4_analyzer_doc_schema_and_public_dev": phase4,
    }
    if args.receipt_out is not None:
        encoded = (json.dumps(receipt, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
        if args.receipt_out.exists():
            args.receipt_out.unlink()
        publish(args.receipt_out, encoded)
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
