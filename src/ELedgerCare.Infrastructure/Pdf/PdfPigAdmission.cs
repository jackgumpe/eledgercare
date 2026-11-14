using ELedgerCare.Application.Intake;
using UglyToad.PdfPig;
using UglyToad.PdfPig.Exceptions;

namespace ELedgerCare.Infrastructure.Pdf;

/// <summary>
/// Restricted developer-fixture admission profile from the accepted F1 design (step 4), using
/// PdfPig 0.1.16 in strict mode. This is not a PDF conformance validator or hostile-content sandbox:
/// PdfPig may internally parse content streams, attempt decompression fallbacks, recover xrefs and
/// look up local fonts. The application itself never reads page text/letters, renders, runs OCR,
/// executes actions or fetches network resources here.
/// </summary>
public sealed class PdfPigAdmission : IPdfAdmission
{
    private const int MaxStackDepth = 32;
    private static readonly byte[] EofMarker = "%%EOF"u8.ToArray();

    public PdfAdmissionResult Evaluate(ReadOnlyMemory<byte> bytes, int maxPages)
    {
        var span = bytes.Span;
        if (!HasSupportedHeader(span))
        {
            return PdfAdmissionResult.Rejected(PdfRejectionReason.UnsupportedHeader);
        }

        if (!EndsWithEofMarker(span))
        {
            return PdfAdmissionResult.Rejected(PdfRejectionReason.MissingEofMarker);
        }

        // PdfPig 0.1.16 recovers a wrong startxref by brute-force search even with lenient parsing off
        // (observed in WP-0003). The profile requires the final startxref to address a cross-reference
        // section ("xref" table or "N G obj" stream) exactly, so such files are not silently repaired.
        if (!StartXrefAddressesCrossReference(span))
        {
            return PdfAdmissionResult.Rejected(PdfRejectionReason.InvalidCrossReference);
        }

        var options = new ParsingOptions
        {
            UseLenientParsing = false,
            SkipMissingFonts = false,
            MaxStackDepth = MaxStackDepth,
        };

        try
        {
            using var document = PdfDocument.Open(bytes.ToArray(), options);

            // Owner-password encryption with an empty user password opens without an exception.
            if (document.IsEncrypted)
            {
                return PdfAdmissionResult.Rejected(PdfRejectionReason.Encrypted);
            }

            var pageCount = document.NumberOfPages;
            if (pageCount < 1 || pageCount > maxPages)
            {
                return PdfAdmissionResult.Rejected(PdfRejectionReason.PageCountOutOfRange);
            }

            // Exercise the supported page structures only; Text/Letters are never accessed.
            for (var pageNumber = 1; pageNumber <= pageCount; pageNumber++)
            {
                _ = document.GetPage(pageNumber);
            }

            return PdfAdmissionResult.Admitted(pageCount);
        }
        catch (PdfDocumentEncryptedException)
        {
            return PdfAdmissionResult.Rejected(PdfRejectionReason.Encrypted);
        }
        catch (Exception ex) when (ex is not OutOfMemoryException)
        {
            // Any parse failure is a rejection, never an accepted state.
            return PdfAdmissionResult.Rejected(PdfRejectionReason.Unreadable);
        }
    }

    /// <summary>Exact byte-zero header %PDF-1.0 .. %PDF-1.7 followed by PDF whitespace.</summary>
    internal static bool HasSupportedHeader(ReadOnlySpan<byte> span)
    {
        ReadOnlySpan<byte> prefix = "%PDF-1."u8;
        if (span.Length < prefix.Length + 2 || !span.StartsWith(prefix))
        {
            return false;
        }

        var minor = span[prefix.Length];
        return minor is >= (byte)'0' and <= (byte)'7' && IsPdfWhitespace(span[prefix.Length + 1]);
    }

    /// <summary>The last non-whitespace bytes must be the %%EOF marker.</summary>
    internal static bool EndsWithEofMarker(ReadOnlySpan<byte> span)
    {
        var end = span.Length;
        while (end > 0 && IsPdfWhitespace(span[end - 1]))
        {
            end--;
        }

        return span[..end].EndsWith(EofMarker);
    }

    /// <summary>
    /// The last startxref value must be the byte offset of an "xref" keyword or of an indirect object
    /// header ("N G obj", a cross-reference stream). This is a structural precondition, not a validator.
    /// </summary>
    internal static bool StartXrefAddressesCrossReference(ReadOnlySpan<byte> span)
    {
        var keyword = span.LastIndexOf("startxref"u8);
        if (keyword < 0)
        {
            return false;
        }

        var position = SkipWhitespace(span, keyword + "startxref"u8.Length);
        if (!TryReadInteger(span, ref position, out var offset) || offset >= span.Length)
        {
            return false;
        }

        var target = (int)offset;
        if (span[target..].StartsWith("xref"u8))
        {
            return true;
        }

        // Cross-reference stream: "<object number> <generation> obj".
        if (!TryReadInteger(span, ref target, out _))
        {
            return false;
        }

        var afterNumber = SkipWhitespace(span, target);
        if (afterNumber == target || !TryReadInteger(span, ref afterNumber, out _))
        {
            return false;
        }

        var afterGeneration = SkipWhitespace(span, afterNumber);
        return afterGeneration > afterNumber && span[afterGeneration..].StartsWith("obj"u8);
    }

    private static int SkipWhitespace(ReadOnlySpan<byte> span, int position)
    {
        while (position < span.Length && IsPdfWhitespace(span[position]))
        {
            position++;
        }

        return position;
    }

    private static bool TryReadInteger(ReadOnlySpan<byte> span, ref int position, out long value)
    {
        value = 0;
        var start = position;
        while (position < span.Length && span[position] is >= (byte)'0' and <= (byte)'9' && position - start < 10)
        {
            value = (value * 10) + (span[position] - (byte)'0');
            position++;
        }

        return position > start;
    }

    private static bool IsPdfWhitespace(byte value) =>
        value is 0x00 or 0x09 or 0x0A or 0x0C or 0x0D or 0x20;
}
