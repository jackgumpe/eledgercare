# WP-0003 / 001: Reproducible scaffold and F1 durable intake implementation

- Report path: `docs/agent-reports/eld-implementer/WP-0003/001_2026-11-14_implementation_eld-implementer.md`
- Sequence reservation: coordinator `INDEX.md` at `b1e4402f488fcd8838d9ebfa12fbbf306b8c7264`, row `WP-0003 / 001`; released by kickoff `docs/kickoffs/WP-0003-eld-implementer.md` and coordinator disposition `WP-0002 / 005` at the same revision (these supersede the HELD wording at the worker base)
- Category: implementation
- Author / agent ID: `eld-implementer`
- Actual model / effort: Claude Opus 5.5, high effort, as selected in the Antigravity session's model setting for this new conversation `5ac4336a-24ed-4139-871a-18ef583b7691`. The backend checkpoint identifier is not exposed to me. I did not resume or read any Carbon conversation.
- Execution environment: Antigravity CLI agent on Windows x64. Windows PowerShell 5.1.26100 (tool shell) and pwsh 7.7.0 (scripts). .NET SDK 10.0.403 with runtimes 10.0.9/10.0.14. Node 24.18.0 / npm 11.16.0. Git 2.55.0.windows.1. Python 3.12.10 (standard library only, used by the PostgreSQL fetch script). PostgreSQL 18.7 (EDB Windows x64 binaries, worktree-owned). Microsoft Edge 157.0.4341.46 (Playwright `msedge` channel).
- Published by: the author, `eld-implementer`, using the existing configured Git identity (`jackgumpe`), unchanged
- Timestamp: 2026-11-14T19:22:00Z
- Repository / branch: private https://github.com/jackgumpe/eledgercare, branch `feature/wp-0003-durable-intake`, worktree `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-implementer`
- Base revision: `bce84931fef5cf2a8fa3652095dbea2973a19aef` (the accepted design candidate; design blob `18476f0c0f1fa7b0f1db99d4404a6ac30085c572`)
- Deliverable revision (frozen code candidate): `e3117ec2aa11a78359a754cfe52ef3ece6c1733f`
  - Intermediate milestone pushed early: `c5103788da33303f522e10a484cec5aaee5325ae` (scaffold and F1, not frozen; it is an ancestor of the candidate)
  - Evidence commit: `6691aaab848263e2f8326a491a9647d239119865` (only `docs/evidence/WP-0003/eld-implementer/**`, no source)
- Previous report: none in WP-0003
- Related or reviewed reports: WP-0002 / 004, Carbon closure, at `6722ff0eb8fdfa3b4fd17a9d0024c90c7bc98449` (evidence `04b08ed3a04daa17f32624878bd5051153b3b801`). WP-0002 / 005, coordinator release, read from `b1e4402f488fcd8838d9ebfa12fbbf306b8c7264`.
- Status: ready-for-review
- Next owner: `eld-reviewer` (Carbon), WP-0003 / 002, on candidate `e3117ec2aa11a78359a754cfe52ef3ece6c1733f` in a separate worktree and cluster. The coordinator binds that review.

## Summary

This is author verification, not independent acceptance.

I built the single production solution `ELedgerCare.slnx`, which contains Domain, Application, Infrastructure, Api and three test projects. I also built:

- an Angular 22 F1 screen
- explicit EF Core migrations
- a worktree-owned PostgreSQL 18.7 setup with least-privilege roles

Together these implement the accepted F1 behaviour:

- Raw-PDF intake with a bounded body.
- Strict PdfPig admission.
- One atomic bytea transaction.
- A unique idempotency key with retry, conflict and race handling.
- Stable server-generated document and job references.
- An honest `awaiting_extraction` status, plus key reconciliation and exact original download.

There is no OCR, no mock and no research or evaluation reference in the product code.

Decisive author checks ran on the frozen candidate after a clean rebuild with locked restores:

| Check | Result |
| --- | --- |
| .NET tests | 52 discovered / 52 passed / 0 failed / 0 skipped |
| Browser checks (real Edge) | 6 / 6 passed |
| Fresh-database explicit migration | passed |
| API publish-contents inspection | passed |
| Demo receipt (API restart plus PostgreSQL fast restart) | all values match |

All BIC-01..06 and DI-01..07 author evidence is produced. DI-08, independent reproduction, belongs to Carbon.

Two items need the reviewer's explicit attention:

1. **Admission addition beyond the literal design.** I added a narrow `startxref`-target precondition. PdfPig strict mode was observed admitting a file with a broken `startxref`.
2. **Known limitation.** Wrong per-object xref offsets behind a valid `startxref` are still recovered and admitted by PdfPig. I did not write a custom xref validator.

## Objective and acceptance criteria

The objective comes from the kickoff:

- Build the one production .NET solution, the Angular shell, explicit PostgreSQL setup and migrations, and the reviewed F1 behaviour.
- Freeze reproducible dependency and setup choices.
- Implement durable intake.
- Fulfil DI-01..DI-08 author-side evidence and carry forward BIC-01..06.
- Publish evidence and this report on the owned branch.

Completion conditions: every criterion below has executed evidence on the frozen candidate, every limitation is stated, and remote publication is verified.

## Change inventory

The base `bce84931â€¦` to the deliverable `e3117ec2â€¦` touches 94 paths (92 added, 2 modified, 0 deleted or renamed). `git diff --check` exits 0. Zero paths fall under AGENTS.md, START_HERE.md, INDEX.md, CURRENT.md, docs/design, docs/agent-reports, docs/kickoffs, docs/coordination or research.

| Action | Exact path(s) | What and why | Relevant symbols |
| --- | --- | --- | --- |
| Added | `ELedgerCare.slnx` | The one production solution: 4 src and 3 test projects | â€” |
| Added | `global.json` | SDK 10.0.403, `rollForward: disable`, `allowPrerelease: false`, `test.runner: Microsoft.Testing.Platform` | BIC-04 |
| Added | `Directory.Build.props` | net10.0, nullable, warnings as errors, `RestorePackagesWithLockFile`, invariant globalization | â€” |
| Added | `Directory.Packages.props` | Central exact pins: EF Core/Relational/Design 10.0.15, Npgsql EF 10.0.3, PdfPig 0.1.16, xunit.v3 4.0.3 | â€” |
| Added | `NuGet.Config` | nuget.org only, with source mapping. `globalPackagesFolder=.local/nuget/packages`, so restores stay in the worktree | â€” |
| Added | `.config/dotnet-tools.json` | Project-local `dotnet-ef` 10.0.15 | â€” |
| Added | `.editorconfig` | Formatting; marks generated migrations | â€” |
| Modified | `.gitignore` | Narrow additions: `playwright-report/`, `test-results/`, `blob-report/`, `coverage/`, `out-tsc/` | BIC-05 |
| Modified | `README.md` | Appended a local setup section. The coordinator's seed paragraphs are unchanged | â€” |
| Added | `src/ELedgerCare.Domain/{ELedgerCare.Domain.csproj, Documents/Document.cs, Documents/OriginalArtifact.cs, Intake/AdmissionCeilings.cs, Processing/ProcessingJob.cs, Processing/ProcessingStatus.cs, packages.lock.json}` | The aggregate is created atomically by `Document.Submit`: immutable original with SHA-256 and length, a single job, status `awaiting_extraction` only. Ceilings: 10,485,760 bytes and 50 pages. No outward references | `Document.Submit`, `ProcessingStatusNames` |
| Added | `src/ELedgerCare.Application/{ELedgerCare.Application.csproj, Intake/IIntakeStore.cs, Intake/IPdfAdmission.cs, Intake/IntakeLimits.cs, Intake/SubmitDocument.cs, packages.lock.json}` | Design steps 3â€“5: compare an existing key by length, digest, then exact bytes (200/409); admit; insert; on a lost race compare with the winner. Startup-validated limits | `SubmitDocument.ExecuteAsync`, `SubmissionOutcome` |
| Added | `src/ELedgerCare.Infrastructure/{ELedgerCare.Infrastructure.csproj, InfrastructureServices.cs, packages.lock.json}` | Composition of EF/Npgsql and PdfPig. Design package is `PrivateAssets=all`. `InternalsVisibleTo` names the infrastructure test assembly | â€” |
| Added | `src/ELedgerCare.Infrastructure/Persistence/{ELedgerCareDbContext.cs, IntakeStore.cs, DesignTimeDbContextFactory.cs}` | Schema `eledgercare`. Check constraints mirror domain ceilings. FKs are `Restrict`. Unique index `ux_documents_idempotency_key`. One Read Committed transaction with `SET LOCAL synchronous_commit = on`. Only that unique violation maps to `IdempotencyKeyTaken`. Metadata projection never selects bytes | `IntakeStore.InsertAsync`, `ProjectMetadata` |
| Added | `src/ELedgerCare.Infrastructure/Persistence/Migrations/{20261114182147_InitialDurableIntake.cs, .Designer.cs, ELedgerCareDbContextModelSnapshot.cs}` | Generated by `dotnet tool run dotnet-ef migrations add`. The snapshot file was moved from a tool-generated namespace path to this folder; its content is unchanged | â€” |
| Added | `src/ELedgerCare.Infrastructure/Pdf/PdfPigAdmission.cs` | Header 1.0â€“1.7, then `%%EOF`, then the `startxref` target, then strict Open, then `IsEncrypted`, then the page count, then `GetPage(1..N)`. No text, letters, rendering, OCR or network access | `Evaluate`, `StartXrefAddressesCrossReference` |
| Added | `src/ELedgerCare.Api/{ELedgerCare.Api.csproj, Program.cs, DocumentEndpoints.cs, BoundedBody.cs, IntakeOptions.cs, LocalOnlyGuard.cs, Problems.cs, SubmissionReceiptResponse.cs, UnhandledExceptionHandler.cs, appsettings.json, packages.lock.json}` | Listens on loopback 127.0.0.1 only. Kestrel body cap equals the effective limit. Two-slot POST concurrency limiter with no queue returns 429. Step-1 validation runs before reading the body. Bounded buffer. 413 mapping for `BadHttpRequestException`. ProblemDetails with a `code`. Host and Origin loopback guard. `nosniff`. Server-generated download name | `SubmitAsync`, `TryParseCanonicalUuid` |
| Added | `deploy/dev/postgres/{fetch_server_subset.py, setup-cluster.ps1, start-cluster.ps1, stop-cluster.ps1}` | Fetches a verified subset of the official EDB archive. Owned initdb, scram-sha-256, 127.0.0.1:55432, durability settings, roles. Refuses a port bound by another process | BIC-06 |
| Added | `deploy/dev/database/{prepare-database.ps1, grant-runtime.sql}` | Explicit `dotnet-ef database update` with the migrator role. Runtime grants SELECT and INSERT on the three tables only. Prints the privilege matrix | BIC-06 |
| Added | `tests/ELedgerCare.Domain.Tests/{csproj, DocumentSubmissionTests.cs, packages.lock.json}` | 7 domain tests | â€” |
| Added | `tests/ELedgerCare.Infrastructure.Tests/{csproj, PdfPigAdmissionTests.cs, PersistenceMappingTests.cs, SyntheticFixtureTests.cs, packages.lock.json}` | 26 real-PdfPig profile tests, 3 tests on generated SQL and mapping, 1 fixture-determinism test | BIC-01, DI-07 |
| Added | `tests/ELedgerCare.Acceptance.Tests/{csproj, DurableIntakeTests.cs, Harness/ApiProcess.cs, Harness/ClusterSettings.cs, Harness/Evidence.cs, Harness/LockObserver.cs, Harness/PostgresFixture.cs, Harness/RawHttp.cs, packages.lock.json}` | 15 tests on real PostgreSQL with the real API OS process. They fail rather than skip when the cluster is missing | DI-01..07, BIC-02/03 |
| Added | `tests/Shared/SyntheticPdf.cs` | Deterministic source-first PDF generator, including RC4 R2 encryption and single-defect variants | â€” |
| Added | `tests/fixtures/{F1-SWO-001.pdf, README.md, .gitattributes}` | Fixture: 887 bytes, SHA-256 `875a2d8câ€¦97cb`, with provenance. `*.pdf binary` stops `core.autocrlf=true` from rewriting the fixture on checkout | â€” |
| Added | `web/{package.json, package-lock.json, .npmrc, angular.json, tsconfig.json, tsconfig.app.json, proxy.conf.json, src/index.html, src/main.ts, src/styles.css, src/app/app.ts, src/app/app.config.ts, src/app/app.routes.ts, src/app/intake/intake-page.ts, src/app/intake/document-page.ts, src/app/intake/submission-api.ts, src/app/intake/receipt.ts}` | Angular 22 zoneless screen: select and submit, receipt, download, document route, reopen. sessionStorage pending key, uncertain/busy/rejected states, explicit New submission | `IntakePage.failed`, `SubmissionApi.pendingOrNew` |
| Added | `web/{playwright.config.ts, e2e/intake.spec.ts, e2e/owned-api.ts}` | 6 browser checks. The spec owns the API child process so that DI-04 can kill and restart exactly that process | BIC-05 |
| Added | `evaluation/product-smoke/{run-browser-checks.ps1, run-demo-smoke.ps1}` | Fresh e2e database plus Playwright runner. Demo restart receipt on the dev database | â€” |
| Added | `docs/product/F1-durable-intake-implementation.md` | Map from code to the design; no design changes | â€” |
| Added | `workers/ocr/README.md` | Boundary README only: no code and no mock | â€” |

**Committed afterwards in evidence commit `6691aaabâ€¦`** (21 files, no source):

- `docs/evidence/WP-0003/eld-implementer/README.md`
- `decisive-run.ps1`
- `postgresql-binaries.md`
- `postgresql-18.7-1-server-subset.sha256`
- `decisive-run/{01..10 step logs, steps.txt, summary.json, acceptance-evidence.jsonl, browser-evidence.json, playwright-results.json, demo-receipt.json, postgres-log-excerpt.txt}`

**This report** is committed separately afterwards.

### External and installation effects (separate from Git)

| Target | Effect | Persistence |
| --- | --- | --- |
| `.local/nuget/packages` (ignored) | NuGet restore of the locked packages and dotnet-ef 10.0.15 | Kept |
| `web/node_modules`, `.local/npm-cache` (ignored) | `npm install`, then `npm ci`: 364 locked packages. npm 11's allow-scripts policy did **not** run 4 install scripts (`esbuild`, `lmdb`, `@parcel/watcher`, `msgpackr-extract`). The build uses the prebuilt optional binary `@esbuild/win32-x64` 0.28.2. I approved no scripts | Kept |
| `.local/tools/pgsql-18.7-1` and `.subset-manifest.json` (ignored) | 1,597 files (151 MB) of the official archive. An earlier partial download through `Invoke-WebRequest` (~25 MB, aborted for speed) was deleted | Kept |
| `.local/postgres-data`, `.local/logs/postgres.log`, `.local/secrets/pg-local.json` (ignored) | Owned cluster and generated credentials. Roles `eledgercare_admin`, `eledgercare_migrator`, `eledgercare_app`. Databases `eledgercare_product_dev` (holds synthetic smoke submissions), `eledgercare_e2e` and `eledgercare_candidate_e3117ec`. All per-test databases and templates were dropped by the harness | Kept. **Cluster stopped** at 2026-11-14T19:19:00Z with `pg_ctl stop -m fast`. Restart with `deploy/dev/postgres/start-cluster.ps1` |
| Processes | Postmasters started and stopped only on my data directory; last PID 25552. API processes on ephemeral loopback ports and on 5180, each terminated by verified PID and start time. Angular dev server on 4200, started and stopped by Playwright | No owned listeners remain on 5180, 4200 or 55432 (verified) |
| `.scratch/` (ignored) | Transient logs, the decisive output copy, publish output, Playwright outputs | Kept, ignored |
| User and machine level | No global installs, Windows services, PATH, firewall, certificate or registry changes. No Docker. No model downloads. No GPU. Restores were pointed at `.local`. I did not audit every incidental user-profile write the dotnet, npm or Edge CLIs make themselves, such as first-run sentinels or a temporary Edge profile in %TEMP% | â€” |
| Remote | Normal pushes of `feature/wp-0003-durable-intake` only, never forced | See publication receipt |

## Decisions and rationale

1. **Partial PostgreSQL download (deviation from "archive hash").**
   - Measured throughput was 17â€“110 KB/s, and pgAdmin 4 is 82% of the 389.5 MB archive.
   - I fetched only bin/lib/share by HTTP range and verified every entry against the central directory (name, sizes, CRC-32).
   - Identity is recorded as Content-Length, ETag, Last-Modified, the central-directory SHA-256, a per-file SHA-256 manifest and its digest `47c3deb9â€¦051f`.
   - All 161 exe/dll files have valid EnterpriseDB Authenticode signatures.
   - **No whole-archive SHA-256 exists.** The reviewer can reproduce the same subset with the same script and compare manifests.
   - Details: `docs/evidence/WP-0003/eld-implementer/postgresql-binaries.md`.
2. **`startxref` precondition (implementation addition).**
   - Exploration showed PdfPig 0.1.16 with `UseLenientParsing=false` admitting a PDF whose `startxref` and xref entries were all shifted. This is the brute-force recovery the design anticipated.
   - Design step 4 also says malformed files must never be accepted. To reduce that gap without building a validator, the final `startxref` must point exactly at `xref` or at an `N G obj` header; otherwise the result is 422 `pdf_invalid_cross_reference`.
   - This is stricter than the design text, never weaker. **The reviewer should confirm it is acceptable or request its removal.**
3. **Known limitation pinned, not hidden.**
   - Wrong object offsets behind a valid `startxref` are still recovered and admitted by PdfPig.
   - A test asserts this observed behaviour, so a dependency change cannot silently alter it.
   - Rejecting such files would need a custom xref-table validator, which the design rules out ("not a complete PDF conformance validator").
4. **Receipt timestamp precision.** PostgreSQL `timestamptz` stores microseconds, so the submission time is truncated to microseconds before persisting. The 201 receipt then equals every later read. The first real acceptance run found this.
5. **Browser.**
   - Playwright uses the installed Edge (`channel: 'msedge'`). This avoids a ~100 MB browser download at the observed bandwidth, and nothing is installed.
   - `PLAYWRIGHT_BROWSERS_PATH` points inside `.local`, and `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` is set.
   - Vitest was not adopted. Behaviour is covered by real-browser checks, and the design pins Vitest only "when used".
6. **Package selection.**
   - Only the Angular packages the screen needs are installed: core, common, compiler, platform-browser, router, plus build, cli and compiler-cli.
   - Forms, animations and zone.js are not installed; the app is zoneless.
   - Every transitive package is frozen in `package-lock.json` (364 entries) and in 7 `packages.lock.json` files.
   - xunit.v3 4.0.3 on MTP transitively brings in `Microsoft.Testing.Extensions.Telemetry` 2.5.2 and `Microsoft.ApplicationInsights` 2.23.0. All test runs set `TESTINGPLATFORM_TELEMETRY_OPTOUT=1`. No VSTest packages are used.
7. **Process-boundary tests.**
   - The acceptance harness launches the built API as a separate OS process and kills it with `TerminateProcess`, after re-verifying the PID and start time. An abrupt kill is a stronger boundary than a graceful stop.
   - There are no production crash switches or test hooks. The only test-related attribute in shipped code is `InternalsVisibleTo`, used for the generated-SQL check.
8. **Schema and ids.**
   - Dedicated schema `eledgercare`, owned by the migrator.
   - `REVOKE ALL ON SCHEMA public FROM PUBLIC` and `REVOKE ALL ON DATABASE â€¦ FROM PUBLIC`.
   - Server ids are UUIDv7 (`Guid.CreateVersion7`).
   - Migrations run only through `dotnet-ef database update` in `prepare-database.ps1`, or through `MigrateAsync` called explicitly by the test harness. The application never migrates.
9. **Transaction cancellation.** The insert transaction is not bound to `RequestAborted`. A client that disconnects after sending its full body therefore cannot turn a commit into a self-inflicted uncertain cancellation; the client reconciles through the key.

## Verification

All checks below ran on `e3117ec2aa11a78359a754cfe52ef3ece6c1733f` unless marked exploratory.

| Check / exact command or tool operation | Environment and revision | Actual result | Evidence location |
| --- | --- | --- | --- |
| Base and ownership: `git status`, `git rev-parse HEAD`, `git worktree list`; `git show b1e4402â€¦:{INDEX.md, kickoff, WP-0002/005}`; Carbon /004 and matrix at `6722ff0â€¦` | Worktree at base `bce84931â€¦`, clean | Branch, worktree and base matched. Reservation released. The only untracked item was the coordinator's ignored `.scratch/dispatch` log, which I left untouched | â€” |
| `dotnet tool restore`; `dotnet restore ELedgerCare.slnx --locked-mode` | Clean tree, all bin/obj deleted | Exit 0. Lock files satisfied | `decisive-run/01`, `02` |
| `dotnet build ELedgerCare.slnx -c Release --no-restore` | Same | Exit 0, **0 warnings** (warnings are errors), 0 errors | `decisive-run/03` |
| `npm ci --no-audit`; `npx ng build` (web/) | Same | Exit 0 and exit 0. Initial bundle 256 kB raw | `decisive-run/04`, `05` |
| `prepare-database.ps1 -Database eledgercare_candidate_e3117ec` | Owned cluster PG 18.7 | `dotnet-ef database update` applied `20261114182147_InitialDurableIntake`. App role: SELECT/INSERT on the 3 tables, no UPDATE/DELETE/TRUNCATE, no access to the history table, no schema CREATE | `decisive-run/06` |
| `dotnet test --solution ELedgerCare.slnx -c Release --no-build` (MTP v2) | Same | **52 discovered / 52 passed / 0 failed / 0 skipped**: Domain 7, Infrastructure 30, Acceptance 15. Runtime 2 min 42 s | `decisive-run/07`, `acceptance-evidence.jsonl` |
| `run-browser-checks.ps1`: Playwright 1.65.1, msedge, `ng serve` on 127.0.0.1:4200, API on 5180, fresh `eledgercare_e2e` | Same | **6 / 6 passed** | `decisive-run/08`, `browser-evidence.json`, `playwright-results.json` |
| `run-demo-smoke.ps1` on the dev database | Same | 201, then API kill and restart, then PostgreSQL fast stop and start, then the same id, status and SHA every time. `allMatch: true` | `decisive-run/09`, `demo-receipt.json` |
| `dotnet publish src/ELedgerCare.Api -c Release` and listing of the output | Same | 26 files: product, EF/Npgsql, PdfPig assemblies and config. **No** test, Design/Roslyn, research or evaluation assemblies, and no secrets. EF 10.0.15 (file version 10.0.1526.53008), Npgsql 10.0.3, PdfPig 0.1.16 run against framework 10.0.x (installed 10.0.14) | `summary.json` (`publishFiles`, `keyAssemblyVersions`, `apiRuntimeConfig`) |
| `dotnet list â€¦ reference` for the 4 src projects | â€” | Domain: no references. Application â†’ Domain. Infrastructure â†’ Application, Domain. Api â†’ Application, Infrastructure. No product project references tests, evaluation or research | â€” |
| Server log, run window only | Same | 1 `duplicate key â€¦ ux_documents_idempotency_key` (the race test). 1 `FATAL: connection to client lost` from backend 25136, the backend recorded as blocked in DI-05 | `postgres-log-excerpt.txt` |
| Secret scan of the evidence for the generated passwords | â€” | 0 hits | Evidence README |
| Exploratory, pre-freeze: preserved failures | Earlier working trees | xref recovery, timestamp precision (10/14), pipeline hang, test SQL cast. Each was fixed in the candidate and the affected checks were re-run | Evidence README, "Preserved exploratory failures" |

### Criterion mapping (author evidence)

| ID | Evidence on the candidate |
| --- | --- |
| BIC-01 | `PersistenceMappingTests`: the generated metadata SQL contains `byte_length`/`sha256` and no `.bytes`. The download query selects only `bytes`. Both FKs are `Restrict` in the model; in the database `confdeltype=r`, per the schema acceptance test |
| BIC-02 | `BIC02_third_concurrent_submissionâ€¦`: two POSTs blocked in the database hold both slots. A third gets 429 `admission_busy`. A GET answers 404 during saturation. The same-key retry then gets 201. Step-1 400/415/413 cases and Kestrel 413 mapping are in `DI07_invalid_requestsâ€¦` (declared 10,485,761 bytes gives `413` with no body sent; streamed chunked oversize gives 413 `document_too_large`) |
| BIC-03 | `DI05_api_killed_inside_a_blocked_transactionâ€¦`: the harness holds `LOCK TABLE processing_jobs IN SHARE MODE`. The API backend (PID 25136) is `active`, waiting on Lock/relation with `backend_xid=1044`. Its query is `INSERT INTO eledgercare.processing_jobs â€¦`. It holds granted RowExclusiveLock on `documents` and `original_artifacts` and is **waiting** on `processing_jobs`. **Interpretation:** an earlier insert in that transaction executed (an XID was assigned and the earlier relation locks were granted while blocked on the third statement), but the unit was uncommitted. The API was killed; the lock was released; the backend ended (FATAL client lost); all three tables had 0 rows; after restart, key lookup returned 404 and the same-key retry returned 201 |
| BIC-04 | `global.json` uses the MTP runner and test projects are `OutputType=Exe`, with no Microsoft.NET.Test.Sdk or xunit.runner.visualstudio. Discovery and execution work: 52 tests. dotnet-ef 10.0.15 ran (migrations add and database update) on the installed 10.0.14 runtime, and the EF 10.0.15 assemblies loaded in the API and tests |
| BIC-05 | `PLAYWRIGHT_BROWSERS_PATH` set to `.local/ms-playwright` (unused, no download). Outputs go to `.scratch/playwright`, and report/test-results/coverage patterns are ignored. The npm registry dual-stack timeout was **not reproduced** (the slowness affected the IPv4 CDN as well), so no `--dns-result-order` fallback was used |
| BIC-06 | `postgresql-binaries.md`, `setup-cluster.ps1`, and the `runtime roleâ€¦` acceptance test: 5 denied operations with 42501, `fsync`/`full_page_writes`/`synchronous_commit` = on, server 18.7, listening on 127.0.0.1, scram-sha-256 |
| DI-01 | HTTP 201 with a `Location` header. A separate session immediately sees the three joined rows. Browser test shows the receipt |
| DI-02 | Bytes compared byte for byte, SHA-256 and length recomputed independently. `Content-Length`, `application/pdf`, `attachment; filename=document-{id}.pdf` and `nosniff` checked. The browser download is compared by bytes and hash |
| DI-03 | `awaiting_extraction` appears in the database, `GET /api/documents`, `GET /api/submissions` and the UI ("Awaiting extraction"). The receipt has exactly 7 fields. There is no extraction column or state, and the UI shows no extracted fields |
| DI-04 | Acceptance: API PID A is killed and PID B started on the same database and cluster, returning the same receipt, bytes and status. Browser: the owned API is killed and restarted, the document is reopened by reference, and the re-download hash matches. Smoke: also restarted after a PostgreSQL fast restart |
| DI-05 | Partial body (declared 887, sent 443, then RST) gives 0 rows, key 404, and same-key retry 201. Interrupted pre-commit transaction: see BIC-03 |
| DI-06 | Lost response: the proxy dropped an upstream `HTTP/1.1 201 Created`, the client got `HttpRequestException`, key lookup returned the same id, and the exact retry returned 200 with the same id (rows 1/1/1). Sequential retries: 201, 200, 200. Conflicting bytes and a single flipped byte both give 409, and the original is unchanged. Different keys with identical bytes give two documents. Concurrent same-key race: the second backend waited on a `transactionid` lock behind the first, giving 201 + 200, the same document and one server unique-violation. Browser: 5xx after a real commit gives "Submission outcome unknown", the key is kept across reload, and a status check reconciles. 429 keeps the key and the same-key retry succeeds. An earlier uncertainty is not resolved by a later 429. A double click sends one request; a new key needs "New submission" |
| DI-07 | 16 PDF-profile cases give 422 with specific codes: non-PDF, PDF 2.0, FDF, leading junk, missing EOF, truncated with and without EOF, shifted `startxref`, truncated content stream, malformed page object, dangling/non-page kid, missing root, password-required encryption, owner-password with empty user password (the precondition shows PdfPig opens it with `IsEncrypted=true`), and 51 pages. 11 HTTP cases (key, media type, encoding, empty, declared/streamed oversize) all leave 0 rows. Filename-like headers give 201 with a server-generated name; the traversal route gives 400; the schema has exactly 13 designed columns; the API directory is unchanged. Configured lower limits apply, and out-of-range startup values are refused |
| DI-08 | Not claimable by the author. Ready for Carbon reproduction |

### Checks not run, and why

- **No power-loss, OS-crash, disk-full, backup/restore or cross-machine test.** Only application restarts and one PostgreSQL service fast restart were tested; none of these prove power-loss durability.
- No load, performance or hostile-PDF fuzzing. The admission profile is for developer fixtures, not a sandbox.
- No Vitest, which was not adopted.
- No Chromium or Firefox browser runs; only Edge 157 was used.
- No `SET LOCAL synchronous_commit` statement-log capture. The statement is in the source (`IntakeStore.InsertAsync`), and the server-wide setting is verified as `on`.
- No whole-archive SHA-256 of the EDB zip.
- No Linux or macOS run.

## Review map

- Pinned diff: `git diff bce84931fef5cf2a8fa3652095dbea2973a19aef e3117ec2aa11a78359a754cfe52ef3ece6c1733f` (94 paths). Evidence: `git show 6691aaab848263e2f8326a491a9647d239119865`.
- Core behaviour:
  - `src/ELedgerCare.Api/DocumentEndpoints.cs` (`SubmitAsync`, step order)
  - `src/ELedgerCare.Application/Intake/SubmitDocument.cs`
  - `src/ELedgerCare.Infrastructure/Persistence/IntakeStore.cs` (`InsertAsync`, the unique-violation filter)
  - `src/ELedgerCare.Infrastructure/Pdf/PdfPigAdmission.cs`
  - `src/ELedgerCare.Infrastructure/Persistence/Migrations/20261114182147_InitialDurableIntake.cs`
- Browser semantics: `web/src/app/intake/intake-page.ts` (`failed`, `resolved`, `newSubmission`) and `submission-api.ts`.
- Failure-boundary harness:
  - `tests/ELedgerCare.Acceptance.Tests/Harness/{ApiProcess,LockObserver,RawHttp}.cs`
  - `DurableIntakeTests.cs`
  - `web/e2e/intake.spec.ts`
- Setup: `deploy/dev/postgres/*`, `deploy/dev/database/*`.
- To reproduce in a separate worktree, follow the README setup section, using `setup-cluster.ps1 -Port 55433` and different API/UI ports.
  - The browser runner and spec are hard-wired to API port 5180 and UI port 4200 (`owned-api.ts`, `proxy.conf.json`, `playwright.config.ts`). The reviewer must run them while my processes are stopped (they are now), or adjust those values in a scratch copy.
  - The .NET acceptance harness uses ephemeral ports and reads the cluster port from its own `.local/secrets/pg-local.json`.

## Risks, disagreements, and unfinished work

- **Design delta for the reviewer's disposition:** the `startxref` precondition (decision 2), and the pinned PdfPig recovery limitation (decision 3).
- **BIC-06 identity is subset-based:** there is no whole-archive hash (decision 1). Network throughput on this machine was ~17â€“110 KB/s, so a reviewer download of the full archive would take roughly 1â€“6 hours.
- **Fixed ports in the browser and smoke runners:** 5180 and 4200, as above. This is a known reproducibility friction in a second worktree, not a correctness issue.
- **Development database contents:** `eledgercare_product_dev` holds two synthetic smoke submissions of F1-SWO-001 (demo data, not seeded by the application).
- **Test-related code in the shipped assembly:** `InternalsVisibleTo` in Infrastructure. It has no runtime behaviour.
- **Unaudited incidental profile writes:** possible writes by the dotnet, npm and Edge CLIs outside `.local` (see external effects).
- No substantive design disagreement or policy blocker was encountered. No escalation is needed.

## Handoff

- Next action: independent product review WP-0003 / 002 by `eld-reviewer` (Carbon), bound by `eld-coordinator`.
- Candidate: `e3117ec2aa11a78359a754cfe52ef3ece6c1733f` on `feature/wp-0003-durable-intake`. Evidence: `6691aaab848263e2f8326a491a9647d239119865`.
- Outstanding acceptance checks (Carbon, isolated worktree, cluster and ports):
  - source inspection
  - locked restore and build
  - real PostgreSQL migration and acceptance
  - restart, retry and lock-boundary reproduction
  - browser checks
  - disposition of the `startxref` addition and the pinned limitation
- The coordinator receives the branch, this report path, the deliverable and evidence SHAs, and the report publication SHA. The report publication SHA is supplied in the handoff message after the push; it cannot appear inside this file.
- Publication receipt at the time of writing: deliverable `e3117ec2â€¦` and evidence `6691aaabâ€¦` were each confirmed as the remote tip of `refs/heads/feature/wp-0003-durable-intake` via `git ls-remote origin` immediately after their pushes. Remote confirmation of this report's own commit is reported in the handoff message.
