namespace ELedgerCare.Domain.Processing;

/// <summary>
/// One durable execution attempt of the local OCR worker with monotonic fencing and OS process identity tracking.
/// </summary>
public sealed class ExecutionAttempt
{
    public const int MaxFailureDetailLength = 500;
    public const int MaxDiagnosticOutputChars = 65_536;

    private ExecutionAttempt()
    {
        // Materialization constructor for EF Core.
        Phase = string.Empty;
        RunDirectoryName = string.Empty;
    }

    private ExecutionAttempt(
        Guid attemptId,
        Guid jobId,
        Guid documentId,
        int attemptNumber,
        long fencingToken,
        Guid? retriedFromAttemptId,
        string runDirectoryName,
        Guid supervisorInstanceId,
        int supervisorPid,
        long supervisorCreateFileTime,
        DateTimeOffset startedAtUtc)
    {
        AttemptId = attemptId;
        JobId = jobId;
        DocumentId = documentId;
        AttemptNumber = attemptNumber;
        FencingToken = fencingToken;
        RetriedFromAttemptId = retriedFromAttemptId;
        Status = AttemptStatus.Running;
        Phase = "claiming";
        RunDirectoryName = runDirectoryName;
        SupervisorInstanceId = supervisorInstanceId;
        SupervisorPid = supervisorPid;
        SupervisorCreateFileTime = supervisorCreateFileTime;
        StartedAtUtc = startedAtUtc;
        LastHeartbeatAtUtc = startedAtUtc;
    }

    public Guid AttemptId { get; private init; }

    public Guid JobId { get; private init; }

    public Guid DocumentId { get; private init; }

    public int AttemptNumber { get; private init; }

    public long FencingToken { get; private init; }

    public Guid? RetriedFromAttemptId { get; private init; }

    public AttemptStatus Status { get; private set; }

    public string Phase { get; private set; }

    public string RunDirectoryName { get; private init; }

    public Guid SupervisorInstanceId { get; private init; }

    public int SupervisorPid { get; private init; }

    public long SupervisorCreateFileTime { get; private init; }

    public int? LauncherPid { get; private set; }

    public long? LauncherCreateFileTime { get; private set; }

    public int? WorkerPid { get; private set; }

    public long? WorkerCreateFileTime { get; private set; }

    public DateTimeOffset StartedAtUtc { get; private init; }

    public DateTimeOffset LastHeartbeatAtUtc { get; private set; }

    public DateTimeOffset? EndedAtUtc { get; private set; }

    public int? ExitCode { get; private set; }

    public string? FailureCode { get; private set; }

    public string? FailureDetail { get; private set; }

    /// <summary>Bounded diagnostic raw text retained only for failed/truncated attempts, never accepted as a result.</summary>
    public string? DiagnosticRawOutputUtf8 { get; private set; }

    public string? DiagnosticMetadataJson { get; private set; }

    public static ExecutionAttempt Start(
        Guid attemptId,
        Guid jobId,
        Guid documentId,
        int attemptNumber,
        long fencingToken,
        Guid? retriedFromAttemptId,
        string runDirectoryName,
        Guid supervisorInstanceId,
        int supervisorPid,
        long supervisorCreateFileTime,
        DateTimeOffset startedAtUtc)
    {
        RequireNonEmpty(attemptId, nameof(attemptId));
        RequireNonEmpty(jobId, nameof(jobId));
        RequireNonEmpty(documentId, nameof(documentId));
        RequireNonEmpty(supervisorInstanceId, nameof(supervisorInstanceId));
        ArgumentException.ThrowIfNullOrWhiteSpace(runDirectoryName);
        if (attemptNumber < 1)
        {
            throw new ArgumentOutOfRangeException(nameof(attemptNumber), attemptNumber, "AttemptNumber must be >= 1.");
        }

        if (fencingToken < 1)
        {
            throw new ArgumentOutOfRangeException(nameof(fencingToken), fencingToken, "FencingToken must be >= 1.");
        }

        if (supervisorPid <= 0 || supervisorCreateFileTime <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(supervisorPid), "Supervisor OS process identity must be positive.");
        }

        if (startedAtUtc.Offset != TimeSpan.Zero)
        {
            throw new ArgumentException("Start time must be UTC.", nameof(startedAtUtc));
        }

        return new ExecutionAttempt(
            attemptId,
            jobId,
            documentId,
            attemptNumber,
            fencingToken,
            retriedFromAttemptId,
            runDirectoryName,
            supervisorInstanceId,
            supervisorPid,
            supervisorCreateFileTime,
            startedAtUtc);
    }

    public void RecordLauncherProcess(int launcherPid, long launcherCreateFileTime, DateTimeOffset heartbeatUtc)
    {
        EnsureRunning();
        if (launcherPid <= 0 || launcherCreateFileTime <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(launcherPid), "Launcher OS process identity must be positive.");
        }

        LauncherPid = launcherPid;
        LauncherCreateFileTime = launcherCreateFileTime;
        Phase = "starting";
        LastHeartbeatAtUtc = heartbeatUtc;
    }

    public void RecordHeartbeat(string phase, int? workerPid, long? workerCreateFileTime, DateTimeOffset heartbeatUtc)
    {
        EnsureRunning();
        ArgumentException.ThrowIfNullOrWhiteSpace(phase);
        Phase = phase;
        if (workerPid is > 0 && workerCreateFileTime is > 0)
        {
            WorkerPid = workerPid;
            WorkerCreateFileTime = workerCreateFileTime;
        }

        LastHeartbeatAtUtc = heartbeatUtc;
    }

    public void MarkCompleted(DateTimeOffset endedAtUtc, int exitCode)
    {
        EnsureRunning();
        Status = AttemptStatus.Completed;
        Phase = AttemptStatusNames.Completed;
        EndedAtUtc = endedAtUtc;
        LastHeartbeatAtUtc = endedAtUtc;
        ExitCode = exitCode;
    }

    public void MarkFailed(
        string failureCode,
        string failureDetail,
        DateTimeOffset endedAtUtc,
        int? exitCode = null,
        string? diagnosticRawOutputUtf8 = null,
        string? diagnosticMetadataJson = null)
    {
        EnsureRunning();
        ArgumentException.ThrowIfNullOrWhiteSpace(failureCode);
        ArgumentException.ThrowIfNullOrWhiteSpace(failureDetail);
        Status = AttemptStatus.Failed;
        Phase = AttemptStatusNames.Failed;
        FailureCode = failureCode;
        FailureDetail = Truncate(failureDetail, MaxFailureDetailLength);
        EndedAtUtc = endedAtUtc;
        LastHeartbeatAtUtc = endedAtUtc;
        ExitCode = exitCode;
        DiagnosticRawOutputUtf8 = diagnosticRawOutputUtf8 is null ? null : Truncate(diagnosticRawOutputUtf8, MaxDiagnosticOutputChars);
        DiagnosticMetadataJson = diagnosticMetadataJson;
    }

    public void MarkInterrupted(
        string failureCode,
        string failureDetail,
        DateTimeOffset endedAtUtc,
        string? diagnosticMetadataJson = null)
    {
        EnsureRunning();
        ArgumentException.ThrowIfNullOrWhiteSpace(failureCode);
        ArgumentException.ThrowIfNullOrWhiteSpace(failureDetail);
        Status = AttemptStatus.Interrupted;
        Phase = AttemptStatusNames.Interrupted;
        FailureCode = failureCode;
        FailureDetail = Truncate(failureDetail, MaxFailureDetailLength);
        EndedAtUtc = endedAtUtc;
        LastHeartbeatAtUtc = endedAtUtc;
        DiagnosticMetadataJson = diagnosticMetadataJson;
    }

    private void EnsureRunning()
    {
        if (Status != AttemptStatus.Running)
        {
            throw new InvalidOperationException($"Attempt {AttemptId} is already in terminal state {Status}.");
        }
    }

    private static string Truncate(string value, int maxLength) =>
        value.Length <= maxLength ? value : value[..maxLength];

    private static void RequireNonEmpty(Guid value, string name)
    {
        if (value == Guid.Empty)
        {
            throw new ArgumentException("Identifier must be a non-empty UUID.", name);
        }
    }
}
