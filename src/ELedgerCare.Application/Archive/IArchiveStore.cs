using ELedgerCare.Domain.Archive;
using ELedgerCare.Domain.Processing;
using ELedgerCare.Domain.Review;

namespace ELedgerCare.Application.Archive;

public enum ArchiveReadinessStatus
{
    Initializing,
    Ready,
    Conflict,
}

public sealed record ArchiveReadinessSnapshot(
    ArchiveReadinessStatus Status,
    string ProjectionVersion,
    string? DiagnosticReason);

public interface IArchiveProjectionReadiness
{
    ArchiveReadinessSnapshot GetSnapshot();

    Task<ArchiveReadinessSnapshot> EnsureCaughtUpAsync(CancellationToken cancellationToken);
}

public sealed record ArchiveReviewedSummary(
    int RevisionNumber,
    DateTimeOffset SavedAtUtc,
    string? WorkOrderId,
    string? PropertyName);

public sealed record ArchiveHeadReviewSummary(
    int CurrentRevisionNumber,
    ReviewRevisionStatus CurrentStatus,
    DateTimeOffset UpdatedAtUtc);

public sealed record ArchiveDocumentCard(
    Guid DocumentId,
    DateTimeOffset SubmittedAtUtc,
    int AdmittedPageCount,
    int OriginalByteLength,
    byte[] OriginalSha256,
    ProcessingStatus ProcessingStatus,
    Guid? ResultId,
    byte[]? RawOutputSha256,
    int? ExtractedPageCount,
    string? ProjectionVersion,
    byte[]? ProjectionSha256,
    bool? ProjectionHasFallback,
    ArchiveReviewedSummary? LatestReviewed,
    ArchiveHeadReviewSummary? CurrentReviewHead,
    bool HasNewerDraft,
    IReadOnlyList<string> ContributingSources,
    IReadOnlyList<SelectedArchiveWitness> Witnesses,
    bool HasMoreMatchesInDocument);

public sealed record ArchiveSearchPage(
    string NormalizedQuery,
    IReadOnlyList<string> Terms,
    ArchiveSourceFilter Source,
    int Limit,
    bool HasMore,
    string? NextCursor,
    IReadOnlyList<ArchiveDocumentCard> Items);

public sealed record ArchiveSearchOutcome(
    ArchiveReadinessStatus Readiness,
    string? ReadinessFailureDetail,
    ArchiveSearchPage? Page);

public interface IArchiveStore
{
    Task<ArchiveSearchOutcome> SearchAsync(
        ParsedArchiveQuery query,
        CancellationToken cancellationToken);
}
