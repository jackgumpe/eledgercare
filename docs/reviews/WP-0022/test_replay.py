"""Small reviewer-only controls for frozen state capture and truth-independent source matching."""
import unittest

from replay import READER_PATH, evaluate_target, execute, import_reader, index_document, side
from pathlib import Path


class IndependentControls(unittest.TestCase):
    def setUp(self):
        self.reader = import_reader(Path(READER_PATH))
        def tokens(y, components):
            out = []
            for i, (literal, x) in enumerate(components):
                out.append(dict(text=literal, ref=f"y{y}w{i}", bbox=[x,y,x+3,y+4]))
            return {"words": out}
        self.lines = [
            tokens(2, [("Property:",1), ("X",12)]),
            tokens(8, [("Unit:",1), ("Y",12)]),
            tokens(14, [("Ledger",1)]),
            tokens(22, [(h,x) for h,x in zip(["Date","Charge","Unit","Amount"],[1,11,21,31])]),
            tokens(32,[("I.00",31)])]
        self.obs = {"pages":[{"page":1, "grids":[{"xs":[0,10,20,30,40],"ys":[20,30,40]}], "lines":self.lines}]}
        def region(box):
            return {"page":1,"bbox":box}
        self.t = {"id":"reviewer-control","page":1,"doc":"unit","kind":"value","scope":"parent",
                  "literal":"1.00","row_box":[0,30,52,40],"amount_box":[30,30,40,40],"note_boxes":[[42,30,52,40]],
                  "heading":region([0,13,7,19]),"property_region":region([11,1,17,7]),"unit_region":region([11,7,17,13]),
                  "amount_header":region([30,20,40,30]),"tags":[]}

    def evaluate(self, others=()):
        output, stack = execute(self.reader, self.obs)
        source, lines, predictions = index_document(self.obs, output)
        return evaluate_target(self.t, lines, predictions, source, stack, [self.t,*others])

    def test_pointer_and_state(self):
        valid = self.evaluate()
        self.assertEqual(valid["status"],"owned")
        self.assertFalse(valid["transcription"])
        self.assertFalse(valid["missing_amount_header_pointer"])
        state = valid["trace"][0]
        self.assertEqual(state["before"],state["after"])
        self.assertEqual(state["before"][0]["anchors"],(1,11,21,31))
        self.assertEqual(state["header_deltas_pt"][0]["candidate_minus_amount_header_x0"],0)
        self.t["heading"]["bbox"] = [0,40,7,50]
        self.assertEqual(self.evaluate()["false_posts"],1)

    def test_blank_vs_missing_vs_incidental_flag(self):
        self.t["kind"]="blank"
        self.assertEqual(self.evaluate()["status"],"silent-wrong")
        self.lines[-1]["words"][0]["bbox"]=[43,32,46,36]
        self.assertEqual(self.evaluate()["status"],"safe-withholding")
        self.t["kind"]="ambiguous"
        self.assertEqual(self.evaluate()["status"],"no-intersecting-source")
        self.lines[-1]["words"].insert(0,dict(text="1.00",ref="a",bbox=[34,32,37,36]))
        self.assertEqual(self.evaluate()["status"],"incidental-flag")
        self.lines[-1]["words"].pop()
        self.assertEqual(self.evaluate()["status"],"silent-wrong")  # Exactly 3 pt still posts.
        self.lines[-1]["words"][0]["bbox"] = [35,32,38,36]
        self.assertEqual(self.evaluate()["status"],"ambiguous-abstention")

    def test_note_duplicates_and_rectangle_limit(self):
        self.t["note_boxes"]=[[30,30,40,40]]
        self.assertEqual(self.evaluate()["events"][0]["source"],"note")
        self.assertEqual(self.evaluate()["status"],"silent-wrong")
        self.t["note_boxes"]=[[37,30,45,40]]
        self.assertEqual(side({"bbox":[31,32,38,36]},self.t),"straddles-region")
        self.assertEqual(side({"bbox":[-50,-40,114,110]},self.t),"other")
        self.t["note_boxes"]=[]
        self.lines.append({"words":[{"text":"1.00","ref":"extra","bbox":[31,35,34,39]}]})
        self.assertEqual(self.evaluate()["false_posts"],1)


if __name__ == "__main__":
    unittest.main()

