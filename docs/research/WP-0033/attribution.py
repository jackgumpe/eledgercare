"""Four full-window input swaps. Account independently for raw linear and normalized effects."""
import math
from dataclasses import asdict

import experiment
import matrix
import online
import torch

from bindings import hybrid_window, opened
from metrics import EPS, LITERALS, compare_read, digest, effect, limit, observe, pack, parity, raw, sign

CONTRASTS = {
    "pooled_at_A":(("AA",1),("CA",-1)), "pooled_at_C":(("AC",1),("CC",-1)),
    "box_at_A":(("AA",1),("AC",-1)), "box_at_C":(("CA",1),("CC",-1)),
    "diagonal":(("AA",1),("CC",-1)), "interaction":(("AA",1),("CA",-1),("AC",-1),("CC",1)),
}


def analyze(contract,model,sources,windows,anchors,cuts,controls,table,checks,out,parity_rows):
    assert model.write_value.bias is None
    weights=model.write_value.weight.double()
    assert weights.shape==(128,1312)
    wa,wc=anchors.double().unbind()
    probes=dict(zip(LITERALS,(wa,wc,wa-wc),strict=True))
    out.update(rows=[],raw_effects={},normalized_effects={})
    fields={}
    for cell in ("AA","CC","AC","CA"):
        g,c=cell
        window,block=hybrid_window(windows,cell)
        k_all,v_all,q_all,a_all,b_all=model.project(window)
        k,v,a,b=k_all[7],v_all[7],a_all[7],b_all[7]
        projected=dict(zip(("key","value","alpha","beta"),(k,v,a,b),strict=True))
        if g==c:
            assert all(raw(x)==raw(y) for x,y in zip(projected.values(),sources[g]["tensors"],strict=True))
        events=list(online.identify(window.spans[7],1))
        assert events==sources[g]["events"]
        state,binding=opened(sources[g],events,True)
        state.matrices=model.write(state.matrices,0,k,v,a,b)
        assert all(lane.count_nonzero().item()==0 for lane in state.matrices[1:])
        q=sources[g]["query"]
        native,vec,obs=observe(model,state,q,anchors,cuts)
        if g==c:
            ref=controls["0"+g]["native"]
            assert all(native[k]==ref[k] for k in ("matrix_sha256","read_f32le","score_f32le","owner_columns_sha256"))
        f=window.features[7].double()
        enc=block[7,1280:].double()
        # Both products operate on promoted raw inputs and promoted frozen weight slices.
        vf=weights[:,:1280]@f
        vb=weights[:,1280:]@enc
        full=v.double()
        checks.vector(cell+"/split_value",full,vf+vb)
        u=q[:32].double()/(q[:32].double().norm()+EPS)
        z=float(k[:32].double()@u)
        t=float(b)*z
        vn=float(full.norm())
        denom=abs(t)*vn+EPS
        scaled_read=t*full
        prediction=compare_read(cell,native,vec,obs,scaled_read,anchors,checks)
        h_y=float(probes["h"]@scaled_read)
        checks.scalar(cell+"/scaled_numerator",obs["numerator"],h_y)
        align={}
        for name,w in probes.items():
            hf,hb=float(w@vf),float(w@vb)
            hw=float(w@full)
            score=t*hw/denom
            observed=native["margin"] if name=="h" else native["scores"][name]
            checks.scalar(cell+"/"+name+"/raw_split",hw,hf+hb)
            checks.scalar(cell+"/"+name+"/finite_epsilon_score",observed,score)
            align[name]=dict(pooled=hf,box=hb,total=hw,split_total=hf+hb,raw_signed=sign(hw),
                             empirical_score=observed,finite_epsilon_score=score,score_signed=sign(observed))
        input_binding={"pooled_source":g,"box_source":c,"full_shape":list(block.shape),
                       "all_pooled_rows_sha256":digest(raw(window.features)),
                       "pooled_row":pack(window.features[7]),"box999":list(window.spans[7].box),
                       "box999_canonical_json_sha256":digest(experiment.json_bytes(window.spans[7].box)),
                       "encoded_box":pack(block[7,1280:]),"full_block_sha256":digest(raw(block)),
                       "full_spans_sha256":digest(experiment.json_bytes([asdict(s) for s in window.spans])),
                       "rows_sha256":[digest(raw(row)) for row in block],"event":asdict(events[0])}
        row=dict(arm="M3",mode="hybrid",point=contract["hybrid"]["point"],cell=cell,status="observed",discrete=binding,
                 input_binding=input_binding,projected={n:pack(x) for n,x in projected.items()},
                 unused_declaration_query_sha256=digest(raw(q_all[7])),eventual_query=pack(q),u=pack(u),z=z,
                 alpha=float(a),beta=float(b),t=sign(t),value_norm=vn,absolute_times_value_norm=abs(t)*vn,
                 epsilon=EPS,denominator=denom,effective_epsilon_in_value_units=EPS/abs(t) if t else None,
                 signed_multiplier_on_raw_dot=t/denom,finite_epsilon_factor_on_unit_value_direction=(t*vn)/denom,
                 epsilon_shrink_magnitude=abs(t)*vn/denom,pooled_value=pack(vf),box_value=pack(vb),
                 fp64_predicted_read=pack(scaled_read),alignments=align,native=native,observed_fp64=obs,prediction=prediction,
                 signed_numerator=sign(obs["numerator"]))
        out["rows"].append(row)
        fields[cell]=(row,f,enc)
        parity_rows.append(parity("M3","hybrid",contract["hybrid"]["point"],cell,native,obs))

    pooled_shift=weights[:,:1280]@(fields["AA"][1]-fields["CC"][1])
    box_shift=weights[:,1280:]@(fields["AA"][2]-fields["CC"][2])
    out["delta_pooled_value"]=pack(pooled_shift)
    out["delta_box_value"]=pack(box_shift)
    for name,w in probes.items():
        align={c:row["alignments"][name] for c,(row,_,_) in fields.items()}
        F,B=float(w@pooled_shift),float(w@box_shift)
        raw_values={c:x["total"] for c,x in align.items()}
        splits={c:x["split_total"] for c,x in align.items()}
        effects={k:effect(raw_values,coeffs,splits) for k,coeffs in CONTRASTS.items()}
        identities={"diagonal":F+B,"interaction":0,"pooled_at_A":F,"pooled_at_C":F,"box_at_A":B,"box_at_C":B}
        for k,pred in identities.items():
            delta=effects[k]
            checks.scalar(f"raw/{name}/{k}/block_difference",delta["value"],pred,delta["budget"])
        out["raw_effects"][name]=dict(independent_pooled_F=F,independent_box_B=B,
                                      pooled_signed=sign(F,effects["pooled_at_A"]["zero_budget"]),
                                      box_signed=sign(B,effects["box_at_A"]["zero_budget"]),effects=effects)
        native_values={c:x["empirical_score"] for c,x in align.items()}
        predicted={c:x["finite_epsilon_score"] for c,x in align.items()}
        effects={k:effect(native_values,coeffs,predicted) for k,coeffs in CONTRASTS.items()}
        for k,d in effects.items():
            checks.scalar("normalized/"+name+"/"+k,d["value"],d["predicted"],d["budget"])
        vals={k:d["value"] for k,d in effects.items()}
        path_f=vals["pooled_at_A"]+vals["box_at_C"]
        path_b=vals["box_at_A"]+vals["pooled_at_C"]
        i_f=vals["pooled_at_A"]-vals["pooled_at_C"]
        i_b=vals["box_at_A"]-vals["box_at_C"]
        for k,path in (("pooled_then_box",path_f),("box_then_pooled",path_b)):
            checks.scalar(name+"/"+k,vals["diagonal"],path,effects["diagonal"]["budget"])
        for k,ipath in (("pooled_path_interaction",i_f),("box_path_interaction",i_b)):
            checks.scalar(name+"/"+k,vals["interaction"],ipath,effects["interaction"]["budget"])
        diag_ref=table["M3_D0"] if name=="h" else table["M3_candidate_shifts"][name]
        checks.scalar(name+"/archive_delta",vals["diagonal"],diag_ref,effects["diagonal"]["budget"])
        symmetric_F=(vals["pooled_at_A"]+vals["pooled_at_C"])/2
        symmetric_B=(vals["box_at_A"]+vals["box_at_C"])/2
        out["normalized_effects"][name]=dict(effects=effects,pooled_then_box=path_f,box_then_pooled=path_b,
                                              pooled_interaction=i_f,box_interaction=i_b,symmetric_F=symmetric_F,symmetric_B=symmetric_B)
