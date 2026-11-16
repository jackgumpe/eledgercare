# WP-0008 F3 Frozen Contract, Request-Digest Specification & Least-Privilege Schema

- **Author**: `eld-f3-implementer`
- **Design Authority**: [`docs/design/F3-review-correction.md`](../../../design/F3-review-correction.md) (`c5b5db3af96abf155c806082583b8a92c687f54d`) & [`docs/reviews/WP-0008/eld-f3-reviewer/design/README.md`](../../../reviews/WP-0008/eld-f3-reviewer/design/README.md) (`bff139bcdf55df77a821b858513b7e6bf5d96b87`)

## 1. Profile, Version Identifiers & Bounds

| Identifier / Limit | Frozen Value |
| --- | --- |
| Profile ID | `maintenance-work-order/1` |
| Field Schema Version | `maintenance-work-order-fields/1` |
| Suggestion Policy Version | `work-order-suggestions/1` |
| Request Digest Schema | `eledgercare.work-order-review-request/1` |
| Machine Snapshot Schema | `eledgercare.work-order-machine-snapshot/1` |
| Max `POST .../review/revisions` Body | `32,768` bytes (`413 review_request_too_large` above limit) |
| Max Revisions per Extraction Result | `128` (`409 revision_limit_reached` on new operation at `128`; idempotent replay of `1..128` still returns `200 OK`) |
| Field UTF-16 `.Length` Caps | `work_order_id`: `64` (single-line); `property_name`: `200` (single-line); `building_unit`: `120` (single-line); `requested_date`: `64` (single-line); `issue_and_resolution`: `4,000` (multiline `\r`/`\n`/`\t` permitted) |
| Optional `unknownReason` Cap | `500` UTF-16 code units (single-line; permitted only when `decision == "unknown"`) |
| Optional `operatorDisplayLabel` Cap | `80` UTF-16 code units (single-line; unauthenticated local operator metadata) |

## 2. Deterministic Request-Digest (`request_sha256`) Specification

Every validated `POST /api/documents/{documentId}/review/revisions` computes a 32-byte SHA-256 digest (`ReviewRequestDigest.ComputeSha256`) over compact UTF-8 JSON emitted by `System.Text.Json.Utf8JsonWriter` in exact property and canonical `0..4` field order:

```json
{
  "schema": "eledgercare.work-order-review-request/1",
  "documentId": "<36-char lowercase UUID D>",
  "profileId": "maintenance-work-order/1",
  "resultId": "<36-char lowercase UUID D>",
  "expectedRevision": 0,
  "status": "draft|reviewed",
  "operatorDisplayLabel": "<string|null>",
  "fields": [
    {
      "fieldKey": "work_order_id",
      "decision": "unreviewed|accepted|edited|unknown",
      "value": "<string|null>",
      "unknownReason": "<string|null>",
      "consultedSource": null | {
        "pageNumber": 1,
        "blockOrdinal": 4,
        "tableRow": null,
        "tableColumn": null
      }
    }
  ]
}
```

- **Canonical field order (`0..4`)**: `work_order_id`, `property_name`, `building_unit`, `requested_date`, `issue_and_resolution`.
- **Server-owned values excluded from caller assertion**: `revisionId`, `revisionNumber`, `savedAtUtc`, `inputSha256`, `rawOutputSha256`, `fieldSchemaVersion`, `suggestionPolicyVersion`, `machineSnapshot`, and `consultedQuote` are owned exclusively by the server; any client JSON payload containing server-owned provenance keys is rejected with `400 client_provenance_forbidden`.
- **Precedence (`F3-BIC-03`)**: `Idempotency-Key` lookup executes **before** context-free validation, `expectedRevision` stale-head checks, and the `128`-revision cap. Exact `(documentId, request_sha256)` match returns `200 OK` (`replayed: true`, `isCurrentHead: revisionNumber == currentRevisionNumber`); any difference returns `409 idempotency_key_conflict`.

## 3. PostgreSQL Schema & Column-Scoped Least Privilege (`F3-BIC-02`)

1. `eledgercare.work_order_review_revisions`: Append-only (`SELECT, INSERT` only for `eledgercare_app`); unique indexes on `idempotency_key`, `(document_id, revision_number)`, and `(result_id, revision_number)`; `RESTRICT` FKs to `documents` and `extraction_results`.
2. `eledgercare.work_order_review_fields`: Append-only (`SELECT, INSERT` only for `eledgercare_app`); composite PK `(revision_id, field_ordinal)` and unique `(revision_id, field_key)`; `RESTRICT` FK to `work_order_review_revisions`.
3. `eledgercare.work_order_review_heads`: `SELECT, INSERT` plus **column-scoped `GRANT UPDATE (current_revision_number, current_revision_id, current_status, updated_at)`** for `eledgercare_app`. Columns `document_id`, `result_id`, `input_sha256`, `raw_output_sha256`, `profile_id`, `field_schema_version`, `suggestion_policy_version`, `machine_snapshot_json`, and `created_at` are immutable at the PostgreSQL privilege layer. `expectedRevision == 0` serializes via unique constraints (`23505` rollback + fresh `DbContext` replay/stale reconciliation); `expectedRevision >= 1` serializes via `SELECT ... FROM eledgercare.work_order_review_heads WHERE document_id = @docId FOR UPDATE` followed by post-lock replay recheck.
