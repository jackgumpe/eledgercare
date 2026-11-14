using ELedgerCare.Application.Intake;
using ELedgerCare.Infrastructure.Pdf;
using ELedgerCare.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;

namespace ELedgerCare.Infrastructure;

public static class InfrastructureServices
{
    public static IServiceCollection AddIntakeInfrastructure(this IServiceCollection services, string runtimeConnectionString)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(runtimeConnectionString);
        services.AddDbContextFactory<ELedgerCareDbContext>(options =>
            options.UseNpgsql(runtimeConnectionString, npgsql =>
                npgsql.MigrationsHistoryTable("__ef_migrations_history", ELedgerCareDbContext.Schema)));
        services.AddSingleton<IIntakeStore, IntakeStore>();
        services.AddSingleton<IPdfAdmission, PdfPigAdmission>();
        return services;
    }
}
