"""Verify all four fresh A1 endpoints against the committed, pre-key WP-0016 predictions."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO=Path(__file__).resolve().parents[3]
HOME=Path("C:/Users/jackg/eLedgerCare-Speed")
ANCHOR=HOME/"WP-0017/coordination/a1-inputs.json"
ANCHOR_SHA="e7f47d141972d0e32c53d16e090fcddc237c453ecfc2eaf5d494c6d3426bc8ef"
INV=REPO/"docs/reviews/WP-0016/evidence/G0-blind-inventory.json"
INV_SHA="366bf5ebb7dc2527c4b11e6f110aa4c08b9f71b6f165d327565b40158bf9ac04"
EXPECTED={"native":"native","all_off":"native","carbon_bf16":"carbon_bf16","all_on":"carbon_bf16"}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    return json.loads(p.read_bytes())

def audit(directory):
    if sha(ANCHOR)!=ANCHOR_SHA or sha(INV)!=INV_SHA:
        raise ValueError("frozen origins changed")
    bound=read(ANCHOR)
    roots=HOME/"WP-0016/review/runs/g0-ab"
    inventories=next(r["files"] for r in read(INV)["runs"] if r["run"]=="g0-ab")
    checked=[]
    for mode,base in EXPECTED.items():
        segment,=directory.glob(f"segment-??-{mode}")
        child=read(segment/"child.json")
        if child["mode"]!=mode:
            raise ValueError("mode mismatch "+mode)
        for w in bound["windows"]:
            start=w["first_page"]
            name=f"window-{start:03d}.json"
            current=read(segment/"free"/name)
            old,=roots.glob(f"*/05-a-{base}/{name}")
            if sha(old)!=inventories[old.relative_to(roots).as_posix()]:
                raise ValueError("historical origin changed")
            historical=read(old)
            expected=w["by_mode"][base]["token_ids"]
            actual=current["window_token_ids"]
            errors=[]
            if current["source_sha256"]!=bound["request"]["sha256"] or current["first_page"]!=start:
                errors.append("source link")
            if current["pages"]!=3 or current["num_pages_out"]!=3 or current["finish_reason"]!="stop":
                errors.append("page count/stop")
            if current["eos_id"] in actual or historical["window_token_ids"]!=expected or actual!=expected:
                errors.append("token/EOS parity")
            for i in range(start,start+3):
                raw=f"raw-{i:03d}.json"
                prior=old.parent/raw
                if sha(prior)!=inventories[prior.relative_to(roots).as_posix()]:
                    raise ValueError("historical page changed")
                got=read(segment/"free"/raw)
                exp=read(prior)
                for k in ("source_sha256","page","rgb_sha256","token_ids","raw_output"):
                    if got[k]!=exp[k]:
                        errors.append(f"{i}/{k}")
            first=next((i for i,(x,y) in enumerate(zip(actual,expected)) if x!=y),None)
            if first is None and len(actual)!=len(expected):
                first=min(len(actual),len(expected))
            checked.append(dict(mode=mode,first_page=start,tokens=len(actual),expected_tokens=len(expected),first_mismatch=first,errors=errors))
    if len(checked)!=8:
        raise ValueError("four endpoints times two windows required")
    return dict(checks=checked,passed=all(not x["errors"] for x in checked))

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory",type=Path)
    p.add_argument("out",type=Path)
    a=p.parse_args()
    record=audit(a.directory)
    with a.out.open("x",encoding="utf8") as f:
        json.dump(record,f,indent=2)
    sys.exit(0 if record["passed"] else 1)
