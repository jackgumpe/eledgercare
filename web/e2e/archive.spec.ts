import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { createHash, randomUUID } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { OwnedApi } from './owned-api';

/**
 * WP-0010 F4 Microsoft Edge Playwright E2E acceptance suite covering F4-01..06 and F4-BIC-06..07
 * with LocalOcr:Enabled=false and zero GPU/model calls.
 * Seeds attributed genuine accepted WP-0006 F2 evidence (SYN-WO-01-v1-raster300 & SYN-MP-01-v0-clean)
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

const f1PdfPath = path.join(repoRoot, 'tests', 'fixtures', 'F1-SWO-001.pdf');

const evidence: Record<string, unknown>[] = [];
const api = new OwnedApi();
const screenshotOutDir =
  process.env['ELEDGERCARE_F4_SCREENSHOT_DIR'] ?? path.join(repoRoot, '.scratch', 'playwright', 'f4-screenshots');

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
    path.join(out, 'f4-browser-evidence.json'),
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

function seedRemappedGenuineCompletedResult(
  pdfBytes: Buffer,
  pdfShaHex: string,
  rawBytes: Buffer,
  rawShaHex: string,
  envelope: Record<string, unknown>,
  submittedAtIso: string,
): SeededIds {
  const documentId = randomUUID();
  const jobId = randomUUID();
  const attemptId = randomUUID();
  const resultId = randomUUID();
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
    VALUES ('${documentId}', '${submissionKey}', '${submittedAtIso}'::timestamptz);

    INSERT INTO eledgercare.original_artifacts (document_id, bytes, sha256, byte_length, media_type, page_count)
    VALUES ('${documentId}', decode('${pdfHex}', 'hex'), decode('${pdfShaHex}', 'hex'), ${pdfBytes.length}, 'application/pdf', ${pageCount});

    INSERT INTO eledgercare.processing_jobs (job_id, document_id, status, requested_at, queued_at, updated_at, attempt_count, latest_fencing_token)
    VALUES ('${jobId}', '${documentId}', 'running', '${submittedAtIso}'::timestamptz, '${submittedAtIso}'::timestamptz, '${submittedAtIso}'::timestamptz, 1, currval('eledgercare.extraction_fencing_seq'));

    INSERT INTO eledgercare.execution_attempts (
      attempt_id, job_id, document_id, attempt_number, fencing_token, retried_from_attempt_id,
      status, phase, run_directory_name, supervisor_instance_id, supervisor_pid, supervisor_create_filetime,
      started_at, last_heartbeat_at
    ) VALUES (
      '${attemptId}', '${jobId}', '${documentId}', 1, currval('eledgercare.extraction_fencing_seq'), NULL,
      'running', 'inferring', 'attempt-${attemptId}', '101b19cf-3133-4ead-91cb-9ca6068e3e72', 18496, 134393243591895019,
      '${submittedAtIso}'::timestamptz, '${submittedAtIso}'::timestamptz
    );

    UPDATE eledgercare.processing_jobs
       SET status = 'completed', updated_at = '${submittedAtIso}'::timestamptz + interval '2 seconds'
     WHERE job_id = '${jobId}' AND latest_fencing_token = currval('eledgercare.extraction_fencing_seq');

    UPDATE eledgercare.execution_attempts
       SET status = 'completed', phase = 'completed',
           ended_at = '${submittedAtIso}'::timestamptz + interval '2 seconds',
           last_heartbeat_at = '${submittedAtIso}'::timestamptz + interval '2 seconds',
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
      '${submittedAtIso}'::timestamptz, '${submittedAtIso}'::timestamptz + interval '2 seconds',
      ${Number(timings['load_duration_ms'])}, ${Number(timings['render_duration_ms'])}, ${Number(timings['infer_duration_ms'])}, ${Number(timings['total_duration_ms'])},
      '${diagEscaped}'::jsonb
    );
    COMMIT;
  `);

  return { documentId, jobId, attemptId, resultId };
}

async function saveRevisionViaApi(
  documentId: string,
  resultId: string,
  expectedRevision: number,
  status: 'draft' | 'reviewed',
  fields: Record<string, unknown>[],
): Promise<void> {
  const resp = await fetch(`http://127.0.0.1:${api.port}/api/documents/${documentId}/review/revisions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': randomUUID(),
    },
    body: JSON.stringify({
      resultId,
      expectedRevision,
      status,
      operatorDisplayLabel: 'E2E Operator',
      fields,
    }),
  });
  expect(resp.status).toBe(201);
}

const woIssueSuggested =
  'Air handler fan running continuously with warm supply air at 79 F setpoint. Inspected condensing unit CHP-B204: ' +
  'dual run capacitor measured 18.2 uF on 45 uF herm leg and contactor points pitted. Replaced capacitor and 2-pole ' +
  'contactor from van stock; verified 19.4 F delta-T across evaporator coil.';

test('F4-01 / F4-02 / F4-06 / F4-BIC-07: browser archive search -> readable PDF page (#page=2) -> return to query, and reviewed hit -> pinned historical revision without fabricated coordinates -> return to query', async ({
  page,
}) => {
  const wo = seedRemappedGenuineCompletedResult(
    woPdfBytes,
    woPdfSha,
    woRawBytes,
    woRawSha,
    woEnvelope,
    '2026-11-17T08:10:00Z',
  );
  const mp = seedRemappedGenuineCompletedResult(
    mpPdfBytes,
    mpPdfSha,
    mpRawBytes,
    mpRawSha,
    mpEnvelope,
    '2026-11-17T08:11:00Z',
  );

  // Submit a live unprocessed awaiting_extraction PDF via Intake screen first
  await page.goto('/');
  await page.getByTestId('file-input').setInputFiles(f1PdfPath);
  await page.getByTestId('submit').click();
  await expect(page.getByTestId('receipt')).toBeVisible();
  const unprocessedDocId = (await page.getByTestId('receipt-document-id').textContent())!.trim();

  // Save real HTTP revisions on SYN-WO-01:
  // Rev #1 (reviewed, later superseded) -> Rev #2 (reviewed, active for search, with 1 unknown & 1 manual no-provenance edit) -> Rev #3 (newer draft)
  await saveRevisionViaApi(wo.documentId, wo.resultId, 0, 'reviewed', [
    { fieldKey: 'work_order_id', decision: 'edited', value: 'WO-F4-SUPERSEDED-101' },
    { fieldKey: 'property_name', decision: 'accepted', value: 'Cedar Hollow Apartments' },
    { fieldKey: 'building_unit', decision: 'accepted', value: 'Bldg B - Unit 204' },
    { fieldKey: 'requested_date', decision: 'accepted', value: '2026-10-16' },
    { fieldKey: 'issue_and_resolution', decision: 'accepted', value: woIssueSuggested },
  ]);

  await saveRevisionViaApi(wo.documentId, wo.resultId, 1, 'reviewed', [
    {
      fieldKey: 'work_order_id',
      decision: 'edited',
      value: 'WO-F4-ACTIVE-202',
      consultedSource: { pageNumber: 1, blockOrdinal: 5 },
    },
    {
      fieldKey: 'property_name',
      decision: 'edited',
      value: 'Cedar Hollow — North Wing',
      consultedSource: { pageNumber: 1, blockOrdinal: 7 },
    },
    { fieldKey: 'building_unit', decision: 'unknown', unknownReason: 'Unit plate painted over' },
    { fieldKey: 'requested_date', decision: 'accepted', value: '2026-10-16' },
    {
      fieldKey: 'issue_and_resolution',
      decision: 'edited',
      value: "Manual boiler check KESTREL-NO-PROV <script>window.__f4_xss='hit'</script>",
      // Intentionally NO consultedSource: human-entered without source coordinates!
    },
  ]);

  await saveRevisionViaApi(wo.documentId, wo.resultId, 2, 'draft', [
    { fieldKey: 'work_order_id', decision: 'edited', value: 'WO-F4-DRAFT-HEAD-303' },
    { fieldKey: 'property_name', decision: 'unreviewed' },
    { fieldKey: 'building_unit', decision: 'unreviewed' },
    { fieldKey: 'requested_date', decision: 'unreviewed' },
    { fieldKey: 'issue_and_resolution', decision: 'unreviewed' },
  ]);

  // 1. Navigate to /archive via top navigation link and verify browse mode
  await page.getByTestId('nav-archive').click();
  await expect(page).toHaveURL(/\/archive$/);
  await expect(page.getByTestId(`archive-card-${unprocessedDocId}`)).toBeVisible();
  await expect(page.getByTestId(`archive-doc-status-${unprocessedDocId}`)).toHaveText('Awaiting extraction');
  await expect(page.getByTestId(`archive-card-${wo.documentId}`)).toBeVisible();
  await expect(page.getByTestId(`archive-card-title-${wo.documentId}`)).toHaveText(
    'WO-F4-ACTIVE-202 — Cedar Hollow — North Wing',
  );
  await expect(page.getByTestId(`archive-newer-draft-${wo.documentId}`)).toContainText(
    'Newer draft exists (head Revision #3)',
  );

  // Secondary provenance details drawer is closed by default (hiding full UUIDs/SHA-256s until expanded)
  await expect(page.getByTestId(`archive-provenance-${wo.documentId}`)).not.toHaveAttribute('open', '');
  await expect(page.getByTestId(`archive-full-doc-id-${wo.documentId}`)).toBeHidden();

  // 2. Machine search -> open readable source PDF Page 2 on 3-page SYN-MP-01 -> return to exact archive query
  await page.getByTestId('archive-source-select').selectOption('machine');
  await page.getByTestId('archive-query-input').fill('Refrigerator Evaporator');
  await page.getByTestId('archive-submit-btn').click();

  await expect(page).toHaveURL(/\/archive\?q=Refrigerator%20Evaporator&source=machine$/);
  const mpCard = page.getByTestId(`archive-card-${mp.documentId}`);
  await expect(mpCard).toBeVisible();
  await expect(page.getByTestId(`witness-source-label-${mp.documentId}-0`)).toHaveText(
    'Machine extraction — unreviewed',
  );
  await expect(page.getByTestId(`archive-snippet-${mp.documentId}-0`).locator('mark.archive-hit')).toHaveText([
    'Refrigerator',
    'Evaporator',
  ]);

  await page.getByTestId(`witness-open-machine-${mp.documentId}-0`).click();
  await expect(page).toHaveURL(new RegExp(`/documents/${mp.documentId}\\?.*page=2`));
  await expect(page.getByTestId('document-pdf-current-page')).toContainText('Page 2 of 3');
  await expect(page.getByTestId('document-pdf-preview-frame')).toHaveAttribute(
    'src',
    `/api/documents/${mp.documentId}/preview#page=2`,
  );
  await expect(page.getByTestId('result-page-2')).toHaveClass(/highlighted-target/);

  // Wait for Microsoft Edge native PDFium viewer to paint Page 2 and capture screenshot!
  await page.waitForTimeout(2000);
  const mpPage2Shot = path.join(screenshotOutDir, 'f4-01-document-mp01-page2-preview.png');
  await page.screenshot({ path: mpPage2Shot });

  await page.getByTestId('back-to-archive').click();
  await expect(page).toHaveURL(/\/archive\?q=Refrigerator%20Evaporator&source=machine$/);
  await expect(page.getByTestId('archive-query-input')).toHaveValue('Refrigerator Evaporator');
  await expect(page.getByTestId('archive-source-select')).toHaveValue('machine');

  // 3. Reviewed search -> inert hostile snippet + open exact pinned historical Revision #2 with zero fabricated page coords -> return to query
  await page.getByTestId('archive-source-select').selectOption('reviewed');
  await page.getByTestId('archive-query-input').fill('KESTREL-NO-PROV');
  await page.getByTestId('archive-submit-btn').click();

  await expect(page).toHaveURL(/\/archive\?q=KESTREL-NO-PROV&source=reviewed$/);
  await expect(page.getByTestId(`archive-card-${wo.documentId}`)).toBeVisible();
  await expect(page.getByTestId(`witness-source-label-${wo.documentId}-0`)).toHaveText(
    'Issue & Resolution · Reviewed Revision #2',
  );
  await expect(page.getByTestId(`witness-consulted-page-${wo.documentId}-0`)).toHaveCount(0);
  await expect(page.getByTestId(`archive-snippet-${wo.documentId}-0`)).toContainText(
    "<script>window.__f4_xss='hit'</script>",
  );
  await expect(page.locator('[data-testid="archive-results-section"] script')).toHaveCount(0);
  expect(await page.evaluate(() => (window as unknown as Record<string, unknown>)['__f4_xss'])).toBeUndefined();

  const archiveHitShot = path.join(screenshotOutDir, 'f4-02-archive-reviewed-hit-newer-draft.png');
  await page.screenshot({ path: archiveHitShot });

  await page.getByTestId(`witness-open-reviewed-${wo.documentId}-0`).click();
  await expect(page).toHaveURL(new RegExp(`/documents/${wo.documentId}/review/revisions/2\\?`));
  expect(page.url()).not.toContain('page=');

  await expect(page.getByTestId('historical-revision-banner')).toContainText(
    'Viewing immutable historical Revision #2 (reviewed)',
  );
  await expect(page.getByTestId('historical-revision-banner')).toContainText(
    'current head is Revision #3: draft',
  );
  await expect(page.getByTestId('historical-field-issue_and_resolution')).toHaveAttribute('data-focused', 'true');
  await expect(page.getByTestId('historical-no-provenance-issue_and_resolution')).toContainText('None recorded');
  await expect(page.getByTestId('historical-consulted-page-issue_and_resolution')).toHaveCount(0);
  // Meanwhile, property_name (which recorded consultedSource Page 1) DOES show its source page jump button!
  await expect(page.getByTestId('historical-consulted-page-property_name')).toHaveCount(1);

  await page.waitForTimeout(1500);
  const pinnedHistShot = path.join(screenshotOutDir, 'f4-03-pinned-historical-rev2-focused.png');
  await page.screenshot({ path: pinnedHistShot });

  await page.getByTestId('review-back-to-archive').click();
  await expect(page).toHaveURL(/\/archive\?q=KESTREL-NO-PROV&source=reviewed$/);
  await expect(page.getByTestId(`archive-card-${wo.documentId}`)).toBeVisible();

  // 4. Superseded Rev #1 and unapproved Draft #3 are excluded from reviewed search
  for (const excluded of ['WO-F4-SUPERSEDED-101', 'WO-F4-DRAFT-HEAD-303']) {
    await page.getByTestId('archive-query-input').fill(excluded);
    await page.getByTestId('archive-submit-btn').click();
    await expect(page.getByTestId('archive-empty')).toBeVisible();
  }

  evidence.push({
    check: 'F4-01 / F4-02 / F4-06 / F4-BIC-07 browser archive -> PDF #page=2 -> pinned historical Rev #2 -> return',
    woDocumentId: wo.documentId,
    mpDocumentId: mp.documentId,
    unprocessedDocId,
    screenshots: [mpPage2Shot, archiveHitShot, pinnedHistShot],
  });
});

test('F4-04 / F4-BIC-06 / F4-BIC-07: obsolete slow search response is ignored after newer query, unsaved review edits are guarded on navigation, and zero storage keys are written', async ({
  page,
}) => {
  const wo = seedRemappedGenuineCompletedResult(
    woPdfBytes,
    woPdfSha,
    woRawBytes,
    woRawSha,
    woEnvelope,
    '2026-11-17T08:20:00Z',
  );
  await saveRevisionViaApi(wo.documentId, wo.resultId, 0, 'reviewed', [
    { fieldKey: 'work_order_id', decision: 'edited', value: 'WO-FAST-SECOND-808' },
    { fieldKey: 'property_name', decision: 'accepted', value: 'Cedar Hollow Apartments' },
    { fieldKey: 'building_unit', decision: 'accepted', value: 'Bldg B - Unit 204' },
    { fieldKey: 'requested_date', decision: 'accepted', value: '2026-10-16' },
    { fieldKey: 'issue_and_resolution', decision: 'accepted', value: woIssueSuggested },
  ]);

  let delayedSlowResolved = false;
  await page.route('**/api/archive?*', async (route) => {
    const url = new URL(route.request().url());
    if (url.searchParams.get('q') === 'SLOW-OBSOLETE-QUERY') {
      await new Promise((r) => setTimeout(r, 700));
      delayedSlowResolved = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          query: 'SLOW-OBSOLETE-QUERY',
          terms: ['SLOW-OBSOLETE-QUERY'],
          source: 'all',
          limit: 20,
          hasMore: false,
          nextCursor: null,
          projectionVersion: 'archive-machine-projection/1',
          items: [],
        }),
      });
      return;
    }
    await route.fallback();
  });

  await page.goto('/archive');
  await page.getByTestId('archive-query-input').fill('SLOW-OBSOLETE-QUERY');
  await page.getByTestId('archive-submit-btn').click();

  // Immediately issue a newer search before SLOW-OBSOLETE-QUERY finishes!
  await page.getByTestId('archive-query-input').fill('WO-FAST-SECOND-808');
  await page.getByTestId('archive-submit-btn').click();

  await expect(page.getByTestId(`archive-card-${wo.documentId}`)).toBeVisible();
  await page.waitForTimeout(900);
  // Even if the slow request wasn't aborted before wire-level fulfillment or finished late, UI must keep WO-FAST-SECOND-808!
  await expect(page.getByTestId(`archive-card-${wo.documentId}`)).toBeVisible();
  await expect(page.getByTestId('archive-empty')).toHaveCount(0);

  await page.unroute('**/api/archive?*');

  // Verify zero browser storage writes from Archive workflow
  const storageKeys = await page.evaluate(() => ({
    local: Object.keys(localStorage),
    session: Object.keys(sessionStorage),
  }));
  expect(storageKeys).toEqual({ local: [], session: [] });

  // Verify unsaved review edits guard when navigating from WorkOrderReviewPage to Archive
  await page.goto(`/documents/${wo.documentId}/review`);
  await page.getByTestId('btn-edit-property_name').click();
  await page.getByTestId('input-value-property_name').fill('Unsaved In-Memory Edit 909');
  await expect(page.getByTestId('unsaved-edits-warning')).toBeVisible();

  // First dialog: dismiss (Cancel) -> stays on review screen with unsaved edit intact!
  page.once('dialog', async (dlg) => {
    await dlg.dismiss();
  });
  await page.getByTestId('review-open-archive').click();
  await expect(page).toHaveURL(new RegExp(`/documents/${wo.documentId}/review$`));
  await expect(page.getByTestId('input-value-property_name')).toHaveValue('Unsaved In-Memory Edit 909');

  // Second dialog: accept (OK) -> proceeds to /archive!
  page.once('dialog', async (dlg) => {
    await dlg.accept();
  });
  await page.getByTestId('review-open-archive').click();
  await expect(page).toHaveURL(/\/archive$/);

  evidence.push({
    check: 'F4-04 / F4-BIC-06 / F4-BIC-07 obsolete response suppression + unsaved review navigation guard + zero storage',
    woDocumentId: wo.documentId,
    delayedSlowResolved,
  });
});

test('F4-04 / WP-0010-006: newer typed draft survives pending router navigation, newer submitted query/filter supersedes pending navigation and late HTTP callbacks, and external Back/Forward & error states stay consistent', async ({
  page,
}) => {
  const wo1 = seedRemappedGenuineCompletedResult(
    woPdfBytes,
    woPdfSha,
    woRawBytes,
    woRawSha,
    woEnvelope,
    '2026-11-17T08:30:00Z',
  );
  const wo2 = seedRemappedGenuineCompletedResult(
    woPdfBytes,
    woPdfSha,
    woRawBytes,
    woRawSha,
    woEnvelope,
    '2026-11-17T08:31:00Z',
  );
  const mp = seedRemappedGenuineCompletedResult(
    mpPdfBytes,
    mpPdfSha,
    mpRawBytes,
    mpRawSha,
    mpEnvelope,
    '2026-11-17T08:32:00Z',
  );

  await saveRevisionViaApi(wo1.documentId, wo1.resultId, 0, 'reviewed', [
    { fieldKey: 'work_order_id', decision: 'edited', value: 'WO-NAV-FIRST-101' },
    { fieldKey: 'property_name', decision: 'accepted', value: 'Cedar Hollow Apartments' },
    { fieldKey: 'building_unit', decision: 'accepted', value: 'Bldg B - Unit 204' },
    { fieldKey: 'requested_date', decision: 'accepted', value: '2026-10-16' },
    { fieldKey: 'issue_and_resolution', decision: 'accepted', value: woIssueSuggested },
  ]);

  await saveRevisionViaApi(wo2.documentId, wo2.resultId, 0, 'reviewed', [
    { fieldKey: 'work_order_id', decision: 'edited', value: 'WO-NAV-SECOND-202' },
    { fieldKey: 'property_name', decision: 'accepted', value: 'Cedar Hollow Apartments' },
    { fieldKey: 'building_unit', decision: 'accepted', value: 'Bldg B - Unit 204' },
    { fieldKey: 'requested_date', decision: 'accepted', value: '2026-10-16' },
    { fieldKey: 'issue_and_resolution', decision: 'accepted', value: woIssueSuggested },
  ]);

  const archiveRequests: string[] = [];
  page.on('request', (req) => {
    if (req.url().includes('/api/archive')) {
      archiveRequests.push(req.url());
    }
  });

  await page.goto('/archive');
  await expect(page.getByTestId(`archive-card-${wo2.documentId}`)).toBeVisible();

  // Install deterministic Promise-latched route guard on live /archive route (separating route propagation from HTTP!)
  await page.evaluate(() => {
    const w = window as unknown as Record<string, unknown>;
    const ngGlobal = w['ng'] as { getComponent: (el: Element) => { router: { config: Array<Record<string, unknown>> } } };
    const cmp = ngGlobal.getComponent(document.querySelector('elc-archive-page')!);
    const archiveRoute = cmp.router.config.find((r) => r['path'] === 'archive')!;

    const state: {
      holdNext: boolean;
      queue: Array<{ resolve: (allow: boolean) => void }>;
    } = { holdNext: false, queue: [] };

    archiveRoute['runGuardsAndResolvers'] = 'paramsOrQueryParamsChange';
    archiveRoute['canActivate'] = [
      () => {
        if (!state.holdNext) {
          return true;
        }
        return new Promise<boolean>((resolve) => {
          state.queue.push({ resolve });
        });
      },
    ];

    w['__e2eArchiveNavLatch'] = {
      arm: () => {
        state.holdNext = true;
      },
      disarm: () => {
        state.holdNext = false;
      },
      pendingCount: () => state.queue.length,
      releaseNext: () => {
        const next = state.queue.shift();
        next?.resolve(true);
      },
      releaseAll: () => {
        while (state.queue.length > 0) {
          state.queue.shift()!.resolve(true);
        }
      },
    };
  });

  // (1) Newer typed draft survives earlier pending navigation completing
  await page.evaluate(() => {
    ((window as unknown as Record<string, unknown>)['__e2eArchiveNavLatch'] as { arm: () => void }).arm();
  });
  await page.getByTestId('archive-query-input').fill('WO-NAV-FIRST-101');
  await page.getByTestId('archive-source-select').selectOption('reviewed');

  // HTTP completes and renders wo1 WHILE router navigation is deterministically held pending
  await expect(page.getByTestId(`archive-card-${wo1.documentId}`)).toBeVisible();
  expect(
    await page.evaluate(
      () => ((window as unknown as Record<string, unknown>)['__e2eArchiveNavLatch'] as { pendingCount: () => number }).pendingCount(),
    ),
  ).toBe(1);
  expect(new URL(page.url()).search).toBe('');

  // User types a newer draft before Navigation #1 settles
  await page.getByTestId('archive-query-input').fill('WO-NAV-SECOND-202');
  const reqCountBeforeNavSettle = archiveRequests.length;

  await page.evaluate(() => {
    const latch = (window as unknown as Record<string, unknown>)['__e2eArchiveNavLatch'] as {
      disarm: () => void;
      releaseNext: () => void;
    };
    latch.disarm();
    latch.releaseNext();
  });
  await expect(page).toHaveURL(/\/archive\?q=WO-NAV-FIRST-101&source=reviewed$/);
  await page.evaluate(
    () => new Promise<void>((r) => requestAnimationFrame(() => setTimeout(r, 0))),
  );

  // Newer typed draft must remain intact, with zero duplicate HTTP search calls!
  await expect(page.getByTestId('archive-query-input')).toHaveValue('WO-NAV-SECOND-202');
  expect(archiveRequests.length).toBe(reqCountBeforeNavSettle);

  // Submitting that preserved draft executes WO-NAV-SECOND-202 cleanly
  await page.getByTestId('archive-submit-btn').click();
  await expect(page).toHaveURL(/\/archive\?q=WO-NAV-SECOND-202&source=reviewed$/);
  await expect(page.getByTestId(`archive-card-${wo2.documentId}`)).toBeVisible();
  await expect(page.getByTestId(`archive-card-${wo1.documentId}`)).toHaveCount(0);

  // (2) Newer submitted query/filter supersedes pending earlier navigation
  await page.getByTestId('archive-clear-btn').click();
  await expect(page).toHaveURL(/\/archive$/);
  await page.evaluate(() => {
    ((window as unknown as Record<string, unknown>)['__e2eArchiveNavLatch'] as { arm: () => void }).arm();
  });
  await page.getByTestId('archive-query-input').fill('WO-NAV-FIRST-101');
  await page.getByTestId('archive-source-select').selectOption('reviewed');
  expect(
    await page.evaluate(
      () => ((window as unknown as Record<string, unknown>)['__e2eArchiveNavLatch'] as { pendingCount: () => number }).pendingCount(),
    ),
  ).toBe(1);

  await page.evaluate(() => {
    ((window as unknown as Record<string, unknown>)['__e2eArchiveNavLatch'] as { disarm: () => void }).disarm();
  });
  await page.getByTestId('archive-query-input').fill('Refrigerator Evaporator');
  await page.getByTestId('archive-source-select').selectOption('machine');
  await page.evaluate(() => {
    ((window as unknown as Record<string, unknown>)['__e2eArchiveNavLatch'] as { releaseAll: () => void }).releaseAll();
  });

  await expect(page).toHaveURL(/\/archive\?q=Refrigerator%20Evaporator&source=machine$/);
  await expect(page.getByTestId('archive-query-input')).toHaveValue('Refrigerator Evaporator');
  await expect(page.getByTestId('archive-source-select')).toHaveValue('machine');
  await expect(page.getByTestId(`archive-card-${mp.documentId}`)).toBeVisible();

  // (3) External browser Back / Forward (popstate) and header routerLink="/archive"
  await page.getByTestId('archive-query-input').fill('WO-NAV-SECOND-202');
  await page.getByTestId('archive-source-select').selectOption('reviewed');
  await expect(page).toHaveURL(/\/archive\?q=WO-NAV-SECOND-202&source=reviewed$/);
  await expect(page.getByTestId(`archive-card-${wo2.documentId}`)).toBeVisible();

  await page.getByTestId('archive-query-input').fill('UNSUBMITTED-SCRATCH');
  await page.goBack();
  await expect(page).toHaveURL(/\/archive\?q=Refrigerator%20Evaporator&source=machine$/);
  await expect(page.getByTestId('archive-query-input')).toHaveValue('Refrigerator Evaporator');
  await expect(page.getByTestId('archive-source-select')).toHaveValue('machine');
  await expect(page.getByTestId(`archive-card-${mp.documentId}`)).toBeVisible();

  await page.goForward();
  await expect(page).toHaveURL(/\/archive\?q=WO-NAV-SECOND-202&source=reviewed$/);
  await expect(page.getByTestId('archive-query-input')).toHaveValue('WO-NAV-SECOND-202');
  await expect(page.getByTestId('archive-source-select')).toHaveValue('reviewed');
  await expect(page.getByTestId(`archive-card-${wo2.documentId}`)).toBeVisible();

  await page.getByTestId('nav-archive').click();
  await expect(page).toHaveURL(/\/archive$/);
  await expect(page.getByTestId('archive-query-input')).toHaveValue('');
  await expect(page.getByTestId('archive-source-select')).toHaveValue('all');

  // (4) Invalid 9-word query hides stale prior cards/cursors and Clear recovers cleanly
  await page.getByTestId('archive-query-input').fill('w1 w2 w3 w4 w5 w6 w7 w8 w9');
  await page.getByTestId('archive-submit-btn').click();
  await expect(page.getByTestId('archive-error')).toBeVisible();
  await expect(page.getByTestId('archive-results-section')).toHaveCount(0);

  await page.getByTestId('archive-clear-btn').click();
  await expect(page).toHaveURL(/\/archive$/);
  await expect(page.getByTestId('archive-error')).toHaveCount(0);
  await expect(page.getByTestId(`archive-card-${wo2.documentId}`)).toBeVisible();

  evidence.push({
    check: 'F4-04 / WP-0010-006 pending navigation draft preservation + newer submit authority + Back/Forward + consistency',
    wo1DocumentId: wo1.documentId,
    wo2DocumentId: wo2.documentId,
    mpDocumentId: mp.documentId,
  });
});
