using Microsoft.AspNetCore.Http.HttpResults;

namespace ELedgerCare.Api;

/// <summary>
/// Consistent ProblemDetails bodies. Details never contain SQL, credentials, document content or parser dumps.
/// </summary>
internal static class Problems
{
    public static ProblemHttpResult Create(int status, string code, string title, string? detail = null) =>
        TypedResults.Problem(
            statusCode: status,
            title: title,
            detail: detail,
            extensions: new Dictionary<string, object?> { ["code"] = code });
}
