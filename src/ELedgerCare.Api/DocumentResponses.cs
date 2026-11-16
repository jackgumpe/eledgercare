using System.Globalization;
using ELedgerCare.Application.Extraction;
using ELedgerCare.Application.Review;
using ELedgerCare.Domain.Processing;
using ELedgerCare.Domain.Review;

namespace ELedgerCare.Api;

/// <summary>Extended document view returned by GET /api/documents/{documentId}.</summary>
public sealed record DocumentDetailResponse(
    Guid DocumentId,
    Guid JobId,
    string Status,
    DateTimeOffset SubmittedAtUtc,
    int ByteLength,
    string Sha256,
    string OriginalUrl,
    string PreviewUrl,
    int AdmittedPageCount,
    string ExtractionUrl,
    string ReviewUrl,
    Guid? CurrentAttemptId,
    Guid? AcceptedResultId,
    WorkOrderReviewSummaryDto? WorkOrderReview)
{
    public static DocumentDetailResponse From(DocumentSummaryProjection summary) => new(
        summary.DocumentId,
        summary.JobId,
        summary.Status.ToWire(),
        summary.SubmittedAtUtc.ToUniversalTime(),
        summary.ByteLength,
        Convert.ToHexStringLower(summary.Sha256),
        string.Create(CultureInfo.InvariantCulture, $"/api/documents/{summary.DocumentId:D}/original"),
        string.Create(CultureInfo.InvariantCulture, $"/api/documents/{summary.DocumentId:D}/preview"),
        summary.AdmittedPageCount,
        string.Create(CultureInfo.InvariantCulture, $"/api/documents/{summary.DocumentId:D}/extraction"),
        string.Create(CultureInfo.InvariantCulture, $"/api/documents/{summary.DocumentId:D}/review"),
        summary.CurrentAttemptId,
        summary.AcceptedResultId,
        summary.WorkOrderReview is not null
            ? WorkOrderReviewSummaryDto.From(summary.DocumentId, summary.WorkOrderReview)
            : null);
}

public sealed record DocumentExtractionResponse(
    Guid DocumentId,
    Guid JobId,
    string Status,
    int AdmittedPageCount,
    int OriginalByteLength,
    string OriginalSha256,
    string OriginalUrl,
    string PreviewUrl,
    string ReviewUrl,
    DateTimeOffset SubmittedAtUtc,
    DateTimeOffset? QueuedAtUtc,
    DateTimeOffset UpdatedAtUtc,
    bool WorkerEnabled,
    bool ProfileSupported,
    int MaxSupportedPages,
    bool CanRequestExtraction,
    bool CanRetryExtraction,
    string? UnavailableReason,
    AttemptSummaryDto? CurrentAttempt,
    IReadOnlyList<AttemptSummaryDto> Attempts,
    AcceptedExtractionResultDto? Result,
    WorkOrderReviewSummaryDto? WorkOrderReview)
{
    public static DocumentExtractionResponse From(DocumentExtractionSnapshot snapshot, ExtractionSettings settings)
    {
        var profileSupported = snapshot.AdmittedPageCount >= 1 && snapshot.AdmittedPageCount <= settings.MaxExtractionPages;
        var canRequest = snapshot.Status == ProcessingStatus.AwaitingExtraction && profileSupported && settings.Enabled;
        var canRetry = snapshot.Status is ProcessingStatus.Failed or ProcessingStatus.Interrupted &&
                       profileSupported && settings.Enabled && snapshot.Attempts.Count > 0;

        string? unavailableReason = null;
        if (!profileSupported)
        {
            unavailableReason = string.Create(
                CultureInfo.InvariantCulture,
                $"This document has {snapshot.AdmittedPageCount} pages. Local extraction supports 1 to {settings.MaxExtractionPages} pages in this profile.");
        }
        else if (!settings.Enabled && snapshot.Status != ProcessingStatus.Completed)
        {
            unavailableReason = "Local OCR execution is disabled by default until a bounded runtime release is configured. Previously saved results remain available.";
        }

        var attempts = snapshot.Attempts.Select(AttemptSummaryDto.From).ToArray();
        var currentAttempt = attempts.Length > 0 ? attempts[^1] : null;
        var result = snapshot.AcceptedResult is not null
            ? AcceptedExtractionResultDto.From(snapshot.AcceptedResult)
            : null;
        var reviewSummary = snapshot.WorkOrderReview is not null
            ? WorkOrderReviewSummaryDto.From(snapshot.DocumentId, snapshot.WorkOrderReview)
            : null;

        return new DocumentExtractionResponse(
            snapshot.DocumentId,
            snapshot.JobId,
            snapshot.Status.ToWire(),
            snapshot.AdmittedPageCount,
            snapshot.OriginalByteLength,
            Convert.ToHexStringLower(snapshot.OriginalSha256),
            string.Create(CultureInfo.InvariantCulture, $"/api/documents/{snapshot.DocumentId:D}/original"),
            string.Create(CultureInfo.InvariantCulture, $"/api/documents/{snapshot.DocumentId:D}/preview"),
            string.Create(CultureInfo.InvariantCulture, $"/api/documents/{snapshot.DocumentId:D}/review"),
            snapshot.SubmittedAtUtc.ToUniversalTime(),
            snapshot.QueuedAtUtc?.ToUniversalTime(),
            snapshot.UpdatedAtUtc.ToUniversalTime(),
            settings.Enabled,
            profileSupported,
            settings.MaxExtractionPages,
            canRequest,
            canRetry,
            unavailableReason,
            currentAttempt,
            attempts,
            result,
            reviewSummary);
    }
}

public sealed record WorkOrderReviewSummaryDto(
    string ProfileId,
    string Status,
    int CurrentRevisionNumber,
    int AcceptedFieldCount,
    int EditedFieldCount,
    int UnknownFieldCount,
    int UnreviewedFieldCount,
    DateTimeOffset UpdatedAtUtc,
    string ReviewUrl)
{
    public static WorkOrderReviewSummaryDto From(Guid documentId, WorkOrderReviewHeadSummary summary) => new(
        summary.ProfileId,
        summary.Status.ToWire(),
        summary.CurrentRevisionNumber,
        summary.AcceptedFieldCount,
        summary.EditedFieldCount,
        summary.UnknownFieldCount,
        summary.UnreviewedFieldCount,
        summary.UpdatedAtUtc.ToUniversalTime(),
        string.Create(CultureInfo.InvariantCulture, $"/api/documents/{documentId:D}/review"));
}

public sealed record AttemptSummaryDto(
    Guid AttemptId,
    int AttemptNumber,
    string Status,
    string Phase,
    DateTimeOffset StartedAtUtc,
    DateTimeOffset LastHeartbeatAtUtc,
    DateTimeOffset? EndedAtUtc,
    string? FailureCode,
    string? FailureMessage)
{
    public static AttemptSummaryDto From(AttemptSummaryProjection attempt) => new(
        attempt.AttemptId,
        attempt.AttemptNumber,
        attempt.Status.ToWire(),
        attempt.Phase,
        attempt.StartedAtUtc.ToUniversalTime(),
        attempt.LastHeartbeatAtUtc.ToUniversalTime(),
        attempt.EndedAtUtc?.ToUniversalTime(),
        attempt.FailureCode,
        attempt.FailureDetail);
}

public sealed record AcceptedExtractionResultDto(
    Guid ResultId,
    Guid AttemptId,
    string ReviewStatus,
    DateTimeOffset CompletedAtUtc,
    int PageCount,
    int RawByteLength,
    string RawSha256,
    string RawText,
    IReadOnlyList<ExtractedPageDto> Pages,
    ExtractionProvenanceDto Provenance)
{
    public static AcceptedExtractionResultDto From(ExtractionResult result)
    {
        var rawText = result.DecodeStrictUtf8();
        var pages = SafeNativeDisplayParser.ParsePages(rawText)
            .Select(p => new ExtractedPageDto(
                p.PageNumber,
                p.RawPageText,
                p.Blocks.Select(b => new ExtractedBlockDto(b.Kind, b.Text, b.TableRows)).ToArray()))
            .ToArray();

        return new AcceptedExtractionResultDto(
            result.ResultId,
            result.AttemptId,
            ExtractionCeilings.ReviewStatusUnreviewed,
            result.CompletedAtUtc.ToUniversalTime(),
            result.PageCount,
            result.RawOutputByteLength,
            Convert.ToHexStringLower(result.RawOutputSha256),
            rawText,
            pages,
            new ExtractionProvenanceDto(
                result.ModelRepoId,
                result.ModelRevision,
                Convert.ToHexStringLower(result.ModelManifestSha256),
                Convert.ToHexStringLower(result.DependencyLockSha256),
                Convert.ToHexStringLower(result.WorkerSourceDigest),
                Convert.ToHexStringLower(result.WorkerConfigDigest),
                result.RendererIdentity,
                result.FinishReason,
                ExtractionCeilings.RequiredProvenanceException,
                result.StartedAtUtc.ToUniversalTime(),
                result.CompletedAtUtc.ToUniversalTime(),
                result.LoadDurationMs,
                result.RenderDurationMs,
                result.InferDurationMs,
                result.TotalDurationMs));
    }
}

public sealed record ExtractedPageDto(
    int PageNumber,
    string RawPageText,
    IReadOnlyList<ExtractedBlockDto> Blocks);

public sealed record ExtractedBlockDto(
    string Kind,
    string Text,
    IReadOnlyList<IReadOnlyList<string>>? TableRows);

public sealed record ExtractionProvenanceDto(
    string ModelRepoId,
    string ModelRevision,
    string ModelManifestSha256,
    string DependencyLockSha256,
    string WorkerSourceSha256,
    string WorkerConfigSha256,
    string RendererIdentity,
    string FinishReason,
    string ProvenanceException,
    DateTimeOffset StartedAtUtc,
    DateTimeOffset CompletedAtUtc,
    long LoadDurationMs,
    long RenderDurationMs,
    long InferDurationMs,
    long TotalDurationMs);
