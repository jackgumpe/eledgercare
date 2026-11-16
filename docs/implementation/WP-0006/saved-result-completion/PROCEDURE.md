# WP-0006 F2 Bounded CPU-Only Saved-Result Completion Procedure (`v3`, `eld-f2-implementer`)

> [!IMPORTANT]
> Authorized by coordinator commit `6dec634c81a4b2cbc1b492541697958cc0f76232` (`docs/kickoffs/WP-0006-eld-f2-saved-result-completion.md`) after explicit return and acknowledgement of GPU lease `WP-0006-author-corrected-20261116T154140Z`. Zero GPU/CUDA queries or imports, zero external runtime-root accesses, and zero `POST`/retry/database mutations are permitted.

## 1. Scope & Preserved Artifacts

- **Unchanged Product Source**: `8a73b7a5dab51e3ccf803aceedded4929529dd35` (independently accepted at `82e8f732afbf038bfb5b6c560f1b1219aaa4e40f`)
- **Preserved Original `v2` Runtime Evidence**: `48e8896d53fa001bba55276ac244f4adee377587` (`docs/implementation/WP-0006/runtime-author-v2/**`, retaining `outcome = "FAILED"` from `v2`'s `'Interrupted'` vs `'Extraction interrupted'` Node assertion mismatch)
- **Existing Persisted Database (Read-Only)**: `eledgercare_f2_runtime_author_v2` on owned cluster `127.0.0.1:55434` (`3` documents, `3` processing jobs, `4` execution attempts, `3` extraction results, `max(fencing_token) == 4`)
- **Versioned Fresh Scratch Directory**: `.scratch/stage2-saved-result-completion/{validation,run}/**`

## 2. Corrected UI Assertion Contract (`verify_saved_results_ui_v3.mjs`)

- Maps underlying API status via the exact frozen `statusLabels` table in `web/src/app/intake/receipt.ts` (`'interrupted' -> 'Extraction interrupted'`, `'completed' -> 'Completed (unreviewed)'`).
- Ties each displayed `<tr data-testid="attempt-row-<N>">` cell-by-cell (`attemptNumber`, `attemptId`, `statusLabel(apiStatus)`, `phase`, `startedAtUtc`, `endedAtUtc`) directly to both the pinned `v2` trial identities and live `GET /api/documents/{id}/extraction` responses while `LocalOcr:Enabled=false`.
- Preserves all document-status, unreviewed-banner, model/renderer provenance, page-ordering (`1..N`), inert DOM (`0` `<script>/<img>/<iframe>`), raw UTF-8 SHA-256, and byte-for-byte original PDF download checks across all `3` saved documents (`01a1e509-...`, `01a1e50c-...`, `01a1e511-...`).

## 3. Execution Sequence

1. Freeze helpers & procedure on `feature/wp-0006-local-extraction`.
2. Run CPU-only guard/syntax/unit validator:
   `python -B docs/implementation/WP-0006/saved-result-completion/helpers/validate_completion_v3_cpu.py`
3. Run decisive read-only saved-result completion across PostgreSQL `18.7` fast restart + `LocalOcr:Enabled=false` API restart + headless MS Edge reopen:
   `python -B docs/implementation/WP-0006/saved-result-completion/helpers/run_f2_saved_result_completion_v3.py --execute`
