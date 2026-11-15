# WP-0005 /009 Phase B Evidence: Independent Verification of `/008` Candidate `24a5866b505532fd03e7db62a4e57875e4c5a170` (`eld-q0-reviewer`)

## Attribution, Lineage, and Bounded Scope

- **Stable review role:** `eld-q0-reviewer`, same uninvolved **Gemini 4 Carbon (High)** conversation **`0815536f-045a-4112-8a89-ebf0e0cc782f`** (`gemini-4-carbon-high`, explicit `high` effort), authorized by `docs/kickoffs/WP-0005-eld-q0-reviewer-correction.md`.
- **Author separation & predecessor preservation:** `/008` was authored by separate Carbon conversation `bd92ddc3-af60-4096-b683-65386d81b718`. Original `/002` (`84cef5ef30685ffee46281fefc5fd1356dbc1876` / `0331efd71ef17e5485adac5a53d864c6d96e8f4a` / `2a52ea58fae2badcb4e9ef47d1cb416c006edca4`, Opus `04e0efba-5292-4cae-b922-1517dee7bbed`), Opus reviewer checkpoints (`b75011da408fed5d2cc4f9025416ead6c5632ceb`, `ef72849519c83a71e59e80c311b48719252d0cd6`, Opus `e6147c9e-0303-475f-99ff-93ee38a681e4`), published `/003` (`17107f369a96d0f40d99c83f21ca72d902d3f035` / `f362a0fc748d1206fe24b4c60a0a74d98495524a` / `4752128b8ceaa65b6d0caa9e44ef7a97d1675dc8`), and Phase A (`b5f2f8ab888424a6961d88ee9f0c08a66d861b0a` / `ca81c44ed3114439036a2e95e2c20d6f6d5f7500`) remain byte-identical.
- **Lineage in `review/wp-0005-q0-carbon`:**
  1. Phase B continuation base: **`ca81c44ed3114439036a2e95e2c20d6f6d5f7500`**
  2. Normal merge of `/008` candidate **`24a5866b505532fd03e7db62a4e57875e4c5a170`**: **`d0edc9337212b84f8907ddc55e613245c7e63095`**
  3. Normal merge of published `/008` evidence **`b70ff45f2c7aa4b2e454429e76a15fa09887fa9d`** and canonical `/008` report **`460e1d81de14c6f77ea4a026bc4b3ab36407bdf7`**: **`3ba3cb124f52699e096992ab49210fb0200fec22`**
  4. Frozen Phase B verification helper commit (decisive check revision): **`a996543ed533393dc9857eb16f255880c8e08f56`**

## Separation of Verification Layers

1. **Real OS / Git / CLI subprocess boundary (established here):**
   - `8/8` spawned CPython `3.12.10` child processes across `build_stage_env(network=False)`, `build_stage_env(network=True)`, `build_child_env(owner="author")`, and `build_child_env(owner="reviewer")` × (`[-I, -B]`, `[-s, -P, -X, utf8]`), running from an outside-worktree `cwd` with `C:\Users\jackg\eLedgerCare-Q0` absent (`False`): `shutil.which("git") is None`, `Q0_GIT_EXECUTABLE` pins `C:\Program Files\Git\cmd\git.exe`, `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=NUL`, `GIT_TERMINAL_PROMPT=0` (verified via live `run_git config --list --show-origin`: only repo `.git/config`), polluted parent credentials/Git overrides stripped, live `release.code_identity` (`harness_clean: true`), live `locks.git_blob_reader` on all 3 pinned Git blobs (`ec8c650ed5fbeb0a754e4daee53aad53753a57a3`, `bca91aaa8e2d51eabb8e9d7d85c7f3602c4e8b8b`, `877d822099e7b3628d36f6b4a709d76ecad6de00`), and `locks.validate_lock` (`32` artifacts, `850` edges, `installable: true`).
   - `20/20` isolated `q0.py` CLI invocations across `stage_offline` and `child_reviewer`, plus `4` negative subprocess matrices (`16` fail-closed CLI exit-`2` `BLOCKED` checks), `5` environment-audit rejections (`SAFETY_VIOLATION`), and `3` direct `q0.py child` (`cmd_child`) subprocess probes (TOCTOU `code_identity` mismatch, missing Git in child, and matching live `code_identity` + live child lock-blob validation stopping cleanly at `STORAGE_NOT_OWNED`).
2. **Synthetic orchestration vs real model execution:**
   - `06-heartbeat-and-supervisor.json` exercises real Windows NTFS `os.replace` contention on `Heartbeat` and a real child process under `supervise(..., poll_s=0.02)`, explicitly tagged `backend_kind: "synthetic_FakeBackend_no_torch_no_gpu"`. It validates harness process/heartbeat orchestration only, **not** `Unlimited-OCR-2` inference or OCR accuracy.
3. **Observer-environment boundary vs unexecuted runtime gates:**
   - Host `q0.py host-precheck --stage initial` passes (`rc=0`, `git_runtime.present: true`, both `nvidia-smi` queries `rc=0`). When invoked inside stripped `stage_offline` (a non-contractual probe recorded in `04-cli-isolated-envs.json`, also confirmed by coordinator diagnostic `cb2629084a67a1d478c40e05a4e90ed92aea7158`), `git_runtime` still passes (`present: true`), while Windows `System32\nvidia-smi.exe` exits `255` (`Failed to initialize NVML`) because `nvidia-smi.exe` reads `ProgramFiles`. In the harness contract, `host-precheck` and `supervisor.run_observers` run in the normal parent host environment (`ProgramFiles` present), while `Session` inside `build_child_env` uses Torch's native CUDA interface rather than `nvidia-smi`. Whether native Torch/CUDA initialization inside unchanged `build_child_env` requires any additional Windows variable remains an empirical WP-0005 `/004` runtime gate.
4. **Pre-freeze exploratory smoke observations (preserved truthfully):**
   - Before freezing `a996543ed533393dc9857eb16f255880c8e08f56`, an exploratory stress probe ran `2` zero-sleep tight-looping reader threads (`while not stop: Path.read_bytes()`, `0 ms` sleep) concurrently with `4` writer threads and a `5 ms` daemon thread. Because two zero-sleep readers hold Win32 `CreateFileW` handles without `FILE_SHARE_DELETE` across nearly 100% of wall-clock time, `Heartbeat._beat_locked` exhausted its `5` attempts (`10 + 20 + 30 + 40 = 100 ms` total backoff) with `PermissionError: [WinError 5]`. That synthetic spin-loop does **not** match the harness contract, where a single `supervisor.py` process polls `heartbeat.json` once every `1.0 s` (`poll_s=1.0`, opening the file for sub-millisecond reads) while `Session` beats every `5.0 s` plus run/fixture/page transitions. Under `check_06`'s frozen aggressive periodic-reader contention check (`4` concurrent writer threads × `100` beats + `5 ms` daemon beat + `1` periodic reader at `poll_s=0.005 s`, **200× faster** than `supervisor.py`'s `1.0 s` poll) and a `poll_s=0.02 s` (`50×` faster) supervised child run, `0` errors occurred across `115` valid snapshots.
   - Four helper-only pre-freeze smoke bugs in draft `verify_coord_q0_01_phase_b.py` (`parents[5]` -> `parents[6]`; reading actual `11,885` / `6,461` / `3,986` frozen-file sizes and lock blob OIDs instead of hardcoded draft literals; recording the `stage_offline` `nvidia-smi` `ProgramFiles` boundary note separately from parent Stage A0 `host-precheck`; parsing `coord_diag["observations"][env_key]`) were fixed prior to freezing `a996543ed533393dc9857eb16f255880c8e08f56`. None reflected a defect in candidate `24a5866b505532fd03e7db62a4e57875e4c5a170`.

## Committed Phase B File Inventory

Captured on clean HEAD **`a996543ed533393dc9857eb16f255880c8e08f56`** (`2026-11-15T18:33:41.154376Z` to `2026-11-15T18:34:33.821836Z`) under `correction-009/.gitattributes` (`* -text`):

| Path (relative to `phase-b-2026-11-15/`) | Bytes | Raw SHA-256 |
| --- | ---: | --- |
| `verify_coord_q0_01_phase_b.py` | 60,887 | `4ce1272a404170352552430d6c2d0d86a7d2c7e7a217e0e32f1162b4fec24a23` |
| `outputs-a996543e/01-diff-and-immutability.json` | 2,515 | `3332f3a800b452d9bfbef8b89e89995bfe7000cc0f96fd278fb237a794024668` |
| `outputs-a996543e/02-unittest.txt` | 10,274 | `e93734437655b92a6971bc372104f6fbae6ecdff7c8f8c1a75ebc0221d8a8bff` |
| `outputs-a996543e/03-real-subprocess-git-matrix.json` | 11,257 | `000d6baa279db48122054170d91a8ce403c70ac8196bfabd96b3d33466e36b80` |
| `outputs-a996543e/04-cli-isolated-envs.json` | 5,592 | `c9259274a6c4d0962042b3d01d7df49f4294ca66682559c80f94c89e62467c2b` |
| `outputs-a996543e/05-fail-closed-git-probes.json` | 7,091 | `ca51d16e80e83d50b7d5d793cdd63b7f0f0f06fb24c3534bade2cc8e66cb37fa` |
| `outputs-a996543e/06-heartbeat-and-supervisor.json` | 1,063 | `d5f4bb0f5a73d5e8cebe376d244eeb10476f34bdce251ca4a543d618554332e5` |
| `outputs-a996543e/07-author-008-evidence-audit.json` | 2,927 | `091d2f4b5d5ae41422554ad90b22967c8f76e98775fc9a715d1917ba770317df` |
| `outputs-a996543e/summary.json` | 3,532 | `73625ac96f6d831c7a8f1879fa5fa7473b3ceead19eb618a16e1af4d1c2b3d1d` |
