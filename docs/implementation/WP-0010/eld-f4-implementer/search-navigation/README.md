# WP-0010 / 006 Bounded Search-Navigation Correction Dossier (`eld-f4-implementer`)

- **Packet / Sequence:** `WP-0010 / 006` (`implementation`)
- **Author / Conversation / Model:** `eld-f4-implementer`, continued Antigravity CLI conversation `b7c54417-db09-49bd-8d2b-7cc808f113be`, `Gemini 4 Carbon (High)` (`high` effort)
- **Governing Kickoff:** [WP-0010-eld-f4-search-navigation-correction.md](../../../../kickoffs/WP-0010-eld-f4-search-navigation-correction.md) (`cd5237303beaa374c3a60e9de58e45808b55435f`)
- **Accepted Design Contract:** [F4-source-linked-archive.md](../../../../design/F4-source-linked-archive.md) (`01a6dab0695c93246b4cf04d1a2098d3b77248d8`) and independent design review [WP-0010 / 002](../../../../agent-reports/eld-f4-reviewer/WP-0010/002_2026-11-17_review_eld-f4-reviewer.md) (`85d879a1adc0ee62090f4c6a5c9a7fb8eb5f3a96`)
- **Continuation Base:** `4b8e9b8231b9543b9a09cc8514a6876a70940d7b` (normal merge of prior author `/003` publication `7c578be6e8abff4d285ea1b519bbcfaeba1bb8c7` and coordinator authority `cd5237303beaa374c3a60e9de58e45808b55435f`)

## 1. Root Cause in `c383021be1774451ba3034d89255b38b4267353b`

In [archive-page.ts](../../../../../web/src/app/archive/archive-page.ts) at `c383021be1774451ba3034d89255b38b4267353b` (`web` tree `2aeddf8ec2e1f3d4e3dc40517866d975efadcd3e`):

1. `applyNewQueryAndNavigate(nextQ, nextSource)` updated signals immediately, started `executeSearch(nextQ, nextSource, null)`, and called asynchronous `void this.router.navigate(['/archive'], { queryParams })`.
2. Simultaneously, `ArchivePage` read route query parameters via `withComponentInputBinding()` (`input()` signals `q` and `source` — which Angular's `RoutedComponentInputBinder` updates after an asynchronous `Promise.resolve(data)` microtask following route activation) inside an `effect()` that **unconditionally** executed `this.draftQuery.set(urlQ)`, `this.activeQuery.set(urlQ)`, and `this.selectedSource.set(urlSource)` without distinguishing `ArchivePage`'s own earlier navigation settling from an external URL/history navigation.
3. Consequently, whenever a user edited `draftQuery` while an earlier `/archive` navigation was still settling (even after the HTTP search response itself had already returned), the late route-input propagation overwrote the newer `draftQuery` with the older `urlQ` (deterministically reproduced and retained in [c383021b-prefire-controlled-pending-nav.json](retained-failures/c383021b-prefire-controlled-pending-nav.json) and [c383021b-prefire-controlled-pending-nav.log](retained-failures/c383021b-prefire-controlled-pending-nav.log)). In addition, starting a new query did not clear `this.response()` before completion, leaving prior cards/cursors visible if a subsequent query failed validation (`HTTP 400`).

## 2. Narrow Frontend Fix (`web/src/app/archive/archive-page.ts`)

1. **Synchronous initial route sync + explicit navigation ownership tagging:**
   - Removed the deferred `input()`/`effect()` dual-update path on `ArchivePage` and synchronized initial `(q, source)` synchronously in `constructor()` from `ActivatedRoute.snapshot.queryParamMap` (`initialNavigationId` recorded so initial `NavigationEnd` does not fire a duplicate search).
   - Tagged every `ArchivePage`-initiated `router.navigate` call with transient `NavigationBehaviorOptions.info` (`{ sourceComponent: this, commandSeq }`, never persisted to `window.history.state` or browser storage).
   - Subscribed to `Router.events` (`NavigationEnd | NavigationSkipped`) while active on `/archive`:
     - Self-initiated navigation completions (`sourceComponent === this`) never overwrite a newer `draftQuery`, never reset cursor state, and never trigger duplicate `executeSearch` calls; if a stale `commandSeq < latestCommandSeq` ever committed out of order, `navigateForActiveState(latestCommandSeq)` re-asserts the authoritative URL.
     - External navigations (`info` absent — browser Back/Forward `popstate`, header `routerLink="/archive"`, or external deep-links) increment `latestCommandSeq`, synchronize `draftQuery`, `activeQuery`, `selectedSource`, reset pagination cursor state, and execute the corresponding search.
2. **Result / source / URL / cursor / error-state consistency:**
   - `executeSearch(...)` clears `this.response.set(null)` alongside `loading.set(true)` and `errorMessage.set(null)` so stale cards, source headers, and `nextCursor` tokens from a previous query/page are never displayed alongside a newer in-flight or failed (`400`/`503`) query, while preserving `cancelInFlight()` and `seq !== this.activeRequestSeq` stale-response suppression.

## 3. Verification Structure & Unchanged Backend Attribution

- **Freshly executed post-freeze frontend & integrated browser checks** ([run_search_navigation_verification.py](scripts/run_search_navigation_verification.py)):
  1. `01-ng-build-production`: Angular `22.2.7` production bundle build (`0` errors/warnings).
  2. `02-pg-cluster-start`: Owned PostgreSQL `18.7` (`127.0.0.1:55438`) startup and pre-run invariance check on `eledgercare_f4_author_seed_f3` (`76e7970b...`) and `eledgercare_f4_author_migrated` (`ad4f44bc...` / `78f0f273...`).
  3. `03-playwright-edge-e2e`: Full `16/16` Playwright Microsoft Edge `157.0.4341.60` regression suite (`F1`–`F4` + new deterministic `WP-0010-006` spec in [archive.spec.ts](../../../../../web/e2e/archive.spec.ts)) on `5590 / 4610`.
  4. `04-edge-search-navigation-deterministic`: Focused 5-part Promise-latched verifier ([verify_search_navigation_edge.mjs](scripts/verify_search_navigation_edge.mjs)) against real API `5590` + retained `eledgercare_f4_author_migrated`.
  5. `05-edge-f4-reopen-regression`: Integrated F4 readable PDF `#page=2`, pinned historical Revision `#2`, and saved-query canonical digest (`4d314f16...`) regression ([verify_f4_restart_edge.mjs](../scripts/verify_f4_restart_edge.mjs)).
  6. `06-pg-cluster-stop-final`: Post-run database invariance verification, clean service shutdown (`5590 / 4610 / 55438` `FREE`), `0` OCR workers, and [resource-return.json](resource-return.json).
- **Attributed unchanged backend proofs:** `src` (`9760402f...`), `tests` (`25c21310...`), `deploy` (`86e0c73d...`), and `workers/local_ocr` (`dc9b69e4...`) are byte-identical to `c383021be1774451ba3034d89255b38b4267353b`. Prior `/003` worker CPU (`9/9`), `.NET` Release (`95/95`), `42501` privilege (`13/13`), forward migration, and restart proofs remain attributed to [WP-0010 / 003](../../../../agent-reports/eld-f4-implementer/WP-0010/003_2026-11-17_implementation_eld-f4-implementer.md) (`ceec957733d6c00c6b4277e7db3f391ab6ccb6b4` / `7c578be6e8abff4d285ea1b519bbcfaeba1bb8c7`).
