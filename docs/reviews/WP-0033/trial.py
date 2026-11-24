"""WP-0033 review only. A measurement consumes exactly one declaration."""
import copy
import dataclasses
import hashlib
import io
import json
import struct
import numpy as np
import torch
import online
import matrix
import audit

NAMES=("Alder","Cedar")
CELLS=("AA","AC","CA","CC")
OWNER=dict(A="Alder",C="Cedar")


def raw(t):
    assert t.dtype==torch.float32 and t.device.type=="cpu" and t.isfinite().all()
    return t.contiguous().numpy().astype("<f4",copy=False).tobytes()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def record(data):
    return sha((json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode())


def tensor(b,shape):
    t=torch.frombuffer(bytearray(b),dtype=torch.float32).reshape(shape)
    assert raw(t)==b
    return t


def hashed(t):
    return sha(raw(t))


def box_sha(box):
    return sha(struct.pack("<4i",*box))


def fields(model,window):
    # The model's own full-window projection order affects native FP32 bytes.
    k,v,_,a,b=model.project(window)
    return k[7],v[7],a[7],b[7]


class Measurement:
    def __init__(self,arm,doc,read,weights,windows,captures,bindings,cuts,anchor_id,prior):
        self.arm,self.doc,self.windows,self.prior=arm,doc,windows,prior
        self.model=matrix.Memory(flat=arm=="M1").eval()
        self.model.load_state_dict(torch.load(io.BytesIO(weights),map_location="cpu",weights_only=True),strict=True)
        assert all(p.device.type=="cpu" and p.dtype==torch.float32 for p in self.model.parameters())
        self.anchors=self.model.anchors("owner",NAMES)
        assert doc["thresholds"]==cuts==[1.,.1] and tuple(doc["owner_order"])==NAMES and doc["status"]=="completed"
        self.cuts=cuts
        assert hashed(self.anchors)==anchor_id
        self.snaps={}; self.params={}; self.source={}
        for name in NAMES:
            key=name[0]
            src=doc["sources"][name]
            snap=src["snapshot"]
            shape=(1 if arm=="M1" else 8,128,128)
            assert tuple(snap["shape"])==shape and snap["dtype"]=="float32-le"
            full=tensor(read(snap["matrices_file"]),shape)
            assert hashed(full)==snap["matrix_sha256"]==src["write7_read"]["matrix_sha256"]
            assert record(snap["discrete"])==snap["discrete_sha256"]
            self.snaps[key]=full
            window=windows[name]
            bundle=src["donor"]
            assert tuple(window.features.shape)==(16,1280) and len(window.spans)==16
            assert list(window.features.shape)==bundle["full_window_shape"]
            assert hashed(window.features)==captures[name]["members"]["pooled.f32"]
            assert src["donor_input_sha256"]==record(bundle) and bundle["window_rgb_key"]==captures[name]["rgb_key"]
            assert bundle["pointer"]==[1,1,7] and bundle["owner"]==name
            span=window.spans[7]
            expected=(53,486 if key=="A" else 487,339,515)
            assert span.index==7 and span.page==1 and span.text==bundle["literal"]=="Ledger: "+name
            assert span.box==expected==tuple(bundle["bbox"]) and hashed(window.features[7])==bundle["feature_sha256"]
            event,=online.identify(span,1)
            assert event==online.Event("OPEN_LEDGER",name,(1,1,7),"Ledger: "+name)
            assert record([dataclasses.asdict(event)])==record(bundle["events"])
            projected=fields(self.model,window)
            assert [raw(t).hex() for t in projected]==[bundle["projected_f32le"][x] for x in ("key","value","alpha","beta")]
            assert sha(b"".join(map(raw,projected)))==bundle["projection_sha256"]
            self.params[key]=projected
            qbytes=bytes.fromhex(src["frozen_query_f32le"])
            assert raw(self.anchors).hex()==src["ordered_anchors_f32le"]
            assert sha(qbytes)==src["write7_read"]["query_sha256"]
            assert src["write7_read"]["ordered_anchor_sha256"]==anchor_id
            for horizon in (12,30):
                hist=bindings[f"{arm}/{horizon}"]
                assert bytes.fromhex(hist[name]["query_f32le"])==qbytes and hist["anchor_sha256"]==anchor_id
                assert hist[name]["keys"][0]==captures[name]["rgb_key"] and hist[name]["binder"]==captures[name]["binders"][horizon]
            self.query=tensor(qbytes,(128,))
            self.source[key]=dict(snapshot=snap,query_f32le=qbytes.hex(),anchor_f32le=raw(self.anchors).hex(),
                           bbox=span.box,bbox_i32le_sha256=box_sha(span.box),
                           window_metadata_sha256=captures[name]["members"]["metadata.json"],
                           pooled_window_sha256=hashed(window.features),pooled_row_sha256=[hashed(r) for r in window.features],
                           donor_input_sha256=record(bundle),projected={s:raw(t).hex() for s,t in zip(("k","v","alpha","beta"),projected)})
        assert self.source["A"]["query_f32le"]==self.source["C"]["query_f32le"]
        assert self.source["A"]["snapshot"]["discrete"]==self.source["C"]["snapshot"]["discrete"]
        self.u,self.axes=audit.directions(self.query,self.anchors)

    def start(self,prefix,event_owner,empty):
        frozen=self.snaps[prefix]
        base=frozen.clone()
        assert base.data_ptr()!=frozen.data_ptr() and hashed(base)==self.source[prefix]["snapshot"]["matrix_sha256"]
        if empty:
            base.zero_()
            assert base.shape[0]==8 and torch.count_nonzero(base)==0
        original=self.source[prefix]["snapshot"]["discrete"]
        d=copy.deepcopy(original)
        ctrl=online.Controller(**d["controller"])
        r=d["registry"]
        directory=online.Registry(owners=set(r["owners"]),units=set(r["units"]),schemas=set(map(tuple,r["schemas"])))
        event,=online.identify(self.windows[OWNER[event_owner]].spans[7],1)
        ctrl.apply(event)
        directory.update(event)
        d["controller"]=dataclasses.asdict(ctrl)
        d["registry"]={key:sorted(list(x) if isinstance(x,tuple) else x for x in vals) for key,vals in vars(directory).items()}
        assert d==original and not ctrl.ambiguous() and ctrl.depth==0 and directory.choices()["owner"]==NAMES
        return tuple(base.unbind()),dict(recipient=prefix,event=dataclasses.asdict(event),discrete_sha256=record(d),
                                         incoming_matrix_sha256=hashed(base),directory=directory.choices()["owner"],depth=ctrl.depth)

    def observe(self,updated,route):
        read=self.model.read(updated,route["depth"],self.query,"owner")
        scores=self.anchors @ matrix.direction(read)
        margin=scores[0].item()-scores[1].item()
        norm=read.norm()
        zero=bool(norm.item()<=matrix.EPS)
        result=matrix.Attempt(choices={"owner":NAMES},scores={"owner":scores},zero=zero).typed(self.cuts)
        # All scheduled observations concern only an owner ranking at write eight.
        parity=dict(score_f32le=raw(scores).hex(),read_sha256=hashed(read),matrix_sha256=hashed(torch.stack(updated)),
                    numerator=audit.scalar(self.axes[-1] @ audit.v64(read)),margin=margin,
                    read_norm=audit.scalar(np.linalg.norm(audit.v64(read))))
        native_n=torch.dot(self.anchors[0]-self.anchors[1],read)
        gap=(scores[0]-scores[1]).abs()
        row=dict(status="completed",parity=parity,routing=route,native_read_f32le=raw(read).hex(),
                 scores=dict(zip(NAMES,scores.tolist())),native_gap=gap.item(),native_gap_f32le=raw(gap).hex(),
                 native_numerator=native_n.item(),native_numerator_f32le=raw(native_n).hex(),native_norm=norm.item(),
                 native_norm_f32le=raw(norm).hex(),rank="tie" if margin==0 else ("Alder" if margin>0 else "Cedar"),
                 zero_read=zero,top_pass=bool(scores.max()>=self.cuts[0]),gap_pass=bool(gap>=self.cuts[1]),
                 owner_threshold_result=result)
        return read,scores,row

    def native_control(self,cell,row,history):
        key=cell if self.arm=="M1" else "0"+cell[0]
        prev=self.doc["cells" if self.arm=="M1" else "empty_cells"][key]
        hist=history[self.arm][key]
        independent=self.prior[key]["binding"]
        p=row["parity"]
        assert p["matrix_sha256"]==prev["read"]["matrix_sha256"]==independent["updated_sha256"]
        assert p["read_sha256"]==prev["read"]["read_sha256"]==independent["native_read_sha256"]
        assert row["native_read_f32le"]==prev["read"]["read_f32le"]==independent["native_read_f32le"]
        assert p["score_f32le"]==prev["read"]["score_f32le"]==hist["native_score_f32le"]==independent["score_f32le"]
        assert p["margin"]==prev["read"]["margin"]==hist["native_margin"]
        assert prev["recipient_before_event"]==prev["after_donor_hook"]==dict(
            matrix_sha256=row["routing"]["incoming_matrix_sha256"],discrete_sha256=row["routing"]["discrete_sha256"])
        assert row["routing"]["directory"]==NAMES and row["zero_read"]==prev["read"]["zero_read"]
        assert row["top_pass"]==prev["read"]["top_score_pass"] and row["gap_pass"]==prev["read"]["top_gap_pass"]
        return dict(archive_key=key,observed=p,archive_expected={k:prev["read"][k] for k in ("score_f32le","read_sha256","matrix_sha256")},
                    archive_discrete_sha256=prev["read"]["discrete_sha256"],passed=True)

    def m1(self,jobs,c,history,prior,rows,controls):
        coefficients={}; components={}; grid={}; witnesses={}
        tables=history["M1"]
        betas={key:x[-1].item() for key,x in self.params.items()}
        roots=audit.m1_roots(tables,betas,c)
        for cell in CELLS:
            i,j=cell
            old,route=self.start(i,j,False)
            params=self.params[j]
            native=self.model.write(old,0,*params)
            _,_,row=self.observe(native,route)
            controls[cell]=self.native_control(cell,row,history)
            parts,recorded=audit.m1_components(old[0],params,self.u,self.axes,prior[cell]["components"],tables[cell])
            components[cell]=parts
            coefficients[cell]=recorded
        for job in jobs:
            if job[0]!="M1":
                continue
            _,mode,point,cell=job
            i,j=cell
            old,route=self.start(i,j,False)
            k,v,a,b=self.params[j]
            request=c[mode][point]
            gain=torch.tensor(request,dtype=torch.float32)
            # Freeze exact recipient-specific, non-in-place FP32 operation orders.
            if mode=="absolute":
                new=(a*old[0]+b*torch.outer(v,k))-gain*torch.outer(a*(old[0]@k),k)
                rho=gain.item()/b.item()
                eta=gain.item()
            else:
                residual=v-gain*(a*(old[0]@k))
                new=a*old[0]+b*torch.outer(residual,k)
                rho=gain.item()
                eta=rho*b.item()
            read,scores,row=self.observe((new,),route)
            R,V,E=components[cell]
            predicted=(R+V)+rho*E
            checks=audit.read_checks(read,scores,predicted,self.axes)
            checks["native32_norm"]=audit.compare(row["native_norm"],checks["norm"]["predicted"])
            checks["native32_numerator"]=audit.compare(row["native_numerator"],checks["numerator"]["predicted"])
            P,L=tables[cell]["omitted_numerator"],tables[cell]["term_numerators"][2]
            affine=audit.signed(audit.compare(row["parity"]["numerator"],P+rho*L))
            if mode=="relative" and point=="1":
                assert row["parity"]==controls[cell]["observed"]
            if mode=="relative" and point=="0":
                omitted=prior[cell]["omitted"]
                checks["omitted_endpoint"]={key:audit.compare(obs,omitted[key]) for key,obs in (
                    ("numerator",row["parity"]["numerator"]),("margin",row["parity"]["margin"]),("norm",row["parity"]["read_norm"]))}
            expected="positive" if j=="A" else "negative"
            row.update(gain_mode=mode,requested=request,executed=gain.item(),gain_f32le=raw(gain).hex(),
                       realized_eta=eta,realized_rho=rho,truth=OWNER[j],signed_rank=affine["sign"],
                       donor_correct=affine["sign"]==expected,affine=affine,checks=checks)
            rows[job]=row
            grid.setdefault((mode,point),{})[cell]=row
        contrasts={}
        for (mode,point),group in grid.items():
            key=mode+"/"+point
            contrasts[key]={}
            for i in ("A","C"):
                a,cc=(group[i+j] for j in ("A","C"))
                obs={m:audit.combination([(1,x),(-1,y)]) for m,x,y in (
                    ("numerator",a["checks"]["numerator"],cc["checks"]["numerator"]),
                    ("margin",a["checks"]["scores"]["margin"],cc["checks"]["scores"]["margin"]))}
                if mode=="relative" and point in ("0","1"):
                    bound=obs["margin"]["budget"]
                    ref=history["M1_donor_contrasts"][i]["omitted_margin" if point=="0" else "native_margin"]
                    obs["historical_margin"]=audit.compare(obs["margin"]["observed"],ref,bound)
                contrasts[key][i]=obs
            witnesses[key]=dict(original_twins_correct=all(group[s]["donor_correct"] for s in ("AA","CC")),
                                four_cells_correct=all(r["donor_correct"] for r in group.values()),
                                ranks={s:r["signed_rank"] for s,r in group.items()})
        return dict(roots=roots,coefficients=coefficients,fixed_prefix_contrasts=contrasts,rank_decisions=witnesses)

    def hybrid(self,g,b):
        original=self.windows[OWNER[g]]
        source=self.windows[OWNER[b]]
        spans=list(original.spans)
        spans[7]=dataclasses.replace(spans[7],box=source.spans[7].box)
        window=dataclasses.replace(original,spans=tuple(spans))
        assert window.features is original.features and window.spans[:7]+window.spans[8:]==original.spans[:7]+original.spans[8:]
        assert dataclasses.replace(window.spans[7],box=original.spans[7].box)==original.spans[7]
        params=fields(self.model,window)
        blocks=matrix.blocks(window.spans,window.features)
        assert tuple(blocks.shape)==(16,1312) and raw(blocks[:,:1280])==raw(original.features)
        box=audit.v64(blocks[7,1280:])
        phases=np.outer(np.asarray(spans[7].box)/999.,[1.,2.,4.,8.])*2*np.pi
        math_box=np.concatenate((np.sin(phases).ravel(),np.cos(phases).ravel()))
        encoding=audit.vector(box,math_box)
        identities=dict(pooled_window_sha256=hashed(window.features),pooled_rows_sha256=[hashed(r) for r in window.features],
                        declaration_feature_sha256=hashed(window.features[7]),source_box_source=b,box_i32le=list(spans[7].box),
                        box_i32le_sha256=box_sha(spans[7].box),window_boxes_sha256=sha(b"".join(struct.pack("<4i",*s.box) for s in spans)),
                        span_records_sha256=record([dataclasses.asdict(s) for s in spans]),
                        blocks_f32le_sha256=hashed(blocks),encoded_box_f32le=raw(blocks[7,1280:]).hex(),
                        projection_f32le=dict(zip(("k","v","alpha","beta"),[raw(t).hex() for t in params])),
                        matches_historical_donor=(g==b),encoding=encoding)
        assert identities["pooled_rows_sha256"]==self.source[g]["pooled_row_sha256"]
        if g==b:
            assert all(raw(t)==raw(r) for t,r in zip(params,self.params[g],strict=True))
        return params,identities,audit.v64(window.features[7]),box

    def m3(self,jobs,history,rows,controls):
        weight=audit.v64(self.model.write_value.weight)
        assert self.model.write_value.bias is None and weight.shape==(128,1312)
        completed={}
        for cell in ("AA","CC","AC","CA"):
            g,b=cell
            job=("M3","hybrid","empty",cell)
            assert job in jobs
            params,inputs,feature,box=self.hybrid(g,b)
            old,route=self.start(g,g,True)
            updated=self.model.write(old,0,*params)
            assert all(hashed(x)==hashed(y) for x,y in zip(old[1:],updated[1:],strict=True))
            native,scores,row=self.observe(updated,route)
            if g==b:
                controls[cell]=self.native_control(cell,row,history)
            checks,analysis=audit.m3_account(params,self.u,self.axes,feature,box,weight,native,scores)
            checks["native32_norm"]=audit.compare(row["native_norm"],checks["norm"]["predicted"])
            checks["native32_numerator"]=audit.compare(row["native_numerator"],checks["numerator"]["predicted"])
            if g==b:
                historical=history["M3"]["0"+g]
                checks["native_scale"]=audit.compare(analysis["t"]["observed"],historical["gain"])
            row.update(inputs=inputs,checks=checks,m3=analysis)
            rows[job]=row
            completed[cell]=row
        effects=audit.factorial(completed)
        for label in audit.LABELS:
            delta=effects[label]["normalized"]["diagonal"]
            ref=history["M3_D0"] if label=="margin" else (
                completed["AA"]["scores"][label]-completed["CC"]["scores"][label])
            delta["historical_control"]=audit.compare(delta["observed"],ref,delta["budget"])
            if label!="margin":
                delta["historical_fp64"]=audit.compare(delta["observed"],history["M3_candidate_shifts"][label],delta["budget"])
        return dict(conditional_effects=effects,eventual_query_u_f64le=audit.packed(self.u),
                    axes_f64le=audit.packed(self.axes),axes_shape=list(self.axes.shape))
