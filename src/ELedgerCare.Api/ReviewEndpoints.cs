using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using ELedgerCare.Application.Intake;
using ELedgerCare.Application.Review;
using ELedgerCare.Domain.Review;
using Microsoft.AspNetCore.Http.HttpResults;
using Microsoft.Extensions.Primitives;
using Microsoft.Net.Http.Headers;

namespace ELedgerCare.Api;

internal static class ReviewEndpoints
{
    private static readonly UTF8Encoding StrictUtf8 = new(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true);

    private static readonly HashSet<string> ForbiddenClientProvenanceProperties = new(StringComparer.OrdinalIgnoreCase)
    {
        "inputSha256",
        "rawSha256",
        "rawOutputSha256",
        "requestSha256",
        "sourceQuote",
        "consultedQuote",
        "machineCandidate",
        "machineSnapshot",
        "revisionId",
        "revisionNumber",
        "savedAtUtc",
        "fieldSchemaVersion",
        "suggestionPolicyVersion",
    };

    public static void MapReviewEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapGet("/api/documents/{documentId}/preview", GetPreviewAsync);
        app.MapGet("/api/documents/{documentId}/review", GetReviewAsync);
        app.MapGet("/api/documents/{documentId}/review/revisions/{revisionNumber}", GetRevisionAsync);
        app.MapPost("/api/documents/{documentId}/review/revisions", SaveRevisionAsync);
    }

    private static async Task<IResult> GetPreviewAsync(
        string documentId,
        HttpContext http,
        IIntakeStore intakeStore,
        CancellationToken cancellationToken)
    {
        if (!DocumentEndpoints.TryParseCanonicalUuid(documentId, out var id))
        {
            return InvalidRouteId("documentId");
        }

        var bytes = await intakeStore.GetOriginalBytesAsync(id, cancellationToken);
        if (bytes is null)
        {
            return Problems.Create(StatusCodes.Status404NotFound, "document_not_found", "Document not found");
        }

        var shaHex = Convert.ToHexStringLower(SHA256.HashData(bytes));
        http.Response.Headers.ContentDisposition =
            string.Create(CultureInfo.InvariantCulture, $"inline; filename=\"document-{id:D}.pdf\"");
        http.Response.Headers.XFrameOptions = "SAMEORIGIN";
        http.Response.Headers.ContentSecurityPolicy = "frame-ancestors 'self'";
        http.Response.Headers.XContentTypeOptions = "nosniff";

        var etag = new EntityTagHeaderValue($"\"{shaHex}\"");
        return TypedResults.File(
            bytes,
            contentType: "application/pdf",
            fileDownloadName: null,
            lastModified: null,
            entityTag: etag,
            enableRangeProcessing: true);
    }

    private static async Task<IResult> GetReviewAsync(
        string documentId,
        HttpContext http,
        IWorkOrderReviewStore reviewStore,
        CancellationToken cancellationToken)
    {
        if (!DocumentEndpoints.TryParseCanonicalUuid(documentId, out var id))
        {
            return InvalidRouteId("documentId");
        }

        var profileQuery = http.Request.Query["profile"];
        if (profileQuery.Count > 1)
        {
            return Problems.Create(StatusCodes.Status400BadRequest, "invalid_review_request",
                "Invalid profile query", "Supply at most one profile query parameter.");
        }

        if (profileQuery.Count == 1 &&
            !string.Equals(profileQuery[0], WorkOrderReviewSchema.ProfileId, StringComparison.Ordinal))
        {
            return Problems.Create(StatusCodes.Status422UnprocessableEntity, "review_profile_unsupported",
                "Unsupported review profile",
                $"Only profile '{WorkOrderReviewSchema.ProfileId}' is supported in this release.");
        }

        var outcome = await reviewStore.GetDocumentReviewAsync(id, cancellationToken);
        return outcome switch
        {
            GetDocumentReviewOutcome.NotFound =>
                Problems.Create(StatusCodes.Status404NotFound, "document_not_found", "Document not found"),
            GetDocumentReviewOutcome.ProfileUnsupported unsupported =>
                Problems.Create(StatusCodes.Status422UnprocessableEntity, "review_profile_unsupported",
                    "Document outside review profile", unsupported.Detail),
            GetDocumentReviewOutcome.ExtractionNotCompleted notReady =>
                Problems.Create(StatusCodes.Status409Conflict, "extraction_not_completed",
                    "Completed extraction required",
                    $"Work-order review requires a completed local extraction result (current status: '{notReady.CurrentExtractionStatus}')."),
            GetDocumentReviewOutcome.Found found =>
                TypedResults.Ok(DocumentReviewResponse.From(found.Snapshot)),
            _ => throw new InvalidOperationException("Unhandled review read outcome."),
        };
    }

    private static async Task<IResult> GetRevisionAsync(
        string documentId,
        string revisionNumber,
        IWorkOrderReviewStore reviewStore,
        CancellationToken cancellationToken)
    {
        if (!DocumentEndpoints.TryParseCanonicalUuid(documentId, out var id))
        {
            return InvalidRouteId("documentId");
        }

        if (!TryParseCanonicalPositiveInt(revisionNumber, out var revNum))
        {
            return Problems.Create(StatusCodes.Status400BadRequest, "invalid_revision_number",
                "Invalid revision number",
                "revisionNumber must be a positive base-10 integer without leading zeros.");
        }

        var outcome = await reviewStore.GetRevisionAsync(id, revNum, cancellationToken);
        return outcome switch
        {
            GetReviewRevisionOutcome.DocumentNotFound =>
                Problems.Create(StatusCodes.Status404NotFound, "document_not_found", "Document not found"),
            GetReviewRevisionOutcome.RevisionNotFound =>
                Problems.Create(StatusCodes.Status404NotFound, "revision_not_found", "Review revision not found"),
            GetReviewRevisionOutcome.Found found =>
                TypedResults.Ok(SelectedReviewRevisionResponse.From(found.Snapshot)),
            _ => throw new InvalidOperationException("Unhandled review revision read outcome."),
        };
    }

    private static async Task<IResult> SaveRevisionAsync(
        string documentId,
        HttpContext http,
        SaveWorkOrderReviewRevision saveRevision)
    {
        if (!DocumentEndpoints.TryParseCanonicalUuid(documentId, out var id))
        {
            return InvalidRouteId("documentId");
        }

        if (!DocumentEndpoints.TryParseCanonicalUuid(http.Request.Headers[DocumentEndpoints.IdempotencyKeyHeader], out var idempotencyKey))
        {
            return Problems.Create(StatusCodes.Status400BadRequest, "invalid_idempotency_key",
                "Invalid Idempotency-Key",
                "Send exactly one Idempotency-Key header containing a non-empty UUID in 36-character D format.");
        }

        if (!IsIdentityEncoding(http.Request.Headers.ContentEncoding))
        {
            return Problems.Create(StatusCodes.Status415UnsupportedMediaType, "unsupported_content_encoding",
                "Unsupported content encoding", "Content-Encoding must be absent or identity.");
        }

        if (http.Request.ContentLength > WorkOrderReviewSchema.MaxRequestBodyBytes)
        {
            return PayloadTooLarge();
        }

        byte[] raw;
        try
        {
            raw = await BoundedBody.ReadAsync(http.Request.Body, WorkOrderReviewSchema.MaxRequestBodyBytes, http.RequestAborted);
        }
        catch (BoundedBody.LimitExceededException)
        {
            return PayloadTooLarge();
        }
        catch (BadHttpRequestException ex) when (ex.StatusCode == StatusCodes.Status413PayloadTooLarge)
        {
            return PayloadTooLarge();
        }

        if (raw.Length == 0)
        {
            return Problems.Create(StatusCodes.Status400BadRequest, "empty_body",
                "Empty review request", "The request body is empty.");
        }

        if (!IsJsonMediaType(http.Request.ContentType))
        {
            return Problems.Create(StatusCodes.Status415UnsupportedMediaType, "unsupported_media_type",
                "Unsupported media type", "Review revision requests must use Content-Type application/json.");
        }

        var (parsedCommand, parseError) = TryParseSaveCommand(id, idempotencyKey, raw);
        if (parseError is not null)
        {
            return parseError;
        }

        var outcome = await saveRevision.ExecuteAsync(parsedCommand!, http.RequestAborted);
        return outcome switch
        {
            SaveReviewRevisionOutcome.DocumentNotFound =>
                Problems.Create(StatusCodes.Status404NotFound, "document_not_found", "Document not found"),

            SaveReviewRevisionOutcome.ExtractionNotCompleted notReady =>
                Problems.Create(StatusCodes.Status409Conflict, "extraction_not_completed",
                    "Completed extraction required",
                    $"Work-order review requires a completed local extraction result (current status: '{notReady.CurrentExtractionStatus}')."),

            SaveReviewRevisionOutcome.ProfileUnsupported unsupported =>
                Problems.Create(StatusCodes.Status422UnprocessableEntity, "review_profile_unsupported",
                    "Unsupported review profile", unsupported.Detail),

            SaveReviewRevisionOutcome.ResultIdMismatch mismatch =>
                Problems.Create(
                    StatusCodes.Status409Conflict,
                    "result_id_mismatch",
                    "Extraction result mismatch",
                    $"resultId does not match this document's accepted extraction result ({mismatch.AcceptedResultId:D}).",
                    new Dictionary<string, object?> { ["acceptedResultId"] = mismatch.AcceptedResultId.ToString("D") }),

            SaveReviewRevisionOutcome.IdempotencyKeyConflict =>
                Problems.Create(StatusCodes.Status409Conflict, "idempotency_key_conflict",
                    "Idempotency key already used",
                    "This Idempotency-Key already identifies a committed review revision with different parameters or field values."),

            SaveReviewRevisionOutcome.StaleExpectedRevision stale =>
                Problems.Create(
                    StatusCodes.Status409Conflict,
                    "stale_expected_revision",
                    "Stale expected revision",
                    string.Create(CultureInfo.InvariantCulture,
                        $"expectedRevision ({stale.ExpectedRevision}) does not match the current revision ({stale.CurrentRevisionNumber}). Reload the current revision to reconcile your unsaved edits."),
                    new Dictionary<string, object?>
                    {
                        ["expectedRevision"] = stale.ExpectedRevision,
                        ["currentRevisionNumber"] = stale.CurrentRevisionNumber,
                        ["currentReviewState"] = stale.CurrentStatus?.ToWire() ?? "unreviewed",
                        ["currentRevisionUrl"] = stale.CurrentRevisionNumber >= 1
                            ? string.Create(CultureInfo.InvariantCulture, $"/api/documents/{id:D}/review/revisions/{stale.CurrentRevisionNumber}")
                            : string.Create(CultureInfo.InvariantCulture, $"/api/documents/{id:D}/review"),
                    }),

            SaveReviewRevisionOutcome.RevisionLimitReached cap =>
                Problems.Create(
                    StatusCodes.Status409Conflict,
                    "revision_limit_reached",
                    "Revision limit reached",
                    string.Create(CultureInfo.InvariantCulture,
                        $"This extraction result already has the maximum of {cap.MaxRevisions} saved review revisions; existing history is preserved."),
                    new Dictionary<string, object?>
                    {
                        ["currentRevisionNumber"] = cap.CurrentRevisionNumber,
                        ["maxRevisions"] = cap.MaxRevisions,
                    }),

            SaveReviewRevisionOutcome.ValidationRejected rejected =>
                Problems.Create(StatusCodes.Status422UnprocessableEntity, rejected.Code,
                    "Review validation failed", rejected.Detail),

            SaveReviewRevisionOutcome.Created created =>
                TypedResults.Created(
                    string.Create(CultureInfo.InvariantCulture,
                        $"/api/documents/{id:D}/review/revisions/{created.Result.Revision.RevisionNumber}"),
                    SaveReviewRevisionResponse.From(created.Result, replayed: false)),

            SaveReviewRevisionOutcome.Replayed replayed =>
                TypedResults.Ok(SaveReviewRevisionResponse.From(replayed.Result, replayed: true)),

            _ => throw new InvalidOperationException("Unhandled save review revision outcome."),
        };
    }

    private static (SaveReviewRevisionCommand? Command, ProblemHttpResult? Error) TryParseSaveCommand(
        Guid documentId,
        Guid idempotencyKey,
        byte[] raw)
    {
        try
        {
            _ = StrictUtf8.GetString(raw);
        }
        catch (DecoderFallbackException)
        {
            return (null, Problems.Create(StatusCodes.Status400BadRequest, "invalid_utf8",
                "Invalid UTF-8 body", "Request body is not valid UTF-8."));
        }

        try
        {
            using var doc = JsonDocument.Parse(raw);
            var root = doc.RootElement;
            if (root.ValueKind != JsonValueKind.Object)
            {
                return (null, InvalidJson("Request root must be a JSON object."));
            }

            string profileId = WorkOrderReviewSchema.ProfileId;
            Guid? resultId = null;
            int? expectedRevision = null;
            ReviewRevisionStatus? status = null;
            string? operatorDisplayLabel = null;
            JsonElement? fieldsElement = null;

            var rootKeys = new HashSet<string>(StringComparer.Ordinal);
            foreach (var prop in root.EnumerateObject())
            {
                if (!rootKeys.Add(prop.Name))
                {
                    return (null, InvalidJson($"Duplicate JSON property '{prop.Name}'."));
                }

                if (ForbiddenClientProvenanceProperties.Contains(prop.Name))
                {
                    return (null, Problems.Create(StatusCodes.Status400BadRequest, "client_provenance_forbidden",
                        "Server-owned provenance field forbidden",
                        $"Property '{prop.Name}' is server-owned and cannot be asserted by the client."));
                }

                switch (prop.Name)
                {
                    case "profileId":
                        if (prop.Value.ValueKind != JsonValueKind.String)
                        {
                            return (null, InvalidJson("profileId must be a string."));
                        }

                        profileId = ReadStrictJsonString(prop.Value);
                        break;

                    case "resultId":
                        if (prop.Value.ValueKind != JsonValueKind.String ||
                            ReadStrictJsonString(prop.Value) is not { Length: 36 } resText ||
                            !Guid.TryParseExact(resText, "D", out var parsedResultId) ||
                            parsedResultId == Guid.Empty)
                        {
                            return (null, Problems.Create(StatusCodes.Status400BadRequest, "invalid_identifier",
                                "Invalid resultId", "resultId must be a non-empty UUID in 36-character D format."));
                        }

                        resultId = parsedResultId;
                        break;

                    case "expectedRevision":
                        if (prop.Value.ValueKind != JsonValueKind.Number ||
                            !prop.Value.TryGetInt32(out var expRev) ||
                            expRev < 0)
                        {
                            return (null, Problems.Create(StatusCodes.Status400BadRequest, "invalid_expected_revision",
                                "Invalid expectedRevision", "expectedRevision must be an integer >= 0."));
                        }

                        expectedRevision = expRev;
                        break;

                    case "status":
                        if (prop.Value.ValueKind != JsonValueKind.String ||
                            !ReviewRevisionStatusNames.TryFromWire(ReadStrictJsonString(prop.Value), out var parsedStatus))
                        {
                            return (null, Problems.Create(StatusCodes.Status400BadRequest, "invalid_review_status",
                                "Invalid status", "status must be 'draft' or 'reviewed'."));
                        }

                        status = parsedStatus;
                        break;

                    case "operatorDisplayLabel":
                        if (prop.Value.ValueKind == JsonValueKind.Null)
                        {
                            operatorDisplayLabel = null;
                        }
                        else if (prop.Value.ValueKind == JsonValueKind.String)
                        {
                            operatorDisplayLabel = ReadStrictJsonString(prop.Value);
                        }
                        else
                        {
                            return (null, InvalidJson("operatorDisplayLabel must be a string or null."));
                        }

                        break;

                    case "fields":
                        if (prop.Value.ValueKind != JsonValueKind.Array)
                        {
                            return (null, InvalidJson("fields must be a JSON array of the five work-order fields."));
                        }

                        fieldsElement = prop.Value;
                        break;

                    default:
                        return (null, InvalidJson($"Unknown property '{prop.Name}'."));
                }
            }

            if (resultId is null || expectedRevision is null || status is null || fieldsElement is null)
            {
                return (null, InvalidJson("resultId, expectedRevision, status, and fields are required."));
            }

            var orderedInputs = new CanonicalReviewFieldInput?[WorkOrderReviewSchema.FieldCount];
            var seenFieldKeys = new HashSet<string>(StringComparer.Ordinal);
            var itemCount = 0;

            foreach (var item in fieldsElement.Value.EnumerateArray())
            {
                itemCount++;
                if (item.ValueKind != JsonValueKind.Object)
                {
                    return (null, InvalidJson("Each element of fields must be a JSON object."));
                }

                string? fieldKey = null;
                ReviewFieldDecision? decision = null;
                string? value = null;
                string? unknownReason = null;
                ReviewSourceCoordinate? consultedSource = null;

                var fieldPropNames = new HashSet<string>(StringComparer.Ordinal);
                foreach (var fp in item.EnumerateObject())
                {
                    if (!fieldPropNames.Add(fp.Name))
                    {
                        return (null, InvalidJson($"Duplicate field property '{fp.Name}'."));
                    }

                    if (ForbiddenClientProvenanceProperties.Contains(fp.Name))
                    {
                        return (null, Problems.Create(StatusCodes.Status400BadRequest, "client_provenance_forbidden",
                            "Server-owned provenance field forbidden",
                            $"Property '{fp.Name}' is server-owned and cannot be asserted by the client."));
                    }

                    switch (fp.Name)
                    {
                        case "fieldKey":
                            if (fp.Value.ValueKind != JsonValueKind.String)
                            {
                                return (null, InvalidJson("fieldKey must be a string."));
                            }

                            fieldKey = ReadStrictJsonString(fp.Value);
                            break;

                        case "decision":
                            if (fp.Value.ValueKind != JsonValueKind.String ||
                                !ReviewFieldDecisionNames.TryFromWire(ReadStrictJsonString(fp.Value), out var parsedDecision))
                            {
                                return (null, Problems.Create(StatusCodes.Status400BadRequest, "invalid_field_decision",
                                    "Invalid field decision",
                                    "decision must be 'unreviewed', 'accepted', 'edited', or 'unknown'."));
                            }

                            decision = parsedDecision;
                            break;

                        case "value":
                            if (fp.Value.ValueKind == JsonValueKind.Null)
                            {
                                value = null;
                            }
                            else if (fp.Value.ValueKind == JsonValueKind.String)
                            {
                                value = ReadStrictJsonString(fp.Value);
                            }
                            else
                            {
                                return (null, InvalidJson("field value must be a string or null."));
                            }

                            break;

                        case "unknownReason":
                            if (fp.Value.ValueKind == JsonValueKind.Null)
                            {
                                unknownReason = null;
                            }
                            else if (fp.Value.ValueKind == JsonValueKind.String)
                            {
                                unknownReason = ReadStrictJsonString(fp.Value);
                            }
                            else
                            {
                                return (null, InvalidJson("unknownReason must be a string or null."));
                            }

                            break;

                        case "consultedSource":
                            if (fp.Value.ValueKind == JsonValueKind.Null)
                            {
                                consultedSource = null;
                            }
                            else if (fp.Value.ValueKind == JsonValueKind.Object)
                            {
                                var (parsedCoord, coordErr) = TryParseSourceCoordinate(fp.Value);
                                if (coordErr is not null)
                                {
                                    return (null, coordErr);
                                }

                                consultedSource = parsedCoord;
                            }
                            else
                            {
                                return (null, InvalidJson("consultedSource must be an object or null."));
                            }

                            break;

                        default:
                            return (null, InvalidJson($"Unknown field property '{fp.Name}'."));
                    }
                }

                if (fieldKey is null || decision is null)
                {
                    return (null, InvalidJson("Each field entry requires fieldKey and decision."));
                }

                if (!WorkOrderReviewSchema.TryGetField(fieldKey, out var spec))
                {
                    return (null, Problems.Create(StatusCodes.Status400BadRequest, "unknown_field_key",
                        "Unknown fieldKey", $"'{fieldKey}' is not part of profile '{WorkOrderReviewSchema.ProfileId}'."));
                }

                if (!seenFieldKeys.Add(fieldKey))
                {
                    return (null, InvalidJson($"Duplicate fieldKey '{fieldKey}' in fields array."));
                }

                orderedInputs[spec.Ordinal] = new CanonicalReviewFieldInput(
                    spec.FieldKey,
                    decision.Value,
                    value,
                    unknownReason,
                    consultedSource);
            }

            if (itemCount != WorkOrderReviewSchema.FieldCount || seenFieldKeys.Count != WorkOrderReviewSchema.FieldCount)
            {
                return (null, InvalidJson($"fields must contain all {WorkOrderReviewSchema.FieldCount} work-order fields exactly once."));
            }

            var finalizedFields = orderedInputs.Select(f => f!).ToArray();
            var requestSha256 = ReviewRequestDigest.ComputeSha256(
                documentId,
                profileId,
                resultId.Value,
                expectedRevision.Value,
                status.Value,
                operatorDisplayLabel,
                finalizedFields);

            return (new SaveReviewRevisionCommand(
                documentId,
                idempotencyKey,
                profileId,
                resultId.Value,
                expectedRevision.Value,
                status.Value,
                operatorDisplayLabel,
                finalizedFields,
                requestSha256), null);
        }
        catch (UnpairedSurrogateJsonException ex)
        {
            return (null, Problems.Create(StatusCodes.Status422UnprocessableEntity, "invalid_field_value",
                "Invalid Unicode text", ex.Message));
        }
        catch (JsonException)
        {
            return (null, InvalidJson("Malformed JSON payload."));
        }
    }

    private static (ReviewSourceCoordinate? Coordinate, ProblemHttpResult? Error) TryParseSourceCoordinate(JsonElement element)
    {
        int? pageNumber = null;
        int? blockOrdinal = null;
        int? tableRow = null;
        int? tableColumn = null;

        var keys = new HashSet<string>(StringComparer.Ordinal);
        foreach (var prop in element.EnumerateObject())
        {
            if (!keys.Add(prop.Name))
            {
                return (null, InvalidJson($"Duplicate consultedSource property '{prop.Name}'."));
            }

            if (ForbiddenClientProvenanceProperties.Contains(prop.Name))
            {
                return (null, Problems.Create(StatusCodes.Status400BadRequest, "client_provenance_forbidden",
                    "Server-owned provenance field forbidden",
                    $"Property '{prop.Name}' is server-owned and cannot be asserted by the client."));
            }

            switch (prop.Name)
            {
                case "pageNumber":
                    if (prop.Value.ValueKind != JsonValueKind.Number || !prop.Value.TryGetInt32(out var p))
                    {
                        return (null, InvalidJson("consultedSource.pageNumber must be an integer."));
                    }

                    pageNumber = p;
                    break;

                case "blockOrdinal":
                    if (prop.Value.ValueKind != JsonValueKind.Number || !prop.Value.TryGetInt32(out var b))
                    {
                        return (null, InvalidJson("consultedSource.blockOrdinal must be an integer."));
                    }

                    blockOrdinal = b;
                    break;

                case "tableRow":
                    if (prop.Value.ValueKind == JsonValueKind.Null)
                    {
                        tableRow = null;
                    }
                    else if (prop.Value.ValueKind == JsonValueKind.Number && prop.Value.TryGetInt32(out var tr))
                    {
                        tableRow = tr;
                    }
                    else
                    {
                        return (null, InvalidJson("consultedSource.tableRow must be an integer or null."));
                    }

                    break;

                case "tableColumn":
                    if (prop.Value.ValueKind == JsonValueKind.Null)
                    {
                        tableColumn = null;
                    }
                    else if (prop.Value.ValueKind == JsonValueKind.Number && prop.Value.TryGetInt32(out var tc))
                    {
                        tableColumn = tc;
                    }
                    else
                    {
                        return (null, InvalidJson("consultedSource.tableColumn must be an integer or null."));
                    }

                    break;

                default:
                    return (null, InvalidJson($"Unknown consultedSource property '{prop.Name}'."));
            }
        }

        if (pageNumber is null || blockOrdinal is null)
        {
            return (null, InvalidJson("consultedSource requires pageNumber and blockOrdinal."));
        }

        return (new ReviewSourceCoordinate(pageNumber.Value, blockOrdinal.Value, tableRow, tableColumn), null);
    }

    private static string ReadStrictJsonString(JsonElement element)
    {
        try
        {
            return element.GetString()!;
        }
        catch (InvalidOperationException ex)
        {
            // JsonElement.GetString() throws InvalidOperationException on unpaired UTF-16 surrogate escapes (\uD800..\uDFFF).
            throw new UnpairedSurrogateJsonException("JSON string contains an invalid unpaired UTF-16 surrogate.", ex);
        }
    }

    private static bool TryParseCanonicalPositiveInt(string? raw, out int value)
    {
        value = 0;
        if (string.IsNullOrEmpty(raw) || raw[0] == '0')
        {
            return false;
        }

        foreach (var ch in raw)
        {
            if (ch is < '0' or > '9')
            {
                return false;
            }
        }

        return int.TryParse(raw, NumberStyles.None, CultureInfo.InvariantCulture, out value) && value >= 1;
    }

    private static bool IsJsonMediaType(string? contentType) =>
        MediaTypeHeaderValue.TryParse(contentType, out var parsed)
        && parsed.MediaType.Equals("application/json", StringComparison.OrdinalIgnoreCase);

    private static bool IsIdentityEncoding(StringValues encodings) =>
        encodings.Count == 0
        || (encodings.Count == 1 && string.Equals(encodings[0]?.Trim(), "identity", StringComparison.OrdinalIgnoreCase));

    private static ProblemHttpResult PayloadTooLarge() =>
        Problems.Create(StatusCodes.Status413PayloadTooLarge, "review_request_too_large",
            "Review request too large",
            $"Review revision payloads cannot exceed {WorkOrderReviewSchema.MaxRequestBodyBytes} bytes.");

    private static ProblemHttpResult InvalidJson(string detail) =>
        Problems.Create(StatusCodes.Status400BadRequest, "invalid_review_request",
            "Invalid review request", detail);

    private static ProblemHttpResult InvalidRouteId(string name) =>
        Problems.Create(StatusCodes.Status400BadRequest, "invalid_identifier", "Invalid identifier",
            $"{name} must be a non-empty UUID in 36-character D format.");

    private sealed class UnpairedSurrogateJsonException(string message, Exception innerException)
        : Exception(message, innerException);
}
