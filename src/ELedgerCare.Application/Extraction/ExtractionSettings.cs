using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using ELedgerCare.Domain.Processing;

namespace ELedgerCare.Application.Extraction;

/// <summary>
/// Validated runtime configuration and pinned artifact digests for local OCR execution.
/// Enabled is false by default until a bounded coordinator runtime release is configured.
/// </summary>
public sealed record ExtractionSettings
{
    public ExtractionSettings(
        bool enabled,
        int maxExtractionPages,
        string? readOnlyQ0Root,
        string? writableRuntimeRoot,
        string? leasedGpuUuid,
        string workerRootPath,
        byte[] modelManifestSha256,
        byte[] dependencyLockSha256,
        byte[] workerSourceSha256)
    {
        if (maxExtractionPages is < 1 or > ExtractionCeilings.MaxExtractionPages)
        {
            throw new ArgumentOutOfRangeException(nameof(maxExtractionPages), maxExtractionPages,
                $"MaxExtractionPages must be within 1..{ExtractionCeilings.MaxExtractionPages}.");
        }

        ArgumentException.ThrowIfNullOrWhiteSpace(workerRootPath);
        ArgumentNullException.ThrowIfNull(modelManifestSha256);
        ArgumentNullException.ThrowIfNull(dependencyLockSha256);
        ArgumentNullException.ThrowIfNull(workerSourceSha256);
        if (modelManifestSha256.Length != 32 || dependencyLockSha256.Length != 32 || workerSourceSha256.Length != 32)
        {
            throw new ArgumentException("Pinned worker/manifest digests must be 32-byte SHA-256 values.");
        }

        if (enabled)
        {
            if (string.IsNullOrWhiteSpace(readOnlyQ0Root) ||
                string.IsNullOrWhiteSpace(writableRuntimeRoot) ||
                string.IsNullOrWhiteSpace(leasedGpuUuid))
            {
                throw new InvalidOperationException(
                    "When LocalOcr:Enabled is true, ReadOnlyQ0Root, WritableRuntimeRoot, and LeasedGpuUuid must all be configured.");
            }
        }

        Enabled = enabled;
        MaxExtractionPages = maxExtractionPages;
        ReadOnlyQ0Root = string.IsNullOrWhiteSpace(readOnlyQ0Root) ? null : Path.GetFullPath(readOnlyQ0Root);
        WritableRuntimeRoot = string.IsNullOrWhiteSpace(writableRuntimeRoot) ? null : Path.GetFullPath(writableRuntimeRoot);
        LeasedGpuUuid = string.IsNullOrWhiteSpace(leasedGpuUuid) ? null : leasedGpuUuid.Trim();
        WorkerRootPath = Path.GetFullPath(workerRootPath);
        ModelManifestSha256 = [.. modelManifestSha256];
        DependencyLockSha256 = [.. dependencyLockSha256];
        WorkerSourceSha256 = [.. workerSourceSha256];
    }

    public bool Enabled { get; }

    public int MaxExtractionPages { get; }

    public string? ReadOnlyQ0Root { get; }

    public string? WritableRuntimeRoot { get; }

    public string? LeasedGpuUuid { get; }

    public string WorkerRootPath { get; }

    public byte[] ModelManifestSha256 { get; }

    public byte[] DependencyLockSha256 { get; }

    public byte[] WorkerSourceSha256 { get; }

    /// <summary>
    /// Computes the exact canonical worker configuration SHA-256 matching workers/local_ocr/local_ocr/protocol.py.
    /// </summary>
    public static byte[] ComputeWorkerConfigSha256(int pageCount)
    {
        if (pageCount is < 1 or > ExtractionCeilings.MaxExtractionPages)
        {
            throw new ArgumentOutOfRangeException(nameof(pageCount));
        }

        var maxNewTokens = 8000 * pageCount;
        var ngramWindow = pageCount > 1 ? 1024 : 128;

        using var buffer = new MemoryStream();
        using (var writer = new Utf8JsonWriter(buffer))
        {
            writer.WriteStartObject();
            writer.WritePropertyName("call_kwargs");
            writer.WriteStartObject();
            writer.WriteNumber("base_size", 1024);
            writer.WriteBoolean("crop_mode", false);
            writer.WriteNumber("dash_topm", 16);
            writer.WriteBoolean("eval_mode", false);
            writer.WriteNumber("image_size", 640);
            writer.WriteNumber("max_crops", 16);
            writer.WriteNumber("max_length", 131072);
            writer.WriteNumber("max_new_tokens", maxNewTokens);
            writer.WriteNumber("max_page_tokens", 20000);
            writer.WriteNull("ngram_whitelist_token_ids");
            writer.WriteNumber("ngram_window", ngramWindow);
            writer.WriteNumber("no_repeat_ngram_size", 35);
            writer.WriteString("output_path", string.Empty);
            writer.WriteBoolean("page_count_guard", true);
            writer.WriteBoolean("save_results", false);
            writer.WritePropertyName("temperature");
            writer.WriteRawValue("0.0");
            writer.WriteBoolean("test_compress", false);
            writer.WriteNumber("tps_interval", 0);
            writer.WriteEndObject();
            writer.WriteString("envelope_schema", ExtractionCeilings.EnvelopeSchema);
            writer.WriteString("model_repo_id", ExtractionCeilings.ModelRepoId);
            writer.WriteString("model_revision", ExtractionCeilings.ModelRevision);
            writer.WriteString("prompt", "Multi page parsing.");
            writer.WriteNumber("render_dpi", 300);
            writer.WriteString("request_schema", ExtractionCeilings.RequestSchema);
            writer.WriteString("worker_id", ExtractionCeilings.WorkerId);
            writer.WriteEndObject();
        }

        return SHA256.HashData(buffer.ToArray());
    }

    public static byte[] ComputeWorkerSourceSha256(string workerRootPath)
    {
        var fullRoot = Path.GetFullPath(workerRootPath);
        var pyFiles = new List<string> { Path.Combine(fullRoot, "run_worker.py") };
        pyFiles.AddRange(Directory.GetFiles(Path.Combine(fullRoot, "local_ocr"), "*.py")
            .OrderBy(Path.GetFileName, StringComparer.Ordinal));

        using var sha = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        foreach (var file in pyFiles)
        {
            var rel = Path.GetRelativePath(fullRoot, file).Replace('\\', '/');
            var raw = File.ReadAllBytes(file);
            var normalized = NormalizeCrLf(raw);
            var fileHex = Convert.ToHexStringLower(SHA256.HashData(normalized));
            var line = Encoding.UTF8.GetBytes($"{rel}:{normalized.Length}:{fileHex}\n");
            sha.AppendData(line);
        }

        return sha.GetHashAndReset();
    }

    private static byte[] NormalizeCrLf(byte[] data)
    {
        var outList = new List<byte>(data.Length);
        for (var i = 0; i < data.Length; i++)
        {
            if (data[i] == (byte)'\r' && i + 1 < data.Length && data[i + 1] == (byte)'\n')
            {
                continue;
            }

            outList.Add(data[i]);
        }

        return [.. outList];
    }
}
