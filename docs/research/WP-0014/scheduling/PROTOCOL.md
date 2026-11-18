# WP-0014 scheduling trial

Freeze before inference. Target already-ready short A at ≤10 seconds from the Extract click to an in-viewport rendered result and ≥2× faster than the matched stock-A wait. Report each case and any failure separately. A and B must retain their expected transcription, reading order, page count, raw bytes across matched repeats, original and result/attempt provenance. An independent reviewer makes the acceptance decision.

## Five new lifetimes, ten real one-page calls

| Lifetime | Trigger | Native calls, in order | Browser action |
| --- | --- | --- | --- |
| Stock | Accepted supervisor claims the queued A | A | Click immediately after submitting and opening A. Accepted worker is unchanged. |
| Demand first | Diagnostic bridge receives the claimed job | A | The first real document pays process/model/first-forward costs. |
| Demand with warmup | Diagnostic bridge receives the claimed job | W, A | Measure a policy that requires a separate real warmup on demand. |
| Intake, immediate | First of two intake screens becomes usable | W, A, B | Two isolated Edge contexts submit distinct documents. Extract clicks start ~180 ms apart once both receipts are open. |
| Intake, ready | Same | W, A, B | Both awaits occur only in the measurement driver. Uploads and browsing proceed during warmup. The controlled Extract clicks wait for successful W. Record that lead time. |

A and B are the frozen image-only one-page fixtures at author commit `4ade03ee00e9701241770523d5df60df27da4b0c`. W is the committed image-only one-page “Warmup page.” using the same fixture generator. Full input hashes live in campaign.py. The 300-DPI PDF renderer, request prompts, limits, model, tokenizer, generation configuration and completion validator come from the accepted worker. Kernel and device observed at runtime. No result reuse. No retry or speculative model call. W is never saved as a product result. The per-attempt API bridge publishes its actual diagnostic source digest.

## Resources and chronology

Isolated worktree-owned PostgreSQL 18.7 on 55464, API 5814, static Angular bundle with streaming API proxy on 4814. Dedicated databases `eledgercare_wp0014_sched` and `eledgercare_wp0014_sched_cpu`. The accepted supervisor still claims one job at a time, builds a per-attempt request and fences and validates publication. Only one resident may start in a lifetime. Three small changes in an ignored copy of worker.py address session-local cache environment audit, separate resident heartbeat and verified model-file reuse. Per-attempt bridge heartbeat maintains the actual child identity. Model and notice file handles deny write/delete beginning before full verification. Inventories and request pins are checked on each subsequent attempt. Input and output validation stay per document.

SQL trace triggers observe queued/active counts under transaction snapshot semantics; concurrent uncommitted work may be invisible. PostgreSQL `pg_xact_commit_timestamp(xmin)` on diagnostic rows written in the same transactions supplies server commit-event times. It does not measure the return of fsync to the caller. Browser clock uses `performance.timeOrigin + performance.now()` for wall alignment and within-navigation intervals. The observer records trusted clicks, a rendered nonzero page with text, then scrolls the result into view and records the second animation frame. This measures DOM/layout and an in-viewport frame opportunity. Compositor pixels and human perception are unobserved. System timestamps use this one Windows host; Python engine also records monotonic counters. Device-wide occupancy sampled ~1 Hz includes desktop usage. PyTorch allocation and reservation peaks cover real inference. Keep overlapping intervals separate.

CPU controls inject a subprocess crash before loading CUDA and exercise read-only Windows pinning plus saved-result/source/draft-history reopening using explicitly replayed archived synthetic output. The replay uses a CPU-only dedicated database. No CPU simulation contributes an OCR timing.

Execute from this worktree with the immutable scheduling candidate, assigned lease and a new ignored run directory. The live database must initially contain zero jobs; package includes no deletion or automatic restart on error. Disk floor 20 GiB, initial free VRAM ≥10,000 MiB, previously observed WDDM graphics clients only, reserved sole RTX 5070 Ti and 840-second campaign budget. Recheck resources with the coordinator before any run. No GPU release is conveyed by this file.
