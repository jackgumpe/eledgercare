/**
 * Focused supplementary Microsoft Edge verifier for WP-0010 / 007 (`eld-f4-reviewer`).
 *
 * Complements the unchanged prepared 6-scenario probe (`../helpers/probe_f4_search_navigation.mjs`)
 * with zero arbitrary `setTimeout` / `waitForTimeout` timer sleeps, specifically exercising:
 *   FX-01: Prolonged Promise-latched pending route activation where real HTTP 200 completes *before*
 *          route activation settles, user types a newer draft, route settles with 0 duplicate HTTP calls,
 *          `window.history.state` has 0 leaked `sourceComponent`/`commandSeq` keys, and submitting
 *          executes the preserved newer draft.
 *   FX-02: Same-URL `NavigationSkipped` semantics (re-submitting the active query refreshes once;
 *          clicking top-bar `Archive search` while diverged vs. already synced at `/archive`).
 *   FX-03: Out-of-order HTTP 503 error callback suppression after a newer valid query succeeds, plus
 *          immediate `response() === null` clearing of prior cards/cursors when a 9-term query returns HTTP 400.
 */

import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..', '..', '..', '..', '..', '..', '..');
const requireFromWeb = createRequire(path.join(repoRoot, 'web', 'package.json'));
const { chromium, expect } = requireFromWeb('@playwright/test');

const SEED_R03 = '01a1e578-8f3a-7e0c-826b-a2c9dc066a8f';
const SEED_R04 = '01a20400-0000-7000-8000-000000000004';
const SEED_R06 = '01a20400-0000-7000-8000-000000000006';
const SEED_R09 = '01a1e8cf-ed70-7826-a834-61d5a3ce13bd';

function parseArgs(argv) {
  const out = { uiPort: 4710, apiPort: 5690, output: '', screenshotDir: '' };
  for (let i = 2; i < argv.length; i += 1) {
    const k = argv[i];
    const v = argv[i + 1];
    if (k === '--ui-port') {
      out.uiPort = Number(v);
      i += 1;
    } else if (k === '--api-port') {
      out.apiPort = Number(v);
      i += 1;
    } else if (k === '--output') {
      out.output = v;
      i += 1;
    } else if (k === '--screenshot-dir') {
      out.screenshotDir = v;
      i += 1;
    } else {
      throw new Error(`Unknown CLI argument: ${k}`);
    }
  }
  if (!out.output || !out.screenshotDir) {
    throw new Error('Both --output and --screenshot-dir are required.');
  }
  return out;
}

function createDeferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

async function flushRenderFrames(page, count = 2) {
  await page.evaluate(async (frames) => {
    for (let i = 0; i < frames; i += 1) {
      await new Promise((r) => requestAnimationFrame(r));
    }
  }, count);
}

async function main() {
  const args = parseArgs(process.argv);
  const baseUrl = `http://127.0.0.1:${args.uiPort}`;
  const receiptPath = path.resolve(repoRoot, args.output);
  const screenshotDir = path.resolve(repoRoot, args.screenshotDir);
  mkdirSync(path.dirname(receiptPath), { recursive: true });
  mkdirSync(screenshotDir, { recursive: true });

  const archiveRequests = [];
  const allApiRequests = [];
  const checks = [];
  const screenshots = [];

  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const browserVersion = browser.version();
    const context = await browser.newContext({ viewport: { width: 1440, height: 920 } });
    const page = await context.newPage();

    page.on('request', (req) => {
      if (req.url().includes('/api/')) {
        allApiRequests.push({ method: req.method(), url: req.url() });
      }
      if (req.url().includes('/api/archive')) {
        archiveRequests.push(req.url());
      }
    });

    const recordShot = async (filename) => {
      const full = path.join(screenshotDir, filename);
      await page.screenshot({ path: full });
      const rel = path.relative(repoRoot, full).replace(/\\/g, '/');
      screenshots.push({
        path: rel,
        bytes: statSync(full).size,
        sha256: createHash('sha256').update(readFileSync(full)).digest('hex'),
      });
      return rel;
    };

    // =========================================================================
    // FX-01: HTTP 200 completes while route activation is Promise-latched pending;
    // newer draft survives route completion with 0 duplicate HTTP calls & clean history.state
    // =========================================================================
    const reqCountBeforeDeepLink = archiveRequests.length;
    await page.goto(`${baseUrl}/archive?source=reviewed`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId(`archive-card-${SEED_R06}`)).toBeVisible({ timeout: 15000 });
    await flushRenderFrames(page, 2);
    const initialDeepLinkRequests = archiveRequests.length - reqCountBeforeDeepLink;
    if (initialDeepLinkRequests !== 1) {
      throw new Error(`Expected exactly 1 HTTP request on initial deep-link mount, got ${initialDeepLinkRequests}`);
    }

    // Install deterministic Promise-latched canActivate gate on live /archive route
    await page.evaluate(() => {
      const ngGlobal = window.ng;
      const cmp = ngGlobal.getComponent(document.querySelector('elc-archive-page'));
      const archiveRoute = cmp.router.config.find((r) => r.path === 'archive');
      const state = { hold: false, queue: [] };
      archiveRoute.runGuardsAndResolvers = 'paramsOrQueryParamsChange';
      archiveRoute.canActivate = [
        () => {
          if (!state.hold) {
            return true;
          }
          return new Promise((resolve) => state.queue.push(resolve));
        },
      ];
      window.__reviewerNavGate = {
        arm: () => {
          state.hold = true;
        },
        disarmAndReleaseAll: () => {
          state.hold = false;
          while (state.queue.length > 0) {
            state.queue.shift()(true);
          }
        },
        pendingCount: () => state.queue.length,
      };
    });

    await page.evaluate(() => window.__reviewerNavGate.arm());
    await page.getByTestId('archive-query-input').fill('WO-009901-CLEAN-HEAD');
    await page.getByTestId('archive-submit-btn').click();

    // Real HTTP completes and renders SEED-R03 while URL is still held at ?source=reviewed!
    await expect(page.getByTestId(`archive-card-${SEED_R03}`)).toBeVisible({ timeout: 15000 });
    const pendingBeforeRelease = await page.evaluate(() => window.__reviewerNavGate.pendingCount());
    const urlWhileLatched = new URL(page.url()).search;
    if (pendingBeforeRelease !== 1 || urlWhileLatched !== '?source=reviewed') {
      throw new Error(`Expected latched navigation (pending=1, search='?source=reviewed'), got pending=${pendingBeforeRelease}, search='${urlWhileLatched}'`);
    }

    // User types a newer draft while Navigation #1 is still pending
    await page.getByTestId('archive-query-input').fill('WO-004724-MP-LINKED');
    const reqCountBeforeLatchRelease = archiveRequests.length;

    await page.evaluate(() => window.__reviewerNavGate.disarmAndReleaseAll());
    await expect(page).toHaveURL(/\/archive\?q=WO-009901-CLEAN-HEAD&source=reviewed$/);
    await flushRenderFrames(page, 3);

    await expect(page.getByTestId('archive-query-input')).toHaveValue('WO-004724-MP-LINKED');
    const reqCountAfterLatchRelease = archiveRequests.length;
    if (reqCountAfterLatchRelease !== reqCountBeforeLatchRelease) {
      throw new Error(`Releasing self-navigation fired duplicate HTTP calls: ${reqCountBeforeLatchRelease} -> ${reqCountAfterLatchRelease}`);
    }

    const historyStateCheck = await page.evaluate(() => {
      const st = window.history.state ?? {};
      return {
        keys: Object.keys(st),
        hasSourceComponent: 'sourceComponent' in st,
        hasCommandSeq: 'commandSeq' in st,
      };
    });
    if (historyStateCheck.hasSourceComponent || historyStateCheck.hasCommandSeq) {
      throw new Error(`Transient NavigationBehaviorOptions.info leaked into window.history.state: ${JSON.stringify(historyStateCheck)}`);
    }

    // Submitting the preserved newer draft executes WO-004724-MP-LINKED and renders SEED-R04!
    await page.getByTestId('archive-submit-btn').click();
    await expect(page).toHaveURL(/\/archive\?q=WO-004724-MP-LINKED&source=reviewed$/);
    await expect(page.getByTestId(`archive-card-${SEED_R04}`)).toBeVisible({ timeout: 15000 });
    const fx01Shot = await recordShot('final-fx01-preserved-draft-submitted-r04.png');
    checks.push({
      id: 'FX-01',
      passed: true,
      detail: {
        initialDeepLinkRequests,
        urlWhileLatched,
        duplicateRequestsOnSettle: reqCountAfterLatchRelease - reqCountBeforeLatchRelease,
        historyStateCheck,
        screenshot: fx01Shot,
      },
    });

    // =========================================================================
    // FX-02: Same-URL `NavigationSkipped` (re-submit active query & top-bar `Archive search`)
    // =========================================================================
    const reqBeforeSameUrlResubmit = archiveRequests.length;
    const sameUrlResp = page.waitForResponse(
      (res) => res.url().includes('/api/archive?') && new URL(res.url()).searchParams.get('q') === 'WO-004724-MP-LINKED',
    );
    await page.getByTestId('archive-submit-btn').click();
    await sameUrlResp;
    await flushRenderFrames(page, 2);
    const sameUrlResubmitDelta = archiveRequests.length - reqBeforeSameUrlResubmit;
    if (sameUrlResubmitDelta !== 1) {
      throw new Error(`Expected exactly 1 HTTP refresh on same-URL Search submit, got ${sameUrlResubmitDelta}`);
    }

    // Clicking top-bar `Archive search` from `/archive?q=WO-004724-MP-LINKED&source=reviewed` resets to `/archive`
    await page.getByTestId('nav-archive').click();
    await expect(page).toHaveURL(/\/archive$/);
    await expect(page.getByTestId(`archive-card-${SEED_R09}`)).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('archive-query-input')).toHaveValue('');
    await expect(page.getByTestId('archive-source-select')).toHaveValue('all');

    // Clicking top-bar `Archive search` AGAIN when already synced at `/archive` skips duplicate HTTP call
    const reqBeforeRedundantNavClick = archiveRequests.length;
    await page.getByTestId('nav-archive').click();
    await flushRenderFrames(page, 3);
    const redundantNavClickDelta = archiveRequests.length - reqBeforeRedundantNavClick;
    if (redundantNavClickDelta !== 0) {
      throw new Error(`Expected 0 HTTP calls on redundant same-URL nav-archive click, got ${redundantNavClickDelta}`);
    }
    checks.push({
      id: 'FX-02',
      passed: true,
      detail: { sameUrlResubmitDelta, redundantNavClickDelta },
    });

    // =========================================================================
    // FX-03: Out-of-order HTTP 503 error suppression + immediate stale-card clearing on HTTP 400
    // =========================================================================
    const slowErrEntered = createDeferred();
    const releaseSlowErr = createDeferred();
    const slowErrFulfilled = createDeferred();

    await page.route('**/api/archive?*', async (route) => {
      const u = new URL(route.request().url());
      if (u.searchParams.get('q') === 'SLOW-STALE-503') {
        slowErrEntered.resolve(true);
        await releaseSlowErr.promise;
        await route.fulfill({
          status: 503,
          contentType: 'application/problem+json',
          body: JSON.stringify({
            title: 'Archive not ready',
            status: 503,
            detail: 'Simulated late 503 from superseded query.',
            code: 'archive_not_ready',
          }),
        });
        slowErrFulfilled.resolve(true);
        return;
      }
      await route.fallback();
    });

    await page.getByTestId('archive-query-input').fill('SLOW-STALE-503');
    await page.getByTestId('archive-submit-btn').click();
    await slowErrEntered.promise;
    // Prior browse cards must already be cleared while SLOW-STALE-503 is loading (`response.set(null)`)!
    await expect(page.getByTestId('archive-results-section')).toHaveCount(0);

    // Issue newer valid query before SLOW-STALE-503 finishes
    await page.getByTestId('archive-query-input').fill('WO-009901-CLEAN-HEAD');
    await page.getByTestId('archive-source-select').selectOption('reviewed');
    await expect(page.getByTestId(`archive-card-${SEED_R03}`)).toBeVisible({ timeout: 15000 });

    // Release late HTTP 503 from superseded query -> must NOT display error banner or clear SEED-R03!
    releaseSlowErr.resolve(true);
    await slowErrFulfilled.promise;
    await flushRenderFrames(page, 3);
    await page.unroute('**/api/archive?*');

    await expect(page.getByTestId('archive-error')).toHaveCount(0);
    await expect(page.getByTestId(`archive-card-${SEED_R03}`)).toBeVisible();

    // Now submit an invalid 9-word query -> HTTP 400 must clear SEED-R03 cards/cursors immediately!
    await page.getByTestId('archive-query-input').fill('t1 t2 t3 t4 t5 t6 t7 t8 t9');
    await page.getByTestId('archive-submit-btn').click();
    await expect(page.getByTestId('archive-error')).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('archive-results-section')).toHaveCount(0);
    await expect(page.getByTestId(`archive-card-${SEED_R03}`)).toHaveCount(0);
    const fx03Shot = await recordShot('final-fx03-400-error-clears-stale-cards.png');

    // Recover via Clear
    await page.getByTestId('archive-clear-btn').click();
    await expect(page).toHaveURL(/\/archive$/);
    await expect(page.getByTestId('archive-error')).toHaveCount(0);
    await expect(page.getByTestId(`archive-card-${SEED_R09}`)).toBeVisible({ timeout: 15000 });

    checks.push({
      id: 'FX-03',
      passed: true,
      detail: { late503Suppressed: true, staleCardsClearedOn400: true, screenshot: fx03Shot },
    });

    const nonGetCalls = allApiRequests.filter((r) => r.method !== 'GET' && r.method !== 'HEAD');
    const storageState = await page.evaluate(() => ({
      local: Object.keys(window.localStorage).length,
      session: Object.keys(window.sessionStorage).length,
    }));
    if (nonGetCalls.length !== 0 || storageState.local !== 0 || storageState.session !== 0) {
      throw new Error(`Unexpected mutating calls or storage keys: nonGet=${nonGetCalls.length}, storage=${JSON.stringify(storageState)}`);
    }

    const receipt = {
      schema: 'eledgercare.wp-0010.reviewer-final-navigation-extras-receipt/1',
      verified_at_utc: new Date().toISOString(),
      reviewer: 'eld-f4-reviewer',
      arbitrary_sleep_calls: 0,
      browser_channel: 'msedge',
      browser_version: browserVersion,
      ui_port: args.uiPort,
      api_port: args.apiPort,
      observed_api_get_count: allApiRequests.length,
      observed_non_get_api_count: nonGetCalls.length,
      local_storage_keys: storageState.local,
      session_storage_keys: storageState.session,
      checks,
      screenshots,
      all_passed: true,
    };

    writeFileSync(receiptPath, JSON.stringify(receipt, null, 2) + '\n', 'utf8');
    console.log(`PASS [final-extras]: Edge ${browserVersion} verified FX-01, FX-02, FX-03 (0 arbitrary sleeps).`);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
