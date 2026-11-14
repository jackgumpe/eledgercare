import { HttpErrorResponse } from '@angular/common/http';
import { Component, effect, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { SubmissionReceipt, statusLabel } from './receipt';
import { SubmissionApi } from './submission-api';

/** Reopens a committed document by its stable reference, e.g. after an application restart. */
@Component({
  selector: 'elc-document-page',
  imports: [RouterLink],
  template: `
    <section>
      <h2>Document</h2>
      @if (loading()) {
        <p>Loading…</p>
      } @else if (document(); as d) {
        <dl data-testid="document">
          <dt>Document reference</dt>
          <dd data-testid="document-id">{{ d.documentId }}</dd>
          <dt>Processing job</dt>
          <dd data-testid="document-job-id">{{ d.jobId }}</dd>
          <dt>Status</dt>
          <dd><span class="status" data-testid="document-status">{{ label(d.status) }}</span></dd>
          <dt>Original size</dt>
          <dd data-testid="document-byte-length">{{ d.byteLength }} bytes</dd>
          <dt>SHA-256</dt>
          <dd data-testid="document-sha256">{{ d.sha256 }}</dd>
          <dt>Submitted (UTC)</dt>
          <dd>{{ d.submittedAtUtc }}</dd>
        </dl>
        <p><a [href]="d.originalUrl" download data-testid="document-download">Download original</a></p>
        <p class="note">No extraction has run for this document.</p>
      } @else {
        <p class="error" data-testid="document-error">{{ error() }}</p>
      }
      <p><a routerLink="/">Back to intake</a></p>
    </section>
  `,
})
export class DocumentPage {
  private readonly api = inject(SubmissionApi);

  readonly documentId = input.required<string>();
  protected readonly loading = signal(true);
  protected readonly document = signal<SubmissionReceipt | null>(null);
  protected readonly error = signal<string | null>(null);

  constructor() {
    effect(() => {
      void this.load(this.documentId());
    });
  }

  protected label(status: string): string {
    return statusLabel(status);
  }

  private async load(documentId: string): Promise<void> {
    this.loading.set(true);
    this.document.set(null);
    this.error.set(null);
    try {
      this.document.set(await firstValueFrom(this.api.document(documentId)));
    } catch (error: unknown) {
      const status = error instanceof HttpErrorResponse ? error.status : 0;
      this.error.set(
        status === 404
          ? 'Document not found.'
          : status === 400
            ? 'That is not a valid document reference.'
            : 'The document could not be loaded. Try again.',
      );
    } finally {
      this.loading.set(false);
    }
  }
}
