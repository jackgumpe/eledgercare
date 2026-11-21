"""Rebuild both model inputs from sealed-run sensor archives, without access to live OCR or the detector."""
from argparse import ArgumentParser
from collections import Counter
from datetime import datetime
from hashlib import sha256
from pathlib import Path
import json
import math
import subprocess

from PIL import Image


def read(path):
    return json.loads(path.read_bytes())


def digest(data):
    return sha256(data).hexdigest()


def instant(value):
    return datetime.fromisoformat(value)


def stage(record):
    wall, cpu = record["wall_ms"], record["process_cpu_ms"]
    assert wall >= 0 and cpu >= 0
    assert instant(record["finished_utc"]) >= instant(record["started_utc"])
    return wall, cpu


def validate_source_stamps(plan):
    for entry in plan["sources"]:
        code = subprocess.check_output(["git", "show", entry["commit"] + ":" + entry["path"]])
        assert digest(code) == entry["sha256"], entry
    assert plan["sources"][0]["commit"] == "613a5ff92e9dd6783b8950529fbda76f6c21e9d3"
    assert {p["commit"] for p in plan["sources"] if p["path"].endswith(("visual.py","formats.py"))} == {
        "a0e738bc03e515999659dda09c5ee76d08fb37df"}


def windows_page(raw, number):
    result = []
    for line_idx, line in enumerate(raw["lines"], 1):
        words = []
        for word_idx, word in enumerate(line["words"], 1):
            x, y, width, height = word["rect_px"]
            assert width > 0 and height > 0
            box = [float(value) * page_size / pixel_size for value, page_size, pixel_size in
                   zip([x,y,x + width,y + height],[612,792,612,792],[2550,3300,2550,3300])]
            words.append(dict(text=word["text"], bbox=box, ref=f"p{number}:L{line_idx}:W{word_idx}"))
        result.append(dict(text=line["text"], words=words))
    return result


def audit(public, evidence):
    manifest_path = public / "manifest.json"
    docs = read(manifest_path)["documents"]
    plan = read(evidence / "plan.json")
    assert digest(manifest_path.read_bytes()) == plan["manifest_sha256"]
    validate_source_stamps(plan)
    inventory = read(evidence / "blind-hashes.json")
    files = [p for p in evidence.rglob("*.json") if p.name != "blind-hashes.json"]
    assert set(inventory) == {p.relative_to(evidence).as_posix() for p in files}
    for f in files:
        assert digest(f.read_bytes()) == inventory[f.relative_to(evidence).as_posix()], f
    pages, native_env, windows = [], set(), {}
    known_rasters, pids = set(), set()
    obs_count = Counter()
    for record in docs:
        doc = record["id"]
        renderer = read(public / "rendered" / (doc + ".json"))["pages"]
        builds = {a:read(evidence / "observations" / a / (doc + ".json"))["pages"] for a in ["R","W"]}
        costs = {a:read(evidence / "timing" / a / (doc + ".json")) for a in ["R","W"]}
        for idx, entry in enumerate(record["pages"]):
            number = idx + 1
            png = entry["sha256"]
            known_rasters.add(png)
            folder = evidence / "captures" / png
            input_meta, grid, before, raw, after, child, gridstart = [read(folder / (name + ".json")) for name in
                ("input","grid","ocr-started","raw","ocr-finished","child-lifetime","grid-started")]
            assert raw["png_sha256"] == after["png_sha256"] == grid["png_sha256"] == gridstart["sha256"] == input_meta["sha256"] == png
            assert digest((folder / "raw.json").read_bytes()) == after["raw_sha256"]
            png_path = public / entry["raster"]
            assert digest(png_path.read_bytes()) == png
            with Image.open(png_path) as im:
                assert im.mode == "RGB" and im.size == (2550,3300)
                assert all(abs(res - 300) < .1 for res in im.info["dpi"])
                rgba = im.convert("RGBA")
                assert digest(im.tobytes()) == plan["inputs"][png]["rgb_sha256"] == input_meta["rgb_sha256"]
                assert digest(rgba.tobytes("raw","BGRA")) == raw["image"]["canonical_bgra_sha256"] == input_meta["canonical_bgra_sha256"]
            assert raw["image"] == before["image"] and raw["image"]["png_sha256"] == png
            assert (raw["image"]["width"],raw["image"]["height"]) == (2550,3300)
            assert raw["image"]["bitmap_format"] == "Bgra8"
            assert raw["image"]["plane"]["stride_bytes"] >= 2550 * 4 and raw["image"]["plane"]["height"] == 3300
            assert raw["language"] == before["environment"]["language"] == "en-US"
            env = before["environment"]
            for asset in env["resources"]:
                asset_path = Path(asset["path"])
                assert asset_path.stat().st_size == asset["bytes"]
                assert digest(asset_path.read_bytes()) == asset["sha256"]
            assert env["loaded_ocr_dll"].lower() == env["resources"][0]["path"].lower()
            native_env.add((env["os_build"],env["ubr"],env["display_version"],env["powershell"],
                            *(asset["sha256"] for asset in env["resources"])))
            pids.add((env["pid"],env["process_created_utc"]))
            assert instant(gridstart["utc"]) <= instant(grid["detect"]["started_utc"]) <= instant(grid["detect"]["finished_utc"])
            times = [before["initialization_started_utc"], before["utc"], raw["recognize_started_utc"],
                     raw["recognize_finished_utc"], after["utc"]]
            assert sorted(instant(t) for t in times) == [instant(t) for t in times]
            assert instant(child["started_utc"]) <= instant(times[0])
            assert instant(child["finished_utc"]) >= instant(times[-1])
            assert after["worker_wall_ms"] >= raw["recognize_wall_ms"] >= 0
            assert after["worker_cpu_ms"] >= raw["recognize_cpu_ms"] >= 0
            assert after["worker_cpu_ms"] >= before["initialization_cpu_ms"] >= 0
            native_ms = 1000 * (instant(times[3]) - instant(times[2])).total_seconds()
            assert math.isclose(native_ms, raw["recognize_wall_ms"], abs_tol=8), (native_ms,raw["recognize_wall_ms"])
            windows[png] = (instant(child["started_utc"]), instant(child["finished_utc"]))
            gridcost, parentwait = stage(grid["detect"]), stage(child)
            preparation = stage(input_meta["prepare"])
            pages.append({"doc":doc,"page":number,"png":png, "grid":gridcost, "preparation":preparation,
                          "recognition":[raw["recognize_wall_ms"],raw["recognize_cpu_ms"]],
                          "in_script_worker":[after["worker_wall_ms"],after["worker_cpu_ms"]],
                          "cold_child_wait":parentwait,"arms":{}})
            for arm in ("R","W"):
                page = builds[arm][idx]
                assert page["grids"] == grid["grids"]
                assert (page["width_pt"],page["height_pt"],page["page"]) == (612,792,number)
                if arm == "W":
                    expected = windows_page(raw,number)
                else:
                    expected = renderer[idx]["lines"]
                assert expected == page["lines"], (arm,doc,number)
                obs_count[arm+"_lines"] += len(expected)
                obs_count[arm+"_words"] += sum(len(l["words"]) for l in expected)
                receipt = costs[arm][idx]
                assert receipt["page"] == number and receipt["sha256"] == png
                building, reading = stage(receipt["observation"]), stage(receipt["reader"])
                wall = gridcost[0] + building[0] + reading[0]
                cpu = gridcost[1] + building[1] + reading[1]
                if arm == "W":
                    wall += parentwait[0]
                    cpu += after["worker_cpu_ms"] + parentwait[1]
                pages[-1]["arms"][arm] = {"assembly":building,"reader":reading,
                                         "standalone_wall_ms":wall,"known_process_cpu_ms":cpu}
    assert len(known_rasters) == len(plan["inputs"]) == plan["rasters"] == len(pids)
    assert len(native_env) == 1
    chronological = sorted(windows.values())
    assert all(a[1] <= b[0] for a,b in zip(chronological, chronological[1:]))
    unique = {p["png"]:p for p in pages}.values()
    physical = {
        "unique_rasters":len(known_rasters), "page_appearances":len(pages),
        "wall_grid_total_ms":sum(p["grid"][0] for p in unique),
        "cpu_grid_total_ms":sum(p["grid"][1] for p in unique),
        "wall_ocr_cold_child_wait_total_ms":sum(p["cold_child_wait"][0] for p in unique),
        "cpu_worker_plus_waiting_parent_total_ms":sum(p["in_script_worker"][1] + p["cold_child_wait"][1] for p in unique),
        "wall_recognition_only_ms_per_unique":sum(p["recognition"][0] for p in unique)/len(known_rasters),
        "cpu_recognition_only_ms_per_unique":sum(p["recognition"][1] for p in unique)/len(known_rasters)}
    for arm in ["R","W"]:
        physical[arm + "_reader_and_assembly_wall_total_ms"] = sum(p["arms"][arm]["assembly"][0]+p["arms"][arm]["reader"][0] for p in pages)
        physical[arm + "_reader_and_assembly_cpu_total_ms"] = sum(p["arms"][arm]["assembly"][1]+p["arms"][arm]["reader"][1] for p in pages)
    totals = {arm: {key: sum(p["arms"][arm][key] for p in pages) / len(pages)
                    for key in ("standalone_wall_ms","known_process_cpu_ms")} for arm in ("R","W")}
    return {"verified_blind_files":len(inventory),"page_count":len(pages),"documents":len(docs),
            "native_captures":len(pids),"word_and_line_counts":dict(obs_count),"environment":list(native_env)[0],
            "per_page_mean":totals, "actual_execution":physical, "pages":pages}


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    for name in ("public","evidence","out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    receipt = audit(args.public,args.evidence)
    args.out.write_bytes((json.dumps(receipt,indent=2) + "\n").encode())
    print(json.dumps({k:v for k,v in receipt.items() if k != "pages"},indent=2))

