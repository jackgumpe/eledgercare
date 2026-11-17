export type ArchiveSourceFilterWire = 'all' | 'machine' | 'reviewed';

export interface ArchiveSnippetSegment {
  text: string;
  highlighted: boolean;
}

export interface ArchiveWitness {
  sourceKind: 'machine' | 'reviewed';
  sourceLabel: string;
  resultId: string | null;
  pageNumber: number | null;
  isFallback: boolean;
  revisionNumber: number | null;
  fieldKey: string | null;
  fieldLabel: string | null;
  consultedPageNumber: number | null;
  snippet: string;
  prefixClipped: boolean;
  suffixClipped: boolean;
  segments: ArchiveSnippetSegment[];
  matchedTerms: string[];
}

export interface ArchiveMachineSummary {
  resultId: string;
  pageCount: number;
  rawSha256: string;
  projectionVersion: string;
  projectionSha256: string;
  hasFallback: boolean;
}

export interface ArchiveReviewedSummary {
  revisionNumber: number;
  savedAtUtc: string;
  workOrderId: string | null;
  propertyName: string | null;
}

export interface ArchiveHeadSummary {
  currentRevisionNumber: number;
  currentStatus: 'draft' | 'reviewed';
  updatedAtUtc: string;
}

export interface ArchiveDocumentCard {
  documentId: string;
  shortDocumentId: string;
  displayTitle: string;
  titleFromReviewed: boolean;
  submittedAtUtc: string;
  admittedPageCount: number;
  originalByteLength: number;
  originalSha256: string;
  originalUrl: string;
  status: string;
  machine: ArchiveMachineSummary | null;
  latestReviewed: ArchiveReviewedSummary | null;
  currentReviewHead: ArchiveHeadSummary | null;
  hasNewerDraft: boolean;
  contributingSources: string[];
  witnesses: ArchiveWitness[];
  hasMoreMatchesInDocument: boolean;
}

export interface ArchiveSearchResponse {
  query: string;
  terms: string[];
  source: ArchiveSourceFilterWire;
  limit: number;
  hasMore: boolean;
  nextCursor: string | null;
  projectionVersion: string;
  items: ArchiveDocumentCard[];
}

export function normalizeArchiveSourceParam(raw: string | undefined | null): ArchiveSourceFilterWire {
  if (raw === 'machine' || raw === 'reviewed') {
    return raw;
  }
  return 'all';
}
