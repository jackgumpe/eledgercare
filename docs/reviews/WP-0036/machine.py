"""Native span grammar, scope and actual-byte slot replay. No truth is passed in."""
from copy import deepcopy
import html
import re
import struct

from inputs import packed, sha
from metric import rank
from money import cents

ZERO = bytes(512)
BLOCK = struct.Struct("<128f")
F32 = struct.Struct("<f")


def clean(s):
    return " ".join(html.unescape(s).split())


def events(row, wi):
    s = row["record"]
    if s["kind"] == "row":
        cells = [clean(c if isinstance(c,str) else c["text"]) for c in s["cells"]]
        if cells and cells[0].casefold()=="item" and len(cells)>=2:
            yield "HEADER", cells, s["text"]
        if cells and cells[0].casefold() in ("posting","maint-summary"):
            yield "TARGET", cells, s["text"]
        return
    if s["block_kind"].casefold()=="table":
        return
    for text in s["text"].splitlines():
        line = clean(text)
        label, colon, value = line.partition(":")
        k, v = label.strip().casefold(), clean(value)
        if colon and v:
            if wi==1 and s["page"]==1 and k in ("owners","units","schema"):
                choices = [clean(p) for p in v.split("/")]
                if len(choices)>=2 and all(choices):
                    yield "DIRECTORY_"+k.upper(), choices, line
            elif k in ("ledger","unit","unit amendment","schedule subtotal"):
                yield dict(ledger="OPEN_LEDGER",unit="DECLARE_UNIT", **{"unit amendment":"AMEND_UNIT",
                           "schedule subtotal":"TENTATIVE_CLOSE"})[k],v,line
        elif k in ("supporting schedule","schedule closed"):
            yield ("OPEN_CHILD" if k=="supporting schedule" else "CONFIRM_POP"),None,line


def single(v):
    return F32.unpack(F32.pack(v))[0]


class Frame:
    def clear(self):
        self.bank[:] = bytes(len(self.bank))
        self.marks = {}
        self.ring = [None]*16
        self.cursor = self.count = self.rows = 0
        self.last_total = self.summary = self.table = self.title = None
        self.held = False

    def __init__(self):
        # Contiguous independent regions inside one frame. No child is a view of its parent.
        self.bank = bytearray(50*512)
        self.clear()

    def vector(self, slot):
        return bytes(self.bank[slot*512:(slot+1)*512])

    def put(self, slot, data, meta, blend=False):
        assert 0<=slot<50 and len(data)==512
        if blend and slot in self.marks:
            prior, obs = BLOCK.unpack(self.vector(slot)), BLOCK.unpack(data)
            data = BLOCK.pack(*(single(a+single(0.5*single(b-a))) for a,b in zip(prior,obs)))
        self.bank[slot*512:(slot+1)*512] = data
        self.marks[slot] = deepcopy(meta)

    def owner_witness(self):
        vector = self.vector(0)
        mark = self.marks.get(0)
        value = mark["value"] if mark else ""
        string = value.encode()
        wire = vector + bytes([int(mark is not None)]) + struct.pack("<I",len(string)) + string + b"\0"
        return dict(vector=sha(vector),slot=sha(wire),valid=bool(mark),text=value,confidence=None,
                    declaration=mark["ptr"] if mark else None)

    def append(self, child, vector, ptr):
        # Fixed summary record. The embedding is a structural diagnostic, here the CLOSE projection.
        pos = self.cursor
        rec = dict(title=child.title,rows=child.rows,subtotal=child.last_total,
                   status=None,attrs=[deepcopy(child.marks.get(k)) for k in (0,1)],
                   attr_vectors=[sha(child.vector(k)) for k in (0,1)],ptr=ptr)
        self.ring[pos] = rec
        self.put(34+pos,vector,rec)
        self.cursor, self.count = (pos+1)%16, min(16,self.count+1)
        self.summary = child.last_total


class Machine:
    def __init__(self):
        self.frames = [Frame() for _ in range(8)]
        assert len({id(f.bank) for f in self.frames})==8 and sum(len(f.bank) for f in self.frames)==204800
        self.depth = 0
        self.fault = ""
        self.directory = {k:set() for k in ("owner","unit","column")}

    @property
    def frame(self):
        return self.frames[self.depth]

    def scope(self):
        if self.fault or not self.depth:
            return self.fault
        return "shadow_hold" if self.frame.held else "open_child_no_return"

    def inherited(self, slot):
        for layer in reversed(self.frames[:self.depth+1]):
            mark = layer.marks.get(slot)
            if mark and mark.get("value") is not None:
                return mark

    def step(self, kind, value, literal, ptr, row):
        f = self.frame
        vec = row["feature"][:512]
        if kind.startswith("DIRECTORY"):
            if kind=="DIRECTORY_SCHEMA":
                self.directory["column"].add(value[1])
            else:
                self.directory[{"DIRECTORY_OWNERS":"owner","DIRECTORY_UNITS":"unit"}[kind]].update(value)
        elif kind in ("OPEN_LEDGER","DECLARE_UNIT","AMEND_UNIT"):
            raw_lines = row["raw"].splitlines()
            matches = [r.partition(":")[2].strip() for r in raw_lines if clean(r)==literal]
            assert len(matches)==1
            f.put(int(kind!="OPEN_LEDGER"),vec,dict(value=matches[0],native=value,ptr=ptr,rawsha=row["rawsha"]),True)
        elif kind=="HEADER":
            assert len(value)<=32
            f.table = value
            for i, hdr in enumerate(value):
                f.put(2+i,vec,dict(value=hdr,ptr=ptr))
        elif kind=="OPEN_CHILD":
            if self.depth==7:
                self.fault="scope_overflow"
            else:
                self.depth+=1
                self.frame.clear()
                self.frame.title = literal
        elif kind=="TENTATIVE_CLOSE" and self.depth:
            f.last_total = dict(value=value,ptr=ptr,rawsha=row["rawsha"])
            f.held = True
        elif kind=="CONFIRM_POP":
            if self.depth:
                self.frames[self.depth-1].append(f,vec,ptr)
                f.clear()
                self.depth-=1
            else:
                self.fault="unmatched_pop"

    def terminal(self, value, ptr):
        marks = [self.inherited(i) for i in (0,1,3)]
        vals = [m["value"] if m else None for m in marks]
        native = {}
        for field,m in zip(("owner","unit","column"),marks):
            v = m.get("native",m["value"]) if m else None
            hits = [s for s in self.directory[field] if v and clean(s).casefold()==clean(v).casefold()]
            native[field] = hits[0] if len(self.directory[field])>=2 and len(hits)==1 else None
        cross = None
        if value and value[0].casefold()=="maint-summary":
            subtotal = self.frame.summary
            left = cents(value[1])
            right = cents(subtotal["value"]) if subtotal else None
            cross = dict(observed=value[1],subtotal=subtotal,left=left,right=right,
                         diff=left-right if left is not None and right is not None else None)
        status = ("BALANCED" if cross["diff"]==0 else "UNBALANCED") if cross and cross["diff"] is not None else None
        reason = "no_target" if value is None else self.scope()
        if not reason and any(v is None for v in native.values()):
            reason = "incomplete_frame_or_candidate"
        if not reason and cross and status is None:
            reason="unobserved_subtotal"
        typed = dict(type="ABSTAIN",reason=reason) if reason else dict(type="Posting",**native,subtotal_status=status)
        results = []
        for eta in (0.0,0.5):
            if value is None:
                fields = {a:None for a in ("owner","unit")}
                out = dict(type="ABSTAIN",reason="no_target")
            else:
                fields = {a:rank(x,self.directory[a],eta,self.scope()) for a,x in zip(("owner","unit"),vals)}
                if all(r["choice"] is not None for r in fields.values()) and native["column"] and (not cross or status):
                    out = dict(type="Posting",**{a:r["choice"] for a,r in fields.items()},
                               column=native["column"],subtotal_status=status)
                else:
                    out = dict(type="ABSTAIN",reason=sorted({c for f in fields.values() for c in f["reason"]}))
            results.append(dict(eta=eta,fields=fields,conditional=out))
        return dict(ptr=ptr,scope=self.scope(),active_depth=self.depth,cross=cross,native=typed,
                    eta=results,attribute_sources=marks,root=self.frames[0].owner_witness())


def replay(route, caps):
    m = Machine()
    steps = []
    source_at = []
    baseline = None
    terminal = None
    for wi,tag in enumerate(route["tags"],1):
        for s in caps[tag]["spans"]:
            r=s["record"]
            ptr = [wi,r["page"],r["index"]]
            items = list(events(s,wi))
            source_at.append((s,ptr,items,route["keys"][wi-1]))
            kinds = [k for k,v,l in items]
            if "TARGET" in kinds:
                assert len(items)==1
                terminal=m.terminal(items[0][1],ptr)
                break
            for kind,value,literal in items:
                m.step(kind,value,literal,ptr,s)
            if r["kind"]=="row" and "HEADER" not in kinds:
                m.frame.rows+=1
            witness = m.frames[0].owner_witness()
            if route["task"]=="A" and witness["valid"]:
                if baseline is None:
                    assert len(steps)==7 and kinds==["OPEN_LEDGER"]
                    baseline=witness
                assert witness==baseline
            steps.append(dict(write=len(steps)+1,ptr=ptr,tag=tag,kinds=kinds,depth=m.depth,scope=m.scope(),
                              witness=witness))
        if terminal:
            break
    if terminal is None:
        terminal=m.terminal(None,None)
    return terminal, steps, source_at


def historic_check(rows, development):
    out=[]
    for row in rows:
        model,h = row["run"].split("/")
        for member in ("Alder","Cedar"):
            bid,terminal,steps,sources = development[int(h),member]
            item=row[member]
            phase,n=row["phase"],row["step"]
            assert (item["phase"],item["step"])==(phase,n)
            last=len(steps)
            ref_only=phase=="post" and n==last+1
            src=item["source"]
            if phase=="initial":
                assert n==0 and src is None
                witness=Frame().owner_witness()
            else:
                target=phase=="native_pre" or ref_only
                s,ptr,items,key=sources[last if target else n-1]
                r=s["record"]
                assert (src["ptr"],src["key"],src["page"])==(ptr,key,3*(ptr[0]-1)+ptr[1])
                assert src["metadata_sha256"]==sha(packed(r)) and src["feature_f32le_sha256"]==sha(s["feature"])
                assert (src["raw_slice_sha256"],src["text_sha256"])==(s["rawsha"],sha(r["text"].encode()))
                assert src["bbox"]==r["bbox999"] and (src["kind"],src["block"],src["text"])==(r["kind"],r["block_kind"],r["text"])
                assert src["cells"]==r["cells"] and src["events"]==[dict(kind=k,value=v,literal=l) for k,v,l in items]
                assert [e["kind"] for e in item["events_applied"]]==[k for k,v,l in items]
                if target:
                    assert ptr==terminal["ptr"] and src["events"][0]["kind"]=="TARGET"
                    assert n==last+int(ref_only)
                witness=None if ref_only else steps[(last if target else n)-1]["witness"]
                depth=steps[(last if target else n)-1]["depth"]
                assert depth==item["read"]["controller"]["depth"]
            out.append(dict(model=model,horizon=int(h),binder=bid,member=member,phase=phase,write=n,
                            witness=witness,source_sha=sha(packed(src)),reference_only=ref_only))
    assert len(out)==448 and sum(r["reference_only"] for r in out)==8
    return out


def e4_case():
    first=Frame()
    second=Frame()
    first.put(0,ZERO,dict(value="Alder",ptr="synthetic ancestor",confidence=.9))
    second.put(0,ZERO,dict(value=None,ptr="synthetic child",confidence=None))
    valid_read=next(f.marks[0] for f in (second,first) if 0 in f.marks)
    committed_read=next(f.marks[0] for f in (second,first) if f.marks.get(0,{}).get("value") is not None)
    assert valid_read["value"] is None and committed_read["value"]=="Alder"
    return dict(c_min=.8,ancestor_confidence=.9,child_confidence=.3,printed=valid_read,committed_guard=committed_read)
