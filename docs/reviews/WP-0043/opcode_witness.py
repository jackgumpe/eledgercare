"""Execute the pinned generator code object on a deterministic CPU-only test receiver."""
import builtins
import dis
from hashlib import sha256
import json
from pathlib import Path
import sys
from types import FunctionType, SimpleNamespace

import torch

from native_review import body, git, PAGE, EOS, VOCAB


def main(model_dir):
    torch.set_num_threads(1)
    path = model_dir / "modeling_unlimitedocr.py"
    source = path.read_bytes()
    assert sha256(source).hexdigest() == json.loads(git("docs/research/WP-0041/source.json"))["files"][path.name]["sha256"]
    compiled = compile(source, str(path), "exec", dont_inherit=True)
    code = body(compiled, "UnlimitedOCRForCausalLM._uocr_generate")
    rep = body(compiled, "_uocr_no_repeat_ngram")
    pg = body(compiled, "_uocr_page_count_guard")
    history = [PAGE, *range(100,134), 7, *range(100,134)]
    tail = [8, PAGE]
    words = []
    next_instruction = {}
    ops = list(dis.get_instructions(code))
    for index, op in enumerate(ops):
        if op.opname == "STORE_FAST" and op.argval == "logits":
            next_instruction[ops[index+1].offset] = "C" + str(len(next_instruction))
        elif op.opname == "STORE_FAST" and op.argval == "pos":
            next_instruction[ops[index+1].offset] = "D"

    class CpuHead:
        weight = torch.zeros(1, device="cpu")

        def __call__(self, hidden):
            step = int(hidden.item())
            x = torch.zeros((1,1,VOCAB), dtype=torch.float32, device="cpu")
            if step < len(history):
                x[0,0,history[step]] = 20
            elif step == len(history):
                x[0,0,[7,EOS,8]] = torch.tensor([9.,8.,4.])
            elif step == len(history)+1:
                x[0,0,PAGE] = 20
            else:
                x[0,0,EOS] = 20
            return x

    class CpuBlocks:
        step = -1

        def __call__(self, **kwargs):
            self.step += 1
            return SimpleNamespace(past_key_values=kwargs["past_key_values"],
                                   last_hidden_state=torch.tensor([[[self.step]]], device="cpu"))

    def test_import(name, *args, **kwargs):
        if name == "transformers.cache_utils":
            return SimpleNamespace(DynamicCache=SimpleNamespace)
        return builtins.__import__(name, *args, **kwargs)

    glob = {"__builtins__": dict(vars(builtins), __import__=test_import),"torch":torch,
            "configure_dash_inference":lambda *args,**kwargs: None}
    glob[rep.co_name] = FunctionType(rep, glob)
    glob[pg.co_name] = FunctionType(pg, glob)
    generate = FunctionType(code, glob)
    receiver = SimpleNamespace(lm_head=CpuHead(),model=CpuBlocks(),
                               config=SimpleNamespace(sparse_attention_config={"page_token_id":PAGE}))
    phases = []
    guard_calls = []

    def instruction(executing, offset):
        if offset not in next_instruction:
            return
        frame = sys._getframe(1)
        assert executing is frame.f_code is code and frame.f_locals["self"] is receiver
        if frame.f_locals.get("step") == len(history):
            x = frame.f_locals["logits"]
            phases.append([next_instruction[offset],offset,int(x.argmax()),list(frame.f_locals["gen"][-2:])])
            words.append(x[[7,EOS,8]].clone())

    def guard_start(executing, offset):
        frame = sys._getframe(1)
        assert executing is frame.f_code and frame.f_back.f_code is code
        if frame.f_back.f_locals.get("step") == len(history):
            guard_calls.append([executing.co_name,frame.f_back.f_lasti])

    assert not torch.cuda.is_initialized()
    monitoring = sys.monitoring
    tool_id = 3
    monitoring.use_tool_id(tool_id, "WP-0043 independent CPU witness")
    monitoring.register_callback(tool_id, monitoring.events.INSTRUCTION, instruction)
    monitoring.register_callback(tool_id, monitoring.events.PY_START, guard_start)
    monitoring.set_local_events(tool_id, code, monitoring.events.INSTRUCTION)
    for guard in (rep, pg):
        monitoring.set_local_events(tool_id, guard, monitoring.events.PY_START)
    try:
        output = generate(receiver,SimpleNamespace(eos_token_id=EOS,decode=lambda ids,**kwargs: str(len(ids))),
                          torch.tensor([PAGE,PAGE]), None,None,None,100,131072,0.0,True,20000,35,1024,None,16,False,0)
    finally:
        for target in (code, rep, pg):
            monitoring.set_local_events(tool_id, target, 0)
        monitoring.register_callback(tool_id, monitoring.events.INSTRUCTION, None)
        monitoring.register_callback(tool_id, monitoring.events.PY_START, None)
        monitoring.free_tool_id(tool_id)
    assert not torch.cuda.is_initialized()
    assert output["finish_reason"] == "stop" and output["token_ids"] == history+tail and EOS not in output["token_ids"]
    assert [r[:3] for r in phases] == [["C0",1174,7],["C1",1238,1],["C2",1282,8],["D",1854,8]]
    assert [r[0] for r in guard_calls] == [rep.co_name,pg.co_name]
    assert phases[0][3] == [132,133] and phases[-1][3] == [133,8]
    print(json.dumps({"execution":"pinned generator and guard bytecode, CPU test receiver, stubbed cache/config",
        "word_token_order":[7,EOS,8],"guard_caller_offsets":guard_calls,"cut_offset_maximum_tail":phases,
        "little_endian_words":[[f"{j & 0xffffffff:08x}" for j in x.view(torch.int32).tolist()] for x in words],
        "true_returned_ids":len(output["token_ids"]),"true_stop":output["finish_reason"],
        "cuda_initialized":False},indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
