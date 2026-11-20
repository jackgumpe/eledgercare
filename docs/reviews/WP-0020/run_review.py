"""Post-release replay of the exact candidate and independent checks in a fresh scratch directory."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
AUTHOR = "b34c046e04ff98ddb0fb021ee8e8dade88a83126"
MANIFEST = "081acd13b7f26b3ea374a8ae3a2de79d71e9b0bf"
ROUTED = "122652984a316c9b8963ec89cf1b61dd994aaf99"
ANALYST = "8ba03b56c2f99570c50b1d4782d38081f008c5a0"
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("project_data", type=Path)
p.add_argument("archive", type=Path)
p.add_argument("scratch", type=Path)
args = p.parse_args()
data, archive, scratch = [a.resolve() for a in (args.project_data,args.archive,args.scratch)]
scratch.mkdir(parents=True,exist_ok=False)
env = os.environ.copy()
env["GIT_DIR"] = subprocess.check_output(["git","rev-parse","--absolute-git-dir"], cwd=REPO,text=True).strip()
stages = []


def extract(revision, relative):
    out = scratch/relative
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(subprocess.check_output(["git","show",revision+":"+relative],cwd=REPO))
    return out


def run(*values, save=None, isolated=True):
    args = [sys.executable,"-B", *(["-I"] if isolated else []), *map(str,values)]
    result = subprocess.run(args, cwd=REPO, env=env, capture_output=True, check=True)
    if save is not None:
        save.parent.mkdir(parents=True,exist_ok=True)
        save.write_bytes(result.stdout)
    stages.append(dict(command=args,exit_code=result.returncode,stdout=result.stdout.decode().strip() if save is None else str(save),
                       stderr=result.stderr.decode().strip()))
    return result.stdout.decode().strip()


for file in ("docs/research/WP-0019/astra/policy.py","docs/evaluation/WP-0015/score.py"):
    extract(AUTHOR,file)
route = extract(AUTHOR,"docs/research/WP-0020/route/route.py")
controls = extract(AUTHOR,"docs/research/WP-0020/route/check_route.py")
run(controls)
run(HERE/"verify_projection.py",archive,data/"windows")
for family in ("H","A"):
    own = scratch/f"{family}-manifest.json"
    cli = scratch/"cli"/family
    run(HERE/"rebuild_manifest.py",data/"windows"/family,save=own)
    assert json.loads(own.read_bytes()) == json.loads((HERE/f"{family}-manifest.json").read_bytes())
    published = extract(MANIFEST,f"docs/research/WP-0020/route/evidence/{family}/manifest.json")
    digest = run(route,"manifest",data/"windows",family,cli/"manifest.json")
    assert (cli/"manifest.json").read_bytes() == published.read_bytes()
    run(route,"route",data/"windows",family,cli/"manifest.json",digest,data/"native",cli)
    run(HERE/"verify_binding.py",family,own,data/"windows",data/"native",published,cli/"decisions.json",cli/"prediction.json")
    run(HERE/"score_archive.py",family,archive,data/"windows"/family,own,cli/"prediction.json",scratch/f"{family}-scores.json")

for path in ("docs/evaluation/WP-0015/commitments.json","docs/research/WP-0015/astra/formats.py",
             "docs/research/WP-0015/astra/sensitivity-title-level/rescore.py",
             "docs/reviews/WP-0015/evidence/H-blind-inventory.json","docs/reviews/WP-0015/evidence/A-recovery-blind-inventory.json",
             "docs/research/WP-0020/analysis/fields.py"):
    extract(ANALYST,path)
for name in ("07-boundary-native/timing.json","07-boundary-native/window-001.json","07-boundary-native/window-004.json","08-boundary-windows/timing.json"):
    extract(ANALYST,"docs/research/WP-0015/astra/evidence/dev-ab-01/"+name)
check = extract(ANALYST,"docs/research/WP-0020/analysis/check.py")
analysis = extract(ANALYST,"docs/research/WP-0020/analysis/replay.py")
run(check, isolated=False)
run(analysis,"--archive",archive,"--route-commit",ROUTED,"--scratch",scratch/"analysis-score","--out",scratch/"analysis-evidence")
run(HERE/"reconcile.py",scratch,archive,save=scratch/"verification.json")
(scratch/"commands.json").write_text(json.dumps(stages,indent=2)+"\n",encoding="utf-8")
print(f"{len(stages)} successful commands; evidence in {scratch}")
