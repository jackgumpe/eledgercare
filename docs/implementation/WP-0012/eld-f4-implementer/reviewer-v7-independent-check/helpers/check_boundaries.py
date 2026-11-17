"""Independent /011 source/schema/storage controls. No model import or service start."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, ast, copy, hashlib, inspect, json, os, subprocess, sys, traceback, types
from unittest import mock

BASE=Path(__file__).resolve().parents[1]
ROOT=Path(subprocess.check_output(["git","rev-parse","--show-toplevel"],text=True).strip())
REVIEW_ROOT=ROOT.parent/"eld-f4-reviewer"
SOURCE="5e75cacd11f18bf6135376e3e1e10887c1447e1f"
RUNTIME="docs/reviews/WP-0012/eld-f4-reviewer/live-004/integration-correction/helpers/run_wp0012_reviewer_rehearsal_v7.py"
PREPARATION="docs/reviews/WP-0012/eld-f4-reviewer/preparation/helpers/run_wp0012_reviewer_rehearsal.py"


def load(raw,path,name):
    tree=ast.parse(raw.decode("utf-8"))
    forbidden={"torch","transformers","safetensors","pypdfium2","PIL","qualification","research","evaluation"}
    for n in ast.walk(tree):
        names=[a.name for a in n.names] if isinstance(n,ast.Import) else [n.module or ""] if isinstance(n,ast.ImportFrom) else []
        assert not any(x.split(".")[0] in forbidden for x in names),names
    mod=types.ModuleType(name); mod.__file__=str(path)
    exec(compile(raw,str(path),"exec"),mod.__dict__)
    return mod


def modules():
    for manifest in ("input-identities.json","v7-input-identities.json"):
        for item in json.loads((BASE/manifest).read_text(encoding="utf-8")):
            raw=(BASE/item["copy"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==item["sha256"]
            assert raw==subprocess.check_output(["git","show",item["commit"]+":"+item["path"]],cwd=ROOT)
    assert (BASE/"inputs/ownership-v7-copy.py.txt").read_bytes()==(BASE/"inputs/ownership-v6.py.txt").read_bytes()
    for local,actual in (("reviewer-v7.py.txt",RUNTIME),("preparation.py.txt",PREPARATION),
                         ("ownership-v7-copy.py.txt",str(Path(RUNTIME).with_name("ownership_v6.py"))),
                         ("browser.mjs.txt","docs/reviews/WP-0012/eld-f4-reviewer/preparation/helpers/drive_wp0012_edge_workflow.mjs")):
        assert (BASE/"inputs"/local).read_bytes()==(REVIEW_ROOT/actual).read_bytes(),actual
    owner=load((BASE/"inputs/ownership-v7-copy.py.txt").read_bytes(),REVIEW_ROOT/Path(RUNTIME).with_name("ownership_v6.py"),"ownership_v6")
    with mock.patch.dict(sys.modules,{"ownership_v6":owner}):
        v7=load((BASE/"inputs/reviewer-v7.py.txt").read_bytes(),REVIEW_ROOT/RUNTIME,"independent_v7")
        v6=load((BASE/"inputs/reviewer-v6.py.txt").read_bytes(),BASE/"inputs/reviewer-v6.py.txt","independent_v6")
    prep=load((BASE/"inputs/preparation.py.txt").read_bytes(),REVIEW_ROOT/PREPARATION,"run_wp0012_reviewer_rehearsal")
    return v7,v6,prep


def schema_audit(v7,prep):
    tree=ast.parse((BASE/"inputs/reviewer-v7.py.txt").read_text(encoding="utf-8"))
    calls=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=="prep_mod":
            fn=getattr(prep,n.func.attr)
            inspect.signature(fn).bind(*([object()]*len(n.args)),**{k.arg:object() for k in n.keywords})
            calls.append(dict(function=n.func.attr,line=n.lineno,signature=str(inspect.signature(fn)),positional=len(n.args)))
    assert sorted(c["function"] for c in calls)==["compute_canonical_8table_snapshot"]*2+["verify_q0_readonly_pure_stdlib"]*2
    def fns(text):
        return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
    old=fns((BASE/"inputs/reviewer-v6.py.txt").read_text(encoding="utf-8")); new=fns((BASE/"inputs/reviewer-v7.py.txt").read_text(encoding="utf-8"))
    changed={k for k in old if old[k]!=new.get(k)}
    assert changed=={"main"},changed
    assert set(new)-set(old)=={"verify_q0_receipt_contract","measure_owned_demo_storage"}
    return dict(preparation_calls=calls,changed_existing_functions=sorted(changed),new_functions=sorted(set(new)-set(old)),unchanged_functions=sorted(set(old)-changed))


def pure_controls(v7,v6,prep,output):
    result=dict(schema_audit=schema_audit(v7,prep),controls=[])
    started=datetime.now(timezone.utc).isoformat()
    receipt=prep.verify_q0_readonly_pure_stdlib(REVIEW_ROOT)
    result["actual_q0"]=dict(started_utc=started,finished_utc=datetime.now(timezone.utc).isoformat(),receipt=receipt)
    (output/"actual-q0.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    assert "demo_root_bytes" not in receipt and "demo_drive_free_bytes" not in receipt
    old=ast.parse((BASE/"inputs/reviewer-v6.py.txt").read_text(encoding="utf-8"))
    disk_if=next(n for n in ast.walk(old) if isinstance(n,ast.If) and "q0_pre['demo_root_bytes']" in ast.unparse(n.test))
    try:
        exec(compile(ast.fix_missing_locations(ast.Module(body=[disk_if],type_ignores=[])),"original-v6-disk-consumer","exec"),
             dict(q0_pre=receipt,STORAGE_CAP_BYTES=v6.STORAGE_CAP_BYTES,MIN_FREE_DISK_BYTES=v6.MIN_FREE_DISK_BYTES,ReviewerLeaseGuardError=v6.ReviewerLeaseGuardError))
        raise AssertionError("Original consumer did not reproduce KeyError")
    except KeyError as exc:
        assert exc.args==("demo_root_bytes",)
        result["original_actual_schema_failure"]=dict(error=repr(exc),actual_q0_used=True,statement=ast.unparse(disk_if),services_started=False)
    def check(name,fn,reject=False):
        row=dict(control=name,expected="reject" if reject else "pass")
        try: row.update(actual="pass",value=fn())
        except (v7.ReviewerLeaseGuardError,OSError) as exc: row.update(actual="reject",error=repr(exc))
        except Exception: row.update(actual="unexpected-exception",error=traceback.format_exc())
        row["passed"]=row["actual"]==row["expected"]; result["controls"].append(row)
    check("actual-q0-schema-accepted",lambda:v7.verify_q0_receipt_contract(receipt,prep))
    for key,value in (("schema","unknown"),("model_manifest_sha256","0"*64),("dependency_lock_sha256","0"*64),
                      ("verified_model_file_count",17),("total_model_bytes",0),("unexpected_extra_model_entries",["rogue.py"]),
                      ("missing_or_mismatched_distributions",["missing"]),("forbidden_modules_present",["forbidden"]),
                      ("verified_model_files",{})):
        broken=copy.deepcopy(receipt); broken[key]=value
        check("q0-reject-"+key,lambda r=broken:v7.verify_q0_receipt_contract(r,prep),True)
    missing=copy.deepcopy(receipt); missing.pop("total_model_bytes")
    check("q0-missing-field-no-default",lambda:v7.verify_q0_receipt_contract(missing,prep),True)
    check("q0-nondictionary",lambda:v7.verify_q0_receipt_contract([],prep),True)
    scratch=ROOT/".local"/("independent011-storage-"+output.name)
    assert not scratch.exists(); (scratch/"nested").mkdir(parents=True)
    (scratch/"one.bin").write_bytes(b"1234567"); (scratch/"nested/two.bin").write_bytes(b"abc")
    def actual_disk():
        observed=v7.measure_owned_demo_storage(scratch)
        assert observed["demo_root_bytes"]==10 and observed["file_count"]==2,observed
        assert observed["demo_drive_free_bytes"]>=v7.MIN_FREE_DISK_BYTES
        return observed
    check("actual-file-lengths-and-volume-free",actual_disk)
    check("missing-root-rejected",lambda:v7.measure_owned_demo_storage(scratch/"missing"),True)
    check("file-root-rejected",lambda:v7.measure_owned_demo_storage(scratch/"one.bin"),True)
    with mock.patch.object(v7,"STORAGE_CAP_BYTES",9): check("actual-bytes-over-cap",lambda:v7.measure_owned_demo_storage(scratch),True)
    with mock.patch.object(v7.shutil,"disk_usage",return_value=types.SimpleNamespace(free=v7.MIN_FREE_DISK_BYTES-1)):
        check("under-floor-observation",lambda:v7.measure_owned_demo_storage(scratch),True)
    with mock.patch.object(v7.shutil,"disk_usage",return_value=types.SimpleNamespace(free="unknown")):
        check("malformed-free-observation",lambda:v7.measure_owned_demo_storage(scratch),True)
    with mock.patch.object(v7,"is_reparse_or_link",side_effect=lambda p:Path(p).name=="one.bin"):
        check("linked-entry-observation",lambda:v7.measure_owned_demo_storage(scratch),True)
    def failing_walk(root,**kwargs): kwargs["onerror"](PermissionError("injected enumeration denial")); return []
    with mock.patch.object(v7.os,"walk",side_effect=failing_walk):
        check("inaccessible-tree-observation",lambda:v7.measure_owned_demo_storage(scratch),True)
    result["scratch_retained"]=str(scratch)
    return result


def main():
    p=argparse.ArgumentParser(); p.add_argument("--output",required=True); args=p.parse_args()
    output=Path(args.output); assert not output.exists()
    assert not subprocess.check_output(["git","status","--porcelain"],cwd=ROOT).strip(),"Freeze first"
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    v7,v6,prep=modules(); output.mkdir(parents=True)
    provenance=dict(source=SOURCE,check_commit=head,started_utc=datetime.now(timezone.utc).isoformat(),pid=os.getpid(),argv=sys.argv)
    try:
        result=pure_controls(v7,v6,prep,output)
        passed=all(r["passed"] for r in result["controls"])
    except Exception:
        result=dict(error=traceback.format_exc()); passed=False
    (output/"result.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    provenance.update(finished_utc=datetime.now(timezone.utc).isoformat(),passed=passed,exit_code=0 if passed else 1)
    (output/"provenance.json").write_text(json.dumps(provenance,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(provenance)); print(json.dumps({k:v for k,v in result.items() if k in ("controls","error")},indent=2))
    return provenance["exit_code"]


if __name__=="__main__": raise SystemExit(main())
