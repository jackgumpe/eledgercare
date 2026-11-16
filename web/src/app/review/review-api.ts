import { HttpClient, HttpResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, timeout } from 'rxjs';
import { submitTimeoutMs } from '../intake/submission-api';
import {
  DocumentReviewView,
  SaveReviewRevisionRequest,
  SaveReviewRevisionResponse,
  SelectedReviewRevisionView,
} from './review-models';

/**
 * HTTP client for F3 work-order review endpoints.
 * Strictly stateless: zero field values, reasons, quotes, or operator labels are ever persisted
 * to sessionStorage, localStorage, or IndexedDB (F3-BIC-05).
 */
@Injectable({ providedIn: 'root' })
export class ReviewApi {
  private readonly http = inject(HttpClient);

  getReview(documentId: string): Observable<DocumentReviewView> {
    return this.http.get<DocumentReviewView>(`/api/documents/${encodeURIComponent(documentId)}/review`);
  }

  getRevision(documentId: string, revisionNumber: number): Observable<SelectedReviewRevisionView> {
    return this.http.get<SelectedReviewRevisionView>(
      `/api/documents/${encodeURIComponent(documentId)}/review/revisions/${encodeURIComponent(String(revisionNumber))}`,
    );
  }

  saveRevision(
    documentId: string,
    idempotencyKey: string,
    request: SaveReviewRevisionRequest,
  ): Observable<HttpResponse<SaveReviewRevisionResponse>> {
    return this.http
      .post<SaveReviewRevisionResponse>(
        `/api/documents/${encodeURIComponent(documentId)}/review/revisions`,
        request,
        {
          headers: {
            'Content-Type': 'application/json',
            'Idempotency-Key': idempotencyKey,
          },
          observe: 'response',
        },
      )
      .pipe(timeout({ first: submitTimeoutMs }));
  }
}
