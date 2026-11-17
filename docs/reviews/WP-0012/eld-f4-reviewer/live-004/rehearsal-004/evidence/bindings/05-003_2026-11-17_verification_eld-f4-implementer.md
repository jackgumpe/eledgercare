# WP-0012 / 003: Complete local workflow rehearsal with two real OCR attempts

- Report path: `docs/agent-reports/eld-f4-implementer/WP-0012/003_2026-11-17_verification_eld-f4-implementer.md`
- Sequence reservation: WP-0012 / 003, `eld-f4-implementer / verification`, under exact runtime authority `0815c028e706751deea13781cb0a08f8d1afc8aa` and `docs/kickoffs/WP-0012-eld-f4-implementer-live-003.md`.
- Category: verification
- Author / agent ID: `eld-f4-implementer`
- Actual model / effort: Native Codex continuation `/root/product_author_continuation`; backend and actual applied effort not exposed; requested `xhigh`. Runtime markers `native-codex-backend-unexposed / xhigh-requested`. This is not the prior Carbon session.
- Execution environment: Windows native Codex/PowerShell tools; Python `3.12.10`, Microsoft Edge `157.0.4341.60`, existing accepted local PostgreSQL/API/Angular build and read-only Q0 worker environment.
- Published by: `eld-f4-implementer`
- Timestamp: 2026-11-17T17:10:05.936862+00:00
- Repository / branch: `https://github.com/jackgumpe/eledgercare.git` / `rehearsal/wp-0012-product`
- Base revision and exact live executing HEAD: `f1b8306ef62bf1c82a9106509ce31988e94b1dab`
- Deliverable revision: accepted rehearsal helper `4ca6bc2dfba3548c6d0dfb820594d25e9c2c9cd4`; accounting-only collector freeze `269f4e722897dccf1baf19c73ab165c9cde2ad65`; evidence/inventory `5d0814a1b28117a048d6b76bfb1ec1d7a9d7358a`.
- Previous report: [WP-0012 / 006](006_2026-11-17_implementation_eld-f4-implementer.md), publication `f1b8306ef62bf1c82a9106509ce31988e94b1dab` (packet sequence order was reserved before the correction).
- Related review: independent accepting `/007`, `1851fc06f0384712a41563e80a0b45f6e43548c6`, retained as a pinned Git input in this package. Original `/002` remains changes-requested history on `/001`.
- Status: ready-for-review
- Next owner: `eld-coordinator`, then independent `eld-f4-reviewer` / 004 under a separate exact lease.

## Summary

The actual local demonstration completed with exactly two fresh browser-uploaded documents and two sequential real OCR attempts: one page, then three pages. Both attempts and both browser phases succeeded. The workflow saved source-grounded reviewed values, a separate newer draft, and two explicit unknowns; searched machine and reviewed content; reopened original page 2 and immutable review history; restarted API and PostgreSQL; and repeated the saved searches with both extraction API responses reporting `workerEnabled=false`. The attempt count remained two.

The single live helper exited 0 at `2026-11-17T16:59:53.845963+00:00`; its supervising wrapper/tool also exited 0. The original return receipt reports `completed`, `clean_return_verified=true`, `lease_returned=true`, returned at `16:59:53.811745Z`, with no lingering workers/services and author ports free. Root independently [acknowledged return at 17:02:36Z](https://github.com/jackgumpe/eledgercare/blob/8398165a1ba8ccb581af702744272aafa752698d/docs/coordination/WP-0012/author-003-after/lease-return-ack.json) before the separate CPU-only database accounting step; the original return receipt SHA-256 is `c01b2018ae1f12f7b91515ab22466e5602d377a6321b6548a53a894b5caa7837`. No third attempt, warmup, retry, source repair or additional inference occurred.

This is author runtime verification on two synthetic documents, not independent acceptance or error-free OCR. Original machine misreads remain visible and unchanged. The model read `SMFD` in the work-order parts text and a `2025` billing year in the statement; reviewed values and unknowns are separate records. No OCR/model/mapping treatment or production feature was introduced.

## Objective and acceptance criteria

Execute the already accepted complete-workflow rehearsal once under root's exact owner/session/source/input/guard binding and sole model-job lease `WP-0012-author-003-20261117T164734Z` (`16:47:34Z` to `22:47:34Z`). Validate the release first, stop at the first failure, and permit only one one-page and one three-page attempt. Preserve source, originals, raw extraction, provenance, history, prior databases, all existing reports/evidence and read-only Q0. Record actual process/tool exits and return resources before any next model owner. Publish complete evidence for independent `/004`.

## Change inventory

All additions are confined to `docs/implementation/WP-0012/eld-f4-implementer/rehearsal-003/` and this later canonical report. Product, worker, fixtures, research, shared routing and all 3713 inherited paths remain unchanged. The [collection inventory](../../../implementation/WP-0012/eld-f4-implementer/rehearsal-003/evidence/collection-inventory.json) lists every source, input, copied output and retained-only cache with exact path/bytes/SHA-256 and the relevant Git identities.

| Added path or resource | Purpose |
| --- | --- |
| `rehearsal-003/.gitattributes` | Preserve exact copied bytes in Git. |
| `rehearsal-003/helpers/collect_author003.py` | Frozen accounting-only collector: copies actual runtime/launch files, hashes external caches, preserves exact release/review inputs, snapshots database tables using read-only queries, verifies prior databases and stopped resources. No extraction or model entry point. |
| `rehearsal-003/retained-failures/collector-draft-syntax-01.py.txt` | Exact unexecuted collector draft with its pre-freeze SQL-string syntax error. |
| `rehearsal-003/retained-failures/collector-draft-syntax-01.log` | Retained syntax failure; repaired before collector freeze and before any accounting database operation. |
| `rehearsal-003/evidence/attempts/**` | Both original PDFs, exact request envelopes, output envelopes, raw UTF-8 bytes, stdout/stderr and final heartbeats. |
| `rehearsal-003/evidence/browser/**` | Both phase receipts, persisted attempt/lease-return receipt, state/provenance, API/UI/browser logs and 12 actual screenshots. |
| `rehearsal-003/evidence/launch/**` | Exact one-shot launcher, original validation/live streams, process identities, commands, UTC times, actual helper/wrapper/tool exits and retained heartbeat observations. |
| `rehearsal-003/evidence/release-inputs/**` | Exact authority JSON/kickoff, accepting independent007 report and hashed pre-release ownership/host/model observations from their Git commits. |
| `rehearsal-003/evidence/database/**` | Post-restart durable table snapshot, actual read-only accounting commands and prior-database preservation hashes. |
| `rehearsal-003/evidence/collection-inventory.json` | Complete 4 source / 54 copied artifact inventory, 56 cache descriptors retained only in the original runtime root, preservation and final resource observations. |

The evidence commit precedes this report-only publication. The report cannot contain its own publication SHA. Runtime and launch originals remain under `C:/Users/jackg/eLedgerCare-Demo/WP-0012/author` and the owned ignored `.local/wp0012-author003-20261117T164734Z`. Generated caches (56 files, 118,002,746 bytes) remain external with exact retained-only descriptors; model weights and credentials are not published. No source mutation occurred during the live invocation: executing HEAD stayed exactly `f1b8306...` until its actual exit. Accounting commits were made afterward.

## Decisions and actual results

| Document / real attempt | Input and output | Actual observation |
| --- | --- | --- |
| `SYN-WO-01-v1-raster300.pdf`, 1 page; attempt `01a1ea6a-6642-7939-8407-e2aba617b795` | Original SHA-256 `47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd`; raw 3,236 bytes, SHA-256 `7503761ae46afef6adf579881d011764283474354fac3e185598fc7d266aff95` | Completed, worker exit0. Browser extraction wall 193.899s; worker total 190.336s, load12.889s/render0.260s/infer152.114s. Saved Reviewed revision1, then distinct Draft revision2. |
| `SYN-MP-01-v0-clean.pdf`, 3 pages; attempt `01a1ea6d-6dbe-724c-beaf-43d820d11048` | Original SHA-256 `15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3`; raw 7,511 bytes, SHA-256 `c399ad892e257500e2b6a9ac8b0bc3d8a17e9c10041262c4bca6a48fb9b9b639` | Completed, worker exit0. Browser extraction wall347.019s; worker total344.622s, load11.869s/render0.316s/infer321.438s. Saved Reviewed revision1 with Work Order ID and Requested Date explicitly unknown. |

Both calls used unmodified `baidu/Unlimited-OCR-2` revision `0480966938291445591f69f08a13b041c073a96a`, manifest `0df07bc60abf6937c917040bced32afabd7e4d11bafc0bd99902abca610a81be`, dependency lock `582071bf20eaca1836c3d1cef21d31cbdaa1e1407184033a918a40612c128111`, worker source `c1c324c36e27f57c3c4ac4a1462984fbe586ad43ab82af3a2883bb7eac4c0d54` and page-specific released configurations. Renderer provenance is `pypdfium2==5.15.2;pdfium=159.0.8149.0;dpi=300;rgb`; `torchvision-local-sha256-TOFU` remains explicitly disclosed. Both finish reasons were `stop`.

Before and after the actual API/PostgreSQL restart, saved-query canonical SHA-256 was `82d194c58fdceefa12ddc177f8f615dd5f5c2fbc94ad3bca7b6bddc0add85abe`; archive browse counts were two in all/machine/reviewed modes. The matching source-page and historical-review routes reopened. The newer draft remained distinct from the earlier reviewed revision; the two statement unknowns remained explicit. Phase B checked actual API booleans false for both documents, unchanged raw/original identities and unchanged attempts. Scripted browser edits were source-grounded synthetic demonstration actions, not customer approval or authenticated human sign-off.

Twelve actual screenshots are retained. The author visually inspected the first extracted-original/review-draft screens and all four post-restart archive/source-page/history/unknown screens. Original PDFs and raw bytes were also compared directly with fixture/API hashes. Browser checks reported zero storage writes. Peak sampled working sets were API196.14MiB and worker5494.93MiB; these are single-host observations, not throughput or memory guarantees.

## Verification

All live commands ran in `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-f4-implementer` at exact clean HEAD `f1b8306ef62bf1c82a9106509ce31988e94b1dab`. Let H be `docs/implementation/WP-0012/eld-f4-implementer/correction-006/helpers/run_wp0012_rehearsal.py`.

| Executed command / operation | Actual result | Evidence |
| --- | --- | --- |
| `python -B H --validate-release --release-commit 0815c028e706751deea13781cb0a08f8d1afc8aa --release-path docs/coordination/WP-0012/releases/author-003.json` | Exit0; `16:49:29.139035Z` to `16:49:30.363574Z`. | [Launch receipt](../../../implementation/WP-0012/eld-f4-implementer/rehearsal-003/evidence/launch/launcher-receipt.json), original validation stdout/stderr. |
| Same command with `--execute-live`, invoked once by retained `launch_once.py` | Exit0; `16:49:30.364083Z` to `16:59:53.845963Z`; exactly two completed attempts and no retry. Wrapper/tool exit0, session96125 final chunk8e987d. | [Tool completion](../../../implementation/WP-0012/eld-f4-implementer/rehearsal-003/evidence/launch/tool-completion.json), [phase A](../../../implementation/WP-0012/eld-f4-implementer/rehearsal-003/evidence/browser/phase-a-live-browser.json), original live streams. |
| Actual API and PostgreSQL stop/restart plus `live-phase-b-reopen` | Exit0, actual workerEnabled false for both; saved-query digest and attempts unchanged. | [Phase B](../../../implementation/WP-0012/eld-f4-implementer/rehearsal-003/evidence/browser/phase-b-disabled-ocr-reopen.json), before/after screenshots and service logs. |
| Full runtime cleanup / model-file verification | Returned=true, clean=true; zero workers, no lingering process identities, all author ports empty, all18 Q0 objects verified; no log scrub mutation required. | [Original owner return](../../../implementation/WP-0012/eld-f4-implementer/rehearsal-003/evidence/browser/owner-lease-return.json). |
| `python -B docs/implementation/WP-0012/eld-f4-implementer/rehearsal-003/helpers/collect_author003.py` | Accounting-only, frozen collector269f4e7; copies/hashes complete original evidence, read-only PostgreSQL snapshots, preserved prior databases and stopped final resources. | [Collection inventory](../../../implementation/WP-0012/eld-f4-implementer/rehearsal-003/evidence/collection-inventory.json), [durable tables](../../../implementation/WP-0012/eld-f4-implementer/rehearsal-003/evidence/database/author-post-restart-tables.json), [preservation](../../../implementation/WP-0012/eld-f4-implementer/rehearsal-003/evidence/database/retained-database-preservation.json). |

Read-only accounting observed 2 documents, 2 attempts/results/originals/jobs/heads, 3 review revisions, 15 review-field rows, 2 archive projections and 4 projection units, plus 4 migration records. Retained F4 seed digest remains `76e7970b50b8fbf968c44e534d6383bdd8251e9f285e2373ea026eeeea157085`; migrated core `ad4f44bcf7c0f7163e91cad81f569bfc4642cbb167c1eaf6c3d1ab9984b2e6d0`, projections `78f0f273dbdb48629924752cba6f863f11f62764e27161d8df1549ad75ce2ac3`. Prior database contents retain their accepted canonical hashes. Only the prepared author rehearsal database gained the demonstration data.

Not run: broad unchanged application suites, research evaluation, extra model calls, independent reviewer reproduction or deployment. Independent `/004` requires its own exact source/input/runtime release after root accepts this author evidence and returned resources.

## Review map

Inspect the [exact base-to-accounting diff](https://github.com/jackgumpe/eledgercare/compare/f1b8306ef62bf1c82a9106509ce31988e94b1dab...269f4e722897dccf1baf19c73ab165c9cde2ad65), [frozen collector](../../../implementation/WP-0012/eld-f4-implementer/rehearsal-003/helpers/collect_author003.py), actual phase/return/launch receipts and full inventory above. The inventory excludes its own recursive hash; its Git blob is bound by the evidence commit. Pinned report/kickoff input copies preserve their original bytes and relative links: resolve those links at the recorded original Git commit/path, not the copy's evidence directory. Screenshots are the actual captured PNG files, without editing.

## Risks, disagreements, and unfinished work

There was no failed live attempt or runtime retry. The only new preparation failure was an unexecuted accounting collector draft's SQL quoting SyntaxError, retained with its exact source, repaired before freeze. No model or database action was triggered by that draft. Earlier `/001`, `/002`, `/006` and `/007` findings, failed evidence and authorship remain immutable.

The original CPU `/006` report has nonblocking timing/encoding prose discrepancies recorded in independent `/007`; the actual final CPU evidence is31 tests in45.760s at `16:34:21.893958Z` to `16:35:11.659367Z`. This report does not rewrite that historical publication. Actual live timing above comes from retained runtime receipts.

Synthetic, local, two-document results do not establish production reliability or general accuracy. Original OCR mistakes remain. Library offline settings do not prove OS outbound denial; desktop/WDDM sharing remained, and no hardware-exclusivity claim is made. No feature, model or mapper change, customer data, training, deployment or production research import is released.

## Handoff

Root should verify this actual runtime evidence and then route independent `/004` under a separate exact lease. Author lease `WP-0012-author-003-20261117T164734Z` is returned and acknowledged; no further author inference is authorized. Owned services are stopped after accounting. Source and evidence publication identities are above; the immutable report publication SHA and exact remote/clean receipt will be sent after its report-only commit. Root alone changes shared routing or releases another model owner.
