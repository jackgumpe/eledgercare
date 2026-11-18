"""CPU-only preflight, unit verification on real Unlimited-OCR-2 Python modules, and plan builder.

Strictly forbids any CUDA query, device transfer, or GPU inference:
- Phase 1 runs with zero torch import (PDF/RGB digests, 26-control check_score.py, lock/AST/pin checks,
  plumbing/evaluator controls, and deterministic plan publication).
- Phase 2 imports torch on CPU with CUDA_VISIBLE_DEVICES='' and hard RuntimeError tripwires on
  torch.cuda.* + Tensor.cuda, testing PackedMoE, StaticDashCache + gather_sparse_decode_step,
  gpu_no_repeat_ngram, gpu_page_count_guard, and end-to-end multi-page burst-8 generation against
  the actual Unlimited_OCR_2_04809669 modeling modules on a miniature CPU config.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import importlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = ""

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EVAL = ROOT / "docs/evaluation/WP-0015"
ASTRA = ROOT / "docs/research/WP-0015/astra"
WP14 = ROOT / "docs/research/WP-0014/eld-latency-author"
WORKER = ROOT / "workers/local_ocr"
sys.path[:0] = [str(HERE), str(EVAL), str(ASTRA), str(WP14), str(WORKER)]

from cases import PYTHON
from engine import (
    LOCK_SHA,
    MANIFEST_SHA,
    MODEL,
    NOTICE,
    apply_carbon_patches,
    build_static_dash_cache_cls,
    gather_sparse_decode_step,
    gpu_no_repeat_ngram,
    gpu_page_count_guard,
    pack_dense_mlp_inplace,
    pack_moe_layer_inplace,
)
from evaluate import evaluate_run
from formats import digest, native_page, publish
from generation import test_generation
from launch import MAX_OWNER_RUNTIME_BYTES, MIN_FREE_DISK_BYTES, split_contiguous_segments
import importlib.util
from local_ocr import protocol, verify_runtime, worker
from local_ocr.env_guard import verify_storage_guards
from local_ocr.pdf_render import verify_renderer_identity

_astra_spec = importlib.util.spec_from_file_location("astra_trial", ASTRA / "trial.py")
_astra_trial = importlib.util.module_from_spec(_astra_spec)
_astra_spec.loader.exec_module(_astra_trial)
run_document = _astra_trial.document
render_inputs = _astra_trial.inputs


def build_plan_rows(eval_root: Path) -> dict[str, dict]:
    warm_pdf = (WP14 / "A.pdf").resolve()
    rows: dict[str, dict] = {
        "warm": dict(
            label="warm",
            pdf=str(warm_pdf),
            pages=1,
            warmup=True,
            sha256="25c14530845cad96329b528f860032c27a1259ed46de3ccb56f0e57730aa0858",
            rgb_sha256=["a189916661ad64469762ea65a693b49c0d59ca2508df2742cc5d92b60f7dd18d"],
        )
    }
    for family in ("short", "dense", "boundary"):
        source = (eval_root / "dev" / family / "source.pdf").resolve()
        manifest = json.loads(source.with_name("rasters.json").read_bytes())
        rows[family] = dict(
            label=family,
            pdf=str(source),
            pages=len(manifest["pages"]),
            warmup=False,
            sha256=manifest["pdf_sha256"],
            rgb_sha256=[p["rgb_sha256"] for p in manifest["pages"]],
        )
    return rows


def run_phase1_no_torch(eval_root: Path, out_dir: Path, plans_dir: Path) -> dict:
    rt = worker.RealTorchRuntime()
    lock, _ = verify_runtime.load_json_checked(protocol.DEPENDENCY_LOCK_PATH, LOCK_SHA, "lock")
    manifest, _ = verify_runtime.load_json_checked(protocol.MODEL_MANIFEST_PATH, MANIFEST_SHA, "manifest")
    deps = verify_runtime.verify_dependency_lock(
        lock,
        accepted_provenance_exceptions=["torchvision-local-sha256-TOFU"],
        installed_distributions=rt.installed_distributions(),
        is_importable_fn=rt.is_importable,
    )
    pdfium = rt.import_pdfium()
    renderer = verify_renderer_identity(pdfium, rt.dist_version, lock)
    verify_runtime.verify_model_sources_ast_safety(MODEL)

    # Check model/notice file existence and byte sizes without hashing 6.7 GB weights if avoidable?
    # Actually verify_model_sources_ast_safety already checked all .py files; check sizes of all 18 files + notice.
    for entry in manifest["files"]:
        fp = MODEL / entry["path"]
        assert fp.is_file() and fp.stat().st_size == entry["size"], f"model file mismatch: {fp}"
    for entry in manifest["notices"]:
        np = NOTICE / entry["path"]
        assert np.is_file() and np.stat().st_size == entry["size"], f"notice file mismatch: {np}"

    # Run custodian 26-control scorer self-check (README.md specifies `python -B check_score.py`)
    scorer_proc = subprocess.run(
        [str(PYTHON), "-B", str(EVAL / "check_score.py")],
        cwd=str(EVAL),
        capture_output=True,
        text=True,
        check=True,
    )
    scorer_check = json.loads(scorer_proc.stdout)
    assert len(scorer_check) == 26 and all(v == "pass" for v in scorer_check.values()), f"Unexpected check_score: {scorer_check}"

    rows = build_plan_rows(eval_root)
    rendered = {}
    for key, req in rows.items():
        pdf_bytes = Path(req["pdf"]).read_bytes()
        assert digest(pdf_bytes) == req["sha256"], f"PDF SHA mismatch for {key}"
        with pdfium.PdfDocument(pdf_bytes) as doc:
            got = render_inputs(doc, 0, len(doc), req)
            rendered[key] = [
                dict(page=r["page"], width=r["width"], height=r["height"], rgb_sha256=r["rgb_sha256"]) for r in got
            ]
            for r in got:
                r["image"].close()

    # Build deterministic release plans
    plans_dir.mkdir(parents=True, exist_ok=False)

    def write_plan(name: str, pairs: list[tuple[str, str]]) -> dict:
        reqs = [dict(**rows[k], mode=m) for k, m in pairs]
        p_path = plans_dir / f"{name}.json"
        sha = publish(p_path, dict(requests=reqs))
        segs = split_contiguous_segments(reqs)
        return dict(path=str(p_path), sha256=sha, request_count=len(reqs), segments=[m for m, _ in segs])

    dev_seq = ("warm", "short", "dense", "boundary")
    plans = {
        "smoke-dense": write_plan(
            "smoke-dense",
            [("warm", "native_profile"), ("dense", "native_profile"), ("warm", "carbon_bf16"), ("dense", "carbon_bf16")],
        ),
        "stage1-falsifier": write_plan(
            "stage1-falsifier",
            [(k, m) for m in ("native_profile", "carbon_moe", "carbon_gather", "carbon_bf16") for k in dev_seq],
        ),
        "ab-dev": write_plan("ab-dev", [(k, m) for m in ("native", "carbon_bf16") for k in dev_seq]),
        "ba-dev": write_plan("ba-dev", [(k, m) for m in ("carbon_bf16", "native") for k in dev_seq]),
    }

    # Plumbing + evaluator negative/positive controls (CPU test double, zero OCR)
    plumb_run = out_dir / "plumbing-sim-run"
    for seg_i, mode in enumerate(("native", "carbon_bf16"), 1):
        seg_d = plumb_run / f"segment-{seg_i:02d}-{mode}"
        seg_d.mkdir(parents=True)
        publish(seg_d / f"load-{mode}.json", dict(elapsed_s=0.01, engine_mode=mode))

        class DummyEngine:
            window = 3

            def read(self, pages, folder):
                out = []
                for p in pages:
                    raw = "<PAGE>"
                    out.append((native_page(raw, p["points"]), dict(raw_output=raw, token_ids=[128827], token_classes={"page": 1, "block_geometry": 0, "table_syntax": 0, "content": 0}, token_count=1)))
                return out, dict(
                    finish_reason="stop",
                    expected_pages=len(pages),
                    num_pages_out=len(pages),
                    native_infer_ms=10,
                    vram={"cuda_max_allocated_bytes": 0, "cuda_max_reserved_bytes": 0},
                    window_token_ids=[128827] * len(pages),
                    raw_output="<PAGE>" * len(pages),
                    test_double=True,
                )

        rec = run_document(dict(**rows["boundary"], mode=mode), DummyEngine(), seg_d / f"01-boundary-{mode}", renderer)
        assert rec["complete_pages"] == 4
    sim_eval = evaluate_run(plumb_run, eval_root / "dev", out_dir / "plumbing-eval.json")
    assert sim_eval["packets"]["boundary"]["carbon_bf16"]["exact_parity"]["exact_bf16_qualified"] is True

    # Negative controls: bad source SHA, duplicate publish, Generation file-lock controls
    try:
        run_document(dict(rows["short"], sha256="0" * 64, mode="carbon_bf16"), DummyEngine(), out_dir / "bad-sha", renderer)
        raise AssertionError("accepted wrong PDF SHA")
    except ValueError as exc:
        assert "frozen release" in str(exc)

    gen_controls = test_generation(out_dir / "generation-controls")
    storage_obs = verify_storage_guards(
        out_dir.parent.parent, min_free_bytes=MIN_FREE_DISK_BYTES, max_root_bytes=MAX_OWNER_RUNTIME_BYTES
    )

    assert "torch" not in sys.modules, "Phase 1 must not import torch"
    return dict(
        renderer=renderer,
        dependencies_verified=deps["verified_distribution_count"],
        scorer_controls_passed=len(scorer_check),
        rendered_fixtures=rendered,
        plans=plans,
        generation_negative_controls=gen_controls,
        storage_guards=storage_obs,
        phase1_torch_imported=False,
    )


def run_phase2_cpu_tensor_tests(out_dir: Path) -> dict:
    """Import actual Unlimited_OCR_2_04809669 Python modules on CPU with hard CUDA poison hooks."""
    import torch

    cuda_calls = []

    def forbid_cuda(name):
        def _fail(*_a, **_kw):
            cuda_calls.append(name)
            raise RuntimeError(f"Forbidden CUDA call during CPU preflight: {name}")

        return _fail

    for attr in ("is_available", "device_count", "current_device", "synchronize", "init", "mem_get_info"):
        if hasattr(torch.cuda, attr):
            setattr(torch.cuda, attr, forbid_cuda(f"torch.cuda.{attr}"))
    torch.Tensor.cuda = forbid_cuda("Tensor.cuda")

    # Stage read-only Python modules from MODEL into out_dir/cpu_uocr_pkg so relative imports work cleanly.
    pkg_root = out_dir / "cpu_uocr_pkg"
    pkg_dir = pkg_root / "uocr_cpu_test"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    for py_file in MODEL.glob("*.py"):
        shutil.copyfile(py_file, pkg_dir / py_file.name)
    sys.path.insert(0, str(pkg_root))

    uocr_mod = importlib.import_module("uocr_cpu_test.modeling_unlimitedocr")
    dsv2_mod = importlib.import_module("uocr_cpu_test.modeling_deepseekv2")

    # Miniature 2-layer config exercising Dense MLP (layer 0) + MoE (layer 1) + 2D page-RoPE DASH router.
    sp_cfg = {
        "training_stage": "dash",
        "use_sparse_attention": True,
        "sparse_attention_freq": [1, 1],
        "sparse_block_size": 4,
        "sparse_local_block": 2,
        "sparse_topk_blocks": 4,
        "dash_topk_blocks": 3,
        "dash_stage0": "head_cls",
        "dash_router": "entmax_topk_perlayer",
        "dash_scaling_factor": 64.0,
        "dash_scale_per_layer": [64.0, 64.0],
        "dash_prior_floor": 1e-4,
        "dash_floor_per_layer": [1e-4, 1e-4],
        "dash_sigma": 1.0,
        "dash_query_chunk": 64,
        "dash_image_only": True,
        "image_bucket_constraint": True,
        "dash_use_triton": False,
        "sparse_index_dim": 16,
        "sparse_num_index_heads": 1,
        "sparse_main_rope_mode": "page2d",
        "sparse_rope_mode": "page2d",
        "sparse_rope_page_mod": 2,
        "sparse_rope_page_pairs": 1,
        "sparse_rope_page_theta": 256.0,
        "sparse_rope_tok_theta": 10000.0,
        "sparse_main_rope_tok_freq_mode": "resample",
        "sparse_rope_tok_freq_mode": "resample",
        "page_token_id": 250,
        "image_token_id": 251,
        "per_page_image_tokens": 8,
    }
    cfg = uocr_mod.UnlimitedOCRConfig(
        vocab_size=256,
        hidden_size=64,
        intermediate_size=128,
        moe_intermediate_size=32,
        num_hidden_layers=2,
        num_attention_heads=4,
        num_key_value_heads=4,
        v_head_dim=16,
        n_routed_experts=8,
        num_experts_per_tok=2,
        n_shared_experts=1,
        first_k_dense_replace=1,
        moe_layer_freq=1,
        topk_method="greedy",
        scoring_func="softmax",
        routed_scaling_factor=1.0,
        norm_topk_prob=False,
        use_mla=False,
        q_lora_rank=None,
        kv_lora_rank=None,
        qk_nope_head_dim=0,
        qk_rope_head_dim=0,
        max_position_embeddings=512,
        bos_token_id=0,
        eos_token_id=1,
        pad_token_id=2,
        sparse_attention_config=sp_cfg,
    )
    cfg._attn_implementation = "eager"

    torch.manual_seed(20261118)
    # Skip 390M-param SAM/CLIP random CPU weight init in UnlimitedOCRModel.__init__ for unit testing.
    orig_sam_b, orig_clip_l = uocr_mod.build_sam_vit_b, uocr_mod.build_clip_l
    uocr_mod.build_sam_vit_b = lambda: None
    uocr_mod.build_clip_l = lambda: None
    try:
        base_lm = uocr_mod.UnlimitedOCRForCausalLM(cfg)
    finally:
        uocr_mod.build_sam_vit_b, uocr_mod.build_clip_l = orig_sam_b, orig_clip_l
    base_lm.model.projector = None
    for layer in base_lm.model.layers:
        # Give head_cls non-zero weights so Stage-0 softmax weighting is non-trivial!
        layer.self_attn.dash_router.head_cls.data.normal_(0.0, 0.25)
    base_lm.eval()

    # --- Test U1: PackedMoE + PackedDenseMLP equivalence (FP32 and BF16) ---
    with torch.no_grad():
        moe_ref = copy.deepcopy(base_lm.model.layers[1].mlp).eval()
        moe_pack = copy.deepcopy(moe_ref).eval()
        pack_moe_layer_inplace(moe_pack)
        x1 = torch.randn(1, 1, 64)
        x19 = torch.randn(1, 19, 64)
        diff_moe_fp32_decode = float((moe_ref(x1) - moe_pack(x1)).abs().max())
        diff_moe_fp32_prefill = float((moe_ref(x19) - moe_pack(x19)).abs().max())
        assert diff_moe_fp32_decode < 1e-5 and diff_moe_fp32_prefill < 1e-5

        moe_ref_bf16 = copy.deepcopy(base_lm.model.layers[1].mlp).to(torch.bfloat16).eval()
        moe_pack_bf16 = copy.deepcopy(moe_ref_bf16).eval()
        pack_moe_layer_inplace(moe_pack_bf16)
        xb1 = x1.to(torch.bfloat16)
        out_r_bf16, out_p_bf16 = moe_ref_bf16(xb1), moe_pack_bf16(xb1)
        cos_moe_bf16 = float(
            torch.nn.functional.cosine_similarity(out_r_bf16.float().view(1, -1), out_p_bf16.float().view(1, -1))
        )
        assert cos_moe_bf16 > 0.9999

        mlp0_ref = copy.deepcopy(base_lm.model.layers[0].mlp).eval()
        mlp0_pack = copy.deepcopy(mlp0_ref).eval()
        pack_dense_mlp_inplace(mlp0_pack)
        diff_mlp0_fp32 = float((mlp0_ref(x1) - mlp0_pack(x1)).abs().max())
        assert diff_mlp0_fp32 < 1e-5

    # --- Test U2: StaticDashCache + gather_sparse_decode_step over 40 multi-page decode steps ---
    from transformers.cache_utils import DynamicCache

    m_ref = copy.deepcopy(base_lm).eval()
    m_gat = copy.deepcopy(base_lm).eval()
    static_cls = build_static_dash_cache_cls()
    for layer in m_gat.model.layers:
        attn = layer.self_attn
        orig_f = attn.forward

        def _wrap(a_mod, o_fn):
            def _f(*a, **kw):
                hs = kw["hidden_states"] if "hidden_states" in kw else a[0]
                pkv = kw.get("past_key_value", a[3] if len(a) > 3 else kw.get("past_key_values"))
                pos = kw.get("position_ids", a[2] if len(a) > 2 else None)
                if hs.shape[1] == 1 and dsv2_mod._INFER["on"] and isinstance(pkv, static_cls):
                    return gather_sparse_decode_step(a_mod, hs, pos, pkv, dsv2_mod)
                return o_fn(*a, **kw)

            return _f

        attn.forward = _wrap(attn, orig_f)

    st_r = dsv2_mod.configure_dash_inference(m_ref.model, True, topm=4)
    st_g = dsv2_mod.configure_dash_inference(m_gat.model, True, topm=4)
    try:
        # 2-page prompt: [BOS, <PAGE>, 8x<image>, <PAGE>, 8x<image>, tok, tok] -> 21 tokens
        prompt_seq = [0, 250] + [251] * 8 + [250] + [251] * 8 + [10, 11]
        p_ids = torch.tensor([prompt_seq], dtype=torch.long)
        s0 = p_ids.shape[1]
        c_ref = DynamicCache()
        c_tmp = DynamicCache()
        out_r = m_ref.model(input_ids=p_ids, past_key_values=c_ref, use_cache=True, position_ids=torch.arange(s0)[None], return_dict=True)
        out_g0 = m_gat.model(input_ids=p_ids, past_key_values=c_tmp, use_cache=True, position_ids=torch.arange(s0)[None], return_dict=True)
        # Force small init_cap=24 so _grow() reallocation is also tested across 40 decode steps!
        c_gat = static_cls(out_g0.past_key_values, m_gat.model, init_cap=24, max_cap=128, act_clamp=dsv2_mod._ACT_CLAMP)

        max_step_diff = 0.0
        step_tokens = [250] + [15 + (i % 40) for i in range(18)] + [250] + [60 + (i % 30) for i in range(20)]
        for step_i, tok_val in enumerate(step_tokens):
            with torch.no_grad():
                t_in = torch.tensor([[tok_val]], dtype=torch.long)
                p_in = torch.tensor([[s0 + step_i]], dtype=torch.long)
                or_step = m_ref.model(input_ids=t_in, past_key_values=c_ref, use_cache=True, position_ids=p_in, return_dict=True)
                og_step = m_gat.model(input_ids=t_in, past_key_values=c_gat, use_cache=True, position_ids=p_in, return_dict=True)
                d = float((or_step.last_hidden_state - og_step.last_hidden_state).abs().max())
            max_step_diff = max(max_step_diff, d)
        assert max_step_diff < 1e-5, f"Gather decode diverged from reference: {max_step_diff}"
        assert c_gat.reallocations >= 1, "Expected StaticDashCache._grow() to be exercised"
    finally:
        dsv2_mod.configure_dash_inference(m_ref.model, False, state=st_r)
        dsv2_mod.configure_dash_inference(m_gat.model, False, state=st_g)

    # --- Test U3: Exact logit parity for gpu_no_repeat_ngram and gpu_page_count_guard ---
    seq_hist = [250, 5, 6, 7, 8, 9, 5, 6, 7, 12, 5, 6, 7, 8, 250, 5, 6, 7]
    gen_t = torch.tensor(seq_hist, dtype=torch.long)
    base_logits = torch.randn(256, dtype=torch.float32)
    ref_ng = uocr_mod._uocr_no_repeat_ngram(base_logits.clone(), seq_hist, 4, 12, {12})
    got_ng = gpu_no_repeat_ngram(base_logits.clone(), gen_t, len(seq_hist), 4, 12, torch.tensor([12], dtype=torch.long))
    assert torch.equal(ref_ng, got_ng), "gpu_no_repeat_ngram mismatch"

    ref_st = {"marker_cum": 0, "scanned": 0, "page_len": 0}
    gpu_st = {"marker_cum": torch.zeros((), dtype=torch.long), "page_len": torch.zeros((), dtype=torch.long)}
    stream_seq = [250, 10, 11, 12, 13, 250, 14, 250]  # includes blank 3rd page at end and max_page_tokens=4 cap!
    for idx_s in range(len(stream_seq) + 1):
        cur_gen = stream_seq[:idx_s]
        last_t = torch.tensor(stream_seq[idx_s - 1], dtype=torch.long) if idx_s > 0 else None
        lg = torch.randn(256, dtype=torch.float32)
        r_lg = uocr_mod._uocr_page_count_guard(lg.clone(), cur_gen, 2, 250, 1, 4, ref_st)
        g_lg = gpu_page_count_guard(lg.clone(), 2, 250, 1, 4, gpu_st, last_tok=last_t)
        assert torch.equal(r_lg, g_lg), f"gpu_page_count_guard mismatch at step {idx_s}"

    # --- Test U4: End-to-end _uocr_generate parity across carbon_moe, carbon_gather, carbon_bf16 (burst=8) ---
    class DummyTok:
        eos_token_id = 1

        def decode(self, ids, skip_special_tokens=False):
            return ",".join(map(str, ids))

    # Bias lm_head slightly so EOS (1) is emitted naturally mid-burst after both <PAGE> markers!
    e2e_base = copy.deepcopy(base_lm).eval()
    with torch.no_grad():
        e2e_base.lm_head.weight[250].mul_(1.8)
        e2e_base.lm_head.weight[1].mul_(1.6)

    prompt_1d = torch.tensor([0, 250] + [251] * 8 + [250] + [251] * 8 + [20, 21], dtype=torch.long)
    tok_dummy = DummyTok()
    ref_res = e2e_base._uocr_generate(
        tok_dummy,
        prompt_1d,
        None,
        None,
        None,
        max_new_tokens=28,
        max_length=256,
        temperature=0.0,
        page_count_guard=True,
        max_page_tokens=6,
        ngram_size=4,
        ngram_window=16,
        stream=False,
    )

    mode_parities = {}
    for m_name in ("carbon_moe", "carbon_gather", "carbon_bf16"):
        cand_m = copy.deepcopy(e2e_base).eval()
        apply_carbon_patches(cand_m, mode=m_name)
        cand_res = cand_m._uocr_generate(
            tok_dummy,
            prompt_1d,
            None,
            None,
            None,
            max_new_tokens=28,
            max_length=256,
            temperature=0.0,
            page_count_guard=True,
            max_page_tokens=6,
            ngram_size=4,
            ngram_window=16,
            stream=False,
        )
        assert cand_res["token_ids"] == ref_res["token_ids"], f"{m_name} token mismatch vs reference"
        assert cand_res["finish_reason"] == ref_res["finish_reason"]
        assert cand_res["num_pages_out"] == ref_res["num_pages_out"]
        mode_parities[m_name] = dict(
            exact_tokens=True,
            token_count=len(cand_res["token_ids"]),
            finish_reason=cand_res["finish_reason"],
            burst_extra_forwards=cand_res.get("burst_extra_forwards", 0),
        )

    assert not cuda_calls, f"CUDA tripwire triggered: {cuda_calls}"
    shutil.rmtree(pkg_root)
    return dict(
        cuda_tripwire_calls=len(cuda_calls),
        moe_fp32_decode_max_diff=diff_moe_fp32_decode,
        moe_fp32_prefill_max_diff=diff_moe_fp32_prefill,
        moe_bf16_cosine_sim=cos_moe_bf16,
        mlp0_fp32_max_diff=diff_mlp0_fp32,
        gather_40step_multipage_fp32_max_diff=max_step_diff,
        ngram_and_page_guard_bit_exact=True,
        end_to_end_mode_parities=mode_parities,
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--eval-root", type=Path, default=EVAL)
    p.add_argument("--label", required=True, help="Unique preflight label under external carbon root")
    p.add_argument("--summary-out", type=Path, help="Optional repository path for preflight receipt JSON")
    args = p.parse_args()

    carbon_ext = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0015/carbon")
    out_dir = (carbon_ext / "preflight" / args.label).resolve()
    plans_dir = (carbon_ext / "plans" / args.label).resolve()
    out_dir.mkdir(parents=True, exist_ok=False)

    phase1 = run_phase1_no_torch(args.eval_root.resolve(), out_dir, plans_dir)
    captured_log = io.StringIO()
    with contextlib.redirect_stdout(captured_log):
        phase2 = run_phase2_cpu_tensor_tests(out_dir)
    (out_dir / "phase2-model-log.txt").write_text(captured_log.getvalue(), encoding="utf-8")

    receipt = dict(
        label=args.label,
        external_preflight_dir=str(out_dir),
        external_plans_dir=str(plans_dir),
        phase1_no_torch=phase1,
        phase2_cpu_model_unit_tests=phase2,
    )
    publish(out_dir / "preflight-receipt.json", receipt)
    if args.summary_out:
        args.summary_out.parent.mkdir(parents=True, exist_ok=True)
        publish(args.summary_out.resolve(), receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
