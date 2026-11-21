"""Retain every H0 cell after a failure, with real token differences, pools and PDF witnesses."""
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from h0_audit import EXPECTED, PLAN_REVISION, PLAN, WITNESS, align
from span_audit import snapshot, T


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def token_digest(ids):
    return sha(b"".join(i.to_bytes(4,"little") for i in ids))


def change(a,b):
    left=a["token_ids"]+[a["eos_id"]]
    right=b["token_ids"]+[b["eos_id"]]
    edits=[]
    for op,i,j,k,l in SequenceMatcher(None,left,right,autojunk=False).get_opcodes():
        if op=="equal":
            continue
        edits.append(dict(op=op,stock_index=[i,j],hook_index=[k,l],stock_ids=left[i:j],hook_ids=right[k:l],
                          stock_text=T.decode(left[i:j],skip_special_tokens=False),
                          hook_text=T.decode(right[k:l],skip_special_tokens=False),
                          stock_prefix_tail=T.decode(left[max(0,i-15):i],skip_special_tokens=False),
                          hook_prefix_tail=T.decode(right[max(0,k-15):k],skip_special_tokens=False)))
    return edits


def main():
    raw_plan=subprocess.check_output(["git","show",PLAN_REVISION+":"+PLAN])
    assert sha(raw_plan)==EXPECTED
    plan=json.loads(raw_plan)
    sensor=Path(plan["output"])/"sensor"
    assert read(sensor/"binding.json")["plan_sha256"]==EXPECTED
    calls={c["tag"]:c for c in plan["calls"]}
    assert len(calls)==16 and len(plan["check_groups"])==8
    samples={}
    for name,c in calls.items():
        try:
            samples[name]=snapshot(sensor/name)|{"independent_check":"pass"}
        except Exception as e:
            samples[name]={"independent_check":"failure","exception":f"{type(e).__name__}: {e}"}
    input_map={}
    comparisons=[]
    for group in plan["check_groups"]:
        left,right=group["left"],group["right"]
        la,lb=calls[left],calls[right]
        assert not la["hooked"] and lb["hooked"] and lb["retain_hidden"]
        assert la["pages"]==lb["pages"] and la["binder"]==lb["binder"] and la["window"]==lb["window"]
        a,b=[read(sensor/name/"native.json") for name in (left,right)]
        ma,mb=[read(sensor/name/"metadata.json") for name in (left,right)]
        edits=change(a,b)
        fields=("prompt","prompt_token_ids","token_ids","text","finish_reason","stop_cause","eos_observed",
                "eos_id","terminal_observation","expected_pages","num_pages_out")
        differences=[k for k in fields if a[k]!=b[k]]
        digests=[token_digest(r["token_ids"]+[r["eos_id"]]) for r in (a,b)]
        comp=dict(stock=left,hooked=right,through_eos_sha256=digests,through_eos_equal=not edits,
                  pre_eos_lengths=[len(a["token_ids"]),len(b["token_ids"])],native_differences=differences,
                  parsed_texts_equal=[x["text"]==y["text"] for x,y in zip(ma["pages"],mb["pages"],strict=True)],
                  parsed_rows_equal=[([t["rows"] for t in x["tables"]]==[t["rows"] for t in y["tables"]])
                                     for x,y in zip(ma["pages"],mb["pages"],strict=True)],source_metadata_equal=ma==mb,
                  edits=edits)
        if comp["pre_eos_lengths"][0]==comp["pre_eos_lengths"][1]:
            comp["different_preeos_positions"]=[i for i,(x,y) in enumerate(zip(a["token_ids"],b["token_ids"])) if x!=y]
        comparisons.append(comp)
        input_map[la["binder"],la["window"]]=(left,right)
    witness_raw=subprocess.check_output(["git","show",plan["candidate"]+":"+WITNESS])
    assert sha(witness_raw)=="dfb55b56833599f111eb29e2b3d4b8a7de9eab13b8caae277e09c9ba60271989"
    witness=json.loads(witness_raw)
    alignments=[]
    for item in witness["witnesses"]:
        binder=item["binder"]
        pdf=next(Path(r["pdf"]) for r in plan["requests"] if Path(r["pdf"]).stem==binder)
        assert sha(pdf.read_bytes())==witness["documents"][binder]
        tags=input_map[binder,item["window"]]
        pair={}
        for role,tag in zip(("stock","hooked"),tags,strict=True):
            meta=read(sensor/tag/"metadata.json")
            evidence=align(item,meta,pdf)
            if not evidence["unique_literal_and_geometry"]:
                evidence["all_native_page_spans"]=[r for r in meta["spans"] if r["page"]==item["window_page"]]
            pair[role]=evidence
        alignments.append(pair)
    yes=sum(r["through_eos_equal"] for r in comparisons)
    pooled=sum(v.get("pooled_bit_exact",0) for v in samples.values())
    hooked_positions=sum(v.get("positions",0) for v in samples.values())
    alignment_counts={r:sum(a[r]["unique_literal_and_geometry"] for a in alignments) for r in ("stock","hooked")}
    return dict(source=plan["candidate"],model_revision=plan["model_revision"],plan_sha256=EXPECTED,
                witness_sha256=sha(witness_raw),samples=samples,comparisons=comparisons,alignments=alignments,
                total_hooked_postconsumption_positions=hooked_positions,total_bit_exact_pools=pooled,
                source_witness_uniques=alignment_counts,token_equal_comparisons=yes,token_unequal_comparisons=8-yes,
                all_sample_internals_pass=all(r["independent_check"]=="pass" for r in samples.values()),
                gate="FAIL" if yes<8 else "REVIEW_SOURCE_ALIGNMENT")


if __name__=="__main__":
    assert sys.flags.isolated and sys.dont_write_bytecode
    print(json.dumps(main(),indent=2))

