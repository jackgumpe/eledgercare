using ELedgerCare.Domain.Intake;

namespace ELedgerCare.Application.Intake;

/// <summary>
/// Effective admission limits. Values may be configured downward from the accepted ceilings only.
/// </summary>
public sealed record IntakeLimits
{
    public IntakeLimits(int maxDocumentBytes, int maxPages)
    {
        if (maxDocumentBytes is < 1 or > AdmissionCeilings.MaxDocumentBytes)
        {
            throw new ArgumentOutOfRangeException(nameof(maxDocumentBytes), maxDocumentBytes,
                $"MaxDocumentBytes must be within 1..{AdmissionCeilings.MaxDocumentBytes}.");
        }

        if (maxPages is < 1 or > AdmissionCeilings.MaxPages)
        {
            throw new ArgumentOutOfRangeException(nameof(maxPages), maxPages,
                $"MaxPages must be within 1..{AdmissionCeilings.MaxPages}.");
        }

        MaxDocumentBytes = maxDocumentBytes;
        MaxPages = maxPages;
    }

    public int MaxDocumentBytes { get; }

    public int MaxPages { get; }
}
