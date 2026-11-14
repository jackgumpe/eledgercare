import { Page, Request, expect, test } from '@playwright/test';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import { OwnedApi } from './owned-api';

const fixturePath = path.resolve(__dirname, '..', '..', 'tests', 'fixtures', 'F1-SWO-001.pdf');
const fixtureBytes = readFileSync(fixturePath);
const fixtureSha = createHash('sha256').update(fixtureBytes).digest('hex');
const evidence: Record<string, unknown>[] = [];
const api = new OwnedApi();

test.describe.configure({ mode: 'serial' });

test.beforeAll(async () => {
  await api.start();
});

test.afterAll(async () => {
  await api.kill();
  const out = path.resolve(__dirname, '..', '..', '.scratch', 'playwright');
  mkdirSync(out, { recursive: true });
  writeFileSync(path.join(out, 'browser-evidence.json'), JSON.stringify({ fixtureSha, apiProcesses: api.starts, checks: evidence }, null, 2));
});

async function pendingFromStorage(page: Page): Promise<{ key: string; uncertain: boolean } | null> {
  const raw = await page.evaluate(() => sessionStorage.getItem('eledgercare.pendingSubmission'));
  return raw ? (JSON.parse(raw) as { key: string; uncertain: boolean }) : null;
}

function isIntakePost(request: Request): boolean {
  return request.method() === 'POST' && new URL(request.url()).pathname === '/api/documents';
}

test('DI-01/02/03/04: receipt shows committed reference, honest status, exact download, reopen after API restart', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('file-input').setInputFiles(fixturePath);
  const postSeen = page.waitForRequest(isIntakePost);
  await page.getByTestId('submit').click();
  const post = await postSeen;
  const response = await post.response();

  await expect(page.getByTestId('receipt')).toBeVisible();
  expect(response?.status()).toBe(201);
  const documentId = (await page.getByTestId('receipt-document-id').textContent())!.trim();
  await expect(page.getByTestId('receipt-status')).toHaveText('Awaiting extraction');
  await expect(page.getByTestId('receipt-sha256')).toHaveText(fixtureSha);
  await expect(page.getByTestId('receipt-byte-length')).toHaveText(`${fixtureBytes.length} bytes`);
  await expect(page.getByText(/extracted fields:|OCR complete|% complete/i)).toHaveCount(0);
  expect(await pendingFromStorage(page)).toBeNull();
  const storageDump = await page.evaluate(() => JSON.stringify({ ...sessionStorage, ...localStorage }));
  expect(storageDump).not.toContain('%PDF');

  // DI-02: real browser download compared byte-for-byte and by recomputed SHA-256.
  const downloadSeen = page.waitForEvent('download');
  await page.getByTestId('receipt-download').click();
  const download = await downloadSeen;
  const downloaded = readFileSync((await download.path())!);
  expect(download.suggestedFilename()).toBe(`document-${documentId}.pdf`);
  expect(Buffer.compare(downloaded, fixtureBytes)).toBe(0);
  expect(createHash('sha256').update(downloaded).digest('hex')).toBe(fixtureSha);

  // Document route survives a browser reload.
  await page.getByTestId('receipt-open').click();
  await expect(page).toHaveURL(new RegExp(`/documents/${documentId}$`));
  await page.reload();
  await expect(page.getByTestId('document-status')).toHaveText('Awaiting extraction');

  // DI-04 (browser view): terminate the owned API process, start a new one, reopen by reference.
  const before = api.starts[api.starts.length - 1].pid;
  await api.kill();
  await api.start();
  const after = api.starts[api.starts.length - 1].pid;
  expect(after).not.toBe(before);
  await page.goto('/');
  await page.getByTestId('reopen-input').fill(documentId);
  await page.getByTestId('reopen').click();
  await expect(page.getByTestId('document-id')).toHaveText(documentId);
  await expect(page.getByTestId('document-status')).toHaveText('Awaiting extraction');
  await expect(page.getByTestId('document-sha256')).toHaveText(fixtureSha);
  const reDownloadSeen = page.waitForEvent('download');
  await page.getByTestId('document-download').click();
  const reDownloaded = readFileSync((await (await reDownloadSeen).path())!);
  expect(Buffer.compare(reDownloaded, fixtureBytes)).toBe(0);

  evidence.push({
    check: 'DI-01/02/03/04 browser',
    postStatus: response?.status(),
    documentId,
    status: 'Awaiting extraction',
    downloadedSha256: createHash('sha256').update(downloaded).digest('hex'),
    downloadName: download.suggestedFilename(),
    apiPidBeforeRestart: before,
    apiPidAfterRestart: after,
    reopenedAfterRestartSha256: createHash('sha256').update(reDownloaded).digest('hex'),
  });
});

test('DI-06: a 5xx after a real commit shows outcome unknown, keeps the key across reload, and reconciles', async ({ page }) => {
  let realStatus = 0;
  let sentKey = '';
  await page.route('**/api/documents', async (route) => {
    if (route.request().method() !== 'POST') {
      return route.fallback();
    }
    sentKey = route.request().headers()['idempotency-key'];
    const real = await route.fetch(); // the server really commits
    realStatus = real.status();
    await route.fulfill({ status: 500, contentType: 'application/problem+json', body: JSON.stringify({ title: 'Unexpected server error', status: 500 }) });
  });

  await page.goto('/');
  await page.getByTestId('file-input').setInputFiles(fixturePath);
  await page.getByTestId('submit').click();
  await expect(page.getByTestId('outcome-unknown')).toBeVisible();
  expect(realStatus).toBe(201);
  await expect(page.getByTestId('pending-key')).toHaveText(sentKey);
  expect(await pendingFromStorage(page)).toEqual({ key: sentKey, uncertain: true });

  await page.unroute('**/api/documents');
  await page.reload();
  await expect(page.getByTestId('outcome-unknown')).toBeVisible();
  await expect(page.getByTestId('pending-key')).toHaveText(sentKey);

  await page.getByTestId('check-status').click();
  await expect(page.getByTestId('receipt')).toBeVisible();
  await expect(page.getByTestId('receipt-status')).toHaveText('Awaiting extraction');
  expect(await pendingFromStorage(page)).toBeNull();
  evidence.push({ check: 'DI-06 browser 5xx', serverCommitStatus: realStatus, shownToUser: 500, keyRetainedAcrossReload: true, reconciledBy: 'GET /api/submissions/{key}', key: sentKey });
});

test('DI-06: a 429 keeps the pending key and the same-key retry succeeds', async ({ page }) => {
  const keys: string[] = [];
  let first = true;
  await page.route('**/api/documents', async (route) => {
    if (route.request().method() !== 'POST') {
      return route.fallback();
    }
    keys.push(route.request().headers()['idempotency-key']);
    if (first) {
      first = false;
      return route.fulfill({ status: 429, contentType: 'application/problem+json', body: JSON.stringify({ title: 'Too many concurrent submissions', status: 429, code: 'admission_busy' }) });
    }
    return route.fallback();
  });

  await page.goto('/');
  await page.getByTestId('file-input').setInputFiles(fixturePath);
  await page.getByTestId('submit').click();
  await expect(page.getByTestId('busy')).toBeVisible();
  const pending = await pendingFromStorage(page);
  expect(pending?.key).toBe(keys[0]);
  expect(pending?.uncertain).toBe(false);

  await page.getByTestId('submit').click();
  await expect(page.getByTestId('receipt')).toBeVisible();
  expect(keys).toHaveLength(2);
  expect(keys[1]).toBe(keys[0]);
  evidence.push({ check: 'DI-06 browser 429', keys, sameKeyRetried: keys[0] === keys[1] });
});

test('DI-06: an earlier uncertain outcome is not resolved by a later 429', async ({ page }) => {
  const keys: string[] = [];
  let attempt = 0;
  await page.route('**/api/documents', async (route) => {
    if (route.request().method() !== 'POST') {
      return route.fallback();
    }
    keys.push(route.request().headers()['idempotency-key']);
    attempt++;
    if (attempt === 1) {
      return route.abort('failed'); // network error: outcome unknown
    }
    if (attempt === 2) {
      return route.fulfill({ status: 429, contentType: 'application/problem+json', body: JSON.stringify({ title: 'busy', status: 429 }) });
    }
    return route.fallback();
  });

  await page.goto('/');
  await page.getByTestId('file-input').setInputFiles(fixturePath);
  await page.getByTestId('submit').click();
  await expect(page.getByTestId('outcome-unknown')).toBeVisible();
  await page.getByTestId('submit').click();
  await expect(page.getByTestId('outcome-unknown')).toBeVisible();
  await expect(page.getByTestId('busy')).toHaveCount(0);
  expect((await pendingFromStorage(page))?.uncertain).toBe(true);

  // Nothing reached the server, so the status query honestly reports no committed submission yet.
  await page.getByTestId('check-status').click();
  await expect(page.getByTestId('message')).toContainText('No committed submission uses this key');
  await page.getByTestId('submit').click();
  await expect(page.getByTestId('receipt')).toBeVisible();
  expect(new Set(keys).size).toBe(1);
  evidence.push({ check: 'DI-06 browser uncertainty then 429', attempts: keys.length, singleKey: new Set(keys).size === 1 });
});

test('double click cannot mint a second key and a new submission is explicit', async ({ page }) => {
  const keys: string[] = [];
  page.on('request', (request) => {
    if (isIntakePost(request)) {
      keys.push(request.headers()['idempotency-key']);
    }
  });
  await page.goto('/');
  await page.getByTestId('file-input').setInputFiles(fixturePath);
  await page.getByTestId('submit').dblclick();
  await expect(page.getByTestId('receipt')).toBeVisible();
  expect(keys).toHaveLength(1);

  await page.getByTestId('new-submission').click();
  await page.getByTestId('file-input').setInputFiles(fixturePath);
  await page.getByTestId('submit').click();
  await expect(page.getByTestId('receipt')).toBeVisible();
  expect(keys).toHaveLength(2);
  expect(keys[1]).not.toBe(keys[0]);
  evidence.push({ check: 'double click / explicit new submission', keys });
});

test('invalid file is rejected definitively without a fabricated receipt', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('file-input').setInputFiles({ name: 'not-a-pdf.pdf', mimeType: 'application/pdf', buffer: Buffer.from('plain text, not a PDF\n') });
  await page.getByTestId('submit').click();
  await expect(page.getByTestId('message')).toContainText('%PDF-1.0 to %PDF-1.7');
  await expect(page.getByTestId('receipt')).toHaveCount(0);
  expect(await pendingFromStorage(page)).toBeNull();
  evidence.push({ check: 'browser 422 rejection', receiptShown: false });
});
