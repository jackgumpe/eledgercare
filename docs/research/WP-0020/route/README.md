# WP-0020 visible-label replay

The selector opens exactly three JSON files beneath the supplied Windows family directory. `prediction.json` supplies saved words, page text and detected table rows. `layout.json` supplies the original WinRT line word counts, ruled grid edges and SHA-256 of the raw-derived ordered word texts and PDF-point boxes. `windows.json` supplies available ordinary Baidu window starts and page ordinals. The selector has no native, scoring or template input.

## Manifest

Word centers use left/top inclusive, right/bottom exclusive grid edges in top-left-origin PDF points. Raw line membership and ruled rows must reproduce every Windows span sequence hash, table value and flattened page text. Header means row zero of a Windows detected grid. Every body row in a matching column qualifies, even an empty row value. Each original WinRT line's non-table words form its prose observation. A nonempty group whose literal text matches the unchanged WP-0019 label predicate qualifies as a whole line. Page title words and labels unrelated to an identifier can trigger. There is no cap or confidence filter.

The manifest records every selected field, its original word indices, observed box, text, label, reason and window. Page ordinals, window starts and slash-delimited location strings use one-based numbering. All explicit array indices use zero-based numbering. The selector records all available windows and deduplicates the selected start ordinals. The output ends in one LF and has a SHA-256 byte commitment.

## Substitution

Both arms use the same source page and PDF-point coordinates. The coordinator supplies title-corrected ordinary Baidu page projections. A region is geometrically eligible at intersection-over-union of at least 0.5, inclusive. A touching boundary has zero overlap. There must be exactly one eligible native region and that native region must qualify against exactly one Windows region of the same kind, including unselected neighbors. Ties or multiple candidates result in retention with a named reason.

- For a detected Windows table, bind against native table block boxes. Require the same row count and column count for every corresponding row. The positional cell at the same row and column then supplies its literal string. An explicit native table cell containing the empty string is an observation. A missing table, incompatible shape, absent cell or non-string supplies no value. Native has no observed per-cell box. Decisions retain the actual native table box and row/column reference.
- For a Windows prose line, bind against native spans after removing spans with at least half their area inside a native table. All Windows prose groups compete for the match. A unique span with usable, non-whitespace, single-line text supplies its complete literal string, including its label and punctuation. No identifier substring selection, repair, spacing edit or label reconstruction occurs. A missing, empty, multiline or ambiguous native read retains the Windows value. Unresolved decisions carry JSON null for native value.
- Read native records for selected pages only. Record each consumed page file hash. Count equal uniquely bound values as substitutions with `changed=false`. A differing substitution updates only the observed field. Existing unrelated Windows spans, row values and flags survive. Changed span text uses the original Windows word-union box, or the detected cell box where no original words existed. A newly empty observed cell remains explicit in its grid and emits no span. Using Windows support lets the ordinary scorer join the substituted text in the same observed region. The decision witness keeps native geometry separate. Changes to page text use the original Windows layout's chunk ordering and whitespace convention. Exact literal spacing remains in the field witness, table or span. The scorer applies its own frozen normalization.
- If source identity, manifest bytes, observed-layout reconstruction or the Windows payload sequence differs, execution fails. A family with no selections produces a Windows-identical prediction object and an empty decision set. No new review flags are created.

## Reproduction

Run from the repository root in PowerShell, substituting a fresh output folder, the frozen manifest digest, and the family. The first invocation requires only the Windows directory. The two output filenames from the second command are `decisions.json` and `prediction.json`. New output files are created exclusively.

```powershell
python -B docs/research/WP-0020/route/check_route.py
python -B docs/research/WP-0020/route/route.py manifest ../wp0020-data/windows H output/H/manifest.json
python -B docs/research/WP-0020/route/route.py route ../wp0020-data/windows H output/H/manifest.json MANIFEST_SHA256 ../wp0020-data/native output/H
```

The source and synthetic controls freeze first. Each family manifest receives a separate byte commitment before native admission. Both routed predictions freeze before outcome access by the analysis role. This directory contains only research replay code and its evidence.
