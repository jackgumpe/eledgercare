import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, effect, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { DocumentDetail, DocumentExtractionView, ProblemBody, statusLabel } from './receipt';
import { SubmissionApi } from './submission-api';

const pollIntervalMs = 2_000;

/**
 * Document and unreviewed local extraction result screen (/documents/:documentId).
 * Renders all extracted content exclusively via Angular text interpolation ({{ ... }});
 * never uses innerHTML, bypassSecurityTrustHtml, or dynamic evaluation.
 */
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
          <dd><span class="status" data-testid="document-status">{{ label(extraction()?.status ?? d.status) }}</span></dd>
          <dt>Admitted pages</dt>
          <dd data-testid="document-page-count">{{ d.admittedPageCount }}</dd>
          <dt>Original size</dt>
          <dd data-testid="document-byte-length">{{ d.byteLength }} bytes</dd>
          <dt>SHA-256</dt>
          <dd data-testid="document-sha256">{{ d.sha256 }}</dd>
          <dt>Submitted (UTC)</dt>
          <dd>{{ d.submittedAtUtc }}</dd>
        </dl>
        <p><a [href]="d.originalUrl" download data-testid="document-download">Download original</a></p>
      } @else {
        <p class="error" data-testid="document-error">{{ error() }}</p>
      }
      <p><a routerLink="/">Back to intake</a></p>
    </section>

    @if (extraction(); as ext) {
      <section data-testid="extraction-panel">
        <h3>Local extraction</h3>

        @if (!ext.profileSupported && ext.unavailableReason) {
          <p class="error" data-testid="extraction-unsupported">{{ ext.unavailableReason }}</p>
        } @else if (!ext.workerEnabled && ext.status !== 'completed' && ext.unavailableReason) {
          <p class="warning note-box" data-testid="extraction-unavailable">{{ ext.unavailableReason }}</p>
        }

        @if (actionError(); as errText) {
          <p class="error" data-testid="extraction-action-error">{{ errText }}</p>
        }

        @if (ext.status === 'awaiting_extraction') {
          <p class="note">No extraction attempt has run for this document.</p>
          <p>
            <button
              type="button"
              data-testid="request-extraction"
              [disabled]="!ext.canRequestExtraction || actionInFlight()"
              (click)="startExtraction()"
            >
              {{ actionInFlight() ? 'Requesting…' : 'Extract document' }}
            </button>
            <button type="button" data-testid="refresh-extraction" [disabled]="actionInFlight()" (click)="refresh()">
              Refresh status
            </button>
          </p>
        }

        @if (ext.status === 'queued' || ext.status === 'running') {
          <div class="note-box" data-testid="extraction-active">
            <p>
              <strong>{{ label(ext.status) }}</strong>
              @if (ext.currentAttempt; as cur) {
                — Attempt #{{ cur.attemptNumber }} (phase: <code data-testid="active-phase">{{ cur.phase }}</code>,
                last heartbeat UTC: {{ cur.lastHeartbeatAtUtc }})
              }
            </p>
            <p class="note">Status updates automatically from persisted state. Elapsed stage status is shown instead of an estimated percentage.</p>
          </div>
        }

        @if (ext.status === 'failed' || ext.status === 'interrupted') {
          <div class="error note-box" data-testid="extraction-failure">
            <p>
              <strong>{{ label(ext.status) }}</strong>
              @if (ext.currentAttempt; as cur) {
                (Attempt #{{ cur.attemptNumber }}@if (cur.failureCode) { · code <code>{{ cur.failureCode }}</code> })
              }
            </p>
            @if (ext.currentAttempt?.failureMessage; as msg) {
              <p data-testid="extraction-failure-message">{{ msg }}</p>
            }
            <p>
              <button
                type="button"
                data-testid="retry-extraction"
                [disabled]="!ext.canRetryExtraction || actionInFlight()"
                (click)="retryExtraction()"
              >
                {{ actionInFlight() ? 'Retrying…' : 'Retry extraction' }}
              </button>
            </p>
          </div>
        }

        @if (ext.attempts.length > 0) {
          <details data-testid="attempt-history">
            <summary>Attempt history ({{ ext.attempts.length }})</summary>
            <table class="grid-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Attempt ID</th>
                  <th>Status</th>
                  <th>Phase</th>
                  <th>Started (UTC)</th>
                  <th>Ended (UTC)</th>
                </tr>
              </thead>
              <tbody>
                @for (att of ext.attempts; track att.attemptId) {
                  <tr [attr.data-testid]="'attempt-row-' + att.attemptNumber">
                    <td>{{ att.attemptNumber }}</td>
                    <td><code>{{ att.attemptId }}</code></td>
                    <td>{{ label(att.status) }}</td>
                    <td>{{ att.phase }}</td>
                    <td>{{ att.startedAtUtc }}</td>
                    <td>{{ att.endedAtUtc ?? '—' }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </details>
        }
      </section>

      @if (ext.status === 'completed' && ext.result; as res) {
        <section data-testid="extraction-result">
          <div class="warning note-box" data-testid="unreviewed-banner">
            <strong>Unreviewed raw extraction output ({{ res.reviewStatus }})</strong>
            <p class="note">
              Generated locally by the unmodified OCR model without field validation, correction, or human review.
              Verify against the <a [href]="ext.originalUrl" download>unchanged original PDF</a>.
            </p>
          </div>

          <div class="note-box review-entry-panel" data-testid="work-order-review-summary">
            <div class="review-entry-row">
              <div>
                <strong>Human work-order review (<code>maintenance-work-order/1</code>): </strong>
                @if (ext.workOrderReview; as rev) {
                  <span class="status" data-testid="document-review-status">
                    @if (rev.status === 'reviewed') {
                      Reviewed (Revision #{{ rev.currentRevisionNumber }} · {{ rev.unknownFieldCount }} unknown)
                    } @else {
                      Draft (Revision #{{ rev.currentRevisionNumber }})
                    }
                  </span>
                  <p class="note">
                    {{ rev.acceptedFieldCount }} accepted · {{ rev.editedFieldCount }} edited ·
                    {{ rev.unknownFieldCount }} unknown · {{ rev.unreviewedFieldCount }} unreviewed
                    (updated UTC: {{ rev.updatedAtUtc }}). Raw extraction output below remains untouched.
                  </p>
                } @else {
                  <span class="status" data-testid="document-review-status">Not started</span>
                  <p class="note">
                    Optional operator action: compare the original PDF beside five work-order fields without classifying other document types automatically.
                  </p>
                }
              </div>
              <div>
                <a
                  class="button-link"
                  [routerLink]="['/documents', ext.documentId, 'review']"
                  data-testid="open-work-order-review"
                >
                  {{ ext.workOrderReview ? 'Open work-order review' : 'Review as maintenance work order' }}
                </a>
              </div>
            </div>
          </div>

          <h3>Provenance &amp; run summary</h3>
          <dl data-testid="result-provenance">
            <dt>Result ID</dt>
            <dd data-testid="result-id">{{ res.resultId }}</dd>
            <dt>Attempt ID</dt>
            <dd data-testid="result-attempt-id">{{ res.attemptId }}</dd>
            <dt>Model checkpoint</dt>
            <dd data-testid="result-model">{{ res.provenance.modelRepoId }} &#64; {{ res.provenance.modelRevision }}</dd>
            <dt>Renderer</dt>
            <dd data-testid="result-renderer">{{ res.provenance.rendererIdentity }}</dd>
            <dt>Completed (UTC)</dt>
            <dd data-testid="result-completed-utc">{{ res.completedAtUtc }}</dd>
            <dt>Total duration</dt>
            <dd>{{ res.provenance.totalDurationMs }} ms (load {{ res.provenance.loadDurationMs }} ms, render {{ res.provenance.renderDurationMs }} ms, infer {{ res.provenance.inferDurationMs }} ms)</dd>
            <dt>Raw output size</dt>
            <dd data-testid="result-raw-byte-length">{{ res.rawByteLength }} bytes ({{ res.pageCount }} page{{ res.pageCount === 1 ? '' : 's' }})</dd>
            <dt>Raw output SHA-256</dt>
            <dd data-testid="result-raw-sha256">{{ res.rawSha256 }}</dd>
          </dl>

          <h3>Extracted pages (in document order)</h3>
          <div data-testid="result-pages">
            @for (page of res.pages; track page.pageNumber) {
              <article class="page-card" [attr.data-testid]="'result-page-' + page.pageNumber">
                <h4>Page {{ page.pageNumber }} of {{ res.pageCount }}</h4>
                @for (block of page.blocks; track $index) {
                  @if (block.tableRows && block.tableRows.length > 0) {
                    <div class="table-scroll">
                      <table class="grid-table" [attr.data-testid]="'result-page-' + page.pageNumber + '-table-' + $index">
                        <tbody>
                          @for (row of block.tableRows; track $index) {
                            <tr>
                              @for (cell of row; track $index) {
                                <td>{{ cell }}</td>
                              }
                            </tr>
                          }
                        </tbody>
                      </table>
                    </div>
                  } @else if (block.kind === 'title') {
                    <p class="extracted-title">{{ block.text }}</p>
                  } @else {
                    <p class="extracted-line">{{ block.text }}</p>
                  }
                }
              </article>
            }
          </div>

          <details data-testid="result-raw-details">
            <summary>Exact raw UTF-8 model output</summary>
            <pre class="raw-output" data-testid="result-raw-text">{{ res.rawText }}</pre>
          </details>
        </section>
      }
    }
  `,
})
export class DocumentPage {
  private readonly api = inject(SubmissionApi);
  private readonly destroyRef = inject(DestroyRef);
  private pollHandle: ReturnType<typeof setTimeout> | null = null;
  private destroyed = false;

  readonly documentId = input.required<string>();
  protected readonly loading = signal(true);
  protected readonly document = signal<DocumentDetail | null>(null);
  protected readonly extraction = signal<DocumentExtractionView | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly actionError = signal<string | null>(null);
  protected readonly actionInFlight = signal(false);

  constructor() {
    this.destroyRef.onDestroy(() => {
      this.destroyed = true;
      this.clearPoll();
    });

    effect(() => {
      const id = this.documentId();
      this.clearPoll();
      void this.load(id, true);
    });
  }

  protected label(status: string): string {
    return statusLabel(status);
  }

  protected async refresh(): Promise<void> {
    await this.load(this.documentId(), false);
  }

  protected async startExtraction(): Promise<void> {
    if (this.actionInFlight()) {
      return;
    }
    this.actionInFlight.set(true);
    this.actionError.set(null);
    try {
      const response = await firstValueFrom(this.api.requestExtraction(this.documentId()));
      if (response.body) {
        this.applyExtractionView(response.body);
      }
      await this.load(this.documentId(), false);
    } catch (error: unknown) {
      this.setActionFailure(error);
    } finally {
      this.actionInFlight.set(false);
    }
  }

  protected async retryExtraction(): Promise<void> {
    const priorAttemptId = this.extraction()?.currentAttempt?.attemptId;
    if (!priorAttemptId || this.actionInFlight()) {
      return;
    }
    this.actionInFlight.set(true);
    this.actionError.set(null);
    try {
      const response = await firstValueFrom(this.api.requestExtraction(this.documentId(), priorAttemptId));
      if (response.body) {
        this.applyExtractionView(response.body);
      }
      await this.load(this.documentId(), false);
    } catch (error: unknown) {
      this.setActionFailure(error);
    } finally {
      this.actionInFlight.set(false);
    }
  }

  private async load(documentId: string, showSpinner: boolean): Promise<void> {
    if (showSpinner) {
      this.loading.set(true);
      this.document.set(null);
      this.extraction.set(null);
      this.error.set(null);
    }
    try {
      const [doc, ext] = await Promise.all([
        firstValueFrom(this.api.document(documentId)),
        firstValueFrom(this.api.extraction(documentId)),
      ]);
      if (this.destroyed || this.documentId() !== documentId) {
        return;
      }
      this.document.set(doc);
      this.applyExtractionView(ext);
    } catch (error: unknown) {
      if (this.destroyed) {
        return;
      }
      const status = error instanceof HttpErrorResponse ? error.status : 0;
      this.error.set(
        status === 404
          ? 'Document not found.'
          : status === 400
            ? 'That is not a valid document reference.'
            : 'The document could not be loaded. Try again.',
      );
    } finally {
      if (showSpinner && !this.destroyed) {
        this.loading.set(false);
      }
    }
  }

  private applyExtractionView(ext: DocumentExtractionView): void {
    this.extraction.set(ext);
    this.clearPoll();
    if (!this.destroyed && (ext.status === 'queued' || ext.status === 'running')) {
      const targetId = ext.documentId;
      this.pollHandle = setTimeout(() => {
        if (!this.destroyed && this.documentId() === targetId) {
          void this.load(targetId, false);
        }
      }, pollIntervalMs);
    }
  }

  private setActionFailure(error: unknown): void {
    if (error instanceof HttpErrorResponse) {
      const problem = error.error as ProblemBody | null;
      this.actionError.set(problem?.detail ?? problem?.title ?? `Request rejected (HTTP ${error.status}).`);
      return;
    }
    this.actionError.set('The extraction request could not be completed. Refresh status and try again.');
  }

  private clearPoll(): void {
    if (this.pollHandle !== null) {
      clearTimeout(this.pollHandle);
      this.pollHandle = null;
    }
  }
}
