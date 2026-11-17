using System.Data;
using System.Text;
using ELedgerCare.Application.Archive;
using ELedgerCare.Domain.Archive;
using ELedgerCare.Domain.Processing;
using ELedgerCare.Domain.Review;
using Npgsql;

namespace ELedgerCare.Infrastructure.Persistence;

/// <summary>
/// Read-only single-snapshot archive search store (F4-BIC-01, F4-BIC-03, F4-BIC-04, F4-BIC-06).
/// Every GET /api/archive query executes inside one IsolationLevel.RepeatableRead READ ONLY transaction,
/// never selects original/raw/diagnostic/machine-snapshot blobs, and fails closed (503) if any
/// committed extraction_results row lacks a current-version projection.
/// </summary>
public sealed class ArchiveStore : IArchiveStore
{
    private readonly string _runtimeConnectionString;
    private readonly ArchiveProjectionInitializer _initializer;

    public ArchiveStore(
        string runtimeConnectionString,
        ArchiveProjectionInitializer initializer)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(runtimeConnectionString);
        ArgumentNullException.ThrowIfNull(initializer);
        _runtimeConnectionString = runtimeConnectionString;
        _initializer = initializer;
    }

    public async Task<ArchiveSearchOutcome> SearchAsync(
        ParsedArchiveQuery query,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(query);

        var attempt = await TryExecuteRepeatableReadSearchAsync(query, cancellationToken);
        if (!attempt.FoundUnprojectedRows)
        {
            return attempt.Outcome!;
        }

        // An extraction_results row existed without a current-version projection (e.g., external SQL seed
        // inserted after startup). Either catch up via the bounded single-flight initializer and open a
        // fresh REPEATABLE READ snapshot, or fail closed with 503 if on-demand catch-up is disabled.
        if (!_initializer.AutoCatchUpOnSearch)
        {
            return new ArchiveSearchOutcome(
                ArchiveReadinessStatus.Initializing,
                "Archive projections are incomplete; retry after backfill completes.",
                Page: null);
        }

        var caughtUp = await _initializer.EnsureCaughtUpAsync(cancellationToken);
        if (caughtUp.Status != ArchiveReadinessStatus.Ready)
        {
            return new ArchiveSearchOutcome(
                caughtUp.Status,
                caughtUp.DiagnosticReason ?? "Archive projections are not ready.",
                Page: null);
        }

        var retryAttempt = await TryExecuteRepeatableReadSearchAsync(query, cancellationToken);
        if (retryAttempt.FoundUnprojectedRows)
        {
            return new ArchiveSearchOutcome(
                ArchiveReadinessStatus.Initializing,
                "Archive projections are still catching up; retry shortly.",
                Page: null);
        }

        return retryAttempt.Outcome!;
    }

    private async Task<(bool FoundUnprojectedRows, ArchiveSearchOutcome? Outcome)> TryExecuteRepeatableReadSearchAsync(
        ParsedArchiveQuery query,
        CancellationToken cancellationToken)
    {
        await using var conn = new NpgsqlConnection(_runtimeConnectionString);
        await conn.OpenAsync(cancellationToken);
        await using var tx = await conn.BeginTransactionAsync(IsolationLevel.RepeatableRead, cancellationToken);

        await using (var sessionCmd = new NpgsqlCommand(
            "SET TRANSACTION READ ONLY; SET LOCAL statement_timeout = '15s';",
            conn,
            tx))
        {
            await sessionCmd.ExecuteNonQueryAsync(cancellationToken);
        }

        // Guard inside the pinned MVCC snapshot: never serve a misleading partial/empty 200 OK if any
        // committed extraction_results row lacks its current-version projection marker (F4-BIC-05).
        await using (var guardCmd = new NpgsqlCommand(UnprojectedGuardSql, conn, tx))
        {
            guardCmd.Parameters.AddWithValue("projVer", ArchiveSchema.ProjectionVersion);
            var hasUnprojected = (bool)(await guardCmd.ExecuteScalarAsync(cancellationToken))!;
            if (hasUnprojected)
            {
                await tx.RollbackAsync(CancellationToken.None);
                return (FoundUnprojectedRows: true, Outcome: null);
            }
        }

        var sql = BuildSearchCardHeadersSql(query);
        var rawRows = new List<CardHeaderRow>(query.Limit + 1);
        await using (var searchCmd = new NpgsqlCommand(sql, conn, tx))
        {
            BindSearchParameters(searchCmd, query);
            await using var reader = await searchCmd.ExecuteReaderAsync(cancellationToken);
            while (await reader.ReadAsync(cancellationToken))
            {
                var hasResult = !reader.IsDBNull(6);
                var hasProjection = !reader.IsDBNull(9);
                var hasLatestReviewed = !reader.IsDBNull(12);
                var hasReviewHead = !reader.IsDBNull(17);

                rawRows.Add(new CardHeaderRow(
                    DocumentId: reader.GetGuid(0),
                    SubmittedAtUtc: reader.GetFieldValue<DateTimeOffset>(1),
                    AdmittedPageCount: reader.GetInt32(2),
                    OriginalByteLength: reader.GetInt32(3),
                    OriginalSha256: (byte[])reader[4],
                    JobStatus: ProcessingStatusNames.FromWire(reader.GetString(5)),
                    ResultId: hasResult ? reader.GetGuid(6) : null,
                    RawOutputSha256: hasResult ? (byte[])reader[7] : null,
                    ExtractedPageCount: hasResult ? reader.GetInt32(8) : null,
                    ProjectionVersion: hasProjection ? reader.GetString(9) : null,
                    ProjectionSha256: hasProjection ? (byte[])reader[10] : null,
                    ProjectionHasFallback: hasProjection ? reader.GetBoolean(11) : null,
                    LatestReviewedRevisionId: hasLatestReviewed ? reader.GetGuid(12) : null,
                    LatestReviewedRevisionNumber: hasLatestReviewed ? reader.GetInt32(13) : null,
                    LatestReviewedSavedAtUtc: hasLatestReviewed ? reader.GetFieldValue<DateTimeOffset>(14) : null,
                    LatestReviewedWorkOrderId: reader.IsDBNull(15) ? null : reader.GetString(15),
                    LatestReviewedPropertyName: reader.IsDBNull(16) ? null : reader.GetString(16),
                    HeadRevisionNumber: hasReviewHead ? reader.GetInt32(17) : null,
                    HeadStatus: hasReviewHead ? ReviewRevisionStatusNames.FromWire(reader.GetString(18)) : null,
                    HeadUpdatedAtUtc: hasReviewHead ? reader.GetFieldValue<DateTimeOffset>(19) : null));
            }
        }

        var hasMore = rawRows.Count > query.Limit;
        var pageRows = hasMore ? rawRows.GetRange(0, query.Limit) : rawRows;

        var unitsByDocument = new Dictionary<Guid, List<CandidateArchiveUnit>>(pageRows.Count);
        if (query.Terms.Count > 0 && pageRows.Count > 0)
        {
            for (var i = 0; i < pageRows.Count; i++)
            {
                unitsByDocument[pageRows[i].DocumentId] = [];
            }

            if (query.Source is ArchiveSourceFilter.All or ArchiveSourceFilter.Reviewed)
            {
                await LoadReviewedUnitsForPageAsync(conn, tx, pageRows, unitsByDocument, cancellationToken);
            }

            if (query.Source is ArchiveSourceFilter.All or ArchiveSourceFilter.Machine)
            {
                await LoadMachineUnitsForPageAsync(conn, tx, pageRows, unitsByDocument, cancellationToken);
            }
        }

        await tx.CommitAsync(cancellationToken);

        var cards = new List<ArchiveDocumentCard>(pageRows.Count);
        for (var i = 0; i < pageRows.Count; i++)
        {
            var r = pageRows[i];
            var latestReviewed = r.LatestReviewedRevisionNumber is int lrNum && r.LatestReviewedSavedAtUtc is DateTimeOffset lrSaved
                ? new ArchiveReviewedSummary(lrNum, lrSaved, r.LatestReviewedWorkOrderId, r.LatestReviewedPropertyName)
                : null;

            var currentHead = r.HeadRevisionNumber is int hNum && r.HeadStatus is ReviewRevisionStatus hStatus && r.HeadUpdatedAtUtc is DateTimeOffset hUpd
                ? new ArchiveHeadReviewSummary(hNum, hStatus, hUpd)
                : null;

            var hasNewerDraft = latestReviewed is not null &&
                                currentHead is { CurrentStatus: ReviewRevisionStatus.Draft } &&
                                currentHead.CurrentRevisionNumber > latestReviewed.RevisionNumber;

            IReadOnlyList<string> contributingSources = [];
            IReadOnlyList<SelectedArchiveWitness> witnesses = [];
            var hasMoreMatchesInDoc = false;

            if (query.Terms.Count > 0)
            {
                var selection = ArchiveSnippetBuilder.SelectWitnesses(
                    query.Terms,
                    unitsByDocument[r.DocumentId]);
                contributingSources = selection.ContributingSources;
                witnesses = selection.Witnesses;
                hasMoreMatchesInDoc = selection.HasMoreMatchesInDocument;
            }

            cards.Add(new ArchiveDocumentCard(
                DocumentId: r.DocumentId,
                SubmittedAtUtc: r.SubmittedAtUtc,
                AdmittedPageCount: r.AdmittedPageCount,
                OriginalByteLength: r.OriginalByteLength,
                OriginalSha256: r.OriginalSha256,
                ProcessingStatus: r.JobStatus,
                ResultId: r.ResultId,
                RawOutputSha256: r.RawOutputSha256,
                ExtractedPageCount: r.ExtractedPageCount,
                ProjectionVersion: r.ProjectionVersion,
                ProjectionSha256: r.ProjectionSha256,
                ProjectionHasFallback: r.ProjectionHasFallback,
                LatestReviewed: latestReviewed,
                CurrentReviewHead: currentHead,
                HasNewerDraft: hasNewerDraft,
                ContributingSources: contributingSources,
                Witnesses: witnesses,
                HasMoreMatchesInDocument: hasMoreMatchesInDoc));
        }

        string? nextCursor = null;
        if (hasMore && cards.Count > 0)
        {
            var last = cards[^1];
            nextCursor = ArchiveCursor.Encode(last.SubmittedAtUtc, last.DocumentId, query.Source, query.Terms);
        }

        return (
            FoundUnprojectedRows: false,
            Outcome: new ArchiveSearchOutcome(
                ArchiveReadinessStatus.Ready,
                ReadinessFailureDetail: null,
                Page: new ArchiveSearchPage(
                    NormalizedQuery: query.NormalizedQuery,
                    Terms: query.Terms,
                    Source: query.Source,
                    Limit: query.Limit,
                    HasMore: hasMore,
                    NextCursor: nextCursor,
                    Items: cards)));
    }

    internal const string UnprojectedGuardSql = """
        SELECT EXISTS (
            SELECT 1
            FROM eledgercare.extraction_results er
            WHERE NOT EXISTS (
                SELECT 1
                FROM eledgercare.archive_result_projections arp
                WHERE arp.result_id = er.result_id
                  AND arp.projection_version = @projVer
            )
        )
        """;

    internal const string LoadReviewedUnitsSql = """
        SELECT rf.revision_id, rf.field_ordinal, rf.field_key, rf.human_value, rf.consulted_page_number
        FROM eledgercare.work_order_review_fields rf
        WHERE rf.revision_id = ANY(@revIds)
          AND rf.decision IN ('accepted', 'edited')
          AND rf.human_value IS NOT NULL
        ORDER BY rf.revision_id ASC, rf.field_ordinal ASC
        """;

    internal const string LoadMachineUnitsSql = """
        SELECT apu.document_id, apu.result_id, apu.unit_ordinal, apu.page_number, apu.is_fallback, apu.search_text
        FROM eledgercare.archive_projection_units apu
        WHERE apu.document_id = ANY(@docIds)
          AND apu.projection_version = @projVer
        ORDER BY apu.document_id ASC, apu.unit_ordinal ASC
        """;

    public static string BuildSearchCardHeadersSql(ParsedArchiveQuery query)
    {
        ArgumentNullException.ThrowIfNull(query);

        var sb = new StringBuilder(2048);
        sb.Append("""
            SELECT d.document_id,
                   d.submitted_at,
                   oa.page_count,
                   oa.byte_length,
                   oa.sha256,
                   pj.status,
                   er.result_id,
                   er.raw_output_sha256,
                   er.page_count AS extracted_page_count,
                   arp.projection_version,
                   arp.projection_sha256,
                   arp.has_fallback,
                   lr.revision_id,
                   lr.revision_number,
                   lr.saved_at,
                   lrf_wo.human_value AS reviewed_work_order_id,
                   lrf_prop.human_value AS reviewed_property_name,
                   rh.current_revision_number,
                   rh.current_status,
                   rh.updated_at
            FROM eledgercare.documents d
            JOIN eledgercare.original_artifacts oa ON oa.document_id = d.document_id
            JOIN eledgercare.processing_jobs pj ON pj.document_id = d.document_id
            LEFT JOIN eledgercare.extraction_results er ON er.document_id = d.document_id
            LEFT JOIN eledgercare.archive_result_projections arp
                   ON arp.result_id = er.result_id AND arp.projection_version = @projVer
            LEFT JOIN LATERAL (
                SELECT r.revision_id, r.revision_number, r.saved_at
                FROM eledgercare.work_order_review_revisions r
                WHERE r.document_id = d.document_id AND r.status = 'reviewed'
                ORDER BY r.revision_number DESC
                LIMIT 1
            ) lr ON TRUE
            LEFT JOIN eledgercare.work_order_review_fields lrf_wo
                   ON lrf_wo.revision_id = lr.revision_id
                  AND lrf_wo.field_key = 'work_order_id'
                  AND lrf_wo.decision IN ('accepted', 'edited')
            LEFT JOIN eledgercare.work_order_review_fields lrf_prop
                   ON lrf_prop.revision_id = lr.revision_id
                  AND lrf_prop.field_key = 'property_name'
                  AND lrf_prop.decision IN ('accepted', 'edited')
            LEFT JOIN eledgercare.work_order_review_heads rh ON rh.document_id = d.document_id
            WHERE TRUE
            """);

        if (query.After is not null)
        {
            sb.Append("\n  AND (d.submitted_at, d.document_id) < (@afterTs, @afterId)");
        }

        if (query.Terms.Count == 0)
        {
            switch (query.Source)
            {
                case ArchiveSourceFilter.Machine:
                    sb.Append("\n  AND er.result_id IS NOT NULL");
                    break;
                case ArchiveSourceFilter.Reviewed:
                    sb.Append("\n  AND lr.revision_id IS NOT NULL");
                    break;
                case ArchiveSourceFilter.All:
                    break;
            }
        }
        else
        {
            switch (query.Source)
            {
                case ArchiveSourceFilter.Machine:
                    sb.Append("\n  AND er.result_id IS NOT NULL");
                    for (var i = 0; i < query.Terms.Count; i++)
                    {
                        sb.Append($"""

                          AND EXISTS (
                              SELECT 1
                              FROM eledgercare.archive_projection_units apu
                              WHERE apu.document_id = d.document_id
                                AND apu.projection_version = @projVer
                                AND apu.search_text ILIKE @term{i} ESCAPE '\'
                          )
                        """);
                    }

                    break;

                case ArchiveSourceFilter.Reviewed:
                    sb.Append("\n  AND lr.revision_id IS NOT NULL");
                    for (var i = 0; i < query.Terms.Count; i++)
                    {
                        sb.Append($"""

                          AND EXISTS (
                              SELECT 1
                              FROM eledgercare.work_order_review_fields rf
                              WHERE rf.revision_id = lr.revision_id
                                AND rf.decision IN ('accepted', 'edited')
                                AND rf.human_value IS NOT NULL
                                AND rf.human_value ILIKE @term{i} ESCAPE '\'
                          )
                        """);
                    }

                    break;

                case ArchiveSourceFilter.All:
                    sb.Append("\n  AND (er.result_id IS NOT NULL OR lr.revision_id IS NOT NULL)");
                    for (var i = 0; i < query.Terms.Count; i++)
                    {
                        sb.Append($"""

                          AND (
                              EXISTS (
                                  SELECT 1
                                  FROM eledgercare.archive_projection_units apu
                                  WHERE apu.document_id = d.document_id
                                    AND apu.projection_version = @projVer
                                    AND apu.search_text ILIKE @term{i} ESCAPE '\'
                              )
                              OR (
                                  lr.revision_id IS NOT NULL
                                  AND EXISTS (
                                      SELECT 1
                                      FROM eledgercare.work_order_review_fields rf
                                      WHERE rf.revision_id = lr.revision_id
                                        AND rf.decision IN ('accepted', 'edited')
                                        AND rf.human_value IS NOT NULL
                                        AND rf.human_value ILIKE @term{i} ESCAPE '\'
                                  )
                              )
                          )
                        """);
                    }

                    break;
            }
        }

        sb.Append("\nORDER BY d.submitted_at DESC, d.document_id DESC");
        sb.Append("\nLIMIT @limitPlusOne");
        return sb.ToString();
    }

    public static void BindSearchParameters(NpgsqlCommand cmd, ParsedArchiveQuery query)
    {
        cmd.Parameters.AddWithValue("projVer", ArchiveSchema.ProjectionVersion);
        cmd.Parameters.AddWithValue("limitPlusOne", query.Limit + 1);

        if (query.After is { } after)
        {
            cmd.Parameters.AddWithValue("afterTs", after.SubmittedAtUtc);
            cmd.Parameters.AddWithValue("afterId", after.DocumentId);
        }

        for (var i = 0; i < query.Terms.Count; i++)
        {
            var pattern = ArchiveQueryValidator.EscapePostgresLikeSubstringPattern(query.Terms[i]);
            cmd.Parameters.AddWithValue($"term{i}", pattern);
        }
    }

    private static async Task LoadReviewedUnitsForPageAsync(
        NpgsqlConnection conn,
        NpgsqlTransaction tx,
        IReadOnlyList<CardHeaderRow> pageRows,
        Dictionary<Guid, List<CandidateArchiveUnit>> unitsByDocument,
        CancellationToken cancellationToken)
    {
        var revToDoc = new Dictionary<Guid, (Guid DocumentId, int RevisionNumber)>(pageRows.Count);
        var revIds = new List<Guid>(pageRows.Count);
        for (var i = 0; i < pageRows.Count; i++)
        {
            if (pageRows[i].LatestReviewedRevisionId is Guid revId &&
                pageRows[i].LatestReviewedRevisionNumber is int revNum)
            {
                revIds.Add(revId);
                revToDoc[revId] = (pageRows[i].DocumentId, revNum);
            }
        }

        if (revIds.Count == 0)
        {
            return;
        }

        await using var cmd = new NpgsqlCommand(LoadReviewedUnitsSql, conn, tx);
        cmd.Parameters.AddWithValue("revIds", revIds.ToArray());

        await using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            var revId = reader.GetGuid(0);
            var fieldKey = reader.GetString(2);
            var humanValue = reader.GetString(3);
            int? consultedPage = reader.IsDBNull(4) ? null : reader.GetInt32(4);

            var (docId, revNum) = revToDoc[revId];
            var fieldLabel = WorkOrderReviewSchema.TryGetField(fieldKey, out var def)
                ? def!.DisplayLabel
                : fieldKey;

            unitsByDocument[docId].Add(new CandidateArchiveUnit(
                SourceKind: "reviewed",
                Text: humanValue,
                ResultId: null,
                PageNumber: null,
                IsFallback: false,
                RevisionNumber: revNum,
                FieldKey: fieldKey,
                FieldLabel: fieldLabel,
                ConsultedPageNumber: consultedPage));
        }
    }

    private static async Task LoadMachineUnitsForPageAsync(
        NpgsqlConnection conn,
        NpgsqlTransaction tx,
        IReadOnlyList<CardHeaderRow> pageRows,
        Dictionary<Guid, List<CandidateArchiveUnit>> unitsByDocument,
        CancellationToken cancellationToken)
    {
        var docIds = new List<Guid>(pageRows.Count);
        for (var i = 0; i < pageRows.Count; i++)
        {
            if (pageRows[i].ResultId is not null)
            {
                docIds.Add(pageRows[i].DocumentId);
            }
        }

        if (docIds.Count == 0)
        {
            return;
        }

        await using var cmd = new NpgsqlCommand(LoadMachineUnitsSql, conn, tx);
        cmd.Parameters.AddWithValue("docIds", docIds.ToArray());
        cmd.Parameters.AddWithValue("projVer", ArchiveSchema.ProjectionVersion);

        await using var reader = await cmd.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            var docId = reader.GetGuid(0);
            var resultId = reader.GetGuid(1);
            int? pageNumber = reader.IsDBNull(3) ? null : reader.GetInt32(3);
            var isFallback = reader.GetBoolean(4);
            var searchText = reader.GetString(5);

            unitsByDocument[docId].Add(new CandidateArchiveUnit(
                SourceKind: "machine",
                Text: searchText,
                ResultId: resultId,
                PageNumber: pageNumber,
                IsFallback: isFallback,
                RevisionNumber: null,
                FieldKey: null,
                FieldLabel: null,
                ConsultedPageNumber: null));
        }
    }

    private sealed record CardHeaderRow(
        Guid DocumentId,
        DateTimeOffset SubmittedAtUtc,
        int AdmittedPageCount,
        int OriginalByteLength,
        byte[] OriginalSha256,
        ProcessingStatus JobStatus,
        Guid? ResultId,
        byte[]? RawOutputSha256,
        int? ExtractedPageCount,
        string? ProjectionVersion,
        byte[]? ProjectionSha256,
        bool? ProjectionHasFallback,
        Guid? LatestReviewedRevisionId,
        int? LatestReviewedRevisionNumber,
        DateTimeOffset? LatestReviewedSavedAtUtc,
        string? LatestReviewedWorkOrderId,
        string? LatestReviewedPropertyName,
        int? HeadRevisionNumber,
        ReviewRevisionStatus? HeadStatus,
        DateTimeOffset? HeadUpdatedAtUtc);
}
