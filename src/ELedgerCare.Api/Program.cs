using System.Net;
using System.Threading.RateLimiting;
using ELedgerCare.Api;
using ELedgerCare.Application.Intake;
using ELedgerCare.Infrastructure;
using Microsoft.AspNetCore.RateLimiting;

var builder = WebApplication.CreateBuilder(args);

// Admission limits: validated at startup; values outside 1..10,485,760 bytes or 1..50 pages fail fast.
var intakeOptions = builder.Configuration.GetSection(IntakeOptions.Section).Get<IntakeOptions>() ?? new IntakeOptions();
var limits = new IntakeLimits(intakeOptions.MaxDocumentBytes, intakeOptions.MaxPages);

// Local-only binding: loopback IPv4 only. Port 0 lets a test harness obtain an ephemeral owned port.
var port = builder.Configuration.GetValue("Api:Port", 5180);
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
builder.Services.AddSingleton(TimeProvider.System);
builder.Services.AddSingleton<SubmitDocument>();
builder.Services.AddIntakeInfrastructure(runtimeConnection);
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
