"""Check the finite-epsilon score and value attribution directly from the sealed operators' vectors."""
import argparse
import json
import math
from pathlib import Path
# Isolated Python excludes the script directory from its import path.
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from compare_rows import CELLS, budget, document, dot, effects, unpack


def checked(a, b):
    assert abs(a-b) <= budget(a,b), (a,b)
    return abs(a-b)


def verify(author, reviewer):
    arows = document(author, "docs/research/WP-0033/evidence/M3.json")["rows"]
    vrows = document(reviewer, "docs/reviews/WP-0033/evidence/M3.json")["rows"]
    historical = document("8f31cc66c4878ca086fa5da1498c4a73ed6a6306","docs/research/WP-0031/evidence/M3.json")
    a = {r["cell"]:r for r in arows}
    b = {r["cell"]:r for r in vrows}
    assert set(a)==set(b)==set(CELLS)
    anchors = unpack(historical["sources"]["Alder"]["ordered_anchors_f32le"],"f")
    axes = {"Alder":anchors[:128],"Cedar":anchors[128:],
            "margin":[x-y for x,y in zip(anchors[:128],anchors[128:],strict=True)]}
    results = {}
    for cell in CELLS:
        p,r = a[cell],b[cell]
        typed = p["projected"]
        for name, key in (("key","k"),("value","v"),("alpha","alpha"),("beta","beta")):
            assert typed[name]["bytes"]==r["inputs"]["projection_f32le"][key]
        assert p["input_binding"]["encoded_box"]["bytes"] == r["inputs"]["encoded_box_f32le"]
        assert p["input_binding"]["all_pooled_rows_sha256"] == r["inputs"]["pooled_window_sha256"]
        assert p["input_binding"]["full_block_sha256"] == r["inputs"]["blocks_f32le_sha256"]
        q = unpack(historical["sources"]["Alder"]["frozen_query_f32le"],"f")[:32]
        k = unpack(typed["key"]["bytes"],"f")[:32]
        v = unpack(typed["value"]["bytes"],"f")
        vf = unpack(p["pooled_value"]["bytes"],"d")
        vb = unpack(p["box_value"]["bytes"],"d")
        split_error = max(checked(x,y+z) for x,y,z in zip(v,vf,vb,strict=True))
        beta, = unpack(typed["beta"]["bytes"],"f")
        eps = 1e-8
        z = dot(k,q)/(math.sqrt(dot(q,q))+eps)
        t = beta*z
        wn = math.sqrt(dot(v,v))
        den = abs(t)*wn + eps
        attenuation = abs(t)*wn/den
        rec = {"z":z,"beta":beta,"t":t,"value_norm":wn,"read_denominator":den,
               "epsilon":eps,"effective_epsilon":eps/abs(t) if t else None,"attenuation":attenuation,
               "max_split_vector_residual":split_error,"axes":{}}
        for v1,v2 in ((z,r["m3"]["z"]),(t,r["m3"]["t"]["observed"]),(attenuation,r["m3"]["attenuation"]),
                      (attenuation,p["finite_epsilon_factor_on_unit_value_direction"])):
            checked(v1,v2)
        scores = unpack(r["parity"]["score_f32le"],"f")
        for i,(name,w) in enumerate(axes.items()):
            raw, f, box = dot(w,v),dot(w,vf),dot(w,vb)
            native = scores[i] if i < 2 else scores[0]-scores[1]
            predicted = t*raw/den
            author_axis = p["alignments"]["h" if name=="margin" else name]
            review_axis = r["m3"]["axes"][name]
            checked(raw,author_axis["total"])
            checked(raw,review_axis["raw"]["observed"])
            checked(f,review_axis["feature"])
            checked(box,review_axis["box"])
            checked(raw,f+box)
            residual = checked(native,predicted)
            rec["axes"][name] = {"raw":raw,"pooled":f,"box":box,"native_score":native,
                                "finite_epsilon_score":predicted,"absolute_residual":residual}
        results[cell]=rec
    by_axis = {}
    for axis in axes:
        raw = {c:results[c]["axes"][axis]["raw"] for c in CELLS}
        native = {c:results[c]["axes"][axis]["native_score"] for c in CELLS}
        raw_effects = effects(raw)
        ae,ce=(results[t]["axes"][axis] for t in ("AA","CC"))
        f=ae["pooled"]-ce["pooled"]
        box=ae["box"]-ce["box"]
        for name in ("feature_at_A_box","feature_at_C_box","box_at_A_feature","box_at_C_feature","interaction","diagonal"):
            target = f if name.startswith("feature") else box if name.startswith("box") else 0 if name=="interaction" else f+box
            e = raw_effects[name]
            assert abs(e["value"]-target)<=e["zero_budget"]
        by_axis[axis]={"linear_pooled_effect":f,"linear_box_effect":box,"raw":raw_effects,"normalized":effects(native)}
    return {"author_evidence":author,"independent_evidence":reviewer,"cells":results,"conditional_effects":by_axis}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("author")
    parser.add_argument("reviewer")
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    report=verify(args.author,args.reviewer)
    with args.output.open("x",encoding="utf-8",newline="\n") as f:
        json.dump(report,f,indent=2,allow_nan=False)
        f.write("\n")
