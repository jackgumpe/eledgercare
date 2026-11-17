import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';

/**
 * Test-only real Microsoft Edge browser rehearsal driver for WP-0012 (eld-f4-implementer).
 *
 * Modes:
 *   1. --mode cpu-preflight
 *      Verifies Intake (/) and Archive (/archive, 0 cards) in headless Microsoft Edge with
 *      LocalOcr:Enabled=false against the empty eledgercare_demo_wp0012_author database.
 *      Performs zero mutations, zero uploads, and zero OCR requests.
 *   2. --mode live-phase-a
 *      Drives the complete customer workflow in real Microsoft Edge under an active coordinator
 *      sole-GPU lease:
 *        - Fresh browser upload of SYN-WO-01-v1-raster300.pdf (1p) -> real local OCR (Attempt 1/2)
 *          -> original PDF comparison -> grounded correction of CAP-45-5MFD-440V from printed Parts
 *          table -> Save Reviewed Revision #1 -> distinct newer Draft Revision #2 (printed sign-off
 *          "D. Callahan") without contaminating reviewed search.
 *        - Fresh browser upload of SYN-MP-01-v0-clean.pdf (3p) -> real local OCR (Attempt 2/2)
 *          -> 3-page original PDF comparison -> grounded review with 2 explicit unknown fields
 *          (work_order_id, requested_date) and 3 grounded printed edits -> Save Reviewed Revision #1.
 *        - Archive browse, machine search ("Refrigerator Evaporator" -> #page=2 PDF preview -> back),
 *          reviewed searches ("CAP-45-5MFD-440V" -> pinned Rev #1 + newer draft notice; "Maple Ridge
 *          Commons" -> pinned Rev #1 without fabricated page coords), newer-draft isolation ("Callahan"
 *          in reviewed == 0), and unknown-reason exclusion ("spans multiple work orders" == 0).
 *      First failed/interrupted extraction stops immediately without retry or extra model calls.
 *   3. --mode live-phase-b-reopen
 *      Re-verifies saved archive queries, readable source PDF #page=2 preview, pinned historical
 *      revisions, newer-draft badge, original PDF SHA-256s, and raw extraction SHA-256s after
 *      owned API + PostgreSQL fast restart with LocalOcr:Enabled=false (0 new attempts).
 */

const repoRoot = path.resolve(import.meta.dirname, '..', '..', '..', '..', '..');
const requireFromWeb = createRequire(path.join(repoRoot, 'web', 'package.json'));
const { chromium } = requireFromWeb('@playwright/test');

const WO_FIXTURE_PATH = path.join(repoRoot, 'tests', 'fixtures', 'SYN-WO-01-v1-raster300.pdf');
const MP_FIXTURE_PATH = path.join(repoRoot, 'tests', 'fixtures', 'SYN-MP-01-v0-clean.pdf');
const EXPECTED_WO_SHA256 = '47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd';
const EXPECTED_WO_BYTES = 372258;
const EXPECTED_MP_SHA256 = '15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3';
const EXPECTED_MP_BYTES = 8422;

const WO_PRINTED_FIELDS = {
  work_order_id: 'WO-004192',
  property_name: 'Cedar Hollow Apartments',
  building_unit: 'Bldg B - Unit 204',
  requested_date: '2026-10-16',
};

const WO_GROUNDED_ISSUE_REV1 =
  'Air handler fan running continuously with warm supply air at 79 F setpoint. Inspected condensing unit CHP-B204: ' +
  'dual run capacitor measured 18.2 uF on 45 uF herm leg and contactor points pitted. Replaced capacitor and 2-pole ' +
  'contactor from van stock; verified 19.4 F delta-T across evaporator coil. Verified stock parts on form: ' +
  'CAP-45-5MFD-440V (Oval Dual Run Capacitor 45/5 uF 440VAC), CONT-24V-2P30A, 0018-TERM-QC.';

const WO_GROUNDED_DRAFT_REV2 =
  WO_GROUNDED_ISSUE_REV1 + ' Supervisor Review: D. Callahan (Completed 2026-10-16 10:45).';

const MP_GROUNDED_REVIEW = {
  work_order_id_unknown_reason:
    'Consolidated monthly statement INV-008810 spans multiple work orders across Pages 1-3; no single Work Order ID applies.',
  property_name: 'Maple Ridge Commons Asset Operations',
  building_unit: 'Buildings A, B, C & Clubhouse',
  requested_date_unknown_reason:
    'Statement records Statement Date 2026-10-31 and Due Date 2026-11-30 only; no Requested Date is printed.',
  issue_and_resolution:
    'Consolidated Monthly Maintenance Statement INV-008810 (Contract CTR-008840, Billing Period 2026-10-01 through 2026-10-31); Current Invoice Total $1,535.35.',
};

function parseArgs(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 2) {
    out[argv[i].replace(/^--/, '')] = argv[i + 1];
  }
  return out;
}

function sha256Buffer(buf) {
  return createHash('sha256').update(buf).digest('hex');
}

async function fetchJson(url) {
  const res = await fetch(url);
  const text = await res.text();
  return { status: res.status, body: text ? JSON.parse(text) : null };
}

async function fetchBinarySha256(url) {
  const res = await fetch(url);
  if (res.status !== 200) {
    throw new Error(`Expected HTTP 200 from ${url}, got ${res.status}`);
  }
  const buf = Buffer.from(await res.arrayBuffer());
  return { byteLength: buf.length, sha256: sha256Buffer(buf) };
}

async function waitForCondition(fn, description, timeoutMs = 25000, pollMs = 150) {
  const deadline = Date.now() + timeoutMs;
  let lastErr = null;
  while (Date.now() < deadline) {
    try {
      if (await fn()) {
        return;
      }
    } catch (err) {
      lastErr = err;
    }
    await new Promise((r) => setTimeout(r, pollMs));
  }
  throw new Error(`Timed out waiting for ${description}${lastErr ? ` (${lastErr})` : ''}`);
}

async function waitForRealExtractionCompletion(page, apiBase, documentId, maxWaitSeconds, shotDir, tag) {
  const startedMs = Date.now();
  const deadline = startedMs + maxWaitSeconds * 1000;
  const observedPhases = [];
  let lastPhaseKey = '';

  while (Date.now() < deadline) {
    const extRes = await fetchJson(`${apiBase}/api/documents/${documentId}/extraction`);
    if (extRes.status !== 200 || !extRes.body) {
      throw new Error(`Read-only extraction status poll failed (${extRes.status}) for ${documentId}`);
    }
    const ext = extRes.body;
    const phase = ext.currentAttempt?.phase ?? ext.status;
    const phaseKey = `${ext.status}:${phase}`;
    if (phaseKey !== lastPhaseKey) {
      lastPhaseKey = phaseKey;
      observedPhases.push({
        observedUtc: new Date().toISOString(),
        elapsedMs: Date.now() - startedMs,
        status: ext.status,
        attemptId: ext.currentAttempt?.attemptId ?? null,
        attemptNumber: ext.currentAttempt?.attemptNumber ?? null,
        phase,
        lastHeartbeatAtUtc: ext.currentAttempt?.lastHeartbeatAtUtc ?? null,
      });
    }

    if (ext.status === 'failed' || ext.status === 'interrupted') {
      if (shotDir) {
        await page.screenshot({ path: path.join(shotDir, `${tag}-FAILURE-stop.png`) });
      }
      throw new Error(
        `STOP-ON-FAILURE: Extraction for ${documentId} ended with status='${ext.status}', ` +
          `code='${ext.currentAttempt?.failureCode ?? 'none'}', detail='${ext.currentAttempt?.failureMessage ?? ''}'. ` +
          `Halting immediately with zero retries.`,
      );
    }

    if (ext.status === 'completed' && ext.result) {
      await page.getByTestId('extraction-result').waitFor({ state: 'visible', timeout: 30000 });
      return {
        wallElapsedMs: Date.now() - startedMs,
        observedPhases,
        extractionView: ext,
      };
    }

    await new Promise((r) => setTimeout(r, 2000));
  }

  throw new Error(`Extraction for ${documentId} did not complete within ${maxWaitSeconds}s.`);
}

async function verifyArchiveAndReopenWorkflow(page, apiBase, uiBase, stateIn, phaseLabel, shotDir) {
  const { woDocId, woRawSha256, mpDocId, mpRawSha256 } = stateIn;
  const screenshots = [];

  // 1. Read-only HTTP saved-query canonical digest + excluded-sentinel verification
  const browseAll = await fetchJson(`${apiBase}/api/archive?limit=20`);
  const browseMachine = await fetchJson(`${apiBase}/api/archive?source=machine&limit=20`);
  const browseReviewed = await fetchJson(`${apiBase}/api/archive?source=reviewed&limit=20`);
  const qMachineMp = await fetchJson(
    `${apiBase}/api/archive?q=${encodeURIComponent('Refrigerator Evaporator')}&source=machine`,
  );
  const qReviewedWo = await fetchJson(
    `${apiBase}/api/archive?q=${encodeURIComponent('CAP-45-5MFD-440V')}&source=reviewed`,
  );
  const qReviewedMp = await fetchJson(
    `${apiBase}/api/archive?q=${encodeURIComponent('Maple Ridge Commons')}&source=reviewed`,
  );
  const qDraftExcluded = await fetchJson(
    `${apiBase}/api/archive?q=${encodeURIComponent('Callahan')}&source=reviewed`,
  );
  const qUnknownReasonExcluded = await fetchJson(
    `${apiBase}/api/archive?q=${encodeURIComponent('spans multiple work orders')}&source=reviewed`,
  );

  if (browseAll.status !== 200 || browseAll.body.items.length !== 2) {
    throw new Error(`Expected 2 documents in browse=all, got ${browseAll.body?.items?.length}`);
  }
  if (browseMachine.status !== 200 || browseMachine.body.items.length !== 2) {
    throw new Error(`Expected 2 documents in browse=machine, got ${browseMachine.body?.items?.length}`);
  }
  if (browseReviewed.status !== 200 || browseReviewed.body.items.length !== 2) {
    throw new Error(`Expected 2 documents in browse=reviewed, got ${browseReviewed.body?.items?.length}`);
  }
  if (qDraftExcluded.body.items.length !== 0) {
    throw new Error('Newer draft text "Callahan" leaked into source=reviewed search!');
  }
  if (qUnknownReasonExcluded.body.items.length !== 0) {
    throw new Error('Unknown-reason text leaked into source=reviewed search!');
  }

  const origWo = await fetchBinarySha256(`${apiBase}/api/documents/${woDocId}/original`);
  const origMp = await fetchBinarySha256(`${apiBase}/api/documents/${mpDocId}/original`);
  if (origWo.sha256 !== EXPECTED_WO_SHA256 || origMp.sha256 !== EXPECTED_MP_SHA256) {
    throw new Error('Original PDF SHA-256 mismatch on persisted documents.');
  }

  const extWo = await fetchJson(`${apiBase}/api/documents/${woDocId}/extraction`);
  const extMp = await fetchJson(`${apiBase}/api/documents/${mpDocId}/extraction`);
  if (
    extWo.body?.result?.rawSha256 !== woRawSha256 ||
    extMp.body?.result?.rawSha256 !== mpRawSha256 ||
    extWo.body?.attempts?.length !== 1 ||
    extMp.body?.attempts?.length !== 1
  ) {
    throw new Error('Extraction rawSha256 or attempt count drifted!');
  }

  // 2. Real Microsoft Edge UI navigation: /archive browse -> machine #page=2 -> reviewed pinned history -> draft exclusion
  await page.goto(`${uiBase}/archive`, { waitUntil: 'networkidle' });
  await page.getByTestId(`archive-card-${woDocId}`).waitFor({ state: 'visible', timeout: 25000 });
  await page.getByTestId(`archive-card-${mpDocId}`).waitFor({ state: 'visible', timeout: 25000 });

  const newerDraftBadge = (await page.getByTestId(`archive-newer-draft-${woDocId}`).textContent()) ?? '';
  if (!newerDraftBadge.includes('Newer draft exists (head Revision #2)')) {
    throw new Error(`Expected newer draft badge on WO card, got: ${newerDraftBadge}`);
  }

  if (shotDir) {
    const s1 = path.join(shotDir, `${phaseLabel}-01-archive-browse-2-docs.png`);
    await page.screenshot({ path: s1 });
    screenshots.push(path.relative(repoRoot, s1).replace(/\\/g, '/'));
  }

  // Machine search -> open SYN-MP-01 Page 2 readable PDF preview -> return to query
  await page.getByTestId('archive-query-input').fill('Refrigerator Evaporator');
  await page.getByTestId('archive-source-select').selectOption('machine');
  await waitForCondition(
    async () =>
      page.url().endsWith('/archive?q=Refrigerator%20Evaporator&source=machine') &&
      (await page.getByTestId(`witness-open-machine-${mpDocId}-0`).isVisible()),
    'machine search hit on SYN-MP-01 Page 2',
  );
  await page.getByTestId(`witness-open-machine-${mpDocId}-0`).click();
  await waitForCondition(
    async () => page.url().includes(`/documents/${mpDocId}`) && page.url().includes('page=2'),
    'DocumentPage opened at page=2',
  );
  await page.getByTestId('document-pdf-preview-frame').waitFor({ state: 'visible', timeout: 20000 });
  const previewSrc = await page.getByTestId('document-pdf-preview-frame').getAttribute('src');
  if (previewSrc !== `/api/documents/${mpDocId}/preview#page=2`) {
    throw new Error(`Expected preview iframe #page=2, got ${previewSrc}`);
  }
  await page.waitForTimeout(2000);
  if (shotDir) {
    const s2 = path.join(shotDir, `${phaseLabel}-02-mp01-source-pdf-page2.png`);
    await page.screenshot({ path: s2 });
    screenshots.push(path.relative(repoRoot, s2).replace(/\\/g, '/'));
  }
  await page.getByTestId('back-to-archive').click();
  await waitForCondition(
    async () => page.url().endsWith('/archive?q=Refrigerator%20Evaporator&source=machine'),
    'returned from DocumentPage to exact machine archive query',
  );

  // Reviewed search #1 -> grounded CAP-45-5MFD-440V correction on SYN-WO-01 -> pinned Historical Rev #1 while Head is Draft #2
  await page.getByTestId('archive-query-input').fill('CAP-45-5MFD-440V');
  await page.getByTestId('archive-source-select').selectOption('reviewed');
  await waitForCondition(
    async () =>
      page.url().endsWith('/archive?q=CAP-45-5MFD-440V&source=reviewed') &&
      (await page.getByTestId(`witness-open-reviewed-${woDocId}-0`).isVisible()),
    'reviewed search hit for grounded CAP-45-5MFD-440V on SYN-WO-01',
  );
  await page.getByTestId(`witness-open-reviewed-${woDocId}-0`).click();
  await waitForCondition(
    async () => page.url().includes(`/documents/${woDocId}/review/revisions/1`),
    'opened pinned historical Revision #1 on SYN-WO-01',
  );
  await page.getByTestId('historical-revision-banner').waitFor({ state: 'visible', timeout: 20000 });
  const woHistBanner = (await page.getByTestId('historical-revision-banner').textContent()) ?? '';
  if (!woHistBanner.includes('Revision #1 (reviewed)') || !woHistBanner.includes('Revision #2: draft')) {
    throw new Error(`Unexpected historical banner on SYN-WO-01: ${woHistBanner}`);
  }
  await page.waitForTimeout(1800);
  if (shotDir) {
    const s3 = path.join(shotDir, `${phaseLabel}-03-wo01-pinned-rev1-with-newer-draft2.png`);
    await page.screenshot({ path: s3 });
    screenshots.push(path.relative(repoRoot, s3).replace(/\\/g, '/'));
  }
  await page.getByTestId('review-back-to-archive').click();
  await waitForCondition(
    async () => page.url().endsWith('/archive?q=CAP-45-5MFD-440V&source=reviewed'),
    'returned to reviewed archive query',
  );

  // Reviewed search #2 -> SYN-MP-01 Maple Ridge Commons -> opens pinned Rev #1 with 2 unknowns & 0 fabricated page coords
  await page.getByTestId('archive-query-input').fill('Maple Ridge Commons');
  await page.getByTestId('archive-submit-btn').click();
  await waitForCondition(
    async () =>
      page.url().endsWith('/archive?q=Maple%20Ridge%20Commons&source=reviewed') &&
      (await page.getByTestId(`witness-open-reviewed-${mpDocId}-0`).isVisible()),
    'reviewed search hit for Maple Ridge Commons on SYN-MP-01',
  );
  if ((await page.getByTestId(`witness-consulted-page-${mpDocId}-0`).count()) !== 0) {
    throw new Error('Unexpected consulted-page label on null-provenance SYN-MP-01 reviewed witness!');
  }
  await page.getByTestId(`witness-open-reviewed-${mpDocId}-0`).click();
  await waitForCondition(
    async () => page.url().includes(`/documents/${mpDocId}/review/revisions/1`),
    'opened pinned Revision #1 on SYN-MP-01',
  );
  if (page.url().includes('page=')) {
    throw new Error(`Fabricated page= param present on null-provenance SYN-MP-01 link: ${page.url()}`);
  }
  await page.getByTestId('historical-no-provenance-property_name').waitFor({ state: 'visible', timeout: 20000 });
  if (
    ((await page.getByTestId('historical-decision-work_order_id').textContent()) ?? '').trim() !== 'unknown' ||
    ((await page.getByTestId('historical-decision-requested_date').textContent()) ?? '').trim() !== 'unknown'
  ) {
    throw new Error('Expected work_order_id and requested_date to remain marked unknown in SYN-MP-01 Revision #1.');
  }
  await page.waitForTimeout(1800);
  if (shotDir) {
    const s4 = path.join(shotDir, `${phaseLabel}-04-mp01-pinned-rev1-two-unknowns.png`);
    await page.screenshot({ path: s4 });
    screenshots.push(path.relative(repoRoot, s4).replace(/\\/g, '/'));
  }
  await page.getByTestId('review-back-to-archive').click();
  await waitForCondition(
    async () => page.url().endsWith('/archive?q=Maple%20Ridge%20Commons&source=reviewed'),
    'returned to Maple Ridge Commons reviewed query',
  );

  // Newer draft ("Callahan") excluded from source=reviewed in UI
  await page.getByTestId('archive-query-input').fill('Callahan');
  await page.getByTestId('archive-submit-btn').click();
  await page.getByTestId('archive-empty').waitFor({ state: 'visible', timeout: 15000 });

  const storageAudit = await page.evaluate(() => ({
    local: Object.keys(localStorage),
    session: Object.keys(sessionStorage),
  }));
  if (storageAudit.local.length !== 0 || storageAudit.session.length !== 0) {
    throw new Error(`Unexpected browser storage keys: ${JSON.stringify(storageAudit)}`);
  }

  const savedQueryCanonicalSha256 = sha256Buffer(
    Buffer.from(
      JSON.stringify({
        browseAll: browseAll.body,
        browseMachine: browseMachine.body,
        browseReviewed: browseReviewed.body,
        qMachineMp: qMachineMp.body,
        qReviewedWo: qReviewedWo.body,
        qReviewedMp: qReviewedMp.body,
        qDraftExcluded: qDraftExcluded.body,
        qUnknownReasonExcluded: qUnknownReasonExcluded.body,
      }),
      'utf8',
    ),
  );

  return {
    phaseLabel,
    savedQueryCanonicalSha256,
    browseCounts: {
      all: browseAll.body.items.length,
      machine: browseMachine.body.items.length,
      reviewed: browseReviewed.body.items.length,
    },
    machineContainsSmfdOcrMisread: (extWo.body?.result?.rawText ?? '').includes('CAP-45-SMFD-440V'),
    mpMachineContains2025BillingYearMisread: (extMp.body?.result?.rawText ?? '').includes('2025-10-01'),
    zeroBrowserStorageWrites: true,
    screenshots,
  };
}

async function main() {
  const args = parseArgs(process.argv);
  const mode = args.mode ?? 'cpu-preflight';
  const apiPort = Number(args.apiPort ?? 5590);
  const uiPort = Number(args.uiPort ?? 4610);
  const outPath = args.output ? path.resolve(args.output) : null;
  const shotDir = args.screenshotDir ? path.resolve(args.screenshotDir) : null;
  const statePath = args.stateFile ? path.resolve(args.stateFile) : null;

  if (!outPath) {
    throw new Error('Required: --output <path>');
  }
  mkdirSync(path.dirname(outPath), { recursive: true });
  if (shotDir) {
    mkdirSync(shotDir, { recursive: true });
  }

  const woBytes = readFileSync(WO_FIXTURE_PATH);
  const mpBytes = readFileSync(MP_FIXTURE_PATH);
  if (woBytes.length !== EXPECTED_WO_BYTES || sha256Buffer(woBytes) !== EXPECTED_WO_SHA256) {
    throw new Error('SYN-WO-01-v1-raster300.pdf byte/SHA-256 mismatch!');
  }
  if (mpBytes.length !== EXPECTED_MP_BYTES || sha256Buffer(mpBytes) !== EXPECTED_MP_SHA256) {
    throw new Error('SYN-MP-01-v0-clean.pdf byte/SHA-256 mismatch!');
  }

  const apiBase = `http://127.0.0.1:${apiPort}`;
  const uiBase = `http://127.0.0.1:${uiPort}`;

  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const browserVersion = browser.version();
  const context = await browser.newContext({ viewport: { width: 1680, height: 980 }, acceptDownloads: true });
  const page = await context.newPage();
  page.setDefaultTimeout(45000);

  try {
    if (mode === 'cpu-preflight') {
      const startedMs = Date.now();
      await page.goto(`${uiBase}/`, { waitUntil: 'networkidle' });
      await page.getByTestId('file-input').waitFor({ state: 'visible', timeout: 20000 });
      await page.getByTestId('submit').waitFor({ state: 'visible', timeout: 20000 });

      await page.getByTestId('nav-archive').click();
      await waitForCondition(async () => page.url().endsWith('/archive'), 'navigated to /archive');
      await page.getByTestId('archive-empty').waitFor({ state: 'visible', timeout: 20000 });

      const apiArchive = await fetchJson(`${apiBase}/api/archive?limit=20`);
      if (apiArchive.status !== 200 || apiArchive.body?.items?.length !== 0) {
        throw new Error(`Expected empty archive in cpu-preflight, got: ${JSON.stringify(apiArchive)}`);
      }

      const storageAudit = await page.evaluate(() => ({
        local: Object.keys(localStorage),
        session: Object.keys(sessionStorage),
      }));

      const preflightShot = shotDir ? path.join(shotDir, 'cpu-preflight-empty-archive.png') : null;
      if (preflightShot) {
        await page.screenshot({ path: preflightShot });
      }

      const out = {
        mode: 'cpu-preflight',
        liveModelExecuted: false,
        edgeBrowserVersion: browserVersion,
        apiPort,
        uiPort,
        elapsedMs: Date.now() - startedMs,
        archiveItemCount: 0,
        fixtureBindingsVerified: {
          synWo01Bytes: EXPECTED_WO_BYTES,
          synWo01Sha256: EXPECTED_WO_SHA256,
          synMp01Bytes: EXPECTED_MP_BYTES,
          synMp01Sha256: EXPECTED_MP_SHA256,
        },
        storageAudit,
        screenshot: preflightShot ? path.relative(repoRoot, preflightShot).replace(/\\/g, '/') : null,
      };
      writeFileSync(outPath, JSON.stringify(out, null, 2) + '\n', 'utf8');
      console.log(`CPU preflight Edge smoke PASSED (${browserVersion}; 0 documents, 0 OCR calls).`);
      return;
    }

    if (mode === 'live-phase-a') {
      const timings = {};

      // --- Document 1: SYN-WO-01-v1-raster300.pdf (1 page, Attempt 1 of 2) ---
      const tWoUpload0 = Date.now();
      await page.goto(`${uiBase}/`, { waitUntil: 'networkidle' });
      await page.getByTestId('file-input').setInputFiles(WO_FIXTURE_PATH);
      await page.getByTestId('submit').click();
      await page.getByTestId('receipt').waitFor({ state: 'visible', timeout: 30000 });
      const woDocId = ((await page.getByTestId('receipt-document-id').textContent()) ?? '').trim();
      const woReceiptSha = ((await page.getByTestId('receipt-sha256').textContent()) ?? '').trim();
      if (woReceiptSha !== EXPECTED_WO_SHA256) {
        throw new Error(`WO receipt SHA mismatch: ${woReceiptSha}`);
      }
      timings.woUploadMs = Date.now() - tWoUpload0;

      await page.getByTestId('receipt-open').click();
      await page.getByTestId('request-extraction').waitFor({ state: 'visible', timeout: 25000 });
      await page.getByTestId('request-extraction').click();

      // Max wait: 1800s load + 1800s 1p call + 120s grace = 3720s
      const woExtOutcome = await waitForRealExtractionCompletion(page, apiBase, woDocId, 3720, shotDir, 'wo01');
      timings.woExtractionWallMs = woExtOutcome.wallElapsedMs;
      const woRawSha256 = woExtOutcome.extractionView.result.rawSha256;

      if (shotDir) {
        await page.waitForTimeout(1500);
        await page.screenshot({ path: path.join(shotDir, 'live-01-wo01-extracted-result.png') });
      }

      // Open Work-Order Review for SYN-WO-01
      const tWoReview0 = Date.now();
      await page.getByTestId('open-work-order-review').click();
      await page.getByTestId('review-workspace').waitFor({ state: 'visible', timeout: 25000 });
      await page.waitForTimeout(1800);

      for (const [fieldKey, printedVal] of Object.entries(WO_PRINTED_FIELDS)) {
        const machineTxt = ((await page.getByTestId(`machine-value-${fieldKey}`).textContent()) ?? '').trim();
        const acceptDisabled = await page.getByTestId(`btn-accept-${fieldKey}`).isDisabled();
        if (!acceptDisabled && machineTxt === printedVal) {
          await page.getByTestId(`btn-accept-${fieldKey}`).click();
        } else {
          await page.getByTestId(`btn-edit-${fieldKey}`).click();
          await page.getByTestId(`input-value-${fieldKey}`).fill(printedVal);
        }
      }

      await page.getByTestId('btn-edit-issue_and_resolution').click();
      await page.getByTestId('input-value-issue_and_resolution').fill(WO_GROUNDED_ISSUE_REV1);
      await page.getByTestId('input-operator-label').fill('WP-0012 Author Rehearsal');
      await page.getByTestId('confirm-reviewed-checkbox').check();
      await page.getByTestId('save-reviewed').click();
      await waitForCondition(
        async () => ((await page.getByTestId('current-revision-number').textContent()) ?? '').trim() === '#1',
        'SYN-WO-01 Reviewed Revision #1 saved',
      );

      // Save distinct newer pending Draft Revision #2 on SYN-WO-01
      await page.getByTestId('btn-edit-issue_and_resolution').click();
      await page.getByTestId('input-value-issue_and_resolution').fill(WO_GROUNDED_DRAFT_REV2);
      await page.getByTestId('save-draft').click();
      await waitForCondition(
        async () =>
          ((await page.getByTestId('current-revision-number').textContent()) ?? '').trim() === '#2' &&
          (await page.getByTestId('prior-reviewed-historical-warning').isVisible()),
        'SYN-WO-01 newer Draft Revision #2 saved alongside prior Reviewed Revision #1',
      );
      timings.woReviewMs = Date.now() - tWoReview0;
      if (shotDir) {
        await page.screenshot({ path: path.join(shotDir, 'live-02-wo01-rev1-reviewed-rev2-draft.png') });
      }

      // --- Document 2: SYN-MP-01-v0-clean.pdf (3 pages, Attempt 2 of 2) ---
      const tMpUpload0 = Date.now();
      await page.getByTestId('nav-intake').click();
      await page.getByTestId('file-input').waitFor({ state: 'visible', timeout: 20000 });
      await page.getByTestId('file-input').setInputFiles(MP_FIXTURE_PATH);
      await page.getByTestId('submit').click();
      await page.getByTestId('receipt').waitFor({ state: 'visible', timeout: 30000 });
      const mpDocId = ((await page.getByTestId('receipt-document-id').textContent()) ?? '').trim();
      const mpReceiptSha = ((await page.getByTestId('receipt-sha256').textContent()) ?? '').trim();
      if (mpReceiptSha !== EXPECTED_MP_SHA256) {
        throw new Error(`MP receipt SHA mismatch: ${mpReceiptSha}`);
      }
      timings.mpUploadMs = Date.now() - tMpUpload0;

      await page.getByTestId('receipt-open').click();
      await page.getByTestId('request-extraction').waitFor({ state: 'visible', timeout: 25000 });
      await page.getByTestId('request-extraction').click();

      // Max wait: 1800s load + 3600s 3p call + 120s grace = 5520s
      const mpExtOutcome = await waitForRealExtractionCompletion(page, apiBase, mpDocId, 5520, shotDir, 'mp01');
      timings.mpExtractionWallMs = mpExtOutcome.wallElapsedMs;
      const mpRawSha256 = mpExtOutcome.extractionView.result.rawSha256;

      if (shotDir) {
        await page.waitForTimeout(1500);
        await page.screenshot({ path: path.join(shotDir, 'live-03-mp01-3page-extracted-result.png') });
      }

      // Open Work-Order Review for SYN-MP-01 (2 explicit unknowns + 3 grounded printed values)
      const tMpReview0 = Date.now();
      await page.getByTestId('open-work-order-review').click();
      await page.getByTestId('review-workspace').waitFor({ state: 'visible', timeout: 25000 });

      // Inspect Pages 1, 2, 3 in two-pane viewer
      await page.getByTestId('pdf-page-btn-2').click();
      await page.waitForTimeout(600);
      await page.getByTestId('pdf-page-btn-3').click();
      await page.waitForTimeout(600);
      await page.getByTestId('pdf-page-btn-1').click();
      await page.waitForTimeout(1000);

      await page.getByTestId('btn-unknown-work_order_id').click();
      await page.getByTestId('input-unknown-reason-work_order_id').fill(MP_GROUNDED_REVIEW.work_order_id_unknown_reason);

      await page.getByTestId('btn-edit-property_name').click();
      await page.getByTestId('input-value-property_name').fill(MP_GROUNDED_REVIEW.property_name);

      await page.getByTestId('btn-edit-building_unit').click();
      await page.getByTestId('input-value-building_unit').fill(MP_GROUNDED_REVIEW.building_unit);

      await page.getByTestId('btn-unknown-requested_date').click();
      await page.getByTestId('input-unknown-reason-requested_date').fill(MP_GROUNDED_REVIEW.requested_date_unknown_reason);

      await page.getByTestId('btn-edit-issue_and_resolution').click();
      await page.getByTestId('input-value-issue_and_resolution').fill(MP_GROUNDED_REVIEW.issue_and_resolution);

      await page.getByTestId('input-operator-label').fill('WP-0012 Author Rehearsal');
      await page.getByTestId('confirm-reviewed-checkbox').check();
      await page.getByTestId('save-reviewed').click();
      await waitForCondition(
        async () =>
          ((await page.getByTestId('review-status-badge').textContent()) ?? '').includes(
            'Reviewed (Revision #1 · 2 unknown)',
          ),
        'SYN-MP-01 Reviewed Revision #1 with 2 unknowns saved',
      );
      timings.mpReviewMs = Date.now() - tMpReview0;
      if (shotDir) {
        await page.screenshot({ path: path.join(shotDir, 'live-04-mp01-reviewed-2-unknowns.png') });
      }

      const stateRecord = {
        woDocId,
        woResultId: woExtOutcome.extractionView.result.resultId,
        woAttemptId: woExtOutcome.extractionView.result.attemptId,
        woRawSha256,
        woRawByteLength: woExtOutcome.extractionView.result.rawByteLength,
        woProvenance: woExtOutcome.extractionView.result.provenance,
        woObservedPhases: woExtOutcome.observedPhases,
        mpDocId,
        mpResultId: mpExtOutcome.extractionView.result.resultId,
        mpAttemptId: mpExtOutcome.extractionView.result.attemptId,
        mpRawSha256,
        mpRawByteLength: mpExtOutcome.extractionView.result.rawByteLength,
        mpProvenance: mpExtOutcome.extractionView.result.provenance,
        mpObservedPhases: mpExtOutcome.observedPhases,
      };
      if (statePath) {
        mkdirSync(path.dirname(statePath), { recursive: true });
        writeFileSync(statePath, JSON.stringify(stateRecord, null, 2) + '\n', 'utf8');
      }

      const tSearch0 = Date.now();
      const archiveCheck = await verifyArchiveAndReopenWorkflow(
        page,
        apiBase,
        uiBase,
        stateRecord,
        'before-restart',
        shotDir,
      );
      timings.preRestartArchiveAndReopenMs = Date.now() - tSearch0;

      const out = {
        mode: 'live-phase-a',
        liveModelExecuted: true,
        edgeBrowserVersion: browserVersion,
        timings,
        documents: stateRecord,
        preRestartArchiveVerification: archiveCheck,
      };
      writeFileSync(outPath, JSON.stringify(out, null, 2) + '\n', 'utf8');
      console.log(`Live Phase A rehearsal PASSED (${browserVersion}; 2 real model attempts completed).`);
      return;
    }

    if (mode === 'live-phase-b-reopen') {
      if (!statePath) {
        throw new Error('--stateFile <path> is required for --mode live-phase-b-reopen');
      }
      const stateRecord = JSON.parse(readFileSync(statePath, 'utf8'));
      const t0 = Date.now();
      const archiveCheck = await verifyArchiveAndReopenWorkflow(
        page,
        apiBase,
        uiBase,
        stateRecord,
        'after-restart-ocr-disabled',
        shotDir,
      );
      const out = {
        mode: 'live-phase-b-reopen',
        liveModelExecuted: false,
        ocrEnabledDuringReopen: false,
        edgeBrowserVersion: browserVersion,
        elapsedMs: Date.now() - t0,
        postRestartArchiveVerification: archiveCheck,
      };
      writeFileSync(outPath, JSON.stringify(out, null, 2) + '\n', 'utf8');
      console.log(`Live Phase B disabled-OCR reopen PASSED (${browserVersion}).`);
      return;
    }

    throw new Error(`Unsupported --mode '${mode}'`);
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
