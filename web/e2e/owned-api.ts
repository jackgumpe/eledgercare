import { ChildProcessWithoutNullStreams, spawn } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';

/**
 * Starts the built ELedgerCare API on 127.0.0.1:5180 as a child process owned by this test run.
 * Requires E2E_DATABASE (prepared by evaluation/product-smoke/run-browser-checks.ps1) and the
 * worktree's .local/secrets/pg-local.json. Only the spawned PID is ever terminated.
 */
export class OwnedApi {
  private child: ChildProcessWithoutNullStreams | null = null;
  readonly starts: { pid: number; startedUtc: string; stoppedUtc?: string }[] = [];

  async start(): Promise<void> {
    const root = path.resolve(__dirname, '..', '..');
    const settings = JSON.parse(readFileSync(path.join(root, '.local', 'secrets', 'pg-local.json'), 'utf8')) as Record<string, string | number>;
    const database = process.env['E2E_DATABASE'];
    if (!database) {
      throw new Error('E2E_DATABASE is required (run evaluation/product-smoke/run-browser-checks.ps1).');
    }
    const apiDir = path.join(root, 'src', 'ELedgerCare.Api', 'bin', 'Release', 'net10.0');
    const connection = `Host=${settings['host']};Port=${settings['port']};Database=${database};Username=${settings['appUser']};Password=${settings['appPassword']}`;

    const child = spawn('dotnet', [path.join(apiDir, 'ELedgerCare.Api.dll')], {
      cwd: apiDir,
      env: { ...process.env, ASPNETCORE_ENVIRONMENT: 'Production', ConnectionStrings__Runtime: connection, Api__Port: '5180', DOTNET_NOLOGO: '1' },
    });
    this.child = child;
    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('API did not start listening within 60 s')), 60_000);
      const onData = (chunk: Buffer) => {
        if (chunk.toString().includes('Now listening on: http://127.0.0.1:5180')) {
          clearTimeout(timer);
          resolve();
        }
      };
      child.stdout.on('data', onData);
      child.stderr.on('data', onData);
      child.on('exit', (code) => {
        clearTimeout(timer);
        reject(new Error(`API exited early with code ${code} (is port 5180 already in use?)`));
      });
    });
    this.starts.push({ pid: child.pid!, startedUtc: new Date().toISOString() });
  }

  /** Abruptly terminates exactly the spawned API process and waits for it to exit. */
  async kill(): Promise<void> {
    const child = this.child;
    if (!child || child.exitCode !== null) {
      return;
    }
    const exited = new Promise<void>((resolve) => child.once('exit', () => resolve()));
    child.kill();
    await exited;
    this.starts[this.starts.length - 1].stoppedUtc = new Date().toISOString();
    this.child = null;
  }
}
