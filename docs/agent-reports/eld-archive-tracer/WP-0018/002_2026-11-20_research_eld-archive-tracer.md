# WP-0018 / 002 · Raw Windows words, grid membership and scored text

| Publication field | Value |
| --- | --- |
| Report path | `docs/agent-reports/eld-archive-tracer/WP-0018/002_2026-11-20_research_eld-archive-tracer.md` |
| Reservation and category | WP-0018 / 002, research, [frozen index](https://github.com/jackgumpe/eledgercare/blob/918701ae318b01395b911b9dbdf597e43908665b/INDEX.md#wp-0018-windows-ocr-archive-diagnostic) |
| Author and publisher | eld-archive-tracer, native Codex subagent `/root/archive18_words` |
| Model and effort | Fresh Codex session, requested xhigh. Exact backend and applied effort are not exposed to the author. |
| Environment | Local Windows PowerShell host, Python 3.12.10, CPU, Git, original synthetic H/A archive copies |
| Authored (UTC) | 2026-11-20T05:33:23Z |
| Repository, branch, worktree | Private `jackgumpe/eledgercare` · `research/wp-0018-word-traces` · `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\archive18-words` |
| Base | `918701ae318b01395b911b9dbdf597e43908665b` |
| Final deliverable and replay revision | `aff3970f2c2cf800139b1e0456ae516a4074e4d5` |
| Four-witness evidence | `873ff5b1e7de51b54cba1f3ddd9e52c3b68263d7` |
| Coverage evidence | `00ce51886d8015f887bb21f17bcd5478cb0b38bf` |
| Previous report | First report by this author |
| Related deliverable | WP-0018 / 001, paired author eld-rd-astra, evidence at `01625378954a55da0fe7ce93c5cbb3b2e174c797` |
| Status and next owner | Ready for independent review by eld-rd-reviewer, followed by coordinator disposition |

## Summary

Five of five originally incorrect H cells and 60 of 65 originally incorrect A cells already differ in the WinRT text at their reference positions. The remaining five A cells have no intersecting exported word box. All three H and 51 A originally incorrect reference prose lines map to whole WinRT lines that already differ. The four predeclared witnesses and every location can be followed from pixels through span identity, saved grids and the actual scorer output. Both authors' ledgers agree for all 320 reference cells. [Four witnesses](../../../research/WP-0018/words/witnesses.json) · [Walkthrough and counts](../../../research/WP-0018/words/README.md)

## Objective and acceptance criteria

Trace the four specified H/A witnesses after both verified original baseline passes and before examining paired totals. Account for every reference cell, preserve the H p2 positive prose control, identify the earliest supported divergence and any demonstrated later contribution, and return unresolved alternatives for a non-author to inspect. I also traced every reference prose line using the same pinned raw bytes. Scope and gating follow the [frozen assignment](https://github.com/jackgumpe/eledgercare/blob/918701ae318b01395b911b9dbdf597e43908665b/docs/coordination/WP-0018/assignment.md).

## Change inventory

All paths in this table are newly added under `docs/research/WP-0018/words/`. The separate canonical report commit adds only the path recorded above.

| Paths | Contents |
| --- | --- |
| `trace.py`, `witnesses.json` | Independent reconstruction of spans, grid rows, page text and routing. Four witnesses include the complete page evidence at three page keys. |
| `coverage.py`, `coverage/summary.json` | Per-location geometry, raw string alignment, missing-group searches and exact comparison with the separately published paired ledger. |
| `coverage/locations-H.jsonl`, `coverage/locations-A.jsonl` | 20 + 300 reference cells and 16 + 288 prose lines. Each row has its own key, source hash, reference pointer, members, values, flags and supporting or unresolved observations. |
| `coverage/pages-H.jsonl`, `coverage/pages-A.jsonl` | Four H and 60 A source-linked page records containing all raw words, projected geometry, line membership, span identity, grid rules, reconstructed rows and archived text. |
| `README.md`, `.gitattributes` | Reader's guide and reproduction commands. Scoped LF attributes preserve the JSONL artifact bytes across Windows checkouts. |

The coordinator prepared the private input copy and its admission receipt under `../wp0018-data/words/`. My retained local output directories under that owned path are `witness-run`, `coverage-run`, `coverage-final`, `confirm-witness`, `confirm-coverage`, `final-witness` and `final-coverage`. The source archive was read through the named private copies. Git publication uses the owned branch only.

## Decisions and rationale

- **Table witnesses.** In H p2 r2 c1, the raw word and entire raw line already read `IL801493` for `1L8O1-493`. In A p60 r2 c2 they read `01801-139` for `0I8O1-139`. The words lie inside the intended cell boxes. Grid assembly and reference fallback select exactly the same single word and flag it false. A wrong character in these archived strings is an observation at the exported surface. Internal causes remain open.
- **Prose witnesses.** On H p1 WinRT line ordinal 2 says `Docket 88L1 L-631`. The words are `Docket`, `88L1`, `L-631`. The expected characters are intact across the ID word boundary. The archived line already contains the extra space, and the adapter page-text and scorer line joins reproduce it. H p2 WinRT line ordinal 18 says `Docket 880LO-977`. Its two words remain in order and its critical token scores correctly. Raw line ordinal and reference line number serve different purposes.
- **Character and whitespace cases.** H has five anchored single-word character mismatches. A has 54 of these, four anchored multiword groups with different characters and an extra ID split, and two raw lines differing only in ID spacing. H prose has one character-different and two whitespace-only raw lines. A prose has 50 character-different and one whitespace-only raw line. Sixteen of the 50 also split the ID. Each of these classifications checks original text and geometric association. [Machine-readable counts](../../../research/WP-0018/words/coverage/summary.json)
- **Missing groups and blank cells.** On the other five originally wrong A locations the reference expects nonempty text, yet no raw word intersects the cell. The expected string is absent from the page's WinRT document text, line and word strings and within-line word concatenations. The original cell is empty and the fallback is null. A missing, merged, displaced or misread group cannot be distinguished. A further 1 H and 22 A correctly empty reference cells lose their match because the same zero words produce an empty grid string and a null scorer fallback. Zero original errors recover. Every cell was available and all original tables matched. [A locations with nearby evidence](../../../research/WP-0018/words/coverage/locations-A.jsonl)

## Verification

Commands ran in the declared worktree. `INPUTS` below is `../wp0018-data/words/inputs` and `OUT` is `../wp0018-data/words`. The coordinator reported both unchanged separate-process baselines passed at 05:25:32 UTC, comparing saved score details and published Windows lookups. This is upstream gate evidence. My coverage author check uses the pinned scorer's per-page layout on both representations. WP-0018 / 001 owns the complete separate-process paired scorer and constructed controls.

| Executed check | Result |
| --- | --- |
| Read `git show a0e738bc03e515999659dda09c5ee76d08fb37df:docs/research/WP-0015/astra/visual.py` and the adjacent `recognize.ps1`, `trial.py` and `formats.py`. Inspect frozen `docs/evaluation/WP-0015/score.py`. | Verified pixel-to-point rounding, raw order, grid center membership, joins and scorer ordering against recorded values. Historical H adapter and bridge also have identical content at its run source. |
| `Get-FileHash ../wp0018-data/words/admission.json` | SHA-256 `64809c0044a081d2335b461070b48a7dd7536c11b0364ccddb629041a0c8e3bf`. Each trace also checks the original pinned H/A inventory blob, own run and hashes of the prediction, raw, truth, page and window before using them. |
| At witness source `acf13b71f026980e99a10e7019a32f890f59f3cc`, `python -B docs/research/WP-0018/words/trace.py INPUTS OUT/witness-run` | Exit 0 after baseline PASS. 60,288-byte witness SHA-256 `64b8e29bcacee8d0978e422bfc3f3c6471877a5c2b30eb69104891f7c073c5a8` communicated and acknowledged before inspecting any paired totals. |
| At `c5995d6813fc26348e6c252d0cbd38734318d290`, `python -B docs/research/WP-0018/words/coverage.py INPUTS OUT/coverage-run` | Exit 0. Inspection showed the empty/absent cases needed explicit differentiation of equal word membership and unequal scorer values. |
| At `531581b609e0d2382ab09ce7e04a72a280d879ac`, `python -B docs/research/WP-0018/words/coverage.py INPUTS OUT/coverage-final` | Exit 0. Added the missing-group search, split-token observations and direct cross-check of the paired author's publication. |
| At final deliverable `aff3970f2c2cf800139b1e0456ae516a4074e4d5`, `python -B docs/research/WP-0018/words/trace.py INPUTS OUT/final-witness`, then `python -B docs/research/WP-0018/words/coverage.py INPUTS OUT/final-coverage --checkpoint OUT/final-witness/witnesses.json` | Both exit 0. Compared binary Git blob contents from `git cat-file blob HEAD:<artifact>` with regenerated bytes. All six generated artifacts match exactly. The 1,389 projected words and their stored spans agree. |
| `git diff --check 918701ae318b01395b911b9dbdf597e43908665b HEAD`, followed by the corrected staged-diff check against the same base | Initial formatting check reported three terminal blank lines. Removed them and set the per-directory JSONL line ending. The corrected check passed and all generated artifacts reproduced unchanged. |
| `git push origin research/wp-0018-word-traces` and `git ls-remote --heads origin research/wp-0018-word-traces` | Remote points to the full final deliverable revision above before canonical report publication. Report publication SHA and remote receipt are supplied to the coordinator after the report commit. |

## Review map and handoff

Review the [base-to-deliverable diff](https://github.com/jackgumpe/eledgercare/compare/918701ae318b01395b911b9dbdf597e43908665b...aff3970f2c2cf800139b1e0456ae516a4074e4d5), following `TracePage`, `spans_and_lines`, `rebuild_grids`, `group_checks`, `attribute` and `verify_pair`. Reproduce using the separately admitted reviewer copy. Inspect the four witnesses, the five missing groups and the 23 empty-value losses directly. The `(packet, at)` keys in the linked [H](https://github.com/jackgumpe/eledgercare/blob/01625378954a55da0fe7ce93c5cbb3b2e174c797/docs/research/WP-0018/pair/evidence/H/cells.jsonl) and [A](https://github.com/jackgumpe/eledgercare/blob/01625378954a55da0fe7ce93c5cbb3b2e174c797/docs/research/WP-0018/pair/evidence/A/cells.jsonl) ledgers permit direct row-by-row comparison.

## Risks, disagreements and unfinished work

A bounded future recognition-input experiment would address the demonstrated character errors. Its positive controls should include the correct H p2 prose token. The empty-string/null behavior warrants a separate scoring check. The smallest additional observation for the five missing groups is local source-image inspection at their reference regions and adjacent words. The released archive run used no image inspection, rasterization, new OCR, model execution, GPU, repair, production code or Packet B. This study covers two exposed synthetic packets. Independent review and coordinator disposition remain pending.
