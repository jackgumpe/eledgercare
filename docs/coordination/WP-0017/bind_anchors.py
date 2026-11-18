"""Derive public A1 anchors from the two historically frozen output windows without opening scoring keys."""
import hashlib
import json
from pathlib import Path
REPO=Path(__file__).resolve().parents[3]
HOME=Path(r"C:\Users\jackg\eLedgerCare-Speed")
prior=HOME/"WP-0016"/"review"
out=HOME/"WP-0017"/"coordination"/"a1-inputs.json"
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    return json.loads(p.read_bytes())
def main():
    invfile=REPO/"docs/reviews/WP-0016/evidence/G0-blind-inventory.json"
    assert sha(invfile)=="366bf5ebb7dc2527c4b11e6f110aa4c08b9f71b6f165d327565b40158bf9ac04"
    inv={a["run"]:a["files"] for a in read(invfile)["runs"]}
    src=prior/"inputs/A/source.pdf"
    ras=read(prior/"inputs/A/rasters.input.json")
    rgb=[p["rgb_sha256"] for p in sorted(ras["pages"],key=lambda x:x["page_number"])]
    assert len(rgb)==60 and ras["pdf_sha256"]==sha(src)=="671e8e18d6cf84db671ea0487be8b197e535753dabac6c1561e169654d113c5b"
    item=dict(label="a", pdf=str(src), sha256=sha(src),pages=60,rgb_sha256=rgb)
    windows=[]
    for first,ids in [(19,["I08O1-388","108O1-388"]),(37,["8OI10-774","80I10-774"])]:
        row=dict(first_page=first,identifier_page=21 if first==19 else 37,alternatives=ids,by_mode={})
        for mode in ("native","carbon_bf16"):
            copies=[]
            for order in ("g0-ab","g0-ba"):
                run=prior/"runs"/order
                file, = run.glob(f"*/05-a-{mode}/window-{first:03d}.json")
                fhash=sha(file)
                assert inv[order][file.relative_to(run).as_posix()]==fhash
                doc=read(file)
                assert doc["source_sha256"]==sha(src) and doc["first_page"]==first and doc["finish_reason"]=="stop" and doc["num_pages_out"]==3
                copies.append((doc["window_token_ids"],fhash))
            assert copies[0][0]==copies[1][0]
            row["by_mode"][mode]=dict(token_ids=copies[0][0],window_ab_sha256=copies[0][1],window_ba_sha256=copies[1][1])
        windows.append(row)
    payload=dict(stage="A1",source="c7b2ee3663317e42a0e9bdd7ff9e17f16747d2cf",inventory_sha256=sha(invfile),request=item,windows=windows)
    out.parent.mkdir(exist_ok=True,parents=True)
    with out.open("x",encoding="utf8",newline="\n") as f:
        json.dump(payload,f,indent=2)
        f.write("\n")
    print(sha(out))
if __name__=="__main__":
    main()
