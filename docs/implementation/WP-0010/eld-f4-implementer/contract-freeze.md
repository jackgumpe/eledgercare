# WP-0010 F4 Contract & Implementation Freeze (`eld-f4-implementer`)

- **Accepted Design Contract**: [`docs/design/F4-source-linked-archive.md`](../../../design/F4-source-linked-archive.md) at `01a6dab0695c93246b4cf04d1a2098d3b77248d8` (coordinator report [`WP-0010 / 001`](../../../agent-reports/eld-coordinator/WP-0010/001_2026-11-17_design_eld-coordinator.md) at `3a59f78df399da449028edb1839be3a5ee457f90`), independently accepted in [`WP-0010 / 002`](../../../agent-reports/eld-f4-reviewer/WP-0010/002_2026-11-17_review_eld-f4-reviewer.md) (`85d879a1adc0ee62090f4c6a5c9a7fb8eb5f3a96`) with `F4-KR-01`, `F4-BIC-01`..`08`, and coordinator clarifications in [`WP-0010-eld-f4-implementer.md`](../../../kickoffs/WP-0010-eld-f4-implementer.md).

## 1. Frozen Constants & Schema Versions

| Identifier | Frozen Value | Source Symbol |
| --- | --- | --- |
| Machine projection version | `archive-machine-projection/1` | `ArchiveSchema.ProjectionVersion` |
| Keyset cursor version | `archive-cursor/1` | `ArchiveSchema.CursorVersion` |
| Raw query ceiling | `2048` UTF-16 code units | `ArchiveSchema.MaxRawQueryStringLength` |
| Trimmed query ceiling | `160` UTF-16 code units | `ArchiveSchema.MaxQueryLength` |
| Term count / length ceilings | `8` terms / `64` UTF-16 code units per term | `ArchiveSchema.MaxTerms`, `MaxTermLength` |
| Page size default / ceiling | `20` / `50` (`LIMIT limit + 1`) | `ArchiveSchema.DefaultLimit`, `MaxLimit` |
| Cursor length ceiling | `256` Base64Url characters | `ArchiveSchema.MaxCursorLength` |
| Witness snippet ceiling | `240` UTF-16 code units (inward surrogate-safe) | `ArchiveSchema.MaxSnippetLength` |
| Witnesses per card ceiling | `8` (`<= 1` per query term, deduplicated) | `ArchiveSchema.MaxWitnessesPerDocument` |
| Machine witness label | `Machine extraction — unreviewed` | `ArchiveSchema.MachineSourceLabel` |

## 2. Query, Collation, Cursor, & Snapshot Semantics

1. **Raw query validation (`ArchiveQueryValidator`)**:
   - Inspects raw `HttpContext.Request.QueryString.Value`, decoding `%XX` runs via strict UTF-8 (`throwOnInvalidBytes: true`) so malformed hex escapes (`%2`, `%ZZ`) and invalid UTF-8 sequences (`%FF`, `%C3%28`, CESU-8 surrogates `%ED%A0%80`) fail with `400 Bad Request` (`invalid_archive_query`) rather than coercing to `U+FFFD`.
   - Rejects unknown parameter names (anything outside `q`, `source`, `limit`, `after` Ordinal), duplicate parameters, `\0`, unpaired UTF-16 surrogates, and control characters other than `\t`, `\r`, `\n`.
   - Escapes `\ -> \\`, `% -> \%`, `_ -> \_` and binds every literal term as `@termN` with explicit `ILIKE @termN ESCAPE '\'`.
2. **PostgreSQL `18.7` `LC_CTYPE = C` parity (`CLocaleTextMatcher`)**:
   - Worktree clusters initialize with `initdb --encoding=UTF8 --no-locale` (`LC_COLLATE = C`, `LC_CTYPE = C`), giving ASCII `A–Z`/`a–z` case-folding and exact UTF-8 code-point matching on non-ASCII characters. C# witness qualification and highlight offset finding fold ASCII `A–Z` only, matching SQL `ILIKE` 1:1.
3. **Keyset cursor (`ArchiveCursor`, coordinator clarification)**:
   - Encodes `{ "v": "archive-cursor/1", "t": <utc_unix_microseconds>, "id": "<lowercase-uuid>", "s": "<source>", "qh": "<sha256_of_(v,source,terms)>" }` as Base64Url (`<= 256` chars) and paginates via `(d.submitted_at, d.document_id) < (@afterTs, @afterId)` over `ix_documents_submitted_at_document_id_desc`.
   - Cursor validation rejects malformed encoding/JSON/shape/version/timestamp range/UUID format and query/source scope mismatches (`400 cursor_query_mismatch`); it is a structural and query-binding check, not cryptographic HMAC tamper authentication.
4. **Single-snapshot read consistency (`ArchiveStore`)**:
   - Every `GET /api/archive` executes inside one `IsolationLevel.RepeatableRead` `READ ONLY` transaction (`SET TRANSACTION READ ONLY; SET LOCAL statement_timeout = '15s'`) without selecting `original_artifacts.bytes`, `extraction_results.raw_output_bytes`, `execution_attempts.diagnostic_raw_output_utf8`, `work_order_review_heads.machine_snapshot_json`, `unknown_reason`, or `operator_display_label`.

## 3. Machine Projection, Startup Readiness, & Least Privilege

1. **Append-only schema (`20261117091519_AddSourceLinkedArchive` + `grant-runtime.sql`)**:
   - `eledgercare.archive_result_projections` (parent completion marker per `(result_id, projection_version)`, `unit_count >= 0`, `projection_sha256`, `has_fallback`, `Restrict` FKs) and `eledgercare.archive_projection_units` (child text units with `\t`/`\n` whitespace separators only, `\0 -> U+FFFD` sanitization without length truncation, `page_number` `1..3` or `NULL` for unbound document fallback).
   - Runtime role `eledgercare_app` receives `SELECT, INSERT` **only** on both projection tables (`0` `UPDATE`, `DELETE`, or `TRUNCATE`).
2. **Atomic fenced publish & startup readiness (`ExtractionStore`, `ArchiveProjectionInitializer`, coordinator clarification)**:
   - Live completions write `ArchiveResultProjection` + `ArchiveProjectionUnit` inside `ExtractionStore.PublishCompletedResultAsync` after the `processing_jobs` and `execution_attempts` fencing checks in the same `ReadCommitted` (`synchronous_commit = on`) transaction.
   - By default (`DeferStartupInitialization = false`), `ArchiveStartupHostedService.StartingAsync` executes bounded batch verification and backfill (`LocalOcr:Enabled = false`, one `<= 16 MiB` raw output materialized at a time, reconciling `23505` concurrent initializers via `projection_sha256` equality) **before** Kestrel begins listening. No HTTP status is claimed before the listener exists. If startup verification detects a conflicting projection digest/count, the host still starts listening with readiness set to `Conflict` (mutating zero rows) so `GET /api/archive` serves `503 archive_projection_conflict` while `/api/documents` and review endpoints remain operational. While listening, if initialization is deferred/in-progress or unprojected rows remain with catch-up disabled, `GET /api/archive` serves `503 archive_not_ready` (`Retry-After: 1`) and never returns partial/empty `200 OK` results.
