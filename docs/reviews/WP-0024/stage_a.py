"""Independent retained-evidence replay. Run from the repository root, with -I -B."""
import ast
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image
from tokenizers import Tokenizer


FORMATS = "a0e738bc03e515999659dda09c5ee76d08fb37df:docs/research/WP-0015/astra/formats.py"
RESCORE = "0186467670074761a777602d77b53deff3451300:docs/research/WP-0015/astra/sensitivity-title-level/rescore.py"
ARCHIVE = Path("docs/reviews/WP-0023/dev-r1.zip")
FIXTURES = Path("docs/coordination/WP-0023/fixtures")
TOKENIZER = Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/models/Unlimited_OCR_2_04809669/tokenizer.json")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def blob(spec):
    return subprocess.check_output(["git", "show", spec])


def projections():
    formats = blob(FORMATS)
    module = {}
    exec(compile(formats, FORMATS, "exec"), module)
    source = blob(RESCORE)
    tree = ast.parse(source)
    assignment, = [s for s in tree.body if isinstance(s, ast.Assign) and s.targets[0].id == "TITLE"]
    namespace = {"re": re}
    exec(compile(ast.Module([assignment], []), RESCORE, "exec"), namespace)
    assert b'TITLE.sub(r"\\1",raw["raw_output"])' in source
    return module["native_page"], namespace["TITLE"], {FORMATS: digest(formats), RESCORE: digest(source)}


def differences(left, right, path=""):
    if isinstance(left, dict) and isinstance(right, dict) and left.keys() == right.keys():
        return [d for key in left for d in differences(left[key], right[key], f"{path}/{key}")]
    if isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        return [d for i in range(len(left)) for d in differences(left[i], right[i], f"{path}/{i}")]
    return [] if left == right else [{"path": path, "before": left, "after": right}]


def main():
    assert sys.flags.isolated and sys.dont_write_bytecode
    native_page, title, pins = projections()
    archive_hash = digest(ARCHIVE.read_bytes())
    assert archive_hash == "9d7b818fab660ef7c25ee98bd5161ea10e7d745516f9bb8ff7b796571571e2ed"
    token_hash = digest(TOKENIZER.read_bytes())
    inventory = json.loads(Path("docs/coordination/WP-0023/model-before.json").read_bytes())
    assert token_hash == inventory["files"]["tokenizer.json"]["sha256"]
    tokenizer = Tokenizer.from_file(str(TOKENIZER))
    decode = lambda ids: tokenizer.decode(ids, skip_special_tokens=False)
    with zipfile.ZipFile(ARCHIVE) as archive:
        def read(name):
            return json.loads(archive.read(name))
        plan = read("binding/dev-r1-plan.json")
        requests = {entry["window"]: entry for entry in plan["requests"]}
        baseline = {case: read("run/trial/g1-stock-"+case+".json")["result"] for case in ("short", "long")}
        both = {order: read("run/trial/g2-"+order+".json")["result"]["lanes"] for order in ("short-long", "long-short")}
    manifest_path = FIXTURES / "manifest.json"
    # Git stores canonical LF; Windows may check out text files using CRLF.
    manifest_hash = digest(blob(plan["candidate"] + ":" + manifest_path.as_posix()))
    manifest = json.loads(manifest_path.read_bytes())
    assert json.loads(blob(plan["candidate"] + ":" + manifest_path.as_posix())) == manifest
    manifest_worktree_hash = digest(manifest_path.read_bytes())
    assert plan["manifest_sha256"] in (manifest_hash, manifest_worktree_hash)
    pdf_path = FIXTURES / manifest["source"]
    pdf_hash = digest(pdf_path.read_bytes())
    pdf = pdfium.PdfDocument(pdf_path)
    pages = requests["long"]["page_numbers"]
    assert pages == [7, 8, 9]
    dims = [pdf.get_page_size(n-1) for n in pages]
    ids = baseline["long"]["token_ids"]
    assert len(ids) == 665
    by_order = {}
    for order, lanes in both.items():
        for case, lane in zip(order.split("-"), lanes, strict=True):
            stock = baseline[case]
            assert lane["prompt_token_ids"] == stock["prompt_token_ids"]
            for record in (lane, stock):
                assert decode(record["token_ids"]) == record["text"]
                assert record["eos_observed"] and record["eos_id"] == 1 and record["stop_cause"] == "eos"
            assert stock["terminal_observation"]["nxt"] == lane["last_selected_token"] == stock["eos_id"]
            if case == "short":
                assert stock["token_ids"] == lane["token_ids"]
            else:
                assert len(lane["token_ids"]) == len(ids)
                by_order[order] = lane["token_ids"]
        assert len(lanes) == 2
    batch_ids, other = by_order.values()
    assert batch_ids == other
    for case, request in requests.items():
        assert pdf_hash == request["sha256"] == manifest["sha256"]
        rasters = manifest["windows"][case]
        assert request["page_numbers"] == [r["page"] for r in rasters]
        assert request["rgb_sha256"] == [r["rgb_sha256"] for r in rasters]
        for r in rasters:
            path = FIXTURES / r["image"]
            assert digest(path.read_bytes()) == r["sha256"]
            with Image.open(path) as image:
                assert digest(image.convert("RGB").tobytes()) == r["rgb_sha256"]
    def parse(ids_, projected):
        raw = decode(ids_).split("<PAGE>")
        assert raw[0] == "" and len(raw) == 4
        return [native_page(title.sub(r"\1", s) if projected else s, size) for s, size in zip(raw[1:], dims, strict=True)]
    changes = [i for i, (a, b) in enumerate(zip(ids, batch_ids, strict=True)) if a != b]
    assert changes == [84, 227, 316, 449, 537, 540, 543]
    interventions = []
    for idx in changes:
        modified = ids.copy()
        modified[idx] = batch_ids[idx]
        source_page = pages[decode(ids[:idx+1]).count("<PAGE>")-1]
        variants = {}
        for name, projected in [("original", False), ("title_projected", True)]:
            variants[name] = differences(parse(ids, projected), parse(modified, projected))
            if idx == 316:
                assert {"path": "/1/tables/0/rows/0/1", "before": "item", "after": "Item"} in variants[name]
        interventions.append({"index_zero_based": idx, "pdf_page": source_page, "from_id": ids[idx],
                              "to_id": modified[idx], "from_piece": decode([ids[idx]]),
                              "to_piece": decode([modified[idx]]), "changed_parser_fields": variants})
    return {"archive_sha256": archive_hash, "wp23_candidate": plan["candidate"], "source_sha256": pins,
            "tokenizer_sha256": token_hash, "input_pdf_sha256": pdf_hash,
            "manifest_sha256_at_run": plan["manifest_sha256"], "long_pages": pages, "page_points": dims,
            "input_pngs_and_rgb_verified": 6, "short_both_orders_equal": True,
            "b2_permutations_identical": True, "long_pre_eos_tokens": len(ids), "terminal_id": 1,
            "single_token_interventions": interventions,
            "joint_differences": {n: differences(parse(ids, b), parse(batch_ids, b)) for n, b in [("original", False), ("title_projected", True)]}}


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, ensure_ascii=True))

