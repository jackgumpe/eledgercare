using ELedgerCare.Domain.Processing;

namespace ELedgerCare.Application.Extraction;

public interface IExtractionStore
{
    Task<DocumentSummaryProjection?> GetDocumentSummaryAsync(Guid documentId, CancellationToken cancellationToken);

    Task<DocumentExtractionSnapshot?> GetDocumentExtractionAsync(Guid documentId, CancellationToken cancellationToken);

    Task<QueueExtractionOutcome> QueueOrReconcileAsync(
        Guid documentId,
        Guid? retryAttemptId,
        int maxExtractionPages,
        bool workerEnabled,
        DateTimeOffset nowUtc,
        CancellationToken cancellationToken);

    Task<IReadOnlyList<RunningAttemptRecord>> GetRunningAttemptsAsync(CancellationToken cancellationToken);

    Task<bool> MarkAttemptInterruptedAsync(
        Guid attemptId,
        Guid jobId,
        long fencingToken,
        string failureCode,
        string failureDetail,
        DateTimeOffset endedAtUtc,
        CancellationToken cancellationToken);

    Task<ClaimedAttemptWork?> ClaimNextQueuedJobAsync(
        Guid supervisorInstanceId,
        int supervisorPid,
        long supervisorCreateFileTime,
        DateTimeOffset nowUtc,
        CancellationToken cancellationToken);

    Task<bool> RecordLauncherProcessAsync(
        Guid attemptId,
        long fencingToken,
        int launcherPid,
        long launcherCreateFileTime,
        DateTimeOffset nowUtc,
        CancellationToken cancellationToken);

    Task<bool> RecordHeartbeatAsync(
        Guid attemptId,
        long fencingToken,
        string phase,
        int? workerPid,
        long? workerCreateFileTime,
        DateTimeOffset nowUtc,
        CancellationToken cancellationToken);

    Task<bool> PublishCompletedResultAsync(
        ExtractionResult result,
        int exitCode,
        DateTimeOffset completedAtUtc,
        CancellationToken cancellationToken);

    Task<bool> MarkAttemptFailedAsync(
        Guid attemptId,
        Guid jobId,
        long fencingToken,
        string failureCode,
        string failureDetail,
        int? exitCode,
        string? diagnosticRawOutputUtf8,
        string? diagnosticMetadataJson,
        DateTimeOffset endedAtUtc,
        CancellationToken cancellationToken);
}

public sealed record DocumentSummaryProjection(
    Guid DocumentId,
    Guid IdempotencyKey,
    Guid JobId,
    ProcessingStatus Status,
    DateTimeOffset SubmittedAtUtc,
    int ByteLength,
    byte[] Sha256,
    int AdmittedPageCount,
    Guid? CurrentAttemptId,
    Guid? AcceptedResultId);

public sealed record AttemptSummaryProjection(
    Guid AttemptId,
    int AttemptNumber,
    AttemptStatus Status,
    string Phase,
    DateTimeOffset StartedAtUtc,
    DateTimeOffset LastHeartbeatAtUtc,
    DateTimeOffset? EndedAtUtc,
    string? FailureCode,
    string? FailureDetail);

public sealed record DocumentExtractionSnapshot(
    Guid DocumentId,
    Guid JobId,
    ProcessingStatus Status,
    int AdmittedPageCount,
    int OriginalByteLength,
    byte[] OriginalSha256,
    DateTimeOffset SubmittedAtUtc,
    DateTimeOffset? QueuedAtUtc,
    DateTimeOffset UpdatedAtUtc,
    Guid? RetriedFromAttemptId,
    IReadOnlyList<AttemptSummaryProjection> Attempts,
    ExtractionResult? AcceptedResult);

public sealed record RunningAttemptRecord(
    Guid AttemptId,
    Guid JobId,
    Guid DocumentId,
    long FencingToken,
    string RunDirectoryName,
    Guid SupervisorInstanceId,
    int SupervisorPid,
    long SupervisorCreateFileTime,
    int? LauncherPid,
    long? LauncherCreateFileTime,
    int? WorkerPid,
    long? WorkerCreateFileTime);

public sealed record ClaimedAttemptWork(
    Guid AttemptId,
    Guid JobId,
    Guid DocumentId,
    int AttemptNumber,
    long FencingToken,
    string RunDirectoryName,
    byte[] PdfBytes,
    byte[] InputSha256,
    int InputByteLength,
    int PageCount);

public abstract record QueueExtractionOutcome
{
    private QueueExtractionOutcome()
    {
    }

    public sealed record NotFound : QueueExtractionOutcome;

    public sealed record ProfileUnsupported(int AdmittedPageCount, int MaxSupportedPages) : QueueExtractionOutcome;

    public sealed record WorkerDisabled : QueueExtractionOutcome;

    public sealed record RetryExplicitRequired(Guid LatestAttemptId) : QueueExtractionOutcome;

    public sealed record RetryConflict(string Code, string Detail) : QueueExtractionOutcome;

    public sealed record QueuedOrActive(DocumentExtractionSnapshot Snapshot) : QueueExtractionOutcome;

    public sealed record AlreadyCompleted(DocumentExtractionSnapshot Snapshot) : QueueExtractionOutcome;
}
