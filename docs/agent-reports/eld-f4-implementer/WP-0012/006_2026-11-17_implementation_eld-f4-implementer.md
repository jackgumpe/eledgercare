# WP-0012 / 006: CPU rehearsal-helper correction after independent changes requested

- Report path: `docs/agent-reports/eld-f4-implementer/WP-0012/006_2026-11-17_implementation_eld-f4-implementer.md`
- Sequence reservation: `INDEX.md`, WP-0012 / 006, author `eld-f4-implementer`, at coordinator handoff authority `3bc2ba5cf5db6698d71c99fccc957e54936fb6c2`; exact correction and native-continuation kickoffs inspected through Git without merging the combined R&D branch.
- Category: implementation
- Author / agent ID: `eld-f4-implementer`
- Actual model / effort: Native Codex continuation `/root/product_author_continuation`; backend model and actual applied effort not exposed; requested `xhigh`. Runtime markers are `native-codex-backend-unexposed` and `xhigh-requested`. Original partial authorship remains Carbon `gemini-4-carbon-high/high`, conversation `b7c54417-db09-49bd-8d2b-7cc808f113be`.
- Execution environment: Windows PowerShell / native Codex tools; Python `3.12.10`, Node `v24.18.0`; worktree `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-f4-implementer`.
- Published by: `eld-f4-implementer`, native continuation
- Timestamp: 2026-11-17T16:36:02.509596+00:00
- Repository / branch: `https://github.com/jackgumpe/eledgercare.git` / `rehearsal/wp-0012-product`
- Base revision: `379d8c5d607fd248d7f272e412b4ed4a97bc64f6`
- Deliverable revision: final frozen `4ca6bc2dfba3548c6d0dfb820594d25e9c2c9cd4`; exact unmodified Carbon checkpoint `d9de3bf1719384c8f6801d78278438a3fdde2e22`; initial candidate/evidence `6d055395b2a4cf22a7926f1728bc31dbe2f315a3` / `900cc1775fc9ab40b02b2bb8f318f4f3f4684acb`; final frozen evidence and inventory `c801f5920dd06f083ccf8ff3554d998317435dca`.
- Previous report: [WP-0012 / 001](001_2026-11-17_implementation_eld-f4-implementer.md), publication `165b2421b297bf49181c91af8d05a449ad69e9b5`.
- Related or reviewed reports: [Independent WP-0012 / 002](../../eld-f4-reviewer/WP-0012/002_2026-11-17_review_eld-f4-reviewer.md), publication/base `379d8c5d607fd248d7f272e412b4ed4a97bc64f6`, remains **changes-requested** on original `/001`.
- Status: ready-for-review
- Next owner: `eld-coordinator`, then independent `eld-f4-reviewer` / 007

## Summary

The bounded helper correction addresses F12-B1/B2/B3 and D4, and reconciles D1â€“D3 without changing the accepted application, worker, fixtures, databases, research, or historical publications. This is author verification, not independent acceptance. All 31 affected CPU tests passed against the final frozen candidate, including actual original-helper failure reproduction and corrected-helper recovery with short-lived owned CPU children. No model or renderer was imported, no GPU query or inference ran, and no product service or database was started.

Carbon exhausted provider credits before publication: provider ERROR, wrapper exit 3. The native continuation verified all 12 inherited partial files against the coordinator's SHA-256/byte manifest and committed them unmodified as `d9de3bf1719384c8f6801d78278438a3fdde2e22`. That checkpoint was not passing source. Carbon authored the initial corrected Python/browser drivers, tests, runbook, sample and inventory draft; the native continuation inspected and completed them, corrected remaining cleanup and acceptance gaps, adapted the session identity, and performed the frozen verification. No Carbon identity is claimed for native work.

Before canonical publication, independent frozen probe `24b19113715dbc3f4ec5672525de9236783285c5` found that the first native candidate still emitted `returned_utc` after failed cleanup. Root released a narrow forward correction. Final receipts always contain `receipt_utc`, explicitly set `lease_returned`, and set `returned_utc=null` when cleanup is unverified. Both the initial passing author suite and the independent adverse finding remain in the lineage; the final suite adds assertions for that missing distinction.

## Objective and acceptance criteria

Continue only the released CPU helper correction from independent `/002`: internally clean partial startup; audit workers/processes/ports and scrub logs on success and failure; emit an honest return receipt; refuse reused decisive outputs; accept the documented release key while requiring a later accepting `/007`; and check actual API `workerEnabled === false` after restart. Preserve original `/001`, `/002`, their evidence, accepted source, existing databases, and every retained failure. Independent `/007` acceptance and a later exact sole GPU lease remain prerequisites to original live author `/003`.

## Change inventory

All paths below are added relative to base `379d8c5d...`. Prefix `C` means `docs/implementation/WP-0012/eld-f4-implementer/correction-006/`. The [complete inventory](../../../implementation/WP-0012/eld-f4-implementer/correction-006/inventory-02.json) provides every exact path, bytes, SHA-256 and Git blob identity, plus pinned input identities. All 3,683 inherited paths are unchanged.

| Action | Exact path under C | Purpose / relevant symbols |
| --- | --- | --- |
| Added | `.gitattributes` | Preserves artifact byte formatting from Carbon draft. |
| Added | `RUNBOOK.md` | Correct release fields/modes, native identity, bounded workflow, cleanup semantics and evidence limitations. |
| Added | `sample-synthetic-release.json` | Executable synthetic envelope; cannot authorize live execution. |
| Added | `helpers/run_wp0012_rehearsal.py` | `start_api_and_ui`, `stop_proc`, `execute_live_rehearsal`, `validate_release_contract`, credential scrub and output guards. |
| Added | `helpers/drive_rehearsal_edge.mjs` | API-backed boolean worker-state assertion in the actual Phase B reopen path; CPU guard mode uses the same assertion. |
| Added | `helpers/validate_wp0012_correction_006_cpu.py` | 31 affected CPU tests, syntax/static audit, immutable source freeze and resource observations; refuses existing evidence. |
| Added | `helpers/build_wp0012_006_inventory.py` | Complete source/evidence/input inventory, preservation and relative-link/credential checks; refuses existing inventory. |
| Added | `helpers/__pycache__/build_wp0012_006_inventory.cpython-312.pyc` | Archival exact Carbon handoff bytecode; not decisive source. |
| Added | `helpers/__pycache__/run_wp0012_rehearsal.cpython-312.pyc` | Archival exact Carbon handoff bytecode; not decisive source. |
| Added | `helpers/__pycache__/validate_wp0012_correction_006_cpu.cpython-312.pyc` | Archival exact Carbon handoff bytecode; not decisive source. |
| Added | `retained-failures/README.md` | Accurate original failure, independent return-state finding and native continuation history. |
| Added | `retained-failures/native-prose-edit-error.log` | Retained Windows encoding error during intermediate documentation edit; repaired forward before decisive rerun. |
| Added | `retained-failures/pre-freeze-01-mock-popen-and-short-secret.log` | Original failed Carbon execution, byte-for-byte preserved. |
| Added | `retained-checks/pre-freeze-02-native-inherited-tests.log` | Non-decisive native preparatory run: 26 tests passed. |
| Added | `retained-checks/pre-freeze-03-native-cleanup-tests.log` | Non-decisive native preparatory run: four additional tests passed. |

The final 22-file base-to-source inventory includes the 15 table entries above plus the seven preserved first-run artifacts from evidence commit `900cc1775fc9ab40b02b2bb8f318f4f3f4684acb`: `evidence/logs/01-node-check-edge-driver.log`, `evidence/logs/02-validate-synthetic-sample-cli.log`, `evidence/logs/03-old-fails-new-passes-and-guard-tests.log`, `evidence/synthetic-sample-validation.json`, `evidence/validation-summary.json`, `evidence/resource-return.json`, and `inventory.json`.

Final post-freeze evidence commit `c801f5920dd06f083ccf8ff3554d998317435dca` adds seven fresh paths under C: `evidence-02/logs/01-node-check-edge-driver.log`, `evidence-02/logs/02-validate-synthetic-sample-cli.log`, `evidence-02/logs/03-old-fails-new-passes-and-guard-tests.log`, `evidence-02/synthetic-sample-validation.json`, `evidence-02/validation-summary.json`, `evidence-02/resource-return.json`, and `inventory-02.json`. The later report-only commit adds this canonical report, which cannot contain its own publication SHA.

External effects were confined to short-lived owned CPU subprocesses, temporary scratch directories and an ephemeral loopback HTTP fixture. Each test reaped its children, including the deliberately leaked original-helper children. Author ports `5590/4610/55438` were observed empty, and worktree-owned `pg_ctl status` returned 3 (stopped). The writable demo root's entry list stayed empty. No database commands, service starts, dependency installs, model/renderer imports, GPU scans, inference, Q0 writes, or other-owner process termination occurred.

## Decisions and rationale

- **F12-B1:** Partial startup cleans every started owned child and opened log even if a later child fails or its readiness times out. Teardown attempts both children independently, preserves the original exception and records any cleanup errors. Tree termination verifies PID/creation identity; the retained `Popen` handle provides direct-child fallback when `taskkill` fails.
- **F12-B2:** Success and failure share final cleanup. Producers stop before the final database attempt query. Service, launcher/worker, worker-count, PostgreSQL, port, model-immutability and log checks continue after another cleanup operation fails. A cleanup error sets `clean_return_verified=false`, `lease_returned=false` and `returned_utc=null`; `receipt_utc` records observation time regardless of lease state; query failure reports `model_attempts_executed=null`; scrub failure reports `logs_scrubbed=false`. Existing decisive directories/files are refused. Lease IDs cannot contain path separators, and explicit output into read-only Q0 is refused.
- **F12-B3:** The documented `independent_preparation_review_002_sha` key now works as a compatibility alias. Its value must identify a later accepting independent `/007`, not historical changes-requested `/002`. Live validation rejects commits lacking an actual accepted reviewer `/007` report. The sample uses explicitly synthetic identities and is rejected in live mode. Exact owner/session/branch/HEAD/product trees/digests/resources/lease window/observations remain checked.
- **F12-D4:** The actual Phase B archive/reopen path asserts both extraction API responses have boolean `workerEnabled === false`; the receipt derives its claim from that check. The CPU endpoint fixture proves `true` fails and `false` passes through the shared JavaScript guard. A real restart has not been rerun in `/006`.
- **F12-D1â€“D3:** Use `--release-commit` plus `--release-path`, and modes `live-phase-a` / `live-phase-b-reopen`. Review existence/status checks differ from ancestry of the author base; an unmerged independent review need not be an ancestor. Original `/001` Step04 did not test live disk usage, dirty worktrees or actual symlink creation as its prose implied: the current affected tests use controlled mocks for dirty/disk/reparse guards, while the decisive runner separately verified its actual clean Git state. Actual archive tables are `archive_result_projections` and `archive_projection_units`.

Native runtime release identity is exactly `owner=eld-f4-implementer`, `conversation_id=/root/product_author_continuation`, `model=native-codex-backend-unexposed`, `effort=xhigh-requested`. These identify this continuation and requested effort without asserting an unexposed backend. Root must bind the later exact executing HEAD and accepting `/007`; no release is implied by these field values.

## Verification

| Executed check / exact command | Revision / environment | Actual result | Evidence |
| --- | --- | --- | --- |
| Git HEAD/branch/origin and 12-file SHA-256/byte comparison against `git show 3bc2ba5c...:docs/coordination/WP-0012/provider-credit-handoff.json` | Inherited base `379d8c5d...`, Windows Python | All 12 match; exact unmodified checkpoint committed before edits | Checkpoint `d9de3bf1719384c8f6801d78278438a3fdde2e22` and coordinator's pinned handoff manifest |
| `python -B docs/implementation/WP-0012/eld-f4-implementer/correction-006/helpers/validate_wp0012_correction_006_cpu.py --require-clean --evidence-name evidence-02` | Frozen `4ca6bc2dfba3548c6d0dfb820594d25e9c2c9cd4`, Python3.12.10 / Node24.18.0 | PASS, 31 tests; 3/3 steps; 45.328s test suite, UTC 16:20:33â€“16:21:22 | [Summary](../../../implementation/WP-0012/eld-f4-implementer/correction-006/evidence-02/validation-summary.json), [test log](../../../implementation/WP-0012/eld-f4-implementer/correction-006/evidence-02/logs/03-old-fails-new-passes-and-guard-tests.log) |
| Runner step01 `node --check .../helpers/drive_rehearsal_edge.mjs` | Same frozen candidate | Exit0 | [Syntax log](../../../implementation/WP-0012/eld-f4-implementer/correction-006/evidence-02/logs/01-node-check-edge-driver.log) |
| Runner step02 `python -B .../helpers/run_wp0012_rehearsal.py --validate-synthetic-sample .../sample-synthetic-release.json --output .../evidence-02/synthetic-sample-validation.json` | Same frozen candidate | CPU envelope passes; live mode rejects it | [Synthetic receipt](../../../implementation/WP-0012/eld-f4-implementer/correction-006/evidence-02/synthetic-sample-validation.json) |
| `python -B docs/implementation/WP-0012/eld-f4-implementer/correction-006/helpers/build_wp0012_006_inventory.py --evidence-name evidence-02 --output-name inventory-02.json` | Same frozen candidate and completed evidence | 22 deliverable + 6 final evidence files; 3,683 preserved inherited paths; 25 relative links; no local credential leaks found | [Inventory](../../../implementation/WP-0012/eld-f4-implementer/correction-006/inventory-02.json) |
| Read-only port and owned `pg_ctl status -D <worktree>/.local/postgres-data` checks | After affected tests | All three ports empty; PostgreSQL exit3; demo entries unchanged; owned CPU children reaped | [Resource return](../../../implementation/WP-0012/eld-f4-implementer/correction-006/evidence-02/resource-return.json) |

Tests 01â€“03 execute original and corrected startup with actual short-lived CPU children; tests05â€“06 reproduce the original skipped cleanup and check corrected return/lingering-worker behavior. Tests07â€“09 cover output/key/history gates; test10 executes the JavaScript API worker-state guard against a loopback fixture. Tests11â€“26 cover the affected release, filesystem, process-identity and import boundaries. Test27 injects six separate teardown failures into the actual orchestrator and verifies remaining checks, honest receipts and explicit unreturned state; test28 proves child fallback when taskkill throws; test29 rejects a missing `/007`; test30 checks short-password scrub; test31 rejects lease-path escape and Q0 output. All real model and product service boundaries are stubbed in orchestrator fault injection.

Not rerun: unchanged .NET/Angular/product/worker suites, production database persistence, actual browser upload/OCR/restart, or model correctness. Prior `/001`, WP-0006/0008/0010 proof stays attributed to its original revisions. No fresh live or independent acceptance claim is made here.

## Review map

Review [the exact base-to-candidate diff](https://github.com/jackgumpe/eledgercare/compare/379d8c5d607fd248d7f272e412b4ed4a97bc64f6...4ca6bc2dfba3548c6d0dfb820594d25e9c2c9cd4), [corrected Python helper](../../../implementation/WP-0012/eld-f4-implementer/correction-006/helpers/run_wp0012_rehearsal.py), [browser helper](../../../implementation/WP-0012/eld-f4-implementer/correction-006/helpers/drive_rehearsal_edge.mjs), [affected CPU tests](../../../implementation/WP-0012/eld-f4-implementer/correction-006/helpers/validate_wp0012_correction_006_cpu.py), [runbook](../../../implementation/WP-0012/eld-f4-implementer/correction-006/RUNBOOK.md), and the pinned evidence above. Original independent findings remain at [the `/002` audit](../../../reviews/WP-0012/eld-f4-reviewer/author-001-review/AUTHOR-001-AUDIT-AND-GUARD-RECONCILIATION.md).

## Risks, disagreements, and unfinished work

The original Carbon pre-freeze run failed with three mock-scoping errors and two failures, including short-secret over-redaction. Its log is immutable. Native continuation corrected the remaining short-secret omission, exception-sensitive cleanup, absent-report acceptance, stale runtime identity and evidence-deletion behavior before freeze. The first frozen author suite passed but missed the unconditional return timestamp; the independent probe reproduced seven unclean receipts with that ambiguity. Final source corrects it and the affected assertions now test both returned and unreturned states. A separate native documentation-edit command encountered a Windows cp1252 decode error after its code changes; intermediate `56d87ffee753708ec7689d8c1d786ef75f8952a6` was not executed. The traceback is retained, UTF-8 text and stale runbook attribution were repaired forward, and final `4ca6bc2...` was frozen before the second run. There was no failed native decisive suite run; successful preliminary runs are explicitly non-decisive. The passing source has no author-known unresolved finding within the released correction, but still requires independent `/007` review.

CPU fakes demonstrate helper control flow, not actual OCR or operating-system GPU isolation. A host crash, forced interpreter termination, or unwritable output filesystem cannot guarantee a receipt; absence or `clean_return_verified=false` never returns a lease. Library offline flags remain distinct from unverified OS outbound denial. Accepted application/worker/fixture trees and all R&D are unchanged.

## Handoff

Root should route exact candidate `4ca6bc2dfba3548c6d0dfb820594d25e9c2c9cd4` and evidence `c801f5920dd06f083ccf8ff3554d998317435dca` plus this report to independent `eld-f4-reviewer` for `/007`. Original `/002` remains changes-requested on `/001`. Live author `/003`, independent live `/004` and final coordinator `/005` stay held pending their exact gates. No user permission is pending within this correction.

Branch: `rehearsal/wp-0012-product`. The frozen candidate was pushed and exact remote branch SHA verified. Final evidence/report publication and clean-origin confirmation will be sent to the coordinator after the report-only commit; this immutable report does not claim its own publication SHA. Root alone updates shared routing and grants any later sole GPU lease.
