"""Set the packet CPU boundary before importing any numerical or tokenizer package."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
SPEED = Path("C:/Users/jackg/eLedgerCare-Speed")
SCRATCH = SPEED / "WP-0027/review"
QPY = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe")
BASE = "ce04b773329c3c67cd0ab4b578ddf442690019a0"
assert Path(sys.executable).resolve() == QPY.resolve() and sys.flags.isolated and sys.dont_write_bytecode and not sys.flags.optimize
assert os.environ["CUDA_VISIBLE_DEVICES"] == "-1"
for name in ("TEMP","TMP","LOCALAPPDATA","APPDATA","HF_HOME","TORCH_HOME","TORCH_EXTENSIONS_DIR",
             "TORCHINDUCTOR_CACHE_DIR","MPLCONFIGDIR","XDG_CACHE_HOME"):
    path = SCRATCH / "environment" / name
    path.mkdir(parents=True, exist_ok=True)
    os.environ[name] = str(path)
os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
                  CUDA_CACHE_DISABLE="1", TOKENIZERS_PARALLELISM="false")

def sha(raw):
    return sha256(raw).hexdigest()

def blob(commit, path):
    return subprocess.check_output(["git","-C",str(ROOT),"show",f"{commit}:{path}"])

def loaded(commit, path):
    return json.loads(blob(commit,path))

def save(path, record):
    with path.open("x", encoding="utf8", newline="\n") as handle:
        json.dump(record, handle, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
