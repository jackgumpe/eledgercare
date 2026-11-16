import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { createHash, randomUUID } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { OwnedApi } from './owned-api';

/**
 * WP-0008 F3 Microsoft Edge Playwright E2E acceptance suite covering F3-01..06 and F3-BIC-01..06
 * with LocalOcr:Enabled=false and zero GPU/model calls.
 * Seeds attributed genuine accepted F2 evidence (SYN-WO-01-v1-raster300 & SYN-MP-01-v0-clean)
 * through the runtime eledgercare_app role while advancing eledgercare.extraction_fencing_seq.
 */
const repoRoot = path.resolve(__dirname, '..', '..');

const woPdfPath = path.join(repoRoot, 'tests', 'fixtures', 'SYN-WO-01-v1-raster300.pdf');
const woPdfBytes = readFileSync(woPdfPath);
const woPdfSha = createHash('sha256').update(woPdfBytes).digest('hex');

const woRunDir = path.join(
  repoRoot,
  'docs',
  'reviews',
  'WP-0006',
  'eld-next-reviewer',
  'runtime-execution',
  'runs',
  'attempt-01a1e571-297a-7f0e-a293-e9e1c0851cd4',
  'output',
);
const woRawBytes = readFileSync(path.join(woRunDir, 'raw_output.utf8.bin'));
const woRawSha = createHash('sha256').update(woRawBytes).digest('hex');
const woEnvelope = JSON.parse(readFileSync(path.join(woRunDir, 'envelope.json'), 'utf8')) as Record<string, unknown>;

const mpPdfPath = path.join(repoRoot, 'tests', 'fixtures', 'SYN-MP-01-v0-clean.pdf');
const mpPdfBytes = readFileSync(mpPdfPath);
const mpPdfSha = createHash('sha256').update(mpPdfBytes).digest('hex');

const mpRunDir = path.join(
  repoRoot,
  'docs',
  'reviews',
  'WP-0006',
  'eld-next-reviewer',
  'runtime-execution',
  'runs',
  'attempt-01a1e573-ca25-733e-b048-44c8ea2ac61d',
  'output',
);
const mpRawBytes = readFileSync(path.join(mpRunDir, 'raw_output.utf8.bin'));
const mpRawSha = createHash('sha256').update(mpRawBytes).digest('hex');
const mpEnvelope = JSON.parse(readFileSync(path.join(mpRunDir, 'envelope.json'), 'utf8')) as Record<string, unknown>;

const evidence: Record<string, unknown>[] = [];
const api = new OwnedApi();
const screenshotOutDir =
  process.env['ELEDGERCARE_F3_SCREENSHOT_DIR'] ?? path.join(repoRoot, '.scratch', 'playwright', 'f3-screenshots');

test.describe.configure({ mode: 'serial' });

test.beforeAll(async () => {
  expect(woPdfBytes.length).toBe(372258);
  expect(woPdfSha).toBe('47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd');
  expect(woRawBytes.length).toBe(3236);
  expect(woRawSha).toBe('7503761ae46afef6adf579881d011764283474354fac3e185598fc7d266aff95');
  expect(mpPdfBytes.length).toBe(8422);
  expect(mpPdfSha).toBe('15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3');
  expect(mpRawBytes.length).toBe(7511);
  expect(mpRawSha).toBe('c399ad892e257500e2b6a9ac8b0bc3d8a17e9c10041262c4bca6a48fb9b9b639');

  mkdirSync(screenshotOutDir, { recursive: true });
  await api.start();
});

test.afterAll(async () => {
  await api.kill();
  const out = path.join(repoRoot, '.scratch', 'playwright');
  mkdirSync(out, { recursive: true });
  writeFileSync(
    path.join(out, 'f3-browser-evidence.json'),
    JSON.stringify({ woPdfSha, woRawSha, mpPdfSha, mpRawSha, apiProcesses: api.starts, checks: evidence }, null, 2),
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

interface SeededIds {
  documentId: string;
  jobId: string;
  attemptId: string;
  resultId: string;
}

function seedGenuineCompletedResult(
  pdfBytes: Buffer,
  pdfShaHex: string,
  rawBytes: Buffer,
  rawShaHex: string,
  envelope: Record<string, unknown>,
  preserveOriginalIds: boolean,
  originalResultId: string,
): SeededIds {
  const documentId = preserveOriginalIds ? String(envelope['document_id']) : randomUUID();
  const jobId = preserveOriginalIds ? String(envelope['job_id']) : randomUUID();
  const attemptId = preserveOriginalIds ? String(envelope['attempt_id']) : randomUUID();
  const resultId = preserveOriginalIds ? originalResultId : randomUUID();
  const submissionKey = randomUUID();

  const input = envelope['input'] as Record<string, unknown>;
  const pageCount = Number(input['page_count']);
  const prov = envelope['provenance'] as Record<string, unknown>;
  const timings = envelope['timings'] as Record<string, unknown>;

  const pdfHex = pdfBytes.toString('hex');
  const rawHex = rawBytes.toString('hex');
  const genSettingsEscaped = JSON.stringify(prov['generation_settings']).replace(/'/g, "''");
  const diagEscaped = JSON.stringify(envelope['diagnostics']).replace(/'/g, "''");
  const rendererEscaped = String(prov['renderer_identity']).replace(/'/g, "''");

  runAppSql(`
    BEGIN;
    SELECT nextval('eledgercare.extraction_fencing_seq');
    INSERT INTO eledgercare.documents (document_id, idempotency_key, submitted_at)
    VALUES ('${documentId}', '${submissionKey}', '${String(timings['started_at_utc'])}'::timestamptz - interval '1 second');

    INSERT INTO eledgercare.original_artifacts (document_id, bytes, sha256, byte_length, media_type, page_count)
    VALUES ('${documentId}', decode('${pdfHex}', 'hex'), decode('${pdfShaHex}', 'hex'), ${pdfBytes.length}, 'application/pdf', ${pageCount});

    INSERT INTO eledgercare.processing_jobs (job_id, document_id, status, requested_at, queued_at, updated_at, attempt_count, latest_fencing_token)
    VALUES ('${jobId}', '${documentId}', 'running', '${String(timings['started_at_utc'])}'::timestamptz - interval '1 second', '${String(timings['started_at_utc'])}'::timestamptz, '${String(timings['started_at_utc'])}'::timestamptz, 1, currval('eledgercare.extraction_fencing_seq'));

    INSERT INTO eledgercare.execution_attempts (
      attempt_id, job_id, document_id, attempt_number, fencing_token, retried_from_attempt_id,
      status, phase, run_directory_name, supervisor_instance_id, supervisor_pid, supervisor_create_filetime,
      started_at, last_heartbeat_at
    ) VALUES (
      '${attemptId}', '${jobId}', '${documentId}', 1, currval('eledgercare.extraction_fencing_seq'), NULL,
      'running', 'inferring', 'attempt-${attemptId}', '101b19cf-3133-4ead-91cb-9ca6068e3e72', 18496, 134393243591895019,
      '${String(timings['started_at_utc'])}'::timestamptz, '${String(timings['started_at_utc'])}'::timestamptz
    );

    UPDATE eledgercare.processing_jobs
       SET status = 'completed', updated_at = '${String(timings['completed_at_utc'])}'::timestamptz
     WHERE job_id = '${jobId}' AND latest_fencing_token = currval('eledgercare.extraction_fencing_seq');

    UPDATE eledgercare.execution_attempts
       SET status = 'completed', phase = 'completed',
           ended_at = '${String(timings['completed_at_utc'])}'::timestamptz,
           last_heartbeat_at = '${String(timings['completed_at_utc'])}'::timestamptz,
           exit_code = 0
     WHERE attempt_id = '${attemptId}';

    INSERT INTO eledgercare.extraction_results (
      result_id, document_id, job_id, attempt_id, fencing_token, schema_version,
      input_sha256, input_byte_length, page_count, raw_output_bytes, raw_output_byte_length, raw_output_sha256,
      model_repo_id, model_revision, model_manifest_sha256, dependency_lock_sha256, worker_source_digest, worker_config_digest,
      renderer_identity, generation_settings_json, finish_reason, output_page_count,
      started_at, completed_at, load_duration_ms, render_duration_ms, infer_duration_ms, total_duration_ms, diagnostic_metadata_json
    ) VALUES (
      '${resultId}', '${documentId}', '${jobId}', '${attemptId}', currval('eledgercare.extraction_fencing_seq'), 'eledgercare.local-extraction/1',
      decode('${pdfShaHex}', 'hex'), ${pdfBytes.length}, ${pageCount}, decode('${rawHex}', 'hex'), ${rawBytes.length}, decode('${rawShaHex}', 'hex'),
      '${String(prov['model_repo_id'])}', '${String(prov['model_revision'])}',
      decode('${String(prov['model_manifest_sha256'])}', 'hex'),
      decode('${String(prov['dependency_lock_sha256'])}', 'hex'),
      decode('${String(prov['worker_source_sha256'])}', 'hex'),
      decode('${String(prov['worker_config_sha256'])}', 'hex'),
      '${rendererEscaped}', '${genSettingsEscaped}'::jsonb, 'stop', ${pageCount},
      '${String(timings['started_at_utc'])}'::timestamptz, '${String(timings['completed_at_utc'])}'::timestamptz,
      ${Number(timings['load_duration_ms'])}, ${Number(timings['render_duration_ms'])}, ${Number(timings['infer_duration_ms'])}, ${Number(timings['total_duration_ms'])},
      '${diagEscaped}'::jsonb
    );
    COMMIT;
  `);

  return { documentId, jobId, attemptId, resultId };
}

test('F3-01 / F3-02 / F3-03 / F3-BIC-04: readable original PDF alongside five fields, correction + unknown + reviewed confirmation, post-review draft, historical reopen, and 3-page navigation', async ({
  page,
}) => {
  const wo = seedGenuineCompletedResult(
    woPdfBytes,
    woPdfSha,
    woRawBytes,
    woRawSha,
    woEnvelope,
    true,
    '01a1e573-a855-7735-96e1-f5d14cada602',
  );
  const mp = seedGenuineCompletedResult(
    mpPdfBytes,
    mpPdfSha,
    mpRawBytes,
    mpRawSha,
    mpEnvelope,
    true,
    '01a1e578-8bfa-7bba-b104-ea8309dbfd9e',
  );

  // 1. Open document screen first: extraction and review states are separate facts.
  await page.goto(`/documents/${wo.documentId}`);
  await expect(page.getByTestId('document-status')).toHaveText('Completed (unreviewed)');
  await expect(page.getByTestId('document-review-status')).toHaveText('Not started');
  await page.getByTestId('open-work-order-review').click();

  await expect(page).toHaveURL(new RegExp(`/documents/${wo.documentId}/review$`));
  await expect(page.getByTestId('review-status-badge')).toHaveText('Unreviewed preview (Revision 0)');
  await expect(page.getByTestId('pdf-preview-frame')).toHaveAttribute(
    'src',
    `/api/documents/${wo.documentId}/preview#page=1`,
  );

  // Verify all five conservative suggestions and zero confidence percentages!
  await expect(page.getByTestId('machine-value-work_order_id')).toHaveText('WO-004192');
  await expect(page.getByTestId('machine-value-property_name')).toHaveText('Cedar Hollow Apartments');
  await expect(page.getByTestId('machine-value-building_unit')).toHaveText('Bldg B - Unit 204');
  await expect(page.getByTestId('machine-value-requested_date')).toHaveText('2026-10-16');
  await expect(page.getByTestId('machine-value-issue_and_resolution')).toContainText(
    'Air handler fan running continuously',
  );
  await expect(page.getByText(/confidence\s*:|\d+(\.\d+)?%\s*confident/i)).toHaveCount(0);

  // Verify default operator presentation hides internal schema/field IDs, result UUID, and full SHA-256s in closed details,
  // while keeping plain headings, character limits, source quotes, and page controls visible!
  await expect(page.getByTestId('review-provenance-details')).not.toHaveAttribute('open', '');
  await expect(page.getByTestId('review-profile-id')).toBeHidden();
  await expect(page.getByTestId('review-field-schema')).toBeHidden();
  await expect(page.getByTestId('review-result-id')).toBeHidden();
  await expect(page.getByTestId('review-raw-sha256')).toBeHidden();
  await expect(page.getByTestId('review-original-sha256')).toBeHidden();
  await expect(page.getByTestId('technical-field-key-work_order_id')).toBeHidden();

  const defaultVisibleText = await page.getByTestId('review-workspace').innerText();
  expect(defaultVisibleText).toContain('Five work-order fields');
  expect(defaultVisibleText).toContain('max 64 characters');
  expect(defaultVisibleText).toContain('max 4000 characters');
  for (const forbiddenInDefaultFlow of [
    'maintenance-work-order/1',
    'maintenance-work-order-fields/1',
    'work-order-suggestions/1',
    'work_order_id',
    'property_name',
    'building_unit',
    'requested_date',
    'issue_and_resolution',
    wo.resultId,
    woPdfSha,
    woRawSha,
  ]) {
    expect(defaultVisibleText).not.toContain(forbiddenInDefaultFlow);
  }

  // Expand provenance & technical details: verify exact identifiers/hashes are accessible, then collapse back.
  await page.getByTestId('toggle-review-provenance').click();
  await expect(page.getByTestId('review-provenance-details')).toHaveAttribute('open', '');
  await expect(page.getByTestId('review-profile-id')).toBeVisible();
  await expect(page.getByTestId('review-profile-id')).toHaveText('maintenance-work-order/1');
  await expect(page.getByTestId('review-field-schema')).toHaveText('maintenance-work-order-fields/1');
  await expect(page.getByTestId('review-suggestion-policy')).toHaveText('work-order-suggestions/1');
  await expect(page.getByTestId('review-document-id')).toHaveText(wo.documentId);
  await expect(page.getByTestId('review-result-id')).toHaveText(wo.resultId);
  await expect(page.getByTestId('review-original-sha256')).toHaveText(woPdfSha);
  await expect(page.getByTestId('review-raw-sha256')).toHaveText(woRawSha);
  await expect(page.getByTestId('technical-field-key-work_order_id')).toHaveText('work_order_id');
  await expect(page.getByTestId('technical-field-key-issue_and_resolution')).toHaveText('issue_and_resolution');
  await page.getByTestId('toggle-review-provenance').click();
  await expect(page.getByTestId('review-provenance-details')).not.toHaveAttribute('open', '');

  // Allow Edge native PDFium viewer inside iframe to complete painting and capture full two-pane screenshot!
  await page.waitForTimeout(2500);
  const twoPaneShot = path.join(screenshotOutDir, 'f3-01-two-pane-wo01-comparison.png');
  await page.screenshot({ path: twoPaneShot });

  // 2. Save Revision #1 (draft): accept 2, edit 1, leave 2 unreviewed.
  await page.getByTestId('btn-accept-work_order_id').click();
  await expect(page.getByTestId('unsaved-edits-warning')).toBeVisible();
  await page.getByTestId('btn-edit-property_name').click();
  await page.getByTestId('input-value-property_name').fill('Cedar Hollow Apartments — Bldg B Campus');
  await page.getByTestId('btn-accept-requested_date').click();
  await page.getByTestId('input-operator-label').fill('Desk Operator 1');

  await expect(page.getByTestId('save-reviewed')).toBeDisabled();
  await page.getByTestId('save-draft').click();
  await expect(page.getByTestId('review-status-badge')).toHaveText('Saved draft (Revision #1)');
  await expect(page.getByTestId('current-revision-number')).toHaveText('#1');

  // 3. Save Revision #2 (explicit reviewed with 1 correction + 1 unknown + affirmative confirmation).
  await page.getByTestId('btn-unknown-building_unit').click();
  await page
    .getByTestId('input-unknown-reason-building_unit')
    .fill('Door unit plate obscured; field verification scheduled');
  await page.getByTestId('btn-accept-issue_and_resolution').click();

  await expect(page.getByTestId('unknown-fields-list')).toContainText('Fields marked unknown (1): Building / Unit');
  await expect(page.getByTestId('save-reviewed')).toBeDisabled();
  await page.getByTestId('confirm-reviewed-checkbox').check();
  await expect(page.getByTestId('save-reviewed')).toBeEnabled();
  await page.getByTestId('save-reviewed').click();

  await expect(page.getByTestId('review-status-badge')).toHaveText('Reviewed (Revision #2 · 1 unknown)');
  await expect(page.getByTestId('history-row-1')).toContainText('draft');
  await expect(page.getByTestId('history-row-2')).toContainText('reviewed');

  // Capture reviewed state two-pane screenshot too!
  await page.waitForTimeout(1000);
  const reviewedShot = path.join(screenshotOutDir, 'f3-02-reviewed-with-unknown.png');
  await page.screenshot({ path: reviewedShot });

  // 4. Verify Document screen shows Reviewed summary alongside untouched raw F2 output & attempt history!
  await page.getByTestId('back-to-document').click();
  await expect(page.getByTestId('document-status')).toHaveText('Completed (unreviewed)');
  await expect(page.getByTestId('document-review-status')).toContainText('Reviewed (Revision #2 · 1 unknown)');
  await expect(page.getByTestId('result-raw-sha256')).toHaveText(woRawSha);
  await page.getByTestId('open-work-order-review').click();

  // 5. Edit after review -> creates Revision #3 (draft), warning that historical reviewed state does not approve newer draft!
  await page.getByTestId('btn-edit-building_unit').click();
  await page.getByTestId('input-value-building_unit').fill('Bldg B - Unit 204 (Confirmed)');
  await page.getByTestId('save-draft').click();

  await expect(page.getByTestId('review-status-badge')).toHaveText('Saved draft (Revision #3)');
  await expect(page.getByTestId('prior-reviewed-historical-warning')).toBeVisible();

  // Reopen historical Revision #2 snapshot and verify immutable unknown decision + reason!
  await page.getByTestId('view-revision-2').click();
  await expect(page.getByTestId('historical-revision-banner')).toContainText('Revision #2 (reviewed)');
  await expect(page.getByTestId('historical-decision-building_unit')).toHaveText('unknown');
  await expect(page.getByTestId('historical-reason-building_unit')).toHaveText(
    'Door unit plate obscured; field verification scheduled',
  );
  await page.getByTestId('return-to-current-head').click();
  await expect(page.getByTestId('review-status-badge')).toHaveText('Saved draft (Revision #3)');

  // 6. Open 3-page SYN-MP-01: verify all 5 missing suggestions, remounted #page=1..3 navigation, and byte-exact fallback download.
  await page.goto(`/documents/${mp.documentId}/review`);
  await expect(page.getByTestId('pdf-current-page')).toContainText('Page 1 of 3');
  await expect(page.getByTestId('machine-value-work_order_id')).toContainText('No suggestion (missing)');
  await expect(page.getByTestId('btn-accept-work_order_id')).toBeDisabled();

  await page.getByTestId('pdf-page-btn-2').click();
  await expect(page.getByTestId('pdf-current-page')).toContainText('Page 2 of 3');
  await expect(page.getByTestId('pdf-preview-frame')).toHaveAttribute(
    'src',
    `/api/documents/${mp.documentId}/preview#page=2`,
  );

  await page.getByTestId('pdf-page-btn-3').click();
  await expect(page.getByTestId('pdf-current-page')).toContainText('Page 3 of 3');
  await expect(page.getByTestId('pdf-preview-frame')).toHaveAttribute(
    'src',
    `/api/documents/${mp.documentId}/preview#page=3`,
  );

  const dlPromise = page.waitForEvent('download');
  await page.getByTestId('pdf-download-fallback').click();
  const dl = await dlPromise;
  const dlBytes = readFileSync((await dl.path())!);
  expect(Buffer.compare(dlBytes, mpPdfBytes)).toBe(0);

  evidence.push({
    check: 'F3-01 / F3-02 / F3-03 / F3-BIC-04 browser comparison, review lifecycle, history, and 3-page nav',
    woDocumentId: wo.documentId,
    mpDocumentId: mp.documentId,
    twoPaneScreenshot: twoPaneShot,
    reviewedScreenshot: reviewedShot,
    revisionsCreated: 3,
    mpDownloadExact: true,
  });
});

test('F3-04 / F3-BIC-05: stale-tab 409 preserves unsaved edits, uncertain 5xx retries with same key, old replay never overwrites newer head, and zero browser storage writes occur', async ({
  browser,
}) => {
  const wo = seedGenuineCompletedResult(woPdfBytes, woPdfSha, woRawBytes, woRawSha, woEnvelope, false, randomUUID());

  const context = await browser.newContext({ viewport: { width: 1440, height: 920 } });
  const tabA = await context.newPage();
  const tabB = await context.newPage();

  await tabA.goto(`/documents/${wo.documentId}/review`);
  await tabB.goto(`/documents/${wo.documentId}/review`);
  await expect(tabA.getByTestId('current-revision-number')).toHaveText('#0');
  await expect(tabB.getByTestId('current-revision-number')).toHaveText('#0');

  // 1. Tab A saves Revision #1.
  await tabA.getByTestId('btn-accept-work_order_id').click();
  await tabA.getByTestId('save-draft').click();
  await expect(tabA.getByTestId('current-revision-number')).toHaveText('#1');

  // 2. Stale Tab B edits property_name and attempts to save from expectedRevision=0 -> 409 stale_expected_revision!
  await tabB.getByTestId('btn-edit-property_name').click();
  await tabB.getByTestId('input-value-property_name').fill('Tab B Preserved Unsaved Edit');
  await tabB.getByTestId('save-draft').click();

  await expect(tabB.getByTestId('stale-conflict-banner')).toBeVisible();
  await expect(tabB.getByTestId('conflict-current-revision')).toHaveText('#1');
  // Unsaved edit in Tab B is preserved in memory!
  await expect(tabB.getByTestId('input-value-property_name')).toHaveValue('Tab B Preserved Unsaved Edit');

  // Inspect server Revision #1, rebase explicitly onto #1, and save Revision #2!
  await tabB.getByTestId('inspect-conflict-head').click();
  await expect(tabB.getByTestId('conflict-server-summary')).toBeVisible();
  const conflictSummaryText = await tabB.getByTestId('conflict-server-summary').innerText();
  expect(conflictSummaryText).toContain('Work Order ID:');
  expect(conflictSummaryText).not.toContain('work_order_id');
  await tabB.getByTestId('reconcile-onto-latest').click();
  await expect(tabB.getByTestId('input-value-property_name')).toHaveValue('Tab B Preserved Unsaved Edit');
  await tabB.getByTestId('save-draft').click();
  await expect(tabB.getByTestId('review-status-badge')).toHaveText('Saved draft (Revision #2)');

  // 3. Uncertain 5xx after real server commit: retains Idempotency-Key & body in page memory ONLY (zero storage writes) and replays 200 OK!
  const seenKeys: string[] = [];
  let interceptFirst500 = true;
  await tabB.route(`**/api/documents/${wo.documentId}/review/revisions`, async (route) => {
    if (route.request().method() !== 'POST') {
      return route.fallback();
    }
    const key = route.request().headers()['idempotency-key'];
    seenKeys.push(key);
    if (interceptFirst500) {
      interceptFirst500 = false;
      const realResp = await route.fetch(); // Server genuinely commits Revision #3!
      expect(realResp.status()).toBe(201);
      return route.fulfill({
        status: 500,
        contentType: 'application/problem+json',
        body: JSON.stringify({ title: 'Simulated gateway failure after commit', status: 500 }),
      });
    }
    return route.fallback();
  });

  await tabB.getByTestId('btn-accept-requested_date').click();
  await tabB.getByTestId('save-draft').click();
  await expect(tabB.getByTestId('uncertain-save-banner')).toBeVisible();
  await expect(tabB.getByTestId('retry-uncertain-save')).toHaveText('Retry pending save');
  await expect(tabB.getByTestId('uncertain-save-details')).not.toHaveAttribute('open', '');
  await expect(tabB.getByTestId('pending-review-key')).toBeHidden();
  const uncertainVisibleText = await tabB.getByTestId('uncertain-save-banner').innerText();
  expect(uncertainVisibleText).not.toContain(seenKeys[0]);
  expect(uncertainVisibleText).not.toContain('Idempotency-Key');

  await tabB.getByTestId('toggle-uncertain-save-details').click();
  await expect(tabB.getByTestId('pending-review-key')).toBeVisible();
  const pendingKey = (await tabB.getByTestId('pending-review-key').textContent())!.trim();
  expect(pendingKey).toBe(seenKeys[0]);

  // Verify ZERO review data in sessionStorage, localStorage, or IndexedDB (F3-BIC-05)!
  const storageSnapshot = await tabB.evaluate(async () => {
    const idbList = 'databases' in indexedDB ? await indexedDB.databases() : [];
    return {
      sessionKeys: Object.keys(sessionStorage),
      localKeys: Object.keys(localStorage),
      sessionDump: JSON.stringify(sessionStorage),
      localDump: JSON.stringify(localStorage),
      idbCount: idbList.length,
    };
  });
  expect(storageSnapshot.sessionKeys).toEqual([]);
  expect(storageSnapshot.localKeys).toEqual([]);
  expect(storageSnapshot.idbCount).toBe(0);

  await tabB.getByTestId('retry-uncertain-save').click();
  await expect(tabB.getByTestId('uncertain-save-banner')).toHaveCount(0);
  await expect(tabB.getByTestId('review-status-badge')).toHaveText('Saved draft (Revision #3)');
  expect(seenKeys).toEqual([pendingKey, pendingKey]);
  await tabB.unroute(`**/api/documents/${wo.documentId}/review/revisions`);

  // 4. Replay of older committed Revision #4 AFTER Tab A advances server head to Revision #5:
  //    Tab B must NEVER silently overwrite client head with old Revision #4!
  let interceptAbortAfterCommit = true;
  await tabB.route(`**/api/documents/${wo.documentId}/review/revisions`, async (route) => {
    if (route.request().method() !== 'POST') {
      return route.fallback();
    }
    if (interceptAbortAfterCommit) {
      interceptAbortAfterCommit = false;
      const realResp = await route.fetch(); // Commits Revision #4!
      expect(realResp.status()).toBe(201);
      return route.abort('connectionreset');
    }
    return route.fallback();
  });

  await tabB.getByTestId('btn-edit-building_unit').click();
  await tabB.getByTestId('input-value-building_unit').fill('Unit 204-Rev4');
  await tabB.getByTestId('save-draft').click();
  await expect(tabB.getByTestId('uncertain-save-banner')).toBeVisible();

  // Meanwhile, Tab A reloads Revision #4 and saves Revision #5 ("Unit 204-Rev5-NewestHead")!
  await tabA.reload();
  await expect(tabA.getByTestId('current-revision-number')).toHaveText('#4');
  await tabA.getByTestId('input-value-building_unit').fill('Unit 204-Rev5-NewestHead');
  await tabA.getByTestId('save-draft').click();
  await expect(tabA.getByTestId('current-revision-number')).toHaveText('#5');

  // Now Tab B retries its uncertain Revision #4 key: server replays Revision #4 (isCurrentHead=false, currentRevisionNumber=5),
  // and Tab B loads current head #5 with an explicit notice instead of overwriting with #4!
  await tabB.getByTestId('retry-uncertain-save').click();
  await expect(tabB.getByTestId('replayed-historical-notice')).toContainText('Revision #4');
  await expect(tabB.getByTestId('replayed-historical-notice')).toContainText('Revision #5');
  await expect(tabB.getByTestId('replayed-historical-details')).not.toHaveAttribute('open', '');
  await expect(tabB.getByTestId('replayed-operation-key')).toBeHidden();
  await expect(tabB.getByTestId('current-revision-number')).toHaveText('#5');
  await expect(tabB.getByTestId('input-value-building_unit')).toHaveValue('Unit 204-Rev5-NewestHead');

  await context.close();

  evidence.push({
    check: 'F3-04 / F3-BIC-05 stale conflict, uncertain same-key retry, old-replay head protection, and zero browser storage',
    documentId: wo.documentId,
    sameKeyRetried: seenKeys[0] === seenKeys[1],
    zeroBrowserStorageConfirmed: true,
    oldReplayProtectedCurrentHeadRev5: true,
  });
});

test('F3-05 / F3-06: XSS-like quotes/values remain strictly inert and saved review survives API restart with OCR disabled', async ({
  page,
}) => {
  const hostileRaw =
    '<PAGE>' +
    '<BLOCK>text[0,0,10,10]<FORK>Work Order ID: <script>window.__f3_xss="wo"</script>\n' +
    '<BLOCK>text[0,0,10,10]<FORK>Property: <img src=x onerror="window.__f3_xss=\'prop1\'">\n' +
    '<BLOCK>text[0,0,10,10]<FORK>Property: <svg onload="window.__f3_xss=\'prop2\'">\n';
  const hostileRawBytes = Buffer.from(hostileRaw, 'utf8');
  const hostileRawSha = createHash('sha256').update(hostileRawBytes).digest('hex');

  const customEnv = structuredClone(woEnvelope) as Record<string, unknown>;
  (customEnv['output'] as Record<string, unknown>)['byte_length'] = hostileRawBytes.length;
  (customEnv['output'] as Record<string, unknown>)['sha256'] = hostileRawSha;

  const seeded = seedGenuineCompletedResult(
    woPdfBytes,
    woPdfSha,
    hostileRawBytes,
    hostileRawSha,
    customEnv,
    false,
    randomUUID(),
  );

  await page.goto(`/documents/${seeded.documentId}/review`);
  await expect(page.getByTestId('machine-value-work_order_id')).toHaveText('<script>window.__f3_xss="wo"</script>');
  await expect(page.getByTestId('competing-sources-property_name')).toContainText(
    '<img src=x onerror="window.__f3_xss=\'prop1\'">',
  );

  await page.getByTestId('btn-accept-work_order_id').click();
  await page.getByTestId('btn-edit-property_name').click();
  await page.getByTestId('input-value-property_name').fill('<script>window.__f3_xss="human"</script>');
  await page.getByTestId('btn-unknown-building_unit').click();
  await page.getByTestId('input-unknown-reason-building_unit').fill('<img src=x onerror="window.__f3_xss=\'reason\'">');
  await page.getByTestId('btn-unknown-requested_date').click();
  await page.getByTestId('btn-unknown-issue_and_resolution').click();
  await page.getByTestId('input-operator-label').fill('<b>Op &lt;script&gt;</b>');
  await page.getByTestId('confirm-reviewed-checkbox').check();
  await page.getByTestId('save-reviewed').click();

  await expect(page.getByTestId('review-status-badge')).toHaveText('Reviewed (Revision #1 · 3 unknown)');
  await expect(
    page.locator('[data-testid="review-workspace"] script, [data-testid="review-workspace"] img, [data-testid="review-workspace"] svg'),
  ).toHaveCount(0);
  const xssFlag = await page.evaluate(() => (window as unknown as Record<string, unknown>)['__f3_xss']);
  expect(xssFlag).toBeUndefined();

  // Restart OwnedApi (new PID, LocalOcr:Enabled=false) and verify exact reopen!
  const pidBefore = api.starts[api.starts.length - 1].pid;
  await api.kill();
  await api.start();
  const pidAfter = api.starts[api.starts.length - 1].pid;
  expect(pidAfter).not.toBe(pidBefore);

  await page.reload();
  await expect(page.getByTestId('review-status-badge')).toHaveText('Reviewed (Revision #1 · 3 unknown)');
  await expect(page.getByTestId('input-value-property_name')).toHaveValue('<script>window.__f3_xss="human"</script>');
  await expect(page.getByTestId('input-unknown-reason-building_unit')).toHaveValue(
    '<img src=x onerror="window.__f3_xss=\'reason\'">',
  );

  evidence.push({
    check: 'F3-05 / F3-06 hostile markup inertness + API restart reopen',
    documentId: seeded.documentId,
    xssExecuted: false,
    apiPidBefore: pidBefore,
    apiPidAfter: pidAfter,
  });
});
