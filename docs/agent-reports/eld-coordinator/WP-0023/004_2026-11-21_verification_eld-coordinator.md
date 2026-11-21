# WP-0023 / 004 — Native B=2 fails exact singleton parity on the long window

| Record | Value |
| --- | --- |
| Report | `docs/agent-reports/eld-coordinator/WP-0023/004_2026-11-21_verification_eld-coordinator.md`, verification, reserved /004 |
| Author and publisher | eld-coordinator, continuous native Codex CLI, Windows. Exact coordinator backend and effort unexposed. Three fresh role sessions requested xhigh. |
| Repository, branch and base | Private `jackgumpe/eledgercare`, `coordination/bootstrap`, `9eedf0f8b684746ff163d614851120c2d7ee88a5` |
| Reservation and reviewer device candidate | `1503bc9f1a7bf3de4bfa7426c2be906226992c0c` and `8682fc7d215c0b063d5c3ef8ccce91a090cff90c` |
| Decision deliverable and reviewed integration | `a47a11b76f83eedd99b52096facd4bf303885a81` and `cfd1dbeeef83e85e793f3a7561e5fdf63903b8c0` |
| Published UTC | 2026-11-21T09:23:18Z |
| Status and next owner | Accepted independent trial finding. The BF16 batching candidate failed the advancement gate. Packet closed by eld-coordinator. |

The release asked whether two concurrent three-page development windows could preserve every native singleton decision and earn a timed throughput trial. Gate 1 passed for both windows. Gate 2 failed for the long window in both batch positions. The coordinator withheld timed AB/BA and a 60-page replay. The diagnostic measured a real difference in output. A native B=2 throughput or accuracy claim would require other evidence. [Independent disposition](https://github.com/jackgumpe/eledgercare/blob/3eb3e9f53db53ba9d148af883a2a05159626c782/docs/agent-reports/eld-batch-reviewer/WP-0023/003_2026-11-21_review_eld-batch-reviewer.md) · [Decision data](../../../coordination/WP-0023/decision.json)

## Exact outcomes

The two windows came from a twelve-page synthetic development PDF. Pages 4–6 each contained a short maintenance note. Pages 7–9 each contained a materials order with a ruled table. Their 300-dpi RGB rasters were frozen before inference. Each native prompt had 827 tokens and three page markers. The counterbalanced slot order preserved each window's images, tokens and terminal criteria. [Inputs](../../../coordination/WP-0023/fixtures/manifest.json) · [Freeze and upstream batch-of-one excerpt](../../../coordination/WP-0023/release-receipt.json)

| Window | Stock output before EOS | Edited B=1 | B=2, short first | B=2, long first |
| --- | ---: | --- | --- | --- |
| Short | 62 tokens, then EOS ID 1 | All 63 decisions matched | All 63 matched | All 63 matched |
| Long | 665 tokens, then EOS ID 1 | All 666 decisions matched | Seven token substitutions, same stop | Same seven substitutions, same stop |

All arms produced three pages per window. Each B=2 permutation used one joint prefill and real decoder calls with input shape `[2,1]`, hidden shape `[2,1,1280]` and logit shape `[2,1,129280]`. The short lane's stop preceded the long lane's first differing decision. Its terminal observation and guard state stayed fixed while the other lane continued. The two batched permutations yielded identical sequences after reassigning slots to window identity. The first long mismatch, at zero-based index 84, moved the bottom edge of the first table from 516 to 518. Later changes affected two heading levels and the capitalization or spacing of table headers. [All decoded differences](../../../coordination/WP-0023/decision.json) · [Engine author /001](https://github.com/jackgumpe/eledgercare/blob/9129ef3976fc754e0c41ca225e9922079b12227d/docs/agent-reports/eld-batch-engine/WP-0023/001_2026-11-21_research_eld-batch-engine.md) · [Trial author /002](https://github.com/jackgumpe/eledgercare/blob/e707b3347956d0333a8094b6329fd85c1feb7b0c/docs/agent-reports/eld-batch-trial/WP-0023/002_2026-11-21_research_eld-batch-trial.md)

## Matched-prefix diagnosis

Both candidate tokens remained eligible under the lane's no-repeat n-gram and page-count guards. Raw and post-guard BF16 scores agreed. Stock and edited B=1 tied, and greedy argmax picked the lower token ID. B=2 separated those scores in both permutations. The table gives the measured logits at the same 84-token long-window prefix. [Independent logit and hidden-state audit](../../../reviews/WP-0023/dev-r1-audit.json)

| Path | `516`, ID 24254 | `518`, ID 25089 | Selected |
| --- | ---: | ---: | --- |
| Stock and edited BF16 B=1 | 58.00 | 58.00 | 516 |
| BF16 B=2, either slot | 57.50 | 57.75 | 518 |
| BF16 difference, B=2 minus B=1 | −0.50 | −0.25 | |
| FP32 B=1 | 58.60135651 | 58.72898102 | 518 |
| FP32 B=2 | 58.60135651 | 58.72896194 | 518 |

The FP32 prefix replay used the frozen weights, with vision, decoder, cache, routed experts and output head evaluated in FP32. The original raster-builder values were promoted, TF32 was disabled, and PyTorch math attention was selected. The FP32 cross-shape delta for `518` was −0.00001907. The BF16 difference was already visible at the first decoder-layer output, with equal observed page state and active candidate masks. The evidence supports sensitivity to numerical precision and batch shape at this prefix. The kernel responsible and full-sequence FP32 behavior remain unknown. [Source and precision contract](../../../research/WP-0023/engine/native_batch.py)

## Time and memory

One cold model load took **14.062 s** within **25.470 s** of verified native initialization. The board-wide device monitor took 212 samples at approximately two-second intervals. The table records observed peaks in MiB for the whole graphics board, including the desktop. Individual allocator peaks and per-call UTC boundaries are preserved in the primary records. No warm crossover samples qualified. [Per-stage board samples and archive digest](../../../reviews/WP-0023/dev-r1-inventory.json)

| Phase | Peak observed board use |
| --- | ---: |
| Cold initialization | 6,962 MiB |
| Gate 1, native and edited B=1 | 8,704 MiB |
| Gate 2, normal BF16 B=2 in both orders | 8,724 MiB |
| Additional BF16 diagnostic probes, including FP32 head | 9,356 MiB |
| Full FP32 diagnostic, B=1 / B=2 | 14,635 / 14,849 MiB |

The reviewer held the shared GPU lock for `dev-r1`. The Windows job returned with a successful child exit, zero resident Ollama models, no observed model-process owner and 1,320 MiB of board memory in use. The successfully completed trial reported a failed scientific gate. [Finite release](../../../coordination/WP-0023/dev-r1-release.json) · [Archive](../../../reviews/WP-0023/dev-r1.zip)

## Verification, scope and handoff

The coordinator rebuilt the eight fixture files byte-for-byte and compared 46 archived records against their originating files. The private GitHub archive returned 471,469 bytes and SHA-256 `9d7b818fab660ef7c25ee98bd5161ea10e7d745516f9bb8ff7b796571571e2ed`. Replaying the independent audit on the archived trial files reproduced its complete JSON. Recomputing the coordinator decision reproduced its published bytes. Both before/after inventories cover 37 model files, 6,699,197,096 bytes and three subdirectories. All content hashes, file write times and directory listings matched. [Verification receipt](../../../coordination/WP-0023/evidence-readback.json) · [Model inventory](../../../coordination/WP-0023/model-after.json)

The following commands identify the principal verification entry points. The GPU command was executed by the independent reviewer. Its plan, output path and source hashes are fixed in the published lease. `$py` is the Q0 Python 3.12.10 interpreter. `$model` is the external frozen model directory named in the release receipt. `$archiveTrial` is the extracted `run/trial` directory from the review archive. Coordinator recomputation uses a new output file.

```powershell
& $py -B docs/research/WP-0023/engine/cpu_checks.py $model
& $py -I -B docs/research/WP-0023/trial/test_cpu.py
& $py -I -B docs/coordination/WP-0023/device_lease.py docs/coordination/WP-0023/dev-r1-release.json 1607be5580efe5af2b640c2a295bbfdd5cf08f88863a0fce746cfe039c14c2d3
& $py -I -B docs/reviews/WP-0023/audit_run.py $archiveTrial
& $py -I -B docs/coordination/WP-0023/decision_from_evidence.py docs/reviews/WP-0023/dev-r1.zip docs/reviews/WP-0023/dev-r1-inventory.json "$model/tokenizer.json" $freshOutput
```

The engine CPU checks and all five trial harness tests passed. Two preliminary coordinator invocations of the engine CPU checker used an incompatible isolated import path and then omitted its model-directory argument. The documented command passed before the lease. The coordinator also found that the preliminary harness would admit equal or reversed stock output lengths. The trial author added an explicit length gate before the sole decisive GPU execution. The reviewer inspected the exact corrected sources and separately verified the raster inputs, control-flow checks, stop decisions, signed score deltas and lease return. [Independent review](https://github.com/jackgumpe/eledgercare/blob/3eb3e9f53db53ba9d148af883a2a05159626c782/docs/agent-reports/eld-batch-reviewer/WP-0023/003_2026-11-21_review_eld-batch-reviewer.md)

The base-to-deliverable changes comprise the packet reservation in INDEX and CURRENT, coordinator fixtures, leases, verification and receipts under `docs/coordination/WP-0023`, the two research paths under `docs/research/WP-0023`, reviewer checks and evidence under `docs/reviews/WP-0023`, the reserved reports and one queue metadata file. External effects were restricted to owned worktrees, private branches, local synthetic fixtures, the Q0 read-only checkpoint, run-local caches and the returned GPU lease. The coordinator did not incorporate the pre-existing worktree change to `web/package.json`. Packet B stayed sealed. Production source tree identities matched the reservation base. [Base-to-integration diff](https://github.com/jackgumpe/eledgercare/compare/9eedf0f8b684746ff163d614851120c2d7ee88a5...cfd1dbeeef83e85e793f3a7561e5fdf63903b8c0)

Twin-Binder v2 remains unnumbered. The queue records both directions of the cached-feature donor-matrix swap at Window W, fixed symmetric candidates, donor flip, abstention and receiver retention. A formerly correct T2/T3 M2 posting lost to M3 abstention reduces paired gain and coverage. Newly silent owner, unit, column or subtotal-status errors, any T1 loss versus M2 and any silent T1/T4 error veto advancement. This packet executed only the two development windows. [Queue entry](../../../coordination/queued/baidu-twin-binder-v2.md)
