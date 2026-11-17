using ELedgerCare.Application.Archive;
using ELedgerCare.Domain.Archive;
using ELedgerCare.Infrastructure.Persistence;

namespace ELedgerCare.Api;

internal sealed class ArchiveStartupHostedService(ArchiveProjectionInitializer initializer) : IHostedLifecycleService
{
    public Task StartingAsync(CancellationToken cancellationToken) =>
        initializer.InitializeStartupAsync(cancellationToken);

    public Task StartAsync(CancellationToken cancellationToken) => Task.CompletedTask;

    public Task StartedAsync(CancellationToken cancellationToken) => Task.CompletedTask;

    public Task StoppingAsync(CancellationToken cancellationToken) => Task.CompletedTask;

    public Task StopAsync(CancellationToken cancellationToken) => Task.CompletedTask;

    public Task StoppedAsync(CancellationToken cancellationToken) => Task.CompletedTask;
}

internal static class ArchiveEndpoints
{
    public static IEndpointRouteBuilder MapArchiveEndpoints(this IEndpointRouteBuilder endpoints)
    {
        endpoints.MapGet("/api/archive", SearchArchiveAsync);
        return endpoints;
    }

    private static async Task<IResult> SearchArchiveAsync(
        HttpContext httpContext,
        SearchArchive searchArchive,
        CancellationToken cancellationToken)
    {
        var rawQuery = httpContext.Request.QueryString.Value;
        if (!ArchiveQueryValidator.TryValidateRawQueryString(rawQuery, out var parsedQuery, out var validationError))
        {
            return Problems.Create(
                StatusCodes.Status400BadRequest,
                validationError!.Code,
                "Invalid archive query",
                validationError.Detail);
        }

        var outcome = await searchArchive.ExecuteAsync(parsedQuery!, cancellationToken);
        if (outcome.Readiness == ArchiveReadinessStatus.Initializing)
        {
            httpContext.Response.Headers.RetryAfter = "1";
            return Problems.Create(
                StatusCodes.Status503ServiceUnavailable,
                "archive_not_ready",
                "Archive projections initializing",
                outcome.ReadinessFailureDetail ?? "Archive machine projections are initializing; retry shortly.");
        }

        if (outcome.Readiness == ArchiveReadinessStatus.Conflict)
        {
            return Problems.Create(
                StatusCodes.Status503ServiceUnavailable,
                "archive_projection_conflict",
                "Archive projection integrity conflict",
                outcome.ReadinessFailureDetail ?? "Archive projection integrity conflict detected.");
        }

        httpContext.Response.Headers.CacheControl = "no-store";
        return TypedResults.Ok(ArchiveSearchResponse.From(outcome.Page!));
    }
}
