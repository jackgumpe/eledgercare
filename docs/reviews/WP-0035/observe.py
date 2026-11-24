"""Independent instrumentation of the frozen CPU probe and observed event stream."""
from dataclasses import asdict, replace
from hashlib import sha256
import struct
import torch
import matrix
import online

AXIS = ("Alder", "Cedar")


def raw(x):
    assert x.device.type == "cpu" and x.dtype == torch.float32 and x.isfinite().all()
    return x.contiguous().numpy().tobytes()


def digest(x):
    return sha256(raw(x)).hexdigest()


def bits(number):
    return struct.pack("<d", number).hex()


def anchors(model, choices):
    x = torch.stack([matrix.lexical_input("owner", name) for name in choices])
    literal = model.anchor_output(model.anchor_value(x) * model.anchor_gate(x).sigmoid())
    adapter = (model.pop_key(literal) @ model.summary_query) @ model.summary_query.T
    projected = literal + model.pop_value(adapter)
    native = model.anchors("owner", choices)
    assert raw(matrix.direction(projected)) == raw(native)
    centered = matrix.direction(projected - projected.mean(dim=0))
    return native, centered, projected


def statistics(logits, labels, cuts):
    sorted_vals, _ = torch.sort(logits, descending=True)
    top, second = sorted_vals[:2].tolist()
    leaders = [s for s,v in zip(labels, logits.tolist(), strict=True) if v == top]
    on_axis = [logits[labels.index(name)].item() if name in labels else None for name in AXIS]
    avail = None not in on_axis
    return dict(scores=dict(zip(labels, logits.tolist(), strict=True)), candidates=list(labels), leaders=leaders,
                score_hex=struct.pack("<ff", *on_axis).hex() if avail else None,
                top=top, gap=top-second, fp32_gap=(sorted_vals[0]-sorted_vals[1]).item(),
                score_pass=bool(sorted_vals[0]>=cuts[0]), gap_pass=bool(sorted_vals[0]-sorted_vals[1]>=cuts[1]),
                tied=len(leaders)>1, margin=on_axis[0]-on_axis[1] if avail else None)


def advance_control(state, model, events):
    applied = []
    for e in events:
        previous = state.controller.depth
        state.controller.apply(e)
        state.registry.update(e)
        depth = state.controller.depth
        rank = None
        if e.kind == "CONFIRM_POP" and depth < previous:
            state.matrices, kept = model.pop(state.matrices, previous)
            rank = int(kept.sum()) if kept is not None else None
        applied.append(dict(kind=e.kind,before_depth=previous,after_depth=depth,pop_rank=rank,
                            held_here=state.controller.held[depth]))
    return applied


def altered(model, state, k, v, a, b, rho, freeze):
    depth = state.controller.depth
    if rho == 1 and not freeze:
        return model.write(state.matrices, depth, k, v, a, b)
    lane = 0 if model.flat else depth
    old = state.matrices[lane]
    eff = torch.ones_like(a) if freeze else a
    residual = v - rho * (eff * (old @ k))
    update = eff * old + b * torch.outer(residual, k)
    return (*state.matrices[:lane], update, *state.matrices[lane+1:])


def lookup(model, state, query, basis, projected, tags, cuts, names, phase, ctx):
    response = model.read(state.matrices, state.controller.depth, query, "owner")
    unit = matrix.direction(response)
    stacked = torch.stack(state.matrices)
    registry = {k:list(v) for k,v in state.registry.choices().items()}
    context = dict(**ctx, query_sha256=digest(query), read_sha256=digest(response), matrix_sha256=digest(stacked),
                   owner_columns_sha256=digest(stacked[:,:,:32]), registry=registry, zero=response.norm().item() <= matrix.EPS,
                   depth=state.controller.depth, scope=state.controller.ambiguous(), held=list(state.controller.held),
                   fault=state.controller.fault, eligible=registry["owner"] == list(names))
    rows = {}
    for read in tags:
        logits = basis[read] @ unit
        if read == "R0":
            assert raw(logits) == raw(matrix.direction(projected) @ unit)
        row = dict(**context, phase=phase, read=read, **statistics(logits, names, cuts))
        row["eligible_decision"] = (row["leaders"][0] if row["eligible"] and not row["scope"] and
                    not row["zero"] and not row["tied"] and row["score_pass"] and row["gap_pass"] else None)
        rows[read] = row
    return rows


def full_attempt(model, state, q, target, cuts, rows):
    item = matrix.attempt(model, state, q, target)
    outs = {}
    for read,row in rows.items():
        scores = item.scores.copy()
        if "owner" in scores:
            assert tuple(row["candidates"]) == item.choices["owner"]
            if read == "R0":
                assert raw(scores["owner"]) == struct.pack("<"+"f"*len(row["scores"]),*row["scores"].values())
            else:
                scores["owner"] = torch.tensor([row["scores"][v] for v in item.choices["owner"]])
        alt = replace(item, scores=scores)
        outputs = {f:{"scores":dict(zip(item.choices[f], t.tolist(), strict=True)), "f32le":raw(t).hex(),
                      "read_sha256":digest(model.read(state.matrices,state.controller.depth,q,f))}
                   for f,t in scores.items()}
        outs[read] = dict(typed=alt.typed(cuts), fields=outputs, zero=item.zero, reason=item.reason,
                          summary_target=item.summary_target, summary_zero=item.summary_zero,
                          ptr=list(target.ptr),literal=target.literal,query_sha256=digest(q))
    return outs


def stream_for(case, member, windows):
    folder = "captures" if case["task"] == "A" else "cal"
    return [(key, windows[(folder,key)]) for key in member["keys"]]


def symbolic(stream):
    state = online.Discrete()
    for ordinal, (_,window) in enumerate(stream,1):
        state.window(window,ordinal)
    return online.single(state.outputs), state.outputs


def binder(model, write, tags, stream, all_steps, cuts):
    root = online.Registry()
    targets = []
    for ordinal,(_,window) in enumerate(stream,1):
        for span in window.spans:
            for e in online.identify(span, ordinal):
                if ordinal == 1 and e.kind == "DIRECTORY_OWNERS":
                    root.update(e)
                if e.kind == "TARGET":
                    targets.append(e)
    if all_steps:
        assert len(targets)==1
    names = root.choices()["owner"]
    assert len(names)>=2
    native, center, proj = anchors(model,names)
    basis = {"R0":native,"R1":center}
    anchor = dict(directory=list(names), projected_hex=raw(proj).hex(), raw_norms=proj.norm(dim=1).tolist(),
                  native_sha256=digest(native), centered_sha256=digest(center),
                  raw_sha256=digest(proj), centered_antisymmetry_max=float((center[0]+center[1]).abs().max()) if len(names)==2 else None)
    if len(names)==2:
        anchor.update(native_axis_norm=(native[0]-native[1]).norm().item(), raw_difference_norm=(proj[0]-proj[1]).norm().item(),
                      native_centered_axis_cos=float(torch.dot(matrix.direction(native[0]-native[1]), matrix.direction(center[0]-center[1]))))
    state = matrix.NeuralState(model.zero())
    step = 0
    output, attempts, writes = [], {r:[] for r in tags}, []
    target_query = None
    if all_steps:
        first, = targets
        target_query = model.project(stream[first.ptr[0]-1][1])[2][first.ptr[2]]
        rows = lookup(model,state,target_query,basis,proj,tags,cuts,names,"initial",dict(step=0,ptr=None,events=[],checkpoint=["initial"]))
        output.extend(rows.values())
    consumed = designated = saw_target = False
    for ordinal,(window_key,window) in enumerate(stream,1):
        keys,vals,queries,alpha,beta = model.project(window)
        for span in window.spans:
            i = span.index
            ptr = [ordinal,span.page,i]
            events = list(online.identify(span,ordinal))
            applied = advance_control(state,model,events)
            kinds = [e.kind for e in events]
            depth = state.controller.depth
            root_decls = [a for a in applied if a["kind"]=="OPEN_LEDGER" and a["before_depth"]==0]
            target_events = [e for e in events if e.kind=="TARGET"]
            designate = False
            if not consumed and not saw_target and root_decls:
                consumed = True
                designate = len(root_decls)==kinds.count("OPEN_LEDGER")==1 and depth==0 and not state.controller.ambiguous()
                designated = designate
            downstream = designated and not designate and depth==0 and "OPEN_LEDGER" not in kinds
            rho = .5 if ((designate and write!="W0") or (downstream and write in ("W2a","W2b"))) else 1.
            freeze = downstream and write=="W2b"
            for e in target_events:
                q = queries[i]
                if all_steps:
                    assert raw(q)==raw(target_query)
                ctx = dict(step=step,ptr=ptr,events=applied,checkpoint=["tpost"],window=window_key,text=span.text)
                # Terminal R1 uses exactly the choices currently available to the native target attempt.
                actual = state.registry.choices()["owner"]
                if actual != names and len(actual)>=2:
                    na,ce,pr=anchors(model,actual)
                    obs=lookup(model,state,q,{"R0":na,"R1":ce},pr,tags,cuts,actual,"native_pre",ctx)
                else:
                    obs=lookup(model,state,q,basis,proj,tags,cuts,names,"native_pre",ctx)
                values = full_attempt(model,state,q,e,cuts,obs)
                for read,row in obs.items():
                    attempts[read].append(values[read])
                    if all_steps or "owner" in values[read]["fields"]:
                        output.append(row)
                saw_target=True
            if not all_steps and target_events and len(attempts[tags[0]]) == len(targets):
                return output, attempts, writes, anchor
            state.matrices = altered(model,state,keys[i],vals[i],alpha[i],beta[i],rho,freeze)
            step+=1
            cp=[]
            if all_steps and step in (7,8,9,11,12):
                cp.append("write"+str(step))
            if designate: cp.append("designated_declaration")
            if "OPEN_CHILD" in kinds: cp.append("child_entry")
            if any(a["after_depth"]<a["before_depth"] for a in applied): cp.append("pop_commit")
            if ordinal==1 and i==len(window.spans)-1: cp.append("opening_end")
            if target_events: cp.append("post_target_write")
            update=dict(step=step,ptr=ptr,window=window_key,text=span.text,events=applied,checkpoint=cp,
                        designate=designate,downstream_root=downstream,depth_after=depth,rho=rho,retention=1. if freeze else alpha[i].item(),
                        alpha=alpha[i].item(), beta=beta[i].item(), alpha_beta=alpha[i].item()*beta[i].item())
            writes.append(update)
            if all_steps:
                obs=lookup(model,state,target_query,basis,proj,tags,cuts,names,"post",
                           {k:update[k] for k in ("step","ptr","window","text","events","checkpoint")})
                output.extend(obs.values())
            if target_events and all_steps:
                return output, attempts, writes, anchor
    return output, attempts, writes, anchor


def crossed(model, openings, query, controls, prior):
    evidence={}
    for letter,(prefix,_) in openings.items():
        for donor,(_,window) in openings.items():
            name=letter+donor
            state=matrix.NeuralState(model.zero())
            k,v,_,a,b=model.project(prefix)
            for i in range(7):
                advance_control(state,model,list(online.identify(prefix.spans[i],1)))
                state.matrices=model.write(state.matrices,state.controller.depth,k[i],v[i],a[i],b[i])
            dk,dv,_,da,db=model.project(window)
            events=list(online.identify(window.spans[7],1))
            assert [e.kind for e in events]==["OPEN_LEDGER"]
            advance_control(state,model,events)
            state.matrices=altered(model,state,dk[7],dv[7],da[7],db[7],.5,False)
            assert state.registry.choices()["owner"] == AXIS
            read=model.read(state.matrices,state.controller.depth,query,"owner")
            score=model.anchors("owner",AXIS) @ matrix.direction(read)
            old=controls["M1/relative/0.50/"+name]
            orig=prior[name]
            assert raw(score).hex()==old["score_f32le"]==orig["score_f32le"]
            assert digest(read)==orig["read_sha256"] and digest(torch.stack(state.matrices))==orig["matrix_sha256"]
            sa,sc=score.tolist()
            assert sa-sc==orig["margin"] and ((sa>sc) if donor=="A" else (sc>sa))
            evidence[name]=dict(score_hex=raw(score).hex(),matrix_sha256=orig["matrix_sha256"],read_sha256=digest(read),
                                query_sha256=digest(query),margin=sa-sc,donor=donor,prefix=letter)
    return evidence
