"""CPU-only specification oracle. Input is tokenizer metadata, with no model or packet input."""
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import tokenizers

PIN = "c55c165e32c5a67830362a53e1f548c8930dcc8469efa30ff3252a982799c589"
BLOCK, FORK = b"<BLOCK>", b"<FORK>"
WS = b" \t\r\n\f\v"
DIG = b"0123456789"
WORD = b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
EOS, PAGE, BLOCK_ID, FORK_ID = 1, 128827, 128828, 128829


def sha(data):
    return hashlib.sha256(data).hexdigest()


def raw_pieces(spec, tokenizer):
    # Invert the 256-glyph ByteLevel alphabet before UTF-8 replacement decoding.
    direct = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    other = [b for b in range(256) if b not in direct]
    inverse = {chr(b): b for b in direct}
    inverse.update({chr(256 + i): b for i, b in enumerate(other)})
    by_id = {item["id"]: item["content"] for item in spec["added_tokens"]}
    pieces = []
    for token_id in range(tokenizer.get_vocab_size()):
        spelling = tokenizer.id_to_token(token_id)
        if token_id in by_id:
            assert spelling == by_id[token_id]
        data = (bytes(inverse[c] for c in spelling) if all(c in inverse for c in spelling)
                else spelling.encode("utf-8"))
        assert data and tokenizer.decode([token_id], skip_special_tokens=False) == data.decode("utf-8", "replace")
        pieces.append(data)
    return pieces


class Grammar:
    def __init__(self):
        self.names = []
        self.rows = []
        self.ids = {}
        dead = self.state("reject")
        prose = [self.state(f"prose/{i}") for i in range(len(BLOCK))]
        self.prose = prose
        start = self.state("label/start")
        any_word = self.state("label/word")
        title = [self.state(f"label/{'title'[:i]}") for i in range(1, 6)]
        gap = self.state("after label")
        level_prefix = [self.state(f"level/prefix/{i}") for i in range(1, 7)]
        level_digits = self.state("level/digits")
        digits = [[self.state(f"coord/{j + 1}/{k}") for k in range(5)] for j in range(4)]
        close_gap = self.state("fourth coordinate/closing whitespace")
        fork = [self.state(f"fork/{i}") for i in range(len(FORK))]
        for i, s in enumerate(prose):
            for b in range(256):
                prefix = BLOCK[:i] + bytes([b])
                if prefix.endswith(BLOCK):
                    self.rows[s][b] = start
                else:
                    self.rows[s][b] = prose[max(k for k in range(len(BLOCK)) if prefix.endswith(BLOCK[:k]))]
        # Compact the UTF-8 prefix trie of every non-ASCII Unicode word codepoint.
        # Python's Unicode regex \w means isalnum or underscore.
        root = {}
        for cp in range(128, sys.maxunicode + 1):
            if chr(cp).isalnum():
                node = root
                enc = chr(cp).encode()
                for b in enc[:-1]:
                    node = node.setdefault(b, {})
                node[enc[-1]] = None
        interned = {}

        def compact(node):
            edges = tuple((b, any_word if child is None else compact(child))
                          for b, child in sorted(node.items()))
            if edges not in interned:
                s = self.state(f"unicode word suffix/{len(interned)}")
                interned[edges] = s
                for b, t in edges:
                    self.rows[s][b] = t
            return interned[edges]

        word_prefix = {b: compact(child) for b, child in root.items()}
        for s in [start, any_word, *title]:
            self.edge(s, WORD, any_word)
            for b, target in word_prefix.items():
                self.rows[s][b] = target
            if s != start:
                self.edge(s, WS, gap)
                self.edge(s, b"[", digits[0][0])
        for i, b in enumerate(b"title"):
            self.rows[start if i == 0 else title[i-1]][b] = title[i]
        self.edge(title[-1], b"<", level_prefix[0])
        for i, b in enumerate(b"LEVEL"):
            self.rows[level_prefix[i]][b] = level_prefix[i + 1]
        self.edge(level_prefix[-1], DIG, level_digits)
        self.edge(level_digits, DIG, level_digits)
        self.edge(level_digits, b">", gap)
        self.edge(gap, WS, gap)
        self.edge(gap, b"[", digits[0][0])
        for j in range(4):
            self.edge(digits[j][0], WS, digits[j][0])
            for k in range(5):
                if k < 4:
                    self.edge(digits[j][k], DIG, digits[j][k + 1])
                if k and j < 3:
                    self.edge(digits[j][k], b",", digits[j + 1][0])
                if k and j == 3:
                    self.edge(digits[j][k], b"]", fork[0])
                    if k < 4:
                        self.edge(digits[j][k], WS, close_gap)
        self.edge(close_gap, WS, close_gap)
        self.edge(close_gap, b"]", fork[0])
        for i, b in enumerate(FORK):
            self.rows[fork[i]][b] = fork[i + 1] if i + 1 < len(fork) else prose[0]
        assert dead == 0
        self.delta = np.array(self.rows, dtype="<u2")

    def state(self, name):
        s = len(self.rows)
        self.ids[name] = s
        self.names.append(name)
        self.rows.append([0] * 256)
        return s

    def edge(self, s, chars, t):
        for b in chars:
            self.rows[s][b] = t

    def consume(self, s, data):
        for b in data:
            s = self.rows[s][b]
        return s


def compile_tokens(grammar, pieces, width):
    n = len(grammar.rows)
    out = np.zeros((width, n), dtype="<u2")
    by_length = {}
    for i, p in enumerate(pieces):
        by_length.setdefault(len(p), []).append(i)
    for length, ids in by_length.items():
        for offset in range(0, len(ids), 512):
            batch = ids[offset:offset + 512]
            chars = np.frombuffer(b"".join(pieces[t] for t in batch), np.uint8).reshape(-1, length)
            cur = np.broadcast_to(np.arange(n, dtype="<u2"), (len(batch), n))
            for column in chars.T:
                cur = grammar.delta[cur, column[:, None]]
            out[batch] = cur
    # EOS acts as a boundary. Its printable special-token spelling is never returned.
    out[EOS] = 0
    out[EOS, grammar.prose] = grammar.prose[0]
    return out


def distances(signature, grammar):
    # Shortest number of whole model tokens to any complete/prose state.
    d = np.full(len(grammar.rows), 65535, dtype=np.int32)
    d[grammar.prose] = 0
    while True:
        nxt = np.minimum(d, d[signature].min(axis=0) + 1)
        if np.array_equal(nxt, d):
            break
        d = nxt
    assert d[0] == 65535 and np.all(d[1:] < 65535)
    return d


def main(checkpoint):
    tokfile = checkpoint / "tokenizer.json"
    data = tokfile.read_bytes()
    assert sha(data) == PIN
    spec = json.loads(data)
    assert spec["model"]["type"] == "BPE" and spec["decoder"]["type"] == "ByteLevel"
    tokenizer = tokenizers.Tokenizer.from_file(str(tokfile))
    width = json.loads((checkpoint / "config.json").read_bytes())["vocab_size"]
    pcs = raw_pieces(spec, tokenizer)
    assert width == 129280 and len(pcs) == 128831
    assert (pcs[PAGE], pcs[BLOCK_ID], pcs[FORK_ID]) == (b"<PAGE>", BLOCK, FORK)
    g = Grammar()
    full = compile_tokens(g, pcs, width)
    signature, grouping = np.unique(full, axis=0, return_inverse=True)
    group_dtype = np.dtype("u1" if len(signature) <= 256 else "<u2")
    grouping = grouping.astype(group_dtype).reshape(-1)
    for i in range(0, width, 1024):
        assert np.array_equal(signature[grouping[i:i + 1024]], full[i:i + 1024])
    d = distances(signature, g)
    single = {p[0]: i for i, p in enumerate(pcs) if len(p) == 1}
    assert len(single) == 256
    for b, i in single.items():
        assert np.array_equal(full[i], g.delta[:, b])
    # Every byte-state has an actual token-ID path from initial prose.
    reachable = {g.prose[0]}
    while True:
        expanded = reachable | set(map(int, signature[:, list(reachable)].flat))
        if expanded == reachable:
            break
        reachable = expanded
    assert len(reachable) == len(g.rows)
    def trace(ids, start=None):
        s = g.prose[0] if start is None else start
        for tok in ids:
            s = int(full[tok, s])
        return s
    yes = ["<BLOCK>text[1,2,3,4]<FORK>", "<BLOCK>title<LEVEL2> [0000, 22, 333, 4444]<FORK>Hi",
           "<BLOCK>表題-1 [ 12,\t42, 1,55 ]<FORK> AB-71.④", "<BLOCK>text[9999,1,2,0]<FORK>"]
    no = ["<BLOCK>[]", "<BLOCK>text[1.0,2,3,4]<FORK>", "<BLOCK>text[1,2,3,]<FORK>",
          "<BLOCK>text[1,2,3,4]", "<BLOCK>text[１,2,3,4]<FORK>", "<BLOCK>text[1,2,3,4444 ]<FORK>",
          "<BLOCK>text[1,2,3,4]<FORX>", "<BLOCK>text[12,3,4,5]<FORK><BLOCK>"]
    examples = []
    for s in yes + no:
        ids = tokenizer.encode(s, add_special_tokens=False).ids
        byte_ids = [single[b] for b in s.encode()]
        assert trace(ids) == trace(byte_ids) == g.consume(g.prose[0], s.encode())
        assert (trace(ids) in g.prose) == (s in yes)
        examples.append(dict(text=s, token_ids=ids, complete=s in yes))
    # All real digit-only tokens at all 20 coordinate-count states.
    # Composition gives coverage for alternative segmentations of a digit string.
    real_digits = [(i, p) for i,p in enumerate(pcs) if re.fullmatch(rb"[0-9]+", p)]
    for j in range(4):
        for k in range(5):
            s = g.ids[f"coord/{j + 1}/{k}"]
            for i, p in real_digits:
                assert int(full[i, s]) == g.ids.get(f"coord/{j + 1}/{k + len(p)}", 0)
        s = g.ids[f"coord/{j + 1}/4"]
        sep = ord(",") if j < 3 else ord("]")
        assert [b for b,target in enumerate(g.rows[s]) if target] == [sep]
        for i in np.flatnonzero(full[:, s]):
            assert pcs[i][0] == sep
    for s in range(1, len(g.rows)):
        assert np.all(full[len(pcs):, s] == 0)
    assert full[70962, g.ids["coord/4/4"]] == g.ids["fork/1"]  # ]<
    assert full[6105, g.ids["coord/4/3"]] == g.ids["fork/0"]  # space and ]
    assert full[6105, g.ids["coord/4/4"]] == 0
    assert full[764, g.ids["label/word"]] == g.ids["coord/1/0"]  # space and [
    assert full[18005, g.ids["coord/1/4"]] == 0  # two commas
    assert set(map(int, np.flatnonzero(full[EOS]))) == set(g.prose)
    assert set(map(int, np.flatnonzero(full[PAGE]))) == set(g.prose)
    assert full[3014, g.ids["coord/4/2"]] == 0  # ][
    # An adversarial legal choice can stay in a whitespace loop indefinitely.
    # With a decreasing budget and the distance constraint, every feasible
    # successor has an eventual completion and the final feasible states are prose.
    for remaining in range(1, 15):
        can_finish = d <= remaining
        eligible = (signature != 0) & (d[signature] <= remaining - 1)
        assert np.all(eligible.any(axis=0)[can_finish])
        if remaining == 1:
            assert set(map(int, signature[eligible])) == set(g.prose)
    # Decoder counterexample to concatenating isolated replacement strings.
    e = [single[b] for b in "表".encode()]
    assert tokenizer.decode(e, False) == "表" and "".join(tokenizer.decode([i], False) for i in e) != "表"
    cs = {}
    for category, pattern in {"space_and_bracket": rb" +\[", "multiple_ascii_digits": rb"[0-9]{2,}",
                              "close_and_less_than": rb"\]<", "whitespace_and_close": rb" +\]",
                              "bracket_sequence": rb"\]\[", "double_comma": rb",,"}.items():
        matches = [(i, p.decode()) for i,p in enumerate(pcs) if re.fullmatch(pattern, p)]
        cs[category] = dict(count=len(matches), examples=matches[:4])
    b = 4
    sizes = {str(s): s * width * 6 for s in (11, len(g.rows))}
    summary = dict(tokenizer_sha256=PIN, tokenizers_version=tokenizers.__version__,
                   numpy_version=np.__version__, unicode_version=unicodedata.unidata_version,
                   python=sys.version.split()[0], head_width=width, addressable_ids=len(pcs),
                   unnamed_ids=width-len(pcs), special_ids={"PAGE":PAGE,"BLOCK":BLOCK_ID,"FORK":FORK_ID,"EOS":EOS},
                   states_including_reject=len(g.rows), reachable_including_reject=len(reachable),
                   unicode_continuation_states=sum(name.startswith("unicode word") for name in g.names),
                   byte_equivalence_classes=len(np.unique(g.delta.T,axis=0)),
                   token_transform_classes=len(signature), class_id_itemsize=group_dtype.itemsize,
                   dense_M_bf16_T_i32_bytes=sizes, classification_bytes=grouping.nbytes,
                   class_transitions_u16_bytes=signature.nbytes, distance_u16_bytes=2*len(d),
                   int32_lane_state_bytes=4*b, selected_bf16_rows_B4_bytes=2*b*width,
                   logits_fp32_B4_bytes=4*b*width, max_shortest_completion_tokens=int(d[1:].max()),
                   distance_histogram={str(int(i)):int(n) for i,n in zip(*np.unique(d[1:],return_counts=True))},
                   digit_only_token_ids=len(real_digits), composite_examples=cs,
                   table_sha256_token_major_little_endian_u16=sha(full.tobytes()),
                   token_to_class_sha256=sha(grouping.tobytes()), class_rows_sha256=sha(signature.tobytes()),
                   states_sha256=sha("\n".join(g.names).encode()), examples=examples,
                   isolated_decode_counterexample=e)
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
