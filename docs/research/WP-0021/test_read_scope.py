"""Author-constructed observation probes. Run with python -B test_read_scope.py."""
import unittest

from read_scope import read


PARENT = (20, 95, 190, 305, 390)
CHILD = (20, 115, 215, 305, 390)
NORMAL_PARENT = ("Date", "Charge", "Unit", "Amount")
NORMAL_CHILD = ("Vendor", "WorkOrder", "Hrs", "Amount")
SHARED = ("Date", "Description", "Ref", "Amount")


def line(page, line_no, top, tokens, offsets):
    return {"words": [
        {"text": text, "bbox": [x, top, x + 10, top + 8],
         "ref": f"p{page}:L{line_no}:W{i}"}
        for i, (text, x) in enumerate(zip(tokens, offsets, strict=True), 1)
    ]}


def row(page, line_no, top, rules, tokens, slots=(0, 1, 2, 3)):
    return line(page, line_no, top, tokens, [rules[i] + 4 for i in slots])


def grid(rules, top):
    return {"xs": list(rules), "ys": [top, top + 20, top + 40]}


def setup(child=CHILD, shared=False):
    return {"page": 1, "width_pt": 480, "height_pt": 600,
            "grids": [grid(PARENT, 100), grid(child, 200)], "lines": [
                line(1, 1, 10, ("Property:", "Coral", "Hill"), (4, 49, 83)),
                line(1, 2, 30, ("Unit:", "S-04"), (4, 30)),
                line(1, 3, 70, ("Ledger",), (20,)),
                row(1, 4, 103, PARENT, SHARED if shared else NORMAL_PARENT),
                row(1, 5, 123, PARENT, ("@1", "Note", "S-04", "+9.010")),
                line(1, 6, 173, ("Contractor", "detail"), (20, 87)),
                row(1, 7, 203, child, SHARED if shared else NORMAL_CHILD),
                row(1, 8, 223, child, ("@1", "Note", "S-04", "+9.010")),
            ]}


def continuation(lines, grids):
    return {"page": 2, "width_pt": 480, "height_pt": 600, "lines": lines, "grids": grids}


def run(first, second, mode):
    return [r for r in read({"pages": [first, second]}, mode)["rows"] if r["page"] == 2]


class ScopeTests(unittest.TestCase):
    def test_keeps_child_across_break_then_restores_parent(self):
        second = continuation([
            row(2, 1, 43, CHILD, ("same", "same", "3", "€0.00")),
            row(2, 2, 63, CHILD, ("same", "same", "3", "€0.00")),
            row(2, 3, 123, PARENT, ("same", "same", "€0.00"), (0, 1, 3)),
        ], [grid(CHILD, 40), grid(PARENT, 120)])
        for mode in ("grid", "grid-words"):
            rows = run(setup(), second, mode)
            self.assertEqual([r["scope"] for r in rows], ["child", "child", "parent"])
            last = rows[-1]
            self.assertEqual(last["stack_before"], ["parent", "child"])
            self.assertEqual(last["stack_after"], ["parent"])
            self.assertEqual(last["literal"], "€0.00")
            self.assertEqual(last["column_role"], "Amount")
            self.assertEqual(last["word_ref"], "p2:L3:W3")
            self.assertEqual(last["property"], "Coral Hill")
            self.assertEqual(last["unit"], "S-04")
            self.assertEqual(tuple(last["property_refs"]), ("p1:L1:W2", "p1:L1:W3"))
            self.assertEqual(tuple(last["unit_refs"]), ("p1:L2:W2",))
            self.assertEqual(tuple(last["header_refs"])[-1], "p1:L4:W4")

    def test_disputed_cells_do_not_pop_on_a_tie(self):
        second = continuation([
            row(2, 1, 43, CHILD, ("0.01",), (3,)),
            row(2, 2, 63, CHILD, ("free", "0.01"), (2, 3)),
            row(2, 3, 83, PARENT, ("free", "0.01"), (2, 3)),
        ], [])
        result = run(setup(), second, "grid-words")
        self.assertEqual([r["scope"] for r in result], [None, "child", "parent"])
        self.assertEqual(result[0]["stack_after"], ["parent", "child"])
        self.assertIsNone(result[0]["column_role"])
        self.assertTrue(result[0]["flagged"])

    def test_unassigned_source_comes_through_even_without_a_grid(self):
        second = continuation([
            row(2, 1, 13, CHILD, ("not-a-schema", "x", "z", "000~13")),
        ], [])
        before = run(setup(), second, "grid")[0]
        after = run(setup(), second, "grid-words")[0]
        self.assertIsNone(before["scope"])
        self.assertEqual(before["grid"]["reason"], "no-grid-band")
        self.assertEqual(after["scope"], "child")
        self.assertEqual(before["literal"], "000~13")
        self.assertEqual(before["word_ref"], after["word_ref"])
        self.assertEqual(before["words"], after["words"])

    def test_partial_or_overlapping_rules_allow_independent_alignment(self):
        obs = row(2, 1, 14, PARENT, ("x", "y", "z", "w"))
        for rules, reason in [
            ([grid((20, 305, 390), 10)], "incomplete-grid"),
            ([grid(PARENT, 10), grid(CHILD, 10)], "overlapping-grid-bands"),
            ([grid((8, 60, 125, 261, 396), 10)], "unmatched-grid"),
        ]:
            second = continuation([obs], rules)
            grid_only = run(setup(), second, "grid")[0]
            self.assertTrue(grid_only["flagged"])
            self.assertEqual(grid_only["grid"]["reason"], reason)
            mixed = run(setup(), second, "grid-words")[0]
            self.assertEqual(mixed["scope"], "parent")

    def test_conflicting_full_grid_and_words_flag_in_combined_mode(self):
        second = continuation([row(2, 1, 44, PARENT, ("x", "x", "x", "x"))],
                              [grid(CHILD, 40)])
        self.assertEqual(run(setup(), second, "grid")[0]["scope"], "child")
        mixed = run(setup(), second, "grid-words")[0]
        self.assertEqual(mixed["reason"], "grid-word-disagreement")
        self.assertIsNone(mixed["scope"])
        self.assertEqual(mixed["stack_after"], ["parent", "child"])

    def test_same_geometry_is_unidentifiable(self):
        second = continuation([row(2, 1, 14, PARENT, ("different", "or", "same", "3"))],
                              [grid(PARENT, 10)])
        for mode in ("grid", "grid-words"):
            r = run(setup(child=PARENT, shared=True), second, mode)[0]
            self.assertTrue(r["flagged"])
            self.assertEqual(r["reason"], "tied-scopes")
            self.assertEqual(r["stack_after"], ["parent", "child"])

    def test_directly_headed_printed_grid_distinguishes_identical_schemas(self):
        first = setup(child=PARENT, shared=True)
        for mode in ("grid", "grid-words"):
            rows = read({"pages": [first]}, mode)["rows"]
            self.assertEqual([r["scope"] for r in rows], ["parent", "child"])
            self.assertTrue(all(r["reason"] == "same-headed-grid" for r in rows))

    def test_missing_shadow_schema_blocks_fallthrough_to_parent(self):
        first = setup()
        del first["lines"][6:]
        second = continuation([row(2, 1, 14, PARENT, ("a", "b", "c", "d"))],
                              [grid(PARENT, 10)])
        for mode in ("grid", "grid-words"):
            r = run(first, second, mode)[0]
            self.assertIsNone(r["scope"])
            self.assertEqual(r["stack_after"], ["parent", "child"])

    def test_detected_header_grid_missing_for_one_frame(self):
        first = setup()
        del first["grids"][1]
        second = continuation([row(2, 1, 14, PARENT, ("e", "f", "g", "h"))],
                              [grid(PARENT, 10)])
        self.assertEqual(run(first, second, "grid")[0]["reason"], "missing-header-grid")
        self.assertEqual(run(first, second, "grid-words")[0]["scope"], "parent")


if __name__ == "__main__":
    unittest.main()
