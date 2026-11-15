import json
import shutil
import unittest

import support
from q0harness import modelfiles, sourcecheck
from q0harness.fixtures import derive_predicted_rasters, read_verified_fixture, verify_rendered_pages
from q0harness.outcome import Q0Failure
from q0harness.protocol import HARNESS_DIR, REPO_ROOT, load_protocol


class UpstreamSnapshotsAndStaticSafety(unittest.TestCase):
    def test_snapshots_are_pinned_hf_blobs(self):
        rows = sourcecheck.verify_snapshots(REPO_ROOT)
        names = {r["upstream_path"] for r in rows}
        self.assertTrue({"modeling_unlimitedocr.py", "modeling_deepseekv2.py", "dash_attention.py", "_sparse_base_impl.py",
                         "sparse_gather_e2e_triton.py", "config.json", "generation_config.json"} <= names)
        self.assertTrue(all(r["tree_oid_ok"] and r["manifest_sha256_ok"] for r in rows))

    def test_static_save_path_analysis_on_pinned_source(self):
        facts = sourcecheck.analyze_model_sources(sourcecheck.SNAPSHOT_DIR, sourcecheck.SNAPSHOT_NAMES)
        e = facts["entry"]
        self.assertEqual([(s["line"], s["builtin"]) for s in e["eval_sites"]], [(120, "eval")])
        self.assertEqual(e["save_guard_lines"], [1103])
        self.assertEqual(e["infer_multi_crop_default"], [False])
        self.assertTrue(e["decode_disables_ring_window"] and e["uses_dynamic_cache"])
        self.assertTrue(sourcecheck.NATIVE_RETURN_KEYS <= set(e["native_return_keys"]))

    def _mutant(self, old, new):
        src = (sourcecheck.SNAPSHOT_DIR / "hf-modeling_unlimitedocr.py.txt").read_text(encoding="utf-8")
        self.assertIn(old, src)
        with self.assertRaises(Q0Failure) as cm:
            sourcecheck.analyze_entry_module(src.replace(old, new, 1))
        self.assertEqual(cm.exception.failure_class, "SAFETY_VIOLATION")

    def test_mutations_are_detected(self):
        self._mutant("if save_results and output_path:", "if save_results or output_path:")
        self._mutant("if save_results and output_path:", "if save_results:")
        self._mutant("kwargs.setdefault('crop_mode', False)", "kwargs.setdefault('crop_mode', True)")
        self._mutant("        outputs = res['text']\n", "        outputs = res['text']\n        self._uocr_save_results(outputs, images, output_path)\n")
        self._mutant("def re_match(text):", "def re_match(text):\n    eval(text)")
        self._mutant("'finish_reason': finish, ", "")


class FixturesAndRasters(unittest.TestCase):
    def setUp(self):
        self.p, _ = load_protocol()

    def test_dev_fixtures_verified(self):
        for f in self.p["fixtures"]:
            self.assertEqual(len(read_verified_fixture(f)), f["size_bytes"])

    def test_raster_predictions_derive_from_committed_dev_children(self):
        for f in self.p["fixtures"]:
            got = derive_predicted_rasters(f)
            self.assertEqual(got, [{k: r[k] for k in ("page", "width", "height", "rgb_sha256")} for r in f["raster"]])

    def test_v1_child_was_generated_from_these_v0_bytes(self):
        manifest = json.loads((REPO_ROOT / "evaluation/manifests/corpus-manifest.json").read_text(encoding="utf-8"))
        dev = {x["fixture_id"]: x for x in manifest["fixtures"]
               if x["fixture_id"] in ("SYN-WO-01-v0-clean", "SYN-WO-01-v1-raster300", "SYN-MP-01-v0-clean", "SYN-MP-01-v1-raster300")}
        for f in self.p["fixtures"]:
            v0, v1 = dev[f["fixture_id"]], dev[f["fixture_id"].replace("v0-clean", "v1-raster300")]
            self.assertEqual((v0["sha256"], v0["git_blob_oid"], v0["split"], v0["page_count"]),
                             (f["sha256"], f["git_blob_oid"], "dev", f["page_count"]))
            self.assertEqual(v1["parent_pdf_sha256"], f["sha256"])
            self.assertEqual(v1["sha256"], f["raster_derivation"]["v1_raster300_sha256"])
            self.assertEqual(v1["generation_or_transform_params"]["pixel_size_per_page"], [2550, 3301])

    def test_tampered_fixture_fails_closed(self):
        scratch = support.new_scratch("fixture-tamper")
        try:
            f = self.p["fixtures"][0]
            dst = scratch / f["path"]
            dst.parent.mkdir(parents=True)
            data = bytearray((REPO_ROOT / f["path"]).read_bytes())
            data[-10] ^= 1
            dst.write_bytes(bytes(data))
            with self.assertRaises(Q0Failure) as cm:
                read_verified_fixture(f, scratch)
            self.assertEqual(cm.exception.failure_class, "HASH_MISMATCH")
        finally:
            support.remove_scratch(scratch)

    def test_rendered_page_contract(self):
        f = self.p["fixtures"][1]
        pages = support.FakePdfium(self.p).by_sha[f["sha256"]]
        ok = [(p["width"], p["height"], p["rgb"]) for p in pages]
        self.assertEqual(len(verify_rendered_pages(f, ok)), 3)
        bad_byte = list(ok)
        bad_byte[2] = (ok[2][0], ok[2][1], ok[2][2][:-1] + bytes([ok[2][2][-1] ^ 1]))
        for bad in (ok[:2], ok[::-1], [(2550, 3302, ok[0][2])] + ok[1:], bad_byte):
            with self.assertRaises(Q0Failure) as cm:
                verify_rendered_pages(f, bad)
            self.assertEqual(cm.exception.failure_class, "RENDER_CONTRACT_MISMATCH")


class ModelDirectoryVerification(unittest.TestCase):
    def test_committed_manifest_matches_pinned_tree(self):
        tree = json.loads(sourcecheck.HF_TREE.read_text(encoding="utf-8"))
        derived = modelfiles.build_manifest_from_tree(tree)
        committed = modelfiles.load_manifest(HARNESS_DIR / "manifests/model-files.json")
        self.assertEqual(derived, committed)
        self.assertEqual(committed["weight_bytes"], 6688305576)
        py = [f for f in committed["files"] if f["path"].endswith(".py")]
        self.assertEqual(len(py), 10)

    def test_verify_model_dir_fail_closed(self):
        scratch = support.new_scratch("modeldir")
        try:
            d = scratch / "m"
            support.write_fake_model_dir(d)
            manifest = support.manifest_for_dir(d)
            rep = modelfiles.verify_model_dir(d, manifest)
            self.assertTrue(all(r["ok"] for r in rep["files"]))
            meta = d / ".cache" / "huggingface" / "download"
            meta.mkdir(parents=True)
            (meta / "config.json.metadata").write_text("x")
            self.assertEqual(modelfiles.verify_model_dir(d, manifest)["tolerated_metadata"],
                             [".cache/huggingface/download/config.json.metadata"])
            cases = []
            (meta / "evil.py").write_text("x"); cases.append(("UNEXPECTED_ARTIFACT", lambda: (meta / "evil.py").unlink()))
            for expect, undo in cases:
                with self.assertRaises(Q0Failure) as cm:
                    modelfiles.verify_model_dir(d, manifest)
                self.assertEqual(cm.exception.failure_class, expect)
                undo()
            (d / "extra_module.py").write_text("x")
            with self.assertRaises(Q0Failure) as cm:
                modelfiles.verify_model_dir(d, manifest)
            self.assertEqual(cm.exception.failure_class, "UNEXPECTED_ARTIFACT")
            (d / "extra_module.py").unlink()
            shard = d / "model-00002-of-00002.safetensors"
            shard.write_bytes(shard.read_bytes()[:-1] + b"?")
            with self.assertRaises(Q0Failure) as cm:
                modelfiles.verify_model_dir(d, manifest)
            self.assertEqual(cm.exception.failure_class, "HASH_MISMATCH")
            shard.unlink()
            with self.assertRaises(Q0Failure) as cm:
                modelfiles.verify_model_dir(d, manifest)
            self.assertEqual(cm.exception.failure_class, "HASH_MISMATCH")
        finally:
            support.remove_scratch(scratch)

    def test_fake_model_dir_passes_the_same_static_analysis(self):
        scratch = support.new_scratch("fakestatic")
        try:
            d = scratch / "m"
            support.write_fake_model_dir(d)
            facts = sourcecheck.analyze_model_sources(d, sourcecheck.MODEL_DIR_NAMES)
            self.assertEqual(len(facts["eval_exec_compile_sites_all_modules"]), 1)
            shutil.copy(d / "modeling_unlimitedocr.py", d / "dash_attention.py")  # eval outside entry module
            with self.assertRaises(Q0Failure):
                sourcecheck.analyze_model_sources(d, sourcecheck.MODEL_DIR_NAMES)
        finally:
            support.remove_scratch(scratch)


if __name__ == "__main__":
    unittest.main()
