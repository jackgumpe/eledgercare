namespace ELedgerCare.Api;

/// <summary>Bound from the "Intake" configuration section; converted to validated IntakeLimits at startup.</summary>
public sealed class IntakeOptions
{
    public const string Section = "Intake";

    /// <summary>Concurrent POST admission slots with no waiting queue (accepted design: two).</summary>
    public const int AdmissionSlots = 2;

    public int MaxDocumentBytes { get; set; } = Domain.Intake.AdmissionCeilings.MaxDocumentBytes;

    public int MaxPages { get; set; } = Domain.Intake.AdmissionCeilings.MaxPages;
}
