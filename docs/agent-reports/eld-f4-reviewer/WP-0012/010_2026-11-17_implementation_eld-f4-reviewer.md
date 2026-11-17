# WP-0012 / 010: Actual Q0 and disk integration with complete disabled lifecycle proof

- Report path: `docs/agent-reports/eld-f4-reviewer/WP-0012/010_2026-11-17_implementation_eld-f4-reviewer.md`
- Sequence reservation: `INDEX.md` and `docs/kickoffs/WP-0012-reviewer-integration-010-011.md` at `bc5b345d812fdd3bdcf6eb7ae6b5a43b895d8113`.
- Category: implementation
- Author / agent ID: `eld-f4-reviewer`
- Actual model / effort: native Codex `/root/product_reviewer_continuation`; requested xhigh; actual backend/applied effort unexposed.
- Execution environment: native Codex/Windows PowerShell, standard-library Python, existing local PostgreSQL/.NET/Node/Edge dependencies.
- Published by: `eld-f4-reviewer`, native continuation
- Timestamp: 2026-11-17T17:56:31Z
- Repository / branch: `https://github.com/jackgumpe/eledgercare.git` / `review/wp-0012-product-rehearsal`
- Base revision: `ae71a7362718f36e351e3fd442d9751d875146fe`
- Deliverable revision: source `5e75cacd11f18bf6135376e3e1e10887c1447e1f`; initial check `dbbf03ed45a39cb2dacdff87e1614aff09288b97`; corrected check `f53794d4b8ffc6569a1243d8f38ebbbf457d0528`; inventory helper `781297f67b2bb55dfd0c94c9d01795b91d0d3c95`; evidence/inventory `d3e40c8680683291e68bd1d28d5cb99f69d18ff9`.
- Previous report: [Reviewer /008](008_2026-11-17_implementation_eld-f4-reviewer.md).
- Related review: [Independent /009](https://github.com/jackgumpe/eledgercare/blob/b2cca5227b27f326e437cc99f2a9b40ba08c6c94/docs/agent-reports/eld-f4-implementer/WP-0012/009_2026-11-17_review_eld-f4-implementer.md), unchanged acceptance of the ownership correction; new /011 is separately assigned.
- Status: ready-for-review
- Next owner: `eld-f4-implementer` for independent /011, then `eld-coordinator` for any new exact /004 runtime release.

## Summary

V7 fixes the demonstrated Q0/disk contract error by measuring actual owned-root file sizes and volume free space independently of the Q0 model-verification receipt. It also checks the real Q0 receipt's conditions before services and after cleanup. A complete CPU integration executed actual Q0 verification, PostgreSQL subset verification, offline build, database snapshots, API/UI startup, two read-only empty-archive browser phases across a real restart, and final cleanup. A separate deliberate boundary failure also returned resources cleanly. All actual document/attempt/result counts remained zero.

This is author verification of a reviewer-owned harness correction. CPU adapters and synthetic phase IDs do not establish live workflow success. Independent /011 and a fresh root lease remain required. V6, /008, /009, product/worker source, fixtures and both original runtime refusals remain unchanged.

## Objective and acceptance criteria

Correct the observed missing disk fields, inspect every preparation-helper call/return and browser interface through full main, and exercise those real boundaries with OCR disabled. Block all live browser modes, uploads, queueing and model execution. Preserve failures, original exits, missing-return facts, prior databases and actual zero counts. Freeze source/checks before execution and hand resources to independent /011 only after return.

## Change inventory and review map

All changes add files under `docs/reviews/WP-0012/eld-f4-reviewer/live-004/integration-correction/`, plus this reserved report. [The complete inventory](../../../reviews/WP-0012/eld-f4-reviewer/live-004/integration-correction/final-inventory.json) records 62 artifacts, 52 exact copied originals, 15 source/evidence bindings and 29 retained input descriptors; all 3,832 inherited Git paths are unchanged. The inventory itself and this later report are separately identified metadata. [Input provenance](../../../reviews/WP-0012/eld-f4-reviewer/live-004/integration-correction/input-inventory.json) includes static Q0 files, notices and existing dependencies; local credentials remain outside Git.

| Added paths under the owned prefix | Purpose |
| --- | --- |
| `helpers/run_wp0012_reviewer_rehearsal_v7.py`, `helpers/ownership_v6.py` | New v7 caller; ownership module copied byte-identically from independently accepted v6. |
| `helpers/check_v7_integration_cpu.py`, `helpers/check_v7_integration_cpu_v2.py`, `helpers/build_010_inventory.py` | Frozen actual-Q0/disk controls, complete disabled-main adapters and exact evidence collector. Original failed adapter preserved. |
| `BOUNDARY-AUDIT.md`, `.gitattributes` | Full interface audit and evidence byte preservation. |
| `native-02-refusal/**`, `evidence/**`, copy/input inventories | Original renewed-runtime failure, root closure, all CPU attempts, actual browser images, logs, PID/creation records, zero-count accounting and return receipts. |

V7 SHA256 is `9a445e00a812c79928c81922c1c43716bf4f04fe48cc8e7fae8f3f1106648c61`; unchanged ownership SHA256 is `ff01e70c09c1e7b69cbed3c660f9f6cb777d381a920a51af7e1204d24eee6d9f`. Inspect [the exact source diff](https://github.com/jackgumpe/eledgercare/compare/ae71a7362718f36e351e3fd442d9751d875146fe...5e75cacd11f18bf6135376e3e1e10887c1447e1f) and [boundary audit](../../../reviews/WP-0012/eld-f4-reviewer/live-004/integration-correction/BOUNDARY-AUDIT.md). No shared routing or other-owner source changed.

## Decisions and actual failure history

Renewed /004 on clean `ae71a736...` passed release validation and actual ownership, wrote the real Q0 receipt, then raised `KeyError: 'demo_root_bytes'` at v6 line 1202 before services/model and before its receipt-finally. Validation exited 0; live helper/wrapper/tool exited 1 at 17:39:54.290817Z, tool `f941c2`. [Original streams and launch identities](../../../reviews/WP-0012/eld-f4-reviewer/live-004/integration-correction/native-02-refusal/launcher-receipt.json) remain. No summary or owner return receipt was produced. Root separately closed that lease at 17:44:38.4885933Z after independent process/port/run observations; [its closure](../../../reviews/WP-0012/eld-f4-reviewer/live-004/integration-correction/native-02-refusal/root-reconciliation.json) does not invent an original receipt. Zero model attempts were consumed.

The actual preparation verifier returns model/notices/dependency metadata, not disk measurements. V7 explicitly enumerates the owned tree without following links, sums actual sizes and calls `shutil.disk_usage`; failed/malformed, missing/linked, over-cap or below-floor observations fail closed. Disk evidence is a separate `owned_demo_storage` object. The four preparation calls—Q0 pre/post and canonical eight-table snapshot pre/final—now use their actual signatures and schemas. Browser CLI pairs and phase-one document-ID output agree with the unchanged driver; the audit covers startup, restart, snapshots, scrub, process/port checks and return construction.

The first CPU lifecycle exposed a separate test-adapter mistake: it queried F4 projection tables in the retained F3 seed database, where those tables correctly do not exist. [That failed attempt](../../../reviews/WP-0012/eld-f4-reviewer/live-004/integration-correction/evidence/lifecycle-01/result.json) and its explicitly unreturned CPU receipt remain. It started/stopped PostgreSQL but reached no API/UI/browser/model startup. Ports/runs were empty and PostgreSQL status was 3 afterward. Adapter v2 alone corrected historical accounting to the existing preparation distinction: canonical eight-table snapshots for both historical databases, projection snapshot only for the migrated F4 database. Runtime v7 source stayed unchanged.

## Verification

Here `P = docs/reviews/WP-0012/eld-f4-reviewer/live-004/integration-correction`; `E = C:/Users/jackg/eLedgerCare-Demo/WP-0012/reviewer/rehearsal-evidence`.

| Exact command | Frozen/executing identity | Actual result |
| --- | --- | --- |
| `python -B P/helpers/check_v7_integration_cpu.py --mode controls --output-dir E/WP-0012-reviewer-v7-cpu-controls-01` | `dbbf03ed45a39cb2dacdff87e1614aff09288b97`, source `5e75cac...` | Exit 0, tool `9ee9a5`, 12/12 controls, actual Q0 receipt; 17:49:38.128447–17:49:42.828538Z. Covers original missing field, real disk sizes and refusal cases. |
| `python -B P/helpers/check_v7_integration_cpu.py --mode lifecycle --output-dir E/WP-0012-reviewer-v7-cpu-lifecycle-01` | Same frozen check/source | Exit 1, completion tool `1b76d3`, 17:50:02.875204–17:50:36.894304Z. Historical-schema adapter failure preserved, not source success. |
| `python -B P/helpers/check_v7_integration_cpu_v2.py --mode lifecycle --output-dir E/WP-0012-reviewer-v7-cpu-lifecycle-02` | `f53794d4b8ffc6569a1243d8f38ebbbf457d0528`, same source | Exit 0, tool `f0f063`, 17:51:44.024413–17:52:52.876965Z. Actual complete restart lifecycle plus deliberate failure/cleanup passed. |
| `python -B P/helpers/build_010_inventory.py` | `781297f67b2bb55dfd0c94c9d01795b91d0d3c95` | Exit 0, tool `8f0efd`; all copies/source bindings/inherited paths verified, no local secret values in artifacts. No service observation while independent /011 owns resources. |

The [complete CPU result](../../../reviews/WP-0012/eld-f4-reviewer/live-004/integration-correction/evidence/lifecycle-02/complete-cpu-lifecycle/adapter-result.json) records real Q0 pre/post verification and eight-table counts, two unchanged historical databases, actual service identities, two successful empty-browser phases, no non-GET API calls and no browser storage. Both captured screenshots show the empty archive. The [deliberate failure result](../../../reviews/WP-0012/eld-f4-reviewer/live-004/integration-correction/evidence/lifecycle-02/deliberate-boundary-failure/adapter-result.json) records the intentional stop before phase one and clean final cleanup. Both final observations show ports 55439/5690/4710 empty, PostgreSQL status 3 and runs empty. Sequential resource use was explicitly handed to independent /011 at 17:52:52.876965Z.

The test-only adapter replaces release validation with `CPU-INTEGRATION-NOT-A-LEASE`, forces every actual API launch to `LocalOcr__Enabled=false`, checks that again at `Popen`, and prevents live browser execution. Actual read-only browser receipts are separate from explicitly synthetic phase-ID plumbing. Thus complete main exit 0/status `completed` means the CPU boundary exercise completed; it is not two-attempt live acceptance. The actual eight-table counts, including attempts/results, are all zero. The real two-attempt invariant remains in unchanged live browser assertions, which were not executed. No fabricated two-attempt success or invented main-count failure is claimed.

## Risks, unfinished work and handoff

This correction contains no model/API-enabled run, upload, queue request, production change, dependency installation or broad unchanged-suite rerun. Original Carbon-derived helpers and prior reports remain immutable. Both runtime refusals and the test-adapter failure remain visible. The required real independent workflow /004 is unfinished.

Independent /011 must inspect and test exact source `5e75cacd11f18bf6135376e3e1e10887c1447e1f` and this /010 publication. Root must then bind fresh observations, accepted source/review, clean executing HEAD, new output paths and a new sole lease before any live invocation. Branch `review/wp-0012-product-rehearsal`; evidence/inventory `d3e40c8680683291e68bd1d28d5cb99f69d18ff9`. The report-only publication SHA and exact-origin receipt follow separately after publication.
