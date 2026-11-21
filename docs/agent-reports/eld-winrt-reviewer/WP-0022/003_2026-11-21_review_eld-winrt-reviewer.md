# WP-0022 / 003 â€” Independent replay of renderer and Windows ledger ownership

**Accepted as a completed study.** The WinRT source correctly spelled all 36 unambiguous amounts. The frozen reader assigned zero of them to their ledgers. Renderer input yielded 24 correct assignments. All eight WinRT parent headings opened a frame, but recognition returned pieces of the schema on separate lines. The reader consequently never captured a typed parent. These data establish a line-grouping and parsing failure ahead of parent restoration. The matrix-memory trigger was unmet. [Independent summary](../../../reviews/WP-0022/summary.json) Â· [Frame and transcription comparisons](../../../reviews/WP-0022/comparison.json)

- Author and publisher â€” eld-winrt-reviewer, fresh native Codex session `/root/win22_review`. Requested effort xhigh. Exact backend and applied effort were unexposed. I did not author the cloud design, study fixtures, reader, harness, frozen scorer or reviewed reports. All my execution was offline on Windows.
- Category and next owner â€” review, accepted. eld-coordinator owns /004 disposition and closure. This is my first report in the packet. [Reservation](https://github.com/jackgumpe/eledgercare/blob/10cbfb0fa8de2befb28a69c6fb10da90ca737219/INDEX.md#wp-0022-rendered-versus-winrt-ledger-ownership)
- Canonical path â€” `docs/agent-reports/eld-winrt-reviewer/WP-0022/003_2026-11-21_review_eld-winrt-reviewer.md`. UTC review completion on 2026-11-21 at 06:58:24Z.
- Repository â€” private `jackgumpe/eledgercare`, branch `review/wp-0022-paired`, worktree `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/scope22-review`. Base `10cbfb0fa8de2befb28a69c6fb10da90ca737219`. Final review source `44809e8880d259ee0bbd7fe9cb84f0143ea6bf9d`. Final evidence `8d1850a711070e15521e2554361de09b4e6129a7`, verified on origin before /003.
- Reviewed the custodian's public commitment `e207ee56ce1716abf6568ecdb254c6f8e0a89f74`, unseal `e6ea32afbfa4aaf4e693cdea8af1c1121c0cadd1` and /001 publication `b011231afb8634b29b13c339ca3d7e3e5dd0ed58`. [Custody report](https://github.com/jackgumpe/eledgercare/blob/b011231afb8634b29b13c339ca3d7e3e5dd0ed58/docs/agent-reports/eld-winrt-custodian/WP-0022/001_2026-11-21_research_eld-winrt-custodian.md)
- Reviewed harness `e8168f54e1c9fc6d7e81babbeb8d749353922c1c`, blind predictions `dc033d1491e930eba933f6afd694a5ecde1ea8f7`, author timing/witnesses `aeb17ed97dbd84dc1a99f7b6cc9269cf658a3008` and /002 publication `a1c2d41cfe39a8fffdffe157633dc1247b32ad4b`. The scorer was frozen at `393e8faeaa5ebec777e949601fe1880bbf78450b`. The release was `d9118c73fc4fa71e9c09ad52b0a49e8bb17f3993` and the blind-freeze receipt was `1da1c80bebdcd6ca7a8285c5b3601bd8c0675b1b`. [Author report](https://github.com/jackgumpe/eledgercare/blob/a1c2d41cfe39a8fffdffe157633dc1247b32ad4b/docs/agent-reports/eld-winrt-author/WP-0022/002_2026-11-21_research_eld-winrt-author.md)

## Results

| R / W paired outcome | All 42 | Setup 16 | Post-break 26 |
| --- | ---: | ---: | ---: |
| Pass / pass | 6 | 0 | 6 |
| Pass / fail | 24 | 12 | 12 |
| Fail / pass | 0 | 0 | 0 |
| Fail / fail | 12 | 4 | 8 |

| Independent source and output check | R | W |
| --- | ---: | ---: |
| Correctly owned ordinary values | 24/36 | 0/36 |
| Exactly one correctly spelled source inside each ordinary Amount cell | 36/36 | 36/36 |
| Ordinary values with any explicit flag | 12 | 36 |
| Ordinary values with a flag on the Amount source itself | 8 | 36 |
| Explicitly flagged ambiguous Amounts | 2/2 | 2/2 |
| Known empty cells safely withheld / positively represented | 4/4 Â· 0/4 | 4/4 Â· 0/4 |
| Populated cells lacking any intersecting source word | 0 | 0 |
| Silent wrong or duplicate assignments, within / outside keyed rows | 0 / 0 | 0 / 0 |
| Silent margin-note captures opposite a value / a blank | 0 / 0 | 0 / 0 |
| All flags on keyed rows / outside keyed rows, in events | 24 / 12 | 134 / 67 |
| Mistranscribed correctly owned values | 0 of 24 | No assigned values |

The six jointly passing rows were the four known blanks and two indistinguishable continuations. All four blanks had zero intersecting amount words. All four note pairs, including both equal-spelling pairs, had zero silent captures. Both arms observed exactly one correctly spelled source in each of the two ambiguous Amount regions as well. N07 and N08 reuse both pages byte for byte. Their opposite hidden interpretations justify review on the same visible continuation. The corpus has eight logical forms and seven visibly distinct two-page forms.

## First divergences and frame witnesses

The following traces are part of this review. Each document file indexes the two arms by page and original line number, with verbatim native line text, every ordered literal, point rectangle, source ID, original prediction and exact stack indices immediately before and after that line. The `frame_states` array expands those indices into the full frames, including heading/header references, anchors, rules, header page and grid. Each keyed row carries its truth rectangles, all participating line IDs, measured physical and saved-header deltas, and spatial word correspondences with four-corner differences. Coordinate units are PDF points. The numbers below identify the relevant original line and printed source in those records.

| Witness | First observed difference and resulting decision |
| --- | --- |
| N01-T01, parent setup | R page 1 line 4 supplies the complete four-word schema. W reads `Date Description` on line 4 and `Ref Amount` on line 7 after intervening body/caption words. R line 5 posts `58.40` at x0 155.04 with state 2 â†’ 2. W line 8 reads it at 155.28, aligned exactly to the observed header, with state 1 â†’ 1. That parent has no schema, rules or anchors. [Exact paired trace](../../../reviews/WP-0022/witnesses/N01.json) |
| N01-T02 and T03, typed child with incomplete parent | W captures the full child header on page 1 line 10. For T02 the Amount rectangle matches R in all four coordinates, and W's left edge is only âˆ’0.24 from its saved child anchor. The same-headed grid identifies the child. The reader requires anchors on every frame and flags W line 11, state 6 â†’ 6. On T03 W splits R's page-two line into lines 1 and 2. The child anchor still fits, but the missing parent also leaves cross-page grid matching without a complete set of rules. State 6 â†’ 6. [Exact paired traces](../../../reviews/WP-0022/witnesses/N01.json) |
| N03-T01, T03 and T06, right-aligned and wrapped | R T01 amount starts +10.80 from the saved parent Amount header, exceeding the 3-point tolerance. R T03 has a typed child on the correct grid. Its value is âˆ’8.64 from the child amount header, and its continuation line offers `packing` as a second terminal candidate. R T06 has a captured parent and a matching parent grid. Its parenthetical amount starts âˆ’10.56 from the parent anchor. Wrapped lines offer `flue` and `seal` separately. R retains both typed frames before and after those lines, 4 â†’ 4. W emits T06's actual value on line 24, separate from the description, at âˆ’10.80 from the physical header. W's saved parent and child schema vectors are empty, 5 â†’ 5. [Exact paired traces](../../../reviews/WP-0022/witnesses/N03.json) |
| N03-T04 and T07, terminal margin note | R's T04 line 4 contains the real `9.00` followed by another printed `9.00` in the margin. The selected last word starts at 533.04, +76.32 from the child header. The real value ends at 492.96. R flags the note, 4 â†’ 4. W separates the two printed amounts into lines 23 and 26 and flags each, 5 â†’ 5. T07 shows the distinct-spelling case where R selects margin `214.75` after `-8.75`. T05 shows the same note opposite a true blank, with no Amount source in either arm. [Exact paired traces](../../../reviews/WP-0022/witnesses/N03.json) |
| N05-T03 through T06, rapid siblings and returns | R posts original child A, restores the complete parent for one row, captures the second sibling, then restores the exact parent again. Its states are 4 â†’ 4, 4 â†’ 2, 6 â†’ 6, and 6 â†’ 2 on those amount lines. W emits the earlier child A amount `63.80` at page 2 line 12 **after** emitting child B's heading on line 7. At the amount W has the later child's heading with empty anchors, 8 â†’ 8. Its one-row parent amount aligned exactly with the physical parent header at line 5, but the parent still lacked typed rules. Its later return at line 17 has the same prerequisite failure. [Exact paired traces](../../../reviews/WP-0022/witnesses/N05.json) |
| N07/N08 ambiguous twins | Renderer state 4 â†’ 4 had two fully typed frames with identical anchors on the ambiguous amount. W state 5 â†’ 5 had two untyped frames. Both flagged the same `41.60`, with no observable return cue to distinguish the hidden keys. [Parent-key twin](../../../reviews/WP-0022/witnesses/N07.json) Â· [Child-key twin](../../../reviews/WP-0022/witnesses/N08.json) |

The mirrored N02, N04 and N06 targets were also replayed in full. W captured zero typed parent schemas and a typed child in only one document. No W witness combines a previously captured typed parent, an observable return cue and a wrong retained/restored frame independent of parsing. The rendered right-alignment and last-word defects are observed with correct typed frames available. I find no basis for SPDB from this packet. [N02](../../../reviews/WP-0022/witnesses/N02.json) Â· [N04](../../../reviews/WP-0022/witnesses/N04.json) Â· [N06](../../../reviews/WP-0022/witnesses/N06.json)

## Source, custody and timing checks

I inspected the original reader, original detector, native capture worker, projection, freeze journal, scorer, fixture generator and author witnesses. Before the release I inspected only committed public materials. After release, the exact key SHA-256 matched `ef32bc6bff114900deda32d6f161dce4bf311930f7802dc23c9a6dd36d8e40df`. I regenerated the fixtures in reviewer-owned scratch from the released generator and compared all 28 generated files, 354 renderer word instances, sibling heading occurrences, banners and all four note pairs. The reader bytes matched Git SHA-256 `62aec65d9a3c363cfbe94ba8c22f7e5b9f17df279790b361c46f6d5850ed6be7`. I verified source stamps for the two capture files and original detector/format modules from Git objects.

The sensor verifier checked 147 archived file digests, full-resolution RGB and independently decoded opaque BGRA pixel digests, serial capture start/finish chronology, raw digests, group/word order, both shared grids, en-US resource and DLL hashes on the host, and every pixel-to-point projection. All 16 reader CLI outputs matched the blind bytes. The controlled frame replay also matched all 348 complete line histories and 182 target events against the official scores/witnesses on `d7d3a5f717662e8e0980e86dd726911e7d04fa3e`. This included both positions of each full stack, the candidate, heading, banner and Amount-role checks, recorded reasons and physical/saved header deltas. Every successful post also carried the expected physical Amount header. I accepted the remote /001 and /002 conclusions on the artifacts above. [Ordered sensor reconstruction](../../../reviews/WP-0022/sensors.json) Â· [Prediction SHA-256 receipts](../../../reviews/WP-0022/cli-prediction-hashes.json)

| Milliseconds per page appearance, 16 logical pages | R | W |
| --- | ---: | ---: |
| Standalone elapsed, shared grid plus arm assembly/reader and W cold worker | 47.69 | 901.24 |
| Measured contributing process CPU | 44.92 | 644.53 |
| Elapsed including input decoding, hash verification and staging | 174.18 | 1,027.73 |
| Measured process CPU including those preparation stages | 165.04 | 764.65 |

One physical job served each of 14 unique rasters. The native request averaged 93.53 ms elapsed and 99.33 ms worker CPU on those 14. Cold W elapsed includes worker startup and exit. Its CPU combines measured worker-script and waiting-controller CPU and omits unmetered startup/shutdown and any execution charged elsewhere. The Python process counter did not advance in the small assembly/reader intervals. The comparison reuses each grid across arms and excludes renderer creation and Git I/O. The author's initial PowerShell module-resolution failure preceded the first native-call receipt. The eventual archive contains 14 uniquely journaled calls and 14 completed original grids. The review invoked neither operation.

## Execution and inventory

Exact commands were run from the reviewer worktree, with `$py` naming the assigned Python 3.12.10 interpreter. The archive exports in `.review-scratch` came from `git archive --format=zip <full-revision> <assigned-subtree>` using the blind, public, scorer and unseal revisions listed above. For the blind byte comparison I ran the reader CLI once for each arm/document and compared the output bytes to its prediction file.

```powershell
$py = 'C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe'
$v = 'docs/reviews/WP-0022'
$f = '.review-scratch/docs/fixtures/WP-0022'
$e = '.review-scratch/docs/research/WP-0022/evidence'
$c = '.review-scratch/docs/coordination/WP-0022'
& $py -B "$f/generate.py" .review-scratch/regenerated
& $py -B "$f/verify_custody.py" $f "$f/generate.py" .review-scratch/regenerated
python -B "$v/test_replay.py" -v
python -B "$c/test_score.py" -v
python -B "$c/score.py" "$f/truth.json" $e .review-scratch/frozen-scores.json
& $py -B "$v/sensors.py" --public "$f/public" --evidence $e --out "$v/sensors.json"
& $py -B "$v/replay.py" --source docs/research/WP-0021/read_scope.py --truth "$f/truth.json" --evidence $e --out .review-scratch/final
python -B "$v/certify.py" .review-scratch/final d7d3a5f717662e8e0980e86dd726911e7d04fa3e "$v/comparison.json"
python -B "$v/package.py" .review-scratch/final "$v/witnesses"
```

The seven frozen scoring tests and three independent regression tests passed. An early reviewer-only synthetic check expected abstention at a +3.00-point offset. The frozen source accepts the equality endpoint. I corrected the test before the study replay, retaining checks at +3 and +4. Product code, native inference, a second grid extraction and a second live timing study were outside the review. Generalization beyond these constructed forms remains unmeasured.

All deliverables lie below `docs/reviews/WP-0022/`. The five scripts are `replay.py`, `test_replay.py`, `sensors.py`, `package.py` and `certify.py`. The four receipts are `summary.json`, `comparison.json`, `sensors.json` and `cli-prediction-hashes.json`. The eight document traces are `witnesses/N01.json` through `witnesses/N08.json`. This canonical report is the sole subsequent metadata path. External effects were isolated scratch copies and the owned private branch push. Temporary review exports were removed after the results were archived. No outstanding material disagreement remains. Root may close the one-study lane at /004. [Complete review deliverable](https://github.com/jackgumpe/eledgercare/compare/10cbfb0fa8de2befb28a69c6fb10da90ca737219...8d1850a711070e15521e2554361de09b4e6129a7)
