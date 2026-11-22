"""Execute a frozen CPU replay from the role-scoped PowerShell entry point."""
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OWNERS = ROOT / "docs/research/WP-0027/owners"
WP27 = "0573f69c481eea2e815899e00ddd5e68bb4e3c42"
RESERVATION = "c000c0299619345c887859b95c45befbb0c68987"
FIXTURE_PATH = "docs/fixtures/WP-0028/manifest.json"
sys.path[:0] = [str(HERE), str(OWNERS)]
from inputs import check, prepare, record, sha


def blob(rev, path):
    return subprocess.check_output(["git","cat-file","blob",rev+":"+path], cwd=ROOT)


def verify_files(candidate):
    hashes = {}
    local = ["protocol.md","score_math.py","measurement.py","historical.py","controlled.py","replay.py","run.ps1"]
    files = [(candidate, HERE/name) for name in local] + [(WP27, OWNERS/name) for name in ("inputs.py","observe.py")]
    for rev, path in files:
        name = path.relative_to(ROOT).as_posix()
        exact = blob(rev,name)
        check(path.read_bytes().replace(b"\r\n",b"\n") == exact.replace(b"\r\n",b"\n"), "source drift "+name)
        hashes[rev+":"+name] = sha(exact)
    return hashes


def run_main(work, mode, candidate, fixture=None):
    cpu_start, start = time.process_time(), time.perf_counter()
    check(sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.optimize, "use -I -B")
    check(work.parent.parent == Path("C:/Users/jackg/eLedgerCare-Speed/WP-0028") and
          work.parent.name in {"probe","review","coordination"}, "wrong scratch")
    guards = {k: os.environ[k] for k in ("CUDA_VISIBLE_DEVICES","HF_HUB_OFFLINE","HF_DATASETS_OFFLINE",
                                          "TRANSFORMERS_OFFLINE","PIP_NO_INDEX","OMP_NUM_THREADS","MKL_NUM_THREADS")}
    check(guards.pop("CUDA_VISIBLE_DEVICES") == "-1" and set(guards.values()) == {"1"}, "process guards")
    check(all(Path(os.environ[k]).parent == work for k in ("TEMP","TMP","TORCH_HOME","HF_HOME",
                                                           "XDG_CACHE_HOME","TORCHINDUCTOR_CACHE_DIR")), "cache guard")
    sources = verify_files(candidate)
    fit, _, routed, logical, physical, inputs = prepare(work)
    sys.path.insert(0, str(work/"probe"))
    import torch
    import matrix
    import run
    from controlled import controlled
    from historical import history, pdf_example
    from score_math import FLOOR, controls
    run.setup()
    check(torch.get_default_dtype() == torch.float32 and not torch.cuda.is_available() and
          torch.cuda.device_count() == 0 and torch.get_num_threads() == torch.get_num_interop_threads() == 1,
          "requires deterministic single-thread CPU FP32")
    refs = {}
    result = {"mode": mode, "arms": {}, "weights_sha256": fit["weights"], "ratio_floor": FLOOR}
    if mode == "historical":
        check(fixture is None, "unexpected manifest")
        for name in ("owner-rankings.json","owner-progression.json"):
            path = "docs/research/WP-0027/owners/" + name
            data = blob(WP27,path)
            refs[name] = json.loads(data)
            inputs[WP27+":"+path] = sha(data)
        result["physical_windows"] = physical
        result["arithmetic_controls"] = controls()
    elif mode == "controlled":
        check(fixture, "a full /001 manifest revision is required")
        manifest = blob(fixture,FIXTURE_PATH)
        inputs[fixture+":"+FIXTURE_PATH] = sha(manifest)
        result["intake"] = {"revision":fixture, "path":FIXTURE_PATH, "sha256":sha(manifest)}
        manifest = json.loads(manifest)
    else:
        raise ValueError("unknown mode")
    elapsed = {}
    with torch.inference_mode():
        for arm in ("M1","M3"):
            arm_start = time.process_time()
            model = matrix.Memory(flat=arm == "M1").eval()
            model.load_state_dict(torch.load(work/(arm+".pt"), weights_only=True, map_location="cpu"))
            cuts = fit["thresholds"][arm]
            check(cuts == [1.,.1] and all(p.device.type == "cpu" for p in model.parameters()), "wrong frozen arm")
            if mode == "historical":
                result["arms"][arm] = history(model,cuts,run.manifest(routed),logical,physical,
                                               refs["owner-rankings.json"]["arms"][arm],
                                               refs["owner-progression.json"]["arms"][arm])
            else:
                result["arms"][arm] = controlled(model,cuts,manifest,work,blob)
            elapsed[arm] = time.process_time()-arm_start
    if mode == "historical":
        result["formula_pdf_example"] = pdf_example(result["arms"]["M3"])
    path = work/(mode+".json")
    record(path,result)
    record(work/"runtime.json", {"mode":mode, "candidate":candidate, "reservation":RESERVATION,
           "command":sys.orig_argv, "cpu_seconds":time.process_time()-cpu_start,
           "wall_seconds":time.perf_counter()-start,"arm_cpu_seconds":elapsed,
           "executable":sys.executable,"python":sys.version,"interpreter_sha256":sha(Path(sys.executable).read_bytes()),
           "torch":str(torch.__version__), "deterministic":torch.are_deterministic_algorithms_enabled(),
           "threads":torch.get_num_threads(),"interop_threads":torch.get_num_interop_threads(),
           "cuda_visible_devices":os.environ["CUDA_VISIBLE_DEVICES"],"native_ocr_or_gpu_calls":0,
           "sources_sha256":sources,"inputs_sha256":inputs,"result_sha256":sha(path.read_bytes()),
           "completed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()})
    print(f"{mode} complete, result SHA-256 {sha(path.read_bytes())}")


if __name__ == "__main__":
    run_main(Path(sys.argv[1]).resolve(), *sys.argv[2:])
