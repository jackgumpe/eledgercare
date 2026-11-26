"""Independently reconstruct one archived native field. Read source and tokenizer data only."""
import hashlib
import io
import json
import re
import subprocess
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader

REPO = Path(__file__).resolve().parents[3]
BASE = "a0bf6122d082675d483ffd9aeb7f4dbedbfb174c"
Q0 = Path.home() / "eLedgerCare-Q0/WP-0005"
MODEL = Q0 / "models/Unlimited_OCR_2_04809669"
SNAP = "docs/coordination/WP-0005/gpu-reviewer-release/author-run-snapshot"
HISTORICAL_HEAD = "9e73ef86600b5e16f74b056676a6d3a4f1474058"


def read(path, ref=BASE):
    return subprocess.check_output(["git", "show", f"{ref}:{path}"], cwd=REPO)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def get_file(name):
    return read(f"{SNAP}/evidence/{name}")


def byte_pieces(data, ids):
    # The ByteLevel alphabet maps printable bytes to themselves and the rest above U+00FF.
    literal = [*range(33, 127), *range(161, 173), *range(174, 256)]
    extra = [n for n in range(256) if n not in literal]
    inverse = {chr(n): n for n in literal}
    inverse.update({chr(256 + i): n for i, n in enumerate(extra)})
    assert data["model"]["type"] == "BPE" and data["decoder"]["type"] == "ByteLevel"
    vocab = {v: k for k, v in data["model"]["vocab"].items()}
    added = {t["id"]: t["content"] for t in data["added_tokens"]}
    return [added[n].encode() if n in added else bytes(inverse[c] for c in vocab[n]) for n in ids]


def shifted(regex, raw, index, offset=0):
    match = list(re.finditer(regex, raw, flags=re.S))[index]
    return match.group(), offset + match.start()


def binding(raw, pieces, ids, prompt_len):
    page = raw.split(b"<PAGE>")[1]
    table, t = shifted(rb"<table>.*?</table>", page, 1, len(b"<PAGE>"))
    rows = rb"<tr>.*?</tr>"
    cells = rb"<td>.*?</td>"
    header, _ = shifted(rows, table, 0)
    row, r = shifted(rows, table, 1, t)
    cell, start = shifted(cells, row, 4, r)
    assert shifted(cells, header, 4)[0] == b"<td>Unit Price</td>"
    assert shifted(cells, row, 0)[0] == b"<td>L01</td>"
    assert re.fullmatch(rb"<td>\$\d+\.\d\d</td>", cell)
    cents = Decimal(cell[5:-5].decode())*100
    end = start + len(cell)
    assert (start + 4, end - 5, end, cents) == (1827, 1833, 1838, 2850)
    assert b"<BLOCK>table[62, 310, 937, 552]<FORK>" in raw[:t]
    cursor = 0
    overlap = []
    for i, piece in enumerate(pieces):
        if cursor < end and cursor + len(piece) > start:
            overlap.append((i, ids[i], cursor, cursor+len(piece), piece.decode("ascii")))
        cursor += len(piece)
    assert overlap[0][2:4] == (start, start+4) and overlap[-1][2:4] == (end-5, end)
    assert overlap[0][0] == 618 and overlap[-1][0] == 623
    return {"raw_ranges_open_value_close": [[start, start+4], [start+4,end-5], [end-5,end]],
            "minor_units": int(cents), "native_tokens_i_id_start_end_piece": overlap,
            "predicting_input_generated_indices": [v[0]-1 for v in overlap[1:]],
            "predicting_input_absolute_positions": [prompt_len+v[0]-1 for v in overlap[1:]]}


def source_identity():
    manifest = json.loads(get_file("model-files.json"))["files"]
    records = {r["path"]: r for r in manifest}
    disk = {}
    for name in ("tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "config.json",
                 "generation_config.json", "model.safetensors.index.json"):
        data = (MODEL / name).read_bytes()
        assert sha(data) == records[name]["sha256"]
        disk[name] = sha(data)
    modules = json.loads(get_file("module-cache.json"))
    cache = Path(modules["modules_cache"]) / "transformers_modules" / MODEL.name
    for r in modules["modules"]:
        filename = r["file"]
        a = (MODEL / filename).read_bytes()
        b = (cache / filename).read_bytes()
        assert sha(a) == sha(b) == r["cache_sha256"] == r["model_sha256"] == records[filename]["sha256"]
        disk[filename] = sha(a)
    assert len(modules["modules"]) == 8
    cfg = json.loads((MODEL/"config.json").read_bytes())
    assert (cfg["num_hidden_layers"], cfg["hidden_size"], cfg["vocab_size"]) == (12,1280,129280)
    assert cfg["sparse_attention_config"]["sparse_main_rope_mode"] == "page2d"
    return disk


def geometry(pdf_data):
    p = PdfReader(io.BytesIO(pdf_data)).pages[0]
    assert list(p.mediabox) == [0, 0, 612, 792] and p.rotation == 0
    stream = p.get_contents().get_data()
    # Distinguish this cell from the duplicate amount under Net Line on the same printed row.
    assert b"359.50 534.00 Tm (Unit Price)" in stream
    assert b"44.00 519.00 Tm (L01)" in stream
    first = stream.index(b"371.44 519.00 Tm ($28.50)")
    left = b"344.00 529.50 m 344.00 504.50 l S"
    right = b"398.00 529.50 m 398.00 504.50 l S"
    assert stream.index(left) < first < stream.index(right)
    assert b"40.00 504.50 532.00 25.00 re" in stream[:first]
    return [344,504.5,398,529.5]


def reader_check(ids, fixture):
    # This subprocess only parses tokenizer data and renders the selected original PDF page on CPU.
    # No transformers, torch, remote-code import, or native model operation.
    program = """
import hashlib, io, json, subprocess, sys
import pypdfium2
from tokenizers import Tokenizer
from importlib.metadata import version
cfg=json.load(sys.stdin)
raw=Tokenizer.from_file(cfg['tokenizer']).decode(cfg['ids'],skip_special_tokens=False).encode()
doc=pypdfium2.PdfDocument(subprocess.check_output(['git','show',cfg['pdf']]))
page=doc[0]
bmp=page.render(scale=300.0/72.0)
pix=bmp.to_pil().convert('RGB')
pos=bmp.get_posconv(page)
print(json.dumps({'full_native_decoded_sha256': hashlib.sha256(raw).hexdigest(),
'pdfium_nearest_grid_corners': [pos.to_bitmap(344,529.5),pos.to_bitmap(398,504.5)],
'rgb_sha256':hashlib.sha256(pix.tobytes()).hexdigest(),'rgb_size':pix.size,
'installed': {n:version(n) for n in ['pypdfium2','tokenizers','torch','transformers']},
'model_modules_loaded': any(n in sys.modules for n in ['transformers','torch'])}))
"""
    output = subprocess.check_output([str(Q0/"venv/Scripts/python.exe"), "-I", "-B", "-c", program],
                                     input=json.dumps({"ids": ids, "tokenizer": str(MODEL/"tokenizer.json"),
                                                       "pdf": f"{BASE}:{fixture['path']}"}).encode(), cwd=REPO)
    return json.loads(output)


def main():
    names = source_identity()
    inventory = json.loads(read(f"{SNAP}/inventory.json"))
    outcome = json.loads(get_file("outcome.json"))
    files = {r["path"]: r for r in inventory["files"]}
    assert len(files) == inventory["file_count"] == 72
    assert inventory["executing_head"] == outcome["context"]["code_identity"]["head"] == HISTORICAL_HEAD
    obs = json.loads(get_file("F07.warm1.observation.json"))
    raw = get_file("F07.warm1.raw.txt")
    id_blob = get_file("F07.warm1.token_ids.json")
    ids = json.loads(id_blob)
    assert len(ids) == obs["native"]["output_tokens"] == 2558
    assert sha(raw) == obs["native"]["text_sha256"] == files["evidence/F07.warm1.raw.txt"]["sha256"]
    assert sha(id_blob) == obs["token_ids_file"]["full_sha256"] == files["evidence/F07.warm1.token_ids.json"]["sha256"]
    assert sha(json.dumps(ids).encode()) == obs["native"]["token_ids_sha256"]
    pieces = byte_pieces(json.loads((MODEL/"tokenizer.json").read_bytes()), ids)
    assert b"".join(pieces) == raw
    protocol = json.loads(read("qualification/q0/harness/protocol.json", HISTORICAL_HEAD))
    fixture = next(x for x in protocol["fixtures"] if x["family_id"] == "F07")
    assert fixture["split"] == "dev"
    data = read(fixture["path"])
    assert sha(data) == fixture["sha256"]
    pdf_geometry = geometry(data)
    second = reader_check(ids, fixture)
    assert second["full_native_decoded_sha256"] == sha(raw) and not second["model_modules_loaded"]
    q0_render = outcome["checks"]["2_artifact_dependency_lock"]["rendered_pages"][fixture["fixture_id"]][0]
    assert second["rgb_sha256"] == fixture["raster"][0]["rgb_sha256"] == q0_render["rgb_sha256"]
    assert second["rgb_size"] == [q0_render["width"], q0_render["height"]] == [2550,3301]
    lease = json.loads(read("docs/coordination/WP-0005/gpu-reviewer-release/author-exit.json"))
    assert lease["author_lease_status"].startswith("RETURNED") and not lease["prior_pids_present"]
    result = binding(raw, pieces, ids, obs["native"]["prompt_len"])
    return {"archive": {"inventory_count":len(files), "source_head":HISTORICAL_HEAD,
                        "status":outcome["status"], "raw_bytes":len(raw), "native_ids":len(ids),
                        "raw_sha256":sha(raw), "id_file_sha256":sha(id_blob),
                        "id_list_sha256":obs["native"]["token_ids_sha256"],
                        "aggregate_cache":obs["cache"], "kernel_path":obs["kernel_path"],
                        "executed_kwargs":obs["call_kwargs"], "prompt_len":obs["native"]["prompt_len"],
                        "lease":lease["author_lease_id"], "lease_return":lease["observed_utc"]},
            "cell":result, "pdf": {"pdf_sha256":sha(data), "pdf_cell_left_bottom_right_top":pdf_geometry,
                                  "actual_Q0_render":q0_render,"independent_reader":second},
            "verified_local_source_blobs":names}


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
