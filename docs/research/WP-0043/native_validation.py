"""Source-qualified obligations for native payload and resource evidence."""
import hashlib
import math
import struct
from transfer import spans
from capture import PHASES
from native import ACTIVE_RUNTIME,ARM,LABELS,LIMITS,MODEL,OUT,PYTHON,SCHEME,UUID,BASE,blob,plan
import json

TENSOR_KEYS=frozenset("type oid dtype shape strides device storage_offset storage_base storage_bytes element_size bytes start sha256 chunks transfer".split())
NULLABLE={"self_attn_weights","kl_loss","cand","allow","block_cand","coords"}
SCALARS={"pg_id","bs","nblk","K","M","q_len"}
CONTAINERS={"p","st","idx_pe","tokens_per_expert"}
PRE=("head_producer","rep_producer","page_producer")
POST=("rep_producer","page_producer","choice_consumer")


def require(obj,field,row,phase,f):
    if not isinstance(obj,dict) or field not in obj:
        f.absent(row,phase,"required_field_missing",field=field)
        return False
    return True


def transfer_map(n,capacity):
    used=copies=0
    stamp=hashlib.sha256()
    receipts=[]
    for offset,length in spans(n["shape"],n["strides"],n["element_size"],n["storage_offset"],n["storage_bytes"],65536):
        while length:
            piece=min(length,capacity-used)
            stamp.update(struct.pack("<QQQ",offset,used,piece))
            used+=piece
            copies+=1
            offset+=piece
            length-=piece
            if used==capacity:
                receipts.append((used,copies,stamp.hexdigest()))
                used=copies=0
                stamp=hashlib.sha256()
    if used or not receipts:
        receipts.append((used,copies,stamp.hexdigest()))
    return receipts


def transfer_contract(n,chunks,row,tag,f):
    expected=transfer_map(n,LIMITS["pinned_host_pool"])
    if len(chunks)!=len(expected):
        f.mismatch(row,tag,"transfer_chunk_count",expected=len(expected),observed=len(chunks))
    for rec,(length,count,sha) in zip(chunks,expected):
        for k,v in {"bytes":length,"byte_runs":count,"address_map_sha256":sha,"pinned":True,
                    "source_storage":n["storage_base"],"source_shape":n["shape"],"source_strides":n["strides"],
                    "element_size":n["element_size"],"source_offset":n["storage_offset"],"allocation_bytes":n["storage_bytes"],
                    "completion":True,"complete_before_return":True,"copy_stream":0,
                    "api":"cudaMemcpyAsync(D2H)" if str(n["device"]).startswith("cuda") else "memmove"}.items():
            f.equal(rec,k,v,row,tag,"transfer_contract")
        for k in ("copy_thread","native_event","fence_serial","dest_storage"):
            if require(rec,k,row,tag,f) and (type(rec[k])!=int or rec[k]<=0):
                f.mismatch(row,tag,"invalid_transfer_identity",field=k)
        before=rec.get("allocator_before",{})
        after=rec.get("allocator_after",{})
        for name in ("allocation.all.allocated","allocated_bytes.all.allocated","reserved_bytes.all.allocated"):
            if require(before,name,row,tag,f):
                f.equal(after,name,before[name],row,tag,"observer_allocator_delta")
        origin=rec.get("producer",{})
        for k in ("site","instruction","frame","receiver","thread","stream","device","ordinal","code_sha256"):
            require(origin,k,row,tag,f)
        if rec.get("copy_thread")!=origin.get("thread") or origin.get("stream")!=rec.get("copy_stream"):
            f.mismatch(row,tag,"source_thread_stream_mismatch")


def local_contract(snap,tag,fields,row,f):
    for name in fields:
        if name not in snap.root:
            f.absent(row,tag,"native_local_missing",field=name)
            continue
        v=snap.root[name]
        if name in SCALARS:
            if type(v)!=int or v<=0:
                f.mismatch(row,tag,"local_scalar_invalid",field=name)
        elif v is None:
            if name not in NULLABLE:
                f.mismatch(row,tag,"null_active_local",field=name)
                f.absent(row,tag,"active_value_missing",field=name)
        elif name in CONTAINERS or name=="coords":
            n=snap.node(v)
            if not any(key in n for key in ("items","entries")):
                f.mismatch(row,tag,"local_container_invalid",field=name)
        else:
            n=snap.node(v)
            if n.get("type") not in ("Tensor","Parameter") or not TENSOR_KEYS.issubset(n):
                f.absent(row,tag,"local_tensor_missing",field=name)
            if name in {"residual","hidden_states","attention_result","final_out","down_proj","final_norm"} and (
                    n.get("shape") not in ([1,1,1280],[1,1280]) or n.get("dtype")!="torch.bfloat16"):
                f.mismatch(row,tag,"hidden_layout",field=name)


def score_events(row,records,lookups,f):
    scopes={k:records.get((row,k),{}) for k in (*PRE,POST[-1],*PHASES)}
    for k,record in scopes.items():
        if not record:
            f.absent(row,k,"score_instruction_missing",site=k)
    for j,p in enumerate(PHASES):
        wrapper=scopes[p]
        rec=wrapper.get("data",{}).get("event",{})
        if not rec:
            continue
        prev=scopes[PRE[j]].get("data",{})
        after=scopes[POST[j]].get("data",{})
        for k in ("frame","receiver","thread","stream","device","ordinal","instruction","site","code_sha256"):
            require(prev,k,row,p,f)
            require(after,k,row,p,f)
        f.equal(rec,"bytes",4*129280,row,p,"score_extent")
        f.equal(rec,"run","native",row,p,"score_run")
        f.equal(rec,"seq",3*row+j+1,row,p,"score_serial")
        if prev:
            f.equal(rec,"producer",prev,row,p,"score_producer_ancestry")
        else:
            f.absent(row,p,"score_producer_missing")
        f.link(rec,"frame",wrapper,"frame",row,p,"frame_binding")
        f.link(rec,"receiver",prev,"receiver",row,p,"receiver_binding")
        f.link(after,"previous_copy",rec,"id",row,p,"next_writer_binding")
        f.link(after,"previous_source",rec,"source",row,p,"next_writer_binding")
        f.equal(after,"preceding_copy_complete",True,row,p,"next_writer_order")
        for stamp,site in ((prev,PRE[j]),(after,POST[j])):
            f.equal(stamp,"site",site,row,p,"producer_site")
            f.equal(stamp,"instruction",lookups[site][1],row,p,"producer_instruction")
            f.equal(stamp,"ordinal",619+row,row,p,"producer_ordinal")
        f.equal(rec,"source_shape",[129280],row,p,"score_layout")
        f.equal(rec,"source_strides",[1],row,p,"score_layout")
        if all(k in rec for k in ("source_shape","source_strides","source_offset","allocation_bytes","source_storage","element_size")):
            n={"shape":rec["source_shape"],"strides":rec["source_strides"],"storage_offset":rec["source_offset"],
               "storage_bytes":rec["allocation_bytes"],"storage_base":rec["source_storage"],"element_size":4,"device":"cuda:0"}
            transfer_contract(n,[rec],row,p,f)
        else:
            f.absent(row,p,"score_address_map_missing")
        nums=[scopes[PRE[j]].get("journal_seq"),wrapper.get("journal_seq"),scopes[POST[j]].get("journal_seq")]
        if all(type(x)==int for x in nums) and not nums[0]<nums[1]<nums[2]:
            f.mismatch(row,p,"producer_copy_consumer_order")


def runtime_receipt(rec,arm,find):
    path_plan=plan()
    for k,want in {"schema":SCHEME,"arm":arm,"uuid":UUID,"eval":True,"training_modules":[],"cuda":"13.0",
                   "torch":"2.13.0+cu130","allocator_limit":LIMITS["allocator_bytes"],
                   "active_runtime":ACTIVE_RUNTIME,"argv":path_plan["worker_argv"][ARM.index(arm)]}.items():
        find.equal(rec,k,want,None,"public_document","runtime_contract")
    for k in ("pid","parent","deterministic","tf32","cudnn_tf32","autocast","device","modules"):
        require(rec,k,None,"public_document",find)
    for name in ("generator","decoder","layer11"):
        receivers=rec.get("receivers",{})
        if require(receivers,name,None,"public_document",find) and type(receivers[name])!=int:
            find.mismatch(None,"public_document","runtime_receiver_invalid",role=name)
    if "modules" not in rec:
        return
    actual={k.rsplit(".",1)[-1]+".py":v for k,v in rec["modules"].items()}
    expected=json.loads(blob(BASE,"docs/research/WP-0041/source.json"))["historical_q0_imported_module_receipt_and_disk"]
    for name,meta in expected.items():
        if name not in actual:
            find.absent(None,"public_document","module_origin_missing",module=name,arm=arm)
            continue
        m=actual[name]
        find.equal(m,"sha256",meta["sha256"],None,"public_document","loaded_module_digest")
        from pathlib import Path
        if not Path(m.get("path","")).is_relative_to(OUT/arm/"modules"):
            find.mismatch(None,"public_document","loaded_module_origin",module=name)




def rooted_state(s,tag,row,contract,pack,f):
    expected={"cache","generator_cache","prompt","history","guard","position","pending","step","finish","streamer",
              "layers","routers","cfg","dash_infer","dash_global","page_scope","config_sparse","ckpt_sparse","saved_cfg"}
    for k in sorted(expected-set(s.root)):
        f.absent(row,tag,"state_root_missing",field=k)
    history=contract["histories"][row]
    if tag=="D":
        history=history+[contract["target_ids"][row]]
    required={"prompt":contract["prompt"],"history":history}
    for key,want in required.items():
        if key in s.root and s.items(s.root[key])!=want:
            f.mismatch(row,tag,"generator_state_mismatch",field=key)
    base=1445+row
    for k,val in (("position",base+(tag=="D")),("pending",history[-1]),("step",618+row+(tag=="D")),("finish","length")):
        f.equal(s.root,k,val,row,tag,"generator_state_mismatch")
    from scorer import canonical_state
    scanned=history[:-1]
    guard=s.as_dict(s.root["guard"])
    for k,want in canonical_state(scanned,128827,True).items():
        f.equal(guard,k,want,row,tag,"guard_counter_mismatch")
    cf=s.as_dict(s.root["cfg"])
    for k in ("_ring_window","sliding_window"):
        f.equal(cf,k,None,row,tag,"decoder_flag")
    f.equal(s.as_dict(s.root["dash_infer"]),"on",True,row,tag,"dash_flag")
    f.equal(s.root,"page_scope",True,row,tag,"page_scope")
    layers=s.items(s.root["layers"])
    routers=s.items(s.root["routers"])
    if len(layers)!=12 or len(routers)!=12:
        f.mismatch(row,tag,"layer_router_cardinality")
    shared={}
    for i,ref in enumerate(layers):
        layer=s.as_dict(ref)
        f.equal(layer,"layer_idx",i,row,tag,"layer_binding")
        for k in ("_sparse_source_input_ids","_dash_dec_allow","_sparse_block_indices_cache"):
            if not require(layer,k,row,tag,f):
                continue
            v=layer[k]
            if k=="_sparse_block_indices_cache" and tag=="D":
                f.equal(layer,k,None,row,tag,"temporary_cache_release")
            elif not isinstance(v,dict) or "ref" not in v:
                f.absent(row,tag,"active_layer_binding_missing",layer=i,field=k)
            else:
                n=s.node(v)
                if k=="_sparse_source_input_ids":
                    read_scalar(n,contract["histories"][row][-1],pack,row,tag,f,k)
                if k=="_dash_dec_allow" and (n.get("shape")!=[1,46] or n.get("dtype")!="torch.bool"):
                    f.mismatch(row,tag,"page_candidate_shape",layer=i)
                if k in shared and v!=shared[k]:
                    f.mismatch(row,tag,"shared_layer_alias",layer=i,field=k)
                shared[k]=v
        if "indexer" not in layer:
            f.absent(row,tag,"indexer_configuration_missing",layer=i)
        elif "rope_mode" not in s.as_dict(layer["indexer"]):
            f.absent(row,tag,"indexer_mode_missing",layer=i)
    for i,ref in enumerate(routers):
        router=s.as_dict(ref)
        for name,val in (("training",False),("stage0","head_cls")):
            f.equal(router,name,val,row,tag,"router_configuration")
        params=s.as_dict(router["_infer_params"])
        for k in ("idx_scale","floor","sigma","K","topm"):
            require(params,k,row,tag,f)
        f.equal(params,"K",12,row,tag,"router_k")
        f.equal(params,"topm",16,row,tag,"router_topm")
    cache=s.as_dict(s.node(s.root["cache"])["fields"])
    f.equal(cache,"_seen_tokens",base+1,row,tag,"cache_seen_tokens")
    pg=s.as_dict(cache["_uocr_pg"])
    marks=contract["prompt"].count(128827)+contract["histories"][row].count(128827)
    read_scalar(s.node(pg["mcum"]),marks,pack,row,tag,f,"mcum")
    rope=s.as_dict(cache["_page_rope_state"])
    if set(rope)!=set(range(12)):
        f.mismatch(row,tag,"rotary_layer_inventory")
    for l,ref in rope.items():
        for k in ("page","tok","pf_cnt","n_pg"):
            require(s.as_dict(ref),k,row,tag,f)
    if tag=="B":
        args=s.as_dict(s.root["arguments"])
        f.equal(args,"use_cache",True,row,tag,"layer_use_cache")
        f.equal(args,"output_attentions",False,row,tag,"layer_output_attentions")
        read_scalar(s.node(args["position_ids"]),base,pack,row,tag,f,"position_ids")
        if args.get("hidden_states")!=s.root.get("lower_output"):
            f.mismatch(row,tag,"forwarded_hidden_alias")


def read_scalar(node,want,pack,row,phase,f,name):
    if (node.get("type")!="Tensor" or node.get("dtype")!="torch.int64" or
        math.prod(node.get("shape",[]))!=1 or node.get("bytes")!=8):
        f.mismatch(row,phase,"scalar_tensor_type",field=name)
        return
    if pack is None or "start" not in node:
        f.absent(row,phase,"scalar_payload_missing",field=name)
        return
    pack.seek(node["start"])
    b=pack.read(8)
    if len(b)!=8:
        f.absent(row,phase,"scalar_payload_missing",field=name)
    elif struct.unpack("<q",b)[0]!=want:
        f.mismatch(row,phase,"scalar_value",field=name,expected=want,observed=struct.unpack("<q",b)[0])
