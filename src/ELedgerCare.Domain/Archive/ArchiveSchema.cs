namespace ELedgerCare.Domain.Archive;

public static class ArchiveSchema
{
    public const string ProjectionVersion = "archive-machine-projection/1";
    public const string CursorVersion = "archive-cursor/1";
    public const int MaxRawQueryStringLength = 2048;
    public const int MaxQueryLength = 160;
    public const int MaxTerms = 8;
    public const int MaxTermLength = 64;
    public const int DefaultLimit = 20;
    public const int MaxLimit = 50;
    public const int MaxCursorLength = 256;
    public const int MaxSnippetLength = 240;
    public const int MaxWitnessesPerDocument = 8;

    public const string UnitKindPage = "page";
    public const string UnitKindPageFallback = "page_fallback";
    public const string UnitKindDocumentFallback = "document_fallback";

    public const string MachineSourceLabel = "Machine extraction — unreviewed";
}

public enum ArchiveSourceFilter
{
    All,
    Machine,
    Reviewed,
}

public static class ArchiveSourceFilterNames
{
    public static string ToWire(this ArchiveSourceFilter filter) => filter switch
    {
        ArchiveSourceFilter.All => "all",
        ArchiveSourceFilter.Machine => "machine",
        ArchiveSourceFilter.Reviewed => "reviewed",
        _ => throw new ArgumentOutOfRangeException(nameof(filter), filter, "Unknown archive source filter."),
    };

    public static bool TryFromWire(string? value, out ArchiveSourceFilter filter)
    {
        switch (value)
        {
            case "all":
                filter = ArchiveSourceFilter.All;
                return true;
            case "machine":
                filter = ArchiveSourceFilter.Machine;
                return true;
            case "reviewed":
                filter = ArchiveSourceFilter.Reviewed;
                return true;
            default:
                filter = default;
                return false;
        }
    }
}
