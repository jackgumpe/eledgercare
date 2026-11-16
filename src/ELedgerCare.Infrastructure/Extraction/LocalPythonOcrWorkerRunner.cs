using System.Diagnostics;
using System.Text;
using System.Text.Json;
using ELedgerCare.Application.Extraction;
using ELedgerCare.Domain.Processing;

namespace ELedgerCare.Infrastructure.Extraction;

/// <summary>
/// Production local OCR child supervisor. Materializes committed PDF bytes into the attempt's owned
/// run directory, launches workers/local_ocr/run_worker.py inside a race-free Windows Job Object,
/// enforces phase/stall/log/storage guards, and returns the raw output + versioned envelope.
/// </summary>
public sealed class LocalPythonOcrWorkerRunner(ExtractionSettings settings) : ILocalOcrWorkerRunner
{
    private static readonly string[] SafeSystemPassthroughVars =
    [
        "SystemRoot", "SYSTEMROOT", "windir", "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE",
        "PROCESSOR_IDENTIFIER", "PROCESSOR_LEVEL", "PROCESSOR_REVISION", "OS", "PATHEXT", "ComSpec",
    ];

    public OsProcessIdentity? TryReadRecordedWorkerIdentity(string runDirectoryName)
    {
        if (string.IsNullOrWhiteSpace(settings.WritableRuntimeRoot) ||
            string.IsNullOrWhiteSpace(runDirectoryName) ||
            runDirectoryName.IndexOfAny(['/', '\\', ':']) >= 0 ||
            runDirectoryName.Contains("..", StringComparison.Ordinal))
        {
            return null;
        }

        var heartbeatPath = Path.Combine(settings.WritableRuntimeRoot, "runs", runDirectoryName, "output", "heartbeat.json");
        var hb = TryReadHeartbeatFile(heartbeatPath);
        return hb is { WorkerPid: > 0, WorkerCreateFileTime: > 0 }
            ? new OsProcessIdentity(hb.Value.WorkerPid, hb.Value.WorkerCreateFileTime)
            : null;
    }

    public async Task<WorkerRunOutcome> ExecuteAttemptAsync(
        ClaimedAttemptWork work,
        Func<int, long, CancellationToken, Task<bool>> onLauncherAssignedBeforeResumeAsync,
        Func<string, int?, long?, CancellationToken, Task<bool>> onHeartbeatAsync,
        CancellationToken cancellationToken)
    {
        if (!settings.Enabled ||
            string.IsNullOrWhiteSpace(settings.ReadOnlyQ0Root) ||
            string.IsNullOrWhiteSpace(settings.WritableRuntimeRoot) ||
            string.IsNullOrWhiteSpace(settings.LeasedGpuUuid))
        {
            return new WorkerRunOutcome(null, null, null, "extraction_disabled",
                "Local OCR execution is disabled until a coordinator runtime release is configured.");
        }

        var q0Root = Path.GetFullPath(settings.ReadOnlyQ0Root);
        var writableRoot = Path.GetFullPath(settings.WritableRuntimeRoot);
        if (!Directory.Exists(q0Root) || IsReparsePoint(q0Root))
        {
            return new WorkerRunOutcome(null, null, null, "runtime_root_invalid",
                "Configured read-only Q0 runtime root is absent or a reparse point.");
        }

        if (!Directory.Exists(writableRoot) || IsReparsePoint(writableRoot))
        {
            return new WorkerRunOutcome(null, null, null, "runtime_root_invalid",
                "Configured writable F2 runtime root is absent or a reparse point.");
        }

        if (!CheckStorageBounds(writableRoot, out var preStorageFailure))
        {
            return new WorkerRunOutcome(null, null, null, "storage_limit_exceeded", preStorageFailure);
        }

        var venvPython = Path.Combine(q0Root, "venv", "Scripts", "python.exe");
        var modelDir = Path.Combine(q0Root, "models", "Unlimited_OCR_2_04809669");
        var noticeDir = Path.Combine(q0Root, "notices", "Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a");
        var workerScript = Path.Combine(settings.WorkerRootPath, "run_worker.py");

        if (work.RunDirectoryName.IndexOfAny(['/', '\\', ':']) >= 0 || work.RunDirectoryName.Contains("..", StringComparison.Ordinal))
        {
            return new WorkerRunOutcome(null, null, null, "invalid_run_directory", "Unsafe run directory name.");
        }

        var runDir = Path.Combine(writableRoot, "runs", work.RunDirectoryName);
        if (Directory.Exists(runDir))
        {
            return new WorkerRunOutcome(null, null, null, "duplicate_run_directory",
                "Attempt run directory already exists; refusing to reuse mutable state.");
        }

        var inputDir = Path.Combine(runDir, "input");
        var outputDir = Path.Combine(runDir, "output");
        var cacheDir = Path.Combine(runDir, "cache");
        Directory.CreateDirectory(inputDir);
        Directory.CreateDirectory(outputDir);
        Directory.CreateDirectory(cacheDir);

        var inputPdfPath = Path.Combine(inputDir, "document.pdf");
        await using (var pdfStream = new FileStream(inputPdfPath, FileMode.CreateNew, FileAccess.Write, FileShare.None))
        {
            await pdfStream.WriteAsync(work.PdfBytes, cancellationToken);
            await pdfStream.FlushAsync(cancellationToken);
        }

        File.SetAttributes(inputPdfPath, FileAttributes.ReadOnly);

        var callTimeoutSeconds = ExtractionCeilings.CallTimeoutSecondsForPages(work.PageCount);
        var expectedConfigSha = ExtractionSettings.ComputeWorkerConfigSha256(work.PageCount);
        var requestPath = Path.Combine(runDir, "request.json");
        await WriteRequestManifestAsync(requestPath, work, writableRoot, q0Root, inputPdfPath, modelDir, noticeDir,
            callTimeoutSeconds, expectedConfigSha, cancellationToken);

        var childEnv = BuildIsolatedEnvironment(q0Root, cacheDir, settings.LeasedGpuUuid);
        string[] childArgs = ["-I", "-B", "-X", "utf8", "-u", workerScript, "--request", requestPath];

        var stdoutLogPath = Path.Combine(outputDir, "child.stdout.log");
        var stderrLogPath = Path.Combine(outputDir, "child.stderr.log");
        var heartbeatPath = Path.Combine(outputDir, "heartbeat.json");
        var envelopePath = Path.Combine(outputDir, "envelope.json");
        var rawOutputPath = Path.Combine(outputDir, "raw_output.utf8.bin");

        long sharedLogBytes = 0;
        using var jobProcess = WindowsJobProcess.CreateSuspendedAssigned(venvPython, childArgs, runDir, childEnv);
        Stream? stdoutPipe = null;
        Stream? stderrPipe = null;
        Task? stdoutPump = null;
        Task? stderrPump = null;
        string? abortCode = null;
        string? abortDetail = null;
        int? exitCode = null;

        try
        {
            // Persist launcher (PID, CreationTime) BEFORE ResumePrimaryThread so zero startup race exists.
            var stillOwns = await onLauncherAssignedBeforeResumeAsync(
                jobProcess.LauncherIdentity.Pid,
                jobProcess.LauncherIdentity.CreateFileTime,
                cancellationToken);
            if (!stillOwns)
            {
                jobProcess.TerminateAllInJob(1);
                await jobProcess.WaitForAllJobProcessesExitAsync(TimeSpan.FromSeconds(10));
                return new WorkerRunOutcome(null, null, null, "attempt_fenced_out", "Attempt lost ownership before worker start.");
            }

            stdoutPipe = jobProcess.OpenStandardOutputReadStream();
            stderrPipe = jobProcess.OpenStandardErrorReadStream();
            jobProcess.ResumePrimaryThread();

            stdoutPump = PumpBoundedLogAsync(stdoutPipe, stdoutLogPath, bytes => Interlocked.Add(ref sharedLogBytes, bytes));
            stderrPump = PumpBoundedLogAsync(stderrPipe, stderrLogPath, bytes => Interlocked.Add(ref sharedLogBytes, bytes));

            var sw = Stopwatch.StartNew();
            var currentPhase = "starting";
            var phaseStartedAt = sw.Elapsed;
            var phaseTimeoutSeconds = ExtractionCeilings.LoadTimeoutSeconds;
            var lastForwardProgress = 0L;
            var lastProgressAt = sw.Elapsed;
            var sessionCapSeconds = ExtractionCeilings.LoadTimeoutSeconds + callTimeoutSeconds + 300;

            while (true)
            {
                cancellationToken.ThrowIfCancellationRequested();

                var launcherDone = jobProcess.TryGetLauncherExitCode(out var code);
                var activeInJob = jobProcess.QueryActiveJobProcesses();
                if (launcherDone && activeInJob.Count == 0)
                {
                    exitCode = code;
                    break;
                }

                var hb = TryReadHeartbeatFile(heartbeatPath);
                int? observedWorkerPid = hb?.WorkerPid;
                long? observedWorkerFt = hb?.WorkerCreateFileTime;

                // Fallback: if Windows venv spawned a child inside the Job Object before writing heartbeat.json, track it immediately!
                if (observedWorkerPid is null)
                {
                    var descendant = activeInJob.FirstOrDefault(p => p.Pid != jobProcess.LauncherIdentity.Pid);
                    if (descendant.Pid > 0)
                    {
                        observedWorkerPid = descendant.Pid;
                        observedWorkerFt = descendant.CreateFileTime;
                    }
                }

                var nowElapsed = sw.Elapsed;
                if (hb is { } beat)
                {
                    if (!string.Equals(beat.Phase, currentPhase, StringComparison.Ordinal))
                    {
                        currentPhase = beat.Phase;
                        phaseStartedAt = nowElapsed;
                        lastForwardProgress = beat.ForwardProgress;
                        lastProgressAt = nowElapsed;
                    }
                    else if (beat.ForwardProgress != lastForwardProgress)
                    {
                        lastForwardProgress = beat.ForwardProgress;
                        lastProgressAt = nowElapsed;
                    }

                    phaseTimeoutSeconds = beat.PhaseTimeoutSeconds ?? phaseTimeoutSeconds;
                }

                var heartbeatOwned = await onHeartbeatAsync(currentPhase, observedWorkerPid, observedWorkerFt, cancellationToken);
                if (!heartbeatOwned)
                {
                    abortCode = "attempt_fenced_out";
                    abortDetail = "Attempt ownership was superseded by a newer fencing token.";
                }
                else if (nowElapsed.TotalSeconds > sessionCapSeconds || (nowElapsed - phaseStartedAt).TotalSeconds > phaseTimeoutSeconds)
                {
                    abortCode = "worker_timeout";
                    abortDetail = $"Local OCR exceeded the {phaseTimeoutSeconds}s timeout during phase '{currentPhase}'.";
                }
                else if (hb is { StallMonitored: true } && (nowElapsed - lastProgressAt).TotalSeconds > ExtractionCeilings.StallTimeoutSeconds)
                {
                    abortCode = "worker_stalled";
                    abortDetail = $"Local OCR made no forward progress for {ExtractionCeilings.StallTimeoutSeconds}s.";
                }
                else if (Interlocked.Read(ref sharedLogBytes) > ExtractionCeilings.MaxLogBytes)
                {
                    abortCode = "log_cap_exceeded";
                    abortDetail = "Local OCR child log output exceeded the 64 MiB limit.";
                }
                else if (!CheckStorageBounds(writableRoot, out var midStorageFailure))
                {
                    abortCode = "storage_limit_exceeded";
                    abortDetail = midStorageFailure;
                }

                if (abortCode is not null)
                {
                    jobProcess.TerminateAllInJob(1);
                    await jobProcess.WaitForAllJobProcessesExitAsync(TimeSpan.FromSeconds(30));
                    break;
                }

                await Task.Delay(TimeSpan.FromSeconds(1), cancellationToken);
            }
        }
        finally
        {
            // F2-S1-02: Guarantee owned Job Object termination & child exit on EVERY non-normal path
            // BEFORE awaiting stdio pumps, with bounded cleanup that never masks primary exceptions.
            if (exitCode is null)
            {
                jobProcess.TerminateAllInJob(1);
                try
                {
                    await jobProcess.WaitForAllJobProcessesExitAsync(TimeSpan.FromSeconds(10)).ConfigureAwait(false);
                }
                catch
                {
                    // Preserve original exception.
                }
            }

            if (stdoutPump is not null && stderrPump is not null)
            {
                try
                {
                    await Task.WhenAll(stdoutPump, stderrPump).WaitAsync(TimeSpan.FromSeconds(5)).ConfigureAwait(false);
                }
                catch
                {
                    // Disposing pipes below unblocks any lingering reader without masking primary exception.
                }
            }

            stdoutPipe?.Dispose();
            stderrPipe?.Dispose();
        }

        byte[]? envelopeBytes = null;
        if (File.Exists(envelopePath))
        {
            var info = new FileInfo(envelopePath);
            if (info.Length <= 4 * 1024 * 1024)
            {
                envelopeBytes = await File.ReadAllBytesAsync(envelopePath, CancellationToken.None);
            }
        }

        byte[]? rawOutputBytes = null;
        if (File.Exists(rawOutputPath))
        {
            var info = new FileInfo(rawOutputPath);
            if (info.Length <= ExtractionCeilings.MaxRawOutputBytes + 1)
            {
                rawOutputBytes = await File.ReadAllBytesAsync(rawOutputPath, CancellationToken.None);
            }
            else
            {
                abortCode ??= "output_cap_exceeded";
                abortDetail ??= "Raw worker output file exceeded the 16 MiB maximum.";
            }
        }

        return new WorkerRunOutcome(envelopeBytes, rawOutputBytes, exitCode, abortCode, abortDetail);
    }

    private static Dictionary<string, string> BuildIsolatedEnvironment(string q0Root, string cacheDir, string leasedGpuUuid)
    {
        var systemRoot = Environment.GetEnvironmentVariable("SystemRoot") ?? @"C:\Windows";
        var venvScripts = Path.Combine(q0Root, "venv", "Scripts");
        var env = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        foreach (var key in SafeSystemPassthroughVars)
        {
            if (Environment.GetEnvironmentVariable(key) is { Length: > 0 } val)
            {
                env[key] = val;
            }
        }

        var tmpDir = Directory.CreateDirectory(Path.Combine(cacheDir, "tmp")).FullName;
        var homeDir = Directory.CreateDirectory(Path.Combine(cacheDir, "home")).FullName;
        var hfHome = Directory.CreateDirectory(Path.Combine(cacheDir, "hf-home")).FullName;
        var hfHub = Directory.CreateDirectory(Path.Combine(hfHome, "hub")).FullName;
        var hfTrans = Directory.CreateDirectory(Path.Combine(hfHome, "transformers")).FullName;
        var hfMods = Directory.CreateDirectory(Path.Combine(cacheDir, "hf-modules")).FullName;

        env["PATH"] = string.Join(Path.PathSeparator, venvScripts, Path.Combine(systemRoot, "System32"), systemRoot);
        env["VIRTUAL_ENV"] = Path.Combine(q0Root, "venv");
        env["TEMP"] = tmpDir;
        env["TMP"] = tmpDir;
        env["TMPDIR"] = tmpDir;
        env["USERPROFILE"] = homeDir;
        env["HOME"] = homeDir;
        env["HF_HOME"] = hfHome;
        env["HF_HUB_CACHE"] = hfHub;
        env["HUGGINGFACE_HUB_CACHE"] = hfHub;
        env["TRANSFORMERS_CACHE"] = hfTrans;
        env["HF_MODULES_CACHE"] = hfMods;
        env["HF_HUB_OFFLINE"] = "1";
        env["TRANSFORMERS_OFFLINE"] = "1";
        env["HF_HUB_DISABLE_XET"] = "1";
        env["HF_HUB_DISABLE_TELEMETRY"] = "1";
        env["HF_HUB_DISABLE_PROGRESS_BARS"] = "1";
        env["TORCH_HOME"] = Directory.CreateDirectory(Path.Combine(cacheDir, "torch-home")).FullName;
        env["TRITON_CACHE_DIR"] = Directory.CreateDirectory(Path.Combine(cacheDir, "triton-cache")).FullName;
        env["TORCHINDUCTOR_CACHE_DIR"] = Directory.CreateDirectory(Path.Combine(cacheDir, "inductor-cache")).FullName;
        env["CUDA_CACHE_PATH"] = Directory.CreateDirectory(Path.Combine(cacheDir, "cuda-cache")).FullName;
        env["XDG_CACHE_HOME"] = Directory.CreateDirectory(Path.Combine(cacheDir, "xdg-cache")).FullName;
        env["PIP_NO_INDEX"] = "1";
        env["PIP_CONFIG_FILE"] = "NUL";
        env["PIP_CACHE_DIR"] = Directory.CreateDirectory(Path.Combine(cacheDir, "pip-cache")).FullName;
        env["UV_CACHE_DIR"] = Directory.CreateDirectory(Path.Combine(cacheDir, "uv-cache")).FullName;
        env["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID";
        env["CUDA_VISIBLE_DEVICES"] = leasedGpuUuid;
        return env;
    }

    private async Task WriteRequestManifestAsync(
        string requestPath,
        ClaimedAttemptWork work,
        string writableRoot,
        string q0Root,
        string inputPdfPath,
        string modelDir,
        string noticeDir,
        int callTimeoutSeconds,
        byte[] expectedConfigSha,
        CancellationToken cancellationToken)
    {
        var payload = new
        {
            schema = ExtractionCeilings.RequestSchema,
            document_id = work.DocumentId.ToString("D"),
            job_id = work.JobId.ToString("D"),
            attempt_id = work.AttemptId.ToString("D"),
            fencing_token = work.FencingToken,
            writable_runtime_root = writableRoot,
            readonly_q0_root = q0Root,
            input_pdf_path = inputPdfPath,
            expected_input_sha256 = Convert.ToHexStringLower(work.InputSha256),
            expected_input_byte_length = work.InputByteLength,
            expected_page_count = work.PageCount,
            model_dir = modelDir,
            notice_dir = noticeDir,
            leased_gpu_uuid = settings.LeasedGpuUuid,
            expected_model_manifest_sha256 = Convert.ToHexStringLower(settings.ModelManifestSha256),
            expected_dependency_lock_sha256 = Convert.ToHexStringLower(settings.DependencyLockSha256),
            expected_worker_source_sha256 = Convert.ToHexStringLower(settings.WorkerSourceSha256),
            expected_worker_config_sha256 = Convert.ToHexStringLower(expectedConfigSha),
            accepted_provenance_exceptions = new[] { ExtractionCeilings.RequiredProvenanceException },
            guards = new
            {
                load_timeout_s = ExtractionCeilings.LoadTimeoutSeconds,
                call_timeout_s = callTimeoutSeconds,
                stall_timeout_s = ExtractionCeilings.StallTimeoutSeconds,
                heartbeat_interval_s = ExtractionCeilings.HeartbeatIntervalSeconds,
                max_raw_output_bytes = ExtractionCeilings.MaxRawOutputBytes,
                max_log_bytes = ExtractionCeilings.MaxLogBytes,
                min_free_disk_bytes = ExtractionCeilings.MinFreeDiskBytes,
                max_runtime_root_bytes = ExtractionCeilings.MaxRuntimeRootBytes,
            },
        };

        var json = JsonSerializer.Serialize(payload, new JsonSerializerOptions { WriteIndented = true });
        await File.WriteAllTextAsync(requestPath, json, new UTF8Encoding(false), cancellationToken);
    }

    private static async Task PumpBoundedLogAsync(Stream pipe, string targetPath, Func<long, long> addTotalBytes)
    {
        await using var file = new FileStream(targetPath, FileMode.CreateNew, FileAccess.Write, FileShare.Read);
        var buffer = new byte[8192];
        while (true)
        {
            int read;
            try
            {
                read = await pipe.ReadAsync(buffer).ConfigureAwait(false);
            }
            catch (IOException)
            {
                break;
            }

            if (read <= 0)
            {
                break;
            }

            var total = addTotalBytes(read);
            if (total <= ExtractionCeilings.MaxLogBytes)
            {
                await file.WriteAsync(buffer.AsMemory(0, read)).ConfigureAwait(false);
                await file.FlushAsync().ConfigureAwait(false);
            }
        }
    }

    private const int MaxStorageScanDepth = 32;
    private const int MaxStorageScanEntries = 100_000;
    private static readonly EnumerationOptions SingleLevelScanOptions = new()
    {
        RecurseSubdirectories = false,
        IgnoreInaccessible = false,
        AttributesToSkip = 0,
    };

    public static bool CheckStorageBounds(string writableRoot, out string failureDetail)
    {
        failureDetail = string.Empty;
        if (string.IsNullOrWhiteSpace(writableRoot) || !Directory.Exists(writableRoot))
        {
            failureDetail = "Configured writable F2 runtime root does not exist.";
            return false;
        }

        bool rootReparse;
        try
        {
            rootReparse = IsReparsePoint(writableRoot);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            failureDetail = "Unable to inspect local OCR runtime root attributes safely.";
            return false;
        }

        if (rootReparse)
        {
            failureDetail = "Configured writable F2 runtime root must not be a symlink or reparse point.";
            return false;
        }

        var rootDrive = Path.GetPathRoot(writableRoot);
        if (!string.IsNullOrWhiteSpace(rootDrive))
        {
            try
            {
                var drive = new DriveInfo(rootDrive);
                if (drive.AvailableFreeSpace < ExtractionCeilings.MinFreeDiskBytes)
                {
                    failureDetail = "Available free disk space fell below the 20 GiB safety floor.";
                    return false;
                }
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
            {
                failureDetail = "Unable to verify free disk space floor safely.";
                return false;
            }
        }

        long used = 0;
        var inspectedEntries = 0;
        var fullRoot = Path.GetFullPath(writableRoot);
        var stack = new Stack<(string DirPath, int Depth)>();
        stack.Push((fullRoot, 0));

        while (stack.Count > 0)
        {
            var (curDir, depth) = stack.Pop();
            if (depth > MaxStorageScanDepth)
            {
                failureDetail = "Local OCR runtime directory nesting exceeded bounded scan depth.";
                return false;
            }

            List<FileSystemInfo>? entries = null;
            DateTime? prevCreationUtc = null;
            var resolved = false;

            for (var attempt = 0; attempt < 6; attempt++)
            {
                try
                {
                    entries = [.. new DirectoryInfo(curDir).EnumerateFileSystemInfos("*", SingleLevelScanOptions)];
                    resolved = true;
                    break;
                }
                catch (Exception ex) when (ex is DirectoryNotFoundException or FileNotFoundException)
                {
                    entries = null;
                    resolved = true;
                    break;
                }
                catch (Exception ex) when (ex is UnauthorizedAccessException or IOException)
                {
                    var curCreation = TryGetDirectoryCreationUtc(curDir);
                    if (curCreation is null)
                    {
                        // Directory vanished concurrently (e.g. NTFS STATUS_DELETE_PENDING completed).
                        entries = null;
                        resolved = true;
                        break;
                    }

                    if (prevCreationUtc is not null && curCreation.Value == prevCreationUtc.Value && attempt >= 3)
                    {
                        // Same persistent directory instance remained unreadable across retries: fail closed.
                        failureDetail = "Unable to inspect local OCR runtime storage directory safely.";
                        return false;
                    }

                    prevCreationUtc = curCreation;
                    Thread.Sleep(2 * (attempt + 1));
                }
            }

            if (!resolved)
            {
                // Directory CreationTimeUtc changed across every retry due to rapid delete/recreate churn in cache.
                if (IsInsideRunCacheOrTemp(fullRoot, curDir))
                {
                    continue;
                }

                failureDetail = "Unable to inspect local OCR runtime storage directory safely.";
                return false;
            }

            if (entries is null)
            {
                continue;
            }

            foreach (var entry in entries)
            {
                inspectedEntries++;
                if (inspectedEntries > MaxStorageScanEntries)
                {
                    failureDetail = "Local OCR runtime directory entry count exceeded bounded scan limit.";
                    return false;
                }

                FileAttributes attrs;
                try
                {
                    attrs = entry.Attributes;
                }
                catch (Exception ex) when (ex is FileNotFoundException or DirectoryNotFoundException)
                {
                    continue;
                }
                catch (Exception ex) when (ex is UnauthorizedAccessException or IOException)
                {
                    Thread.Sleep(2);
                    if (!Path.Exists(entry.FullName))
                    {
                        continue;
                    }

                    failureDetail = "Unable to inspect local OCR runtime entry attributes safely.";
                    return false;
                }

                if ((attrs & FileAttributes.ReparsePoint) != 0)
                {
                    failureDetail = "Reparse point or symlink detected inside local OCR runtime directory.";
                    return false;
                }

                if ((attrs & FileAttributes.Directory) != 0)
                {
                    stack.Push((entry.FullName, depth + 1));
                }
                else if (entry is FileInfo fi)
                {
                    long len;
                    try
                    {
                        len = fi.Length;
                    }
                    catch (Exception ex) when (ex is FileNotFoundException or DirectoryNotFoundException)
                    {
                        continue;
                    }
                    catch (Exception ex) when (ex is UnauthorizedAccessException or IOException)
                    {
                        Thread.Sleep(2);
                        if (!File.Exists(fi.FullName))
                        {
                            continue;
                        }

                        failureDetail = "Unable to inspect local OCR runtime file size safely.";
                        return false;
                    }

                    used += len;
                    if (used > ExtractionCeilings.MaxRuntimeRootBytes)
                    {
                        failureDetail = "Local OCR runtime directory exceeded the 4 GiB storage ceiling.";
                        return false;
                    }
                }
            }
        }

        return true;
    }

    private static DateTime? TryGetDirectoryCreationUtc(string dirPath)
    {
        try
        {
            if (!Directory.Exists(dirPath))
            {
                return null;
            }

            return Directory.GetCreationTimeUtc(dirPath);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            return Directory.Exists(dirPath) ? DateTime.MinValue : null;
        }
    }

    private static bool IsInsideRunCacheOrTemp(string fullRoot, string candidateDir)
    {
        var rel = Path.GetRelativePath(fullRoot, candidateDir).Replace('\\', '/');
        return rel.StartsWith("runs/", StringComparison.OrdinalIgnoreCase) &&
               rel.Contains("/cache/", StringComparison.OrdinalIgnoreCase);
    }

    private static bool IsReparsePoint(string path) =>
        (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0;

    private static HeartbeatRecord? TryReadHeartbeatFile(string path)
    {
        if (!File.Exists(path))
        {
            return null;
        }

        try
        {
            using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
            using var doc = JsonDocument.Parse(stream);
            var root = doc.RootElement;
            var phase = root.TryGetProperty("phase", out var p) && p.ValueKind == JsonValueKind.String ? p.GetString() ?? "running" : "running";
            var workerPid = root.TryGetProperty("worker_pid", out var wp) && wp.TryGetInt32(out var pidVal) ? pidVal : 0;
            var workerFt = root.TryGetProperty("worker_create_filetime", out var wf) && wf.TryGetInt64(out var ftVal) ? ftVal : 0L;
            var phaseTimeout = root.TryGetProperty("phase_timeout_s", out var pt) && pt.ValueKind == JsonValueKind.Number && pt.TryGetInt32(out var ptVal)
                ? (int?)ptVal
                : null;
            var stallMon = root.TryGetProperty("stall_monitored", out var sm) && sm.ValueKind == JsonValueKind.True;
            var progress = root.TryGetProperty("forward_progress", out var fp) && fp.TryGetInt64(out var progVal) ? progVal : 0L;
            return new HeartbeatRecord(phase, workerPid, workerFt, phaseTimeout, stallMon, progress);
        }
        catch (Exception ex) when (ex is IOException or JsonException or UnauthorizedAccessException)
        {
            return null;
        }
    }

    private readonly record struct HeartbeatRecord(
        string Phase,
        int WorkerPid,
        long WorkerCreateFileTime,
        int? PhaseTimeoutSeconds,
        bool StallMonitored,
        long ForwardProgress);
}
