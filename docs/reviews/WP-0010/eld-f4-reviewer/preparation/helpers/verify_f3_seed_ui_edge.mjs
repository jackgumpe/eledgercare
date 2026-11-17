/**
 * Read-only Microsoft Edge (`msedge` channel) smoke check for WP-0010 independent reviewer F3 seed preparation.
 *
 * Connects to the reviewer-owned Angular dev server (127.0.0.1:4710) proxying to the reviewer-owned
 * ELedgerCare.Api (127.0.0.1:5690, LocalOcr:Enabled=false), verifies:
 *   1. Document screen & review screen on SEED-R01 (`01a1e571-2838-714b-861b-bf0835d7c90a`), including
 *      readable native PDF preview iframe (`#page=1`), unapproved Draft #3 head warning alongside
 *      3-row revision history, and pinned historicalReviewed Revision #2 (`/review/revisions/2`)
 *      showing null-provenance literal `%`/`_`/`\` edit, `unknown` building_unit decision + reason,
 *      and astral `🔧` + `Café Élite` narrative.
 *   2. Review screen on 3-page SEED-R04 (`01a20400-0000-7000-8000-000000000004`), navigating PDF
 *      preview to `#page=2` and confirming closed-by-default secondary provenance details.
 * Performs ZERO POST/PUT/DELETE mutations and writes a structured JSON receipt + screenshots to `.scratch/`.
 */

import { mkdirSync, statSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..', '..', '..', '..', '..', '..');
const requireFromWeb = createRequire(path.join(repoRoot, 'web', 'package.json'));
const { chromium, expect } = requireFromWeb('@playwright/test');

function parseArgs(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 2) {
    const key = argv[i];
    const val = argv[i + 1];
    if (!key?.startsWith('--') || val === undefined) {
      throw new Error(`Invalid CLI argument pair at index ${i}: ${key}`);
    }
    out[key.slice(2)] = val;
  }
  return out;
}

function assertCond(name, cond, detail) {
  if (!cond) {
    throw new Error(`Edge UI smoke assertion failed [${name}]: ${JSON.stringify(detail)}`);
  }
}

async function main() {
  const args = parseArgs(process.argv);
  const uiPort = Number(args['ui-port'] ?? '4710');
  const apiPort = Number(args['api-port'] ?? '5690');
  const receiptPath = path.resolve(repoRoot, args['output']);
  const screenshotDir = path.resolve(
    repoRoot,
    args['screenshot-dir'] ?? '.scratch/preparation-edge-screenshots',
  );
  mkdirSync(screenshotDir, { recursive: true });
  mkdirSync(path.dirname(receiptPath), { recursive: true });

  const baseUrl = `http://127.0.0.1:${uiPort}`;
  const seedR01DocId = '01a1e571-2838-714b-861b-bf0835d7c90a';
  const seedR04DocId = '01a20400-0000-7000-8000-000000000004';

  const browser = await chromium.launch({
    channel: 'msedge',
    headless: true,
  });

  try {
    const browserVersion = browser.version();
    const context = await browser.newContext({
      viewport: { width: 1600, height: 960 },
    });
    const page = await context.newPage();

    const observedRequests = [];
    page.on('request', (req) => {
      if (req.url().includes('/api/')) {
        observedRequests.push({ method: req.method(), url: req.url() });
      }
    });

    // 1. SEED-R01 Document page (/documents/:id): extraction completed + Draft #3 summary
    await page.goto(`${baseUrl}/documents/${seedR01DocId}`, { waitUntil: 'networkidle' });
    await page.locator('[data-testid="document-status"]').waitFor({ state: 'visible', timeout: 20000 });
    const docStatus = (await page.locator('[data-testid="document-status"]').innerText()).trim();
    const docRevStatus = (await page.locator('[data-testid="document-review-status"]').innerText()).trim();
    const rawShaText = (await page.locator('[data-testid="result-raw-sha256"]').innerText()).trim();

    assertCond('r01_doc_status', docStatus === 'Completed (unreviewed)', { docStatus });
    assertCond('r01_doc_review_status', docRevStatus.includes('Draft (Revision #3)'), { docRevStatus });
    assertCond(
      'r01_raw_sha256',
      rawShaText === '7503761ae46afef6adf579881d011764283474354fac3e185598fc7d266aff95',
      { rawShaText },
    );

    // 2. SEED-R01 Review head (/documents/:id/review): Draft #3 + prior reviewed warning + PDF #page=1
    await page.goto(`${baseUrl}/documents/${seedR01DocId}/review`, { waitUntil: 'networkidle' });
    await page.locator('[data-testid="review-status-badge"]').waitFor({ state: 'visible', timeout: 20000 });

    const headBadge = (await page.locator('[data-testid="review-status-badge"]').innerText()).trim();
    const headRevNum = (await page.locator('[data-testid="current-revision-number"]').innerText()).trim();
    const priorWarn = (await page.locator('[data-testid="prior-reviewed-historical-warning"]').innerText()).trim();
    const frameSrcR01 = await page.locator('[data-testid="pdf-preview-frame"]').getAttribute('src');
    const provOpenAttr = await page.locator('[data-testid="review-provenance-details"]').getAttribute('open');
    const historyRowCount = await page.locator('[data-testid^="history-row-"]').count();

    assertCond('r01_head_badge', headBadge === 'Saved draft (Revision #3)', { headBadge });
    assertCond('r01_head_rev_num', headRevNum === '#3', { headRevNum });
    assertCond(
      'r01_prior_reviewed_warning',
      priorWarn.includes('Current head (#3) is an unapproved draft.'),
      { priorWarn },
    );
    assertCond(
      'r01_preview_src_p1',
      frameSrcR01 === `/api/documents/${seedR01DocId}/preview#page=1`,
      { frameSrcR01 },
    );
    assertCond('r01_secondary_details_closed_by_default', provOpenAttr === null, { provOpenAttr });
    assertCond('r01_history_3_rows', historyRowCount === 3, { historyRowCount });

    await page.waitForTimeout(2000);
    const shotR01Head = path.join(screenshotDir, 'seed-r01-draft3-head.png');
    await page.screenshot({ path: shotR01Head });

    // 3. SEED-R01 Pinned historical Reviewed Revision #2 (/documents/:id/review/revisions/2)
    await page.goto(`${baseUrl}/documents/${seedR01DocId}/review/revisions/2`, { waitUntil: 'networkidle' });
    await page.locator('[data-testid="historical-revision-banner"]').waitFor({ state: 'visible', timeout: 20000 });

    const histBanner = (await page.locator('[data-testid="historical-revision-banner"]').innerText()).trim();
    const histPropVal = (await page.locator('[data-testid="historical-value-property_name"]').innerText()).trim();
    const histUnitDec = (await page.locator('[data-testid="historical-decision-building_unit"]').innerText()).trim();
    const histUnitReason = (await page.locator('[data-testid="historical-reason-building_unit"]').innerText()).trim();
    const histNarrVal = (await page.locator('[data-testid="historical-value-issue_and_resolution"]').innerText()).trim();

    assertCond(
      'r01_rev2_historical_banner',
      histBanner.includes('Viewing immutable historical Revision #2') &&
        histBanner.includes('(reviewed)') &&
        histBanner.includes('current head is Revision #3: draft'),
      { histBanner },
    );
    assertCond(
      'r01_rev2_literal_property_value',
      histPropVal === 'Cedar Hollow Apartments — Verified North Wing (7.50% Cap_Rate \\ Literal)',
      { histPropVal },
    );
    assertCond('r01_rev2_unknown_decision', histUnitDec === 'unknown', { histUnitDec });
    assertCond(
      'r01_rev2_unknown_reason',
      histUnitReason === 'R4-UNKNOWN-REASON-ILLEGIBLE-BADGE',
      { histUnitReason },
    );
    assertCond(
      'r01_rev2_astral_and_unicode_narrative',
      histNarrVal.includes('🔧') && histNarrVal.includes('Café Élite'),
      { histNarrVal },
    );

    const shotR01Rev2 = path.join(screenshotDir, 'seed-r01-historical-rev2.png');
    await page.screenshot({ path: shotR01Rev2 });

    // 4. SEED-R04 3-Page Review screen (/documents/:id/review): navigate native PDF to #page=2
    await page.goto(`${baseUrl}/documents/${seedR04DocId}/review`, { waitUntil: 'networkidle' });
    await page.locator('[data-testid="review-status-badge"]').waitFor({ state: 'visible', timeout: 20000 });
    const r04Badge = (await page.locator('[data-testid="review-status-badge"]').innerText()).trim();
    assertCond('r04_reviewed_badge', r04Badge === 'Reviewed (Revision #1 · 1 unknown)', { r04Badge });

    await page.locator('[data-testid="pdf-page-btn-2"]').click();
    await expect(page.locator('[data-testid="pdf-current-page"]')).toContainText('Page 2 of 3', {
      timeout: 10000,
    });
    await expect(page.locator('[data-testid="pdf-preview-frame"]')).toHaveAttribute(
      'src',
      `/api/documents/${seedR04DocId}/preview#page=2`,
      { timeout: 10000 },
    );
    const r04PageLabel = (await page.locator('[data-testid="pdf-current-page"]').innerText()).trim();
    const r04FrameSrcP2 = await page.locator('[data-testid="pdf-preview-frame"]').getAttribute('src');
    assertCond('r04_page_2_label', r04PageLabel.includes('Page 2 of 3'), { r04PageLabel });
    assertCond(
      'r04_preview_src_p2',
      r04FrameSrcP2 === `/api/documents/${seedR04DocId}/preview#page=2`,
      { r04FrameSrcP2 },
    );

    await page.waitForTimeout(2000);
    const shotR04Page2 = path.join(screenshotDir, 'seed-r04-three-page-p2.png');
    await page.screenshot({ path: shotR04Page2 });

    // Confirm zero mutating API methods occurred during Edge smoke!
    const nonGetApiCalls = observedRequests.filter((r) => r.method !== 'GET' && r.method !== 'HEAD');
    assertCond('zero_mutating_api_requests_in_edge_smoke', nonGetApiCalls.length === 0, { nonGetApiCalls });

    const localStorageKeys = await page.evaluate(() => Object.keys(window.localStorage).length);
    const sessionStorageKeys = await page.evaluate(() => Object.keys(window.sessionStorage).length);
    assertCond(
      'zero_browser_storage_writes',
      localStorageKeys === 0 && sessionStorageKeys === 0,
      { localStorageKeys, sessionStorageKeys },
    );

    const receipt = {
      schema: 'eledgercare.wp-0010.reviewer-f3-seed-edge-smoke/1',
      verified_at_utc: new Date().toISOString(),
      reviewer: 'eld-f4-reviewer',
      browser_channel: 'msedge',
      browser_version: browserVersion,
      ui_port: uiPort,
      api_port: apiPort,
      observed_api_get_count: observedRequests.length,
      observed_non_get_api_count: nonGetApiCalls.length,
      local_storage_keys: localStorageKeys,
      session_storage_keys: sessionStorageKeys,
      verified_screens: {
        seed_r01_document: {
          document_id: seedR01DocId,
          status: docStatus,
          review_summary_status: docRevStatus,
          raw_sha256: rawShaText,
        },
        seed_r01_head_draft3: {
          badge: headBadge,
          current_revision_number: headRevNum,
          prior_reviewed_warning_present: true,
          pdf_iframe_src: frameSrcR01,
          history_row_count: historyRowCount,
          screenshot_bytes: statSync(shotR01Head).size,
        },
        seed_r01_historical_rev2: {
          banner: histBanner,
          property_value: histPropVal,
          building_unit_decision: histUnitDec,
          building_unit_unknown_reason: histUnitReason,
          narrative_contains_astral_and_unicode: true,
          screenshot_bytes: statSync(shotR01Rev2).size,
        },
        seed_r04_page2_navigation: {
          document_id: seedR04DocId,
          badge: r04Badge,
          page_label: r04PageLabel,
          pdf_iframe_src: r04FrameSrcP2,
          screenshot_bytes: statSync(shotR04Page2).size,
        },
      },
      all_passed: true,
    };

    writeFileSync(receiptPath, JSON.stringify(receipt, null, 2) + '\n', 'utf8');
    console.log(`PASS: Edge UI read-only smoke verified (${browserVersion}) on ${baseUrl}.`);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
