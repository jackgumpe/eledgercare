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
        if name not in got:
            self.absent(row,phase,key+"_missing",field=name)
        elif type(got[name]) is not type(expected) or got[name] != expected:
            self.mismatch(row,phase,key,field=name,expected=expected,observed=got[name])

    def byte_diff(self,row,phase,key,slot,token,expected,observed):
        if expected[:len(observed)] == observed:
            return
        lane = next(i for i in range(len(observed)) if expected[i]!=observed[i])
        self.mismatch(row,phase,key,id=token,lane=lane,dense_offset=4*token+lane,
                      compact_offset=4*slot+lane,expected_le=expected.hex(),observed_le=observed.hex())

    def result(self,rows):
        order_before=["page_before","page_after","B","dash_dispatch","kv_before","kv_after","idx_1d","idx_2d",
                      "idx_main","router_qk","index_after","scores_pre_clean","top_m","route_final",
                      "token_mask","routing_exit","attention_exit","residual","post_rms","expert_route",
                      "expert_dispatch","expert_return","expert_total","shared_output","shared_sum","mixture","block_exit"]
        priority={p:i for i,p in enumerate(order_before+list(PHASES)+["D_selection","D","public_document","terminal"])}
        def order(item):
            return item["row"] if item["row"] is not None else 10**8, priority.get(item["phase"],0)
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


def provenance(rec, phase, row, events, cuts, identity, f, transport):
    event_id = rec.get("copy")
    if not event_id or event_id not in events:
        f.absent(row,phase,"copy_ancestry_missing")
        return None
    event = events[event_id]
    for key,want in {**identity,"offset":cuts[phase],"row":row}.items():
        if key not in event:
            f.absent(row,phase,"copy_ancestry_missing",field=key)
        elif event[key]!=want:
            f.mismatch(row,phase,"phase_cut_binding_mismatch",field=key,expected=want,observed=event[key])
    fields = ["seq","frame","source","source_storage","dest_storage","bytes","run","transport"]
    for key in fields:
        if key not in event:
            f.absent(row,phase,"copy_ancestry_missing",field=key)
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
    for event in e.get("events",[]):
        if event.get("id") in events:
            find.mismatch(event.get("row"),PHASES[0],"duplicate_copy_event_id")
        events[event.get("id")] = event
    rows_by_id = {}
    for r in e.get("rows",[]):
        key = r.get("index")
        if key in rows_by_id or key not in range(len(c["histories"])):
            find.mismatch(None,"public_document","invalid_row_index",observed=key)
        else:
            rows_by_id[key]=r
    summaries = []
    for i,history in enumerate(c["histories"]):
        r = rows_by_id.get(i,{})
        entry = f"B{i}_entry_state"
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
            rec = r.get("phases",{}).get(phase)
            if rec is None:
                find.absent(i,phase,"phase_missing")
                continue
            event = provenance(rec,phase,i,events,cuts,identity,find,transport)
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
                if source is None:
                    source = reference
                expected = source[start:start+4] if source is not None else b""
                if (j==1 and token in banned) or (j==2 and token not in allowed):
                    expected = NEG_INF
                if j==2 and token in allowed and len(word)==4 and not math.isfinite(f32(word)):
                    find.mismatch(i,phase,"allowed_non_finite",id=token)
                if len(expected)<len(word):
                    continue
                key = ["raw_word_mismatch","post_rep_word_mismatch","post_page_word_mismatch"][j]
                if len(word)==4 and len(expected)==4 and word!=expected and f32(word)==0==f32(expected):
                    key = "signed_zero_winner_corrupted" if token==r.get("y") else "signed_zero_corrupted"
                find.byte_diff(i,phase,key,slot,token,expected,word)
        pairs = list(receipts.items())
        for (p,a),(q,b) in zip(pairs,pairs[1:]):
            if a["id"]!=b["id"] and isinstance(a.get("seq"),int) and isinstance(b.get("seq"),int) and a["seq"]>=b["seq"]:
                find.mismatch(i,p,"non_monotonic_capture_seq",also=q)
            for field in ("source","frame","run","source_storage"):
                if field in a and field in b and a[field]!=b[field]:
                    find.mismatch(i,p,"source_binding_mismatch",field=field)
        final = captures.get(PHASES[-1],b"")
        ties = firstmax(final,vocab) if len(final)==len(vocab)*4 else []
        if "y" not in r:
            find.absent(i,"D_selection","selection_missing")
        elif ties and r["y"]!=ties[0]:
            find.mismatch(i,"D_selection","firstmax_tie_violation" if r["y"] in ties else "y_mismatch",
                          expected=ties[0],observed=r["y"])
        elif allowed and r["y"] not in allowed:
            find.mismatch(i,"D_selection","y_mismatch",observed=r["y"])
        summaries.append({"row":i,"banned":sorted(banned),"support":sorted(allowed),"ties":ties,"y":r.get("y")})
    return summaries


def public_document(doc,expected,f):
    for k,want in expected.items():
        if k=="ids":
            if k not in doc:
                f.absent(None,"public_document","public_ids_missing")
                continue
            ids = doc[k]
            for i,(x,y) in enumerate(zip(want,ids)):
                if x!=y:
                    f.mismatch(None,"public_document","public_id_mismatch",index=i,expected=x,observed=y)
            if len(ids)<len(want) and "terminal" not in doc:
                f.absent(None,"public_document","public_ids_missing",available=len(ids),required=len(want))
            elif len(ids)!=len(want):
                f.mismatch(None,"public_document","public_length_mismatch",expected=len(want),observed=len(ids))
        elif k in ("text","prompt") and isinstance(want,str) and isinstance(doc.get(k),str):
            a,b=want.encode("utf8"),doc[k].encode("utf8")
            if a!=b:
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


def score(evidence,contract):
    from analogue import predict, bindings
    from capture import code_identity
    f = Findings()
    f.equal(evidence,"schema","wp43-cpu/1",None,"public_document","evidence_domain_mismatch")
    f.equal(evidence,"vocab",contract["vocab"],None,"public_document","vocabulary_mismatch")
    f.equal(evidence,"prompt",contract["prompt"],None,"public_document","prompt_mismatch")
    rows = score_rows(evidence,contract,code_identity(predict.__code__),bindings(),f,"cpu-owned")
    public_document(evidence.get("document",{}),contract["document"],f)
    result = f.result(rows)
    result["domain"]="cpu_analogue"
    result["native_rows_completed"]=0
    return result
