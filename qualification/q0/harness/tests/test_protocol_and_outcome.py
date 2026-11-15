import copy
import json
import unittest

import support  # noqa: F401  (path setup)
from q0harness.hashing import git_blob_sha1_bytes
from q0harness.outcome import BLOCKED, QUALIFIED, Q0Failure, assert_no_score, make_outcome
from q0harness.protocol import (FROZEN_FIXED_KWARGS, build_call_kwargs, check_context_budget,
                                check_repo_path_allowed, load_protocol, schedule, validate_protocol)


class HashingVectors(unittest.TestCase):
    def test_git_blob_known_vectors(self):
        # `git hash-object` reference values.
        self.assertEqual(git_blob_sha1_bytes(b""), "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")
        self.assertEqual(git_blob_sha1_bytes(b"hello\n"), "ce013625030ba8dba906f756967f9e9ca394464a")


class ProtocolFreeze(unittest.TestCase):
    def setUp(self):
        self.p, self.sha = load_protocol()

    def mutated(self, fn):
        p = copy.deepcopy(self.p)
        fn(p)
        with self.assertRaises(Q0Failure) as cm:
            validate_protocol(p)
        return cm.exception

    def test_committed_protocol_valid(self):
        self.assertEqual(len(self.sha), 64)
        self.assertEqual([f["fixture_id"] for f in self.p["fixtures"]], ["SYN-WO-01-v0-clean", "SYN-MP-01-v0-clean"])

    def test_safety_kwargs_cannot_change(self):
        for key, bad in [("save_results", True), ("crop_mode", True), ("temperature", 0.1), ("output_path", "out"),
                         ("crop_mode", 0), ("temperature", 0), ("max_length", 4096), ("page_count_guard", False),
                         ("no_repeat_ngram_size", 0)]:
            with self.subTest(key=key, bad=bad):
                self.mutated(lambda p: p["call"]["fixed_kwargs"].__setitem__(key, bad))
        self.mutated(lambda p: p["call"]["fixed_kwargs"].__setitem__("extra", 1))
        self.mutated(lambda p: p["call"].__setitem__("prompt", "Free OCR."))

    def test_holdout_and_expected_refused(self):
        def to_holdout(p):
            p["fixtures"][0]["family_id"] = "F03"
        self.mutated(to_holdout)
        self.mutated(lambda p: p["fixtures"][0].__setitem__("path", "evaluation/synthetic/pdfs/F03/SYN-WO-03-v0-clean.pdf"))
        self.mutated(lambda p: p["fixtures"][0].__setitem__("split", "eval_holdout"))
        self.mutated(lambda p: p["fixtures"].append(copy.deepcopy(p["fixtures"][0])))
        for bad in ["evaluation/synthetic/expected/SYN-WO-01-v0-clean_expected.json",
                    "evaluation\\synthetic\\expected\\x.json", "evaluation/synthetic/sources/F01_SYN-WO-01_source.json",
                    "evaluation/synthetic/pdfs/F05/SYN-INV-02-v0-clean.pdf", "../outside.pdf",
                    "evaluation/synthetic/pdfs/F01/../F08/SYN-MP-02-v0-clean.pdf", "C:/abs.pdf"]:
            with self.subTest(path=bad):
                with self.assertRaises(Q0Failure) as cm:
                    check_repo_path_allowed(bad)
                self.assertEqual(cm.exception.failure_class, "HOLDOUT_ACCESS_REFUSED")

    def test_sequence_exactly_two_warm_repeats(self):
        self.mutated(lambda p: p["sequence"].__setitem__("warm_repeats_per_fixture", 3))
        self.mutated(lambda p: p["sequence"].__setitem__("warmup_per_fixture", 0))
        plan = schedule(self.p)
        self.assertEqual([(i["fixture_id"][:9], i["kind"], i["repeat"]) for i in plan], [
            ("SYN-WO-01", "warmup", 0), ("SYN-MP-01", "warmup", 0), ("SYN-WO-01", "warm", 1), ("SYN-MP-01", "warm", 1),
            ("SYN-WO-01", "warm", 2), ("SYN-MP-01", "warm", 2)])
        self.assertEqual([i["excluded"] for i in plan], [True, True, False, False, False, False])

    def test_call_kwargs_and_budget_rules(self):
        f01, f07 = self.p["fixtures"]
        k1, k7 = build_call_kwargs(self.p, f01), build_call_kwargs(self.p, f07)
        self.assertEqual((k1["max_new_tokens"], k1["ngram_window"]), (8000, 128))
        self.assertEqual((k7["max_new_tokens"], k7["ngram_window"]), (24000, 1024))
        for k in (k1, k7):
            self.assertIs(k["save_results"], False)
            self.assertEqual(k["output_path"], "")
            self.assertIs(k["crop_mode"], False)
            self.assertEqual({x: k[x] for x in FROZEN_FIXED_KWARGS}, FROZEN_FIXED_KWARGS)
        self.mutated(lambda p: p["fixtures"][1].__setitem__("max_new_tokens", 20000))
        check_context_budget(830, 24000, 131072)
        with self.assertRaises(Q0Failure) as cm:
            check_context_budget(131072 - 7999, 8000, 131072)
        self.assertEqual(cm.exception.failure_class, "CONTEXT_BUDGET_EXCEEDED")

    def test_guards_validated(self):
        self.mutated(lambda p: p["guards"].__setitem__("stall_s", 10))  # < 4 heartbeats
        self.mutated(lambda p: p["guards"]["timeouts_s"].__setitem__("load", 0))
        self.mutated(lambda p: p["gpu"].__setitem__("concurrency", 2))


class OutcomeHonesty(unittest.TestCase):
    def test_no_score_anywhere(self):
        for bad in [{"cer": 0.1}, {"x": [{"field_accuracy": 0.0}]}, {"exact_matched": 3}, {"F1Score": 1}]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    assert_no_score(bad)
        assert_no_score({"lower_bound": 1, "power": 2, "answer": "x", "accuracy_score": None, "recurrence": 1})

    def test_outcome_invariants(self):
        rec = make_outcome(BLOCKED, failures=[Q0Failure("OOM", "x").as_record()])
        self.assertIsNone(rec["accuracy_score"])
        with self.assertRaises(ValueError):
            make_outcome(BLOCKED)
        with self.assertRaises(ValueError):
            make_outcome(QUALIFIED, failures=[Q0Failure("OOM", "x").as_record()])
        with self.assertRaises(ValueError):
            make_outcome(QUALIFIED, observations=[{"score": 0.0}])
        with self.assertRaises(ValueError):
            Q0Failure("NOT_A_CLASS", "x")
        json.dumps(rec, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
