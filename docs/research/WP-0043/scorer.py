"""Read-only verification, independent of the executed native guard functions."""
import math
import struct
from capture import PHASES, digest, pack_word


NEG_INF = bytes.fromhex("000080ff")


def support(history, contract):
    k, width = contract["order"], contract["window"]
    end = len(history)
    banned = set()
    if k > 0 and end >= k:
        suffix = history[end-k+1:]
        for i in range(max(0,end-width), end-k+1):
            if history[i:i+k-1] == suffix:
                banned.add(history[i+k-1])
    return banned


def canonical_state(history, page, enabled):
    if not enabled:
        return {"scanned":0,"marker_cum":0,"page_len":0}
    markers = [i for i,t in enumerate(history) if t == page]
    return {"scanned":len(history),"marker_cum":len(markers),
            "page_len":len(history)-1-markers[-1] if markers else len(history)}


def page_support(vocab, c, state, count):
    marker, eos = c["page"], c["eos"]
    m = state["marker_cum"]
    if count <= 0:
        return set(vocab)
    if m > count:
        return {eos}
    if 0 < c["cap"] <= state["page_len"]:
        return {marker if m < count else eos}
    return set(vocab) - {eos} if m < count else set(vocab)


def f32(word):
    return struct.unpack("<f",word)[0]


class Findings:
    def __init__(self):
        self.conflicts = []
        self.missing = []

    def add(self, missing, row, phase, key, **details):
        target = self.missing if missing else self.conflicts
        target.append({"row":row,"phase":phase,"key":key,**details})

    def mismatch(self,row,phase,key,**details):
        self.add(False,row,phase,key,**details)

    def absent(self,row,phase,key,**details):
        self.add(True,row,phase,key,**details)

    def equal(self, got, name, expected, row,phase,key):
        if not isinstance(got,dict):
            self.mismatch(row,phase,"invalid_object_type",field=name)
            self.absent(row,phase,key+"_missing",field=name)
        elif name not in got:
            self.absent(row,phase,key+"_missing",field=name)
        elif type(got[name]) is not type(expected) or got[name] != expected:
            self.mismatch(row,phase,key,field=name,expected=expected,observed=got[name])

    def link(self,left,name,right,reference,row,phase,key):
        if not isinstance(right,dict) or reference not in right:
            self.absent(row,phase,key+"_reference_missing",field=reference)
        else:
            self.equal(left,name,right[reference],row,phase,key)

    def byte_diff(self,row,phase,key,slot,token,expected,observed,**comparison):
        if expected[:len(observed)] == observed:
            return
        lane = next(i for i in range(len(observed)) if expected[i]!=observed[i])
        self.mismatch(row,phase,key,id=token,lane=lane,dense_offset=4*token+lane,
                      compact_offset=4*slot+lane,expected_le=expected.hex(),observed_le=observed.hex(),**comparison)

    def result(self,rows):
        order_before=["page_before","page_after","B","dash_dispatch","kv_before","kv_after","idx_1d","idx_2d",
                      "idx_main","router_qk","index_after","scores_pre_clean","top_m","route_final",
                      "token_mask","routing_exit","attention_exit","residual","post_rms","expert_route",
                      "expert_dispatch","expert_return","expert_total","shared_output","shared_sum","mixture","block_exit"]
        priority={p:i for i,p in enumerate(order_before+list(PHASES)+["D_selection","D","public_document","terminal"])}
        def order(item):
            row=item.get("row")
            return row if type(row)==int else 10**8, priority.get(str(item.get("phase")),0)
        self.conflicts.sort(key=order)
        self.missing.sort(key=order)
        entries = self.conflicts or self.missing
        per_row = []
        for i,row in enumerate(rows):
            row["verdict"] = ("M" if any(x["row"]==i for x in self.conflicts) else
                              "U" if any(x["row"]==i for x in self.missing) else "P")
            per_row.append(row)
        return {"verdict":"M" if self.conflicts else "U" if self.missing else "P",
                "first_divergent_phase":entries[0]["phase"] if entries else None,
                "conflict_keys":sorted({x["key"] for x in self.conflicts}),
                "missing_keys":sorted({x["key"] for x in self.missing}),
                "conflicts":self.conflicts,"missing":self.missing,"rows":per_row}


def provenance(rec, phase, row, events, cuts, identity, f, transport, expected_bytes):
    event_id = rec.get("copy")
    if not isinstance(event_id,str) or event_id not in events:
        f.absent(row,phase,"copy_ancestry_missing")
        return None
    event = events[event_id]
    for key,want in {**identity,"offset":cuts[phase],"row":row}.items():
        if key not in event:
            f.absent(row,phase,"copy_ancestry_missing",field=key)
        elif event[key]!=want:
            f.mismatch(row,phase,"phase_cut_binding_mismatch",field=key,expected=want,observed=event[key])
    fields = ["seq","frame","receiver","source","source_storage","dest_storage","bytes","run","transport"]
    domain="cpu" if transport=="cpu-owned" else "native"
    for key in fields:
        if key not in event:
            f.absent(row,phase,"copy_ancestry_missing",field=key)
        elif key not in {"run","transport"} and (type(event[key])!=int or event[key]<=0):
            f.mismatch(row,phase,"copy_event_invalid",field=key,observed=event[key])
    if "run" in event and event["run"]!=domain:
        f.mismatch(row,phase,"copy_event_invalid",field="run")
    if "bytes" in event and event["bytes"]!=expected_bytes:
        f.mismatch(row,phase,"copy_event_invalid",field="bytes",expected=expected_bytes,observed=event["bytes"])
    if "seq" in event and event["id"]!=f"{domain}/{row}/{event['seq']}":
        f.mismatch(row,phase,"copy_event_invalid",field="id")
    if event.get("transport") not in (None,transport) or (
            event.get("source_storage") is not None and event["source_storage"]==event.get("dest_storage")):
        f.mismatch(row,phase,"owned_copy_violation")
    if transport=="cuda-fenced-pinned":
        for key in ("producer_stream","copy_stream","completion","complete_before_return","pinned"):
            if key not in event:
                f.absent(row,phase,"copy_ancestry_missing",field=key)
        if (event.get("producer_stream")!=event.get("copy_stream") or
            event.get("completion") is False or event.get("complete_before_return") is False or event.get("pinned") is False):
            f.mismatch(row,phase,"owned_copy_violation")
    return event


def vector(rec,phase,row,vocab,find):
    size = len(vocab)*4
    if "hex" not in rec:
        find.absent(row,phase,"vector_bytes_missing")
        return b""
    try:
        data = bytes.fromhex(rec["hex"])
    except (TypeError,ValueError):
        find.mismatch(row,phase,"vector_encoding_invalid")
        find.absent(row,phase,"vector_bytes_missing")
        return b""
    if rec.get("sha256") is None:
        find.absent(row,phase,"digest_missing")
    elif digest(data)!=rec["sha256"]:
        find.mismatch(row,phase,"digest_mismatch")
    find.equal(rec,"dtype","f32le",row,phase,"dtype_mismatch")
    if len(data)<size or rec.get("complete") is not True:
        find.absent(row,phase,"vector_bytes_missing",available=len(data),required=size)
    if len(data)>size or (len(data)!=size and rec.get("complete") is True):
        find.mismatch(row,phase,"complete_length_mismatch",observed=len(data),required=size)
    return data


def firstmax(data,vocab):
    values = [f32(data[i:i+4]) for i in range(0,len(data),4)]
    if len(values)!=len(vocab) or any(math.isnan(v) for v in values):
        return []
    maximum = max(values)
    return [t for t,v in zip(vocab,values) if v==maximum]


def score_rows(e,c,identity,cuts,find,transport,raw_reference=True):
    vocab = c["vocab"]
    count = c["prompt"].count(c["page"])
    events = {}
    used = {}
    journal_serial=0
    def items(name):
        value=e.get(name,[])
        if not isinstance(value,list):
            find.mismatch(None,"public_document","record_list_invalid",field=name)
            find.absent(None,"public_document","record_list_missing",field=name)
            return []
        return value
    for event in items("events"):
        if not isinstance(event,dict) or not isinstance(event.get("id"),str):
            find.mismatch(None,"public_document","copy_receipt_invalid")
            continue
        sequence=event.get("seq")
        if type(sequence) is int:
            if sequence<=journal_serial:
                find.mismatch(event.get("row"),PHASES[0],"non_monotonic_capture_seq")
            journal_serial=sequence
        if event.get("id") in events:
            find.mismatch(event.get("row"),PHASES[0],"duplicate_copy_event_id")
        events[event.get("id")] = event
    rows_by_id = {}
    for r in items("rows"):
        if not isinstance(r,dict) or type(r.get("index"))!=int:
            find.mismatch(None,"public_document","invalid_row_index")
            continue
        key = r.get("index")
        if key in rows_by_id or key not in range(len(c["histories"])):
            find.mismatch(None,"public_document","invalid_row_index",observed=key)
        else:
            rows_by_id[key]=r
    summaries = []
    for i,history in enumerate(c["histories"]):
        r = rows_by_id.get(i,{})
        entry = f"B{i}_entry_state"
        if transport=="cpu-owned":
            from analogue_guards import _uocr_no_repeat_ngram,_uocr_page_count_guard
            from capture import code_identity
            calls=r.get("guard_calls")
            if calls is None:
                find.absent(i,entry,"guard_calls_missing")
            elif not isinstance(calls,list) or not all(isinstance(v,dict) for v in calls):
                find.mismatch(i,entry,"guard_calls_invalid")
                find.absent(i,entry,"guard_calls_missing")
            else:
                expected_guards=(_uocr_no_repeat_ngram,_uocr_page_count_guard)
                if [v.get("kind") for v in calls]!=["rep","page"]:
                    find.mismatch(i,PHASES[2],"guard_invocation_count")
                for j,(call,fn) in enumerate(zip(calls,expected_guards)):
                    at=PHASES[j+1]
                    find.equal(call,"guard",code_identity(fn.__code__),i,at,"guard_code_mismatch")
                    if call.get("source")!=call.get("result") or type(call.get("source")) is not int:
                        find.mismatch(i,at,"guard_source_binding")

        find.equal(r,"history",history,i,entry,"generation_history_mismatch")
        for name,want in [("page",c["page"]),("eos",c["eos"]),("cap",c["cap"]),("expected_pages",count)]:
            find.equal(r,name,want,i,entry,"guard_config_mismatch")
        state = canonical_state(history,c["page"],count>0)
        for key,want,at in (("before",canonical_state(history[:-1],c["page"],count>0),entry),
                            ("after",state,PHASES[2])):
            for field,val in want.items():
                find.equal(r.get(key,{}),field,val,i,at,
                           "saved_cursor_mismatch" if field=="scanned" else "page_state_mismatch")
        banned = support(history,c)
        allowed = page_support(vocab,c,state,count)-banned
        if not allowed:
            find.mismatch(i,PHASES[2],"empty_support")
        reference = b"".join(pack_word(w) for w in c["raw_words"][i]) if raw_reference else None
        captures = {}
        receipts = {}
        for j,phase in enumerate(PHASES):
            table=r.get("phases",{})
            if not isinstance(table,dict):
                find.mismatch(i,phase,"phase_table_invalid")
                table={}
            rec=table.get(phase)
            if rec is not None and not isinstance(rec,dict):
                find.mismatch(i,phase,"phase_record_invalid")
                rec=None
            if rec is None:
                find.absent(i,phase,"phase_missing")
                continue
            event = provenance(rec,phase,i,events,cuts,identity,find,transport,len(vocab)*4)
            if "fragments" in rec:
                fragments=rec["fragments"] if isinstance(rec["fragments"],list) else []
                fragments=[cid for cid in fragments if isinstance(cid,str)]
                if len(fragments)!=1:
                    find.mismatch(i,phase,"fragmented_capture",copies=fragments)
                for cid in fragments:
                    if cid not in events:
                        find.absent(i,phase,"copy_ancestry_missing",copy=cid)
                    elif cid!=rec.get("copy"):
                        used[cid]=(i,phase)
            if event:
                receipts[phase] = event
                cid = event["id"]
                if cid in used:
                    otherrow,otherphase = used[cid]
                    find.mismatch(otherrow,otherphase,"duplicate_copy_event_id",also=[i,phase])
                else:
                    used[cid] = (i,phase)
            data = vector(rec,phase,i,vocab,find)
            if event and rec.get("complete") is True and len(data)==len(vocab)*4:
                if "payload_sha256" not in event:
                    find.absent(i,phase,"copy_ancestry_missing",field="payload_sha256")
                elif digest(data)!=event["payload_sha256"]:
                    find.mismatch(i,phase,"capture_payload_mismatch")
            captures[phase]=data
            for slot,token in enumerate(vocab):
                start = 4*slot
                word = data[start:start+4]
                if not word:
                    break
                if j==0 and len(word)==4 and not math.isfinite(f32(word)):
                    find.mismatch(i,phase,"raw_non_finite_pos_inf" if f32(word)==math.inf else "raw_non_finite",
                                  id=token,observed_le=word.hex())
                source = reference if j==0 else captures.get(PHASES[j-1])
                if source is None and j==2:
                    source=captures.get(PHASES[0])
                if source is None:
                    source = reference
                expected = source[start:start+4] if source is not None else b""
                if len(expected)<len(word) and j==2 and token in allowed:
                    fallback=captures.get(PHASES[0],reference or b"")
                    expected=fallback[start:start+4]
                if (j==1 and token in banned) or (j==2 and token not in allowed):
                    expected = NEG_INF
                if j==2 and token in allowed and len(word)==4 and not math.isfinite(f32(word)):
                    find.mismatch(i,phase,"allowed_non_finite",id=token)
                if j==2:
                    # Compare both native equations independently. A damaged C1 can be
                    # faithfully preserved at C2 while disagreeing with the composition at C0.
                    baselines=[("captured_C0",captures.get(PHASES[0]))]
                    if reference is not None:
                        baselines.append(("controlled_input",reference))
                    for origin,raw in baselines:
                        composed=NEG_INF if token not in allowed else (raw or b"")[start:start+4]
                        if len(composed)>=len(word):
                            find.byte_diff(i,phase,"post_page_composed_word_mismatch",slot,token,composed,word,
                                           comparison=origin)
                if len(expected)<len(word):
                    continue
                key = ["raw_word_mismatch","post_rep_word_mismatch","post_page_word_mismatch"][j]
                if len(word)==4 and len(expected)==4 and word!=expected and f32(word)==0==f32(expected):
                    key = "signed_zero_winner_corrupted" if token==r.get("y") else "signed_zero_corrupted"
                find.byte_diff(i,phase,key,slot,token,expected,word)
        if transport=="cpu-owned" and isinstance(r.get("guard_calls"),list) and receipts:
            for call in r["guard_calls"]:
                if not isinstance(call,dict):
                    continue
                for phase,event in receipts.items():
                    if call.get("source")!=event.get("source"):
                        find.mismatch(i,phase,"guard_source_binding",field="source")
        pairs = list(receipts.items())
        for (p,a),(q,b) in zip(pairs,pairs[1:]):
            if type(a.get("seq"))==int and type(b.get("seq"))==int and a["seq"]>=b["seq"]:
                find.mismatch(i,p,"non_monotonic_capture_seq",also=q)
            for field in ("source","frame","receiver","run","source_storage"):
                if field in a and field in b and a[field]!=b[field]:
                    find.mismatch(i,p,"source_binding_mismatch",field=field)
        final = captures.get(PHASES[-1],b"")
        ties = firstmax(final,vocab) if len(final)==len(vocab)*4 else []
        if "y" not in r:
            find.absent(i,"D_selection","selection_missing")
        else:
            y=r["y"]
            if ties and y!=ties[0]:
                find.mismatch(i,"D_selection","firstmax_tie_violation" if y in ties else "y_mismatch",
                              expected=ties[0],observed=y)
            if type(y)!=int or y not in allowed:
                find.mismatch(i,"D_selection","selection_outside_support",observed=y,support_size=len(allowed))
        summaries.append({"row":i,"banned":sorted(banned),"support":sorted(allowed),"ties":ties,"y":r.get("y")})
    for cid,event in events.items():
        if cid not in used:
            find.mismatch(event.get("row"),PHASES[0],"orphan_copy_event",copy=cid)
    return summaries


def public_document(doc,expected,f):
    if not isinstance(doc,dict):
        f.mismatch(None,"public_document","public_record_invalid")
        doc={}
    partial=("terminal" not in doc and isinstance(doc.get("ids"),list) and
             isinstance(expected.get("ids"),list) and len(doc["ids"])<len(expected["ids"]))
    for k,want in expected.items():
        if partial and k=="output_tokens" and doc.get(k)==len(doc["ids"]):
            f.absent(None,"public_document","public_count_incomplete",available=doc[k])
            continue
        if partial and k=="markers" and doc.get(k)==[v for v in want if v<len(doc["ids"])]:
            f.absent(None,"public_document","public_markers_incomplete",available=doc[k])
            continue
        if k=="ids":
            if k not in doc:
                f.absent(None,"public_document","public_ids_missing")
                continue
            ids = doc[k]
            if not isinstance(ids,list):
                f.mismatch(None,"public_document","public_ids_invalid")
                f.absent(None,"public_document","public_ids_missing")
                continue
            for i,(x,y) in enumerate(zip(want,ids)):
                if x!=y:
                    f.mismatch(None,"public_document","public_id_mismatch",index=i,expected=x,observed=y)
            if len(ids)<len(want) and "terminal" not in doc:
                f.absent(None,"public_document","public_ids_missing",available=len(ids),required=len(want))
            elif len(ids)!=len(want):
                f.mismatch(None,"public_document","public_length_mismatch",expected=len(want),observed=len(ids))
        elif k in ("text","prompt") and isinstance(want,str) and isinstance(doc.get(k),str):
            a,b=want.encode("utf8"),doc[k].encode("utf8")
            if k=="text" and partial and a.startswith(b) and len(b)<len(a):
                f.absent(None,"public_document","public_text_incomplete",available=len(b))
            elif a!=b:
                offset=next((i for i,(x,y) in enumerate(zip(a,b)) if x!=y),min(len(a),len(b)))
                f.mismatch(None,"public_document","public_utf8_mismatch",field=k,utf8_offset=offset,
                           expected_hex=a[offset:offset+1].hex(),observed_hex=b[offset:offset+1].hex())
        elif k=="terminal":
            if k not in doc:
                f.absent(None,"terminal","terminal_missing")
            elif doc[k]!=want:
                f.mismatch(None,"terminal","terminal_mismatch",expected=want,observed=doc[k])
        else:
            f.equal(doc,k,want,None,"public_document","public_projection_mismatch")


def executed_document(artifact,contract,arm,f):
    doc=artifact.get("document",{})
    if not isinstance(doc,dict):
        f.mismatch(None,"public_document","public_record_invalid",arm=arm)
        doc={}
    try:
        history=list(artifact["prefix"])
        events=artifact["events"]
        limit=artifact["limit"]
        if not isinstance(events,list) or type(limit)!=int or limit<0 or contract["eos"] in history:
            raise ValueError("invalid initial continuation state")
    except (ValueError,TypeError,KeyError) as exc:
        f.absent(None,"public_document","continuation_receipt_missing",arm=arm,reason=str(exc))
        return doc
    stopped=False
    for i,rec in enumerate(events):
        try:
            choices=rec["domain"]
            data=bytes.fromhex(rec["f32le"])
            if (not choices or sorted(set(choices))!=choices or len(data)!=4*len(choices)
                or not all(math.isfinite(v) for v, in struct.iter_unpack("<f",data))):
                raise ValueError("invalid score vector")
            if stopped or i>=limit:
                f.mismatch(None,"terminal","continued_after_stop_or_limit",step=i,arm=arm)
            wanted=firstmax(data,choices)[0]
            for k,v in (("step",i),("previous",history[-1] if history else None),("before",len(history)),("selected",wanted)):
                f.equal(rec,k,v,None,"public_document","continuation_transition")
            stopped=rec.get("selected")==contract["eos"]
            if not stopped:
                history.append(rec["selected"])
            f.equal(rec,"action","stop" if stopped else "append",None,"public_document","continuation_transition")
            f.equal(rec,"after",len(history),None,"public_document","continuation_transition")
        except (ValueError,TypeError,KeyError,IndexError) as exc:
            f.mismatch(None,"public_document","continuation_event_invalid",arm=arm,step=i,reason=str(exc))
            f.absent(None,"public_document","continuation_transition_missing",arm=arm,step=i)
    check={"ids":history,"output_tokens":len(history),"markers":[i for i,t in enumerate(history) if t==contract["page"]]}
    if stopped:
        check["terminal"]="stop"
    elif len(events)==limit:
        check["terminal"]="length"
    elif "terminal" in doc:
        f.mismatch(None,"terminal","unwitnessed_terminal",arm=arm)
    else:
        f.absent(None,"terminal","terminal_missing",arm=arm)
    if "pieces" in artifact:
        try:
            check["text"]="".join(artifact["pieces"][str(t)] for t in history)
        except (ValueError,TypeError,KeyError):
            f.absent(None,"public_document","decoded_pieces_missing",arm=arm)
    public_document(doc,check,f)
    return doc


def score(evidence,contract):
    from analogue import predict, bindings
    from capture import code_identity
    f = Findings()
    if not isinstance(evidence,dict):
        f.mismatch(None,"public_document","invalid_evidence_object")
        evidence={}
    f.equal(evidence,"schema","wp43-cpu/1",None,"public_document","evidence_domain_mismatch")
    f.equal(evidence,"vocab",contract["vocab"],None,"public_document","vocabulary_mismatch")
    f.equal(evidence,"prompt",contract["prompt"],None,"public_document","prompt_mismatch")
    rows = score_rows(evidence,contract,code_identity(predict.__code__),bindings(),f,"cpu-owned")
    if evidence.get("public_source")=="executed_continuation":
        arms=evidence.get("continuation",{})
        if not isinstance(arms,dict):
            f.mismatch(None,"public_document","continuation_arms_invalid")
            arms={}
        got={}
        for arm in ("untouched","observed"):
            payload=arms.get(arm,{})
            if not isinstance(payload,dict):
                f.mismatch(None,"public_document","continuation_arm_invalid",arm=arm)
                payload={}
            got[arm]=executed_document(payload,contract,arm,f)
            public_document(got[arm],contract["document"],f)
        public_document(got["observed"],got["untouched"],f)
        public_document(evidence.get("document",{}),got["observed"],f)
    else:
        public_document(evidence.get("document",{}),contract["document"],f)
    result = f.result(rows)
    result["domain"]="cpu_analogue"
    result["public_source"]=evidence.get("public_source","unspecified")
    result["native_rows_completed"]=0
    return result
