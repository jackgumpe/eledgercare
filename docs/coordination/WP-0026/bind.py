"""Freeze one phase's plans on a clean exact checkout before dispatch to the independent operator."""
import argparse
import io
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from supervise import guard, environment, QPY, HOST, OUT, P
sys.path.append(str(HERE.parent / "WP-0024"))
import corpus_plan

EARLIER = "77a858a9278cbd5480a45ece25543ab4c80d987d"
OLD = HERE.parent / "WP-0024"
H0 = OLD / "h0-r1-plan.json"
WARM = "docs/fixtures/WP-0026/w0/receipt.json"
OLD_HOST = HOST.parent / "WP-0024/custody"
BASE_KEYS = ("historical_plan_sha256", "historical_archive_sha256", "historical_sensor_revision",
             "model_revision", "module_sha256", "tokenizer_sha256", "model_manifest_sha256", "environment_lock_sha256",
             "target_dtype", "historical_platform", "q0_python", "executable_sha256", "interpreter_flags", "settings",
             "prompt", "api_prompt", "prompt_token_ids", "prompt_sha256", "eos_id")


def read(path):
    return json.loads(path.read_bytes())


def git(repo, *args):
    return subprocess.check_output(["git", "-C", repo, *args], text=True).strip()


def require(test, message):
    if not test:
        raise ValueError(message)


def warmup(repo):
    path = repo / WARM
    meta = read(path)
    folder = path.parent
    pdf = (folder / meta["pdf"]["path"]).resolve()
    require(pdf.is_relative_to(folder) and guard.sha(pdf) == meta["pdf"]["sha256"], "W0 PDF identity")
    pages = []
    for n, row in enumerate(meta["pages"], 1):
        file = (folder / row["image"]).resolve()
        require(file.is_relative_to(folder) and guard.sha(file) == row["sha256"] and row["page"] == n, "W0 order or PNG")
        with Image.open(io.BytesIO(file.read_bytes())) as src:
            rgb = src.convert("RGB")
            from hashlib import sha256
            require(rgb.size == (2550, 3300) and sha256(rgb.tobytes()).hexdigest() == row["rgb_sha256"], "W0 RGB")
        pages.append({"image": str(file), "sha256": row["sha256"], "rgb_sha256": row["rgb_sha256"]})
    require(len(pages) == len({r["rgb_sha256"] for r in pages}) == 3, "W0 requires three distinct pages")
    return {"fixture_sha256": guard.sha(path), "raster_root": str(folder), "pages": pages,
            "request": {"pdf": str(pdf), "sha256": guard.sha(pdf), "pages": 3,
                        "rgb_sha256": [i["rgb_sha256"] for i in pages]}}


def h0_orders():
    plan = read(H0)
    require(guard.sha(H0) == "0bf358c54fc97f32ca213d9a1dd10cfb2838f42f7c5dcded1625c0cca1fd2f89", "H0 plan")
    for i, pattern in enumerate(("SSSSHHHH", "HHHHSSSS"), 1):
        calls = []
        for j, mode in enumerate(pattern):
            old = plan["calls"][2*j + int(mode == "H")]
            require(old["tag"] == f"b{j//4+1:02d}w{j%4+1:02d}{mode}", "Original study order")
            calls.append(dict(old, ordinal=j+2, mode=mode))
        yield {"process_id": f"p{i}", "process_ordinal": i, "requests": plan["requests"],
               "raster_root": plan["raster_root"], "calls": calls, "check_groups": []}


def sources(repo):
    previous = read(HERE.parent / "WP-0025/window-repeat-r1-release.json")["source_files"]
    extra = git(repo, "ls-files", "--", "docs/research/WP-0026", "docs/fixtures/WP-0026/w0", P+"/*.py",
                "docs/coordination/WP-0024/corpus_plan.py", "docs/coordination/WP-0024/plan_features.py",
                "docs/coordination/WP-0024/h0-r1-plan.json", "docs/coordination/WP-0025/p1-plan.json",
                "docs/reviews/WP-0024/c1_audit.py").splitlines()
    historical_paths = sorted(set(previous) | {p for p in extra if "WP-0026/" not in p})
    require(not git(repo, "diff", "--name-only", EARLIER, "HEAD", "--", *historical_paths), "Changed frozen sources")
    pins = {p: guard.sha(repo / p) for p in sorted(set(previous) | set(extra))}
    require(all(pins[p] == v for p, v in previous.items()), "Recorded baseline source bytes changed")
    require("docs/research/WP-0026/worker.py" in pins and WARM in pins, "Missing acquisition or fixture")
    coord = {p: v for p, v in pins.items() if p.startswith(P+"/") or p in
             ("docs/coordination/WP-0016/device_lease.py", "qualification/baseline/winjob.py",
              "docs/reviews/WP-0024/admission-watch-binding.json")}
    require(all(guard.sha(ROOT / p) == v for p, v in coord.items()), "Local coordination code changed")
    return pins, coord


def corpus_order(repo, split, phase, label, prior, gate):
    if split == "blind":
        public = HOST / "custody/v2/public/blind"
        signed = repo / "docs/fixtures/WP-0026/blind"
        require(gate.get("fit_sha256") and gate.get("thresholds_frozen") and gate.get("blind_plan_sha256"),
                "Frozen blind inputs and fitted weights required")
    else:
        public = OLD_HOST / "v2/public" / split
        signed = repo / "docs/fixtures/WP-0024/v2" / split
    for name in ("manifest.json", "receipt.json", "cross-pair.json", "pairs.json"):
        require(guard.sha(public / name) == guard.sha(signed / name), "Unsigned split file "+name)
    require(gate.get("h0_accepted") and gate.get("independent_evidence"), "H0 needs independent acceptance")
    cached = None
    if phase == "features":
        require(gate.get("development_c1_accepted"), "Development C1 required")
        if split in ("train", "blind"):
            require(prior and gate.get("accepted_split") == split and gate.get("c1_plan_sha256") == guard.sha(prior),
                    "Uncached qualification must belong to this split")
            old, cached = corpus_plan.read_prior(prior)
            require(old["split"] == split and old["manifest_sha256"] == guard.sha(public/"manifest.json")
                    and old["sensor_tree"] == git(repo,"rev-parse","HEAD:docs/research/WP-0024/sensor")
                    and old["warmup"]["fixture_sha256"] == guard.sha(repo/WARM)
                    and old["model_revision"] == read(H0)["model_revision"], "Incompatible C1 provenance")
    sched = corpus_plan.schedule(public, phase, cached)
    if phase == "features" and split in ("train", "cal"):
        require(len(sched["calls"]) == {"train":11,"cal":29}[split], "Development count")
    receipt = read(public / "receipt.json")
    binders = {b["binder"]:b for b in read(public / "manifest.json")["binders"]}
    requests = []
    for b in sorted({c["binder"] for c in sched["calls"]}):
        pdf = public / "pdf" / (b+".pdf")
        pages = [p["rgb_sha256"] for window in binders[b]["windows"] for p in window["pages"]]
        require(guard.sha(pdf) == receipt["source_pdfs"][b], "Source changed")
        requests.append({"pdf":str(pdf), "sha256":guard.sha(pdf), "pages":len(pages), "rgb_sha256":pages})
    sched.update(process_id=label, process_ordinal=1, raster_root=str(public/"rasters"), requests=requests,
                 prior_c1_sha256=guard.sha(prior) if prior else None)
    sched["calls"] = [dict(c, ordinal=i, mode="H") for i,c in enumerate(sched["calls"], 2)]
    return [sched]


def bind(repo, candidate, split, phase, gate_path, gate_pin, prior):
    require(git(repo,"rev-parse","HEAD")==candidate and not git(repo,"status","--porcelain","--untracked-files=all"),
            "Clean frozen execution checkout required")
    require(read(HERE/"q0-before.json")==read(HERE.parent/"WP-0025/q0-after.json"), "Unexpected Q0 preflight")
    prev = HERE.parent / "WP-0025"
    historic_path = prev / "p1-plan.json"
    require(guard.sha(historic_path) == read(prev/"window-repeat-r1-release.json")["orders"][0]["plan_sha256"],
            "Historic prompt or execution identity changed")
    identity = {k:read(historic_path)[k] for k in BASE_KEYS}
    fixture = warmup(repo)
    source, coord = sources(repo)
    if split == phase == "h0":
        label, orders = "h0-r1", list(h0_orders())
        require(not gate_path and not prior, "Initial release")
    else:
        require((split,phase) in (("train","c1"),("train","features"),("cal","features"),("blind","c1"),("blind","features")),
                "Unknown stage")
        require(gate_path and gate_path.resolve().is_relative_to(HERE) and guard.sha(gate_path)==gate_pin,
                "Signed gate required")
        label = split+"-"+phase+"-r1"
        orders = corpus_order(repo,split,phase,label,prior,read(gate_path))
    release_path = HERE/(label+"-release.json")
    require(not release_path.exists() and not (HOST/"coordination/leases"/label).exists(), "Phase already issued")
    staging = HOST / "coordination/preflight"
    staging.mkdir(parents=True, exist_ok=True)
    issued = []
    for order in orders:
        name = order["process_id"]
        output = OUT / name
        path = HERE/(name+"-plan.json")
        require(not output.exists() and not path.exists(), "Run or plan already exists")
        with TemporaryDirectory(dir=staging) as tmp:
            env = {k:v.replace(str(Path(tmp)),str(output/"sensor")) for k,v in environment(Path(tmp)).items()}
        for c in order["calls"]:
            require(len(c["pages"])==3 and all(guard.sha(Path(p["image"]))==p["sha256"] for p in c["pages"]),
                    "Scored source image changed")
        scored_rgb = {h for r in order["requests"] for h in r["rgb_sha256"]}
        require(scored_rgb.isdisjoint(fixture["request"]["rgb_sha256"]), "Warm/study page collision")
        limit = 600 + 150*(len(order["calls"])+1)
        plan = dict(identity, **order, packet="WP-0026", split=split, lease=label, candidate=candidate,
                    output=str(output), warmup=fixture, environment=env, deadline_seconds=limit,
                    sensor_tree=git(repo,"rev-parse","HEAD:docs/research/WP-0024/sensor"),
                    runner_sha256=source["docs/research/WP-0026/worker.py"], gate_sha256=gate_pin)
        plan.update(phase=phase, requests=[fixture["request"],*order["requests"]])
        guard.dump(path,plan)
        digest=guard.sha(path)
        issued.append({"run":name,"plan":str(path),"plan_sha256":digest,"output":str(output),"seconds":limit,
                       "argv":[str(QPY),"-I","-B",str(repo/P/"supervise.py"),str(path),digest]})
    release = {"packet":"WP-0026","name":label,"operator":"eld-rd-reviewer","prepared_utc":guard.utc(),
               "review_worktree_head":candidate,"worktree":str(repo),"gpu_uuid":guard.GPU,"ceiling_mib":12500,
               "free_floor_mib":12000,"source_files":source,"coordination_files":coord,"orders":issued,
               "warm_fixture_sha256":fixture["fixture_sha256"],"loads":len(orders),"excluded_w0":len(orders),
               "scored_calls":sum(len(o["calls"]) for o in orders),"gate_sha256":gate_pin}
    guard.dump(release_path, release)
    print(label, guard.sha(release_path), release["scored_calls"], "scored singleton calls")


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("repo",type=Path)
    p.add_argument("candidate")
    p.add_argument("split")
    p.add_argument("phase")
    p.add_argument("--gate",type=Path)
    p.add_argument("--gate-pin")
    p.add_argument("--prior",type=Path)
    a=p.parse_args()
    bind(a.repo.resolve(),a.candidate,a.split,a.phase,a.gate,a.gate_pin,a.prior)
