using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text.Json;
using ELedgerCare.Acceptance.Tests.Harness;
using ELedgerCare.Tests.Shared;
using Npgsql;
using Xunit;

namespace ELedgerCare.Acceptance.Tests;

/// <summary>
/// F1 acceptance checks against a real PostgreSQL 18.7 database and the real API process over HTTP.
/// Every test owns a fresh database cloned from the migrated template and its own API process.
/// </summary>
[Collection(PostgresCollection.Name)]
public sealed class DurableIntakeTests(PostgresFixture fixture)
{
    private static readonly byte[] FixturePdf = SyntheticPdf.CanonicalFixture();
    private static readonly TimeSpan LockWait = TimeSpan.FromSeconds(20);

    private static CancellationToken Cancel => TestContext.Current.CancellationToken;

    [Fact]
    public async Task DI01_DI02_DI03_receipt_after_commit_exact_original_and_honest_status()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        await using var api = await ApiProcess.StartAsync(db.AppConnectionString);
        using var client = api.CreateClient();
        var key = Guid.NewGuid();

        using var response = await client.SendAsync(Submit(key, FixturePdf), Cancel);

        // DI-01: 201 only after commit - a separate session sees all three committed rows immediately.
        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        var receipt = await ReadReceiptAsync(response);
        Assert.Equal($"/api/documents/{receipt.DocumentId:D}", response.Headers.Location?.OriginalString);
        Assert.Equal((1L, 1L, 1L), await db.CountRowsAsync());
        Assert.Equal(1L, await db.ScalarAsync(
            "SELECT count(*) FROM eledgercare.documents d JOIN eledgercare.original_artifacts a USING (document_id) " +
            "JOIN eledgercare.processing_jobs j USING (document_id) WHERE d.idempotency_key = @key AND d.document_id = @id AND j.job_id = @job",
            ("key", key), ("id", receipt.DocumentId), ("job", receipt.JobId)));

        // DI-02: exact bytes plus independently recomputed SHA-256 and length.
        var expectedSha = Convert.ToHexStringLower(SHA256.HashData(FixturePdf));
        Assert.Equal(FixturePdf.Length, receipt.ByteLength);
        Assert.Equal(expectedSha, receipt.Sha256);
        using var download = await client.GetAsync(receipt.OriginalUrl, Cancel);
        Assert.Equal(HttpStatusCode.OK, download.StatusCode);
        var downloaded = await download.Content.ReadAsByteArrayAsync(Cancel);
        Assert.Equal(FixturePdf, downloaded);
        Assert.Equal(expectedSha, Convert.ToHexStringLower(SHA256.HashData(downloaded)));
        Assert.Equal(FixturePdf.Length, download.Content.Headers.ContentLength);
        Assert.Equal("application/pdf", download.Content.Headers.ContentType?.MediaType);
        Assert.Equal("attachment", download.Content.Headers.ContentDisposition?.DispositionType);
        Assert.Equal($"document-{receipt.DocumentId:D}.pdf", download.Content.Headers.ContentDisposition?.FileName?.Trim('"'));
        Assert.Equal("nosniff", string.Join(',', download.Headers.GetValues("X-Content-Type-Options")));

        // DI-03: persisted awaiting_extraction in database, API and key reconciliation; no extraction state exists.
        Assert.Equal("awaiting_extraction", receipt.Status);
        Assert.Equal(1L, await db.ScalarAsync("SELECT count(*) FROM eledgercare.processing_jobs WHERE status = 'awaiting_extraction'"));
        var byDocument = await client.GetFromJsonAsync<Receipt>($"/api/documents/{receipt.DocumentId:D}", Cancel);
        var byKey = await client.GetFromJsonAsync<Receipt>($"/api/submissions/{key:D}", Cancel);
        Assert.Equal(receipt, byDocument);
        Assert.Equal(receipt, byKey);
        var receiptJson = JsonDocument.Parse(await response.Content.ReadAsStringAsync(Cancel)).RootElement;
        Assert.Equal(
            ["byteLength", "documentId", "jobId", "originalUrl", "sha256", "status", "submittedAtUtc"],
            receiptJson.EnumerateObject().Select(p => p.Name).Order(StringComparer.Ordinal).ToArray());

        Evidence.Record("DI-01/02/03", new
        {
            apiPid = api.Pid,
            apiStartUtc = api.StartTimeUtc,
            database = db.Name,
            status = (int)response.StatusCode,
            receipt.DocumentId,
            receipt.JobId,
            receipt.Status,
            receipt.ByteLength,
            receipt.Sha256,
            downloadedSha256 = Convert.ToHexStringLower(SHA256.HashData(downloaded)),
            byteForByteEqual = FixturePdf.AsSpan().SequenceEqual(downloaded),
        });
    }

    [Fact]
    public async Task DI04_restart_of_the_api_process_returns_same_reference_bytes_and_status()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        var key = Guid.NewGuid();
        Receipt before;
        int firstPid;
        DateTime firstStart;

        await using (var first = await ApiProcess.StartAsync(db.AppConnectionString))
        {
            using var client = first.CreateClient();
            using var response = await client.SendAsync(Submit(key, FixturePdf), Cancel);
            Assert.Equal(HttpStatusCode.Created, response.StatusCode);
            before = await ReadReceiptAsync(response);
            firstPid = first.Pid;
            firstStart = first.StartTimeUtc;
            await first.KillAsync();
            Assert.True(first.HasExited);
        }

        await using var second = await ApiProcess.StartAsync(db.AppConnectionString);
        Assert.NotEqual(firstPid, second.Pid);
        using var after = second.CreateClient();
        var byDocument = await after.GetFromJsonAsync<Receipt>($"/api/documents/{before.DocumentId:D}", Cancel);
        var byKey = await after.GetFromJsonAsync<Receipt>($"/api/submissions/{key:D}", Cancel);
        var bytes = await after.GetByteArrayAsync(before.OriginalUrl, Cancel);

        Assert.Equal(before, byDocument);
        Assert.Equal(before, byKey);
        Assert.Equal(FixturePdf, bytes);
        Assert.Equal("awaiting_extraction", byDocument!.Status);

        Evidence.Record("DI-04", new
        {
            database = db.Name,
            firstApi = new { pid = firstPid, startUtc = firstStart, termination = "TerminateProcess (abrupt) on verified PID/start time" },
            secondApi = new { pid = second.Pid, startUtc = second.StartTimeUtc },
            before.DocumentId,
            before.JobId,
            sha256AfterRestart = Convert.ToHexStringLower(SHA256.HashData(bytes)),
            statusAfterRestart = byDocument.Status,
            boundary = "API process restart only; same PostgreSQL cluster kept running",
        });
    }

    [Fact]
    public async Task DI05_partial_body_disconnect_creates_no_rows_and_same_key_retry_succeeds()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        await using var api = await ApiProcess.StartAsync(db.AppConnectionString);
        using var client = api.CreateClient();
        var key = Guid.NewGuid();

        await RawHttp.SendPartialBodyAndDisconnectAsync(api.BaseAddress, key, FixturePdf.Length, FixturePdf[..(FixturePdf.Length / 2)]);
        await Task.Delay(500, Cancel);

        Assert.Equal((0L, 0L, 0L), await db.CountRowsAsync());
        using var lookup = await client.GetAsync($"/api/submissions/{key:D}", Cancel);
        Assert.Equal(HttpStatusCode.NotFound, lookup.StatusCode);

        using var retry = await client.SendAsync(Submit(key, FixturePdf), Cancel);
        Assert.Equal(HttpStatusCode.Created, retry.StatusCode);
        Assert.Equal((1L, 1L, 1L), await db.CountRowsAsync());

        Evidence.Record("DI-05 partial body", new
        {
            apiPid = api.Pid,
            database = db.Name,
            declaredLength = FixturePdf.Length,
            sentBytes = FixturePdf.Length / 2,
            rowsAfterDisconnect = new[] { 0, 0, 0 },
            keyLookupAfterDisconnect = (int)lookup.StatusCode,
            sameKeyRetry = (int)retry.StatusCode,
        });
    }

    [Fact]
    public async Task DI05_api_killed_inside_a_blocked_transaction_leaves_no_partial_unit()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        var api = await ApiProcess.StartAsync(db.AppConnectionString);
        var key = Guid.NewGuid();
        BlockedBackend backend;
        Exception? clientFailure;

        await using (var locker = await db.OpenAdminAsync())
        {
            await using var lockTransaction = await locker.BeginTransactionAsync(Cancel);
            await using (var lockCommand = new NpgsqlCommand("LOCK TABLE eledgercare.processing_jobs IN SHARE MODE", locker, lockTransaction))
            {
                await lockCommand.ExecuteNonQueryAsync(Cancel);
            }

            using var client = api.CreateClient();
            var pending = client.SendAsync(Submit(key, FixturePdf), Cancel);
            backend = (await LockObserver.WaitForBlockedAsync(db, fixture.Settings.AppUser, 1, LockWait)).Single();

            // While blocked, nothing of the unit is visible to other sessions.
            Assert.Equal((0L, 0L, 0L), await db.CountRowsAsync());
            Assert.Contains("processing_jobs", backend.Query, StringComparison.Ordinal);
            Assert.Contains(backend.Locks, l => l.Relation == "processing_jobs" && l.Mode == "RowExclusiveLock" && !l.Granted);
            Assert.Contains(backend.Locks, l => l.Relation == "documents" && l.Mode == "RowExclusiveLock" && l.Granted);

            await api.KillAsync();
            clientFailure = await Record.ExceptionAsync(() => pending);
            Assert.NotNull(clientFailure);

            await lockTransaction.RollbackAsync(Cancel);
        }

        Assert.True(await LockObserver.BackendGoneAsync(db, backend.Pid, TimeSpan.FromSeconds(20)));
        Assert.Equal((0L, 0L, 0L), await db.CountRowsAsync());

        await using var restarted = await ApiProcess.StartAsync(db.AppConnectionString);
        using var after = restarted.CreateClient();
        using var lookup = await after.GetAsync($"/api/submissions/{key:D}", Cancel);
        Assert.Equal(HttpStatusCode.NotFound, lookup.StatusCode);
        using var retry = await after.SendAsync(Submit(key, FixturePdf), Cancel);
        Assert.Equal(HttpStatusCode.Created, retry.StatusCode);
        Assert.Equal((1L, 1L, 1L), await db.CountRowsAsync());

        Evidence.Record("DI-05 interrupted transaction", new
        {
            database = db.Name,
            killedApi = new { pid = api.Pid, startUtc = api.StartTimeUtc, termination = "TerminateProcess on verified PID/start time" },
            observedBackend = backend,
            interpretation = backend.BackendXid is null
                ? "blocked pre-commit transaction; no XID assigned, so no completed earlier insert is established"
                : "XID assigned and statement blocked on processing_jobs with documents RowExclusiveLock granted: an earlier insert in this transaction executed; unit was uncommitted",
            clientFailure = clientFailure?.GetType().Name,
            rowsAfterKillAndRelease = new[] { 0, 0, 0 },
            backendTerminated = true,
            restartedApi = new { pid = restarted.Pid, startUtc = restarted.StartTimeUtc },
            keyLookupAfterRestart = (int)lookup.StatusCode,
            sameKeyRetry = (int)retry.StatusCode,
        });
        await api.DisposeAsync();
    }

    [Fact]
    public async Task DI06_lost_committed_response_is_recovered_by_key_lookup_and_exact_retry()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        await using var api = await ApiProcess.StartAsync(db.AppConnectionString);
        await using var proxy = new ResponseDroppingProxy(api.BaseAddress);
        var key = Guid.NewGuid();

        using (var viaProxy = new HttpClient { BaseAddress = proxy.Address, Timeout = TimeSpan.FromSeconds(30) })
        {
            var lost = await Record.ExceptionAsync(() => viaProxy.SendAsync(Submit(key, FixturePdf), Cancel));
            Assert.IsType<HttpRequestException>(lost);
        }

        var dropped = await proxy.DroppedStatusLine;
        Assert.StartsWith("HTTP/1.1 201", dropped, StringComparison.Ordinal);

        using var client = api.CreateClient();
        var reconciled = await client.GetFromJsonAsync<Receipt>($"/api/submissions/{key:D}", Cancel);
        using var retry = await client.SendAsync(Submit(key, FixturePdf), Cancel);
        Assert.Equal(HttpStatusCode.OK, retry.StatusCode);
        var retried = await ReadReceiptAsync(retry);
        Assert.Equal(reconciled, retried);
        Assert.Equal((1L, 1L, 1L), await db.CountRowsAsync());

        Evidence.Record("DI-06 lost response", new
        {
            apiPid = api.Pid,
            database = db.Name,
            droppedUpstreamStatus = dropped,
            clientObserved = "HttpRequestException (no response)",
            reconciledDocumentId = reconciled!.DocumentId,
            exactRetryStatus = (int)retry.StatusCode,
            retryDocumentId = retried.DocumentId,
            rows = new[] { 1, 1, 1 },
        });
    }

    [Fact]
    public async Task DI06_sequential_exact_retries_conflicts_and_distinct_keys_follow_the_identity_policy()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        await using var api = await ApiProcess.StartAsync(db.AppConnectionString);
        using var client = api.CreateClient();
        var key = Guid.NewGuid();

        using var first = await client.SendAsync(Submit(key, FixturePdf), Cancel);
        using var second = await client.SendAsync(Submit(key, FixturePdf), Cancel);
        using var third = await client.SendAsync(Submit(key, FixturePdf), Cancel);
        Assert.Equal(HttpStatusCode.Created, first.StatusCode);
        Assert.Equal(HttpStatusCode.OK, second.StatusCode);
        Assert.Equal(HttpStatusCode.OK, third.StatusCode);
        var original = await ReadReceiptAsync(first);
        Assert.Equal(original, await ReadReceiptAsync(second));
        Assert.Equal(original, await ReadReceiptAsync(third));

        // Conflicting bytes under the same key: 409, committed original untouched.
        var otherPdf = SyntheticPdf.Build(new SyntheticPdf.Spec { Pages = 2 });
        using var conflict = await client.SendAsync(Submit(key, otherPdf), Cancel);
        Assert.Equal(HttpStatusCode.Conflict, conflict.StatusCode);
        Assert.Equal("idempotency_key_conflict", await ProblemCodeAsync(conflict));
        Assert.Equal(FixturePdf, await client.GetByteArrayAsync(original.OriginalUrl, Cancel));

        // Same length and digest prefix is irrelevant: a single flipped byte is still a conflict.
        var flipped = (byte[])FixturePdf.Clone();
        flipped[FixturePdf.Length / 2] ^= 0x01;
        using var flippedConflict = await client.SendAsync(Submit(key, flipped), Cancel);
        Assert.Equal(HttpStatusCode.Conflict, flippedConflict.StatusCode);

        // Identical bytes under a different key: a separate business document.
        using var otherKey = await client.SendAsync(Submit(Guid.NewGuid(), FixturePdf), Cancel);
        Assert.Equal(HttpStatusCode.Created, otherKey.StatusCode);
        var separate = await ReadReceiptAsync(otherKey);
        Assert.NotEqual(original.DocumentId, separate.DocumentId);
        Assert.Equal(original.Sha256, separate.Sha256);
        Assert.Equal((2L, 2L, 2L), await db.CountRowsAsync());

        Evidence.Record("DI-06 identity policy", new
        {
            apiPid = api.Pid,
            database = db.Name,
            sequential = new[] { (int)first.StatusCode, (int)second.StatusCode, (int)third.StatusCode },
            conflictingBytes = (int)conflict.StatusCode,
            singleByteFlip = (int)flippedConflict.StatusCode,
            differentKeySameBytes = (int)otherKey.StatusCode,
            distinctDocuments = original.DocumentId != separate.DocumentId,
            rows = new[] { 2, 2, 2 },
        });
    }

    [Fact]
    public async Task DI06_concurrent_same_key_race_is_resolved_by_the_unique_constraint()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        await using var api = await ApiProcess.StartAsync(db.AppConnectionString);
        using var client = api.CreateClient();
        var key = Guid.NewGuid();
        IReadOnlyList<BlockedBackend> blocked;
        HttpResponseMessage[] responses;

        await using (var locker = await db.OpenAdminAsync())
        {
            await using var lockTransaction = await locker.BeginTransactionAsync(Cancel);
            await using (var lockCommand = new NpgsqlCommand("LOCK TABLE eledgercare.processing_jobs IN SHARE MODE", locker, lockTransaction))
            {
                await lockCommand.ExecuteNonQueryAsync(Cancel);
            }

            var a = client.SendAsync(Submit(key, FixturePdf), Cancel);
            var b = client.SendAsync(Submit(key, FixturePdf), Cancel);
            blocked = await LockObserver.WaitForBlockedAsync(db, fixture.Settings.AppUser, 2, LockWait);
            await lockTransaction.RollbackAsync(Cancel);
            responses = await Task.WhenAll(a, b);
        }

        // One backend waited on the processing_jobs relation lock, the other on the first transaction's
        // uncommitted idempotency-key tuple (transactionid lock) - the unique-constraint race path.
        Assert.Contains(blocked, backend => backend.Locks.Any(l => l.Relation == "processing_jobs" && !l.Granted));
        Assert.Contains(blocked, backend => backend.Locks.Any(l => l.LockType == "transactionid" && !l.Granted));

        var statuses = responses.Select(r => r.StatusCode).Order().ToArray();
        Assert.Equal([HttpStatusCode.OK, HttpStatusCode.Created], statuses);
        var receipts = await Task.WhenAll(responses.Select(ReadReceiptAsync));
        Assert.Equal(receipts[0], receipts[1]);
        Assert.Equal((1L, 1L, 1L), await db.CountRowsAsync());
        foreach (var response in responses)
        {
            response.Dispose();
        }

        Evidence.Record("DI-06 concurrent race", new
        {
            apiPid = api.Pid,
            database = db.Name,
            blockedBackends = blocked,
            statuses = statuses.Select(s => (int)s),
            sameDocument = receipts[0].DocumentId == receipts[1].DocumentId,
            rows = new[] { 1, 1, 1 },
        });
    }

    [Fact]
    public async Task BIC02_third_concurrent_submission_gets_429_while_reads_stay_outside_the_gate()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        await using var api = await ApiProcess.StartAsync(db.AppConnectionString);
        using var client = api.CreateClient();
        var keys = new[] { Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid() };
        HttpStatusCode busy, readDuringBusy;
        string? busyCode;
        HttpResponseMessage[] admitted;

        await using (var locker = await db.OpenAdminAsync())
        {
            await using var lockTransaction = await locker.BeginTransactionAsync(Cancel);
            await using (var lockCommand = new NpgsqlCommand("LOCK TABLE eledgercare.processing_jobs IN SHARE MODE", locker, lockTransaction))
            {
                await lockCommand.ExecuteNonQueryAsync(Cancel);
            }

            var first = client.SendAsync(Submit(keys[0], FixturePdf), Cancel);
            var second = client.SendAsync(Submit(keys[1], FixturePdf), Cancel);
            await LockObserver.WaitForBlockedAsync(db, fixture.Settings.AppUser, 2, LockWait);

            using (var third = await client.SendAsync(Submit(keys[2], FixturePdf), Cancel))
            {
                busy = third.StatusCode;
                busyCode = await ProblemCodeAsync(third);
            }

            using (var read = await client.GetAsync($"/api/submissions/{keys[2]:D}", Cancel))
            {
                readDuringBusy = read.StatusCode;
            }

            await lockTransaction.RollbackAsync(Cancel);
            admitted = await Task.WhenAll(first, second);
        }

        Assert.Equal(HttpStatusCode.TooManyRequests, busy);
        Assert.Equal("admission_busy", busyCode);
        Assert.Equal(HttpStatusCode.NotFound, readDuringBusy);
        Assert.All(admitted, r => Assert.Equal(HttpStatusCode.Created, r.StatusCode));
        using var retry = await client.SendAsync(Submit(keys[2], FixturePdf), Cancel);
        Assert.Equal(HttpStatusCode.Created, retry.StatusCode);
        Assert.Equal((3L, 3L, 3L), await db.CountRowsAsync());
        foreach (var response in admitted)
        {
            response.Dispose();
        }

        Evidence.Record("BIC-02 admission gate", new
        {
            apiPid = api.Pid,
            database = db.Name,
            thirdConcurrentPost = (int)busy,
            getDuringSaturation = (int)readDuringBusy,
            firstTwo = admitted.Select(r => (int)r.StatusCode),
            sameKeyRetryAfter429 = (int)retry.StatusCode,
        });
    }

    [Fact]
    public async Task DI07_invalid_requests_are_rejected_without_creating_rows()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        await using var api = await ApiProcess.StartAsync(db.AppConnectionString);
        using var client = api.CreateClient();
        var results = new List<object>();

        async Task Expect(string name, HttpRequestMessage request, HttpStatusCode expected, string code)
        {
            using var response = await client.SendAsync(request, Cancel);
            var actualCode = await ProblemCodeAsync(response);
            results.Add(new { name, status = (int)response.StatusCode, code = actualCode });
            Assert.True(expected == response.StatusCode, $"{name}: expected {(int)expected}, got {(int)response.StatusCode}");
            Assert.Equal(code, actualCode);
            Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        }

        await Expect("missing key", Submit(null, FixturePdf), HttpStatusCode.BadRequest, "invalid_idempotency_key");
        await Expect("non-uuid key", SubmitRawKey("not-a-uuid", FixturePdf), HttpStatusCode.BadRequest, "invalid_idempotency_key");
        await Expect("N-format key", SubmitRawKey(Guid.NewGuid().ToString("N"), FixturePdf), HttpStatusCode.BadRequest, "invalid_idempotency_key");
        await Expect("braced key", SubmitRawKey(Guid.NewGuid().ToString("B"), FixturePdf), HttpStatusCode.BadRequest, "invalid_idempotency_key");
        await Expect("empty uuid key", Submit(Guid.Empty, FixturePdf), HttpStatusCode.BadRequest, "invalid_idempotency_key");
        await Expect("text/plain", Submit(Guid.NewGuid(), FixturePdf, "text/plain"), HttpStatusCode.UnsupportedMediaType, "unsupported_media_type");
        await Expect("multipart", Submit(Guid.NewGuid(), FixturePdf, "multipart/form-data"), HttpStatusCode.UnsupportedMediaType, "unsupported_media_type");
        var gzip = Submit(Guid.NewGuid(), FixturePdf);
        gzip.Content!.Headers.ContentEncoding.Add("gzip");
        await Expect("gzip encoding", gzip, HttpStatusCode.UnsupportedMediaType, "unsupported_content_encoding");
        await Expect("empty body", Submit(Guid.NewGuid(), []), HttpStatusCode.BadRequest, "empty_body");

        var declared = await RawHttp.SendHeadersOnlyAsync(api.BaseAddress, Guid.NewGuid(), 10_485_761);
        results.Add(new { name = "declared oversize (no body sent)", statusLine = declared });
        Assert.StartsWith("HTTP/1.1 413", declared, StringComparison.Ordinal);

        var streamed = new HttpRequestMessage(HttpMethod.Post, "/api/documents")
        {
            Content = new StreamContent(new NonSeekableStream(new byte[10_485_761])),
        };
        streamed.Headers.Add("Idempotency-Key", Guid.NewGuid().ToString("D"));
        streamed.Content.Headers.ContentType = new MediaTypeHeaderValue("application/pdf");
        streamed.Headers.TransferEncodingChunked = true;
        await Expect("streamed oversize (chunked)", streamed, HttpStatusCode.RequestEntityTooLarge, "document_too_large");

        Assert.Equal((0L, 0L, 0L), await db.CountRowsAsync());
        Evidence.Record("DI-07 HTTP rejections", new { apiPid = api.Pid, database = db.Name, results, rows = new[] { 0, 0, 0 } });
    }

    [Fact]
    public async Task DI07_pdfs_outside_the_admission_profile_return_422_without_rows()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        await using var api = await ApiProcess.StartAsync(db.AppConnectionString);
        using var client = api.CreateClient();
        var valid = FixturePdf;
        var eof = System.Text.Encoding.ASCII.GetString(valid).LastIndexOf("%%EOF", StringComparison.Ordinal);
        var cases = new (string Name, byte[] Body, string Code)[]
        {
            ("non-PDF text", "plain text, not a PDF\n"u8.ToArray(), "pdf_unsupported_header"),
            ("PDF 2.0 header", SyntheticPdf.Build(new SyntheticPdf.Spec { Header = "%PDF-2.0" }), "pdf_unsupported_header"),
            ("FDF header", SyntheticPdf.Build(new SyntheticPdf.Spec { Header = "%FDF-1.2" }), "pdf_unsupported_header"),
            ("leading junk", "junk\n"u8.ToArray().Concat(valid).ToArray(), "pdf_unsupported_header"),
            ("missing EOF", valid[..eof], "pdf_missing_eof"),
            ("truncated without EOF", valid[..(valid.Length / 2)], "pdf_missing_eof"),
            ("truncated with appended EOF", valid[..(valid.Length * 6 / 10)].Concat("\n%%EOF\n"u8.ToArray()).ToArray(), "pdf_invalid_cross_reference"),
            ("startxref shifted", SyntheticPdf.Build(new SyntheticPdf.Spec { StartXrefShift = 7 }), "pdf_invalid_cross_reference"),
            ("truncated content stream", SyntheticPdf.Build(new SyntheticPdf.Spec { TruncateFirstContentStream = true }), "pdf_unreadable"),
            ("malformed page object", SyntheticPdf.Build(new SyntheticPdf.Spec { BreakFirstPageObject = true }), "pdf_unreadable"),
            ("dangling page reference", SyntheticPdf.Build(new SyntheticPdf.Spec { KidsOverride = "99 0 R" }), "*"),
            ("non-page kid", SyntheticPdf.Build(new SyntheticPdf.Spec { KidsOverride = "3 0 R" }), "*"),
            ("missing root object", SyntheticPdf.Build(new SyntheticPdf.Spec { RootOverride = "99 0 R" }), "pdf_unreadable"),
            ("password-required encryption", SyntheticPdf.Build(new SyntheticPdf.Spec { UserPassword = "u", OwnerPassword = "o" }), "pdf_encrypted"),
            ("owner-password, empty user password", SyntheticPdf.Build(new SyntheticPdf.Spec { UserPassword = string.Empty, OwnerPassword = "o" }), "pdf_encrypted"),
            ("51 pages", SyntheticPdf.Build(new SyntheticPdf.Spec { Pages = 51 }), "pdf_page_count_out_of_range"),
        };
        var results = new List<object>();
        foreach (var (name, body, code) in cases)
        {
            using var response = await client.SendAsync(Submit(Guid.NewGuid(), body), Cancel);
            var actualCode = await ProblemCodeAsync(response);
            results.Add(new { name, bytes = body.Length, status = (int)response.StatusCode, code = actualCode });
            Assert.True(response.StatusCode == HttpStatusCode.UnprocessableEntity, $"{name}: got {(int)response.StatusCode}");
            Assert.True(code == "*" ? actualCode!.StartsWith("pdf_", StringComparison.Ordinal) : actualCode == code, $"{name}: code {actualCode}");
        }

        Assert.Equal((0L, 0L, 0L), await db.CountRowsAsync());
        Evidence.Record("DI-07 PDF profile rejections", new { apiPid = api.Pid, database = db.Name, results, rows = new[] { 0, 0, 0 } });
    }

    [Fact]
    public async Task DI07_filename_like_input_cannot_select_storage_or_the_download_name()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        await using var api = await ApiProcess.StartAsync(db.AppConnectionString);
        using var client = api.CreateClient();
        var apiDirectory = Path.GetDirectoryName(RepositoryPaths.ApiAssembly)!;
        var filesBefore = Directory.GetFiles(apiDirectory, "*", SearchOption.AllDirectories).Order().ToArray();

        var request = Submit(Guid.NewGuid(), FixturePdf);
        request.Content!.Headers.ContentDisposition = ContentDispositionHeaderValue.Parse("attachment; filename=\"..\\..\\..\\Windows\\win.ini\"");
        request.Headers.Add("X-File-Name", "../../../../etc/passwd");
        using var response = await client.SendAsync(request, Cancel);
        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        var receipt = await ReadReceiptAsync(response);

        using var download = await client.GetAsync(receipt.OriginalUrl, Cancel);
        Assert.Equal($"document-{receipt.DocumentId:D}.pdf", download.Content.Headers.ContentDisposition?.FileName?.Trim('"'));

        using var traversal = await client.GetAsync("/api/documents/..%2F..%2FWindows%2Fwin.ini/original", Cancel);
        Assert.Equal(HttpStatusCode.BadRequest, traversal.StatusCode);

        // No filename column exists; the schema has exactly the designed F1+F2+F3 columns.
        await using var admin = await db.OpenAdminAsync();
        await using var command = new NpgsqlCommand(
            "SELECT string_agg(table_name || '.' || column_name, ',' ORDER BY table_name, column_name) FROM information_schema.columns WHERE table_schema = 'eledgercare' AND table_name <> '__ef_migrations_history'",
            admin);
        var columns = (string)(await command.ExecuteScalarAsync(Cancel))!;
        Assert.DoesNotContain("file_name", columns, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("filename", columns, StringComparison.OrdinalIgnoreCase);
        Assert.Equal(
            "documents.document_id,documents.idempotency_key,documents.submitted_at," +
            "execution_attempts.attempt_id,execution_attempts.attempt_number,execution_attempts.diagnostic_metadata_json," +
            "execution_attempts.diagnostic_raw_output_utf8,execution_attempts.document_id,execution_attempts.ended_at," +
            "execution_attempts.exit_code,execution_attempts.failure_code,execution_attempts.failure_detail," +
            "execution_attempts.fencing_token,execution_attempts.job_id,execution_attempts.last_heartbeat_at," +
            "execution_attempts.launcher_create_filetime,execution_attempts.launcher_pid,execution_attempts.phase," +
            "execution_attempts.retried_from_attempt_id,execution_attempts.run_directory_name,execution_attempts.started_at," +
            "execution_attempts.status,execution_attempts.supervisor_create_filetime,execution_attempts.supervisor_instance_id," +
            "execution_attempts.supervisor_pid,execution_attempts.worker_create_filetime,execution_attempts.worker_pid," +
            "extraction_results.attempt_id,extraction_results.completed_at,extraction_results.dependency_lock_sha256," +
            "extraction_results.diagnostic_metadata_json,extraction_results.document_id,extraction_results.fencing_token," +
            "extraction_results.finish_reason,extraction_results.generation_settings_json,extraction_results.infer_duration_ms," +
            "extraction_results.input_byte_length,extraction_results.input_sha256,extraction_results.job_id," +
            "extraction_results.load_duration_ms,extraction_results.model_manifest_sha256,extraction_results.model_repo_id," +
            "extraction_results.model_revision,extraction_results.output_page_count,extraction_results.page_count," +
            "extraction_results.raw_output_byte_length,extraction_results.raw_output_bytes,extraction_results.raw_output_sha256," +
            "extraction_results.render_duration_ms,extraction_results.renderer_identity,extraction_results.result_id," +
            "extraction_results.schema_version,extraction_results.started_at,extraction_results.total_duration_ms," +
            "extraction_results.worker_config_digest,extraction_results.worker_source_digest," +
            "original_artifacts.byte_length,original_artifacts.bytes,original_artifacts.document_id,original_artifacts.media_type,original_artifacts.page_count,original_artifacts.sha256," +
            "processing_jobs.attempt_count,processing_jobs.document_id,processing_jobs.job_id,processing_jobs.latest_fencing_token," +
            "processing_jobs.queued_at,processing_jobs.requested_at,processing_jobs.retried_from_attempt_id,processing_jobs.status,processing_jobs.updated_at," +
            "work_order_review_fields.consulted_block_ordinal,work_order_review_fields.consulted_page_number,work_order_review_fields.consulted_quote," +
            "work_order_review_fields.consulted_table_column,work_order_review_fields.consulted_table_row,work_order_review_fields.decision," +
            "work_order_review_fields.field_key,work_order_review_fields.field_ordinal,work_order_review_fields.human_value," +
            "work_order_review_fields.revision_id,work_order_review_fields.unknown_reason," +
            "work_order_review_heads.created_at,work_order_review_heads.current_revision_id,work_order_review_heads.current_revision_number," +
            "work_order_review_heads.current_status,work_order_review_heads.document_id,work_order_review_heads.field_schema_version," +
            "work_order_review_heads.input_sha256,work_order_review_heads.machine_snapshot_json,work_order_review_heads.profile_id," +
            "work_order_review_heads.raw_output_sha256,work_order_review_heads.result_id,work_order_review_heads.suggestion_policy_version," +
            "work_order_review_heads.updated_at," +
            "work_order_review_revisions.accepted_field_count,work_order_review_revisions.document_id,work_order_review_revisions.edited_field_count," +
            "work_order_review_revisions.field_schema_version,work_order_review_revisions.idempotency_key,work_order_review_revisions.input_sha256," +
            "work_order_review_revisions.operator_display_label,work_order_review_revisions.previous_revision_number,work_order_review_revisions.profile_id," +
            "work_order_review_revisions.raw_output_sha256,work_order_review_revisions.request_sha256,work_order_review_revisions.result_id," +
            "work_order_review_revisions.revision_id,work_order_review_revisions.revision_number,work_order_review_revisions.saved_at," +
            "work_order_review_revisions.status,work_order_review_revisions.suggestion_policy_version,work_order_review_revisions.unknown_field_count," +
            "work_order_review_revisions.unreviewed_field_count",
            columns);

        var filesAfter = Directory.GetFiles(apiDirectory, "*", SearchOption.AllDirectories).Order().ToArray();
        Assert.Equal(filesBefore, filesAfter);

        Evidence.Record("DI-07 filename input", new
        {
            apiPid = api.Pid,
            database = db.Name,
            submittedHeaders = new[] { "Content-Disposition filename=..\\..\\..\\Windows\\win.ini", "X-File-Name: ../../../../etc/passwd" },
            status = (int)response.StatusCode,
            downloadName = download.Content.Headers.ContentDisposition?.FileName,
            traversalRouteStatus = (int)traversal.StatusCode,
            schemaColumns = columns,
            apiDirectoryFilesUnchanged = true,
        });
    }

    [Fact]
    public async Task Route_identifiers_and_local_only_guards_are_enforced()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        await using var api = await ApiProcess.StartAsync(db.AppConnectionString);
        using var client = api.CreateClient();
        var unknown = Guid.NewGuid();
        var checks = new List<object>();

        async Task Check(string name, HttpRequestMessage request, HttpStatusCode expected)
        {
            using var response = await client.SendAsync(request, Cancel);
            checks.Add(new { name, status = (int)response.StatusCode });
            Assert.True(expected == response.StatusCode, $"{name}: expected {(int)expected}, got {(int)response.StatusCode}");
        }

        await Check("document malformed id", new HttpRequestMessage(HttpMethod.Get, "/api/documents/not-a-uuid"), HttpStatusCode.BadRequest);
        await Check("document N-format id", new HttpRequestMessage(HttpMethod.Get, $"/api/documents/{unknown:N}"), HttpStatusCode.BadRequest);
        await Check("document empty uuid", new HttpRequestMessage(HttpMethod.Get, $"/api/documents/{Guid.Empty:D}"), HttpStatusCode.BadRequest);
        await Check("document unknown", new HttpRequestMessage(HttpMethod.Get, $"/api/documents/{unknown:D}"), HttpStatusCode.NotFound);
        await Check("original unknown", new HttpRequestMessage(HttpMethod.Get, $"/api/documents/{unknown:D}/original"), HttpStatusCode.NotFound);
        await Check("submission malformed key", new HttpRequestMessage(HttpMethod.Get, "/api/submissions/xyz"), HttpStatusCode.BadRequest);
        await Check("submission unknown", new HttpRequestMessage(HttpMethod.Get, $"/api/submissions/{unknown:D}"), HttpStatusCode.NotFound);

        var foreignHost = new HttpRequestMessage(HttpMethod.Get, $"/api/documents/{unknown:D}");
        foreignHost.Headers.Host = "attacker.example";
        await Check("non-local Host", foreignHost, HttpStatusCode.BadRequest);
        var foreignOrigin = Submit(Guid.NewGuid(), FixturePdf);
        foreignOrigin.Headers.Add("Origin", "https://attacker.example");
        await Check("non-local Origin", foreignOrigin, HttpStatusCode.Forbidden);
        var localOrigin = new HttpRequestMessage(HttpMethod.Get, $"/api/documents/{unknown:D}");
        localOrigin.Headers.Add("Origin", "http://127.0.0.1:4200");
        await Check("local Origin", localOrigin, HttpStatusCode.NotFound);

        Assert.Equal((0L, 0L, 0L), await db.CountRowsAsync());
        Evidence.Record("route and local-only guards", new { apiPid = api.Pid, database = db.Name, checks });
    }

    [Fact]
    public async Task Runtime_role_has_only_select_and_insert_and_server_durability_settings_are_on()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        await using var app = await db.OpenAppAsync();
        var denied = new List<string>();
        foreach (var sql in new[]
                 {
                     "UPDATE eledgercare.original_artifacts SET media_type = media_type",
                     "UPDATE eledgercare.documents SET submitted_at = submitted_at",
                     "UPDATE eledgercare.extraction_results SET finish_reason = finish_reason",
                     "UPDATE eledgercare.processing_jobs SET job_id = job_id",
                     "UPDATE eledgercare.execution_attempts SET attempt_id = attempt_id",
                     "DELETE FROM eledgercare.documents",
                     "DELETE FROM eledgercare.execution_attempts",
                     "DELETE FROM eledgercare.extraction_results",
                     "TRUNCATE eledgercare.processing_jobs",
                     "CREATE TABLE eledgercare.not_allowed (id int)",
                     "SELECT count(*) FROM eledgercare.__ef_migrations_history",
                 })
        {
            await using var command = new NpgsqlCommand(sql, app);
            var error = await Assert.ThrowsAsync<PostgresException>(() => command.ExecuteNonQueryAsync(Cancel));
            Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, error.SqlState);
            denied.Add($"{sql.Split(' ')[0]}: {error.SqlState}");
        }

        await using (var allowed = new NpgsqlCommand("SELECT count(*) FROM eledgercare.documents", app))
        {
            Assert.Equal(0L, (long)(await allowed.ExecuteScalarAsync(Cancel))!);
        }

        Assert.Equal("on", fixture.ServerSettings["fsync"]);
        Assert.Equal("on", fixture.ServerSettings["full_page_writes"]);
        Assert.Equal("on", fixture.ServerSettings["synchronous_commit"]);
        Assert.Equal("18.7", fixture.ServerSettings["server_version"]);
        Assert.Equal("127.0.0.1", fixture.ServerSettings["listen_addresses"]);

        Evidence.Record("runtime role and server settings", new { database = db.Name, denied, serverSettings = fixture.ServerSettings });
    }

    [Fact]
    public async Task Startup_rejects_limits_outside_the_ceilings_and_lower_limits_apply()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        var refused = new List<object>();
        foreach (var (setting, value) in new[]
                 {
                     ("Intake__MaxDocumentBytes", "10485761"), ("Intake__MaxDocumentBytes", "0"),
                     ("Intake__MaxPages", "51"), ("Intake__MaxPages", "0"),
                 })
        {
            var failure = await Record.ExceptionAsync(() =>
                ApiProcess.StartAsync(db.AppConnectionString, new Dictionary<string, string> { [setting] = value }));
            Assert.NotNull(failure);
            Assert.Contains(setting.Split("__")[1] + " must be within", failure.Message, StringComparison.Ordinal);
            refused.Add(new { setting, value, refused = true });
        }

        await using var api = await ApiProcess.StartAsync(db.AppConnectionString, new Dictionary<string, string>
        {
            ["Intake__MaxDocumentBytes"] = "4096",
            ["Intake__MaxPages"] = "1",
        });
        using var client = api.CreateClient();
        using var ok = await client.SendAsync(Submit(Guid.NewGuid(), FixturePdf), Cancel);
        using var twoPages = await client.SendAsync(Submit(Guid.NewGuid(), SyntheticPdf.Build(new SyntheticPdf.Spec { Pages = 2 })), Cancel);
        using var tooBig = await client.SendAsync(Submit(Guid.NewGuid(), new byte[4097]), Cancel);
        Assert.Equal(HttpStatusCode.Created, ok.StatusCode);
        Assert.Equal(HttpStatusCode.UnprocessableEntity, twoPages.StatusCode);
        Assert.Equal(HttpStatusCode.RequestEntityTooLarge, tooBig.StatusCode);
        Assert.Equal((1L, 1L, 1L), await db.CountRowsAsync());

        Evidence.Record("configured limits", new
        {
            database = db.Name,
            refused,
            lowered = new { maxDocumentBytes = 4096, maxPages = 1, fixture = (int)ok.StatusCode, twoPages = (int)twoPages.StatusCode, bytes4097 = (int)tooBig.StatusCode },
        });
    }

    [Fact]
    public async Task Migrated_schema_has_logged_tables_restrict_foreign_keys_and_designed_constraints()
    {
        await using var db = await fixture.CreateDatabaseAsync();
        await using var admin = await db.OpenAdminAsync();

        async Task<string> Text(string sql)
        {
            await using var command = new NpgsqlCommand(sql, admin);
            return (string)(await command.ExecuteScalarAsync(Cancel))!;
        }

        var persistence = await Text(
            "SELECT string_agg(relname || '=' || relpersistence::text, ',' ORDER BY relname) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace " +
            "WHERE n.nspname = 'eledgercare' AND c.relkind = 'r' AND relname <> '__ef_migrations_history'");
        var foreignKeys = await Text(
            "SELECT string_agg(conname || ':del=' || confdeltype::text || ',upd=' || confupdtype::text, ';' ORDER BY conname) FROM pg_constraint " +
            "WHERE contype = 'f' AND connamespace = 'eledgercare'::regnamespace");
        var checks = await Text(
            "SELECT string_agg(conname, ',' ORDER BY conname) FROM pg_constraint WHERE contype = 'c' AND connamespace = 'eledgercare'::regnamespace");
        var uniqueKey = await Text(
            "SELECT indexdef FROM pg_indexes WHERE schemaname = 'eledgercare' AND indexname = 'ux_documents_idempotency_key'");

        Assert.Equal(
            "documents=p,execution_attempts=p,extraction_results=p,original_artifacts=p,processing_jobs=p," +
            "work_order_review_fields=p,work_order_review_heads=p,work_order_review_revisions=p",
            persistence);
        Assert.Equal(
            "fk_execution_attempts_documents:del=r,upd=a;fk_execution_attempts_processing_jobs:del=r,upd=a;" +
            "fk_execution_attempts_retried_from:del=r,upd=a;fk_extraction_results_documents:del=r,upd=a;" +
            "fk_extraction_results_execution_attempts:del=r,upd=a;fk_extraction_results_processing_jobs:del=r,upd=a;" +
            "fk_original_artifacts_documents:del=r,upd=a;fk_processing_jobs_documents:del=r,upd=a;" +
            "fk_processing_jobs_retried_from_attempt:del=r,upd=a;" +
            "fk_work_order_review_fields_revisions:del=r,upd=a;" +
            "fk_work_order_review_heads_current_revision:del=r,upd=a;" +
            "fk_work_order_review_heads_documents:del=r,upd=a;" +
            "fk_work_order_review_heads_extraction_results:del=r,upd=a;" +
            "fk_work_order_review_revisions_documents:del=r,upd=a;" +
            "fk_work_order_review_revisions_extraction_results:del=r,upd=a",
            foreignKeys);
        Assert.Equal(
            "ck_execution_attempts_ended_consistency,ck_execution_attempts_failure_consistency,ck_execution_attempts_positive_ids," +
            "ck_execution_attempts_status,ck_extraction_results_digests,ck_extraction_results_durations," +
            "ck_extraction_results_finish_reason,ck_extraction_results_page_bounds,ck_extraction_results_raw_length_matches," +
            "ck_extraction_results_schema,ck_original_artifacts_byte_length_matches,ck_original_artifacts_byte_length_range," +
            "ck_original_artifacts_media_type,ck_original_artifacts_page_count_range,ck_original_artifacts_sha256_length," +
            "ck_processing_jobs_state_invariants,ck_processing_jobs_status," +
            "ck_work_order_review_fields_decision,ck_work_order_review_fields_key_ordinal,ck_work_order_review_fields_source_coords," +
            "ck_work_order_review_fields_unknown_reason,ck_work_order_review_fields_value_consistency,ck_work_order_review_fields_value_lengths," +
            "ck_work_order_review_heads_digests,ck_work_order_review_heads_profile,ck_work_order_review_heads_revision_bounds," +
            "ck_work_order_review_heads_status," +
            "ck_work_order_review_revisions_bounds,ck_work_order_review_revisions_digests,ck_work_order_review_revisions_field_counts," +
            "ck_work_order_review_revisions_operator_label,ck_work_order_review_revisions_profile,ck_work_order_review_revisions_status",
            checks);
        Assert.Contains("UNIQUE INDEX ux_documents_idempotency_key", uniqueKey, StringComparison.Ordinal);

        // The database itself refuses an artifact whose declared length disagrees with its bytes.
        await using var migrator = await PostgresFixture.OpenAsync(fixture.Settings.Migrator(db.Name));
        var documentId = Guid.NewGuid();
        await using (var insertDocument = new NpgsqlCommand(
            "INSERT INTO eledgercare.documents (document_id, idempotency_key, submitted_at) VALUES (@id, @key, now())", migrator))
        {
            insertDocument.Parameters.AddWithValue("id", documentId);
            insertDocument.Parameters.AddWithValue("key", Guid.NewGuid());
            await insertDocument.ExecuteNonQueryAsync(Cancel);
        }

        await using var badArtifact = new NpgsqlCommand(
            "INSERT INTO eledgercare.original_artifacts (document_id, bytes, sha256, byte_length, media_type, page_count) " +
            "VALUES (@id, '\\x01'::bytea, decode(repeat('00', 32), 'hex'), 2, 'application/pdf', 1)", migrator);
        badArtifact.Parameters.AddWithValue("id", documentId);
        var violation = await Assert.ThrowsAsync<PostgresException>(() => badArtifact.ExecuteNonQueryAsync(Cancel));
        Assert.Equal(PostgresErrorCodes.CheckViolation, violation.SqlState);
        Assert.Equal("ck_original_artifacts_byte_length_matches", violation.ConstraintName);

        Evidence.Record("schema constraints", new { database = db.Name, persistence, foreignKeys, checks, uniqueKey, lengthMismatch = violation.SqlState });
    }

    private static HttpRequestMessage Submit(Guid? key, byte[] body, string contentType = "application/pdf")
    {
        var request = new HttpRequestMessage(HttpMethod.Post, "/api/documents") { Content = new ByteArrayContent(body) };
        request.Content.Headers.ContentType = new MediaTypeHeaderValue(contentType);
        if (key is { } value)
        {
            request.Headers.Add("Idempotency-Key", value.ToString("D"));
        }

        return request;
    }

    private static HttpRequestMessage SubmitRawKey(string key, byte[] body)
    {
        var request = Submit(null, body);
        request.Headers.TryAddWithoutValidation("Idempotency-Key", key);
        return request;
    }

    private static async Task<Receipt> ReadReceiptAsync(HttpResponseMessage response) =>
        (await response.Content.ReadFromJsonAsync<Receipt>(Cancel))!;

    private static async Task<string?> ProblemCodeAsync(HttpResponseMessage response)
    {
        var text = await response.Content.ReadAsStringAsync(Cancel);
        if (string.IsNullOrWhiteSpace(text))
        {
            return null;
        }

        using var json = JsonDocument.Parse(text);
        return json.RootElement.TryGetProperty("code", out var code) ? code.GetString() : null;
    }

    private sealed record Receipt(
        Guid DocumentId,
        Guid JobId,
        string Status,
        DateTimeOffset SubmittedAtUtc,
        int ByteLength,
        string Sha256,
        string OriginalUrl);
}
