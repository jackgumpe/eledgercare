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

const SEED2_MP_DOC_ID = '01a1e573-ca14-72ba-a46a-c84690288e22';
const SEED2_MP_PDF_SHA = '15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3';

const SEED4_F1_DOC_ID = '01a1e580-0000-7000-8000-000000000001';

function assert(condition, message) {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

function sha256Hex(buf) {
  return createHash('sha256').update(buf).digest('hex');
}

async function waitForTextContains(locator, substring, timeoutMs = 20_000) {
  const deadline = Date.now() + timeoutMs;
  let lastText = '';
  while (Date.now() < deadline) {
    if ((await locator.count()) > 0) {
      lastText = ((await locator.first().textContent()) ?? '').trim();
      if (lastText.includes(substring)) {
        return lastText;
      }
    }
    await new Promise((r) => setTimeout(r, 150));
  }
  throw new Error(`Timed out waiting for text containing '${substring}' (last='${lastText}')`);
}

async function waitForExactText(locator, expected, timeoutMs = 20_000) {
  const deadline = Date.now() + timeoutMs;
  let lastText = '';
  while (Date.now() < deadline) {
    if ((await locator.count()) > 0) {
      lastText = ((await locator.first().textContent()) ?? '').trim();
      if (lastText === expected) {
        return lastText;
      }
    }
    await new Promise((r) => setTimeout(r, 150));
  }
  throw new Error(`Timed out waiting for exact text '${expected}' (last='${lastText}')`);
}

async function waitForEnabled(locator, label, timeoutMs = 15_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if ((await locator.count()) > 0 && (await locator.first().isEnabled())) {
      return;
    }
    await new Promise((r) => setTimeout(r, 75));
  }
  throw new Error(`Timed out waiting for '${label}' to become enabled`);
}

async function waitForDisabled(locator, label, timeoutMs = 15_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if ((await locator.count()) > 0 && (await locator.first().isDisabled())) {
      return;
    }
    await new Promise((r) => setTimeout(r, 75));
  }
  throw new Error(`Timed out waiting for '${label}' to become disabled`);
}

async function waitForAttr(locator, attrName, expectedVal, timeoutMs = 15_000) {
  const deadline = Date.now() + timeoutMs;
  let lastVal = null;
  while (Date.now() < deadline) {
    if ((await locator.count()) > 0) {
      lastVal = await locator.first().getAttribute(attrName);
      if (lastVal === expectedVal) {
        return;
      }
    }
    await new Promise((r) => setTimeout(r, 75));
  }
  throw new Error(`Timed out waiting for attribute ${attrName}='${expectedVal}' (last='${lastVal}')`);
}

async function readStorageState(page) {
  return await page.evaluate(async () => {
    const idbList = 'databases' in indexedDB ? await indexedDB.databases() : [];
    return {
      localKeys: Object.keys(localStorage),
      sessionKeys: Object.keys(sessionStorage),
      idbCount: idbList.length,
    };
  });
}

function assertZeroStorage(storage, label) {
  assert(
    storage.localKeys.length === 0 && storage.sessionKeys.length === 0 && storage.idbCount === 0,
    `${label}: expected zero browser storage entries, got ${JSON.stringify(storage)}`,
  );
}

function recordScreenshot(shotPath) {
  const bytes = readFileSync(shotPath);
  assert(bytes.length > 20_000, `Screenshot unexpectedly small (${bytes.length} B): ${shotPath}`);
  return {
    file: path.basename(shotPath),
    bytes: bytes.length,
    sha256: sha256Hex(bytes),
  };
}

async function main() {
  const args = process.argv.slice(2);
  const phaseIdx = args.indexOf('--phase');
  const configIdx = args.indexOf('--config');
  if (phaseIdx < 0 || configIdx < 0) {
    throw new Error('Usage: node verify_f3_edge_reviewer.mjs --phase <before-restart|after-restart> --config <path>');
  }

  const phase = args[phaseIdx + 1];
  const cfg = JSON.parse(readFileSync(args[configIdx + 1], 'utf8'));
  const uiBase = `http://127.0.0.1:${cfg.uiPort}`;
  const screenshotsDir = cfg.screenshotsDir;
  mkdirSync(screenshotsDir, { recursive: true });

  const woPdfBytes = readFileSync(path.join(repoRoot, 'tests', 'fixtures', 'SYN-WO-01-v1-raster300.pdf'));
  assert(woPdfBytes.length === 372_258 && sha256Hex(woPdfBytes) === SEED1_WO_PDF_SHA, 'SYN-WO-01 fixture hash mismatch');

  const mpPdfBytes = readFileSync(path.join(repoRoot, 'tests', 'fixtures', 'SYN-MP-01-v0-clean.pdf'));
  assert(mpPdfBytes.length === 8_422 && sha256Hex(mpPdfBytes) === SEED2_MP_PDF_SHA, 'SYN-MP-01 fixture hash mismatch');

  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const browserVersion = browser.version();
  const context = await browser.newContext({
    viewport: { width: 1680, height: 980 },
    acceptDownloads: true,
  });
  const tabA = await context.newPage();

  try {
    if (phase === 'before-restart') {
      // 1. Open Document screen for Seed 1 (SYN-WO-01) and confirm separate extraction vs review facts.
      await tabA.goto(`${uiBase}/documents/${SEED1_WO_DOC_ID}`, { waitUntil: 'networkidle' });
      await waitForExactText(tabA.getByTestId('document-status'), 'Completed (unreviewed)');
      await waitForExactText(tabA.getByTestId('document-review-status'), 'Not started');
      await waitForExactText(tabA.getByTestId('result-raw-sha256'), SEED1_WO_RAW_SHA);
      assert((await tabA.getByTestId('attempt-row-1').count()) === 1, 'Expected 1 extraction attempt on Seed 1');
      assert((await tabA.getByTestId('attempt-row-2').count()) === 0, 'Expected zero extra extraction attempts on Seed 1');

      // 2. Enter two-pane work-order review screen at Revision 0.
      await tabA.getByTestId('open-work-order-review').click();
      await waitForExactText(tabA.getByTestId('review-status-badge'), 'Unreviewed preview (Revision 0)');
      await waitForExactText(tabA.getByTestId('current-revision-number'), '#0');
      await waitForExactText(tabA.getByTestId('review-result-id'), SEED1_WO_RESULT_ID);
      await waitForExactText(tabA.getByTestId('review-raw-sha256'), SEED1_WO_RAW_SHA);
      await waitForExactText(tabA.getByTestId('review-original-sha256'), SEED1_WO_PDF_SHA);

      const frameSrc = await tabA.getByTestId('pdf-preview-frame').getAttribute('src');
      assert(
        frameSrc === `/api/documents/${SEED1_WO_DOC_ID}/preview#page=1`,
        `Unexpected iframe src on Seed 1: ${frameSrc}`,
      );

      // Verify all 5 conservative suggestions, initial unreviewed decisions, and zero confidence percentages.
      await waitForExactText(tabA.getByTestId('machine-value-work_order_id'), 'WO-004192');
      await waitForExactText(tabA.getByTestId('machine-value-property_name'), 'Cedar Hollow Apartments');
      await waitForExactText(tabA.getByTestId('machine-value-building_unit'), 'Bldg B - Unit 204');
      await waitForExactText(tabA.getByTestId('machine-value-requested_date'), '2026-10-16');
      const narrativeCand = await waitForTextContains(
        tabA.getByTestId('machine-value-issue_and_resolution'),
        'Air handler fan running continuously',
      );
      assert(narrativeCand.length === 298, `Expected 298-char narrative candidate, got ${narrativeCand.length}`);

      for (const fk of [
        'work_order_id',
        'property_name',
        'building_unit',
        'requested_date',
        'issue_and_resolution',
      ]) {
        await waitForExactText(tabA.getByTestId(`field-decision-${fk}`), 'unreviewed');
      }

      const bodyText0 = await tabA.locator('[data-testid="review-workspace"]').innerText();
      assert(!/confidence\s*:|\d+(\.\d+)?%\s*confident/i.test(bodyText0), 'Forbidden confidence percentage displayed');
      assertZeroStorage(await readStorageState(tabA), 'rev0-initial');

      // Allow Microsoft Edge native PDFium viewer to paint raster PDF before screenshot #01.
      await tabA.waitForTimeout(2500);
      const shot01Path = path.join(screenshotsDir, '01-reviewer-wo01-rev0-two-pane.png');
      await tabA.screenshot({ path: shot01Path });
      const shot01 = recordScreenshot(shot01Path);

      // 3. Save Revision #1 (draft: 2 accepted, 1 edited, 1 unknown + reason, 1 unreviewed draft value).
      await tabA.getByTestId('btn-accept-work_order_id').click();
      await tabA.getByTestId('btn-edit-property_name').click();
      await tabA.getByTestId('input-value-property_name').fill('Cedar Hollow Apartments — Reviewer Verified North');
      await tabA.getByTestId('btn-unknown-building_unit').click();
      await tabA
        .getByTestId('input-unknown-reason-building_unit')
        .fill('Door unit plate unreadable on scan; field check required');
      await tabA.getByTestId('btn-accept-requested_date').click();
      // Keep issue_and_resolution unreviewed with draft note (type then click Leave unreviewed).
      await tabA
        .getByTestId('input-value-issue_and_resolution')
        .fill('Draft technician note pending supervisor sign-off');
      await tabA.getByTestId('btn-unreviewed-issue_and_resolution').click();
      await tabA.getByTestId('input-operator-label').fill('Independent Reviewer Desk');

      await waitForDisabled(tabA.getByTestId('save-reviewed'), 'save-reviewed when unreviewed > 0');
      await tabA.getByTestId('save-draft').click();
      await waitForExactText(tabA.getByTestId('review-status-badge'), 'Saved draft (Revision #1)');
      await waitForExactText(tabA.getByTestId('current-revision-number'), '#1');
      assertZeroStorage(await readStorageState(tabA), 'after-rev1-draft');

      // 4. Resolve 5th field, verify premature save-reviewed stays disabled until confirmation checkbox, save Revision #2 (reviewed, 1 unknown).
      await tabA.getByTestId('btn-accept-issue_and_resolution').click();
      await waitForTextContains(tabA.getByTestId('unknown-fields-list'), 'Fields marked unknown (1): Building / Unit');
      await waitForDisabled(tabA.getByTestId('save-reviewed'), 'save-reviewed before confirmation checkbox');
      await waitForEnabled(tabA.getByTestId('confirm-reviewed-checkbox'), 'confirm-reviewed-checkbox when 0 unreviewed');
      await tabA.getByTestId('confirm-reviewed-checkbox').check();
      await waitForEnabled(tabA.getByTestId('save-reviewed'), 'save-reviewed after confirmation checkbox');
      await tabA.getByTestId('save-reviewed').click();

      await waitForExactText(tabA.getByTestId('review-status-badge'), 'Reviewed (Revision #2 · 1 unknown)');
      await waitForExactText(tabA.getByTestId('current-revision-number'), '#2');
      await tabA.evaluate(() => window.scrollTo(0, 0));
      await tabA.waitForTimeout(1000);
      const shot02Path = path.join(screenshotsDir, '02-reviewer-wo01-rev2-reviewed.png');
      await tabA.screenshot({ path: shot02Path });
      const shot02 = recordScreenshot(shot02Path);

      // 5. Verify Document screen shows Reviewed summary alongside untouched raw F2 status, then reopen review.
      await tabA.getByTestId('back-to-document').click();
      await waitForExactText(tabA.getByTestId('document-status'), 'Completed (unreviewed)');
      await waitForTextContains(tabA.getByTestId('document-review-status'), 'Reviewed (Revision #2 · 1 unknown)');
      await waitForExactText(tabA.getByTestId('result-raw-sha256'), SEED1_WO_RAW_SHA);
      await tabA.getByTestId('open-work-order-review').click();
      await waitForExactText(tabA.getByTestId('current-revision-number'), '#2');

      // 6. Open second tab (tabB) at #2, save post-review edit Revision #3 (draft) in tabA, inspect historical #2, and prove stale-tab 409 in tabB.
      const tabB = await context.newPage();
      await tabB.goto(`${uiBase}/documents/${SEED1_WO_DOC_ID}/review`, { waitUntil: 'networkidle' });
      await waitForExactText(tabB.getByTestId('current-revision-number'), '#2');

      await tabA.getByTestId('btn-edit-building_unit').click();
      await tabA.getByTestId('input-value-building_unit').fill('Bldg B - Unit 204 (Field Confirmed)');
      await tabA.getByTestId('btn-unreviewed-requested_date').click();
      await tabA.getByTestId('input-operator-label').fill('Reviewer Post-Review Draft');
      await tabA.getByTestId('save-draft').click();

      await waitForExactText(tabA.getByTestId('review-status-badge'), 'Saved draft (Revision #3)');
      assert(
        (await tabA.getByTestId('prior-reviewed-historical-warning').count()) === 1,
        'Expected prior-reviewed-historical-warning banner when head #3 is draft after reviewed #2',
      );

      // Reopen historical Revision #2 and confirm immutable unknown decision + reason + machine candidate.
      await tabA.getByTestId('view-revision-2').click();
      await waitForTextContains(tabA.getByTestId('historical-revision-banner'), 'Revision #2 (reviewed)');
      await waitForExactText(tabA.getByTestId('historical-decision-building_unit'), 'unknown');
      await waitForExactText(
        tabA.getByTestId('historical-reason-building_unit'),
        'Door unit plate unreadable on scan; field check required',
      );
      await tabA.getByTestId('return-to-current-head').click();
      await waitForExactText(tabA.getByTestId('review-status-badge'), 'Saved draft (Revision #3)');

      // Stale tabB (expectedRevision=2) edits property_name and attempts save -> 409 stale_expected_revision preserving unsaved memory!
      await tabB.getByTestId('btn-edit-property_name').click();
      await tabB.getByTestId('input-value-property_name').fill('Stale Tab Unsaved Property Edit');
      await tabB.getByTestId('save-draft').click();
      await waitForExactText(tabB.getByTestId('conflict-current-revision'), '#3');
      const preservedStaleValue = await tabB.getByTestId('input-value-property_name').inputValue();
      assert(
        preservedStaleValue === 'Stale Tab Unsaved Property Edit',
        `Expected stale unsaved edit preserved, got '${preservedStaleValue}'`,
      );
      assertZeroStorage(await readStorageState(tabB), 'stale-tab-409');
      await tabB.getByTestId('reload-discard-stale').click();
      await waitForExactText(tabB.getByTestId('current-revision-number'), '#3');
      await tabB.close();

      // 7. Uncertain 500 after real server commit of Revision #4 (reviewed · 1 unknown on requested_date) + same-key retry!
      const seenKeys = [];
      let inject500Once = true;
      await tabA.route(`**/api/documents/${SEED1_WO_DOC_ID}/review/revisions`, async (route) => {
        if (route.request().method() !== 'POST') {
          return route.fallback();
        }
        const key = route.request().headers()['idempotency-key'];
        seenKeys.push(key);
        if (inject500Once) {
          inject500Once = false;
          const realResp = await route.fetch();
          assert(realResp.status() === 201, `Expected real server 201 on uncertain test, got ${realResp.status()}`);
          return route.fulfill({
            status: 500,
            contentType: 'application/problem+json',
            body: JSON.stringify({ title: 'Simulated post-commit gateway error', status: 500 }),
          });
        }
        return route.fallback();
      });

      await tabA.getByTestId('btn-unknown-requested_date').click();
      await tabA
        .getByTestId('input-unknown-reason-requested_date')
        .fill('Printed request date smudged on carbon copy; awaiting dispatch log');
      await tabA.getByTestId('input-operator-label').fill('Reviewer Final Sign-off');
      await waitForTextContains(tabA.getByTestId('unknown-fields-list'), 'Fields marked unknown (1): Requested Date');
      await waitForEnabled(tabA.getByTestId('confirm-reviewed-checkbox'), 'confirm-reviewed-checkbox on Rev 4');
      await tabA.getByTestId('confirm-reviewed-checkbox').check();
      await waitForEnabled(tabA.getByTestId('save-reviewed'), 'save-reviewed on Rev 4');
      await tabA.getByTestId('save-reviewed').click();

      await waitForExactText(tabA.getByTestId('review-status-badge'), 'Save outcome uncertain');
      const displayedPendingKey = ((await tabA.getByTestId('pending-review-key').textContent()) ?? '').trim();
      assert(displayedPendingKey === seenKeys[0], 'Displayed pending Idempotency-Key disagrees with sent header');
      assertZeroStorage(await readStorageState(tabA), 'during-uncertain-500');

      await tabA.getByTestId('retry-uncertain-save').click();
      await waitForExactText(tabA.getByTestId('review-status-badge'), 'Reviewed (Revision #4 · 1 unknown)');
      await waitForExactText(tabA.getByTestId('current-revision-number'), '#4');
      assert(seenKeys.length === 2 && seenKeys[0] === seenKeys[1], `Expected exact same-key retry, got ${JSON.stringify(seenKeys)}`);
      await tabA.unroute(`**/api/documents/${SEED1_WO_DOC_ID}/review/revisions`);
      assertZeroStorage(await readStorageState(tabA), 'after-uncertain-retry-rev4');

      await tabA.evaluate(() => window.scrollTo(0, 0));
      await tabA.waitForTimeout(1500);
      const shot03Path = path.join(screenshotsDir, '03-reviewer-wo01-rev4-before-restart.png');
      await tabA.screenshot({ path: shot03Path });
      const shot03 = recordScreenshot(shot03Path);

      // Fetch exact API review payload on Seed 1 to record Revision 1..4 UUIDs and field snapshot before restart.
      const seed1ReviewJson = await tabA.evaluate(async (docId) => {
        const resp = await fetch(`/api/documents/${docId}/review`);
        return await resp.json();
      }, SEED1_WO_DOC_ID);
      assert(seed1ReviewJson.currentRevisionNumber === 4, 'Expected Seed 1 currentRevisionNumber === 4');
      assert(seed1ReviewJson.history.length === 4, 'Expected 4 history entries on Seed 1');

      // 8. Open Seed 2 (3-page SYN-MP-01 invoice): verify 5 missing candidates, #page=1..3 navigation, screenshots, and fallback download.
      await tabA.goto(`${uiBase}/documents/${SEED2_MP_DOC_ID}/review`, { waitUntil: 'networkidle' });
      await waitForTextContains(tabA.getByTestId('pdf-current-page'), 'Page 1 of 3');
      for (const fk of [
        'work_order_id',
        'property_name',
        'building_unit',
        'requested_date',
        'issue_and_resolution',
      ]) {
        await waitForTextContains(tabA.getByTestId(`machine-value-${fk}`), 'No suggestion (missing)');
        await waitForDisabled(tabA.getByTestId(`btn-accept-${fk}`), `btn-accept-${fk} on missing`);
      }

      await tabA.getByTestId('pdf-page-btn-2').click();
      await waitForTextContains(tabA.getByTestId('pdf-current-page'), 'Page 2 of 3');
      await waitForAttr(tabA.getByTestId('pdf-preview-frame'), 'src', `/api/documents/${SEED2_MP_DOC_ID}/preview#page=2`);
      await tabA.waitForTimeout(2000);
      const shot04Path = path.join(screenshotsDir, '04-reviewer-mp01-page2-navigation.png');
      await tabA.screenshot({ path: shot04Path });
      const shot04 = recordScreenshot(shot04Path);

      await tabA.getByTestId('pdf-page-btn-3').click();
      await waitForTextContains(tabA.getByTestId('pdf-current-page'), 'Page 3 of 3');
      await waitForAttr(tabA.getByTestId('pdf-preview-frame'), 'src', `/api/documents/${SEED2_MP_DOC_ID}/preview#page=3`);
      await tabA.waitForTimeout(2000);
      const shot05Path = path.join(screenshotsDir, '05-reviewer-mp01-page3-navigation.png');
      await tabA.screenshot({ path: shot05Path });
      const shot05 = recordScreenshot(shot05Path);

      const mpDlPromise = tabA.waitForEvent('download');
      await tabA.getByTestId('pdf-download-fallback').click();
      const mpDl = await mpDlPromise;
      const mpDlBytes = readFileSync(await mpDl.path());
      assert(Buffer.compare(mpDlBytes, mpPdfBytes) === 0, 'Seed 2 fallback download bytes disagreed with SYN-MP-01');

      // 9. Open Seed 4 (F1-SWO-001 awaiting_extraction): verify clean 409 error panel in UI.
      await tabA.goto(`${uiBase}/documents/${SEED4_F1_DOC_ID}/review`, { waitUntil: 'networkidle' });
      await waitForTextContains(tabA.getByTestId('review-load-error'), 'completed local extraction result');

      const receipt = {
        phase: 'before-restart',
        browserVersion,
        seed1DocumentId: SEED1_WO_DOC_ID,
        seed1ResultId: SEED1_WO_RESULT_ID,
        seed1CurrentRevisionNumber: seed1ReviewJson.currentRevisionNumber,
        seed1CurrentRevisionId: seed1ReviewJson.currentRevision.revisionId,
        seed1RequestSha256: seed1ReviewJson.currentRevision.requestSha256,
        seed1History: seed1ReviewJson.history,
        seed1Fields: seed1ReviewJson.fields,
        uncertainRetryIdempotencyKey: seenKeys[0],
        uncertainRetryKeyCount: seenKeys.length,
        staleConflictPreservedEditVerified: true,
        zeroPersistentBrowserStorageVerified: true,
        seed2ThreePageNavigationVerified: true,
        seed2DownloadSha256: sha256Hex(mpDlBytes),
        seed4NonCompletedRejectedInUi: true,
        screenshots: [shot01, shot02, shot03, shot04, shot05],
      };
      writeFileSync(cfg.receiptPath, JSON.stringify(receipt, null, 2));
      console.log(JSON.stringify({ ok: true, phase, browserVersion, rev4Id: receipt.seed1CurrentRevisionId }));
    } else if (phase === 'after-restart') {
      const beforeReceipt = JSON.parse(readFileSync(cfg.beforeReceiptPath, 'utf8'));

      // 1. Open Seed 1 review in fresh Edge process after PostgreSQL + API + UI restart (LocalOcr:Enabled=false).
      await tabA.goto(`${uiBase}/documents/${SEED1_WO_DOC_ID}/review`, { waitUntil: 'networkidle' });
      await waitForExactText(tabA.getByTestId('review-status-badge'), 'Reviewed (Revision #4 · 1 unknown)');
      await waitForExactText(tabA.getByTestId('current-revision-number'), '#4');
      await waitForExactText(tabA.getByTestId('review-result-id'), SEED1_WO_RESULT_ID);
      await waitForExactText(tabA.getByTestId('review-raw-sha256'), SEED1_WO_RAW_SHA);
      await waitForExactText(tabA.getByTestId('review-original-sha256'), SEED1_WO_PDF_SHA);

      assert(
        (await tabA.getByTestId('input-value-property_name').inputValue()) ===
          'Cedar Hollow Apartments — Reviewer Verified North',
        'Property value mismatch after PG+API restart',
      );
      assert(
        (await tabA.getByTestId('input-value-building_unit').inputValue()) === 'Bldg B - Unit 204 (Field Confirmed)',
        'Building/Unit value mismatch after PG+API restart',
      );
      assert(
        (await tabA.getByTestId('input-unknown-reason-requested_date').inputValue()) ===
          'Printed request date smudged on carbon copy; awaiting dispatch log',
        'Unknown reason mismatch after PG+API restart',
      );
      assert(
        (await tabA.getByTestId('input-operator-label').inputValue()) === 'Reviewer Final Sign-off',
        'Operator display label mismatch after PG+API restart',
      );
      assertZeroStorage(await readStorageState(tabA), 'after-pg-api-restart');

      await tabA.waitForTimeout(2500);
      const shot06Path = path.join(screenshotsDir, '06-reviewer-wo01-rev4-after-pg-api-restart.png');
      await tabA.screenshot({ path: shot06Path });
      const shot06 = recordScreenshot(shot06Path);

      // 2. Verify historical Revision #2 survived restart identically.
      await tabA.getByTestId('view-revision-2').click();
      await waitForTextContains(tabA.getByTestId('historical-revision-banner'), 'Revision #2 (reviewed)');
      await waitForExactText(tabA.getByTestId('historical-decision-building_unit'), 'unknown');
      await waitForExactText(
        tabA.getByTestId('historical-reason-building_unit'),
        'Door unit plate unreadable on scan; field check required',
      );
      await tabA.getByTestId('return-to-current-head').click();
      await waitForExactText(tabA.getByTestId('current-revision-number'), '#4');

      // 3. Download original PDF after restart and confirm byte-exact 372,258 B.
      const woDlPromise = tabA.waitForEvent('download');
      await tabA.getByTestId('pdf-download-fallback').click();
      const woDl = await woDlPromise;
      const woDlBytes = readFileSync(await woDl.path());
      assert(Buffer.compare(woDlBytes, woPdfBytes) === 0, 'Seed 1 original download mismatch after PG+API restart');

      // 4. Compare full API JSON state before vs after restart and verify attempt count remained 1.
      const afterReviewJson = await tabA.evaluate(async (docId) => {
        const resp = await fetch(`/api/documents/${docId}/review`);
        return await resp.json();
      }, SEED1_WO_DOC_ID);

      assert(
        afterReviewJson.currentRevision.revisionId === beforeReceipt.seed1CurrentRevisionId &&
          afterReviewJson.currentRevision.requestSha256 === beforeReceipt.seed1RequestSha256 &&
          JSON.stringify(afterReviewJson.history) === JSON.stringify(beforeReceipt.seed1History) &&
          JSON.stringify(afterReviewJson.fields) === JSON.stringify(beforeReceipt.seed1Fields),
        'Post-restart review JSON disagreed with pre-restart committed state',
      );

      await tabA.goto(`${uiBase}/documents/${SEED1_WO_DOC_ID}`, { waitUntil: 'networkidle' });
      await waitForExactText(tabA.getByTestId('document-status'), 'Completed (unreviewed)');
      await waitForTextContains(tabA.getByTestId('document-review-status'), 'Reviewed (Revision #4 · 1 unknown)');
      assert((await tabA.getByTestId('attempt-row-1').count()) === 1, 'Expected 1 extraction attempt after restart');
      assert((await tabA.getByTestId('attempt-row-2').count()) === 0, 'Expected zero new extraction attempts after restart');

      const afterReceipt = {
        phase: 'after-restart',
        browserVersion,
        seed1DocumentId: SEED1_WO_DOC_ID,
        seed1CurrentRevisionId: afterReviewJson.currentRevision.revisionId,
        exactMatchWithBeforeRestart: true,
        historicalRevision2VerifiedAfterRestart: true,
        seed1OriginalDownloadSha256: sha256Hex(woDlBytes),
        zeroExtraExtractionAttemptsVerified: true,
        screenshots: [shot06],
      };
      writeFileSync(cfg.receiptPath, JSON.stringify(afterReceipt, null, 2));
      console.log(JSON.stringify({ ok: true, phase, browserVersion, rev4Id: afterReceipt.seed1CurrentRevisionId }));
    } else {
      throw new Error(`Unknown phase: ${phase}`);
    }
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
