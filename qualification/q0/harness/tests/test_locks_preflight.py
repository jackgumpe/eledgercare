import copy
import hashlib
import io
import json
import subprocess
import sys
import unittest
import zipfile

import support
from q0harness import locks
from q0harness.locks import (inspect_wheel_metadata, readiness, require_installable, requirements_text,
                             validate_lock, verify_installed, verify_wheelhouse)
from q0harness.outcome import Q0Failure
from q0harness.preflight import cpu_preflight
from q0harness.protocol import HARNESS_DIR, load_protocol
from q0harness.release import validate_release


def tv_metadata(requires="torch (==2.13.0)", version="0.28.0+cu130") -> bytes:
    return (f"Metadata-Version: 2.1\nName: torchvision\nVersion: {version}\nRequires-Dist: numpy\n"
            f"Requires-Dist: {requires}\n\nbody\n").encode()


def wheel_bytes(meta: bytes, name="torchvision-0.28.0+cu130.dist-info/METADATA") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("torchvision/__init__.py", "")
        z.writestr(name, meta)
    return buf.getvalue()


class BoundLock(unittest.TestCase):
    def test_committed_lock_binds_astra_007_and_blocks_install(self):
        lock = support.committed_lock()
        self.assertEqual(lock["source"]["commit"], "d666c4163b8b6bdf5f6c69b455c30f3c377cbdc5")
        pkgs = validate_lock(lock, support.git_reader())
        r = readiness(pkgs)
        self.assertEqual(len(pkgs), 32)
        self.assertEqual(r["counts"], {"publisher-declared": 31, "local-sha256-TOFU": 0, "missing": 1})
        self.assertEqual(r["missing_wheel_sha256"], ["torchvision"])
        self.assertFalse(r["installable"])
        self.assertIsNone(pkgs["torchvision"]["effective_sha256"])
        self.assertEqual(pkgs["torch"]["version"], "2.13.0+cu130")
        self.assertEqual(pkgs["torch"]["effective_sha256"],
                         "2efab1e83604ca628c6d85b9e188c153690980498d1297081a9dad704919303c")
        with self.assertRaises(Q0Failure) as cm:
            require_installable(pkgs, None)
        self.assertEqual(cm.exception.failure_class, "ACQUISITION_PROVENANCE_PENDING")
        with self.assertRaises(Q0Failure):
            requirements_text(pkgs)

    def test_lock_is_not_circular(self):
        text = (HARNESS_DIR / "locks/dependency-lock.json").read_text(encoding="utf-8")
        self.assertNotIn("review_003", text)
        self.assertNotIn("accepted_review", text)
        for bad in ({"accepted_review": {"report_commit": "a" * 40}},
                    {"lineage": {"review_003": {"report": "a" * 40}}}):
            lock = support.committed_lock() | bad
            with self.assertRaises(Q0Failure):
                validate_lock(lock, support.git_reader())

    def test_source_binding_fails_closed(self):
        good = support.committed_lock()
        real = support.git_reader()
        data = real(good["source"]["git_blob"])
        cases = {
            "altered bytes": lambda oid: data.replace(b'"size": 9091113', b'"size": 9091114', 1),
            "missing object": lambda oid: (_ for _ in ()).throw(Q0Failure("DEPENDENCY_LOCK_PENDING", "absent")),
        }
        for label, reader in cases.items():
            with self.subTest(label):
                with self.assertRaises(Q0Failure) as cm:
                    validate_lock(good, reader)
                self.assertEqual(cm.exception.failure_class, "DEPENDENCY_LOCK_PENDING")
        mutations = [
            lambda l: l["platform"]["marker_environment"].__setitem__("platform_machine", "amd64"),
            lambda l: l["platform"].__setitem__("python", "3.12.9"),
            lambda l: l["expect"].__setitem__("artifact_count", 31),
            lambda l: l["expect"].__setitem__("missing_publisher_hash", []),
            lambda l: l.__setitem__("triton_policy", "present"),
            lambda l: l["cuda"].__setitem__("device_capability", [8, 9]),
            lambda l: l["source"].__setitem__("status", "final"),
        ]
        for i, m in enumerate(mutations):
            with self.subTest(i=i):
                lock = copy.deepcopy(good)
                m(lock)
                with self.assertRaises(Q0Failure):
                    validate_lock(lock, real)

    def test_local_record_rules(self):
        pkgs = support.lock_pkgs(support.final_lock())
        r = readiness(pkgs)
        self.assertTrue(r["installable"])
        self.assertEqual(r["required_exceptions"], ["torchvision-local-sha256-TOFU"])
        self.assertEqual(pkgs["torchvision"]["effective_kind"], "local-sha256-TOFU")
        with self.assertRaises(Q0Failure) as cm:
            require_installable(pkgs, {"accepted_provenance_exceptions": []})
        self.assertEqual(cm.exception.failure_class, "ACQUISITION_PROVENANCE_PENDING")
        require_installable(pkgs, {"accepted_provenance_exceptions": ["torchvision-local-sha256-TOFU"]})
        bad_records = [
            lambda rec: rec.__setitem__("hash_kind", "publisher-declared"),
            lambda rec: rec.__setitem__("size", 9091112),
            lambda rec: rec.__setitem__("metadata_sha256", "0" * 64),
            lambda rec: rec.__setitem__("sha256", "xyz"),
            lambda rec: rec["receipt"].__setitem__("commit", None),
            lambda rec: rec.__setitem__("name", "torch"),
        ]
        for i, m in enumerate(bad_records):
            with self.subTest(i=i):
                lock = support.final_lock()
                m(lock["local_hash_records"][0])
                with self.assertRaises(Q0Failure):
                    support.lock_pkgs(lock)
        lines = requirements_text(pkgs).splitlines()
        self.assertEqual(len(lines), 32)
        self.assertIn(f"torchvision==0.28.0+cu130 --hash=sha256:{support.FAKE_TOFU_SHA}", lines)
        self.assertIn("torch==2.13.0+cu130 --hash=sha256:2efab1e83604ca628c6d85b9e188c153690980498d1297081a9dad704919303c", lines)

    def test_installed_set_exact_and_backends_absent(self):
        lock = support.final_lock()
        pkgs = support.lock_pkgs(lock)
        inst = {a["name"]: a["version"] for a in pkgs.values()} | {"pip": "25.0.1"}
        rep = verify_installed(pkgs, lock, inst, lambda m: False)
        self.assertIn("triton", rep["forbidden_absent_find_spec_none"])
        for bad_inst, imp in [(inst | {"flash-attn": "2.7"}, lambda m: False),
                              (inst | {"torch": "2.13.0"}, lambda m: False),  # CPU torch confusion (Q0R-08)
                              (inst, lambda m: m == "xformers"), (inst, lambda m: m == "triton")]:
            with self.assertRaises(Q0Failure) as cm:
                verify_installed(pkgs, lock, bad_inst, imp)
            self.assertEqual(cm.exception.failure_class, "DEPENDENCY_MISMATCH")

    def test_wheelhouse_sizes_hashes_and_tofu_metadata(self):
        d = support.new_scratch("wheelhouse")
        try:
            meta = tv_metadata()
            gap = support.committed_lock()["hash_gaps"][0]
            # Synthetic lock whose expectations match synthetic wheels (test-only rewrite of sizes/hashes).
            lock = support.final_lock()
            pkgs = support.lock_pkgs(lock)
            for a in pkgs.values():
                data = wheel_bytes(meta) if a["name"] == "torchvision" else a["name"].encode()
                (d / a["filename"]).write_bytes(data)
                a["size"], a["effective_sha256"] = len(data), hashlib.sha256(data).hexdigest()
            gap_lock = copy.deepcopy(lock)
            gap_lock["hash_gaps"][0]["published_metadata_sha256"] = hashlib.sha256(meta).hexdigest()
            self.assertEqual(len(verify_wheelhouse(pkgs, d, gap_lock)["wheels"]), 32)
            # METADATA digest differing from the published PEP 658 digest fails.
            with self.assertRaises(Q0Failure):
                verify_wheelhouse(pkgs, d, lock)
            (d / "unlocked-1.0-py3-none-any.whl").write_bytes(b"x")
            with self.assertRaises(Q0Failure):
                verify_wheelhouse(pkgs, d, gap_lock)
            (d / "unlocked-1.0-py3-none-any.whl").unlink()
            (d / pkgs["numpy"]["filename"]).write_bytes(b"tampered")
            with self.assertRaises(Q0Failure):
                verify_wheelhouse(pkgs, d, gap_lock)
            self.assertEqual(gap["required_requires_dist"], "torch (==2.13.0)")
        finally:
            support.remove_scratch(d)

    def test_inspect_wheel_metadata(self):
        d = support.new_scratch("wheelmeta")
        try:
            w = d / "tv.whl"
            w.write_bytes(wheel_bytes(tv_metadata("torch==2.13.0")))
            m = inspect_wheel_metadata(w, "torchvision", "0.28.0+cu130")
            self.assertIn("torch==2.13.0", m["requires_dist"])
            self.assertEqual(locks._req_norm("torch (==2.13.0)"), locks._req_norm("torch==2.13.0"))
            w.write_bytes(wheel_bytes(tv_metadata(version="0.28.0")))
            with self.assertRaises(Q0Failure):
                inspect_wheel_metadata(w, "torchvision", "0.28.0+cu130")
            w.write_bytes(wheel_bytes(tv_metadata(), name="nested/x.dist-info/METADATA"))
            with self.assertRaises(Q0Failure):
                inspect_wheel_metadata(w, "torchvision", "0.28.0+cu130")
        finally:
            support.remove_scratch(d)


class ReleaseRecord(unittest.TestCase):
    def setUp(self):
        self.p, self.sha = load_protocol()
        self.root = "C:\\q0root"

    def check(self, rel, stage="execute", code=None, owner="author"):
        return validate_release(rel, stage=stage, owner=owner, protocol=self.p, protocol_sha256=self.sha,
                                lock_sha256="1" * 64, root=self.root, code=code or support.FAKE_CODE)

    def test_binds_review_code_protocol_lock(self):
        good = support.fake_release(self.p, self.sha, "1" * 64, self.root)
        self.check(good)
        self.check(support.fake_release(self.p, self.sha, "1" * 64, self.root, stage="install"), stage="install")
        bad = [
            ("schema", "eldq0-release/1"), ("stage", "install"), ("sequence", "002"), ("harness_commit", "0" * 40),
            ("protocol_sha256", "0" * 64), ("lock_sha256", "0" * 64), ("accepted_review", None),
            ("released_by", "eld-q0-harness"), ("storage_root", "C:\\elsewhere"), ("lease_id", ""),
        ]
        for key, value in bad:
            with self.subTest(key=key):
                with self.assertRaises(Q0Failure) as cm:
                    self.check(good | {key: value})
                self.assertEqual(cm.exception.failure_class, "EXECUTION_NOT_RELEASED")
        with self.assertRaises(Q0Failure):
            self.check(good, code=support.FAKE_CODE | {"harness_clean": False})
        with self.assertRaises(Q0Failure):
            self.check(None)


class InstallStageCli(unittest.TestCase):
    def test_install_commands_refuse_while_hash_missing(self):
        d = support.new_scratch("cli-pending")
        try:
            for args in (["write-requirements", str(d / "req.txt")], ["verify-wheelhouse", str(d)], ["preflight-cpu"]):
                with self.subTest(args=args[0]):
                    cp = subprocess.run([sys.executable, "-I", "-B", str(HARNESS_DIR / "q0.py"), *args],
                                        capture_output=True, text=True, timeout=120)
                    self.assertEqual(cp.returncode, 2, cp.stderr)
                    self.assertEqual(json.loads(cp.stdout)["failures"][0]["failure_class"], "ACQUISITION_PROVENANCE_PENDING")
            self.assertFalse((d / "req.txt").exists())
        finally:
            support.remove_scratch(d)


class CpuPreflight(unittest.TestCase):
    def test_preflight_with_fake_renderer_and_model_dir(self):
        protocol, _ = load_protocol()
        lock = support.final_lock()
        pkgs = support.lock_pkgs(lock)
        d = support.new_scratch("preflight")
        try:
            md = d / "Unlimited_OCR_2_test"
            support.write_fake_model_dir(md)
            support.write_notice_dir(d / "notices")
            (d / "mf.json").write_text(json.dumps(support.manifest_for_dir(md)), encoding="utf-8")
            inst = {a["name"]: a["version"] for a in pkgs.values()}
            kw = dict(protocol=protocol, lock=lock, pkgs=pkgs, installed=inst, importable=lambda m: False,
                      dist_version=lambda n: "5.15.2", model_dir=str(md), notice_dir=d / "notices",
                      manifest_path=d / "mf.json")
            rep = cpu_preflight(pdfium=support.FakePdfium(protocol), **kw)
            self.assertEqual((rep["status"], rep["model_runtime_objects_verified"]), ("pass", 18))
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
