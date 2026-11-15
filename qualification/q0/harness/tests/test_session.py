"""End-to-end bookkeeping of the execution session against the fake model package and
real committed fixtures/raster contracts (no torch, no GPU)."""

import json
import shutil
import unittest

import support
from q0harness.outcome import BLOCKED, NOT_QUALIFIED, QUALIFIED
from q0harness.protocol import REPO_ROOT


class SessionBookkeeping(unittest.TestCase):
    def setUp(self):
        self.scratches = []

    def tearDown(self):
        support.purge_fake_modules()
        for s in self.scratches:
            support.remove_scratch(s)

    def run_kit(self, tag, **kw):
        session, backend, scratch, run_dir = support.session_kit(tag, **kw)
        self.scratches.append(scratch)
        outcome = session.run()
        on_disk = json.loads((run_dir / "evidence" / "outcome.json").read_text(encoding="utf-8"))
        self.assertEqual(on_disk["status"], outcome["status"])
        self.assertIsNone(outcome["accuracy_score"])
        return outcome, backend, run_dir

    def classes(self, outcome):
        return sorted({f["failure_class"] for f in outcome["failures"]})

    def test_qualified_path_records_everything(self):
        out, be, run_dir = self.run_kit("happy")
        self.assertEqual(out["status"], QUALIFIED, out["failures"])
        obs = out["observations"]
        self.assertEqual([(o["family_id"], o["kind"], o["repeat"]) for o in obs],
                         [("F01", "warmup", 0), ("F07", "warmup", 0), ("F01", "warm", 1), ("F07", "warm", 1),
                          ("F01", "warm", 2), ("F07", "warm", 2)])
        self.assertEqual(be.invocations, 6)
        for o in obs:
            self.assertEqual(o["excluded_from_warm_statistics"], o["kind"] == "warmup")
            self.assertEqual(o["call_kwargs"]["save_results"], False)
            self.assertEqual(o["call_kwargs"]["output_path"], "")
            self.assertEqual(o["native"]["finish_reason"], "stop")
            self.assertEqual(o["page_markers"]["out"], o["page_count_in"])
            self.assertEqual(len(o["page_markers"]["marker_token_positions"]), o["page_count_in"])
            self.assertEqual(o["kernel_path"]["label"], "triton_import_failed_dense_fallback")
            self.assertTrue(o["cache"]["grows_by_one_each_decode_step"])
            self.assertEqual(o["timing"]["decode_s"]["provenance"], "derived")
            self.assertEqual(o["timing"]["external_synchronized_wall_s"]["provenance"], "direct")
            raw = (run_dir / "evidence" / o["raw_output"]["name"]).read_text(encoding="utf-8")
            self.assertEqual(raw.count("<PAGE>"), o["page_count_in"])
            self.assertFalse(o["raw_output"]["truncated_by_writer"])
        self.assertTrue(all(r["warm_repeats_identical"] for r in out["checks"]["5_smoke_execution"]["repeatability"].values()))
        self.assertEqual(sorted(out["checks"]), ["1_storage_isolation", "2_artifact_dependency_lock",
                                                 "3_save_results_invariant", "4_kernel_cache_telemetry",
                                                 "5_smoke_execution", "6_honest_failure_accounting"])
        self.assertTrue(all(c["status"] == "pass" for c in out["checks"].values()))
        self.assertEqual(len(out["checks"]["2_artifact_dependency_lock"]["rendered_pages"]["SYN-MP-01-v0-clean"]), 3)
        mc = json.loads((run_dir / "evidence" / "module-cache.json").read_text(encoding="utf-8"))
        self.assertTrue(all(m["identical"] for m in mc["modules"]))
        self.assertTrue((run_dir / "heartbeat.json").is_file())
        c2, c4 = out["checks"]["2_artifact_dependency_lock"], out["checks"]["4_kernel_cache_telemetry"]
        self.assertEqual(c2["lock_counts"], {"publisher-declared": 31, "local-sha256-TOFU": 1, "missing": 0})
        self.assertEqual(c2["model_runtime_objects_verified"], 18)
        self.assertTrue(c2["triton_find_spec_none"] and c4["triton_find_spec_none"])
        self.assertEqual(c4["baseline_label"], "unmodified model on non-Triton fallback path")
        self.assertEqual(out["context"]["code_identity"]["head"], "c" * 40)
        self.assertEqual(out["context"]["release"]["accepted_provenance_exceptions"], ["torchvision-local-sha256-TOFU"])
        for o in obs:  # prefill-boundary allocator probe: exactly one read per call window
            self.assertEqual(o["prefill_memory"]["provenance"], "direct")
            self.assertEqual(o["prefill_memory"]["value"]["max_reserved"], 2000)
        self.assertEqual(be.probes, 6)

    def test_executed_triton_path_is_not_the_frozen_baseline(self):
        out, _, _ = self.run_kit("tritonstub", triton_stub=True)
        self.assertEqual(out["status"], NOT_QUALIFIED)
        self.assertEqual(self.classes(out), ["TELEMETRY_UNSUPPORTED"])
        self.assertEqual({o["kernel_path"]["label"] for o in out["observations"]}, {"triton_executed"})
        self.assertIsNone(out["checks"]["4_kernel_cache_telemetry"]["baseline_label"])

    def assert_blocked_before_load(self, tag, expect, **kw):
        out, be, _ = self.run_kit(tag, **kw)
        self.assertEqual(out["status"], BLOCKED)
        self.assertEqual(self.classes(out), [expect])
        self.assertFalse(be.load_called, "model load must not happen after a preflight failure")
        self.assertEqual(be.invocations, 0)

    def test_gates_fail_closed_before_any_model_load(self):
        from collections import namedtuple
        du = namedtuple("du", "total used free")
        self.assert_blocked_before_load("nolease", "EXECUTION_NOT_RELEASED", release_mutation=lambda r: None)
        self.assert_blocked_before_load("wrongseq", "EXECUTION_NOT_RELEASED", release_mutation=lambda r: r | {"sequence": "002"})
        self.assert_blocked_before_load("installstage", "EXECUTION_NOT_RELEASED", release_mutation=lambda r: r | {"stage": "install"})
        self.assert_blocked_before_load("wronggpu", "EXECUTION_NOT_RELEASED",
                                        release_mutation=lambda r: r | {"gpu_uuid": "GPU-00000000-0000-0000-0000-000000000000"})
        self.assert_blocked_before_load("dirtycode", "EXECUTION_NOT_RELEASED",
                                        code=support.FAKE_CODE | {"harness_clean": False})
        self.assert_blocked_before_load("hashgap", "ACQUISITION_PROVENANCE_PENDING",
                                        lock=support.without_local_records(support.committed_lock()))
        self.assert_blocked_before_load("noexception", "ACQUISITION_PROVENANCE_PENDING",
                                        release_mutation=lambda r: r | {"accepted_provenance_exceptions": []})
        self.assert_blocked_before_load("floor", "STORAGE_FLOOR", disk_usage=lambda p: du(10 ** 12, 0, 10 ** 9))
        self.assert_blocked_before_load("nonotice", "HASH_MISMATCH", no_notice=True)
        self.assert_blocked_before_load("cputorch", "DEPENDENCY_MISMATCH", opts={"extra_installed": {"torch": "2.13.0"}})
        self.assert_blocked_before_load("capab", "UNSUPPORTED_PLATFORM", opts={"platform_override": {"device_capability": [8, 9]}})
        self.assert_blocked_before_load("noarch", "UNSUPPORTED_PLATFORM", opts={"platform_override": {"arch_list": ["sm_90"]}})
        self.assert_blocked_before_load("py", "UNSUPPORTED_PLATFORM", opts={"platform_override": {"python": "3.10.11"}})
        self.assert_blocked_before_load("flash", "DEPENDENCY_MISMATCH", opts={"importable": ("flash_attn",)})
        self.assert_blocked_before_load("tritonpolicy", "DEPENDENCY_MISMATCH", opts={"importable": ("triton",)})
        self.assert_blocked_before_load("render", "RENDER_CONTRACT_MISMATCH", opts={"corrupt_render": True})
        self.assert_blocked_before_load("modeltamper", "HASH_MISMATCH", model_tamper=True)

    def test_tampered_fixture_blocks(self):
        scratch = support.new_scratch("repo-copy")
        self.scratches.append(scratch)
        for rel in ("evaluation/synthetic/pdfs/F01/SYN-WO-01-v0-clean.pdf", "evaluation/synthetic/pdfs/F07/SYN-MP-01-v0-clean.pdf"):
            (scratch / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(REPO_ROOT / rel, scratch / rel)
        p = scratch / "evaluation/synthetic/pdfs/F07/SYN-MP-01-v0-clean.pdf"
        p.write_bytes(p.read_bytes().replace(b"%PDF-1.4", b"%PDF-1.5", 1))
        self.assert_blocked_before_load("fxtamper", "HASH_MISMATCH", repo_root=scratch)

    def test_module_cache_divergence_blocks_after_load_without_calls(self):
        out, be, _ = self.run_kit("cachetamper", opts={"tamper_cache": "modeling_deepseekv2.py"})
        self.assertEqual((out["status"], self.classes(out)), (BLOCKED, ["HASH_MISMATCH"]))
        self.assertTrue(be.load_called)
        self.assertEqual(be.invocations, 0)

    def test_nondeterminism_is_a_failure_not_a_score(self):
        out, be, _ = self.run_kit("flaky", opts={"flaky": True})
        self.assertEqual(out["status"], NOT_QUALIFIED)
        self.assertEqual(self.classes(out), ["NONDETERMINISTIC_OUTPUT"])
        self.assertEqual(be.invocations, 6)

    def test_truncation_flagged(self):
        out, _, _ = self.run_kit("trunc", opts={"force_length": True})
        self.assertEqual(out["status"], NOT_QUALIFIED)
        self.assertIn("TRUNCATION", self.classes(out))
        self.assertTrue(all(o["native"]["finish_reason"] == "length" for o in out["observations"]))

    def test_oom_stops_further_calls(self):
        out, be, run_dir = self.run_kit("oom", opts={"oom_on_invocation": 2})
        self.assertEqual(self.classes(out), ["OOM"])
        self.assertEqual(be.invocations, 2)
        self.assertEqual(out["status"], NOT_QUALIFIED)
        self.assertEqual([("error" in o) for o in out["observations"]], [False, True])
        self.assertEqual(out["observations"][1]["error"]["failure_class"], "OOM")
        err = json.loads((run_dir / "evidence" / "F07.warmup.observation.json").read_text(encoding="utf-8"))
        self.assertEqual(err["error"]["failure_class"], "OOM")

    def test_save_path_entry_is_a_safety_violation(self):
        out, be, _ = self.run_kit("savepath", opts={"enter_save_path_on_invocation": 3})
        self.assertEqual(self.classes(out), ["SAFETY_VIOLATION"])
        self.assertEqual(be.invocations, 3)
        self.assertEqual(out["observations"][-1]["safety_violations"][0]["target"],
                         "UnlimitedOCRForCausalLM._uocr_save_results")


if __name__ == "__main__":
    unittest.main()
