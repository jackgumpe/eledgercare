"""Run the exact pinned Windows venv redirector, with no model import, to expose its two executable names."""
import hashlib
import json
from pathlib import Path
import sys


def sig(p):
    with p.open("rb") as src:
        return hashlib.file_digest(src,"sha256").hexdigest()


p=Path(sys.executable).resolve()
q=Path(sys._base_executable).resolve()
v=Path(sys.orig_argv[0]).resolve()
print(json.dumps({"version":sys.version,"sys_executable":str(p),"sys_base_executable":str(q),"orig_argv0":str(v),
    "sha256_executable":sig(p),"sha256_base_executable":sig(q),"sha256_orig_argv0":sig(v),
    "orig_equals_base":v==q,"orig_equals_venv":v==p,"torch_loaded":"torch" in sys.modules},indent=2))
