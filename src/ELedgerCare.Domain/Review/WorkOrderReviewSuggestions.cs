using System.Text.Json;
using System.Text.Json.Serialization;
using ELedgerCare.Domain.Processing;

namespace ELedgerCare.Domain.Review;

/// <summary>
/// Self-contained conservative five-label suggestion boundary (<c>work-order-suggestions/1</c>)
/// operating exclusively on stored <see cref="ExtractionResult"/> raw UTF-8 output and
/// <see cref="SafeNativeDisplayParser"/>. Zero references to qualification, research, or evaluation.
/// </summary>
public static class WorkOrderReviewSuggestions
{
    private static readonly JsonSerializerOptions SnapshotJsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        DefaultIgnoreCondition = JsonIgnoreCondition.Never,
        WriteIndented = false,
    };

    public static WorkOrderMachineSnapshot Evaluate(ExtractionResult result)
    {
        ArgumentNullException.ThrowIfNull(result);
        var rawText = result.DecodeStrictUtf8();
        var pages = SafeNativeDisplayParser.ParsePages(rawText);
        return EvaluateFromParsedPages(
            result.ResultId,
            Convert.ToHexStringLower(result.RawOutputSha256),
            pages);
    }

    public static WorkOrderMachineSnapshot EvaluateFromParsedPages(
        Guid resultId,
        string rawOutputSha256Hex,
        IReadOnlyList<ExtractedPageView> pages)
    {
        ArgumentNullException.ThrowIfNull(pages);
        if (resultId == Guid.Empty)
        {
            throw new ArgumentException("ResultId must be non-empty.", nameof(resultId));
        }

        if (string.IsNullOrWhiteSpace(rawOutputSha256Hex) || rawOutputSha256Hex.Length != 64)
        {
            throw new ArgumentException("rawOutputSha256Hex must be 64 lowercase hex characters.", nameof(rawOutputSha256Hex));
        }

        var matchesByField = new List<RawCandidateMatch>[WorkOrderReviewSchema.FieldCount];
        for (var i = 0; i < matchesByField.Length; i++)
        {
            matchesByField[i] = [];
        }

        foreach (var page in pages)
        {
            var blocks = page.Blocks;
            for (var b = 0; b < blocks.Count; b++)
            {
                var block = blocks[b];

                // 1. Plain 2-simple-cell table rows (inspecting raw markup to reject colspan/rowspan/nested/unbalanced).
                if (string.Equals(block.Kind, "table", StringComparison.Ordinal))
                {
                    if (SafeNativeDisplayParser.TryParseStrictSimpleTableRows(block.Text, out var strictRows))
                    {
                        for (var r = 0; r < strictRows.Count; r++)
                        {
                            var row = strictRows[r];
                            if (row.Count != 2)
                            {
                                continue;
                            }

                            var labelCell = row[0];
                            var valueCell = row[1];
                            if (TryMatchStandaloneLabel(labelCell, allowTitleBlock: true, blockKind: "text", out var tableField) &&
                                !string.IsNullOrWhiteSpace(valueCell) &&
                                !IsRecognizedStandaloneOrInlineLabel(valueCell))
                            {
                                var safeQuote = DiagnosticTextSanitizer.SanitizeForPostgresText(
                                    valueCell, WorkOrderReviewSchema.MaxStoredQuoteChars) ?? string.Empty;
                                matchesByField[tableField.Ordinal].Add(new RawCandidateMatch(
                                    CandidateValue: valueCell,
                                    Source: new ReviewSourceReference(
                                        PageNumber: page.PageNumber,
                                        BlockOrdinal: b,
                                        TableRow: r,
                                        TableColumn: 1,
                                        SourceQuote: safeQuote)));
                            }
                        }
                    }

                    continue;
                }

                // 2. Inline "<ExactLabel>:<nonempty value>" on 'text' blocks only.
                if (string.Equals(block.Kind, "text", StringComparison.Ordinal) &&
                    TryMatchInlineLabelValue(block.Text, out var inlineField, out var inlineValue))
                {
                    if (!IsRecognizedStandaloneOrInlineLabel(inlineValue))
                    {
                        var safeQuote = DiagnosticTextSanitizer.SanitizeForPostgresText(
                            block.Text.Trim(), WorkOrderReviewSchema.MaxStoredQuoteChars) ?? string.Empty;
                        matchesByField[inlineField.Ordinal].Add(new RawCandidateMatch(
                            CandidateValue: inlineValue,
                            Source: new ReviewSourceReference(
                                PageNumber: page.PageNumber,
                                BlockOrdinal: b,
                                TableRow: null,
                                TableColumn: null,
                                SourceQuote: safeQuote)));
                    }

                    continue;
                }

                // 3. Standalone exact label followed immediately by a 'text' block on the same page (zero block skipping).
                if (TryMatchStandaloneLabel(block.Text, allowTitleBlock: true, blockKind: block.Kind, out var standaloneField))
                {
                    if (b + 1 < blocks.Count)
                    {
                        var nextBlock = blocks[b + 1];
                        if (string.Equals(nextBlock.Kind, "text", StringComparison.Ordinal) &&
                            !string.IsNullOrWhiteSpace(nextBlock.Text) &&
                            !IsRecognizedStandaloneOrInlineLabel(nextBlock.Text))
                        {
                            var rawCandidate = nextBlock.Text.Trim();
                            var safeQuote = DiagnosticTextSanitizer.SanitizeForPostgresText(
                                nextBlock.Text.Trim(), WorkOrderReviewSchema.MaxStoredQuoteChars) ?? string.Empty;
                            matchesByField[standaloneField.Ordinal].Add(new RawCandidateMatch(
                                CandidateValue: rawCandidate,
                                Source: new ReviewSourceReference(
                                    PageNumber: page.PageNumber,
                                    BlockOrdinal: b + 1,
                                    TableRow: null,
                                    TableColumn: null,
                                    SourceQuote: safeQuote)));
                        }
                    }
                }
            }
        }

        var candidates = new WorkOrderMachineFieldCandidate[WorkOrderReviewSchema.FieldCount];
        for (var f = 0; f < WorkOrderReviewSchema.FieldCount; f++)
        {
            var spec = WorkOrderReviewSchema.Fields[f];
            var matches = matchesByField[f];

            if (matches.Count == 0)
            {
                candidates[f] = new WorkOrderMachineFieldCandidate(
                    spec.FieldKey,
                    MachineCandidateStatus.Missing,
                    Value: null,
                    Source: null,
                    CompetingSources: []);
                continue;
            }

            if (matches.Count >= 2)
            {
                // More than one candidate for a field is ambiguous even if values repeat:
                // produce null candidate value and expose competing source references.
                candidates[f] = new WorkOrderMachineFieldCandidate(
                    spec.FieldKey,
                    MachineCandidateStatus.Ambiguous,
                    Value: null,
                    Source: null,
                    CompetingSources: matches.Select(m => m.Source).ToArray());
                continue;
            }

            var single = matches[0];
            if (!ReviewTextValidator.ValidateNonEmptyText(
                    single.CandidateValue,
                    spec.MaxChars,
                    allowMultilineWhitespace: spec.Multiline,
                    out var rejection))
            {
                var failedStatus = rejection == ReviewTextValidator.TextRejectionReason.ExceedsMaxLength
                    ? MachineCandidateStatus.Oversized
                    : MachineCandidateStatus.InvalidText;

                // Never truncate or coerce an invalid/oversized candidate into a plausible suggestion.
                candidates[f] = new WorkOrderMachineFieldCandidate(
                    spec.FieldKey,
                    failedStatus,
                    Value: null,
                    Source: single.Source,
                    CompetingSources: []);
                continue;
            }

            candidates[f] = new WorkOrderMachineFieldCandidate(
                spec.FieldKey,
                MachineCandidateStatus.Suggested,
                Value: single.CandidateValue,
                Source: single.Source,
                CompetingSources: []);
        }

        return new WorkOrderMachineSnapshot(
            Schema: WorkOrderReviewSchema.MachineSnapshotSchema,
            ProfileId: WorkOrderReviewSchema.ProfileId,
            FieldSchemaVersion: WorkOrderReviewSchema.FieldSchemaVersion,
            SuggestionPolicyVersion: WorkOrderReviewSchema.SuggestionPolicyVersion,
            ResultId: resultId,
            RawOutputSha256: rawOutputSha256Hex,
            Fields: candidates);
    }

    /// <summary>
    /// Validates caller-supplied source coordinates against the immutable parsed <see cref="ExtractionResult"/>
    /// pages and extracts the server-owned quote (F3-BIC-03: clients cannot invent provenance or quotes).
    /// </summary>
    public static bool TryResolveConsultedSource(
        IReadOnlyList<ExtractedPageView> pages,
        ReviewSourceCoordinate coordinate,
        out ReviewSourceReference resolved,
        out string? error)
    {
        ArgumentNullException.ThrowIfNull(pages);
        resolved = default!;

        if (coordinate.PageNumber < 1 || coordinate.PageNumber > pages.Count)
        {
            error = $"consultedSource.pageNumber ({coordinate.PageNumber}) is outside 1..{pages.Count}.";
            return false;
        }

        var page = pages[coordinate.PageNumber - 1];
        if (coordinate.BlockOrdinal < 0 || coordinate.BlockOrdinal >= page.Blocks.Count)
        {
            error = $"consultedSource.blockOrdinal ({coordinate.BlockOrdinal}) is outside 0..{page.Blocks.Count - 1} on page {coordinate.PageNumber}.";
            return false;
        }

        if (coordinate.TableRow.HasValue != coordinate.TableColumn.HasValue)
        {
            error = "consultedSource.tableRow and consultedSource.tableColumn must either both be null or both be non-negative integers.";
            return false;
        }

        var block = page.Blocks[coordinate.BlockOrdinal];
        if (coordinate.TableRow is { } rowIndex && coordinate.TableColumn is { } colIndex)
        {
            if (!string.Equals(block.Kind, "table", StringComparison.Ordinal) || block.TableRows is null)
            {
                error = $"Block {coordinate.BlockOrdinal} on page {coordinate.PageNumber} is not a parsed table.";
                return false;
            }

            if (rowIndex < 0 || rowIndex >= block.TableRows.Count)
            {
                error = $"consultedSource.tableRow ({rowIndex}) is outside 0..{block.TableRows.Count - 1}.";
                return false;
            }

            var row = block.TableRows[rowIndex];
            if (colIndex < 0 || colIndex >= row.Count)
            {
                error = $"consultedSource.tableColumn ({colIndex}) is outside 0..{row.Count - 1}.";
                return false;
            }

            var cellQuote = DiagnosticTextSanitizer.SanitizeForPostgresText(
                row[colIndex], WorkOrderReviewSchema.MaxStoredQuoteChars) ?? string.Empty;
            resolved = new ReviewSourceReference(coordinate.PageNumber, coordinate.BlockOrdinal, rowIndex, colIndex, cellQuote);
            error = null;
            return true;
        }

        var blockQuote = DiagnosticTextSanitizer.SanitizeForPostgresText(
            block.Text.Trim(), WorkOrderReviewSchema.MaxStoredQuoteChars) ?? string.Empty;
        resolved = new ReviewSourceReference(coordinate.PageNumber, coordinate.BlockOrdinal, null, null, blockQuote);
        error = null;
        return true;
    }

    public static string SerializeSnapshotJson(WorkOrderMachineSnapshot snapshot)
    {
        ArgumentNullException.ThrowIfNull(snapshot);
        var dto = PersistedSnapshotJson.FromDomain(snapshot);
        return JsonSerializer.Serialize(dto, SnapshotJsonOptions);
    }

    public static WorkOrderMachineSnapshot DeserializeSnapshotJson(string json)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(json);
        var dto = JsonSerializer.Deserialize<PersistedSnapshotJson>(json, SnapshotJsonOptions)
            ?? throw new InvalidOperationException("Persisted machine snapshot JSON deserialized to null.");
        return dto.ToDomain();
    }

    private static bool TryMatchStandaloneLabel(
        string text,
        bool allowTitleBlock,
        string blockKind,
        out WorkOrderFieldSpec matchedField)
    {
        matchedField = default!;
        if (string.IsNullOrWhiteSpace(text))
        {
            return false;
        }

        var isTextKind = string.Equals(blockKind, "text", StringComparison.Ordinal);
        var isTitleKind = string.Equals(blockKind, "title", StringComparison.Ordinal);
        if (!isTextKind && !(allowTitleBlock && isTitleKind))
        {
            return false;
        }

        // Exact label match after outer whitespace removal and AT MOST ONE trailing ':' removal.
        // Do NOT trim again or strip a second colon ("Work Order ID::" -> "Work Order ID:" -> rejected).
        var trimmed = text.Trim();
        var candidateLabel = trimmed.EndsWith(':') ? trimmed[..^1] : trimmed;

        foreach (var spec in WorkOrderReviewSchema.Fields)
        {
            if (isTitleKind && !spec.AllowTitleHeading)
            {
                continue;
            }

            if (string.Equals(candidateLabel, spec.ExactSourceLabel, StringComparison.Ordinal))
            {
                matchedField = spec;
                return true;
            }
        }

        return false;
    }

    private static bool TryMatchInlineLabelValue(
        string text,
        out WorkOrderFieldSpec matchedField,
        out string candidateValue)
    {
        matchedField = default!;
        candidateValue = string.Empty;
        if (string.IsNullOrWhiteSpace(text))
        {
            return false;
        }

        var leadingTrimmed = text.TrimStart();
        foreach (var spec in WorkOrderReviewSchema.Fields)
        {
            var prefixLen = spec.ExactSourceLabel.Length;
            if (leadingTrimmed.Length <= prefixLen + 1)
            {
                continue;
            }

            if (!leadingTrimmed.StartsWith(spec.ExactSourceLabel, StringComparison.Ordinal) ||
                leadingTrimmed[prefixLen] != ':')
            {
                continue;
            }

            var remainder = leadingTrimmed[(prefixLen + 1)..];
            // Guard against double-colon ("Property::" or "Property::foo" or "Property: :") being misparsed!
            if (remainder.StartsWith(':'))
            {
                return false;
            }

            var trimmedRemainder = remainder.Trim();
            if (trimmedRemainder.Length == 0 || trimmedRemainder == ":")
            {
                return false;
            }

            matchedField = spec;
            candidateValue = trimmedRemainder;
            return true;
        }

        return false;
    }

    private static bool IsRecognizedStandaloneOrInlineLabel(string text)
    {
        if (TryMatchStandaloneLabel(text, allowTitleBlock: true, blockKind: "text", out _))
        {
            return true;
        }

        return TryMatchInlineLabelValue(text, out _, out _);
    }

    private sealed record RawCandidateMatch(string CandidateValue, ReviewSourceReference Source);

    private sealed record PersistedSnapshotJson(
        string Schema,
        string ProfileId,
        string FieldSchemaVersion,
        string SuggestionPolicyVersion,
        Guid ResultId,
        string RawOutputSha256,
        PersistedFieldCandidateJson[] Fields)
    {
        public static PersistedSnapshotJson FromDomain(WorkOrderMachineSnapshot s) => new(
            s.Schema,
            s.ProfileId,
            s.FieldSchemaVersion,
            s.SuggestionPolicyVersion,
            s.ResultId,
            s.RawOutputSha256,
            s.Fields.Select(f => new PersistedFieldCandidateJson(
                f.FieldKey,
                f.Status.ToWire(),
                f.Value,
                f.Source,
                f.CompetingSources.ToArray())).ToArray());

        public WorkOrderMachineSnapshot ToDomain() => new(
            Schema,
            ProfileId,
            FieldSchemaVersion,
            SuggestionPolicyVersion,
            ResultId,
            RawOutputSha256,
            Fields.Select(f => new WorkOrderMachineFieldCandidate(
                f.FieldKey,
                MachineCandidateStatusNames.FromWire(f.Status),
                f.Value,
                f.Source,
                f.CompetingSources ?? [])).ToArray());
    }

    private sealed record PersistedFieldCandidateJson(
        string FieldKey,
        string Status,
        string? Value,
        ReviewSourceReference? Source,
        ReviewSourceReference[]? CompetingSources);
}

public sealed record ReviewSourceCoordinate(
    int PageNumber,
    int BlockOrdinal,
    int? TableRow,
    int? TableColumn);

public sealed record ReviewSourceReference(
    int PageNumber,
    int BlockOrdinal,
    int? TableRow,
    int? TableColumn,
    string SourceQuote)
{
    public ReviewSourceCoordinate ToCoordinate() => new(PageNumber, BlockOrdinal, TableRow, TableColumn);
}

public sealed record WorkOrderMachineFieldCandidate(
    string FieldKey,
    MachineCandidateStatus Status,
    string? Value,
    ReviewSourceReference? Source,
    IReadOnlyList<ReviewSourceReference> CompetingSources);

public sealed record WorkOrderMachineSnapshot(
    string Schema,
    string ProfileId,
    string FieldSchemaVersion,
    string SuggestionPolicyVersion,
    Guid ResultId,
    string RawOutputSha256,
    IReadOnlyList<WorkOrderMachineFieldCandidate> Fields)
{
    public WorkOrderMachineFieldCandidate GetCandidate(string fieldKey) =>
        Fields.Single(f => string.Equals(f.FieldKey, fieldKey, StringComparison.Ordinal));
}
