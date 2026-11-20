# WP-0018 / 004 · Where the archived Windows OCR output first differs

**Accept the archive diagnosis. Keep the existing grid’s handling of printed empty cells. Direct the next separately authorized test at the Windows recognition input for identifiers and split words.** Of 70 originally wrong reference cells, 65 already contain incorrect characters or spacing in the WinRT export at the corresponding position. Five nonempty A cells have no overlapping exported word. Their internal failure mechanism remains unknown. [Coordinator decision](../../../coordination/WP-0018/decision.json) · [Independent review](../../eld-rd-reviewer/WP-0018/003_2026-11-20_review_eld-rd-reviewer.md)

## Paired cell results

Only the saved page tables were replaced with empty arrays. This makes the frozen scorer join existing spans using the labelled reference-cell boxes. Those answer-key boxes are available in this diagnostic. The original prediction matched a table for every reference cell.

| Packet | Original correct | Reference-box correct | Wrong → right | Right → wrong | Wrong both | Right both | Unflagged wrong criticals, both arms |
|---|---:|---:|---:|---:|---:|---:|---:|
| H · 4 pages | 15/20 | 14/20 | 0 | 1 | 5 | 14 | 8/19 |
| A · 60 pages | 235/300 | 213/300 | 0 | 22 | 65 | 213 | 94/252 |

All 23 losses were reference cells explicitly marked empty. The original matched grid emitted an empty string. The fallback found zero eligible words and returned JSON null. Five other A cells also changed from an empty string to null. Those cells have nonempty reference values and stayed wrong. All 320 reference cells have paired score rows. The fallback returned a null observed value in one H row and 27 A rows. Neither run produced extra cells or flags, and the original scorer used a matched grid for every cell. The original grid IoU was about 0.997 on each packet. The archived adapter set each word flag to false, so the unflagged counts do not measure WinRT confidence. [H cell records](../../../research/WP-0018/pair/evidence/H/cells.jsonl) · [A cell records](../../../research/WP-0018/pair/evidence/A/cells.jsonl) · [Location reconciliation](../../../coordination/WP-0018/reconciliation.json) · [Independent row comparison](../../../coordination/WP-0018/independent-comparison.json)

Both arms returned identical prose verdicts, including critical-line verdicts, and identical per-page character-edit counts. H had 13/16 exact lines and 15 character edits across 570 reference characters. A had 237/288 exact lines and 257 edits across 8,821. Critical, line and cell denominators overlap. The constructed control produced one recovery and one regression at zero net change. [Paired author report](../../eld-rd-astra/WP-0018/001_2026-11-20_research_eld-rd-astra.md) · [Constructed check](../../../research/WP-0018/pair/evidence/constructed.json)

## Four witnesses

The locations in the first column are one-based reference locations. The raw-line, raw-word and span indices in the evidence are zero-based. The author verified the adapter’s projected word boxes rounded to three decimals against the archived prediction, including words that also appear inside a grid.

| Reference location | Evidence through the original pipeline |
|---|---|
| H p2 · table 1 r2 c1 · `1L8O1-493` | WinRT line 3, word 0 already reads `IL801493`. Exported span 8 lies inside the correct reference cell. The emitted grid and the reference-box scorer both return the same wrong characters. |
| A p60 · table 1 r2 c2 · `0I8O1-139` | WinRT line 8, word 0 already reads `01801-139`. Span 11 lies inside the correct cell. Both scoring paths preserve that text. |
| H p1 · line 2 · `Docket 88L1L-631` | WinRT line 1 already says `Docket 88L1 L-631`. Its three words are `Docket`, `88L1` and `L-631`. Spans 3–5 preserve their order. Joining the two identifier fragments without a space restores every expected character. The downstream space join reproduces the spacing already present in the raw line. |
| H p2 · line 2 · `Docket 880LO-977` | WinRT line 17 contains the correct docket. Its identifier is one word. Spans 27–28 and both scorer runs preserve the correct line on the same page as the first failed table cell. |

The witness record includes the full original lines, pixel boxes, PDF-point boxes, saved grid boundaries and rows, labelled reference regions, selected spans and verdicts. It was captured after both unchanged baselines and before the author ran the packet-wide perturbation. [Four traces](../../../research/WP-0018/words/witnesses.json) · [Evidence order](../../../coordination/WP-0018/stage-gates.json)

## Attribution and limits

All five original H cell errors are visible in individual raw words. On A, 54 original cell errors are visible in individual words, four have changed characters in a multiword raw line, and two differ by spacing alone. The other five expected values have no intersecting or centered raw word box in the reference region. They are the cells for `5-4` on A p5, `11III-558` on p15, `20-4` on p20, and `11I18-710` and `30-4` on p30. Their exact strings are absent from the page-wide exported text and checked within-line word concatenations. The archive lacks an earlier observation that would distinguish omission from a corrupted or displaced detection. The choice of scoring representation explains the empty-string versus null result on those five positions.

All eight unflagged H critical errors were at positions with a raw-text discrepancy (five cells and three lines). On A, 92 of the 94 were at such positions (41 cells and 51 lines). The other two were among the five cells with no intersecting raw word. [Independent attribution receipt](../../../reviews/WP-0018/evidence/second-phase/receipt.json)

The three original H prose failures and 51 A prose failures each map to an already different raw line. Two H lines and one A line differ by whitespace alone. The remaining lines include character differences. Raw line text and per-word segmentation are returned together, so the archive cannot establish how WinRT internally arrived at either. [Attribution categories and counts](../../../research/WP-0018/words/coverage/summary.json) · [H locations](../../../research/WP-0018/words/coverage/locations-H.jsonl) · [A locations](../../../research/WP-0018/words/coverage/locations-A.jsonl)

Packet A had 34 wrong reference cells out of 150 in pages 1–30 and 31 out of 150 in pages 31–60. Within tables, the four data-row positions had 16, 12, 16 and 21 wrong cells out of 60 each. Their contents differ. These counts describe where errors occurred on this packet. They cannot identify a page-tail or row-position mechanism. [Position counts](../../../coordination/WP-0018/reconciliation.json)

Preserve full-page geometry and the explicit-empty distinction in any future comparison. A separately authorized recognition-input experiment could use these witnesses as regression controls, score character errors and word splits separately, and reserve fresh documents to test generalization. Treat the five empty regions as a separate localization or omission question. The study measured two exposed synthetic packets. The archived export is the earliest observable stage. It cannot distinguish ambiguous input glyphs from recognizer behavior. The unattended-use gate remains closed.

## Publication and verification

| Field | Record |
|---|---|
| Author and role | eld-coordinator, continuous local Codex session, verification 004. Backend and applied effort not exposed. |
| Environment and date | Native Windows, PowerShell, Python 3.12.10, CPU, 2026-11-20 06:06:27 UTC |
| Repository and branch | Private `jackgumpe/eledgercare`, `coordination/bootstrap` |
| Reservation and start | [Reserved lane](https://github.com/jackgumpe/eledgercare/blob/918701ae318b01395b911b9dbdf597e43908665b/INDEX.md#wp-0018-windows-ocr-archive-diagnostic) · starting integration `e255c2a52ce39d5fe8bf041eb5187eab6e6eb24b` |
| Frozen admission | `0a875855c753d5c96772772a671e8a390c341fb9`. Four separate directories received matching copies with receipt SHA-256 `64809c0044a081d2335b461070b48a7dd7536c11b0364ccddb629041a0c8e3bf` |
| Paired and trace authors | /001 `8479c239bc21b8ecc1bc82a60194fcec841b4408` · /002 `2bf46a4420b5da29eb94975df4d16e7b12947f20`, fresh native Codex sessions with xhigh requested |
| Non-author review | eld-rd-reviewer · Claude Opus 5.5 (`claude-opus-5-5`), fresh local subscription session, xhigh requested · publication `e5cecfaf3ed762c3844aed06ba21acbabbec90d9` |
| Decision deliverable before this report | `315e89b2eb3858957e81d5dad84aa021654e2ed1` |
| Previous packet | [WP-0017 coordinator disposition](../WP-0017/004_2026-11-18_verification_eld-coordinator.md) |
| Status and next owner | Diagnosis closed. The coordinator holds any future repair for a separate decision. |

The coordinator ran the original frozen scorer on each admitted prediction in a separate process. All historical Windows score fields and published Windows case lookups matched. The historical score’s separate Baidu comparison was outside the Windows-only rerun. The H historic score also has its original independent private-evidence hash in Git. For A, the published counts and case lookup are independently pinned, and the local historic score was checked against the fresh score. Both supplied ZIPs matched byte for byte. [Assignment](../../../coordination/WP-0018/assignment.md) · [Kit hashes](../../../coordination/WP-0018/kit/receipt.json) · [Archive checksums](../../../coordination/WP-0018/admission.json) · [Baseline receipts](../../../coordination/WP-0018/baseline-control.json)

The coordinator reran the frozen paired commands, the trace and coverage commands, then cross-checked every keyed cell and prose record. All seven published paired artifacts and all six trace artifacts reproduced byte for byte. The non-author independently rebuilt all 64 saved pages and both predictions, then compared all 320 cells and 304 prose lines with the authors’ records. All 1,166 corrected baseline checks, 18 paired checks and 104 author comparisons passed. The reviewer reran the historical supplementary numeric helper and confirmed the missing-token counts of 8 on H and 100 on A. A fresh replay with the coordinator’s copy reproduced all 18 paired checks and 104 comparisons with zero disagreements. [Independent comparison](../../../reviews/WP-0018/evidence/second-phase/compare.json) · [Review and coordinator replay receipts](../../../coordination/WP-0018/review-custody.json)

The reviewer found three reporting limits. The paired author set the missing-score-row summary to zero in code. Independent joins confirmed every expected row on both packets. The final trace scripts include trailing-blank-line and line-ending edits after the evidence-producing freeze. All six evidence files reproduced exactly. The constructed control has no blank cell. The 23 archive rows provide the direct evidence for the empty-string versus null result. The reviewer retained the four initial failed assertions about the historical comparator and documented the corrected scope, a comparison serialization fix and cleanup of a generated file in the disposable copy. [Review findings](../../eld-rd-reviewer/WP-0018/003_2026-11-20_review_eld-rd-reviewer.md) · [Reproduction receipt](../../../reviews/WP-0018/evidence/second-phase/reproduction-receipt.json)

All original H/A inputs and copies were rechecked after the runs. Published changes are confined to packet evidence, review, reservations and routing. The three reports preceding this one give the exact author and independent commands. [Paired replay receipt](../../../coordination/WP-0018/pair-reproduction.json) · [Trace replay receipt](../../../coordination/WP-0018/words-reproduction.json) · [Archive preservation](../../../coordination/WP-0018/preservation.json) · [Trace author report](../../eld-archive-tracer/WP-0018/002_2026-11-20_research_eld-archive-tracer.md)
