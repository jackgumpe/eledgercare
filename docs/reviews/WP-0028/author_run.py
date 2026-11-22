"""Materialize just the named candidate and eligible local imports under review scratch."""
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BASE, HISTORY, ROOT, WORK, blob

def stage(kind, candidate, run_name, fixture=None):
    dest=WORK/(kind+"-source-"+candidate[:12])
    dest.mkdir(parents=True,exist_ok=True)
    if not (dest/".git").exists():
        subprocess.run(["git","init","--quiet",str(dest)],check=True)
    common=subprocess.check_output(["git","rev-parse","--path-format=absolute","--git-common-dir"],cwd=ROOT,text=True).strip()
    (dest/".git/objects/info/alternates").write_text(Path(common,"objects").as_posix()+"\n",encoding="utf8")
    sub="docs/fixtures/WP-0028" if kind=="fixtures" else "docs/research/WP-0028"
    sources=[(candidate,p) for p in subprocess.check_output(["git","ls-tree","-r","--name-only",candidate,"--",sub],cwd=ROOT,text=True).splitlines()
             if p.endswith((".py",".md",".ps1"))]
    if kind=="fixtures":
        sources += [(BASE,"docs/reviews/WP-0024/"+f) for f in ("stage_a.py","span_audit.py")]
        sources += [(BASE,"docs/reviews/WP-0026/"+n+"-primary/primary-001.zip")
                    for n in ("h0","cal-features","train-c1","train-features")]
    else:
        sources += [(HISTORY,"docs/research/WP-0027/owners/"+f) for f in ("inputs.py","observe.py")]
    for rev,name in sources:
        path=dest/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(blob(rev,name))
    if kind=="fixtures":
        cmd=[sys.executable,"-I","-B",str(dest/sub/"build.py"),str(WORK/run_name)]
    else:
        cmd=["pwsh","-NoProfile","-File",str(dest/sub/"run.ps1"),"-Role","review","-RunName",run_name,
             "-Mode",kind,"-Candidate",candidate]
        if fixture:
            cmd+=["-FixtureRevision",fixture]
    subprocess.run(cmd,cwd=dest,check=True)
if __name__=="__main__":
    stage(*sys.argv[1:])
