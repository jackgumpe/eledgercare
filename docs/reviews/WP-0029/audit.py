"""Isolated CPU verification of the released, development-only Git objects."""
from hashlib import sha256
from pathlib import Path
import json
import os
import re
import subprocess
import sys

ROOT = Path.cwd()
HERE = Path(__file__).resolve().parent
BASE = "4d94271a56f550bcf96b76d970f54e4c8b845ad5"
PROPOSAL = "eb814e399d50fc9b28738751fbbf92ca3c732214"
SENSOR = "1843cdb7b6279b84b539d3ca1ba7bd0affa1f7dd"
WORKER = "9c02c9fae465dc1d1322a81c23eb3af45bbb0aff"
KEY = "33362fbbeb37e805a64acbf3afdc3ec04315a4706820ed634a8fe0fb865ce2d5"
ZIP = "docs/research/WP-0029/acquisition/native-return.zip"
GATE = "docs/reviews/WP-0029/capture-gate.json"
SCRATCH = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0029/review")
Q0 = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005")

def initialize():
    assert ROOT.name == "w029-review" and HERE == ROOT/"docs/reviews/WP-0029"
    assert sys.flags.isolated and sys.dont_write_bytecode and not sys.flags.optimize
    assert Path(sys.executable).resolve() == (Q0/"venv/Scripts/python.exe").resolve()
    os.environ.update(CUDA_VISIBLE_DEVICES="-1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                      OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                      PIP_NO_INDEX="1", HF_HUB_DISABLE_TELEMETRY="1")
    for key in ("TEMP","TMP","TMPDIR","LOCALAPPDATA","APPDATA","HF_HOME","TORCH_HOME","XDG_CACHE_HOME",
                "TORCH_EXTENSIONS_DIR","TORCHINDUCTOR_CACHE_DIR","MPLCONFIGDIR"):
        path = SCRATCH/"cache"/key
        path.mkdir(parents=True, exist_ok=True)
        os.environ[key] = str(path)

def blob(rev, path):
    assert re.fullmatch(r"[a-f0-9]{40}",rev) and "blind" not in path.lower()
    return subprocess.check_output(["git","cat-file","blob",rev+":"+path],cwd=ROOT)

def pin(rev, path):
    expected = blob(rev,path)
    assert (ROOT/path).read_bytes()==expected, path
    return expected

def sha(raw):
    return sha256(raw).hexdigest()

def canon(obj):
    return (json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False)+"\n").encode()

def save(name, obj):
    assert Path(name).name==name
    with (SCRATCH/name).open("x",encoding="utf-8",newline="\n") as stream:
        json.dump(obj,stream,sort_keys=True,indent=2,allow_nan=False)
        stream.write("\n")
