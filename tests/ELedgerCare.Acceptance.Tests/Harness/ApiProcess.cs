using System.Diagnostics;
using System.Text.RegularExpressions;

namespace ELedgerCare.Acceptance.Tests.Harness;

/// <summary>
/// Launches the built ELedgerCare.Api as a separate OS process bound to an ephemeral loopback port.
/// Only this harness-started process (verified by PID and start time) is ever terminated.
/// </summary>
public sealed partial class ApiProcess : IAsyncDisposable
{
    private readonly Process process;
    private readonly List<string> output = [];
    private readonly TaskCompletionSource<int> listening = new(TaskCreationOptions.RunContinuationsAsynchronously);

    private ApiProcess(Process process)
    {
        this.process = process;
    }

    public int Pid { get; private set; }

    public DateTime StartTimeUtc { get; private set; }

    public int Port { get; private set; }

    public Uri BaseAddress => new($"http://127.0.0.1:{Port}");

    public bool HasExited => process.HasExited;

    public IReadOnlyList<string> Output
    {
        get
        {
            lock (output)
            {
                return [.. output];
            }
        }
    }

    public static async Task<ApiProcess> StartAsync(string runtimeConnectionString, IDictionary<string, string>? extraSettings = null)
    {
        if (!File.Exists(RepositoryPaths.ApiAssembly))
        {
            throw new InvalidOperationException($"Built API not found at {RepositoryPaths.ApiAssembly}; build the solution first.");
        }

        var start = new ProcessStartInfo("dotnet")
        {
            WorkingDirectory = Path.GetDirectoryName(RepositoryPaths.ApiAssembly)!,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        start.ArgumentList.Add(RepositoryPaths.ApiAssembly);
        start.Environment["ASPNETCORE_ENVIRONMENT"] = "Production";
        start.Environment["DOTNET_NOLOGO"] = "1";
        start.Environment["ConnectionStrings__Runtime"] = runtimeConnectionString;
        start.Environment["Api__Port"] = "0";
        start.Environment["Logging__Console__FormatterName"] = "simple";
        foreach (var (key, value) in extraSettings ?? new Dictionary<string, string>())
        {
            start.Environment[key] = value;
        }

        var api = new ApiProcess(new Process { StartInfo = start, EnableRaisingEvents = true });
        api.process.OutputDataReceived += (_, e) => api.OnOutput(e.Data);
        api.process.ErrorDataReceived += (_, e) => api.OnOutput(e.Data);
        api.process.Exited += (_, _) => api.listening.TrySetException(
            new InvalidOperationException("API process exited before listening:\n" + string.Join('\n', api.Output)));
        api.process.Start();
        api.Pid = api.process.Id;
        api.StartTimeUtc = api.process.StartTime.ToUniversalTime();
        api.process.BeginOutputReadLine();
        api.process.BeginErrorReadLine();

        api.Port = await api.listening.Task.WaitAsync(TimeSpan.FromSeconds(60));
        return api;
    }

    public HttpClient CreateClient() => new() { BaseAddress = BaseAddress, Timeout = TimeSpan.FromSeconds(60) };

    /// <summary>
    /// Abruptly terminates exactly this harness-owned process (TerminateProcess), after re-verifying its
    /// identity by PID and start time, and waits for exit. No graceful shutdown or flush runs.
    /// </summary>
    public async Task KillAsync()
    {
        if (process.HasExited)
        {
            return;
        }

        using var current = Process.GetProcessById(Pid);
        if (current.StartTime.ToUniversalTime() != StartTimeUtc)
        {
            throw new InvalidOperationException($"PID {Pid} no longer identifies the harness-started API process; not terminating.");
        }

        process.Kill(entireProcessTree: false);
        await process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(30));
    }

    public async ValueTask DisposeAsync()
    {
        await KillAsync();
        process.Dispose();
    }

    private void OnOutput(string? line)
    {
        if (line is null)
        {
            return;
        }

        lock (output)
        {
            output.Add(line);
        }

        var match = ListeningPattern().Match(line);
        if (match.Success)
        {
            listening.TrySetResult(int.Parse(match.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture));
        }
    }

    [GeneratedRegex(@"Now listening on: http://127\.0\.0\.1:(\d+)")]
    private static partial Regex ListeningPattern();
}
