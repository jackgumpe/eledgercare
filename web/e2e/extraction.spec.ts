import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { createHash, randomUUID } from 'node:crypto';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { OwnedApi } from './owned-api';

const repoRoot = path.resolve(__dirname, '..', '..');
const f01Path = path.join(repoRoot, 'tests', 'fixtures', 'SYN-WO-01-v1-raster300.pdf');
const f01Bytes = readFileSync(f01Path);
const f01Sha = createHash('sha256').update(f01Bytes).digest('hex');

const f07Path = path.join(repoRoot, 'tests', 'fixtures', 'SYN-MP-01-v0-clean.pdf');
const f07Bytes = readFileSync(f07Path);
const f07Sha = createHash('sha256').update(f07Bytes).digest('hex');

const manifestSha = createHash('sha256')
  .update(readFileSync(path.join(repoRoot, 'workers', 'local_ocr', 'manifests', 'model-files.json')))
  .digest('hex');
const lockSha = createHash('sha256')
  .update(readFileSync(path.join(repoRoot, 'workers', 'local_ocr', 'manifests', 'dependency-lock.json')))
  .digest('hex');

const evidence: Record<string, unknown>[] = [];
const api = new OwnedApi();

test.describe.configure({ mode: 'serial' });

test.beforeAll(async () => {
  await api.start();
});

test.afterAll(async () => {
  await api.kill();
  const out = path.join(repoRoot, '.scratch', 'playwright');
  mkdirSync(out, { recursive: true });
  writeFileSync(
    path.join(out, 'f2-browser-evidence.json'),
    JSON.stringify({ f01Sha, f07Sha, apiProcesses: api.starts, checks: evidence }, null, 2),
  );
});

function runAppSql(sql: string): string {
  const settings = api.settings;
  const psql = path.join(repoRoot, '.local', 'tools', 'pgsql-18.7-1', 'bin', 'psql.exe');
  return execFileSync(
    psql,
    [
      '-X',
      '-q',
      '-A',
      '-t',
      '-v',
      'ON_ERROR_STOP=1',
      '-h',
      String(settings['host']),
      '-p',
      String(settings['port']),
      '-U',
      String(settings['appUser']),
      '-d',
      api.database,
      '-f',
      '-',
    ],
    {
      input: sql,
      encoding: 'utf8',
      env: { ...process.env, PGPASSWORD: String(settings['appPassword']) },
    },
  ).trim();
}

/** Deterministic minimal multi-page PDF 1.4 builder with exact byte-offset xref table. */
function buildMinimalPdf(pageCount: number): Buffer {
  const objects: string[] = [];
  const kids: string[] = [];
  for (let i = 0; i < pageCount; i++) {
    kids.push(`${3 + i * 2} 0 R`);
  }
  objects.push('1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n');
  objects.push(`2 0 obj\n<< /Type /Pages /Kids [${kids.join(' ')}] /Count ${pageCount} >>\nendobj\n`);
  for (let i = 0; i < pageCount; i++) {
    const pageObjNum = 3 + i * 2;
    const contentObjNum = pageObjNum + 1;
    const streamBody = `BT /F1 12 Tf 72 720 Td (Synthetic Page ${i + 1}) Tj ET\n`;
    objects.push(
      `${pageObjNum} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] ` +
        `/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> ` +
        `/Contents ${contentObjNum} 0 R >>\nendobj\n`,
    );
    objects.push(`${contentObjNum} 0 obj\n<< /Length ${Buffer.byteLength(streamBody, 'ascii')} >>\nstream\n${streamBody}endstream\nendobj\n`);
  }

  let pdf = '%PDF-1.4\n';
  const offsets: number[] = [0];
  for (const obj of objects) {
    offsets.push(Buffer.byteLength(pdf, 'ascii'));
    pdf += obj;
  }
  const xrefOffset = Buffer.byteLength(pdf, 'ascii');
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (let i = 1; i < offsets.length; i++) {
    pdf += `${String(offsets[i]).padStart(10, '0')} 00000 n \n`;
  }
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`;
  return Buffer.from(pdf, 'ascii');
}

test('F2-06: disabled-by-default worker shows honest unavailable notice, disabled action, and zero fabricated progress', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('file-input').setInputFiles(f01Path);
  await page.getByTestId('submit').click();
  await expect(page.getByTestId('receipt')).toBeVisible();
  const documentId = (await page.getByTestId('receipt-document-id').textContent())!.trim();

  await page.getByTestId('receipt-open').click();
  await expect(page).toHaveURL(new RegExp(`/documents/${documentId}$`));
  await expect(page.getByTestId('document-status')).toHaveText('Awaiting extraction');
  await expect(page.getByTestId('document-page-count')).toHaveText('1');
  await expect(page.getByTestId('extraction-unavailable')).toContainText('disabled');
  await expect(page.getByTestId('request-extraction')).toBeDisabled();
  await expect(page.getByText(/%\s*complete|extracted fields:|approved/i)).toHaveCount(0);

  evidence.push({
    check: 'F2-06 disabled-by-default UI',
    documentId,
    admittedPages: 1,
    requestExtractionDisabled: true,
  });
});

test('F2-06: 4-page PDF is admitted at intake and shows honest unsupported 1..3 page extraction profile', async ({ page }) => {
  const fourPagePdf = buildMinimalPdf(4);
  await page.goto('/');
  await page.getByTestId('file-input').setInputFiles({
    name: 'four-page-synthetic.pdf',
    mimeType: 'application/pdf',
    buffer: fourPagePdf,
  });
  await page.getByTestId('submit').click();
  await expect(page.getByTestId('receipt')).toBeVisible();
  const documentId = (await page.getByTestId('receipt-document-id').textContent())!.trim();

  await page.getByTestId('receipt-open').click();
  await expect(page.getByTestId('document-page-count')).toHaveText('4');
  await expect(page.getByTestId('extraction-unsupported')).toContainText('1 to 3 pages');
  await expect(page.getByTestId('request-extraction')).toBeDisabled();

  evidence.push({
    check: 'F2-06 unsupported 4-page profile UI',
    documentId,
    admittedPages: 4,
    requestExtractionDisabled: true,
  });
});

test('F2-03: failed attempt displays failure details, attempt history, and sends explicit retryAttemptId on retry', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('file-input').setInputFiles(f01Path);
  await page.getByTestId('submit').click();
  await expect(page.getByTestId('receipt')).toBeVisible();
  const documentId = (await page.getByTestId('receipt-document-id').textContent())!.trim();
  const jobId = runAppSql(`SELECT job_id::text FROM eledgercare.processing_jobs WHERE document_id = '${documentId}';`);
  const attempt1Id = randomUUID();

  // Persist Attempt #1 as failed using the runtime app role (proving column-scoped grants work).
  runAppSql(`
    BEGIN;
    SELECT nextval('eledgercare.extraction_fencing_seq');
    UPDATE eledgercare.processing_jobs
       SET status = 'queued', queued_at = now(), updated_at = now()
     WHERE job_id = '${jobId}';
    UPDATE eledgercare.processing_jobs
       SET status = 'running', attempt_count = 1, latest_fencing_token = currval('eledgercare.extraction_fencing_seq'), updated_at = now()
     WHERE job_id = '${jobId}';
    INSERT INTO eledgercare.execution_attempts (
      attempt_id, job_id, document_id, attempt_number, fencing_token, retried_from_attempt_id,
      status, phase, run_directory_name, supervisor_instance_id, supervisor_pid, supervisor_create_filetime,
      started_at, last_heartbeat_at
    ) VALUES (
      '${attempt1Id}', '${jobId}', '${documentId}', 1, currval('eledgercare.extraction_fencing_seq'), NULL,
      'running', 'inferring', 'attempt-${attempt1Id}', '${randomUUID()}', 4242, 133700000000004242,
      now(), now()
    );
    UPDATE eledgercare.processing_jobs
       SET status = 'failed', updated_at = now()
     WHERE job_id = '${jobId}' AND latest_fencing_token = currval('eledgercare.extraction_fencing_seq');
    UPDATE eledgercare.execution_attempts
       SET status = 'failed', phase = 'failed', ended_at = now(), last_heartbeat_at = now(),
           exit_code = 2, failure_code = 'model_output_truncated',
           failure_detail = 'Model generation stopped before completion (length limit reached).'
     WHERE attempt_id = '${attempt1Id}';
    COMMIT;
  `);

  // Temporarily run OwnedApi with empty temp roots so Retry button is enabled and Attempt #2 executes CPU-only root failure.
  const dummyQ0 = mkdtempSync(path.join(os.tmpdir(), 'elc-e2e-q0-'));
  const dummyRt = mkdtempSync(path.join(os.tmpdir(), 'elc-e2e-rt-'));
  try {
    await api.kill();
    await api.start({
      LocalOcr__Enabled: 'true',
      LocalOcr__ReadOnlyQ0Root: dummyQ0,
      LocalOcr__WritableRuntimeRoot: dummyRt,
      LocalOcr__LeasedGpuUuid: 'GPU-00000000-0000-0000-0000-000000000000',
    });

    await page.goto(`/documents/${documentId}`);
    await expect(page.getByTestId('document-status')).toHaveText('Extraction failed');
    await expect(page.getByTestId('extraction-failure')).toContainText('model_output_truncated');
    await expect(page.getByTestId('attempt-row-1')).toBeAttached();

    const retryReqPromise = page.waitForRequest(
      (req) => req.method() === 'POST' && new URL(req.url()).pathname === `/api/documents/${documentId}/extraction`,
    );
    await page.getByTestId('retry-extraction').click();
    const retryReq = await retryReqPromise;
    expect(retryReq.postDataJSON()).toEqual({ retryAttemptId: attempt1Id });

    // Attempt #2 runs against the empty temp Q0 dir (missing venv python -> supervisor_launch_failed), retaining Attempt #1!
    await expect(page.getByTestId('attempt-row-2')).toBeAttached({ timeout: 15_000 });
    await page.getByTestId('attempt-history').locator('summary').click();
    await expect(page.getByTestId('attempt-row-1')).toContainText('1');
    await expect(page.getByTestId('attempt-row-2')).toContainText('2');

    evidence.push({
      check: 'F2-03 explicit retry UI + history retention',
      documentId,
      retriedAttemptId: attempt1Id,
      observedAttemptRows: 2,
    });
  } finally {
    await api.kill();
    rmSync(dummyQ0, { recursive: true, force: true });
    rmSync(dummyRt, { recursive: true, force: true });
    await api.start(); // Restore default LocalOcr:Enabled=false for subsequent tests.
  }
});

test('F2-05 / F2-BIC-04: saved 3-page unreviewed result renders in order with inert hostile markup and survives API restart', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('file-input').setInputFiles(f07Path);
  await page.getByTestId('submit').click();
  await expect(page.getByTestId('receipt')).toBeVisible();
  const documentId = (await page.getByTestId('receipt-document-id').textContent())!.trim();
  const jobId = runAppSql(`SELECT job_id::text FROM eledgercare.processing_jobs WHERE document_id = '${documentId}';`);

  const rawText =
    '<PAGE>\n' +
    '<BLOCK>title[[61,43,390,63]]<FORK>MAINTENANCE PACKET SYN-MP-01\n' +
    "<BLOCK>text[[61,80,520,100]]<FORK>Hostile script check: <script>window.__f2_xss = 'script'</script>\n" +
    '<PAGE>\n' +
    '<BLOCK>table[[61,120,760,260]]<FORK><table><tr><th>Step</th><th>Observation</th></tr>' +
    '<tr><td>Inspect &amp; Torque</td><td><img src=x onerror="window.__f2_xss = \'img\'">Seal intact</td></tr></table>\n' +
    '<PAGE>\n' +
    '<BLOCK>text[[61,110,480,135]]<FORK>Page 3 Sign-off: Saved Unreviewed Output\n';

  const rawBytes = Buffer.from(rawText, 'utf8');
  const rawHex = rawBytes.toString('hex');
  const rawShaHex = createHash('sha256').update(rawBytes).digest('hex');
  const workerShaHex = createHash('sha256').update('stage1-seeded-worker').digest('hex');
  const configShaHex = createHash('sha256').update('stage1-seeded-config').digest('hex');
  const attemptId = randomUUID();
  const resultId = randomUUID();

  runAppSql(`
    BEGIN;
    SELECT nextval('eledgercare.extraction_fencing_seq');
    UPDATE eledgercare.processing_jobs
       SET status = 'queued', queued_at = now(), updated_at = now()
     WHERE job_id = '${jobId}';
    UPDATE eledgercare.processing_jobs
       SET status = 'running', attempt_count = 1, latest_fencing_token = currval('eledgercare.extraction_fencing_seq'), updated_at = now()
     WHERE job_id = '${jobId}';
    INSERT INTO eledgercare.execution_attempts (
      attempt_id, job_id, document_id, attempt_number, fencing_token, retried_from_attempt_id,
      status, phase, run_directory_name, supervisor_instance_id, supervisor_pid, supervisor_create_filetime,
      started_at, last_heartbeat_at
    ) VALUES (
      '${attemptId}', '${jobId}', '${documentId}', 1, currval('eledgercare.extraction_fencing_seq'), NULL,
      'running', 'inferring', 'attempt-${attemptId}', '${randomUUID()}', 5151, 133700000000005151,
      now(), now()
    );
    UPDATE eledgercare.processing_jobs
       SET status = 'completed', updated_at = now()
     WHERE job_id = '${jobId}' AND latest_fencing_token = currval('eledgercare.extraction_fencing_seq');
    UPDATE eledgercare.execution_attempts
       SET status = 'completed', phase = 'completed', ended_at = now(), last_heartbeat_at = now(), exit_code = 0
     WHERE attempt_id = '${attemptId}';
    INSERT INTO eledgercare.extraction_results (
      result_id, document_id, job_id, attempt_id, fencing_token, schema_version,
      input_sha256, input_byte_length, page_count, raw_output_bytes, raw_output_byte_length, raw_output_sha256,
      model_repo_id, model_revision, model_manifest_sha256, dependency_lock_sha256, worker_source_digest, worker_config_digest,
      renderer_identity, generation_settings_json, finish_reason, output_page_count,
      started_at, completed_at, load_duration_ms, render_duration_ms, infer_duration_ms, total_duration_ms, diagnostic_metadata_json
    ) VALUES (
      '${resultId}', '${documentId}', '${jobId}', '${attemptId}', currval('eledgercare.extraction_fencing_seq'), 'eledgercare.local-extraction/1',
      decode('${f07Sha}', 'hex'), ${f07Bytes.length}, 3, decode('${rawHex}', 'hex'), ${rawBytes.length}, decode('${rawShaHex}', 'hex'),
      'baidu/Unlimited-OCR-2', '0480966938291445591f69f08a13b041c073a96a',
      decode('${manifestSha}', 'hex'), decode('${lockSha}', 'hex'), decode('${workerShaHex}', 'hex'), decode('${configShaHex}', 'hex'),
      'pypdfium2==5.15.2 (PDFium 159.0.8149.0)', '{"temperature":0.0,"max_new_tokens":24000}'::jsonb, 'stop', 3,
      now() - interval '5 seconds', now(), 1100, 95, 3805, 5000, '{"fallback_used":false}'::jsonb
    );
    COMMIT;
  `);

  // Verify saved result opens while LocalOcr:Enabled=false, with inert hostile markup and exact page order.
  await page.goto(`/documents/${documentId}`);
  await expect(page.getByTestId('document-status')).toHaveText('Completed (unreviewed)');
  await expect(page.getByTestId('unreviewed-banner')).toContainText('unreviewed');
  await expect(page.getByTestId('extraction-unavailable')).toHaveCount(0);
  await expect(page.getByTestId('result-model')).toContainText('baidu/Unlimited-OCR-2 @ 0480966938291445591f69f08a13b041c073a96a');
  await expect(page.getByTestId('result-raw-sha256')).toHaveText(rawShaHex);

  const pageHeadings = await page.locator('[data-testid^="result-page-"] h4').allTextContents();
  expect(pageHeadings).toEqual(['Page 1 of 3', 'Page 2 of 3', 'Page 3 of 3']);

  await expect(page.getByTestId('result-page-1')).toContainText("<script>window.__f2_xss = 'script'</script>");
  await expect(page.getByTestId('result-page-2-table-0')).toContainText('Inspect & Torque');
  await expect(page.getByTestId('result-page-2-table-0')).toContainText('<img src=x onerror="window.__f2_xss = \'img\'">Seal intact');
  await expect(page.getByTestId('result-page-3')).toContainText('Page 3 Sign-off: Saved Unreviewed Output');

  // Prove zero executable DOM elements (<script>, <img>) were created inside extraction-result and no JS ran.
  await expect(page.locator('[data-testid="extraction-result"] script, [data-testid="extraction-result"] img')).toHaveCount(0);
  const xssValue = await page.evaluate(() => (window as unknown as Record<string, unknown>)['__f2_xss']);
  expect(xssValue).toBeUndefined();

  await page.getByTestId('result-raw-details').locator('summary').click();
  await expect(page.getByTestId('result-raw-text')).toHaveText(rawText);

  // Restart OwnedApi (new PID, LocalOcr:Enabled=false) and reopen without re-running OCR!
  const pidBefore = api.starts[api.starts.length - 1].pid;
  await api.kill();
  await api.start();
  const pidAfter = api.starts[api.starts.length - 1].pid;
  expect(pidAfter).not.toBe(pidBefore);

  await page.reload();
  await expect(page.getByTestId('document-status')).toHaveText('Completed (unreviewed)');
  await expect(page.getByTestId('result-raw-sha256')).toHaveText(rawShaHex);

  const dlPromise = page.waitForEvent('download');
  await page.getByTestId('document-download').click();
  const dl = await dlPromise;
  const dlBytes = readFileSync((await dl.path())!);
  expect(Buffer.compare(dlBytes, f07Bytes)).toBe(0);

  evidence.push({
    check: 'F2-05 / F2-BIC-04 3-page saved result + XSS inertness + API restart reopen',
    documentId,
    resultId,
    rawSha256: rawShaHex,
    xssExecuted: false,
    apiPidBefore: pidBefore,
    apiPidAfter: pidAfter,
    originalBytesEqualAfterRestart: true,
  });
});
