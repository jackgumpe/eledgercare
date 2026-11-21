"""Synthetic scoring controls. Run before fresh study input release."""
import unittest
from score import collect_outputs, evaluate, index_observation


def word(page, line, n, text, x, y):
    return {"text":text, "bbox":[x,y,x+10,y+5], "ref":f"p{page}:L{line}:W{n}"}


def region(line):
    y=10*line
    return {"page":1, "bbox":[0,y-1,40,y+6]}


class Scoring(unittest.TestCase):
    def setUp(self):
        self.target = dict(id="test", doc="dev", page=2, kind="value", scope="child", literal="200.00",
            amount_box=[180,90,240,112], row_box=[0,89,605,113], note_boxes=[[550,90,595,112]],
            property_region=region(1), unit_region=region(2), heading=region(3), tags=[])
        self.header = [{"words":[word(1,i,1,s,10,i*10)]} for i,s in enumerate(["prop","unit","child A","child B"],1)]
        self.words = [word(2,1,1,"2O0.00",200,93),word(2,2,1,"200.00",565,96)]
    def evaluate(self, indices, flagged=(), heading="p1:L3:W1", empty=False):
        obs={"pages":[{"page":1,"lines":self.header},{"page":2,"lines":[{"words":[w]} for w in ([] if empty else self.words)]}]}
        sources,lines=index_observation(obs)
        rows=[]
        for i in indices:
            w=self.words[i]
            flag=i in flagged
            rows.append(dict(page=2,line=i+1,literal=w["text"],word_ref=w["ref"],
                words=[{"literal":w["text"],"word_ref":w["ref"]}], flagged=flag,scope=None if flag else "child",
                column_role=None if flag else "Amount",property_refs=["p1:L1:W1"],unit_refs=["p1:L2:W1"],
                heading_refs=[] if flag else [heading],reason="control"))
        located,other=collect_outputs([self.target],sources,lines,{"rows":rows})
        self.assertEqual(other,[])
        return evaluate(self.target,located["test"],sources)
    def test_typo_owned(self):
        d=self.evaluate([0])
        self.assertTrue(d["passed"])
        self.assertEqual(d["transcriptionMismatch"],1)
    def test_matching_note_and_extra(self):
        self.assertEqual(self.evaluate([1])["outcome"],"silent_wrong")
        self.assertEqual(self.evaluate([0,1])["silentWrongPosts"],1)
    def test_empty_safety_and_spurious_post(self):
        self.target.update(kind="blank",literal="")
        self.words=self.words[1:]
        self.words[0]=word(2,1,1,"200.00",565,96)
        self.assertEqual(self.evaluate([0])["noteCaptures"],1)
        d=self.evaluate([0],flagged=[0])
        self.assertTrue(d["passed"])
        self.assertFalse(d["positivelyRepresentedBlank"])
    def test_sibling_provenance(self):
        self.assertEqual(self.evaluate([0],heading="p1:L4:W1")["outcome"],"silent_wrong")
    def test_ambiguous_flag_needs_the_literal_source(self):
        self.target["kind"]="ambiguous"
        self.assertTrue(self.evaluate([0],flagged=[0])["passed"])
        self.assertFalse(self.evaluate([1],flagged=[1])["passed"])
        self.assertFalse(self.evaluate([0])["passed"])
    def test_missing_and_suppressed_are_different(self):
        self.assertEqual(self.evaluate([],empty=True)["outcome"],"no_intersecting_word")
        self.assertEqual(self.evaluate([])["outcome"],"no_field_emitted")
    def test_source_identity_beats_similar_strings(self):
        self.target["property_region"]=region(2)
        self.assertEqual(self.evaluate([0])["outcome"],"silent_wrong")


if __name__ == "__main__":
    unittest.main()
