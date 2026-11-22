"""Run independent synthetic and archived checks on a hash-fixed reader. No native inference."""
from copy import deepcopy
import io
import json
from pathlib import Path
import struct
import sys
import time
from zipfile import ZipFile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT,SCRATCH,blob,save,sha
from reader_expectations import CASES,Case
from witness import WITNESS,original,tokenizer
from PIL import Image,ImageDraw

CANDIDATE = "67e0898e09ee9fc848677990850f9320a7d3cd6f"
AUTHORITY = {
    "p":("Ångström 38",), "q":("Repair bay 2","Québec 714"), "r":("Safety register",),
    "s":("Foreign source",), "empty":()
}
EXTRA=(
    Case("synthetic simple table/ordinary", ("p","q_table","r"),allowed="A"),
    Case("synthetic simple table/exception", ("p","q_table","r","empty"),allowed="E"),
    Case("unsupported inline markup", ("p","q_html","r","empty")),
    Case("unseen visible text omitted from binding/exception", ("p","q","r","empty"), binding="hidden_ink"),
    Case("source raster contains untranscribed text/ordinary", ("p","q","r"), binding="hidden_ink"),
    Case("missing transcript despite four markers", ("p","q","r","empty"),binding="no_transcript"),
    Case("two identical source pages", ("p","q","q","empty"),("p","q","q")),
    Case("wrong EOS observation index",("p","q","r","empty"),binding="bad_index"),
)
def encode(j):
    return (json.dumps(j,ensure_ascii=False,sort_keys=True)+"\n").encode()

def pages(labels,hidden=False):
    ps,imgs=[],[]
    for i,label in enumerate(labels):
        image=Image.new("RGB",(512,256),"white")
        drawing=ImageDraw.Draw(image)
        lines=[]
        for j,literal in enumerate(AUTHORITY[label]):
            position=(42,22+80*j)
            drawing.text(position,literal,fill="black")
            box=drawing.textbbox(position,literal)
            coords=[round(999*v/image.size[n%2],6) for n,v in enumerate(box)]
            lines.append({"text":literal,"bbox999":coords})
        if hidden and i==1:
            drawing.text((40,205),"Additional line visible on this source.",fill="black")
        buf=io.BytesIO()
        image.save(buf,format="PNG")
        raw=buf.getvalue()
        imgs.append(raw)
        ps.append({"page":i+31,"png_sha256":sha(raw),"rgb_sha256":sha(image.tobytes()),"size":list(image.size),"lines":lines})
    return ps,imgs

def body(label):
    if label in AUTHORITY:
        return "".join(f"<BLOCK>text[55,{40+300*j},820,{250+300*j}]<FORK>{v}\n" for j,v in enumerate(AUTHORITY[label]))
    if label=="qr": return body("q")+body("r")
    if label=="q_partial": return body("q").split("\n")[0]+"\n"
    if label=="q_unmapped": return "not grounded\n"+body("q")
    if label=="q_html": return body("q").replace("Québec 714","<em>Québec 714</em>")
    if label=="q_table":
        return ("<BLOCK>table[55,40,820,550]<FORK><table>"
                "<tr><td>Repair bay</td><td>2</td></tr><tr><td>Québec</td><td>714</td></tr></table>\n")
    return {"literal":"ticket","space":" ","newline":"\n","markup":"<i></i>"}[label]

def test(reader,t,vocab,added,old,c,prompt):
    raw="".join("<PAGE>"+body(label) for label in c.sections)
    ids=t.encode(raw,add_special_tokens=False).ids
    markers=[i for i,v in enumerate(ids) if v==128827]
    native=dict(text=raw,token_ids=ids,prompt_token_ids=prompt,eos_id=1,eos_observed=c.eos,
                stop_cause="eos" if c.eos else "length",finish_reason="stop" if c.eos else "length",
                expected_pages=3,num_pages_out=len(markers),terminal_observation=dict(nxt=1,
                    step=len(ids)+int(c.binding=="bad_index"),prompt_length=len(prompt),
                    guard=dict(scanned=len(ids),marker_cum=len(markers),page_len=len(ids)-1-markers[-1])))
    data=encode(native)
    ps,images=pages(c.source,hidden=c.binding=="hidden_ink")
    binding={"schema":"wp0027-reader-binding-v1","call":"review/"+c.name,"document_sha256":sha(encode(ps)),
             "native_sha256":sha(data),"pages":ps}
    if c.binding=="no_transcript":
        binding["pages"][1]["lines"]=[]
    signed=encode(binding)
    pin=sha(signed)
    if c.binding=="foreign_page": images[-1]=pages(("s",))[1][0]
    if c.binding=="wrong_order": images[0],images[1]=images[1],images[0]
    if c.binding=="foreign_pdf": signed=encode(dict(binding,document_sha256=sha(b"different document")))
    answer=reader.map(data,signed,pin,images)
    actual={"ordinary":"A","one_empty_terminal_marker":"E"}.get(answer["reason"],"U")
    assert (answer["decision"]=="accepted")==(actual in "AE")
    result={"case":c.name,"expected":c.allowed,"actual":actual,"reason":answer["reason"],
            "native_sha256":sha(data),"binding_sha256":sha(signed),"trusted_binding_sha256":pin,
            "ordered_images":[sha(im) for im in images],"match":actual in c.allowed}
    if actual in "AE":
        cut=markers[-1] if actual=="E" else len(ids)
        bound=raw[:-6] if actual=="E" else raw
        prior=old.map_window(bound,ids[:cut],vocab,added)
        assert answer["projection"]==prior and answer["observation"]["ids_through_eos"]==ids+[1]
        assert answer["observation"]["observed_eos"]["token_index"]==len(ids)
        assert [m["source"]["page"] for m in answer["source_to_section"]]==[31,32,33]
        selections=[]
        edges=old.token_bytes(raw,ids,vocab,added)
        for span in prior["spans"]:
            lo,hi=span["char_range"]
            b0,b1=span["byte_range"]
            assert raw[lo:hi].encode()==raw.encode()[b0:b1]
            indices=[i for i,(l,r) in enumerate(zip(edges,edges[1:])) if r>b0 and l<b1]
            assert indices==span["token_indices"] and set(indices).isdisjoint(markers)
            selections.append({"kind":span["kind"],"page":span["page"],"bytes":[b0,b1],"chars":[lo,hi],
                               "emitted_positions":indices,"absolute_positions":[len(prompt)+i for i in indices]})
        if actual=="E":
            delimiter=answer["unused_delimiter"]
            assert delimiter["token_range"]==[cut,cut+1] and delimiter["byte_range"]==[len(bound.encode()),len(raw.encode())]
            assert delimiter["disposition"]=="retained_unassigned"
        result["verified_span_positions"]=selections
    return result

def development(rund):
    checks=[]
    path=ROOT/"docs/reviews/WP-0024/h0-r1.zip"
    assert sha(path.read_bytes())=="37670af4116f543e2d0104b5d3599d88f2e2d06fc092418ee1cf839769430fc6"
    with ZipFile(path) as z:
        for tag in ("b01w01H","b01w02H"):
            data=json.loads((rund/(tag+".json")).read_bytes())
            root="run/sensor/"+tag+"/"
            positions=json.loads(z.read(root+"observed-positions.json"))
            meta=json.loads(z.read(root+"metadata.json"))
            candidate=data["candidate"]["projection"]
            assert all(v==meta[k] for k,v in candidate.items())
            for row in data["feature_position_selections"]:
                indices=meta["spans"][row["span"]]["token_indices"]
                assert row["absolute_positions"]==[positions["absolute_positions"][i] for i in indices]
            checks.append({"tag":tag,"unchanged_spans":len(candidate["spans"]),
                           "unchanged_pages":len(candidate["pages"]),"features":len(data["feature_position_selections"]),
                           "archive_positions_sha256":sha(z.read(root+"observed-positions.json"))})
    return checks

def audit(candidate=CANDIDATE, run="reader-replay-01"):
    start=time.perf_counter()
    checkout=SCRATCH/"reader-source/docs/research/WP-0027/reader"
    for f in ("reader.py","replay.py","fixtures.py","POLICY.md","run.ps1"):
        assert (checkout/f).read_bytes()==blob(candidate,"docs/research/WP-0027/reader/"+f)
    sys.path.insert(0,str(checkout))
    from reader import Reader
    reader=Reader()
    t,vocab,added=tokenizer()
    old=original()
    witness_record=json.loads((WITNESS/"native.json").read_bytes())
    prompt=witness_record["prompt_token_ids"]
    rows=[test(reader,t,vocab,added,old,c,prompt) for c in (*CASES,*EXTRA)]
    folder=SCRATCH/run/"results"
    actual=json.loads((folder/"k0014.json").read_bytes())["candidate"]
    ref=json.loads((SCRATCH/"witness-r1.json").read_bytes())
    assert actual["decision"]=="accepted" and actual["native_sha256"]==ref["native_sha256"]
    assert actual["observation"]["ids_through_eos_u32le_sha256"]==ref["through_eos_sha256"]
    assert actual["projection"]["spans"]==ref["comparison_prefix_spans"]
    assert [page["source"]["page"] for page in actual["source_to_section"]]==[16,17,18]
    assert [page["source"]["rgb_sha256"] for page in actual["source_to_section"]]==[p["rgb_sha256"] for p in ref["source_pages"]]
    assert actual["unused_delimiter"]["token_range"]==[121,122] and actual["unused_delimiter"]["byte_range"]==[356,362]
    return {"candidate":candidate,"seconds":time.perf_counter()-start,"cases":rows,
            "mismatches":[r["case"] for r in rows if not r["match"]],
            "development":development(folder),"k0014_equality":"original authenticated pixels, spans, raw IDs through EOS, delimiter offsets",
            "observed_feature_return_for_k0014":False}

if __name__=="__main__":
    save(SCRATCH/sys.argv[1],audit(*sys.argv[2:]))
