import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';

const repoRoot = path.resolve(import.meta.dirname, '..', '..', '..', '..', '..', '..');
if (!existsSync(path.join(repoRoot, 'ELedgerCare.slnx'))) {
  throw new Error(`Resolved repoRoot does not contain ELedgerCare.slnx: ${repoRoot}`);
}

const requireFromWeb = createRequire(path.join(repoRoot, 'web', 'package.json'));
const { chromium } = requireFromWeb('@playwright/test');

const SEED1_WO_DOC_ID = '01a1e571-2838-714b-861b-bf0835d7c90a';
const SEED1_WO_RESULT_ID = '01a1e573-a855-7735-96e1-f5d14cada602';
const SEED1_WO_PDF_SHA = '47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd';
const SEED1_WO_RAW_SHA = '7503761ae46afef6adf579881d011764283474354fac3e185598fc7d266aff95';
const MODEL_REV = '0480966938291445591f69f08a13b041c073a96a';

const SEED2_MP_DOC_ID = '01a1e573-ca14-72ba-a46a-c84690288e22';
const SEED2_MP_PDF_SHA = '15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3';

const SEED3_CAP_DOC_ID = '01a1e578-8f3a-7e0c-826b-a2c9dc066a8f';

const UUID_REGEX = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/i;
const HEX64_REGEX = /\b[0-9a-f]{64}\b/i;

function assert(condition, message) {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

function sha256Hex(buf) {
  return createHash('sha256').update(buf).digest('hex');
}

async function waitForCondition(fn, description, timeoutMs = 20_000) {
  const deadline = Date.now() + timeoutMs;
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      const val = await fn();
      if (val) {
        return val;
      }
    } catch (err) {
      lastError = err;
    }
    await new Promise((r) => setTimeout(r, 150));
  }
  throw new Error(
    `Timed out waiting for ${description}${lastError ? ` (last error: ${lastError.message})` : ''}`,
  );
}

async function waitForExactText(locator, expected, timeoutMs = 20_000) {
  return waitForCondition(async () => {
    if ((await locator.count()) === 0) return false;
    const txt = ((await locator.first().textContent()) ?? '').trim();
    return txt === expected ? txt : false;
  }, `exact text '${expected}'`, timeoutMs);
}

async function waitForTextContains(locator, substring, timeoutMs = 20_000) {
  return waitForCondition(async () => {
    if ((await locator.count()) === 0) return false;
    const txt = ((await locator.first().textContent()) ?? '').trim();
    return txt.includes(substring) ? txt : false;
  }, `text containing '${substring}'`, timeoutMs);
}

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 2) {
    const k = argv[i];
    const v = argv[i + 1];
    if (!k?.startsWith('--') || v === undefined) {
      throw new Error(`Invalid CLI arguments near '${k}'`);
    }
    args[k.slice(2)] = v;
  }
  return args;
}

async function capturePng(page, screenshotsDir, filename, records) {
  const outPath = path.join(screenshotsDir, filename);
  await page.screenshot({ path: outPath, fullPage: false });
  const buf = readFileSync(outPath);
  records.push({
    file: filename,
    bytes: buf.length,
    sha256: sha256Hex(buf),
  });
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.config) {
    throw new Error('Missing --config <path>');
  }
  const cfg = JSON.parse(readFileSync(args.config, 'utf-8'));
  const baseUrl = `http://127.0.0.1:${cfg.uiPort}`;
  mkdirSync(cfg.screenshotsDir, { recursive: true });

  process.env.PLAYWRIGHT_BROWSERS_PATH = path.join(repoRoot, '.local', 'ms-playwright');

  const browser = await chromium.launch({
    channel: 'msedge',
    headless: true,
  });

  const screenshots = [];
  try {
    const browserVersion = browser.version();
    const context = await browser.newContext({
      viewport: { width: 1680, height: 980 },
      acceptDownloads: true,
    });

    // -------------------------------------------------------------------------
    // 1. Preserved /004 Seed 1 (SYN-WO-01 at Reviewed Revision #4 · 1 unknown)
    //    Default presentation: closed <details>, zero internal IDs/UUIDs/SHA-256s
    // -------------------------------------------------------------------------
    const page1 = await context.newPage();
    await page1.goto(`${baseUrl}/documents/${SEED1_WO_DOC_ID}/review`, { waitUntil: 'networkidle' });

    await waitForExactText(page1.getByTestId('review-status-badge'), 'Reviewed (Revision #4 · 1 unknown)');
    await waitForExactText(page1.getByTestId('current-revision-number'), '#4');
    await waitForTextContains(page1.getByTestId('pdf-current-page'), 'Page 1 of 1');

    const detailsOpenInitially = await page1
      .getByTestId('review-provenance-details')
      .evaluate((el) => el.open === true);
    assert(detailsOpenInitially === false, 'review-provenance-details must be closed initially');

    for (const hiddenTestId of [
      'review-profile-id',
      'review-field-schema',
      'review-suggestion-policy',
      'review-document-id',
      'review-result-id',
      'review-original-sha256',
      'review-raw-sha256',
      'review-model-checkpoint',
      'technical-field-key-work_order_id',
      'technical-field-key-property_name',
      'technical-field-key-building_unit',
      'technical-field-key-requested_date',
      'technical-field-key-issue_and_resolution',
    ]) {
      const visible = await page1.getByTestId(hiddenTestId).isVisible();
      assert(visible === false, `${hiddenTestId} must be hidden when provenance details are closed`);
    }

    const defaultWoVisibleText = await page1.getByTestId('review-workspace').innerText();
    const forbiddenDefaultTokens = [
      'maintenance-work-order/1',
      'maintenance-work-order-fields/1',
      'work-order-suggestions/1',
      'work_order_id',
      'property_name',
      'building_unit',
      'requested_date',
      'issue_and_resolution',
      'UTF-16 code units',
      'Idempotency-Key',
      SEED1_WO_DOC_ID,
      SEED1_WO_RESULT_ID,
      SEED1_WO_PDF_SHA,
      SEED1_WO_RAW_SHA,
      MODEL_REV,
    ];
    for (const token of forbiddenDefaultTokens) {
      assert(
        !defaultWoVisibleText.includes(token),
        `Default visible review flow leaked internal token '${token}'`,
      );
    }
    assert(!UUID_REGEX.test(defaultWoVisibleText), 'Default visible review flow leaked a raw UUID');
    assert(!HEX64_REGEX.test(defaultWoVisibleText), 'Default visible review flow leaked a 64-hex SHA-256');

    const requiredPlainStrings = [
      'Work-order review & source comparison',
      'Compare the original PDF beside the five work-order fields · Local unauthenticated operator review.',
      'Unsaved edits and pending retries remain in page memory only (never written to browser storage).',
      'Provenance & technical details',
      'Five work-order fields',
      'Work Order ID',
      'Property',
      'Building / Unit',
      'Requested Date',
      'Issue & Resolution',
      'max 64 characters',
      'max 200 characters',
      'max 120 characters',
      'max 4000 characters',
      '9 / 64 characters',
      'Source quote (Page 1): WO-004192',
      'View Page 1',
      'Reason marked unknown (optional, single line, max 500 characters):',
      '(optional self-reported local note, max 80 characters — unauthenticated)',
      'Saved revision history (4)',
      '2 accepted, 2 edited, 1 unknown',
      'Reviewer Final Sign-off',
    ];
    for (const plain of requiredPlainStrings) {
      assert(
        defaultWoVisibleText.includes(plain),
        `Default visible review flow missing expected plain string '${plain}'`,
      );
    }

    // Verify preserved /004 field values & history rows 1..4 on Seed 1
    assert((await page1.getByTestId('input-value-work_order_id').inputValue()) === 'WO-004192', 'Seed 1 work_order_id value');
    assert(
      (await page1.getByTestId('input-value-property_name').inputValue()) ===
        'Cedar Hollow Apartments — Reviewer Verified North',
      'Seed 1 property_name value',
    );
    assert(
      (await page1.getByTestId('input-value-building_unit').inputValue()) ===
        'Bldg B - Unit 204 (Field Confirmed)',
      'Seed 1 building_unit value',
    );
    assert(
      (await page1.getByTestId('input-unknown-reason-requested_date').inputValue()) ===
        'Printed request date smudged on carbon copy; awaiting dispatch log',
      'Seed 1 requested_date unknownReason',
    );
    assert((await page1.getByTestId('input-operator-label').inputValue()) === 'Reviewer Final Sign-off', 'Seed 1 operator label');
    for (const revNum of [1, 2, 3, 4]) {
      assert((await page1.getByTestId(`history-row-${revNum}`).count()) === 1, `Seed 1 history row #${revNum} present`);
    }

    await page1.waitForTimeout(2500);
    await capturePng(page1, cfg.screenshotsDir, '01-reviewer-p007-wo01-rev4-default.png', screenshots);

    // -------------------------------------------------------------------------
    // 2. Expand Provenance & technical details: verify exact values on demand
    // -------------------------------------------------------------------------
    await page1.getByTestId('toggle-review-provenance').click();
    await waitForCondition(
      () => page1.getByTestId('review-provenance-details').evaluate((el) => el.open === true),
      'review-provenance-details open',
    );

    const expandedProvenance = {
      profileId: await waitForExactText(page1.getByTestId('review-profile-id'), 'maintenance-work-order/1'),
      fieldSchema: await waitForExactText(page1.getByTestId('review-field-schema'), 'maintenance-work-order-fields/1'),
      suggestionPolicy: await waitForExactText(page1.getByTestId('review-suggestion-policy'), 'work-order-suggestions/1'),
      documentId: await waitForExactText(page1.getByTestId('review-document-id'), SEED1_WO_DOC_ID),
      resultId: await waitForExactText(page1.getByTestId('review-result-id'), SEED1_WO_RESULT_ID),
      originalSha256: await waitForExactText(page1.getByTestId('review-original-sha256'), SEED1_WO_PDF_SHA),
      rawSha256: await waitForExactText(page1.getByTestId('review-raw-sha256'), SEED1_WO_RAW_SHA),
      modelCheckpoint: await waitForExactText(
        page1.getByTestId('review-model-checkpoint'),
        `baidu/Unlimited-OCR-2 @ ${MODEL_REV}`,
      ),
      fieldKeys: {
        work_order_id: await waitForExactText(page1.getByTestId('technical-field-key-work_order_id'), 'work_order_id'),
        property_name: await waitForExactText(page1.getByTestId('technical-field-key-property_name'), 'property_name'),
        building_unit: await waitForExactText(page1.getByTestId('technical-field-key-building_unit'), 'building_unit'),
        requested_date: await waitForExactText(page1.getByTestId('technical-field-key-requested_date'), 'requested_date'),
        issue_and_resolution: await waitForExactText(
          page1.getByTestId('technical-field-key-issue_and_resolution'),
          'issue_and_resolution',
        ),
      },
    };
    const expandedDetailsText = await page1.getByTestId('review-provenance-details').innerText();
    assert(expandedDetailsText.includes('UTF-16 code units'), 'Expanded provenance shows UTF-16 code unit detail');
    assert(expandedDetailsText.includes('page 1, block 4'), 'Expanded provenance shows source block ordinals');

    await capturePng(page1, cfg.screenshotsDir, '02-reviewer-p007-wo01-rev4-expanded-provenance.png', screenshots);

    await page1.getByTestId('toggle-review-provenance').click();
    await waitForCondition(
      () => page1.getByTestId('review-provenance-details').evaluate((el) => el.open === false),
      'review-provenance-details closed again',
    );

    // -------------------------------------------------------------------------
    // 3. Historical snapshot view (Revision #2) plain-language verification
    // -------------------------------------------------------------------------
    await page1.getByTestId('view-revision-2').click();
    await waitForTextContains(
      page1.getByTestId('historical-revision-banner'),
      'Viewing immutable historical Revision #2 (reviewed)',
    );
    const histVisibleText = await page1.getByTestId('fields-review-pane').innerText();
    assert(histVisibleText.includes('Historical snapshot — Revision #2 (reviewed)'), 'Historical heading plain');
    assert(histVisibleText.includes('View Page 1'), 'Historical jump button plain');
    assert(histVisibleText.includes('Page 1 — quote: WO-004192'), 'Historical consulted source plain');
    assert(!histVisibleText.includes('work_order_id'), 'Historical snapshot hides snake_case fieldKey');
    assert(!histVisibleText.includes('Block 4'), 'Historical snapshot hides raw block ordinal in default view');

    await page1.getByTestId('return-to-current-head').click();
    await waitForCondition(
      async () => (await page1.getByTestId('historical-revision-banner').count()) === 0,
      'returned from historical Revision #2 to head #4',
    );

    // -------------------------------------------------------------------------
    // 4. Plain-label client validation, inline unsaved-edits warning, route guard,
    //    and pre-network uncertain-save banner (ZERO packets sent to API/PostgreSQL!)
    // -------------------------------------------------------------------------
    await page1.getByTestId('input-value-work_order_id').fill('   ');
    await waitForTextContains(
      page1.getByTestId('unsaved-edits-warning'),
      'Unsaved edits in page memory: Save a draft or reviewed revision before closing or leaving this page.',
    );

    // Verify plain DisplayLabel in client-side validation error (never snake_case work_order_id)
    await page1.getByTestId('save-draft').click();
    const valErrText = await waitForTextContains(
      page1.getByTestId('review-validation-error'),
      '"Work Order ID" requires a non-whitespace value when marked edited.',
    );
    assert(!valErrText.includes('work_order_id'), 'Validation error must use plain label, not fieldKey');

    // Verify unsavedReviewChangesGuard prompts before leaving and dismissing preserves unsaved state
    let leaveGuardPrompt = null;
    page1.once('dialog', async (dialog) => {
      leaveGuardPrompt = dialog.message();
      await dialog.dismiss();
    });
    await page1.getByTestId('back-to-document').click();
    await waitForCondition(() => leaveGuardPrompt !== null, 'unsavedReviewChangesGuard confirm dialog');
    assert(
      leaveGuardPrompt.includes('unsaved work-order review changes'),
      `Unexpected guard prompt: ${leaveGuardPrompt}`,
    );
    assert(page1.url().endsWith(`/documents/${SEED1_WO_DOC_ID}/review`), 'Guard kept operator on review route');

    // Trigger uncertain save via pre-network route abort (never reaches API/PostgreSQL, preserving Seed 1 Rev 4!)
    await page1.getByTestId('input-value-work_order_id').fill('WO-004192 — Unsaved Reviewer Memory Check');
    let interceptedOperationKey = null;
    const postPattern = `**/api/documents/${SEED1_WO_DOC_ID}/review/revisions`;
    await page1.route(postPattern, async (route) => {
      interceptedOperationKey = route.request().headers()['idempotency-key'] ?? null;
      await route.abort('connectionreset');
    });

    await page1.getByTestId('save-draft').click();
    await waitForTextContains(
      page1.getByTestId('uncertain-save-banner'),
      'Save outcome uncertain — connection interrupted before confirmation.',
    );
    assert(
      typeof interceptedOperationKey === 'string' && UUID_REGEX.test(interceptedOperationKey),
      'Captured valid UUID Idempotency-Key on intercepted POST',
    );

    const uncertainDetailsOpenInitially = await page1
      .getByTestId('uncertain-save-details')
      .evaluate((el) => el.open === true);
    assert(uncertainDetailsOpenInitially === false, 'uncertain-save-details must be closed initially');
    assert(
      (await page1.getByTestId('pending-review-key').isVisible()) === false,
      'pending-review-key must be hidden initially',
    );

    const uncertainDefaultText = await page1.getByTestId('uncertain-save-banner').innerText();
    assert(uncertainDefaultText.includes('Retry pending save'), 'Plain Retry pending save CTA visible');
    assert(uncertainDefaultText.includes('Check saved state'), 'Plain Check saved state CTA visible');
    assert(!uncertainDefaultText.includes(interceptedOperationKey), 'Operation UUID hidden from default uncertain banner');
    assert(!uncertainDefaultText.includes('Idempotency-Key'), 'Protocol header name hidden from default uncertain banner');
    assert(!UUID_REGEX.test(uncertainDefaultText), 'Zero raw UUIDs in default uncertain banner');

    await capturePng(page1, cfg.screenshotsDir, '03-reviewer-p007-uncertain-default.png', screenshots);

    await page1.getByTestId('toggle-uncertain-save-details').click();
    await waitForCondition(
      () => page1.getByTestId('uncertain-save-details').evaluate((el) => el.open === true),
      'uncertain-save-details open',
    );
    await waitForExactText(page1.getByTestId('pending-review-key'), interceptedOperationKey);

    await capturePng(page1, cfg.screenshotsDir, '04-reviewer-p007-uncertain-expanded.png', screenshots);
    await page1.unroute(postPattern);

    const storageAudit = await page1.evaluate(async () => {
      const dbs = typeof indexedDB.databases === 'function' ? await indexedDB.databases() : [];
      return {
        localStorageKeys: Object.keys(localStorage),
        sessionStorageKeys: Object.keys(sessionStorage),
        indexedDbCount: dbs.length,
        forbiddenDomCount: document.querySelectorAll('script[src*="onerror"], img[onerror]').length,
      };
    });
    assert(storageAudit.localStorageKeys.length === 0, 'Zero localStorage keys');
    assert(storageAudit.sessionStorageKeys.length === 0, 'Zero sessionStorage keys');
    assert(storageAudit.indexedDbCount === 0, 'Zero IndexedDB databases');
    assert(storageAudit.forbiddenDomCount === 0, 'Zero unsafe DOM elements');
    await page1.close();

    // -------------------------------------------------------------------------
    // 5. Preserved /004 Seed 3 (128-revision cap intact, plain default view)
    // -------------------------------------------------------------------------
    const page3 = await context.newPage();
    await page3.goto(`${baseUrl}/documents/${SEED3_CAP_DOC_ID}/review`, { waitUntil: 'networkidle' });
    await waitForExactText(page3.getByTestId('current-revision-number'), '#128');
    await waitForTextContains(
      page3.getByTestId('revision-cap-notice'),
      'Maximum of 128 revisions reached for this extraction result; history remains readable.',
    );
    const seed3DetailsOpen = await page3
      .getByTestId('review-provenance-details')
      .evaluate((el) => el.open === true);
    assert(seed3DetailsOpen === false, 'Seed 3 review-provenance-details closed initially');
    const seed3VisibleText = await page3.getByTestId('review-workspace').innerText();
    assert(seed3VisibleText.includes('Saved revision history (128)'), 'Seed 3 preserves all 128 history rows');
    assert(!UUID_REGEX.test(seed3VisibleText), 'Seed 3 default visible text contains zero raw UUIDs');
    assert(!HEX64_REGEX.test(seed3VisibleText), 'Seed 3 default visible text contains zero 64-hex hashes');
    await page3.close();

    // -------------------------------------------------------------------------
    // 6. Preserved /004 Seed 2 (3-page SYN-MP-01, #page=1..3 navigation & download)
    // -------------------------------------------------------------------------
    const page2 = await context.newPage();
    await page2.goto(`${baseUrl}/documents/${SEED2_MP_DOC_ID}/review`, { waitUntil: 'networkidle' });
    await waitForExactText(page2.getByTestId('review-status-badge'), 'Unreviewed preview (Revision 0)');
    await waitForTextContains(page2.getByTestId('pdf-current-page'), 'Page 1 of 3');

    const seed2DetailsOpen = await page2
      .getByTestId('review-provenance-details')
      .evaluate((el) => el.open === true);
    assert(seed2DetailsOpen === false, 'Seed 2 review-provenance-details closed initially');

    await page2.getByTestId('pdf-page-btn-2').click();
    await waitForTextContains(page2.getByTestId('pdf-current-page'), 'Page 2 of 3');
    await waitForCondition(async () => {
      const src = await page2.getByTestId('pdf-preview-frame').getAttribute('src');
      return typeof src === 'string' && src.endsWith('#page=2');
    }, 'iframe #page=2');

    const seed2Page2VisibleText = await page2.getByTestId('review-workspace').innerText();
    assert(seed2Page2VisibleText.includes('No suggestion (missing)'), 'Seed 2 shows plain missing status');
    assert(!UUID_REGEX.test(seed2Page2VisibleText), 'Seed 2 default visible text contains zero raw UUIDs');
    assert(!HEX64_REGEX.test(seed2Page2VisibleText), 'Seed 2 default visible text contains zero 64-hex hashes');

    await page2.waitForTimeout(2500);
    await capturePng(page2, cfg.screenshotsDir, '05-reviewer-p007-mp01-page2-default.png', screenshots);

    await page2.getByTestId('pdf-page-btn-3').click();
    await waitForTextContains(page2.getByTestId('pdf-current-page'), 'Page 3 of 3');
    await waitForCondition(async () => {
      const src = await page2.getByTestId('pdf-preview-frame').getAttribute('src');
      return typeof src === 'string' && src.endsWith('#page=3');
    }, 'iframe #page=3');

    const [download] = await Promise.all([
      page2.waitForEvent('download'),
      page2.getByTestId('pdf-download-fallback').click(),
    ]);
    const dlPath = await download.path();
    const dlBuf = readFileSync(dlPath);
    const dlSha = sha256Hex(dlBuf);
    assert(dlBuf.length === 8422 && dlSha === SEED2_MP_PDF_SHA, 'Seed 2 downloaded PDF SHA-256 matches exact original');
    await page2.close();

    const receipt = {
      schema: 'eledgercare.wp-0008.f3-reviewer-p007-edge-receipt/1',
      browserVersion,
      seed1DocumentId: SEED1_WO_DOC_ID,
      seed1SavedHeadRevisionVerified: 4,
      seed1HistoricalRevision2PlainVerified: true,
      defaultDetailsClosedInitially: true,
      uncertainDetailsClosedInitially: true,
      zeroUuidAndHex64InDefaultViews: true,
      plainClientValidationErrorVerified: valErrText,
      unsavedLeaveGuardPromptVerified: leaveGuardPrompt,
      interceptedPreNetworkOperationKey: interceptedOperationKey,
      expandedProvenance,
      seed3CapRevision128Preserved: true,
      seed2ThreePageNavigationVerified: true,
      seed2DownloadedBytes: dlBuf.length,
      seed2DownloadedSha256: dlSha,
      storageAudit,
      screenshots,
    };
    writeFileSync(cfg.receiptPath, JSON.stringify(receipt, null, 2) + '\n', 'utf-8');
  } finally {
    await browser.close();
  }
}

await main();
