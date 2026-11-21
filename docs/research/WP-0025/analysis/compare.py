"""Stream, box, table, row and feature comparisons. All indices are zero-based unless labeled."""
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from itertools import zip_longest
import re

import numpy as np

from evidence import SIGNATURE


def divergence(a,b):
    for i,(x,y) in enumerate(zip_longest(a,b,fillvalue="end_of_stream")):
        if x!=y:
            return i,x,y
    return "+infinity",None,None


def signature(a,b,reference):
    stock,hook = [reference[m]["ids"] for m in "SH"]
    if a==stock and b==hook:
        return dict(classification="original_stock_to_hook",forward_indices=list(SIGNATURE),reverse_indices=[])
    if a==hook and b==stock:
        return dict(classification="reverse_original_pair",forward_indices=[],reverse_indices=list(SIGNATURE))
    directions = [[],[]]
    for i,expected in SIGNATURE.items():
        if min(len(a),len(b))>i:
            for matched,values in zip(directions,(expected,expected[::-1])):
                if (a[i],b[i])==values:
                    matched.append(i)
    forward, reverse = directions
    if a==b:
        label = "same_final_stream"
    elif len(forward)==4 or len(reverse)==4:
        label = "four_index_transitions_on_other_streams"
    else:
        label = "partial_original_transitions" if forward or reverse else "no_original_transitions"
    return dict(classification=label,forward_indices=forward,reverse_indices=reverse)


def structure_changes(a,b,path=()):
    if a==b:
        return []
    if isinstance(a,list) and isinstance(b,list):
        return [diff for i,(x,y) in enumerate(zip_longest(a,b)) for diff in structure_changes(x,y,(*path,i))]
    if isinstance(a,dict) and isinstance(b,dict):
        return [diff for k in sorted(a.keys()|b.keys()) for diff in structure_changes(a.get(k),b.get(k),(*path,k))]
    return [dict(path=list(path),left=a,right=b)]


def projection(r):
    return [dict(page=i+1,text=p["text"],blocks=[v["text"] for v in p["spans"]],
                 tables=[t["rows"] for t in p["tables"]]) for i,p in enumerate(r["pages"])]


HEAD = re.compile(r"<BLOCK>([^\[]+?)\s*\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]<FORK>")


def headers(raw):
    pages = []
    for page in raw.split("<PAGE>")[1:]:
        heads = list(HEAD.finditer(page))
        rows = []
        for i,m in enumerate(heads):
            stop = heads[i+1].start() if i+1<len(heads) else len(page)
            rows.append(dict(kind=m[1],literal=page[m.end():stop].strip(),bbox999=list(map(int,m.groups()[1:]))))
        pages.append(rows)
    return pages


def box_changes(a,b):
    output = []
    for p,(left,right) in enumerate(zip(headers(a["raw"]),headers(b["raw"]),strict=True),1):
        # Physical page then block ordinal. Record full unmatched entries and flag identity changes.
        for j,(x,y) in enumerate(zip_longest(left,right)):
            if x==y or (x and y and x["bbox999"]==y["bbox999"]):
                continue
            delta = [v-u for u,v in zip(x["bbox999"],y["bbox999"])] if x and y else None
            output.append(dict(page=p,block_index=j,left=x,right=y,delta_right_minus_left_999=delta,
                               same_kind_and_literal=bool(x and y and x["kind"]==y["kind"] and x["literal"]==y["literal"])))
    return output


def compare_streams(a,b,ref):
    aa,bb = a["ids"],b["ids"]
    k,x,y = divergence(aa,bb)
    edits = []
    for op, i,j,u,v in SequenceMatcher(None,aa,bb,autojunk=False).get_opcodes():
        if op!="equal":
            left,right=aa[i:j],bb[u:v]
            edits.append(dict(op=op,left_range=[i,j],right_range=[u,v],left_ids=left,right_ids=right,
                              left_literal=ref.tokenizer.decode(left,skip_special_tokens=False),
                              right_literal=ref.tokenizer.decode(right,skip_special_tokens=False)))
    raw_edits = [dict(left_range=[i,j],right_range=[u,v],left=a["raw"][i:j],right=b["raw"][u:v])
                 for op,i,j,u,v in SequenceMatcher(None,a["raw"],b["raw"],autojunk=False).get_opcodes() if op!="equal"]
    semantic = structure_changes(projection(a),projection(b))
    return dict(through_eos_equal=aa==bb,first_shared_prefix_divergence=k,first_decisions=[x,y],
                exact_positional_differences=[i for i,(s,t) in enumerate(zip_longest(aa,bb)) if s!=t],
                edits=edits,raw_literal_edits=raw_edits,page_block_table_cell_changes=semantic,
                source_box_changes=box_changes(a,b),stop_changes=structure_changes(a["stop"],b["stop"]),
                terminal_event_changes=structure_changes(a["terminal"],b["terminal"]),
                signature=signature(aa,bb,ref.history))


def span_key(span):
    return (span["page"],span["kind"],span["block_kind"],span["text"],tuple(span["cells"]))


def comparable_spans(a,b):
    # Separate repeated equal printed spans by their occurrence number on this page and kind.
    def locate(spans):
        counts = Counter()
        by_id = {}
        for s in spans:
            key = span_key(s)
            by_id[s["index"]] = (*key, counts[key])
            counts[key] += 1
        return by_id
    return locate(a["spans"]),locate(b["spans"])


def vector_difference(a,b,bits_a,bits_b):
    different = bits_a!=bits_b
    return [int(np.count_nonzero(different)),float(np.max(np.abs(np.subtract(a,b,dtype=np.float32))))]


def summarize_vectors(rows):
    if not rows:
        return dict(count=0,first_differing=None,max_abs_f32=None,bit_equal=None)
    first = next((r[0] for r in rows if r[-2]),None)
    return dict(count=len(rows),first_differing=first,max_abs_f32=max(r[-1] for r in rows),bit_equal=first is None)


def compare_hidden(a,b):
    ha,hb = a["hidden"],b["hidden"]
    ia,ib = a["ids"][:-1],b["ids"][:-1]
    keys_a,keys_b = comparable_spans(a,b)
    kb = {key:i for i,key in keys_b.items()}
    pa,pb = len(a["prompt_ids"]),len(b["prompt_ids"])
    first = divergence(a["ids"],b["ids"])[0]
    prefix = len(ia) if first=="+infinity" else first
    rows, shared, later, excluded = [],[],[],[]
    aligned = set()
    for i in range(len(ia)):
        j = pa+i-pb
        if not 0<=j<len(ib) or ia[i]!=ib[j]:
            excluded.append([i,"no_identical_token_at_absolute_position"])
            continue
        ma = [keys_a[k] for k in ha["membership"][i]]
        mb = [keys_b[k] for k in hb["membership"][j]]
        if ma!=mb:
            excluded.append([i,"span_memberships_differ"])
            continue
        aligned.add(i)
        diff = vector_difference(ha["states"][i],hb["states"][j],ha["bits"][i],hb["bits"][j])
        row = [i,j,pa+i,ia[i],ha["membership"][i],hb["membership"][j],*diff]
        rows.append(row)
        (shared if i==j and i<prefix else later).append(row)
    pools, prefix_pools, later_pools,excluded_pools = [],[],[],[]
    for i,key in keys_a.items():
        j = kb.get(key)
        indices = a["spans"][i]["token_indices"]
        member_pos = [pa+k for k in indices]
        if (j is None or any(k not in aligned for k in indices) or
                member_pos != [pb+k for k in b["spans"][j]["token_indices"]]):
            excluded_pools.append(i)
            continue
        left,right = ha["pools"][i],hb["pools"][j]
        diff = vector_difference(left,right,left.view("<u4"),right.view("<u4"))
        row = [i,j,member_pos,*diff]
        pools.append(row)
        (prefix_pools if all(k<prefix for k in indices) and pa==pb else later_pools).append(row)
    return dict(first_output_divergence=first,left_rows=len(ia),right_rows=len(ib),
                hidden=summarize_vectors(rows),hidden_shared_prefix=summarize_vectors(shared),
                hidden_matched_after_divergence=summarize_vectors(later),
                hidden_row_fields=["left_row","right_row","absolute_position","token_id","left_span_indices",
                                   "right_span_indices","different_BF16_components","max_abs_f32"],
                hidden_row_differences=rows,excluded_left_rows=excluded,unmatched_right_rows=len(ib)-len(rows),
                left_spans=len(keys_a),right_spans=len(keys_b),pooled=summarize_vectors(pools),
                pooled_shared_prefix=summarize_vectors(prefix_pools),pooled_with_any_later_row=summarize_vectors(later_pools),
                pool_row_fields=["left_span","right_span","absolute_members","different_F32_components","max_abs_f32"],
                pool_differences=pools,excluded_left_spans=excluded_pools,unmatched_right_spans=len(keys_b)-len(pools))


def order_profile(schedule):
    strata = {}
    for key in ("mode","process_id","ordinal","absolute_call","prior_mode","transition","odd_even",
                "absolute_odd_even","first_or_resident"):
        groups = defaultdict(list)
        for slot in schedule:
            groups[str(slot[key])].append([slot["tag"],slot["stream"]])
        strata[key] = {k:dict(tag_stream=v,distinct_verified_streams=sorted({s for _,s in v if s}))
                       for k,v in groups.items()}
    return strata
