"""Observe the model, exact development inputs and the selected board. No GPU API or launch."""
import argparse
import csv
import hashlib
import importlib.metadata
from io import BytesIO, StringIO
import json
from pathlib import Path
import platform
import re
import sys
import time
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (BASE, GPU, HERE, LEASE, MAIN, Q0, ROOT, RUN, SCOPE, SCOPE_HASH, SCRATCH,
                    SOURCE, WARM, check_env, checked, file_sha, freeze, git_identity, json_bytes,
                    keep, require, sha, text_cmd, utc)

PLAN_PATH = "docs/coordination/WP-0026/cal-features-r1-plan.json"
HISTORICAL = ROOT / "docs/reviews/WP-0026/cal-features-primary"
FIXTURE_PIN = "cb058f1931758c516e21e2d791d5b5dffd04646bc773b8e967a11024fdf58cf2"
CEDAR = "33362fbbeb37e805a64acbf3afdc3ec04315a4706820ed634a8fe0fb865ce2d5"

def one_model_file(path, row):
    expected_bytes = row["size"]
    require(path.resolve(strict=True) == path and path.stat().st_size == expected_bytes,
            "Redirected or wrong size: " + str(path))
    git_blob = row["digest_kind"] == "git_blob_sha1"
    git_hash = hashlib.sha1(f"blob {expected_bytes}\0".encode()) if git_blob else None
    digest = hashlib.sha256()
    start = path.stat()
    with path.open("rb") as model_file:
        while block := model_file.read(4 * 1024**2):
            digest.update(block)
            if git_blob:
                git_hash.update(block)
    require(path.stat().st_mtime_ns == start.st_mtime_ns and path.stat().st_size == expected_bytes,
            "Changed while hashing " + str(path))
    observed = git_hash.hexdigest() if git_blob else digest.hexdigest()
    require(observed == row["git_blob_sha1" if git_blob else "sha256"], "Content mismatch " + str(path))
    return dict(name=path.name, bytes=expected_bytes, sha256=digest.hexdigest(),
                upstream_kind=row["digest_kind"], upstream_digest=observed)

def model_identity(plan):
    source = ROOT / "workers/local_ocr/manifests"
    manifest = checked(source / "model-files.json", plan["model_manifest_sha256"])
    lock = checked(source / "dependency-lock.json", plan["environment_lock_sha256"])
    require(manifest["revision"] == plan["model_revision"] and manifest["runtime_object_count"] == 18,
            "Unexpected model inventory")
    groups = {}
    for group, directory, rows in (
            ("model", Q0 / "models" / manifest["model_dir_basename"], manifest["files"]),
            ("notice", Q0 / "notices" / manifest["notice_dir_basename"], manifest["notices"])):
        entries = {p.name for p in directory.iterdir()}
        names = {item["path"] for item in rows}
        require(entries - {".cache"} == names and len(rows) == len(names), "Unexpected " + group + " contents")
        groups[group] = [one_model_file(directory / row["path"], row) for row in rows]
    model_files = {r["name"]: r for r in groups["model"]}
    require(model_files["modeling_unlimitedocr.py"]["sha256"] == plan["module_sha256"]
            and model_files["tokenizer.json"]["sha256"] == plan["tokenizer_sha256"], "Code/tokenizer changed")
    require(sum(x["bytes"] for x in groups["model"]) == manifest["total_bytes"], "Model bytes")
    exe = Path(sys.executable)
    require(file_sha(exe) == plan["executable_sha256"] and platform.python_version() == lock["platform"]["python"],
            "Unexpected interpreter bytes/version")
    norm = lambda k: re.sub("[-_.]+", "-", k.lower())
    installed = {norm(d.metadata["Name"]): d.version for d in importlib.metadata.distributions()}
    versions = {norm(d["name"]): d["version"] for d in lock["distributions"]}
    require(all(installed.get(k) == v for k, v in versions.items()), "Pinned distribution version mismatch")
    require(set(installed) - set(versions) <= set(lock["allowed_unlocked_tooling"]), "Unexpected distribution")
    return dict(revision=manifest["revision"], model_manifest_sha256=plan["model_manifest_sha256"],
                dependency_lock_sha256=plan["environment_lock_sha256"], model_bytes=manifest["total_bytes"],
                weight_bytes=manifest["weight_bytes"], interpreter=str(exe), python=platform.python_version(),
                executable_sha256=plan["executable_sha256"], installed_versions=installed, **groups)

def board_observation():
    binding = checked(ROOT / "docs/reviews/WP-0024/admission-watch-binding.json",
                      "ad311561b81f7d3f86938861726385fa5f7ddd0ffff826d6a205552697b7ab6d")
    argv = ["nvidia-smi", "--id=" + GPU]
    line = text_cmd(argv + ["--query-gpu=uuid,name,driver_version,memory.total,memory.used,memory.free",
                            "--format=csv,noheader,nounits"])
    uuid, board, driver, total, used, free = next(csv.reader([line], skipinitialspace=True))
    raw = text_cmd(argv + ["--query-compute-apps=pid,process_name", "--format=csv,noheader,nounits"])
    clients = []
    for entry in csv.reader(StringIO(raw), skipinitialspace=True):
        require(len(entry) == 2 and entry[0].isdigit(), "Unparseable NVIDIA process entry")
        clients.append(dict(pid=int(entry[0]), image=Path(entry[1]).name))
    require(uuid == binding["gpu"] == GPU, "Wrong GPU")
    unrecognized = [c for c in clients if c["image"].lower() not in binding["observed_desktop_images"]]
    models = text_cmd(["ollama", "ps"]).splitlines()
    require(models and models[0].startswith("NAME"), "Uninterpretable resident-model observation")
    return dict(utc=utc(), gpu_uuid=uuid, board=board, driver=driver, total_mib=int(total), used_mib=int(used),
                free_mib=int(free), clients=clients, unrecognized_gpu_clients=unrecognized,
                resident_ollama_rows=len(models)-1, free_floor_available=int(free)>=12000,
                expected_clients_only=not unrecognized and len(models)==1,
                scope="Read-only observation outside lock. Guard separately adjudicates admission under lock.")

def image_identity(path, rgb, png):
    from PIL import Image
    raw = path.read_bytes()
    require(sha(raw) == png, "PNG bytes changed")
    with Image.open(BytesIO(raw)) as im:
        require(im.mode == "RGB" and im.size == (2550,3300) and sha(im.tobytes()) == rgb, "RGB changed")
    return dict(png_sha256=png, rgb_sha256=rgb, bytes=len(raw))

def fixture_and_archive(scope, plan):
    release = scope["proposed_future_acquisition"]
    fixture = checked(SOURCE / "manifest.json", FIXTURE_PIN)
    warm = checked(WARM / "receipt.json", release["warmup_fixture_sha256"])
    require(file_sha(WARM / warm["pdf"]["path"]) == warm["pdf"]["sha256"], "Warmup PDF changed")
    warm_rasters = [image_identity(WARM/p["image"],p["rgb_sha256"],p["sha256"]) for p in warm["pages"]]
    pages, pdfs, logical = {}, [], {}
    for pair in fixture["pairs"]:
        for member in pair["members"]:
            path = ROOT / member["source_pdf"]
            require(file_sha(path) == member["source_pdf_sha256"], "Changed source PDF")
            pdfs.append(dict(binder=member["binder"], horizon=pair["horizon"], owner=member["owner"],
                             path=member["source_pdf"], sha256=member["source_pdf_sha256"]))
            for window in member["windows"]:
                ordered = []
                for page in window["pages"]:
                    png, rgb = page["sha256"], page["rgb_sha256"]
                    if png not in pages:
                        pages[png] = image_identity(ROOT/page["image"],rgb,png)
                    require(pages[png]["rgb_sha256"] == rgb, "Duplicate PNG changed identity")
                    ordered.append(rgb)
                key = sha(json_bytes(ordered))
                require(key == window["rgb_key"], "Window order")
                logical[pair["horizon"],member["owner"],window["window"]] = key
    missing, = scope["missing"]
    ordered = [p["rgb_sha256"] for p in missing["ordered_pages"]]
    require(sha(json_bytes(ordered)) == CEDAR and not set(ordered) & {p["rgb_sha256"] for p in warm_rasters},
            "Cedar/W0 identity or disjointness")
    inv_rel = (HISTORICAL/"inventory.json").relative_to(ROOT).as_posix()
    inv = checked(ROOT/inv_rel,scope["input_identities"][inv_rel]["sha256"])
    archive = HISTORICAL / "primary-001.zip"
    zip_pin = scope["input_identities"][archive.relative_to(ROOT).as_posix()]["sha256"]
    require(zip_pin == inv["parts"][archive.name]["sha256"] == file_sha(archive), "Historical ZIP changed")
    groups, covered = [], []
    with ZipFile(archive) as z:
        for item in [*scope["cached"], missing]:
            triples = item["ordered_pages"]
            key = sha(json_bytes([p["rgb_sha256"] for p in triples]))
            require(all(pages[p["png_sha256"]]["rgb_sha256"] == p["rgb_sha256"] for p in triples), "Scope raster")
            for usage in item["uses"]:
                slot = usage["horizon"], usage["owner"], usage["window"]
                require(slot not in covered and logical[slot] == key, "Logical route disagrees")
                covered.append(slot)
            if item is missing:
                continue
            tag = item["tag"]
            prefix = f"runs/cal-features-r1/sensor/{tag}/"
            receipt_bytes = z.read(prefix + "receipt.json")
            receipt = json.loads(receipt_bytes)
            require(sha(receipt_bytes)==inv["members"][prefix+"receipt.json"]["sha256"], "Archive receipt")
            require(receipt["tag"] == tag and receipt["verified"] and receipt["mode"] == "H" and
                    [(p["sha256"],p["rgb_sha256"]) for p in receipt["pages"]] ==
                    [(p["png_sha256"],p["rgb_sha256"]) for p in triples], "Archived source order")
            for file, digest in receipt["artifacts"].items():
                require(sha(z.read(prefix+file)) == digest == inv["members"][prefix+file]["sha256"], file)
            for f, key_name in (("metadata.json","metadata_sha256"),("through-eos.u32le","through_eos_sha256"),
                                ("pooled.f32","pooled_sha256")):
                require(receipt["artifacts"][f] == item[key_name], "Archive disagrees with acquisition proposal")
            groups.append(dict(tag=tag,rgb_key=key,uses=item["uses"],receipt_sha256=sha(receipt_bytes),
                               artifacts=receipt["artifacts"]))
        historical_warm = json.loads(z.read("runs/cal-features-r1/sensor/warmup.json"))
    require(len(pages)==31 and len(pdfs)==4 and len(groups)==10 and set(covered)==set(logical)
            and len(covered)==28, "Wrong fixture counts")
    worker = release["pinned_worker_revision"]
    sensor = release["capture_revision"]
    worker_file = "docs/research/WP-0026/worker.py"
    require(file_sha(ROOT/worker_file) == plan["runner_sha256"] and git_identity(worker_file,worker) ==
            git_identity(worker_file,BASE), "Historical worker")
    sensor_tree = git_identity("docs/research/WP-0024/sensor",sensor)
    require(sensor_tree == plan["sensor_tree"] == git_identity("docs/research/WP-0024/sensor",BASE),
            "Historical sensor tree")
    return dict(scope_sha256=SCOPE_HASH, fixture_manifest_sha256=FIXTURE_PIN, warmup_fixture_sha256=
                release["warmup_fixture_sha256"], warmup_pdf=warm["pdf"], warmup_rasters=warm_rasters,
                historical_w0_through_eos=historical_warm["through_eos_sha256"], all_fixture_pdfs=pdfs,
                all_fixture_rasters=pages, missing_key=CEDAR, missing=missing, development_zip=zip_pin,
                ten_archived_groups=groups, logical_windows=len(covered), worker_revision=worker,
                worker_sha256=plan["runner_sha256"],sensor_revision=sensor,sensor_tree=sensor_tree,
                historical_comparator=scope["historical_timing_comparator"])

def previous_attempts():
    # These are the paths in this packet's reservation and handoff. A shared lock file's
    # existence or age cannot establish whether one holds the board.
    paths = [RUN, LEASE, HERE/"native-return.zip", HERE/"evidence/return.json", SCRATCH/"issuance.json"]
    return dict(utc=utc(), checked_paths={str(p):p.exists() for p in paths},
                local_history=text_cmd(["git","log","--all","--format=%H %s","--","docs/coordination/WP-0029",
                                        "docs/research/WP-0029/acquisition","docs/agent-reports/eld-cedar-operator/WP-0029"]).splitlines(),
                remote_owned_heads=text_cmd(["git","ls-remote","--heads","origin","*wp-0029*"]).splitlines(),
                historical_wp0028_native_calls=0, method="Repository history and packet-specific on-disk evidence.")

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("phase",choices=["prepare","return"])
    args=p.parse_args()
    check_env()
    begin=time.monotonic()
    scope=checked(SCOPE,SCOPE_HASH)
    plan=checked(ROOT/PLAN_PATH,scope["input_identities"][PLAN_PATH]["sha256"])
    row=dict(phase=args.phase, started=utc(), operator_source=freeze(), assignment_base=BASE,
             command=[sys.executable,*sys.orig_argv[1:]], board=board_observation())
    if args.phase=="prepare":
        row["reconciliation"]=previous_attempts()
        require(not any(row["reconciliation"]["checked_paths"].values()), "Possible earlier issuance")
        row["inputs"]=fixture_and_archive(scope,plan)
    row["q0"]=model_identity(plan)
    if args.phase=="return":
        before=json.loads((SCRATCH/"prepare.json").read_bytes())
        row["q0_matches_before"] = before["q0"] == row["q0"]
        require(row["q0_matches_before"], "Pre/post Q0 changed")
    row.update(completed=utc(), wall_seconds=time.monotonic()-begin)
    keep(SCRATCH/(args.phase+".json"),row)
    print(args.phase, row["q0"]["model_bytes"], row["board"]["free_mib"], row["wall_seconds"])

if __name__ == "__main__":
    main()
