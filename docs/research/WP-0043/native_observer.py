"""Stock instruction callbacks. Import torch only in an admitted worker process."""
import json
import sys
from pathlib import Path
from bindings import GEN, LAYER, resolve
from transfer import PinnedTransport
from capture import CaptureAdapter, InstructionMonitor, PHASES, code_identity, digest

MIB=1<<20
PINNED_BYTES=16*MIB
PACK_LIMIT=1792*MIB

CACHE_FIELDS=("key_cache","value_cache","_dash_idx_k","_page_rope_state","_seen_tokens","_uocr_pg")
ATTN_FIELDS=("_main_rope_pos_2d","_rope_pos_2d","_page_rope_meta","_dash_dec_allow",
             "_sparse_source_input_ids","_sparse_block_indices_cache","main_rope_mode","layer_idx")
LOCAL_FIELDS={
 "page_before":("st","ids","pg_id"),"page_after":("st","qp","same","open_row","allow","nblk","bs"),
 "dash_dispatch":("q_len","position_ids"),"generic_dispatch":("q_len","position_ids"),
 "idx_2d":("coords","pos_ids"),"idx_1d":("coords","pos_ids"),"idx_main":("coords","pos_ids"),
 "shared_output":("down_proj",),
 "attention_exit":("residual","hidden_states","attention_result"),
 "residual":("residual","hidden_states","self_attn_weights","kl_loss"),
 "post_rms":("hidden_states",),"mixture":("hidden_states",),"block_exit":("hidden_states",),
 "kv_before":("coords","cos","sin","position_ids","k","v","q"),
 "kv_after":("coords","position_ids"),"router_qk":("idx_pe","p"),
 "index_after":("idx_q","idx_k_new"),"routing_exit":("sc","cand","allow","topi","bias","valid","out"),
 "scores_pre_clean":("x","p","block_scores","block_cand","remote","cand"),
 "top_m":("M","xi","prior","xv","is_cand"),"route_final":("K","xi","prior","bias","valid"),
 "token_mask":("kpos","causal","local","keep","m"),
 "expert_route":("logits","scores","topk_idx","topk_weight"),
 "expert_total":("topk_idx","topk_weight","y"),"shared_sum":("y",),
 "expert_dispatch":("idxs","sorted_tokens","tokens_per_expert","outs"),
 "expert_return":("final_out",),
}


class Arena:
    def __init__(self,torch,out):
        self.torch=torch
        self.transport=PinnedTransport(torch,PINNED_BYTES)
        self.pack=(out/"tensors.bin").open("xb")
        self.seq=0
        self.by_digest={}

    def scores(self,tensor,alias):
        if alias or tuple(tensor.shape)!=(129280,) or tensor.dtype!=self.torch.float32 or not tensor.is_cuda:
            raise ValueError("unexpected native score source")
        data,chunks=self.transport.read(tensor)
        if len(chunks)!=1:
            raise ValueError("score row does not fit one owned transfer")
        return data,chunks[0]

    def tensor(self,t):
        n=t.numel()*t.element_size()
        rec={"dtype":str(t.dtype),"shape":list(t.shape),"strides":list(t.stride()),"device":str(t.device),
             "storage_offset":t.storage_offset(),"storage_base":t.untyped_storage().data_ptr(),
             "storage_bytes":t.untyped_storage().nbytes(),"element_size":t.element_size(),"bytes":n}
        if t.layout!=self.torch.strided or n>192*MIB:
            return {**rec,"unobserved":"layout or individual byte ceiling"}
        try:
            data,chunks=self.transport.read(t)
        except ValueError as e:
            return {**rec,"unobserved":str(e)}
        sha=digest(data)
        start=self.by_digest.get(sha)
        if start is None:
            if self.pack.tell()+n>PACK_LIMIT:
                raise RuntimeError("tensor archive byte ceiling")
            start=self.pack.tell()
            self.pack.write(data)
            self.by_digest[sha]=start
        rec.update(start=start,sha256=sha,transfer=chunks[0],chunks=chunks)
        return rec


def attributes(obj,keys):
    return {k:getattr(obj,k,{"absent":True}) for k in keys}


class Graph:
    """References preserve alias partitions inside each instantaneous logical snapshot."""
    def __init__(self,arena):
        self.arena=arena
        self.memo={}
        self.keepalive=[]
        self.nodes=[]

    def encode(self,x):
        if x is None or type(x) in (bool,int,str):
            return x
        if type(x) is float:
            return {"float_hex":x.hex()}
        oid=id(x)
        if oid in self.memo:
            return {"ref":self.memo[oid]}
        key=len(self.nodes)
        self.memo[oid]=key
        self.keepalive.append(x)
        node={"type":type(x).__qualname__,"oid":oid}
        self.nodes.append(node)
        t=self.arena.torch
        if isinstance(x,t.Tensor):
            node.update(self.arena.tensor(x))
        elif isinstance(x,dict):
            node["entries"]=[[self.encode(k),self.encode(v)] for k,v in x.items()]
        elif isinstance(x,(tuple,list)):
            node["items"]=[self.encode(v) for v in x]
        elif type(x).__module__.startswith("numpy") and hasattr(x,"tolist"):
            node.update(dtype=str(x.dtype),shape=list(x.shape),items=self.encode(x.tolist()))
        elif type(x).__name__=="DynamicCache":
            node["fields"]=self.encode(attributes(x,CACHE_FIELDS))
            node["actual_keys"]=list(vars(x))
        else:
            node["unobserved"]="unsupported active object"
        return {"ref":key}

    def snapshot(self,roots):
        root=self.encode(roots)
        return {"root":root,"nodes":self.nodes}


class StockObserver:
    def __init__(self,torch,model,model_dir,out):
        self.model=model
        self.progress=out/"progress"
        self.sites=resolve(model_dir,type(model).__module__.rsplit(".",1)[0])
        self.gen=next(c for c in self.sites if c.co_qualname==GEN)
        self.arena=Arena(torch,out)
        self.log=(out/"observations.jsonl").open("x",encoding="utf-8")
        self.ledger=CaptureAdapter(self.gen,self.arena.scores,"native")
        self.monitor=InstructionMonitor(self.sites,self.visit)
        self.active=None
        self.early_producer=None
        self.last_copy=None
        self.last_tensor=None
        self.record_number=0
        self.receiver=model.model.layers[11]
        self.identities={c:code_identity(c) for c in self.sites}

    def write(self,key,row,frame,data):
        self.record_number+=1
        record={"journal_seq":self.record_number,"tag":key,"row":row,"instruction":frame.f_lasti,"identity":self.identities[frame.f_code],
                "frame":id(frame),"data":data}
        line=json.dumps(record,separators=(",",":"),allow_nan=False)
        if self.log.tell()+len(line.encode())+2>96*MIB:
            raise RuntimeError("observation journal ceiling")
        self.log.write(line+"\n")
        self.log.flush()
        self.arena.pack.flush()

    def roots(self,gen,cache):
        model=self.model.model
        g=gen.f_locals
        attrs=[attributes(layer.self_attn,ATTN_FIELDS) for layer in model.layers]
        routers=[attributes(layer.self_attn.dash_router,("_infer_params","stage0","training"))
                 for layer in model.layers]
        dash=sys.modules[type(self.model).__module__.rsplit(".",1)[0]+".modeling_deepseekv2"]
        for i,layer in enumerate(model.layers):
            att=layer.self_attn
            attrs[i]["indexer"]=attributes(att.indexer,("_page_rope_meta","_rope_pos_2d","rope_mode"))
            attrs[i]["buffers"]={k:v for k,v in att.named_buffers() if "rotary" in k}
        streamer=g.get("streamer")
        return {"cache":cache,"generator_cache":g.get("cache"),"prompt":g["prompt_ids"],
                "history":g["gen"],"guard":g["guard_st"],"position":g.get("pos"),
                "pending":g.get("nxt"),"step":g["step"],"finish":g["finish"],"streamer":attributes(
                    streamer,("token_cache","print_len","next_tokens_are_prompt","skip_prompt")),
                "layers":attrs,"routers":routers,"cfg":attributes(self.model.config,("_ring_window","sliding_window")),
                "dash_infer":gen.f_globals.get("_DASH_INFER"),"dash_global":dash._INFER,
                "page_scope":dash._base._PAGE_SCOPE_PREFILL,"config_sparse":self.model.config.sparse_attention_config,
                "ckpt_sparse":dash._CKPT_SP.get(id(self.model.config.sparse_attention_config)),"saved_cfg":g["saved_cfg"]}

    def visit(self,tag,frame):
        local=frame.f_locals
        if frame.f_code is self.gen:
            if local["self"] is not self.model:
                raise RuntimeError("wrong generator receiver")
            if tag in ("prefill_producer","model_producer","head_producer","rep_producer","page_producer","choice_consumer"):
                stream=self.arena.transport.stream_record()
                origin={**stream,"site":tag,"instruction":frame.f_lasti,"frame":id(frame),"receiver":id(local["self"]),
                        "ordinal":local.get("step",-1),"code_sha256":self.identities[frame.f_code]["code_sha256"]}
                if tag in ("prefill_producer","model_producer"):
                    if tag=="model_producer" and len(local["gen"])-619 in range(5):
                        self.write(tag,len(local["gen"])-619,frame,origin)
                    self.early_producer=origin
                    self.arena.transport.origin_event=origin
                row=local.get("step",-1)-619
                if row in range(5) and tag in ("head_producer","rep_producer","page_producer","choice_consumer"):
                    previous=self.last_copy if tag!="head_producer" else None
                    if previous:
                        if self.last_tensor is not local["logits"] or not self.arena.transport.done.query():
                            raise RuntimeError("next writer source or prior transfer completion changed")
                        origin.update(previous_copy=previous,previous_source=id(local["logits"]),preceding_copy_complete=True)
                    self.write(tag,row,frame,origin)
                    self.arena.transport.origin_event=origin
                return
            if tag in ("terminal_eos","cleanup"):
                self.write(tag,None,frame,{"nxt":local.get("nxt"),"finish":local.get("finish"),
                    "ids":list(local["gen"]),"length":int(local["cache"].key_cache[0].shape[-2]),
                    "router_stage0":[x.self_attn.dash_router.stage0 for x in self.model.model.layers],
                    "saved_stage0":[v for _,v in local["dash_state"]["stage0"]],
                    "retained_params":[x.self_attn.dash_router._infer_params for x in self.model.model.layers],
                    "saved_cfg":list(local["saved_cfg"]),
                    "dash_on":frame.f_globals["_DASH_INFER"]["on"],"ring":getattr(self.model.config,"_ring_window",None),
                    "sliding":getattr(self.model.config,"sliding_window",None)})
                return
            if tag=="D":
                if len(local["gen"])%16==0:
                    self.progress.write_bytes(str(len(local["gen"])).encode("ascii"))
                self.write("append",None,frame,{"index":len(local["gen"])-1,"id":local["nxt"],"pos":local["pos"]})
            row=local["step"]-619
            if row not in range(5):
                return
            if tag in PHASES:
                item=self.ledger.copy(row,frame,local["logits"])
                self.last_copy=item["copy"]
                self.last_tensor=local["logits"]
                data=item.pop("data")
                item.update(hex=data.hex(),sha256=digest(data))
                hidden=Graph(self.arena).snapshot({"final_norm":local["h"]}) if tag==PHASES[0] else None
                self.write(tag,row,frame,{"record":item,"event":self.ledger.events[-1],"hidden":hidden,"guard":dict(local["guard_st"]),
                    "history":list(local["gen"]),"cap":local["max_page_tokens"],"page":local["page_id"],
                    "eos":local["eos_id"],"expected_pages":local["expected_pages"]})
            elif tag=="D":
                roots=self.roots(frame,local["cache"])
                self.write(tag,row,frame,{"y":local["nxt"],"history":list(local["gen"]),"pos":local["pos"],
                     "graph":Graph(self.arena).snapshot(roots),"lengths":[v.shape[-2] for v in local["cache"].key_cache]})
                self.active=None
                self.last_tensor=None
                self.last_copy=None
            return
        if tag in ("page_before","page_after"):
            ancestor=frame.f_back
            while ancestor and ancestor.f_code is not self.gen:
                ancestor=ancestor.f_back
            if ancestor:
                row=len(ancestor.f_locals["gen"])-619
                if row in range(5):
                    values={k:local[k] for k in LOCAL_FIELDS[tag]}
                    self.write(tag,row,frame,Graph(self.arena).snapshot(values))
            return
        if tag=="B":
            if local["self"] is not self.receiver or local["hidden_states"].shape[1]!=1:
                return
            ancestor=frame.f_back
            caller=None
            while ancestor and ancestor.f_code is not self.gen:
                if "layer_outputs" in ancestor.f_locals and ancestor.f_locals.get("decoder_layer") is self.receiver:
                    caller=ancestor
                ancestor=ancestor.f_back
            if ancestor is None:
                raise RuntimeError("stock caller binding unavailable")
            g=ancestor.f_locals
            row=len(g["gen"])-619
            if row not in range(5):
                return
            self.active=row
            self.arena.transport.origin_event=self.early_producer
            roots=self.roots(ancestor,local["past_key_value"])
            roots["arguments"]={k:v for k,v in local.items() if k!="self"}
            if caller:
                roots["lower_output"]=caller.f_locals["layer_outputs"][0]
            self.write(tag,row,frame,{"graph":Graph(self.arena).snapshot(roots),
                "history":list(g["gen"]),"pos":g["pos"],"guard":dict(g["guard_st"]),
                "lower_forwarded":bool(caller and caller.f_locals["layer_outputs"][0] is local["hidden_states"]),
                "receiver_id":id(local["self"]),"caller_receiver":id(caller.f_locals["self"]) if caller else None,
                "caller_code":code_identity(caller.f_code) if caller else None,"caller_offset":caller.f_lasti if caller else None,
                "lengths":[v.shape[-2] for v in local["past_key_value"].key_cache]})
            return
        if self.active is not None:
            if tag=="shared_output" and local["self"] is not self.receiver.mlp.shared_experts:
                return
            values={k:local[k] for k in LOCAL_FIELDS[tag] if k in local}
            if tag=="attention_exit":
                values["attention_result"]=local["attn_outputs"][0]
            self.write(tag,self.active,frame,Graph(self.arena).snapshot(values))

    def close(self):
        self.log.close()
        self.arena.pack.close()
