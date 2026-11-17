# WP-0013: guarded vocabulary experiment accepted within its bounds

The research experiment is complete. The frozen v2 mapper improves structured coverage on this four-family synthetic matrix while honoring its conflict/unsupported-label abstention policy. It still misses an entire supported family because of an exact header-case mismatch. This accepts the experiment and its evidence; it does not promote the research mapper into the product or establish general extraction accuracy.

The separately accepted [WP-0012 product rehearsal](../../../agent-reports/eld-coordinator/WP-0012/005_2026-11-17_verification_eld-coordinator.md), publication68230cf7ddfb4d85e41e9d6718c822090a706631, remains closed. Four actual product attempts across two operators exercised upload, OCR, correction, search, source/history reopening and disabled-OCR restart on two synthetic fixtures. The product source remains c1fed68020ae67e8b4763bc6ea5473adaa86de2b; capture limitations remain in that disposition.

## Results and interpretation

These are complete extraction-and-mapping results on twelve cases from four families, not the percentage of characters read correctly. Every mapper receives the same saved native output; the original scoring and normalization are unchanged.

| Pooled original metric | B0 | Previous v1 | Guarded v2 |
| --- | ---: | ---: | ---: |
| Printed fields | 0/87 | 1/87 | 37/87 |
| Printed table cells | 0/153 | 0/153 | 48/153 |
| Rows, declared known cells | 0/27 | 0/27 | 12/27 |
| Verified absences | 0/12 | 0/12 | 6/12 |
| Page count | 12/12 | 12/12 | 12/12 |

V2's equal-family field/cell means are48.81%/50.00%, distinct from pooled slot counts. Against v1 there are37 field gains, one loss and49 neutral uncredited fields;48 cell gains, zero losses and105 neutral uncredited cells. The lost exact field is F01-conflict work_order_id: a duplicate equal label/value is deliberately withheld. Its printed-field loss remains counted, while its separate required-abstention violation is removed. Three other ambiguous assignments are also withheld; they were not known-value credits.

All255 policy slots are eligible:252 known and3 ambiguous, with0 unknown/unavailable. V2 makes91 correct known assignments and0 incorrect, ambiguous or unknown assignments; it violates0/89 required abstentions. It also makes75 unexpected abstentions. V1 violates4 required abstentions. These are schema-relative results, not a claim that all prose is factual or that abstention recovers values. Unsupported cases stay in every denominator:85 required-abstention slots receive no assignments.

Supported/conflict v2 field counts are20/30 and17/27; cells24/51 in each. Unsupported cases score0/30 fields and0/51 cells, as their value recovery remains absent. F02 supported/conflict account for the remaining coverage gap: retained native headers say `Service / Item`, while the frozen exact case-sensitive catalog has `Service / item`. The unresolved description column prevents a complete profile match, so its table and alias fields are refused. No catalog change or new model run was made to improve this result. Any later treatment must be separately versioned and evaluated.

## Original failure, separate recovery and independent check

| Population | Actual outcome | Immutable record |
| --- | --- | --- |
| Original007 |0 model calls; all12 primary outcomes unavailable after pre-model missing-Git failure. No output-quality estimate or successful-abstention claim.|Author0d610695c87f3998deee2b6b3d48f7c7d531eddb; independent original accounting7f8cf7db29156c6e5f22a2d1ac320debacdf2d50.|
| Separate recovery012 |2 excluded warmups+12 primaries complete once; execute/score0. Four families, already exposed content; not newly blind.|[Author012](../../../agent-reports/eld-mapping-author/WP-0013/012_2026-11-17_research_eld-mapping-author.md), publication0bd4ebc26228266fa6f365e7e9bbc6f8dd2845ec.|
| Independent008 |2 excluded warmups+one preselected WP13-F04-conflict-v0 repeat complete once; execute/score0. All12 author and1 reviewer full prediction/score/policy packets reproduced; raw/token/raster/full result identities match for the repeated case.|[Independent008](../../../agent-reports/eld-mapping-reviewer/WP-0013/008_2026-11-17_review_eld-mapping-reviewer.md), publicationb882001f13177d6cd56cdde7dcb590a16836c211.|

Original007 is never replaced by recovery or pooled into its quality estimates. The finite protocol/catalog were independently accepted before mapper implementation; fresh family bytes were reserved/admitted before source acceptance and unseal. The later runtime-only corrections occurred after exposure without changing mapper, scorer, corpus or model settings. Frozen comparison helper76741706e58467fedfa6bc142551c1c1264388e0 precedes recovery outputs; original comparison helper and original full-object failure reproduction remain unchanged.

## Exact source, execution and preservation

Accepted research sourceae790497f3fdd10573e8179757416bc2d1736250/tree8fd68c96bb18ca0177f227ad9a82505090d997b0; runtime protocolef648a3cd52df16ed6ed352e666ffedf789148100d640e2582cf13f76b6f9783. Corpus373106d94b56e619e2210308ca3bf237b45affc0/treeaf22f632c2b69531f61866ca467c6f04f386df7e matches the reserved admitted bytes. Public protocol, aliases/guards, all old comparators/scorers/normalizers, Q0 and Baidu model revision0480966938291445591f69f08a13b041c073a96a remain frozen.

Initial010's Git PATH correction had a reproducible shadow-selection defect, F011-01. Author01310a635d2b9292944a54221e72f4c82566bcb464b and independent011b782c66990476e5cdefeaf6880aa7685debd222d corrected and verified the actual Windows selection boundary:26 author children/61 tests;20 independent children,3 affected tests and4 comparison-binding controls. Only runtime.py, new runtime_git.py, the runtime test fixture and source-review route differ from the original accepted research implementation. The guard is a repeated lookup snapshot, not an atomic filesystem lock. The initial failure, rejected010, reviewer193-versus216 expectation failure and byte-preserving packaging incidents remain recorded.

Author execution used clean fbc2ab64e9ae1b4ff6655e427d78e69930d40b72 under73fbbd7856b61d227b4462c9120ca6d117316a04,19:29:02–19:46:23Z; same-HEAD score0 ended19:47:01Z. Root return6090281419d54292cf8917b38ae50316eb26f3f9 verifies five owned model/wrapper/score PIDs absent and model/notices unchanged. Reviewer execution used clean b782c66990476e5cdefeaf6880aa7685debd222d underd82237366a9877433ba81751ab6ae09b2f182734,19:49:34–19:58:35Z; score0 ended19:58:57Z. Root return44560f5633c1b87556b01fe490dd831f951dbc11 verifies its five owned PIDs absent and model/notices unchanged. No lease remains active.

Root authenticated author152 artifacts/5,173 preserved paths/140 original copies/50 scheduled inputs/310 source identities/all131 run files (103 published,28 cache-only), and reviewer77 runtime artifacts/5,315 preserved paths/52 originals/19 Git proof copies/all70 run files (41 published,29 cache-only). Full audits and exact normalized inputs are adjacent coordinator files. Final independent publication audit and the [complete combined preservation inventory](../../WP-0012-0013/final-preservation.json) provide all final paths/modes/blobs/sizes/hashes and accepted publication ancestry. Later canonical report/receipt/routing are separate metadata.

## Limits and closure

Primary synchronized author calls totaled559.555s, mean46.630s, range36.106–68.794s; warmups are excluded. Peak sampled memory, native dense fallback, one cold load, fixed order, desktop sharing and WDDM gaps remain in the original records. These observations support no causal performance claim. Existing quantity normalization validates supported units but compares numeric magnitude; row credit covers declared known cells. Synthetic families and one repeat do not establish broad generalization. Library offline settings do not verify OS outbound denial.

All authorized implementation, actual execution, independent verification and publication are complete. Retained runtime/cache evidence and product databases remain intact, with owned model processes/services stopped. No new experiment, model tuning, customer data, deployment or production mapping integration is released.
