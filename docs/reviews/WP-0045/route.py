"""Blind harness and ordinary CLI. Native evidence requires the limited interactive-user entry."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import hashlib
import json
import os
import time
import traceback
from clauses import branch, scores, query, provenance
from common import BASE, HERE, HOME, OLD, SCHEDULE, ENV_KEYS, clean_env, image_id, ordinary, read, runtime, save, sha
from native import collect
from history import compare_old

HIST=HERE.parents[1]/"coordination"/"WP-0044"/"disposition.json"
ATOMS=read(SCHEDULE)["atoms"]


def manifest():
    cfg=runtime()
    cfg["env"]={k:clean_env().get(k) for k in ENV_KEYS}
    return dict(sources={p.name:sha(p) for p in sorted(HERE.glob("*.py"))},runtime=cfg,
                image=image_id(), wp44_win=sha(OLD/"win.py"), hist=sha(HIST), schedule=sha(SCHEDULE))


def finite(request):
    if "expected" in request:
        return provenance(request,ATOMS)
    name=request["clause"]
    if name=="archive":
        assert request["packet"]=="WP-0044"
        old=read(HIST)
        g=old["genuine_all_P"]
        assert old["qualification"]=="withheld" and old["smallest_shared_unmet_obligation"].startswith("E.parent.")
        reviewer=read(OLD/"blind-results.json")
        author=read(HERE.parents[1]/"research"/"WP-0044"/"blind-results.json")
        joints={v for case in ("W1.A","W1.B") for v in
                (author["rows"][case]["verdict"]["joint"],reviewer[case]["joint"])}
        assert joints=={"U"}
        return dict(old_joint=joints.pop(), author_genuine_P=g["author"], reviewer_genuine_P=g["reviewer"],
                    genuine_per_route=g["scheduled_per_route"], direct_edge="unobserved")
    return {"A1":branch,"A2":scores,"C1":query}[name](request)


def run():
    ordinary()
    baseline=read(HERE/"manifest.json")
    base_check=manifest()
    base_check["runtime"]["all_modules"]=baseline["runtime"]["all_modules"]
    assert baseline==base_check
    label=sys.argv[1]
    if label=="smoke":
        arm=HOME/sys.argv[2]
        assert arm.name.startswith("smoke") and arm.parent==HOME
        request=dict(clause="Q1",selection=89,payload_hex="5354380a")
        print(json.dumps(collect(arm,request,baseline,ATOMS)))
        return
    assert label=="run"
    out=HOME/"decisive01"
    out.mkdir()
    start=time.monotonic()
    schedule=read(SCHEDULE)["rows"]
    rows,digests,errors={}, {}, {}
    for group, cases in schedule.items():
        for case in cases:
            try:
                raw=(HOME/"blind"/(case+".json")).read_bytes()
                digests[case]=hashlib.sha256(raw).hexdigest()
                req=json.loads(raw)
                if group=="live":
                    assert req["clause"]=="Q1" and req["selection"] in (0,1) and req["payload_hex"]=="4630370a"
                    native_dir=out/("native-"+str(req["selection"]))
                    rows[case]=collect(native_dir,req,baseline,ATOMS)
                    save(native_dir/"historical-comparison.json",
                         compare_old(read(native_dir/"public-witness.json"),req["selection"]))
                else:
                    rows[case]=finite(req)
                save(out/(case+".json"),rows[case])
            except Exception:
                errors[case]=traceback.format_exc()
    save(out/"rows.json",rows)
    save(out/"digests.json",digests)
    files={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob("*")) if p.is_file()}
    save(out/"archive.json",dict(files=files,errors=errors,seconds=time.monotonic()-start,
                                  bytes=sum(p.stat().st_size for p in out.rglob("*") if p.is_file())))
    print(json.dumps(dict(records=len(rows),errors=list(errors),archive_sha256=sha(out/"archive.json"))))


if __name__=="__main__":
    if sys.argv[1]=="manifest":
        import subprocess
        m=manifest()
        m["runtime"]["all_modules"]=json.loads(subprocess.check_output(
             [str(BASE),"-I","-S","-B",str(HERE/"worker.py"),"profile"],env=clean_env()))
        save(HERE/"manifest.json",m)
    elif sys.argv[1]=="evaluate":
        print(json.dumps(finite(json.loads(sys.stdin.buffer.read()))))
    else:
        run()
