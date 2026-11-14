using System.Security.Cryptography;
using ELedgerCare.Domain.Intake;

namespace ELedgerCare.Domain.Documents;

/// <summary>
/// The immutable submitted PDF. Bytes, digest and length have no update path once created.
/// </summary>
public sealed class OriginalArtifact
{
    public const string PdfMediaType = "application/pdf";
    public const int Sha256Length = 32;

    private OriginalArtifact()
    {
        // Materialization constructor for the persistence mapping.
        Bytes = [];
        Sha256 = [];
        MediaType = PdfMediaType;
    }

    private OriginalArtifact(Guid documentId, byte[] bytes, int pageCount)
    {
        if (bytes.Length is < 1 or > AdmissionCeilings.MaxDocumentBytes)
        {
            throw new ArgumentOutOfRangeException(nameof(bytes), bytes.Length,
                $"An original must contain 1..{AdmissionCeilings.MaxDocumentBytes} bytes.");
        }

        if (pageCount is < 1 or > AdmissionCeilings.MaxPages)
        {
            throw new ArgumentOutOfRangeException(nameof(pageCount), pageCount,
                $"An admitted original must have 1..{AdmissionCeilings.MaxPages} pages.");
        }

        DocumentId = documentId;
        Bytes = bytes;
        Sha256 = SHA256.HashData(bytes);
        ByteLength = bytes.Length;
        MediaType = PdfMediaType;
        PageCount = pageCount;
    }

    public Guid DocumentId { get; private init; }

    public byte[] Bytes { get; private init; }

    public byte[] Sha256 { get; private init; }

    public int ByteLength { get; private init; }

    public string MediaType { get; private init; }

    /// <summary>Admitted page count; internal to F1 and not part of the receipt.</summary>
    public int PageCount { get; private init; }

    internal static OriginalArtifact Create(Guid documentId, byte[] bytes, int pageCount)
        => new(documentId, bytes, pageCount);
}
