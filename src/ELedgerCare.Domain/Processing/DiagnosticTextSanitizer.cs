using System.Text;
using System.Text.Json;

namespace ELedgerCare.Domain.Processing;

/// <summary>
/// Sanitizes bounded failure/diagnostic text and JSON for PostgreSQL text/jsonb columns (F2-S1-03)
/// without ever altering accepted raw UTF-8 output bytes (stored in bytea) or original PDF bytes.
/// </summary>
public static class DiagnosticTextSanitizer
{
    public const int MaxFailureCodeChars = 100;
    public const int MaxDiagnosticJsonBytes = 65_536;

    /// <summary>
    /// Produces a PostgreSQL-safe UTF-8/UTF-16 text value bounded to <paramref name="maxChars"/> UTF-16 code units:
    /// replaces U+0000 (NUL) and unpaired UTF-16 surrogates with U+FFFD, and never splits a surrogate pair across the cap.
    /// </summary>
    public static string? SanitizeForPostgresText(string? value, int maxChars)
    {
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(maxChars);
        if (value is null)
        {
            return null;
        }

        if (value.Length == 0)
        {
            return string.Empty;
        }

        var sb = new StringBuilder(Math.Min(value.Length, maxChars));
        var i = 0;
        while (i < value.Length && sb.Length < maxChars)
        {
            var ch = value[i];
            if (ch == '\0')
            {
                sb.Append('\uFFFD');
                i++;
            }
            else if (char.IsHighSurrogate(ch))
            {
                if (i + 1 < value.Length && char.IsLowSurrogate(value[i + 1]))
                {
                    if (sb.Length + 2 > maxChars)
                    {
                        // Avoid splitting a valid astral scalar across the truncation boundary.
                        break;
                    }

                    sb.Append(ch);
                    sb.Append(value[i + 1]);
                    i += 2;
                }
                else
                {
                    sb.Append('\uFFFD');
                    i++;
                }
            }
            else if (char.IsLowSurrogate(ch))
            {
                sb.Append('\uFFFD');
                i++;
            }
            else
            {
                sb.Append(ch);
                i++;
            }
        }

        return sb.ToString();
    }

    public static string SanitizeRequiredForPostgresText(string? value, int maxChars, string fallback)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(fallback);
        var sanitized = SanitizeForPostgresText(value, maxChars);
        return string.IsNullOrWhiteSpace(sanitized) ? fallback : sanitized;
    }

    /// <summary>
    /// Decodes a bounded diagnostic UTF-8 preview from rejected/failed raw bytes, avoiding mid-sequence splits,
    /// U+0000 NUL bytes, and surrogate splits.
    /// </summary>
    public static string? DecodeBoundedPreview(byte[]? rawBytes, int maxChars)
    {
        if (rawBytes is null || rawBytes.Length == 0)
        {
            return null;
        }

        // At most 4 UTF-8 bytes per UTF-16 code unit; trim incomplete trailing UTF-8 continuation bytes if sliced.
        var maxByteSlice = (int)Math.Min(rawBytes.Length, (long)maxChars * 4);
        var span = TrimIncompleteUtf8Tail(rawBytes.AsSpan(0, maxByteSlice));
        var decoded = Encoding.UTF8.GetString(span);
        return SanitizeForPostgresText(decoded, maxChars);
    }

    /// <summary>
    /// Ensures diagnostic metadata JSON is valid UTF-8 JSON free of U+0000 (which PostgreSQL jsonb rejects with 22P02)
    /// and bounded in byte size; returns null if absent or malformed.
    /// </summary>
    public static string? SanitizeDiagnosticJsonOrNull(string? rawJson, int maxUtf8Bytes = MaxDiagnosticJsonBytes)
    {
        if (string.IsNullOrWhiteSpace(rawJson))
        {
            return null;
        }

        try
        {
            using var doc = JsonDocument.Parse(rawJson);
            using var buffer = new MemoryStream();
            using (var writer = new Utf8JsonWriter(buffer))
            {
                WriteSanitizedElement(writer, doc.RootElement);
            }

            return buffer.Length <= maxUtf8Bytes
                ? Encoding.UTF8.GetString(buffer.GetBuffer(), 0, (int)buffer.Length)
                : "{\"truncated\":true}";
        }
        catch (Exception ex) when (ex is JsonException or EncoderFallbackException)
        {
            return null;
        }
    }

    private static void WriteSanitizedElement(Utf8JsonWriter writer, JsonElement element)
    {
        switch (element.ValueKind)
        {
            case JsonValueKind.Object:
                writer.WriteStartObject();
                foreach (var prop in element.EnumerateObject())
                {
                    var safeName = SanitizeForPostgresText(prop.Name, 256) ?? "key";
                    writer.WritePropertyName(safeName);
                    WriteSanitizedElement(writer, prop.Value);
                }

                writer.WriteEndObject();
                break;

            case JsonValueKind.Array:
                writer.WriteStartArray();
                foreach (var item in element.EnumerateArray())
                {
                    WriteSanitizedElement(writer, item);
                }

                writer.WriteEndArray();
                break;

            case JsonValueKind.String:
                writer.WriteStringValue(SanitizeForPostgresText(element.GetString(), ExecutionAttempt.MaxDiagnosticOutputChars));
                break;

            case JsonValueKind.Number:
                writer.WriteRawValue(element.GetRawText(), skipInputValidation: true);
                break;

            case JsonValueKind.True:
                writer.WriteBooleanValue(true);
                break;

            case JsonValueKind.False:
                writer.WriteBooleanValue(false);
                break;

            default:
                writer.WriteNullValue();
                break;
        }
    }

    private static ReadOnlySpan<byte> TrimIncompleteUtf8Tail(ReadOnlySpan<byte> span)
    {
        if (span.IsEmpty || span.Length < 4)
        {
            return span;
        }

        // Check last 1..3 bytes for an unfinished multi-byte UTF-8 lead byte.
        var idx = span.Length - 1;
        var continuations = 0;
        while (idx >= 0 && continuations < 3 && (span[idx] & 0b1100_0000) == 0b1000_0000)
        {
            continuations++;
            idx--;
        }

        if (idx >= 0 && idx >= span.Length - 4)
        {
            var lead = span[idx];
            var expectedLen = lead switch
            {
                >= 0b1111_0000 and <= 0b1111_0111 => 4,
                >= 0b1110_0000 and <= 0b1110_1111 => 3,
                >= 0b1100_0000 and <= 0b1101_1111 => 2,
                _ => 1,
            };
            if (expectedLen > 1 && idx + expectedLen > span.Length)
            {
                return span[..idx];
            }
        }

        return span;
    }
}
