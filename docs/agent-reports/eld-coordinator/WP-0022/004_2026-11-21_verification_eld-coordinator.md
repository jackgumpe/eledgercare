# WP-0022 / 004 — Windows reads the amounts, but its lines do not establish ledger ownership

| Report metadata | Record |
| --- | --- |
| Report path, sequence and category | `docs/agent-reports/eld-coordinator/WP-0022/004_2026-11-21_verification_eld-coordinator.md`, reserved coordinator verification 004. [Assignment](../../../coordination/WP-0022/assignment.md) |
| Author and publisher | eld-coordinator, continuous native Codex CLI session on Windows. Actual coordinator backend and effort unexposed. Three fresh Codex role sessions requested xhigh. |
| UTC, repository and worktree | 2026-11-21T07:01:45Z · private `jackgumpe/eledgercare`, `coordination/bootstrap`, `C:/Users/jackg/Asp.net Projects/eledgercare` |
| Base and decision deliverable | `967ac0830d0acb73acd0e8b0e29f37e4732d0237` · `99e848ad427c4110480f0bc4bcc253ca60eb181b` |
| Status and next owner | Accepted diagnostic finding. The single paired Windows study is closed. Further work requires its own decision. |
| Related reports | [Custody /001](https://github.com/jackgumpe/eledgercare/blob/b011231afb8634b29b13c339ca3d7e3e5dd0ed58/docs/agent-reports/eld-winrt-custodian/WP-0022/001_2026-11-21_research_eld-winrt-custodian.md) · [Research /002](https://github.com/jackgumpe/eledgercare/blob/a1c2d41cfe39a8fffdffe157633dc1247b32ad4b/docs/agent-reports/eld-winrt-author/WP-0022/002_2026-11-21_research_eld-winrt-author.md) · [Independent review /003](https://github.com/jackgumpe/eledgercare/blob/80022dc0d0b501a9a19972291e7129df8a5fa1f0/docs/agent-reports/eld-winrt-reviewer/WP-0022/003_2026-11-21_review_eld-winrt-reviewer.md) · [WP-0021 disposition](../WP-0021/003_2026-11-21_verification_eld-coordinator.md) |

## Disposition

The frozen saved-frame reader failed end-to-end ownership on the Windows observations. Windows returned the exact printed amount at the correct spatial location on **36/36 ordinary populated rows**. The reader assigned **0/36** to the right property, ledger section and Amount column. It explicitly flagged all 36. On the paired renderer inputs, the same reader correctly assigned **24/36**. Independent reproduction matched all 16 prediction files and every paired classification. [Complete decision](../../../coordination/WP-0022/decision.json) · [Source-word readback](../../../coordination/WP-0022/diagnostic-readback.json)

The first demonstrated obstacle on Windows was the interface between native line organization and header parsing. Each rendered parent header contains `Date Description Ref Amount` on one line. Windows split each parent header across two or more lines. The frozen reader needs a complete typed header on one line to save column positions. It opened a parent in every document but captured a complete parent column schema in **0/8**. It captured one child schema. Even that child's correctly positioned amount could be rejected because the all-open-frames check required anchors from the parent. There was no qualifying instance of a previously captured parent schema being lost despite an observable return cue. The strict SPDB trigger was unmet. [Reader](../../../research/WP-0021/read_scope.py) · [Paired witness guide](../../../coordination/WP-0022/witness-guide.md)

| Primary target measure | Rendered | WinRT |
| --- | ---: | ---: |
| Exact ordinary value ownership | 24/36 | 0/36 |
| Unambiguous ordinary value rows with an explicit flag | 12/36 | 36/36 |
| Among these, amount itself explicitly flagged | 8/36 | 36/36 |
| Ordinary populated parent returns correctly owned | 6/10 | 0/10 |
| Known blank safely withheld / positively represented | 4/4 · 0/4 | 4/4 · 0/4 |
| Genuinely ambiguous rows rightly flagged | 2/2 | 2/2 |
| Unflagged wrong posts inside / outside keyed rows | 0 / 0 | 0 / 0 |
| False note captures opposite populated / blank targets | 0/4 · 0/4 | 0/4 · 0/4 |
| Populated targets with zero intersecting words | 0 | 0 |
| Transcription-only mismatches among correctly owned amounts | 0 of 24 | No owned values |

| Paired outcomes | Windows passes | Windows fails |
| --- | ---: | ---: |
| Rendered passes | 6 | 24 |
| Rendered fails | 0 | 12 |

The six both-pass results consist of four known blanks safely withheld and two ambiguous rows flagged. In the Windows arm the ambiguous amounts were flagged with missing anchors. The two visibly identical ledgers had opposite intended continuations, so guessing either way would be unsound. No reader output positively declared a blank. The research report and primary score also give separate setup, post-break, out-of-band and flagged-event counts. [Full scores and row IDs](../../../coordination/WP-0022/scores.json)

## Failure witnesses

- **An amount stays in place while its header loses its structure.** In N01-T04 the renderer's second-page parent row ended with `71.50` at [155.04, 295.20, 180.24, 302.88] pt. The Windows amount box on native line 4 has exactly those coordinates. Windows had emitted the original parent header as `Date Description` and `Ref Amount`, separated by other lines. The rendered stack popped the child and restored the typed parent. The Windows stack kept both frames with the parent's header unobserved and flagged the literal. N01-T02 and T03 show how that missing schema also prevents local and continuation matches in a correctly captured child. [Complete lines, boxes and frames](../../../coordination/WP-0022/witness-guide.md)
- **The renderer exposes two additional frozen-rule defects.** On eight populated rows the correct scope was captured, but right alignment put the price's left edge beyond ±3 pt of the header. On four further rows a numeric margin note became the final candidate. In N03-T04 both the cell and the note say `9.00`; only the fourth source word belongs to the cell, while the terminal fifth word is 59.76 pt further right. The reader flagged the note. In N03-T06 the parenthetical price was 10.56 pt left of its saved header, and two wrapped lines separately offered description words as amount candidates. [Full example traces](../../../research/WP-0022/analysis/witness-rows.md) · [N03 data](../../../coordination/WP-0022/witnesses/N03.json)
- **Native reading order can change the active child.** In N05-T03 Windows emitted a later child B heading before child A's earlier `63.80`. Its receipt records the new child at the instant the older amount is considered. The parser had already missed the parent column anchors. This supports a reading-order diagnosis. [N05 lines and live state history](../../../coordination/WP-0022/witnesses/N05.json)

## Measurement boundary and timing

Eight fresh two-page synthetic ledgers contributed 42 logical targets (16 setup and 26 post-break). An intentionally indistinguishable pair shares both page images, leaving 14 distinct 300-DPI RGB rasters. Each was recognized by en-US Windows OCR and processed through the frozen table detector exactly once. Both arms share the raster and grid. The renderer supplied its line/word structure; Windows supplied native ordered lines/words and pixel rectangles, projected onto the identical 612 × 792 point frame. Windows build 26300.9974 was the measured installation; the DLL, English resource, pixel format and stride are pinned in the native receipts. [Custody pre-counts](../../../fixtures/WP-0022/precounts.json) · [Capture evidence](../../../research/WP-0022/evidence)

| Mean cost, milliseconds per page | Elapsed | Measured process CPU |
| --- | ---: | ---: |
| R, grid + observation construction + reader | 47.69 | 44.92 |
| W, same stages + cold Windows worker per page | 901.24 | 644.53 |
| R including verified PNG preparation and staging | 174.18 | 165.04 |
| W including verified PNG preparation and staging | 1,027.73 | 764.65 |
| Recognition call alone, 14 actual unique pages | 93.53 | 99.33 |

The first four means weight all 16 logical page appearances. The standalone arms each include a grid cost; the paired study paid it once for each distinct raster. The cold-worker elapsed figure covers process startup through exit. Its CPU figure includes the measured in-script worker and waiting parent, excluding pre-script/exit CPU and work charged elsewhere. Offline generation, publishing and a failed initialization before the first OCR call sit outside these timings. This was an ownership test on small fresh forms, without a throughput claim on the 60-page archive. [Detailed timings](../../../research/WP-0022/analysis/timing-and-audit.json)

## Verification and change inventory

1. Fetched the integration head, checked all reservations and reserved WP-0022 at `10cbfb0fa8de2befb28a69c6fb10da90ca737219`. Used the verified WP-0021 closure instead of the mistyped predecessor SHA in the supplied handoff. Integration preserved the user's unrelated worktree edit.
2. The custodian committed the input files and answer digest before execution. The coordinator pinned a new spatial ownership scorer with seven fixture-independent checks and released the exact reader `613a5ff92e9dd6783b8950529fbda76f6c21e9d3`, detector `a0e738bc03e515999659dda09c5ee76d08fb37df`, capture harness and public manifest at `d9118c73fc4fa71e9c09ad52b0a49e8bb17f3993`. Only the assigned Windows operator made live recognition calls. The first launch failed while resolving a PowerShell module before recognition. The process-local module path correction let the unchanged harness reuse the existing grid. [Release](../../../coordination/WP-0022/release.json) · [Author execution log](https://github.com/jackgumpe/eledgercare/blob/a1c2d41cfe39a8fffdffe157633dc1247b32ad4b/docs/agent-reports/eld-winrt-author/WP-0022/002_2026-11-21_research_eld-winrt-author.md)
3. Read back 147 pre-key file digests, 14 start/finish/raw records and 14 grid receipts. Confirmed the same per-page grid in both arms, native line text/ordering and all 342 logical WinRT word references and rectangle projections. Both twin documents produced identical outputs in each arm. The coordinator committed the blind receipt before authorizing the custodian to publish the key. The opened truth SHA-256 was `ef32bc6bff114900deda32d6f161dce4bf311930f7802dc23c9a6dd36d8e40df`, matching the pre-run commitment. [Pre-key receipt](../../../coordination/WP-0022/blind-freeze.json)
4. Ran the frozen scorer, then separately replayed the original reader with per-line live frame recording and required equality to the blind predictions. The independent reviewer rebuilt the sensor projections from frozen raw bytes, reran the reader in isolation and reconciled per-target verdicts, exact literals, spatial provenance, frame identity and timings. [Research witnesses](../../../research/WP-0022/analysis/witness-rows.md) · [Independent reproduction](https://github.com/jackgumpe/eledgercare/blob/80022dc0d0b501a9a19972291e7129df8a5fa1f0/docs/agent-reports/eld-winrt-reviewer/WP-0022/003_2026-11-21_review_eld-winrt-reviewer.md)

The independent report's original Git blob misdecodes several arrows, minus signs and punctuation marks. A reversibly decoded display preserves the reviewer’s wording and all numeric findings. Its body round-trips to the exact immutable publication bytes. [Readable independent report](../../../coordination/WP-0022/readable/independent-review.md)

Reproduction of the decisive post-capture checks from the repository root uses separate scratch outputs. `$scratch` below is an existing empty owned directory.

```powershell
$packet = 'docs/coordination/WP-0022'
$truth = 'docs/fixtures/WP-0022/truth.json'
$evidence = 'docs/research/WP-0022/evidence'
python -B "$packet/test_score.py" -v
python -B "$packet/score.py" $truth $evidence "$scratch/scores.json"
python -B "$packet/trace.py" docs/research/WP-0021/read_scope.py $truth $evidence "$scratch/scores.json" "$scratch/witnesses"
```

The packet added fixtures and custody materials under `docs/fixtures/WP-0022/`, the paired sensor harness and archived output under `docs/research/WP-0022/`, independent checks under `docs/reviews/WP-0022/`, and the coordination handoff, scorer, release, evidence and decision under `docs/coordination/WP-0022/`. Each role published its own reserved report. The coordinator updated `INDEX.md` and `CURRENT.md`. Scratch stays under `eledgercare-worktrees/wp0022-data`; the four owned branches were published to the private remote. The final durable publication readback and ledger closure follow this report. [Full base-to-decision inventory](https://github.com/jackgumpe/eledgercare/compare/967ac0830d0acb73acd0e8b0e29f37e4732d0237...99e848ad427c4110480f0bc4bcc253ca60eb181b)

The finding applies to the seven distinct visible two-page documents in this study. Fixing the Windows line-to-table interface would be a separate intervention. The packet ends at diagnosis, with matrix memory parked.
