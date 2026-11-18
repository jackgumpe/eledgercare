"""CPU-only render/link/publish controls. Generates release plans without starting an OCR model."""
import argparse
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from trial import ROOT, document, inputs
from formats import digest, native_page, publish
from visual import Visual, rule_tables
from cases import PYTHON


def plan_rows(custody):
    probe=ROOT/"docs/research/WP-0014/eld-latency-author"
    warm=probe/"A.pdf"
    rows={"warm":dict(label="warm",pdf=str(warm),pages=1,warmup=True,
            sha256="25c14530845cad96329b528f860032c27a1259ed46de3ccb56f0e57730aa0858",
            rgb_sha256=["a189916661ad64469762ea65a693b49c0d59ca2508df2742cc5d92b60f7dd18d"])}
    for family in ("short","dense","boundary"):
        source=(custody/"dev"/family/"source.pdf").resolve()
        manifest=json.loads(source.with_name("rasters.json").read_bytes())
        rows[family]=dict(label=family,pdf=str(source),pages=len(manifest["pages"]),warmup=False,
            sha256=manifest["pdf_sha256"],rgb_sha256=[p["rgb_sha256"] for p in manifest["pages"]])
    return rows


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument("custody",type=Path)
    p.add_argument("out",type=Path)
    args=p.parse_args()
    out=args.out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    rows=plan_rows(args.custody)
    def plan(name,pairs):
        return publish(out/(name+".json"),dict(requests=[dict(**rows[k],mode=m) for k,m in pairs]))
    plans={"initial":plan("initial",[(k,"native") for k in rows])}
    for name,modes in (("ab",("native","windows")),("ba",("windows","native"))):
        plans[name]=plan(name,[(k,m) for k in rows for m in modes])
    import pypdfium2
    checked={}
    for k,r in rows.items():
        pdf=Path(r["pdf"]).read_bytes()
        assert digest(pdf)==r["sha256"]
        with pypdfium2.PdfDocument(pdf) as doc:
            got=inputs(doc,0,len(doc),r)
            checked[k]=[]
            for row in got:
                grids=rule_tables(row["image"],row["points"])
                checked[k].append(dict(page=row["page"],rgb=row["rgb_sha256"],grids=[(len(g["ys"])-1,len(g["xs"])-1) for g in grids]))
                row["image"].close()
    class Plumbing:
        window=3
        def read(self,pages,folder):
            return [(dict(text="",spans=[],tables=[]),dict(test_double=True)) for _ in pages],dict(test_double=True)
    record=document(rows["boundary"],Plumbing(),out/"plumbing-only","CPU plumbing test double; no OCR")
    assert record["complete_pages"]==4 and len(list((out/"plumbing-only").glob("window-*.json")))==2
    try:
        document(dict(rows["short"],sha256="0"*64),Plumbing(),out/"bad-source","test")
        raise AssertionError("accepted changed source")
    except ValueError as exc:
        assert "frozen release" in str(exc)
    try:
        publish(out/"initial.json",b"second publication")
        raise AssertionError("destination was overwritten")
    except OSError:
        assert digest((out/"initial.json").read_bytes())==plans["initial"]
    native=native_page("<PAGE><BLOCK>table[0,0,999,999]<FORK><table><tr><td>A</td><td></td></tr></table>",(612,792))
    assert native["tables"]==[dict(bbox=[0,0,612,792],rows=[["A",""]])]
    engine=Visual(out)
    try:
        end=dict(plans=plans,rendered=checked,visual_start=engine.info,
                 checks=["frozen PDFs and all RGB digests","window split and durable ordered publication",
                         "bad source refused","duplicate publication refused","native 999 bbox + empty cell","recognizer initialized; zero recognition calls"])
        publish(out/"prep.json",end)
        print(json.dumps(end))
    finally:
        engine.close()


if __name__=="__main__":
    main()
