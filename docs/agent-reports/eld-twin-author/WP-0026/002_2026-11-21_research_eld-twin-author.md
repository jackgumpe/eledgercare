# WP-0026 /002 — Conditioned acquisition, fitted probes and blind C1 stop

Blind C1 stopped on scored call **k0014**. The unmodified model emitted four page markers for a three-page input and reached EOS. The frozen parser required three grounded pages. Thirteen earlier blind captures were sealed. The incomplete split yielded zero blind predictions and no held-out comparison among the six views.

| Report metadata | Value |
|---|---|
| Report / reservation | `docs/agent-reports/eld-twin-author/WP-0026/002_2026-11-21_research_eld-twin-author.md`, WP-0026 /002, research. [Reserved row and assignment](https://github.com/jackgumpe/eledgercare/blob/f05dcc4c1f5ca7d7ecd82e83ca63f889369bc6fd/INDEX.md#wp-0026-w0-conditioned-twin-binder-memory-study) |
| Author and publication | `eld-twin-author`, native Codex session `/root/w26_author`, self-published. Requested xhigh. Backend and effective effort were not exposed. Publication UTC 2026-11-21T22:00:20Z. |
| Repository and checkout | Private `jackgumpe/eledgercare`, branch `research/wp-0026-acquisition`, `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w026-author` |
| Base, source and deliverable | Reservation `f05dcc4c1f5ca7d7ecd82e83ca63f889369bc6fd`, acquisition `345309af8bbbcb5831d885197c5f09ee9edacfef`, CPU study `e6f41a7d3580894a8d6aefdb8704d5d52e2fbb7d`, published fit `6d79c24364ba10a1d9bfa4c72c837e2f216cf4bc`. |
| Runtime | Windows, pinned Q0 Python 3.12.10 with `-I -B`, PyTorch 2.13.0+cu130. Native BF16 B=1 extraction. CPU FP32, one intra-op/inter-op thread, deterministic algorithms and CUDA hidden for the external probes. |
| Status and next owner | First author report in WP-0026. Ready for review at the stopped boundary. `eld-rd-reviewer` owns independent /003 and `eld-coordinator` owns final disposition in /004. |

## Acquisition

The study asked whether an external learned stack carries earlier ledger bindings into an identical suffix. Each loaded worker first completed one excluded stock W0 using the original native generation path. Its receipt bound the disjoint three-page fixture, all 827 expanded prompt IDs, observed EOS, model-load ID, GPU UUID, lease and signed plan. The stock model constructed a fresh decode cache on every invocation. W0 supplied no feature or score to the study. All workers used checkpoint `0480966938291445591f69f08a13b041c073a96a`, sensor source `1843cdb7b6279b84b539d3ca1ba7bd0affa1f7dd` and W0 fixture SHA-256 `7c509b3514daf75854b2b719cc7a94d44175c5af9fdcbae8ef4df0c68ec812e7`. The coordinator issued the leases and the independent reviewer operated the GPU. [Acquisition worker](https://github.com/jackgumpe/eledgercare/blob/345309af8bbbcb5831d885197c5f09ee9edacfef/docs/research/WP-0026/worker.py)

All eight H0 pairs, including the first scored ordinal, matched through EOS and in source metadata across the complementary SSSSHHHH / HHHHSSSS schedules. The reviewer reconstructed 72 pools and verified 1,412 consumed positions. Development C1 accepted 28 true calls and all 12 duplicate groups, covering one complete 12-page pair and one complete 30-page pair. A further 11 training and 29 calibration extractions resolved 140 logical windows per split to 27 and 29 physical providers, respectively. The split-specific comparison of cached and uncached decisions also passed at the frozen fit. [H0 evidence](https://github.com/jackgumpe/eledgercare/blob/1d643452ba2b88e6bd54d6d609112ddc743b1cc9/docs/reviews/WP-0026/h0-live.json) · [Train C1 evidence](https://github.com/jackgumpe/eledgercare/blob/039b68997b7566de05c1f6cdd5a0e5ab23ace17a/docs/reviews/WP-0026/train-c1-live.json) · [Independent fit and decision bindings](https://github.com/jackgumpe/eledgercare/blob/e5487a2a8a9f62eca94921131eb38997d50b62f9/docs/coordination/WP-0026/blind-entry.json)

| Resident process | Scored starts / sealed | Load s | Excluded W0 s | Sealed scored inference s | Worker phase s |
|---|---:|---:|---:|---:|---:|
| H0 p1 | 8 / 8 | 22.388 | 28.086 | 176.653 | 229.009 |
| H0 p2 | 8 / 8 | 21.420 | 27.038 | 157.934 | 208.405 |
| Train C1 | 28 / 28 | 20.725 | 24.737 | 481.453 | 532.828 |
| Remaining train | 11 / 11 | 24.608 | 25.183 | 226.642 | 278.851 |
| Calibration | 29 / 29 | 20.596 | 24.754 | 603.041 | 654.270 |
| Blind C1 | 14 / 13 | 22.015 | 25.848 | 246.986 | 312.547 |
| **Total** | **98 / 97** | **131.751** | **155.646** | **1,892.710** | **2,215.910** |

Six successful once-only W0 calls and 98 scored starts give 104 actual native calls. Worker phase time includes k0014 up to the reported exception. That call has no duration receipt, so its individual inference time is unavailable. Worker phase sums exclude idle gaps and CPU fitting. Run evidence lives beneath `C:/Users/jackg/eLedgerCare-Speed/WP-0026/review/runs/<process>/sensor`. [Development cost accounting](https://github.com/jackgumpe/eledgercare/blob/e3e3e9afd5de35bcb8ea5b2af0559d3025a5aefa/docs/coordination/WP-0026/development-costs.json)

## Matched fit and calibration

I executed one actual fit using the signed train/cal acquisition plans and their respective development truth. The original WP-0024 rules fixed the six-epoch optimizer budget and seed 2401. Fit wall time was 10.220 s including validation and routing, with 10.002 s in the CPU child. Each model had 880,258 parameters, 12 binder steps and 44 supervised fields in each of six epochs. All 11 parameter tensors in each model received a nonzero gradient. Four ambiguous binders and four binders lacking a unique target were skipped per epoch. [Exact release](https://github.com/jackgumpe/eledgercare/blob/e3e3e9afd5de35bcb8ea5b2af0559d3025a5aefa/docs/coordination/WP-0026/fit-release.json) · [Executed child command and input hashes](https://github.com/jackgumpe/eledgercare/blob/6d79c24364ba10a1d9bfa4c72c837e2f216cf4bc/docs/research/WP-0026/fit/bound.json)

| Probe | Training s | Weight SHA-256 | Frozen similarity / margin |
|---|---:|---|---|
| M1 | 2.4229395 | `e2420949c0990992fae61b42280617bedd95dfa7013ce25ff52c8fd760c0f291` | 1.0 / 0.1 |
| M3 | 2.4101639 | `391b19e5629faf62b2f6ae6614bd18f91ba8e7c112a78dc191cdd6e602d10031` | 1.0 / 0.1 |

Both selected settings yielded zero answerable postings, zero silent errors and two fully correct pairs on the ten calibration pairs. Across all 24 threshold settings, M1 had 22 with no postings and M3 had 23. Every answerable posting at the other settings was silently wrong. The frozen tie-break selected the strictest similarity threshold and margin among the equally safe settings. The weight files, full grids, optimization histories and fit receipt `e664109765b0482cb7d330c825c4c9dbbe3b8b8c63e17a991fe6ab14f42925b2` were verified on the private remote before blind execution. [Frozen fit and weights](https://github.com/jackgumpe/eledgercare/tree/6d79c24364ba10a1d9bfa4c72c837e2f216cf4bc/docs/research/WP-0026/fit)

## Terminal evidence and limits

Blind C1 plan SHA-256 `12a683f1d0562206f8fe4f9ea61c163790e374ef8a23204b2d7905cb0c2ae238` ran on device candidate `4a867f91d47c12e49e78c2381d5bc4661c6927fa`. All development device phases had run at `9c02c9fae465dc1d1322a81c23eb3af45bbb0aff`. At blind C1 call 14, model ordinal 15, the native return recorded 122 emitted IDs and EOS 1 at step 122. It reported three expected pages, four output pages, four page markers and prompt length 827. The worker preserved the native return before the frozen span mapper raised `ValueError: Expected three grounded native pages`. Only `native.json` exists in that slot, SHA-256 `ce9d03a8d73ecf4366b96bc2dbbf9e129f5a2ca30265876a16b17c07cc20b169`. The process error SHA-256 is `74fb0291ff5f25b0c9f58a54727ce00654ac601ade4799e66cd454653a6a18bf`. The 13 complete captures and fourteenth native return were preserved without retry. [Frozen blind release](https://github.com/jackgumpe/eledgercare/blob/e5487a2a8a9f62eca94921131eb38997d50b62f9/docs/coordination/WP-0026/blind-c1-r1-release.json)

Blind C1 did not qualify. The remaining 14 planned uncached calls and 248 further feature calls did not run. Blind six-view inference, prediction freeze, C0 eligibility, full and eligible-subset pair scoring, donor/receiver comparisons, safety vetoes and resource-qualified arm selection are unmeasured. There are zero blind predictions. Calibration alone cannot establish a held-out model comparison or a replication recommendation. I never read the blind truth.

## Verification and deliverables

The Python executable for each command below was `C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe`, invoked with `-I -B`.

| Author check | Executed check and observation |
|---|---|
| Exact source and archival acquisition | `docs/research/WP-0026/preflight.py` at `345309af` replayed both eight-call orders and rejected invalid warm EOS, missing hidden bytes, wrong order, changed prompt and overlapping W0. Pooled-only readback and a differing duplicate pool were exercised. Zero Baidu loads. |
| Inherited CPU checks | `docs/research/WP-0024/probe/preflight.py` and `docs/research/WP-0024/sensor/test_capture_cpu.py MODEL_PATH`, with CUDA hidden. All 11 calibration cases, matched parameters, gradients, QR/rank, symmetry and six-view checks passed. Sensor replay reconstructed 3 and 33 archive spans and verified causal pooling. Receipts reside in author scratch `preflight-r1`. |
| Real H0 and development routes | Called `worker.validate_plan` and `images_for` on both signed H0 plans, verifying three 2550×3300 W0 RGBs each time. After return, compared all eight through-EOS and metadata file pairs byte-for-byte. Checked the frozen probe tree against `7db67283a4ffd3e7a20bb8d80499572cc7118c71` and physically reverified train/cal W0, metadata and pool provenance. |
| Actual fit and pre-blind freeze | Ran `docs/research/WP-0026/study.py fit` with the exact plan/truth paths and digests in the release and the fresh `WP-0026/author/fit-r1` destination. Exit 0. The nine published fit artifacts were byte-equal to the originals. The six-file output-freeze helper received synthetic success/duplicate controls only. |
| Blind stop | Inspected the error, native terminal metadata, recorded hashes, and filenames at k0014. Independent terminal acceptance is reserved to /003. |

Author changes were limited to `docs/research/WP-0026/{worker.py,preflight.py,study.py}`, `fit/{M1.pt,M3.pt,M1-development.json,M3-development.json,fit.json,bound.json,process.json,train-transport.json,cal-transport.json}` and this subsequent report. External author writes used only `C:/Users/jackg/eLedgerCare-Speed/WP-0026/author`. No production application, checkpoint, scorer or historical evidence changed. The source and fit commits were pushed on the owned branch without force. The report publication SHA is supplied to the coordinator after the report commit. [Author diff](https://github.com/jackgumpe/eledgercare/compare/f05dcc4c1f5ca7d7ecd82e83ca63f889369bc6fd...6d79c24364ba10a1d9bfa4c72c837e2f216cf4bc)
