"""Constructed contract checks. Synthetic words and a local rectangle test double never call OCR."""
import argparse
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import bgra_digest, full_identity, measure, sha, validate_manifest, validate_read
from policy import MAX_REGIONS, attach_read, compare_words, layout, prediction, regions


def word(text, box):
    return dict(text=text, bbox=box)


def line(*words):
    return dict(text=" ".join(w["text"] for w in words), words=list(words))


def outcome(before, after, kind="prose", lines=1):
    return compare_words(before, after, kind, lines)


def checks():
    a = word("AB3", [30, 4, 50, 14])
    b = word("C-34", [52, 4, 75, 14])
    joined = word("AB3C-34", [30, 4, 75, 14])
    label = word("Unit", [2, 4, 23, 14])
    assert outcome([label, a, b], [label, joined]) == "use_crop_single_word"
    assert outcome([a, dict(b, bbox=[60, 4, 75, 14])], [joined]).startswith("keep")
    assert outcome([a, b], [joined], lines=2) == "keep_multiline"
    assert outcome([joined], [dict(joined, text="AB7C-34")]).startswith("keep")
    assert outcome([dict(joined, text="AB3C34")], [joined]) == "use_crop_delimiter"
    assert outcome([dict(joined, text="A73C34")], [joined]).startswith("keep")
    assert outcome([], [joined], kind="cell") == "use_detected_empty_cell_read"
    assert outcome([], [label], kind="cell").startswith("keep")
    assert outcome([joined], []) == "keep_empty_read"
    assert outcome([], []) == "keep_agree"

    raw = dict(width=200, height=160,
               lines=[line(label, a, b), line(word("ID", [5, 45, 25, 55])),
                      line(word("Cost", [105, 45, 135, 55])), line(word("AB2C-12", [10, 73, 50, 85]))])
    grid = [dict(xs=[0, 100, 200], ys=[40, 65, 100, 140])]
    points = [200, 160]
    base = layout(raw, grid, points)
    rows = regions(raw, grid, points, 1, base)
    assert [r["full_value"] for r in rows if r["selected"]] == ["AB2C-12", "", "Unit AB3 C-34"]
    for r in rows:
        r["emitted_value"] = r["full_value"]
    empty, prose = rows[4], rows[-1]
    assert empty["selected"] and empty["rect_px"] == [4, 104, 96, 136]
    assert not rows[5]["selected"] and rows[5]["full_value"] == ""
    attach_read(empty, raw, dict(lines=[line(word("ZX2-34", [6, 5, 45, 15]))]))
    attach_read(prose, raw, dict(lines=[line(label, joined)]))
    # rect begins at (0,0), while the cell starts at (4,104).
    assert empty["projected_words"][0]["bbox"] == [10, 109, 49, 119]
    output = prediction(raw, grid, points, rows)
    assert output["tables"][0]["rows"] == [["ID", "Cost"], ["AB2C-12", ""], ["ZX2-34", ""]]
    assert [s["text"] for s in output["spans"]][:2] == ["Unit", "AB3C-34"]
    assert "Unit AB3C-34" in output["text"]
    attach_read(prose, raw, dict(lines=[line(label, dict(joined, text="AB7C-34"))]))
    output = prediction(raw, grid, points, rows)
    assert prose["flagged"] and not prose["decision"].startswith("use_")
    assert all(s["flagged"] for s in output["spans"][:3])
    assert [s["text"] for s in output["spans"][:3]] == ["Unit", "AB3", "C-34"]

    many = dict(width=200, height=3000, lines=[
        line(word("AC2-34", [10, i*50+1, 40, i*50+11])) for i in range(MAX_REGIONS+2)])
    many["lines"].insert(1, many["lines"][0])
    rows = regions(many, [], points, 1, layout(many, [], points))
    assert sum(r["selected"] for r in rows) == MAX_REGIONS
    assert rows[1]["reason"] == "overlapping_region" and rows[-1]["reason"] == "page_cap"

    for bad in (dict(family="fixture", source_sha256="dummy", pages=[], truth={}),
                dict(family="fixture", source_sha256="dummy", pages=[{"page": 1, "expected": 0}])):
        try:
            validate_manifest(bad)
            raise AssertionError("labels passed")
        except ValueError:
            pass


class ConstructedWorker:
    def __enter__(self):
        self.info = dict(language="en-US", max_dimension=2048, engine="constructed")
        self.bitmap = None
        return self

    def __exit__(self, *_):
        if self.bitmap is not None:
            self.bitmap.close()

    def full(self, path):
        if self.bitmap is not None:
            self.bitmap.close()
        self.bitmap = Image.open(path)
        words = [word("Unit", [20, 20, 40, 34]), word("AB3", [45, 20, 65, 34]), word("C-34", [67, 20, 91, 34])]
        return dict(text=line(*words)["text"], lines=[line(*words)], angle=0, width=self.bitmap.width,
                    height=self.bitmap.height, bgra_sha256=bgra_digest(self.bitmap), pixel_format="Bgra8")

    def crop(self, rect):
        with self.bitmap.crop(rect) as clipped:
            bgra = bgra_digest(clipped)
            x, y, _, _ = rect
            words = [word("Unit", [20-x, 20-y, 40-x, 34-y]), word("AB3C-34", [45-x, 20-y, 91-x, 34-y])]
            return dict(text=line(*words)["text"], lines=[line(*words)], angle=0, width=clipped.width,
                        height=clipped.height, bgra_sha256=bgra, pixel_format="Bgra8",
                        source_rectangle_sha256=bgra, full_bgra_sha256=bgra_digest(self.bitmap))


def run_synthetic(out):
    checks()
    out.mkdir(parents=True, exist_ok=False)
    bitmap = out / "constructed.bmp"
    with Image.new("RGB", (211, 123), "white") as image:
        draw = ImageDraw.Draw(image)
        draw.text((20, 20), "AB3C-34", fill=(0, 64, 128))
        image.save(bitmap)
        page = dict(page=1, bmp=str(bitmap), width=image.width, height=image.height, points=[211, 123],
                    rgb_sha256=sha(image.tobytes()), bgra_sha256=bgra_digest(image))
    manifest = dict(family="constructed", pages=[page], source_sha256=sha(b"constructed"))
    outcomes = {}
    for order in ("AB", "BA"):
        result = measure(manifest, order, out / order, ConstructedWorker, {"constructed": True})
        for arm in "AB":
            pred = json.loads((out / order / arm / "prediction.json").read_bytes())
            want = "Unit AB3 C-34" if arm == "A" else "Unit AB3C-34"
            assert pred["pages"][0]["text"] == want
            assert result["arms"][arm]["crops"] == (arm == "B")
            outcomes.setdefault(arm, result["arms"][arm]["prediction_sha256"])
            assert outcomes[arm] == result["arms"][arm]["prediction_sha256"]
    with ConstructedWorker() as worker:
        full = worker.full(str(bitmap))
        assert full_identity(full) != full_identity(dict(full, lines=[]))
        try:
            validate_read(full, (211, 123), "wrong image")
            raise AssertionError("wrong full bytes accepted")
        except ValueError:
            pass
    print(json.dumps(dict(constructed_checks="passed", orders=["AB", "BA"], prediction_sha256=outcomes)))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, type=Path)
    run_synthetic(p.parse_args().out.resolve())
