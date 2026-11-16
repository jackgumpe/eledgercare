# WP-0006 F2 Author Runtime Trial Evidence, Concrete Defect Report, and Explicit GPU Lease Return (`eld-f2-implementer`)

> **Disposition**: **BLOCKED ON CONCRETE 2-LINE WORKER ENTRYPOINT DEFECT AFTER ATTEMPT #1 (`1 / 4` model attempts used); GPU LEASE `WP-0006-author-runtime-20261116T062318Z` EXPLICITLY RETURNED WITH ALL OWNED PROCESSES OBSERVED EXITED AND ALL 18 MODEL OBJECTS UNCHANGED.**
>
> Per `docs/kickoffs/WP-0006-eld-f2-author-runtime.md` (`717a768994bbbabf75b8ee96b3b1aadca1bc5df3`), no product source edits and no extra retry attempts were performed under this lease, and canonical `docs/agent-reports/eld-f2-implementer/WP-0006/003_2026-11-16_implementation_eld-f2-implementer.md` is intentionally held unconsumed until the bounded source fix is released, verified, and the 4-attempt matrix completes genuinely.

## 1. Session, Lineage, and Lease Return Summary

- **Owner / Session / Model**: `eld-f2-implementer` · Antigravity CLI `2b6861af-031b-4e8b-9ce9-2a6d476f9da0` · **Gemini 4 Carbon (High)** (`High` effort)
- **Prior Public CLI Note**: The earlier Stage 1 CLI wrapper terminated with stream idle timeout (`ERROR`, wrapper exit `0`) *after* valid publication of `6faec9bf6eccc297a548523dbb52ae9262b25152`; that CLI wrapper run is not claimed as `SUCCESS`.
- **Coordinator Runtime Release Authority**: `717a768994bbbabf75b8ee96b3b1aadca1bc5df3` (`docs/kickoffs/WP-0006-eld-f2-author-runtime.md`, `docs/coordination/WP-0006/releases/author-runtime.json`)
- **Executing HEAD During Trial**: `6faec9bf6eccc297a548523dbb52ae9262b25152` (clean `git status --porcelain == ""` before and after trial)
- **Frozen Product Source Commit**: `0ad2fcd1e1c2cc918fe24db14d4b58ba347c0978` (`src`, `workers/local_ocr`, `web`, `tests`, `deploy` trees 100% unchanged)
- **Frozen Trial Plan & Helper Manifest**: [`helpers/plan-and-helper-freeze.json`](helpers/plan-and-helper-freeze.json) (`SHA-256: a69bd6e0ae2e8f721fe92fd8f1e4f3080b6c33b365e99fbd7625607fce22e9dc`, frozen at `2026-11-16T06:40:13Z` before starting services)
- **GPU Lease & Return**:
  - Lease ID: `WP-0006-author-runtime-20261116T062318Z` (`GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d`, NVIDIA GeForce RTX 5070 Ti)
  - Explicit Return Receipt: [`lease-return.json`](lease-return.json) (`returned_utc: 2026-11-16T06:41:18.798639+00:00`, `lease_state: "RETURNED_BY_OWNER_PENDING_COORDINATOR_ACK"`)
  - Model Attempts Used: `1` of `4` (`attempt-01a1e316-879e-737e-b222-cf9ebea58b09`, exited in `1.13s` prior to any `torch`/`transformers` import or GPU allocation)
  - Observed Process Identities (all verified exited via Win32 `OpenProcess` + `GetProcessTimes` + `GetExitCodeProcess`):
    - API Supervisor: `PID 21268`, `CreationTime FILETIME 134392848651100851` — terminated and exited (`127.0.0.1:5190` unbound)
    - Venv Launcher (`python.exe`): `PID 33412`, `CreationTime FILETIME 134392848670691163` — `launcher_alive_at_return: false`
    - Base Worker Child (`python.exe`, captured automatically via `QueryInformationJobObject` fallback): `PID 19996`, `CreationTime FILETIME 134392848670834387` — `worker_alive_at_return: false`
    - Owned PostgreSQL 18.7 Postmaster: `PID 15440`, `CreationTime FILETIME 134392848549629600` — cleanly stopped (`127.0.0.1:55434` unbound; `127.0.0.1:4210` unbound)
  - Active CUDA Compute Apps at Return: `[]` (`0` CUDA compute processes)
  - Post-Run Model Integrity ([`observations/model-after.json`](observations/model-after.json)): all `18/18` runtime objects + `README.md` notice verified unchanged against `model-files.json` (`0df07bc60abf6937c917040bced32afabd7e4d11bafc0bd99902abca610a81be`).
  - Preserved External Writable Root: `C:\Users\jackg\eLedgerCare-F2\WP-0006\author` (`374,331` bytes used vs `4 GiB` cap; preserved untouched on disk).

## 2. Concrete Root-Cause Diagnosis of Attempt #1 Failure

1. **What succeeded in Attempt #1 (`documentId = 01a1e316-866e-7b80-bc30-991e2ac465ef`, `attemptId = 01a1e316-879e-737e-b222-cf9ebea58b09`)**:
   - Real `POST /api/documents` admitted `SYN-WO-01-v1-raster300.pdf` (`372,258` B, `47b2df6a...`, `201 Created`).
   - Real `POST /api/documents/{id}/extraction` queued the job (`202 Accepted`), and `ExtractionSupervisorService` claimed Attempt #1 (`fencing_token = 1`).
   - `LocalPythonOcrWorkerRunner` created `C:\Users\jackg\eLedgerCare-F2\WP-0006\author\runs\attempt-01a1e316-879e-737e-b222-cf9ebea58b09`, materialized `input\document.pdf` read-only + [`attempt-1-failure/request.json`](attempt-1-failure/request.json), spawned `C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv\Scripts\python.exe` suspended inside `WindowsJobProcess` (`CREATE_SUSPENDED` + `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`), persisted `(launcher_pid=33412, launcher_create_filetime=134392848670691163)` before `ResumeThread`, and tracked the spawned venv child `(worker_pid=19996, worker_create_filetime=134392848670834387)` directly from the kernel Job Object!
2. **Exact Failure ([`attempt-1-failure/child.stderr.log`](attempt-1-failure/child.stderr.log))**:
   ```text
   Traceback (most recent call last):
     File "C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-f2-implementer\workers\local_ocr\run_worker.py", line 9, in <module>
       from local_ocr.worker import execute_request_file
   ModuleNotFoundError: No module named 'local_ocr'
   ```
3. **Why it happened and why Stage 1 CPU unit tests missed it**:
   - `LocalPythonOcrWorkerRunner.cs` line 113 invokes Python with `-I` (isolated mode):
     `["-I", "-B", "-X", "utf8", "-u", workerScript, "--request", requestPath]` with `workingDirectory = runDir` (`...\runs\attempt-<id>`).
   - In Python 3.11+, `-I` implies `-P` (`sys.flags.safe_path == True`), which **omits the script's parent directory (`workers/local_ocr`) from `sys.path[0]`**.
   - `workers/local_ocr/run_worker.py` line 9 executed `from local_ocr.worker import execute_request_file` without first inserting `str(Path(__file__).resolve().parent)` into `sys.path`.
   - In Stage 1, `workers/local_ocr/tests/test_worker_cpu.py` lines 14–16 explicitly inserted `WORKER_ROOT` into `sys.path` and called `execute_request_file(...)` in-process rather than spawning `python.exe -I run_worker.py` from an external working directory.
   - The `.NET` supervisor handled the child exit (`code 1`) fail-closed: persisted `status = 'failed'`, `failure_code = 'worker_missing_envelope'`, `canRetryExtraction = true`, and `0` rows in `extraction_results`.

## 3. Proposed Bounded Fix for Coordinator Reconciliation

Once `eld-coordinator` reconciles this runtime finding (and any concurrent `eld-next-reviewer` CPU/source review observations) into a new source release:
1. **`workers/local_ocr/run_worker.py`**: prepend `WORKER_ROOT = Path(__file__).resolve().parent` to `sys.path` (`if str(WORKER_ROOT) not in sys.path: sys.path.insert(0, str(WORKER_ROOT))`) before `from local_ocr.worker import execute_request_file` (note: this updates `ComputeWorkerSourceSha256`, which both `.NET` and Python compute dynamically from `workers/local_ocr`).
2. **`workers/local_ocr/tests/test_worker_cpu.py` & `WorkerEnvelopeAndJobObjectTests.cs`**: add a subprocess test invoking `python.exe -I -B -X utf8 -u workers/local_ocr/run_worker.py --request <temp_run_dir>/request.json` with `cwd = <temp_run_dir>` (outside `workers/local_ocr`) so `-I` isolated-mode package resolution and envelope writing are directly verified on CPU before re-running the 4-attempt GPU matrix.

## 4. Host / Desktop WDDM Confounders Disclosed

- Per [`preflight-before.json`](preflight-before.json) and [`observations/host-after.json`](observations/host-after.json), the RTX 5070 Ti (`16,303 MiB`) runs under a live Windows 11 desktop WDDM session (`22` desktop WDDM graphics processes holding `~1,352 MiB` baseline VRAM, `0` competing CUDA compute processes), while independent F2 CPU/PostgreSQL/Edge review (`eld-next-reviewer`) and WP-0007 CPU correction work share the 12-logical-CPU / 32-GiB-RAM host.

## 5. Original 11 Stage 1 Logs & Dual-Hash Reconciliation

All 11 original Stage 1 logs from `.scratch/stage1-decisive/logs/` are preserved byte-for-byte under [`stage1-original-logs/`](stage1-original-logs/) with scoped `-text -whitespace` in [`.gitattributes`](.gitattributes) so Git stores and checks out the exact Windows CRLF file bytes without newline conversion. [`stage1-log-hashes.json`](stage1-log-hashes.json) records both:
- `raw_file_sha256`: SHA-256 of the exact CRLF file bytes on disk (matching coordinator `stage1-publication-audit.json` `sha256`), and
- `lf_normalized_sha256`: SHA-256 of the LF-normalized text string (matching `stage1-checkpoint/decisive-summary.json` `log_sha256` and coordinator `published_sha256`).

Complete file-by-file byte sizes, SHA-256 digests, and Git-blob SHA-1s for this directory are recorded in [`inventory.json`](inventory.json).
