"""Record file-list/size/write-time digests for the whole external Q0 tree and content hashes for the model."""
from argparse import ArgumentParser
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"WP-0023"))
from model_receipt import inventory


def inspect(root):
    rows=[]
    groups=Counter()
    def fail(e):
        raise e
    for parent,dirs,files in os.walk(root,onerror=fail,followlinks=False):
        prefix=Path(parent).relative_to(root).as_posix()
        if prefix==".":
            prefix=""
        for is_dir,names in ((True,dirs),(False,files)):
            for name in names:
                entry=(prefix+"/" if prefix else "")+name
                stat=os.stat(os.path.join(parent,name),follow_symlinks=False)
                rows.append((entry,"d" if is_dir else "f",0 if is_dir else stat.st_size,stat.st_mtime_ns))
                groups[entry.split("/",1)[0]]+=1
    serial=json.dumps(sorted(rows),ensure_ascii=True,separators=(",",":")).encode()
    model=inventory(root/"models/Unlimited_OCR_2_04809669")
    historic=json.loads((HERE.parent/"WP-0023/model-before.json").read_bytes())
    if model!=historic:
        raise ValueError("Checkpoint differs from WP-0023 pretrial content/write-time inventory")
    return {"root":str(root),"whole_tree_entries":len(rows),"top_level_counts":dict(sorted(groups.items())),
            "namespace_size_and_mtime_sha256":sha256(serial).hexdigest(),"model_files":len(model["files"]),
            "matches_wp0023_full_model_inventory":True,
            "wp0023_model_inventory_sha256":sha256((HERE.parent/"WP-0023/model-before.json").read_bytes()).hexdigest()}


if __name__=="__main__":
    p=ArgumentParser(description=__doc__)
    p.add_argument("root",type=Path)
    p.add_argument("out",type=Path)
    p.add_argument("--compare",type=Path)
    a=p.parse_args()
    record=inspect(a.root.resolve())
    if a.compare and record!=json.loads(a.compare.read_bytes()):
        raise ValueError("Whole Q0 inventory changed")
    with a.out.open("x",encoding="utf8",newline="\n") as f:
        json.dump(record,f,indent=2)
        f.write("\n")
    print(json.dumps(record))
