"""Offline native admission and pair verifier. Opens all run and tensor files read-only."""
import json
import math
import dis
import struct
from pathlib import Path
from capture import PHASES, code_identity, digest
from bindings import GEN,resolve
from native import ARCH,ARM,BASE,HIST,LABELS,LIMITS,MODEL,OUT,SCHEME,RELEASE,blob,bytes_json,plan,hash_file
from native_observer import CACHE_FIELDS,LOCAL_FIELDS
from timing import read_timing,timeline as validate_timing
from scorer import Findings,public_document,score_rows
from native_validation import TENSOR_KEYS,local_contract,require,rooted_state,runtime_receipt,score_events,transfer_contract

SIZE={"torch.float32":4,"torch.bfloat16":2,"torch.float16":2,"torch.int64":8,"torch.int32":4,
      "torch.int16":2,"torch.bool":1,"torch.uint8":1,"torch.int8":1,"torch.float64":8}


def read(path,find,key):
    if not path.exists():
        find.absent(None,"public_document",key+"_missing")
        return {}
    try:
        obj=json.loads(path.read_bytes())
        if not isinstance(obj,dict):
            raise ValueError()
        if not obj:
            find.absent(None,"public_document",key+"_empty")
        return obj
    except (ValueError,UnicodeError):
        find.mismatch(None,"public_document",key+"_invalid")
        return {}


def archived(label):
    obs=json.loads(blob(ARCH,HIST+label+".observation.json"))
    ids=json.loads(blob(ARCH,HIST+label+".token_ids.json"))
    raw=blob(ARCH,HIST+label+".raw.txt")
    nat=obs["native"]
    if digest(raw)!=nat["text_sha256"] or digest(json.dumps(ids).encode())!=nat["token_ids_sha256"]:
        raise RuntimeError("historical anchor integrity")
    return {"ids":ids,"text":raw.decode(),"prompt":nat["prompt"],"expected_pages":nat["expected_pages"],
            "num_pages_out":nat["num_pages_out"],"output_tokens":nat["output_tokens"],
            "terminal":nat["finish_reason"],"markers":obs["page_markers"]["marker_token_positions"]},nat["prompt_len"]


def verify_docs(find):
    docs={}
    runtime={}
    for arm in ARM:
        runtime[arm]=read(OUT/arm/"runtime.json",find,arm+"_runtime")
        try:
            runtime_receipt(runtime[arm],arm,find)
        except (KeyError,ValueError,TypeError,AttributeError) as exc:
            find.mismatch(None,"public_document","runtime_body_invalid",arm=arm,detail=str(exc))
            find.absent(None,"public_document","runtime_verification_incomplete",arm=arm)
        for j,label in enumerate(LABELS):
            item=read(OUT/arm/(label+".json"),find,arm+"_"+label)
            expected,plen=archived(label)
            # Keep both coordinates when an earlier/later warmup conflicts.
            mark=(len(find.missing),len(find.conflicts))
            public_document(item.get("document",{}),expected,find)
            doc=item.get("document",{})
            if not isinstance(doc,dict):
                find.mismatch(None,"public_document","public_record_invalid",arm=arm)
                doc={}
            if "prompt_token_ids" not in doc:
                find.absent(None,"public_document","prompt_ids_missing",arm=arm,call=label)
            else:
                ids=doc["prompt_token_ids"]
                if not isinstance(ids,list) or len(ids)!=plen or ids.count(128827)!=expected["expected_pages"]:
                    find.mismatch(None,"public_document","prompt_receipt_mismatch",arm=arm,call=label)
            if item:
                find.equal(item,"call",j,None,"public_document","schedule_mismatch")
                find.equal(item,"family",label[:3],None,"public_document","schedule_mismatch")
                obs=json.loads(blob(ARCH,HIST+label+".observation.json"))
                find.equal(item,"kwargs",obs["call_kwargs"],None,"public_document","call_kwargs_mismatch")
                for key in ("peak_allocated","peak_reserved"):
                    if key not in item:
                        find.absent(None,"public_document","device_peak_missing",field=key)
                    elif type(item[key])!=int or not 0<=item[key]<=LIMITS["allocator_bytes"]:
                        find.mismatch(None,"public_document","device_peak_overrun",field=key)
            for finding in find.missing[mark[0]:]+find.conflicts[mark[1]:]:
                finding.update(arm=arm,call=label,comparator="archive")
            docs[arm,label]=doc
    for label in LABELS:
        public_document(docs["observed",label],docs["untouched",label],find)
    for k in ("eval","cuda","torch","deterministic","tf32","cudnn_tf32","autocast","training_modules"):
        if k in runtime["untouched"]:
            find.equal(runtime["observed"],k,runtime["untouched"][k],None,"public_document","runtime_mismatch")
    if runtime["untouched"].get("pid") is not None and runtime["untouched"].get("pid")==runtime["observed"].get("pid"):
        find.mismatch(None,"public_document","cold_process_identity")
    return docs,runtime


class Snapshot:
    def __init__(self,graph):
        self.nodes=graph["nodes"]
        self.root=self.as_dict(graph["root"])

    def node(self,value):
        i=value["ref"]
        if type(i)!=int or not 0<=i<len(self.nodes):
            raise ValueError("invalid graph reference")
        return self.nodes[i]

    def as_dict(self,value):
        n=self.node(value)
        items=n["entries"]
        if n.get("type")!="dict" or len(items)!=len(dict(items)):
            raise ValueError("typed dictionary slot inventory")
        return dict(items)

    def items(self,value):
        n=self.node(value)
        if n.get("type") not in ("list","tuple"):
            raise ValueError("typed sequence")
        return n["items"]

    def check(self,pack,row,tag,f):
        ids=[n.get("oid") for n in self.nodes]
        if any(type(oid)!=int or oid<=0 for oid in ids) or len(ids)!=len(set(ids)):
            f.mismatch(row,tag,"object_identity_inventory")
        for j,n in enumerate(self.nodes):
            try:
                self.check_node(n,j,pack,row,tag,f)
            except (KeyError,TypeError,ValueError,IndexError,OverflowError) as exc:
                f.mismatch(row,tag,"malformed_graph_node",node=j,detail=str(exc))
                f.absent(row,tag,"graph_node_incomplete",node=j)
    def check_node(self,n,j,pack,row,tag,f):
            if "unobserved" in n:
                f.absent(row,tag,"active_value_missing",node=j,reason=n["unobserved"])
                return
            if n.get("type") not in ("Tensor","Parameter"):
                if "storage_base" in n or "strides" in n:
                    f.mismatch(row,tag,"unknown_tensor_type",node=j)
                return
            missing=TENSOR_KEYS-set(n)
            if missing:
                f.absent(row,tag,"tensor_schema_incomplete",node=j,fields=sorted(missing))
                return
            size=SIZE.get(n["dtype"])
            expected=size*math.prod(n["shape"]) if size else None
            if expected!=n["bytes"] or len(n["shape"])!=len(n["strides"]):
                f.mismatch(row,tag,"tensor_layout",node=j)
            if pack is None or "start" not in n:
                f.absent(row,tag,"tensor_bytes_missing",node=j)
                return
            if n["bytes"]<0 or n["bytes"]>192*(1<<20) or n["start"]<0:
                f.mismatch(row,tag,"tensor_extent",node=j)
                return
            pack.seek(n["start"])
            data=pack.read(n["bytes"])
            if len(data)!=n["bytes"]:
                f.absent(row,tag,"tensor_bytes_missing",node=j)
            elif digest(data)!=n["sha256"]:
                f.mismatch(row,tag,"tensor_digest_mismatch",node=j)
            chunks=n["chunks"]
            transfer_contract(n,chunks,row,tag,f)
            if (sum(t["bytes"] for t in chunks)!=n["bytes"] or any(t["bytes"]>LIMITS["pinned_host_pool"]
                or not t["completion"] or not t["pinned"] or not t["complete_before_return"]
                or t["producer_stream"]!=t["copy_stream"] for t in chunks)):
                f.mismatch(row,tag,"graph_chunk_coverage",node=j)
            transfer=n["transfer"]
            if (not transfer["completion"] or not transfer["complete_before_return"] or not transfer["pinned"]
                or transfer["copy_stream"]!=transfer["producer_stream"] or n["storage_base"]==transfer["dest_storage"]):
                f.mismatch(row,tag,"graph_copy_ancestry",node=j)
            # Native tensor addresses describe strided views; logical bytes are serialized in C order.
            if n["bytes"]:
                hi=n["storage_offset"]+sum((a-1)*b for a,b in zip(n["shape"],n["strides"]))
                if any(x<0 for x in n["strides"]) or n["storage_offset"]<0 or size and (hi+1)*size>n["storage_bytes"]:
                    f.mismatch(row,tag,"source_view_extent",node=j)

    def cache(self,row,tag,position,f):
        cache=self.node(self.root["cache"])
        if self.root["cache"]!=self.root["generator_cache"] or cache["type"]!="DynamicCache":
            f.mismatch(row,tag,"cache_identity")
        fields=self.as_dict(cache["fields"])
        if list(fields)!=cache["actual_keys"]:
            f.mismatch(row,tag,"cache_instance_key_inventory")
        for name in sorted(set(fields)-set(CACHE_FIELDS)):
            if name in {"_ring_pos","_prefill_length","_idx_keys"}:
                f.mismatch(row,tag,"unadmitted_cache_path",field=name)
            else:
                f.absent(row,tag,"unknown_cache_field_semantics",field=name)
        # These are Python container/object slots, including the underlying tensor physical ranges.
        for name in CACHE_FIELDS:
            if name not in fields or name not in cache["actual_keys"]:
                f.absent(row,tag,"cache_field_missing",field=name)
        if self.root["dash_infer"]!=self.root["dash_global"]:
            f.mismatch(row,tag,"dash_global_alias")
        if tag=="B":
            args=self.as_dict(self.root["arguments"])
            hidden=self.node(args["hidden_states"])
            if (self.root.get("lower_output")!=args["hidden_states"] or args["past_key_value"]!=self.root["cache"]
                or hidden.get("shape")!=[1,1,1280] or hidden.get("dtype")!="torch.bfloat16"):
                f.mismatch(row,tag,"input_forwarding")
        output={}
        for name in ("key_cache","value_cache","_dash_idx_k"):
            vec=(self.as_dict(fields[name]) if name=="_dash_idx_k" else
                 dict(enumerate(self.items(fields[name]))))
            if set(vec)!=set(range(12)):
                f.mismatch(row,tag,"cache_layer_inventory",field=name)
            for l,v in vec.items():
                node=self.node(v)
                size=position+int(l<11 or tag=="D")
                shape=[1,size,128] if name=="_dash_idx_k" else [1,10,size,128]
                dtype="torch.float32" if name=="_dash_idx_k" else "torch.bfloat16"
                if node.get("shape")!=shape or node.get("dtype")!=dtype:
                    f.mismatch(row,tag,"layer_cache_shape",field=name,layer=l)
                if TENSOR_KEYS.issubset(node) and node.get("type")=="Tensor":
                    output[name,l]=node
                else:
                    f.absent(row,tag,"layer_cache_payload_missing",layer=l,field=name)
        ranges=[]
        for (name,l),node in output.items():
            size=node["element_size"]
            low=node["storage_base"]+size*node["storage_offset"]
            high=low+size*(1+sum((n-1)*s for n,s in zip(node["shape"],node["strides"])))
            ranges.append((low,high,name,l))
        ranges.sort()
        for a,b in zip(ranges,ranges[1:]):
            if a[1]>b[0]:
                f.mismatch(row,tag,"cache_storage_overlap",left=a[2:],right=b[2:])
        return output


def verify_append(a,b,pack,row,phase,f):
    # Compare corresponding logical prefixes per head. Fresh native cat rebinds the tensor.
    complete={(kind,l) for kind in ("key_cache","value_cache","_dash_idx_k") for l in range(12)}
    for name,layer in sorted(complete-(a.keys() & b.keys())):
        f.absent(row,phase,"append_comparison_missing",field=name,layer=layer)
    for key in a.keys() & b.keys():
        old,new=a[key],b[key]
        ly=key[1]
        if old["shape"]==new["shape"]:
            if old["sha256"]!=new["sha256"] or old["oid"]!=new["oid"] or old["storage_base"]!=new["storage_base"]:
                f.mismatch(row,phase,"unmodified_cache_changed",field=key[0],layer=ly)
        elif pack is not None:
            if new["shape"][-2]!=old["shape"][-2]+1 or old["oid"]==new["oid"] or old["storage_base"]==new["storage_base"]:
                f.mismatch(row,phase,"cache_append_binding",field=key[0],layer=ly)
                continue
            heads=math.prod(old["shape"][:-2])
            old_stride=old["bytes"]//heads
            new_stride=new["bytes"]//heads
            for h in range(heads):
                pack.seek(old["start"]+h*old_stride)
                before=pack.read(old_stride)
                pack.seek(new["start"]+h*new_stride)
                after=pack.read(old_stride)
                if before!=after:
                    offset=next((k for k,(x,y) in enumerate(zip(before,after)) if x!=y),min(len(before),len(after)))
                    f.mismatch(row,phase,"cache_prefix_changed",field=key[0],layer=ly,head=h,byte=offset)
                    break


def check_finite(snapshot,fields,pack,row,phase,f):
    for field in fields:
        value=snapshot.root.get(field)
        if not isinstance(value,dict) or "ref" not in value or pack is None:
            continue
        node=snapshot.node(value)
        if "start" not in node:
            continue
        pack.seek(node["start"])
        data=pack.read(node["bytes"])
        dtype=node["dtype"]
        if dtype=="torch.bfloat16":
            bad=next((i for i,(w,) in enumerate(struct.iter_unpack("<H",data)) if w&0x7f80==0x7f80),None)
        elif dtype in ("torch.float32","torch.float16"):
            fmt="<f" if dtype=="torch.float32" else "<e"
            bad=next((i for i,(v,) in enumerate(struct.iter_unpack(fmt,data)) if not math.isfinite(v)),None)
        else:
            continue
        if bad is not None:
            f.mismatch(row,phase,"nonfinite_active_value",field=field,index=bad)


def native_records(find):
    journal=OUT/"observed/observations.jsonl"
    records={}
    if not journal.exists():
        return records
    with journal.open("rb") as src:
        for serial,line in enumerate(src,1):
            try:
                rec=json.loads(line)
                if not isinstance(rec,dict) or not isinstance(rec.get("tag"),str):
                    raise ValueError("invalid native record")
                if not isinstance(rec.get("data"),dict):
                    find.mismatch(None,"public_document","invalid_native_payload")
                    find.absent(None,"public_document","native_payload_missing")
                    rec["data"]={}
                key=rec["row"],rec["tag"]
                if key[0] is not None and (type(key[0])!=int or not 0<=key[0]<5):
                    raise ValueError("invalid native row")
                if rec["tag"]=="append" and type(rec["data"].get("index"))!=int:
                    raise ValueError("append ordinal")
                if rec["tag"]=="layer_path":
                    key=rec["row"],("path",rec["data"]["layer"])
                if rec["tag"]=="append":
                    key=None,("append",rec["data"]["index"])
                if rec.get("journal_seq")!=serial:
                    find.mismatch(*key,"journal_sequence_mismatch")
                if key in records:
                    find.mismatch(key[0],rec["tag"],"duplicate_native_record")
                else:
                    records[key]=rec
            except (ValueError,KeyError,TypeError):
                if line.endswith(b"\n"):
                    find.mismatch(None,"public_document","journal_record_invalid")
                find.absent(None,"public_document","journal_record_incomplete")
    return records


def check_guard_calls(records,row,h,c,f):
    from scorer import canonical_state,support
    for label,phase,caller,return_offset in (("rep",PHASES[1],1228,402),("page",PHASES[2],1272,520)):
        entry=records.get((row,label+"_entry"),{})
        exit=records.get((row,label+"_return"),{})
        pre=entry.get("data",{})
        post=exit.get("data",{})
        capture=records.get((row,phase),{}).get("data",{}).get("event",{})
        for stamp in (pre,post):
            for key,val in (("source",capture.get("source")),("history",h),("generator_frame",capture.get("frame")),
                            ("generator_receiver",capture.get("receiver")),("history_object",stamp.get("generator_history")),
                            ("generator_logits",capture.get("source"))):
                if val is None and key!="history":
                    f.absent(row,phase,"guard_call_binding_reference_missing",field=key)
                else:
                    f.equal(stamp,key,val,row,phase,"guard_call_binding")
            if stamp.get("caller_offset") not in (caller,caller+2,caller+4,caller+6):
                if "caller_offset" in stamp:
                    f.mismatch(row,phase,"guard_caller_instruction")
                else:
                    f.absent(row,phase,"guard_caller_instruction_missing")
        f.equal(exit,"instruction",return_offset,row,phase,"active_guard_return")
        f.link(exit,"frame",entry,"frame",row,phase,"guard_frame_pair")
        f.link(post,"returned_object",capture,"source",row,phase,"guard_return_identity")
        if label=="rep":
            for k,v in (("order",35),("window",1024),("whitelist",[])):
                f.equal(pre,k,v,row,phase,"guard_arguments")
            f.equal(post,"banned",sorted(support(h,c)),row,phase,"actual_ban_set")
        else:
            for stamp in (pre,post):
                for k,v in (("page",c["page"]),("eos",c["eos"]),("cap",c["cap"]),("expected_pages",3),
                            ("guard_object",stamp.get("generator_guard"))):
                    f.equal(stamp,k,v,row,phase,"guard_arguments")
            f.equal(pre,"cursor",canonical_state(h[:-1],c["page"],True),row,phase,"guard_entry_cursor")
            f.equal(post,"cursor",canonical_state(h,c["page"],True),row,phase,"guard_exit_cursor")


def score_native():
    from contextlib import nullcontext
    f=Findings()
    admission=read(OUT/"admission.json",f,"admission")
    if admission:
        for k in ("release","plan","initial_device","n_model","wheels"):
            require(admission,k,None,"public_document",f)
        f.equal(admission,"n_model",18,None,"public_document","model_count")
        f.equal(admission,"wheels",32,None,"public_document","wheel_count")
        if (admission.get("plan")!=json.loads(bytes_json(plan())) or not isinstance(admission.get("release"),dict) or
            admission.get("release",{}).get("plan_sha256")!=digest(bytes_json(plan()))):
            f.mismatch(None,"public_document","plan_mismatch")
    done=read(OUT/"outcome.json",f,"supervisor_outcome")
    if done.get("status")=="finished":
        for key in ("files","bytes","elapsed_s","logs"):
            require(done.get("final_resources",{}),key,None,"public_document",f)
        if not isinstance(done.get("files"),dict) or not isinstance(done.get("final_resources"),dict) or len(done["files"])!=done["final_resources"].get("files"):
            f.mismatch(None,"public_document","final_inventory_cardinality")
        timing=done.get("timing")
        for arm in ARM:
            interval=timing.get(arm) if isinstance(timing,dict) else None
            if not isinstance(interval,dict) or not (OUT/arm/"phase").is_file():
                f.absent(None,"public_document","arm_timing_missing",arm=arm)
                continue
            try:
                validate_timing(read_timing(OUT/arm),arm,LABELS,LIMITS,interval["origin_ns"],interval["exit_check_ns"],finished=True)
            except (TypeError,KeyError,ValueError,OSError,RuntimeError) as exc:
                f.mismatch(None,"public_document","arm_timing_invalid",arm=arm,detail=str(exc))
    if done.get("status")!="finished":
        f.absent(None,"public_document","paired_execution_incomplete")
    if admission:
        try:
            authorized=json.loads(blob("refs/heads/coordination/bootstrap",RELEASE))
            f.equal(admission,"release",authorized,None,"public_document","coordinator_release_mismatch")
        except Exception:
            f.absent(None,"public_document","coordinator_release_unavailable")
    files=done.get("files",{})
    if not isinstance(files,dict):
        f.mismatch(None,"public_document","invalid_file_inventory")
        files={}
    mandatory={"admission.json","observed/tensors.bin","observed/observations.jsonl"}
    mandatory.update(f"{a}/{k}" for a in ARM for k in ("runtime.json","phase","stdout.log","stderr.log",*(v+".json" for v in LABELS)))
    for rel in sorted(mandatory-set(files)):
        f.absent(None,"public_document","inventory_obligation_missing",file=rel)
    if done.get("status")=="finished" and OUT.exists():
        disk={p.relative_to(OUT).as_posix() for p in OUT.rglob("*") if p.is_file() and p.name!="outcome.json"}
        if disk!=set(files):
            f.mismatch(None,"public_document","final_inventory_mismatch",extra=sorted(disk-set(files)),missing=sorted(set(files)-disk))
    for rel,sha in files.items():
        file=(OUT/rel).resolve()
        if not file.is_relative_to(OUT.resolve()):
            f.mismatch(None,"public_document","inventory_path_invalid")
        elif not file.is_file():
            f.absent(None,"public_document","archived_file_missing",file=rel)
        elif hash_file(file)!=sha:
            f.mismatch(None,"public_document","archived_file_corrupt",file=rel)
    public_findings=Findings()
    docs,runtimes=verify_docs(public_findings)
    f.conflicts.extend(public_findings.conflicts)
    f.missing.extend(public_findings.missing)
    archive,_=archived(LABELS[-1])
    prompt=docs["untouched",LABELS[-1]].get("prompt_token_ids")
    # An absent reference never supplies positive native evidence; page count can still
    # be independently checked against the archived count while other contrasts execute.
    contract={"vocab":list(range(129280)),"histories":[archive["ids"][:619+i] for i in range(5)],
              "order":35,"window":1024,"cap":20000,"eos":1,"page":128827,
              "target_ids":archive["ids"][619:624],"prompt":prompt if prompt is not None else [128827]*archive["expected_pages"]}
    sites=resolve(MODEL)
    lookup={tag:(code,offset) for code,ofs in sites.items() for offset,tag in ofs.items()}
    gen=next(code for code in sites if code.co_qualname==GEN)
    records=native_records(f)
    core={k for k in LOCAL_FIELDS if k not in ("generic_dispatch","idx_1d","idx_2d","idx_main")}
    score_e={"rows":[],"events":[]}
    tensors=OUT/"observed/tensors.bin"
    old_cache=None
    with tensors.open("rb") if tensors.exists() else nullcontext(None) as pack:
        for (row,tag),rec in records.items():
            if isinstance(tag,tuple):
                tag="D" if tag[0]=="append" else rec["data"].get("site","unbound")
                if not isinstance(tag,str):
                    f.mismatch(row,"B","unbound_site")
                    continue
            if tag in ("rep_return","page_return"):
                code=lookup["rep_entry" if tag=="rep_return" else "page_entry"][0]
                admissible={i.offset for i in dis.get_instructions(code) if i.opname in ("RETURN_VALUE","RETURN_CONST")}
                if rec.get("identity")!=code_identity(code) or rec.get("instruction") not in admissible:
                    f.mismatch(row,tag,"guard_return_instruction")
                continue
            if tag not in lookup:
                f.mismatch(row,tag,"unbound_site")
                continue
            code,offset=lookup[tag]
            if type(rec.get("frame"))!=int or rec.get("frame",0)<=0:
                f.mismatch(row,tag,"executing_frame_identity")
            if rec.get("identity")!=code_identity(code) or rec.get("instruction")!=offset:
                f.mismatch(row,tag,"phase_cut_binding_mismatch")
        for i,h in enumerate(contract["histories"]):
            r={"index":i,"phases":{}}
            score_e["rows"].append(r)
            expected_tags=core|{"B","D","model_producer","rep_entry","rep_return","page_entry","page_return",*PHASES}
            for depth in range(12):
                for index,site,size in ((None,"prefill_dispatch",827),(i,"dash_dispatch",1)):
                    record=records.get((index,("path",depth)),{}).get("data",{})
                    for key,val in (("layer",depth),("q_len",size),("site",site)):
                        f.equal(record,key,val,i,"B","dispatch_path")
            try:
                check_guard_calls(records,i,h,contract,f)
            except (KeyError,TypeError,ValueError) as exc:
                f.absent(i,PHASES[1],"guard_callee_incomplete",detail=str(exc))
            try:
                score_events(i,records,lookup,f)
            except (ValueError,TypeError,KeyError,IndexError) as exc:
                f.mismatch(i,PHASES[0],"malformed_score_ancestry",detail=str(exc))
            for tag in sorted(expected_tags):
                if (i,tag) not in records:
                    f.absent(i,tag,"native_observation_missing",required=tag)
            alt=[t for t in ("idx_1d","idx_2d","idx_main") if (i,t) in records]
            if not alt:
                f.absent(i,"B","indexer_rotary_branch_missing")
            if len(alt)>1 or (i,"generic_dispatch") in records:
                f.mismatch(i,"B","unexpected_dispatch")
            for tag in ("B",*LOCAL_FIELDS.keys(),*PHASES,"D"):
                if (i,tag) not in records:
                    continue
                data=records[i,tag]["data"]
                try:
                    if tag in PHASES:
                        f.link(data["event"],"receiver",runtimes["observed"].get("receivers",{}),"generator",
                                i,tag,"generator_receiver")
                        r["phases"][tag]=data["record"]
                        score_e["events"].append(data["event"])
                        if tag==PHASES[0]:
                            r.update({k:data[k] for k in ("history","page","eos","cap","expected_pages")})
                            r["before"]=data["guard"]
                            snap=Snapshot(data["hidden"])
                            snap.check(pack,i,tag,f)
                            local_contract(snap,tag,["final_norm"],i,f)
                            check_finite(snap,["final_norm"],pack,i,tag,f)
                        if tag==PHASES[-1]:
                            r["after"]=data["guard"]
                    elif tag in ("B","D"):
                        if tag=="B":
                            receivers=runtimes["observed"].get("receivers",{})
                            f.link(data,"receiver_id",receivers,"layer11",i,tag,"layer_receiver")
                            f.link(data,"caller_receiver",receivers,"decoder",i,tag,"decoder_receiver")
                        snap=Snapshot(data["graph"])
                        snap.check(pack,i,tag,f)
                        try:
                            rooted_state(snap,tag,i,contract,pack,f)
                        except (KeyError,ValueError,TypeError,IndexError) as exc:
                            f.absent(i,tag,"state_projection_incomplete",detail=str(exc))
                        now=snap.cache(i,tag,1445+i,f)
                        if old_cache is not None:
                            verify_append(old_cache,now,pack,i,tag,f)
                        old_cache=now
                        if tag=="B":
                            check_finite(snap,["lower_output"],pack,i,tag,f)
                            c0=records.get((i,PHASES[0]),{}).get("data",{})
                            if "guard" in c0:
                                f.equal(data,"guard",c0["guard"],i,tag,"guard_entry_binding")
                            from bindings import caller_binding
                            f.equal(data,"caller_code",caller_binding(MODEL),i,tag,"caller_code")
                            if data.get("caller_offset") not in (1270,1272,1274,1276):
                                f.mismatch(i,tag,"caller_instruction",observed=data.get("caller_offset"))
                            f.equal(data,"lower_forwarded",True,i,tag,"input_forwarding")
                            f.equal(data,"history",h,i,tag,"entry_history")
                            f.equal(data,"pos",1445+i,i,tag,"entry_position")
                        else:
                            r["y"]=data["y"]
                            f.equal(data,"y",archive["ids"][619+i],i,tag,"anchored_y")
                            f.equal(data,"history",archive["ids"][:620+i],i,tag,"single_append")
                            f.equal(data,"pos",1446+i,i,tag,"next_position")
                    else:
                        snap=Snapshot(data)
                        snap.check(pack,i,tag,f)
                        local_contract(snap,tag,LOCAL_FIELDS[tag],i,f)
                        for field in LOCAL_FIELDS[tag]:
                            if field not in snap.root:
                                f.absent(i,tag,"native_local_missing",field=field)
                        check_finite(snap,("hidden_states","residual","final_out","down_proj","scores","logits",
                                           "topk_weight","y","out","idx_k_new","idx_q"),pack,i,tag,f)
                except (ValueError,TypeError,KeyError,IndexError,struct.error) as exc:
                    f.mismatch(i,tag,"malformed_native_record",detail=str(exc))
                    f.absent(i,tag,"projection_incomplete")
    appends=[(tag[1],rec) for (row,tag),rec in records.items() if isinstance(tag,tuple) and tag[0]=="append"]
    for index,rec in appends:
        data=rec["data"]
        if index not in range(len(archive["ids"])) or archive["ids"][index]!=data.get("id") or data.get("pos")!=827+index:
            f.mismatch(None,"public_document","public_append_mismatch",index=index,observed=data)
    if [i for i,_ in appends]!=list(range(len(archive["ids"]))):
        f.absent(None,"public_document","public_append_receipts_missing",measured=len(appends))
    timeline=[]
    for j in range(len(archive["ids"])):
        timeline.append((None,("append",j)))
        if 619<=j<=623:
            timeline.append((j-619,"D"))
        if 618<=j<=622:
            timeline.extend((j-618,tag) for tag in ("model_producer","page_before","page_after","B","block_exit","head_producer",
                PHASES[0],"rep_producer","rep_entry","rep_return",PHASES[1],"page_producer","page_entry","page_return",PHASES[2],"choice_consumer"))
    timeline.extend([(None,"terminal_eos"),(None,"cleanup")])
    previous=None
    for key in timeline:
        if key not in records:
            continue
        seq=records[key].get("journal_seq")
        if type(seq)!=int:
            f.mismatch(key[0],"terminal" if key[0] is None else "B","journal_sequence_invalid")
        elif previous is not None and seq<=previous:
            f.mismatch(key[0],"terminal" if key[0] is None else "B","continuation_event_order",site=str(key[1]))
        previous=seq if type(seq)==int else previous
    for i in range(5):
        required=["page_before","page_after","B","block_exit",*PHASES,"D"]
        serials=[records[i,tag]["journal_seq"] for tag in required if (i,tag) in records]
        if any(type(v)!=int for v in serials) or serials!=sorted(serials):
            f.mismatch(i,"B","non_monotonic_native_transition")
    params_at_field=None
    if (4,"D") in records:
        try:
            graph=Snapshot(records[4,"D"]["data"]["graph"])
            params_at_field=[]
            for router in graph.items(graph.root["routers"]):
                values=graph.as_dict(graph.as_dict(router)["_infer_params"])
                params_at_field.append({k:float.fromhex(v["float_hex"]) if isinstance(v,dict) and "float_hex" in v else v
                                        for k,v in values.items()})
        except (KeyError,ValueError,TypeError,IndexError):
            f.absent(4,"D","retained_parameter_reference_missing")
    for tag in ("terminal_eos","cleanup"):
        if (None,tag) not in records:
            f.absent(None,"terminal","terminal_receipt_missing",field=tag)
        else:
            data=records[None,tag]["data"]
            for key in ("saved_stage0","router_stage0","saved_cfg","retained_params","dash_on","ring","sliding","finish","nxt","length","ids"):
                require(data,key,None,"terminal",f)
            for key,want in (("ids",archive["ids"]),("nxt",1),("length",3385)):
                f.equal(data,key,want,None,"terminal","terminal_branch_mismatch")
            if params_at_field is None:
                f.absent(None,"terminal","retained_parameter_reference_missing")
            else:
                f.equal(data,"retained_params",params_at_field,None,"terminal","retained_parameters_changed")
            if tag=="terminal_eos":
                for key,want in (("finish","length"),("dash_on",True),("page_scope",True)):
                    f.equal(data,key,want,None,"terminal","pre_cleanup_state")
            if tag=="cleanup":
                before=records.get((None,"terminal_eos"),{}).get("data",{})
                for saved in ("saved_cfg","saved_stage0","saved_page_scope","retained_params"):
                    if saved in before:
                        f.equal(data,saved,before[saved],None,"terminal","saved_state_changed")
                    else:
                        f.absent(None,"terminal","pre_cleanup_state_missing",field=saved)
                f.link(data,"page_scope",before,"saved_page_scope",None,"terminal","page_scope_restore")
                f.link(data,"router_stage0",before,"saved_stage0",None,"terminal","router_stage0_restore")
                streamer=data.get("streamer_state",{})
                f.equal(streamer,"token_cache",[],None,"terminal","streamer_flush")
                f.equal(streamer,"next_tokens_are_prompt",True,None,"terminal","streamer_reset")
                for key,want in (("finish","stop"),("dash_on",False)):
                    f.equal(data,key,want,None,"terminal","cleanup_mismatch")
                saved=before.get("saved_cfg")
                if isinstance(saved,list) and len(saved)==2:
                    f.equal(data,"ring",saved[0],None,"terminal","ring_restore")
                    f.equal(data,"sliding",saved[1],None,"terminal","sliding_restore")
                else:
                    f.absent(None,"terminal","saved_decoder_configuration_missing")
                if not isinstance(before.get("saved_stage0"),list) or len(before["saved_stage0"])!=12:
                    f.absent(None,"terminal","saved_router_modes_missing")
                if not isinstance(data.get("retained_params"),list) or len(data["retained_params"])!=12:
                    f.absent(None,"terminal","retained_router_params_missing")
    if any(x["row"] is None and x["phase"]=="public_document" and
           ("runtime" in x["key"] or "admission" in x["key"] or "inventory" in x["key"] or
            "release" in x["key"] or "loaded_module" in x["key"] or "module_origin" in x["key"])
           for x in f.missing+f.conflicts):
        for row in range(5):
            f.absent(row,"B","native_custody_unqualified")
    rows=score_rows(score_e,contract,code_identity(gen),{p:lookup[p][1] for p in PHASES},f,
                    "cuda-fenced-pinned",raw_reference=False)
    for row in rows:
        row["support_size"]=len(row.pop("support"))
    res=f.result(rows)
    doc_conflicts=public_findings.conflicts+[x for x in f.conflicts if x["key"]=="public_append_mismatch"]
    doc_missing=public_findings.missing
    res.update(domain="native_stock",scheduled_rows=5,complete_rows=sum(r["verdict"]=="P" for r in rows),
               scheduled_pairs=1,public_pairs_matched=int(not doc_conflicts and not doc_missing),
               public_verdict="M" if doc_conflicts else "U" if doc_missing else "P")
    return res
