"""Verify the public H/A commitments and make byte-identical, CPU-only working copies."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
EVAL = "7598bf4155452c4a1294b7421595009d39ea1bc9"
RELEASE = "918701ae318b01395b911b9dbdf597e43908665b"
SCORES = "ce4206f20d63101f6344121eaaeeeb86d2ec85a0"
H_INVENTORY = "bd48af1a7f968b2231fe1d870a22c88f265ae347"
RUNS = {"H": ("h-r1-ab", "04-h-windows", 4), "A": ("a-recovery-ab", "04-a-windows", 60)}
EVIDENCE = "docs/reviews/WP-0015/evidence/"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git_bytes(rev, path):
    return subprocess.check_output(["git", "-C", str(REPO), "show", f"{rev}:{path}"])


def same(left, right, label):
    if left != right:
        raise ValueError(f"Mismatch in {label}")


def save_copy(out, relative, data, verify_only):
    path = out / relative
    if verify_only or path.exists():
        same(path.read_bytes(), data, relative)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as target:
        target.write(data)


def admit_family(name, archive, out, pins, commitments, verify_only):
    run, folder, pages = RUNS[name]
    spec = pins["families"][name]
    same((spec["run"], spec["folder"], spec["family"]), (run, folder, name), name)
    revision = H_INVENTORY if name == "H" else SCORES
    filename = "H-blind-inventory.json" if name == "H" else "A-recovery-blind-inventory.json"
    ref = EVIDENCE + filename
    inventory_data = git_bytes(revision, ref)
    inventory_blob = hashlib.sha1(b"blob " + str(len(inventory_data)).encode() + b"\0" + inventory_data).hexdigest()
    same(inventory_blob, spec["archive_inventory_git_blob"], ref)
    inventory = json.loads(inventory_data)
    selected = [row for row in inventory["runs"] if row["run"] == run]
    same(len(selected), 1, run)
    item = selected[0]
    file_hashes = item["files"]
    records = []

    def archive_file(relative, local, expected, authority):
        data = (archive / relative).read_bytes()
        actual = digest(data)
        if expected is not None:
            same(actual, expected, relative)
        save_copy(out, f"{name}/{local}", data, verify_only)
        records.append(dict(source=relative, copy=f"{name}/{local}", sha256=actual, bytes=len(data), authority=authority))
        return data

    same(commitments["pages"], pages, "committed page count")
    for k in ("source.pdf", "truth.json", "rasters.json"):
        expected = spec["source_commitments_sha256"][k]
        same(expected, commitments["files"][k], k)
        sub = "input" if k == "source.pdf" else "scoring"
        if k == "source.pdf":
            same(expected, inventory["input"][k], "input PDF inventory")
        archive_file(f"{sub}-{name}/{k}", k, expected, f"{EVAL}:commitments.json#{name}")
    input_manifest = "rasters.input.json"
    archive_file(f"input-{name}/{input_manifest}", input_manifest, inventory["input"][input_manifest], inventory_blob)
    plan = archive_file(f"runs/{run}/plan.json", "plan.json", item["plan_sha256"], inventory_blob)
    request = json.loads(plan)["requests"][3]
    same((request["label"], request["mode"], request["warmup"]), (name.lower(), "windows", False), "run request 04")
    names = ["prediction.json", "timing.json"] + [
        f"{kind}-{page:03d}.json" for page in range(1, pages + 1) for kind in ("page", "raw", "window")
    ]
    for k, wanted in spec["relative_files_in_named_run_sha256"].items():
        same(file_hashes[k], wanted, k)
    by_name = {}
    for k in names:
        rel = f"{folder}/{k}"
        data = archive_file(f"runs/{run}/{rel}", f"windows/{k}", file_hashes[rel], inventory_blob)
        by_name[k] = json.loads(data)

    pred = by_name["prediction.json"]
    truth = json.loads((out / name / "truth.json").read_bytes())
    rasters = json.loads((out / name / "rasters.json").read_bytes())
    blind = json.loads((out / name / input_manifest).read_bytes())
    source = spec["source_commitments_sha256"]["source.pdf"]
    same(truth["source_sha256"], source, "truth source")
    same(rasters["pdf_sha256"], source, "raster source")
    same(rasters["truth_sha256"], spec["source_commitments_sha256"]["truth.json"], "raster truth")
    same([p["page"] for p in pred["pages"]], list(range(1, pages + 1)), "predicted page order")
    same(len(blind["pages"]), pages, "input manifest length")
    same(len(rasters["pages"]), pages, "released manifest length")
    for n, (pin, input_pin, page) in enumerate(zip(rasters["pages"], blind["pages"], pred["pages"], strict=True), 1):
        for key in ("page_number", "width_px", "height_px", "rgb_sha256"):
            same(pin[key], input_pin[key], f"{name}/{n}/{key}")
        raw = by_name[f"raw-{n:03d}.json"]
        window = by_name[f"window-{n:03d}.json"]
        same((raw["page"], raw["width"], raw["height"], raw["rgb_sha256"], raw["source_sha256"]),
             (n, pin["width_px"], pin["height_px"], pin["rgb_sha256"], source), f"{name}/{n}/raw")
        same(pin["page_number"], n, "manifest order")
        same((window["first_page"], window["source_sha256"]), (n, source), f"{name}/{n}/window")
        same(page, by_name[f"page-{n:03d}.json"], f"{name}/{n}/durable page")
    historic_name = f"analysis-{name}-stage2/score-{run}-windows.json"
    historic_hash = None
    historic_authority = "Retained score copy. Compare the full scorer result and the independently Git-pinned public counts and lookups."
    if name == "H":
        receipt = json.loads(git_bytes(SCORES, EVIDENCE + "H-scored-receipt.json"))
        historic_hash = receipt["private_evidence_sha256"][historic_name]
        historic_authority = f"{SCORES}:H-scored-receipt.json"
    archive_file(historic_name, "historical-score.json", historic_hash, historic_authority)
    return dict(packet=name, run=run, folder=folder, inventoryGitBlob=inventory_blob,
                namedWindowsFiles=len(names), rgbPageBindings=pages, records=records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true", help="Recheck the original archive against the existing working copies")
    args = parser.parse_args()
    archive, out, receipt = (p.resolve() for p in (args.archive, args.out, args.receipt))
    if archive.is_relative_to(out) or out.is_relative_to(archive) or receipt.is_relative_to(archive):
        parser.error("Working copies and receipt require a separate directory from the archive.")
    kit = "docs/coordination/WP-0018/kit/"
    member_hashes = json.loads(git_bytes(RELEASE, kit + "receipt.json"))["members"]
    pin_data = git_bytes(RELEASE, kit + "archive-pins.json")
    method_data = git_bytes(RELEASE, kit + "constructed-scorer-control.json")
    same(digest(pin_data), member_hashes["archive-pins.json"], "kit archive pins")
    same(digest(method_data), member_hashes["constructed-scorer-control.json"], "kit method control")
    pins = json.loads(pin_data)
    score = git_bytes(EVAL, "docs/evaluation/WP-0015/score.py")
    same(digest(score), pins["scorer_sha256"], "frozen scorer")
    same(json.loads(method_data)["scorer_sha256"], digest(score), "constructed control")
    controls = {"score.py": score, "scored-H-A.json": git_bytes(SCORES, EVIDENCE + "scored-H-A.json"),
                "archive-pins.json": pin_data, "constructed-scorer-control.json": method_data}
    for name, data in controls.items():
        save_copy(out, "control/" + name, data, args.verify_only)
    commitments = json.loads(git_bytes(EVAL, "docs/evaluation/WP-0015/commitments.json"))["packets"]
    report = dict(controlSha256={k: digest(v) for k, v in controls.items()}, families={}, failures={})
    for name in RUNS:
        try:
            report["families"][name] = admit_family(name, archive, out, pins, commitments[name], args.verify_only)
        except (KeyError, OSError, ValueError) as exc:
            report["failures"][name] = str(exc)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(report, indent=2, ensure_ascii=True) + "\n").encode()
    receipt.write_bytes(data)
    print(json.dumps(dict(receiptSha256=digest(data), families=list(report["families"]), failures=report["failures"])))
    return int(bool(report["failures"]))


if __name__ == "__main__":
    raise SystemExit(main())
