# WP-0005 /008 candidate `24a5866b`: author CPU and isolated-subprocess evidence (`eld-q0-harness`)

This is author verification by fresh **Gemini 4 Carbon (High)** session `bd92ddc3-af60-4096-b683-65386d81b718`, not an independent review. It establishes **CPU and isolated-subprocess harness readiness only**, not model or runtime qualification. Prior `/002` evidence (`fde7fdc1…`, `1b88bfd7…`, `912f4f4f…`, `0331efd7…`) authored by stopped Claude Code session `04e0efba-5292-4cae-b922-1517dee7bbed` is preserved byte-for-byte.

| Item | Value |
| --- | --- |
| Frozen `/008` candidate | `24a5866b505532fd03e7db62a4e57875e4c5a170` (harness tree `48ce82ffc8f78d27aa0338d5ec926ab9b1f683a4`) |
| Continuation / correction base | `2a52ea58fae2badcb4e9ef47d1cb416c006edca4` (prior candidate `84cef5ef30685ffee46281fefc5fd1356dbc1876`) |
| Original WP-0005 base | `df9a2b50894f01987d779d7f9ae805794503ce6f` |
| `protocol.json` SHA-256 (unchanged) | `dd8a7dc38c2a0c46103f6667f522656a2dddf5882727c18bf7b6b5426c5e2309` |
| `locks/dependency-lock.json` SHA-256 (unchanged) | `d8eeaf0fe838d9df5728f17fcbacc8b504d98b79644a524b4faa705d97c49e6e` |
| `manifests/model-files.json` SHA-256 (unchanged) | `085ac7ba1e25a7300846de18bdac19c7f9612bf417041643beff6a9cab6b8ea8` |
| Host Python / Git | `C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe` (`3.12.10`) / `C:\Program Files\Git\cmd\git.exe` (`2.55.0.windows.1`) |

## Decisive Run `24a5866b/`

Executed against clean frozen `HEAD` `24a5866b505532fd03e7db62a4e57875e4c5a170` from `2026-11-15T18:08:01.088703Z` to `2026-11-15T18:08:49.394047Z` via:

```text
C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe -I -B qualification/q0/harness/evidence/008-git-isolation/run_checks.py 24a5866b
```

This directory uses `* -text`, so committed raw bytes match `output_sha256` in [24a5866b/summary.json](24a5866b/summary.json) (`6,711` B, SHA-256 `9770a6a282d000518294c517137c7444b26814cf26c70471d0f025fcd7594a3c`). `C:\Users\jackg\eLedgerCare-Q0` was absent before and after (`false` -> `false`), tracked diff remained empty, `.scratch/never-written.txt` was never created, and no test scratch subdirectories remained.

| Output file | Exit | Bytes | Raw SHA-256 | Result |
| --- | --- | --- | --- | --- |
| `24a5866b/01-unittest.txt` | 0 | 10,274 | `e6d0160d475bf136ee293cf2d937f52899ba7e9456274c831a2273ddea8c33b5` | **80 tests ran: 79 passed, 1 skipped** (`test_links_rejected`, `WinError 1314`) |
| `24a5866b/02-verify-snapshots.txt` | 0 | 7,100 | `ab0d1999b41619f51cb0a3204c96864275663ae6184f128bfa3842804ada3d6b` | 4 upstream snapshots match pinned HF blobs; static save-path facts unchanged |
| `24a5866b/03-derive-rasters-check.txt` | 0 | 911 | `3830bbd14720b6c09320d263ccfe3ac9888040e09865e4d0eca4df3198d94500` | F01 p1 and F07 p1-p3 predicted RGB digests match `protocol.json` |
| `24a5866b/04-model-manifest-check.txt` | 0 | 190 | `b9503dd1b8a99dfa601eea1f999e8cfae513219b042d1ce255d38266546a1c47` | 18 runtime objects + 1 notice identical to pinned HF tree derivation |
| `24a5866b/05-check-protocol.txt` | 0 | 198 | `3698b7f74d5aa896221dc05930aaa6421f0b4b19c36ca600cf1f9d329bd5379e` | Protocol SHA-256 `dd8a7dc3…`; dev fixture digests verified |
| `24a5866b/06-lock-check.txt` | 0 | 3,708 | `e1769d403a348e107d262ed12140eb8b6907233348a9b000a40aad590c51ca93` | 32 artifacts (`31` publisher-declared, `1` `local-sha256-TOFU`), `installable: true`, 850 graph edges, receipt checks all `true` |
| `24a5866b/07-status.txt` | 0 | 703 | `ed4bb346ec5afdb0f8aba79d603dbdf1e9b65555b307db4a5f2640dd5acc0af5` | `code_identity`: `24a5866b505532fd03e7db62a4e57875e4c5a170`, `harness_clean: true`, `storage_root_exists: false` |
| `24a5866b/08-host-precheck-initial.txt` | 0 | 5,530 | `e06e9aeef6101b4422961c67855f03e96b9dd12c75bc7427340c51e0f3591318` | `status: "pass"`; `git_runtime: C:\Program Files\Git\cmd\git.exe`; `C:\` free `68,484,792,320` B; MSVC ×3; `nvidia-smi` ×2 valid |
| `24a5866b/09-execute-refused.txt` | 2 (expected) | 566 | `f6c35002dab1e3f784df0c918653c6a6d1a88af2f7f159e318690e598e727050` | `BLOCKED` (`EXECUTION_NOT_RELEASED`); nothing created |
| `24a5866b/10-write-requirements-refused.txt` | 2 (expected) | 566 | `7237b13dba7996e3ed2969de44da309a02033d31ef0c77b668ec7b6f5d2deeb4` | `BLOCKED` (`EXECUTION_NOT_RELEASED`); `.scratch/never-written.txt` absent |
| `24a5866b/11-verify-wheelhouse-refused.txt` | 2 (expected) | 566 | `7237b13dba7996e3ed2969de44da309a02033d31ef0c77b668ec7b6f5d2deeb4` | `BLOCKED` (`EXECUTION_NOT_RELEASED`) before reading |
| `24a5866b/12-isolated-git-subprocess-check.txt` | 0 | 6,498 | `ce5dc2aacb4c261417e764f27b3100dbf9a8e0b4df7d8e7a2be9db6e823f43f2` | Standalone real-subprocess verifier ([verify_isolated_git.py](verify_isolated_git.py)): `status: "pass"` across all 4 isolated environments, 4 CLI subcommands, released/unreleased `write-requirements`, and nested stage-env `unittest` |
| `24a5866b/coordinator-worker-git-check.txt` | 0 | 605 | `cb4bd7584d6c7914de27276996cd026998111e0a531f8c5e6a09acbe97c925b9` | Read-only run of unchanged coordinator diagnostic `73b5ba98d1e3834cc8c58768ff269730b867ee4c` (`worker-git-check.py`, SHA-256 `a2125bdc…`) on clean `24a5866b`: both `install_stage` and `runtime_child` exit `0` with `git_which: null` and clean `code_identity` |

## What `COORD-Q0-01` Verification Covers

1. **Real OS subprocesses across all generated environments:** Spawns separate Python `3.12.10` child processes (`-I -B` and `-s -P -X utf8`) with `cwd` outside the worktree under `build_stage_env(network=False)`, `build_stage_env(network=True)`, `build_child_env(owner="author")`, and `build_child_env(owner="reviewer")`. Confirms `shutil.which("git") is None` (`PATH` stays strictly `<venv>\Scripts;<SystemRoot>\System32;<SystemRoot>`), `Q0_GIT_EXECUTABLE` pins `C:\Program Files\Git\cmd\git.exe`, `GIT_CONFIG_NOSYSTEM=1` / `GIT_CONFIG_GLOBAL=NUL` / `GIT_TERMINAL_PROMPT=0` are active, credentials/switches are stripped, and both `release.code_identity` and `locks.validate_lock(..., locks.git_blob_reader)` succeed.
2. **Real CLI and supervised runtime child paths:** Exercises `q0.py status`, `q0.py lock-check`, released and unreleased `q0.py write-requirements` inside offline `stage_env`, and a full `supervise(...)` -> child `Session.run()` run (`test_supervised_child_session_runs_real_git_checks`) executing live `code_identity` and `git_blob_reader` inside `build_child_env`.
3. **Fail-closed negative checks:** Stripping `Q0_GIT_EXECUTABLE` in an isolated subprocess causes `code_identity` / `q0.py execute` to fail closed with `Q0Failure("HOST_PRECHECK_FAILED")` (`BLOCKED`, exit `2`) and `git_blob_reader` / `q0.py lock-check` / `q0.py status` to fail closed with `Q0Failure("DEPENDENCY_LOCK_PENDING")` (`BLOCKED`, exit `2`), never an unhandled `FileNotFoundError` traceback. Relative paths, missing binaries, non-`git` executables, mutable-root `git.exe` copies, and untrusted `PATH` prepends are rejected.

## Pre-Freeze Development Failure Disclosure

During local authoring before freezing `24a5866b505532fd03e7db62a4e57875e4c5a170`, one pre-freeze `unittest` run failed two assertions, separated by root cause as required:

- **Source defect fixed before freeze (`q0harness/session.py`, `Heartbeat`):** The new real-subprocess `supervise(...)` + `Session.run()` test exposed a Windows NTFS race in `Heartbeat.beat`: `self.heartbeat.set_phase("finished", None, False)` raised `PermissionError: [WinError 5] Access is denied` at `os.replace(tmp, self.path)` when concurrent with the daemon heartbeat thread or `supervisor.py` polling `heartbeat.json`. Fixed by adding `self._lock = threading.Lock()` and a bounded 5-attempt (`10..50 ms`) retry on transient `PermissionError` in `Heartbeat._beat_locked`, with deterministic unit coverage in `test_heartbeat_serializes_threads_and_retries_transient_replace_lock`.
- **Test-helper expectation fixed before freeze (`tests/test_isolated_git_subprocess.py`):** An initial negative assertion expected `q0.py status` under a Git-stripped environment to report `HOST_PRECHECK_FAILED`, whereas `cmd_status` evaluates `_lock()` (`git_blob_reader`) before `code_identity()` and therefore returns `DEPENDENCY_LOCK_PENDING`. Updated the test to assert `DEPENDENCY_LOCK_PENDING` for `status` / `lock-check` and `HOST_PRECHECK_FAILED` for `execute --owner author`.

## Not Run

- Any wheel, PyTorch, or model-shard download.
- Real 32-wheel `METADATA` inspection on downloaded wheels (synthetic ZIPs + committed CUDA `METADATA` blobs tested).
- Task `venv` creation, package installation, `pip check`, or installed `venv` path-length walk.
- Real `pypdfium2` rendering, `torch` / `transformers` / tokenizer import, model load, `backend_torch.py`, CUDA allocation, or GPU execution.
- Real Windows symlink rejection (`WinError 1314` privilege absent).
