using System.Security.Cryptography;
using System.Text;
using ELedgerCare.Domain.Archive;
using Xunit;

namespace ELedgerCare.Domain.Tests;

public sealed class ArchiveDomainTests
{
    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "ELedgerCare.slnx")))
        {
            dir = dir.Parent;
        }

        return dir?.FullName ?? throw new InvalidOperationException("Repo root not found.");
    }

    [Fact]
    public void Genuine_F2_SYN_WO_01_and_SYN_MP_01_project_onto_bound_pages_without_structural_table_tags_or_punctuation_delimiters()
    {
        var root = FindRepoRoot();
        var woPath = Path.Combine(
            root, "docs", "reviews", "WP-0006", "eld-next-reviewer", "runtime-execution",
            "runs", "attempt-01a1e571-297a-7f0e-a293-e9e1c0851cd4", "output", "raw_output.utf8.bin");
        var mpPath = Path.Combine(
            root, "docs", "reviews", "WP-0006", "eld-next-reviewer", "runtime-execution",
            "runs", "attempt-01a1e573-ca25-733e-b048-44c8ea2ac61d", "output", "raw_output.utf8.bin");

        var woBytes = File.ReadAllBytes(woPath);
        var woSha = SHA256.HashData(woBytes);
        var mpBytes = File.ReadAllBytes(mpPath);
        var mpSha = SHA256.HashData(mpBytes);

        var now = DateTimeOffset.Parse("2026-11-17T08:00:00Z", System.Globalization.CultureInfo.InvariantCulture);

        var woProj = ArchiveMachineProjector.ProjectFromBytes(
            Guid.Parse("01a1e573-a855-7735-96e1-f5d14cada602"),
            Guid.Parse("01a1e571-2838-714b-861b-bf0835d7c90a"),
            woBytes,
            woSha,
            expectedPageCount: 1,
            projectedAtUtc: now);

        Assert.False(woProj.HasFallback);
        Assert.Equal(1, woProj.UnitCount);
        Assert.Single(woProj.Units);
        Assert.Equal(1, woProj.Units[0].PageNumber);
        Assert.False(woProj.Units[0].IsFallback);
        Assert.Contains("WO-004192", woProj.Units[0].SearchText, StringComparison.Ordinal);
        Assert.Contains("0018-TERM-QC", woProj.Units[0].SearchText, StringComparison.Ordinal);
        Assert.Contains("Priority: Urgent [X]", woProj.Units[0].SearchText, StringComparison.Ordinal);
        Assert.DoesNotContain("<table", woProj.Units[0].SearchText, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("<td", woProj.Units[0].SearchText, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("<table><tr><td>", woProj.Units[0].SearchText, StringComparison.Ordinal);

        var mpProj = ArchiveMachineProjector.ProjectFromBytes(
            Guid.Parse("01a1e578-8bfa-7bba-b104-ea8309dbfd9e"),
            Guid.Parse("01a1e573-ca14-72ba-a46a-c84690288e22"),
            mpBytes,
            mpSha,
            expectedPageCount: 3,
            projectedAtUtc: now);

        Assert.False(mpProj.HasFallback);
        Assert.Equal(3, mpProj.UnitCount);
        Assert.Equal([1, 2, 3], mpProj.Units.Select(u => u.PageNumber!.Value).ToArray());
        Assert.All(mpProj.Units, u =>
        {
            Assert.False(u.IsFallback);
            Assert.DoesNotContain("colspan", u.SearchText, StringComparison.OrdinalIgnoreCase);
            Assert.DoesNotContain("<table", u.SearchText, StringComparison.OrdinalIgnoreCase);
        });
        Assert.Contains("MP01-P1", mpProj.Units[0].SearchText, StringComparison.Ordinal);
        Assert.Contains("MP01-P2", mpProj.Units[1].SearchText, StringComparison.Ordinal);
        Assert.Contains("MP01-P3", mpProj.Units[2].SearchText, StringComparison.Ordinal);
        Assert.Contains("$1,535.35", mpProj.Units[2].SearchText, StringComparison.Ordinal);
        Assert.Contains("7.50%", mpProj.Units[2].SearchText, StringComparison.Ordinal);

        // Deterministic projection_sha256 across repeated calls with distinct timestamps.
        var mpProjRepeat = ArchiveMachineProjector.ProjectFromBytes(
            mpProj.ResultId,
            mpProj.DocumentId,
            mpBytes,
            mpSha,
            expectedPageCount: 3,
            projectedAtUtc: now.AddHours(3));
        Assert.Equal(mpProj.ProjectionSha256, mpProjRepeat.ProjectionSha256);
    }

    [Fact]
    public void Machine_projector_handles_caption_tables_missing_fork_unbound_pages_nul_bytes_and_empty_results()
    {
        var now = DateTimeOffset.UtcNow;

        // 1. Table with <caption> and missing <FORK> retains fallback on Page 1 without losing non-cell text.
        var captionRaw =
            "<PAGE>\n" +
            "<BLOCK>text[[1,1,10,10]]<FORK>Normal heading\n" +
            "<BLOCK>table[[1,20,100,80]]<FORK><table><caption>ANNUAL BOILER SCHEDULE</caption><tr><td>RowCell1</td></tr></table>\n" +
            "<BLOCK>unparsed segment without fork token\n";
        var captionBytes = Encoding.UTF8.GetBytes(captionRaw);
        var captionProj = ArchiveMachineProjector.ProjectFromBytes(
            Guid.NewGuid(), Guid.NewGuid(), captionBytes, SHA256.HashData(captionBytes), 1, now);

        Assert.True(captionProj.HasFallback);
        Assert.Equal(2, captionProj.UnitCount);
        Assert.Contains(captionProj.Units, u => !u.IsFallback && u.PageNumber == 1 && u.SearchText.Contains("RowCell1", StringComparison.Ordinal));
        Assert.Contains(captionProj.Units, u =>
            u.IsFallback &&
            u.PageNumber == 1 &&
            u.SearchText.Contains("ANNUAL BOILER SCHEDULE", StringComparison.Ordinal) &&
            u.SearchText.Contains("unparsed segment without fork token", StringComparison.Ordinal));

        // 2. Missing <PAGE> or mismatched <PAGE> count produces document-level fallback with null pageNumber.
        var unboundBytes = Encoding.UTF8.GetBytes("Unstructured raw output without page markers.");
        var unboundProj = ArchiveMachineProjector.ProjectFromBytes(
            Guid.NewGuid(), Guid.NewGuid(), unboundBytes, SHA256.HashData(unboundBytes), 2, now);
        Assert.True(unboundProj.HasFallback);
        Assert.Single(unboundProj.Units);
        Assert.Null(unboundProj.Units[0].PageNumber);
        Assert.Equal(ArchiveSchema.UnitKindDocumentFallback, unboundProj.Units[0].UnitKind);
        Assert.True(unboundProj.Units[0].IsFallback);

        // 3. NUL (\0) is sanitized to U+FFFD without length truncation even on large (> 8,000 char) content.
        var prefix = new string('A', 5_000);
        var suffix = new string('Z', 5_000) + " TAIL-TOKEN-991";
        var nulRaw = $"<PAGE>\n<BLOCK>text[[0,0,10,10]]<FORK>{prefix}\0{suffix}\n";
        var nulBytes = Encoding.UTF8.GetBytes(nulRaw);
        var nulProj = ArchiveMachineProjector.ProjectFromBytes(
            Guid.NewGuid(), Guid.NewGuid(), nulBytes, SHA256.HashData(nulBytes), 1, now);
        Assert.True(nulProj.HasFallback);
        Assert.Single(nulProj.Units);
        Assert.DoesNotContain('\0', nulProj.Units[0].SearchText);
        Assert.Contains('\uFFFD', nulProj.Units[0].SearchText);
        Assert.Contains("TAIL-TOKEN-991", nulProj.Units[0].SearchText, StringComparison.Ordinal);
        Assert.True(nulProj.Units[0].SearchText.Length > 10_000);

        // 4. Empty/whitespace-only extraction output produces unitCount == 0 with a valid completion marker.
        var emptyBytes = Encoding.UTF8.GetBytes("<PAGE>\n<BLOCK>text[[0,0,10,10]]<FORK>   \t  \n");
        var emptyProj = ArchiveMachineProjector.ProjectFromBytes(
            Guid.NewGuid(), Guid.NewGuid(), emptyBytes, SHA256.HashData(emptyBytes), 1, now);
        Assert.Equal(0, emptyProj.UnitCount);
        Assert.Empty(emptyProj.Units);
        Assert.False(emptyProj.HasFallback);
    }

    [Fact]
    public void Raw_query_validator_enforces_utf8_parameter_bounds_escaping_and_cursor_binding()
    {
        // Valid default empty query
        Assert.True(ArchiveQueryValidator.TryValidateRawQueryString(null, out var emptyParsed, out _));
        Assert.Empty(emptyParsed!.Terms);
        Assert.Equal(ArchiveSourceFilter.All, emptyParsed.Source);
        Assert.Equal(20, emptyParsed.Limit);

        // Valid query with literal %, _, \, +, leading zero, and emoji (🔧 = 2 UTF-16 code units)
        var rawValid = "?q=WO-004192+100%25+A_B+%5C+%2B+%F0%9F%94%A7&source=reviewed&limit=50";
        Assert.True(ArchiveQueryValidator.TryValidateRawQueryString(rawValid, out var validParsed, out _));
        Assert.Equal(["WO-004192", "100%", "A_B", "\\", "+", "🔧"], validParsed!.Terms);
        Assert.Equal(ArchiveSourceFilter.Reviewed, validParsed.Source);
        Assert.Equal(50, validParsed.Limit);

        // Explicit ESCAPE '\' pattern escaping
        Assert.Equal(@"%100\%\_a\\b%", ArchiveQueryValidator.EscapePostgresLikeSubstringPattern(@"100%_a\b"));

        // Invalid queries must all fail with 400 validation errors
        string[] invalidRawQueries =
        [
            "?unknown=1",
            "?Q=caseSensitiveKey",
            "?q=a&q=b",
            "?source=all&source=machine",
            "?q=%2",
            "?q=%ZZ",
            "?q=%FF",
            "?q=%C3%28",
            "?q=%ED%A0%80",
            "?q=abc%00def",
            "?q=abc%01def",
            "?q=abc%7Fdef",
            "?source=invalid",
            "?source=",
            "?limit=0",
            "?limit=51",
            "?limit=01",
            "?limit=+5",
            "?limit=-1",
            "?q=" + new string('x', 161),
            // 80 wrench emojis = 160 UTF-16 code units + 'a' = 161 UTF-16 code units -> rejected!
            "?q=" + string.Concat(Enumerable.Repeat("%F0%9F%94%A7", 80)) + "a",
            "?q=t1+t2+t3+t4+t5+t6+t7+t8+t9",
            "?q=" + new string('y', 65),
            "?after=not_valid_json_cursor",
            "?after=" + new string('a', 257),
        ];

        foreach (var bad in invalidRawQueries)
        {
            Assert.False(
                ArchiveQueryValidator.TryValidateRawQueryString(bad, out _, out var err),
                $"Expected invalid query '{bad}' to be rejected.");
            Assert.NotNull(err);
        }

        // Keyset cursor roundtrip and query/source mismatch rejection
        var ts = new DateTimeOffset(2026, 11, 17, 8, 30, 15, 0, TimeSpan.Zero).AddTicks(4560); // .000456s
        var docId = Guid.Parse("01a1e571-2838-714b-861b-bf0835d7c90a");
        var cursor = ArchiveCursor.Encode(ts, docId, ArchiveSourceFilter.All, ["WO-004192", "pump"]);
        Assert.True(cursor.Length <= ArchiveSchema.MaxCursorLength);

        Assert.True(ArchiveQueryValidator.TryValidateRawQueryString(
            $"?q=WO-004192+pump&source=all&after={cursor}", out var withCursor, out _));
        Assert.Equal(ts, withCursor!.After!.SubmittedAtUtc);
        Assert.Equal(docId, withCursor.After.DocumentId);

        // Changing query or source rejects the cursor with cursor_query_mismatch
        Assert.False(ArchiveQueryValidator.TryValidateRawQueryString(
            $"?q=WO-004192+other&source=all&after={cursor}", out _, out var qMismatch));
        Assert.Equal("cursor_query_mismatch", qMismatch!.Code);

        Assert.False(ArchiveQueryValidator.TryValidateRawQueryString(
            $"?q=WO-004192+pump&source=machine&after={cursor}", out _, out var sMismatch));
        Assert.Equal("cursor_query_mismatch", sMismatch!.Code);
    }

    [Fact]
    public void CLocale_matcher_and_snippet_builder_preserve_surrogate_pairs_and_inert_hostile_segments()
    {
        // ASCII case-insensitive, non-ASCII Unicode exact code-unit match (matching PostgreSQL LC_CTYPE=C ILIKE)
        Assert.True(CLocaleTextMatcher.Contains("Cedar Hollow HAWTHORNE", "hawthorne"));
        Assert.True(CLocaleTextMatcher.Contains("Café_100%", "café_100%"));
        Assert.False(CLocaleTextMatcher.Contains("Café", "CAFÉ"));
        Assert.False(CLocaleTextMatcher.Contains("pump\u00ADseal", "pumpseal"));

        // Construct string where 240-UTF16 window boundaries land directly inside astral emoji surrogate pairs (🔧 = 2 units)
        var emojiRun = string.Concat(Enumerable.Repeat("🔧", 90)); // 180 UTF-16 code units
        var fullText = $"{emojiRun} <script>alert('xss')</script> TARGET-TOKEN-77 {emojiRun}";
        var clipped = ArchiveSnippetBuilder.BuildClippedSnippet(fullText, "target-token-77", ["target-token-77", "<script>"]);

        Assert.True(clipped.Snippet.Length <= ArchiveSchema.MaxSnippetLength);
        Assert.True(clipped.PrefixClipped);
        Assert.True(clipped.SuffixClipped);
        Assert.Equal(clipped.Snippet, string.Concat(clipped.Segments.Select(s => s.Text)));
        Assert.Contains(clipped.Segments, s => s.Highlighted && s.Text == "TARGET-TOKEN-77");
        Assert.Contains(clipped.Segments, s => s.Highlighted && s.Text == "<script>");

        // Verify zero unpaired UTF-16 surrogates in snippet or any segment
        foreach (var piece in clipped.Segments.Select(s => s.Text).Append(clipped.Snippet))
        {
            for (var i = 0; i < piece.Length; i++)
            {
                if (char.IsHighSurrogate(piece[i]))
                {
                    Assert.True(i + 1 < piece.Length && char.IsLowSurrogate(piece[i + 1]));
                    i++;
                }
                else
                {
                    Assert.False(char.IsLowSurrogate(piece[i]));
                }
            }
        }
    }
}
