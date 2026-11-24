"""Native controller owns target-before-write, pop and scope. Observe its write boundary."""
import hashlib
import math
import struct
from dataclasses import replace

import matrix
import online
import torch

AXIS = ("Alder", "Cedar")
CUTS = (1.0, 0.1)

def raw(tensor):
    assert tensor.device.type == "cpu" and tensor.dtype == torch.float32
    return tensor.detach().contiguous().numpy().tobytes()

def digest(tensor):
    return hashlib.sha256(raw(tensor)).hexdigest()

def f64(value):
    return struct.pack("<d", value).hex()

class Readout:
    def __init__(self, model, names, centered):
        self.names = tuple(names)
        assert len(names) >= 2
        x = torch.stack([matrix.lexical_input("owner", v) for v in names])
        literal = model.anchor_output(model.anchor_value(x) * model.anchor_gate(x).sigmoid())
        adapter = (model.pop_key(literal) @ model.summary_query) @ model.summary_query.T
        self.raw = literal + model.pop_value(adapter)
        self.native = model.anchors("owner", names)
        assert raw(matrix.direction(self.raw)) == raw(self.native)
        self.anchors = {"R0":self.native}
        if centered:
            self.anchors["R1"] = matrix.direction(self.raw - self.raw.mean(dim=0, keepdim=True))

    def details(self):
        z = self.raw.double()
        norms = z.norm(dim=1)
        metrics = {}
        if len(z) == 2:
            n = z / norms[:,None]
            axis = n[0] - n[1]
            theta = math.acos(float((n[0] @ n[1]).clamp(-1, 1)))
            metrics = dict(angle_radians=theta, equal_norm_theoretical_gain=2/axis.norm().item(),
                           unequal_norm_inverse_difference=1/float(norms[0])-1/float(norms[1]))
            if "R1" in self.anchors:
                c = self.anchors["R1"].double()
                actual = c[0]-c[1]
                metrics.update(centered_antipodal_residual_norm=(c[0]+c[1]).norm().item(),
                               predicted_equal_norm_axis_residual=(actual-metrics["equal_norm_theoretical_gain"]*axis).norm().item(),
                               measured_axis_gain=float(actual.norm()/axis.norm()))
        return dict(choices=self.names, raw_f32le=raw(self.raw).hex(), norms=norms.tolist(),
                    anchors_f32le={k:raw(v).hex() for k,v in self.anchors.items()}, **metrics)

def owner_record(logits, names):
    assert torch.isfinite(logits).all()
    scores = dict(zip(names, logits.tolist(), strict=True))
    leaders = [k for k,v in scores.items() if v == max(scores.values())]
    top = logits.topk(2).values
    gap = top[0].item()-top[1].item()
    axis = [scores.get(k) for k in AXIS]
    return dict(directory=names, scores=scores, full_score_hex=raw(logits).hex(), leaders=leaders,
                score_hex=struct.pack("<ff", *axis).hex() if None not in axis else None,
                top=top[0].item(), gap=gap, gate_gap_f32=(top[0]-top[1]).item(), score_pass=bool(top[0]>=CUTS[0]),
                gap_pass=bool(top[0]-top[1]>=CUTS[1]), signed_margin=axis[0]-axis[1] if None not in axis else None)

def damp(matrices, flat, depth, k, v, alpha, beta, freeze):
    lane = 0 if flat else depth
    old = matrices[lane]
    effective = torch.ones_like(alpha) if freeze else alpha
    residual = v - 0.5 * (effective * (old @ k))
    new = effective * old + beta * torch.outer(residual, k)
    return matrices[:lane] + (new,) + matrices[lane+1:]

def scan(windows):
    registry = online.Registry()
    targets = []
    for wi,window in enumerate(windows,1):
        for s in window.spans:
            for e in online.identify(s,wi):
                if e.kind == "DIRECTORY_OWNERS":
                    registry.update(e)
                elif e.kind == "TARGET":
                    targets.append(e)
    return registry.choices()["owner"], targets

class Replay:
    def __init__(self, model, write, windows, tags, task, centered, capture_cross=False):
        self.model, self.write_arm, self.task = model, write, task
        self.state = matrix.NeuralState(model.zero())
        self.step, self.seen, self.designated, self.target_seen = 0, False, False, False
        self.rows, self.updates, self.attempts, self.cross = [], [], [], {}
        self.capture_cross = capture_cross
        self.window = self.wi = self.index = None
        self.tags = tags
        names, targets = scan(windows)
        self.reader = Readout(model,names,centered)
        self.query = None
        if task == "A":
            event, = targets
            wi, _, i = event.ptr
            self.query = model.project(windows[wi-1])[2][i]
            self.sample("initial", self.state.matrices, self.query, None, [], ["initial"])
        for self.wi,self.window in enumerate(windows,1):
            self.index = 0
            view = self.window
            if task == "A" and self.wi == targets[0].ptr[0]:
                i = targets[0].ptr[2] + 1
                view = online.Window(view.spans[:i], view.features[:i])
            matrix.advance(self,self.state,view,self.wi)
            assert self.index == len(view.spans)
            if task == "A" and self.target_seen:
                break
        assert len(targets) == len(self.state.attempts) == len(self.attempts)
        self.final_outputs = {read:online.single([a[read]["typed"] for a in self.attempts]) for read in self.reader.anchors}
        assert self.final_outputs["R0"] == matrix.result(self.state,CUTS)

    def __getattr__(self, name):
        return getattr(self.model,name)

    def project(self, view):
        projected = self.model.project(self.window)
        self.window_queries = projected[2]
        return projected

    def sample(self, phase, matrices, query, ptr, events, labels):
        depth = self.state.controller.depth
        response = self.model.read(matrices,depth,query,"owner")
        direction = matrix.direction(response)
        registry = self.state.registry.choices()
        matrices_full = torch.stack(matrices)
        row = dict(phase=phase,actual_step=self.step,ptr=ptr,checkpoints=labels,event_kinds=events,
                   depth=depth,scope=self.state.controller.ambiguous(),registry=registry,
                   eligible=registry["owner"] == self.reader.names, zero=response.norm().item() <= matrix.EPS,
                   query_sha256=digest(query),read_sha256=digest(response),matrix_sha256=digest(matrices_full),
                   owner_columns_sha256=digest(matrices_full[:,:,:32]))
        observed = {}
        for read,anchors in self.reader.anchors.items():
            logits = anchors @ direction
            observed[read] = logits
            self.rows.append(dict(**row,read=read,**owner_record(logits,self.reader.names)))
        return observed

    def write(self, matrices, depth, k, v, a, b):
        span = self.window.spans[self.index]
        ptr = [self.wi,span.page,span.index]
        assert span.index == self.index and depth == self.state.controller.depth
        events = list(online.identify(span,self.wi))
        kinds = [e.kind for e in events]
        trace = self.state.trace[-len(events):] if events else []
        assert [e["event"] for e in trace] == kinds and all(list(e["ptr"]) == ptr for e in trace)
        root_declarations = [e for e in trace if e["event"] == "OPEN_LEDGER" and e["depth_after"] == 0]
        first = bool(root_declarations) and not self.seen and not self.target_seen
        downstream = self.designated and depth == 0 and "OPEN_LEDGER" not in kinds
        if first:
            self.seen = True
            self.designated = (kinds.count("OPEN_LEDGER") == 1 and depth == 0 and not self.state.controller.ambiguous()
                               and "TARGET" not in kinds)
        declaration = first and self.designated
        do_damp = (self.write_arm != "W0" and declaration) or (self.write_arm in ("W2a","W2b") and downstream)
        freeze = self.write_arm == "W2b" and downstream
        labels = []
        if self.task == "A" and self.step+1 in (7,8,9,11,12):
            labels.append("write_"+str(self.step+1))
        labels.extend(k for k in kinds if k in ("OPEN_CHILD","CONFIRM_POP"))
        if declaration:
            labels.append("root_declaration")
        if self.capture_cross and declaration:
            self.cross = dict(incoming=matrices,operands=(k,v,a,b),query=self.query,depth=depth,events=kinds,
                              declaration_literal=events[kinds.index("OPEN_LEDGER")].literal,ptr=ptr)
        for i in range(kinds.count("TARGET")):
            item = self.state.attempts[len(self.attempts)]
            q = self.window_queries[self.index]
            if self.query is not None:
                assert raw(q) == raw(self.query)
            owner = item.scores.get("owner")
            numeric = {}
            if owner is not None:
                assert tuple(item.choices["owner"]) == self.reader.names
                numeric = self.sample("native_pre",matrices,q,ptr,kinds,["tpost"])
                assert raw(owner) == raw(numeric["R0"])
            elif self.task == "A":
                raise ValueError("unexpected Task A terminal without native scores")
            variants = {}
            for read in self.reader.anchors:
                scores = dict(item.scores)
                if owner is not None:
                    scores["owner"] = numeric[read]
                actual = replace(item,scores=scores)
                variants[read] = dict(typed=actual.typed(CUTS),reason=actual.reason,zero=actual.zero,
                                       summary_target=actual.summary_target,summary_zero=actual.summary_zero,choices=actual.choices,
                                       field_scores_hex={name:raw(vals).hex() for name,vals in scores.items()},
                                       field_scores={name:dict(zip(actual.choices[name],vals.tolist(),strict=True)) for name,vals in scores.items()},
                                       ptr=ptr,actual_step=self.step)
            self.attempts.append(variants)
            self.target_seen = True
        updated = damp(matrices,self.model.flat,depth,k,v,a,b,freeze) if do_damp else self.model.write(matrices,depth,k,v,a,b)
        self.step += 1
        after = self.target_seen
        self.updates.append(dict(step=self.step,ptr=ptr,window_key=self.tags[self.wi-1],span_text=span.text,
                                 events=kinds,depth=depth,first_root_open=first,designated=declaration,downstream=downstream,
                                 alpha=a.item(),effective_alpha=1. if freeze else a.item(),beta=b.item(),rho=.5 if do_damp else 1.,
                                 alpha_beta=float(a)*float(b),after_target=after))
        if self.task == "A":
            if after:
                labels.append("post_target")
            if self.wi == 1 and self.index+1 == len(self.window.spans):
                labels.append("first_window_end")
            self.sample("post",updated,self.query,ptr,kinds,labels)
        self.index += 1
        return updated

def cross_controls(model, natives, expected):
    out = []
    for prefix in AXIS:
        src = natives[prefix]
        for donor in AXIS:
            dst = natives[donor]
            cell = prefix[0]+donor[0]
            a, d = src.cross, dst.cross
            assert a["depth"] == d["depth"] == 0 and d["events"] == ["OPEN_LEDGER"]
            assert d["declaration_literal"] == "Ledger: "+donor and a["ptr"] == d["ptr"] == [1,1,7]
            matrices = damp(a["incoming"],True,0,*d["operands"],False)
            original = model.write(a["incoming"],0,*d["operands"])
            baseline_logits = src.reader.native @ matrix.direction(model.read(original,0,a["query"],"owner"))
            assert raw(baseline_logits).hex() == expected["M1/relative/1/"+cell]["score_f32le"]
            response = model.read(matrices,0,a["query"],"owner")
            score = src.reader.native @ matrix.direction(response)
            ref = expected["M1/relative/0.50/"+cell]
            record = owner_record(score,src.reader.names)
            assert record["score_hex"] == ref["score_f32le"] and record["leaders"] == [donor]
            assert record["signed_margin"] == ref["observed"]["margin"]
            out.append(dict(cell=cell,expected_hex=ref["score_f32le"],original_hex=raw(baseline_logits).hex(),prefix_matrix=digest(torch.stack(a["incoming"])),
                            donor_ptr=d["ptr"],result_matrix=digest(torch.stack(matrices)),query_sha256=digest(a["query"]),
                            read_sha256=digest(response),**record))
    return out
