import os
import unittest
from pathlib import Path

import support
from q0harness import procmem
from q0harness.environment import (audit_child_env, build_child_env, check_run_dir, check_storage_root,
                                   default_forbidden_parents, layout)
from q0harness.outcome import Q0Failure
from q0harness.protocol import REPO_ROOT, load_protocol
from q0harness.writer import BoundedJsonl, BoundedWriter, CapExceeded


class ChildEnvironment(unittest.TestCase):
    def setUp(self):
        self.root = Path(r"C:\q0-test-root-never-created")
        self.run = layout(self.root, "author")["run_owner"] / "r1"
        self.gpu = load_protocol()[0]["gpu"]["uuid"]

    def test_allowlist_drops_secrets_and_model_switches(self):
        parent = {"SystemRoot": r"C:\Windows", "PATH": r"C:\evil", "HF_TOKEN": "s", "HUGGING_FACE_HUB_TOKEN": "s",
                  "ANTHROPIC_API_KEY": "s", "OPENAI_API_KEY": "s", "GITHUB_TOKEN": "s", "DASH_STAGE0": "indexer",
                  "TIME_DIAG": "1", "PAGE_SCOPE_PREFILL": "1", "WARMUP_MAIN_LOCAL_WINDOW": "0", "PYTHONPATH": "x",
                  "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True", "SGLANG_UOCR_MAX_PAGE_TOKENS": "1",
                  "HF_HOME": r"C:\shared\hf", "TEMP": r"C:\Users\x\AppData\Local\Temp", "MY_PASSWORD": "s"}
        env = build_child_env(parent, root=self.root, owner="author", run_dir=self.run, gpu_uuid=self.gpu)
        for k in parent:
            if k not in ("SystemRoot", "PATH", "HF_HOME", "TEMP"):
                self.assertNotIn(k, env)
        self.assertNotIn(r"C:\evil", env["PATH"])
        self.assertTrue(env["HF_HOME"].startswith(str(self.root)))
        self.assertTrue(env["TEMP"].startswith(str(self.run)))
        self.assertTrue(env["HF_MODULES_CACHE"].startswith(str(self.run)))
        self.assertEqual((env["HF_HUB_OFFLINE"], env["TRANSFORMERS_OFFLINE"]), ("1", "1"))
        self.assertEqual(env["CUDA_VISIBLE_DEVICES"], self.gpu)
        for bad in ({"DASH_DEBUG_ANOMALY": "1"}, {"HF_TOKEN": "x"}, {"TIME_DIAG": "1"}, {"HF_HUB_OFFLINE": "0"},
                    {"TEMP": r"C:\Windows\Temp"}):
            with self.subTest(bad=bad):
                with self.assertRaises(Q0Failure):
                    audit_child_env(env | bad, root=self.root, owner="author", run_dir=self.run)

    def test_storage_root_and_run_dir_ownership(self):
        check_storage_root(self.root, expected_root=str(self.root), forbidden_parents=[str(REPO_ROOT)])
        for root, forb in [(Path(r"C:\other"), []), (REPO_ROOT / "q0", [str(REPO_ROOT)])]:
            with self.assertRaises(Q0Failure) as cm:
                check_storage_root(root, expected_root=str(root if forb else self.root), forbidden_parents=forb)
            self.assertEqual(cm.exception.failure_class, "STORAGE_NOT_OWNED")
        forb = default_forbidden_parents(REPO_ROOT, {"TEMP": r"C:\T", "USERPROFILE": r"C:\Users\u"})
        self.assertIn(str(REPO_ROOT), forb)
        self.assertIn(r"C:\T", forb)
        for bad in (layout(self.root, "author")["run_owner"], layout(self.root, "reviewer")["run_owner"] / "r1",
                    self.root / "elsewhere"):
            with self.assertRaises(Q0Failure):
                check_run_dir(bad, self.root, "author")
        with self.assertRaises(Q0Failure):
            layout(self.root, "someone")


class Writer(unittest.TestCase):
    def setUp(self):
        self.d = support.new_scratch("writer")

    def tearDown(self):
        support.remove_scratch(self.d)

    def test_exclusive_bounded_and_honest(self):
        w = BoundedWriter(self.d, total_cap_bytes=100)
        r = w.write_bytes("a.txt", b"0123456789", cap_bytes=4)
        self.assertEqual((r["bytes_written"], r["full_bytes"], r["truncated_by_writer"]), (4, 10, True))
        self.assertEqual((self.d / "a.txt").read_bytes(), b"0123")
        self.assertNotEqual(r["sha256_written"], r["full_sha256"])
        with self.assertRaises(FileExistsError):
            w.write_bytes("a.txt", b"x", cap_bytes=10)
        for bad in ("../x", "a/b", "", "x.partial", "con:"):
            with self.assertRaises(ValueError):
                w.write_bytes(bad, b"x", cap_bytes=1)
        with self.assertRaises(CapExceeded):
            w.write_bytes("big", b"x" * 97, cap_bytes=1000)
        with self.assertRaises(CapExceeded):
            w.write_json("j.json", {"k": "v" * 50}, cap_bytes=10)
        t = w.write_text("t.txt", "<PAGE>\u00e9\ud800", cap_bytes=50)
        self.assertFalse(t["utf8_lossless"])
        self.assertEqual(len(w.index), 2)

    def test_jsonl_cap(self):
        log = BoundedJsonl(self.d / "e.jsonl", cap_bytes=120)
        results = [log.append({"i": i, "pad": "x" * 20}) for i in range(10)]
        info = log.close()
        self.assertIn(False, results)
        self.assertLessEqual(info["bytes"], 120)
        self.assertGreater(info["dropped_events"], 0)
        self.assertIn(b"log_cap_reached", (self.d / "e.jsonl").read_bytes())


@unittest.skipUnless(procmem.supported(), "Windows-only counters")
class ProcessMemory(unittest.TestCase):
    def test_snapshot_and_window_peak(self):
        s = procmem.snapshot()
        self.assertGreater(s["working_set"], 0)
        with procmem.PeakSampler(0.01) as ps:
            blob = bytearray(64 << 20)
            blob[::4096] = b"\x01" * len(blob[::4096])
            import time
            time.sleep(0.1)
            del blob
        r = ps.result()
        self.assertGreater(r["samples"], 1)
        self.assertGreaterEqual(r["window_peak_working_set_lower_bound"], s["working_set"] + (48 << 20))
        self.assertEqual(r["provenance"], "direct_sampled")


if __name__ == "__main__":
    unittest.main()
