# WP-0006 F2 Stage 1 Resource and Process Ownership Ledger (`eld-f2-implementer`)

- **Owner / Session**: `eld-f2-implementer` — **Gemini 4 Carbon (High)** (`High` effort), conversation `2b6861af-031b-4e8b-9ce9-2a6d476f9da0`
- **Repository / Branch / Worktree**: `https://github.com/jackgumpe/eledgercare` · `feature/wp-0006-local-extraction` · `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-f2-implementer`
- **Governing Implementation Release**: `d106db76de6dc8d9b52770d405ca95300b6dacd6` (`docs/kickoffs/WP-0006-eld-f2-implementation.md` + `docs/coordination/WP-0006/design-acceptance.md`)

## 1. Owned Loopback Ports (Stage 1)

| Service | Loopback Binding | Default / Override | Lifecycle |
|---|---|---|---|
| `ELedgerCare.Api` | `127.0.0.1:5190` (or ephemeral `0` in xUnit `ApiProcess`) | `Api:Port` (`5190` default; `-ApiPort` / `ELEDGERCARE_API_PORT`) | Started per smoke/E2E test run; verified unbound before start and terminated by exact `(PID, StartTimeUtc)` on completion |
| Angular Dev Server (`ng serve`) | `127.0.0.1:4210` | `ELEDGERCARE_UI_PORT` (`4210` default; `-UiPort`) | Started/stopped by Playwright `webServer` inside `deploy/dev/smoke/run-browser-checks.ps1` |
| Worktree PostgreSQL 18.7 | `127.0.0.1:55434` | `.local/secrets/pg-local.json` (`setup-cluster.ps1 -Port 55434`) | Worktree-owned local cluster (`unix_socket_directories=''`, `scram-sha-256`, `fsync=on`, `full_page_writes=on`, `synchronous_commit=on`) |

## 2. Owned Filesystem & Database Boundaries

- **Worktree-local state (`.local/`, gitignored)**:
  - `.local/tools/pgsql-18.7-1`: verified `1,597`-file PostgreSQL 18.7 server subset (`subset_sha = 47c3deb9c917f79c353b3683b2c2611ee975285ea06226c8f72444c96ce9051f`).
  - `.local/postgres-data` & `.local/logs/postgres.log`: owned cluster data/log directory on `127.0.0.1:55434`.
  - `.local/secrets/pg-local.json`: generated random SCRAM-SHA-256 credentials for `eledgercare_admin`, `eledgercare_migrator`, and `eledgercare_app` (never committed or printed).
  - `.local/nuget` & `.local/npm-cache`: copied read-only from existing eLedgerCare worktree caches; zero old `.local/postgres-data` or `.local/secrets` accessed or mutated.
- **Databases on `127.0.0.1:55434`**:
  - `eledgercare_product_dev` (development / demo smoke database)
  - `eledgercare_e2e` (Playwright E2E database)
  - `eledgercare_stage1_<shortsha>` (decisive post-freeze migration/grant verification database)
  - `eledgercare_test_tpl_<runId>` / `eledgercare_test_<runId>_*` / `eledgercare_f1_fwd_*` (ephemeral xUnit acceptance databases, dropped with `DROP DATABASE ... WITH (FORCE)` on disposal)

## 3. Child Process Lifetime & Non-Access Enforcement

- **Race-Free Child Containment (`WindowsJobProcess`)**:
  - Spawns worker processes via Win32 `CreateProcessW` with `CREATE_SUSPENDED` and `PROC_THREAD_ATTRIBUTE_HANDLE_LIST` (`[NUL, stdoutPipe, stderrPipe]` only — job handle and server sockets are never inherited).
  - Assigns the suspended child to a non-inheritable Job Object (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, zero breakaway flags) and persists `(launcher_pid, launcher_create_filetime)` in `eledgercare.execution_attempts` **before** `ResumeThread`.
  - Queries `QueryInformationJobObject(JobObjectBasicProcessIdList)` + `GetProcessTimes` (`CreationTime` FILETIME) to track descendants and guarantee kernel termination if the supervisor exits or crashes.
- **Stage 1 Strict Non-Access**:
  - `LocalOcr:Enabled` defaults to `false` in `src/ELedgerCare.Api/appsettings.json`.
  - Zero GPU lease, zero `torch`/`transformers` imports, zero execution of `C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv\Scripts\python.exe`, and `C:\Users\jackg\eLedgerCare-F2\WP-0006` is **not created** in Stage 1.
  - Zero reads of holdout families (`F03`, `F05`, `F06`, `F08`).
  - Zero runtime references or calls from `src/`, `web/`, `deploy/dev/`, or `workers/local_ocr/` into `qualification/`, `research/`, `evaluation/`, or `git.exe`.

## 4. Stage 2 Coordinator Runtime Release Requirements

To execute the finite Stage 2 real-GPU acceptance and recovery run against the frozen Stage 1 candidate (without source changes), `eld-coordinator` binds:
1. Exclusive GPU lease (`CUDA_DEVICE_ORDER=PCI_BUS_ID` + exact `GPU-...` UUID via `LocalOcr__LeasedGpuUuid`) after confirming `eld-baseline` / other GPU leases are idle.
2. Read-only Q0 root (`LocalOcr__ReadOnlyQ0Root=C:\Users\jackg\eLedgerCare-Q0\WP-0005`) verified unchanged against `workers/local_ocr/manifests/model-files.json` and `dependency-lock.json`.
3. Authorized writable F2 runtime root (`LocalOcr__WritableRuntimeRoot=C:\Users\jackg\eLedgerCare-F2\WP-0006`, `<= 4 GiB` cap, `>= 20 GiB` free-space floor) and `LocalOcr__Enabled=true` for the bounded Stage 2 acceptance run only.
4. Finite approved dev-only acceptance matrix: `SYN-WO-01-v1-raster300.pdf` (`1` page), `SYN-MP-01-v0-clean.pdf` (`3` pages), owned interruption + explicit retry recovery, full API + PostgreSQL restart reopen, and `LocalOcr__Enabled=false` saved-result reopen.
