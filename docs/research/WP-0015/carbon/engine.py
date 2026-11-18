"""WP-0015 Carbon BF16 Baidu challenger, isolated MoE/gather ablations, and stage profiler.

All modes run on the pinned read-only Baidu Unlimited-OCR-2 BF16 checkpoint
(0480966938291445591f69f08a13b041c073a96a), 3-page windows, 300-DPI PDFium RGB
rasters, greedy decoding, and the common native_page output projection.
No torch/CUDA module is imported at module import time.
"""
from __future__ import annotations

import functools
import gc
import inspect
import math
import os
import sys
import time
from pathlib import Path
from time import perf_counter_ns as clock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ASTRA = ROOT / "docs/research/WP-0015/astra"
WP14 = ROOT / "docs/research/WP-0014/eld-latency-author"
WORKER = ROOT / "workers/local_ocr"
sys.path[:0] = [str(HERE), str(ASTRA), str(WP14), str(WORKER)]

from formats import digest, native_page, token_classes
from generation import Generation
from local_ocr import observer, protocol, verify_runtime, worker
from native import GPU, LOCK_SHA, MANIFEST_SHA, MODEL, NOTICE, Native, StageMonitor

MODES = ("native", "native_profile", "carbon_moe", "carbon_gather", "carbon_bf16")
MODE_SPECS = {
    "carbon_moe": {
        "use_packed_moe": True,
        "use_gather_decode": False,
        "use_gpu_burst": False,
        "burst_stride": 1,
        "combination": ["packed_bf16_moe", "no_text_streamer"],
    },
    "carbon_gather": {
        "use_packed_moe": False,
        "use_gather_decode": True,
        "use_gpu_burst": False,
        "burst_stride": 1,
        "combination": ["static_kv_gather_sparse_decode", "no_text_streamer"],
    },
    "carbon_bf16": {
        "use_packed_moe": True,
        "use_gather_decode": True,
        "use_gpu_burst": True,
        "burst_stride": 8,
        "combination": [
            "packed_bf16_moe",
            "static_kv_gather_sparse_decode",
            "gpu_logit_guards_burst8",
            "no_text_streamer",
        ],
    },
}

SAFETY_ONLY_SPECS = tuple(s for s in observer.DEFAULT_TARGETS if s.tripwire)


def make_safety_monitor(model):
    module = sys.modules[type(model).__module__]
    targets = observer.resolve_monitoring_targets(
        sys.modules, prefix=module.__package__ + ".", specs=SAFETY_ONLY_SPECS
    )
    return observer.InferenceMonitor(targets)


def resolve_model_modules(model):
    uocr_mod = sys.modules[type(model).__module__]
    dsv2_mod = sys.modules[uocr_mod.configure_dash_inference.__module__]
    base_mod = dsv2_mod._base
    dash_mod = sys.modules[dsv2_mod.DashAttention.__module__]
    return uocr_mod, dsv2_mod, base_mod, dash_mod


def _extract_dynamic_kv(dyn_cache, layer_idx: int):
    if hasattr(dyn_cache, "key_cache"):
        return dyn_cache.key_cache[layer_idx], dyn_cache.value_cache[layer_idx]
    return dyn_cache.layers[layer_idx].keys, dyn_cache.layers[layer_idx].values


def _compute_headcls_kbar_blocks(idx_k_blk, valid_mask, head_cls, inv_sqrt_d: float, act_clamp: float):
    """Exact Stage-0 head_cls block summary matching modeling_deepseekv2._block_scores_infer.

    idx_k_blk: [B, n_b, bs, d] fp32; valid_mask: [B, n_b, bs] bool; head_cls: [d] parameter.
    Returns [B, n_b, d] fp32.
    """
    import torch

    hc = head_cls.to(idx_k_blk.dtype).view(1, 1, 1, -1)
    aw = ((idx_k_blk * hc).sum(-1) * inv_sqrt_d).clamp(-act_clamp, act_clamp)
    neg = torch.finfo(aw.dtype).min
    row_max = torch.where(valid_mask, aw, aw.new_full((), neg)).amax(dim=-1, keepdim=True)
    row_max = torch.where(valid_mask.any(dim=-1, keepdim=True), row_max, torch.zeros_like(row_max))
    e = torch.exp(aw - row_max) * valid_mask.to(aw.dtype)
    w = e / e.sum(dim=-1, keepdim=True).clamp_min(1e-6)
    return torch.nan_to_num((w.unsqueeze(-1) * idx_k_blk).sum(dim=2), nan=0.0, posinf=0.0, neginf=0.0)


def build_static_dash_cache_cls():
    import torch
    from transformers.cache_utils import Cache

    class StaticDashCache(Cache):
        """Pre-allocated BF16 KV + FP32 router index cache + incremental head_cls summary cache."""

        def __init__(self, dyn_cache, decoder, *, init_cap: int, max_cap: int, act_clamp: float):
            super().__init__()
            self.num_layers = len(decoder.layers)
            k0, _ = _extract_dynamic_kv(dyn_cache, 0)
            self.bsz, self.num_kv_heads, s0, self.head_dim = k0.shape
            self.dtype = k0.dtype
            self.device = k0.device
            self.max_cap = max(s0 + 1, int(max_cap))
            first_router = decoder.layers[0].self_attn.dash_router
            self.block_size = int(first_router.block_size)
            self.index_dim = int(first_router.index_dim)
            self.act_clamp = float(act_clamp)
            self.inv_sqrt_idx_d = 1.0 / math.sqrt(self.index_dim)
            self._blk_arange = torch.arange(self.block_size, device=self.device)
            self._local_arange = torch.arange(int(first_router.local_window), device=self.device)

            cap_tok = min(self.max_cap, max(int(init_cap), s0 + 1))
            cap_blk = -(-cap_tok // self.block_size)
            cap_tok = cap_blk * self.block_size
            self.cap_tok = cap_tok
            self.cap_blk = cap_blk
            self.seq_lens = [s0] * self.num_layers
            self.reallocations = 0

            self.k_buf = []
            self.v_buf = []
            self._dash_idx_k = {}
            self.k_bar_buf = []
            for li in range(self.num_layers):
                kp, vp = _extract_dynamic_kv(dyn_cache, li)
                kb = torch.empty((self.bsz, self.num_kv_heads, cap_tok, self.head_dim), dtype=self.dtype, device=self.device)
                vb = torch.empty((self.bsz, self.num_kv_heads, cap_tok, self.head_dim), dtype=self.dtype, device=self.device)
                kb[:, :, :s0, :].copy_(kp)
                vb[:, :, :s0, :].copy_(vp)
                self.k_buf.append(kb)
                self.v_buf.append(vb)

                ik_src = dyn_cache._dash_idx_k[li]
                ik_buf = torch.zeros((self.bsz, cap_tok, self.index_dim), dtype=torch.float32, device=self.device)
                ik_buf[:, :s0, :].copy_(ik_src)
                self._dash_idx_k[li] = ik_buf

                router = decoder.layers[li].self_attn.dash_router
                nblk0 = -(-s0 // self.block_size)
                kbar = torch.zeros((self.bsz, cap_blk, self.index_dim), dtype=torch.float32, device=self.device)
                if nblk0 > 0 and router.stage0 == "head_cls":
                    sp0 = nblk0 * self.block_size
                    kk0 = ik_buf[:, :sp0, :].view(self.bsz, nblk0, self.block_size, self.index_dim)
                    pos0 = torch.arange(sp0, device=self.device).view(1, nblk0, self.block_size)
                    vmask0 = (pos0 < s0).expand(self.bsz, nblk0, self.block_size)
                    kbar[:, :nblk0, :] = _compute_headcls_kbar_blocks(
                        kk0, vmask0, router.head_cls, self.inv_sqrt_idx_d, self.act_clamp
                    )
                self.k_bar_buf.append(kbar)

            if hasattr(dyn_cache, "_page_rope_state"):
                self._page_rope_state = {
                    li: {k: (v.clone() if hasattr(v, "clone") else v) for k, v in st.items()}
                    for li, st in dyn_cache._page_rope_state.items()
                }
            if hasattr(dyn_cache, "_uocr_pg"):
                self._uocr_pg = {
                    k: (v.clone() if hasattr(v, "clone") else v) for k, v in dyn_cache._uocr_pg.items()
                }

        def get_seq_length(self, layer_idx: int | None = 0) -> int:
            return self.seq_lens[0 if layer_idx is None else layer_idx]

        def get_max_length(self):
            return None

        def _grow(self, needed_tok: int):
            import torch

            new_tok = max(needed_tok, self.cap_tok * 2)
            new_blk = -(-new_tok // self.block_size)
            new_tok = new_blk * self.block_size
            for li in range(self.num_layers):
                s = self.seq_lens[li]
                nblk = -(-s // self.block_size)
                kb = torch.empty((self.bsz, self.num_kv_heads, new_tok, self.head_dim), dtype=self.dtype, device=self.device)
                vb = torch.empty((self.bsz, self.num_kv_heads, new_tok, self.head_dim), dtype=self.dtype, device=self.device)
                kb[:, :, :s, :].copy_(self.k_buf[li][:, :, :s, :])
                vb[:, :, :s, :].copy_(self.v_buf[li][:, :, :s, :])
                self.k_buf[li] = kb
                self.v_buf[li] = vb

                ik = torch.zeros((self.bsz, new_tok, self.index_dim), dtype=torch.float32, device=self.device)
                ik[:, :s, :].copy_(self._dash_idx_k[li][:, :s, :])
                self._dash_idx_k[li] = ik

                kbar = torch.zeros((self.bsz, new_blk, self.index_dim), dtype=torch.float32, device=self.device)
                kbar[:, :nblk, :].copy_(self.k_bar_buf[li][:, :nblk, :])
                self.k_bar_buf[li] = kbar
            self.cap_tok = new_tok
            self.cap_blk = new_blk
            self.reallocations += 1

        def append_decode(self, layer_idx: int, k_new, v_new, idx_k_new, router):
            s_old = self.seq_lens[layer_idx]
            s_new = s_old + 1
            if s_new > self.cap_tok:
                self._grow(s_new)
            self.k_buf[layer_idx][:, :, s_old:s_new, :].copy_(k_new)
            self.v_buf[layer_idx][:, :, s_old:s_new, :].copy_(v_new)
            ik_buf = self._dash_idx_k[layer_idx]
            ik_buf[:, s_old:s_new, :].copy_(idx_k_new)
            self.seq_lens[layer_idx] = s_new

            if router.stage0 == "head_cls":
                blk = s_old // self.block_size
                valid_len = s_new - blk * self.block_size
                b0 = blk * self.block_size
                kk_b = ik_buf[:, b0 : b0 + self.block_size, :].unsqueeze(1)
                vmask_b = (self._blk_arange < valid_len).view(1, 1, self.block_size).expand(self.bsz, 1, self.block_size)
                self.k_bar_buf[layer_idx][:, blk : blk + 1, :] = _compute_headcls_kbar_blocks(
                    kk_b, vmask_b, router.head_cls, self.inv_sqrt_idx_d, self.act_clamp
                )
            return s_new

    return StaticDashCache


def gather_sparse_decode_step(attn, hidden_states, position_ids, static_cache, dsv2_mod):
    """Exact O(1) gather-only sparse decode step for a single token (q_len == 1)."""
    import torch
    import torch.nn.functional as F

    idx = attn.indexer
    router = attn.dash_router
    nh = attn.config.num_attention_heads
    nkv = attn.config.num_key_value_heads
    hd = attn.head_dim
    bsz, q_len, _ = hidden_states.size()
    if position_ids is None:
        past = static_cache.get_seq_length(attn.layer_idx)
        position_ids = torch.arange(past, past + q_len, device=hidden_states.device)[None].expand(bsz, -1)

    q = attn.q_proj(hidden_states).view(bsz, q_len, nh, hd).transpose(1, 2)
    k = attn.k_proj(hidden_states).view(bsz, q_len, nkv, hd).transpose(1, 2)
    v = attn.v_proj(hidden_states).view(bsz, q_len, nkv, hd).transpose(1, 2)

    coords = None
    if attn.main_rope_mode == "page2d" and attn.rotary_emb_2d_main is not None:
        coords = attn._main_rope_coords(q_len, static_cache)
    if coords is not None:
        cos, sin = attn.rotary_emb_2d_main(v, coords[0], coords[1])
    else:
        cos, sin = attn.rotary_emb(v, position_ids)
    q, k = dsv2_mod._llama_apply_rotary_pos_emb(q, k, cos, sin)
    idx_pe = dsv2_mod._dash_indexer_rope(
        attn, idx, router, v, position_ids, coords if idx.rope_mode == "page2d" else None, (cos, sin)
    )

    p = router._infer_params
    bs = router.block_size
    lw = router.local_window
    with torch.autocast(device_type=hidden_states.device.type, enabled=False):
        idx_q, idx_k_new = dsv2_mod._router_qk(router, hidden_states, idx_pe)
        s_total = static_cache.append_decode(attn.layer_idx, k, v, idx_k_new, router)
        nblk = (s_total + bs - 1) // bs

        if router.stage0 == "head_cls":
            k_bar = static_cache.k_bar_buf[attn.layer_idx][:, :nblk, :]
            z = torch.matmul(idx_q, k_bar.transpose(-1, -2)) * static_cache.inv_sqrt_idx_d
            z = z.clamp(-dsv2_mod._ACT_CLAMP, dsv2_mod._ACT_CLAMP)
            qblk = position_ids // bs
            blk_ids = torch.arange(nblk, device=hidden_states.device)
            keep_blk = blk_ids[None, None, :] <= (qblk[:, :, None] - router.local_blocks)
            sc = z.masked_fill(~keep_blk, dsv2_mod._SCORE_NEG)
        else:
            ik_slice = static_cache._dash_idx_k[attn.layer_idx][:, :s_total, :]
            sc = dsv2_mod._block_scores_infer(router, idx_q, ik_slice, position_ids, nblk)

        allow = getattr(attn, "_dash_dec_allow", None)
        cand = None
        if allow is not None and router.image_only:
            if allow.shape[-1] < nblk:
                allow = F.pad(allow, (0, nblk - allow.shape[-1]), value=False)
            cand = allow[:, None, :nblk].expand(bsz, q_len, nblk)
        topi, bias, valid = dsv2_mod._infer_route_select(sc, cand, p)

        # Disjoint gather of routed remote blocks (strictly <= qp - local_window) U local_window.
        # bsz == 1 and q_len == 1 in single-document research/product inference; fall back to
        # reference _decode_attend if ever called with bsz > 1.
        k_full = static_cache.k_buf[attn.layer_idx][:, :, :s_total, :]
        v_full = static_cache.v_buf[attn.layer_idx][:, :, :s_total, :]
        if bsz == 1 and q_len == 1:
            qp = position_ids[0, 0]
            k_sel_cnt = topi.shape[-1]
            rem_pos = (topi[0, 0, :, None] * bs + static_cache._blk_arange[None, :]).reshape(-1)
            rem_bias = bias[0, 0, :, None].expand(k_sel_cnt, bs).reshape(-1)
            rem_valid = valid[0, 0, :, None].expand(k_sel_cnt, bs).reshape(-1)
            rem_keep = rem_valid & (rem_pos >= 0) & (rem_pos < s_total) & (rem_pos <= (qp - lw))

            loc_pos_raw = (qp - lw + 1) + static_cache._local_arange
            loc_keep = (loc_pos_raw >= 0) & (loc_pos_raw <= qp) & (loc_pos_raw < s_total)

            gather_idx = torch.cat([rem_pos.clamp(0, s_total - 1), loc_pos_raw.clamp(0, s_total - 1)], dim=0)
            neg_inf = torch.full((), float("-inf"), dtype=torch.float32, device=hidden_states.device)
            zero_f = torch.zeros((), dtype=torch.float32, device=hidden_states.device)
            rem_m = torch.where(rem_keep, rem_bias.float(), neg_inf)
            loc_m = torch.where(loc_keep, zero_f.expand_as(loc_pos_raw), neg_inf)
            attn_bias = torch.cat([rem_m, loc_m], dim=0)[None, None, None, :]

            kk = k_full.index_select(2, gather_idx).float()
            vv = v_full.index_select(2, gather_idx).float()
            if kk.shape[1] != nh:
                kk = dsv2_mod._llama_repeat_kv(kk, nh // kk.shape[1])
                vv = dsv2_mod._llama_repeat_kv(vv, nh // vv.shape[1])
            scores = torch.matmul(q.float(), kk.transpose(-1, -2)) * router._scale + attn_bias
            out = torch.matmul(torch.softmax(scores, dim=-1), vv)
        else:
            out = dsv2_mod._decode_attend(
                q, k_full, v_full, topi, bias, valid, position_ids, bs, lw, router._scale
            )

    out = out.to(hidden_states.dtype).transpose(1, 2).contiguous().reshape(bsz, q_len, -1)
    return attn.o_proj(out), None, static_cache, None


def pack_dense_mlp_inplace(mlp):
    """Fuse gate_proj + up_proj on Layer 0's dense DeepseekV2MLP with zero extra weight VRAM."""
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    inter = mlp.gate_proj.out_features
    w_gu = torch.cat([mlp.gate_proj.weight.data, mlp.up_proj.weight.data], dim=0).contiguous()
    w_dn = mlp.down_proj.weight.data
    act_fn = mlp.act_fn
    mlp.gate_proj = None
    mlp.up_proj = None
    mlp.w_gate_up = nn.Parameter(w_gu, requires_grad=False)

    def packed_mlp_forward(x):
        gu = F.linear(x, mlp.w_gate_up)
        gate, up = gu.split(inter, dim=-1)
        return F.linear(act_fn(gate) * up, w_dn)

    mlp.forward = packed_mlp_forward


def pack_moe_layer_inplace(moe):
    """Replace 64-expert Python loop + .cpu().numpy() sync with contiguous BF16 GPU tensors."""
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    n_routed = len(moe.experts)
    e0 = moe.experts[0]
    hidden = e0.gate_proj.in_features
    inter = e0.gate_proj.out_features
    dtype = e0.gate_proj.weight.dtype
    device = e0.gate_proj.weight.device
    act_fn = e0.act_fn

    w_gu_nk = torch.empty((n_routed, 2 * inter, hidden), dtype=dtype, device=device)
    w_dn_nk = torch.empty((n_routed, hidden, inter), dtype=dtype, device=device)
    for i, exp in enumerate(moe.experts):
        w_gu_nk[i, :inter, :].copy_(exp.gate_proj.weight.data)
        w_gu_nk[i, inter:, :].copy_(exp.up_proj.weight.data)
        w_dn_nk[i].copy_(exp.down_proj.weight.data)

    sh_gu = sh_dn = None
    sh_inter = 0
    if moe.config.n_shared_experts is not None and moe.shared_experts is not None:
        sh = moe.shared_experts
        sh_inter = sh.gate_proj.out_features
        sh_gu = nn.Parameter(
            torch.cat([sh.gate_proj.weight.data, sh.up_proj.weight.data], dim=0).contiguous(),
            requires_grad=False,
        )
        sh_dn = sh.down_proj.weight
        moe.shared_experts = None

    moe.experts = nn.ModuleList()
    moe.w_gate_up_nk = nn.Parameter(w_gu_nk, requires_grad=False)
    moe.w_down_nk = nn.Parameter(w_dn_nk, requires_grad=False)
    if sh_gu is not None:
        moe.sh_gate_up = sh_gu
    moe.prefill_grouped_mm_calls = 0
    moe.prefill_fallback_calls = 0
    moe._grouped_mm_supported = hasattr(torch, "_grouped_mm")

    @torch.no_grad()
    def packed_moe_forward(hidden_states):
        orig_shape = hidden_states.shape
        topk_idx, topk_weight, _ = moe.gate(hidden_states)
        x = hidden_states.view(-1, hidden)
        n_tok = x.shape[0]
        k_top = topk_idx.shape[1]

        if n_tok == 1:
            idx = topk_idx.view(k_top)
            w_gu = moe.w_gate_up_nk.index_select(0, idx)
            gu = torch.bmm(x.expand(k_top, hidden).unsqueeze(1), w_gu.transpose(1, 2))
            gate, up = gu.split(inter, dim=-1)
            act = act_fn(gate) * up
            w_dn = moe.w_down_nk.index_select(0, idx)
            exp_out = torch.bmm(act, w_dn.transpose(1, 2)).squeeze(1)
            routed = (
                exp_out.to(topk_weight.dtype)
                .mul_(topk_weight.view(k_top, 1))
                .sum(dim=0, keepdim=True)
                .to(x.dtype)
            )
        else:
            flat_idx = topk_idx.view(-1)
            order = flat_idx.argsort()
            sorted_x = x.index_select(0, order // k_top)
            counts = torch.bincount(flat_idx, minlength=n_routed)
            used_grouped = False
            if moe._grouped_mm_supported and x.is_cuda and x.dtype == torch.bfloat16:
                try:
                    offs = counts.cumsum(dim=0).to(torch.int32)
                    gu = torch._grouped_mm(sorted_x, moe.w_gate_up_nk.transpose(1, 2), offs=offs)
                    gate, up = gu.split(inter, dim=-1)
                    act = act_fn(gate) * up
                    sorted_out = torch._grouped_mm(act, moe.w_down_nk.transpose(1, 2), offs=offs)
                    used_grouped = True
                    moe.prefill_grouped_mm_calls += 1
                except (RuntimeError, NotImplementedError):
                    moe._grouped_mm_supported = False
            if not used_grouped:
                moe.prefill_fallback_calls += 1
                counts_cpu = counts.cpu().tolist()
                pieces = []
                cur = 0
                for ei, cnt in enumerate(counts_cpu):
                    if cnt == 0:
                        continue
                    seg = sorted_x[cur : cur + cnt]
                    gu = F.linear(seg, moe.w_gate_up_nk[ei])
                    gate, up = gu.split(inter, dim=-1)
                    pieces.append(F.linear(act_fn(gate) * up, moe.w_down_nk[ei]))
                    cur += cnt
                sorted_out = torch.cat(pieces, dim=0) if pieces else sorted_x.new_empty((0, hidden))
            unsorted = torch.empty_like(sorted_out)
            unsorted[order] = sorted_out
            routed = (
                unsorted.view(n_tok, k_top, hidden)
                .to(topk_weight.dtype)
                .mul_(topk_weight.unsqueeze(-1))
                .sum(dim=1)
                .to(x.dtype)
            )

        if sh_gu is not None:
            s_gu = F.linear(x, moe.sh_gate_up)
            s_gate, s_up = s_gu.split(sh_inter, dim=-1)
            routed = routed + F.linear(act_fn(s_gate) * s_up, sh_dn)
        return routed.view(*orig_shape)

    moe.forward = packed_moe_forward


def gpu_no_repeat_ngram(logits, gen_buf, cur_len: int, ngram_size: int, window_size: int, whitelist_gpu=None):
    """Duplicate-safe, sync-free GPU 1D n-gram repeat blocker matching _uocr_no_repeat_ngram."""
    import torch
    import torch.nn.functional as F

    if ngram_size <= 0 or cur_len < ngram_size:
        return logits
    win = min(cur_len, window_size)
    if win < ngram_size:
        return logits
    tail = gen_buf[cur_len - win : cur_len]
    windows = tail.unfold(0, ngram_size, 1)
    if ngram_size > 1:
        prefix = gen_buf[cur_len - (ngram_size - 1) : cur_len]
        matches = (windows[:, :-1] == prefix).all(dim=1)
    else:
        matches = torch.ones(windows.shape[0], dtype=torch.bool, device=logits.device)
    cand = windows[:, -1]
    if whitelist_gpu is not None and whitelist_gpu.numel() > 0:
        matches = matches & ~torch.isin(cand, whitelist_gpu)
    vocab = logits.shape[0]
    ext = F.pad(logits, (0, 1), value=0.0)
    safe_idx = torch.where(matches, cand, torch.full_like(cand, vocab))
    ext.scatter_(0, safe_idx, float("-inf"))
    return ext[:-1]


def gpu_page_count_guard(logits, expected_pages: int, page_id: int, eos_id: int, max_page_tokens: int, state: dict, last_tok=None):
    """Sync-free GPU PageCountGuard matching modeling_unlimitedocr._uocr_page_count_guard."""
    import torch

    if expected_pages <= 0:
        return logits
    if last_tok is not None:
        is_pg = last_tok == page_id
        state["marker_cum"] = state["marker_cum"] + is_pg.long()
        state["page_len"] = torch.where(is_pg, torch.zeros_like(state["page_len"]), state["page_len"] + 1)

    mc = state["marker_cum"]
    pl = state["page_len"]
    eos_val = logits[eos_id].clone()
    pg_val = logits[page_id].clone()

    only_eos = torch.full_like(logits, float("-inf"))
    only_eos[eos_id] = eos_val
    only_pg = torch.full_like(logits, float("-inf"))
    only_pg[page_id] = pg_val
    no_eos = logits.clone()
    no_eos[eos_id] = float("-inf")

    cond1 = mc > expected_pages
    cond2 = (~cond1) & (pl >= max_page_tokens if max_page_tokens > 0 else torch.zeros_like(cond1))
    cond3 = (~cond1) & (~cond2) & (mc < expected_pages)
    forced_cap = torch.where(mc < expected_pages, only_pg, only_eos)
    return torch.where(cond1, only_eos, torch.where(cond2, forced_cap, torch.where(cond3, no_eos, logits)))


def carbon_generate(
    model_lm,
    tokenizer,
    input_ids,
    imgs,
    seq_mask,
    spatial,
    *,
    uocr_mod,
    dsv2_mod,
    static_cache_cls,
    use_gather_decode: bool,
    use_gpu_burst: bool,
    burst_stride: int,
    max_new_tokens: int,
    max_length: int,
    temperature: float,
    page_count_guard: bool,
    max_page_tokens: int,
    ngram_size: int,
    ngram_window: int,
    ngram_whitelist,
    dash_topm: int,
):
    """Drop-in replacement for UnlimitedOCRForCausalLM._uocr_generate without TextStreamer."""
    import torch
    from transformers.cache_utils import DynamicCache

    if temperature and temperature > 0:
        raise ValueError("CarbonEngine supports deterministic greedy decoding (temperature == 0.0) only")

    device = model_lm.lm_head.weight.device
    ids = input_ids.unsqueeze(0).to(device)
    prompt_ids = input_ids.tolist()
    sp_cfg = getattr(model_lm.config, "sparse_attention_config", None)
    page_id = int((sp_cfg or {}).get("page_token_id", 128827)) if isinstance(sp_cfg, dict) else 128827
    eos_id = int(tokenizer.eos_token_id)
    expected_pages = prompt_ids.count(page_id) if page_count_guard else 0

    kw = {}
    if imgs is not None:
        kw = dict(
            images=[(imgs[0].to(device), imgs[1].to(device), spatial)],
            images_seq_mask=seq_mask.unsqueeze(0).to(device),
            images_spatial_crop=spatial,
        )

    cfg = model_lm.config
    saved_cfg = (getattr(cfg, "_ring_window", None), getattr(cfg, "sliding_window", None))
    cfg._ring_window = None
    cfg.sliding_window = None
    dash_state = dsv2_mod.configure_dash_inference(model_lm.model, True, topm=dash_topm)

    t0 = time.perf_counter()
    marks = {"generate_start": clock()}
    gen: list[int] = []
    finish = "length"
    executed_forwards = 0
    burst_extra_forwards = 0
    cache_reallocs = 0

    try:
        dyn_cache = DynamicCache()
        s_prefill = ids.shape[1]
        max_tokens_eff = min(int(max_new_tokens), max(0, int(max_length) - s_prefill))
        out = model_lm.model(
            input_ids=ids,
            past_key_values=dyn_cache,
            use_cache=True,
            position_ids=torch.arange(s_prefill, device=device)[None],
            return_dict=True,
            **kw,
        )
        executed_forwards += 1
        h = out.last_hidden_state[:, -1:]
        cache = (
            static_cache_cls(
                out.past_key_values,
                model_lm.model,
                init_cap=max(4096, s_prefill + 2048),
                max_cap=s_prefill + max_tokens_eff + 32,
                act_clamp=dsv2_mod._ACT_CLAMP,
            )
            if use_gather_decode
            else out.past_key_values
        )

        if max_tokens_eff > 0:
            if not use_gpu_burst:
                guard_st = {"marker_cum": 0, "scanned": 0, "page_len": 0}
                wl_set = set(ngram_whitelist or [])
                for step in range(max_tokens_eff):
                    logits = model_lm.lm_head(h).float()[0, -1]
                    if ngram_size > 0:
                        logits = uocr_mod._uocr_no_repeat_ngram(logits, gen, ngram_size, ngram_window, wl_set)
                    if expected_pages > 0:
                        logits = uocr_mod._uocr_page_count_guard(
                            logits, gen, expected_pages, page_id, eos_id, max_page_tokens, guard_st
                        )
                    nxt = int(torch.argmax(logits))
                    if step == 0:
                        marks["first_token"] = clock()
                    if nxt == eos_id:
                        finish = "stop"
                        break
                    gen.append(nxt)
                    marks["last_token"] = clock()
                    if step + 1 >= max_tokens_eff:
                        break
                    pos = s_prefill + step
                    out = model_lm.model(
                        input_ids=torch.tensor([[nxt]], dtype=torch.long, device=device),
                        past_key_values=cache,
                        use_cache=True,
                        position_ids=torch.tensor([[pos]], dtype=torch.long, device=device),
                        return_dict=True,
                    )
                    executed_forwards += 1
                    cache = out.past_key_values
                    h = out.last_hidden_state
            else:
                gen_buf = torch.empty(max_tokens_eff, dtype=torch.long, device=device)
                pos_all = torch.arange(s_prefill, s_prefill + max_tokens_eff, dtype=torch.long, device=device).view(-1, 1, 1)
                wl_list = sorted(set(ngram_whitelist or []))
                wl_gpu = torch.tensor(wl_list, dtype=torch.long, device=device) if wl_list else None
                gpu_guard = {
                    "marker_cum": torch.zeros((), dtype=torch.long, device=device),
                    "page_len": torch.zeros((), dtype=torch.long, device=device),
                }

                # Step 0: synchronize first token immediately for exact first_token mark.
                logits0 = model_lm.lm_head(h).float()[0, -1]
                if expected_pages > 0:
                    logits0 = gpu_page_count_guard(
                        logits0, expected_pages, page_id, eos_id, max_page_tokens, gpu_guard, last_tok=None
                    )
                tok0 = torch.argmax(logits0)
                gen_buf[0] = tok0
                nxt0 = int(tok0.item())
                marks["first_token"] = clock()
                if nxt0 == eos_id:
                    finish = "stop"
                else:
                    gen.append(nxt0)
                    marks["last_token"] = marks["first_token"]
                    cur = 1
                    if cur < max_tokens_eff:
                        out = model_lm.model(
                            input_ids=gen_buf[0:1].view(1, 1),
                            past_key_values=cache,
                            use_cache=True,
                            position_ids=pos_all[0],
                            return_dict=True,
                        )
                        executed_forwards += 1
                        cache = out.past_key_values
                        h = out.last_hidden_state

                    stride = max(1, int(burst_stride))
                    while cur < max_tokens_eff:
                        b = min(stride, max_tokens_eff - cur)
                        for k in range(b):
                            s_idx = cur + k
                            logits = model_lm.lm_head(h).float()[0, -1]
                            if ngram_size > 0:
                                logits = gpu_no_repeat_ngram(logits, gen_buf, s_idx, ngram_size, ngram_window, wl_gpu)
                            if expected_pages > 0:
                                logits = gpu_page_count_guard(
                                    logits,
                                    expected_pages,
                                    page_id,
                                    eos_id,
                                    max_page_tokens,
                                    gpu_guard,
                                    last_tok=gen_buf[s_idx - 1],
                                )
                            gen_buf[s_idx] = torch.argmax(logits)
                            if s_idx + 1 < max_tokens_eff:
                                out = model_lm.model(
                                    input_ids=gen_buf[s_idx : s_idx + 1].view(1, 1),
                                    past_key_values=cache,
                                    use_cache=True,
                                    position_ids=pos_all[s_idx],
                                    return_dict=True,
                                )
                                executed_forwards += 1
                                cache = out.past_key_values
                                h = out.last_hidden_state
                        chunk = gen_buf[cur : cur + b].tolist()
                        marks["last_token"] = clock()
                        if eos_id in chunk:
                            cut = chunk.index(eos_id)
                            gen.extend(chunk[:cut])
                            # Steps after (cur + cut) inside this burst were speculative post-EOS steps.
                            last_needed_fwd_step = cur + cut - 1
                            last_ran_fwd_step = min(cur + b - 1, max_tokens_eff - 2)
                            burst_extra_forwards = max(0, last_ran_fwd_step - last_needed_fwd_step)
                            finish = "stop"
                            break
                        gen.extend(chunk)
                        cur += b
        if use_gather_decode and hasattr(cache, "reallocations"):
            cache_reallocs = int(cache.reallocations)
    finally:
        dsv2_mod.configure_dash_inference(model_lm.model, False, state=dash_state)
        cfg._ring_window, cfg.sliding_window = saved_cfg
        marks["generate_end"] = clock()

    t_end = time.perf_counter()
    prefill_s = ((marks["first_token"] - marks["generate_start"]) / 1e9) if "first_token" in marks else None
    text = tokenizer.decode(gen, skip_special_tokens=False)
    return {
        "text": text,
        "token_ids": gen,
        "prompt_token_ids": prompt_ids,
        "finish_reason": finish,
        "num_pages_out": gen.count(page_id),
        "expected_pages": expected_pages,
        "time": t_end - t0,
        "prefill_time": prefill_s,
        "clock_marks_ns": marks,
        "executed_forwards": executed_forwards,
        "burst_extra_forwards": burst_extra_forwards,
        "static_cache_reallocations": cache_reallocs,
    }


def apply_carbon_patches(model_lm, *, mode: str):
    """Apply in-memory BF16 execution patches to a loaded UnlimitedOCRForCausalLM instance."""
    spec = MODE_SPECS[mode]
    uocr_mod, dsv2_mod, _, _ = resolve_model_modules(model_lm)
    static_cache_cls = build_static_dash_cache_cls() if spec["use_gather_decode"] else None

    if spec["use_packed_moe"]:
        for li, layer in enumerate(model_lm.model.layers):
            if hasattr(layer.mlp, "experts"):
                pack_moe_layer_inplace(layer.mlp)
            elif li == 0 and hasattr(layer.mlp, "gate_proj"):
                pack_dense_mlp_inplace(layer.mlp)
        gc.collect()
        torch_mod = sys.modules.get("torch")
        if torch_mod is not None and model_lm.lm_head.weight.is_cuda:
            torch_mod.cuda.empty_cache()

    if spec["use_gather_decode"]:
        for layer in model_lm.model.layers:
            attn = layer.self_attn
            orig_fwd = attn.forward

            def make_attn_fwd(_attn, _orig):
                def _wrapped_attn_fwd(*args, **kwargs):
                    hs = kwargs["hidden_states"] if "hidden_states" in kwargs else args[0]
                    pkv = kwargs.get("past_key_value", args[3] if len(args) > 3 else kwargs.get("past_key_values"))
                    pos = kwargs.get("position_ids", args[2] if len(args) > 2 else None)
                    if (
                        hs.shape[1] == 1
                        and dsv2_mod._INFER["on"]
                        and isinstance(pkv, static_cache_cls)
                        and getattr(_attn, "dash_router", None) is not None
                    ):
                        return gather_sparse_decode_step(_attn, hs, pos, pkv, dsv2_mod)
                    return _orig(*args, **kwargs)

                return _wrapped_attn_fwd

            attn.forward = make_attn_fwd(attn, orig_fwd)

    def patched_uocr_generate(
        tokenizer,
        input_ids,
        imgs,
        seq_mask,
        spatial,
        max_new_tokens=16384,
        max_length=131072,
        temperature=0.0,
        page_count_guard=True,
        max_page_tokens=20000,
        ngram_size=0,
        ngram_window=100,
        ngram_whitelist=None,
        dash_topm=16,
        stream=False,
        tps_interval=0,
    ):
        return carbon_generate(
            model_lm,
            tokenizer,
            input_ids,
            imgs,
            seq_mask,
            spatial,
            uocr_mod=uocr_mod,
            dsv2_mod=dsv2_mod,
            static_cache_cls=static_cache_cls,
            use_gather_decode=spec["use_gather_decode"],
            use_gpu_burst=spec["use_gpu_burst"],
            burst_stride=spec["burst_stride"],
            max_new_tokens=max_new_tokens,
            max_length=max_length,
            temperature=temperature,
            page_count_guard=page_count_guard,
            max_page_tokens=max_page_tokens,
            ngram_size=ngram_size,
            ngram_window=ngram_window,
            ngram_whitelist=ngram_whitelist,
            dash_topm=dash_topm,
        )

    model_lm._uocr_generate = patched_uocr_generate
    return spec


class CarbonEngine:
    """Isolated Baidu BF16 challenger / ablation runner matching Native's window and output contract."""

    window = 3

    def __init__(self, run: Path, mode: str = "carbon_bf16"):
        if mode not in MODE_SPECS:
            raise ValueError(f"Unsupported Carbon mode: {mode}")
        self.mode = mode
        rt = self.runtime = worker.RealTorchRuntime()
        lock, _ = verify_runtime.load_json_checked(protocol.DEPENDENCY_LOCK_PATH, LOCK_SHA, "lock")
        manifest, _ = verify_runtime.load_json_checked(protocol.MODEL_MANIFEST_PATH, MANIFEST_SHA, "manifest")
        deps = verify_runtime.verify_dependency_lock(
            lock,
            accepted_provenance_exceptions=["torchvision-local-sha256-TOFU"],
            installed_distributions=rt.installed_distributions(),
            is_importable_fn=rt.is_importable,
        )
        platform = rt.query_platform()
        verify_runtime.verify_platform_and_gpu(lock, platform, GPU)
        self.pin = Generation(str(MODEL), str(NOTICE), manifest, verify_runtime.normalize_and_verify_model_dir)
        try:
            verify_runtime.verify_model_sources_ast_safety(MODEL)
            self.tokenizer, self.model, base_load_ms = rt.load_model(MODEL)
            modules = verify_runtime.verify_loaded_module_cache(Path(os.environ["HF_MODULES_CACHE"]), MODEL, sys.modules)
            import torch

            if self.model.lm_head.weight.dtype != torch.bfloat16:
                raise ValueError("native target dtype mismatch")
            t_pack = time.perf_counter()
            spec = apply_carbon_patches(self.model, mode=mode)
            torch.cuda.synchronize()
            pack_ms = int(round((time.perf_counter() - t_pack) * 1000))
            self.spec = spec
            self.info = dict(
                engine_mode=mode,
                combination=spec["combination"],
                use_packed_moe=spec["use_packed_moe"],
                use_gather_decode=spec["use_gather_decode"],
                use_gpu_burst=spec["use_gpu_burst"],
                burst_stride=spec["burst_stride"],
                model_revision=protocol.MODEL_REVISION,
                manifest_sha256=MANIFEST_SHA,
                dependency_lock_sha256=LOCK_SHA,
                platform=platform,
                dependencies=deps,
                verified_modules=modules,
                base_load_ms=base_load_ms,
                pack_patch_ms=pack_ms,
                load_ms=base_load_ms + pack_ms,
                weight_allocated_bytes_after_pack=int(torch.cuda.memory_allocated()),
                weight_reserved_bytes_after_pack=int(torch.cuda.memory_reserved()),
                tokenizer=type(self.tokenizer).__name__,
                tokenizer_sha256=digest((MODEL / "tokenizer.json").read_bytes()),
                eos_id=self.tokenizer.eos_token_id,
                page_id=protocol.PAGE_TOKEN_ID,
                target_dtype=str(torch.bfloat16),
            )
        except BaseException:
            self.close()
            raise

    def close(self):
        self.pin.close()

    def read(self, pages, folder):
        import torch

        self.pin.verify(str(MODEL), str(NOTICE), self.pin.manifest)
        cfg = protocol.build_call_kwargs(len(pages))
        uocr_mod, _, _, _ = resolve_model_modules(self.model)

        # Capture exact build_inputs, vision, and _uocr_generate dict without touching disk code.
        vision_marks = {}
        visual_tokens = None
        last_gen_dict = {}

        orig_build = uocr_mod._uocr_build_inputs
        orig_sam = self.model.model.sam_model.forward
        orig_proj = self.model.model.projector.forward
        cur_gen = self.model._uocr_generate

        def wrapped_build(*a, **kw):
            nonlocal visual_tokens
            vision_marks["build_inputs_start"] = clock()
            res = orig_build(*a, **kw)
            vision_marks["build_inputs_end"] = clock()
            visual_tokens = int(res[2].sum())
            return res

        def wrapped_sam(*a, **kw):
            if "vision_start_start" not in vision_marks:
                torch.cuda.synchronize()
                vision_marks["vision_start_start"] = clock()
            return orig_sam(*a, **kw)

        def wrapped_proj(*a, **kw):
            res = orig_proj(*a, **kw)
            torch.cuda.synchronize()
            vision_marks["vision_end_end"] = clock()
            return res

        def wrapped_gen(*a, **kw):
            res = cur_gen(*a, **kw)
            last_gen_dict.update(res)
            return res

        uocr_mod._uocr_build_inputs = wrapped_build
        self.model.model.sam_model.forward = wrapped_sam
        self.model.model.projector.forward = wrapped_proj
        self.model._uocr_generate = wrapped_gen
        safety = make_safety_monitor(self.model)
        try:
            with safety:
                text, count, elapsed_ms, vram = self.runtime.run_infer_multi(
                    self.model, self.tokenizer, [p["image"] for p in pages], cfg
                )
        finally:
            uocr_mod._uocr_build_inputs = orig_build
            self.model.model.sam_model.forward = orig_sam
            self.model.model.projector.forward = orig_proj
            self.model._uocr_generate = cur_gen

        if safety.tripwire_hits:
            raise ValueError(f"Forbidden save/eval chain entered: {safety.tripwire_hits}")
        ids = list(last_gen_dict["token_ids"])
        if last_gen_dict["text"] != text or len(ids) != count:
            raise ValueError("carbon generation output mismatch")

        marks = {**vision_marks, **last_gen_dict.get("clock_marks_ns", {})}
        grouped_calls = sum(getattr(l.mlp, "prefill_grouped_mm_calls", 0) for l in self.model.model.layers)
        fallback_calls = sum(getattr(l.mlp, "prefill_fallback_calls", 0) for l in self.model.model.layers)

        indices = [i for i, tok in enumerate(ids) if tok == protocol.PAGE_TOKEN_ID]
        raw_parts = text.split("<PAGE>")
        ok = (
            last_gen_dict["finish_reason"] == "stop"
            and last_gen_dict["expected_pages"] == last_gen_dict["num_pages_out"] == len(pages)
            and len(indices) == len(pages)
            and indices[0] == 0
            and len(raw_parts) == len(pages) + 1
            and not raw_parts[0]
        )
        details = dict(
            engine_mode=self.mode,
            combination=self.spec["combination"],
            finish_reason=last_gen_dict["finish_reason"],
            num_pages_out=last_gen_dict["num_pages_out"],
            expected_pages=last_gen_dict["expected_pages"],
            time_s=last_gen_dict["time"],
            prefill_time_s=last_gen_dict["prefill_time"],
            prompt_len=len(last_gen_dict["prompt_token_ids"]),
            native_call_kwargs=cfg,
            prompt=protocol.PROMPT,
            native_infer_ms=elapsed_ms,
            vram=vram,
            clock_marks_ns=marks,
            visual_tokens=visual_tokens,
            forward_count=last_gen_dict["executed_forwards"],
            burst_extra_forwards=last_gen_dict["burst_extra_forwards"],
            static_cache_reallocations=last_gen_dict["static_cache_reallocations"],
            prefill_grouped_mm_layer_calls=grouped_calls,
            prefill_moe_fallback_layer_calls=fallback_calls,
            eos_id=self.tokenizer.eos_token_id,
            eos_is_excluded_from_returned_ids=True,
            window_token_ids=ids,
            raw_output=text,
        )
        output = []
        if ok:
            for i, (page, start) in enumerate(zip(pages, indices)):
                raw = "<PAGE>" + raw_parts[i + 1]
                toks = ids[start : indices[i + 1] if i + 1 < len(indices) else len(ids)]
                output.append(
                    (
                        native_page(raw, page["points"]),
                        dict(
                            raw_output=raw,
                            token_ids=toks,
                            token_classes=token_classes(toks, self.tokenizer),
                            token_count=len(toks),
                        ),
                    )
                )
        self.pin.verify(str(MODEL), str(NOTICE), self.pin.manifest)
        return output, details


class ProfiledNative(Native):
    """Unmodified BF16 Native control with deferred CUDA-event + host decode stage attribution.

    Tests Carbon's >=60% stage-share falsifier while explicitly separating GPU stream
    time from post-sync host stalls and documenting asynchronous launch coupling.
    """

    MAX_EVENT_STEPS = 256

    def __init__(self, run: Path):
        super().__init__(run)
        import torch

        self.info["engine_mode"] = "native_profile"
        self.info["max_event_steps"] = self.MAX_EVENT_STEPS
        n_layers = len(self.model.model.layers)
        n_moe = sum(1 for l in self.model.model.layers if hasattr(l.mlp, "experts"))
        # Pre-allocate event pools outside timed inference to avoid cudaEventCreate overhead.
        self._ev_attn = [
            [(torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)) for _ in range(n_layers)]
            for _ in range(self.MAX_EVENT_STEPS)
        ]
        self._ev_mlp0 = [
            (torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True))
            for _ in range(self.MAX_EVENT_STEPS)
        ]
        self._ev_moe_pre = [
            [(torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)) for _ in range(n_moe)]
            for _ in range(self.MAX_EVENT_STEPS)
        ]
        self._ev_moe_exp = [
            [(torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)) for _ in range(n_moe)]
            for _ in range(self.MAX_EVENT_STEPS)
        ]
        self._ev_lmhead = [
            (torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True))
            for _ in range(self.MAX_EVENT_STEPS)
        ]

    def read(self, pages, folder):
        import torch

        uocr_mod, _, _, _ = resolve_model_modules(self.model)
        layers = list(self.model.model.layers)

        state = {
            "decode_step": -1,  # incremented on layer 0 decode entry
            "event_steps": 0,
            "lmhead_steps": 0,
            "host_ns": {
                "attn_router": 0,
                "mlp0": 0,
                "moe_gate_sort_launch": 0,
                "moe_cpu_numpy_call": 0,
                "moe_python_expert_loop": 0,
                "moe_shared_and_combine": 0,
                "lm_head_launch": 0,
                "ngram_guard_post_lmhead": 0,
                "page_guard_post_lmhead": 0,
                "streamer_put_post_sync": 0,
            },
        }

        saved_attn = []
        saved_mlp = []
        moe_slot = 0
        for li, layer in enumerate(layers):
            orig_a = layer.self_attn.forward
            saved_attn.append((layer.self_attn, orig_a))

            def make_prof_attn(_li, _orig_a):
                def _pa(*a, **kw):
                    hs = kw["hidden_states"] if "hidden_states" in kw else a[0]
                    if hs.shape[1] == 1:
                        if _li == 0:
                            state["decode_step"] += 1
                            if state["decode_step"] < self.MAX_EVENT_STEPS:
                                state["event_steps"] = state["decode_step"] + 1
                        s_idx = state["decode_step"]
                        if 0 <= s_idx < self.MAX_EVENT_STEPS:
                            ev0, ev1 = self._ev_attn[s_idx][_li]
                            ev0.record()
                            t0 = clock()
                            out = _orig_a(*a, **kw)
                            state["host_ns"]["attn_router"] += clock() - t0
                            ev1.record()
                            return out
                        t0 = clock()
                        out = _orig_a(*a, **kw)
                        state["host_ns"]["attn_router"] += clock() - t0
                        return out
                    return _orig_a(*a, **kw)

                return _pa

            layer.self_attn.forward = make_prof_attn(li, orig_a)

            if hasattr(layer.mlp, "experts"):
                moe = layer.mlp
                orig_m = moe.forward
                saved_mlp.append((moe, orig_m))
                ms = moe_slot
                moe_slot += 1

                def make_prof_moe(_moe, _ms, _orig_m):
                    @torch.no_grad()
                    def _pm(hidden_states):
                        if hidden_states.shape[1] != 1:
                            return _orig_m(hidden_states)
                        s_idx = state["decode_step"]
                        rec = 0 <= s_idx < self.MAX_EVENT_STEPS
                        if rec:
                            self._ev_moe_pre[s_idx][_ms][0].record()
                        t0 = clock()
                        identity = hidden_states
                        orig_shape = hidden_states.shape
                        topk_idx, topk_weight, _ = _moe.gate(hidden_states)
                        x = hidden_states.view(-1, hidden_states.shape[-1])
                        cnts = topk_idx.new_zeros((topk_idx.shape[0], len(_moe.experts)))
                        cnts.scatter_(1, topk_idx, 1)
                        tokens_per_expert = cnts.sum(dim=0)
                        idxs = topk_idx.view(-1).argsort()
                        sorted_tokens = x[idxs // topk_idx.shape[1]]
                        t1 = clock()
                        state["host_ns"]["moe_gate_sort_launch"] += t1 - t0
                        if rec:
                            self._ev_moe_pre[s_idx][_ms][1].record()

                        # Exact upstream synchronous GPU->CPU transfer:
                        tokens_per_expert_np = tokens_per_expert.cpu().numpy()
                        t2 = clock()
                        state["host_ns"]["moe_cpu_numpy_call"] += t2 - t1

                        if rec:
                            self._ev_moe_exp[s_idx][_ms][0].record()
                        outputs = []
                        start_idx = 0
                        for i, num_tokens in enumerate(tokens_per_expert_np):
                            end_idx = start_idx + num_tokens
                            if num_tokens == 0:
                                continue
                            expert = _moe.experts[i + _moe.ep_rank * _moe.experts_per_rank]
                            outputs.append(expert(sorted_tokens[start_idx:end_idx]))
                            start_idx = end_idx
                        t3 = clock()
                        state["host_ns"]["moe_python_expert_loop"] += t3 - t2

                        outs = torch.cat(outputs, dim=0) if len(outputs) else sorted_tokens.new_empty(0)
                        new_x = torch.empty_like(outs)
                        new_x[idxs] = outs
                        final_out = (
                            new_x.view(*topk_ids_shape(topk_idx), -1)
                            .type(topk_weight.dtype)
                            .mul_(topk_weight.unsqueeze(dim=-1))
                            .sum(dim=1)
                            .type(new_x.dtype)
                            .view(*orig_shape)
                        )
                        if _moe.config.n_shared_experts is not None:
                            final_out = final_out + _moe.shared_experts(identity)
                        if rec:
                            self._ev_moe_exp[s_idx][_ms][1].record()
                        state["host_ns"]["moe_shared_and_combine"] += clock() - t3
                        return final_out

                    return _pm

                moe.forward = make_prof_moe(moe, ms, orig_m)
            else:
                mlp0 = layer.mlp
                orig_m0 = mlp0.forward
                saved_mlp.append((mlp0, orig_m0))

                def make_prof_mlp0(_orig_m0):
                    def _pm0(x):
                        if x.shape[1] == 1:
                            s_idx = state["decode_step"]
                            if 0 <= s_idx < self.MAX_EVENT_STEPS:
                                self._ev_mlp0[s_idx][0].record()
                            t0 = clock()
                            out = _orig_m0(x)
                            state["host_ns"]["mlp0"] += clock() - t0
                            if 0 <= s_idx < self.MAX_EVENT_STEPS:
                                self._ev_mlp0[s_idx][1].record()
                            return out
                        return _orig_m0(x)

                    return _pm0

                mlp0.forward = make_prof_mlp0(orig_m0)

        orig_lm = self.model.lm_head.forward
        orig_ng = uocr_mod._uocr_no_repeat_ngram
        orig_pg = uocr_mod._uocr_page_count_guard
        streamer_cls = uocr_mod.TextStreamer
        orig_put = streamer_cls.put

        def prof_lm(x):
            s_idx = state["decode_step"]
            rec = 0 <= s_idx < self.MAX_EVENT_STEPS and s_idx == state["lmhead_steps"]
            if rec:
                self._ev_lmhead[s_idx][0].record()
            t0 = clock()
            out = orig_lm(x)
            state["host_ns"]["lm_head_launch"] += clock() - t0
            if rec:
                self._ev_lmhead[s_idx][1].record()
                state["lmhead_steps"] = s_idx + 1
            return out

        def prof_ng(*a, **kw):
            t0 = clock()
            res = orig_ng(*a, **kw)
            if state["decode_step"] >= 0:
                state["host_ns"]["ngram_guard_post_lmhead"] += clock() - t0
            return res

        def prof_pg(*a, **kw):
            t0 = clock()
            res = orig_pg(*a, **kw)
            if state["decode_step"] >= 0:
                state["host_ns"]["page_guard_post_lmhead"] += clock() - t0
            return res

        @functools.wraps(orig_put)
        def prof_put(self_s, value):
            t0 = clock()
            res = orig_put(self_s, value)
            if state["decode_step"] >= 0:
                state["host_ns"]["streamer_put_post_sync"] += clock() - t0
            return res

        self.model.lm_head.forward = prof_lm
        uocr_mod._uocr_no_repeat_ngram = prof_ng
        uocr_mod._uocr_page_count_guard = prof_pg
        streamer_cls.put = prof_put

        try:
            output, details = super().read(pages, folder)
        finally:
            for mod, fn in saved_attn:
                mod.forward = fn
            for mod, fn in saved_mlp:
                mod.forward = fn
            self.model.lm_head.forward = orig_lm
            uocr_mod._uocr_no_repeat_ngram = orig_ng
            uocr_mod._uocr_page_count_guard = orig_pg
            streamer_cls.put = orig_put

        torch.cuda.synchronize()
        es = state["event_steps"]
        lms = state["lmhead_steps"]
        gpu_ms = {
            "attn_router": sum(e0.elapsed_time(e1) for s in range(es) for e0, e1 in self._ev_attn[s]),
            "mlp0_dense": sum(self._ev_mlp0[s][0].elapsed_time(self._ev_mlp0[s][1]) for s in range(es)),
            "moe_gate_and_sort": sum(e0.elapsed_time(e1) for s in range(es) for e0, e1 in self._ev_moe_pre[s]),
            "moe_experts_and_shared": sum(e0.elapsed_time(e1) for s in range(es) for e0, e1 in self._ev_moe_exp[s]),
            "lm_head": sum(self._ev_lmhead[s][0].elapsed_time(self._ev_lmhead[s][1]) for s in range(lms)),
        }
        total_decode_steps = max(0, state["decode_step"] + 1)
        marks = details["clock_marks_ns"]
        post_first_wall_ms = (
            (marks["generate_end"] - marks["first_token"]) / 1e6
            if "first_token" in marks and "generate_end" in marks
            else None
        )
        host_ms = {k: v / 1e6 for k, v in state["host_ns"].items()}
        gpu_per_step_ms = {k: (v / es if es > 0 else 0.0) for k, v in gpu_ms.items()}
        host_per_step_ms = {k: (v / total_decode_steps if total_decode_steps > 0 else 0.0) for k, v in host_ms.items()}

        # Streamer.put runs strictly AFTER int(torch.argmax(logits)) synchronized the stream,
        # so streamer_put_post_sync is pure host-induced GPU-idle wall time.
        # In contrast, moe_cpu_numpy_call includes queued GPU work from preceding async ops
        # (attn_router + layer norms + moe_gate_and_sort) plus WDDM D2H sync overhead.
        targeted_host_per_step_ms = (
            host_per_step_ms["attn_router"]
            + host_per_step_ms["moe_gate_sort_launch"]
            + host_per_step_ms["moe_cpu_numpy_call"]
            + host_per_step_ms["moe_python_expert_loop"]
            + host_per_step_ms["moe_shared_and_combine"]
            + host_per_step_ms["ngram_guard_post_lmhead"]
            + host_per_step_ms["page_guard_post_lmhead"]
            + host_per_step_ms["streamer_put_post_sync"]
        )
        decode_step_wall_ms = (post_first_wall_ms / total_decode_steps) if (post_first_wall_ms and total_decode_steps > 0) else None
        details["engine_mode"] = "native_profile"
        details["decode_stage_profile"] = {
            "total_decode_steps": total_decode_steps,
            "cuda_event_sampled_steps": es,
            "post_first_token_wall_ms": post_first_wall_ms,
            "mean_decode_step_wall_ms": decode_step_wall_ms,
            "cuda_event_sum_ms_over_sampled_steps": gpu_ms,
            "cuda_event_mean_ms_per_step": gpu_per_step_ms,
            "host_span_sum_ms_over_all_steps": host_ms,
            "host_span_mean_ms_per_step": host_per_step_ms,
            "targeted_subsystems_host_ms_per_step": targeted_host_per_step_ms,
            "targeted_subsystems_fraction_of_step_wall": (
                targeted_host_per_step_ms / decode_step_wall_ms if decode_step_wall_ms else None
            ),
            "falsifier_60pct_stage_share_passed": (
                bool((targeted_host_per_step_ms / decode_step_wall_ms) >= 0.60)
                if decode_step_wall_ms
                else None
            ),
            "attribution_caveats": {
                "pure_host_idle_after_argmax_sync": "streamer_put_post_sync runs strictly after int(torch.argmax(logits)) flushes the default stream, so the GPU decode stream is idle during that span.",
                "coupled_sync_and_async_gpu": "moe_cpu_numpy_call host time spans both WDDM D2H synchronization latency and completion of prior asynchronously launched GPU kernels (self_attn + norms + MoEGate/sort) since the previous sync.",
                "inter_kernel_launch_bubbles": "CUDA event brackets (e.g., moe_experts_and_shared, attn_router) include GPU kernel execution plus any inter-kernel launch gaps inside that bracket; only paired ablations (carbon_moe, carbon_gather, carbon_bf16) establish causal wall-time savings.",
            },
        }
        return output, details


def topk_ids_shape(t):
    return t.shape


def create_engine(mode: str, run: Path):
    if mode == "native":
        return Native(run)
    if mode == "native_profile":
        return ProfiledNative(run)
    if mode in MODE_SPECS:
        return CarbonEngine(run, mode=mode)
    raise ValueError(f"Unknown mode: {mode}")
