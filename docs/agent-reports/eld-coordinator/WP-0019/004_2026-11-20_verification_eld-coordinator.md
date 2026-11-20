# WP-0019 / 004 · Same-pixel Windows OCR crop trial

**Disposition. Close WP-0019 at Stage 2. The frozen crop policy did not qualify for a larger research trial.** One missing hyphen recovered on exposed Packet A and zero critical regressions across H/A earned the fresh check. On the two fresh families, each arm read 42 of 60 critical identifiers exactly. All 18 originally wrong criticals remained wrong and all 42 originally correct criticals stayed correct. The fresh treatment delivered 149.09 pages/minute and cost an additional 67.77 ms/page. [Stage 1 gate](../../../coordination/WP-0019/stage1-gate.json) · [Stage 2 gate](../../../coordination/WP-0019/stage2-gate.json)

| Report metadata | Record |
| --- | --- |
| Canonical path | `docs/agent-reports/eld-coordinator/WP-0019/004_2026-11-20_verification_eld-coordinator.md` |
| Category and author/publisher | Verification and coordinator disposition · eld-coordinator |
| Session | Continuous local Codex coordinator `01a1d895-c605-7ab2-b7ec-c3159c0634ba`, Windows CLI. Actual backend and applied reasoning effort were unexposed. |
| Published UTC | 2026-11-20T20:20:06Z |
| Repository, branch and base | Private `jackgumpe/eledgercare` · `coordination/bootstrap` · `6706d7671a382ead98b058673ba1822c18477b24` |
| Packet-wide reservation | `fc15d1bd3af1b4c7dfbfbf1eac2680b9ae9ac1af` · [assignment](../../../coordination/WP-0019/assignment.md) |
| Exact runtime candidate | `9418bccd339dea1d89445f2fec93927168c7a5f0` for all crossovers |
| Decision and verification deliverable | `266f64c701a210e9a37fc27ed37d2b0b905bae75` · [decision record](../../../coordination/WP-0019/decision.json) |
| Previous coordinator report | [WP-0018 / 004 archive diagnosis](../../eld-coordinator/WP-0018/004_2026-11-20_verification_eld-coordinator.md) |
| Related publications | [Astra / 001](../../eld-rd-astra/WP-0019/001_2026-11-20_research_eld-rd-astra.md) · [Carbon / 002](../../eld-rd-carbon/WP-0019/002_2026-11-20_research_eld-rd-carbon.md) · [independent Opus / 003](../../eld-rd-reviewer/WP-0019/003_2026-11-20_review_eld-rd-reviewer.md) |
| Status and next owner | Accepted as a completed bounded experiment. Larger-trial criterion failed. Coordinator disposition is final for this packet. |

## Same-installation control and protocol

The first real H/A run used the original WP-0015 full-page reader in one persistent, warmed en-US WinRT process on Windows 26H2, build 26300.9974. The OCR DLL and English resource matched the historical hashes. WinRT exposed its 10,000-pixel limit and language, but no recognizer model version or per-word confidence. All 64 historical raw readings and exported page predictions matched, including word boxes. H reproduced 15/20 correct table cells and 8/19 unflagged critical errors. A reproduced 235/300 cells and 94/252 unflagged critical errors. Original-reader startup and excluded warmup took 389 and 208 ms. [System record](../../../coordination/WP-0019/current-environment.json) · [Post-update control](../../../coordination/WP-0019/control.json)

Astra froze the application-visible selector and merge at `d62a96f8145345ce4c43544850d20fce13659879`. Carbon froze the worker at `793fbb7a2a5a3a9354bb753c39b29fcdda959160`. Each treatment made its own full-page read, used four-pixel grid insets and 12-pixel horizontal/eight-pixel vertical prose padding, deduplicated regions and capped attempts at 32 per page. The worker read BGRA8 pixels from the retained full bitmap and checked every crop against the exact source rectangle. Coordinates were mapped back to the page. The structural replacement rule could emit a literal crop word. Other disagreements retained the full reading and could raise a review flag. Each family ran full-only then full-plus-crops and in the reverse order, using one warmed process per order. We counted each field once. [Design and selection](../../../research/WP-0019/astra/policy.py) · [Worker](../../../research/WP-0019/carbon/engine.py) · [Registered decision rule](../../../coordination/WP-0019/gate.py)

## Accuracy and time

Disagreements compare the full and crop readings on all attempted regions. “Both wrong” includes a change to a different wrong reading. Time includes the independent full passes, input verification, region selection, cropping, recognition, merging and durable writes. Added time is the difference in end-to-end duration, averaged across both orders. All expected critical fields were selected, including those whose readings stayed wrong.

| Family | Full → final exact critical IDs | Recovered | Regressed | Both wrong | Both right | Full/crop disagreements | Added ms/page | Treatment pages/min |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H, 4 exposed pages | 11 → 11 / 19 | 0 | 0 | 8 | 11 | 1 / 20 | 35.60 | 165.36 |
| A, 60 exposed pages | 158 → 159 / 252 | 1 | 0 | 93 | 158 | 27 / 460 | 44.52 | 167.78 |
| LIFT, 6 fresh pages | 21 → 21 / 30 | 0 | 0 | 9 | 21 | 6 / 48 | 58.69 | 151.08 |
| VALVE, 6 fresh pages | 21 → 21 / 30 | 0 | 0 | 9 | 21 | 1 / 66 | 76.85 | 147.15 |

The complete 60-page Packet A averaged 18.785 s full-only and 21.456 s with crops. The fresh rate pools the 24 treatment-page timings across both orders and two six-page forms. It applies to this host, warm reader and ready bitmaps. Individual arm times, startup, warmup, crops/page and before/after flags are recorded per order. [Stage 1 timings and selections](../../../coordination/WP-0019/stage1-verified.json) · [Independent fresh timings and selections](../../../coordination/WP-0019/stage2-verified.json) · [Fresh critical, timing and control breakdown](../../../coordination/WP-0019/fresh-field-analysis.json)

### Exposed witnesses and absent words

- **Only recovery.** A p50, table 1, row 2, column 2 changed from `80808479` to the exact printed `80808-479` in both orders.
- H p2, table 1, row 2, column 1 changed from `IL801493` to `IL801-493`. The restored hyphen left it wrong against `1L8O1-493`. A p60, table 1, row 2, column 2 repeated `01801-139` against `0I8O1-139`.
- H p1, line 2 retained the extra space in `88L1 L-631`. The H p2 line 2 positive control retained the correct `880LO-977`.
- All five historically nonempty A cells with zero intersecting full-page words were selected. A p5 r5c1, A p15 r4c2 and A p30 r3c2 returned zero crop words. A p20 r5c1 and A p30 r5c1 returned `20—4` and `30—4` with em dashes. The policy flagged and retained the original empty observations. None of the five reached an exact final reading. All 23 original H/A blank cells remained explicitly empty. [Nine field traces with raw words and boxes](../../../research/WP-0019/astra/evidence/nine-fields.json)

A generated 17 disagreements on critical IDs. Six were right throughout, ten stayed wrong and one recovered. H's sole critical disagreement stayed wrong. A's unflagged wrong count fell from 94 to 84 because nine remaining errors gained flags and one was corrected. H retained eight unflagged errors. [All exposed scored locations](../../../coordination/WP-0019/stage1-scoring/receipt.json)

### Fresh forms and disagreement as a review signal

Both fresh families contributed nine intentionally confusable, nine ordinary and twelve legitimately spaced IDs. All 18 confusables were wrong on both arms. All 18 ordinary and all 24 legitimately spaced IDs stayed correct. Each of the 18 printed blank cells stayed explicitly empty. The 18 numeric negative controls stayed correct. Of 24 text negatives, 18 stayed correct and six pre-existing LIFT text discrepancies persisted. The diagnostic post-score check found zero exact crop readings hidden by the merge at a still-wrong critical field. [Fresh strata and all locations](../../../coordination/WP-0019/fresh-field-analysis.json) · [Frozen-scorer outputs for both arms](../../../coordination/WP-0019/stage2-scoring/receipt.json)

The seven fresh disagreements all became flags. Five identified real errors and two flagged already-correct IDs, including one legitimately spaced value. The reads agreed on the other 13 wrong IDs. This is evidence that same-pixel cropping can flag some errors on these forms and that agreement alone cannot certify an identifier. One exposed hyphen recovery supplies the observed benefit. It did not repeat on these two fresh layouts.

## Custody, independent checks and limitations

The coordinator created the two synthetic form families after the exposed gate passed. The generator digest was fixed at `19b98baa253de3139e1f65807b26723294480359`. Rasters and answer-key hashes were committed separately at `9610737251545cbf2577c4c5035cf36365f9bc29` and `962bfefd5eb6f84a0be34970b8547a7668897bd9`. A non-author Opus 5.5 session executed the blind plan on the same frozen SHA. It published all four orders at `3f48b04fd33bef91f734af1a0db206c02320d180`. I verified all 60 returned files and committed the blind archive at `810cf72aa2af3c4bc5fff4711e892ca44e2cecca` before opening the keys at `0d34800ded1c5284257a7f3a2c2f72411c64188b`. Custody used separate session roles and user-scoped Windows DPAPI under a shared local account. A post-release deterministic rebuild reproduced both TIFFs, every ready bitmap and all key commitments. [Blind return](../../../coordination/WP-0019/blind-escrow-return.json) · [Preservation and rebuild](../../../coordination/WP-0019/preservation.json)

The reviewer independently reproduced all eight H/A prediction files byte for byte and ran the fresh crossovers and scoring. A preregistered search of every author source file found three exposed H/A witness strings in a synthetic worker test. The reviewer retained the formal `INCONCLUSIVE_CONTROL` result. The runtime hashes that test file for provenance but never executes or imports it. The reviewer independently reconstructed the runtime selections and decisions and judged the finding immaterial to the user's Stage 1 quality gate. The reviewer had seen the exposed one-recovery branch headline after writing its checks. Fresh predictions were committed before the keys were opened. The reviewer also retained the absence of a separately instrumented file-access audit on fresh runs. Additional checks reconstructed crop projections and timing when the original trace schema lacked those fields. All eight fresh frozen-scorer files were byte-identical between the reviewer and coordinator, and the reviewer reconciled all 684 fresh field records from the two orders. [Independent Stage 1 record](../../../coordination/WP-0019/stage1-independent.json) · [Independent final review](../../eld-rd-reviewer/WP-0019/003_2026-11-20_review_eld-rd-reviewer.md)

Two reporting details reconcile against the original evidence. The reviewer’s Stage 1 join omits the flag on A p54 line 5, a noncritical prose field. Its prose gives 179.32 full-only fresh pages/min, the arithmetic mean of the four rates. Pooling pages and elapsed time as registered gives 179.28 full-only and 149.09 with crops. Independent and coordinator records agree on all critical values, flags, treatment throughput and added time. [Location and timing reconciliation](../../../coordination/WP-0019/scoring-reconciliation.json)

The non-author published the scores and independent evidence at `a78798e6c1a5ce8d43a9fd08d2561651fa7d9b52`. Its provider reached the usage limit after writing /003. I verified the completed author-write payload, the independent worktree file and the Git publication were byte-identical, and published the report as coordinator at `a215cd0272eb409720145524e60c50ea40b2ece9`. The accompanying record supplies the actual publisher for the author’s originally planned push. [Author and publication receipt](../../../coordination/WP-0019/reviewer-publication.json)

## Reproduction, inventory and handoff

| Operation performed | Command or durable evidence |
| --- | --- |
| Verify H/A before and after, regenerate historical RGB and run the current reader | `docs/coordination/WP-0018/admit.py --verify-only`, `reference.py prepare` and `reference.py control`. The before/after archive receipt SHA-256 was `64809c0044a081d2335b461070b48a7dd7536c11b0364ccddb629041a0c8e3bf`. [Admitted inputs](../../../coordination/WP-0019/admission.json) |
| Run four H/A and four blind fresh crossovers | `execute.py --plan … --expected-sha256 … --code … --out … --lock …`. Each plan pins manifests and the candidate. [Stage 1 plan](../../../coordination/WP-0019/stage1-release.json) · [Fresh plan](../../../coordination/WP-0019/stage2-blind-release.json) |
| Geometrically verify real readings and retain original evidence bytes | `verify_run.py --run-root … --families … --out …` with `--reference` for H/A. [Exposed outputs](../../../coordination/WP-0019/stage1-runs/receipt.json) · [Blind outputs](../../../coordination/WP-0019/stage2-runs/receipt.json) |
| Open committed labels, score all arms separately, join every critical position | `forms.py release`, `score_pair.py --truth … --control … --treated … --out …`, `account.py --truth … --paired … --out …` and `fresh_strata.py`. Both scoring paths bind original WP-0015 `score.py` at SHA-256 `1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7`. |
| Integrate and record the disposition | The packet-local coordination, research, review, report files and the two routing ledgers contain the work. The final publication receipt records the private-origin copy of each report. [Inventory from the pre-packet base through the decision](https://github.com/jackgumpe/eledgercare/compare/6706d7671a382ead98b058673ba1822c18477b24...266f64c701a210e9a37fc27ed37d2b0b905bae75) · [Actual agent sessions](../../../coordination/WP-0019/participants.json) |

The trial used synthetic material on this Windows host. It measured native-resolution crops and a single frozen policy. The scope ends with this disposition, with the production application and sealed Packet B preserved. [Decision and handoff](../../../coordination/WP-0019/decision.json)
