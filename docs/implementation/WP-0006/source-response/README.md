# WP-0006 F2 Consolidated Source/CPU Response Checkpoint (`eld-f2-implementer`)

> **Disposition**: **SINGLE CONSOLIDATED SOURCE RESPONSE COMPLETE FOR `F2-S1-01`, `F2-S1-02`, AND `F2-S1-03` AT FROZEN CANDIDATE `8a73b7a5dab51e3ccf803aceedded4929529dd35` (`83 / 83` FOCUSED CPU / CHILD-PROCESS / POSTGRESQL `18.7` CHECKS PASSED).**
>
> Ready for single-pass independent reconciliation by `eld-next-reviewer` (`101b19cf-3133-4ead-91cb-9ca6068e3e72`) and subsequent coordinator binding of a fresh finite GPU runtime release. Canonical `docs/agent-reports/eld-f2-implementer/WP-0006/003_2026-11-16_implementation_eld-f2-implementer.md` remains intentionally unpublished until genuine model/recovery execution completes.

## 1. Identity, Lineage, and CLI Disclosure

- **Author / Session / Model**: `eld-f2-implementer` · Antigravity CLI `2b6861af-031b-4e8b-9ce9-2a6d476f9da0` · **Gemini 4 Carbon (High)** (`High` effort)
- **Prior CLI Disclosures**: Both earlier Stage 1 (`6faec9b...`) and initial runtime-failure (`7280463...`) public CLI runs ended with stream idle timeout / network disconnect (`ERROR`) after valid Git publication; neither CLI wrapper run is claimed as `SUCCESS`.
- **Governing Coordinator Release**: `2c54927463b46a96a9b0c0c5d1012636fb4f961e` ([`docs/kickoffs/WP-0006-eld-f2-source-response.md`](../../../kickoffs/WP-0006-eld-f2-source-response.md), merged cleanly onto `feature/wp-0006-local-extraction` at `3d12dcdc7735b48053f2a56a95c4247c49168786` from author failure publication `7280463accdf0ff9fb3a218299193eeff2ec9c9e`)
- **Addressed Independent Findings**: `10193e2c904f99cfc23c97367f1e5d881b0630f2` (`docs/reviews/WP-0006/eld-next-reviewer/implementation/README.md`, helper `7cd33c003a35f16c5168085de1093666c21d8662`, evidence `b1103deddff414dfd4b4e8f10c2d2ce42480e742`)
- **Previous Product Source Commit**: `0ad2fcd1e1c2cc918fe24db14d4b58ba347c0978`
- **Intermediate Candidate (Retained Test-Harness Assertion Failure)**: `850d20063f09f0564a1008da20f09ff185fd0dfb` (`73/74` `.NET` tests passed; `1` test assertion in `LocalExtractionAcceptanceTests.cs:598` expected `canRetryExtraction == true` on an `ApiProcess` started with default `LocalOcr:Enabled=false` — exact failure log preserved at [`retained-failures/05-dotnet-test-solution-850d200.log`](retained-failures/05-dotnet-test-solution-850d200.log))
- **Frozen Corrected Source Candidate SHA**: **`8a73b7a5dab51e3ccf803aceedded4929529dd35`** (`12` changed files total relative to `0ad2fcd1e1c2cc918fe24db14d4b58ba347c0978`; `web`, `deploy`, `qualification`, `research`, `evaluation`, lockfiles, and all prior reports/evidence 100% unchanged)

## 2. Consolidated Disposition of `F2-S1-01` .. `F2-S1-03`

| Finding | Changed Paths | Resolution & Focused Regression Proof |
|---|---|---|
| **`F2-S1-01`** (Isolated `-I` entrypoint `ModuleNotFoundError: No module named 'local_ocr'`) | `workers/local_ocr/run_worker.py`, `workers/local_ocr/tests/test_worker_cpu.py`, `tests/ELedgerCare.Infrastructure.Tests/WorkerEnvelopeAndJobObjectTests.cs` | `run_worker.py` resolves `WORKER_ROOT = Path(__file__).resolve().parent` and prepends only `str(WORKER_ROOT)` to `sys.path` before importing `local_ocr.worker`, preserving full `-I` isolation (`cwd`/`runDir`, `PYTHONPATH`, and user-site stay excluded from `sys.path`). Verified by Python subprocess test (`-I -B -X utf8 -u` from external `runDir` containing a poison `local_ocr.py`) and C# `F2_S1_01_LocalPythonOcrWorkerRunner_executes_isolated_run_worker_from_external_venv_and_parses_envelope` (real `LocalPythonOcrWorkerRunner` + `WindowsJobProcess` + external stdlib venv writing `heartbeat.json` + structured `envelope.json` with `0` `ModuleNotFoundError` and `0` ML/GPU imports). |
| **`F2-S1-02`** (Transient/reparse-aware storage scan, guaranteed child kill before pipe drain, same-instance stale-`running` recovery) | `src/ELedgerCare.Infrastructure/Extraction/LocalPythonOcrWorkerRunner.cs`, `src/ELedgerCare.Application/Extraction/ExtractionAttemptCoordinator.cs`, `workers/local_ocr/local_ocr/env_guard.py`, `WorkerEnvelopeAndJobObjectTests.cs`, `LocalExtractionAcceptanceTests.cs` | (1) `CheckStorageBounds` (and Python `directory_size_bytes`) walks iteratively with bounded depth (`32`) and entry cap (`100,000`), tolerating concurrent NTFS `STATUS_DELETE_PENDING` / disappearing cache subdirectories while failing closed (`false`) on symlinks/junctions, persistent permission/I/O errors (verified via `icacls /deny *S-1-1-0:(RD)` and `mklink /J` + `1,200` iterations of 4-thread `%16` churn). (2) `ExecuteAttemptAsync`'s `finally` unconditionally calls `jobProcess.TerminateAllInJob(1)` and awaits bounded child exit whenever `exitCode is null` **before** bounded stdio pipe drain, verified with a live venv launcher + grandchild holding pipes open while `onHeartbeatAsync` throws. (3) `ExtractionAttemptCoordinator` tracks `activeExecutionGate` + `activeAttemptId` so `ReconcileAbandonedAttemptsAsync` protects any actively executing attempt on the same or another live supervisor, refuses to interrupt while launcher/worker PIDs remain alive, and reconciles an orphaned same-instance `running` row to terminal `interrupted` without an API restart and without auto-launching any retry. |
| **`F2-S1-03`** (PostgreSQL-safe diagnostic text & surrogate-safe truncation) | `src/ELedgerCare.Domain/Processing/DiagnosticTextSanitizer.cs`, `src/ELedgerCare.Domain/Processing/ExecutionAttempt.cs`, `src/ELedgerCare.Application/Extraction/WorkerEnvelopeValidator.cs`, `src/ELedgerCare.Infrastructure/Persistence/ExtractionStore.cs`, `ExtractionDomainAndParserTests.cs`, `LocalExtractionAcceptanceTests.cs` | `DiagnosticTextSanitizer` replaces `U+0000` (`\0`) and unpaired UTF-16 surrogates with `U+FFFD`, prevents UTF-16 surrogate-pair splits across `MaxDiagnosticOutputChars` (`65,536`) / `MaxFailureDetailLength` (`500`), trims incomplete trailing multi-byte UTF-8 sequences on raw byte previews, and sanitizes `\u0000` inside `diagnostic_metadata_json` (`jsonb`), while keeping accepted `extraction_results.raw_output_bytes` (`bytea`) and `original_artifacts.bytes` (`bytea`) exact and unmodified. Verified against real PostgreSQL `18.7` (`eledgercare_app`) and HTTP `GET /api/documents/{id}/extraction`. |

## 3. Changed File Inventory (`0ad2fcd1e1c2cc918fe24db14d4b58ba347c0978..8a73b7a5dab51e3ccf803aceedded4929529dd35` Product/Test Scope)

1. `workers/local_ocr/run_worker.py` (modified — `F2-S1-01`)
2. `workers/local_ocr/local_ocr/env_guard.py` (modified — `F2-S1-02`)
3. `src/ELedgerCare.Domain/Processing/DiagnosticTextSanitizer.cs` (added — `F2-S1-03`)
4. `src/ELedgerCare.Domain/Processing/ExecutionAttempt.cs` (modified — `F2-S1-03`)
5. `src/ELedgerCare.Application/Extraction/WorkerEnvelopeValidator.cs` (modified — `F2-S1-03`)
6. `src/ELedgerCare.Application/Extraction/ExtractionAttemptCoordinator.cs` (modified — `F2-S1-02`)
7. `src/ELedgerCare.Infrastructure/Extraction/LocalPythonOcrWorkerRunner.cs` (modified — `F2-S1-02`)
8. `src/ELedgerCare.Infrastructure/Persistence/ExtractionStore.cs` (modified — `F2-S1-03`)
9. `workers/local_ocr/tests/test_worker_cpu.py` (modified — `F2-S1-01`, `F2-S1-02`)
10. `tests/ELedgerCare.Domain.Tests/ExtractionDomainAndParserTests.cs` (modified — `F2-S1-03`)
11. `tests/ELedgerCare.Infrastructure.Tests/WorkerEnvelopeAndJobObjectTests.cs` (modified — `F2-S1-01`, `F2-S1-02`)
12. `tests/ELedgerCare.Acceptance.Tests/LocalExtractionAcceptanceTests.cs` (modified — `F2-S1-02`, `F2-S1-03`)

## 4. Updated Worker Source Digest & Unchanged Pinned Identities (`8a73b7a5dab51e3ccf803aceedded4929529dd35`)

- **New `worker_source_sha256` (`ComputeWorkerSourceSha256`)**: **`c1c324c36e27f57c3c4ac4a1462984fbe586ad43ab82af3a2883bb7eac4c0d54`** (updated from `01ad2fa1d6dcf8643ecb5801a934b37bae4630faca2f70959b4a85cc4480eb01` due to `run_worker.py` and `env_guard.py`; verified identical between C# and Python)
- **Unchanged `model_manifest_sha256`**: `0df07bc60abf6937c917040bced32afabd7e4d11bafc0bd99902abca610a81be`
- **Unchanged `dependency_lock_sha256`**: `582071bf20eaca1836c3d1cef21d31cbdaa1e1407184033a918a40612c128111`
- **Unchanged `worker_config_sha256` (`1p` / `2p` / `3p`)**:
  - `1p`: `579aad63a9893a58466baf005ea63f87e92540d4c1f71f6b3c399e8b1e6b35ff`
  - `2p`: `e4df504ddb51dcc8fb137e97f5af97c735252374738b1a1754a88b16a05de5df`
  - `3p`: `ac90459ca4011b5859cfdd0b224d5ea247489b7c01775118736df7c1c9819e86`
- **Unchanged Git Tree OIDs**:
  - `web`: `f0877a006922818bf731d5f87603a368ed782487`
  - `deploy`: `dade6a38e165b5cc2ba81ba895bd9d3c572d26f2`

## 5. Decisive Post-Freeze Verification Results (`8a73b7a5dab51e3ccf803aceedded4929529dd35`)

Executed sequentially on clean `HEAD = 8a73b7a5dab51e3ccf803aceedded4929529dd35` via [`helpers/run_source_response_decisive.py`](helpers/run_source_response_decisive.py) using owned PostgreSQL `18.7` on `127.0.0.1:55434` (`postmaster PID 27824`, `FILETIME 134393134479381670`, cleanly stopped afterward; ports `5190`/`4210`/`55434` verified `false` before and after; zero GPU/model imports; external `C:\Users\jackg\eLedgerCare-F2\WP-0006\author` verified unchanged at `4` files / `374,331` bytes). Exact raw log files (preserved byte-for-byte via [`.gitattributes`](.gitattributes)) and dual raw/LF SHA-256s are recorded in [`decisive-summary.json`](decisive-summary.json) and [`inventory.json`](inventory.json).

| Step | Command | Result | Duration |
|---|---|---|---|
| `01` | `dotnet restore ELedgerCare.slnx --locked-mode` | `EXIT 0` | `1,890 ms` |
| `02` | `dotnet build ELedgerCare.slnx -c Release --no-restore` | `EXIT 0` (`0` warnings, `0` errors) | `8,838 ms` |
| `03` | `dotnet publish src/ELedgerCare.Api/ELedgerCare.Api.csproj -c Release --no-restore` | `EXIT 0` (`0` warnings, `0` errors) | `1,897 ms` |
| `04` | `python -B -m unittest discover -s workers/local_ocr/tests -p "test_*.py" -v` | `EXIT 0` (**`9 / 9` passed**) | `848 ms` |
| `05` | `dotnet test --solution ELedgerCare.slnx -c Release --no-build` | `EXIT 0` (**`74 / 74` passed**: `12` Domain, `42` Infra, `20` PG Acceptance; `0` failed/skipped) | `103,673 ms` |

- **Total Focused Automated Checks Passed on `8a73b7a5dab51e3ccf803aceedded4929529dd35`**: **`83 / 83` (`0` failed, `0` skipped)**.
- **Checks Intentionally Not Repeated**: Angular build / Playwright browser E2E (`web` tree `f0877a00...` is byte-identical to `0ad2fcd1...` where `10/10` Edge E2E tests passed in both author and independent review runs); GPU model execution (held pending reviewer source reconciliation and new coordinator runtime lease).
