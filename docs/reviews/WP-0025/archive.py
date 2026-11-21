"""Package the released plans and actual primary operator/guard/run evidence for independent replay."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

HOST=Path("C:/Users/jackg/eLedgerCare-Speed/WP-0025")
LEASE=HOST/"coordination/leases/window-repeat-r1"


def archive(release_path, expected_digest, dest, inventory):
    raw=release_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==expected_digest
    release=json.loads(raw)
    assert release["name"]=="window-repeat-r1"
    entries={"binding/"+release_path.name:raw}
    for order in release["orders"]:
        plan=Path(order["plan"])
        raw_plan=plan.read_bytes()
        assert hashlib.sha256(raw_plan).hexdigest()==order["plan_sha256"]
        entries["binding/"+plan.name]=raw_plan
    for prefix,path in [("guard",LEASE),("runs",HOST/"review/runs"),("operator",HOST/"review/operator")]:
        for p in sorted(path.rglob("*")):
            relative=p.relative_to(path)
            if p.is_file() and "cache" not in relative.parts:
                entries[prefix+"/"+relative.as_posix()]=p.read_bytes()
    assert "guard/returned.json" in entries
    assert json.loads(entries["guard/returned.json"])["release_sha256"]==expected_digest
    with ZipFile(dest,"x") as z:
        for name,content in sorted(entries.items()):
            item=ZipInfo(name,(2026,11,21,0,0,0))
            z.writestr(item,content,compress_type=ZIP_DEFLATED,compresslevel=6)
    with ZipFile(dest) as z:
        assert z.testzip() is None and set(z.namelist())==set(entries)
        for k,v in entries.items():
            assert z.read(k)==v
    item=lambda raw: {"size":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
    inv={"archive":item(dest.read_bytes()),"release_sha256":expected_digest,
         "files":{k:item(v) for k,v in sorted(entries.items())}}
    with inventory.open("x",encoding="utf8",newline="\n") as out:
        out.write(json.dumps(inv,indent=2)+"\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("release",type=Path)
    p.add_argument("digest")
    p.add_argument("zip",type=Path)
    p.add_argument("inventory",type=Path)
    a=p.parse_args()
    archive(a.release,a.digest,a.zip,a.inventory)
