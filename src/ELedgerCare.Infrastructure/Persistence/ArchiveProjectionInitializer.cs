using System.Data;
using System.Security.Cryptography;
using ELedgerCare.Application.Archive;
using ELedgerCare.Domain.Archive;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Npgsql;

namespace ELedgerCare.Infrastructure.Persistence;

public sealed record ArchiveBackfillOptions
{
    public const string Section = "Archive";

    public int BatchSize { get; init; } = 32;

    public bool DeferStartupInitialization { get; init; }

    public bool AutoCatchUpOnSearch { get; init; } = true;
}

public sealed record ArchiveBackfillRunReceipt(
    ArchiveReadinessStatus Status,
    int VerifiedExistingCount,
    int NewlyProjectedCount,
    int ReconciledConcurrentCount,
    bool StoppedAtLimit,
    string? DiagnosticReason);

/// <summary>
/// Bounded, idempotent startup and catch-up initializer for archive machine projections (F4-BIC-05).
/// Works with LocalOcr:Enabled=false, processes identities in result_id batches and materializes at most
/// one &lt;= 16 MiB raw output at a time, reconciles 23505 concurrent initializer races via deterministic
/// projection_sha256 equality, and fails closed (Conflict -> 503) without mutating data on any mismatch.
/// </summary>
public sealed class ArchiveProjectionInitializer : IArchiveProjectionReadiness, IDisposable
{
    private readonly IDbContextFactory<ELedgerCareDbContext> _contextFactory;
    private readonly string _runtimeConnectionString;
    private readonly ArchiveBackfillOptions _options;
    private readonly TimeProvider _timeProvider;
    private readonly ILogger<ArchiveProjectionInitializer> _logger;
    private readonly SemaphoreSlim _singleFlight = new(1, 1);
    private readonly Lock _stateLock = new();

    private ArchiveReadinessSnapshot _snapshot = new(
        ArchiveReadinessStatus.Initializing,
        ArchiveSchema.ProjectionVersion,
        "Archive projection initializer has not completed yet.");

    public ArchiveProjectionInitializer(
        IDbContextFactory<ELedgerCareDbContext> contextFactory,
        string runtimeConnectionString,
        ArchiveBackfillOptions options,
        TimeProvider timeProvider,
        ILogger<ArchiveProjectionInitializer> logger)
    {
        ArgumentNullException.ThrowIfNull(contextFactory);
        ArgumentException.ThrowIfNullOrWhiteSpace(runtimeConnectionString);
        ArgumentNullException.ThrowIfNull(options);
        ArgumentNullException.ThrowIfNull(timeProvider);
        ArgumentNullException.ThrowIfNull(logger);

        if (options.BatchSize is < 1 or > 256)
        {
            throw new InvalidOperationException("Archive:BatchSize must be within 1..256.");
        }

        _contextFactory = contextFactory;
        _runtimeConnectionString = runtimeConnectionString;
        _options = options;
        _timeProvider = timeProvider;
        _logger = logger;
    }

    public bool AutoCatchUpOnSearch => _options.AutoCatchUpOnSearch;

    public ArchiveReadinessSnapshot GetSnapshot()
    {
        lock (_stateLock)
        {
            return _snapshot;
        }
    }

    public void SetManualReadinessForTesting(ArchiveReadinessSnapshot snapshot)
    {
        lock (_stateLock)
        {
            _snapshot = snapshot;
        }
    }

    public async Task InitializeStartupAsync(CancellationToken cancellationToken)
    {
        if (_options.DeferStartupInitialization)
        {
            SetSnapshot(
                ArchiveReadinessStatus.Initializing,
                "Archive startup initialization is deferred; projections are not ready yet.");
            return;
        }

        await EnsureCaughtUpAsync(cancellationToken);
    }

    public async Task<ArchiveReadinessSnapshot> EnsureCaughtUpAsync(CancellationToken cancellationToken)
    {
        await _singleFlight.WaitAsync(cancellationToken);
        try
        {
            var current = GetSnapshot();
            if (current.Status == ArchiveReadinessStatus.Conflict)
            {
                return current;
            }

            await RunBoundedPassCoreAsync(maxNewProjections: null, beforeCommitHook: null, cancellationToken);
            return GetSnapshot();
        }
        finally
        {
            _singleFlight.Release();
        }
    }

    public async Task<ArchiveBackfillRunReceipt> RunBoundedPassAsync(
        int? maxNewProjections = null,
        Func<Guid, CancellationToken, Task>? beforeCommitHook = null,
        CancellationToken cancellationToken = default)
    {
        await _singleFlight.WaitAsync(cancellationToken);
        try
        {
            return await RunBoundedPassCoreAsync(maxNewProjections, beforeCommitHook, cancellationToken);
        }
        finally
        {
            _singleFlight.Release();
        }
    }

    private async Task<ArchiveBackfillRunReceipt> RunBoundedPassCoreAsync(
        int? maxNewProjections,
        Func<Guid, CancellationToken, Task>? beforeCommitHook,
        CancellationToken cancellationToken)
    {
        var verifiedExisting = 0;
        var newlyProjected = 0;
        var reconciledConcurrent = 0;

        await using var conn = new NpgsqlConnection(_runtimeConnectionString);
        await conn.OpenAsync(cancellationToken);

        // Phase 1: Verify existing current-version projections in bounded result_id batches
        // without materializing raw_output_bytes blobs.
        Guid? lastVerifiedResultId = null;
        while (true)
        {
            var existingBatch = await LoadExistingProjectionHeaderBatchAsync(conn, lastVerifiedResultId, _options.BatchSize, cancellationToken);
            if (existingBatch.Count == 0)
            {
                break;
            }

            foreach (var row in existingBatch)
            {
                lastVerifiedResultId = row.ResultId;
                if (!row.ResultExists ||
                    row.DocumentId != row.ExpectedDocumentId ||
                    row.ExpectedRawSha256 is null ||
                    !CryptographicOperations.FixedTimeEquals(row.RawOutputSha256, row.ExpectedRawSha256))
                {
                    return MarkConflict(
                        $"Existing archive projection for result {row.ResultId:D} disagrees with extraction_results identity.",
                        verifiedExisting,
                        newlyProjected,
                        reconciledConcurrent);
                }

                var units = await LoadUnitsForResultAsync(conn, row.ResultId, row.DocumentId, cancellationToken);
                if (units.Count != row.UnitCount)
                {
                    return MarkConflict(
                        $"Existing archive projection for result {row.ResultId:D} declares {row.UnitCount} units but stores {units.Count}.",
                        verifiedExisting,
                        newlyProjected,
                        reconciledConcurrent);
                }

                var recomputedSha = ArchiveMachineProjector.ComputeProjectionSha256(
                    row.ResultId,
                    row.DocumentId,
                    ArchiveSchema.ProjectionVersion,
                    row.RawOutputSha256,
                    row.HasFallback,
                    units);
                if (!CryptographicOperations.FixedTimeEquals(recomputedSha, row.ProjectionSha256))
                {
                    return MarkConflict(
                        $"Existing archive projection digest mismatch for result {row.ResultId:D}.",
                        verifiedExisting,
                        newlyProjected,
                        reconciledConcurrent);
                }

                verifiedExisting++;
            }
        }

        // Phase 2: Stream missing extraction_results identities in bounded batches and materialize
        // at most one raw_output_bytes blob (<= 16 MiB) at a time.
        Guid? lastProjectedResultId = null;
        while (true)
        {
            var missingIdentities = await LoadMissingResultIdentityBatchAsync(conn, lastProjectedResultId, _options.BatchSize, cancellationToken);
            if (missingIdentities.Count == 0)
            {
                break;
            }

            foreach (var missing in missingIdentities)
            {
                if (maxNewProjections is int cap && (newlyProjected + reconciledConcurrent) >= cap)
                {
                    SetSnapshot(
                        ArchiveReadinessStatus.Initializing,
                        "Archive projection backfill paused with remaining unprojected results.");
                    return new ArchiveBackfillRunReceipt(
                        ArchiveReadinessStatus.Initializing,
                        verifiedExisting,
                        newlyProjected,
                        reconciledConcurrent,
                        StoppedAtLimit: true,
                        DiagnosticReason: "Stopped at requested maxNewProjections limit.");
                }

                lastProjectedResultId = missing.ResultId;
                var rawBytes = await LoadSingleRawOutputBytesAsync(conn, missing.ResultId, cancellationToken);
                if (rawBytes is null)
                {
                    return MarkConflict(
                        $"Extraction result {missing.ResultId:D} disappeared during projection backfill.",
                        verifiedExisting,
                        newlyProjected,
                        reconciledConcurrent);
                }

                ArchiveResultProjection projection;
                try
                {
                    projection = ArchiveMachineProjector.ProjectFromBytes(
                        missing.ResultId,
                        missing.DocumentId,
                        rawBytes,
                        missing.RawOutputSha256,
                        missing.PageCount,
                        _timeProvider.GetUtcNow());
                }
                catch (Exception ex) when (ex is not OperationCanceledException)
                {
                    _logger.LogError(ex, "Archive projection computation failed for result {ResultId}.", missing.ResultId);
                    return MarkConflict(
                        $"Saved extraction result {missing.ResultId:D} failed archive projection integrity check.",
                        verifiedExisting,
                        newlyProjected,
                        reconciledConcurrent);
                }

                var outcome = await CommitOrReconcileSingleProjectionAsync(
                    projection,
                    beforeCommitHook,
                    cancellationToken);

                if (outcome == SingleProjectionOutcome.Committed)
                {
                    newlyProjected++;
                }
                else if (outcome == SingleProjectionOutcome.ReconciledConcurrentWinner)
                {
                    reconciledConcurrent++;
                }
                else
                {
                    return MarkConflict(
                        $"Concurrent archive projection for result {missing.ResultId:D} conflicted with expected digest.",
                        verifiedExisting,
                        newlyProjected,
                        reconciledConcurrent);
                }
            }
        }

        SetSnapshot(ArchiveReadinessStatus.Ready, null);
        _logger.LogInformation(
            "Archive machine projections ready ({Version}): {Verified} existing verified, {NewlyProjected} projected, {Reconciled} concurrent reconciled.",
            ArchiveSchema.ProjectionVersion,
            verifiedExisting,
            newlyProjected,
            reconciledConcurrent);

        return new ArchiveBackfillRunReceipt(
            ArchiveReadinessStatus.Ready,
            verifiedExisting,
            newlyProjected,
            reconciledConcurrent,
            StoppedAtLimit: false,
            DiagnosticReason: null);
    }

    private async Task<SingleProjectionOutcome> CommitOrReconcileSingleProjectionAsync(
        ArchiveResultProjection projection,
        Func<Guid, CancellationToken, Task>? beforeCommitHook,
        CancellationToken cancellationToken)
    {
        await using (var db = await _contextFactory.CreateDbContextAsync(cancellationToken))
        {
            await using var tx = await db.Database.BeginTransactionAsync(IsolationLevel.ReadCommitted, cancellationToken);
            await db.Database.ExecuteSqlRawAsync("SET LOCAL synchronous_commit = on", cancellationToken);

            db.ArchiveResultProjections.Add(projection);

            try
            {
                if (beforeCommitHook is not null)
                {
                    await beforeCommitHook(projection.ResultId, cancellationToken);
                }

                await db.SaveChangesAsync(cancellationToken);
                await tx.CommitAsync(cancellationToken);
                return SingleProjectionOutcome.Committed;
            }
            catch (DbUpdateException ex) when (ex.InnerException is PostgresException { SqlState: PostgresErrorCodes.UniqueViolation })
            {
                await tx.RollbackAsync(CancellationToken.None);
            }
        }

        // Another initializer inserted the row concurrently: verify the committed winner matches
        // our deterministic projection_sha256 and unit_count byte-for-byte!
        await using var verifyConn = new NpgsqlConnection(_runtimeConnectionString);
        await verifyConn.OpenAsync(cancellationToken);

        const string winnerSql = """
            SELECT arp.document_id, arp.raw_output_sha256, arp.projection_sha256, arp.unit_count, arp.has_fallback
            FROM eledgercare.archive_result_projections arp
            WHERE arp.result_id = @resultId AND arp.projection_version = @ver
            """;
        await using var cmd = new NpgsqlCommand(winnerSql, verifyConn);
        cmd.Parameters.AddWithValue("resultId", projection.ResultId);
        cmd.Parameters.AddWithValue("ver", ArchiveSchema.ProjectionVersion);

        await using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
        if (!await reader.ReadAsync(cancellationToken))
        {
            return SingleProjectionOutcome.Conflict;
        }

        var winnerDocId = reader.GetGuid(0);
        var winnerRawSha = (byte[])reader[1];
        var winnerProjSha = (byte[])reader[2];
        var winnerUnitCount = reader.GetInt32(3);
        var winnerHasFallback = reader.GetBoolean(4);
        await reader.CloseAsync();

        if (winnerDocId != projection.DocumentId ||
            winnerUnitCount != projection.UnitCount ||
            winnerHasFallback != projection.HasFallback ||
            !CryptographicOperations.FixedTimeEquals(winnerRawSha, projection.RawOutputSha256) ||
            !CryptographicOperations.FixedTimeEquals(winnerProjSha, projection.ProjectionSha256))
        {
            return SingleProjectionOutcome.Conflict;
        }

        var winnerUnits = await LoadUnitsForResultAsync(verifyConn, projection.ResultId, projection.DocumentId, cancellationToken);
        if (winnerUnits.Count != projection.UnitCount)
        {
            return SingleProjectionOutcome.Conflict;
        }

        var recomputedWinnerSha = ArchiveMachineProjector.ComputeProjectionSha256(
            projection.ResultId,
            projection.DocumentId,
            ArchiveSchema.ProjectionVersion,
            winnerRawSha,
            winnerHasFallback,
            winnerUnits);

        return CryptographicOperations.FixedTimeEquals(recomputedWinnerSha, projection.ProjectionSha256)
            ? SingleProjectionOutcome.ReconciledConcurrentWinner
            : SingleProjectionOutcome.Conflict;
    }

    private ArchiveBackfillRunReceipt MarkConflict(
        string reason,
        int verifiedExisting,
        int newlyProjected,
        int reconciledConcurrent)
    {
        _logger.LogError("Archive projection conflict detected: {Reason}", reason);
        SetSnapshot(ArchiveReadinessStatus.Conflict, reason);
        return new ArchiveBackfillRunReceipt(
            ArchiveReadinessStatus.Conflict,
            verifiedExisting,
            newlyProjected,
            reconciledConcurrent,
            StoppedAtLimit: false,
            DiagnosticReason: reason);
    }

    private void SetSnapshot(ArchiveReadinessStatus status, string? reason)
    {
        lock (_stateLock)
        {
            _snapshot = new ArchiveReadinessSnapshot(status, ArchiveSchema.ProjectionVersion, reason);
        }
    }

    private static async Task<List<ExistingProjectionHeaderRow>> LoadExistingProjectionHeaderBatchAsync(
        NpgsqlConnection conn,
        Guid? afterResultId,
        int batchSize,
        CancellationToken cancellationToken)
    {
        const string sql = """
            SELECT arp.result_id,
                   arp.document_id,
                   arp.raw_output_sha256,
                   arp.projection_sha256,
                   arp.unit_count,
                   arp.has_fallback,
                   er.result_id IS NOT NULL AS result_exists,
                   er.document_id AS expected_document_id,
                   er.raw_output_sha256 AS expected_raw_sha256
            FROM eledgercare.archive_result_projections arp
            LEFT JOIN eledgercare.extraction_results er ON er.result_id = arp.result_id
            WHERE arp.projection_version = @ver
              AND (@afterId IS NULL OR arp.result_id > @afterId)
            ORDER BY arp.result_id ASC
            LIMIT @batchSize
            """;

        await using var cmd = new NpgsqlCommand(sql, conn);
        cmd.Parameters.AddWithValue("ver", ArchiveSchema.ProjectionVersion);
        cmd.Parameters.Add(new NpgsqlParameter("afterId", NpgsqlTypes.NpgsqlDbType.Uuid)
        {
            Value = afterResultId is Guid id ? id : DBNull.Value,
        });
        cmd.Parameters.AddWithValue("batchSize", batchSize);

        var list = new List<ExistingProjectionHeaderRow>(batchSize);
        await using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            var resultExists = reader.GetBoolean(6);
            list.Add(new ExistingProjectionHeaderRow(
                ResultId: reader.GetGuid(0),
                DocumentId: reader.GetGuid(1),
                RawOutputSha256: (byte[])reader[2],
                ProjectionSha256: (byte[])reader[3],
                UnitCount: reader.GetInt32(4),
                HasFallback: reader.GetBoolean(5),
                ResultExists: resultExists,
                ExpectedDocumentId: resultExists ? reader.GetGuid(7) : Guid.Empty,
                ExpectedRawSha256: resultExists ? (byte[])reader[8] : null));
        }

        return list;
    }

    private static async Task<List<ArchiveProjectionUnit>> LoadUnitsForResultAsync(
        NpgsqlConnection conn,
        Guid resultId,
        Guid expectedDocumentId,
        CancellationToken cancellationToken)
    {
        const string sql = """
            SELECT unit_ordinal, document_id, page_number, unit_kind, is_fallback, search_text
            FROM eledgercare.archive_projection_units
            WHERE result_id = @resultId AND projection_version = @ver
            ORDER BY unit_ordinal ASC
            """;

        await using var cmd = new NpgsqlCommand(sql, conn);
        cmd.Parameters.AddWithValue("resultId", resultId);
        cmd.Parameters.AddWithValue("ver", ArchiveSchema.ProjectionVersion);

        var units = new List<ArchiveProjectionUnit>();
        await using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            var ordinal = reader.GetInt32(0);
            var docId = reader.GetGuid(1);
            if (ordinal != units.Count || docId != expectedDocumentId)
            {
                // Return an empty/short list so caller flags integrity mismatch immediately.
                return [];
            }

            int? pageNumber = reader.IsDBNull(2) ? null : reader.GetInt32(2);
            var unitKind = reader.GetString(3);
            var isFallback = reader.GetBoolean(4);
            var searchText = reader.GetString(5);

            units.Add(new ArchiveProjectionUnit(
                resultId,
                ArchiveSchema.ProjectionVersion,
                ordinal,
                docId,
                pageNumber,
                unitKind,
                isFallback,
                searchText));
        }

        return units;
    }

    private static async Task<List<MissingResultIdentityRow>> LoadMissingResultIdentityBatchAsync(
        NpgsqlConnection conn,
        Guid? afterResultId,
        int batchSize,
        CancellationToken cancellationToken)
    {
        const string sql = """
            SELECT er.result_id, er.document_id, er.raw_output_sha256, er.page_count
            FROM eledgercare.extraction_results er
            WHERE (@afterId IS NULL OR er.result_id > @afterId)
              AND NOT EXISTS (
                  SELECT 1 FROM eledgercare.archive_result_projections arp
                  WHERE arp.result_id = er.result_id AND arp.projection_version = @ver
              )
            ORDER BY er.result_id ASC
            LIMIT @batchSize
            """;

        await using var cmd = new NpgsqlCommand(sql, conn);
        cmd.Parameters.AddWithValue("ver", ArchiveSchema.ProjectionVersion);
        cmd.Parameters.Add(new NpgsqlParameter("afterId", NpgsqlTypes.NpgsqlDbType.Uuid)
        {
            Value = afterResultId is Guid id ? id : DBNull.Value,
        });
        cmd.Parameters.AddWithValue("batchSize", batchSize);

        var list = new List<MissingResultIdentityRow>(batchSize);
        await using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            list.Add(new MissingResultIdentityRow(
                ResultId: reader.GetGuid(0),
                DocumentId: reader.GetGuid(1),
                RawOutputSha256: (byte[])reader[2],
                PageCount: reader.GetInt32(3)));
        }

        return list;
    }

    private static async Task<byte[]?> LoadSingleRawOutputBytesAsync(
        NpgsqlConnection conn,
        Guid resultId,
        CancellationToken cancellationToken)
    {
        const string sql = "SELECT raw_output_bytes FROM eledgercare.extraction_results WHERE result_id = @resultId";
        await using var cmd = new NpgsqlCommand(sql, conn);
        cmd.Parameters.AddWithValue("resultId", resultId);
        var scalar = await cmd.ExecuteScalarAsync(cancellationToken);
        return scalar as byte[];
    }

    public void Dispose()
    {
        _singleFlight.Dispose();
    }

    private enum SingleProjectionOutcome
    {
        Committed,
        ReconciledConcurrentWinner,
        Conflict,
    }

    private sealed record ExistingProjectionHeaderRow(
        Guid ResultId,
        Guid DocumentId,
        byte[] RawOutputSha256,
        byte[] ProjectionSha256,
        int UnitCount,
        bool HasFallback,
        bool ResultExists,
        Guid ExpectedDocumentId,
        byte[]? ExpectedRawSha256);

    private sealed record MissingResultIdentityRow(
        Guid ResultId,
        Guid DocumentId,
        byte[] RawOutputSha256,
        int PageCount);
}
