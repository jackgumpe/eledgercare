# WP-0030 / 002 — Independent review of the cached owner-score trace

**Accepted.** Both probes gave a small positive signed response at the first title. After the printed owner declaration, M1 first returned to a positive response at write 9 and M3 at write 12. Neither probe ever ranked both twins correctly at the same step. The independent replay reproduced every historical boundary and all seven deterministic author files, totaling 1,306,128 identical bytes. [Byte comparison](https://github.com/jackgumpe/eledgercare/blob/6d62d773399c53c8efbbce0ee38067ea474a7d4d/docs/reviews/WP-0030/evidence/comparison.json)

- Report path `docs/agent-reports/eld-rd-reviewer/WP-0030/002_2026-11-22_review_eld-rd-reviewer.md`
- Category review, sequence 002, author and publisher `eld-rd-reviewer`. [Reservation](https://github.com/jackgumpe/eledgercare/blob/f19d7fdca840af7b81e6a0bb1edd062d690898de/INDEX.md#wp-0030-cpu-trace-of-every-span-through-the-owner-postings)
- Timestamp 2026-11-22T20:15:09Z
- Session fresh native GPT-6-based Codex subagent `/root/w30_review`, thread `01a204da-e5c5-76a3-a76a-7ffcc34e1ab7`. Exact backend variant and effective effort unexposed. Assignment requested xhigh. The reviewer had no role in either cloud design contribution or the WP-0030 author's implementation, execution or report.
- Environment Windows 11, PowerShell, Python 3.12.10, PyTorch 2.13.0+cpu, NumPy 2.2.6, CPU FP32, one computation thread and one interop thread
- Repository `jackgumpe/eledgercare`, branch `review/wp-0030-span-trace`, worktree `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w030-review`
- Base and reservation `f19d7fdca840af7b81e6a0bb1edd062d690898de`. Previous reviewer report in this packet none.
- Independent source `603cfbc85c259112fb76ea7c1b9c514557149653`, replay evidence `7d65875a1ff2d7ad8a008ea83f5484507dbd5db3`, comparison source `a6bf30a8682eedb4b39cbedd188966ba6de62599`, deliverable including comparison receipt `6d62d773399c53c8efbbce0ee38067ea474a7d4d`
- Reviewed author source `447a9e7adc2dbd81933510068742ba1b82bbe84d`, evidence `6c9ecae26aff3b2faa47d90d2f16bcee12b8a191`, canonical /001 publication `81b96a16a6ca9d27186ce8e5d68d955557713f73`. [Author report](https://github.com/jackgumpe/eledgercare/blob/81b96a16a6ca9d27186ce8e5d68d955557713f73/docs/agent-reports/eld-owner-probe/WP-0030/001_2026-11-22_research_eld-owner-probe.md)
- Status accepted. Next owner `eld-coordinator` for integration and packet disposition.

## Findings

The four zero-state reads gave exact ties and δ = 0. The signed response δ subtracts the Cedar document's Alder-minus-Cedar score margin from the Alder document's margin. On both horizons the first strictly positive response occurred after write 1, the page 1 title `Portfolio directory`. M1 reached +0.0006333887577056885 and M3 reached +0.0005374550819396973. Both probes still ranked Cedar first on both documents. At write 2, the page 1 schema text `Schema: Item / Ref / Amount`, δ changed to −0.007469784468412399 for M1 and −0.0004481971263885498 for M3. Both owners first entered the registry at write 3.

The sole edited literal was the parent declaration at write 8, pointer [1, 1, 7]. At this write M1 had δ = −0.022005513310432434 and M3 had δ = −0.017752446234226227. On both horizons M1 next became positive at the page 1 text block `Unit: Unit3`, pointer [1, 1, 8], write 9, reaching +0.01377890445291996. M3 took until the page 1 table row `Service 180 103`, pointer [1, 1, 11], write 12. Its preceding header row had δ = −0.00026670098304748535 and the service row had δ = +0.0004915148019790649. The sign stayed positive through the target write on all four trajectories. All 16 aligned opening spans had different pooled-feature bytes across twins. Their OCR literals differed only at write 8 and their full span metadata differed at writes 8–16. Downstream writes used identical source and feature bytes across twins. [Per-span source and feature catalog](https://github.com/jackgumpe/eledgercare/blob/7d65875a1ff2d7ad8a008ea83f5484507dbd5db3/docs/reviews/WP-0030/evidence/catalog.json)

| Probe / pages | Paired reads | Strict paired wins | δ after opening | Native pre-target δ | Post-target δ | Reductions in absolute δ | Drops from positive δ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| M1 / 12 | 38 | 0 | +0.019793041050434113 | +0.009357478469610214 | +0.009533971548080444 | 16 | 14 |
| M1 / 30 | 74 | 0 | +0.019793041050434113 | +0.006276067346334457 | +0.006367038935422897 | 36 | 34 |
| M3 / 12 | 38 | 0 | +0.004570405930280685 | +0.0004988275468349457 | +0.0005054101347923279 | 18 | 13 |
| M3 / 30 | 74 | 0 | +0.004570405930280685 | +0.0004988275468349457 | +0.0005054101347923279 | 34 | 29 |

The test required a strict Alder lead on the Alder document and a strict Cedar lead on the Cedar document. Zero of 224 observations qualified across the two arms and horizons, including the reads before registration, the native postings and the post-target reads. Each M3 owner declaration at write 8 produced the reverse ranking, with margins −0.0013106614351272583 and +0.01644178479909897. All other noninitial observations ranked the same owner first on both members. Every one of the 448 member reads fell below the frozen top-score cutoff. Each trajectory has three sign transitions, including leaving zero, and two opposite-sign crossings. Every preceding and current value for each transition and both attenuation definitions is retained. [Full transition lists](https://github.com/jackgumpe/eledgercare/blob/7d65875a1ff2d7ad8a008ea83f5484507dbd5db3/docs/reviews/WP-0030/evidence/findings.json)

The 12-page document had 35 writes before the native posting and the 30-page document had 71. At depth zero each native attempt returned `ABSTAIN / below_threshold_owner`. The retrospective read following write 36 or 72 records the changed state after the target span has entered memory. Both horizons reuse the same owner edit and opening. These results localize a difference in two development trajectories. Its cause and held-out accuracy remain undetermined.

## Objective, methods and verification

The review required full traversal of the admitted development windows with an independently frozen observer, historical byte parity, complete source-aligned per-step reproduction and separate decisions on direction and strict paired wins. I froze, ran and published the reviewer replay before inspecting this packet's author code, evidence or report. I independently admitted the two pinned development archives, authenticated 11 capture triples across 28 uses and catalogued 90 unique source rows. Each arm and member began with new zero matrices and a fresh controller and registry. The replay independently schedules control events, pops, native attempts, recurrent writes and reads using the original WP-0024 primitives. The corrected author observes the existing frozen `matrix.advance` through a write wrapper. Both use the full-window projection, the fixed eventual posting query and the original fitted owner anchors. [Independent replay](https://github.com/jackgumpe/eledgercare/blob/603cfbc85c259112fb76ea7c1b9c514557149653/docs/reviews/WP-0030/replay.py) · [Author source](https://github.com/jackgumpe/eledgercare/blob/447a9e7adc2dbd81933510068742ba1b82bbe84d/docs/research/WP-0030/trace/trace.py)

| Actual check | Outcome |
| --- | --- |
| Python `ast.parse` over reviewer sources, `git diff --cached --check` before each commit | Sources parsed. The initial whitespace check identified two trailing blank lines which were removed before freezing. |
| `& 'C:/Users/jackg/eLedgerCare-Speed/WP-0030/runtime/venv/Scripts/python.exe' -I -B docs/reviews/WP-0030/replay.py 603cfbc85c259112fb76ea7c1b9c514557149653` | Exit 0, 9.03 seconds wall. All 24 historical member checkpoints reproduced exact score pairs, margins, query digests, full matrix digests, owner columns, read digests, controller and field controls. The original native decisions, choices, flags and scores across all three fields matched for all eight postings. Every reconstructed projected query matched the original WP-0029 digest. |
| `& 'C:/Users/jackg/eLedgerCare-Speed/WP-0030/runtime/venv/Scripts/python.exe' -I -B docs/reviews/WP-0030/compare.py a6bf30a8682eedb4b39cbedd188966ba6de62599` | Exit 0. The reviewer data rendered in the author schema reproduced the exact bytes of all four paired arrays, source catalog, findings and parity file. Comparison covered every source pointer, event, depth, registry eligibility, score, fixed query, state digest, rank and transition. Both author run receipts also matched the seven recomputed hashes. |
| `git diff a8b9c69f6f2dd8430d178341ad3aa91307525e3f 447a9e7adc2dbd81933510068742ba1b82bbe84d -- docs/research/WP-0030/trace` | Confirmed the two-reference attribute rename in the author wrapper. Its initial tensor named `anchors` masked the native callable, and its recorded first run failed before completing a pair. The corrected source and its two successful run receipts were reviewed. |
| Inspection of author `inputs30.py`, `trace.py`, `findings.py`, `run.ps1`, README, final /001, both runtime receipts and seven deterministic outputs at the stated revisions | The implementation and publication maintain the intended phase order, alignment, literal anchors, tie handling, cutoffs and findings. The independent trace also reproduced both numeric margins at M3 write 8, the 16 opening feature differences, the 8–16 metadata differences and the absence of a threshold pass on all 448 member reads. |
| Normal `git push origin HEAD:refs/heads/review/wp-0030-span-trace` and `git ls-remote --heads origin refs/heads/review/wp-0030-span-trace` | Reviewer freeze, replay evidence and comparison deliverable published on the owned private branch. The report-only tip is verified separately after committing this report. |

The runtime receipt records the Git input digests and the venv launcher hash. Python on Windows records the base Python executable in `sys.orig_argv`. The replay checked `sys.executable` against the assigned venv before loading any probe tensors. External writes were confined to the assigned reviewer scratch outputs under `C:/Users/jackg/eLedgerCare-Speed/WP-0030/review`, the owned worktree and its normal private Git branch. Native OCR, accelerator execution, fitting, blind/Packet B access and production tests were outside the CPU diagnostic. [Runtime receipt](https://github.com/jackgumpe/eledgercare/blob/7d65875a1ff2d7ad8a008ea83f5484507dbd5db3/docs/reviews/WP-0030/evidence/runtime.json)

## Change inventory and handoff

The following nine files were added under `docs/reviews/WP-0030/` between the reservation and review deliverable. The separately reserved canonical report is the only subsequent report metadata. [Review diff](https://github.com/jackgumpe/eledgercare/compare/f19d7fdca840af7b81e6a0bb1edd062d690898de...6d62d773399c53c8efbbce0ee38067ea474a7d4d)

| Added paths | Contents |
| --- | --- |
| `inputs.py`, `replay.py` | Input authentication, independent recurrence and native checkpoint verification |
| `evidence/bindings.json`, `evidence/catalog.json` | Exact queries, fixed anchor digests, ordered capture and source/feature identities |
| `evidence/steps.jsonl`, `evidence/findings.json`, `evidence/runtime.json` | All 448 member observations, both findings, ordered transitions and CPU run receipt |
| `compare.py`, `evidence/comparison.json` | Independent schema transcription and whole-file comparison on pinned inputs |

The review accepts /001 and the exact source and results identified above. There is no outstanding discrepancy. The coordinator owns the packet's final disposition and publication verification.
