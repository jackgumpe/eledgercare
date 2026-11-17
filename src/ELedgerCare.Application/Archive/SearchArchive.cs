using ELedgerCare.Domain.Archive;

namespace ELedgerCare.Application.Archive;

public sealed class SearchArchive(
    IArchiveProjectionReadiness readiness,
    IArchiveStore archiveStore)
{
    public async Task<ArchiveSearchOutcome> ExecuteAsync(
        ParsedArchiveQuery query,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(query);

        var current = readiness.GetSnapshot();
        if (current.Status == ArchiveReadinessStatus.Initializing)
        {
            return new ArchiveSearchOutcome(
                ArchiveReadinessStatus.Initializing,
                current.DiagnosticReason ?? "Archive machine projections are initializing; retry shortly.",
                Page: null);
        }

        if (current.Status == ArchiveReadinessStatus.Conflict)
        {
            return new ArchiveSearchOutcome(
                ArchiveReadinessStatus.Conflict,
                current.DiagnosticReason ?? "Archive projection integrity conflict detected; refusing partial search.",
                Page: null);
        }

        return await archiveStore.SearchAsync(query, cancellationToken);
    }
}
