using ELedgerCare.Application.Archive;
using ELedgerCare.Application.Extraction;
using ELedgerCare.Application.Intake;
using ELedgerCare.Application.Review;
using ELedgerCare.Infrastructure.Extraction;
using ELedgerCare.Infrastructure.Pdf;
using ELedgerCare.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace ELedgerCare.Infrastructure;

public static class InfrastructureServices
{
    public static IServiceCollection AddIntakeAndExtractionInfrastructure(
        this IServiceCollection services,
        string runtimeConnectionString,
        ArchiveBackfillOptions? archiveOptions = null)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(runtimeConnectionString);
        var effectiveArchiveOptions = archiveOptions ?? new ArchiveBackfillOptions();

        services.AddDbContextFactory<ELedgerCareDbContext>(options =>
            options.UseNpgsql(runtimeConnectionString, npgsql =>
                npgsql.MigrationsHistoryTable("__ef_migrations_history", ELedgerCareDbContext.Schema)));
        services.AddSingleton(effectiveArchiveOptions);
        services.AddSingleton<IIntakeStore, IntakeStore>();
        services.AddSingleton<IExtractionStore, ExtractionStore>();
        services.AddSingleton<IWorkOrderReviewStore, WorkOrderReviewStore>();
        services.AddSingleton(sp => new ArchiveProjectionInitializer(
            sp.GetRequiredService<IDbContextFactory<ELedgerCareDbContext>>(),
            runtimeConnectionString,
            effectiveArchiveOptions,
            sp.GetRequiredService<TimeProvider>(),
            sp.GetRequiredService<ILogger<ArchiveProjectionInitializer>>()));
        services.AddSingleton<IArchiveProjectionReadiness>(sp => sp.GetRequiredService<ArchiveProjectionInitializer>());
        services.AddSingleton<IArchiveStore>(sp => new ArchiveStore(
            runtimeConnectionString,
            sp.GetRequiredService<ArchiveProjectionInitializer>()));
        services.AddSingleton<IPdfAdmission, PdfPigAdmission>();
        services.AddSingleton<IProcessIdentityProbe, WindowsProcessIdentityProbe>();
        services.AddSingleton<ILocalOcrWorkerRunner, LocalPythonOcrWorkerRunner>();
        return services;
    }
}
