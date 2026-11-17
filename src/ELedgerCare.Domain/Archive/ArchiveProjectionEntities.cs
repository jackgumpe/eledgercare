using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using ELedgerCare.Domain.Processing;

namespace ELedgerCare.Domain.Archive;

/// <summary>
/// Append-only completion marker for a deterministic archive machine projection over an immutable ExtractionResult.
/// Even when an extraction result yields zero non-whitespace searchable text units (UnitCount == 0),
/// this parent row is committed so readiness distinguishes empty-text results from unprojected results (F4-BIC-05).
/// </summary>
public sealed class ArchiveResultProjection
{
    private readonly List<ArchiveProjectionUnit> _units = [];

    private ArchiveResultProjection()
    {
        ProjectionVersion = string.Empty;
        RawOutputSha256 = [];
        ProjectionSha256 = [];
    }

    public ArchiveResultProjection(
        Guid resultId,
        Guid documentId,
        string projectionVersion,
        byte[] rawOutputSha256,
        byte[] projectionSha256,
        int unitCount,
        bool hasFallback,
        DateTimeOffset projectedAtUtc,
        IReadOnlyList<ArchiveProjectionUnit> units)
    {
        if (resultId == Guid.Empty)
        {
            throw new ArgumentException("ResultId must be non-empty.", nameof(resultId));
        }

        if (documentId == Guid.Empty)
        {
            throw new ArgumentException("DocumentId must be non-empty.", nameof(documentId));
        }

        if (!string.Equals(projectionVersion, ArchiveSchema.ProjectionVersion, StringComparison.Ordinal))
        {
            throw new ArgumentException($"Unsupported projection version '{projectionVersion}'.", nameof(projectionVersion));
        }

        if (rawOutputSha256 is not { Length: 32 })
        {
            throw new ArgumentException("RawOutputSha256 must be 32 bytes.", nameof(rawOutputSha256));
        }

        if (projectionSha256 is not { Length: 32 })
        {
            throw new ArgumentException("ProjectionSha256 must be 32 bytes.", nameof(projectionSha256));
        }

        if (unitCount < 0 || units.Count != unitCount)
        {
            throw new ArgumentException("UnitCount must match units count.", nameof(unitCount));
        }

        ResultId = resultId;
        DocumentId = documentId;
        ProjectionVersion = projectionVersion;
        RawOutputSha256 = rawOutputSha256.ToArray();
        ProjectionSha256 = projectionSha256.ToArray();
        UnitCount = unitCount;
        HasFallback = hasFallback;
        ProjectedAtUtc = projectedAtUtc;
        _units.AddRange(units);
    }

    public Guid ResultId { get; private set; }

    public Guid DocumentId { get; private set; }

    public string ProjectionVersion { get; private set; }

    public byte[] RawOutputSha256 { get; private set; }

    public byte[] ProjectionSha256 { get; private set; }

    public int UnitCount { get; private set; }

    public bool HasFallback { get; private set; }

    public DateTimeOffset ProjectedAtUtc { get; private set; }

    public IReadOnlyList<ArchiveProjectionUnit> Units => _units;
}

/// <summary>
/// Append-only searchable text unit derived from an ExtractionResult via SafeNativeDisplayParser.
/// </summary>
public sealed class ArchiveProjectionUnit
{
    private ArchiveProjectionUnit()
    {
        ProjectionVersion = string.Empty;
        UnitKind = string.Empty;
        SearchText = string.Empty;
    }

    public ArchiveProjectionUnit(
        Guid resultId,
        string projectionVersion,
        int unitOrdinal,
        Guid documentId,
        int? pageNumber,
        string unitKind,
        bool isFallback,
        string searchText)
    {
        if (resultId == Guid.Empty)
        {
            throw new ArgumentException("ResultId must be non-empty.", nameof(resultId));
        }

        if (documentId == Guid.Empty)
        {
            throw new ArgumentException("DocumentId must be non-empty.", nameof(documentId));
        }

        if (unitOrdinal < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(unitOrdinal));
        }

        if (string.IsNullOrWhiteSpace(searchText) || searchText.Contains('\0', StringComparison.Ordinal))
        {
            throw new ArgumentException("SearchText must be non-whitespace and NUL-free.", nameof(searchText));
        }

        if (string.Equals(unitKind, ArchiveSchema.UnitKindDocumentFallback, StringComparison.Ordinal))
        {
            if (pageNumber is not null || !isFallback)
            {
                throw new ArgumentException("Document fallback unit must have null PageNumber and IsFallback=true.");
            }
        }
        else if (string.Equals(unitKind, ArchiveSchema.UnitKindPageFallback, StringComparison.Ordinal))
        {
            if (pageNumber is null or < 1 or > ExtractionCeilings.MaxExtractionPages || !isFallback)
            {
                throw new ArgumentException("Page fallback unit must have PageNumber in 1..3 and IsFallback=true.");
            }
        }
        else if (string.Equals(unitKind, ArchiveSchema.UnitKindPage, StringComparison.Ordinal))
        {
            if (pageNumber is null or < 1 or > ExtractionCeilings.MaxExtractionPages)
            {
                throw new ArgumentException("Page unit must have PageNumber in 1..3.");
            }
        }
        else
        {
            throw new ArgumentException($"Unsupported unit kind '{unitKind}'.", nameof(unitKind));
        }

        ResultId = resultId;
        ProjectionVersion = projectionVersion;
        UnitOrdinal = unitOrdinal;
        DocumentId = documentId;
        PageNumber = pageNumber;
        UnitKind = unitKind;
        IsFallback = isFallback;
        SearchText = searchText;
    }

    public Guid ResultId { get; private set; }

    public string ProjectionVersion { get; private set; }

    public int UnitOrdinal { get; private set; }

    public Guid DocumentId { get; private set; }

    public int? PageNumber { get; private set; }

    public string UnitKind { get; private set; }

    public bool IsFallback { get; private set; }

    public string SearchText { get; private set; }
}

/// <summary>
/// Deterministic production-only machine projector built strictly over ExtractionResult bytes and
/// SafeNativeDisplayParser (zero non-product imports; F4-BIC-02, F4-BIC-05).
/// </summary>
public static class ArchiveMachineProjector
{
    private const string PageToken = "<PAGE>";
    private static readonly UTF8Encoding StrictUtf8 = new(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true);

    public static ArchiveResultProjection Project(ExtractionResult result, DateTimeOffset projectedAtUtc)
    {
        ArgumentNullException.ThrowIfNull(result);
        return ProjectFromBytes(
            result.ResultId,
            result.DocumentId,
            result.RawOutputBytes,
            result.RawOutputSha256,
            result.PageCount,
            projectedAtUtc);
    }

    public static ArchiveResultProjection ProjectFromBytes(
        Guid resultId,
        Guid documentId,
        byte[] rawOutputBytes,
        byte[] rawOutputSha256,
        int expectedPageCount,
        DateTimeOffset projectedAtUtc)
    {
        ArgumentNullException.ThrowIfNull(rawOutputBytes);
        ArgumentNullException.ThrowIfNull(rawOutputSha256);

        if (rawOutputBytes.Length is < 1 or > ExtractionCeilings.MaxRawOutputBytes)
        {
            throw new ArgumentOutOfRangeException(
                nameof(rawOutputBytes),
                $"Raw output byte length must be within 1..{ExtractionCeilings.MaxRawOutputBytes}.");
        }

        if (expectedPageCount is < 1 or > ExtractionCeilings.MaxExtractionPages)
        {
            throw new ArgumentOutOfRangeException(
                nameof(expectedPageCount),
                $"Expected page count must be within 1..{ExtractionCeilings.MaxExtractionPages}.");
        }

        var computedRawSha = SHA256.HashData(rawOutputBytes);
        if (!CryptographicOperations.FixedTimeEquals(computedRawSha, rawOutputSha256))
        {
            throw new InvalidOperationException("RawOutputSha256 does not match RawOutputBytes.");
        }

        string rawText;
        try
        {
            rawText = StrictUtf8.GetString(rawOutputBytes);
        }
        catch (DecoderFallbackException ex)
        {
            throw new InvalidOperationException("ExtractionResult RawOutputBytes is not valid UTF-8.", ex);
        }

        var units = new List<ArchiveProjectionUnit>();

        void AppendUnit(int? pageNumber, string baseKind, bool fallbackFromStructure, string candidateText)
        {
            var (cleaned, hadNul) = SanitizePostgresTextWithoutTruncation(candidateText);
            if (string.IsNullOrWhiteSpace(cleaned))
            {
                return;
            }

            var isFallback = fallbackFromStructure || hadNul;
            var effectiveKind = pageNumber is null
                ? ArchiveSchema.UnitKindDocumentFallback
                : (fallbackFromStructure ? ArchiveSchema.UnitKindPageFallback : ArchiveSchema.UnitKindPage);

            units.Add(new ArchiveProjectionUnit(
                resultId: resultId,
                projectionVersion: ArchiveSchema.ProjectionVersion,
                unitOrdinal: units.Count,
                documentId: documentId,
                pageNumber: pageNumber,
                unitKind: effectiveKind,
                isFallback: isFallback,
                searchText: cleaned));
        }

        if (!HasExactBoundPhysicalPages(rawText, expectedPageCount))
        {
            // Missing <PAGE>, <PAGE> count disagrees with PageCount, or non-whitespace text precedes the first <PAGE>:
            // emit a single document-level fallback with no fabricated page coordinate (F4-BIC-02).
            AppendUnit(
                pageNumber: null,
                baseKind: ArchiveSchema.UnitKindDocumentFallback,
                fallbackFromStructure: true,
                candidateText: SafeNativeDisplayParser.DecodeBasicEntities(rawText));
        }
        else
        {
            var pages = SafeNativeDisplayParser.ParsePages(rawText);
            for (var pIdx = 0; pIdx < pages.Count; pIdx++)
            {
                var page = pages[pIdx];
                var normalLines = new List<string>();
                var fallbackLines = new List<string>();

                for (var bIdx = 0; bIdx < page.Blocks.Count; bIdx++)
                {
                    var block = page.Blocks[bIdx];
                    switch (block.Kind)
                    {
                        case "text" or "title" or "other" or "footer":
                            if (!string.IsNullOrWhiteSpace(block.Text))
                            {
                                normalLines.Add(block.Text);
                            }

                            break;

                        case "table":
                            if (block.TableRows is not null)
                            {
                                var malformed = block.TableRows.Count == 0 || TableHasNonCellTextOrUnclosedTag(block.Text);
                                foreach (var row in block.TableRows)
                                {
                                    var nonEmptyCells = new List<string>(row.Count);
                                    for (var c = 0; c < row.Count; c++)
                                    {
                                        if (!string.IsNullOrEmpty(row[c]))
                                        {
                                            nonEmptyCells.Add(row[c]);
                                        }
                                    }

                                    if (nonEmptyCells.Count > 0)
                                    {
                                        // Join cells strictly with '\t' whitespace (never '|' or ',') per F4-BIC-02!
                                        normalLines.Add(string.Join('\t', nonEmptyCells));
                                    }
                                }

                                if (malformed && !string.IsNullOrWhiteSpace(block.Text))
                                {
                                    fallbackLines.Add(SafeNativeDisplayParser.DecodeBasicEntities(block.Text));
                                }
                            }
                            else if (!string.IsNullOrWhiteSpace(block.Text))
                            {
                                fallbackLines.Add(block.Text);
                            }

                            break;

                        default:
                            // Includes "raw" (missing <FORK>), "block" (empty/unrecognized header), or any unfamiliar block type.
                            if (!string.IsNullOrWhiteSpace(block.Text))
                            {
                                fallbackLines.Add(block.Text);
                            }

                            break;
                    }
                }

                if (normalLines.Count > 0)
                {
                    AppendUnit(
                        pageNumber: page.PageNumber,
                        baseKind: ArchiveSchema.UnitKindPage,
                        fallbackFromStructure: false,
                        candidateText: string.Join('\n', normalLines));
                }

                if (fallbackLines.Count > 0)
                {
                    AppendUnit(
                        pageNumber: page.PageNumber,
                        baseKind: ArchiveSchema.UnitKindPageFallback,
                        fallbackFromStructure: true,
                        candidateText: string.Join('\n', fallbackLines));
                }
            }
        }

        var hasFallback = units.Any(static u => u.IsFallback);
        var projectionSha256 = ComputeProjectionSha256(
            resultId,
            documentId,
            ArchiveSchema.ProjectionVersion,
            rawOutputSha256,
            hasFallback,
            units);

        return new ArchiveResultProjection(
            resultId: resultId,
            documentId: documentId,
            projectionVersion: ArchiveSchema.ProjectionVersion,
            rawOutputSha256: rawOutputSha256,
            projectionSha256: projectionSha256,
            unitCount: units.Count,
            hasFallback: hasFallback,
            projectedAtUtc: projectedAtUtc,
            units: units);
    }

    public static byte[] ComputeProjectionSha256(
        Guid resultId,
        Guid documentId,
        string projectionVersion,
        ReadOnlySpan<byte> rawOutputSha256,
        bool hasFallback,
        IReadOnlyList<ArchiveProjectionUnit> units)
    {
        using var buffer = new MemoryStream();
        using (var writer = new Utf8JsonWriter(buffer))
        {
            writer.WriteStartObject();
            writer.WriteString("projectionVersion", projectionVersion);
            writer.WriteString("resultId", resultId.ToString("D"));
            writer.WriteString("documentId", documentId.ToString("D"));
            writer.WriteString("rawOutputSha256", Convert.ToHexStringLower(rawOutputSha256));
            writer.WriteBoolean("hasFallback", hasFallback);
            writer.WriteNumber("unitCount", units.Count);
            writer.WriteStartArray("units");
            for (var i = 0; i < units.Count; i++)
            {
                var u = units[i];
                writer.WriteStartObject();
                writer.WriteNumber("ordinal", u.UnitOrdinal);
                if (u.PageNumber is int p)
                {
                    writer.WriteNumber("page", p);
                }
                else
                {
                    writer.WriteNull("page");
                }

                writer.WriteString("kind", u.UnitKind);
                writer.WriteBoolean("fallback", u.IsFallback);
                writer.WriteString("text", u.SearchText);
                writer.WriteEndObject();
            }

            writer.WriteEndArray();
            writer.WriteEndObject();
        }

        return SHA256.HashData(buffer.GetBuffer().AsSpan(0, (int)buffer.Length));
    }

    internal static (string Sanitized, bool HadNul) SanitizePostgresTextWithoutTruncation(string text)
    {
        if (!text.Contains('\0', StringComparison.Ordinal))
        {
            return (text, false);
        }

        return (text.Replace('\0', '\uFFFD'), true);
    }

    private static bool HasExactBoundPhysicalPages(string rawText, int expectedPageCount)
    {
        var count = 0;
        var firstIdx = -1;
        var searchFrom = 0;
        while (searchFrom <= rawText.Length)
        {
            var idx = rawText.IndexOf(PageToken, searchFrom, StringComparison.Ordinal);
            if (idx < 0)
            {
                break;
            }

            if (count == 0)
            {
                firstIdx = idx;
            }

            count++;
            searchFrom = idx + PageToken.Length;
        }

        if (count == 0 || count != expectedPageCount)
        {
            return false;
        }

        if (firstIdx > 0 && !rawText.AsSpan(0, firstIdx).IsWhiteSpace())
        {
            return false;
        }

        return true;
    }

    /// <summary>
    /// Detects malformed table markup, unclosed angle brackets, unbalanced cells/tables, or non-whitespace
    /// character data outside &lt;td&gt;/&lt;th&gt; cells (such as &lt;caption&gt; or stray text) that
    /// <see cref="SafeNativeDisplayParser.ParsePlainTableRows"/> would otherwise drop (F4-BIC-02).
    /// </summary>
    public static bool TableHasNonCellTextOrUnclosedTag(string tableMarkup)
    {
        var inCell = false;
        var openCellTag = string.Empty;
        var tableDepth = 0;
        var sawTableOpen = false;
        var inRow = false;

        var i = 0;
        while (i < tableMarkup.Length)
        {
            var lt = tableMarkup.IndexOf('<', i);
            if (lt < 0)
            {
                if (inCell)
                {
                    return true;
                }

                if (!tableMarkup.AsSpan(i).IsWhiteSpace())
                {
                    return true;
                }

                break;
            }

            if (lt > i && !inCell && !tableMarkup.AsSpan(i, lt - i).IsWhiteSpace())
            {
                return true;
            }

            var gt = tableMarkup.IndexOf('>', lt + 1);
            if (gt < 0)
            {
                return true;
            }

            var rawTag = tableMarkup.AsSpan(lt + 1, gt - lt - 1).Trim();
            if (rawTag.IsEmpty)
            {
                if (!inCell)
                {
                    return true;
                }

                i = gt + 1;
                continue;
            }

            var isClosing = rawTag[0] == '/';
            var tagBody = (isClosing ? rawTag[1..] : rawTag).Trim();
            var nameEnd = 0;
            while (nameEnd < tagBody.Length && char.IsAsciiLetterOrDigit(tagBody[nameEnd]))
            {
                nameEnd++;
            }

            if (nameEnd == 0)
            {
                if (!inCell)
                {
                    return true;
                }

                i = gt + 1;
                continue;
            }

            var tagName = tagBody[..nameEnd].ToString().ToLowerInvariant();
            var isSelfClosing = !isClosing && tagBody[^1] == '/';

            if (inCell)
            {
                if (isClosing && string.Equals(tagName, openCellTag, StringComparison.Ordinal))
                {
                    inCell = false;
                    openCellTag = string.Empty;
                }
                else if (tagName is "table" or "thead" or "tbody" or "tfoot" or "tr" or "td" or "th")
                {
                    // Structural table tag encountered before open cell was closed -> malformed.
                    return true;
                }

                // Other tags inside a cell (<br>, <script>, <img>, etc.) stay inside the cell safely.
                i = gt + 1;
                continue;
            }

            // Outside any <td>/<th> cell:
            if (isSelfClosing)
            {
                return true;
            }

            switch (tagName)
            {
                case "table":
                    if (!isClosing)
                    {
                        if (tableDepth > 0)
                        {
                            return true;
                        }

                        tableDepth = 1;
                        sawTableOpen = true;
                    }
                    else
                    {
                        if (tableDepth != 1 || inRow)
                        {
                            return true;
                        }

                        tableDepth = 0;
                    }

                    break;

                case "thead" or "tbody" or "tfoot":
                    if (tableDepth != 1 || inRow)
                    {
                        return true;
                    }

                    break;

                case "tr":
                    if (tableDepth != 1)
                    {
                        return true;
                    }

                    if (!isClosing)
                    {
                        if (inRow)
                        {
                            return true;
                        }

                        inRow = true;
                    }
                    else
                    {
                        if (!inRow)
                        {
                            return true;
                        }

                        inRow = false;
                    }

                    break;

                case "td" or "th":
                    if (tableDepth != 1 || !inRow || isClosing)
                    {
                        return true;
                    }

                    inCell = true;
                    openCellTag = tagName;
                    break;

                default:
                    // Any non-structural tag outside cells (e.g. <caption>, <colgroup>, <div>) -> malformed/non-cell!
                    return true;
            }

            i = gt + 1;
        }

        return !sawTableOpen || tableDepth != 0 || inRow || inCell;
    }
}
