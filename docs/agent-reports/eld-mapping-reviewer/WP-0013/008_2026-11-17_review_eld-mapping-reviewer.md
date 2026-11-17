# WP-0013 /008: independent recovery and fixed-sentinel acceptance

- Report path: `docs/agent-reports/eld-mapping-reviewer/WP-0013/008_2026-11-17_review_eld-mapping-reviewer.md`.
- Reservation: `47fbc7612e4a08cf1960ad7ac01bd2843ae645e5:INDEX.md`; actual sentinel authority `d82237366a9877433ba81751ab6ae09b2f182734`, [kickoff](../../../kickoffs/WP-0013-eld-mapping-reviewer-sentinel-008.md).
- Category / author / publisher: review; eld-mapping-reviewer, continuing native `/root/mapping_reviewer`, independent of mapper/corpus authors; no subagents.
- Actual model / effort: not exposed; user-requested xhigh session retained.
- Environment: Windows PowerShell; Python 3.12.10; existing qualified external model environment for the one released sentinel run, then CPU-only comparison.
- Timestamp: 2026-11-17T20:13:31.508466+00:00.
- Repository / branch / worktree: `jackgumpe/eledgercare`, `review/wp-0013-vocabulary`, `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-vocabulary-reviewer`.
- Held execute and score HEAD: `b782c66990476e5cdefeaf6880aa7685debd222d`, clean throughout both commands.
- Accepted source: `ae790497f3fdd10573e8179757416bc2d1736250`; tree `8fd68c96bb18ca0177f227ad9a82505090d997b0`; runtime protocol SHA256 `ef648a3cd52df16ed6ed352e666ffedf789148100d640e2582cf13f76b6f9783`.
- Admitted corpus: `373106d94b56e619e2210308ca3bf237b45affc0`, tree `af22f632c2b69531f61866ca467c6f04f386df7e`, unchanged.
- Reviewed author publications: original /007 `0d610695c87f3998deee2b6b3d48f7c7d531eddb`; separate recovery /012 `0bd4ebc26228266fa6f365e7e9bbc6f8dd2845ec`.
- Reviewer runtime deliverable: `722dcab4e98f00c7c5bfec07548d15201e2283ce`; immutable packet/inventory publication `5c24219c79803fffd3c2ccf51b1a602d473d2dea`.
- Final comparison deliverable: `409fb1dd553ad5b149515e04cf4db51ac98ff48c`; inventory revision `f33b886402f4c7bc7b8d79ff43d814d17818d270`; inventory SHA256 `1d0d45f00ae2259993c1574b30b6b178293b9451e9b7dad95ff52f9932ce803b`.
- Report integration base: `bfc0ee479bf3e6dd3117aa6ad2ac9e92c1a56215`, after authorized normal merge of root `80a1c6d1872aa85f465d27a732c57279b0aa9e5b`; source/corpus trees verified unchanged.
- Previous review: [source /011](011_2026-11-17_review_eld-mapping-reviewer.md). Reviewed reports: [original /007](../../eld-mapping-author/WP-0013/007_2026-11-17_research_eld-mapping-author.md), [recovery /012](../../eld-mapping-author/WP-0013/012_2026-11-17_research_eld-mapping-author.md).
- Status: accepted, bounded results/accounting and empirical sentinel reproduction. Next owner: eld-coordinator for /009 disposition.

## Disposition and reproduced results

Accept the exact published recovery and independent sentinel evidence. The
single combined CPU comparison reproduces all twelve author full B0/v1/v2
prediction, score and policy packets, plus the reviewer's one selected packet.
No metadata issue or unexplained discrepancy remains. This does not replace
the original failed trial or establish broad quality, performance or promotion.

| Separate recovery012, twelve documents/four families | B0 | v1 | v2 |
| --- | ---: | ---: | ---: |
| Printed fields | 0/87 | 1/87 | 37/87 |
| Printed cells | 0/153 | 0/153 | 48/153 |
| Rows, declared known cells | 0/27 | 0/27 | 12/27 |
| Verified absences | 0/12 | 0/12 | 6/12 |
| Pages | 12/12 | 12/12 | 12/12 |

Normalized field/cell counts equal printed counts here. V2 equal-family mean
field/cell rates are 0.488095/0.5, distinct from pooled slot rates. Against v1,
v2 has 37 field gains, one loss and 49 neutral credit outcomes; 48 cell gains,
zero losses and 105 neutral outcomes. The known duplicate-equal F01 identifier
loses original-score credit because the accepted guard abstains. That loss is
retained alongside removal of its separate required-abstention violation.

All 255 policy slots remain eligible: 252 known, three ambiguous, zero unknown
or unavailable. V2 has 91 correct known assignments, zero incorrect/ambiguous
assignments, zero surplus output candidates and zero of 89 required-abstention
violations; 75 unexpected abstentions remain. V1 has four violations. All four
unsupported cases remain in the denominator with 85 required abstentions.
Abstention success is separate from value recovery.

Actual F02 supported/conflict native outputs contain `Service / Item`, while
the frozen catalog requires `Service / item`; inspected decisions retain
`missing_profile`. This remains a coverage limitation, with no retuning.

The independently executed `WP13-F04-conflict-v0` matches author raw bytes,
token IDs, raster identities, full predictions, original scores and policy
scores. Raw SHA256 is `6765de153bd318a03d5339966349f5ddc484ba03ef694ae1a9cf6f485c702d05`.
V2 scores 6/6 fields, 8/8 cells, 2/2 rows and 1/1 absence; policy has 15 known
assignments and one required ambiguous abstention. This is one empirical
reproduction, not GPU determinism or a replacement twelve-document estimate.

## Actual execution and independent checks

| Operation | Actual result and immutable evidence |
| --- | --- |
| Reviewer accepted CLI `execute` under d8223736, 19:49:34–19:58:35 UTC | One invocation; two excluded warmups plus fixed sentinel, all three complete. Tool03e24b/session76354/completion12dc16, supervisor/tool/child exits0; [actual receipts](../../../reviews/WP-0013/eld-mapping-reviewer/008/results/attempt-1/launch/tool-attestation.json). |
| Same clean-HEAD `score-run`, 19:58:54–19:58:57 UTC | One CPU invocation, tool ebecb2 exit0; [original score](../../../reviews/WP-0013/eld-mapping-reviewer/008/results/attempt-1/scores.json). |
| Owner return and independent root ACK | Owner19:59:27; root44560f5633c1b87556b01fe490dd831f951dbc11 at20:01:05 confirms five bound PIDs absent and post identities; [exact proof](../../../reviews/WP-0013/eld-mapping-reviewer/008/results/attempt-1/bindings/return/lease-return-ack.json). |
| Frozen `compare_published_recovery012.py --author-spec .../author.json --reviewer-spec .../reviewer.json --out .../comparison.json` | Single CPU comparison20:06:22–20:07:02; toolf0a4fe/session50153/completiondb6986 exit0. [Exact argv and helper HEAD](../../../reviews/WP-0013/eld-mapping-reviewer/008/combined-recovery012-001/execution/launch.json), [full result](../../../reviews/WP-0013/eld-mapping-reviewer/008/combined-recovery012-001/comparison.json). |
| Runtime and final comparison inventories | Tools4f9006 and8f5b99/session73537/completiond6a086 exit0. Exact original copies, all prior paths and consumed input identities verified; no additional scoring. |

Comparator freeze `76741706e58467fedfa6bc142551c1c1264388e0` predates recovery
outputs; actual comparison helper HEAD is `5c24219c79803fffd3c2ccf51b1a602d473d2dea`.
Author spec ddad3b4c29b4a4231f592c33fa539094e66c908a and reviewer spec
caa6b142d504540f7485e87e9f0008c78c9a0716 were exported as exact Git bytes.
The corrected author LF hash was bound before execution; no repeat comparison
was needed. Complete hashes, commands, outcomes, metrics and human proof review
are in the [reconciliation dossier](../../../reviews/WP-0013/eld-mapping-reviewer/008/combined-recovery012-001/README.md).

## Inventory, original failure and limits

The [runtime inventory](../../../reviews/WP-0013/eld-mapping-reviewer/008/results/publication-inventory.json)
covers 77 additions, 5,315 preserved paths, 52 original copies and 19 Git proof
copies. All 70 runtime files are accounted for: 41 published, 29 cache files
hashed and retained in the owned runtime. The [final comparison inventory](../../../reviews/WP-0013/eld-mapping-reviewer/008/combined-recovery012-001/inventory.json)
covers 15 additions (6,601,717 bytes), 5,394 preserved paths, 453 distinct
immutable input bindings and 93 source descriptors. Each phase adds its
inventory/receipt afterward; this canonical report follows separately. Earlier
[CPU preparation](../../../reviews/WP-0013/eld-mapping-reviewer/008/preparation-inventory.json),
[launch handoff](../../../reviews/WP-0013/eld-mapping-reviewer/008/launch-handoff/inventory.json)
and [original007 comparison](../../../reviews/WP-0013/eld-mapping-reviewer/008/actual-original007-001/inventory.json)
remain immutable and fully inventoried. Source corrections/failures are separately
accounted for by /011. Root integration introduces unchanged upstream publications,
not reviewer authorship.

Original007 remains zero model calls and twelve unavailable primaries, with
87 field/153 cell/27 row/12 absence denominators and 255 unavailable policy
slots. Its independent comparison publication
`7f8cf7db29156c6e5f22a2d1ac320debacdf2d50` is never pooled into recovery quality
or relabeled successful abstention. All original lookup, control and packaging
failures remain in their respective evidence. Current model, scoring,
comparison and collection succeeded without retry; the harmless read-only
missing-local-branch lookup is recorded in the runtime packet.

Actual author supervisor/tool exits and root process/model observations were
inspected and remain attributed to their owners. Author return19:47:55 precedes
reviewer lease19:48:33. Root confirms both leases returned. No additional model,
observer, service, source change or scoring experiment is released.

Recovery used already exposed material. Four families and one sentinel limit
generalization. Author primary mean46.630s versus sentinel50.180s is descriptive
only: one load, fixed order, dense fallback, different supervisor environments,
desktop/WDDM sharing and sampled host peaks prevent performance claims. Rows
mean declared-known-cell agreement; typed quantity scores do not establish
complete unit semantics; reference text metrics are bounded. Zero counted
policy violations does not establish absence of every possible invention.

Publication receipt: deliverables and inventories precede this report. Normal
owned push, report-only diff, relative-link and exact-origin/clean checks follow;
the full publication SHA is sent to root without rewriting this report.
