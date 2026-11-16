namespace ELedgerCare.Domain.Processing;

/// <summary>
/// Hard contract ceilings, schema identifiers, and model pins for F2 local extraction.
/// </summary>
public static class ExtractionCeilings
{
    public const int MaxExtractionPages = 3;
    public const int MaxRawOutputBytes = 16_777_216;
    public const int MaxLogBytes = 67_108_864;
    public const long MinFreeDiskBytes = 21_474_836_480L;
    public const long MaxRuntimeRootBytes = 4_294_967_296L;

    public const int LoadTimeoutSeconds = 1800;
    public const int OnePageCallTimeoutSeconds = 1800;
    public const int TwoPageCallTimeoutSeconds = 2700;
    public const int ThreePageCallTimeoutSeconds = 3600;
    public const int StallTimeoutSeconds = 300;
    public const int HeartbeatIntervalSeconds = 5;

    public const string EnvelopeSchema = "eledgercare.local-extraction/1";
    public const string RequestSchema = "eledgercare.local-extraction-request/1";
    public const string WorkerId = "eledgercare.local-ocr-worker/1";
    public const string ModelRepoId = "baidu/Unlimited-OCR-2";
    public const string ModelRevision = "0480966938291445591f69f08a13b041c073a96a";
    public const string RequiredProvenanceException = "torchvision-local-sha256-TOFU";
    public const string ReviewStatusUnreviewed = "unreviewed";
    public const string StopFinishReason = "stop";
    public const string PageMarker = "<PAGE>";

    public static int CallTimeoutSecondsForPages(int pageCount) => pageCount switch
    {
        1 => OnePageCallTimeoutSeconds,
        2 => TwoPageCallTimeoutSeconds,
        3 => ThreePageCallTimeoutSeconds,
        _ => throw new ArgumentOutOfRangeException(nameof(pageCount), pageCount,
            $"Extraction page count must be within 1..{MaxExtractionPages}."),
    };
}
