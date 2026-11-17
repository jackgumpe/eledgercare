# WP-0010 / 002: Independent review of F4 source-linked archive retrieval design

- Report path: `docs/agent-reports/eld-f4-reviewer/WP-0010/002_2026-11-17_review_eld-f4-reviewer.md`
- Sequence reservation: `WP-0010 / 002` in [INDEX.md](../../../../INDEX.md) at `8d23d755a35be26ff29c319c527bd770abdcae4b` / `01a6dab0695c93246b4cf04d1a2098d3b77248d8`; bound kickoff [WP-0010-eld-f4-reviewer-design.md](../../../kickoffs/WP-0010-eld-f4-reviewer-design.md) (`8a7fd82e6d504da5da5a5898440eae55c9031973`)
- Category: review
- Author / agent ID: `eld-f4-reviewer`
- Actual model / effort: Gemini 4 Carbon (High), high effort (fresh independent Antigravity CLI conversation `61105d43-7706-45f2-9176-69d3256248e0`; backend checkpoint identifier not separately exposed)
- Execution environment: CLI (`Antigravity CLI` on Windows x64 PowerShell; conversation `61105d43-7706-45f2-9176-69d3256248e0`; Git `2.55.0.windows.1`; CPython `3.12.10`; `.NET SDK 10.0.403`; Node `v24.18.0`)
- Published by: `eld-f4-reviewer`
- Timestamp: 2026-11-17T08:40:00Z
- Repository / branch: private `https://github.com/jackgumpe/eledgercare` / `review/wp-0010-f4` (owned worktree `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-f4-reviewer`)
- Base revision: `3a59f78df399da449028edb1839be3a5ee457f90` (clean fast-forwarded coordinator `/001` publication `HEAD`; initial branch authority `8d23d755a35be26ff29c319c527bd770abdcae4b`; packet base `956c056be2ec970340074871ecdd7e1a9855d944`)
- Deliverable revision: `0584e68d7fa494e1d8c442a9642c9e1edbbe5655` (frozen review dossier, preparation receipt, and verification helper; post-freeze verification evidence and inventory `9af6a521eea1b74d3e7230e671034453b4558d8a`); reviewed root design candidate `01a6dab0695c93246b4cf04d1a2098d3b77248d8` (coordinator `/001` publication `3a59f78df399da449028edb1839be3a5ee457f90`)
- Previous report: none (first report in fresh independent conversation `61105d43-7706-45f2-9176-69d3256248e0`; prior accepted F3 final review [WP-0008 / 007](../../eld-f3-reviewer/WP-0008/007_2026-11-16_review_eld-f3-reviewer.md) at `299b9ee81528191e4d964b9e22745f477f2c4e8c` referenced as input baseline only)
- Related or reviewed reports: [WP-0010 / 001](../../eld-coordinator/WP-0010/001_2026-11-17_design_eld-coordinator.md) (`3a59f78df399da449028edb1839be3a5ee457f90`); [WP-0008 / 005](../../eld-coordinator/WP-0008/005_2026-11-16_verification_eld-coordinator.md) (`3282b9db7b7f05bbb14fd000591a732bbda581bc`); [WP-0008 / 007](../../eld-f3-reviewer/WP-0008/007_2026-11-16_review_eld-f3-reviewer.md) (`299b9ee81528191e4d964b9e22745f477f2c4e8c`); [WP-0006 / 004](../../eld-next-reviewer/WP-0006/004_2026-11-16_review_eld-next-reviewer.md) (`c854a1d4c306c3b10d78df42a1a2552a06bb4a98`)
- Status: accepted
- Next owner: `eld-coordinator` (reconcile/bind and dispatch `WP-0010 /003` `eld-f4-implementer` release incorporating `F4-KR-01` and carrying `F4-BIC-01`..`08` into `/003`–`/004`)

## Summary

Independent non-author product design review (`WP-0010 / 002`) **ACCEPTS** frozen root design candidate **`01a6dab0695c93246b4cf04d1a2098d3b77248d8`** ([F4-source-linked-archive.md](../../../design/F4-source-linked-archive.md), blob `f821581ccb32d545bed51a80f316613286ead3bf`) and coordinator report [WP-0010 / 001](../../eld-coordinator/WP-0010/001_2026-11-17_design_eld-coordinator.md) (`3a59f78df399da449028edb1839be3a5ee457f90`, blob `fe3532d6e3e2ac4e9ba89b94dad68c8493dffced`).

- **Zero concrete design blockers** (`0` contradictions) were found against accepted `F1`–`F3` product source (`dda4b4d5856ac45105c31ba1d6d6813debdab8a7`), recorded in [preparation-findings.md](../../../reviews/WP-0010/eld-f4-reviewer/design/preparation-findings.md) and [design/README.md](../../../reviews/WP-0010/eld-f4-reviewer/design/README.md).
- One `/003` kickoff path binding (`F4-KR-01`: `deploy/dev/**` ownership for `grant-runtime.sql` projection privileges and parameterized `5590/4610/55438` vs. `5690/4710/55439` port defaults) and eight source-pinned implementation checkpoints (`F4-BIC-01`..`08`) are documented with observable acceptance criteria for `WP-0010 /003`–`/004` without modifying the reviewed design contract.
- **Design vs. Application Acceptance:** This report accepts the F4 design contract only; F4 application acceptance awaits `/003` implementation and independent `/004` runtime verification.
- **Independence and Non-Access Attestation:** Fresh conversation `61105d43-7706-45f2-9176-69d3256248e0` authored zero files in `01a6dab0...` or prior packets, edited no product or shared-routing files, started no services or GPU/model processes, invoked no subagents, made no network downloads, and accessed **zero** `WP-0011` diagnostic/custodian or `WP-0009` sealed paths.

## Objective and acceptance criteria

1. Verify Git lineage (`956c056b...` -> `8d23d755...` -> `01a6dab0...` -> `3a59f78d...`), exact 7-path authority and 9-path candidate diffs, single-file `/001` report commit, and byte-identical preservation of all product, worker, qualification, research, evaluation, and historical report trees.
2. Audit [F4-source-linked-archive.md](../../../design/F4-source-linked-archive.md) against actual accepted F3 source across query/matching semantics, SQL `LIKE`/`ILIKE` metacharacter escaping and PostgreSQL 18.7 collation, bounded snippets and keyset pagination, latest reviewed revision vs. newer draft isolation, unknown removal and pinned historical links, source/provenance navigation, transactional snapshot consistency, immutable machine projection and competing-initializer backfill, existing extraction fences, startup with `LocalOcr:Enabled=false`, PostgreSQL least privilege, and independent test coverage (`F4-01`..`08`).
3. Freeze the verification helper before decisive execution, commit deliverables (`0584e68d...`) and post-freeze evidence/inventory (`9af6a521...`) before this single-file canonical report, push `review/wp-0010-f4` without force, and verify exact `origin` publication.

## Change inventory

### Base-to-Deliverable Diff (`3a59f78df399da449028edb1839be3a5ee457f90..0584e68d7fa494e1d8c442a9642c9e1edbbe5655`)

| Action | Exact path or external resource | What changed and why | Relevant symbols / sections |
| --- | --- | --- | --- |
| Added (`0584e68d...`) | [preparation-findings.md](../../../reviews/WP-0010/eld-f4-reviewer/design/preparation-findings.md) | Prompt preparation/blocker receipt recording `0` concrete design blockers, `accepted` design verdict, `F4-KR-01`, and `F4-BIC-01`..`08` summary | Concrete Design Blockers; Kickoff Binding & Checkpoints |
| Added (`0584e68d...`) | [README.md](../../../reviews/WP-0010/eld-f4-reviewer/design/README.md) | Full primary-source design review dossier pinning code/schema/collation findings, `F4-KR-01`, and `F4-BIC-01`..`08` | Sections 1–3 |
| Added (`0584e68d...`) | [verify_f4_design.py](../../../reviews/WP-0010/eld-f4-reviewer/design/verify_f4_design.py) | Frozen pure-stdlib CPU verification helper checking Git diffs/preservation, genuine F2 projections, `C`-locale `ILIKE` escaping, revision/draft/unknown/AND/cursor/surrogate/XSS/initializer invariants, 24-port disjointness, WP-0011 refusal, and Markdown links | `SafeRepoReader`, `build_machine_projection`, `postgres_c_ilike_evaluate`, `clip_surrogate_safe_witness_snippet`, `ArchiveSimulator`, `main` |

### Post-Deliverable Evidence, Report Metadata, Scratch, and External Effects

- Added (`9af6a521eea1b74d3e7230e671034453b4558d8a`):
  - [verification-receipt.json](../../../reviews/WP-0010/eld-f4-reviewer/design/verification-receipt.json) — decisive post-freeze verification output generated against clean frozen `HEAD = 0584e68d7fa494e1d8c442a9642c9e1edbbe5655` (`56 / 56` assertions passed).
  - [inventory.json](../../../reviews/WP-0010/eld-f4-reviewer/design/inventory.json) — complete SHA-256 and Git blob/tree inventory of all 3 deliverable files and 9 preserved repository trees.
- Added (single-file report commit immediately following `9af6a521eea1b74d3e7230e671034453b4558d8a`): `docs/agent-reports/eld-f4-reviewer/WP-0010/002_2026-11-17_review_eld-f4-reviewer.md`.
- Ignored `.scratch/` files in owned worktree (`.gitignore` L25): `.scratch/pre-freeze-receipt.json`, `.scratch/report-link-check.json`.
- External effects: fast-forward of owned `review/wp-0010-f4` from `8d23d755a35be26ff29c319c527bd770abdcae4b` to `3a59f78df399da449028edb1839be3a5ee457f90`, followed by normal non-force push of `review/wp-0010-f4` to `origin`; zero database, service, GPU, model, network-download, or shared-checkout changes.

## Decisions and rationale

Full line-pinned code analysis lives in [design/README.md](../../../reviews/WP-0010/eld-f4-reviewer/design/README.md):

1. **Query bounds, `ESCAPE '\'` metacharacter escaping, & `C`-locale collation parity (`F4-BIC-01`):**
   - [setup-cluster.ps1](../../../../deploy/dev/postgres/setup-cluster.ps1) (`L73`) initializes PostgreSQL 18.7 with `--encoding=UTF8 --no-locale` (`LC_CTYPE = C`), giving ASCII `A–Z`/`a–z` case-folding and exact UTF-8 code-point matching on non-ASCII characters. Escaping `\` -> `\\`, `%` -> `\%`, `_` -> `\_` with `ILIKE @p ESCAPE '\'`, validating raw percent-encoded UTF-8 query strings plus UTF-16/surrogate/control/parameter bounds (`<= 8` terms, `<= 64` per term, `<= 160` total), and aligning C# witness matching to SQL `C`-locale `ILIKE` prevents SQL-vs-.NET witness mismatches.
2. **Machine projection over `SafeNativeDisplayParser`, fallbacks, & `U+0000` safety (`F4-BIC-02`):**
   - Genuine WP-0006 F2 raw outputs for `SYN-WO-01` (`7503761a...`, `1` page) and `SYN-MP-01` (`c399ad89...`, `3` pages including `colspan` tables on Pages 2–3) project cleanly through [SafeNativeDisplayParser.cs](../../../../src/ELedgerCare.Domain/Processing/SafeNativeDisplayParser.cs) (`L16–248`) onto physical pages `1..3` without structural HTML tags. Retaining `is_fallback = true` text when `table` blocks have `TableRows.Count == 0`, unclosed tags, or non-cell text (`<caption>`/stray text dropped by `ParsePlainTableRows` `L149–160`), emitting `page_number = NULL` fallback when `<PAGE>` boundaries are missing/mismatched, sanitizing `\0` -> `U+FFFD` for PostgreSQL `text` without length truncation, and using whitespace-only delimiters (`\t`/`\n`, never `|`) prevents silent text loss, PostgreSQL `22021` failures, and false punctuation matches.
3. **Latest reviewed revision vs. newer draft, single-snapshot consistency, & fenced backfill (`F4-BIC-03`..`05`):**
   - Selecting the greatest `revision_number` with `status = 'reviewed'` (`decision IN ('accepted', 'edited') AND human_value IS NOT NULL`) cleanly separates reviewed search values and card titles from unreviewed drafts (`"Newer draft exists"` when `current_status = 'draft'` and `current_revision_number > latest_reviewed.revision_number`) and removes superseded values marked `unknown`.
   - Running `GET /api/archive` inside one `REPEATABLE READ READ ONLY` transaction guarantees single-snapshot consistency without blocking writers. Storing a parent completion marker (`unit_count >= 0`, `projection_sha256`) + child unit rows inside [ExtractionStore.cs](../../../../src/ELedgerCare.Infrastructure/Persistence/ExtractionStore.cs) `PublishCompletedResultAsync` (`L471–537`) after existing job/attempt fencing checks, granting `eledgercare_app` `SELECT, INSERT` only in [grant-runtime.sql](../../../../deploy/dev/database/grant-runtime.sql) (`F4-KR-01`), and reconciling `23505` initializer races via `projection_sha256` while failing closed (`503`) on conflicts or unprojected rows satisfies all durability and privilege invariants.
4. **Keyset cursor precision, surrogate-safe `<= 240` snippets, navigation, & disjoint ports (`F4-BIC-06`..`08`):**
   - Microsecond-exact `timestamptz` + RFC 4122 lowercase UUID tuple paging (`LIMIT limit + 1`) bound to normalized `(q, source)` SHA-256, inward surrogate-safe `<= 240` UTF-16 snippet clipping rendered solely via Angular text interpolation (`0` `innerHTML`), inline readable PDF `#page=N` preview on [document-page.ts](../../../../web/src/app/intake/document-page.ts), provenance-gated page links and pinned revision history on [work-order-review-page.ts](../../../../web/src/app/review/work-order-review-page.ts) preserving unsaved memory edits, and 24-port disjointness (`5590/4610/55438` author; `5690/4710/55439` reviewer) are fully compatible with accepted `F1`–`F3` code.

## Verification

### Inspected vs. Executed Checks

| Check / exact command or operation | Mode, environment, and revision | Actual result | Evidence location |
| --- | --- | --- | --- |
| Primary-source inspection of `F4-source-linked-archive.md`, `WP-0010 /001`, `src/**`, `web/**`, `deploy/**`, `tests/**`, and genuine WP-0006 F2 raw outputs (`SYN-WO-01`, `SYN-MP-01`) | **Inspected** (read-only in `eld-f4-reviewer` at `3a59f78df399da449028edb1839be3a5ee457f90`) | Confirmed `0` blocking design contradictions against accepted F3 source `dda4b4d5856ac45105c31ba1d6d6813debdab8a7`; documented `F4-KR-01` and `F4-BIC-01`..`08` | [preparation-findings.md](../../../reviews/WP-0010/eld-f4-reviewer/design/preparation-findings.md), [design/README.md](../../../reviews/WP-0010/eld-f4-reviewer/design/README.md) |
| Pre-freeze helper dry-runs (`python -B docs/reviews/WP-0010/eld-f4-reviewer/design/verify_f4_design.py --output .scratch/pre-freeze-receipt.json`) | **Executed** (CPU/Python `3.12.10` pre-freeze at `3a59f78df399da449028edb1839be3a5ee457f90`) | **Exit `0`:** `53/53` then `54/54` assertions passed after adding active `SafeRepoReader` `PermissionError` probe checks; zero pre-freeze failures occurred | `.scratch/pre-freeze-receipt.json` (retained in ignored `.scratch/`) |
| Decisive post-freeze verification (`python -B docs/reviews/WP-0010/eld-f4-reviewer/design/verify_f4_design.py --require-clean --output docs/reviews/WP-0010/eld-f4-reviewer/design/verification-receipt.json --inventory-output docs/reviews/WP-0010/eld-f4-reviewer/design/inventory.json`) | **Executed** (CPU/Git/Python `3.12.10` on clean frozen `HEAD` `0584e68d7fa494e1d8c442a9642c9e1edbbe5655`, helper SHA-256 `e1163edcbe9e111db6f7b69f62b606ec515c3dd0a6efc68f0d7b6aa20875832f`) | **Exit `0`:** `56 / 56` assertions passed (exact 7-path authority & 9-path candidate diffs, single-file `/001` report commit, 9 preserved trees + F3 parity, 68 unchanged historical report files, genuine F2 projections + caption/`\0`/empty/missing-`<PAGE>` fallbacks, `C`-locale `ILIKE` escaping, 14 invalid-query rejections + astral UTF-16 cap, surrogate-safe `<= 240` snippet + XSS segments, `503` readiness/conflict + two-initializer reconciliation + fenced rollback + multi-revision/draft/unknown/cross-source-AND/keyset simulation, 24 disjoint ports, 50 Markdown links, active WP-0011 refusal, `0` sealed paths opened) | [verification-receipt.json](../../../reviews/WP-0010/eld-f4-reviewer/design/verification-receipt.json), [inventory.json](../../../reviews/WP-0010/eld-f4-reviewer/design/inventory.json) (`9af6a521eea1b74d3e7230e671034453b4558d8a`) |
| Canonical report link & whitespace check (`python -B .../verify_f4_design.py --extra-md docs/agent-reports/eld-f4-reviewer/WP-0010/002_2026-11-17_review_eld-f4-reviewer.md --output .scratch/report-link-check.json` + `git diff --cached --check`) | **Executed** (CPU/Git/Python `3.12.10` at `9af6a521eea1b74d3e7230e671034453b4558d8a`) | **Exit `0`:** all local Markdown links in dossier, preparation receipt, design, `/001`, and this `/002` report resolved; zero whitespace issues | `.scratch/report-link-check.json` & Git commit history on `review/wp-0010-f4` |

### Checks Not Run and Why

- **`.NET` build/tests, PostgreSQL `18.7` cluster/migration, Angular `ng serve`, and Playwright Microsoft Edge E2E:** Not run in `/002`; no F4 application code exists yet and starting services is prohibited in `/002` by [WP-0010-eld-f4-reviewer-design.md](../../../kickoffs/WP-0010-eld-f4-reviewer-design.md) (scheduled for independent `WP-0010 /004` on `5690/4710/55439` after `/003` implementation freeze).
- **GPU / model inference:** Prohibited; F4 product acceptance uses attributed genuine WP-0006 F2 extraction seeds with `LocalOcr:Enabled=false` and zero GPU/model runs.
- **`WP-0011` diagnostic protocol, mapper, or custodian sealed fixtures:** Out of product-reviewer scope and procedurally sealed.

## Review map

- Reviewed root candidate (`01a6dab0695c93246b4cf04d1a2098d3b77248d8`): [F4-source-linked-archive.md](../../../design/F4-source-linked-archive.md) (`f821581ccb32d545bed51a80f316613286ead3bf`), [WP-0010-eld-f4-reviewer-design.md](../../../kickoffs/WP-0010-eld-f4-reviewer-design.md) (`8a7fd82e6d504da5da5a5898440eae55c9031973`), and [WP-0010-0011-authority.md](../../../coordination/WP-0010-0011-authority.md) (`3479b028d80d75f246233ef286fd000864708fa7`).
- Reviewed coordinator `/001` report (`3a59f78df399da449028edb1839be3a5ee457f90`): [WP-0010 / 001](../../eld-coordinator/WP-0010/001_2026-11-17_design_eld-coordinator.md) (`fe3532d6e3e2ac4e9ba89b94dad68c8493dffced`).
- Reviewer frozen deliverable (`0584e68d7fa494e1d8c442a9642c9e1edbbe5655`): [preparation-findings.md](../../../reviews/WP-0010/eld-f4-reviewer/design/preparation-findings.md) (`6ab690428aff57b4863add6caa27025de0d052c6`), [design/README.md](../../../reviews/WP-0010/eld-f4-reviewer/design/README.md) (`3cbb36c90a13941529773c1ed1a367d7ff2133fd`), and [verify_f4_design.py](../../../reviews/WP-0010/eld-f4-reviewer/design/verify_f4_design.py) (`3a9868cf58ea1b4502408c7b789b6d28d7f9c932`).
- Post-freeze verification evidence and inventory (`9af6a521eea1b74d3e7230e671034453b4558d8a`): [verification-receipt.json](../../../reviews/WP-0010/eld-f4-reviewer/design/verification-receipt.json) and [inventory.json](../../../reviews/WP-0010/eld-f4-reviewer/design/inventory.json).

## Risks, disagreements, and unfinished work

- **Substantive design disagreements or blockers:** **None** (`0` concrete blockers; no coordinator rewrite of `F4-source-linked-archive.md` required before `/003`).
- **Carried-forward implementation & acceptance gates (`WP-0010 /003`–`/004`):**
  1. Coordinator binds `deploy/dev/**` path ownership (`F4-KR-01`) in `docs/kickoffs/WP-0010-eld-f4-implementer.md`.
  2. Implementer (`/003`) and independent reviewer (`/004`) execute and verify `F4-01`..`08` and `F4-BIC-01`..`08` against real PostgreSQL `18.7` (`5590/4610/55438` author; `5690/4710/55439` reviewer) and actual Microsoft Edge, including readable rendered source PDF pages, exact historical revision reopening, two-initializer backfill + fenced atomic publish, `REPEATABLE READ` snapshot consistency, least-privilege denials, and API + PostgreSQL restart with `LocalOcr:Enabled=false`.

## Handoff

- **Disposition:** **`accepted`** on frozen root design candidate `01a6dab0695c93246b4cf04d1a2098d3b77248d8` (`docs/design/F4-source-linked-archive.md`, blob `f821581ccb32d545bed51a80f316613286ead3bf`) and coordinator report `WP-0010 / 001` (`3a59f78df399da449028edb1839be3a5ee457f90`). Publication is design acceptance only, not F4 application acceptance.
- **Next owner:** `eld-coordinator` (update `INDEX.md` / `CURRENT.md` and bind/dispatch `WP-0010 /003` `eld-f4-implementer` incorporating `F4-KR-01` and `F4-BIC-01`..`08`).
- **Owned branch:** `review/wp-0010-f4`
- **Base SHA:** `3a59f78df399da449028edb1839be3a5ee457f90` (packet base `956c056be2ec970340074871ecdd7e1a9855d944`, authority `8d23d755a35be26ff29c319c527bd770abdcae4b`)
- **Reviewed design candidate SHA:** `01a6dab0695c93246b4cf04d1a2098d3b77248d8`
- **Frozen review deliverable SHA:** `0584e68d7fa494e1d8c442a9642c9e1edbbe5655`
- **Post-freeze verification evidence & inventory SHA:** `9af6a521eea1b74d3e7230e671034453b4558d8a`
- **Report path:** `docs/agent-reports/eld-f4-reviewer/WP-0010/002_2026-11-17_review_eld-f4-reviewer.md`
- **Publication receipt:** Committed as a single-file report-only commit immediately following `9af6a521eea1b74d3e7230e671034453b4558d8a`, pushed without force on `review/wp-0010-f4`, verified on `origin` via `git ls-remote`, and its exact publication SHA is returned in the handoff message to `eld-coordinator`.
