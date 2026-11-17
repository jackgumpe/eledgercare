import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';

const repoRoot = path.resolve(import.meta.dirname, '..', '..', '..', '..', '..');
const requireFromWeb = createRequire(path.join(repoRoot, 'web', 'package.json'));
const { chromium } = requireFromWeb('@playwright/test');

const SEED1_DOC = '01a1e571-2838-714b-861b-bf0835d7c90a';
const SEED2_DOC = '01a1e573-ca14-72ba-a46a-c84690288e22';
const SEED3_DOC = '01a1e578-8f3a-7e0c-826b-a2c9dc066a8f';
const SEED4_DOC = '01a1f400-0000-7000-8000-000000000401';
const SEED5_DOC = '01a1f400-0000-7000-8000-000000000501';
const SEED6_DOC = '01a1f400-0000-7000-8000-000000000601';
const SEED7_DOC = '01a1e8aa-cbe8-7306-a339-816fae2a05e0';

const EXPECTED_WO_PDF_SHA = '47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd';
const EXPECTED_MP_PDF_SHA = '15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3';
const EXPECTED_F1_PDF_SHA = '875a2d8ca1ba87db17a866898902116a9f6579bd6dc4c599850c34eb392526a0';

async function waitForCondition(fn, description, timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs;
  let lastErr = null;
  while (Date.now() < deadline) {
    try {
      const ok = await fn();
      if (ok) {
        return;
      }
    } catch (err) {
      lastErr = err;
    }
    await new Promise((r) => setTimeout(r, 150));
  }
  throw new Error(`Timed out waiting for condition: ${description}${lastErr ? ` (${lastErr})` : ''}`);
}

async function fetchJson(url) {
  const res = await fetch(url);
  const text = await res.text();
  return { status: res.status, body: text ? JSON.parse(text) : null };
}

async function fetchSha256(url) {
  const res = await fetch(url);
  if (res.status !== 200) {
    throw new Error(`Expected 200 for ${url}, got ${res.status}`);
  }
  const buf = Buffer.from(await res.arrayBuffer());
  return {
    bytes: buf.length,
    sha256: createHash('sha256').update(buf).digest('hex'),
  };
}

/**
 * Read-only headless Microsoft Edge verification against the forward-migrated 7-document retained F3
 * database (`eledgercare_f4_author_migrated`) with LocalOcr:Enabled=false.
 * Invoked both before and after the actual owned API + PostgreSQL 18.7 cluster fast restart (F4-06, F4-07).
 */
async function main() {
  const args = process.argv.slice(2);
  const phaseIdx = args.indexOf('--phase');
  const outIdx = args.indexOf('--output');
  const shotDirIdx = args.indexOf('--screenshot-dir');
  const apiPortIdx = args.indexOf('--api-port');
  const uiPortIdx = args.indexOf('--ui-port');

  const phase = phaseIdx >= 0 ? args[phaseIdx + 1] : 'before-restart';
  const outPath = outIdx >= 0 ? args[outIdx + 1] : null;
  const shotDir = shotDirIdx >= 0 ? args[shotDirIdx + 1] : null;
  const apiPort = apiPortIdx >= 0 ? Number(args[apiPortIdx + 1]) : 5590;
  const uiPort = uiPortIdx >= 0 ? Number(args[uiPortIdx + 1]) : 4610;

  if (!outPath || !shotDir) {
    throw new Error('Usage: node verify_f4_restart_edge.mjs --phase <before-restart|after-restart> --output <json> --screenshot-dir <dir>');
  }

  mkdirSync(shotDir, { recursive: true });
  mkdirSync(path.dirname(outPath), { recursive: true });

  const apiBase = `http://127.0.0.1:${apiPort}`;
  const uiBase = `http://127.0.0.1:${uiPort}`;

  // 1. Direct HTTP verification of saved archive queries, revision isolation, and original hashes (zero writes!)
  const browseAll = await fetchJson(`${apiBase}/api/archive?limit=20`);
  const browseMachine = await fetchJson(`${apiBase}/api/archive?source=machine&limit=20`);
  const browseReviewed = await fetchJson(`${apiBase}/api/archive?source=reviewed&limit=20`);

  if (browseAll.status !== 200 || browseAll.body.items.length !== 7) {
    throw new Error(`Expected 7 browse=all items, got status=${browseAll.status} count=${browseAll.body?.items?.length}`);
  }
  if (browseMachine.status !== 200 || browseMachine.body.items.length !== 5) {
    throw new Error(`Expected 5 browse=machine items, got ${browseMachine.body?.items?.length}`);
  }
  if (browseReviewed.status !== 200 || browseReviewed.body.items.length !== 3) {
    throw new Error(`Expected 3 browse=reviewed items (Seeds 1,3,5), got ${browseReviewed.body?.items?.length}`);
  }

  // Excluded sentinels (superseded Rev #1, unknown reason, unapproved drafts, failed diagnostics) must all return 0 items!
  const excludedQueries = [
    'SUPERSEDED-REV1-BIRCHWOOD',
    'SUPERSEDED-UNIT-TAG-991',
    'NONSEARCH-UNKNOWN-REASON-PLACARD-772',
    'DRAFT-ONLY-UNAPPROVED-JUNIPER-883',
    'DRAFT-UNREVIEWED-UNIT-999',
    'DRAFT-PREDECESSOR-WILLOW-301',
    'NEVER-REVIEWED-DRAFT-PINECREST-501',
    'NONSEARCH-MP-SUMMARY-OMITTED-604',
    'NONSEARCH-DIAGNOSTIC-PARTIAL-719',
    'NONSEARCH-FAILURE-DETAIL-719',
  ];
  for (const token of excludedQueries) {
    const res = await fetchJson(`${apiBase}/api/archive?q=${encodeURIComponent(token)}`);
    if (res.status !== 200 || res.body.items.length !== 0) {
      throw new Error(`Excluded sentinel '${token}' leaked into archive search!`);
    }
  }

  // Saved active queries for deterministic before-vs-after restart comparison
  const qHawthorne = await fetchJson(
    `${apiBase}/api/archive?q=${encodeURIComponent('Café_100% \\ [REV2-ACTIVE-HAWTHORNE]')}&source=reviewed`,
  );
  const qKestrelCrossSource = await fetchJson(
    `${apiBase}/api/archive?q=${encodeURIComponent('MANUAL-NO-PROVENANCE-KESTREL-0042 0018-TERM-QC')}&source=all`,
  );
  const qMpPage2 = await fetchJson(
    `${apiBase}/api/archive?q=${encodeURIComponent('Refrigerator Evaporator')}&source=machine`,
  );
  const qAlderReviewed = await fetchJson(
    `${apiBase}/api/archive?q=${encodeURIComponent('MULTIPAGE-REVIEWED-ALDER-P2')}&source=reviewed`,
  );

  if (qHawthorne.body.items.length !== 1 || qHawthorne.body.items[0].documentId !== SEED1_DOC) {
    throw new Error('Expected Seed 1 match for Café_100% \\ [REV2-ACTIVE-HAWTHORNE]');
  }
  if (qKestrelCrossSource.body.items.length !== 1 || qKestrelCrossSource.body.items[0].documentId !== SEED1_DOC) {
    throw new Error('Expected Seed 1 cross-source AND match for KESTREL + 0018-TERM-QC');
  }
  if (qMpPage2.body.items.length !== 2) {
    throw new Error(`Expected 2 machine matches (Seeds 2 & 5) for Refrigerator Evaporator, got ${qMpPage2.body.items.length}`);
  }
  if (qAlderReviewed.body.items.length !== 1 || qAlderReviewed.body.items[0].documentId !== SEED5_DOC) {
    throw new Error('Expected Seed 5 match for MULTIPAGE-REVIEWED-ALDER-P2');
  }

  const origSeed1 = await fetchSha256(`${apiBase}/api/documents/${SEED1_DOC}/original`);
  const prevSeed2 = await fetchSha256(`${apiBase}/api/documents/${SEED2_DOC}/preview`);
  const origSeed7 = await fetchSha256(`${apiBase}/api/documents/${SEED7_DOC}/original`);
  if (
    origSeed1.sha256 !== EXPECTED_WO_PDF_SHA ||
    prevSeed2.sha256 !== EXPECTED_MP_PDF_SHA ||
    origSeed7.sha256 !== EXPECTED_F1_PDF_SHA
  ) {
    throw new Error('Original/preview SHA-256 mismatch on retained seed documents!');
  }

  // 2. Real headless Microsoft Edge browser verification (readable PDF pages + pinned history + query-preserving navigation)
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const browserVersion = browser.version();
  const context = await browser.newContext({
    viewport: { width: 1680, height: 980 },
    acceptDownloads: true,
  });
  const page = await context.newPage();
  const dialogs = [];
  page.on('dialog', async (d) => {
    dialogs.push(d.message());
    await d.dismiss();
  });

  const screenshots = [];
  try {
    // A. Browse /archive: verify 7 cards, Seed 1 newer draft badge, Seed 6 failed, Seed 7 awaiting_extraction
    await page.goto(`${uiBase}/archive`, { waitUntil: 'networkidle' });
    await page.getByTestId(`archive-card-${SEED1_DOC}`).waitFor({ state: 'visible', timeout: 30000 });
    await waitForCondition(
      async () => (await page.locator('article.archive-card').count()) === 7,
      '7 archive cards rendered',
    );

    const browseShot = path.join(shotDir, `${phase}-01-archive-browse-7-seeds.png`);
    await page.screenshot({ path: browseShot });
    screenshots.push(browseShot);

    // B. Search machine text "Refrigerator Evaporator" -> open Seed 2 Page 2 readable PDF preview -> return to query
    await page.getByTestId('archive-source-select').selectOption('machine');
    await page.getByTestId('archive-query-input').fill('Refrigerator Evaporator');
    await page.getByTestId('archive-submit-btn').click();

    await waitForCondition(
      async () => page.url().includes('q=Refrigerator%20Evaporator') && page.url().includes('source=machine'),
      'URL updated for machine search',
    );
    await page.getByTestId(`witness-open-machine-${SEED2_DOC}-0`).waitFor({ state: 'visible', timeout: 15000 });
    await page.getByTestId(`witness-open-machine-${SEED2_DOC}-0`).click();

    await waitForCondition(
      async () => page.url().includes(`/documents/${SEED2_DOC}`) && page.url().includes('page=2'),
      'DocumentPage opened at page=2',
    );
    await page.getByTestId('document-pdf-preview-frame').waitFor({ state: 'visible', timeout: 15000 });
    const frameSrc = await page.getByTestId('document-pdf-preview-frame').getAttribute('src');
    if (frameSrc !== `/api/documents/${SEED2_DOC}/preview#page=2`) {
      throw new Error(`Unexpected DocumentPage preview iframe src: ${frameSrc}`);
    }
    await page.waitForTimeout(2200);
    const pdfPage2Shot = path.join(shotDir, `${phase}-02-seed2-mp01-page2-pdf-preview.png`);
    await page.screenshot({ path: pdfPage2Shot });
    screenshots.push(pdfPage2Shot);

    await page.getByTestId('back-to-archive').click();
    await waitForCondition(
      async () => page.url().endsWith('/archive?q=Refrigerator%20Evaporator&source=machine'),
      'Returned to exact machine archive query',
    );

    // C. Search Seed 1 reviewed hit ("MANUAL-NO-PROVENANCE-KESTREL-0042") -> inert <script> + 🔧 -> open pinned Rev #2 (no fabricated page!) -> return
    await page.getByTestId('archive-source-select').selectOption('reviewed');
    await page.getByTestId('archive-query-input').fill('MANUAL-NO-PROVENANCE-KESTREL-0042');
    await page.getByTestId('archive-submit-btn').click();

    await page.getByTestId(`witness-open-reviewed-${SEED1_DOC}-0`).waitFor({ state: 'visible', timeout: 15000 });
    const snippetText = await page.getByTestId(`archive-snippet-${SEED1_DOC}-0`).textContent();
    if (!snippetText.includes("<script>alert('inert')</script>") || !snippetText.includes('🔧')) {
      throw new Error(`Expected inert <script> and 🔧 in snippet, got: ${snippetText}`);
    }
    const injectedScripts = await page.locator('[data-testid="archive-results-section"] script').count();
    if (injectedScripts !== 0 || dialogs.length !== 0) {
      throw new Error(`Unexpected script tag or alert dialog: scripts=${injectedScripts}, dialogs=${dialogs.length}`);
    }

    await page.getByTestId(`witness-open-reviewed-${SEED1_DOC}-0`).click();
    await waitForCondition(
      async () => page.url().includes(`/documents/${SEED1_DOC}/review/revisions/2`),
      'Opened Seed 1 pinned historical Revision #2',
    );
    if (page.url().includes('page=')) {
      throw new Error(`Fabricated page= param found on null-provenance reviewed link: ${page.url()}`);
    }
    await page.getByTestId('historical-revision-banner').waitFor({ state: 'visible', timeout: 15000 });
    const bannerTxt = await page.getByTestId('historical-revision-banner').textContent();
    if (!bannerTxt.includes('Revision #2 (reviewed)') || !bannerTxt.includes('Revision #3: draft')) {
      throw new Error(`Unexpected historical banner on Seed 1: ${bannerTxt}`);
    }
    const noProvCount = await page.getByTestId('historical-no-provenance-issue_and_resolution').count();
    const fabricatedBtnCount = await page.getByTestId('historical-consulted-page-issue_and_resolution').count();
    if (noProvCount !== 1 || fabricatedBtnCount !== 0) {
      throw new Error(`Expected explicit no-provenance notice and 0 page jump buttons, got ${noProvCount}/${fabricatedBtnCount}`);
    }
    await page.waitForTimeout(1800);
    const seed1HistShot = path.join(shotDir, `${phase}-03-seed1-pinned-rev2-history.png`);
    await page.screenshot({ path: seed1HistShot });
    screenshots.push(seed1HistShot);

    await page.getByTestId('review-back-to-archive').click();
    await waitForCondition(
      async () => page.url().endsWith('/archive?q=MANUAL-NO-PROVENANCE-KESTREL-0042&source=reviewed'),
      'Returned to exact reviewed archive query',
    );

    // D. Search Seed 5 reviewed hit ("MULTIPAGE-REVIEWED-ALDER-P2") -> recorded Page 2 provenance opens #page=2 two-pane review!
    await page.getByTestId('archive-query-input').fill('MULTIPAGE-REVIEWED-ALDER-P2');
    await page.getByTestId('archive-submit-btn').click();
    await page.getByTestId(`witness-open-reviewed-${SEED5_DOC}-0`).waitFor({ state: 'visible', timeout: 15000 });
    await page.getByTestId(`witness-open-reviewed-${SEED5_DOC}-0`).click();

    await waitForCondition(
      async () => page.url().includes(`/documents/${SEED5_DOC}/review/revisions/1`) && page.url().includes('page=2'),
      'Opened Seed 5 Revision #1 with recorded page=2',
    );
    await page.getByTestId('pdf-preview-frame').waitFor({ state: 'visible', timeout: 15000 });
    const reviewFrameSrc = await page.getByTestId('pdf-preview-frame').getAttribute('src');
    if (reviewFrameSrc !== `/api/documents/${SEED5_DOC}/preview#page=2`) {
      throw new Error(`Expected Seed 5 review iframe #page=2, got ${reviewFrameSrc}`);
    }
    await page.waitForTimeout(2000);
    const seed5Page2Shot = path.join(shotDir, `${phase}-04-seed5-reviewed-page2-two-pane.png`);
    await page.screenshot({ path: seed5Page2Shot });
    screenshots.push(seed5Page2Shot);

    const storageDump = await page.evaluate(() => ({
      local: Object.keys(localStorage),
      session: Object.keys(sessionStorage),
    }));
    if (storageDump.local.length !== 0 || storageDump.session.length !== 0) {
      throw new Error(`Unexpected browser storage writes: ${JSON.stringify(storageDump)}`);
    }

    const receipt = {
      phase,
      edgeBrowserVersion: browserVersion,
      apiPort,
      uiPort,
      browseCounts: {
        all: browseAll.body.items.length,
        machine: browseMachine.body.items.length,
        reviewed: browseReviewed.body.items.length,
      },
      excludedSentinelsVerifiedZero: excludedQueries.length,
      savedQueryResponsesCanonicalSha256: createHash('sha256')
        .update(
          JSON.stringify({
            browseAll: browseAll.body,
            browseMachine: browseMachine.body,
            browseReviewed: browseReviewed.body,
            qHawthorne: qHawthorne.body,
            qKestrelCrossSource: qKestrelCrossSource.body,
            qMpPage2: qMpPage2.body,
            qAlderReviewed: qAlderReviewed.body,
          }),
        )
        .digest('hex'),
      originalDigests: {
        seed1WoPdfSha256: origSeed1.sha256,
        seed2MpPreviewSha256: prevSeed2.sha256,
        seed7F1PdfSha256: origSeed7.sha256,
      },
      screenshots: screenshots.map((p) => path.relative(repoRoot, p).replace(/\\/g, '/')),
      zeroBrowserStorageWrites: true,
      zeroAlertDialogs: dialogs.length === 0,
    };

    writeFileSync(outPath, JSON.stringify(receipt, null, 2) + '\n', 'utf8');
    console.log(`Edge F4 ${phase} verification passed (${browserVersion}, savedQueriesSha=${receipt.savedQueryResponsesCanonicalSha256}).`);
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
