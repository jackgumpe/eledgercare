"""CPU-only source analogue. Mutation commands belong exclusively to capture."""
from collections import defaultdict
import dis
import struct
from analogue_guards import _uocr_no_repeat_ngram, _uocr_page_count_guard
from capture import CaptureAdapter, InstructionMonitor, PHASES, code_identity, digest, pack_word


class Word:
    def __init__(self, data):
        self.data = data

    def clone(self):
        return Word(bytes(self.data))


class Scores:
    def __init__(self, vocab, words):
        if len(vocab) != len(words):
            raise ValueError("input vector length")
        self.vocab = vocab
        self.slot = {token: i for i, token in enumerate(vocab)}
        self.data = bytearray(b"".join(pack_word(w) for w in words))

    def __getitem__(self, key):
        slot = self.slot[key] * 4
        return Word(self.data[slot:slot + 4])

    def __setitem__(self, key, value):
        keys = self.vocab if isinstance(key, slice) else key if isinstance(key, list) else [key]
        word = value.data if isinstance(value, Word) else struct.pack("<f", value)
        for token in keys:
            if token in self.slot:
                offset = self.slot[token] * 4
                self.data[offset:offset + 4] = word


def select(scores):
    values = [v for v, in struct.iter_unpack("<f", scores.data)]
    return scores.vocab[max(range(len(values)), key=values.__getitem__)]


def call_rep(logits,history,order,window,receipts):
    result=_uocr_no_repeat_ngram(logits,history,order,window,set())
    receipts.append({"kind":"rep","source":id(logits),"result":id(result),
                     "guard":code_identity(_uocr_no_repeat_ngram.__code__)})
    return result


def call_page(logits,history,count,c,state,extra,receipts):
    for invocation in [None,*extra]:
        if invocation and "cursor" in invocation:
            state["scanned"]=invocation["cursor"]
        initial=dict(state)
        result=_uocr_page_count_guard(logits,history,count,c["page"],c["eos"],c["cap"],state)
        receipts.append({"kind":"page","source":id(logits),"result":id(result),"before":initial,
                         "after":dict(state),"guard":code_identity(_uocr_page_count_guard.__code__)})
    return result


def predict(scores, history, ngram_history, contract, window, page_count, state, extra,receipts):
    logits = scores
    logits = call_rep(logits, ngram_history, contract["order"], window, receipts)
    logits = call_page(logits, history, page_count, contract, state,extra,receipts)
    return select(logits)


def bindings():
    targets = ["call_rep", "call_page", "select"]
    code = predict.__code__
    offsets = [i.offset for i in dis.get_instructions(code)
               if i.opname == "LOAD_GLOBAL" and i.argval in targets]
    if len(offsets) != 3:
        raise ValueError("unsupported CPU bytecode")
    return dict(zip(PHASES, offsets, strict=True))


def clone_cpu(scores, alias):
    data = memoryview(scores.data) if alias else bytes(scores.data)
    return data, {"transport": "cpu-view" if alias else "cpu-owned",
                  "source_storage": id(scores.data), "dest_storage": id(data.obj if alias else data),
                  "bytes": len(data)}


OPS = {"capture_at","swap","duplicate","unwitness","drop","truncate","alias","write","choose",
       "cursor","ngram_start","include_prompt","torn","omit_state","reenter_page","recompute","lastmax"}


def capture_analogue(scenario):
    c = scenario["contract"]
    vocab = c["vocab"]
    if not vocab or sorted(set(vocab)) != vocab or c["eos"] not in vocab:
        raise ValueError("invalid compact vocabulary")
    histories = c["histories"]
    schedule = defaultdict(list)
    for instruction in scenario.get("injections", []):
        if instruction["op"] not in OPS or instruction.get("row", 0) not in range(len(histories)):
            raise ValueError("unsupported injection")
        schedule[instruction.get("row", 0)].append(instruction)
    cuts = bindings()
    read_span=None
    def read_cpu(source,alias):
        if read_span is None:
            return clone_cpu(source,alias)
        start,end=read_span
        data=bytes(memoryview(source.data)[start:end])
        return data,{"transport":"cpu-owned","source_storage":id(source.data),"dest_storage":id(data),
                     "bytes":len(data),"source_byte_start":start,"source_byte_end":end}
    ledger = CaptureAdapter(predict.__code__, read_cpu, "cpu")
    rows = []
    lost_receipts=set()
    for row, (history, words) in enumerate(zip(histories, c["raw_words"], strict=True)):
        actions = schedule[row]
        if len(history) == 0:
            previous = []
        else:
            previous = history[:-1]
        expected_pages = c["prompt"].count(c["page"])
        if not row or histories[row-1] != previous:
            # Prime the same state using the stock guard on an unobserved prefix.
            st = {"scanned": 0, "page_len": 0, "marker_cum": 0}
            _uocr_page_count_guard(Scores(vocab,words), previous, expected_pages,
                                   c["page"], c["eos"], c["cap"], st)
        offsets = {p:p for p in PHASES}
        ngram_history = history
        window = c["window"]
        aliases = set()
        for a in actions:
            if a["op"] == "cursor":
                st["scanned"] = a["value"]
            elif a["op"] == "ngram_start":
                window -= a["delta"]
            elif a["op"] == "include_prompt":
                ngram_history = c["prompt"] + history
            elif a["op"] == "capture_at":
                offsets[a["phase"]] = a["at"]
            elif a["op"] == "alias":
                aliases.add(a["phase"])
        before = dict(st)
        skipped={a["to"] for a in actions if a["op"]=="duplicate"} | {a["phase"] for a in actions if a["op"]=="drop"}
        records = {}
        fragments={}
        def visit(at, frame):
            nonlocal read_span
            source = frame.f_locals["logits"]
            for a in actions:
                if a["op"] == "write" and a["phase"] == at:
                    source[a["id"]] = Word(pack_word(a["value"]))
            for label, site in offsets.items():
                if site == at and label not in skipped:
                    torn=next((a for a in actions if a["op"]=="torn" and a["phase"]==label),None)
                    if torn:
                        if torn["at"] not in PHASES[PHASES.index(at)+1:] or not 0<torn["bytes"]<len(source.data):
                            raise ValueError("invalid two-cut fragment schedule")
                        read_span=(0,torn["bytes"])
                    records[label] = ledger.copy(row, frame, source, label in aliases)
                    read_span=None
                    if torn:
                        fragments[label]=[records[label]["copy"]]
            for a in actions:
                if a["op"]=="torn" and a["at"]==at:
                    label=a["phase"]
                    read_span=(a["bytes"],len(source.data))
                    tail=ledger.copy(row,frame,source)
                    read_span=None
                    fragments[label].append(tail["copy"])
                    records[label]["data"]+=tail["data"]
                    records[label]["fragments"]=fragments[label]
        inverse = {offset:phase for phase,offset in cuts.items()}
        guard_calls=[]
        extra=[a for a in actions if a["op"]=="reenter_page"]
        with InstructionMonitor({predict.__code__: inverse},visit):
            y = predict(Scores(vocab,words),history,ngram_history,c,window,expected_pages,st,extra,guard_calls)
        after=dict(st)
        for a in actions:
            op = a["op"]
            if op=="omit_state":
                state={"before":before,"after":after}[a["when"]]
                state.pop(a["field"],None)
            elif op=="lastmax":
                final=records[PHASES[-1]]["data"]
                values=[v for v, in struct.iter_unpack("<f",final)]
                y=vocab[max(range(len(values)),key=lambda j:(values[j],j))]
            elif op=="recompute":
                phase=a["phase"]
                replica=Scores(vocab,words)
                if phase in PHASES[1:]:
                    _uocr_no_repeat_ngram(replica,history,c["order"],c["window"],set())
                if phase==PHASES[2]:
                    baseline={"scanned":0,"marker_cum":0,"page_len":0}
                    _uocr_page_count_guard(replica,history,expected_pages,c["page"],c["eos"],c["cap"],baseline)
                r=records[phase]
                old=r.pop("copy",None)
                if old:
                    lost_receipts.add(old)
                if a["ancestry"]=="raw":
                    r["copy"]=records[PHASES[0]]["copy"]
                elif a["ancestry"]!="absent":
                    raise ValueError("invalid recomputed-byte provenance")
                r["data"]=bytes(replica.data)
            if op == "choose":
                y = a["id"]
            elif op == "swap":
                x,b = a["a"],a["b"]
                records[x],records[b] = records[b],records[x]
            elif op == "duplicate":
                records[a["to"]] = dict(records[a["from"]])
            elif op == "unwitness":
                lost_receipts.add(records[a["phase"]].pop("copy",None))
            elif op == "drop":
                records.pop(a["phase"],None)
            elif op == "truncate":
                data = records[a["phase"]]
                limit=a["bytes"] if "bytes" in a else int(len(data["data"])*a["fraction"])
                if limit<0 or limit>len(data["data"]):
                    raise ValueError("truncate extent")
                data["data"] = data["data"][:limit]
                data["complete"] = a["complete"]
        for rec in records.values():
            data = bytes(rec.pop("data"))
            rec.update(hex=data.hex(),sha256=digest(data))
        rows.append({"index":row,"history":history,"before":before,"after":after,"guard_calls":guard_calls,
                     "phases":records,"y":y,"page":c["page"],"eos":c["eos"],
                     "cap":c["cap"],"expected_pages":expected_pages})
    return {"schema":"wp43-cpu/1","events":[e for e in ledger.events if e["id"] not in lost_receipts],"rows":rows,
            "document":scenario.get("document",{}),"prompt":c["prompt"],"vocab":vocab}
