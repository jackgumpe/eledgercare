"""Run the frozen author candidate once, into a new owned scratch directory."""
import datetime
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = "74f23b10d428acc3477db6ce4af7eb663e28d9f4"
SPEED = Path("C:/Users/jackg/eLedgerCare-Speed")
PYTHON = SPEED / "WP-0030/runtime/venv/Scripts/python.exe"
PYTHON_SHA = "0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def run(candidate):
    assert re.fullmatch("[0-9a-f]{40}", candidate) and git("rev-parse", "HEAD").decode().strip() == candidate
    assert git("merge-base", BASE, candidate).decode().strip() == BASE
    for name in ("replay.py", "inputs.py", "experiment.py"):
        path = HERE / name
        frozen = git("cat-file", "blob", f"{candidate}:{path.relative_to(ROOT).as_posix()}")
        assert path.read_bytes().replace(b"\r\n", b"\n") == frozen.replace(b"\r\n", b"\n")
    assert sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.optimize
    assert Path(sys.executable).resolve() == PYTHON.resolve() and sys.byteorder == "little"
    assert hashlib.sha256(PYTHON.read_bytes()).hexdigest() == PYTHON_SHA and sys.version_info[:3] == (3, 12, 10)
    work = SPEED / "WP-0031/author" / candidate
    work.mkdir(parents=True, exist_ok=False)
    evidence = work / "evidence"
    for key in ("TEMP", "TMP", "TORCH_HOME", "XDG_CACHE_HOME", "TORCHINDUCTOR_CACHE_DIR", "HF_HOME"):
        owned = work / key
        owned.mkdir()
        os.environ[key] = str(owned)
    os.environ.update(HF_HUB_OFFLINE="1", HF_DATASETS_OFFLINE="1", TRANSFORMERS_OFFLINE="1", PIP_NO_INDEX="1",
                      CUDA_VISIBLE_DEVICES="-1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    sys.path.insert(0, str(HERE))
    from inputs import archive_helpers, inputs
    archive = archive_helpers(work / "library")
    captures, weights, thresholds, archived_anchors, bindings, steps = inputs(archive, work)
    sys.path.insert(0, str(work / "library"))
    import torch
    import numpy
    from experiment import run_arm
    assert str(torch.__version__) == "2.13.0+cpu" and torch.version.cuda is None and numpy.__version__ == "2.2.6"
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.default_generator.manual_seed(2401)
    assert torch.get_num_threads() == torch.get_num_interop_threads() == 1 and torch.get_default_dtype() == torch.float32

    def save(name, value):
        archive.write(evidence / name, (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())

    start = time.perf_counter()
    save("inputs.json", {"captures": captures, "blobs_sha256": archive.RECEIPTS})
    with torch.inference_mode():
        for arm in ("M1", "M3"):
            result = run_arm(arm, weights[arm], thresholds[arm], archived_anchors[arm], bindings, steps,
                             captures, work, evidence, archive.write)
            save(arm + ".json", result)
            print(arm, result["status"], result["contrasts"], result["trigger"], flush=True)
    save("runtime.json", {"candidate": candidate, "base": BASE, "argv": sys.orig_argv,
         "git_head": git("rev-parse", "HEAD").decode().strip(), "worktree": str(ROOT), "scratch": str(work),
         "python": sys.version, "python_sha256": PYTHON_SHA, "torch": str(torch.__version__), "numpy": numpy.__version__,
         "torch_build_cuda": torch.version.cuda, "deterministic": torch.are_deterministic_algorithms_enabled(),
         "intraop_threads": torch.get_num_threads(), "interop_threads": torch.get_num_interop_threads(),
         "platform": platform.platform(), "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
         "compute_wall_seconds": time.perf_counter() - start,
         "evidence_sha256": {p.name: archive.sha(p.read_bytes()) for p in evidence.iterdir()}})


if __name__ == "__main__":
    run(*sys.argv[1:])
