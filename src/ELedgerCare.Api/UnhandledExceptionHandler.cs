using Microsoft.AspNetCore.Diagnostics;

namespace ELedgerCare.Api;

/// <summary>
/// Maps Kestrel body-limit failures to the same 413 ProblemDetails response where a response can still
/// be sent; every other unexpected failure becomes a generic 500 that leaks no internals. A 500 on
/// POST /api/documents does not imply rollback: the client must reconcile its idempotency key.
/// </summary>
internal sealed partial class UnhandledExceptionHandler(ILogger<UnhandledExceptionHandler> logger) : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(HttpContext httpContext, Exception exception, CancellationToken cancellationToken)
    {
        if (httpContext.Response.HasStarted || httpContext.RequestAborted.IsCancellationRequested)
        {
            LogAbandoned(logger, exception.GetType().Name);
            return true;
        }

        var result = exception switch
        {
            BadHttpRequestException { StatusCode: StatusCodes.Status413PayloadTooLarge } =>
                Problems.Create(StatusCodes.Status413PayloadTooLarge, "document_too_large", "Document too large"),
            BadHttpRequestException bad =>
                Problems.Create(bad.StatusCode, "bad_request", "Bad request"),
            _ => Problems.Create(StatusCodes.Status500InternalServerError, "server_error", "Unexpected server error",
                "If this was a submission, its outcome is unknown: query the Idempotency-Key before retrying with it."),
        };

        if (result.StatusCode >= 500)
        {
            LogUnexpected(logger, exception.GetType().FullName ?? exception.GetType().Name, exception);
        }

        await result.ExecuteAsync(httpContext);
        return true;
    }

    [LoggerMessage(Level = LogLevel.Error, Message = "Unhandled {ExceptionType} while processing request.")]
    private static partial void LogUnexpected(ILogger logger, string exceptionType, Exception exception);

    [LoggerMessage(Level = LogLevel.Information, Message = "Request abandoned after {ExceptionType}; no response sent.")]
    private static partial void LogAbandoned(ILogger logger, string exceptionType);
}
