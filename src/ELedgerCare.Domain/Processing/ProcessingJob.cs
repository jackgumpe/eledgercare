namespace ELedgerCare.Domain.Processing;

/// <summary>
/// Requested extraction work for one document. A job is not an execution attempt.
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
    }

    public Guid JobId { get; private init; }

    public Guid DocumentId { get; private init; }

    public ProcessingStatus Status { get; private init; }

    public DateTimeOffset RequestedAtUtc { get; private init; }

    internal static ProcessingJob Request(Guid jobId, Guid documentId, DateTimeOffset requestedAtUtc)
        => new(jobId, documentId, requestedAtUtc);
}
