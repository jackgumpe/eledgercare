# WP-0024 / 002 External memory probe and H0 stop

**H0 failed.** The independent operator ran all sixteen stock and hooked B=1 calls on the two development binders. Seven of eight stock/hooked window comparisons matched through EOS. Four bounding-box coordinate tokens differed in the first binder's first window. The protocol stopped real probe fitting, threshold calibration and blind extraction. There are no held-out predictions or pair-level model results. [Independent H0 audit](https://github.com/jackgumpe/eledgercare/blob/823b5eedd5687188c4b6cc0d0698ea3db12d9798/docs/reviews/WP-0024/h0-r1-independent.json) · [Independent /003 disposition](https://github.com/jackgumpe/eledgercare/blob/b1db32ce45507eda024dd1f83e31c49365f5484f/docs/agent-reports/eld-rd-reviewer/WP-0024/003_2026-11-21_review_eld-rd-reviewer.md)

| Report metadata | Value |
| --- | --- |
| Report path | `docs/agent-reports/eld-twin-author/WP-0024/002_2026-11-21_research_eld-twin-author.md` |
| Reservation and category | WP-0024 /002, research. [Reserved INDEX row](https://github.com/jackgumpe/eledgercare/blob/d8ad61f6bedbf80fe183d801345ca77c735884d4/INDEX.md#wp-0024-counterfactual-twin-binder-baidu-memory-trial) |
| Author and publisher | `eld-twin-author`, native Codex project session `/root/t24_probe`, self-published. Fresh session, requested xhigh. The served backend and effective effort were not exposed. |
| Execution environment | Windows PowerShell, pinned local Q0 Python 3.12.10 invoked with `-I -B`, PyTorch 2.13.0+cu130, CPU FP32 with CUDA hidden. |
| Repository and worktree | Private `jackgumpe/eledgercare`, branch `research/wp-0024-twin-probe`, worktree `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/twin24-author` |
| Base and final deliverable | Reservation `d8ad61f6bedbf80fe183d801345ca77c735884d4`, frozen probe `7db67283a4ffd3e7a20bb8d80499572cc7118c71` |
| Publication time UTC | 2026-11-21T18:01:37Z |
| Status and next owner | Author evidence ready for review. Independent /003 has already recorded the stopped execution. Next owner `eld-coordinator` for /004 and ledger disposition. |
| Related work | First report by this author in the packet. Custodian /001 owns the fixture and independent scorer. Development source `7ae03a8fc60719f162552a4ccf218227fcb0f92a`, scorer `e6c1abaed36a379780084be826c5fd0afaf3132b`. Neither cloud design participant served as accepting reviewer. |

## Objective and implementation

Compare whether an eight-level external PDS matrix restores earlier owner, unit, column and child subtotal beyond a flat matrix or a discrete saved frame over frozen Baidu activations. The decision requires exact stock/hook parity first, independent C1 and C0 evidence, frozen fits and predictions, pair-level leakage and safety checks, and measured resources. [Released handoff](https://github.com/jackgumpe/eledgercare/blob/d8ad61f6bedbf80fe183d801345ca77c735884d4/docs/coordination/WP-0024/inputs/release-instruction.md) · [Frozen author protocol](https://github.com/jackgumpe/eledgercare/blob/7db67283a4ffd3e7a20bb8d80499572cc7118c71/docs/research/WP-0024/probe/PROTOCOL.md)

The frozen candidate implements six views on the same online observations. M0 reads the suffix and the canonical choices. M1 writes one flat delta matrix. M2 updates typed frames, holds a tentative child close until confirmation and applies observed unit amendments. M3 reads eight protected matrices. M3-Zero retains the M3 controller and registry with matrix reads disabled. M3-Swap transfers the entire matrix state in both directions at entry to the last window. Each receiver retains its own controller, registry, observations and suffix features. Opaque donor and receiver IDs are attached after all decisions. Every arm retains actual or structural Window-1 evidence. Binding and subtotal diagnostics remain separate from the typed posting or abstention.

M1 and M3 each contain 880,258 trainable parameters. The final-layer pooled 1,280-vector and 32 Fourier box features enter the neural recurrence. M3 freezes inactive lanes exactly. Rank-four quotient Pop-Commit uses the final 32 key coordinates, applies the 1e-6 QR rank mask, preserves the first 96 protected coordinates and wipes the child lane. M1 and M3 share the content-only candidate encoder and learned projection budget. M2 stores parsed symbolic records. The scorer and probe were authored separately.

The fixed development plan specifies ten training and ten calibration pairs, identical initial seed 2401, six epochs, AdamW at 0.0005, weight decay 0.01, gradient norm cap 1.0 and the same finite threshold grid for both models. Calibration ranks silent errors, correct pairs and answerable coverage, with the frozen thresholds' tie-break order. The training algorithm and calibration semantics were tested on synthetic controls. The actual per-arm fit, selected thresholds and weight hashes could only be produced after H0.

## Verification and evidence

From the owned worktree I ran the following preflight on the initial candidate, on the reconciled candidate and again at the final source. Each run exited 0. The independent reviewer also executed the final candidate in isolated scratch. [Final preflight output](https://github.com/jackgumpe/eledgercare/blob/ccfebec4975c1b9ea4fb8cbc3ab1a5622680fb1b/docs/reviews/WP-0024/probe-preflight-7db67283.json)

```powershell
$env:CUDA_VISIBLE_DEVICES='-1'
$env:OMP_NUM_THREADS='1'
& 'C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe' -I -B docs/research/WP-0024/probe/preflight.py
```

| Check | Actual result |
| --- | --- |
| Matrix equations on constructed inputs | Author nonempty rank 4, summary-coordinate max change 1.8394217491149902, protected-read FP32 max change 0.0. Empty child rank 0 left the parent identical. Inactive lanes and cleared child passed. Rank-one backward stayed finite. The rank mask kept exactly columns 1 and 3 on the four-column threshold control. All 11 optimizer tensors in each arm received finite nonzero gradients. [Author evidence](https://github.com/jackgumpe/eledgercare/blob/a678e61145c76f7d2b33296551d62cc866a62d15/docs/research/WP-0024/probe/preflight-calibration-result.json) |
| Independent matrix controls | The reviewer compared 24 active writes per model against FP64, max error 2.684e-7, zero inactive change. Separate rank 4, 2, 3 and 0 cases preserved protected reads exactly and wiped the child. [Independent controls](https://github.com/jackgumpe/eledgercare/blob/ccfebec4975c1b9ea4fb8cbc3ab1a5622680fb1b/docs/reviews/WP-0024/matrix-7db67283.json) |
| Six-view controls | On public constructed inputs M2 recovered both amended units, distinguished balanced and unbalanced quantities, and abstained on an unresolved child. Zero-state tied and abstained. Both swaps installed the opposite matrix digest, preserved receiver nonmatrix digests and changed untrained component scores. Directory-choice equality receipts, structural and actual Window-1 audits, and source-aware provenance survived serialization. [Independent Window-1 replay](https://github.com/jackgumpe/eledgercare/blob/ccfebec4975c1b9ea4fb8cbc3ab1a5622680fb1b/docs/reviews/WP-0024/w1-7db67283-e6c1abae.json) |
| Calibration disagreement and correction | Original `ae5b78b99d85619e8faca4550ed2ed0ee2fd060d` treated `BIRCH` versus `Birch` as a silent wrong posting. I reproduced it. Candidate `998e21e11257d26a868d54cf593cb56bcd18d4eb` compares non-null text after entity decoding, whitespace normalization and case folding, preserves literal tag content, and requires null equality. My eleven checks include invalid type rejection. The independent tester compared ten valid cases to its separately owned scorer and reproduced agreement. The original candidate, original CPU evidence `f30ed3efab65049ded54d9bdc15265fffa4a12de`, and corrective evidence remain available. [Independent calibration audit](https://github.com/jackgumpe/eledgercare/blob/ccfebec4975c1b9ea4fb8cbc3ab1a5622680fb1b/docs/reviews/WP-0024/calibration-7db67283-e6c1abae.json) |
| Serialized inference harness | Two fresh Q0 Python `run.py infer` subprocesses at final source consumed generated feature files and fixed random weights, exited 0, and produced 12 typed records each with both donor/receiver directions. Prediction SHA-256 was `7f14d7b93aeead44878f009ecfea4a5827a749e9b5997308a5bed239dc2e48d6` both times. Complete process times 6.6255348 and 6.0575668 seconds include startup. These are transport controls. |

The exact synthetic subprocess argument arrays, UTC start/end, stdout/stderr and result digests are retained under `C:/Users/jackg/eLedgerCare-Speed/WP-0024/probe/inference-transport-cpu-r2/` in `replay1-command.json`, `replay2-command.json` and the corresponding receipt files. Command SHA-256s are `8a76e23f0298f60a391c1ee96a578fb56b496e0ffc053b4311942912de32627a` and `0470e1019304d84c1426ad4740c1dd57ff84c9226aecb4f9ddeee3b04a072b47`. The control generator `replay.py` has SHA-256 `dd37f6d45b6b31c762041d857a3f6a6a678a75e8c3d25b58330f7e1c3e37645f`. The earlier `inference-transport-cpu-r1` contains the pre-correction transport controls, including the telemetry sample used to verify the coordinator's resource reader. Temporary fake weights, feature files and routing inputs were removed after the controls. These two retained scratch directories and owned branch pushes are the author's external effects.

## Actual trial boundary

The reviewer operated checkpoint `0480966938291445591f69f08a13b041c073a96a` using H0 sensor candidate `1843cdb7b6279b84b539d3ca1ba7bd0affa1f7dd` and release `f5ff53945e11c8b0edf2da009c851768f77514ed`. The first window contained 284 emitted IDs before EOS in both views. Zero-based positions 13, 77, 100 and 146 changed from 399 to 395, 388 to 387, 388 to 387 and 202 to 201 respectively. The parsed visible texts and table cells matched. Token-through-EOS SHA-256s were `887ff948d9da26e2933d1d2f396dd04c865e43c7efd860aeaf3773bfc6f60705` and `d63703395cdc61e15fb86b3df73f021a56adb823ed563eb8065978023ea1554c`. All ten physical source witnesses aligned in both views, and the complete audit reproduced 72 bit-exact pools across 1,412 hooked post-consumption positions. The token differences violate H0 independently of the successful span checks. [Exact calls and independent comparison](https://github.com/jackgumpe/eledgercare/blob/823b5eedd5687188c4b6cc0d0698ea3db12d9798/docs/reviews/WP-0024/h0-r1-independent.json)

The independent operator measured 320.972 seconds summed across windows, 357.827 seconds for the sensor phase and 359.828 seconds for the guarded order. Its 173 board samples peaked at 8,500 MiB used. The guard returned and the after-inventory matched the before-inventory for the Q0 namespace, sizes and write times and the 37 model files. The original archive SHA-256 is `37670af4116f543e2d0104b5d3599d88f2e2d06fc092418ee1cf839769430fc6`. I read the review evidence without operating the device. [Archive inventory](https://github.com/jackgumpe/eledgercare/blob/823b5eedd5687188c4b6cc0d0698ea3db12d9798/docs/reviews/WP-0024/h0-r1-inventory.json) · [Return and audit receipts](https://github.com/jackgumpe/eledgercare/blob/823b5eedd5687188c4b6cc0d0698ea3db12d9798/docs/reviews/WP-0024/post-return-evidence.json)

**INCONCLUSIVE / FAILED at H0.** Real train/cal feature extraction, M1/M3 fitting, threshold selection, C1 at either horizon, blind feature extraction, blind predictions, C0 eligibility, paired scoring and advancement did not run. Actual training wall time, registry growth and lookup on real binders, cached blind inference latency, device budget qualification for the external probe, and paired donor flips, retention, coverage and safety are unmeasured. There is no measured advantage for any arm. This author did not access blind labels or customer data.

## Change inventory and handoff

All eight base-to-deliverable paths are additions in `docs/research/WP-0024/probe/`. This report is the only subsequent publication file on the author branch. [Exact author diff](https://github.com/jackgumpe/eledgercare/compare/d8ad61f6bedbf80fe183d801345ca77c735884d4...7db67283a4ffd3e7a20bb8d80499572cc7118c71)

| Files | Purpose |
| --- | --- |
| `PROTOCOL.md` | Inputs, online grammar, views, numerical conventions, budgets, calibration choices, evidence and decision boundaries |
| `online.py` | Sensor window loading, online events, candidate registry, controller, symbolic saved frames and typed output |
| `matrix.py` | Flat/PDS projections and updates, masked QR and pop, protected/summary reads, lexical anchors and calibrated output |
| `views.py` | Six causal views, Window-1 audits, directional swaps, digest checks, witnesses and telemetry |
| `run.py` | Separate fit and inference entry points, development-only calibration, output freeze and post-decision routing metadata |
| `preflight.py` | Positive and negative CPU math, gradient, causal and calibration invariants |
| `preflight-result.json`, `preflight-calibration-result.json` | Original and reconciled author CPU evidence |

The independent reviewer completed /003 on the final sources and observed H0 evidence. The next owner is `eld-coordinator` for /004 and packet closure. The private remote contained the frozen deliverable before report publication. The separate publication receipt identifies the report commit after push.
