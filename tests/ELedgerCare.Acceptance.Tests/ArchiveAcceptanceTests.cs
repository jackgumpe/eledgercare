using System.Diagnostics;
using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using ELedgerCare.Acceptance.Tests.Harness;
using ELedgerCare.Application.Archive;
using ELedgerCare.Application.Extraction;
using ELedgerCare.Application.Intake;
using ELedgerCare.Domain.Archive;
using ELedgerCare.Domain.Documents;
using ELedgerCare.Domain.Processing;
using ELedgerCare.Domain.Review;
using ELedgerCare.Infrastructure.Persistence;
using ELedgerCare.Tests.Shared;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;
using Microsoft.Extensions.Logging.Abstractions;
using Npgsql;
using Xunit;

namespace ELedgerCare.Acceptance.Tests;

/// <summary>
/// WP-0010 F4 real PostgreSQL 18.7 and real ELedgerCare.Api HTTP acceptance tests covering F4-01..05,
/// F4-BIC-01..06, and F4-BIC-08 with LocalOcr:Enabled=false and zero GPU/model calls.
/// </summary>
[Collection(PostgresCollection.Name)]
public sealed class ArchiveAcceptanceTests(PostgresFixture fixture)
{
    private static CancellationToken Cancel => TestContext.Current.CancellationToken;

    private static byte[] FixturePdf => File.ReadAllBytes(
        Path.Combine(RepositoryPaths.Root, "tests", "fixtures", "F1-SWO-001.pdf"));

    [Fact]
    public async Task F4_01_and_03_browse_source_filters_and_literal_machine_search_on_genuine_F2_seeds()
    {
        await using var db = await fixture.CreateDatabaseAsync();

        var wo = await GenuineF2Seeds.SeedSynWo01Async(db.AppConnectionString, remapIds: false, Cancel);
        var mp = await GenuineF2Seeds.SeedSynMp01Async(db.AppConnectionString, remapIds: false, Cancel);

        await using var api = await ApiProcess.StartAsync(db.AppConnectionString);
        using var client = api.CreateClient();

        // Submit an unprocessed awaiting_extraction document and a failed document with diagnostics.
        var pendingDocId = await SubmitPdfAsync(client, FixturePdf);
        var failedDocId = await SubmitPdfAsync(client, FixturePdf);
        await MarkJobFailedWithDiagnosticsAsync(
            db.AppConnectionString,
            failedDocId,
            diagnosticPartial: "DIAGNOSTIC-ONLY-TOKEN-719",
            failureDetail: "FAILURE-DETAIL-ONLY-719");

        // 1. Empty browse across all / machine / reviewed filters
        var browseAll = await GetArchiveOkAsync(client, "/api/archive");
        Assert.Equal(4, browseAll.GetProperty("items").GetArrayLength());
        Assert.False(browseAll.GetProperty("hasMore").GetBoolean());

        var statusesById = browseAll.GetProperty("items")
            .EnumerateArray()
            .ToDictionary(x => Guid.Parse(x.GetProperty("documentId").GetString()!), x => x.GetProperty("status").GetString()!);
        Assert.Equal("completed", statusesById[wo.DocumentId]);
        Assert.Equal("completed", statusesById[mp.DocumentId]);
        Assert.Equal("awaiting_extraction", statusesById[pendingDocId]);
        Assert.Equal("failed", statusesById[failedDocId]);

        var browseMachine = await GetArchiveOkAsync(client, "/api/archive?source=machine");
        Assert.Equal(2, browseMachine.GetProperty("items").GetArrayLength());

        var browseReviewed = await GetArchiveOkAsync(client, "/api/archive?source=reviewed");
        Assert.Equal(0, browseReviewed.GetProperty("items").GetArrayLength());

        // 2. Diagnostics and failure details are never searchable
        foreach (var nonSearchToken in new[] { "DIAGNOSTIC-ONLY-TOKEN-719", "FAILURE-DETAIL-ONLY-719", wo.DocumentId.ToString("D") })
        {
            var diagRes = await GetArchiveOkAsync(client, $"/api/archive?q={Uri.EscapeDataString(nonSearchToken)}");
            Assert.Equal(0, diagRes.GetProperty("items").GetArrayLength());
        }

        // 3. Machine text and spanning table cells are found with exact physical page coordinates
        var mpPage3Hit = await GetArchiveOkAsync(client, "/api/archive?q=%241%2C535.35");
        Assert.Single(mpPage3Hit.GetProperty("items").EnumerateArray());
        var mpCard = mpPage3Hit.GetProperty("items")[0];
        Assert.Equal(mp.DocumentId.ToString("D"), mpCard.GetProperty("documentId").GetString());
        Assert.Equal(["machine"], mpCard.GetProperty("contributingSources").EnumerateArray().Select(e => e.GetString()).ToArray());
        var mpWitness = mpCard.GetProperty("witnesses")[0];
        Assert.Equal("machine", mpWitness.GetProperty("sourceKind").GetString());
        Assert.Equal("Machine extraction — unreviewed", mpWitness.GetProperty("sourceLabel").GetString());
        Assert.Equal(3, mpWitness.GetProperty("pageNumber").GetInt32());

        // 4. Multi-page AND within one document succeeds (order-independent); cross-document AND returns empty
        var multiPageAnd = await GetArchiveOkAsync(client, "/api/archive?q=MP01-P3+MP01-P1");
        Assert.Single(multiPageAnd.GetProperty("items").EnumerateArray());
        var mpAndWitnesses = multiPageAnd.GetProperty("items")[0].GetProperty("witnesses").EnumerateArray().ToArray();
        Assert.Equal(2, mpAndWitnesses.Length);
        Assert.Equal([3, 1], mpAndWitnesses.Select(w => w.GetProperty("pageNumber").GetInt32()).ToArray());

        var crossDocAnd = await GetArchiveOkAsync(client, "/api/archive?q=WO-004192+MP01-P2");
        Assert.Equal(0, crossDocAnd.GetProperty("items").GetArrayLength());

        // 5. Nonexistent term produces honest empty result
        var missingRes = await GetArchiveOkAsync(client, "/api/archive?q=NONEXISTENT-MAINT-TOKEN-99999");
        Assert.Equal(0, missingRes.GetProperty("items").GetArrayLength());
        Assert.False(missingRes.GetProperty("hasMore").GetBoolean());
        Assert.Equal(JsonValueKind.Null, missingRes.GetProperty("nextCursor").ValueKind);
    }

    [Fact]
    public async Task F4_02_and_03_revision_lifecycle_unknown_removal_newer_draft_isolation_cross_source_AND_collation_and_validation()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        var wo = await GenuineF2Seeds.SeedSynWo01Async(db.AppConnectionString, remapIds: false, Cancel);

        await using var api = await ApiProcess.StartAsync(db.AppConnectionString);
        using var client = api.CreateClient();

        const string woIssueSuggested =
            "Air handler fan running continuously with warm supply air at 79 F setpoint. Inspected condensing unit CHP-B204: " +
            "dual run capacitor measured 18.2 uF on 45 uF herm leg and contactor points pitted. Replaced capacitor and 2-pole " +
            "contactor from van stock; verified 19.4 F delta-T across evaporator coil.";

        // 1. Save Revision #1 (reviewed) with metacharacters %, _, \, non-ASCII Café, emoji 🔧, and operator label.
        await SaveReviewRevisionAsync(
            client,
            wo.DocumentId,
            wo.ResultId,
            expectedRevision: 0,
            status: "reviewed",
            operatorLabel: "OPERATOR-NONSEARCH-555",
            fields:
            [
                new { fieldKey = "work_order_id", decision = "edited", value = "WO-REV1-OLD-777" },
                new { fieldKey = "property_name", decision = "edited", value = @"Cedar_100% \ [Café] 🔧" },
                new { fieldKey = "building_unit", decision = "accepted", value = "Bldg B - Unit 204" },
                new { fieldKey = "requested_date", decision = "accepted", value = "2026-10-16" },
                new { fieldKey = "issue_and_resolution", decision = "accepted", value = woIssueSuggested },
            ]);

        // Immediately searchable in reviewed & all
        var rev1Hit = await GetArchiveOkAsync(client, "/api/archive?q=wo-rev1-old-777&source=reviewed");
        Assert.Single(rev1Hit.GetProperty("items").EnumerateArray());
        Assert.Contains("WO-REV1-OLD-777", rev1Hit.GetProperty("items")[0].GetProperty("displayTitle").GetString(), StringComparison.Ordinal);

        // Literal %, _, \, Café, and 🔧 match; C-locale case-sensitivity on non-ASCII 'É' vs 'é' pinned!
        var metaHit = await GetArchiveOkAsync(client, $"/api/archive?q={Uri.EscapeDataString(@"cedar_100% \ [Café] 🔧")}&source=reviewed");
        Assert.Single(metaHit.GetProperty("items").EnumerateArray());

        var nonAsciiUpperMiss = await GetArchiveOkAsync(client, $"/api/archive?q={Uri.EscapeDataString("CAFÉ")}&source=reviewed");
        Assert.Equal(0, nonAsciiUpperMiss.GetProperty("items").GetArrayLength());

        // Prove '%' and '_' are not wildcards: 'Cedar%999' and 'OPERATOR-NONSEARCH-555' return 0
        var wildcardProbe = await GetArchiveOkAsync(client, $"/api/archive?q={Uri.EscapeDataString("Cedar%[Café]")}&source=reviewed");
        Assert.Equal(0, wildcardProbe.GetProperty("items").GetArrayLength());

        var opLabelProbe = await GetArchiveOkAsync(client, "/api/archive?q=OPERATOR-NONSEARCH-555");
        Assert.Equal(0, opLabelProbe.GetProperty("items").GetArrayLength());

        // 2. Save Revision #2 (reviewed): supersede work_order_id, mark building_unit unknown + reason,
        // and edit issue_and_resolution manually without source coordinates!
        await SaveReviewRevisionAsync(
            client,
            wo.DocumentId,
            wo.ResultId,
            expectedRevision: 1,
            status: "reviewed",
            operatorLabel: "Operator Two",
            fields:
            [
                new { fieldKey = "work_order_id", decision = "edited", value = "WO-REV2-ACTIVE-888" },
                new { fieldKey = "property_name", decision = "accepted", value = "Cedar Hollow Apartments" },
                new { fieldKey = "building_unit", decision = "unknown", unknownReason = "UNKNOWN-REASON-NONSEARCH-444" },
                new { fieldKey = "requested_date", decision = "accepted", value = "2026-10-16" },
                new { fieldKey = "issue_and_resolution", decision = "edited", value = "Manual boiler inspection KESTREL-0042 <script>alert('x')</script>" },
            ]);

        // Superseded reviewed value and unknown-cleared unit are removed from reviewed search!
        var oldRev1Miss = await GetArchiveOkAsync(client, "/api/archive?q=WO-REV1-OLD-777");
        Assert.Equal(0, oldRev1Miss.GetProperty("items").GetArrayLength());

        var unitReviewedMiss = await GetArchiveOkAsync(client, $"/api/archive?q={Uri.EscapeDataString("Unit 204")}&source=reviewed");
        Assert.Equal(0, unitReviewedMiss.GetProperty("items").GetArrayLength());

        var unknownReasonMiss = await GetArchiveOkAsync(client, "/api/archive?q=UNKNOWN-REASON-NONSEARCH-444");
        Assert.Equal(0, unknownReasonMiss.GetProperty("items").GetArrayLength());

        // Original machine value "Unit 204" remains searchable in source=all and source=machine, labelled Machine!
        var unitMachineHit = await GetArchiveOkAsync(client, $"/api/archive?q={Uri.EscapeDataString("Unit 204")}&source=all");
        Assert.Single(unitMachineHit.GetProperty("items").EnumerateArray());
        Assert.Equal(["machine"], unitMachineHit.GetProperty("items")[0].GetProperty("contributingSources").EnumerateArray().Select(e => e.GetString()).ToArray());
        Assert.Equal("Machine extraction — unreviewed", unitMachineHit.GetProperty("items")[0].GetProperty("witnesses")[0].GetProperty("sourceLabel").GetString());

        // Cross-source AND under source=all: KESTREL-0042 (only in reviewed Rev #2, null provenance) + 0018-TERM-QC (only in machine Page 1)
        var crossSourceHit = await GetArchiveOkAsync(client, "/api/archive?q=KESTREL-0042+0018-TERM-QC&source=all");
        Assert.Single(crossSourceHit.GetProperty("items").EnumerateArray());
        var csItem = crossSourceHit.GetProperty("items")[0];
        Assert.Equal(["reviewed", "machine"], csItem.GetProperty("contributingSources").EnumerateArray().Select(e => e.GetString()).ToArray());
        var csWitnesses = csItem.GetProperty("witnesses").EnumerateArray().ToArray();
        Assert.Equal(2, csWitnesses.Length);
        Assert.Equal("reviewed", csWitnesses[0].GetProperty("sourceKind").GetString());
        Assert.Equal(2, csWitnesses[0].GetProperty("revisionNumber").GetInt32());
        Assert.Equal(JsonValueKind.Null, csWitnesses[0].GetProperty("consultedPageNumber").ValueKind);
        Assert.Equal("machine", csWitnesses[1].GetProperty("sourceKind").GetString());
        Assert.Equal(1, csWitnesses[1].GetProperty("pageNumber").GetInt32());

        Assert.Equal(0, (await GetArchiveOkAsync(client, "/api/archive?q=KESTREL-0042+0018-TERM-QC&source=reviewed")).GetProperty("items").GetArrayLength());
        Assert.Equal(0, (await GetArchiveOkAsync(client, "/api/archive?q=KESTREL-0042+0018-TERM-QC&source=machine")).GetProperty("items").GetArrayLength());

        // 3. Save Revision #3 (draft): newer draft is NOT searched as reviewed, card reports hasNewerDraft=true,
        // and pinned historical link /review/revisions/2 resolves immutable Revision #2!
        await SaveReviewRevisionAsync(
            client,
            wo.DocumentId,
            wo.ResultId,
            expectedRevision: 2,
            status: "draft",
            operatorLabel: "Draft Author",
            fields:
            [
                new { fieldKey = "work_order_id", decision = "edited", value = "DRAFT-ONLY-UNAPPROVED-999" },
                new { fieldKey = "property_name", decision = "unreviewed" },
                new { fieldKey = "building_unit", decision = "unreviewed" },
                new { fieldKey = "requested_date", decision = "unreviewed" },
                new { fieldKey = "issue_and_resolution", decision = "unreviewed" },
            ]);

        var draftMiss = await GetArchiveOkAsync(client, "/api/archive?q=DRAFT-ONLY-UNAPPROVED-999");
        Assert.Equal(0, draftMiss.GetProperty("items").GetArrayLength());

        var rev2StillActive = await GetArchiveOkAsync(client, "/api/archive?q=WO-REV2-ACTIVE-888&source=reviewed");
        Assert.Single(rev2StillActive.GetProperty("items").EnumerateArray());
        var activeCard = rev2StillActive.GetProperty("items")[0];
        Assert.True(activeCard.GetProperty("hasNewerDraft").GetBoolean());
        Assert.Equal(2, activeCard.GetProperty("latestReviewed").GetProperty("revisionNumber").GetInt32());
        Assert.Equal(3, activeCard.GetProperty("currentReviewHead").GetProperty("currentRevisionNumber").GetInt32());
        Assert.Equal("draft", activeCard.GetProperty("currentReviewHead").GetProperty("currentStatus").GetString());

        using var pinnedRev2Resp = await client.GetAsync($"/api/documents/{wo.DocumentId:D}/review/revisions/2", Cancel);
        Assert.Equal(HttpStatusCode.OK, pinnedRev2Resp.StatusCode);
        var pinnedRev2Json = await pinnedRev2Resp.Content.ReadFromJsonAsync<JsonElement>(Cancel);
        Assert.False(pinnedRev2Json.GetProperty("isCurrentHead").GetBoolean());
        Assert.Equal(2, pinnedRev2Json.GetProperty("revision").GetProperty("revisionNumber").GetInt32());

        // 4. HTTP 400 validation bounds on live endpoint
        foreach (var badUrl in new[]
                 {
                     "/api/archive?q=%FF",
                     "/api/archive?foo=1",
                     "/api/archive?q=a&q=b",
                     "/api/archive?source=bogus",
                     "/api/archive?limit=0",
                     "/api/archive?limit=51",
                     "/api/archive?limit=05",
                     "/api/archive?after=invalid!",
                 })
        {
            using var badResp = await client.GetAsync(badUrl, Cancel);
            Assert.Equal(HttpStatusCode.BadRequest, badResp.StatusCode);
        }
    }

    [Fact]
    public async Task F4_04_and_BIC04_keyset_pagination_tie_breaking_cursor_mismatch_and_repeatable_read_snapshot()
    {
        await using var db = await fixture.CreateDatabaseAsync();

        // Insert 5 documents including 2 sharing the exact same microsecond submitted_at timestamp!
        var sharedTs = new DateTimeOffset(2026, 11, 17, 7, 15, 0, TimeSpan.Zero).AddTicks(123450); // .012345s
        var docIds = new[]
        {
            Guid.Parse("01a1f410-0000-7000-8000-000000000001"),
            Guid.Parse("01a1f410-0000-7000-8000-000000000002"),
            Guid.Parse("01a1f410-0000-7000-8000-000000000003"),
            Guid.Parse("01a1f410-0000-7000-8000-000000000004"),
            Guid.Parse("01a1f410-0000-7000-8000-000000000005"),
        };
        var timestamps = new[]
        {
            sharedTs.AddMinutes(-2),
            sharedTs,
            sharedTs, // Exact microsecond tie with docIds[1]; broken deterministically by document_id DESC!
            sharedTs.AddMinutes(1),
            sharedTs.AddMinutes(2),
        };

        var pdfBytes = FixturePdf;
        var pdfSha = SHA256.HashData(pdfBytes);
        await using (var appConn = await db.OpenAppAsync())
        {
            for (var i = 0; i < docIds.Length; i++)
            {
                await InsertAwaitingDocumentAtTimestampAsync(appConn, docIds[i], timestamps[i], pdfBytes, pdfSha);
            }
        }

        await using var api = await ApiProcess.StartAsync(db.AppConnectionString);
        using var client = api.CreateClient();

        var seenIds = new List<Guid>();
        string? after = null;
        var pageCount = 0;
        while (true)
        {
            var url = after is null ? "/api/archive?limit=2" : $"/api/archive?limit=2&after={Uri.EscapeDataString(after)}";
            var pageJson = await GetArchiveOkAsync(client, url);
            pageCount++;
            foreach (var item in pageJson.GetProperty("items").EnumerateArray())
            {
                seenIds.Add(Guid.Parse(item.GetProperty("documentId").GetString()!));
            }

            if (!pageJson.GetProperty("hasMore").GetBoolean())
            {
                Assert.Equal(JsonValueKind.Null, pageJson.GetProperty("nextCursor").ValueKind);
                break;
            }

            after = pageJson.GetProperty("nextCursor").GetString();
            Assert.False(string.IsNullOrEmpty(after));

            // Verify reusing this browse cursor with a modified query or source returns 400!
            using var mismatchQ = await client.GetAsync($"/api/archive?q=changed&limit=2&after={Uri.EscapeDataString(after!)}", Cancel);
            Assert.Equal(HttpStatusCode.BadRequest, mismatchQ.StatusCode);
            using var mismatchS = await client.GetAsync($"/api/archive?source=machine&limit=2&after={Uri.EscapeDataString(after!)}", Cancel);
            Assert.Equal(HttpStatusCode.BadRequest, mismatchS.StatusCode);
        }

        Assert.Equal(3, pageCount);
        Assert.Equal(
            [docIds[4], docIds[3], docIds[2], docIds[1], docIds[0]],
            seenIds);

        // Verify REPEATABLE READ READ ONLY snapshot isolation on PostgreSQL:
        // Pin a REPEATABLE READ READ ONLY transaction before inserting a 6th document on a separate connection;
        // the pinned snapshot sees 5 documents, while a new ArchiveStore search immediately sees 6!
        await using var pinnedConn = await db.OpenAppAsync();
        await using var pinnedTx = await pinnedConn.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead, Cancel);
        await using (var setRo = new NpgsqlCommand("SET TRANSACTION READ ONLY", pinnedConn, pinnedTx))
        {
            await setRo.ExecuteNonQueryAsync(Cancel);
        }

        await using (var firstRead = new NpgsqlCommand("SELECT count(*) FROM eledgercare.documents", pinnedConn, pinnedTx))
        {
            Assert.Equal(5L, (long)(await firstRead.ExecuteScalarAsync(Cancel))!);
        }

        var sixthDocId = await SubmitPdfAsync(client, pdfBytes);

        await using (var secondReadSameSnapshot = new NpgsqlCommand("SELECT count(*) FROM eledgercare.documents", pinnedConn, pinnedTx))
        {
            Assert.Equal(5L, (long)(await secondReadSameSnapshot.ExecuteScalarAsync(Cancel))!);
        }

        await pinnedTx.CommitAsync(Cancel);

        var freshBrowse = await GetArchiveOkAsync(client, "/api/archive?limit=20");
        Assert.Equal(6, freshBrowse.GetProperty("items").GetArrayLength());
        Assert.Equal(sixthDocId.ToString("D"), freshBrowse.GetProperty("items")[0].GetProperty("documentId").GetString());
    }

    [Fact]
    public async Task F4_05_and_BIC05_forward_migration_interrupted_backfill_competing_initializers_fenced_publish_and_conflict_503()
    {
        // 1. Real forward migration from 3-migration F3 schema (20261116200918_AddWorkOrderReview) -> AddSourceLinkedArchive
        var dbName = $"eledgercare_f4_fwd_{Guid.NewGuid().ToString("N")[..10]}";
        await using var admin = await PostgresFixture.OpenAsync(fixture.Settings.Admin());
        await PostgresFixture.ExecuteAsync(admin, $"CREATE DATABASE {dbName} OWNER {fixture.Settings.MigratorUser} ENCODING 'UTF8' TEMPLATE template0");
        await PostgresFixture.ExecuteAsync(admin, $"REVOKE ALL ON DATABASE {dbName} FROM PUBLIC");
        await PostgresFixture.ExecuteAsync(admin, $"GRANT CONNECT ON DATABASE {dbName} TO {fixture.Settings.AppUser}");

        try
        {
            await using (var dbAdmin = await PostgresFixture.OpenAsync(fixture.Settings.Admin(dbName)))
            {
                await PostgresFixture.ExecuteAsync(dbAdmin, "REVOKE ALL ON SCHEMA public FROM PUBLIC");
            }

            var migConnStr = fixture.Settings.Migrator(dbName);
            var appConnStr = fixture.Settings.App(dbName);
            var migOptions = new DbContextOptionsBuilder<ELedgerCareDbContext>()
                .UseNpgsql(migConnStr, npgsql =>
                    npgsql.MigrationsHistoryTable("__ef_migrations_history", ELedgerCareDbContext.Schema))
                .Options;

            // Apply only up to F3 (20261116200918_AddWorkOrderReview) and grant F1-F3 runtime privileges!
            await using (var preF4Db = new ELedgerCareDbContext(migOptions))
            {
                await preF4Db.GetService<IMigrator>().MigrateAsync("20261116200918_AddWorkOrderReview", Cancel);
            }

            await ApplyF3OnlyRuntimeGrantsAsync(migConnStr);

            // Seed 3 genuine pre-F4 completed extraction results while archive tables do not exist yet!
            var preWo1 = await GenuineF2Seeds.SeedSynWo01Async(appConnStr, remapIds: false, Cancel);
            var preMp1 = await GenuineF2Seeds.SeedSynMp01Async(appConnStr, remapIds: false, Cancel);
            var preWo2 = await GenuineF2Seeds.SeedSynWo01Async(appConnStr, remapIds: true, Cancel);

            // Now apply forward F4 migration (AddSourceLinkedArchive) and full grant-runtime.sql!
            await using (var f4MigDb = new ELedgerCareDbContext(migOptions))
            {
                await f4MigDb.Database.MigrateAsync(Cancel);
            }

            var grantSql = await File.ReadAllTextAsync(
                Path.Combine(RepositoryPaths.Root, "deploy", "dev", "database", "grant-runtime.sql"), Cancel);
            await using (var migConn = await PostgresFixture.OpenAsync(migConnStr))
            {
                await PostgresFixture.ExecuteAsync(migConn, grantSql);
            }

            var runtimeFactory = new PooledDbContextFactory<ELedgerCareDbContext>(
                new DbContextOptionsBuilder<ELedgerCareDbContext>()
                    .UseNpgsql(appConnStr)
                    .Options);

            // 2. Interrupted backfill (BatchSize=1, maxNewProjections=1): commits 1, leaves 2 unprojected;
            // with AutoCatchUpOnSearch=false, ArchiveStore refuses partial 200 OK and returns Initializing (503)!
            using (var partialInit = new ArchiveProjectionInitializer(
                runtimeFactory,
                appConnStr,
                new ArchiveBackfillOptions { BatchSize = 1, AutoCatchUpOnSearch = false },
                TimeProvider.System,
                NullLogger<ArchiveProjectionInitializer>.Instance))
            {
                var partialReceipt = await partialInit.RunBoundedPassAsync(maxNewProjections: 1, cancellationToken: Cancel);
                Assert.True(partialReceipt.StoppedAtLimit);
                Assert.Equal(1, partialReceipt.NewlyProjectedCount);
                Assert.Equal(ArchiveReadinessStatus.Initializing, partialReceipt.Status);

                var noCatchupStore = new ArchiveStore(appConnStr, partialInit);
                var parsedAll = new ParsedArchiveQuery(string.Empty, [], ArchiveSourceFilter.All, 20, After: null);
                var blockedOutcome = await noCatchupStore.SearchAsync(parsedAll, Cancel);
                Assert.Equal(ArchiveReadinessStatus.Initializing, blockedOutcome.Readiness);
                Assert.Null(blockedOutcome.Page);
            }

            // 3. Two competing initializers race simultaneously on the remaining 2 unprojected results!
            // Barrier ensures both initializers enter CommitOrReconcileSingleProjectionAsync concurrently on the next result_id.
            var firstRaceTargetEntered = 0;
            var bothEnteredBarrier = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);

            async Task SyncHook(Guid _, CancellationToken ct)
            {
                var count = Interlocked.Increment(ref firstRaceTargetEntered);
                if (count == 2)
                {
                    bothEnteredBarrier.TrySetResult();
                }

                if (count <= 2)
                {
                    await bothEnteredBarrier.Task.WaitAsync(TimeSpan.FromSeconds(10), ct);
                }
            }

            using var initA = new ArchiveProjectionInitializer(
                runtimeFactory,
                appConnStr,
                new ArchiveBackfillOptions { BatchSize = 1 },
                TimeProvider.System,
                NullLogger<ArchiveProjectionInitializer>.Instance);
            using var initB = new ArchiveProjectionInitializer(
                runtimeFactory,
                appConnStr,
                new ArchiveBackfillOptions { BatchSize = 1 },
                TimeProvider.System,
                NullLogger<ArchiveProjectionInitializer>.Instance);

            var raceResults = await Task.WhenAll(
                initA.RunBoundedPassAsync(beforeCommitHook: SyncHook, cancellationToken: Cancel),
                initB.RunBoundedPassAsync(beforeCommitHook: SyncHook, cancellationToken: Cancel));

            Assert.All(raceResults, r => Assert.Equal(ArchiveReadinessStatus.Ready, r.Status));
            Assert.Equal(2, raceResults.Sum(r => r.NewlyProjectedCount));
            Assert.True(raceResults.Sum(r => r.ReconciledConcurrentCount) >= 1);

            // 4. Live PublishCompletedResultAsync atomic publish, stale fencing rejection, and rollback atomicity!
            var extractionStore = new ExtractionStore(runtimeFactory);
            var intakeStore = new IntakeStore(runtimeFactory);

            var liveDocId = Guid.NewGuid();
            var liveJobId = Guid.NewGuid();
            var pdfBytes = File.ReadAllBytes(Path.Combine(RepositoryPaths.Root, "tests", "fixtures", "SYN-WO-01-v1-raster300.pdf"));
            var pdfSha = SHA256.HashData(pdfBytes);
            var doc = Document.Submit(liveDocId, liveJobId, Guid.NewGuid(), pdfBytes, 1, DateTimeOffset.UtcNow);
            Assert.Equal(InsertResult.Committed, await intakeStore.InsertAsync(doc, Cancel));

            var queuedOutcome = await extractionStore.QueueOrReconcileAsync(liveDocId, null, 3, workerEnabled: true, DateTimeOffset.UtcNow, Cancel);
            Assert.IsType<QueueExtractionOutcome.QueuedOrActive>(queuedOutcome);
            var leased = await extractionStore.ClaimNextQueuedJobAsync(
                Guid.NewGuid(), 1234, 999999L, DateTimeOffset.UtcNow, Cancel);
            Assert.NotNull(leased);

            var rawLiveBytes = Encoding.UTF8.GetBytes("<PAGE>\n<BLOCK>text[1,1,10,10]<FORK>LIVE-PUBLISHED-ATOMIC-TOKEN-314\n");
            var dummyDigest = SHA256.HashData("pin"u8);

            // Stale fencing token (FencingToken + 999) must fail and commit zero result or projection rows!
            var staleResult = ExtractionResult.Create(
                Guid.NewGuid(), liveDocId, liveJobId, leased.AttemptId,
                fencingToken: leased.FencingToken + 999,
                pdfSha, pdfBytes.Length, 1,
                rawLiveBytes, SHA256.HashData(rawLiveBytes),
                "baidu/Unlimited-OCR-2", "0480966938291445591f69f08a13b041c073a96a",
                dummyDigest, dummyDigest, dummyDigest, dummyDigest,
                "pypdfium2", "{}", "stop", 1,
                DateTimeOffset.UtcNow.AddSeconds(-1), DateTimeOffset.UtcNow,
                10, 10, 10, 30, "{}");

            Assert.False(await extractionStore.PublishCompletedResultAsync(staleResult, 0, DateTimeOffset.UtcNow, Cancel));

            // Valid fencing token publishes BOTH extraction_results AND archive_result_projections atomically!
            var validResult = ExtractionResult.Create(
                Guid.NewGuid(), liveDocId, liveJobId, leased.AttemptId,
                fencingToken: leased.FencingToken,
                pdfSha, pdfBytes.Length, 1,
                rawLiveBytes, SHA256.HashData(rawLiveBytes),
                "baidu/Unlimited-OCR-2", "0480966938291445591f69f08a13b041c073a96a",
                dummyDigest, dummyDigest, dummyDigest, dummyDigest,
                "pypdfium2", "{}", "stop", 1,
                DateTimeOffset.UtcNow.AddSeconds(-1), DateTimeOffset.UtcNow,
                10, 10, 10, 30, "{}");

            Assert.True(await extractionStore.PublishCompletedResultAsync(validResult, 0, DateTimeOffset.UtcNow, Cancel));

            await using (var apiReady = await ApiProcess.StartAsync(appConnStr))
            {
                using var clientReady = apiReady.CreateClient();
                var liveHit = await GetArchiveOkAsync(clientReady, "/api/archive?q=LIVE-PUBLISHED-ATOMIC-TOKEN-314&source=machine");
                Assert.Single(liveHit.GetProperty("items").EnumerateArray());
                Assert.Equal(liveDocId.ToString("D"), liveHit.GetProperty("items")[0].GetProperty("documentId").GetString());
            }

            // 5. Deferred startup initialization serves 503 archive_not_ready while listening!
            await using (var apiDeferred = await ApiProcess.StartAsync(appConnStr, new Dictionary<string, string>
            {
                ["Archive__DeferStartupInitialization"] = "true",
            }))
            {
                using var clientDef = apiDeferred.CreateClient();
                using var notReadyResp = await clientDef.GetAsync("/api/archive", Cancel);
                Assert.Equal(HttpStatusCode.ServiceUnavailable, notReadyResp.StatusCode);
                var problem = await notReadyResp.Content.ReadFromJsonAsync<JsonElement>(Cancel);
                Assert.Equal("archive_not_ready", problem.GetProperty("code").GetString());
            }

            // 6. Conflicting projection digest detected at startup serves 503 archive_projection_conflict without mutating data!
            await using (var dbAdmin = await PostgresFixture.OpenAsync(fixture.Settings.Admin(dbName)))
            {
                await using var tamperCmd = new NpgsqlCommand(
                    "UPDATE eledgercare.archive_result_projections SET projection_sha256 = decode(repeat('ff', 32), 'hex') WHERE result_id = @id",
                    dbAdmin);
                tamperCmd.Parameters.AddWithValue("id", preWo1.ResultId);
                await tamperCmd.ExecuteNonQueryAsync(Cancel);
            }

            await using (var apiConflict = await ApiProcess.StartAsync(appConnStr))
            {
                using var clientConflict = apiConflict.CreateClient();
                using var conflictResp = await clientConflict.GetAsync("/api/archive?q=WO-004192", Cancel);
                Assert.Equal(HttpStatusCode.ServiceUnavailable, conflictResp.StatusCode);
                var conflictProb = await conflictResp.Content.ReadFromJsonAsync<JsonElement>(Cancel);
                Assert.Equal("archive_projection_conflict", conflictProb.GetProperty("code").GetString());

                // Existing document endpoint remains unaffected and truthful!
                using var docResp = await clientConflict.GetAsync($"/api/documents/{preWo1.DocumentId:D}", Cancel);
                Assert.Equal(HttpStatusCode.OK, docResp.StatusCode);
            }
        }
        finally
        {
            await PostgresFixture.ExecuteAsync(admin, $"DROP DATABASE IF EXISTS {dbName} WITH (FORCE)");
        }
    }

    [Fact]
    public async Task F4_BIC08_modest_synthetic_archive_explain_plans_and_bounded_search_execution()
    {
        await using var db = await fixture.CreateDatabaseAsync();

        // Populate a declared modest 50-document synthetic archive (40 projected results + 10 unprocessed).
        var pdfBytes = FixturePdf;
        var pdfSha = SHA256.HashData(pdfBytes);
        var baseTs = new DateTimeOffset(2026, 11, 17, 6, 0, 0, TimeSpan.Zero);
        var dummyDigest = SHA256.HashData("modest-archive"u8);

        var runtimeFactory = new PooledDbContextFactory<ELedgerCareDbContext>(
            new DbContextOptionsBuilder<ELedgerCareDbContext>().UseNpgsql(db.AppConnectionString).Options);
        var intakeStore = new IntakeStore(runtimeFactory);
        var extractionStore = new ExtractionStore(runtimeFactory);

        for (var i = 0; i < 50; i++)
        {
            var docId = Guid.NewGuid();
            var jobId = Guid.NewGuid();
            var doc = Document.Submit(docId, jobId, Guid.NewGuid(), pdfBytes, 1, baseTs.AddSeconds(i));
            Assert.Equal(InsertResult.Committed, await intakeStore.InsertAsync(doc, Cancel));

            if (i < 40)
            {
                await extractionStore.QueueOrReconcileAsync(docId, null, 3, workerEnabled: true, baseTs.AddSeconds(i), Cancel);
                var leased = (await extractionStore.ClaimNextQueuedJobAsync(
                    Guid.NewGuid(), 2000 + i, 800000L + i, baseTs.AddSeconds(i), Cancel))!;
                var raw = Encoding.UTF8.GetBytes(
                    $"<PAGE>\n<BLOCK>text[1,1,10,10]<FORK>Synthetic Work Order SYNTH-MODEST-{i:D4} Valve Inspection\n");
                var res = ExtractionResult.Create(
                    Guid.NewGuid(), docId, jobId, leased.AttemptId, leased.FencingToken,
                    pdfSha, pdfBytes.Length, 1, raw, SHA256.HashData(raw),
                    "baidu/Unlimited-OCR-2", "0480966938291445591f69f08a13b041c073a96a",
                    dummyDigest, dummyDigest, dummyDigest, dummyDigest,
                    "pypdfium2", "{}", "stop", 1,
                    baseTs.AddSeconds(i), baseTs.AddSeconds(i).AddMilliseconds(50),
                    5, 5, 40, 50, "{}");
                Assert.True(await extractionStore.PublishCompletedResultAsync(res, 0, baseTs.AddSeconds(i).AddMilliseconds(50), Cancel));
            }
        }

        await using (var admin = await db.OpenAdminAsync())
        {
            await PostgresFixture.ExecuteAsync(admin, "ANALYZE");

            var parsedKeyset = new ParsedArchiveQuery(
                "SYNTH-MODEST-0025 Valve",
                ["SYNTH-MODEST-0025", "Valve"],
                ArchiveSourceFilter.All,
                20,
                new ArchiveCursorPosition(baseTs.AddSeconds(45), ArchiveCursor.ToUnixMicroseconds(baseTs.AddSeconds(45)), Guid.NewGuid()));

            var explainSql = "EXPLAIN (FORMAT TEXT) " + ArchiveStore.BuildSearchCardHeadersSql(parsedKeyset);
            await using var explainCmd = new NpgsqlCommand(explainSql, admin);
            ArchiveStore.BindSearchParameters(explainCmd, parsedKeyset);

            var planLines = new List<string>();
            await using (var reader = await explainCmd.ExecuteReaderAsync(Cancel))
            {
                while (await reader.ReadAsync(Cancel))
                {
                    planLines.Add(reader.GetString(0));
                }
            }

            var planText = string.Join('\n', planLines);
            Assert.NotEmpty(planText);
            TestContext.Current.TestOutputHelper?.WriteLine(planText);
        }

        await using var api = await ApiProcess.StartAsync(db.AppConnectionString);
        using var client = api.CreateClient();

        var sw = Stopwatch.StartNew();
        var hit = await GetArchiveOkAsync(client, "/api/archive?q=SYNTH-MODEST-0025+Valve");
        sw.Stop();

        Assert.Single(hit.GetProperty("items").EnumerateArray());
        Assert.True(sw.Elapsed < TimeSpan.FromSeconds(5));
    }

    private static async Task<Guid> SubmitPdfAsync(HttpClient client, byte[] pdfBytes)
    {
        using var req = new HttpRequestMessage(HttpMethod.Post, "/api/documents");
        req.Headers.Add("Idempotency-Key", Guid.NewGuid().ToString("D"));
        req.Content = new ByteArrayContent(pdfBytes);
        req.Content.Headers.ContentType = new MediaTypeHeaderValue("application/pdf");

        using var resp = await client.SendAsync(req, Cancel);
        Assert.Equal(HttpStatusCode.Created, resp.StatusCode);
        var json = await resp.Content.ReadFromJsonAsync<JsonElement>(Cancel);
        return Guid.Parse(json.GetProperty("documentId").GetString()!);
    }

    private static async Task<JsonElement> GetArchiveOkAsync(HttpClient client, string pathAndQuery)
    {
        using var resp = await client.GetAsync(pathAndQuery, Cancel);
        Assert.Equal(HttpStatusCode.OK, resp.StatusCode);
        return await resp.Content.ReadFromJsonAsync<JsonElement>(Cancel);
    }

    private static async Task SaveReviewRevisionAsync(
        HttpClient client,
        Guid documentId,
        Guid resultId,
        int expectedRevision,
        string status,
        string? operatorLabel,
        object[] fields)
    {
        using var req = new HttpRequestMessage(HttpMethod.Post, $"/api/documents/{documentId:D}/review/revisions");
        req.Headers.Add("Idempotency-Key", Guid.NewGuid().ToString("D"));
        req.Content = JsonContent.Create(new
        {
            resultId = resultId.ToString("D"),
            expectedRevision,
            status,
            operatorDisplayLabel = operatorLabel,
            fields,
        });

        using var resp = await client.SendAsync(req, Cancel);
        Assert.Equal(HttpStatusCode.Created, resp.StatusCode);
    }

    private static async Task MarkJobFailedWithDiagnosticsAsync(
        string appConnStr,
        Guid documentId,
        string diagnosticPartial,
        string failureDetail)
    {
        await using var conn = new NpgsqlConnection(appConnStr);
        await conn.OpenAsync(Cancel);
        await using var tx = await conn.BeginTransactionAsync(Cancel);

        Guid jobId;
        await using (var q = new NpgsqlCommand("SELECT job_id FROM eledgercare.processing_jobs WHERE document_id = @d", conn, tx))
        {
            q.Parameters.AddWithValue("d", documentId);
            jobId = (Guid)(await q.ExecuteScalarAsync(Cancel))!;
        }

        long token;
        await using (var s = new NpgsqlCommand("SELECT nextval('eledgercare.extraction_fencing_seq')", conn, tx))
        {
            token = (long)(await s.ExecuteScalarAsync(Cancel))!;
        }

        var attemptId = Guid.NewGuid();
        const string sql = """
            UPDATE eledgercare.processing_jobs
               SET status = 'queued', queued_at = now(), updated_at = now()
             WHERE job_id = @jobId;
            UPDATE eledgercare.processing_jobs
               SET status = 'running', attempt_count = 1, latest_fencing_token = @tok, updated_at = now()
             WHERE job_id = @jobId;
            INSERT INTO eledgercare.execution_attempts (
                attempt_id, job_id, document_id, attempt_number, fencing_token, retried_from_attempt_id,
                status, phase, run_directory_name, supervisor_instance_id, supervisor_pid, supervisor_create_filetime,
                started_at, last_heartbeat_at
            ) VALUES (
                @attId, @jobId, @docId, 1, @tok, NULL,
                'running', 'inferring', @runDir, @supId, 4400, 133700000000004400,
                now(), now()
            );
            UPDATE eledgercare.processing_jobs
               SET status = 'failed', updated_at = now()
             WHERE job_id = @jobId AND latest_fencing_token = @tok;
            UPDATE eledgercare.execution_attempts
               SET status = 'failed', phase = 'failed', ended_at = now(), last_heartbeat_at = now(),
                   exit_code = 2, failure_code = 'model_output_truncated',
                   failure_detail = @detail, diagnostic_raw_output_utf8 = @diag
             WHERE attempt_id = @attId;
            """;
        await using (var cmd = new NpgsqlCommand(sql, conn, tx))
        {
            cmd.Parameters.AddWithValue("jobId", jobId);
            cmd.Parameters.AddWithValue("docId", documentId);
            cmd.Parameters.AddWithValue("attId", attemptId);
            cmd.Parameters.AddWithValue("tok", token);
            cmd.Parameters.AddWithValue("runDir", $"attempt-{attemptId:D}");
            cmd.Parameters.AddWithValue("supId", Guid.NewGuid());
            cmd.Parameters.AddWithValue("detail", failureDetail);
            cmd.Parameters.AddWithValue("diag", diagnosticPartial);
            await cmd.ExecuteNonQueryAsync(Cancel);
        }

        await tx.CommitAsync(Cancel);
    }

    private static async Task InsertAwaitingDocumentAtTimestampAsync(
        NpgsqlConnection appConn,
        Guid docId,
        DateTimeOffset submittedAtUtc,
        byte[] pdfBytes,
        byte[] pdfSha)
    {
        await using var tx = await appConn.BeginTransactionAsync(Cancel);
        const string sql = """
            INSERT INTO eledgercare.documents (document_id, idempotency_key, submitted_at)
            VALUES (@docId, @key, @ts);
            INSERT INTO eledgercare.original_artifacts (document_id, bytes, sha256, byte_length, media_type, page_count)
            VALUES (@docId, @bytes, @sha, @len, 'application/pdf', 1);
            INSERT INTO eledgercare.processing_jobs (job_id, document_id, status, requested_at, queued_at, updated_at, attempt_count, latest_fencing_token, retried_from_attempt_id)
            VALUES (@jobId, @docId, 'awaiting_extraction', @ts, NULL, @ts, 0, 0, NULL);
            """;
        await using var cmd = new NpgsqlCommand(sql, appConn, tx);
        cmd.Parameters.AddWithValue("docId", docId);
        cmd.Parameters.AddWithValue("key", Guid.NewGuid());
        cmd.Parameters.AddWithValue("ts", submittedAtUtc);
        cmd.Parameters.AddWithValue("bytes", pdfBytes);
        cmd.Parameters.AddWithValue("sha", pdfSha);
        cmd.Parameters.AddWithValue("len", pdfBytes.Length);
        cmd.Parameters.AddWithValue("jobId", Guid.NewGuid());
        await cmd.ExecuteNonQueryAsync(Cancel);
        await tx.CommitAsync(Cancel);
    }

    private static async Task ApplyF3OnlyRuntimeGrantsAsync(string migratorConnectionString)
    {
        const string f3Grants = """
            GRANT USAGE ON SCHEMA eledgercare TO eledgercare_app;
            GRANT USAGE, SELECT ON SEQUENCE eledgercare.extraction_fencing_seq TO eledgercare_app;
            GRANT SELECT, INSERT ON TABLE
                eledgercare.documents,
                eledgercare.original_artifacts,
                eledgercare.processing_jobs,
                eledgercare.execution_attempts,
                eledgercare.extraction_results,
                eledgercare.work_order_review_revisions,
                eledgercare.work_order_review_fields,
                eledgercare.work_order_review_heads
            TO eledgercare_app;
            GRANT UPDATE (status, queued_at, updated_at, attempt_count, latest_fencing_token, retried_from_attempt_id)
                ON TABLE eledgercare.processing_jobs TO eledgercare_app;
            GRANT UPDATE (status, phase, launcher_pid, launcher_create_filetime, worker_pid, worker_create_filetime,
                          last_heartbeat_at, ended_at, exit_code, failure_code, failure_detail, diagnostic_raw_output_utf8, diagnostic_metadata_json)
                ON TABLE eledgercare.execution_attempts TO eledgercare_app;
            GRANT UPDATE (current_revision_number, current_revision_id, current_status, updated_at)
                ON TABLE eledgercare.work_order_review_heads TO eledgercare_app;
            """;
        await using var conn = await PostgresFixture.OpenAsync(migratorConnectionString);
        await PostgresFixture.ExecuteAsync(conn, f3Grants);
    }
}
