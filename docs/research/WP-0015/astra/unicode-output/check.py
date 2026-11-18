"""Exercise TextStreamer on redirected Windows handles with -I and zero OCR calls."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRIAL_DIR = HERE.parent
ROOT = TRIAL_DIR.parents[3]
sys.path.insert(0, str(ROOT/"docs/research/WP-0014/eld-latency-author"))
from probe import isolated_env

PAYLOAD = "Synthetic \u6a5f \u03a9 \U0001f9fe"
CHILD = r"""
import json, os, runpy, sys
from pathlib import Path
trial_dir, scratch, mode, payload = sys.argv[1:]
before = [sys.stdout.encoding, sys.stderr.encoding]
assert sys.flags.isolated and sys.flags.ignore_environment
assert not sys.stdout.isatty() and not sys.stderr.isatty()
assert before == ["cp1252", "cp1252"], before
assert os.environ["PYTHONIOENCODING"] == "utf-8"
sys.path.insert(0, trial_dir)
if mode == "main":
    sys.argv = [str(Path(trial_dir)/"trial.py"), scratch]
    runpy.run_path(sys.argv[0], run_name="__main__")
elif mode == "import":
    from trial import document
from transformers import TextStreamer
import torch
assert not torch.cuda.is_initialized()
after = [sys.stdout.encoding, sys.stderr.encoding]
Path(scratch, "metadata.json").write_text(json.dumps(dict(before=before, after=after, isolated=sys.flags.isolated,
    ignore_environment=sys.flags.ignore_environment, stdout_errors=sys.stdout.errors, stderr_errors=sys.stderr.errors,
    cuda_initialized=torch.cuda.is_initialized(), python=sys.version.split()[0])), encoding="utf-8")
TextStreamer.on_finalized_text(None, payload)
print(payload, file=sys.stderr, end="", flush=True)
"""


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("scratch", type=Path, help="New owned local scratch directory")
    args = parser.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=False)
    result = {}
    for mode in ("unconfigured", "import", "main"):
        folder = args.scratch.resolve()/mode
        folder.mkdir()
        (folder/"plan.json").write_text('{"requests":[]}', encoding="ascii")
        env = isolated_env(folder)
        env["PYTHONIOENCODING"] = "utf-8"
        cmd = [sys.executable, "-I", "-B", "-c", CHILD, str(TRIAL_DIR), str(folder), mode, PAYLOAD]
        with (folder/"stdout.bin").open("xb") as out, (folder/"stderr.bin").open("xb") as err:
            completed = subprocess.run(cmd, cwd=folder, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err, timeout=60)
        stdout = (folder/"stdout.bin").read_bytes()
        stderr = (folder/"stderr.bin").read_bytes()
        meta = json.loads((folder/"metadata.json").read_bytes())
        if mode == "unconfigured":
            assert completed.returncode != 0 and not stdout and b"UnicodeEncodeError" in stderr
            assert meta["after"] == meta["before"]
        else:
            assert completed.returncode == 0 and stdout == PAYLOAD.encode("utf-8") and stderr.endswith(stdout)
            assert meta["after"] == ["utf-8","utf-8"]
            if mode == "main":
                assert json.loads((folder/"session.json").read_bytes()) == []
        result[mode] = dict(**meta, exit_code=completed.returncode, stdout_hex=stdout.hex(),
            stdout_sha256=hashlib.sha256(stdout).hexdigest(), stderr_ends_with_utf8_payload=stderr.endswith(PAYLOAD.encode("utf-8")),
            error_name="UnicodeEncodeError" if mode == "unconfigured" else None)
    receipt = dict(test="redirected binary files, actual transformers TextStreamer.on_finalized_text, -I -B",
                   expected_utf8_hex=PAYLOAD.encode("utf-8").hex(), model_calls=0, tests=result)
    (args.scratch/"receipt.json").write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
