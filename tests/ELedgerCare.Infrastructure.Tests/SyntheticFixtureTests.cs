using System.Security.Cryptography;
using ELedgerCare.Infrastructure.Pdf;
using ELedgerCare.Tests.Shared;
using Xunit;

namespace ELedgerCare.Infrastructure.Tests;

public sealed class SyntheticFixtureTests
{
    private static string FindRepoRoot()
    {
        var root = new DirectoryInfo(AppContext.BaseDirectory);
        while (root is not null && !File.Exists(Path.Combine(root.FullName, "ELedgerCare.slnx")))
        {
            root = root.Parent;
        }

        Assert.NotNull(root);
        return root.FullName;
    }

    /// <summary>
    /// The committed product fixture is exactly the deterministic generator output (source-first provenance).
    /// </summary>
    [Fact]
    public void Committed_fixture_equals_generator_output_and_recorded_digest()
    {
        var root = FindRepoRoot();
        var committed = File.ReadAllBytes(Path.Combine(root, "tests", "fixtures", "F1-SWO-001.pdf"));

        Assert.Equal(SyntheticPdf.CanonicalFixture(), committed);
        Assert.Equal(887, committed.Length);
        Assert.Equal("875a2d8c83c1c1002b38840f8136b60bd5ebcfe8d2df47187bf36454c59497cb", Convert.ToHexStringLower(SHA256.HashData(committed)));
    }

    [Fact]
    public void Committed_f2_dev_fixtures_match_pinned_digests_and_admitted_page_counts()
    {
        var root = FindRepoRoot();
        var admission = new PdfPigAdmission();

        var f01 = File.ReadAllBytes(Path.Combine(root, "tests", "fixtures", "SYN-WO-01-v1-raster300.pdf"));
        Assert.Equal(372_258, f01.Length);
        Assert.Equal("47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd", Convert.ToHexStringLower(SHA256.HashData(f01)));
        var f01Result = admission.Evaluate(f01, maxPages: 50);
        Assert.True(f01Result.IsAdmitted);
        Assert.Equal(1, f01Result.PageCount);

        var f07 = File.ReadAllBytes(Path.Combine(root, "tests", "fixtures", "SYN-MP-01-v0-clean.pdf"));
        Assert.Equal(8_422, f07.Length);
        Assert.Equal("15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3", Convert.ToHexStringLower(SHA256.HashData(f07)));
        var f07Result = admission.Evaluate(f07, maxPages: 50);
        Assert.True(f07Result.IsAdmitted);
        Assert.Equal(3, f07Result.PageCount);
    }

    /// <summary>
    /// F2-KR-01 / F2-BIC-01: production code, UI, dev smoke scripts, and local OCR worker runtime code
    /// must never import, reference, or invoke qualification/, research/, evaluation/, or runtime git.exe.
    /// </summary>
    [Fact]
    public void Product_and_worker_runtime_sources_never_reference_qualification_research_evaluation_or_git_exe()
    {
        var root = FindRepoRoot();
        string[] guardedRoots =
        [
            Path.Combine(root, "src"),
            Path.Combine(root, "web", "src"),
            Path.Combine(root, "web", "e2e"),
            Path.Combine(root, "deploy", "dev"),
            Path.Combine(root, "workers", "local_ocr", "local_ocr"),
        ];
        string[] extraFiles =
        [
            Path.Combine(root, "ELedgerCare.slnx"),
            Path.Combine(root, "workers", "local_ocr", "run_worker.py"),
            Path.Combine(root, "web", "playwright.config.ts"),
            Path.Combine(root, "web", "proxy.conf.mjs"),
        ];

        var files = guardedRoots
            .SelectMany(dir => Directory.EnumerateFiles(dir, "*", SearchOption.AllDirectories))
            .Concat(extraFiles)
            .Where(f => !f.Contains($"{Path.DirectorySeparatorChar}bin{Path.DirectorySeparatorChar}", StringComparison.OrdinalIgnoreCase) &&
                        !f.Contains($"{Path.DirectorySeparatorChar}obj{Path.DirectorySeparatorChar}", StringComparison.OrdinalIgnoreCase) &&
                        !f.Contains($"{Path.DirectorySeparatorChar}__pycache__{Path.DirectorySeparatorChar}", StringComparison.OrdinalIgnoreCase))
            .ToList();

        Assert.NotEmpty(files);

        string[] forbiddenTokens =
        [
            "qualification/", "qualification\\",
            "research/", "research\\",
            "evaluation/", "evaluation\\",
            "git.exe", "git hash-object",
        ];

        foreach (var file in files)
        {
            var content = File.ReadAllText(file);
            // Comments in run-browser-checks.ps1 explain it replaces F1's evaluation runner; inspect non-comment lines in .ps1.
            var lines = file.EndsWith(".ps1", StringComparison.OrdinalIgnoreCase)
                ? string.Join('\n', content.Split('\n').Where(l => !l.TrimStart().StartsWith('#')))
                : content;
            foreach (var token in forbiddenTokens)
            {
                Assert.DoesNotContain(token, lines, StringComparison.OrdinalIgnoreCase);
            }
        }
    }
}
