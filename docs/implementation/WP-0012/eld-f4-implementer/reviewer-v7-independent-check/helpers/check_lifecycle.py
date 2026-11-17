"""Independent real v7 main lifecycle, with explicit no-model CPU boundary adapters.

Authority bc5b345; invoke only after reviewer's explicit sequential resource return.
Never executes either live browser mode. Every API subprocess receives OCR=false.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, copy, hashlib, json, os, subprocess, sys, traceback
from unittest import mock
from check_boundaries import BASE, ROOT, REVIEW_ROOT, SOURCE, modules, schema_audit

FAKE_WO="11111111-1111-4111-8111-111111111111"
FAKE_MP="33333333-3333-4333-8333-333333333333"


def scenario(v7,prep,folder,kind):
    assert not folder.exists(),folder
    settings=json.loads((REVIEW_ROOT/".local/secrets/pg-local.json").read_text(encoding="utf-8"))
    secrets=[str(settings[k]) for k in ("adminPassword","migratorPassword","appPassword")]
    psql=REVIEW_ROOT/".local/tools/pgsql-18.7-1/bin/psql.exe"
    pgctl=REVIEW_ROOT/".local/tools/pgsql-18.7-1/bin/pg_ctl.exe"
    data=REVIEW_ROOT/".local/postgres-data"
    real_run=v7.run_cmd; real_popen=subprocess.Popen
    real_q0=prep.verify_q0_readonly_pure_stdlib
    real_snapshot=prep.compute_canonical_8table_snapshot
    real_projection=prep.compute_projection_tables_snapshot
    before_ports=v7.observe_ports(v7.REVIEWER_PORTS,REVIEW_ROOT)
    assert all(before_ports[str(p)]==[] for p in v7.REVIEWER_PORTS),before_ports
    assert real_run([str(pgctl),"status","-D",str(data)],cwd=REVIEW_ROOT).returncode==3
    runs=v7.WRITABLE_DEMO_ROOT/"runs"
    assert runs.is_dir() and not list(runs.iterdir()),"Existing runs must remain empty"
    result=dict(scenario=kind,cpu_only=True,runtime_authority=False,model_calls=0,uploads=0,
                synthetic_phase_ids=dict(wo=FAKE_WO,mp=FAKE_MP),commands=[],api_launches=[],browser_phases=[],
                q0_receipts=[],database_receipts=[],before_ports=before_ports,started_utc=datetime.now(timezone.utc).isoformat())
    launched=[]
    def safe_popen(argv,*args,**kwargs):
        args_list=[str(x) for x in argv] if isinstance(argv,(list,tuple)) else [str(argv)]
        lowered=" ".join(args_list).lower().replace("\\","/")
        assert "venv/scripts/python" not in lowered and "run_worker" not in lowered and "q0harness" not in lowered,"Blocked model command"
        if args_list and Path(args_list[0]).name.lower() in ("python","python.exe","pythonw.exe"):
            raise AssertionError("No Python subprocess is needed by this no-model lifecycle")
        if "--mode" in args_list:
            mode=args_list[args_list.index("--mode")+1]
            assert mode=="cpu-preflight","Blocked live browser mode at process boundary"
            assert "--target" in args_list and args_list[args_list.index("--target")+1]=="empty-ready-db"
        api=any(x.lower().endswith("eledgercare.api.dll") for x in args_list)
        if api:
            env=dict(kwargs.get("env") or {})
            requested=env.get("LocalOcr__Enabled")
            env["LocalOcr__Enabled"]="false"
            kwargs["env"]=env
            assert kwargs["env"]["LocalOcr__Enabled"]=="false"
        proc=real_popen(argv,*args,**kwargs)
        if api:
            result["api_launches"].append(dict(pid=proc.pid,requested_by_unmodified_main=requested,actual_child_ocr_enabled=False))
            launched.append(proc)
        elif args_list and any("@angular/cli" in x.replace("\\","/") for x in args_list): launched.append(proc)
        return proc
    def q0_call(repo):
        assert Path(repo).resolve()==REVIEW_ROOT.resolve()
        observed=real_q0(repo)
        result["q0_receipts"].append(copy.deepcopy(observed))
        return observed
    def snapshot_call(exe,config,database,cwd):
        assert Path(exe)==psql and database==v7.DEMO_DATABASE and Path(cwd)==REVIEW_ROOT
        observed=real_snapshot(exe,config,database,cwd)
        historical=dict(seed8=real_snapshot(exe,config,prep.HISTORICAL_SEED_DB,cwd),
                        migrated8=real_snapshot(exe,config,prep.HISTORICAL_MIGRATED_DB,cwd),
                        migrated_projection=real_projection(exe,config,prep.HISTORICAL_MIGRATED_DB,cwd))
        result["database_receipts"].append(dict(demo=copy.deepcopy(observed),demo_projection=real_projection(exe,config,database,cwd),historical=historical))
        return observed
    def adapted_run(argv,**kwargs):
        args_list=[str(x) for x in argv]
        if "--mode" in args_list and args_list[args_list.index("--mode")+1].startswith("live-phase"):
            mode=args_list[args_list.index("--mode")+1]
            index=len(result["browser_phases"])+1
            assert mode==("live-phase1-leased" if index==1 else "live-phase2-post-restart")
            dest=Path(args_list[args_list.index("--output")+1])
            record=dict(intercepted_live_mode=mode,live_mode_executed=False,received_argv=args_list)
            result["browser_phases"].append(record)
            if kind=="boundary-failure" and index==1:
                record.update(deliberate_failure=True,exit_code=7)
                return subprocess.CompletedProcess(argv,7,"","INDEPENDENT CPU INJECTED FIRST BROWSER BOUNDARY FAILURE")
            if index==2:
                assert args_list[args_list.index("--wo-document-id")+1]==FAKE_WO
                assert args_list[args_list.index("--mp-document-id")+1]==FAKE_MP
            cpu_out=folder/f"actual-empty-browser-{index}.json"
            cpu_shots=folder/f"actual-empty-browser-{index}-screenshots"
            cpu_args=[args_list[0],args_list[1],"--mode","cpu-preflight","--target","empty-ready-db",
                      "--ui-port",str(v7.UI_PORT),"--api-port",str(v7.API_PORT),"--output",str(cpu_out),"--screenshot-dir",str(cpu_shots)]
            cp=real_run(cpu_args,**kwargs)
            record.update(actual_cpu_argv=cpu_args,exit_code=cp.returncode,stdout=cp.stdout,stderr=cp.stderr)
            if cp.returncode: return cp
            browser=json.loads(cpu_out.read_text(encoding="utf-8"))
            assert browser["allEmptyCount"]==browser["machineEmptyCount"]==browser["reviewedEmptyCount"]==browser["nonGetApiCallCount"]==0
            record["actual_cpu_browser"]=browser
            synthetic=dict(schema="independent011.synthetic-phase-plumbing/1",cpu_only=True,actual_browser_output=str(cpu_out),
                           woDocument=dict(documentId=FAKE_WO,synthetic=True),mpDocument=dict(documentId=FAKE_MP,synthetic=True),model_attempts=0)
            dest.write_text(json.dumps(synthetic,indent=2)+"\n",encoding="utf-8")
            return cp
        cp=real_run(argv,**kwargs)
        result["commands"].append(dict(argv=args_list,returncode=cp.returncode,stdout=v7.redact_secrets(cp.stdout,secrets),stderr=v7.redact_secrets(cp.stderr,secrets)))
        return cp
    summary=folder/"main-summary.json"; rr=folder/"main-resource-return.json"
    argv=["--mode","live-leased-rehearsal","--release-commit","b"*40,"--release-path","docs/coordination/WP-0012/cpu-independent011-synthetic.json",
          "--summary-output",str(summary),"--q0-check-output",str(folder/"main-q0.json"),"--resource-return-output",str(rr),
          "--logs-dir",str(folder/"logs"),"--screenshots-dir",str(folder/"synthetic-phase-screenshots")]
    result["main_argv"]=argv
    ownership=dict(sole_model_job_verified=True,hardware_exclusivity_claimed=False,cpu_test_placeholder=True,actual_gpu_observation=False)
    try:
        with mock.patch.dict(sys.modules,{"run_wp0012_reviewer_rehearsal":prep}), \
             mock.patch.object(v7,"git_object_exists",return_value=True), mock.patch.object(v7,"git_bytes",return_value=b'{"cpu_only":true}'), \
             mock.patch.object(v7,"validate_reviewer_release_contract",return_value=dict(lease_id="CPU-ONLY-INDEPENDENT011-"+kind,parsed_pre_lease_blobs={})), \
             mock.patch.object(v7,"collect_live_ownership_snapshot",return_value=dict(cpu_test_placeholder=True)), \
             mock.patch.object(v7,"evaluate_gpu_and_model_ownership",return_value=ownership), \
             mock.patch.object(prep,"verify_q0_readonly_pure_stdlib",side_effect=q0_call), \
             mock.patch.object(prep,"compute_canonical_8table_snapshot",side_effect=snapshot_call), \
             mock.patch.object(v7,"run_cmd",side_effect=adapted_run), mock.patch.object(subprocess,"Popen",side_effect=safe_popen):
            result["main_return_code"]=v7.main(argv)
    except Exception:
        result["main_exception"]=traceback.format_exc()
    result["after_ports"]=v7.observe_ports(v7.REVIEWER_PORTS,REVIEW_ROOT)
    result["pg_status_after"]=real_run([str(pgctl),"status","-D",str(data)],cwd=REVIEW_ROOT).returncode
    result["retained_child_exit_codes"]=[dict(pid=p.pid,exit_code=p.poll()) for p in launched]
    result["run_directories_after"]=sorted(p.name for p in runs.iterdir())
    result["main_resource_return"]=json.loads(rr.read_text(encoding="utf-8")) if rr.exists() else None
    result["main_summary"]=json.loads(summary.read_text(encoding="utf-8")) if summary.exists() else None
    returned=result["main_resource_return"] or {}
    snapshots=result["database_receipts"]
    checks=dict(expected_main_outcome=(result.get("main_return_code")==0 if kind=="complete" else "Phase 1 live Edge workflow stopped/failed (exit 7)" in result.get("main_exception","")),
                real_api_launches=len(result["api_launches"])==(2 if kind=="complete" else 1),
                all_api_ocr_disabled=all(row["actual_child_ocr_enabled"] is False for row in result["api_launches"]),
                expected_browser_boundaries=len(result["browser_phases"])==(2 if kind=="complete" else 1),
                actual_pre_post_q0=len(result["q0_receipts"])==2 and result["q0_receipts"][0]["verified_model_files"]==result["q0_receipts"][-1]["verified_model_files"],
                actual_pre_final_db=len(snapshots)==2,
                all_eight_demo_counts_zero=len(snapshots)==2 and all(v==0 for snap in snapshots for v in snap["demo"]["counts"].values()),
                demo_projections_zero=len(snapshots)==2 and all(snap["demo_projection"]["projection_count"]==snap["demo_projection"]["unit_count"]==0 for snap in snapshots),
                historical_database_snapshots_unchanged=len(snapshots)==2 and snapshots[0]["historical"]==snapshots[-1]["historical"],
                clean_return=returned.get("clean_return_verified") is True and returned.get("lease_returned") is True,
                correct_return_status=returned.get("status")==("completed" if kind=="complete" else "failed_stopped_lease_returned"),
                ports_unbound=all(result["after_ports"][str(p)]==[] for p in v7.REVIEWER_PORTS),
                pg_stopped=result["pg_status_after"]==3,
                owned_children_exited=all(row["exit_code"] is not None for row in result["retained_child_exit_codes"]),
                runs_still_empty=result["run_directories_after"]==[])
    result.update(checks=checks,passed=all(checks.values()),finished_utc=datetime.now(timezone.utc).isoformat(),
                  live_model_success_claimed=False,live_browser_two_attempt_assertion_executed=False,
                  live_browser_requirement="Still requires actual two successful attempts; CPU empty archive with zero attempts/results does not satisfy it.")
    # Return artifacts are real main outputs bearing an unmistakable synthetic CPU lease ID.
    text=json.dumps(result,indent=2)+"\n"
    for secret in secrets: assert not secret or secret not in text,"Secret in independent result"
    return result


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--output",required=True); parser.add_argument("--external-name",required=True)
    parser.add_argument("--reviewer-return-message",required=True)
    args=parser.parse_args(); output=Path(args.output)
    assert not output.exists() and args.external_name.replace("-","").isalnum()
    assert not subprocess.check_output(["git","status","--porcelain"],cwd=ROOT).strip(),"Freeze independent source before execution"
    v7,_,prep=modules()
    external=v7.WRITABLE_DEMO_ROOT/"independent-011"/args.external_name
    assert not external.exists()
    output.mkdir(parents=True)
    provenance=dict(source=SOURCE,check_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
                    reviewer_head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=REVIEW_ROOT,text=True).strip(),
                    authority="bc5b345d812fdd3bdcf6eb7ae6b5a43b895d8113",reviewer_resource_return=args.reviewer_return_message,
                    started_utc=datetime.now(timezone.utc).isoformat(),pid=os.getpid(),argv=sys.argv,
                    synthetic_release_and_ownership=True,actual_model_or_gpu_calls=0)
    results=[]
    try:
        # Actual frozen PostgreSQL subset; static local dependencies only, no installation.
        dependency=prep.verify_pg_subset(REVIEW_ROOT/".local/tools",REVIEW_ROOT)
        (output/"pg-subset.json").write_text(json.dumps(dependency,indent=2)+"\n",encoding="utf-8")
        assert dependency["file_count"]==prep.EXPECTED_PG_FILES and dependency["total_bytes"]==prep.EXPECTED_PG_BYTES
        assert all(dependency[k]==[] for k in ("missing_files","extra_files","mismatched_files","reparse_points"))
        assert dependency["subset_manifest_sha256"]==prep.EXPECTED_PG_SUBSET_SHA
        assert dependency["central_directory_sha256"]==prep.EXPECTED_PG_CD_SHA and dependency["authenticode_status"]=="Valid"
        for kind in ("complete","boundary-failure"):
            observed=scenario(v7,prep,external/kind,kind)
            (output/(kind+".json")).write_text(json.dumps(observed,indent=2)+"\n",encoding="utf-8")
            results.append(dict(scenario=kind,passed=observed["passed"],checks=observed["checks"]))
            print(json.dumps(results[-1]),flush=True)
            if not observed["passed"]: break
    except Exception:
        (output/"unexpected-error.log").write_text(traceback.format_exc(),encoding="utf-8")
    copied=[]
    if external.exists():
        for item in sorted(external.rglob("*")):
            if item.is_file():
                relative=item.relative_to(external); dest=output/"original-runtime"/relative
                dest.parent.mkdir(parents=True,exist_ok=True); raw=item.read_bytes(); dest.write_bytes(raw)
                copied.append(dict(external=str(item),copy=dest.relative_to(output).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    (output/"runtime-copy-inventory.json").write_text(json.dumps(copied,indent=2)+"\n",encoding="utf-8")
    passed=len(results)==2 and all(r["passed"] for r in results)
    provenance.update(completed_utc=datetime.now(timezone.utc).isoformat(),results=results,passed=passed,exit_code=0 if passed else 1)
    (output/"provenance.json").write_text(json.dumps(provenance,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(provenance),flush=True)
    return provenance["exit_code"]


if __name__=="__main__": raise SystemExit(main())
