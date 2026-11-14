# WP-0003 / 001 evidence (eld-implementer)

All decisive results below were produced against the frozen code candidate
**`e3117ec2aa11a78359a754cfe52ef3ece6c1733f`** (`git status --porcelain` empty, recorded in
[summary.json](decisive-run/summary.json)) by [decisive-run.ps1](decisive-run.ps1), executed
2026-11-14 19:04–19:09 UTC with all `bin/`/`obj/`/`web/dist`/`web/.angular` outputs deleted first.
Evidence files contain no credentials (scanned against the generated passwords: 0 hits) and no document contents.

| Step | Command (from the script) | Result | Log |
| --- | --- | --- | --- |
| 01 | `dotnet tool restore` | exit 0, dotnet-ef 10.0.15 | [01](decisive-run/01-tool-restore.txt) |
| 02 | `dotnet restore ELedgerCare.slnx --locked-mode` | exit 0 (lock files satisfied) | [02](decisive-run/02-restore-locked.txt) |
| 03 | `dotnet build ELedgerCare.slnx -c Release --no-restore` | exit 0, 0 warnings, 0 errors (warnings are errors) | [03](decisive-run/03-build.txt) |
| 04 | `npm ci --no-audit` (web/) | exit 0 (package-lock satisfied) | [04](decisive-run/04-npm-ci.txt) |
| 05 | `npx ng build` | exit 0 | [05](decisive-run/05-ng-build.txt) |
| 06 | `prepare-database.ps1 -Database eledgercare_candidate_e3117ec` (fresh DB, `dotnet tool run dotnet-ef database update`, grants) | exit 0; runtime role SELECT/INSERT only | [06](decisive-run/06-migrate-fresh-db.txt) |
| 07 | `dotnet test --solution ELedgerCare.slnx -c Release --no-build` (MTP) | **52 discovered / 52 passed / 0 failed / 0 skipped** (Domain 7, Infrastructure 30, Acceptance 15) | [07](decisive-run/07-dotnet-test.txt), [acceptance-evidence.jsonl](decisive-run/acceptance-evidence.jsonl) |
| 08 | `run-browser-checks.ps1` (Playwright 1.65.1, msedge 157) | **6 / 6 passed** | [08](decisive-run/08-browser.txt), [browser-evidence.json](decisive-run/browser-evidence.json), [playwright-results.json](decisive-run/playwright-results.json) |
| 09 | `run-demo-smoke.ps1` (dev DB; API restart then PostgreSQL fast restart) | exit 0, `allMatch: true` | [09](decisive-run/09-demo-smoke.txt), [demo-receipt.json](decisive-run/demo-receipt.json) |
| 10 | `dotnet publish src/ELedgerCare.Api -c Release` | exit 0; 26 files, no test/Design/Roslyn/research assemblies | [10](decisive-run/10-publish.txt), [summary.json](decisive-run/summary.json) `publishFiles` |

Server log during the run ([excerpt](decisive-run/postgres-log-excerpt.txt)): exactly one
`duplicate key value violates unique constraint "ux_documents_idempotency_key"` (the deterministic
concurrent-race test) and exactly one `FATAL: connection to client lost` from backend PID 25136 — the
same backend recorded as blocked on `processing_jobs` in the DI-05 interrupted-transaction evidence, which
aborted its uncommitted transaction once the harness released the lock after the API process was killed.

PostgreSQL binary acquisition/validation: [postgresql-binaries.md](postgresql-binaries.md) and the
per-file [server-subset manifest](postgresql-18.7-1-server-subset.sha256).

## Preserved exploratory failures (before the candidate was frozen)

These were real failures observed while developing; each led to a source change that is part of the
candidate, and all affected checks were re-run in the decisive run above.

| When (UTC) | Check | Observed failure | Disposition |
| --- | --- | --- | --- |
| 18:14 | `PdfPigAdmissionTests` (exploratory) | A PDF with both `startxref` and every xref entry shifted by 7 bytes was **admitted**: PdfPig 0.1.16 strict mode recovered it (the brute-force xref recovery the design anticipated). 22/23 passed. | Added the narrow `startxref`-target precondition (`InvalidCrossReference`, HTTP 422 `pdf_invalid_cross_reference`). |
| 18:17 | same (23/25 passed) | With the precondition, a file whose **object offsets** are wrong behind a *valid* `startxref` is still recovered and admitted by PdfPig. | Not "fixed" with a custom xref validator (outside the design's restricted profile); pinned as `Known_limitation_wrong_object_offsets_behind_a_valid_startxref_are_recovered_by_pdfpig` so a dependency change is detected. Reported as a limitation. |
| 18:17 | same | "Truncated + appended `%%EOF`" now stops at the `startxref` check instead of reaching the parser. | Test expectation updated; added `TruncateFirstContentStream` variant (valid offsets, short stream) that reaches PdfPig and is rejected (`pdf_unreadable`). |
| 18:21–18:23 | `setup-cluster.ps1` | Script hung after `pg_ctl start` because the postmaster inherited the calling pipeline's stdout. Cluster was stopped cleanly with `pg_ctl stop -m fast`. | `start-cluster.ps1` launches `pg_ctl` through ShellExecute (hidden window); re-run succeeded. |
| 18:46 | Acceptance (first real run) | **10/14 passed**; 4 failed: the 201 receipt's `submittedAtUtc` had 100 ns precision while PostgreSQL `timestamptz` stores microseconds, so later GETs differed by < 1 µs. | `SubmitDocument` truncates the submission time to microseconds before persisting; all 4 then passed. |
| 18:59 | New schema acceptance test | `42725 operator is not unique: text \|\| "char"` (test SQL). | Cast `"char"` columns to `text` in the test query. |

## Not run / limits

No power-loss, OS-crash, disk-full, backup/restore or cross-machine check. The demo smoke also restarted
the PostgreSQL service (fast shutdown), which is still not a power-loss test. No load/performance test,
no hostile-PDF fuzzing, no Vitest unit tests (not used). Whole-archive SHA-256 of the EDB zip not computed
(see postgresql-binaries.md). Independent reproduction (DI-08) belongs to eld-reviewer.
