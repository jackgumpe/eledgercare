/**
 * Deterministic Microsoft Edge regression & reproduction probe for WP-0010 F4-04
 * search-navigation / draft / active-query ownership (`eld-f4-reviewer`, `/007` preparation).
 *
 * Strictly zero arbitrary `setTimeout` / `waitForTimeout` sleeps:
 *   - Uses explicit Promise barriers in Playwright `page.route(...)` to control HTTP response order.
 *   - Uses exact synchronous post-click (`window.location.search` pre-commit) and one-shot
 *     `history.pushState`/`replaceState` (`queueMicrotask` pre-zoneless-rAF-`effect()`) hooks plus
 *     `requestAnimationFrame` render-frame barriers.
 *
 * Modes:
 *   --mode enforce-ownership : Exits 0 iff SN-01A, SN-01B, SN-02A, SN-02B, SN-03, and SN-04 ALL pass
 *                              (exits 1 deterministically on unchanged `c383021b`; target pass gate for `/006`->`/007`).
 */

import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..', '..', '..', '..', '..', '..');
const requireFromWeb = createRequire(path.join(repoRoot, 'web', 'package.json'));
const { chromium, expect } = requireFromWeb('@playwright/test');

const SEED_R01 = '01a1e571-2838-714b-861b-bf0835d7c90a';
const SEED_R02 = '01a1e573-ca14-72ba-a46a-c84690288e22';
const SEED_R03 = '01a1e578-8f3a-7e0c-826b-a2c9dc066a8f';
const SEED_R04 = '01a20400-0000-7000-8000-000000000004';
const SEED_R05 = '01a20400-0000-7000-8000-000000000005';
const SEED_R06 = '01a20400-0000-7000-8000-000000000006';
const SEED_R07 = '01a20400-0000-7000-8000-000000000007';
const SEED_R08 = '01a1e8cf-ec7a-744c-bbd4-04074813c931';
const SEED_R09 = '01a1e8cf-ed70-7826-a834-61d5a3ce13bd';

const EXPECTED_BROWSE_ORDER = [
  SEED_R09,
  SEED_R08,
  SEED_R07,
  SEED_R06,
  SEED_R05,
  SEED_R04,
  SEED_R03,
  SEED_R02,
  SEED_R01,
];

function parseArgs(argv) {
  const out = {
    mode: 'enforce-ownership',
    uiPort: 4710,
    apiPort: 5690,
    output: '',
    screenshotDir: '',
    tag: 'probe',
  };
  for (let i = 2; i < argv.length; i += 1) {
    const k = argv[i];
    const v = argv[i + 1];
    if (k === '--mode') {
      out.mode = v;
      i += 1;
    } else if (k === '--ui-port') {
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
    } else if (k === '--tag') {
      out.tag = v;
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

function emptyArchiveJson(query, source) {
  return JSON.stringify({
    query,
    terms: query.trim().length > 0 ? query.trim().split(/\s+/) : [],
    source,
    limit: 20,
    hasMore: false,
    nextCursor: null,
    projectionVersion: 'archive-machine-projection/1',
    items: [],
  });
}

async function main() {
  const args = parseArgs(process.argv);
  const baseUrl = `http://127.0.0.1:${args.uiPort}`;
  const receiptPath = path.resolve(repoRoot, args.output);
  const screenshotDir = path.resolve(repoRoot, args.screenshotDir);
  mkdirSync(path.dirname(receiptPath), { recursive: true });
  mkdirSync(screenshotDir, { recursive: true });

  const observedApiRequests = [];
  const scenarios = [];
  const capturedScreenshots = [];

  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const browserVersion = browser.version();
    const context = await browser.newContext({ viewport: { width: 1440, height: 920 } });
    const page = await context.newPage();

    page.on('request', (req) => {
      if (req.url().includes('/api/')) {
        const parsed = new URL(req.url());
        observedApiRequests.push({
          method: req.method(),
          pathname: parsed.pathname,
          search: parsed.search,
          q: parsed.searchParams.get('q'),
          source: parsed.searchParams.get('source'),
        });
      }
    });

    const recordShot = async (filename) => {
      const full = path.join(screenshotDir, filename);
      await page.screenshot({ path: full });
      capturedScreenshots.push({
        path: path.relative(repoRoot, full).replace(/\\/g, '/'),
        bytes: statSync(full).size,
        sha256: createHash('sha256').update(readFileSync(full)).digest('hex'),
      });
      return path.relative(repoRoot, full).replace(/\\/g, '/');
    };

    // =========================================================================
    // SN-01A: Newer typed draft while Router Promise is pending (`location.search` pre-commit)
    // =========================================================================
    {
      await page.goto(`${baseUrl}/archive?source=reviewed`, { waitUntil: 'domcontentloaded' });
      await expect(page.getByTestId(`archive-card-${SEED_R06}`)).toBeVisible({ timeout: 15000 });

      await page.getByTestId('archive-query-input').fill('FIRST-PENDING-NAV-A');

      const navAFirstResp = page.waitForResponse(
        (res) => res.url().includes('/api/archive?') && new URL(res.url()).searchParams.get('q') === 'FIRST-PENDING-NAV-A',
      );

      const hookA = await page.evaluate(() => {
        const input = document.querySelector('[data-testid="archive-query-input"]');
        const submitBtn = document.querySelector('[data-testid="archive-submit-btn"]');
        const searchBeforeClick = window.location.search;
        submitBtn.click();
        const searchImmediatelyAfterClick = window.location.search;
        input.value = 'WO-009901-CLEAN-HEAD';
        input.dispatchEvent(
          new InputEvent('input', {
            bubbles: true,
            data: 'WO-009901-CLEAN-HEAD',
            inputType: 'insertText',
          }),
        );
        return {
          searchBeforeClick,
          searchImmediatelyAfterClick,
          routerWasPendingAtEdit: searchImmediatelyAfterClick === '?source=reviewed',
          domValueImmediatelyAfterEdit: input.value,
        };
      });

      await navAFirstResp;
      await flushRenderFrames(page, 3);

      const domValueAfterFirstNavSettled = await page.getByTestId('archive-query-input').inputValue();
      const reqCountBeforeSecondClick = observedApiRequests.length;

      // Now user clicks Search expecting the visible draft ('WO-009901-CLEAN-HEAD') to be submitted!
      const secondClickRespPromise = page.waitForResponse((res) => res.url().includes('/api/archive?'));
      await page.getByTestId('archive-submit-btn').click();
      const secondClickResp = await secondClickRespPromise;
      await flushRenderFrames(page, 3);

      const secondClickSubmittedQ = new URL(secondClickResp.url()).searchParams.get('q');
      const finalUrl = page.url();
      const domValueAfterSecondClick = await page.getByTestId('archive-query-input').inputValue();
      const r03Visible = (await page.getByTestId(`archive-card-${SEED_R03}`).count()) > 0 &&
        (await page.getByTestId(`archive-card-${SEED_R03}`).isVisible());
      const emptyVisible = (await page.getByTestId('archive-empty').count()) > 0 &&
        (await page.getByTestId('archive-empty').isVisible());

      const shotPath = await recordShot(`${args.tag}-01-sn01a-pending-promise-draft.png`);

      const passed =
        hookA.routerWasPendingAtEdit === true &&
        domValueAfterFirstNavSettled === 'WO-009901-CLEAN-HEAD' &&
        secondClickSubmittedQ === 'WO-009901-CLEAN-HEAD' &&
        finalUrl.includes('q=WO-009901-CLEAN-HEAD') &&
        domValueAfterSecondClick === 'WO-009901-CLEAN-HEAD' &&
        r03Visible === true &&
        emptyVisible === false;

      scenarios.push({
        id: 'SN-01A',
        name: 'pending_router_promise_draft_survives_and_submits_authoritatively',
        passed,
        detail: {
          ...hookA,
          domValueAfterFirstNavSettled,
          secondClickSubmittedQ,
          domValueAfterSecondClick,
          finalUrl,
          r03Visible,
          emptyVisible,
          emittedRequestsDuringSecondClick: observedApiRequests.slice(reqCountBeforeSecondClick),
          screenshot: shotPath,
        },
      });
    }

    // =========================================================================
    // SN-01B: Newer typed draft AFTER `history.pushState`/`replaceState`, BEFORE zoneless rAF `effect()`
    // =========================================================================
    {
      await page.goto(`${baseUrl}/archive?source=reviewed`, { waitUntil: 'domcontentloaded' });
      await expect(page.getByTestId(`archive-card-${SEED_R06}`)).toBeVisible({ timeout: 15000 });

      await page.getByTestId('archive-query-input').fill('FIRST-PENDING-NAV-B');

      const navBFirstResp = page.waitForResponse(
        (res) => res.url().includes('/api/archive?') && new URL(res.url()).searchParams.get('q') === 'FIRST-PENDING-NAV-B',
      );

      const hookB = await page.evaluate(async () => {
        const input = document.querySelector('[data-testid="archive-query-input"]');
        const submitBtn = document.querySelector('[data-testid="archive-submit-btn"]');
        const origPush = history.pushState;
        const origReplace = history.replaceState;
        let restored = false;
        const restore = () => {
          if (!restored) {
            restored = true;
            history.pushState = origPush;
            history.replaceState = origReplace;
          }
        };

        try {
          return await new Promise((resolveHook, rejectHook) => {
            let triggered = false;
            const wrap = (origFn) =>
              function (...hArgs) {
                const ret = origFn.apply(this, hArgs);
                if (!triggered && String(hArgs[2] ?? '').includes('FIRST-PENDING-NAV-B')) {
                  triggered = true;
                  restore();
                  const locationAtHistoryCommit = window.location.search;
                  // Queue right after Router writes ComponentInputBinding signal `q`, BEFORE zoneless rAF flushes `effect()`!
                  queueMicrotask(() => {
                    try {
                      input.value = 'WO-004724-MP-LINKED';
                      input.dispatchEvent(
                        new InputEvent('input', {
                          bubbles: true,
                          data: 'WO-004724-MP-LINKED',
                          inputType: 'insertText',
                        }),
                      );
                      requestAnimationFrame(() =>
                        requestAnimationFrame(() =>
                          resolveHook({
                            historyHookTriggered: true,
                            locationAtHistoryCommit,
                            domValueAfterZonelessFlush: input.value,
                          }),
                        ),
                      );
                    } catch (e) {
                      rejectHook(e);
                    }
                  });
                }
                return ret;
              };

            history.pushState = wrap(origPush);
            history.replaceState = wrap(origReplace);
            submitBtn.click();
          });
        } finally {
          restore();
        }
      });

      await navBFirstResp;
      await flushRenderFrames(page, 2);

      const domValueBeforeSecondSubmit = await page.getByTestId('archive-query-input').inputValue();
      const secondRespPromise = page.waitForResponse((res) => res.url().includes('/api/archive?'));
      await page.getByTestId('archive-submit-btn').click();
      const secondResp = await secondRespPromise;
      await flushRenderFrames(page, 3);

      const secondSubmittedQ = new URL(secondResp.url()).searchParams.get('q');
      const r04Visible = (await page.getByTestId(`archive-card-${SEED_R04}`).count()) > 0 &&
        (await page.getByTestId(`archive-card-${SEED_R04}`).isVisible());
      const shotPath = await recordShot(`${args.tag}-02-sn01b-post-pushstate-pre-zoneless-effect.png`);

      const passed =
        hookB.historyHookTriggered === true &&
        hookB.locationAtHistoryCommit.includes('FIRST-PENDING-NAV-B') &&
        domValueBeforeSecondSubmit === 'WO-004724-MP-LINKED' &&
        secondSubmittedQ === 'WO-004724-MP-LINKED' &&
        page.url().includes('q=WO-004724-MP-LINKED') &&
        r04Visible === true;

      scenarios.push({
        id: 'SN-01B',
        name: 'post_pushstate_pre_zoneless_effect_draft_survives_and_submits_authoritatively',
        passed,
        detail: {
          ...hookB,
          domValueBeforeSecondSubmit,
          secondSubmittedQ,
          finalUrl: page.url(),
          r04Visible,
          screenshot: shotPath,
        },
      });
    }

    // =========================================================================
    // SN-02A: Pending-nav draft edit + Source filter change + out-of-order older HTTP completion
    // =========================================================================
    {
      await page.goto(`${baseUrl}/archive?source=reviewed`, { waitUntil: 'domcontentloaded' });
      await expect(page.getByTestId(`archive-card-${SEED_R06}`)).toBeVisible({ timeout: 15000 });

      const olderEnteredWire = createDeferred();
      const releaseOlderHttp = createDeferred();
      const olderFulfilledDone = createDeferred();

      await page.route('**/api/archive?*', async (route) => {
        const u = new URL(route.request().url());
        if (u.searchParams.get('q') === 'SLOW-OLDER-SEARCH-2A' && u.searchParams.get('source') === 'reviewed') {
          olderEnteredWire.resolve(true);
          await releaseOlderHttp.promise;
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: emptyArchiveJson('SLOW-OLDER-SEARCH-2A', 'reviewed'),
          });
          olderFulfilledDone.resolve(true);
          return;
        }
        await route.fallback();
      });

      await page.getByTestId('archive-query-input').fill('SLOW-OLDER-SEARCH-2A');

      // Submit Search 1 and immediately type 'Refrigerator Evaporator' while Router #1 is pending
      await page.evaluate(() => {
        const input = document.querySelector('[data-testid="archive-query-input"]');
        const submitBtn = document.querySelector('[data-testid="archive-submit-btn"]');
        submitBtn.click();
        input.value = 'Refrigerator Evaporator';
        input.dispatchEvent(
          new InputEvent('input', {
            bubbles: true,
            data: 'Refrigerator Evaporator',
            inputType: 'insertText',
          }),
        );
      });

      await olderEnteredWire.promise;
      await flushRenderFrames(page, 3);

      // Now user switches Source filter to 'machine' while Search 1 HTTP is still held in flight!
      const filterRespPromise = page.waitForResponse(
        (res) => res.url().includes('/api/archive?') && new URL(res.url()).searchParams.get('source') === 'machine',
      );
      await page.getByTestId('archive-source-select').selectOption('machine');
      const filterResp = await filterRespPromise;
      await flushRenderFrames(page, 3);

      // Now release Search 1's slow HTTP response out-of-order AFTER the 'machine' search completed!
      releaseOlderHttp.resolve(true);
      await olderFulfilledDone.promise;
      await flushRenderFrames(page, 3);
      await page.unroute('**/api/archive?*');

      const filterSubmittedQ = new URL(filterResp.url()).searchParams.get('q');
      const r02Visible = (await page.getByTestId(`archive-card-${SEED_R02}`).count()) > 0 &&
        (await page.getByTestId(`archive-card-${SEED_R02}`).isVisible());
      const r04Visible = (await page.getByTestId(`archive-card-${SEED_R04}`).count()) > 0 &&
        (await page.getByTestId(`archive-card-${SEED_R04}`).isVisible());
      const emptyVisible = (await page.getByTestId('archive-empty').count()) > 0 &&
        (await page.getByTestId('archive-empty').isVisible());
      const selectedSourceAfter = await page.getByTestId('archive-source-select').inputValue();
      const inputAfter = await page.getByTestId('archive-query-input').inputValue();

      const passed =
        filterSubmittedQ === 'Refrigerator Evaporator' &&
        selectedSourceAfter === 'machine' &&
        inputAfter === 'Refrigerator Evaporator' &&
        (page.url().includes('q=Refrigerator%20Evaporator') || page.url().includes('q=Refrigerator+Evaporator')) &&
        page.url().includes('source=machine') &&
        r02Visible === true &&
        r04Visible === true &&
        emptyVisible === false;

      scenarios.push({
        id: 'SN-02A',
        name: 'pending_nav_draft_plus_source_filter_change_beats_out_of_order_older_http',
        passed,
        detail: {
          filterSubmittedQ,
          selectedSourceAfter,
          inputAfter,
          finalUrl: page.url(),
          r02Visible,
          r04Visible,
          emptyVisible,
        },
      });
    }

    // =========================================================================
    // SN-02B: Immediate back-to-back two submits in same task + out-of-order HTTP completion
    // =========================================================================
    {
      await page.goto(`${baseUrl}/archive?source=reviewed`, { waitUntil: 'domcontentloaded' });
      await expect(page.getByTestId(`archive-card-${SEED_R06}`)).toBeVisible({ timeout: 15000 });

      let older2BIntercepted = false;
      const releaseOlder2B = createDeferred();
      const older2BFulfilled = createDeferred();

      await page.route('**/api/archive?*', async (route) => {
        const u = new URL(route.request().url());
        if (u.searchParams.get('q') === 'SLOW-OLDER-SEARCH-2B') {
          older2BIntercepted = true;
          await releaseOlder2B.promise;
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: emptyArchiveJson('SLOW-OLDER-SEARCH-2B', 'reviewed'),
          });
          older2BFulfilled.resolve(true);
          return;
        }
        await route.fallback();
      });

      const fast2BRespPromise = page.waitForResponse(
        (res) => res.url().includes('/api/archive?') && new URL(res.url()).searchParams.get('q') === 'WO-009901-CLEAN-HEAD',
      );

      await page.evaluate(() => {
        const input = document.querySelector('[data-testid="archive-query-input"]');
        const submitBtn = document.querySelector('[data-testid="archive-submit-btn"]');
        input.value = 'SLOW-OLDER-SEARCH-2B';
        input.dispatchEvent(new InputEvent('input', { bubbles: true }));
        submitBtn.click();

        input.value = 'WO-009901-CLEAN-HEAD';
        input.dispatchEvent(new InputEvent('input', { bubbles: true }));
        submitBtn.click();
      });

      await fast2BRespPromise;
      await flushRenderFrames(page, 3);

      releaseOlder2B.resolve(true);
      if (older2BIntercepted) {
        await older2BFulfilled.promise;
      }
      await flushRenderFrames(page, 2);
      await page.unroute('**/api/archive?*');

      const r03Visible = (await page.getByTestId(`archive-card-${SEED_R03}`).count()) > 0 &&
        (await page.getByTestId(`archive-card-${SEED_R03}`).isVisible());
      const emptyVisible = (await page.getByTestId('archive-empty').count()) > 0 &&
        (await page.getByTestId('archive-empty').isVisible());
      const inputAfter = await page.getByTestId('archive-query-input').inputValue();

      const passed =
        page.url().includes('q=WO-009901-CLEAN-HEAD') &&
        inputAfter === 'WO-009901-CLEAN-HEAD' &&
        r03Visible === true &&
        emptyVisible === false;

      scenarios.push({
        id: 'SN-02B',
        name: 'same_turn_rapid_double_submit_keeps_newest_query_and_url',
        passed,
        detail: {
          older2BIntercepted,
          inputAfter,
          finalUrl: page.url(),
          r03Visible,
          emptyVisible,
        },
      });
    }

    // =========================================================================
    // SN-03: Deterministic zero-sleep reproduction of `prefreeze-dryrun-failure-06`
    // (`review-back-to-archive` with `response() === null` + pending-nav edit + second submit)
    // =========================================================================
    {
      await page.goto(
        `${baseUrl}/documents/${SEED_R01}/review/revisions/2?returnSource=reviewed&returnQ=7.50%25%20Cap_Rate%20%5C&field=property_name`,
        { waitUntil: 'domcontentloaded' },
      );
      await expect(page.getByTestId('historical-revision-banner')).toContainText(
        'Viewing immutable historical Revision #2 (reviewed)',
        { timeout: 15000 },
      );

      const restoreEnteredWire = createDeferred();
      const releaseRestoreHttp = createDeferred();
      const restoreFulfilled = createDeferred();
      const stale1EnteredWire = createDeferred();
      const releaseStale1Http = createDeferred();
      const stale1Fulfilled = createDeferred();
      let stale1RequestCount = 0;

      await page.route('**/api/archive?*', async (route) => {
        const u = new URL(route.request().url());
        const qParam = u.searchParams.get('q');
        if (qParam === '7.50% Cap_Rate \\') {
          restoreEnteredWire.resolve(true);
          await releaseRestoreHttp.promise;
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: emptyArchiveJson('7.50% Cap_Rate \\', 'reviewed'),
          });
          restoreFulfilled.resolve(true);
          return;
        }
        if (qParam === 'SLOW-REVIEWER-STALE-1') {
          stale1RequestCount += 1;
          stale1EnteredWire.resolve(true);
          await releaseStale1Http.promise;
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: emptyArchiveJson('SLOW-REVIEWER-STALE-1', 'reviewed'),
          });
          stale1Fulfilled.resolve(true);
          return;
        }
        await route.fallback();
      });

      // Return to archive while holding initial restore HTTP open so `this.response()` is deterministically `null`!
      await page.getByTestId('review-back-to-archive').click();
      await expect(page).toHaveURL(/\/archive\?q=7.50%25%20Cap_Rate%20%5C&source=reviewed$/);
      await restoreEnteredWire.promise;

      await page.getByTestId('archive-query-input').fill('SLOW-REVIEWER-STALE-1');

      // Submit Search 1 ('SLOW-REVIEWER-STALE-1') and edit input to 'WO-009901-CLEAN-HEAD' while Router #1 is pending
      await page.evaluate(() => {
        const input = document.querySelector('[data-testid="archive-query-input"]');
        const submitBtn = document.querySelector('[data-testid="archive-submit-btn"]');
        submitBtn.click();
        input.value = 'WO-009901-CLEAN-HEAD';
        input.dispatchEvent(
          new InputEvent('input', {
            bubbles: true,
            data: 'WO-009901-CLEAN-HEAD',
            inputType: 'insertText',
          }),
        );
      });

      await stale1EnteredWire.promise;
      await flushRenderFrames(page, 3);

      // Click Search #2!
      const secondClickRespPromise = page.waitForResponse((res) => res.url().includes('/api/archive?'));
      // Note: if c383021b re-submits 'SLOW-REVIEWER-STALE-1', our route handler holds it until releaseStale1Http!
      // So release stale1 & restore AFTER observing which query Search #2 emitted on the wire!
      const secondClickWireReqPromise = page.waitForRequest((req) => req.url().includes('/api/archive?'));
      await page.getByTestId('archive-submit-btn').click();
      const secondClickWireReq = await secondClickWireReqPromise;
      const secondClickWireQ = new URL(secondClickWireReq.url()).searchParams.get('q');

      // Now release held older HTTP gates so all in-flight responses finish deterministically!
      releaseRestoreHttp.resolve(true);
      releaseStale1Http.resolve(true);
      await secondClickRespPromise;
      await stale1Fulfilled.promise;
      await flushRenderFrames(page, 3);
      await page.unroute('**/api/archive?*');

      const r03Visible = (await page.getByTestId(`archive-card-${SEED_R03}`).count()) > 0 &&
        (await page.getByTestId(`archive-card-${SEED_R03}`).isVisible());
      const emptyVisible = (await page.getByTestId('archive-empty').count()) > 0 &&
        (await page.getByTestId('archive-empty').isVisible());
      const domInputAfter = await page.getByTestId('archive-query-input').inputValue();
      const shotPath = await recordShot(`${args.tag}-03-sn03-prefreeze06-deterministic-repro.png`);

      const passed =
        secondClickWireQ === 'WO-009901-CLEAN-HEAD' &&
        page.url().includes('q=WO-009901-CLEAN-HEAD') &&
        domInputAfter === 'WO-009901-CLEAN-HEAD' &&
        r03Visible === true &&
        emptyVisible === false;

      scenarios.push({
        id: 'SN-03',
        name: 'null_response_back_from_review_pending_nav_rapid_resubmit_deterministic',
        passed,
        detail: {
          secondClickWireQ,
          stale1RequestCount,
          domInputAfter,
          finalUrl: page.url(),
          r03Visible,
          emptyVisible,
          screenshot: shotPath,
        },
      });
    }

    // =========================================================================
    // SN-04: Ordinary external URL deep-link, browser Back/Forward (`popstate`), & Clear
    // =========================================================================
    {
      await page.goto(`${baseUrl}/archive?q=WO-009901-CLEAN-HEAD&source=reviewed`, {
        waitUntil: 'domcontentloaded',
      });
      await expect(page.getByTestId(`archive-card-${SEED_R03}`)).toBeVisible({ timeout: 15000 });
      const deepLinkInput = await page.getByTestId('archive-query-input').inputValue();
      const deepLinkSource = await page.getByTestId('archive-source-select').inputValue();

      // Step to History Entry 2: q='Cedar Hollow', source='all'
      await page.getByTestId('archive-query-input').fill('Cedar Hollow');
      await page.getByTestId('archive-source-select').selectOption('all');
      await expect(page).toHaveURL(/\/archive\?q=Cedar(%20|\+)Hollow$/);
      await expect(page.getByTestId(`archive-card-${SEED_R06}`)).toBeVisible({ timeout: 15000 });

      // Step to History Entry 3: q='Refrigerator Evaporator', source='machine'
      await page.getByTestId('archive-query-input').fill('Refrigerator Evaporator');
      await page.getByTestId('archive-source-select').selectOption('machine');
      await expect(page).toHaveURL(/\/archive\?q=Refrigerator(%20|\+)Evaporator&source=machine$/);
      await expect(page.getByTestId(`archive-card-${SEED_R02}`)).toBeVisible({ timeout: 15000 });

      // External Back #1 -> Entry 2 ('Cedar Hollow', 'all')
      await page.goBack({ waitUntil: 'domcontentloaded' });
      await expect(page).toHaveURL(/\/archive\?q=Cedar(%20|\+)Hollow$/);
      await expect(page.getByTestId(`archive-card-${SEED_R06}`)).toBeVisible({ timeout: 15000 });
      const back1Input = await page.getByTestId('archive-query-input').inputValue();
      const back1Source = await page.getByTestId('archive-source-select').inputValue();

      // External Back #2 -> Entry 1 ('WO-009901-CLEAN-HEAD', 'reviewed')
      await page.goBack({ waitUntil: 'domcontentloaded' });
      await expect(page).toHaveURL(/\/archive\?q=WO-009901-CLEAN-HEAD&source=reviewed$/);
      await expect(page.getByTestId(`archive-card-${SEED_R03}`)).toBeVisible({ timeout: 15000 });
      const back2Input = await page.getByTestId('archive-query-input').inputValue();
      const back2Source = await page.getByTestId('archive-source-select').inputValue();

      // External Forward #1 -> Entry 2 ('Cedar Hollow', 'all')
      await page.goForward({ waitUntil: 'domcontentloaded' });
      await expect(page).toHaveURL(/\/archive\?q=Cedar(%20|\+)Hollow$/);
      await expect(page.getByTestId(`archive-card-${SEED_R06}`)).toBeVisible({ timeout: 15000 });
      const forward1Input = await page.getByTestId('archive-query-input').inputValue();
      const forward1Source = await page.getByTestId('archive-source-select').inputValue();

      // Clear -> '/archive' browse all 9 seeds in deterministic order
      await page.getByTestId('archive-clear-btn').click();
      await expect(page).toHaveURL(/\/archive$/);
      await expect(page.getByTestId(`archive-card-${SEED_R09}`)).toBeVisible({ timeout: 15000 });
      await expect(page.locator('[data-testid^="archive-card-title-"]')).toHaveCount(9);
      const clearOrder = await page
        .locator('article[data-testid^="archive-card-"]')
        .evaluateAll((els) => els.map((e) => e.getAttribute('data-testid').replace('archive-card-', '')));
      const clearInput = await page.getByTestId('archive-query-input').inputValue();
      const clearSource = await page.getByTestId('archive-source-select').inputValue();
      const pageIndicator = (await page.getByTestId('archive-page-indicator').textContent()).trim();

      const passed =
        deepLinkInput === 'WO-009901-CLEAN-HEAD' &&
        deepLinkSource === 'reviewed' &&
        back1Input === 'Cedar Hollow' &&
        back1Source === 'all' &&
        back2Input === 'WO-009901-CLEAN-HEAD' &&
        back2Source === 'reviewed' &&
        forward1Input === 'Cedar Hollow' &&
        forward1Source === 'all' &&
        clearInput === '' &&
        clearSource === 'all' &&
        pageIndicator.includes('Page 1') &&
        JSON.stringify(clearOrder) === JSON.stringify(EXPECTED_BROWSE_ORDER);

      scenarios.push({
        id: 'SN-04',
        name: 'external_deep_link_browser_back_forward_and_clear_consistency',
        passed,
        detail: {
          deepLinkInput,
          deepLinkSource,
          back1Input,
          back1Source,
          back2Input,
          back2Source,
          forward1Input,
          forward1Source,
          clearInput,
          clearSource,
          pageIndicator,
          clearOrderMatchesExpected: JSON.stringify(clearOrder) === JSON.stringify(EXPECTED_BROWSE_ORDER),
        },
      });
    }

    const nonGetCalls = observedApiRequests.filter((r) => r.method !== 'GET' && r.method !== 'HEAD');
    const storageState = await page.evaluate(() => ({
      local: Object.keys(window.localStorage).length,
      session: Object.keys(window.sessionStorage).length,
    }));

    const passedIds = scenarios.filter((s) => s.passed).map((s) => s.id);
    const failedIds = scenarios.filter((s) => !s.passed).map((s) => s.id);
    const allOwnershipPassed =
      failedIds.length === 0 &&
      nonGetCalls.length === 0 &&
      storageState.local === 0 &&
      storageState.session === 0;

    const receipt = {
      schema: 'eledgercare.wp-0010.reviewer-search-navigation-probe-receipt/1',
      verified_at_utc: new Date().toISOString(),
      reviewer: 'eld-f4-reviewer',
      mode: args.mode,
      tag: args.tag,
      arbitrary_sleep_calls: 0,
      browser_channel: 'msedge',
      browser_version: browserVersion,
      ui_port: args.uiPort,
      api_port: args.apiPort,
      passed_scenario_ids: passedIds,
      failed_scenario_ids: failedIds,
      all_ownership_passed: allOwnershipPassed,
      observed_api_get_count: observedApiRequests.length,
      observed_non_get_api_count: nonGetCalls.length,
      local_storage_keys: storageState.local,
      session_storage_keys: storageState.session,
      screenshots: capturedScreenshots,
      scenarios,
    };

    writeFileSync(receiptPath, JSON.stringify(receipt, null, 2) + '\n', 'utf8');
    console.log(
      `PROBE RESULT [${args.tag}]: passed=[${passedIds.join(', ')}] failed=[${failedIds.join(', ')}] (0 arbitrary sleeps, Edge ${browserVersion}).`,
    );

    if (args.mode === 'enforce-ownership' && !allOwnershipPassed) {
      console.error(
        `OWNERSHIP ENFORCEMENT FAILED as expected on unpatched source: failed scenarios = [${failedIds.join(', ')}].`,
      );
      process.exitCode = 1;
    }
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
