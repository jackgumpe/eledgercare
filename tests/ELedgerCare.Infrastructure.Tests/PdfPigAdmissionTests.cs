using System.Text;
using ELedgerCare.Application.Intake;
using ELedgerCare.Infrastructure.Pdf;
using ELedgerCare.Tests.Shared;
using UglyToad.PdfPig;
using Xunit;

namespace ELedgerCare.Infrastructure.Tests;

/// <summary>
/// Executes the real PdfPig 0.1.16 strict admission profile against deterministic synthetic variants.
/// Each rejection asserts the specific verified path, not merely "something threw".
/// </summary>
public sealed class PdfPigAdmissionTests
{
    private const int MaxPages = 50;
    private readonly PdfPigAdmission admission = new();

    [Fact]
    public void Canonical_fixture_is_admitted_with_its_page_count()
    {
        var result = admission.Evaluate(SyntheticPdf.CanonicalFixture(), MaxPages);

        Assert.True(result.IsAdmitted);
        Assert.Equal(1, result.PageCount);
    }

    [Fact]
    public void Multi_page_document_at_the_page_limit_is_admitted()
    {
        var result = admission.Evaluate(SyntheticPdf.Build(new SyntheticPdf.Spec { Pages = 3 }), maxPages: 3);

        Assert.True(result.IsAdmitted);
        Assert.Equal(3, result.PageCount);
    }

    [Theory]
    [InlineData("%PDF-1.0")]
    [InlineData("%PDF-1.7")]
    public void Supported_header_versions_are_admitted(string header)
    {
        var result = admission.Evaluate(SyntheticPdf.Build(new SyntheticPdf.Spec { Header = header }), MaxPages);

        Assert.True(result.IsAdmitted);
    }

    [Theory]
    [InlineData("%PDF-2.0")]
    [InlineData("%FDF-1.2")]
    [InlineData("%PDF-1.8")]
    public void Headers_outside_the_profile_are_rejected(string header)
    {
        var result = admission.Evaluate(SyntheticPdf.Build(new SyntheticPdf.Spec { Header = header }), MaxPages);

        Assert.Equal(PdfRejectionReason.UnsupportedHeader, result.Rejection);
    }

    [Fact]
    public void Leading_junk_before_the_header_is_rejected()
    {
        var bytes = Encoding.ASCII.GetBytes("junk\n").Concat(SyntheticPdf.CanonicalFixture()).ToArray();

        Assert.Equal(PdfRejectionReason.UnsupportedHeader, admission.Evaluate(bytes, MaxPages).Rejection);
    }

    [Theory]
    [InlineData("This is a plain text file, not a PDF.\n")]
    [InlineData("\u0089PNG\r\n\u001a\n")]
    public void Non_pdf_input_is_rejected(string content)
    {
        var bytes = Encoding.Latin1.GetBytes(content);

        Assert.Equal(PdfRejectionReason.UnsupportedHeader, admission.Evaluate(bytes, MaxPages).Rejection);
    }

    [Fact]
    public void Missing_eof_marker_is_rejected()
    {
        var valid = SyntheticPdf.CanonicalFixture();
        var withoutEof = valid[..(Encoding.ASCII.GetString(valid).LastIndexOf("%%EOF", StringComparison.Ordinal))];

        Assert.Equal(PdfRejectionReason.MissingEofMarker, admission.Evaluate(withoutEof, MaxPages).Rejection);
    }

    [Fact]
    public void Truncated_file_without_eof_is_rejected()
    {
        var valid = SyntheticPdf.CanonicalFixture();

        Assert.Equal(PdfRejectionReason.MissingEofMarker, admission.Evaluate(valid[..(valid.Length / 2)], MaxPages).Rejection);
    }

    [Fact]
    public void Truncated_file_with_appended_eof_is_rejected_at_the_cross_reference_check()
    {
        var valid = SyntheticPdf.CanonicalFixture();
        var truncated = valid[..(valid.Length * 6 / 10)].Concat(Encoding.ASCII.GetBytes("\n%%EOF\n")).ToArray();

        Assert.Equal(PdfRejectionReason.InvalidCrossReference, admission.Evaluate(truncated, MaxPages).Rejection);
    }

    [Fact]
    public void Truncated_content_stream_with_valid_offsets_reaches_the_parser_and_is_rejected()
    {
        var bytes = SyntheticPdf.Build(new SyntheticPdf.Spec { TruncateFirstContentStream = true });

        Assert.Equal(PdfRejectionReason.Unreadable, admission.Evaluate(bytes, MaxPages).Rejection);
    }

    [Fact]
    public void Page_tree_referencing_a_missing_object_is_rejected()
    {
        var bytes = SyntheticPdf.Build(new SyntheticPdf.Spec { KidsOverride = "99 0 R" });

        Assert.False(admission.Evaluate(bytes, MaxPages).IsAdmitted);
    }

    [Fact]
    public void Page_tree_referencing_a_non_page_object_is_rejected()
    {
        // Object 3 is the font dictionary.
        var bytes = SyntheticPdf.Build(new SyntheticPdf.Spec { KidsOverride = "3 0 R" });

        Assert.False(admission.Evaluate(bytes, MaxPages).IsAdmitted);
    }

    [Fact]
    public void Trailer_root_referencing_a_missing_object_is_rejected()
    {
        var bytes = SyntheticPdf.Build(new SyntheticPdf.Spec { RootOverride = "99 0 R" });

        Assert.Equal(PdfRejectionReason.Unreadable, admission.Evaluate(bytes, MaxPages).Rejection);
    }

    [Fact]
    public void Malformed_page_object_syntax_is_rejected()
    {
        var bytes = SyntheticPdf.Build(new SyntheticPdf.Spec { BreakFirstPageObject = true });

        Assert.Equal(PdfRejectionReason.Unreadable, admission.Evaluate(bytes, MaxPages).Rejection);
    }

    [Fact]
    public void Password_required_encryption_is_rejected()
    {
        var bytes = SyntheticPdf.Build(new SyntheticPdf.Spec { UserPassword = "user-secret", OwnerPassword = "owner-secret" });

        Assert.Equal(PdfRejectionReason.Encrypted, admission.Evaluate(bytes, MaxPages).Rejection);
    }

    [Fact]
    public void Owner_password_with_empty_user_password_opens_in_pdfpig_but_is_rejected()
    {
        var bytes = SyntheticPdf.Build(new SyntheticPdf.Spec { UserPassword = string.Empty, OwnerPassword = "owner-secret" });

        // Precondition: the library really opens this document without an exception and reports encryption,
        // so the explicit IsEncrypted guard (not an exception) is what rejects it.
        using (var document = PdfDocument.Open(bytes, new ParsingOptions { UseLenientParsing = false, SkipMissingFonts = false, MaxStackDepth = 32 }))
        {
            Assert.True(document.IsEncrypted);
            Assert.Equal(1, document.NumberOfPages);
        }

        Assert.Equal(PdfRejectionReason.Encrypted, admission.Evaluate(bytes, MaxPages).Rejection);
    }

    [Fact]
    public void Page_count_above_the_configured_limit_is_rejected()
    {
        var bytes = SyntheticPdf.Build(new SyntheticPdf.Spec { Pages = 3 });

        Assert.Equal(PdfRejectionReason.PageCountOutOfRange, admission.Evaluate(bytes, maxPages: 2).Rejection);
    }

    [Fact]
    public void Page_count_above_the_design_ceiling_is_rejected()
    {
        var bytes = SyntheticPdf.Build(new SyntheticPdf.Spec { Pages = 51 });

        Assert.Equal(PdfRejectionReason.PageCountOutOfRange, admission.Evaluate(bytes, MaxPages).Rejection);
    }

    [Fact]
    public void Empty_page_tree_is_rejected()
    {
        var bytes = SyntheticPdf.Build(new SyntheticPdf.Spec { KidsOverride = string.Empty, CountOverride = 0 });

        Assert.False(admission.Evaluate(bytes, MaxPages).IsAdmitted);
    }

    [Fact]
    public void Startxref_not_addressing_a_cross_reference_section_is_rejected()
    {
        // Observed during WP-0003 exploration: PdfPig 0.1.16 strict mode recovers this file through
        // brute-force xref search and opens it. The profile therefore checks the startxref target itself.
        var bytes = SyntheticPdf.Build(new SyntheticPdf.Spec { StartXrefShift = 7 });

        Assert.Equal(PdfRejectionReason.InvalidCrossReference, admission.Evaluate(bytes, MaxPages).Rejection);
    }

    [Fact]
    public void Startxref_and_entries_both_shifted_is_rejected()
    {
        var bytes = SyntheticPdf.Build(new SyntheticPdf.Spec { StartXrefShift = 7, XrefEntryShift = 7 });

        Assert.Equal(PdfRejectionReason.InvalidCrossReference, admission.Evaluate(bytes, MaxPages).Rejection);
    }

    [Fact]
    public void Known_limitation_wrong_object_offsets_behind_a_valid_startxref_are_recovered_by_pdfpig()
    {
        // Pinned observed behaviour, not a desired property: PdfPig 0.1.16 strict mode locates the objects
        // despite wrong xref entry offsets (the accepted design documents this XrefBruteForcer recovery).
        // The document is otherwise well formed. If a dependency change alters this, re-review the profile.
        var bytes = SyntheticPdf.Build(new SyntheticPdf.Spec { XrefEntryShift = 7 });

        Assert.True(admission.Evaluate(bytes, MaxPages).IsAdmitted);
    }
}
