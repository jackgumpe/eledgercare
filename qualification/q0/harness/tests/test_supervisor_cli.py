import json
import subprocess
import sys
import textwrap
import time
import unittest
from pathlib import Path

import support
from q0harness.protocol import HARNESS_DIR, load_protocol
from q0harness.supervisor import supervise

CHILD = textwrap.dedent("""
    import json, os, sys, time
    run_dir, mode = sys.argv[1], sys.argv[2]
    hb = os.path.join(run_dir, "heartbeat.json")
    def beat(phase, progress, timeout=None, stall=False):
        with open(hb + ".tmp", "w") as f:
            json.dump({"phase": phase, "progress": progress, "phase_timeout_s": timeout, "stall_monitored": stall}, f)
        os.replace(hb + ".tmp", hb)
    if mode == "ok":
        for i in range(3):
            beat("call:F01", i, 30, True); time.sleep(0.2)
        os.makedirs(os.path.join(run_dir, "evidence"), exist_ok=True)
        with open(os.path.join(run_dir, "evidence", "outcome.json"), "w") as f:
            json.dump({"status": "QUALIFIED_RUNTIME_OBSERVATION"}, f)
    elif mode == "stall":
        while True:
            beat("call:F07", 5, 600, True); time.sleep(0.2)
    elif mode == "phase_timeout":
        beat("load", 0, 1, False); time.sleep(600)
    elif mode == "flood":
        beat("call:F01", 0, 600, False)
        while True:
            sys.stdout.write("x" * 65536); sys.stdout.flush()
    elif mode == "crash":
        sys.exit(7)
""")


def pid_alive(pid: int) -> bool:
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
    return str(pid) in out


class Supervisor(unittest.TestCase):
    def setUp(self):
        self.d = support.new_scratch("supervisor")
        self.script = self.d / "child.py"
        self.script.write_text(CHILD, encoding="utf-8")

    def tearDown(self):
        support.remove_scratch(self.d)

    def sup(self, mode, **kw):
        run = self.d / mode
        run.mkdir()
        env = {"SystemRoot": r"C:\Windows", "PATH": r"C:\Windows\System32"}
        args = dict(session_timeout_s=60, stall_s=2, max_log_bytes=1 << 20, default_phase_timeout_s=30, poll_s=0.2)
        args.update(kw)
        t0 = time.monotonic()
        rec = supervise([sys.executable, "-I", str(self.script), str(run), mode], env=env, cwd=run, run_dir=run,
                        heartbeat_path=run / "heartbeat.json", **args)
        rec["_wall"] = time.monotonic() - t0
        self.assertIsNotNone(rec["child_returncode"])
        self.assertFalse(pid_alive(rec["child_pid"]), "supervisor must leave no running child")
        self.assertTrue((run / "supervisor.json").is_file())
        self.assertIsNone(rec["accuracy_score"])
        return rec

    def test_completed(self):
        rec = self.sup("ok", observer_cmd=[sys.executable, "-I", "-c", "print('observer')"], observer_every_s=1)
        self.assertEqual(rec["verdict"], "CHILD_COMPLETED")
        self.assertEqual(rec["child_outcome_status"], "QUALIFIED_RUNTIME_OBSERVATION")
        self.assertEqual([o["tag"] for o in rec["observers"]][0], "pre")
        self.assertEqual(rec["observers"][-1]["tag"], "post")

    def test_stall_kills_own_child(self):
        rec = self.sup("stall")
        self.assertEqual(rec["verdict"], "SEVERE_STALL")
        self.assertLess(rec["_wall"], 30)

    def test_phase_timeout(self):
        rec = self.sup("phase_timeout")
        self.assertEqual(rec["verdict"], "TIMEOUT")
        self.assertIn("phase load", rec["failure"]["detail"])

    def test_session_timeout(self):
        rec = self.sup("stall", stall_s=600, session_timeout_s=2)
        self.assertEqual(rec["verdict"], "TIMEOUT")

    def test_log_cap(self):
        rec = self.sup("flood", max_log_bytes=256 * 1024)
        self.assertEqual(rec["verdict"], "LOG_CAP_EXCEEDED")

    def test_crash_without_outcome(self):
        rec = self.sup("crash")
        self.assertEqual((rec["verdict"], rec["child_returncode"]), ("CHILD_EXIT_NONZERO", 7))


class CliRefusesWithoutRelease(unittest.TestCase):
    def test_execute_is_blocked_and_creates_nothing(self):
        protocol, _ = load_protocol()
        root = Path(protocol["storage"]["root"])
        existed = root.exists()
        cp = subprocess.run([sys.executable, "-I", "-B", str(HARNESS_DIR / "q0.py"), "execute", "--owner", "author"],
                            capture_output=True, text=True, timeout=120)
        self.assertEqual(cp.returncode, 2, cp.stderr)
        rec = json.loads(cp.stdout)
        self.assertEqual(rec["status"], "BLOCKED")
        self.assertEqual(rec["failures"][0]["failure_class"], "DEPENDENCY_LOCK_PENDING")
        self.assertIsNone(rec["accuracy_score"])
        self.assertEqual(root.exists(), existed, "execute must not create the external storage root")

    def test_cpu_commands_succeed(self):
        for args in (["check-protocol"], ["derive-rasters", "--check"], ["build-model-manifest", "--check"],
                     ["verify-snapshots"], ["status"]):
            with self.subTest(args=args):
                cp = subprocess.run([sys.executable, "-I", "-B", str(HARNESS_DIR / "q0.py"), *args],
                                    capture_output=True, text=True, timeout=300)
                self.assertEqual(cp.returncode, 0, cp.stderr)
                json.loads(cp.stdout)


if __name__ == "__main__":
    unittest.main()
