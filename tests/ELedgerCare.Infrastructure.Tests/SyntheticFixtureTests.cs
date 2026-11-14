using System.Security.Cryptography;
using ELedgerCare.Tests.Shared;
using Xunit;

namespace ELedgerCare.Infrastructure.Tests;

public sealed class SyntheticFixtureTests
{
    /// <summary>
    /// The committed product fixture is exactly the deterministic generator output (source-first provenance).
    /// </summary>
    [Fact]
    public void Committed_fixture_equals_generator_output_and_recorded_digest()
    {
        var root = new DirectoryInfo(AppContext.BaseDirectory);
        while (root is not null && !File.Exists(Path.Combine(root.FullName, "ELedgerCare.slnx")))
        {
            root = root.Parent;
        }

        Assert.NotNull(root);
        var committed = File.ReadAllBytes(Path.Combine(root.FullName, "tests", "fixtures", "F1-SWO-001.pdf"));

        Assert.Equal(SyntheticPdf.CanonicalFixture(), committed);
        Assert.Equal(887, committed.Length);
        Assert.Equal("875a2d8c83c1c1002b38840f8136b60bd5ebcfe8d2df47187bf36454c59497cb", Convert.ToHexStringLower(SHA256.HashData(committed)));
    }
}
