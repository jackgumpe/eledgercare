import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ArchiveSearchResponse, ArchiveSourceFilterWire } from './archive-models';

export interface ArchiveQueryRequest {
  q: string;
  source: ArchiveSourceFilterWire;
  limit?: number;
  after?: string | null;
}

@Injectable({ providedIn: 'root' })
export class ArchiveApi {
  private readonly http = inject(HttpClient);

  search(req: ArchiveQueryRequest): Observable<ArchiveSearchResponse> {
    const parts: string[] = [];
    if (req.q.length > 0) {
      parts.push(`q=${encodeURIComponent(req.q)}`);
    }
    parts.push(`source=${encodeURIComponent(req.source)}`);
    if (req.limit !== undefined) {
      parts.push(`limit=${encodeURIComponent(String(req.limit))}`);
    }
    if (req.after) {
      parts.push(`after=${encodeURIComponent(req.after)}`);
    }
    const qs = parts.join('&');
    return this.http.get<ArchiveSearchResponse>(`/api/archive?${qs}`);
  }
}
