"""CPU regression checks for stop observation, in-place guards, crossover and failure routing."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from diagnostic import guard_summary
from gates import ORDER, PAGE, compare, deltas
import run
import stock as observer


def model_loop():
    import torch
    S, max_length, max_new_tokens, eos_id = 2, 10, 4, 12
    gen, guard_st, t_first, ngram_size = [], {"marker_cum": 0}, None, 35
    for step in range(max_new_tokens):
        logits = torch.tensor([0., 1., 2., 3., 4., 5., 6., 7., 8., 9., 10., 11., 12.])
        if ngram_size > 0:
            if step == 0:
                logits[eos_id] = -float("inf")
        nxt = int(logits.argmax())
        if t_first is None:
            t_first = True
        if nxt == eos_id:
            break
        gen.append(nxt)
    return gen


def row(key):
    ids = [PAGE, 9 if key == "short" else 10, PAGE, 8, PAGE, 7]
    if key == "long":
        ids.append(5)
    return dict(prompt_token_ids=[PAGE]*3, token_ids=ids, eos_id=0, eos_observed=True, stop_cause="eos",
                finish_reason="stop", num_pages_out=3, expected_pages=3, text="<PAGE>a<PAGE>b<PAGE>c")


class FakeTrial(run.Trial):
    def __init__(self, folder, fail=None):
        self.folder, self.fail, self.control, self.calls = folder, fail, {}, []

    def measured(self, name, fn):
        self.calls.append(dict(name=name, wall_ns=2 if "native" in name else 1))
        return fn()

    def single(self, key, **kwargs):
        if "prefix" in kwargs:
            return self.probe(kwargs["candidates"], 0)
        return row("short" if self.fail == "equal" else key)

    def probe(self, candidates, winner):
        stage = dict(argmax=candidates[winner], top2=[{"id": c, "logit": float(i == winner)}
                                                     for i, c in enumerate(candidates)],
                     candidates={str(c): float(i == winner) for i, c in enumerate(candidates)})
        return dict(raw=stage, processed=stage)

    def wrapped(self, order, probe=None):
        if probe is not None:
            return {"probe": self.probe(probe["candidates"], int(len(order) == 2))}
        lanes = [row("short" if self.fail == "equal" else key) for key in order]
        if self.fail == "g1" and len(order) == 1:
            lanes[0]["eos_observed"] = False
        if self.fail == "g2" and len(order) == 2:
            lanes[0]["text"] += "x"
        if self.fail == "flip" and len(order) == 2:
            for lane in lanes:
                lane["token_ids"][1] += 1
        return dict(lanes=lanes, forwards=dict(batch_size=len(order), prefill=1, decode=6))


class Checks(unittest.TestCase):
    def test_stock_events(self):
        receipt = {}
        with observer.observe(model_loop, receipt):
            self.assertEqual(model_loop(), [11])
        self.assertEqual((receipt["step"], receipt["nxt"]), (1, 12))
        for prefix in ([], [11]):
            receipt = {}
            with self.assertRaises(observer.AtDecision):
                with observer.observe(model_loop, receipt, prefix=prefix, candidates=[11, 12]):
                    model_loop()
            self.assertEqual(receipt["raw"]["candidates"], {"11": 11., "12": 12.})
            self.assertEqual(receipt["processed"]["candidates"]["12"], 12. if prefix else "-inf")
            self.assertEqual(receipt["selected"], 12 if prefix else 11)

    def test_stream_and_terminal_gate(self):
        left = row("short")
        right = deepcopy(left)
        self.assertTrue(compare(left, right)["passed"])
        right["token_ids"].append(7)
        self.assertEqual(compare(left, right)["first"], dict(step_zero_based=6, native_id=0, batch_id=7))
        right = deepcopy(left)
        right["finish_reason"] = "length"
        self.assertFalse(compare(left, right)["passed"])
        self.assertIsNone(compare(left, right)["first"])

    def test_signed_delta_and_guard(self):
        a = {"candidates": {"10": 2., "11": "-inf"}}
        b = {"candidates": {"10": -1., "11": "-inf"}}
        diff = deltas(dict(raw=a, processed=b), dict(raw=b, processed=a), [10, 11])
        self.assertEqual(diff["raw"]["10"]["b2_minus_b1"], -3)
        self.assertEqual(diff["processed"]["10"]["b2_minus_b1"], 3)
        self.assertEqual(diff["raw"]["11"]["b2_minus_b1"], "undefined-equal-infinities")
        h = guard_summary([PAGE] + [1]*40, 0, [0, 1])
        self.assertTrue(h["candidate_restrictions"]["0"]["page_banned"])
        self.assertTrue(h["candidate_restrictions"]["1"]["ngram_banned"])

    def test_covered_gates(self):
        for fail, status, expected in ((None, "timing-completed", 12), ("g1", "g1-failed", 4),
                                       ("g2", "g2-failed", 6), ("equal", "g1-ineligible-window-lengths", 4)):
            with tempfile.TemporaryDirectory() as tmp:
                trial = FakeTrial(Path(tmp), fail)
                result = trial.execute()
                self.assertEqual(result["status"], status)
                self.assertEqual(len(trial.calls), expected)
                if fail is None:
                    self.assertEqual([r["name"] for r in result["arms"]],
                                     ["g3-warmup-native","g3-warmup-batch","g3-ab-native",
                                      "g3-ab-batch","g3-ba-batch","g3-ba-native"])

    def test_concrete_failure_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            trial = FakeTrial(Path(tmp), "flip")
            result = trial.execute()
            self.assertEqual(result["status"], "g2-failed")
            diagnostics = result["diagnostics"]
            self.assertEqual(len(diagnostics["mismatches"]), 4)
            for item in diagnostics["mismatches"]:
                token = str(item["first"]["native_id"])
                self.assertEqual(item["stock_to_b2"]["processed"][token]["b2_minus_b1"], -1)
                self.assertEqual(item["target_history"]["length"], 1)
            self.assertEqual(diagnostics["full_precision"]["status"], "completed")
            self.assertEqual(len(trial.calls), 16)
            self.assertFalse(any(c["name"].startswith("g3-") for c in trial.calls))


if __name__ == "__main__":
    unittest.main()
