import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import net from 'node:net';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

/**
 * Independent Stage 2 real-result Microsoft Edge UI verifier v2 (eld-next-reviewer, WP-0006).
 * Reconciles UI status-label & attempt-history assertions against accepted Angular UI source
 * (web/src/app/intake/receipt.ts & document-page.ts at 8a73b7a5dab51e3ccf803aceedded4929529dd35)
 * while preserving runtime-preparation/helpers/verify_ui_reviewer_real_results.mjs unchanged.
 *
 * Exports EXPECTED_UI_STATUS_LABELS and validateDocumentUiObservation() so both live headless
 * Microsoft Edge runs (UI 4310 -> API 5290) and CPU-only deterministic preparation tests execute
 * the exact same verification logic.
 */
export const EXPECTED_UI_STATUS_LABELS = Object.freeze({
  awaiting_extraction: 'Awaiting extraction',
  queued: 'Queued for extraction',
  running: 'Extraction running',
  completed: 'Completed (unreviewed)',
  failed: 'Extraction failed',
  interrupted: 'Extraction interrupted',
});

export const EXPECTED_MODEL_CHECKPOINT_TEXT =
  'baidu/Unlimited-OCR-2 @ 0480966938291445591f69f08a13b041c073a96a';
export const EXPECTED_UNREVIEWED_STRONG_TEXT = 'Unreviewed raw extraction output (unreviewed)';

/**
 * Pure deterministic validator enforcing exact UI labels, provenance, page ordering, inert DOM,
 * raw UTF-8 SHA-256, downloaded original PDF bytes/SHA-256, and per-attempt API <-> DOM cell bindings.
 */
export function validateDocumentUiObservation(specItem, apiExtractionView, domObservation, expectOcrDisabled) {
  if (!specItem || typeof specItem !== 'object') {
    throw new Error('Missing document specification item.');
  }
  if (!apiExtractionView || typeof apiExtractionView !== 'object') {
    throw new Error(`Missing API extraction view for ${specItem.documentId}`);
  }
  if (!domObservation || typeof domObservation !== 'object') {
    throw new Error(`Missing DOM observation for ${specItem.documentId}`);
  }

  const docId = specItem.documentId;

  // 1. Document header & top-level status assertions (document-page.ts:24-40)
  if (domObservation.documentIdText !== docId || apiExtractionView.documentId !== docId) {
    throw new Error(
      `Document ID mismatch on ${docId}: dom='${domObservation.documentIdText}', api='${apiExtractionView.documentId}'`,
    );
  }
  if (!apiExtractionView.jobId || domObservation.jobIdText !== apiExtractionView.jobId) {
    throw new Error(
      `Job ID mismatch on ${docId}: dom='${domObservation.jobIdText}', api='${apiExtractionView.jobId}'`,
    );
  }
  if (apiExtractionView.status !== 'completed') {
    throw new Error(`Expected API extraction status 'completed' on ${docId}, got '${apiExtractionView.status}'`);
  }
  if (domObservation.statusText !== EXPECTED_UI_STATUS_LABELS.completed) {
    throw new Error(
      `Document ${docId} UI status '${domObservation.statusText}' != '${EXPECTED_UI_STATUS_LABELS.completed}'`,
    );
  }
  if (domObservation.documentPageCountText !== String(specItem.expectedPages)) {
    throw new Error(
      `Document ${docId} UI admittedPageCount '${domObservation.documentPageCountText}' != '${specItem.expectedPages}'`,
    );
  }
  const wantDocBytesText = `${specItem.expectedOriginalBytes} bytes`;
  if (domObservation.documentByteLengthText !== wantDocBytesText) {
    throw new Error(
      `Document ${docId} UI byteLength '${domObservation.documentByteLengthText}' != '${wantDocBytesText}'`,
    );
  }
  if (domObservation.documentSha256Text !== specItem.expectedOriginalSha256) {
    throw new Error(
      `Document ${docId} UI original SHA-256 '${domObservation.documentSha256Text}' != '${specItem.expectedOriginalSha256}'`,
    );
  }

  // 2. Worker-disabled / action-button / error-banner assertions (document-page.ts:51-113)
  if (expectOcrDisabled) {
    if (
      apiExtractionView.workerEnabled !== false ||
      apiExtractionView.canRequestExtraction !== false ||
      apiExtractionView.canRetryExtraction !== false
    ) {
      throw new Error(
        `Expected workerEnabled=false & canRequest/canRetry=false on ${docId}, got workerEnabled=${apiExtractionView.workerEnabled}`,
      );
    }
  }
  if (
    domObservation.unsupportedCount !== 0 ||
    domObservation.unavailableCount !== 0 ||
    domObservation.activePanelCount !== 0 ||
    domObservation.failurePanelCount !== 0
  ) {
    throw new Error(
      `Unexpected non-completed banner visible on ${docId}: unsupported=${domObservation.unsupportedCount}, unavailable=${domObservation.unavailableCount}, active=${domObservation.activePanelCount}, failure=${domObservation.failurePanelCount}`,
    );
  }
  if (domObservation.actionButtonsCount !== 0) {
    throw new Error(
      `Completed document ${docId} unexpectedly rendered ${domObservation.actionButtonsCount} request/refresh/retry action button(s)`,
    );
  }

  // 3. Unreviewed banner & provenance assertions (document-page.ts:147-174)
  const apiRes = apiExtractionView.result;
  if (!apiRes || apiRes.reviewStatus !== 'unreviewed') {
    throw new Error(`Expected API result.reviewStatus='unreviewed' on ${docId}`);
  }
  if (domObservation.unreviewedBannerStrongText !== EXPECTED_UNREVIEWED_STRONG_TEXT) {
    throw new Error(
      `Unreviewed banner strong text '${domObservation.unreviewedBannerStrongText}' != '${EXPECTED_UNREVIEWED_STRONG_TEXT}' on ${docId}`,
    );
  }
  if (specItem.expectedResultId && domObservation.resultIdText !== specItem.expectedResultId) {
    throw new Error(
      `Result ID '${domObservation.resultIdText}' != expected '${specItem.expectedResultId}' on ${docId}`,
    );
  }
  if (domObservation.resultIdText !== apiRes.resultId) {
    throw new Error(
      `UI result-id '${domObservation.resultIdText}' != API resultId '${apiRes.resultId}' on ${docId}`,
    );
  }
  if (!specItem.expectedWinningAttemptId || domObservation.resultAttemptIdText !== specItem.expectedWinningAttemptId) {
    throw new Error(
      `UI result-attempt-id '${domObservation.resultAttemptIdText}' != expected winning attempt '${specItem.expectedWinningAttemptId}' on ${docId}`,
    );
  }
  if (domObservation.resultAttemptIdText !== apiRes.attemptId) {
    throw new Error(
      `UI result-attempt-id '${domObservation.resultAttemptIdText}' != API result.attemptId '${apiRes.attemptId}' on ${docId}`,
    );
  }
  if (domObservation.modelText !== EXPECTED_MODEL_CHECKPOINT_TEXT) {
    throw new Error(
      `UI result-model '${domObservation.modelText}' != '${EXPECTED_MODEL_CHECKPOINT_TEXT}' on ${docId}`,
    );
  }
  if (
    !domObservation.rendererText.includes('pypdfium2==5.15.2') ||
    !domObservation.rendererText.includes('159.0.8149.0')
  ) {
    throw new Error(`Renderer provenance unexpected on ${docId}: '${domObservation.rendererText}'`);
  }
  if (specItem.expectedRawByteLength !== undefined) {
    const pageWord = specItem.expectedPages === 1 ? 'page' : 'pages';
    const wantRawSizeText = `${specItem.expectedRawByteLength} bytes (${specItem.expectedPages} ${pageWord})`;
    if (domObservation.rawByteLengthText !== wantRawSizeText) {
      throw new Error(
        `UI result-raw-byte-length '${domObservation.rawByteLengthText}' != '${wantRawSizeText}' on ${docId}`,
      );
    }
  }
  if (domObservation.uiRawSha256 !== specItem.expectedRawSha256) {
    throw new Error(`UI rawSha256 ${domObservation.uiRawSha256} != expected ${specItem.expectedRawSha256}`);
  }

  // 4. Page ordering, inert DOM, raw <pre> UTF-8 SHA-256, and original PDF download
  const wantHeadings = Array.from(
    { length: specItem.expectedPages },
    (_, idx) => `Page ${idx + 1} of ${specItem.expectedPages}`,
  );
  if (JSON.stringify(domObservation.pageHeadings) !== JSON.stringify(wantHeadings)) {
    throw new Error(
      `Page headings ${JSON.stringify(domObservation.pageHeadings)} != ${JSON.stringify(wantHeadings)} on ${docId}`,
    );
  }
  if (domObservation.forbiddenDomTagCount !== 0 || domObservation.inlineEventAttrCount !== 0) {
    throw new Error(
      `Unsafe DOM inside extraction-result on ${docId}: tags=${domObservation.forbiddenDomTagCount}, inlineEvents=${domObservation.inlineEventAttrCount}`,
    );
  }
  if (domObservation.renderedBlockCount < 1) {
    throw new Error(`Expected >= 1 rendered block on ${docId}, found ${domObservation.renderedBlockCount}`);
  }
  if (domObservation.rawPreElementSha256 !== specItem.expectedRawSha256) {
    throw new Error(
      `Rendered raw-text SHA-256 ${domObservation.rawPreElementSha256} != ${specItem.expectedRawSha256} on ${docId}`,
    );
  }
  if (
    domObservation.downloadedSha256 !== specItem.expectedOriginalSha256 ||
    domObservation.downloadedByteLength !== specItem.expectedOriginalBytes
  ) {
    throw new Error(
      `Downloaded original mismatch on ${docId}: sha=${domObservation.downloadedSha256}, len=${domObservation.downloadedByteLength}`,
    );
  }

  // 5. Exact Attempt History table & API association (document-page.ts:115-143 & receipt.ts:105-116)
  if (!Array.isArray(specItem.expectedAttempts) || specItem.expectedAttempts.length < 1) {
    throw new Error(`specItem.expectedAttempts must be a non-empty array of structured attempt expectations on ${docId}`);
  }
  const wantSummary = `Attempt history (${specItem.expectedAttempts.length})`;
  if (domObservation.attemptHistorySummaryText !== wantSummary) {
    throw new Error(
      `Attempt history summary '${domObservation.attemptHistorySummaryText}' != '${wantSummary}' on ${docId}`,
    );
  }
  const apiAttempts = apiExtractionView.attempts;
  if (!Array.isArray(apiAttempts) || apiAttempts.length !== specItem.expectedAttempts.length) {
    throw new Error(
      `API attempts count ${apiAttempts?.length} != expected ${specItem.expectedAttempts.length} on ${docId}`,
    );
  }
  if (!Array.isArray(domObservation.attemptRows) || domObservation.attemptRows.length !== specItem.expectedAttempts.length) {
    throw new Error(
      `DOM attempt-row count ${domObservation.attemptRows?.length} != expected ${specItem.expectedAttempts.length} on ${docId}`,
    );
  }

  const verifiedAttempts = [];
  for (let i = 0; i < specItem.expectedAttempts.length; i++) {
    const exp = specItem.expectedAttempts[i];
    const apiAtt = apiAttempts[i];
    const domRow = domObservation.attemptRows[i];

    const canonicalLabel = EXPECTED_UI_STATUS_LABELS[exp.apiStatus];
    if (!canonicalLabel) {
      throw new Error(`Unknown expected apiStatus '${exp.apiStatus}' on ${docId} attempt index ${i}`);
    }
    if (exp.expectedUiStatusLabel !== canonicalLabel) {
      throw new Error(
        `Invalid spec expectedUiStatusLabel '${exp.expectedUiStatusLabel}' for apiStatus '${exp.apiStatus}'; expected exact '${canonicalLabel}'`,
      );
    }
    if (exp.attemptNumber !== i + 1) {
      throw new Error(`Expected sequential 1-based attemptNumber ${i + 1}, got ${exp.attemptNumber}`);
    }

    // Verify underlying API attempt record matches expected attemptNumber, attemptId, status, and phase
    if (
      apiAtt.attemptNumber !== exp.attemptNumber ||
      apiAtt.attemptId !== exp.attemptId ||
      apiAtt.status !== exp.apiStatus ||
      apiAtt.phase !== exp.expectedPhase
    ) {
      throw new Error(
        `API attempt #${i + 1} mismatch on ${docId}: got ${JSON.stringify(apiAtt)}, expected ${JSON.stringify(exp)}`,
      );
    }
    if (!apiAtt.startedAtUtc || !apiAtt.endedAtUtc) {
      throw new Error(`Terminal attempt #${exp.attemptNumber} missing startedAtUtc/endedAtUtc in API view on ${docId}`);
    }

    // Verify exact 6 <td> cells rendered in <tr data-testid="attempt-row-N">
    if (!domRow || domRow.testId !== `attempt-row-${exp.attemptNumber}` || !Array.isArray(domRow.cells) || domRow.cells.length !== 6) {
      throw new Error(`Malformed DOM row for attempt #${exp.attemptNumber} on ${docId}: ${JSON.stringify(domRow)}`);
    }
    const [numCell, idCell, statusLabelCell, phaseCell, startedCell, endedCell] = domRow.cells;
    if (numCell !== String(exp.attemptNumber)) {
      throw new Error(`Attempt row #${exp.attemptNumber} cell[0] '${numCell}' != '${exp.attemptNumber}' on ${docId}`);
    }
    if (idCell !== exp.attemptId || domRow.codeAttemptId !== exp.attemptId) {
      throw new Error(
        `Attempt row #${exp.attemptNumber} attemptId cell '${idCell}' (code='${domRow.codeAttemptId}') != '${exp.attemptId}' on ${docId}`,
      );
    }
    if (statusLabelCell !== canonicalLabel) {
      throw new Error(
        `Attempt row #${exp.attemptNumber} UI status label '${statusLabelCell}' != '${canonicalLabel}' (apiStatus='${exp.apiStatus}') on ${docId}`,
      );
    }
    if (phaseCell !== exp.expectedPhase) {
      throw new Error(
        `Attempt row #${exp.attemptNumber} phase cell '${phaseCell}' != '${exp.expectedPhase}' on ${docId}`,
      );
    }
    if (startedCell !== apiAtt.startedAtUtc) {
      throw new Error(
        `Attempt row #${exp.attemptNumber} startedAtUtc cell '${startedCell}' != API '${apiAtt.startedAtUtc}' on ${docId}`,
      );
    }
    if (endedCell !== apiAtt.endedAtUtc || endedCell === '—') {
      throw new Error(
        `Attempt row #${exp.attemptNumber} endedAtUtc cell '${endedCell}' != API '${apiAtt.endedAtUtc}' on ${docId}`,
      );
    }

    verifiedAttempts.push({
      attemptNumber: exp.attemptNumber,
      attemptId: exp.attemptId,
      apiStatus: apiAtt.status,
      uiStatusLabel: statusLabelCell,
      phase: phaseCell,
      startedAtUtc: startedCell,
      endedAtUtc: endedCell,
    });
  }

  const winningExp = specItem.expectedAttempts[specItem.expectedAttempts.length - 1];
  if (winningExp.apiStatus !== 'completed' || winningExp.attemptId !== specItem.expectedWinningAttemptId) {
    throw new Error(`Final attempt on completed document ${docId} must be the winning completed attempt.`);
  }

  return {
    documentId: docId,
    label: specItem.label,
    expectOcrDisabled: Boolean(expectOcrDisabled),
    statusText: domObservation.statusText,
    unreviewedBannerStrongText: domObservation.unreviewedBannerStrongText,
    actionButtonsCount: domObservation.actionButtonsCount,
    resultId: domObservation.resultIdText,
    winningAttemptId: domObservation.resultAttemptIdText,
    modelText: domObservation.modelText,
    rendererText: domObservation.rendererText,
    rawByteLengthText: domObservation.rawByteLengthText,
    uiRawSha256: domObservation.uiRawSha256,
    rawPreElementSha256: domObservation.rawPreElementSha256,
    pageHeadings: domObservation.pageHeadings,
    renderedBlockCount: domObservation.renderedBlockCount,
    renderedTableCount: domObservation.renderedTableCount,
    forbiddenDomTagCount: domObservation.forbiddenDomTagCount,
    inlineEventAttrCount: domObservation.inlineEventAttrCount,
    attemptHistorySummaryText: domObservation.attemptHistorySummaryText,
    attemptHistoryRowCount: verifiedAttempts.length,
    verifiedAttempts,
    downloadedFilename: domObservation.downloadedFilename,
    downloadedByteLength: domObservation.downloadedByteLength,
    downloadedSha256: domObservation.downloadedSha256,
  };
}

function parseArgs(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 2) {
    out[argv[i].replace(/^--/, '')] = argv[i + 1];
  }
  return out;
}

function checkPortBound(port) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host: '127.0.0.1', port });
    socket.setTimeout(300);
    socket.on('connect', () => {
      socket.destroy();
      resolve(true);
    });
    socket.on('error', () => resolve(false));
    socket.on('timeout', () => {
      socket.destroy();
      resolve(false);
    });
  });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.input || !args.output || !args.repoRoot) {
    throw new Error(
      'Usage: node verify_ui_reviewer_real_results_v2.mjs --repoRoot <dir> --input <in.json> --output <out.json>',
    );
  }

  const repoRoot = path.resolve(args.repoRoot);
  const webDir = path.join(repoRoot, 'web');
  const reqFromWeb = createRequire(path.join(webDir, 'package.json'));
  const { chromium } = reqFromWeb('playwright');

  const spec = JSON.parse(readFileSync(args.input, 'utf8'));
  const uiPort = Number(spec.uiPort ?? 4310);
  const apiPort = Number(spec.apiPort ?? 5290);
  const expectOcrDisabled = Boolean(spec.expectOcrDisabled ?? false);

  if (uiPort !== 4310 || apiPort !== 5290) {
    throw new Error(
      `Reviewer UI verifier v2 requires owned loopback ports UI=4310 / API=5290, got UI=${uiPort} / API=${apiPort}`,
    );
  }

  if (await checkPortBound(uiPort)) {
    throw new Error(`Owned reviewer UI port ${uiPort} is already bound before starting ng serve.`);
  }

  const ngBin = path.join(webDir, 'node_modules', '@angular', 'cli', 'bin', 'ng.js');
  const ngProc = spawn(
    process.execPath,
    [ngBin, 'serve', '--host', '127.0.0.1', '--port', String(uiPort), '--proxy-config', 'proxy.conf.mjs'],
    {
      cwd: webDir,
      env: {
        ...process.env,
        ELEDGERCARE_API_PORT: String(apiPort),
        NG_CLI_ANALYTICS: 'false',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    },
  );

  const ngStartedUtc = new Date().toISOString();
  const ngPid = ngProc.pid;

  try {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error(`ng serve did not listen on ${uiPort} within 120s`)), 120_000);
      const onChunk = (buf) => {
        if (buf.toString().includes(`http://127.0.0.1:${uiPort}`)) {
          clearTimeout(timer);
          resolve();
        }
      };
      ngProc.stdout.on('data', onChunk);
      ngProc.stderr.on('data', onChunk);
      ngProc.on('exit', (code) => {
        clearTimeout(timer);
        reject(new Error(`ng serve exited early with code ${code}`));
      });
    });

    const browser = await chromium.launch({ channel: 'msedge', headless: true });
    const browserVersion = browser.version();
    const results = [];

    try {
      const context = await browser.newContext({ acceptDownloads: true });
      const page = await context.newPage();

      for (const item of spec.documents) {
        const apiResp = await fetch(`http://127.0.0.1:${uiPort}/api/documents/${encodeURIComponent(item.documentId)}/extraction`);
        if (!apiResp.ok) {
          throw new Error(`Proxied GET /api/documents/${item.documentId}/extraction returned HTTP ${apiResp.status}`);
        }
        const apiExtractionView = await apiResp.json();

        await page.goto(`http://127.0.0.1:${uiPort}/documents/${item.documentId}`, { waitUntil: 'domcontentloaded' });
        await page.getByTestId('document-status').waitFor({ state: 'visible', timeout: 30_000 });
        await page.getByTestId('extraction-result').waitFor({ state: 'visible', timeout: 30_000 });

        const documentIdText = (await page.getByTestId('document-id').textContent())?.trim() ?? '';
        const jobIdText = (await page.getByTestId('document-job-id').textContent())?.trim() ?? '';
        const statusText = (await page.getByTestId('document-status').textContent())?.trim() ?? '';
        const documentPageCountText = (await page.getByTestId('document-page-count').textContent())?.trim() ?? '';
        const documentByteLengthText = (await page.getByTestId('document-byte-length').textContent())?.trim() ?? '';
        const documentSha256Text = (await page.getByTestId('document-sha256').textContent())?.trim() ?? '';

        const unsupportedCount = await page.getByTestId('extraction-unsupported').count();
        const unavailableCount = await page.getByTestId('extraction-unavailable').count();
        const activePanelCount = await page.getByTestId('extraction-active').count();
        const failurePanelCount = await page.getByTestId('extraction-failure').count();
        const actionButtonsCount = await page
          .locator('[data-testid="request-extraction"], [data-testid="refresh-extraction"], [data-testid="retry-extraction"]')
          .count();

        const unreviewedBannerStrongText =
          (await page.getByTestId('unreviewed-banner').locator('strong').textContent())?.trim() ?? '';
        const resultIdText = (await page.getByTestId('result-id').textContent())?.trim() ?? '';
        const resultAttemptIdText = (await page.getByTestId('result-attempt-id').textContent())?.trim() ?? '';
        const modelText = (await page.getByTestId('result-model').textContent())?.trim() ?? '';
        const rendererText = (await page.getByTestId('result-renderer').textContent())?.trim() ?? '';
        const rawByteLengthText = (await page.getByTestId('result-raw-byte-length').textContent())?.trim() ?? '';
        const uiRawSha256 = (await page.getByTestId('result-raw-sha256').textContent())?.trim() ?? '';

        const pageHeadings = await page.locator('[data-testid^="result-page-"] h4').allTextContents();

        const domSafety = await page.locator('[data-testid="extraction-result"]').evaluate((rootEl) => {
          const forbiddenTags = ['SCRIPT', 'IMG', 'IFRAME', 'OBJECT', 'EMBED', 'SVG', 'LINK', 'STYLE', 'FORM'];
          let forbiddenTagCount = 0;
          let inlineEventAttrCount = 0;
          const walker = document.createTreeWalker(rootEl, NodeFilter.SHOW_ELEMENT);
          let cur = walker.nextNode();
          while (cur) {
            if (forbiddenTags.includes(cur.tagName)) {
              forbiddenTagCount++;
            }
            for (const attr of cur.getAttributeNames()) {
              if (attr.toLowerCase().startsWith('on')) {
                inlineEventAttrCount++;
              }
            }
            cur = walker.nextNode();
          }
          return { forbiddenTagCount, inlineEventAttrCount };
        });

        const renderedTableCount = await page.locator('[data-testid="extraction-result"] table.grid-table').count();
        const renderedBlockCount = await page
          .locator(
            '[data-testid="extraction-result"] p.extracted-title, [data-testid="extraction-result"] p.extracted-line, [data-testid="extraction-result"] table.grid-table',
          )
          .count();

        await page.getByTestId('result-raw-details').locator('summary').click();
        const rawTextUi = (await page.getByTestId('result-raw-text').textContent()) ?? '';
        const rawPreElementSha256 = createHash('sha256').update(Buffer.from(rawTextUi, 'utf8')).digest('hex');

        const attemptHistorySummaryText =
          (await page.getByTestId('attempt-history').locator('summary').textContent())?.trim() ?? '';
        await page.getByTestId('attempt-history').locator('summary').click();

        const totalRenderedRows = await page.locator('[data-testid^="attempt-row-"]').count();
        const attemptRows = [];
        for (let n = 1; n <= totalRenderedRows; n++) {
          const rowLoc = page.getByTestId(`attempt-row-${n}`);
          const cells = (await rowLoc.locator('td').allTextContents()).map((c) => c.trim());
          const codeAttemptId = (await rowLoc.locator('td code').textContent())?.trim() ?? '';
          attemptRows.push({
            testId: `attempt-row-${n}`,
            cells,
            codeAttemptId,
          });
        }

        const dlPromise = page.waitForEvent('download');
        await page.getByTestId('document-download').click();
        const dl = await dlPromise;
        const dlBytes = readFileSync(await dl.path());
        const downloadedSha256 = createHash('sha256').update(dlBytes).digest('hex');

        const verified = validateDocumentUiObservation(
          item,
          apiExtractionView,
          {
            documentIdText,
            jobIdText,
            statusText,
            documentPageCountText,
            documentByteLengthText,
            documentSha256Text,
            unsupportedCount,
            unavailableCount,
            activePanelCount,
            failurePanelCount,
            actionButtonsCount,
            unreviewedBannerStrongText,
            resultIdText,
            resultAttemptIdText,
            modelText,
            rendererText,
            rawByteLengthText,
            uiRawSha256,
            pageHeadings,
            forbiddenDomTagCount: domSafety.forbiddenTagCount,
            inlineEventAttrCount: domSafety.inlineEventAttrCount,
            renderedTableCount,
            renderedBlockCount,
            rawPreElementSha256,
            attemptHistorySummaryText,
            attemptRows,
            downloadedFilename: dl.suggestedFilename(),
            downloadedByteLength: dlBytes.length,
            downloadedSha256,
          },
          expectOcrDisabled,
        );
        results.push(verified);
      }

      await context.close();
    } finally {
      await browser.close();
    }

    writeFileSync(
      args.output,
      Buffer.from(
        JSON.stringify(
          {
            schema: 'eledgercare.wp-0006.reviewer-ui-verification/2',
            reviewer: 'eld-next-reviewer',
            verifiedUtc: new Date().toISOString(),
            browserChannel: 'msedge',
            browserVersion,
            ngServePid: ngPid,
            ngServeStartedUtc: ngStartedUtc,
            uiPort,
            apiPort,
            expectOcrDisabled,
            documentsVerified: results,
          },
          null,
          2,
        ) + '\n',
        'utf8',
      ),
    );
  } finally {
    if (ngProc.exitCode === null) {
      const exited = new Promise((resolve) => ngProc.once('exit', () => resolve()));
      ngProc.kill();
      await exited;
    }
    const deadline = Date.now() + 5_000;
    while (Date.now() < deadline && (await checkPortBound(uiPort))) {
      await sleep(100);
    }
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
