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

## Synchronization with the published design (second CLI turn, before any GPU measurement)

The coordinator asked me to synchronize A1 normalization and pair selection with Astra's design at `1fad21c3817be175628992a559e3947d5a88952a`, which is merged on integration. The relevant inputs are `PROTOCOL.md` `fe915bba…` and `rules.py` `678f27d5…`, plus `WP-0017/coordination/roles-interface.txt` and the A1 manifest `a1-inputs.json` `e7f47d14…`. No WP-0017 model output existed or was read.

[decision_procedure.md](decision_procedure.md) was rewritten. The first version stays at `9a1fbb9`. What changed:

| Area | Before (`9a1fbb9`) | Now |
| --- | --- | --- |
| Field reading | Searched for the public strings. | Unique structural locator (site page, raw block ordinal 1, header type, label `Inspection `, byte offset 11). It never searches for either value. Missing, moved, malformed and abstained fields are counted separately. |
| Statistic | Probe gap. | Full-span D = ℓ(native) − ℓ(Carbon) on the frozen native history (path effect), plus the 037 history-shift effect. |
| Pair eligibility | Any exact change in a shift. | An anchored, actually emitted ID change, or a repeated same-sign forced change > E_w = max(1e-5 nats, endpoint repeat noise). Re-probes are requested only when needed. |
| Selection | Same rule. | A single removal that restores both fields decides, even if the addition alone did not flip both. Ordering is fewest removed, then smallest ordinary seconds, then switch order. Sufficiency (additions) is kept separate from necessity (removals). A unique-cause label is given only under strict conditions. |
| Speed | Combined. | Free (uninstrumented) and probed (instrumented) timing are reported separately. |
| Labels | None. | S3 with S0 off must carry a deferred-callback label. S1c's routed/shared/layer-0 scope is the engine's contract, checked through its counters. |
| A1 infrastructure error | Not separated. | Recorded as `INFRASTRUCTURE_ERROR`; it needs cause inspection and a new source binding, and is never treated as an engine outcome. |
| A2 | Reversal only, frozen view. | Exact AB = native/full/surgical and BA = surgical/full/native. Six windows per arm, identical warm-ups, frozen and title views, zero new silent criticals in all four comparisons, strict spread comparison. Dev key pinned at `dfdf62cb…`. |
| A3 | Static cache only. | Static cache, or a dynamic-only label when S2 is off. Margin flags use the predeclared 0.125-logit gap. |

`rules.py` is loaded from its blob only to cross-check `rank_restorations`, `qualifying_pairs` and `a2`. A disagreement is recorded as a failure.

## GPU execution method: reviewer command plus coordinator carrier

My observed limitation (no breakaway from the CLI job) is resolved without giving the coordinator operational discretion.

**Steps for each release:**
1. Root publishes `docs/coordination/WP-0017/<name>-release.json` and its signed digest, issued with `issue_lease.py` `10c14e1b…`.
2. I run `command.py review --name <name> --sha256 <digest> --stage <A1|A2|A3>`. This is an independent check of:
   - the release, the executor `device_lease.py` `a25adcab…` and the carrier `review_command.py` `c5596d0e…`, all pinned at `d17669e`;
   - the coordination files, the candidate worktree (HEAD, clean, source digests) and the plans;
   - that output roots are new, that inputs are public, and that the GPU UUID and stage ceiling are correct.
3. Only if all of those pass, I run `command.py issue`. It writes `docs/reviews/WP-0017/commands/<name>.json` with `release_name`, `release_sha256`, `executor_sha256`, `candidate`, `operator=eld-rd-reviewer`, `action="execute once"` and `stage`, plus the reviewer session and orders. I commit and push it to `review/wp-0017-escrow`.
4. The passive carrier, an eld-coordinator Windows process running `review_command.py`, checks that the pushed object equals the signed release and executes only that pinned lease once. It writes its own `received.json` and `return.json` under `WP-0017/coordination/carrier/<name>`.

**Identities:**
- **Operator:** eld-rd-reviewer, Antigravity CLI, Claude Opus 5.5 High, conversation `5ab6a228-4214-49e5-aa83-c00fe9315782`.
- **Carrier:** eld-coordinator Windows process.
- **Executor:** `device_lease.py`, which reuses the WP-0016 lock, job and board guard.

I start no detached process and keep no tool call open during GPU execution. **No GPU command has been issued.**

## Continuation after provider-credit exhaustion (native session, CPU only)

Everything above this heading was written by the prior session `5ab6a228-4214-49e5-aa83-c00fe9315782` and is left as written.

- **Author of this section and later commits:** eld-rd-reviewer.
  - Fresh native Claude Code CLI session `e2d32880-3555-4a4d-b695-b7963a903c2c`.
  - Model `claude-opus-5-5`, requested effort xhigh. The coordinator launched it with `dispatch/nativeopus.py`.
- **Independence:** I authored no WP-0017 design, fixture, engine or runtime, and no coordinator tool. I dispatch no agent.
- **Operator of record:** from this revision on, the operator for any command is `common.OPERATOR`, meaning this session. The identity paragraph above describes the prior session only.
- **What was found and done, in order:**
  1. **`90747b3` pushed unchanged.** The prior session had committed it but not pushed it. The remote head was verified as `90747b38…` before I made any commit.
  2. **Its CPU tests were run.** `evidence/cpu-selftest-q0-r3-90747b3.json` records 44/44 on Q0 3.12.10 with the tools unchanged. The prior session had run them only in its own scratch space.
  3. **Its A1 anchors were frozen.** `a1_sync.py` wrote `evidence/A1-anchors-reviewer.json` (SHA `339b9f77…`, 20 checks, 0 failures). The prior session had produced only a scratch dry run. Both were committed at `d29a3b5`.
  4. **The tools were revised to the coordinator's actual A1 wave.** That wave uses 16 configurations: 14 unique bit vectors plus the `all_off`/`all_on` endpoint controls, with the eight-window endpoint gate. The revision also adds an independent normalizer for the combined endpoint/switch run directories, the A2 both-view adapter with raw-capture, path and metric validation, and the release-review hardening. Rules are in [decision_procedure.md](decision_procedure.md). The self-tests are `selftest.py` (still 44 tests, with the scenario on the 16 wave) and `selftest_continuation.py`.
- **Findings for the coordinator** (CPU, before any release):
  - **F1, line endings.** The main checkout's working copies of nine WP-0017 coordination files each end with exactly one CRLF: `assignment.md`, `bind_dev.py`, `check_endpoints.py`, `issue_lease.py`, `participants.json`, `prepare_a1.py`, `review_command.py`, `a1-anchors.json` and `a2-inputs.json`.
    - Their raw SHA-256 values therefore differ from the committed LF blobs. For example, the carrier `review_command.py` is `f10c7e7f…` on disk against blob `c5596d0e…`, and `issue_lease.py` is `f2f765b3…` against `10c14e1b…`.
    - Content is equal after CRLF→LF normalization, and `git status` shows them clean.
    - Releases and plans record raw disk digests. Under `90747b3`'s exact-pin check, the carrier comparison would have failed.
    - This revision accepts an EOL-only variant and records both digests.
    - **Recommendation:** restore LF bytes, for example by checking those files out again, before issuing releases. Then the release digests will equal the committed blobs.
  - **F2, executor binding.** `device_lease.bind_inputs` re-checks HEAD and the candidate's `*.py` digests at execution, but not cleanliness or other tracked engine files. An example is a frozen surgical JSON, which matters for A2. My issue-time review checks every tracked engine file against its blob and requires a clean tree, untracked files included.
    - **Recommendation:** bind all tracked engine files, or re-check `git status --porcelain` in the executor, before A2.
- **Engine candidate binding:**
  - Carbon published `research/wp-0017-engine`, with source deliverable `3cb28112…` and head `eb167088…`, plus `dispatch/carbon-ready.json`. The coordinator integrated it at `08b72c2`.
  - The corrected candidate is still pending. It was requested in `dispatch/carbon-fix.txt` (the joint peer-review fixes), and no `carbon-corrected-ready.json` exists yet.
  - I read the published schema only from Git blobs: `CONTRACT.md`, `a1_trial.py`, `span_probe.py`, `launch.py`, `ablation_engine.py` and `doc_trial.py`. I never read the author's working tree.
- **Binding of `a1_normalize.py`:**
  - The probe/label mapping is bound to `eb167088…` only. A run whose `launch.json` source is any other SHA is refused (`UNBOUND`) until a reviewed re-bind commit adds it. I expect the corrected candidate to need exactly that.
  - The mapping moves the shared pre-divergence tokens into the prefix. On 037 that is the `' '` (223) after the engine's 40-token prefix, which gives the frozen 41-token prefix `0df32b06…`.
  - It recomputes D from per-token guarded FP32 log-probabilities and requires agreement with the engine's D within 1e-9.
  - It maps the implementation labels and derives the S3-on/S0-off deferred-callback label from the bound contract plus nonzero counters.
  - It rejects any S3-on probe that does not record the configuration's device guards. That is the joint design read's finding 3, and `eb16708` uses host guards only.
- **Engine geometry check.** `engine_geometry.py` runs the candidate's own `span_probe.py` locator functions from their verified blob (`f0638af3…`) with the pinned tokenizer on CPU. It confirmed the geometry the normalizer assumes: 019 has P=417 with no shared token, and 037 has P=40 plus `[223]`. Both match the audited digests and spans.
- **A2/A3:** `doc_trial.py` at `eb16708` uses the WP-0016 segmented layout that `a2_views.py` assumes. `command.py` still fails closed for A2/A3 until their plan generator is published and reviewed.
- **Exposure:** CPU only. No torch, CUDA or model was loaded. No H, A, B or dev key was opened; the A2 tests use a synthetic key in scratch. No WP-0017 output exists. Scratch is under `WP-0017/review/scratch-e2d32880/` and is never an input to a decision.

**Continuation evidence** (Q0 Python 3.12.10, `tokenizers` 0.21.4; tools committed before each receipt):

| Evidence | Tools at | Result | SHA-256 |
| --- | --- | --- | --- |
| `evidence/cpu-selftest-q0-r3-90747b3.json` | `90747b3` (prior session, unchanged) | 44/44 | in `d29a3b5` |
| `evidence/A1-anchors-reviewer.json` | `90747b3` `a1_sync.py` | 20 checks, 0 failures | `339b9f77…` |
| `evidence/cpu-selftest-q0-r4-3ee83ab.json` | `3ee83ab` | 44/44 | `cc72dd6b…` |
| `evidence/cpu-selftest-continuation-q0-3ee83ab.json` | `3ee83ab` | 36/36 | `0eda459c…` |
| `evidence/A1-engine-geometry-eb16708.json` | `3ee83ab`, candidate `eb16708` `span_probe.py` `f0638af3…` | 18 checks, 0 failures | `209eda6b…` |

**Not run:**
- `command.py review` against a real release, because none exists. Its A1 plan re-derivation is self-tested against the pinned `prepare_a1.py` blob. The full candidate/worktree review needs the actual release.
- The engine author's own `verify_cpu.py`. That is the author's preflight. I ran only the candidate's pure locator functions.
- No GPU or model step of any kind.
