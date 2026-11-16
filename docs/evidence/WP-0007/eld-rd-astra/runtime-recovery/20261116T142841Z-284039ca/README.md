# Supplemental recovery checkpoint: runtime complete, exact-credit gate rejected output

Author eld-rd-astra, same native /root/rd_astra; inherited dispatched gpt-6-astra/high, backend checkpoint/session UUID unexposed. Timestamp 2026-11-16T14:45:50.107154+00:00. This is a separately labeled one-document supplement, not a replacement primary result or canonical WP-0007 /004.

- Owned branch/worktree: research/wp-0007-vanilla-baseline; `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-baseline-astra`.
- Exact executing clean HEAD: `b4ed262c6916a548b65c57df119d809847421ab2`; frozen source `522f15f1f6e399c36b9c6c107fc08f51862f1fc1`; tree `deae8e826f4770e880374c68e6a56c8c65b6f8a3`.
- Accepted independent /010: `b9dc09fa3dc6838c59f519063bb38d2c2a7f44f0`.
- Exact coordinator authority: `934d6a204bea0a61eb30c33a395b5c616dd00063`; kickoff `docs/kickoffs/WP-0007-eld-rd-astra-dev-recovery.md`; release `docs/coordination/WP-0007/releases/author-dev-recovery.json`.
- Evidence commit: `414b24d7a1752698fc9bb3bd95e06715b8ebb677` (54 new files: 53 byte-identical copies plus capture.json). This subsequent README is metadata only.
- New run: `C:\Users\jackg\eLedgerCare-Baseline\WP-0007\author\runs\author\20261116T142841Z-284039ca`.
- Sole lease: `WP-0007-author-recovery-20261116T142729Z`; GPU UUID GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d.

## Runtime outcome and immutable lineage

The local full read_release check passed at the exact clean HEAD, all three coordinator observation Git-byte digests matched, and no previous baseline worker was observed. Exactly one cold-load session ran: two excluded dev warmups, then only SYN-MP-01-v2-skew-pos4deg as measured. All three calls completed; supervisor/worker exit 0, no failure or primary/secondary finalization error, every final observation available. Elapsed session 777.281s. No retry, successful-measurement replay, heldout input or source/model/library/protocol/scorer change occurred.

The release and [scores.json](scores.json) retain exact supplemental_recovery lineage to original evidence `1d6a681f09b0eaf233f838c54465c36a042ec326`, run20261116T051059Z-eda73dc6 and authority `a6f8f2a17fc8f3db68e11d2971423f78b2dc7861`. Exact failed-record digest/matrix/state validation ran before execution. Original primary13 scores remain byte-identical with SHA-256 **8cc924888baf65ebcb3ee867891402ede6dd0b0224768c6931592a9a3cce710e**, including the original failed document's zero credit. The supplement does not enter those aggregates or replace that row. Later primary corpus aggregation must use original dev plus separately released heldout, with the runtime revision boundary disclosed.

## Separate supplemental score

Scoring ran once with the same authority, clean executing HEAD, parser/mapping/reference/printed/typed functions and exactly one expected measured document. Its scope is explicitly `supplemental_single_failed_dev; does not replace original primary scores`.

Runtime completion is distinct from score eligibility: native page-three markup contains `rowspan="2"`, which the frozen table grammar does not support. The retained diagnostic is **page_3:table:unsupported_span**. Therefore all exact-credit metrics receive zero under the existing whole-document parse-validity gate; no grammar repair or result-driven tuning was applied.

| Supplemental metric | Credited /expected |
| --- | ---: |
| Printed fields | 0/15 |
| Printed cells | 0/180 |
| Typed normalized fields | 0/15 |
| Typed normalized cells | 0/180 |
| Rows | 0/20 |
| Expected absence | 0/1 |
| Page-count decision | 0/1 |
| Page sentinels | 0/3 |
| Adjacencies | 0/2 |
| Cross-page links | 0/5 |

The output still has 7/15 mapped field candidates and 72/180 mapped cells; 5 field and 70 cell comparisons are observed exact but explicitly uncredited. These are diagnostic comparisons, not a replacement accuracy metric. Twelve expected rows remain unsupported/missing, 35 content records unclassified, three field candidates unmatched; unmapped physical table coverage is 23 rows/110 cells. Field/cell errors combine parsing, mapping and recognition; zero credit does not mean zero readable characters. Raw token sequence diagnostics remain separate: 687 reference/636 prediction tokens, 48 substitutions, 91 deletions, 40 insertions, rate0.2605531295 using frozen SequenceMatcher alignment, not minimum-Levenshtein WER. Unsupported markup retained as diagnostics also limits a pure reading-error interpretation.

Measured raw output is 7,434 bytes, lossless/untruncated, SHA-256 **8515081c860b655d5ab1c344d141b21c88d69f0baf8dd7fe22e7dd214a5496a0**. Raw/native observation, token IDs, rendered RGB digests, timings/memory and all score details remain retained unchanged. All three completed observations have empty flags/no error and the expected triton_import_failed_dense_fallback path.

Measured external synchronized call time is285.7435537s; native generate total285.4755437s, native prefill-to-first-token0.4885721s, derived decode284.9869716s. Warmups are excluded from supplemental accuracy and measurement summaries. F2 CPU source work can contend for CPU/RAM, and desktop WDDM remains active; these uncontrolled confounders prevent controlled-performance, causal improvement or distribution claims from this single supplemental attempt.

## Ownership, verification and lease return

| Role | PID /parent | Creation UTC |
| --- | --- | --- |
| Host supervisor | 15196 /21152 | 2026-11-16T14:28:40.7551340Z |
| Venv launcher | 11928 /15196 | 2026-11-16T14:28:41.4754800Z |
| Actual worker | 10396 /11928 | 2026-11-16T14:28:41.5057420Z |

[Start receipt](author-process-start.json) preserves exact executable/command identity. After successful execution, all three PIDs were absent. Scoring completed exit0 while clean HEAD and release remained valid. A read-only post-run invocation of accepted Q0 verify_model_dir/verify_notices verified all **18 model objects and one notice** against the unchanged manifest; [model-after record](author-model-after.json) retains results. No model import/inference occurred during that verification.

The [exit/lease receipt](author-process-exit-and-lease-return.json) records all three PIDs absent again, execute/score/model verification exit0, original clean HEAD and explicit lease return at **2026-11-16T14:42:18.9420168Z**. This was immediately sent to the coordinator. No further model work remains under this lease. Run-end recorded owner usage125,286,703 bytes and C: free51,577,647,104 bytes; these include the preserved earlier owner state and are not presented as isolated model-memory values.

## Commands and byte-preserving publication

Registered CPython3.12.10 host interpreter launched the unchanged isolated venv worker. Every shell command used the owned worktree. No root merge/source commit occurred before execution/scoring completed.

```powershell
& 'C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe' -I -B qualification/baseline/baseline.py execute --authority 934d6a204bea0a61eb30c33a395b5c616dd00063 --release-path docs/coordination/WP-0007/releases/author-dev-recovery.json --split dev --owner author

& 'C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe' -I -B qualification/baseline/baseline.py score-run --authority 934d6a204bea0a61eb30c33a395b5c616dd00063 --release-path docs/coordination/WP-0007/releases/author-dev-recovery.json --split dev --owner author --run-dir 'C:\Users\jackg\eLedgerCare-Baseline\WP-0007\author\runs\author\20261116T142841Z-284039ca' --output 'C:\Users\jackg\eLedgerCare-Baseline\WP-0007\author\runs\author\20261116T142841Z-284039ca\scores.json'
```

Post verification used a host `-I -B` stdlib script importing only accepted q0harness.modelfiles, loading the frozen protocol/model manifest and running verify_model_dir(base/model_relative, manifest) plus verify_notices(base/notice_relative, manifest); its result was exclusively created in the new run. Existing Q0 model/environment and original baseline run were not written.

[Capture inventory](capture.json) lists all 53 copied paths, original external paths, bytes and SHA-256 values (400,066 bytes total), plus the pinned lineage/protected Git objects and raw observation checks. Copies include run/plan/score, three raw/token/render/native observations, load/preflight/events, heartbeat, stdout/stderr, periodic host observers, process/lease receipts and post-model verification. All 53 copied committed blobs match size/hash; all three raw digests match their observations. Caches, weights, packages and private agent transcripts are excluded; external originals remain retained.

The frozen worker runs its child-environment audit, but it does not emit a complete per-child environment-name snapshot. None was separately captured during this run; this checkpoint does not fabricate or infer a measured snapshot afterward. The retained plan/preflight/source contract and audit execution are narrower evidence. The torchvision local SHA-256 TOFU provenance limitation remains unchanged.

Protected baseline/Q0/evaluation/product and original runtime-dev Git trees remain exact at the executing HEAD. Only this new owned evidence directory and its later README are authored. No historical report/raw file, original13 primary score, shared routing or product source was changed.

## Handoff

eld-coordinator receives the completed supplemental checkpoint and explicit lease return; independent eld-baseline-reviewer /005 still owns later reproduction/disposition. Runtime completion and parse-invalid zero credit are both retained without substitution. No holdout input was read, no retry/new model work is implied, and canonical /004 waits for the separately released heldout phase and consolidated outcome. Normal owned-branch push/exact-origin verification follow this metadata commit; the publication SHA is supplied separately in the handoff.
