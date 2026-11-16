# F2: extract a submitted maintenance document and reopen its saved result

Author: eld-coordinator. WP-0006 /001, proposed for independent review. Original base `8e80a42c29c0fc27a4af6348cfb1ec22cab3764d`. Jack authorized this bounded implementation plus a separate vanilla baseline on 2026-11-16 UTC. This extends accepted F1 and Q0; prior designs/reports remain immutable.

## Customer outcome and scope

After durable intake, the local user requests extraction, sees honest progress/state, and can reopen the saved unreviewed result with the unchanged original. The first profile is admitted synthetic PDFs with 1-3 pages, within existing F1 format/byte limits. Acceptance includes the admitted dev F01 v1-raster300 PDF (a real raster-only PDF input to the model), and dev F07 v0-clean for page ordering if the 3-page profile is enabled. Unsupported profile inputs produce an explicit response without a model attempt. Product use remains local with admitted fixtures only; arbitrary/customer PDFs are not released.

Q0 established execution, not content correctness. F2 does not promise accurate fields, apply corrections, run an LLM judge, or promote an R&D improvement. F3 review/correction and F4 search remain later features. The result screen labels extracted content as unreviewed, preserves page order, escapes all text, and links/downloads the original. It shows useful status/error/retry actions without raw infrastructure logs or fabricated percent progress. A saved result is readable with the GPU worker disabled or unavailable.

## Small application boundary

Keep the existing one .NET solution and dependency direction. Add only demonstrated execution-attempt/result concepts, a local extraction service boundary and one production Python worker under `workers/local_ocr/`. No product reference, import or subprocess invocation may target `qualification/`, `research/` or `evaluation/` code. Necessary pinned runtime manifests can be copied with exact provenance into the worker; no evaluation scorer belongs in the product.

The .NET service owns PostgreSQL persistence, claims, process lifecycle and publication. A Python child reads only a coordinator/service-selected immutable PDF materialization and writes a bounded result envelope to its owned directory. Do not give the Python child database credentials, permit user-supplied paths/commands, use a shell to assemble its arguments, or introduce a broker/serving stack. Existing model and venv are reused read-only; generated module/cache/temp/output files go to the current task's owned run directory.

Proposed API: `POST /api/documents/{documentId}/extraction` requests or reconciles work; `GET /api/documents/{documentId}` retains F1 identity/status and adds current attempt/result references; `GET /api/documents/{documentId}/extraction` returns persisted attempt/result state. A duplicate request while queued/running or after successful publication returns the same durable work/result identity. Explicit retry is available only for failed/interrupted attempts and creates a new attempt while retaining old evidence. Freeze exact status codes and response schema during implementation without weakening these semantics.

F1 intake still creates `awaiting_extraction`; an explicit request queues work. States are `awaiting_extraction`, `queued`, `running`, `completed`, `failed`, `interrupted`. A job is distinct from each attempt. Commit queued work before acknowledgement; claim atomically; persist attempt identifier, monotonically distinct ownership/fencing token, start/heartbeat/end, outcome, and safe failure classification. Only the owning live attempt can publish its result. Publish validated result plus completion atomically, with a unique accepted-result boundary preventing duplicate completion on retry/replay. Failed/truncated output may be retained as diagnostic raw output but is never marked completed.

## Interruption and recovery

No long transaction spans model execution. Couple the child lifetime to its owned supervisor, including abrupt API/supervisor exit. Track the actual CUDA worker as well as a launcher if Windows creates both; PID alone is not a durable identity. After restart an abandoned running attempt becomes interrupted and retryable only after its old child is confirmed gone. Do not reclaim another live supervisor's work or start duplicate model children. Late completion from a fenced-out attempt cannot overwrite a newer state/result. A queued job survives restart. A committed result survives process and PostgreSQL restart and remains accessible without executing OCR again. No exactly-once model-execution guarantee is claimed.

Runtime role privileges expand only for required updates/inserts/selects on job/attempt/result tables; original artifact bytes/digest remain immutable and migration/schema privileges stay separate. Add a forward migration, preserving existing F1 rows and constraints that remain applicable. Use real isolated PostgreSQL in acceptance; no SQLite/in-memory substitute.

## Frozen unmodified inference and provenance

Model `baidu/Unlimited-OCR-2@0480966938291445591f69f08a13b041c073a96a`; same verified 18 runtime objects, separate notice, CPython 3.12.10 and Q0 lock (torch 2.13.0+cu130, torchvision 0.28.0+cu130, transformers 4.52.1, pypdfium2 5.15.2/PDFium 159.0.8149.0). Retain disclosed `torchvision-local-sha256-TOFU`; no new runtime dependencies/upgrades without evidence review. Verify actual files before model load, keep network offline, use separate cache directories and verify imported custom-code copies. No changes to model, weights or library internals.

Render committed PDF bytes at 300 DPI with Q0's exact PDFium RGB call. Use native `infer_multi`, `crop_mode=False`, `save_results=False`, `output_path=""`, greedy temperature 0 and Q0 generation kwargs: `max_length=131072`, `max_new_tokens=8000*pages` only when context budget permits, `max_page_tokens=20000`, page guard on, `no_repeat_ngram_size=35`, `ngram_window=128` for one page or 1024 for multiple pages, no whitelist, base/image/crop limits 1024/640/16. Expected native dense fallback is allowed; optional backend, CPU/device fallback, preprocessing/treatment or wrapper substitution is not. The unsafe native save/eval path must remain unreachable. Safe display parsing must never eval model text or render it as trusted HTML.

Persist raw UTF-8 native output exactly, its digest, document/attempt IDs, input hash/length/page count, model revision and manifest digest, dependency-lock digest, worker source revision/config digest, renderer identity, generation settings, timestamps/durations, finish reason/page count and bounded diagnostic metadata. Preserve full provenance server-side; show meaningful model/run/date information in the UI. Return a versioned worker envelope (`eledgercare.local-extraction/1`) with these identities; validate every binding and output limit before acceptance. The protocol is shared conceptually with R&D, with no shared product dependency on research code.

## Owned resources and acceptance

Author worktree `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-f2-implementer`, branch `feature/wp-0006-local-extraction`; reviewer worktree `...\eld-next-reviewer`, branch `review/wp-0006-0007-next-tracks`. Author ports API 5190/UI 4210/PostgreSQL 55434; reviewer 5290/4310/55435, all loopback, availability observed before bind. Each uses its own `.local` cluster/secrets/logs and databases. Read-only reuse of existing eLedgerCare PostgreSQL binaries/package caches is permitted; never reuse an old mutable cluster or its credentials. No global installs, service/Docker changes or unrelated-resource cleanup.

Verified read-only model/venv root: `C:\Users\jackg\eLedgerCare-Q0\WP-0005`. New runtime state: `C:\Users\jackg\eLedgerCare-F2\WP-0006\author` or `reviewer`, up to 4 GiB each and at least 20 GiB free on C:. Process/GPU/run-directory observations precede each sole lease. Local extraction is disabled by default until a bounded coordinator runtime release; UI must describe unavailable execution honestly. Model guards retain Q0 limits: load 1800s, 1-page call 1800s, 3-page 3600s, no-forward-progress stall 300s, raw output 16 MiB, logs 64 MiB. GPU concurrency one across both packets; stale timer/low VRAM alone never grants ownership.

| Criterion | Required actual evidence |
| --- | --- |
| F2-01 | Real admitted raster PDF submission -> durable extraction request -> actual unchanged model output -> saved completed result -> usable browser result |
| F2-02 | Original bytes/digest unchanged; raw output/digest and provenance binding verified independently against child output; page order/count preserved |
| F2-03 | Duplicate/concurrent requests reconcile to one active attempt/accepted result; failed/interrupted retry retains prior attempt and fences stale publication |
| F2-04 | Queued work survives restart; forced termination of owned active worker/supervisor gives honest interrupted/failed state, no orphan/duplicate child, and successful explicit retry |
| F2-05 | API and real PostgreSQL restart preserve attempt/result identities, raw bytes and readable UI; reopening with OCR disabled performs no new model run |
| F2-06 | Unsupported/oversized profile, bounded worker error, malformed/mismatched result, timeout/truncation and unsafe text are handled honestly; focused tests may use failure envelopes at the service boundary, but real OCR is mandatory for happy-path acceptance and no mock enters production |
| F2-07 | Forward migration of F1 data, least-privilege runtime grants, applicable F1 regression/build/browser checks, product/research separation and independent reproduction on exact candidate |

Author freezes source before decisive tests; evidence/report follow. Independent reviewer inspects actual source and reproduces meaningful boundaries in separate resources. One combined review response/evidence reconciliation resolves substantive findings before escalation. R&D accuracy measurements and optional optimization wins do not hold up this feature's correct persistence/state behavior.
