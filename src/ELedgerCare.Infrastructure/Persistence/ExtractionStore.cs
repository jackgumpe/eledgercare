using System.Data;
using System.Globalization;
using ELedgerCare.Application.Extraction;
using ELedgerCare.Application.Review;
using ELedgerCare.Domain.Documents;
using ELedgerCare.Domain.Processing;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;
using Npgsql;
using NpgsqlTypes;

namespace ELedgerCare.Infrastructure.Persistence;

public sealed class ExtractionStore(IDbContextFactory<ELedgerCareDbContext> contextFactory) : IExtractionStore
{
    public async Task<DocumentSummaryProjection?> GetDocumentSummaryAsync(Guid documentId, CancellationToken cancellationToken)
    {
        await using var db = await contextFactory.CreateDbContextAsync(cancellationToken);
        return await ProjectDocumentSummary(db, db.Documents.Where(d => d.DocumentId == documentId))
            .SingleOrDefaultAsync(cancellationToken);
    }

    public async Task<DocumentExtractionSnapshot?> GetDocumentExtractionAsync(Guid documentId, CancellationToken cancellationToken)
    {
        await using var db = await contextFactory.CreateDbContextAsync(cancellationToken);
        return await ReadSnapshotCoreAsync(db, documentId, cancellationToken);
    }

    public async Task<QueueExtractionOutcome> QueueOrReconcileAsync(
        Guid documentId,
        Guid? retryAttemptId,
        int maxExtractionPages,
        bool workerEnabled,
        DateTimeOffset nowUtc,
        CancellationToken cancellationToken)
    {
        await using var db = await contextFactory.CreateDbContextAsync(cancellationToken);
        await using var tx = await db.Database.BeginTransactionAsync(IsolationLevel.ReadCommitted, cancellationToken);
        await db.Database.ExecuteSqlRawAsync("SET LOCAL synchronous_commit = on", cancellationToken);

        var conn = (NpgsqlConnection)db.Database.GetDbConnection();
        var npgsqlTx = (NpgsqlTransaction)tx.GetDbTransaction();

        // Lock the processing_jobs row so concurrent POST /extraction calls serialize deterministically.
        Guid jobId;
        ProcessingStatus status;
        Guid? retriedFromAttemptId;
        int pageCount;

        const string lockSql = """
            SELECT j.job_id, j.status, j.retried_from_attempt_id, a.page_count
            FROM eledgercare.processing_jobs j
            JOIN eledgercare.original_artifacts a ON a.document_id = j.document_id
            WHERE j.document_id = @docId
            FOR UPDATE OF j
            """;

        await using (var lockCmd = new NpgsqlCommand(lockSql, conn, npgsqlTx))
        {
            lockCmd.Parameters.AddWithValue("docId", documentId);
            await using var reader = await lockCmd.ExecuteReaderAsync(cancellationToken);
            if (!await reader.ReadAsync(cancellationToken))
            {
                await reader.CloseAsync();
                await tx.RollbackAsync(CancellationToken.None);
                return new QueueExtractionOutcome.NotFound();
            }

            jobId = reader.GetGuid(0);
            status = ProcessingStatusNames.FromWire(reader.GetString(1));
            retriedFromAttemptId = reader.IsDBNull(2) ? null : reader.GetGuid(2);
            pageCount = reader.GetInt32(3);
        }

        // Latest attempt identity (if any) for replay vs explicit retry validation.
        var latestAttemptId = await db.ExecutionAttempts.AsNoTracking()
            .Where(a => a.JobId == jobId)
            .OrderByDescending(a => a.AttemptNumber)
            .Select(a => (Guid?)a.AttemptId)
            .FirstOrDefaultAsync(cancellationToken);

        if (retryAttemptId is null)
        {
            // Initial request or duplicate reconciliation.
            if (status == ProcessingStatus.Completed)
            {
                var completedSnap = (await ReadSnapshotCoreAsync(db, documentId, cancellationToken))!;
                await tx.CommitAsync(cancellationToken);
                return new QueueExtractionOutcome.AlreadyCompleted(completedSnap);
            }

            if (status is ProcessingStatus.Queued or ProcessingStatus.Running)
            {
                var activeSnap = (await ReadSnapshotCoreAsync(db, documentId, cancellationToken))!;
                await tx.CommitAsync(cancellationToken);
                return new QueueExtractionOutcome.QueuedOrActive(activeSnap);
            }

            if (status is ProcessingStatus.Failed or ProcessingStatus.Interrupted)
            {
                await tx.RollbackAsync(CancellationToken.None);
                return new QueueExtractionOutcome.RetryExplicitRequired(latestAttemptId ?? Guid.Empty);
            }

            // Status == AwaitingExtraction: check profile & worker availability before queuing.
            if (pageCount < 1 || pageCount > maxExtractionPages)
            {
                await tx.RollbackAsync(CancellationToken.None);
                return new QueueExtractionOutcome.ProfileUnsupported(pageCount, maxExtractionPages);
            }

            if (!workerEnabled)
            {
                await tx.RollbackAsync(CancellationToken.None);
                return new QueueExtractionOutcome.WorkerDisabled();
            }

            const string queueSql = """
                UPDATE eledgercare.processing_jobs
                SET status = 'queued', queued_at = @now, updated_at = @now, retried_from_attempt_id = NULL
                WHERE job_id = @jobId AND status = 'awaiting_extraction'
                """;
            await using (var updateCmd = new NpgsqlCommand(queueSql, conn, npgsqlTx))
            {
                updateCmd.Parameters.AddWithValue("now", nowUtc);
                updateCmd.Parameters.AddWithValue("jobId", jobId);
                await updateCmd.ExecuteNonQueryAsync(CancellationToken.None);
            }

            var queuedSnap = (await ReadSnapshotCoreAsync(db, documentId, CancellationToken.None))!;
            await tx.CommitAsync(CancellationToken.None);
            return new QueueExtractionOutcome.QueuedOrActive(queuedSnap);
        }

        // Explicit retry path (retryAttemptId != null).
        var targetAttemptId = retryAttemptId.Value;

        // Concurrent duplicate retry of the same failed/interrupted attempt reconciles cleanly!
        if (status is ProcessingStatus.Queued or ProcessingStatus.Running)
        {
            if (retriedFromAttemptId == targetAttemptId)
            {
                var reconciledSnap = (await ReadSnapshotCoreAsync(db, documentId, cancellationToken))!;
                await tx.CommitAsync(cancellationToken);
                return new QueueExtractionOutcome.QueuedOrActive(reconciledSnap);
            }

            await tx.RollbackAsync(CancellationToken.None);
            return new QueueExtractionOutcome.RetryConflict(
                "extraction_already_active",
                "An extraction attempt is already queued or running for this document.");
        }

        if (status == ProcessingStatus.Completed)
        {
            await tx.RollbackAsync(CancellationToken.None);
            return new QueueExtractionOutcome.RetryConflict(
                "extraction_already_completed",
                "This document already has a completed extraction result.");
        }

        if (status == ProcessingStatus.AwaitingExtraction)
        {
            await tx.RollbackAsync(CancellationToken.None);
            return new QueueExtractionOutcome.RetryConflict(
                "retry_without_prior_attempt",
                "No failed or interrupted extraction attempt exists to retry.");
        }

        if (latestAttemptId != targetAttemptId)
        {
            await tx.RollbackAsync(CancellationToken.None);
            return new QueueExtractionOutcome.RetryConflict(
                "stale_retry_target",
                "retryAttemptId must name the latest failed or interrupted attempt for this document.");
        }

        if (pageCount < 1 || pageCount > maxExtractionPages)
        {
            await tx.RollbackAsync(CancellationToken.None);
            return new QueueExtractionOutcome.ProfileUnsupported(pageCount, maxExtractionPages);
        }

        if (!workerEnabled)
        {
            await tx.RollbackAsync(CancellationToken.None);
            return new QueueExtractionOutcome.WorkerDisabled();
        }

        const string retryQueueSql = """
            UPDATE eledgercare.processing_jobs
            SET status = 'queued', queued_at = @now, updated_at = @now, retried_from_attempt_id = @priorId
            WHERE job_id = @jobId AND status IN ('failed', 'interrupted')
            """;
        await using (var retryCmd = new NpgsqlCommand(retryQueueSql, conn, npgsqlTx))
        {
            retryCmd.Parameters.AddWithValue("now", nowUtc);
            retryCmd.Parameters.AddWithValue("priorId", targetAttemptId);
            retryCmd.Parameters.AddWithValue("jobId", jobId);
            await retryCmd.ExecuteNonQueryAsync(CancellationToken.None);
        }

        var retriedSnap = (await ReadSnapshotCoreAsync(db, documentId, CancellationToken.None))!;
        await tx.CommitAsync(CancellationToken.None);
        return new QueueExtractionOutcome.QueuedOrActive(retriedSnap);
    }

    public async Task<IReadOnlyList<RunningAttemptRecord>> GetRunningAttemptsAsync(CancellationToken cancellationToken)
    {
        await using var db = await contextFactory.CreateDbContextAsync(cancellationToken);
        return await db.ExecutionAttempts.AsNoTracking()
            .Where(a => a.Status == AttemptStatus.Running)
            .OrderBy(a => a.StartedAtUtc)
            .Select(a => new RunningAttemptRecord(
                a.AttemptId,
                a.JobId,
                a.DocumentId,
                a.FencingToken,
                a.RunDirectoryName,
                a.SupervisorInstanceId,
                a.SupervisorPid,
                a.SupervisorCreateFileTime,
                a.LauncherPid,
                a.LauncherCreateFileTime,
                a.WorkerPid,
                a.WorkerCreateFileTime))
            .ToListAsync(cancellationToken);
    }

    public async Task<bool> MarkAttemptInterruptedAsync(
        Guid attemptId,
        Guid jobId,
        long fencingToken,
        string failureCode,
        string failureDetail,
        DateTimeOffset endedAtUtc,
        CancellationToken cancellationToken)
    {
        await using var db = await contextFactory.CreateDbContextAsync(cancellationToken);
        await using var tx = await db.Database.BeginTransactionAsync(IsolationLevel.ReadCommitted, cancellationToken);
        await db.Database.ExecuteSqlRawAsync("SET LOCAL synchronous_commit = on", cancellationToken);

        var conn = (NpgsqlConnection)db.Database.GetDbConnection();
        var npgsqlTx = (NpgsqlTransaction)tx.GetDbTransaction();

        const string jobSql = """
            UPDATE eledgercare.processing_jobs
            SET status = 'interrupted', updated_at = @now
            WHERE job_id = @jobId AND status = 'running' AND latest_fencing_token = @token
            """;
        await using (var jobCmd = new NpgsqlCommand(jobSql, conn, npgsqlTx))
        {
            jobCmd.Parameters.AddWithValue("now", endedAtUtc);
            jobCmd.Parameters.AddWithValue("jobId", jobId);
            jobCmd.Parameters.AddWithValue("token", fencingToken);
            if (await jobCmd.ExecuteNonQueryAsync(cancellationToken) != 1)
            {
                await tx.RollbackAsync(CancellationToken.None);
                return false;
            }
        }

        var safeCode = DiagnosticTextSanitizer.SanitizeRequiredForPostgresText(
            failureCode, DiagnosticTextSanitizer.MaxFailureCodeChars, "supervisor_interrupted");
        var safeDetail = DiagnosticTextSanitizer.SanitizeRequiredForPostgresText(
            failureDetail, ExecutionAttempt.MaxFailureDetailLength, "Local extraction was interrupted.");

        const string attemptSql = """
            UPDATE eledgercare.execution_attempts
            SET status = 'interrupted',
                phase = 'interrupted',
                ended_at = @now,
                last_heartbeat_at = @now,
                failure_code = @code,
                failure_detail = @detail
            WHERE attempt_id = @attemptId AND job_id = @jobId AND status = 'running' AND fencing_token = @token
            """;
        await using (var attCmd = new NpgsqlCommand(attemptSql, conn, npgsqlTx))
        {
            attCmd.Parameters.AddWithValue("now", endedAtUtc);
            attCmd.Parameters.AddWithValue("code", safeCode);
            attCmd.Parameters.AddWithValue("detail", safeDetail);
            attCmd.Parameters.AddWithValue("attemptId", attemptId);
            attCmd.Parameters.AddWithValue("jobId", jobId);
            attCmd.Parameters.AddWithValue("token", fencingToken);
            if (await attCmd.ExecuteNonQueryAsync(cancellationToken) != 1)
            {
                await tx.RollbackAsync(CancellationToken.None);
                return false;
            }
        }

        await tx.CommitAsync(cancellationToken);
        return true;
    }

    public async Task<ClaimedAttemptWork?> ClaimNextQueuedJobAsync(
        Guid supervisorInstanceId,
        int supervisorPid,
        long supervisorCreateFileTime,
        DateTimeOffset nowUtc,
        CancellationToken cancellationToken)
    {
        await using var db = await contextFactory.CreateDbContextAsync(cancellationToken);
        await using var tx = await db.Database.BeginTransactionAsync(IsolationLevel.ReadCommitted, cancellationToken);
        await db.Database.ExecuteSqlRawAsync("SET LOCAL synchronous_commit = on", cancellationToken);

        var conn = (NpgsqlConnection)db.Database.GetDbConnection();
        var npgsqlTx = (NpgsqlTransaction)tx.GetDbTransaction();

        const string selectSql = """
            SELECT job_id, document_id, attempt_count, retried_from_attempt_id
            FROM eledgercare.processing_jobs
            WHERE status = 'queued'
            ORDER BY queued_at ASC, job_id ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
            """;

        Guid jobId;
        Guid documentId;
        int priorCount;
        Guid? retriedFrom;

        await using (var selCmd = new NpgsqlCommand(selectSql, conn, npgsqlTx))
        await using (var reader = await selCmd.ExecuteReaderAsync(cancellationToken))
        {
            if (!await reader.ReadAsync(cancellationToken))
            {
                await reader.CloseAsync();
                await tx.RollbackAsync(CancellationToken.None);
                return null;
            }

            jobId = reader.GetGuid(0);
            documentId = reader.GetGuid(1);
            priorCount = reader.GetInt32(2);
            retriedFrom = reader.IsDBNull(3) ? null : reader.GetGuid(3);
        }

        long fencingToken;
        await using (var seqCmd = new NpgsqlCommand("SELECT nextval('eledgercare.extraction_fencing_seq')", conn, npgsqlTx))
        {
            fencingToken = Convert.ToInt64(await seqCmd.ExecuteScalarAsync(cancellationToken), CultureInfo.InvariantCulture);
        }

        var attemptNumber = priorCount + 1;
        var attemptId = Guid.CreateVersion7(nowUtc);
        var runDirName = $"attempt-{attemptId:D}";

        const string updateJobSql = """
            UPDATE eledgercare.processing_jobs
            SET status = 'running',
                attempt_count = @attemptNumber,
                latest_fencing_token = @token,
                updated_at = @now
            WHERE job_id = @jobId AND status = 'queued'
            """;
        await using (var updCmd = new NpgsqlCommand(updateJobSql, conn, npgsqlTx))
        {
            updCmd.Parameters.AddWithValue("attemptNumber", attemptNumber);
            updCmd.Parameters.AddWithValue("token", fencingToken);
            updCmd.Parameters.AddWithValue("now", nowUtc);
            updCmd.Parameters.AddWithValue("jobId", jobId);
            await updCmd.ExecuteNonQueryAsync(cancellationToken);
        }

        var attempt = ExecutionAttempt.Start(
            attemptId,
            jobId,
            documentId,
            attemptNumber,
            fencingToken,
            retriedFrom,
            runDirName,
            supervisorInstanceId,
            supervisorPid,
            supervisorCreateFileTime,
            nowUtc);

        db.ExecutionAttempts.Add(attempt);
        await db.SaveChangesAsync(cancellationToken);

        var original = await db.OriginalArtifacts.AsNoTracking()
            .Where(a => a.DocumentId == documentId)
            .Select(a => new { a.Bytes, a.Sha256, a.ByteLength, a.PageCount })
            .SingleAsync(cancellationToken);

        await tx.CommitAsync(cancellationToken);

        return new ClaimedAttemptWork(
            attemptId,
            jobId,
            documentId,
            attemptNumber,
            fencingToken,
            runDirName,
            original.Bytes,
            original.Sha256,
            original.ByteLength,
            original.PageCount);
    }

    public async Task<bool> RecordLauncherProcessAsync(
        Guid attemptId,
        long fencingToken,
        int launcherPid,
        long launcherCreateFileTime,
        DateTimeOffset nowUtc,
        CancellationToken cancellationToken)
    {
        await using var db = await contextFactory.CreateDbContextAsync(cancellationToken);
        var conn = (NpgsqlConnection)db.Database.GetDbConnection();
        if (conn.State != ConnectionState.Open)
        {
            await conn.OpenAsync(cancellationToken);
        }

        const string sql = """
            UPDATE eledgercare.execution_attempts
            SET launcher_pid = @pid,
                launcher_create_filetime = @ft,
                phase = 'starting',
                last_heartbeat_at = @now
            WHERE attempt_id = @attemptId AND status = 'running' AND fencing_token = @token
            """;
        await using var cmd = new NpgsqlCommand(sql, conn);
        cmd.Parameters.AddWithValue("pid", launcherPid);
        cmd.Parameters.AddWithValue("ft", launcherCreateFileTime);
        cmd.Parameters.AddWithValue("now", nowUtc);
        cmd.Parameters.AddWithValue("attemptId", attemptId);
        cmd.Parameters.AddWithValue("token", fencingToken);
        return await cmd.ExecuteNonQueryAsync(cancellationToken) == 1;
    }

    public async Task<bool> RecordHeartbeatAsync(
        Guid attemptId,
        long fencingToken,
        string phase,
        int? workerPid,
        long? workerCreateFileTime,
        DateTimeOffset nowUtc,
        CancellationToken cancellationToken)
    {
        await using var db = await contextFactory.CreateDbContextAsync(cancellationToken);
        var conn = (NpgsqlConnection)db.Database.GetDbConnection();
        if (conn.State != ConnectionState.Open)
        {
            await conn.OpenAsync(cancellationToken);
        }

        const string sql = """
            UPDATE eledgercare.execution_attempts
            SET phase = @phase,
                worker_pid = COALESCE(@wPid, worker_pid),
                worker_create_filetime = COALESCE(@wFt, worker_create_filetime),
                last_heartbeat_at = @now
            WHERE attempt_id = @attemptId AND status = 'running' AND fencing_token = @token
            """;
        var safePhase = DiagnosticTextSanitizer.SanitizeRequiredForPostgresText(phase, 64, "running");
        await using var cmd = new NpgsqlCommand(sql, conn);
        cmd.Parameters.AddWithValue("phase", safePhase);
        cmd.Parameters.Add(new NpgsqlParameter("wPid", NpgsqlDbType.Integer) { Value = workerPid is { } p ? p : DBNull.Value });
        cmd.Parameters.Add(new NpgsqlParameter("wFt", NpgsqlDbType.Bigint) { Value = workerCreateFileTime is { } f ? f : DBNull.Value });
        cmd.Parameters.AddWithValue("now", nowUtc);
        cmd.Parameters.AddWithValue("attemptId", attemptId);
        cmd.Parameters.AddWithValue("token", fencingToken);
        return await cmd.ExecuteNonQueryAsync(cancellationToken) == 1;
    }

    public async Task<bool> PublishCompletedResultAsync(
        ExtractionResult result,
        int exitCode,
        DateTimeOffset completedAtUtc,
        CancellationToken cancellationToken)
    {
        await using var db = await contextFactory.CreateDbContextAsync(cancellationToken);
        await using var tx = await db.Database.BeginTransactionAsync(IsolationLevel.ReadCommitted, cancellationToken);
        await db.Database.ExecuteSqlRawAsync("SET LOCAL synchronous_commit = on", cancellationToken);

        var conn = (NpgsqlConnection)db.Database.GetDbConnection();
        var npgsqlTx = (NpgsqlTransaction)tx.GetDbTransaction();

        const string jobSql = """
            UPDATE eledgercare.processing_jobs
            SET status = 'completed', updated_at = @now
            WHERE job_id = @jobId AND status = 'running' AND latest_fencing_token = @token
            """;
        await using (var jobCmd = new NpgsqlCommand(jobSql, conn, npgsqlTx))
        {
            jobCmd.Parameters.AddWithValue("now", completedAtUtc);
            jobCmd.Parameters.AddWithValue("jobId", result.JobId);
            jobCmd.Parameters.AddWithValue("token", result.FencingToken);
            if (await jobCmd.ExecuteNonQueryAsync(cancellationToken) != 1)
            {
                await tx.RollbackAsync(CancellationToken.None);
                return false;
            }
        }

        const string attSql = """
            UPDATE eledgercare.execution_attempts
            SET status = 'completed',
                phase = 'completed',
                ended_at = @now,
                last_heartbeat_at = @now,
                exit_code = @exitCode
            WHERE attempt_id = @attemptId AND job_id = @jobId AND status = 'running' AND fencing_token = @token
            """;
        await using (var attCmd = new NpgsqlCommand(attSql, conn, npgsqlTx))
        {
            attCmd.Parameters.AddWithValue("now", completedAtUtc);
            attCmd.Parameters.AddWithValue("exitCode", exitCode);
            attCmd.Parameters.AddWithValue("attemptId", result.AttemptId);
            attCmd.Parameters.AddWithValue("jobId", result.JobId);
            attCmd.Parameters.AddWithValue("token", result.FencingToken);
            if (await attCmd.ExecuteNonQueryAsync(cancellationToken) != 1)
            {
                await tx.RollbackAsync(CancellationToken.None);
                return false;
            }
        }

        db.ExtractionResults.Add(result);
        try
        {
            await db.SaveChangesAsync(cancellationToken);
        }
        catch (DbUpdateException)
        {
            await tx.RollbackAsync(CancellationToken.None);
            return false;
        }

        await tx.CommitAsync(cancellationToken);
        return true;
    }

    public async Task<bool> MarkAttemptFailedAsync(
        Guid attemptId,
        Guid jobId,
        long fencingToken,
        string failureCode,
        string failureDetail,
        int? exitCode,
        string? diagnosticRawOutputUtf8,
        string? diagnosticMetadataJson,
        DateTimeOffset endedAtUtc,
        CancellationToken cancellationToken)
    {
        await using var db = await contextFactory.CreateDbContextAsync(cancellationToken);
        await using var tx = await db.Database.BeginTransactionAsync(IsolationLevel.ReadCommitted, cancellationToken);
        await db.Database.ExecuteSqlRawAsync("SET LOCAL synchronous_commit = on", cancellationToken);

        var conn = (NpgsqlConnection)db.Database.GetDbConnection();
        var npgsqlTx = (NpgsqlTransaction)tx.GetDbTransaction();

        const string jobSql = """
            UPDATE eledgercare.processing_jobs
            SET status = 'failed', updated_at = @now
            WHERE job_id = @jobId AND status = 'running' AND latest_fencing_token = @token
            """;
        await using (var jobCmd = new NpgsqlCommand(jobSql, conn, npgsqlTx))
        {
            jobCmd.Parameters.AddWithValue("now", endedAtUtc);
            jobCmd.Parameters.AddWithValue("jobId", jobId);
            jobCmd.Parameters.AddWithValue("token", fencingToken);
            if (await jobCmd.ExecuteNonQueryAsync(cancellationToken) != 1)
            {
                await tx.RollbackAsync(CancellationToken.None);
                return false;
            }
        }

        var safeCode = DiagnosticTextSanitizer.SanitizeRequiredForPostgresText(
            failureCode, DiagnosticTextSanitizer.MaxFailureCodeChars, "worker_failed");
        var boundedDetail = DiagnosticTextSanitizer.SanitizeRequiredForPostgresText(
            failureDetail, ExecutionAttempt.MaxFailureDetailLength, "Local OCR execution failed.");
        var boundedDiagRaw = DiagnosticTextSanitizer.SanitizeForPostgresText(
            diagnosticRawOutputUtf8, ExecutionAttempt.MaxDiagnosticOutputChars);
        var sanitizedDiagJson = DiagnosticTextSanitizer.SanitizeDiagnosticJsonOrNull(diagnosticMetadataJson);

        const string attSql = """
            UPDATE eledgercare.execution_attempts
            SET status = 'failed',
                phase = 'failed',
                ended_at = @now,
                last_heartbeat_at = @now,
                exit_code = @exitCode,
                failure_code = @code,
                failure_detail = @detail,
                diagnostic_raw_output_utf8 = @diagRaw,
                diagnostic_metadata_json = @diagJson
            WHERE attempt_id = @attemptId AND job_id = @jobId AND status = 'running' AND fencing_token = @token
            """;
        await using (var attCmd = new NpgsqlCommand(attSql, conn, npgsqlTx))
        {
            attCmd.Parameters.AddWithValue("now", endedAtUtc);
            attCmd.Parameters.Add(new NpgsqlParameter("exitCode", NpgsqlDbType.Integer) { Value = exitCode is { } e ? e : DBNull.Value });
            attCmd.Parameters.AddWithValue("code", safeCode);
            attCmd.Parameters.AddWithValue("detail", boundedDetail);
            attCmd.Parameters.Add(new NpgsqlParameter("diagRaw", NpgsqlDbType.Text) { Value = boundedDiagRaw is not null ? boundedDiagRaw : DBNull.Value });
            attCmd.Parameters.Add(new NpgsqlParameter("diagJson", NpgsqlDbType.Jsonb) { Value = sanitizedDiagJson is not null ? sanitizedDiagJson : DBNull.Value });
            attCmd.Parameters.AddWithValue("attemptId", attemptId);
            attCmd.Parameters.AddWithValue("jobId", jobId);
            attCmd.Parameters.AddWithValue("token", fencingToken);
            if (await attCmd.ExecuteNonQueryAsync(cancellationToken) != 1)
            {
                await tx.RollbackAsync(CancellationToken.None);
                return false;
            }
        }

        await tx.CommitAsync(cancellationToken);
        return true;
    }

    internal static IQueryable<DocumentSummaryProjection> ProjectDocumentSummary(
        ELedgerCareDbContext db,
        IQueryable<Document> documents) =>
        documents.AsNoTracking().Select(d => new DocumentSummaryProjection(
            d.DocumentId,
            d.IdempotencyKey,
            d.Job.JobId,
            d.Job.Status,
            d.SubmittedAtUtc,
            d.Original.ByteLength,
            d.Original.Sha256,
            d.Original.PageCount,
            db.ExecutionAttempts
                .Where(a => a.JobId == d.Job.JobId)
                .OrderByDescending(a => a.AttemptNumber)
                .Select(a => (Guid?)a.AttemptId)
                .FirstOrDefault(),
            db.ExtractionResults
                .Where(r => r.DocumentId == d.DocumentId)
                .Select(r => (Guid?)r.ResultId)
                .SingleOrDefault(),
            (from h in db.WorkOrderReviewHeads
             join rev in db.WorkOrderReviewRevisions on h.CurrentRevisionId equals rev.RevisionId
             where h.DocumentId == d.DocumentId
             select new WorkOrderReviewHeadSummary(
                 h.ProfileId,
                 h.CurrentStatus,
                 h.CurrentRevisionNumber,
                 rev.AcceptedFieldCount,
                 rev.EditedFieldCount,
                 rev.UnknownFieldCount,
                 rev.UnreviewedFieldCount,
                 h.UpdatedAtUtc)).SingleOrDefault()));

    private static async Task<DocumentExtractionSnapshot?> ReadSnapshotCoreAsync(
        ELedgerCareDbContext db,
        Guid documentId,
        CancellationToken cancellationToken)
    {
        var head = await db.Documents.AsNoTracking()
            .Where(d => d.DocumentId == documentId)
            .Select(d => new
            {
                d.DocumentId,
                d.Job.JobId,
                d.Job.Status,
                d.Original.PageCount,
                d.Original.ByteLength,
                d.Original.Sha256,
                d.SubmittedAtUtc,
                d.Job.QueuedAtUtc,
                d.Job.UpdatedAtUtc,
                d.Job.RetriedFromAttemptId,
            })
            .SingleOrDefaultAsync(cancellationToken);

        if (head is null)
        {
            return null;
        }

        var attempts = await db.ExecutionAttempts.AsNoTracking()
            .Where(a => a.JobId == head.JobId)
            .OrderBy(a => a.AttemptNumber)
            .Select(a => new AttemptSummaryProjection(
                a.AttemptId,
                a.AttemptNumber,
                a.Status,
                a.Phase,
                a.StartedAtUtc,
                a.LastHeartbeatAtUtc,
                a.EndedAtUtc,
                a.FailureCode,
                a.FailureDetail))
            .ToListAsync(cancellationToken);

        var acceptedResult = head.Status == ProcessingStatus.Completed
            ? await db.ExtractionResults.AsNoTracking()
                .SingleOrDefaultAsync(r => r.DocumentId == documentId, cancellationToken)
            : null;

        var reviewHeadSummary = acceptedResult is not null
            ? await (from h in db.WorkOrderReviewHeads.AsNoTracking()
                     join rev in db.WorkOrderReviewRevisions.AsNoTracking() on h.CurrentRevisionId equals rev.RevisionId
                     where h.DocumentId == documentId
                     select new WorkOrderReviewHeadSummary(
                         h.ProfileId,
                         h.CurrentStatus,
                         h.CurrentRevisionNumber,
                         rev.AcceptedFieldCount,
                         rev.EditedFieldCount,
                         rev.UnknownFieldCount,
                         rev.UnreviewedFieldCount,
                         h.UpdatedAtUtc))
                .SingleOrDefaultAsync(cancellationToken)
            : null;

        return new DocumentExtractionSnapshot(
            head.DocumentId,
            head.JobId,
            head.Status,
            head.PageCount,
            head.ByteLength,
            head.Sha256,
            head.SubmittedAtUtc,
            head.QueuedAtUtc,
            head.UpdatedAtUtc,
            head.RetriedFromAttemptId,
            attempts,
            acceptedResult,
            reviewHeadSummary);
    }
}
