"""Reviewer reconstruction of raw source spans and the post-consumption native states."""
import argparse
import hashlib
import json
import re
import sys
from itertools import accumulate
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from tokenizers import Tokenizer

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from stage_a import ARCHIVE, TOKENIZER, projections


# Match structural headers in the original source. LEVEL is valid only for titles.
HEADER = re.compile(r"<BLOCK>(?P<name>title(?:<LEVEL\d+>)?|[\w-]+)\s*"
                    r"\[\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\]<FORK>")
ROW = re.compile(r"<tr\b[^>]*>(?:(?!<tr\b).)*?</tr\s*>", flags=re.I|re.S)
TABLE = re.compile(r"<table\b[^>]*>.*?</table>", flags=re.I|re.S)
NATIVE, TITLE, _PINS = projections()
T = Tokenizer.from_file(str(TOKENIZER))
CONFIG = json.loads(TOKENIZER.read_bytes())
ADDED = {t["id"]: t["content"].encode("utf8") for t in CONFIG["added_tokens"]}
INVERSE = {}
next_supplemental = 256
for byte in range(256):
    direct = byte in range(33, 127) or byte in range(161, 173) or byte in range(174, 256)
    INVERSE[chr(byte if direct else next_supplemental)] = byte
    next_supplemental += int(not direct)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def token_piece(idx):
    if idx in ADDED:
        return ADDED[idx]
    return bytes(INVERSE[g] for g in T.id_to_token(idx))


def reconstruct(raw, ids):
    assert T.decode(ids, skip_special_tokens=False) == raw
    pieces = list(map(token_piece, ids))
    assert b"".join(pieces).decode("utf8") == raw
    edges = list(accumulate(map(len, pieces), initial=0))
    char_edges = list(accumulate((len(c.encode("utf8")) for c in raw), initial=0))
    starts, ends = np.array(edges[:-1]), np.array(edges[1:])
    rows = []
    pages = []
    def add(kind, start, stop, text, cells, block, bbox, page):
        b0, b1 = char_edges[start], char_edges[stop]
        indices = np.flatnonzero((starts < b1) & (ends > b0)).tolist()
        assert indices
        rows.append(dict(index=len(rows), kind=kind, page=page, block_kind=block, bbox999=bbox,
                         cells=cells, text=text, char_range=[start,stop], byte_range=[b0,b1],
                         token_indices=indices))
    markers = [m.start() for m in re.finditer("<PAGE>",raw)]
    assert len(markers) == 3 and markers[0] == 0
    for n,(p0,p1) in enumerate(zip(markers, [*markers[1:], len(raw)], strict=True), 1):
        page_raw = raw[p0:p1]
        parsed = NATIVE(TITLE.sub(r"\1", page_raw), (612,792))
        pages.append(parsed)
        headers = list(HEADER.finditer(raw,p0,p1))
        visible_index = 0
        table_index = 0
        for h, stop in zip(headers, [h2.start() for h2 in headers[1:]]+[p1]):
            name = h["name"].split("<",1)[0]
            bbox = list(map(int,h.groups()[1:]))
            body = raw[h.end():stop]
            literal = body.strip()
            if (not literal or max(bbox)>999 or bbox[0]>=bbox[2] or bbox[1]>=bbox[3]):
                continue
            # Use actual upstream visible text, including its table-flattening convention.
            block = NATIVE(TITLE.sub(r"\1", raw[h.start():stop]), (612,792))
            if not block["spans"]:
                continue
            source, = block["spans"]
            assert source == parsed["spans"][visible_index]
            visible_index += 1
            lo = h.end() + body.index(literal)
            add("block", lo, lo+len(literal), source["text"], [], name, bbox, n)
            for table in TABLE.finditer(raw, h.end(), stop):
                completed = list(ROW.finditer(raw, table.start(), table.end()))
                if not completed:
                    continue
                expected_table = parsed["tables"][table_index]
                assert len(completed) == len(expected_table["rows"])
                table_index += 1
                for row, cells in zip(completed, expected_table["rows"],strict=True):
                    # Verify row contents independently of coordinates/ordinal supplied by sensor.
                    isolated = NATIVE("<BLOCK>table[0,0,999,999]<FORK><table>"+row.group()+"</table>", (612,792))
                    assert isolated["tables"][0]["rows"] == [cells]
                    add("row", row.start(), row.end(), " ".join(cells), cells, name, bbox, n)
        assert visible_index == len(parsed["spans"]) and table_index == len(parsed["tables"])
    return dict(spans=rows, pages=pages, token_byte_edges=edges)


def snapshot(directory):
    def read(name):
        return json.loads((directory/name).read_bytes())
    native, meta = read("native.json"), read("metadata.json")
    ids, raw = native["token_ids"],native["text"]
    prompt = native["prompt_token_ids"]
    terminal = native["terminal_observation"]
    assert ids == meta["token_ids"] and raw == meta["raw"] and prompt == meta["prompt_token_ids"]
    assert terminal["prompt_length"] == len(prompt) and terminal["step"] == len(ids)
    assert len(set([terminal["nxt"], native["eos_id"], meta["eos_id"], 1])) == 1
    assert 1 not in ids and meta["stop_cause"] == "eos" and native["eos_observed"] is True
    rebuilt = reconstruct(raw, ids)
    for key, value in rebuilt.items():
        assert value == meta[key], f"{directory.name}: independent reconstruction of {key} disagreed"
    out = dict(emitted=len(ids), eos=terminal["nxt"], rows=sum(r["kind"]=="row" for r in rebuilt["spans"]),
               blocks=sum(r["kind"]=="block" for r in rebuilt["spans"]), source_pages=len(rebuilt["pages"]))
    if (directory/"capture.json").is_file():
        trace = read("observed-positions.json")
        assert trace["ids"] == ids and trace["absolute_positions"] == list(range(len(prompt), len(prompt)+len(ids)))
        hidden_bytes = (directory/"token_hidden.bf16").read_bytes()
        pooled_bytes = (directory/"pooled.f32").read_bytes()
        assert len(hidden_bytes) == len(ids)*1280*2 and len(pooled_bytes) == len(rebuilt["spans"])*1280*4
        h = np.frombuffer(hidden_bytes,dtype="<u2").astype("<u4")
        h = np.left_shift(h, 16).view("<f4").reshape(len(ids),1280)
        assert np.isfinite(h).all()
        assert np.any(h) and len(np.unique(h[:,:4],axis=0)) > 1
        pooled = np.frombuffer(pooled_bytes,dtype="<f4").reshape(-1,1280)
        for index, r in enumerate(rebuilt["spans"]):
            # Independent FP32 running-sum recurrence. Token rows precede all range reductions.
            state = np.zeros(1280,dtype="<f4")
            for i in r["token_indices"]:
                np.add(state,h[i],out=state)
            state /= np.float32(len(r["token_indices"]))
            assert state.tobytes() == pooled[index].tobytes(), f"FP32 pool differs for {directory.name}/{index}"
        capture = read("capture.json")
        assert capture["hidden_sha256"] == sha(hidden_bytes) and capture["pooled_sha256"] == sha(pooled_bytes)
        out.update(positions=len(ids), pooled_bit_exact=len(pooled), pooled_sha256=sha(pooled_bytes), hidden_sha256=sha(hidden_bytes))
    return out


def archive_control():
    result = {}
    with ZipFile(ARCHIVE) as z:
        for case in ("short","long"):
            r = json.loads(z.read("run/trial/g1-stock-"+case+".json"))["result"]
            mapping = reconstruct(r["text"],r["token_ids"])
            result[case] = {"tokens":len(r["token_ids"]),"blocks":sum(s["kind"]=="block" for s in mapping["spans"]),
                            "rows":sum(s["kind"]=="row" for s in mapping["spans"])}
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample", nargs="*", type=Path)
    a = parser.parse_args()
    assert sys.flags.isolated and sys.dont_write_bytecode
    print(json.dumps({str(p):snapshot(p) for p in a.sample} if a.sample else archive_control(),indent=2))

