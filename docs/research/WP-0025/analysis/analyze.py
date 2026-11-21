"""Analyze frozen WP-0025 evidence without initializing model or device."""
import argparse
from collections import Counter, defaultdict
from itertools import combinations
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from compare import compare_hidden, compare_streams, order_profile, signature
from evidence import BASE_FILES, H_FILES, PIN, SIGNATURE, Reference, check, checked_file, digest, ids_bytes, packed, reconstruct_pool

ORDERS = {"P1":"SHHS","P2":"HSSH"}
HOST = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0025")
IDENTITY = ("packet","process_id","process_ordinal","candidate","plan_sha256","pid","process_create_filetime","parent_pid")
ERRORS = (OSError, ValueError, KeyError, IndexError, TypeError, OverflowError)


def read(path):
    return json.loads(path.read_bytes())


def same_identity(row,binding):
    check(all(row[k]==binding[k] for k in IDENTITY), "Process identity disagreement")


def schedule():
    items = []
    for p,order in ORDERS.items():
        for j,mode in enumerate(order,1):
            previous = order[j-2] if j>1 else "cold"
            absolute = len(items)+1
            items.append(dict(tag=f"{p}J{j}{mode}",process_id=p,ordinal=j,absolute_call=absolute,
                              mode=mode,prior_mode=previous,transition=("cold" if j==1 else "repeat" if mode==previous else "switch"),
                              first_or_resident="first" if j==1 else "later",odd_even="odd" if j%2 else "even",
                              absolute_odd_even="odd" if absolute%2 else "even",stream=None))
    return items


def process_binding(ref,p,plan,expected,folder,slots):
    binding = read(folder/"binding.json")
    cold = read(folder/"cold.json")
    tags = [s["tag"] for s in slots]
    check(plan["packet"]=="WP-0025" and plan["process_id"]==p and plan["process_ordinal"]==int(p[1])
          and Path(plan["output"])==HOST/"review/runs"/p.lower(), "Released process or output")
    check(plan["prompt"]==ref.history["S"]["prompt"] and plan["prompt_token_ids"]==ref.history["S"]["prompt_ids"]
          and plan["model_revision"]==ref.plan["model_revision"] and plan["module_sha256"]==ref.plan["module_sha256"]
          and plan["tokenizer_sha256"]==PIN["tokenizer"] and plan["prompt_sha256"]==digest(packed(plan["prompt_token_ids"])),
          "Shared prompt/model/tokenizer")
    for slot,call in zip(slots,plan["calls"],strict=True):
        check(all(slot[k]==call[k] for k in ("tag","ordinal","mode")) and call["pages"]==ref.pages and
              call["hooked"] is (slot["mode"]=="H") and call["retain_hidden"]==call["hooked"],"Released call identity")
    check(all(plan[k]==binding[k] for k in ("packet","process_id","process_ordinal","candidate","model_revision",
              "module_sha256","tokenizer_sha256","prompt_sha256","prompt","settings")) and
          all(plan["environment"][k]==v for k,v in binding["environment"].items())
          and binding["order"]==tags and binding["pages"]==ref.pages and binding["plan_sha256"]==expected
          and binding["sensor_candidate"]==ref.plan["candidate"], "Before-load plan binding")
    same_identity(cold,binding)
    check(cold["loads"]==1 and cold["start_utc_ns"]<=cold["ready_utc_ns"] and
          cold["model"]["model_revision"]==plan["model_revision"] and cold["model"]["target_dtype"]=="torch.bfloat16",
          "Cold resident model receipt")
    return binding,cold


def read_slot(ref,folder,slot,plan,binding,previous_time):
    tag,mode = slot["tag"],slot["mode"]
    d = folder/tag
    begin = read(folder/(tag+"-begin.json"))
    receipt = read(d/"receipt.json")
    for row in (begin,receipt):
        same_identity(row,binding)
        check(all(row[k]==slot[k] for k in ("tag","ordinal","mode")), "Slot tag/ordinal/mode")
    check(receipt["verified"] is True and previous_time<=begin["utc_ns"]<=receipt["utc_ns"]
          and begin["monotonic_ns"]<=receipt["monotonic_ns"], "Unverified or out-of-order slot")
    files = BASE_FILES | (H_FILES if mode=="H" else set())
    check(set(receipt["artifacts"])==files and {f.name for f in d.iterdir()}==files|{"receipt.json"}, "Artifact set")
    for name, sha in receipt["artifacts"].items():
        checked_file(d/name,sha)
    sample = ref.decode(read(d/"native.json"),read(d/"metadata.json"))
    duration = read(d/"duration.json")
    ids = sample["ids"]
    check(sample["prompt"]==plan["prompt"] and sample["prompt_ids"]==plan["prompt_token_ids"], "Run prompt")
    check(ids_bytes(ids)==(d/"through-eos.u32le").read_bytes() and sample["sha256"]==receipt["through_eos_sha256"]
          and len(ids)==receipt["through_eos_length"], "Through-EOS bytes")
    n = len(ids)-1
    t = sample["terminal"]
    check(t["max_length"]==plan["settings"]["max_length"] and t["max_new_tokens"]==plan["settings"]["max_new_tokens"]
          and t["guard"]==dict(scanned=n,marker_cum=3,page_len=ids[:-1][::-1].index(ids[0]))
          and ids[0]==ref.history["S"]["ids"][0] and ids.count(ids[0])==3, "Processed stop guard")
    check(duration["emitted"]==n and duration["eos"]==ids[-1] and duration["token_sha256"]==digest(packed(ids[:-1]))
          and duration["metadata_sha256"]==receipt["artifacts"]["metadata.json"] and duration["prompt_sha256"]==plan["prompt_sha256"]
          and duration["spans"]==len(sample["spans"]), "Capture duration binding")
    check(begin["utc_ns"]<=duration["start_utc_ns"]<=duration["end_inference_utc_ns"]<=duration["end_capture_utc_ns"]
          <=receipt["utc_ns"],"Call wall times")
    if mode=="H":
        sample["hidden"] = reconstruct_pool(d,sample,duration)
    else:
        check(duration["capture"] is None,"Unobserved stock hidden trace")
    slot.update(stream=sample["sha256"],timing_ns={k:duration[k] for k in ("start_utc_ns","end_inference_utc_ns",
                "end_capture_utc_ns","wall_inference_ns","complete_window_wall_ns")},receipt_sha256=digest((d/"receipt.json").read_bytes()),
                through_eos_length=len(ids),stop=sample["stop"],terminal=sample["terminal"],witnesses=sample["witnesses"],
                hidden=sample["hidden"]["summary"] if mode=="H" else "unobserved_stock",verified=True)
    return sample,receipt["utc_ns"]


def examine_process(ref,p,plan_path,plan_digest,runs,lease,slots,samples,issues):
    folder = runs/p.lower()/"sensor"
    result = {"expected_plan_sha256":plan_digest}
    try:
        plan = json.loads(checked_file(plan_path,plan_digest))
        binding,cold = process_binding(ref,p,plan,plan_digest,folder,slots)
    except ERRORS as e:
        issues.append(f"{p} plan/binding/cold: {e}")
        return result
    result.update(candidate=plan["candidate"],pid=binding["pid"],process_create_filetime=binding["process_create_filetime"],
                  ready_utc_ns=cold["ready_utc_ns"],load_start_utc_ns=cold["start_utc_ns"],load_count=cold["loads"])
    previous = cold["ready_utc_ns"]
    for slot in slots:
        tag=slot["tag"]
        try:
            samples[tag],previous = read_slot(ref,folder,slot,plan,binding,previous)
        except ERRORS as e:
            slot["error"] = str(e)
            try:
                raw = read(folder/tag/"native.json")
                slot["unverified_stop_observation"] = {
                    k: raw.get(k) for k in ("finish_reason","stop_cause","eos_id","eos_observed","terminal_observation")}
            except ERRORS:
                slot["unverified_stop_observation"] = None
            issues.append(f"{tag}: {e}")
            # Later slots cannot be attributed after a missing receipt in this prefix.
            break
    try:
        tags = [s["tag"] for s in slots]
        outcome = read(folder/"outcome.json")
        same_identity(outcome,binding)
        check(outcome["status"]=="complete" and outcome["verified_tags"]==outcome["started_tags"]==tags and
              not (folder/"error.json").exists() and previous<=outcome["utc_ns"],"Incomplete worker return")
        proc = read(folder.parent/"process.json")
        segment, = proc["segments"]
        check(proc["all_segments_completed"] is True and segment["returncode"]==0 and segment["plan_sha256"]==plan_digest
              and segment["start_utc_ns"]<=cold["start_utc_ns"]<=outcome["utc_ns"]<=segment["end_utc_ns"],
              "Supervisor return")
        name = p.lower()
        issued,returned = [read(lease/(name+"-"+suffix+".json")) for suffix in ("issued","returned")]
        check(issued["admission"]["device"]["free_mib"]>=12000 and issued["admission"]["ollama_models"]==0
              and returned["exit"]==0 and returned["guard"] is None and Path(returned["output"])==Path(plan["output"])
              and issued["argv"][-1]==plan_digest, "Lease admission or return")
        result.update(complete_return=True,end_utc_ns=segment["end_utc_ns"],start_utc_ns=segment["start_utc_ns"])
    except ERRORS as e:
        result.update(complete_return=False)
        issues.append(f"{p} outcome/supervisor/guard: {e}")
    return result


def assemble(ref,slots,samples,processes,issues):
    tags = [s["tag"] for s in slots]
    audit,streams = {},{}
    def details(a,b):
        pair = f"{a['sha256']}>{b['sha256']}"
        if pair not in audit:
            audit[pair] = compare_streams(a,b,ref)
        return pair
    for r in (*ref.history.values(),*samples.values()):
        streams[r["sha256"]] = dict(through_eos_ids=r["ids"],raw=r["raw"],pages=r["pages"],spans=r["spans"])
    pairs,hh,historical = [],{},[]
    E = [[None]*8 for _ in range(8)]
    K = [[None]*8 for _ in range(8)]
    for i,tag in enumerate(tags):
        if tag in samples:
            E[i][i],K[i][i] = True,"+infinity"
        for m,hist in ref.history.items():
            k = details(samples[tag],hist) if tag in samples else None
            historical.append(dict(tag=tag,historical_mode=m,detail=k,equal=audit[k]["through_eos_equal"] if k else None,
                                   first_divergence=audit[k]["first_shared_prefix_divergence"] if k else None))
    for i,j in combinations(range(8),2):
        a,b = tags[i],tags[j]
        kind = "".join(sorted([a[-1],b[-1]],reverse=True))
        row = dict(left=a,right=b,kind=kind,same_process=a[:2]==b[:2],same_call_ordinal=a[3]==b[3],
                   absolute_call_gap=j-i,detail=None,equal=None,first_divergence=None,mode_oriented_signature=None)
        if a in samples and b in samples:
            x,y = samples[a],samples[b]
            k = details(x,y)
            d = audit[k]
            E[i][j]=E[j][i]=d["through_eos_equal"]
            K[i][j]=K[j][i]=d["first_shared_prefix_divergence"]
            row.update(detail=k,equal=E[i][j],first_divergence=K[i][j])
            if kind=="SH":
                left,right = (x,y) if a[-1]=="S" else (y,x)
                row["mode_oriented_signature"]=signature(left["ids"],right["ids"],ref.history)
            if kind=="HH":
                hh[a+":"+b] = compare_hidden(x,y)
        elif kind=="HH":
            hh[a+":"+b] = None
        pairs.append(row)
    unique = {m:{s["stream"] for s in slots if s["mode"]==m and s["stream"]} for m in "SH"}
    if issues or len(samples)<8:
        disposition="incomplete"
    elif len(unique["S"])>1:
        disposition="stock_within_mode_variation"
    elif len(unique["H"])>1:
        disposition="hooked_within_mode_variation_with_stable_stock"
    elif unique["S"]!=unique["H"]:
        disposition="mode_associated_difference_under_both_orders"
    else:
        disposition="historical_mismatch_not_reproduced"
    strata=defaultdict(Counter)
    for row in pairs:
        strata[row["kind"]][{True:"equal",False:"differ",None:"undefined"}[row["equal"]]]+=1
    for s in slots:
        s.setdefault("verified",False)
        s.setdefault("hidden","unobserved_stock" if s["mode"]=="S" else "undefined")
    return dict(schema="WP-0025-analysis-v1",disposition=disposition,issues=issues,processes=processes,
                physical_source=dict(binder="34054347f091c087a39efe17",window=1,pages=ref.pages,
                                     pdf_sha256=ref.plan["requests"][0]["sha256"],
                                     applicable_pdf_witnesses=ref.witnesses),reference_pins=PIN,
                historical_stream_sha256={k:v["sha256"] for k,v in ref.history.items()},
                historical_signature_zero_based=SIGNATURE,historical_detail=details(*ref.history.values()),
                slots=slots,tags_in_matrix_order=tags,through_eos_equal=E,first_shared_prefix_divergence=K,
                unique_pairs_reusing_eight_slots=dict(count=28,by_mode=dict(strata)),pairs=pairs,
                historical_comparisons=historical,signature_counts_stock_to_hook=dict(Counter(
                    r["mode_oriented_signature"]["classification"] for r in pairs if r["mode_oriented_signature"])),
                order_profile=order_profile(slots),streams=streams,stream_pair_details=audit,hidden_pairs=hh,
                flags=dict(semantic_changes_on_verified_comparisons=any(d["page_block_table_cell_changes"] for d in audit.values()),
                           witness_binding_failure=[(s["tag"],w["kind"]) for s in slots for w in s.get("witnesses",[]) if not w["unique"]],
                           stop_changes_on_verified_comparisons=any(d["stop_changes"] for d in audit.values()),
                           unverified_stop_evidence={s["tag"]:s["unverified_stop_observation"] for s in slots
                                                     if "unverified_stop_observation" in s},
                           undefined_slots=[s["tag"] for s in slots if not s["verified"]]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_dir",type=Path)
    parser.add_argument("p1_sha256")
    parser.add_argument("p2_sha256")
    parser.add_argument("output",type=Path)
    parser.add_argument("--runs",type=Path,default=HOST/"review/runs")
    parser.add_argument("--lease",type=Path,default=HOST/"coordination/leases/window-repeat-r1")
    parser.add_argument("--external-issue",action="append",default=[],help="Independent binding/resource issue (forces incomplete)")
    args=parser.parse_args()
    check(sys.flags.isolated and sys.dont_write_bytecode and os.environ.get("CUDA_VISIBLE_DEVICES")=="-1",
          "Run CPU analysis with -I -B and CUDA_VISIBLE_DEVICES=-1")
    slots=schedule()
    ref=Reference()
    issues,samples,processes=args.external_issue.copy(),{},{}
    for p,sha in zip(ORDERS,(args.p1_sha256,args.p2_sha256),strict=True):
        processes[p]=examine_process(ref,p,args.plan_dir/(p.lower()+"-plan.json"),sha,args.runs,args.lease,
                                     [s for s in slots if s["process_id"]==p],samples,issues)
    try:
        a,b=processes.values()
        check((a["pid"],a["process_create_filetime"])!=(b["pid"],b["process_create_filetime"]) and
              a["candidate"]==b["candidate"] and a["end_utc_ns"]<=b["start_utc_ns"], "Sequential cold processes")
        acquired,ret=[read(args.lease/f) for f in ("acquired.json","returned.json")]
        check(acquired["pid"]==ret["retiring_pid"] and acquired["release_sha256"]==ret["release_sha256"]
              and ret["error"] is None, "Single released lease return")
    except ERRORS as e:
        issues.append(f"Experiment return: {e}")
    result=assemble(ref,slots,samples,processes,issues)
    output=(json.dumps(result,allow_nan=False,ensure_ascii=False,sort_keys=False,separators=(",",":"))+"\n").encode()
    with args.output.open("xb") as f:
        f.write(output)
    print(json.dumps(dict(disposition=result["disposition"],issues=issues,verified=len(samples),sha256=digest(output))))


if __name__=="__main__":
    main()

