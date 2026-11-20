# WP-0018 / 003: four frozen witness traces (reviewer, first phase)

- **Author:** eld-rd-reviewer, independent non-author. Local subscription Claude Opus 5.5 (`claude-opus-5-5`), xhigh effort requested; the applied effort is not exposed.
- **Source:** `review_checks.py witnesses`, run at frozen candidate `ecbeb8b858f6086027ae767b421465e1c8608b3b`, script SHA-256 `325085102c09d527a8549b128bbd3f7c14d396fb5cb0e443834f423b050484cb`. The first freeze was `e531eef74156f325b2747307adecc09ecd7890ee`; the C4.2r correction is described in PREREGISTRATION Addendum 1 and did not touch witness code.
- **Inputs:** reviewer copies only, under `wp0018-data/review/inputs`. All 208 records match the admission manifest, the Git pins and the exact-path originals (phase 1).
- **Evidence:** [index](evidence/witnesses-ecbeb8b/witnesses.json) (`57ef2a68…`), [W1](evidence/witnesses-ecbeb8b/witness-W1.json) (`552b242e…`), [W2](evidence/witnesses-ecbeb8b/witness-W2.json) (`b1a1495b…`), [W3](evidence/witnesses-ecbeb8b/witness-W3.json) (`26dbe446…`), [W4](evidence/witnesses-ecbeb8b/witness-W4.json) (`c307cffe…`).
- **Baseline score:** the separate-process frozen scorer outputs stay in scratch: `out/witnesses-ecbeb8b/baseline-H.json` `0e59f3ca5d90f1d80839b91e90a4d0599a787538aa0688c33e08668b077a8c56` and `baseline-A.json` `0db04b1debea6843e29251abffa10273ddb4bdccf150f191b085aad41e40705d`. They are byte-identical to both phase-1 runs.

These traces were saved before any H/A `tables=[]` result was produced. No paired totals have been run.

## Common projection facts

All four witness pages share the same raster facts:

- the raster is 2550×3301 px from a 612×792 pt page
- the WinRT bitmap is the same size, so no resize was applied
- the angle is 0
- the scale is x 0.24 pt/px and y 792/3301 ≈ 0.2399273 pt/px

The pinned adapter `a0e738bc:visual.py` computes `round(px*pt/size, 3)`. My independent projection equals every stored span box exactly. Phase-1 check C3 also rebuilt all 64 page files and both `prediction.json` files byte for byte. Every span is `flagged:false`, and WinRT exposes no confidence values, so flags cannot discriminate any case here.

## W1: H p2 table 1 r2 c1 (critical cell)

**Reference.** Truth pointer `/pages/1/tables/0/rows/1/0`. Expected value `1L8O1-493`, bounding box [54,251,171,284], critical. The reference table box is [54,218,520,383].

**Raw WinRT.** Line ordinal 3 (`raw-002.json` `/reader_result/lines/3`) has text `IL801493`. Its single word is `IL801493` at px [250,1079,470,1113].

**Adapter span.** Pointer `/spans/8` (prediction `/pages/1/spans/8`). Projected box [60.0, 258.882, 112.8, 267.039], equal to the stored box. The word's centre is (86.4, 262.96).

**Emitted grid.** Window rule grid `/rule_tables/0`: xs [54,171,261,439,520], ys [218.5,251,284,317,350,383]. The word falls in grid cell [0,1,0], which is r2 c1, and is the only word there. The emitted cell `/pages/1/tables/0/rows/1/0` is `IL801493`. The emitted row is `["IL801493","15.10","Inlet seat","018"]`. My rebuild matches it.

**Scored selection.** The predicted table box [54.0,218.5,520.0,383.0] has IoU 0.99697 with the reference table, so the cell is scored in **grid** mode. Score pointer `/pages/1/cells/4` (critical `/pages/1/critical/1`) gives observed `IL801493`, correct false, flagged false.

**Geometry check.** The frozen scorer's `in_cell` and first-cell assignment, evaluated on the stored spans for this one cell, select only span 8 (`IL801493`).

**First divergence: raw WinRT word.** The value stays unchanged through the span, the grid and the scored stages. One minimal alignment has distance 3: `1`→`I` at index 0, `O`→`0` at index 3, and `-` deleted at index 5.

**Cannot distinguish:**

- whether the raster glyphs are visually ambiguous (1/I, O/0) or WinRT misread clean glyphs
- whether a hyphen is rendered at that position (no rasterization or re-recognition)
- whether the recorded rule grid follows the raster's actual rule pixels; only its downstream use is reproduced

**Later contributors.** The adapter, grid and scorer change nothing. The alternative span path selects the same single span text.

## W2: A p60 table 1 r2 c2 (critical cell)

**Reference.** Truth pointer `/pages/59/tables/0/rows/1/1`. Expected value `0I8O1-139`, bounding box [123,226,258,256], critical. The reference table box is [43,196,532,346].

**Raw WinRT.** Line ordinal 8 (`raw-060.json` `/reader_result/lines/8`) has text `01801-139`. Its single word is `01801-139` at px [535,975,745,1009].

**Adapter span.** Pointer `/spans/11` (prediction `/pages/59/spans/11`). Projected box [128.4, 233.929, 178.8, 242.087], equal to the stored box. The word's centre is (153.6, 238.008).

**Emitted grid.** Window rule grid `/rule_tables/0`: xs [43,123,258,344,430,532], ys [196.5,226,256,286,316,346]. The word falls in grid cell [0,1,1], which is r2 c2, and is the only word there. The emitted cell `/pages/59/tables/0/rows/1/1` is `01801-139`. The emitted row is `["60-1","01801-139","89.19","50.91","0K"]`. My rebuild matches it.

**Scored selection.** IoU is 0.99667, so the cell is scored in **grid** mode. Score pointer `/pages/59/cells/6` (critical `/pages/59/critical/1`) gives observed `01801-139`, correct false, flagged false. This equals the published lookup (C5.4).

**Geometry check.** `in_cell` selects only span 11, with the same text.

**First divergence: raw WinRT word.** Distance 2: `I`→`1` at index 1 and `O`→`0` at index 3.

**Cannot distinguish:** the same raster, glyph and rule-pixel limits as W1.

**Later contributors.** None change the value.

## W3: H p1 line 2 (critical line, token `88L1L-631`)

**Reference.** Truth pointer `/pages/0/lines/1`. Expected text `Docket 88L1L-631`, bounding box [378,118,482,127.5].

**Raw WinRT.** Line ordinal 1 (`raw-001.json` `/reader_result/lines/1`) has text `Docket 88L1 L-631` and three words:

| Word | Pixel box |
|---|---|
| `Docket` | [1579,491,1742,532] |
| `88L1` | [1758,491,1865,532] |
| `L-631` | [1876,491,2001,532] |

The pixel gaps between words are 16 px and 11 px.

**Adapter spans.** Pointers `/spans/3`, `/spans/4` and `/spans/5` have projected boxes [378.96,117.804,418.08,127.641], [421.92,117.804,447.6,127.641] and [450.24,117.804,480.24,127.641]. All equal the stored boxes, and none is in a grid. The adapter emits no line object; the page text contains the WinRT line text verbatim.

**Scorer line assembly.** No span falls in a reference cell. All three spans are eligible only for line 2 and are assigned there. Joined in (x0, y0) order they give `Docket 88L1 L-631`. Score pointer `/pages/0/lines/1` gives correct false. The critical record `/pages/0/critical/0` has token-found false. The numbered tokens are `["88L1","L-631"]` against the expected `["88L1L-631"]`, giving correct false, flagged false.

**First divergence: raw WinRT line text.** The divergence is one inserted space at expected index 11, a word split between `88L1` and `L-631`. Every character of the expected text is present.

**Cannot distinguish:**

- whether the raster shows a visible gap at the split
- whether the split is WinRT's segmentation of uniform spacing

**Later contributors.** By design the scorer joins separate spans with a single space and requires a standalone critical token. Once WinRT emits two words, no downstream stage in this pipeline can recover the token. A gap-aware merge is a plausible alternative remedy; it is outside this release and was not evaluated.

## W4: H p2 line 2 (critical line, token `880LO-977`, positive control)

**Reference.** Truth pointer `/pages/1/lines/1`. Expected text `Docket 880LO-977`, bounding box [378,118,485,127.5].

**Raw WinRT.** Line ordinal 17 (`raw-002.json` `/reader_result/lines/17`) has text `Docket 880LO-977`. Its words are `Docket` at px [1579,491,1742,532] and `880LO-977` at px [1758,491,2021,532]. WinRT emitted this header line after the table column lines. The scorer's assembly is geometric, so that order does not matter.

**Adapter spans.** Pointers `/spans/27` and `/spans/28` have projected boxes [378.96,117.804,418.08,127.641] and [421.92,117.804,485.04,127.641], equal to the stored boxes. The x1 value 485.04 overshoots the reference by 0.04 pt, but `on_line` still holds.

**Scorer line assembly.** Joined text `Docket 880LO-977`. Score pointer `/pages/1/lines/1` gives correct true. Critical `/pages/1/critical/0` gives token-found true, matching numbered tokens, and correct true. This equals the published lookup (C5.3).

**First divergence: none.** All stages equal the expected text. This positive control shows the same header geometry scoring correctly when WinRT emits the identifier as one word. It does not generalize beyond this line.

## Phase-1 context (no paired result)

- **Baseline gates.** Both pass: H 15/20 cells and 8/19 unflagged critical errors; A 235/300 and 94/252.
- **Baseline modes.** Every reference cell is in grid mode: H 20/20, A 300/300. So neither packet has an already-fallback cell at baseline.
- **Constructed control.** Reproduced exactly: one gain, one loss, net zero.
- **Published lookups.** All published lookups for H p2, H p4 and A p60 match.
