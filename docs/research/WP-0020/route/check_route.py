"""Constructed controls for selection, absence vs explicit blank, ambiguity and stock-score joins."""
import ast
from copy import deepcopy
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import route as r

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "docs/evaluation/WP-0015"))
import score


def span(text, box):
    return dict(text=text, bbox=box, flagged=False)


def controls(root):
    page = dict(page=1, source_sha256="synthetic", state="complete", text="Inspection ID WI Alpha Serial Name WI",
                spans=[span("Inspection", [10, 10, 29, 20]), span("ID", [31, 10, 39, 20]),
                       span("WI", [41, 10, 50, 20]), span("Alpha", [10, 35, 30, 45]),
                       span("Serial", [12, 62, 33, 70]), span("Name", [62, 62, 84, 70]),
                       span("WI", [12, 82, 24, 90])],
                tables=[dict(bbox=[10, 60, 110, 120], rows=[["Serial", "Name"], ["WI", ""], ["", ""]])])
    layout = dict(page=1, rule_tables=[dict(xs=[10, 60, 110], ys=[60, 80, 100, 120])],
                  line_word_counts=[3, 1, 2, 1],
                  span_sha256=r.digest(r.encode([[s["text"], s["bbox"]] for s in page["spans"]])))
    folder = root / "DEV"
    folder.mkdir()
    for name, obj in (("prediction", dict(source_sha256="synthetic", pages=[page])),
                      ("layout", dict(pages=[layout])), ("windows", dict(windows=[dict(start=1, pages=[1])]))):
        (folder / (name+".json")).write_bytes(r.encode(obj))
    native = dict(page=1, source_sha256="synthetic", spans=[span("Inspection ID N-123", [9, 9, 51, 21]),
                                                           span("Serial Name NEW", [10, 60, 110, 120])],
                  tables=[dict(bbox=[10, 60, 110, 120], rows=[["Serial", "NAME"], ["NEW", "EXTRA"], ["", "X"]])])
    pred, lines, m = r.read_windows(root, "DEV")
    return pred["pages"][0], lines[1], m["fields"], native


class RouteTests(unittest.TestCase):
    def setUp(self):
        with TemporaryDirectory() as d:
            self.page, self.lines, self.fields, self.native = controls(Path(d))

    def test_label_identity(self):
        def label_nodes(path):
            return [ast.dump(n) for n in ast.parse(path.read_bytes()).body
                    if (isinstance(n, ast.FunctionDef) and n.name == "label") or
                    (isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "LABELS")]
        self.assertEqual(label_nodes(Path(r.__file__)), label_nodes(REPO/"docs/research/WP-0019/astra/policy.py"))
        self.assertFalse(r.label("Valid Lotions 007"))
        self.assertTrue(r.label("Inspection + ID-008"))

    def test_raw_selection_and_scorer(self):
        self.assertEqual([f["id"] for f in self.fields],
                         ["page/1/table/1/row/2/col/1", "page/1/table/1/row/3/col/1", "page/1/raw_line/1"])
        self.assertEqual(self.fields[1]["span_indices"], [])
        out, rows = r.route(self.page, self.lines, self.fields, self.native)
        self.assertEqual(out["text"], "Inspection ID N-123 Alpha Serial Name NEW")
        self.assertEqual([row["native_value"] for row in rows], ["NEW", "", "Inspection ID N-123"])
        self.assertEqual(out["spans"][1], self.page["spans"][3])  # unselected line
        self.assertEqual(out["tables"][0]["rows"], [["Serial", "Name"], ["NEW", ""], ["", ""]])
        ref = dict(page=1, width=200, height=200, lines=[dict(bbox=[10,10,50,20], text="Inspection ID N-123",
                                                              critical="N-123"),
                                                       dict(bbox=[10,35,30,45], text="Alpha", critical=None)],
                   tables=[dict(bbox=[10,60,110,120], rows=[
                       [dict(text=val, critical=bool(ri and not ci),
                             bbox=[10+50*ci,60+20*ri,60+50*ci,80+20*ri]) for ci,val in enumerate(row)]
                       for ri,row in enumerate(out["tables"][0]["rows"])])])
        observed = score.layout(ref, out, "synthetic")
        self.assertTrue(all(v["correct"] for group in ("critical", "cells", "lines") for v in observed[group]))
        self.assertEqual(observed["faults"], [])

    def test_native_absence_and_ambiguities(self):
        for mutate, why in (
              (lambda p: p.update(tables=[]), "no_overlapping_region"),
              (lambda p: p["tables"].append(deepcopy(p["tables"][0])), "multiple_native_regions"),
              (lambda p: p["tables"][0]["rows"].pop(), "grid_shape_mismatch"),
              (lambda p: p["tables"][0]["rows"][1].__setitem__(0, None), "no_literal_cell")):
            native = deepcopy(self.native)
            mutate(native)
            _, rows = r.route(self.page, self.lines, self.fields, native)
            self.assertEqual((rows[0]["reason"], rows[0]["emitted_value"], rows[0]["native_value"]), (why, "WI", None))
        native = deepcopy(self.native)
        native["spans"] = [span("mixed\nblock", [10, 10, 50, 20])]
        self.assertEqual(r.route(self.page, self.lines, self.fields, native)[1][-1]["reason"], "no_literal_single_line")
        native["spans"] = [span("only adjacent", [50, 10, 90, 20])]
        self.assertEqual(r.route(self.page, self.lines, self.fields, native)[1][-1]["native_value"], None)
        self.assertTrue(r.eligible([0,0,20,20], [0,0,10,20]))
        self.assertFalse(r.eligible([0,0,20,20], [0,0,9.99,20]))
        self.assertEqual(r.lookup(0, {0:[0,0,20,20],1:[0,0,21,20]}, {0:[0,0,20,20]})[1],
                         "native_region_matches_multiple_windows_regions")

    def test_explicit_empty_and_spaced_values(self):
        self.native["tables"][0]["rows"][1][0] = ""
        self.native["tables"][0]["rows"][2][0] = "N  7"
        out, rows = r.route(self.page, self.lines, self.fields, self.native)
        self.assertEqual([d["status"] for d in rows], ["substituted"]*3)
        self.assertEqual(out["tables"][0]["rows"][1:], [["", ""], ["N  7", ""]])
        self.assertEqual(out["spans"][-1], span("N  7", [10, 100, 60, 120]))
        self.assertFalse(any(s["text"] == "WI" for s in out["spans"]))


if __name__ == "__main__":
    unittest.main()
