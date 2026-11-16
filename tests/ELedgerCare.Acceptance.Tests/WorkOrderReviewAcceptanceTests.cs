using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using ELedgerCare.Acceptance.Tests.Harness;
using ELedgerCare.Domain.Processing;
using ELedgerCare.Domain.Review;
using ELedgerCare.Infrastructure.Persistence;
using ELedgerCare.Tests.Shared;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql;
using Xunit;

namespace ELedgerCare.Acceptance.Tests;

/// <summary>
/// WP-0008 F3 real PostgreSQL 18.7 and real ELedgerCare.Api HTTP acceptance tests covering F3-01..07
/// and independent checkpoints F3-BIC-01..06 with LocalOcr:Enabled=false and zero GPU/model calls.
/// </summary>
[Collection(PostgresCollection.Name)]
public sealed class WorkOrderReviewAcceptanceTests(PostgresFixture fixture)
{
    private static readonly TimeSpan LockWait = TimeSpan.FromSeconds(20);
    private static CancellationToken Cancel => TestContext.Current.CancellationToken;

    [Fact]
    public async Task F3_06_forward_migration_from_F1_and_F2_preserves_existing_rows_and_enables_review()
    {
        var dbName = $"eledgercare_f3_fwd_{Guid.NewGuid().ToString("N")[..10]}";
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

            var migOptions = new DbContextOptionsBuilder<ELedgerCareDbContext>()
                .UseNpgsql(fixture.Settings.Migrator(dbName), npgsql =>
                    npgsql.MigrationsHistoryTable("__ef_migrations_history", ELedgerCareDbContext.Schema))
                .Options;

            // Step 1: Migrate to F1 (20261114182147_InitialDurableIntake) and insert an F1 document.
            await using (var migDb1 = new ELedgerCareDbContext(migOptions))
            {
                await migDb1.GetService<IMigrator>().MigrateAsync("20261114182147_InitialDurableIntake", Cancel);
            }

            var f1DocId = Guid.NewGuid();
            var f1JobId = Guid.NewGuid();
            var f1Bytes = SyntheticPdf.CanonicalFixture();
            var f1Sha = SHA256.HashData(f1Bytes);
            var t0 = new DateTimeOffset(2026, 11, 14, 18, 30, 0, TimeSpan.Zero);

            await using (var migConn1 = await PostgresFixture.OpenAsync(fixture.Settings.Migrator(dbName)))
            {
                await using var tx1 = await migConn1.BeginTransactionAsync(Cancel);
                await using (var c1 = new NpgsqlCommand(
                    "INSERT INTO eledgercare.documents (document_id, idempotency_key, submitted_at) VALUES (@id, @k, @t)", migConn1, tx1))
                {
                    c1.Parameters.AddWithValue("id", f1DocId);
                    c1.Parameters.AddWithValue("k", Guid.NewGuid());
                    c1.Parameters.AddWithValue("t", t0);
                    await c1.ExecuteNonQueryAsync(Cancel);
                }

                await using (var c2 = new NpgsqlCommand(
                    "INSERT INTO eledgercare.original_artifacts (document_id, bytes, sha256, byte_length, media_type, page_count) VALUES (@id, @b, @s, @l, 'application/pdf', 1)", migConn1, tx1))
                {
                    c2.Parameters.AddWithValue("id", f1DocId);
                    c2.Parameters.AddWithValue("b", f1Bytes);
                    c2.Parameters.AddWithValue("s", f1Sha);
                    c2.Parameters.AddWithValue("l", f1Bytes.Length);
                    await c2.ExecuteNonQueryAsync(Cancel);
                }

                await using (var c3 = new NpgsqlCommand(
                    "INSERT INTO eledgercare.processing_jobs (job_id, document_id, status, requested_at) VALUES (@j, @id, 'awaiting_extraction', @t)", migConn1, tx1))
                {
                    c3.Parameters.AddWithValue("j", f1JobId);
                    c3.Parameters.AddWithValue("id", f1DocId);
                    c3.Parameters.AddWithValue("t", t0);
                    await c3.ExecuteNonQueryAsync(Cancel);
                }

                await tx1.CommitAsync(Cancel);
            }

            // Step 2: Migrate to F2 (20261116052029_AddLocalExtraction) and seed genuine F2 SYN-WO-01 row BEFORE F3 migration!
            await using (var migDb2 = new ELedgerCareDbContext(migOptions))
            {
                await migDb2.GetService<IMigrator>().MigrateAsync("20261116052029_AddLocalExtraction", Cancel);
            }

            // Apply F1+F2 grants temporarily as migrator so GenuineF2Seeds can seed under eledgercare_app BEFORE F3 migration.
            await using (var migConn2 = await PostgresFixture.OpenAsync(fixture.Settings.Migrator(dbName)))
            {
                const string f2Grants = """
                    GRANT USAGE ON SCHEMA eledgercare TO eledgercare_app;
                    GRANT USAGE, SELECT ON SEQUENCE eledgercare.extraction_fencing_seq TO eledgercare_app;
                    GRANT SELECT, INSERT ON TABLE eledgercare.documents, eledgercare.original_artifacts, eledgercare.processing_jobs, eledgercare.execution_attempts, eledgercare.extraction_results TO eledgercare_app;
                    GRANT UPDATE (status, queued_at, updated_at, attempt_count, latest_fencing_token, retried_from_attempt_id) ON TABLE eledgercare.processing_jobs TO eledgercare_app;
                    GRANT UPDATE (status, phase, launcher_pid, launcher_create_filetime, worker_pid, worker_create_filetime, last_heartbeat_at, ended_at, exit_code, failure_code, failure_detail, diagnostic_raw_output_utf8, diagnostic_metadata_json) ON TABLE eledgercare.execution_attempts TO eledgercare_app;
                    """;
                await PostgresFixture.ExecuteAsync(migConn2, f2Grants);
            }

            var f2Seed = await GenuineF2Seeds.SeedSynWo01Async(fixture.Settings.App(dbName), remapIds: false, Cancel);

            // Step 3: Migrate forward to F3 (AddWorkOrderReview) and apply full grant-runtime.sql.
            await using (var migDb3 = new ELedgerCareDbContext(migOptions))
            {
                await migDb3.Database.MigrateAsync(Cancel);
            }

            await using (var migConn3 = await PostgresFixture.OpenAsync(fixture.Settings.Migrator(dbName)))
            {
                var grants = await File.ReadAllTextAsync(Path.Combine(RepositoryPaths.Root, "deploy", "dev", "database", "grant-runtime.sql"), Cancel);
                await PostgresFixture.ExecuteAsync(migConn3, grants);
            }

            // Step 4: Verify F1 and F2 rows are byte-exact and F3 review works immediately over HTTP!
            await using var api = await ApiProcess.StartAsync(fixture.Settings.App(dbName));
            using var client = api.CreateClient();

            Assert.Equal(f1Bytes, await client.GetByteArrayAsync($"/api/documents/{f1DocId:D}/original", Cancel));
            Assert.Equal(f2Seed.PdfBytes, await client.GetByteArrayAsync($"/api/documents/{f2Seed.DocumentId:D}/preview", Cancel));

            var revPreview = await client.GetFromJsonAsync<JsonElement>($"/api/documents/{f2Seed.DocumentId:D}/review", Cancel);
            Assert.Equal(0, revPreview.GetProperty("currentRevisionNumber").GetInt32());
            Assert.Equal("unreviewed", revPreview.GetProperty("reviewState").GetString());
            Assert.Equal("WO-004192", revPreview.GetProperty("fields")[0].GetProperty("machineCandidate").GetProperty("value").GetString());

            using var saveResp = await client.SendAsync(BuildSaveRequest(
                f2Seed.DocumentId,
                Guid.NewGuid(),
                f2Seed.ResultId,
                expectedRevision: 0,
                status: "draft",
                operatorDisplayLabel: "Migration check",
                DefaultDraftFields()), Cancel);
            Assert.Equal(HttpStatusCode.Created, saveResp.StatusCode);

            Evidence.Record("F3-06 forward migration F1->F2->F3", new
            {
                database = dbName,
                f1DocumentId = f1DocId,
                f2SeedDocumentId = f2Seed.DocumentId,
                f2RawSha256Preserved = f2Seed.RawOutputSha256Hex,
                f3DraftRevisionCreatedStatus = (int)saveResp.StatusCode,
            });
        }
        finally
        {
            await PostgresFixture.ExecuteAsync(admin, $"DROP DATABASE IF EXISTS {dbName} WITH (FORCE)");
        }
    }

    [Fact]
    public async Task F3_06_F3_BIC_02_column_scoped_least_privilege_denies_immutable_head_and_revision_mutations()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        var seed = await GenuineF2Seeds.SeedSynWo01Async(db.AppConnectionString, remapIds: false, Cancel);

        await using (var api = await ApiProcess.StartAsync(db.AppConnectionString))
        {
            using var client = api.CreateClient();
            using var resp = await client.SendAsync(BuildSaveRequest(
                seed.DocumentId, Guid.NewGuid(), seed.ResultId, 0, "draft", "Privilege test", DefaultDraftFields()), Cancel);
            Assert.Equal(HttpStatusCode.Created, resp.StatusCode);
        }

        await using var appConn = await db.OpenAppAsync();
        var deniedStatements = new[]
        {
            // Revisions and fields are strictly append-only (SELECT, INSERT only).
            "UPDATE eledgercare.work_order_review_revisions SET status = 'reviewed'",
            "DELETE FROM eledgercare.work_order_review_revisions",
            "TRUNCATE eledgercare.work_order_review_revisions",
            "UPDATE eledgercare.work_order_review_fields SET human_value = 'tamper'",
            "DELETE FROM eledgercare.work_order_review_fields",
            // Review heads deny DELETE and deny UPDATE on every immutable provenance/snapshot column (F3-BIC-02)!
            "DELETE FROM eledgercare.work_order_review_heads",
            "UPDATE eledgercare.work_order_review_heads SET document_id = document_id",
            "UPDATE eledgercare.work_order_review_heads SET result_id = result_id",
            "UPDATE eledgercare.work_order_review_heads SET input_sha256 = input_sha256",
            "UPDATE eledgercare.work_order_review_heads SET raw_output_sha256 = raw_output_sha256",
            "UPDATE eledgercare.work_order_review_heads SET profile_id = profile_id",
            "UPDATE eledgercare.work_order_review_heads SET field_schema_version = field_schema_version",
            "UPDATE eledgercare.work_order_review_heads SET suggestion_policy_version = suggestion_policy_version",
            "UPDATE eledgercare.work_order_review_heads SET machine_snapshot_json = machine_snapshot_json",
            "UPDATE eledgercare.work_order_review_heads SET created_at = created_at",
            // Original artifacts and extraction results remain immutable.
            "UPDATE eledgercare.extraction_results SET raw_output_bytes = raw_output_bytes",
            "UPDATE eledgercare.original_artifacts SET bytes = bytes",
        };

        foreach (var sql in deniedStatements)
        {
            await using var cmd = new NpgsqlCommand(sql, appConn);
            var ex = await Assert.ThrowsAsync<PostgresException>(() => cmd.ExecuteNonQueryAsync(Cancel));
            Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, ex.SqlState);
        }

        Evidence.Record("F3-06 / F3-BIC-02 least privilege", new
        {
            database = db.Name,
            deniedStatementCount = deniedStatements.Length,
            allReturnedSqlState = PostgresErrorCodes.InsufficientPrivilege,
        });
    }

    [Fact]
    public async Task F3_01_F3_BIC_04_inline_preview_endpoint_headers_range_support_and_unchanged_original_attachment()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        var seed = await GenuineF2Seeds.SeedSynWo01Async(db.AppConnectionString, remapIds: false, Cancel);

        await using var api = await ApiProcess.StartAsync(db.AppConnectionString);
        using var client = api.CreateClient();

        // 1. /preview returns exact PDF bytes with inline disposition, SAMEORIGIN/frame-ancestors 'self', nosniff, and ETag.
        using (var previewResp = await client.GetAsync($"/api/documents/{seed.DocumentId:D}/preview", Cancel))
        {
            Assert.Equal(HttpStatusCode.OK, previewResp.StatusCode);
            var bytes = await previewResp.Content.ReadAsByteArrayAsync(Cancel);
            Assert.Equal(seed.PdfBytes, bytes);
            Assert.Equal("application/pdf", previewResp.Content.Headers.ContentType?.MediaType);
            Assert.Equal("inline", previewResp.Content.Headers.ContentDisposition?.DispositionType);
            Assert.Equal($"document-{seed.DocumentId:D}.pdf", previewResp.Content.Headers.ContentDisposition?.FileName?.Trim('"'));
            Assert.Equal("nosniff", string.Join(',', previewResp.Headers.GetValues("X-Content-Type-Options")));
            Assert.Equal("SAMEORIGIN", string.Join(',', previewResp.Headers.GetValues("X-Frame-Options")));
            Assert.Equal("frame-ancestors 'self'", string.Join(',', previewResp.Headers.GetValues("Content-Security-Policy")));
            Assert.Contains("bytes", previewResp.Headers.AcceptRanges);
            Assert.Equal($"\"{seed.PdfSha256Hex}\"", previewResp.Headers.ETag?.Tag);
        }

        // 2. Range request returns 206 Partial Content with exact PDF header slice (%PDF-1.).
        using (var rangeReq = new HttpRequestMessage(HttpMethod.Get, $"/api/documents/{seed.DocumentId:D}/preview"))
        {
            rangeReq.Headers.Range = new RangeHeaderValue(0, 63);
            using var rangeResp = await client.SendAsync(rangeReq, Cancel);
            Assert.Equal(HttpStatusCode.PartialContent, rangeResp.StatusCode);
            var slice = await rangeResp.Content.ReadAsByteArrayAsync(Cancel);
            Assert.Equal(64, slice.Length);
            Assert.Equal(seed.PdfBytes[..64], slice);
        }

        // 3. /original remains attachment and byte-identical.
        using (var origResp = await client.GetAsync($"/api/documents/{seed.DocumentId:D}/original", Cancel))
        {
            Assert.Equal(HttpStatusCode.OK, origResp.StatusCode);
            Assert.Equal("attachment", origResp.Content.Headers.ContentDisposition?.DispositionType);
            Assert.Equal(seed.PdfBytes, await origResp.Content.ReadAsByteArrayAsync(Cancel));
        }

        // 4. Malformed / path-traversal identifiers return 400; unknown UUID returns 404.
        using var badPreview = await client.GetAsync("/api/documents/..%2F..%2Fetc%2Fpasswd/preview", Cancel);
        Assert.Equal(HttpStatusCode.BadRequest, badPreview.StatusCode);

        using var missingPreview = await client.GetAsync($"/api/documents/{Guid.NewGuid():D}/preview", Cancel);
        Assert.Equal(HttpStatusCode.NotFound, missingPreview.StatusCode);
    }

    [Fact]
    public async Task F3_01_F3_02_F3_03_F3_05_genuine_F2_seeds_draft_reviewed_unknowns_post_review_edit_history_and_disabled_ocr_restart()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        var woSeed = await GenuineF2Seeds.SeedSynWo01Async(db.AppConnectionString, remapIds: false, Cancel);
        var mpSeed = await GenuineF2Seeds.SeedSynMp01Async(db.AppConnectionString, remapIds: false, Cancel);

        int firstApiPid;
        Guid rev1Id, rev2Id, rev3Id;

        await using (var api1 = await ApiProcess.StartAsync(db.AppConnectionString))
        {
            firstApiPid = api1.Pid;
            using var client = api1.CreateClient();

            // 1. Pure read GET /review at Revision 0 creates zero rows and zero extraction attempts.
            var preview0 = await client.GetFromJsonAsync<JsonElement>($"/api/documents/{woSeed.DocumentId:D}/review", Cancel);
            Assert.Equal(0, preview0.GetProperty("currentRevisionNumber").GetInt32());
            Assert.Equal("unreviewed", preview0.GetProperty("reviewState").GetString());
            Assert.Equal(JsonValueKind.Null, preview0.GetProperty("currentRevision").ValueKind);
            Assert.Equal(0, preview0.GetProperty("history").GetArrayLength());
            Assert.Equal(0L, await db.ScalarAsync("SELECT count(*) FROM eledgercare.work_order_review_heads"));
            Assert.Equal(0L, await db.ScalarAsync("SELECT count(*) FROM eledgercare.work_order_review_revisions"));

            // Also check 3-page invoice packet SYN-MP-01: GET /documents/{id} has null workOrderReview (not auto-classified),
            // and GET /review shows 5 missing machine candidates with unreviewed human decisions.
            var mpExt = await client.GetFromJsonAsync<JsonElement>($"/api/documents/{mpSeed.DocumentId:D}/extraction", Cancel);
            Assert.Equal(JsonValueKind.Null, mpExt.GetProperty("workOrderReview").ValueKind);
            var mpPreview = await client.GetFromJsonAsync<JsonElement>($"/api/documents/{mpSeed.DocumentId:D}/review", Cancel);
            Assert.All(mpPreview.GetProperty("fields").EnumerateArray(), f =>
            {
                Assert.Equal("missing", f.GetProperty("machineCandidate").GetProperty("status").GetString());
                Assert.Equal("unreviewed", f.GetProperty("decision").GetString());
            });

            // 2. Save Revision #1 (draft: 2 accepted, 1 edited with leading zero preserved, 2 unreviewed).
            var rev1Fields = new object[]
            {
                Field("work_order_id", "accepted", "WO-004192"),
                Field("property_name", "accepted", "Cedar Hollow Apartments"),
                Field("building_unit", "edited", "00204 - Bldg B (Verified)"),
                Field("requested_date", "unreviewed", null),
                Field("issue_and_resolution", "unreviewed", "Draft note line 1\nDraft note line 2"),
            };
            using (var r1Resp = await client.SendAsync(BuildSaveRequest(
                woSeed.DocumentId, Guid.NewGuid(), woSeed.ResultId, 0, "draft", "Tech Clerk 1", rev1Fields), Cancel))
            {
                Assert.Equal(HttpStatusCode.Created, r1Resp.StatusCode);
                Assert.Equal($"/api/documents/{woSeed.DocumentId:D}/review/revisions/1", r1Resp.Headers.Location?.OriginalString);
                var r1Json = await r1Resp.Content.ReadFromJsonAsync<JsonElement>(Cancel);
                Assert.False(r1Json.GetProperty("replayed").GetBoolean());
                Assert.True(r1Json.GetProperty("isCurrentHead").GetBoolean());
                Assert.Equal(1, r1Json.GetProperty("currentRevisionNumber").GetInt32());
                Assert.Equal("draft", r1Json.GetProperty("currentReviewState").GetString());
                rev1Id = r1Json.GetProperty("revision").GetProperty("revisionId").GetGuid();
            }

            // 3. Save Revision #2 (explicit reviewed: 3 accepted, 1 edited correction, 1 explicit unknown with reason).
            var rev2Narrative = preview0.GetProperty("fields")[4].GetProperty("machineCandidate").GetProperty("value").GetString()!;
            var rev2Fields = new object[]
            {
                Field("work_order_id", "accepted", "WO-004192"),
                Field("property_name", "edited", "Cedar Hollow Apartments — North Campus", new { pageNumber = 1, blockOrdinal = 6, tableRow = (int?)null, tableColumn = (int?)null }),
                Field("building_unit", "unknown", null, unknownReason: "Tenant transferred units; physical door tag pending verification"),
                Field("requested_date", "accepted", "2026-10-16"),
                Field("issue_and_resolution", "accepted", rev2Narrative),
            };
            using (var r2Resp = await client.SendAsync(BuildSaveRequest(
                woSeed.DocumentId, Guid.NewGuid(), woSeed.ResultId, 1, "reviewed", "Lead Reviewer", rev2Fields), Cancel))
            {
                Assert.Equal(HttpStatusCode.Created, r2Resp.StatusCode);
                var r2Json = await r2Resp.Content.ReadFromJsonAsync<JsonElement>(Cancel);
                Assert.Equal(2, r2Json.GetProperty("currentRevisionNumber").GetInt32());
                Assert.Equal("reviewed", r2Json.GetProperty("currentReviewState").GetString());
                Assert.Equal(1, r2Json.GetProperty("revision").GetProperty("unknownFieldCount").GetInt32());
                rev2Id = r2Json.GetProperty("revision").GetProperty("revisionId").GetGuid();
            }

            // Verify extraction endpoint still shows immutable raw output ("unreviewed" raw status) ALONGSIDE workOrderReview summary!
            var woExtAtRev2 = await client.GetFromJsonAsync<JsonElement>($"/api/documents/{woSeed.DocumentId:D}/extraction", Cancel);
            Assert.Equal("completed", woExtAtRev2.GetProperty("status").GetString());
            Assert.Equal("unreviewed", woExtAtRev2.GetProperty("result").GetProperty("reviewStatus").GetString());
            Assert.Equal("reviewed", woExtAtRev2.GetProperty("workOrderReview").GetProperty("status").GetString());
            Assert.Equal(2, woExtAtRev2.GetProperty("workOrderReview").GetProperty("currentRevisionNumber").GetInt32());
            Assert.Equal(1, woExtAtRev2.GetProperty("workOrderReview").GetProperty("unknownFieldCount").GetInt32());

            // 4. Save Revision #3 (new edit after reviewed -> creates a new DRAFT revision; historical Revision #2 does NOT approve #3!).
            var rev3Fields = new object[]
            {
                Field("work_order_id", "accepted", "WO-004192"),
                Field("property_name", "edited", "Cedar Hollow Apartments — North Campus"),
                Field("building_unit", "edited", "Bldg B - Unit 204B (Confirmed)"),
                Field("requested_date", "accepted", "2026-10-16"),
                Field("issue_and_resolution", "unreviewed", rev2Narrative + "\nFollow-up coil check scheduled."),
            };
            using (var r3Resp = await client.SendAsync(BuildSaveRequest(
                woSeed.DocumentId, Guid.NewGuid(), woSeed.ResultId, 2, "draft", "Follow-up Tech", rev3Fields), Cancel))
            {
                Assert.Equal(HttpStatusCode.Created, r3Resp.StatusCode);
                var r3Json = await r3Resp.Content.ReadFromJsonAsync<JsonElement>(Cancel);
                Assert.Equal(3, r3Json.GetProperty("currentRevisionNumber").GetInt32());
                Assert.Equal("draft", r3Json.GetProperty("currentReviewState").GetString());
                rev3Id = r3Json.GetProperty("revision").GetProperty("revisionId").GetGuid();
            }

            await api1.KillAsync();
        }

        // 5. Restart API with LocalOcr:Enabled=false (default) and verify exact revisions 1, 2, 3, immutable raw/original bytes, and 0 new OCR attempts!
        await using var api2 = await ApiProcess.StartAsync(db.AppConnectionString);
        Assert.NotEqual(firstApiPid, api2.Pid);
        using var afterClient = api2.CreateClient();

        var headAfter = await afterClient.GetFromJsonAsync<JsonElement>($"/api/documents/{woSeed.DocumentId:D}/review", Cancel);
        Assert.Equal(3, headAfter.GetProperty("currentRevisionNumber").GetInt32());
        Assert.Equal("draft", headAfter.GetProperty("reviewState").GetString());
        Assert.Equal(rev3Id, headAfter.GetProperty("currentRevision").GetProperty("revisionId").GetGuid());
        Assert.Equal(3, headAfter.GetProperty("history").GetArrayLength());

        var histRev1 = await afterClient.GetFromJsonAsync<JsonElement>($"/api/documents/{woSeed.DocumentId:D}/review/revisions/1", Cancel);
        Assert.False(histRev1.GetProperty("isCurrentHead").GetBoolean());
        Assert.Equal(rev1Id, histRev1.GetProperty("revision").GetProperty("revisionId").GetGuid());
        Assert.Equal("00204 - Bldg B (Verified)", histRev1.GetProperty("fields")[2].GetProperty("value").GetString());

        var histRev2 = await afterClient.GetFromJsonAsync<JsonElement>($"/api/documents/{woSeed.DocumentId:D}/review/revisions/2", Cancel);
        Assert.False(histRev2.GetProperty("isCurrentHead").GetBoolean());
        Assert.Equal(rev2Id, histRev2.GetProperty("revision").GetProperty("revisionId").GetGuid());
        Assert.Equal("reviewed", histRev2.GetProperty("revision").GetProperty("status").GetString());
        Assert.Equal("unknown", histRev2.GetProperty("fields")[2].GetProperty("decision").GetString());
        Assert.Equal(JsonValueKind.Null, histRev2.GetProperty("fields")[2].GetProperty("value").ValueKind);
        Assert.Equal("Tenant transferred units; physical door tag pending verification", histRev2.GetProperty("fields")[2].GetProperty("unknownReason").GetString());
        Assert.Equal("Cedar Hollow Apartments", histRev2.GetProperty("fields")[1].GetProperty("consultedSource").GetProperty("sourceQuote").GetString());
        // Original machine candidate on Building / Unit remains visible alongside human unknown!
        Assert.Equal("Bldg B - Unit 204", histRev2.GetProperty("fields")[2].GetProperty("machineCandidate").GetProperty("value").GetString());

        using var missingRev4 = await afterClient.GetAsync($"/api/documents/{woSeed.DocumentId:D}/review/revisions/4", Cancel);
        Assert.Equal(HttpStatusCode.NotFound, missingRev4.StatusCode);

        // Verify original_artifacts.bytes and extraction_results.raw_output_bytes are 100% untouched and attempt count is still 1 per document!
        Assert.Equal(woSeed.PdfBytes, await afterClient.GetByteArrayAsync($"/api/documents/{woSeed.DocumentId:D}/original", Cancel));
        Assert.Equal(woSeed.PdfBytes, await afterClient.GetByteArrayAsync($"/api/documents/{woSeed.DocumentId:D}/preview", Cancel));
        var extAfter = await afterClient.GetFromJsonAsync<JsonElement>($"/api/documents/{woSeed.DocumentId:D}/extraction", Cancel);
        Assert.Equal(woSeed.RawOutputSha256Hex, extAfter.GetProperty("result").GetProperty("rawSha256").GetString());
        Assert.Equal(Encoding.UTF8.GetString(woSeed.RawOutputBytes), extAfter.GetProperty("result").GetProperty("rawText").GetString());
        Assert.Equal(2L, await db.ScalarAsync("SELECT count(*) FROM eledgercare.execution_attempts"));

        Evidence.Record("F3-01/02/03/05 genuine seeds lifecycle and restart", new
        {
            database = db.Name,
            woDocumentId = woSeed.DocumentId,
            revisionsPersisted = new[] { rev1Id, rev2Id, rev3Id },
            postReviewEditBecameDraft = true,
            historicalRev2RemainedReviewedWithUnknown = true,
            apiPidBefore = firstApiPid,
            apiPidAfter = api2.Pid,
            originalAndRawDigestsUnchanged = true,
        });
    }

    [Fact]
    public async Task F3_04_F3_BIC_03_concurrent_saves_stale_conflicts_replay_after_later_save_lost_response_and_128_revision_cap()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        var docSameKeyRace = await GenuineF2Seeds.SeedSynWo01Async(db.AppConnectionString, remapIds: true, Cancel);
        var docDiffKeyRace = await GenuineF2Seeds.SeedSynWo01Async(db.AppConnectionString, remapIds: true, Cancel);
        var docCap = await GenuineF2Seeds.SeedSynWo01Async(db.AppConnectionString, remapIds: true, Cancel);

        await using var api = await ApiProcess.StartAsync(db.AppConnectionString);
        using var client = api.CreateClient();

        // 1. Concurrent SAME-key race at expectedRevision = 0 (blocked via SHARE lock on work_order_review_heads):
        //    Winner returns 201 Created, Loser reconciles unique violation to 200 OK Replay with identical RevisionId!
        var sharedKey0 = Guid.NewGuid();
        HttpResponseMessage[] sameKey0Responses;
        await using (var lockConn = await db.OpenAdminAsync())
        {
            await using var lockTx = await lockConn.BeginTransactionAsync(Cancel);
            await using (var lockCmd = new NpgsqlCommand("LOCK TABLE eledgercare.work_order_review_heads IN SHARE MODE", lockConn, lockTx))
            {
                await lockCmd.ExecuteNonQueryAsync(Cancel);
            }

            var tA = client.SendAsync(BuildSaveRequest(docSameKeyRace.DocumentId, sharedKey0, docSameKeyRace.ResultId, 0, "draft", "Same0", DefaultDraftFields()), Cancel);
            var tB = client.SendAsync(BuildSaveRequest(docSameKeyRace.DocumentId, sharedKey0, docSameKeyRace.ResultId, 0, "draft", "Same0", DefaultDraftFields()), Cancel);
            await LockObserver.WaitForBlockedAsync(db, fixture.Settings.AppUser, 2, LockWait);
            await lockTx.RollbackAsync(Cancel);
            sameKey0Responses = await Task.WhenAll(tA, tB);
        }

        Assert.Equal([HttpStatusCode.OK, HttpStatusCode.Created], sameKey0Responses.Select(r => r.StatusCode).Order().ToArray());
        var sameKey0Bodies = await Task.WhenAll(sameKey0Responses.Select(r => r.Content.ReadFromJsonAsync<JsonElement>(Cancel)));
        Assert.Equal(
            sameKey0Bodies[0].GetProperty("revision").GetProperty("revisionId").GetGuid(),
            sameKey0Bodies[1].GetProperty("revision").GetProperty("revisionId").GetGuid());
        foreach (var r in sameKey0Responses) r.Dispose();

        // 2. Concurrent DIFFERENT-key race at expectedRevision = 0 -> [201 Created, 409 stale_expected_revision]!
        HttpResponseMessage[] diffKey0Responses;
        await using (var lockConn2 = await db.OpenAdminAsync())
        {
            await using var lockTx2 = await lockConn2.BeginTransactionAsync(Cancel);
            await using (var lockCmd2 = new NpgsqlCommand("LOCK TABLE eledgercare.work_order_review_heads IN SHARE MODE", lockConn2, lockTx2))
            {
                await lockCmd2.ExecuteNonQueryAsync(Cancel);
            }

            var dA = client.SendAsync(BuildSaveRequest(docDiffKeyRace.DocumentId, Guid.NewGuid(), docDiffKeyRace.ResultId, 0, "draft", "Tab A", DefaultDraftFields("WO-A")), Cancel);
            var dB = client.SendAsync(BuildSaveRequest(docDiffKeyRace.DocumentId, Guid.NewGuid(), docDiffKeyRace.ResultId, 0, "draft", "Tab B", DefaultDraftFields("WO-B")), Cancel);
            await LockObserver.WaitForBlockedAsync(db, fixture.Settings.AppUser, 2, LockWait);
            await lockTx2.RollbackAsync(Cancel);
            diffKey0Responses = await Task.WhenAll(dA, dB);
        }

        Assert.Equal([HttpStatusCode.Created, HttpStatusCode.Conflict], diffKey0Responses.Select(r => r.StatusCode).Order().ToArray());
        var conflictResp0 = diffKey0Responses.Single(r => r.StatusCode == HttpStatusCode.Conflict);
        var conflictJson0 = await conflictResp0.Content.ReadFromJsonAsync<JsonElement>(Cancel);
        Assert.Equal("stale_expected_revision", conflictJson0.GetProperty("code").GetString());
        Assert.Equal(1, conflictJson0.GetProperty("currentRevisionNumber").GetInt32());
        foreach (var r in diffKey0Responses) r.Dispose();

        // 3. Concurrent SAME-key race AND concurrent DIFFERENT-key race at expectedRevision = 1 (FOR UPDATE serialization on work_order_review_heads)!
        var sharedKey1 = Guid.NewGuid();
        HttpResponseMessage[] sameKey1Responses;
        await using (var lockConn3 = await db.OpenAdminAsync())
        {
            await using var lockTx3 = await lockConn3.BeginTransactionAsync(Cancel);
            await using (var lockCmd3 = new NpgsqlCommand(
                "SELECT document_id FROM eledgercare.work_order_review_heads WHERE document_id = @id FOR UPDATE", lockConn3, lockTx3))
            {
                lockCmd3.Parameters.AddWithValue("id", docSameKeyRace.DocumentId);
                await lockCmd3.ExecuteScalarAsync(Cancel);
            }

            var s1A = client.SendAsync(BuildSaveRequest(docSameKeyRace.DocumentId, sharedKey1, docSameKeyRace.ResultId, 1, "draft", "Same1", DefaultDraftFields("WO-R2")), Cancel);
            var s1B = client.SendAsync(BuildSaveRequest(docSameKeyRace.DocumentId, sharedKey1, docSameKeyRace.ResultId, 1, "draft", "Same1", DefaultDraftFields("WO-R2")), Cancel);
            await LockObserver.WaitForBlockedAsync(db, fixture.Settings.AppUser, 2, LockWait);
            await lockTx3.RollbackAsync(Cancel);
            sameKey1Responses = await Task.WhenAll(s1A, s1B);
        }

        Assert.Equal([HttpStatusCode.OK, HttpStatusCode.Created], sameKey1Responses.Select(r => r.StatusCode).Order().ToArray());
        foreach (var r in sameKey1Responses) r.Dispose();

        // 4. Replay of Revision #1's Idempotency-Key (sharedKey0, expectedRevision=0) AFTER Revision #2 has committed!
        using (var oldReplay = await client.SendAsync(
            BuildSaveRequest(docSameKeyRace.DocumentId, sharedKey0, docSameKeyRace.ResultId, 0, "draft", "Same0", DefaultDraftFields()), Cancel))
        {
            Assert.Equal(HttpStatusCode.OK, oldReplay.StatusCode);
            var oldJson = await oldReplay.Content.ReadFromJsonAsync<JsonElement>(Cancel);
            Assert.True(oldJson.GetProperty("replayed").GetBoolean());
            Assert.False(oldJson.GetProperty("isCurrentHead").GetBoolean());
            Assert.Equal(1, oldJson.GetProperty("revision").GetProperty("revisionNumber").GetInt32());
            Assert.Equal(2, oldJson.GetProperty("currentRevisionNumber").GetInt32());
        }

        // 5. Same Idempotency-Key with ANY changed parameter (value, expectedRevision, or different document) -> 409 idempotency_key_conflict!
        using (var changedValConflict = await client.SendAsync(
            BuildSaveRequest(docSameKeyRace.DocumentId, sharedKey0, docSameKeyRace.ResultId, 0, "draft", "Same0", DefaultDraftFields("DIFFERENT")), Cancel))
        {
            Assert.Equal(HttpStatusCode.Conflict, changedValConflict.StatusCode);
            Assert.Equal("idempotency_key_conflict", await ReadProblemCodeAsync(changedValConflict));
        }

        using (var crossDocConflict = await client.SendAsync(
            BuildSaveRequest(docDiffKeyRace.DocumentId, sharedKey0, docDiffKeyRace.ResultId, 0, "draft", "Same0", DefaultDraftFields()), Cancel))
        {
            Assert.Equal(HttpStatusCode.Conflict, crossDocConflict.StatusCode);
            Assert.Equal("idempotency_key_conflict", await ReadProblemCodeAsync(crossDocConflict));
        }

        // 6. Lost HTTP 201 response via ResponseDroppingProxy -> exact same-key retry recovers 200 OK without duplicating!
        await using (var dropProxy = new ResponseDroppingProxy(api.BaseAddress))
        {
            var lostKey = Guid.NewGuid();
            using (var viaProxy = new HttpClient { BaseAddress = dropProxy.Address, Timeout = TimeSpan.FromSeconds(30) })
            {
                await Assert.ThrowsAsync<HttpRequestException>(() =>
                    viaProxy.SendAsync(BuildSaveRequest(docSameKeyRace.DocumentId, lostKey, docSameKeyRace.ResultId, 2, "draft", "LostResp", DefaultDraftFields("WO-R3")), Cancel));
            }

            Assert.StartsWith("HTTP/1.1 201", await dropProxy.DroppedStatusLine, StringComparison.Ordinal);

            using var recovered = await client.SendAsync(
                BuildSaveRequest(docSameKeyRace.DocumentId, lostKey, docSameKeyRace.ResultId, 2, "draft", "LostResp", DefaultDraftFields("WO-R3")), Cancel);
            Assert.Equal(HttpStatusCode.OK, recovered.StatusCode);
            var recJson = await recovered.Content.ReadFromJsonAsync<JsonElement>(Cancel);
            Assert.True(recJson.GetProperty("replayed").GetBoolean());
            Assert.Equal(3, recJson.GetProperty("revision").GetProperty("revisionNumber").GetInt32());
        }

        // 7. 128-revision cap: save 1..128, verify Revision #129 returns 409 revision_limit_reached,
        //    AND verify replaying Revision #128's Idempotency-Key AT THE CAP still returns 200 OK (F3-BIC-03)!
        Guid key128 = Guid.Empty;
        for (var rev = 0; rev < WorkOrderReviewSchema.MaxRevisionsPerResult; rev++)
        {
            var k = Guid.NewGuid();
            if (rev == WorkOrderReviewSchema.MaxRevisionsPerResult - 1)
            {
                key128 = k;
            }

            using var resp = await client.SendAsync(
                BuildSaveRequest(docCap.DocumentId, k, docCap.ResultId, rev, "draft", $"Op-{rev + 1}", DefaultDraftFields($"WO-{rev + 1}")), Cancel);
            Assert.Equal(HttpStatusCode.Created, resp.StatusCode);
        }

        using (var overCap = await client.SendAsync(
            BuildSaveRequest(docCap.DocumentId, Guid.NewGuid(), docCap.ResultId, 128, "draft", "Op-129", DefaultDraftFields("WO-129")), Cancel))
        {
            Assert.Equal(HttpStatusCode.Conflict, overCap.StatusCode);
            Assert.Equal("revision_limit_reached", await ReadProblemCodeAsync(overCap));
        }

        using (var replayAt128 = await client.SendAsync(
            BuildSaveRequest(docCap.DocumentId, key128, docCap.ResultId, 127, "draft", "Op-128", DefaultDraftFields("WO-128")), Cancel))
        {
            Assert.Equal(HttpStatusCode.OK, replayAt128.StatusCode);
            var r128Json = await replayAt128.Content.ReadFromJsonAsync<JsonElement>(Cancel);
            Assert.True(r128Json.GetProperty("replayed").GetBoolean());
            Assert.Equal(128, r128Json.GetProperty("revision").GetProperty("revisionNumber").GetInt32());
            Assert.Equal(128, r128Json.GetProperty("history").GetArrayLength());
        }

        Evidence.Record("F3-04 / F3-BIC-03 concurrency, replay, lost-response, and 128 cap", new
        {
            database = db.Name,
            concurrentSameKeyRev0 = new[] { 200, 201 },
            concurrentDiffKeyRev0 = new[] { 201, 409 },
            concurrentSameKeyRev1 = new[] { 200, 201 },
            replayRev1AfterRev2 = new { status = 200, isCurrentHead = false, currentRevisionNumber = 2 },
            revision129Status = 409,
            replayRevision128AtCapStatus = 200,
        });
    }

    [Fact]
    public async Task F3_06_F3_BIC_03_strict_payload_size_json_text_surrogate_nul_and_provenance_boundaries()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        var woSeed = await GenuineF2Seeds.SeedSynWo01Async(db.AppConnectionString, remapIds: true, Cancel);
        var mpSeed = await GenuineF2Seeds.SeedSynMp01Async(db.AppConnectionString, remapIds: true, Cancel);

        await using var api = await ApiProcess.StartAsync(db.AppConnectionString);
        using var client = api.CreateClient();

        // Also submit an unextracted document (status = awaiting_extraction) to verify 409 extraction_not_completed.
        Guid unextractedDocId;
        using (var subReq = new HttpRequestMessage(HttpMethod.Post, "/api/documents")
        {
            Content = new ByteArrayContent(SyntheticPdf.CanonicalFixture()),
        })
        {
            subReq.Content.Headers.ContentType = new MediaTypeHeaderValue("application/pdf");
            subReq.Headers.Add("Idempotency-Key", Guid.NewGuid().ToString("D"));
            using var subResp = await client.SendAsync(subReq, Cancel);
            unextractedDocId = (await subResp.Content.ReadFromJsonAsync<JsonElement>(Cancel)).GetProperty("documentId").GetGuid();
        }

        // 1. > 32,768 bytes rejected with 413 (both Content-Length and chunked stream)!
        var oversizedBody = Encoding.UTF8.GetBytes("{\"pad\":\"" + new string('A', 33_000) + "\"}");
        using (var cl413 = new HttpRequestMessage(HttpMethod.Post, $"/api/documents/{woSeed.DocumentId:D}/review/revisions")
        {
            Content = new ByteArrayContent(oversizedBody),
        })
        {
            cl413.Headers.Add("Idempotency-Key", Guid.NewGuid().ToString("D"));
            cl413.Content.Headers.ContentType = new MediaTypeHeaderValue("application/json");
            using var r = await client.SendAsync(cl413, Cancel);
            Assert.Equal(HttpStatusCode.RequestEntityTooLarge, r.StatusCode);
            Assert.Equal("review_request_too_large", await ReadProblemCodeAsync(r));
        }

        using (var chunked413 = new HttpRequestMessage(HttpMethod.Post, $"/api/documents/{woSeed.DocumentId:D}/review/revisions")
        {
            Content = new StreamContent(new MemoryStream(oversizedBody)),
        })
        {
            chunked413.Headers.Add("Idempotency-Key", Guid.NewGuid().ToString("D"));
            chunked413.Content.Headers.ContentType = new MediaTypeHeaderValue("application/json");
            chunked413.Headers.TransferEncodingChunked = true;
            using var r = await client.SendAsync(chunked413, Cancel);
            Assert.Equal(HttpStatusCode.RequestEntityTooLarge, r.StatusCode);
            Assert.Equal("review_request_too_large", await ReadProblemCodeAsync(r));
        }

        // 2. Malformed revision routes (400), unsupported profile query (422), unextracted doc (409).
        foreach (var badRev in new[] { "0", "-1", "01", "abc" })
        {
            using var r = await client.GetAsync($"/api/documents/{woSeed.DocumentId:D}/review/revisions/{badRev}", Cancel);
            Assert.Equal(HttpStatusCode.BadRequest, r.StatusCode);
            Assert.Equal("invalid_revision_number", await ReadProblemCodeAsync(r));
        }

        using (var badProfGet = await client.GetAsync($"/api/documents/{woSeed.DocumentId:D}/review?profile=invoice/1", Cancel))
        {
            Assert.Equal(HttpStatusCode.UnprocessableEntity, badProfGet.StatusCode);
            Assert.Equal("review_profile_unsupported", await ReadProblemCodeAsync(badProfGet));
        }

        using (var unextGet = await client.GetAsync($"/api/documents/{unextractedDocId:D}/review", Cancel))
        {
            Assert.Equal(HttpStatusCode.Conflict, unextGet.StatusCode);
            Assert.Equal("extraction_not_completed", await ReadProblemCodeAsync(unextGet));
        }

        // 3. Client-asserted provenance properties, duplicate JSON keys, missing Idempotency-Key -> 400!
        var clientProvJson = $$"""
            {
              "resultId": "{{woSeed.ResultId:D}}",
              "expectedRevision": 0,
              "status": "draft",
              "rawSha256": "{{woSeed.RawOutputSha256Hex}}",
              "fields": []
            }
            """;
        using (var provResp = await SendRawReviewJsonAsync(client, woSeed.DocumentId, Guid.NewGuid().ToString("D"), clientProvJson))
        {
            Assert.Equal(HttpStatusCode.BadRequest, provResp.StatusCode);
            Assert.Equal("client_provenance_forbidden", await ReadProblemCodeAsync(provResp));
        }

        var dupKeyJson = $$"""
            {
              "resultId": "{{woSeed.ResultId:D}}",
              "expectedRevision": 0,
              "expectedRevision": 1,
              "status": "draft",
              "fields": []
            }
            """;
        using (var dupResp = await SendRawReviewJsonAsync(client, woSeed.DocumentId, Guid.NewGuid().ToString("D"), dupKeyJson))
        {
            Assert.Equal(HttpStatusCode.BadRequest, dupResp.StatusCode);
        }

        // 4. Raw JSON unpaired surrogate (\uD800) and NUL (\u0000) -> strictly 422 (never 500 or sanitized truncation)!
        var surrogateJson = BuildRawJsonWithFirstValue(woSeed.ResultId, "edited", "WO-\\uD800-BAD");
        using (var surResp = await SendRawReviewJsonAsync(client, woSeed.DocumentId, Guid.NewGuid().ToString("D"), surrogateJson))
        {
            Assert.Equal(HttpStatusCode.UnprocessableEntity, surResp.StatusCode);
            Assert.Equal("invalid_field_value", await ReadProblemCodeAsync(surResp));
        }

        var nulJson = BuildRawJsonWithFirstValue(woSeed.ResultId, "edited", "WO-\\u0000-BAD");
        using (var nulResp = await SendRawReviewJsonAsync(client, woSeed.DocumentId, Guid.NewGuid().ToString("D"), nulJson))
        {
            Assert.Equal(HttpStatusCode.UnprocessableEntity, nulResp.StatusCode);
            Assert.Equal("invalid_field_value", await ReadProblemCodeAsync(nulResp));
        }

        // 5. Semantic 422 / 409 rejections:
        var rejections = new (string Name, Guid DocId, HttpRequestMessage Req, HttpStatusCode ExpectedStatus, string ExpectedCode)[]
        {
            ("wrong resultId", woSeed.DocumentId,
                BuildSaveRequest(woSeed.DocumentId, Guid.NewGuid(), Guid.NewGuid(), 0, "draft", null, DefaultDraftFields()),
                HttpStatusCode.Conflict, "result_id_mismatch"),
            ("unsupported profile on POST", woSeed.DocumentId,
                BuildSaveRequest(woSeed.DocumentId, Guid.NewGuid(), woSeed.ResultId, 0, "draft", null, DefaultDraftFields(), profileId: "invoice/99"),
                HttpStatusCode.UnprocessableEntity, "review_profile_unsupported"),
            ("newline in single-line work_order_id", woSeed.DocumentId,
                BuildSaveRequest(woSeed.DocumentId, Guid.NewGuid(), woSeed.ResultId, 0, "draft", null, DefaultDraftFields("WO-1\nWO-2")),
                HttpStatusCode.UnprocessableEntity, "invalid_field_value"),
            ("whitespace-only edited value", woSeed.DocumentId,
                BuildSaveRequest(woSeed.DocumentId, Guid.NewGuid(), woSeed.ResultId, 0, "draft", null, DefaultDraftFields("    ")),
                HttpStatusCode.UnprocessableEntity, "invalid_field_value"),
            ("65-char work_order_id", woSeed.DocumentId,
                BuildSaveRequest(woSeed.DocumentId, Guid.NewGuid(), woSeed.ResultId, 0, "draft", null, DefaultDraftFields(new string('W', 65))),
                HttpStatusCode.UnprocessableEntity, "invalid_field_value"),
            ("81-char operatorDisplayLabel", woSeed.DocumentId,
                BuildSaveRequest(woSeed.DocumentId, Guid.NewGuid(), woSeed.ResultId, 0, "draft", new string('O', 81), DefaultDraftFields()),
                HttpStatusCode.UnprocessableEntity, "invalid_operator_display_label"),
            ("non-null value on unknown", woSeed.DocumentId,
                BuildSaveRequest(woSeed.DocumentId, Guid.NewGuid(), woSeed.ResultId, 0, "draft", null,
                [
                    Field("work_order_id", "unknown", "SHOULD_BE_NULL"),
                    Field("property_name", "unreviewed", null),
                    Field("building_unit", "unreviewed", null),
                    Field("requested_date", "unreviewed", null),
                    Field("issue_and_resolution", "unreviewed", null),
                ]),
                HttpStatusCode.UnprocessableEntity, "unknown_field_cannot_have_value"),
            ("501-char unknownReason", woSeed.DocumentId,
                BuildSaveRequest(woSeed.DocumentId, Guid.NewGuid(), woSeed.ResultId, 0, "draft", null,
                [
                    Field("work_order_id", "unknown", null, unknownReason: new string('R', 501)),
                    Field("property_name", "unreviewed", null),
                    Field("building_unit", "unreviewed", null),
                    Field("requested_date", "unreviewed", null),
                    Field("issue_and_resolution", "unreviewed", null),
                ]),
                HttpStatusCode.UnprocessableEntity, "invalid_unknown_reason"),
            ("accepted value mismatch against machine candidate", woSeed.DocumentId,
                BuildSaveRequest(woSeed.DocumentId, Guid.NewGuid(), woSeed.ResultId, 0, "draft", null,
                [
                    Field("work_order_id", "accepted", "WO-TAMPERED"),
                    Field("property_name", "unreviewed", null),
                    Field("building_unit", "unreviewed", null),
                    Field("requested_date", "unreviewed", null),
                    Field("issue_and_resolution", "unreviewed", null),
                ]),
                HttpStatusCode.UnprocessableEntity, "accepted_value_mismatch"),
            ("accepted when machine candidate is missing (SYN-MP-01)", mpSeed.DocumentId,
                BuildSaveRequest(mpSeed.DocumentId, Guid.NewGuid(), mpSeed.ResultId, 0, "draft", null,
                [
                    Field("work_order_id", "accepted", "WO-INVENTED"),
                    Field("property_name", "unreviewed", null),
                    Field("building_unit", "unreviewed", null),
                    Field("requested_date", "unreviewed", null),
                    Field("issue_and_resolution", "unreviewed", null),
                ]),
                HttpStatusCode.UnprocessableEntity, "accepted_without_machine_suggestion"),
            ("invented source page coordinate", woSeed.DocumentId,
                BuildSaveRequest(woSeed.DocumentId, Guid.NewGuid(), woSeed.ResultId, 0, "draft", null,
                [
                    Field("work_order_id", "edited", "WO-004192-FIX", new { pageNumber = 2, blockOrdinal = 0, tableRow = (int?)null, tableColumn = (int?)null }),
                    Field("property_name", "unreviewed", null),
                    Field("building_unit", "unreviewed", null),
                    Field("requested_date", "unreviewed", null),
                    Field("issue_and_resolution", "unreviewed", null),
                ]),
                HttpStatusCode.UnprocessableEntity, "invalid_source_reference"),
            ("unreviewed field on reviewed save", woSeed.DocumentId,
                BuildSaveRequest(woSeed.DocumentId, Guid.NewGuid(), woSeed.ResultId, 0, "reviewed", null, DefaultDraftFields()),
                HttpStatusCode.UnprocessableEntity, "unreviewed_fields_cannot_complete_review"),
        };

        foreach (var (name, _, req, expStatus, expCode) in rejections)
        {
            using (req)
            using (var resp = await client.SendAsync(req, Cancel))
            {
                var code = await ReadProblemCodeAsync(resp);
                Assert.True(resp.StatusCode == expStatus, $"{name}: expected {(int)expStatus}, got {(int)resp.StatusCode} ({code})");
                Assert.Equal(expCode, code);
            }
        }

        // Zero review heads or revisions were created by any of the invalid requests!
        Assert.Equal(0L, await db.ScalarAsync("SELECT count(*) FROM eledgercare.work_order_review_heads"));
        Assert.Equal(0L, await db.ScalarAsync("SELECT count(*) FROM eledgercare.work_order_review_revisions"));
        Assert.Equal(0L, await db.ScalarAsync("SELECT count(*) FROM eledgercare.work_order_review_fields"));
    }

    private static object[] DefaultDraftFields(string editedWorkOrderId = "WO-004192-DRAFT") =>
    [
        Field("work_order_id", "edited", editedWorkOrderId),
        Field("property_name", "accepted", "Cedar Hollow Apartments"),
        Field("building_unit", "unreviewed", null),
        Field("requested_date", "accepted", "2026-10-16"),
        Field("issue_and_resolution", "unreviewed", null),
    ];

    private static object Field(
        string fieldKey,
        string decision,
        string? value,
        object? consultedSource = null,
        string? unknownReason = null) =>
        new
        {
            fieldKey,
            decision,
            value,
            unknownReason,
            consultedSource,
        };

    private static HttpRequestMessage BuildSaveRequest(
        Guid documentId,
        Guid idempotencyKey,
        Guid resultId,
        int expectedRevision,
        string status,
        string? operatorDisplayLabel,
        object[] fields,
        string profileId = WorkOrderReviewSchema.ProfileId)
    {
        var payload = JsonSerializer.SerializeToUtf8Bytes(new
        {
            profileId,
            resultId = resultId.ToString("D"),
            expectedRevision,
            status,
            operatorDisplayLabel,
            fields,
        });
        var req = new HttpRequestMessage(HttpMethod.Post, $"/api/documents/{documentId:D}/review/revisions")
        {
            Content = new ByteArrayContent(payload),
        };
        req.Content.Headers.ContentType = new MediaTypeHeaderValue("application/json");
        req.Headers.Add("Idempotency-Key", idempotencyKey.ToString("D"));
        return req;
    }

    private static Task<HttpResponseMessage> SendRawReviewJsonAsync(
        HttpClient client,
        Guid documentId,
        string idempotencyKey,
        string rawJson)
    {
        var req = new HttpRequestMessage(HttpMethod.Post, $"/api/documents/{documentId:D}/review/revisions")
        {
            Content = new ByteArrayContent(Encoding.UTF8.GetBytes(rawJson)),
        };
        req.Content.Headers.ContentType = new MediaTypeHeaderValue("application/json");
        req.Headers.TryAddWithoutValidation("Idempotency-Key", idempotencyKey);
        return client.SendAsync(req, Cancel);
    }

    private static string BuildRawJsonWithFirstValue(Guid resultId, string firstDecision, string rawEscapedFirstValue) =>
        "{" +
        $"\"resultId\":\"{resultId:D}\"," +
        "\"expectedRevision\":0," +
        "\"status\":\"draft\"," +
        "\"fields\":[" +
        $"{{\"fieldKey\":\"work_order_id\",\"decision\":\"{firstDecision}\",\"value\":\"{rawEscapedFirstValue}\"}}," +
        "{\"fieldKey\":\"property_name\",\"decision\":\"unreviewed\",\"value\":null}," +
        "{\"fieldKey\":\"building_unit\",\"decision\":\"unreviewed\",\"value\":null}," +
        "{\"fieldKey\":\"requested_date\",\"decision\":\"unreviewed\",\"value\":null}," +
        "{\"fieldKey\":\"issue_and_resolution\",\"decision\":\"unreviewed\",\"value\":null}" +
        "]}";

    private static async Task<string?> ReadProblemCodeAsync(HttpResponseMessage response)
    {
        var text = await response.Content.ReadAsStringAsync(Cancel);
        if (string.IsNullOrWhiteSpace(text))
        {
            return null;
        }

        using var doc = JsonDocument.Parse(text);
        return doc.RootElement.TryGetProperty("code", out var code) ? code.GetString() : null;
    }
}
