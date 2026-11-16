# WP-0006 Independent F2 Runtime Verification & Safe Evidence Capture Procedure v2 (`eld-next-reviewer`)

> [!IMPORTANT]
> This versioned procedure (`v2`) reconciles the UI attempt-history status-label expectation identified during `eld-f2-implementer`'s real runtime trial (`48e8896d53fa001bba55276ac244f4adee377587` under `e28471997f425b0e074f65432dccc3abf2116490`) **before** `eld-next-reviewer` executes its own GPU trial, as authorized by coordinator commit `6dec634c81a4b2cbc1b492541697958cc0f76232` (`docs/kickoffs/WP-0006-eld-next-reviewer-ui-expectation.md`).
> Prior reviewer preparation (`bc91d331979ed5fbcf4f38b3f359a1cf71cd9960`, helper `863fcd3a94188aa5a09b4e53f0f7192022950cbd`, [runtime-preparation/README.md](../runtime-preparation/README.md)), accepted source reconciliation (`82e8f732afbf038bfb5b6c560f1b1219aaa4e40f`), accepted design `/002` (`e2452e1ab3d8937868c07ffb30ce430715b5be78`), and product source (`8a73b7a5dab51e3ccf803aceedded4929529dd35`) remain byte-for-byte unchanged. Canonical `WP-0006 /004` remains **held** until separately released real independent execution and full disposition on actual author `/003`.

## 1. What Changed from `runtime-preparation` (`v1`) -> `runtime-expectation-reconciliation` (`v2`)

1. **Exact Accepted Angular UI Label + API Status + Attempt-ID/Number Association**:
   - In accepted Angular source [receipt.ts](../../../../../web/src/app/intake/receipt.ts) (`lines 105-112`) and [document-page.ts](../../../../../web/src/app/intake/document-page.ts) (`lines 130-140`), `<tr [attr.data-testid]="'attempt-row-' + att.attemptNumber">` renders 6 `<td>` columns (`attemptNumber`, `<code>attemptId</code>`, `statusLabel(att.status)`, `att.phase`, `att.startedAtUtc`, `att.endedAtUtc ?? '—'`), where `statusLabels` maps:
     - `awaiting_extraction` -> `'Awaiting extraction'`
     - `queued` -> `'Queued for extraction'`
     - `running` -> `'Extraction running'`
     - `completed` -> `'Completed (unreviewed)'`
     - `failed` -> `'Extraction failed'`
     - `interrupted` -> **`'Extraction interrupted'`** (lowercase `'i'`, not `'Interrupted'`)
   - Our `v1` browser helper (`863fcd3a94188aa5a09b4e53f0f7192022950cbd`) inherited `expectedAttemptStatuses: ["Interrupted", "Completed"]` substring matching on concatenated row text.
   - `v2` ([helpers/run_f2_reviewer_runtime_v2.py](helpers/run_f2_reviewer_runtime_v2.py) + [helpers/verify_ui_reviewer_real_results_v2.mjs](helpers/verify_ui_reviewer_real_results_v2.mjs)) replaces loose substring matching with exact structured `expectedAttempts` bindings (`attemptNumber`, `attemptId`, `apiStatus`, `expectedUiStatusLabel`, `expectedPhase`) verified simultaneously against **both** live `GET /api/documents/{id}/extraction` JSON **and** all 6 individual `<td>` cells of `<tr data-testid="attempt-row-N">` in Microsoft Edge.
2. **Comprehensive Direct UI Label & Selector Audit Against `document-page.ts`**:
   - Verifies exact `document-id`, `document-job-id`, `document-status` (`'Completed (unreviewed)'`), `document-page-count`, `document-byte-length` (`'<N> bytes'`), and `document-sha256`.
   - Verifies exact `unreviewed-banner` heading `'Unreviewed raw extraction output (unreviewed)'`, `0` `extraction-unsupported` / `extraction-unavailable` / `extraction-active` / `extraction-failure` banners, and `0` `request-extraction` / `refresh-extraction` / `retry-extraction` buttons on completed documents (updating `v1`'s `trigger-extraction` selector to the exact `request-extraction` / `refresh-extraction` / `retry-extraction` `data-testid`s in `document-page.ts:66,72,105`).
   - Verifies exact `result-id`, `result-attempt-id` (bound to the winning completed attempt UUID—Attempt #2 on the interrupted-then-retried document), `result-model` (`'baidu/Unlimited-OCR-2 @ 0480966938291445591f69f08a13b041c073a96a'`), `result-renderer` (`pypdfium2==5.15.2` & `159.0.8149.0`), `result-raw-byte-length` (`'<B> bytes (<P> page[s])'`), `result-raw-sha256`, `attempt-history` summary (`'Attempt history (<K>)'`), exact `1..N` page headings, inert DOM (`0` forbidden tags or `on*=` attributes), `<pre data-testid="result-raw-text">` UTF-8 SHA-256, and downloaded original PDF byte length + SHA-256.
3. **Preserved Immutability & Updated Release Guards**:
   - Locks `docs/reviews/WP-0006/eld-next-reviewer/runtime-preparation` (`70e22361b7eca2915b0e3da43975da7dec7f0c92`) as an additional immutable protected tree (`16` protected product/Q0/corpus/reviewer identities total).
   - Rejects superseded `v1` executing heads (`0de423c6...`, `863fcd3a...`, `e7733f9e...`, `bc91d331...`), historical/preparation coordinator commits (including `0e16cfd4...`, `e2847199...`, `6dec634c...`), returned author lease `WP-0006-author-corrected-20261116T154140Z`, and baseline sentinel lease `WP-0007-reviewer-dev-20261116T160924Z`.
   - Uses `.scratch/stage2-reviewer-runtime-v2` and fresh DB `eledgercare_f2_runtime_reviewer` on reviewer loopback ports `5290` (API) / `4310` (UI) / `55435` (PostgreSQL `18.7`) and future writable root `C:\Users\jackg\eLedgerCare-F2\WP-0006\reviewer`.

## 2. Bounded 4-Attempt Independent Runtime Matrix (`F2-01..07`, Unchanged)

1. **Scenario 1 (Attempt #1 of 4 — `SYN-WO-01-v1-raster300.pdf`, 1 page)**: Real 1-page CUDA extraction completion, PostgreSQL `sha256(raw_output_bytes)` (`bytea`) parity, provenance/timing verification, and headless Edge `v2` verification (`expectedAttempts`: `[#1 completed -> 'Completed (unreviewed)']`).
2. **Scenario 2 (Attempt #2 of 4 — `SYN-MP-01-v0-clean.pdf`, 3 pages)**: Real 3-page CUDA extraction completion, `[1, 2, 3]` page ordering, 3p config digest (`ac90459c...`), and descriptive comparison against Q0 `F07.warm1.raw.txt` and author `v2` raw SHA-256.
3. **Scenario 3 (Attempt #3 Interrupted + Attempt #4 Explicit Retry — fresh `SYN-WO-01-v1-raster300.pdf`)**: Single-process Win32 `TerminateProcess` of `ELedgerCare.Api` during live `inferring` (`forward_progress >= 1`), kernel Job Object termination of `launcher` + `worker`, `0` partial result rows, startup reconciliation to `interrupted`, `2.5 s` zero-auto-retry check, `409 retry_explicit_required` on empty replay, and explicit retry completion (`fencing_token_2 > fencing_token_1`) preserving Attempt #1 as `interrupted`.
4. **Scenario 4 (`0` Model Attempts — Fast Restart API + PostgreSQL `18.7` & `LocalOcr:Enabled=false` Saved-Result Reopen)**: Clean `pg_ctl` fast restart (`55435`), `LocalOcr__Enabled=false` API reopen (`5290`), HTTP + headless Edge `v2` verification (`4310` -> `5290`) across all 3 saved documents (including Doc 3's exact 2-row `['Extraction interrupted' ('interrupted'), 'Completed (unreviewed)' ('completed')]` attempt history bound to exact UUIDs), process-exit & 18-object Q0 model integrity verification, and `lease-return-reviewer-v2.json`.

## 3. Future Live Commands (Only After Fresh Coordinator Reviewer Release)

```powershell
Set-Location "C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-next-reviewer"
git fetch origin --no-tags

# 1. Pure CPU/Git dry-run validation of the future coordinator reviewer release:
& "C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe" -B `
  docs/reviews/WP-0006/eld-next-reviewer/runtime-expectation-reconciliation/helpers/run_f2_reviewer_runtime_v2.py `
  --dry-run-validate `
  --release-commit <FUTURE_COORDINATOR_RELEASE_SHA> `
  --release-path <FUTURE_REVIEWER_RELEASE_JSON_PATH> `
  --validation-output .scratch/stage2-reviewer-runtime-v2/dry-run-validation.json

# 2. Bounded <=4-attempt independent GPU runtime verification under active sole reviewer lease:
& "C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe" -B `
  docs/reviews/WP-0006/eld-next-reviewer/runtime-expectation-reconciliation/helpers/run_f2_reviewer_runtime_v2.py `
  --execute-live `
  --release-commit <FUTURE_COORDINATOR_RELEASE_SHA> `
  --release-path <FUTURE_REVIEWER_RELEASE_JSON_PATH>

# 3. Safe secret-checked & holdout-checked evidence packaging before canonical /004 report:
& "C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe" -B `
  docs/reviews/WP-0006/eld-next-reviewer/runtime-expectation-reconciliation/helpers/run_f2_reviewer_runtime_v2.py `
  --package-evidence `
  --release-commit <FUTURE_COORDINATOR_RELEASE_SHA> `
  --release-path <FUTURE_REVIEWER_RELEASE_JSON_PATH> `
  --dest-dir docs/reviews/WP-0006/eld-next-reviewer/runtime-execution
```
