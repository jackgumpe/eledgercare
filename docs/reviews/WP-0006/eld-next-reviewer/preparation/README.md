# WP-0006 F2 Independent Reviewer Resource Preparation Checkpoint

- **Owner / Session:** `eld-next-reviewer` — continued independent Google DeepMind Gemini 4 Carbon (High) conversation `101b19cf-3133-4ead-91cb-9ca6068e3e72` (high effort; owns `WP-0006` F2 review only; `WP-0007` `/003` and `/005` reassigned to `eld-baseline-reviewer` at [AGENTS.md](../../../../AGENTS.md) L64)
- **Branch / Worktree:** `review/wp-0006-0007-next-tracks` (`C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-next-reviewer`)
- **Phase Scope:** **Isolated resource preparation checkpoint only** under [WP-0006-eld-next-reviewer-preparation.md](../../../kickoffs/WP-0006-eld-next-reviewer-preparation.md) (merged coordinator release `9ae311e3d0f4e4a75a596ddb538a802cd92869eb` at `7903bf509d54d8767fdb21ab4b11f01bb573e939` atop accepted `/002` `e2452e1ab3d8937868c07ffb30ce430715b5be78`). **This is NOT canonical `WP-0006 /004` and claims zero F2 feature/migration/GPU acceptance.**
- **Frozen Helper / Receipt:** [verify_preparation.py](verify_preparation.py) frozen at `91322f5f73581a3327ab180d9b3828fc22fbc666` (SHA-256 `70b2d7aa9d561bf2b462a48d10259637abfbd2fe23b7addf64b0ccad7c5d5b06`) prior to decisive execution -> [preparation-receipt.json](preparation-receipt.json) (`11/11` assertions passed, zero secret values printed or committed).

## 1. Binary, Cache, and Toolchain Provenance

| Resource | Verified Identity & Provenance | Owned Retained Path |
| --- | --- | --- |
| PostgreSQL `18.7` server subset | Copied read-only from accepted `eLedgerCare` reviewer/implementer `.local\tools` and verified byte-for-byte: `1,597` files, `151,078,582` B, `0` reparse points, `0` SHA-256/CRC-32/size mismatches; `subset_manifest_sha256` `47c3deb9c917f79c353b3683b2c2611ee975285ea06226c8f72444c96ce9051f`, EDB archive `central_directory_sha256` `3132ca63b424f7ec371eabe50753ad7cd036278d942a6ea465547b17bf90a149` (`389,515,503` B); `postgres.exe`, `pg_ctl.exe`, `initdb.exe`, `psql.exe` all `(PostgreSQL) 18.7` and Authenticode `Valid` (`CN=EnterpriseDB Corporation`). | `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-next-reviewer\.local\tools\pgsql-18.7-1` + `pgsql-18.7-1.subset-manifest.json` |
| `.NET` SDK, runtimes, & locked NuGet cache | `.NET SDK 10.0.403` (`rollForward=disable`), shared runtimes `10.0.9` & `10.0.14`, local `dotnet-ef 10.0.15` (`dotnet tool restore` + `dotnet restore ELedgerCare.slnx --locked-mode`); `126/126` entries (`53` unique packages) across all `7` `packages.lock.json` files verified in owned cache with `0` `.nupkg.metadata` `contentHash` mismatches and `0` lockfile edits. | `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-next-reviewer\.local\nuget\packages` & `.local\dotnet-home` |
| Node / npm / Angular / Playwright / Edge | `Node.js v24.18.0`, `npm 11.16.0`, `pwsh 7.7.0`; `npm ci --prefer-offline` (`PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`) restored `@angular/cli 22.2.7` and `@playwright/test 1.65.1` with `0` lockfile edits; local Microsoft Edge verified at `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` (`157.0.4341.60`, no browser download). | `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-next-reviewer\.local\npm-cache` & `web\node_modules` |

## 2. Owned PostgreSQL `18.7` Cluster Bootstrap & Decisive Start/Query/Stop Observation (`127.0.0.1:55435`)

- **Independent Cluster Initialization (`setup-cluster.ps1 -Port 55435`):**
  - Created fresh `.local\secrets\pg-local.json` (`host=127.0.0.1`, `port=55435`, `devDatabase=eledgercare_product_dev`, three distinct newly generated >=32-char secrets; zero old cluster/credential access; zero secret values emitted) and initialized `.local\postgres-data` (`PG_VERSION=18`, `UTF8`, `locale=C`, `data_checksums=on`).
  - Bootstrap run started `postmaster` PID `26692` (`2026-11-16T04:57:06.1182968Z`), created roles, and stopped cleanly via `stop-cluster.ps1`.
- **Decisive Frozen-Helper Cycle (`verify_preparation.py` @ `91322f5f73581a3327ab180d9b3828fc22fbc666`):**
  - **Pre-start port check:** Loopback ports `5290`, `4310`, and `55435` all confirmed unbound (`0` listeners).
  - **Start & bind check (`start-cluster.ps1`):** Started owned `postgres` `postmaster` PID **`3096`** at **`2026-11-16T04:59:22.7119110Z`**, listening solely on `127.0.0.1:55435` (`owningPid=3096`; `5290` and `4310` unbound).
  - **Catalog & durability queries (`psql.exe`):** `server_version=18.7`, `listen_addresses=127.0.0.1`, `port=55435`, `password_encryption=scram-sha-256`, `fsync=on`, `full_page_writes=on`, `synchronous_commit=on`, `wal_level=replica`, `data_checksums=on`, `default_transaction_isolation=read committed`.
  - **Role & authentication verification (role names only, secrets redacted):**
    - `eledgercare_admin`: `can_login=true`, `superuser=true`, `create_db=true`, `create_role=true`, `inherit=true`, `SCRAM-SHA-256` verifier present.
    - `eledgercare_migrator`: `can_login=true`, `superuser=false`, `create_db=false`, `create_role=false`, `inherit=false`, `SCRAM-SHA-256` verifier present; loopback login probe succeeded (`127.0.0.1:55435`).
    - `eledgercare_app`: `can_login=true`, `superuser=false`, `create_db=false`, `create_role=false`, `inherit=false`, `SCRAM-SHA-256` verifier present; loopback login probe succeeded (`127.0.0.1:55435`).
  - **Clean stop & retention (`stop-cluster.ps1`):** Exit `0`; `pg_ctl status` exit `3` (not running); `postmaster.pid` absent; `(PID 3096, 2026-11-16T04:59:22.7119110Z)` confirmed terminated; ports `5290`, `4310`, and `55435` all unbound; `.local\postgres-data` and `.local\secrets\pg-local.json` retained on disk.

## 3. Boundaries Preserved & Pending Exact-Candidate Checks (`WP-0006 /004`)

- **Not performed in this phase (by design):**
  - Zero tracked source, migration, or lockfile edits (`git status --porcelain=v1` clean); immutable Phase 1 `/002` (`e2452e1ab3d8937868c07ffb30ce430715b5be78`) and `design/` files untouched.
  - Non-template database list is `["postgres"]` only; `eledgercare_product_dev`, `F1 -> F2` forward migrations, `grant-runtime.sql`, `.NET` test suites, and Playwright suites were **not** run against old pre-F2 application code.
  - External F2 reviewer runtime root `C:\Users\jackg\eLedgerCare-F2\WP-0006\reviewer` was **not** created (`exists=false`); zero Python model imports, GPU activity, or holdout (`F03,F05,F06,F08`) reads occurred.
- **Pending after `eld-coordinator` binds frozen `F2` candidate(s) and GPU release:**
  1. Independent source audit of frozen `eld-f2-implementer` candidate (`F2-01`..`07`, `F2-KR-01`, `F2-BIC-01`..`04`, race-free Windows Job Object containment).
  2. Independent reproduction of `F1 -> F2` forward migration, least-privilege `eledgercare_app` grants, `.NET` domain/infrastructure/acceptance suites, and Edge browser checks on isolated reviewer endpoints `5290 / 4310 / 55435`.
  3. Under a separate exclusive reviewer GPU lease and bound `C:\Users\jackg\eLedgerCare-F2\WP-0006\reviewer` runtime root, independent reproduction of real `SYN-WO-01-v1-raster300.pdf` (1p raster) and `SYN-MP-01-v0-clean.pdf` (3p ordering) extraction, forced supervisor/worker kill & explicit retry, API + PostgreSQL restart persistence, and disabled-worker reopening, followed by canonical `WP-0006 /004`.
