namespace ELedgerCare.Api;

/// <summary>
/// F1 is local-only. Reject requests whose Host or browser Origin is not a loopback name, and mark
/// every response nosniff. No CORS policy is registered; the Angular dev server proxies /api.
/// </summary>
internal static class LocalOnlyGuard
{
    public static Task InvokeAsync(HttpContext context, RequestDelegate next)
    {
        context.Response.Headers.XContentTypeOptions = "nosniff";

        if (!IsLoopbackName(context.Request.Host.Host))
        {
            return Problems.Create(StatusCodes.Status400BadRequest, "non_local_host", "Non-local host rejected")
                .ExecuteAsync(context);
        }

        var origin = context.Request.Headers.Origin;
        if (origin.Count > 0)
        {
            if (origin.Count != 1 || !Uri.TryCreate(origin[0], UriKind.Absolute, out var originUri) || !IsLoopbackName(originUri.Host))
            {
                return Problems.Create(StatusCodes.Status403Forbidden, "non_local_origin", "Non-local origin rejected")
                    .ExecuteAsync(context);
            }
        }

        return next(context);
    }

    private static bool IsLoopbackName(string host) =>
        host is "127.0.0.1" or "localhost" or "[::1]" or "::1";
}
