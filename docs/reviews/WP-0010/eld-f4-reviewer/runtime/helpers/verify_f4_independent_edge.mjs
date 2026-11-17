/**
 * Frozen independent Microsoft Edge (`msedge` channel) F4 runtime verifier (`eld-f4-reviewer`).
 *
 * Executes strictly read-only HTTP GET / UI interactions against the reviewer-owned Angular server
 * (`127.0.0.1:4710`) proxying to the reviewer-owned `ELedgerCare.Api` (`127.0.0.1:5690`,
 * `LocalOcr:Enabled=false`) backed by `eledgercare_f4_reviewer_migrated` (forward-migrated clone of
 * independently prepared 9-document `eledgercare_f4_reviewer_seed_f3`).
 *
 * Phases: `before-restart` and `after-restart`.
 * Verifies:
 *   1. `/archive` browse of all 9 reviewer seeds in exact `(submitted_at DESC, document_id DESC)` order,
 *      including `awaiting_extraction` (`SEED-R09`), `failed` (`SEED-R08`), microsecond tie-breaker
 *      (`SEED-R07` `...0007` before `SEED-R06` `...0006`), draft-only fallback title (`SEED-R05`),
 *      clean reviewed head (`SEED-R03`), and `Reviewed (Revision #2)` + `Newer draft exists (head Revision #3)`
 *      on `SEED-R01`, with secondary `<details>` provenance closed by default.
 *   2. Machine search on 3-page `colspan` `SEED-R02` (`q=Refrigerator L09`, `source=machine`) ->
 *      inline readable native PDF `#page=2` & `#page=3` on `DocumentPage`, byte-exact PDF download,
 *      and query-preserving `Back to archive search`.
 *   3. Reviewed search with Page-2 table provenance (`SEED-R04` `WO-004724-MP-LINKED` -> `#page=2` +
 *      pinned immutable Revision #1) AND reviewed search without provenance (`SEED-R01` literal
 *      `7.50% Cap_Rate \` -> pinned historical Revision #2 with `0` fabricated page coordinates,
 *      preserving Draft #3 head untouched) + inert `<script>`/emoji rendering + query-preserving return.
 *   4. Obsolete slow-response suppression, unsaved in-memory review edit preservation across `?page=`/`?field=`
 *      query focus updates, `window.confirm` guard on route exit (dismiss retains edit; accept navigates
 *      without saving), `0` mutating API calls, and `0` `localStorage`/`sessionStorage` keys.
 */

import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..', '..', '..', '..', '..', '..');
const requireFromWeb = createRequire(path.join(repoRoot, 'web', 'package.json'));
const { chromium, expect } = requireFromWeb('@playwright/test');

const EXPECTED_MP_PDF_SHA256 = '15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3';

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
  const out = {};
  for (let i = 2; i < argv.length; i += 2) {
    const k = argv[i];
    const v = argv[i + 1];
    if (!k?.startsWith('--') || v === undefined) {
      throw new Error(`Invalid CLI argument at index ${i}: ${k}`);
    }
    out[k.slice(2)] = v;
  }
  return out;
}

function assertCond(name, cond, detail) {
  if (!cond) {
    throw new Error(`Independent Edge F4 assertion failed [${name}]: ${JSON.stringify(detail)}`);
  }
}

async function main() {
  const args = parseArgs(process.argv);
  const phase = args['phase'] ?? 'before-restart';
  const uiPort = Number(args['ui-port'] ?? '4710');
  const apiPort = Number(args['api-port'] ?? '5690');
  const receiptPath = path.resolve(repoRoot, args['output']);
  const screenshotDir = path.resolve(repoRoot, args['screenshot-dir']);

  mkdirSync(path.dirname(receiptPath), { recursive: true });
  mkdirSync(screenshotDir, { recursive: true });

  const mpPdfBytes = readFileSync(path.join(repoRoot, 'tests', 'fixtures', 'SYN-MP-01-v0-clean.pdf'));
  const mpPdfSha = createHash('sha256').update(mpPdfBytes).digest('hex');
  assertCond('mp_fixture_sha256', mpPdfSha === EXPECTED_MP_PDF_SHA256, { mpPdfSha });

  const baseUrl = `http://127.0.0.1:${uiPort}`;
  const browser = await chromium.launch({
    channel: 'msedge',
    headless: true,
  });

  try {
    const browserVersion = browser.version();
    const context = await browser.newContext({
      viewport: { width: 1680, height: 980 },
      acceptDownloads: true,
    });
    const page = await context.newPage();

    const observedApiRequests = [];
    page.on('request', (req) => {
      if (req.url().includes('/api/')) {
        observedApiRequests.push({ method: req.method(), url: req.url() });
      }
    });

    // -------------------------------------------------------------------------
    // E1. Intake -> Archive browse of all 9 reviewer seeds & badge/order checks
    // -------------------------------------------------------------------------
    await page.goto(`${baseUrl}/`, { waitUntil: 'networkidle' });
    await expect(page.getByTestId('intake-open-archive')).toBeVisible({ timeout: 15000 });
    await page.getByTestId('nav-archive').click();
    await expect(page).toHaveURL(/\/archive$/);
    await expect(page.getByTestId('archive-card-list')).toBeVisible({ timeout: 15000 });

    const renderedCards = page.locator('[data-testid^="archive-card-01a"]');
    await expect(renderedCards).toHaveCount(9, { timeout: 15000 });

    const actualOrder = [];
    for (let i = 0; i < 9; i++) {
      const tid = await renderedCards.nth(i).getAttribute('data-testid');
      actualOrder.push(tid.replace('archive-card-', ''));
    }
    assertCond(
      'browse_9_seed_exact_order_and_microsecond_tiebreak',
      JSON.stringify(actualOrder) === JSON.stringify(EXPECTED_BROWSE_ORDER),
      { actualOrder, expected: EXPECTED_BROWSE_ORDER },
    );

    await expect(page.getByTestId(`archive-doc-status-${SEED_R09}`)).toHaveText('Awaiting extraction');
    await expect(page.getByTestId(`archive-doc-status-${SEED_R08}`)).toHaveText('Failed');
    await expect(page.getByTestId(`archive-review-badge-${SEED_R05}`)).toContainText(
      'Draft (Revision #2 — unreviewed)',
    );
    const r05Title = (await page.getByTestId(`archive-card-title-${SEED_R05}`).innerText()).trim();
    assertCond(
      'draft_only_seed_r05_never_uses_draft_title',
      r05Title.startsWith('Document 01a20400') && !r05Title.includes('Draft Only'),
      { r05Title },
    );

    await expect(page.getByTestId(`archive-card-title-${SEED_R01}`)).toHaveText(
      'WO-004192 — Cedar Hollow Apartments — Verified North Wing (7.50% Cap_Rate \\ Literal)',
    );
    await expect(page.getByTestId(`archive-doc-status-${SEED_R01}`)).toHaveText('Completed (unreviewed)');
    await expect(page.getByTestId(`archive-review-badge-${SEED_R01}`)).toHaveText('Reviewed (Revision #2)');
    await expect(page.getByTestId(`archive-newer-draft-${SEED_R01}`)).toHaveText(
      'Newer draft exists (head Revision #3)',
    );
    await expect(page.getByTestId(`archive-newer-draft-${SEED_R03}`)).toHaveCount(0);
    await expect(page.getByTestId(`archive-provenance-${SEED_R01}`)).not.toHaveAttribute('open', '');
    await expect(page.getByTestId(`archive-full-doc-id-${SEED_R01}`)).toBeHidden();

    const shotBrowse = path.join(screenshotDir, `${phase}-01-archive-browse-9-seeds.png`);
    await page.screenshot({ path: shotBrowse, fullPage: false });

    // -------------------------------------------------------------------------
    // E2. Machine search on 3-page colspan SEED-R02 -> readable PDF #page=2 & #page=3 -> return
    // -------------------------------------------------------------------------
    await page.getByTestId('archive-source-select').selectOption('machine');
    await page.getByTestId('archive-query-input').fill('Refrigerator L09');
    await page.getByTestId('archive-submit-btn').click();

    await expect(page).toHaveURL(/\/archive\?q=Refrigerator%20L09&source=machine$/);
    await expect(page.getByTestId(`archive-card-${SEED_R02}`)).toBeVisible();
    await expect(page.getByTestId(`archive-card-${SEED_R04}`)).toBeVisible();
    await expect(page.getByTestId(`witness-source-label-${SEED_R02}-0`)).toHaveText(
      'Machine extraction — unreviewed',
    );
    const markTexts = await page
      .getByTestId(`archive-snippet-${SEED_R02}-0`)
      .locator('mark.archive-hit')
      .allInnerTexts();
    assertCond(
      'seed_r02_snippet_highlights_both_terms',
      markTexts.includes('L09') && markTexts.includes('Refrigerator'),
      { markTexts },
    );

    await page.getByTestId(`witness-open-machine-${SEED_R02}-0`).click();
    await expect(page).toHaveURL(new RegExp(`/documents/${SEED_R02}\\?.*page=2`));
    await expect(page.getByTestId('document-pdf-current-page')).toContainText('Page 2 of 3', { timeout: 10000 });
    await expect(page.getByTestId('document-pdf-preview-frame')).toHaveAttribute(
      'src',
      `/api/documents/${SEED_R02}/preview#page=2`,
      { timeout: 10000 },
    );
    await expect(page.getByTestId('result-page-2')).toHaveClass(/highlighted-target/);

    // Allow Edge native PDFium iframe to finish painting Page 2 and capture screenshot
    await page.waitForTimeout(2200);
    const shotMpPage2 = path.join(screenshotDir, `${phase}-02-seed-r02-mp01-page2-pdf.png`);
    await page.screenshot({ path: shotMpPage2 });

    // Navigate inline preview to Page 3 and verify byte-exact original PDF download
    await page.getByTestId('document-pdf-page-btn-3').click();
    await expect(page.getByTestId('document-pdf-current-page')).toContainText('Page 3 of 3', { timeout: 10000 });
    await expect(page.getByTestId('document-pdf-preview-frame')).toHaveAttribute(
      'src',
      `/api/documents/${SEED_R02}/preview#page=3`,
      { timeout: 10000 },
    );

    const dlPromise = page.waitForEvent('download');
    await page.getByTestId('document-pdf-download-fallback').click();
    const dl = await dlPromise;
    const dlBytes = readFileSync(await dl.path());
    assertCond('mp_download_byte_exact', Buffer.compare(dlBytes, mpPdfBytes) === 0, {
      downloadedLength: dlBytes.length,
    });

    // Also verify out-of-range ?page=99 on DocumentPage falls back without #page claim
    await page.goto(
      `${baseUrl}/documents/${SEED_R02}?returnSource=machine&returnQ=Refrigerator%20L09&page=99`,
      { waitUntil: 'networkidle' },
    );
    await expect(page.getByTestId('document-invalid-page-warning')).toContainText("outside this document's 1..3");
    await expect(page.getByTestId('document-pdf-preview-frame')).toHaveAttribute(
      'src',
      `/api/documents/${SEED_R02}/preview`,
    );

    await page.getByTestId('back-to-archive').click();
    await expect(page).toHaveURL(/\/archive\?q=Refrigerator%20L09&source=machine$/);
    await expect(page.getByTestId('archive-query-input')).toHaveValue('Refrigerator L09');
    await expect(page.getByTestId('archive-source-select')).toHaveValue('machine');

    // -------------------------------------------------------------------------
    // E3A. Reviewed hit WITH Page-2 table provenance (SEED-R04) -> pinned Rev #1 + PDF #page=2
    // -------------------------------------------------------------------------
    await page.getByTestId('archive-source-select').selectOption('reviewed');
    await page.getByTestId('archive-query-input').fill('WO-004724-MP-LINKED');
    await page.getByTestId('archive-submit-btn').click();

    await expect(page.getByTestId(`archive-card-${SEED_R04}`)).toBeVisible();
    await expect(page.getByTestId(`witness-consulted-page-${SEED_R04}-0`)).toContainText(
      'Recorded source Page 2',
    );
    await page.getByTestId(`witness-open-reviewed-${SEED_R04}-0`).click();

    await expect(page).toHaveURL(new RegExp(`/documents/${SEED_R04}/review/revisions/1\\?.*page=2`));
    await expect(page.getByTestId('historical-revision-banner')).toContainText(
      'Viewing pinned immutable Revision #1 (reviewed)',
      { timeout: 15000 },
    );
    await expect(page.getByTestId('pdf-current-page')).toContainText('Page 2 of 3', { timeout: 10000 });
    await expect(page.getByTestId('pdf-preview-frame')).toHaveAttribute(
      'src',
      `/api/documents/${SEED_R04}/preview#page=2`,
      { timeout: 10000 },
    );
    await expect(page.getByTestId('historical-field-work_order_id')).toHaveAttribute('data-focused', 'true');
    await expect(page.getByTestId('historical-consulted-page-work_order_id')).toHaveCount(1);
    // ZeroCoords field on the very same revision has NO fabricated page button!
    await expect(page.getByTestId('historical-no-provenance-property_name')).toContainText('None recorded');
    await expect(page.getByTestId('historical-consulted-page-property_name')).toHaveCount(0);

    await page.waitForTimeout(2000);
    const shotR04PinnedP2 = path.join(screenshotDir, `${phase}-03-seed-r04-pinned-rev1-page2.png`);
    await page.screenshot({ path: shotR04PinnedP2 });

    await page.getByTestId('review-back-to-archive').click();
    await expect(page).toHaveURL(/\/archive\?q=WO-004724-MP-LINKED&source=reviewed$/);

    // -------------------------------------------------------------------------
    // E3B. Reviewed hit WITHOUT provenance on SEED-R01 (literal %, _, \) + newer Draft #3
    // -------------------------------------------------------------------------
    await page.getByTestId('archive-query-input').fill('7.50% Cap_Rate \\');
    await page.getByTestId('archive-submit-btn').click();

    await expect(page.getByTestId(`archive-card-${SEED_R01}`)).toBeVisible();
    await expect(page.getByTestId(`archive-newer-draft-${SEED_R01}`)).toContainText(
      'Newer draft exists (head Revision #3)',
    );
    await expect(page.getByTestId(`witness-source-label-${SEED_R01}-0`)).toHaveText(
      'Property Name · Reviewed Revision #2',
    );
    await expect(page.getByTestId(`witness-consulted-page-${SEED_R01}-0`)).toHaveCount(0);

    const shotR01ArchiveCard = path.join(screenshotDir, `${phase}-04-seed-r01-metachar-newer-draft.png`);
    await page.screenshot({ path: shotR01ArchiveCard });

    await page.getByTestId(`witness-open-reviewed-${SEED_R01}-0`).click();
    await expect(page).toHaveURL(new RegExp(`/documents/${SEED_R01}/review/revisions/2\\?`));
    assertCond('r01_null_prov_url_has_no_page_param', !page.url().includes('page='), { url: page.url() });

    await expect(page.getByTestId('historical-revision-banner')).toContainText(
      'Viewing immutable historical Revision #2 (reviewed)',
      { timeout: 15000 },
    );
    await expect(page.getByTestId('historical-revision-banner')).toContainText(
      'current head is Revision #3: draft',
    );
    await expect(page.getByTestId('historical-field-property_name')).toHaveAttribute('data-focused', 'true');
    await expect(page.getByTestId('historical-no-provenance-property_name')).toContainText('None recorded');
    await expect(page.getByTestId('historical-consulted-page-property_name')).toHaveCount(0);

    await page.waitForTimeout(1800);
    const shotR01PinnedRev2 = path.join(screenshotDir, `${phase}-05-seed-r01-pinned-rev2-noprov.png`);
    await page.screenshot({ path: shotR01PinnedRev2 });

    // Switch to editable current head (#3) and confirm opening historical Rev #2 did NOT overwrite Draft #3!
    await page.getByTestId('return-to-current-head').click();
    await expect(page.getByTestId('review-status-badge')).toHaveText('Saved draft (Revision #3)', {
      timeout: 10000,
    });
    await expect(page.getByTestId('input-value-property_name')).toHaveValue(
      'UNAPPROVED-DRAFT-R3-DO-NOT-INDEX',
    );

    await page.getByTestId('review-back-to-archive').click();
    await expect(page).toHaveURL(/\/archive\?q=7.50%25%20Cap_Rate%20%5C&source=reviewed$/);

    // -------------------------------------------------------------------------
    // E4. Obsolete response suppression + unsaved review guard across query & route transitions
    // -------------------------------------------------------------------------
    let slowStaleFulfilled = false;
    await page.route('**/api/archive?*', async (route) => {
      const reqUrl = new URL(route.request().url());
      if (reqUrl.searchParams.get('q') === 'SLOW-REVIEWER-STALE-1') {
        await new Promise((r) => setTimeout(r, 650));
        slowStaleFulfilled = true;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            query: 'SLOW-REVIEWER-STALE-1',
            terms: ['SLOW-REVIEWER-STALE-1'],
            source: 'reviewed',
            limit: 20,
            hasMore: false,
            nextCursor: null,
            projectionVersion: 'archive-machine-projection/1',
            items: [],
          }),
        });
        return;
      }
      await route.fallback();
    });

    await page.getByTestId('archive-query-input').fill('SLOW-REVIEWER-STALE-1');
    await page.getByTestId('archive-submit-btn').click();
    await page.getByTestId('archive-query-input').fill('WO-009901-CLEAN-HEAD');
    await page.getByTestId('archive-submit-btn').click();

    await expect(page.getByTestId(`archive-card-${SEED_R03}`)).toBeVisible({ timeout: 15000 });
    await page.waitForTimeout(850);
    await expect(page.getByTestId(`archive-card-${SEED_R03}`)).toBeVisible();
    await expect(page.getByTestId('archive-empty')).toHaveCount(0);
    await page.unroute('**/api/archive?*');

    // Dismissing confirm on historical snapshot button ('View') also preserves unsaved edit
    await page.goto(`${baseUrl}/documents/${SEED_R01}/review`, { waitUntil: 'networkidle' });
    await expect(page.getByTestId('review-status-badge')).toHaveText('Saved draft (Revision #3)', {
      timeout: 15000,
    });
    await page.getByTestId('btn-edit-property_name').click();
    await page.getByTestId('input-value-property_name').fill('Unsaved Reviewer Memory Guard Probe');
    await expect(page.getByTestId('unsaved-edits-warning')).toBeVisible();

    page.once('dialog', async (dlg) => {
      await dlg.dismiss();
    });
    await page.getByTestId('view-revision-2').click();
    await expect(page.getByTestId('input-value-property_name')).toHaveValue(
      'Unsaved Reviewer Memory Guard Probe',
    );

    // Dismissing confirm on route exit keeps unsaved edit intact on WorkOrderReviewPage
    page.once('dialog', async (dlg) => {
      await dlg.dismiss();
    });
    await page.getByTestId('review-open-archive').click();
    await expect(page).toHaveURL(new RegExp(`/documents/${SEED_R01}/review$`));
    await expect(page.getByTestId('input-value-property_name')).toHaveValue(
      'Unsaved Reviewer Memory Guard Probe',
    );

    // Accepting confirm navigates cleanly to /archive without saving any revision
    page.once('dialog', async (dlg) => {
      await dlg.accept();
    });
    await page.getByTestId('review-open-archive').click();
    await expect(page).toHaveURL(/\/archive$/);

    const nonGetCalls = observedApiRequests.filter((r) => r.method !== 'GET' && r.method !== 'HEAD');
    assertCond('zero_mutating_api_calls_during_edge_verification', nonGetCalls.length === 0, { nonGetCalls });

    const storageState = await page.evaluate(() => ({
      local: Object.keys(window.localStorage).length,
      session: Object.keys(window.sessionStorage).length,
    }));
    assertCond(
      'zero_browser_storage_keys',
      storageState.local === 0 && storageState.session === 0,
      storageState,
    );

    const screenshots = [shotBrowse, shotMpPage2, shotR04PinnedP2, shotR01ArchiveCard, shotR01PinnedRev2].map(
      (p) => ({
        path: path.relative(repoRoot, p).replace(/\\/g, '/'),
        bytes: statSync(p).size,
        sha256: createHash('sha256').update(readFileSync(p)).digest('hex'),
      }),
    );

    const receipt = {
      schema: 'eledgercare.wp-0010.reviewer-f4-edge-runtime-receipt/1',
      phase,
      verified_at_utc: new Date().toISOString(),
      reviewer: 'eld-f4-reviewer',
      browser_channel: 'msedge',
      browser_version: browserVersion,
      ui_port: uiPort,
      api_port: apiPort,
      browse_order_verified: actualOrder,
      mp_download_sha256: mpPdfSha,
      slow_stale_fulfilled_without_overwriting: slowStaleFulfilled,
      observed_api_get_count: observedApiRequests.length,
      observed_non_get_api_count: nonGetCalls.length,
      local_storage_keys: storageState.local,
      session_storage_keys: storageState.session,
      screenshots,
      all_passed: true,
    };

    writeFileSync(receiptPath, JSON.stringify(receipt, null, 2) + '\n', 'utf8');
    console.log(
      `PASS [${phase}]: Edge ${browserVersion} verified 9-seed browse, #page=2/#page=3 PDF, pinned Rev #1/#2, stale suppression, & unsaved guard.`,
    );
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
