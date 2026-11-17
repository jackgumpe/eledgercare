"""Preserve original controls; add exact Windows app-alias image controls."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import traceback
from unittest.mock import patch

import check_ownership_v6_cpu as original
import ownership_v6 as guard
import run_wp0012_reviewer_rehearsal_v6 as runner


def controls():
    # Original fake Popen predates the new handle-image call. Supply only that
    # missing fake observation; all original scenarios/assertions are unchanged.
    with patch.object(guard, "popen_image", return_value=original.PWSH):
        results = original.controls()
    alias = r"C:\synthetic\WindowsApps\PowerShellAlias\pwsh.EXE"

    class FakeProcess:
        pid = 37576
        returncode = 0
        def communicate(self, timeout):
            snapshot, _ = original.fixture()
            return json.dumps({"observer_pid": self.pid, "processes": snapshot["candidate_and_gpu_processes"]}).encode(), b""
        def poll(self):
            return 0

    def fake_run(argv, **kwargs):
        if argv[0] == "nvidia-smi":
            out = "" if "--query-compute-apps=pid,process_name,used_memory" in argv else original.fixture()[0]["gpu"][0]
        else:
            assert argv == [original.OLLAMA, "ps"]
            out = original.HEADER
        return subprocess.CompletedProcess(argv, 0, out, "")

    for label, image, reject in (("windows_app_alias_retained_image_matches_cim", original.PWSH, False),
                                  ("retained_image_cim_mismatch", r"C:\different\pwsh.exe", True)):
        with patch.object(guard.shutil, "which", side_effect=lambda name: alias if name == "pwsh" else original.OLLAMA), patch.object(guard.subprocess, "Popen", return_value=FakeProcess()), patch.object(guard, "popen_creation_utc", return_value="2026-11-12T16:09:34.549904Z"), patch.object(guard, "popen_image", return_value=image):
            try:
                snapshot = guard.collect(original.ROOT, runner.EXPECTED_GPU_UUID, fake_run)
                assert snapshot["observer"]["issued_executable"] == alias
                assert snapshot["observer"]["retained_process_image"] == image
                original.evaluate(snapshot, original.fixture()[1])
                results.append(dict(name=label, passed=not reject, actual="passed", issued_alias=alias, retained_image=image))
            except guard.ObservationError as exc:
                results.append(dict(name=label, passed=reject, actual="refused", message=str(exc)))
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("cpu", "read-only"), required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    record = dict(mode=args.mode, started_utc=datetime.now(timezone.utc).isoformat(), source_commit=args.source_commit,
                  executing_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=original.ROOT, text=True).strip(),
                  source_files={str(p.relative_to(original.ROOT)).replace("\\", "/"): original.sha(p.read_bytes()) for p in (Path(__file__), Path(original.__file__), Path(guard.__file__), Path(runner.__file__))},
                  no_model_or_service_started=True)
    exitcode = 0
    try:
        if args.mode == "cpu":
            record["cases"] = controls()
            record["passed"] = sum(c["passed"] for c in record["cases"])
            record["total"] = len(record["cases"])
            exitcode = 0 if record["passed"] == record["total"] else 1
        else:
            record.update(original.actual_probe())
    except BaseException as exc:
        record["error"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        exitcode = 1
    record.update(exit_code=exitcode, finished_utc=datetime.now(timezone.utc).isoformat())
    (args.output_dir / "result.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: record[k] for k in ("mode", "source_commit", "executing_head", "exit_code", "started_utc", "finished_utc")}))
    print(f"Result: {args.output_dir / 'result.json'}")
    return exitcode


if __name__ == "__main__":
    raise SystemExit(main())
