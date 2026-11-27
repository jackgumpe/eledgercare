"""Independent journal, embedded sources and PDF/readback checks on final package."""
from collections import Counter
from io import BytesIO
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile

from pypdf import PdfReader
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from common import HOME,read,save,sha

WORK=HOME/"opened"
INPUT=HOME.parent/"coordination"/"inputs"
AS=WORK/"assembled-final"
ED=WORK/"repack-final"/"docs"/"editions"/"WP-0045"
R=HOME.parent/"eld-depth-author"/"complete-02.1"
PINS=read(HERE.parents[1]/"coordination"/"WP-0045"/"source-pins.json")


def outline(doc, nodes, offset):
    out=[]
    for node in nodes:
        if isinstance(node,list):
            out.append(outline(doc,node,offset))
        else:
            out.append([node.title,doc.get_destination_page_number(node)-offset,
                        *map(str,node.dest_array[1:])])
    return out


def main():
    for k,wanted in PINS.items():
        if isinstance(wanted,str):
            assert sha(INPUT/k)==wanted
    baseline=WORK/"assembled-original"
    assert all(p.read_bytes()==(R/p.name).read_bytes() for p in AS.iterdir() if p.is_file())
    original_sources=INPUT/"Edition02-source.zip"
    with ZipFile(original_sources) as original,ZipFile(baseline/"Edition02.1-source.zip") as z:
        for k in original.namelist():
            if not k.endswith("/"):
                assert z.read("edition02/"+k)==original.read(k)
        for k in ("paper-I.md","paper-II.md","paper-III.md","shared.md","model-02.1.tex","profile-02.1.json","clauses.py","fixtures.json"):
            assert z.read("edition021/"+k)==(ED/k).read_bytes()
        model=original.read("tex/model.tex")+b"\n"+(ED/"model-02.1.tex").read_bytes()
        assert model==z.read("edition021/tex/model.tex")
        profile=json.loads(original.read("profile.json"))
        profile.update(read(ED/"profile-02.1.json"))
        assert profile==json.loads(z.read("edition021/profile.json"))
    papers={}
    for roman,title in [("I","Mathematical-Specification"),("II","Integrated-Concepts"),("III","Coordinator-Handoff")]:
        orig=INPUT/f"Targeted-Depth-{roman}-{title}.pdf"
        note=ED/"papers"/f"Amendment-{roman}-02.1.pdf"
        complete=AS/f"Targeted-Depth-{roman}-Complete-02.1.pdf"
        prior,new,full=map(PdfReader,(orig,note,complete))
        n=len(new.pages)
        assert n==5 and len(full.pages)==n+len(prior.pages)
        changed_headings=["A1 / Which state","A2 / What makes","C1 / Which observation"]
        assert all(h in new.pages[j+1].extract_text() for j,h in enumerate(changed_headings))
        assert full.page_labels[n:]==prior.page_labels
        assert outline(full,full.outline[2:],n)==outline(prior,prior.outline,0)
        assert [full.get_destination_page_number(o) for o in full.outline[:2]]==[0,n]
        assert full.get_destination_page_number(full.open_destination)==0
        names={k:[prior.get_destination_page_number(v), *map(str,v.dest_array[1:])] for k,v in prior.named_destinations.items()}
        shifted={k:[full.get_destination_page_number(v)-n, *map(str,v.dest_array[1:])] for k,v in full.named_destinations.items()}
        assert names==shifted
        for k,items in prior.attachments.items():
            assert full.attachments[k]==items
        assert full.attachments[orig.name]==[orig.read_bytes()] and full.attachments[note.name]==[note.read_bytes()]
        assert full.attachments["Edition02.1-source.zip"]==[(baseline/"Edition02.1-source.zip").read_bytes()]
        assert full.attachments["Edition02.1-navigation.zip"]==[(AS/"Edition02.1-navigation.zip").read_bytes()]
        gemini=next(k for k in PINS if k.startswith("PGDA"))
        assert full.attachments[gemini]==[(INPUT/gemini).read_bytes()]
        if roman=="III":
            for j in ("I","II"):
                other=AS/f"Targeted-Depth-{j}-Complete-02.1.pdf"
                assert full.attachments[other.name]==[other.read_bytes()]
        for k in ("shared.md","model-02.1.tex","profile-02.1.json","fixtures.json",f"paper-{roman}.md","clauses.py"):
            assert new.attachments[k]==[(ED/k).read_bytes()]
        raster_diff=[]
        for j in range(len(full.pages)):
            doc,stem,directory,jj=((new,note.stem,"public-render",j) if j<n else
                                   (prior,orig.stem,"original-render",j-n))
            a,b=full.pages[j],doc.pages[jj]
            assert a.extract_text()==b.extract_text() and a.get_contents().get_data()==b.get_contents().get_data()
            assert len(a.get("/Annots",[]))==len(b.get("/Annots",[]))
            if sha(WORK/"complete-render"/f"{complete.stem}-{j:02}.png")!=sha(WORK/directory/f"{stem}-{jj:02}.png"):
                raster_diff.append(j+1)
        papers[roman]=dict(complete_sha256=sha(complete),public_sha256=sha(note),pages=len(full.pages),
                           original_pages=len(prior.pages),attachments={k:[hashlib.sha256(b).hexdigest() for b in v]
                           for k,v in full.attachments.items()},named_destinations=len(names),
                           raster_encoded_differences_one_based=raster_diff)
    save(HERE/"opening"/"papers.json",papers)
    print({k:(v["pages"],v["raster_encoded_differences_one_based"]) for k,v in papers.items()})


if __name__=="__main__":
    main()
