"""CPU-only author controls. No OCR model import, benchmark input, or escrow key."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from itertools import combinations
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fixture
import rules

SCORER_SHA = "1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7"


def check_rules():
    matrix = rules.matrix()
    assert len(set(matrix.values())) == len(matrix) == 14
    for i, switch in enumerate(rules.SWITCHES):
        assert matrix["add_" + switch][i] == "1" and matrix["remove_" + switch][i] == "0"
        assert matrix["add_" + switch].count("1") == matrix["remove_" + switch].count("0") == 1
    endpoints = [[2.0, -3.0], [2.001, -3.0]]
    rows = {s: dict(d=[2.0, -3.0], anchored_id_flip=False) for s in rules.SWITCHES}
    assert rules.qualifying_pairs(endpoints, endpoints, rows) == []
    rows["S0"]["anchored_id_flip"] = True  # greedy flip despite zero score shift
    rows["S1a"].update(d=[2, -3.00002], repeat_d=[2.001, -3.00003])
    rows["S1c"].update(d=[2.0009, -3])  # smaller than observed endpoint noise
    rows["S2"].update(d=[2.1, -3], repeat_d=[1.9, -3])  # inconsistent sign
    assert rules.qualifying_pairs(endpoints, endpoints, rows) == [("S0", "S1a")]
    for row in rows.values():
        row.update(anchored_id_flip=True)
    assert rules.qualifying_pairs(endpoints, endpoints, rows) == list(combinations(rules.SWITCHES, 2))
    singles = [(s,) for s in rules.SWITCHES]
    rs = {s: dict(ordinary_window_seconds=[6, 6], free_ids=list(rules.IDS),
                  probe_and_bindings_verified=True) for s in singles}
    assert rules.rank_restorations(singles, rs) == ("S0",)
    rs[("S0",)]["free_ids"] = list(rules.ALTERNATES)
    rs[("S2",)]["ordinary_window_seconds"] = [5, 6]
    assert rules.rank_restorations(singles, rs) == ("S2",)
    for row in rs.values():
        row["free_ids"] = [None, None]
    assert rules.rank_restorations(singles, rs) is None
    clean = [0] * 4
    t = dict(native=[100, 101], carbon_bf16=[90, 91], carbon_surgical=[94, 95])
    assert rules.a2(t, clean, True)["advance"]  # exactly 60% both ways
    assert not rules.a2(t, [0, 1, 0, 0], True)["advance"]
    assert not rules.a2(t, clean, False)["advance"]
    assert not rules.a2(dict(t, carbon_bf16=[100, 91]), clean, True)["advance"]
    assert not rules.a2(dict(t, carbon_surgical=[94, 95.1]), clean, True)["advance"]
    equal_spread = dict(native=[100, 106], carbon_bf16=[92, 96], carbon_surgical=[94, 100])
    assert not rules.a2(equal_spread, clean, True)["advance"]  # six-second tie
    for bad in ([float("nan"), 3], [3], [False, 3]):
        try:
            rules.a2(dict(t, native=bad), clean, True)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid timing accepted")
    return dict(matrix=len(matrix), max_qualifying_pairs=15, valid_orders=rules.A2_ORDERS)


def oracle(truth):
    sha = truth["source_sha256"]
    pages = []
    for ref in truth["pages"]:
        spans = [dict(text=line["text"], bbox=line["bbox"], flagged=False) for line in ref["lines"]]
        tables = [dict(bbox=table["bbox"], rows=[[cell["text"] for cell in row] for row in table["rows"]])
                  for table in ref["tables"]]
        pages.append(dict(page=ref["page"], source_sha256=sha, state="complete",
                          text=ref["text"], spans=spans, tables=tables))
    return dict(source_sha256=sha, pages=pages)


def check_fixture(folder):
    pub = folder / "public/dev/id_ablation"
    custody = folder / "custody/dev/id_ablation"
    sha = fixture.digest
    man = json.loads((pub / "rasters.json").read_bytes())
    truth = json.loads((custody / "truth.json").read_bytes())
    assert truth["source_sha256"] == man["pdf_sha256"] == sha((pub / "source.pdf").read_bytes())
    old_docs = json.loads((fixture.EVAL / "commitments.json").read_bytes())["packets"]
    assert all(man["pdf_sha256"] != old_docs[f]["files"]["source.pdf"] for f in ("H", "A", "B"))
    assert man["windows"] == [list(range(i, i+3)) for i in range(1, 19, 3)]
    assert len(man["pages"]) == len(truth["pages"]) == 18
    expected_files = {"source.pdf", "rasters.json"} | {f"rgb/page-{n:03d}.png" for n in range(1, 19)}
    assert {p.relative_to(pub).as_posix() for p in pub.rglob("*") if p.is_file()} == expected_files
    chars = defaultdict(Counter)
    all_ids = []
    for page, ref in zip(man["pages"], truth["pages"], strict=True):
        assert len(ref["lines"]) == 3 and len(ref["tables"]) == 1
        assert page["page"] == page["page_number"] == ref["page"]
        assert page["text_layer_chars"] == 0 and page["embedded_images"] == 1
        assert page["font_family"] == fixture.page_family(ref["page"] - 1)
        cells = [c for row in ref["tables"][0]["rows"] for c in row if c["critical"]]
        assert len(cells) == 2
        for pos, label in zip(fixture.POSITIONS, [ref["lines"][1]["critical"]] + [c["text"] for c in cells], strict=True):
            assert len(label) == 12 and label[5:9] == "-R17" and label[9:].isdigit()
            chars[page["font_family"], pos].update(label[:5])
            all_ids.append(label)
        png = pub / page["png"]
        assert sha(png.read_bytes()) == page["png_sha256"]
        with Image.open(png) as image:
            assert image.mode == "RGB" and image.size == (page["width_px"], page["height_px"])
            assert (ref["width"], ref["height"]) == (595, 842) and image.size != (2550, 3301)
            assert sha(image.tobytes()) == page["rgb_sha256"]
    assert len(set(all_ids)) == len(all_ids) == 54
    assert len(chars) == 9 and all(c == Counter(dict(I=6, L=6, O=6, **{"0": 6, "1": 6})) for c in chars.values())
    assert len(set(p["rgb_sha256"] for p in man["pages"])) == 18
    anchor = "0d50f40b6520604c2c92f31d3afd74d097149fd5:docs/reviews/WP-0016/evidence/G0-stage1.json"
    stage1 = json.loads(subprocess.check_output(["git", "show", anchor], cwd=fixture.ROOT))
    historic = stage1["runs"]["g0-ab"]["arms"]["native"]["grammar_pages"]
    assert len(historic["H"]) == 4 and len(historic["A"]) == 60
    old_rgb = {p["rgb_sha256"] for family in ("H", "A") for p in historic[family]}
    assert old_rgb.isdisjoint(p["rgb_sha256"] for p in man["pages"])
    for window in man["windows"]:
        assert {man["pages"][p-1]["font_family"] for p in window} == set(fixture.FONTS)

    # Keep oracle and deliberately bad predictions in scoring custody.
    from tempfile import TemporaryDirectory
    scorer = fixture.EVAL / "score.py"
    assert sha(scorer.read_bytes()) == SCORER_SHA
    with TemporaryDirectory(dir=custody) as tmp:
        work = Path(tmp)
        pred = oracle(truth)
        def score(prediction):
            inp = work / "prediction.json"
            inp.write_bytes(fixture.json_bytes(prediction))
            result = subprocess.run([sys.executable, "-I", "-B", str(scorer), str(custody / "truth.json"),
                                     str(inp)], check=True, capture_output=True, encoding="utf-8")
            return json.loads(result.stdout)
        good = score(pred)
        assert good["packet_complete"] and not good["faults"]
        assert good["counts"]["correct_cells"] == good["counts"]["reference_cells"] == 162
        assert good["counts"]["correct_lines"] == good["counts"]["reference_lines"] == 54
        assert good["counts"]["critical_values"] == 54
        assert good["counts"]["cer"] == good["counts"]["unflagged_critical_errors"] == 0
        bad = deepcopy(pred)
        bad["pages"][0]["spans"][1]["text"] = "Inspection ID: OTHER"
        bad["pages"][1]["tables"][0]["rows"][1][1] = "OTHER"
        faults = score(bad)
        paths = [c["at"] for p in faults["pages"] for c in p["critical"] if not c["correct"]]
        assert paths == ["page/1/line/2", "page/2/table/1/row/2/col/2"]
        assert faults["counts"]["unflagged_critical_errors"] == 2
    return dict(pdf_sha256=man["pdf_sha256"], manifest_sha256=sha((pub / "rasters.json").read_bytes()),
                truth_sha256=sha((custody / "truth.json").read_bytes()),
                seed_sha256=sha((custody / "seed.bin").read_bytes()),
                scorer_sha256=SCORER_SHA, public_file_count=len(expected_files), pages=18, windows=6,
                unique_critical_ids=54, lines=54, cells=162, oracle_cer=0, injected_new_silent=2,
                balanced_font_placement_strata=len(chars), balanced_per_glyph_per_stratum=6,
                historical_pdf_commitments_distinct=["H", "A", "B"],
                H_A_published_page_hashes_compared=64, matching_pages=0,
                source_points=[595, 842], raster_pixels=[man["pages"][0]["width_px"], man["pages"][0]["height_px"]])


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fixture", type=Path)
    args = p.parse_args()
    results = {"rules": check_rules()}
    if args.fixture:
        results["fixture"] = check_fixture(args.fixture)
    print(json.dumps(results, indent=2))
