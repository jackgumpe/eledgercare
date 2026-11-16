import { HttpClient, HttpErrorResponse, HttpResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, timeout } from 'rxjs';
import { DocumentDetail, DocumentExtractionView, SubmissionReceipt } from './receipt';

/**
 * One pending business submission. The key is created and stored before the first upload attempt
 * and reused for every retry or status query until the outcome is confirmed. Document bytes and
 * contents are never stored in the browser.
 */
export interface PendingSubmission {
  key: string;
  /** True once any attempt ended without a definitive server answer (network error, timeout or 5xx). */
  uncertain: boolean;
}

const storageKey = 'eledgercare.pendingSubmission';
export const submitTimeoutMs = 60_000;

@Injectable({ providedIn: 'root' })
export class SubmissionApi {
  private readonly http = inject(HttpClient);

  loadPending(): PendingSubmission | null {
    const raw = sessionStorage.getItem(storageKey);
    if (!raw) {
      return null;
    }
    try {
      const parsed = JSON.parse(raw) as Partial<PendingSubmission>;
      return typeof parsed.key === 'string' ? { key: parsed.key, uncertain: parsed.uncertain === true } : null;
    } catch {
      return null;
    }
  }

  savePending(pending: PendingSubmission): void {
    sessionStorage.setItem(storageKey, JSON.stringify(pending));
  }

  clearPending(): void {
    sessionStorage.removeItem(storageKey);
  }

  /** Mints a key only when no pending submission exists; a double click cannot create another key. */
  pendingOrNew(): PendingSubmission {
    const existing = this.loadPending();
    if (existing) {
      return existing;
    }
    const created: PendingSubmission = { key: crypto.randomUUID(), uncertain: false };
    this.savePending(created);
    return created;
  }

  submit(key: string, bytes: ArrayBuffer): Observable<HttpResponse<SubmissionReceipt>> {
    return this.http
      .post<SubmissionReceipt>('/api/documents', bytes, {
        headers: { 'Content-Type': 'application/pdf', 'Idempotency-Key': key },
        observe: 'response',
      })
      .pipe(timeout({ first: submitTimeoutMs }));
  }

  submissionByKey(key: string): Observable<SubmissionReceipt> {
    return this.http.get<SubmissionReceipt>(`/api/submissions/${encodeURIComponent(key)}`);
  }

  document(documentId: string): Observable<DocumentDetail> {
    return this.http.get<DocumentDetail>(`/api/documents/${encodeURIComponent(documentId)}`);
  }

  extraction(documentId: string): Observable<DocumentExtractionView> {
    return this.http.get<DocumentExtractionView>(`/api/documents/${encodeURIComponent(documentId)}/extraction`);
  }

  requestExtraction(documentId: string, retryAttemptId?: string): Observable<HttpResponse<DocumentExtractionView>> {
    const url = `/api/documents/${encodeURIComponent(documentId)}/extraction`;
    const body = retryAttemptId ? { retryAttemptId } : {};
    return this.http
      .post<DocumentExtractionView>(url, body, {
        headers: { 'Content-Type': 'application/json' },
        observe: 'response',
      })
      .pipe(timeout({ first: submitTimeoutMs }));
  }
}

/** Network failures, client timeouts and 5xx answers leave the submission outcome unknown. */
export function isUncertainFailure(error: unknown): boolean {
  if (error instanceof HttpErrorResponse) {
    return error.status === 0 || error.status >= 500;
  }
  return true;
}
