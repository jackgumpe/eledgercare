using System.Buffers.Text;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace ELedgerCare.Domain.Archive;

public sealed record ArchiveCursorPosition(
    DateTimeOffset SubmittedAtUtc,
    long SubmittedAtUnixMicros,
    Guid DocumentId);

/// <summary>
/// Structural and query-binding keyset cursor codec for GET /api/archive (F4-BIC-06).
/// Binds cursor version, normalized (source, terms) SHA-256 scope digest, exact UTC microsecond
/// timestamptz value, and canonical lowercase UUID within &lt;= 256 Base64Url characters.
/// Note: rejects malformed shape/version/range/query mismatch; does not perform cryptographic HMAC authentication.
/// </summary>
public static class ArchiveCursor
{
    // Reasonable timestamptz microsecond range: 2000-01-01T00:00:00Z .. 2200-01-01T00:00:00Z.
    private const long MinUnixMicros = 946_684_800_000_000L;
    private const long MaxUnixMicros = 7_258_118_400_000_000L;
    private const long TicksPerMicrosecond = 10L;

    public static long ToUnixMicroseconds(DateTimeOffset utcTimestamp)
    {
        var utcTicks = utcTimestamp.UtcDateTime.Ticks;
        var epochTicks = DateTime.UnixEpoch.Ticks;
        return (utcTicks - epochTicks) / TicksPerMicrosecond;
    }

    public static DateTimeOffset FromUnixMicroseconds(long unixMicros)
    {
        var ticks = DateTime.UnixEpoch.Ticks + checked(unixMicros * TicksPerMicrosecond);
        return new DateTimeOffset(ticks, TimeSpan.Zero);
    }

    public static string ComputeQueryScopeDigestHex(ArchiveSourceFilter source, IReadOnlyList<string> terms)
    {
        using var ms = new MemoryStream();
        using (var writer = new Utf8JsonWriter(ms))
        {
            writer.WriteStartObject();
            writer.WriteString("v", ArchiveSchema.CursorVersion);
            writer.WriteString("source", source.ToWire());
            writer.WriteStartArray("terms");
            for (var i = 0; i < terms.Count; i++)
            {
                writer.WriteStringValue(terms[i]);
            }

            writer.WriteEndArray();
            writer.WriteEndObject();
        }

        return Convert.ToHexStringLower(SHA256.HashData(ms.GetBuffer().AsSpan(0, (int)ms.Length)));
    }

    public static string Encode(
        DateTimeOffset submittedAtUtc,
        Guid documentId,
        ArchiveSourceFilter source,
        IReadOnlyList<string> terms)
    {
        if (documentId == Guid.Empty)
        {
            throw new ArgumentException("DocumentId must be non-empty.", nameof(documentId));
        }

        var micros = ToUnixMicroseconds(submittedAtUtc);
        var digestHex = ComputeQueryScopeDigestHex(source, terms);

        using var ms = new MemoryStream();
        using (var writer = new Utf8JsonWriter(ms))
        {
            writer.WriteStartObject();
            writer.WriteString("v", ArchiveSchema.CursorVersion);
            writer.WriteNumber("t", micros);
            writer.WriteString("id", documentId.ToString("D"));
            writer.WriteString("s", source.ToWire());
            writer.WriteString("qh", digestHex);
            writer.WriteEndObject();
        }

        var encoded = Base64Url.EncodeToString(ms.GetBuffer().AsSpan(0, (int)ms.Length));
        if (encoded.Length > ArchiveSchema.MaxCursorLength)
        {
            throw new InvalidOperationException($"Encoded archive cursor length {encoded.Length} exceeds ceiling {ArchiveSchema.MaxCursorLength}.");
        }

        return encoded;
    }

    public static bool TryDecodeAndValidate(
        string? cursor,
        ArchiveSourceFilter expectedSource,
        IReadOnlyList<string> expectedTerms,
        out ArchiveCursorPosition? position,
        out ArchiveQueryValidationError? error)
    {
        position = null;
        error = null;

        if (string.IsNullOrEmpty(cursor) || cursor.Length > ArchiveSchema.MaxCursorLength)
        {
            error = new ArchiveQueryValidationError(
                "invalid_archive_cursor",
                $"Parameter 'after' must be a valid non-empty cursor of at most {ArchiveSchema.MaxCursorLength} characters.");
            return false;
        }

        for (var i = 0; i < cursor.Length; i++)
        {
            var ch = cursor[i];
            var isValidBase64Url = char.IsAsciiLetterOrDigit(ch) || ch is '-' or '_';
            if (!isValidBase64Url)
            {
                error = new ArchiveQueryValidationError("invalid_archive_cursor", "Parameter 'after' contains invalid cursor characters.");
                return false;
            }
        }

        byte[] utf8Bytes;
        try
        {
            utf8Bytes = Base64Url.DecodeFromChars(cursor);
        }
        catch (FormatException)
        {
            error = new ArchiveQueryValidationError("invalid_archive_cursor", "Parameter 'after' is not valid Base64Url.");
            return false;
        }

        try
        {
            using var doc = JsonDocument.Parse(utf8Bytes, new JsonDocumentOptions
            {
                AllowTrailingCommas = false,
                CommentHandling = JsonCommentHandling.Disallow,
                MaxDepth = 4,
            });

            if (doc.RootElement.ValueKind != JsonValueKind.Object)
            {
                error = new ArchiveQueryValidationError("invalid_archive_cursor", "Cursor payload must be a JSON object.");
                return false;
            }

            var propCount = 0;
            foreach (var _ in doc.RootElement.EnumerateObject())
            {
                propCount++;
            }

            if (propCount != 5 ||
                !doc.RootElement.TryGetProperty("v", out var vEl) || vEl.ValueKind != JsonValueKind.String ||
                !doc.RootElement.TryGetProperty("t", out var tEl) || tEl.ValueKind != JsonValueKind.Number ||
                !doc.RootElement.TryGetProperty("id", out var idEl) || idEl.ValueKind != JsonValueKind.String ||
                !doc.RootElement.TryGetProperty("s", out var sEl) || sEl.ValueKind != JsonValueKind.String ||
                !doc.RootElement.TryGetProperty("qh", out var qhEl) || qhEl.ValueKind != JsonValueKind.String)
            {
                error = new ArchiveQueryValidationError("invalid_archive_cursor", "Cursor payload has an invalid structure.");
                return false;
            }

            if (!string.Equals(vEl.GetString(), ArchiveSchema.CursorVersion, StringComparison.Ordinal))
            {
                error = new ArchiveQueryValidationError("invalid_archive_cursor", "Unsupported archive cursor version.");
                return false;
            }

            if (!tEl.TryGetInt64(out var micros) || micros < MinUnixMicros || micros > MaxUnixMicros)
            {
                error = new ArchiveQueryValidationError("invalid_archive_cursor", "Cursor timestamp is out of bounds.");
                return false;
            }

            var idStr = idEl.GetString()!;
            if (!IsCanonicalLowercaseNonZeroUuid(idStr, out var docId))
            {
                error = new ArchiveQueryValidationError("invalid_archive_cursor", "Cursor document ID is invalid.");
                return false;
            }

            var cursorSource = sEl.GetString();
            var cursorDigest = qhEl.GetString();
            var expectedDigest = ComputeQueryScopeDigestHex(expectedSource, expectedTerms);

            if (!string.Equals(cursorSource, expectedSource.ToWire(), StringComparison.Ordinal) ||
                !string.Equals(cursorDigest, expectedDigest, StringComparison.Ordinal))
            {
                error = new ArchiveQueryValidationError(
                    "cursor_query_mismatch",
                    "Pagination cursor does not match the current query or source filter. Restart pagination from the first page.");
                return false;
            }

            position = new ArchiveCursorPosition(
                SubmittedAtUtc: FromUnixMicroseconds(micros),
                SubmittedAtUnixMicros: micros,
                DocumentId: docId);
            return true;
        }
        catch (JsonException)
        {
            error = new ArchiveQueryValidationError("invalid_archive_cursor", "Cursor payload is not valid JSON.");
            return false;
        }
    }

    private static bool IsCanonicalLowercaseNonZeroUuid(string value, out Guid parsed)
    {
        parsed = Guid.Empty;
        if (value.Length != 36)
        {
            return false;
        }

        for (var i = 0; i < value.Length; i++)
        {
            var c = value[i];
            if (i is 8 or 13 or 18 or 23)
            {
                if (c != '-')
                {
                    return false;
                }
            }
            else if (!(char.IsAsciiDigit(c) || c is >= 'a' and <= 'f'))
            {
                return false;
            }
        }

        return Guid.TryParseExact(value, "D", out parsed) && parsed != Guid.Empty;
    }
}
