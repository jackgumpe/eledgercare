import { defineConfig } from '@playwright/test';
import path from 'node:path';

/**
 * Browser checks for the F1 screen. The Angular dev server (127.0.0.1:4200, /api proxied to
 * 127.0.0.1:5180) is started by Playwright; the API process is started, restarted and stopped by the
 * spec itself so that DI-04 can terminate exactly the process it owns. Uses the locally installed
 * Microsoft Edge (channel "msedge"); no browser is downloaded. Outputs stay in ignored folders.
 */
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
    baseURL: 'http://127.0.0.1:4200',
    channel: 'msedge',
    headless: true,
    acceptDownloads: true,
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'npx ng serve --host 127.0.0.1 --port 4200',
    url: 'http://127.0.0.1:4200',
    reuseExistingServer: false,
    timeout: 180_000,
    stdout: 'pipe',
  },
});
