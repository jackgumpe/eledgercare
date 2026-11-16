using System.Data;
using System.Security.Cryptography;
using ELedgerCare.Application.Review;
using ELedgerCare.Domain.Processing;
using ELedgerCare.Domain.Review;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;
using Npgsql;

namespace ELedgerCare.Infrastructure.Persistence;

public sealed class WorkOrderReviewStore(IDbContextFactory<ELedgerCareDbContext> contextFactory) : IWorkOrderReviewStore
{
    public async Task<GetDocumentReviewOutcome> GetDocumentReviewAsync(
        Guid documentId,
        CancellationToken cancellationToken)
    {
        await using var db = await contextFactory.CreateDbContextAsync(cancellationToken);

        var docHead = await db.Documents.AsNoTracking()
            .Where(d => d.DocumentId == documentId)
            .Select(d => new
            {
                d.DocumentId,
                d.Job.JobId,
                d.Job.Status,
                d.Original.PageCount,
                d.Original.ByteLength,
                d.Original.Sha256,
            })
            .SingleOrDefaultAsync(cancellationToken);

        if (docHead is null)
        {
            return new GetDocumentReviewOutcome.NotFound();
        }

        if (docHead.PageCount < 1 || docHead.PageCount > ExtractionCeilings.MaxExtractionPages)
        {
            return new GetDocumentReviewOutcome.ProfileUnsupported(
                $"Work-order review supports 1 to {ExtractionCeilings.MaxExtractionPages} pages; this document has {docHead.PageCount} pages.");
        }

        if (docHead.Status != ProcessingStatus.Completed)
        {
            return new GetDocumentReviewOutcome.ExtractionNotCompleted(docHead.Status.ToWire());
        }

        var acceptedResult = await db.ExtractionResults.AsNoTracking()
            .SingleOrDefaultAsync(r => r.DocumentId == documentId, cancellationToken);

        if (acceptedResult is null)
        {
            return new GetDocumentReviewOutcome.ExtractionNotCompleted(ProcessingStatus.AwaitingExtraction.ToWire());
        }

        var reviewHead = await db.WorkOrderReviewHeads.AsNoTracking()
            .Where(h => h.DocumentId == documentId)
            .Select(h => new
            {
                h.CurrentRevisionNumber,
                h.CurrentRevisionId,
                h.CurrentStatus,
                h.MachineSnapshotJson,
            })
            .SingleOrDefaultAsync(cancellationToken);

        if (reviewHead is null)
        {
            // Pure read at revision 0: evaluate deterministic machine suggestions without persisting any rows.
            var previewSnapshot = WorkOrderReviewSuggestions.Evaluate(acceptedResult);
            return new GetDocumentReviewOutcome.Found(new DocumentReviewSnapshot(
                DocumentId: docHead.DocumentId,
                JobId: docHead.JobId,
                ResultId: acceptedResult.ResultId,
                PageCount: docHead.PageCount,
                OriginalByteLength: docHead.ByteLength,
                OriginalSha256: docHead.Sha256,
                RawOutputByteLength: acceptedResult.RawOutputByteLength,
                RawOutputSha256: acceptedResult.RawOutputSha256,
                ExtractionCompletedAtUtc: acceptedResult.CompletedAtUtc,
                ModelRepoId: acceptedResult.ModelRepoId,
                ModelRevision: acceptedResult.ModelRevision,
                CurrentRevisionNumber: 0,
                CurrentStatus: null,
                MachineSnapshot: previewSnapshot,
                CurrentRevision: null,
                History: []));
        }

        var persistedSnapshot = WorkOrderReviewSuggestions.DeserializeSnapshotJson(reviewHead.MachineSnapshotJson);
        var currentRevision = await ReadRevisionDetailAsync(db, reviewHead.CurrentRevisionId, cancellationToken)
            ?? throw new InvalidOperationException("Review head references a missing current revision.");
        var history = await ReadHistorySummariesAsync(db, documentId, cancellationToken);

        return new GetDocumentReviewOutcome.Found(new DocumentReviewSnapshot(
            DocumentId: docHead.DocumentId,
            JobId: docHead.JobId,
            ResultId: acceptedResult.ResultId,
            PageCount: docHead.PageCount,
            OriginalByteLength: docHead.ByteLength,
            OriginalSha256: docHead.Sha256,
            RawOutputByteLength: acceptedResult.RawOutputByteLength,
            RawOutputSha256: acceptedResult.RawOutputSha256,
            ExtractionCompletedAtUtc: acceptedResult.CompletedAtUtc,
            ModelRepoId: acceptedResult.ModelRepoId,
            ModelRevision: acceptedResult.ModelRevision,
            CurrentRevisionNumber: reviewHead.CurrentRevisionNumber,
            CurrentStatus: reviewHead.CurrentStatus,
            MachineSnapshot: persistedSnapshot,
            CurrentRevision: currentRevision,
            History: history));
    }

    public async Task<GetReviewRevisionOutcome> GetRevisionAsync(
        Guid documentId,
        int revisionNumber,
        CancellationToken cancellationToken)
    {
        await using var db = await contextFactory.CreateDbContextAsync(cancellationToken);

        var docHead = await db.Documents.AsNoTracking()
            .Where(d => d.DocumentId == documentId)
            .Select(d => new
            {
                d.DocumentId,
                d.Original.PageCount,
                d.Original.Sha256,
            })
            .SingleOrDefaultAsync(cancellationToken);

        if (docHead is null)
        {
            return new GetReviewRevisionOutcome.DocumentNotFound();
        }

        if (revisionNumber is < 1 or > WorkOrderReviewSchema.MaxRevisionsPerResult)
        {
            return new GetReviewRevisionOutcome.RevisionNotFound();
        }

        var reviewHead = await db.WorkOrderReviewHeads.AsNoTracking()
            .Where(h => h.DocumentId == documentId)
            .Select(h => new
            {
                h.ResultId,
                h.RawOutputSha256,
                h.CurrentRevisionNumber,
                h.CurrentStatus,
                h.MachineSnapshotJson,
            })
            .SingleOrDefaultAsync(cancellationToken);

        if (reviewHead is null)
        {
            return new GetReviewRevisionOutcome.RevisionNotFound();
        }

        var revisionId = await db.WorkOrderReviewRevisions.AsNoTracking()
            .Where(r => r.DocumentId == documentId && r.RevisionNumber == revisionNumber)
            .Select(r => (Guid?)r.RevisionId)
            .SingleOrDefaultAsync(cancellationToken);

        if (revisionId is null)
        {
            return new GetReviewRevisionOutcome.RevisionNotFound();
        }

        var revisionDetail = await ReadRevisionDetailAsync(db, revisionId.Value, cancellationToken)
            ?? throw new InvalidOperationException("Selected revision row disappeared unexpectedly.");
        var history = await ReadHistorySummariesAsync(db, documentId, cancellationToken);
        var machineSnapshot = WorkOrderReviewSuggestions.DeserializeSnapshotJson(reviewHead.MachineSnapshotJson);

        return new GetReviewRevisionOutcome.Found(new SelectedReviewRevisionSnapshot(
            DocumentId: docHead.DocumentId,
            ResultId: reviewHead.ResultId,
            PageCount: docHead.PageCount,
            OriginalSha256: docHead.Sha256,
            RawOutputSha256: reviewHead.RawOutputSha256,
            CurrentRevisionNumber: reviewHead.CurrentRevisionNumber,
            CurrentStatus: reviewHead.CurrentStatus,
            MachineSnapshot: machineSnapshot,
            Revision: revisionDetail,
            History: history));
    }

    public async Task<SaveReviewRevisionOutcome> SaveRevisionAsync(
        SaveReviewRevisionCommand command,
        DateTimeOffset nowUtc,
        CancellationToken cancellationToken)
    {
        // Step 1 (F3-BIC-03): Check Idempotency-Key replay BEFORE stale-head rejection, cap check, or context validation!
        await using (var preCheckDb = await contextFactory.CreateDbContextAsync(cancellationToken))
        {
            var preReplay = await TryResolveExistingOperationAsync(preCheckDb, command, cancellationToken);
            if (preReplay is not null)
            {
                return preReplay;
            }
        }

        // Step 2: Context-free profile, length, Unicode/control-char, and decision invariants.
        var contextFreeError = SaveWorkOrderReviewRevision.ValidateContextFreeInvariants(command);
        if (contextFreeError is not null)
        {
            return contextFreeError;
        }

        // Step 3: Transactional persistence with synchronous_commit = on.
        await using var db = await contextFactory.CreateDbContextAsync(cancellationToken);
        await using var tx = await db.Database.BeginTransactionAsync(IsolationLevel.ReadCommitted, cancellationToken);
        await db.Database.ExecuteSqlRawAsync("SET LOCAL synchronous_commit = on", cancellationToken);

        var conn = (NpgsqlConnection)db.Database.GetDbConnection();
        var npgsqlTx = (NpgsqlTransaction)tx.GetDbTransaction();

        var docMeta = await db.Documents.AsNoTracking()
            .Where(d => d.DocumentId == command.DocumentId)
            .Select(d => new
            {
                d.DocumentId,
                d.Job.Status,
                d.Original.PageCount,
            })
            .SingleOrDefaultAsync(cancellationToken);

        if (docMeta is null)
        {
            await tx.RollbackAsync(CancellationToken.None);
            return new SaveReviewRevisionOutcome.DocumentNotFound();
        }

        if (docMeta.PageCount < 1 || docMeta.PageCount > ExtractionCeilings.MaxExtractionPages)
        {
            await tx.RollbackAsync(CancellationToken.None);
            return new SaveReviewRevisionOutcome.ProfileUnsupported(
                $"Work-order review supports 1 to {ExtractionCeilings.MaxExtractionPages} pages; this document has {docMeta.PageCount} pages.");
        }

        if (docMeta.Status != ProcessingStatus.Completed)
        {
            await tx.RollbackAsync(CancellationToken.None);
            return new SaveReviewRevisionOutcome.ExtractionNotCompleted(docMeta.Status.ToWire());
        }

        var acceptedResult = await db.ExtractionResults.AsNoTracking()
            .SingleOrDefaultAsync(r => r.DocumentId == command.DocumentId, cancellationToken);

        if (acceptedResult is null)
        {
            await tx.RollbackAsync(CancellationToken.None);
            return new SaveReviewRevisionOutcome.ExtractionNotCompleted(ProcessingStatus.AwaitingExtraction.ToWire());
        }

        if (acceptedResult.ResultId != command.ResultId)
        {
            await tx.RollbackAsync(CancellationToken.None);
            return new SaveReviewRevisionOutcome.ResultIdMismatch(acceptedResult.ResultId);
        }

        var parsedPages = SafeNativeDisplayParser.ParsePages(acceptedResult.DecodeStrictUtf8());

        if (command.ExpectedRevision == 0)
        {
            // Fast stale check before attempting initial insert (unique constraints serialize concurrent races; F3-BIC-02).
            var existingHead = await db.WorkOrderReviewHeads.AsNoTracking()
                .Where(h => h.DocumentId == command.DocumentId)
                .Select(h => new { h.CurrentRevisionNumber, h.CurrentStatus })
                .SingleOrDefaultAsync(cancellationToken);

            if (existingHead is not null)
            {
                await tx.RollbackAsync(CancellationToken.None);
                return new SaveReviewRevisionOutcome.StaleExpectedRevision(
                    0,
                    existingHead.CurrentRevisionNumber,
                    existingHead.CurrentStatus);
            }

            var initialSnapshot = WorkOrderReviewSuggestions.EvaluateFromParsedPages(
                acceptedResult.ResultId,
                Convert.ToHexStringLower(acceptedResult.RawOutputSha256),
                parsedPages);
            var snapshotJson = WorkOrderReviewSuggestions.SerializeSnapshotJson(initialSnapshot);

            var rev1Id = Guid.CreateVersion7(nowUtc);
            var (fieldError, builtFields1) = SaveWorkOrderReviewRevision.ValidateAndBuildFields(
                rev1Id,
                command.OrderedFields,
                initialSnapshot,
                parsedPages);

            if (fieldError is not null)
            {
                await tx.RollbackAsync(CancellationToken.None);
                return fieldError;
            }

            var rev1 = WorkOrderReviewRevision.Create(
                rev1Id,
                command.DocumentId,
                acceptedResult.ResultId,
                revisionNumber: 1,
                command.Status,
                command.IdempotencyKey,
                command.RequestSha256,
                acceptedResult.InputSha256,
                acceptedResult.RawOutputSha256,
                command.OperatorDisplayLabel,
                nowUtc,
                builtFields1!);

            var head1 = WorkOrderReviewHead.CreateInitial(
                command.DocumentId,
                acceptedResult.ResultId,
                acceptedResult.InputSha256,
                acceptedResult.RawOutputSha256,
                snapshotJson,
                rev1Id,
                command.Status,
                nowUtc);

            try
            {
                // Insert revision + fields first so fk_work_order_review_heads_current_revision is satisfied immediately.
                db.WorkOrderReviewRevisions.Add(rev1);
                await db.SaveChangesAsync(cancellationToken);

                db.WorkOrderReviewHeads.Add(head1);
                await db.SaveChangesAsync(cancellationToken);
            }
            catch (DbUpdateException ex) when (ex.InnerException is PostgresException
            {
                SqlState: PostgresErrorCodes.UniqueViolation,
            })
            {
                await tx.RollbackAsync(CancellationToken.None);
                return await ReconcileAfterUniqueConflictAsync(command, cancellationToken);
            }

            var createdDetail1 = MapRevisionDetail(rev1);
            var history1 = new[] { MapRevisionSummary(rev1) };
            await tx.CommitAsync(cancellationToken);

            return new SaveReviewRevisionOutcome.Created(new SavedReviewRevisionResult(
                CurrentRevisionNumber: 1,
                CurrentStatus: command.Status,
                MachineSnapshot: initialSnapshot,
                Revision: createdDetail1,
                History: history1));
        }

        // ExpectedRevision >= 1: serialize directly on work_order_review_heads via FOR UPDATE (F3-BIC-02).
        int lockedRevisionNumber;
        ReviewRevisionStatus lockedStatus;
        string lockedSnapshotJson;

        const string lockHeadSql = """
            SELECT current_revision_number, current_status, machine_snapshot_json
            FROM eledgercare.work_order_review_heads
            WHERE document_id = @docId
            FOR UPDATE
            """;

        await using (var lockCmd = new NpgsqlCommand(lockHeadSql, conn, npgsqlTx))
        {
            lockCmd.Parameters.AddWithValue("docId", command.DocumentId);
            await using var reader = await lockCmd.ExecuteReaderAsync(cancellationToken);
            if (!await reader.ReadAsync(cancellationToken))
            {
                await reader.CloseAsync();
                await tx.RollbackAsync(CancellationToken.None);
                return new SaveReviewRevisionOutcome.StaleExpectedRevision(command.ExpectedRevision, 0, null);
            }

            lockedRevisionNumber = reader.GetInt32(0);
            lockedStatus = ReviewRevisionStatusNames.FromWire(reader.GetString(1));
            lockedSnapshotJson = reader.GetString(2);
        }

        // Re-check Idempotency-Key after acquiring FOR UPDATE so a concurrent duplicate retry that waited
        // behind its twin's commit replays 200 OK rather than failing with stale_expected_revision!
        var postLockReplay = await TryResolveExistingOperationAsync(db, command, cancellationToken);
        if (postLockReplay is not null)
        {
            await tx.RollbackAsync(CancellationToken.None);
            return postLockReplay;
        }

        if (lockedRevisionNumber != command.ExpectedRevision)
        {
            await tx.RollbackAsync(CancellationToken.None);
            return new SaveReviewRevisionOutcome.StaleExpectedRevision(
                command.ExpectedRevision,
                lockedRevisionNumber,
                lockedStatus);
        }

        if (lockedRevisionNumber >= WorkOrderReviewSchema.MaxRevisionsPerResult)
        {
            await tx.RollbackAsync(CancellationToken.None);
            return new SaveReviewRevisionOutcome.RevisionLimitReached(
                lockedRevisionNumber,
                WorkOrderReviewSchema.MaxRevisionsPerResult);
        }

        var machineSnapshot = WorkOrderReviewSuggestions.DeserializeSnapshotJson(lockedSnapshotJson);
        var nextRevisionNumber = lockedRevisionNumber + 1;
        var nextRevisionId = Guid.CreateVersion7(nowUtc);

        var (validationError, builtFields) = SaveWorkOrderReviewRevision.ValidateAndBuildFields(
            nextRevisionId,
            command.OrderedFields,
            machineSnapshot,
            parsedPages);

        if (validationError is not null)
        {
            await tx.RollbackAsync(CancellationToken.None);
            return validationError;
        }

        var nextRevision = WorkOrderReviewRevision.Create(
            nextRevisionId,
            command.DocumentId,
            acceptedResult.ResultId,
            nextRevisionNumber,
            command.Status,
            command.IdempotencyKey,
            command.RequestSha256,
            acceptedResult.InputSha256,
            acceptedResult.RawOutputSha256,
            command.OperatorDisplayLabel,
            nowUtc,
            builtFields!);

        try
        {
            db.WorkOrderReviewRevisions.Add(nextRevision);
            await db.SaveChangesAsync(cancellationToken);
        }
        catch (DbUpdateException ex) when (ex.InnerException is PostgresException
        {
            SqlState: PostgresErrorCodes.UniqueViolation,
        })
        {
            await tx.RollbackAsync(CancellationToken.None);
            return await ReconcileAfterUniqueConflictAsync(command, cancellationToken);
        }

        // Touch ONLY the four column-granted mutable columns on work_order_review_heads (F3-BIC-02).
        const string advanceHeadSql = """
            UPDATE eledgercare.work_order_review_heads
            SET current_revision_number = @nextRev,
                current_revision_id = @nextRevId,
                current_status = @status,
                updated_at = @now
            WHERE document_id = @docId AND current_revision_number = @expectedRev
            """;

        await using (var updateCmd = new NpgsqlCommand(advanceHeadSql, conn, npgsqlTx))
        {
            updateCmd.Parameters.AddWithValue("nextRev", nextRevisionNumber);
            updateCmd.Parameters.AddWithValue("nextRevId", nextRevisionId);
            updateCmd.Parameters.AddWithValue("status", command.Status.ToWire());
            updateCmd.Parameters.AddWithValue("now", nowUtc);
            updateCmd.Parameters.AddWithValue("docId", command.DocumentId);
            updateCmd.Parameters.AddWithValue("expectedRev", command.ExpectedRevision);
            if (await updateCmd.ExecuteNonQueryAsync(cancellationToken) != 1)
            {
                await tx.RollbackAsync(CancellationToken.None);
                throw new InvalidOperationException("Failed to advance locked work_order_review_heads row.");
            }
        }

        var history = await ReadHistorySummariesAsync(db, command.DocumentId, cancellationToken);
        var createdDetail = MapRevisionDetail(nextRevision);
        await tx.CommitAsync(cancellationToken);

        return new SaveReviewRevisionOutcome.Created(new SavedReviewRevisionResult(
            CurrentRevisionNumber: nextRevisionNumber,
            CurrentStatus: command.Status,
            MachineSnapshot: machineSnapshot,
            Revision: createdDetail,
            History: history));
    }

    private async Task<SaveReviewRevisionOutcome> ReconcileAfterUniqueConflictAsync(
        SaveReviewRevisionCommand command,
        CancellationToken cancellationToken)
    {
        await using var freshDb = await contextFactory.CreateDbContextAsync(cancellationToken);
        var replay = await TryResolveExistingOperationAsync(freshDb, command, cancellationToken);
        if (replay is not null)
        {
            return replay;
        }

        var head = await freshDb.WorkOrderReviewHeads.AsNoTracking()
            .Where(h => h.DocumentId == command.DocumentId)
            .Select(h => new { h.CurrentRevisionNumber, h.CurrentStatus })
            .SingleOrDefaultAsync(cancellationToken);

        return new SaveReviewRevisionOutcome.StaleExpectedRevision(
            command.ExpectedRevision,
            head?.CurrentRevisionNumber ?? 0,
            head?.CurrentStatus);
    }

    private static async Task<SaveReviewRevisionOutcome?> TryResolveExistingOperationAsync(
        ELedgerCareDbContext db,
        SaveReviewRevisionCommand command,
        CancellationToken cancellationToken)
    {
        var existingMeta = await db.WorkOrderReviewRevisions.AsNoTracking()
            .Where(r => r.IdempotencyKey == command.IdempotencyKey)
            .Select(r => new
            {
                r.RevisionId,
                r.DocumentId,
                r.RequestSha256,
            })
            .SingleOrDefaultAsync(cancellationToken);

        if (existingMeta is null)
        {
            return null;
        }

        if (existingMeta.DocumentId != command.DocumentId ||
            !CryptographicOperations.FixedTimeEquals(existingMeta.RequestSha256, command.RequestSha256))
        {
            return new SaveReviewRevisionOutcome.IdempotencyKeyConflict();
        }

        var head = await db.WorkOrderReviewHeads.AsNoTracking()
            .Where(h => h.DocumentId == command.DocumentId)
            .Select(h => new
            {
                h.CurrentRevisionNumber,
                h.CurrentStatus,
                h.MachineSnapshotJson,
            })
            .SingleAsync(cancellationToken);

        var replayedDetail = await ReadRevisionDetailAsync(db, existingMeta.RevisionId, cancellationToken)
            ?? throw new InvalidOperationException("Committed revision missing during idempotent replay.");
        var history = await ReadHistorySummariesAsync(db, command.DocumentId, cancellationToken);
        var machineSnapshot = WorkOrderReviewSuggestions.DeserializeSnapshotJson(head.MachineSnapshotJson);

        return new SaveReviewRevisionOutcome.Replayed(new SavedReviewRevisionResult(
            CurrentRevisionNumber: head.CurrentRevisionNumber,
            CurrentStatus: head.CurrentStatus,
            MachineSnapshot: machineSnapshot,
            Revision: replayedDetail,
            History: history));
    }

    internal static IQueryable<ReviewRevisionSummaryProjection> ProjectHistorySummaries(
        ELedgerCareDbContext db,
        Guid documentId) =>
        db.WorkOrderReviewRevisions.AsNoTracking()
            .Where(r => r.DocumentId == documentId)
            .OrderBy(r => r.RevisionNumber)
            .Select(r => new ReviewRevisionSummaryProjection(
                r.RevisionId,
                r.RevisionNumber,
                r.PreviousRevisionNumber,
                r.Status,
                r.OperatorDisplayLabel,
                r.AcceptedFieldCount,
                r.EditedFieldCount,
                r.UnknownFieldCount,
                r.UnreviewedFieldCount,
                r.SavedAtUtc));

    private static async Task<IReadOnlyList<ReviewRevisionSummaryProjection>> ReadHistorySummariesAsync(
        ELedgerCareDbContext db,
        Guid documentId,
        CancellationToken cancellationToken) =>
        await ProjectHistorySummaries(db, documentId).ToListAsync(cancellationToken);

    private static async Task<ReviewRevisionDetailProjection?> ReadRevisionDetailAsync(
        ELedgerCareDbContext db,
        Guid revisionId,
        CancellationToken cancellationToken)
    {
        var rev = await db.WorkOrderReviewRevisions.AsNoTracking()
            .Include(r => r.Fields)
            .SingleOrDefaultAsync(r => r.RevisionId == revisionId, cancellationToken);

        return rev is null ? null : MapRevisionDetail(rev);
    }

    private static ReviewRevisionSummaryProjection MapRevisionSummary(WorkOrderReviewRevision r) => new(
        r.RevisionId,
        r.RevisionNumber,
        r.PreviousRevisionNumber,
        r.Status,
        r.OperatorDisplayLabel,
        r.AcceptedFieldCount,
        r.EditedFieldCount,
        r.UnknownFieldCount,
        r.UnreviewedFieldCount,
        r.SavedAtUtc);

    private static ReviewRevisionDetailProjection MapRevisionDetail(WorkOrderReviewRevision r) => new(
        r.RevisionId,
        r.DocumentId,
        r.ResultId,
        r.RevisionNumber,
        r.PreviousRevisionNumber,
        r.Status,
        r.IdempotencyKey,
        r.RequestSha256,
        r.InputSha256,
        r.RawOutputSha256,
        r.ProfileId,
        r.FieldSchemaVersion,
        r.SuggestionPolicyVersion,
        r.OperatorDisplayLabel,
        r.AcceptedFieldCount,
        r.EditedFieldCount,
        r.UnknownFieldCount,
        r.UnreviewedFieldCount,
        r.SavedAtUtc,
        r.Fields
            .OrderBy(f => f.FieldOrdinal)
            .Select(f => new ReviewFieldProjection(
                f.FieldOrdinal,
                f.FieldKey,
                f.Decision,
                f.HumanValue,
                f.UnknownReason,
                f.GetConsultedSource()))
            .ToArray());
}
