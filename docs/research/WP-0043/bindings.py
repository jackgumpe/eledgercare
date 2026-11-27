"""Resolve qualified code + instruction by matching exact, unmodified source bytes."""
import inspect
import sys
import types
from pathlib import Path
from capture import PHASES, code_identity, digest, line_offset

OCR = "modeling_unlimitedocr.py"
BASE = "_sparse_base_impl.py"
DASH = "modeling_deepseekv2.py"
HASHES = {OCR:"f6df813cef23cc28b1daca40fd8cb20740d05a238e7b9dfa2334531fdcf39f1f",
          BASE:"86da9c5638704bb9338575040568a97b3e10820bbeb426f51c07e866f3423ccd",
          DASH:"24a15dfd47578ab24a7a4d4e977dc5d7a23dfef0a2a4c4bf73fcf3e2ce7acaf2"}
GEN = "UnlimitedOCRForCausalLM._uocr_generate"
LAYER = "DeepseekV2DecoderLayer.forward"
# First instruction on each statement: values assigned on the previous line exist.
SITES = {
 (OCR,"_uocr_no_repeat_ngram"):{610:"rep_entry"},
 (OCR,"_uocr_page_count_guard"):{585:"page_entry"},
 (OCR,GEN):{1162:"prefill_producer",1191:"model_producer",1167:"head_producer",1169:"rep_producer",1171:"page_producer",1176:"choice_consumer",1168:PHASES[0],1170:PHASES[1],1173:PHASES[2],1189:"D",
            1180:"terminal_eos",1201:"cleanup"},
 (OCR,"_uocr_dash_decode_allow"):{517:"page_before",528:"page_after"},
 (DASH,"_patched_forward"):{237:"prefill_dispatch",241:"dash_dispatch",243:"generic_dispatch"},
 (DASH,"_dash_indexer_rope"):{134:"idx_2d",142:"idx_1d",143:"idx_main"},
 (BASE,"DeepseekV2MLP.forward"):{519:"shared_output"},
 (BASE,LAYER):{3693:"B",3707:"attention_exit",3713:"residual",3715:"post_rms",
               3716:"mixture",3718:"block_exit"},
 (DASH,"_dash_decode_forward"):{509:"kv_before",510:"kv_after",515:"router_qk",
                               518:"index_after",530:"routing_exit"},
 (DASH,"_infer_route_select"):{350:"scores_pre_clean",356:"top_m",362:"route_final"},
 (DASH,"_decode_attend"):{475:"token_mask"},
 (BASE,"MoEGate.forward"):{629:"expert_route"},
 (BASE,"DeepseekV2MoE.forward"):{746:"expert_total",748:"shared_sum"},
 (BASE,"DeepseekV2MoE.moe_infer"):{815:"expert_dispatch",824:"expert_return"},
}


def recursive_codes(code):
    yield code
    for child in code.co_consts:
        if isinstance(child,types.CodeType):
            yield from recursive_codes(child)


def static_sources(model_dir):
    if sys.version_info[:3] != (3,12,10):
        raise ValueError("pinned CPython 3.12.10 required")
    by_name = {}
    for name,sha in HASHES.items():
        file = Path(model_dir)/name
        raw = file.read_bytes()
        if digest(raw)!=sha:
            raise ValueError("source bytes: "+name)
        for code in recursive_codes(compile(raw,str(file),"exec",dont_inherit=True)):
            if (name,code.co_qualname) in SITES:
                by_name[(name,code.co_qualname)] = code
    if set(by_name)!=set(SITES):
        raise ValueError("source callable inventory differs")
    return by_name


def resolve(model_dir,package=None):
    static = static_sources(model_dir)
    runtime = {}
    for (name,qual),expected in static.items():
        if package is None:
            code = expected
        else:
            obj = sys.modules[package+"."+name[:-3]]
            for part in qual.split("."):
                obj = getattr(obj,part)
            code = inspect.unwrap(obj).__code__
            if code_identity(code)!=code_identity(expected):
                raise ValueError("loaded code differs: "+qual)
        runtime[code] = {line_offset(code,line):tag for line,tag in SITES[(name,qual)].items()}
    return runtime


def caller_binding(root):
    file=Path(root)/BASE
    raw=file.read_bytes()
    if digest(raw)!=HASHES[BASE]:
        raise ValueError("caller source digest")
    code=next(c for c in recursive_codes(compile(raw,str(file),"exec",dont_inherit=True))
              if c.co_qualname=="DeepseekV2Model.forward")
    return code_identity(code)
