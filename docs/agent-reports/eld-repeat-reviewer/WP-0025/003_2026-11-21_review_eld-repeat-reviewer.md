# WP-0025 / 003 Independent review of the eight-call window replay

**Baseline variation was observed.** In both fresh processes, the first call reproduced the historical stock stream and all three subsequent calls reproduced the historical hooked stream. Stock and hooked calls each produced both streams. The original four page-one right-edge edits recurred. The page text, table cells, source-witness assignments and processed EOS matched throughout. The eight observations establish a first-call association on this input. They do not identify its cause. [Independent results](../../../reviews/WP-0025/independent.json) · [Primary archive](../../../reviews/WP-0025/window-repeat-r1.zip)

| Report metadata | Value |
| --- | --- |
| Author and publisher | `eld-repeat-reviewer`, native Codex role `/root/repeat25_review`, requested xhigh. Exact served backend and effective effort were not exposed. I operated the two orders and authored the review instruments. I had no authorship of Cloud Astra's handoff, either researcher's methods, the synthetic source, the sensor or the release. |
| Category, reservation and previous report | Review, WP-0025 /003 at `842f587e8d223360aaa6058518d999964d304278`. First report by this role. |
| Report path | `docs/agent-reports/eld-repeat-reviewer/WP-0025/003_2026-11-21_review_eld-repeat-reviewer.md` |
| Repository and worktree | `jackgumpe/eledgercare`, branch `review/wp-0025-window-repeat`, `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/replay25-review` |
| Environment and timestamp | Native Windows, PowerShell, Q0 Python 3.12.10 with `-I -B`, PyTorch 2.13.0+cu130, one RTX 5070 Ti. UTC REPORT_TIMESTAMP |
| Base and deliverable | Base `842f587e8d223360aaa6058518d999964d304278`, primary archive and independent analysis `60a9ffe3c610e06669daff98a88aa3da062df553`, completed reviewer deliverable `f45254227cac696e7f11bb5478a18a12e56e6c3e`, verified at origin. |
| Reviewed authors | /001 runner source `376e82b1fc85a1f28d3f77f505ef9b9891b4446f`, report publication `9064b7bed4beb1b900113460fd34734e42622948`. /002 analysis source `efcf568373a4745243c084f45f68167cceb89076`, result `a7962d81c3e339f73e30c27eda5ea5bef51e23b3`, report publication `ANALYSIS_PUBLICATION`. |
| Disposition and next owner | Accepted for this bounded diagnostic. `eld-coordinator` owns /004 and packet closure. |

## Physical input and frozen execution

I checked the PDF handoff digest `d5affad84f220465e4c4cc4d0b28bc035d6d15781c0929e144420547d2550797`, its first six pages, the old H0 plan and the historical primary archive. I rerendered physical pages 1–3 of synthetic binder `34054347f091c087a39efe17` at 300 DPI, independently decoded the three PNGs and verified each ordered 2550×3300 RGB buffer against the release. The accepted PDF SHA-256 is `675367788d2b872511d05b704b98069e8b636d02d07d78095cc4bbeab3e63d5b`. I checked both archived native streams, every recorded historical source hash, the unchanged model module, tokenizer and all 827 expanded prompt IDs. [Historical reconstruction](../../../reviews/WP-0025/historical-check.json)

The clean integrated runtime was `43b625bb97d403da99e888966dbf4e781e9674d1`, with unmodified BF16 Baidu checkpoint `0480966938291445591f69f08a13b041c073a96a` and historical sensor `1843cdb7b6279b84b539d3ca1ba7bd0affa1f7dd`. I verified release commit `88748016392246031d517efef22c4b3ef48f3057`, the exact eight tags, output directories, deadlines and each process's environment. Source inspection verified one resident load per process, real native `capture.infer` for each scheduled call, the common processed-terminal recorder and the two historical pre-hooks on H only. The under-lock desktop check runs before each order. [Exact release](https://github.com/jackgumpe/eledgercare/tree/88748016392246031d517efef22c4b3ef48f3057/docs/coordination/WP-0025)

| Actual order | Call 1 | Call 2 | Call 3 | Call 4 | First-call match | Later matches |
| --- | --- | --- | --- | --- | --- | --- |
| P1, PID 5132 | S | H | H | S | Historical stock | Historical hooked ×3 |
| P2, PID 20176 | H | S | S | H | Historical stock | Historical hooked ×3 |

The historical stock SHA-256 over 285 little-endian uint32 IDs including EOS is `887ff948d9da26e2933d1d2f396dd04c865e43c7efd860aeaf3773bfc6f60705`. The historical hooked SHA-256 is `d63703395cdc61e15fb86b3df73f021a56adb823ed563eb8065978023ea1554c`. I reconstructed all eight byte streams from the raw native IDs and processing events. Every terminal event selected ID 1 after 284 non-EOS tokens, with a three-page guard and the same stopping bounds. The first-call and later-call streams account for all 16 comparisons with historical S and H. [Eight-by-eight matrix and 16 historical comparisons](../../../reviews/WP-0025/independent.json)

## Token, geometry and feature evidence

The six S/S pairs split three equal and three unequal. The six H/H pairs split the same way. Ten of sixteen S/H pairs were equal. The six unequal S/H pairs split evenly between the historical stock-to-hook direction and its reverse when oriented by mode. The 28 pairs reuse the eight measured calls.

| Zero-based decision | Physical page-one block | Right edge on first calls | Right edge on later calls |
| ---: | --- | ---: | ---: |
| 13 | Portfolio directory heading | 399 | 395 |
| 77 | First listed schema | 388 | 387 |
| 100 | Second listed schema | 388 | 387 |
| 146 | Active unit declaration | 202 | 201 |

All 12 unequal pairs differed at these four IDs only. Decision 13 is the first divergence after an identical prefix. Each physical page's full parsed text, block literals and table grid agreed. I independently resolved the glyph rectangles for the owner “Ledger: Oak”, the unit “Unit: Unit4”, the schema row “Item / Amount / Ref” and the ordinary row “Service / 180 / 103”. Each bound to exactly one native block or row in all eight reads, for 32 of 32. All four source boxes above change the frozen 32-component geometry features, with maximum absolute FP32 changes of 0.181358, 0.040118, 0.040118 and 0.038027 respectively. [Source glyphs, boxes, IDs and feature changes](../../../reviews/WP-0025/independent.json)

Each H capture contained 284 BF16 rows of width 1,280 at consumed prompt-relative positions 827–1110. The selected EOS has no consumed row. I reconstructed each of 56 FP32 span means from independently mapped token membership and the underlying BF16 bytes, and matched all 56 exactly.

- The three later H traces and their pools matched one another and the historical H capture byte for byte.
- Each of the three first-versus-later H/H comparisons had 280 aligned token rows. Thirteen of those rows belonged to the common prefix and 267 matched in token ID, absolute position and span membership after the first differing decision. Four differing coordinate IDs were ineligible. Every aligned row differed, starting at row 0. The maximum absolute FP32 difference was 0.09375 in the common prefix and 0.890625 across all aligned rows.
- Each comparison had 14 aligned printed spans. All their pooled bytes differed, starting at span 0. Maximum absolute FP32 pool difference was 0.1000976711511612. S exposes no hidden state. The recording protocol supplies no S/H hidden comparison.
- The independent and /002 analyses agreed row by row and pool by pool for all six current H/H comparisons. They also agreed on the entire agreement matrix, first divergences, both historical comparisons per slot, witness statuses and terminal events. [Cross-check against /002](../../../reviews/WP-0025/author-crosscheck.json)

## Admission, return and verification

I invoked the guard once under the physical lock for `GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d`. Both admissions observed the known desktop clients with zero Ollama models and no unrecognized GPU client. I captured both worker-to-guard Windows parent chains, including the separate venv redirector PIDs. The guard retired at 20:25:37.233944 UTC with exit 0 and no error. All 15 recorded operator/guard/worker-chain PIDs were absent at 20:25:45.9995269 UTC.

| Order | Admission free MiB | Highest sampled board use MiB | Samples | Resident initialization, s | Guard wall, s | Exit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| P1 | 14,817 | 8,564 | 83 | 22.758 | 172.297 | 0 |
| P2 | 14,830 | 8,551 | 80 | 21.562 | 166.610 | 0 |

Both orders returned with 14,830 MiB free. The coordinator's before/after Q0 inventories are byte-identical, SHA-256 `1999f59e67c5c313d443f6bc72347c52bdd6dac961c21962b5e0920fcc1787f6`, covering 30,938 namespace/size/time entries and a separate content check on 37 model files. Library-offline controls were bound and checked. OS-level outbound filtering was outside this trial. [Process and board readback](../../../reviews/WP-0025/process-return.json) · [Primary inventory](../../../reviews/WP-0025/window-repeat-r1-inventory.json)

From the reviewer worktree I executed the following checks with the pinned Q0 interpreter and `-I -B`. CPU runs supplied reviewer-owned scratch, and numerical comparisons used CPU tensors.

| Commands or operation | Observed result |
| --- | --- |
| `reconstruct.py historical-check.json` and `runner_cpu.py <candidate-worktree> 43b625bb97d403da99e888966dbf4e781e9674d1 runner-cpu.json` | Historical raw streams, real PDF pages and all 14 historical H pools verified. Runner archival replays completed both orders. Wrong ordering, prompt or environment failed before load. Bad processed EOS, invalid guard accounting and missing H bytes each stopped at call 2 after one verified call. Exact clean candidate and a real Windows child passed the 37-key environment check. No model call in CPU preflight. |
| `analysis/preflight.main()` at `efcf568373a4745243c084f45f68167cceb89076` with its temporary directory redirected to reviewer scratch | Seven manufactured schedules, historical coordinates and witnesses, pool corruption, partial H/H alignment, undefined comparisons and nondivergence passed. |
| `binding.py`, then `operator.py` with the release SHA, integrated candidate and both plan SHAs | Operator verified the bindings and invoked the exact released guard command below. All eight slot verifications, two supervisor returns and the one guard return succeeded. |
| `reconstruct.py independent.json --runs <review/runs> --release <release> --release-sha <digest>`, `archive.py <release> <digest> window-repeat-r1.zip window-repeat-r1-inventory.json`, `return_audit.py window-repeat-r1.zip process-return.json` | Eight independent receipts, complete raw comparisons and six new H/H comparisons. Archive integrity, 108 file hashes, process order and guard data verified. |
| `crosscheck.py independent.json <analyst-result> process-return.json author-crosscheck.json` | Exact agreement with the independently authored numerical result at SHA-256 `899bf79acdf3d051a99b232bb30a383bfb0f356b9e861c62dbc11cdbc7fceffb`. An initial plain system-Python invocation of this post-run check failed at module import because the local operator script shadowed the standard-library module. The isolated pinned command passed. This caused no device call or primary-data change. |

```powershell
& 'C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe' -I -B 'C:/Users/jackg/Asp.net Projects/eledgercare/docs/coordination/WP-0025/device_lease.py' 'C:/Users/jackg/Asp.net Projects/eledgercare/docs/coordination/WP-0025/window-repeat-r1-release.json' '5509c70ff808edfbe65ab53578c89f0bb9c7e97778cec9317e486789bf6ac74f'
```

Plan SHA-256 values are `298f2cf3f087da67c6ac967969102a3e7f3c87d5f30f3750a23e1786749e747f` for P1 and `80f7e6f28927758bdfb4f989e63b661d36af1e2e8f88857d98b3fc0a7c6301e2` for P2. The 2,780,891-byte primary archive SHA-256 is `85efa292f454eed04fe73a6d8c4280db619ca97b5a031dbb31e88b84804ff764`. It includes both orders' native artifacts and clocks, the frozen plans, source PDF and three PNGs, all H traces and pools, guard receipts, board samples, process lineage and cleanup. [Source and live primary evidence](../../../reviews/WP-0025/window-repeat-r1.zip)

## Inventory, limitations and handoff

Every deliverable change is an addition under `docs/reviews/WP-0025/`. The 14 files are listed below. This canonical report is the sole subsequent addition. [Exact reviewer diff](https://github.com/jackgumpe/eledgercare/compare/842f587e8d223360aaa6058518d999964d304278...f45254227cac696e7f11bb5478a18a12e56e6c3e)

| Purpose | Added files |
| --- | --- |
| Input and runner preflight | `binding.py`, `runner_cpu.py`, `runner-cpu.json`, `historical-check.json` |
| Live operation and evidence | `operator.py`, `archive.py`, `window-repeat-r1.zip`, `window-repeat-r1-inventory.json` |
| Independent measurements | `reconstruct.py`, `independent.json`, `return_audit.py`, `process-return.json` |
| Analysis reconciliation | `crosscheck.py`, `author-crosscheck.json` |

The persistent runtime outputs, isolated caches and operator observations remain under `C:/Users/jackg/eLedgerCare-Speed/WP-0025/review`. Shared-guard journals remain under the packet's `coordination/leases/window-repeat-r1`. Temporary CPU scratch expired on exit. No outside process was stopped. The eight observations concern one public synthetic page triple and two cold loads. No logit margin, causal mechanism, training result, blind performance or memory outcome was measured. This closes independent review and hands the frozen evidence to `eld-coordinator` for /004.
