import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import net from 'node:net';
import path from 'node:path';

/**
 * Independent Stage 2 real-result Microsoft Edge UI verifier (eld-next-reviewer, WP-0006).
 * Structurally informed by eld-f2-implementer's verify_ui_real_results_v2.mjs (5b33924b...) with
 * attribution preserved; independently owned by eld-next-reviewer for reviewer ports (UI 4310 -> API 5290)
 * and stricter inert-DOM, trigger-gating, provenance, and attempt-history assertions.
 *
 * Starts Angular ng serve on owned loopback 127.0.0.1:4310 proxying to 127.0.0.1:5290, opens real
 * persisted extraction documents in headless Microsoft Edge, verifies:
 *   1. 'Completed (unreviewed)' status & explicit unreviewed banner (F2-05), zero unavailable banner;
 *   2. Trigger/retry action buttons absent or disabled on completed saved results when OCR is disabled;
 *   3. Pinned baidu/Unlimited-OCR-2 @ 0480966938291445591f69f08a13b041c073a96a & pypdfium2 5.15.2 / PDFium 159.0.8149.0;
 *   4. Exact 1..N page ordering ('Page k of N');
 *   5. Inert plain-text/table DOM (zero <script>, <img>, <iframe>, <object>, <embed>, <svg>, <link>, <style>, or inline on* handlers);
 *   6. Exact UTF-8 SHA-256 of rendered <pre data-testid="result-raw-text"> matching DB/disk raw output;
 *   7. Exact attempt-history count and ordered per-attempt statuses (including preserved 'Interrupted' before 'Completed');
 *   8. Byte-for-byte SHA-256 and length parity of downloaded original PDF.
 * Stops only its own spawned ng serve child process and confirms 127.0.0.1:4310 release on exit.
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
    throw new Error(
      'Usage: node verify_ui_reviewer_real_results.mjs --repoRoot <dir> --input <in.json> --output <out.json>',
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
    throw new Error(`Reviewer UI verifier requires owned loopback ports UI=4310 / API=5290, got UI=${uiPort} / API=${apiPort}`);
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
        await page.goto(`http://127.0.0.1:${uiPort}/documents/${item.documentId}`, { waitUntil: 'domcontentloaded' });
        await page.getByTestId('document-status').waitFor({ state: 'visible', timeout: 30_000 });
        await page.getByTestId('extraction-result').waitFor({ state: 'visible', timeout: 30_000 });

        const docStatus = (await page.getByTestId('document-status').textContent())?.trim();
        if (docStatus !== 'Completed (unreviewed)') {
          throw new Error(`Document ${item.documentId} UI status '${docStatus}' != 'Completed (unreviewed)'`);
        }

        const bannerText = (await page.getByTestId('unreviewed-banner').textContent())?.trim() ?? '';
        if (!bannerText.toLowerCase().includes('unreviewed')) {
          throw new Error(`Unreviewed banner missing expected label on ${item.documentId}: '${bannerText}'`);
        }

        const unavailableCount = await page.getByTestId('extraction-unavailable').count();
        if (unavailableCount !== 0) {
          throw new Error(`Completed document ${item.documentId} unexpectedly showed extraction-unavailable banner`);
        }

        const triggerButtonsVisible = await page
          .locator('[data-testid="trigger-extraction"], [data-testid="retry-extraction"]')
          .count();
        if (triggerButtonsVisible !== 0) {
          throw new Error(
            `Completed document ${item.documentId} unexpectedly rendered ${triggerButtonsVisible} trigger/retry button(s)`,
          );
        }

        const modelText = (await page.getByTestId('result-model').textContent())?.trim() ?? '';
        if (
          !modelText.includes('baidu/Unlimited-OCR-2') ||
          !modelText.includes('0480966938291445591f69f08a13b041c073a96a')
        ) {
          throw new Error(`Model checkpoint provenance unexpected on ${item.documentId}: '${modelText}'`);
        }

        const rendererText = (await page.getByTestId('result-renderer').textContent())?.trim() ?? '';
        if (!rendererText.includes('pypdfium2==5.15.2') || !rendererText.includes('159.0.8149.0')) {
          throw new Error(`Renderer provenance unexpected on ${item.documentId}: '${rendererText}'`);
        }

        const uiRawSha = (await page.getByTestId('result-raw-sha256').textContent())?.trim() ?? '';
        if (uiRawSha !== item.expectedRawSha256) {
          throw new Error(`UI rawSha256 ${uiRawSha} != expected ${item.expectedRawSha256}`);
        }

        const pageHeadings = await page.locator('[data-testid^="result-page-"] h4').allTextContents();
        const wantHeadings = Array.from(
          { length: item.expectedPages },
          (_, idx) => `Page ${idx + 1} of ${item.expectedPages}`,
        );
        if (JSON.stringify(pageHeadings) !== JSON.stringify(wantHeadings)) {
          throw new Error(`Page headings ${JSON.stringify(pageHeadings)} != ${JSON.stringify(wantHeadings)}`);
        }

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
        if (domSafety.forbiddenTagCount !== 0 || domSafety.inlineEventAttrCount !== 0) {
          throw new Error(`Unsafe DOM inside extraction-result on ${item.documentId}: ${JSON.stringify(domSafety)}`);
        }

        const tableCount = await page.locator('[data-testid="extraction-result"] table.grid-table').count();
        const blockCount = await page
          .locator(
            '[data-testid="extraction-result"] p.extracted-title, [data-testid="extraction-result"] p.extracted-line, [data-testid="extraction-result"] table.grid-table',
          )
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
        const totalRenderedAttemptRows = await page.locator('[data-testid^="attempt-row-"]').count();
        if (totalRenderedAttemptRows !== item.expectedAttemptCount) {
          throw new Error(
            `Expected ${item.expectedAttemptCount} attempt-history rows on ${item.documentId}, found ${totalRenderedAttemptRows}`,
          );
        }
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
          throw new Error(
            `Downloaded original mismatch on ${item.documentId}: sha=${dlSha}, len=${dlBytes.length}`,
          );
        }

        results.push({
          documentId: item.documentId,
          label: item.label,
          expectOcrDisabled,
          statusText: docStatus,
          unreviewedBannerVisible: true,
          triggerOrRetryButtonsCount: triggerButtonsVisible,
          modelText,
          rendererText,
          uiRawSha256: uiRawSha,
          rawPreElementSha256: rawTextUiSha,
          pageHeadings,
          renderedBlockCount: blockCount,
          renderedTableCount: tableCount,
          forbiddenDomTagCount: domSafety.forbiddenTagCount,
          inlineEventAttrCount: domSafety.inlineEventAttrCount,
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
            schema: 'eledgercare.wp-0006.reviewer-ui-verification/1',
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

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
