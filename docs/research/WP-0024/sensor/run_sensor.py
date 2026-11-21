"""Execute a source- and input-bound set of stock singleton captures with one resident model."""
from argparse import ArgumentParser
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
Q0 = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005")
HOST = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0024")
GPU = "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d"
sys.path[:0] = [str(HERE),str(ROOT/"docs/research/WP-0015/astra"),str(ROOT/"docs/research/WP-0014/eld-latency-author"),
                str(ROOT/"workers/local_ocr")]
from capture import infer, pack_json, save


def record(path, data):
    return save(path, pack_json(data))


def shafile(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def read_images(items, raster_root):
    from PIL import Image
    image_list=[]
    if len(items)!=3:
        raise ValueError("Stock singleton requires exactly three pages")
    for item in items:
        img_path=Path(item["image"]).resolve()
        if not img_path.is_relative_to(raster_root):
            raise ValueError("Unbound raster path")
        raw=img_path.read_bytes()
        if sha256(raw).hexdigest()!=item["sha256"]:
            raise ValueError("PNG digest changed")
        with Image.open(io.BytesIO(raw)) as opened:
            image=opened.convert("RGB")
        if image.size!=(2550,3300) or sha256(image.tobytes()).hexdigest()!=item["rgb_sha256"]:
            raise ValueError("RGB dimensions or digest changed")
        image_list.append(image)
    return image_list


def conduct(plan, folder):
    from native import MODEL,Native
    from spans import verify_parsers
    from local_ocr.env_guard import audit_worker_environment
    audit_worker_environment(dict(os.environ),run_dir=folder,readonly_q0_root=Q0,leased_gpu_uuid=GPU)
    verify_parsers()
    if shafile(MODEL/"modeling_unlimitedocr.py")!=plan["module_sha256"]:
        raise ValueError("Model module changed")
    if Path(sys.executable).resolve()!=(Q0/"venv/Scripts/python.exe").resolve() or not sys.flags.isolated or not sys.flags.dont_write_bytecode:
        raise ValueError("Run in read-only Q0 Python with -I -B")
    git="C:/Program Files/Git/cmd/git.exe"
    def git_call(*args):
        return subprocess.check_output([git,"-C",str(ROOT),*args],text=True).strip()
    if git_call("rev-parse","HEAD")!=plan["candidate"] or git_call("status","--porcelain","--untracked-files=all"):
        raise ValueError("Clean frozen execution checkout required")
    start=time.time_ns()
    native=Native(folder)
    record(folder/"cold.json",{"start_utc_ns":start,"ready_utc_ns":time.time_ns(),"model":native.info})
    rows={}
    try:
        for idx, call in enumerate(plan["calls"]):
            tag=call["tag"]
            if not tag.isascii() or not tag.isalnum() or tag in rows:
                raise ValueError("Invalid or repeated trial slot")
            sample=folder/tag
            images=read_images(call["pages"], Path(plan["raster_root"]).resolve())
            record(folder/(tag+"-begin.json"),{"utc_ns":time.time_ns(),"ordinal":idx})
            try:
                rows[tag]=infer(native,images,sample,call["hooked"],call["retain_hidden"])
            finally:
                for img in images:
                    img.close()
        groups = []
        for check in plan["check_groups"]:
            first,other = rows[check["left"]],rows[check["right"]]
            keys=("token_sha256","prompt_sha256","eos","metadata_sha256")
            differences=[k for k in keys if first[k]!=other[k]]
            if check["mode"]=="duplicate":
                for k in ("hidden_sha256","pooled_sha256","capture_layer","native_dtype","pool_dtype","hidden_shape","pool_shape"):
                    if first["capture"][k]!=other["capture"][k]:
                        differences.append(k)
            groups.append({**check,"differing":differences,"passed":not differences})
        receipts={"phase":plan["phase"],"candidate":plan["candidate"],"checks":groups,
                  "all_equal":all(c["passed"] for c in groups),"real_inference_calls":len(rows),
                  "window_metric_sum_s":sum(r["complete_window_wall_ns"] for r in rows.values())/1e9,
                  "complete_phase_s":(time.time_ns()-start)/1e9,"rows":rows}
        record(folder/"outcome.json",receipts)
    finally:
        native.close()


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument("plan",type=Path)
    parser.add_argument("digest")
    a=parser.parse_args()
    raw=a.plan.read_bytes()
    if sha256(raw).hexdigest()!=a.digest:
        raise ValueError("Plan digest mismatch")
    plan=json.loads(raw)
    out=Path(plan["output"]).resolve()
    if out.parent!=(HOST/"review/runs").resolve():
        raise ValueError("Output outside the owned run directory")
    folder=out/"sensor"
    if not folder.exists() or list(x for x in folder.iterdir() if x.name!="cache"):
        raise ValueError("Supervisor must prepare a clean run-local cache")
    os.chdir(folder)
    sys.stdout.reconfigure(encoding="utf8")
    sys.stderr.reconfigure(encoding="utf8")
    record(folder/"binding.json",{"candidate":plan["candidate"],"plan_sha256":a.digest,
                                  "model_revision":plan["model_revision"],"python":sys.executable,"utc_ns":time.time_ns()})
    try:
        conduct(plan,folder)
    except Exception as e:
        record(folder/"error.json",{"type":type(e).__name__,"message":str(e),"traceback":traceback.format_exc()})
        raise


if __name__=="__main__":
    main()
