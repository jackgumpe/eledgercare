using Microsoft.AspNetCore.Http.HttpResults;

namespace ELedgerCare.Api;

/// <summary>
/// Consistent ProblemDetails bodies. Details never contain SQL, credentials, document content or parser dumps.
/// </summary>
internal static class Problems
{
    public static ProblemHttpResult Create(
        int status,
        string code,
        string title,
        string? detail = null,
        IReadOnlyDictionary<string, object?>? extraExtensions = null)
    {
        var extensions = new Dictionary<string, object?>(StringComparer.Ordinal)
        {
            ["code"] = code,
        };
        if (extraExtensions is not null)
        {
            foreach (var (key, value) in extraExtensions)
            {
                extensions[key] = value;
            }
        }

        return TypedResults.Problem(
            statusCode: status,
            title: title,
            detail: detail,
            extensions: extensions);
    }
}
