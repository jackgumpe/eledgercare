using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using ELedgerCare.Application.Extraction;
using ELedgerCare.Domain.Processing;
using ELedgerCare.Infrastructure.Extraction;
using Xunit;

namespace ELedgerCare.Infrastructure.Tests;

public sealed class WorkerEnvelopeAndJobObjectTests
{
    private static readonly DateTimeOffset Now = new(2026, 11, 16, 5, 30, 0, TimeSpan.Zero);

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "ELedgerCare.slnx")))
        {
            dir = dir.Parent;
        }

        return dir?.FullName ?? throw new InvalidOperationException("Repository root not found.");
    }

    internal static string ResolveHostPythonExe()
    {
        const string pinnedHostPython = @"C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe";
        if (File.Exists(pinnedHostPython))
        {
            return pinnedHostPython;
        }

        var pathEnv = Environment.GetEnvironmentVariable("PATH") ?? string.Empty;
        foreach (var entry in pathEnv.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries))
        {
            var candidate = Path.Combine(entry.Trim(), "python.exe");
            if (File.Exists(candidate))
            {
                return candidate;
            }
        }

        throw new FileNotFoundException("Host Python 3.12 executable not found.");
    }

    private static (ExtractionSettings Settings, ClaimedAttemptWork Work) CreatePinnedContext(int pageCount = 3)
    {
        var root = FindRepoRoot();
        var workerRoot = Path.Combine(root, "workers", "local_ocr");
        var manifestSha = SHA256.HashData(File.ReadAllBytes(Path.Combine(workerRoot, "manifests", "model-files.json")));
        var lockSha = SHA256.HashData(File.ReadAllBytes(Path.Combine(workerRoot, "manifests", "dependency-lock.json")));
        var workerSha = ExtractionSettings.ComputeWorkerSourceSha256(workerRoot);

        var settings = new ExtractionSettings(
            enabled: false,
            maxExtractionPages: 3,
            readOnlyQ0Root: null,
            writableRuntimeRoot: null,
            leasedGpuUuid: null,
            workerRootPath: workerRoot,
            modelManifestSha256: manifestSha,
            dependencyLockSha256: lockSha,
            workerSourceSha256: workerSha);

        var pdfBytes = Encoding.ASCII.GetBytes("%PDF-1.4\n%%EOF\n");
        var inputSha = SHA256.HashData(pdfBytes);
        var work = new ClaimedAttemptWork(
            AttemptId: Guid.Parse("019a8000-0000-7000-8000-000000000003"),
            JobId: Guid.Parse("019a8000-0000-7000-8000-000000000002"),
            DocumentId: Guid.Parse("019a8000-0000-7000-8000-000000000001"),
            AttemptNumber: 1,
            FencingToken: 7,
            RunDirectoryName: "attempt-019a8000-0000-7000-8000-000000000003",
            PdfBytes: pdfBytes,
            InputSha256: inputSha,
            InputByteLength: pdfBytes.Length,
            PageCount: pageCount);

        return (settings, work);
    }

    private static byte[] BuildEnvelopeBytes(
        ClaimedAttemptWork work,
        ExtractionSettings settings,
        byte[] rawOutputBytes,
        string status = "completed",
        string finishReason = "stop",
        int? outputPageCount = null,
        long? fencingToken = null,
        string? rawShaHexOverride = null,
        string? configShaHexOverride = null,
        string rendererIdentity = "pypdfium2==5.15.2 (PDFium 159.0.8149.0)",
        string[]? provenanceExceptions = null,
        string schema = ExtractionCeilings.EnvelopeSchema)
    {
        var rawShaHex = rawShaHexOverride ?? Convert.ToHexStringLower(SHA256.HashData(rawOutputBytes));
        var configShaHex = configShaHexOverride ?? Convert.ToHexStringLower(ExtractionSettings.ComputeWorkerConfigSha256(work.PageCount));
        var payload = new
        {
            schema,
            status,
            document_id = work.DocumentId.ToString("D"),
            job_id = work.JobId.ToString("D"),
            attempt_id = work.AttemptId.ToString("D"),
            fencing_token = fencingToken ?? work.FencingToken,
            input = new
            {
                sha256 = Convert.ToHexStringLower(work.InputSha256),
                byte_length = work.InputByteLength,
                page_count = work.PageCount,
            },
            provenance = new
            {
                model_repo_id = ExtractionCeilings.ModelRepoId,
                model_revision = ExtractionCeilings.ModelRevision,
                model_manifest_sha256 = Convert.ToHexStringLower(settings.ModelManifestSha256),
                dependency_lock_sha256 = Convert.ToHexStringLower(settings.DependencyLockSha256),
                worker_source_sha256 = Convert.ToHexStringLower(settings.WorkerSourceSha256),
                worker_config_sha256 = configShaHex,
                renderer_identity = rendererIdentity,
                provenance_exceptions = provenanceExceptions ?? [ExtractionCeilings.RequiredProvenanceException],
                generation_settings = new { temperature = 0.0, max_new_tokens = 8000 * work.PageCount },
            },
            output = new
            {
                finish_reason = finishReason,
                output_page_count = outputPageCount ?? work.PageCount,
                byte_length = rawOutputBytes.Length,
                sha256 = rawShaHex,
            },
            timings = new
            {
                started_at_utc = "2026-11-16T05:29:50Z",
                completed_at_utc = "2026-11-16T05:30:00Z",
                load_duration_ms = 1200L,
                render_duration_ms = 85L,
                infer_duration_ms = 4300L,
                total_duration_ms = 5585L,
            },
            diagnostics = new { fallback_used = false, forward_progress = 42 },
        };

        return JsonSerializer.SerializeToUtf8Bytes(payload);
    }

    [Fact]
    public async Task Worker_source_and_config_digests_match_python_protocol_exactly()
    {
        var root = FindRepoRoot();
        var workerRoot = Path.Combine(root, "workers", "local_ocr");
        var pythonExe = ResolveHostPythonExe();

        var psi = new ProcessStartInfo(pythonExe)
        {
            WorkingDirectory = workerRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        psi.ArgumentList.Add("-B");
        psi.ArgumentList.Add("-c");
        psi.ArgumentList.Add(
            "import json; from local_ocr import protocol as p; " +
            "print(json.dumps({'src': p.compute_worker_source_sha256(), " +
            "'c1': p.compute_config_digest(1), 'c2': p.compute_config_digest(2), 'c3': p.compute_config_digest(3)}))");

        using var proc = Process.Start(psi)!;
        var stdout = await proc.StandardOutput.ReadToEndAsync(TestContext.Current.CancellationToken);
        var stderr = await proc.StandardError.ReadToEndAsync(TestContext.Current.CancellationToken);
        await proc.WaitForExitAsync(TestContext.Current.CancellationToken);
        Assert.True(proc.ExitCode == 0, $"Python failed: {stderr}");

        using var doc = JsonDocument.Parse(stdout);
        var pyRoot = doc.RootElement;

        Assert.Equal(
            pyRoot.GetProperty("src").GetString(),
            Convert.ToHexStringLower(ExtractionSettings.ComputeWorkerSourceSha256(workerRoot)));
        Assert.Equal(
            pyRoot.GetProperty("c1").GetString(),
            Convert.ToHexStringLower(ExtractionSettings.ComputeWorkerConfigSha256(1)));
        Assert.Equal(
            pyRoot.GetProperty("c2").GetString(),
            Convert.ToHexStringLower(ExtractionSettings.ComputeWorkerConfigSha256(2)));
        Assert.Equal(
            pyRoot.GetProperty("c3").GetString(),
            Convert.ToHexStringLower(ExtractionSettings.ComputeWorkerConfigSha256(3)));
    }

    [Fact]
    public void Validator_accepts_valid_three_page_envelope_and_rejects_tampered_or_truncated_outputs()
    {
        var (settings, work) = CreatePinnedContext(pageCount: 3);
        var raw3Pages = "<PAGE>\nPage 1\n<PAGE>\nPage 2\n<PAGE>\nPage 3\n"u8.ToArray();
        var validEnvelope = BuildEnvelopeBytes(work, settings, raw3Pages);

        var accepted = Assert.IsType<EnvelopeValidationOutcome.Accepted>(
            WorkerEnvelopeValidator.Validate(work, settings, new WorkerRunOutcome(validEnvelope, raw3Pages, 0, null, null), Now));
        Assert.Equal(3, accepted.Result.PageCount);
        Assert.Equal(3, accepted.Result.OutputPageCount);
        Assert.Equal(work.FencingToken, accepted.Result.FencingToken);

        // 1. Truncated finish_reason='length' is rejected and retains bounded diagnostic preview.
        var truncatedEnv = BuildEnvelopeBytes(work, settings, raw3Pages, finishReason: "length");
        var truncated = Assert.IsType<EnvelopeValidationOutcome.Rejected>(
            WorkerEnvelopeValidator.Validate(work, settings, new WorkerRunOutcome(truncatedEnv, raw3Pages, 0, null, null), Now));
        Assert.Equal("model_output_truncated", truncated.FailureCode);
        Assert.Contains("Page 1", truncated.DiagnosticRawOutputUtf8, StringComparison.Ordinal);

        // 2. Mismatched fencing token is rejected.
        var wrongTokenEnv = BuildEnvelopeBytes(work, settings, raw3Pages, fencingToken: work.FencingToken - 1);
        var wrongToken = Assert.IsType<EnvelopeValidationOutcome.Rejected>(
            WorkerEnvelopeValidator.Validate(work, settings, new WorkerRunOutcome(wrongTokenEnv, raw3Pages, 0, null, null), Now));
        Assert.Equal("worker_identity_mismatch", wrongToken.FailureCode);

        // 3. Missing torchvision TOFU provenance exception is rejected.
        var missingTofuEnv = BuildEnvelopeBytes(work, settings, raw3Pages, provenanceExceptions: []);
        var missingTofu = Assert.IsType<EnvelopeValidationOutcome.Rejected>(
            WorkerEnvelopeValidator.Validate(work, settings, new WorkerRunOutcome(missingTofuEnv, raw3Pages, 0, null, null), Now));
        Assert.Equal("worker_provenance_mismatch", missingTofu.FailureCode);

        // 4. Tampered config digest is rejected.
        var badConfigEnv = BuildEnvelopeBytes(work, settings, raw3Pages, configShaHexOverride: new string('a', 64));
        var badConfig = Assert.IsType<EnvelopeValidationOutcome.Rejected>(
            WorkerEnvelopeValidator.Validate(work, settings, new WorkerRunOutcome(badConfigEnv, raw3Pages, 0, null, null), Now));
        Assert.Equal("worker_provenance_mismatch", badConfig.FailureCode);

        // 5. Raw SHA-256 mismatch is rejected.
        var badShaEnv = BuildEnvelopeBytes(work, settings, raw3Pages, rawShaHexOverride: new string('b', 64));
        var badSha = Assert.IsType<EnvelopeValidationOutcome.Rejected>(
            WorkerEnvelopeValidator.Validate(work, settings, new WorkerRunOutcome(badShaEnv, raw3Pages, 0, null, null), Now));
        Assert.Equal("worker_output_digest_mismatch", badSha.FailureCode);

        // 6. <PAGE> marker count mismatch (2 markers for 3-page document) is rejected.
        var twoPageBytes = "<PAGE>\nPage 1\n<PAGE>\nPage 2\n"u8.ToArray();
        var badMarkerEnv = BuildEnvelopeBytes(work, settings, twoPageBytes, outputPageCount: 3);
        var badMarker = Assert.IsType<EnvelopeValidationOutcome.Rejected>(
            WorkerEnvelopeValidator.Validate(work, settings, new WorkerRunOutcome(badMarkerEnv, twoPageBytes, 0, null, null), Now));
        Assert.Equal("page_count_mismatch", badMarker.FailureCode);

        // 7. Invalid UTF-8 bytes with matching SHA-256 are rejected.
        byte[] invalidUtf8 = [(byte)'<', (byte)'P', (byte)'A', (byte)'G', (byte)'E', (byte)'>', 0xFF, 0xFE];
        var (_, work1) = CreatePinnedContext(pageCount: 1);
        var badUtf8Env = BuildEnvelopeBytes(work1, settings, invalidUtf8);
        var badUtf8 = Assert.IsType<EnvelopeValidationOutcome.Rejected>(
            WorkerEnvelopeValidator.Validate(work1, settings, new WorkerRunOutcome(badUtf8Env, invalidUtf8, 0, null, null), Now));
        Assert.Equal("worker_invalid_utf8", badUtf8.FailureCode);

        // 8. Malformed JSON envelope and non-zero exit code are rejected.
        var malformed = Assert.IsType<EnvelopeValidationOutcome.Rejected>(
            WorkerEnvelopeValidator.Validate(work, settings, new WorkerRunOutcome("{not-json"u8.ToArray(), raw3Pages, 0, null, null), Now));
        Assert.Equal("worker_malformed_envelope", malformed.FailureCode);

        var nonZero = Assert.IsType<EnvelopeValidationOutcome.Rejected>(
            WorkerEnvelopeValidator.Validate(work, settings, new WorkerRunOutcome(validEnvelope, raw3Pages, 1, null, null), Now));
        Assert.Equal("worker_nonzero_exit", nonZero.FailureCode);
    }

    /// <summary>
    /// F2-04: proves CREATE_SUSPENDED assigns the launcher into the Windows Job Object BEFORE any
    /// user-mode instruction executes (zero startup race), and tracks spawned grandchildren inside the job.
    /// </summary>
    [Fact]
    public async Task WindowsJobProcess_suspended_assignment_contains_launcher_before_execution_and_tracks_grandchild()
    {
        var tempDir = Path.Combine(Path.GetTempPath(), $"elc-job-unit-{Guid.NewGuid():N}");
        Directory.CreateDirectory(tempDir);
        try
        {
            var (launcherScript, _) = ExternalJobSupervisorHelper.WriteLauncherAndGrandchildScripts(tempDir);
            var pythonExe = ResolveHostPythonExe();
            var env = ExternalJobSupervisorHelper.MinimalWin32Env();
            var probe = new WindowsProcessIdentityProbe();

            using var job = WindowsJobProcess.CreateSuspendedAssigned(
                pythonExe,
                ["-B", launcherScript, tempDir],
                tempDir,
                env);

            Assert.False(job.IsResumed);
            Assert.True(job.LauncherIdentity.Pid > 0);
            Assert.True(job.LauncherIdentity.CreateFileTime > 0);
            Assert.True(probe.IsProcessAlive(job.LauncherIdentity.Pid, job.LauncherIdentity.CreateFileTime));

            // Kernel Job Object already contains the suspended launcher BEFORE ResumePrimaryThread!
            var preResumeMembers = job.QueryActiveJobProcesses();
            Assert.Contains(job.LauncherIdentity, preResumeMembers);

            // Wait 150ms while suspended: zero child instructions execute and zero grandchild exists.
            await Task.Delay(150, TestContext.Current.CancellationToken);
            Assert.False(File.Exists(Path.Combine(tempDir, "started.txt")));
            Assert.False(File.Exists(Path.Combine(tempDir, "grandchild.json")));

            job.ResumePrimaryThread();
            Assert.True(job.IsResumed);

            var grandchild = await ExternalJobSupervisorHelper.WaitForGrandchildAsync(tempDir, TimeSpan.FromSeconds(15));
            Assert.True(probe.IsProcessAlive(grandchild.Pid, grandchild.CreateFileTime));

            // Both launcher and spawned grandchild are inside the same kernel Job Object.
            var postResumeMembers = job.QueryActiveJobProcesses();
            Assert.Contains(job.LauncherIdentity, postResumeMembers);
            Assert.Contains(grandchild, postResumeMembers);

            job.TerminateAllInJob(1);
            await job.WaitForAllJobProcessesExitAsync(TimeSpan.FromSeconds(10));

            Assert.False(probe.IsProcessAlive(job.LauncherIdentity.Pid, job.LauncherIdentity.CreateFileTime));
            Assert.False(probe.IsProcessAlive(grandchild.Pid, grandchild.CreateFileTime));
        }
        finally
        {
            try { Directory.Delete(tempDir, recursive: true); } catch { /* best effort */ }
        }
    }

    /// <summary>
    /// F2-04: spawns a separate external .NET supervisor process that creates a WindowsJobProcess
    /// launcher+grandchild tree, then kills ONLY the supervisor via TerminateProcess (entireProcessTree: false),
    /// proving the Windows kernel (JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE) terminates both launcher and grandchild
    /// in BOTH the suspended pre-resume window and the active grandchild-running window.
    /// </summary>
    [Theory]
    [InlineData("suspended")]
    [InlineData("running")]
    public async Task Abrupt_TerminateProcess_of_external_supervisor_kills_launcher_and_grandchild_via_Job_Object(string mode)
    {
        var tempDir = Path.Combine(Path.GetTempPath(), $"elc-job-crash-{mode}-{Guid.NewGuid():N}");
        Directory.CreateDirectory(tempDir);
        var probe = new WindowsProcessIdentityProbe();

        try
        {
            var selfExe = Path.Combine(AppContext.BaseDirectory, "ELedgerCare.Infrastructure.Tests.exe");
            Assert.True(File.Exists(selfExe), $"Expected test executable at {selfExe}");

            var psi = new ProcessStartInfo(selfExe)
            {
                WorkingDirectory = AppContext.BaseDirectory,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
            };
            psi.ArgumentList.Add("-method");
            psi.ArgumentList.Add($"{typeof(ExternalJobSupervisorHelper).FullName}.{nameof(ExternalJobSupervisorHelper.RunHelperIfRequested)}");
            psi.Environment["ELEDGERCARE_JOB_HELPER_DIR"] = tempDir;
            psi.Environment["ELEDGERCARE_JOB_HELPER_MODE"] = mode;

            using var supervisor = Process.Start(psi)!;
            var statePath = Path.Combine(tempDir, "helper_state.json");
            var deadline = DateTime.UtcNow.AddSeconds(20);
            while (!File.Exists(statePath))
            {
                if (supervisor.HasExited)
                {
                    var outText = await supervisor.StandardOutput.ReadToEndAsync(TestContext.Current.CancellationToken);
                    var errText = await supervisor.StandardError.ReadToEndAsync(TestContext.Current.CancellationToken);
                    throw new InvalidOperationException($"Helper supervisor exited prematurely ({supervisor.ExitCode}):\n{outText}\n{errText}");
                }

                if (DateTime.UtcNow > deadline)
                {
                    supervisor.Kill(entireProcessTree: true);
                    throw new TimeoutException($"Timed out waiting for helper_state.json in mode '{mode}'.");
                }

                await Task.Delay(40, TestContext.Current.CancellationToken);
            }

            using var stateDoc = JsonDocument.Parse(await File.ReadAllTextAsync(statePath, TestContext.Current.CancellationToken));
            var root = stateDoc.RootElement;
            var supPid = root.GetProperty("supervisorPid").GetInt32();
            var supFt = root.GetProperty("supervisorCreateFileTime").GetInt64();
            var launcherPid = root.GetProperty("launcherPid").GetInt32();
            var launcherFt = root.GetProperty("launcherCreateFileTime").GetInt64();
            var grandchildPid = root.GetProperty("grandchildPid").GetInt32();
            var grandchildFt = root.GetProperty("grandchildCreateFileTime").GetInt64();

            Assert.Equal(supervisor.Id, supPid);
            Assert.True(probe.IsProcessAlive(supPid, supFt));
            Assert.True(probe.IsProcessAlive(launcherPid, launcherFt));
            if (mode == "suspended")
            {
                Assert.False(File.Exists(Path.Combine(tempDir, "started.txt")));
            }
            else
            {
                Assert.True(grandchildPid > 0);
                Assert.True(probe.IsProcessAlive(grandchildPid, grandchildFt));
            }

            // Abruptly TerminateProcess ONLY the supervisor (entireProcessTree: false).
            // Only the kernel's JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE handle closure can kill the children!
            supervisor.Kill(entireProcessTree: false);
            await supervisor.WaitForExitAsync(TestContext.Current.CancellationToken);

            var exitDeadline = DateTime.UtcNow.AddSeconds(10);
            while (DateTime.UtcNow < exitDeadline &&
                   (probe.IsProcessAlive(launcherPid, launcherFt) ||
                    (grandchildPid > 0 && probe.IsProcessAlive(grandchildPid, grandchildFt))))
            {
                await Task.Delay(40, TestContext.Current.CancellationToken);
            }

            Assert.False(probe.IsProcessAlive(supPid, supFt));
            Assert.False(probe.IsProcessAlive(launcherPid, launcherFt));
            if (mode == "suspended")
            {
                Assert.False(File.Exists(Path.Combine(tempDir, "started.txt")));
            }
            else
            {
                Assert.False(probe.IsProcessAlive(grandchildPid, grandchildFt));
            }
        }
        finally
        {
            try { Directory.Delete(tempDir, recursive: true); } catch { /* best effort */ }
        }
    }

    /// <summary>
    /// F2-S1-01: runs the real LocalPythonOcrWorkerRunner -> WindowsJobProcess -> venv python.exe -I -B -X utf8 -u
    /// -> workers/local_ocr/run_worker.py from an external runDir (with no torch/model libraries installed),
    /// proving run_worker.py resolves local_ocr cleanly under -I, writes heartbeat.json + envelope.json,
    /// and validates as structured dependency_lock_mismatch (zero ModuleNotFoundError).
    /// </summary>
    [Fact]
    public async Task F2_S1_01_LocalPythonOcrWorkerRunner_executes_isolated_run_worker_from_external_venv_and_parses_envelope()
    {
        var ct = TestContext.Current.CancellationToken;
        var tempRoot = Path.Combine(Path.GetTempPath(), $"elc-s1-01-{Guid.NewGuid():N}");
        var fakeQ0 = Path.Combine(tempRoot, "q0");
        var fakeRt = Path.Combine(tempRoot, "rt");
        Directory.CreateDirectory(fakeQ0);
        Directory.CreateDirectory(fakeRt);

        try
        {
            var hostPy = ResolveHostPythonExe();
            using (var venvProc = Process.Start(new ProcessStartInfo(hostPy)
            {
                ArgumentList = { "-m", "venv", "--without-pip", Path.Combine(fakeQ0, "venv") },
                UseShellExecute = false,
                CreateNoWindow = true,
            })!)
            {
                await venvProc.WaitForExitAsync(ct);
                Assert.Equal(0, venvProc.ExitCode);
            }

            Directory.CreateDirectory(Path.Combine(fakeQ0, "models", "Unlimited_OCR_2_04809669"));
            Directory.CreateDirectory(Path.Combine(fakeQ0, "notices", "Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a"));

            var (baseSettings, work) = CreatePinnedContext(pageCount: 1);
            var enabledSettings = new ExtractionSettings(
                enabled: true,
                maxExtractionPages: 3,
                readOnlyQ0Root: fakeQ0,
                writableRuntimeRoot: fakeRt,
                leasedGpuUuid: "GPU-00000000-0000-0000-0000-000000000000",
                workerRootPath: baseSettings.WorkerRootPath,
                modelManifestSha256: baseSettings.ModelManifestSha256,
                dependencyLockSha256: baseSettings.DependencyLockSha256,
                workerSourceSha256: baseSettings.WorkerSourceSha256);

            var runner = new LocalPythonOcrWorkerRunner(enabledSettings);
            var probe = new WindowsProcessIdentityProbe();
            int capturedLauncherPid = 0;
            long capturedLauncherFt = 0;

            var outcome = await runner.ExecuteAttemptAsync(
                work,
                (pid, ft, _) =>
                {
                    capturedLauncherPid = pid;
                    capturedLauncherFt = ft;
                    return Task.FromResult(true);
                },
                (_, _, _, _) => Task.FromResult(true),
                ct);

            var runOutDir = Path.Combine(fakeRt, "runs", work.RunDirectoryName, "output");
            var stderrLog = await File.ReadAllTextAsync(Path.Combine(runOutDir, "child.stderr.log"), ct);

            Assert.DoesNotContain("ModuleNotFoundError", stderrLog, StringComparison.Ordinal);
            Assert.Equal(2, outcome.ExitCode);
            Assert.NotNull(outcome.EnvelopeJsonBytes);
            Assert.True(File.Exists(Path.Combine(runOutDir, "heartbeat.json")));
            Assert.False(probe.IsProcessAlive(capturedLauncherPid, capturedLauncherFt));

            var validated = Assert.IsType<EnvelopeValidationOutcome.Rejected>(
                WorkerEnvelopeValidator.Validate(work, enabledSettings, outcome, Now));
            Assert.Equal("dependency_lock_mismatch", validated.FailureCode);
        }
        finally
        {
            try { Directory.Delete(tempRoot, recursive: true); } catch { /* best effort */ }
        }
    }

    /// <summary>
    /// F2-S1-02: proves CheckStorageBounds tolerates heavy multi-threaded NTFS cache subdirectory churn
    /// without throwing, while failing closed (false) on reparse points and persistent unreadable directories.
    /// </summary>
    [Fact]
    public async Task F2_S1_02_CheckStorageBounds_survives_concurrent_ntfs_subdir_churn_and_rejects_reparse_and_locked_dirs()
    {
        var ct = TestContext.Current.CancellationToken;
        var tempRt = Path.Combine(Path.GetTempPath(), $"elc-s1-02-storage-{Guid.NewGuid():N}");
        Directory.CreateDirectory(tempRt);
        string? aclLockedDir = null;

        try
        {
            for (var s = 0; s < 16; s++)
            {
                var seedDir = Path.Combine(tempRt, "runs", "attempt-1", "cache", $"seed-{s:D2}");
                Directory.CreateDirectory(seedDir);
                await File.WriteAllBytesAsync(Path.Combine(seedDir, "blob.bin"), [1, 2, 3, 4], ct);
            }

            // 1. 4-thread rapid subdirectory create/write/delete churn on same %16 names: zero exceptions!
            using (var churnCts = CancellationTokenSource.CreateLinkedTokenSource(ct))
            {
                churnCts.CancelAfter(TimeSpan.FromSeconds(4));
                var churnTasks = Enumerable.Range(0, 4).Select(workerIdx => Task.Run(() =>
                {
                    var seq = 0;
                    while (!churnCts.IsCancellationRequested)
                    {
                        var sub = Path.Combine(tempRt, "runs", "attempt-1", "cache", "tmp", $"w{workerIdx}-transient-{seq++ % 16}");
                        try
                        {
                            Directory.CreateDirectory(sub);
                            for (var f = 0; f < 6; f++)
                            {
                                File.WriteAllBytes(Path.Combine(sub, $"part-{f}.tmp"), [1, 2, 3, 4]);
                            }

                            Directory.Delete(sub, recursive: true);
                        }
                        catch
                        {
                            // Expected concurrent churn races among worker threads.
                        }
                    }
                }, CancellationToken.None)).ToArray();

                for (var iter = 0; iter < 1200 && !churnCts.IsCancellationRequested; iter++)
                {
                    Assert.True(LocalPythonOcrWorkerRunner.CheckStorageBounds(tempRt, out var err), $"Failed on iter {iter}: {err}");
                }

                await churnCts.CancelAsync();
                try { await Task.WhenAll(churnTasks); } catch { /* best effort */ }
            }

            // 2. Reparse point (NTFS directory junction) inside writableRoot fails closed.
            var outsideTarget = Path.Combine(Path.GetTempPath(), $"elc-s1-02-target-{Guid.NewGuid():N}");
            var junctionPath = Path.Combine(tempRt, "runs", "junction-escape");
            Directory.CreateDirectory(outsideTarget);
            try
            {
                using (var mklink = Process.Start(new ProcessStartInfo("cmd.exe")
                {
                    ArgumentList = { "/c", "mklink", "/J", junctionPath, outsideTarget },
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                })!)
                {
                    await mklink.WaitForExitAsync(ct);
                    Assert.Equal(0, mklink.ExitCode);
                }

                Assert.False(LocalPythonOcrWorkerRunner.CheckStorageBounds(tempRt, out var reparseDetail));
                Assert.Contains("Reparse point", reparseDetail, StringComparison.OrdinalIgnoreCase);
            }
            finally
            {
                if (Directory.Exists(junctionPath))
                {
                    Directory.Delete(junctionPath, recursive: false);
                }

                try { Directory.Delete(outsideTarget, recursive: true); } catch { /* best effort */ }
            }

            // 3. Persistent unreadable directory (NTFS DENY ListDirectory ACL for Everyone S-1-1-0) fails closed instead of being swallowed.
            aclLockedDir = Path.Combine(tempRt, "runs", "locked-persistent");
            Directory.CreateDirectory(aclLockedDir);
            await File.WriteAllBytesAsync(Path.Combine(aclLockedDir, "hidden.bin"), [9, 9, 9], ct);
            using (var denyProc = Process.Start(new ProcessStartInfo("icacls.exe")
            {
                ArgumentList = { aclLockedDir, "/deny", "*S-1-1-0:(RD)" },
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
            })!)
            {
                await denyProc.WaitForExitAsync(ct);
                Assert.Equal(0, denyProc.ExitCode);
            }

            Assert.False(LocalPythonOcrWorkerRunner.CheckStorageBounds(tempRt, out var aclDetail));
            Assert.Contains("Unable to inspect", aclDetail, StringComparison.OrdinalIgnoreCase);
        }
        finally
        {
            if (aclLockedDir is not null && Directory.Exists(aclLockedDir))
            {
                try
                {
                    using var resetProc = Process.Start(new ProcessStartInfo("icacls.exe")
                    {
                        ArgumentList = { aclLockedDir, "/reset" },
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                        UseShellExecute = false,
                        CreateNoWindow = true,
                    })!;
                    resetProc.WaitForExit(5000);
                }
                catch { /* best effort */ }
            }

            try { Directory.Delete(tempRt, recursive: true); } catch { /* best effort */ }
        }
    }

    /// <summary>
    /// F2-S1-02: proves ExecuteAttemptAsync terminates both the venv launcher and its spawned grandchild
    /// BEFORE awaiting stdio pipe drain whenever a supervision callback throws mid-flight, returning promptly
    /// without hanging on open pipes and propagating the original exception.
    /// </summary>
    [Fact]
    public async Task F2_S1_02_ExecuteAttemptAsync_terminates_launcher_and_grandchild_before_pipe_drain_when_callback_throws()
    {
        var ct = TestContext.Current.CancellationToken;
        var rootDir = Path.Combine(Path.GetTempPath(), $"elc-s1-02-pipe-{Guid.NewGuid():N}");
        var fakeQ0 = Path.Combine(rootDir, "q0");
        var fakeRt = Path.Combine(rootDir, "rt");
        var fakeWorkerRoot = Path.Combine(rootDir, "worker");
        Directory.CreateDirectory(fakeQ0);
        Directory.CreateDirectory(fakeRt);
        Directory.CreateDirectory(Path.Combine(fakeWorkerRoot, "local_ocr"));

        try
        {
            var hostPy = ResolveHostPythonExe();
            using (var venvProc = Process.Start(new ProcessStartInfo(hostPy)
            {
                ArgumentList = { "-m", "venv", "--without-pip", Path.Combine(fakeQ0, "venv") },
                UseShellExecute = false,
                CreateNoWindow = true,
            })!)
            {
                await venvProc.WaitForExitAsync(ct);
                Assert.Equal(0, venvProc.ExitCode);
            }

            Directory.CreateDirectory(Path.Combine(fakeQ0, "models", "Unlimited_OCR_2_04809669"));
            Directory.CreateDirectory(Path.Combine(fakeQ0, "notices", "Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a"));

            // Worker spawns a grandchild python holding inherited stdout/stderr open for 60s.
            const string workerPy = """
                import ctypes, ctypes.wintypes, json, os, pathlib, subprocess, sys, time
                grandchild_code = (
                    "import ctypes, ctypes.wintypes, json, os, pathlib, sys, time\n"
                    "k32 = ctypes.WinDLL('kernel32', use_last_error=True)\n"
                    "k32.GetCurrentProcess.restype = ctypes.wintypes.HANDLE\n"
                    "k32.GetProcessTimes.argtypes = [ctypes.wintypes.HANDLE] + [ctypes.POINTER(ctypes.wintypes.FILETIME)]*4\n"
                    "k32.GetProcessTimes.restype = ctypes.wintypes.BOOL\n"
                    "c, e, kt, ut = ctypes.wintypes.FILETIME(), ctypes.wintypes.FILETIME(), ctypes.wintypes.FILETIME(), ctypes.wintypes.FILETIME()\n"
                    "k32.GetProcessTimes(k32.GetCurrentProcess(), ctypes.byref(c), ctypes.byref(e), ctypes.byref(kt), ctypes.byref(ut))\n"
                    "ft = (int(c.dwHighDateTime) << 32) | int(c.dwLowDateTime)\n"
                    "p = pathlib.Path('output/grandchild.json')\n"
                    "p.write_text(json.dumps({'pid': os.getpid(), 'create_filetime': ft}), encoding='utf-8')\n"
                    "print('grandchild holding pipe', flush=True)\n"
                    "time.sleep(60)\n"
                )
                child = subprocess.Popen([sys.executable, "-c", grandchild_code])
                sys.exit(child.wait())
                """;
            await File.WriteAllTextAsync(Path.Combine(fakeWorkerRoot, "local_ocr", "__init__.py"), string.Empty, ct);
            await File.WriteAllTextAsync(Path.Combine(fakeWorkerRoot, "run_worker.py"), workerPy, ct);

            var (baseSettings, work) = CreatePinnedContext(pageCount: 1);
            var fakeWorkerSha = ExtractionSettings.ComputeWorkerSourceSha256(fakeWorkerRoot);
            var settings = new ExtractionSettings(
                enabled: true,
                maxExtractionPages: 3,
                readOnlyQ0Root: fakeQ0,
                writableRuntimeRoot: fakeRt,
                leasedGpuUuid: "GPU-00000000-0000-0000-0000-000000000000",
                workerRootPath: fakeWorkerRoot,
                modelManifestSha256: baseSettings.ModelManifestSha256,
                dependencyLockSha256: baseSettings.DependencyLockSha256,
                workerSourceSha256: fakeWorkerSha);

            var runner = new LocalPythonOcrWorkerRunner(settings);
            var probe = new WindowsProcessIdentityProbe();
            var grandchildPath = Path.Combine(fakeRt, "runs", work.RunDirectoryName, "output", "grandchild.json");

            int launcherPid = 0;
            long launcherFt = 0;
            OsProcessIdentity grandchild = default;

            var thrown = await Assert.ThrowsAsync<InvalidOperationException>(() =>
                runner.ExecuteAttemptAsync(
                    work,
                    (pid, ft, _) =>
                    {
                        launcherPid = pid;
                        launcherFt = ft;
                        return Task.FromResult(true);
                    },
                    async (_, _, _, innerCt) =>
                    {
                        if (!File.Exists(grandchildPath))
                        {
                            return true;
                        }

                        using var doc = JsonDocument.Parse(await File.ReadAllTextAsync(grandchildPath, innerCt));
                        grandchild = new OsProcessIdentity(
                            doc.RootElement.GetProperty("pid").GetInt32(),
                            doc.RootElement.GetProperty("create_filetime").GetInt64());
                        Assert.True(probe.IsProcessAlive(launcherPid, launcherFt));
                        Assert.True(probe.IsProcessAlive(grandchild.Pid, grandchild.CreateFileTime));
                        throw new InvalidOperationException("Simulated mid-run DB failure");
                    },
                    ct).WaitAsync(TimeSpan.FromSeconds(15), ct));

            Assert.Equal("Simulated mid-run DB failure", thrown.Message);
            Assert.True(grandchild.Pid > 0);
            Assert.False(probe.IsProcessAlive(launcherPid, launcherFt));
            Assert.False(probe.IsProcessAlive(grandchild.Pid, grandchild.CreateFileTime));
        }
        finally
        {
            try { Directory.Delete(rootDir, recursive: true); } catch { /* best effort */ }
        }
    }
}

public sealed class ExternalJobSupervisorHelper
{
    [Fact]
    public async Task RunHelperIfRequested()
    {
        var helperDir = Environment.GetEnvironmentVariable("ELEDGERCARE_JOB_HELPER_DIR");
        var mode = Environment.GetEnvironmentVariable("ELEDGERCARE_JOB_HELPER_MODE");
        if (string.IsNullOrWhiteSpace(helperDir) || string.IsNullOrWhiteSpace(mode))
        {
            // No-op during normal suite execution; active only in the dedicated external helper process.
            return;
        }

        var probe = new WindowsProcessIdentityProbe();
        var supId = probe.GetCurrentProcessIdentity();
        var (launcherScript, _) = WriteLauncherAndGrandchildScripts(helperDir);
        var pythonExe = WorkerEnvelopeAndJobObjectTests.ResolveHostPythonExe();

        using var job = WindowsJobProcess.CreateSuspendedAssigned(
            pythonExe,
            ["-B", launcherScript, helperDir],
            helperDir,
            MinimalWin32Env());

        var grandchild = new OsProcessIdentity(0, 0);
        if (mode == "running")
        {
            job.ResumePrimaryThread();
            grandchild = await WaitForGrandchildAsync(helperDir, TimeSpan.FromSeconds(15));
        }

        var stateTmp = Path.Combine(helperDir, "helper_state.tmp");
        var stateFinal = Path.Combine(helperDir, "helper_state.json");
        var json = JsonSerializer.Serialize(new
        {
            supervisorPid = supId.Pid,
            supervisorCreateFileTime = supId.CreateFileTime,
            launcherPid = job.LauncherIdentity.Pid,
            launcherCreateFileTime = job.LauncherIdentity.CreateFileTime,
            grandchildPid = grandchild.Pid,
            grandchildCreateFileTime = grandchild.CreateFileTime,
        });
        await File.WriteAllTextAsync(stateTmp, json, TestContext.Current.CancellationToken);
        File.Move(stateTmp, stateFinal, overwrite: true);

        // Hold the Job Object handle open until the parent test abruptly kills this process via TerminateProcess.
        await Task.Delay(TimeSpan.FromSeconds(60), TestContext.Current.CancellationToken);
    }

    internal static Dictionary<string, string> MinimalWin32Env()
    {
        var sysRoot = Environment.GetEnvironmentVariable("SystemRoot") ?? @"C:\Windows";
        return new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
        {
            ["SystemRoot"] = sysRoot,
            ["PATH"] = Path.Combine(sysRoot, "System32"),
            ["TEMP"] = Path.GetTempPath(),
            ["TMP"] = Path.GetTempPath(),
        };
    }

    internal static (string LauncherScript, string GrandchildScript) WriteLauncherAndGrandchildScripts(string dir)
    {
        var grandchildPy = Path.Combine(dir, "grandchild.py");
        var launcherPy = Path.Combine(dir, "launcher.py");

        const string grandchildCode = """
            import ctypes, ctypes.wintypes, json, os, pathlib, sys, time
            out_dir = pathlib.Path(sys.argv[1])
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            k32.GetCurrentProcess.restype = ctypes.wintypes.HANDLE
            k32.GetProcessTimes.argtypes = [
                ctypes.wintypes.HANDLE,
                ctypes.POINTER(ctypes.wintypes.FILETIME),
                ctypes.POINTER(ctypes.wintypes.FILETIME),
                ctypes.POINTER(ctypes.wintypes.FILETIME),
                ctypes.POINTER(ctypes.wintypes.FILETIME),
            ]
            k32.GetProcessTimes.restype = ctypes.wintypes.BOOL
            c, e, kt, ut = ctypes.wintypes.FILETIME(), ctypes.wintypes.FILETIME(), ctypes.wintypes.FILETIME(), ctypes.wintypes.FILETIME()
            if not k32.GetProcessTimes(k32.GetCurrentProcess(), ctypes.byref(c), ctypes.byref(e), ctypes.byref(kt), ctypes.byref(ut)):
                raise OSError(ctypes.get_last_error(), "GetProcessTimes failed")
            ft = (int(c.dwHighDateTime) << 32) | int(c.dwLowDateTime)
            tmp = out_dir / "grandchild.tmp"
            final = out_dir / "grandchild.json"
            tmp.write_text(json.dumps({"pid": os.getpid(), "create_filetime": ft}), encoding="utf-8")
            os.replace(tmp, final)
            time.sleep(120)
            """;

        const string launcherCode = """
            import os, pathlib, subprocess, sys
            out_dir = pathlib.Path(sys.argv[1])
            (out_dir / "started.txt").write_text(str(os.getpid()), encoding="utf-8")
            child = subprocess.Popen([sys.executable, "-B", str(out_dir / "grandchild.py"), str(out_dir)])
            sys.exit(child.wait())
            """;

        File.WriteAllText(grandchildPy, grandchildCode, new UTF8Encoding(false));
        File.WriteAllText(launcherPy, launcherCode, new UTF8Encoding(false));
        return (launcherPy, grandchildPy);
    }

    internal static async Task<OsProcessIdentity> WaitForGrandchildAsync(string dir, TimeSpan timeout)
    {
        var path = Path.Combine(dir, "grandchild.json");
        var deadline = DateTime.UtcNow + timeout;
        while (!File.Exists(path))
        {
            if (DateTime.UtcNow > deadline)
            {
                throw new TimeoutException("Timed out waiting for grandchild.json.");
            }

            await Task.Delay(30);
        }

        using var doc = JsonDocument.Parse(await File.ReadAllTextAsync(path));
        return new OsProcessIdentity(
            doc.RootElement.GetProperty("pid").GetInt32(),
            doc.RootElement.GetProperty("create_filetime").GetInt64());
    }
}
