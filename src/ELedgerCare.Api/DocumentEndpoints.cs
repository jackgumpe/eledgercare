using System.Globalization;
using System.Text.Json;
using ELedgerCare.Application.Extraction;
using ELedgerCare.Application.Intake;
using Microsoft.AspNetCore.Http.HttpResults;
using Microsoft.Extensions.Primitives;
using Microsoft.Net.Http.Headers;

namespace ELedgerCare.Api;

internal static class DocumentEndpoints
{
    public const string IdempotencyKeyHeader = "Idempotency-Key";
    public const string IntakeRateLimitPolicy = "intake-admission";
    private const int MaxExtractionRequestBodyBytes = 512;

    public static void MapDocumentEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapPost("/api/documents", SubmitAsync).RequireRateLimiting(IntakeRateLimitPolicy);
        app.MapGet("/api/documents/{documentId}", GetDocumentAsync);
        app.MapGet("/api/documents/{documentId}/original", GetOriginalAsync);
        app.MapPost("/api/documents/{documentId}/extraction", RequestExtractionAsync);
        app.MapGet("/api/documents/{documentId}/extraction", GetExtractionAsync);
        app.MapGet("/api/submissions/{idempotencyKey}", GetSubmissionAsync);
    }

    private static async Task<IResult> SubmitAsync(HttpContext http, SubmitDocument submitDocument, IntakeLimits limits)
    {
        var request = http.Request;

        // Step 1: header validation before reading the body.
        if (!TryParseCanonicalUuid(request.Headers[IdempotencyKeyHeader], out var idempotencyKey))
        {
            return Problems.Create(StatusCodes.Status400BadRequest, "invalid_idempotency_key",
                "Invalid Idempotency-Key",
                "Send exactly one Idempotency-Key header containing a non-empty UUID in 36-character D format.");
        }

        if (!IsPdfMediaType(request.ContentType))
        {
            return Problems.Create(StatusCodes.Status415UnsupportedMediaType, "unsupported_media_type",
                "Unsupported media type", "The request body must be sent as Content-Type application/pdf.");
        }

        if (!IsIdentityEncoding(request.Headers.ContentEncoding))
        {
            return Problems.Create(StatusCodes.Status415UnsupportedMediaType, "unsupported_content_encoding",
                "Unsupported content encoding", "Content-Encoding must be absent or identity.");
        }

        if (request.ContentLength > limits.MaxDocumentBytes)
        {
            return TooLarge(limits);
        }

        // Step 2: read the complete body into a bounded buffer.
        byte[] body;
        try
        {
            body = await BoundedBody.ReadAsync(request.Body, limits.MaxDocumentBytes, http.RequestAborted);
        }
        catch (BoundedBody.LimitExceededException)
        {
            return TooLarge(limits);
        }
        catch (BadHttpRequestException ex) when (ex.StatusCode == StatusCodes.Status413PayloadTooLarge)
        {
            return TooLarge(limits);
        }

        if (body.Length == 0)
        {
            return Problems.Create(StatusCodes.Status400BadRequest, "empty_body", "Empty document",
                "The request body is empty.");
        }

        // Steps 3-5.
        var outcome = await submitDocument.ExecuteAsync(idempotencyKey, body, http.RequestAborted);
        return outcome switch
        {
            SubmissionOutcome.Created created => TypedResults.Created(
                $"/api/documents/{created.Submission.DocumentId:D}",
                SubmissionReceiptResponse.From(created.Submission)),
            SubmissionOutcome.Replayed replayed => TypedResults.Ok(SubmissionReceiptResponse.From(replayed.Submission)),
            SubmissionOutcome.Conflict => Problems.Create(StatusCodes.Status409Conflict, "idempotency_key_conflict",
                "Idempotency key already used",
                "This Idempotency-Key already identifies a committed document with different bytes."),
            SubmissionOutcome.Rejected rejected => Rejected(rejected.Reason, limits),
            _ => throw new InvalidOperationException("Unhandled submission outcome."),
        };
    }

    private static async Task<IResult> GetDocumentAsync(
        string documentId,
        IExtractionStore extractionStore,
        CancellationToken cancellationToken)
    {
        if (!TryParseCanonicalUuid(documentId, out var id))
        {
            return InvalidRouteId("documentId");
        }

        var summary = await extractionStore.GetDocumentSummaryAsync(id, cancellationToken);
        return summary is null
            ? Problems.Create(StatusCodes.Status404NotFound, "document_not_found", "Document not found")
            : TypedResults.Ok(DocumentDetailResponse.From(summary));
    }

    private static async Task<IResult> GetOriginalAsync(string documentId, IIntakeStore store, CancellationToken cancellationToken)
    {
        if (!TryParseCanonicalUuid(documentId, out var id))
        {
            return InvalidRouteId("documentId");
        }

        var bytes = await store.GetOriginalBytesAsync(id, cancellationToken);
        return bytes is null
            ? Problems.Create(StatusCodes.Status404NotFound, "document_not_found", "Document not found")
            : TypedResults.File(bytes, "application/pdf", $"document-{id:D}.pdf");
    }

    private static async Task<IResult> RequestExtractionAsync(
        string documentId,
        HttpContext http,
        RequestExtraction requestExtraction,
        ExtractionSettings settings,
        IExtractionWakeSignal wakeSignal)
    {
        if (!TryParseCanonicalUuid(documentId, out var id))
        {
            return InvalidRouteId("documentId");
        }

        var (parseOk, retryAttemptId, parseError) = await TryReadOptionalRetryTargetAsync(http.Request, http.RequestAborted);
        if (!parseOk)
        {
            return parseError!;
        }

        var outcome = await requestExtraction.ExecuteAsync(id, retryAttemptId, http.RequestAborted);
        switch (outcome)
        {
            case QueueExtractionOutcome.NotFound:
                return Problems.Create(StatusCodes.Status404NotFound, "document_not_found", "Document not found");

            case QueueExtractionOutcome.ProfileUnsupported unsupported:
                return Problems.Create(
                    StatusCodes.Status422UnprocessableEntity,
                    "extraction_profile_unsupported",
                    "Document outside extraction profile",
                    string.Create(CultureInfo.InvariantCulture,
                        $"Local extraction supports 1 to {unsupported.MaxSupportedPages} pages in this profile; this document has {unsupported.AdmittedPageCount} pages."));

            case QueueExtractionOutcome.WorkerDisabled:
                return Problems.Create(
                    StatusCodes.Status503ServiceUnavailable,
                    "extraction_disabled",
                    "Local extraction unavailable",
                    "Local OCR execution is disabled until a coordinator runtime release is configured.");

            case QueueExtractionOutcome.RetryExplicitRequired reqRetry:
                return Problems.Create(
                    StatusCodes.Status409Conflict,
                    "retry_explicit_required",
                    "Explicit retry required",
                    string.Create(CultureInfo.InvariantCulture,
                        $"The previous attempt ({reqRetry.LatestAttemptId:D}) did not complete. Supply retryAttemptId to start a new attempt."));

            case QueueExtractionOutcome.RetryConflict conflict:
                return Problems.Create(StatusCodes.Status409Conflict, conflict.Code, "Extraction retry conflict", conflict.Detail);

            case QueueExtractionOutcome.AlreadyCompleted completed:
                return TypedResults.Ok(DocumentExtractionResponse.From(completed.Snapshot, settings));

            case QueueExtractionOutcome.QueuedOrActive active:
                wakeSignal.NotifyWorkQueued();
                return TypedResults.Accepted(
                    $"/api/documents/{id:D}/extraction",
                    DocumentExtractionResponse.From(active.Snapshot, settings));

            default:
                throw new InvalidOperationException("Unhandled extraction request outcome.");
        }
    }

    private static async Task<IResult> GetExtractionAsync(
        string documentId,
        IExtractionStore extractionStore,
        ExtractionSettings settings,
        CancellationToken cancellationToken)
    {
        if (!TryParseCanonicalUuid(documentId, out var id))
        {
            return InvalidRouteId("documentId");
        }

        var snapshot = await extractionStore.GetDocumentExtractionAsync(id, cancellationToken);
        return snapshot is null
            ? Problems.Create(StatusCodes.Status404NotFound, "document_not_found", "Document not found")
            : TypedResults.Ok(DocumentExtractionResponse.From(snapshot, settings));
    }

    private static async Task<IResult> GetSubmissionAsync(string idempotencyKey, IIntakeStore store, CancellationToken cancellationToken)
    {
        if (!TryParseCanonicalUuid(idempotencyKey, out var key))
        {
            return InvalidRouteId("idempotencyKey");
        }

        var submission = await store.FindByIdempotencyKeyAsync(key, cancellationToken);
        return submission is null
            ? Problems.Create(StatusCodes.Status404NotFound, "submission_not_found", "No committed submission",
                "No committed submission uses this key at this instant; an in-flight request may still commit.")
            : TypedResults.Ok(SubmissionReceiptResponse.From(submission));
    }

    private static async Task<(bool Ok, Guid? RetryAttemptId, ProblemHttpResult? Error)> TryReadOptionalRetryTargetAsync(
        HttpRequest request,
        CancellationToken cancellationToken)
    {
        if (request.ContentLength == 0)
        {
            return (true, null, null);
        }

        if (request.ContentLength > MaxExtractionRequestBodyBytes)
        {
            return (false, null, Problems.Create(StatusCodes.Status400BadRequest, "invalid_extraction_request",
                "Request body too large", "Extraction request payload exceeds 512 bytes."));
        }

        byte[] raw;
        try
        {
            raw = await BoundedBody.ReadAsync(request.Body, MaxExtractionRequestBodyBytes, cancellationToken);
        }
        catch (BoundedBody.LimitExceededException)
        {
            return (false, null, Problems.Create(StatusCodes.Status400BadRequest, "invalid_extraction_request",
                "Request body too large", "Extraction request payload exceeds 512 bytes."));
        }

        if (raw.Length == 0 || raw.All(b => b is (byte)' ' or (byte)'\t' or (byte)'\r' or (byte)'\n'))
        {
            return (true, null, null);
        }

        if (!IsJsonMediaType(request.ContentType))
        {
            return (false, null, Problems.Create(StatusCodes.Status415UnsupportedMediaType, "unsupported_media_type",
                "Unsupported media type", "Non-empty extraction request bodies must use Content-Type application/json."));
        }

        try
        {
            using var doc = JsonDocument.Parse(raw);
            var root = doc.RootElement;
            if (root.ValueKind != JsonValueKind.Object)
            {
                return (false, null, InvalidExtractionPayload());
            }

            Guid? retryId = null;
            foreach (var prop in root.EnumerateObject())
            {
                if (prop.Name != "retryAttemptId")
                {
                    return (false, null, InvalidExtractionPayload());
                }

                if (prop.Value.ValueKind == JsonValueKind.Null)
                {
                    continue;
                }

                if (prop.Value.ValueKind != JsonValueKind.String ||
                    prop.Value.GetString() is not { Length: 36 } text ||
                    !Guid.TryParseExact(text, "D", out var parsed) ||
                    parsed == Guid.Empty)
                {
                    return (false, null, Problems.Create(StatusCodes.Status400BadRequest, "invalid_identifier",
                        "Invalid retryAttemptId", "retryAttemptId must be a non-empty UUID in 36-character D format."));
                }

                retryId = parsed;
            }

            return (true, retryId, null);
        }
        catch (JsonException)
        {
            return (false, null, InvalidExtractionPayload());
        }
    }

    private static ProblemHttpResult InvalidExtractionPayload() =>
        Problems.Create(StatusCodes.Status400BadRequest, "invalid_extraction_request",
            "Invalid extraction request", "Send an empty body or a JSON object with optional retryAttemptId.");

    internal static bool TryParseCanonicalUuid(StringValues values, out Guid value)
    {
        value = Guid.Empty;
        if (values.Count != 1 || values[0] is not { Length: 36 } text)
        {
            return false;
        }

        return Guid.TryParseExact(text, "D", out value) && value != Guid.Empty;
    }

    private static bool IsPdfMediaType(string? contentType) =>
        MediaTypeHeaderValue.TryParse(contentType, out var parsed)
        && parsed.MediaType.Equals("application/pdf", StringComparison.OrdinalIgnoreCase)
        && parsed.Parameters.Count == 0;

    private static bool IsJsonMediaType(string? contentType) =>
        MediaTypeHeaderValue.TryParse(contentType, out var parsed)
        && parsed.MediaType.Equals("application/json", StringComparison.OrdinalIgnoreCase);

    private static bool IsIdentityEncoding(StringValues encodings) =>
        encodings.Count == 0
        || (encodings.Count == 1 && string.Equals(encodings[0]?.Trim(), "identity", StringComparison.OrdinalIgnoreCase));

    private static ProblemHttpResult TooLarge(IntakeLimits limits) =>
        Problems.Create(StatusCodes.Status413PayloadTooLarge, "document_too_large", "Document too large",
            $"The document exceeds the {limits.MaxDocumentBytes}-byte limit.");

    private static ProblemHttpResult InvalidRouteId(string name) =>
        Problems.Create(StatusCodes.Status400BadRequest, "invalid_identifier", "Invalid identifier",
            $"{name} must be a non-empty UUID in 36-character D format.");

    private static ProblemHttpResult Rejected(PdfRejectionReason reason, IntakeLimits limits)
    {
        var (code, detail) = reason switch
        {
            PdfRejectionReason.UnsupportedHeader => ("pdf_unsupported_header",
                "Only files beginning exactly with a %PDF-1.0 to %PDF-1.7 header are admitted."),
            PdfRejectionReason.MissingEofMarker => ("pdf_missing_eof", "The file does not end with a PDF %%EOF marker."),
            PdfRejectionReason.InvalidCrossReference => ("pdf_invalid_cross_reference",
                "The final startxref does not address a cross-reference section."),
            PdfRejectionReason.Encrypted => ("pdf_encrypted", "Encrypted PDFs are not admitted."),
            PdfRejectionReason.PageCountOutOfRange => ("pdf_page_count_out_of_range",
                $"The PDF must have between 1 and {limits.MaxPages} pages."),
            PdfRejectionReason.Unreadable => ("pdf_unreadable", "The PDF structure could not be read in strict mode."),
            _ => throw new ArgumentOutOfRangeException(nameof(reason), reason, null),
        };
        return Problems.Create(StatusCodes.Status422UnprocessableEntity, code, "PDF not admitted", detail);
    }
}
