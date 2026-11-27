"""CPU tests of definitions extracted from pinned native source; no model import/load."""
import ast
import dis
from hashlib import sha256
import json
from pathlib import Path
import struct
import subprocess
import sys
from types import CodeType

import torch

VOCAB = 129280
PAGE, EOS = 128827, 1


def body(code, qualname):
    if code.co_qualname == qualname:
        return code
    for obj in code.co_consts:
        if isinstance(obj, CodeType):
            found = body(obj, qualname)
            if found is not None:
                return found


def git(path):
    return subprocess.check_output(["git", "show", "d497bae7db42589bd2ede512f932b0488f6309cd:" + path])


def main(root):
    torch.set_num_threads(1)
    assert not torch.cuda.is_initialized()
    pins = json.loads(git("docs/research/WP-0041/source.json"))
    native = root / "models/Unlimited_OCR_2_04809669"
    names = ["modeling_unlimitedocr.py", "modeling_deepseekv2.py", "_sparse_base_impl.py", "dash_attention.py", "config.json"]
    for name in names:
        assert sha256((native / name).read_bytes()).hexdigest() == pins["files"][name]["sha256"]
    util = "transformers/cache_utils.py"
    assert sha256((root / "venv/Lib/site-packages" / util).read_bytes()).hexdigest() == pins["versions"]["runtime_source_sha256"][util]
    source = (native / names[0]).read_bytes()
    module = compile(source, names[0], "exec", dont_inherit=True)
    gen = body(module, "UnlimitedOCRForCausalLM._uocr_generate")
    bound = [[i.offset, i.opname, i.argrepr, i.positions.lineno] for i in dis.get_instructions(gen)
             if i.positions.lineno is not None and 1167 <= i.positions.lineno <= 1191
             and i.opname in {"CALL","STORE_FAST","RETURN_VALUE","JUMP_FORWARD","FOR_ITER","LOAD_GLOBAL","LOAD_FAST"}]
    tree = ast.parse(source)
    guards = {"_uocr_no_repeat_ngram","_uocr_page_count_guard"}
    ns = {}
    selected = ast.Module(body=[fn for fn in tree.body if getattr(fn,"name",None) in guards],type_ignores=[])
    exec(compile(selected, names[0], "exec"), ns)
    repeat, pages = ns["_uocr_no_repeat_ngram"], ns["_uocr_page_count_guard"]
    assert repeat.__code__.co_code == body(module, repeat.__name__).co_code
    assert pages.__code__.co_code == body(module, pages.__name__).co_code
    p = list(range(100,134))

    def logits():
        x = torch.zeros(VOCAB, dtype=torch.float32, device="cpu")
        x[7], x[8], x[EOS] = 9., 4., 8.
        return x

    state = {"scanned":0,"marker_cum":0,"page_len":0}
    h = [PAGE]+p+[7]+p
    x = logits()
    raw = x.clone()
    assert repeat(x, h, 35, 1024, set()) is x
    zn = x.clone()
    assert pages(x,h,3,PAGE,EOS,20000,state) is x
    assert [int(z.argmax()) for z in (raw,zn,x)] == [7,1,8]
    assert x[7].isneginf() and x[EOS].isneginf()
    assert state == {"scanned":70,"marker_cum":1,"page_len":69}
    # Force a previously banned PAGE. Its cloned value is already minus infinity.
    y = logits()
    h = [PAGE] + p + [PAGE] + p
    repeat(y,h,35,1024,set())
    pages(y,h,3,PAGE,EOS,1,dict.fromkeys(state,0))
    assert bool(y.isneginf().all()) and int(y.argmax()) == 0

    h = [PAGE,10,11,12]
    st = dict.fromkeys(state,0)
    y = torch.zeros_like(x)
    y[EOS], y[13] = 10., 5.
    pages(y,h,2,PAGE,EOS,4,st)
    assert int(y.argmax()) == 13 and st == {"scanned":4,"marker_cum":1,"page_len":3}
    states = []
    for cursor in (4,0):
        restored = dict(st, scanned=cursor)
        y = torch.zeros_like(x)
        y[PAGE], y[EOS], y[14] = 4., 9., 6.
        pages(y,h+[13],2,PAGE,EOS,4,restored)
        states.append([restored,int(y.argmax()), torch.isfinite(y).sum().item()])
    assert states[0] == [{"scanned":5,"marker_cum":1,"page_len":4},PAGE,1]
    assert states[1] == [{"scanned":5,"marker_cum":2,"page_len":4},EOS,1]
    # A prompt-only predecessor is absent from gen_ids, the actual function argument.
    winners = []
    for i in (35,36,None):
        h = list(range(1000,2060)) if i is not None else list(range(1000,1050))
        h[-34:] = p
        if i is not None:
            h[i:i+35] = p+[7]
        y = logits()
        y[EOS] = 0.
        repeat(y,h,35,1024,set())
        winners.append(int(y.argmax()))
        if i is None:
            mixed = logits()
            mixed[EOS] = 0.
            repeat(mixed,p+[7]+h,35,1024,set())
            assert int(mixed.argmax()) == 8
    assert winners == [7,8,7]
    # First differing lane is not in general an exponent lane of the finite value.
    infword = struct.pack("<I",0xff800000)
    witnesses = {}
    for word in (0xff000001,0xff000100,0xff000000,0x7f800000,0x00800000):
        rawword = struct.pack("<I",word)
        if (word >> 23) & 255 == 255:
            continue
        lane = next(i for i in range(4) if rawword[i] != infword[i])
        witnesses[lane] = f"{word:08x}"
    assert set(witnesses) == set(range(4))
    assert not torch.cuda.is_initialized()
    print(json.dumps({"python":sys.version,"torch":torch.__version__,"native_sha256":sha256(source).hexdigest(),
        "unloaded_generator_qualname":gen.co_qualname,"code_bytes_sha256":sha256(gen.co_code).hexdigest(),
        "native_code_instructions":bound,"actual_guard_names":sorted(guards),"native_cpu_guards_pass":True,
        "cursor_witness":states,"native_window_winners":winners,"first_differing_finite_words_by_lane":witnesses,
        "cuda_initialized":False},indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
