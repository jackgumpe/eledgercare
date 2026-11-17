# WP-0010 / 007 Preparation: Evidence Reconciliation on Pending-Navigation Draft & Query Ownership (`eld-f4-reviewer`)

- **Reviewer / Session Disclosure:** `eld-f4-reviewer` — continued independent Google DeepMind Gemini 4 Carbon (High) session in Antigravity CLI conversation `61105d43-7706-45f2-9176-69d3256248e0` (`effort: high`; backend checkpoint identifier not separately exposed; reporting recipient: `eld-coordinator`).
- **Prior Publications & Turn Status Disclosure:**
  - Immutable `/002` design acceptance: [002_2026-11-17_review_eld-f4-reviewer.md](../../../../agent-reports/eld-f4-reviewer/WP-0010/002_2026-11-17_review_eld-f4-reviewer.md) (`85d879a1adc0ee62090f4c6a5c9a7fb8eb5f3a96`).
  - Immutable resource preparation: [preparation/README.md](../preparation/README.md) (`349c29773009abdf1bc228d01696d58a83d3eaa2`).
  - Immutable `/004` runtime review: [004_2026-11-17_review_eld-f4-reviewer.md](../../../../agent-reports/eld-f4-reviewer/WP-0010/004_2026-11-17_review_eld-f4-reviewer.md) (`324f09934b0aa2ee8e7bed7e8118c6109effb918`; helpers `85d3c36c874026a8e9166f29259fb44755422de0`, inventory `41efc840a874601acfa711f27073d2c90ad35c32`, audited by `eld-coordinator` in [independent004-audit.json](../../../../coordination/WP-0010/independent004-audit.json)).
  - All three prior CLI turns ended post-publication with provider `resultERROR` (`OS wrapper 0`); CLI `SUCCESS` is never claimed for any prior turn, and all historical reports/dossiers remain 100% untouched.
- **Bound Kickoff & Merged Base (`review/wp-0010-f4`):** [WP-0010-eld-f4-search-navigation-correction.md](../../../../kickoffs/WP-0010-eld-f4-search-navigation-correction.md) at coordinator authority `6daa37223b81335c686e7afae8fc376d2f8abfeb`, merged cleanly over `324f09934b0aa2ee8e7bed7e8118c6109effb918` at `e59232e0f1466b8d56dfe062994c112a632f8769`.
- **Canonical `/007` Gate:** **Not published.** Author `/006` (`eld-f4-implementer`) runs separately and was not accessed; exact `/006` source inspection and canonical `WP-0010 / 007` remain held until `eld-coordinator` binds the completed candidate.

---

## 1. Evidence Reconciliation: Why `eld-coordinator` Is Right on `prefreeze-dryrun-failure-06`

In immutable `/004` ([SOURCE-AND-DESIGN-AUDIT.md](../runtime/SOURCE-AND-DESIGN-AUDIT.md) Section 2.3 and [prefreeze-dryrun-failure-06.txt](../runtime/retained-failures/prefreeze-dryrun-failure-06.txt)), we accurately identified that `ArchivePage` ([archive-page.ts](../../../../../web/src/app/archive/archive-page.ts) `L365–381`, `L508–527`) overwrote `draftQuery` when an input edit occurred before `router.navigate` committed `this.q()`, but we treated that race as non-blocking based on an observed `1–3ms` local Router settling duration and added `await expect(page).toHaveURL(...)` before the second search in `verify_f4_independent_edge.mjs`.

Re-inspecting unchanged `c383021be1774451ba3034d89255b38b4267353b` ([app.config.ts](../../../../../web/src/app/app.config.ts) and [archive-page.ts](../../../../../web/src/app/archive/archive-page.ts)) confirms **`eld-coordinator`'s disposition is technically sound** — we **agree** with holding final `WP-0010 / 005` acceptance for a narrow `F4-04` correction and retract the "human-unreachable" inference in these new reconciliation notes (leaving historical `/004` immutable) for three concrete reasons:

### 1.1 Observed `1–3ms` Duration Is Not a Scheduling Guarantee (`provideZonelessChangeDetection()`)

1. [app.config.ts](../../../../../web/src/app/app.config.ts) (`L9`, `L11`) configures Angular `22.2.6` with **`provideZonelessChangeDetection()`** and **`provideRouter(routes, withComponentInputBinding())`**.
2. When `applyNewQueryAndNavigate(nextQ, nextSource)` ([archive-page.ts](../../../../../web/src/app/archive/archive-page.ts) `L508–527`) calls `void this.router.navigate(['/archive'], { queryParams, replaceUrl: false })` (`L521`), two separate asynchronous boundaries stand between the user's submit action and `effect()` (`L365–381`):
   - **Boundary 1 (Async Router navigation pipeline):** Angular Router resolves route matching, title strategy, and `Location.go` / `history.pushState` across asynchronous Promise turns.
   - **Boundary 2 (Zoneless render-frame scheduler):** Even *after* `history.pushState` updates `window.location.search` and `withComponentInputBinding()` writes signal `this.q`, `provideZonelessChangeDetection()` does **not** flush `effect()` synchronously — it schedules `effect()` onto Angular's next render/animation-frame pass (`requestAnimationFrame` + macrotask fallback)!
3. That combined window (`submit` -> Router Promise chain -> `requestAnimationFrame` render flush) is **not bounded to `1–3ms`**:
   - At ordinary `60Hz` / `30Hz` VSync or throttled remote/low-power frame timers, a render frame alone spans `16.7ms`–`33.3ms+`, and main-thread contention (such as native Edge PDFium rasterizing multi-page 300-DPI PDFs, GC pauses, or OS scheduling) extends it arbitrarily further.
   - Real operator input mechanisms — queued keystrokes during a busy frame, clipboard paste + `Enter`, IME composition commits, assistive input tools, and USB/Bluetooth keyboard-wedge barcode/work-order scanners — dispatch `input` and `submit`/`change` events without waiting for Angular's next animation frame.

### 1.2 Permanent DOM-vs.-Signal Split-Brain Persists Indefinitely After Overlap

Even more critically, inspecting [archive-page.ts](../../../../../web/src/app/archive/archive-page.ts) (`L51`, `L371`, `L384–398`, `L508–510`) reveals that **only the `input` edit has to overlap the pending-navigation window — the subsequent broken `Search` click can happen seconds or minutes later**:

1. Suppose the user submits `Q1` (`draftQuery` becomes `Q1` at `L509`, matching last-rendered `[value]="draftQuery()"` `== Q1`).
2. Before `effect()` flushes `urlQ = Q1`, an `input` event sets `<input>.value = Q2` and `onQueryInput` sets `draftQuery = Q2` (`L386`).
3. When `effect()` runs on the render pass (`L365–381`), `this.draftQuery.set(urlQ)` (`L371`) resets `draftQuery` from `Q2` back to `Q1` **within the same render cycle**.
4. Because `draftQuery()` at render time (`Q1`) equals the previously rendered `[value]` property (`Q1`), Angular's template binding `[value]="draftQuery()"` (`L51`) performs **no DOM write**!
5. As a result, **`<input>.value` on screen visibly remains `Q2` indefinitely**, while `this.draftQuery()` in component memory holds `Q1`! Whenever the user later clicks `Search` (`onSearchSubmit`, `L397`) or changes `Source filter` (`onSourceChange`, `L391`) — even `10` or `60` seconds after navigation settled — `ArchivePage` submits stale `Q1` instead of the `Q2` text visibly displayed inside the search box!

### 1.3 Separating Two Distinct `F4-04` Requirements

Our `/004` helper `verify_f4_independent_edge.mjs` (`L354–364`) added `await expect(page).toHaveURL(/q=SLOW-REVIEWER-STALE-1/)` before typing the second query. That wait genuinely proved **Property A**, while stepping around **Property B**:

| Property under `F4-04` | What it requires | Status on unchanged `c383021b` |
| --- | --- | --- |
| **Property A — Stale HTTP response suppression after route settles** | Once Search 1's route-input propagation has already settled, a newer Search 2 cancels/ignores Search 1's slower HTTP response (`cancelInFlight()` + `seq !== activeRequestSeq`, `L537`). | **Passes** (verified in `/004` `85d3c36c...`). |
| **Property B — Newest draft & query/filter authority across pending route-input propagation** | While Search 1's self-initiated navigation / route-input `effect()` is still pending: (1) a newer typed draft survives in both DOM and `draftQuery`; (2) a newer submitted query or `Source filter` change remains authoritative over older Router callbacks and out-of-order HTTP responses; (3) external URL loads and browser `Back`/`Forward` (`popstate`) still update `draftQuery`/`activeQuery`/`selectedSource` and reset pagination; (4) URL, inputs, header, cursor, and cards stay consistent. | **Fails on `c383021b`** (`SN-01A`, `SN-01B`, `SN-02A`, `SN-03` deterministically fail; `SN-02B` & `SN-04` pass). |

*(Secondary code observation on `L370`: `const queryChanged = ... || this.response() === null` also causes `effect()` to re-run `executeSearch(urlQ, ...)` when `response()` is still `null` as a self-initiated navigation commits, cancelling its own first HTTP request and issuing a duplicate identical request.)*

---

## 2. Deterministic Ownership Boundary Probe Suite (Zero Arbitrary Sleeps)

To verify Property B without timing luck or `setTimeout` delays, [probe_f4_search_navigation.mjs](helpers/probe_f4_search_navigation.mjs) uses **only** causal browser and network barriers against real Microsoft Edge (`4710`), Kestrel API (`5690`), and PostgreSQL `18.7` (`55439`, `eledgercare_f4_reviewer_migrated`):

1. **`SN-01A` (`pending_router_promise_draft_survives`):** Submits `'FIRST-PENDING-NAV-A'`, verifies `window.location.search === '?source=reviewed'` (Router Promise still pending), dispatches user `InputEvent('input')` setting `'WO-009901-CLEAN-HEAD'`, flushes URL + Search 1 response + two `requestAnimationFrame` render passes, then clicks `Search` and asserts `<input>.value === 'WO-009901-CLEAN-HEAD'`, wire query `q === 'WO-009901-CLEAN-HEAD'`, URL `/archive?q=WO-009901-CLEAN-HEAD&source=reviewed`, and `SEED-R03` (`01a1e578-8f3a-7e0c-826b-a2c9dc066a8f`) visible. *(Fails deterministically on `c383021b` with visible DOM-vs.-signal split-brain.)*
2. **`SN-01B` (`post_pushstate_pre_zoneless_effect_draft_survives`):** Intercepts the exact `history.pushState`/`replaceState` commit for `'FIRST-PENDING-NAV-B'` (`window.location.search` already updated to `?q=FIRST-PENDING-NAV-B&source=reviewed`, before Angular's zoneless `requestAnimationFrame` flushes `effect()`), dispatches `InputEvent('input')` for `'WO-004724-MP-LINKED'`, flushes two `requestAnimationFrame`s, clicks `Search`, and asserts `SEED-R04` (`01a20400-0000-7000-8000-000000000004`) renders. *(Fails deterministically on `c383021b`, proving Boundary 2 directly.)*
3. **`SN-02A` & `SN-02B` (`newer_filter_and_rapid_resubmit_beat_pending_nav_and_out_of_order_http`):** Holds Search 1's `/api/archive` HTTP response at an explicit `Promise` gate (`releaseOlderHttp`) while a newer draft + `Source filter` change (`SN-02A`: `'Refrigerator Evaporator'` + `'machine'`) or immediate second submit (`SN-02B`: `'WO-009901-CLEAN-HEAD'`) executes during pending navigation, then releases Search 1's HTTP response **after** Search 2 renders to verify out-of-order HTTP + Router callbacks cannot overwrite newer state. *(`SN-02A` fails deterministically on `c383021b`.)*
4. **`SN-03` (`null_response_return_from_review_pending_nav_resubmit`):** Reproduces `prefreeze-dryrun-failure-06` deterministically with zero timers by holding `GET /api/archive?q=7.50%25...` at a `Promise` gate after clicking `review-back-to-archive` (guaranteeing `response() === null`), submitting `'SLOW-REVIEWER-STALE-1'` (also `Promise`-gated), editing `<input>` to `'WO-009901-CLEAN-HEAD'` before `effect()` flushes, clicking `Search` #2, and releasing both older HTTP responses afterward. *(Fails deterministically on `c383021b`.)*
5. **`SN-04` (`external_deep_link_browser_back_forward_and_clear`):** Exercises deep-link entry, multi-step history pushes across source filters, browser `goBack()` x2 + `goForward()`, and `Clear`, asserting external `popstate` updates `draftQuery`/`activeQuery`/`selectedSource`, resets pagination to `Page 1`, issues `0` non-`GET` calls, and writes `0` browser storage keys. *(Passes on `c383021b`; guards against `/006` regressions on external URL navigation.)*
