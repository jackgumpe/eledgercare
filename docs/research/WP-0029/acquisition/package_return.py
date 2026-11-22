"""Journal the unique issued order and archive every reached raw boundary after its terminal return."""
import argparse
import json
import os
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (DEVICE, HERE, LEASE, MAIN, ROOT, RUN, SCRATCH, check_env, checked, file_sha, freeze,
                    json_bytes, keep, require, sha, text_cmd, utc)

BIND = MAIN/"docs/coordination/WP-0029"
PLAN = BIND/"cedar-r1-plan.json"
RELEASE = BIND/"cedar-r1-release.json"

def journal(args):
    require(not RUN.exists() and not LEASE.exists() and not (HERE/"native-return.zip").exists(),
            "Evidence already exists: check the attempt record before issuing anything")
    checked(PLAN,args.plan_sha)
    checked(RELEASE,args.release_sha)
    require(text_cmd(["git","-C",str(DEVICE),"rev-parse","HEAD"])==args.candidate, "Wrong device HEAD")
    require(not text_cmd(["git","-C",str(DEVICE),"status","--porcelain","--untracked-files=all"]),
            "Device tree is dirty")
    require(args.command and args.command[-1]==args.release_sha, "Missing exact released invocation")
    before=json.loads((SCRATCH/"prepare.json").read_bytes())
    require(before["q0"]["model_bytes"]==6699195181 and before["inputs"]["logical_windows"]==28,
            "Missing verified model and development inputs")
    keep(SCRATCH/"issuance.json", dict(utc=utc(), state="operator issuance intent recorded before invoking supervisor",
         operator_source=freeze(), device_candidate=args.candidate, reviewer_preflight=args.review,
         plan_sha256=args.plan_sha,release_sha256=args.release_sha,prepare_sha256=file_sha(SCRATCH/"prepare.json"),
         cwd=str(args.cwd),argv=args.command,lease=str(LEASE),native_output=str(RUN),retry_budget=0))

def files_below(folder):
    if folder.exists():
        require(folder.resolve(strict=True)==folder, "Unexpected redirection at " + str(folder))
        for parent, dirs, files in os.walk(folder):
            base=Path(parent)
            dirs[:] = sorted(d for d in dirs if d not in {"cache","__pycache__"})
            for d in dirs:
                require((base/d).resolve(strict=True)==base/d, "Redirected evidence directory")
            for name in sorted(files):
                path=base/name
                require(path.resolve(strict=True)==path, "Redirected evidence file")
                yield path.relative_to(folder).as_posix(), path

def package(exit_code):
    issue=json.loads((SCRATCH/"issuance.json").read_bytes())
    checked(PLAN,issue["plan_sha256"])
    checked(RELEASE,issue["release_sha256"])
    items={**dict(files_below(RUN)), **{"lease/"+k:v for k,v in files_below(LEASE)}}
    items.update({"binding/"+p.name:p for p in (PLAN,RELEASE)})
    items["operator/issuance.json"]=SCRATCH/"issuance.json"
    items["operator/supervisor-terminal.json"]=SCRATCH/"supervisor-terminal.json"
    actual_exit=json.loads(items["operator/supervisor-terminal.json"].read_bytes())
    require(actual_exit["exit_code"]==exit_code, "Inconsistent supervisor return")
    inventory={}
    dest=HERE/"native-return.zip"
    temp=SCRATCH/"native-return.partial.zip"
    with ZipFile(temp,"x",compression=ZIP_DEFLATED,compresslevel=4) as z:
        for key, path in sorted(items.items()):
            data=path.read_bytes()
            inventory[key]={"bytes":len(data),"sha256":sha(data)}
            z.writestr(key,data)
    with ZipFile(temp) as z:
        require(z.namelist()==sorted(items) and all(z.read(k)==p.read_bytes() for k,p in items.items()),
                "Raw ZIP did not reproduce the physical bytes")
    require(not dest.exists(), "Published return already exists")
    # Both scratch and repository lie on the same Windows drive. Rename the sealed archive once.
    temp.rename(dest)
    stage=["sensor/binding.json","sensor/cold.json","sensor/warmup-begin.json","sensor/warmup.json",
           "sensor/k0001-begin.json","sensor/k0001/native.json","sensor/k0001/metadata.json",
           "sensor/k0001/pooled.f32","sensor/k0001/through-eos.u32le","sensor/k0001/receipt.json",
           "sensor/outcome.json"]
    reached=[k for k in stage if k in items]
    row=dict(archive=dest.name,sha256=file_sha(dest),bytes=dest.stat().st_size,members=inventory,
             operator_source=issue["operator_source"],device_candidate=issue["device_candidate"],
             exit_code=exit_code, archived_utc=utc(), native_artifacts_reached_in_protocol_order=reached,
             last_retained_native_boundary=(reached[-1] if reached else None),
             failures_or_stops=[k for k in items if any(s in k.lower() for s in ("error","stop","failure"))],
             scope="Physical raw evidence including partial artifacts. Independent authentication pending.")
    keep(HERE/"evidence/native-inventory.json",row)
    print(row["sha256"],len(inventory),row["last_retained_native_boundary"])

def main():
    check_env()
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="step",required=True)
    start=sub.add_parser("intent")
    start.add_argument("candidate")
    start.add_argument("plan_sha")
    start.add_argument("release_sha")
    start.add_argument("review")
    start.add_argument("cwd",type=Path)
    start.add_argument("command",nargs=argparse.REMAINDER)
    returned=sub.add_parser("returned")
    returned.add_argument("exit_code",type=int)
    args=p.parse_args()
    if args.step=="intent":
        journal(args)
    else:
        keep(SCRATCH/"supervisor-terminal.json",dict(observed_utc=utc(),exit_code=args.exit_code,
             layer="exact released supervisor process, observed by dispatching operator"))
        package(args.exit_code)

if __name__=="__main__":
    main()
