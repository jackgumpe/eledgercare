using System.Data;
using ELedgerCare.Application.Intake;
using ELedgerCare.Domain.Documents;
using Microsoft.EntityFrameworkCore;
using Npgsql;

namespace ELedgerCare.Infrastructure.Persistence;

public sealed class IntakeStore(IDbContextFactory<ELedgerCareDbContext> contextFactory) : IIntakeStore
{
    public async Task<CommittedSubmission?> FindByIdempotencyKeyAsync(Guid idempotencyKey, CancellationToken cancellationToken)
    {
        // A fresh context per call: a retry after a lost race must observe the winner's committed rows.
        await using var db = await contextFactory.CreateDbContextAsync(cancellationToken);
        return await ProjectMetadata(db.Documents.Where(d => d.IdempotencyKey == idempotencyKey))
            .SingleOrDefaultAsync(cancellationToken);
    }

    public async Task<CommittedSubmission?> FindByDocumentIdAsync(Guid documentId, CancellationToken cancellationToken)
    {
        await using var db = await contextFactory.CreateDbContextAsync(cancellationToken);
        return await ProjectMetadata(db.Documents.Where(d => d.DocumentId == documentId))
            .SingleOrDefaultAsync(cancellationToken);
    }

    public async Task<byte[]?> GetOriginalBytesAsync(Guid documentId, CancellationToken cancellationToken)
    {
        await using var db = await contextFactory.CreateDbContextAsync(cancellationToken);
        return await db.OriginalArtifacts.AsNoTracking()
            .Where(a => a.DocumentId == documentId)
            .Select(a => a.Bytes)
            .SingleOrDefaultAsync(cancellationToken);
    }

    public async Task<InsertResult> InsertAsync(Document document, CancellationToken cancellationToken)
    {
        await using var db = await contextFactory.CreateDbContextAsync(cancellationToken);
        await using var transaction = await db.Database.BeginTransactionAsync(IsolationLevel.ReadCommitted, cancellationToken);
        await db.Database.ExecuteSqlRawAsync("SET LOCAL synchronous_commit = on", cancellationToken);

        db.Documents.Add(document);
        try
        {
            await db.SaveChangesAsync(cancellationToken);
        }
        catch (DbUpdateException ex) when (ex.InnerException is PostgresException
        {
            SqlState: PostgresErrorCodes.UniqueViolation,
            ConstraintName: ELedgerCareDbContext.IdempotencyKeyUniqueIndex,
        })
        {
            // The whole losing unit rolls back; nothing of this attempt becomes visible.
            await transaction.RollbackAsync(CancellationToken.None);
            return InsertResult.IdempotencyKeyTaken;
        }

        await transaction.CommitAsync(cancellationToken);
        return InsertResult.Committed;
    }

    private static IQueryable<CommittedSubmission> ProjectMetadata(IQueryable<Document> documents) =>
        documents.AsNoTracking().Select(d => new CommittedSubmission(
            d.DocumentId,
            d.IdempotencyKey,
            d.Job.JobId,
            d.Job.Status,
            d.SubmittedAtUtc,
            d.Original.ByteLength,
            d.Original.Sha256));
}
