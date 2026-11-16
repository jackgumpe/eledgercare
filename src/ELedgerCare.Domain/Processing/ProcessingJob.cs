namespace ELedgerCare.Domain.Processing;

/// <summary>
/// Requested extraction work for one document. A job is distinct from each execution attempt.
/// </summary>
public sealed class ProcessingJob
{
    private ProcessingJob()
    {
        // Materialization constructor for the persistence mapping.
    }

    private ProcessingJob(Guid jobId, Guid documentId, DateTimeOffset requestedAtUtc)
    {
        JobId = jobId;
        DocumentId = documentId;
        Status = ProcessingStatus.AwaitingExtraction;
        RequestedAtUtc = requestedAtUtc;
        UpdatedAtUtc = requestedAtUtc;
        AttemptCount = 0;
        LatestFencingToken = 0;
    }

    public Guid JobId { get; private init; }

    public Guid DocumentId { get; private init; }

    public ProcessingStatus Status { get; private set; }

    public DateTimeOffset RequestedAtUtc { get; private init; }

    public DateTimeOffset? QueuedAtUtc { get; private set; }

    public DateTimeOffset UpdatedAtUtc { get; private set; }

    public int AttemptCount { get; private set; }

    public long LatestFencingToken { get; private set; }

    public Guid? RetriedFromAttemptId { get; private set; }

    internal static ProcessingJob Request(Guid jobId, Guid documentId, DateTimeOffset requestedAtUtc)
        => new(jobId, documentId, requestedAtUtc);

    public void QueueInitial(DateTimeOffset queuedAtUtc)
    {
        RequireUtc(queuedAtUtc, nameof(queuedAtUtc));
        if (Status != ProcessingStatus.AwaitingExtraction)
        {
            throw new InvalidOperationException($"Cannot queue initial extraction from status {Status}.");
        }

        Status = ProcessingStatus.Queued;
        QueuedAtUtc = queuedAtUtc;
        UpdatedAtUtc = queuedAtUtc;
        RetriedFromAttemptId = null;
    }

    public void QueueRetry(Guid priorAttemptId, DateTimeOffset queuedAtUtc)
    {
        RequireUtc(queuedAtUtc, nameof(queuedAtUtc));
        if (priorAttemptId == Guid.Empty)
        {
            throw new ArgumentException("Retry target attempt ID must be non-empty.", nameof(priorAttemptId));
        }

        if (Status is not (ProcessingStatus.Failed or ProcessingStatus.Interrupted))
        {
            throw new InvalidOperationException($"Explicit retry is permitted only for failed or interrupted jobs (current: {Status}).");
        }

        Status = ProcessingStatus.Queued;
        QueuedAtUtc = queuedAtUtc;
        UpdatedAtUtc = queuedAtUtc;
        RetriedFromAttemptId = priorAttemptId;
    }

    public int Claim(long fencingToken, DateTimeOffset claimedAtUtc)
    {
        RequireUtc(claimedAtUtc, nameof(claimedAtUtc));
        if (Status != ProcessingStatus.Queued)
        {
            throw new InvalidOperationException($"Only queued jobs can be claimed (current: {Status}).");
        }

        if (fencingToken <= LatestFencingToken || fencingToken < 1)
        {
            throw new ArgumentOutOfRangeException(nameof(fencingToken), fencingToken,
                "Fencing token must be positive and strictly greater than LatestFencingToken.");
        }

        Status = ProcessingStatus.Running;
        AttemptCount += 1;
        LatestFencingToken = fencingToken;
        UpdatedAtUtc = claimedAtUtc;
        return AttemptCount;
    }

    public void MarkCompleted(long fencingToken, DateTimeOffset completedAtUtc)
    {
        RequireLiveOwner(fencingToken);
        RequireUtc(completedAtUtc, nameof(completedAtUtc));
        Status = ProcessingStatus.Completed;
        UpdatedAtUtc = completedAtUtc;
    }

    public void MarkFailed(long fencingToken, DateTimeOffset endedAtUtc)
    {
        RequireLiveOwner(fencingToken);
        RequireUtc(endedAtUtc, nameof(endedAtUtc));
        Status = ProcessingStatus.Failed;
        UpdatedAtUtc = endedAtUtc;
    }

    public void MarkInterrupted(long fencingToken, DateTimeOffset endedAtUtc)
    {
        RequireLiveOwner(fencingToken);
        RequireUtc(endedAtUtc, nameof(endedAtUtc));
        Status = ProcessingStatus.Interrupted;
        UpdatedAtUtc = endedAtUtc;
    }

    private void RequireLiveOwner(long fencingToken)
    {
        if (Status != ProcessingStatus.Running)
        {
            throw new InvalidOperationException($"Job is not running (current: {Status}).");
        }

        if (fencingToken != LatestFencingToken)
        {
            throw new InvalidOperationException("Attempt fencing token no longer owns this job.");
        }
    }

    private static void RequireUtc(DateTimeOffset timestamp, string paramName)
    {
        if (timestamp.Offset != TimeSpan.Zero)
        {
            throw new ArgumentException("Timestamp must be UTC.", paramName);
        }
    }
}
