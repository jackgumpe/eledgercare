namespace ELedgerCare.Domain.Archive;

public sealed record ArchiveSnippetSegment(
    string Text,
    bool Highlighted);

public sealed record ArchiveClippedSnippet(
    string Snippet,
    bool PrefixClipped,
    bool SuffixClipped,
    IReadOnlyList<ArchiveSnippetSegment> Segments,
    IReadOnlyList<string> MatchedTerms,
    int HighlightedOccurrenceCount);

public sealed record CandidateArchiveUnit(
    string SourceKind, // "machine" or "reviewed"
    string Text,
    Guid? ResultId,
    int? PageNumber,
    bool IsFallback,
    int? RevisionNumber,
    string? FieldKey,
    string? FieldLabel,
    int? ConsultedPageNumber);

public sealed record SelectedArchiveWitness(
    string SourceKind,
    string SourceLabel,
    Guid? ResultId,
    int? PageNumber,
    bool IsFallback,
    int? RevisionNumber,
    string? FieldKey,
    string? FieldLabel,
    int? ConsultedPageNumber,
    string Snippet,
    bool PrefixClipped,
    bool SuffixClipped,
    IReadOnlyList<ArchiveSnippetSegment> Segments,
    IReadOnlyList<string> MatchedTerms);

public sealed record ArchiveWitnessSelectionResult(
    IReadOnlyList<string> ContributingSources,
    IReadOnlyList<SelectedArchiveWitness> Witnesses,
    bool HasMoreMatchesInDocument);

/// <summary>
/// Surrogate-safe &lt;= 240 UTF-16 code-unit snippet clipper and witness deduplicator (F4-BIC-06).
/// Produces plain-text highlight segments so UI templates never invoke innerHTML or bypassSecurityTrustHtml.
/// </summary>
public static class ArchiveSnippetBuilder
{
    public static ArchiveClippedSnippet BuildClippedSnippet(
        string text,
        string primaryTerm,
        IReadOnlyList<string> allQueryTerms,
        int maxUtf16CodeUnits = ArchiveSchema.MaxSnippetLength)
    {
        ArgumentNullException.ThrowIfNull(text);
        ArgumentException.ThrowIfNullOrEmpty(primaryTerm);
        ArgumentNullException.ThrowIfNull(allQueryTerms);

        if (maxUtf16CodeUnits < ArchiveSchema.MaxTermLength)
        {
            throw new ArgumentOutOfRangeException(nameof(maxUtf16CodeUnits));
        }

        var matchStart = CLocaleTextMatcher.IndexOf(text, primaryTerm);
        if (matchStart < 0)
        {
            throw new InvalidOperationException("Primary query term was not found in matched unit under C-locale semantics.");
        }

        var matchEnd = matchStart + primaryTerm.Length;
        var budgetAround = Math.Max(0, maxUtf16CodeUnits - primaryTerm.Length);
        var beforeBudget = budgetAround / 2;

        var winStart = Math.Max(0, matchStart - beforeBudget);
        var winEnd = Math.Min(text.Length, winStart + maxUtf16CodeUnits);
        if (winEnd - winStart < maxUtf16CodeUnits && winStart > 0)
        {
            winStart = Math.Max(0, winEnd - maxUtf16CodeUnits);
        }

        // Step INWARD if boundary lands mid-surrogate pair so length never exceeds maxUtf16CodeUnits
        // and no unpaired UTF-16 surrogate is ever emitted (F4-BIC-06).
        if (winStart > 0 && winStart < text.Length && char.IsLowSurrogate(text[winStart]))
        {
            winStart++;
        }

        if (winEnd > winStart && winEnd < text.Length && char.IsHighSurrogate(text[winEnd - 1]))
        {
            winEnd--;
        }

        var snippet = text[winStart..winEnd];
        var coveredTerms = new List<string>();
        var rawIntervals = new List<(int Start, int End)>();
        var occurrenceCount = 0;

        for (var tIdx = 0; tIdx < allQueryTerms.Count; tIdx++)
        {
            var term = allQueryTerms[tIdx];
            var found = CLocaleTextMatcher.FindAllIntervals(snippet, term);
            if (found.Count > 0)
            {
                if (!coveredTerms.Contains(term, StringComparer.Ordinal))
                {
                    coveredTerms.Add(term);
                }

                occurrenceCount += found.Count;
                rawIntervals.AddRange(found);
            }
        }

        rawIntervals.Sort(static (a, b) =>
        {
            var cmp = a.Start.CompareTo(b.Start);
            return cmp != 0 ? cmp : b.End.CompareTo(a.End);
        });

        var merged = new List<(int Start, int End)>(rawIntervals.Count);
        for (var i = 0; i < rawIntervals.Count; i++)
        {
            var cur = rawIntervals[i];
            if (merged.Count == 0 || cur.Start > merged[^1].End)
            {
                merged.Add(cur);
            }
            else if (cur.End > merged[^1].End)
            {
                merged[^1] = (merged[^1].Start, cur.End);
            }
        }

        var segments = new List<ArchiveSnippetSegment>(merged.Count * 2 + 1);
        var cursor = 0;
        for (var i = 0; i < merged.Count; i++)
        {
            var (s, e) = merged[i];
            if (s > cursor)
            {
                segments.Add(new ArchiveSnippetSegment(snippet[cursor..s], Highlighted: false));
            }

            segments.Add(new ArchiveSnippetSegment(snippet[s..e], Highlighted: true));
            cursor = e;
        }

        if (cursor < snippet.Length)
        {
            segments.Add(new ArchiveSnippetSegment(snippet[cursor..], Highlighted: false));
        }

        return new ArchiveClippedSnippet(
            Snippet: snippet,
            PrefixClipped: winStart > 0,
            SuffixClipped: winEnd < text.Length,
            Segments: segments,
            MatchedTerms: coveredTerms,
            HighlightedOccurrenceCount: occurrenceCount);
    }

    public static ArchiveWitnessSelectionResult SelectWitnesses(
        IReadOnlyList<string> terms,
        IReadOnlyList<CandidateArchiveUnit> candidateUnits)
    {
        ArgumentNullException.ThrowIfNull(terms);
        ArgumentNullException.ThrowIfNull(candidateUnits);

        if (terms.Count == 0)
        {
            return new ArchiveWitnessSelectionResult([], [], HasMoreMatchesInDocument: false);
        }

        var reviewedMatchedAny = false;
        var machineMatchedAny = false;
        var totalOccurrencesAcrossUnits = 0;

        for (var uIdx = 0; uIdx < candidateUnits.Count; uIdx++)
        {
            var unit = candidateUnits[uIdx];
            for (var tIdx = 0; tIdx < terms.Count; tIdx++)
            {
                var occ = CLocaleTextMatcher.CountNonOverlappingOccurrences(unit.Text, terms[tIdx]);
                if (occ > 0)
                {
                    totalOccurrencesAcrossUnits += occ;
                    if (string.Equals(unit.SourceKind, "reviewed", StringComparison.Ordinal))
                    {
                        reviewedMatchedAny = true;
                    }
                    else if (string.Equals(unit.SourceKind, "machine", StringComparison.Ordinal))
                    {
                        machineMatchedAny = true;
                    }
                }
            }
        }

        var contributingSources = new List<string>(2);
        if (reviewedMatchedAny)
        {
            contributingSources.Add("reviewed");
        }

        if (machineMatchedAny)
        {
            contributingSources.Add("machine");
        }

        var coveredTermIndices = new bool[terms.Count];
        var representedSources = new HashSet<string>(StringComparer.Ordinal);
        var witnesses = new List<SelectedArchiveWitness>(Math.Min(terms.Count, ArchiveSchema.MaxWitnessesPerDocument));
        var displayedOccurrenceSum = 0;

        for (var tIdx = 0; tIdx < terms.Count; tIdx++)
        {
            if (coveredTermIndices[tIdx])
            {
                continue;
            }

            var term = terms[tIdx];
            var chosenUnit = ChooseBestUnitForTerm(term, candidateUnits, contributingSources, representedSources);
            if (chosenUnit is null)
            {
                // Defensive guard: SQL already filtered documents to match every term in the same REPEATABLE READ snapshot.
                throw new InvalidOperationException("Matched document had no eligible unit for query term under C-locale matcher.");
            }

            var clipped = BuildClippedSnippet(chosenUnit.Text, term, terms);
            representedSources.Add(chosenUnit.SourceKind);
            displayedOccurrenceSum += clipped.HighlightedOccurrenceCount;

            for (var checkIdx = tIdx; checkIdx < terms.Count; checkIdx++)
            {
                if (clipped.MatchedTerms.Contains(terms[checkIdx], StringComparer.Ordinal))
                {
                    coveredTermIndices[checkIdx] = true;
                }
            }

            var sourceLabel = string.Equals(chosenUnit.SourceKind, "reviewed", StringComparison.Ordinal)
                ? $"{chosenUnit.FieldLabel} · Reviewed Revision #{chosenUnit.RevisionNumber}"
                : ArchiveSchema.MachineSourceLabel;

            witnesses.Add(new SelectedArchiveWitness(
                SourceKind: chosenUnit.SourceKind,
                SourceLabel: sourceLabel,
                ResultId: chosenUnit.ResultId,
                PageNumber: chosenUnit.PageNumber,
                IsFallback: chosenUnit.IsFallback,
                RevisionNumber: chosenUnit.RevisionNumber,
                FieldKey: chosenUnit.FieldKey,
                FieldLabel: chosenUnit.FieldLabel,
                ConsultedPageNumber: chosenUnit.ConsultedPageNumber,
                Snippet: clipped.Snippet,
                PrefixClipped: clipped.PrefixClipped,
                SuffixClipped: clipped.SuffixClipped,
                Segments: clipped.Segments,
                MatchedTerms: clipped.MatchedTerms));
        }

        var hasMoreMatches = totalOccurrencesAcrossUnits > displayedOccurrenceSum;
        return new ArchiveWitnessSelectionResult(
            ContributingSources: contributingSources,
            Witnesses: witnesses,
            HasMoreMatchesInDocument: hasMoreMatches);
    }

    private static CandidateArchiveUnit? ChooseBestUnitForTerm(
        string term,
        IReadOnlyList<CandidateArchiveUnit> units,
        IReadOnlyList<string> contributingSources,
        HashSet<string> representedSources)
    {
        CandidateArchiveUnit? bestUnrepresentedSourceUnit = null;
        CandidateArchiveUnit? bestReviewedNonFallback = null;
        CandidateArchiveUnit? bestMachineNonFallback = null;
        CandidateArchiveUnit? bestFallback = null;

        for (var i = 0; i < units.Count; i++)
        {
            var u = units[i];
            if (!CLocaleTextMatcher.Contains(u.Text, term))
            {
                continue;
            }

            if (contributingSources.Count > 1 &&
                !representedSources.Contains(u.SourceKind) &&
                bestUnrepresentedSourceUnit is null)
            {
                bestUnrepresentedSourceUnit = u;
            }

            if (string.Equals(u.SourceKind, "reviewed", StringComparison.Ordinal))
            {
                bestReviewedNonFallback ??= u;
            }
            else if (!u.IsFallback)
            {
                bestMachineNonFallback ??= u;
            }
            else
            {
                bestFallback ??= u;
            }
        }

        return bestUnrepresentedSourceUnit
            ?? bestReviewedNonFallback
            ?? bestMachineNonFallback
            ?? bestFallback;
    }
}
