"""Read-only NVIDIA observer comparison; no package/model import or runtime-root creation."""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(r"C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-harness")
EXPECTED_HEAD = "460e1d81de14c6f77ea4a026bc4b3ab36407bdf7"
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
if head != EXPECTED_HEAD:
    raise SystemExit("Target changed; this diagnostic is bound to " + EXPECTED_HEAD)
sys.path.insert(0, str(REPO / "qualification/q0/harness"))
from q0harness.environment import build_child_env, build_stage_env
from q0harness.protocol import load_protocol

protocol, digest = load_protocol()
parent = dict(os.environ)
root = Path(protocol["storage"]["root"])
if root.exists():
    raise SystemExit("Pre-storage diagnostic requires the selected runtime root to remain absent")
program_files = parent.get("ProgramFiles") or parent.get("PROGRAMFILES")
if not program_files:
    raise SystemExit("No host ProgramFiles value is available for this comparison")
stage = build_stage_env(parent, root=root, protocol=protocol, network=False)
child = build_child_env(parent, root=root, owner="author", run_dir=root / "runs/author/readonly-nvml-probe",
                        gpu_uuid=protocol["gpu"]["uuid"])
record = {
    "schema": "eldq0-nvml-environment-observation/1",
    "started_utc": datetime.now(timezone.utc).isoformat(),
    "harness_head": head,
    "source_candidate": "24a5866b505532fd03e7db62a4e57875e4c5a170",
    "protocol_sha256": digest,
    "program_files_value": program_files,
    "observations": [],
}
for label, env in (("host_parent", parent), ("stage_as_built", stage), ("child_as_built", child),
                   ("stage_plus_ProgramFiles", stage | {"ProgramFiles": program_files}),
                   ("child_plus_ProgramFiles", child | {"ProgramFiles": program_files})):
    row = {"environment": label, "queries": []}
    for argv in protocol["gpu"]["observer"]["commands"]:
        cp = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=30)
        row["queries"].append({"argv": argv, "returncode": cp.returncode,
                               "stdout": cp.stdout, "stderr": cp.stderr})
    record["observations"].append(row)
record["external_runtime_root_exists_after"] = root.exists()
record["torch_or_transformers_imported"] = any(x in sys.modules for x in ("torch", "transformers"))
record["finished_utc"] = datetime.now(timezone.utc).isoformat()
record["scope"] = "Read-only nvidia-smi subprocesses; no model execution, CUDA allocation, or acceptance inference."
print(json.dumps(record, indent=2))
