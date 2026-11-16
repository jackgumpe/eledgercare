# WP-0006 /005: accepted F2 integration verification

- Report path: `docs/agent-reports/eld-coordinator/WP-0006/005_2026-11-16_verification_eld-coordinator.md`.
- Reservation: WP-0006 /005 in [INDEX at runtime authority](https://github.com/jackgumpe/eledgercare/blob/513da1a18c9b80ed99d56dd1ff7bf3bc1cb77905/INDEX.md).
- Category: verification.
- Author / publisher: `eld-coordinator`, session `01a1d895-c605-7ab2-b7ec-c3159c0634ba`.
- Actual model / effort: not independently exposed. Fresh delegated Codex continuation explicitly requested xhigh per Jack; Carbon sessions retained their separately assigned model/effort.
- Environment: native Codex tools, Windows / PowerShell, Git, CPython3.12.10 for read-only evidence audits.
- Timestamp: 2026-11-16T18:06:25.710696+00:00.
- Repository / branch / worktree: private `https://github.com/jackgumpe/eledgercare`; `coordination/bootstrap`; `C:/Users/jackg/Asp.net Projects/eledgercare`.
- Original authorized two-track base: `8e80a42c29c0fc27a4af6348cfb1ec22cab3764d`.
- Frozen integrated deliverable: **`0a2a2914e2dee652b072a4a0029b3c3156b36254`**.
- Subsequent complete inventory/preservation evidence commit: **`e6c4e35e25732bb7b17924d484d30055fbd585ae`**.
- Status: **accepted, integrated; canonical coordinator publication**. Next owner: Jack for selection of any subsequent bounded milestone; no execution/review/integration gate remains for these tracks.
- Previous coordinator report: WP-0006 /001 design; independently accepted by /002 `e2452e1ab3d8937868c07ffb30ce430715b5be78`.
- Reviewed source: `8a73b7a5dab51e3ccf803aceedded4929529dd35`; independent source reconciliation `82e8f732afbf038bfb5b6c560f1b1219aaa4e40f`.
- Author /003: `3ece293f4ea9b78f19dbfb7f95472b95d091d79e`; completion evidence `88f24fb2f08eeaa773d330ab0d8b1e7c74037d8f`.
- Independent /004: **`c854a1d4c306c3b10d78df42a1a2552a06bb4a98`**; final runtime evidence **`7f0ec3a9338606ce54c4c6d2eeabab8a2c245e2a`**.

## Outcome and acceptance

Accept F2, “Extract a submitted maintenance document and reopen its saved result,” within the authorized local synthetic one-to-three-page profile. The [final disposition and F2-01..07 evidence map](../../../coordination/WP-0006/final-disposition/README.md) records the complete outcome, exact revisions, actual document/attempt/result identities and limits. Product code is implemented by the assigned author and reviewed by a separate Carbon conversation; the coordinator authored no product implementation. The qualification/baseline harness remains separate from production imports.

Actual independent execution on clean `b343f6ff78aa41332ecbe957577b6776f8edc22f`, frozen helper `694f4b61294aa1b489fb0a486cd328bdc61643aa`, under authority `513da1a18c9b80ed99d56dd1ff7bf3bc1cb77905` completed four intended scenarios: raster extraction, three-page extraction, live supervisor interruption with child cleanup and explicit retry, then API/PostgreSQL restart and disabled-OCR saved-result Edge reopen. This comprises **three completed extractions and one deliberate interruption**, with four durable attempts and three saved results.

## Verification and review map

| Executed check / executor | Actual result / evidence |
| --- | --- |
| Independent source regression and actual boundary probes | 74 .NET tests (including20 real-PostgreSQL acceptance), nine Python tests, actual child/NTFS/storage/diagnostic probes passed on8a73; ten unchanged Edge regression cases retained with exact UI tree proof. [Source acceptance audit](../../../coordination/WP-0006/source-reconciliation-acceptance-audit.json). |
| Independent genuine runtime / Carbon reviewer | All four planned scenarios passed; actual-model browser output, ordered pages, raw/provenance/original integrity, no automatic retry, retained interrupted history, saved results with OCR disabled. [Runtime evidence](../../../reviews/WP-0006/eld-next-reviewer/runtime-execution/trial-summary-reviewer-v2.json). |
| Coordinator original/publication audit | Every inventory capture matches original bytes; directly read completed original native raw/envelope files and matched PostgreSQL/API/Edge digests for all three results; exact source/protected identities and report-only publication verified. [Audit](../../../coordination/WP-0006/reviewer-runtime-publication-audit.json). |
| Coordinator fresh model/notice and process cleanup | `python -I -B qualification/q0/harness/q0.py verify-model <pinned-model-dir> --notices <pinned-notice-dir>` exit0,18 objects/notice unchanged; actual model/service PIDs and all owned ports absent. [Returned lease](../../../coordination/WP-0006/gpu-reviewer-release/lease-return.json), [service observation](../../../coordination/WP-0006/gpu-reviewer-release/service-exit-observation.json). |
| Coordinator final integration preservation | CPU/Git audit on frozen deliverable verifies complete inventory and exact accepted product/baseline/protected identities. Linked combined inventory. |

The read-only coordinator audit helper was `.scratch/dispatch/audit-f2-reviewer-final.py --evidence 7f0ec3a9338606ce54c4c6d2eeabab8a2c245e2a --report c854a1d4c306c3b10d78df42a1a2552a06bb4a98 --output docs/coordination/WP-0006/reviewer-runtime-publication-audit.json`. Final preservation used `.scratch/dispatch/final-preservation-audit.py --deliverable 0a2a2914e2dee652b072a4a0029b3c3156b36254 --product-candidate 8a73b7a5dab51e3ccf803aceedded4929529dd35 --baseline-candidate 522f15f1f6e399c36b9c6c107fc08f51862f1fc1 --output docs/coordination/final-two-track-preservation.json`. Both exit0. Coordinator did not rerun unchanged accepted suites or make additional model calls; no changed source required repetition.

## Complete inventory and preservation

The [combined exact base-to-deliverable inventory](../../../coordination/final-two-track-preservation.json) accounts for all **1192** changed paths, with action, Git object, byte length and SHA256. It intentionally covers both concurrently authorized packets and their coordinator metadata; linked packet dispositions identify each workstream. All **34** original report-guide/template/report files retain exact identity. Protected Q0, evaluation corpus, research, supplied inputs and F1 design trees match the original base. Product `src`, `tests`, `workers`, `web`, `deploy` and solution objects match accepted8a73 exactly; baseline source tree matches accepted522f exactly.

The inventory and [final independent publication receipt](../../../coordination/WP-0006/reviewer-final-publication-receipt.json) are the two subsequent evidence metadata files at `e6c4e35e25732bb7b17924d484d30055fbd585ae`. The receipt verifies all five exact remote refs and the completed reviewer CLI SUCCESS/exit0. This report and the companion coordinator final report are later report-only metadata, followed by shared INDEX/CURRENT publication receipts. None claims its own publication SHA. Original author/reviewer reports and failures remain immutable.

## Corrections, resources and limits

Original source/import and runtime failures remain recorded. The author's corrected runtime retained a failed final browser assertion caused by its expected label “Interrupted”; actual UI was “Extraction interrupted.” A separate CPU-only supplement verified the same saved results with OCR disabled, with its helper setup failures also retained. The independent final run used frozen corrected expectations and passed without product changes.

Immutable author /003 incorrectly states CUDA12.8 / torchvision0.23.0+cu128. Actual pinned packages are **torch2.13.0+cu130 / torchvision0.28.0+cu130**. No environment change occurred. Three completions plus one intended interruption must not be described as four completed extractions. Observed equal raw outputs/retry bytes do not establish general determinism or accuracy.

Author/reviewer isolated PostgreSQL databases, stopped clusters and runtime directories under `C:/Users/jackg/eLedgerCare-F2/WP-0006/` remain retained. Author ports5190/4210/55434 and reviewer5290/4310/55435 are closed. All leases are explicitly returned and acknowledged. Existing Q0 model/venv/notice remained read-only. The restart was a clean PostgreSQL fast restart, not power-loss verification. Unreviewed output, synthetic-only scope and local torchvision TOFU provenance limits remain explicit. No F3/F4, E1-E3, customer data, training, deployment or legacy migration is released.

## Publication and handoff

Author and independent reviewer commits were normally merged without rewriting attribution. Their exact remote refs were verified before acceptance. This report is committed after the frozen deliverable and audit evidence; exact origin confirmation and its publication SHA are recorded afterward in INDEX/CURRENT. No work remains within WP-0006 acceptance; selecting a subsequent feature is a separate decision.
