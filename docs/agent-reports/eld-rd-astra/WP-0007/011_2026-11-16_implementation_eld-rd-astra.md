# WP-0007 /011: preserve supervisor result through fallible finalization

- Canonical path: `docs/agent-reports/eld-rd-astra/WP-0007/011_2026-11-16_implementation_eld-rd-astra.md`.
- Reservation / exact authority: [INDEX](https://github.com/jackgumpe/eledgercare/blob/8224cf6e822c117ac3f6b90baadffd550e38f265/INDEX.md) and `docs/kickoffs/WP-0007-eld-rd-astra-finalization-response.md` at `8224cf6e822c117ac3f6b90baadffd550e38f265`.
- Category / author / publisher: implementation; eld-rd-astra, same native `/root/rd_astra`.
- Actual model / effort: inherited dispatched gpt-6-astra/high; backend checkpoint/session UUID not exposed. Earlier authorship remains; no delegated agent or other model invocation.
- Environment: native Codex shell tools; Windows PowerShell; registered CPython 3.12.10 AMD64, isolated `-I -B` CPU subprocesses.
- Timestamp: 2026-11-16T06:50:31.448475+00:00.
- Repository / branch / worktree: private jackgumpe/eledgercare; `research/wp-0007-vanilla-baseline`; `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-baseline-astra`.
- Exact clean base: `3892d9d7070adc9a25e6f0e57987ad0f73fb6527`, prior immutable /009 publication; prior source `f11fcd1141c08d49ac538858354f3b5d87277038`, tree `21de152f436f76915855421feae486342860ed92`.
- Authorized normal merge: `c18dca86da7f79bfda972178dd45cb1649514e1d`; 15 coordinator/reviewer paths, separately attributed below.
- Final source deliverable: `522f15f1f6e399c36b9c6c107fc08f51862f1fc1`; baseline tree `deae8e826f4770e880374c68e6a56c8c65b6f8a3`.
- Evidence publication: `43fac62dc5b078abb0db1637798d99102c113717`; same frozen source tree.
- Reviewed input: [consolidated R1 finding](https://github.com/jackgumpe/eledgercare/blob/6c8df2292f9982e2f1222587ac30ae3464868bec/docs/reviews/WP-0007/eld-baseline-reviewer/runtime-correction/findings.md), actual runtime source and immutable initial-results evidence at `6c8df2292f9982e2f1222587ac30ae3464868bec`; original probe evidence `19254515f7ee6b70fa36156a1035c554b6816ec0`, directory recheck `42a7c917702efe3e267998b392ef82fad50f785c`.
- Status / next owner: ready-for-review; same independent eld-baseline-reviewer reconciles unpublished /010. /004 stays held; no self-acceptance.

## Result and scope

This one bounded response addresses R1: a later filesystem/observer/record-read failure no longer prevents the supervisor from attempting its complete run-result write when that destination remains writable. The first structured diagnostic is retained, later errors retain their own stages, unavailable measurements are null with explicit status, and every planned record remains classified. The normal-success control also passes.

All **24 selected CPU tests pass** on the first frozen response candidate: 22 focused runtime/recovery/finalization tests plus two accepted guard and actual Windows job-child tests. The new full-control-flow cases exercise **13 finalization scenarios**: 12 persist results (one success and 11 failure cases), plus the distinct unwritable-destination limitation. No new test failed in this response; prior author/reviewer failures remain immutable.

No directory-race correction, recovery validation/selection, score/reference/parser/conversion, protocol/model/Q0 or original primary result changed. The original runtime failure's cause remains unproven; this response does not revise its historical evidence. No GPU/model/query/inference, held-out content or external runtime access occurred; F2's separate GPU lease was untouched.

## Implementation

Only `runtime.execute` behavior changes. A local bounded finalization guard records the stage and existing structured exception fields while preserving the first `supervisor_error`; later diagnostics go to `secondary_errors`. `finalization_errors` lists all errors arising during finalization. Existing failure classification is preserved when already set; a finalization-only error sets a failed supervisor classification.

The supervisor guards post-observer collection, worker outcome/per-call JSON reads, final free-space and directory-size measurements, and fallible cleanup observations/actions. Cleanup continues attempting the owned job close and child poll/kill/wait, even if an earlier cleanup action failed. No unrelated process is inspected for termination. Pre/during observer evidence survives a failed post collection. The already-bound executing HEAD is retained from plan creation instead of adding a fallible Git lookup during result persistence.

Malformed/non-object worker outcomes and malformed/non-object call observations are unavailable errors. Missing files remain explicitly absent rather than being confused with a successful record. An unreadable/malformed per-call record is failed with a null observation pointer and `observation_status: unavailable`; its original file is untouched. Every planned warmup/measurement remains in the run result. A worker-outcome read failure has its own status/diagnostic; valid completed call records remain distinguishable from unavailable records.

Final free/owned-byte failures produce null and `final_observation_status: unavailable`, never a successful zero. The whole run is failed if any finalization error occurs, even if inference records had completed. The exclusive run-result write is still attempted after those observations. A deleted/unwritable destination can prevent writing, and pre-run rejection before a run exists remains a separate limit; no impossible persistence guarantee or generic retry/logging framework is claimed.

## Executed verification

[checks.json](https://github.com/jackgumpe/eledgercare/blob/43fac62dc5b078abb0db1637798d99102c113717/docs/evidence/WP-0007/eld-rd-astra/finalization-response/522f15f1/checks.json) records exact argv, interpreter, exit codes, source and 17 protected identities. All shell commands used the owned worktree. Test TEMP/TMP/TMPDIR point to newly created ignored `.scratch/finalization-response/522f15f1/`; no external original runtime directory is opened.

| Command / scenario | Actual result |
| --- | --- |
| `python -I -B qualification/baseline/tests/run_runtime_checks.py` at `522f15f1f6e399c36b9c6c107fc08f51862f1fc1` | Exit 0; source was committed and worktree clean before execution. No source change after checks. |
| `python.exe -I -B qualification/baseline/tests/test_runtime_correction.py -v` | 22 tests pass, including accepted directory/recovery checks and new full-finalization scenarios. The focused import guard forbids model libraries/backend. |
| `python.exe -I -B qualification/baseline/tests/test_baseline.py CorpusReleaseTests.test_timeout_stall_storage_log_guard CorpusReleaseTests.test_worker_job_ownership_kills_only_owned_child -v` | Both pass; guard limits/floor retained and actual owned Windows job-child exits on close. Unrelated accepted scorer tests were not broadly rerun. |
| Persistent loop-and-final scan PermissionError | First supervision diagnostic retains type/message/filename/traceback/active phase; final scan becomes secondary stage `owned_bytes_after`; owned-byte result null/unavailable. Fifteen planned records /13 measured retained; active call failed. Job close once, kill once, wait once. |
| Final-only scan /post observer /final disk errors | Failed result persists. The matching stage is primary; unavailable telemetry is explicit. Completed-process cases close job once, do not kill the exited child and wait once. |
| Malformed JSON, unreadable and invalid-structure worker outcomes /call observations | All six cases persist complete planned results with correct unavailable status. Failed per-call records have null pointers and remain counted. |
| Combined failure case | Original persistent scan diagnostic stays primary; five secondary stages remain ordered: post_observers, worker_outcome, call_observation for the active warmup, free_bytes_after, owned_bytes_after. All planned denominators/cleanup retained. |
| Normal successful control | Exit 0, all 15 calls completed, no supervisor/secondary errors, final telemetry available. |
| Unwritable result destination | PermissionError propagates as the explicit persistence limit; owned close/kill/wait still occur exactly once. No false claim that a result was saved. |
| Actual unchanged Q0 heartbeat concurrency | 2,266 writes /10,757 successful scans in 3.0 seconds; no writer error and joined thread. Accelerated CPU overlap, not original failure attribution or new model execution. |
| Preservation and byte audit | All 17 protected object identities match base. Six unchanged runtime function bodies have exact source-segment SHA-256 identity. All four captured output blobs match committed size/hash. Source diff whitespace check passes. |

The complete supervisor cases use explicit doubled release/environment/observer/process resources and an owned writable scratch output. They test full orchestration and cleanup call counts, not a new actual CUDA worker. The separate real Windows job-child check and real Q0 heartbeat thread are identified separately. Structured diagnostics and case outcomes are retained in captured stdout; assertions inspect the saved JSON before temporary test directories are cleaned.

## Complete change inventory

The authorized coordinator merge imports these 15 paths, preserving their original coordinator/reviewer authorship:

| Action | Imported path |
| --- | --- |
| M | `CURRENT.md` |
| M | `INDEX.md` |
| A | `docs/coordination/WP-0006/gpu-author-release/.gitattributes` |
| A | `docs/coordination/WP-0006/gpu-author-release/README.md` |
| A | `docs/coordination/WP-0006/gpu-author-release/dispatch.json` |
| A | `docs/coordination/WP-0006/gpu-author-release/host-before.json` |
| A | `docs/coordination/WP-0006/gpu-author-release/model-before.json` |
| A | `docs/coordination/WP-0006/gpu-author-release/processes-before.json` |
| A | `docs/coordination/WP-0006/releases/author-runtime.json` |
| A | `docs/coordination/WP-0006/source-review-and-runtime-dispatch.json` |
| A | `docs/coordination/WP-0007/runtime-correction-publication-audit.json` |
| A | `docs/coordination/WP-0007/runtime-finalization-review-receipt.json` |
| A | `docs/kickoffs/WP-0006-eld-f2-author-runtime.md` |
| M | `docs/kickoffs/WP-0007-eld-baseline-reviewer-runtime-correction.md` |
| A | `docs/kickoffs/WP-0007-eld-rd-astra-finalization-response.md` |

Only these four source paths are authored in the response:

| Action | Authored path |
| --- | --- |
| M | `qualification/baseline/README.md` |
| M | `qualification/baseline/runtime.py` |
| M | `qualification/baseline/tests/run_runtime_checks.py` |
| M | `qualification/baseline/tests/test_runtime_correction.py` |

Evidence is committed afterward in these six new files:

| Action | Evidence path |
| --- | --- |
| A | `docs/evidence/WP-0007/eld-rd-astra/finalization-response/522f15f1/checks.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/finalization-response/522f15f1/reconciliation.json` |
| A | `docs/evidence/WP-0007/eld-rd-astra/finalization-response/522f15f1/test_baseline.py.stderr.txt` |
| A | `docs/evidence/WP-0007/eld-rd-astra/finalization-response/522f15f1/test_baseline.py.stdout.txt` |
| A | `docs/evidence/WP-0007/eld-rd-astra/finalization-response/522f15f1/test_runtime_correction.py.stderr.txt` |
| A | `docs/evidence/WP-0007/eld-rd-astra/finalization-response/522f15f1/test_runtime_correction.py.stdout.txt` |

This canonical /011 report is the sole later authored path. [reconciliation.json](https://github.com/jackgumpe/eledgercare/blob/43fac62dc5b078abb0db1637798d99102c113717/docs/evidence/WP-0007/eld-rd-astra/finalization-response/522f15f1/reconciliation.json) repeats the exact imported/authored inventory and preservation identities. No shared coordination file, other author's evidence/report, historical author report or original raw result was rewritten.

Protected baseline files are native.py, score.py, typed_values.py, corpus.py, mapping.json, protocol.json, winjob.py, release.py and baseline.py. Q0, evaluation, product trees, original runtime-dev evidence and earlier author reports retain their exact Git objects. Within runtime.py, `directory_size`, `guard_reason`, `worker`, `write`, `q0_imports` and `supervisor_diagnostic` source bodies are identical to /009. Only supervisor execution/finalization, focused tests/capture helper and a narrow README clarification changed.

## Handoff and remaining limits

Inspect the [exact source response](https://github.com/jackgumpe/eledgercare/compare/c18dca86da7f79bfda972178dd45cb1649514e1d...522f15f1f6e399c36b9c6c107fc08f51862f1fc1) and evidence `43fac62dc5b078abb0db1637798d99102c113717`. Same independent eld-baseline-reviewer should reconcile R1 against this source and the preserved coordinator recovery design, then publish /010 if accepted. No future review SHA is fabricated and /003-/009 history remains immutable.

No new model/GPU work, supplemental call, heldout access, dependency or external runtime write was authorized or performed. Resource/accounting failures remain failures; final telemetry is not repaired into successful values. Result-file persistence is necessarily limited by its destination remaining writable. The original returned lease remains unusable; any later execution requires /010 acceptance and a fresh exact coordinator release. Canonical /004 and final /005-/006 remain pending actual later work.

Normal owned push and exact-origin verification follow the report commit. The separate handoff supplies the report's publication SHA and remote-object confirmation; this immutable report does not claim its own SHA.
