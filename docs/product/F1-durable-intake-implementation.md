# F1 durable intake — implementation guide

Implements the accepted design [F1-durable-intake.md](../design/F1-durable-intake.md) (design candidate
`bce84931fef5cf2a8fa3652095dbea2973a19aef`). This page maps the design onto the code; it does not change the design.

## Layers

| Project | Responsibility | Key types |
| --- | --- | --- |
| `src/ELedgerCare.Domain` | Invariants, no outward references | `Document.Submit`, `OriginalArtifact`, `ProcessingJob`, `ProcessingStatus`, `AdmissionCeilings` |
| `src/ELedgerCare.Application` | Intake use case and the two needed boundaries | `SubmitDocument`, `IIntakeStore`, `IPdfAdmission`, `IntakeLimits` |
| `src/ELedgerCare.Infrastructure` | PostgreSQL/EF Core + PdfPig admission, migrations | `ELedgerCareDbContext`, `IntakeStore`, `PdfPigAdmission`, `Persistence/Migrations` |
| `src/ELedgerCare.Api` | Loopback Kestrel host, HTTP validation, endpoints | `Program`, `DocumentEndpoints`, `BoundedBody`, `LocalOnlyGuard`, `UnhandledExceptionHandler` |
| `web/` | Angular 22 screen | `IntakePage`, `DocumentPage`, `SubmissionApi` |

## HTTP contract as implemented

| Endpoint | Results |
| --- | --- |
| `POST /api/documents` (raw `application/pdf`, `Idempotency-Key`) | 201 new (after commit, `Location`), 200 exact replay, 400 key/empty, 409 different bytes, 413 declared/streamed oversize, 415 media type/encoding, 422 PDF outside profile, 429 both admission slots busy, 500 unknown outcome |
| `GET /api/documents/{documentId}` | 200 receipt metadata (no bytes loaded), 400 malformed id, 404 |
| `GET /api/documents/{documentId}/original` | exact bytes, `application/pdf`, `Content-Length`, `attachment; filename=document-{id}.pdf`, `nosniff` |
| `GET /api/submissions/{idempotencyKey}` | 200 committed receipt, 400 malformed key, 404 at this instant |

Errors are ProblemDetails with a stable `code` extension (for example `pdf_encrypted`,
`idempotency_key_conflict`, `admission_busy`). Admission order follows design steps 1–5; the 429 gate
applies to POST only.

## Admission profile

Header `%PDF-1.0`..`%PDF-1.7` at byte zero → trailing `%%EOF` → **final `startxref` must address an `xref`
keyword or an `N G obj` header** → PdfPig 0.1.16 strict open (`UseLenientParsing=false`,
`SkipMissingFonts=false`, `MaxStackDepth=32`) → reject `IsEncrypted` → reject `NumberOfPages` outside
1..MaxPages → `GetPage(1..N)`; no text/letters are read. The `startxref` precondition is an
implementation addition (see the WP-0003 implementation report): PdfPig recovers a wrong `startxref` by brute force
even in strict mode. Wrong per-object xref offsets behind a valid `startxref` are still recovered by PdfPig
and admitted; this is a pinned known limitation, consistent with the design's statement that strict mode is
not exhaustive corruption rejection.

## Persistence

Schema `eledgercare`: `documents`, `original_artifacts` (bytea), `processing_jobs`, created only by the
explicit migration `20261114182147_InitialDurableIntake`. Check constraints mirror the domain ceilings;
foreign keys use `RESTRICT`; `ux_documents_idempotency_key` resolves same-key races. Intake runs one Read
Committed transaction with `SET LOCAL synchronous_commit = on`, inserting all three rows before commit.
The runtime role has only `CONNECT`, schema `USAGE` and `SELECT, INSERT` on the three tables.

## Browser behaviour

The pending key is written to `sessionStorage` before the first upload. Network error, timeout or 5xx →
**Submission outcome unknown** (key kept, survives reload); 429 → busy, key kept, and an earlier uncertainty
stays unknown; definitive 4xx without earlier uncertainty clears the key. **New submission** is the only
way to mint a new key; the submit button is disabled while sending. No document bytes are stored in the
browser.
