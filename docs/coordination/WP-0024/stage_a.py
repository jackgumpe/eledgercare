"""Read the retained WP-0023 records and compare the frozen and title-projected visible tables on CPU."""
from hashlib import sha256
import json
from pathlib import Path
import sys
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PARSER = ROOT / "docs/research/WP-0015/astra"
sys.path[:0] = [str(PARSER / "sensitivity-title-level"), str(PARSER)]
from formats import native_page
from rescore import TITLE


def run():
    inputs = {
        ROOT / "docs/reviews/WP-0023/dev-r1.zip": "9d7b818fab660ef7c25ee98bd5161ea10e7d745516f9bb8ff7b796571571e2ed",
        PARSER / "formats.py": "b832a7ee452f807a01a4acaa4d63fed927241f73b75fc1a47c7ae830ce28c0a6",
        PARSER / "sensitivity-title-level/rescore.py": "86b9606468d12afff952b0b24dc7fcd1de932aa9c18400c966a3789e1609b700"}
    for path, digest in inputs.items():
        assert sha256(path.read_bytes()).hexdigest() == digest
    with ZipFile(next(iter(inputs))) as archive:
        def record(name):
            return json.loads(archive.read("run/trial/" + name + ".json"))["result"]
        stock = record("g1-stock-long")
        batches = {k: record("g2-" + k)["lanes"][slot] for k, slot in (("short-long",1),("long-short",0))}
    rows = {}
    for order, candidate in batches.items():
        assert stock["eos_observed"] and candidate["eos_observed"] and stock["eos_id"] == candidate["eos_id"] == 1
        assert len(stock["token_ids"]) == len(candidate["token_ids"]) == 665
        differences = [i for i,(a,b) in enumerate(zip(stock["token_ids"],candidate["token_ids"],strict=True)) if a!=b]
        checks = {}
        for mode in ("frozen","title-projected"):
            def project(raw):
                parts = raw.split("<PAGE>")
                assert not parts[0] and len(parts)==4
                return [native_page("<PAGE>" + (TITLE.sub(r"\1",p) if mode=="title-projected" else p), [612,792]) for p in parts[1:]]
            old, new = project(stock["text"]), project(candidate["text"])
            changed = []
            for pg,(left,right) in enumerate(zip(old,new,strict=True),7):
                for j,(x,y) in enumerate(zip(left["tables"],right["tables"],strict=True),1):
                    for i,(lx,ly) in enumerate(zip(x["rows"],y["rows"],strict=True),1):
                        for col,(cx,cy) in enumerate(zip(lx,ly,strict=True),1):
                            if cx!=cy:
                                changed.append(dict(pdf_page=pg,table=j,row=i,column=col,stock=cx,batch=cy))
            assert changed == [dict(pdf_page=8,table=1,row=1,column=2,stock="item",batch="Item")]
            checks[mode] = dict(parsed_cell_changes=changed,
                                visible_text_changed_pages=[p for p,(a,b) in enumerate(zip(old,new),7) if a["text"]!=b["text"]])
        assert differences == [84,227,316,449,537,540,543]
        rows[order] = {"changed_token_positions_zero_based":differences, "page8_header_decision_one_based":317,
                       "token_at_index316":{"b1":stock["token_ids"][316],"b2":candidate["token_ids"][316]},"parsers":checks}
    return {"packet":"WP-0024", "post_wp0023_stage":"A", "basis":"Cloud Astra's replay as reported in Jack's handoff; local archive replay",
            "source_sha256":{p.relative_to(ROOT).as_posix():s for p,s in inputs.items()}, "orders":rows,
            "disposition":"Stage A failed visible-cell identity. Close the batch follow-on. Preserve WP-0023 exact-token gate and unmodified native B=1 reference.",
            "gpu_runs":0,"stage_b_released":False}


if __name__=="__main__":
    with Path(sys.argv[1]).open("x",encoding="utf8",newline="\n") as out:
        json.dump(run(),out,indent=2)
        out.write("\n")
