"""Authenticate the sole exposed return against history, then inspect only PDF pages 16,17,18."""
from contextlib import closing
import json
import math
from pathlib import Path
import re
import struct
import sys
import time
from zipfile import ZipFile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT,SCRATCH,SPEED,blob,loaded,save,sha
from PIL import Image
import pypdfium2 as pdfium
from tokenizers import Tokenizer

SENSOR = "4a867f91d47c12e49e78c2381d5bc4661c6927fa"
FAIL = "d6178bb72cd250a40d8b92ff2751afa6fc0f57d7"
WITNESS = SPEED/"WP-0027/coordination/inputs/k0014"
TOKENIZER = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/models/Unlimited_OCR_2_04809669/tokenizer.json")
SENSOR_PATH = "docs/research/WP-0024/sensor/spans.py"

def tokenizer():
    assert sha(TOKENIZER.read_bytes())=="c55c165e32c5a67830362a53e1f548c8930dcc8469efa30ff3252a982799c589"
    t = Tokenizer.from_file(str(TOKENIZER))
    added={r["id"]:r["content"] for r in json.loads(TOKENIZER.read_bytes())["added_tokens"]}
    return t,lambda seq:[t.id_to_token(i) for i in seq],added

def original():
    path=ROOT/SENSOR_PATH
    assert path.read_bytes()==blob(SENSOR,SENSOR_PATH)
    sys.path.insert(0,str(path.parent))
    import spans
    spans.verify_parsers()
    return spans

def audit(pdf_pin,source_pin):
    t0=time.perf_counter()
    previous=loaded(FAIL,"docs/reviews/WP-0026/blind-c1-partial.json")["diagnostic"]
    archive=ROOT/"docs/reviews/WP-0026/blind-c1-primary/primary-001.zip"
    assert sha(archive.read_bytes())=="76d203b4c70047b2f75c254da23ca3c51616ffb09d9f540c0f31ffee49d94b0f"
    with ZipFile(archive) as z:
        prefix="runs/blind-c1-r1/sensor/k0014"
        begin_raw=z.read(prefix+"-begin.json")
        native_raw=z.read(prefix+"/native.json")
        pdf_raw=z.read("inputs/"+pdf_pin+".pdf")
    assert native_raw==(WITNESS/"native.json").read_bytes()
    assert sha(native_raw)==previous["native_sha256"]=="ce9d03a8d73ecf4366b96bc2dbbf9e129f5a2ca30265876a16b17c07cc20b169"
    begin=json.loads(begin_raw)
    n=json.loads(native_raw)
    raw,ids=n["text"],n["token_ids"]
    spans=original()
    t,vocab,added=tokenizer()
    assert t.decode(ids,skip_special_tokens=False)==raw
    ends=spans.token_bytes(raw,ids,vocab,added)
    markers=[i for i,tok in enumerate(ids) if tok==t.token_to_id("<PAGE>")]
    assert markers==[0,42,81,121]
    assert n["terminal_observation"]["nxt"]==n["eos_id"]==1 and n["eos_observed"] is True
    assert n["terminal_observation"]["step"]==len(ids)==122 and 1 not in ids and raw.endswith("<PAGE>")
    assert n["terminal_observation"]["guard"]=={"scanned":122,"marker_cum":4,"page_len":0}
    struct_ids=struct.pack("<"+"I"*(len(ids)+1),*ids,1)
    assert sha(struct_ids)==previous["derived_through_eos_u32le_sha256"]
    try:
        spans.map_window(raw,ids,vocab,added)
    except ValueError as exc:
        rejection=str(exc)
        assert rejection==previous["frozen_exception"]=="Expected three grounded native pages"
    else:
        raise AssertionError("frozen rejection disappeared")
    sraw=(WITNESS/"source.json").read_bytes()
    assert sha(sraw)==source_pin and sha(pdf_raw)==pdf_pin
    source=json.loads(sraw)
    assert source["binder"]==begin["binder"] and source["plan_sha256"]==begin["plan_sha256"]
    assert source["begin_sha256"]==sha(begin_raw) and source["source_pdf_sha256"]==pdf_pin
    assert source["archive_sha256"]==sha(archive.read_bytes()) and source["native_sha256"]==sha(native_raw)
    assert [s["page_number"] for s in source["pages"]]==[16,17,18]
    original_prefix=spans.map_window(raw[:-6],ids[:-1],vocab,added)
    checks=[]
    with pdfium.PdfDocument(pdf_raw) as pdf:
        assert len(pdf)==source["source_page_count"]
        for i,pno in enumerate((16,17,18)):
            signed=begin["pages"][i]
            s=source["pages"][i]
            png=WITNESS/f"page-{pno:03}.png"
            assert sha(png.read_bytes())==signed["sha256"]==s["png_sha256"]
            with Image.open(png) as im:
                assert im.mode=="RGB" and im.size==(2550,3300) and sha(im.tobytes())==signed["rgb_sha256"]==s["rgb_sha256"]
            with closing(pdf[pno-1]) as page:
                assert page.get_size()==(612.,792.)
                with closing(page.render(scale=math.nextafter(300/72,0))) as bmp:
                    with bmp.to_pil().convert("RGB") as im:
                        assert sha(im.tobytes())==signed["rgb_sha256"]
                with closing(page.get_textpage()) as text:
                    lines=text.get_text_bounded().splitlines()
                    assert lines==[r["text"] for r in s["source_lines"]]
                    assert lines==[r["text"] for r in original_prefix["spans"] if r["page"]==i+1]
                    bounds=[]
                    for line_info in s["source_lines"]:
                        line=line_info["text"]
                        with closing(text.search(line,match_case=True)) as search:
                            first,count=search.get_next()
                            assert search.get_next() is None
                        coords=[text.get_charbox(j) for j in range(first,first+count)]
                        box=(min(c[0] for c in coords),792-max(c[3] for c in coords),
                             max(c[2] for c in coords),792-min(c[1] for c in coords))
                        assert max(abs(a-b) for a,b in zip(box,line_info["bbox_pt_top_left"],strict=True))<0.0001
                        source_box=[round(v*999/d) for v,d in zip(box,(612,792,612,792),strict=True)]
                        assert source_box==line_info["bbox999"]
                        x,y=(box[0]+box[2])*999/(2*612),(box[1]+box[3])*999/(2*792)
                        matching=[r for r in original_prefix["spans"] if r["page"]==i+1 and r["text"]==line]
                        left,top,right,bottom=matching[0]["bbox999"]
                        assert len(matching)==1 and left<=x<=right and top<=y<=bottom
                        bounds.append(list(box))
            checks.append({"physical_page":pno,"png_sha256":signed["sha256"],"rgb_sha256":signed["rgb_sha256"],
                           "glyph_lines":lines,"glyph_boxes_pt_top_left":bounds})
    return {"runtime_seconds":time.perf_counter()-t0,"native_sha256":sha(native_raw),"source_sha256":source_pin,
            "pdf_sha256":pdf_pin,"archive_sha256":sha(archive.read_bytes()),"begin_sha256":sha(begin_raw),
            "original_rejection":rejection,"raw_utf8_sha256":sha(raw.encode()),"through_eos_sha256":sha(struct_ids),
            "marker_token_indices":markers,"marker_byte_offsets":[ends[i] for i in markers],"eos":1,
            "source_pages":checks,"accepted_feature_return":False,
            "comparison_prefix_spans":original_prefix["spans"],"trimmed_for_original_positive_control_only":True}

if __name__=="__main__":
    save(SCRATCH/sys.argv[3],audit(sys.argv[1],sys.argv[2]))

