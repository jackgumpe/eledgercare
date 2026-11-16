/** Receipt returned by POST /api/documents and GET /api/submissions/{key} after rows committed. */
export interface SubmissionReceipt {
  documentId: string;
  jobId: string;
  status: string;
  submittedAtUtc: string;
  byteLength: number;
  sha256: string;
  originalUrl: string;
}

/** Extended document metadata returned by GET /api/documents/{documentId}. */
export interface DocumentDetail extends SubmissionReceipt {
  admittedPageCount: number;
  extractionUrl: string;
  currentAttemptId: string | null;
  acceptedResultId: string | null;
}

export interface AttemptSummary {
  attemptId: string;
  attemptNumber: number;
  status: string;
  phase: string;
  startedAtUtc: string;
  lastHeartbeatAtUtc: string;
  endedAtUtc: string | null;
  failureCode: string | null;
  failureMessage: string | null;
}

export interface ExtractedBlock {
  kind: string;
  text: string;
  tableRows: string[][] | null;
}

export interface ExtractedPage {
  pageNumber: number;
  rawPageText: string;
  blocks: ExtractedBlock[];
}

export interface ExtractionProvenance {
  modelRepoId: string;
  modelRevision: string;
  modelManifestSha256: string;
  dependencyLockSha256: string;
  workerSourceSha256: string;
  workerConfigSha256: string;
  rendererIdentity: string;
  finishReason: string;
  provenanceException: string;
  startedAtUtc: string;
  completedAtUtc: string;
  loadDurationMs: number;
  renderDurationMs: number;
  inferDurationMs: number;
  totalDurationMs: number;
}

export interface AcceptedExtractionResult {
  resultId: string;
  attemptId: string;
  reviewStatus: string;
  completedAtUtc: string;
  pageCount: number;
  rawByteLength: number;
  rawSha256: string;
  rawText: string;
  pages: ExtractedPage[];
  provenance: ExtractionProvenance;
}

export interface DocumentExtractionView {
  documentId: string;
  jobId: string;
  status: string;
  admittedPageCount: number;
  OriginalByteLength?: number;
  originalByteLength: number;
  originalSha256: string;
  originalUrl: string;
  submittedAtUtc: string;
  queuedAtUtc: string | null;
  updatedAtUtc: string;
  workerEnabled: boolean;
  profileSupported: boolean;
  maxSupportedPages: number;
  canRequestExtraction: boolean;
  canRetryExtraction: boolean;
  unavailableReason: string | null;
  currentAttempt: AttemptSummary | null;
  attempts: AttemptSummary[];
  result: AcceptedExtractionResult | null;
}

export interface ProblemBody {
  title?: string;
  detail?: string;
  code?: string;
  status?: number;
}

const statusLabels: Record<string, string> = {
  awaiting_extraction: 'Awaiting extraction',
  queued: 'Queued for extraction',
  running: 'Extraction running',
  completed: 'Completed (unreviewed)',
  failed: 'Extraction failed',
  interrupted: 'Extraction interrupted',
};

/** Displays only the persisted server status; never invents extraction progress. */
export function statusLabel(status: string): string {
  return statusLabels[status] ?? `Unrecognised status (${status})`;
}
