# WP-0026 / 001 — Twin-binder custody at the blind C1 stop

| Report metadata | Value |
| --- | --- |
| Report path | `docs/agent-reports/eld-twin-custodian/WP-0026/001_2026-11-21_research_eld-twin-custodian.md` |
| Reservation | [WP-0026 / 001 at the assignment revision](https://github.com/jackgumpe/eledgercare/blob/f05dcc4c1f5ca7d7ecd82e83ca63f889369bc6fd/INDEX.md#wp-0026-w0-conditioned-twin-binder-memory-study) |
| Category, author and publisher | Research, `eld-twin-custodian`, self-published |
| Session and environment | Native Codex collaboration session `/root/w26_custody`, GPT-6 family, xhigh requested. Exact backend variant and applied effort were not exposed. Windows build 26300, PowerShell, Q0 Python 3.12.10 with `-I -B`, pypdfium2 5.15.2, PDFium 159.0.8149.0, Pillow 13.0.0. |
| UTC timestamp | 2026-11-21T21:58:39Z |
| Repository, branch and worktree | Private `jackgumpe/eledgercare`, `research/wp-0026-custody`, `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w026-custody` |
| Assignment base | `f05dcc4c1f5ca7d7ecd82e83ca63f889369bc6fd` |
| Deliverables | W0 `9ed0b70e53eb47ae2f6d47b35196f846408a0c2c`, CPU evidence `e334512cf9be6034d1ae0d4b06aabaeaaa853902`, blind commitments `38d30ab57d4e1d1f32b831a609e23eaa10c87a87` |
| Previous report and status | First custody report in this packet. Ready for independent review at the blind C1 stop. |
| Next owners | `eld-rd-reviewer` for /003 and `eld-coordinator` for /004 |

## Outcome

The fixed three-page warm-up was disjoint from all 864 development and 1,344 blind page appearances by both PNG and decoded RGB hashes. Custody materialized the single authorized 32-pair held-out family after fit and calibration freeze. Blind C1 stopped during the 14th model call. The frozen span mapper encountered four page markers where three were required. The held-out scoring key remains sealed. There is no six-view prediction freeze, C0 denominator, blind score or measured memory advantage. [Signed blind entry and budget](https://github.com/jackgumpe/eledgercare/blob/e5487a2a8a9f62eca94921131eb38997d50b62f9/docs/coordination/WP-0026/blind-entry.json)

## Deliverables and checks

The custody assignment covered the disjoint warm-up, development source and scorer checks, an exclusive held-out key and conditional scoring. All paths below are relative to `docs/fixtures/WP-0026/`. These eleven files are the complete base-to-deliverable change. The reserved report is the sole subsequent metadata addition. [Custody diff](https://github.com/jackgumpe/eledgercare/compare/f05dcc4c1f5ca7d7ecd82e83ca63f889369bc6fd...38d30ab57d4e1d1f32b831a609e23eaa10c87a87)

| Added paths | Verification and result |
| --- | --- |
| `make_w0.py`, `w0/w0.pdf`, `w0/receipt.json`, and the three `w0/*.png` named by SHA-256 in the receipt | W0 froze at 20:58:56 UTC. Each page carries one original weather sentence. Single-page rasterization and rendering the corresponding full-PDF page gave identical 2550 × 3300 RGB8 and PNG bytes at 300 dpi. Running `make_w0.py OUTPUT_DIRECTORY` again from the frozen candidate reproduced all five output files byte for byte. [Ordered raster and source receipts](https://github.com/jackgumpe/eledgercare/blob/9ed0b70e53eb47ae2f6d47b35196f846408a0c2c/docs/fixtures/WP-0026/w0/receipt.json) |
| `development-checks.json` | Replayed the predecessor's H0, training and calibration PDFs, covering 13, 53 and 55 distinct PNGs respectively. H0 source witnesses matched exactly. The synthetic scorer tests passed. The CPU probe reproduced all historical preflight fields, including 880,258 parameters per arm, zero maximum FP32 change on protected reads and a rank-four nonempty pop. [Development replay](https://github.com/jackgumpe/eledgercare/blob/e334512cf9be6034d1ae0d4b06aabaeaaa853902/docs/fixtures/WP-0026/development-checks.json) |
| `blind/receipt.json`, `blind/manifest.json`, `blind/pairs.json`, `blind/cross-pair.json` | Froze at 21:48:09 UTC. The public commitments cover 64 synthetic PDFs, 61 distinct rasters and 448 three-page windows across 32 twin pairs. The verifier matched all 61 distinct rasters to full-PDF renders, checked the first page of every binder, matched horizons and checked family construction against the custodian-private truth. It performed no scoring. [Blind receipt](https://github.com/jackgumpe/eledgercare/blob/38d30ab57d4e1d1f32b831a609e23eaa10c87a87/docs/fixtures/WP-0026/blind/receipt.json) |

All custody Python commands used `C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe -I -B`. From the worktree, the unchanged development commands were `docs/fixtures/WP-0024/check_score.py`, `docs/research/WP-0024/probe/preflight.py` with `CUDA_VISIBLE_DEVICES=-1`, and `docs/fixtures/WP-0024/verify_fixtures.py SPLIT ROOT`. H0 used the original WP-0024 custody root and wrote `--h0-witness` to the new preflight directory. Training and calibration used its `v2` subdirectory. All returned zero. The development receipt SHA-256 is `86b2185c1c675b4ab5e047454bf55602fd0e6bef1e5dd4834eafc10cc6e568da`.

The coordinator signed the materialization release at `131997ee503e98024b7d06c45a866f5038a4b333`, release SHA-256 `8dd958b4535112971d1fca05d4cdfe398d7622b33fd63af9ca9be85b1d03892b`. Custody checked the generator, scorer, H0 and development C1 gates, fit, two weights, thresholds and reviewer evidence against the signed revision before creating the new private root. With `ROOT=C:/Users/jackg/eLedgerCare-Speed/WP-0026/custody/v2` and `RELEASE` the matching JSON in its parent directory, both commands below returned zero, with empty stderr. [Materialization release](https://github.com/jackgumpe/eledgercare/blob/131997ee503e98024b7d06c45a866f5038a4b333/docs/coordination/WP-0026/blind-custody-release.json)

| Command after the interpreter flags | Start UTC | Elapsed wall time on CPU | External log SHA-256 |
| --- | --- | ---: | --- |
| `docs/fixtures/WP-0024/corpus.py blind ROOT --release RELEASE` | 21:47:27.346 | 8.485 s | `3fe2e67fce7835320d9b10f5a7f1cfc7b0dc6cd21c58b47e59376e34753324e3` |
| `docs/fixtures/WP-0024/verify_fixtures.py blind ROOT` | 21:47:35.836 | 11.453 s | `4ccbab35c255d6241659655ff1f2ffaac023a9a9f2120cfd72173a45c2d8a0cd` |

Public receipt SHA-256 is `647ad65aa2a3787931c0b7af057432492fb8de8fc282c9f9a87304f28d8b1953`. The published truth commitment is `a5c79547fb086b9d160fba1ee1350c1dce2464a9857e6ef44e6bb0c75e5945dc`. Persistent custody output under `C:/Users/jackg/eLedgerCare-Speed/WP-0026/custody` consists of preflight outputs, release and execution receipts, source PDFs and PNGs, and the separate private entropy and truth. Git received the four opaque blind files. The scoring key was never transmitted. Custody made zero GPU calls.

## Budget, failure and disposition

The coordinator's precommitted within-pair schedule allowed reuse only at matching window positions within each twin pair. Its budget was 28 uncached C1 calls followed by 248 calls conditional on acceptance, for 276 physical calls across 448 logical windows. A separate CPU-only invocation of the inherited unrestricted planner counted 50 distinct triples across all 32 twin pairs and projected 67 physical calls using cross-pair reuse. That estimate played no role in the signed device schedule. [Blind C1 release](https://github.com/jackgumpe/eledgercare/blob/e5487a2a8a9f62eca94921131eb38997d50b62f9/docs/coordination/WP-0026/blind-c1-r1-release.json)

Custody inspected the returned operator files in `C:/Users/jackg/eLedgerCare-Speed/WP-0026/review/runs/blind-c1-r1`. The signed plan SHA-256 was `12a683f1d0562206f8fe4f9ea61c163790e374ef8a23204b2d7905cb0c2ae238`. The sensor error receipt lists 14 started tags and 13 verified tags. At `k0014`, the 7,171-byte native return contained four literal page markers, with the first at offset zero. The unchanged mapper raised `Expected three grounded native pages`. The supervisor recorded exit code 1. Its failed return and the native bytes remain available for the non-author review. [Frozen span-mapping source](https://github.com/jackgumpe/eledgercare/blob/4a867f91d47c12e49e78c2381d5bc4661c6927fa/docs/research/WP-0024/sensor/spans.py)

| Relative operator evidence | SHA-256 |
| --- | --- |
| `sensor/k0014/native.json` | `ce9d03a8d73ecf4366b96bc2dbbf9e129f5a2ca30265876a16b17c07cc20b169` |
| `sensor/error.json` | `74fb0291ff5f25b0c9f58a54727ce00654ac601ade4799e66cd454653a6a18bf` |
| `process.json` | `f63f81c4951b05f1fa10f35165e5f4ed292b24a7184f7267de036f2687b3a548` |

The incomplete C1 phase closed held-out extraction, prediction and scoring. Custody requests independent verification of the public commitments and the stop evidence. The coordinator owns the packet disposition.
