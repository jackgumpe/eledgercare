using System.Globalization;
using ELedgerCare.Application.Intake;
using ELedgerCare.Domain.Processing;

namespace ELedgerCare.Api;

/// <summary>Receipt returned only for committed rows.</summary>
public sealed record SubmissionReceiptResponse(
    Guid DocumentId,
    Guid JobId,
    string Status,
    DateTimeOffset SubmittedAtUtc,
    int ByteLength,
    string Sha256,
    string OriginalUrl)
{
    public static SubmissionReceiptResponse From(CommittedSubmission submission) => new(
        submission.DocumentId,
        submission.JobId,
        submission.Status.ToWire(),
        submission.SubmittedAtUtc.ToUniversalTime(),
        submission.ByteLength,
        Convert.ToHexStringLower(submission.Sha256),
        string.Create(CultureInfo.InvariantCulture, $"/api/documents/{submission.DocumentId:D}/original"));
}
