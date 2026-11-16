using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using ELedgerCare.Domain.Processing;

namespace ELedgerCare.Application.Extraction;

/// <summary>
/// Independently validates the versioned worker envelope (eledgercare.local-extraction/1),
/// raw UTF-8 output bytes, SHA-256 digests, page markers, and pinned provenance before publication.
/// </summary>
public static class WorkerEnvelopeValidator
{
    private static readonly UTF8Encoding StrictUtf8 = new(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true);

    public static EnvelopeValidationOutcome Validate(
        ClaimedAttemptWork work,
        ExtractionSettings settings,
        WorkerRunOutcome outcome,
        DateTimeOffset nowUtc)
    {
        ArgumentNullException.ThrowIfNull(work);
        ArgumentNullException.ThrowIfNull(settings);
        ArgumentNullException.ThrowIfNull(outcome);

        if (!string.IsNullOrWhiteSpace(outcome.SupervisorFailureCode))
        {
            return new EnvelopeValidationOutcome.Rejected(
                outcome.SupervisorFailureCode,
                outcome.SupervisorFailureDetail ?? "The local OCR worker attempt did not complete within configured guards.",
                TryExtractPreview(outcome.RawOutputBytes),
                null);
        }

        if (outcome.EnvelopeJsonBytes is null || outcome.EnvelopeJsonBytes.Length == 0)
        {
            return new EnvelopeValidationOutcome.Rejected(
                "worker_missing_envelope",
                $"The local OCR worker exited (code {outcome.ExitCode?.ToString(CultureInfo.InvariantCulture) ?? "unknown"}) without writing a result envelope.",
                null,
                null);
        }

        JsonDocument doc;
        try
        {
            doc = JsonDocument.Parse(outcome.EnvelopeJsonBytes);
        }
        catch (JsonException)
        {
            return new EnvelopeValidationOutcome.Rejected(
                "worker_malformed_envelope",
                "The local OCR worker returned malformed JSON in its result envelope.",
                null,
                null);
        }

        using (doc)
        {
            var root = doc.RootElement;
            if (root.ValueKind != JsonValueKind.Object)
            {
                return new EnvelopeValidationOutcome.Rejected(
                    "worker_malformed_envelope",
                    "The worker envelope root must be a JSON object.",
                    null,
                    null);
            }

            if (GetString(root, "schema") != ExtractionCeilings.EnvelopeSchema)
            {
                return new EnvelopeValidationOutcome.Rejected(
                    "worker_schema_mismatch",
                    "The worker envelope schema version was not recognized.",
                    null,
                    null);
            }

            var status = GetString(root, "status");
            var diagnosticsJson = root.TryGetProperty("diagnostics", out var diagEl) && diagEl.ValueKind == JsonValueKind.Object
                ? diagEl.GetRawText()
                : "{}";

            if (status == "failed")
            {
                var failureEl = root.TryGetProperty("failure", out var fEl) && fEl.ValueKind == JsonValueKind.Object
                    ? fEl
                    : default;
                var code = failureEl.ValueKind == JsonValueKind.Object
                    ? (GetString(failureEl, "code") ?? "worker_failed")
                    : "worker_failed";
                var safeMsg = failureEl.ValueKind == JsonValueKind.Object
                    ? (GetString(failureEl, "message") ?? GetString(failureEl, "detail") ?? "Local OCR execution failed.")
                    : "Local OCR execution failed.";
                var diagRaw = failureEl.ValueKind == JsonValueKind.Object
                    ? GetString(failureEl, "diagnostic_raw_output_utf8")
                    : null;
                return new EnvelopeValidationOutcome.Rejected(code, safeMsg, diagRaw, diagnosticsJson);
            }

            if (status != "completed")
            {
                return new EnvelopeValidationOutcome.Rejected(
                    "worker_invalid_status",
                    "The worker envelope status was neither 'completed' nor 'failed'.",
                    null,
                    diagnosticsJson);
            }

            if (outcome.ExitCode != 0)
            {
                return new EnvelopeValidationOutcome.Rejected(
                    "worker_nonzero_exit",
                    "The worker exited with a non-zero status despite reporting completion.",
                    null,
                    diagnosticsJson);
            }

            if (!MatchesGuid(root, "document_id", work.DocumentId) ||
                !MatchesGuid(root, "job_id", work.JobId) ||
                !MatchesGuid(root, "attempt_id", work.AttemptId) ||
                !TryGetInt64(root, "fencing_token", out var envToken) ||
                envToken != work.FencingToken)
            {
                return new EnvelopeValidationOutcome.Rejected(
                    "worker_identity_mismatch",
                    "The worker envelope identity or fencing token did not match the claimed attempt.",
                    null,
                    diagnosticsJson);
            }

            if (!root.TryGetProperty("input", out var inputEl) || inputEl.ValueKind != JsonValueKind.Object ||
                !TryParseSha256Hex(GetString(inputEl, "sha256"), out var envInputSha) ||
                !CryptographicOperations.FixedTimeEquals(envInputSha, work.InputSha256) ||
                !TryGetInt32(inputEl, "byte_length", out var envInputLen) || envInputLen != work.InputByteLength ||
                !TryGetInt32(inputEl, "page_count", out var envInputPages) || envInputPages != work.PageCount)
            {
                return new EnvelopeValidationOutcome.Rejected(
                    "worker_input_provenance_mismatch",
                    "The worker envelope input digest, length, or page count disagreed with the original PDF.",
                    null,
                    diagnosticsJson);
            }

            if (!root.TryGetProperty("provenance", out var provEl) || provEl.ValueKind != JsonValueKind.Object)
            {
                return new EnvelopeValidationOutcome.Rejected(
                    "worker_missing_provenance",
                    "The worker envelope omitted required model/runtime provenance.",
                    null,
                    diagnosticsJson);
            }

            var expectedConfigSha = ExtractionSettings.ComputeWorkerConfigSha256(work.PageCount);
            if (GetString(provEl, "model_repo_id") != ExtractionCeilings.ModelRepoId ||
                GetString(provEl, "model_revision") != ExtractionCeilings.ModelRevision ||
                !TryParseSha256Hex(GetString(provEl, "model_manifest_sha256"), out var envManifestSha) ||
                !CryptographicOperations.FixedTimeEquals(envManifestSha, settings.ModelManifestSha256) ||
                !TryParseSha256Hex(GetString(provEl, "dependency_lock_sha256"), out var envLockSha) ||
                !CryptographicOperations.FixedTimeEquals(envLockSha, settings.DependencyLockSha256) ||
                !TryParseSha256Hex(GetString(provEl, "worker_source_sha256"), out var envWorkerSha) ||
                !CryptographicOperations.FixedTimeEquals(envWorkerSha, settings.WorkerSourceSha256) ||
                !TryParseSha256Hex(GetString(provEl, "worker_config_sha256"), out var envConfigSha) ||
                !CryptographicOperations.FixedTimeEquals(envConfigSha, expectedConfigSha))
            {
                return new EnvelopeValidationOutcome.Rejected(
                    "worker_provenance_mismatch",
                    "The worker envelope model, manifest, dependency-lock, or source digest failed verification.",
                    null,
                    diagnosticsJson);
            }

            var rendererIdentity = GetString(provEl, "renderer_identity");
            if (string.IsNullOrWhiteSpace(rendererIdentity) ||
                !rendererIdentity.Contains("pypdfium2==5.15.2", StringComparison.Ordinal) ||
                !rendererIdentity.Contains("159.0.8149.0", StringComparison.Ordinal))
            {
                return new EnvelopeValidationOutcome.Rejected(
                    "worker_renderer_mismatch",
                    "The worker renderer identity did not match pinned pypdfium2 5.15.2 / PDFium 159.0.8149.0.",
                    null,
                    diagnosticsJson);
            }

            if (!provEl.TryGetProperty("provenance_exceptions", out var excArr) ||
                excArr.ValueKind != JsonValueKind.Array ||
                !excArr.EnumerateArray().Any(e => e.ValueKind == JsonValueKind.String &&
                    e.GetString() == ExtractionCeilings.RequiredProvenanceException))
            {
                return new EnvelopeValidationOutcome.Rejected(
                    "worker_provenance_mismatch",
                    "The worker envelope omitted the required torchvision TOFU provenance disclosure.",
                    null,
                    diagnosticsJson);
            }

            var genSettingsJson = provEl.TryGetProperty("generation_settings", out var genEl) && genEl.ValueKind == JsonValueKind.Object
                ? genEl.GetRawText()
                : null;
            if (string.IsNullOrWhiteSpace(genSettingsJson))
            {
                return new EnvelopeValidationOutcome.Rejected(
                    "worker_provenance_mismatch",
                    "The worker envelope omitted generation_settings.",
                    null,
                    diagnosticsJson);
            }

            if (!root.TryGetProperty("output", out var outEl) || outEl.ValueKind != JsonValueKind.Object)
            {
                return new EnvelopeValidationOutcome.Rejected(
                    "worker_missing_output",
                    "The worker envelope omitted output metadata.",
                    null,
                    diagnosticsJson);
            }

            var finishReason = GetString(outEl, "finish_reason");
            if (finishReason != ExtractionCeilings.StopFinishReason)
            {
                return new EnvelopeValidationOutcome.Rejected(
                    "model_output_truncated",
                    "Model generation did not finish with 'stop' and was not accepted as a complete extraction.",
                    TryExtractPreview(outcome.RawOutputBytes),
                    diagnosticsJson);
            }

            if (!TryGetInt32(outEl, "output_page_count", out var outPages) || outPages != work.PageCount)
            {
                return new EnvelopeValidationOutcome.Rejected(
                    "page_count_mismatch",
                    "Model output page count disagreed with the admitted document page count.",
                    TryExtractPreview(outcome.RawOutputBytes),
                    diagnosticsJson);
            }

            if (outcome.RawOutputBytes is null || outcome.RawOutputBytes.Length == 0)
            {
                return new EnvelopeValidationOutcome.Rejected(
                    "worker_missing_output",
                    "The worker reported completion without a non-empty raw UTF-8 output file.",
                    null,
                    diagnosticsJson);
            }

            if (outcome.RawOutputBytes.Length > ExtractionCeilings.MaxRawOutputBytes)
            {
                return new EnvelopeValidationOutcome.Rejected(
                    "output_cap_exceeded",
                    "The raw UTF-8 output exceeded the 16 MiB maximum.",
                    TryExtractPreview(outcome.RawOutputBytes),
                    diagnosticsJson);
            }

            if (!TryGetInt32(outEl, "byte_length", out var declaredLen) || declaredLen != outcome.RawOutputBytes.Length ||
                !TryParseSha256Hex(GetString(outEl, "sha256"), out var declaredSha))
            {
                return new EnvelopeValidationOutcome.Rejected(
                    "worker_output_digest_mismatch",
                    "The worker envelope raw output byte length or SHA-256 was missing or inconsistent.",
                    TryExtractPreview(outcome.RawOutputBytes),
                    diagnosticsJson);
            }

            var actualRawSha = SHA256.HashData(outcome.RawOutputBytes);
            if (!CryptographicOperations.FixedTimeEquals(actualRawSha, declaredSha))
            {
                return new EnvelopeValidationOutcome.Rejected(
                    "worker_output_digest_mismatch",
                    "Recomputed raw output SHA-256 disagreed with the worker envelope digest.",
                    TryExtractPreview(outcome.RawOutputBytes),
                    diagnosticsJson);
            }

            string decodedText;
            try
            {
                decodedText = StrictUtf8.GetString(outcome.RawOutputBytes);
            }
            catch (DecoderFallbackException)
            {
                return new EnvelopeValidationOutcome.Rejected(
                    "worker_invalid_utf8",
                    "The raw worker output contained invalid UTF-8 byte sequences.",
                    null,
                    diagnosticsJson);
            }

            var parsedPages = SafeNativeDisplayParser.ParsePages(decodedText);
            if (parsedPages.Count != work.PageCount)
            {
                return new EnvelopeValidationOutcome.Rejected(
                    "page_count_mismatch",
                    $"Parsed <PAGE> marker count ({parsedPages.Count}) disagreed with document page count ({work.PageCount}).",
                    TryExtractPreview(outcome.RawOutputBytes),
                    diagnosticsJson);
            }

            var timingsEl = root.TryGetProperty("timings", out var tEl) && tEl.ValueKind == JsonValueKind.Object ? tEl : default;
            var startedUtc = TryParseUtc(timingsEl, "started_at_utc") ?? nowUtc;
            var completedUtc = TryParseUtc(timingsEl, "completed_at_utc") ?? nowUtc;
            var loadMs = TryGetInt64(timingsEl, "load_duration_ms", out var lMs) ? lMs : 0L;
            var renderMs = TryGetInt64(timingsEl, "render_duration_ms", out var rMs) ? rMs : 0L;
            var inferMs = TryGetInt64(timingsEl, "infer_duration_ms", out var iMs) ? iMs : 0L;
            var totalMs = TryGetInt64(timingsEl, "total_duration_ms", out var totMs) ? totMs : 0L;

            var accepted = ExtractionResult.Create(
                Guid.CreateVersion7(nowUtc),
                work.DocumentId,
                work.JobId,
                work.AttemptId,
                work.FencingToken,
                work.InputSha256,
                work.InputByteLength,
                work.PageCount,
                outcome.RawOutputBytes,
                declaredSha,
                ExtractionCeilings.ModelRepoId,
                ExtractionCeilings.ModelRevision,
                envManifestSha,
                envLockSha,
                envWorkerSha,
                envConfigSha,
                rendererIdentity,
                genSettingsJson,
                finishReason,
                outPages,
                startedUtc,
                completedUtc,
                loadMs,
                renderMs,
                inferMs,
                totalMs,
                diagnosticsJson);

            return new EnvelopeValidationOutcome.Accepted(accepted);
        }
    }

    private static string? TryExtractPreview(byte[]? raw)
    {
        if (raw is null || raw.Length == 0)
        {
            return null;
        }

        var slice = raw.AsSpan(0, Math.Min(raw.Length, ExecutionAttempt.MaxDiagnosticOutputChars));
        return Encoding.UTF8.GetString(slice);
    }

    private static string? GetString(JsonElement obj, string prop) =>
        obj.ValueKind == JsonValueKind.Object && obj.TryGetProperty(prop, out var val) && val.ValueKind == JsonValueKind.String
            ? val.GetString()
            : null;

    private static bool TryGetInt32(JsonElement obj, string prop, out int value)
    {
        value = 0;
        return obj.ValueKind == JsonValueKind.Object && obj.TryGetProperty(prop, out var val) &&
               val.ValueKind == JsonValueKind.Number && val.TryGetInt32(out value);
    }

    private static bool TryGetInt64(JsonElement obj, string prop, out long value)
    {
        value = 0;
        return obj.ValueKind == JsonValueKind.Object && obj.TryGetProperty(prop, out var val) &&
               val.ValueKind == JsonValueKind.Number && val.TryGetInt64(out value);
    }

    private static bool MatchesGuid(JsonElement obj, string prop, Guid expected) =>
        GetString(obj, prop) is { } text && Guid.TryParseExact(text, "D", out var parsed) && parsed == expected;

    private static bool TryParseSha256Hex(string? hex, out byte[] bytes)
    {
        bytes = [];
        if (hex is not { Length: 64 })
        {
            return false;
        }

        try
        {
            bytes = Convert.FromHexString(hex);
            return bytes.Length == 32;
        }
        catch (FormatException)
        {
            return false;
        }
    }

    private static DateTimeOffset? TryParseUtc(JsonElement obj, string prop)
    {
        if (GetString(obj, prop) is { } text &&
            DateTimeOffset.TryParse(text, CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal, out var parsed))
        {
            var utc = parsed.ToUniversalTime();
            return new DateTimeOffset(utc.UtcTicks - (utc.UtcTicks % 10), TimeSpan.Zero);
        }

        return null;
    }
}

public abstract record EnvelopeValidationOutcome
{
    private EnvelopeValidationOutcome()
    {
    }

    public sealed record Accepted(ExtractionResult Result) : EnvelopeValidationOutcome;

    public sealed record Rejected(
        string FailureCode,
        string SafeDetail,
        string? DiagnosticRawOutputUtf8,
        string? DiagnosticMetadataJson) : EnvelopeValidationOutcome;
}
