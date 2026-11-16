using System.Security.Cryptography;
using ELedgerCare.Application.Extraction;
using ELedgerCare.Domain.Processing;

namespace ELedgerCare.Api;

public sealed class LocalOcrOptions
{
    public const string Section = "LocalOcr";

    public bool Enabled { get; set; }

    public int MaxExtractionPages { get; set; } = ExtractionCeilings.MaxExtractionPages;

    public string? ReadOnlyQ0Root { get; set; }

    public string? WritableRuntimeRoot { get; set; }

    public string? LeasedGpuUuid { get; set; }

    public string? WorkerRootPath { get; set; }

    public ExtractionSettings BuildValidatedSettings(string contentRootPath)
    {
        var workerRoot = ResolveWorkerRoot(WorkerRootPath, contentRootPath);
        var modelManifestPath = Path.Combine(workerRoot, "manifests", "model-files.json");
        var depLockPath = Path.Combine(workerRoot, "manifests", "dependency-lock.json");
        if (!File.Exists(modelManifestPath) || !File.Exists(depLockPath))
        {
            throw new InvalidOperationException(
                $"Self-contained worker manifests not found under '{workerRoot}'.");
        }

        var modelManifestSha = SHA256.HashData(File.ReadAllBytes(modelManifestPath));
        var depLockSha = SHA256.HashData(File.ReadAllBytes(depLockPath));
        var workerSourceSha = ExtractionSettings.ComputeWorkerSourceSha256(workerRoot);

        return new ExtractionSettings(
            Enabled,
            MaxExtractionPages,
            ReadOnlyQ0Root,
            WritableRuntimeRoot,
            LeasedGpuUuid,
            workerRoot,
            modelManifestSha,
            depLockSha,
            workerSourceSha);
    }

    private static string ResolveWorkerRoot(string? configuredPath, string contentRootPath)
    {
        if (!string.IsNullOrWhiteSpace(configuredPath))
        {
            var full = Path.GetFullPath(configuredPath);
            if (!Directory.Exists(full))
            {
                throw new InvalidOperationException($"Configured LocalOcr:WorkerRootPath '{full}' does not exist.");
            }

            return full;
        }

        foreach (var start in new[] { contentRootPath, AppContext.BaseDirectory })
        {
            var dir = new DirectoryInfo(start);
            while (dir is not null)
            {
                var candidate = Path.Combine(dir.FullName, "workers", "local_ocr");
                if (File.Exists(Path.Combine(candidate, "run_worker.py")))
                {
                    return candidate;
                }

                dir = dir.Parent;
            }
        }

        throw new InvalidOperationException(
            "Could not locate workers/local_ocr/run_worker.py; configure LocalOcr:WorkerRootPath explicitly.");
    }
}
