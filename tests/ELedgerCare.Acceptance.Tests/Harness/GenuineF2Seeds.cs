using System.Security.Cryptography;
using System.Text.Json;
using ELedgerCare.Domain.Documents;
using ELedgerCare.Domain.Processing;
using ELedgerCare.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;
using Npgsql;
using Xunit;

namespace ELedgerCare.Acceptance.Tests.Harness;

/// <summary>
/// Test-only durable acceptance seeder using genuine accepted WP-0006 F2 evidence (F3-BIC-06).
/// Zero production code or fake OCR paths exist; all inserts execute through the runtime <c>eledgercare_app</c>
/// role and advance <c>eledgercare.extraction_fencing_seq</c>.
/// Attribution: product source <c>8a73b7a5dab51e3ccf803aceedded4929529dd35</c>, executing revision
/// <c>b343f6ff78aa41332ecbe957577b6776f8edc22f</c>, independent runtime evidence <c>7f0ec3a9338606ce54c4c6d2eeabab8a2c245e2a</c>,
/// accepted report <c>c854a1d4c306c3b10d78df42a1a2552a06bb4a98</c>.
/// </summary>
public static class GenuineF2Seeds
{
    public const string SynWo01PdfSha256 = "47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd";
    public const int SynWo01PdfLength = 372_258;
    public const string SynWo01RawSha256 = "7503761ae46afef6adf579881d011764283474354fac3e185598fc7d266aff95";
    public const int SynWo01RawLength = 3_236;
    public const string SynWo01EnvelopeSha256 = "8e6e5b81c5bc1fb6e102438daef815bf19f4722994ba5acf737b732e703779ee";

    public const string SynMp01PdfSha256 = "15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3";
    public const int SynMp01PdfLength = 8_422;
    public const string SynMp01RawSha256 = "c399ad892e257500e2b6a9ac8b0bc3d8a17e9c10041262c4bca6a48fb9b9b639";
    public const int SynMp01RawLength = 7_511;
    public const string SynMp01EnvelopeSha256 = "7fd536919461171d933cb1e8db36a21164db5b7b04bcf364c094cace3c012d96";

    public static readonly Guid OriginalSynWo01ResultId = Guid.Parse("01a1e573-a855-7735-96e1-f5d14cada602");
    public static readonly Guid OriginalSynMp01ResultId = Guid.Parse("01a1e578-8bfa-7bba-b104-ea8309dbfd9e");

    public sealed record SeededDocumentReceipt(
        Guid DocumentId,
        Guid JobId,
        Guid AttemptId,
        Guid ResultId,
        long FencingToken,
        byte[] PdfBytes,
        string PdfSha256Hex,
        byte[] RawOutputBytes,
        string RawOutputSha256Hex,
        int PageCount,
        bool IdsRemapped);

    public static Task<SeededDocumentReceipt> SeedSynWo01Async(
        string appConnectionString,
        bool remapIds = false,
        CancellationToken cancellationToken = default) =>
        SeedFromGenuineEvidenceAsync(
            appConnectionString,
            pdfRelativePath: Path.Combine("tests", "fixtures", "SYN-WO-01-v1-raster300.pdf"),
            expectedPdfLength: SynWo01PdfLength,
            expectedPdfShaHex: SynWo01PdfSha256,
            runFolderName: "attempt-01a1e571-297a-7f0e-a293-e9e1c0851cd4",
            expectedRawLength: SynWo01RawLength,
            expectedRawShaHex: SynWo01RawSha256,
            expectedEnvelopeShaHex: SynWo01EnvelopeSha256,
            originalSubmissionKey: Guid.Parse("43858522-5c3d-47d2-be8c-66f7162a190e"),
            originalResultId: OriginalSynWo01ResultId,
            remapIds: remapIds,
            cancellationToken: cancellationToken);

    public static Task<SeededDocumentReceipt> SeedSynMp01Async(
        string appConnectionString,
        bool remapIds = false,
        CancellationToken cancellationToken = default) =>
        SeedFromGenuineEvidenceAsync(
            appConnectionString,
            pdfRelativePath: Path.Combine("tests", "fixtures", "SYN-MP-01-v0-clean.pdf"),
            expectedPdfLength: SynMp01PdfLength,
            expectedPdfShaHex: SynMp01PdfSha256,
            runFolderName: "attempt-01a1e573-ca25-733e-b048-44c8ea2ac61d",
            expectedRawLength: SynMp01RawLength,
            expectedRawShaHex: SynMp01RawSha256,
            expectedEnvelopeShaHex: SynMp01EnvelopeSha256,
            originalSubmissionKey: Guid.Parse("92f639e5-321d-464a-9628-f056251495cb"),
            originalResultId: OriginalSynMp01ResultId,
            remapIds: remapIds,
            cancellationToken: cancellationToken);

    private static async Task<SeededDocumentReceipt> SeedFromGenuineEvidenceAsync(
        string appConnectionString,
        string pdfRelativePath,
        int expectedPdfLength,
        string expectedPdfShaHex,
        string runFolderName,
        int expectedRawLength,
        string expectedRawShaHex,
        string expectedEnvelopeShaHex,
        Guid originalSubmissionKey,
        Guid originalResultId,
        bool remapIds,
        CancellationToken cancellationToken)
    {
        var root = RepositoryPaths.Root;
        var pdfBytes = await File.ReadAllBytesAsync(Path.Combine(root, pdfRelativePath), cancellationToken);
        var pdfSha = SHA256.HashData(pdfBytes);
        var pdfShaHex = Convert.ToHexStringLower(pdfSha);
        Assert.Equal(expectedPdfLength, pdfBytes.Length);
        Assert.Equal(expectedPdfShaHex, pdfShaHex);

        var runOutputDir = Path.Combine(
            root, "docs", "reviews", "WP-0006", "eld-next-reviewer", "runtime-execution", "runs", runFolderName, "output");
        var rawBytes = await File.ReadAllBytesAsync(Path.Combine(runOutputDir, "raw_output.utf8.bin"), cancellationToken);
        var rawSha = SHA256.HashData(rawBytes);
        var rawShaHex = Convert.ToHexStringLower(rawSha);
        Assert.Equal(expectedRawLength, rawBytes.Length);
        Assert.Equal(expectedRawShaHex, rawShaHex);

        var envelopeBytes = await File.ReadAllBytesAsync(Path.Combine(runOutputDir, "envelope.json"), cancellationToken);
        var envelopeShaHex = Convert.ToHexStringLower(SHA256.HashData(envelopeBytes));
        Assert.Equal(expectedEnvelopeShaHex, envelopeShaHex);

        using var envDoc = JsonDocument.Parse(envelopeBytes);
        var env = envDoc.RootElement;

        var documentId = remapIds ? Guid.NewGuid() : Guid.Parse(env.GetProperty("document_id").GetString()!);
        var jobId = remapIds ? Guid.NewGuid() : Guid.Parse(env.GetProperty("job_id").GetString()!);
        var attemptId = remapIds ? Guid.NewGuid() : Guid.Parse(env.GetProperty("attempt_id").GetString()!);
        var resultId = remapIds ? Guid.NewGuid() : originalResultId;
        var submissionKey = remapIds ? Guid.NewGuid() : originalSubmissionKey;

        var inputNode = env.GetProperty("input");
        var pageCount = inputNode.GetProperty("page_count").GetInt32();
        Assert.Equal(expectedPdfShaHex, inputNode.GetProperty("sha256").GetString());

        var outputNode = env.GetProperty("output");
        var finishReason = outputNode.GetProperty("finish_reason").GetString()!;
        var outputPageCount = outputNode.GetProperty("output_page_count").GetInt32();
        Assert.Equal(expectedRawShaHex, outputNode.GetProperty("sha256").GetString());

        var prov = env.GetProperty("provenance");
        var modelRepoId = prov.GetProperty("model_repo_id").GetString()!;
        var modelRevision = prov.GetProperty("model_revision").GetString()!;
        var manifestSha = Convert.FromHexString(prov.GetProperty("model_manifest_sha256").GetString()!);
        var lockSha = Convert.FromHexString(prov.GetProperty("dependency_lock_sha256").GetString()!);
        var workerSourceSha = Convert.FromHexString(prov.GetProperty("worker_source_sha256").GetString()!);
        var workerConfigSha = Convert.FromHexString(prov.GetProperty("worker_config_sha256").GetString()!);
        var rendererIdentity = prov.GetProperty("renderer_identity").GetString()!;
        var genSettingsJson = prov.GetProperty("generation_settings").GetRawText();
        var diagJson = env.GetProperty("diagnostics").GetRawText();

        var timings = env.GetProperty("timings");
        var startedAtUtc = DateTimeOffset.Parse(timings.GetProperty("started_at_utc").GetString()!, System.Globalization.CultureInfo.InvariantCulture).ToUniversalTime();
        var completedAtUtc = DateTimeOffset.Parse(timings.GetProperty("completed_at_utc").GetString()!, System.Globalization.CultureInfo.InvariantCulture).ToUniversalTime();
        var loadMs = timings.GetProperty("load_duration_ms").GetInt64();
        var renderMs = timings.GetProperty("render_duration_ms").GetInt64();
        var inferMs = timings.GetProperty("infer_duration_ms").GetInt64();
        var totalMs = timings.GetProperty("total_duration_ms").GetInt64();
        var submittedAtUtc = startedAtUtc.AddSeconds(-1);

        var dbOptions = new DbContextOptionsBuilder<ELedgerCareDbContext>()
            .UseNpgsql(appConnectionString)
            .Options;

        await using var db = new ELedgerCareDbContext(dbOptions);
        await using var tx = await db.Database.BeginTransactionAsync(System.Data.IsolationLevel.ReadCommitted, cancellationToken);
        await db.Database.ExecuteSqlRawAsync("SET LOCAL synchronous_commit = on", cancellationToken);

        var conn = (NpgsqlConnection)db.Database.GetDbConnection();
        var npgsqlTx = (NpgsqlTransaction)tx.GetDbTransaction();

        // Advance extraction_fencing_seq (F3-BIC-06) so any later extraction operations never collide.
        long fencingToken;
        await using (var seqCmd = new NpgsqlCommand("SELECT nextval('eledgercare.extraction_fencing_seq')", conn, npgsqlTx))
        {
            fencingToken = Convert.ToInt64(await seqCmd.ExecuteScalarAsync(cancellationToken), System.Globalization.CultureInfo.InvariantCulture);
        }

        var document = Document.Submit(documentId, jobId, submissionKey, pdfBytes, pageCount, submittedAtUtc);
        db.Documents.Add(document);
        await db.SaveChangesAsync(cancellationToken);

        const string queueAndRunSql = """
            UPDATE eledgercare.processing_jobs
            SET status = 'running',
                queued_at = @queuedAt,
                updated_at = @startedAt,
                attempt_count = 1,
                latest_fencing_token = @token
            WHERE job_id = @jobId
            """;
        await using (var qCmd = new NpgsqlCommand(queueAndRunSql, conn, npgsqlTx))
        {
            qCmd.Parameters.AddWithValue("queuedAt", submittedAtUtc);
            qCmd.Parameters.AddWithValue("startedAt", startedAtUtc);
            qCmd.Parameters.AddWithValue("token", fencingToken);
            qCmd.Parameters.AddWithValue("jobId", jobId);
            await qCmd.ExecuteNonQueryAsync(cancellationToken);
        }

        var attempt = ExecutionAttempt.Start(
            attemptId,
            jobId,
            documentId,
            attemptNumber: 1,
            fencingToken: fencingToken,
            retriedFromAttemptId: null,
            runDirectoryName: $"attempt-{attemptId:D}",
            supervisorInstanceId: Guid.Parse("101b19cf-3133-4ead-91cb-9ca6068e3e72"),
            supervisorPid: 18496,
            supervisorCreateFileTime: 134393243591895019L,
            startedAtUtc: startedAtUtc);
        db.ExecutionAttempts.Add(attempt);
        await db.SaveChangesAsync(cancellationToken);

        const string completeJobAndAttemptSql = """
            UPDATE eledgercare.processing_jobs
            SET status = 'completed', updated_at = @completedAt
            WHERE job_id = @jobId AND latest_fencing_token = @token;

            UPDATE eledgercare.execution_attempts
            SET status = 'completed',
                phase = 'completed',
                ended_at = @completedAt,
                last_heartbeat_at = @completedAt,
                exit_code = 0
            WHERE attempt_id = @attemptId AND fencing_token = @token;
            """;
        await using (var cCmd = new NpgsqlCommand(completeJobAndAttemptSql, conn, npgsqlTx))
        {
            cCmd.Parameters.AddWithValue("completedAt", completedAtUtc);
            cCmd.Parameters.AddWithValue("jobId", jobId);
            cCmd.Parameters.AddWithValue("attemptId", attemptId);
            cCmd.Parameters.AddWithValue("token", fencingToken);
            await cCmd.ExecuteNonQueryAsync(cancellationToken);
        }

        var result = ExtractionResult.Create(
            resultId,
            documentId,
            jobId,
            attemptId,
            fencingToken,
            pdfSha,
            pdfBytes.Length,
            pageCount,
            rawBytes,
            rawSha,
            modelRepoId,
            modelRevision,
            manifestSha,
            lockSha,
            workerSourceSha,
            workerConfigSha,
            rendererIdentity,
            genSettingsJson,
            finishReason,
            outputPageCount,
            startedAtUtc,
            completedAtUtc,
            loadMs,
            renderMs,
            inferMs,
            totalMs,
            diagJson);

        db.ExtractionResults.Add(result);
        await db.SaveChangesAsync(cancellationToken);
        await tx.CommitAsync(cancellationToken);

        return new SeededDocumentReceipt(
            documentId,
            jobId,
            attemptId,
            resultId,
            fencingToken,
            pdfBytes,
            pdfShaHex,
            rawBytes,
            rawShaHex,
            pageCount,
            remapIds);
    }
}
