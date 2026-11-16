using System.Globalization;
using ELedgerCare.Application.Review;
using ELedgerCare.Domain.Review;

namespace ELedgerCare.Api;

public sealed record DocumentReviewResponse(
    Guid DocumentId,
    Guid JobId,
    Guid ResultId,
    string ProfileId,
    string FieldSchemaVersion,
    string SuggestionPolicyVersion,
    int PageCount,
    int OriginalByteLength,
    string OriginalSha256,
    string OriginalUrl,
    string PreviewUrl,
    int RawByteLength,
    string RawSha256,
    DateTimeOffset ExtractionCompletedAtUtc,
    string ModelRepoId,
    string ModelRevision,
    string ReviewState,
    int CurrentRevisionNumber,
    int MaxRevisions,
    bool CanSaveRevision,
    MachineSnapshotDto MachineSnapshot,
    ReviewRevisionDetailDto? CurrentRevision,
    IReadOnlyList<ReviewFieldViewDto> Fields,
    IReadOnlyList<ReviewRevisionSummaryDto> History)
{
    public static DocumentReviewResponse From(DocumentReviewSnapshot snapshot)
    {
        var reviewState = snapshot.CurrentStatus?.ToWire() ?? "unreviewed";
        var machineDto = MachineSnapshotDto.From(snapshot.MachineSnapshot);
        var currentRevDto = snapshot.CurrentRevision is not null
            ? ReviewRevisionDetailDto.From(snapshot.CurrentRevision)
            : null;
        var combinedFields = ReviewFieldViewDto.BuildOrdered(snapshot.MachineSnapshot, snapshot.CurrentRevision);
        var history = snapshot.History
            .Select(h => ReviewRevisionSummaryDto.From(snapshot.DocumentId, h, snapshot.CurrentRevisionNumber))
            .ToArray();

        return new DocumentReviewResponse(
            DocumentId: snapshot.DocumentId,
            JobId: snapshot.JobId,
            ResultId: snapshot.ResultId,
            ProfileId: WorkOrderReviewSchema.ProfileId,
            FieldSchemaVersion: WorkOrderReviewSchema.FieldSchemaVersion,
            SuggestionPolicyVersion: WorkOrderReviewSchema.SuggestionPolicyVersion,
            PageCount: snapshot.PageCount,
            OriginalByteLength: snapshot.OriginalByteLength,
            OriginalSha256: Convert.ToHexStringLower(snapshot.OriginalSha256),
            OriginalUrl: string.Create(CultureInfo.InvariantCulture, $"/api/documents/{snapshot.DocumentId:D}/original"),
            PreviewUrl: string.Create(CultureInfo.InvariantCulture, $"/api/documents/{snapshot.DocumentId:D}/preview"),
            RawByteLength: snapshot.RawOutputByteLength,
            RawSha256: Convert.ToHexStringLower(snapshot.RawOutputSha256),
            ExtractionCompletedAtUtc: snapshot.ExtractionCompletedAtUtc.ToUniversalTime(),
            ModelRepoId: snapshot.ModelRepoId,
            ModelRevision: snapshot.ModelRevision,
            ReviewState: reviewState,
            CurrentRevisionNumber: snapshot.CurrentRevisionNumber,
            MaxRevisions: WorkOrderReviewSchema.MaxRevisionsPerResult,
            CanSaveRevision: snapshot.CurrentRevisionNumber < WorkOrderReviewSchema.MaxRevisionsPerResult,
            MachineSnapshot: machineDto,
            CurrentRevision: currentRevDto,
            Fields: combinedFields,
            History: history);
    }
}

public sealed record SelectedReviewRevisionResponse(
    Guid DocumentId,
    Guid ResultId,
    string ProfileId,
    string FieldSchemaVersion,
    string SuggestionPolicyVersion,
    int PageCount,
    string OriginalSha256,
    string RawSha256,
    string OriginalUrl,
    string PreviewUrl,
    int CurrentRevisionNumber,
    string CurrentReviewState,
    bool IsCurrentHead,
    MachineSnapshotDto MachineSnapshot,
    ReviewRevisionDetailDto Revision,
    IReadOnlyList<ReviewFieldViewDto> Fields,
    IReadOnlyList<ReviewRevisionSummaryDto> History)
{
    public static SelectedReviewRevisionResponse From(SelectedReviewRevisionSnapshot snapshot) => new(
        DocumentId: snapshot.DocumentId,
        ResultId: snapshot.ResultId,
        ProfileId: WorkOrderReviewSchema.ProfileId,
        FieldSchemaVersion: WorkOrderReviewSchema.FieldSchemaVersion,
        SuggestionPolicyVersion: WorkOrderReviewSchema.SuggestionPolicyVersion,
        PageCount: snapshot.PageCount,
        OriginalSha256: Convert.ToHexStringLower(snapshot.OriginalSha256),
        RawSha256: Convert.ToHexStringLower(snapshot.RawOutputSha256),
        OriginalUrl: string.Create(CultureInfo.InvariantCulture, $"/api/documents/{snapshot.DocumentId:D}/original"),
        PreviewUrl: string.Create(CultureInfo.InvariantCulture, $"/api/documents/{snapshot.DocumentId:D}/preview"),
        CurrentRevisionNumber: snapshot.CurrentRevisionNumber,
        CurrentReviewState: snapshot.CurrentStatus.ToWire(),
        IsCurrentHead: snapshot.Revision.RevisionNumber == snapshot.CurrentRevisionNumber,
        MachineSnapshot: MachineSnapshotDto.From(snapshot.MachineSnapshot),
        Revision: ReviewRevisionDetailDto.From(snapshot.Revision),
        Fields: ReviewFieldViewDto.BuildOrdered(snapshot.MachineSnapshot, snapshot.Revision),
        History: snapshot.History
            .Select(h => ReviewRevisionSummaryDto.From(snapshot.DocumentId, h, snapshot.CurrentRevisionNumber))
            .ToArray());
}

public sealed record SaveReviewRevisionResponse(
    bool Replayed,
    bool IsCurrentHead,
    int CurrentRevisionNumber,
    string CurrentReviewState,
    int MaxRevisions,
    bool CanSaveRevision,
    MachineSnapshotDto MachineSnapshot,
    ReviewRevisionDetailDto Revision,
    IReadOnlyList<ReviewFieldViewDto> Fields,
    IReadOnlyList<ReviewRevisionSummaryDto> History)
{
    public static SaveReviewRevisionResponse From(SavedReviewRevisionResult result, bool replayed) => new(
        Replayed: replayed,
        IsCurrentHead: result.Revision.RevisionNumber == result.CurrentRevisionNumber,
        CurrentRevisionNumber: result.CurrentRevisionNumber,
        CurrentReviewState: result.CurrentStatus.ToWire(),
        MaxRevisions: WorkOrderReviewSchema.MaxRevisionsPerResult,
        CanSaveRevision: result.CurrentRevisionNumber < WorkOrderReviewSchema.MaxRevisionsPerResult,
        MachineSnapshot: MachineSnapshotDto.From(result.MachineSnapshot),
        Revision: ReviewRevisionDetailDto.From(result.Revision),
        Fields: ReviewFieldViewDto.BuildOrdered(result.MachineSnapshot, result.Revision),
        History: result.History
            .Select(h => ReviewRevisionSummaryDto.From(result.Revision.DocumentId, h, result.CurrentRevisionNumber))
            .ToArray());
}

public sealed record MachineSnapshotDto(
    string Schema,
    string ProfileId,
    string FieldSchemaVersion,
    string SuggestionPolicyVersion,
    Guid ResultId,
    string RawOutputSha256,
    IReadOnlyList<MachineFieldCandidateDto> Fields)
{
    public static MachineSnapshotDto From(WorkOrderMachineSnapshot snapshot) => new(
        snapshot.Schema,
        snapshot.ProfileId,
        snapshot.FieldSchemaVersion,
        snapshot.SuggestionPolicyVersion,
        snapshot.ResultId,
        snapshot.RawOutputSha256,
        snapshot.Fields.Select(MachineFieldCandidateDto.From).ToArray());
}

public sealed record MachineFieldCandidateDto(
    string FieldKey,
    string Status,
    string? Value,
    SourceReferenceDto? Source,
    IReadOnlyList<SourceReferenceDto> CompetingSources)
{
    public static MachineFieldCandidateDto From(WorkOrderMachineFieldCandidate c) => new(
        c.FieldKey,
        c.Status.ToWire(),
        c.Value,
        c.Source is not null ? SourceReferenceDto.From(c.Source) : null,
        c.CompetingSources.Select(SourceReferenceDto.From).ToArray());
}

public sealed record SourceReferenceDto(
    int PageNumber,
    int BlockOrdinal,
    int? TableRow,
    int? TableColumn,
    string SourceQuote)
{
    public static SourceReferenceDto From(ReviewSourceReference s) => new(
        s.PageNumber,
        s.BlockOrdinal,
        s.TableRow,
        s.TableColumn,
        s.SourceQuote);
}

public sealed record ReviewFieldViewDto(
    int Ordinal,
    string FieldKey,
    string Label,
    int MaxLength,
    bool Multiline,
    MachineFieldCandidateDto MachineCandidate,
    string Decision,
    string? Value,
    string? UnknownReason,
    SourceReferenceDto? ConsultedSource)
{
    public static IReadOnlyList<ReviewFieldViewDto> BuildOrdered(
        WorkOrderMachineSnapshot snapshot,
        ReviewRevisionDetailProjection? revision)
    {
        var items = new ReviewFieldViewDto[WorkOrderReviewSchema.FieldCount];
        for (var i = 0; i < WorkOrderReviewSchema.FieldCount; i++)
        {
            var spec = WorkOrderReviewSchema.Fields[i];
            var candidateDto = MachineFieldCandidateDto.From(snapshot.Fields[i]);
            var revField = revision?.Fields[i];
            items[i] = new ReviewFieldViewDto(
                Ordinal: spec.Ordinal,
                FieldKey: spec.FieldKey,
                Label: spec.DisplayLabel,
                MaxLength: spec.MaxChars,
                Multiline: spec.Multiline,
                MachineCandidate: candidateDto,
                Decision: revField?.Decision.ToWire() ?? ReviewFieldDecision.Unreviewed.ToWire(),
                Value: revField?.Value,
                UnknownReason: revField?.UnknownReason,
                ConsultedSource: revField?.ConsultedSource is { } cs ? SourceReferenceDto.From(cs) : null);
        }

        return items;
    }
}

public sealed record ReviewFieldSnapshotDto(
    int Ordinal,
    string FieldKey,
    string Decision,
    string? Value,
    string? UnknownReason,
    SourceReferenceDto? ConsultedSource)
{
    public static ReviewFieldSnapshotDto From(ReviewFieldProjection f) => new(
        f.FieldOrdinal,
        f.FieldKey,
        f.Decision.ToWire(),
        f.Value,
        f.UnknownReason,
        f.ConsultedSource is not null ? SourceReferenceDto.From(f.ConsultedSource) : null);
}

public sealed record ReviewRevisionDetailDto(
    Guid RevisionId,
    Guid DocumentId,
    Guid ResultId,
    int RevisionNumber,
    int? PreviousRevisionNumber,
    string Status,
    Guid IdempotencyKey,
    string RequestSha256,
    string InputSha256,
    string RawOutputSha256,
    string ProfileId,
    string FieldSchemaVersion,
    string SuggestionPolicyVersion,
    string? OperatorDisplayLabel,
    int AcceptedFieldCount,
    int EditedFieldCount,
    int UnknownFieldCount,
    int UnreviewedFieldCount,
    DateTimeOffset SavedAtUtc,
    IReadOnlyList<ReviewFieldSnapshotDto> Fields)
{
    public static ReviewRevisionDetailDto From(ReviewRevisionDetailProjection r) => new(
        r.RevisionId,
        r.DocumentId,
        r.ResultId,
        r.RevisionNumber,
        r.PreviousRevisionNumber,
        r.Status.ToWire(),
        r.IdempotencyKey,
        Convert.ToHexStringLower(r.RequestSha256),
        Convert.ToHexStringLower(r.InputSha256),
        Convert.ToHexStringLower(r.RawOutputSha256),
        r.ProfileId,
        r.FieldSchemaVersion,
        r.SuggestionPolicyVersion,
        r.OperatorDisplayLabel,
        r.AcceptedFieldCount,
        r.EditedFieldCount,
        r.UnknownFieldCount,
        r.UnreviewedFieldCount,
        r.SavedAtUtc.ToUniversalTime(),
        r.Fields.Select(ReviewFieldSnapshotDto.From).ToArray());
}

public sealed record ReviewRevisionSummaryDto(
    Guid RevisionId,
    int RevisionNumber,
    int? PreviousRevisionNumber,
    string Status,
    bool IsCurrentHead,
    string? OperatorDisplayLabel,
    int AcceptedFieldCount,
    int EditedFieldCount,
    int UnknownFieldCount,
    int UnreviewedFieldCount,
    DateTimeOffset SavedAtUtc,
    string RevisionUrl)
{
    public static ReviewRevisionSummaryDto From(Guid documentId, ReviewRevisionSummaryProjection s, int currentRevisionNumber) => new(
        s.RevisionId,
        s.RevisionNumber,
        s.PreviousRevisionNumber,
        s.Status.ToWire(),
        s.RevisionNumber == currentRevisionNumber,
        s.OperatorDisplayLabel,
        s.AcceptedFieldCount,
        s.EditedFieldCount,
        s.UnknownFieldCount,
        s.UnreviewedFieldCount,
        s.SavedAtUtc.ToUniversalTime(),
        string.Create(CultureInfo.InvariantCulture, $"/api/documents/{documentId:D}/review/revisions/{s.RevisionNumber}"));
}
