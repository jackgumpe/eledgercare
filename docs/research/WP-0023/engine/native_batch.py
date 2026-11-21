"""WP-0023 frozen-checkpoint research decode. Inputs are equal-length three-page windows."""

import importlib.util
import math
import sys
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel
from transformers.cache_utils import DynamicCache


MAX_NEW_TOKENS = 24000
MAX_LENGTH = 131072
MAX_PAGE_TOKENS = 20000
NGRAM_SIZE = 35
NGRAM_WINDOW = 1024


@dataclass
class Lane:
    prompt: list
    pages: int
    tokens: list = field(default_factory=list)
    guard: dict = field(default_factory=lambda: {"marker_cum": 0, "scanned": 0, "page_len": 0})
    stop: str | None = None
    last_choice: int | None = None
    last_step: int | None = None

    def summary(self, tokenizer, page_id, diagnostic):
        return {
            "prompt_token_ids": self.prompt,
            "token_ids": self.tokens,
            "text": tokenizer.decode(self.tokens, skip_special_tokens=False),
            "expected_pages": self.pages,
            "num_pages_out": self.tokens.count(page_id),
            "finish_reason": "stop" if self.stop == "eos" else ("prefix" if diagnostic and self.stop is None else "length"),
            "stop_cause": self.stop or ("prefix" if diagnostic else "max_new_tokens"),
            "eos_id": int(tokenizer.eos_token_id),
            "eos_observed": self.stop == "eos",
            "last_selected_token": self.last_choice,
            "last_selected_step": self.last_step,
            "last_guard_scan": dict(self.guard),
        }


def _inputs(native, tokenizer, lanes, device, pixel_dtype, page_id):
    ids, images, masks, state = [], [], [], []
    for pages in lanes:
        if len(pages) != 3:
            raise ValueError("Every WP-0023 input must have three pages")
        prompt = "<PAGE><image>" * 3 + "Multi page parsing."
        row, pixels, mask, spatial = native._uocr_build_inputs(
            tokenizer, prompt, [im.convert("RGB") for im in pages], crop_mode=False,
            base_size=1024, image_size=640, max_crops=16,
        )
        prompt_ids = row.tolist()
        if prompt_ids.count(page_id) != 3:
            raise ValueError("Each input must have three prompt page markers")
        ids.append(row)
        images.append((pixels[0].to(device, pixel_dtype), pixels[1].to(device, pixel_dtype), spatial))
        masks.append(mask)
        state.append(Lane(prompt_ids, 3))
    if len({len(row) for row in ids}) != 1:
        raise ValueError("Ragged and padded prompts are outside this trial")
    return torch.stack(ids).to(device), images, torch.stack(masks).to(device), state


@contextmanager
def _ieee_math():
    # Q0 PyTorch 2.13. CUDA matmul and cuDNN convolution have distinct TF32 policies.
    backends = (torch.backends.cuda.matmul, torch.backends.cudnn.conv)
    prior = [backend.fp32_precision for backend in backends]
    try:
        for backend in backends:
            backend.fp32_precision = "ieee"
        yield
    finally:
        for backend, precision in zip(backends, prior):
            backend.fp32_precision = precision


def _fp32_state(module, *, skip_routed=False):
    weights = {}
    for name, value in (*module.named_parameters(), *module.named_buffers()):
        if skip_routed and ".experts." in name:
            continue
        if value.is_floating_point() and value.dtype != torch.float32:
            weights[name] = value.detach().float()
    return weights


class _FP32Expert(torch.nn.Module):
    """Project through the original expert with transient FP32 coefficients."""
    def __init__(self, original):
        super().__init__()
        self.original = original

    def forward(self, hidden):
        return torch.func.functional_call(self.original, _fp32_state(self.original), (hidden,))


@contextmanager
def _fp32_forwards(model):
    # Keep BF16 masters and the large expert bank intact. Only non-routed parameters and
    # buffers get persistent FP32 shadows; each selected expert gets one transient copy.
    if importlib.util.find_spec("triton") is not None:
        raise RuntimeError("WP-0023 FP32 reference requires the Q0 Triton-absent dense fallback")
    decoder = model.model
    decoder_weights = _fp32_state(decoder, skip_routed=True)
    head_weights = _fp32_state(model.lm_head)
    installed = []
    try:
        for layer in decoder.layers:
            experts = getattr(layer.mlp, "experts", ())
            for i, original in enumerate(experts):
                if original is None:
                    raise ValueError("This trial requires single-device resident experts")
                experts[i] = _FP32Expert(original)
                installed.append((experts, i, original))

        def decoder_forward(**kwargs):
            return torch.func.functional_call(decoder, decoder_weights, (), kwargs)

        def head_forward(hidden):
            return torch.func.functional_call(model.lm_head, head_weights, (hidden,))

        with _ieee_math(), sdpa_kernel(SDPBackend.MATH), torch.autocast(model.lm_head.weight.device.type, enabled=False):
            yield decoder_forward, head_forward
    finally:
        for experts, index, original in installed:
            experts[index] = original


def _finite_number(value):
    scalar = float(value)
    return scalar if math.isfinite(scalar) else str(scalar)


def _scores(row, candidates):
    top, ids = torch.topk(row, 2)
    return {
        "argmax": int(torch.argmax(row)),
        "top2": [{"id": i, "logit": _finite_number(v)} for i, v in zip(ids.tolist(), top.tolist())],
        "candidates": {str(i): _finite_number(row[i]) for i in candidates},
    }


def _guard(native, row, state, page_id, eos):
    row = native._uocr_no_repeat_ngram(row, state.tokens, NGRAM_SIZE, NGRAM_WINDOW, set())
    return native._uocr_page_count_guard(row, state.tokens, state.pages, page_id, eos, MAX_PAGE_TOKENS, state.guard)


def _cache_shapes(cache):
    return {
        "kv": [list(x.shape) for x in cache.key_cache],
        "dash_index_keys": {str(i): list(x.shape) for i, x in cache._dash_idx_k.items()},
        "page_state": {k: list(v.shape) for k, v in cache._uocr_pg.items()},
        "page_rope": {str(i): list(s["pf_cnt"].shape) for i, s in cache._page_rope_state.items()},
    }


def _check_probe(probe, batch, eos):
    row = probe["lane"]
    prefixes = probe["prefixes"]
    if not 0 <= row < batch or len(prefixes) != batch:
        raise ValueError("Invalid probe lane or prefix count")
    step = len(prefixes[row])
    if step >= MAX_NEW_TOKENS or eos in prefixes[row]:
        raise ValueError("Target decision must be active and inside the native token bound")
    for prefix in prefixes:
        if len(prefix) > step or (len(prefix) < step and prefix[-1:] != [eos]):
            raise ValueError("A shorter peer prefix must end with its observed EOS")
        if eos in prefix[:-1]:
            raise ValueError("A prefix cannot continue after EOS")
    return step


def _observe(probe, scores, out, hidden, native, model, states, page_id, eos):
    lane = probe["lane"]
    state = states[lane]
    candidates = probe["candidates"]
    row = scores[lane, -1].float()
    raw_scores = _scores(row, candidates)
    guard_before = dict(state.guard)
    after_ngram = native._uocr_no_repeat_ngram(row.clone(), state.tokens, NGRAM_SIZE, NGRAM_WINDOW, set())
    ngram_scores = _scores(after_ngram, candidates)
    after_page = native._uocr_page_count_guard(after_ngram, state.tokens, state.pages, page_id, eos,
                                              MAX_PAGE_TOKENS, state.guard)
    processed = _scores(after_page, candidates)
    cache = out.past_key_values
    page_rope = {str(key): {"page": int(entry["page"][lane]), "tok": int(entry["tok"][lane]),
                            "pf_cnt": entry["pf_cnt"][lane].tolist()} for key, entry in cache._page_rope_state.items()}
    result = {
        "lane": lane, "step": len(state.tokens), "batch_size": len(states),
        "raw": raw_scores, "after_ngram": ngram_scores, "processed": processed,
        "guard": {"before": guard_before, "after": dict(state.guard), "expected_pages": state.pages,
                  "page_id": page_id, "eos_id": eos, "max_page_tokens": MAX_PAGE_TOKENS,
                  "ngram_size": NGRAM_SIZE, "ngram_window": NGRAM_WINDOW,
                  "eos_suppressed": state.guard["marker_cum"] < state.pages},
        "dash_page_state": {key: val[lane].tolist() for key, val in cache._uocr_pg.items()},
        "page_rope": page_rope, "cache_shapes": _cache_shapes(cache),
        "hidden_dtype": str(hidden.dtype), "raw_head_dtype": str(scores.dtype),
        "hidden_states": [tensor[lane, -1].float().tolist() for tensor in out.hidden_states],
        "hidden_order": "decoder input, intermediate layer boundaries, final normalized decoder output; last position only",
    }
    if probe.get("fp32"):
        result["precision_scope"] = ("FP32 native vision, input embeddings, decoder, router, KV and head; "
            "same checkpoint coefficients and native BF16 raster-builder values promoted to FP32; "
            "on-demand FP32 native routed experts; autocast off, CUDA matmul and cuDNN convolution TF32 off; "
            "Triton absent, native dense fallback, PyTorch SDPA MATH forced throughout the reference replay")
    else:
        # Restore original pre-processor state: page-count guard has its own mutable scan cursor.
        probe_state = Lane(state.prompt, state.pages, list(state.tokens), guard_before.copy())
        with _ieee_math(), torch.autocast(hidden.device.type, enabled=False):
            raw_head = torch.nn.functional.linear(hidden.float(), model.lm_head.weight.float(),
                model.lm_head.bias.float() if model.lm_head.bias is not None else None)[lane, -1]
            result["fp32_head"] = {"raw": _scores(raw_head, candidates),
                "processed": _scores(_guard(native, raw_head, probe_state, page_id, eos), candidates)}
        result["precision_scope"] = "Native BF16 execution; additional TF32-off FP32 head uses BF16 decoder output."
    return result


@torch.inference_mode()
def run(model, tokenizer, lanes, *, probe=None):
    """Free greedy decode, or teacher-force prefixes and measure the target next-token decision.

    A peer stopping before the target decision supplies its complete prefix including EOS.
    Finished slots retain their original index and consume inert EOS while their peers decode.
    They no longer collect tokens, process logits, update guards or feed their streamer.
    """
    if not lanes or model.training:
        raise ValueError("At least one lane and an eval-mode model are required")
    native = sys.modules[type(model).__module__]
    batch = len(lanes)
    device = model.lm_head.weight.device
    eos = int(tokenizer.eos_token_id)
    page_id = int(model.config.sparse_attention_config.get("page_token_id", 128827))
    target = _check_probe(probe, batch, eos) if probe is not None else None
    fp32 = probe is not None and probe.get("fp32", False)
    ids, images, masks, states = _inputs(native, tokenizer, lanes, device,
                                          torch.float32 if fp32 else torch.bfloat16, page_id)
    length = ids.size(1)
    streamers = [] if probe is not None else [native.TextStreamer(tokenizer, skip_prompt=False,
                                      skip_special_tokens=False) for _ in states]
    cfg = model.config
    old_cfg = (getattr(cfg, "_ring_window", None), getattr(cfg, "sliding_window", None))
    cfg._ring_window = cfg.sliding_window = None
    dash_state = None
    forwards = {"batch_size": batch, "prefill": 0, "decode": 0}
    result = {"forwards": forwards}
    try:
        dash_state = native.configure_dash_inference(model.model, True, topm=16)
        precision = _fp32_forwards(model) if fp32 else nullcontext((model.model, model.lm_head))
        with precision as (decoder, head):
            # Supply [B,S] positions: the native page-aware indexer reshapes using
            # position_ids.shape[0]. A broadcastable [1,S] silently misdescribes B.
            pos = torch.arange(length, device=device)[None].expand(batch, -1)
            out = decoder(input_ids=ids, position_ids=pos, images=images, images_seq_mask=masks,
                          images_spatial_crop=torch.stack([im[2] for im in images]) if batch > 1 else images[0][2],
                          past_key_values=DynamicCache(), use_cache=True, return_dict=True,
                          output_hidden_states=(target == 0))
            forwards["prefill"] += 1
            result["prefill_cache_shapes"] = _cache_shapes(out.past_key_values)
            for step in range(MAX_NEW_TOKENS):
                hidden = out.last_hidden_state[:, -1:]
                scores = head(hidden)
                if step in (0, 1):
                    forwards["prefill_shapes" if step == 0 else "first_decode_shapes"] = {
                        "input_ids": list(ids.shape if step == 0 else next_input.shape),
                        "hidden": list(out.last_hidden_state.shape), "lm_head": list(scores.shape),
                    }
                if target == step:
                    result["probe"] = _observe(probe, scores, out, hidden, native, model, states, page_id, eos)
                    break
                next_ids = [eos] * batch
                for i, state in enumerate(states):
                    if state.stop is not None:
                        continue
                    logits = _guard(native, scores[i, -1].float(), state, page_id, eos)
                    token = int(torch.argmax(logits)) if probe is None else int(probe["prefixes"][i][step])
                    state.last_choice, state.last_step = token, step
                    if token == eos:
                        state.stop = "eos"
                        continue
                    next_ids[i] = token
                    state.tokens.append(token)
                    if streamers:
                        streamers[i].put(torch.tensor([token]))
                    if length + len(state.tokens) >= MAX_LENGTH:
                        state.stop = "max_length"
                if all(state.stop is not None for state in states):
                    break
                pos = torch.full((batch, 1), length + step, device=device, dtype=torch.long)
                next_input = torch.tensor(next_ids, device=device)[:, None]
                out = decoder(input_ids=next_input, position_ids=pos,
                              past_key_values=out.past_key_values, use_cache=True, return_dict=True,
                              output_hidden_states=(target == step + 1))
                forwards["decode"] += 1
            result["lanes"] = [state.summary(tokenizer, page_id, probe is not None) for state in states]
    finally:
        if dash_state is not None:
            native.configure_dash_inference(model.model, False, state=dash_state)
        cfg._ring_window, cfg.sliding_window = old_cfg
        for streamer in streamers:
            streamer.end()
    return result
