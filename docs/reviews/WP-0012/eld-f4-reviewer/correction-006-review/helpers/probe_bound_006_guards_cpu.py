"""Independent frozen source/CPU checks for correction006; no real product services.

Exercises real Python startup with owned benign CPU children, exact release
guards, output non-reuse, and actual JS workerEnabled assertion over ephemeral
loopback HTTP. No browser/model/renderer import or inference.
"""
from __future__ import annotations
import argparse
import ast
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
import hashlib
import http.server
import json
import os
from pathlib import Path
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import types
from unittest import mock

sys.dont_write_bytecode = True
from probe_bound_006_return_semantics import load_exact, simulate_first_failure, ROOT, PREFIX, OWNED


def startup_probe(mod, mode):
    children, handles = [], []
    original_popen = subprocess.Popen
    with tempfile.TemporaryDirectory(prefix="wp0012-startup-owned-") as scratch:
        temp = Path(scratch)
        def spawn(argv, **kwargs):
            if len(children) == 1 and mode == "ui_spawn_exception":
                raise OSError("synthetic UI spawn failure")
            code = "import time; time.sleep(60)"
            if len(children) == 1 and mode == "ui_early_exit":
                code = "raise SystemExit(1)"
            handles.append(kwargs["stdout"])
            proc = original_popen([sys.executable, "-B", "-c", code], cwd=temp,
                                  stdout=kwargs["stdout"], stderr=subprocess.STDOUT)
            children.append(proc)
            return proc
        def ports(*args):
            return {"5590": [] if mode == "api_timeout" else [{"owningPid": children[0].pid}]}
        ticks = [0]
        def monotonic():
            ticks[0] += 20
            return ticks[0]
        timer = types.SimpleNamespace(monotonic=monotonic, sleep=lambda n: time.sleep(0.01))
        opener = mock.Mock()
        opener.open.side_effect = OSError("no author HTTP access permitted in CPU probe")
        proxy = types.SimpleNamespace(Popen=spawn, run=subprocess.run, STDOUT=subprocess.STDOUT,
                                      TimeoutExpired=subprocess.TimeoutExpired)
        error = None
        try:
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(mod, "assert_ports_unbound", return_value={}))
                stack.enter_context(mock.patch.object(mod, "observe_ports", side_effect=ports))
                stack.enter_context(mock.patch.object(mod, "subprocess", proxy))
                stack.enter_context(mock.patch.object(mod.urllib.request, "build_opener", return_value=opener))
                if mode in ("api_timeout", "ui_timeout"):
                    stack.enter_context(mock.patch.object(mod, "time", timer))
                try:
                    mod.start_api_and_ui(app_conn_str="Password=SYNTHETIC-STARTUP", ocr_enabled=False,
                                         leased_gpu_uuid="", log_dir=temp, tag=mode)
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
            before = [{"pid": p.pid, "alive_after_helper": p.poll() is None} for p in children]
            open_handles = sum(not h.closed for h in handles)
        finally:
            for proc in children:
                if proc.poll() is None:
                    proc.kill()
                proc.wait(timeout=10)
            for handle in handles:
                if not handle.closed:
                    handle.close()
        return {"mode": mode, "error": error, "children": before, "open_handles_after_helper": open_handles,
                "all_owned_children_exited_after_harness": all(p.poll() is not None for p in children)}


def release_probes(mod):
    sample = json.loads((ROOT / PREFIX / "correction-006/sample-synthetic-release.json").read_text(encoding="utf-8"))
    now = datetime(2026, 11, 17, 16, 30, tzinfo=timezone.utc)
    sample["executing_head"] = mod.git_stdout(ROOT, ["rev-parse", "HEAD"])
    def validate(doc, *, require_clean=False, synth=True):
        return mod.validate_release_contract(doc, root=ROOT, release_commit="9" * 40,
            release_path="docs/coordination/WP-0012/synthetic-probe.json", now_utc=now,
            blob_loader=lambda path: mod.SYNTHETIC_SAMPLE_BLOBS[path],
            commit_exists_fn=lambda sha: True, require_clean_worktree=require_clean, allow_synthetic_test_only=synth)
    passed, rejected = {}, {}
    validate(sample)
    for key in ("accepted_preparation_review", "accepted_preparation_review_sha", "accepted_review_007",
                "independent_preparation_review_007_sha", "independent_review_007", "accepted_007",
                "independent_preparation_review_sha", "accepted_review", "independent_preparation_review_002_sha",
                "accepted_review_002", "independent_review_002", "accepted_002", "preparation_review"):
        doc = dict(sample)
        value = doc.pop("accepted_preparation_review")
        doc[key] = value
        validate(doc)
        passed[key] = True
    mutations = {
        "old_changes_requested_002": ("accepted_preparation_review", "379d8c5d607fd248d7f272e412b4ed4a97bc64f6"),
        "wrong_conversation": ("conversation_id", "b7c54417-db09-49bd-8d2b-7cc808f113be"),
        "wrong_model": ("model", "gemini-4-carbon-high"), "wrong_effort": ("effort", "high"),
        "wrong_source": ("source_commit", "0" * 40), "wrong_head": ("executing_head", "1" * 40),
        "wrong_gpu": ("gpu_uuid", "not-owned"), "too_many_attempts": ("max_model_attempts", 3),
        "expired": ("expires_utc", (now - timedelta(seconds=1)).isoformat()),
        "future": ("released_utc", (now + timedelta(seconds=1)).isoformat()),
        "long_window": ("expires_utc", (now + timedelta(hours=7)).isoformat()),
        "path_in_lease": ("lease_id", "WP-0012/escape"), "wrong_ports": ("ports", {}),
        "wrong_runtime": ("runtime_root", str(OWNED)), "wrong_db": ("database", "not-owned"),
        "wrong_pins": ("pinned_digests", {}), "wrong_trees": ("product_tree_objects", {}),
        "missing_observations": ("observation_files", {}), "wrong_storage": ("storage_cap_bytes", 1),
        "wrong_disk_floor": ("free_floor_bytes", 0), "nonaccepting_binding": ("accepted_preparation_review", {"commit": "7"*40, "disposition": "changes-requested"}),
    }
    for name, (key, value) in mutations.items():
        doc = dict(sample)
        doc[key] = value
        try:
            validate(doc)
        except mod.RehearsalGuardError as exc:
            rejected[name] = str(exc)
        else:
            raise AssertionError(f"Release mutation accepted: {name}")
    try:
        validate(sample, synth=False)
    except mod.RehearsalGuardError as exc:
        rejected["synthetic_live"] = str(exc)
    else:
        raise AssertionError("Synthetic release authorized live validation")
    for sha in ("8729db9323e4d2945a30d525b0d67e5ad2a1692e", "6d055395b2a4cf22a7926f1728bc31dbe2f315a3"):
        doc = dict(sample)
        doc.update(synthetic_test_only=False, accepted_preparation_review=sha, lease_id="WP-0012-CPU-NO-EXECUTION")
        try:
            validate(doc, synth=False)
        except mod.RehearsalGuardError as exc:
            if "no accepted independent" not in str(exc):
                raise
            rejected["real_commit_without_007_" + sha[:8]] = str(exc)
        else:
            raise AssertionError("Real commit without /007 was accepted")
    original_git = mod.git_stdout
    def fake_git(root, args):
        if args == ["rev-parse", "--abbrev-ref", "HEAD"]:
            return mod.EXPECTED_BRANCH
        if args == ["status", "--porcelain", "--untracked-files=all"]:
            return " M synthetic-dirty-file"
        return original_git(root, args)
    with mock.patch.object(mod, "git_stdout", side_effect=fake_git):
        try:
            validate(sample, require_clean=True)
        except mod.RehearsalGuardError as exc:
            if "clean before live" not in str(exc):
                raise
            rejected["dirty_worktree"] = str(exc)
        else:
            raise AssertionError("Dirty worktree accepted")
    return {"synthetic_alias_controls": passed, "rejections": rejected,
            "native_identity": {k: sample[k] for k in ("owner", "conversation_id", "model", "effort")}}


def output_probes(mod):
    with tempfile.TemporaryDirectory(prefix="wp0012-output-owned-") as scratch:
        base = Path(scratch)
        existing = base / "old-evidence"
        existing.mkdir()
        sentinel = existing / "failure.txt"
        sentinel.write_bytes(b"preserve-failure-bytes\n")
        for label, directory, explicit in (("existing_directory", existing, None),
                ("existing_output", base / "new1", sentinel),
                ("reviewer_namespace", base / "new2", OWNED / "forbidden-live-output.json")):
            try:
                mod.guard_decisive_output_destinations(directory, explicit)
            except mod.RehearsalGuardError:
                pass
            else:
                raise AssertionError(f"Output guard accepted {label}")
        mod.guard_decisive_output_destinations(base / "new3")
        assert sentinel.read_bytes() == b"preserve-failure-bytes\n"
        return {"existing_directory_rejected": True, "existing_output_rejected": True,
                "reviewer_namespace_rejected": True, "fresh_output_accepted": True, "sentinel_preserved": True}


def http_guards(edge):
    flags = {"wo": False, "mp": False}
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            is_wo = "0001" in self.path
            value = flags["wo" if is_wo else "mp"]
            payload = {"status": "completed", "workerEnabled": value, "attempts": [{"attemptId": "1"}],
                       "result": {"rawSha256": ("a" if is_wo else "b") * 64}}
            if value == "OMIT":
                payload.pop("workerEnabled")
            raw = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        def log_message(self, *args):
            pass
    results = []
    with socketserver.TCPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory(prefix="wp0012-http-owned-") as scratch:
                for index, (wo, mp, expected, should_pass) in enumerate([
                    (False, False, "false", True), (True, True, "true", True),
                    (True, False, "false", False), (False, True, "false", False),
                    ("OMIT", False, "false", False), (False, "false", "false", False)]):
                    flags.update(wo=wo, mp=mp)
                    cp = subprocess.run(["node", str(edge), "--mode", "verify-worker-enabled-guard",
                        "--apiPort", str(server.server_address[1]), "--expectWorkerEnabled", expected,
                        "--output", str(Path(scratch) / f"case-{index}.json")], cwd=ROOT,
                        text=True, capture_output=True, timeout=30)
                    results.append({"wo": wo, "mp": mp, "expected": expected, "expected_success": should_pass,
                                    "exit_code": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr})
                    assert (cp.returncode == 0) == should_pass
        finally:
            server.shutdown()
            thread.join(timeout=5)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-commit", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    assert not subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT).strip()
    output = (ROOT / args.output_dir).resolve()
    assert output.is_relative_to(OWNED) and not output.exists()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    old, old_input = load_exact("ad5202a029a7a86bea5fa3e3d97760d0a9cc673a", PREFIX + "/helpers/run_wp0012_rehearsal.py", "guard_old001")
    new, new_input = load_exact(args.candidate_commit, PREFIX + "/correction-006/helpers/run_wp0012_rehearsal.py", "guard_new006")
    doc = {"source_candidate": args.candidate_commit, "reviewer_frozen_head": head,
           "inputs": [old_input, new_input], "model_gpu_services_executed": False, "results": {}, "passed": False}
    try:
        # Correct ONLY the previous old-control harness's missing temporary log
        # directory. The published eight-case helper and evidence stay unchanged.
        original_write = Path.write_text
        def temporary_log_write(path, *args, **kwargs):
            if path.name == "synthetic-api.log":
                assert "wp0012-independent-return-" in str(path)
                path.parent.mkdir(parents=True, exist_ok=True)
            return original_write(path, *args, **kwargs)
        with mock.patch.object(Path, "write_text", temporary_log_write):
            control = simulate_first_failure(old, 0)
        assert control["calls"]["browser"] == 1 and control["receipt"] is None
        doc["results"]["corrected_old_browser_control"] = control
        startup = []
        for mode in ("ui_early_exit", "api_timeout", "ui_timeout", "ui_spawn_exception"):
            before, after = startup_probe(old, mode), startup_probe(new, mode)
            assert any(p["alive_after_helper"] for p in before["children"])
            assert not any(p["alive_after_helper"] for p in after["children"])
            assert after["open_handles_after_helper"] == 0 and after["error"]
            startup.append({"case": mode, "old": before, "new": after})
        doc["results"]["startup_old_fails_new_passes"] = startup
        doc["results"]["release"] = release_probes(new)
        doc["results"]["output"] = output_probes(new)
        edge = ROOT / PREFIX / "correction-006/helpers/drive_rehearsal_edge.mjs"
        raw = edge.read_bytes()
        expected = subprocess.check_output(["git", "show", f"{args.candidate_commit}:{edge.relative_to(ROOT).as_posix()}"], cwd=ROOT)
        assert raw == expected
        doc["inputs"].append({"path": edge.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(raw).hexdigest()})
        doc["results"]["http_worker_enabled"] = http_guards(edge)
        tree = ast.parse(Path(new.__file__).read_text(encoding="utf-8"))
        imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module]
        imports += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        assert not any(x.split(".")[0] in {"torch", "transformers", "pypdfium2", "PIL", "research", "evaluation"} for x in imports)
        doc["results"]["imports"] = imports
        doc["passed"] = True
    except BaseException as exc:
        doc["exception"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        output.mkdir(parents=True, exist_ok=False)
        doc["utc"] = datetime.now(timezone.utc).isoformat()
        (output / "guards.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"passed": doc["passed"], "groups": list(doc["results"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
