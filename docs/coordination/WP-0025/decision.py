"""Summarize the observed repeatability gate directly from the sealed primary evidence on CPU."""
from collections import Counter
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import struct
import sys
from zipfile import ZipFile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REVIEW = ROOT / "docs/reviews/WP-0025"
HIST = ROOT / "docs/reviews/WP-0024/h0-r1.zip"
HIST_SHA = "37670af4116f543e2d0104b5d3599d88f2e2d06fc092418ee1cf839769430fc6"
RELEASE = "window-repeat-r1-release.json"


def digest(raw):
    return sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def get(archive, name):
    return json.loads(archive.read(name))


def through(native):
    ids = native["token_ids"]
    eos = native["eos_id"]
    stop = native["terminal_observation"]
    if not (native["eos_observed"] and native["stop_cause"] == "eos" and native["finish_reason"] == "stop" and
            stop["step"] == len(ids) and stop["nxt"] == eos == 1 and eos not in ids and
            native["expected_pages"] == native["num_pages_out"] == 3):
        raise ValueError("Unverified EOS or page count")
    return struct.pack(f"<{len(ids) + 1}I", *ids, eos)


def slot(archive, tag, root, plan, candidate):
    path = root + "/sensor/" + tag + "/"
    receipt = get(archive, path + "receipt.json")
    if (not receipt["verified"] or receipt["tag"] != tag or receipt["plan_sha256"] != plan or
            receipt["candidate"] != candidate or receipt["mode"] != tag[-1]):
        raise ValueError("Slot receipt does not match the released order")
    for name, pin in receipt["artifacts"].items():
        if digest(archive.read(path + name)) != pin:
            raise ValueError("Changed sealed slot artifact: " + name)
    native = get(archive, path + "native.json")
    raw = through(native)
    if raw != archive.read(path + "through-eos.u32le") or digest(raw) != receipt["through_eos_sha256"]:
        raise ValueError("Little-endian through-EOS receipt disagrees")
    duration = get(archive, path + "duration.json")
    return {"stream": digest(raw), "pre_eos_ids": len(native["token_ids"]),
            "inference_s": duration["wall_inference_ns"] / 1e9,
            "complete_window_s": duration["complete_window_wall_ns"] / 1e9, "pid": receipt["pid"],
            "hidden_bf16_sha256": receipt["artifacts"].get("token_hidden.bf16"),
            "pooled_fp32_sha256": receipt["artifacts"].get("pooled.f32")}


def summarize():
    plan = read(HERE / RELEASE)
    inv = read(REVIEW / "window-repeat-r1-inventory.json")
    archive_path = REVIEW / "window-repeat-r1.zip"
    if digest(archive_path.read_bytes()) != inv["archive"]["sha256"] or digest(HIST.read_bytes()) != HIST_SHA:
        raise ValueError("Primary archive identity changed")
    with ZipFile(HIST) as old:
        old_hashes = {mode: digest(through(get(old, f"run/sensor/b01w01{mode}/native.json"))) for mode in "SH"}
    if len(set(old_hashes.values())) != 2:
        raise ValueError("Historical controls do not differ")
    issues, runs, orders, tags = [], {}, {}, []
    with ZipFile(archive_path) as data:
        names = data.namelist()
        if sorted(names) != sorted(inv["files"]):
            raise ValueError("Incomplete inventory")
        for name, metadata in inv["files"].items():
            raw = data.read(name)
            if len(raw) != metadata["size"] or digest(raw) != metadata["sha256"]:
                raise ValueError("Changed archive member: " + name)
        if data.read("binding/" + RELEASE) != (HERE / RELEASE).read_bytes():
            raise ValueError("Archive release disagrees with the ledger")
        guard_return = get(data, "guard/returned.json")
        if guard_return["error"] is not None:
            issues.append({"lease_error": guard_return["error"]})
        for order in plan["orders"]:
            label = order["run"]
            folder = "runs/" + label
            filename = label + "-plan.json"
            raw = data.read("binding/" + filename)
            if digest(raw) != order["plan_sha256"] or raw != (HERE / filename).read_bytes():
                raise ValueError("Changed process plan")
            process_plan = json.loads(raw)
            ordered = [c["tag"] for c in process_plan["calls"]]
            tags.extend(ordered)
            for tag in ordered:
                try:
                    result = slot(data, tag, folder, order["plan_sha256"], plan["review_worktree_head"])
                    result["historical_match"] = next((m for m, value in old_hashes.items()
                                                      if result["stream"] == value), "neither")
                    runs[tag] = result
                except (KeyError, ValueError, TypeError) as exc:
                    issues.append({"slot": tag, "missing_or_invalid": str(exc)})
            try:
                receipt = get(data, "guard/" + label + "-returned.json")
                issued = get(data, "guard/" + label + "-issued.json")
                process = get(data, folder + "/process.json")
                final = get(data, folder + "/sensor/outcome.json")
                cold = get(data, folder + "/sensor/cold.json")
                samples = [json.loads(line) for line in data.read("guard/" + label + "-device.jsonl").splitlines()]
                if (not samples or receipt["exit"] or receipt["guard"] or not process["all_segments_completed"] or
                        final["verified_tags"] != ordered or final["started_tags"] != ordered or cold["loads"] != 1):
                    raise ValueError("Incomplete supervisor, call or guard receipt")
                orders[label] = {"issued_utc": issued["issued"], "returned_utc": receipt["utc"],
                                 "sampled_peak_board_mib": max(s["used_mib"] for s in samples),
                                 "board_samples": len(samples), "supervised_s": receipt["wall_s"],
                                 "native_load_s": cold["model"]["load_ms"] / 1000,
                                 "worker_pid": cold["pid"], "worker_create_filetime": cold["process_create_filetime"]}
            except (KeyError, ValueError, TypeError) as exc:
                issues.append({"order": label, "missing_or_invalid": str(exc)})
    if len(orders) == 2 and len({(s["worker_pid"], s["worker_create_filetime"]) for s in orders.values()}) != 2:
        issues.append({"process_identity": "Expected two independent cold workers"})
    matrix = [[runs[a]["stream"] == runs[b]["stream"] if a in runs and b in runs else None for b in tags] for a in tags]
    counts = {k: Counter() for k in ("SS", "HH", "SH")}
    for a, b in combinations(tags, 2):
        pair_type = a[-1] * 2 if a[-1] == b[-1] else "SH"
        match = None if a not in runs or b not in runs else runs[a]["stream"] == runs[b]["stream"]
        counts[pair_type][{None: "undefined", True: "exact", False: "different"}[match]] += 1
    if issues:
        verdict = "INCOMPLETE"
    elif counts["SS"]["different"]:
        verdict = "BASELINE_VARIATION_OBSERVED"
    elif counts["HH"]["different"]:
        verdict = "VARIATION_OBSERVED_WITH_CAPTURE_ENABLED"
    elif counts["SH"]["different"]:
        verdict = "MODE_ASSOCIATED_DIFFERENCE_UNDER_BOTH_ORDERS"
    else:
        verdict = "MISMATCH_NOT_REPRODUCED"
    return {"packet": "WP-0025", "scope": "historical b01w01 ordered three-page input only",
            "verdict": verdict, "receipt_issues": issues, "archive_sha256": inv["archive"]["sha256"],
            "archive_members": len(inv["files"]), "historical_streams": old_hashes,
            "candidate": plan["review_worktree_head"], "order": tags, "runs": runs, "resources": orders,
            "through_eos_matrix": matrix, "pair_counts": counts,
            "target_memory_outcome": None, "stock_hidden_state_observation": None}


if __name__ == "__main__":
    result = summarize()
    with Path(sys.argv[1]).open("x", encoding="utf8", newline="\n") as output:
        json.dump(result, output, indent=2, allow_nan=False)
        output.write("\n")
