"""Reconstruct the terminal blind C1 stop from the preserved incomplete order and non-author evidence."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from gate import evidence, verify_primary
from costs import HOST


def read(p):
    return json.loads(p.read_bytes())


def digest(p):
    return sha256(p.read_bytes()).hexdigest()


def check(revision, inventory_path, review_record):
    release=read(HERE/"blind-c1-r1-release.json")
    order,=release["orders"]
    p=Path(order["plan"])
    if digest(p)!=order["plan_sha256"]:
        raise ValueError("Plan digest changed")
    plan=read(p)
    out=Path(plan["output"])/"sensor"
    warm=read(out/"warmup.json")
    error=read(out/"error.json")
    calls=plan["calls"]
    complete=[c["tag"] for c in calls if (out/c["tag"]/"receipt.json").exists()]
    started=[c["tag"] for c in calls if (out/(c["tag"]+"-begin.json")).exists()]
    if len(complete)!=13 or len(started)!=14 or complete!=error["verified_tags"] or started!=error["started_tags"]:
        raise ValueError("Changed partial execution")
    partial=started[-1]
    folder=out/partial
    native=read(folder/"native.json")
    marker=128827
    positions=[i for i,v in enumerate(native["token_ids"]) if v==marker]
    text_positions=[i for i in range(len(native["text"])) if native["text"].startswith("<PAGE>",i)]
    if (warm["success"] is not True or native["prompt_token_ids"]!=plan["prompt_token_ids"]
            or len(native["prompt_token_ids"])!=827 or native["num_pages_out"]!=4 or native["expected_pages"]!=3
            or positions != [0,42,81,121] or len(text_positions)!=4 or not native["text"].endswith("<PAGE>")
            or len(native["token_ids"])!=122 or native["terminal_observation"]["nxt"]!=native["eos_id"]
            or native["eos_id"]!=1 or not native["eos_observed"]
            or native["terminal_observation"]["guard"]!={"marker_cum":4,"page_len":0,"scanned":122}
            or error["message"]!="Expected three grounded native pages" or sorted(f.name for f in folder.iterdir())!=["native.json"]):
        raise ValueError("Terminal data differs from the observed structural condition")
    compared=[]
    for pair in plan["check_groups"]:
        left,right=pair["left"],pair["right"]
        if left in complete and right in complete:
            fields=("through-eos.u32le","metadata.json","observed-positions.json","token_hidden.bf16","pooled.f32","capture.json")
            same=all((out/left/f).read_bytes()==(out/right/f).read_bytes() for f in fields)
            compared.append({"left":left,"right":right,"exact":same,"fields":list(fields)})
    if len(compared)!=3 or not all(o["exact"] for o in compared):
        raise ValueError("Changed short-horizon duplicate evidence")
    inventory=verify_primary(inventory_path,revision)
    inv=read(inventory_path)
    if inv["members"][f"runs/{order['run']}/sensor/{partial}/native.json"]["sha256"]!=digest(folder/"native.json"):
        raise ValueError("Independent archive does not contain exact terminal native record")
    gate=read(HERE/"h0-gate.json")
    train=read(HERE/"train-c1-gate.json")
    cal=read(ROOT/"docs/reviews/WP-0026/calibration-independent.json")
    entry=read(HERE/"blind-entry.json")
    if (not gate["gate_passed"] or not train["gate_passed"] or cal["fit_sha256"]!=entry["fit_sha256"]
            or read(HERE/"q0-before.json")!=read(HERE/"q0-after.json")):
        raise ValueError("Contradictory development or Q0 record")
    review=evidence(review_record,revision)
    independent=read(review_record)
    runtime_path=review_record.with_name("blind-c1-partial-runtime.json")
    reviewed_clock=evidence(runtime_path,revision)
    clock=read(runtime_path)
    if (independent["disposition"]!="STOP" or independent["complete_captures"]!=len(complete)
            or independent["diagnostic"]["native_sha256"]!=digest(folder/"native.json")
            or independent["cache_release"] or clock["guard_exit"]!=1):
        raise ValueError("Independent completion, native return or disposition differs")
    fail=calls[len(started)-1]
    slot_time=(error["utc_ns"]-read(out/(partial+"-begin.json"))["utc_ns"])/1e9
    guard=read(HOST/"coordination/leases/blind-c1-r1/blind-c1-r1-returned.json")
    if guard["exit"]!=1 or guard["guard"] is not None:
        raise ValueError("Expected returned process error")
    totals=read(HERE/"final-costs.json")["totals"]
    assert totals["scored_started"]==98 and totals["scored_verified"]==97 and totals["physical_calls_started"]==104
    fit=read(ROOT/"docs/research/WP-0026/fit/fit.json")
    now=datetime.now(timezone.utc)
    reserved=datetime.fromisoformat(subprocess.check_output(["git","-C",ROOT,"show","-s","--format=%cI",
                                    "f05dcc4c1f5ca7d7ecd82e83ca63f889369bc6fd"],text=True).strip())
    return {
        "packet":"WP-0026","disposition":"CLOSED_STOPPED_BLIND_C1_INCOMPLETE","memory_comparison":"INCONCLUSIVE_UNSCORED",
        "decision_utc":now.isoformat(),"reservation_utc":reserved.astimezone(timezone.utc).isoformat(),
        "reservation_to_decision_s_including_handoffs":(now-reserved).total_seconds(),
        "independent_stop":review,"independent_partial_clock":reviewed_clock,"primary":inventory,
        "development":{"h0_gate_sha256":digest(HERE/"h0-gate.json"),"exact_h0_pairs":gate["exact_pairs"],
          "first_scored_equal":gate["first_scored_equal"],"required_witnesses_per_mode":gate["unique_witnesses"],
          "h0_reconstructed_pools":gate["pools_reconstructed"],"train_gate_sha256":digest(HERE/"train-c1-gate.json"),
          "train_uncached_calls":28,"train_c1_exact_duplicate_groups":train["exact_duplicate_groups"],
          "c1_six_view_decision_equivalence":read(ROOT/"docs/reviews/WP-0026/train-c1-decisions.json")["six_view_equivalence"],
          "fit_sha256":entry["fit_sha256"],"fit_weights":fit["weights"],"matched_parameters_each":880258,
          "fit_epochs_each":fit["epochs"],"thresholds":fit["thresholds"],
          "calibration_by_arm":{arm:cal["actual_frozen_calibration"][arm]["selected"] for arm in ("M1","M3")}},
        "blind":{"bound_pairs":32,"bound_binders":64,"within_pair_planned_total_calls":276,"uncached_planned":28,
          "started":len(started),"verified_feature_returns":len(complete),"native_returns":len(complete)+1,
          "uncached_not_started":len(calls)-len(started),"residual_feature_calls_started":0,
          "fully_compared_duplicates":compared,"remaining_unverified_duplicates":12-len(compared),
          "verified_consumed_positions":independent["retained_positions"],"reconstructed_pools":independent["recomputed_pools"],
          "completed_12_page_pairs":1,"completed_30_page_pairs":0,"fitted_decision_equivalence_on_blind":None,
          "predictions_frozen":0,"c0":None,"blind_score":None,"donor_outcome":None,"heldout_effect_or_safety_conclusion":None,
          "truth_commitment":entry["truth_commitment"],"scoring_key_release":None},
        "failure":{"tag":partial,"window":fail["window"],"pages_one_based":[3*fail["window"]-2,3*fail["window"]-1,3*fail["window"]],
          "model_ordinal":fail["ordinal"],"native_sha256":digest(folder/"native.json"),"error_sha256":digest(out/"error.json"),
          "expected_pages":3,"reported_pages":4,"page_token_id":marker,"zero_based_page_token_positions":positions,
          "raw_page_marker_offsets":text_positions,"prefix_tokens_before_eos":122,"observed_eos_id":1,
          "terminal_observation":native["terminal_observation"],"final_marker_has_payload":False,
          "grounded_nonempty_segments":independent["diagnostic"]["grounded_nonempty_segments"],
          "parser_sha256":independent["diagnostic"]["parser_sha256"],
          "frozen_parser_exception":error["message"],"guard_exit":guard["exit"],"guard_reason":guard["guard"],
          "guard_source_sha256":plan["module_sha256"],"native_page_guard_line":583,"frozen_span_gate_line":108,
          "cause_limit":"The native guard permits another page marker at the expected count and forces EOS after the count is exceeded. The evidence does not locate why the model selected that marker."},
        "costs":{"aggregate":totals,"incomplete_slot_native_reported_s":native["time"],"incomplete_slot_begin_to_error_s":slot_time,
          "incomplete_slot_wrapper_inference_s":None,"blind_c1_scored_inference_bounds_s":clock["scored_inference_s_bounds"],
          "fit_phase_s":read(ROOT/"docs/research/WP-0026/fit/process.json")["elapsed_phase_ns"]/1e9,
          "optimization_s":{arm:fit["training"][arm]["training_seconds"] for arm in ("M1","M3")},
          "scope":"Scored aggregate inference and capture timings cover 97 verified calls only. The partial call is included in physical counts and whole-order time."},
        "q0":{"matched":True,"entries":read(HERE/"q0-after.json")["whole_tree_entries"],"full_model_content_hashes":37},
        "next_gpu_release":None
    }


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("revision")
    p.add_argument("inventory",type=Path)
    p.add_argument("review_record",type=Path)
    args=p.parse_args()
    doc=check(args.revision,args.inventory.resolve(),args.review_record.resolve())
    with (HERE/"decision.json").open("x",encoding="utf8",newline="\n") as f:
        json.dump(doc,f,indent=2,allow_nan=False);f.write("\n")
    print(doc["disposition"],doc["failure"]["tag"],doc["primary"]["members"])
