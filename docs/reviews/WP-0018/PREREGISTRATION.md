# WP-0018 / 003 reviewer preregistration (eld-rd-reviewer)

The independent non-author reviewer wrote this file and `review_checks.py`. Both are committed on `review/wp-0018-windows-archive` before any decisive execution. They are based on `918701ae318b01395b911b9dbdf597e43908665b`. The reviewer authored none of the WP-0018 diagnostic and has read no WP-0018 author source, metric or summary. Execution model: local subscription Claude Opus 5.5 (`claude-opus-5-5`), with xhigh effort requested. The applied effort is not exposed.

## Scope and exclusions

- This is a CPU replay of the admitted reviewer copies at `wp0018-data/review/inputs`, with `../admission.json`. The checks also read the named H/A originals under `%USERPROFILE%/eLedgerCare-Speed/WP-0015/review` by exact path, read-only, and never enumerate them.
- The checks perform no OCR, WinRT call, rasterization, GPU work, network access, training, or production or product change. Packet B stays sealed.
- The frozen scorer `inputs/control/score.py` (SHA-256 `1ceb36fe…4bf7`, `7598bf41…`) runs in a separate `python -I` process for every H/A score. It is imported in-process only for predicate functions and for the constructed control's `layout` call, which the control prescribes.
- **Held:** `paired --execute-held-paired` (H/A `pages[*].tables=[]` totals) runs only after a separate coordinator instruction. Until then `paired` evaluates the constructed control only.

## Pre-freeze development disclosure

Only the constructed control was executed before this freeze. There were two control-only `paired` smoke runs, without H/A. They went to `wp0018-data/review/out/prefreeze-smoke-control{,-2}` and both passed 6/6.

The first run's in-process scorer import left `inputs/control/__pycache__/score.cpython-312.pyc` in the reviewer's own control copy. The reviewer removed it and re-verified the four control hashes. The loader now executes the hash-verified bytes with bytecode writing disabled, and C1.1 rejects any extra input entry.

Before writing this source, the reviewer had viewed the following directly:

- the raw, page and window files, truth and published lookups for the four witness pages
- the frozen scorer and adapter source
- the custody metadata
- the prior published WP-0015 summary counts and lookups

The reviewer had run no H/A scorer and examined no paired (`tables=[]`) result and no WP-0018 author material.

## Phase 1 checks (`review_checks.py phase1`)

| ID | Check | Pass condition |
|---|---|---|
| C1.0–C1.1 | Admission manifest and control hashes | no admission failures; control file SHA-256 values equal the manifest |
| C1.2 | Kit receipt/members | the repository kit files at the start pin equal the copies and match the receipt hashes |
| C1.3 | Scorer identity | copy bytes equal Git `7598bf41:docs/evaluation/WP-0015/score.py`; SHA-256 `1ceb36fe…` |
| C1.4 | Published summary | copy bytes equal Git `ce4206f2:docs/reviews/WP-0015/evidence/scored-H-A.json` |
| C1.5–C1.6 | Named runs, copy hashes and sizes | H `h-r1-ab/04-h-windows` and A `a-recovery-ab/04-a-windows`; every record's hash and byte count match |
| C1.7 | Originals (supplementary custody) | exact-path original bytes equal each copy; an unavailable original is recorded at its own scope |
| C1.8 | Copy set | copy directories contain exactly the admitted records; 14 H and 182 A named Windows files |
| C1.9 | Commitments | source/truth/rasters equal `7598bf41:docs/evaluation/WP-0015/commitments.json` and the archive pins; page counts and PDF byte counts match |
| C1.10 | Inventories | blob IDs `8e72acfc…`/`156e53d2…` are at the stated commits. Inputs, plan, the complete named-run file set, every file hash and the prediction hash all match, with return code 0 |
| C1.11 | Archive-pins named files | the pinned relative file hashes match |
| C1.12 | H historical score | the copy equals `ce4206f2:H-scored-receipt.json` for `score-h-r1-ab-windows.json`. A has no Git pin, so it is checked only through C4.2 |
| C2.1–C2.8 | Structure | source hash agreement across PDF/truth/prediction/timing; page order; timing status and prediction hash. RGB pins agree across `rasters.json`, `rasters.input.json` and `timing`. Raw page, source, RGB and size agree, with no WinRT resize. Word counts agree across raw, window and spans. Every page is complete and every span is unflagged |
| C3.1–C3.2 | Adapter reproduction | every `page-NNN.json` and the full `prediction.json` are rebuilt **byte for byte** from the raw WinRT words plus the window `rule_tables`. The rebuild independently re-implements the pinned `a0e738bc` `visual.layout` (`round(px*points/size,3)`, centre-in-grid with `bisect_right`, (line, x0) cell join, sorted chunk text) and `formats.publish` serialization |
| C4.0–C4.2 | Baseline | two separate-process scorer runs per family are byte-identical, and equal the retained historical score copy byte for byte |
| C4.3–C4.4 | Published counts | the archive-pins `published_windows` counts and all 23 published `official` keys match. CER and cell accuracy are compared at the published four-decimal rounding |
| C4.5 | Assignment gate | H 15/20 cells and 8/19 unflagged critical errors; A 235/300 and 94/252. **A failure stops that family** |
| C5.0–C5.5 | Existing case lookups | the header plus every published windows-arm lookup (H p2, H p4, A p60) equals the reviewer's baseline record. This covers identity, prediction shape, the critical line and the critical cell. Centre-only cell membership is also compared with the scorer's `in_cell` |
| C6.0–C6.3 | Constructed control | the frozen `layout` before and after `tables=[]` reproduces the supplied before and after exactly. Prediction invariants hold, lines and critical lines are identical, and the classifier reports one gain, one loss and net zero |

Not reproduced: `missing_numeric_tokens_supplementary`. Its definition belongs to an unadmitted private WP-0015 sensitivity tool.

## Witness traces (`review_checks.py witnesses`)

These four traces run before any aggregate treatment result:

| ID | Location |
|---|---|
| W1 | H p2 table 1 r2 c1 |
| W2 | A p60 table 1 r2 c2 |
| W3 | H p1 line 2 |
| W4 | H p2 line 2 |

Each trace records:

- the reference value, bounding box and critical status, with the truth JSON pointer
- the raw WinRT line text, line ordinal, words and pixel boxes, with raw pointers
- the projected boxes, rounded as the adapter rounds them, compared with the stored spans
- span order and the adapter's cell join order, or the scorer's line join order
- the window rule grid and the emitted grid row and cell in the page and prediction files
- the table IoU match and the scored selection (score pointer, record and mechanism)
- the stage-by-stage first divergence from the expected value, with a minimal character alignment
- what the trace cannot distinguish

For cells, the frozen scorer's `in_cell` first-cell geometry is evaluated on the stored spans for that single reference cell. It is not a `tables=[]` scoring run.

## Held paired accounting (`review_checks.py paired --execute-held-paired`)

This mode runs only on later instruction. It copies each prediction privately and changes exactly `pages[*].tables` to `[]`. Before scoring it requires an identical document, page order and every non-table page field (text, spans, boxes, flags, state).

It then scores both arms in separate processes and requires several invariants:

- the before arm equals the historical bytes
- packet completeness, page order, edits, CER and line counts are identical
- every line record and critical-line verdict is identical
- per-page edit distances are identical
- non-table faults are identical

**Any violation stops reconciliation.** Every reference cell is accounted with:

- the expected value and the before and after observed values, correctness and flags
- the before mode (grid or span fallback, with the already-fallback rows separated)
- the grid JSON pointer and prediction SHA-256, and the after span pointers
- gain, loss, unchanged right, unchanged wrong and unavailable tags
- extra cells by page

Totals are also split by before mode and by critical cells. Their consistency is checked as before correct + gains − losses = after correct.

## Addendum 1: post-freeze correction to C4.2

The first decisive `phase1` run at freeze `e531eef74156f325b2747307adecc09ecd7890ee` passed 1158 of 1162 checks. Its output is preserved at `wp0018-data/review/out/phase1-e531eef/phase1.json`, SHA-256 `eadc6f713d2af1ee79e493e419aaa9add5edf64381cb9b811f3af8d9325d3915`.

The four failures were all the preregistered C4.2 condition: byte and parsed equality with the full retained historical score copies, for H and for A. The only difference is an extra top-level `comparison` block in each retained copy, written by the frozen scorer's `--baseline` option against the native arm. That native prediction is not an admitted input. Every other key, including all counts, page records and faults, was identical.

The preregistered expectation was wrong; this was not an evidence fault. C4.2 is replaced by C4.2r, which checks four things:

- the only extra key is `comparison`
- the reviewer's separate-process bytes equal the retained copy re-serialized without that block in the scorer's own format
- the parsed objects are equal
- the block's family and source identity match

The block itself is recorded by hash and is **not reproduced**. The held paired check P2 now compares against the same comparison-free form.

No other check, threshold, witness or paired-accounting rule changed. No paired (`tables=[]`) result was produced or examined before this correction.

## Addendum 2: released paired run and attribution freeze (second phase)

After the coordinator released the step, the reviewer re-ran `phase1` at `94eba5b68e1635db8a557c690d85585c1582fea7`, with source unchanged since `ecbeb8b`. It passed 1166/1166. The reviewer then ran `paired --execute-held-paired` from the same frozen source, writing to `out/paired-94eba5b/paired.json` (SHA-256 `640ea4f05fca0438642a21fe100b5a8dfd45f5333c36afd20232d478a5b7ae4f`). All 18 checks passed, including every prediction and score invariant.

`review_attribution.py` was written after that run and is committed **before any WP-0018 author source or evidence was opened**. It assigns every incorrect cell and line the earliest supported stage and the split-versus-character effect described in its docstring. It reads only the reviewer copies and the hash-checked reviewer paired outputs. It changes no frozen check, threshold or paired rule.
