using System.Security.Cryptography;
using System.Text;
using ELedgerCare.Domain.Documents;
using ELedgerCare.Domain.Processing;
using Xunit;

namespace ELedgerCare.Domain.Tests;

public sealed class ExtractionDomainAndParserTests
{
    private static readonly DateTimeOffset T0 = new(2026, 11, 16, 5, 0, 0, TimeSpan.Zero);

    [Fact]
    public void ProcessingJob_enforces_explicit_retry_and_monotonic_fencing_ownership()
    {
        var doc = Document.Submit(Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), [1, 2, 3], 1, T0);
        var job = doc.Job;

        Assert.Equal(ProcessingStatus.AwaitingExtraction, job.Status);
        Assert.Equal(0, job.AttemptCount);
        Assert.Equal(0, job.LatestFencingToken);
        Assert.Equal(T0, job.UpdatedAtUtc);

        // Retry without a prior failed/interrupted attempt is refused.
        Assert.Throws<InvalidOperationException>(() => job.QueueRetry(Guid.NewGuid(), T0.AddSeconds(1)));

        job.QueueInitial(T0.AddSeconds(2));
        Assert.Equal(ProcessingStatus.Queued, job.Status);
        Assert.Throws<InvalidOperationException>(() => job.QueueInitial(T0.AddSeconds(3)));

        Assert.Throws<ArgumentOutOfRangeException>(() => job.Claim(0, T0.AddSeconds(3)));
        var attempt1 = job.Claim(10, T0.AddSeconds(3));
        Assert.Equal(1, attempt1);
        Assert.Equal(ProcessingStatus.Running, job.Status);
        Assert.Equal(10, job.LatestFencingToken);

        // Stale or wrong fencing token cannot mutate job state.
        Assert.Throws<InvalidOperationException>(() => job.MarkFailed(9, T0.AddSeconds(4)));
        Assert.Throws<InvalidOperationException>(() => job.MarkCompleted(9, T0.AddSeconds(4)));

        job.MarkInterrupted(10, T0.AddSeconds(5));
        Assert.Equal(ProcessingStatus.Interrupted, job.Status);

        var priorAttemptId = Guid.NewGuid();
        job.QueueRetry(priorAttemptId, T0.AddSeconds(6));
        Assert.Equal(ProcessingStatus.Queued, job.Status);
        Assert.Equal(priorAttemptId, job.RetriedFromAttemptId);

        // Monotonic fencing: token <= 10 is rejected on Attempt #2.
        Assert.Throws<ArgumentOutOfRangeException>(() => job.Claim(10, T0.AddSeconds(7)));
        var attempt2 = job.Claim(11, T0.AddSeconds(7));
        Assert.Equal(2, attempt2);
        Assert.Equal(11, job.LatestFencingToken);

        job.MarkCompleted(11, T0.AddSeconds(8));
        Assert.Equal(ProcessingStatus.Completed, job.Status);

        // Completed jobs cannot be retried.
        Assert.Throws<InvalidOperationException>(() => job.QueueRetry(Guid.NewGuid(), T0.AddSeconds(9)));
    }

    [Fact]
    public void ExecutionAttempt_tracks_os_identities_and_bounds_failure_diagnostics()
    {
        var attempt = ExecutionAttempt.Start(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            attemptNumber: 1,
            fencingToken: 1,
            retriedFromAttemptId: null,
            runDirectoryName: "attempt-test",
            supervisorInstanceId: Guid.NewGuid(),
            supervisorPid: 4200,
            supervisorCreateFileTime: 133700000000000000L,
            startedAtUtc: T0);

        Assert.Equal(AttemptStatus.Running, attempt.Status);
        Assert.Equal("claiming", attempt.Phase);

        attempt.RecordLauncherProcess(5100, 133700000000000010L, T0.AddSeconds(1));
        Assert.Equal(5100, attempt.LauncherPid);
        Assert.Equal("starting", attempt.Phase);

        attempt.RecordHeartbeat("inferring", 5200, 133700000000000020L, T0.AddSeconds(2));
        Assert.Equal(5200, attempt.WorkerPid);
        Assert.Equal("inferring", attempt.Phase);

        var oversizedDetail = new string('x', 800);
        var oversizedDiag = new string('y', 70_000);
        attempt.MarkFailed("model_output_truncated", oversizedDetail, T0.AddSeconds(3), exitCode: 0, oversizedDiag, "{}");

        Assert.Equal(AttemptStatus.Failed, attempt.Status);
        Assert.Equal(ExecutionAttempt.MaxFailureDetailLength, attempt.FailureDetail!.Length);
        Assert.Equal(ExecutionAttempt.MaxDiagnosticOutputChars, attempt.DiagnosticRawOutputUtf8!.Length);
        Assert.Throws<InvalidOperationException>(() =>
            attempt.RecordHeartbeat("late", 5200, 133700000000000020L, T0.AddSeconds(4)));
    }

    [Fact]
    public void ExtractionResult_enforces_sha256_strict_utf8_stop_reason_page_markers_and_pinned_model()
    {
        var rawText = "<PAGE>\n<BLOCK>title[[0,0,100,20]]<FORK>WORK ORDER 101\n<PAGE>\n<BLOCK>text[[0,0,100,20]]<FORK>Page two\n";
        var rawBytes = Encoding.UTF8.GetBytes(rawText);
        var rawSha = SHA256.HashData(rawBytes);
        var zeroSha = new byte[32];

        const string PinnedRenderer = "pypdfium2==5.15.2 (PDFium 159.0.8149.0)";
        var valid = ExtractionResult.Create(
            Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(),
            fencingToken: 1,
            inputSha256: zeroSha,
            inputByteLength: 1024,
            pageCount: 2,
            rawOutputBytes: rawBytes,
            declaredRawOutputSha256: rawSha,
            modelRepoId: ExtractionCeilings.ModelRepoId,
            modelRevision: ExtractionCeilings.ModelRevision,
            modelManifestSha256: zeroSha,
            dependencyLockSha256: zeroSha,
            workerSourceDigest: zeroSha,
            workerConfigDigest: zeroSha,
            rendererIdentity: PinnedRenderer,
            generationSettingsJson: "{\"temperature\":0.0}",
            finishReason: "stop",
            outputPageCount: 2,
            startedAtUtc: T0,
            completedAtUtc: T0.AddSeconds(5),
            loadDurationMs: 100,
            renderDurationMs: 20,
            inferDurationMs: 300,
            totalDurationMs: 420,
            diagnosticMetadataJson: "{}");

        Assert.Equal(rawText, valid.DecodeStrictUtf8());
        Assert.Equal(rawBytes.Length, valid.RawOutputByteLength);

        // Truncated finish_reason='length' is refused.
        Assert.Throws<ArgumentException>(() => ExtractionResult.Create(
            Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), 1, zeroSha, 1024, 2,
            rawBytes, rawSha, ExtractionCeilings.ModelRepoId, ExtractionCeilings.ModelRevision,
            zeroSha, zeroSha, zeroSha, zeroSha, PinnedRenderer, "{}",
            finishReason: "length", outputPageCount: 2, T0, T0, 1, 1, 1, 3, "{}"));

        // Page count > 3 is refused.
        var fourPages = Encoding.UTF8.GetBytes("<PAGE>1<PAGE>2<PAGE>3<PAGE>4");
        Assert.Throws<ArgumentOutOfRangeException>(() => ExtractionResult.Create(
            Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), 1, zeroSha, 1024, 4,
            fourPages, SHA256.HashData(fourPages), ExtractionCeilings.ModelRepoId, ExtractionCeilings.ModelRevision,
            zeroSha, zeroSha, zeroSha, zeroSha, PinnedRenderer, "{}",
            finishReason: "stop", outputPageCount: 4, T0, T0, 1, 1, 1, 3, "{}"));

        // Invalid UTF-8 bytes with matching SHA-256 are refused.
        byte[] badUtf8 = [(byte)'<', (byte)'P', (byte)'A', (byte)'G', (byte)'E', (byte)'>', 0xFF, 0xFE];
        Assert.Throws<DecoderFallbackException>(() => ExtractionResult.Create(
            Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), 1, zeroSha, 1024, 1,
            badUtf8, SHA256.HashData(badUtf8), ExtractionCeilings.ModelRepoId, ExtractionCeilings.ModelRevision,
            zeroSha, zeroSha, zeroSha, zeroSha, PinnedRenderer, "{}",
            finishReason: "stop", outputPageCount: 1, T0, T0, 1, 1, 1, 3, "{}"));

        // <PAGE> marker count mismatch with admitted pageCount is refused.
        Assert.Throws<ArgumentException>(() => ExtractionResult.Create(
            Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), 1, zeroSha, 1024, 3,
            rawBytes, rawSha, ExtractionCeilings.ModelRepoId, ExtractionCeilings.ModelRevision,
            zeroSha, zeroSha, zeroSha, zeroSha, PinnedRenderer, "{}",
            finishReason: "stop", outputPageCount: 3, T0, T0, 1, 1, 1, 3, "{}"));
    }

    [Fact]
    public void SafeNativeDisplayParser_preserves_page_order_decodes_table_cells_and_keeps_hostile_tags_inert()
    {
        const string nativeOutput =
            "<PAGE>\n" +
            "<BLOCK>title[[61,43,390,63]]<FORK>MAINTENANCE WORK ORDER #SYN-01\n" +
            "<BLOCK>text[[61,70,500,90]]<FORK>Note: <script>window.__xss=1</script> &amp; check valve\n" +
            "<PAGE>\n" +
            "<BLOCK>table[[61,100,900,300]]<FORK><table><tr><th>Item</th><th>Note</th></tr>" +
            "<tr><td>Filter &amp; Seal</td><td><img src=x onerror=\"alert(1)\"><script>evil()</script></td></tr></table>\n" +
            "<PAGE>\n" +
            "<BLOCK>text[[61,120,400,150]]<FORK>Inspector Sign-off: Complete\n";

        var pages = SafeNativeDisplayParser.ParsePages(nativeOutput);

        Assert.Equal(3, pages.Count);
        Assert.Equal([1, 2, 3], pages.Select(p => p.PageNumber).ToArray());

        Assert.Equal("title", pages[0].Blocks[0].Kind);
        Assert.Equal("MAINTENANCE WORK ORDER #SYN-01", pages[0].Blocks[0].Text);
        Assert.Equal("Note: <script>window.__xss=1</script> & check valve", pages[0].Blocks[1].Text);

        var tableBlock = Assert.Single(pages[1].Blocks);
        Assert.Equal("table", tableBlock.Kind);
        Assert.NotNull(tableBlock.TableRows);
        Assert.Equal(2, tableBlock.TableRows!.Count);
        Assert.Equal(["Item", "Note"], tableBlock.TableRows[0]);
        Assert.Equal("Filter & Seal", tableBlock.TableRows[1][0]);
        Assert.Equal("<img src=x onerror=\"alert(1)\"><script>evil()</script>", tableBlock.TableRows[1][1]);

        Assert.Equal("Inspector Sign-off: Complete", Assert.Single(pages[2].Blocks).Text);
    }
}
