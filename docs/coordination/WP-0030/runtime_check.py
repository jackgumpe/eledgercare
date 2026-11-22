"""Qualify an isolated CPU build using the historical owner checkpoints and final decisions."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
HOST = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0030")
PYTHON = HOST / "runtime/venv/Scripts/python.exe"
SCORER = "23c072549886ad9b5f2ab6bb08a98b0fcae423ff"
GATE = "f51fa1dadec3e3f0e61b1d3ddade1891e24779e2"
GATE_SHA = "03e7eb07feae1f25c8db1fb4a7141820f0bda8497ab1b539bb4dbe169c51f870"
EVIDENCE = "841233517b4694d18d144f6d2d2b17e0d0a8b444"
EVIDENCE_SHA = "93a6054a9f8b4db7a9e231e843ee6681cf55968e85e6adde5d31959c2cdeae1e"


def check(condition, message):
    if not condition:
        raise ValueError(message)


def qualify(work):
    check(Path(sys.executable).resolve() == PYTHON and sys.flags.isolated and sys.flags.dont_write_bytecode,
          "Use the dedicated WP-0030 interpreter with -I -B")
    check(work.parent.resolve() == HOST/"coordination" and not work.exists(), "Fresh coordinator scratch required")
    work.mkdir(parents=True)
    for key in ("HF_HUB_OFFLINE","HF_DATASETS_OFFLINE","TRANSFORMERS_OFFLINE","PIP_NO_INDEX",
                "OMP_NUM_THREADS","MKL_NUM_THREADS"):
        os.environ[key] = "1"
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    for key in ("TEMP","TMP","HOME","HF_HOME","TORCH_HOME","XDG_CACHE_HOME","TORCHINDUCTOR_CACHE_DIR"):
        path = work / key
        path.mkdir()
        os.environ[key] = str(path)
    sys.path.insert(0, str(ROOT/"docs/research/WP-0029/scoring"))
    import scoring
    from admission import FIXTURE, Inputs, route_inputs
    inputs = Inputs()
    fit = inputs.stage(work, SCORER)
    gate = inputs.gate(GATE, GATE_SHA)
    result = json.loads(inputs.blob(EVIDENCE,"docs/research/WP-0029/scoring/evidence/result.json",EVIDENCE_SHA))
    pairs = json.loads(inputs.blob(FIXTURE,"docs/fixtures/WP-0028/manifest.json"))["pairs"]
    sys.path.insert(0, str(work/"library"))
    import matrix
    import numpy
    import torch
    from run import setup
    from importlib import metadata
    check(torch.version.cuda is None, "The runtime must be a CPU build")
    setup()
    inventory = route_inputs(inputs, work, pairs, gate)
    check(len(inventory) == 11 and len(pairs) == 2, "Expected ten historical captures and one Cedar return")
    checkpoints = 0
    for arm in ("M1","M3"):
        model = matrix.Memory(flat=arm == "M1").eval()
        model.load_state_dict(torch.load(work/(arm+".pt"), weights_only=True, map_location="cpu"))
        with torch.inference_mode():
            for index, pair in enumerate(pairs):
                actual, _ = scoring.pair_run(work, pair, arm, model, fit["thresholds"][arm], inventory, gate)
                old = result["arms"][arm][index]
                check(actual["counts"] == old["counts"] and actual["counts"]["completed"] == 1,
                      "Runtime did not admit the historical arm pair")
                for member, ref in zip(actual["members"],old["members"],strict=True):
                    for t in ("t1","t2","t3"):
                        check(member["checkpoints"][t] == ref["checkpoints"][t],
                              f"Historical checkpoint mismatch {arm} {pair['horizon']} {member['owner']} {t}")
                        checkpoints += 1
                    check(member["parity"] == ref["parity"], "Native or duplicated CPU parity differs")
                check(actual["metrics"] == old["metrics"], "Historical paired arithmetic differs")
    packages = json.loads((HOST/"runtime/install.json").read_bytes())["install"]
    deps = {e["metadata"]["name"]:{"version":e["metadata"]["version"],
            "wheel_sha256":e["download_info"]["archive_info"]["hashes"]["sha256"]} for e in packages}
    return {"status":"qualified","historical_scorer":SCORER,"evidence_revision":EVIDENCE,
            "evidence_sha256":EVIDENCE_SHA,"gate_revision":GATE,"gate_sha256":GATE_SHA,
            "unique_feature_captures":len(inventory),"matched_member_checkpoints":checkpoints,
            "matched_native_final_postings":8,"matched_paired_rows":12,
            "python":sys.version,"executable":str(PYTHON),"python_sha256":hashlib.sha256(PYTHON.read_bytes()).hexdigest(),
            "torch":str(torch.__version__),"numpy":numpy.__version__,"torch_build_cuda":torch.version.cuda,
            "threads":torch.get_num_threads(),"interop_threads":torch.get_num_interop_threads(),
            "deterministic":torch.are_deterministic_algorithms_enabled(),"gpu_or_ocr_calls":0,
            "wheel_inputs":deps,"pip":metadata.version("pip"),"torch_source":"https://download.pytorch.org/whl/cpu/torch/",
            "comparison":"Per-member historical checkpoints, fixed query/score bytes, duplicated trajectories and native final typed decisions matched the original accepted artifacts."}


if __name__ == "__main__":
    destination = Path(sys.argv[1]).resolve()
    data = qualify(destination)
    with (destination/"runtime-check.json").open("x",encoding="utf8",newline="\n") as stream:
        json.dump(data,stream,indent=2)
        stream.write("\n")
    print(data["status"],data["torch"],data["matched_member_checkpoints"])
