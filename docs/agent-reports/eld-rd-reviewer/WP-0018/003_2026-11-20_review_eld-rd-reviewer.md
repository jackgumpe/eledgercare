# WP-0018 / 003: Independent review of the Windows OCR archive diagnostic

- Report path: `docs/agent-reports/eld-rd-reviewer/WP-0018/003_2026-11-20_review_eld-rd-reviewer.md`
- Sequence reservation: [INDEX.md WP-0018 / 003 at `918701ae`](https://github.com/jackgumpe/eledgercare/blob/918701ae318b01395b911b9dbdf597e43908665b/INDEX.md#wp-0018-windows-ocr-archive-diagnostic)
- Category: review
- Author / agent ID: eld-rd-reviewer (a fresh, uninvolved non-author, who authored none of /001, /002 or the coordinator's reconciliation)
- Actual model / effort: Claude Opus 5.5 (`claude-opus-5-5`), native local subscription Claude Code session. xhigh effort was requested; the applied effort is not exposed.
- Execution environment: CLI (Claude Code) on Windows 11 10.0.26200, CPython 3.12.10 AMD64 with no third-party packages, Git 2.55.0.windows.1. CPU only.
- Published by: the author, eld-rd-reviewer, by normal push of the owned branch
- Timestamp: 2026-11-20T06:04:40Z
- Repository / branch: private `jackgumpe/eledgercare` · `review/wp-0018-windows-archive` · worktree `eledgercare-worktrees/archive18-review`
- Base revision: `918701ae318b01395b911b9dbdf597e43908665b`
- Deliverable revision: `3db33e2b75aa64a5ce2df976f05d9c93b9b644e6` (evidence). The source freezes are listed under Change inventory.
- Previous report: none by this reviewer in WP-0018
- Related or reviewed reports:
  - WP-0018 / 001, eld-rd-astra: source `3a1591768828bf72a9cce42db05f0d7c95f6cd60`, evidence `01625378954a55da0fe7ce93c5cbb3b2e174c797`, publication `8479c239bc21b8ecc1bc82a60194fcec841b4408`
  - WP-0018 / 002, eld-archive-tracer: source `aff3970f2c2cf800139b1e0456ae516a4074e4d5`, witness `873ff5b1e7de51b54cba1f3ddd9e52c3b68263d7`, coverage `00ce51886d8015f887bb21f17bcd5478cb0b38bf`, publication `2bf46a4420b5da29eb94975df4d16e7b12947f20`
  - Coordinator reconciliation `b1a033d26988fd4b5718803599c86a9023754145`
- Status: accepted. The independent review concurs, with the minor findings below; none blocks acceptance. Coordinator disposition is pending.
- Next owner: eld-coordinator

## Summary

**Independent disposition: concur.** I verified the custody of the H and A copies, the four witnesses, the frozen scorer replay, the tables-only treatment and every per-location attribution from my own frozen code on my own admitted copies. That code was written and committed before I opened any author object. Afterwards I joined my rows to both authors' immutable rows, field by field, at all 320 cells and 304 prose lines. There are **zero row-level disagreements**. Every published count I checked is reproduced.

**Removing the archived tables (`pages[*].tables = []`) recovered 0 incorrect cells.** It turned 23 correct printed-empty cells into misses (H 1, A 22), all noncritical. In each, the matched grid emitted `""`, which equals the reference value. With no grid, the frozen scorer's span fallback over zero spans returns `null`, which can never equal `""`. Nothing else changed. Prose, critical lines, per-page edit counts, completeness, faults and unflagged critical errors were identical in both arms: H 8/19, A 94/252.

**Every originally incorrect location first diverges at the archived WinRT export.** No case diverges in the adapter's projection or grid assembly, or in the scorer's selection.

| | H cells | A cells | H prose | A prose |
|---|---:|---:|---:|---:|
| Originally incorrect | 5 | 65 | 3 | 51 |
| WinRT text: characters only | 5 | 54 | 1 | 34 |
| WinRT text: characters and a split inside the ID | 0 | 4 | 0 | 16 |
| WinRT text: whitespace only (word split) | 0 | 2 | 2 | 1 |
| No exported word box intersects the cell | 0 | 5 | 0 | 0 |

The supplementary WP-0015 numeric checks also reproduce exactly, both from the historical helper bytes and from an independent re-implementation: H 8 missing and 10 surplus, A 100 missing and 126 surplus.

This is independent review, not author verification. The coordinator owns the final disposition.

## Objective and acceptance criteria

**Objective.** Independently decide where error first appears, at H/A scope only: between the original WinRT text and words, the adapter's spans and grid, and the frozen scorer. Decide also what removing the tables changes. Base this on archived evidence alone, with no new OCR, WinRT call, rendering, GPU work, repair, production write or Packet B, and with independent copies, code and scratch.

The acceptance criteria come from the assignment, steps 1–5, and the coordinator's release. The table shows each with its result.

| Criterion | Result |
|---|---|
| Originals and baselines | **Met.** All 208 copies equal the admission manifest, the Git commitments, the inventories and the originals read by exact path. Both separate-process baselines meet the gates: H 15/20 cells and 8/19 unflagged critical errors, A 235/300 and 94/252. The constructed control reproduces exactly. |
| Four witnesses before totals | **Met.** The traces were committed at `94eba5b` before the coordinator released the paired run, and they equal the word tracer's witness record. |
| Structural-diff scope | **Met.** Only `pages[*].tables` changed, on 13 pages: H p2 and A p5, 10, …, 60. The retained projection hash equals the pair author's. |
| Per-location transitions, flags and original mode | **Met.** All 320 cells are accounted for. Every cell originally used a matched grid, at IoU 0.99697 for H and 0.99667 for every A page, so none was already on fallback. Every flag is false in both arms. |
| Missing versus printed empty | **Met.** There are 23 printed-empty `"" → null` losses. Five nonempty cells were missing in both arms (`"" → null`). |
| Critical-line and edit invariants | **Met.** All 304 line records, all 116 critical-line verdicts and all 64 per-page edit distances are identical across arms. |
| Limits of the earliest supported diagnosis, including no eligible word and spatial intersections | **Met.** See Decisions and rationale. |
| Audit of the authors' counts, split versus character, flags and source | **Met.** Two minor non-blocking findings are recorded below. |
| Supplementary item | **Reproduced.** My earlier "unavailable" statement is corrected in Preregistration Addendum 3. |

## Change inventory

Every path in the base-to-deliverable diff `918701a..3db33e2` is newly added under `docs/reviews/WP-0018/`:

| Action | Exact path | What and why | Relevant symbols |
| --- | --- | --- | --- |
| Added | `review_checks.py` | Frozen independent checks. **phase1** covers custody and commitments, structural invariants, a byte-level rebuild of the pinned adapter output from the raw words, the separate-process baselines, the published lookups and the constructed control. **witnesses** produces the four traces. **paired** runs the held `tables=[]` accounting. | `custody`, `structure`, `adapter_layout`, `baseline`, `lookups`, `constructed_control`, `witness_trace`, `paired_family`, `score_invariants`, `classify_cell` |
| Added | `review_attribution.py` | Earliest supported stage and the split-versus-character effect for every cell and line. Frozen before any author object was opened. | `attribute_family`, `text_effect`, `alignment_pairs`, `tallies` |
| Added | `review_compare.py` | Joins my rows to both authors' immutable rows, reproduces the author receipt hashes, audits published claims, compares the witnesses and reproduces the supplementary counts. Also provides a `--fresh` rerun mode. | `identity`, `pair_receipts`, `row_compare`, `count_audit`, `witnesses`, `supplementary`, `stable` |
| Added | `PREREGISTRATION.md` | Preregistered checks and decision rules, with Addenda 1–3 covering the C4.2r correction, the release and attribution freeze, and the supplementary correction and runs. | — |
| Added | `WITNESS-TRACES.md` | Readable record of the four first-phase traces. | — |
| Added | `evidence/README.md` | Evidence index, scratch-only hashes and the executable reproduction commands. | — |
| Added | `evidence/phase1-e531eef/phase1.json` | The first decisive phase-1 run, preserved with its four failures under the original C4.2 check. | — |
| Added | `evidence/phase1-ecbeb8b/phase1.json`, `evidence/witnesses-ecbeb8b/{witnesses,witness-W1..W4}.json` | First-phase evidence: 1166/1166 checks, plus the four traces. | — |
| Added | `evidence/second-phase/{receipt,phase1-pre-paired,paired,attribution,compare,compare-fresh-0e31c99,reproduction-receipt}.json` | Second phase. A truth-free receipt was committed before any author inspection, followed by the paired run, the attribution, the reconciliation and the fresh end-to-end reproduction. | — |

The commits on the owned branch, all pushed normally:

| Commit | Content |
|---|---|
| `e531eef74156f325b2747307adecc09ecd7890ee` | First freeze |
| `ecbeb8b858f6086027ae767b421465e1c8608b3b` | C4.2r correction |
| `94eba5b68e1635db8a557c690d85585c1582fea7` | First-phase evidence |
| `d9c5e7f1a21be12cefc3a8ea69a6670993bd830a` | Attribution freeze |
| `199662d6195d2512fa02a430af751ac4e06fe55e` | Truth-free receipt, committed before author inspection |
| `6fd3e5d7694ca6df475d3c804aef5d336f1c4680` | Comparison script |
| `bacdaaf9cdd16626430c91ee974a7bded7cb9997` | Serialization fix |
| `0e31c99a1907cbab866e186975757baf80b055d2` | `--fresh` mode |
| `3db33e2b75aa64a5ce2df976f05d9c93b9b644e6` | Evidence |

This report is committed afterwards, separately.

The work had these external effects:

- **Remote.** Normal pushes of the owned branch only, to `origin/review/wp-0018-windows-archive`.
- **Scratch.** New directories under the owned `wp0018-data/review/out/`: `prefreeze-smoke-control{,-2}`, `phase1-e531eef`, `phase1-ecbeb8b`, `witnesses-ecbeb8b`, `phase1-94eba5b-pre-paired`, `paired-94eba5b`, `attribution-d9c5e7f`, `compare-6fd3e5d` (empty, from a failed run), `compare-bacdaaf` and `repro-0e31c99`.
- **Own inputs.** One self-caused bytecode cache was removed from my own `inputs/control/`; the four control hashes were re-verified afterwards (Addendum 1).
- **Read-only.** The original archive was read by exact named path only; I listed no directories in it. Local immutable Git objects were read.
- **Untouched.** No other worktree, shared pointer, product, database, GPU, OCR, WinRT or network API was used or changed.

## Decisions and rationale

**Independence and ordering.** The order of work was fixed in advance and followed:

1. The first freeze, `e531eef`, was pushed before any decisive run.
2. The witness traces were committed at `94eba5b`, before the release.
3. After the release, the paired run used unchanged frozen source.
4. `review_attribution.py` was committed at `d9c5e7f`, and a truth-free tally receipt at `199662d` (05:48:30Z).
5. Only then did I open any author source, evidence or report. Every later comparison therefore tests my precomputed rows against theirs.

By committer time, the word tracer's witness commit (05:26:37Z) precedes the pair author's paired source (05:27:28Z) and evidence (05:28:37Z). Commit time does not prove viewing order; `stage-gates.json` records the coordinator's release sequence.

**Representation effect, not recovery.** The 23 losses are an exact artifact of the frozen scorer:

- With a matched grid, an empty grid cell scores `""`.
- Without one, `joined([])` returns `None` and `"" != None`.

So span fallback can never score a printed-empty cell correct. Every lost cell is a printed blank, mostly in the A "Notice" column (column 5); all 23 are noncritical. The five nonempty A cells that were wrong in both arms (`"" → null`) are a separate class: genuine absence at export.

**Earliest supported stage.** For each wrong cell I required, in order:

1. a raw WinRT word box with positive-area overlap
2. a word whose centre lies in the cell
3. the centred raw words' text, in adapter join order, compared with the expected value
4. the emitted grid compared with those raw words
5. the scored value compared with the emitted grid

For prose I compared the overlapping raw words in scorer join order, then the scorer's assigned set. No case reached the adapter or scorer stage.

Two observations hold at every one of the 624 locations, in my rows and the tracer's alike:

- The intersecting, centred and scorer-owned sets are identical; that is, the geometry is unanimous.
- The emitted grid equals the centred raw words, so the adapter never differs.

The prose assignment never omits an overlapping word, and never takes one from another line or a cell. So there is no spatial or no-eligible-word explanation for any prose error. The only no-word cases are the five A cells. For each:

- no word box intersects the cell
- no word on the page is within two edits of the expected value
- the distinguishing suffix does not occur anywhere in that page's WinRT output: `558` and `710` for the two IDs, and the `-4` row label for p5, p20 and p30

**Split versus character.** My classifier aligns the space-free strings and compares the token-boundary positions. The word tracer instead anchors the token literally and tests for a space inside the raw fragment. The two methods differ in principle, but they agree at every wrong location: 4 A cells and 16 A lines have both character and split effects, 2 A cells and 3 prose lines are whitespace only, and the rest are character only.

The character-operation counts in `attribution.json` come from one minimal alignment and are not unique. They are dominated by O→0 (81) and I→1 (69), followed by 1→I (20), 0→O (16) and hyphen deletions or em-dash substitutions. The synthetic IDs use the confusable set {0, O, 1, I, L, 8} by design.

**Flags.** Every span is hard-coded `flagged:false` by the adapter, and WinRT exposes no confidence. So flags cannot separate any case, and all 102 critical errors are unflagged.

**Rejected complexity.** I did not re-run the authors' executables. Instead, my own code reproduced their outputs and receipt hashes independently. The pair author's baseline and trial score files are byte-identical to mine, and their trial-prediction, retained-projection, packet-invariant and per-page invariant hashes recompute exactly from my copy. The coordinator separately re-executed both authors' code (`b1a033d`), and I verified those receipts against the Git bytes.

## Verification

All commands ran from the worktree root in Git Bash, with `O = wp0018-data/review/out`. Every exit code was 0 except where the result says otherwise.

| Check / exact command or tool operation | Environment and revision | Actual result | Evidence location |
| --- | --- | --- | --- |
| `python docs/reviews/WP-0018/review_checks.py paired --out $O/prefreeze-smoke-control` and `…-2` (constructed control only) | Pre-freeze, uncommitted | 6/6 each. The first run left a self-caused `__pycache__` in my control copy; I removed it and hardened the loader. | `PREREGISTRATION.md` (pre-freeze disclosure) |
| `… review_checks.py phase1 --out $O/phase1-e531eef` | `e531eef` | 1158/1162, **exit 1**. C4.2 failed for H and A: the historical copies carry an extra top-level `comparison` block from the scorer's `--baseline` option, against the unadmitted native arm. | `evidence/phase1-e531eef/phase1.json` |
| `… phase1 --out $O/phase1-ecbeb8b`, then `… witnesses --out $O/witnesses-ecbeb8b` | `ecbeb8b` | 1166/1166. Four traces: W1, W2 and W3 diverge first at raw WinRT; W4 is correct. | `evidence/phase1-ecbeb8b/`, `evidence/witnesses-ecbeb8b/`, `WITNESS-TRACES.md` |
| `… phase1 --out $O/phase1-94eba5b-pre-paired`, then `… paired --execute-held-paired --out $O/paired-94eba5b` | `94eba5b` (source = `ecbeb8b`) | 1166/1166 and 18/18. H: 0 gains, 1 loss, 5 unchanged wrong, 14 unchanged right. A: 0 gains, 22 losses, 65 unchanged wrong, 213 unchanged right. | `evidence/second-phase/{phase1-pre-paired,paired}.json` |
| `python docs/reviews/WP-0018/review_attribution.py --paired-dir $O/paired-94eba5b --out $O/attribution-d9c5e7f` | `d9c5e7f` | Every stage and effect in the Summary table. The edit and line invariants hold, and the line join reproduces the scorer. | `evidence/second-phase/attribution.json` |
| `python docs/reviews/WP-0018/review_compare.py --out $O/compare-6fd3e5d` | `6fd3e5d` | **Exit 1**: TypeError serializing tuple keys. All checks had been evaluated, but no output was written. | `$O/compare-6fd3e5d/` (empty); Addendum 3 |
| `… review_compare.py --out $O/compare-bacdaaf` | `bacdaaf` | **104/104 passed, 0 row disagreements.** | `evidence/second-phase/compare.json` |
| Ad hoc mutation test: `review_compare.row_compare` with 4 faults injected into in-memory author rows | `bacdaaf` | All 4 detected, as 5 disagreement records. | Recorded in `reproduction-receipt.json` |
| Fresh rerun into `$O/repro-0e31c99`: `phase1`; `witnesses`; `paired --execute-held-paired`; `review_attribution.py`; `review_compare.py --fresh` | `0e31c99` | All exit 0: 1166/1166, four traces equal to the committed ones apart from paths, 18/18, and 104/104 with 0 disagreements. | `evidence/second-phase/{reproduction-receipt,compare-fresh-0e31c99}.json` |
| `git show`, `diff`, `log` and `merge-base` on every author and coordinator SHA | Local immutable objects | See the breakdown of R1–R5 and S1–S4 checks below the table. | `compare.json` `checks` |

The 104 reconciliation checks break down as follows:

- **R1, identity and ancestry.** Pair evidence is equal from evidence to publication, and the pair source is unchanged from `3a15917` to `8479c23`. All words artifacts are stable across `873ff5b`/`00ce518`/`aff3970`/`2bf46a4`. The witness SHA-256 is `64b8e29b…`. All 13 coordinator reproduction hashes equal the Git bytes. Every ancestry chain holds.
- **R2, pair receipts.** The score bytes are equal. The trial-prediction hashes `3b94516f…` (H) and `b5c12161…` (A), the retained-projection hash, the packet-invariant hash and all 64 per-page invariant hashes are reproduced from my copy. Counts match. The author admission lists (20 and 188 files) equal my copies, and the published examples match.
- **R3, row join.** Across all 624 locations, these all agree: values, correctness, flags, modes, grid pointers, fallback span order, IoU, pointers, bindings, geometry sets, grid membership, ownership, raw lines, critical verdicts, stages and split classes. Span counts are H 88 and A 1301.
- **R4, count audit.** Both authors' summaries re-derive from their own rows. The /001 and /002 numeric claims and the coordinator's `reconciliation.json` (losses, the five changed-wrong cells, half and row positions) match my rows.
- **R5, witnesses.** All four equal mine.
- **S1–S4, supplementary.** The historical `diag` and `diagnostics` bytes from `ce4206f` equal the published values for H and A, as does the independent re-implementation. The result is invariant under `tables=[]`.

Checks not run, and why:

- the authors' executables (outputs were reproduced independently instead; see Rejected complexity)
- the WP-0015 native arm and its `comparison` block (not admitted; recorded by hash only)
- any raster, image or WinRT inspection (outside this release)
- Packet B (sealed)

## Review map

- Source:
  - [`review_checks.py` at `ecbeb8b`](../../../reviews/WP-0018/review_checks.py): `adapter_layout` reimplements the pinned `a0e738bc:visual.py`, and `paired_family` with `score_invariants` covers the treatment.
  - [`review_attribution.py`](../../../reviews/WP-0018/review_attribution.py): the stage and effect rules are in its docstring.
  - [`review_compare.py`](../../../reviews/WP-0018/review_compare.py): `row_compare` holds the full field-by-field join.
- Evidence index and reproduction: [evidence/README.md](../../../reviews/WP-0018/evidence/README.md) · [PREREGISTRATION.md](../../../reviews/WP-0018/PREREGISTRATION.md) · [WITNESS-TRACES.md](../../../reviews/WP-0018/WITNESS-TRACES.md)
- Author material inspected:
  - Pair: `baseline.py`, `paired.py` and `method_control.py` at `3a15917`, plus the evidence at `0162537`.
  - Words: `trace.py` and `coverage.py` at `aff3970`. The evidence-producing blobs at `873ff5b`/`00ce518` differ only by one trailing blank line each.
  - Coordinator: `reconcile.py` and its receipts at `b1a033d`.

## Risks, disagreements, and unfinished work

There is no substantive disagreement with either author. All 320 cells, all 304 lines and every published count I checked agree.

Minor findings (non-blocking):

1. **Hard-coded field in the pair code.** `paired.py` `summarize()` hard-codes `unavailable_score_rows=0` instead of computing it. The value is true here, since all rows have scores, but the /001 column "Unavailable score rows" is asserted, not measured. Separately, /001 and /002 say "no reference cell is unavailable", meaning no missing score row. Read that alongside the explicit null observations: in the treatment arm, 1 H and 27 A cells observe `null` (22 printed-empty and 5 missing).
2. **Words source designation.** The designated /002 source `aff3970` is not the exact blob that produced the witness and coverage evidence. It differs only by one trailing blank line per script, plus a `.gitattributes` line-ending pin, so its behaviour is identical. /002 discloses the change, and the coordinator reproduced the evidence at `aff3970`.
3. **Constructed control.** The supplied constructed control has no printed-empty cell. It shows that the method detects offsetting gains and losses, but it does not exercise the `""`/`null` asymmetry that produced every observed loss.
4. **My own corrected errors.** All are disclosed and the original evidence is preserved:
   - the C4.2 expectation (Addendum 1)
   - the "unadmitted private tool" statement for the supplementary item (Addendum 3, now reproduced)
   - a serialization bug in the first comparison run
   - a self-caused bytecode cache in my own control copy

Limits of the diagnosis:

- **Earliest observable, not root cause.** The earliest observable divergence is the exported WinRT text. Rendering, bitmap handoff and recognizer internals are unobserved, so the archive cannot separate genuinely ambiguous glyph rendering from recognition error. As context only, and not reproduced here: the published WP-0015 native arm read 18/20 H and 288/300 A cells from the same pinned rasters. That suggests the rasters carry distinguishing information for at least one engine.
- **The five no-word cells.** Omission at export is the narrowest supported reading. A misread, merged or displaced group outside the cell box cannot be excluded entirely, although no near match or suffix exists anywhere on those pages.
- **Scope.** These two synthetic, now-exposed packets are not a measure of customer accuracy. Flags carry no information.

## Handoff

**Recommendation (narrowest supported).**

- **Diagnosis.** For H and A, every incorrect cell and prose line first diverges at the archived WinRT export: substituted, deleted or split characters, or no exported word for 5 A cells. None diverges at adapter projection, grid assembly or scorer selection.
- **Do not adopt reference-box fallback, and do not change grid emission, on this evidence.** Table removal recovers nothing and only adds blank-cell losses.
- **Scorer semantics.** Record the frozen scorer's `""`/`null` asymmetry as a caveat for any future comparison that relies on fallback. It is not a repair.
- **Recognition work needs its own release.** Any work on recognition input or the engine needs a separate release with fresh, unexposed material; H and A are now regression data. It should include the correct H p2 line 2 ID as a positive control and report word splits separately from character errors.
- **No change is authorized.** No product, model or adapter change follows from this diagnostic, and unattended use stays gated, since all critical errors are unflagged.

**Handoff details.**

- Next owner: eld-coordinator, for disposition.
- Branch `review/wp-0018-windows-archive`. Deliverable/evidence revision `3db33e2b75aa64a5ce2df976f05d9c93b9b644e6`. This report's path is above; its publication SHA follows in the handoff message, since a report cannot contain its own commit.
- No acceptance check is outstanding for this review.
- Publication receipt: the remote confirmed `3db33e2b…` at `refs/heads/review/wp-0018-windows-archive` before this report was committed. Confirmation of the report commit is given in the handoff message.
