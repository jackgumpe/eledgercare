using System.Runtime.InteropServices;
using ELedgerCare.Application.Extraction;

namespace ELedgerCare.Infrastructure.Extraction;

/// <summary>
/// Queries exact 64-bit Win32 process CreationTime FILETIMEs via PROCESS_QUERY_LIMITED_INFORMATION
/// so recycled OS PIDs are never mistaken for a prior process instance.
/// </summary>
public sealed class WindowsProcessIdentityProbe : IProcessIdentityProbe
{
    private const uint ProcessQueryLimitedInformation = 0x1000;
    private const uint StillActive = 259;

    public OsProcessIdentity GetCurrentProcessIdentity()
    {
        var pid = Environment.ProcessId;
        var handle = GetCurrentProcess();
        if (!GetProcessTimes(handle, out var creation, out _, out _, out _))
        {
            throw new InvalidOperationException($"GetProcessTimes failed for current process (Win32 error {Marshal.GetLastWin32Error()}).");
        }

        return new OsProcessIdentity(pid, creation.ToInt64());
    }

    public bool IsProcessAlive(int pid, long expectedCreateFileTime)
    {
        if (pid <= 0 || expectedCreateFileTime <= 0)
        {
            return false;
        }

        var hProcess = OpenProcess(ProcessQueryLimitedInformation, bInheritHandle: false, (uint)pid);
        if (hProcess == IntPtr.Zero)
        {
            return false;
        }

        try
        {
            if (!GetProcessTimes(hProcess, out var creation, out _, out _, out _))
            {
                return false;
            }

            if (creation.ToInt64() != expectedCreateFileTime)
            {
                return false;
            }

            return GetExitCodeProcess(hProcess, out var exitCode) && exitCode == StillActive;
        }
        finally
        {
            _ = CloseHandle(hProcess);
        }
    }

    public static bool TryGetProcessCreateFileTime(int pid, out long createFileTime)
    {
        createFileTime = 0;
        if (pid <= 0)
        {
            return false;
        }

        var hProcess = OpenProcess(ProcessQueryLimitedInformation, bInheritHandle: false, (uint)pid);
        if (hProcess == IntPtr.Zero)
        {
            return false;
        }

        try
        {
            if (!GetProcessTimes(hProcess, out var creation, out _, out _, out _))
            {
                return false;
            }

            createFileTime = creation.ToInt64();
            return createFileTime > 0;
        }
        finally
        {
            _ = CloseHandle(hProcess);
        }
    }

    [StructLayout(LayoutKind.Sequential)]
    internal readonly struct FileTime(uint low, uint high)
    {
        public readonly uint LowDateTime = low;
        public readonly uint HighDateTime = high;

        public long ToInt64() => ((long)HighDateTime << 32) | LowDateTime;
    }

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [DllImport("kernel32.dll")]
    private static extern IntPtr GetCurrentProcess();

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr OpenProcess(uint dwDesiredAccess, [MarshalAs(UnmanagedType.Bool)] bool bInheritHandle, uint dwProcessId);

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    internal static extern bool GetProcessTimes(
        IntPtr hProcess,
        out FileTime lpCreationTime,
        out FileTime lpExitTime,
        out FileTime lpKernelTime,
        out FileTime lpUserTime);

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    internal static extern bool GetExitCodeProcess(IntPtr hProcess, out uint lpExitCode);

    [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    internal static extern bool CloseHandle(IntPtr hObject);
}
