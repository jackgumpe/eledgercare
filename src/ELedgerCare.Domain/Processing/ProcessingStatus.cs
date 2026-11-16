namespace ELedgerCare.Domain.Processing;

/// <summary>
/// Durable requested-work status across intake (F1) and local extraction (F2).
/// </summary>
public enum ProcessingStatus
{
    AwaitingExtraction,
    Queued,
    Running,
    Completed,
    Failed,
    Interrupted,
}

public static class ProcessingStatusNames
{
    public const string AwaitingExtraction = "awaiting_extraction";
    public const string Queued = "queued";
    public const string Running = "running";
    public const string Completed = "completed";
    public const string Failed = "failed";
    public const string Interrupted = "interrupted";

    public static string ToWire(this ProcessingStatus status) => status switch
    {
        ProcessingStatus.AwaitingExtraction => AwaitingExtraction,
        ProcessingStatus.Queued => Queued,
        ProcessingStatus.Running => Running,
        ProcessingStatus.Completed => Completed,
        ProcessingStatus.Failed => Failed,
        ProcessingStatus.Interrupted => Interrupted,
        _ => throw new ArgumentOutOfRangeException(nameof(status), status, "Unknown processing status."),
    };

    public static ProcessingStatus FromWire(string value) => value switch
    {
        AwaitingExtraction => ProcessingStatus.AwaitingExtraction,
        Queued => ProcessingStatus.Queued,
        Running => ProcessingStatus.Running,
        Completed => ProcessingStatus.Completed,
        Failed => ProcessingStatus.Failed,
        Interrupted => ProcessingStatus.Interrupted,
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, "Unknown processing status."),
    };
}
