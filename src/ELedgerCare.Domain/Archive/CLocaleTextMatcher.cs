namespace ELedgerCare.Domain.Archive;

/// <summary>
/// Exact C# mirror of PostgreSQL 18.7 ILIKE semantics under initdb --encoding=UTF8 --no-locale (LC_CTYPE = C).
/// Folds ASCII 'A'..'Z' to 'a'..'z' only and compares all non-ASCII Unicode code units by exact Ordinal equality,
/// preventing SQL-vs-.NET witness/highlight drift (F4-BIC-01).
/// </summary>
public static class CLocaleTextMatcher
{
    public static char FoldAsciiUpper(char c) =>
        c is >= 'A' and <= 'Z' ? (char)(c + ('a' - 'A')) : c;

    public static bool Contains(ReadOnlySpan<char> haystack, ReadOnlySpan<char> needle) =>
        IndexOf(haystack, needle, 0) >= 0;

    public static int IndexOf(ReadOnlySpan<char> haystack, ReadOnlySpan<char> needle, int startIndex = 0)
    {
        if (needle.IsEmpty)
        {
            return startIndex <= haystack.Length ? startIndex : -1;
        }

        if (startIndex < 0 || needle.Length > haystack.Length - startIndex)
        {
            return -1;
        }

        var firstFolded = FoldAsciiUpper(needle[0]);
        var lastStart = haystack.Length - needle.Length;

        for (var i = startIndex; i <= lastStart; i++)
        {
            if (FoldAsciiUpper(haystack[i]) != firstFolded)
            {
                continue;
            }

            var matched = true;
            for (var j = 1; j < needle.Length; j++)
            {
                if (FoldAsciiUpper(haystack[i + j]) != FoldAsciiUpper(needle[j]))
                {
                    matched = false;
                    break;
                }
            }

            if (matched)
            {
                return i;
            }
        }

        return -1;
    }

    public static int CountNonOverlappingOccurrences(ReadOnlySpan<char> haystack, ReadOnlySpan<char> needle)
    {
        if (needle.IsEmpty)
        {
            return 0;
        }

        var count = 0;
        var pos = 0;
        while (pos <= haystack.Length - needle.Length)
        {
            var idx = IndexOf(haystack, needle, pos);
            if (idx < 0)
            {
                break;
            }

            count++;
            pos = idx + needle.Length;
        }

        return count;
    }

    public static List<(int Start, int End)> FindAllIntervals(ReadOnlySpan<char> haystack, ReadOnlySpan<char> needle)
    {
        var intervals = new List<(int Start, int End)>();
        if (needle.IsEmpty)
        {
            return intervals;
        }

        var pos = 0;
        while (pos <= haystack.Length - needle.Length)
        {
            var idx = IndexOf(haystack, needle, pos);
            if (idx < 0)
            {
                break;
            }

            intervals.Add((idx, idx + needle.Length));
            pos = idx + needle.Length;
        }

        return intervals;
    }
}
