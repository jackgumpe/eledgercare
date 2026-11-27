"""Summarize real retained branch, CPU/CUDA fence, typed graph and cache-prefix facts."""
from collections import Counter
import json
import math
from pathlib import Path
import sys

PHASES=("C0_raw","C1_post_rep","C2_post_page")
CHAIN=("model_producer","page_before","page_after","B","block_exit","head_producer","C0_raw","rep_producer",
       "rep_entry","rep_return","C1_post_rep","page_producer","page_entry","page_return","C2_post_page","choice_consumer","D")


class Graph:
    def __init__(self,data):
        self.nodes=data["nodes"]
        self.root=self.mapping(data["root"])

    def val(self,ref):
        return self.nodes[ref["ref"]]

    def mapping(self,ref):
        return dict(self.val(ref)["entries"])


def leaf(v,g):
    if not isinstance(v,dict) or "ref" not in v:
        return {"primitive":v}
    o=g.val(v)
    return {k:o[k] for k in ("type","dtype","shape","unobserved") if k in o}


def compare_cache(old,new,stream):
    results=Counter()
    for key,curr in new.items():
        prev=old[key]
        if prev["shape"]==curr["shape"]:
            results["unchanged_slots"]+=1
            if (prev["sha256"],prev["oid"],prev["storage_base"])!=(curr["sha256"],curr["oid"],curr["storage_base"]):
                results["changed_in_place"]+=1
            continue
        results["grown_slots"]+=1
        heads=math.prod(prev["shape"][:-2])
        prev_len=prev["bytes"]//heads
        curr_len=curr["bytes"]//heads
        for h in range(heads):
            stream.seek(prev["start"]+h*prev_len)
            left=stream.read(prev_len)
            stream.seek(curr["start"]+h*curr_len)
            if left!=stream.read(prev_len):
                results["old_prefix_difference"]+=1
            results["compared_prefix_bytes"]+=prev_len
        if prev["oid"]==curr["oid"]:
            results["same_numeric_oid_after_growth"]+=1
        if prev["storage_base"]==curr["storage_base"]:
            results["same_address_after_growth"]+=1
    return dict(results)


def main(root):
    source=root/"observed"
    rows={k:{} for k in range(5)}
    globals={}
    path={}
    for line in (source/"observations.jsonl").open("rb"):
        x=json.loads(line)
        tag=x["tag"]
        if tag=="layer_path":
            path.setdefault(x["row"],[]).append(x["data"])
        elif x["row"] in rows:
            rows[x["row"]][tag]=x
        elif tag in ("terminal_eos","cleanup"):
            globals[tag]=x
    outcomes=[]
    prev=None
    with (source/"tensors.bin").open("rb") as stream:
        for k,row in rows.items():
            f=lambda t:row[t]["data"]
            sites={tag:row[tag]["journal_seq"] for tag in CHAIN}
            s={"row":k,"strict_branch_order":list(sites.values())==sorted(set(sites.values())),
               "sequence":sites,"page_state_entry":f("page_entry")["cursor"],"page_state_return":f("page_return")["cursor"],
               "banned":f("rep_return").get("banned"),
               "callee_same_source":[f(t)["source"]==f(t.replace("return","entry"))["source"]==f(t)["returned_object"] for t in ("rep_return","page_return")],
               "prefill_path":sorted([d["layer"],d["site"],d["q_len"]] for d in path[None]),
               "decode_path":sorted([d["layer"],d["site"],d["q_len"]] for d in path[k]),"cuts":{},"graphs":{},"active_locals":{}}
            for i,t in enumerate(PHASES):
                d=f(t)["event"]
                s["cuts"][t]={n:d.get(n) for n in ("instruction","seq","bytes","run","api","copy_stream","producer_stream","pinned",
                                                    "completion","complete_before_return","byte_runs","source_shape","source_strides")}
                nxt=f(("rep_producer","page_producer","choice_consumer")[i])
                s["cuts"][t]["same_source_at_next"]=nxt.get("previous_source")==d.get("source")
                s["cuts"][t]["next_names_this_copy"]=nxt.get("previous_copy")==d.get("id")
                s["cuts"][t]["next_observed_complete"]=nxt.get("preceding_copy_complete")
            for t in ("B","D"):
                g=Graph(f(t)["graph"])
                cache=g.val(g.root["cache"])
                fs=g.mapping(cache["fields"])
                cards={}
                slots={}
                for name in ("key_cache","value_cache","_dash_idx_k"):
                    group=([v for _,v in sorted(g.mapping(fs[name]).items())] if name=="_dash_idx_k" else g.val(fs[name])["items"])
                    vals=[g.val(ref) for ref in group]
                    cards[name]=[n["shape"][-2] for n in vals]
                    slots.update({(name,j):n for j,n in enumerate(vals)})
                z={"cache_slot_names":cache["actual_keys"],"cache_is_generator_cache":g.root["cache"]==g.root["generator_cache"],
                   "cache_lengths":cards,"unobserved_nodes":dict(Counter(n["unobserved"] for n in g.nodes if "unobserved" in n)),
                   "lower_forwarded":f(t).get("lower_forwarded"),"caller_offset":f(t).get("caller_offset")}
                if prev is not None:
                    z["cache_transition"]=compare_cache(prev,slots,stream)
                s["graphs"][t]=z
                prev=slots
            for t,x in row.items():
                data=x["data"]
                if "nodes" in data and "root" in data:
                    g=Graph(data)
                    s["active_locals"][t]={n:leaf(v,g) for n,v in g.root.items()}
            outcomes.append(s)
    a,b=(globals[t]["data"] for t in ("terminal_eos","cleanup"))
    terminal={t:{"cache_len":x["data"]["length"],"ids":len(x["data"]["ids"]),"nxt":x["data"]["nxt"],
                 "finish":x["data"]["finish"],"dash_on":x["data"]["dash_on"]} for t,x in globals.items()}
    terminal["checks"]={"pre_before_cleanup":globals["terminal_eos"]["journal_seq"]<globals["cleanup"]["journal_seq"],
               "same_ids":a["ids"]==b["ids"],"return_router_modes_restored":b["router_stage0"]==a["saved_stage0"],
               "retained_params_equal":a["retained_params"]==b["retained_params"],"page_scope_restored":b["page_scope"]==a["saved_page_scope"],
               "saved_window_restored":[b["ring"],b["sliding"]]==a["saved_cfg"],"terminal_streamer_empty":b["streamer_state"].get("token_cache")==[]}
    print(json.dumps({"rows":outcomes,"terminal":terminal},indent=2))


if __name__=="__main__":
    main(Path(sys.argv[1]))
