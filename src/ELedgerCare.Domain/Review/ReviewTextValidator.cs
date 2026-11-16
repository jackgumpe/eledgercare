namespace ELedgerCare.Domain.Review;

/// <summary>
/// Strict non-mutating text validator for F3 human review fields, unknown reasons, operator display
/// labels, and machine suggestion candidates (F3-BIC-03).
/// Counts .NET UTF-16 code units consistently; strictly rejects unpaired UTF-16 surrogates, NUL (\0),
/// control characters (except \r, \n, \t in multiline narrative <c>issue_and_resolution</c>),
/// whitespace-only strings, and strings exceeding field limits. Never truncates or silently replaces.
/// </summary>
public static class ReviewTextValidator
{
    public enum TextRejectionReason
    {
        EmptyOrWhitespaceOnly,
        ExceedsMaxLength,
        NullCharacter,
        UnpairedSurrogate,
        DisallowedControlCharacter,
    }

    public static bool ValidateNonEmptyText(
        string value,
        int maxUtf16Chars,
        bool allowMultilineWhitespace,
        out TextRejectionReason? rejection)
    {
        ArgumentNullException.ThrowIfNull(value);
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(maxUtf16Chars);

        // Check structural character validity first so NUL / surrogates / control chars are always
        // classified accurately even if surrounded by whitespace or exceeding length.
        for (var i = 0; i < value.Length; i++)
        {
            var ch = value[i];
            if (ch == '\0')
            {
                rejection = TextRejectionReason.NullCharacter;
                return false;
            }

            if (char.IsHighSurrogate(ch))
            {
                if (i + 1 < value.Length && char.IsLowSurrogate(value[i + 1]))
                {
                    i++; // Valid UTF-16 surrogate pair representing one astral Unicode scalar.
                    continue;
                }

                rejection = TextRejectionReason.UnpairedSurrogate;
                return false;
            }

            if (char.IsLowSurrogate(ch))
            {
                rejection = TextRejectionReason.UnpairedSurrogate;
                return false;
            }

            if (char.IsControl(ch))
            {
                if (allowMultilineWhitespace && ch is '\r' or '\n' or '\t')
                {
                    continue;
                }

                rejection = TextRejectionReason.DisallowedControlCharacter;
                return false;
            }
        }

        if (string.IsNullOrWhiteSpace(value))
        {
            rejection = TextRejectionReason.EmptyOrWhitespaceOnly;
            return false;
        }

        if (value.Length > maxUtf16Chars)
        {
            rejection = TextRejectionReason.ExceedsMaxLength;
            return false;
        }

        rejection = null;
        return true;
    }

    public static string DescribeRejection(string targetName, int maxChars, TextRejectionReason reason) =>
        reason switch
        {
            TextRejectionReason.EmptyOrWhitespaceOnly => $"{targetName} cannot be empty or composed only of whitespace.",
            TextRejectionReason.ExceedsMaxLength => $"{targetName} exceeds the {maxChars}-character UTF-16 limit.",
            TextRejectionReason.NullCharacter => $"{targetName} contains a disallowed NUL character.",
            TextRejectionReason.UnpairedSurrogate => $"{targetName} contains an invalid unpaired UTF-16 surrogate.",
            TextRejectionReason.DisallowedControlCharacter => $"{targetName} contains a disallowed control character.",
            _ => $"{targetName} failed text validation.",
        };
}
