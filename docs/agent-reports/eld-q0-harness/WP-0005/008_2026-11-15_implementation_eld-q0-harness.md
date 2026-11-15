# WP-0005 / 008: Bounded `COORD-Q0-01` isolated Git plumbing correction and real-subprocess verification

- Report path: `docs/agent-reports/eld-q0-harness/WP-0005/008_2026-11-15_implementation_eld-q0-harness.md`
- Sequence reservation: main `INDEX.md`, WP-0005 `/008` row; authoritative kickoff `docs/kickoffs/WP-0005-eld-q0-harness-correction.md` (published at `350097d06acbafe9323d89a8fb752a46bfccf5d0`, amended with `/009` Phase A receipt at `b1f904deaa2a7d0fa53bc4dd42587c618ef997bc`)
- Category: implementation
- Author / agent ID: `eld-q0-harness`
- Actual model / effort: **Gemini 4 Carbon (High)** (selected `gemini-4-carbon-high` via existing `agy.exe`, explicit `high` effort) in fresh, separate author conversation **`bd92ddc3-af60-4096-b683-65386d81b718`**, authorized under Jack's credits-first / Carbon-fallback instruction after Claude Pro 5-hour quota rejection and secondary AGY Opus attempt `ac662045-04ec-4de6-ba20-b2e6e8b2020d` (`RESOURCE_EXHAUSTED` / `429`, exit `3`, `0` tokens, `0` changes). Stopped original Claude Code Opus conversation `04e0efba-5292-4cae-b922-1517dee7bbed` authored `/002` (`84cef5ef…` / `0331efd7…` / `2a52ea58…`), which is preserved byte-for-byte. Separate uninvolved Carbon reviewer `0815536f-045a-4112-8a89-ebf0e0cc782f` (`eld-q0-reviewer`) was neither accessed nor reused.
- Execution environment: Antigravity CLI (`agy.exe`) on Windows 11 (`10.0.26200`), PowerShell shell; host CPython `3.12.10` (`C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe`, stdlib only) and Git `2.55.0.windows.1` (`C:\Program Files\Git\cmd\git.exe`).
- Published by: author (normal owned-branch push)
- Timestamp: 2026-11-15T18:11:30Z
- Repository / branch: `https://github.com/jackgumpe/eledgercare` (private) / `qualification/wp-0005-harness`; owned worktree `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-harness`
- Base revision: continuation/correction base **`2a52ea58fae2badcb4e9ef47d1cb416c006edca4`**; original WP-0005 base **`df9a2b50894f01987d779d7f9ae805794503ce6f`**
- Deliverable revision: frozen `/008` candidate **`24a5866b505532fd03e7db62a4e57875e4c5a170`** (harness tree `48ce82ffc8f78d27aa0338d5ec926ab9b1f683a4`); `/008` author evidence **`b70ff45f2c7aa4b2e454429e76a15fa09887fa9d`**
- Previous report: `docs/agent-reports/eld-q0-harness/WP-0005/002_2026-11-15_implementation_eld-q0-harness.md` (`2a52ea58fae2badcb4e9ef47d1cb416c006edca4`, authored by stopped Claude Code Opus session `04e0efba-5292-4cae-b922-1517dee7bbed`; candidate `84cef5ef30685ffee46281fefc5fd1356dbc1876`, evidence `0331efd71ef17e5485adac5a53d864c6d96e8f4a`)
- Related or reviewed reports:
  - Coordinator `COORD-Q0-01` diagnostic helper `73b5ba98d1e3834cc8c58768ff269730b867ee4c:docs/coordination/WP-0005/diagnostics/worker-git-check.py` (SHA-256 `a2125bdc42bfdbf3aa84056f9f0736f438d9d272dfaa085dd2a58b9f036b1c52`) and observation `8016f88f2e055e2a4e33335021824367e6230309:docs/coordination/WP-0005/diagnostics/worker-git-observation.json`
  - WP-0005 `/003` independent review `4752128b8ceaa65b6d0caa9e44ef7a97d1675dc8:docs/agent-reports/eld-q0-reviewer/WP-0005/003_2026-11-15_review_eld-q0-reviewer.md` (evidence `f362a0fc748d1206fe24b4c60a0a74d98495524a`, helper `17107f369a96d0f40d99c83f21ca72d902d3f035` on `review/wp-0005-q0-carbon`)
  - WP-0005 `/009` Phase A independent checkpoint `ca81c44ed3114439036a2e95e2c20d6f6d5f7500:docs/reviews/WP-0005/eld-q0-reviewer/correction-009/README.md` (helper `b5f2f8ab888424a6961d88ee9f0c08a66d861b0a`)
  - Upstream preflight / receipt pins unchanged from `/002`: Astra `/001` (`95ce0a8df728ae2c41aaf9e09d1b97c7d990fe36` / `2c32dde602b274251043bb216752f5d7fe9593be`), Astra `/007` (`d666c4163b8b6bdf5f6c69b455c30f3c377cbdc5` / `6cb6a258b9652b7becd3fca9c7cf2f04866c3ec3` / `951d408aabf7bdad3602c0e7698869e2e2457aed`), Opus reviewer receipt checkpoint `ef72849519c83a71e59e80c311b48719252d0cd6`
- Status: ready-for-review (author verification only; not independent acceptance)
- Next owner: separate uninvolved `eld-q0-reviewer` (`0815536f-045a-4112-8a89-ebf0e0cc782f`) for reserved WP-0005 `/009` Phase B correction review

## Summary

This bounded correction resolves **`COORD-Q0-01`** in the Q0 research harness and validates the frozen `/008` candidate **`24a5866b505532fd03e7db62a4e57875e4c5a170`** across real OS subprocesses spawned under every generated isolated environment (`build_stage_env(network=False)`, `build_stage_env(network=True)`, `build_child_env(owner="author")`, and `build_child_env(owner="reviewer")`).

In `/002` candidate `84cef5ef30685ffee46281fefc5fd1356dbc1876`, both environment builders stripped `PATH` to `<venv>\Scripts;<SystemRoot>\System32;<SystemRoot>` while `release.code_identity` and `locks.git_blob_reader` invoked bare `git`, raising `FileNotFoundError: [WinError 2]` inside spawned stage and runtime-child processes. Candidate `24a5866b505532fd03e7db62a4e57875e4c5a170` resolves this without widening `PATH` or inheriting the operator environment:

1. `build_stage_env` and `build_child_env` resolve and validate the exact host `git.exe` into `Q0_GIT_EXECUTABLE` (`C:\Program Files\Git\cmd\git.exe` on this host) and enforce `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=NUL`, and `GIT_TERMINAL_PROMPT=0`, while `PATH` remains `<venv>\Scripts;<SystemRoot>\System32;<SystemRoot>` (`shutil.which("git") is None`).
2. `release.code_identity` and `locks.git_blob_reader` route all Git plumbing calls through `q0harness.environment.run_git` (`[git_exe, "--no-optional-locks", ...]`, `stdin=DEVNULL`), failing closed with `Q0Failure("HOST_PRECHECK_FAILED")` or `Q0Failure("DEPENDENCY_LOCK_PENDING")` (`BLOCKED`, exit `2`) if Git is absent or invalid.
3. `q0.py child` re-verifies live `code_identity(REPO_ROOT)` inside the isolated child process against `parent-context.json`, and `host_precheck` records read-only `git_runtime` availability.
4. `q0harness/session.py` (`Heartbeat`) adds thread serialization (`threading.Lock()`) and a bounded 5-attempt (`10..50 ms`) retry on transient Windows `PermissionError` during `os.replace(tmp, self.path)`, fixing a real Windows NTFS race uncovered when running `supervise(...)` + `Session.run()` across real subprocesses.

**What is established is author CPU and isolated-subprocess harness readiness only.** No wheel or model shard was downloaded, no package was installed, `C:\Users\jackg\eLedgerCare-Q0` was never created (`false` before and after), no `torch`/`transformers`/model code was imported, and no CUDA/GPU execution occurred.

All frozen protocol, dependency-lock, and model-manifest blobs remain **byte-identical** to `84cef5ef30685ffee46281fefc5fd1356dbc1876`:

- `qualification/q0/harness/protocol.json`: **`dd8a7dc38c2a0c46103f6667f522656a2dddf5882727c18bf7b6b5426c5e2309`**
- `qualification/q0/harness/locks/dependency-lock.json`: **`d8eeaf0fe838d9df5728f17fcbacc8b504d98b79644a524b4faa705d97c49e6e`**
- `qualification/q0/harness/manifests/model-files.json`: **`085ac7ba1e25a7300846de18bdac19c7f9612bf417041643beff6a9cab6b8ea8`**

## Objective and acceptance criteria

Authorized scope from `docs/kickoffs/WP-0005-eld-q0-harness-correction.md`:

| Requirement | Where met |
| --- | --- |
| Fix `COORD-Q0-01` across both `build_stage_env` and `build_child_env` so mandatory Git identity and Git blob lock checks succeed in spawned Python processes | `q0harness/environment.py`, `q0harness/release.py`, `q0harness/locks.py`, `q0.py` |
| Retain strict environment allowlisting, stripped `PATH`, credential/switch scrubbing, and exact source/lock verification; do not inherit user env or alter global `PATH`/settings | `environment.py` (`Q0_GIT_EXECUTABLE`, `GIT_ISOLATION_ENV`, `_audit_git_pin`, `audit_stage_env`, `audit_child_env`) |
| Exercise the real OS subprocess boundary (not mocks or parent-env checks alone) across both environment builders using existing CPython `3.12.10` and Git without creating `C:\Users\jackg\eLedgerCare-Q0` | `tests/test_isolated_git_subprocess.py`, `evidence/008-git-isolation/verify_isolated_git.py`, `24a5866b/coordinator-worker-git-check.txt` |
| Preserve frozen protocol/lock/manifest values unchanged despite `/003` narrative errata (3-page F07, `ngram_window` `128`/`1024`, non-cryptographic PEP 658 index SHA-256 + TLS TOFU receipt) | Verified by unchanged blob SHA-256s above |
| Preserve all prior `/002` authorship, reports, and evidence byte-for-byte; freeze candidate first, run decisive checks on clean candidate, commit `/008` evidence second, publish `/008` report third, verify `origin`, and stop for `/009` | Candidate `24a5866b…` -> evidence `b70ff45f…` -> this `/008` report |

## Change inventory

### Continuation base to frozen `/008` candidate (`2a52ea58fae2badcb4e9ef47d1cb416c006edca4..24a5866b505532fd03e7db62a4e57875e4c5a170` — 14 paths)

All 14 candidate changes lie inside `qualification/q0/harness/` (`13` modified, `1` added):

| Action | Exact path | What changed and why | Relevant symbols |
| --- | --- | --- | --- |
| Modified | `qualification/q0/harness/q0harness/environment.py` | Pin validated absolute `git.exe` via `Q0_GIT_EXECUTABLE` without widening `PATH`; enforce `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=NUL`, `GIT_TERMINAL_PROMPT=0`; audit stage and child Git pins (rejecting missing/non-`git` binaries or paths inside mutable task root); execute Git plumbing via `run_git` (`--no-optional-locks`, `stdin=DEVNULL`) | `GIT_EXECUTABLE_VAR`, `GIT_ISOLATION_ENV`, `validate_git_executable`, `resolve_host_git`, `resolve_runtime_git`, `run_git`, `_audit_git_pin`, `audit_stage_env`, `build_stage_env`, `audit_child_env`, `build_child_env` |
| Modified | `qualification/q0/harness/q0harness/release.py` | Route `rev-parse HEAD` and `status --porcelain=v1` through `run_git` instead of bare `subprocess.run(["git", ...])` | `code_identity` |
| Modified | `qualification/q0/harness/q0harness/locks.py` | Route `cat-file blob <oid>` through `run_git` and translate unavailable-Git `Q0Failure` into fail-closed `Q0Failure("DEPENDENCY_LOCK_PENDING", ...)` | `git_blob_reader` |
| Modified | `qualification/q0/harness/q0harness/hostcheck.py` | Record read-only `git_runtime` check (`present`, `executable`) and fail `host_precheck` with `HOST_PRECHECK_FAILED` if host Git is absent | `host_precheck` |
| Modified | `qualification/q0/harness/q0.py` | Evaluate `code_identity(REPO_ROOT)` inside `cmd_execute`'s `try` block so missing Git fails closed as `BLOCKED` JSON before directory creation; re-verify live `code_identity(REPO_ROOT)` inside `cmd_child` against `parent-context.json` | `cmd_execute`, `cmd_child` |
| Modified | `qualification/q0/harness/q0harness/session.py` | Serialize `Heartbeat` daemon/main-thread beats with `threading.Lock()` and retry transient Windows `PermissionError` (`os.replace`) up to 5 times (`10..50 ms`) | `Heartbeat`, `Heartbeat._beat_locked` |
| Modified | `qualification/q0/harness/ACQUISITION.md` | Document `Q0_GIT_EXECUTABLE` and Git config isolation in stage environment description | Stage isolation notes |
| Modified | `qualification/q0/harness/PROTOCOL.md` | Document `Q0_GIT_EXECUTABLE` and Git config isolation alongside stripped `PATH` in §1 | §1 Storage and environment isolation |
| Modified | `qualification/q0/harness/README.md` | Note explicit `Q0_GIT_EXECUTABLE` pinning without widening `PATH` | Isolation summary |
| Modified | `qualification/q0/harness/tests/test_environment_writer_memory.py` | Assert `Q0_GIT_EXECUTABLE`, `GIT_ISOLATION_ENV`, stripped `PATH` (`git` absent from `PATH`), and rejection of missing or mutable-root `git.exe` pins in `ChildEnvironment` | `ChildEnvironment` |
| Modified | `qualification/q0/harness/tests/test_host_model_env.py` | Assert `git_runtime` in `HostPrecheck` (including injectable missing-Git failure) and `Q0_GIT_EXECUTABLE` / `audit_stage_env` invariants in `StageEnvironmentAndLogs` | `HostPrecheck`, `StageEnvironmentAndLogs` |
| Modified | `qualification/q0/harness/tests/test_locks_preflight.py` | Use `run_git` instead of bare `git` in `cuda_records()` test helper so lock tests run cleanly even when invoked inside an isolated stage/child parent environment | `cuda_records` |
| Modified | `qualification/q0/harness/tests/test_session.py` | Add deterministic unit test for `Heartbeat` thread serialization and transient Windows `PermissionError` retry/exhaustion | `SessionBookkeeping.test_heartbeat_serializes_threads_and_retries_transient_replace_lock` |
| Added | `qualification/q0/harness/tests/test_isolated_git_subprocess.py` | Add 4 real OS subprocess test methods exercising stage/child API probes, CLI subcommands (`status`, `lock-check`, `write-requirements`, `execute`), supervised `Session.run()`, and fail-closed negative/untrusted-`PATH` cases | `IsolatedGitSubprocess` |

### Frozen `/008` candidate to `/008` evidence (`24a5866b505532fd03e7db62a4e57875e4c5a170..b70ff45f2c7aa4b2e454429e76a15fa09887fa9d` — 18 paths)

All 18 additions lie under `qualification/q0/harness/evidence/008-git-isolation/`:

- `.gitattributes` (`* -text`), `README.md`, `run_checks.py`, `verify_isolated_git.py` (4 files)
- `24a5866b/01-unittest.txt` through `24a5866b/12-isolated-git-subprocess-check.txt`, `24a5866b/coordinator-worker-git-check.txt`, and `24a5866b/summary.json` (14 raw output/summary files)

Cumulative path counts verified via `git diff --name-only`:

- `2a52ea58..24a5866b`: `14` paths
- `24a5866b..b70ff45f`: `18` paths
- `2a52ea58..b70ff45f`: `32` paths
- `df9a2b50..b70ff45f`: `108` paths (`88` `/002` harness paths + `1` `/002` report + `1` new `/008` test file + `18` new `/008` evidence files)

### Metadata committed afterward and external effects

- **Report metadata committed afterward:** only this file (`docs/agent-reports/eld-q0-harness/WP-0005/008_2026-11-15_implementation_eld-q0-harness.md`).
- **Ignored local scratch:** `.scratch/msg-008-candidate.txt`, `.scratch/msg-008-evidence.txt`, `.scratch/msg-008-report.txt`, and `.scratch/coordinator-worker-git-check-24a5866b.txt` inside this worktree's untracked `.scratch/` (prior `.scratch/msg-*.txt` files from `/002` preserved untouched).
- **External effects:** normal push of owned branch `qualification/wp-0005-harness` to `origin`; read-only host checks (`nvidia-smi`, `System32` DLLs, registry reads, volume free space) and ephemeral child Python/Git processes during test execution. `C:\Users\jackg\eLedgerCare-Q0` remained absent (`false` -> `false`). No coordinator file, reviewer worktree, package installation, model/wheel download, GPU context, or global setting was touched.

## Decisions and rationale

1. **Pin `Q0_GIT_EXECUTABLE` explicitly rather than adding `Git\cmd` to `PATH`.** On Windows, `C:\Program Files\Git\cmd` (and especially user shim directories when Git is installed elsewhere) can expose sibling executables (`git-lfs.exe`, `scalar.exe`, `gitk.exe`, `start-ssh-agent.cmd`, or unrelated shims) to every child library call. Keeping `PATH` strictly `<venv>\Scripts;<SystemRoot>\System32;<SystemRoot>` (`shutil.which("git") is None`) while binding the validated absolute `git.exe` path in `Q0_GIT_EXECUTABLE` satisfies `COORD-Q0-01` with minimum surface area.
2. **Prevent untrusted `PATH` hijacking and user/system Git config leakage.** `resolve_host_git` checks explicit `Q0_GIT_EXECUTABLE` first, then canonical system locations (`%ProgramW6432%\Git\cmd\git.exe`, `%ProgramFiles%\Git\cmd\git.exe`, `C:\Program Files\Git\cmd\git.exe`) before consulting parent `PATH`, so an untrusted directory prepended to an operator's `PATH` cannot shadow the system `git.exe`. `_audit_git_pin` rejects any `Q0_GIT_EXECUTABLE` inside `root` or `run_dir`. Every `run_git` call passes `--no-optional-locks`, `stdin=DEVNULL`, `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=NUL`, and `GIT_TERMINAL_PROMPT=0` so Git never writes `.git/index.lock` during background status checks, never reads user/system `.gitconfig` or credential helpers, and never blocks on interactive prompts.
3. **Strict active-environment resolution at runtime (`resolve_runtime_git`).** Unlike `resolve_host_git` (used by parent builders and `host_precheck`), `resolve_runtime_git` inspects only the active process's `Q0_GIT_EXECUTABLE` and `PATH`—it never silently probes `C:\Program Files\Git` if `Q0_GIT_EXECUTABLE` was omitted. Consequently, an improperly constructed isolated environment fails closed immediately (`HOST_PRECHECK_FAILED` / `DEPENDENCY_LOCK_PENDING`) rather than masking a broken environment builder.
4. **Live child `code_identity` cross-check.** Previously `cmd_child` trusted `ctx["code_identity"]` written by the parent because the child lacked Git access. With `Q0_GIT_EXECUTABLE` available in `build_child_env`, `cmd_child` now calls `code_identity(REPO_ROOT)` directly inside the isolated child and marks `harness_clean: False` if the live child observation fails or diverges from `parent-context.json`.
5. **Windows `Heartbeat` concurrency fix (`session.py`).** Exercising a real supervised `Session.run()` child process (`test_supervised_child_session_runs_real_git_checks`) uncovered a genuine Windows NTFS defect: `Heartbeat` wrote `heartbeat.tmp` and called `os.replace(tmp, self.path)` from both its background thread and `set_phase()` without a lock, and on Windows `os.replace` transiently raises `PermissionError: [WinError 5] Access is denied` while `supervisor.py` has `heartbeat.json` open for reading. Adding `threading.Lock()` and 5 bounded retries (`10..50 ms`) fixes the race cleanly without masking persistent permission errors.
6. **Preserving frozen protocol and lock values unchanged.** As instructed in the kickoff and independently reconciled in `/009` Phase A (`ca81c44ed3114439036a2e95e2c20d6f6d5f7500`), `/003`'s three narrative misstatements (`F07` 6 pages vs protocol `3`; `ngram_window` formula vs protocol `128` for `F01` and `1024` for `F07`; "publisher-signed" PEP 658 metadata vs published index SHA-256 over TLS + `local-sha256-TOFU` wheel receipt) were report-only errata in `/003`. `protocol.json`, `locks/dependency-lock.json`, and `manifests/model-files.json` were already accurate and remain untouched.

## Verification

Decisive checks executed on clean frozen candidate **`24a5866b505532fd03e7db62a4e57875e4c5a170`** between `2026-11-15T18:08:01.088703Z` and `2026-11-15T18:08:49.394047Z`, committed at **`b70ff45f2c7aa4b2e454429e76a15fa09887fa9d`**. All 12 `summary.json` output blobs plus `coordinator-worker-git-check.txt` were verified via `git cat-file blob` to match their recorded SHA-256 digests byte-for-byte.

| Check / exact command (from worktree root) | Environment & revision | Actual result | Evidence location |
| --- | --- | --- | --- |
| `python.exe -I -B "C:\Users\jackg\Asp.net Projects\eledgercare\docs\coordination\WP-0005\diagnostics\worker-git-check.py"` (verified SHA-256 `a2125bdc…`) | Host Python `3.12.10` spawning `install_stage` & `runtime_child` on clean `24a5866b` | Exit `0`: `runtime_root_exists: false`; both `install_stage` and `runtime_child` return `rc=0`, `git_which: null`, `code_identity: {"head": "24a5866b505532fd03e7db62a4e57875e4c5a170", "harness_clean": true, "dirty": []}` | `evidence/008-git-isolation/24a5866b/coordinator-worker-git-check.txt` (`cb4bd758…`) |
| `python.exe -I -B qualification/q0/harness/evidence/008-git-isolation/run_checks.py 24a5866b` | Host Python `3.12.10` on clean `24a5866b` | Exit `0`: `HEAD` unchanged (`24a5866b…`), tracked diff empty, `C:\Users\jackg\eLedgerCare-Q0` `false` -> `false`, `.scratch/never-written.txt` absent, `scratch_test_dirs_left: []` | `evidence/008-git-isolation/24a5866b/summary.json` (`9770a6a2…`) |
| ↳ `-m unittest discover -s qualification/q0/harness/tests -t qualification/q0/harness/tests -v` | `-I -B` + spawned isolated stage/child subprocesses on `24a5866b` | Exit `0` (`36.875s`): **80 tests ran: 79 passed, 1 skipped** (`test_links_rejected`, `WinError 1314` symlink privilege) | `24a5866b/01-unittest.txt` (`e6d0160d…`) |
| ↳ `q0.py verify-snapshots` | `-I -B` on `24a5866b` | Exit `0`: 4 snapshots match pinned HF blobs; static save-path facts unchanged | `24a5866b/02-verify-snapshots.txt` (`ab0d1999…`) |
| ↳ `q0.py derive-rasters --check` | `-I -B` on `24a5866b` | Exit `0`: `F01` p1 and `F07` p1-p3 RGB digests match `protocol.json` | `24a5866b/03-derive-rasters-check.txt` (`3830bbd1…`) |
| ↳ `q0.py build-model-manifest --check` | `-I -B` on `24a5866b` | Exit `0`: `identical_to_derivation: true` (18 runtime objects + 1 notice) | `24a5866b/04-model-manifest-check.txt` (`b9503dd1…`) |
| ↳ `q0.py check-protocol` | `-I -B` on `24a5866b` | Exit `0`: `protocol_sha256` `dd8a7dc3…`; `F01` (`1,490` B) & `F07` (`4,060` B) verified | `24a5866b/05-check-protocol.txt` (`3698b7f7…`) |
| ↳ `q0.py lock-check` | `-I -B` on `24a5866b` | Exit `0`: `lock_sha256` `d8eeaf0f…`, 32 artifacts (`31` publisher, `1` `local-sha256-TOFU`), `installable: true`, 850 edges, receipt checks all `true` | `24a5866b/06-lock-check.txt` (`e1769d40…`) |
| ↳ `q0.py status` | `-I -B` on `24a5866b` | Exit `0`: `code_identity` `24a5866b…` (`harness_clean: true`), `storage_root_exists: false` | `24a5866b/07-status.txt` (`ed4bb346…`) |
| ↳ `q0.py host-precheck --stage initial` | `-I -B` on `24a5866b` | Exit `0`: `status: "pass"`, `git_runtime: {"executable": "C:\\Program Files\\Git\\cmd\\git.exe", "present": true}`, `C:\` free `68,484,792,320` B, MSVC `14.51.36247.0` ×3, `LongPathsEnabled=0` (known max `162`), both `nvidia-smi` queries `rc=0` | `24a5866b/08-host-precheck-initial.txt` (`e06e9aee…`) |
| ↳ `q0.py execute --owner author` | `-I -B` on `24a5866b` | Exit `2` (expected): `BLOCKED` (`EXECUTION_NOT_RELEASED`), `accuracy_score: null` | `24a5866b/09-execute-refused.txt` (`f6c35002…`) |
| ↳ `q0.py write-requirements .scratch/never-written.txt` | `-I -B` on `24a5866b` | Exit `2` (expected): `BLOCKED` (`EXECUTION_NOT_RELEASED`), file not created | `24a5866b/10-write-requirements-refused.txt` (`7237b13d…`) |
| ↳ `q0.py verify-wheelhouse .scratch` | `-I -B` on `24a5866b` | Exit `2` (expected): `BLOCKED` (`EXECUTION_NOT_RELEASED`) | `24a5866b/11-verify-wheelhouse-refused.txt` (`7237b13d…`) |
| ↳ `verify_isolated_git.py` | Spawned child processes across `acquire_stage_network`, `install_stage_offline`, `runtime_child_author`, `runtime_child_reviewer` on `24a5866b` | Exit `0`: `status: "pass"`, all 4 environment API probes + 4 isolated CLI checks (`status`/`lock-check`) + released `write-requirements` (32 lines, SHA-256 `a1598dca…`) + unreleased `write-requirements` (`rc=2`, `EXECUTION_NOT_RELEASED`) + nested offline-stage `unittest` (`rc=0`) passed; external root `false` -> `false` | `24a5866b/12-isolated-git-subprocess-check.txt` (`ce5dc2aa…`) |

### Pre-freeze development failures (preserved and separated)

During local pre-freeze testing before `24a5866b505532fd03e7db62a4e57875e4c5a170` was committed, an initial 79-test development run recorded 2 failures:

1. **Source defect (`q0harness/session.py`):** `test_supervised_child_session_runs_real_git_checks` failed with `PermissionError: [WinError 5] Access is denied` at `os.replace(tmp, self.path)` in `Heartbeat.beat` during `Session.run()` shutdown on Windows NTFS (concurrent daemon/main-thread writes and `supervisor.py` reads of `heartbeat.json`). Resolved before freeze in `session.py` (`threading.Lock()` + bounded 5-attempt retry) and covered by `test_heartbeat_serializes_threads_and_retries_transient_replace_lock`.
2. **Test-helper expectation defect (`tests/test_isolated_git_subprocess.py`):** `test_missing_invalid_or_untrusted_git_fails_closed` initially expected `q0.py status` without Git to return `HOST_PRECHECK_FAILED`, whereas `cmd_status` calls `_lock()` (`git_blob_reader`) before `code_identity()` and legitimately raises `DEPENDENCY_LOCK_PENDING`. Resolved before freeze by asserting `DEPENDENCY_LOCK_PENDING` on `status` / `lock-check` and `HOST_PRECHECK_FAILED` on `execute --owner author`.

### Checks not run

- Wheel, PyTorch, or model-shard downloads (not authorized).
- Real 32-wheel `METADATA` check against downloaded wheels (tested on synthetic wheels and committed CUDA `METADATA` blobs).
- `venv` creation, `pip install`, `pip check`, and installed `venv` path-length walk (not released).
- Real `pypdfium2` PDF rendering, `torch` / `transformers` / tokenizer imports, `backend_torch.py`, model loading, CUDA allocation, or GPU qualification runs (held for `/004` after `/009` acceptance and coordinator resource/lease release).
- Real Windows symlink rejection (`WinError 1314`: privilege not held by user account).

## Review map

- **Pinned diffs:**
  - Candidate source/test/doc diff (`14` paths): `2a52ea58fae2badcb4e9ef47d1cb416c006edca4..24a5866b505532fd03e7db62a4e57875e4c5a170`
  - Author `/008` evidence diff (`18` paths): `24a5866b505532fd03e7db62a4e57875e4c5a170..b70ff45f2c7aa4b2e454429e76a15fa09887fa9d`
- **Primary source files to inspect:**
  - `qualification/q0/harness/q0harness/environment.py` (`GIT_EXECUTABLE_VAR`, `GIT_ISOLATION_ENV`, `validate_git_executable`, `resolve_host_git`, `resolve_runtime_git`, `run_git`, `_audit_git_pin`, `audit_stage_env`, `build_stage_env`, `audit_child_env`, `build_child_env`)
  - `qualification/q0/harness/q0harness/release.py` (`code_identity`) and `qualification/q0/harness/q0harness/locks.py` (`git_blob_reader`)
  - `qualification/q0/harness/q0.py` (`cmd_execute`, `cmd_child`) and `qualification/q0/harness/q0harness/hostcheck.py` (`host_precheck`)
  - `qualification/q0/harness/q0harness/session.py` (`Heartbeat`)
  - `qualification/q0/harness/tests/test_isolated_git_subprocess.py` and `qualification/q0/harness/tests/test_session.py`
- **Portable reviewer reproduction:** From the reviewer's own isolated worktree (with `qualification/wp-0005-harness` fetched/merged per coordinator instructions), run:
  - `C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe -I -B qualification/q0/harness/evidence/008-git-isolation/run_checks.py <reviewer-subdir>`
  - Both `run_checks.py` and `verify_isolated_git.py` resolve paths relative to their own worktree (`HERE.parents[4]`) and never touch `eld-q0-harness` or `C:\Users\jackg\eLedgerCare-Q0`.

## Risks, disagreements, and unfinished work

- **No open source disagreements.** Both the coordinator's `COORD-Q0-01` reproduction (`73b5ba98…`) and the independent reviewer's `/009` Phase A reproduction (`b5f2f8ab…` / `ca81c44e…`) are directly addressed and exercised across real child processes.
- **Host Git path assumption across stages.** `build_stage_env` and `build_child_env` pin the validated host `git.exe` (`C:\Program Files\Git\cmd\git.exe` on this machine, or an explicit `Q0_GIT_EXECUTABLE` override). If Git were uninstalled before `/004` execution, `host-precheck`, `_install_gate`, and `execute` will fail closed (`HOST_PRECHECK_FAILED` / `DEPENDENCY_LOCK_PENDING`).
- **Remaining Q0 runtime unknowns are unchanged from `/002`.** CPU and isolated-subprocess readiness does not establish wheel installation path lengths under `LongPathsEnabled=0`, `torch`/`transformers` import under `cu130` (`sm_120`), dense SDPA fallback behaviour, memory/VRAM peaks, determinism, or inference completion; all belong to `/004`–`/006` after independent `/009` disposition and coordinator release.

## Handoff

- **Next action & owner:** Independent non-author review in reserved **WP-0005 `/009`** (Phase B) by separate Carbon reviewer **`eld-q0-reviewer`** (`0815536f-045a-4112-8a89-ebf0e0cc782f`), dispatched by **`eld-coordinator`**.
- **Pinned revisions for `INDEX.md` / `/009` binding:**
  - Owned branch: `qualification/wp-0005-harness`
  - Continuation base: `2a52ea58fae2badcb4e9ef47d1cb416c006edca4` (original WP-0005 base `df9a2b50894f01987d779d7f9ae805794503ce6f`)
  - Frozen `/008` candidate SHA: **`24a5866b505532fd03e7db62a4e57875e4c5a170`** (harness tree `48ce82ffc8f78d27aa0338d5ec926ab9b1f683a4`)
  - Author `/008` evidence SHA: **`b70ff45f2c7aa4b2e454429e76a15fa09887fa9d`**
  - Canonical `/008` report path: `docs/agent-reports/eld-q0-harness/WP-0005/008_2026-11-15_implementation_eld-q0-harness.md` (its publication commit SHA is supplied in the handoff message after commit and `origin` verification; this report does not claim to contain its own commit SHA).
- **Publication receipt:** Candidate `24a5866b505532fd03e7db62a4e57875e4c5a170` and evidence `b70ff45f2c7aa4b2e454429e76a15fa09887fa9d` are committed locally on `qualification/wp-0005-harness` and pushed with this report; exact remote object verification on `origin/qualification/wp-0005-harness` is executed immediately after this commit and reported to the coordinator/user. No runtime or installation stage is released by this publication.
