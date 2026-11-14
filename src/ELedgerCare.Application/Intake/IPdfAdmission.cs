namespace ELedgerCare.Application.Intake;

/// <summary>
/// Restricted developer-fixture PDF admission profile (accepted design step 4). Implementations
/// must never read, return or persist page text, run OCR, render pages or fetch network resources.
/// </summary>
public interface IPdfAdmission
{
    PdfAdmissionResult Evaluate(ReadOnlyMemory<byte> bytes, int maxPages);
}

public enum PdfRejectionReason
{
    UnsupportedHeader,
    MissingEofMarker,
    InvalidCrossReference,
    Encrypted,
    PageCountOutOfRange,
    Unreadable,
}

public sealed record PdfAdmissionResult
{
    private PdfAdmissionResult(int? pageCount, PdfRejectionReason? rejection)
    {
        PageCount = pageCount;
        Rejection = rejection;
    }

    public int? PageCount { get; }

    public PdfRejectionReason? Rejection { get; }

    public bool IsAdmitted => Rejection is null;

    public static PdfAdmissionResult Admitted(int pageCount) => new(pageCount, null);

    public static PdfAdmissionResult Rejected(PdfRejectionReason reason) => new(null, reason);
}
