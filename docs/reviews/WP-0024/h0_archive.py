"""Archive H0 primary outputs, timings and board/job evidence after the guard returns."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


HOST=Path("C:/Users/jackg/eLedgerCare-Speed/WP-0024")
RELEASE_REV="f5ff53945e11c8b0edf2da009c851768f77514ed"


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def collect(output):
    guard=HOST/"coordination/leases/h0-r1"
    runtime=HOST/"review/runs/h0-r1"
    data={}
    returned=json.loads((guard/"returned.json").read_bytes())
    assert returned["release_sha256"]=="0e64d12cf0a39adf681ce6eaece4437e7d2af756449e8b3b6eea8d31e586f82d"
    for file in guard.iterdir():
        if file.is_file():
            data["guard/"+file.name]=file.read_bytes()
    for file in runtime.rglob("*"):
        if file.is_file():
            relative=file.relative_to(runtime)
            if relative.parts[:2]!=("sensor","cache"):
                data["run/"+relative.as_posix()]=file.read_bytes()
    for name in ("h0-r1-plan.json","h0-r1-release.json"):
        data["binding/"+name]=subprocess.check_output(["git","show",RELEASE_REV+":docs/coordination/WP-0024/"+name])
    for name in ("attempt.json","admission-watch-binding.json","guard-launch.log"):
        path=HOST/"review/h0-watch-r1"/name
        if path.exists():
            data["admission/"+name]=path.read_bytes()
    sample_board=[json.loads(line) for line in data["guard/h0-r1-device.jsonl"].splitlines()]
    outcome=json.loads(data["run/sensor/outcome.json"])
    ordered=sorted(data.items())
    with ZipFile(output,"x") as zip_out:
        for name,raw in ordered:
            item=ZipInfo(name,date_time=(2026,11,21,0,0,0))
            zip_out.writestr(item,raw,compress_type=ZIP_DEFLATED,compresslevel=6)
    with ZipFile(output) as check:
        assert check.testzip() is None
        assert all(check.read(name)==raw for name,raw in ordered)
    return {"archive_sha256":sha(output.read_bytes()),"archive_size":output.stat().st_size,
            "files":{name:{"sha256":sha(raw),"bytes":len(raw)} for name,raw in ordered},
            "sampled_device":{"samples":len(sample_board),"max_used_mib":max(r["used_mib"] for r in sample_board),
                              "min_free_mib":min(r["free_mib"] for r in sample_board)},
            "window_metric_sum_s":outcome["window_metric_sum_s"],"complete_phase_s":outcome["complete_phase_s"],
            "real_calls":outcome["real_inference_calls"],"sensor_reported_all_equal":outcome["all_equal"],
            "guard":returned}


if __name__=="__main__":
    assert sys.flags.isolated and sys.dont_write_bytecode
    print(json.dumps(collect(Path(sys.argv[1])),indent=2))

