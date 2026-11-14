# eLedgerCare repository and delivery contract

Prepared 2026-11-14. Direction accepted by Jack; detailed technical profile requires bounded non-author review. This document is an input to the local coordinator, not an existing Git assignment.

## Decisions and limits

- Brand-new eledgercare repository. No legacy product migration or reuse in bootstrap.
- PostgreSQL is selected. Whether eTenantCare already uses it is unknown and immaterial to this feature. Its future migration effort depends on its actual schema, SQL, data, and integrations.
- ASP.NET Core 10, EF Core 10 with Npgsql 10, Angular 22, and a later local Python OCR worker form a modular monolith with a local worker companion.
- One production Visual Studio/.NET solution. Research remains in the same repository with separate environments and dependency graphs. Add a separate research solution only if actual C# research tools need one.
- Sensitive originals, derived text, queries, and operational logs stay in the client environment. No automatic cloud OCR/reasoning fallback.
- Demonstration target: 26 November 2026, maintenance paperwork. First delivery is durable intake; real extraction, document/fields review, and searchable archive follow as separate features. Do not relabel this first slice as the complete Thanksgiving product.
- Small synthetic and explicitly reusable public developer documents are the initial data. Later customer documents require authorized access and their own handling plan. No clinical-document feature is in this release.
- Programming-book material remains the tutoring source. Official docs here support engineering compatibility and implementation decisions, not an invented book lesson. Do not invent chapter references.

## Repository shape

| Location | Responsibility |
|---|---|
| ELedgerCare.slnx | Production .NET projects and their tests |
| src/ELedgerCare.Domain/ | Business concepts and invariants, without EF, HTTP, filesystem, or Python dependencies |
| src/ELedgerCare.Application/ | Use cases and narrowly justified boundaries to external resources |
| src/ELedgerCare.Infrastructure/ | PostgreSQL/EF, original storage, and later worker/search adapters |
| src/ELedgerCare.Api/ | ASP.NET host, endpoints, validation, composition, and later authentication |
| web/ | Angular application and frontend tests |
| workers/ocr/ | Supported production OCR worker; initially a documented boundary, not a mock OCR service |
| contracts/ | Application/worker schemas and examples when needed |
| tests/ | .NET unit/integration and cross-component acceptance checks |
| evaluation/ | Approved fixture manifests, ground truth, small reusable fixtures, and shared scoring definitions |
| research/ | Isolated hypotheses, experiment code/configuration, and result summaries |
| deploy/ | Reproducible development setup and later installation/backup instructions |
| docs/ | FDD model/features, decisions, work packets, coordination, agent reports |

Organize business code within those boundaries by Documents, Intake, Processing, Review, and Archive as features require. Do not create empty classes or generic abstractions merely to populate the tree. One responsibility per type is a design judgment, not a file-count quota. Folder structure alone does not enforce dependencies.

Domain has no outward project dependency; Application depends on Domain; Infrastructure implements needed boundaries using Application/Domain; Api composes the system. Product projects must not reference research code. Evaluation tools may consume public contracts or immutable artifacts; shipping application code must not import evaluation machinery. The release package has explicit contents.

## Toolchain and local resources

Proposed bootstrap pins from intake: .NET SDK 10.0.403 and Node 24.18.0. Pin the SDK deliberately; when strict reproducibility is required, use an explicit roll-forward policy rather than silently selecting any installed SDK. Freeze exact compatible Angular 22, TypeScript, EF Core/Npgsql 10, and stable PostgreSQL versions during bootstrap. Do not adopt previews or upgrade global tools incidentally.

PostgreSQL 18 is a proposed server family, not an observed installation. Choose and record one development launch path after checking what actually works locally. A present Docker client proves neither a usable daemon nor permission to redistribute Docker Desktop to clients. The eventual customer installer is a separate decision. Create only owned databases/volumes, use local credentials outside Git, and do not reuse or alter another application's database.

Python 3.12.10 is installed; the OCR runtime remains unqualified. Baidu's published example uses Python 3.10. Select a separate worker environment from actual dependency/platform evidence. Do not infer Windows compatibility or incompatibility solely from shell examples. No GPU/model setup is required for durable intake.

C: had 65.70 GiB free at intake. Model/data/output storage must be explicitly selected before large downloads. Keep weights, large corpora, secrets, uploads, database contents, and transient caches outside Git. Keep small licensed fixtures, manifests, and compact auditable evidence in Git.

Separate product/research databases, writable directories, ports, and worktrees. Reserve GPU execution to one owner initially; a stale lease record or timeout does not prove a process has stopped. Browser/display VRAM use is an observation, not an out-of-memory finding.

## Compact overall model

A submitted Document has a stable identity and an immutable OriginalArtifact with independently checkable content identity. A ProcessingJob records the durable requested work/status. A future ExecutionAttempt records a particular execution; a job is not an attempt. ExtractionResult and ReviewDecision are separate future concepts, with source-page/cell provenance.

Initial user journey: choose a synthetic maintenance PDF -> submit -> receive a stable document reference -> see its awaiting-extraction status -> restart the application -> retrieve the same reference, status, and original bytes.

Required distinctions:
- submitted original versus extracted/normalized derivative;
- successful durable receipt versus uncertain submission outcome;
- job versus execution attempt;
- awaiting extraction versus actual OCR success;
- observed absence versus inaccessible or unknown;
- published work versus independently accepted work.

Only implement concepts required for the first feature. Keep future concepts in the model without generating speculative classes.

## FDD execution

Use develop-an-overall-model, build-a-feature-list, plan-by-feature, design-by-feature, and build-by-feature as the delivery sequence. The first two are compact inputs here; the coordinator makes them concrete and reviewed. Technical bootstrap supports the feature and does not itself count as a customer outcome.

Feature order:
1. Retain a submitted maintenance document and its processing status across restart.
2. Extract one scanned maintenance-document path through a qualified local OCR runtime.
3. Review source pages alongside extracted fields and record corrections.
4. Find archived documents with source-linked results.
Later: additional deterministic format adapters, permissions and deployment hardening, hybrid semantic search, local reasoning, and qualified R&D promotion. Dependencies can require earlier security work before shared/customer access; “later” is not approval to deploy an unsafe prototype.

The first feature and parallel research are authorized in this kit. The rest is a feature list, not automatic release authority.

## Roles and independence

The receiving coordinator registers actual IDs and sessions. Suggested product-scoped IDs:

| Suggested ID | Starting model / role | Ownership |
|---|---|---|
| eld-coordinator | Astra / coordination and design | New product INDEX, CURRENT, packet release, dispositions |
| eld-implementer | Opus / application implementation | Assigned product branch/worktree |
| eld-reviewer | Carbon / independent product review | Review records and disposable execution evidence |
| eld-rd-astra | Astra / R&D hypotheses | Assigned research branch/worktree |
| eld-rd-carbon | Carbon / R&D challenge and corpus work | Separate research branch/worktree |
| eld-rd-reviewer | Uninvolved Opus session / R&D review | Independent reproduction/review when required |

These are role assignments to test in practice, not measured rankings. Separate the stable identity, role, provider/model, effort, and execution session in reports.

A fresh session does not erase authorship. Product reviewers must not approve their own fixes. An R&D author cannot independently accept joint R&D because they switched role, session, or provider label. A product implementation consuming R&D outputs needs review of the promoted delta; reviewer participation in upstream criteria/data must be disclosed.

Coordinator-authored substantive designs and fixes require non-author review. If the coordinator must make a small closing fix, record that exception and obtain independent review of the fix rather than silently self-accepting it.

Use one review exchange and one evidence reconciliation for substantive disagreements. Then escalate the affected question to Jack with issue category, affected extent, pinned evidence, practical impact, alternatives, and owner. Independent authorized work continues. Routine handoffs do not need Jack's button press.

## Authority, reports, and acceptance

Adopt the reporting convention in 06. The local coordinator is the sole writer for this new repository only. Workspace Ledger's existing codex-cloud index remains unchanged. No unfinished kernel, diagnostic helper, automatic runner, or host-enforcement service is a dependency.

The initial seed has no prior commit and is provisional; record that explicitly. Subsequent packets require full base revisions and pre-reserved identities/paths. Each report inventories all changed files and external effects, with UTC timestamps and actual checks.

Freeze the code candidate before its decisive execution. Add evidence/report metadata afterward without silently changing the tested source. If code changes, bind new evidence to the new candidate. Preserve failed evidence relevant to the disposition. Do not require thousands of trivial tests or tests that merely mirror the implementation; use meaningful behavior and failure-boundary checks.

The coordinator may integrate changes only within their assigned authority after independent review and verification. Published, tested, reviewed, accepted, and merged are distinct states. Missing evidence is a gap, not proof of failure or success.

No raw private transcripts, credentials, or customer documents go in agent reports. The repository remains private unless Jack explicitly chooses otherwise. Public test documents do not imply public source-code publication.

