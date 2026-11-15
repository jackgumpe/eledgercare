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
from q0harness.environment import run_git
from q0harness.locks import (inspect_wheel_metadata, readiness, require_installable, requirements_text,
                             validate_lock, verify_installed, verify_wheel_metadata, verify_wheelhouse)
from q0harness.outcome import Q0Failure
from q0harness.preflight import cpu_preflight
from q0harness.protocol import HARNESS_DIR, load_protocol
from q0harness.release import validate_release

CUDA_META = "d666c4163b8b6bdf5f6c69b455c30f3c377cbdc5:qualification/q0/preflight/response/cuda-metadata.json"


def wheel_bytes(meta: bytes, dist: str = "x-1.0", extra_members=()) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("pkg/__init__.py", "")
        z.writestr(f"{dist}.dist-info/METADATA", meta)
        for m in extra_members:
            z.writestr(m, meta)
    return buf.getvalue()


def synth_metadata(art: dict, *, raw_style: bool = False, drop: int | None = None, add: str | None = None) -> bytes:
    """Wheel METADATA built from the frozen graph; raw_style rewrites entries into the
    parenthesized/single-quoted form wheels often use, to exercise normalization."""
    reqs = list(art["graph_requires"])
    if drop is not None:
        reqs.pop(drop)
    if add:
        reqs.append(add)
    lines = [f"Metadata-Version: 2.1", f"Name: {art['name']}", f"Version: {art['version']}"]
    for r in reqs:
        if raw_style:
            spec, sep, mk = r.partition(";")
            m = locks._REQ.match(spec.replace(" ", ""))
            name, extras, specs = m.group(1), m.group(2) or "", m.group(3)
            spec = f"{name}{extras} ({specs})" if specs else f"{name}{extras}"
            r = spec + (" ; " + mk.strip().replace('"', "'") if sep else "")
        lines.append(f"Requires-Dist: {r}")
    return ("\n".join(lines) + "\n\nlong description\nRequires-Dist: not-a-header\n").encode()


def cuda_records() -> dict:
    data = run_git(("cat-file", "blob", CUDA_META), cwd=support.REPO_ROOT).stdout
    return {r["name"]: r for r in json.loads(data)}


class BoundLock(unittest.TestCase):
    def test_committed_lock_is_complete_and_bound(self):
        lock = support.committed_lock()
        self.assertEqual(lock["source"]["commit"], "d666c4163b8b6bdf5f6c69b455c30f3c377cbdc5")
        pkgs = validate_lock(lock, support.git_reader())
        r = readiness(pkgs)
        self.assertEqual(len(pkgs), 32)
        self.assertEqual(r["counts"], {"publisher-declared": 31, "local-sha256-TOFU": 1, "missing": 0})
        self.assertTrue(r["installable"])
        self.assertEqual(r["required_exceptions"], ["torchvision-local-sha256-TOFU"])
        tv = pkgs["torchvision"]
        self.assertEqual((tv["effective_kind"], tv["effective_sha256"]), ("local-sha256-TOFU", support.TV_LOCAL_SHA))
        self.assertTrue(all(tv["receipt_checks"].values()))
        self.assertEqual(tv["local_record"]["receipt"]["commit"], "ef72849519c83a71e59e80c311b48719252d0cd6")
        self.assertEqual(pkgs["torch"]["effective_sha256"],
                         "2efab1e83604ca628c6d85b9e188c153690980498d1297081a9dad704919303c")
        self.assertEqual(set(n for n, a in pkgs.items() if a.get("published_metadata_sha256")), {"torch", "torchvision"})
        self.assertEqual(sum(len(a["graph_requires"]) for a in pkgs.values()), 850)
        text = (HARNESS_DIR / "locks/dependency-lock.json").read_text(encoding="utf-8")
        for unwanted in ("set-cookie", "__cf_bm", "CF-RAY", "Server-Timing"):
            self.assertNotIn(unwanted, text)

    def test_install_requires_release_exception(self):
        pkgs = validate_lock(support.committed_lock(), support.git_reader())
        for release in (None, {"accepted_provenance_exceptions": []}):
            with self.assertRaises(Q0Failure) as cm:
                require_installable(pkgs, release)
            self.assertEqual(cm.exception.failure_class, "ACQUISITION_PROVENANCE_PENDING")
        require_installable(pkgs, {"accepted_provenance_exceptions": ["torchvision-local-sha256-TOFU"]})

    def test_gap_state_blocks(self):
        pkgs = validate_lock(support.without_local_records(support.committed_lock()), support.git_reader())
        self.assertEqual(readiness(pkgs)["missing_wheel_sha256"], ["torchvision"])
        with self.assertRaises(Q0Failure) as cm:
            require_installable(pkgs, {"accepted_provenance_exceptions": ["torchvision-local-sha256-TOFU"]})
        self.assertEqual(cm.exception.failure_class, "ACQUISITION_PROVENANCE_PENDING")
        with self.assertRaises(Q0Failure):
            requirements_text(pkgs)

    def test_lock_is_not_circular(self):
        text = (HARNESS_DIR / "locks/dependency-lock.json").read_text(encoding="utf-8")
        self.assertNotIn("review_003", text)
        self.assertNotIn("accepted_review", text)
        for bad in ({"accepted_review": {"report_commit": "a" * 40}}, {"lineage": {"review_003": {"report": "a" * 40}}}):
            with self.assertRaises(Q0Failure):
                validate_lock(support.committed_lock() | bad, support.git_reader())

    def test_source_binding_fails_closed(self):
        good = support.committed_lock()
        real = support.git_reader()
        meta_blob = good["source"]["git_blob"]

        def altering(oid):
            data = real(oid)
            return data.replace(b'"size": 9091113', b'"size": 9091114', 1) if oid == meta_blob else data
        with self.assertRaises(Q0Failure) as cm:
            validate_lock(good, altering)
        self.assertEqual(cm.exception.failure_class, "DEPENDENCY_LOCK_PENDING")
        mutations = [
            lambda l: l["platform"]["marker_environment"].__setitem__("platform_machine", "amd64"),
            lambda l: l["platform"].__setitem__("python", "3.12.9"),
            lambda l: l["expect"].__setitem__("artifact_count", 31),
            lambda l: l["expect"].__setitem__("missing_publisher_hash", []),
            lambda l: l.__setitem__("triton_policy", "present"),
            lambda l: l["cuda"].__setitem__("device_capability", [8, 9]),
            lambda l: l["source"].__setitem__("status", "final"),
            lambda l: l["metadata_digest_source"].__setitem__("git_blob", "0" * 40),
            lambda l: l["metadata_digest_source"].__setitem__("names", ["torch"]),
        ]
        for i, m in enumerate(mutations):
            with self.subTest(i=i):
                lock = copy.deepcopy(good)
                m(lock)
                with self.assertRaises(Q0Failure):
                    validate_lock(lock, real)

    def test_local_record_and_receipt_rules(self):
        bad_records = [
            lambda rec: rec.__setitem__("hash_kind", "publisher-declared"),
            lambda rec: rec.__setitem__("provenance_label", "publisher-verified"),
            lambda rec: rec.__setitem__("size", 9091112),
            lambda rec: rec.__setitem__("metadata_sha256", "0" * 64),
            lambda rec: rec.__setitem__("sha256", "0" * 64),           # receipt says 5ae0ff50...
            lambda rec: rec.__setitem__("sha256", "xyz"),
            lambda rec: rec["receipt"].__setitem__("commit", None),
            lambda rec: rec["receipt"].__setitem__("git_blob", "0" * 40),  # object absent
            lambda rec: rec["receipt"].__setitem__("size", 3104),
            lambda rec: rec.__setitem__("name", "torch"),
        ]
        for i, m in enumerate(bad_records):
            with self.subTest(i=i):
                lock = support.committed_lock()
                m(lock["local_hash_records"][0])
                with self.assertRaises(Q0Failure):
                    support.lock_pkgs(lock)
        # A receipt whose content does not support the record (pass=false) is refused.
        real = support.git_reader()
        rb = support.committed_lock()["local_hash_records"][0]["receipt"]["git_blob"]
        data = real(rb).replace(b'"pass": true', b'"pass": false')
        forged = support.committed_lock()
        forged["local_hash_records"][0]["receipt"].update(git_blob=locks.git_blob_sha1_bytes(data), size=len(data))
        reader = lambda oid: data if oid == locks.git_blob_sha1_bytes(data) else real(oid)
        with self.assertRaises(Q0Failure) as cm:
            validate_lock(forged, reader)
        self.assertIn("does not support", str(cm.exception))

    def test_requirements_text(self):
        lines = requirements_text(support.lock_pkgs(support.final_lock())).splitlines()
        self.assertEqual(len(lines), 32)
        self.assertIn(f"torchvision==0.28.0+cu130 --hash=sha256:{support.TV_LOCAL_SHA}", lines)
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


class EveryWheelMetadata(unittest.TestCase):
    """N-02: each acquired wheel's own METADATA against the frozen graph, before install."""

    def setUp(self):
        self.d = support.new_scratch("wheelmeta")
        self.pkgs = support.lock_pkgs(support.final_lock())

    def tearDown(self):
        support.remove_scratch(self.d)

    def put(self, name, data):
        p = self.d / name
        p.write_bytes(data)
        return p

    def test_real_recorded_cuda_metadata_bodies_pass(self):
        recs = cuda_records()
        for n in ("torch", "torchvision"):
            with self.subTest(n=n):
                body = recs[n]["metadata_text"].encode("utf-8")
                w = self.put(f"{n}.whl", wheel_bytes(body, dist=f"{n}-{self.pkgs[n]['version']}"))
                row = verify_wheel_metadata(w, self.pkgs[n])
                self.assertTrue(row["requires_match"] and row["published_metadata_sha256_match"])
                self.assertEqual(row["requires_dist"], len(self.pkgs[n]["graph_requires"]))

    def test_every_pypi_artifact_in_both_forms(self):
        for n, a in sorted(self.pkgs.items()):
            if a.get("published_metadata_sha256"):
                continue
            for raw in (False, True):
                with self.subTest(n=n, raw=raw):
                    w = self.put(f"{n}-{raw}.whl", wheel_bytes(synth_metadata(a, raw_style=raw)))
                    self.assertTrue(verify_wheel_metadata(w, a)["ok"])

    def test_divergent_metadata_fails(self):
        tr = self.pkgs["transformers"]
        cases = {
            "dropped requirement": synth_metadata(tr, drop=0),
            "added requirement": synth_metadata(tr, add="evil-dependency>=1"),
            "changed specifier": synth_metadata(tr).replace(b"Requires-Dist: huggingface-hub<1.0,>=0.30.0",
                                                            b"Requires-Dist: huggingface-hub<2.0,>=0.30.0"),
            "wrong version": synth_metadata(tr).replace(b"Version: 4.52.1", b"Version: 4.52.2"),
        }
        for label, meta in cases.items():
            with self.subTest(label):
                w = self.put(label.replace(" ", "_") + ".whl", wheel_bytes(meta))
                with self.assertRaises(Q0Failure):
                    verify_wheel_metadata(w, tr)
        recs = cuda_records()
        body = recs["torch"]["metadata_text"].encode("utf-8") + b"\n"  # same fields, different bytes
        w = self.put("torch_altered.whl", wheel_bytes(body))
        with self.assertRaises(Q0Failure) as cm:
            verify_wheel_metadata(w, self.pkgs["torch"])
        self.assertIn("published_metadata_sha256_match", json.dumps(cm.exception.evidence))
        w = self.put("two.whl", wheel_bytes(synth_metadata(tr), extra_members=("y-1.dist-info/METADATA",)))
        with self.assertRaises(Q0Failure):
            verify_wheel_metadata(w, tr)

    def test_wheelhouse_checks_payload_then_every_metadata(self):
        recs = cuda_records()
        wh = self.d / "wh"
        wh.mkdir()
        for n, a in self.pkgs.items():
            meta = recs[n]["metadata_text"].encode("utf-8") if n in recs else synth_metadata(a)
            data = wheel_bytes(meta)
            (wh / a["filename"]).write_bytes(data)
            # Test-only: point the in-memory lock entry at the synthetic payload.
            a["size"], a["effective_sha256"] = len(data), hashlib.sha256(data).hexdigest()
        rep = verify_wheelhouse(self.pkgs, wh, support.final_lock())
        self.assertEqual(rep["metadata_checked"], 32)
        self.assertTrue(all(r["payload_ok"] and r["metadata"]["ok"] for r in rep["wheels"]))
        # Payload hash still matches, but METADATA diverges from the graph -> refused.
        a = self.pkgs["requests"]
        data = wheel_bytes(synth_metadata(a, add="extra-dep"))
        (wh / a["filename"]).write_bytes(data)
        a["size"], a["effective_sha256"] = len(data), hashlib.sha256(data).hexdigest()
        with self.assertRaises(Q0Failure):
            verify_wheelhouse(self.pkgs, wh, support.final_lock())
        (wh / "unlocked-1.0-py3-none-any.whl").write_bytes(b"x")
        with self.assertRaises(Q0Failure):
            verify_wheelhouse(self.pkgs, wh, support.final_lock())
        (wh / "unlocked-1.0-py3-none-any.whl").unlink()
        (wh / self.pkgs["numpy"]["filename"]).write_bytes(b"tampered")
        with self.assertRaises(Q0Failure):
            verify_wheelhouse(self.pkgs, wh, support.final_lock())

    def test_inspect_wheel_metadata_ignores_body(self):
        w = self.put("tv.whl", wheel_bytes(synth_metadata(self.pkgs["idna"])))
        m = inspect_wheel_metadata(w, "idna", "3.11")
        self.assertNotIn("not-a-header", m["requires_dist"])
        with self.assertRaises(Q0Failure):
            inspect_wheel_metadata(w, "idna", "3.10")

    def test_normalizer(self):
        n = locks._req_norm
        self.assertEqual(n("torch (==2.13.0)"), n("torch==2.13.0"))
        self.assertEqual(n("pillow (!=8.3.*,>=5.3.0)"), n("pillow>=5.3.0,!=8.3.*"))
        self.assertEqual(n("gdown (>=4.7.3) ; extra == 'gdown'"), n('gdown>=4.7.3; extra == "gdown"'))
        self.assertEqual(n("Typing_Extensions>=4"), n("typing-extensions>=4"))
        self.assertNotEqual(n("torch==2.13.0"), n("torch==2.13.1"))
        self.assertNotEqual(n('x; extra == "a"'), n('x; extra == "b"'))
        self.assertNotEqual(n("x[a]"), n("x"))


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
    def test_install_commands_refuse_without_release(self):
        d = support.new_scratch("cli-norelease")
        try:
            for args in (["write-requirements", str(d / "req.txt")], ["verify-wheelhouse", str(d)], ["preflight-cpu"]):
                with self.subTest(args=args[0]):
                    cp = subprocess.run([sys.executable, "-I", "-B", str(HARNESS_DIR / "q0.py"), *args],
                                        capture_output=True, text=True, timeout=120)
                    self.assertEqual(cp.returncode, 2, cp.stderr)
                    self.assertEqual(json.loads(cp.stdout)["failures"][0]["failure_class"], "EXECUTION_NOT_RELEASED")
            self.assertFalse((d / "req.txt").exists())
            # A release whose code/protocol/lock identities do not bind this worktree is refused too.
            rel = d / "install.json"
            p, sha = load_protocol()
            rel.write_text(json.dumps(support.fake_release(p, sha, "1" * 64, p["storage"]["root"], stage="install")))
            cp = subprocess.run([sys.executable, "-I", "-B", str(HARNESS_DIR / "q0.py"), "write-requirements",
                                 str(d / "req.txt"), "--release", str(rel)], capture_output=True, text=True, timeout=120)
            self.assertEqual(cp.returncode, 2, cp.stderr)
            self.assertEqual(json.loads(cp.stdout)["failures"][0]["failure_class"], "EXECUTION_NOT_RELEASED")
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
