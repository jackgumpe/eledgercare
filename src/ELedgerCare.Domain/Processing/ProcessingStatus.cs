namespace ELedgerCare.Domain.Processing;

/// <summary>
/// Durable requested-work status. F1 knows only the honest initial state: no extraction
/// has run. Future states are added by the features that actually perform them.
/// </summary>
public enum ProcessingStatus
{
    AwaitingExtraction,
}

public static class ProcessingStatusNames
{
    public const string AwaitingExtraction = "awaiting_extraction";

    public static string ToWire(this ProcessingStatus status) => status switch
    {
        ProcessingStatus.AwaitingExtraction => AwaitingExtraction,
        _ => throw new ArgumentOutOfRangeException(nameof(status), status, "Unknown processing status."),
    };

    public static ProcessingStatus FromWire(string value) => value switch
    {
        AwaitingExtraction => ProcessingStatus.AwaitingExtraction,
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, "Unknown processing status."),
    };
}
