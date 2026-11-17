"""File-only recovery after the original lifecycle's 264-character copy target failed."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, stat, subprocess

BASE=Path(__file__).resolve().parents[1]
ROOT=Path(subprocess.check_output(["git","rev-parse","--show-toplevel"],text=True).strip())
EXTERNAL=Path("C:/Users/jackg/eLedgerCare-Demo/WP-0012/reviewer/independent-011/run-01")


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--output",required=True); args=parser.parse_args()
    output=Path(args.output); assert not output.exists()
    assert not subprocess.check_output(["git","status","--porcelain"],cwd=ROOT).strip(),"Freeze collector first"
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    assert EXTERNAL.is_dir()
    original=BASE/"evidence/lifecycle-01"
    invocation=json.loads((original/"invocation.json").read_text(encoding="utf-8"))
    assert invocation["exit_code"]==1
    outcomes={name:json.loads((original/(name+".json")).read_text(encoding="utf-8")) for name in ("complete","boundary-failure")}
    assert all(row["passed"] and all(row["checks"].values()) for row in outcomes.values())
    assert outcomes["complete"]["main_return_code"]==0
    assert "Phase 1 live Edge workflow stopped/failed (exit 7)" in outcomes["boundary-failure"]["main_exception"]
    assert all(row["pg_status_after"]==3 and all(v==[] for v in row["after_ports"].values()) for row in outcomes.values())
    settings=json.loads((ROOT.parent/"eld-f4-reviewer/.local/secrets/pg-local.json").read_text(encoding="utf-8"))
    secrets=[str(settings[k]).encode() for k in ("adminPassword","migratorPassword","appPassword")]
    output.mkdir(parents=True)
    items=[]
    for item in sorted(EXTERNAL.rglob("*")):
        before=item.lstat()
        assert not stat.S_ISLNK(before.st_mode) and not (getattr(before,"st_file_attributes",0)&getattr(stat,"FILE_ATTRIBUTE_REPARSE_POINT",0x400))
        assert item.resolve().is_relative_to(EXTERNAL.resolve())
        if not item.is_file(): continue
        raw=item.read_bytes(); after=item.stat()
        assert before.st_size==after.st_size and before.st_mtime_ns==after.st_mtime_ns
        assert not any(secret and secret in raw for secret in secrets),"Credential detected in artifact; no value printed"
        dest=output/(f"{len(items)+1:03d}"+item.suffix)
        assert len(str(dest.resolve()))<250
        dest.write_bytes(raw)
        digest=hashlib.sha256(raw).hexdigest()
        assert hashlib.sha256(dest.read_bytes()).hexdigest()==digest
        items.append(dict(original=str(item),relative_original=item.relative_to(EXTERNAL).as_posix(),copy=dest.relative_to(BASE).as_posix(),
                          bytes=len(raw),sha256=digest,original_mtime_ns=before.st_mtime_ns))
    expected_files={p.relative_to(EXTERNAL).as_posix() for p in EXTERNAL.rglob("*") if p.is_file()}
    assert expected_files=={row["relative_original"] for row in items}
    receipt=dict(collector_commit=head,completed_utc=datetime.now(timezone.utc).isoformat(),file_only=True,no_service_or_test_rerun=True,
                 source="5e75cacd11f18bf6135376e3e1e10887c1447e1f",lifecycle_check_commit="6803bca48d57c1c026f9317ce764063441ba2d79",
                 original_lifecycle_exit=1,original_tool_chunk="c49865",original_copy_error="FileNotFoundError at 264-character destination; parent existed and original 52,227-byte PNG existed",
                 original_failures_preserved=True,actual_lifecycle_scenarios={k:dict(passed=v["passed"],finished_utc=v["finished_utc"],checks=v["checks"]) for k,v in outcomes.items()},
                 live_model_success_claimed=False,model_attempts=0,artifact_count=len(items),artifacts=items)
    (output/"manifest.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in receipt.items() if k not in ("artifacts","actual_lifecycle_scenarios")},indent=2))
    return 0


if __name__=="__main__": raise SystemExit(main())
