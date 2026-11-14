using System.Security.Cryptography;
using ELedgerCare.Domain.Documents;

namespace ELedgerCare.Application.Intake;

/// <summary>
/// Intake use case after HTTP validation and bounded body buffering (accepted design steps 3-5).
/// </summary>
public sealed class SubmitDocument(IIntakeStore store, IPdfAdmission admission, IntakeLimits limits, TimeProvider clock)
{
    public async Task<SubmissionOutcome> ExecuteAsync(Guid idempotencyKey, byte[] body, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(body);
        if (idempotencyKey == Guid.Empty)
        {
            throw new ArgumentException("Idempotency key must be a non-empty UUID.", nameof(idempotencyKey));
        }

        if (body.Length == 0 || body.Length > limits.MaxDocumentBytes)
        {
            throw new ArgumentOutOfRangeException(nameof(body), body.Length, "Body length must be validated by the caller.");
        }

        var digest = SHA256.HashData(body);

        // Step 3: an existing key is resolved by exact bytes; an immutable accepted PDF is not revalidated.
        var existing = await store.FindByIdempotencyKeyAsync(idempotencyKey, cancellationToken);
        if (existing is not null)
        {
            return await CompareWithCommittedAsync(existing, body, digest, cancellationToken);
        }

        // Step 4: restricted PDF admission for a new key.
        var verdict = admission.Evaluate(body, limits.MaxPages);
        if (!verdict.IsAdmitted)
        {
            return new SubmissionOutcome.Rejected(verdict.Rejection!.Value);
        }

        // Step 5: one atomic unit. The transaction is not bound to the request-abort token, so a client
        // that disconnects after the full body was received does not turn a commit into an uncertain cancel.
        // PostgreSQL timestamptz stores microseconds: truncate first so the 201 receipt equals what is committed.
        var now = TruncateToMicroseconds(clock.GetUtcNow());
        var document = Document.Submit(
            Guid.CreateVersion7(now),
            Guid.CreateVersion7(now),
            idempotencyKey,
            body,
            verdict.PageCount!.Value,
            now);

        var inserted = await store.InsertAsync(document, CancellationToken.None);
        if (inserted == InsertResult.Committed)
        {
            return new SubmissionOutcome.Created(new CommittedSubmission(
                document.DocumentId,
                document.IdempotencyKey,
                document.Job.JobId,
                document.Job.Status,
                document.SubmittedAtUtc,
                document.Original.ByteLength,
                document.Original.Sha256));
        }

        // Lost a same-key race: the losing transaction rolled back entirely; compare with the winner.
        var winner = await store.FindByIdempotencyKeyAsync(idempotencyKey, CancellationToken.None)
            ?? throw new InvalidOperationException("Idempotency key conflict reported but no committed submission is visible.");
        return await CompareWithCommittedAsync(winner, body, digest, CancellationToken.None);
    }

    private static DateTimeOffset TruncateToMicroseconds(DateTimeOffset value) =>
        new(value.UtcTicks - (value.UtcTicks % 10), TimeSpan.Zero);

    private async Task<SubmissionOutcome> CompareWithCommittedAsync(
        CommittedSubmission committed, byte[] body, byte[] digest, CancellationToken cancellationToken)
    {
        if (committed.ByteLength != body.Length || !CryptographicOperations.FixedTimeEquals(committed.Sha256, digest))
        {
            return new SubmissionOutcome.Conflict();
        }

        var committedBytes = await store.GetOriginalBytesAsync(committed.DocumentId, cancellationToken)
            ?? throw new InvalidOperationException("Committed document has no original artifact.");
        return committedBytes.AsSpan().SequenceEqual(body)
            ? new SubmissionOutcome.Replayed(committed)
            : new SubmissionOutcome.Conflict();
    }
}

public abstract record SubmissionOutcome
{
    private SubmissionOutcome()
    {
    }

    /// <summary>A new document committed by this request (HTTP 201).</summary>
    public sealed record Created(CommittedSubmission Submission) : SubmissionOutcome;

    /// <summary>The key already names a document with exactly these bytes (HTTP 200).</summary>
    public sealed record Replayed(CommittedSubmission Submission) : SubmissionOutcome;

    /// <summary>The key already names a document with different bytes (HTTP 409).</summary>
    public sealed record Conflict : SubmissionOutcome;

    /// <summary>New key, body outside the admission profile (HTTP 422).</summary>
    public sealed record Rejected(PdfRejectionReason Reason) : SubmissionOutcome;
}
