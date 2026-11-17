# WP-0011 /006: independent controlled-diagnosis and sentinel acceptance

- Report path: `docs/agent-reports/eld-mapping-reviewer/WP-0011/006_2026-11-17_review_eld-mapping-reviewer.md`.
- Sequence reservation: `08313e4bc3457dab2c0cee0ff238b3c61c668ddb:INDEX.md`, WP-0011 /006; [execution kickoff](../../../kickoffs/WP-0011-eld-mapping-reviewer-execution.md), runtime release `6ad846322afeb3781c50cc70d3144bc1d456f24b`, final comparison authority `cacbe2c34dd7a9a978af763ecb3b77279cccb404`.
- Category: review.
- Author / stable agent ID: eld-mapping-reviewer, existing independent native session `/root/mapping_reviewer`; no subagents.
- Actual model / effort: backend and actual effort not exposed; existing user-requested xhigh Codex session. No impersonated model identity.
- Execution environment: Windows/PowerShell, qualified Q0 Python3.12 environment; one explicitly leased unchanged model execution, followed by CPU-only comparison and publication.
- Published by: reviewer.
- Timestamp: 2026-11-17T11:19:18Z.
- Repository / branch: `https://github.com/jackgumpe/eledgercare.git`, `review/wp-0011-coverage`.
- Owned worktree: `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-coverage-reviewer`.
- Base / exact executing revision: `08313e4bc3457dab2c0cee0ff238b3c61c668ddb`; remained clean and unchanged through execute and score-run.
- Final deliverable revision: `6518651ce94aa9f770b43371e923d625f8150c99`.
- Final inventory metadata revision: `393a2efc525d5e851ad95c1190964785e88481d8`; inventory SHA256 `2ce5f6ee18ce4f74e05862964565cafc2761407dfcf185539df10d767cb77435`.
- Intermediate immutable packet: `d61593d3998e37e93178d650102a13df5a485f92`, deliverable `c9e900f874cae78a94a49f6c18f6345f41e57cd9`; root independently audited before normalized reviewer binding.
- Accepted source: `253519e07e7d45cf1f5ecb3e03053582f7f7d4cc`; coverage tree `6bdab544c9fe26cbf093cc765212db2a2e7a97a5`; protocol SHA256 `03b13a41a0047c827af32e71209933700457a5dfd6d38ec106daed82ef5b9000`.
- Reviewed author /005 publication: `97821f17926f9a6c409fe4c3b409b66f1cd9b824`; deliverable `367bcd93cfa4913c4b7b6fb98931bdd34c3296d8`, inventory `94a05113ced0473bc89afb5c7396c4bb6963ed14`.
- Previous reviewer report: [WP-0011 /002](002_2026-11-17_review_eld-mapping-reviewer.md), accepted source at `bfac3057ce0142dcd37372dee26398d682238202`. Related [admission /004](004_2026-11-17_review_eld-mapping-reviewer.md) at `021dc265790c90ae83f1afa24fc3f2a71eae41e1`; unchanged admission evidence `9033a5f9b6988abf8e5784c2e700b2b046bae37a`.
- Corpus: admitted publication `970675115b948defc32125d20e6a31ab788d88f9`, tree `7c119e1cbb329e5777608834c3c9a33880e667ed`; explicit unseal `e47def37be1ceaf04722125a8aee7ddb49e4159e`.
- Status: accepted, within the finite experiment and limitations below.
- Next owner: eld-coordinator for publication audit, integration and WP-0011 /007 synthesis. All task model leases are returned.

## Summary

Independently reproduced all twelve author full B0/v1 predictions, scores and diagnostic records, all nine within-family paired comparisons, actual statuses and complete denominators. The unchanged frozen comparison helper reports no runtime metadata issues. A separately released reviewer cold load, two excluded historical warmups and one fixed `WP11-F03-degraded-v0` call completed without retry; clean-HEAD CPU scoring passed. The sentinel exactly matches the author raw bytes, token IDs, rendered input identities, full predictions, full scores and full diagnostics. Timing differs and remains descriptive.

The bounded diagnosis is accepted. Existing v1 has27 field gains and zero losses over B0 on identical raw outputs,42/92 versus69/92 fields. Both have129/172 cells and21/28 rows. All three vocabulary variants retain all66 expected values but score0/23 fields and0/43 cells; the known-label association failures and unsupported vocabulary evidence are distinguishable without forcing every failure into a single causal category. The result does not establish general OCR accuracy, character accuracy, exclusive GPU hardware or deterministic inference. Reviewer authored no evaluated mapper, scorer, corpus or runtime source.

## Objective and acceptance criteria

Inspect exact author evidence rather than relying on its summary; independently reproduce full original metric objects and separate stage diagnostics; verify immutable source/corpus/release/identity bindings, finite status progression, all failed/not-run denominators if present, observer availability and complete copied/retained inventories. Execute only the preselected one-primary reviewer schedule under a separately observed sole-model-job lease, retain actual tool/worker/cleanup evidence, score at the released clean HEAD and honestly compare raw/token/raster/full-result identity. Freeze helpers before decisive checks and preserve all failures. These conditions are satisfied; no further model calls are needed or authorized.

## Independent findings and interpretation

All twelve actual raw records were inspected alongside the reproduced complete slot records and admitted paired references. The [dossier](../../../reviews/WP-0011/eld-mapping-reviewer/results/RESULTS.md) gives concrete raw locations, counts, unit/identifier checks and limitations. There are three independent families, twelve conditions and nine paired comparisons; all pairs are retained, with zero unavailable pairs. Presence264/264 has zero unavailable slots but52 repeated-value/multiple-occurrence ambiguities, including16 fields and36 cells.

| Three-family condition | B0 fields | v1 fields | Cells, both | Rows, both | Exact visible payload presence |
| --- | ---: | ---: | ---: | ---: | ---: |
| Control |6/23|23/23|43/43|7/7|66/66|
| Layout |23/23|23/23|43/43|7/7|66/66|
| Vocabulary |0/23|0/23|0/43|0/7|66/66|
| Degraded |13/23|23/23|43/43|7/7|66/66|

All27 gains occur in F01-control (seven) and F02-control/degraded (ten each): actual native field tables place labels beside values, while B0 selects below-row content and v1 selects the correct adjacent value. For example F01-control p1/b2/r0 contains `Work Order ID` beside `WO-0008645`, but B0 predicts `Property`. Ideal-native control witnesses support both mappers; they remain reference-only counterfactuals, not model observations. F01-degraded switches native representation to separate text blocks and B0 recovers, without a value-presence gain. This does not imply that worse images improve general OCR.

Vocabulary controls preserve values while exact labels/headers fall outside frozen schema support. Raw examples include `Repair record`/`Stock reference`, `Billing reference`/`Item ref` and `Inspection record`/`Check ref`. Supported field/header counts are69/92 and129/172, no unknown states. Supported unique/local field-payload conditional accuracy is38/57 B0 and57/57 v1, with35 fields outside that conditional but retained in92 total. Supported row-local cells are129/129 with43 vocabulary cells outside the conditional but retained in172 total. Overlapping flags and unadjudicated relationships remain visible; a missing mapping is not by itself a recognition failure.

Typed credit equals printed credit here. Nine mapped quantity units EA/HR/KT agree literally; three unmapped vocabulary units are unavailable despite visible raw quantities. Historical numeric normalization is unchanged and does not substitute for unit identity. Identifier printed exactness is57/84 B0 and63/84 v1, with literal zero-bearing strings preserved. Nine of twelve blank absences are verified; three vocabulary absences remain unmapped/unverified. Zero nonempty violations or unmatched candidates does not prove no inventions. One-page sentinel/adjacency/link metrics have no author-primary denominator. SequenceMatcher token alignment is not character accuracy or minimum-edit WER.

## Actual runtime and empirical sentinel

Reviewer runtime authority `6ad846322afeb3781c50cc70d3144bc1d456f24b` bound lease `WP-0011-reviewer-sentinel-20261117T105850Z` to the exact clean executing revision and accepted source. Actual run: `C:/Users/jackg/eLedgerCare-Coverage/WP-0011/reviewer/runs/reviewer/20261117T105934Z-63dbbc52`. Start2026-11-17T10:59:31.883512+00:00, supervisor completion11:08:36.086720+00:00; tool session22202, launch chunk0749c5, completion chunkfd9abd, exit0. Wrapper32048, supervisor6556, launcher36532, worker24624. All three scheduled calls completed, worker0 and observed exit, no failure/secondary/finalization errors; all20 observer rows returned0. The two warmups were excluded and no other primary was selected.

CPU scoring used the same held clean HEAD, release and run. Score wrapper37844/child6184, start11:08:48.081906, finish11:08:51.327315+00:00; actual tool chunk608a5e, exit0. Reviewer primary denominator is1, with14 eligible slots, fields6/6, cells8/8, rows2/2 and absence1/1 for both mappers. It is not a fabricated twelve-document repeat.

The sentinel has439 tokens. Both raw SHA256 identities are `80b17a24cf280d57d7a1ee4e94c3e16c3fb0bf43eb048f69c729a793e548d1e7`; both token-sequence identities are `ddc2fd25d5aa5aa17a4a598a7d59c656713b2b14c3dc03077120eaa9b1110a84`. All six comparison flags for raw/token/raster/full-prediction/full-score/full-diagnostic equality are true. Author/reviewer synchronized wall times51.2625956/54.4922784 seconds and sampled memory observations remain in the full evidence; no latency improvement or GPU determinism follows. Reviewer supervised elapsed541.281 seconds includes excluded warmups142.5401431/314.8814073 seconds. Final runtime accounting68,243,015 bytes and43,525,193,728 bytes free satisfy the4GiB cap and20GiB floor.

Root independently observed all six reviewer execution/scoring PIDs absent at11:09:42.3947056Z, verified model18/notices/host, and returned the lease at11:10:09.675380+00:00 under `36e6c639a1993583c756620b88b8f3cc1c875579`. Author root return is `d412da43d0aa0c717a7649fc38de12a439a5824f`. Actual author tool65789/chunk4ee67f is attributed to the author; neither root nor this reviewer falsely claims direct polling of that tool. Reviewer directly observed its own original tool exits. Root independent cleanup/postidentity receipts are distinct from worker and supervisor exits. Sole model-job leases retain desktop sharing and WDDM unavailable process memory; no other owner's process was terminated and no further inference occurred.

## Change inventory

The [final inventory](../../../reviews/WP-0011/eld-mapping-reviewer/results/final-inventory.json) enumerates all94 base-to-deliverable additions with Git blob, size and SHA256 for both working and committed bytes. All3112 pre-existing mode/type/blob entries are unchanged, including accepted source, corpus, historical evidence, frozen helpers and shared routing. No existing path is modified, deleted or renamed.

| Added set | Exact root | Count and purpose |
| --- | --- | --- |
| Preserved reviewer evidence | `docs/evidence/WP-0011/eld-mapping-reviewer/006/attempt-1/` |65:41 run files,12 original launch/scoring/tool files,9 root proof copies, byte attributes, collection result and normalized run manifest. |
| Author-only comparison | `docs/reviews/WP-0011/eld-mapping-reviewer/comparison-preparation/actual-author-001/` |7:full independently reproduced audit, frozen-wrapper launch/start/completion, both actual streams and byte attributes. |
| Combined comparison | sibling `actual-combined-001/` |7:both complete populations, sentinel comparison and actual execution receipts/streams/attributes. |
| Interpretation/publication evidence | `docs/reviews/WP-0011/eld-mapping-reviewer/results/` |15 added paths:exact bindings/copy manifest, collection/comparison tool receipts, intermediate inventory, frozen package helper, two dossiers and five whitespace-check artifacts. Every filename is in final inventory. |

Final inventory itself is subsequent metadata at `393a2efc525d5e851ad95c1190964785e88481d8`; this canonical report is committed separately afterward. No shared ledger edits. External effects are limited to the released reviewer runtime root and owned ignored execution/comparison/check scratch. All72 original runtime files remain:41 copied and31 cache-only files individually inventoried and rehashed. All53 original copies and9 root proof copies remain byte-identical to originals and Git; caches are retained, not deleted. Model/dependency/notice roots remain read-only. No packages, services, downloads or product changes were introduced.

## Verification

| Actual check / command | Revision and outcome | Evidence |
| --- | --- | --- |
| Frozen `results/execute_wrapper.py execute --authority 6ad846322afeb3781c50cc70d3144bc1d456f24b --attempt .scratch/wp0011-reviewer-execution/006-attempt-1`, via qualified Python `-I -B` | Wrapper frozen071c9f1bd3f670eea1f954571365985923ed76ff, SHA256aca42eeaae34c9b6443c8cec1a8bbe4becec85389a8d0b5f473166597a627808; exact clean08313e4; supervisor0/worker0,3 completed. | `attempt-1/launch/`, `run/`, direct tool attestation. |
| Same wrapper `score --authority 6ad846322afeb3781c50cc70d3144bc1d456f24b --attempt .scratch/wp0011-reviewer-execution/006-attempt-1 --run` exact path above | Same clean executing HEAD, exit0, one primary retained. | `launch/score-*.json`, actual streams, complete `launch/scores.json`. |
| `comparison-preparation/compare_published.py --author-spec` exact bound author spec `--out .../actual-author-001/audit.json` | Unchanged frozen d2088bf19e79cd91732e9d848c917dd3d3721f3e; actual tool96839/chunk249d95 exit0; twelve full packets/nine pairs exact, no metadata issues. | Full audit and compare launch/start/completion/streams. |
| Same helper with `--author-spec` and `--reviewer-spec` from exact cacbe2c authority, `--out .../actual-combined-001/audit.json` | Actual tool69736/chunka31f50 exit0; both populations reproduce, all sentinel equality flags true. | Full combined audit; source inventory67 entries, complete original/input/publication/proof inventories. |
| Frozen `collect_evidence_v2.py --authority 6ad846322afeb3781c50cc70d3144bc1d456f24b --after 36e6c639a1993583c756620b88b8f3cc1c875579 --run` exact path above `--attempt .scratch/wp0011-reviewer-execution/006-attempt-1 --destination docs/evidence/WP-0011/eld-mapping-reviewer/006/attempt-1` | Frozen b1299ba5ff20b0e77f816859dc1785402eb24cb4, SHA2561fd6d886edd1a143fa2c83bf7d05088454beeb4860004a660e4c92cff72ecb21; actual chunk9253cd exit0. | Collection result, all53 original/9 root copies, complete72-file runtime inventory, no missing wrapper artifacts. |
| `results/package_results.py --output .../results/collected-inventory.json`, then final `--output .../results/final-inventory.json` | Helper frozen c9e900f874cae78a94a49f6c18f6345f41e57cd9; actual exits0;75 then94 artifacts,3112 protected paths, all original/Git bytes and31 caches reverified. | Complete separate inventories; final tool chunk449c19. |
| Human exact-object review | All12 raw records, full slot/paired results, literal units/identifiers/absences, actual supervisor receipts, lease times, postmodel18/notices and owned process proofs inspected. | Dossier concrete anchors and exact proof bindings; full audits preserve underlying objects. |
| Git whitespace and publication checks | Default CRLF checks failed as described below; `git -c core.whitespace=cr-at-eol diff --cached --check` passed before final deliverable. | `results/publication-checks/`, preserved raw captures, byte inventories. |

No full source suite, corpus regeneration, PDF rendering or additional inference was repeated for evidence-only publication. Prior source /002 and corpus /004 acceptances remain separately attributed. The standalone comparison and wrapper preparation tests remain immutable; no accepted source changed after those reviews.

## Risks, failures and unfinished work

Execute, score, collection and both actual comparisons succeeded on first attempts. Prior preparation import failures and versioned corrections are preserved in the base. A stale functions wait-cell lookup failed after context compaction; the original live session22202 resumed, without rerunning execute or scoring. Default cached whitespace check returned1 because preserved CRLF logs were treated as trailing whitespace; the committed-diff reproduction returned2 and retained its full79,416 stdout bytes. The explicit `cr-at-eol` check passed; raw evidence was not normalized. These tooling/formatting outcomes are distinct from runtime/source failures.

Three families, twelve fixed-order conditions, one composite degradation recipe and one independent sentinel limit generalization. Presence and schema-relative invention accounting are incomplete semantic assurances. Warm caches, output lengths, shared desktop/F4 activity, WDDM gaps and sampled memory peaks limit performance attribution. The approved torchvision local-SHA TOFU and qualified dense fallback remain unchanged limitations. No new unresolved source/result blocker was found. A future vocabulary-coverage treatment would require separate scope, exact freeze, independent review and new reserved evaluation families; this acceptance releases none of those actions or production integration.

## Review map and handoff

[Exact base-to-deliverable diff](https://github.com/jackgumpe/eledgercare/compare/08313e4bc3457dab2c0cee0ff238b3c61c668ddb...6518651ce94aa9f770b43371e923d625f8150c99), [reviewed author report](https://github.com/jackgumpe/eledgercare/blob/97821f17926f9a6c409fe4c3b409b66f1cd9b824/docs/agent-reports/eld-mapping-author/WP-0011/005_2026-11-17_research_eld-mapping-author.md), [full combined audit](../../../reviews/WP-0011/eld-mapping-reviewer/comparison-preparation/actual-combined-001/audit.json), [independent dossier](../../../reviews/WP-0011/eld-mapping-reviewer/results/RESULTS.md), [complete inventory](../../../reviews/WP-0011/eld-mapping-reviewer/results/final-inventory.json), [runtime collection](../../../evidence/WP-0011/eld-mapping-reviewer/006/attempt-1/collection.json), [sentinel score packet](../../../evidence/WP-0011/eld-mapping-reviewer/006/attempt-1/launch/scores.json).

Root should audit/integrate exact deliverable6518651ce94aa9f770b43371e923d625f8150c99 and inventory393a2efc525d5e851ad95c1190964785e88481d8, then synthesize /007. Reviewer's branch is `review/wp-0011-coverage`; all runtime leases are returned and no further inference is pending. Normal owned push, report-only diff, exact-origin and clean-state verification follow this report commit. Full publication SHA and verification receipt are sent to root without rewriting the canonical report.
