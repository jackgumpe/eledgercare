using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;
using ELedgerCare.Application.Extraction;
using Microsoft.Win32.SafeHandles;

namespace ELedgerCare.Infrastructure.Extraction;

/// <summary>
/// Race-free Windows Job Object process launcher and lifetime container:
///   1. Creates a non-inheritable Job Object configured with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE (no breakaway).
///   2. Spawns the child via CreateProcessW with CREATE_SUSPENDED and PROC_THREAD_ATTRIBUTE_HANDLE_LIST
///      inheriting ONLY [stdin=NUL, stdoutPipe, stderrPipe] (never the job handle or server sockets).
///   3. Assigns the suspended process to the Job Object and records its (PID, CreationTime) BEFORE ResumeThread,
///      so zero instructions can execute and zero grandchildren can spawn outside the Job Object.
///   4. When disposed, terminated, or if the owning .NET process dies abruptly via TerminateProcess,
///      the Windows kernel closes the Job Object handle and terminates both launcher and all descendants.
/// </summary>
public sealed partial class WindowsJobProcess : IDisposable
{
    private const uint CreateSuspended = 0x00000004;
    private const uint CreateNewProcessGroup = 0x00000200;
    private const uint CreateUnicodeEnvironment = 0x00000400;
    private const uint ExtendedStartupInfoPresent = 0x00080000;
    private const uint CreateNoWindow = 0x08000000;

    private const uint JobObjectLimitKillOnJobClose = 0x00002000;
    private const int JobObjectBasicProcessIdList = 3;
    private const int JobObjectExtendedLimitInformation = 9;

    private const int ProcThreadAttributeHandleList = 0x00020002;
    private const uint GenericRead = 0x80000000;
    private const uint OpenExisting = 3;
    private const uint FileShareReadWrite = 0x00000001 | 0x00000002;
    private const uint HandleFlagInherit = 0x00000001;
    private const uint WaitObject0 = 0x00000000;

    private IntPtr jobHandle;
    private IntPtr processHandle;
    private IntPtr primaryThreadHandle;
    private SafeFileHandle? stdoutReadHandle;
    private SafeFileHandle? stderrReadHandle;
    private bool resumed;
    private bool disposed;

    private WindowsJobProcess(
        IntPtr jobHandle,
        IntPtr processHandle,
        IntPtr primaryThreadHandle,
        OsProcessIdentity launcherIdentity,
        SafeFileHandle stdoutReadHandle,
        SafeFileHandle stderrReadHandle)
    {
        this.jobHandle = jobHandle;
        this.processHandle = processHandle;
        this.primaryThreadHandle = primaryThreadHandle;
        LauncherIdentity = launcherIdentity;
        this.stdoutReadHandle = stdoutReadHandle;
        this.stderrReadHandle = stderrReadHandle;
    }

    public OsProcessIdentity LauncherIdentity { get; }

    public bool IsResumed => resumed;

    public static WindowsJobProcess CreateSuspendedAssigned(
        string executablePath,
        IReadOnlyList<string> arguments,
        string workingDirectory,
        IReadOnlyDictionary<string, string> environment)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(executablePath);
        ArgumentNullException.ThrowIfNull(arguments);
        ArgumentException.ThrowIfNullOrWhiteSpace(workingDirectory);
        ArgumentNullException.ThrowIfNull(environment);

        if (!Path.IsPathFullyQualified(executablePath) || !File.Exists(executablePath))
        {
            throw new FileNotFoundException("Worker executable path must exist and be fully qualified.", executablePath);
        }

        // 1. Non-inheritable Job Object with KILL_ON_JOB_CLOSE and zero breakaway flags.
        var hJob = CreateJobObjectW(IntPtr.Zero, null);
        if (hJob == IntPtr.Zero)
        {
            throw new Win32Exception(Marshal.GetLastWin32Error(), "CreateJobObjectW failed.");
        }

        var hStdoutRead = IntPtr.Zero;
        var hStdoutWrite = IntPtr.Zero;
        var hStderrRead = IntPtr.Zero;
        var hStderrWrite = IntPtr.Zero;
        var hStdinNull = IntPtr.Zero;
        var attrListBuffer = IntPtr.Zero;
        var handlesBuffer = IntPtr.Zero;

        try
        {
            var extendedInfo = new JobObjectExtendedLimitInfo
            {
                BasicLimitInformation = new JobObjectBasicLimitInfo
                {
                    LimitFlags = JobObjectLimitKillOnJobClose,
                },
            };

            if (!SetInformationJobObject(
                hJob,
                JobObjectExtendedLimitInformation,
                ref extendedInfo,
                Marshal.SizeOf<JobObjectExtendedLimitInfo>()))
            {
                throw new Win32Exception(Marshal.GetLastWin32Error(), "SetInformationJobObject(KILL_ON_JOB_CLOSE) failed.");
            }

            // 2. Create stdio pipes: only child ends are inheritable, and PROC_THREAD_ATTRIBUTE_HANDLE_LIST
            // restricts inheritance strictly to [hStdinNull, hStdoutWrite, hStderrWrite].
            var inheritableSa = new SecurityAttributes
            {
                nLength = Marshal.SizeOf<SecurityAttributes>(),
                bInheritHandle = 1,
            };

            if (!CreatePipe(out hStdoutRead, out hStdoutWrite, ref inheritableSa, 0) ||
                !SetHandleInformation(hStdoutRead, HandleFlagInherit, 0))
            {
                throw new Win32Exception(Marshal.GetLastWin32Error(), "Failed creating stdout pipe.");
            }

            if (!CreatePipe(out hStderrRead, out hStderrWrite, ref inheritableSa, 0) ||
                !SetHandleInformation(hStderrRead, HandleFlagInherit, 0))
            {
                throw new Win32Exception(Marshal.GetLastWin32Error(), "Failed creating stderr pipe.");
            }

            hStdinNull = CreateFileW("NUL", GenericRead, FileShareReadWrite, ref inheritableSa, OpenExisting, 0, IntPtr.Zero);
            if (hStdinNull == IntPtr.Zero || hStdinNull == new IntPtr(-1))
            {
                hStdinNull = IntPtr.Zero;
                throw new Win32Exception(Marshal.GetLastWin32Error(), "Failed opening NUL for child stdin.");
            }

            nuint attrSize = 0;
            _ = InitializeProcThreadAttributeList(IntPtr.Zero, 1, 0, ref attrSize);
            attrListBuffer = Marshal.AllocHGlobal((nint)attrSize);
            if (!InitializeProcThreadAttributeList(attrListBuffer, 1, 0, ref attrSize))
            {
                throw new Win32Exception(Marshal.GetLastWin32Error(), "InitializeProcThreadAttributeList failed.");
            }

            handlesBuffer = Marshal.AllocHGlobal(IntPtr.Size * 3);
            Marshal.WriteIntPtr(handlesBuffer, 0, hStdinNull);
            Marshal.WriteIntPtr(handlesBuffer, IntPtr.Size, hStdoutWrite);
            Marshal.WriteIntPtr(handlesBuffer, IntPtr.Size * 2, hStderrWrite);

            if (!UpdateProcThreadAttribute(
                attrListBuffer,
                0,
                (IntPtr)ProcThreadAttributeHandleList,
                handlesBuffer,
                (nuint)(IntPtr.Size * 3),
                IntPtr.Zero,
                IntPtr.Zero))
            {
                throw new Win32Exception(Marshal.GetLastWin32Error(), "UpdateProcThreadAttribute(HANDLE_LIST) failed.");
            }

            var startupInfoEx = new StartupInfoEx
            {
                StartupInfo = new StartupInfo
                {
                    cb = Marshal.SizeOf<StartupInfoEx>(),
                    dwFlags = 0x00000100, // STARTF_USESTDHANDLES
                    hStdInput = hStdinNull,
                    hStdOutput = hStdoutWrite,
                    hStdError = hStderrWrite,
                },
                lpAttributeList = attrListBuffer,
            };

            var commandLine = BuildWindowsCommandLine(executablePath, arguments);
            var cmdBuffer = new StringBuilder(commandLine);
            var envBlock = BuildUnicodeEnvironmentBlock(environment);

            // 3. CreateProcessW with CREATE_SUSPENDED: primary thread has executed 0 instructions.
            var created = CreateProcessW(
                executablePath,
                cmdBuffer,
                IntPtr.Zero,
                IntPtr.Zero,
                bInheritHandles: true,
                CreateSuspended | CreateUnicodeEnvironment | CreateNoWindow | CreateNewProcessGroup | ExtendedStartupInfoPresent,
                envBlock,
                workingDirectory,
                ref startupInfoEx,
                out var procInfo);

            if (!created)
            {
                throw new Win32Exception(Marshal.GetLastWin32Error(), "CreateProcessW(CREATE_SUSPENDED) failed.");
            }

            try
            {
                if (!WindowsProcessIdentityProbe.GetProcessTimes(procInfo.hProcess, out var creationFt, out _, out _, out _))
                {
                    throw new Win32Exception(Marshal.GetLastWin32Error(), "GetProcessTimes on suspended child failed.");
                }

                // 4. Assign to Job Object BEFORE ResumeThread: race-free containment of launcher + all future descendants.
                if (!AssignProcessToJobObject(hJob, procInfo.hProcess))
                {
                    var err = Marshal.GetLastWin32Error();
                    _ = TerminateProcess(procInfo.hProcess, 1);
                    throw new Win32Exception(err, "AssignProcessToJobObject failed on suspended child.");
                }

                // Child-side pipe ends are now duplicated into the suspended child; close our copies so EOF is observed on exit.
                CloseIfValid(ref hStdinNull);
                CloseIfValid(ref hStdoutWrite);
                CloseIfValid(ref hStderrWrite);

                var launcherIdentity = new OsProcessIdentity((int)procInfo.dwProcessId, creationFt.ToInt64());
                var outSafe = new SafeFileHandle(hStdoutRead, ownsHandle: true);
                hStdoutRead = IntPtr.Zero;
                var errSafe = new SafeFileHandle(hStderrRead, ownsHandle: true);
                hStderrRead = IntPtr.Zero;
                var result = new WindowsJobProcess(
                    hJob,
                    procInfo.hProcess,
                    procInfo.hThread,
                    launcherIdentity,
                    outSafe,
                    errSafe);
                hJob = IntPtr.Zero;
                return result;
            }
            catch
            {
                _ = TerminateProcess(procInfo.hProcess, 1);
                _ = WindowsProcessIdentityProbe.CloseHandle(procInfo.hThread);
                _ = WindowsProcessIdentityProbe.CloseHandle(procInfo.hProcess);
                throw;
            }
        }
        finally
        {
            if (attrListBuffer != IntPtr.Zero)
            {
                DeleteProcThreadAttributeList(attrListBuffer);
                Marshal.FreeHGlobal(attrListBuffer);
            }

            if (handlesBuffer != IntPtr.Zero)
            {
                Marshal.FreeHGlobal(handlesBuffer);
            }

            CloseIfValid(ref hStdinNull);
            CloseIfValid(ref hStdoutWrite);
            CloseIfValid(ref hStderrWrite);
            CloseIfValid(ref hStdoutRead);
            CloseIfValid(ref hStderrRead);
            CloseIfValid(ref hJob);
        }
    }

    public void ResumePrimaryThread()
    {
        ObjectDisposedException.ThrowIf(disposed, this);
        if (resumed)
        {
            throw new InvalidOperationException("Primary thread was already resumed.");
        }

        var prevSuspendCount = ResumeThread(primaryThreadHandle);
        if (prevSuspendCount == uint.MaxValue)
        {
            throw new Win32Exception(Marshal.GetLastWin32Error(), "ResumeThread failed.");
        }

        resumed = true;
        CloseIfValid(ref primaryThreadHandle);
    }

    public Stream OpenStandardOutputReadStream()
    {
        ObjectDisposedException.ThrowIf(disposed, this);
        var handle = stdoutReadHandle ?? throw new InvalidOperationException("Stdout stream already opened.");
        stdoutReadHandle = null;
        return new FileStream(handle, FileAccess.Read, bufferSize: 8192, isAsync: false);
    }

    public Stream OpenStandardErrorReadStream()
    {
        ObjectDisposedException.ThrowIf(disposed, this);
        var handle = stderrReadHandle ?? throw new InvalidOperationException("Stderr stream already opened.");
        stderrReadHandle = null;
        return new FileStream(handle, FileAccess.Read, bufferSize: 8192, isAsync: false);
    }

    public bool TryGetLauncherExitCode(out int exitCode)
    {
        exitCode = -1;
        if (disposed || processHandle == IntPtr.Zero)
        {
            return true;
        }

        if (WaitForSingleObject(processHandle, 0) != WaitObject0)
        {
            return false;
        }

        if (WindowsProcessIdentityProbe.GetExitCodeProcess(processHandle, out var raw))
        {
            exitCode = unchecked((int)raw);
        }

        return true;
    }

    /// <summary>
    /// Queries the kernel Job Object directly for every live PID inside the job (launcher + actual CUDA worker),
    /// paired with each process's exact CreationTime FILETIME.
    /// </summary>
    public IReadOnlyList<OsProcessIdentity> QueryActiveJobProcesses()
    {
        if (disposed || jobHandle == IntPtr.Zero)
        {
            return [];
        }

        const int maxPids = 64;
        var size = (sizeof(uint) * 2) + (IntPtr.Size * maxPids);
        var buffer = Marshal.AllocHGlobal(size);
        try
        {
            if (!QueryInformationJobObject(jobHandle, JobObjectBasicProcessIdList, buffer, size, out _))
            {
                return [];
            }

            var assigned = Marshal.ReadInt32(buffer, sizeof(uint));
            var count = Math.Clamp(assigned, 0, maxPids);
            var list = new List<OsProcessIdentity>(count);
            for (var i = 0; i < count; i++)
            {
                var pidPtr = Marshal.ReadIntPtr(buffer, (sizeof(uint) * 2) + (i * IntPtr.Size));
                var pid = (int)pidPtr.ToInt64();
                if (WindowsProcessIdentityProbe.TryGetProcessCreateFileTime(pid, out var ft))
                {
                    list.Add(new OsProcessIdentity(pid, ft));
                }
            }

            return list;
        }
        finally
        {
            Marshal.FreeHGlobal(buffer);
        }
    }

    public void TerminateAllInJob(uint exitCode = 1)
    {
        if (jobHandle != IntPtr.Zero)
        {
            _ = TerminateJobObject(jobHandle, exitCode);
        }
    }

    public async Task WaitForAllJobProcessesExitAsync(TimeSpan timeout)
    {
        var deadline = DateTime.UtcNow + timeout;
        while (DateTime.UtcNow < deadline)
        {
            if (QueryActiveJobProcesses().Count == 0 && TryGetLauncherExitCode(out _))
            {
                return;
            }

            await Task.Delay(50).ConfigureAwait(false);
        }
    }

    public void Dispose()
    {
        if (disposed)
        {
            return;
        }

        disposed = true;
        if (jobHandle != IntPtr.Zero)
        {
            _ = TerminateJobObject(jobHandle, 1);
        }

        stdoutReadHandle?.Dispose();
        stderrReadHandle?.Dispose();
        CloseIfValid(ref primaryThreadHandle);
        CloseIfValid(ref processHandle);
        CloseIfValid(ref jobHandle);
    }

    internal static string BuildWindowsCommandLine(string executablePath, IReadOnlyList<string> arguments)
    {
        var sb = new StringBuilder();
        AppendQuotedArg(sb, executablePath);
        foreach (var arg in arguments)
        {
            sb.Append(' ');
            AppendQuotedArg(sb, arg);
        }

        return sb.ToString();
    }

    private static void AppendQuotedArg(StringBuilder sb, string arg)
    {
        if (arg.Length > 0 && !arg.Any(c => c is ' ' or '\t' or '\n' or '\v' or '"'))
        {
            sb.Append(arg);
            return;
        }

        sb.Append('"');
        var backslashes = 0;
        foreach (var ch in arg)
        {
            if (ch == '\\')
            {
                backslashes++;
            }
            else if (ch == '"')
            {
                sb.Append('\\', (backslashes * 2) + 1);
                sb.Append('"');
                backslashes = 0;
            }
            else
            {
                if (backslashes > 0)
                {
                    sb.Append('\\', backslashes);
                    backslashes = 0;
                }

                sb.Append(ch);
            }
        }

        if (backslashes > 0)
        {
            sb.Append('\\', backslashes * 2);
        }

        sb.Append('"');
    }

    private static byte[] BuildUnicodeEnvironmentBlock(IReadOnlyDictionary<string, string> environment)
    {
        var sb = new StringBuilder();
        foreach (var kv in environment.OrderBy(k => k.Key, StringComparer.OrdinalIgnoreCase))
        {
            if (kv.Key.Contains('=', StringComparison.Ordinal) || kv.Key.Contains('\0', StringComparison.Ordinal) ||
                kv.Value.Contains('\0', StringComparison.Ordinal))
            {
                throw new ArgumentException($"Invalid environment entry key '{kv.Key}'.");
            }

            sb.Append(kv.Key).Append('=').Append(kv.Value).Append('\0');
        }

        sb.Append('\0');
        return Encoding.Unicode.GetBytes(sb.ToString());
    }

    private static void CloseIfValid(ref IntPtr handle)
    {
        if (handle != IntPtr.Zero && handle != new IntPtr(-1))
        {
            _ = WindowsProcessIdentityProbe.CloseHandle(handle);
        }

        handle = IntPtr.Zero;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct SecurityAttributes
    {
        public int nLength;
        public IntPtr lpSecurityDescriptor;
        public int bInheritHandle;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct StartupInfo
    {
        public int cb;
        public IntPtr lpReserved;
        public IntPtr lpDesktop;
        public IntPtr lpTitle;
        public int dwX;
        public int dwY;
        public int dwXSize;
        public int dwYSize;
        public int dwXCountChars;
        public int dwYCountChars;
        public int dwFillAttribute;
        public int dwFlags;
        public short wShowWindow;
        public short cbReserved2;
        public IntPtr lpReserved2;
        public IntPtr hStdInput;
        public IntPtr hStdOutput;
        public IntPtr hStdError;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct StartupInfoEx
    {
        public StartupInfo StartupInfo;
        public IntPtr lpAttributeList;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct ProcessInformation
    {
        public IntPtr hProcess;
        public IntPtr hThread;
        public uint dwProcessId;
        public uint dwThreadId;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct JobObjectBasicLimitInfo
    {
        public long PerProcessUserTimeLimit;
        public long PerJobUserTimeLimit;
        public uint LimitFlags;
        public nuint MinimumWorkingSetSize;
        public nuint MaximumWorkingSetSize;
        public uint ActiveProcessLimit;
        public nuint Affinity;
        public uint PriorityClass;
        public uint SchedulingClass;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct IoCounters
    {
        public ulong ReadOperationCount;
        public ulong WriteOperationCount;
        public ulong OtherOperationCount;
        public ulong ReadTransferCount;
        public ulong WriteTransferCount;
        public ulong OtherTransferCount;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct JobObjectExtendedLimitInfo
    {
        public JobObjectBasicLimitInfo BasicLimitInformation;
        public IoCounters IoInfo;
        public nuint ProcessMemoryLimit;
        public nuint JobMemoryLimit;
        public nuint PeakProcessMemoryUsed;
        public nuint PeakJobMemoryUsed;
    }

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr CreateJobObjectW(IntPtr lpJobAttributes, string? lpName);

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool SetInformationJobObject(
        IntPtr hJob,
        int infoType,
        ref JobObjectExtendedLimitInfo lpJobObjectInfo,
        int cbJobObjectInfoLength);

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool AssignProcessToJobObject(IntPtr hJob, IntPtr hProcess);

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool TerminateJobObject(IntPtr hJob, uint uExitCode);

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool QueryInformationJobObject(
        IntPtr hJob,
        int jobObjectInformationClass,
        IntPtr lpJobObjectInformation,
        int cbJobObjectInformationLength,
        out int lpReturnLength);

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CreatePipe(
        out IntPtr hReadPipe,
        out IntPtr hWritePipe,
        ref SecurityAttributes lpPipeAttributes,
        uint nSize);

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool SetHandleInformation(IntPtr hObject, uint dwMask, uint dwFlags);

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr CreateFileW(
        string lpFileName,
        uint dwDesiredAccess,
        uint dwShareMode,
        ref SecurityAttributes lpSecurityAttributes,
        uint dwCreationDisposition,
        uint dwFlagsAndAttributes,
        IntPtr hTemplateFile);

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool InitializeProcThreadAttributeList(
        IntPtr lpAttributeList,
        int dwAttributeCount,
        int dwFlags,
        ref nuint lpSize);

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool UpdateProcThreadAttribute(
        IntPtr lpAttributeList,
        uint dwFlags,
        IntPtr attribute,
        IntPtr lpValue,
        nuint cbSize,
        IntPtr lpPreviousValue,
        IntPtr lpReturnSize);

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [DllImport("kernel32.dll")]
    private static extern void DeleteProcThreadAttributeList(IntPtr lpAttributeList);

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CreateProcessW(
        string lpApplicationName,
        StringBuilder lpCommandLine,
        IntPtr lpProcessAttributes,
        IntPtr lpThreadAttributes,
        [MarshalAs(UnmanagedType.Bool)] bool bInheritHandles,
        uint dwCreationFlags,
        byte[] lpEnvironment,
        string lpCurrentDirectory,
        ref StartupInfoEx lpStartupInfo,
        out ProcessInformation lpProcessInformation);

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern uint ResumeThread(IntPtr hThread);

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool TerminateProcess(IntPtr hProcess, uint uExitCode);

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern uint WaitForSingleObject(IntPtr hHandle, uint dwMilliseconds);
}
