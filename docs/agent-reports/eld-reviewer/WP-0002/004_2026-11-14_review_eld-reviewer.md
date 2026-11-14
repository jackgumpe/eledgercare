# WP-0002 / 004: Independent verification and closure of bounded F1 design corrections

- Report path: `docs/agent-reports/eld-reviewer/WP-0002/004_2026-11-14_review_eld-reviewer.md`
- Sequence reservation: coordinator `INDEX.md` at `4ecc3ffe1d2842decf19ecdcfec0f5424fb4ac8b`, `WP-0002 / 004`; bound kickoff `docs/kickoffs/WP-0002-eld-reviewer-reconciliation.md` at `dfb2fad6a357324d02303d48fbf73139b943afdb`
- Category: review
- Author / agent ID: `eld-reviewer`
- Actual model / effort: Google DeepMind Gemini 4 Carbon, high effort (exposed via Antigravity session model-selection metadata in continued conversation `780ff7d0-276e-490c-b280-f6df87c57404`; raw backend checkpoint identifier not separately exposed)
- Execution environment: Antigravity CLI on Windows x64 (`pwsh` / PowerShell; continued session `780ff7d0-276e-490c-b280-f6df87c57404`; Git `2.55.0.windows.1`; Python `3.12.10`)
- Published by: `eld-reviewer` using the existing configured Git author identity, unchanged
- Timestamp: 2026-11-14T17:36:00Z
- Repository / branch: `jackgumpe/eledgercare` (PRIVATE) / `review/wp-0002-contract` (worktree `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-reviewer`)
- Base revision: `266a80bf7a123496ef0d0c848fbd521b117f4543`
- Deliverable revision: `04b08ed3a04daa17f32624878bd5051153b3b801` (own-branch correction-closure matrix on `review/wp-0002-contract`); reviewed corrected design candidate `bce84931fef5cf2a8fa3652095dbea2973a19aef` (inspected read-only via `git show`/`git diff`, unchanged; prior reviewed candidate `e90c71817bc793dfbfc7576006be3cbf0b4310bf`)
- Previous report: `WP-0002 / 002` ([002_2026-11-14_review_eld-reviewer.md](002_2026-11-14_review_eld-reviewer.md) at `266a80bf7a123496ef0d0c848fbd521b117f4543`, unchanged)
- Related or reviewed reports: `WP-0002 / 001` (`9b49c0f330ea5a71263432cbc3f785b51767b304`); `WP-0002 / 002` ([002_2026-11-14_review_eld-reviewer.md](002_2026-11-14_review_eld-reviewer.md) at `266a80bf7a123496ef0d0c848fbd521b117f4543`); `WP-0002 / 003` (`docs/agent-reports/eld-coordinator/WP-0002/003_2026-11-14_verification_eld-coordinator.md` at `dfb2fad6a357324d02303d48fbf73139b943afdb`)
- Status: accepted
- Next owner: `eld-coordinator` (reserved `WP-0002 / 005` final design disposition and held `WP-0003 / 001` Opus release rebinding)

## Summary

Bounded independent non-author correction review (`WP-0002 / 004`) of frozen corrected startup design candidate `bce84931fef5cf2a8fa3652095dbea2973a19aef`, following `WP-0002 / 002` (`266a80bf7a123496ef0d0c848fbd521b117f4543`) and coordinator correction/disposition `WP-0002 / 003` (`dfb2fad6a357324d02303d48fbf73139b943afdb`).

**Verdict on corrected candidate `bce84931fef5cf2a8fa3652095dbea2973a19aef`: `accepted`.**

All three substantive blockers from `/002` (`SB-01`, `SB-02`, `SB-03`) are **closed** in `bce84931fef5cf2a8fa3652095dbea2973a19aef:docs/design/F1-durable-intake.md` (Git blob `18476f0c0f1fa7b0f1db99d4404a6ac30085c572`). All six bounded implementation checks (`BIC-01` through `BIC-06`) are accurately carried forward as **unexecuted** bootstrap and implementation obligations, including the coordinator's refined `BIC-03` evidence rule prohibiting claims of completed earlier insertion from relation lock mode or timing alone. Optional items `OPT-01` (keeping `page_count` internal) and `OPT-02` (consistent canonical 36-character non-empty `D` UUID validation on `GET` routes) are cleanly adopted; `OPT-03` (browser digest caching) remains intentionally deferred.

Independence and execution-scope disclosure: this report continues the same independent `eld-reviewer` session (`780ff7d0-276e-490c-b280-f6df87c57404`), did not author any part of `bce84931fef5cf2a8fa3652095dbea2973a19aef`, left `/002` and `INDEX.md`/`CURRENT.md` untouched, and did not read `research/wp-0004-*` branches or worktrees. **All checks in `/004` are deterministic Git diff/tree/blob inspections — zero application builds, dependency restores, database startups, PDF parser runs, or tests have been executed.**

## Objective and acceptance criteria

1. Inspect corrected candidate `bce84931fef5cf2a8fa3652095dbea2973a19aef` against prior candidate `e90c71817bc793dfbfc7576006be3cbf0b4310bf` read-only from `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-reviewer` on `review/wp-0002-contract` without merging coordinator files into the review branch or modifying `/002`.
2. Verify complete, contradiction-free closure of `SB-01`, `SB-02`, and `SB-03` in `docs/design/F1-durable-intake.md`.
3. Verify that `BIC-01` through `BIC-06` are carried forward as unexecuted implementation obligations (never misreported as executed) and evaluate whether `BIC-03`'s lock/statement correlation and boundary-claim restriction is a faithful, precise implementation obligation.
4. Preserve all unexecuted setup, lockfile, build, parser, and OCR runtime qualifications, and return `accepted` or `changes-requested` for `bce84931fef5cf2a8fa3652095dbea2973a19aef`.

## Change inventory

| Action | Exact path or external resource | What changed and why | Relevant symbols / sections |
| --- | --- | --- | --- |
| Added (deliverable `04b08ed3a04daa17f32624878bd5051153b3b801`) | `docs/reviews/WP-0002/eld-reviewer/correction-closure/sb-closure-and-bic-matrix.md` | Deterministic reconciliation matrix verifying `e90c7181..bce84931` tree integrity, `SB-01..03` closure, and `BIC-01..06` / `OPT-01..03` carry-forward | Sections 1–3 |
| Unchanged | Prior `/002` dossier and report (`266a80bf7a123496ef0d0c848fbd521b117f4543`); inspected candidate `bce84931fef5cf2a8fa3652095dbea2973a19aef` | Immutable prior review artifacts and coordinator candidate preserved untouched | [002_2026-11-14_review_eld-reviewer.md](002_2026-11-14_review_eld-reviewer.md), [pdfpig-and-contract-evidence.md](../../../reviews/WP-0002/eld-reviewer/pdfpig-and-contract-evidence.md) |

Post-deliverable report metadata committed separately on `review/wp-0002-contract`:

- Added `docs/agent-reports/eld-reviewer/WP-0002/004_2026-11-14_review_eld-reviewer.md` (this report; its own publication SHA is verified on `origin` after commit/push and supplied in the handoff message).

Local ignored scratch artifacts added in `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-reviewer\.scratch\`:

- `.scratch/verify_wp0002_004_closure.py`, `.scratch/wp0002-004-closure-verification.json`.

External effects:

- Committed deliverable `04b08ed3a04daa17f32624878bd5051153b3b801` and this report on `review/wp-0002-contract`, pushed `review/wp-0002-contract` without force to `origin`, and verified remote Git objects via `git ls-remote` and `gh api`.
- Zero `dotnet`, `npm`, `docker`, database, parser, or model commands were run in `/004`; zero machine-state or certificate side effects occurred in this step.

## Decisions and rationale

### 1. Closure of substantive blockers (`SB-01` through `SB-03`)

- **`SB-01` — CLOSED (`docs/design/F1-durable-intake.md` L37, L40, L126 at `bce84931fef5cf2a8fa3652095dbea2973a19aef`)**:
  Step 4 now restricts new-key admission to an exact byte-zero `%PDF-1.0` through `%PDF-1.7` header with trailing EOF/whitespace, explicitly rejecting PDF `2.0`, `FDF`, and leading-junk headers with `422` without turning on `UseLenientParsing`, and `DI-07` mandates testing `PDF 2.0/FDF` rejection. This removes the strict-mode contradiction with `UglyToad/PdfPig@a7bb35662bbbf405efddad50aedc9bcdcf515afc` `FileHeaderParser.cs` while keeping `UseLenientParsing=false` intact across the rest of the parser.
- **`SB-02` — CLOSED (`docs/design/F1-durable-intake.md` L37, L40, L126 at `bce84931fef5cf2a8fa3652095dbea2973a19aef`)**:
  Step 4 now requires immediate `document.IsEncrypted=true -> 422` rejection after `Open` (explicitly naming empty-user-password owner encryption that `PdfPig` opens without throwing) and `document.NumberOfPages` validation (`1..MaxPages -> else 422`) *before* `GetPage(1..NumberOfPages)`. L37 and L40 accurately separate application prohibitions (never reading, returning, or persisting `Page.Text`/`Letters`, running OCR, rendering, executing PDF actions, or fetching network resources) from `PdfPig` internals (glyph/content-stream parsing, local `WindowsSystemFontLister` lookup, `FlateFilter` decompression catch-and-ignore fallback, and `XrefBruteForcer` recovery), require embedded or standard-14 fonts in product fixtures, and expand `DI-07` to cover both encryption forms, over-page-limit inputs, and verified corruption rejection paths.
- **`SB-03` — CLOSED (`docs/design/F1-durable-intake.md` L60, L125 at `bce84931fef5cf2a8fa3652095dbea2973a19aef`)**:
  L60 now transitions `POST /api/documents` to **Submission outcome unknown** (retaining the `sessionStorage` UUID key for status query or same-key retry) on network error, client timeout, **or HTTP `5xx`**, retains the pending key on `429` without classifying the PDF invalid or minting a replacement key, and explicitly preserves prior uncertainty if a subsequent retry receives `429`. `DI-06` requires browser retention/reconciliation evidence on both `5xx` and `429`.

### 2. Carry-forward of `BIC-01` through `BIC-06`, `BIC-03` reconciliation, and `OPT-01..03`

- **All six implementation checks (`BIC-01`..`BIC-06`) are carried forward accurately as unexecuted obligations** (detailed mapping in [sb-closure-and-bic-matrix.md](../../../reviews/WP-0002/eld-reviewer/correction-closure/sb-closure-and-bic-matrix.md) Section 3):
  - `BIC-01` (L52): `DeleteBehavior.Restrict` on artifact/job FKs plus explicit metadata column projection avoiding `bytea` reads on status/reconciliation/digest pre-checks.
  - `BIC-02` (L30, L34): 2-slot `POST /api/documents` concurrency gate (`GET` excluded), strict 36-character canonical `D` non-empty UUID / `415` / declared-length `413` checks before reading the body, and Kestrel `BadHttpRequestException` mapped to `413 ProblemDetails`.
  - `BIC-04` & `BIC-05` (L91, L98): `global.json` `test.runner=Microsoft.Testing.Platform`, `OutputType=Exe` without VSTest packages, `EF Core` / `dotnet-ef` `10.0.15` assembly check on `10.0.14` runtime, `.local/` `PLAYWRIGHT_BROWSERS_PATH` and routed/ignored test outputs, and conditional per-process `--dns-result-order=ipv4first` fallback if the dual-stack npm timeout recurs — all explicitly labeled *"execution checks, not completed setup"*.
  - `BIC-06` (L76, L89, L104, L135): exact PostgreSQL `18.7` binary archive identity/SHA-256, `127.0.0.1` cluster, `scram-sha-256`, and separate migration vs runtime (`INSERT, SELECT` only) credentials — explicitly labeled *"proposed, not qualified"* / *"unexecuted"*.
- **Explicit reconciliation of `BIC-03` (`docs/design/F1-durable-intake.md` L124, L129)**:
  The corrected design specifies `LOCK TABLE processing_jobs IN SHARE MODE` on a harness connection, requires correlating the API's owned connection/statement and granted versus waiting locks (including `documents`), and adds: *"Record whether the evidence establishes a completed earlier insert or only a blocked pre-commit transaction; do not claim a more specific boundary from a timing guess or lock mode alone."*
  **Reviewer decision: accepted as a faithful, strictly more precise implementation obligation.** In PostgreSQL, relation lock modes in `pg_locks` alone do not universally prove prior tuple insertion across every SQL shape (for example, a single multi-table CTE statement acquires `RowExclusiveLock` on earlier target relations during `AcquireExecutorLocks` before inserting tuples, whereas sequential/pipelined EF `INSERT` commands assign a write XID and advance the active `pg_stat_activity` statement to `INSERT INTO processing_jobs` after completing earlier statements). Requiring direct correlation of owned backend statement/XID/lock state and forbidding overclaiming from lock mode or sleep timing alone strengthens evidentiary honesty without adding production crash hooks.
- **Optional items (`OPT-01..03`)**: `OPT-01` (`page_count` internal in `F1`) and `OPT-02` (`GET` UUID route parameter `400` vs `404` validation) are cleanly incorporated at L24; `OPT-03` (browser digest caching) stays deferred at L135.

## Verification

| Check / exact command or tool operation | Environment and revision | Actual result | Evidence location |
| --- | --- | --- | --- |
| `git status --porcelain=v1 --branch`, `git rev-parse HEAD`, `git show dfb2fad...:docs/kickoffs/WP-0002-eld-reviewer-reconciliation.md`, `git show 4ecc3ff...:INDEX.md` | `eld-reviewer` worktree on `review/wp-0002-contract` at `266a80bf7a123496ef0d0c848fbd521b117f4543` | Confirmed clean worktree, exact base `266a80bf...`, authoritative `WP-0002 / 004` reservation, and kickoff scope | [sb-closure-and-bic-matrix.md](../../../reviews/WP-0002/eld-reviewer/correction-closure/sb-closure-and-bic-matrix.md) |
| `git diff -U5 e90c7181... bce84931... -- docs/design/F1-durable-intake.md` and `git show bce84931...:docs/design/F1-durable-intake.md` | Read-only Git object inspection from `eld-reviewer` worktree | Full 137-line corrected design (`18476f0c0f1fa7b0f1db99d4404a6ac30085c572`) and `WP-0002 / 003` disposition (`dfb2fad6...`) inspected line-by-line | [sb-closure-and-bic-matrix.md](../../../reviews/WP-0002/eld-reviewer/correction-closure/sb-closure-and-bic-matrix.md) Sections 1–3 |
| Deterministic Python closure script `.scratch/verify_wp0002_004_closure.py` | Python `3.12.10` in `eld-reviewer` worktree | 22/25 prior blobs unchanged; `F1-durable-intake.md` sole modified design file; `git diff --check` clean; 24/24 `.md` files in `bce84931...` had 0 broken links; 15/15 `SB`/`BIC`/`OPT`/unexecuted-gate assertions passed | `.scratch/wp0002-004-closure-verification.json`; [sb-closure-and-bic-matrix.md](../../../reviews/WP-0002/eld-reviewer/correction-closure/sb-closure-and-bic-matrix.md) |
| `git diff --cached --check` and link verification on deliverable `04b08ed3a04daa17f32624878bd5051153b3b801` and this `/004` report | `eld-reviewer` worktree on `review/wp-0002-contract` | 0 whitespace/EOL warnings; all local relative links verified; `/002` report and dossier verified unchanged | Git history on `review/wp-0002-contract` |

Checks **not** run and why (outside `WP-0002 / 004` design-closure scope; carried to `WP-0003`):

- No PostgreSQL `18.7` binary archive download/hash validation, cluster initialization, or SQL execution.
- No NuGet restore, npm install, lockfile generation, `.NET`/Angular build, `xunit.v3` MTP v2 run, Vitest/Playwright run, or live `PdfPig` runtime test.
- No Python OCR setup, model weight download, or GPU activity.

## Review map

- Reviewed corrected candidate: `bce84931fef5cf2a8fa3652095dbea2973a19aef` (`docs/design/F1-durable-intake.md` blob `18476f0c0f1fa7b0f1db99d4404a6ac30085c572`)
- Prior candidate and coordinator correction receipt: `e90c71817bc793dfbfc7576006be3cbf0b4310bf` and `WP-0002 / 003` at `dfb2fad6a357324d02303d48fbf73139b943afdb`
- Prior `/002` review and primary-source dossier (immutable): [002_2026-11-14_review_eld-reviewer.md](002_2026-11-14_review_eld-reviewer.md) (`266a80bf7a123496ef0d0c848fbd521b117f4543`) and [pdfpig-and-contract-evidence.md](../../../reviews/WP-0002/eld-reviewer/pdfpig-and-contract-evidence.md) (`b279d28879316939b308cf50b8f5cc792a235775`)
- `/004` closure verification deliverable (`04b08ed3a04daa17f32624878bd5051153b3b801`): [sb-closure-and-bic-matrix.md](../../../reviews/WP-0002/eld-reviewer/correction-closure/sb-closure-and-bic-matrix.md)

## Risks, disagreements, and unfinished work

- **Substantive design blockers**: None remaining (`SB-01`, `SB-02`, `SB-03` closed; zero unresolved disagreements requiring escalation).
- **Carried-forward `WP-0003` bootstrap and implementation obligations (`BIC-01`..`BIC-06`)**: All six remain unexecuted and must be evidenced against frozen product code in `WP-0003 / 001` and independently reproduced in `WP-0003 / 002`:
  1. `BIC-01` metadata projection / `DeleteBehavior.Restrict` FKs;
  2. `BIC-02` `POST`-only 2-slot concurrency gate, pre-body validation order, and Kestrel `413 ProblemDetails`;
  3. `BIC-03` `processing_jobs` lock harness with honest statement/XID/lock boundary reporting;
  4. `BIC-04` `global.json` MTP v2 + `OutputType=Exe` runner execution and `10.0.15` over `10.0.14` runtime assembly check;
  5. `BIC-05` `.local/` Playwright browser path, ignored/routed test outputs, and per-process `--dns-result-order=ipv4first` fallback if dual-stack npm timeouts recur;
  6. `BIC-06` PostgreSQL `18.7` Windows binary archive URL/SHA-256 verification, `127.0.0.1` `scram-sha-256` cluster launch, `fsync`/`full_page_writes`/`synchronous_commit` verification, and split migration vs `INSERT, SELECT` runtime roles.
- **Preserved scope and risk boundaries**: `F1` remains a local-only synthetic maintenance-PDF slice (not a hostile-upload sandbox, disaster-recovery proof, or OCR runtime qualification); Python `3.12.10` / RTX 5070 Ti Baidu Unlimited-OCR-2 runtime remains unqualified and out of scope for `F1`.

## Handoff

- **Verdict**: **`accepted`** for exact corrected startup design candidate `bce84931fef5cf2a8fa3652095dbea2973a19aef`.
- **Next owner**: `eld-coordinator` (`WP-0002 / 005` final design disposition, followed by refreshing `eld-implementer`'s `WP-0003 / 001` base SHA and kickoff to the accepted corrected design and carrying `BIC-01`..`BIC-06` and `DI-01`..`DI-08` into product execution).
- **Branch**: `review/wp-0002-contract`
- **Own-branch base SHA**: `266a80bf7a123496ef0d0c848fbd521b117f4543`
- **Reviewed corrected candidate SHA**: `bce84931fef5cf2a8fa3652095dbea2973a19aef`
- **Own-branch closure deliverable SHA**: `04b08ed3a04daa17f32624878bd5051153b3b801`
- **Report path**: `docs/agent-reports/eld-reviewer/WP-0002/004_2026-11-14_review_eld-reviewer.md`
- **Publication receipt**: Committed as a separate metadata commit after deliverable `04b08ed3a04daa17f32624878bd5051153b3b801`, pushed without force on `review/wp-0002-contract`, verified on `origin`, and its exact publication SHA is returned in the handoff message to `eld-coordinator`.
