# Retained Failure Lineage (`WP-0010 / 006` Search-Navigation Correction)

## 1. Controlled Pre-Fix Failure Reproduction on Unmodified `c383021be1774451ba3034d89255b38b4267353b` Frontend Source

- **Artifacts:**
  - [c383021b-prefire-controlled-pending-nav.log](c383021b-prefire-controlled-pending-nav.log)
  - [c383021b-prefire-controlled-pending-nav.json](c383021b-prefire-controlled-pending-nav.json)
- **Tested Revision / Tree Identity:** Continuation merge `4b8e9b8231b9543b9a09cc8514a6876a70940d7b` prior to any `web/` edits (`git rev-parse HEAD:web` === `git rev-parse c383021be1774451ba3034d89255b38b4267353b:web` === `2aeddf8ec2e1f3d4e3dc40517866d975efadcd3e`).
- **Environment:** Real Microsoft Edge `157.0.4341.60`, owned UI `127.0.0.1:4610`, owned `.NET 10` API `127.0.0.1:5590` (`LocalOcr:Enabled=false`), owned PostgreSQL `18.7` `127.0.0.1:55438` (`eledgercare_f4_author_migrated`, read-only).
- **Controlled Reproduction Scenario (Zero Arbitrary Sleeps, Zero Artificial HTTP Delay):**
  1. Installed a Promise-latched `canActivate` guard (`runGuardsAndResolvers = 'paramsOrQueryParamsChange'`) on the live `/archive` route via Angular's `window.ng.getComponent` dev-mode hook in [verify_search_navigation_edge.mjs](../scripts/verify_search_navigation_edge.mjs).
  2. Submitted query `REV2-ACTIVE-HAWTHORNE` with source `reviewed`.
  3. Confirmed that the real PostgreSQL + `.NET` API HTTP search **completed and rendered** (`httpCompletedWhileRoutePending: true`, `1` card rendered) while Router Navigation #1 (`?q=REV2-ACTIVE-HAWTHORNE&source=reviewed`) remained deterministically held pending (`pendingBeforeEdit.count = 1`, `window.location.search = ""`).
  4. Filled a newer unsubmitted draft `MULTIPAGE-REVIEWED-ALDER-P2` into `[data-testid="archive-query-input"]` (`draftBeforeRelease = "MULTIPAGE-REVIEWED-ALDER-P2"`).
  5. Deterministically released Navigation #1 (`releaseNext(true)`).
- **Observed Pre-Fix Failure (`exit=1`):**
  - When Navigation #1 settled (`urlAfterRelease = "http://127.0.0.1:4610/archive?q=REV2-ACTIVE-HAWTHORNE&source=reviewed"`), `ArchivePage`'s `effect()` unconditionally executed `this.draftQuery.set(urlQ)` and overwrote `[data-testid="archive-query-input"]` from `"MULTIPAGE-REVIEWED-ALDER-P2"` back to `"REV2-ACTIVE-HAWTHORNE"`:
    ```text
    Search-navigation Edge verification FAILED: Criterion (1) FAILED: newer typed draft "MULTIPAGE-REVIEWED-ALDER-P2" was overwritten with "REV2-ACTIVE-HAWTHORNE" when earlier pending navigation settled.
    ```
- **Resolution:** Fixed in [archive-page.ts](../../../../../../web/src/app/archive/archive-page.ts) by synchronizing initial route parameters synchronously on mount, tagging `ArchivePage`-initiated `router.navigate` calls via transient `NavigationBehaviorOptions.info`, ignoring self-initiated route completions on `draftQuery`/search state while keeping external URL/Back-Forward updates authoritative, and clearing stale `response()` on new query execution.
