"""Check actual pinned upstream guard and cache functions on CPU with unlike lane histories."""
import ast
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import torch
import torch.nn.functional as F


MODEL = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/models/Unlimited_OCR_2_04809669")
PINS = {
    "modeling_unlimitedocr.py": "f6df813cef23cc28b1daca40fd8cb20740d05a238e7b9dfa2334531fdcf39f1f",
    "_sparse_base_impl.py": "86da9c5638704bb9338575040568a97b3e10820bbeb426f51c07e866f3423ccd",
}


def source_function(filename, name):
    path = MODEL / filename
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PINS[filename]
    defs = [f for f in ast.walk(ast.parse(raw)) if isinstance(f, ast.FunctionDef) and f.name == name]
    assert len(defs) == 1
    scope = {"torch": torch, "F": F}
    exec(compile(ast.Module(body=defs, type_ignores=[]), str(path), "exec"), scope)
    return scope[name]


def decode_state(prompts, steps, allow, rope):
    indexer = SimpleNamespace(image_token_id=4, page_token_id=3, block_size=2, per_page_image_tokens=1)
    ids = torch.tensor(prompts)
    size, width = ids.shape
    cache = SimpleNamespace(get_seq_length=lambda: width)
    assert allow(indexer, ids, cache) is None
    # Supply a known terminal page, token and three page offsets for incremental RoPE.
    state = dict(page=torch.zeros(size, dtype=torch.long), tok=torch.full((size,), 2),
                 pf_cnt=torch.tensor([[1, 2, 3, 4]] * size), n_pg=4)
    cache._page_rope_state = {0: state}
    layer = SimpleNamespace(indexer=indexer, layer_idx=0)
    trace = []
    for consumed in steps:
        row = torch.tensor(consumed)[:, None]
        mask = allow(indexer, row, cache)
        layer._sparse_source_input_ids = row
        tok, page = rope(layer, 1, cache)
        trace.append([
            dict(allow=mask[i].tolist(), token_position=tok[i].item(), page=page[i].item(),
                 marker_sum=cache._uocr_pg["mcum"][i].item()) for i in range(size)
        ])
        width += 1
    return trace


def main():
    torch.set_num_threads(1)
    source = "modeling_unlimitedocr.py"
    allow = source_function(source, "_uocr_dash_decode_allow")
    rope = source_function("_sparse_base_impl.py", "_main_rope_coords")
    # Same length, same three page markers, distinct ordering of image blocks.
    prompts = [[3, 4, 3, 4, 3, 4, 6, 6], [6, 3, 4, 6, 3, 4, 3, 4]]
    steps = [[3, 3], [9, 3], [3, 7], [2, 3], [2, 7]]
    traces = [decode_state([prompt], [[row[i]] for row in steps], allow, rope)
              for i, prompt in enumerate(prompts)]
    orders = []
    for order in [(0, 1), (1, 0)]:
        double = decode_state([prompts[i] for i in order], [[row[i] for i in order] for row in steps], allow, rope)
        for t, rows in enumerate(double):
            for slot, row in enumerate(rows):
                assert row == traces[order[slot]][t][0]
        orders.append(dict(order=order, matched_steps=len(double)))
    # Distinct lane marker counters and pages after a different second token.
    assert traces[0][1][0]["marker_sum"] == 4 and traces[1][1][0]["marker_sum"] == 5
    assert traces[0][3][0]["page"] == 2 and traces[1][3][0]["page"] == 3

    guard = source_function(source, "_uocr_page_count_guard")
    ngram = source_function(source, "_uocr_no_repeat_ngram")
    histories = [[3, 7, 8, 7], [3, 3, 3, 6]]
    state = [dict(marker_cum=0, scanned=0, page_len=0) for _ in histories]
    masked = []
    for history, item in zip(histories, state):
        logits = torch.arange(10, dtype=torch.float32)
        logits = guard(ngram(logits, history, 2, 8, set()), history, 3, 3, 2, 50, item)
        masked.append(torch.isneginf(logits).nonzero().flatten().tolist())
    assert masked == [[2, 8], []]
    assert [s["marker_cum"] for s in state] == [1, 3]
    assert not torch.cuda.is_initialized()
    print(json.dumps(dict(torch=torch.__version__, source=PINS, device="cpu", cuda_initialized=False,
                          history=histories, masked=masked, page_guard=state,
                          singleton_decode_traces=traces, double_against_singletons=orders), indent=2))


if __name__ == "__main__":
    main()
