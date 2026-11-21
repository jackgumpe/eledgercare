# WP-0024 / 001 — Twin-binder custody at the H0 stop

| Report metadata | Value |
| --- | --- |
| Report path | `docs/agent-reports/eld-twin-custodian/WP-0024/001_2026-11-21_research_eld-twin-custodian.md` |
| Reservation | WP-0024 / 001 in [INDEX at the assignment base](https://github.com/jackgumpe/eledgercare/blob/d8ad61f6bedbf80fe183d801345ca77c735884d4/INDEX.md#wp-0024-counterfactual-twin-binder-baidu-memory-trial) |
| Category, author and publisher | Research, `eld-twin-custodian`, self-published |
| Actual session | Native Codex collaboration session `/root/t24_custody`, GPT-6 family. Requested effort xhigh. Exact backend variant and applied effort were not exposed. |
| Execution environment | Windows 11 build 26300, PowerShell, read-only Q0 Python 3.12.10 with `-I -B`, pypdfium2 5.15.2, PDFium 159.0.8149.0 and Pillow 13.0.0 |
| Timestamp | 2026-11-21T18:01:07Z |
| Repository, branch and worktree | Private `jackgumpe/eledgercare`, `research/wp-0024-twin-custody`, `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/twin24-custody` |
| Assignment base | `d8ad61f6bedbf80fe183d801345ca77c735884d4` |
| Final custody deliverable | `6b36c4ed6f56b408edd0e15451b64504b0e2f465` including both fixed-scorer replay artifacts. Final executable scorer revision `e6c1abaed36a379780084be826c5fd0afaf3132b`. |
| Previous report | First report by this author in WP-0024 |
| Status and next owners | Ready for review at the H0 hard stop. `eld-rd-reviewer` owns /003 and `eld-coordinator` owns /004. |

## Outcome

H0 failed on the two public development binders. The independent reviewer found byte-identical emitted token IDs through EOS in seven of eight stock/hooked window comparisons. The first binder’s W1 emitted four different bounding-box coordinate tokens at zero-based indices 13, 77, 100 and 146. They changed from 399 to 395, 388 to 387, 388 to 387 and 202 to 201. The three parsed page texts and table rows agreed in that window. All ten custody witnesses matched their literal and location in both arms. Exact token equality was a separate entry requirement. The reviewer’s H0 archive records 16 real calls and 357.827 seconds for the complete phase. This author inspected the retained evidence and made no model calls. [Independent replay](https://github.com/jackgumpe/eledgercare/blob/823b5eedd5687188c4b6cc0d0698ea3db12d9798/docs/reviews/WP-0024/h0-r1-independent.json) · [Run inventory](https://github.com/jackgumpe/eledgercare/blob/823b5eedd5687188c4b6cc0d0698ea3db12d9798/docs/reviews/WP-0024/h0-r1-inventory.json)

The blind corpus was never materialized, extracted or scored. C1, real training and calibration, blind predictions, C0 capture rates, model comparisons, masking/swap outcomes on actual binders and any advancement decision based on effects were unreached. Custody has no measured PDS-versus-stack result.

## Objective, inputs and boundary

Custody owned disjoint synthetic families, opaque public sensor plans, separately held answers, a 32-pair matched blind design and scoring. The corrected generation and scoring rules were published before any blind data. The reviewer owned independent device execution. The coordinator retained the GPU release and stop decision. [Assignment](https://github.com/jackgumpe/eledgercare/blob/d8ad61f6bedbf80fe183d801345ca77c735884d4/docs/coordination/WP-0024/assignment.md) · [Custody protocol](https://github.com/jackgumpe/eledgercare/blob/6b36c4ed6f56b408edd0e15451b64504b0e2f465/docs/fixtures/WP-0024/protocol.md)

| Delivered split | Pairs / binders | Page appearances / distinct PNGs | Custody manifest SHA-256 |
| --- | --- | --- | --- |
| Public H0 | 1 / 2 | 24 / 13 | `20cb3a35c03e752e4f83a455278dbf558bb9712163057901110069f2ec23bf4e` |
| Revised training | 10 / 20 | 420 / 53 | `63bf807667495ec8b18f27d163bc6592a49369636cdb6a38aed0f23e27383f2b` |
| Revised calibration | 10 / 20 | 420 / 55 | `e41a6aa2f389fc8ca8fae294afbde159fd866d9c4cdef3299ce7bcab324c0efa` |

Each source is a 612 × 792 point PDF. Each RGB raster is 2550 × 3300 pixels. The H0 PDFs have SHA-256 `675367788d2b872511d05b704b98069e8b636d02d07d78095cc4bbeab3e63d5b` and `3989e9e2d5d199e4c10b074e5e495a798c95a9bf2a4f24b2f37e24ea0eb52dbd`. The committed H0 glyph witness has SHA-256 `dfb55b56833599f111eb29e2b3d4b8a7de9eab13b8caae277e09c9ba60271989`. The reviewer's bound runtime plan has SHA-256 `0bf358c54fc97f32ca213d9a1dd10cfb2838f42f7c5dcded1625c0cca1fd2f89`, sensor source `1843cdb7b6279b84b539d3ca1ba7bd0affa1f7dd` and model revision `0480966938291445591f69f08a13b041c073a96a`. [H0 source receipts](https://github.com/jackgumpe/eledgercare/blob/6ae4b1c81146d939da3cc2ecf244cdd9424f6350/docs/fixtures/WP-0024/h0/receipt.json)

## Changes, corrections and checks

All paths in the base-to-deliverable diff are additions under `docs/fixtures/WP-0024/`. [Complete custody diff](https://github.com/jackgumpe/eledgercare/compare/d8ad61f6bedbf80fe183d801345ca77c735884d4...6b36c4ed6f56b408edd0e15451b64504b0e2f465)

| Paths relative to the fixture directory | Purpose and verification |
| --- | --- |
| `corpus.py`, `verify_fixtures.py` | Vector construction, custodian-private keys, individually hashed PDF/PNG/RGB data, exact source geometry and matched-horizon checks. Early execution exposed an unsupported PDFium page context manager and a floating-point ceiling producing 3301 rows. Explicit page closure and the adjacent lower render scale produced exactly 3300 rows. |
| `h0/`, `train/`, `cal/`, `v2/train/`, `v2/cal/`, each containing `manifest.json`, `pairs.json`, `cross-pair.json`, `receipt.json` | Bind every source and cached-feature reuse candidate before execution. H0 retains its original pair. The original train/cal folders preserve superseded inputs. Revised development has physical two-row candidate cards and opposite true T3 outcomes with identical final pages. Each development split includes two matched T3 source cases to cover both outcomes. |
| `h0/source-witness.json` | Ten literal and PDF glyph-coordinate witnesses covering owner, unit, header, ordinary row and final charge for both binders. |
| `protocol.md`, `score.py`, `check_score.py` | Key separation, common C0, same-denominator six-arm attribution, controls, full and component scoring, tied-owner summary alternative, per-target safety vetoes, horizon/abstention accounting and both donor directions. |
| `c0-boundary-replay.json`, `c0-attribution-replay.json` | Retain actual before/after CPU records. A child-only declaration initially passed C0 incorrectly. The corrected scan stops on the first child heading. A later audit made an exposed M1 acquisition failure visible while retaining genuine zero-control evidence and receiver-side swap attribution. Neither test reads a blind key. |

The H0 source and witnesses were verified using `verify_fixtures.py h0 ROOT --h0-witness h0/source-witness.json` against all 24 PDF page appearances. On corrected generator `3e6adf11d02bc116873b2c7ebac0fab9b8acaea7`, `corpus.py train ROOT/v2` and `corpus.py cal ROOT/v2` generated the revised plans. `verify_fixtures.py train ROOT/v2` and `verify_fixtures.py cal ROOT/v2` checked every distinct raster plus each binder’s first page against the full source PDF, source geometry, horizon equality, printed arithmetic and opposing-status suffix collisions. All commands used the Q0 Python with `-I -B`. Source verification passed. Separate split-local cross-pair commitments covered 27 unique ordered training windows and 29 calibration windows. The four-case blind design necessarily aliases one earlier layout contrast with T3 status, limiting any anticipated causal claim even had H0 passed. [Revised development evidence](https://github.com/jackgumpe/eledgercare/tree/7ae03a8fc60719f162552a4ccf218227fcb0f92a/docs/fixtures/WP-0024/v2)

The final `check_score.py` CPU regression passed, including synthetic gate failures, a formerly correct posting changed to abstention, component errors, two donor directions, zero/suffix controls and declared resource ceilings. A supplementary test showed three usable paired summary gains, then two after a loss that appears in both debit categories, then one after a diagnostic-only abstention. The reviewer independently replayed the parent-scope fix, six-view attribution, matched summary accounting and candidate/swap checks. These are implementation checks over manufactured observations. [Parent-scope review](https://github.com/jackgumpe/eledgercare/commit/ef6b68b8a0a6347a7ba393cbe77bba69ba4fe91b) · [Six-view review](https://github.com/jackgumpe/eledgercare/commit/ccfebec4975c1b9ea4fb8cbc3ab1a5622680fb1b)

## External effects and handoff

Persistent local output is confined to `C:/Users/jackg/eLedgerCare-Speed/WP-0024/custody` (`ROOT` above). It contains the H0 PDFs and rasters, superseded and corrected public development plans, separate development keys and the visual check. At publication it contained 336 files totaling 17,899,298 bytes. The revised public/private roots contained only training and calibration. The blind-release and scoring commands were never invoked. External writes also include normal, non-force pushes to this author’s reserved branch on the private repository. The sole post-deliverable change is this report under its reserved path.

The independently documented H0 stop governs this handoff. Custody has completed its released work. The coordinator receives the verified report publication SHA separately after push.
