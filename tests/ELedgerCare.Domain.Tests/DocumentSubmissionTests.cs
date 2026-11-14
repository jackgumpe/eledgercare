using System.Security.Cryptography;
using ELedgerCare.Domain.Documents;
using ELedgerCare.Domain.Intake;
using ELedgerCare.Domain.Processing;
using Xunit;

namespace ELedgerCare.Domain.Tests;

public sealed class DocumentSubmissionTests
{
    private static readonly DateTimeOffset Now = new(2026, 11, 14, 17, 0, 0, TimeSpan.Zero);

    [Fact]
    public void Submission_creates_one_unit_awaiting_extraction_with_content_identity()
    {
        byte[] bytes = [1, 2, 3, 4];
        var documentId = Guid.NewGuid();
        var jobId = Guid.NewGuid();
        var key = Guid.NewGuid();

        var document = Document.Submit(documentId, jobId, key, bytes, admittedPageCount: 2, Now);

        Assert.Equal(documentId, document.DocumentId);
        Assert.Equal(key, document.IdempotencyKey);
        Assert.Equal(documentId, document.Original.DocumentId);
        Assert.Equal(documentId, document.Job.DocumentId);
        Assert.Equal(jobId, document.Job.JobId);
        Assert.Equal(ProcessingStatus.AwaitingExtraction, document.Job.Status);
        Assert.Equal("awaiting_extraction", document.Job.Status.ToWire());
        Assert.Equal(4, document.Original.ByteLength);
        Assert.Equal(SHA256.HashData(bytes), document.Original.Sha256);
        Assert.Equal("application/pdf", document.Original.MediaType);
        Assert.Equal(2, document.Original.PageCount);
        Assert.Equal(Now, document.Job.RequestedAtUtc);
    }

    [Fact]
    public void Identical_bytes_under_distinct_keys_are_distinct_documents()
    {
        byte[] bytes = [9, 9, 9];

        var first = Document.Submit(Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), bytes, 1, Now);
        var second = Document.Submit(Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), bytes, 1, Now);

        Assert.NotEqual(first.DocumentId, second.DocumentId);
        Assert.Equal(first.Original.Sha256, second.Original.Sha256);
    }

    [Fact]
    public void Empty_or_oversized_originals_cannot_be_created()
    {
        Assert.Throws<ArgumentOutOfRangeException>(() =>
            Document.Submit(Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), [], 1, Now));
        Assert.Throws<ArgumentOutOfRangeException>(() =>
            Document.Submit(Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), new byte[AdmissionCeilings.MaxDocumentBytes + 1], 1, Now));
    }

    [Theory]
    [InlineData(0)]
    [InlineData(51)]
    public void Page_count_outside_the_ceiling_cannot_be_admitted(int pages)
    {
        Assert.Throws<ArgumentOutOfRangeException>(() =>
            Document.Submit(Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), [1], pages, Now));
    }

    [Fact]
    public void Empty_identifiers_and_non_utc_times_are_refused()
    {
        Assert.Throws<ArgumentException>(() => Document.Submit(Guid.Empty, Guid.NewGuid(), Guid.NewGuid(), [1], 1, Now));
        Assert.Throws<ArgumentException>(() => Document.Submit(Guid.NewGuid(), Guid.Empty, Guid.NewGuid(), [1], 1, Now));
        Assert.Throws<ArgumentException>(() => Document.Submit(Guid.NewGuid(), Guid.NewGuid(), Guid.Empty, [1], 1, Now));
        Assert.Throws<ArgumentException>(() =>
            Document.Submit(Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), [1], 1, Now.ToOffset(TimeSpan.FromHours(-5))));
    }

    [Fact]
    public void Unknown_wire_status_is_not_silently_mapped()
    {
        Assert.Equal(ProcessingStatus.AwaitingExtraction, ProcessingStatusNames.FromWire("awaiting_extraction"));
        Assert.Throws<ArgumentOutOfRangeException>(() => ProcessingStatusNames.FromWire("extracted"));
    }
}
