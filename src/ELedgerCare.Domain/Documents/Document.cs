using ELedgerCare.Domain.Processing;

namespace ELedgerCare.Domain.Documents;

/// <summary>
/// One business submission with a stable server-generated identity. It owns its immutable
/// original and the single requested processing job. The client-supplied idempotency key
/// identifies the submission attempt series; content digests are content identity only.
/// </summary>
public sealed class Document
{
    private Document()
    {
        // Materialization constructor for the persistence mapping.
        Original = null!;
        Job = null!;
    }

    private Document(Guid documentId, Guid idempotencyKey, DateTimeOffset submittedAtUtc,
        OriginalArtifact original, ProcessingJob job)
    {
        DocumentId = documentId;
        IdempotencyKey = idempotencyKey;
        SubmittedAtUtc = submittedAtUtc;
        Original = original;
        Job = job;
    }

    public Guid DocumentId { get; private init; }

    public Guid IdempotencyKey { get; private init; }

    public DateTimeOffset SubmittedAtUtc { get; private init; }

    public OriginalArtifact Original { get; private init; }

    public ProcessingJob Job { get; private init; }

    /// <summary>
    /// Creates the complete unit that must commit atomically: document, original and job.
    /// </summary>
    public static Document Submit(Guid documentId, Guid jobId, Guid idempotencyKey,
        byte[] originalBytes, int admittedPageCount, DateTimeOffset submittedAtUtc)
    {
        ArgumentNullException.ThrowIfNull(originalBytes);
        RequireNonEmpty(documentId, nameof(documentId));
        RequireNonEmpty(jobId, nameof(jobId));
        RequireNonEmpty(idempotencyKey, nameof(idempotencyKey));
        if (submittedAtUtc.Offset != TimeSpan.Zero)
        {
            throw new ArgumentException("Submission time must be UTC.", nameof(submittedAtUtc));
        }

        var original = OriginalArtifact.Create(documentId, originalBytes, admittedPageCount);
        var job = ProcessingJob.Request(jobId, documentId, submittedAtUtc);
        return new Document(documentId, idempotencyKey, submittedAtUtc, original, job);
    }

    private static void RequireNonEmpty(Guid value, string name)
    {
        if (value == Guid.Empty)
        {
            throw new ArgumentException("Identifier must be a non-empty UUID.", name);
        }
    }
}
