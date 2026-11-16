using ELedgerCare.Domain.Review;

namespace ELedgerCare.Application.Review;

public interface IWorkOrderReviewStore
{
    Task<GetDocumentReviewOutcome> GetDocumentReviewAsync(
        Guid documentId,
        CancellationToken cancellationToken);

    Task<GetReviewRevisionOutcome> GetRevisionAsync(
        Guid documentId,
        int revisionNumber,
        CancellationToken cancellationToken);

    Task<SaveReviewRevisionOutcome> SaveRevisionAsync(
        SaveReviewRevisionCommand command,
        DateTimeOffset nowUtc,
        CancellationToken cancellationToken);
}

public sealed record WorkOrderReviewHeadSummary(
    string ProfileId,
    ReviewRevisionStatus Status,
    int CurrentRevisionNumber,
    int AcceptedFieldCount,
    int EditedFieldCount,
    int UnknownFieldCount,
    int UnreviewedFieldCount,
    DateTimeOffset UpdatedAtUtc);

public sealed record ReviewRevisionSummaryProjection(
    Guid RevisionId,
    int RevisionNumber,
    int? PreviousRevisionNumber,
    ReviewRevisionStatus Status,
    string? OperatorDisplayLabel,
    int AcceptedFieldCount,
    int EditedFieldCount,
    int UnknownFieldCount,
    int UnreviewedFieldCount,
    DateTimeOffset SavedAtUtc);

public sealed record ReviewFieldProjection(
    int FieldOrdinal,
    string FieldKey,
    ReviewFieldDecision Decision,
    string? Value,
    string? UnknownReason,
    ReviewSourceReference? ConsultedSource);

public sealed record ReviewRevisionDetailProjection(
    Guid RevisionId,
    Guid DocumentId,
    Guid ResultId,
    int RevisionNumber,
    int? PreviousRevisionNumber,
    ReviewRevisionStatus Status,
    Guid IdempotencyKey,
    byte[] RequestSha256,
    byte[] InputSha256,
    byte[] RawOutputSha256,
    string ProfileId,
    string FieldSchemaVersion,
    string SuggestionPolicyVersion,
    string? OperatorDisplayLabel,
    int AcceptedFieldCount,
    int EditedFieldCount,
    int UnknownFieldCount,
    int UnreviewedFieldCount,
    DateTimeOffset SavedAtUtc,
    IReadOnlyList<ReviewFieldProjection> Fields);

public sealed record DocumentReviewSnapshot(
    Guid DocumentId,
    Guid JobId,
    Guid ResultId,
    int PageCount,
    int OriginalByteLength,
    byte[] OriginalSha256,
    int RawOutputByteLength,
    byte[] RawOutputSha256,
    DateTimeOffset ExtractionCompletedAtUtc,
    string ModelRepoId,
    string ModelRevision,
    int CurrentRevisionNumber,
    ReviewRevisionStatus? CurrentStatus,
    WorkOrderMachineSnapshot MachineSnapshot,
    ReviewRevisionDetailProjection? CurrentRevision,
    IReadOnlyList<ReviewRevisionSummaryProjection> History);

public sealed record SelectedReviewRevisionSnapshot(
    Guid DocumentId,
    Guid ResultId,
    int PageCount,
    byte[] OriginalSha256,
    byte[] RawOutputSha256,
    int CurrentRevisionNumber,
    ReviewRevisionStatus CurrentStatus,
    WorkOrderMachineSnapshot MachineSnapshot,
    ReviewRevisionDetailProjection Revision,
    IReadOnlyList<ReviewRevisionSummaryProjection> History);

public sealed record SavedReviewRevisionResult(
    int CurrentRevisionNumber,
    ReviewRevisionStatus CurrentStatus,
    WorkOrderMachineSnapshot MachineSnapshot,
    ReviewRevisionDetailProjection Revision,
    IReadOnlyList<ReviewRevisionSummaryProjection> History);

public sealed record SaveReviewRevisionCommand(
    Guid DocumentId,
    Guid IdempotencyKey,
    string ProfileId,
    Guid ResultId,
    int ExpectedRevision,
    ReviewRevisionStatus Status,
    string? OperatorDisplayLabel,
    IReadOnlyList<CanonicalReviewFieldInput> OrderedFields,
    byte[] RequestSha256);

public abstract record GetDocumentReviewOutcome
{
    private GetDocumentReviewOutcome()
    {
    }

    public sealed record NotFound : GetDocumentReviewOutcome;

    public sealed record ExtractionNotCompleted(string CurrentExtractionStatus) : GetDocumentReviewOutcome;

    public sealed record ProfileUnsupported(string Detail) : GetDocumentReviewOutcome;

    public sealed record Found(DocumentReviewSnapshot Snapshot) : GetDocumentReviewOutcome;
}

public abstract record GetReviewRevisionOutcome
{
    private GetReviewRevisionOutcome()
    {
    }

    public sealed record DocumentNotFound : GetReviewRevisionOutcome;

    public sealed record RevisionNotFound : GetReviewRevisionOutcome;

    public sealed record Found(SelectedReviewRevisionSnapshot Snapshot) : GetReviewRevisionOutcome;
}

public abstract record SaveReviewRevisionOutcome
{
    private SaveReviewRevisionOutcome()
    {
    }

    public sealed record DocumentNotFound : SaveReviewRevisionOutcome;

    public sealed record ExtractionNotCompleted(string CurrentExtractionStatus) : SaveReviewRevisionOutcome;

    public sealed record ProfileUnsupported(string Detail) : SaveReviewRevisionOutcome;

    public sealed record ResultIdMismatch(Guid AcceptedResultId) : SaveReviewRevisionOutcome;

    public sealed record IdempotencyKeyConflict : SaveReviewRevisionOutcome;

    public sealed record StaleExpectedRevision(
        int ExpectedRevision,
        int CurrentRevisionNumber,
        ReviewRevisionStatus? CurrentStatus) : SaveReviewRevisionOutcome;

    public sealed record RevisionLimitReached(int CurrentRevisionNumber, int MaxRevisions) : SaveReviewRevisionOutcome;

    public sealed record ValidationRejected(string Code, string Detail) : SaveReviewRevisionOutcome;

    public sealed record Created(SavedReviewRevisionResult Result) : SaveReviewRevisionOutcome;

    public sealed record Replayed(SavedReviewRevisionResult Result) : SaveReviewRevisionOutcome;
}
