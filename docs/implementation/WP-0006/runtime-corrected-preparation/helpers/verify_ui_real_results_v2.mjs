import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import net from 'node:net';
import path from 'node:path';

/**
 * Versioned Stage 2 real-result Microsoft Edge UI verifier v2 (eld-f2-implementer, WP-0006).
 * Starts Angular ng serve directly on owned loopback 127.0.0.1:4210 proxying to 127.0.0.1:5190,
 * opens real persisted extraction documents in headless Microsoft Edge, verifies unreviewed banner,
 * pinned model provenance, exact page ordering, inert plain-text/table DOM, raw UTF-8 SHA-256,
 * attempt history rows/statuses, and byte-for-byte original PDF download, then stops only its
 * spawned ng serve node process and confirms loopback port release.
 */
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
    throw new Error('Usage: node verify_ui_real_results_v2.mjs --repoRoot <dir> --input <in.json> --output <out.json>');
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
        await page.goto(`http://127.0.0.1:${uiPort}/documents/${item.documentId}`, { waitUntil: 'domcontentloaded' });
        await page.getByTestId('document-status').waitFor({ state: 'visible', timeout: 30_000 });
        await page.getByTestId('extraction-result').waitFor({ state: 'visible', timeout: 30_000 });

        const docStatus = (await page.getByTestId('document-status').textContent())?.trim();
        if (docStatus !== 'Completed (unreviewed)') {
          throw new Error(`Document ${item.documentId} UI status '${docStatus}' != 'Completed (unreviewed)'`);
        }

        const bannerText = (await page.getByTestId('unreviewed-banner').textContent())?.trim() ?? '';
        if (!bannerText.toLowerCase().includes('unreviewed')) {
          throw new Error(`Unreviewed banner missing expected label on ${item.documentId}`);
        }

        const unavailableCount = await page.getByTestId('extraction-unavailable').count();
        if (unavailableCount !== 0) {
          throw new Error(`Completed document ${item.documentId} unexpectedly showed extraction-unavailable banner`);
        }

        const modelText = (await page.getByTestId('result-model').textContent())?.trim() ?? '';
        if (!modelText.includes('baidu/Unlimited-OCR-2') || !modelText.includes('0480966938291445591f69f08a13b041c073a96a')) {
          throw new Error(`Model checkpoint provenance unexpected on ${item.documentId}: '${modelText}'`);
        }

        const rendererText = (await page.getByTestId('result-renderer').textContent())?.trim() ?? '';
        const uiRawSha = (await page.getByTestId('result-raw-sha256').textContent())?.trim() ?? '';
        if (uiRawSha !== item.expectedRawSha256) {
          throw new Error(`UI rawSha256 ${uiRawSha} != expected ${item.expectedRawSha256}`);
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
        const rawTextUiSha = createHash('sha256').update(Buffer.from(rawTextUi, 'utf8')).digest('hex');
        if (rawTextUiSha !== item.expectedRawSha256) {
          throw new Error(`Rendered raw-text SHA-256 ${rawTextUiSha} != ${item.expectedRawSha256}`);
        }

        await page.getByTestId('attempt-history').locator('summary').click();
        const attemptRows = [];
        for (let n = 1; n <= item.expectedAttemptCount; n++) {
          const rowText = (await page.getByTestId(`attempt-row-${n}`).textContent())?.trim() ?? '';
          if (Array.isArray(item.expectedAttemptStatuses) && item.expectedAttemptStatuses[n - 1]) {
            const wantStatus = item.expectedAttemptStatuses[n - 1];
            if (!rowText.includes(wantStatus)) {
              throw new Error(`Attempt row #${n} ('${rowText}') missing expected status '${wantStatus}'`);
            }
          }
          attemptRows.push(rowText);
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
          label: item.label,
          statusText: docStatus,
          unreviewedBannerVisible: true,
          modelText,
          rendererText,
          uiRawSha256: uiRawSha,
          rawPreElementSha256: rawTextUiSha,
          pageHeadings,
          renderedBlockCount: blockCount,
          renderedTableCount: tableCount,
          executableDomElementsInsideResult: executableNodes,
          attemptHistoryRowCount: attemptRows.length,
          attemptRowsSummary: attemptRows,
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
            schema: 'eledgercare.wp-0006.ui-verification/2',
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

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
