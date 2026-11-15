"""Read-only coordinator diagnostic: no root creation, packages, model or GPU."""
import json
import os
import subprocess
import sys
from pathlib import Path

repo = Path(r"C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-harness")
harness = repo / "qualification/q0/harness"
sys.path.insert(0, str(harness))
from q0harness.environment import build_child_env, build_stage_env

protocol = json.loads((harness / "protocol.json").read_text(encoding="utf-8"))
root = Path(protocol["storage"]["root"])
probe = """import json,shutil,subprocess,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from q0harness.release import code_identity
out={'git_which':shutil.which('git')}
try:
    out['code_identity']=code_identity(Path(sys.argv[2]))
except Exception as exc:
    out['error']={'type':type(exc).__name__,'text':str(exc)}
print(json.dumps(out))
"""
rows = {}
envs = {
    "install_stage": build_stage_env(dict(os.environ), root=root, protocol=protocol, network=False),
    "runtime_child": build_child_env(dict(os.environ), root=root, owner="author",
        run_dir=root / "runs/author/coordinator-readonly-probe", gpu_uuid=protocol["gpu"]["uuid"]),
}
for name, env in envs.items():
    cp = subprocess.run([sys.executable, "-I", "-B", "-c", probe, str(harness), str(repo)],
        env=env, cwd=repo, capture_output=True, text=True)
    rows[name] = {"returncode": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr}
print(json.dumps({"harness_revision":subprocess.check_output(["git","rev-parse","HEAD"],cwd=repo,text=True).strip(),
    "runtime_root_exists":root.exists(), "observations":rows},indent=2))
