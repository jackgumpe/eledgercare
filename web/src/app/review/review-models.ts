export type ReviewRevisionStatus = 'draft' | 'reviewed';
export type ReviewFieldDecision = 'unreviewed' | 'accepted' | 'edited' | 'unknown';
export type MachineCandidateStatus = 'suggested' | 'missing' | 'ambiguous' | 'oversized' | 'invalid_text';

export interface SourceReference {
  pageNumber: number;
  blockOrdinal: number;
  tableRow: number | null;
  tableColumn: number | null;
  sourceQuote: string;
}

export interface SourceCoordinateInput {
  pageNumber: number;
  blockOrdinal: number;
  tableRow: number | null;
  tableColumn: number | null;
}

export interface MachineFieldCandidate {
  fieldKey: string;
  status: MachineCandidateStatus;
  value: string | null;
  source: SourceReference | null;
  competingSources: SourceReference[];
}

export interface MachineSnapshot {
  schema: string;
  profileId: string;
  fieldSchemaVersion: string;
  suggestionPolicyVersion: string;
  resultId: string;
  rawOutputSha256: string;
  fields: MachineFieldCandidate[];
}

export interface ReviewFieldView {
  ordinal: number;
  fieldKey: string;
  label: string;
  maxLength: number;
  multiline: boolean;
  machineCandidate: MachineFieldCandidate;
  decision: ReviewFieldDecision;
  value: string | null;
  unknownReason: string | null;
  consultedSource: SourceReference | null;
}

export interface ReviewFieldSnapshot {
  ordinal: number;
  fieldKey: string;
  decision: ReviewFieldDecision;
  value: string | null;
  unknownReason: string | null;
  consultedSource: SourceReference | null;
}

export interface ReviewRevisionDetail {
  revisionId: string;
  documentId: string;
  resultId: string;
  revisionNumber: number;
  previousRevisionNumber: number | null;
  status: ReviewRevisionStatus;
  idempotencyKey: string;
  requestSha256: string;
  inputSha256: string;
  rawOutputSha256: string;
  profileId: string;
  fieldSchemaVersion: string;
  suggestionPolicyVersion: string;
  operatorDisplayLabel: string | null;
  acceptedFieldCount: number;
  editedFieldCount: number;
  unknownFieldCount: number;
  unreviewedFieldCount: number;
  savedAtUtc: string;
  fields: ReviewFieldSnapshot[];
}

export interface ReviewRevisionSummary {
  revisionId: string;
  revisionNumber: number;
  previousRevisionNumber: number | null;
  status: ReviewRevisionStatus;
  isCurrentHead: boolean;
  operatorDisplayLabel: string | null;
  acceptedFieldCount: number;
  editedFieldCount: number;
  unknownFieldCount: number;
  unreviewedFieldCount: number;
  savedAtUtc: string;
  revisionUrl: string;
}

export interface DocumentReviewView {
  documentId: string;
  jobId: string;
  resultId: string;
  profileId: string;
  fieldSchemaVersion: string;
  suggestionPolicyVersion: string;
  pageCount: number;
  originalByteLength: number;
  originalSha256: string;
  originalUrl: string;
  previewUrl: string;
  rawByteLength: number;
  rawSha256: string;
  extractionCompletedAtUtc: string;
  modelRepoId: string;
  modelRevision: string;
  reviewState: 'unreviewed' | ReviewRevisionStatus;
  currentRevisionNumber: number;
  maxRevisions: number;
  canSaveRevision: boolean;
  machineSnapshot: MachineSnapshot;
  currentRevision: ReviewRevisionDetail | null;
  fields: ReviewFieldView[];
  history: ReviewRevisionSummary[];
}

export interface SelectedReviewRevisionView {
  documentId: string;
  resultId: string;
  profileId: string;
  fieldSchemaVersion: string;
  suggestionPolicyVersion: string;
  pageCount: number;
  originalSha256: string;
  rawSha256: string;
  originalUrl: string;
  previewUrl: string;
  currentRevisionNumber: number;
  currentReviewState: ReviewRevisionStatus;
  isCurrentHead: boolean;
  machineSnapshot: MachineSnapshot;
  revision: ReviewRevisionDetail;
  fields: ReviewFieldView[];
  history: ReviewRevisionSummary[];
}

export interface SaveReviewRevisionResponse {
  replayed: boolean;
  isCurrentHead: boolean;
  currentRevisionNumber: number;
  currentReviewState: ReviewRevisionStatus;
  maxRevisions: number;
  canSaveRevision: boolean;
  machineSnapshot: MachineSnapshot;
  revision: ReviewRevisionDetail;
  fields: ReviewFieldView[];
  history: ReviewRevisionSummary[];
}

export interface SaveReviewFieldInput {
  fieldKey: string;
  decision: ReviewFieldDecision;
  value: string | null;
  unknownReason: string | null;
  consultedSource: SourceCoordinateInput | null;
}

export interface SaveReviewRevisionRequest {
  profileId: string;
  resultId: string;
  expectedRevision: number;
  status: ReviewRevisionStatus;
  operatorDisplayLabel: string | null;
  fields: SaveReviewFieldInput[];
}

export interface ReviewProblemBody {
  title?: string;
  detail?: string;
  code?: string;
  status?: number;
  expectedRevision?: number;
  currentRevisionNumber?: number;
  currentReviewState?: string;
  currentRevisionUrl?: string;
  maxRevisions?: number;
}
