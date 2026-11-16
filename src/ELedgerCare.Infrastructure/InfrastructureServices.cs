using ELedgerCare.Application.Extraction;
using ELedgerCare.Application.Intake;
using ELedgerCare.Application.Review;
using ELedgerCare.Infrastructure.Extraction;
using ELedgerCare.Infrastructure.Pdf;
using ELedgerCare.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;

namespace ELedgerCare.Infrastructure;

public static class InfrastructureServices
{
    public static IServiceCollection AddIntakeAndExtractionInfrastructure(
        this IServiceCollection services,
        string runtimeConnectionString)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(runtimeConnectionString);
        services.AddDbContextFactory<ELedgerCareDbContext>(options =>
            options.UseNpgsql(runtimeConnectionString, npgsql =>
                npgsql.MigrationsHistoryTable("__ef_migrations_history", ELedgerCareDbContext.Schema)));
        services.AddSingleton<IIntakeStore, IntakeStore>();
        services.AddSingleton<IExtractionStore, ExtractionStore>();
        services.AddSingleton<IWorkOrderReviewStore, WorkOrderReviewStore>();
        services.AddSingleton<IPdfAdmission, PdfPigAdmission>();
        services.AddSingleton<IProcessIdentityProbe, WindowsProcessIdentityProbe>();
        services.AddSingleton<ILocalOcrWorkerRunner, LocalPythonOcrWorkerRunner>();
        return services;
    }
}
