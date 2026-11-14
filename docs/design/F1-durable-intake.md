# F1: retain a maintenance PDF and its status across application restart

Author: eld-coordinator. WP-0002 / 001. **Proposed design, awaiting the combined independent Carbon review.** Jack's product/database direction is accepted; this technical design is not. This document, the supplied contract/product brief, seed profile and dependency observations form one review candidate.

## Overall model, feature list and delivery plan

A Document is one business submission with a stable identity. It owns an immutable OriginalArtifact (bytes, SHA-256, length and media type) and has one ProcessingJob describing requested extraction. A job is not an execution attempt. ExecutionAttempt, ExtractionResult, ReviewDecision and source-linked Archive results remain future model concepts, not classes to scaffold now.

Feature sequence: F1 durable intake; F2 one locally qualified scanned-document extraction path; F3 source-linked field review/corrections; F4 source-linked archive retrieval. Only F1 and the separately bounded initial source R&D are released by the kit. Technical scaffolding enables F1 but is not itself a customer outcome. Additional formats, permissions, installer/backup hardening and semantic search are visible future work, not current release authority.

After this design is independently accepted, Opus first establishes the reproducible scaffold, then implements F1 and meaningful checks in the same product packet. Carbon reviews actual frozen code and reproduces the PostgreSQL/restart/retry checks in separate resources. The coordinator integrates only accepted deltas and reruns affected checks on the combined candidate. Do not equate this slice with the entire 26 November demonstration or production readiness.

## Customer behavior and API

The local Angular screen selects one permitted synthetic maintenance PDF and submits it. It displays the stable document reference, original-byte size/digest, and **Awaiting extraction** status returned by the server. It offers original download and reopening a document reference after restart. It does not fabricate OCR fields, completion percentages or extraction success.

| Boundary | Behavior |
| --- | --- |
| POST /api/documents | Raw PDF body, Content-Type application/pdf, required Idempotency-Key containing a non-empty UUID in canonical D format; 201 only after commit for a new document |
| GET /api/documents/{documentId} | Committed metadata and job status, or 404; does not load original bytes just to show status |
| GET /api/documents/{documentId}/original | Exact committed bytes, application/pdf, Content-Length, attachment filename document-{server-generated-documentId}.pdf, X-Content-Type-Options nosniff |
| GET /api/submissions/{idempotencyKey} | Committed receipt or 404 at this observation instant; supports reconciliation of a lost response |

Receipt fields: documentId, jobId, status=`awaiting_extraction`, submittedAtUtc, byteLength, lowercase hexadecimal sha256 and originalUrl. Stable references are returned only after the corresponding rows commit. Error bodies use a consistent ProblemDetails shape without SQL, credentials, document content or parser dumps.

The original upload filename is not transmitted or persisted in F1; the UI can display the browser's local selection name. The raw-body protocol avoids multipart temporary-file storage. Every server download name is generated from the server document UUID. Arbitrary filename headers or a client File name resembling a path cannot select a storage path. This intentionally omits filename persistence rather than implementing an unreliable path sanitizer.

## Admission limits and error precedence

Freeze MaxDocumentBytes at **10,485,760 (10 MiB)**, configurable downward for this slice; reject startup values outside 1..10,485,760. MaxPages defaults to **50**, configurable in 1..50. Apply the effective byte cap both in Kestrel and while reading a body with unknown or misleading Content-Length. Permit at most two concurrent admission requests with no waiting queue; excess requests return 429. Read only into a bounded buffer; no production upload directory or multipart spill file is needed.

Admission order is explicit:

1. Reject missing/invalid/empty UUID key with 400; unsupported media type or Content-Encoding with 415. Require application/pdf and identity/no content encoding. Reject declared over-limit length with 413 without full buffering.
2. Read the complete bounded body. Empty input is 400; streamed overflow is 413. A disconnect before full receipt cannot create accepted rows. Compute byte length and SHA-256 from the actual buffered bytes.
3. If the key already names a committed document, compare length/digest and then exact bytes. Exact match returns its existing receipt with 200; any different bytes return 409. Do not revalidate an immutable previously accepted PDF just because limits/library versions later change; the request-level byte cap still applies.
4. For a new key, require a PDF header at the start (%PDF-1.0 through %PDF-1.7, or %PDF-2.0) and an EOF marker followed only by PDF whitespace. Use PdfPig 0.1.16 with UseLenientParsing=false, SkipMissingFonts=false and MaxStackDepth=32 to open the complete document and visit each of its 1..MaxPages pages. Reject encrypted PDFs, malformed/truncated files, zero-page files and unsupported parse structures with 422. Never convert a parse exception into accepted status. Do not run OCR, render pages, extract/persist text, execute actions or fetch external resources.
5. Persist the new submission atomically as below. The database constraint resolves races on the same key. An unexpected infrastructure failure is not a successful receipt; return an appropriate 5xx where the connection remains usable and let the client reconcile the key.

These are a restricted developer-fixture admission profile, not a complete PDF conformance validator or hostile-content sandbox. Byte/page/depth caps do not prove a CPU/memory bound for every compressed PDF. This local-only synthetic-data slice must not be exposed to customer/untrusted uploads without separate parser/resource/security qualification. The test suite must demonstrate actual rejection of representative missing EOF, truncated structure, malformed object/page references, encrypted, empty, oversized and non-PDF inputs; do not claim exhaustive rejection from a header check.

## One storage and transaction boundary

Choose PostgreSQL bytea storage for these small originals, so original bytes, receipt metadata and the requested processing job commit together. This avoids a cross-filesystem/database commit/recovery protocol in F1. PostgreSQL supports binary byte strings directly. The tradeoff is database/WAL/backup growth and bounded buffering; larger files or alternative artifact storage require a later reviewed design. [PostgreSQL binary data](https://www.postgresql.org/docs/18/datatype-binary.html).

| Table / concept | Required data and constraints |
| --- | --- |
| documents / Document | document_id UUID primary key; idempotency_key UUID unique and not null; submitted_at timestamptz not null |
| original_artifacts / OriginalArtifact | document_id UUID primary key and FK; bytes bytea not null; sha256 bytea exactly 32 bytes; byte_length integer, 1..10,485,760, equal to octet_length(bytes); media_type fixed application/pdf; admitted page_count 1..50 |
| processing_jobs / ProcessingJob | job_id UUID primary key; document_id UUID unique FK; status constrained to awaiting_extraction for F1; requested_at timestamptz not null |

Generate document/job UUIDs server-side. Content digests are content identity, not business identity: identical bytes submitted under distinct keys create separate documents. Original bytes and digest have no update/delete application path. Record invariants in the domain and persistence mapping; do not create generic repository/unit-of-work wrappers over EF solely for pattern compliance.

After admission, use one short explicit EF/Npgsql transaction at PostgreSQL Read Committed isolation. Insert all three rows and commit before sending a receipt. A unique-key collision rolls back the entire losing transaction; use a fresh context/read to compare the winner's committed bytes and return 200 or 409. Catch only the specifically identified idempotency unique constraint for this path; other SQL errors must not masquerade as retries. A fresh key whose first attempt rolled back can subsequently succeed.

Use logged tables. Setup/evidence must show fsync=on, full_page_writes=on and synchronous_commit=on; issue SET LOCAL synchronous_commit=on for the intake transaction and fail the durability qualification if required server settings differ. Do not turn these off to speed tests. The transaction is the all-or-nothing boundary; PostgreSQL documents that synchronous commit controls acknowledgement relative to WAL flush. This design still makes only the tested application-restart claim, not demonstrated power-loss survival. [Transactions](https://www.postgresql.org/docs/18/tutorial-transactions.html), [WAL settings](https://www.postgresql.org/docs/18/runtime-config-wal.html).

## Retry, interruption and restart semantics

The browser generates and saves one pending UUID in sessionStorage before sending an upload. A network error or client timeout shows **Submission outcome unknown**, retaining that key. The user can query its committed receipt or reselect and retry the same bytes using the same key. A new business submission requires an explicit new-submission action/key; a double click cannot silently mint another key. Do not save original bytes or document contents in browser storage. A normal document route retains the document reference for reload/reopen.

| Failure boundary | Durable state / recovery |
| --- | --- |
| Before complete body/admission | No database rows; key lookup can return 404; same-key retry remains possible |
| After some inserts, before transaction commit | No accepted state visible; rollback on failure/connection loss removes the entire uncommitted unit |
| Commit succeeded, HTTP response lost | Original/document/job remain; key lookup or exact retry recovers the same reference and status |
| Commit result uncertain to the application | Never infer rollback or erase data from a timeout; reconnect/query the key and retry with the same identity |
| Restart after an acknowledged receipt | Fetch the same rows/bytes/status from PostgreSQL; do not recreate state from process memory |

A 404 key lookup is an instantaneous absence observation; another request may still be in flight. There is no durable receiving state because F1 accepts only a whole buffered PDF in one database transaction. The browser's uncertain transport state is distinct from ProcessingJob status. No orphan-file reconciler, OCR job runner, distributed broker, workflow engine or event-sourcing store is needed. Restart reads committed state; it does not mark any job extracted.

## Code boundaries and reproducible scaffold

One production ELedgerCare.slnx contains Domain, Application, Infrastructure, Api and their .NET tests. Domain has no outward project dependency. Application depends on Domain and expresses intake/query use cases with only the necessary persistence/PDF-admission boundaries. Infrastructure implements PostgreSQL/EF and PDF admission. Api performs HTTP validation/composition and hosts endpoints. The Angular application is under web/. workers/ocr/ initially contains a boundary README only. Product references neither research nor evaluation tooling.

Put actual business types under Documents/Intake/Processing as needed; no empty future classes. Keep migrations in Infrastructure and invoke them explicitly through the project-local EF tool, not as silent application startup side effects. Use a dedicated local cluster/database and credentials outside Git. Restrict runtime credentials to the tables/actions actually needed; use separate schema/migration access where practical and record the arrangement. Seed no fake customer/processing data automatically.

Exact proposed bootstrap pins, supported by metadata observations in dependency-metadata-2026-11-14.json:

| Component | Pin / policy |
| --- | --- |
| .NET | SDK 10.0.403; global.json rollForward=disable, allowPrerelease=false; target net10.0 |
| Node / npm | 24.18.0 / 11.16.0, record exact engine/package-manager expectations |
| Angular framework packages | core/common/forms/compiler/platform-browser/router/compiler-cli 22.2.6 |
| Angular tooling | cli/build 22.2.7; project-local only |
| TypeScript / RxJS / tslib | 6.0.3 / 7.8.2 / 2.8.1 |
| EF Core / Design / local dotnet-ef | 10.0.15; no global tool changes |
| Npgsql EF provider | 10.0.3; metadata requires EF >=10.0.4 and <11.0.0 |
| PostgreSQL | 18.7; exact downloadable vendor build/hash and successful launch remain a bootstrap gate |
| PDF admission | PdfPig 0.1.16; release tag resolves to a7bb35662bbbf405efddad50aedc9bcdcf515afc, matching nuspec repository metadata |
| .NET tests | xunit.v3 4.0.3, using its MTP v2 dependency path; qualify .NET 10 runner configuration during bootstrap; do not silently mix MTP/VSTest |
| UI checks | vitest 4.0.18; @playwright/test 1.65.1 for actual browser behavior when used |

Angular's published compatibility table and observed package metadata permit Node 24.18.0 and TypeScript 6.0.3 for Angular 22. This is metadata compatibility, not an executed restore/build. [Angular compatibility](https://angular.dev/reference/versions). SDK selection is independent of the runtime target; explicit disable prevents silently switching SDKs. [global.json](https://learn.microsoft.com/en-us/dotnet/core/tools/global-json). Npgsql 10 is the EF 10 provider family. [Npgsql release notes](https://www.npgsql.org/efcore/release-notes/10.0.html).

Retain exact direct versions and generate/check in package-lock.json, NuGet packages.lock.json and the local tool manifest after reviewed release. The implementation must resolve optional versus required peers (for example Angular animations/zone and UI test DOM packages), select only needed packages, and pin every resulting direct/transitive dependency in the lockfile. Inspected alternate test packages in the metadata file are not automatically selected dependencies. No floating latest, previews, global package installs, automatic runtime upgrades or worker dependency guesses. Any incompatibility that changes this substantive design returns as a bounded correction before feature implementation; routine additional dev-only pins are inventoried and reviewed with the scaffold.

## Local resource plan and known setup gap

Observed on 2026-11-14: docker version could not connect to dockerDesktopLinuxEngine because its pipe was absent. postgres/pg_ctl/psql were not found on the checked PATH; the specifically checked PostgreSQL 17/18 Program Files server paths were absent. This is not a claim that no server exists anywhere. No daemon or existing service was started or modified.

Selected next setup route: evaluate a project-scoped Windows PostgreSQL 18.7 binary archive from the EDB distribution linked by PostgreSQL, then initdb/pg_ctl for an owned per-worktree cluster, without a machine-wide installer or Windows service. Record the exact download/build/hash, validate the binaries and demonstrate start/query/restart before calling this route reproducible. It is currently **proposed, not qualified**; no working database launch is claimed. If prerequisites fail, report that evidence and continue independent scaffold/research work without pretending SQLite/in-memory establishes PostgreSQL persistence. [Official Windows download route](https://www.postgresql.org/download/windows/).

| Owner | Local-only candidate ports | Owned state / separation |
| --- | --- | --- |
| eld-implementer | API 5180; UI 4200; PostgreSQL 55432 | its worktree .local/tools, .local/postgres-data, .local/logs; database eledgercare_product_dev and separate per-test databases |
| eld-reviewer, later product checks | API 5280; UI 4300; PostgreSQL 55433 | its isolated review worktree .local directories and independently initialized cluster |
| R&D authors | no ports, databases or GPU released | own research directories/worktrees; no product state writes |

These are coordination reservations, not proof of a free port or a bind. Check immediately before starting, record actual PIDs/endpoints and change only owned resources. Bind PostgreSQL and both servers to 127.0.0.1, use a development proxy for /api instead of broad CORS, and reject non-local public host/origin exposure. Authentication/customer access requires a later bounded release. Do not auto-start Docker Desktop and its unrelated workloads as a fallback.

## Acceptance and independent execution plan

Use one small independently generated synthetic PDF for product progress; do not wait for or claim admission of the R&D corpus. Record source data, fixture ID, SHA-256 and licensing/ownership. Each decisive check runs against a frozen code candidate, with secrets and outputs in owned ignored scratch paths. The reviewer repeats applicable checks against that same code in another worktree/cluster, without source edits.

| Criterion | Required evidence |
| --- | --- |
| DI-01 | Real HTTP submission returns 201 only after all rows are committed; browser smoke shows the receipt |
| DI-02 | Download bytes compared byte-for-byte and with independently recomputed SHA-256/length |
| DI-03 | Database/query/UI show awaiting_extraction, with no extracted fields or simulated OCR |
| DI-04 | Stop/restart only the harness-owned actual API process; same persistent cluster yields identical reference, bytes and status |
| DI-05 | Partial-body disconnect and an interrupted pre-commit transaction leave no accepted partial unit; restart/retry succeeds honestly |
| DI-06 | Lose a committed HTTP response, reconcile/retry the same key; test sequential and concurrent exact retries, conflicting bytes, and different keys with identical bytes |
| DI-07 | Empty, declared/streamed oversized, unsupported media, malformed/truncated/encrypted PDFs and filename-like input cannot create an accepted record or arbitrary file |
| DI-08 | Non-author source inspection plus actual build, PostgreSQL migration/integration, restart/retry and applicable browser checks on the pinned candidate in isolated resources |

Failure evidence should exercise the actual process/database boundary without production crash switches. A harness can hold a database lock to block inserts/commit, observe the owned connection waiting, terminate only its own API process, release its own lock and verify rollback. A controlled local response-dropping proxy can demonstrate committed-but-unobserved receipt. Record which boundary the mechanism actually reached; timing guesses are not decisive evidence. Do not terminate arbitrary listeners or inspect unrelated process command lines.

Verify project-reference direction and that release contents exclude research/evaluation tooling, test hooks, raw evidence and secrets. Use a few meaningful domain checks and real PostgreSQL acceptance tests, not implementation-mirroring test inflation. Publish discovered/passed/failed/skipped counts, exact commands, process/database restart boundaries, candidate SHA and evidence paths. An application restart is not a database/OS/power-loss test; describe additional checks separately if actually performed.

## Review questions and held work

Carbon should assess the one-store transaction/retry contract, constrained PDF admission limitations, interrupt/response-loss evidence mechanisms, dependency/runner choices, local resource plan and reporting/authority profile together. The PostgreSQL binary build/launch, full dependency locks, parser behavior and actual tests remain unexecuted bootstrap work. No self-acceptance is claimed. Record acceptance, bounded corrections or a substantive unresolved disagreement on this exact revision before Opus writes application code.

The first milestone stops at independently accepted F1 and independently reviewed initial R&D backlog/corpus. OCR runtime/model downloads, GPU runs, search, training, architecture modification, customer-data handling and deployment require separate assignments.
