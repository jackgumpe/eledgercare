import { HttpErrorResponse } from '@angular/common/http';
import { Component, ElementRef, inject, signal, viewChild } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ProblemBody, SubmissionReceipt, statusLabel } from './receipt';
import { PendingSubmission, SubmissionApi, isUncertainFailure } from './submission-api';

type Phase = 'idle' | 'sending' | 'receipt' | 'unknown' | 'busy' | 'rejected';

/**
 * Intake screen: select one permitted synthetic PDF, submit it with a stable pending Idempotency-Key,
 * and show the committed receipt. Uncertain outcomes keep the key for status queries or same-key retries.
 */
@Component({
  selector: 'elc-intake-page',
  imports: [RouterLink],
  template: `
    <section>
      <h2>Submit a maintenance PDF</h2>
      <input #fileInput type="file" accept="application/pdf,.pdf" data-testid="file-input" (change)="onFileSelected($event)" />
      @if (selectedFile(); as file) {
        <p class="note" data-testid="local-selection">Selected locally: {{ file.name }} ({{ file.size }} bytes). The file name is not sent.</p>
      }
      <p>
        <button type="button" data-testid="submit" [disabled]="!selectedFile() || phase() === 'sending'" (click)="submit()">
          {{ pending() ? 'Retry with same key' : 'Submit' }}
        </button>
        @if (pending()) {
          <button type="button" data-testid="check-status" [disabled]="phase() === 'sending'" (click)="checkStatus()">Check submission status</button>
        }
        <button type="button" data-testid="new-submission" [disabled]="phase() === 'sending'" (click)="newSubmission()">New submission</button>
      </p>
      @if (pending(); as p) {
        <p class="note">Pending submission key: <code data-testid="pending-key">{{ p.key }}</code></p>
      }
      @if (phase() === 'sending') {
        <p data-testid="sending">Submitting…</p>
      }
    </section>

    @if (phase() === 'unknown') {
      <section class="warning" data-testid="outcome-unknown">
        <h3>Submission outcome unknown</h3>
        <p>
          The server did not confirm this submission. It may or may not have been stored. Check its status, or
          reselect the same file and retry; the same key is reused so a retry cannot create a duplicate.
        </p>
      </section>
    }

    @if (phase() === 'busy') {
      <section class="warning" data-testid="busy">
        <h3>Server busy</h3>
        <p>Too many submissions are in progress. Retry the same file; the same key is kept.</p>
      </section>
    }

    @if (message(); as text) {
      <section [class.error]="phase() === 'rejected'" data-testid="message">
        <p>{{ text }}</p>
      </section>
    }

    @if (receipt(); as r) {
      <section data-testid="receipt">
        <h3>Document stored</h3>
        <dl>
          <dt>Document reference</dt>
          <dd data-testid="receipt-document-id">{{ r.documentId }}</dd>
          <dt>Status</dt>
          <dd><span class="status" data-testid="receipt-status">{{ label(r.status) }}</span></dd>
          <dt>Original size</dt>
          <dd data-testid="receipt-byte-length">{{ r.byteLength }} bytes</dd>
          <dt>SHA-256</dt>
          <dd data-testid="receipt-sha256">{{ r.sha256 }}</dd>
          <dt>Submitted (UTC)</dt>
          <dd>{{ r.submittedAtUtc }}</dd>
        </dl>
        <p>
          <a [href]="r.originalUrl" download data-testid="receipt-download">Download original</a>
          ·
          <a [routerLink]="['/documents', r.documentId]" data-testid="receipt-open">Open document page</a>
        </p>
        <p class="note">No extraction has run at intake. Open the document page to inspect extraction state or saved results.</p>
      </section>
    }

    <section>
      <h2>Reopen a document</h2>
      <input type="text" size="40" placeholder="Document reference (UUID)" data-testid="reopen-input" #reopenInput />
      <button type="button" data-testid="reopen" (click)="reopen(reopenInput.value)">Open</button>
      <p class="note">
        Or <a routerLink="/archive" data-testid="intake-open-archive">browse &amp; search the saved archive</a> by machine text or reviewed work-order values.
      </p>
    </section>
  `,
})
export class IntakePage {
  private readonly api = inject(SubmissionApi);
  private readonly router = inject(Router);
  private readonly fileInput = viewChild.required<ElementRef<HTMLInputElement>>('fileInput');

  protected readonly selectedFile = signal<File | null>(null);
  protected readonly pending = signal<PendingSubmission | null>(this.api.loadPending());
  protected readonly phase = signal<Phase>(this.pending() ? 'unknown' : 'idle');
  protected readonly receipt = signal<SubmissionReceipt | null>(null);
  protected readonly message = signal<string | null>(null);

  protected label(status: string): string {
    return statusLabel(status);
  }

  protected onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedFile.set(input.files?.item(0) ?? null);
  }

  protected async submit(): Promise<void> {
    const file = this.selectedFile();
    if (!file || this.phase() === 'sending') {
      return;
    }

    const pending = this.api.pendingOrNew();
    this.pending.set(pending);
    this.phase.set('sending');
    this.message.set(null);
    this.receipt.set(null);

    try {
      const bytes = await file.arrayBuffer();
      const response = await firstValueFrom(this.api.submit(pending.key, bytes));
      this.resolved(response.body as SubmissionReceipt);
    } catch (error: unknown) {
      this.failed(pending, error);
    }
  }

  protected async checkStatus(): Promise<void> {
    const pending = this.pending();
    if (!pending) {
      return;
    }
    this.message.set(null);
    try {
      this.resolved(await firstValueFrom(this.api.submissionByKey(pending.key)));
    } catch (error: unknown) {
      if (error instanceof HttpErrorResponse && error.status === 404) {
        this.message.set(
          'No committed submission uses this key at this moment. You can reselect the same file and retry with the same key.',
        );
      } else {
        this.message.set('The status check did not complete. Try again.');
      }
    }
  }

  protected newSubmission(): void {
    this.api.clearPending();
    this.pending.set(null);
    this.phase.set('idle');
    this.receipt.set(null);
    this.message.set(null);
    this.selectedFile.set(null);
    this.fileInput().nativeElement.value = '';
  }

  protected reopen(reference: string): void {
    const trimmed = reference.trim();
    if (trimmed) {
      void this.router.navigate(['/documents', trimmed]);
    }
  }

  private resolved(receipt: SubmissionReceipt): void {
    this.api.clearPending();
    this.pending.set(null);
    this.receipt.set(receipt);
    this.phase.set('receipt');
    this.message.set(null);
  }

  private failed(pending: PendingSubmission, error: unknown): void {
    const status = error instanceof HttpErrorResponse ? error.status : 0;
    const problem = error instanceof HttpErrorResponse ? (error.error as ProblemBody | null) : null;

    if (isUncertainFailure(error)) {
      const uncertain = { ...pending, uncertain: true };
      this.api.savePending(uncertain);
      this.pending.set(uncertain);
      this.phase.set('unknown');
      return;
    }

    if (status === 429) {
      this.phase.set(pending.uncertain ? 'unknown' : 'busy');
      return;
    }

    const detail = problem?.detail ?? problem?.title ?? `Request rejected (HTTP ${status}).`;
    if (status === 409 || pending.uncertain) {
      this.phase.set(pending.uncertain ? 'unknown' : 'rejected');
      this.message.set(detail);
      return;
    }

    this.api.clearPending();
    this.pending.set(null);
    this.phase.set('rejected');
    this.message.set(detail);
  }
}
