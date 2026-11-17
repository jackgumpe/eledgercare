using System.Text;

namespace ELedgerCare.Domain.Archive;

public sealed record ParsedArchiveQuery(
    string NormalizedQuery,
    IReadOnlyList<string> Terms,
    ArchiveSourceFilter Source,
    int Limit,
    ArchiveCursorPosition? After);

public sealed record ArchiveQueryValidationError(string Code, string Detail);

/// <summary>
/// Strict raw HTTP query-string parser and validator for GET /api/archive (F4-BIC-01).
/// Rejects malformed percent-encoding, invalid UTF-8 byte sequences, unknown/duplicate parameters,
/// NUL, unpaired UTF-16 surrogates, control characters (other than \t, \r, \n), query/term bounds
/// outside 160/8/64 UTF-16 code units, non-canonical limits outside 1..50, and invalid/mismatched cursors.
/// </summary>
public static class ArchiveQueryValidator
{
    private static readonly UTF8Encoding StrictUtf8 = new(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true);

    public static bool TryValidateRawQueryString(
        string? rawQueryString,
        out ParsedArchiveQuery? parsed,
        out ArchiveQueryValidationError? error)
    {
        parsed = null;
        error = null;

        if (string.IsNullOrEmpty(rawQueryString) || rawQueryString == "?")
        {
            parsed = new ParsedArchiveQuery(
                NormalizedQuery: string.Empty,
                Terms: [],
                Source: ArchiveSourceFilter.All,
                Limit: ArchiveSchema.DefaultLimit,
                After: null);
            return true;
        }

        if (rawQueryString.Length > ArchiveSchema.MaxRawQueryStringLength)
        {
            error = new ArchiveQueryValidationError(
                "invalid_archive_query",
                $"Raw query string exceeds {ArchiveSchema.MaxRawQueryStringLength} characters.");
            return false;
        }

        var body = rawQueryString[0] == '?' ? rawQueryString.AsSpan(1) : rawQueryString.AsSpan();
        var seenKeys = new HashSet<string>(StringComparer.Ordinal);
        string? rawQ = null;
        string? rawSource = null;
        string? rawLimit = null;
        string? rawAfter = null;

        if (!body.IsEmpty)
        {
            var start = 0;
            while (start <= body.Length)
            {
                var ampRel = body[start..].IndexOf('&');
                var seg = ampRel < 0 ? body[start..] : body.Slice(start, ampRel);
                if (seg.IsEmpty)
                {
                    error = new ArchiveQueryValidationError("invalid_archive_query", "Empty query parameter segment is not allowed.");
                    return false;
                }

                var eqIdx = seg.IndexOf('=');
                var encodedKey = eqIdx < 0 ? seg : seg[..eqIdx];
                var encodedVal = eqIdx < 0 ? ReadOnlySpan<char>.Empty : seg[(eqIdx + 1)..];

                string? valReason = null;
                if (!TryPercentDecodeStrictUtf8(encodedKey, out var key, out var keyReason) ||
                    !TryPercentDecodeStrictUtf8(encodedVal, out var val, out valReason))
                {
                    error = new ArchiveQueryValidationError(
                        "invalid_archive_query",
                        keyReason ?? valReason ?? "Query string contains malformed percent-encoding or invalid UTF-8 bytes.");
                    return false;
                }

                if (key is not ("q" or "source" or "limit" or "after"))
                {
                    error = new ArchiveQueryValidationError(
                        "unknown_query_parameter",
                        $"Unsupported query parameter '{SanitizeParameterNameForError(key)}'. Allowed parameters: q, source, limit, after.");
                    return false;
                }

                if (!seenKeys.Add(key))
                {
                    error = new ArchiveQueryValidationError(
                        "duplicate_query_parameter",
                        $"Duplicate query parameter '{key}' is not allowed.");
                    return false;
                }

                switch (key)
                {
                    case "q":
                        rawQ = val;
                        break;
                    case "source":
                        rawSource = val;
                        break;
                    case "limit":
                        rawLimit = val;
                        break;
                    case "after":
                        rawAfter = val;
                        break;
                }

                if (ampRel < 0)
                {
                    break;
                }

                start += ampRel + 1;
            }
        }

        var sourceFilter = ArchiveSourceFilter.All;
        if (rawSource is not null && !ArchiveSourceFilterNames.TryFromWire(rawSource, out sourceFilter))
        {
            error = new ArchiveQueryValidationError(
                "invalid_source_filter",
                "Parameter 'source' must be one of: all, machine, reviewed.");
            return false;
        }

        var limit = ArchiveSchema.DefaultLimit;
        if (rawLimit is not null && !TryParseCanonicalLimit(rawLimit, out limit))
        {
            error = new ArchiveQueryValidationError(
                "invalid_limit",
                $"Parameter 'limit' must be a canonical integer within 1..{ArchiveSchema.MaxLimit}.");
            return false;
        }

        var qValue = rawQ ?? string.Empty;
        if (!ValidateTextCharacters(qValue, out var charError))
        {
            error = charError;
            return false;
        }

        var trimmed = TrimUnicodeWhitespace(qValue);
        if (trimmed.Length > ArchiveSchema.MaxQueryLength)
        {
            error = new ArchiveQueryValidationError(
                "query_too_long",
                $"Query exceeds the maximum length of {ArchiveSchema.MaxQueryLength} characters.");
            return false;
        }

        var terms = SplitUnicodeWhitespaceTerms(trimmed);
        if (terms.Count > ArchiveSchema.MaxTerms)
        {
            error = new ArchiveQueryValidationError(
                "too_many_query_terms",
                $"Query may contain at most {ArchiveSchema.MaxTerms} whitespace-separated terms.");
            return false;
        }

        for (var i = 0; i < terms.Count; i++)
        {
            if (terms[i].Length > ArchiveSchema.MaxTermLength)
            {
                error = new ArchiveQueryValidationError(
                    "query_term_too_long",
                    $"Each query term may contain at most {ArchiveSchema.MaxTermLength} characters.");
                return false;
            }
        }

        ArchiveCursorPosition? cursorPos = null;
        if (rawAfter is not null)
        {
            if (!ArchiveCursor.TryDecodeAndValidate(rawAfter, sourceFilter, terms, out var decodedCursor, out var cursorError))
            {
                error = cursorError;
                return false;
            }

            cursorPos = decodedCursor;
        }

        var normalizedQuery = terms.Count == 0 ? string.Empty : string.Join(' ', terms);
        parsed = new ParsedArchiveQuery(
            NormalizedQuery: normalizedQuery,
            Terms: terms,
            Source: sourceFilter,
            Limit: limit,
            After: cursorPos);
        return true;
    }

    /// <summary>
    /// Escapes SQL LIKE/ILIKE metacharacters ('\', '%', '_') with explicit '\' escape character (F4-BIC-01).
    /// </summary>
    public static string EscapePostgresLikeSubstringPattern(string literalTerm)
    {
        ArgumentNullException.ThrowIfNull(literalTerm);
        var sb = new StringBuilder(literalTerm.Length + 4);
        sb.Append('%');
        for (var i = 0; i < literalTerm.Length; i++)
        {
            var ch = literalTerm[i];
            if (ch is '\\' or '%' or '_')
            {
                sb.Append('\\');
            }

            sb.Append(ch);
        }

        sb.Append('%');
        return sb.ToString();
    }

    private static bool TryParseCanonicalLimit(string rawLimit, out int limit)
    {
        limit = 0;
        if (rawLimit.Length is < 1 or > 2)
        {
            return false;
        }

        if (rawLimit[0] is < '1' or > '9')
        {
            return false;
        }

        for (var i = 1; i < rawLimit.Length; i++)
        {
            if (!char.IsAsciiDigit(rawLimit[i]))
            {
                return false;
            }
        }

        if (!int.TryParse(rawLimit, System.Globalization.NumberStyles.None, System.Globalization.CultureInfo.InvariantCulture, out limit))
        {
            return false;
        }

        return limit is >= 1 and <= ArchiveSchema.MaxLimit;
    }

    private static bool ValidateTextCharacters(string value, out ArchiveQueryValidationError? error)
    {
        error = null;
        for (var i = 0; i < value.Length; i++)
        {
            var ch = value[i];
            if (ch == '\0')
            {
                error = new ArchiveQueryValidationError("invalid_archive_query", "Query must not contain NUL characters.");
                return false;
            }

            if (char.IsHighSurrogate(ch))
            {
                if (i + 1 >= value.Length || !char.IsLowSurrogate(value[i + 1]))
                {
                    error = new ArchiveQueryValidationError("invalid_archive_query", "Query contains an unpaired UTF-16 surrogate.");
                    return false;
                }

                i++;
                continue;
            }

            if (char.IsLowSurrogate(ch))
            {
                error = new ArchiveQueryValidationError("invalid_archive_query", "Query contains an unpaired UTF-16 surrogate.");
                return false;
            }

            if (char.IsControl(ch) && ch is not ('\t' or '\r' or '\n'))
            {
                error = new ArchiveQueryValidationError("invalid_archive_query", "Query contains a forbidden control character.");
                return false;
            }
        }

        return true;
    }

    private static string TrimUnicodeWhitespace(string value)
    {
        var start = 0;
        while (start < value.Length && char.IsWhiteSpace(value[start]))
        {
            start++;
        }

        var end = value.Length;
        while (end > start && char.IsWhiteSpace(value[end - 1]))
        {
            end--;
        }

        return value[start..end];
    }

    private static List<string> SplitUnicodeWhitespaceTerms(string trimmed)
    {
        var terms = new List<string>();
        if (trimmed.Length == 0)
        {
            return terms;
        }

        var i = 0;
        while (i < trimmed.Length)
        {
            while (i < trimmed.Length && char.IsWhiteSpace(trimmed[i]))
            {
                i++;
            }

            if (i >= trimmed.Length)
            {
                break;
            }

            var start = i;
            while (i < trimmed.Length && !char.IsWhiteSpace(trimmed[i]))
            {
                i++;
            }

            terms.Add(trimmed[start..i]);
        }

        return terms;
    }

    private static bool TryPercentDecodeStrictUtf8(
        ReadOnlySpan<char> input,
        out string decoded,
        out string? failureReason)
    {
        decoded = string.Empty;
        failureReason = null;

        if (input.IsEmpty)
        {
            return true;
        }

        var sb = new StringBuilder(input.Length);
        byte[]? byteBuffer = null;

        var i = 0;
        while (i < input.Length)
        {
            var ch = input[i];
            if (ch == '%')
            {
                byteBuffer ??= new byte[input.Length / 3 + 1];
                var count = 0;
                while (i < input.Length && input[i] == '%')
                {
                    if (i + 2 >= input.Length ||
                        !TryParseHexNibble(input[i + 1], out var hi) ||
                        !TryParseHexNibble(input[i + 2], out var lo))
                    {
                        failureReason = "Malformed percent-escape in query string.";
                        return false;
                    }

                    byteBuffer[count++] = (byte)((hi << 4) | lo);
                    i += 3;
                }

                try
                {
                    sb.Append(StrictUtf8.GetString(byteBuffer.AsSpan(0, count)));
                }
                catch (DecoderFallbackException)
                {
                    failureReason = "Query string percent-encoding is not valid UTF-8.";
                    return false;
                }

                continue;
            }

            if (ch == '+')
            {
                sb.Append(' ');
                i++;
                continue;
            }

            if (char.IsHighSurrogate(ch))
            {
                if (i + 1 >= input.Length || !char.IsLowSurrogate(input[i + 1]))
                {
                    failureReason = "Query string contains an unpaired UTF-16 surrogate.";
                    return false;
                }

                sb.Append(ch);
                sb.Append(input[i + 1]);
                i += 2;
                continue;
            }

            if (char.IsLowSurrogate(ch))
            {
                failureReason = "Query string contains an unpaired UTF-16 surrogate.";
                return false;
            }

            sb.Append(ch);
            i++;
        }

        decoded = sb.ToString();
        return true;
    }

    private static bool TryParseHexNibble(char c, out int value)
    {
        if (c is >= '0' and <= '9')
        {
            value = c - '0';
            return true;
        }

        if (c is >= 'a' and <= 'f')
        {
            value = c - 'a' + 10;
            return true;
        }

        if (c is >= 'A' and <= 'F')
        {
            value = c - 'A' + 10;
            return true;
        }

        value = 0;
        return false;
    }

    private static string SanitizeParameterNameForError(string key)
    {
        const int maxLen = 32;
        var sb = new StringBuilder(Math.Min(key.Length, maxLen));
        for (var i = 0; i < key.Length && sb.Length < maxLen; i++)
        {
            var c = key[i];
            sb.Append(char.IsAsciiLetterOrDigit(c) || c is '_' or '-' ? c : '?');
        }

        return sb.ToString();
    }
}
