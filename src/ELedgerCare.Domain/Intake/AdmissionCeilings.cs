namespace ELedgerCare.Domain.Intake;

/// <summary>
/// Hard ceilings fixed by the accepted F1 design. Configuration may lower them, never raise them.
/// The persistence schema enforces the same ceilings with check constraints.
/// </summary>
public static class AdmissionCeilings
{
    public const int MaxDocumentBytes = 10_485_760;
    public const int MaxPages = 50;
}
