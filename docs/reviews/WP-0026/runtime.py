"""Reconcile model/load/W0 identities, raw scored receipts, native EOS, ownership, order and costs."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_common import HOST, MODEL, cpu, pinned, read, reference, save, sha, stream
from w0_inputs import RECEIPT

def verify_order(order,release,pin,lease):
    name = order["run"]
    plan = pinned(Path(order["plan"]),order["plan_sha256"])
    assert plan["candidate"] == release["review_worktree_head"] and plan["model_revision"] == MODEL
    d = Path(order["output"])/"sensor"
    assert d.parent == HOST/"review/runs"/name
    known = reference()
    for k in ("historical_platform","model_revision","module_sha256","tokenizer_sha256","model_manifest_sha256",
              "target_dtype","prompt_token_ids","prompt_sha256","prompt","api_prompt","settings","eos_id"):
        assert plan[k] == known[k], k
    cold,bind,warm,outcome = [read(d/(f+".json")) for f in ("cold","binding","warmup","outcome")]
    assert cold["loads"] == 1 and cold["model"]["platform"] == plan["historical_platform"]
    assert cold["model"]["target_dtype"] == "torch.bfloat16"
    assert cold["model"]["model_revision"] == MODEL
    identity = {k:bind[k] for k in ("model_load_id","pid","process_create_filetime","parent_pid","plan_sha256",
                                      "candidate","model_revision","process_id","lease","gpu_uuid")}
    assert bind["plan_sha256"] == order["plan_sha256"] and bind["gpu_uuid"] == release["gpu_uuid"]
    assert bind["model_load_id"] == f"{bind['pid']}-{bind['process_create_filetime']}-1"
    for r in (cold,warm,outcome):
        assert all(r[k] == v for k,v in identity.items())
    assert bind["settings"] == plan["settings"] and bind["request_prompt"] == plan["api_prompt"]
    omitted = {"PATHEXT","NUMBER_OF_PROCESSORS","windir","SystemRoot","PROCESSOR_IDENTIFIER","OS",
               "PROCESSOR_REVISION","PROCESSOR_LEVEL","ComSpec","PROCESSOR_ARCHITECTURE"}
    assert bind["environment"] == {k:v for k,v in plan["environment"].items() if k not in omitted}
    assert bind["warmup_fixture_sha256"] == RECEIPT
    warm_pin = sha((d/"warmup.json").read_bytes())
    assert warm["fixture_sha256"] == plan["warmup"]["fixture_sha256"] == RECEIPT
    assert warm["tag"] == "W0" and warm["mode"] == "S" and warm["ordinal"] == 1 and warm["scored"] is False
    assert warm["success"] is True and warm["eos_observed"] is True and warm["finish_reason"] == "stop"
    assert warm["prompt"] == warm["observed_prompt"] == bind["prompt"] == plan["prompt"]
    assert warm["observed_prompt_token_ids"] == warm["prompt_token_ids"] == bind["prompt_token_ids"] == plan["prompt_token_ids"]
    assert warm["prompt_shape"] == warm["observed_prompt_shape"] == [1,827]
    assert warm["prompt_sha256"] == bind["prompt_sha256"] == plan["prompt_sha256"]
    assert warm["request"] == plan["warmup"]["request"] == plan["requests"][0] and warm["pages"] == plan["warmup"]["pages"]
    assert "token_ids" not in warm and "text" not in warm and not (d/"W0").exists()
    assert not {p["rgb_sha256"] for p in warm["pages"]}.intersection(
        p["rgb_sha256"] for c in plan["calls"] for p in c["pages"])
    t = warm["terminal_observation"]
    assert t["nxt"] == warm["eos_id"] == 1 and t["guard"]["marker_cum"] == 3
    assert t["step"] == t["guard"]["scanned"] == warm["emitted"] and 0 <= t["guard"]["page_len"] < t["step"]
    assert t["prompt_length"] == 827 and 0 < t["step"] < t["max_new_tokens"] == plan["settings"]["max_new_tokens"]
    assert t["step"] + 827 < t["max_length"] == plan["settings"]["max_length"]
    assert bind["utc_ns"] <= cold["start_utc_ns"] < cold["ready_utc_ns"] <= warm["start_utc_ns"] < warm["end_utc_ns"]
    tags = [c["tag"] for c in plan["calls"]]
    assert bind["order"] == outcome["started_tags"] == outcome["verified_tags"] == tags
    assert set(outcome["rows"]) == set(tags) and outcome["real_inference_calls"] == len(tags)
    assert outcome["warmup_calls"] == 1 and outcome["total_inference_calls"] == len(tags)+1
    previous = warm["end_utc_ns"]
    total = complete = 0
    captured = []
    for ordinal,c in enumerate(plan["calls"],2):
        tag = c["tag"]
        s = d/tag
        start,r = read(d/(tag+"-begin.json")),read(s/"receipt.json")
        duration = read(s/"duration.json")
        for rec in (start,r):
            assert all(rec[k] == v for k,v in identity.items())
            assert rec["warmup_sha256"] == warm_pin and rec["warmup_fixture_sha256"] == RECEIPT
            assert rec["ordinal"] == c["ordinal"] == ordinal and rec["mode"] == c["mode"]
            assert rec["sensor_candidate"] == plan["historical_sensor_revision"]
            assert rec["pages"] == c["pages"] and rec["binder"] == c["binder"] and rec["window"] == c["window"]
        assert previous <= start["utc_ns"] <= duration["start_utc_ns"] < duration["end_inference_utc_ns"]
        assert duration["end_inference_utc_ns"] <= duration["end_capture_utc_ns"] <= r["utc_ns"]
        previous = r["utc_ns"]
        assert r["verified"] is True and all(sha((s/f).read_bytes()) == v for f,v in r["artifacts"].items())
        native = read(s/"native.json")
        assert native["prompt_token_ids"] == plan["prompt_token_ids"] and native["prompt"] == plan["prompt"]
        ids,terminal = native["token_ids"],native["terminal_observation"]
        assert ids.count(128827) == 3 and ids[0] == 128827 and ids[-1] != 1
        assert terminal["guard"] == {"marker_cum":3,"scanned":len(ids),"page_len":ids[::-1].index(128827)}
        assert terminal["max_length"] == t["max_length"] and terminal["max_new_tokens"] == t["max_new_tokens"]
        assert sha(stream(s)) == r["through_eos_sha256"] and len(ids)+1 == r["through_eos_length"]
        total += duration["wall_inference_ns"]
        complete += duration["complete_window_wall_ns"]
        captured.append({"tag":tag,"ordinal":ordinal,"mode":c["mode"],"emitted":len(ids),"through_eos":r["through_eos_sha256"]})
    assert outcome["load_s"] == cold["elapsed_ns"]/1e9 and outcome["warmup_s"] == warm["elapsed_ns"]/1e9
    assert outcome["scored_inference_s"] == total/1e9 and outcome["window_metric_sum_s"] == complete/1e9
    issue,desktop,ret = [read(lease/(name+"-"+f+".json")) for f in ("issued","desktop-admission","returned")]
    proc = read(d.parent/"process.json")
    seg, = proc["segments"]
    assert seg["plan_sha256"] == order["plan_sha256"] and seg["launcher_pid"] in (bind["parent_pid"],bind["pid"])
    assert desktop["unrecognized_gpu_clients"] == [] and issue["admission"]["ollama_models"] == 0
    assert issue["admission"]["device"]["free_mib"] >= 12000 and ret["ownership_after_job_close"]["ollama_models"] == 0
    assert seg["start_utc_ns"] <= bind["utc_ns"] and previous <= seg["end_utc_ns"]
    samples = [json.loads(x) for x in (lease/(name+"-device.jsonl")).read_bytes().splitlines()]
    peak = max(s["used_mib"] for s in samples)
    assert peak <= 12500
    return {"phase":plan["phase"],"split":plan["split"],"identity":identity,"warmup_sha256":warm_pin,
            "load_s":cold["elapsed_ns"]/1e9,"model_load_ms":cold["model"]["load_ms"],"warmup_s":warm["elapsed_ns"]/1e9,
            "warmup_inference_s":warm["wall_inference_ns"]/1e9,"warmup_emitted_before_eos":warm["emitted"],
            "warmup_through_eos_sha256":warm["through_eos_sha256"],"scored_calls":len(tags),"scored_inference_s":total/1e9,
            "scored_complete_window_s":complete/1e9,"phase_s":outcome["complete_phase_s"],"samples":len(samples),
            "peak_board_used_mib":peak,"minimum_free_mib":min(s["free_mib"] for s in samples),
            "admission_free_mib":issue["admission"]["device"]["free_mib"],"return_free_mib":ret["ownership_after_job_close"]["device"]["free_mib"],
            "job":issue["job"],"guard_wall_s":ret["wall_s"],"order_exit":ret["exit"],"guard_error":ret["guard"],
            "outcome_status":outcome["status"],"process_completed":proc["all_segments_completed"],
            "supervisor_interval":[seg["start_utc_ns"],seg["end_utc_ns"]],"scored":captured}

def audit(path,pin):
    rel = pinned(path,pin)
    lease = HOST/"coordination/leases"/rel["name"]
    acq,ret = [read(lease/(s+".json")) for s in ("acquired","returned")]
    assert acq["release_sha256"] == ret["release_sha256"] == pin and acq["pid"] == ret["retiring_pid"]
    operator = HOST/"review/operator"/rel["name"]
    observed = read(operator/"issued.json")
    assert observed["release_sha256"] == pin and observed["board"]["holds"] == []
    op_return = read(operator/"return.json")
    rows = [verify_order(o,rel,pin,lease) for o in rel["orders"]]
    assert len({r["identity"]["model_load_id"] for r in rows}) == len(rows) == len({r["job"] for r in rows})
    for before,after in zip(rows,rows[1:]):
        assert before["supervisor_interval"][1] < after["supervisor_interval"][0]
    ok = op_return["exit_code"] == 0 and not ret["error"] and all(
        r["order_exit"] == 0 and r["guard_error"] is None and r["process_completed"] and r["outcome_status"]=="complete" for r in rows)
    return {"release_sha256":pin,"candidate":rel["review_worktree_head"],"orders":rows,"clean_return":ok,
            "guard_error":ret["error"],"guard_pid":acq["pid"],"operator_exit":op_return["exit_code"],
            "guard_interval":[acq["utc"],ret["utc"]],"guard_total_s":(datetime.fromisoformat(ret["utc"])-datetime.fromisoformat(acq["utc"])).total_seconds(),
            "returned_utc":op_return["utc"],"post_observation_holds":op_return["board"]["holds"]}

if __name__ == "__main__":
    cpu()
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("release",type=Path)
    cli.add_argument("digest")
    cli.add_argument("output",type=Path)
    a = cli.parse_args()
    save(a.output,audit(a.release,a.digest))
