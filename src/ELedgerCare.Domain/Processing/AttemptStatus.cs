namespace ELedgerCare.Domain.Processing;

/// <summary>
/// Durable lifecycle status of one individual local OCR execution attempt.
/// </summary>
public enum AttemptStatus
{
    Running,
    Completed,
    Failed,
    Interrupted,
}

public static class AttemptStatusNames
{
    public const string Running = "running";
    public const string Completed = "completed";
    public const string Failed = "failed";
    public const string Interrupted = "interrupted";

    public static string ToWire(this AttemptStatus status) => status switch
    {
        AttemptStatus.Running => Running,
        AttemptStatus.Completed => Completed,
        AttemptStatus.Failed => Failed,
        AttemptStatus.Interrupted => Interrupted,
        _ => throw new ArgumentOutOfRangeException(nameof(status), status, "Unknown attempt status."),
    };

    public static AttemptStatus FromWire(string value) => value switch
    {
        Running => AttemptStatus.Running,
        Completed => AttemptStatus.Completed,
        Failed => AttemptStatus.Failed,
        Interrupted => AttemptStatus.Interrupted,
        _ => throw new ArgumentOutOfRangeException(nameof(value), value, "Unknown attempt status."),
    };
}
