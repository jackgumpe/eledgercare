namespace ELedgerCare.Domain.Review;

/// <summary>
/// Frozen profile, version identifiers, field definitions, bounds, and wire status names for
/// WP-0008 F3 work-order review and correction (<c>docs/design/F3-review-correction.md</c>).
/// </summary>
public static class WorkOrderReviewSchema
{
    public const string ProfileId = "maintenance-work-order/1";
    public const string FieldSchemaVersion = "maintenance-work-order-fields/1";
    public const string SuggestionPolicyVersion = "work-order-suggestions/1";
    public const string RequestDigestSchema = "eledgercare.work-order-review-request/1";
    public const string MachineSnapshotSchema = "eledgercare.work-order-machine-snapshot/1";

    public const int MaxRequestBodyBytes = 32_768;
    public const int MaxRevisionsPerResult = 128;
    public const int MaxUnknownReasonChars = 500;
    public const int MaxOperatorDisplayLabelChars = 80;
    public const int MaxStoredQuoteChars = 4_096;
    public const int FieldCount = 5;

    public const string WorkOrderIdKey = "work_order_id";
    public const string PropertyNameKey = "property_name";
    public const string BuildingUnitKey = "building_unit";
    public const string RequestedDateKey = "requested_date";
    public const string IssueAndResolutionKey = "issue_and_resolution";

    public static readonly IReadOnlyList<WorkOrderFieldSpec> Fields =
    [
        new(
            Ordinal: 0,
            FieldKey: WorkOrderIdKey,
            DisplayLabel: "Work Order ID",
            ExactSourceLabel: "Work Order ID",
            MaxChars: 64,
            Multiline: false,
            AllowTitleHeading: false),
        new(
            Ordinal: 1,
            FieldKey: PropertyNameKey,
            DisplayLabel: "Property",
            ExactSourceLabel: "Property",
            MaxChars: 200,
            Multiline: false,
            AllowTitleHeading: false),
        new(
            Ordinal: 2,
            FieldKey: BuildingUnitKey,
            DisplayLabel: "Building / Unit",
            ExactSourceLabel: "Building / Unit",
            MaxChars: 120,
            Multiline: false,
            AllowTitleHeading: false),
        new(
            Ordinal: 3,
            FieldKey: RequestedDateKey,
            DisplayLabel: "Requested Date",
            ExactSourceLabel: "Requested Date",
            MaxChars: 64,
            Multiline: false,
            AllowTitleHeading: false),
        new(
            Ordinal: 4,
            FieldKey: IssueAndResolutionKey,
            DisplayLabel: "Issue & Resolution",
            ExactSourceLabel: "REPORTED SYMPTOM & TECHNICIAN RESOLUTION SUMMARY",
            MaxChars: 4_000,
            Multiline: true,
            AllowTitleHeading: true),
    ];

    private static readonly Dictionary<string, WorkOrderFieldSpec> FieldsByKey =
        Fields.ToDictionary(f => f.FieldKey, StringComparer.Ordinal);

    public static bool TryGetField(string? fieldKey, out WorkOrderFieldSpec spec)
    {
        if (fieldKey is not null && FieldsByKey.TryGetValue(fieldKey, out var found))
        {
            spec = found;
            return true;
        }

        spec = default!;
        return false;
    }
}

public sealed record WorkOrderFieldSpec(
    int Ordinal,
    string FieldKey,
    string DisplayLabel,
    string ExactSourceLabel,
    int MaxChars,
    bool Multiline,
    bool AllowTitleHeading);

public enum ReviewRevisionStatus
{
    Draft,
    Reviewed,
}

public static class ReviewRevisionStatusNames
{
    public static string ToWire(this ReviewRevisionStatus status) => status switch
    {
        ReviewRevisionStatus.Draft => "draft",
        ReviewRevisionStatus.Reviewed => "reviewed",
        _ => throw new ArgumentOutOfRangeException(nameof(status), status, null),
    };

    public static ReviewRevisionStatus FromWire(string value) => value switch
    {
        "draft" => ReviewRevisionStatus.Draft,
        "reviewed" => ReviewRevisionStatus.Reviewed,
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, "Unrecognized review revision status."),
    };

    public static bool TryFromWire(string? value, out ReviewRevisionStatus status)
    {
        switch (value)
        {
            case "draft":
                status = ReviewRevisionStatus.Draft;
                return true;
            case "reviewed":
                status = ReviewRevisionStatus.Reviewed;
                return true;
            default:
                status = default;
                return false;
        }
    }
}

public enum ReviewFieldDecision
{
    Unreviewed,
    Accepted,
    Edited,
    Unknown,
}

public static class ReviewFieldDecisionNames
{
    public static string ToWire(this ReviewFieldDecision decision) => decision switch
    {
        ReviewFieldDecision.Unreviewed => "unreviewed",
        ReviewFieldDecision.Accepted => "accepted",
        ReviewFieldDecision.Edited => "edited",
        ReviewFieldDecision.Unknown => "unknown",
        _ => throw new ArgumentOutOfRangeException(nameof(decision), decision, null),
    };

    public static ReviewFieldDecision FromWire(string value) => value switch
    {
        "unreviewed" => ReviewFieldDecision.Unreviewed,
        "accepted" => ReviewFieldDecision.Accepted,
        "edited" => ReviewFieldDecision.Edited,
        "unknown" => ReviewFieldDecision.Unknown,
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, "Unrecognized review field decision."),
    };

    public static bool TryFromWire(string? value, out ReviewFieldDecision decision)
    {
        switch (value)
        {
            case "unreviewed":
                decision = ReviewFieldDecision.Unreviewed;
                return true;
            case "accepted":
                decision = ReviewFieldDecision.Accepted;
                return true;
            case "edited":
                decision = ReviewFieldDecision.Edited;
                return true;
            case "unknown":
                decision = ReviewFieldDecision.Unknown;
                return true;
            default:
                decision = default;
                return false;
        }
    }
}

public enum MachineCandidateStatus
{
    Suggested,
    Missing,
    Ambiguous,
    Oversized,
    InvalidText,
}

public static class MachineCandidateStatusNames
{
    public static string ToWire(this MachineCandidateStatus status) => status switch
    {
        MachineCandidateStatus.Suggested => "suggested",
        MachineCandidateStatus.Missing => "missing",
        MachineCandidateStatus.Ambiguous => "ambiguous",
        MachineCandidateStatus.Oversized => "oversized",
        MachineCandidateStatus.InvalidText => "invalid_text",
        _ => throw new ArgumentOutOfRangeException(nameof(status), status, null),
    };

    public static MachineCandidateStatus FromWire(string value) => value switch
    {
        "suggested" => MachineCandidateStatus.Suggested,
        "missing" => MachineCandidateStatus.Missing,
        "ambiguous" => MachineCandidateStatus.Ambiguous,
        "oversized" => MachineCandidateStatus.Oversized,
        "invalid_text" => MachineCandidateStatus.InvalidText,
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, "Unrecognized machine candidate status."),
    };
}
