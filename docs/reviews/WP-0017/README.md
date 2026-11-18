# WP-0017 independent escrow tooling (eld-rd-reviewer)

Working notes for reservation 003. This is **not** the canonical report. Sequence 003 is reserved for the final independent disposition at `docs/agent-reports/eld-rd-reviewer/WP-0017/003_2026-11-18_review_eld-rd-reviewer.md`. It will be written only after the actual terminal outcome of the gate.

- **Author:** eld-rd-reviewer. A fresh Antigravity CLI session on Claude Opus 5.5 with High effort, launched by the coordinator's `runrole.py review` (`claude-opus-5-5-high`, `--effort high`). The applied backend configuration is not otherwise exposed.
- **Branch and worktree:** `review/wp-0017-escrow`, `eledgercare-worktrees/ablation-review`, base `1e75ebe25814227ef6450913bce301ba9e2ef0f2`.
- **Release:** the assignment and specification were committed at `0d50f40b6520604c2c92f31d3afd74d097149fd5` (specification.pdf SHA-256 `6d9de7f1…89cd`).
- **Independence:** I authored none of the WP-0017 design, fixtures, engine switches or runtime. Nor did I author the WP-0016 candidate. I dispatch no other agent. This role ID wrote the WP-0016 escrow tools, which I use only as reading material. The frozen scorer and title rule are third-party bytes pinned by SHA-256.
- **Hardware:** CPU only. Torch, CUDA and the model are never imported or loaded. GPU work waits for a coordinator-signed, SHA-pinned outer lease.

## Exposure state

| Item | State |
| --- | --- |
| H/A truth | Not opened. `common.guard_path` refuses any `truth.json`, `details.json`, `escrow-stage2.json` or `g0-quality-return.json`, and any Packet B path. |
| WP-0016 score outputs | Not opened by any tool. One disclosure: early in the session, an exploratory `Select-String` for `417`/`291` over `docs/coordination/WP-0016/*.json` printed four matching lines from the committed `escrow-stage2.json` and `g0-quality-return.json`. They were two aggregate CER values and two `edits_saved_per_extra_s` values, figures already published in WP-0016/003 and 004. No reference text, path detail or score-detail key was displayed. |
| WP-0016 predictions | Read for the four A arms (native and carbon_bf16 × AB and BA) and for windows 019 and 037 only. Every file read was first re-hashed against the committed blind inventory. Only token pieces at differing positions and in the public identifier spans are published. |
| Packet B | Never resolved, read or listed. |

## A1 prefix audit (frozen)

- **Tool:** `prefix_audit.py` and `common.py`, committed at `61c2734069e5fef32ec5c80c065504d9f62de02a` before the evidence was produced.
- **Evidence:** `evidence/A1-prefix-audit.json`, SHA-256 `16eca676114e847059503290b3c4a620eb1625769dd7f3a3e0a39ab252d263b3`.
- **Result:** 180 checks, 0 failures, and all 12 claims under audit agree.
- **Command:** `python -I -B docs/reviews/WP-0017/prefix_audit.py --out docs/reviews/WP-0017/evidence/A1-prefix-audit.json`, using the Q0 interpreter 3.12.10. The secondary `tokenizers` 0.21.4 cross-check runs only when that library is importable. With system CPython it is skipped (176 checks, 0 failures).

| Fact | Independently rebuilt value |
| --- | --- |
| Inventory binding | Both run trees (all files, cache included) equal `G0-blind-inventory.json` at `6f32732` (SHA `366bf5eb…`). Plans equal `g0-plans.json` at `be8c7f1`. |
| RGB | Pages 19–21 and 37–39 in all four arms equal the pinned A raster inventory `54ac6864…`. |
| Repeatability | Each mode is token-identical across AB and BA in both windows. |
| window-019 | LCP = **417**. All of page 19 (125 tokens) and page 20 (255 tokens) are identical, plus the first **37** tokens of page 21. The first difference is at window index 417, page-21 index 37, a content token: native `342 ' I'`, carbon `223 ' '`. |
| window-019 span | Common line prefix `[1124 'In', 64276 'spection']`. Spans: native `[342 ' I', 3019 '08', 49 'O', 19 '1', 15 '-', 21895 '388']` = `" I08O1-388"`; carbon `[223 ' ', 6924 '108', 49, 19, 15, 21895]` = `" 108O1-388"`. The identifier step is the window's first difference. Page 21 is position-aligned (121 = 121 tokens) and has 5 differing positions: the 2 identifier tokens plus geometry 235→234, 292→291, 259→260. |
| window-037 | LCP = **7**. The first difference is a block-geometry token: native `17979 '291'`, carbon `16234 '290'`. Page 37 is position-aligned (128 tokens) with 8 differences: 6 geometry and 2 content. Pages 38 and 39 then differ in length (141 vs 135, 127 vs 128). |
| window-037 span | Both arms have common line prefix `[1124, 64276, 223 ' ']` at page index 41. Spans: native `[26 '8', 90169 'OI', 553 '10', 15 '-', 30591 '774']`; carbon `[1892 '80', 43 'I', 553, 15, 30591]`. The free-running prefixes up to index 41 differ (native `0df32b06…`, carbon `656b1fdd…`). |
| Canonicality | Every emitted line span equals the pinned tokenizer's canonical encoding of its own text. |
| A1 replay targets | window-019: native 501 tokens `795dd68a…`, carbon 501 `6dfc195c…`. window-037: native 396 `2fe3906d…`, carbon 391 `aab3cbf2…`. |
| Two-window clock | Sum of `engine_end_ns − engine_begin_ns`: native 100.56 s (AB) and 106.26 s (BA); carbon 89.31 s (AB) and 87.30 s (BA). This reproduces the assignment's 87.30–106.26 s. `time_s` gives 86.67–105.71 s. |

**Disclosed claim translations, revised after scratch dry runs and before freezing:**
- **C8.** Carbon's "6 other diffs" is ambiguous. The first reading (7 geometry diffs) disagreed. The recorded reading is "6 besides the identifier pair", and both readings are noted.
- **C11.** The first clock tried was `time_s`. The recorded clock is the engine span, and all four clock definitions are published.
- No observation was changed. Only the expected-value translation of the prose claims changed.

Prefix digests use SHA-256 of a compact JSON token-id list such as `[128827,128828,…]`.

## Frozen CPU tooling (no WP-0017 output existed when it was frozen)

The tools were committed at `9a1fbb9258566765342a812380fb0e8be9afe16d`. A later operator correction is at `64583bf1a561aadd24f345ac9a943d33737dd0d9`. The rules are in [decision_procedure.md](decision_procedure.md).

| File | Stage | Purpose |
| --- | --- | --- |
| `escrow.py` | 0 (A1/A2/A3) | Content-agnostic blind inventory. Hashes every file, binds release/plan/operator digests, records process outcomes only, and provides `verify_unchanged`. |
| `operate.py` | GPU stages | Digest-verified launch of exactly `<lease.py> <release> <digest>`. Low-frequency reviewer `watch`/`monitor`/`status`. Never retries, never kills. |
| `prefix_audit.py` | A1 pre-run | The frozen audit described above. |
| `a1_decide.py` | A1 | Binding to the audit, replay gate, readings, single/pair attribution, 037 cascade classification, margins, local speed and advisory candidate ranking. |
| `a2_stoploss.py` | A2 | Reversed-order check for the three arms. Separate-process `score.py`. Per-order stop-loss: 0 new unflagged criticals, positive Carbon saving, retention ≥ 0.60, minimum saving greater than both spreads. |
| `a3/derive.py` | A3 | Mechanical derivation of the WP-0016 G0 verifier/scorer at `1e75ebe`. Only enumerated literal substitutions are applied (carbon_bf16 → carbon_surgical, the A3 plan pin, the repo depth, kind strings). |
| `a3_gate.py` | A3 | Combines stage-2 G0 with static-cache == 0, the external board peak ≤ 10,000 MiB, and an A saving that is positive and exceeds both spreads. |
| `scorecard.py` | A3 (non-gate) | Net repairs, Windows recovery per second, malformed headers and the flags-false lock. Simulates margin flags only from a predeclared threshold file. |
| `selftest.py` | CPU | 40 tests. A1 scenarios are built from the real WP-0016 window token sequences: single culprit, replay failure, pair request/resolution, interaction-only, site split, ranking and binding failures. Also covers A2/A3 rules, scorecard, inventory, guard and operator. |

**CPU evidence:**

| Evidence file | Interpreter / tool commit | Result |
| --- | --- | --- |
| `evidence/cpu-selftest-q0.json` | Q0 venv, tools at `9a1fbb9` | 40/40 |
| `evidence/cpu-selftest-syspython.json` | System CPython, tools at `9a1fbb9` | 36/40. The 4 operator tests fail because breakaway is refused (WinError 5). |
| `evidence/cpu-selftest-q0-r2.json` | Q0 venv, tools at `64583bf` | 40/40 |
| `evidence/a3-trial-derivation.json` and `evidence/a3-trial-derived-selftest.json` | Derivation against the WP-0016 plan pin (identity binding), then the derived WP-0016 selftest | All synthetic and public-dev cases pass with `carbon_surgical` in place of carbon_bf16. The trial directory was deleted. A3 derivation will be rerun against the real A3 plan record. |
| (reproduction, not committed) | Q0 venv, tools at `9a1fbb9` | Reran the prefix audit; content identical to the frozen evidence apart from `created_utc`. |

### Operator boundary observed

[operator-survival-probe.json](evidence/operator-survival-probe.json) documents what happened when a dummy 25-second executor and monitor were launched from a tool command that then finished. Both ended before writing their first file.

- Under this Antigravity CLI, processes cannot break away from the outer job. The system CPython is refused outright. The venv redirector's flag acceptance is ineffective.
- I made no attempt to escape the job by other means.
- **Consequence:** a reviewer-operated GPU lease must run inside a CLI turn that stays alive until the lease returns (a background tool task plus timers), or root starts the executor in its own context and I only `watch`/`status`.
- `operate.py` now fails closed when breakaway is refused.
