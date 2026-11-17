import { mkdirSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';

const repoRoot = path.resolve(import.meta.dirname, '..', '..', '..', '..', '..', '..');
const requireFromWeb = createRequire(path.join(repoRoot, 'web', 'package.json'));
const { chromium } = requireFromWeb('@playwright/test');

const SEED1_DOC = '01a1e571-2838-714b-861b-bf0835d7c90a';
const SEED2_DOC = '01a1e573-ca14-72ba-a46a-c84690288e22';
const SEED5_DOC = '01a1f400-0000-7000-8000-000000000501';

async function waitForCondition(fn, description, timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs;
  let lastErr = null;
  while (Date.now() < deadline) {
    try {
      const ok = await fn();
      if (ok) {
        return;
      }
    } catch (err) {
      lastErr = err;
    }
    await new Promise((r) => setTimeout(r, 50));
  }
  throw new Error(`Timed out waiting for condition: ${description}${lastErr ? ` (${lastErr})` : ''}`);
}

async function flushBrowserTicks(page) {
  await page.evaluate(
    () =>
      new Promise((resolve) => {
        Promise.resolve().then(() => {
          requestAnimationFrame(() => {
            setTimeout(resolve, 0);
          });
        });
      }),
  );
}

async function installArchiveNavigationLatch(page) {
  await page.evaluate(() => {
    const ngGlobal = window.ng;
    if (!ngGlobal || typeof ngGlobal.getComponent !== 'function') {
      throw new Error('Angular dev-mode window.ng.getComponent is required for deterministic route-latch control.');
    }
    const el = document.querySelector('elc-archive-page');
    if (!el) {
      throw new Error('elc-archive-page element not found in DOM.');
    }
    const cmp = ngGlobal.getComponent(el);
    if (!cmp || !cmp.router) {
      throw new Error('ArchivePage.router not accessible on live component.');
    }
    const archiveRoute = cmp.router.config.find((r) => r.path === 'archive');
    if (!archiveRoute) {
      throw new Error('Could not find path="archive" in Router.config.');
    }

    const state = {
      holdNext: false,
      pendingQueue: [],
      interceptedCount: 0,
    };

    archiveRoute.runGuardsAndResolvers = 'paramsOrQueryParamsChange';
    archiveRoute.canActivate = [
      (routeSnapshot) => {
        if (!state.holdNext) {
          return true;
        }
        state.interceptedCount += 1;
        return new Promise((resolve) => {
          state.pendingQueue.push({
            id: state.interceptedCount,
            targetQueryParams: { ...routeSnapshot.queryParams },
            resolve,
          });
        });
      },
    ];

    window.__archiveNavLatch = {
      armHold() {
        state.holdNext = true;
      },
      disarmHold() {
        state.holdNext = false;
      },
      pendingCount() {
        return state.pendingQueue.length;
      },
      pendingTargets() {
        return state.pendingQueue.map((item) => ({ id: item.id, targetQueryParams: item.targetQueryParams }));
      },
      releaseNext(allow = true) {
        const next = state.pendingQueue.shift();
        if (!next) {
          return null;
        }
        next.resolve(allow);
        return { id: next.id, targetQueryParams: next.targetQueryParams };
      },
      releaseAll(allow = true) {
        const released = [];
        while (state.pendingQueue.length > 0) {
          const next = state.pendingQueue.shift();
          next.resolve(allow);
          released.push({ id: next.id, targetQueryParams: next.targetQueryParams });
        }
        return released;
      },
    };
  });
}

function createDeferred() {
  let resolve;
  const promise = new Promise((r) => {
    resolve = r;
  });
  return { promise, resolve };
}

/**
 * Deterministic Microsoft Edge verification of WP-0010 / 006 search-navigation ownership,
 * pending-navigation draft preservation, newer-search authority, external Back/Forward sync,
 * and result/source/URL/cursor consistency against real owned API (5590) + PostgreSQL 18.7 (55438).
 *
 * Separates pending route-input propagation from delayed HTTP responses via explicit Promise latches
 * rather than arbitrary sleep assumptions.
 */
async function main() {
  const args = process.argv.slice(2);
  const outIdx = args.indexOf('--output');
  const shotDirIdx = args.indexOf('--screenshot-dir');
  const apiPortIdx = args.indexOf('--api-port');
  const uiPortIdx = args.indexOf('--ui-port');
  const modeIdx = args.indexOf('--mode');

  const outPath = outIdx >= 0 ? args[outIdx + 1] : null;
  const shotDir = shotDirIdx >= 0 ? args[shotDirIdx + 1] : null;
  const apiPort = apiPortIdx >= 0 ? Number(args[apiPortIdx + 1]) : 5590;
  const uiPort = uiPortIdx >= 0 ? Number(args[uiPortIdx + 1]) : 4610;
  const mode = modeIdx >= 0 ? args[modeIdx + 1] : 'post-fix';

  if (!outPath) {
    throw new Error('Usage: node verify_search_navigation_edge.mjs --output <json> [--screenshot-dir <dir>] [--api-port 5590] [--ui-port 4610] [--mode pre-fix|post-fix]');
  }
  mkdirSync(path.dirname(outPath), { recursive: true });
  if (shotDir) {
    mkdirSync(shotDir, { recursive: true });
  }

  const uiBase = `http://127.0.0.1:${uiPort}`;
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const browserVersion = browser.version();
  const context = await browser.newContext({ viewport: { width: 1600, height: 940 } });
  const page = await context.newPage();

  const archiveApiUrls = [];
  page.on('request', (req) => {
    if (req.url().includes('/api/archive')) {
      archiveApiUrls.push(req.url());
    }
  });

  const summary = {
    startedUtc: new Date().toISOString(),
    mode,
    edgeBrowserVersion: browserVersion,
    apiPort,
    uiPort,
    checks: {},
    screenshots: [],
    status: 'failed',
    failureError: null,
  };

  try {
    // =========================================================================
    // CHECK 1: Newer typed draft survives earlier pending navigation completing
    // (Real fast HTTP completes BEFORE route navigation settles!)
    // =========================================================================
    await page.goto(`${uiBase}/archive`, { waitUntil: 'networkidle' });
    await page.getByTestId(`archive-card-${SEED1_DOC}`).waitFor({ state: 'visible', timeout: 25000 });
    await waitForCondition(
      async () => (await page.locator('article.archive-card').count()) === 7,
      'initial 7 archive cards rendered',
    );

    await installArchiveNavigationLatch(page);
    await page.evaluate(() => window.__archiveNavLatch.armHold());

    const reqCountBeforeSubmit1 = archiveApiUrls.length;
    // Select reviewed (triggers navigation #1a) or fill first then submit:
    // Fill 'REV2-ACTIVE-HAWTHORNE' first, then select 'reviewed' (single applyNewQueryAndNavigate call!)
    await page.getByTestId('archive-query-input').fill('REV2-ACTIVE-HAWTHORNE');
    await page.getByTestId('archive-source-select').selectOption('reviewed');

    // Wait for real PostgreSQL + .NET API HTTP search to complete and render SEED1_DOC WHILE route navigation is still held pending!
    await waitForCondition(async () => {
      const headerTxt = (await page.locator('.archive-results-header').textContent()) ?? '';
      const cardCount = await page.locator('article.archive-card').count();
      return (
        headerTxt.includes('Search results for “REV2-ACTIVE-HAWTHORNE” (reviewed values only)') &&
        cardCount === 1
      );
    }, 'HTTP response for REV2-ACTIVE-HAWTHORNE rendered before route navigation settled');

    const pendingBeforeEdit = await page.evaluate(() => ({
      count: window.__archiveNavLatch.pendingCount(),
      targets: window.__archiveNavLatch.pendingTargets(),
      browserSearch: window.location.search,
    }));
    if (pendingBeforeEdit.count !== 1 || pendingBeforeEdit.browserSearch !== '') {
      throw new Error(
        `Expected 1 held pending navigation and empty location.search before draft edit, got: ${JSON.stringify(pendingBeforeEdit)}`,
      );
    }

    // User types a newer unsubmitted draft while Navigation #1 is still pending in Router
    await page.getByTestId('archive-query-input').fill('MULTIPAGE-REVIEWED-ALDER-P2');
    const draftBeforeRelease = await page.getByTestId('archive-query-input').inputValue();
    const reqCountBeforeRelease = archiveApiUrls.length;

    // Deterministically release Navigation #1 and wait for URL commit + microtask/render flush
    const releasedNav1 = await page.evaluate(() => {
      window.__archiveNavLatch.disarmHold();
      return window.__archiveNavLatch.releaseNext(true);
    });
    await waitForCondition(
      async () => page.url().endsWith('/archive?q=REV2-ACTIVE-HAWTHORNE&source=reviewed'),
      'pending Navigation #1 committed URL ?q=REV2-ACTIVE-HAWTHORNE&source=reviewed',
    );
    await flushBrowserTicks(page);

    const draftAfterRelease = await page.getByTestId('archive-query-input').inputValue();
    const sourceAfterRelease = await page.getByTestId('archive-source-select').inputValue();
    const headerAfterRelease = ((await page.locator('.archive-results-header').textContent()) ?? '').trim();
    const reqCountAfterRelease = archiveApiUrls.length;

    summary.checks.c1_pending_nav_preserves_newer_draft = {
      httpCompletedWhileRoutePending: true,
      pendingBeforeEdit,
      releasedNav1,
      draftBeforeRelease,
      draftAfterRelease,
      sourceAfterRelease,
      urlAfterRelease: page.url(),
      headerAfterRelease,
      httpRequestsDuringSubmit1: reqCountBeforeRelease - reqCountBeforeSubmit1,
      duplicateHttpRequestsOnRouteSettle: reqCountAfterRelease - reqCountBeforeRelease,
      passed:
        draftAfterRelease === 'MULTIPAGE-REVIEWED-ALDER-P2' &&
        sourceAfterRelease === 'reviewed' &&
        reqCountAfterRelease === reqCountBeforeRelease,
    };

    if (draftAfterRelease !== 'MULTIPAGE-REVIEWED-ALDER-P2') {
      throw new Error(
        `Criterion (1) FAILED: newer typed draft "MULTIPAGE-REVIEWED-ALDER-P2" was overwritten with "${draftAfterRelease}" when earlier pending navigation settled.`,
      );
    }
    if (reqCountAfterRelease !== reqCountBeforeRelease) {
      throw new Error(
        `Unexpected duplicate /api/archive HTTP request fired when self-initiated navigation settled (${reqCountBeforeRelease} -> ${reqCountAfterRelease}).`,
      );
    }

    if (shotDir) {
      const shot1 = path.join(shotDir, 'sn-01-newer-draft-preserved-after-nav-settle.png');
      await page.screenshot({ path: shot1 });
      summary.screenshots.push(path.relative(repoRoot, shot1).replace(/\\/g, '/'));
    }

    // Submitting that preserved draft now searches MULTIPAGE-REVIEWED-ALDER-P2 cleanly!
    await page.getByTestId('archive-submit-btn').click();
    await waitForCondition(
      async () =>
        page.url().endsWith('/archive?q=MULTIPAGE-REVIEWED-ALDER-P2&source=reviewed') &&
        (await page.getByTestId(`archive-card-${SEED5_DOC}`).isVisible()),
      'submitting preserved newer draft renders SEED5_DOC',
    );

    // =========================================================================
    // CHECK 2A: Newer submitted query/filter & Clear remain authoritative while
    //           earlier navigation was pending in Router
    // =========================================================================
    await page.getByTestId('archive-clear-btn').click();
    await waitForCondition(
      async () => page.url().endsWith('/archive') && (await page.locator('article.archive-card').count()) === 7,
      'cleared back to /archive with 7 cards',
    );

    await page.evaluate(() => window.__archiveNavLatch.armHold());
    await page.getByTestId('archive-query-input').fill('REV2-ACTIVE-HAWTHORNE');
    await page.getByTestId('archive-source-select').selectOption('reviewed');
    await waitForCondition(
      async () => (await page.evaluate(() => window.__archiveNavLatch.pendingCount())) === 1,
      'Navigation #1 held pending for Check 2A supersede',
    );

    // Issue newer submitted search ('Refrigerator Evaporator', 'machine') while Navigation #1 is pending
    await page.evaluate(() => window.__archiveNavLatch.disarmHold());
    await page.getByTestId('archive-query-input').fill('Refrigerator Evaporator');
    await page.getByTestId('archive-source-select').selectOption('machine');
    await page.evaluate(() => window.__archiveNavLatch.releaseAll(true));

    await waitForCondition(
      async () =>
        page.url().endsWith('/archive?q=Refrigerator%20Evaporator&source=machine') &&
        (await page.getByTestId(`archive-card-${SEED2_DOC}`).isVisible()) &&
        (await page.locator('article.archive-card').count()) === 2,
      'newer machine search authoritative over superseded pending navigation',
    );
    await flushBrowserTicks(page);

    if ((await page.getByTestId('archive-query-input').inputValue()) !== 'Refrigerator Evaporator') {
      throw new Error('Check 2A failed: input value rolled back after superseded navigation.');
    }
    if ((await page.getByTestId('archive-source-select').inputValue()) !== 'machine') {
      throw new Error('Check 2A failed: source select rolled back after superseded navigation.');
    }

    // Same-URL Clear superseding a pending navigation when committed URL is already /archive
    await page.getByTestId('archive-clear-btn').click();
    await waitForCondition(
      async () => page.url().endsWith('/archive') && (await page.locator('article.archive-card').count()) === 7,
      'reset to /archive before pending-then-clear check',
    );
    await page.evaluate(() => window.__archiveNavLatch.armHold());
    await page.getByTestId('archive-query-input').fill('REV2-ACTIVE-HAWTHORNE');
    await page.getByTestId('archive-source-select').selectOption('reviewed');
    await waitForCondition(
      async () =>
        (await page.evaluate(() => window.__archiveNavLatch.pendingCount())) === 1 &&
        new URL(page.url()).search === '',
      'Navigation held with committed URL still at /archive',
    );
    await page.evaluate(() => window.__archiveNavLatch.disarmHold());
    await page.getByTestId('archive-clear-btn').click();
    await page.evaluate(() => window.__archiveNavLatch.releaseAll(true));
    await waitForCondition(
      async () =>
        page.url().endsWith('/archive') &&
        (await page.locator('article.archive-card').count()) === 7 &&
        ((await page.locator('.archive-results-header').textContent()) ?? '').includes(
          'Browsing saved documents (all sources)',
        ),
      'Clear back to committed /archive remained authoritative',
    );
    await flushBrowserTicks(page);

    summary.checks.c2a_newer_submit_and_clear_supersede_pending_nav = {
      passed: true,
      finalUrl: page.url(),
      finalDraft: await page.getByTestId('archive-query-input').inputValue(),
      finalSource: await page.getByTestId('archive-source-select').inputValue(),
    };

    // =========================================================================
    // CHECK 2B: Deterministic Promise-latched out-of-order HTTP 200 and HTTP 500
    //           responses suppressed after newer query completes
    // =========================================================================
    const slowSuccessArrived = createDeferred();
    const releaseSlowSuccess = createDeferred();
    const slowErrorArrived = createDeferred();
    const releaseSlowError = createDeferred();
    let slowSuccessFulfilled = false;
    let slowErrorFulfilled = false;

    await page.route('**/api/archive?*', async (route) => {
      const reqUrl = new URL(route.request().url());
      const qParam = reqUrl.searchParams.get('q');
      if (qParam === 'MANUAL-NO-PROVENANCE-KESTREL-0042') {
        slowSuccessArrived.resolve(true);
        await releaseSlowSuccess.promise;
        try {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              query: 'MANUAL-NO-PROVENANCE-KESTREL-0042',
              terms: ['MANUAL-NO-PROVENANCE-KESTREL-0042'],
              source: 'reviewed',
              limit: 20,
              hasMore: false,
              nextCursor: null,
              projectionVersion: 'archive-machine-projection/1',
              items: [],
            }),
          });
          slowSuccessFulfilled = true;
        } catch {
          // Request already aborted by HttpClient unsubscribe — equally valid cancellation!
          slowSuccessFulfilled = true;
        }
        return;
      }
      if (qParam === 'WO-004192') {
        slowErrorArrived.resolve(true);
        await releaseSlowError.promise;
        try {
          await route.fulfill({
            status: 500,
            contentType: 'application/problem+json',
            body: JSON.stringify({
              title: 'Simulated obsolete error',
              status: 500,
              detail: 'Obsolete request failed after newer search.',
            }),
          });
          slowErrorFulfilled = true;
        } catch {
          slowErrorFulfilled = true;
        }
        return;
      }
      await route.fallback();
    });

    await page.getByTestId('archive-query-input').fill('MANUAL-NO-PROVENANCE-KESTREL-0042');
    await page.getByTestId('archive-source-select').selectOption('reviewed');
    await slowSuccessArrived.promise;

    await page.getByTestId('archive-query-input').fill('WO-004192');
    await page.getByTestId('archive-source-select').selectOption('machine');
    await slowErrorArrived.promise;

    // Issue authoritative third search against real PostgreSQL + API
    await page.getByTestId('archive-query-input').fill('MULTIPAGE-REVIEWED-ALDER-P2');
    await page.getByTestId('archive-source-select').selectOption('reviewed');
    await waitForCondition(
      async () =>
        page.url().endsWith('/archive?q=MULTIPAGE-REVIEWED-ALDER-P2&source=reviewed') &&
        (await page.getByTestId(`archive-card-${SEED5_DOC}`).isVisible()),
      'authoritative third search MULTIPAGE-REVIEWED-ALDER-P2 rendered before releasing stale HTTP latches',
    );

    // Deterministically release both older HTTP responses now that #3 has already rendered
    releaseSlowSuccess.resolve(true);
    releaseSlowError.resolve(true);
    await waitForCondition(() => slowSuccessFulfilled && slowErrorFulfilled, 'both stale HTTP latches completed');
    await flushBrowserTicks(page);

    const errBannerCount = await page.getByTestId('archive-error').count();
    const seed5StillVisible = await page.getByTestId(`archive-card-${SEED5_DOC}`).isVisible();
    const headerAfterStaleHttp = ((await page.locator('.archive-results-header').textContent()) ?? '').trim();
    await page.unroute('**/api/archive?*');

    if (
      errBannerCount !== 0 ||
      !seed5StillVisible ||
      !headerAfterStaleHttp.includes('Search results for “MULTIPAGE-REVIEWED-ALDER-P2” (reviewed values only)')
    ) {
      throw new Error(
        `Check 2B failed: stale HTTP callback polluted UI (errCount=${errBannerCount}, seed5=${seed5StillVisible}, header=${headerAfterStaleHttp})`,
      );
    }

    summary.checks.c2b_out_of_order_http_suppressed = {
      passed: true,
      slowSuccessFulfilled,
      slowErrorFulfilled,
      errBannerCount,
      seed5StillVisible,
      headerAfterStaleHttp,
    };

    // =========================================================================
    // CHECK 3: Ordinary external URL deep-link, browser Back/Forward (popstate),
    //          and top-header routerLink="/archive"
    // =========================================================================
    const reqCountBeforeDeepLink = archiveApiUrls.length;
    await page.goto(`${uiBase}/archive?q=Refrigerator%20Evaporator&source=machine`, { waitUntil: 'networkidle' });
    await page.getByTestId(`archive-card-${SEED2_DOC}`).waitFor({ state: 'visible', timeout: 20000 });
    await flushBrowserTicks(page);
    const deepLinkHttpCount = archiveApiUrls.length - reqCountBeforeDeepLink;
    if (deepLinkHttpCount !== 1) {
      throw new Error(`Expected exactly 1 initial HTTP search on deep-link mount, got ${deepLinkHttpCount}`);
    }
    if (
      (await page.getByTestId('archive-query-input').inputValue()) !== 'Refrigerator Evaporator' ||
      (await page.getByTestId('archive-source-select').inputValue()) !== 'machine'
    ) {
      throw new Error('Deep-link initial inputs did not match URL query parameters.');
    }

    // Navigate to a second query via form submit
    await page.getByTestId('archive-query-input').fill('MULTIPAGE-REVIEWED-ALDER-P2');
    await page.getByTestId('archive-source-select').selectOption('reviewed');
    await waitForCondition(
      async () =>
        page.url().endsWith('/archive?q=MULTIPAGE-REVIEWED-ALDER-P2&source=reviewed') &&
        (await page.getByTestId(`archive-card-${SEED5_DOC}`).isVisible()),
      'second search committed before Back/Forward test',
    );

    // Type unsubmitted text, then trigger external browser Back (popstate)
    await page.getByTestId('archive-query-input').fill('UNSUBMITTED-BEFORE-BACK');
    await page.goBack();
    await waitForCondition(
      async () =>
        page.url().endsWith('/archive?q=Refrigerator%20Evaporator&source=machine') &&
        (await page.getByTestId('archive-query-input').inputValue()) === 'Refrigerator Evaporator' &&
        (await page.getByTestId('archive-source-select').inputValue()) === 'machine' &&
        (await page.locator('article.archive-card').count()) === 2,
      'browser Back restored machine query, inputs, and 2 results',
    );

    // Trigger external browser Forward (popstate)
    await page.goForward();
    await waitForCondition(
      async () =>
        page.url().endsWith('/archive?q=MULTIPAGE-REVIEWED-ALDER-P2&source=reviewed') &&
        (await page.getByTestId('archive-query-input').inputValue()) === 'MULTIPAGE-REVIEWED-ALDER-P2' &&
        (await page.getByTestId('archive-source-select').inputValue()) === 'reviewed' &&
        (await page.getByTestId(`archive-card-${SEED5_DOC}`).isVisible()) &&
        (await page.locator('article.archive-card').count()) === 1,
      'browser Forward restored reviewed query, inputs, and SEED5_DOC',
    );

    // Click external top-header routerLink="/archive" while mounted on /archive?q=...
    await page.getByTestId('nav-archive').click();
    await waitForCondition(
      async () =>
        page.url().endsWith('/archive') &&
        (await page.getByTestId('archive-query-input').inputValue()) === '' &&
        (await page.getByTestId('archive-source-select').inputValue()) === 'all' &&
        (await page.locator('article.archive-card').count()) === 7,
      'header nav-archive reset to empty browse (7 cards)',
    );

    if (shotDir) {
      const shot2 = path.join(shotDir, 'sn-02-external-back-forward-and-header-reset.png');
      await page.screenshot({ path: shot2 });
      summary.screenshots.push(path.relative(repoRoot, shot2).replace(/\\/g, '/'));
    }

    summary.checks.c3_external_deeplink_back_forward_and_header = {
      passed: true,
      deepLinkInitialHttpRequests: deepLinkHttpCount,
    };

    // =========================================================================
    // CHECK 4: Results / source labels / URL / cursor & error-state consistency
    //          + zero browser storage or history.state leakage
    // =========================================================================
    await page.getByTestId('archive-query-input').fill('t1 t2 t3 t4 t5 t6 t7 t8 t9');
    await page.getByTestId('archive-source-select').selectOption('reviewed');
    await waitForCondition(
      async () =>
        page.url().includes('source=reviewed') && (await page.getByTestId('archive-error').isVisible()),
      '9-term invalid query displays 400 error banner',
    );
    const staleResultsDuringError = await page.getByTestId('archive-results-section').count();
    if (staleResultsDuringError !== 0) {
      throw new Error(
        `Criterion (4) FAILED: ${staleResultsDuringError} stale results section remained visible alongside failed new query!`,
      );
    }

    await page.getByTestId('archive-clear-btn').click();
    await waitForCondition(
      async () =>
        page.url().endsWith('/archive') &&
        (await page.getByTestId('archive-error').count()) === 0 &&
        (await page.locator('article.archive-card').count()) === 7,
      'Clear recovered cleanly from 400 error to 7-card browse',
    );

    const browserStateAudit = await page.evaluate(() => ({
      localStorageKeys: Object.keys(localStorage),
      sessionStorageKeys: Object.keys(sessionStorage),
      historyStateKeys: window.history.state ? Object.keys(window.history.state) : [],
    }));
    if (browserStateAudit.localStorageKeys.length !== 0 || browserStateAudit.sessionStorageKeys.length !== 0) {
      throw new Error(`Unexpected browser storage keys: ${JSON.stringify(browserStateAudit)}`);
    }
    const nonRouterHistoryKeys = browserStateAudit.historyStateKeys.filter(
      (k) => k !== 'navigationId' && !k.startsWith('ɵrouter'),
    );
    if (nonRouterHistoryKeys.length !== 0) {
      throw new Error(`Unexpected custom keys persisted to window.history.state: ${JSON.stringify(nonRouterHistoryKeys)}`);
    }

    summary.checks.c4_consistency_and_zero_storage = {
      passed: true,
      staleResultsDuringError,
      browserStateAudit,
    };

    summary.status = 'passed';
    summary.completedUtc = new Date().toISOString();
    writeFileSync(outPath, JSON.stringify(summary, null, 2) + '\n', 'utf8');
    console.log(
      `Search-navigation Edge verification PASSED (${browserVersion}; 5/5 deterministic checks green).`,
    );
  } catch (err) {
    summary.status = 'failed';
    summary.completedUtc = new Date().toISOString();
    summary.failureError = err instanceof Error ? err.message : String(err);
    writeFileSync(outPath, JSON.stringify(summary, null, 2) + '\n', 'utf8');
    console.error(`Search-navigation Edge verification FAILED: ${summary.failureError}`);
    process.exitCode = 1;
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
