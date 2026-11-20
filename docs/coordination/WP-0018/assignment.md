# WP-0018 · Windows OCR archive diagnostic

Jack authorized the local coordinator to determine where error first appears between original WinRT text, individual words, the adapter’s spans and grid, and the frozen scorer. This packet covers only the synthetic WP-0015 H and A captures. It ends with a recommendation. Packet B stays sealed. New recognition, rasterization, GPU execution, training, production changes and repairs are outside this release.

## Custody and inputs

The repository is the private `jackgumpe/eledgercare`. Integration base is `e255c2a52ce39d5fe8bf041eb5187eab6e6eb24b` on `coordination/bootstrap`. The release commit containing this assignment is the starting pin for all three new worktrees. Report ownership and dates are [reserved in INDEX.md](../../../INDEX.md#wp-0018-windows-ocr-archive-diagnostic). The original input is Jack’s `Windows-OCR-Archive-Diagnostic-Kit (1).zip`, SHA-256 `2504bbb624bc17a437d84ec2bf6ea03ebf95a9dacdbaa691aa86e293a89fab28`. The brief, original Gemini PDF, archive pins and constructed control match the original kit byte for byte. The kit’s brief and evidence files are retained as supplied.

| Packet | Only admitted Windows run | Inventory revision and Git blob |
|---|---|---|
| H | `h-r1-ab/04-h-windows` | `bd48af1a7f968b2231fe1d870a22c88f265ae347` · `8e72acfc3f307da7e0f074edd937e61ce22f64ce` |
| A | `a-recovery-ab/04-a-windows` | `ce4206f20d63101f6344121eaaeeeb86d2ec85a0` · `156e53d20f448d2410e218b961ae6a1630e9a978` |

Use the committed `score.py` at `7598bf4155452c4a1294b7421595009d39ea1bc9`, SHA-256 `1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7`, and the score/lookups at `ce4206f20d63101f6344121eaaeeeb86d2ec85a0`. The adapter and WinRT bridge are pinned at `a0e738bc03e515999659dda09c5ee76d08fb37df`. All original archive reads use the exact named H/A files under `%USERPROFILE%/eLedgerCare-Speed/WP-0015/review`. Never enumerate other packet input roots.

Owned working copies sit under the existing sibling `eledgercare-worktrees/wp0018-data/{pair,words,review,coordinator}/inputs`. Each has `H/` and `A/` containing `source.pdf`, `truth.json`, `rasters.json`, `rasters.input.json`, `plan.json`, `historical-score.json`, and `windows/{prediction,timing,raw-NNN,page-NNN,window-NNN}.json`. The `control/` directory contains the exact scorer, prior published H/A summary, supplied archive pins and constructed control. Original archive files are read-only sources. Runtime outputs go to each role's own sibling scratch directory. Check names, commitments, raw and page identities, preserved input hashes and published lookup values. Record an unavailable input or failed baseline at the affected scope.

## Assignments

| Sequence | Owner and execution | Permitted repository writes | Deliverable and next reviewer |
|---|---|---|---|
| 001 | eld-rd-astra, fresh native Codex requested xhigh | `docs/research/WP-0018/pair/` and own reserved report | Frozen separate-process score, method control, paired location records and invariants. Review by eld-rd-reviewer. |
| 002 | eld-archive-tracer, fresh native Codex requested xhigh | `docs/research/WP-0018/words/` and own reserved report | Four witness traces first, then documented attribution for reference locations. Review by eld-rd-reviewer. |
| 003 | eld-rd-reviewer, fresh uninvolved local subscription Opus session, requested xhigh | `docs/reviews/WP-0018/` and own reserved report | Native CPU reproduction on independent copies, direct inspection of frozen source, outputs and provenance. Disposition to eld-coordinator. A fresh non-author Codex xhigh may take over if the subscription is unavailable, with a recorded handoff. |
| 004 | eld-coordinator, receiving local Codex session bound in CURRENT.md | `docs/coordination/WP-0018/`, canonical coordinator report, INDEX.md, CURRENT.md and integration commits | Archive admission, releases, preserve originals, verify remote publications and dispose under the observed scope. |

Inspect the actual source before execution and freeze executable changes in Git before decisive runs. Push only owned branches normally. Commit freeze, evidence and canonical report separately where the report names an evidence revision. Disclose the execution model/effort as actually observed. Preserve other owners’ work.

## Order and decision rules

1. Verify and copy the named historical inputs. Reproduce both unmodified baselines with the frozen scorer in a separate process. Compare counts, faults, and published lookups. H requires 15 of 20 correct cells and 8 of 19 unflagged critical errors. A requires 235 of 300 and 94 of 252. Stop the affected pair if its baseline fails.
2. Capture H p2 table 1 r2 c1, A p60 table 1 r2 c2, H p1 line 2 and H p2 line 2 before examining paired packet totals. Record raw WinRT line text/ordinal and ordered word boxes in pixels, projected boxes rounded as the adapter does, span order, original emitted grid and scored selection. Include expected and observed values, links or exact JSON pointers, and what the trace cannot distinguish.
3. On private copies change exactly `pages[*].tables` to `[]`. Require identical source, page order, text, spans, word boxes and flags. Verify identical prose verdicts including critical lines, identical per-page text-edit counts and stable packet completeness. Stop and reconcile any violation. Reproduce the supplied constructed control, which exercises gains and losses even at zero net change.
4. Account separately for every reference cell in H and A, with expected and before/after values, archive hash and JSON location, both flags, match/fallback mode, gain, loss, unchanged wrong, unchanged right, unavailable and extra cells. Separate already-fallback rows. Ground any attribution in original evidence. The reference boxes used in the second arm are an oracle available to the diagnostic. Preserve later contributors and plausible alternatives.
5. The non-author independently reruns the controls and decisive comparisons, verifies the four raw witnesses, and examines the authors’ implementation and artifacts at pinned revisions. The coordinator publishes the narrowest supported conclusion, including evidence limits and disagreements. A passing diagnostic does not authorize a product or model change.
