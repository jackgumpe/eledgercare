"""Reproduce the terminal blind C1 stop and audit only the evidence actually written."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_common import HOST, MODEL, ROOT, blob, cpu, pinned, read, reference, sample, save, sha, stream
from c1 import same_rasters
from w0_inputs import RECEIPT

EXPECTED_FAILURE = "Expected three grounded native pages"
ARTIFACTS = ("metadata.json", "observed-positions.json", "token_hidden.bf16", "pooled.f32",
             "through-eos.u32le", "capture.json")
NATIVE_FIELDS = ("prompt", "prompt_token_ids", "token_ids", "text", "eos_id", "eos_observed",
                 "expected_pages", "num_pages_out", "terminal_observation", "stop_cause", "finish_reason")


def reproduce(slot, dev, candidate, plan):
    from span_audit import ADDED, NATIVE, T, TITLE, token_piece
    script = "docs/research/WP-0024/sensor/spans.py"
    source = dev / script
    assert source.read_bytes() == blob(candidate, script)
    sys.path.insert(0, str(source.parent))
    import spans
    assert Path(spans.__file__).resolve() == source.resolve()
    spans.verify_parsers()
    native = read(slot / "native.json")
    raw, ids, term = native["text"], native["token_ids"], native["terminal_observation"]
    assert native["prompt"] == plan["prompt"] and native["prompt_token_ids"] == plan["prompt_token_ids"]
    assert T.decode(ids, skip_special_tokens=False) == raw
    assert b"".join(map(token_piece, ids)) == raw.encode("utf8")
    vocabulary = lambda seq: [T.id_to_token(i) for i in seq]
    try:
        spans.map_window(raw, ids, vocabulary, {i: b.decode("utf8") for i, b in ADDED.items()})
    except ValueError as exc:
        assert str(exc) == EXPECTED_FAILURE
    else:
        raise AssertionError("Frozen parser accepted partial native output")
    markers = [m.start() for m in re.finditer(re.escape("<PAGE>"), raw)]
    token_markers = [n for n, i in enumerate(ids) if i == T.token_to_id("<PAGE>")]
    assert native["expected_pages"] == 3
    assert len(markers) == len(token_markers) == native["num_pages_out"] == term["guard"]["marker_cum"] == 4
    assert markers[0] == token_markers[0] == 0 and token_markers[-1] == len(ids)-1
    assert term["nxt"] == native["eos_id"] == 1 and 1 not in ids and term["step"] == len(ids)
    assert term["guard"] == {"marker_cum":4,"page_len":0,"scanned":len(ids)}
    assert native["eos_observed"] and native["stop_cause"] == "eos" and native["finish_reason"] == "stop"
    assert term["prompt_length"] == len(native["prompt_token_ids"]) == 827
    assert term["max_new_tokens"] == plan["settings"]["max_new_tokens"] and term["max_length"] == plan["settings"]["max_length"]
    pages = []
    for index, (lo, hi) in enumerate(zip(markers, markers[1:]+[len(raw)], strict=True), 1):
        part = raw[lo:hi]
        parsed = NATIVE(TITLE.sub(r"\1", part), (612,792))
        pages.append({"marker":index, "marker_char_offset":lo, "marker_token_offset":token_markers[index-1],
                      "characters_after_marker":len(part)-len("<PAGE>"),
                      "grounded_nonempty_spans":sum(bool(b["text"].strip()) for b in parsed["spans"]),
                      "tables":len(parsed["tables"]), "table_rows":sum(len(t["rows"]) for t in parsed["tables"])})
    assert pages[-1]["characters_after_marker"] == pages[-1]["grounded_nonempty_spans"] == 0
    encoded = struct.pack("<"+"I"*(len(ids)+1), *ids, term["nxt"])
    return {"parser_revision":candidate, "parser_path":script, "parser_sha256":sha(source.read_bytes()),
            "native_sha256":sha((slot/"native.json").read_bytes()), "frozen_exception":EXPECTED_FAILURE,
            "decoded_raw_and_all_token_bytes_verified":True, "expected_pages":3, "emitted_markers":len(markers),
            "grounded_nonempty_segments":sum(p["grounded_nonempty_spans"] > 0 for p in pages), "segments":pages,
            "prompt_ids":827, "emitted_before_eos":len(ids), "terminal_observation":term, "finish_reason":"stop",
            "stop_cause":"eos", "derived_through_eos_u32le_sha256":sha(encoded),
            "generation_s":native["time"], "prefill_s":native["prefill_time"],
            "retained_files":sorted(p.name for p in slot.iterdir()),
            "missing_postparse_files":sorted((*ARTIFACTS,"duration.json","receipt.json"))}


def inspect(release_file, release_pin):
    release = pinned(release_file,release_pin)
    order, = release["orders"]
    name = order["run"]
    plan = pinned(Path(order["plan"]),order["plan_sha256"])
    dev = Path(release["worktree"])
    assert release["review_worktree_head"] == plan["candidate"] and plan["model_revision"] == MODEL
    assert all(sha((dev/k).read_bytes()) == v for k,v in release["source_files"].items())
    d = Path(order["output"])/"sensor"
    known = reference()
    for key in ("historical_platform","model_revision","module_sha256","tokenizer_sha256","model_manifest_sha256",
                "target_dtype","prompt_token_ids","prompt_sha256","prompt","api_prompt","settings","eos_id"):
        assert known[key] == plan[key]
    cold,bind,warm,error = [read(d/(f+".json")) for f in ("cold","binding","warmup","error")]
    identity = {k:bind[k] for k in ("pid","parent_pid","process_create_filetime","model_load_id","plan_sha256",
                                    "process_id","lease","candidate","model_revision","gpu_uuid")}
    assert all(all(row[k] == v for k,v in identity.items()) for row in (cold,warm,error))
    assert identity["plan_sha256"] == order["plan_sha256"] and identity["candidate"] == plan["candidate"]
    assert identity["gpu_uuid"] == release["gpu_uuid"] and identity["model_revision"] == MODEL
    assert bind["settings"] == plan["settings"] and bind["request_prompt"] == plan["api_prompt"]
    assert bind["model_load_id"] == f"{bind['pid']}-{bind['process_create_filetime']}-1"
    assert cold["loads"] == 1 and cold["model"]["platform"] == plan["historical_platform"]
    assert cold["model"]["target_dtype"] == "torch.bfloat16"
    assert warm["tag"] == "W0" and warm["mode"] == "S" and warm["ordinal"] == 1 and warm["scored"] is False
    assert warm["fixture_sha256"] == plan["warmup"]["fixture_sha256"] == bind["warmup_fixture_sha256"] == RECEIPT
    assert warm["pages"] == plan["warmup"]["pages"] and warm["request"] == plan["warmup"]["request"]
    assert warm["success"] and warm["eos_observed"] and warm["finish_reason"] == "stop"
    assert warm["prompt"] == warm["observed_prompt"] == bind["prompt"] == plan["prompt"]
    assert warm["observed_prompt_token_ids"] == warm["prompt_token_ids"] == bind["prompt_token_ids"] == plan["prompt_token_ids"]
    assert warm["terminal_observation"]["nxt"] == warm["eos_id"] == 1
    assert warm["terminal_observation"]["guard"]["marker_cum"] == 3 and warm["terminal_observation"]["step"] == warm["emitted"]
    assert bind["utc_ns"] <= cold["start_utc_ns"] < cold["ready_utc_ns"] <= warm["start_utc_ns"] < warm["end_utc_ns"]
    assert error["status"] == "incomplete" and error["error_type"] == "ValueError" and error["message"] == EXPECTED_FAILURE
    assert not (d/"outcome.json").exists()
    calls = {c["tag"]:c for c in plan["calls"]}
    tags = list(calls)
    started,completed = error["started_tags"],error["verified_tags"]
    assert len(tags) == 28 and bind["order"] == tags and completed == tags[:13] and started == tags[:14]
    assert [t for t in tags if (d/t).exists()] == [t for t in tags if (d/(t+"-begin.json")).exists()] == started
    assert [t for t in tags if (d/t/"receipt.json").exists()] == completed
    assert [p.name for p in (d/started[-1]).iterdir()] == ["native.json"]
    assert all(c["hooked"] and c["retain_hidden"] for c in calls.values())
    warm_sha = sha((d/"warmup.json").read_bytes())
    rows, groups = {}, []
    exact_s = window_s = 0
    previous = warm["end_utc_ns"]
    for ordinal,tag in enumerate(started,2):
        c = calls[tag]
        begin = read(d/(tag+"-begin.json"))
        recs = [begin] + ([read(d/tag/"receipt.json")] if tag in completed else [])
        for r in recs:
            assert all(r[k] == v for k,v in identity.items())
            assert r["ordinal"] == c["ordinal"] == ordinal and r["tag"] == tag and r["mode"] == c["mode"]
            assert r["pages"] == c["pages"] and r["window"] == c["window"] and r["binder"] == c["binder"]
            assert r["sensor_candidate"] == plan["historical_sensor_revision"] and r["warmup_sha256"] == warm_sha
            assert r["warmup_fixture_sha256"] == RECEIPT
        assert previous <= begin["utc_ns"]
        if tag in completed:
            dur,rec = read(d/tag/"duration.json"),recs[-1]
            assert begin["utc_ns"] <= dur["start_utc_ns"] < dur["end_inference_utc_ns"] <= dur["end_capture_utc_ns"] <= rec["utc_ns"]
            previous = rec["utc_ns"]
            assert rec["verified"] and all(sha((d/tag/f).read_bytes()) == digest for f,digest in rec["artifacts"].items())
            n = read(d/tag/"native.json")
            ids,term = n["token_ids"],n["terminal_observation"]
            assert ids.count(128827) == 3 and ids[0] == 128827
            assert term["guard"] == {"marker_cum":3,"scanned":len(ids),"page_len":ids[::-1].index(128827)}
            assert term["max_new_tokens"] == plan["settings"]["max_new_tokens"] and term["max_length"] == plan["settings"]["max_length"]
            rows[tag] = sample(d/tag,True,known)
            assert rows[tag]["through_eos_sha256"] == rec["through_eos_sha256"] and len(ids)+1 == rec["through_eos_length"]
            exact_s += dur["wall_inference_ns"]
            window_s += dur["complete_window_wall_ns"]
    failed = started[-1]
    diagnostic = reproduce(d/failed,dev,plan["candidate"],plan)
    upper = (error["utc_ns"] - read(d/(failed+"-begin.json"))["utc_ns"])/1e9
    assert 0 < diagnostic["generation_s"] <= upper
    assert len(plan["check_groups"]) == 12
    for g in plan["check_groups"]:
        a,b = (calls[g[key]] for key in ("left","right"))
        assert g["mode"] == "duplicate" and a["binder"] != b["binder"] and a["window"] == b["window"]
        left,right = a["tag"],b["tag"]
        same_rasters(a["pages"],b["pages"])
        def state(tag):
            return "complete" if tag in rows else "native-only" if tag == failed else "unissued"
        group = {"left":left,"right":right,"window":a["window"],"states":[state(left),state(right)],
                 "three_source_png_and_rgb_pairs_equal":True,"result":"unassessable"}
        if left in rows and right in rows:
            equal = {f:(d/left/f).read_bytes() == (d/right/f).read_bytes() for f in ARTIFACTS}
            na,nb = [read(d/tag/"native.json") for tag in (left,right)]
            equal.update({k:na[k] == nb[k] for k in NATIVE_FIELDS})
            equal["observed_through_eos"] = stream(d/left) == stream(d/right)
            assert all(equal.values())
            group.update(equal=equal,result="byte-exact")
        groups.append(group)
    assert sum(g["result"] == "byte-exact" for g in groups) == 3
    lease = HOST/"coordination/leases"/name
    acq,returned = [read(lease/(f+".json")) for f in ("acquired","returned")]
    issue,desktop,job = [read(lease/(name+"-"+f+".json")) for f in ("issued","desktop-admission","returned")]
    op = HOST/"review/operator"/name
    opissue,opret = [read(op/(f+".json")) for f in ("issued","return")]
    proc = read(d.parent/"process.json")
    seg, = proc["segments"]
    assert acq["release_sha256"] == returned["release_sha256"] == opissue["release_sha256"] == release_pin
    assert acq["pid"] == returned["retiring_pid"] and not desktop["unrecognized_gpu_clients"]
    assert not opissue["board"]["holds"] and not opret["board"]["holds"]
    assert seg["plan_sha256"] == order["plan_sha256"] and seg["launcher_pid"] == bind["parent_pid"]
    assert seg["start_utc_ns"] <= bind["utc_ns"] and error["utc_ns"] <= seg["end_utc_ns"]
    assert not proc["all_segments_completed"] and job["exit"] == opret["exit_code"] == seg["returncode"] == 1
    assert job["guard"] is None and returned["error"] == "RuntimeError('Order blind-c1-r1 stopped. 1')"
    samples = [json.loads(line) for line in (lease/(name+"-device.jsonl")).read_bytes().splitlines()]
    peak = max(s["used_mib"] for s in samples)
    assert peak <= release["ceiling_mib"] and issue["admission"]["device"]["free_mib"] >= release["free_floor_mib"]
    assert issue["admission"]["ollama_models"] == job["ownership_after_job_close"]["ollama_models"] == 0
    runt = {"candidate":plan["candidate"],"release_sha256":release_pin,"plan_sha256":order["plan_sha256"],
            "identity":identity,"load_s":cold["elapsed_ns"]/1e9,"warmup_elapsed_s":warm["elapsed_ns"]/1e9,
            "warmup_inference_s":warm["wall_inference_ns"]/1e9,"warmup_sha256":warm_sha,"warmup_emitted":warm["emitted"],
            "issued_scored":started,"verified_scored":completed,"unissued":tags[len(started):],
            "exact_completed_scored_inference_s":exact_s/1e9,"exact_completed_scored_window_s":window_s/1e9,
            "partial_generation_s":diagnostic["generation_s"],"partial_prefill_s_included":diagnostic["prefill_s"],
            "partial_elapsed_upper_bound_begin_to_error_s":upper,"partial_exact_capture_clock":None,
            "scored_inference_s_bounds":[exact_s/1e9+diagnostic["generation_s"],exact_s/1e9+upper],
            "fault_worker_s":error["elapsed_ns"]/1e9,"supervisor_elapsed_s":seg["elapsed_s"],
            "guarded_order_wall_s":job["wall_s"],"guard_utc":[acq["utc"],returned["utc"]],
            "whole_guard_s":(datetime.fromisoformat(returned["utc"])-datetime.fromisoformat(acq["utc"])).total_seconds(),
            "admission_free_mib":issue["admission"]["device"]["free_mib"],"return_free_mib":job["ownership_after_job_close"]["device"]["free_mib"],
            "board_samples":len(samples),"peak_board_used_mib":peak,"guard_exit":1,"guard_error":returned["error"],
            "native_model_calls_including_w0":1+len(started),"model_loads":1,"w0_calls":1}
    part = {"disposition":"STOP","candidate":plan["candidate"],"plan_sha256":order["plan_sha256"],
            "checked_receipts":rows,"complete_captures":len(rows),"retained_positions":sum(r["positions"] for r in rows.values()),
            "recomputed_pools":sum(r["pooled_bit_exact"] for r in rows.values()),"partial_tag":failed,
            "partial_model_ordinal":calls[failed]["ordinal"],"partial_window":calls[failed]["window"],
            "diagnostic":diagnostic,"groups":groups,"six_view_blind_equivalence":"not reached",
            "cache_release":False,"blind_scoring":"not reached"}
    return runt,part


if __name__ == "__main__":
    cpu()
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("release",type=Path)
    cli.add_argument("pin")
    cli.add_argument("runtime",type=Path)
    cli.add_argument("c1",type=Path)
    argv = cli.parse_args()
    runtime,c1 = inspect(argv.release,argv.pin)
    save(argv.runtime,runtime)
    save(argv.c1,c1)
