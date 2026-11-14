/** Receipt returned by the server only after the document, original and job rows committed. */
export interface SubmissionReceipt {
  documentId: string;
  jobId: string;
  status: string;
  submittedAtUtc: string;
  byteLength: number;
  sha256: string;
  originalUrl: string;
}

export interface ProblemBody {
  title?: string;
  detail?: string;
  code?: string;
  status?: number;
}

const statusLabels: Record<string, string> = {
  awaiting_extraction: 'Awaiting extraction',
};

/** Displays only the persisted server status; never invents extraction progress. */
export function statusLabel(status: string): string {
  return statusLabels[status] ?? `Unrecognised status (${status})`;
}
