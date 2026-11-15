import copy
import json
import os
import unittest
from pathlib import Path

import support
from q0harness import hostcheck, logscan, modelfiles
from q0harness.environment import GIT_EXECUTABLE_VAR, GIT_ISOLATION_ENV, audit_stage_env, build_stage_env
from q0harness.outcome import Q0Failure
from q0harness.protocol import HARNESS_DIR, load_protocol, validate_protocol


def obs_ok(protocol):
    gpu = (f"2026/11/15 11:00:25.416, {protocol['gpu']['uuid']}, NVIDIA GeForce RTX 5070 Ti, 621.01, 12.0, "
           "16303, 1355, 14643, 5, P8\r\n")

    def observe(cmd):
        out = gpu if any(a.startswith("--query-gpu") for a in cmd) else "4788, C:\\x.exe, [N/A]\r\n"
        return {"argv": cmd, "returncode": 0, "stdout": out, "stderr": "", "observed_utc": "t"}
    return observe


class HostPrecheck(unittest.TestCase):
    def setUp(self):
        self.p, _ = load_protocol()
        self.m = modelfiles.load_manifest(HARNESS_DIR / "manifests/model-files.json")
        self.d = support.new_scratch("host")
        for n in hostcheck.MSVC_DLLS:
            (self.d / n).write_bytes(b"dll")

    def tearDown(self):
        support.remove_scratch(self.d)

    def run_check(self, protocol=None, registry=None, observe=None, stage="initial", git_resolver=None):
        reg = registry or (lambda k, v: {"value": 0, "type": 4} if v == "LongPathsEnabled" else {"value": ["?:\\pagefile.sys"], "type": 7})
        kw = {"git_resolver": git_resolver} if git_resolver is not None else {}
        return hostcheck.host_precheck(protocol or self.p, self.m, stage=stage, system32=self.d, registry=reg,
                                       observe=observe or obs_ok(self.p), **kw)

    def test_pass_and_records_limits(self):
        rec = self.run_check()
        self.assertEqual(rec["status"], "pass", rec["failures"])
        self.assertTrue(rec["git_runtime"]["present"])
        self.assertTrue(Path(rec["git_runtime"]["executable"]).is_file())
        self.assertTrue(all(r["present"] for r in rec["msvc_runtime"]))
        self.assertLess(rec["known_paths"]["max_len"], 240)
        self.assertTrue(any("WDDM" in s for s in rec["limits"]))

    def test_failures(self):
        def no_git():
            raise Q0Failure("HOST_PRECHECK_FAILED", "git absent")
        rec_nogit = self.run_check(git_resolver=no_git)
        self.assertEqual([f["failure_class"] for f in rec_nogit["failures"]], ["HOST_PRECHECK_FAILED"])
        os.remove(self.d / "vcruntime140_1.dll")
        rec = self.run_check()
        self.assertEqual([f["failure_class"] for f in rec["failures"]], ["HOST_PRECHECK_FAILED"])
        (self.d / "vcruntime140_1.dll").write_bytes(b"dll")
        # Initial floor larger than any plausible free space -> STORAGE_FLOOR.
        p = copy.deepcopy(self.p)
        p["storage"]["free_space"]["initial_min_bytes"] = 10 ** 18
        self.assertEqual([f["failure_class"] for f in self.run_check(protocol=p)["failures"]], ["STORAGE_FLOOR"])
        # Long root with long paths disabled -> fail; enabled -> pass.
        p = copy.deepcopy(self.p)
        p["storage"]["root"] = "C:\\" + "x" * 200
        self.assertEqual(self.run_check(protocol=p)["failures"][0]["failure_class"], "HOST_PRECHECK_FAILED")
        enabled = self.run_check(protocol=p, registry=lambda k, v: {"value": 1, "type": 4})
        self.assertNotIn("long paths", json.dumps(enabled["failures"]))
        # Observer failure or a different GPU is a precheck failure.
        bad = lambda cmd: {"argv": cmd, "returncode": 9, "stdout": "", "stderr": "Invalid combination", "observed_utc": "t"}
        self.assertEqual(self.run_check(observe=bad)["status"], "fail")
        other = obs_ok(self.p | {"gpu": self.p["gpu"] | {"uuid": "GPU-00000000-0000-0000-0000-000000000000"}})
        self.assertIn("gpu uuid differs", json.dumps(self.run_check(observe=other)["failures"]))


class ProtocolObserverFreeze(unittest.TestCase):
    def test_observer_and_storage_rules(self):
        p, _ = load_protocol()
        self.assertEqual(len(p["gpu"]["observer"]["commands"]), 2)
        mutations = [
            lambda q: q["gpu"]["observer"]["commands"].__setitem__(0, q["gpu"]["observer"]["commands"][0] + ["--query-compute-apps=pid"]),
            lambda q: q["gpu"]["observer"]["commands"].pop(),
            lambda q: q["gpu"]["observer"]["gpu_fields"].pop(),
            lambda q: q["storage"]["subdirs"].__setitem__("models", "models\\0480966938291445591f69f08a13b041c073a96a"),
            lambda q: q["storage"]["free_space"].__setitem__("during_min_bytes", 0),
            lambda q: q.__setitem__("baseline_label", "native fast path"),
        ]
        for i, m in enumerate(mutations):
            with self.subTest(i=i):
                q = copy.deepcopy(p)
                m(q)
                with self.assertRaises(Q0Failure):
                    validate_protocol(q)


class ModelDirectoryHygiene(unittest.TestCase):
    def setUp(self):
        self.d = support.new_scratch("mdir")

    def tearDown(self):
        support.remove_scratch(self.d)

    def test_normalize_model_dir(self):
        md = self.d / "Unlimited_OCR_2_04809669"
        md.mkdir()
        self.assertEqual(modelfiles.normalize_model_dir(str(md), str(md)), md)
        cases = [(str(md) + "\\", "UNSUPPORTED_PLATFORM"), ("relative\\dir", "UNSUPPORTED_PLATFORM"),
                 (str(self.d / "other"), "STORAGE_NOT_OWNED")]
        for path, cls in cases:
            with self.subTest(path=path):
                with self.assertRaises(Q0Failure) as cm:
                    modelfiles.normalize_model_dir(path, str(md))
                self.assertEqual(cm.exception.failure_class, cls)
        digit = self.d / "0480966938291445591f69f08a13b041c073a96a"
        digit.mkdir()
        with self.assertRaises(Q0Failure) as cm:
            modelfiles.normalize_model_dir(str(digit), str(digit))
        self.assertEqual(cm.exception.failure_class, "UNSUPPORTED_PLATFORM")
        missing = self.d / "Absent_dir"
        with self.assertRaises(Q0Failure) as cm:
            modelfiles.normalize_model_dir(str(missing), str(missing))
        self.assertEqual(cm.exception.failure_class, "HASH_MISMATCH")

    def test_readme_is_a_notice_not_a_runtime_object(self):
        md = self.d / "m"
        support.write_fake_model_dir(md)
        manifest = support.manifest_for_dir(md)
        self.assertEqual(len(manifest["files"]), 18)
        (md / "README.md").write_text("card")
        with self.assertRaises(Q0Failure) as cm:
            modelfiles.verify_model_dir(md, manifest)
        self.assertEqual(cm.exception.failure_class, "UNEXPECTED_ARTIFACT")
        (md / "README.md").unlink()
        support.write_notice_dir(self.d / "n")
        self.assertTrue(modelfiles.verify_notices(self.d / "n", manifest)["notices"][0]["ok"])
        (self.d / "n" / "README.md").write_bytes(b"changed")
        with self.assertRaises(Q0Failure):
            modelfiles.verify_notices(self.d / "n", manifest)

    def test_links_rejected(self):
        md = self.d / "m"
        support.write_fake_model_dir(md)
        manifest = support.manifest_for_dir(md)
        target = self.d / "elsewhere.py"
        target.write_text("x")
        try:
            os.symlink(target, md / ".cache_link.py")
        except (OSError, NotImplementedError) as e:
            self.skipTest(f"symlink creation not permitted on this host: {e}")
        with self.assertRaises(Q0Failure) as cm:
            modelfiles.verify_model_dir(md, manifest)
        self.assertEqual(cm.exception.failure_class, "UNEXPECTED_ARTIFACT")

    def test_committed_manifest_counts(self):
        m = modelfiles.load_manifest(HARNESS_DIR / "manifests/model-files.json")
        self.assertEqual((m["runtime_object_count"], m["total_bytes"]), (18, 6699195181))
        self.assertEqual(sum(1 for f in m["files"] if f["digest_kind"] == "git_blob_sha1"), 16)
        self.assertEqual(sum(1 for f in m["files"] if f["digest_kind"] == "lfs_sha256"), 2)
        self.assertEqual(m["notices"][0]["git_blob_sha1"], "c79e1e3362c8fd2f9193d79c1db80fbf7f041c45")


class StageEnvironmentAndLogs(unittest.TestCase):
    def test_stage_env(self):
        p, _ = load_protocol()
        root = Path(r"C:\q0-root-never-created")
        parent = {"SystemRoot": r"C:\Windows", "HF_TOKEN": "s", "PIP_INDEX_URL": "https://evil", "PATH": r"C:\evil"}
        on = build_stage_env(parent, root=root, protocol=p, network=True)
        off = build_stage_env(parent, root=root, protocol=p, network=False)
        for env in (on, off):
            self.assertNotIn("HF_TOKEN", env)
            self.assertNotIn("PIP_INDEX_URL", env)
            self.assertNotIn(r"C:\evil", env["PATH"])
            self.assertTrue(Path(env[GIT_EXECUTABLE_VAR]).is_file())
            for k, want in GIT_ISOLATION_ENV.items():
                self.assertEqual(env[k], want)
            self.assertTrue(env["PIP_CACHE_DIR"].startswith(str(root)))
            self.assertTrue(env["TEMP"].startswith(str(root)))
            self.assertEqual((env["PIP_CONFIG_FILE"], env["HF_HUB_DISABLE_XET"]), ("NUL", "1"))
        self.assertNotIn("PIP_NO_INDEX", on)
        self.assertEqual((off["PIP_NO_INDEX"], off["HF_HUB_OFFLINE"]), ("1", "1"))
        for bad in ({GIT_EXECUTABLE_VAR: ""}, {"GIT_CONFIG_GLOBAL": "user"}, {"HF_TOKEN": "s"}, {"PIP_NO_INDEX": "0"}):
            with self.subTest(bad=bad):
                with self.assertRaises(Q0Failure):
                    audit_stage_env(off | bad, root=root, network=False)

    def test_logscan(self):
        data = (b"[CodeStamp] warmup-window-page-switches-v4 sha256=x\n"
                b"[DASH] differentiable DASH attention active (entmax router)\n")
        r = logscan.scan(data)
        counts = {m["marker"]: m["count"] for m in r["markers"]}
        self.assertEqual(counts["[CodeStamp]"], 1)
        self.assertEqual(counts["[DASH] Triton block-sparse path active"], 0)
        self.assertIn("not evidence", r["note"])


if __name__ == "__main__":
    unittest.main()
