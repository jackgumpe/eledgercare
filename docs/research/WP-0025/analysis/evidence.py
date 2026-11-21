"""CPU reconstruction of terminal events, printed source spans and retained BF16 observations."""
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from zipfile import ZipFile

import numpy as np
import pypdfium2 as pdfium
from tokenizers import Tokenizer

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SENSOR = ROOT / "docs/research/WP-0024/sensor"
ARCHIVE = ROOT / "docs/reviews/WP-0024/h0-r1.zip"
WITNESS = ROOT / "docs/fixtures/WP-0024/h0/source-witness.json"
TOKENIZER = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/models/Unlimited_OCR_2_04809669/tokenizer.json")
BINDER = "34054347f091c087a39efe17"
LAYER = "native model.model final normalized decoder state, lm_head input, after consuming emitted token"
WIDTH = 1280
PIN = {"archive":"37670af4116f543e2d0104b5d3599d88f2e2d06fc092418ee1cf839769430fc6",
       "plan":"0bf358c54fc97f32ca213d9a1dd10cfb2838f42f7c5dcded1625c0cca1fd2f89",
       "witness":"dfb55b56833599f111eb29e2b3d4b8a7de9eab13b8caae277e09c9ba60271989",
       "tokenizer":"c55c165e32c5a67830362a53e1f548c8930dcc8469efa30ff3252a982799c589",
       "spans":"29817b77589e88ef6b741dc1c36e9da3d07bcf641887109f3a77d4b7a39aeece"}
H_FILES = {"token_hidden.bf16","pooled.f32","capture.json","observed-positions.json"}
BASE_FILES = {"native.json","duration.json","metadata.json","through-eos.u32le"}
SIGNATURE = {13:(20375,21577),77:(21895,22476),100:(21895,22476),146:(939,643)}


def check(ok, message):
    if not ok:
        raise ValueError(message)


def digest(data):
    return sha256(data).hexdigest()


def checked_file(path, expected):
    data = path.read_bytes()
    check(digest(data) == expected, f"SHA-256 mismatch for {path.name}")
    return data


def packed(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=True, allow_nan=False)+"\n").encode()


def ids_bytes(ids):
    return b"".join(i.to_bytes(4,"little") for i in ids)


def source_witnesses(plan):
    document = json.loads(checked_file(WITNESS, PIN["witness"]))
    request, = [row for row in plan["requests"] if Path(row["pdf"]).stem == BINDER]
    source = checked_file(Path(request["pdf"]), document["documents"][BINDER])
    items = [w for w in document["witnesses"] if w["binder"] == BINDER and w["window"] == 1]
    check([r["kind"] for r in items] == ["owner","unit","schema","ordinary row"], "Witness scope")
    output = []
    with pdfium.PdfDocument(source) as doc:
        for w in items:
            check(w["page"] == w["window_page"] == 1, "Unreleased witness page")
            glyphs = []
            with closing(doc[w["page"]-1]) as page, closing(page.get_textpage()) as text:
                check(list(page.get_size()) == document["pdf_page_pt"], "Physical page dimensions")
                for cell in w["cells"]:
                    matches = []
                    with closing(text.search(cell["literal"], match_case=True)) as search:
                        while (found := search.get_next()) is not None:
                            start, length = found
                            boxes = [text.get_charbox(i) for i in range(start,start+length)]
                            box = [min(b[0] for b in boxes),792-max(b[3] for b in boxes),
                                   max(b[2] for b in boxes),792-min(b[1] for b in boxes)]
                            if max(abs(x-y) for x,y in zip(box,cell["source_ink_bbox_pt"],strict=True)) < 0.02:
                                matches.append(box)
                    check(len(matches) == 1, f"PDF glyph binding {cell['literal']}")
                    x0,y0,x1,y1 = matches[0]
                    glyphs.append(dict(literal=cell["literal"],ink_bbox_pt=matches[0],
                                       center999=[(x0+x1)*999/1224,(y0+y1)*999/1584]))
            output.append(dict(page=w["page"],kind=w["kind"],cells=glyphs))
    return output


def bind_witnesses(witnesses, spans):
    def words(s):
        return re.findall(r"\w+",s.casefold())
    output = []
    for w in witnesses:
        cells = w["cells"]
        candidates = []
        expected = [words(c["literal"]) for c in cells]
        for span in spans:
            kind = "row" if len(cells)>1 else "block"
            if (span["page"],span["kind"]) != (w["page"],kind):
                continue
            actual = words(span["text"])
            literal = ([words(c) for c in span["cells"]] == expected if kind == "row" else
                       any(actual[i:i+len(expected[0])] == expected[0] for i in range(len(actual))))
            x0,y0,x1,y1 = span["bbox999"]
            inside = [x0<=c["center999"][0]<=x1 and y0<=c["center999"][1]<=y1 for c in cells]
            if literal or all(inside):
                candidates.append(dict(span=span["index"],bbox999=span["bbox999"],text=span["text"],
                                       cells=span["cells"],token_indices=span["token_indices"],
                                       all_centers_inside=all(inside),lexical=literal))
        hits = [c["span"] for c in candidates if c["all_centers_inside"] and c["lexical"]]
        output.append(dict(kind=w["kind"],unique=len(hits)==1,matches=hits,candidates=candidates))
    return output


class Reference:
    def __init__(self):
        checked_file(SENSOR/"spans.py",PIN["spans"])
        sys.path.insert(0,str(SENSOR))
        import spans
        spans.verify_parsers()
        self.map_window = spans.map_window
        tokenizer_raw = checked_file(TOKENIZER,PIN["tokenizer"])
        self.tokenizer = Tokenizer.from_buffer(tokenizer_raw)
        self.added = {t["id"]:t["content"] for t in json.loads(tokenizer_raw)["added_tokens"]}
        checked_file(ARCHIVE,PIN["archive"])
        with ZipFile(ARCHIVE) as z:
            raw_plan = z.read("binding/h0-r1-plan.json")
            check(digest(raw_plan)==PIN["plan"], "Historical plan")
            self.plan = json.loads(raw_plan)
            self.witnesses = source_witnesses(self.plan)
            self.history = {}
            for mode in "SH":
                prefix = f"run/sensor/b01w01{mode}/"
                self.history[mode] = self.decode(json.loads(z.read(prefix+"native.json")),
                                                 json.loads(z.read(prefix+"metadata.json")))
        a,b = [rec["ids"] for rec in self.history.values()]
        check({i:(x,y) for i,(x,y) in enumerate(zip(a,b,strict=True)) if x!=y} == SIGNATURE,
              "Historical archive signature")
        self.pages = self.plan["calls"][0]["pages"]
        check(self.plan["calls"][0]["tag"]=="b01w01S", "Historical triple")

    def decode(self, native, meta):
        ids = native["token_ids"]
        terminal = native["terminal_observation"]
        check(native["finish_reason"]=="stop" and native["stop_cause"]=="eos" and native["eos_observed"] is True
              and native["eos_id"]==terminal["nxt"]==1 and 1 not in ids, "Unverified EOS")
        check(terminal["step"]==len(ids) and native["expected_pages"]==native["num_pages_out"]==3
              and terminal["prompt_length"]==len(native["prompt_token_ids"]), "Terminal step, pages or prefix")
        for key in ("eos_id","eos_observed","expected_pages","num_pages_out","prompt_token_ids",
                    "stop_cause","terminal_observation","token_ids"):
            check(meta[key]==native[key], "Native/metadata "+key)
        check(self.tokenizer.decode(ids,skip_special_tokens=False)==native["text"]==meta["raw"], "Literal decode")
        verified = self.map_window(meta["raw"],ids,lambda pieces:[self.tokenizer.id_to_token(i) for i in pieces],self.added)
        for key, value in verified.items():
            check(meta[key]==value, "Metadata projection "+key)
        through = [*ids,terminal["nxt"]]
        return dict(ids=through,sha256=digest(ids_bytes(through)),raw=native["text"],pages=meta["pages"],
                    spans=meta["spans"],terminal=terminal,stop={k:native[k] for k in ("stop_cause","eos_id",
                    "eos_observed","expected_pages","num_pages_out","finish_reason")},prompt=native["prompt"],
                    prompt_ids=native["prompt_token_ids"],witnesses=bind_witnesses(self.witnesses,meta["spans"]))


def reconstruct_pool(folder, sample, duration):
    capture = json.loads((folder/"capture.json").read_bytes())
    trace = json.loads((folder/"observed-positions.json").read_bytes())
    ids = sample["ids"][:-1]
    start = len(sample["prompt_ids"])
    stop = start + len(ids)
    check(capture==duration["capture"] and capture["capture_layer"]==LAYER and capture["native_dtype"]=="bfloat16"
          and capture["pool_dtype"]=="little-endian float32", "Capture format/layer")
    check(trace["ids"]==ids and trace["absolute_positions"]==list(range(start,stop))
          and (capture["position_start"],capture["position_stop_exclusive"])==(start,stop)
          and capture["consumed_id_sha256"]==digest(packed(ids)), "Consumed IDs or positions")
    spans = sample["spans"]
    check(capture["hidden_shape"]==[len(ids),WIDTH] and capture["pool_shape"]==[len(spans),WIDTH], "Capture shapes")
    bits = np.frombuffer(checked_file(folder/"token_hidden.bf16",capture["hidden_sha256"]),"<u2").reshape(len(ids),WIDTH)
    # Every BF16 exponent/significand is the high half of the corresponding IEEE FP32 representation.
    states = (bits.astype("<u4") * np.uint32(65536)).view("<f4")
    pools = np.frombuffer(checked_file(folder/"pooled.f32",capture["pooled_sha256"]),"<f4").reshape(len(spans),WIDTH)
    check(np.isfinite(states).all() and np.isfinite(pools).all(), "Nonfinite capture")
    rebuilt = np.zeros_like(pools)
    membership = [[] for _ in ids]
    for i, s in enumerate(spans):
        indices = s["token_indices"]
        check(i==s["index"] and indices and indices==sorted(set(indices)) and 0<=indices[0]<=indices[-1]<len(ids),
              "Invalid span membership")
        for j in indices:
            membership[j].append(i)
            np.add(rebuilt[i],states[j],out=rebuilt[i])
        np.divide(rebuilt[i],np.float32(len(indices)),out=rebuilt[i])
    check(rebuilt.tobytes()==pools.tobytes(), "Retained pool differs from independent FP32 accumulation")
    return dict(bits=bits,states=states,pools=pools,membership=membership,summary=dict(
        rows=len(ids),width=WIDTH,absolute_position_range_half_open=[start,stop],pool_count=len(pools),
        rebuilt_exact_sha256=digest(rebuilt.tobytes()),retained_pool_sha256=capture["pooled_sha256"],
        retained_hidden_sha256=capture["hidden_sha256"],all_span_means_bit_exact=True))
