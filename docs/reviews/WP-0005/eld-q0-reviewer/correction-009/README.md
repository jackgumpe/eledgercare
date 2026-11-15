# WP-0005 /009 Phase A Checkpoint: Independent `COORD-Q0-01` Reproduction and `/003` Factual Reconciliation (`eld-q0-reviewer`)

## Attribution, State, and Phase Boundary

- **Stable review role:** `eld-q0-reviewer`, same uninvolved **Gemini 4 Carbon (High)** conversation **`0815536f-045a-4112-8a89-ebf0e0cc782f`** (`gemini-4-carbon-high`, explicit `high` effort), authorized by `docs/kickoffs/WP-0005-eld-q0-reviewer-correction.md` at `350097d06acbafe9323d89a8fb752a46bfccf5d0`.
- **Predecessor and prior-report preservation:** Earlier Opus checkpoints (`e6147c9e-0303-475f-99ff-93ee38a681e4`, `b75011da408fed5d2cc4f9025416ead6c5632ceb`, `ef72849519c83a71e59e80c311b48719252d0cd6`) remain attributed to Opus. Published `/003` helper (`17107f369a96d0f40d99c83f21ca72d902d3f035`), `/003` evidence (`f362a0fc748d1206fe24b4c60a0a74d98495524a`), `/003` canonical report (`4752128b8ceaa65b6d0caa9e44ef7a97d1675dc8`, SHA-256 `eaa629c2b754c3e5514da26ba208a7d2cfa92130418864fc43dc8227a4f8ea9b`), and initial harness candidate (`84cef5ef30685ffee46281fefc5fd1356dbc1876`, tree `b7afcd512d508e43b874cf7b9857b7493359a879`) are preserved byte-for-byte.
- **Current state:** **Phase A prepared/published checkpoint only.** Canonical `/009` (`docs/agent-reports/eld-q0-reviewer/WP-0005/009_2026-11-15_review_eld-q0-reviewer.md`) and corrected-source review remain **HELD** until `eld-coordinator` binds exact `/008` candidate, evidence, and report SHAs in Phase B. The separate `/008` Carbon author worktree was not inspected or touched.

## Phase A.1: Independent Reproduction of `COORD-Q0-01` on Unchanged `84cef5ef…` Source

Frozen Phase A helper [reproduce_coord_q0_01_phase_a.py](reproduce_coord_q0_01_phase_a.py) (`b5f2f8ab888424a6961d88ee9f0c08a66d861b0a`) verified coordinator diagnostic helper `73b5ba98d1e3834cc8c58768ff269730b867ee4c:docs/coordination/WP-0005/diagnostics/worker-git-check.py` (SHA-256 `a2125bdc42bfdbf3aa84056f9f0736f438d9d272dfaa085dd2a58b9f036b1c52`) and observation `8016f88f2e055e2a4e33335021824367e6230309` from the shared Git object store without running the coordinator's author-targeted script, then independently executed real separate Python 3.12.10 (`-I -B`) child processes against this reviewer worktree's unchanged `84cef5ef…` harness source ([phase-a-b5f2f8ab/summary.json](phase-a-b5f2f8ab/summary.json)):

1. **Parent-process control (operator `PATH` includes `C:\Program Files\Git\cmd\git.EXE`):**
   - `release.code_identity(REPO_ROOT)` succeeds (`head: b5f2f8ab…`, `harness_clean: true`), `locks.git_blob_reader` reads `123,592` B (`ec8c650e…`), and `locks.validate_lock` validates all `32` artifacts.
2. **Real child API probes under all generated environments (`build_stage_env(network=False)`, `build_stage_env(network=True)`, and `build_child_env`):**
   - Each builder sets `PATH` solely to `[C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv\Scripts, C:\WINDOWS\System32, C:\WINDOWS]`.
   - Inside every spawned child process:
     - `shutil.which("git")` is `null`.
     - `q0harness.release.code_identity(repo_root)` raises **`FileNotFoundError: [WinError 2] The system cannot find the file specified`** (`errno=2`, `winerror=2`).
     - `q0harness.locks.git_blob_reader(repo_root)("ec8c650ed5fbeb0a754e4daee53aad53753a57a3")` raises **`FileNotFoundError: [WinError 2] The system cannot find the file specified`**.
     - `q0harness.locks.validate_lock(lock, locks.git_blob_reader(repo_root))` raises **`FileNotFoundError: [WinError 2] The system cannot find the file specified`**.
   - Note: `reproduce_coord_q0_01_phase_a.py` exits `0` because its child API harness catches and records those `FileNotFoundError` exceptions to assert reproduction; the underlying identity and lock checks **failed** in every generated child environment.
3. **Real child `q0.py` CLI invocations under `build_stage_env(network=False)` and `build_child_env`:**
   - Spawning `q0.py status`, `q0.py lock-check`, and `q0.py write-requirements .scratch/phase-a-never-written.txt` under `install_stage_offline` (`01..03-*.txt`) and `q0.py status` / `q0.py lock-check` under `runtime_child` (`04..05-*.txt`) each terminated with **`exit_code: 1`** and an uncaught `FileNotFoundError: [WinError 2]` traceback at `q0harness/locks.py:46` (`subprocess.run(["git", "cat-file", "blob", oid], ...)`). In `q0.py child` (`Session._run`, `session.py:139`), the same `validate_lock(..., self.lock_reader)` call occurs at the start of every supervised runtime run.

### Effect on Earlier `/003` Readiness Conclusion

- **Does `COORD-Q0-01` change `/003`'s bounded pre-execution readiness conclusion?** **Yes.** Unchanged candidate `84cef5ef30685ffee46281fefc5fd1356dbc1876` is **not** ready for install or runtime release: its own stage and runtime-child environment builders strip `Git` from `PATH` while both `_install_gate` (`code_identity` + `locks.git_blob_reader`) and `cmd_child` (`locks.git_blob_reader`) invoke bare `git` subprocesses. Accordingly, the updated review disposition on unchanged `84cef5ef30685ffee46281fefc5fd1356dbc1876` is **`CHANGES REQUESTED` (`COORD-Q0-01`)**, pending `/008` harness correction and `/009` Phase B verification.
- **Why `/003` missed it:** `/003` (`17107f36`) verified `build_child_env` and `build_stage_env` dictionary keys in-process while executing `q0.py status` and `q0.py lock-check` in the parent shell environment (which had `git.exe` on `PATH`), and author unit tests injected in-memory lock readers / precomputed `code_identity` dicts instead of spawning real child processes under the generated environments.
- **Scope classification:** Harness subprocess/environment integration defect only—**not** a model failure, runtime qualification failure, or OCR accuracy result. `C:\Users\jackg\eLedgerCare-Q0` remained absent (`false` → `false`).

## Phase A.2: Reconciliation of `/003` Narrative Discrepancies Against Unchanged Protocol and Evidence

Machine-verified against unchanged `qualification/q0/harness/protocol.json` (`dd8a7dc38c2a0c46103f6667f522656a2dddf5882727c18bf7b6b5426c5e2309`), `protocol.py`, `cuda-metadata.json` (`bca91aaa8e2d51eabb8e9d7d85c7f3602c4e8b8b`), and `torchvision-acquisition-receipt.json` (`877d822099e7b3628d36f6b4a709d76ecad6de00`) in [phase-a-b5f2f8ab/reconciliation-003.json](phase-a-b5f2f8ab/reconciliation-003.json):

| ID | Erroneous `/003` Report Wording (`4752128b…`) | Actual Unchanged Protocol / Evidence Fact | Impact |
| --- | --- | --- | --- |
| `R-003-01` | Stated `F07/SYN-MP-01-v0-clean.pdf` is "6 pages" / "6-page `F07`" (`/003` L62, L88) | **`3` pages** (`protocol.json` L70 `page_count: 3`, 3 `2550x3301` raster digests, `max_new_tokens: 24000` = `8000 * 3`, timeout key `call_pages_3: 3600`) | Narrative erratum in `/003` only; `protocol.json` and `derive-rasters --check` were already 3 pages |
| `R-003-02` | Stated `ngram_window=max(2048,512*N)` (`/003` L62) | **`128` for 1-page `F01`** and **`1024` for 3-page `F07`**, per frozen rule `"1024 if page_count > 1 else 128 (upstream README evaluation setup), no whitelist"` (`protocol.json` L51, L72, L113; `protocol.py:71-73`) | Narrative erratum in `/003` only; `protocol.json` and `protocol.py` already implement `128` / `1024` |
| `R-003-03` | Described PEP 658 `METADATA` digest `f8e91ee9…` as "publisher-signed" (`/003` L86) | **Published PEP 658 SHA-256 attribute over HTTPS/TLS** (`data-dist-info-metadata` from the official PyTorch `cu130` index matching the wheel's `METADATA` member `f8e91ee987603053e2166e2e4063ddcfb533f266c88bae82b7f79119aadceb59`). **No publisher cryptographic signature** (PGP/Sigstore/wheel signature) was published or verified; wheel payload `5ae0ff50…` remains `local-sha256-TOFU` over TLS | Narrative overstatement in `/003` corrected here and for `/009`; lock and Opus receipt already state non-cryptographic TLS/TOFU limits accurately |

## Phase A Output Inventory (`phase-a-b5f2f8ab/`)

Captured on clean HEAD `b5f2f8ab888424a6961d88ee9f0c08a66d861b0a` (`2026-11-15T17:52:30.641965Z` to `17:52:32.555478Z`) under `* -text`:

| File | Exit | Bytes | Raw SHA-256 |
| --- | --- | --- | --- |
| `phase-a-b5f2f8ab/01-stage-offline-q0-status.txt` | 1 (reproduced `WinError 2`) | 2,734 | `747f601794701fc33e813fed35fe374475ee5ca813810a4dcd2b3a0f6bd7fba2` |
| `phase-a-b5f2f8ab/02-stage-offline-q0-lock-check.txt` | 1 (reproduced `WinError 2`) | 2,734 | `2c7a47b8b745deaa74baf4306aff5f317d8a3e3f93d7c662ee39183e701249ad` |
| `phase-a-b5f2f8ab/03-stage-offline-q0-write-requirements.txt` | 1 (reproduced `WinError 2`) | 2,962 | `3a4aec2af51115157294857935cc1922732847371d342c1b8a73f4eb8f15f3c1` |
| `phase-a-b5f2f8ab/04-runtime-child-q0-status.txt` | 1 (reproduced `WinError 2`) | 2,734 | `747f601794701fc33e813fed35fe374475ee5ca813810a4dcd2b3a0f6bd7fba2` |
| `phase-a-b5f2f8ab/05-runtime-child-q0-lock-check.txt` | 1 (reproduced `WinError 2`) | 2,734 | `2c7a47b8b745deaa74baf4306aff5f317d8a3e3f93d7c662ee39183e701249ad` |
| `phase-a-b5f2f8ab/reconciliation-003.json` | — | 2,334 | `598f712d021a48d855186e14cfb1e958dca237290b307a1b1221331ca560323d` |
| `phase-a-b5f2f8ab/summary.json` | — | 8,370 | `0000fb0ef296a1b476aeaa3e2c404124c67fa7dc094462ea63140feca38b3d35` |
