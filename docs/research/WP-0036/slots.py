"""Structural FP32 instance and conditional observed-text pathway. No learned parameters."""
from dataclasses import dataclass,field
import struct
from archive import sha
from arithmetic import Table,minor
from directory import decode

ZEROS = bytes(512)


def rounded(x):
    return struct.unpack("<f",struct.pack("<f",x))[0]


@dataclass
class Slot:
    v:bytearray=field(default_factory=lambda:bytearray(512))
    valid:bool=False
    text:str|None=None
    source:dict|None=None

    def write(self,projection,text,source,eligible=True):
        if self.valid:
            old=struct.unpack("<128f",self.v)
            incoming=struct.unpack("<128f",projection)
            self.v[:]=struct.pack("<128f",*(rounded(a+rounded(.5*rounded(b-a))) for a,b in zip(old,incoming)))
        else:
            self.v[:]=projection
        self.valid=True
        if eligible:
            self.text,self.source=text,source

    def witness(self):
        text=(self.text or "").encode()
        serial=bytes(self.v)+bytes([self.valid])+struct.pack("<I",len(text))+text+b"\0"
        return dict(vector_sha256=sha(self.v),full_sha256=sha(serial),valid=self.valid,text=self.text,
                    confidence=None,confidence_provenance="unmeasured",text_source=self.source)


@dataclass
class Frame:
    slots:dict=field(default_factory=lambda:{k:Slot() for k in ("owner","unit")})
    header:list=field(default_factory=lambda:[Slot() for _ in range(32)])
    ring:list=field(default_factory=lambda:[Slot() for _ in range(16)])
    records:list=field(default_factory=lambda:[None]*16)
    cursor:int=0
    last_child:dict|None=None
    pending:dict|None=None
    rows:int=0
    title:str|None=None


class Stack:
    def __init__(self,online):
        self.online=online
        self.frames=[Frame() for _ in range(8)]
        vectors=[s.v for f in self.frames for s in (*f.slots.values(),*f.header,*f.ring)]
        assert len(set(map(id,vectors)))==400 and sum(map(len,vectors))==204800
        self.controller=online.Controller()
        self.registry=online.Registry()

    def read(self,key,committed=True):
        for level in reversed(range(self.controller.depth+1)):
            f=self.frames[level]
            s=f.header[key] if isinstance(key,int) else f.slots[key]
            if s.valid and (not committed or s.text is not None):
                return level,s
        return None,None

    def capture(self,e,item,tag):
        ptr=list(e.ptr)
        return dict(tag=tag,ptr=ptr,raw_slice_sha256=item["sha256"],byte_range=item["byte_range"])

    def apply(self,e,item,tag):
        kind=e.kind
        before=self.controller.depth
        frame=self.frames[before]
        source=self.capture(e,item,tag)
        self.registry.update(e)
        self.controller.apply(e)
        after=self.controller.depth
        if kind in ("OPEN_LEDGER","DECLARE_UNIT","AMEND_UNIT","TENTATIVE_CLOSE"):
            lines=[line.partition(":") for line in item["observed"].splitlines()]
            cue=self.online.key(e.literal.partition(":")[0])
            values=[v.strip() for label,sep,v in lines if sep and self.online.key(label)==cue]
            assert len(values)==1, (tag,e.ptr,cue)
            value,=values
            if kind=="TENTATIVE_CLOSE":
                if before: frame.pending=dict(text=value,source=source,minor=minor(value),projection=item["projected"])
            else:
                field="owner" if kind=="OPEN_LEDGER" else "unit"
                frame.slots[field].write(item["projected"],value,source)
        elif kind=="HEADER":
            cells,=Table(item["observed"]).rows
            assert tuple(cells)==e.value and len(cells)<=32
            for i,cell in enumerate(cells):
                # The archive has one pooled row, so each observed column gets the same projected row.
                frame.header[i]=Slot()
                frame.header[i].write(item["projected"],cell,source)
        elif kind=="OPEN_CHILD" and after>before:
            self.frames[after]=Frame(title=e.literal)
        elif kind=="CONFIRM_POP" and after<before:
            dest=self.frames[after]
            pending=frame.pending
            record=dict(title=frame.title,rows=frame.rows,
                        subtotal=pending["text"] if pending else None,
                        subtotal_source=pending["source"] if pending else None,validator_status="unmeasured",
                        attrs={k:v.witness() for k,v in frame.slots.items()},close=source)
            dest.records[dest.cursor]=record
            dest.ring[dest.cursor]=Slot()
            dest.ring[dest.cursor].write(pending["projection"] if pending else item["projected"],record["subtotal"],source)
            dest.cursor=(dest.cursor+1)%16
            dest.last_child=record
            self.frames[before]=Frame()
        return (before,after)

    def post(self,e,eta):
        scope=self.controller.ambiguous()
        candidates=self.registry.choices()
        attrs={}
        for field in ("owner","unit"):
            level,slot=self.read(field)
            attrs[field]=dict(level=level,source=slot.source if slot else None,
                              **decode(slot.text if slot else None,candidates[field],eta,scope))
        reasons=[reason for col in attrs.values() for reason in col["reasons"]]
        _,header=self.read(1)
        hits=[v for v in candidates["column"] if header and self.online.key(v)==self.online.key(header.text)]
        if len(hits)!=1 or len(candidates["column"])<2: reasons.append("unresolved_column")
        status=None
        if e.value[0].casefold()=="maint-summary":
            row=self.frames[self.controller.depth].last_child
            subtotal=minor(row["subtotal"]) if row and row["subtotal"] is not None else None
            observed=minor(e.value[1])
            if observed is None or subtotal is None: reasons.append("unobserved_subtotal")
            else: status="BALANCED" if observed==subtotal else "UNBALANCED"
        typed=(dict(type="ABSTAIN",reason=reasons[0]) if reasons else
               dict(type="Posting",owner=attrs["owner"]["decision"],unit=attrs["unit"]["decision"],column=hits[0],subtotal_status=status))
        return dict(eta=eta,fields=attrs,typed=typed,reasons=reasons,scope=scope,
                    measured_confidence=None,end_to_end="unmeasured",target=list(e.ptr))


def source_descriptor(span,item,wi,key,events):
    return dict(bbox=list(span.box),block=span.block_kind,cells=list(span.cells),
                events=[dict(kind=e.kind,literal=e.literal,value=list(e.value) if isinstance(e.value,tuple) else e.value) for e in events],
                feature_f32le_sha256=item["feature_sha256"],key=key,kind=span.kind,metadata_sha256=item["metadata_span_sha256"],
                page=(wi-1)*3+span.page,ptr=[wi,span.page,span.index],raw_slice_sha256=item["sha256"],text=span.text,
                text_sha256=sha(span.text.encode()))


def stream(route,physical,online):
    stack=Stack(online)
    m2=online.Discrete()
    for wi,tag in enumerate(route["tags"],1):
        m2.window(online.Window(tuple(i["canonical"] for i in physical[tag]["spans"]),None),wi)
    typed=online.single(m2.outputs)
    timeline=[dict(phase="initial",step=0,source=None,events=[],witness=stack.frames[0].slots["owner"].witness(),depth=0)]
    terminals=[]
    done=False
    step=0
    for wi,(tag,key) in enumerate(zip(route["tags"],route["keys"],strict=True),1):
        for item in physical[tag]["spans"]:
            span=item["canonical"]
            events=list(online.identify(span,wi))
            descriptor=source_descriptor(span,item,wi,key,events)
            snap=dict(source=descriptor,events=[e.kind for e in events])
            if any(e.kind=="TARGET" for e in events):
                tgt,=[e for e in events if e.kind=="TARGET"]
                assert len(events)==1
                terminals=[stack.post(tgt,eta) for eta in (0,.5)]
                timeline.append(dict(phase="native_pre",step=step,depth=stack.controller.depth,witness=stack.frames[0].slots["owner"].witness(),**snap))
                timeline.append(dict(phase="post",step=step+1,depth=stack.controller.depth,witness=None,excluded="reference_only_target_write",**snap))
                done=True
                break
            for e in events:
                stack.apply(e,item,tag)
            if span.kind=="row" and not events:
                stack.frames[stack.controller.depth].rows+=1
            step+=1
            timeline.append(dict(phase="post",step=step,depth=stack.controller.depth,witness=stack.frames[0].slots["owner"].witness(),**snap))
        if done: break
    assert sum(e["event"]=="TARGET" for e in m2.trace)==int(done)
    if not done:
        terminals=[dict(eta=e,typed=online.abstain("no_target"),reasons=["no_target"],fields={},target=None,
                        scope=stack.controller.ambiguous(),end_to_end="no_target",measured_confidence=None) for e in (0,.5)]
    return dict(timeline=timeline,terminals=terminals,native=typed,native_targets=[list(e["ptr"]) for e in m2.trace if e["event"]=="TARGET"])


def e4(online):
    s=Stack(online)
    root=s.frames[0].slots["owner"]
    root.write(struct.pack("<128f",*([1.]*128)),"parent",None)
    s.controller.depth=1
    child=s.frames[1].slots["owner"]
    child.write(struct.pack("<128f",*([2.]*128)),"child",None,eligible=False)
    old_level,old=s.read("owner",committed=False)
    new_level,new=s.read("owner")
    return dict(scope="synthetic first low-confidence child DECL",root=root.witness(),child=child.witness(),
                original_level=old_level,original_text=old.text,committed_lookup_level=new_level,committed_lookup_text=new.text)
