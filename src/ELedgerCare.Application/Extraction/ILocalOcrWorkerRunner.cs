namespace ELedgerCare.Application.Extraction;

public readonly record struct OsProcessIdentity(int Pid, long CreateFileTime);

public interface IProcessIdentityProbe
{
    OsProcessIdentity GetCurrentProcessIdentity();

    bool IsProcessAlive(int pid, long expectedCreateFileTime);
}

public interface ILocalOcrWorkerRunner
{
    /// <summary>
    /// Inspects any worker heartbeat left in the owned run directory of an interrupted attempt
    /// so startup recovery can verify actual worker exit even if the supervisor died before a DB heartbeat.
    /// </summary>
    OsProcessIdentity? TryReadRecordedWorkerIdentity(string runDirectoryName);

    Task<WorkerRunOutcome> ExecuteAttemptAsync(
        ClaimedAttemptWork work,
        Func<int, long, CancellationToken, Task<bool>> onLauncherAssignedBeforeResumeAsync,
        Func<string, int?, long?, CancellationToken, Task<bool>> onHeartbeatAsync,
        CancellationToken cancellationToken);
}

public sealed record WorkerRunOutcome(
    byte[]? EnvelopeJsonBytes,
    byte[]? RawOutputBytes,
    int? ExitCode,
    string? SupervisorFailureCode,
    string? SupervisorFailureDetail);
