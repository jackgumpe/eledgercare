"""Orthogonal 6-switch decomposition of Carbon BF16 over Unlimited-OCR-2 (04809669...).

Switches (in canonical bit order):
  S0  no_text_streamer       False: per-token host TextStreamer callback
                             True:  silent token accumulation (UTF-8 safe)
  S1a packed_moe_prefill     False: per-expert F.linear loop during prefill
                             True:  torch._grouped_mm over packed routed expert weights during prefill
  S1b packed_moe_decode_bmm  False: per-expert F.linear loop during single-token decode
                             True:  torch.bmm gathered expert dispatch during single-token decode
  S1c fused_gate_up_proj     False: separate gate_proj and up_proj GEMMs (Layer-0 dense, shared, routed)
                             True:  concatenated [gate_proj; up_proj] GEMM + split before activation
  S2  gather_sparse_decode   False: DynamicCache + upstream full-KV masked _decode_attend
                             True:  StaticDashCache (init_cap>=4096) + 512-key gather_sparse_decode_step
  S3  gpu_burst_stride_8     False: 1-step host guarded greedy loop with immediate EOS stop
                             True:  8-step device guarded greedy burst loop with post-EOS host truncation

No torch or CUDA module is imported at module import time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import gc
from itertools import combinations
import json
import math
import sys
import time
from pathlib import Path
from time import perf_counter_ns as clock

HERE = Path(__file__).resolve().parent
SURGICAL_JSON_PATH = HERE / "surgical.json"

SWITCH_ORDER: tuple[str, ...] = ("S0", "S1a", "S1b", "S1c", "S2", "S3")
SWITCH_FLAG_NAMES: dict[str, str] = {
    "S0": "no_text_streamer",
    "S1a": "packed_moe_prefill",
    "S1b": "packed_moe_decode_bmm",
    "S1c": "fused_gate_up_proj",
    "S2": "gather_sparse_decode",
    "S3": "gpu_burst_stride_8",
}

# Canonical 16-arm Stage A1 sweep:
#   - 2 genuine existing WP-0015/0016 endpoints ('native', 'carbon_bf16')
#   - 2 parameterized endpoint equivalence proofs ('all_off' == 000000, 'all_on' == 111111)
#   - 6 single-switch additions ('add_S0' .. 'add_S3')
#   - 6 single-switch removals ('remove_S0' .. 'remove_S3')
CANONICAL_A1_CONFIGS: tuple[str, ...] = (
    "native",
    "all_off",
    "carbon_bf16",
    "all_on",
    "add_S0",
    "add_S1a",
    "add_S1b",
    "add_S1c",
    "add_S2",
    "add_S3",
    "remove_S0",
    "remove_S1a",
    "remove_S1b",
    "remove_S1c",
    "remove_S2",
    "remove_S3",
)

# 14-vector design matrix names matching docs/research/WP-0017/design/rules.py:matrix()
DESIGN_14_NAMES: tuple[str, ...] = (
    "native",
    "carbon_bf16",
    "add_S0",
    "add_S1a",
    "add_S1b",
    "add_S1c",
    "add_S2",
    "add_S3",
    "remove_S0",
    "remove_S1a",
    "remove_S1b",
    "remove_S1c",
    "remove_S2",
    "remove_S3",
)


@dataclass(frozen=True)
class SwitchConfig:
    no_text_streamer: bool = False       # S0
    packed_moe_prefill: bool = False     # S1a
    packed_moe_decode_bmm: bool = False  # S1b
    fused_gate_up_proj: bool = False     # S1c
    gather_sparse_decode: bool = False   # S2
    gpu_burst_stride_8: bool = False     # S3

    @property
    def bits(self) -> str:
        vals = (
            self.no_text_streamer,
            self.packed_moe_prefill,
            self.packed_moe_decode_bmm,
            self.fused_gate_up_proj,
            self.gather_sparse_decode,
            self.gpu_burst_stride_8,
        )
        return "".join("1" if v else "0" for v in vals)

    @property
    def by_id(self) -> dict[str, bool]:
        return {
            "S0": self.no_text_streamer,
            "S1a": self.packed_moe_prefill,
            "S1b": self.packed_moe_decode_bmm,
            "S1c": self.fused_gate_up_proj,
            "S2": self.gather_sparse_decode,
            "S3": self.gpu_burst_stride_8,
        }

    @property
    def by_flag(self) -> dict[str, bool]:
        return {SWITCH_FLAG_NAMES[k]: v for k, v in self.by_id.items()}

    @property
    def enabled_switches(self) -> list[str]:
        return [s for s in SWITCH_ORDER if self.by_id[s]]

    @property
    def disabled_switches(self) -> list[str]:
        return [s for s in SWITCH_ORDER if not self.by_id[s]]

    @classmethod
    def from_bits(cls, bitstr: str) -> "SwitchConfig":
        if len(bitstr) != 6 or any(c not in ("0", "1") for c in bitstr):
            raise ValueError(f"Expected 6-char 0/1 bitstring, got {bitstr!r}")
        b = [c == "1" for c in bitstr]
        return cls(
            no_text_streamer=b[0],
            packed_moe_prefill=b[1],
            packed_moe_decode_bmm=b[2],
            fused_gate_up_proj=b[3],
            gather_sparse_decode=b[4],
            gpu_burst_stride_8=b[5],
        )

    @classmethod
    def from_enabled(cls, enabled: set[str] | tuple[str, ...] | list[str]) -> "SwitchConfig":
        unknown = set(enabled) - set(SWITCH_ORDER)
        if unknown:
            raise ValueError(f"Unknown switch IDs: {sorted(unknown)}")
        en = set(enabled)
        return cls(
            no_text_streamer=("S0" in en),
            packed_moe_prefill=("S1a" in en),
            packed_moe_decode_bmm=("S1b" in en),
            fused_gate_up_proj=("S1c" in en),
            gather_sparse_decode=("S2" in en),
            gpu_burst_stride_8=("S3" in en),
        )


@dataclass(frozen=True)
class ResolvedMode:
    requested_name: str
    canonical_name: str
    implementation: str  # 'genuine_native' | 'genuine_carbon_bf16' | 'ablation_engine'
    switch_config: SwitchConfig
    family: str  # 'genuine_endpoint' | 'endpoint_proof' | 'single_add' | 'single_remove' | 'pair_remove' | 'custom_bits' | 'surgical'
    removed_switches: tuple[str, ...] = ()
    added_switches: tuple[str, ...] = ()


def _build_named_switch_table() -> dict[str, tuple[str, SwitchConfig, str, tuple[str, ...], tuple[str, ...]]]:
    table: dict[str, tuple[str, SwitchConfig, str, tuple[str, ...], tuple[str, ...]]] = {}
    all_off = SwitchConfig.from_bits("000000")
    all_on = SwitchConfig.from_bits("111111")
    table["all_off"] = ("all_off", all_off, "endpoint_proof", (), ())
    table["all_on"] = ("all_on", all_on, "endpoint_proof", (), tuple(SWITCH_ORDER))

    for s in SWITCH_ORDER:
        add_cfg = SwitchConfig.from_enabled((s,))
        add_name = f"add_{s}"
        table[add_name] = (add_name, add_cfg, "single_add", (), (s,))

        rem_cfg = SwitchConfig.from_enabled([x for x in SWITCH_ORDER if x != s])
        rem_name = f"remove_{s}"
        table[rem_name] = (rem_name, rem_cfg, "single_remove", (s,), tuple(x for x in SWITCH_ORDER if x != s))
        table[f"rem_{s}"] = (rem_name, rem_cfg, "single_remove", (s,), tuple(x for x in SWITCH_ORDER if x != s))

    for s1, s2 in combinations(SWITCH_ORDER, 2):
        pair_cfg = SwitchConfig.from_enabled([x for x in SWITCH_ORDER if x not in (s1, s2)])
        pair_name = f"remove_{s1}_{s2}"
        enabled_rest = tuple(x for x in SWITCH_ORDER if x not in (s1, s2))
        table[pair_name] = (pair_name, pair_cfg, "pair_remove", (s1, s2), enabled_rest)
        table[f"rem_{s1}_{s2}"] = (pair_name, pair_cfg, "pair_remove", (s1, s2), enabled_rest)

    return table


NAMED_SWITCH_TABLE = _build_named_switch_table()


def _pruned_bits(name: str) -> str:
    if name == "carbon_surgical":
        raise ValueError("Self-referential surgical configuration")
    bits = resolve_mode(name).switch_config.bits
    if bits.count("0") not in (1, 2):
        raise ValueError("Surgical configuration requires exactly one or two removed switches")
    return bits


def load_frozen_surgical_target(surgical_json_path: Path = SURGICAL_JSON_PATH) -> str | None:
    if not surgical_json_path.is_file():
        return None
    doc = json.loads(surgical_json_path.read_text(encoding="utf-8"))
    targets = [doc[k] for k in ("frozen_switch_config", "frozen_bits") if doc.get(k) is not None]
    if not targets:
        return None
    bits = {_pruned_bits(name) for name in targets}
    if len(bits) != 1:
        raise ValueError("Frozen surgical configuration and bits disagree")
    return bits.pop()


def resolve_mode(name: str, *, surgical_override: str | None = None) -> ResolvedMode:
    if name == "native":
        return ResolvedMode(
            requested_name="native",
            canonical_name="native",
            implementation="genuine_native",
            switch_config=SwitchConfig.from_bits("000000"),
            family="genuine_endpoint",
        )
    if name == "carbon_bf16":
        return ResolvedMode(
            requested_name="carbon_bf16",
            canonical_name="carbon_bf16",
            implementation="genuine_carbon_bf16",
            switch_config=SwitchConfig.from_bits("111111"),
            family="genuine_endpoint",
            added_switches=SWITCH_ORDER,
        )
    if name == "carbon_surgical":
        target = load_frozen_surgical_target()
        if not target:
            raise ValueError(
                "carbon_surgical is locked prior to Stage A1 disposition (surgical.json has frozen_switch_config=null)."
            )
        if surgical_override is not None and _pruned_bits(surgical_override) != target:
            raise ValueError("Plan surgical configuration disagrees with frozen source")
        inner = resolve_mode(target)
        return ResolvedMode(
            requested_name="carbon_surgical",
            canonical_name="carbon_surgical",
            implementation="ablation_engine",
            switch_config=inner.switch_config,
            family="surgical",
            removed_switches=tuple(inner.switch_config.disabled_switches),
            added_switches=tuple(inner.switch_config.enabled_switches),
        )
    if name in NAMED_SWITCH_TABLE:
        canon, cfg, fam, rem, add = NAMED_SWITCH_TABLE[name]
        return ResolvedMode(
            requested_name=name,
            canonical_name=canon,
            implementation="ablation_engine",
            switch_config=cfg,
            family=fam,
            removed_switches=rem,
            added_switches=add,
        )
    bit_candidate = name.removeprefix("s_") if name.startswith("s_") else name
    if len(bit_candidate) == 6 and all(c in ("0", "1") for c in bit_candidate):
        cfg = SwitchConfig.from_bits(bit_candidate)
        return ResolvedMode(
            requested_name=name,
            canonical_name=f"s_{cfg.bits}",
            implementation="ablation_engine",
            switch_config=cfg,
            family="custom_bits",
            removed_switches=tuple(cfg.disabled_switches),
            added_switches=tuple(cfg.enabled_switches),
        )
    raise ValueError(f"Unsupported WP-0017 engine mode: {name!r}")


@dataclass
class SwitchActivationCounters:
    """Cumulative and window-delta instrumentation proving every switch executes its real op."""

    num_layers: int = 12
    s0_streamer_put_calls: int = 0
    s0_streamer_end_calls: int = 0
    s0_silent_accum_tokens: int = 0

    s1a_prefill_grouped_mm_calls: int = 0
    s1a_prefill_fallback_calls: int = 0
    s1a_prefill_linear_loop_calls: int = 0
    s1a_prefill_linear_expert_calls: int = 0
    per_layer_prefill_grouped_mm: dict[int, int] = field(default_factory=dict)
    per_layer_prefill_fallback: dict[int, int] = field(default_factory=dict)
    per_layer_prefill_linear_loop: dict[int, int] = field(default_factory=dict)

    s1b_decode_bmm_calls: int = 0
    s1b_decode_linear_loop_calls: int = 0
    s1b_decode_linear_expert_calls: int = 0

    s1c_dense_fused_calls: int = 0
    s1c_dense_unfused_calls: int = 0
    s1c_shared_fused_calls: int = 0
    s1c_shared_unfused_calls: int = 0
    s1c_routed_fused_op_calls: int = 0
    s1c_routed_unfused_op_calls: int = 0

    s2_static_gather_decode_calls: int = 0
    s2_dynamic_masked_decode_calls: int = 0
    s2_last_cache_telemetry: dict[str, object] = field(default_factory=dict)

    s3_single_step_iters: int = 0
    s3_burst_chunks: int = 0
    s3_burst_steps_launched: int = 0
    s3_burst_extra_forwards: int = 0

    def snapshot(self) -> dict:
        return {
            "s0_streamer_put_calls": self.s0_streamer_put_calls,
            "s0_streamer_end_calls": self.s0_streamer_end_calls,
            "s0_silent_accum_tokens": self.s0_silent_accum_tokens,
            "s1a_prefill_grouped_mm_calls": self.s1a_prefill_grouped_mm_calls,
            "s1a_prefill_fallback_calls": self.s1a_prefill_fallback_calls,
            "s1a_prefill_linear_loop_calls": self.s1a_prefill_linear_loop_calls,
            "s1a_prefill_linear_expert_calls": self.s1a_prefill_linear_expert_calls,
            "per_layer_prefill_grouped_mm": {str(k): v for k, v in sorted(self.per_layer_prefill_grouped_mm.items())},
            "per_layer_prefill_fallback": {str(k): v for k, v in sorted(self.per_layer_prefill_fallback.items())},
            "per_layer_prefill_linear_loop": {str(k): v for k, v in sorted(self.per_layer_prefill_linear_loop.items())},
            "s1b_decode_bmm_calls": self.s1b_decode_bmm_calls,
            "s1b_decode_linear_loop_calls": self.s1b_decode_linear_loop_calls,
            "s1b_decode_linear_expert_calls": self.s1b_decode_linear_expert_calls,
            "s1c_dense_fused_calls": self.s1c_dense_fused_calls,
            "s1c_dense_unfused_calls": self.s1c_dense_unfused_calls,
            "s1c_shared_fused_calls": self.s1c_shared_fused_calls,
            "s1c_shared_unfused_calls": self.s1c_shared_unfused_calls,
            "s1c_routed_fused_op_calls": self.s1c_routed_fused_op_calls,
            "s1c_routed_unfused_op_calls": self.s1c_routed_unfused_op_calls,
            "s2_static_gather_decode_calls": self.s2_static_gather_decode_calls,
            "s2_dynamic_masked_decode_calls": self.s2_dynamic_masked_decode_calls,
            "s2_last_cache_telemetry": dict(self.s2_last_cache_telemetry),
            "s3_single_step_iters": self.s3_single_step_iters,
            "s3_burst_chunks": self.s3_burst_chunks,
            "s3_burst_steps_launched": self.s3_burst_steps_launched,
            "s3_burst_extra_forwards": self.s3_burst_extra_forwards,
        }

    @staticmethod
    def delta(before: dict, after: dict) -> dict:
        out: dict[str, object] = {}
        for k, v_after in after.items():
            v_before = before.get(k)
            if isinstance(v_after, int) and isinstance(v_before, int):
                out[k] = v_after - v_before
            elif k.startswith("per_layer_") and isinstance(v_after, dict) and isinstance(v_before, dict):
                keys = sorted(set(v_after) | set(v_before), key=lambda x: int(x))
                out[k] = {lk: int(v_after.get(lk, 0)) - int(v_before.get(lk, 0)) for lk in keys}
            else:
                out[k] = v_after
        return out


def _extract_dynamic_kv(dyn_cache, layer_idx: int):
    if hasattr(dyn_cache, "key_cache"):
        return dyn_cache.key_cache[layer_idx], dyn_cache.value_cache[layer_idx]
    return dyn_cache.layers[layer_idx].keys, dyn_cache.layers[layer_idx].values


def _compute_headcls_kbar_blocks(idx_k_blk, valid_mask, head_cls, inv_sqrt_d: float, act_clamp: float):
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
    """Build StaticDashCache matching WP-0015 engine.py with true capacity telemetry and snapshot cloning."""
    import torch
    from transformers.cache_utils import Cache

    class StaticDashCache(Cache):
        def __init__(self, dyn_cache, decoder, *, init_cap: int, max_cap: int, act_clamp: float):
            super().__init__()
            self.num_layers = len(decoder.layers)
            k0, _ = _extract_dynamic_kv(dyn_cache, 0)
            self.bsz, self.num_kv_heads, s0, self.head_dim = k0.shape
            self.dtype = k0.dtype
            self.device = k0.device
            self.prefill_seq_len = int(s0)
            self.requested_init_cap = int(init_cap)
            self.max_cap = max(s0 + 1, int(max_cap))
            first_router = decoder.layers[0].self_attn.dash_router
            self.block_size = int(first_router.block_size)
            self.local_window = int(first_router.local_window)
            p_infer = getattr(first_router, "_infer_params", None) or {}
            self.routed_topk_blocks = int(p_infer.get("K", 12))
            self.index_dim = int(first_router.index_dim)
            self.act_clamp = float(act_clamp)
            self.inv_sqrt_idx_d = 1.0 / math.sqrt(self.index_dim)
            self._blk_arange = torch.arange(self.block_size, device=self.device)
            self._local_arange = torch.arange(self.local_window, device=self.device)

            cap_tok = min(self.max_cap, max(int(init_cap), s0 + 1))
            cap_blk = -(-cap_tok // self.block_size)
            cap_tok = cap_blk * self.block_size
            self.init_cap_tok = int(cap_tok)
            self.cap_tok = int(cap_tok)
            self.cap_blk = int(cap_blk)
            self.seq_lens = [s0] * self.num_layers
            self.peak_seq_len = int(s0)
            self.reallocations = 0
            self.decode_layer_appends = 0

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
            self.cap_tok = int(new_tok)
            self.cap_blk = int(new_blk)
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
            if s_new > self.peak_seq_len:
                self.peak_seq_len = int(s_new)
            self.decode_layer_appends += 1

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

        def capacity_telemetry(self) -> dict:
            return {
                "cache_type": "StaticDashCache",
                "prefill_seq_len": self.prefill_seq_len,
                "requested_init_cap": self.requested_init_cap,
                "init_cap_tok": self.init_cap_tok,
                "final_cap_tok": self.cap_tok,
                "max_cap_tok": self.max_cap,
                "block_size": self.block_size,
                "local_window": self.local_window,
                "routed_topk_blocks": self.routed_topk_blocks,
                "gathered_key_width": self.routed_topk_blocks * self.block_size + self.local_window,
                "peak_seq_len": self.peak_seq_len,
                "reallocations": self.reallocations,
                "decode_layer_appends": self.decode_layer_appends,
                "num_layers": self.num_layers,
            }

    return StaticDashCache


def gather_sparse_decode_step(attn, hidden_states, position_ids, static_cache, dsv2_mod):
    """Exact single-token gather-sparse decode step matching WP-0015 engine.py."""
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


def patch_dense_mlp_s1c(mlp, *, fused: bool, counters: SwitchActivationCounters) -> None:
    """Configure Layer-0 dense DeepseekV2MLP for S1c (True: fused [gate; up], False: separate GEMMs)."""
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    if fused:
        inter = mlp.gate_proj.out_features
        w_gu = torch.cat([mlp.gate_proj.weight.data, mlp.up_proj.weight.data], dim=0).contiguous()
        w_dn = mlp.down_proj.weight.data
        act_fn = mlp.act_fn
        mlp.gate_proj = None
        mlp.up_proj = None
        mlp.w_gate_up = nn.Parameter(w_gu, requires_grad=False)

        def fused_dense_forward(x):
            counters.s1c_dense_fused_calls += 1
            gu = F.linear(x, mlp.w_gate_up)
            gate, up = gu.split(inter, dim=-1)
            return F.linear(act_fn(gate) * up, w_dn)

        mlp.forward = fused_dense_forward
    else:
        orig_forward = mlp.forward

        def unfused_dense_forward(x):
            counters.s1c_dense_unfused_calls += 1
            return orig_forward(x)

        mlp.forward = unfused_dense_forward


def patch_moe_layer_s1(
    moe,
    *,
    layer_idx: int,
    s1a_grouped_prefill: bool,
    s1b_decode_bmm: bool,
    s1c_fused_gate_up: bool,
    counters: SwitchActivationCounters,
) -> None:
    """Orthogonal S1a (prefill grouped_mm), S1b (decode bmm), S1c (fused gate_up) for DeepseekV2MoE.

    Weight storage is strictly in-place (zero extra VRAM vs unmodified checkpoint):
      - All three False (0,0,0): retains original moe.experts and moe.shared_experts nn.Linear modules
        and runs the exact upstream per-expert loop + separate gate/up GEMMs, adding only counters.
      - S1c == True: packs w_gate_up_nk [E, 2*inter, hidden], w_down_nk [E, hidden, inter], and
        sh_gate_up [2*sh_inter, hidden], freeing moe.experts and moe.shared_experts.
      - S1c == False and (S1a or S1b): packs separate w_gate_nk [E, inter, hidden],
        w_up_nk [E, inter, hidden], and w_down_nk [E, hidden, inter], freeing moe.experts while
        keeping moe.shared_experts separate (unfused).
    """
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    counters.per_layer_prefill_grouped_mm.setdefault(layer_idx, 0)
    counters.per_layer_prefill_fallback.setdefault(layer_idx, 0)
    counters.per_layer_prefill_linear_loop.setdefault(layer_idx, 0)

    if not s1a_grouped_prefill and not s1b_decode_bmm and not s1c_fused_gate_up:
        # Pure native MoE execution path with non-invasive call counters.
        has_shared = moe.config.n_shared_experts is not None and moe.shared_experts is not None

        @torch.no_grad()
        def instrumented_native_moe_forward(hidden_states):
            identity = hidden_states
            orig_shape = hidden_states.shape
            topk_idx, topk_weight, _ = moe.gate(hidden_states)
            x = hidden_states.view(-1, hidden_states.shape[-1])
            n_tok = x.shape[0]

            cnts = topk_idx.new_zeros((topk_idx.shape[0], len(moe.experts)))
            cnts.scatter_(1, topk_idx, 1)
            tokens_per_expert = cnts.sum(dim=0)
            idxs = topk_idx.view(-1).argsort()
            sorted_tokens = x[idxs // topk_idx.shape[1]]
            tokens_per_expert_np = tokens_per_expert.cpu().numpy()

            if n_tok == 1:
                counters.s1b_decode_linear_loop_calls += 1
            else:
                counters.s1a_prefill_linear_loop_calls += 1
                counters.per_layer_prefill_linear_loop[layer_idx] += 1

            outputs = []
            start_idx = 0
            for i, num_tokens in enumerate(tokens_per_expert_np):
                end_idx = start_idx + num_tokens
                if num_tokens == 0:
                    continue
                expert = moe.experts[i + moe.ep_rank * moe.experts_per_rank]
                outputs.append(expert(sorted_tokens[start_idx:end_idx]))
                if n_tok == 1:
                    counters.s1b_decode_linear_expert_calls += 1
                else:
                    counters.s1a_prefill_linear_expert_calls += 1
                counters.s1c_routed_unfused_op_calls += 1
                start_idx = end_idx

            outs = torch.cat(outputs, dim=0) if len(outputs) else sorted_tokens.new_empty(0)
            new_x = torch.empty_like(outs)
            new_x[idxs] = outs
            y = (
                new_x.view(*topk_idx.shape, -1)
                .type(topk_weight.dtype)
                .mul_(topk_weight.unsqueeze(dim=-1))
                .sum(dim=1)
                .type(new_x.dtype)
                .view(*orig_shape)
            )
            if has_shared:
                counters.s1c_shared_unfused_calls += 1
                y = y + moe.shared_experts(identity)
            return y

        moe.forward = instrumented_native_moe_forward
        return

    n_routed = len(moe.experts)
    e0 = moe.experts[0]
    hidden = e0.gate_proj.in_features
    inter = e0.gate_proj.out_features
    dtype = e0.gate_proj.weight.dtype
    device = e0.gate_proj.weight.device
    act_fn = e0.act_fn

    w_dn_nk = torch.empty((n_routed, hidden, inter), dtype=dtype, device=device)
    if s1c_fused_gate_up:
        w_gu_nk = torch.empty((n_routed, 2 * inter, hidden), dtype=dtype, device=device)
        for i, exp in enumerate(moe.experts):
            w_gu_nk[i, :inter, :].copy_(exp.gate_proj.weight.data)
            w_gu_nk[i, inter:, :].copy_(exp.up_proj.weight.data)
            w_dn_nk[i].copy_(exp.down_proj.weight.data)
        moe.w_gate_up_nk = nn.Parameter(w_gu_nk, requires_grad=False)
    else:
        w_g_nk = torch.empty((n_routed, inter, hidden), dtype=dtype, device=device)
        w_u_nk = torch.empty((n_routed, inter, hidden), dtype=dtype, device=device)
        for i, exp in enumerate(moe.experts):
            w_g_nk[i].copy_(exp.gate_proj.weight.data)
            w_u_nk[i].copy_(exp.up_proj.weight.data)
            w_dn_nk[i].copy_(exp.down_proj.weight.data)
        moe.w_gate_nk = nn.Parameter(w_g_nk, requires_grad=False)
        moe.w_up_nk = nn.Parameter(w_u_nk, requires_grad=False)

    moe.w_down_nk = nn.Parameter(w_dn_nk, requires_grad=False)
    moe.experts = nn.ModuleList()

    has_shared = moe.config.n_shared_experts is not None and moe.shared_experts is not None
    sh_inter = 0
    sh_dn = None
    if has_shared and s1c_fused_gate_up:
        sh = moe.shared_experts
        sh_inter = sh.gate_proj.out_features
        moe.sh_gate_up = nn.Parameter(
            torch.cat([sh.gate_proj.weight.data, sh.up_proj.weight.data], dim=0).contiguous(),
            requires_grad=False,
        )
        sh_dn = sh.down_proj.weight
        moe.shared_experts = None

    moe.prefill_grouped_mm_calls = 0
    moe.prefill_fallback_calls = 0
    moe._grouped_mm_supported = hasattr(torch, "_grouped_mm")
    moe._force_grouped_mm_for_test = False

    @torch.no_grad()
    def orthogonal_moe_forward(hidden_states):
        identity = hidden_states
        orig_shape = hidden_states.shape
        topk_idx, topk_weight, _ = moe.gate(hidden_states)
        x = hidden_states.view(-1, hidden)
        n_tok = x.shape[0]
        k_top = topk_idx.shape[1]

        if n_tok == 1:
            if s1b_decode_bmm:
                counters.s1b_decode_bmm_calls += 1
                idx = topk_idx.view(k_top)
                x_bmm = x.expand(k_top, hidden).unsqueeze(1)
                if s1c_fused_gate_up:
                    counters.s1c_routed_fused_op_calls += 1
                    w_gu = moe.w_gate_up_nk.index_select(0, idx)
                    gu = torch.bmm(x_bmm, w_gu.transpose(1, 2))
                    gate, up = gu.split(inter, dim=-1)
                else:
                    counters.s1c_routed_unfused_op_calls += 1
                    w_g = moe.w_gate_nk.index_select(0, idx)
                    w_u = moe.w_up_nk.index_select(0, idx)
                    gate = torch.bmm(x_bmm, w_g.transpose(1, 2))
                    up = torch.bmm(x_bmm, w_u.transpose(1, 2))
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
                counters.s1b_decode_linear_loop_calls += 1
                cnts = topk_idx.new_zeros((topk_idx.shape[0], n_routed))
                cnts.scatter_(1, topk_idx, 1)
                tokens_per_expert = cnts.sum(dim=0)
                idxs = topk_idx.view(-1).argsort()
                sorted_tokens = x[idxs // k_top]
                tokens_per_expert_np = tokens_per_expert.cpu().numpy()
                outputs = []
                start_idx = 0
                for ei, num_tokens in enumerate(tokens_per_expert_np):
                    end_idx = start_idx + num_tokens
                    if num_tokens == 0:
                        continue
                    seg = sorted_tokens[start_idx:end_idx]
                    if s1c_fused_gate_up:
                        counters.s1c_routed_fused_op_calls += 1
                        gu = F.linear(seg, moe.w_gate_up_nk[ei])
                        gate, up = gu.split(inter, dim=-1)
                    else:
                        counters.s1c_routed_unfused_op_calls += 1
                        gate = F.linear(seg, moe.w_gate_nk[ei])
                        up = F.linear(seg, moe.w_up_nk[ei])
                    outputs.append(F.linear(act_fn(gate) * up, moe.w_down_nk[ei]))
                    counters.s1b_decode_linear_expert_calls += 1
                    start_idx = end_idx
                outs = torch.cat(outputs, dim=0) if len(outputs) else sorted_tokens.new_empty(0)
                new_x = torch.empty_like(outs)
                new_x[idxs] = outs
                routed = (
                    new_x.view(*topk_idx.shape, -1)
                    .type(topk_weight.dtype)
                    .mul_(topk_weight.unsqueeze(dim=-1))
                    .sum(dim=1)
                    .type(new_x.dtype)
                )
        else:
            if s1a_grouped_prefill:
                flat_idx = topk_idx.view(-1)
                order = flat_idx.argsort()
                sorted_x = x.index_select(0, order // k_top)
                counts = torch.bincount(flat_idx, minlength=n_routed)
                used_grouped = False
                if moe._grouped_mm_supported and (
                    (x.is_cuda and x.dtype == torch.bfloat16) or moe._force_grouped_mm_for_test
                ):
                    try:
                        offs = counts.cumsum(dim=0).to(torch.int32)
                        if s1c_fused_gate_up:
                            gu = torch._grouped_mm(sorted_x, moe.w_gate_up_nk.transpose(1, 2), offs=offs)
                            gate, up = gu.split(inter, dim=-1)
                            counters.s1c_routed_fused_op_calls += 1
                        else:
                            gate = torch._grouped_mm(sorted_x, moe.w_gate_nk.transpose(1, 2), offs=offs)
                            up = torch._grouped_mm(sorted_x, moe.w_up_nk.transpose(1, 2), offs=offs)
                            counters.s1c_routed_unfused_op_calls += 1
                        act = act_fn(gate) * up
                        sorted_out = torch._grouped_mm(act, moe.w_down_nk.transpose(1, 2), offs=offs)
                        used_grouped = True
                        moe.prefill_grouped_mm_calls += 1
                        counters.s1a_prefill_grouped_mm_calls += 1
                        counters.per_layer_prefill_grouped_mm[layer_idx] += 1
                    except (RuntimeError, NotImplementedError):
                        moe._grouped_mm_supported = False
                if not used_grouped:
                    moe.prefill_fallback_calls += 1
                    counters.s1a_prefill_fallback_calls += 1
                    counters.per_layer_prefill_fallback[layer_idx] += 1
                    counts_cpu = counts.cpu().tolist()
                    pieces = []
                    cur = 0
                    for ei, cnt in enumerate(counts_cpu):
                        if cnt == 0:
                            continue
                        seg = sorted_x[cur : cur + cnt]
                        if s1c_fused_gate_up:
                            counters.s1c_routed_fused_op_calls += 1
                            gu = F.linear(seg, moe.w_gate_up_nk[ei])
                            gate, up = gu.split(inter, dim=-1)
                        else:
                            counters.s1c_routed_unfused_op_calls += 1
                            gate = F.linear(seg, moe.w_gate_nk[ei])
                            up = F.linear(seg, moe.w_up_nk[ei])
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
            else:
                counters.s1a_prefill_linear_loop_calls += 1
                counters.per_layer_prefill_linear_loop[layer_idx] += 1
                cnts = topk_idx.new_zeros((topk_idx.shape[0], n_routed))
                cnts.scatter_(1, topk_idx, 1)
                tokens_per_expert = cnts.sum(dim=0)
                idxs = topk_idx.view(-1).argsort()
                sorted_tokens = x[idxs // k_top]
                tokens_per_expert_np = tokens_per_expert.cpu().numpy()
                outputs = []
                start_idx = 0
                for ei, num_tokens in enumerate(tokens_per_expert_np):
                    end_idx = start_idx + num_tokens
                    if num_tokens == 0:
                        continue
                    seg = sorted_tokens[start_idx:end_idx]
                    if s1c_fused_gate_up:
                        counters.s1c_routed_fused_op_calls += 1
                        gu = F.linear(seg, moe.w_gate_up_nk[ei])
                        gate, up = gu.split(inter, dim=-1)
                    else:
                        counters.s1c_routed_unfused_op_calls += 1
                        gate = F.linear(seg, moe.w_gate_nk[ei])
                        up = F.linear(seg, moe.w_up_nk[ei])
                    outputs.append(F.linear(act_fn(gate) * up, moe.w_down_nk[ei]))
                    counters.s1a_prefill_linear_expert_calls += 1
                    start_idx = end_idx
                outs = torch.cat(outputs, dim=0) if len(outputs) else sorted_tokens.new_empty(0)
                new_x = torch.empty_like(outs)
                new_x[idxs] = outs
                routed = (
                    new_x.view(*topk_idx.shape, -1)
                    .type(topk_weight.dtype)
                    .mul_(topk_weight.unsqueeze(dim=-1))
                    .sum(dim=1)
                    .type(new_x.dtype)
                )

        if has_shared:
            if s1c_fused_gate_up:
                counters.s1c_shared_fused_calls += 1
                s_gu = F.linear(x, moe.sh_gate_up)
                s_gate, s_up = s_gu.split(sh_inter, dim=-1)
                routed = routed + F.linear(act_fn(s_gate) * s_up, sh_dn)
                return routed.view(*orig_shape)
            counters.s1c_shared_unfused_calls += 1
            return routed.view(*orig_shape) + moe.shared_experts(identity)
        return routed.view(*orig_shape)

    moe.forward = orthogonal_moe_forward


def gpu_no_repeat_ngram(logits, gen_buf, cur_len: int, ngram_size: int, window_size: int, whitelist_gpu=None):
    """Duplicate-safe, sync-free device 1D n-gram repeat blocker matching _uocr_no_repeat_ngram."""
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
    """Sync-free device PageCountGuard matching modeling_unlimitedocr._uocr_page_count_guard."""
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


def ablation_generate(
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
    switch_cfg: SwitchConfig,
    counters: SwitchActivationCounters,
    max_new_tokens: int,
    max_length: int,
    temperature: float,
    page_count_guard: bool,
    max_page_tokens: int,
    ngram_size: int,
    ngram_window: int,
    ngram_whitelist,
    dash_topm: int,
    stream: bool,
):
    """Orthogonal generation loop implementing S0 (streamer), S2 (cache), and S3 (burst=8 vs single-step)."""
    import torch
    from transformers.cache_utils import DynamicCache

    if temperature and temperature > 0:
        raise ValueError("WP-0017 AblationEngine supports deterministic greedy decoding (temperature == 0.0) only")

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

    # S0: when no_text_streamer is False and stream is True, instantiate exact upstream TextStreamer.
    use_streamer = (not switch_cfg.no_text_streamer) and bool(stream)
    streamer = uocr_mod.TextStreamer(tokenizer, skip_prompt=False, skip_special_tokens=False) if use_streamer else None

    t0 = time.perf_counter()
    marks = {"generate_start": clock()}
    gen: list[int] = []
    finish = "length"
    executed_forwards = 0
    burst_extra_forwards = 0
    cache_reallocs = 0
    cache_telemetry: dict[str, object] = {}

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
        if switch_cfg.gather_sparse_decode:
            cache = static_cache_cls(
                out.past_key_values,
                model_lm.model,
                init_cap=max(4096, s_prefill + 2048),
                max_cap=s_prefill + max_tokens_eff + 32,
                act_clamp=dsv2_mod._ACT_CLAMP,
            )
        else:
            cache = out.past_key_values

        if max_tokens_eff > 0:
            if not switch_cfg.gpu_burst_stride_8:
                guard_st = {"marker_cum": 0, "scanned": 0, "page_len": 0}
                wl_set = set(ngram_whitelist or [])
                for step in range(max_tokens_eff):
                    counters.s3_single_step_iters += 1
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
                    if streamer is not None:
                        streamer.put(torch.tensor([nxt]))
                        counters.s0_streamer_put_calls += 1
                    else:
                        counters.s0_silent_accum_tokens += 1
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
                if ngram_size > 0:
                    logits0 = gpu_no_repeat_ngram(logits0, gen_buf, 0, ngram_size, ngram_window, wl_gpu)
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
                    if streamer is not None:
                        streamer.put(torch.tensor([nxt0]))
                        counters.s0_streamer_put_calls += 1
                    else:
                        counters.s0_silent_accum_tokens += 1
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

                    stride = 8
                    while cur < max_tokens_eff:
                        b = min(stride, max_tokens_eff - cur)
                        counters.s3_burst_chunks += 1
                        for k in range(b):
                            s_idx = cur + k
                            counters.s3_burst_steps_launched += 1
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
                            accepted = chunk[:cut]
                            gen.extend(accepted)
                            if streamer is not None:
                                for tid in accepted:
                                    streamer.put(torch.tensor([tid]))
                                    counters.s0_streamer_put_calls += 1
                            else:
                                counters.s0_silent_accum_tokens += len(accepted)
                            last_needed_fwd_step = cur + cut - 1
                            last_ran_fwd_step = min(cur + b - 1, max_tokens_eff - 2)
                            burst_extra_forwards = max(0, last_ran_fwd_step - last_needed_fwd_step)
                            counters.s3_burst_extra_forwards += burst_extra_forwards
                            finish = "stop"
                            break
                        gen.extend(chunk)
                        if streamer is not None:
                            for tid in chunk:
                                streamer.put(torch.tensor([tid]))
                                counters.s0_streamer_put_calls += 1
                        else:
                            counters.s0_silent_accum_tokens += len(chunk)
                        cur += b

        if switch_cfg.gather_sparse_decode and hasattr(cache, "capacity_telemetry"):
            cache_telemetry = cache.capacity_telemetry()
            cache_reallocs = int(cache.reallocations)
        else:
            seq_final = int(cache.get_seq_length(0)) if hasattr(cache, "get_seq_length") else s_prefill + len(gen)
            cache_telemetry = {
                "cache_type": "DynamicCache",
                "prefill_seq_len": int(s_prefill),
                "peak_seq_len": seq_final,
                "reallocations": None,
                "num_layers": len(model_lm.model.layers),
            }
        counters.s2_last_cache_telemetry = cache_telemetry
    finally:
        dsv2_mod.configure_dash_inference(model_lm.model, False, state=dash_state)
        cfg._ring_window, cfg.sliding_window = saved_cfg
        if streamer is not None:
            streamer.end()
            counters.s0_streamer_end_calls += 1
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
        "cache_telemetry": cache_telemetry,
    }


def resolve_model_modules(model):
    uocr_mod = sys.modules[type(model).__module__]
    dsv2_mod = sys.modules[uocr_mod.configure_dash_inference.__module__]
    base_mod = dsv2_mod._base
    dash_mod = sys.modules[dsv2_mod.DashAttention.__module__]
    return uocr_mod, dsv2_mod, base_mod, dash_mod


def apply_ablation_patches(model_lm, *, switch_cfg: SwitchConfig) -> tuple[SwitchActivationCounters, type | None]:
    """Patch a loaded UnlimitedOCRForCausalLM instance in memory for the 6-bit SwitchConfig."""
    uocr_mod, dsv2_mod, _, _ = resolve_model_modules(model_lm)
    counters = SwitchActivationCounters(num_layers=len(model_lm.model.layers))
    static_cache_cls = build_static_dash_cache_cls() if switch_cfg.gather_sparse_decode else None

    for li, layer in enumerate(model_lm.model.layers):
        if hasattr(layer.mlp, "experts"):
            patch_moe_layer_s1(
                layer.mlp,
                layer_idx=li,
                s1a_grouped_prefill=switch_cfg.packed_moe_prefill,
                s1b_decode_bmm=switch_cfg.packed_moe_decode_bmm,
                s1c_fused_gate_up=switch_cfg.fused_gate_up_proj,
                counters=counters,
            )
        elif hasattr(layer.mlp, "gate_proj"):
            patch_dense_mlp_s1c(layer.mlp, fused=switch_cfg.fused_gate_up_proj, counters=counters)

    gc.collect()
    torch_mod = sys.modules.get("torch")
    if torch_mod is not None and model_lm.lm_head.weight.is_cuda:
        torch_mod.cuda.empty_cache()

    for layer in model_lm.model.layers:
        attn = layer.self_attn
        orig_fwd = attn.forward

        if switch_cfg.gather_sparse_decode:

            def make_gather_attn_fwd(_attn, _orig):
                def _wrapped_gather_attn_fwd(*args, **kwargs):
                    hs = kwargs["hidden_states"] if "hidden_states" in kwargs else args[0]
                    pkv = kwargs.get("past_key_value", args[3] if len(args) > 3 else kwargs.get("past_key_values"))
                    pos = kwargs.get("position_ids", args[2] if len(args) > 2 else None)
                    if (
                        hs.shape[1] == 1
                        and dsv2_mod._INFER["on"]
                        and isinstance(pkv, static_cache_cls)
                        and getattr(_attn, "dash_router", None) is not None
                    ):
                        counters.s2_static_gather_decode_calls += 1
                        return gather_sparse_decode_step(_attn, hs, pos, pkv, dsv2_mod)
                    return _orig(*args, **kwargs)

                return _wrapped_gather_attn_fwd

            attn.forward = make_gather_attn_fwd(attn, orig_fwd)
        else:

            def make_dynamic_attn_fwd(_attn, _orig):
                def _wrapped_dynamic_attn_fwd(*args, **kwargs):
                    hs = kwargs["hidden_states"] if "hidden_states" in kwargs else args[0]
                    pkv = kwargs.get("past_key_value", args[3] if len(args) > 3 else kwargs.get("past_key_values"))
                    if (
                        hs.shape[1] == 1
                        and dsv2_mod._INFER["on"]
                        and pkv is not None
                        and _attn.layer_idx in getattr(pkv, "_dash_idx_k", {})
                    ):
                        counters.s2_dynamic_masked_decode_calls += 1
                    return _orig(*args, **kwargs)

                return _wrapped_dynamic_attn_fwd

            attn.forward = make_dynamic_attn_fwd(attn, orig_fwd)

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
        return ablation_generate(
            model_lm,
            tokenizer,
            input_ids,
            imgs,
            seq_mask,
            spatial,
            uocr_mod=uocr_mod,
            dsv2_mod=dsv2_mod,
            static_cache_cls=static_cache_cls,
            switch_cfg=switch_cfg,
            counters=counters,
            max_new_tokens=max_new_tokens,
            max_length=max_length,
            temperature=temperature,
            page_count_guard=page_count_guard,
            max_page_tokens=max_page_tokens,
            ngram_size=ngram_size,
            ngram_window=ngram_window,
            ngram_whitelist=ngram_whitelist,
            dash_topm=dash_topm,
            stream=stream,
        )

    model_lm._uocr_generate = patched_uocr_generate
    return counters, static_cache_cls
