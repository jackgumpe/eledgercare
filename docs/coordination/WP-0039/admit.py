"""Authenticate WP-0038 decisions and construct the input visible to a planner."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

BASE = "5cd88ed3f38dd23102045cb8c32580b310dc1424"
PREFIX = "docs/coordination/WP-0038/"
DIGESTS = {"grid":"31c7caa313ea4f1d2f559d2df792f50c8790d8821e4345ae45d63ab4b72319eb",
           "named":"482719a0dcc129524adb8644fe424cd541a6549921b5fdfc89e7c2a98b1687d8"}


def encoded(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False).encode()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def blob(path):
    return subprocess.check_output(["git","cat-file","blob",BASE+":"+path])


def admitted():
    receipt = json.loads(blob(PREFIX+"publication-receipt.json"))["downloaded_files"]
    roles = []
    for area in ("research","reviews"):
        name = "docs/"+area+"/WP-0038/evidence/run-01/outputs.jsonl"
        raw = blob(name)
        assert sha(raw)==receipt[name]["sha256"]
        roles.append([json.loads(b)["answer"] for b in raw.splitlines()])
    records = []
    used = set()
    custody = {}
    for group,size in (("grid",288),("named",20)):
        name = PREFIX+"results/"+group+".jsonl"
        data = blob(name)
        assert sha(data)==DIGESTS[group]==receipt[name]["sha256"]
        rawrows = data.splitlines()
        assert len(rawrows)==size
        custody[group] = {"path":name,"sha256":sha(data),"git_blob":receipt[name]["git_blob"],"records":size}
        for line in rawrows:
            row = json.loads(line)
            ans,up = row["answer"],row["operator_row"]
            assert encoded(ans)==encoded(roles[0][up])==encoded(roles[1][up])
            assert not row["failures"] and row["signed_outputs_equal"] and row["section"]==group and up not in used
            used.add(up)
            o = row["observed"]
            n = len(o["amounts"])
            start = 1 if o["domain"]=="TRUSTED_OPEN" else 0
            names = [f"A{i}" for i in range(1,n+1)]+[f"B{i}" for i in range(start,n+1)]+["T"]
            values = o["amounts"]+o["balances"][start:]+[o["total"]]
            view = {"mutable":names,"observed":values,"answer":ans}
            tag = {k: row[k] for k in ("id","section","variant","generated_grid_id")}
            tag.update(n=n,domain=o["domain"],upstream_line_sha256=sha(line),upstream_operator_row=up)
            records.append((tag,view))
    assert len(used)==308 and {len(r) for r in roles}=={308}
    # Interface-only sentinels. The empty record is supplied as a candidate API state.
    # Neither sentinel describes an additional observation from WP-0038.
    empty = dict(status="ADMITTED", anchor_status="VERIFIED", solve_skipped=False, rho=[1],D=1,
                 clean=False, finite=[],families=[])
    for label,status in (("empty","ADMITTED"),("unsupported","UNRECOGNIZED_UPSTREAM_STATUS")):
        records.append((dict(section="interface",id=label,variant="",domain=None,n=None),
                        dict(mutable=["A1","B1","T"],observed=[11,111,11],answer=dict(empty,status=status))))
    records.sort(key=lambda kv: hashlib.sha256(b"WP0039-order\0"+encoded(kv[0])).digest())
    return records,custody


def batch(records):
    return b"".join(encoded(view)+b"\n" for _,view in records)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("out",type=Path)
    opts=cli.parse_args()
    records,refs=admitted()
    data=batch(records)
    with opts.out.open("xb") as f:
        f.write(data)
    print(json.dumps(dict(inputs=refs,records=len(records),input_sha256=sha(data))))
