import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';

const repoRoot = path.resolve(import.meta.dirname, '..', '..', '..', '..', '..', '..');
const requireFromWeb = createRequire(path.join(repoRoot, 'web', 'package.json'));
const { chromium } = requireFromWeb('@playwright/test');

/**
 * Read-only headless Microsoft Edge smoke check against the retained WP-0010 F4 author seed DB
 * (`eledgercare_f4_author_seed_f3`) through owned Angular dev UI (`127.0.0.1:4610`) and owned
 * unchanged F3 API (`127.0.0.1:5590`, `LocalOcr:Enabled=false`). Performs zero writes/mutations.
 */
async function main() {
  const args = process.argv.slice(2);
  const cfgIdx = args.indexOf('--config');
  if (cfgIdx < 0 || !args[cfgIdx + 1]) {
    throw new Error('Usage: node verify_f3_seed_ui_edge.mjs --config <jsonPath>');
  }

  const cfg = JSON.parse(readFileSync(args[cfgIdx + 1], 'utf8'));
  const uiBase = `http://127.0.0.1:${cfg.uiPort}`;

  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const browserVersion = browser.version();
  const context = await browser.newContext({
    viewport: { width: 1680, height: 980 },
    acceptDownloads: true,
  });
  const page = await context.newPage();
  const pageDialogs = [];
  page.on('dialog', async (d) => {
    pageDialogs.push(d.message());
    await d.dismiss();
  });

  try {
    // 1. Seed 1 head (/review): Current head #3 is unapproved draft with prior reviewed warning banner.
    await page.goto(`${uiBase}/documents/${cfg.seed1DocumentId}/review`, { waitUntil: 'networkidle' });
    await page.getByTestId('review-status-badge').waitFor({ state: 'visible', timeout: 30000 });
    await page.waitForTimeout(1500);

    const seed1HeadRevText = (await page.getByTestId('current-revision-number').textContent()).trim();
    const seed1HeadBadge = (await page.getByTestId('review-status-badge').textContent()).trim();
    const priorReviewedWarningVisible = await page.getByTestId('prior-reviewed-historical-warning').isVisible();
    const priorReviewedWarningText = priorReviewedWarningVisible
      ? (await page.getByTestId('prior-reviewed-historical-warning').textContent()).replace(/\s+/g, ' ').trim()
      : '';
    const frameBox1 = await page.getByTestId('pdf-preview-frame').boundingBox();
    if (!frameBox1 || frameBox1.width < 400 || frameBox1.height < 500) {
      throw new Error(`Unexpected PDF frame bounding box on Seed 1: ${JSON.stringify(frameBox1)}`);
    }

    // 2. Seed 1 historical Rev #2 (/review/revisions/2): immutable greatest reviewed revision & inert <script> text.
    await page.goto(`${uiBase}/documents/${cfg.seed1DocumentId}/review/revisions/2`, { waitUntil: 'networkidle' });
    await page.getByTestId('historical-revision-banner').waitFor({ state: 'visible', timeout: 30000 });

    const histBannerText = (await page.getByTestId('historical-revision-banner').textContent()).replace(/\s+/g, ' ').trim();
    const rev2PropVal = (await page.getByTestId('historical-value-property_name').textContent()).trim();
    const rev2UnitDec = (await page.getByTestId('historical-decision-building_unit').textContent()).trim();
    const rev2IssueVal = (await page.getByTestId('historical-value-issue_and_resolution').textContent()).trim();
    const injectedScriptsInFieldsPane = await page.getByTestId('fields-review-pane').locator('script').count();

    if (!rev2PropVal.includes('REV2-ACTIVE-HAWTHORNE')) {
      throw new Error(`Expected REV2-ACTIVE-HAWTHORNE in Rev #2 property_name, got: ${rev2PropVal}`);
    }
    if (rev2UnitDec !== 'unknown') {
      throw new Error(`Expected Rev #2 building_unit decision 'unknown', got: ${rev2UnitDec}`);
    }
    if (!rev2IssueVal.includes('MANUAL-NO-PROVENANCE-KESTREL-0042') || !rev2IssueVal.includes("<script>alert('inert')</script>")) {
      throw new Error(`Unexpected Rev #2 issue_and_resolution text: ${rev2IssueVal}`);
    }
    if (injectedScriptsInFieldsPane !== 0 || pageDialogs.length !== 0) {
      throw new Error(`Inertness check failed: scripts=${injectedScriptsInFieldsPane}, dialogs=${pageDialogs.length}`);
    }

    // 3. Seed 5 multipage reviewed head (/review): 3-page PDF navigation to Page 2.
    await page.goto(`${uiBase}/documents/${cfg.seed5DocumentId}/review`, { waitUntil: 'networkidle' });
    await page.getByTestId('review-status-badge').waitFor({ state: 'visible', timeout: 30000 });
    await page.getByTestId('pdf-page-btn-2').click();
    await page.waitForTimeout(1000);

    const seed5PageLabel = (await page.getByTestId('pdf-current-page').textContent()).replace(/\s+/g, ' ').trim();
    const seed5FrameSrc = await page.getByTestId('pdf-preview-frame').getAttribute('src');
    if (!seed5PageLabel.includes('Page 2 of 3') || !seed5FrameSrc || !seed5FrameSrc.includes('#page=2')) {
      throw new Error(`Seed 5 Page 2 navigation failed: label='${seed5PageLabel}', src='${seed5FrameSrc}'`);
    }

    const result = {
      ok: true,
      browserChannel: 'msedge',
      browserVersion,
      uiPort: cfg.uiPort,
      seed1Head: {
        documentId: cfg.seed1DocumentId,
        currentRevisionLabel: seed1HeadRevText,
        statusBadge: seed1HeadBadge,
        priorReviewedWarningVisible,
        priorReviewedWarningText,
        pdfFrameBoundingBox: frameBox1,
      },
      seed1HistoricalRev2: {
        bannerText: histBannerText,
        propertyValue: rev2PropVal,
        buildingUnitDecision: rev2UnitDec,
        issueContainsKestrel0042: rev2IssueVal.includes('MANUAL-NO-PROVENANCE-KESTREL-0042'),
        issueContainsSurrogateWrench: rev2IssueVal.includes('\u{1F527}'),
        issueContainsLiteralScriptText: rev2IssueVal.includes("<script>alert('inert')</script>"),
        injectedScriptElements: injectedScriptsInFieldsPane,
        dialogsTriggered: pageDialogs.length,
      },
      seed5MultipageReview: {
        documentId: cfg.seed5DocumentId,
        pageLabelAfterClick2: seed5PageLabel,
        iframeSrcContainsPage2: seed5FrameSrc.includes('#page=2'),
      },
    };

    mkdirSync(path.dirname(cfg.outputJsonPath), { recursive: true });
    writeFileSync(cfg.outputJsonPath, JSON.stringify(result, null, 2).replace(/\r\n/g, '\n') + '\n', 'utf8');
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
