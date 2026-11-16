using System.Text;

namespace ELedgerCare.Domain.Processing;

/// <summary>
/// Deterministic, non-HTML, non-eval parser for native Unlimited-OCR-2 output strings.
/// Splits pages on &lt;PAGE&gt; in exact 1..N order and extracts plain-text blocks and plain-text
/// table grids without ever interpreting or emitting executable HTML.
/// </summary>
public static class SafeNativeDisplayParser
{
    private const string PageToken = "<PAGE>";
    private const string BlockToken = "<BLOCK>";
    private const string ForkToken = "<FORK>";

    public static IReadOnlyList<ExtractedPageView> ParsePages(string rawText)
    {
        ArgumentNullException.ThrowIfNull(rawText);
        var positions = new List<int>();
        var searchFrom = 0;
        while (searchFrom <= rawText.Length)
        {
            var idx = rawText.IndexOf(PageToken, searchFrom, StringComparison.Ordinal);
            if (idx < 0)
            {
                break;
            }

            positions.Add(idx);
            searchFrom = idx + PageToken.Length;
        }

        if (positions.Count == 0)
        {
            return [];
        }

        var pages = new List<ExtractedPageView>(positions.Count);
        for (var i = 0; i < positions.Count; i++)
        {
            var contentStart = positions[i] + PageToken.Length;
            var contentEnd = i + 1 < positions.Count ? positions[i + 1] : rawText.Length;
            var pageSlice = rawText[contentStart..contentEnd];
            pages.Add(new ExtractedPageView(
                PageNumber: i + 1,
                RawPageText: PageToken + pageSlice,
                Blocks: ParseBlocks(pageSlice)));
        }

        return pages;
    }

    private static List<ExtractedBlockView> ParseBlocks(string pageBody)
    {
        var blocks = new List<ExtractedBlockView>();
        var blockPositions = new List<int>();
        var pos = 0;
        while (pos <= pageBody.Length)
        {
            var idx = pageBody.IndexOf(BlockToken, pos, StringComparison.Ordinal);
            if (idx < 0)
            {
                break;
            }

            blockPositions.Add(idx);
            pos = idx + BlockToken.Length;
        }

        if (blockPositions.Count == 0)
        {
            var trimmed = pageBody.Trim();
            if (trimmed.Length > 0)
            {
                blocks.Add(new ExtractedBlockView("text", trimmed, null));
            }

            return blocks;
        }

        if (blockPositions[0] > 0)
        {
            var leading = pageBody[..blockPositions[0]].Trim();
            if (leading.Length > 0)
            {
                blocks.Add(new ExtractedBlockView("text", leading, null));
            }
        }

        for (var i = 0; i < blockPositions.Count; i++)
        {
            var start = blockPositions[i] + BlockToken.Length;
            var end = i + 1 < blockPositions.Count ? blockPositions[i + 1] : pageBody.Length;
            var segment = pageBody[start..end];
            var forkIdx = segment.IndexOf(ForkToken, StringComparison.Ordinal);
            if (forkIdx < 0)
            {
                blocks.Add(new ExtractedBlockView("raw", segment.Trim(), null));
                continue;
            }

            var header = segment[..forkIdx];
            var content = segment[(forkIdx + ForkToken.Length)..].TrimEnd('\r', '\n');
            var kind = ExtractBlockKind(header);
            if (string.Equals(kind, "table", StringComparison.OrdinalIgnoreCase) &&
                content.Contains("<table", StringComparison.OrdinalIgnoreCase))
            {
                var rows = ParsePlainTableRows(content);
                blocks.Add(new ExtractedBlockView("table", content, rows));
            }
            else
            {
                blocks.Add(new ExtractedBlockView(kind, DecodeBasicEntities(content), null));
            }
        }

        return blocks;
    }

    private static string ExtractBlockKind(string header)
    {
        var end = 0;
        while (end < header.Length && char.IsAsciiLetter(header[end]))
        {
            end++;
        }

        return end > 0 ? header[..end].ToLowerInvariant() : "block";
    }

    /// <summary>
    /// Bounded non-DOM state-machine parser for native &lt;table&gt;&lt;tr&gt;&lt;td&gt;...&lt;/td&gt;&lt;/tr&gt;&lt;/table&gt; fragments.
    /// Recognizes only table/thead/tbody/tfoot/tr/td/th/br structural tags; any other tag (such as &lt;script&gt;
    /// or &lt;img&gt;) is preserved literally as inert plain text inside the cell so hostile markup is visible
    /// as plain text and never executed.
    /// </summary>
    internal static IReadOnlyList<IReadOnlyList<string>> ParsePlainTableRows(string tableMarkup)
    {
        var rows = new List<IReadOnlyList<string>>();
        List<string>? currentRow = null;
        StringBuilder? currentCell = null;

        var i = 0;
        while (i < tableMarkup.Length)
        {
            var lt = tableMarkup.IndexOf('<', i);
            if (lt < 0)
            {
                if (currentCell is not null)
                {
                    currentCell.Append(DecodeBasicEntities(tableMarkup[i..]));
                }

                break;
            }

            if (lt > i && currentCell is not null)
            {
                currentCell.Append(DecodeBasicEntities(tableMarkup[i..lt]));
            }

            var gt = tableMarkup.IndexOf('>', lt + 1);
            if (gt < 0)
            {
                if (currentCell is not null)
                {
                    currentCell.Append(tableMarkup[lt..]);
                }

                break;
            }

            var rawTag = tableMarkup[(lt + 1)..gt].Trim();
            var isClosing = rawTag.StartsWith('/');
            var tagBody = (isClosing ? rawTag[1..] : rawTag).Trim();
            var nameEnd = 0;
            while (nameEnd < tagBody.Length && char.IsAsciiLetterOrDigit(tagBody[nameEnd]))
            {
                nameEnd++;
            }

            var tagName = tagBody[..nameEnd].ToLowerInvariant();
            switch (tagName)
            {
                case "table" or "thead" or "tbody" or "tfoot":
                    break;
                case "tr":
                    if (!isClosing)
                    {
                        currentRow = [];
                    }
                    else if (currentRow is not null)
                    {
                        if (currentCell is not null)
                        {
                            currentRow.Add(currentCell.ToString().Trim());
                            currentCell = null;
                        }

                        rows.Add(currentRow);
                        currentRow = null;
                    }

                    break;
                case "td" or "th":
                    if (!isClosing)
                    {
                        currentRow ??= [];
                        if (currentCell is not null)
                        {
                            currentRow.Add(currentCell.ToString().Trim());
                        }

                        currentCell = new StringBuilder();
                    }
                    else if (currentCell is not null)
                    {
                        currentRow ??= [];
                        currentRow.Add(currentCell.ToString().Trim());
                        currentCell = null;
                    }

                    break;
                case "br":
                    currentCell?.Append('\n');
                    break;
                default:
                    // Non-table tags (including <script>, <img>, etc.) stay literal plain text!
                    currentCell?.Append(tableMarkup[lt..(gt + 1)]);
                    break;
            }

            i = gt + 1;
        }

        if (currentCell is not null)
        {
            currentRow ??= [];
            currentRow.Add(currentCell.ToString().Trim());
        }

        if (currentRow is { Count: > 0 })
        {
            rows.Add(currentRow);
        }

        return rows;
    }

    public static string DecodeBasicEntities(string value)
    {
        if (!value.Contains('&', StringComparison.Ordinal))
        {
            return value;
        }

        return value
            .Replace("&lt;", "<", StringComparison.Ordinal)
            .Replace("&gt;", ">", StringComparison.Ordinal)
            .Replace("&quot;", "\"", StringComparison.Ordinal)
            .Replace("&#39;", "'", StringComparison.Ordinal)
            .Replace("&#x27;", "'", StringComparison.OrdinalIgnoreCase)
            .Replace("&amp;", "&", StringComparison.Ordinal);
    }
}

public sealed record ExtractedPageView(
    int PageNumber,
    string RawPageText,
    IReadOnlyList<ExtractedBlockView> Blocks);

public sealed record ExtractedBlockView(
    string Kind,
    string Text,
    IReadOnlyList<IReadOnlyList<string>>? TableRows);
