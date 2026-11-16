# WP-0006 Independent Reviewer UI-Expectation Reconciliation Checkpoint (`v2`, `eld-next-reviewer`)

> **Ordinary Reviewer UI-Expectation Reconciliation Checkpoint (NOT Canonical `WP-0006 /004`)**
> **Disposition**: **INDEPENDENT REVIEWER RUNTIME `v2` HELPERS & PROCEDURE FROZEN (`694f4b61294aa1b489fb0a486cd328bdc61643aa`) AND CPU-ONLY VALIDATION PASSED (`3 / 3` DECISIVE STEPS `EXIT 0`, `12 / 12` DETERMINISTIC NODE UI EXPECTATION CASES PASSED, `19 / 19` PYTHON RELEASE-VALIDATOR & PACKAGER TESTS PASSED).**
> Canonical `WP-0006 /004` (`docs/agent-reports/eld-next-reviewer/WP-0006/004_2026-11-16_review_eld-next-reviewer.md`) remains **held** until `eld-coordinator` binds the published tip SHA of this checkpoint in a fresh sole reviewer GPU runtime release and `eld-f2-implementer` publishes its saved-result completion and canonical `/003`.

## 1. Reviewer Identity, Lineage, and Exact Revisions

| Field | Value |
| --- | --- |
| Reviewer agent ID | `eld-next-reviewer` |
| Conversation / session ID | `101b19cf-3133-4ead-91cb-9ca6068e3e72` |
| Disclosed actual model / effort | Google DeepMind **Gemini 4 Carbon (High)** (`gemini-4-carbon-high`, `High` effort) |
| Repository | `https://github.com/jackgumpe/eledgercare` (private) |
| Owned branch | `review/wp-0006-0007-next-tracks` |
| Owned worktree | `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-next-reviewer` |
| Coordinator reconciliation authority | `6dec634c81a4b2cbc1b492541697958cc0f76232` (`docs/kickoffs/WP-0006-eld-next-reviewer-ui-expectation.md` and `docs/coordination/WP-0006/reviewer-runtime-preparation-audit.json`, inspected read-only from `main` Git objects without merging `WP-0007` heldout paths) |
| Clean starting reviewer base (`v1` prep) | `bc91d331979ed5fbcf4f38b3f359a1cf71cd9960` ([../runtime-preparation/README.md](../runtime-preparation/README.md), helper `863fcd3a94188aa5a09b4e53f0f7192022950cbd`, tree OID `70e22361b7eca2915b0e3da43975da7dec7f0c92`, preserved byte-for-byte; prior reviewer CLI finished `SUCCESS` / `exit 0`) |
| Accepted Stage 1 source reconciliation | `82e8f732afbf038bfb5b6c560f1b1219aaa4e40f` ([../source-reconciliation/README.md](../source-reconciliation/README.md), immutable) |
| Accepted design review `/002` SHA | `e2452e1ab3d8937868c07ffb30ce430715b5be78` ([002_2026-11-16_review_eld-next-reviewer.md](../../../../../docs/agent-reports/eld-next-reviewer/WP-0006/002_2026-11-16_review_eld-next-reviewer.md), immutable) |
| Unchanged accepted product source | `8a73b7a5dab51e3ccf803aceedded4929529dd35` (`0` product/worker/test/web/deploy files modified) |
| Read-only inspected author `v2` GPU evidence | `48e8896d53fa001bba55276ac244f4adee377587` (under returned author lease `WP-0006-author-corrected-20261116T154140Z` / `e28471997f425b0e074f65432dccc3abf2116490`; 4 model attempts completed, failed only on author UI helper `rowText.includes('Interrupted')` vs UI `'Extraction interrupted'`) |
| Retained pre-final `v2` helper candidates | `3ebb727329bb7a67e59bfe5dc74434c5ec95d300` (static template audit checked `<td>{{ statusLabel(att.status) }}</td>` instead of `<td>{{ label(att.status) }}</td>` delegating to `statusLabel(status)` in [document-page.ts](../../../../../web/src/app/intake/document-page.ts); retained at [retained-failures/01-validate-reconciliation-3ebb727.log](retained-failures/01-validate-reconciliation-3ebb727.log)); `e16ff5a0ab44698d9a60963be94f6712b75244d5` / `fe3afba3d80bb94dce492e45f01aab373d072867` (passed before refining `F03..F08` holdout guard with hex-boundary regex so `>=4`-hex Git OIDs/UUIDs never false-positive during `--package-evidence`) |
| **Final frozen `v2` helper & procedure SHA** | **`694f4b61294aa1b489fb0a486cd328bdc61643aa`** ([PROCEDURE.md](PROCEDURE.md), [helpers/run_f2_reviewer_runtime_v2.py](helpers/run_f2_reviewer_runtime_v2.py), [helpers/verify_ui_reviewer_real_results_v2.mjs](helpers/verify_ui_reviewer_real_results_v2.mjs), [helpers/validate_reviewer_expectation_reconciliation_cpu.py](helpers/validate_reviewer_expectation_reconciliation_cpu.py)) |
| **Post-freeze validation evidence SHA** | **`ee003bb83984dc68f135e2ce64d052a6678562e5`** ([validation-summary.json](validation-summary.json), `logs/01..03*.log`) |
| Next owner | `eld-coordinator` (ready for separate reviewer GPU lease after active `WP-0007` baseline sentinel lease `WP-0007-reviewer-dev-20261116T160924Z` returns and author saved-result / `/003` completes; zero user permission pending) |

---

## 2. Reconciled UI Expectations & Retained Stronger Reviewer Assertions

1. **Exact Accepted UI Status Labels Bound to Exact Attempt IDs, Numbers, Phases, Timestamps, and API Statuses**:
   - Audited accepted Angular source [receipt.ts](../../../../../web/src/app/intake/receipt.ts) (`lines 105-116`), [document-page.ts](../../../../../web/src/app/intake/document-page.ts) (`lines 19-212, 242-244`), and API DTOs [DocumentResponses.cs](../../../../../src/ELedgerCare.Api/DocumentResponses.cs) (`lines 35-125`).
   - Replaced `v1`'s `expectedAttemptStatuses: ["Interrupted", "Completed"]` row-substring matching with `build_ui_document_spec(...)` in [helpers/run_f2_reviewer_runtime_v2.py](helpers/run_f2_reviewer_runtime_v2.py) and `validateDocumentUiObservation(...)` in [helpers/verify_ui_reviewer_real_results_v2.mjs](helpers/verify_ui_reviewer_real_results_v2.mjs), verifying simultaneously against live `GET /api/documents/{id}/extraction` JSON and all **6 individual `<td>` cells** of `<tr data-testid="attempt-row-N">`:
     - Cell `0`: exact `String(attemptNumber)` (`1..K` sequential)
     - Cell `1` & `td code`: exact `attemptId` UUID matching `api.attempts[i].attemptId`
     - Cell `2`: exact displayed UI status label (`EXPECTED_UI_STATUS_LABELS[apiStatus]`):
       - `awaiting_extraction` -> `'Awaiting extraction'`
       - `queued` -> `'Queued for extraction'`
       - `running` -> `'Extraction running'`
       - `completed` -> `'Completed (unreviewed)'`
       - `failed` -> `'Extraction failed'`
       - `interrupted` -> **`'Extraction interrupted'`**
     - Cell `3`: exact `phase` (`'interrupted'` on Attempt `#1`, `'completed'` on Attempt `#2`)
     - Cell `4` & Cell `5`: exact ISO-8601 `startedAtUtc` and non-dash `endedAtUtc` matching `api.attempts[i]` character-for-character.
2. **All Stronger Document, Provenance, Raw/Original Digest, Action-Button, and Inert-DOM Checks Retained & Strengthened**:
   - Exact header `document-id`, `document-job-id`, `document-status` (`'Completed (unreviewed)'`), `document-page-count`, `document-byte-length` (`'<B> bytes'`), and `document-sha256`.
   - `0` visible `extraction-unsupported` / `extraction-unavailable` / `extraction-active` / `extraction-failure` banners and `0` visible `[data-testid="request-extraction"]`, `[data-testid="refresh-extraction"]`, or `[data-testid="retry-extraction"]` buttons on completed documents (`workerEnabled === false` and `canRequestExtraction === false` / `canRetryExtraction === false` when `expectOcrDisabled=true`).
   - Exact `unreviewed-banner` strong heading `'Unreviewed raw extraction output (unreviewed)'`, `result-id`, `result-attempt-id` (bound to the winning completed attempt UUID—Attempt `#2` on the interrupted+retried document), `result-model` (`'baidu/Unlimited-OCR-2 @ 0480966938291445591f69f08a13b041c073a96a'`), `result-renderer` (`pypdfium2==5.15.2` & `159.0.8149.0`), `result-raw-byte-length` (`'<R> bytes (<P> page[s])'`), `result-raw-sha256`, `attempt-history` summary (`'Attempt history (<K>)'`), ordered `Page 1..N of N` headings, `0` forbidden DOM tags (`SCRIPT`, `IMG`, `IFRAME`, `OBJECT`, `EMBED`, `SVG`, `LINK`, `STYLE`, `FORM`) or `on*=` attributes, `<pre data-testid="result-raw-text">` UTF-8 SHA-256 parity, and downloaded original PDF byte length + SHA-256 parity.
3. **Updated `v2` Immutability, Release, Lease, and Hex-Safe Packaging Guards**:
   - Locks `16` protected product/Q0/corpus/reviewer Git tree and blob identities (adding `docs/reviews/WP-0006/eld-next-reviewer/runtime-preparation == 70e22361b7eca2915b0e3da43975da7dec7f0c92` and blocking `--package-evidence` writes into `runtime-preparation` or `runtime-expectation-reconciliation`).
   - Rejects superseded executing heads (`863fcd3a...`, `bc91d331...`, `3ebb7273...`, `e16ff5a0...`, `fe3afba3...`), preparation/returned authorities (`0e16cfd4...`, `e2847199...`, `6dec634c...`), returned author lease `WP-0006-author-corrected-20261116T154140Z`, and baseline sentinel lease `WP-0007-reviewer-dev-20261116T160924Z`, while recognizing real author `v2` GPU evidence `48e8896d53fa001bba55276ac244f4adee377587` and reading its published `F01`/`F07` raw SHA-256s (`7503761a...`, `c399ad89...`) read-only from Git objects.
   - Hardens `find_holdout_token(...)` with `(?<![0-9a-fA-F])(F03|F05|F06|F08)(?![0-9a-fA-F])` alongside family/split substrings so standalone holdout IDs fail closed while `>=4`-hex Git OIDs (`f0877a00...`) and UUIDs never trigger false positives during `--package-evidence`.

---

## 3. Protected Product & Immutable Reviewer Git Object Identities (`16 / 16` Verified)

| Path | Git Tree / Blob OID |
| --- | --- |
| `src` | `73d0146b3624ab4928a4d2cda7806d7d6166906e` |
| `workers/local_ocr` | `1ed609368ca4c6bff8b92231362be2d802ae8baf` |
| `workers/ocr` | `493935fad8163ec9242b396232a55564446a52e6` |
| `web` | `f0877a006922818bf731d5f87603a368ed782487` |
| `tests` | `5ad9bd15f41ab24bd5851ca02bfa0d8054dc1453` |
| `deploy` | `dade6a38e165b5cc2ba81ba895bd9d3c572d26f2` |
| `ELedgerCare.slnx` | `c00c2bc5ef46019fb4452fdf0bba7ca2271fc976` |
| `qualification/q0` | `5ca1507d0fb3f5905c9af1cb358642972e9c15dc` |
| `research` | `5036d17e55f96af3bdeea82a20a32eb54a26ddca` |
| `evaluation` | `60fcc7fa1741b6c44489bb9cf8484e03a4cbf019` |
| `docs/agent-reports/eld-next-reviewer/WP-0006/002_2026-11-16_review_eld-next-reviewer.md` | `10729efdedd954983153b4a6a93ef9e9d10753d7` |
| `docs/reviews/WP-0006/eld-next-reviewer/design` | `c1a059a16b06d07d3d026c7b396029498cdd9b64` |
| `docs/reviews/WP-0006/eld-next-reviewer/preparation` | `99ea0d2b1282eaf7ee32e9909c170c1587ad634c` |
| `docs/reviews/WP-0006/eld-next-reviewer/implementation` | `41b4611dbb71185e8dd94b544596749f36741fc8` |
| `docs/reviews/WP-0006/eld-next-reviewer/source-reconciliation` | `49318ac139f771339b787fc9c83d26d87c8a2488` |
| `docs/reviews/WP-0006/eld-next-reviewer/runtime-preparation` | `70e22361b7eca2915b0e3da43975da7dec7f0c92` |

---

## 4. Decisive CPU-Only Post-Freeze Validation (`694f4b61294aa1b489fb0a486cd328bdc61643aa`)

Executed on clean frozen `HEAD = 694f4b61294aa1b489fb0a486cd328bdc61643aa` via [helpers/validate_reviewer_expectation_reconciliation_cpu.py](helpers/validate_reviewer_expectation_reconciliation_cpu.py) using clearly labeled `TEST_FIXTURE_ONLY` synthetic inputs (see [validation-summary.json](validation-summary.json) and [inventory.json](inventory.json)):

| Step | Check | Result | Duration |
| --- | --- | --- | --- |
| `01` | Python `py_compile`, AST forbidden-import & zero-`HEAD~1` guard, direct `receipt.ts` (`6/6` labels) & `document-page.ts` (`25` `data-testid`s + `11` bindings) source audit, `9` local digests, `16` Git tree/blob OIDs, canonical `/004` & external reviewer root absence checks ([logs/01-python-compile-ast-and-ui-source-audit.log](logs/01-python-compile-ast-and-ui-source-audit.log)) | `EXIT 0` | `780 ms` |
| `02` | `node --check verify_ui_reviewer_real_results_v2.mjs` + `12` deterministic Node ESM UI expectation cases covering `1p`, `3p`, **2-attempt `interrupted` (`'Extraction interrupted'`) + `completed` (`'Completed (unreviewed)'`) history**, stale `'Interrupted'` rejection, `attemptId` swap rejection, API status drift rejection, wrong winning `result-attempt-id` rejection, action-button/disabled-OCR guard, inert DOM guard, and raw/original SHA mismatch guard ([logs/02-node-ui-expectation-deterministic-tests.log](logs/02-node-ui-expectation-deterministic-tests.log)) | `EXIT 0` (**`12 / 12` passed**) | `126 ms` |
| `03` | `19` focused `unittest` & CLI subprocess `v2` release-validator, `build_ui_document_spec`, author `48e8896d...` digest lookup, and hex-safe evidence-packager test methods ([logs/03-reviewer-v2-release-validator-tests.log](logs/03-reviewer-v2-release-validator-tests.log)) | `EXIT 0` (**`19 / 19` passed**) | `34,322 ms` |

## 5. Checks Intentionally Held for Released Runtime

- **GPU / CUDA / ML model imports, `nvidia-smi` queries, or inference**: Forbidden during UI-expectation reconciliation (`0` executed; `eld-baseline-reviewer` holds active sole lease `WP-0007-reviewer-dev-20261116T160924Z`).
- **PostgreSQL (`55435`), `ELedgerCare.Api` (`5290`), and Angular/Edge (`4310`) startup**: Forbidden during preparation; reviewer ports verified unbound (`false`) before and after validation.
- **External `C:\Users\jackg\eLedgerCare-F2\WP-0006\reviewer` and `C:\Users\jackg\eLedgerCare-Q0\WP-0005`**: Untouched; `C:\Users\jackg\eLedgerCare-F2\WP-0006\reviewer` verified absent (`false`) before and after validation.
