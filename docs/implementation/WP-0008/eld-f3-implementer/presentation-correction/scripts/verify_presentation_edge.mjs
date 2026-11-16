import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const repoRoot = path.resolve(import.meta.dirname, '..', '..', '..', '..', '..', '..');
const requireFromWeb = createRequire(path.join(repoRoot, 'web', 'package.json'));
const { chromium } = requireFromWeb('@playwright/test');

/**
 * Presentation-correction browser verifier (WP-0008 / 006) executed against retained
 * eledgercare_f3_author_acceptance with LocalOcr:Enabled=false and zero DB mutations:
 *   1. Opens saved SYN-WO-01 (Reviewed Rev #2 + historical Rev #1) in Microsoft Edge:
 *      - Verifies default operator flow hides all internal schema/field IDs, result UUID,
 *        and full SHA-256 digests inside closed <details> while keeping plain headings,
 *        character limits, source quotes, page navigation, and review controls visible.
 *      - Captures 01-default-operator-flow-wo01.png.
 *      - Expands Provenance & technical details, verifies exact identifiers/hashes,
 *        and captures 02-expanded-provenance-wo01.png.
 *      - Verifies historical Revision #1 snapshot uses plain labels without internal keys.
 *   2. Intercepts save POST locally with connectionreset (before forwarding to API so the
 *      retained database stays 100% untouched):
 *      - Verifies unsaved-edits-warning appears on edit.
 *      - Verifies uncertain-save-banner explains recovery via "Retry pending save" while
 *        keeping the operation UUID inside closed Technical save details.
 *      - Captures 03-uncertain-save-default.png and 04-uncertain-save-expanded-details.png.
 *   3. Opens saved 3-page SYN-MP-01, navigates to Page 2, verifies plain default flow,
 *      captures 05-default-operator-flow-mp01-page2.png, and verifies byte-exact download.
 */
async function main() {
  const args = process.argv.slice(2);
  const configIdx = args.indexOf('--config');
  if (configIdx < 0) {
    throw new Error('Usage: node verify_presentation_edge.mjs --config <jsonPath>');
  }

  const cfg = JSON.parse(readFileSync(args[configIdx + 1], 'utf8'));
  const uiBase = `http://127.0.0.1:${cfg.uiPort}`;
  const outDir = cfg.outputDir;
  mkdirSync(outDir, { recursive: true });

  const woPdfBytes = readFileSync(path.join(repoRoot, 'tests', 'fixtures', 'SYN-WO-01-v1-raster300.pdf'));
  const woPdfSha = createHash('sha256').update(woPdfBytes).digest('hex');
  const woRawSha = '7503761ae46afef6adf579881d011764283474354fac3e185598fc7d266aff95';
  const woResultId = '01a1e573-a855-7735-96e1-f5d14cada602';

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
    // 1. Saved SYN-WO-01 default operator flow (closed provenance details).
    await page.goto(`${uiBase}/documents/${cfg.woDocumentId}/review`, { waitUntil: 'networkidle' });
    await page.getByTestId('review-status-badge').waitFor({ state: 'visible', timeout: 30000 });
    await page.waitForTimeout(2500); // Allow Edge native PDFium surface to paint.

    const badge = (await page.getByTestId('review-status-badge').textContent()).trim();
    if (badge !== 'Reviewed (Revision #2 · 1 unknown)') {
      throw new Error(`Expected saved 'Reviewed (Revision #2 · 1 unknown)', got '${badge}'`);
    }

    const detailsOpenInitially = await page
      .getByTestId('review-provenance-details')
      .evaluate((el) => el.hasAttribute('open'));
    if (detailsOpenInitially) {
      throw new Error('review-provenance-details must be closed initially.');
    }

    const defaultVisibleText = await page.getByTestId('review-workspace').innerText();
    const forbiddenInDefault = [
      'maintenance-work-order/1',
      'maintenance-work-order-fields/1',
      'work-order-suggestions/1',
      'work_order_id',
      'property_name',
      'building_unit',
      'requested_date',
      'issue_and_resolution',
      'UTF-16 code units',
      woResultId,
      woPdfSha,
      woRawSha,
    ];
    for (const tok of forbiddenInDefault) {
      if (defaultVisibleText.includes(tok)) {
        throw new Error(`Internal token leaked into default operator flow: '${tok}'`);
      }
    }

    const requiredInDefault = [
      'Work-order review & source comparison',
      'Five work-order fields',
      'Work Order ID',
      'Property',
      'Building / Unit',
      'Requested / Service Date',
      'Reported Issue & Work Performed',
      'max 64 characters',
      'max 4000 characters',
      'Source quote (Page 1): WO-004192',
      'Provenance & technical details',
    ];
    for (const tok of requiredInDefault) {
      if (!defaultVisibleText.includes(tok)) {
        throw new Error(`Expected operator text missing from default flow: '${tok}'`);
      }
    }

    const shotDefaultWo = path.join(outDir, '01-default-operator-flow-wo01.png');
    await page.screenshot({ path: shotDefaultWo });

    // 2. Expand Provenance & technical details and verify exact values.
    await page.getByTestId('toggle-review-provenance').click();
    await page.getByTestId('review-profile-id').waitFor({ state: 'visible', timeout: 5000 });

    const expandedProvenance = {
      profileId: (await page.getByTestId('review-profile-id').textContent()).trim(),
      fieldSchema: (await page.getByTestId('review-field-schema').textContent()).trim(),
      suggestionPolicy: (await page.getByTestId('review-suggestion-policy').textContent()).trim(),
      documentId: (await page.getByTestId('review-document-id').textContent()).trim(),
      resultId: (await page.getByTestId('review-result-id').textContent()).trim(),
      originalSha256: (await page.getByTestId('review-original-sha256').textContent()).trim(),
      rawSha256: (await page.getByTestId('review-raw-sha256').textContent()).trim(),
      fieldKeys: {
        work_order_id: (await page.getByTestId('technical-field-key-work_order_id').textContent()).trim(),
        property_name: (await page.getByTestId('technical-field-key-property_name').textContent()).trim(),
        building_unit: (await page.getByTestId('technical-field-key-building_unit').textContent()).trim(),
        requested_date: (await page.getByTestId('technical-field-key-requested_date').textContent()).trim(),
        issue_and_resolution: (await page.getByTestId('technical-field-key-issue_and_resolution').textContent()).trim(),
      },
    };
    if (
      expandedProvenance.profileId !== 'maintenance-work-order/1' ||
      expandedProvenance.fieldSchema !== 'maintenance-work-order-fields/1' ||
      expandedProvenance.suggestionPolicy !== 'work-order-suggestions/1' ||
      expandedProvenance.documentId !== cfg.woDocumentId ||
      expandedProvenance.resultId !== woResultId ||
      expandedProvenance.originalSha256 !== woPdfSha ||
      expandedProvenance.rawSha256 !== woRawSha
    ) {
      throw new Error(`Expanded provenance mismatch: ${JSON.stringify(expandedProvenance)}`);
    }

    const shotExpandedWo = path.join(outDir, '02-expanded-provenance-wo01.png');
    await page.screenshot({ path: shotExpandedWo });

    // Collapse provenance back and check historical Revision #1 snapshot presentation.
    await page.getByTestId('toggle-review-provenance').click();
    await page.getByTestId('view-revision-1').click();
    await page.getByTestId('historical-revision-banner').waitFor({ state: 'visible', timeout: 10000 });
    const histVisibleText = await page.getByTestId('fields-review-pane').innerText();
    if (histVisibleText.includes('work_order_id') || histVisibleText.includes('Block 4')) {
      throw new Error('Historical snapshot leaked internal field key or block ordinal.');
    }
    await page.getByTestId('return-to-current-head').click();

    // 3. Demonstrate unsaved-edit warning & uncertain-save banner without mutating PostgreSQL!
    let interceptedKey = '';
    await page.route(`**/api/documents/${cfg.woDocumentId}/review/revisions`, async (route) => {
      if (route.request().method() === 'POST') {
        interceptedKey = route.request().headers()['idempotency-key'] ?? '';
        return route.abort('connectionreset');
      }
      return route.fallback();
    });

    await page.getByTestId('btn-edit-property_name').click();
    await page.getByTestId('input-value-property_name').fill('Cedar Hollow Apartments — Operator Check');
    await page.getByTestId('unsaved-edits-warning').waitFor({ state: 'visible', timeout: 5000 });

    await page.getByTestId('save-draft').click();
    await page.getByTestId('uncertain-save-banner').waitFor({ state: 'visible', timeout: 10000 });
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(500);

    const uncertainDetailsOpenInitially = await page
      .getByTestId('uncertain-save-details')
      .evaluate((el) => el.hasAttribute('open'));
    if (uncertainDetailsOpenInitially) {
      throw new Error('uncertain-save-details must be closed initially.');
    }

    const uncertainDefaultText = await page.getByTestId('uncertain-save-banner').innerText();
    if (!interceptedKey || uncertainDefaultText.includes(interceptedKey) || uncertainDefaultText.includes('Idempotency-Key')) {
      throw new Error(`Uncertain banner leaked operation key or header jargon: ${uncertainDefaultText}`);
    }
    if (!uncertainDefaultText.includes('Retry pending save')) {
      throw new Error(`Uncertain banner missing 'Retry pending save': ${uncertainDefaultText}`);
    }

    const shotUncertainDefault = path.join(outDir, '03-uncertain-save-default.png');
    await page.screenshot({ path: shotUncertainDefault });

    await page.getByTestId('toggle-uncertain-save-details').click();
    await page.getByTestId('pending-review-key').waitFor({ state: 'visible', timeout: 5000 });
    const shownKey = (await page.getByTestId('pending-review-key').textContent()).trim();
    if (shownKey !== interceptedKey) {
      throw new Error(`Expanded pending-review-key '${shownKey}' != intercepted '${interceptedKey}'`);
    }

    const shotUncertainExpanded = path.join(outDir, '04-uncertain-save-expanded-details.png');
    await page.screenshot({ path: shotUncertainExpanded });
    await page.unroute(`**/api/documents/${cfg.woDocumentId}/review/revisions`);

    // Handle unsaved-memory confirmation dialog when navigating to SYN-MP-01.
    page.once('dialog', (dlg) => dlg.accept());

    // 4. Open 3-page SYN-MP-01, navigate to Page 2, verify plain default flow & byte-exact download.
    await page.goto(`${uiBase}/documents/${cfg.mpDocumentId}/review`, { waitUntil: 'networkidle' });
    await page.getByTestId('pdf-page-btn-2').click();
    await page.waitForTimeout(2500);

    const mpDefaultText = await page.getByTestId('review-workspace').innerText();
    if (mpDefaultText.includes('maintenance-work-order/1') || mpDefaultText.includes('work_order_id') || mpDefaultText.includes(mpPdfSha)) {
      throw new Error('3-page review default flow leaked internal identifiers or PDF SHA-256.');
    }

    const shotMpPage2 = path.join(outDir, '05-default-operator-flow-mp01-page2.png');
    await page.screenshot({ path: shotMpPage2 });

    const dlPromise = page.waitForEvent('download');
    await page.getByTestId('pdf-download-fallback').click();
    const dl = await dlPromise;
    const dlBytes = readFileSync(await dl.path());
    const dlSha = createHash('sha256').update(dlBytes).digest('hex');
    if (dlSha !== mpPdfSha || dlBytes.length !== mpPdfBytes.length) {
      throw new Error(`MP PDF download mismatch: ${dlSha} != ${mpPdfSha}`);
    }

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
    if (
      storageCheck.sessionKeys.length !== 0 ||
      storageCheck.localKeys.length !== 0 ||
      storageCheck.idbCount !== 0 ||
      storageCheck.forbiddenDomCount !== 0
    ) {
      throw new Error(`Storage/DOM check failed: ${JSON.stringify(storageCheck)}`);
    }

    const receipt = {
      schema: 'eledgercare.wp-0008.f3-presentation-edge-receipt/1',
      browserVersion,
      woDocumentId: cfg.woDocumentId,
      mpDocumentId: cfg.mpDocumentId,
      defaultDetailsClosedInitially: !detailsOpenInitially,
      uncertainDetailsClosedInitially: !uncertainDetailsOpenInitially,
      forbiddenTokensAbsentFromDefaultFlow: forbiddenInDefault,
      requiredPlainControlsPresent: requiredInDefault,
      expandedProvenance,
      interceptedUncertainOperationKey: interceptedKey,
      mpDownloadedBytes: dlBytes.length,
      mpDownloadedSha256: dlSha,
      storageCheck,
      screenshots: {
        defaultOperatorFlowWo01: shotDefaultWo,
        expandedProvenanceWo01: shotExpandedWo,
        uncertainSaveDefault: shotUncertainDefault,
        uncertainSaveExpandedDetails: shotUncertainExpanded,
        defaultOperatorFlowMp01Page2: shotMpPage2,
      },
    };
    writeFileSync(path.join(outDir, 'edge-presentation-receipt.json'), JSON.stringify(receipt, null, 2));
    console.log(JSON.stringify(receipt));
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
