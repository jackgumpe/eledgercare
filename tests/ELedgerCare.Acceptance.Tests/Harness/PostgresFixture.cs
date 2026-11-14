using ELedgerCare.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;
using Npgsql;
using Xunit;

namespace ELedgerCare.Acceptance.Tests.Harness;

/// <summary>
/// Once per test run: verifies the cluster's durability settings, then builds a migrated template
/// database (explicit migration with the migration role, followed by the runtime grants script).
/// Each test clones a fresh, disposable database from it.
/// </summary>
public sealed class PostgresFixture : IAsyncLifetime
{
    private readonly string runId = Guid.NewGuid().ToString("N")[..10];

    public ClusterSettings Settings { get; } = ClusterSettings.Load();

    public string TemplateDatabase => $"eledgercare_test_tpl_{runId}";

    public IReadOnlyDictionary<string, string> ServerSettings { get; private set; } = new Dictionary<string, string>();

    public async ValueTask InitializeAsync()
    {
        await using (var admin = await OpenAsync(Settings.Admin()))
        {
            ServerSettings = await ReadServerSettingsAsync(admin);
            foreach (var name in new[] { "fsync", "full_page_writes", "synchronous_commit" })
            {
                if (ServerSettings[name] != "on")
                {
                    throw new InvalidOperationException($"Durability qualification failed: {name}={ServerSettings[name]} (must be on).");
                }
            }

            await ExecuteAsync(admin, $"CREATE DATABASE {TemplateDatabase} OWNER {Settings.MigratorUser} ENCODING 'UTF8' TEMPLATE template0");
            await ExecuteAsync(admin, $"REVOKE ALL ON DATABASE {TemplateDatabase} FROM PUBLIC");
        }

        await using (var templateAdmin = await OpenAsync(Settings.Admin(TemplateDatabase)))
        {
            await ExecuteAsync(templateAdmin, "REVOKE ALL ON SCHEMA public FROM PUBLIC");
        }

        var options = new DbContextOptionsBuilder<ELedgerCareDbContext>()
            .UseNpgsql(Settings.Migrator(TemplateDatabase), npgsql =>
                npgsql.MigrationsHistoryTable("__ef_migrations_history", ELedgerCareDbContext.Schema))
            .Options;
        await using (var migrationContext = new ELedgerCareDbContext(options))
        {
            await migrationContext.Database.MigrateAsync();
        }

        await using (var migrator = await OpenAsync(Settings.Migrator(TemplateDatabase)))
        {
            var grants = await File.ReadAllTextAsync(Path.Combine(RepositoryPaths.Root, "deploy", "dev", "database", "grant-runtime.sql"));
            await ExecuteAsync(migrator, grants);
        }
    }

    public async ValueTask DisposeAsync()
    {
        await using var admin = await OpenAsync(Settings.Admin());
        await ExecuteAsync(admin, $"DROP DATABASE IF EXISTS {TemplateDatabase} WITH (FORCE)");
    }

    public async Task<TestDatabase> CreateDatabaseAsync()
    {
        var name = $"eledgercare_test_{runId}_{Guid.NewGuid().ToString("N")[..8]}";
        await using var admin = await OpenAsync(Settings.Admin());
        await ExecuteAsync(admin, $"CREATE DATABASE {name} TEMPLATE {TemplateDatabase} OWNER {Settings.MigratorUser}");
        await ExecuteAsync(admin, $"REVOKE ALL ON DATABASE {name} FROM PUBLIC");
        await ExecuteAsync(admin, $"GRANT CONNECT ON DATABASE {name} TO {Settings.AppUser}");
        return new TestDatabase(this, name);
    }

    public static async Task<NpgsqlConnection> OpenAsync(string connectionString)
    {
        var connection = new NpgsqlConnection(connectionString);
        await connection.OpenAsync();
        return connection;
    }

    public static async Task ExecuteAsync(NpgsqlConnection connection, string sql)
    {
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    private static async Task<IReadOnlyDictionary<string, string>> ReadServerSettingsAsync(NpgsqlConnection connection)
    {
        const string sql = """
            SELECT name, setting FROM pg_settings
            WHERE name IN ('server_version', 'fsync', 'full_page_writes', 'synchronous_commit', 'listen_addresses',
                           'port', 'password_encryption', 'wal_level', 'data_checksums', 'default_transaction_isolation')
            """;
        var settings = new Dictionary<string, string>();
        await using var command = new NpgsqlCommand(sql, connection);
        await using var reader = await command.ExecuteReaderAsync();
        while (await reader.ReadAsync())
        {
            settings[reader.GetString(0)] = reader.GetString(1);
        }

        return settings;
    }
}

[CollectionDefinition(Name)]
public sealed class PostgresCollection : ICollectionFixture<PostgresFixture>
{
    public const string Name = "real-postgresql";
}

/// <summary>A disposable owned database cloned from the migrated template.</summary>
public sealed class TestDatabase(PostgresFixture fixture, string name) : IAsyncDisposable
{
    public string Name { get; } = name;

    public string AppConnectionString => fixture.Settings.App(Name);

    public Task<NpgsqlConnection> OpenAdminAsync() => PostgresFixture.OpenAsync(fixture.Settings.Admin(Name));

    public Task<NpgsqlConnection> OpenAppAsync() => PostgresFixture.OpenAsync(fixture.Settings.App(Name));

    public async Task<long> ScalarAsync(string sql, params (string Name, object Value)[] parameters)
    {
        await using var connection = await OpenAdminAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        foreach (var (parameterName, value) in parameters)
        {
            command.Parameters.AddWithValue(parameterName, value);
        }

        return Convert.ToInt64(await command.ExecuteScalarAsync(), System.Globalization.CultureInfo.InvariantCulture);
    }

    /// <summary>Row counts in all three F1 tables.</summary>
    public async Task<(long Documents, long Originals, long Jobs)> CountRowsAsync() => (
        await ScalarAsync("SELECT count(*) FROM eledgercare.documents"),
        await ScalarAsync("SELECT count(*) FROM eledgercare.original_artifacts"),
        await ScalarAsync("SELECT count(*) FROM eledgercare.processing_jobs"));

    public async ValueTask DisposeAsync()
    {
        await using var admin = await PostgresFixture.OpenAsync(fixture.Settings.Admin());
        await PostgresFixture.ExecuteAsync(admin, $"DROP DATABASE IF EXISTS {Name} WITH (FORCE)");
    }
}
