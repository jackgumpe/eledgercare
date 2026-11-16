import { defineConfig } from '@playwright/test';
import path from 'node:path';

/**
 * Browser checks for the F1/F2/F3 screens. Ports default to F3 author loopback reservations
 * (UI 4410, API 5390 via proxy.conf.mjs) and honor ELEDGERCARE_UI_PORT / ELEDGERCARE_API_PORT
 * so independent review (4510 / 5490) runs the exact frozen candidate without source edits.
 * Uses locally installed Microsoft Edge (channel "msedge"); no browser is downloaded.
 */
const uiPort = process.env['ELEDGERCARE_UI_PORT'] ?? '4410';
const baseUrl = `http://127.0.0.1:${uiPort}`;
const outputRoot = path.resolve(__dirname, '..', '.scratch', 'playwright');

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 90_000,
  outputDir: path.join(outputRoot, 'test-results'),
  reporter: [['list'], ['json', { outputFile: path.join(outputRoot, 'results.json') }]],
  use: {
    baseURL: baseUrl,
    channel: 'msedge',
    headless: true,
    viewport: { width: 1680, height: 980 },
    acceptDownloads: true,
    trace: 'retain-on-failure',
  },
  webServer: {
    command: `npx ng serve --host 127.0.0.1 --port ${uiPort} --proxy-config proxy.conf.mjs`,
    url: baseUrl,
    reuseExistingServer: false,
    timeout: 180_000,
    stdout: 'pipe',
  },
});
