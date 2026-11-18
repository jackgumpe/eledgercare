"""Prepare document orders only after the preceding decision and surgical configuration are frozen."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
ROOT=Path("C:/Users/jackg/eLedgerCare-Speed")
PACKET=ROOT/"WP-0017"
PYTHON=Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def write(path, data):
    with path.open("x",encoding="utf8",newline="\n") as f:
        json.dump(data,f,indent=2)
        f.write("\n")


def git(worktree,*args):
    return subprocess.check_output(["git","-C",worktree,*args],text=True).strip()


def verify(wt,head,bits):
    if git(wt,"rev-parse","HEAD")!=head or git(wt,"status","--porcelain","--untracked-files=all"):
        raise ValueError("the candidate worktree or files changed")
    path=wt/"docs/research/WP-0017/engine/surgical.json"
    pinned=subprocess.check_output(["git","-C",wt,"show",head+":docs/research/WP-0017/engine/surgical.json"])
    if path.read_bytes().replace(b"\r\n",b"\n")!=pinned.replace(b"\r\n",b"\n"):
        raise ValueError("surgical mask file differs from the commit")
    cfg=read(path)
    if cfg["frozen_bits"]!=bits or len(bits)!=6 or set(bits)-{"0","1"} or bits.count("0") not in (1,2):
        raise ValueError("invalid or unbound surgical mask")
    return path


def prepare(a):
    wt=a.worktree.resolve(strict=True)
    head=git(wt,"rev-parse","HEAD")
    config=verify(wt,head,a.bits)
    approval=a.prerequisite.resolve(strict=True)
    if not approval.is_relative_to(HERE):
        raise ValueError("prerequisite evidence must be in this packet")
    rel=approval.relative_to(REPO).as_posix()
    published=subprocess.check_output(["git","-C",REPO,"show","origin/coordination/bootstrap:"+rel])
    if published!=approval.read_bytes().replace(b"\r\n",b"\n"):
        raise ValueError("unpublished prerequisite evidence")
    if not a.tag.isalnum():
        raise ValueError("use an alphanumeric run tag")
    prefix=a.stage.lower()+"-"+a.tag
    plans=PACKET/"coordination/plans"/prefix
    plans.mkdir(parents=True,exist_ok=False)
    warm=wt/"docs/research/WP-0014/eld-latency-author/A.pdf"
    short=dict(pdf=str(warm),pages=1,sha256="25c14530845cad96329b528f860032c27a1259ed46de3ccb56f0e57730aa0858",
               rgb_sha256=["a189916661ad64469762ea65a693b49c0d59ca2508df2742cc5d92b60f7dd18d"])
    assert sha(warm)==short["sha256"]
    stage2=a.stage=="A2"
    families=("dev",) if stage2 else ("H","A")
    docs=[]
    for fam in families:
        if fam=="dev":
            folder=PACKET/"review/inputs/dev-id-ablation"
            rasfile=folder/"rasters.json"
            expected=read(HERE/"a2-inputs.json")
            pdfsha=expected["pdf_sha256"]
            assert sha(rasfile)==expected["rasters_sha256"]
        else:
            folder=ROOT/"WP-0016/review/inputs"/fam
            rasfile=folder/"rasters.input.json"
            expected=read(HERE.parent/"WP-0016/g0-plans.json")["inputs"][fam]
            pdfsha=expected["files"]["source.pdf"]
            assert sha(rasfile)==expected["raster_input_sha256"]
        pdf=folder/"source.pdf"
        ref=read(rasfile)
        assert sha(pdf)==pdfsha==ref["pdf_sha256"]
        rows=sorted(ref["pages"],key=lambda r:r["page_number"])
        docs.append(dict(label="dev" if stage2 else fam.lower(),pdf=str(pdf),pages=len(rows),sha256=pdfsha,
                         rgb_sha256=[r["rgb_sha256"] for r in rows],warmup=False))
    names=["native","carbon_bf16","carbon_surgical"] if stage2 else ["native","carbon_surgical"]
    metadata=dict(gate=a.stage,source=head,frozen_bits=a.bits,prerequisite_sha256=sha(approval),
                  warm_sha256=short["sha256"],warm_rgb_sha256=short["rgb_sha256"][0],orders={})
    if not stage2:
        metadata["inputs"]=read(HERE.parent/"WP-0016/g0-plans.json")["inputs"]
    for ordname,modes in (("ab",names),("ba",list(reversed(names)))):
        run=prefix+"-"+ordname
        requests=[]
        for mode in modes:
            requests.extend(dict(short,label=f"warm-{i}",mode=mode,warmup=True) for i in range(1,4))
            requests.extend(dict(row,mode=mode) for row in docs)
        inner=plans/(run+"-engine.json")
        write(inner,dict(stage=a.stage,requests=requests))
        innerout=PACKET/"review/runs"/run
        outerout=PACKET/"review/runs"/(run+"-order")
        budget=4800 if stage2 else 5400
        args=[str(PYTHON),"-I","-B",str(wt/"docs/research/WP-0017/engine/launch.py"),"--source",head,
              "--owner","review","--run",run,"--lease",prefix,"--plan",str(inner),"--sha256",sha(inner),
              "--seconds",str(budget),"--min-vram-mib","12000"]
        checker=Path(__file__).resolve()
        outer=plans/(run+".json")
        write(outer,dict(stage=a.stage,worktree=str(wt),source=head,output=str(outerout),requests=requests,
                         bound_files={str(p):sha(p) for p in (inner,config,checker,approval)},
                         commands=[dict(label="verify-clean-frozen-surgical",argv=[str(PYTHON),"-I","-B",str(checker),
                                  "verify",str(wt),head,a.bits]),dict(label=run,argv=args,required_outputs=[str(innerout/"process.json")])]))
        metadata["orders"][ordname]=dict(path=str(inner),sha256=sha(inner),order=modes,outer_plan=str(outer),
                                         outer_sha256=sha(outer),run=run,excluded_warm_windows=len(modes)*3,
                                         scored_windows=len(modes)*sum((d["pages"]+2)//3 for d in docs))
    write(plans/"plans-record.json",metadata)
    print(plans/"plans-record.json")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    ap=p.add_subparsers(dest="action",required=True)
    chk=ap.add_parser("verify")
    chk.add_argument("worktree",type=Path)
    chk.add_argument("head")
    chk.add_argument("bits")
    prep=ap.add_parser("prepare")
    prep.add_argument("stage",choices=["A2","A3"])
    prep.add_argument("worktree",type=Path)
    prep.add_argument("tag")
    prep.add_argument("bits")
    prep.add_argument("prerequisite",type=Path)
    a=p.parse_args()
    if a.action=="verify":
        verify(a.worktree,a.head,a.bits)
    else:
        prepare(a)
