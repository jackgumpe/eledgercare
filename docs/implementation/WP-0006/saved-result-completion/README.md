# WP-0006 F2 Bounded CPU-Only Saved-Result Completion (`v3`, `eld-f2-implementer`)

> **Disposition**: **SAVED-RESULT PERSISTENCE & MICROSOFT EDGE REOPEN VERIFICATION COMPLETE (`EXIT 0`, `COMPLETED_SAVED_RESULT_REOPEN_VERIFICATION`).**
>
> Executed on clean frozen helper commit `1bee2171a8c616dd48ca5561049c9a4e458805e2` under coordinator authority `6dec634c81a4b2cbc1b492541697958cc0f76232` (`docs/kickoffs/WP-0006-eld-f2-saved-result-completion.md`) with `LocalOcr:Enabled=false` throughout, zero GPU/CUDA/model queries or imports, zero external runtime-root touches, zero `POST`/retry requests, and zero database mutations (`db_before_canonical_sha256 == db_after_canonical_sha256 == 0304cbee0c0cd6894176c0bc10ef845fd9744cf91f415153bb6a97928cc6bb26`). Original `v2` runtime trial summary (`docs/implementation/WP-0006/runtime-author-v2/trial-summary-v2.json` at `48e8896d53fa001bba55276ac244f4adee377587`) remains preserved unchanged as `FAILED`.

## 1. Lineage & Retained Helper Iteration Logs

- **Coordinator Authority**: `6dec634c81a4b2cbc1b492541697958cc0f76232` (`docs/kickoffs/WP-0006-eld-f2-saved-result-completion.md`)
- **Starting Clean Base**: `48e8896d53fa001bba55276ac244f4adee377587` (`runtime-author-v2` publication; GPU lease `WP-0006-author-corrected-20261116T154140Z` returned and coordinator-acknowledged)
- **Unchanged Product Source**: `8a73b7a5dab51e3ccf803aceedded4929529dd35` (independently accepted at `82e8f732afbf038bfb5b6c560f1b1219aaa4e40f`)
- **Retained Helper-Only Failures During `v3` Preparation**:
  - `467ccb717ff97cd3d31536707de7ea559ae2d6d6`: helper SQL snapshot referenced `d.admitted_page_count` instead of `o.page_count` (`retained-failures/execute-completion-v3-467ccb7.log`, `retained-failures/completion-summary-v3-467ccb7.json`).
  - `9bae839ad678b793429acfbfed508469b0cb6f76`: helper `select_json_readonly` parsed `out.splitlines()[-1]` instead of full multi-line `json_agg(t)` output (`retained-failures/execute-completion-v3-9bae839.log`, `retained-failures/completion-summary-v3-9bae839.json`).
- **Final Frozen `v3` Helper Commit**: **`1bee2171a8c616dd48ca5561049c9a4e458805e2`** (`6 / 6` CPU validator unit tests + `py_compile` + `node --check` passed in [`logs/cpu-validation-summary-v3.json`](logs/cpu-validation-summary-v3.json)).

## 2. Decisive Read-Only Completion Results (`completion-summary-v3.json`)

1. **Before vs. After Read-Only Database State (`eledgercare_f2_runtime_author_v2` via `PGOPTIONS="-c default_transaction_read_only=on"`)**:
   - Before (`observations/db-snapshot-before.json`): `3` documents, `3` jobs, `4` execution attempts, `3` extraction results, `max_fencing_token = 4`, canonical SHA-256 `0304cbee0c0cd6894176c0bc10ef845fd9744cf91f415153bb6a97928cc6bb26`.
   - After (`observations/db-snapshot-after.json`): identical counts and identical canonical SHA-256 `0304cbee0c0cd6894176c0bc10ef845fd9744cf91f415153bb6a97928cc6bb26` (**zero new attempts, zero mutations**).
2. **PostgreSQL `18.7` Fast Restart & `LocalOcr:Enabled=false` API Restart**:
   - `postgres` #1 (`PID 17624`, `FILETIME 134393199490787020`) + `ELedgerCare.Api` #1 (`PID 11176`, `FILETIME 134393199500491263`, `LocalOcr:Enabled=false`, `0` child processes) -> all `3` documents verified via read-only `GET` (`/api/documents/{id}`, `/api/documents/{id}/extraction`, `/api/documents/{id}/original`).
   - Clean `pg_ctl` fast restart (`PID 17624` stopped -> `PID 19604`, `FILETIME 134393199545449925` started; *not a power-loss test*) + `ELedgerCare.Api` #2 (`PID 24068`, `FILETIME 134393199551093358`, `LocalOcr:Enabled=false`, `0` child processes) -> byte-identical `GET /extraction` payloads (`cef5dc76...`, `1b4ca304...`, `ae6e6938...`) and byte-identical raw UTF-8 outputs matching committed `runtime-author-v2` `.bin` files.
3. **Headless Microsoft Edge `157.0.4341.60` Saved-Result Reopen (`observations/ui-verified-v3-all-saved-ocr-disabled.json`)**:
   - Verified all `3` saved documents (`01a1e509-f496-737c-901f-2b6a8fb84094` `1`p, `01a1e50c-bd99-775e-8748-dc55022f4b04` `3`p ordered `Page 1..3 of 3`, `01a1e511-ae58-72ad-a79e-0b359340f539` `1`p interrupted + retried):
     - `Completed (unreviewed)` status, visible `unreviewed-banner`, `0` `extraction-unavailable` banners, `0` executable `<script>/<img>/<iframe>` DOM nodes, exact model/renderer provenance, exact `<pre data-testid="result-raw-text">` UTF-8 byte lengths & SHA-256s, and byte-for-byte original PDF downloads (`372,258 B`, `8,422 B`, `372,258 B`).
     - Cell-by-cell `<tr data-testid="attempt-row-*">` tie to underlying API statuses and UUIDs, including Doc 3 Row #1 (`attemptNumber=1`, `01a1e511-ae6a-74cf-b0c9-d6e5933a22ea`, API `'interrupted'` -> UI `'Extraction interrupted'`) and Row #2 (`attemptNumber=2`, `01a1e512-6a6d-7554-a1b6-352f03223bda`, API `'completed'` -> UI `'Completed (unreviewed)'`).
4. **Clean Shutdown**: Owned ports `5190`, `4210`, and `55434` all verified `false` (unbound) on completion.
