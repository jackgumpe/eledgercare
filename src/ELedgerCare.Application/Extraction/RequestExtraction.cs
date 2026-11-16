namespace ELedgerCare.Application.Extraction;

/// <summary>
/// Use case for POST /api/documents/{documentId}/extraction: queues initial work, reconciles
/// active/completed work idempotently, or queues an explicit retry of a failed/interrupted attempt.
/// </summary>
public sealed class RequestExtraction(IExtractionStore store, ExtractionSettings settings, TimeProvider clock)
{
    public Task<QueueExtractionOutcome> ExecuteAsync(
        Guid documentId,
        Guid? retryAttemptId,
        CancellationToken cancellationToken)
    {
        if (documentId == Guid.Empty)
        {
            throw new ArgumentException("Document ID must be a non-empty UUID.", nameof(documentId));
        }

        if (retryAttemptId == Guid.Empty)
        {
            throw new ArgumentException("Retry attempt ID cannot be an empty UUID.", nameof(retryAttemptId));
        }

        var nowUtc = ExtractionAttemptCoordinator.TruncateToMicroseconds(clock.GetUtcNow());
        return store.QueueOrReconcileAsync(
            documentId,
            retryAttemptId,
            settings.MaxExtractionPages,
            settings.Enabled,
            nowUtc,
            cancellationToken);
    }
}
