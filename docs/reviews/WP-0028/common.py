"""Restrict this independent CPU audit to one reviewer's runtime and scratch."""
from hashlib import sha256
from pathlib import Path
import json
import os
import subprocess
import sys

ROOT = Path.cwd()
BASE = "c000c0299619345c887859b95c45befbb0c68987"
PROBE = "7db67283a4ffd3e7a20bb8d80499572cc7118c71"
FIT = "6d79c24364ba10a1d9bfa4c72c837e2f216cf4bc"
HISTORY = "0573f69c481eea2e815899e00ddd5e68bb4e3c42"
WORK = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0028/review")
DEV = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0024/custody/v2")
assert Path(sys.executable).resolve() == Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe").resolve()
assert sys.flags.isolated and sys.dont_write_bytecode and not sys.flags.optimize
assert ROOT.name == "w028-review"
for key in ("TEMP", "TMP", "TMPDIR", "LOCALAPPDATA", "APPDATA", "HF_HOME", "TORCH_HOME",
            "TORCH_EXTENSIONS_DIR", "TORCHINDUCTOR_CACHE_DIR", "XDG_CACHE_HOME", "MPLCONFIGDIR"):
    directory = WORK / "cache" / key
    directory.mkdir(parents=True, exist_ok=True)
    os.environ[key] = str(directory)
os.environ.update(CUDA_VISIBLE_DEVICES="-1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                  HF_DATASETS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", PIP_NO_INDEX="1",
                  OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
def sha(raw):
    return sha256(raw).hexdigest()

def blob(rev, path):
    return subprocess.check_output(["git", "cat-file", "blob", f"{rev}:{path}"], cwd=ROOT)

def js(path):
    return json.loads(path.read_bytes())

def output(name, data):
    with (WORK/name).open("x", encoding="utf8", newline="\n") as fh:
        json.dump(data, fh, indent=2, sort_keys=True, allow_nan=False)
        fh.write("\n")

def pinned(rev, rel):
    data = (ROOT / rel).read_bytes()
    assert data == blob(rev, rel), rel
    return data
