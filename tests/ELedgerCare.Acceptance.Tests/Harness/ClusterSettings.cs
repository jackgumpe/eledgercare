using System.Text.Json;

namespace ELedgerCare.Acceptance.Tests.Harness;

/// <summary>
/// Connection settings for the worktree-owned local PostgreSQL cluster created by
/// deploy/dev/postgres/setup-cluster.ps1. Missing settings fail the tests (they never skip),
/// so absent infrastructure cannot masquerade as a pass.
/// </summary>
public sealed record ClusterSettings(
    string Host,
    int Port,
    string AdminUser,
    string AdminPassword,
    string MigratorUser,
    string MigratorPassword,
    string AppUser,
    string AppPassword)
{
    public const string SettingsVariable = "ELEDGERCARE_PG_SETTINGS";

    public static ClusterSettings Load()
    {
        var path = Environment.GetEnvironmentVariable(SettingsVariable)
            ?? Path.Combine(RepositoryPaths.Root, ".local", "secrets", "pg-local.json");
        if (!File.Exists(path))
        {
            throw new InvalidOperationException(
                $"PostgreSQL settings not found at '{path}'. Run deploy/dev/postgres/setup-cluster.ps1 first " +
                $"or set {SettingsVariable}. These acceptance tests require a real PostgreSQL cluster.");
        }

        using var json = JsonDocument.Parse(File.ReadAllText(path));
        var root = json.RootElement;
        string Text(string name) => root.GetProperty(name).GetString()
            ?? throw new InvalidOperationException($"Missing '{name}' in {path}.");
        return new ClusterSettings(
            Text("host"),
            root.GetProperty("port").GetInt32(),
            Text("adminUser"),
            Text("adminPassword"),
            Text("migratorUser"),
            Text("migratorPassword"),
            Text("appUser"),
            Text("appPassword"));
    }

    public string ConnectionString(string user, string password, string database) =>
        $"Host={Host};Port={Port};Database={database};Username={user};Password={password};Pooling=false;Timeout=15";

    public string Admin(string database = "postgres") => ConnectionString(AdminUser, AdminPassword, database);

    public string Migrator(string database) => ConnectionString(MigratorUser, MigratorPassword, database);

    public string App(string database) => ConnectionString(AppUser, AppPassword, database);
}

public static class RepositoryPaths
{
    public static string Root { get; } = FindRoot();

    public static string Configuration { get; } =
        AppContext.BaseDirectory.Contains($"{Path.DirectorySeparatorChar}Release{Path.DirectorySeparatorChar}", StringComparison.OrdinalIgnoreCase)
            ? "Release"
            : "Debug";

    public static string ApiAssembly => Path.Combine(Root, "src", "ELedgerCare.Api", "bin", Configuration, "net10.0", "ELedgerCare.Api.dll");

    private static string FindRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null && !File.Exists(Path.Combine(directory.FullName, "ELedgerCare.slnx")))
        {
            directory = directory.Parent;
        }

        return directory?.FullName ?? throw new InvalidOperationException("Repository root (ELedgerCare.slnx) not found.");
    }
}
