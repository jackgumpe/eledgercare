"""Freeze the two WP-0025 orders from the historical first window at a clean runner revision."""
import argparse
from hashlib import sha256
import io
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
P = "docs/coordination/WP-0025"
sys.path[:0] = [str(HERE), str(ROOT / "workers/local_ocr")]
from device_lease import guard
from local_ocr import protocol
from supervise import environment, HOST, QPY


SENSOR_REV = "1843cdb7b6279b84b539d3ca1ba7bd0affa1f7dd"
ARCHIVE = "37670af4116f543e2d0104b5d3599d88f2e2d06fc092418ee1cf839769430fc6"
OLD_PLAN = "0bf358c54fc97f32ca213d9a1dd10cfb2838f42f7c5dcded1625c0cca1fd2f89"
LABEL = "window-repeat-r1"
DEADLINE = 1200


def git(repo, *args):
    return subprocess.check_output(["git", "-C", repo, *args], text=True).strip()


def read(path):
    return json.loads(path.read_bytes())


def prior():
    old = ROOT / "docs/reviews/WP-0024/h0-r1.zip"
    if guard.sha(old) != ARCHIVE:
        raise ValueError("WP-0024 archive changed")
    with ZipFile(old) as archive:
        raw = archive.read("binding/h0-r1-plan.json")
        if sha256(raw).hexdigest() != OLD_PLAN or raw != (HERE.parent / "WP-0024/h0-r1-plan.json").read_bytes():
            raise ValueError("Historical input plan changed")
        plan = json.loads(raw)
        call, other = plan["calls"][:2]
        if (plan["candidate"] != SENSOR_REV or [call["tag"], other["tag"]] != ["b01w01S", "b01w01H"] or
                call["pages"] != other["pages"] or len(call["pages"]) != 3):
            raise ValueError("Expected the original b01w01 raster triple")
        for page in call["pages"]:
            encoded = Path(page["image"]).read_bytes()
            if sha256(encoded).hexdigest() != page["sha256"]:
                raise ValueError("Changed PNG")
            with Image.open(io.BytesIO(encoded)) as src:
                rgb = src.convert("RGB")
                if rgb.size != (2550, 3300) or sha256(rgb.tobytes()).hexdigest() != page["rgb_sha256"]:
                    raise ValueError("Changed 300 dpi RGB bytes")
        def record(name):
            return json.loads(archive.read("run/sensor/" + name))
        stock, hooked = (record(tag + "/native.json") for tag in ("b01w01S", "b01w01H"))
        prompt_sha = record("b01w01S/duration.json")["prompt_sha256"]
        serial = (json.dumps(stock["prompt_token_ids"], separators=(",", ":")) + "\n").encode("ascii")
        if (stock["prompt"] != hooked["prompt"] or stock["prompt_token_ids"] != hooked["prompt_token_ids"] or
                sha256(serial).hexdigest() != prompt_sha or len(stock["prompt_token_ids"]) != 827):
            raise ValueError("Historical prompt binding failed")
        return plan, call, record("cold.json")["model"], stock, prompt_sha


def source_files(repo, candidate):
    common = ["docs/coordination/WP-0016/device_lease.py", "qualification/baseline/winjob.py",
              "docs/research/WP-0015/astra/native.py", "docs/research/WP-0015/astra/formats.py",
              "docs/research/WP-0015/astra/sensitivity-title-level/rescore.py", "docs/research/WP-0023/trial/stock.py",
              "docs/research/WP-0024/sensor", "workers/local_ocr/local_ocr",
              "workers/local_ocr/manifests/dependency-lock.json", "workers/local_ocr/manifests/model-files.json"]
    common.extend("docs/research/WP-0014/eld-latency-author/" + name
                  for name in ("probe.py", "cases.py", "fixtures.py", "generation.py"))
    historical = git(repo, "ls-files", "--", *common).splitlines()
    for rel in historical:
        if git(repo, "rev-parse", SENSOR_REV + ":" + rel) != git(repo, "rev-parse", candidate + ":" + rel):
            raise ValueError("A frozen dependency changed: " + rel)
    old_release = read(HERE.parent / "WP-0024/h0-r1-release.json")
    for rel in set(historical) & old_release["source_files"].keys():
        if guard.sha(repo / rel) != old_release["source_files"][rel]:
            raise ValueError("Historical source bytes changed: " + rel)
    new = git(repo, "ls-files", "--", "docs/research/WP-0025/runner", P + "/supervise.py",
              "docs/reviews/WP-0024/admission-watch-binding.json", P + "/device_lease.py", P + "/bind.py").splitlines()
    if "docs/research/WP-0025/runner/process.py" not in new:
        raise ValueError("No committed runner at this candidate")
    return {rel: guard.sha(repo / rel) for rel in sorted(set(new + historical))}


def bind(repo, candidate):
    if git(repo, "rev-parse", "HEAD") != candidate or git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Execution checkout must be clean at the full release revision")
    old, call, cold, stock, prompt_sha = prior()
    historical_request = next(r for r in old["requests"] if Path(r["pdf"]).stem == call["binder"])
    if guard.sha(Path(historical_request["pdf"])) != historical_request["sha256"]:
        raise ValueError("Source PDF changed")
    source = source_files(repo, candidate)
    coordin = {key: guard.sha(ROOT / key) for key in source if key.startswith(P + "/") or
               key in ("docs/coordination/WP-0016/device_lease.py", "qualification/baseline/winjob.py",
                       "docs/reviews/WP-0024/admission-watch-binding.json")}
    if any(source[k] != v for k, v in coordin.items()):
        raise ValueError("Coordinator dependency differs from candidate")
    if read(HERE / "q0-before.json") != read(HERE.parent / "WP-0024/q0-after.json"):
        raise ValueError("Q0 inventory differs from the verified WP-0024 return")
    staging = HOST / "coordination/preflight"
    staging.mkdir(parents=True, exist_ok=True)
    plans = []
    for index, modes in enumerate(("SHHS", "HSSH"), 1):
        pid = f"P{index}"
        output = HOST / "review/runs" / pid.lower()
        if output.exists():
            raise FileExistsError(output)
        with TemporaryDirectory(dir=staging) as temp:
            scratch = Path(temp)
            env = {key: value.replace(str(scratch), str(output / "sensor"))
                   for key, value in environment(scratch).items()}
        settings = protocol.build_call_kwargs(3)
        plans.append({
            "packet": "WP-0025", "phase": "H0 repeatability", "lease": LABEL, "process_id": pid,
            "process_ordinal": index, "deadline_seconds": DEADLINE, "candidate": candidate, "output": str(output),
            "raster_root": old["raster_root"], "historical_plan_sha256": OLD_PLAN, "historical_archive_sha256": ARCHIVE,
            "historical_sensor_revision": SENSOR_REV, "model_revision": old["model_revision"],
            "module_sha256": old["module_sha256"], "tokenizer_sha256": cold["tokenizer_sha256"],
            "model_manifest_sha256": cold["manifest_sha256"], "environment_lock_sha256": cold["dependency_lock_sha256"],
            "target_dtype": cold["target_dtype"], "historical_platform": cold["platform"],
            "q0_python": str(QPY), "executable_sha256": guard.sha(QPY), "interpreter_flags": ["-I", "-B"],
            "settings": settings, "environment": env, "prompt": stock["prompt"], "api_prompt": protocol.PROMPT,
            "prompt_token_ids": stock["prompt_token_ids"], "prompt_sha256": prompt_sha, "eos_id": stock["eos_id"],
            "requests": [historical_request],
            "calls": [{"tag": f"{pid}J{j}{mode}", "ordinal": j, "mode": mode, "hooked": mode == "H",
                       "retain_hidden": mode == "H", "pages": call["pages"]} for j, mode in enumerate(modes, 1)],
        })
    paths = [HERE / "p1-plan.json", HERE / "p2-plan.json", HERE / (LABEL + "-release.json")]
    if any(p.exists() for p in paths) or (HOST / "coordination/leases" / LABEL).exists():
        raise FileExistsError("The release namespace is already occupied")
    orders = []
    for plan, path in zip(plans, paths[:2], strict=True):
        guard.dump(path, plan)
        digest = guard.sha(path)
        orders.append({"run": plan["process_id"].lower(), "plan": str(path), "plan_sha256": digest,
                       "output": plan["output"], "seconds": DEADLINE,
                       "argv": [str(QPY), "-I", "-B", str(repo / P / "supervise.py"), str(path), digest]})
    lease = {"packet": "WP-0025", "name": LABEL, "operator": "eld-repeat-reviewer", "prepared_utc": guard.utc(),
             "review_worktree_head": candidate, "worktree": str(repo), "gpu_uuid": guard.GPU, "ceiling_mib": 12500,
             "free_floor_mib": 12000, "source_files": source, "coordination_files": coordin, "orders": orders}
    guard.dump(paths[2], lease)
    print(json.dumps({p.name: guard.sha(p) for p in paths}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("candidate")
    args = parser.parse_args()
    bind(args.repo.resolve(), args.candidate)
