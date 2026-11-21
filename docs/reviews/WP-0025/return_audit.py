"""Reconcile the guarded process returns, cold-load identities, clocks, board samples and selected runtime files."""
import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile


def verify(archive):
    with ZipFile(archive) as z:
        def raw(path):
            return z.read(path)
        def read(path):
            return json.loads(raw(path))
        def guard(file):
            return read("guard/"+file+".json")
        def operator(file):
            return read("operator/"+file+".json")
        release_file="binding/window-repeat-r1-release.json"
        rel=read(release_file)
        digest=sha256(raw(release_file)).hexdigest()
        acquired,returned=guard("acquired"),guard("returned")
        entered,launched,exited=(operator(f) for f in ("issued","guard-start","return"))
        assert acquired["release_sha256"]==returned["release_sha256"]==entered["binding"]["release_sha256"]==digest
        assert acquired["pid"]==returned["retiring_pid"] and launched["pid"]==exited["pid"]
        assert Path(acquired["lock"]).name==rel["gpu_uuid"]+".lock"
        assert not entered["board"]["holds"] and entered["board"]["free_mib"]>=12000
        assert all(not ("cache" in Path(f).parts) for f in z.namelist())
        result={}
        problems=[]
        if returned["error"] or exited["exit_code"]:
            problems.append(dict(guard_error=returned["error"],operator_return=exited["exit_code"]))
        starts=[]
        intervals=[]
        worker_identities=[]
        known_pids={acquired["pid"],launched["pid"],entered["pid"]}
        for order in rel["orders"]:
            p=order["run"]
            try:
                def run(file):
                    return read("runs/"+p+"/"+file+".json")
                plan=read("binding/"+p+"-plan.json")
                assert sha256(raw("binding/"+p+"-plan.json")).hexdigest()==order["plan_sha256"]
                desktop,issue,ret=(guard(p+"-"+k) for k in ("desktop-admission","issued","returned"))
                assert desktop["unrecognized_gpu_clients"]==[] and issue["admission"]["ollama_models"]==0
                assert issue["admission"]["device"]["free_mib"]>=12000 and ret["ownership_after_job_close"]["ollama_models"]==0
                samples=[json.loads(line) for line in raw("guard/"+p+"-device.jsonl").splitlines()]
                assert samples and max(s["used_mib"] for s in samples)<=12500
                assert ret["exit"]==0 and ret["guard"] is None
                issued_worker,process=run("worker-issued"),run("process")
                seg,=process["segments"]
                assert seg["argv"]==issued_worker["argv"] and seg["launcher_pid"]==issued_worker["launcher_pid"]
                assert seg["returncode"]==0 and seg["plan_sha256"]==order["plan_sha256"]
                assert process["all_segments_completed"] is True and seg["elapsed_s"]<=order["seconds"]
                bind,cold,outcome=(run("sensor/"+k) for k in ("binding","cold","outcome"))
                ids=[r["tag"] for r in plan["calls"]]
                assert outcome["verified_tags"]==ids==outcome["started_tags"]
                assert bind["order"]==ids and outcome["status"]=="complete" and cold["loads"]==1
                assert cold["model"]["platform"]==plan["historical_platform"]
                assert bind["pid"]==cold["pid"]==outcome["pid"]
                assert bind["process_create_filetime"]==cold["process_create_filetime"]==outcome["process_create_filetime"]
                assert seg["launcher_pid"] in (bind["pid"],bind["parent_pid"])
                creation=(bind["process_create_filetime"]-116444736000000000)*100
                assert seg["start_utc_ns"]<=creation<=bind["utc_ns"]<=cold["start_utc_ns"]<=cold["ready_utc_ns"]
                previous=cold["ready_utc_ns"]
                stamps=[]
                for i,t in enumerate(ids,1):
                    b,d,r=(run("sensor/"+t+"-begin"),run("sensor/"+t+"/duration"),run("sensor/"+t+"/receipt"))
                    assert b["pid"]==r["pid"]==bind["pid"] and b["ordinal"]==r["ordinal"]==i
                    assert previous<=b["utc_ns"]<=d["start_utc_ns"]<=d["end_inference_utc_ns"]<=d["end_capture_utc_ns"]<=r["utc_ns"]
                    assert b["monotonic_ns"]<=r["monotonic_ns"] and r["verified"] is True
                    previous=r["utc_ns"]
                    stamps.append([t,b["utc_ns"],r["utc_ns"]])
                assert previous<=outcome["utc_ns"]<=seg["end_utc_ns"]
                assert (ret["wall_s"]<=order["seconds"]+15 and datetime.fromisoformat(issue["issued"])<=datetime.fromisoformat(ret["utc"]))
                starts.append((p,issue["job"]))
                intervals.append((seg["start_utc_ns"],seg["end_utc_ns"]))
                worker_identities.append((bind["pid"],bind["process_create_filetime"]))
                known_pids.update([issue["pid"],seg["launcher_pid"],seg["supervisor_pid"],seg["supervisor_parent_pid"],bind["pid"],bind["parent_pid"]])
                result[p]=dict(child_pid=issue["pid"],worker_launcher=seg["launcher_pid"],worker=bind["pid"],
                    worker_parent=bind["parent_pid"],worker_create_filetime=bind["process_create_filetime"],
                    supervisor=seg["supervisor_pid"],job=issue["job"],guard_wall_s=ret["wall_s"],
                    exact_worker_s=outcome["process_wall_ns"]/1e9,supervised_s=seg["elapsed_s"],
                    admission_free_mib=issue["admission"]["device"]["free_mib"],samples=len(samples),
                    max_board_used_mib=max(s["used_mib"] for s in samples),min_board_free_mib=min(s["free_mib"] for s in samples),
                    returned_free_mib=ret["ownership_after_job_close"]["device"]["free_mib"],
                    load_s=(cold["ready_utc_ns"]-cold["start_utc_ns"])/1e9,ordered_call_receipts=stamps)
            except (KeyError,AssertionError,TypeError,ValueError) as exc:
                problems.append({"order":p,"reason":repr(exc)})
        if len(intervals)==2:
            assert intervals[0][1]<=intervals[1][0] and len(set(worker_identities))==2 and len({j for _,j in starts})==2
        return dict(issues=problems,release_sha256=digest,retired_guard_pid=returned["retiring_pid"],
                    observed_process_ids=sorted(known_pids),post_return_operator=exited["post_observation"],
                    orders=result,worker_intervals_utc_ns=intervals)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive",type=Path)
    p.add_argument("output",type=Path)
    a=p.parse_args()
    with a.output.open("x",encoding="utf8",newline="\n") as f:
        f.write(json.dumps(verify(a.archive),indent=2)+"\n")
