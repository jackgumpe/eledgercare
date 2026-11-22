"""Require independent source, ownership, signed-return and numeric checks before feature use."""
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
from zipfile import ZipFile
import psutil

sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit import KEY, Q0, SCRATCH, ZIP, blob, initialize, save, sha
from auth import authenticate
from preflight import BIND, CANDIDATE, P

PREFLIGHT="3674ed58b88184abaececbef601c49602af69489"
OPERATOR="12577f907a5806f4f443a6f5067b4c49c60511e5"

def model_after():
    pre=json.loads(blob(OPERATOR,"docs/research/WP-0029/acquisition/evidence/prepare.json"))["q0"]
    manifest=json.loads(blob(CANDIDATE,"workers/local_ocr/manifests/model-files.json"))
    objects={}
    for kind,spec,folder in (("model","files",Q0/"models"/manifest["model_dir_basename"]),
                             ("notice","notices",Q0/"notices"/manifest["notice_dir_basename"])):
        prior={r["name"]:r for r in pre[kind]}
        assert (folder/".cache").is_dir() and {p.name for p in folder.iterdir()}-{".cache"}==set(prior)=={r["path"] for r in manifest[spec]}
        for ref in manifest[spec]:
            p=folder/ref["path"]
            assert p.stat().st_size==ref["size"]==prior[p.name]["bytes"]
            h=hashlib.sha256()
            git=hashlib.sha1(f"blob {p.stat().st_size}\x00".encode())
            using_git=ref["digest_kind"]=="git_blob_sha1"
            with p.open("rb") as stream:
                while chunk:=stream.read(4*1024*1024):
                    h.update(chunk)
                    if using_git: git.update(chunk)
            assert h.hexdigest()==prior[p.name]["sha256"]
            assert (git.hexdigest()==ref["git_blob_sha1"] if using_git else h.hexdigest()==ref["sha256"])
            objects[kind+"/"+p.name]=h.hexdigest()
    assert len(objects)==19
    return objects

def check(rev):
    raw=blob(rev,ZIP)
    original=json.loads(blob(rev,"docs/research/WP-0029/acquisition/evidence/native-inventory.json"))
    with ZipFile(io.BytesIO(raw)) as z:
        members={k:sha(z.read(k)) for k in z.namelist()}
        assert len(members)==len(z.namelist()) and z.testzip() is None
        assert {k:(v["sha256"],v["bytes"]) for k,v in original["members"].items()}=={
            k:(h,z.getinfo(k).file_size) for k,h in members.items()}
        assert original["sha256"]==sha(raw)
        result={"archive_revision":rev,"archive_sha256":sha(raw),"rgb_key":KEY,"members_sha256":members,
                "authenticated":False,"eligible_owner_cue":False,"reason":None,"preflight_revision":PREFLIGHT,
                "native_evidence_reached":original["native_artifacts_reached_in_protocol_order"]}
        for name in ("release","plan"):
            f="cedar-r1-"+name+".json"
            assert z.read("binding/"+f)==blob(BIND,P+f)
        def read(p): return json.loads(z.read(p))
        issue=read("operator/issuance.json")
        term=read("operator/supervisor-terminal.json")
        assert issue["device_candidate"]==CANDIDATE and issue["retry_budget"]==0
        assert issue["reviewer_preflight"]==PREFLIGHT and issue["plan_sha256"]==members["binding/cedar-r1-plan.json"]
        assert issue["release_sha256"]==members["binding/cedar-r1-release.json"]
        assert issue["prepare_sha256"]==sha(blob(OPERATOR,"docs/research/WP-0029/acquisition/evidence/prepare.json"))
        assert term["exit_code"]==original["exit_code"]
        result["post_model_files_sha256"]=model_after()
        if term["exit_code"]!=0 or "sensor/outcome.json" not in members:
            result["reason"]="Unsuccessful native supervision or incomplete acquisition"
            result["stop_observations"]={k:read(k) for k in ("lease/returned.json","process.json","sensor/error.json",
                "lease/issued.json","sensor/binding.json","sensor/cold.json","sensor/warmup.json") if k in members}
            return result
        acquire=read("lease/acquired.json")
        admission=read("lease/admission.json")
        issued=read("lease/issued.json")
        returned=read("lease/returned.json")
        process=read("process.json")
        assert acquire["release_sha256"]==issue["release_sha256"]==returned["release_sha256"]
        assert issued["plan_sha256"]==issue["plan_sha256"] and issued["deadline_mono_ns"]-issued["start_mono_ns"]==180*10**9
        assert acquire["guard_pid"]==issued["guard_pid"]==process["guard_pid"]==returned["retiring_pid"]
        assert issued["job"]==process["job"] and issued["argv"][-1]==issued["job"]
        assert len(issued["argv"])==7 and issued["argv"][1:3]==["-I","-B"] and issued["argv"][-2]==issued["plan_sha256"]
        assert issued["job"].startswith("Local\\eLedgerCare-WP0029-")
        assert 0<process["native_job_wall_s"]<=180 and process["returncode"]==0 and process["stop_reason"] is None
        assert process["telemetry_errors"]==[] and returned["error"] is None
        pre,post=admission["observed"],returned["ownership_after_job_close"]
        known=set(json.loads(blob(CANDIDATE,"docs/reviews/WP-0024/admission-watch-binding.json"))["observed_desktop_images"])
        assert admission["unknown"]==[] and pre["device"]["free_mib"]>=12000
        for sample in (pre,post):
            assert sample["ollama_models"]==0 and all(r["image"].casefold() in known for r in sample["processes"])
            assert 0<=sample["device"]["used_mib"]<=12500
        samples=[json.loads(line) for line in z.read("lease/device.jsonl").splitlines()]
        assert samples and [s["mono_ns"] for s in samples]==sorted(s["mono_ns"] for s in samples)
        peak=max(s["used_mib"] for s in samples)
        assert 0<peak<=12500 and all(s["total_mib"]==pre["device"]["total_mib"] for s in samples)
        binding=read("sensor/binding.json")
        assert ((binding["pid"]==issued["launcher_pid"] and binding["parent_pid"]==issued["guard_pid"]) or
                (binding["pid"]!=issued["launcher_pid"] and binding["parent_pid"]==issued["launcher_pid"]))
        # Windows venv may use a forwarding executable. Only the recorded actual
        # worker may be the direct job child, or the direct child of its launcher.
        pids={process["guard_pid"],process["launcher_pid"],binding["pid"],binding["parent_pid"]}
        assert process["launcher_pid"]==issued["launcher_pid"] and binding["pid"] in pids
        statuses={}
        latest=datetime.fromisoformat(returned["utc"]).timestamp()
        for pid in sorted(pids):
            if not psutil.pid_exists(pid):
                statuses[str(pid)]="absent"
            else:
                created=psutil.Process(pid).create_time()
                assert created>latest
                statuses[str(pid)]={"reused_after_return":created}
        cold=read("sensor/cold.json")
        duration=read("sensor/k0001/duration.json")
        assert issued["utc_ns"]<=binding["utc_ns"]<=cold["start_utc_ns"]<cold["ready_utc_ns"]<=duration["start_utc_ns"]
        assert duration["end_capture_utc_ns"]-issued["utc_ns"]<=180*10**9
        assert samples[0]["mono_ns"]<issued["deadline_mono_ns"]
        result.update(authenticate(rev))
        result.update(authenticated=True,
                      hardware={"peak_board_mib":peak,"samples":len(samples),"admission_free_mib":pre["device"]["free_mib"],
                                "native_job_wall_s":process["native_job_wall_s"],"after_free_mib":post["device"]["free_mib"],
                                "guard_exit":term["exit_code"],"model_load_s":cold["elapsed_ns"]/1e9,
                                "w0_s":read("sensor/warmup.json")["elapsed_ns"]/1e9,
                                "cedar_infer_s":duration["wall_inference_ns"]/1e9,
                                "cedar_window_s":duration["complete_window_wall_ns"]/1e9,"owned_pids":statuses})
        return result

if __name__=="__main__":
    initialize()
    save(sys.argv[2],check(sys.argv[1]))
