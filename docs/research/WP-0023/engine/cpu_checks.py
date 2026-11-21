"""CPU-only control flow and pinned DASH mathematics checks; no checkpoint load."""
import argparse
import ast
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import torch
from torch import nn
from torch.nn import functional as F
from PIL import Image

import native_batch as engine


def load_helpers(source, names):
    tree = ast.parse(source.read_text(encoding="utf-8"))
    functions = [f for f in tree.body if isinstance(f, ast.FunctionDef) and f.name in names]
    assert {f.name for f in functions} == set(names)
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), "exec"), globals())


def check_native_mask_math():
    block_size = 3
    idx = SimpleNamespace(image_token_id=3, page_token_id=4, block_size=block_size, per_page_image_tokens=2)
    prompt = torch.tensor([[0, 4, 3, 3, 4, 3, 3, 4, 3, 3, 7]] * 2)
    kv = SimpleNamespace(get_seq_length=lambda: prompt.size(1) + 1)
    _uocr_dash_decode_allow(idx, prompt, kv)
    _uocr_dash_decode_allow(idx, torch.tensor([[4], [4]]), kv)
    actual = _uocr_dash_decode_allow(idx, torch.tensor([[6], [4]]), kv)
    assert not torch.equal(actual[0], actual[1])
    assert kv._uocr_pg["mcum"].tolist() == [4, 5]
    for i, token in enumerate((6, 4)):
        single = SimpleNamespace(get_seq_length=kv.get_seq_length)
        _uocr_dash_decode_allow(idx, prompt[i:i+1], single)
        _uocr_dash_decode_allow(idx, torch.tensor([[4]]), single)
        reference = _uocr_dash_decode_allow(idx, torch.tensor([[token]]), single)
        assert torch.equal(actual[i], reference[0])
    # Different row read sets/values make an unintended broadcast visible.
    torch.manual_seed(23)
    q = torch.randn(2, 2, 1, 4)
    k, v = torch.randn(2, 2, 9, 4), torch.randn(2, 2, 9, 4)
    selected = torch.tensor([[[0]], [[1]]])
    bias = torch.tensor([[[-0.25]], [[-1.5]]])
    valid = torch.ones_like(bias).bool()
    pos = torch.tensor([[8], [8]])
    args = [q, k, v, selected, bias, valid, pos]
    batched = _decode_attend(*args, 3, 2, 0.5)
    reference = torch.cat([_decode_attend(*(x[i:i+1] for x in args), 3, 2, 0.5) for i in range(2)])
    torch.testing.assert_close(batched, reference)


def _uocr_build_inputs(tokenizer, prompt, pages, **kwargs):
    assert prompt == "<PAGE><image>" * 3 + "Multi page parsing."
    marker = pages[0].getpixel((0, 0))[0]
    pixels = torch.tensor([marker], dtype=torch.bfloat16)
    ids = torch.tensor([4, 3, 4, 3, 4, 3, 6])
    return ids, (pixels, pixels), ids == 3, torch.ones((3, 2), dtype=torch.long)


class TextStreamer:
    seen = []

    def __init__(self, tokenizer, **kwargs):
        self.tokens = []
        self.ended = False
        self.seen.append(self)

    def put(self, token):
        assert not self.ended
        self.tokens.append(int(token))

    def end(self):
        self.ended = True


def configure_dash_inference(decoder, on, **kwargs):
    decoder.dash_active = on
    return {"enabled": on}


class Decoder(nn.Module):
    def __init__(self):
        super().__init__()
        layer = nn.Module()
        layer.mlp = nn.Module()
        layer.mlp.experts = nn.ModuleList([nn.Linear(8, 8, bias=False)])
        layer.mlp.experts[0].weight.data.copy_(torch.eye(8))
        self.layers = nn.ModuleList([layer])
        self.register_buffer("template", torch.ones(1, dtype=torch.bfloat16))

    def forward(self, *, input_ids, position_ids, past_key_values, output_hidden_states, images=None,
                images_seq_mask=None, **kwargs):
        assert self.dash_active
        batch, length = input_ids.shape
        assert position_ids.shape == input_ids.shape
        cache = past_key_values
        idx = SimpleNamespace(page_token_id=4, image_token_id=3, block_size=2, per_page_image_tokens=1)
        _uocr_dash_decode_allow(idx, input_ids, cache)
        transcripts = [[4, 4, 4, 1], [4, 5, 4, 6, 4, 7, 1]]
        if images is not None:
            assert len(images) == batch and images_seq_mask.shape == input_ids.shape
            assert images[0][1].dtype == self.template.dtype
            cache.kinds = [int(row[1]) for row in images]
            cache.steps = 0
        else:
            cache.steps += 1
        shape = (batch, 1, length, 2)
        cache.update(torch.zeros(shape), torch.zeros(shape), 0)
        cache._dash_idx_k = {0: torch.zeros(batch, cache.get_seq_length(), 2)}
        cache._page_rope_state = {0: {"pf_cnt": torch.ones(batch, 4), "page": torch.zeros(batch),
                                      "tok": torch.ones(batch)}}
        tokens = [transcripts[kind][min(cache.steps, len(transcripts[kind])-1)] for kind in cache.kinds]
        hidden = F.one_hot(torch.tensor(tokens), 8).to(self.template.dtype)[:, None, :]
        hidden = self.layers[0].mlp.experts[0](hidden)
        return SimpleNamespace(last_hidden_state=hidden, past_key_values=cache,
                               hidden_states=(hidden, hidden) if output_hidden_states else None)


class Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.lm_head = nn.Linear(8, 8, bias=False)
        self.lm_head.weight.data.copy_(torch.eye(8))
        self.model = Decoder()
        self.config = SimpleNamespace(sparse_attention_config={"page_token_id": 4}, _ring_window=77, sliding_window=9)


def check_wrapper():
    torch.set_num_threads(1)
    model = Model().bfloat16().eval()
    tokenizer = SimpleNamespace(eos_token_id=1, decode=lambda ids, **kwargs: str(ids))
    inputs = [[Image.new("RGB", (2, 2), (i, 0, 0)) for _ in range(3)] for i in (0, 1)]
    singles = [engine.run(model, tokenizer, [x])["lanes"][0] for x in inputs]
    assert [x["token_ids"] for x in singles] == [[4, 4, 4], [4, 5, 4, 6, 4, 7]]
    for order in ([0, 1], [1, 0]):
        results = engine.run(model, tokenizer, [inputs[i] for i in order])
        counts = results["forwards"]
        assert (counts["prefill"], counts["decode"], counts["batch_size"]) == (1, 6, 2)
        assert counts["first_decode_shapes"]["input_ids"] == [2, 1]
        assert counts["first_decode_shapes"]["lm_head"] == [2, 1, 8]
        assert results["lanes"] == [singles[i] for i in order]
        for stream, i in zip(TextStreamer.seen[-2:], order):
            assert stream.tokens == singles[i]["token_ids"] and stream.ended
    orig_expert = model.model.layers[0].mlp.experts[0]
    for fp32 in (False, True):
        probe = {"lane": 1, "prefixes": [[4, 4, 4, 1], [4, 5, 4, 6, 4]], "fp32": fp32, "candidates": [6, 7]}
        observed = engine.run(model, tokenizer, inputs, probe=probe)
        assert observed["lanes"][0] == singles[0] and observed["probe"]["processed"]["argmax"] == 7
        assert observed["probe"]["raw_head_dtype"] == ("torch.float32" if fp32 else "torch.bfloat16")
        assert model.model.layers[0].mlp.experts[0] is orig_expert
        assert model.config._ring_window == 77 and model.config.sliding_window == 9 and not model.model.dash_active
    with patch.object(engine, "MAX_LENGTH", 9):
        length_stop = engine.run(model, tokenizer, inputs)
        assert all(row["stop_cause"] == "max_length" and len(row["token_ids"]) == 2 for row in length_stop["lanes"])
    with patch.object(engine, "MAX_NEW_TOKENS", 1):
        limit = engine.run(model, tokenizer, inputs)
        assert all(row["stop_cause"] == "max_new_tokens" and len(row["token_ids"]) == 1 for row in limit["lanes"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("model_tree", type=Path)
    tree = parser.parse_args().model_tree
    load_helpers(tree / "modeling_unlimitedocr.py", [
        "_uocr_dash_decode_allow", "_uocr_no_repeat_ngram", "_uocr_page_count_guard"])
    load_helpers(tree / "modeling_deepseekv2.py", ["_decode_attend"])
    _MASK_NEG = -1e9  # pinned dash_attention.py constant
    check_native_mask_math()
    check_wrapper()
    print("PASS: CPU native page mask and attention; singleton/both orders, post-EOS outputs and streamer; "
          "teacher forcing, numeric stages, atomic FP32 expert restoration, length limits.")
