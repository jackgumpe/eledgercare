using System.Net;
using System.Threading.RateLimiting;
using ELedgerCare.Api;
using ELedgerCare.Application.Extraction;
using ELedgerCare.Application.Intake;
using ELedgerCare.Infrastructure;
using Microsoft.AspNetCore.RateLimiting;

var builder = WebApplication.CreateBuilder(args);

// Admission limits: validated at startup; values outside 1..10,485,760 bytes or 1..50 pages fail fast.
var intakeOptions = builder.Configuration.GetSection(IntakeOptions.Section).Get<IntakeOptions>() ?? new IntakeOptions();
var limits = new IntakeLimits(intakeOptions.MaxDocumentBytes, intakeOptions.MaxPages);

// Local OCR settings: disabled by default until a bounded coordinator runtime release is configured.
var localOcrOptions = builder.Configuration.GetSection(LocalOcrOptions.Section).Get<LocalOcrOptions>() ?? new LocalOcrOptions();
var extractionSettings = localOcrOptions.BuildValidatedSettings(builder.Environment.ContentRootPath);

// Local-only binding: loopback IPv4 only. Port 0 lets a test harness obtain an ephemeral owned port.
var port = builder.Configuration.GetValue("Api:Port", 5190);
if (port is < 0 or > 65535)
{
    throw new InvalidOperationException("Api:Port must be within 0..65535.");
}

builder.WebHost.UseUrls();
builder.WebHost.ConfigureKestrel(kestrel =>
{
    kestrel.Listen(IPAddress.Loopback, port);
    kestrel.Limits.MaxRequestBodySize = limits.MaxDocumentBytes;
    kestrel.AddServerHeader = false;
});

var runtimeConnection = builder.Configuration.GetConnectionString("Runtime");
if (string.IsNullOrWhiteSpace(runtimeConnection))
{
    throw new InvalidOperationException(
        "ConnectionStrings:Runtime is required (supply it through the environment, never source control).");
}

builder.Services.AddSingleton(limits);
builder.Services.AddSingleton(extractionSettings);
builder.Services.AddSingleton(TimeProvider.System);
builder.Services.AddSingleton<SubmitDocument>();
builder.Services.AddSingleton<RequestExtraction>();
builder.Services.AddSingleton<ExtractionAttemptCoordinator>();
builder.Services.AddSingleton<ExtractionSupervisorService>();
builder.Services.AddSingleton<IExtractionWakeSignal>(sp => sp.GetRequiredService<ExtractionSupervisorService>());
builder.Services.AddHostedService(sp => sp.GetRequiredService<ExtractionSupervisorService>());
builder.Services.AddIntakeAndExtractionInfrastructure(runtimeConnection);
builder.Services.AddProblemDetails();
builder.Services.AddExceptionHandler<UnhandledExceptionHandler>();
builder.Services.AddRateLimiter(rateLimiter =>
{
    rateLimiter.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
    rateLimiter.OnRejected = (context, _) => new ValueTask(
        Problems.Create(StatusCodes.Status429TooManyRequests, "admission_busy", "Too many concurrent submissions",
            "Retry the same submission with the same Idempotency-Key.").ExecuteAsync(context.HttpContext));
    rateLimiter.AddConcurrencyLimiter(DocumentEndpoints.IntakeRateLimitPolicy, concurrency =>
    {
        concurrency.PermitLimit = IntakeOptions.AdmissionSlots;
        concurrency.QueueLimit = 0;
        concurrency.QueueProcessingOrder = QueueProcessingOrder.OldestFirst;
    });
});

var app = builder.Build();

app.UseExceptionHandler();
app.Use(LocalOnlyGuard.InvokeAsync);
app.UseRateLimiter();
app.MapDocumentEndpoints();

app.Run();
