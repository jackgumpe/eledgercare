/**
 * Independent Microsoft Edge (`msedge` channel) end-to-end workflow driver for WP-0012 (`eld-f4-reviewer`).
 *
 * Modes:
 *   1. `cpu-preflight` (CPU-only, `LocalOcr:Enabled=false`, zero model/GPU calls, zero SQL-seeded results):
 *      - `--target scratch-guard`: submits `SYN-WO-01-v1-raster300.pdf` via real browser IntakePage,
 *        verifies DocumentPage `extraction-unavailable` disabled guard + HTTP `503 extraction_disabled`,
 *        and verifies `/archive` shows `Awaiting extraction` in `all` browse (`0` in `machine`/`reviewed`).
 *      - `--target scratch-post-restart`: reopens the scratch document and `/archive` after PG+API restart
 *        with `LocalOcr:Enabled=false`, confirming `0` extraction attempts and `workerEnabled === false`.
 *      - `--target empty-ready-db`: read-only GET check on the fresh retained `eledgercare_demo_wp0012_reviewer`
 *        database (`/` + `/archive` across `all`/`machine`/`reviewed`), confirming `0` rows, `0` non-GET API
 *        calls, and `0` browser storage keys.
 *   2. `live-phase1-leased` (HELD for `/004` sole GPU lease):
 *      - Hard-caps extraction requests at `MAX_EXTRACTION_REQUESTS = 2` (`0` warmups, `0` retries).
 *      - Uploads `SYN-WO-01-v1-raster300.pdf` (1p) + `SYN-MP-01-v0-clean.pdf` (3p), runs real local OCR
 *        once per document (stopping immediately on any failure), saves source-grounded `Reviewed #1` +
 *        newer `Draft #2` on `SYN-WO-01` and `Reviewed #1` (`2 edited` + `3 unknown`) on `SYN-MP-01`,
 *        and exercises `/archive` retrieval (`machine`, `reviewed`, `all`), `#page=2` PDF preview reopen,
 *        and pinned `/review/revisions/1` reopen without overwriting `Draft #2`.
 *   3. `live-phase2-post-restart` (HELD for `/004` post-restart with `LocalOcr:Enabled=false`):
 *      - Reopens `/archive`, `/documents/:id`, and `/documents/:id/review` after PG+API restart with
 *        `LocalOcr:Enabled=false`, verifying preserved search, `#page=2` preview, pinned history, and
 *        unchanged attempt count (`2` total attempts, `0` new worker runs).
 */

import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..', '..', '..', '..', '..', '..');
const requireFromWeb = createRequire(path.join(repoRoot, 'web', 'package.json'));
const { chromium } = requireFromWeb('@playwright/test');

const SYN_WO_REL = 'tests/fixtures/SYN-WO-01-v1-raster300.pdf';
const SYN_WO_BYTES = 372258;
const SYN_WO_SHA256 = '47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd';

const SYN_MP_REL = 'tests/fixtures/SYN-MP-01-v0-clean.pdf';
const SYN_MP_BYTES = 8422;
const SYN_MP_SHA256 = '15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3';

const MAX_EXTRACTION_REQUESTS = 2;

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
    throw new Error(`Edge workflow assertion failed [${name}]: ${JSON.stringify(detail)}`);
  }
}

function sha256Hex(buf) {
  return createHash('sha256').update(buf).digest('hex');
}

async function runArchiveSearch(page, query, source) {
  await page.getByTestId('archive-query-input').fill(query);
  await page.getByTestId('archive-source-select').selectOption(source);
  await page.getByTestId('archive-submit-btn').click();
  await page.getByTestId('archive-results-section').waitFor({ state: 'visible', timeout: 15_000 });
  await page.waitForFunction(
    () => document.querySelector('[data-testid="archive-loading"]') === null,
    null,
    { timeout: 15_000 },
  );
  const cards = page.locator('article[data-testid^="archive-card-"]');
  const count = await cards.count();
  const ids = [];
  for (let i = 0; i < count; i++) {
    const attr = await cards.nth(i).getAttribute('data-testid');
    if (attr && attr.startsWith('archive-card-')) {
      ids.push(attr.slice('archive-card-'.length));
    }
  }
  return { count, documentIds: ids };
}

async function uploadPdfInEdge(page, baseUrl, fixturePath, expectedBytes, expectedSha) {
  await page.goto(`${baseUrl}/`, { waitUntil: 'networkidle' });
  await page.getByTestId('file-input').setInputFiles(fixturePath);
  await page.getByTestId('submit').click();
  await page.getByTestId('receipt').waitFor({ state: 'visible', timeout: 30_000 });

  const docId = (await page.getByTestId('receipt-document-id').innerText()).trim();
  const statusText = (await page.getByTestId('receipt-status').innerText()).trim();
  const bytesText = (await page.getByTestId('receipt-byte-length').innerText()).trim();
  const shaText = (await page.getByTestId('receipt-sha256').innerText()).trim();

  assertCond('upload_receipt_integrity', statusText === 'Awaiting extraction' && bytesText === `${expectedBytes} bytes` && shaText === expectedSha, {
    docId,
    statusText,
    bytesText,
    shaText,
  });

  await page.getByTestId('receipt-open').click();
  await page.getByTestId('document').waitFor({ state: 'visible', timeout: 15_000 });
  return { documentId: docId, statusText, bytesText, shaText };
}

async function verifyReadableOriginalRange(page, baseUrl, docId, expectedBytes) {
  const probe = await page.evaluate(async ({ url, docIdVal }) => {
    const prevResp = await fetch(`${url}/api/documents/${docIdVal}/preview`, {
      headers: { Range: 'bytes=0-7' },
    });
    const prevBytes = new Uint8Array(await prevResp.arrayBuffer());
    const magic = Array.from(prevBytes)
      .map((b) => String.fromCharCode(b))
      .join('');
    const origResp = await fetch(`${url}/api/documents/${docIdVal}/original`);
    const origBuf = await origResp.arrayBuffer();
    return {
      previewStatus: prevResp.status,
      contentRange: prevResp.headers.get('content-range'),
      magic,
      originalStatus: origResp.status,
      originalByteLength: origBuf.byteLength,
    };
  }, { url: baseUrl, docIdVal: docId });

  assertCond(
    'pdf_range_206_readable',
    probe.previewStatus === 206 &&
      probe.magic.startsWith('%PDF-1.') &&
      probe.contentRange === `bytes 0-7/${expectedBytes}` &&
      probe.originalStatus === 200 &&
      probe.originalByteLength === expectedBytes,
    probe,
  );
  return probe;
}

async function main() {
  const args = parseArgs(process.argv);
  const mode = args['mode'];
  const uiPort = Number(args['ui-port'] ?? '4710');
  const apiPort = Number(args['api-port'] ?? '5690');
  const outputPath = path.resolve(repoRoot, args['output']);
  const screenshotDir = path.resolve(repoRoot, args['screenshot-dir']);
  mkdirSync(path.dirname(outputPath), { recursive: true });
  mkdirSync(screenshotDir, { recursive: true });

  const baseUrl = `http://127.0.0.1:${uiPort}`;
  const synWoPath = path.resolve(repoRoot, SYN_WO_REL);
  const synMpPath = path.resolve(repoRoot, SYN_MP_REL);
  assertCond('syn_wo_fixture_digest', sha256Hex(readFileSync(synWoPath)) === SYN_WO_SHA256, { synWoPath });
  assertCond('syn_mp_fixture_digest', sha256Hex(readFileSync(synMpPath)) === SYN_MP_SHA256, { synMpPath });

  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const browserVersion = browser.version();
  const context = await browser.newContext({ viewport: { width: 1440, height: 920 } });
  const page = await context.newPage();

  const apiRequests = [];
  let extractionPostCount = 0;
  page.on('request', (req) => {
    const u = req.url();
    if (u.includes('/api/')) {
      const m = req.method();
      const p = new URL(u).pathname;
      apiRequests.push({ method: m, pathname: p });
      if (m === 'POST' && p.endsWith('/extraction')) {
        extractionPostCount += 1;
      }
    }
  });

  try {
    if (mode === 'cpu-preflight') {
      const target = args['target'];
      if (target === 'scratch-guard') {
        const uploaded = await uploadPdfInEdge(page, baseUrl, synWoPath, SYN_WO_BYTES, SYN_WO_SHA256);
        const docId = uploaded.documentId;

        await page.getByTestId('extraction-unavailable').waitFor({ state: 'visible', timeout: 10_000 });
        const unavailText = (await page.getByTestId('extraction-unavailable').innerText()).trim();
        const btnDisabled = await page.getByTestId('request-extraction').isDisabled();
        const frameSrc = await page.getByTestId('document-pdf-preview-frame').getAttribute('src');
        const rangeProbe = await verifyReadableOriginalRange(page, baseUrl, docId, SYN_WO_BYTES);

        const directPost = await page.evaluate(async ({ url, id }) => {
          const resp = await fetch(`${url}/api/documents/${id}/extraction`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: '{}',
          });
          const body = await resp.json().catch(() => null);
          return { status: resp.status, body };
        }, { url: baseUrl, id: docId });

        assertCond(
          'ocr_disabled_guard_enforced',
          btnDisabled === true &&
            unavailText.length > 0 &&
            frameSrc === `/api/documents/${docId}/preview` &&
            directPost.status === 503 &&
            directPost.body?.code === 'extraction_disabled',
          { btnDisabled, unavailText, frameSrc, directPost },
        );

        const shotPath = path.join(screenshotDir, 'cpu-preflight-ocr-disabled-doc.png');
        await page.waitForTimeout(800);
        await page.screenshot({ path: shotPath, fullPage: true });

        await page.getByTestId('document-open-archive').click();
        await page.getByTestId('archive-search-panel').waitFor({ state: 'visible', timeout: 15_000 });
        const allBrowse = await runArchiveSearch(page, '', 'all');
        const machineBrowse = await runArchiveSearch(page, '', 'machine');
        const reviewedBrowse = await runArchiveSearch(page, '', 'reviewed');
        assertCond(
          'scratch_archive_unprocessed_visibility',
          allBrowse.count === 1 && allBrowse.documentIds[0] === docId && machineBrowse.count === 0 && reviewedBrowse.count === 0,
          { allBrowse, machineBrowse, reviewedBrowse },
        );

        writeFileSync(
          outputPath,
          JSON.stringify(
            {
              schema: 'eledgercare.wp-0012.edge-cpu-preflight-scratch/1',
              verifiedUtc: new Date().toISOString(),
              browserChannel: 'msedge',
              browserVersion,
              uiPort,
              apiPort,
              documentId: docId,
              unavailableBannerText: unavailText,
              requestButtonDisabled: btnDisabled,
              directExtractionPost503: directPost,
              rangeProbe,
              archiveBrowse: { allBrowse, machineBrowse, reviewedBrowse },
              screenshot: path.relative(repoRoot, shotPath).replace(/\\/g, '/'),
            },
            null,
            2,
          ) + '\n',
          'utf-8',
        );
      } else if (target === 'scratch-post-restart') {
        const docId = args['document-id'];
        assertCond('scratch_doc_id_supplied', Boolean(docId), { docId });

        await page.goto(`${baseUrl}/documents/${docId}`, { waitUntil: 'networkidle' });
        await page.getByTestId('document').waitFor({ state: 'visible', timeout: 15_000 });
        await page.getByTestId('extraction-unavailable').waitFor({ state: 'visible', timeout: 10_000 });
        const btnDisabled = await page.getByTestId('request-extraction').isDisabled();
        const extJson = await page.evaluate(async ({ url, id }) => {
          const r = await fetch(`${url}/api/documents/${id}/extraction`);
          return await r.json();
        }, { url: baseUrl, id: docId });

        assertCond(
          'post_restart_ocr_still_disabled_zero_attempts',
          btnDisabled === true && extJson.workerEnabled === false && Array.isArray(extJson.attempts) && extJson.attempts.length === 0,
          { btnDisabled, workerEnabled: extJson.workerEnabled, attemptsCount: extJson.attempts?.length },
        );

        await page.getByTestId('document-open-archive').click();
        const allBrowse = await runArchiveSearch(page, '', 'all');
        assertCond('post_restart_archive_retains_doc', allBrowse.documentIds.includes(docId), allBrowse);

        writeFileSync(
          outputPath,
          JSON.stringify(
            {
              schema: 'eledgercare.wp-0012.edge-cpu-preflight-scratch-restart/1',
              verifiedUtc: new Date().toISOString(),
              browserVersion,
              documentId: docId,
              workerEnabled: extJson.workerEnabled,
              attemptCountAfterRestart: extJson.attempts.length,
              archiveCountAfterRestart: allBrowse.count,
            },
            null,
            2,
          ) + '\n',
          'utf-8',
        );
      } else if (target === 'empty-ready-db') {
        await page.goto(`${baseUrl}/`, { waitUntil: 'networkidle' });
        await page.getByTestId('file-input').waitFor({ state: 'visible', timeout: 15_000 });
        await page.getByTestId('intake-open-archive').click();
        await page.getByTestId('archive-search-panel').waitFor({ state: 'visible', timeout: 15_000 });

        const allEmpty = await runArchiveSearch(page, '', 'all');
        const machineEmpty = await runArchiveSearch(page, '', 'machine');
        const reviewedEmpty = await runArchiveSearch(page, '', 'reviewed');
        await page.getByTestId('archive-empty').waitFor({ state: 'visible', timeout: 10_000 });

        const storageCounts = await page.evaluate(() => ({
          localKeys: Object.keys(window.localStorage),
          sessionKeys: Object.keys(window.sessionStorage),
        }));
        const nonGetApiCalls = apiRequests.filter((r) => r.method !== 'GET');

        assertCond(
          'empty_ready_db_zero_rows_and_zero_mutations',
          allEmpty.count === 0 &&
            machineEmpty.count === 0 &&
            reviewedEmpty.count === 0 &&
            nonGetApiCalls.length === 0 &&
            storageCounts.localKeys.length === 0 &&
            storageCounts.sessionKeys.length === 0,
          { allEmpty, machineEmpty, reviewedEmpty, nonGetApiCalls, storageCounts },
        );

        const shotPath = path.join(screenshotDir, 'cpu-preflight-empty-archive.png');
        await page.screenshot({ path: shotPath, fullPage: true });

        writeFileSync(
          outputPath,
          JSON.stringify(
            {
              schema: 'eledgercare.wp-0012.edge-cpu-preflight-empty-ready/1',
              verifiedUtc: new Date().toISOString(),
              browserChannel: 'msedge',
              browserVersion,
              uiPort,
              apiPort,
              allEmptyCount: allEmpty.count,
              machineEmptyCount: machineEmpty.count,
              reviewedEmptyCount: reviewedEmpty.count,
              nonGetApiCallCount: nonGetApiCalls.length,
              storageCounts,
              screenshot: path.relative(repoRoot, shotPath).replace(/\\/g, '/'),
            },
            null,
            2,
          ) + '\n',
          'utf-8',
        );
      } else {
        throw new Error(`Unsupported cpu-preflight target: ${target}`);
      }
    } else if (mode === 'live-phase1-leased') {
      // Strict 2-attempt ceiling (0 warmups, 0 retries, immediate stop on any failure).
      let issuedClicks = 0;
      const requestExtractionOnce = async (docId, label) => {
        if (issuedClicks >= MAX_EXTRACTION_REQUESTS) {
          throw new Error(`Hard 2-attempt cap reached before ${label}; refusing additional extraction request.`);
        }
        issuedClicks += 1;
        const startedPerf = Date.now();
        const phasesObserved = [];
        await page.getByTestId('request-extraction').click();

        const deadline = Date.now() + 540_000;
        while (Date.now() < deadline) {
          if (await page.getByTestId('extraction-failure').isVisible().catch(() => false)) {
            const failMsg = await page.getByTestId('extraction-failure').innerText();
            throw new Error(`Live extraction failed on ${label} (${docId}) — halting with 0 retries: ${failMsg}`);
          }
          if (await page.getByTestId('extraction-result').isVisible().catch(() => false)) {
            break;
          }
          if (await page.getByTestId('active-phase').isVisible().catch(() => false)) {
            const ph = (await page.getByTestId('active-phase').innerText()).trim();
            if (ph && !phasesObserved.includes(ph)) {
              phasesObserved.push(ph);
            }
          }
          await page.waitForTimeout(1000);
        }

        await page.getByTestId('extraction-result').waitFor({ state: 'visible', timeout: 5_000 });
        const uiElapsedMs = Date.now() - startedPerf;
        assertCond('extraction_post_cap_enforced', extractionPostCount <= MAX_EXTRACTION_REQUESTS, {
          extractionPostCount,
          issuedClicks,
        });
        return { uiElapsedMs, phasesObserved };
      };

      // 1. Document 1: SYN-WO-01-v1-raster300.pdf (1 page)
      const woUp = await uploadPdfInEdge(page, baseUrl, synWoPath, SYN_WO_BYTES, SYN_WO_SHA256);
      const woExt = await requestExtractionOnce(woUp.documentId, 'SYN-WO-01-v1-raster300');
      await verifyReadableOriginalRange(page, baseUrl, woUp.documentId, SYN_WO_BYTES);
      await page.screenshot({ path: path.join(screenshotDir, 'live-01-wo01-extracted.png'), fullPage: true });

      await page.getByTestId('open-work-order-review').click();
      await page.getByTestId('review-workspace').waitFor({ state: 'visible', timeout: 15_000 });

      const woFallbackValues = {
        work_order_id: 'WO-004192',
        property_name: 'Cedar Hollow Apartments',
        building_unit: 'Bldg B - Unit 204',
        requested_date: '2026-10-16',
      };
      for (const [fk, fallbackVal] of Object.entries(woFallbackValues)) {
        const acceptBtn = page.getByTestId(`btn-accept-${fk}`);
        if (!(await acceptBtn.isDisabled())) {
          await acceptBtn.click();
        } else {
          await page.getByTestId(`btn-edit-${fk}`).click();
          await page.getByTestId(`input-value-${fk}`).fill(fallbackVal);
        }
      }

      const woRev1Summary =
        'Air handler fan running continuously with warm supply air at 79 F setpoint. ' +
        'Inspected condensing unit CHP-B204: dual run capacitor measured 18.2 uF on 45 uF herm leg and contactor points pitted. ' +
        'Replaced capacitor (SKU CAP-45-5MFD-440V) and 2-pole contactor from van stock; verified 19.4 F delta-T across evaporator coil.';
      await page.getByTestId('btn-edit-issue_and_resolution').click();
      await page.getByTestId('input-value-issue_and_resolution').fill(woRev1Summary);
      await page.getByTestId('input-operator-label').fill('Reviewer operator');
      await page.getByTestId('confirm-reviewed-checkbox').check();
      await page.getByTestId('save-reviewed').click();
      await page.getByTestId('review-save-receipt').waitFor({ state: 'visible', timeout: 15_000 });

      // Newer unapproved Draft #2 on SYN-WO-01 incorporating grounded Page 1 completion sign-off
      const woDraft2Summary = `${woRev1Summary} Completed 2026-10-16 10:45; supervisor review: D. Callahan.`;
      await page.getByTestId('input-value-issue_and_resolution').fill(woDraft2Summary);
      await page.getByTestId('save-draft').click();
      await page.getByTestId('prior-reviewed-historical-warning').waitFor({ state: 'visible', timeout: 15_000 });
      await page.screenshot({ path: path.join(screenshotDir, 'live-02-wo01-rev1-and-draft2.png'), fullPage: true });

      // 2. Document 2: SYN-MP-01-v0-clean.pdf (3 pages)
      const mpUp = await uploadPdfInEdge(page, baseUrl, synMpPath, SYN_MP_BYTES, SYN_MP_SHA256);
      const mpExt = await requestExtractionOnce(mpUp.documentId, 'SYN-MP-01-v0-clean');
      await verifyReadableOriginalRange(page, baseUrl, mpUp.documentId, SYN_MP_BYTES);
      await page.screenshot({ path: path.join(screenshotDir, 'live-03-mp01-extracted-3p.png'), fullPage: true });

      await page.getByTestId('open-work-order-review').click();
      await page.getByTestId('review-workspace').waitFor({ state: 'visible', timeout: 15_000 });
      await page.getByTestId('pdf-page-btn-2').click();
      await page.getByTestId('pdf-page-btn-3').click();

      await page.getByTestId('btn-unknown-work_order_id').click();
      await page
        .getByTestId('input-unknown-reason-work_order_id')
        .fill('Consolidated monthly statement INV-008810 lists multiple work orders across Pages 1-3 (WO-004701 through WO-004759); no single Work Order ID applies.');

      await page.getByTestId('btn-edit-property_name').click();
      await page.getByTestId('input-value-property_name').fill('Maple Ridge Commons Asset Operations');

      await page.getByTestId('btn-unknown-building_unit').click();
      await page
        .getByTestId('input-unknown-reason-building_unit')
        .fill('Statement covers Buildings A, B, C & Clubhouse across multiple units; no single Building / Unit applies.');

      await page.getByTestId('btn-unknown-requested_date').click();
      await page
        .getByTestId('input-unknown-reason-requested_date')
        .fill('Shows Billing Period 2026-10-01 through 2026-10-31 and Statement Date 2026-10-31 rather than a single work-order Requested Date.');

      await page.getByTestId('btn-edit-issue_and_resolution').click();
      await page
        .getByTestId('input-value-issue_and_resolution')
        .fill(
          'Consolidated monthly maintenance statement INV-008810 under Master Service Agreement CTR-008840 ' +
            'for Billing Period 2026-10-01 through 2026-10-31; Total Amount Due $1,535.35 across Pages 1-3.',
        );
      await page.getByTestId('input-operator-label').fill('Reviewer operator');
      await page.getByTestId('confirm-reviewed-checkbox').check();
      await page.getByTestId('save-reviewed').click();
      await page.getByTestId('review-save-receipt').waitFor({ state: 'visible', timeout: 15_000 });
      await page.screenshot({ path: path.join(screenshotDir, 'live-04-mp01-reviewed-unknowns.png'), fullPage: true });

      // 3. Archive search, #page=2 PDF reopen, and pinned historical Revision #1 reopen
      await page.getByTestId('review-open-archive').click();
      await page.getByTestId('archive-search-panel').waitFor({ state: 'visible', timeout: 15_000 });

      const qMachineMp = await runArchiveSearch(page, 'WO-004724', 'machine');
      const qReviewedMpUnknownAbsent = await runArchiveSearch(page, 'WO-004724', 'reviewed');
      assertCond(
        'machine_page2_vs_unknown_absent_in_reviewed',
        qMachineMp.documentIds.includes(mpUp.documentId) && qReviewedMpUnknownAbsent.count === 0,
        { qMachineMp, qReviewedMpUnknownAbsent },
      );

      await runArchiveSearch(page, 'WO-004724', 'machine');
      await page.getByTestId(`witness-open-machine-${mpUp.documentId}-0`).click();
      await page.getByTestId('document-pdf-preview-frame').waitFor({ state: 'visible', timeout: 15_000 });
      const mpPage2Src = await page.getByTestId('document-pdf-preview-frame').getAttribute('src');
      assertCond('mp01_reopened_at_page_2', mpPage2Src?.endsWith(`/api/documents/${mpUp.documentId}/preview#page=2`), { mpPage2Src });
      await page.screenshot({ path: path.join(screenshotDir, 'live-05-mp01-archive-reopen-page2.png'), fullPage: true });
      await page.getByTestId('back-to-archive').click();
      await page.getByTestId('archive-search-panel').waitFor({ state: 'visible', timeout: 15_000 });

      const qDraftNonLeak = await runArchiveSearch(page, 'Callahan', 'reviewed');
      const qCallahanMachine = await runArchiveSearch(page, 'Callahan', 'machine');
      assertCond(
        'draft_never_leaks_into_reviewed_search',
        qDraftNonLeak.count === 0 && qCallahanMachine.documentIds.includes(woUp.documentId),
        { qDraftNonLeak, qCallahanMachine },
      );

      const qReviewedSku = await runArchiveSearch(page, 'CAP-45-5MFD-440V', 'reviewed');
      assertCond('reviewed_grounded_sku_found', qReviewedSku.documentIds.includes(woUp.documentId), qReviewedSku);
      await page.getByTestId(`archive-newer-draft-${woUp.documentId}`).waitFor({ state: 'visible', timeout: 10_000 });
      await page.screenshot({ path: path.join(screenshotDir, 'live-06-archive-reviewed-newer-draft.png'), fullPage: true });

      await page.getByTestId(`witness-open-reviewed-${woUp.documentId}-0`).click();
      await page.getByTestId('historical-revision-banner').waitFor({ state: 'visible', timeout: 15_000 });
      const histBanner = (await page.getByTestId('historical-revision-banner').innerText()).trim();
      assertCond(
        'pinned_rev1_preserves_draft2_head',
        histBanner.includes('Revision #1') && histBanner.includes('current head is Revision #2: draft'),
        { histBanner },
      );
      await page.screenshot({ path: path.join(screenshotDir, 'live-07-wo01-pinned-rev1-preserves-draft2.png'), fullPage: true });
      await page.getByTestId('review-back-to-archive').click();
      await page.getByTestId('archive-search-panel').waitFor({ state: 'visible', timeout: 15_000 });

      const qReviewedMpDate = await runArchiveSearch(page, '2026-10-01', 'reviewed');
      assertCond('mp01_reviewed_billing_start_found', qReviewedMpDate.documentIds.includes(mpUp.documentId), qReviewedMpDate);

      writeFileSync(
        outputPath,
        JSON.stringify(
          {
            schema: 'eledgercare.wp-0012.edge-live-phase1/1',
            verifiedUtc: new Date().toISOString(),
            browserChannel: 'msedge',
            browserVersion,
            extractionRequestsIssued: issuedClicks,
            extractionPostCountObserved: extractionPostCount,
            woDocument: { ...woUp, ...woExt },
            mpDocument: { ...mpUp, ...mpExt },
            archiveChecks: {
              qMachineMp,
              qReviewedMpUnknownAbsent,
              qDraftNonLeak,
              qCallahanMachine,
              qReviewedSku,
              qReviewedMpDate,
            },
          },
          null,
          2,
        ) + '\n',
        'utf-8',
      );
    } else if (mode === 'live-phase2-post-restart') {
      const woDocId = args['wo-document-id'];
      const mpDocId = args['mp-document-id'];
      assertCond('phase2_doc_ids_supplied', Boolean(woDocId) && Boolean(mpDocId), { woDocId, mpDocId });

      await page.goto(`${baseUrl}/archive`, { waitUntil: 'networkidle' });
      await page.getByTestId('archive-search-panel').waitFor({ state: 'visible', timeout: 15_000 });

      const browseAll = await runArchiveSearch(page, '', 'all');
      const qMachineMp = await runArchiveSearch(page, 'WO-004724', 'machine');
      assertCond(
        'post_restart_archive_persisted',
        browseAll.count === 2 && qMachineMp.documentIds.includes(mpDocId),
        { browseAll, qMachineMp },
      );

      await page.getByTestId(`witness-open-machine-${mpDocId}-0`).click();
      await page.getByTestId('document-pdf-preview-frame').waitFor({ state: 'visible', timeout: 15_000 });
      const mpFrameSrc = await page.getByTestId('document-pdf-preview-frame').getAttribute('src');
      await verifyReadableOriginalRange(page, baseUrl, mpDocId, SYN_MP_BYTES);
      assertCond('post_restart_mp01_page2', mpFrameSrc?.endsWith(`/api/documents/${mpDocId}/preview#page=2`), { mpFrameSrc });
      await page.screenshot({ path: path.join(screenshotDir, 'live-08-post-restart-mp01-page2.png'), fullPage: true });

      await page.getByTestId('back-to-archive').click();
      const qDraftNonLeak = await runArchiveSearch(page, 'Callahan', 'reviewed');
      const qReviewedSku = await runArchiveSearch(page, 'CAP-45-5MFD-440V', 'reviewed');
      assertCond(
        'post_restart_reviewed_and_draft_separation',
        qDraftNonLeak.count === 0 && qReviewedSku.documentIds.includes(woDocId),
        { qDraftNonLeak, qReviewedSku },
      );

      await page.getByTestId(`witness-open-reviewed-${woDocId}-0`).click();
      await page.getByTestId('historical-revision-banner').waitFor({ state: 'visible', timeout: 15_000 });
      const histBanner = (await page.getByTestId('historical-revision-banner').innerText()).trim();
      assertCond(
        'post_restart_pinned_rev1_and_draft2_head',
        histBanner.includes('Revision #1') && histBanner.includes('current head is Revision #2: draft'),
        { histBanner },
      );
      await page.screenshot({ path: path.join(screenshotDir, 'live-09-post-restart-wo01-pinned-rev1.png'), fullPage: true });

      const extChecks = await page.evaluate(async ({ url, woId, mpId }) => {
        const rWo = await (await fetch(`${url}/api/documents/${woId}/extraction`)).json();
        const rMp = await (await fetch(`${url}/api/documents/${mpId}/extraction`)).json();
        return {
          woWorkerEnabled: rWo.workerEnabled,
          woAttempts: rWo.attempts?.length ?? -1,
          mpWorkerEnabled: rMp.workerEnabled,
          mpAttempts: rMp.attempts?.length ?? -1,
        };
      }, { url: baseUrl, woId: woDocId, mpId: mpDocId });

      const storageCounts = await page.evaluate(() => ({
        localKeys: Object.keys(window.localStorage),
        sessionKeys: Object.keys(window.sessionStorage),
      }));

      assertCond(
        'post_restart_ocr_disabled_attempt_count_unchanged',
        extChecks.woWorkerEnabled === false &&
          extChecks.mpWorkerEnabled === false &&
          extChecks.woAttempts === 1 &&
          extChecks.mpAttempts === 1 &&
          extractionPostCount === 0 &&
          storageCounts.localKeys.length === 0 &&
          storageCounts.sessionKeys.length === 0,
        { extChecks, extractionPostCount, storageCounts },
      );

      writeFileSync(
        outputPath,
        JSON.stringify(
          {
            schema: 'eledgercare.wp-0012.edge-live-phase2-post-restart/1',
            verifiedUtc: new Date().toISOString(),
            browserChannel: 'msedge',
            browserVersion,
            woDocumentId: woDocId,
            mpDocumentId: mpDocId,
            extChecks,
            extractionPostCountDuringPhase2: extractionPostCount,
            storageCounts,
          },
          null,
          2,
        ) + '\n',
        'utf-8',
      );
    } else {
      throw new Error(`Unsupported mode: ${mode}`);
    }
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err?.stack ?? String(err));
  process.exit(1);
});
