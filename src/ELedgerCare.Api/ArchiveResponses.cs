using ELedgerCare.Application.Archive;
using ELedgerCare.Domain.Archive;
using ELedgerCare.Domain.Processing;
using ELedgerCare.Domain.Review;

namespace ELedgerCare.Api;

public sealed record ArchiveSearchResponse(
    string Query,
    IReadOnlyList<string> Terms,
    string Source,
    int Limit,
    bool HasMore,
    string? NextCursor,
    string ProjectionVersion,
    IReadOnlyList<ArchiveDocumentCardResponse> Items)
{
    public static ArchiveSearchResponse From(ArchiveSearchPage page) => new(
        Query: page.NormalizedQuery,
        Terms: page.Terms,
        Source: page.Source.ToWire(),
        Limit: page.Limit,
        HasMore: page.HasMore,
        NextCursor: page.NextCursor,
        ProjectionVersion: ArchiveSchema.ProjectionVersion,
        Items: page.Items.Select(ArchiveDocumentCardResponse.From).ToArray());
}

public sealed record ArchiveDocumentCardResponse(
    string DocumentId,
    string ShortDocumentId,
    string DisplayTitle,
    bool TitleFromReviewed,
    DateTimeOffset SubmittedAtUtc,
    int AdmittedPageCount,
    int OriginalByteLength,
    string OriginalSha256,
    string OriginalUrl,
    string Status,
    ArchiveMachineSummaryResponse? Machine,
    ArchiveReviewedSummaryResponse? LatestReviewed,
    ArchiveHeadSummaryResponse? CurrentReviewHead,
    bool HasNewerDraft,
    IReadOnlyList<string> ContributingSources,
    IReadOnlyList<ArchiveWitnessResponse> Witnesses,
    bool HasMoreMatchesInDocument)
{
    public static ArchiveDocumentCardResponse From(ArchiveDocumentCard card)
    {
        var docIdStr = card.DocumentId.ToString("D");
        var shortId = docIdStr[..8];
        var wo = card.LatestReviewed?.WorkOrderId;
        var prop = card.LatestReviewed?.PropertyName;

        string displayTitle;
        bool titleFromReviewed;
        if (!string.IsNullOrWhiteSpace(wo) && !string.IsNullOrWhiteSpace(prop))
        {
            displayTitle = $"{wo} — {prop}";
            titleFromReviewed = true;
        }
        else if (!string.IsNullOrWhiteSpace(wo))
        {
            displayTitle = wo;
            titleFromReviewed = true;
        }
        else if (!string.IsNullOrWhiteSpace(prop))
        {
            displayTitle = prop;
            titleFromReviewed = true;
        }
        else
        {
            displayTitle = $"Document {shortId} · {card.SubmittedAtUtc.UtcDateTime:yyyy-MM-dd HH:mm} UTC";
            titleFromReviewed = false;
        }

        ArchiveMachineSummaryResponse? machine = null;
        if (card.ResultId is Guid resultId &&
            card.RawOutputSha256 is { } rawSha &&
            card.ExtractedPageCount is int pageCount &&
            card.ProjectionVersion is { } projVer &&
            card.ProjectionSha256 is { } projSha &&
            card.ProjectionHasFallback is bool hasFallback)
        {
            machine = new ArchiveMachineSummaryResponse(
                ResultId: resultId.ToString("D"),
                PageCount: pageCount,
                RawSha256: Convert.ToHexStringLower(rawSha),
                ProjectionVersion: projVer,
                ProjectionSha256: Convert.ToHexStringLower(projSha),
                HasFallback: hasFallback);
        }

        var latestReviewed = card.LatestReviewed is { } lr
            ? new ArchiveReviewedSummaryResponse(
                RevisionNumber: lr.RevisionNumber,
                SavedAtUtc: lr.SavedAtUtc,
                WorkOrderId: lr.WorkOrderId,
                PropertyName: lr.PropertyName)
            : null;

        var currentHead = card.CurrentReviewHead is { } h
            ? new ArchiveHeadSummaryResponse(
                CurrentRevisionNumber: h.CurrentRevisionNumber,
                CurrentStatus: h.CurrentStatus.ToWire(),
                UpdatedAtUtc: h.UpdatedAtUtc)
            : null;

        return new ArchiveDocumentCardResponse(
            DocumentId: docIdStr,
            ShortDocumentId: shortId,
            DisplayTitle: displayTitle,
            TitleFromReviewed: titleFromReviewed,
            SubmittedAtUtc: card.SubmittedAtUtc,
            AdmittedPageCount: card.AdmittedPageCount,
            OriginalByteLength: card.OriginalByteLength,
            OriginalSha256: Convert.ToHexStringLower(card.OriginalSha256),
            OriginalUrl: $"/api/documents/{docIdStr}/original",
            Status: card.ProcessingStatus.ToWire(),
            Machine: machine,
            LatestReviewed: latestReviewed,
            CurrentReviewHead: currentHead,
            HasNewerDraft: card.HasNewerDraft,
            ContributingSources: card.ContributingSources,
            Witnesses: card.Witnesses.Select(ArchiveWitnessResponse.From).ToArray(),
            HasMoreMatchesInDocument: card.HasMoreMatchesInDocument);
    }
}

public sealed record ArchiveMachineSummaryResponse(
    string ResultId,
    int PageCount,
    string RawSha256,
    string ProjectionVersion,
    string ProjectionSha256,
    bool HasFallback);

public sealed record ArchiveReviewedSummaryResponse(
    int RevisionNumber,
    DateTimeOffset SavedAtUtc,
    string? WorkOrderId,
    string? PropertyName);

public sealed record ArchiveHeadSummaryResponse(
    int CurrentRevisionNumber,
    string CurrentStatus,
    DateTimeOffset UpdatedAtUtc);

public sealed record ArchiveWitnessResponse(
    string SourceKind,
    string SourceLabel,
    string? ResultId,
    int? PageNumber,
    bool IsFallback,
    int? RevisionNumber,
    string? FieldKey,
    string? FieldLabel,
    int? ConsultedPageNumber,
    string Snippet,
    bool PrefixClipped,
    bool SuffixClipped,
    IReadOnlyList<ArchiveSnippetSegmentResponse> Segments,
    IReadOnlyList<string> MatchedTerms)
{
    public static ArchiveWitnessResponse From(SelectedArchiveWitness w) => new(
        SourceKind: w.SourceKind,
        SourceLabel: w.SourceLabel,
        ResultId: w.ResultId?.ToString("D"),
        PageNumber: w.PageNumber,
        IsFallback: w.IsFallback,
        RevisionNumber: w.RevisionNumber,
        FieldKey: w.FieldKey,
        FieldLabel: w.FieldLabel,
        ConsultedPageNumber: w.ConsultedPageNumber,
        Snippet: w.Snippet,
        PrefixClipped: w.PrefixClipped,
        SuffixClipped: w.SuffixClipped,
        Segments: w.Segments.Select(static s => new ArchiveSnippetSegmentResponse(s.Text, s.Highlighted)).ToArray(),
        MatchedTerms: w.MatchedTerms);
}

public sealed record ArchiveSnippetSegmentResponse(
    string Text,
    bool Highlighted);
