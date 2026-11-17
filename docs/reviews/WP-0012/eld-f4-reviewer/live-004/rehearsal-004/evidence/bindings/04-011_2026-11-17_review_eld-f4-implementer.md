# WP-0012 / 011: Independent acceptance of v7 Q0/disk and lifecycle integration

- Report path: `docs/agent-reports/eld-f4-implementer/WP-0012/011_2026-11-17_review_eld-f4-implementer.md`
- Sequence reservation: coordinator `bc5b345d812fdd3bdcf6eb7ae6b5a43b895d8113`, `docs/kickoffs/WP-0012-reviewer-integration-010-011.md` and INDEX, inspected through Git.
- Category: review
- Author / agent ID: `eld-f4-implementer`
- Actual model / effort: native Codex `/root/product_author_continuation`; requested xhigh; actual backend and applied effort not exposed.
- Execution environment: Windows PowerShell/native Codex, standard-library Python, existing reviewer PostgreSQL/.NET/Node/Edge resources under explicit sequential transfer.
- Published by: `eld-f4-implementer`, native continuation
- Timestamp: 2026-11-17T18:01:26Z
- Repository / branch: `https://github.com/jackgumpe/eledgercare.git` / `rehearsal/wp-0012-product`; worktree `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-f4-implementer`.
- Base revision: `b2cca5227b27f326e437cc99f2a9b40ba08c6c94`
- Deliverable revision: independent pure-check freeze `ff21272a0c45d2859e273003a61e5ff88be78abb`; lifecycle freeze `6803bca48d57c1c026f9317ce764063441ba2d79`; completed evidence `0cfe43870eeb44fb7fdfde69c272aeb0654a3f4d`; inventory `8618d90c91b61bdbb60584f4fdd0be0393af4ccd`.
- Previous report: [Independent /009](009_2026-11-17_review_eld-f4-implementer.md), unchanged narrow ownership acceptance.
- Reviewed report: [Reviewer implementation /010](https://github.com/jackgumpe/eledgercare/blob/bf2172c9ecaab63de038300960082f3b521f8074/docs/agent-reports/eld-f4-reviewer/WP-0012/010_2026-11-17_implementation_eld-f4-reviewer.md), exact publication `bf2172c9ecaab63de038300960082f3b521f8074`.
- Status: accepted
- Next owner: `eld-coordinator`, for disposition and any separately bound reviewer /004 release.

## Summary

Accept reviewer-owned v7 source `5e75cacd11f18bf6135376e3e1e10887c1447e1f`. Independent verification passed 20 actual-Q0/schema/storage controls and both complete-main CPU lifecycle scenarios, with 15 assertions each. Real database counts remained zero; actual startup, browser checks, restart, Q0 verification, historical preservation and cleanup completed. I did not author this reviewer helper. This review concerns its harness integration, not my previously authored product implementation.

The lifecycle wrapper's actual exit remains **1**: after both scenarios passed and services stopped, screenshot copying failed at a 264-character Windows destination. The failure, partial copies and original streams are immutable. A separately frozen file-only collector completed all 20 original artifact copies with matching hashes; no test or service was rerun. This packaging failure is not concealed by the passing lifecycle assertions.

## Objective and acceptance criteria

Verify the actual preparation-helper signatures and returned schemas, reproduce the original missing-disk-field defect with the actual Q0 receipt, and test v7's independent real disk measurement. Exercise full main through actual OCR-disabled PG/API/UI startup, empty-archive browser, restart and cleanup, plus deliberate boundary failure. Block live browser/upload/queue/model paths, preserve zero counts and historical databases, and retain original failures and source identities.

## Change inventory

Here `P` means `docs/implementation/WP-0012/eld-f4-implementer/reviewer-v7-independent-check`. [The exact inventory](../../../implementation/WP-0012/eld-f4-implementer/reviewer-v7-independent-check/final-inventory.json) enumerates all 65 input/helper/evidence artifacts, 574,706 bytes, with SHA-256 and Git metadata. All 3,818 inherited Git rows, including /009, are unchanged. The inventory itself and this report are the only two later metadata additions.

| Added paths under P | Purpose |
| --- | --- |
| `.gitattributes`, `control-intent.json`, `input-identities.json`, `v7-input-identities.json`, `inputs/**` | Independent preparation, byte preservation, exact v6/v7/preparation/browser copies, source diff, original second refusal/Q0/root closure. |
| `helpers/check_boundaries.py`, `helpers/check_lifecycle.py`, `helpers/collect_lifecycle.py` | Frozen independent schema/storage controls, actual-main CPU adapters, then separate file-only collection recovery. |
| `evidence/pure-01/**`, `evidence/lifecycle-01/**` | Actual Q0 receipt, controls, both lifecycle outcomes, commands/PIDs/exits, original wrapper failure and partial original copies. |
| `evidence/files-01/**`, `evidence/author-audit.json`, `final-inventory.json` | Complete short-path copies with original-to-copy mapping, author source/evidence verification and full inventory. |

External effects used only the explicitly transferred reviewer PG 55439/API 5690/UI 4710, existing empty `eledgercare_demo_wp0012_reviewer`, read-only historical snapshots, and new `C:/Users/jackg/eLedgerCare-Demo/WP-0012/reviewer/independent-011/run-01` evidence. Existing runs stayed empty. No production/worker/fixture/source change, dependency install, upload, queue request, GPU command, model import or inference occurred.

## Decisions and rationale

The real Q0 verifier returned its 18-file, 6,699,195,181-byte verification receipt, without either disk field. Executing the exact original v6 disk-consumer AST against that actual receipt reproduced `KeyError('demo_root_bytes')`; this was an isolated original-consumer reproduction, not another live invocation. V7 accepts the actual receipt, rejects altered/missing schema conditions, and measures actual file sizes and volume free space separately. Controls covered real byte totals and over-cap behavior, missing/file roots, below-floor/malformed free-space observations, and injected linked/inaccessible entries.

All four `prep_mod` calls bind to the real function signatures: Q0 pre/post and canonical eight-table snapshot pre/final. AST comparison confirms only `main` changed among existing functions; the two new helpers implement Q0 receipt validation and storage measurement. The ownership module is byte-identical to accepted v6. Release, output, startup, cleanup and return functions remain unchanged. The [source diff](../../../implementation/WP-0012/eld-f4-implementer/reviewer-v7-independent-check/inputs/v6-to-v7.diff) supports that bounded scope.

The independent lifecycle harness invoked actual v7 `main` with explicit test-only release/ownership placeholders, forced every API subprocess environment to `LocalOcr__Enabled=false`, and blocked both live browser modes. At those boundaries it executed the unchanged real `cpu-preflight --target empty-ready-db` browser mode. Labelled synthetic document IDs tested phase-two argument plumbing only. Actual Q0, disk, PostgreSQL subset, database snapshots, ports, startup, restart, scrub and cleanup ran unchanged. Canonical snapshots covered both historical databases; projection snapshots covered only the migrated F4 database, respecting the actual schemas.

## Verification

Commands use P above. Exact absolute argv, source commits, timestamps and original streams are retained with each result. Helper/input bytes were checked against exact Git objects and actual reviewer files before execution.

| Executed check | Actual outcome and evidence |
| --- | --- |
| `python -B P/helpers/check_boundaries.py --output P/evidence/pure-01` | Frozen `ff21272a0c45d2859e273003a61e5ff88be78abb`; 20/20 controls and actual original-consumer reproduction pass; exit 0, tool `02e6d6`, 17:50:22.974246–17:50:27.837434Z. [Result](../../../implementation/WP-0012/eld-f4-implementer/reviewer-v7-independent-check/evidence/pure-01/result.json). |
| `python -B P/helpers/check_lifecycle.py --output P/evidence/lifecycle-01 --external-name run-01 --reviewer-return-message <recorded exact sequential return>` | Frozen `6803bca48d57c1c026f9317ce764063441ba2d79`; complete main returned 0 with 15/15 assertions, finished 17:55:56.986115Z. Deliberate first-browser-boundary exit 7 raised the expected main exception, then 15/15 cleanup/state assertions passed at 17:56:20.453869Z. Wrapper/tool exit **1**, `c49865`, 17:56:20.500634Z, from subsequent file copying. [Complete outcome](../../../implementation/WP-0012/eld-f4-implementer/reviewer-v7-independent-check/evidence/lifecycle-01/complete.json), [deliberate failure](../../../implementation/WP-0012/eld-f4-implementer/reviewer-v7-independent-check/evidence/lifecycle-01/boundary-failure.json), [original stderr](../../../implementation/WP-0012/eld-f4-implementer/reviewer-v7-independent-check/evidence/lifecycle-01/stderr.log). |
| `python -B P/helpers/collect_lifecycle.py --output P/evidence/files-01` | Separate frozen collector `a3f14a7d580d8741619df12e846b3118c87f608a`; file-only exit 0, tool `1af866`, 17:58:55.989028Z; all 20 originals copied and hashed, no service/test rerun. [Original-to-copy manifest](../../../implementation/WP-0012/eld-f4-implementer/reviewer-v7-independent-check/evidence/files-01/manifest.json). |
| Exact Git blob/tree audit, tool `ac5462` | Author evidence `d3e40c8680683291e68bd1d28d5cb99f69d18ff9`: 62 artifact hashes, 15 source bindings, 3,832 inherited rows verified; source unchanged through report-only publication `bf2172c9...`. [Audit](../../../implementation/WP-0012/eld-f4-implementer/reviewer-v7-independent-check/evidence/author-audit.json). |
| Own committed-byte/tree and external-copy inventory, tool `b731e7` | 65 artifacts, 20 exact external copies, all 3,818 inherited rows unchanged; owned namespace only. [Inventory](../../../implementation/WP-0012/eld-f4-implementer/reviewer-v7-independent-check/final-inventory.json). |

The reviewer explicitly transferred services after its 17:52:52.876965Z return. My complete scenario used two actual API/UI launches and two read-only browser phases across PG/API/UI restart. The failure scenario used one launch and deliberately stopped at the first browser boundary. Each retained actual pre/final database snapshots with eight counts zero, zero archive projections/units, matching historical hashes and unchanged Q0 files. Both final observations show all three ports empty, PG status 3, runs empty and captured children exited. Forced service-stop child exits are recorded as 1; they are not represented as graceful exit 0. Actual final resource return was sent immediately, before file-only recovery.

Both [pre-restart](../../../implementation/WP-0012/eld-f4-implementer/reviewer-v7-independent-check/evidence/files-01/007.png) and [post-restart](../../../implementation/WP-0012/eld-f4-implementer/reviewer-v7-independent-check/evidence/files-01/009.png) images were inspected and show the empty archive. Browser receipts record zero all/machine/reviewed rows, zero non-GET calls and empty browser storage. Actual API launch environments were disabled; no persisted document or synthetic phase ID was created in PostgreSQL.

## Risks, failures and unfinished work

Both original runtime refusals remain historical. The second refusal and root's separate closure are copied from `bc5b345d...`; the missing original owner receipt remains missing. Author /010 also preserves its first adapter failure from querying F4 projection tables on an F3 seed. That author test failure is distinct from my subsequent screenshot-copy failure. The original independent wrapper exit 1 remains visible at outcome commit `6a612fd7fd1b060be9061d7e2081cfd6e0ff9820`; its failed destination was 264 characters, parent existed and source PNG was present. File-only collection completed the evidence without changing v7 or rerunning either scenario.

CPU main exit 0/status `completed` is only CPU integration completion. The actual counts are zero; the unchanged live browser's two-attempt requirement was not executed and remains unsatisfied. No invented main-count failure or fabricated live success is asserted. This review does not prove real OCR/browser extraction correctness or continuing GPU ownership. Existing product suites were not rerun. No unresolved finding remains in the released v7 integration correction; real independent /004 remains unfinished.

## Handoff

Accept /010 only on exact source `5e75cacd11f18bf6135376e3e1e10887c1447e1f` and publication `bf2172c9ecaab63de038300960082f3b521f8074`. Root should audit this /011 and alone bind any fresh /004 lease, observations, clean executing HEAD and new output namespace. No live authority follows from this acceptance.

Independent evidence `0cfe43870eeb44fb7fdfde69c272aeb0654a3f4d` and inventory `8618d90c91b61bdbb60584f4fdd0be0393af4ccd` were pushed to the exact origin; remote HEAD was verified before this report. The later report-only publication SHA and final clean-origin receipt follow in the handoff. Root alone edits shared routing.
