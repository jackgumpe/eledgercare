import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, HostListener, computed, effect, inject, input, signal } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { Router, RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { isUncertainFailure } from '../intake/submission-api';
import { buildRelativePdfPreviewHref, trustSameOriginPdfPreviewUrl } from './pdf-preview-url';
import { ReviewApi } from './review-api';
import {
  DocumentReviewView,
  MachineFieldCandidate,
  ReviewFieldDecision,
  ReviewFieldView,
  ReviewProblemBody,
  ReviewRevisionDetail,
  ReviewRevisionStatus,
  ReviewRevisionSummary,
  SaveReviewRevisionRequest,
  SelectedReviewRevisionView,
  SourceCoordinateInput,
  SourceReference,
} from './review-models';

interface EditableFieldState {
  ordinal: number;
  fieldKey: string;
  label: string;
  maxLength: number;
  multiline: boolean;
  machineCandidate: MachineFieldCandidate;
  decision: ReviewFieldDecision;
  editValue: string;
  unknownReason: string;
  consultedSource: SourceReference | null;
}

interface PendingReviewSave {
  idempotencyKey: string;
  requestBody: SaveReviewRevisionRequest;
  uncertain: boolean;
}

interface StaleConflictInfo {
  expectedRevision: number;
  currentRevisionNumber: number;
  currentReviewState: string;
  detail: string;
  fetchedServerHead: DocumentReviewView | null;
}

/**
 * Two-pane work-order source comparison and human review screen (/documents/:documentId/review).
 * - Renders all model/human text exclusively via inert Angular text interpolation ({{ ... }});
 *   zero innerHTML or bypassSecurityTrustHtml anywhere.
 * - Native PDF preview URL is gated through trustSameOriginPdfPreviewUrl (F3-BIC-04) and remounted
 *   on page navigation so #page=1..3 navigates reliably in Microsoft Edge PDFium.
 * - Retains uncertain/stale edits strictly in component memory (zero browser storage writes, F3-BIC-05).
 */
@Component({
  selector: 'elc-work-order-review-page',
  imports: [RouterLink],
  template: `
    <div class="review-workspace" data-testid="review-workspace">
      <header class="review-topbar">
        <div>
          <h2>Work-order review &amp; source comparison</h2>
          <p class="note">
            Profile <code>maintenance-work-order/1</code> · Local unauthenticated operator review.
            Unsaved edits and pending retries remain in page memory only (never written to browser storage).
          </p>
        </div>
        <div class="review-topbar-links">
          <a [routerLink]="['/documents', documentId()]" data-testid="back-to-document">
            &larr; Extraction &amp; provenance screen
          </a>
        </div>
      </header>

      @if (loading()) {
        <section><p>Loading work-order review…</p></section>
      } @else if (loadError(); as err) {
        <section class="error note-box" data-testid="review-load-error">
          <p><strong>Unable to open work-order review</strong></p>
          <p>{{ err }}</p>
          <p><a [routerLink]="['/documents', documentId()]">Return to document screen</a></p>
        </section>
      } @else if (reviewHead(); as head) {
        <!-- Status & Reconciliation Banners -->
        <section class="review-status-section" data-testid="review-state-banner">
          <div class="review-state-row">
            <div>
              <strong>Current state: </strong>
              <span class="status" data-testid="review-status-badge">{{ activeBannerStatusLabel() }}</span>
              <span class="note">
                · Head revision <strong data-testid="current-revision-number">#{{ head.currentRevisionNumber }}</strong>
                (of {{ head.maxRevisions }} max)
                · Result <code data-testid="review-result-id">{{ head.resultId }}</code>
                · Raw SHA-256 <code data-testid="review-raw-sha256">{{ head.rawSha256 }}</code>
              </span>
            </div>
            @if (hasPriorReviewedWhileCurrentlyDraft()) {
              <div class="warning note-box compact-box" data-testid="prior-reviewed-historical-warning">
                <strong>Current head (#{{ head.currentRevisionNumber }}) is an unapproved draft.</strong>
                Earlier reviewed revision(s) remain in history and do not approve newer draft edits.
              </div>
            }
          </div>

          @if (selectedHistorical(); as histView) {
            <div class="warning note-box" data-testid="historical-revision-banner">
              <p>
                <strong>
                  Viewing immutable historical Revision #{{ histView.revision.revisionNumber }}
                  ({{ histView.revision.status }})
                </strong>
                — saved {{ histView.revision.savedAtUtc }}
                @if (histView.revision.operatorDisplayLabel; as op) {
                  by <span>{{ op }}</span>
                }
                (current head is Revision #{{ histView.currentRevisionNumber }}: {{ histView.currentReviewState }}).
              </p>
              <p>
                <button type="button" data-testid="return-to-current-head" (click)="returnToCurrentHead()">
                  Return to current head (#{{ histView.currentRevisionNumber }})
                </button>
              </p>
            </div>
          }

          @if (replayedHistoricalNotice(); as replayMsg) {
            <div class="warning note-box" data-testid="replayed-historical-notice">
              <p><strong>Earlier operation reconciled without overwriting newer head:</strong> {{ replayMsg }}</p>
              <button type="button" data-testid="dismiss-replayed-notice" (click)="replayedHistoricalNotice.set(null)">
                Dismiss notice
              </button>
            </div>
          }

          @if (pendingSave(); as pending) {
            @if (pending.uncertain) {
              <div class="warning note-box" data-testid="uncertain-save-banner">
                <p>
                  <strong>Save outcome unknown (network error, timeout, or HTTP 5xx).</strong>
                  Your operation key (<code data-testid="pending-review-key">{{ pending.idempotencyKey }}</code>)
                  and exact five-field edits are retained in page memory. Do not assume failure: the revision may have committed.
                </p>
                <p>
                  <button
                    type="button"
                    data-testid="retry-uncertain-save"
                    [disabled]="saving()"
                    (click)="retryPendingUncertainSave()"
                  >
                    {{ saving() ? 'Retrying…' : 'Retry save with same Idempotency-Key' }}
                  </button>
                  <button
                    type="button"
                    data-testid="reconcile-server-state"
                    [disabled]="saving()"
                    (click)="inspectServerDuringUncertainty()"
                  >
                    Check committed server state
                  </button>
                </p>
                @if (uncertaintyObservation(); as obs) {
                  <p class="note" data-testid="uncertainty-server-observation">{{ obs }}</p>
                }
              </div>
            }
          }

          @if (staleConflict(); as conflict) {
            <div class="error note-box" data-testid="stale-conflict-banner">
              <p>
                <strong>Stale revision conflict (HTTP 409):</strong> {{ conflict.detail }}
              </p>
              <p class="note">
                Your unsaved edits based on Revision #{{ conflict.expectedRevision }} are preserved in page memory below.
                Server head is now Revision <strong data-testid="conflict-current-revision">#{{ conflict.currentRevisionNumber }}</strong>
                ({{ conflict.currentReviewState }}).
              </p>
              <p>
                <button
                  type="button"
                  data-testid="inspect-conflict-head"
                  [disabled]="saving()"
                  (click)="fetchConflictServerHead()"
                >
                  Inspect server Revision #{{ conflict.currentRevisionNumber }}
                </button>
                <button
                  type="button"
                  data-testid="reload-discard-stale"
                  [disabled]="saving()"
                  (click)="reloadAndDiscardUnsavedEdits()"
                >
                  Reload server Revision #{{ conflict.currentRevisionNumber }} (discard unsaved memory)
                </button>
                @if (conflict.fetchedServerHead) {
                  <button
                    type="button"
                    data-testid="reconcile-onto-latest"
                    [disabled]="saving()"
                    (click)="adoptLatestBaseKeepingUnsavedEdits()"
                  >
                    Keep my current edits atop Revision #{{ conflict.fetchedServerHead.currentRevisionNumber }}
                  </button>
                }
              </p>
              @if (conflict.fetchedServerHead?.currentRevision; as srvRev) {
                <div class="conflict-diff-box" data-testid="conflict-server-summary">
                  <strong>Committed server Revision #{{ srvRev.revisionNumber }} ({{ srvRev.status }}):</strong>
                  <ul>
                    @for (sf of conflict.fetchedServerHead!.fields; track sf.fieldKey) {
                      <li>
                        <code>{{ sf.fieldKey }}</code>: <strong>{{ sf.decision }}</strong>
                        — {{ sf.value !== null ? sf.value : '(no value)' }}
                      </li>
                    }
                  </ul>
                </div>
              }
            </div>
          }

          @if (validationError(); as valErr) {
            <div class="error note-box" data-testid="review-validation-error">
              <p><strong>Save rejected:</strong> {{ valErr }}</p>
            </div>
          }

          @if (saveSuccessMessage(); as okMsg) {
            <div class="note-box success-box" data-testid="review-save-receipt">
              <p>{{ okMsg }}</p>
            </div>
          }
        </section>

        <!-- Two-Pane Comparison Workspace -->
        <div class="review-two-pane">
          <!-- Left Pane: Native Original PDF Viewer -->
          <section class="pdf-pane" data-testid="pdf-source-pane">
            <div class="pdf-toolbar">
              <div>
                <strong>Original PDF</strong>
                <span class="note" data-testid="pdf-current-page">
                  · Page {{ currentPage() }} of {{ head.pageCount }}
                </span>
              </div>
              <div class="pdf-page-controls" role="group" aria-label="PDF page navigation">
                @for (pg of pageNumbers(); track pg) {
                  <button
                    type="button"
                    [class.active-page]="currentPage() === pg"
                    [attr.data-testid]="'pdf-page-btn-' + pg"
                    (click)="goToPage(pg)"
                  >
                    Page {{ pg }}
                  </button>
                }
              </div>
              <div class="pdf-fallback-links">
                <a
                  [href]="currentPreviewHref()"
                  target="_blank"
                  rel="noopener"
                  data-testid="pdf-open-fallback"
                >
                  Open PDF
                </a>
                ·
                <a [href]="head.originalUrl" download data-testid="pdf-download-fallback">
                  Download original ({{ head.originalByteLength }} B)
                </a>
              </div>
            </div>

            <div class="pdf-frame-container">
              @for (frameKey of [viewerFrameKey()]; track frameKey) {
                <iframe
                  class="pdf-preview-frame"
                  data-testid="pdf-preview-frame"
                  title="Original submitted PDF page preview"
                  [src]="safePreviewResourceUrl()"
                ></iframe>
              }
            </div>
            <p class="note">
              Original SHA-256: <code data-testid="review-original-sha256">{{ head.originalSha256 }}</code>
            </p>
          </section>

          <!-- Right Pane: Five Work-Order Fields & Review Controls -->
          <section class="fields-pane" data-testid="fields-review-pane">
            @if (selectedHistorical(); as hist) {
              <h3>Historical snapshot — Revision #{{ hist.revision.revisionNumber }} ({{ hist.revision.status }})</h3>
              @for (hf of hist.fields; track hf.fieldKey) {
                <article class="field-card" [attr.data-testid]="'historical-field-' + hf.fieldKey">
                  <div class="field-header">
                    <strong>{{ hf.label }}</strong>
                    <span class="status" [attr.data-testid]="'historical-decision-' + hf.fieldKey">{{ hf.decision }}</span>
                  </div>
                  <div class="machine-box">
                    <span class="note">Immutable machine candidate ({{ hf.machineCandidate.status }}): </span>
                    <code>{{ hf.machineCandidate.value ?? 'none' }}</code>
                    @if (hf.machineCandidate.source; as msrc) {
                      <button
                        type="button"
                        class="link-btn"
                        (click)="goToPage(msrc.pageNumber)"
                      >
                        Page {{ msrc.pageNumber }}, Block {{ msrc.blockOrdinal }}
                      </button>
                    }
                  </div>
                  <dl class="compact-dl">
                    <dt>Saved human value</dt>
                    <dd [attr.data-testid]="'historical-value-' + hf.fieldKey">{{ hf.value ?? '(none — ' + hf.decision + ')' }}</dd>
                    @if (hf.unknownReason) {
                      <dt>Unknown reason</dt>
                      <dd [attr.data-testid]="'historical-reason-' + hf.fieldKey">{{ hf.unknownReason }}</dd>
                    }
                    @if (hf.consultedSource; as csrc) {
                      <dt>Consulted source</dt>
                      <dd>
                        Page {{ csrc.pageNumber }}, Block {{ csrc.blockOrdinal }} — quote: {{ csrc.sourceQuote }}
                      </dd>
                    }
                  </dl>
                </article>
              }
            } @else {
              <h3>Five work-order fields (<code>{{ head.fieldSchemaVersion }}</code>)</h3>

              @for (f of editableFields(); track f.fieldKey) {
                <article class="field-card" [attr.data-testid]="'review-field-' + f.fieldKey">
                  <div class="field-header">
                    <div>
                      <strong>{{ f.label }}</strong>
                      <span class="note"> (<code>{{ f.fieldKey }}</code> · max {{ f.maxLength }} chars)</span>
                    </div>
                    <span class="status" [attr.data-testid]="'field-decision-' + f.fieldKey">{{ f.decision }}</span>
                  </div>

                  <!-- Immutable Machine Candidate & Provenance -->
                  <div class="machine-box" [attr.data-testid]="'machine-candidate-' + f.fieldKey">
                    <div class="machine-row">
                      <span>
                        <strong>Machine candidate ({{ f.machineCandidate.status }}): </strong>
                        @if (f.machineCandidate.value !== null) {
                          <span class="machine-value" [attr.data-testid]="'machine-value-' + f.fieldKey">{{ f.machineCandidate.value }}</span>
                        } @else {
                          <em [attr.data-testid]="'machine-value-' + f.fieldKey">No suggestion ({{ f.machineCandidate.status }})</em>
                        }
                      </span>
                      @if (f.machineCandidate.source; as src) {
                        <button
                          type="button"
                          class="small-btn"
                          [attr.data-testid]="'jump-source-' + f.fieldKey"
                          (click)="goToPage(src.pageNumber)"
                        >
                          View Page {{ src.pageNumber }} (block {{ src.blockOrdinal }}@if (src.tableRow !== null) {, r{{ src.tableRow }}:c{{ src.tableColumn }}})
                        </button>
                      }
                    </div>
                    @if (f.machineCandidate.source; as srcQuote) {
                      <p class="quote-line" [attr.data-testid]="'machine-quote-' + f.fieldKey">
                        Source quote: {{ srcQuote.sourceQuote }}
                      </p>
                    }
                    @if (f.machineCandidate.competingSources.length > 0) {
                      <div class="competing-sources" [attr.data-testid]="'competing-sources-' + f.fieldKey">
                        <p class="note"><strong>Ambiguous competing candidates (not auto-selected):</strong></p>
                        <ul>
                          @for (comp of f.machineCandidate.competingSources; track $index) {
                            <li>
                              Page {{ comp.pageNumber }}, Block {{ comp.blockOrdinal }}:
                              {{ comp.sourceQuote }}
                              <button type="button" class="small-btn" (click)="goToPage(comp.pageNumber)">
                                Page {{ comp.pageNumber }}
                              </button>
                            </li>
                          }
                        </ul>
                      </div>
                    }
                  </div>

                  <!-- Explicit Operator Decision Buttons -->
                  <div class="decision-buttons" role="group" [attr.aria-label]="f.label + ' decision'">
                    <button
                      type="button"
                      class="small-btn"
                      [class.selected-decision]="f.decision === 'accepted'"
                      [disabled]="!canAcceptCandidate(f) || isEditorLocked()"
                      [attr.data-testid]="'btn-accept-' + f.fieldKey"
                      (click)="chooseAccept(f.fieldKey)"
                    >
                      Accept suggestion
                    </button>
                    <button
                      type="button"
                      class="small-btn"
                      [class.selected-decision]="f.decision === 'edited'"
                      [disabled]="isEditorLocked()"
                      [attr.data-testid]="'btn-edit-' + f.fieldKey"
                      (click)="chooseEdit(f.fieldKey)"
                    >
                      Edit value
                    </button>
                    <button
                      type="button"
                      class="small-btn"
                      [class.selected-decision]="f.decision === 'unknown'"
                      [disabled]="isEditorLocked()"
                      [attr.data-testid]="'btn-unknown-' + f.fieldKey"
                      (click)="chooseUnknown(f.fieldKey)"
                    >
                      Mark unknown
                    </button>
                    <button
                      type="button"
                      class="small-btn"
                      [class.selected-decision]="f.decision === 'unreviewed'"
                      [disabled]="isEditorLocked()"
                      [attr.data-testid]="'btn-unreviewed-' + f.fieldKey"
                      (click)="chooseUnreviewed(f.fieldKey)"
                    >
                      Leave unreviewed
                    </button>
                  </div>

                  <!-- Human Value Input -->
                  <div class="field-input-wrap">
                    @if (f.multiline) {
                      <textarea
                        rows="4"
                        class="field-textarea"
                        [attr.maxlength]="f.maxLength"
                        [disabled]="f.decision === 'unknown' || isEditorLocked()"
                        [value]="f.editValue"
                        [placeholder]="f.decision === 'unknown' ? 'Marked unknown (no asserted value)' : 'Enter human-verified narrative…'"
                        [attr.data-testid]="'input-value-' + f.fieldKey"
                        (input)="onValueInput(f.fieldKey, $any($event.target).value)"
                      ></textarea>
                    } @else {
                      <input
                        type="text"
                        class="field-input"
                        [attr.maxlength]="f.maxLength"
                        [disabled]="f.decision === 'unknown' || isEditorLocked()"
                        [value]="f.editValue"
                        [placeholder]="f.decision === 'unknown' ? 'Marked unknown (no asserted value)' : 'Enter human-verified value…'"
                        [attr.data-testid]="'input-value-' + f.fieldKey"
                        (input)="onValueInput(f.fieldKey, $any($event.target).value)"
                      />
                    }
                    <div class="char-counter note">
                      {{ f.editValue.length }} / {{ f.maxLength }} UTF-16 code units
                    </div>
                  </div>

                  @if (f.decision === 'unknown') {
                    <div class="unknown-reason-wrap">
                      <label class="note" [attr.for]="'reason-' + f.fieldKey">
                        Unknown reason (optional, single-line, max 500 chars):
                      </label>
                      <input
                        [id]="'reason-' + f.fieldKey"
                        type="text"
                        class="field-input"
                        maxlength="500"
                        [disabled]="isEditorLocked()"
                        [value]="f.unknownReason"
                        placeholder="e.g., Unit illegible or absent on page"
                        [attr.data-testid]="'input-unknown-reason-' + f.fieldKey"
                        (input)="onUnknownReasonInput(f.fieldKey, $any($event.target).value)"
                      />
                    </div>
                  }
                </article>
              }

              <!-- Operator Label & Save Controls -->
              <div class="save-panel" data-testid="review-save-panel">
                <div class="operator-label-wrap">
                  <label for="operator-label-input">
                    <strong>Operator display label</strong>
                    <span class="note"> (optional self-reported local note, max 80 chars — unauthenticated)</span>
                  </label>
                  <input
                    id="operator-label-input"
                    type="text"
                    class="field-input"
                    maxlength="80"
                    [disabled]="isEditorLocked()"
                    [value]="operatorDisplayLabel()"
                    placeholder="e.g., Desk operator A"
                    data-testid="input-operator-label"
                    (input)="onOperatorLabelInput($any($event.target).value)"
                  />
                </div>

                <div class="review-summary-box" data-testid="unknown-summary">
                  <p>
                    <strong>Decision summary:</strong>
                    {{ decisionCounts().accepted }} accepted ·
                    {{ decisionCounts().edited }} edited ·
                    {{ decisionCounts().unknown }} unknown ·
                    {{ decisionCounts().unreviewed }} unreviewed
                  </p>
                  @if (unknownFieldLabels().length > 0) {
                    <p class="warning-inline" data-testid="unknown-fields-list">
                      <strong>Fields marked unknown ({{ unknownFieldLabels().length }}):</strong>
                      {{ unknownFieldLabels().join(', ') }}.
                      A reviewed revision with unknowns is valid and does not claim factual completeness.
                    </p>
                  } @else {
                    <p class="note" data-testid="unknown-fields-list">Fields marked unknown (0): none.</p>
                  }

                  <label class="confirm-row">
                    <input
                      type="checkbox"
                      [checked]="confirmReviewed()"
                      [disabled]="decisionCounts().unreviewed > 0 || isEditorLocked()"
                      data-testid="confirm-reviewed-checkbox"
                      (change)="confirmReviewed.set($any($event.target).checked)"
                    />
                    <span>
                      I confirm all five field decisions (including {{ unknownFieldLabels().length }} unknown field{{ unknownFieldLabels().length === 1 ? '' : 's' }})
                      after comparing against the original PDF.
                    </span>
                  </label>
                </div>

                @if (!head.canSaveRevision) {
                  <p class="error note-box" data-testid="revision-cap-notice">
                    Maximum of {{ head.maxRevisions }} revisions reached for this extraction result; history remains readable.
                  </p>
                }

                <div class="save-actions">
                  <button
                    type="button"
                    data-testid="save-draft"
                    [disabled]="!head.canSaveRevision || isEditorLocked() || staleConflict() !== null"
                    (click)="submitRevision('draft')"
                  >
                    {{ saving() ? 'Saving…' : 'Save draft revision' }}
                  </button>
                  <button
                    type="button"
                    class="primary-btn"
                    data-testid="save-reviewed"
                    [disabled]="
                      !head.canSaveRevision ||
                      isEditorLocked() ||
                      staleConflict() !== null ||
                      decisionCounts().unreviewed > 0 ||
                      !confirmReviewed()
                    "
                    (click)="submitRevision('reviewed')"
                  >
                    {{ saving() ? 'Saving…' : 'Save reviewed revision' }}
                  </button>
                </div>
              </div>
            }

            <!-- Append-Only Revision History -->
            <section class="history-section" data-testid="review-history">
              <h4>Saved revision history ({{ head.history.length }})</h4>
              @if (head.history.length === 0) {
                <p class="note" data-testid="review-history-empty">No saved revisions yet (currently at Revision 0 preview).</p>
              } @else {
                <table class="grid-table">
                  <thead>
                    <tr>
                      <th>Rev</th>
                      <th>Status</th>
                      <th>Summary</th>
                      <th>Operator label</th>
                      <th>Saved (UTC)</th>
                      <th>Snapshot</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (rev of head.history; track rev.revisionId) {
                      <tr [attr.data-testid]="'history-row-' + rev.revisionNumber">
                        <td>
                          #{{ rev.revisionNumber }}
                          @if (rev.isCurrentHead) {
                            <span class="note">(head)</span>
                          }
                        </td>
                        <td [attr.data-testid]="'history-status-' + rev.revisionNumber">{{ rev.status }}</td>
                        <td>
                          {{ rev.acceptedFieldCount }}A / {{ rev.editedFieldCount }}E / {{ rev.unknownFieldCount }}U
                          @if (rev.unreviewedFieldCount > 0) {
                            / {{ rev.unreviewedFieldCount }} unrev
                          }
                        </td>
                        <td>{{ rev.operatorDisplayLabel ?? '—' }}</td>
                        <td>{{ rev.savedAtUtc }}</td>
                        <td>
                          @if (rev.isCurrentHead && !selectedHistorical()) {
                            <span class="note">Active</span>
                          } @else if (rev.isCurrentHead && selectedHistorical()) {
                            <button
                              type="button"
                              class="small-btn"
                              [attr.data-testid]="'view-revision-' + rev.revisionNumber"
                              (click)="returnToCurrentHead()"
                            >
                              Edit head
                            </button>
                          } @else {
                            <button
                              type="button"
                              class="small-btn"
                              [attr.data-testid]="'view-revision-' + rev.revisionNumber"
                              (click)="openHistoricalRevision(rev.revisionNumber)"
                            >
                              View #{{ rev.revisionNumber }}
                            </button>
                          }
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              }
            </section>
          </section>
        </div>
      }
    </div>
  `,
})
export class WorkOrderReviewPage {
  private readonly api = inject(ReviewApi);
  private readonly sanitizer = inject(DomSanitizer);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private destroyed = false;

  readonly documentId = input.required<string>();
  readonly revision = input<string | undefined>(undefined);
  readonly revisionNumber = input<string | undefined>(undefined);

  protected readonly loading = signal(true);
  protected readonly loadError = signal<string | null>(null);
  protected readonly reviewHead = signal<DocumentReviewView | null>(null);
  protected readonly selectedHistorical = signal<SelectedReviewRevisionView | null>(null);

  protected readonly expectedRevision = signal(0);
  protected readonly editableFields = signal<EditableFieldState[]>([]);
  protected readonly operatorDisplayLabel = signal('');
  protected readonly baselineSignature = signal('');
  protected readonly confirmReviewed = signal(false);

  protected readonly currentPage = signal(1);
  protected readonly remountSeq = signal(0);

  protected readonly saving = signal(false);
  protected readonly pendingSave = signal<PendingReviewSave | null>(null);
  protected readonly uncertaintyObservation = signal<string | null>(null);
  protected readonly staleConflict = signal<StaleConflictInfo | null>(null);
  protected readonly replayedHistoricalNotice = signal<string | null>(null);
  protected readonly validationError = signal<string | null>(null);
  protected readonly saveSuccessMessage = signal<string | null>(null);

  protected readonly pageNumbers = computed(() => {
    const count = this.reviewHead()?.pageCount ?? 1;
    return Array.from({ length: count }, (_, idx) => idx + 1);
  });

  protected readonly viewerFrameKey = computed(
    () => `${this.documentId()}:p${this.currentPage()}:r${this.remountSeq()}`,
  );

  protected readonly currentPreviewHref = computed(() => {
    const head = this.reviewHead();
    if (!head) {
      return '';
    }
    return buildRelativePdfPreviewHref(head.documentId, this.currentPage());
  });

  protected readonly safePreviewResourceUrl = computed<SafeResourceUrl>(() => {
    const head = this.reviewHead();
    if (!head) {
      throw new Error('Cannot build SafeResourceUrl before reviewHead is loaded.');
    }
    return trustSameOriginPdfPreviewUrl(this.sanitizer, head.documentId, this.currentPage());
  });

  protected readonly decisionCounts = computed(() => {
    let accepted = 0;
    let edited = 0;
    let unknown = 0;
    let unreviewed = 0;
    for (const f of this.editableFields()) {
      if (f.decision === 'accepted') accepted++;
      else if (f.decision === 'edited') edited++;
      else if (f.decision === 'unknown') unknown++;
      else unreviewed++;
    }
    return { accepted, edited, unknown, unreviewed };
  });

  protected readonly unknownFieldLabels = computed(() =>
    this.editableFields()
      .filter((f) => f.decision === 'unknown')
      .map((f) => f.label),
  );

  protected readonly hasUnsavedEdits = computed(() => {
    if (!this.reviewHead() || this.selectedHistorical()) {
      return false;
    }
    return this.computeEditorSignature(this.editableFields(), this.operatorDisplayLabel()) !== this.baselineSignature();
  });

  protected readonly hasPriorReviewedWhileCurrentlyDraft = computed(() => {
    const head = this.reviewHead();
    if (!head || head.reviewState !== 'draft') {
      return false;
    }
    return head.history.some((r) => r.status === 'reviewed' && r.revisionNumber < head.currentRevisionNumber);
  });

  protected readonly activeBannerStatusLabel = computed(() => {
    if (this.saving()) {
      return 'Saving…';
    }
    if (this.pendingSave()?.uncertain) {
      return 'Save outcome uncertain';
    }
    if (this.staleConflict()) {
      return 'Stale conflict — unsaved edits preserved';
    }
    const hist = this.selectedHistorical();
    if (hist) {
      return `Historical Revision #${hist.revision.revisionNumber} (${hist.revision.status})`;
    }
    if (this.hasUnsavedEdits()) {
      return `Unsaved edits (from Revision #${this.expectedRevision()})`;
    }
    const head = this.reviewHead();
    if (!head || head.currentRevisionNumber === 0) {
      return 'Unreviewed preview (Revision 0)';
    }
    if (head.reviewState === 'draft') {
      return `Saved draft (Revision #${head.currentRevisionNumber})`;
    }
    const unk = head.currentRevision?.unknownFieldCount ?? 0;
    return `Reviewed (Revision #${head.currentRevisionNumber} · ${unk} unknown)`;
  });

  constructor() {
    this.destroyRef.onDestroy(() => {
      this.destroyed = true;
    });

    effect(() => {
      const id = this.documentId();
      const revParam = this.revisionNumber() ?? this.revision();
      void this.loadInitial(id, revParam);
    });
  }

  @HostListener('window:beforeunload', ['$event'])
  protected onBeforeUnload(event: BeforeUnloadEvent): void {
    if (this.hasUnsavedMemoryWarning()) {
      event.preventDefault();
      event.returnValue = '';
    }
  }

  hasUnsavedMemoryWarning(): boolean {
    return this.hasUnsavedEdits() || this.pendingSave() !== null;
  }

  protected isEditorLocked(): boolean {
    return this.saving() || Boolean(this.pendingSave()?.uncertain);
  }

  protected canAcceptCandidate(field: EditableFieldState): boolean {
    return field.machineCandidate.status === 'suggested' && field.machineCandidate.value !== null;
  }

  protected goToPage(page: number): void {
    const maxPage = this.reviewHead()?.pageCount ?? 1;
    if (page < 1 || page > maxPage) {
      return;
    }
    if (this.currentPage() === page) {
      this.remountSeq.update((n) => n + 1);
    } else {
      this.currentPage.set(page);
    }
  }

  protected chooseAccept(fieldKey: string): void {
    this.clearTransientAlerts();
    this.editableFields.update((list) =>
      list.map((f) => {
        if (f.fieldKey !== fieldKey || !this.canAcceptCandidate(f)) {
          return f;
        }
        return {
          ...f,
          decision: 'accepted',
          editValue: f.machineCandidate.value!,
          unknownReason: '',
          consultedSource: f.machineCandidate.source,
        };
      }),
    );
  }

  protected chooseEdit(fieldKey: string): void {
    this.clearTransientAlerts();
    this.confirmReviewed.set(false);
    this.editableFields.update((list) =>
      list.map((f) => {
        if (f.fieldKey !== fieldKey) {
          return f;
        }
        const initialEdit =
          f.editValue.length > 0 ? f.editValue : (f.machineCandidate.value ?? '');
        return {
          ...f,
          decision: 'edited',
          editValue: initialEdit,
          unknownReason: '',
          consultedSource: f.consultedSource ?? f.machineCandidate.source,
        };
      }),
    );
  }

  protected chooseUnknown(fieldKey: string): void {
    this.clearTransientAlerts();
    this.confirmReviewed.set(false);
    this.editableFields.update((list) =>
      list.map((f) =>
        f.fieldKey === fieldKey
          ? {
              ...f,
              decision: 'unknown',
              editValue: '',
              consultedSource: f.consultedSource ?? f.machineCandidate.source,
            }
          : f,
      ),
    );
  }

  protected chooseUnreviewed(fieldKey: string): void {
    this.clearTransientAlerts();
    this.confirmReviewed.set(false);
    this.editableFields.update((list) =>
      list.map((f) =>
        f.fieldKey === fieldKey
          ? {
              ...f,
              decision: 'unreviewed',
              unknownReason: '',
            }
          : f,
      ),
    );
  }

  protected onValueInput(fieldKey: string, nextValue: string): void {
    this.clearTransientAlerts();
    this.confirmReviewed.set(false);
    this.editableFields.update((list) =>
      list.map((f) => {
        if (f.fieldKey !== fieldKey) {
          return f;
        }
        let nextDecision: ReviewFieldDecision = f.decision;
        if (f.decision === 'accepted') {
          nextDecision = nextValue === f.machineCandidate.value ? 'accepted' : 'edited';
        } else if (f.decision === 'unreviewed' && nextValue.trim().length > 0) {
          nextDecision = 'edited';
        } else if (f.decision === 'unknown') {
          nextDecision = 'edited';
        }
        return {
          ...f,
          decision: nextDecision,
          editValue: nextValue,
          unknownReason: '',
          consultedSource: f.consultedSource ?? f.machineCandidate.source,
        };
      }),
    );
  }

  protected onUnknownReasonInput(fieldKey: string, reason: string): void {
    this.clearTransientAlerts();
    this.editableFields.update((list) =>
      list.map((f) => (f.fieldKey === fieldKey ? { ...f, unknownReason: reason } : f)),
    );
  }

  protected onOperatorLabelInput(value: string): void {
    this.clearTransientAlerts();
    this.operatorDisplayLabel.set(value);
  }

  protected async submitRevision(targetStatus: ReviewRevisionStatus): Promise<void> {
    const head = this.reviewHead();
    if (!head || this.saving() || this.pendingSave()?.uncertain) {
      return;
    }

    this.validationError.set(null);
    this.saveSuccessMessage.set(null);

    const fieldsPayload = this.editableFields().map((f) => {
      const trimmedVal = f.editValue.trim();
      const trimmedReason = f.unknownReason.trim();
      let wireValue: string | null = null;
      if (f.decision === 'accepted' || f.decision === 'edited') {
        wireValue = f.editValue;
      } else if (f.decision === 'unreviewed') {
        wireValue = trimmedVal.length > 0 ? f.editValue : null;
      }

      let coord: SourceCoordinateInput | null = null;
      if (f.consultedSource) {
        coord = {
          pageNumber: f.consultedSource.pageNumber,
          blockOrdinal: f.consultedSource.blockOrdinal,
          tableRow: f.consultedSource.tableRow,
          tableColumn: f.consultedSource.tableColumn,
        };
      }

      return {
        fieldKey: f.fieldKey,
        decision: f.decision,
        value: wireValue,
        unknownReason: f.decision === 'unknown' && trimmedReason.length > 0 ? f.unknownReason : null,
        consultedSource: coord,
      };
    });

    for (const fp of fieldsPayload) {
      if ((fp.decision === 'accepted' || fp.decision === 'edited') && (!fp.value || fp.value.trim().length === 0)) {
        this.validationError.set(`Field '${fp.fieldKey}' requires a non-whitespace value when marked '${fp.decision}'.`);
        return;
      }
      if (targetStatus === 'reviewed' && fp.decision === 'unreviewed') {
        this.validationError.set(`Field '${fp.fieldKey}' is still unreviewed; resolve all five fields first.`);
        return;
      }
    }

    const opLabelRaw = this.operatorDisplayLabel();
    const requestBody: SaveReviewRevisionRequest = {
      profileId: head.profileId,
      resultId: head.resultId,
      expectedRevision: this.expectedRevision(),
      status: targetStatus,
      operatorDisplayLabel: opLabelRaw.trim().length > 0 ? opLabelRaw : null,
      fields: fieldsPayload,
    };

    const operation: PendingReviewSave = {
      idempotencyKey: crypto.randomUUID(),
      requestBody,
      uncertain: false,
    };
    this.pendingSave.set(operation);
    await this.executeSaveOperation(operation);
  }

  protected async retryPendingUncertainSave(): Promise<void> {
    const pending = this.pendingSave();
    if (!pending || this.saving()) {
      return;
    }
    await this.executeSaveOperation(pending);
  }

  protected async inspectServerDuringUncertainty(): Promise<void> {
    const head = this.reviewHead();
    const pending = this.pendingSave();
    if (!head || !pending || this.saving()) {
      return;
    }
    try {
      const latest = await firstValueFrom(this.api.getReview(head.documentId));
      if (this.destroyed) {
        return;
      }
      if (latest.currentRevision && latest.currentRevision.idempotencyKey === pending.idempotencyKey) {
        // Our uncertain save DID commit and IS the current head!
        this.pendingSave.set(null);
        this.uncertaintyObservation.set(null);
        this.applyHeadView(latest, true);
        this.saveSuccessMessage.set(
          `Confirmed committed Revision #${latest.currentRevisionNumber} (${latest.reviewState}) for Idempotency-Key ${pending.idempotencyKey}.`,
        );
        return;
      }
      this.uncertaintyObservation.set(
        `Server head is currently Revision #${latest.currentRevisionNumber} (${latest.reviewState}). ` +
          `Use "Retry save with same Idempotency-Key" to replay or complete your pending operation safely.`,
      );
    } catch {
      this.uncertaintyObservation.set('Could not reach server yet; pending operation remains preserved in memory.');
    }
  }

  protected async fetchConflictServerHead(): Promise<void> {
    const head = this.reviewHead();
    const conflict = this.staleConflict();
    if (!head || !conflict || this.saving()) {
      return;
    }
    try {
      const latest = await firstValueFrom(this.api.getReview(head.documentId));
      if (this.destroyed) {
        return;
      }
      this.staleConflict.set({
        ...conflict,
        currentRevisionNumber: latest.currentRevisionNumber,
        currentReviewState: latest.reviewState,
        fetchedServerHead: latest,
      });
    } catch {
      this.validationError.set('Could not fetch the current server revision; try again.');
    }
  }

  protected async reloadAndDiscardUnsavedEdits(): Promise<void> {
    const head = this.reviewHead();
    if (!head || this.saving()) {
      return;
    }
    this.staleConflict.set(null);
    this.pendingSave.set(null);
    this.validationError.set(null);
    const latest = await firstValueFrom(this.api.getReview(head.documentId));
    if (!this.destroyed) {
      this.applyHeadView(latest, true);
    }
  }

  protected adoptLatestBaseKeepingUnsavedEdits(): void {
    const conflict = this.staleConflict();
    const latest = conflict?.fetchedServerHead;
    if (!conflict || !latest) {
      return;
    }
    // Advance only the base head metadata & expectedRevision while keeping the operator's unsaved field edits intact!
    this.reviewHead.set(latest);
    this.expectedRevision.set(latest.currentRevisionNumber);
    this.baselineSignature.set(
      this.computeEditorSignature(
        this.mapFieldsToEditable(latest.fields),
        latest.currentRevision?.operatorDisplayLabel ?? '',
      ),
    );
    this.staleConflict.set(null);
    this.confirmReviewed.set(false);
    this.saveSuccessMessage.set(
      `Reconciled editor base to Revision #${latest.currentRevisionNumber}; review your preserved edits and save explicitly.`,
    );
  }

  protected async openHistoricalRevision(revNum: number): Promise<void> {
    const head = this.reviewHead();
    if (!head) {
      return;
    }
    if (this.hasUnsavedMemoryWarning()) {
      const proceed = window.confirm(
        'Switch to historical snapshot? Any unsaved field edits in memory will be discarded.',
      );
      if (!proceed) {
        return;
      }
      this.pendingSave.set(null);
      this.staleConflict.set(null);
      this.applyHeadView(head, true);
    }

    try {
      const snap = await firstValueFrom(this.api.getRevision(head.documentId, revNum));
      if (!this.destroyed) {
        this.selectedHistorical.set(snap);
        void this.router.navigate(['/documents', head.documentId, 'review'], {
          queryParams: { revision: revNum },
          replaceUrl: true,
        });
      }
    } catch {
      this.validationError.set(`Could not load Revision #${revNum}.`);
    }
  }

  protected returnToCurrentHead(): void {
    const head = this.reviewHead();
    this.selectedHistorical.set(null);
    if (head) {
      void this.router.navigate(['/documents', head.documentId, 'review'], {
        queryParams: {},
        replaceUrl: true,
      });
    }
  }

  private async executeSaveOperation(operation: PendingReviewSave): Promise<void> {
    const head = this.reviewHead();
    if (!head) {
      return;
    }
    this.saving.set(true);
    this.validationError.set(null);
    this.uncertaintyObservation.set(null);

    try {
      const response = await firstValueFrom(
        this.api.saveRevision(head.documentId, operation.idempotencyKey, operation.requestBody),
      );
      if (this.destroyed) {
        return;
      }
      const body = response.body!;
      this.pendingSave.set(null);
      this.staleConflict.set(null);

      if (!body.isCurrentHead) {
        // Replay of an older committed revision AFTER a newer revision was already committed!
        // Never silently overwrite client state with the older revision (Kickoff L9).
        this.replayedHistoricalNotice.set(
          `Your earlier operation (${operation.idempotencyKey}) had committed as Revision #${body.revision.revisionNumber} ` +
            `(${body.revision.status}), while server head has since advanced to Revision #${body.currentRevisionNumber} ` +
            `(${body.currentReviewState}). Loaded current head Revision #${body.currentRevisionNumber}.`,
        );
        const currentHeadView = await firstValueFrom(this.api.getReview(head.documentId));
        if (!this.destroyed) {
          this.applyHeadView(currentHeadView, true);
        }
        return;
      }

      const updatedHead: DocumentReviewView = {
        ...head,
        reviewState: body.currentReviewState,
        currentRevisionNumber: body.currentRevisionNumber,
        maxRevisions: body.maxRevisions,
        canSaveRevision: body.canSaveRevision,
        machineSnapshot: body.machineSnapshot,
        currentRevision: body.revision,
        fields: body.fields,
        history: body.history,
      };
      this.applyHeadView(updatedHead, true);
      this.saveSuccessMessage.set(
        body.replayed
          ? `Reconciled existing Revision #${body.revision.revisionNumber} (${body.revision.status}) via idempotent replay.`
          : `Saved Revision #${body.revision.revisionNumber} (${body.revision.status}).`,
      );
    } catch (error: unknown) {
      if (this.destroyed) {
        return;
      }
      if (isUncertainFailure(error)) {
        // Retain exact idempotencyKey and requestBody in component memory (never browser storage).
        this.pendingSave.set({ ...operation, uncertain: true });
        return;
      }

      // Definitive 4xx rejection: clear pending operation key so corrected submission gets a fresh key,
      // while preserving all unsaved operator edits in UI memory!
      this.pendingSave.set(null);
      if (error instanceof HttpErrorResponse) {
        const problem = (error.error ?? null) as ReviewProblemBody | null;
        if (error.status === 409 && problem?.code === 'stale_expected_revision') {
          this.staleConflict.set({
            expectedRevision: problem.expectedRevision ?? operation.requestBody.expectedRevision,
            currentRevisionNumber: problem.currentRevisionNumber ?? head.currentRevisionNumber,
            currentReviewState: problem.currentReviewState ?? head.reviewState,
            detail:
              problem.detail ??
              'Another revision was saved since this screen loaded. Your unsaved edits remain in memory.',
            fetchedServerHead: null,
          });
          return;
        }
        this.validationError.set(
          problem?.detail ?? problem?.title ?? `Request rejected (HTTP ${error.status}).`,
        );
        return;
      }
      this.validationError.set('Review save could not be completed.');
    } finally {
      if (!this.destroyed) {
        this.saving.set(false);
      }
    }
  }

  private async loadInitial(documentId: string, revisionParam: string | undefined): Promise<void> {
    this.loading.set(true);
    this.loadError.set(null);
    this.selectedHistorical.set(null);
    this.pendingSave.set(null);
    this.staleConflict.set(null);
    this.validationError.set(null);
    this.saveSuccessMessage.set(null);

    try {
      const head = await firstValueFrom(this.api.getReview(documentId));
      if (this.destroyed || this.documentId() !== documentId) {
        return;
      }
      this.currentPage.set(1);
      this.applyHeadView(head, true);

      if (revisionParam !== undefined && revisionParam !== '') {
        const parsedRev = Number(revisionParam);
        if (
          !Number.isInteger(parsedRev) ||
          parsedRev < 1 ||
          !/^[1-9][0-9]*$/.test(revisionParam)
        ) {
          this.validationError.set(`Invalid revision parameter '${revisionParam}'. Showing current head.`);
        } else if (parsedRev !== head.currentRevisionNumber) {
          const hist = await firstValueFrom(this.api.getRevision(documentId, parsedRev));
          if (!this.destroyed) {
            this.selectedHistorical.set(hist);
          }
        }
      }
    } catch (error: unknown) {
      if (this.destroyed) {
        return;
      }
      if (error instanceof HttpErrorResponse) {
        const problem = (error.error ?? null) as ReviewProblemBody | null;
        this.loadError.set(
          problem?.detail ??
            (error.status === 404
              ? 'Document or requested revision was not found.'
              : error.status === 409
                ? 'A completed extraction result is required before starting a work-order review.'
                : `Review screen could not be loaded (HTTP ${error.status}).`),
        );
      } else {
        this.loadError.set('The work-order review could not be loaded.');
      }
    } finally {
      if (!this.destroyed) {
        this.loading.set(false);
      }
    }
  }

  private applyHeadView(head: DocumentReviewView, resetEditor: boolean): void {
    this.reviewHead.set(head);
    this.selectedHistorical.set(null);
    if (resetEditor) {
      const mapped = this.mapFieldsToEditable(head.fields);
      const opLabel = head.currentRevision?.operatorDisplayLabel ?? '';
      this.expectedRevision.set(head.currentRevisionNumber);
      this.editableFields.set(mapped);
      this.operatorDisplayLabel.set(opLabel);
      this.baselineSignature.set(this.computeEditorSignature(mapped, opLabel));
      this.confirmReviewed.set(false);
    }
  }

  private mapFieldsToEditable(fields: ReviewFieldView[]): EditableFieldState[] {
    return fields.map((f) => ({
      ordinal: f.ordinal,
      fieldKey: f.fieldKey,
      label: f.label,
      maxLength: f.maxLength,
      multiline: f.multiline,
      machineCandidate: f.machineCandidate,
      decision: f.decision,
      editValue: f.value ?? '',
      unknownReason: f.unknownReason ?? '',
      consultedSource: f.consultedSource,
    }));
  }

  private computeEditorSignature(fields: EditableFieldState[], opLabel: string): string {
    return JSON.stringify({
      opLabel,
      fields: fields.map((f) => ({
        k: f.fieldKey,
        d: f.decision,
        v: f.editValue,
        r: f.unknownReason,
      })),
    });
  }

  private clearTransientAlerts(): void {
    this.validationError.set(null);
    this.saveSuccessMessage.set(null);
  }
}

export function unsavedReviewChangesGuard(component: WorkOrderReviewPage): boolean {
  if (!component.hasUnsavedMemoryWarning()) {
    return true;
  }
  return window.confirm(
    'You have unsaved work-order review changes or an uncertain save in page memory. Leave and discard unsaved memory?',
  );
}
