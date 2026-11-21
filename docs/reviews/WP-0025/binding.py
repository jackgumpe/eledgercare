"""Check the coordinator's exact two orders and guard/supervisor source before invoking its guard."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

REVIEW=Path(__file__).resolve().parents[3]
QPY=Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe")
HOST=Path("C:/Users/jackg/eLedgerCare-Speed/WP-0025")
HIST=REVIEW/"docs/reviews/WP-0024/h0-r1.zip"
OLD="1843cdb7b6279b84b539d3ca1ba7bd0affa1f7dd"
GPU="GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d"


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return sha256(path.read_bytes()).hexdigest()


def verify(path, pin, expected_candidate, plan_pins):
    assert sha(path)==pin
    rel=read(path)
    exe=Path(rel["worktree"])
    root=path.parent.parents[2]
    assert subprocess.check_output(["git","-C",exe,"rev-parse","HEAD"],text=True).strip()==expected_candidate
    assert not subprocess.check_output(["git","-C",exe,"status","--porcelain","--untracked-files=all"])
    assert rel["review_worktree_head"]==expected_candidate
    assert rel["name"]=="window-repeat-r1" and rel["operator"]=="eld-repeat-reviewer" and rel["gpu_uuid"]==GPU
    assert rel["ceiling_mib"]==12500 and rel["free_floor_mib"]==12000
    for folder,key in [(exe,"source_files"),(root,"coordination_files")]:
        for name,pin2 in rel[key].items():
            assert sha(folder/name)==pin2
    with ZipFile(HIST) as z:
        old=json.loads(z.read("binding/h0-r1-plan.json"))
        cold=json.loads(z.read("run/sensor/cold.json"))["model"]
        native=json.loads(z.read("run/sensor/b01w01S/native.json"))
    sys.path.insert(0,str(REVIEW/"workers/local_ocr"))
    from local_ocr.protocol import build_call_kwargs
    summary=[]
    assert len(rel["orders"])==2
    for idx,(order,pin2,modes) in enumerate(zip(rel["orders"],plan_pins,["SHHS","HSSH"],strict=True),1):
        process="p"+str(idx)
        plan_path=Path(order["plan"])
        plan=read(plan_path)
        assert order["run"]==process and sha(plan_path)==order["plan_sha256"]==pin2
        assert order["seconds"]==plan["deadline_seconds"]==1200
        assert str(Path(order["output"]).resolve())==str((HOST/"review/runs"/process).resolve())
        assert Path(order["output"])==Path(plan["output"]) and not Path(plan["output"]).exists()
        argv=order["argv"]
        assert Path(argv[0])==QPY and argv[1:3]==["-I","-B"]
        assert Path(argv[3])==exe/"docs/coordination/WP-0025/supervise.py"
        assert Path(argv[4])==plan_path and argv[5:]==[pin2]
        assert plan["process_id"]==process.upper() and plan["process_ordinal"]==idx
        assert [c["mode"] for c in plan["calls"]]==list(modes)
        assert [c["tag"] for c in plan["calls"]]==[f"P{idx}J{j}{m}" for j,m in enumerate(modes,1)]
        for j,c in enumerate(plan["calls"],1):
            assert c["pages"]==old["calls"][0]["pages"] and c["hooked"] is (modes[j-1]=="H")
            assert c["retain_hidden"] is c["hooked"] and c["ordinal"]==j
        assert plan["settings"]==build_call_kwargs(3)
        assert plan["prompt"]==native["prompt"] and plan["prompt_token_ids"]==native["prompt_token_ids"]
        assert plan["model_revision"]==old["model_revision"] and plan["module_sha256"]==old["module_sha256"]
        assert plan["tokenizer_sha256"]==cold["tokenizer_sha256"] and plan["candidate"]==expected_candidate
        env=plan["environment"]
        assert env["CUDA_VISIBLE_DEVICES"]==GPU and env["HF_HUB_OFFLINE"]==env["TRANSFORMERS_OFFLINE"]==env["PIP_NO_INDEX"]=="1"
        assert plan["raster_root"]==old["raster_root"]
        summary.append(dict(process=process,plan_sha256=pin2,tags=[c["tag"] for c in plan["calls"]],
                            output=plan["output"],deadline_s=order["seconds"]))
    return dict(utc=datetime.now(timezone.utc).isoformat(),candidate=expected_candidate,release_sha256=pin,
                source_files_count=len(rel["source_files"]),guard_files_count=len(rel["coordination_files"]),
                orders=summary,worktree=str(exe),gpu=GPU)


if __name__=="__main__":
    assert sys.flags.isolated and sys.dont_write_bytecode
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("release",type=Path)
    p.add_argument("release_sha")
    p.add_argument("candidate")
    p.add_argument("plans",nargs=2)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    data=verify(a.release,a.release_sha,a.candidate,a.plans)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf8") as f:
        json.dump(data,f,indent=2)

