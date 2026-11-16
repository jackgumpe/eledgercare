namespace ELedgerCare.Application.Extraction;

/// <summary>
/// Coordinates abandoned-attempt recovery, atomic queue claims, child worker supervision,
/// envelope validation, and fenced result/failure publication without holding long DB transactions.
/// </summary>
public sealed class ExtractionAttemptCoordinator(
    IExtractionStore store,
    ILocalOcrWorkerRunner workerRunner,
    IProcessIdentityProbe processProbe,
    ExtractionSettings settings,
    TimeProvider clock)
{
    private readonly Guid supervisorInstanceId = Guid.NewGuid();
    private readonly OsProcessIdentity supervisorIdentity = processProbe.GetCurrentProcessIdentity();
    private readonly object activeAttemptLock = new();
    private int activeExecutionGate;
    private Guid? activeAttemptId;

    public Guid SupervisorInstanceId => supervisorInstanceId;

    public OsProcessIdentity SupervisorIdentity => supervisorIdentity;

    /// <summary>
    /// Marks abandoned running attempts as interrupted ONLY after confirming that:
    ///   - for another supervisor instance, its supervisor OS process (PID, CreationTime) is no longer alive;
    ///   - for this supervisor instance, no in-flight claim/execution is active on that attempt; and
    ///   - the launcher and actual worker child processes (both DB-recorded and run-directory heartbeat) are gone.
    /// Never steals work from a genuinely live attempt, and never auto-launches a retry.
    /// </summary>
    public async Task<int> ReconcileAbandonedAttemptsAsync(CancellationToken cancellationToken)
    {
        var running = await store.GetRunningAttemptsAsync(cancellationToken);
        var reconciled = 0;

        foreach (var attempt in running)
        {
            if (attempt.SupervisorInstanceId == supervisorInstanceId)
            {
                // F2-S1-02: Protect any actively executing attempt in this coordinator, while allowing
                // same-process recovery of an orphaned 'running' row once execution has exited.
                if (Volatile.Read(ref activeExecutionGate) != 0 || GetActiveAttemptId() == attempt.AttemptId)
                {
                    continue;
                }
            }
            else if (processProbe.IsProcessAlive(attempt.SupervisorPid, attempt.SupervisorCreateFileTime))
            {
                // Never reclaim work owned by another live supervisor instance.
                continue;
            }

            // Confirm launcher and actual worker child processes are completely gone before marking interrupted.
            if (attempt.LauncherPid is { } lPid && attempt.LauncherCreateFileTime is { } lFt &&
                processProbe.IsProcessAlive(lPid, lFt))
            {
                continue;
            }

            if (attempt.WorkerPid is { } wPid && attempt.WorkerCreateFileTime is { } wFt &&
                processProbe.IsProcessAlive(wPid, wFt))
            {
                continue;
            }

            if (workerRunner.TryReadRecordedWorkerIdentity(attempt.RunDirectoryName) is { } hbWorker &&
                processProbe.IsProcessAlive(hbWorker.Pid, hbWorker.CreateFileTime))
            {
                continue;
            }

            var now = TruncateToMicroseconds(clock.GetUtcNow());
            var updated = await store.MarkAttemptInterruptedAsync(
                attempt.AttemptId,
                attempt.JobId,
                attempt.FencingToken,
                "supervisor_interrupted",
                "The previous extraction attempt was interrupted before completion. You can explicitly retry extraction.",
                now,
                cancellationToken);
            if (updated)
            {
                reconciled++;
            }
        }

        return reconciled;
    }

    public async Task<bool> ExecuteNextQueuedAttemptAsync(CancellationToken cancellationToken)
    {
        if (!settings.Enabled)
        {
            return false;
        }

        if (Interlocked.CompareExchange(ref activeExecutionGate, 1, 0) != 0)
        {
            return false;
        }

        try
        {
            var claimTime = TruncateToMicroseconds(clock.GetUtcNow());
            var claimed = await store.ClaimNextQueuedJobAsync(
                supervisorInstanceId,
                supervisorIdentity.Pid,
                supervisorIdentity.CreateFileTime,
                claimTime,
                cancellationToken);
            if (claimed is null)
            {
                return false;
            }

            SetActiveAttemptId(claimed.AttemptId);

            WorkerRunOutcome runOutcome;
            try
            {
                runOutcome = await workerRunner.ExecuteAttemptAsync(
                    claimed,
                    async (launcherPid, launcherFt, ct) =>
                    {
                        var now = TruncateToMicroseconds(clock.GetUtcNow());
                        return await store.RecordLauncherProcessAsync(
                            claimed.AttemptId, claimed.FencingToken, launcherPid, launcherFt, now, ct);
                    },
                    async (phase, workerPid, workerFt, ct) =>
                    {
                        var now = TruncateToMicroseconds(clock.GetUtcNow());
                        return await store.RecordHeartbeatAsync(
                            claimed.AttemptId, claimed.FencingToken, phase, workerPid, workerFt, now, ct);
                    },
                    cancellationToken);
            }
            catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
            {
                // Supervisor host is stopping; Job Object guarantees child cleanup. Record interrupted if DB is reachable.
                var stopTime = TruncateToMicroseconds(clock.GetUtcNow());
                await store.MarkAttemptInterruptedAsync(
                    claimed.AttemptId,
                    claimed.JobId,
                    claimed.FencingToken,
                    "supervisor_stopping",
                    "Local extraction was interrupted while the application service was stopping. Explicitly retry extraction when ready.",
                    stopTime,
                    CancellationToken.None);
                throw;
            }
            catch (Exception)
            {
                var errTime = TruncateToMicroseconds(clock.GetUtcNow());
                await store.MarkAttemptFailedAsync(
                    claimed.AttemptId,
                    claimed.JobId,
                    claimed.FencingToken,
                    "supervisor_launch_failed",
                    "The local OCR worker could not be started or supervised safely.",
                    null,
                    null,
                    null,
                    errTime,
                    CancellationToken.None);
                return true;
            }

            var endTime = TruncateToMicroseconds(clock.GetUtcNow());
            var validation = WorkerEnvelopeValidator.Validate(claimed, settings, runOutcome, endTime);
            switch (validation)
            {
                case EnvelopeValidationOutcome.Accepted accepted:
                    await store.PublishCompletedResultAsync(accepted.Result, runOutcome.ExitCode ?? 0, endTime, CancellationToken.None);
                    break;

                case EnvelopeValidationOutcome.Rejected rejected:
                    await store.MarkAttemptFailedAsync(
                        claimed.AttemptId,
                        claimed.JobId,
                        claimed.FencingToken,
                        rejected.FailureCode,
                        rejected.SafeDetail,
                        runOutcome.ExitCode,
                        rejected.DiagnosticRawOutputUtf8,
                        rejected.DiagnosticMetadataJson,
                        endTime,
                        CancellationToken.None);
                    break;
            }

            return true;
        }
        finally
        {
            SetActiveAttemptId(null);
            Interlocked.Exchange(ref activeExecutionGate, 0);
        }
    }

    public static DateTimeOffset TruncateToMicroseconds(DateTimeOffset value) =>
        new(value.UtcTicks - (value.UtcTicks % 10), TimeSpan.Zero);

    private Guid? GetActiveAttemptId()
    {
        lock (activeAttemptLock)
        {
            return activeAttemptId;
        }
    }

    private void SetActiveAttemptId(Guid? attemptId)
    {
        lock (activeAttemptLock)
        {
            activeAttemptId = attemptId;
        }
    }
}
