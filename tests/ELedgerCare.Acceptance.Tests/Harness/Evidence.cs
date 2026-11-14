using System.Text.Json;
using System.Text.Json.Nodes;
using Xunit;

namespace ELedgerCare.Acceptance.Tests.Harness;

/// <summary>
/// Appends compact structured evidence (process ownership, statuses, lock observations) to a JSON-lines
/// file and the test output. Contains no credentials or document contents.
/// </summary>
public static class Evidence
{
    public const string FileVariable = "ELEDGERCARE_EVIDENCE_FILE";
    private static readonly Lock Gate = new();

    public static void Record(string check, object data)
    {
        var node = new JsonObject
        {
            ["utc"] = DateTime.UtcNow.ToString("O", System.Globalization.CultureInfo.InvariantCulture),
            ["check"] = check,
            ["data"] = JsonSerializer.SerializeToNode(data),
        };
        var line = node.ToJsonString();
        TestContext.Current.TestOutputHelper?.WriteLine(line);

        var path = Environment.GetEnvironmentVariable(FileVariable);
        if (string.IsNullOrWhiteSpace(path))
        {
            return;
        }

        lock (Gate)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
            File.AppendAllText(path, line + Environment.NewLine);
        }
    }
}
