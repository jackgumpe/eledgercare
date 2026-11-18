"""Prepare the two orders of the A1 release with a separate eight-window endpoint check between them."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
PACKET=Path("C:/Users/jackg/eLedgerCare-Speed/WP-0017")
Q0=Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe")
ENDPOINTS=("native","all_off","carbon_bf16","all_on")
SWITCHES=("S0","S1a","S1b","S1c","S2","S3")

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main(worktree, tag):
    if not tag.isalnum():
        raise ValueError("tag must be alphanumeric")
    worktree=worktree.resolve(strict=True)
    head=subprocess.check_output(["git","-C",worktree,"rev-parse","HEAD"],text=True).strip()
    anchor=PACKET/"coordination/a1-inputs.json"
    anchors=json.loads(anchor.read_bytes())
    if sha(anchor)!="e7f47d141972d0e32c53d16e090fcddc237c453ecfc2eaf5d494c6d3426bc8ef":
        raise ValueError("unexpected anchors")
    req=dict(anchors["request"])
    warm=dict(pages=1,pdf=str(worktree/"docs/research/WP-0014/eld-latency-author/A.pdf"),
              sha256="25c14530845cad96329b528f860032c27a1259ed46de3ccb56f0e57730aa0858",
              rgb_sha256=["a189916661ad64469762ea65a693b49c0d59ca2508df2742cc5d92b60f7dd18d"])
    folder=PACKET/"coordination/plans"/tag
    folder.mkdir(parents=True,exist_ok=False)
    modes=[("endpoints",ENDPOINTS,2700),
           ("switches",tuple(f"{kind}_{sw}" for kind in ("add","remove") for sw in SWITCHES),7200)]
    for group,configs,seconds in modes:
        name=f"a1-{tag}-{group}"
        inner=PACKET/"review/runs"/name
        outer=PACKET/"review/runs"/(name+"-order")
        argv=[str(Q0),"-I","-B",str(worktree/"docs/research/WP-0017/engine/launch.py"),
              "--source",head,"--owner","review","--run",name,"--lease","a1-"+tag,
              "--plan",str(anchor),"--sha256",sha(anchor),"--seconds",str(seconds),"--min-vram-mib","12000",
              "--warmup-count","3","--configs",",".join(configs)]
        commands=[dict(label=name,argv=argv,required_outputs=[str(inner/"process.json")])]
        files={str(anchor):sha(anchor)}
        if group=="endpoints":
            check=HERE/"check_endpoints.py"
            files[str(check)]=sha(check)
            commands.append(dict(label="require-eight-endpoint-matches",argv=[str(Q0),"-I","-B",str(check),str(inner),str(outer/"endpoint-check.json")]))
        record=dict(stage="A1",worktree=str(worktree),source=head,output=str(outer),requests=[req,warm],
                    bound_files=files,commands=commands)
        p=folder/(name+".json")
        with p.open("x",encoding="utf8",newline="\n") as f:
            json.dump(record,f,indent=2)
            f.write("\n")
        print(p,sha(p))

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worktree",type=Path)
    parser.add_argument("tag")
    a=parser.parse_args()
    main(a.worktree,a.tag)
