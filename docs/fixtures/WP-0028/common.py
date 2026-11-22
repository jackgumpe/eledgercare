"""Fixed WP-0028 development inputs and content-addressed output helpers."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEST = Path("docs/fixtures/WP-0028")
BASE = "c000c0299619345c887859b95c45befbb0c68987"
CUSTODY = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0024/custody/v2")
TRUTH = CUSTODY / "private/cal/truth.json"
TRUTH_PIN = "a227da1293bcd6f8b0f636ce3349abd12d02a52361a46b47dbf34969cc773ff1"
CASES = {
    12: ("366ef9f7a5a787497b0f6634", "388abc9b198838d05730e328", "c68d80f8a27dd80a95e5aea0"),
    30: ("dd21685671af3251fb1cbcd6", "770f5bcd4ed40c3ff28a3905", "3d942ef5cf4ec8f1ce6b503f"),
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def encode(obj):
    return (json.dumps(obj, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")

def git_blob(path, revision=BASE):
    return subprocess.check_output(["git", "-C", ROOT, "show", revision + ":" + str(path).replace("\\", "/")])

def pinned(raw, digest):
    if sha(raw) != digest:
        raise ValueError("input digest mismatch: expected " + digest)
    return raw

def checked_json(raw, digest):
    return json.loads(pinned(raw, digest))

def keep(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"refusing to replace different bytes at {path}")
    else:
        with path.open("xb") as file:
            file.write(data)

def triple(pages):
    assert len(pages) == 3
    return sha(encode([p["rgb_sha256"] for p in pages]))

def identity(pages):
    return tuple((p["sha256"], p["rgb_sha256"]) for p in pages)

def case_id(template, suffix):
    return sha(f"WP-0028/{template}/{suffix}".encode("ascii"))[:24]

def cpu(scratch):
    assert sys.flags.isolated and sys.dont_write_bytecode and not sys.flags.optimize
    assert Path(sys.executable).resolve() == Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe").resolve()
    os.environ.update(CUDA_VISIBLE_DEVICES="-1", CUDA_CACHE_DISABLE="1", HF_HUB_OFFLINE="1",
                      TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", TOKENIZERS_PARALLELISM="false",
                      OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    for k in ("TMP", "TEMP", "HF_HOME", "TORCH_HOME", "XDG_CACHE_HOME", "MPLCONFIGDIR"):
        path = scratch / "cache" / k
        path.mkdir(parents=True, exist_ok=True)
        os.environ[k] = str(path)
    os.chdir(ROOT)
