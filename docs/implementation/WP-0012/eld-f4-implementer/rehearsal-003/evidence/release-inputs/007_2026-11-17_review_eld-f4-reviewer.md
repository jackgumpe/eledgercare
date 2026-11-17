# WP-0012 / 007: Independent acceptance of corrected CPU rehearsal preparation

- Report path: `docs/agent-reports/eld-f4-reviewer/WP-0012/007_2026-11-17_review_eld-f4-reviewer.md`
- Sequence reservation: WP-0012 / 007 in `INDEX.md` at handoff authority `3bc2ba5cf5db6698d71c99fccc957e54936fb6c2`; final review release `a728d6dc6d4e44c404ea6c1703cfb0a890e0b766`.
- Category: review
- Author / agent ID: `eld-f4-reviewer`
- Actual model / effort: Native Codex continuation `/root/product_reviewer_continuation`; requested xhigh, actual backend/applied effort not exposed. Original partial reviewer work: Carbon `gemini-4-carbon-high/high`, conversation `61105d43-7706-45f2-9176-69d3256248e0`.
- Execution environment: Windows PowerShell/native Codex tools, owned worktree `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-f4-reviewer`; Python CPU subprocesses and Node HTTP guard execution.
- Published by: `eld-f4-reviewer`, native continuation
- Timestamp: 2026-11-17T16:41:04Z
- Repository / branch: `https://github.com/jackgumpe/eledgercare.git` / `review/wp-0012-product-rehearsal`
- Base revision: `379d8c5d607fd248d7f272e412b4ed4a97bc64f6`
- Deliverable revision: independent audit `c5aed9325662b769f3d074972bdb6d50ddcb8ed1`; final inventory metadata `f7500d2b5ca2c2fc48363b8275a29ab7bb69b980`
- Reviewed source: `4ca6bc2dfba3548c6d0dfb820594d25e9c2c9cd4`; author /006 publication `f1b8306ef62bf1c82a9106509ce31988e94b1dab`; author final evidence `c801f5920dd06f083ccf8ff3554d998317435dca`
- Previous report: [Independent /002](002_2026-11-17_review_eld-f4-reviewer.md), immutable changes-requested disposition on original /001.
- Related report: [Author /006](../../eld-f4-implementer/WP-0012/006_2026-11-17_implementation_eld-f4-implementer.md).
- Status: accepted
- Next owner: `eld-coordinator`; exact author /003 runtime release remains a separate gate.

## Summary

Accepted for the authorized CPU preparation correction. Independent source inspection and focused execution resolve F12-B1/B2/B3 and D4, with D1–D3 prose reconciled. No reviewed author source was written by this reviewer. Accepted application, worker and fixture identities remain unchanged. This is not live OCR or end-to-end runtime acceptance.

The first frozen author candidate still timestamped failed cleanup as returned. Independent execution reproduced that ambiguity in seven cleanup-failure paths; root assigned the author a narrow forward correction. The same frozen probe passes the corrected source: failed cleanup explicitly reports `lease_returned=false`, `returned_utc=null`, while `receipt_utc` records observation time. Original adverse evidence remains intact.

## Objective and acceptance criteria

Independently verify atomic startup cleanup, all-exit audit/scrub/return, first-failure stop with zero retries, no reused evidence, exact release/source/review guards, and actual API disabled-worker assertions. Preserve original /001, changes-requested /002, prior databases, Carbon partial work and failures. Runtime /003, independent /004 and coordinator /005 remain separate gates.

## Change inventory

[The final inventory](../../../reviews/WP-0012/eld-f4-reviewer/correction-006-review/final/final-inventory.json) enumerates every exact path and hash: 26 reviewer deliverable paths under `docs/reviews/WP-0012/eld-f4-reviewer/correction-006-review/`, plus 30 unchanged author input paths introduced by exact product-author merges. It verifies 78 artifact/input identities, 53 relative links, all 22 bound source paths and all 3,683 inherited paths. Metadata committed afterward is `final/final-inventory.json` and this report. Shared routing was not edited; root's combined R&D branch was not merged.

Reviewer additions comprise the three untouched Carbon partial files; attributed preparation/audit notes; native v5 runtime helper and focused probes; retained failed/passing preliminary evidence; both candidate return/guard observations; the old-control limitation note; source/input/output inventories. [The complete audit](../../../reviews/WP-0012/eld-f4-reviewer/correction-006-review/FINAL-INDEPENDENT-AUDIT.md) maps each change and finding.

External effects were owned benign CPU children, temporary files and ephemeral loopback HTTP. Old leaked test children were reaped by the harness; corrected startup exited its children and closed handles before raising. No product service or database was started. Final reviewer ports 5690/4710/55439 were empty, owned PostgreSQL status exited 3, and reviewer runtime runs remained empty.

## Verification

Commands below use prefix `R = docs/reviews/WP-0012/eld-f4-reviewer/correction-006-review`.

| Executed check | Exact source / execution | Actual result and evidence |
| --- | --- | --- |
| `python -B R/helpers/probe_native_preparation_cpu.py --output-dir R/preliminary/native-attempt-02` | Frozen reviewer `66b7144722036e4280003e2f1330d5e3c586735c` | 22 tests passed, including reviewer missing-report/return-proof/native-identity/cleanup guards. [Log](../../../reviews/WP-0012/eld-f4-reviewer/correction-006-review/preliminary/native-attempt-02/tests.log). |
| `python -B R/helpers/probe_bound_006_return_semantics.py --candidate-commit 4ca6bc2dfba3548c6d0dfb820594d25e9c2c9cd4 --output-dir R/final/candidate-4ca6bc2d-return-02` | Probe frozen `24b19113715dbc3f4ec5672525de9236783285c5`, executing merge `c2a695c596d07772e01dc8603dce09b639209da2` | Exit 0. Eight new-candidate first-failure scenarios, seven explicitly unreturned cleanup failures, zero retries. [Receipts](../../../reviews/WP-0012/eld-f4-reviewer/correction-006-review/final/candidate-4ca6bc2d-return-02/return-probe.json). |
| `python -B R/helpers/probe_bound_006_guards_cpu.py --candidate-commit 4ca6bc2dfba3548c6d0dfb820594d25e9c2c9cd4 --output-dir R/final/candidate-4ca6bc2d-guards-02` | Probe frozen `0e3069737b49d3d61a8e23421d11b519f04ce376`, executing `4053da3a8fded97ef751f937eed978922b73874f` | Exit 0. Four startup old-fails/new-passes cases; 13 release-key controls and 25 rejection cases; output-preservation controls; six actual JavaScript API boolean cases; corrected old first-browser-failure control. [Results](../../../reviews/WP-0012/eld-f4-reviewer/correction-006-review/final/candidate-4ca6bc2d-guards-02/guards.json). |
| `python -B R/helpers/build_native_007_inventory.py --source-commit 4ca6bc2dfba3548c6d0dfb820594d25e9c2c9cd4 --author-publication f1b8306ef62bf1c82a9106509ce31988e94b1dab --output R/final/final-inventory.json` | Frozen auditor `fc26739814139b664ada86d217c377e5bf78919c`, executing audit `c5aed9325662b769f3d074972bdb6d50ddcb8ed1` | Exit 0; exact source/evidence/input preservation, link/credential checks and actual idle resource observations. |

The unchanged return probe's old-version control hits a temporary-directory setup failure before a browser call in both runs. It is **not** old-browser-failure proof. The separate guard probe corrects only that harness setup and records an actual old browser failure with no receipt. [The limitation and retraction](../../../reviews/WP-0012/eld-f4-reviewer/correction-006-review/final/CONTROL-LIMITATION.md) and original bytes remain. Prior /002 also contains valid original failure proof.

Author evidence was inspected, not rerun as independent proof: final evidence-02 records 31 tests in **45.760 seconds**, UTC `16:34:21.893958`–`16:35:11.659367`, on exact `4ca6bc2d...`. Immutable /006's verification table accidentally repeats first-run timings; this report records the actual final timing. Some dash prose in /006 is misencoded. These are nonblocking metadata discrepancies, not source failures.

Not run: model/renderer execution, GPU query/inference, actual upload/OCR/browser restart, PostgreSQL persistence, broad unchanged product suites, or research-content work. CPU simulations establish helper behavior only.

## Decisions, review map and unfinished work

See [the independent audit](../../../reviews/WP-0012/eld-f4-reviewer/correction-006-review/FINAL-INDEPENDENT-AUDIT.md) and [exact reviewed diff](https://github.com/jackgumpe/eledgercare/compare/379d8c5d607fd248d7f272e412b4ed4a97bc64f6...4ca6bc2dfba3548c6d0dfb820594d25e9c2c9cd4). No substantive correction finding remains open on final source.

Carbon partial reviewer authorship is preserved unchanged at `8729db9323e4d2945a30d525b0d67e5ad2a1692e`; its low-credit provider ERROR/wrapper exit 3 is not success. Native preliminary attempt01 failed a tuple-versus-string test assertion; its retained result and separate correction precede passing attempt02. First candidate adverse return evidence remains. The earlier candidate guard wrapper exit was not captured by tool forwarding; its passing artifact is retained without a numeric exit claim. Both final candidate command exits were observed directly as 0.

Reviewer-authored v5 preserves v3/v4 and requires exact native identity, an actual accepting /007 report and substantive hashed author-return proof. Its CPU tests are own-helper verification; root must inspect it before /004. Later `accepted_preparation_review` must identify this accepting /007 publication, never relabel historical /002. Root must semantically accept actual author /003 and observe returned resources before issuing the independent /004 lease. Missing/unverified receipts do not return a lease.

## Handoff

Root may route the accepted corrected preparation toward its separately bound runtime /003. No live lease is granted by this review. Own future runtime identity: `owner=eld-f4-reviewer`, `conversation_id=/root/product_reviewer_continuation`, `model=native-codex-backend-unexposed`, `effort=xhigh-requested`.

Branch `review/wp-0012-product-rehearsal`; audit deliverable `c5aed9325662b769f3d074972bdb6d50ddcb8ed1`; inventory metadata `f7500d2b5ca2c2fc48363b8275a29ab7bb69b980`. The report publication SHA and exact-origin receipt will be sent separately after the report-only commit. This report cannot contain its own publication SHA. Root alone writes shared routing.
