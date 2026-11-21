"""Read signed inputs and the frozen independent WP24 span and PDF readers on CPU."""
from hashlib import sha256
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HIST = ROOT / "docs/reviews/WP-0024"
HOST = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0026")
SCRATCH = HOST / "review/cpu"
QPY = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe")
BASE = "f05dcc4c1f5ca7d7ecd82e83ca63f889369bc6fd"
ARCHIVE25 = "60a9ffe3c610e06669daff98a88aa3da062df553"
H0_PLAN = "0bf358c54fc97f32ca213d9a1dd10cfb2838f42f7c5dcded1625c0cca1fd2f89"
WITNESS = "dfb55b56833599f111eb29e2b3d4b8a7de9eab13b8caae277e09c9ba60271989"
LAYER = "native model.model final normalized decoder state, lm_head input, after consuming emitted token"
MODEL = "0480966938291445591f69f08a13b041c073a96a"

def cpu():
    assert sys.flags.isolated and sys.dont_write_bytecode and not sys.flags.optimize
    assert Path(sys.executable).resolve() == QPY.resolve()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    for name in ("TMP", "TEMP", "TORCH_HOME", "HF_HOME", "LOCALAPPDATA", "APPDATA", "TORCHINDUCTOR_CACHE_DIR",
                 "TORCH_EXTENSIONS_DIR", "MPLCONFIGDIR"):
        target = SCRATCH/name.lower()
        target.mkdir(exist_ok=True)
        os.environ[name] = str(target)
    os.environ.update(CUDA_VISIBLE_DEVICES="-1", CUDA_CACHE_DISABLE="1", HF_HUB_OFFLINE="1",
                      TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    sys.path.insert(0, str(HIST))

def sha(raw):
    return sha256(raw).hexdigest()

def blob(revision, path):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", revision+":"+path])

def read(path):
    return json.loads(path.read_bytes())

def save(path, record):
    with path.open("x", encoding="utf8", newline="\n") as handle:
        json.dump(record, handle, ensure_ascii=True, allow_nan=False, indent=2)
        handle.write("\n")

def pinned(path, digest):
    raw = path.read_bytes()
    assert sha(raw) == digest, path
    return json.loads(raw)

def stream(directory, explicit=True):
    native = read(directory/"native.json")
    ids, term = native["token_ids"], native["terminal_observation"]
    assert native["eos_observed"] is True and native["stop_cause"] == "eos"
    assert term["nxt"] == native["eos_id"] == 1 and 1 not in ids and term["step"] == len(ids)
    assert term["prompt_length"] == len(native["prompt_token_ids"]) == 827
    assert native["expected_pages"] == native["num_pages_out"] == 3
    encoded = struct.pack("<"+"I"*(len(ids)+1), *ids, term["nxt"])
    if explicit:
        assert (directory/"through-eos.u32le").read_bytes() == encoded
    return encoded

def sample(directory, hooked, reference, explicit=True):
    from span_audit import snapshot
    native = read(directory/"native.json")
    assert native["prompt_token_ids"] == reference["prompt_token_ids"] and native["prompt"] == reference["prompt"]
    raw = stream(directory, explicit)
    for file in ("token_hidden.bf16", "pooled.f32", "observed-positions.json", "capture.json"):
        assert (directory/file).is_file() == hooked, (directory, file)
    result = snapshot(directory)
    if hooked:
        capture = read(directory/"capture.json")
        assert capture["native_dtype"] == "bfloat16" and capture["pool_dtype"] == "little-endian float32"
        assert capture["capture_layer"] == LAYER and capture["position_start"] == 827
        assert capture["position_stop_exclusive"] == 827 + result["positions"]
        assert capture["hidden_shape"] == [result["positions"], 1280]
        assert capture["pool_shape"] == [result["pooled_bit_exact"], 1280]
    return result | {"through_eos_sha256":sha(raw), "through_eos_bytes":len(raw)}

def reference():
    return json.loads(blob(ARCHIVE25, "docs/coordination/WP-0025/p1-plan.json"))
