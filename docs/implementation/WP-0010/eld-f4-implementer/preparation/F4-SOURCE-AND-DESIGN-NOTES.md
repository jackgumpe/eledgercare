# WP-0010 Author Preparation & Actionable Design Findings (`eld-f4-implementer`)

- **Author / Session / Model**: `eld-f4-implementer` — separate Google DeepMind Gemini 4 Carbon (High) conversation `b7c54417-db09-49bd-8d2b-7cc808f113be` (`gemini-4-carbon-high` / `high`)
- **Worktree / Branch**: `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-f4-implementer` / `feature/wp-0010-f4-archive`
- **Packet Base / Initial Authority / Merged Coordinator Authority**: `956c056be2ec970340074871ecdd7e1a9855d944` -> `8d23d755a35be26ff29c319c527bd770abdcae4b` -> `419159c0c35f8adccae88ca65b5d7d72ccdde729` ([`WP-0010-eld-f4-implementer-preparation.md`](../../../../kickoffs/WP-0010-eld-f4-implementer-preparation.md))
- **Inspected Accepted F3 Source**: `dda4b4d5856ac45105c31ba1d6d6813debdab8a7` (`src` tree `e0dc8651c9fefb228ad26e17f62da6c20fd59ae0`, `web` tree `381d5e754ea7d7e8612c4c19d07f7d7aafb6ffdd`, `tests` tree `838979ed5f81050c2cc7b7938aa9ae5eb641bbbb`, `deploy` tree `4c410b6cff7575a522d38e3c191db33924214841`)
- **Inspected Provisional F4 Design**: [`docs/design/F4-source-linked-archive.md`](../../../../design/F4-source-linked-archive.md) (`01a6dab0695c93246b4cf04d1a2098d3b77248d8`, coordinator report [`WP-0010 / 001`](../../../../agent-reports/eld-coordinator/WP-0010/001_2026-11-17_design_eld-coordinator.md) at `3a59f78df399da449028edb1839be3a5ee457f90`)
- **Gate Status**: **Preparation only.** F4 application implementation and canonical `WP-0010 / 003` remain held until independent `WP-0010 / 002` design acceptance and coordinator implementation release.

---

## 1. Concrete Preparation Requirements Derived from Accepted F3 Source & Provisional F4 Design

To verify forward migration (`F4-05`), projection backfill, browse/search/filter behavior (`F4-01`..`F4-04`), source/history reopening (`F4-06`), and disabled-OCR restart durability (`F4-07`) without running any GPU/OCR worker, the retained pre-F4 seed database `eledgercare_f4_author_seed_f3` on owned PostgreSQL `18.7` (`127.0.0.1:55438`) must be constructed strictly against the **unchanged accepted F3 schema** (`20261114182147_InitialDurableIntake`, `20261116052029_AddLocalExtraction`, `20261116200918_AddWorkOrderReview` + [`grant-runtime.sql`](../../../../../deploy/dev/database/grant-runtime.sql)) and contain:

1. **Genuine accepted WP-0006 F2 extraction artifacts** (`SYN-WO-01-v1-raster300.pdf` 1p raster work order + `SYN-MP-01-v0-clean.pdf` 3p vector statement/invoice) with verified input PDF, raw UTF-8 output, and worker envelope SHA-256s, preserving original UUIDs on primary scenarios (`ids_remapped: false`) and explicitly disclosing deterministic `01a1f400-...` UUID remapping (`ids_remapped: true`) where additional distinct F3 review states are needed, while advancing `eledgercare.extraction_fencing_seq` monotonically (`1..7`) as least-privilege role `eledgercare_app`.
2. **Reviewed revision followed by a newer unapproved draft** (**Seed 1**: Rev `#1` `reviewed` -> Rev `#2` `reviewed` -> Rev `#3` `draft` head) created via real `POST /api/documents/{id}/review/revisions` calls on unchanged `ELedgerCare.Api` (`127.0.0.1:5590`, `LocalOcr:Enabled=false`), exercising:
   - Replacement of superseded Rev `#1` reviewed token (`SUPERSEDED-REV1-BIRCHWOOD`) by active Rev `#2` reviewed token (`REV2-ACTIVE-HAWTHORNE`).
   - Removal of a prior reviewed value (`SUPERSEDED-UNIT-TAG-991`) when Rev `#2` marks `building_unit` `unknown` (`human_value = NULL`, `unknown_reason = "NONSEARCH-UNKNOWN-REASON-PLACARD-772: ..."`), while original machine `"Bldg B - Unit 204"` remains searchable strictly as machine extraction.
   - Literal punctuation, Unicode, leading zeros, and SQL `LIKE` metacharacters (`Café_100%`, `\`, `—`, `0042`).
   - Manual `edited` reviewed field saved with `consultedSource: null` (`consulted_page_number IS NULL` on `issue_and_resolution`, token `MANUAL-NO-PROVENANCE-KESTREL-0042`), verifying F4 never fabricates page coordinates for human-entered values without provenance.
   - Newer `draft` head (`#3`) tokens (`DRAFT-ONLY-UNAPPROVED-JUNIPER-883`, `DRAFT-UNREVIEWED-UNIT-999`) excluded from reviewed search while surfacing `"Newer draft exists"`.
3. **Genuine 3-page multipage completed extraction with zero reviews** (**Seed 2**: `SYN-MP-01-v0-clean.pdf`, `0` review revisions, `unreviewed`) containing per-page anchors (`MP01-P1`, `MP01-P2`, `MP01-P3`), `<td colspan="9">` spanning tables on Pages 2 & 3, and HTML entity `&amp;` (`Tombstone Rewire & Lamp Retrofit`).
4. **Interrupted-then-retried completed extraction with `reviewed` current head** (**Seed 3**: Attempt `#1` `interrupted` + Attempt `#2` `completed`, Rev `#1` `draft` -> Rev `#2` `reviewed` head with `WO-009450` overriding machine `WO-004192` and `REVIEWED-HEAD-SYCAMORE-402`).
5. **Draft-only completed document with zero `reviewed` revisions** (**Seed 4**, `ids_remapped: true`: Rev `#1` `draft` only, token `NEVER-REVIEWED-DRAFT-PINECREST-501`), ensuring `source=reviewed` excludes draft-only documents in both browse and keyword modes.
6. **Genuine 3-page multipage completed document with `reviewed` head & Page 2 / Page 3 table-cell provenance** (**Seed 5**, `ids_remapped: true`: `SYN-MP-01-v0-clean.pdf`, Rev `#1` `reviewed` with server-verified `consultedSource` on Page 2 Block 2 Row 5 Col 1/2 and Page 3 Block 2 Row 5 Col 2, token `MULTIPAGE-REVIEWED-ALDER-P2`), enabling both cross-source AND queries (`MP01-P3` + `MULTIPAGE-REVIEWED-ALDER-P2`) and reviewed `#page=2` / `#page=3` source jumps.
7. **Non-completed submissions (`failed` with diagnostic partial output & `awaiting_extraction` via real `POST /api/documents`)** (**Seed 6** `failed` with `diagnostic_raw_output_utf8` sentinel `NONSEARCH-DIAGNOSTIC-PARTIAL-719` and `failure_detail` sentinel `NONSEARCH-FAILURE-DETAIL-719`; **Seed 7** `F1-SWO-001.pdf` submitted via real `POST /api/documents` in `awaiting_extraction`), proving browse surfaces non-completed jobs honestly while nonempty search never reads `diagnostic_raw_output_utf8`, `failure_detail`, `unknown_reason`, or `operator_display_label`.

---

## 2. Actionable Source-Backed Design Observations (`DF-01`..`DF-05`)

These observations record concrete interactions between the accepted F3 codebase (`419159c0c35f8adccae88ca65b5d7d72ccdde729`) and provisional [`F4-source-linked-archive.md`](../../../../design/F4-source-linked-archive.md). None block author preparation; each has a clear, bounded implementation handling once independent `/002` design review is accepted.

### `DF-01` — Physical-Page Alignment & Spanning/Malformed Table Handling in `SafeNativeDisplayParser`
- **Accepted F3 source**:
  - [`SafeNativeDisplayParser.ParsePages`](../../../../../src/ELedgerCare.Domain/Processing/SafeNativeDisplayParser.cs) (`L16-L51`) splits strictly on literal `<PAGE>` substrings. Although [`ELedgerCareDbContext`](../../../../../src/ELedgerCare.Infrastructure/Persistence/ELedgerCareDbContext.cs) (`L216-L217`) checks `output_page_count = page_count` (`1..3`) from worker envelope metadata, `ParsePages(rawText).Count` can still differ from `result.PageCount` (`0` if `<PAGE>` is absent, or `!= result.PageCount` if raw text contains an extra literal `<PAGE>`).
  - For `<BLOCK>table...<FORK>...` blocks (`L105-L110`), `ExtractedBlockView.Text` retains raw `<table>...</table>` markup (including un-decoded `&amp;` entities such as `Tombstone Rewire &amp; Lamp Retrofit` on `SYN-MP-01` Page 3), whereas `ExtractedBlockView.TableRows` holds entity-decoded cell text produced by `ParsePlainTableRows` (`L137-L248`). Note that `TryParseStrictSimpleTableRows` (`L256-L503`, used for conservative F3 2-column field suggestions) rejects `SYN-MP-01` Pages 2 and 3 because their genuine native output contains `<td colspan="9">`.
  - Conversely, `ParsePlainTableRows` (`L149-L168`) ignores character data outside `<td>`/`<th>` (`if (currentCell is not null)`), so malformed `<BLOCK>table` markup with text outside cells would drop text if `TableRows` were used without a structural completeness check.
- **Concrete F4 handling**:
  1. Bind physical `page_number` (`1..result.PageCount`, `is_fallback = false`) **only when `parsedPages.Count == result.PageCount`**; otherwise emit a document-level fallback projection (`page_number = NULL`, `is_fallback = true`) over decoded raw text so no out-of-range or misaligned page coordinate is fabricated.
  2. Index plain decoded `TableRows` cell text (including spanning `<td colspan="9">` tables in `SYN-MP-01` Pages 2 & 3, with zero `<table>`/`<tr>`/`<td>`/`colspan` tag noise) when `table` markup has balanced table/row/cell tags and no non-whitespace text outside cells; otherwise retain inert raw block text with `is_fallback = true` so unfamiliar or malformed table output is never silently lost.
  3. Persist an explicit per-result projection completion record (`result_id`, `projection_version`, `raw_output_sha256`) even when searchable text is empty so readiness distinguishes empty results from unbackfilled results.

### `DF-02` — Owned PostgreSQL `18.7` `C`-Locale (`--no-locale`) `ILIKE` vs UTF-16 Snippet Slicing
- **Accepted F3 source**:
  - [`deploy/dev/postgres/setup-cluster.ps1`](../../../../../deploy/dev/postgres/setup-cluster.ps1) (`L72-L73`) runs `initdb.exe --encoding=UTF8 --no-locale`, establishing `LC_COLLATE = 'C'` and `LC_CTYPE = 'C'`, while [`Directory.Build.props`](../../../../../Directory.Build.props) (`L13`) enables `<InvariantGlobalization>true</InvariantGlobalization>`.
  - Under PostgreSQL `C` `LC_CTYPE`, `ILIKE ... ESCAPE '\'` folds ASCII `A-Z`/`a-z` case-insensitively and preserves exact UTF-8 code-point matching on non-ASCII characters (e.g., `Café`, `—`).
- **Concrete F4 handling**:
  - Parameterize every escaped literal term (`\`, `%`, `_` escaped with `ESCAPE '\'`) in PostgreSQL `ILIKE`, and pair C# witness/highlight offset locating with matching deterministic ASCII case-folding (` ascii-fold / Ordinal ` comparison) and `Rune` / surrogate-pair boundary checks (`char.IsHighSurrogate` / `char.IsLowSurrogate`) when clipping `<= 240` UTF-16 code units so SQL matches and C# witnesses never diverge or split surrogate pairs.

### `DF-03` — Single-Snapshot `REPEATABLE READ` Archive Queries & `SELECT, INSERT`-Only Backfill Concurrency
- **Accepted F3 source**:
  - Existing F1–F3 read methods use default `READ COMMITTED` standalone queries, whereas [`grant-runtime.sql`](../../../../../deploy/dev/database/grant-runtime.sql) (`L12-L53`) withholds `UPDATE`/`DELETE` on all append-only tables (`extraction_results`, `work_order_review_revisions`, `work_order_review_fields`).
  - [`ExtractionStore.PublishCompletedResultAsync`](../../../../../src/ELedgerCare.Infrastructure/Persistence/ExtractionStore.cs) (`L471-L537`) already commits `processing_jobs`, `execution_attempts`, and `extraction_results` inside one `synchronous_commit = on` transaction guarded by `latest_fencing_token = @token`.
- **Concrete F4 handling**:
  - Run `GET /api/archive` inside an explicit `IsolationLevel.RepeatableRead` (`READ ONLY`) transaction so document selection, `MAX(revision_number) FILTER (WHERE status = 'reviewed')` per document, `"Newer draft exists"` head status, and snippet witnesses observe a single MVCC snapshot without blocking writers.
  - Keep new archive projection table(s) strictly `SELECT, INSERT` for `eledgercare_app`: publish new projections atomically inside `PublishCompletedResultAsync` under the existing fencing guard, and handle two-initializer backfill (`F4-05`) via per-result transactions using `INSERT ... ON CONFLICT DO NOTHING` + read-back verification of `raw_output_sha256` and projected rows (raising a diagnostic conflict error on any mismatch without requiring `UPDATE` privileges).

### `DF-04` — Route Validation, Unsaved-Edit Guard Preservation, & Null-Provenance Reviewed Hits
- **Accepted F3 source**:
  - [`app.routes.ts`](../../../../../web/src/app/app.routes.ts) (`L6-L22`) protects `/documents/:documentId/review` and `/documents/:documentId/review/revisions/:revisionNumber` with `canDeactivate: [unsavedReviewChangesGuard]`, and [`pdf-preview-url.ts`](../../../../../web/src/app/review/pdf-preview-url.ts) restricts iframe preview URLs strictly to `/api/documents/<uuid>/preview#page=<1..pageCount>`.
  - [`SaveWorkOrderReviewRevision.cs`](../../../../../src/ELedgerCare.Application/Review/SaveWorkOrderReviewRevision.cs) (`L190-L208`) stores `consulted_page_number = NULL` when an `edited` field has `consultedSource = null`.
- **Concrete F4 handling**:
  - Register `/archive` before wildcard `'**'`, preserve `unsavedReviewChangesGuard` on all review transitions, encode search/return state in URL query parameters (`q`, `source`, `returnQ`, `returnSource`) with `switchMap` / request-token cancellation for obsolete UI responses, validate `page` (`1..pageCount`) and `field` (`WorkOrderReviewSchema.TryGetField`), and omit `#page=` source jumps whenever `consulted_page_number IS NULL`.

### `DF-05` — Card Display Title & Non-Searchable Column Isolation
- **Accepted F3 source**:
  - [`DocumentEndpoints.SubmitAsync`](../../../../../src/ELedgerCare.Api/DocumentEndpoints.cs) (`L27-L91`) accepts raw PDF bytes without any client filename (`eledgercare.documents` has only `document_id`, `idempotency_key`, `submitted_at`).
- **Concrete F4 handling**:
  - Display latest `reviewed` `work_order_id` / `property_name` (`decision IN ('accepted','edited')`) when present and fall back to short document ID + `submitted_at` UTC otherwise (never using unreviewed `draft` fields as reviewed card titles), and restrict keyword `ILIKE` predicates exclusively to projection text and active-reviewed `human_value` columns.
