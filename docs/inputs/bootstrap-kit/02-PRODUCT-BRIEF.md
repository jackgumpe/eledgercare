# Product lane: bootstrap and durable maintenance-document intake

This is a release template. The local coordinator must bind it to an actual packet, agent, branch/worktree, base commit, report sequence/path, and reviewer before execution. Do not fill unknown bindings by guessing.

## Customer feature

Retain a submitted maintenance document and its processing status across an application restart.

User: an eTenantCare maintenance operator trying to digitize a work order or invoice.
Value: submission is a durable, inspectable record; closing/restarting the application does not lose the original or misrepresent extraction progress.

This first slice demonstrates persistence, state modeling, and evidence-based delivery. It does not measure OCR quality or establish that a particular model/team is superior.

## Design before implementation

Astra supplies a compact design; Carbon reviews the frozen design. Opus then implements within it. Decide:

- First accepted input: small PDF fixtures representing maintenance work orders/invoices; freeze a configurable byte limit and handling of empty/truncated/unsupported inputs. Supporting later .xlsx/.csv/image intake remains visible in the feature list.
- Original storage: choose PostgreSQL binary storage or controlled local artifact storage with PostgreSQL metadata. Explain the tradeoff for this slice. If separate stores are used, define the commit/recovery protocol; a database transaction does not automatically make file writes atomic.
- Stable document/job IDs, stored content digest and byte count, persisted status, and the response returned after durable acceptance.
- Submission retry identity and how repeated/conflicting requests are handled. Identical bytes do not automatically mean the same business document. A client timeout is not proof that a submission failed.
- Interrupted submission and restart reconciliation. Incomplete records must remain distinguishable from accepted documents and successfully extracted documents.
- Retrieval of the original and the visible status, with safe server-controlled storage identities rather than trusting an uploaded filename as a path.

Keep the design to one coherent feature. Choose the least complex implementation satisfying the criteria, with visible Domain/Application/Infrastructure responsibilities. Do not introduce a workflow engine, distributed broker, generic event-sourcing framework, multiple database providers, or an OCR mock in the production path.

## Bootstrap outcome

Establish the new .NET solution, Angular shell, required project references, PostgreSQL access through EF Core/Npgsql, and reproducible setup/build commands. Pin dependencies. The supported OCR worker directory may initially contain its boundary/README only.

A missing Docker daemon or database server is a setup finding. Do not treat an EF in-memory provider or SQLite as PostgreSQL persistence evidence. Scoped setup and owned development services are allowed; unapproved global/elevated changes are not a reason to overwrite existing installations.

Keep early development bound locally while authentication and customer access remain out of scope. No public/intranet deployment or production-data processing is authorized by bootstrap.

## Acceptance criteria

| ID | Required observable behavior |
|---|---|
| DI-01 | Submit an admitted synthetic PDF through the actual application boundary and receive a stable document reference only after the reviewed durability conditions hold. |
| DI-02 | Retrieve the original bytes and independently recompute their digest/length; they match the submitted original. |
| DI-03 | Display an honest persisted awaiting-extraction status; do not fabricate extracted fields or OCR-success states. |
| DI-04 | Restart the application process, then retrieve the same document reference, bytes, and status from durable storage. |
| DI-05 | Exercise the chosen interrupted-submission boundaries and demonstrate recovery without a false accepted/extracted state or silent loss of an acknowledged original. |
| DI-06 | Exercise a lost response/retry and a conflicting retry according to the reviewed identity policy; do not assume timeout means no side effect. |
| DI-07 | Reject or explicitly classify empty, oversized, and unsupported inputs without producing a valid accepted-document record; uploaded names cannot escape controlled storage. |
| DI-08 | The reviewer reproduces applicable build, PostgreSQL integration, and restart/retry checks against the exact candidate with synthetic data in isolated resources. |

Record the database/process restart boundaries actually tested. Application restart is not proof of power-loss durability, disaster recovery, customer backup readiness, or installation portability. Additional high-value failure checks may be proposed without bloating the packet or silently widening its acceptance claim.

Prefer a small usable Angular upload/status/original-download screen so Jack can demonstrate the slice. No polished extraction-review UI is required yet.

## Evidence and report

Use meaningful focused unit tests for domain state rules and real PostgreSQL integration/acceptance tests for persistence. Report actual discovered/passed/failed/skipped counts, commands, environment, and evidence paths. A high test count is not a quality metric on its own.

Pin base -> code candidate -> evidence (if separate) -> report publication. Show which revision was built/executed; bind observations to the same candidate. Include schema/migration changes and any external database/service setup in the change inventory. Do not put credentials, uploaded private contents, or full machine-environment dumps in logs.

Non-author Carbon review must inspect actual code, tests, and relevant traces, not just the author's narrative. Author checks alone remain ready-for-review. The coordinator's disposition names the candidate and any remaining limitations.

Finish with a short demo receipt: fixture ID/hash, candidate, submit/reference outcome, restart observation, recovered digest/status, and checks not run. Publication, independent acceptance, and merged state must be reported separately.

