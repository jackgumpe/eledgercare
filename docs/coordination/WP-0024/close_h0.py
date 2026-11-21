"""Rebuild the WP-0024 stopping decision from the published H0 archive on CPU."""
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
from struct import pack
import sys
from zipfile import ZipFile


HERE = Path(__file__).resolve().parent
REVIEW = HERE.parents[1] / "reviews/WP-0024"
ARCHIVE_SHA = "37670af4116f543e2d0104b5d3599d88f2e2d06fc092418ee1cf839769430fc6"


def digest(data):
    return sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def token_record(native):
    if (native["expected_pages"], native["num_pages_out"], native["stop_cause"], native["eos_observed"]) != (3, 3, "eos", True):
        raise ValueError("Incomplete singleton output")
    return native["token_ids"] + [native["eos_id"]]


def token_piece(meta, i):
    edges = meta["token_byte_edges"]
    return meta["raw"].encode("utf8")[edges[i]:edges[i + 1]].decode("utf8")


def compare(archive, group):
    left, right = group["left"], group["right"]

    def pair(file):
        return [json.loads(archive.read(f"run/sensor/{tag}/{file}")) for tag in (left, right)]

    a, b = pair("native.json")
    ma, mb = pair("metadata.json")
    ta, tb = token_record(a), token_record(b)
    pages = list(zip(ma["pages"], mb["pages"], strict=True))
    rows = lambda page: [table["rows"] for table in page["tables"]]
    if a["prompt_token_ids"] != b["prompt_token_ids"] or a["terminal_observation"] != b["terminal_observation"]:
        raise ValueError("Prompt or terminal record mismatch")
    changes = [
        {"index_zero_based": i, "stock_id": x, "hooked_id": y,
         "stock_piece": token_piece(ma, i), "hooked_piece": token_piece(mb, i)}
        for i, (x, y) in enumerate(zip(ta, tb, strict=True)) if x != y
    ]
    boxes = []
    for sa, sb in zip(ma["spans"], mb["spans"], strict=True):
        if sa["bbox999"] != sb["bbox999"]:
            boxes.append({"page": sa["page"], "span": sa["index"], "stock_text": sa["text"],
                          "hooked_text": sb["text"], "stock_bbox999": sa["bbox999"], "hooked_bbox999": sb["bbox999"]})
    return {
        "stock": left, "hooked": right, "tokens_before_eos": len(ta) - 1, "eos_id": ta[-1],
        "through_eos_sha256": [digest(pack(f"<{len(ids)}I", *ids)) for ids in (ta, tb)],
        "token_equal": ta == tb, "changed_tokens": changes, "changed_span_boxes": boxes,
        "pages": len(pages), "identical_page_texts": sum(x["text"] == y["text"] for x, y in pages),
        "identical_page_table_grids": sum(rows(x) == rows(y) for x, y in pages),
    }


def reconcile():
    archive_path = REVIEW / "h0-r1.zip"
    inventory = read(REVIEW / "h0-r1-inventory.json")
    independent = read(REVIEW / "h0-r1-independent.json")
    if digest(archive_path.read_bytes()) != ARCHIVE_SHA or inventory["archive_sha256"] != ARCHIVE_SHA:
        raise ValueError("Primary archive identity changed")
    with ZipFile(archive_path) as archive:
        if sorted(archive.namelist()) != sorted(inventory["files"]):
            raise ValueError("Unaccounted primary record")
        for name, item in inventory["files"].items():
            raw = archive.read(name)
            if len(raw) != item["bytes"] or digest(raw) != item["sha256"]:
                raise ValueError(f"Archive member differs: {name}")
        for filename in ("h0-r1-plan.json", "h0-r1-release.json"):
            if archive.read("binding/" + filename) != (HERE / filename).read_bytes():
                raise ValueError("Archived binding differs")
        plan = read(HERE / "h0-r1-plan.json")
        calls = {c["tag"]: c for c in plan["calls"]}
        source_groups = defaultdict(list)
        for call in calls.values():
            source_groups[tuple(p["rgb_sha256"] for p in call["pages"])].append(call["tag"])
        results = []
        for group in plan["check_groups"]:
            a, b = (calls[group[k]] for k in ("left", "right"))
            if a["pages"] != b["pages"] or a["hooked"] or not b["hooked"]:
                raise ValueError("Changed physical comparison")
            result = compare(archive, group)
            result["all_calls_for_same_ordered_rgb"] = source_groups[tuple(p["rgb_sha256"] for p in a["pages"])]
            results.append(result)
        order = json.loads(archive.read("guard/h0-r1-returned.json"))
        board = [json.loads(line) for line in archive.read("guard/h0-r1-device.jsonl").splitlines()]
        if order["exit"] or order["guard"] or json.loads(archive.read("guard/returned.json"))["error"]:
            raise ValueError("GPU job did not return cleanly")
    for result, other in zip(results, independent["comparisons"], strict=True):
        if result["stock"] != other["stock"] or result["through_eos_sha256"] != other["through_eos_sha256"]:
            raise ValueError("Independent token comparison disagrees")
    same = sum(r["token_equal"] for r in results)
    if same == len(results) or independent["gate"] != "FAIL" or same != independent["token_equal_comparisons"]:
        raise ValueError("Failed stopping boundary was not reproduced")
    resources = read(HERE / "resources.json")["sensor_phases"][0]
    if (len(board), max(s["used_mib"] for s in board), order["wall_s"]) != (
            resources["whole_board_samples"], resources["whole_board_peak_sampled_mib"], resources["whole_supervised_s"]):
        raise ValueError("Archived board telemetry differs from the resource summary")
    after = read(HERE / "q0-after.json")
    if after != read(HERE / "q0-before.json") or after != read(REVIEW / "q0-after-independent.json")["after"]:
        raise ValueError("Q0 inventories disagree")
    return {
        "packet": "WP-0024", "disposition": "CLOSED_H0_FAILED", "memory_comparison": "INCONCLUSIVE_UNMEASURED",
        "archive_sha256": ARCHIVE_SHA, "verified_archive_members": len(inventory["files"]),
        "sensor_candidate": plan["candidate"], "native_revision": plan["model_revision"],
        "real_b1_calls": len(calls), "exact_pairs": same, "total_pairs": len(results),
        "page_text_matches": sum(r["identical_page_texts"] for r in results),
        "page_table_grid_matches": sum(r["identical_page_table_grids"] for r in results),
        "page_appearances": sum(r["pages"] for r in results), "comparisons": results,
        "independent_source_witnesses": independent["source_witness_uniques"],
        "independent_hooked_positions": independent["total_hooked_postconsumption_positions"],
        "independent_exact_pools": independent["total_bit_exact_pools"],
        "subsequent_trial_observations": {"C1": None, "probe_fit": None, "blind_C0": None, "heldout_views": None},
    }


if __name__ == "__main__":
    result = reconcile()
    with Path(sys.argv[1]).open("x", encoding="utf8", newline="\n") as output:
        json.dump(result, output, indent=2)
        output.write("\n")
