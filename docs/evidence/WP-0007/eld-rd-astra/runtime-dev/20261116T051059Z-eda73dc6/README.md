# B0 dev checkpoint: first run stopped on final document

Author eld-rd-astra, same native /root/rd_astra; inherited dispatched gpt-6-astra/high, backend checkpoint/session UUID not exposed. Timestamp 2026-11-16T05:50:26.968196+00:00. This is an intermediate dev checkpoint, not canonical WP-0007 /004, independent acceptance or a completed 26-document baseline.

- Branch: research/wp-0007-vanilla-baseline; owned worktree `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-baseline-astra`.
- Exact executing clean HEAD/base: `e22c6730d19a6d616f0e7afb00b9416635799c16`.
- Frozen accepted source: `f807e0ac737df4e9e0aeeb96f716afec57f58ff6`; baseline tree `df44162c62641596032df04bc834754da38a5f7b`.
- Independent /003: `8c208273c2524b0253b046159178a9f5e6788049`.
- Exact authority: `a6f8f2a17fc8f3db68e11d2971423f78b2dc7861`; release `docs/coordination/WP-0007/releases/author-dev.json` and its bound dev-runtime kickoff were read through Git. No coordinator commit was merged into the executing worktree.
- Evidence commit: `1d6a681f09b0eaf233f838c54465c36a042ec326` (143 new files: 142 exact copies plus capture.json). This later README is metadata only.
- Actual run: `C:\Users\jackg\eLedgerCare-Baseline\WP-0007\author\runs\author\20261116T051059Z-eda73dc6`.
- Sole lease: `WP-0007-author-dev-20261116T050815Z`; GPU UUID `GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d`.

## Execution and first failure

Exactly one invocation ran the frozen schedule: two excluded warmups and 13 measured dev documents (19 planned measured pages). Both warmups and 12 measured documents completed. The final three-page `SYN-MP-01-v2-skew-pos4deg` call was interrupted and is marked failed. No automatic or manual retry, substituted observation, source change, prompt/parameter change, optimization or score tuning occurred.

Supervisor exit code 1, elapsed 2139.687 seconds; exact retained failure:

```text
SUPERVISOR_ERROR:FileNotFoundError(2, 'The system cannot find the file specified')
```

The supervisor's exception record contains no missing filename or traceback. It closed its owned job; actual worker and venv launcher exited. `worker-outcome.json` is absent. Last heartbeat remains at the final call, progress 18709; its render record and partial native text in stdout are retained. No completed raw/token/observation artifacts exist for that last call. Partial stdout was not reconstructed into a completed native observation or granted exact credit.

A source-only hypothesis is a race between `runtime.directory_size` recursively enumerating/stating live files and the unchanged Q0 heartbeat writing `heartbeat.tmp` then atomically replacing it. That code path can encounter a disappearing file; the captured exception does not establish that this was the cause. No new reproducer or fix was executed in this released run. One diagnostic rg search also named a nonexistent q0harness/evidence.py; the actual heartbeat source was then read from session.py. This inspection error is separate from the runtime failure.

Completed observations all have empty failure flags, no error and `triton_import_failed_dense_fallback`. Preflight retained wheel/installed-lock checks, model/notice/source checks and renderer identity; load evidence retains verified module-cache copies and timing/memory. This does not imply the full B0 run succeeded or establish a post-run rehash of external model files.

## Process ownership and explicit lease return

| Role | PID / parent | Observed creation UTC |
| --- | --- | --- |
| Host supervisor | 31824 /33708 | 2026-11-16T05:10:59.298237Z |
| Venv launcher | 18748 /31824 | 2026-11-16T05:10:59.891201Z |
| Actual worker | 2156 /18748 | 2026-11-16T05:10:59.914662Z |

[Start receipt](author-process-start.json) preserves the observed executable paths/commands. After the supervisor exited, a CIM query confirmed all three PIDs absent; the query was repeated after scoring. [Exit and lease receipt](author-process-exit-and-lease-return.json) explicitly returns the lease at **2026-11-16T05:47:18.7008507Z** with no owned processes present. This return was immediately sent to eld-coordinator. No GPU work continues under this assignment.

The score command completed exit 0 while the exact e22c HEAD remained clean and the a6f8 release valid. Only after execution/scoring did evidence copying and commits change the worktree. No source was edited. Normal private-origin publication follows this checkpoint commit; exact remote verification is supplied in the handoff, not fabricated into the immutable record.

## Exact commands and retention

Registered host interpreter: `C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe`, CPython 3.12.10. All shell commands explicitly used the owned worktree. The supervisor created its unchanged isolated pinned venv child.

```powershell
& 'C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe' -I -B qualification/baseline/baseline.py execute --authority a6f8f2a17fc8f3db68e11d2971423f78b2dc7861 --release-path docs/coordination/WP-0007/releases/author-dev.json --split dev --owner author

& 'C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe' -I -B qualification/baseline/baseline.py score-run --authority a6f8f2a17fc8f3db68e11d2971423f78b2dc7861 --release-path docs/coordination/WP-0007/releases/author-dev.json --split dev --owner author --run-dir 'C:\Users\jackg\eLedgerCare-Baseline\WP-0007\author\runs\author\20261116T051059Z-eda73dc6' --output 'C:\Users\jackg\eLedgerCare-Baseline\WP-0007\author\runs\author\20261116T051059Z-eda73dc6\scores.json'
```

[Capture inventory](capture.json) enumerates every copied path, original external path, byte length and SHA-256: 142 files /1,514,717 bytes, comprising top-level run/plan/score/process/heartbeat/log/observer files and all evidence files. Caches, weights, packages and private agent transcripts are excluded. All 142 copied files match committed bytes at evidence commit; all 14 completed native raw files match their observation digests. Original external raw bytes remain retained. The capture JSON adds provenance, all protected Git object identities and observation/timing summaries; it is not an independently executed review.

No held-out PDF/source/expected content was accessed, no libraries/models/configuration installed or edited, no source changes made, and no other owner's process stopped. Git diff against e22c for baseline/Q0/evaluation/src/tests/web/workers/deploy is empty; all captured protected tree identities remain exact. Only the authorized author runtime root was created. The run result records 61,441,868 owned bytes and 54,011,527,168 C: free bytes at its end; later copied metadata does not change the recorded runtime observation.

## Descriptive dev scores, including failed denominators

[Scores](scores.json) retain all 13 measured documents; warmups are excluded. Every missing/unmapped/failed expected item remains in denominator. The interrupted final document receives 0/15 fields and 0/180 cells for both metrics, with missing/parse diagnostics and text deletion/error bookkeeping from its absent completed output.

| Fixture | Completion | Printed fields | Printed cells | Typed fields | Typed cells |
| --- | --- | ---: | ---: | ---: | ---: |
| SYN-WO-01-v0-clean | completed | 15/15 | 18/19 | 15/15 | 18/19 |
| SYN-WO-01-v1-raster300 | completed | 15/15 | 18/19 | 15/15 | 18/19 |
| SYN-WO-01-v2-skew-pos4deg | completed | 7/15 | 16/19 | 7/15 | 16/19 |
| SYN-WO-02-v0-clean | completed | 15/15 | 12/12 | 15/15 | 12/12 |
| SYN-WO-02-v1-raster300 | completed | 15/15 | 12/12 | 15/15 | 12/12 |
| SYN-WO-02-v2-skew-neg3deg | completed | 7/15 | 0/12 | 7/15 | 0/12 |
| SYN-WO-02-v3-hybrid-note | completed | 15/16 | 12/12 | 15/16 | 12/12 |
| SYN-INV-01-v0-clean | completed | 13/15 | 36/36 | 13/15 | 36/36 |
| SYN-INV-01-v1-raster300 | completed | 13/15 | 36/36 | 13/15 | 36/36 |
| SYN-INV-01-v2-skew-neg3deg | completed | 5/15 | 0/36 | 5/15 | 0/36 |
| SYN-MP-01-v0-clean | completed | 13/15 | 72/180 | 13/15 | 72/180 |
| SYN-MP-01-v1-raster300 | completed | 13/15 | 72/180 | 13/15 | 72/180 |
| SYN-MP-01-v2-skew-pos4deg | failed | 0/15 | 0/180 | 0/15 | 0/180 |

Equal-family macro: printed fields **0.7349826389**, printed cells **0.6489035088**; separately labeled typed fields **0.7349826389**, typed cells **0.6489035088**. Pooled counts are 146/196 fields and 304/753 cells for each metric, reported only as additional counts, not substituted for the frozen family macro. Per-family/per-variant aggregates, absence/excess/duplicate/sentinel/adjacency/link metrics and all detail reasons remain in scores.json.

These values combine schema mapping and recognition. F07 clean/raster each map only 72/180 cells because later headers do not exactly match dev rules. Skewed F02/F04 tables also fail exact-header mapping. The hybrid addendum lacks a mapped field candidate. These uncredited items are not asserted measured character-reading errors or automatic factual hallucinations. Raw token sequence error is separately reported (dev family macro 0.2489363828); it includes native-versus-reference ordering and the failed output's deletion bookkeeping and is not minimum-Levenshtein WER.

Completed measured external synchronized call times range 77.9050–291.0588 seconds. The failed call has no completed timing observation and is not silently treated as a fast completion. Host load timings include import 2.0614s, tokenizer 0.4316s, CPU from_pretrained 7.1033s and synchronized CUDA transfer 3.9704s. Per-call native/derived timing and sampled host/CUDA memory are retained with provenance. Root explicitly reported concurrent F2 CPU/RAM work and desktop WDDM activity: these are uncontrolled latency/memory confounders despite exclusive task GPU ownership. One measured call/document gives descriptive observations, not controlled causal improvement, repeatability or population accuracy.

## Next owner and remaining scope

eld-coordinator receives this first-failure checkpoint and explicit lease return. The same independent eld-baseline-reviewer may inspect the retained run/failure/score evidence; this author does not accept its own execution. No held-out phase or additional model invocation is implied by the still-future release expiry. A separate exact coordinator disposition/release is required before any next model phase, and any runtime source correction requires its own bound review rather than silent repair. Canonical /004 waits for the separately released holdout phase and consolidated outcome; independent /005 and final coordinator /006 remain outstanding. Earlier Q0 retrospective diagnostics remain separate from these new B0 measured calls.
