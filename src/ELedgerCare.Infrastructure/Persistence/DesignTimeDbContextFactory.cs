using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace ELedgerCare.Infrastructure.Persistence;

/// <summary>
/// Used only by the project-local dotnet-ef tool. Migrations are applied explicitly with the
/// separate migration role; the application never migrates on startup.
/// The connection string comes from the process environment, never from source control.
/// </summary>
public sealed class DesignTimeDbContextFactory : IDesignTimeDbContextFactory<ELedgerCareDbContext>
{
    public const string MigrationConnectionVariable = "ELEDGERCARE_MIGRATION_CONNECTION";

    public ELedgerCareDbContext CreateDbContext(string[] args)
    {
        // Generating a migration needs no server; applying one requires the variable.
        var connectionString = Environment.GetEnvironmentVariable(MigrationConnectionVariable)
            ?? "Host=127.0.0.1;Port=1;Database=design_time_only";
        var options = new DbContextOptionsBuilder<ELedgerCareDbContext>()
            .UseNpgsql(connectionString, npgsql =>
                npgsql.MigrationsHistoryTable("__ef_migrations_history", ELedgerCareDbContext.Schema))
            .Options;
        return new ELedgerCareDbContext(options);
    }
}
