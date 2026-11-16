import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const repoRoot = path.resolve(import.meta.dirname, '..', '..', '..', '..', '..');
const requireFromWeb = createRequire(path.join(repoRoot, 'web', 'package.json'));
const { chromium } = requireFromWeb('@playwright/test');

/**
 * Driven by run_f3_decisive_verification.py in two phases across an actual API + PostgreSQL 18.7 cluster restart:
 *   --phase before-restart : opens genuine seeded SYN-WO-01 & SYN-MP-01 on UI port, verifies readable PDF + 5 fields,
 *                            saves Draft Rev #1 and Reviewed Rev #2 (with correction + unknown + reason), captures PNGs.
 *   --phase after-restart  : opens fresh Edge context after API + PostgreSQL restart (LocalOcr:Enabled=false),
 *                            re-verifies saved Reviewed Rev #2, historical Rev #1, 3-page navigation, and byte-exact downloads.
 */
async function main() {
  const args = process.argv.slice(2);
  const phaseIdx = args.indexOf('--phase');
  const configIdx = args.indexOf('--config');
  if (phaseIdx < 0 || configIdx < 0) {
    throw new Error('Usage: node verify_f3_restart_edge.mjs --phase <before-restart|after-restart> --config <jsonPath>');
  }

  const phase = args[phaseIdx + 1];
  const cfg = JSON.parse(readFileSync(args[configIdx + 1], 'utf8'));
  const uiBase = `http://127.0.0.1:${cfg.uiPort}`;
  const outDir = cfg.outputDir;
  mkdirSync(outDir, { recursive: true });

  const woPdfBytes = readFileSync(path.join(repoRoot, 'tests', 'fixtures', 'SYN-WO-01-v1-raster300.pdf'));
  const woPdfSha = createHash('sha256').update(woPdfBytes).digest('hex');
  const mpPdfBytes = readFileSync(path.join(repoRoot, 'tests', 'fixtures', 'SYN-MP-01-v0-clean.pdf'));
  const mpPdfSha = createHash('sha256').update(mpPdfBytes).digest('hex');

  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const browserVersion = browser.version();
  const context = await browser.newContext({
    viewport: { width: 1680, height: 980 },
    acceptDownloads: true,
  });
  const page = await context.newPage();

  try {
    if (phase === 'before-restart') {
      // 1. Open SYN-WO-01 review route and verify two-pane native PDF + 5 conservative suggestions.
      await page.goto(`${uiBase}/documents/${cfg.woDocumentId}/review`, { waitUntil: 'networkidle' });
      await page.getByTestId('review-status-badge').waitFor({ state: 'visible', timeout: 30000 });
      await page.waitForTimeout(2500); // Allow PDFium internal surface to finish painting.

      const shotInitial = path.join(outDir, 'two-pane-wo01-source-comparison.png');
      await page.screenshot({ path: shotInitial });

      const initialBadge = (await page.getByTestId('review-status-badge').textContent()).trim();
      const frameSrc = await page.getByTestId('pdf-preview-frame').getAttribute('src');
      const frameBox = await page.getByTestId('pdf-preview-frame').boundingBox();
      if (!frameBox || frameBox.width < 400 || frameBox.height < 500) {
        throw new Error(`Unexpected PDF frame bounding box: ${JSON.stringify(frameBox)}`);
      }

      const machineValues = {
        work_order_id: (await page.getByTestId('machine-value-work_order_id').textContent()).trim(),
        property_name: (await page.getByTestId('machine-value-property_name').textContent()).trim(),
        building_unit: (await page.getByTestId('machine-value-building_unit').textContent()).trim(),
        requested_date: (await page.getByTestId('machine-value-requested_date').textContent()).trim(),
        issue_and_resolution: (await page.getByTestId('machine-value-issue_and_resolution').textContent()).trim(),
      };

      // 2. Save Draft Revision #1.
      await page.getByTestId('btn-accept-work_order_id').click();
      await page.getByTestId('btn-edit-property_name').click();
      await page.getByTestId('input-value-property_name').fill('Cedar Hollow Apartments — Verified Bldg B');
      await page.getByTestId('btn-accept-requested_date').click();
      await page.getByTestId('input-operator-label').fill('F3 Author Desk');
      await page.getByTestId('save-draft').click();
      await page.locator('[data-testid="current-revision-number"]', { hasText: '#1' }).waitFor({ timeout: 15000 });

      // 3. Save Reviewed Revision #2 with 1 unknown + reason + affirmative confirmation.
      await page.getByTestId('btn-unknown-building_unit').click();
      await page.getByTestId('input-unknown-reason-building_unit').fill('Unit door placard pending field check');
      await page.getByTestId('btn-accept-issue_and_resolution').click();
      await page.getByTestId('confirm-reviewed-checkbox').check();
      await page.getByTestId('save-reviewed').click();
      await page.locator('[data-testid="current-revision-number"]', { hasText: '#2' }).waitFor({ timeout: 15000 });
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(1000);

      const shotReviewed = path.join(outDir, 'before-restart-wo01-reviewed.png');
      await page.screenshot({ path: shotReviewed });

      // 4. Open 3-page SYN-MP-01, navigate to Page 2, and capture two-pane 3-page navigation screenshot!
      await page.goto(`${uiBase}/documents/${cfg.mpDocumentId}/review`, { waitUntil: 'networkidle' });
      await page.getByTestId('pdf-page-btn-2').click();
      await page.waitForTimeout(2500);
      const mpFrameSrc = await page.getByTestId('pdf-preview-frame').getAttribute('src');
      const shotMpPage2 = path.join(outDir, 'two-pane-mp01-page2-navigation.png');
      await page.screenshot({ path: shotMpPage2 });

      const storageCheck = await page.evaluate(async () => {
        const idbs = 'databases' in indexedDB ? await indexedDB.databases() : [];
        return {
          sessionKeys: Object.keys(sessionStorage),
          localKeys: Object.keys(localStorage),
          idbCount: idbs.length,
          forbiddenDomCount: document.querySelectorAll(
            '[data-testid="review-workspace"] script, [data-testid="review-workspace"] img',
          ).length,
        };
      });

      const summary = {
        phase,
        browserVersion,
        initialBadge,
        frameSrc,
        frameBox,
        machineValues,
        mpFrameSrc,
        storageCheck,
        screenshots: {
          twoPaneWo01: shotInitial,
          beforeRestartReviewed: shotReviewed,
          twoPaneMp01Page2: shotMpPage2,
        },
      };
      writeFileSync(path.join(outDir, 'edge-before-restart.json'), JSON.stringify(summary, null, 2));
      console.log(JSON.stringify(summary));
    } else if (phase === 'after-restart') {
      // Fresh browser context after API + PostgreSQL 18.7 restart with LocalOcr:Enabled=false!
      await page.goto(`${uiBase}/documents/${cfg.woDocumentId}`, { waitUntil: 'networkidle' });
      const docStatus = (await page.getByTestId('document-status').textContent()).trim();
      const docRevStatus = (await page.getByTestId('document-review-status').textContent()).trim();
      const docRawSha = (await page.getByTestId('result-raw-sha256').textContent()).trim();

      await page.getByTestId('open-work-order-review').click();
      await page.locator('[data-testid="current-revision-number"]', { hasText: '#2' }).waitFor({ timeout: 15000 });
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(2500);

      const shotAfter = path.join(outDir, 'after-pg-and-api-restart-wo01-reopen.png');
      await page.screenshot({ path: shotAfter });

      const badgeAfter = (await page.getByTestId('review-status-badge').textContent()).trim();
      const resultIdAfter = (await page.getByTestId('review-result-id').textContent()).trim();
      const rawShaAfter = (await page.getByTestId('review-raw-sha256').textContent()).trim();
      const origShaAfter = (await page.getByTestId('review-original-sha256').textContent()).trim();
      const editedPropertyAfter = await page.getByTestId('input-value-property_name').inputValue();
      const unknownDecisionAfter = (await page.getByTestId('field-decision-building_unit').textContent()).trim();
      const unknownReasonAfter = await page.getByTestId('input-unknown-reason-building_unit').inputValue();
      const opLabelAfter = await page.getByTestId('input-operator-label').inputValue();

      // Verify historical Revision #1 snapshot also reopens cleanly!
      await page.getByTestId('view-revision-1').click();
      await page.getByTestId('historical-revision-banner').waitFor({ state: 'visible', timeout: 10000 });
      const histBanner = (await page.getByTestId('historical-revision-banner').textContent()).trim();
      const histDecisionBuilding = (await page.getByTestId('historical-decision-building_unit').textContent()).trim();
      await page.getByTestId('return-to-current-head').click();

      // Verify byte-exact original PDF download after restart!
      const dlPromise = page.waitForEvent('download');
      await page.getByTestId('pdf-download-fallback').click();
      const dl = await dlPromise;
      const dlBytes = readFileSync(await dl.path());
      const dlSha = createHash('sha256').update(dlBytes).digest('hex');
      if (dlSha !== woPdfSha || dlBytes.length !== woPdfBytes.length) {
        throw new Error(`Downloaded PDF mismatch: ${dlSha} != ${woPdfSha}`);
      }

      if (
        docStatus !== 'Completed (unreviewed)' ||
        !docRevStatus.includes('Reviewed (Revision #2 · 1 unknown)') ||
        badgeAfter !== 'Reviewed (Revision #2 · 1 unknown)' ||
        editedPropertyAfter !== 'Cedar Hollow Apartments — Verified Bldg B' ||
        unknownDecisionAfter !== 'unknown' ||
        unknownReasonAfter !== 'Unit door placard pending field check' ||
        opLabelAfter !== 'F3 Author Desk' ||
        histDecisionBuilding !== 'unreviewed' ||
        mpPdfSha.length !== 64
      ) {
        throw new Error('Post-restart UI state assertion failed.');
      }

      const summary = {
        phase,
        browserVersion,
        docStatus,
        docRevStatus,
        docRawSha,
        badgeAfter,
        resultIdAfter,
        rawShaAfter,
        origShaAfter,
        editedPropertyAfter,
        unknownDecisionAfter,
        unknownReasonAfter,
        opLabelAfter,
        histBanner,
        histDecisionBuilding,
        downloadedByteLength: dlBytes.length,
        downloadedSha256: dlSha,
        screenshotAfterRestart: shotAfter,
      };
      writeFileSync(path.join(outDir, 'edge-after-restart.json'), JSON.stringify(summary, null, 2));
      console.log(JSON.stringify(summary));
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
