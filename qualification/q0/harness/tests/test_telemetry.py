import sys
import unittest
import uuid

import support
from q0harness.outcome import Q0Failure
from q0harness.telemetry import TARGETS, TOOL_ID, NativeObserver, SafetyTripwire, resolve_targets


class Observer(unittest.TestCase):
    def setUp(self):
        self.scratch = support.new_scratch("telemetry")

    def tearDown(self):
        support.purge_fake_modules()
        support.remove_scratch(self.scratch)

    def load(self, triton_stub=False):
        d = self.scratch / "m"
        support.write_fake_model_dir(d, triton_stub=triton_stub)
        pkg = f"tel_{uuid.uuid4().hex[:8]}"
        mod = support.install_package(self.scratch / "cache", pkg, d)
        model = mod.UnlimitedOCRForCausalLM(mod.UnlimitedOCRConfig())
        resolved, unresolved = resolve_targets(sys.modules, prefix=f"transformers_modules.{pkg}.")
        return mod, model, resolved, unresolved

    def call(self, mod, model, pages=3, **kw):
        imgs = [object()] * pages
        return model.infer_multi(mod.FakeTokenizer(), prompt="Multi page parsing.", image_files=imgs,
                                 save_results=False, output_path="", max_new_tokens=8000 * pages, **kw)

    def test_import_fallback_cache_growth_and_native_capture(self):
        mod, model, resolved, unresolved = self.load()
        self.assertEqual(unresolved, ["sparse_gather_e2e_triton:triton_gather_attention_e2e"])
        self.assertEqual(len(resolved), len(TARGETS) - 1)
        with NativeObserver(resolved, unresolved) as obs:
            mark = obs.begin_window()
            text, n = self.call(mod, model)
            win = obs.end_window(mark)
        kp = win["kernel_path"]
        self.assertEqual(kp["label"], "triton_import_failed_dense_fallback")
        self.assertEqual((kp["triton_attempts"], kp["triton_non_null_returns"], kp["dense_sdpa_calls"]), (1, 0, 1))
        self.assertEqual(kp["triton_import_exception_types"], ["builtins.ModuleNotFoundError"])
        self.assertEqual(kp["decode_forward_calls"], n)
        self.assertEqual(kp["decode_attend_fp32_calls"], n)
        self.assertEqual(kp["non_dash_attention_calls"], 0)
        c = win["cache"]
        self.assertTrue(c["observed"] and c["grows_by_one_each_decode_step"])
        self.assertEqual(c["prefill_seq_len"], 1 + 3 * 274 + 3)
        self.assertEqual(c["final_seq_len"], c["prefill_seq_len"] + n)
        self.assertEqual(c["kv_bytes_per_token_derived"], 2 * 12 * 10 * 128 * 2)
        self.assertFalse(c["ring_buffer_marker_seen"])
        nat = win["native_results"]
        self.assertEqual(len(nat), 1)
        self.assertEqual((nat[0]["text"], nat[0]["output_tokens"], nat[0]["finish_reason"], nat[0]["num_pages_out"]),
                         (text, n, "stop", 3))
        self.assertEqual(win["violations"], [])
        self.assertGreater(win["observer_overhead"]["callback_ns"], 0)
        # Observer removed: the tool id is free again and no callbacks fire.
        sys.monitoring.use_tool_id(TOOL_ID, "probe")
        sys.monitoring.free_tool_id(TOOL_ID)

    def test_executed_and_propagated_kernel_paths(self):
        mod, model, resolved, unresolved = self.load(triton_stub=True)
        self.assertEqual(unresolved, [])
        with NativeObserver(resolved, unresolved) as obs:
            mark = obs.begin_window()
            self.call(mod, model, pages=1)
            win = obs.end_window(mark)
            self.assertEqual(win["kernel_path"]["label"], "triton_executed")
            self.assertEqual((win["kernel_path"]["triton_kernel_entries"], win["kernel_path"]["dense_sdpa_calls"]), (1, 0))
            # A kernel exception is not caught natively: observed as propagated, never hidden.
            orig = mod.DynamicCache.__init__
            def init(self):
                orig(self)
                self.raise_in_kernel = True
            mod.DynamicCache.__init__ = init  # test double only; never done to the real model
            mark = obs.begin_window()
            with self.assertRaises(RuntimeError):
                self.call(mod, model, pages=1)
            win = obs.end_window(mark)
            self.assertEqual(win["kernel_path"]["label"], "triton_exception_propagated")

    def test_tripwire_blocks_save_path_even_under_bare_except(self):
        mod, model, resolved, unresolved = self.load()
        # A broken freeze (save_results=True with a path) is stopped at the gate before any save code runs.
        with NativeObserver(resolved, unresolved) as obs:
            mark = obs.begin_window()
            with self.assertRaises(SafetyTripwire):
                model.infer_multi(mod.FakeTokenizer(), prompt="p", image_files=[object()], save_results=True,
                                  output_path=str(self.scratch / "must-not-exist"), max_new_tokens=8000)
            win = obs.end_window(mark)
        self.assertEqual([v["target"] for v in win["violations"]], ["UnlimitedOCRForCausalLM._uocr_save_results"])
        self.assertFalse((self.scratch / "must-not-exist").exists())
        # Entering a deeper link directly is also stopped and recorded.
        with NativeObserver(resolved, unresolved) as obs:
            mark = obs.begin_window()
            with self.assertRaises(SafetyTripwire):
                mod.draw_bounding_boxes(None, [("a", "b", "[1, 2]")], "o")
            win = obs.end_window(mark)
        self.assertEqual(win["violations"][0]["target"], "draw_bounding_boxes")

    def test_extract_site_tripwire_recorded_when_swallowed(self):
        mod, model, resolved, unresolved = self.load()
        import os
        os.environ.pop("Q0_EVAL_RAN", None)
        code = "__import__('os').environ.__setitem__('Q0_EVAL_RAN', '1')"
        # Control: without the observer, this fake eval site does execute the payload.
        mod.extract_coordinates_and_label(("a", "b", code), 1, 1)
        self.assertEqual(os.environ.pop("Q0_EVAL_RAN", None), "1")
        with NativeObserver(resolved, unresolved) as obs:
            mark = obs.begin_window()
            # A caller reaching the eval site through a bare-except loop swallows the tripwire...
            try:
                mod.extract_coordinates_and_label(("a", "b", code), 1, 1)
            except:  # noqa: E722
                pass
            win = obs.end_window(mark)
        # ...but the payload never ran and the violation is recorded regardless.
        self.assertNotIn("Q0_EVAL_RAN", os.environ)
        self.assertEqual(win["violations"][0]["role"], "forbidden_eval_site")

    def test_required_target_missing_is_unsupported(self):
        mod, model, resolved, unresolved = self.load()
        with self.assertRaises(Q0Failure) as cm:
            resolve_targets(sys.modules, prefix="transformers_modules.absent_pkg.")
        self.assertEqual(cm.exception.failure_class, "TELEMETRY_UNSUPPORTED")


if __name__ == "__main__":
    unittest.main()
