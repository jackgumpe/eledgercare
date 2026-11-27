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


def predict(scores, history, ngram_history, contract, window, page_count, state):
    logits = scores
    logits = _uocr_no_repeat_ngram(logits, ngram_history, contract["order"], window, set())
    logits = _uocr_page_count_guard(logits, history, page_count, contract["page"], contract["eos"], contract["cap"], state)
    return select(logits)


def bindings():
    targets = ["_uocr_no_repeat_ngram", "_uocr_page_count_guard", "select"]
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
       "cursor","ngram_start","include_prompt"}


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
    ledger = CaptureAdapter(predict.__code__, clone_cpu, "cpu")
    rows = []
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
        records = {}
        def visit(at, frame):
            source = frame.f_locals["logits"]
            for a in actions:
                if a["op"] == "write" and a["phase"] == at:
                    source[a["id"]] = Word(pack_word(a["value"]))
            for label, site in offsets.items():
                if site == at:
                    records[label] = ledger.copy(row, frame, source, label in aliases)
        inverse = {offset:phase for phase,offset in cuts.items()}
        with InstructionMonitor({predict.__code__: inverse},visit):
            y = predict(Scores(vocab,words),history,ngram_history,c,window,expected_pages,st)
        for a in actions:
            op = a["op"]
            if op == "choose":
                y = a["id"]
            elif op == "swap":
                x,b = a["a"],a["b"]
                records[x],records[b] = records[b],records[x]
            elif op == "duplicate":
                records[a["to"]] = dict(records[a["from"]])
            elif op == "unwitness":
                records[a["phase"]].pop("copy",None)
            elif op == "drop":
                records.pop(a["phase"],None)
            elif op == "truncate":
                data = records[a["phase"]]
                data["data"] = data["data"][:a["bytes"]]
                data["complete"] = a["complete"]
        for rec in records.values():
            data = bytes(rec.pop("data"))
            rec.update(hex=data.hex(),sha256=digest(data))
        rows.append({"index":row,"history":history,"before":before,"after":dict(st),
                     "phases":records,"y":y,"page":c["page"],"eos":c["eos"],
                     "cap":c["cap"],"expected_pages":expected_pages})
    return {"schema":"wp43-cpu/1","events":ledger.events,"rows":rows,
            "document":scenario.get("document",{}),"prompt":c["prompt"],"vocab":vocab}
