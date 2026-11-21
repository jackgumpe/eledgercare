# WP-0025 repeatability analysis

Run from the analysis checkout with the pinned Q0 Python 3.12.10 interpreter, `-I -B` and `CUDA_VISIBLE_DEVICES=-1`. The historical projection uses the original tokenizer, frozen title-aware parser and the exposed binder 1 PDF. The CPU script reads the coordinator's two plan files, the runner's sealed returns and the exclusive lease receipts. Pass an unused destination filename. The optional `--runs` and `--lease` arguments support a byte-preserving archive replay.

```powershell
$env:CUDA_VISIBLE_DEVICES = '-1'
$py = 'C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe'
& $py -I -B docs/research/WP-0025/analysis/preflight.py
& $py -I -B docs/research/WP-0025/analysis/analyze.py $planDirectory $p1Digest $p2Digest $outputPath
```

## Frozen interpretation

The raw per-slot artifacts preserve each integer and its little-endian uint32 bytes through the selected EOS. The result references full stream contents by SHA-256. Each fresh slot is compared to both historical streams. Ordered stream pairs share a detail record for literal, cell, geometry and terminal comparisons. Historical reproduction requires the entire WP-0024 stock and hooked streams in the appropriate direction. The signature report distinguishes a reverse pair, partial historical coordinate transitions, four transitions on other streams, and identical final streams. The sequence alignment of token edits is descriptive. Only the earliest differing decision shares the complete preceding prefix.

The 8 × 8 matrices use a Boolean for exact agreement, a zero-based index for first divergence, `"+infinity"` for full agreement and JSON null for undefined. The 28 unique comparisons (6 stock/stock, 6 hooked/hooked and 16 cross-mode) reuse eight model observations. A receipt, process or guard problem makes the overall disposition incomplete. A failed slot and its unverified suffix have undefined comparisons. Completed verified prefixes are retained. A separately reported integrity issue can be recorded with `--external-issue`. Stock variation takes precedence over hooked variation with stable stock, stable mode-specific separation and complete agreement. Flags separately cover semantic, physical witness and terminal changes. Absolute call number, process, within-process ordinal, parity, previous mode and mode transitions describe this fixed order only.

The analyzer decodes token IDs to literal bytes, reconciles the native parser spans, compares page text, block text and each table cell, and reports right-minus-left deltas of all changed native boxes on the original 0–999 scale. Block geometry comparisons use physical page and block ordinal with full old/new kind and literal. A changed identity or missing block is labeled in its comparison. The glyph search reopens the bound public PDF at page 1 and verifies the owner, unit, schema and ordinary row against their ink rectangles. In each slot a witness succeeds only when one eligible block or table row has both matching words/cells and a box containing all glyph centers. Binder 1's window 4 target belongs to a different input.

For H, reconstruction verifies the post-consumption token IDs and absolute positions, maps BF16 bit patterns to FP32 and accumulates each span in token order before FP32 division. It compares the resulting bytes with the saved mean for every printed span. EOS has no consumed row. For each H/H pair, two hidden rows qualify when their absolute positions, token IDs and printed-span membership keys match. Keys include page, kind, block type, literal, cells and occurrence index. A pool additionally requires the same aligned absolute token-member list. Geometry remains an independent comparison because a box can shift while its printed text and pool membership stay stable. The JSON retains per-row and per-span component difference counts, FP32 maximum absolute differences and a separate summary for shared-prefix rows and matching rows after divergence. Matched rows after divergence can have different prior token histories. Unmatched counts and excluded rows/spans limit the scope of the feature comparison. All S hidden states are unobserved.

Independent review verifies the execution environment, input bytes and guard telemetry in addition to reconstructing numerical results from the primary artifacts. The fixed eight calls on one ordered image triple provide no independent estimate of the hook's causal effect or the downstream memory probe's performance.

