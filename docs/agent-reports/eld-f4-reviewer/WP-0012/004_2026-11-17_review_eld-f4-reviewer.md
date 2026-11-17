# WP-0012 / 004: Independent actual workflow rehearsal

- Report path: `docs/agent-reports/eld-f4-reviewer/WP-0012/004_2026-11-17_review_eld-f4-reviewer.md`
- Sequence reservation: `INDEX.md`, original live004 kickoff and renewed live004-r3 kickoff at authority `2d19a46b0d5e31995c5a00720faa285a61ab4fa8`.
- Category: review
- Author / agent ID: `eld-f4-reviewer`
- Actual model / effort: native Codex `/root/product_reviewer_continuation`; requested xhigh; actual backend and applied effort unexposed.
- Execution environment: native Codex, Windows PowerShell, Python 3.12 launcher, existing PostgreSQL/.NET/Node dependencies, Microsoft Edge `157.0.4341.60`.
- Published by: `eld-f4-reviewer`, native continuation
- Timestamp: 2026-11-17T18:31:28Z
- Repository / branch: `https://github.com/jackgumpe/eledgercare.git` / `review/wp-0012-product-rehearsal`
- Base revision / clean actual executing HEAD: `bf2172c9ecaab63de038300960082f3b521f8074`
- Reviewed product revision: `c1fed68020ae67e8b4763bc6ea5473adaa86de2b`; author003 publication `bd21e07eb322ea64dee59ba5562ee6b03087d079`.
- Deliverable revisions: frozen collector `e463bb3ed624baacda05c2f58232ef0b8b68bdae`; actual evidence and frozen semantic audit `be646cbd9fac9ed1ac316be11c9ac7800e33f691`; audit results and final inventory `2bf824375d79b9a3ef8919ffc782a8e1e2220bbb`.
- Previous reports: [independent preparation007](007_2026-11-17_review_eld-f4-reviewer.md), [ownership correction008](008_2026-11-17_implementation_eld-f4-reviewer.md), [integration correction010](010_2026-11-17_implementation_eld-f4-reviewer.md).
- Related reports: [actual author003](https://github.com/jackgumpe/eledgercare/blob/bd21e07eb322ea64dee59ba5562ee6b03087d079/docs/agent-reports/eld-f4-implementer/WP-0012/003_2026-11-17_verification_eld-f4-implementer.md), [independent ownership009](https://github.com/jackgumpe/eledgercare/blob/b2cca5227b27f326e437cc99f2a9b40ba08c6c94/docs/agent-reports/eld-f4-implementer/WP-0012/009_2026-11-17_review_eld-f4-implementer.md), [independent integration011](https://github.com/jackgumpe/eledgercare/blob/ed9651edfb4206cb13d564924a342b91679277c2/docs/agent-reports/eld-f4-implementer/WP-0012/011_2026-11-17_review_eld-f4-implementer.md).
- Status: accepted
- Next owner: `eld-coordinator` for exact evidence/publication audit and final005 disposition.

## Summary

The bounded independent workflow passed with two fresh real OCR attempts, one one-page work order and one three-page statement. Original uploads, raw model output and provenance persisted; reviewed values, explicit unknowns and a newer unapproved draft remained distinct. Saved machine/reviewed searches and historical revision reopening passed after actual API/PostgreSQL restart with both API payloads reporting `workerEnabled=false`. No extra extraction was issued after restart. Both attempts, live helper, launcher and tool exited 0. Resources returned cleanly and root acknowledged the actual receipt before read-only accounting.

Acceptance covers this actual workflow and its stored/DOM evidence. Screenshot06 still shows loading archive results; screenshots08/09 do not show painted native PDF pages. Those captures do not establish rendered archive cards or a painted target PDF page. The detailed limits below are part of this acceptance.

This is independent review of unchanged product source and actual author003, followed by a fresh reviewer execution. I authored reviewer-only harness corrections008/010, independently accepted by the separate author in009/011 and by root before this lease. I did not author the reviewed product or author003 helper. Carbon's original preparation/review work and the native continuation remain separately attributed; the original Carbon partial checkpoint `8729db9323e4d2945a30d525b0d67e5ad2a1692e` and published002 are unchanged.

## Objective and exact execution binding

Reproduce the accepted complete workflow on the two authorized synthetic inputs, using exactly two attempts, no warmups and no retries. Establish durable source/raw/provenance, human review and unknown decisions, source-linked archive retrieval, draft/history separation and restart persistence. Preserve failures and original exits, account for every copied or retained artifact, and return only owned resources.

[The immutable release](../../../reviews/WP-0012/eld-f4-reviewer/live-004/rehearsal-004/evidence/bindings/00-reviewer-004-r3.json) binds authority `2d19a46b0d5e31995c5a00720faa285a61ab4fa8`, sole lease `WP-0012-reviewer-004-r3-20261117T181101Z`, issued `2026-11-17T18:11:01.705559Z`, and held clean HEAD `bf2172c9ecaab63de038300960082f3b521f8074`. Authority and accepted011 were read as Git objects without merging. Runtime v7 source is `5e75cacd11f18bf6135376e3e1e10887c1447e1f`; v7 SHA256 `9a445e00a812c79928c81922c1c43716bf4f04fe48cc8e7fae8f3f1106648c61`; ownership module SHA256 `ff01e70c09c1e7b69cbed3c660f9f6cb777d381a920a51af7e1204d24eee6d9f`.

Owned resources were `eledgercare_demo_wp0012_reviewer`, PostgreSQL 55439 / API 5690 / UI 4710, and `C:/Users/jackg/eLedgerCare-Demo/WP-0012/reviewer`. New runtime outputs used `rehearsal-evidence/WP-0012-reviewer-004-native-03`; native01/native02 remained intact. GPU UUID was `GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d`. Observations accounted for exact idle Ollama PID 3892/creation/image and shared desktop processes; this was sole model-job coordination, not hardware exclusivity.

## Change inventory and review map

All additions since the runtime base are under `docs/reviews/WP-0012/eld-f4-reviewer/live-004/rehearsal-004/`, plus this report. The [final inventory](../../../reviews/WP-0012/eld-f4-reviewer/live-004/rehearsal-004/final-inventory.json) identifies 61 artifacts by size/hash; the inventory itself and this later report are separate metadata. All 3,896 inherited Git paths and the exact accepted product trees are unchanged. No shared routing, production source, dependency, model, fixture or prior report changed.

| Added paths or external effects | Purpose and persistence |
| --- | --- |
| `.gitattributes`, `helpers/collect_reviewer004.py`, `helpers/audit_reviewer004.py` | Byte preservation, frozen read-only accounting/copy collector and frozen offline semantic/inventory audit. The collector follows the already used author003 inventory/read-only SQL approach with reviewer-specific exact bindings. |
| `evidence/attempts/**` | Both original input PDFs, requests, worker streams, envelopes, heartbeats and exact raw UTF-8 bytes. |
| `evidence/browser/**`, `evidence/launch/**` | Original validation/live/return/Q0 receipts, browser phases, nine screenshots, service logs, launcher source/freeze, exact argv and PID/creation events, original stdout/stderr and actual tool completion. |
| `evidence/bindings/**`, `evidence/database/**`, `evidence/collection-inventory.json`, `semantic-audit.json` | Nine copied Git inputs, durable table snapshot, historical preservation, accounting commands, complete originals/copies inventory and 20-check audit. |
| External reviewer runtime root and owned database | Two durable document/attempt/result sets, human revisions and projections retained. Generated caches retained only in the runtime root. Services stopped; no resources were deleted. |

[The collection inventory](../../../reviews/WP-0012/eld-f4-reviewer/live-004/rehearsal-004/evidence/collection-inventory.json) verifies 104 external runtime/launch files: 44 copied and 60 generated cache files retained only, all with hashes and disposition. There are 56 copied artifacts in total: those 44, nine exact Git inputs and three database/accounting files. The final audit also binds four unchanged runtime helper files. All 62 previously inventoried external artifacts remained unchanged. Secrets stayed outside Git. Inspect [the exact evidence diff](https://github.com/jackgumpe/eledgercare/compare/bf2172c9ecaab63de038300960082f3b521f8074...2bf824375d79b9a3ef8919ffc782a8e1e2220bbb) alongside these inventories.

## Executed checks and actual outcomes

Here `P = docs/reviews/WP-0012/eld-f4-reviewer/live-004/rehearsal-004`. The [original launcher receipt](../../../reviews/WP-0012/eld-f4-reviewer/live-004/rehearsal-004/evidence/launch/launcher-receipt.json) contains full literal argv, outputs, times and creation identities. Launcher SHA256 is `867f52edb387ab67f782a4ddf9b4bae8123034efe026fb9b7e0b7befec472011`, frozen before execution at 18:11:44.985320Z.

| Exact command or operation | Actual result |
| --- | --- |
| `python -B .local/wp0012-reviewer004-r3-20261117T181101Z/launch_once.py` | Executed once at held base. Validation PID 9384, creation FILETIME 134394127098961102, 18:11:49.890938–18:11:51.101510Z, exit 0. Live PID 38196, creation 134394127111073911, 18:11:51.101510–18:20:39.951937Z, exit 0. Wrapper PID 32712, creation 134394127097262509, exit 0. Tool session 43402, initial chunk `b8187f`, completion `6a806d`, exit 0. |
| V7 `--mode validate-release-cpu`, then once `--mode live-leased-rehearsal`, exact authority/release and separate native03 paths | Actual release validation, Q0/model immutability, ownership, disk/local dependencies, real OCR/browser workflow, restart, cleanup and return all passed. Full arguments and original streams are retained, rather than reconstructed from this shorthand. |
| Actual Edge phase1 and phase2 through the frozen driver | Two extraction requests/two observed POSTs in phase1; all source/query/history assertions passed. Phase2 both workers disabled, one attempt per document, zero extraction POSTs, empty local/session storage. |
| `python -B P/helpers/collect_reviewer004.py` at `e463bb3ed624baacda05c2f58232ef0b8b68bdae` | Tool `c93010`, exit 0. Read-only PG accounting started 18:25:36.690322Z, stopped18:25:39.781845Z, after actual root ACK. Copies, original hashes, prior artifacts, historical DBs and final owned process/port return verified. No API/UI/model started. |
| `python -B P/helpers/audit_reviewer004.py` at `be646cbd9fac9ed1ac316be11c9ac7800e33f691` | Tool `7ee058`, exit 0; 20/20 offline checks, recorded18:28:11.731520Z. Exact database/runtime bytes and provenance, review/query/restart semantics, return, unchanged product trees and inherited paths passed. |

The [semantic audit](../../../reviews/WP-0012/eld-f4-reviewer/live-004/rehearsal-004/semantic-audit.json) and [durable snapshot](../../../reviews/WP-0012/eld-f4-reviewer/live-004/rehearsal-004/evidence/database/post-restart-tables.json) retain both complete actual attempts. Each has attempt_number 1, no retry parent, completed status and worker exit 0.

| Input | Fresh document / attempt | Actual output and timing |
| --- | --- | --- |
| `SYN-WO-01-v1-raster300.pdf`, 1 page, 372,258 bytes; SHA256 `47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd` | Document `01a1eab5-894c-7734-8b5e-616320cb1268`; attempt `01a1eab5-8bc4-7b78-b49e-d195ef17a94e` | 3,236 raw bytes, 1,122 output tokens; raw SHA256 `7503761ae46afef6adf579881d011764283474354fac3e185598fc7d266aff95`. Started18:12:09.153777Z, completed 18:14:53.837725Z; total 164,690ms, load 11,870/render 162/infer 141,795ms. |
| `SYN-MP-01-v0-clean.pdf`, 3 pages, 8,422 bytes; SHA256 `15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3` | Document `01a1eab8-2463-7bd8-b22d-1feb6d76e1d1`; attempt `01a1eab8-2500-7ba0-b002-9f97af23cb62` | 7,511 raw bytes, 2,513 output tokens; raw SHA256 `c399ad892e257500e2b6a9ac8b0bc3d8a17e9c10041262c4bca6a48fb9b9b639`. Started18:14:59.338041Z, completed 18:20:12.773238Z; total 313,434ms, load 11,413/render 317/infer 291,116ms. |

The model was unchanged `baidu/Unlimited-OCR-2` revision `0480966938291445591f69f08a13b041c073a96a`; Q0, renderer/dependency/worker/configuration hashes match their pinned records. The established torchvision trust exception and `triton_import_failed_dense_fallback` remain disclosed in original provenance. UI elapsed times were168,419ms and 317,282ms. These two observations are not a performance benchmark.

## Durable workflow disposition

The stored state contains two documents, originals, processing jobs, attempts, results and review heads; three human revisions, 15 review fields, two archive projections and four projection units. Database original PDF/raw-output values match the runtime files, byte counts, request/envelope hashes and provenance. Original model output remains immutable and visibly unreviewed.

For the work order, reviewed revision 1 contains four accepted source values (`WO-004192`, `Cedar Hollow Apartments`, `Bldg B - Unit 204`, `2026-10-16`) and one edited issue summary with grounded SKU `CAP-45-5MFD-440V`. A later draft revision 2 adds completion/supervisor details. Reopening the reviewed search witness pins revision 1 while head 2 remains an unapproved draft; draft-only Callahan content does not enter reviewed search.

For the monthly statement, reviewed revision 1 contains two edited values and three explicit unknowns: work-order ID, building/unit and requested date. Unknown values remain null with substantive reasons; this multi-work-order monthly statement does not supply one defensible value for those fields. No suggestion/source-page citation is invented where the original machine suggestion was absent. The human issue summary records the source's billing period beginning `2026-10-01` and total `$1,535.35`; raw machine text retains its actual incorrect `2025-10-01`. This is workflow evidence, not an accuracy acceptance or a claim that every field is known.

The [phase1 query receipts](../../../reviews/WP-0012/eld-f4-reviewer/live-004/rehearsal-004/evidence/browser/edge-live-phase1.json) distinguish machine content, reviewed values and unknown/draft exclusion: machine `WO-004724` finds the statement while its unknown reviewed work-order value does not; reviewed Callahan has no result while machine Callahan finds the work order; reviewed SKU and corrected billing date find the intended documents. Source links target the matching original page, and historical review reopening preserves the draft. The driver subsequently clicked `witness-open-reviewed` and asserted historical revision 1/head 2; this is stronger evidence of that interaction than the still-loading screenshot06.

The [post-restart receipt](../../../reviews/WP-0012/eld-f4-reviewer/live-004/rehearsal-004/evidence/browser/edge-live-phase2-post-restart.json), verified 18:20:30.577Z, records actual API `woWorkerEnabled=false` and `mpWorkerEnabled=false`, one attempt each, no new extraction POST and empty browser storage. Saved source/history/query semantics were exercised after restarting API/PostgreSQL; offline accounting then confirmed durable rows. Both historical reviewer databases retain their previous canonical digest; only the already migrated historical database has the F4 projection digest, also unchanged.

## Evidence limits and preserved failures

Visual inspection of the original PNGs is narrower than the successful browser assertions. Screenshot02 shows saved draft 2, the earlier reviewed revision and a painted one-page original. Screenshot04 shows reviewed revision 1 with three unknowns, but its app page indicator says 3 while the native PDF pane still shows page1. [Screenshot06](../../../reviews/WP-0012/eld-f4-reviewer/live-004/rehearsal-004/evidence/browser/screenshots/live-06-archive-reviewed-newer-draft.png) reads “Searching…” / “Loading archive results…”; it does not visually prove completed archive cards or a newer-draft label despite the preceding DOM wait. [Screenshot08](../../../reviews/WP-0012/eld-f4-reviewer/live-004/rehearsal-004/evidence/browser/screenshots/live-08-post-restart-mp01-page2.png) and screenshot09 show dark, unpainted native PDF panes. The successful URL `#page=2`, range-read, DOM page-indicator and extracted-page highlight checks do not prove painted native target-page pixels. All nine originals remain unchanged. No product defect is inferred from these capture timing limits, and no screenshot-only UI/model rerun occurred.

Both earlier live invocations are preserved as refusals, not successful runs. Native01 validated 0 then live/wrapper 2 and outer tool 1 before Q0/services/model: v5 rejected accounted idle Ollama and its own observer. It emitted no original summary/return; root separately closed its lease. Correction008 preserves the initial v6 app-alias image mismatch/root read-only failure, the narrow actual-image fix and independent009 acceptance. Native02 validated 0 then live/wrapper/tool 1 after actual Q0 verification, with `KeyError: 'demo_root_bytes'` before services/model and before its return-finally. Its missing summary/return and root closure remain in010. Both consumed zero OCR attempts; each renewed release used new paths and explicit root reconciliation.

Correction010 also preserves its first CPU adapter's historical-schema failure; corrected CPU integration kept actual counts zero. Independent011 preserves its post-cleanup Windows long-path copy failure/outer exit 1 and separate file-only recovery 0. None is relabelled a passing live run. The earlier author/preparation findings and Carbon low-credit termination remain in their immutable reports/checkpoints. No reviewed source was silently repaired during actual native03 execution.

## Resource return and handoff

[The actual owner receipt](../../../reviews/WP-0012/eld-f4-reviewer/live-004/rehearsal-004/evidence/browser/resource-return.json) at 18:20:39.931168Z records `status=completed`, `lease_returned=true`, `clean_return_verified=true`, no cleanup errors, empty owned ports and PostgreSQL status 3. Both actual model workers exited0. Deliberately stopped API/UI processes report exit 1 with `aliveAfter=false`; their stop codes are not relabelled worker failures or exit 0. Exact PID/creation identities and pre/post ownership evidence remain in the originals.

Root's actual [lease-return acknowledgement](../../../reviews/WP-0012/eld-f4-reviewer/live-004/rehearsal-004/evidence/bindings/02-lease-return-ack.json) is commit `6a3408747201693a45aa09228af58420ea07cdef`, at 18:23:11.221876Z. Earlier `09152856d4a6a553facbdc0eeeb0600878cfd738` preserved observations but did not contain the ACK despite premature commit wording; the encoding-name writer failure and correction metadata remain copied. No database accounting began before the actual ACK. The later read-only accounting ended with PG stopped/status 3, owned ports empty and owned exact identities absent; it started no API/UI/model. Historical databases, native01/native02, actual native03 originals and both fresh run directories remain retained.

No general accuracy evaluation, hardware-exclusive timing study, network-denial proof, customer input, dependency change, production deployment or broad unchanged-suite rerun was performed. These were outside this bounded rehearsal. The accepted runtime and product source are unchanged; no further reviewer execution is required for this disposition. Root retains final005 acceptance/publication responsibility.

Evidence/audit commit `2bf824375d79b9a3ef8919ffc782a8e1e2220bbb` was pushed and matched exact origin before this report was written. This later report's own publication SHA and remote confirmation will be sent separately to `eld-coordinator`; no self-referential publication identity is claimed here.
