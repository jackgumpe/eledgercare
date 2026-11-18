"""CPU contract controls using only plan metadata, synthetic token rows and geometry."""
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

PLAN = {
    "ab": "b705772d04e1cab173096bd9fb779a57f71e68af1eaccc4f7dc107a0432fffbf",
    "ba": "7a48e28f6ef5f736d4fed0c89a28e07800ecf827a8ad646197fc3fa9aac924a9",
}
INPUT = {
    "h": "e5270d9eca7bb902f692795949bfe718240bc0e3733d0a02508fef850497eca7",
    "a": "671e8e18d6cf84db671ea0487be8b197e535753dabac6c1561e169654d113c5b",
    "warm": "25c14530845cad96329b528f860032c27a1259ed46de3ccb56f0e57730aa0858",
}


def read_plans(folder):
    summary = {}
    matched = {}
    for name, want in PLAN.items():
        raw = (folder / f"g0-{name}.json").read_bytes()
        assert hashlib.sha256(raw).hexdigest() == want
        request = json.loads(raw)["requests"]
        order = ["native", "carbon_bf16"]
        if name == "ba":
            order.reverse()
        assert len(request) == 10
        held_out = scored = 0
        for j, mode in enumerate(order):
            rows = request[5*j:5*j+5]
            assert [r["mode"] for r in rows] == [mode]*5
            assert [r["label"] for r in rows] == ["warm-1", "warm-2", "warm-3", "h", "a"]
            assert [r["pages"] for r in rows] == [1, 1, 1, 4, 60]
            assert [r["warmup"] for r in rows] == [True, True, True, False, False]
            for r in rows:
                key = "warm" if r["warmup"] else r["label"]
                assert r["sha256"] == INPUT[key] and len(r["rgb_sha256"]) == r["pages"]
                sig = (r["sha256"], tuple(r["rgb_sha256"]), r["pdf"])
                assert matched.setdefault(key, sig) == sig
                if r["warmup"]:
                    held_out += math.ceil(r["pages"]/3)
                else:
                    scored += math.ceil(r["pages"]/3)
        assert (held_out, scored) == (6, 44)
        summary[name] = dict(sha256=want, order=order, excluded_windows=held_out, scored_windows=scored)
    return summary


def batched_control(prompts, outputs):
    # Toy K/V values are traceable unique tokens. Never use a GPU or a model here.
    sentinel = -100000
    storage = np.full((4, 32), sentinel, dtype=np.int32)
    ptr = storage.ctypes.data
    valid = np.array([bool(p) for p in prompts])
    live = valid.copy()
    lens = np.array([len(p) for p in prompts], dtype=np.int32)
    for lane, p in enumerate(prompts):
        storage[lane, :len(p)] = p
    snapshots = [None] * 4
    saved_tokens = [[] for _ in prompts]
    for step in range(16):  # two complete eight-step bursts, including post-EOS steps
        for lane in range(4):
            if not live[lane]:
                if snapshots[lane] is None:
                    snapshots[lane] = storage[lane].copy()
                assert np.array_equal(storage[lane], snapshots[lane])
                continue
            # EOS is sampled and recorded as stop before any K/V write for it.
            nxt = outputs[lane][step]
            if nxt == 1:
                live[lane] = False
                snapshots[lane] = storage[lane].copy()
                continue
            assert np.array_equal(storage[lane, :lens[lane]], prompts[lane] + saved_tokens[lane])
            storage[lane, lens[lane]] = nxt
            lens[lane] += 1
            saved_tokens[lane].append(nxt)
        assert storage.ctypes.data == ptr
    assert not live.any()
    for lane, seq in enumerate(outputs):
        serial = prompts[lane] + (seq[:seq.index(1)] if valid[lane] else [])
        assert list(storage[lane, :lens[lane]]) == serial
        assert (storage[lane, lens[lane]:] == sentinel).all()
    return lens.tolist()


def critical_control():
    # Correctness matrix W rows, N columns and novel-unflagged semantics are distinct.
    # A wrong-but-changed value is a new unflagged error even on a wrong->wrong row.
    win = [(True,"K",False),(True,"K",False),(False,"M",False),(False,"M",True),(False,"M",False)]
    neural = [(True,"K",False),(False,"L",False),(True,"K",False),(False,"L",False),(False,"M",False)]
    matrix = [[0,0],[0,0]]
    novel = []
    for i,(w,n) in enumerate(zip(win,neural)):
        matrix[int(w[0])][int(n[0])] += 1
        if not n[0] and not n[2] and (w[0] or w[1:] != n[1:]):
            novel.append(i)
    assert matrix == [[2,1],[1,1]] and novel == [1,3]
    return dict(matrix_wrong_correct=matrix, repairs=matrix[0][1], regressions=matrix[1][0],
                net=matrix[0][1]-matrix[1][0], new_or_changed_unflagged=novel)


def main(folder):
    p = [[4,6,8], [3], [2,9], []]
    y = [[10,11,1], [1], [18,19,20,21,22,23,24,25,26,1], []]
    normal = batched_control(p,y)
    perm = [2,3,0,1]
    assert batched_control([p[i] for i in perm], [y[i] for i in perm]) == [normal[i] for i in perm]
    assert batched_control([[],[],[],[]],[[],[],[],[]]) == [0]*4
    s = 1 + 3*(273+1) + 4
    capacity = 32*math.ceil((s+24000)/32)
    kv = 4*12*capacity*10*128*4
    idx = 4*12*capacity*128*4
    bar = 4*12*(capacity//32)*128*4
    assert (s,capacity,kv,idx,bar) == (827,24832,6102712320,610271232,19070976)
    print(json.dumps(dict(plans=read_plans(folder), masked_lane_final_lengths=normal,
                          lane_permutation=perm, burst_size=8, dummy_writes=0,
                          three_page_prefill=s, static_capacity=capacity,
                          kv_bytes=kv, router_key_bytes=idx, block_summary_bytes=bar,
                          synthetic_transitions=critical_control()),indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
