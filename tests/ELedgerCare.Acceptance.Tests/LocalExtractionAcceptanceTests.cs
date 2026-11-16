using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using ELedgerCare.Acceptance.Tests.Harness;
using ELedgerCare.Application.Extraction;
using ELedgerCare.Domain.Processing;
using ELedgerCare.Infrastructure.Extraction;
using ELedgerCare.Infrastructure.Persistence;
using ELedgerCare.Tests.Shared;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql;
using Xunit;

namespace ELedgerCare.Acceptance.Tests;

/// <summary>
/// Stage 1 F2 acceptance checks against real PostgreSQL 18.7 and the real ELedgerCare.Api process.
/// Covers forward migration (F2-07), disabled-by-default and 1..3 page profile bounds (F2-06),
/// caller replay vs explicit retry and concurrent races (F2-03 / F2-BIC-03), supervisor crash/reconciliation
/// and monotonic fencing (F2-04), and atomic unreviewed result persistence + safe display reopen (F2-02 / F2-05 / F2-BIC-04).
/// </summary>
[Collection(PostgresCollection.Name)]
public sealed class LocalExtractionAcceptanceTests(PostgresFixture fixture)
{
    private static readonly TimeSpan LockWait = TimeSpan.FromSeconds(20);
    private static CancellationToken Cancel => TestContext.Current.CancellationToken;

    [Fact]
    public async Task F2_07_forward_migration_from_F1_preserves_existing_documents_bytes_and_backfills_updated_at()
    {
        var dbName = $"eledgercare_f1_fwd_{Guid.NewGuid().ToString("N")[..10]}";
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

            // Step 1: Migrate ONLY to F1's InitialDurableIntake migration.
            await using (var migDb = new ELedgerCareDbContext(migOptions))
            {
                var migrator = migDb.GetService<IMigrator>();
                await migrator.MigrateAsync("20261114182147_InitialDurableIntake", Cancel);
            }

            // Step 2: Insert an authentic F1 committed submission using only F1 columns.
            var f1DocId = Guid.NewGuid();
            var f1JobId = Guid.NewGuid();
            var f1Key = Guid.NewGuid();
            var f1Bytes = SyntheticPdf.CanonicalFixture();
            var f1Sha = SHA256.HashData(f1Bytes);
            var f1SubmittedUtc = new DateTimeOffset(2026, 11, 14, 18, 30, 0, TimeSpan.Zero);

            await using (var migConn = await PostgresFixture.OpenAsync(fixture.Settings.Migrator(dbName)))
            {
                await using var tx = await migConn.BeginTransactionAsync(Cancel);
                await using (var docCmd = new NpgsqlCommand(
                    "INSERT INTO eledgercare.documents (document_id, idempotency_key, submitted_at) VALUES (@id, @key, @ts)", migConn, tx))
                {
                    docCmd.Parameters.AddWithValue("id", f1DocId);
                    docCmd.Parameters.AddWithValue("key", f1Key);
                    docCmd.Parameters.AddWithValue("ts", f1SubmittedUtc);
                    await docCmd.ExecuteNonQueryAsync(Cancel);
                }

                await using (var artCmd = new NpgsqlCommand(
                    "INSERT INTO eledgercare.original_artifacts (document_id, bytes, sha256, byte_length, media_type, page_count) " +
                    "VALUES (@id, @bytes, @sha, @len, 'application/pdf', 1)", migConn, tx))
                {
                    artCmd.Parameters.AddWithValue("id", f1DocId);
                    artCmd.Parameters.AddWithValue("bytes", f1Bytes);
                    artCmd.Parameters.AddWithValue("sha", f1Sha);
                    artCmd.Parameters.AddWithValue("len", f1Bytes.Length);
                    await artCmd.ExecuteNonQueryAsync(Cancel);
                }

                await using (var jobCmd = new NpgsqlCommand(
                    "INSERT INTO eledgercare.processing_jobs (job_id, document_id, status, requested_at) " +
                    "VALUES (@jobId, @id, 'awaiting_extraction', @ts)", migConn, tx))
                {
                    jobCmd.Parameters.AddWithValue("jobId", f1JobId);
                    jobCmd.Parameters.AddWithValue("id", f1DocId);
                    jobCmd.Parameters.AddWithValue("ts", f1SubmittedUtc);
                    await jobCmd.ExecuteNonQueryAsync(Cancel);
                }

                await tx.CommitAsync(Cancel);
            }

            // Step 3: Migrate forward to F2 AddLocalExtraction and apply runtime grants.
            await using (var migDb2 = new ELedgerCareDbContext(migOptions))
            {
                await migDb2.Database.MigrateAsync(Cancel);
            }

            await using (var migConn2 = await PostgresFixture.OpenAsync(fixture.Settings.Migrator(dbName)))
            {
                var grants = await File.ReadAllTextAsync(Path.Combine(RepositoryPaths.Root, "deploy", "dev", "database", "grant-runtime.sql"), Cancel);
                await PostgresFixture.ExecuteAsync(migConn2, grants);

                await using var verifyCmd = new NpgsqlCommand(
                    "SELECT updated_at, attempt_count, latest_fencing_token FROM eledgercare.processing_jobs WHERE job_id = @jobId", migConn2);
                verifyCmd.Parameters.AddWithValue("jobId", f1JobId);
                await using var reader = await verifyCmd.ExecuteReaderAsync(Cancel);
                Assert.True(await reader.ReadAsync(Cancel));
                Assert.Equal(f1SubmittedUtc, reader.GetFieldValue<DateTimeOffset>(0));
                Assert.Equal(0, reader.GetInt32(1));
                Assert.Equal(0L, reader.GetInt64(2));
            }

            // Step 4: Real API serves the migrated F1 document seamlessly across F1 + F2 endpoints.
            await using var api = await ApiProcess.StartAsync(fixture.Settings.App(dbName));
            using var client = api.CreateClient();

            var docJson = await client.GetFromJsonAsync<JsonElement>($"/api/documents/{f1DocId:D}", Cancel);
            Assert.Equal(f1DocId, docJson.GetProperty("documentId").GetGuid());
            Assert.Equal("awaiting_extraction", docJson.GetProperty("status").GetString());
            Assert.Equal(1, docJson.GetProperty("admittedPageCount").GetInt32());

            var subJson = await client.GetFromJsonAsync<JsonElement>($"/api/submissions/{f1Key:D}", Cancel);
            Assert.Equal(f1DocId, subJson.GetProperty("documentId").GetGuid());

            var downloaded = await client.GetByteArrayAsync($"/api/documents/{f1DocId:D}/original", Cancel);
            Assert.Equal(f1Bytes, downloaded);

            var extJson = await client.GetFromJsonAsync<JsonElement>($"/api/documents/{f1DocId:D}/extraction", Cancel);
            Assert.Equal("awaiting_extraction", extJson.GetProperty("status").GetString());
            Assert.False(extJson.GetProperty("workerEnabled").GetBoolean());
            Assert.True(extJson.GetProperty("profileSupported").GetBoolean());
            Assert.Equal(0, extJson.GetProperty("attempts").GetArrayLength());

            Evidence.Record("F2-07 forward migration", new
            {
                database = dbName,
                f1DocumentId = f1DocId,
                backfilledUpdatedAtMatchesRequestedAt = true,
                originalBytesPreserved = true,
            });
        }
        finally
        {
            await PostgresFixture.ExecuteAsync(admin, $"DROP DATABASE IF EXISTS {dbName} WITH (FORCE)");
        }
    }

    [Fact]
    public async Task F2_06_disabled_by_default_and_unsupported_4_page_profile_fail_honestly_while_dev_fixtures_admit()
    {
        await using var db = await fixture.CreateDatabaseAsync();

        // Startup validation refuses LocalOcr:Enabled=true without runtime roots/GPU UUID, or MaxExtractionPages > 3.
        var missingRootsFailure = await Record.ExceptionAsync(() =>
            ApiProcess.StartAsync(db.AppConnectionString, new Dictionary<string, string> { ["LocalOcr__Enabled"] = "true" }));
        Assert.NotNull(missingRootsFailure);

        var badMaxPagesFailure = await Record.ExceptionAsync(() =>
            ApiProcess.StartAsync(db.AppConnectionString, new Dictionary<string, string> { ["LocalOcr__MaxExtractionPages"] = "4" }));
        Assert.NotNull(badMaxPagesFailure);

        await using var api = await ApiProcess.StartAsync(db.AppConnectionString);
        using var client = api.CreateClient();

        var f01Bytes = await File.ReadAllBytesAsync(Path.Combine(RepositoryPaths.Root, "tests", "fixtures", "SYN-WO-01-v1-raster300.pdf"), Cancel);
        var f07Bytes = await File.ReadAllBytesAsync(Path.Combine(RepositoryPaths.Root, "tests", "fixtures", "SYN-MP-01-v0-clean.pdf"), Cancel);
        var fourPageBytes = SyntheticPdf.Build(new SyntheticPdf.Spec { Pages = 4 });

        var f01DocId = await SubmitDocumentAsync(client, f01Bytes);
        var f07DocId = await SubmitDocumentAsync(client, f07Bytes);
        var fourPageDocId = await SubmitDocumentAsync(client, fourPageBytes);

        // 1-page F01 and 3-page F07 are admitted and supported by the F2 profile, but disabled by default (503).
        var f07Ext = await client.GetFromJsonAsync<JsonElement>($"/api/documents/{f07DocId:D}/extraction", Cancel);
        Assert.Equal(3, f07Ext.GetProperty("admittedPageCount").GetInt32());
        Assert.True(f07Ext.GetProperty("profileSupported").GetBoolean());
        Assert.False(f07Ext.GetProperty("workerEnabled").GetBoolean());
        Assert.False(f07Ext.GetProperty("canRequestExtraction").GetBoolean());

        using (var postDisabled = await client.PostAsync($"/api/documents/{f01DocId:D}/extraction", content: null, Cancel))
        {
            Assert.Equal(HttpStatusCode.ServiceUnavailable, postDisabled.StatusCode);
            Assert.Equal("extraction_disabled", await ReadProblemCodeAsync(postDisabled));
        }

        // 4-page PDF is admitted at intake (201), but outside the 1..3 page F2 profile (422 extraction_profile_unsupported).
        var fourExt = await client.GetFromJsonAsync<JsonElement>($"/api/documents/{fourPageDocId:D}/extraction", Cancel);
        Assert.Equal(4, fourExt.GetProperty("admittedPageCount").GetInt32());
        Assert.False(fourExt.GetProperty("profileSupported").GetBoolean());

        using (var postUnsupported = await client.PostAsync($"/api/documents/{fourPageDocId:D}/extraction", content: null, Cancel))
        {
            Assert.Equal(HttpStatusCode.UnprocessableEntity, postUnsupported.StatusCode);
            Assert.Equal("extraction_profile_unsupported", await ReadProblemCodeAsync(postUnsupported));
        }

        Assert.Equal(0L, await db.ScalarAsync("SELECT count(*) FROM eledgercare.execution_attempts"));
        Assert.Equal(0L, await db.ScalarAsync("SELECT count(*) FROM eledgercare.extraction_results"));
        Assert.Equal(3L, await db.ScalarAsync("SELECT count(*) FROM eledgercare.processing_jobs WHERE status = 'awaiting_extraction'"));

        Evidence.Record("F2-06 profile and disabled default", new
        {
            database = db.Name,
            f01Pages = 1,
            f07Pages = 3,
            disabledPostStatus = 503,
            fourPagePostStatus = 422,
            attemptsCreated = 0,
        });
    }

    [Fact]
    public async Task F2_03_F2_04_F2_BIC_03_queued_survival_caller_replay_guard_and_concurrent_retry_reconciliation()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        var dummyQ0 = Path.Combine(Path.GetTempPath(), $"elc-dummy-q0-{Guid.NewGuid():N}");
        var dummyRuntime = Path.Combine(Path.GetTempPath(), $"elc-dummy-rt-{Guid.NewGuid():N}");
        Directory.CreateDirectory(dummyQ0);
        Directory.CreateDirectory(dummyRuntime);

        try
        {
            var enabledSettings = new Dictionary<string, string>
            {
                ["LocalOcr__Enabled"] = "true",
                ["LocalOcr__ReadOnlyQ0Root"] = dummyQ0,
                ["LocalOcr__WritableRuntimeRoot"] = dummyRuntime,
                ["LocalOcr__LeasedGpuUuid"] = "GPU-00000000-0000-0000-0000-000000000000",
            };

            Guid docId;
            // Hold SHARE lock on execution_attempts so ClaimNextQueuedJobAsync cannot commit a claim while we test
            // concurrent initial POST /extraction and abrupt supervisor crash with a queued job!
            await using (var adminLockConn = await db.OpenAdminAsync())
            {
                await using var lockTx = await adminLockConn.BeginTransactionAsync(Cancel);
                await using (var lockCmd = new NpgsqlCommand("LOCK TABLE eledgercare.execution_attempts IN SHARE MODE", adminLockConn, lockTx))
                {
                    await lockCmd.ExecuteNonQueryAsync(Cancel);
                }

                await using (var api = await ApiProcess.StartAsync(db.AppConnectionString, enabledSettings))
                {
                    using var client = api.CreateClient();
                    docId = await SubmitDocumentAsync(client, SyntheticPdf.CanonicalFixture());

                    // Concurrent initial POST /extraction race: both reconcile to 202 Accepted for the single job.
                    var reqA = client.PostAsync($"/api/documents/{docId:D}/extraction", content: null, Cancel);
                    var reqB = client.PostAsync($"/api/documents/{docId:D}/extraction", content: null, Cancel);
                    var initialResponses = await Task.WhenAll(reqA, reqB);
                    Assert.All(initialResponses, r => Assert.Equal(HttpStatusCode.Accepted, r.StatusCode));
                    foreach (var r in initialResponses)
                    {
                        r.Dispose();
                    }

                    Assert.Equal("queued", await ScalarTextAsync(db, "SELECT status FROM eledgercare.processing_jobs WHERE document_id = @id", ("id", docId)));

                    // Abruptly kill the API process; any blocked uncommitted claim rolls back, preserving 'queued' state!
                    await api.KillAsync();
                }

                await lockTx.RollbackAsync(Cancel);
            }

            // Queued job survived the abrupt API termination with 0 attempts.
            Assert.Equal("queued", await ScalarTextAsync(db, "SELECT status FROM eledgercare.processing_jobs WHERE document_id = @id", ("id", docId)));
            Assert.Equal(0L, await db.ScalarAsync("SELECT count(*) FROM eledgercare.execution_attempts"));

            // Now transition Attempt #1 through claim -> failed via real ExtractionStore on eledgercare_app,
            // then test HTTP replay rejection (409 retry_explicit_required), stale retry rejection (409 stale_retry_target),
            // and concurrent explicit retry reconciliation over the real API!
            var store = CreateAppExtractionStore(db.AppConnectionString);
            var now = ExtractionAttemptCoordinator.TruncateToMicroseconds(DateTimeOffset.UtcNow);
            var claimed1 = await store.ClaimNextQueuedJobAsync(Guid.NewGuid(), 12345, 133700000000000001L, now, Cancel);
            Assert.NotNull(claimed1);
            Assert.Equal(1, claimed1.AttemptNumber);
            Assert.True(await store.MarkAttemptFailedAsync(
                claimed1.AttemptId, claimed1.JobId, claimed1.FencingToken,
                "worker_timeout", "Simulated timeout for explicit retry verification.",
                exitCode: 1, diagnosticRawOutputUtf8: null, diagnosticMetadataJson: "{}", now.AddSeconds(5), Cancel));

            await using (var adminLockConn2 = await db.OpenAdminAsync())
            {
                await using var lockTx2 = await adminLockConn2.BeginTransactionAsync(Cancel);
                await using (var lockCmd2 = new NpgsqlCommand("LOCK TABLE eledgercare.execution_attempts IN SHARE MODE", adminLockConn2, lockTx2))
                {
                    await lockCmd2.ExecuteNonQueryAsync(Cancel);
                }

                await using var api2 = await ApiProcess.StartAsync(db.AppConnectionString, enabledSettings);
                using var client2 = api2.CreateClient();

                // 1. Empty-body caller replay MUST NOT retry a failed attempt!
                using (var replayResp = await client2.PostAsync($"/api/documents/{docId:D}/extraction", content: null, Cancel))
                {
                    Assert.Equal(HttpStatusCode.Conflict, replayResp.StatusCode);
                    Assert.Equal("retry_explicit_required", await ReadProblemCodeAsync(replayResp));
                }

                // 2. Wrong/stale retryAttemptId is rejected with 409 stale_retry_target.
                using (var staleResp = await client2.PostAsJsonAsync(
                    $"/api/documents/{docId:D}/extraction",
                    new { retryAttemptId = Guid.NewGuid().ToString("D") },
                    Cancel))
                {
                    Assert.Equal(HttpStatusCode.Conflict, staleResp.StatusCode);
                    Assert.Equal("stale_retry_target", await ReadProblemCodeAsync(staleResp));
                }

                // 3. Concurrent explicit retry requests naming Attempt #1 reconcile to 202 Accepted without duplicating!
                var retryPayload = new { retryAttemptId = claimed1.AttemptId.ToString("D") };
                var retryA = client2.PostAsJsonAsync($"/api/documents/{docId:D}/extraction", retryPayload, Cancel);
                var retryB = client2.PostAsJsonAsync($"/api/documents/{docId:D}/extraction", retryPayload, Cancel);
                var retryResponses = await Task.WhenAll(retryA, retryB);
                Assert.All(retryResponses, r => Assert.Equal(HttpStatusCode.Accepted, r.StatusCode));
                foreach (var r in retryResponses)
                {
                    r.Dispose();
                }

                Assert.Equal("queued", await ScalarTextAsync(db, "SELECT status FROM eledgercare.processing_jobs WHERE document_id = @id", ("id", docId)));
                Assert.Equal(1L, await db.ScalarAsync("SELECT count(*) FROM eledgercare.execution_attempts"));

                await api2.KillAsync();
                await lockTx2.RollbackAsync(Cancel);
            }

            Evidence.Record("F2-03/F2-BIC-03 replay and retry", new
            {
                database = db.Name,
                documentId = docId,
                attempt1Id = claimed1.AttemptId,
                queuedSurvivedApiCrash = true,
                emptyReplayOnFailedStatus = 409,
                staleRetryTargetStatus = 409,
                concurrentExplicitRetryStatuses = new[] { 202, 202 },
            });
        }
        finally
        {
            try { Directory.Delete(dummyQ0, recursive: true); } catch { /* best effort */ }
            try { Directory.Delete(dummyRuntime, recursive: true); } catch { /* best effort */ }
        }
    }

    [Fact]
    public async Task F2_02_F2_04_F2_05_fencing_live_owner_protection_atomic_3_page_completion_and_reopen_after_restart()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        var f07Bytes = await File.ReadAllBytesAsync(Path.Combine(RepositoryPaths.Root, "tests", "fixtures", "SYN-MP-01-v0-clean.pdf"), Cancel);
        Guid docId;

        await using (var intakeApi = await ApiProcess.StartAsync(db.AppConnectionString))
        {
            using var intakeClient = intakeApi.CreateClient();
            docId = await SubmitDocumentAsync(intakeClient, f07Bytes);
        }

        var store = CreateAppExtractionStore(db.AppConnectionString);
        var settings = CreateEnabledTestSettings();
        var t0 = new DateTimeOffset(2026, 11, 16, 6, 0, 0, TimeSpan.Zero);

        // Queue initial extraction on the 3-page F07 document.
        var queued = await store.QueueOrReconcileAsync(docId, retryAttemptId: null, maxExtractionPages: 3, workerEnabled: true, t0, Cancel);
        Assert.IsType<QueueExtractionOutcome.QueuedOrActive>(queued);

        // --- Attempt #1: Claimed by Supervisor A ---
        var fakeProbe = new FakeProcessIdentityProbe(current: new OsProcessIdentity(9001, 133700000000009001L));
        fakeProbe.SetAlive(9001, 133700000000009001L, alive: true);
        var claimed1 = await store.ClaimNextQueuedJobAsync(Guid.NewGuid(), 9001, 133700000000009001L, t0.AddSeconds(1), Cancel);
        Assert.NotNull(claimed1);
        Assert.Equal(1, claimed1.AttemptNumber);
        Assert.Equal(3, claimed1.PageCount);
        Assert.True(await store.RecordHeartbeatAsync(claimed1.AttemptId, claimed1.FencingToken, "inferring", 9002, 133700000000009002L, t0.AddSeconds(2), Cancel));
        fakeProbe.SetAlive(9002, 133700000000009002L, alive: true);

        // Supervisor B starts while Supervisor A is STILL ALIVE: must NOT steal or mark Attempt #1 interrupted!
        fakeProbe.Current = new OsProcessIdentity(9100, 133700000000009100L);
        fakeProbe.SetAlive(9100, 133700000000009100L, alive: true);
        var stubRunner = new ScriptedWorkerRunner();
        var coordinatorB = new ExtractionAttemptCoordinator(store, stubRunner, fakeProbe, settings, TimeProvider.System);

        Assert.Equal(0, await coordinatorB.ReconcileAbandonedAttemptsAsync(Cancel));
        Assert.Equal("running", await ScalarTextAsync(db, "SELECT status FROM eledgercare.execution_attempts WHERE attempt_id = @id", ("id", claimed1.AttemptId)));

        // Supervisor A dies, but child worker (9002) is STILL ALIVE: must NOT mark interrupted until worker also exits!
        fakeProbe.SetAlive(9001, 133700000000009001L, alive: false);
        Assert.Equal(0, await coordinatorB.ReconcileAbandonedAttemptsAsync(Cancel));

        // Now child worker (9002) exits: Supervisor B reconciles Attempt #1 to 'interrupted'.
        fakeProbe.SetAlive(9002, 133700000000009002L, alive: false);
        Assert.Equal(1, await coordinatorB.ReconcileAbandonedAttemptsAsync(Cancel));
        Assert.Equal("interrupted", await ScalarTextAsync(db, "SELECT status FROM eledgercare.processing_jobs WHERE document_id = @id", ("id", docId)));
        Assert.Equal("interrupted", await ScalarTextAsync(db, "SELECT status FROM eledgercare.execution_attempts WHERE attempt_id = @id", ("id", claimed1.AttemptId)));

        // --- Attempt #2: Explicit retry, fencing check against stale Attempt #1 token, and truncated output rejection ---
        var retry2 = await store.QueueOrReconcileAsync(docId, claimed1.AttemptId, maxExtractionPages: 3, workerEnabled: true, t0.AddSeconds(10), Cancel);
        Assert.IsType<QueueExtractionOutcome.QueuedOrActive>(retry2);

        const string native3Pages =
            "<PAGE>\n<BLOCK>title[[50,40,400,65]]<FORK>WORK PACKET SYN-MP-01 (PAGE 1)\n" +
            "<BLOCK>text[[50,80,500,100]]<FORK>Hostile literal check: <script>window.__f2_xss=1</script>\n" +
            "<PAGE>\n<BLOCK>table[[50,120,700,260]]<FORK><table><tr><th>Step</th><th>Detail</th></tr>" +
            "<tr><td>1</td><td>Torque &amp; Verify <img src=x onerror=\"window.__f2_xss=2\"></td></tr></table>\n" +
            "<PAGE>\n<BLOCK>text[[50,120,450,145]]<FORK>Page 3 Sign-off: Unreviewed Raw Output\n";
        var raw3PageBytes = Encoding.UTF8.GetBytes(native3Pages);

        // Configure Attempt #2 to return finish_reason='length' (truncated), while ALSO testing stale token=1 writes mid-flight!
        stubRunner.NextHandler = async (work, onLauncher, onHeartbeat) =>
        {
            Assert.Equal(2, work.AttemptNumber);
            Assert.True(work.FencingToken > claimed1.FencingToken);
            Assert.True(await onLauncher(9201, 133700000000009201L, Cancel));
            Assert.True(await onHeartbeat("inferring", 9202, 133700000000009202L, Cancel));

            // Stale writes carrying Attempt #1's fencing token are fenced out completely!
            Assert.False(await store.RecordHeartbeatAsync(claimed1.AttemptId, claimed1.FencingToken, "zombie", 9002, 133700000000009002L, DateTimeOffset.UtcNow, Cancel));
            Assert.False(await store.MarkAttemptFailedAsync(claimed1.AttemptId, claimed1.JobId, claimed1.FencingToken, "zombie", "stale", 1, null, null, DateTimeOffset.UtcNow, Cancel));
            var staleResult = BuildAcceptedDomainResult(claimed1, settings, raw3PageBytes);
            Assert.False(await store.PublishCompletedResultAsync(staleResult, 0, DateTimeOffset.UtcNow, Cancel));

            var truncatedEnvelope = BuildEnvelopeJson(work, settings, raw3PageBytes, finishReason: "length");
            return new WorkerRunOutcome(truncatedEnvelope, raw3PageBytes, ExitCode: 0, null, null);
        };

        Assert.True(await coordinatorB.ExecuteNextQueuedAttemptAsync(Cancel));
        Assert.Equal("failed", await ScalarTextAsync(db, "SELECT status FROM eledgercare.processing_jobs WHERE document_id = @id", ("id", docId)));
        Assert.Equal(0L, await db.ScalarAsync("SELECT count(*) FROM eledgercare.extraction_results"));
        var attempt2Id = Guid.Parse(await ScalarTextAsync(db, "SELECT attempt_id::text FROM eledgercare.execution_attempts WHERE attempt_number = 2 AND document_id = @id", ("id", docId)));
        Assert.Equal("model_output_truncated", await ScalarTextAsync(db, "SELECT failure_code FROM eledgercare.execution_attempts WHERE attempt_id = @id", ("id", attempt2Id)));

        // --- Attempt #3: Explicit retry of Attempt #2 -> valid 3-page envelope -> atomic completed result ---
        var retry3 = await store.QueueOrReconcileAsync(docId, attempt2Id, maxExtractionPages: 3, workerEnabled: true, t0.AddSeconds(20), Cancel);
        Assert.IsType<QueueExtractionOutcome.QueuedOrActive>(retry3);

        stubRunner.NextHandler = async (work, onLauncher, onHeartbeat) =>
        {
            Assert.Equal(3, work.AttemptNumber);
            Assert.True(await onLauncher(9301, 133700000000009301L, Cancel));
            Assert.True(await onHeartbeat("inferring", 9302, 133700000000009302L, Cancel));
            var validEnvelope = BuildEnvelopeJson(work, settings, raw3PageBytes, finishReason: "stop");
            return new WorkerRunOutcome(validEnvelope, raw3PageBytes, ExitCode: 0, null, null);
        };

        Assert.True(await coordinatorB.ExecuteNextQueuedAttemptAsync(Cancel));
        Assert.Equal("completed", await ScalarTextAsync(db, "SELECT status FROM eledgercare.processing_jobs WHERE document_id = @id", ("id", docId)));
        Assert.Equal(3L, await db.ScalarAsync("SELECT count(*) FROM eledgercare.execution_attempts WHERE document_id = @id", ("id", docId)));
        Assert.Equal(1L, await db.ScalarAsync("SELECT count(*) FROM eledgercare.extraction_results WHERE document_id = @id", ("id", docId)));

        // --- Reopen over real HTTP API with LocalOcr:Enabled=false across API process restart ---
        int firstApiPid;
        await using (var api1 = await ApiProcess.StartAsync(db.AppConnectionString))
        {
            firstApiPid = api1.Pid;
            using var client1 = api1.CreateClient();

            // Completed replay POST returns 200 OK even while worker execution is disabled!
            using var replayCompleted = await client1.PostAsync($"/api/documents/{docId:D}/extraction", content: null, Cancel);
            Assert.Equal(HttpStatusCode.OK, replayCompleted.StatusCode);

            // Explicit retry of a completed document is rejected with 409 extraction_already_completed.
            using var retryCompleted = await client1.PostAsJsonAsync(
                $"/api/documents/{docId:D}/extraction",
                new { retryAttemptId = attempt2Id.ToString("D") },
                Cancel);
            Assert.Equal(HttpStatusCode.Conflict, retryCompleted.StatusCode);
            Assert.Equal("extraction_already_completed", await ReadProblemCodeAsync(retryCompleted));

            await api1.KillAsync();
        }

        await using var api2 = await ApiProcess.StartAsync(db.AppConnectionString);
        Assert.NotEqual(firstApiPid, api2.Pid);
        using var client2 = api2.CreateClient();

        var extView = await client2.GetFromJsonAsync<JsonElement>($"/api/documents/{docId:D}/extraction", Cancel);
        Assert.Equal("completed", extView.GetProperty("status").GetString());
        Assert.False(extView.GetProperty("workerEnabled").GetBoolean());
        Assert.Equal(3, extView.GetProperty("attempts").GetArrayLength());

        var res = extView.GetProperty("result");
        Assert.Equal("unreviewed", res.GetProperty("reviewStatus").GetString());
        Assert.Equal(3, res.GetProperty("pageCount").GetInt32());
        Assert.Equal(Convert.ToHexStringLower(SHA256.HashData(raw3PageBytes)), res.GetProperty("rawSha256").GetString());
        Assert.Equal(native3Pages, res.GetProperty("rawText").GetString());
        Assert.Equal(ExtractionCeilings.ModelRepoId, res.GetProperty("provenance").GetProperty("modelRepoId").GetString());
        Assert.Equal(ExtractionCeilings.ModelRevision, res.GetProperty("provenance").GetProperty("modelRevision").GetString());

        var pages = res.GetProperty("pages").EnumerateArray().ToArray();
        Assert.Equal(3, pages.Length);
        Assert.Equal([1, 2, 3], pages.Select(p => p.GetProperty("pageNumber").GetInt32()).ToArray());
        Assert.Contains("<script>window.__f2_xss=1</script>", pages[0].GetProperty("blocks")[1].GetProperty("text").GetString(), StringComparison.Ordinal);
        var row1Cells = pages[1].GetProperty("blocks")[0].GetProperty("tableRows")[1].EnumerateArray().Select(c => c.GetString()).ToArray();
        Assert.Equal("Torque & Verify <img src=x onerror=\"window.__f2_xss=2\">", row1Cells[1]);

        var downloadedAfter = await client2.GetByteArrayAsync($"/api/documents/{docId:D}/original", Cancel);
        Assert.Equal(f07Bytes, downloadedAfter);

        Evidence.Record("F2-02/04/05 coordinator fencing and 3-page reopen", new
        {
            database = db.Name,
            documentId = docId,
            attemptsRecorded = new[] { "1:interrupted", "2:failed(model_output_truncated)", "3:completed" },
            staleFencingWritesRejected = true,
            reopenedAcrossApiRestartWithWorkerDisabled = true,
            originalSha256Preserved = Convert.ToHexStringLower(SHA256.HashData(downloadedAfter)),
        });
    }

    private static ExtractionStore CreateAppExtractionStore(string appConnectionString)
    {
        var options = new DbContextOptionsBuilder<ELedgerCareDbContext>()
            .UseNpgsql(appConnectionString)
            .Options;
        return new ExtractionStore(new PooledDbContextFactory<ELedgerCareDbContext>(options));
    }

    private static ExtractionSettings CreateEnabledTestSettings()
    {
        var workerRoot = Path.Combine(RepositoryPaths.Root, "workers", "local_ocr");
        var manifestSha = SHA256.HashData(File.ReadAllBytes(Path.Combine(workerRoot, "manifests", "model-files.json")));
        var lockSha = SHA256.HashData(File.ReadAllBytes(Path.Combine(workerRoot, "manifests", "dependency-lock.json")));
        var workerSha = ExtractionSettings.ComputeWorkerSourceSha256(workerRoot);
        return new ExtractionSettings(
            enabled: true,
            maxExtractionPages: 3,
            readOnlyQ0Root: Path.GetTempPath(),
            writableRuntimeRoot: Path.GetTempPath(),
            leasedGpuUuid: "GPU-00000000-0000-0000-0000-000000000000",
            workerRootPath: workerRoot,
            modelManifestSha256: manifestSha,
            dependencyLockSha256: lockSha,
            workerSourceSha256: workerSha);
    }

    private static byte[] BuildEnvelopeJson(
        ClaimedAttemptWork work,
        ExtractionSettings settings,
        byte[] rawBytes,
        string finishReason)
    {
        var configSha = ExtractionSettings.ComputeWorkerConfigSha256(work.PageCount);
        var payload = new
        {
            schema = ExtractionCeilings.EnvelopeSchema,
            status = "completed",
            document_id = work.DocumentId.ToString("D"),
            job_id = work.JobId.ToString("D"),
            attempt_id = work.AttemptId.ToString("D"),
            fencing_token = work.FencingToken,
            input = new
            {
                sha256 = Convert.ToHexStringLower(work.InputSha256),
                byte_length = work.InputByteLength,
                page_count = work.PageCount,
            },
            provenance = new
            {
                model_repo_id = ExtractionCeilings.ModelRepoId,
                model_revision = ExtractionCeilings.ModelRevision,
                model_manifest_sha256 = Convert.ToHexStringLower(settings.ModelManifestSha256),
                dependency_lock_sha256 = Convert.ToHexStringLower(settings.DependencyLockSha256),
                worker_source_sha256 = Convert.ToHexStringLower(settings.WorkerSourceSha256),
                worker_config_sha256 = Convert.ToHexStringLower(configSha),
                renderer_identity = "pypdfium2==5.15.2 (PDFium 159.0.8149.0)",
                provenance_exceptions = new[] { ExtractionCeilings.RequiredProvenanceException },
                generation_settings = new { temperature = 0.0, max_new_tokens = 8000 * work.PageCount },
            },
            output = new
            {
                finish_reason = finishReason,
                output_page_count = work.PageCount,
                byte_length = rawBytes.Length,
                sha256 = Convert.ToHexStringLower(SHA256.HashData(rawBytes)),
            },
            timings = new
            {
                started_at_utc = "2026-11-16T06:00:00Z",
                completed_at_utc = "2026-11-16T06:00:05Z",
                load_duration_ms = 1000L,
                render_duration_ms = 90L,
                infer_duration_ms = 3910L,
                total_duration_ms = 5000L,
            },
            diagnostics = new { fallback_used = false, forward_progress = 64 },
        };
        return JsonSerializer.SerializeToUtf8Bytes(payload);
    }

    private static ExtractionResult BuildAcceptedDomainResult(
        ClaimedAttemptWork work,
        ExtractionSettings settings,
        byte[] rawBytes)
    {
        var env = BuildEnvelopeJson(work, settings, rawBytes, "stop");
        var validated = Assert.IsType<EnvelopeValidationOutcome.Accepted>(
            WorkerEnvelopeValidator.Validate(work, settings, new WorkerRunOutcome(env, rawBytes, 0, null, null), DateTimeOffset.UtcNow));
        return validated.Result;
    }

    private static async Task<Guid> SubmitDocumentAsync(HttpClient client, byte[] pdfBytes)
    {
        using var req = new HttpRequestMessage(HttpMethod.Post, "/api/documents")
        {
            Content = new ByteArrayContent(pdfBytes),
        };
        req.Content.Headers.ContentType = new MediaTypeHeaderValue("application/pdf");
        req.Headers.Add("Idempotency-Key", Guid.NewGuid().ToString("D"));
        using var resp = await client.SendAsync(req, Cancel);
        Assert.Equal(HttpStatusCode.Created, resp.StatusCode);
        var json = await resp.Content.ReadFromJsonAsync<JsonElement>(Cancel);
        return json.GetProperty("documentId").GetGuid();
    }

    private static async Task<string?> ReadProblemCodeAsync(HttpResponseMessage response)
    {
        var body = await response.Content.ReadAsStringAsync(Cancel);
        if (string.IsNullOrWhiteSpace(body))
        {
            return null;
        }

        using var doc = JsonDocument.Parse(body);
        return doc.RootElement.TryGetProperty("code", out var c) ? c.GetString() : null;
    }

    private static async Task<string> ScalarTextAsync(TestDatabase db, string sql, params (string Name, object Value)[] parameters)
    {
        await using var conn = await db.OpenAdminAsync();
        await using var cmd = new NpgsqlCommand(sql, conn);
        foreach (var (name, val) in parameters)
        {
            cmd.Parameters.AddWithValue(name, val);
        }

        return (string)(await cmd.ExecuteScalarAsync(Cancel))!;
    }

    private sealed class FakeProcessIdentityProbe(OsProcessIdentity current) : IProcessIdentityProbe
    {
        private readonly HashSet<OsProcessIdentity> live = [];

        public OsProcessIdentity Current { get; set; } = current;

        public void SetAlive(int pid, long createFileTime, bool alive)
        {
            var id = new OsProcessIdentity(pid, createFileTime);
            if (alive)
            {
                live.Add(id);
            }
            else
            {
                live.Remove(id);
            }
        }

        public OsProcessIdentity GetCurrentProcessIdentity() => Current;

        public bool IsProcessAlive(int pid, long expectedCreateFileTime) =>
            live.Contains(new OsProcessIdentity(pid, expectedCreateFileTime));
    }

    private sealed class ScriptedWorkerRunner : ILocalOcrWorkerRunner
    {
        public Func<
            ClaimedAttemptWork,
            Func<int, long, CancellationToken, Task<bool>>,
            Func<string, int?, long?, CancellationToken, Task<bool>>,
            Task<WorkerRunOutcome>>? NextHandler { get; set; }

        public OsProcessIdentity? TryReadRecordedWorkerIdentity(string runDirectoryName) => null;

        public Task<WorkerRunOutcome> ExecuteAttemptAsync(
            ClaimedAttemptWork work,
            Func<int, long, CancellationToken, Task<bool>> onLauncherAssignedBeforeResumeAsync,
            Func<string, int?, long?, CancellationToken, Task<bool>> onHeartbeatAsync,
            CancellationToken cancellationToken) =>
            NextHandler is not null
                ? NextHandler(work, onLauncherAssignedBeforeResumeAsync, onHeartbeatAsync)
                : throw new InvalidOperationException("No NextHandler configured.");
    }
}
