"""Paths and write-once records shared by CPU-only acquisition evidence tools."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MAIN = Path("C:/Users/jackg/Asp.net Projects/eledgercare")
PART = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0029")
SCRATCH = PART / "acquisition"
RUN = SCRATCH / "runs/cedar-r1"
LEASE = PART / "coordination/leases/cedar-r1"
DEVICE = ROOT.parent / "w029-device"
Q0 = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005")
GPU = "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d"
BASE = "4d94271a56f550bcf96b76d970f54e4c8b845ad5"
SCOPE = ROOT / "docs/coordination/WP-0028/acquisition-scope.json"
SCOPE_HASH = "887772656057b4188118adc5b7501bfb592f196ccd6decb496d8dbd3ba9a08b1"
WARM = ROOT / "docs/fixtures/WP-0026/w0"
SOURCE = ROOT / "docs/fixtures/WP-0028"

def require(value, message):
    if not value:
        raise ValueError(message)

def utc():
    return datetime.now(timezone.utc).isoformat()

def check_env():
    require(sys.flags.isolated and sys.dont_write_bytecode and not sys.flags.optimize, "Use -I -B")
    require(Path(sys.executable).resolve() == Q0 / "venv/Scripts/python.exe", "Unexpected interpreter")
    require(os.environ.get("CUDA_VISIBLE_DEVICES") == "-1", "Evidence tools are CPU only")

def sha(data):
    return hashlib.sha256(data).hexdigest()

def file_sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()

def checked(path, expected):
    require(file_sha(path) == expected, "Wrong digest for " + str(path))
    return json.loads(path.read_bytes())

def text_cmd(argv):
    return subprocess.check_output(argv, cwd=ROOT, text=True, timeout=35).strip()

def json_bytes(obj):
    return (json.dumps(obj, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode()

def keep(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f:
        f.write(json_bytes(obj))

def freeze():
    return text_cmd(["git", "rev-parse", "HEAD"])

def git_identity(path, revision):
    return text_cmd(["git", "rev-parse", revision + ":" + path])
