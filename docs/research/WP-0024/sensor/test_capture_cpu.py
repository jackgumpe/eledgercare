"""Check native span offsets on archived emissions and causal hook alignment without CUDA or weights."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE))
import numpy as np
import torch
from tokenizers import Tokenizer
from capture import finish_capture, observer
from spans import map_window, token_bytes, verify_parsers


class Toy(torch.nn.Module):
    def forward(self, input_ids, position_ids):
        return input_ids[...,None].to(torch.bfloat16).expand(-1,-1,1280)


def run(model):
    verify_parsers()
    jsonfile=model/"tokenizer.json"
    tokenizer=Tokenizer.from_file(str(jsonfile))
    added={r["id"]:r["content"] for r in json.loads(jsonfile.read_bytes())["added_tokens"]}
    lookup=lambda ids:[tokenizer.id_to_token(i) for i in ids]
    rows={}
    with ZipFile(ROOT/"docs/reviews/WP-0023/dev-r1.zip") as z:
        for kind in ("short","long"):
            raw=json.loads(z.read("run/trial/g1-stock-"+kind+".json"))["result"]
            out=map_window(raw["text"],raw["token_ids"],lookup,added)
            assert len(out["pages"])==3
            for span in out["spans"]:
                start,end=span["char_range"]
                byte0,byte1=span["byte_range"]
                assert raw["text"][start:end].encode()==raw["text"].encode()[byte0:byte1]
                if span["kind"]=="row":
                    assert raw["text"][start:end].startswith("<tr>")
            if kind=="long":
                assert [r["cells"] for r in out["spans"] if r["kind"]=="row" and r["page"]==2][0]==["Part","item","Count","Price"]
            rows[kind]={"spans":len(out["spans"]),"native_ids":len(raw["token_ids"])}
    unicode_text="Météo · 川水"
    ids=tokenizer.encode(unicode_text,add_special_tokens=False).ids
    ends=token_bytes(unicode_text,ids,lookup,added)
    assert ends[-1]==len(unicode_text.encode())
    toy=torch.nn.Module()
    toy.model=Toy()
    toy.lm_head=torch.nn.Identity()
    inp=torch.tensor([[24,35,46]])
    seq=[3,19,7]
    with observer(toy) as tr:
        toy.lm_head(toy.model(input_ids=inp,position_ids=torch.arange(3)[None])[:,-1:])
        for n,tok in enumerate(seq,3):
            toy.lm_head(toy.model(input_ids=torch.tensor([[tok]]),position_ids=torch.tensor([[n]])))
    meta={"token_ids":seq,"prompt_token_ids":inp[0].tolist(),"spans":[{"index":0,"token_indices":[1,2]}]}
    with TemporaryDirectory() as tmp:
        stats=finish_capture(tr,meta,Path(tmp),True)
        mat=np.fromfile(Path(tmp)/"pooled.f32",dtype="<f4")
        assert stats["hidden_shape"]==[3,1280] and np.all(mat==13)
    assert not torch.cuda.is_initialized()
    print(json.dumps({"archive":rows,"unicode_bytes":ends[-1],"causal_pool":13,"cuda_initialized":False}))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model",type=Path)
    run(parser.parse_args().model)
