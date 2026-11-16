using System.Security.Cryptography;
using System.Text.Json;
using ELedgerCare.Domain.Documents;

namespace ELedgerCare.Domain.Review;

/// <summary>
/// Deterministic SHA-256 request digest over all caller-supplied parameters of a review revision save
/// (<c>docs/design/F3-review-correction.md</c> &amp; F3-BIC-03).
/// Fields are serialized in canonical <c>0..4</c> schema order; server-owned provenance/timestamps are excluded.
/// Any difference in <c>documentId</c>, <c>profileId</c>, <c>resultId</c>, <c>expectedRevision</c>,
/// <c>status</c>, <c>operatorDisplayLabel</c>, or any field's <c>decision</c>/<c>value</c>/<c>unknownReason</c>/<c>consultedSource</c>
/// produces a distinct 32-byte digest.
/// </summary>
public static class ReviewRequestDigest
{
    public static byte[] ComputeSha256(
        Guid documentId,
        string profileId,
        Guid resultId,
        int expectedRevision,
        ReviewRevisionStatus status,
        string? operatorDisplayLabel,
        IReadOnlyList<CanonicalReviewFieldInput> orderedFields)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(profileId);
        ArgumentNullException.ThrowIfNull(orderedFields);
        if (orderedFields.Count != WorkOrderReviewSchema.FieldCount)
        {
            throw new ArgumentException($"Expected exactly {WorkOrderReviewSchema.FieldCount} ordered fields.", nameof(orderedFields));
        }

        using var buffer = new MemoryStream();
        using (var writer = new Utf8JsonWriter(buffer))
        {
            writer.WriteStartObject();
            writer.WriteString("schema", WorkOrderReviewSchema.RequestDigestSchema);
            writer.WriteString("documentId", documentId.ToString("D"));
            writer.WriteString("profileId", profileId);
            writer.WriteString("resultId", resultId.ToString("D"));
            writer.WriteNumber("expectedRevision", expectedRevision);
            writer.WriteString("status", status.ToWire());
            if (operatorDisplayLabel is null)
            {
                writer.WriteNull("operatorDisplayLabel");
            }
            else
            {
                writer.WriteString("operatorDisplayLabel", operatorDisplayLabel);
            }

            writer.WriteStartArray("fields");
            for (var i = 0; i < WorkOrderReviewSchema.FieldCount; i++)
            {
                var field = orderedFields[i];
                var expectedKey = WorkOrderReviewSchema.Fields[i].FieldKey;
                if (!string.Equals(field.FieldKey, expectedKey, StringComparison.Ordinal))
                {
                    throw new ArgumentException($"Field at ordinal {i} must be '{expectedKey}', got '{field.FieldKey}'.", nameof(orderedFields));
                }

                writer.WriteStartObject();
                writer.WriteString("fieldKey", field.FieldKey);
                writer.WriteString("decision", field.Decision.ToWire());
                if (field.Value is null)
                {
                    writer.WriteNull("value");
                }
                else
                {
                    writer.WriteString("value", field.Value);
                }

                if (field.UnknownReason is null)
                {
                    writer.WriteNull("unknownReason");
                }
                else
                {
                    writer.WriteString("unknownReason", field.UnknownReason);
                }

                if (field.CallerConsultedSource is null)
                {
                    writer.WriteNull("consultedSource");
                }
                else
                {
                    var src = field.CallerConsultedSource;
                    writer.WriteStartObject("consultedSource");
                    writer.WriteNumber("pageNumber", src.PageNumber);
                    writer.WriteNumber("blockOrdinal", src.BlockOrdinal);
                    if (src.TableRow is { } tr)
                    {
                        writer.WriteNumber("tableRow", tr);
                    }
                    else
                    {
                        writer.WriteNull("tableRow");
                    }

                    if (src.TableColumn is { } tc)
                    {
                        writer.WriteNumber("tableColumn", tc);
                    }
                    else
                    {
                        writer.WriteNull("tableColumn");
                    }

                    writer.WriteEndObject();
                }

                writer.WriteEndObject();
            }

            writer.WriteEndArray();
            writer.WriteEndObject();
        }

        return SHA256.HashData(buffer.GetBuffer().AsSpan(0, (int)buffer.Length));
    }
}

public sealed record CanonicalReviewFieldInput(
    string FieldKey,
    ReviewFieldDecision Decision,
    string? Value,
    string? UnknownReason,
    ReviewSourceCoordinate? CallerConsultedSource);

/// <summary>
/// Small mutable review-head row identifying the current revision for a document/result while keeping
/// <c>result_id</c>, <c>input_sha256</c>, <c>raw_output_sha256</c>, <c>profile_id</c>,
/// <c>field_schema_version</c>, <c>suggestion_policy_version</c>, and first-save <c>machine_snapshot_json</c>
/// immutable at both the application and PostgreSQL column-grant layers (F3-BIC-02).
/// </summary>
public sealed class WorkOrderReviewHead
{
    private WorkOrderReviewHead()
    {
        InputSha256 = [];
        RawOutputSha256 = [];
        ProfileId = WorkOrderReviewSchema.ProfileId;
        FieldSchemaVersion = WorkOrderReviewSchema.FieldSchemaVersion;
        SuggestionPolicyVersion = WorkOrderReviewSchema.SuggestionPolicyVersion;
        MachineSnapshotJson = "{}";
    }

    private WorkOrderReviewHead(
        Guid documentId,
        Guid resultId,
        byte[] inputSha256,
        byte[] rawOutputSha256,
        string machineSnapshotJson,
        int currentRevisionNumber,
        Guid currentRevisionId,
        ReviewRevisionStatus currentStatus,
        DateTimeOffset createdAtUtc,
        DateTimeOffset updatedAtUtc)
    {
        DocumentId = documentId;
        ResultId = resultId;
        InputSha256 = [.. inputSha256];
        RawOutputSha256 = [.. rawOutputSha256];
        ProfileId = WorkOrderReviewSchema.ProfileId;
        FieldSchemaVersion = WorkOrderReviewSchema.FieldSchemaVersion;
        SuggestionPolicyVersion = WorkOrderReviewSchema.SuggestionPolicyVersion;
        MachineSnapshotJson = machineSnapshotJson;
        CurrentRevisionNumber = currentRevisionNumber;
        CurrentRevisionId = currentRevisionId;
        CurrentStatus = currentStatus;
        CreatedAtUtc = createdAtUtc;
        UpdatedAtUtc = updatedAtUtc;
    }

    public Guid DocumentId { get; private init; }

    public Guid ResultId { get; private init; }

    public byte[] InputSha256 { get; private init; }

    public byte[] RawOutputSha256 { get; private init; }

    public string ProfileId { get; private init; }

    public string FieldSchemaVersion { get; private init; }

    public string SuggestionPolicyVersion { get; private init; }

    public string MachineSnapshotJson { get; private init; }

    public int CurrentRevisionNumber { get; private set; }

    public Guid CurrentRevisionId { get; private set; }

    public ReviewRevisionStatus CurrentStatus { get; private set; }

    public DateTimeOffset CreatedAtUtc { get; private init; }

    public DateTimeOffset UpdatedAtUtc { get; private set; }

    public static WorkOrderReviewHead CreateInitial(
        Guid documentId,
        Guid resultId,
        byte[] inputSha256,
        byte[] rawOutputSha256,
        string machineSnapshotJson,
        Guid revision1Id,
        ReviewRevisionStatus status,
        DateTimeOffset nowUtc)
    {
        if (documentId == Guid.Empty || resultId == Guid.Empty || revision1Id == Guid.Empty)
        {
            throw new ArgumentException("Identifiers must be non-empty UUIDs.");
        }

        if (inputSha256 is not { Length: OriginalArtifact.Sha256Length } ||
            rawOutputSha256 is not { Length: OriginalArtifact.Sha256Length })
        {
            throw new ArgumentException("SHA-256 digests must be 32 bytes.");
        }

        ArgumentException.ThrowIfNullOrWhiteSpace(machineSnapshotJson);

        return new WorkOrderReviewHead(
            documentId,
            resultId,
            inputSha256,
            rawOutputSha256,
            machineSnapshotJson,
            currentRevisionNumber: 1,
            currentRevisionId: revision1Id,
            currentStatus: status,
            createdAtUtc: nowUtc,
            updatedAtUtc: nowUtc);
    }
}

/// <summary>
/// Append-only human review revision bound to one document and its accepted extraction result.
/// </summary>
public sealed class WorkOrderReviewRevision
{
    private readonly List<WorkOrderReviewField> fields = [];

    private WorkOrderReviewRevision()
    {
        RequestSha256 = [];
        InputSha256 = [];
        RawOutputSha256 = [];
        ProfileId = WorkOrderReviewSchema.ProfileId;
        FieldSchemaVersion = WorkOrderReviewSchema.FieldSchemaVersion;
        SuggestionPolicyVersion = WorkOrderReviewSchema.SuggestionPolicyVersion;
    }

    private WorkOrderReviewRevision(
        Guid revisionId,
        Guid documentId,
        Guid resultId,
        int revisionNumber,
        int? previousRevisionNumber,
        ReviewRevisionStatus status,
        Guid idempotencyKey,
        byte[] requestSha256,
        byte[] inputSha256,
        byte[] rawOutputSha256,
        string? operatorDisplayLabel,
        int acceptedFieldCount,
        int editedFieldCount,
        int unknownFieldCount,
        int unreviewedFieldCount,
        DateTimeOffset savedAtUtc,
        IReadOnlyList<WorkOrderReviewField> orderedFields)
    {
        RevisionId = revisionId;
        DocumentId = documentId;
        ResultId = resultId;
        RevisionNumber = revisionNumber;
        PreviousRevisionNumber = previousRevisionNumber;
        Status = status;
        IdempotencyKey = idempotencyKey;
        RequestSha256 = [.. requestSha256];
        InputSha256 = [.. inputSha256];
        RawOutputSha256 = [.. rawOutputSha256];
        ProfileId = WorkOrderReviewSchema.ProfileId;
        FieldSchemaVersion = WorkOrderReviewSchema.FieldSchemaVersion;
        SuggestionPolicyVersion = WorkOrderReviewSchema.SuggestionPolicyVersion;
        OperatorDisplayLabel = operatorDisplayLabel;
        AcceptedFieldCount = acceptedFieldCount;
        EditedFieldCount = editedFieldCount;
        UnknownFieldCount = unknownFieldCount;
        UnreviewedFieldCount = unreviewedFieldCount;
        SavedAtUtc = savedAtUtc;
        fields.AddRange(orderedFields);
    }

    public Guid RevisionId { get; private init; }

    public Guid DocumentId { get; private init; }

    public Guid ResultId { get; private init; }

    public int RevisionNumber { get; private init; }

    public int? PreviousRevisionNumber { get; private init; }

    public ReviewRevisionStatus Status { get; private init; }

    public Guid IdempotencyKey { get; private init; }

    public byte[] RequestSha256 { get; private init; }

    public byte[] InputSha256 { get; private init; }

    public byte[] RawOutputSha256 { get; private init; }

    public string ProfileId { get; private init; }

    public string FieldSchemaVersion { get; private init; }

    public string SuggestionPolicyVersion { get; private init; }

    public string? OperatorDisplayLabel { get; private init; }

    public int AcceptedFieldCount { get; private init; }

    public int EditedFieldCount { get; private init; }

    public int UnknownFieldCount { get; private init; }

    public int UnreviewedFieldCount { get; private init; }

    public DateTimeOffset SavedAtUtc { get; private init; }

    public IReadOnlyList<WorkOrderReviewField> Fields => fields;

    public static WorkOrderReviewRevision Create(
        Guid revisionId,
        Guid documentId,
        Guid resultId,
        int revisionNumber,
        ReviewRevisionStatus status,
        Guid idempotencyKey,
        byte[] requestSha256,
        byte[] inputSha256,
        byte[] rawOutputSha256,
        string? operatorDisplayLabel,
        DateTimeOffset savedAtUtc,
        IReadOnlyList<WorkOrderReviewField> orderedFields)
    {
        if (revisionId == Guid.Empty || documentId == Guid.Empty || resultId == Guid.Empty || idempotencyKey == Guid.Empty)
        {
            throw new ArgumentException("Identifiers must be non-empty UUIDs.");
        }

        if (revisionNumber is < 1 or > WorkOrderReviewSchema.MaxRevisionsPerResult)
        {
            throw new ArgumentOutOfRangeException(nameof(revisionNumber), revisionNumber,
                $"RevisionNumber must be within 1..{WorkOrderReviewSchema.MaxRevisionsPerResult}.");
        }

        if (requestSha256 is not { Length: OriginalArtifact.Sha256Length } ||
            inputSha256 is not { Length: OriginalArtifact.Sha256Length } ||
            rawOutputSha256 is not { Length: OriginalArtifact.Sha256Length })
        {
            throw new ArgumentException("SHA-256 digests must be 32 bytes.");
        }

        ArgumentNullException.ThrowIfNull(orderedFields);
        if (orderedFields.Count != WorkOrderReviewSchema.FieldCount)
        {
            throw new ArgumentException($"Revision must contain exactly {WorkOrderReviewSchema.FieldCount} fields.", nameof(orderedFields));
        }

        var accepted = 0;
        var edited = 0;
        var unknown = 0;
        var unreviewed = 0;
        for (var i = 0; i < WorkOrderReviewSchema.FieldCount; i++)
        {
            var f = orderedFields[i];
            if (f.RevisionId != revisionId || f.FieldOrdinal != i || f.FieldKey != WorkOrderReviewSchema.Fields[i].FieldKey)
            {
                throw new ArgumentException($"Field at ordinal {i} disagrees with canonical revision/field binding.", nameof(orderedFields));
            }

            switch (f.Decision)
            {
                case ReviewFieldDecision.Accepted:
                    accepted++;
                    break;
                case ReviewFieldDecision.Edited:
                    edited++;
                    break;
                case ReviewFieldDecision.Unknown:
                    unknown++;
                    break;
                case ReviewFieldDecision.Unreviewed:
                    unreviewed++;
                    break;
            }
        }

        if (status == ReviewRevisionStatus.Reviewed && unreviewed > 0)
        {
            throw new ArgumentException("A reviewed revision cannot contain unreviewed fields.", nameof(status));
        }

        int? prevRevision = revisionNumber == 1 ? null : revisionNumber - 1;

        return new WorkOrderReviewRevision(
            revisionId,
            documentId,
            resultId,
            revisionNumber,
            prevRevision,
            status,
            idempotencyKey,
            requestSha256,
            inputSha256,
            rawOutputSha256,
            operatorDisplayLabel,
            accepted,
            edited,
            unknown,
            unreviewed,
            savedAtUtc,
            orderedFields);
    }
}

/// <summary>
/// Append-only snapshot of one field's human decision, value, optional unknown reason, and server-verified consulted source.
/// </summary>
public sealed class WorkOrderReviewField
{
    private WorkOrderReviewField()
    {
        FieldKey = string.Empty;
    }

    private WorkOrderReviewField(
        Guid revisionId,
        int fieldOrdinal,
        string fieldKey,
        ReviewFieldDecision decision,
        string? humanValue,
        string? unknownReason,
        ReviewSourceReference? consultedSource)
    {
        RevisionId = revisionId;
        FieldOrdinal = fieldOrdinal;
        FieldKey = fieldKey;
        Decision = decision;
        HumanValue = humanValue;
        UnknownReason = unknownReason;
        ConsultedPageNumber = consultedSource?.PageNumber;
        ConsultedBlockOrdinal = consultedSource?.BlockOrdinal;
        ConsultedTableRow = consultedSource?.TableRow;
        ConsultedTableColumn = consultedSource?.TableColumn;
        ConsultedQuote = consultedSource?.SourceQuote;
    }

    public Guid RevisionId { get; private init; }

    public int FieldOrdinal { get; private init; }

    public string FieldKey { get; private init; }

    public ReviewFieldDecision Decision { get; private init; }

    public string? HumanValue { get; private init; }

    public string? UnknownReason { get; private init; }

    public int? ConsultedPageNumber { get; private init; }

    public int? ConsultedBlockOrdinal { get; private init; }

    public int? ConsultedTableRow { get; private init; }

    public int? ConsultedTableColumn { get; private init; }

    public string? ConsultedQuote { get; private init; }

    public ReviewSourceReference? GetConsultedSource() =>
        ConsultedPageNumber is { } page && ConsultedBlockOrdinal is { } block
            ? new ReviewSourceReference(page, block, ConsultedTableRow, ConsultedTableColumn, ConsultedQuote ?? string.Empty)
            : null;

    public static WorkOrderReviewField Create(
        Guid revisionId,
        WorkOrderFieldSpec spec,
        ReviewFieldDecision decision,
        string? humanValue,
        string? unknownReason,
        ReviewSourceReference? consultedSource)
    {
        ArgumentNullException.ThrowIfNull(spec);
        if (revisionId == Guid.Empty)
        {
            throw new ArgumentException("RevisionId must be non-empty.", nameof(revisionId));
        }

        return new WorkOrderReviewField(
            revisionId,
            spec.Ordinal,
            spec.FieldKey,
            decision,
            humanValue,
            unknownReason,
            consultedSource);
    }
}
