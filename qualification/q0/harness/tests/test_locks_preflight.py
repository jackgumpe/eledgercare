import copy
import json
import subprocess
import sys
import unittest

import support
from q0harness.locks import load_lock, requirements_text, validate_lock, verify_installed, verify_wheelhouse
from q0harness.outcome import Q0Failure
from q0harness.preflight import cpu_preflight
from q0harness.protocol import HARNESS_DIR, load_protocol


class Locks(unittest.TestCase):
    def test_committed_lock_is_pending_and_blocks(self):
        lock = load_lock(HARNESS_DIR / "locks/dependency-lock.json")
        with self.assertRaises(Q0Failure) as cm:
            validate_lock(lock)
        self.assertEqual(cm.exception.failure_class, "DEPENDENCY_LOCK_PENDING")
        self.assertIsNone(lock["provenance"]["astra_001"])
        self.assertEqual(lock["fixed_by_accepted_specification"]["transformers"], "4.52.1")

    def test_final_lock_shape_enforced(self):
        good = support.final_lock()
        self.assertEqual(len(validate_lock(good)), 14)
        mutations = [
            lambda l: l["packages"].pop(0),
            lambda l: l["packages"][2].__setitem__("version", "4.53.0"),
            lambda l: l["packages"][0].__setitem__("version", ">=2.13"),
            lambda l: l["packages"][0].__setitem__("sha256", "abc"),
            lambda l: l["packages"][0].__setitem__("index_url", "http://insecure"),
            lambda l: l["packages"].append(copy.deepcopy(l["packages"][0])),
            lambda l: l["platform"].__setitem__("python", "3.12"),
            lambda l: l["cuda"].__setitem__("device_capability", [8, 9]),
            lambda l: l.__setitem__("triton_policy", "maybe"),
            lambda l: l.__setitem__("triton_policy", "present"),
            lambda l: l["provenance"].__setitem__("review_003", None),
        ]
        for i, m in enumerate(mutations):
            with self.subTest(i=i):
                lock = copy.deepcopy(good)
                m(lock)
                with self.assertRaises(Q0Failure):
                    validate_lock(lock)

    def test_installed_set_exact(self):
        lock = support.final_lock()
        inst = {p["name"]: p["version"] for p in lock["packages"]} | {"pip": "24"}
        self.assertEqual(verify_installed(lock, inst, lambda m: False)["triton_policy"], "absent")
        for bad_inst, imp in [(inst | {"flash-attn": "2.7"}, lambda m: False), (inst | {"numpy": "1.26.0"}, lambda m: False),
                              (inst, lambda m: m == "xformers"), (inst, lambda m: m == "triton")]:
            with self.assertRaises(Q0Failure) as cm:
                verify_installed(lock, bad_inst, imp)
            self.assertEqual(cm.exception.failure_class, "DEPENDENCY_MISMATCH")

    def test_requirements_and_wheelhouse(self):
        lock = support.final_lock()
        text = requirements_text(lock)
        self.assertEqual(len(text.splitlines()), 14)
        self.assertTrue(all(" --hash=sha256:" in line and "==" in line for line in text.splitlines()))
        d = support.new_scratch("wheelhouse")
        try:
            for p in lock["packages"]:
                data = p["name"].encode()
                (d / p["filename"]).write_bytes(data)
                p["sha256"] = __import__("hashlib").sha256(data).hexdigest()
            self.assertEqual(len(verify_wheelhouse(lock, d)["wheels"]), 14)
            (d / "unlocked-1.0-py3-none-any.whl").write_bytes(b"x")
            with self.assertRaises(Q0Failure):
                verify_wheelhouse(lock, d)
            (d / "unlocked-1.0-py3-none-any.whl").unlink()
            (d / lock["packages"][0]["filename"]).write_bytes(b"tampered")
            with self.assertRaises(Q0Failure):
                verify_wheelhouse(lock, d)
        finally:
            support.remove_scratch(d)

    def test_install_stage_cli_refuses_pending_lock(self):
        d = support.new_scratch("cli-pending")
        try:
            cp = subprocess.run([sys.executable, "-I", "-B", str(HARNESS_DIR / "q0.py"), "write-requirements",
                                 str(d / "req.txt")], capture_output=True, text=True, timeout=120)
            self.assertEqual(cp.returncode, 2, cp.stderr)
            self.assertEqual(json.loads(cp.stdout)["failures"][0]["failure_class"], "DEPENDENCY_LOCK_PENDING")
            self.assertFalse((d / "req.txt").exists())
        finally:
            support.remove_scratch(d)


class CpuPreflight(unittest.TestCase):
    def test_preflight_with_fake_renderer_and_model_dir(self):
        protocol, _ = load_protocol()
        lock = support.final_lock()
        d = support.new_scratch("preflight")
        try:
            support.write_fake_model_dir(d / "m")
            (d / "mf.json").write_text(json.dumps(support.manifest_for_dir(d / "m")), encoding="utf-8")
            inst = {p["name"]: p["version"] for p in lock["packages"]}
            kw = dict(protocol=protocol, lock=lock, installed=inst, importable=lambda m: False,
                      dist_version=lambda n: "5.15.2", model_dir=d / "m", manifest_path=d / "mf.json")
            rep = cpu_preflight(pdfium=support.FakePdfium(protocol), **kw)
            self.assertEqual(rep["status"], "pass")
            self.assertEqual(len(rep["rasters"]["SYN-MP-01-v0-clean"]), 3)
            with self.assertRaises(Q0Failure) as cm:
                cpu_preflight(pdfium=support.FakePdfium(protocol, corrupt=True), **kw)
            self.assertEqual(cm.exception.failure_class, "RENDER_CONTRACT_MISMATCH")
            with self.assertRaises(Q0Failure) as cm:
                cpu_preflight(pdfium=support.FakePdfium(protocol), **(kw | {"dist_version": lambda n: "4.30.0"}))
            self.assertEqual(cm.exception.failure_class, "RENDER_CONTRACT_MISMATCH")
        finally:
            support.remove_scratch(d)


if __name__ == "__main__":
    unittest.main()
