# WP-0011 /005: completed finite controlled coverage diagnosis

- Report path: `docs/agent-reports/eld-mapping-author/WP-0011/005_2026-11-17_research_eld-mapping-author.md`
- Sequence reservation: `65f24d33be9eb4571a8372a28e3bf2114173d928:INDEX.md`, WP-0011 /005; [execution kickoff](../../../kickoffs/WP-0011-eld-mapping-author-execution.md).
- Category: research.
- Author / agent ID: eld-mapping-author, stable native session `/root/mapping_author`; no subagents.
- Actual model / effort: author backend/effort not exposed; same user-requested xhigh Codex session. The qualified OCR model is independently pinned in the accepted protocol/release and actual preflight, rather than inferred from the author role.
- Execution environment: Windows, PowerShell7.7.0, host and qualified Q0 Python3.12.10; one released GPU/model job followed by CPU scoring/collection.
- Published by: author.
- Timestamp: 2026-11-17T10:25:24.400528+00:00.
- Repository / branch: `https://github.com/jackgumpe/eledgercare.git`, `research/wp-0011-coverage`.
- Worktree: `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-coverage-author`.
- Base / exact executing revision: `65f24d33be9eb4571a8372a28e3bf2114173d928`; remained clean and unchanged through execute and score-run.
- Accepted source: `253519e07e7d45cf1f5ecb3e03053582f7f7d4cc`; coverage tree `6bdab544c9fe26cbf093cc765212db2a2e7a97a5`.
- Protocol SHA256: `03b13a41a0047c827af32e71209933700457a5dfd6d38ec106daed82ef5b9000`.
- Exact runtime authority: `56b36b52e682a7396b02c34cf40c85a4f31f9329:docs/coordination/WP-0011/releases/author.json`.
- Collection helper revision: `001d126fa2d7e3c06d043d8c2407f8447ba2d4c3`.
- Deliverable revision: `367bcd93cfa4913c4b7b6fb98931bdd34c3296d8`.
- Inventory metadata revision: `94a05113ced0473bc89afb5c7396c4bb6963ed14`.
- Previous author report: [WP-0011 /009](009_2026-11-17_research_eld-mapping-author.md), source correction; packet sequence /005 was reserved earlier for execution.
- Related acceptance/publication: source /002 `bfac3057ce0142dcd37372dee26398d682238202`; corpus admission /004 `021dc265790c90ae83f1afa24fc3f2a71eae41e1`; root unseal `e47def37be1ceaf04722125a8aee7ddb49e4159e`; corpus deliverable `970675115b948defc32125d20e6a31ab788d88f9`, tree `7c119e1cbb329e5777608834c3c9a33880e667ed`; custodian /008 `e5a1a995a22c6fb89722b75ea5152966cb21ab98`; root observed return `d412da43d0aa0c717a7649fc38de12a439a5824f`.
- Status: ready-for-review; actual execution complete and lease returned, results awaiting independent /006.
- Next owner: eld-mapping-reviewer /006 under separate root result/sentinel release.

## Summary

Completed the exact fourteen-call schedule once: two excluded historical warmups, then all twelve frozen primaries across three matched families. Every call stopped normally, with no flags, retries, substitutions or source changes. Supervisor and worker exits were0, all42 observer command rows returned0, finalization had no errors, and root independently confirmed lease return and the absence of all four owned PIDs. CPU score-run completed at the same clean executing HEAD.

The unchanged mapping-v1 recovered27 printed/typed field slots over B0 with zero losses on the same raw outputs: fields69/92 versus42/92. Both mappers scored129/172 cells and21/28 rows. All three vocabulary variants failed structured extraction (0/23 fields,0/43 cells) despite all66 expected slot values being present; supported-condition v1 results were complete. This is evidence of a vocabulary/schema coverage barrier and native association sensitivity, not an OCR character-accuracy estimate or a new treatment result.

All264 field/cell slots had eligible exact visible-payload matches, but52 retained repeated-value/multiple-occurrence ambiguity. All nine matched pairs remained eligible; none was dropped. The [results dossier](../../../research/WP-0011/eld-mapping-author/005/README.md) supplies every document result, raw/expected anchors, conditional denominators, timing/memory provenance and limits. Prior failures/reports/source remain immutable. No author inference remains authorized or pending.

## Objective and acceptance criteria

Execute only the separately released finite schedule with accepted source, admitted unchanged corpus, explicit unseal, qualified read-only Q0 dependencies/model and fresh observed sole-model-job ownership. Preserve first-failure/no-retry behavior and all twelve primary denominators; score the same raw under frozen B0/v1 and separate diagnostics at the exact bound HEAD; retain complete raw/token/render/observer/resource/process evidence, return the lease, then freeze collection helper and publish exact copies/inventories/results. Author-side execution, scoring, cleanup, collection and publication are complete. Independent result reproduction and the reviewer's separately leased preselected sentinel remain distinct acceptance work.

## Actual execution and cleanup

Lease `WP-0011-author-diagnostic-20261117T095303Z` was bound to the source/HEAD above, exact GPU UUID `GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d`,14-call plan,6h ceiling,4GiB storage cap and20GiB free floor. Root resolved competing ownership before launch: the F4 Python verifier was a separately owned CPU task, Ollama had no loaded model/runner, and ordinary desktop GPU clients were retained. The lease promised sole model-job ownership, not exclusive hardware.

Executed `python -I -B qualification/coverage_v1/cli.py execute --authority 56b36b52e682a7396b02c34cf40c85a4f31f9329 --release-path docs/coordination/WP-0011/releases/author.json --owner author` through a hidden Start-Process wrapper with separate stdout/stderr capture. Actual wrapper PID8072/supervisor15344, launcher14864/model heartbeat25204; tool session65789, launch chunkbcf944. Start2026-11-17T09:54:24.1581107Z; supervisor completed10:13:55.6978562Z, exit0 (final chunk4ee67f). External run is `C:/Users/jackg/eLedgerCare-Coverage/WP-0011/author/runs/author/20261117T095427Z-75adb724`.

The supervisor retained14 completed rows, no failure, worker exit0 and observed exit, no secondary/finalization errors, successful final observations and complete operational logs. Author exact-PID observation found supervisor/launcher/worker absent at10:15:06.0219834Z. Root independently verified model18/notices/host after execution and all four PIDs absent, then recorded `RETURNED_OBSERVED` in `d412da43d0aa0c717a7649fc38de12a439a5824f:docs/coordination/WP-0011/author-after/lease-return.json`. No other owner's process was terminated. No later author inference occurred.

CPU score-run used the same authority/release-path/owner, external run path above, and output `.scratch/wp0011-coverage-execution/005-attempt-1/scores.json`; started10:15:06.1712842Z, finished10:15:10.7501001Z, exit0, exact clean HEAD unchanged. Actual command and timestamps are retained in `attempt-1/launch/score-execution.json`. Source/helper commits began only afterward.

## Results and interpretation

| Three-family condition | B0 fields | v1 fields | Cells, both | Rows, both | Exact payload presence / eligible |
| --- | ---: | ---: | ---: | ---: | ---: |
| Control |6/23|23/23|43/43|7/7|66/66|
| Layout |23/23|23/23|43/43|7/7|66/66|
| Vocabulary |0/23|0/23|0/43|0/7|66/66|
| Degraded |13/23|23/23|43/43|7/7|66/66|

Typed credits equal printed credits in this set. Original equal-family field means are0.50 B0 and0.75 v1; both cell/row/absence means are0.75. Those original family means are distinguished from pooled42/92 versus69/92 field counts. Both mappers verify9/12 absences, with three vocabulary absences unmapped/unverified; nonempty violations0 and unmatched field candidates0 do not establish no inventions. Page count is12/12; one-page sentinels/adjacency/cross-page-link metrics have no primary denominator, not assumed perfect scores.

All nine condition-minus-own-control comparisons are retained with zero unavailable pairs. Presence-count deltas are0 for every pair. Cell/row deltas are-1 on each vocabulary pair and0 on the others. B0 field deltas: F01 layout+1/vocabulary0/degraded+1; F02 layout+1/vocabulary0/degraded0; F03 layout0/vocabulary-1/degraded0. V1 field deltas are-1 for vocabulary and0 otherwise. The fixed composite degradation caused no expected-value presence loss here; F01 B0 improves through a changed native arrangement, which does not imply degraded scans are generally easier.

Actual F01 control serializes known fields as same-row label/value table cells. Raw p1/b2/r0/c1 contains `WO-0008645` beside `Work Order ID`; B0's below-row association chooses `Property`, while v1 chooses the adjacent correct value. F02 control/degraded similarly contain `IV-0005638` beside `Invoice No`; B0 chooses `Invoice Date`, v1 chooses the correct value. These three documents account for all27 gains and no losses. Their ideal-native control witnesses support both mappers, but the actual model's native representation differs: known-label/ideal support does not guarantee actual association success. Exact raw locations and score pointers are in the dossier and full packet.

Vocabulary cases preserve values but change exact declared labels/headers outside both frozen vocabularies. F02 raw has `Billing reference IV-0005638` and headers `Seq Item ref Service / item Units Rate Rebate% Rebate Levy Extended`; canonical schema support is absent even where row-local payload is exact. All66 vocabulary slots carry unsupported visible label/header evidence; repeated values and unadjudicated field relationships remain explicit overlapping evidence. No forced causal partition is claimed.

Stage counts keep their own denominators:92/92 field and172/172 cell presence, zero unavailable;69/92 field and129/172 cell schema support, zero unknown. Among57 supported unique field-payload cases B0 credits38, v1 57;35 field slots are excluded from that conditional, not dropped from the full92. Supported row-local cell evidence gives129/129 under both,43 vocabulary cells excluded. Typed-given-printed exact is42/42 B0 fields,69/69 v1 fields and129/129 cells. Nine mapped units agree literally; three unmapped vocabulary units are unavailable. Leading-zero identifier exactness remains57/84 B0 and63/84 v1, without normalization repair. These diagnostics do not claim all text or semantic facts are correct. The unchanged text score uses SequenceMatcher token alignment, not character accuracy or minimum-edit WER.

Primary synchronized wall times range34.793â€“81.984s with313â€“747 output tokens; all twelve individual timings are in the dossier and full raw observations. Warmups1122 tokens/164.899s and2558 tokens/324.071s are excluded. Runtime elapsed1168.297s includes the one cold load, warmups and primaries. Load sampled private peak14,656,323,584 bytes, sampled working-set peak6,824,980,480 bytes, and host lifetime working-set peak7,222,951,936 bytes are distinct measurements. Primary sampled peaks reach10,887,880,704 private bytes and2,389,639,168 working-set bytes; sampling gives lower bounds on true window peaks. Primary CUDA max allocated is about7.293GB and max reserved7,480,541,184 bytes; full precise bytes/provenance remain per call. Device-free memory includes desktop/WDDM sharing. Fixed order, variable output length, warm caches, parallel F4 CPU/browser activity and one draw per condition limit performance attribution.

Recommend a subsequent separately versioned exact label/header alias-coverage treatment with ambiguity/absence guards, independent review and newly reserved families. This candidate follows the observed vocabulary barrier; no aliases are added or recovery promised here. Existing v1 already handles the observed known-label association failures. Three families and one fixed composite degradation severity do not establish broad generalization. These inputs are now exposed regression material.

## Change inventory

The [complete deliverable inventory](../../../research/WP-0011/eld-mapping-author/005/deliverable-inventory.json) enumerates all146 added paths with Git blob, committed/worktree byte sizes and SHA256. All3064 base mode/type/blob entries remain identical, including accepted source, corpus, prior failures/reports and shared routing. No existing path is modified, renamed or deleted. Exact run files are separately enumerated by relative path in [run-copy-manifest.json](../../../evidence/WP-0011/eld-mapping-author/005/attempt-1/run-copy-manifest.json).

| Added set | Exact root / identity | Count and purpose |
| --- | --- | --- |
| Evidence attributes | `docs/evidence/WP-0011/eld-mapping-author/005/.gitattributes` |1, preserve original runtime bytes in Git. |
| Complete runtime copy | `docs/evidence/WP-0011/eld-mapping-author/005/attempt-1/run/` |107 files, individually enumerated in run-copy manifest and deliverable inventory: plan/result/heartbeat/stdout/stderr,42 observer captures, preflight/load/events/worker outcome and every call's raw/token/render/observation records. |
| Actual launch/scoring/cleanup receipts | `docs/evidence/WP-0011/eld-mapping-author/005/attempt-1/launch/` |9 files; original launch/completion, initial and complete PID cleanup, score execution and both streams for supervisor/scoring. |
| Immutable authority/return proofs | `docs/evidence/WP-0011/eld-mapping-author/005/attempt-1/bindings/` |19 files; exact source/admission/unseal/runtime lease/preflight/ownership/root-return objects, individually inventoried with source commit/path. |
| Full scores | `docs/evidence/WP-0011/eld-mapping-author/005/attempt-1/scores.json` |1; all12 predictions/full original scores/separate stage evidence and nine pairs. |
| Derived collection/accounting manifests | `docs/evidence/WP-0011/eld-mapping-author/005/attempt-1/{analysis.json,collection.json,run-copy-manifest.json}` |3; raw/input/metric/condition/gain-loss/latency/memory accounting and complete copy/retention provenance. |
| Frozen collection helper | `docs/research/WP-0011/eld-mapping-author/005/collect_evidence.py` |1; CPU byte collection/binding and Git-object preservation verification only. |
| Dossier/byte attributes | `docs/research/WP-0011/eld-mapping-author/005/{README.md,.gitattributes}` |2; actual result interpretation/anchors and original capture-byte preservation. |
| Collection execution receipt | `docs/research/WP-0011/eld-mapping-author/005/collection-execution/{execution.json,stdout.txt,stderr.txt}` |3; exact command/helper/times/exit0 and actual collection streams. |

The collection covers all134 external run files:107 copied and27 retained-only task-local cache files with path/size/SHA256. Original external run/caches remain in place. It verifies48 fresh artifact identities against the admitted corpus commit plus two warmup PDFs, totaling50 inference inputs. Collection copies136 source files in total (runtime107, launch/scoring10, proofs19); analysis/manifests and dossier metadata are generated separately. Weights, credentials and unrelated files are not published. Root proof copies are explicitly Git-object representations; `bindings/12-copy-representations.json` distinguishes root LF copies from original working CRLF. Original author receipts in `launch/` remain byte-exact. No silent newline equivalence is asserted.

Post-deliverable metadata is committed separately: `docs/research/WP-0011/eld-mapping-author/005/deliverable-inventory.json` at `94a05113ced0473bc89afb5c7396c4bb6963ed14`, followed by this report. No source/helper modification occurred after the collection helper freeze. External changes are limited to the released author runtime root and ignored owned execution/collection capture scratch; the model/dependency/notice roots remain read-only, independently post-verified. No package install/download or service change occurred.

## Verification

| Check / exact operation | Revision / actual result | Evidence |
| --- | --- | --- |
| Released `cli.py execute` command above, one cold load and exact14 calls | Clean executing `65f24d33be9eb4571a8372a28e3bf2114173d928`; supervisor/worker0,14 completed, no failure/finalization error,42 observer rows0. | `run/plan.json`, `run/run-result.json`, all per-call artifacts, `launch/launch.json`, `launch/completion.json`. |
| `python -I -B qualification/coverage_v1/cli.py score-run --authority 56b36b52e682a7396b02c34cf40c85a4f31f9329 --release-path docs/coordination/WP-0011/releases/author.json --owner author --run C:/Users/jackg/eLedgerCare-Coverage/WP-0011/author/runs/author/20261117T095427Z-75adb724 --output .scratch/wp0011-coverage-execution/005-attempt-1/scores.json` | Same clean executing HEAD; exit0, all12 primary rows/nine pairs retained. | `launch/score-execution.json`, complete `scores.json`. |
| Exact author PID observation and root independent post identity/ownership audit | Author matching_count0 for15344/14864/25204; root also8072 absent; model18/notices/host pass; `RETURNED_OBSERVED`. | Original `launch/cleanup-complete.json`, exact root `d412da43d0aa0c717a7649fc38de12a439a5824f` proof copies. |
| `python -I -B docs/research/WP-0011/eld-mapping-author/005/collect_evidence.py collect --return-authority d412da43d0aa0c717a7649fc38de12a439a5824f --out docs/evidence/WP-0011/eld-mapping-author/005/attempt-1` | Frozen helper `001d126fa2d7e3c06d043d8c2407f8447ba2d4c3`; exit0; raw/token/render hashes,14 calls,12 rows,50 inputs,136 copies and complete134-file run manifest pass. | `collection-execution/`, `collection.json`, `run-copy-manifest.json`. |
| Same helper `verify --deliverable 367bcd93cfa4913c4b7b6fb98931bdd34c3296d8 --out docs/research/WP-0011/eld-mapping-author/005/deliverable-inventory.json` | Clean deliverable; exit0,146 additions and3064 protected base paths; copied bytes, retained cache hashes, inputs, manifest and Git evidence bytes reverified. | Inventory `94a05113ced0473bc89afb5c7396c4bb6963ed14`. |
| `git diff --cached --check` before commits | Passed. | Exact commits. |

No execution, score-run, collection or inventory attempt failed in /005. The initial two-PID cleanup observation was preserved before adding the complete three-PID author check; root independently included the wrapper as well. Prior source-test/probe failures remain immutable and are not erased. Deprecation and unavailable-Triton warnings remain in runtime stderr; accepted dense fallback was verified by the worker. No full CPU suite or model call was repeated after the decisive run because packaging introduced no accepted-source change. Independent /006 sentinel/reproduction has not been performed by this author.

## Review map, limits and handoff

[Exact base-to-deliverable diff](https://github.com/jackgumpe/eledgercare/compare/65f24d33be9eb4571a8372a28e3bf2114173d928...367bcd93cfa4913c4b7b6fb98931bdd34c3296d8), [results dossier](../../../research/WP-0011/eld-mapping-author/005/README.md), [complete scores](../../../evidence/WP-0011/eld-mapping-author/005/attempt-1/scores.json), [analysis](../../../evidence/WP-0011/eld-mapping-author/005/attempt-1/analysis.json), [run-copy manifest](../../../evidence/WP-0011/eld-mapping-author/005/attempt-1/run-copy-manifest.json), [inventory](../../../research/WP-0011/eld-mapping-author/005/deliverable-inventory.json).

Independent /006 should inspect actual raw/expected/layout/semantic anchors, reproduce all12 paired outcomes with the frozen source and preserve the complete denominator/absence/ambiguity frame. The independent sentinel remains exactly `WP11-F03-degraded-v0` plus two historical warmups, under a separate fresh root lease. Neither the author result nor its recommendation releases another model call, source change, quality treatment or production integration. Three families, fixed order and one degradation severity limit generalization; presence and schema-relative invention checks are incomplete semantic assurances. All environment/dependency limits, including approved torchvision local-SHA TOFU, remain explicitly bound by the original protocol/release.

Handoff identities: source `253519e07e7d45cf1f5ecb3e03053582f7f7d4cc`, tree `6bdab544c9fe26cbf093cc765212db2a2e7a97a5`, executing HEAD `65f24d33be9eb4571a8372a28e3bf2114173d928`, helper `001d126fa2d7e3c06d043d8c2407f8447ba2d4c3`, deliverable `367bcd93cfa4913c4b7b6fb98931bdd34c3296d8`, inventory `94a05113ced0473bc89afb5c7396c4bb6963ed14`, runtime authority `56b36b52e682a7396b02c34cf40c85a4f31f9329`, root lease return `d412da43d0aa0c717a7649fc38de12a439a5824f`. Packet prefix and relative run paths above are stable for reviewer binding.

Publication receipt: this canonical report is committed after deliverable/inventory. Normal owned push, exact-origin/clean status and ancestry verification follow; full publication SHA and receipt are sent to root without rewriting this report. Root alone updates routing and releases independent execution.
