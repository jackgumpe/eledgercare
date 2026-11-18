"""Serial-decode teacher-forced BPE span-logit probe and structural field locator for WP-0017.

Key invariants:
  1. Never uses a prompt-prefill shortcut: prompt prefill runs on visual/text prompt tokens only,
     and every generated prefix token + competing identifier token executes 1-by-1 (q_len == 1)
     through the active configuration's decode attention, KV cache, page2d RoPE, and MoE path.
  2. Structural field locators are frozen on the anchored native stream (<PAGE> index, <BLOCK>
     ordinal, fixed label prefix) and never search new emissions for competing target strings.
  3. Casts logits to FP32 across the full vocabulary before torch.log_softmax, recording both
     effective post-guard logits (ngram + PageCountGuard) and raw pre-guard lm_head logits,
     top-5 candidates, explicit ranks/logits of both competing branch tokens even below rank 5,
     top-1 minus top-2 margin, tie status, and early coordinate divergence (token 7 on 037).

No torch or CUDA module is imported at module import time.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from time import perf_counter_ns as clock

PAGE_TOKEN_ID = 128827
BLOCK_TOKEN_ID = 128828
FORK_TOKEN_ID = 128829
OFFLINE_MARGIN_FLAG_THRESHOLD = 0.125


def token_ids_sha256(token_ids: list[int]) -> str:
    payload = json.dumps([int(x) for x in token_ids], separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _decode_tokens(tokenizer, ids: list[int]) -> str:
    if not ids:
        return ""
    return tokenizer.decode([int(t) for t in ids], skip_special_tokens=False)


def _encode_no_special(tokenizer, text: str) -> list[int]:
    res = tokenizer.encode(text, add_special_tokens=False)
    if hasattr(res, "ids"):
        return [int(x) for x in res.ids]
    return [int(x) for x in res]


def _split_pages(token_ids: list[int], page_token_id: int = PAGE_TOKEN_ID) -> list[tuple[int, int]]:
    """Return [(start_idx, end_idx), ...] in window token_ids for each <PAGE> segment."""
    starts = [i for i, t in enumerate(token_ids) if int(t) == page_token_id]
    return [
        (starts[idx], starts[idx + 1] if idx + 1 < len(starts) else len(token_ids))
        for idx in range(len(starts))
    ]


def _split_blocks_in_slice(
    token_ids: list[int],
    slice_start: int,
    slice_end: int,
    block_token_id: int = BLOCK_TOKEN_ID,
    fork_token_id: int = FORK_TOKEN_ID,
) -> list[dict]:
    """Locate <BLOCK>...<FORK><body> segments inside token_ids[slice_start:slice_end]."""
    blk_starts = [i for i in range(slice_start, slice_end) if int(token_ids[i]) == block_token_id]
    blocks: list[dict] = []
    for b_ord, b_start in enumerate(blk_starts):
        b_end = blk_starts[b_ord + 1] if b_ord + 1 < len(blk_starts) else slice_end
        fork_pos = None
        for j in range(b_start + 1, b_end):
            if int(token_ids[j]) == fork_token_id:
                fork_pos = j
                break
        blocks.append(
            {
                "block_ordinal_0based": b_ord,
                "block_start": b_start,
                "fork_index": fork_pos,
                "body_start": (fork_pos + 1) if fork_pos is not None else None,
                "body_end": b_end,
            }
        )
    return blocks


def build_frozen_field_locator(
    *,
    first_page: int,
    identifier_page: int,
    alternatives: list[str],
    native_token_ids: list[int],
    carbon_token_ids: list[int] | None,
    tokenizer,
    page_token_id: int = PAGE_TOKEN_ID,
    block_token_id: int = BLOCK_TOKEN_ID,
    fork_token_id: int = FORK_TOKEN_ID,
) -> dict:
    """Freeze a unique structural field locator from the anchored native token history."""
    if len(alternatives) != 2:
        raise ValueError(f"Expected exactly 2 competing alternatives [native_id, carbon_id], got {alternatives!r}")
    native_alt, carbon_alt = str(alternatives[0]), str(alternatives[1])
    page_offset = int(identifier_page) - int(first_page)
    pages = _split_pages(native_token_ids, page_token_id=page_token_id)
    if not (0 <= page_offset < len(pages)):
        raise ValueError(f"identifier_page={identifier_page} out of range for first_page={first_page} ({len(pages)} pages)")

    p_start, p_end = pages[page_offset]
    blocks = _split_blocks_in_slice(
        native_token_ids, p_start, p_end, block_token_id=block_token_id, fork_token_id=fork_token_id
    )

    hits = []
    for blk in blocks:
        if blk["body_start"] is None:
            continue
        body_ids = native_token_ids[blk["body_start"] : blk["body_end"]]
        body_text = _decode_tokens(tokenizer, body_ids)
        pos = body_text.find(native_alt)
        if pos != -1:
            hits.append((blk, body_ids, body_text, pos))
    if len(hits) != 1:
        raise ValueError(
            f"Expected unique native anchor block containing {native_alt!r} on page {identifier_page}, found {len(hits)}"
        )

    blk, body_ids, body_text, char_pos = hits[0]
    preceding_label = body_text[:char_pos]
    after_alt = body_text[char_pos + len(native_alt) :]
    delimiter = "\n" if after_alt.startswith("\n") else (after_alt[:1] or "")
    has_leading_space = preceding_label.endswith(" ")
    preceding_label_pre_space = preceding_label[:-1] if has_leading_space else preceding_label

    # Walk body_ids from body_start to find exact token boundary right at preceding_label_pre_space.
    pre_space_body_len = None
    for m in range(len(body_ids) + 1):
        dec = _decode_tokens(tokenizer, body_ids[:m])
        if dec == preceding_label_pre_space:
            pre_space_body_len = m
            break
    if pre_space_body_len is None:
        raise ValueError(
            f"Could not find exact pre-space token boundary for {preceding_label_pre_space!r} in {body_text!r}"
        )

    prefix_end = int(blk["body_start"]) + int(pre_space_body_len)
    native_prefix_tokens = [int(t) for t in native_token_ids[:prefix_end]]

    early_divergence = None
    if carbon_token_ids is not None:
        limit = min(len(native_token_ids), len(carbon_token_ids), prefix_end)
        for idx in range(limit):
            if int(native_token_ids[idx]) != int(carbon_token_ids[idx]):
                early_divergence = {
                    "step_index": idx,
                    "native_token_id": int(native_token_ids[idx]),
                    "native_token_piece": _decode_tokens(tokenizer, [int(native_token_ids[idx])]),
                    "carbon_token_id": int(carbon_token_ids[idx]),
                    "carbon_token_piece": _decode_tokens(tokenizer, [int(carbon_token_ids[idx])]),
                }
                break

    spans = resolve_competing_spans(
        preceding_label=preceding_label,
        preceding_label_pre_space=preceding_label_pre_space,
        alternatives=[native_alt, carbon_alt],
        tokenizer=tokenizer,
        expected_pre_space_label_ids=[int(t) for t in body_ids[:pre_space_body_len]],
    )

    return {
        "window_label": f"{int(first_page):03d}",
        "first_page": int(first_page),
        "identifier_page": int(identifier_page),
        "page_offset_0based": page_offset,
        "block_ordinal_0based": int(blk["block_ordinal_0based"]),
        "line_ordinal_1based": int(blk["block_ordinal_0based"]) + 1,
        "preceding_label": preceding_label,
        "preceding_label_pre_space": preceding_label_pre_space,
        "has_leading_space": has_leading_space,
        "delimiter": delimiter,
        "char_offset_in_block_body": int(char_pos),
        "byte_offset_in_block_body": len(preceding_label.encode("utf-8")),
        "alternatives": [native_alt, carbon_alt],
        "native_prefix_end_index": prefix_end,
        "native_prefix_tokens": native_prefix_tokens,
        "native_prefix_sha256": token_ids_sha256(native_prefix_tokens),
        "early_pre_id_divergence": early_divergence,
        "competing_spans": spans,
    }


def resolve_competing_spans(
    *,
    preceding_label: str,
    preceding_label_pre_space: str,
    alternatives: list[str],
    tokenizer,
    expected_pre_space_label_ids: list[int] | None = None,
) -> dict:
    """Tokenize competing identifiers in context and extract pre-space & common-boundary spans."""
    pre_ids = _encode_no_special(tokenizer, preceding_label_pre_space) if preceding_label_pre_space else []
    if expected_pre_space_label_ids is not None and pre_ids != list(expected_pre_space_label_ids):
        raise ValueError(
            f"Context BPE mismatch on {preceding_label_pre_space!r}: got {pre_ids} vs {expected_pre_space_label_ids}"
        )

    pre_space_spans: list[list[int]] = []
    for alt in alternatives:
        full_ids = _encode_no_special(tokenizer, preceding_label + alt)
        if full_ids[: len(pre_ids)] != pre_ids:
            raise ValueError(
                f"Alternative {alt!r} mutated BPE tokenization before pre-space boundary: {full_ids} vs {pre_ids}"
            )
        pre_space_spans.append(full_ids[len(pre_ids) :])

    s0, s1 = pre_space_spans[0], pre_space_spans[1]
    lcp_len = 0
    while lcp_len < min(len(s0), len(s1)) and s0[lcp_len] == s1[lcp_len]:
        lcp_len += 1

    shared_post_label_ids = s0[:lcp_len]
    entries = []
    for idx, (alt, span_ids) in enumerate(zip(alternatives, pre_space_spans)):
        div_ids = span_ids[lcp_len:]
        entries.append(
            {
                "role": "native_id" if idx == 0 else "carbon_id",
                "identifier": alt,
                "text_from_pre_space": (" " + alt) if preceding_label != preceding_label_pre_space else alt,
                "pre_space_token_ids": span_ids,
                "pre_space_token_pieces": [_decode_tokens(tokenizer, [t]) for t in span_ids],
                "common_boundary_token_ids": div_ids,
                "common_boundary_token_pieces": [_decode_tokens(tokenizer, [t]) for t in div_ids],
            }
        )

    return {
        "shared_post_label_token_ids": shared_post_label_ids,
        "shared_post_label_pieces": [_decode_tokens(tokenizer, [t]) for t in shared_post_label_ids],
        "lcp_offset_from_pre_space": lcp_len,
        "entries": entries,
    }


def extract_free_field_at_locator(
    emitted_token_ids: list[int],
    tokenizer,
    locator: dict,
    *,
    native_window_token_ids: list[int] | None = None,
    page_token_id: int = PAGE_TOKEN_ID,
    block_token_id: int = BLOCK_TOKEN_ID,
    fork_token_id: int = FORK_TOKEN_ID,
) -> dict:
    """Extract observed free-run identifier and prefix at the frozen structural locator without value search."""
    pages = _split_pages(emitted_token_ids, page_token_id=page_token_id)
    page_offset = int(locator["page_offset_0based"])
    if not (0 <= page_offset < len(pages)):
        return {
            "aligned": False,
            "failure_reason": f"missing_page_offset_{page_offset}_in_{len(pages)}_pages",
            "observed_id": None,
            "free_prefix_tokens": None,
            "free_prefix_sha256": None,
        }

    p_start, p_end = pages[page_offset]
    blocks = _split_blocks_in_slice(
        emitted_token_ids, p_start, p_end, block_token_id=block_token_id, fork_token_id=fork_token_id
    )
    blk_ord = int(locator["block_ordinal_0based"])
    if not (0 <= blk_ord < len(blocks)):
        return {
            "aligned": False,
            "failure_reason": f"missing_block_ordinal_{blk_ord}_in_{len(blocks)}_blocks",
            "observed_id": None,
            "free_prefix_tokens": None,
            "free_prefix_sha256": None,
        }

    blk = blocks[blk_ord]
    if blk["body_start"] is None:
        return {
            "aligned": False,
            "failure_reason": "malformed_block_missing_fork",
            "observed_id": None,
            "free_prefix_tokens": None,
            "free_prefix_sha256": None,
        }

    body_ids = [int(t) for t in emitted_token_ids[blk["body_start"] : blk["body_end"]]]
    body_text = _decode_tokens(tokenizer, body_ids)
    preceding_label = str(locator["preceding_label"])
    preceding_pre_space = str(locator["preceding_label_pre_space"])

    if not body_text.startswith(preceding_label):
        return {
            "aligned": False,
            "failure_reason": "preceding_label_mismatch",
            "observed_body_preview": body_text[:80],
            "observed_id": None,
            "free_prefix_tokens": None,
            "free_prefix_sha256": None,
        }

    remainder = body_text[len(preceding_label) :]
    delim = str(locator["delimiter"])
    if delim and delim in remainder:
        observed_id = remainder.split(delim, 1)[0].rstrip("\r")
    else:
        observed_id = remainder.splitlines()[0].rstrip("\r") if remainder else ""

    pre_space_len = None
    for m in range(len(body_ids) + 1):
        if _decode_tokens(tokenizer, body_ids[:m]) == preceding_pre_space:
            pre_space_len = m
            break

    if pre_space_len is None:
        return {
            "aligned": False,
            "failure_reason": "missing_pre_space_token_boundary",
            "observed_id": observed_id or None,
            "free_prefix_tokens": None,
            "free_prefix_sha256": None,
        }

    free_prefix_end = int(blk["body_start"]) + int(pre_space_len)
    free_prefix_tokens = [int(t) for t in emitted_token_ids[:free_prefix_end]]
    free_body_tail = [int(t) for t in emitted_token_ids[free_prefix_end : blk["body_end"]]]
    nat_prefix = locator["native_prefix_tokens"]

    first_prefix_diff = None
    for idx in range(min(len(free_prefix_tokens), len(nat_prefix))):
        if free_prefix_tokens[idx] != nat_prefix[idx]:
            first_prefix_diff = {
                "step_index": idx,
                "free_token_id": int(free_prefix_tokens[idx]),
                "free_token_piece": _decode_tokens(tokenizer, [int(free_prefix_tokens[idx])]),
                "native_token_id": int(nat_prefix[idx]),
                "native_token_piece": _decode_tokens(tokenizer, [int(nat_prefix[idx])]),
            }
            break
    if first_prefix_diff is None and len(free_prefix_tokens) != len(nat_prefix):
        first_prefix_diff = {
            "step_index": min(len(free_prefix_tokens), len(nat_prefix)),
            "length_mismatch": [len(free_prefix_tokens), len(nat_prefix)],
        }

    changed_positions = sum(
        1 for a, b in zip(free_prefix_tokens, nat_prefix) if a != b
    ) + abs(len(free_prefix_tokens) - len(nat_prefix))

    first_window_diff = None
    if native_window_token_ids is not None:
        for idx in range(min(len(emitted_token_ids), len(native_window_token_ids))):
            if int(emitted_token_ids[idx]) != int(native_window_token_ids[idx]):
                first_window_diff = idx
                break
        if first_window_diff is None and len(emitted_token_ids) != len(native_window_token_ids):
            first_window_diff = min(len(emitted_token_ids), len(native_window_token_ids))

    # Check whether free_body_tail begins with the exact pre-space tokens of one of the probed alternatives.
    matched_alt_role = None
    for entry in locator["competing_spans"]["entries"]:
        ps_ids = entry["pre_space_token_ids"]
        if free_body_tail[: len(ps_ids)] == ps_ids and observed_id == entry["identifier"]:
            matched_alt_role = entry["role"]
            break

    return {
        "aligned": bool(observed_id),
        "failure_reason": None if observed_id else "empty_field_value",
        "observed_id": observed_id if observed_id else None,
        "matches_native_id": (observed_id == locator["alternatives"][0]),
        "matches_carbon_id": (observed_id == locator["alternatives"][1]),
        "matched_probed_branch_role": matched_alt_role,
        "free_prefix_end_index": free_prefix_end,
        "free_prefix_len": len(free_prefix_tokens),
        "free_prefix_tokens": free_prefix_tokens,
        "free_prefix_sha256": token_ids_sha256(free_prefix_tokens),
        "prefix_identical_to_native": (free_prefix_tokens == nat_prefix),
        "first_prefix_diff_vs_native": first_prefix_diff,
        "prefix_changed_token_positions_vs_native": changed_positions,
        "first_window_diff_vs_native": first_window_diff,
    }


def clone_kv_cache(cache):
    """Deep-clone either DynamicCache or StaticDashCache (including _dash_idx_k, _page_rope_state, _uocr_pg)."""
    from transformers.cache_utils import DynamicCache

    if isinstance(cache, DynamicCache):
        out = DynamicCache()
        if hasattr(cache, "_seen_tokens"):
            out._seen_tokens = int(cache._seen_tokens)
        if hasattr(cache, "key_cache"):
            out.key_cache = [t.clone() for t in cache.key_cache]
            out.value_cache = [t.clone() for t in cache.value_cache]
        elif hasattr(cache, "layers"):
            for li, lyr in enumerate(cache.layers):
                out.update(lyr.keys.clone(), lyr.values.clone(), li)
        if hasattr(cache, "_dash_idx_k"):
            out._dash_idx_k = {li: v.clone() for li, v in cache._dash_idx_k.items()}
        if hasattr(cache, "_page_rope_state"):
            out._page_rope_state = {
                li: {k: (v.clone() if hasattr(v, "clone") else v) for k, v in st.items()}
                for li, st in cache._page_rope_state.items()
            }
        if hasattr(cache, "_uocr_pg"):
            out._uocr_pg = {
                k: (v.clone() if hasattr(v, "clone") else v) for k, v in cache._uocr_pg.items()
            }
        return out

    # StaticDashCache (either WP-0017 switches.StaticDashCache or WP-0015 engine.StaticDashCache)
    cls = type(cache)
    out = cls.__new__(cls)
    for scalar_attr in (
        "num_layers",
        "bsz",
        "num_kv_heads",
        "head_dim",
        "dtype",
        "device",
        "prefill_seq_len",
        "requested_init_cap",
        "max_cap",
        "block_size",
        "local_window",
        "routed_topk_blocks",
        "index_dim",
        "act_clamp",
        "inv_sqrt_idx_d",
        "init_cap_tok",
        "cap_tok",
        "cap_blk",
        "peak_seq_len",
        "reallocations",
        "decode_layer_appends",
    ):
        if hasattr(cache, scalar_attr):
            setattr(out, scalar_attr, getattr(cache, scalar_attr))
    out._blk_arange = cache._blk_arange.clone()
    out._local_arange = cache._local_arange.clone()
    out.seq_lens = list(cache.seq_lens)
    out.k_buf = [t.clone() for t in cache.k_buf]
    out.v_buf = [t.clone() for t in cache.v_buf]
    out._dash_idx_k = {li: v.clone() for li, v in cache._dash_idx_k.items()}
    out.k_bar_buf = [t.clone() for t in cache.k_bar_buf]
    if hasattr(cache, "_page_rope_state"):
        out._page_rope_state = {
            li: {k: (v.clone() if hasattr(v, "clone") else v) for k, v in st.items()}
            for li, st in cache._page_rope_state.items()
        }
    if hasattr(cache, "_uocr_pg"):
        out._uocr_pg = {
            k: (v.clone() if hasattr(v, "clone") else v) for k, v in cache._uocr_pg.items()
        }
    return out


def apply_pure_host_guards(
    raw_logits_fp32,
    gen_history: list[int],
    *,
    uocr_mod,
    expected_pages: int,
    page_id: int,
    eos_id: int,
    max_page_tokens: int,
    ngram_size: int,
    ngram_window: int,
    whitelist: set[int],
):
    """Apply exact upstream _uocr_no_repeat_ngram and _uocr_page_count_guard on a cloned FP32 logit vector."""
    import torch

    after_ngram = raw_logits_fp32.clone()
    if ngram_size > 0:
        uocr_mod._uocr_no_repeat_ngram(after_ngram, gen_history, ngram_size, ngram_window, whitelist)
    ngram_banned_mask = torch.isfinite(raw_logits_fp32) & ~torch.isfinite(after_ngram)
    ngram_banned_ids = [int(i) for i in torch.nonzero(ngram_banned_mask, as_tuple=False).view(-1).tolist()]

    guarded = after_ngram.clone()
    guard_st = {"marker_cum": 0, "scanned": 0, "page_len": 0}
    if expected_pages > 0:
        uocr_mod._uocr_page_count_guard(
            guarded, gen_history, expected_pages, page_id, eos_id, max_page_tokens, guard_st
        )
    pg_banned_mask = torch.isfinite(after_ngram) & ~torch.isfinite(guarded)
    pg_banned_count = int(pg_banned_mask.sum().item())
    eos_banned_by_page_guard = bool(
        torch.isfinite(after_ngram[eos_id]).item() and not torch.isfinite(guarded[eos_id]).item()
    )

    return guarded, {
        "marker_cum": int(guard_st["marker_cum"]),
        "page_len": int(guard_st["page_len"]),
        "ngram_banned_ids": ngram_banned_ids,
        "page_guard_banned_count": pg_banned_count,
        "eos_banned_by_page_guard": eos_banned_by_page_guard,
        "any_logit_modified_by_guards": bool(len(ngram_banned_ids) > 0 or pg_banned_count > 0),
    }


def summarize_logit_step(
    raw_logits_fp32,
    guarded_logits_fp32,
    guard_meta: dict,
    *,
    tokenizer,
    target_token_id: int,
    competing_token_ids: list[int] | None = None,
) -> dict:
    """Compute full-vocab FP32 log_softmax, top-5, margin, tie status, and competing candidate ranks."""
    import torch

    logp_raw = torch.log_softmax(raw_logits_fp32, dim=-1)
    logp_grd = torch.log_softmax(guarded_logits_fp32, dim=-1)

    def _pack_dist(logits_1d, logp_1d) -> dict:
        k = min(5, int(logits_1d.shape[0]))
        vals, idxs = torch.topk(logits_1d, k=k, dim=-1, largest=True, sorted=True)
        top5 = [
            {
                "rank": r + 1,
                "token_id": int(tid),
                "piece": _decode_tokens(tokenizer, [int(tid)]),
                "logit_fp32": float(val),
                "logprob_fp32": float(logp_1d[int(tid)].item()),
            }
            for r, (val, tid) in enumerate(zip(vals.tolist(), idxs.tolist()))
        ]
        margin = float((vals[0] - vals[1]).item()) if k >= 2 else None
        tie_top1 = bool(vals[0].item() == vals[1].item()) if k >= 2 else False
        greedy_id = int(torch.argmax(logits_1d).item())

        tgt_logit = float(logits_1d[target_token_id].item())
        tgt_finite = math.isfinite(tgt_logit)
        tgt_logprob = float(logp_1d[target_token_id].item()) if tgt_finite else None

        competing = None
        if competing_token_ids:
            competing = []
            for cid in competing_token_ids:
                cid_int = int(cid)
                c_logit = float(logits_1d[cid_int].item())
                c_finite = math.isfinite(c_logit)
                strictly_higher = int((logits_1d > c_logit).sum().item()) if c_finite else int(torch.isfinite(logits_1d).sum().item())
                tie_smaller_id = (
                    int((logits_1d[:cid_int] == c_logit).sum().item()) if (c_finite and cid_int > 0) else 0
                )
                competing.append(
                    {
                        "token_id": cid_int,
                        "piece": _decode_tokens(tokenizer, [cid_int]),
                        "is_finite": c_finite,
                        "logit_fp32": c_logit if c_finite else None,
                        "logprob_fp32": float(logp_1d[cid_int].item()) if c_finite else None,
                        "strict_higher_count": strictly_higher,
                        "effective_greedy_rank_1based": strictly_higher + tie_smaller_id + 1,
                    }
                )

        return {
            "target_token_id": int(target_token_id),
            "target_piece": _decode_tokens(tokenizer, [int(target_token_id)]),
            "target_is_finite": tgt_finite,
            "target_logit_fp32": tgt_logit if tgt_finite else None,
            "target_logprob_fp32": tgt_logprob,
            "greedy_argmax_token_id": greedy_id,
            "greedy_argmax_piece": _decode_tokens(tokenizer, [greedy_id]),
            "margin_top1_top2_fp32": margin,
            "tie_at_top1": tie_top1,
            "top5": top5,
            "competing_candidates": competing,
        }

    grd_summary = _pack_dist(guarded_logits_fp32, logp_grd)
    raw_summary = _pack_dist(raw_logits_fp32, logp_raw)
    return {
        "guarded": grd_summary,
        "raw": raw_summary,
        "guard_meta": guard_meta,
        "guards_changed_target_logit": (grd_summary["target_logit_fp32"] != raw_summary["target_logit_fp32"]),
        "guards_changed_top1": (grd_summary["greedy_argmax_token_id"] != raw_summary["greedy_argmax_token_id"]),
    }


def _sync_device(device) -> None:
    import torch

    if device.type == "cuda":
        torch.cuda.synchronize(device)


def run_teacher_forced_window_probe(
    *,
    engine_hooks: dict,
    images: list,
    locator: dict,
    prefix_tokens: list[int],
    prefix_label: str,
    call_kwargs: dict,
    prompt_text: str = "Multi page parsing.",
) -> dict:
    """Execute serial 1-token-at-a-time prefix replay and branched identifier span scoring."""
    import torch
    from transformers.cache_utils import DynamicCache

    model_lm = engine_hooks["model"]
    tokenizer = engine_hooks["tokenizer"]
    use_gather_decode = bool(engine_hooks["use_gather_decode"])
    static_cache_cls = engine_hooks["static_cache_cls"]

    uocr_mod = sys.modules[type(model_lm).__module__]
    dsv2_mod = sys.modules[uocr_mod.configure_dash_inference.__module__]

    rgb_images = [im.convert("RGB") if hasattr(im, "convert") else im for im in images]
    n_img = len(rgb_images)
    full_prompt = "<PAGE><image>" * n_img + prompt_text
    input_ids, imgs, seq_mask, spatial = uocr_mod._uocr_build_inputs(
        tokenizer,
        full_prompt,
        rgb_images,
        crop_mode=call_kwargs.get("crop_mode", False),
        base_size=int(call_kwargs.get("base_size", 1024)),
        image_size=int(call_kwargs.get("image_size", 640)),
        max_crops=int(call_kwargs.get("max_crops", 16)),
    )

    device = model_lm.lm_head.weight.device
    ids = input_ids.unsqueeze(0).to(device)
    prompt_ids = input_ids.tolist()
    sp_cfg = getattr(model_lm.config, "sparse_attention_config", None)
    page_id = int((sp_cfg or {}).get("page_token_id", PAGE_TOKEN_ID)) if isinstance(sp_cfg, dict) else PAGE_TOKEN_ID
    eos_id = int(tokenizer.eos_token_id)
    expected_pages = prompt_ids.count(page_id) if bool(call_kwargs.get("page_count_guard", True)) else 0
    max_page_tokens = int(call_kwargs.get("max_page_tokens", 20000))
    ngram_size = int(call_kwargs.get("no_repeat_ngram_size", 35))
    ngram_window = int(call_kwargs.get("ngram_window", 1024 if n_img > 1 else 128))
    wl_set = set(call_kwargs.get("ngram_whitelist_token_ids") or [])
    max_new_tokens = int(call_kwargs.get("max_new_tokens", 8000 * n_img))
    max_length = int(call_kwargs.get("max_length", 131072))
    dash_topm = int(call_kwargs.get("dash_topm", 16))

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

    early_div = locator.get("early_pre_id_divergence")
    early_step_idx = int(early_div["step_index"]) if early_div is not None else None
    early_step_telemetry = None

    try:
        with torch.no_grad():
            dyn_cache = DynamicCache()
            s_prefill = int(ids.shape[1])
            max_tokens_eff = min(max_new_tokens, max(0, max_length - s_prefill))

            _sync_device(device)
            t_pf0 = clock()
            out = model_lm.model(
                input_ids=ids,
                past_key_values=dyn_cache,
                use_cache=True,
                position_ids=torch.arange(s_prefill, device=device)[None],
                return_dict=True,
                **kw,
            )
            if use_gather_decode:
                cache = static_cache_cls(
                    out.past_key_values,
                    model_lm.model,
                    init_cap=max(4096, s_prefill + 2048),
                    max_cap=s_prefill + max_tokens_eff + 32,
                    act_clamp=dsv2_mod._ACT_CLAMP,
                )
            else:
                cache = out.past_key_values
            h = out.last_hidden_state[:, -1:]
            _sync_device(device)
            prefill_ms = (clock() - t_pf0) / 1e6

            # Serial 1-token-at-a-time decode replay through prefix_tokens (q_len == 1 strictly).
            gen_history: list[int] = []
            prefix_forwards = 0
            _sync_device(device)
            t_pre0 = clock()
            for step_idx, forced_tok in enumerate(prefix_tokens):
                if early_step_idx is not None and step_idx == early_step_idx:
                    raw_z = model_lm.lm_head(h).float()[0, -1].clone()
                    grd_z, g_meta = apply_pure_host_guards(
                        raw_z,
                        gen_history,
                        uocr_mod=uocr_mod,
                        expected_pages=expected_pages,
                        page_id=page_id,
                        eos_id=eos_id,
                        max_page_tokens=max_page_tokens,
                        ngram_size=ngram_size,
                        ngram_window=ngram_window,
                        whitelist=wl_set,
                    )
                    early_step_telemetry = {
                        "step_index": step_idx,
                        "replayed_token_id": int(forced_tok),
                        "replayed_piece": _decode_tokens(tokenizer, [int(forced_tok)]),
                        **summarize_logit_step(
                            raw_z,
                            grd_z,
                            g_meta,
                            tokenizer=tokenizer,
                            target_token_id=int(forced_tok),
                            competing_token_ids=[
                                int(early_div["native_token_id"]),
                                int(early_div["carbon_token_id"]),
                            ],
                        ),
                    }
                gen_history.append(int(forced_tok))
                pos = s_prefill + step_idx
                out = model_lm.model(
                    input_ids=torch.tensor([[int(forced_tok)]], dtype=torch.long, device=device),
                    past_key_values=cache,
                    use_cache=True,
                    position_ids=torch.tensor([[pos]], dtype=torch.long, device=device),
                    return_dict=True,
                )
                prefix_forwards += 1
                cache = out.past_key_values
                h = out.last_hidden_state
            _sync_device(device)
            prefix_decode_ms = (clock() - t_pre0) / 1e6

            # Branch at the exact pre-space prefix boundary P = len(prefix_tokens).
            P = len(prefix_tokens)
            span_spec = locator["competing_spans"]
            lcp_len = int(span_spec["lcp_offset_from_pre_space"])
            entries = span_spec["entries"]
            div_competing_ids = [
                int(entries[0]["common_boundary_token_ids"][0]),
                int(entries[1]["common_boundary_token_ids"][0]),
            ]

            branch_results = []
            branch_forwards = 0
            _sync_device(device)
            t_br0 = clock()
            for b_idx, entry in enumerate(entries):
                if b_idx + 1 < len(entries):
                    b_cache = clone_kv_cache(cache)
                    b_h = h.clone()
                else:
                    b_cache = cache
                    b_h = h
                b_gen = list(prefix_tokens)
                span_ids = [int(t) for t in entry["pre_space_token_ids"]]

                step_rows = []
                for k, tok_id in enumerate(span_ids):
                    raw_z = model_lm.lm_head(b_h).float()[0, -1].clone()
                    grd_z, g_meta = apply_pure_host_guards(
                        raw_z,
                        b_gen,
                        uocr_mod=uocr_mod,
                        expected_pages=expected_pages,
                        page_id=page_id,
                        eos_id=eos_id,
                        max_page_tokens=max_page_tokens,
                        ngram_size=ngram_size,
                        ngram_window=ngram_window,
                        whitelist=wl_set,
                    )
                    is_div = (k == lcp_len)
                    step_info = summarize_logit_step(
                        raw_z,
                        grd_z,
                        g_meta,
                        tokenizer=tokenizer,
                        target_token_id=tok_id,
                        competing_token_ids=div_competing_ids if is_div else None,
                    )
                    step_rows.append(
                        {
                            "window_step": P + k,
                            "span_offset": k,
                            "in_common_boundary_suffix": bool(k >= lcp_len),
                            "is_first_divergent_step": is_div,
                            **step_info,
                        }
                    )
                    b_gen.append(tok_id)
                    if k + 1 < len(span_ids):
                        pos = s_prefill + P + k
                        out_b = model_lm.model(
                            input_ids=torch.tensor([[tok_id]], dtype=torch.long, device=device),
                            past_key_values=b_cache,
                            use_cache=True,
                            position_ids=torch.tensor([[pos]], dtype=torch.long, device=device),
                            return_dict=True,
                        )
                        branch_forwards += 1
                        b_cache = out_b.past_key_values
                        b_h = out_b.last_hidden_state

                div_steps = [s for s in step_rows if s["in_common_boundary_suffix"]]
                all_grd_finite = all(s["guarded"]["target_is_finite"] for s in step_rows)
                all_raw_finite = all(s["raw"]["target_is_finite"] for s in step_rows)

                ell_full_grd = (
                    math.fsum(s["guarded"]["target_logprob_fp32"] for s in step_rows) if all_grd_finite else None
                )
                ell_cb_grd = (
                    math.fsum(s["guarded"]["target_logprob_fp32"] for s in div_steps) if all_grd_finite else None
                )
                ell_full_raw = (
                    math.fsum(s["raw"]["target_logprob_fp32"] for s in step_rows) if all_raw_finite else None
                )
                ell_cb_raw = (
                    math.fsum(s["raw"]["target_logprob_fp32"] for s in div_steps) if all_raw_finite else None
                )
                min_margin_grd = min(
                    (s["guarded"]["margin_top1_top2_fp32"] for s in step_rows if s["guarded"]["margin_top1_top2_fp32"] is not None),
                    default=None,
                )
                min_margin_cb_grd = min(
                    (s["guarded"]["margin_top1_top2_fp32"] for s in div_steps if s["guarded"]["margin_top1_top2_fp32"] is not None),
                    default=None,
                )

                branch_results.append(
                    {
                        "role": entry["role"],
                        "identifier": entry["identifier"],
                        "text_from_pre_space": entry["text_from_pre_space"],
                        "pre_space_token_ids": entry["pre_space_token_ids"],
                        "pre_space_token_pieces": entry["pre_space_token_pieces"],
                        "common_boundary_token_ids": entry["common_boundary_token_ids"],
                        "common_boundary_token_pieces": entry["common_boundary_token_pieces"],
                        "all_targets_finite_guarded": all_grd_finite,
                        "all_targets_finite_raw": all_raw_finite,
                        "ell_full_with_space_guarded_nats": ell_full_grd,
                        "ell_common_boundary_guarded_nats": ell_cb_grd,
                        "ell_full_with_space_raw_nats": ell_full_raw,
                        "ell_common_boundary_raw_nats": ell_cb_raw,
                        "min_step_margin_guarded_fp32": min_margin_grd,
                        "min_common_boundary_margin_guarded_fp32": min_margin_cb_grd,
                        "steps": step_rows,
                    }
                )
            _sync_device(device)
            branch_decode_ms = (clock() - t_br0) / 1e6
    finally:
        dsv2_mod.configure_dash_inference(model_lm.model, False, state=dash_state)
        cfg._ring_window, cfg.sliding_window = saved_cfg

    b_nat, b_car = branch_results[0], branch_results[1]
    both_grd_finite = bool(b_nat["all_targets_finite_guarded"] and b_car["all_targets_finite_guarded"])
    both_raw_finite = bool(b_nat["all_targets_finite_raw"] and b_car["all_targets_finite_raw"])

    d_guarded = (
        b_nat["ell_common_boundary_guarded_nats"] - b_car["ell_common_boundary_guarded_nats"]
        if both_grd_finite
        else None
    )
    d_full_space_guarded = (
        b_nat["ell_full_with_space_guarded_nats"] - b_car["ell_full_with_space_guarded_nats"]
        if both_grd_finite
        else None
    )
    d_raw = (
        b_nat["ell_common_boundary_raw_nats"] - b_car["ell_common_boundary_raw_nats"]
        if both_raw_finite
        else None
    )

    div_step_nat = next(s for s in b_nat["steps"] if s["is_first_divergent_step"])
    total_fwd = prefix_forwards + branch_forwards
    total_decode_ms = prefix_decode_ms + branch_decode_ms

    return {
        "prefix_mode": prefix_label,
        "window_label": locator["window_label"],
        "first_page": locator["first_page"],
        "identifier_page": locator["identifier_page"],
        "prompt_token_len": s_prefill,
        "prefix_token_len": P,
        "prefix_sha256": token_ids_sha256(prefix_tokens),
        "serial_single_token_decode_enforced": True,
        "lcp_offset_from_pre_space": lcp_len,
        "divergence_window_step": P + lcp_len,
        "divergence_step_summary": {
            "window_step": div_step_nat["window_step"],
            "guarded_top5": div_step_nat["guarded"]["top5"],
            "guarded_margin_top1_top2_fp32": div_step_nat["guarded"]["margin_top1_top2_fp32"],
            "guarded_tie_at_top1": div_step_nat["guarded"]["tie_at_top1"],
            "guarded_greedy_argmax_token_id": div_step_nat["guarded"]["greedy_argmax_token_id"],
            "guarded_competing_candidates": div_step_nat["guarded"]["competing_candidates"],
            "raw_top5": div_step_nat["raw"]["top5"],
            "raw_margin_top1_top2_fp32": div_step_nat["raw"]["margin_top1_top2_fp32"],
            "raw_competing_candidates": div_step_nat["raw"]["competing_candidates"],
            "guard_meta": div_step_nat["guard_meta"],
        },
        "early_pre_id_divergence_telemetry": early_step_telemetry,
        "both_branches_finite_guarded": both_grd_finite,
        "both_branches_finite_raw": both_raw_finite,
        "D_native_minus_carbon_guarded_nats": d_guarded,
        "D_native_minus_carbon_with_space_guarded_nats": d_full_space_guarded,
        "D_sign_guarded": (1 if d_guarded > 0 else (-1 if d_guarded < 0 else 0)) if d_guarded is not None else None,
        "D_native_minus_carbon_raw_nats": d_raw,
        "guards_differed_from_raw_on_D": (
            bool(abs(d_guarded - d_raw) > 0.0) if (d_guarded is not None and d_raw is not None) else None
        ),
        "probe_timing": {
            "device_synchronized": (device.type == "cuda"),
            "prefill_ms": prefill_ms,
            "prefix_decode_ms": prefix_decode_ms,
            "prefix_forwarded_tokens": prefix_forwards,
            "prefix_decode_ms_per_forwarded_token": (prefix_decode_ms / prefix_forwards) if prefix_forwards > 0 else None,
            "branch_decode_ms": branch_decode_ms,
            "branch_forwarded_tokens": branch_forwards,
            "total_decode_ms": total_decode_ms,
            "total_forwarded_decode_tokens": total_fwd,
            "decode_ms_per_forwarded_token": (total_decode_ms / total_fwd) if total_fwd > 0 else None,
            "denominator_note": (
                "prefill_ms covers prompt visual+text prefill (1 forward) plus StaticDashCache init when S2=True; "
                "total_forwarded_decode_tokens = prefix_forwarded_tokens + branch_forwarded_tokens (all q_len==1); "
                "excludes setup/image-render and ordinary free-run clock."
            ),
        },
        "branches": branch_results,
    }


def evaluate_offline_margin_flag(
    free_extraction: dict,
    free_prefix_probe: dict | None,
    *,
    threshold: float = OFFLINE_MARGIN_FLAG_THRESHOLD,
) -> dict:
    """Offline diagnostic (<0.125 strict top-2 logit gap on aligned free-emitted ID; never alters flagged=False)."""
    if not free_extraction.get("aligned") or not free_extraction.get("observed_id"):
        return {
            "evaluable": False,
            "reason": free_extraction.get("failure_reason") or "unaligned_field",
            "threshold_logits_strict_lt": threshold,
            "min_effective_margin_fp32": None,
            "would_flag_offline": None,
        }
    role = free_extraction.get("matched_probed_branch_role")
    if role is None or free_prefix_probe is None:
        return {
            "evaluable": False,
            "reason": "emitted_id_not_among_probed_free_prefix_branches",
            "observed_id": free_extraction.get("observed_id"),
            "threshold_logits_strict_lt": threshold,
            "min_effective_margin_fp32": None,
            "would_flag_offline": None,
        }
    branch = next((b for b in free_prefix_probe["branches"] if b["role"] == role), None)
    if branch is None or branch["min_common_boundary_margin_guarded_fp32"] is None:
        return {
            "evaluable": False,
            "reason": "missing_branch_margin",
            "threshold_logits_strict_lt": threshold,
            "min_effective_margin_fp32": None,
            "would_flag_offline": None,
        }
    min_m = float(branch["min_common_boundary_margin_guarded_fp32"])
    return {
        "evaluable": True,
        "reason": None,
        "observed_id": free_extraction["observed_id"],
        "matched_branch_role": role,
        "threshold_logits_strict_lt": threshold,
        "min_effective_margin_fp32": min_m,
        "would_flag_offline": bool(min_m < threshold),
        "emitted_prediction_flagged_field_unchanged": False,
    }
