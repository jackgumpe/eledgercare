# WP-0018 / 001 — Windows grid and reference-box replay on the H and A archives

Removing the archived grids recovered **0** incorrect reference cells. It lost **1** correct cell on H and **22** on A. Each lost cell had an empty reference value. The grid supplied an explicit empty string, and the frozen scorer returned JSON `null` when the reference-box fallback selected zero spans. Every lost cell was noncritical. Full prose-line records, prose-critical records, per-page text edit counts, and packet completeness matched across arms. [H paired ledger](../../../research/WP-0018/pair/evidence/H/cells.jsonl) · [A paired ledger](../../../research/WP-0018/pair/evidence/A/cells.jsonl)

| Metadata | Value |
| --- | --- |
| Report path and category | `docs/agent-reports/eld-rd-astra/WP-0018/001_2026-11-20_research_eld-rd-astra.md` · research |
| Reservation | [WP-0018 / 001 in the release ledger](https://github.com/jackgumpe/eledgercare/blob/918701ae318b01395b911b9dbdf597e43908665b/INDEX.md#wp-0018-windows-ocr-archive-diagnostic) |
| Author and publisher | eld-rd-astra, native Codex delegated author, task `/root/archive18_pair`. Effort requested xhigh. Exact serving model and applied effort unexposed. |
| Environment | Local Windows 11 build 26200, PowerShell, CPython 3.12.10 AMD64, Git 2.55.0.windows.1 |
| Timestamp | 2026-11-20T05:29:27Z |
| Repository, owned branch and worktree | `jackgumpe/eledgercare` · `research/wp-0018-windows-archive` · `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\archive18-pair` |
| Release base | `918701ae318b01395b911b9dbdf597e43908665b` |
| Baseline and constructed control freeze | `41195166a382108557394bed92ddf47a54452488` |
| Full executable deliverable | `3a1591768828bf72a9cce42db05f0d7c95f6cd60` |
| Data and checksum receipts | `01625378954a55da0fe7ce93c5cbb3b2e174c797` |
| Windows checksum checkout metadata | `fcb2126b545e77481bd0e601b87d67410b4fdc57` |
| Previous report | First report in this packet. Historical WP-0015 review supplies the Windows baseline. [Scored H/A publication](https://github.com/jackgumpe/eledgercare/blob/ce4206f20d63101f6344121eaaeeeb86d2ec85a0/docs/reviews/WP-0015/evidence/scored-H-A.json) |
| Related work and next owner | WP-0018 / 002, eld-archive-tracer, owns original-word attribution. WP-0018 / 003, eld-rd-reviewer, owns independent reproduction. Status **ready-for-review**. |

## Scope and custody

The question is whether the scorer's choice between an emitted grid and ordered word spans inside labelled reference boxes changes any H/A cell verdict. Evidence comes from two archived synthetic Windows captures. Neither arm runs recognition. The coordinator supplied separate owned input copies and a successful admission receipt with SHA-256 `64809c0044a081d2335b461070b48a7dd7536c11b0364ccddb629041a0c8e3bf`. The frozen scorer SHA-256 is `1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7`. [Assignment](../../../coordination/WP-0018/assignment.md)

The author independently checked the source PDF, truth and raster commitments, full named Windows inventory, plan and timing request, page sequence, RGB pins, raw source/page/RGB identity, window coverage, and equality of each archived page to its prediction entry. The H inventory blob is `8e72acfc3f307da7e0f074edd937e61ce22f64ce` for `h-r1-ab/04-h-windows`. The A blob is `156e53d20f448d2410e218b961ae6a1630e9a978` for `a-recovery-ab/04-a-windows`. The baseline receipts list all 20 H and 188 A input-file SHA-256 values and the four common control-file hashes. All recorded inputs were available. [H receipt](../../../research/WP-0018/pair/evidence/H/baseline.json) · [A receipt](../../../research/WP-0018/pair/evidence/A/baseline.json)

## Baseline, witness order and method control

Each baseline score came from a separate invocation of the pinned CLI. Every Windows score detail matched the archived historical score after omitting its separate native-control comparison field. All official counts and faults, supplementary numeric/page/flag checks, source-linked lookups, and Windows observations in the two published sets of examples also matched. H reproduced 15/20 cells, 13/16 exact lines, and 8/19 unflagged wrong criticals. A reproduced 235/300, 237/288, and 94/252. Both scored zero extra cells.

The constructed page used two separate processes invoking the frozen `layout` function on the kit's actual inputs. Its first cell went from `ZZ` to the correct `A1` and the second from correct `B2` to `82`. Both arms scored 1/2. Their complete line and prose-critical records agreed, including the observed `ID AB C-123`. The method detects offsetting changes. [Constructed input](../../../coordination/WP-0018/kit/constructed-scorer-control.json) · [Executed control](../../../research/WP-0018/pair/evidence/constructed.json)

Before either H/A treatment ran, the coordinator confirmed the four original case traces from eld-archive-tracer, naming source `acf13b71f026980e99a10e7019a32f890f59f3cc` and witness-evidence SHA-256 `64b8e29bcacee8d0978e422bfc3f3c6471877a5c2b30eb69104891f7c073c5a8`. The paired executable was committed next. Each treatment scored the same truth in a fresh frozen-scorer process.

## Paired results

| Packet | Correct grid → fallback | Wrong → right | Right → wrong | Wrong both | Right both | Already using fallback | Unavailable score rows | Extra cells before / after |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H, 4 pages | 15 → 14 of 20 | 0 | 1 | 5 | 14 | 0 | 0 | 0 / 0 |
| A, 60 pages | 235 → 213 of 300 | 0 | 22 | 65 | 213 | 0 | 0 | 0 / 0 |

All 20 H reference cells originally used the matched grid on p2, where table intersection-over-union (IoU) was 0.996970. All 300 A cells used matched grids on 12 pages, each at IoU 0.996667. The scorer's acceptance threshold is 0.5. All 320 treatment rows used reference-box fallback. Every cell flag was false in both arms. All archived and treatment scores were available, including rows for which the scorer explicitly observed JSON `null`.

On H, p2 r3c4 was the sole loss. On A, all 22 losses were labelled blank values in column 5. The 5 additional A cells below had a nonempty expected value. The grid supplied an empty string and fallback returned `null`, so their verdict stayed wrong. Every other wrong-both row kept its original observation. The raw-word evidence is needed to determine why any expected nonempty value was absent or different.

| A location, table 1 | Expected | Critical |
| --- | --- | --- |
| p5 r5c1 | `5-4` | no |
| p15 r4c2 | `11III-558` | yes |
| p20 r5c1 | `20-4` | no |
| p30 r3c2 | `11I18-710` | yes |
| p30 r5c1 | `30-4` | no |

| Invariant or check | H, both arms | A, both arms |
| --- | ---: | ---: |
| Complete packet, reported faults | yes, 0 | yes, 0 |
| Character edits / reference characters | 15/570 | 257/8,821 |
| Exact lines / reference lines | 13/16 | 237/288 |
| Wrong prose criticals / prose criticals | 3/8 | 51/108 |
| Wrong table criticals / table criticals | 5/11 | 43/144 |
| Unflagged wrong criticals / criticals | 8/19 | 94/252 |
| Flagged criticals | 0 | 0 |

The executable reads back the serialized prediction copy and compares canonical JSON bytes for every prediction field after excluding per-page table arrays. It checks that each new array is empty. Only H p2 and A p5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55 and 60 had nonempty arrays to remove. It compares full ordered line records including all reported boxes, full prose-critical records including flags, and per-page reference lengths and edit distances. It also checks packet identity, order, state, faults and extra-page records. Receipts store hashes of these verified equal canonical projections, exact structural-change pointers, and hashes of both prediction and score files. Serialization of the two prediction files differs. The structural comparison explicitly retains every page's text, spans, flags and source links. [H pair receipt](../../../research/WP-0018/pair/evidence/H/pair.json) · [A pair receipt](../../../research/WP-0018/pair/evidence/A/pair.json)

## Location records and change inventory

Each JSON Lines row is keyed by `packet` and `at`, the frozen scorer's one-based location. `reference_pointer` locates the truth object and `score_pointer` indexes the cell in either complete CLI result. These JSON pointers are zero-based. `before.selected` and `after.selected` are relative to the hash-bound archived page object. For fallback they give the original span indices in the scorer's join order. An empty list represents zero selected spans. Both arms record match mode, IoU, observed value, correctness and flag. Joining the ledger to the tracer's records on the two keys attaches original-word provenance. Attribution is owned by /002. No causal distribution is inferred from paired verdicts in this report.

| Change | Paths relative to `docs/research/WP-0018/pair/` | Purpose |
| --- | --- | --- |
| Source, first freeze | `baseline.py`, `method_control.py` | Historical admission/score reproduction and two-arm invented control |
| Source, full freeze | `paired.py` | Isolated score, structural and per-page checks, both observations per location |
| Evidence | `evidence/constructed.json` | Constructed-control full layouts |
| Evidence | `evidence/H/baseline.json`, `evidence/H/pair.json`, `evidence/H/cells.jsonl` | H inputs, decisions, invariants and 20 paired cells |
| Evidence | `evidence/A/baseline.json`, `evidence/A/pair.json`, `evidence/A/cells.jsonl` | A inputs, decisions, invariants and 300 paired cells |
| Evidence checkout metadata | `evidence/.gitattributes` | Retain LF bytes of checksum-bound JSON Lines files on Windows |
| Subsequent report metadata | Own reserved /001 report path above | Publication and handoff |

## Verification and handoff

Executed in the owned worktree. Each command exited 0. The two baselines and the constructed control ran at `41195166a382108557394bed92ddf47a54452488`. Both treatments used `3a1591768828bf72a9cce42db05f0d7c95f6cd60`, which preserves the baseline executable. Each treatment reverified the archive before and after the separate scorer call.

```powershell
python -B docs/research/WP-0018/pair/baseline.py ../wp0018-data/pair/inputs H ../wp0018-data/pair/r01/H
python -B docs/research/WP-0018/pair/baseline.py ../wp0018-data/pair/inputs A ../wp0018-data/pair/r01/A
python -B docs/research/WP-0018/pair/method_control.py ../wp0018-data/pair/inputs ../wp0018-data/pair/r01/control
python -B docs/research/WP-0018/pair/paired.py ../wp0018-data/pair/inputs H ../wp0018-data/pair/r01/H ../wp0018-data/pair/r02/H
python -B docs/research/WP-0018/pair/paired.py ../wp0018-data/pair/inputs A ../wp0018-data/pair/r01/A ../wp0018-data/pair/r02/A
```

Full transient predictions and scores are retained under the author's sibling `wp0018-data/pair/r01` and `r02`. The reviewer can substitute their own input copy and fresh output directories. After copying the seven bounded evidence files, the author checked them against the generated bytes and read back the Git objects. Git warned that a subsequent checkout could change JSON Lines line endings. The scoped checkout setting addresses that warning and each receipt's JSONL checksum matches its Git blob contents. No runtime exception or failed invariant occurred in either decisive comparison. Source inspection and reproduction of the original WinRT witnesses belong to the separate /002 and /003 owners. No renderer, reader, GPU job, production change or Packet B evaluation was run.

**Recommendation.** Retain explicit blank cells when interpreting this archive. Reference-box fallback recovered none of the existing errors and added 23 blank-cell losses. It uses labelled cell positions, and its scores cannot estimate deployment accuracy. For the remaining critical errors, base the next investigation on the first divergence visible in /002's original-word traces. The paired comparison alone establishes representation sensitivity only on the rows where observations changed. Unattended use remains gated and no repair has been tested.

The reviewer should inspect and rerun the candidate, reconcile counts and selected pointers, and compare the four witnesses with original source bytes. The coordinator owns final disposition. The author confirmed remote evidence revision `01625378954a55da0fe7ce93c5cbb3b2e174c797` by exact branch lookup. Final report publication and its remote SHA are handed to the coordinator after this report is committed. [Source diff](https://github.com/jackgumpe/eledgercare/compare/918701ae318b01395b911b9dbdf597e43908665b...3a1591768828bf72a9cce42db05f0d7c95f6cd60) · [Evidence tree](https://github.com/jackgumpe/eledgercare/tree/01625378954a55da0fe7ce93c5cbb3b2e174c797/docs/research/WP-0018/pair/evidence)
