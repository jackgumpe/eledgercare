"""Inspect released development inputs and prior costs. This program has no model execution path."""
from collections import defaultdict
from contextlib import closing
from hashlib import sha256
from io import BytesIO
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

if os.environ.get("CUDA_VISIBLE_DEVICES") != "-1" or not sys.flags.isolated or not sys.dont_write_bytecode:
    raise SystemExit("Use CPU-only isolated Python with bytecode disabled")
import pypdfium2 as pdfium

BASE = "71e451d8eafdfa15245e522d347bdf781b0c57b7"
CAL = "docs/fixtures/WP-0024/v2/cal/"
COORD = "docs/coordination/WP-0026/"
REVIEW = "docs/reviews/WP-0026/cal-features-primary/"
PUBLIC = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0024/custody/v2/public/cal")
TEMPLATES = {12: "366ef9f7a5a787497b0f6634", 30: "dd21685671af3251fb1cbcd6"}
SOURCES = {"handoff.md": "561609e611657e83ac761cd58c696c63cade5a8334c7a088dd90d992706dbf83",
           "owner-math.pdf": "926356c85d186244cfa7e22947d72604d44dc3f483ea3cb91979ab20d1ed0f94"}
INPUT_PINS = {}


def digest(data):
    return sha256(data).hexdigest()


def blob(path, ref=BASE):
    data = subprocess.check_output(["git", "cat-file", "blob", f"{ref}:{path}"])
    INPUT_PINS[path] = {"revision": ref, "sha256": digest(data)}
    return data


def at(path):
    return json.loads(blob(path))


def pages_key(pages):
    return tuple((p["sha256"], p["rgb_sha256"]) for p in pages)


def pages_record(key):
    return [{"position": i, "png_sha256": png, "rgb_sha256": rgb} for i, (png, rgb) in enumerate(key, 1)]


def first_page(data):
    with pdfium.PdfDocument(data) as pdf, closing(pdf[0]) as page:
        assert page.get_size() == (612, 792)
        with closing(page.render(scale=math.nextafter(300/72, 0))) as bitmap, bitmap.to_pil().convert("RGB") as image:
            assert image.size == (2550, 3300)
            encoded = BytesIO()
            image.save(encoded, format="PNG", dpi=(300, 300), compress_level=3)
            return digest(encoded.getvalue()), digest(image.tobytes())


def study_routes():
    binders = {r["binder"]:r for r in at(CAL+"manifest.json")["binders"]}
    pdfs = at(CAL+"receipt.json")["source_pdfs"]
    routes = defaultdict(list)
    for horizon, binder in TEMPLATES.items():
        source = (PUBLIC/"pdf"/(binder+".pdf")).read_bytes()
        original = b"(Ledger: Alder) Tj"
        assert digest(source) == pdfs[binder] and source.count(original) == 1
        windows = binders[binder]["windows"]
        assert len(windows)*3 == horizon
        base_page = pages_key(windows[0]["pages"])[0]
        assert first_page(source) == base_page
        changed_page = first_page(source.replace(original, b"(Ledger: Cedar) Tj"))
        assert changed_page != base_page
        for window in windows:
            base_key = pages_key(window["pages"])
            edited_key = (changed_page, *base_key[1:]) if window["window"] == 1 else base_key
            for owner, key in (("Alder",base_key), ("Cedar",edited_key)):
                routes[key].append({"horizon":horizon, "owner":owner, "window":window["window"]})
    return routes


def eligible_orders():
    calls = defaultdict(list)
    plans = {}
    for release_name in ("h0-r1", "train-c1-r1", "train-features-r1", "cal-features-r1"):
        release = at(COORD+release_name+"-release.json")
        for order in release["orders"]:
            path = COORD+Path(order["plan"]).name
            raw = blob(path)
            assert digest(raw) == order["plan_sha256"]
            plan = json.loads(raw)
            plans[order["run"]] = plan
            for call in plan["calls"]:
                if call["hooked"] and call["mode"] == "H":
                    calls[pages_key(call["pages"])].append((release_name,order["run"],call["tag"]))
    return calls, plans["cal-features-r1"]


def checked_member(archive, prefix, name, receipt):
    data = archive.read(prefix+name)
    assert digest(data) == receipt["artifacts"][name]
    return data


def proposal():
    for name, expected in SOURCES.items():
        assert digest(blob("docs/coordination/WP-0028/"+name,"c000c0299619345c887859b95c45befbb0c68987")) == expected
    routes = study_routes()
    eligible, plan = eligible_orders()
    inv = at(REVIEW+"inventory.json")
    archive = blob(REVIEW+"primary-001.zip")
    assert digest(archive) == inv["parts"]["primary-001.zip"]["sha256"]
    missing, cached = [], []
    reference = None
    with ZipFile(BytesIO(archive)) as z:
        for key, uses in routes.items():
            matches = eligible.get(key, [])
            if not matches:
                missing.append({"ordered_pages":pages_record(key), "uses":uses})
                continue
            # All already-available windows on these predeclared templates have a verifiable calibration return.
            matches = [tag for rel, _, tag in matches if rel == "cal-features-r1"]
            if not matches:
                raise ValueError("Found a matching non-calibration capture requiring independent authentication")
            tag = sorted(matches)[0]
            prefix = "runs/cal-features-r1/sensor/"+tag+"/"
            receipt = json.loads(z.read(prefix+"receipt.json"))
            assert receipt["verified"] and receipt["mode"] == "H" and pages_key(receipt["pages"]) == key
            assert receipt["model_revision"] == plan["model_revision"] and receipt["sensor_candidate"] == plan["historical_sensor_revision"]
            assert receipt["plan_sha256"] == INPUT_PINS[COORD+"cal-features-r1-plan.json"]["sha256"]
            for name in ("metadata.json","pooled.f32","through-eos.u32le","capture.json"):
                checked_member(z, prefix, name, receipt)
            duration = checked_member(z,prefix,"duration.json",receipt)
            cached.append({"tag":tag, "ordered_pages":pages_record(key), "uses":uses,
                           "metadata_sha256":receipt["artifacts"]["metadata.json"], "pooled_sha256":receipt["artifacts"]["pooled.f32"],
                           "through_eos_sha256":receipt["through_eos_sha256"]})
            if {"owner":"Alder","horizon":12,"window":1} in uses:
                reference = {"tag":tag,"duration_sha256":digest(duration),"source":prefix+"duration.json",
                             "complete_window_seconds":json.loads(duration)["complete_window_wall_ns"]/1e9,
                             "warmup_receipt_sha256":receipt["warmup_sha256"]}
    assert reference is not None
    order, = [d for d in at(COORD+"development-costs.json")["orders"] if d["lease"] == "cal-features-r1"]
    r = at(COORD+"cal-features-r1-release.json")
    reference.update(load_seconds=order["load_s"], warmup_seconds=order["w0_s"],
                     historical_global_peak_board_mib=order["board_sampled_peak_mib"])
    reference["combined_comparator_seconds"] = reference["load_seconds"]+reference["warmup_seconds"]+reference["complete_window_seconds"]
    proposed = None
    if len(missing)==1:
        proposed = {"released":False, "device_execution_in_this_packet":0, "loads":1,
                    "excluded_W0_calls":1, "scored_B1_calls":1, "maximum_total_native_calls":2,
                    "automatic_retries":0,"hard_supervised_wall_seconds":180,
                    "historical_device_ceiling_mib":r["ceiling_mib"], "historical_preflight_free_floor_mib":r["free_floor_mib"],
                    "native_model_revision":plan["model_revision"], "model_manifest_sha256":plan["model_manifest_sha256"],
                    "pinned_worker_revision":r["review_worktree_head"], "capture_revision":plan["historical_sensor_revision"],
                    "dtype":plan["target_dtype"], "warmup_fixture_sha256":r["warm_fixture_sha256"],
                    "operator":"Uninvolved native research reviewer on one verified exclusive device lease in a separately authorized packet.",
                    "admission":"One verified W0 on the new load, then exactly the listed missing ordered RGB triple. Reject on identity or W0 mismatch, missing EOS, invalid source-page span or feature-position binding, invalid hash, time or VRAM ceiling. Bind through-EOS IDs, metadata, normalized decoder input to the LM head, pooled F32, and acquisition receipts together. An independent verifier must check source/worker identity, source order, archive bytes and W0/return provenance before a CPU probe reads it.",
                    "reuse":"Point both identical opening-window uses at the one authenticated return; keep all existing validated feature references. A stopped or unverifiable call ends this proposal's budget."}
    return {"packet":"WP-0028","status":"CPU analysis of released development source and archives","archive_scope":"Two H0 orders, development C1, training feature acquisition and calibration feature acquisition, hooked W0-conditioned records only.",
            "source_base":BASE,"templates":TEMPLATES,"logical_windows":sum(map(len,routes.values())),"unique_ordered_windows":len(routes),
            "cached_unique":len(cached), "cached_logical":sum(len(r["uses"]) for r in cached),
            "missing_unique":len(missing),"missing_logical":sum(len(r["uses"]) for r in missing),
            "missing":missing, "cached":cached, "historical_timing_comparator":reference,
            "proposed_future_acquisition":proposed, "input_identities":INPUT_PINS}


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.write_bytes((json.dumps(proposal(),indent=2)+"\n").encode("utf8"))
    print(digest(out.read_bytes()))
