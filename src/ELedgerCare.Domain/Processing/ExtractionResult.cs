using System.Security.Cryptography;
using System.Text;
using ELedgerCare.Domain.Documents;
using ELedgerCare.Domain.Intake;

namespace ELedgerCare.Domain.Processing;

/// <summary>
/// Immutable accepted unreviewed extraction result committed atomically with job/attempt completion.
/// </summary>
public sealed class ExtractionResult
{
    private static readonly UTF8Encoding StrictUtf8 = new(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true);

    private ExtractionResult()
    {
        // Materialization constructor for EF Core.
        SchemaVersion = ExtractionCeilings.EnvelopeSchema;
        InputSha256 = [];
        RawOutputBytes = [];
        RawOutputSha256 = [];
        ModelRepoId = string.Empty;
        ModelRevision = string.Empty;
        ModelManifestSha256 = [];
        DependencyLockSha256 = [];
        WorkerSourceDigest = [];
        WorkerConfigDigest = [];
        RendererIdentity = string.Empty;
        GenerationSettingsJson = "{}";
        FinishReason = ExtractionCeilings.StopFinishReason;
        DiagnosticMetadataJson = "{}";
    }

    private ExtractionResult(
        Guid resultId,
        Guid documentId,
        Guid jobId,
        Guid attemptId,
        long fencingToken,
        byte[] inputSha256,
        int inputByteLength,
        int pageCount,
        byte[] rawOutputBytes,
        byte[] rawOutputSha256,
        string modelRepoId,
        string modelRevision,
        byte[] modelManifestSha256,
        byte[] dependencyLockSha256,
        byte[] workerSourceDigest,
        byte[] workerConfigDigest,
        string rendererIdentity,
        string generationSettingsJson,
        string finishReason,
        int outputPageCount,
        DateTimeOffset startedAtUtc,
        DateTimeOffset completedAtUtc,
        long loadDurationMs,
        long renderDurationMs,
        long inferDurationMs,
        long totalDurationMs,
        string diagnosticMetadataJson)
    {
        ResultId = resultId;
        DocumentId = documentId;
        JobId = jobId;
        AttemptId = attemptId;
        FencingToken = fencingToken;
        SchemaVersion = ExtractionCeilings.EnvelopeSchema;
        InputSha256 = inputSha256;
        InputByteLength = inputByteLength;
        PageCount = pageCount;
        RawOutputBytes = rawOutputBytes;
        RawOutputByteLength = rawOutputBytes.Length;
        RawOutputSha256 = rawOutputSha256;
        ModelRepoId = modelRepoId;
        ModelRevision = modelRevision;
        ModelManifestSha256 = modelManifestSha256;
        DependencyLockSha256 = dependencyLockSha256;
        WorkerSourceDigest = workerSourceDigest;
        WorkerConfigDigest = workerConfigDigest;
        RendererIdentity = rendererIdentity;
        GenerationSettingsJson = generationSettingsJson;
        FinishReason = finishReason;
        OutputPageCount = outputPageCount;
        StartedAtUtc = startedAtUtc;
        CompletedAtUtc = completedAtUtc;
        LoadDurationMs = loadDurationMs;
        RenderDurationMs = renderDurationMs;
        InferDurationMs = inferDurationMs;
        TotalDurationMs = totalDurationMs;
        DiagnosticMetadataJson = diagnosticMetadataJson;
    }

    public Guid ResultId { get; private init; }

    public Guid DocumentId { get; private init; }

    public Guid JobId { get; private init; }

    public Guid AttemptId { get; private init; }

    public long FencingToken { get; private init; }

    public string SchemaVersion { get; private init; }

    public byte[] InputSha256 { get; private init; }

    public int InputByteLength { get; private init; }

    public int PageCount { get; private init; }

    public byte[] RawOutputBytes { get; private init; }

    public int RawOutputByteLength { get; private init; }

    public byte[] RawOutputSha256 { get; private init; }

    public string ModelRepoId { get; private init; }

    public string ModelRevision { get; private init; }

    public byte[] ModelManifestSha256 { get; private init; }

    public byte[] DependencyLockSha256 { get; private init; }

    public byte[] WorkerSourceDigest { get; private init; }

    public byte[] WorkerConfigDigest { get; private init; }

    public string RendererIdentity { get; private init; }

    public string GenerationSettingsJson { get; private init; }

    public string FinishReason { get; private init; }

    public int OutputPageCount { get; private init; }

    public DateTimeOffset StartedAtUtc { get; private init; }

    public DateTimeOffset CompletedAtUtc { get; private init; }

    public long LoadDurationMs { get; private init; }

    public long RenderDurationMs { get; private init; }

    public long InferDurationMs { get; private init; }

    public long TotalDurationMs { get; private init; }

    public string DiagnosticMetadataJson { get; private init; }

    public string DecodeStrictUtf8() => StrictUtf8.GetString(RawOutputBytes);

    public static ExtractionResult Create(
        Guid resultId,
        Guid documentId,
        Guid jobId,
        Guid attemptId,
        long fencingToken,
        byte[] inputSha256,
        int inputByteLength,
        int pageCount,
        byte[] rawOutputBytes,
        byte[] declaredRawOutputSha256,
        string modelRepoId,
        string modelRevision,
        byte[] modelManifestSha256,
        byte[] dependencyLockSha256,
        byte[] workerSourceDigest,
        byte[] workerConfigDigest,
        string rendererIdentity,
        string generationSettingsJson,
        string finishReason,
        int outputPageCount,
        DateTimeOffset startedAtUtc,
        DateTimeOffset completedAtUtc,
        long loadDurationMs,
        long renderDurationMs,
        long inferDurationMs,
        long totalDurationMs,
        string diagnosticMetadataJson)
    {
        RequireNonEmpty(resultId, nameof(resultId));
        RequireNonEmpty(documentId, nameof(documentId));
        RequireNonEmpty(jobId, nameof(jobId));
        RequireNonEmpty(attemptId, nameof(attemptId));
        if (fencingToken < 1)
        {
            throw new ArgumentOutOfRangeException(nameof(fencingToken), fencingToken, "FencingToken must be >= 1.");
        }

        RequireSha256(inputSha256, nameof(inputSha256));
        RequireSha256(declaredRawOutputSha256, nameof(declaredRawOutputSha256));
        RequireSha256(modelManifestSha256, nameof(modelManifestSha256));
        RequireSha256(dependencyLockSha256, nameof(dependencyLockSha256));
        RequireSha256(workerSourceDigest, nameof(workerSourceDigest));
        RequireSha256(workerConfigDigest, nameof(workerConfigDigest));

        if (inputByteLength is < 1 or > AdmissionCeilings.MaxDocumentBytes)
        {
            throw new ArgumentOutOfRangeException(nameof(inputByteLength), inputByteLength, "Invalid inputByteLength.");
        }

        if (pageCount is < 1 or > ExtractionCeilings.MaxExtractionPages)
        {
            throw new ArgumentOutOfRangeException(nameof(pageCount), pageCount,
                $"Extraction result pageCount must be within 1..{ExtractionCeilings.MaxExtractionPages}.");
        }

        ArgumentNullException.ThrowIfNull(rawOutputBytes);
        if (rawOutputBytes.Length is < 1 or > ExtractionCeilings.MaxRawOutputBytes)
        {
            throw new ArgumentOutOfRangeException(nameof(rawOutputBytes), rawOutputBytes.Length,
                $"Raw output must contain 1..{ExtractionCeilings.MaxRawOutputBytes} bytes.");
        }

        var recomputedRawSha = SHA256.HashData(rawOutputBytes);
        if (!CryptographicOperations.FixedTimeEquals(recomputedRawSha, declaredRawOutputSha256))
        {
            throw new ArgumentException("Declared raw output SHA-256 disagrees with rawOutputBytes.", nameof(declaredRawOutputSha256));
        }

        var decodedText = StrictUtf8.GetString(rawOutputBytes);
        if (finishReason != ExtractionCeilings.StopFinishReason)
        {
            throw new ArgumentException("Only finishReason='stop' can be published as a completed result.", nameof(finishReason));
        }

        if (outputPageCount != pageCount)
        {
            throw new ArgumentException("OutputPageCount must equal input PageCount.", nameof(outputPageCount));
        }

        var parsedPages = SafeNativeDisplayParser.ParsePages(decodedText);
        if (parsedPages.Count != pageCount)
        {
            throw new ArgumentException(
                $"Parsed <PAGE> section count ({parsedPages.Count}) disagreed with PageCount ({pageCount}).",
                nameof(rawOutputBytes));
        }

        if (modelRepoId != ExtractionCeilings.ModelRepoId || modelRevision != ExtractionCeilings.ModelRevision)
        {
            throw new ArgumentException("Model identity does not match pinned unmodified checkpoint.");
        }

        ArgumentException.ThrowIfNullOrWhiteSpace(rendererIdentity);
        ArgumentException.ThrowIfNullOrWhiteSpace(generationSettingsJson);
        ArgumentException.ThrowIfNullOrWhiteSpace(diagnosticMetadataJson);

        return new ExtractionResult(
            resultId,
            documentId,
            jobId,
            attemptId,
            fencingToken,
            [.. inputSha256],
            inputByteLength,
            pageCount,
            [.. rawOutputBytes],
            recomputedRawSha,
            modelRepoId,
            modelRevision,
            [.. modelManifestSha256],
            [.. dependencyLockSha256],
            [.. workerSourceDigest],
            [.. workerConfigDigest],
            rendererIdentity,
            generationSettingsJson,
            finishReason,
            outputPageCount,
            startedAtUtc,
            completedAtUtc,
            Math.Max(0, loadDurationMs),
            Math.Max(0, renderDurationMs),
            Math.Max(0, inferDurationMs),
            Math.Max(0, totalDurationMs),
            diagnosticMetadataJson);
    }

    private static void RequireSha256(byte[]? digest, string name)
    {
        ArgumentNullException.ThrowIfNull(digest, name);
        if (digest.Length != OriginalArtifact.Sha256Length)
        {
            throw new ArgumentException($"SHA-256 digest must be {OriginalArtifact.Sha256Length} bytes.", name);
        }
    }

    private static void RequireNonEmpty(Guid value, string name)
    {
        if (value == Guid.Empty)
        {
            throw new ArgumentException("Identifier must be a non-empty UUID.", name);
        }
    }
}
