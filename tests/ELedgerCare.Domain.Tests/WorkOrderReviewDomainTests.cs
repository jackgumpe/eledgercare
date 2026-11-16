using System.Security.Cryptography;
using System.Text;
using ELedgerCare.Domain.Processing;
using ELedgerCare.Domain.Review;
using Xunit;

namespace ELedgerCare.Domain.Tests;

public sealed class WorkOrderReviewDomainTests
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
    public void Genuine_F2_SYN_WO_01_raw_output_resolves_all_five_fields_unambiguously_and_roundtrips_snapshot_json()
    {
        var root = FindRepoRoot();
        var rawPath = Path.Combine(
            root,
            "docs", "reviews", "WP-0006", "eld-next-reviewer", "runtime-execution",
            "runs", "attempt-01a1e571-297a-7f0e-a293-e9e1c0851cd4", "output", "raw_output.utf8.bin");
        var rawBytes = File.ReadAllBytes(rawPath);
        var rawShaHex = Convert.ToHexStringLower(SHA256.HashData(rawBytes));

        Assert.Equal(3236, rawBytes.Length);
        Assert.Equal("7503761ae46afef6adf579881d011764283474354fac3e185598fc7d266aff95", rawShaHex);

        var pages = SafeNativeDisplayParser.ParsePages(Encoding.UTF8.GetString(rawBytes));
        Assert.Single(pages);
        Assert.Equal(36, pages[0].Blocks.Count);

        var resultId = Guid.Parse("01a1e573-a855-7735-96e1-f5d14cada602");
        var snapshot = WorkOrderReviewSuggestions.EvaluateFromParsedPages(resultId, rawShaHex, pages);

        Assert.Equal(WorkOrderReviewSchema.ProfileId, snapshot.ProfileId);
        Assert.Equal(WorkOrderReviewSchema.FieldSchemaVersion, snapshot.FieldSchemaVersion);
        Assert.Equal(WorkOrderReviewSchema.SuggestionPolicyVersion, snapshot.SuggestionPolicyVersion);
        Assert.Equal(5, snapshot.Fields.Count);

        var woId = snapshot.GetCandidate("work_order_id");
        Assert.Equal(MachineCandidateStatus.Suggested, woId.Status);
        Assert.Equal("WO-004192", woId.Value);
        Assert.Equal(new ReviewSourceCoordinate(1, 4, null, null), woId.Source!.ToCoordinate());

        var prop = snapshot.GetCandidate("property_name");
        Assert.Equal(MachineCandidateStatus.Suggested, prop.Status);
        Assert.Equal("Cedar Hollow Apartments", prop.Value);
        Assert.Equal(new ReviewSourceCoordinate(1, 6, null, null), prop.Source!.ToCoordinate());

        var unit = snapshot.GetCandidate("building_unit");
        Assert.Equal(MachineCandidateStatus.Suggested, unit.Status);
        Assert.Equal("Bldg B - Unit 204", unit.Value);
        Assert.Equal(new ReviewSourceCoordinate(1, 8, null, null), unit.Source!.ToCoordinate());

        var date = snapshot.GetCandidate("requested_date");
        Assert.Equal(MachineCandidateStatus.Suggested, date.Status);
        Assert.Equal("2026-10-16", date.Value);
        Assert.Equal(new ReviewSourceCoordinate(1, 10, null, null), date.Source!.ToCoordinate());

        var narrative = snapshot.GetCandidate("issue_and_resolution");
        Assert.Equal(MachineCandidateStatus.Suggested, narrative.Status);
        Assert.Equal(298, narrative.Value!.Length);
        Assert.StartsWith("Air handler fan running continuously", narrative.Value, StringComparison.Ordinal);
        Assert.Equal(new ReviewSourceCoordinate(1, 24, null, null), narrative.Source!.ToCoordinate());

        var json = WorkOrderReviewSuggestions.SerializeSnapshotJson(snapshot);
        var deserialized = WorkOrderReviewSuggestions.DeserializeSnapshotJson(json);
        Assert.Equal(snapshot.ResultId, deserialized.ResultId);
        Assert.Equal(snapshot.RawOutputSha256, deserialized.RawOutputSha256);
        for (var i = 0; i < 5; i++)
        {
            Assert.Equal(snapshot.Fields[i].FieldKey, deserialized.Fields[i].FieldKey);
            Assert.Equal(snapshot.Fields[i].Status, deserialized.Fields[i].Status);
            Assert.Equal(snapshot.Fields[i].Value, deserialized.Fields[i].Value);
            Assert.Equal(snapshot.Fields[i].Source, deserialized.Fields[i].Source);
        }
    }

    [Fact]
    public void Genuine_F2_SYN_MP_01_three_page_invoice_yields_all_missing_suggestions_with_zero_false_matches()
    {
        var root = FindRepoRoot();
        var rawPath = Path.Combine(
            root,
            "docs", "reviews", "WP-0006", "eld-next-reviewer", "runtime-execution",
            "runs", "attempt-01a1e573-ca25-733e-b048-44c8ea2ac61d", "output", "raw_output.utf8.bin");
        var rawBytes = File.ReadAllBytes(rawPath);
        var rawShaHex = Convert.ToHexStringLower(SHA256.HashData(rawBytes));

        Assert.Equal(7511, rawBytes.Length);
        Assert.Equal("c399ad892e257500e2b6a9ac8b0bc3d8a17e9c10041262c4bca6a48fb9b9b639", rawShaHex);

        var pages = SafeNativeDisplayParser.ParsePages(Encoding.UTF8.GetString(rawBytes));
        Assert.Equal(3, pages.Count);

        var snapshot = WorkOrderReviewSuggestions.EvaluateFromParsedPages(Guid.NewGuid(), rawShaHex, pages);
        Assert.All(snapshot.Fields, f =>
        {
            Assert.Equal(MachineCandidateStatus.Missing, f.Status);
            Assert.Null(f.Value);
            Assert.Null(f.Source);
            Assert.Empty(f.CompetingSources);
        });
    }

    [Fact]
    public void Suggestion_policy_enforces_F3_BIC_01_double_colon_table_spans_block_skipping_ambiguity_and_caps()
    {
        var sha = new string('a', 64);

        // 1. Double-colon standalone ("Work Order ID::") and inline ("Property::", "Property: :") are rejected.
        var doubleColonRaw =
            "<PAGE>" +
            "<BLOCK>text[0,0,10,10]<FORK>Work Order ID::\n" +
            "<BLOCK>text[0,0,10,10]<FORK>WO-SHOULD-NOT-MATCH\n" +
            "<BLOCK>text[0,0,10,10]<FORK>Property::\n" +
            "<BLOCK>text[0,0,10,10]<FORK>Building / Unit: :\n";
        var dcSnap = WorkOrderReviewSuggestions.EvaluateFromParsedPages(
            Guid.NewGuid(), sha, SafeNativeDisplayParser.ParsePages(doubleColonRaw));
        Assert.All(dcSnap.Fields, f => Assert.Equal(MachineCandidateStatus.Missing, f.Status));

        // 2. Spanning tables (colspan/rowspan), nested tables, unbalanced tags, and 2-label header rows are rejected,
        //    whereas a clean 2-simple-cell table row and inline text block resolve cleanly.
        var tableRaw =
            "<PAGE>" +
            "<BLOCK>table[0,0,10,10]<FORK><table><tr><td>Work Order ID</td><td colspan=\"2\">WO-SPAN</td></tr></table>\n" +
            "<BLOCK>table[0,0,10,10]<FORK><table><tr><td rowspan=\"2\">Hdr</td><td>Property</td></tr><tr><td>Cedar</td></tr></table>\n" +
            "<BLOCK>table[0,0,10,10]<FORK><table><tr><td><table><tr><td>Building / Unit</td><td>U1</td></tr></table></td><td>X</td></tr></table>\n" +
            "<BLOCK>table[0,0,10,10]<FORK><table><tr><td>Requested Date<td>2026-10-16</tr></table>\n" +
            "<BLOCK>table[0,0,10,10]<FORK><table><tr><th>Work Order ID</th><th>Property</th></tr><tr><td>Building / Unit:</td><td>Unit 09B</td></tr></table>\n" +
            "<BLOCK>text[0,0,10,10]<FORK>Requested Date: 2026-11-01\n";
        var tblSnap = WorkOrderReviewSuggestions.EvaluateFromParsedPages(
            Guid.NewGuid(), sha, SafeNativeDisplayParser.ParsePages(tableRaw));
        Assert.Equal(MachineCandidateStatus.Missing, tblSnap.GetCandidate("work_order_id").Status);
        Assert.Equal(MachineCandidateStatus.Missing, tblSnap.GetCandidate("property_name").Status);
        Assert.Equal("Unit 09B", tblSnap.GetCandidate("building_unit").Value);
        Assert.Equal(new ReviewSourceCoordinate(1, 4, 1, 1), tblSnap.GetCandidate("building_unit").Source!.ToCoordinate());
        Assert.Equal("2026-11-01", tblSnap.GetCandidate("requested_date").Value);
        Assert.Equal(new ReviewSourceCoordinate(1, 5, null, null), tblSnap.GetCandidate("requested_date").Source!.ToCoordinate());

        // 3. No skipping across title/footer/other/label, and non-narrative title label is ignored.
        var noSkipRaw =
            "<PAGE>" +
            "<BLOCK>title[0,0,10,10]<FORK>Work Order ID:\n" +
            "<BLOCK>text[0,0,10,10]<FORK>WO-FROM-TITLE-INVALID\n" +
            "<BLOCK>text[0,0,10,10]<FORK>Property:\n" +
            "<BLOCK>other[0,0,10,10]<FORK>INTERVENING BANNER\n" +
            "<BLOCK>text[0,0,10,10]<FORK>Skipped Property Value\n" +
            "<BLOCK>text[0,0,10,10]<FORK>Building / Unit:\n" +
            "<BLOCK>text[0,0,10,10]<FORK>Requested Date:\n" +
            "<BLOCK>text[0,0,10,10]<FORK>2026-12-01\n";
        var nsSnap = WorkOrderReviewSuggestions.EvaluateFromParsedPages(
            Guid.NewGuid(), sha, SafeNativeDisplayParser.ParsePages(noSkipRaw));
        Assert.Equal(MachineCandidateStatus.Missing, nsSnap.GetCandidate("work_order_id").Status);
        Assert.Equal(MachineCandidateStatus.Missing, nsSnap.GetCandidate("property_name").Status);
        Assert.Equal(MachineCandidateStatus.Missing, nsSnap.GetCandidate("building_unit").Status);
        Assert.Equal("2026-12-01", nsSnap.GetCandidate("requested_date").Value);

        // 4. Duplicate candidate (even with identical value) -> Ambiguous with competing source refs; oversized -> Oversized (not truncated).
        var longId = new string('9', 65);
        var ambigAndOversizedRaw =
            "<PAGE>" +
            "<BLOCK>text[0,0,10,10]<FORK>Property: Oak View\n" +
            "<BLOCK>text[0,0,10,10]<FORK>Work Order ID: " + longId + "\n" +
            "<PAGE>" +
            "<BLOCK>text[0,0,10,10]<FORK>Property:\n" +
            "<BLOCK>text[0,0,10,10]<FORK>Oak View\n";
        var aoSnap = WorkOrderReviewSuggestions.EvaluateFromParsedPages(
            Guid.NewGuid(), sha, SafeNativeDisplayParser.ParsePages(ambigAndOversizedRaw));

        var ambigProp = aoSnap.GetCandidate("property_name");
        Assert.Equal(MachineCandidateStatus.Ambiguous, ambigProp.Status);
        Assert.Null(ambigProp.Value);
        Assert.Null(ambigProp.Source);
        Assert.Equal(2, ambigProp.CompetingSources.Count);
        Assert.Equal(1, ambigProp.CompetingSources[0].PageNumber);
        Assert.Equal(2, ambigProp.CompetingSources[1].PageNumber);

        var overWo = aoSnap.GetCandidate("work_order_id");
        Assert.Equal(MachineCandidateStatus.Oversized, overWo.Status);
        Assert.Null(overWo.Value);
        Assert.NotNull(overWo.Source);
    }

    [Fact]
    public void ReviewTextValidator_and_ReviewRequestDigest_enforce_utf16_caps_surrogates_controls_and_digest_determinism()
    {
        // Leading zeros and valid astral Unicode (2 UTF-16 code units) remain exact.
        Assert.True(ReviewTextValidator.ValidateNonEmptyText("0004192-\U0001F527", 64, allowMultilineWhitespace: false, out _));

        // Multiline narrative allows \r, \n, \t; single-line fields reject them.
        Assert.True(ReviewTextValidator.ValidateNonEmptyText("Line 1\r\n\tLine 2", 4000, allowMultilineWhitespace: true, out _));
        Assert.False(ReviewTextValidator.ValidateNonEmptyText("Line 1\nLine 2", 200, allowMultilineWhitespace: false, out var nlReason));
        Assert.Equal(ReviewTextValidator.TextRejectionReason.DisallowedControlCharacter, nlReason);

        // NUL, unpaired high/low surrogates, whitespace-only, and cap+1 are strictly rejected.
        Assert.False(ReviewTextValidator.ValidateNonEmptyText("WO\0123", 64, false, out var nulReason));
        Assert.Equal(ReviewTextValidator.TextRejectionReason.NullCharacter, nulReason);

        var unpairedHigh = "abc" + '\uD800' + "def";
        var unpairedLow = "abc" + '\uDC00' + "def";
        Assert.False(ReviewTextValidator.ValidateNonEmptyText(unpairedHigh, 64, false, out var highReason));
        Assert.Equal(ReviewTextValidator.TextRejectionReason.UnpairedSurrogate, highReason);
        Assert.False(ReviewTextValidator.ValidateNonEmptyText(unpairedLow, 64, false, out var lowReason));
        Assert.Equal(ReviewTextValidator.TextRejectionReason.UnpairedSurrogate, lowReason);

        Assert.False(ReviewTextValidator.ValidateNonEmptyText("   \t\r\n  ", 4000, true, out var wsReason));
        Assert.Equal(ReviewTextValidator.TextRejectionReason.EmptyOrWhitespaceOnly, wsReason);

        Assert.True(ReviewTextValidator.ValidateNonEmptyText(new string('X', 64), 64, false, out _));
        Assert.False(ReviewTextValidator.ValidateNonEmptyText(new string('X', 65), 64, false, out var lenReason));
        Assert.Equal(ReviewTextValidator.TextRejectionReason.ExceedsMaxLength, lenReason);

        // Request digest determinism & sensitivity.
        var docId = Guid.NewGuid();
        var resId = Guid.NewGuid();
        CanonicalReviewFieldInput[] baseFields =
        [
            new("work_order_id", ReviewFieldDecision.Accepted, "WO-004192", null, new ReviewSourceCoordinate(1, 4, null, null)),
            new("property_name", ReviewFieldDecision.Edited, "Cedar Hollow North", null, null),
            new("building_unit", ReviewFieldDecision.Unknown, null, "Illegible on scan", null),
            new("requested_date", ReviewFieldDecision.Accepted, "2026-10-16", null, null),
            new("issue_and_resolution", ReviewFieldDecision.Unreviewed, null, null, null),
        ];

        var d1 = ReviewRequestDigest.ComputeSha256(docId, WorkOrderReviewSchema.ProfileId, resId, 0, ReviewRevisionStatus.Draft, "Op A", baseFields);
        var d2 = ReviewRequestDigest.ComputeSha256(docId, WorkOrderReviewSchema.ProfileId, resId, 0, ReviewRevisionStatus.Draft, "Op A", baseFields);
        Assert.Equal(d1, d2);

        // Any change in expectedRevision, status, operator label, documentId, or field value produces a distinct digest.
        var diffRev = ReviewRequestDigest.ComputeSha256(docId, WorkOrderReviewSchema.ProfileId, resId, 1, ReviewRevisionStatus.Draft, "Op A", baseFields);
        var diffDoc = ReviewRequestDigest.ComputeSha256(Guid.NewGuid(), WorkOrderReviewSchema.ProfileId, resId, 0, ReviewRevisionStatus.Draft, "Op A", baseFields);
        var diffLabel = ReviewRequestDigest.ComputeSha256(docId, WorkOrderReviewSchema.ProfileId, resId, 0, ReviewRevisionStatus.Draft, "Op B", baseFields);
        Assert.NotEqual(d1, diffRev);
        Assert.NotEqual(d1, diffDoc);
        Assert.NotEqual(d1, diffLabel);
    }
}
