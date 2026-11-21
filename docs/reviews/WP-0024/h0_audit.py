"""Independent complete H0 comparison and public development PDF-to-hidden alignment witnesses."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import pypdfium2 as pdfium

sys.path.insert(0,str(Path(__file__).resolve().parent))
from span_audit import snapshot


PLAN_REVISION = "f5ff53945e11c8b0edf2da009c851768f77514ed"
PLAN = "docs/coordination/WP-0024/h0-r1-plan.json"
WITNESS = "docs/fixtures/WP-0024/h0/source-witness.json"
EXPECTED = "0bf358c54fc97f32ca213d9a1dd10cfb2838f42f7c5dcded1625c0cca1fd2f89"


def stock_words(s):
    return re.findall(r"\w+", s.casefold(),re.UNICODE)


def contains(box, point):
    x,y=point
    return box[0] <= x <= box[2] and box[1] <= y <= box[3]


def source_cells(page, items):
    observed = []
    with closing(page.get_textpage()) as text:
        for cell in items:
            # Resolve repeated PDF strings, e.g. "Item" in both directory and real header,
            # against their published glyph rectangles on the original physical page.
            x0,y0,x1,y1 = cell["source_ink_bbox_pt"]
            matches = []
            with closing(text.search(cell["literal"],match_case=True)) as search:
                while (location:=search.get_next()) is not None:
                    i,num = location
                    chars = [text.get_charbox(j) for j in range(i,i+num)]
                    bounds = (min(b[0] for b in chars),792-max(b[3] for b in chars),
                              max(b[2] for b in chars),792-min(b[1] for b in chars))
                    if max(abs(a-b) for a,b in zip(bounds,(x0,y0,x1,y1))) < 0.02:
                        matches.append(bounds)
            assert len(matches) == 1
            x0,y0,x1,y1 = matches[0]
            observed.append((cell["literal"], ((x0+x1)*999/(2*612), (y0+y1)*999/(2*792))))
    return observed


def align(w, metadata, pdf_path):
    with pdfium.PdfDocument(pdf_path) as doc:
        with closing(doc[w["page"]-1]) as p:
            source = source_cells(p,w["cells"])
    table_witness = len(source)>1
    results = []
    expected = [literal for literal,_ in source]
    for row in metadata["spans"]:
        if row["page"] != w["window_page"]:
            continue
        if table_witness and row["kind"] != "row" or not table_witness and row["kind"] != "block":
            continue
        points = [contains(row["bbox999"], pt) for _,pt in source]
        if table_witness:
            lexical = [stock_words(c) for c in row["cells"]] == [stock_words(c) for c in expected]
        else:
            want,actual = stock_words(expected[0]),stock_words(row["text"])
            lexical = any(actual[i:i+len(want)]==want for i in range(len(actual)))
        if all(points) or lexical:
            results.append(dict(index=row["index"],raw_text=row["text"],cells=row["cells"],bbox999=row["bbox999"],
                                char_range=row["char_range"],token_indices=row["token_indices"],
                                all_glyph_centers_inside=all(points),word_sequence_match=lexical))
    decisive = [r for r in results if r["all_glyph_centers_inside"] and r["word_sequence_match"]]
    return {"expected_pdf_text":expected,"binder":w["binder"],"page":w["page"],"kind":w["kind"],
            "unique_literal_and_geometry":len(decisive)==1, "candidate_rows":results}


def main():
    raw_plan = subprocess.check_output(["git","show",PLAN_REVISION+":"+PLAN])
    assert hashlib.sha256(raw_plan).hexdigest() == EXPECTED
    plan = json.loads(raw_plan)
    native_root = Path(plan["output"])/"sensor"
    load = lambda at: json.loads(at.read_bytes())
    witness_record = subprocess.check_output(["git","show",plan["candidate"]+":"+WITNESS])
    assert hashlib.sha256(witness_record).hexdigest() == "dfb55b56833599f111eb29e2b3d4b8a7de9eab13b8caae277e09c9ba60271989"
    witnesses = json.loads(witness_record)
    reads = {}
    comparisons,alignment = [],[]
    calls = {call["tag"]:call for call in plan["calls"]}
    assert len(calls) == 16 and len(set(c["binder"] for c in calls.values())) == 2
    for tag in calls:
        reads[tag] = snapshot(native_root/tag)
    selected = {}
    for group in plan["check_groups"]:
        unhooked,hooked = (native_root/group[k] for k in ("left","right"))
        order = calls[unhooked.name],calls[hooked.name]
        assert [c["hooked"] for c in order] == [False,True]
        assert order[0]["pages"] == order[1]["pages"]
        a,b = [load(d/"native.json") for d in (unhooked,hooked)]
        for k in ("prompt","prompt_token_ids","token_ids","eos_id","text","eos_observed","stop_cause",
                  "expected_pages","num_pages_out","finish_reason","terminal_observation"):
            assert a[k] == b[k], f"{hooked.name} mismatch in {k}"
        assert reads[hooked.name]["emitted"] == reads[hooked.name]["positions"]
        assert (unhooked/"metadata.json").read_bytes() == (hooked/"metadata.json").read_bytes()
        ordered_ids = a["token_ids"]+[a["eos_id"]]
        token_bytes = b"".join(i.to_bytes(4,"little") for i in ordered_ids)
        comparisons.append({"stock":unhooked.name,"hooked":hooked.name,"pre_eos":len(ordered_ids)-1,
                            "through_eos_le_u32_sha256":hashlib.sha256(token_bytes).hexdigest()})
        selected[(order[1]["binder"],order[1]["window"])] = hooked
    for w in witnesses["witnesses"]:
        binder=w["binder"]
        pdf = Path(next(r["pdf"] for r in plan["requests"] if Path(r["pdf"]).stem==binder))
        assert hashlib.sha256(pdf.read_bytes()).hexdigest() == witnesses["documents"][binder]
        alignment.append(align(w, load(selected[binder,w["window"]]/"metadata.json"), pdf))
    return {"phase":plan["phase"],"source":plan["candidate"],"plan_sha256":EXPECTED,"samples":reads,
            "comparisons":comparisons,"alignment":alignment,
            "uniquely_aligned_count":sum(w["unique_literal_and_geometry"] for w in alignment)}


if __name__ == "__main__":
    assert sys.flags.isolated and sys.dont_write_bytecode
    print(json.dumps(main(),indent=2))

