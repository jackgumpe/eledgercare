import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, effect, inject, input, signal, untracked } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';
import { ProblemBody, statusLabel } from '../intake/receipt';
import { ArchiveApi } from './archive-api';
import {
  ArchiveDocumentCard,
  ArchiveSearchResponse,
  ArchiveSourceFilterWire,
  normalizeArchiveSourceParam,
} from './archive-models';

/**
 * Source-linked maintenance archive browse & keyword search screen (/archive).
 * - Renders all document titles, snippets, and highlight segments strictly through escaped Angular
 *   text interpolation ({{ ... }}); zero innerHTML or bypassSecurityTrustHtml anywhere (F4-BIC-06).
 * - Cancels and ignores obsolete in-flight responses whenever a newer search is issued (F4-04).
 * - Preserves (q, source) in URL query params and resets pagination cursor whenever either changes.
 */
@Component({
  selector: 'elc-archive-page',
  imports: [RouterLink],
  template: `
    <section data-testid="archive-search-panel">
      <div class="review-topbar">
        <div>
          <h2>Saved maintenance document archive</h2>
          <p class="note" data-testid="archive-help-note">
            All words must occur in the same document; word order does not matter. Literal substring matching only
            (ASCII case-insensitive; punctuation, <code>%</code>, <code>_</code>, <code>\\</code>, and leading zeros keep
            literal meaning — no wildcards, Boolean operators, or semantic search). Leave empty to browse saved submissions.
          </p>
        </div>
        <div>
          <a routerLink="/" data-testid="archive-back-to-intake">&larr; Submit a document</a>
        </div>
      </div>

      <form class="archive-search-form" (submit)="onSearchSubmit($event)">
        <div class="archive-form-row">
          <div class="archive-field-grow">
            <label for="archive-query-input"><strong>Keyword query</strong> <span class="note">(max 160 characters, up to 8 words)</span></label>
            <input
              id="archive-query-input"
              type="search"
              class="field-input"
              maxlength="160"
              placeholder="e.g. WO-004192 Hawthorne pump"
              data-testid="archive-query-input"
              [value]="draftQuery()"
              (input)="onQueryInput($event)"
            />
          </div>

          <div class="archive-field-source">
            <label for="archive-source-select"><strong>Source filter</strong></label>
            <select
              id="archive-source-select"
              class="field-input"
              data-testid="archive-source-select"
              [value]="selectedSource()"
              (change)="onSourceChange($event)"
            >
              <option value="all">All sources (machine &amp; reviewed)</option>
              <option value="machine">Machine extraction only</option>
              <option value="reviewed">Reviewed values only</option>
            </select>
          </div>

          <div class="archive-form-buttons">
            <button type="submit" class="primary-btn" data-testid="archive-submit-btn">
              {{ loading() ? 'Searching…' : 'Search' }}
            </button>
            <button
              type="button"
              data-testid="archive-clear-btn"
              [disabled]="draftQuery().length === 0 && activeQuery().length === 0 && selectedSource() === 'all'"
              (click)="clearSearch()"
            >
              Clear
            </button>
          </div>
        </div>
      </form>
    </section>

    @if (loading()) {
      <section data-testid="archive-loading">
        <p>Loading archive results…</p>
      </section>
    }

    @if (errorMessage(); as err) {
      <section class="error note-box" data-testid="archive-error">
        <p><strong>Archive search unavailable or rejected</strong></p>
        <p data-testid="archive-error-detail">{{ err }}</p>
        <p>
          <button type="button" data-testid="archive-retry-btn" (click)="retryCurrentPage()">Retry search</button>
        </p>
      </section>
    }

    @if (response(); as res) {
      <section data-testid="archive-results-section">
        <div class="archive-results-header">
          <div>
            <strong>
              @if (res.terms.length === 0) {
                Browsing saved documents ({{ sourceFilterLabel(res.source) }})
              } @else {
                Search results for “{{ res.query }}” ({{ sourceFilterLabel(res.source) }})
              }
            </strong>
            <span class="note" data-testid="archive-page-indicator"> · Page {{ pageNumber() }}</span>
          </div>

          <div class="archive-pagination-controls" role="group" aria-label="Archive pagination">
            @if (cursorStack().length > 0) {
              <button
                type="button"
                class="small-btn"
                data-testid="archive-first-page"
                [disabled]="loading()"
                (click)="goToFirstPage()"
              >
                First page
              </button>
              <button
                type="button"
                class="small-btn"
                data-testid="archive-prev-page"
                [disabled]="loading()"
                (click)="goToPreviousPage()"
              >
                &larr; Previous
              </button>
            }
            <button
              type="button"
              class="small-btn"
              data-testid="archive-next-page"
              [disabled]="!res.hasMore || !res.nextCursor || loading()"
              (click)="goToNextPage()"
            >
              Next page &rarr;
            </button>
          </div>
        </div>

        @if (res.items.length === 0) {
          <div class="note-box" data-testid="archive-empty">
            @if (res.terms.length === 0) {
              <p>No saved documents match the selected browse filter ({{ sourceFilterLabel(res.source) }}).</p>
            } @else {
              <p>
                No saved documents contain all query terms (<strong>{{ res.terms.join(', ') }}</strong>) in
                {{ sourceFilterLabel(res.source) }}.
              </p>
            }
          </div>
        } @else {
          <div class="archive-card-list" data-testid="archive-card-list">
            @for (item of res.items; track item.documentId) {
              <article class="archive-card" [attr.data-testid]="'archive-card-' + item.documentId">
                <div class="archive-card-header">
                  <div>
                    <h3 class="archive-card-title" [attr.data-testid]="'archive-card-title-' + item.documentId">
                      {{ item.displayTitle }}
                    </h3>
                    <p class="note archive-card-meta">
                      Submitted {{ item.submittedAtUtc }} · {{ item.admittedPageCount }} page{{ item.admittedPageCount === 1 ? '' : 's' }}
                      @if (item.titleFromReviewed && item.latestReviewed; as lr) {
                        · Title from Reviewed Revision #{{ lr.revisionNumber }}
                      }
                    </p>
                  </div>

                  <div class="archive-badges">
                    <span class="status" [attr.data-testid]="'archive-doc-status-' + item.documentId">
                      {{ docStatusLabel(item.status) }}
                    </span>

                    @if (item.latestReviewed; as lrBadge) {
                      <span class="status reviewed-badge" [attr.data-testid]="'archive-review-badge-' + item.documentId">
                        Reviewed (Revision #{{ lrBadge.revisionNumber }})
                      </span>
                    } @else if (item.currentReviewHead; as headBadge) {
                      <span class="status" [attr.data-testid]="'archive-review-badge-' + item.documentId">
                        Draft (Revision #{{ headBadge.currentRevisionNumber }} — unreviewed)
                      </span>
                    } @else if (item.status === 'completed') {
                      <span class="status" [attr.data-testid]="'archive-review-badge-' + item.documentId">
                        Unreviewed
                      </span>
                    }

                    @if (item.hasNewerDraft && item.currentReviewHead; as draftHead) {
                      <span
                        class="status newer-draft-badge"
                        [attr.data-testid]="'archive-newer-draft-' + item.documentId"
                      >
                        Newer draft exists (head Revision #{{ draftHead.currentRevisionNumber }})
                      </span>
                    }
                  </div>
                </div>

                @if (res.terms.length > 0 && item.contributingSources.length > 0) {
                  <p class="note archive-contributing" [attr.data-testid]="'archive-contributing-' + item.documentId">
                    <strong>Matched source{{ item.contributingSources.length === 1 ? '' : 's' }}: </strong>
                    {{ formatContributingSources(item) }}
                  </p>
                }

                @if (item.witnesses.length > 0) {
                  <div class="archive-witness-list" [attr.data-testid]="'archive-witnesses-' + item.documentId">
                    @for (w of item.witnesses; track $index) {
                      <div class="archive-witness-box" [attr.data-testid]="'archive-witness-' + item.documentId + '-' + $index">
                        <div class="archive-witness-header">
                          <div>
                            <strong [attr.data-testid]="'witness-source-label-' + item.documentId + '-' + $index">{{ w.sourceLabel }}</strong>
                            @if (w.sourceKind === 'machine') {
                              @if (w.pageNumber !== null) {
                                <span class="note"> · Page {{ w.pageNumber }}@if (w.isFallback) { (raw fallback)}</span>
                              } @else {
                                <span class="note"> · Document-level raw fallback (no bound page)</span>
                              }
                            } @else if (w.consultedPageNumber !== null) {
                              <span class="note" [attr.data-testid]="'witness-consulted-page-' + item.documentId + '-' + $index">
                                · Recorded source Page {{ w.consultedPageNumber }}
                              </span>
                            }
                            <span class="note"> · Matched: {{ w.matchedTerms.join(', ') }}</span>
                          </div>

                          <div class="archive-witness-actions">
                            @if (w.sourceKind === 'machine') {
                              <a
                                class="small-link-btn"
                                [routerLink]="['/documents', item.documentId]"
                                [queryParams]="buildMachineWitnessQueryParams(w.pageNumber)"
                                [attr.data-testid]="'witness-open-machine-' + item.documentId + '-' + $index"
                              >
                                @if (w.pageNumber !== null) {
                                  Open source PDF Page {{ w.pageNumber }} &amp; result
                                } @else {
                                  Open document &amp; result
                                }
                              </a>
                            } @else if (w.revisionNumber !== null) {
                              <a
                                class="small-link-btn"
                                [routerLink]="['/documents', item.documentId, 'review', 'revisions', w.revisionNumber]"
                                [queryParams]="buildReviewedWitnessQueryParams(w.fieldKey, w.consultedPageNumber)"
                                [attr.data-testid]="'witness-open-reviewed-' + item.documentId + '-' + $index"
                              >
                                Open Reviewed Revision #{{ w.revisionNumber }}@if (w.fieldLabel) { ({{ w.fieldLabel }})}
                              </a>
                            }
                          </div>
                        </div>

                        <p class="archive-snippet" [attr.data-testid]="'archive-snippet-' + item.documentId + '-' + $index">
                          @if (w.prefixClipped) {<span>…</span>}@for (seg of w.segments; track $index) {@if (seg.highlighted) {<mark class="archive-hit">{{ seg.text }}</mark>} @else {<span>{{ seg.text }}</span>}}@if (w.suffixClipped) {<span>…</span>}
                        </p>
                      </div>
                    }
                  </div>
                }

                @if (item.hasMoreMatchesInDocument) {
                  <p class="note" [attr.data-testid]="'archive-more-matches-' + item.documentId">
                    More matches are available by opening this document.
                  </p>
                }

                <div class="archive-card-footer">
                  <div class="archive-card-links">
                    <a
                      [routerLink]="['/documents', item.documentId]"
                      [queryParams]="buildReturnOnlyQueryParams()"
                      [attr.data-testid]="'archive-open-document-' + item.documentId"
                    >
                      Open document &amp; original
                    </a>
                    @if (item.latestReviewed; as lrLink) {
                      ·
                      <a
                        [routerLink]="['/documents', item.documentId, 'review', 'revisions', lrLink.revisionNumber]"
                        [queryParams]="buildReturnOnlyQueryParams()"
                        [attr.data-testid]="'archive-open-latest-reviewed-' + item.documentId"
                      >
                        Open Reviewed Revision #{{ lrLink.revisionNumber }}
                      </a>
                    }
                    @if (item.status === 'completed') {
                      ·
                      <a
                        [routerLink]="['/documents', item.documentId, 'review']"
                        [queryParams]="buildReturnOnlyQueryParams()"
                        [attr.data-testid]="'archive-open-review-head-' + item.documentId"
                      >
                        {{ item.currentReviewHead ? 'Open current review head' : 'Start work-order review' }}
                      </a>
                    }
                  </div>

                  <details class="technical-details" [attr.data-testid]="'archive-provenance-' + item.documentId">
                    <summary>Provenance &amp; technical identifiers</summary>
                    <dl class="compact-dl technical-dl">
                      <dt>Document UUID</dt>
                      <dd [attr.data-testid]="'archive-full-doc-id-' + item.documentId">{{ item.documentId }}</dd>
                      <dt>Original SHA-256</dt>
                      <dd [attr.data-testid]="'archive-orig-sha-' + item.documentId">{{ item.originalSha256 }} ({{ item.originalByteLength }} bytes)</dd>
                      @if (item.machine; as m) {
                        <dt>Extraction result ID</dt>
                        <dd>{{ m.resultId }}</dd>
                        <dt>Raw output SHA-256</dt>
                        <dd>{{ m.rawSha256 }}</dd>
                        <dt>Archive projection</dt>
                        <dd>{{ m.projectionVersion }} · {{ m.projectionSha256 }}@if (m.hasFallback) { (includes fallback)}</dd>
                      }
                    </dl>
                  </details>
                </div>
              </article>
            }
          </div>
        }
      </section>
    }
  `,
})
export class ArchivePage {
  private readonly api = inject(ArchiveApi);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  private activeRequestSeq = 0;
  private inFlightSub: Subscription | null = null;
  private destroyed = false;

  // Bound from URL query parameters (?q=...&source=...) via withComponentInputBinding().
  readonly q = input<string | undefined>(undefined);
  readonly source = input<string | undefined>(undefined);

  protected readonly draftQuery = signal('');
  protected readonly activeQuery = signal('');
  protected readonly selectedSource = signal<ArchiveSourceFilterWire>('all');
  protected readonly cursorStack = signal<(string | null)[]>([]);
  protected readonly currentCursor = signal<string | null>(null);
  protected readonly pageNumber = signal(1);

  protected readonly loading = signal(false);
  protected readonly errorMessage = signal<string | null>(null);
  protected readonly response = signal<ArchiveSearchResponse | null>(null);

  constructor() {
    this.destroyRef.onDestroy(() => {
      this.destroyed = true;
      this.cancelInFlight();
    });

    effect(() => {
      const urlQ = this.q() ?? '';
      const urlSource = normalizeArchiveSourceParam(this.source());

      untracked(() => {
        const queryChanged = urlQ !== this.activeQuery() || urlSource !== this.selectedSource() || this.response() === null;
        this.draftQuery.set(urlQ);
        this.activeQuery.set(urlQ);
        this.selectedSource.set(urlSource);
        if (queryChanged) {
          this.cursorStack.set([]);
          this.currentCursor.set(null);
          this.pageNumber.set(1);
          this.executeSearch(urlQ, urlSource, null);
        }
      });
    });
  }

  protected onQueryInput(event: Event): void {
    const val = (event.target as HTMLInputElement).value;
    this.draftQuery.set(val);
  }

  protected onSourceChange(event: Event): void {
    const nextSource = normalizeArchiveSourceParam((event.target as HTMLSelectElement).value);
    const nextQ = this.draftQuery();
    this.applyNewQueryAndNavigate(nextQ, nextSource);
  }

  protected onSearchSubmit(event: Event): void {
    event.preventDefault();
    this.applyNewQueryAndNavigate(this.draftQuery(), this.selectedSource());
  }

  protected clearSearch(): void {
    this.applyNewQueryAndNavigate('', 'all');
  }

  protected retryCurrentPage(): void {
    this.executeSearch(this.activeQuery(), this.selectedSource(), this.currentCursor());
  }

  protected goToNextPage(): void {
    const res = this.response();
    if (!res?.hasMore || !res.nextCursor || this.loading()) {
      return;
    }
    const prev = this.currentCursor();
    this.cursorStack.update((stack) => [...stack, prev]);
    this.currentCursor.set(res.nextCursor);
    this.pageNumber.update((n) => n + 1);
    this.executeSearch(this.activeQuery(), this.selectedSource(), res.nextCursor);
  }

  protected goToPreviousPage(): void {
    const stack = this.cursorStack();
    if (stack.length === 0 || this.loading()) {
      return;
    }
    const prevCursor = stack[stack.length - 1];
    this.cursorStack.set(stack.slice(0, -1));
    this.currentCursor.set(prevCursor);
    this.pageNumber.update((n) => Math.max(1, n - 1));
    this.executeSearch(this.activeQuery(), this.selectedSource(), prevCursor);
  }

  protected goToFirstPage(): void {
    if (this.cursorStack().length === 0 || this.loading()) {
      return;
    }
    this.cursorStack.set([]);
    this.currentCursor.set(null);
    this.pageNumber.set(1);
    this.executeSearch(this.activeQuery(), this.selectedSource(), null);
  }

  protected docStatusLabel(status: string): string {
    return statusLabel(status);
  }

  protected sourceFilterLabel(source: ArchiveSourceFilterWire): string {
    switch (source) {
      case 'machine':
        return 'machine extraction only';
      case 'reviewed':
        return 'reviewed values only';
      default:
        return 'all sources';
    }
  }

  protected formatContributingSources(item: ArchiveDocumentCard): string {
    return item.contributingSources
      .map((s) => {
        if (s === 'machine') {
          return 'Machine extraction — unreviewed';
        }
        if (s === 'reviewed' && item.latestReviewed) {
          return `Reviewed fields (Revision #${item.latestReviewed.revisionNumber})`;
        }
        return s;
      })
      .join(' + ');
  }

  protected buildReturnOnlyQueryParams(): Record<string, string> {
    const params: Record<string, string> = {
      returnSource: this.selectedSource(),
    };
    if (this.activeQuery().length > 0) {
      params['returnQ'] = this.activeQuery();
    }
    return params;
  }

  protected buildMachineWitnessQueryParams(pageNumber: number | null): Record<string, string | number> {
    const params: Record<string, string | number> = {
      ...this.buildReturnOnlyQueryParams(),
    };
    if (pageNumber !== null && pageNumber >= 1 && pageNumber <= 3) {
      params['page'] = pageNumber;
    }
    return params;
  }

  protected buildReviewedWitnessQueryParams(
    fieldKey: string | null,
    consultedPageNumber: number | null,
  ): Record<string, string | number> {
    const params: Record<string, string | number> = {
      ...this.buildReturnOnlyQueryParams(),
    };
    if (fieldKey) {
      params['field'] = fieldKey;
    }
    // Never fabricate a source page claim when consultedPageNumber is null (F4-BIC-07)!
    if (consultedPageNumber !== null && consultedPageNumber >= 1 && consultedPageNumber <= 3) {
      params['page'] = consultedPageNumber;
    }
    return params;
  }

  private applyNewQueryAndNavigate(nextQ: string, nextSource: ArchiveSourceFilterWire): void {
    this.draftQuery.set(nextQ);
    this.activeQuery.set(nextQ);
    this.selectedSource.set(nextSource);
    this.cursorStack.set([]);
    this.currentCursor.set(null);
    this.pageNumber.set(1);

    const queryParams: Record<string, string | null> = {
      q: nextQ.length > 0 ? nextQ : null,
      source: nextSource !== 'all' ? nextSource : null,
    };

    void this.router.navigate(['/archive'], {
      queryParams,
      replaceUrl: false,
    });

    this.executeSearch(nextQ, nextSource, null);
  }

  private executeSearch(q: string, source: ArchiveSourceFilterWire, after: string | null): void {
    this.cancelInFlight();
    const seq = ++this.activeRequestSeq;
    this.loading.set(true);
    this.errorMessage.set(null);

    this.inFlightSub = this.api.search({ q, source, after }).subscribe({
      next: (res) => {
        if (this.destroyed || seq !== this.activeRequestSeq) {
          return;
        }
        this.response.set(res);
        this.loading.set(false);
      },
      error: (err: unknown) => {
        if (this.destroyed || seq !== this.activeRequestSeq) {
          return;
        }
        this.loading.set(false);
        if (err instanceof HttpErrorResponse) {
          const problem = (err.error ?? null) as ProblemBody | null;
          this.errorMessage.set(
            problem?.detail ?? problem?.title ?? `Archive query failed (HTTP ${err.status}).`,
          );
          return;
        }
        this.errorMessage.set('Archive query could not reach the local API. Retry when ready.');
      },
    });
  }

  private cancelInFlight(): void {
    if (this.inFlightSub) {
      this.inFlightSub.unsubscribe();
      this.inFlightSub = null;
    }
  }
}
