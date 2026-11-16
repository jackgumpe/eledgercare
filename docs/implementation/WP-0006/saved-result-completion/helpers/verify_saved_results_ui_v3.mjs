import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import net from 'node:net';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

/**
 * Frozen Angular statusLabel mapping (must match web/src/app/intake/receipt.ts lines 105-112).
 */
export const UI_STATUS_LABELS = Object.freeze({
  awaiting_extraction: 'Awaiting extraction',
  queued: 'Queued for extraction',
  running: 'Extraction running',
  completed: 'Completed (unreviewed)',
  failed: 'Extraction failed',
  interrupted: 'Extraction interrupted',
});

export function mapApiStatusToUiLabel(apiStatus) {
  const label = UI_STATUS_LABELS[apiStatus];
  if (!label) {
    throw new Error(`Unmapped API status '${apiStatus}'`);
  }
  return label;
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

async function fetchJsonGetOnly(url) {
  const resp = await fetch(url, { method: 'GET' });
  if (!resp.ok) {
    throw new Error(`GET ${url} failed with HTTP ${resp.status}`);
  }
  return await resp.json();
}

export async function runUiVerification(args) {
  if (!args.input || !args.output || !args.repoRoot) {
    throw new Error('Usage: node verify_saved_results_ui_v3.mjs --repoRoot <dir> --input <in.json> --output <out.json>');
  }

  const repoRoot = path.resolve(args.repoRoot);
  const webDir = path.join(repoRoot, 'web');
  const reqFromWeb = createRequire(path.join(webDir, 'package.json'));
  const { chromium } = reqFromWeb('playwright');

  const spec = JSON.parse(readFileSync(args.input, 'utf8'));
  const uiPort = Number(spec.uiPort ?? 4210);
  const apiPort = Number(spec.apiPort ?? 5190);

  if (await checkPortBound(uiPort)) {
    throw new Error(`Owned UI port ${uiPort} is already bound before starting ng serve.`);
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
        const docApi = await fetchJsonGetOnly(`http://127.0.0.1:${apiPort}/api/documents/${item.documentId}`);
        const extApi = await fetchJsonGetOnly(`http://127.0.0.1:${apiPort}/api/documents/${item.documentId}/extraction`);

        if (extApi.workerEnabled !== false || extApi.canRequestExtraction !== false || extApi.canRetryExtraction !== false) {
          throw new Error(
            `Expected OCR-disabled API flags on ${item.documentId}, got workerEnabled=${extApi.workerEnabled}, ` +
              `canRequest=${extApi.canRequestExtraction}, canRetry=${extApi.canRetryExtraction}`,
          );
        }

        await page.goto(`http://127.0.0.1:${uiPort}/documents/${item.documentId}`, { waitUntil: 'domcontentloaded' });
        await page.getByTestId('document-status').waitFor({ state: 'visible', timeout: 30_000 });
        await page.getByTestId('extraction-result').waitFor({ state: 'visible', timeout: 30_000 });

        const uiDocId = (await page.getByTestId('document-id').textContent())?.trim();
        const uiJobId = (await page.getByTestId('document-job-id').textContent())?.trim();
        const uiDocStatus = (await page.getByTestId('document-status').textContent())?.trim();
        const uiPageCount = Number((await page.getByTestId('document-page-count').textContent())?.trim());
        const uiDocSha = (await page.getByTestId('document-sha256').textContent())?.trim();

        const wantTopStatusLabel = mapApiStatusToUiLabel(extApi.status);
        if (uiDocId !== item.documentId || docApi.documentId !== item.documentId) {
          throw new Error(`Document ID mismatch on ${item.documentId}: ui='${uiDocId}', api='${docApi.documentId}'`);
        }
        if (uiJobId !== item.expectedJobId || docApi.jobId !== item.expectedJobId) {
          throw new Error(`Job ID mismatch on ${item.documentId}: ui='${uiJobId}', expected='${item.expectedJobId}'`);
        }
        if (extApi.status !== 'completed' || uiDocStatus !== wantTopStatusLabel) {
          throw new Error(`Document status mismatch on ${item.documentId}: ui='${uiDocStatus}', api='${extApi.status}'`);
        }
        if (uiPageCount !== item.expectedPages || uiDocSha !== item.expectedOriginalSha256) {
          throw new Error(`Document metadata mismatch on ${item.documentId}: pages=${uiPageCount}, sha=${uiDocSha}`);
        }

        const bannerText = (await page.getByTestId('unreviewed-banner').textContent())?.trim() ?? '';
        if (!bannerText.toLowerCase().includes('unreviewed')) {
          throw new Error(`Unreviewed banner missing expected label on ${item.documentId}`);
        }
        if ((await page.getByTestId('extraction-unavailable').count()) !== 0) {
          throw new Error(`Completed document ${item.documentId} unexpectedly showed extraction-unavailable banner`);
        }

        const uiResultId = (await page.getByTestId('result-id').textContent())?.trim() ?? '';
        const uiResultAttemptId = (await page.getByTestId('result-attempt-id').textContent())?.trim() ?? '';
        const modelText = (await page.getByTestId('result-model').textContent())?.trim() ?? '';
        const rendererText = (await page.getByTestId('result-renderer').textContent())?.trim() ?? '';
        const uiRawSha = (await page.getByTestId('result-raw-sha256').textContent())?.trim() ?? '';

        if (uiResultId !== item.expectedResultId || extApi.result?.resultId !== item.expectedResultId) {
          throw new Error(`Result ID mismatch on ${item.documentId}: ui='${uiResultId}', expected='${item.expectedResultId}'`);
        }
        if (uiResultAttemptId !== item.expectedWinningAttemptId || extApi.result?.attemptId !== item.expectedWinningAttemptId) {
          throw new Error(
            `Winning attempt ID mismatch on ${item.documentId}: ui='${uiResultAttemptId}', expected='${item.expectedWinningAttemptId}'`,
          );
        }
        if (modelText !== 'baidu/Unlimited-OCR-2 @ 0480966938291445591f69f08a13b041c073a96a') {
          throw new Error(`Model provenance mismatch on ${item.documentId}: '${modelText}'`);
        }
        if (rendererText !== 'pypdfium2==5.15.2;pdfium=159.0.8149.0;dpi=300;rgb') {
          throw new Error(`Renderer provenance mismatch on ${item.documentId}: '${rendererText}'`);
        }
        if (uiRawSha !== item.expectedRawSha256 || extApi.result?.rawSha256 !== item.expectedRawSha256) {
          throw new Error(`UI rawSha256 '${uiRawSha}' != expected '${item.expectedRawSha256}'`);
        }

        const pageHeadings = await page.locator('[data-testid^="result-page-"] h4').allTextContents();
        const wantHeadings = Array.from({ length: item.expectedPages }, (_, idx) => `Page ${idx + 1} of ${item.expectedPages}`);
        if (JSON.stringify(pageHeadings) !== JSON.stringify(wantHeadings)) {
          throw new Error(`Page headings ${JSON.stringify(pageHeadings)} != ${JSON.stringify(wantHeadings)}`);
        }

        const executableNodes = await page
          .locator('[data-testid="extraction-result"] script, [data-testid="extraction-result"] img, [data-testid="extraction-result"] iframe')
          .count();
        if (executableNodes !== 0) {
          throw new Error(`Expected 0 executable DOM elements inside extraction-result, found ${executableNodes}`);
        }

        const tableCount = await page.locator('[data-testid="extraction-result"] table.grid-table').count();
        const blockCount = await page
          .locator('[data-testid="extraction-result"] p.extracted-title, [data-testid="extraction-result"] p.extracted-line, [data-testid="extraction-result"] table.grid-table')
          .count();
        if (blockCount < 1) {
          throw new Error(`Expected >= 1 rendered block on ${item.documentId}`);
        }

        await page.getByTestId('result-raw-details').locator('summary').click();
        const rawTextUi = (await page.getByTestId('result-raw-text').textContent()) ?? '';
        const rawTextBuf = Buffer.from(rawTextUi, 'utf8');
        const rawTextUiSha = createHash('sha256').update(rawTextBuf).digest('hex');
        if (rawTextBuf.length !== item.expectedRawBytes || rawTextUiSha !== item.expectedRawSha256) {
          throw new Error(
            `Rendered raw-text mismatch on ${item.documentId}: bytes=${rawTextBuf.length} (want ${item.expectedRawBytes}), sha=${rawTextUiSha}`,
          );
        }

        // Expand attempt history and tie EVERY displayed row cell-by-cell to API status, attemptNumber, and exact attemptId
        await page.getByTestId('attempt-history').locator('summary').click();
        const domRowCount = await page.locator('[data-testid="attempt-history"] tbody tr').count();
        if (domRowCount !== item.expectedAttempts.length || extApi.attempts.length !== item.expectedAttempts.length) {
          throw new Error(
            `Attempt row count mismatch on ${item.documentId}: dom=${domRowCount}, api=${extApi.attempts.length}, expected=${item.expectedAttempts.length}`,
          );
        }

        const verifiedAttemptRows = [];
        for (let idx = 0; idx < item.expectedAttempts.length; idx++) {
          const expAtt = item.expectedAttempts[idx];
          const apiAtt = extApi.attempts[idx];
          const rowLocator = page.getByTestId(`attempt-row-${expAtt.attemptNumber}`);
          await rowLocator.waitFor({ state: 'visible', timeout: 10_000 });
          const cells = (await rowLocator.locator('td').allTextContents()).map((c) => c.trim());
          if (cells.length !== 6) {
            throw new Error(`Expected 6 <td> cells in attempt-row-${expAtt.attemptNumber}, got ${cells.length}: ${JSON.stringify(cells)}`);
          }
          const [cellNum, cellAttemptId, cellUiStatus, cellPhase, cellStarted, cellEnded] = cells;
          const expectedUiLabelFromApi = mapApiStatusToUiLabel(apiAtt.status);

          if (Number(cellNum) !== expAtt.attemptNumber || apiAtt.attemptNumber !== expAtt.attemptNumber) {
            throw new Error(`Attempt number mismatch at row ${idx + 1}: dom='${cellNum}', api='${apiAtt.attemptNumber}', expected='${expAtt.attemptNumber}'`);
          }
          if (cellAttemptId !== expAtt.attemptId || apiAtt.attemptId !== expAtt.attemptId) {
            throw new Error(`Attempt ID mismatch at row ${idx + 1}: dom='${cellAttemptId}', api='${apiAtt.attemptId}', expected='${expAtt.attemptId}'`);
          }
          if (apiAtt.status !== expAtt.apiStatus) {
            throw new Error(`Underlying API status '${apiAtt.status}' != expected '${expAtt.apiStatus}' on attempt ${expAtt.attemptId}`);
          }
          if (cellUiStatus !== expectedUiLabelFromApi || cellUiStatus !== expAtt.expectedUiLabel) {
            throw new Error(
              `Displayed UI status label '${cellUiStatus}' != frozen statusLabel('${apiAtt.status}')='${expectedUiLabelFromApi}' ` +
                `(expected '${expAtt.expectedUiLabel}') on attempt ${expAtt.attemptId}`,
            );
          }
          if (cellPhase !== expAtt.phase || apiAtt.phase !== expAtt.phase) {
            throw new Error(`Attempt phase mismatch on ${expAtt.attemptId}: dom='${cellPhase}', api='${apiAtt.phase}', expected='${expAtt.phase}'`);
          }
          if (!cellStarted || !cellEnded || cellEnded === '—') {
            throw new Error(`Missing started/ended UTC cell on terminal attempt ${expAtt.attemptId}: started='${cellStarted}', ended='${cellEnded}'`);
          }

          verifiedAttemptRows.push({
            attemptNumber: expAtt.attemptNumber,
            attemptId: cellAttemptId,
            underlyingApiStatus: apiAtt.status,
            displayedUiStatusLabel: cellUiStatus,
            phase: cellPhase,
            startedAtUtc: cellStarted,
            endedAtUtc: cellEnded,
          });
        }

        const dlPromise = page.waitForEvent('download');
        await page.getByTestId('document-download').click();
        const dl = await dlPromise;
        const dlBytes = readFileSync(await dl.path());
        const dlSha = createHash('sha256').update(dlBytes).digest('hex');
        if (dlSha !== item.expectedOriginalSha256 || dlBytes.length !== item.expectedOriginalBytes) {
          throw new Error(`Downloaded original mismatch on ${item.documentId}: sha=${dlSha}, len=${dlBytes.length}`);
        }

        results.push({
          documentId: item.documentId,
          jobId: uiJobId,
          resultId: uiResultId,
          winningAttemptId: uiResultAttemptId,
          label: item.label,
          statusText: uiDocStatus,
          unreviewedBannerVisible: true,
          modelText,
          rendererText,
          uiRawSha256: uiRawSha,
          rawPreElementByteLength: rawTextBuf.length,
          rawPreElementSha256: rawTextUiSha,
          pageHeadings,
          renderedBlockCount: blockCount,
          renderedTableCount: tableCount,
          executableDomElementsInsideResult: executableNodes,
          attemptHistoryRowCount: verifiedAttemptRows.length,
          verifiedAttemptRows,
          downloadedFilename: dl.suggestedFilename(),
          downloadedByteLength: dlBytes.length,
          downloadedSha256: dlSha,
        });
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
            schema: 'eledgercare.wp-0006.saved-result-ui-verification/3',
            verifiedUtc: new Date().toISOString(),
            browserChannel: 'msedge',
            browserVersion,
            ngServePid: ngPid,
            ngServeStartedUtc: ngStartedUtc,
            uiPort,
            apiPort,
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

const isDirectEntry =
  process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url));

if (isDirectEntry) {
  runUiVerification(parseArgs(process.argv)).catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
