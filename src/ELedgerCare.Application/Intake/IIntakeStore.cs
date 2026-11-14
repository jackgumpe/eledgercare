using ELedgerCare.Domain.Documents;
using ELedgerCare.Domain.Processing;

namespace ELedgerCare.Application.Intake;

/// <summary>
/// The persistence boundary F1 needs. Metadata queries never load original bytes;
/// only <see cref="GetOriginalBytesAsync"/> selects them.
/// </summary>
public interface IIntakeStore
{
    Task<CommittedSubmission?> FindByIdempotencyKeyAsync(Guid idempotencyKey, CancellationToken cancellationToken);

    Task<CommittedSubmission?> FindByDocumentIdAsync(Guid documentId, CancellationToken cancellationToken);

    Task<byte[]?> GetOriginalBytesAsync(Guid documentId, CancellationToken cancellationToken);

    /// <summary>
    /// Inserts document, original and job in one Read Committed transaction and commits before returning.
    /// Returns <see cref="InsertResult.IdempotencyKeyTaken"/> only for the idempotency-key unique constraint;
    /// every other failure propagates.
    /// </summary>
    Task<InsertResult> InsertAsync(Document document, CancellationToken cancellationToken);
}

public enum InsertResult
{
    Committed,
    IdempotencyKeyTaken,
}

/// <summary>Committed metadata projection; contains no original bytes.</summary>
public sealed record CommittedSubmission(
    Guid DocumentId,
    Guid IdempotencyKey,
    Guid JobId,
    ProcessingStatus Status,
    DateTimeOffset SubmittedAtUtc,
    int ByteLength,
    byte[] Sha256);
