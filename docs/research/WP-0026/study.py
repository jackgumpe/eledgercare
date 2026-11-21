"""Prepare hash-checked conditioned feature routes, then invoke the frozen CPU probe."""
from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
AUTHOR = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0026/author")
RUNS = AUTHOR.parent / "review/runs"
PROBE_REVISION = "7db67283a4ffd3e7a20bb8d80499572cc7118c71"
PROBE = ROOT / "docs/research/WP-0024/probe"
sys.path.insert(0, str(ROOT / "docs/coordination/WP-0025"))
from supervise import environment
sys.path.insert(0, str(ROOT / "docs/coordination/WP-0024"))
from corpus_plan import transport

ARMS = ("M0", "M1", "M2", "M3-Zero", "M3", "M3-Swap")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def checked(ref):
    path = Path(ref[0]).resolve(strict=True)
    require(digest(path) == ref[1], "Input hash changed: " + str(path))
    return path


def read(path):
    return json.loads(path.read_bytes())


def write(path, obj):
    with path.open("x", encoding="utf8", newline="\n") as stream:
        json.dump(obj, stream, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        stream.write("\n")
    return digest(path)


def source_revision():
    git = "C:/Program Files/Git/cmd/git.exe"
    def command(*args):
        return subprocess.check_output([git, "-C", str(ROOT), *args], text=True).strip()
    require(not command("status", "--porcelain", "--untracked-files=all"), "Clean author checkout required")
    command("diff", "--exit-code", PROBE_REVISION, "HEAD", "--", "docs/research/WP-0024/probe")
    return command("rev-parse", "HEAD")


def prepare_split(split, ref, output):
    plan_path = checked(ref)
    plan = read(plan_path)
    direct = RUNS / f"{split}-features-r1" / "sensor"
    require(plan["packet"] == "WP-0026" and plan["phase"] == "features" and plan["split"] == split
            and Path(plan["output"]).resolve() == direct.parent, "Wrong feature phase")
    binding = read(direct / "binding.json")
    require(binding["plan_sha256"] == ref[1] and binding["candidate"] == plan["candidate"]
            and read(direct.parent / "process.json")["all_segments_completed"], "Feature phase did not return")
    manifest = transport(plan)
    paths = {Path(w).resolve(strict=True) for pair in manifest["pairs"] for twin in pair["twins"] for w in twin["windows"]}
    expected_pairs = 32 if split == "blind" else 10
    require(len(manifest["pairs"]) == expected_pairs, "Wrong split size")
    phases = {}
    for path in sorted(paths):
        folder = path.parent
        require(folder == direct or (split != "cal" and folder == RUNS / f"{split}-c1-r1" / "sensor"),
                "Route crosses acquisition split or phase")
        if folder not in phases:
            cold = read(folder / "binding.json")
            warm = read(folder / "warmup.json")
            require(cold["packet"] == warm["packet"] == "WP-0026" and cold["split"] == warm["split"] == split
                    and cold["model_revision"] == binding["model_revision"] and cold["sensor_candidate"] == binding["sensor_candidate"]
                    and warm["fixture_sha256"] == plan["warmup"]["fixture_sha256"] and warm["success"]
                    and warm["eos_observed"] and warm["ordinal"] == 1 and warm["model_load_id"] == cold["model_load_id"]
                    and cold["candidate"] == warm["candidate"] and read(folder.parent / "process.json")["all_segments_completed"],
                    "Unconditioned feature source")
            phases[folder] = (digest(folder / "warmup.json"), cold)
        warm_sha, cold = phases[folder]
        row = read(path / "receipt.json")
        require(row["tag"] == path.name and row["verified"] and row["warmup_sha256"] == warm_sha
                and row["model_load_id"] == cold["model_load_id"] and row["sensor_candidate"] == binding["sensor_candidate"]
                and row["warmup_fixture_sha256"] == plan["warmup"]["fixture_sha256"] and row["ordinal"] >= 2
                and row["plan_sha256"] == cold["plan_sha256"] and row["candidate"] == cold["candidate"], "Invalid scored provenance")
        require(all(row["artifacts"][k] == digest(path / k) for k in ("metadata.json", "pooled.f32")), "Changed feature bytes")
    path = output / (split + "-transport.json")
    pin = write(path, manifest)
    return path, dict(plan=str(plan_path), plan_sha256=ref[1], transport_sha256=pin, windows=len(paths),
                      logical_windows=sum(len(t["windows"]) for p in manifest["pairs"] for t in p["twins"]),
                      warmup_fixture_sha256=plan["warmup"]["fixture_sha256"], sensor_candidate=binding["sensor_candidate"],
                      model_revision=binding["model_revision"])


def labels(ref, split):
    path = Path(ref[0]).resolve(strict=True)
    allowed = [AUTHOR.parent / "custody", AUTHOR.parents[1] / "WP-0024/custody"]
    require(any(path.is_relative_to(root) for root in allowed)
            and path.name == "truth.json" and path.parent.name == split and split in ("train", "cal"),
            "Only development truth permitted")
    return checked(ref)


def freeze_views(output):
    joint_path = output / "predictions.json"
    freeze = read(output / "freeze.json")
    require(digest(joint_path) == freeze["predictions_sha256"], "Joint prediction freeze changed")
    rows = read(joint_path)["predictions"]
    require(len(rows) == 384 and {r["arm"] for r in rows} == set(ARMS), "Expected six views of 64 binders")
    views, recipients = {}, None
    for arm in ARMS:
        selected = [r for r in rows if r["arm"] == arm]
        ids = {(r["binder"], r["target"]) for r in selected}
        require(len(selected) == len(ids) == 64 and all(r["type"] in ("Posting", "ABSTAIN") for r in selected),
                "Missing, duplicate or invalid prediction")
        require(recipients is None or ids == recipients, "Arms address different binders or targets")
        recipients = ids
        path = output / (arm + "-predictions.json")
        views[arm] = dict(file=path.name, predictions=64, sha256=write(path, {"predictions": selected}))
    return dict(joint_sha256=freeze["predictions_sha256"], views=views, freeze_sha256=digest(output / "freeze.json"))


def main():
    parser = ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    fit = sub.add_parser("fit")
    infer = sub.add_parser("infer")
    for arg in ("train-plan", "cal-plan", "train-truth", "cal-truth"):
        fit.add_argument("--" + arg, nargs=2, metavar=("PATH","SHA256"), required=True)
    for arg in ("blind-plan", "fit"):
        infer.add_argument("--" + arg, nargs=2, metavar=("PATH","SHA256"), required=True)
    for cmd in (fit, infer):
        cmd.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    qpy = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe").resolve()
    require(sys.flags.isolated and sys.dont_write_bytecode and not sys.flags.optimize
            and Path(sys.executable).resolve() == qpy, "Use pinned Q0 Python -I -B")
    candidate = source_revision()
    output = args.output.resolve()
    require(output.parent == AUTHOR and output.name not in ("cache", "private"), "Use a new direct author directory")
    output.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter_ns()
    env = environment(output)
    env.update(CUDA_VISIBLE_DEVICES="-1", CUDA_CACHE_DISABLE="1")
    pins = {}
    command = [str(qpy), "-I", "-B", str(PROBE / "run.py"), args.mode]
    result = output / "result"
    if args.mode == "fit":
        for split in ("train", "cal"):
            route, pins[split] = prepare_split(split, getattr(args, split + "_plan"), output)
            ref = getattr(args, split + "_truth")
            truth = labels(ref, split)
            pins[split]["truth_sha256"] = ref[1]
            command.extend(["--" + split, str(route), "--" + split + "-truth", str(truth)])
        for key in ("warmup_fixture_sha256", "sensor_candidate", "model_revision"):
            require(pins["train"][key] == pins["cal"][key], "Development source mismatch: " + key)
    else:
        route, pins["blind"] = prepare_split("blind", args.blind_plan, output)
        path = checked(args.fit)
        require(path.name == "fit.json" and path.is_relative_to(AUTHOR), "Use frozen author fit")
        command.extend(["--manifest", str(route), "--weights", str(path.parent), "--fit-sha256", args.fit[1]])
        pins["fit_sha256"] = args.fit[1]
    command.extend(["--output", str(result)])
    write(output / "bound.json", dict(pins=pins, command=command, candidate=candidate, probe_revision=PROBE_REVISION))
    with (output/"stdout.txt").open("xb") as so, (output/"stderr.txt").open("xb") as se:
        cpu_start = time.perf_counter_ns()
        code = subprocess.run(command, cwd=output, env=env, stdin=subprocess.DEVNULL, stdout=so, stderr=se).returncode
    receipt = dict(returncode=code, elapsed_child_ns=time.perf_counter_ns()-cpu_start, elapsed_phase_ns=time.perf_counter_ns()-start)
    write(output / "process.json", receipt)
    require(code == 0, "Probe failed; see process, stderr and result/failure records")
    if args.mode == "fit":
        fit_receipt = read(result / "fit.json")
        require(all(fit_receipt["weights"][arm] == digest(result / (arm+".pt")) for arm in ("M1","M3")), "Weights changed")
        print(json.dumps(dict(fit_sha256=digest(result / "fit.json"), weights=fit_receipt["weights"],
                              thresholds=fit_receipt["thresholds"], **receipt), indent=2))
    else:
        views = freeze_views(result)
        print(json.dumps(dict(views_sha256=write(result / "six-freeze.json", views), **views, **receipt), indent=2))


if __name__ == "__main__":
    main()
