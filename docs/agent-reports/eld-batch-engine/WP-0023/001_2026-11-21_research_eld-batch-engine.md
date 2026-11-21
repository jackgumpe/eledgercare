# WP-0023 / 001 — Native Baidu multi-window decode

- Author and publisher — `eld-batch-engine`, Codex subagent `/root/b23_engine`. Fresh-session requested effort was xhigh. Exact backend and effective effort were not exposed.
- Category and status — research, ready for independent review.
- Reservation — [WP-0023 /001](https://github.com/jackgumpe/eledgercare/blob/1503bc9f1a7bf3de4bfa7426c2be906226992c0c/INDEX.md#wp-0023-native-baidu-b1-versus-b2-speed-trial). Previous report none. Related owners are /002 trial and /003 independent operator/reviewer.
- Report path — `docs/agent-reports/eld-batch-engine/WP-0023/001_2026-11-21_research_eld-batch-engine.md`.
- Repository and worktree — private `jackgumpe/eledgercare`, branch `research/wp-0023-native-batch`, `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/batch23-engine`.
- Base — `1503bc9f1a7bf3de4bfa7426c2be906226992c0c`. Engine deliverable — `d9b100a59d689fff3ef495a29991f3d3c768044d`. Operator candidate — `8682fc7d215c0b063d5c3ef8ccce91a090cff90c`, identical engine tree.
- Environment — Windows PowerShell, pinned Q0 Python 3.12 / torch 2.13.0+cu130 / transformers 4.52.1. Author executed CPU checks. The separate /003 session operated the GPU.
- Timestamp — 2026-11-21T09:18:51Z. Next owner — `eld-batch-reviewer` for /003, then `eld-coordinator` for disposition.

## Outcome and scope

On the two released three-page synthetic windows, the wrapper reproduced stock singleton outputs and EOS exactly. With simultaneous B=2 decode, both lane permutations changed the long window's first table bottom coordinate from 516 to 518 at emitted token index 84. Seven of its 665 emitted IDs differed. The short window's 62 emitted IDs and EOS matched in both slots. The prespecified G2 failure closed the timing gate. The research wrapper has no speed or scale acceptance.

The frozen engine checks native greedy IDs, prompt and generated page counts, terminal selection and actual active-lane state. G1 requires exact B=1 agreement, G2 exact agreement in each slot of both orders. The accepted input form here is a list of three-page, equal-prompt-length windows. No product code, training, checkpoint file, runtime configuration on disk or external service changed.

## Change inventory

| New source in the base-to-deliverable diff | Behavior |
| --- | --- |
| `docs/research/WP-0023/engine/native_batch.py` | `run` constructs native prompts and processes each lane independently. It calls the checkpoint's actual vision, decoder, DASH configuration and head. `_observe` measures matched decision prefixes and `_fp32_forwards` runs reference arithmetic. |
| `docs/research/WP-0023/engine/cpu_checks.py` | `check_native_mask_math` exercises the pinned row-wise candidate mask and decode attention. `check_wrapper` verifies both orders, peer EOS, finite limits and FP32 restoration with a small constructed module. |

This report is the only subsequent author metadata. The branch was published by normal push. The GPU lease, guard and stage files belong to /003.

## Implementation

Each lane has its own prompt tensor, image tuple, generated token list, native streaming state, n-gram history, page-counter cursor and finish event. `[B,S]` absolute positions matter because the upstream page-aware mask uses the position tensor's batch dimension when reshaping image blocks. The native vision encoder loops over pages and scatters the features into the corresponding sample. The full native LM prefill and subsequent LM decode run with B simultaneous rows. The native dynamic cache carries per-row self-attention keys/values, DASH index keys, prompt page-block bounds, cumulative page counts and per-layer page-RoPE state.

An EOS freezes the lane's published outputs, page guard and stream. Later decoder calls retain physical batch width by consuming dummy EOS in that lane's private cache. This preserves the tested physical shape while its peer continues. The observed first difference came 22 decision steps after the short window selected EOS.

The reference replay promotes the same checkpoint coefficients and native BF16 raster-builder values to FP32. Each selected expert uses its original forward via a transient FP32 parameter map to limit resident memory. The replay covers vision, cached prefill, incremental decoder, router and head, with autocast disabled, TF32 disabled for CUDA matmul and cuDNN convolution, PyTorch math SDPA forced and Triton absent. This changes backend precision and SDPA selection together. The localized FP32-head check keeps each BF16 decoder result as its input.

## Verification

| Author checks on frozen engine | Result |
| --- | --- |
| `C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe -B docs/research/WP-0023/engine/cpu_checks.py C:/Users/jackg/eLedgerCare-Q0/WP-0005/models/Unlimited_OCR_2_04809669` | Exit 0. The script hides CUDA and reads three native helper definitions plus native decode-attention source. Both lane orders, post-EOS output/streamer history, forced prefixes, FP32 expert restoration and token/length limits passed. |
| `git diff --check 1503bc9f1a7bf3de4bfa7426c2be906226992c0c HEAD` | Exit 0 at the engine revision. |
| `git diff --exit-code d9b100a59d689fff3ef495a29991f3d3c768044d 8682fc7d215c0b063d5c3ef8ccce91a090cff90c -- docs/research/WP-0023/engine` | Exit 0. |
| `git ls-remote --heads origin refs/heads/research/wp-0023-native-batch` | Returned exact engine deliverable before report publication. |
| `Get-FileHash` on the pinned `modeling_unlimitedocr.py` | SHA-256 `f6df813cef23cc28b1daca40fd8cb20740d05a238e7b9dfa2334531fdcf39f1f`. Source inspection covered `modeling_deepseekv2.py`, `dash_attention.py` and `_sparse_base_impl.py`. |

### Decisive execution by the independent operator

I read the operator's `C:/Users/jackg/eLedgerCare-Speed/WP-0023/review/runs/dev-r1/trial` JSON files and recomputed disagreement positions, score deltas and last-position hidden-vector differences using Python. I did not execute the GPU. The operator's `g1.json`, `g2.json` and `decision.json` have SHA-256 digests `ce3f82594b455664217a7811c772469cbaf9a20dc26c50c5401664ca97fb9c6c`, `d082d5b2cd7c8180bcb0f9cb9dd69c11f1d8ca2b825cbc26a554ab8e1eb651c8` and `e552254a514596afa4bbf66c354681c0faaca5ae1870634ff4578015c8dff75a`.

The reviewer published the preserved run at `b17836281b07f580bf28c96bf5e1ad349496667c`. The archive SHA-256 is `9d7b818fab660ef7c25ee98bd5161ea10e7d745516f9bb8ff7b796571571e2ed`. Stage records live under `run/trial/` inside the archive. [Raw run archive](https://github.com/jackgumpe/eledgercare/blob/b17836281b07f580bf28c96bf5e1ad349496667c/docs/reviews/WP-0023/dev-r1.zip) · [Independent audit](https://github.com/jackgumpe/eledgercare/blob/b17836281b07f580bf28c96bf5e1ad349496667c/docs/reviews/WP-0023/dev-r1-audit.json)

Both orders used `[2,827,1280]` decoder prefill, `[2,1,1280]` decode and `[2,1,129280]` head output. The first layer's prefill keys had shape `[2,10,827,128]` and its cached DASH keys had shape `[2,827,128]`. Short emitted EOS at index 62, long at 665, with three generated page markers in each case. At index 84, the long lane had one page marker and zero n-gram bans. Both candidates were allowed. The initial 84 long-lane IDs matched across modes.

| Next-token logits at long prefix length 84 | ID 24254 | ID 25089 | Argmax |
| --- | ---: | ---: | ---: |
| Stock and wrapper BF16 B=1 | 58.0 | 58.0 | 24254 |
| Wrapper BF16 B=2, either slot | 57.5 | 57.75 | 25089 |
| FP32 head on BF16 B=1 hidden | 57.914852 | 58.061798 | 25089 |
| FP32 head on BF16 B=2 hidden, long in slot 1 | 57.590645 | 57.732563 | 25089 |
| Full FP32 B=1 replay | 58.601357 | 58.728981 | 25089 |
| Full FP32 B=2 replay, long in slot 1 | 58.601357 | 58.728962 | 25089 |

BF16 B=2 minus B=1 candidate deltas were −0.50 and −0.25. `torch.argmax` selected the lower vocabulary ID at the B=1 tie. The localized FP32 head separated the pair for both BF16 hidden states. The BF16 last-position decoder input vectors matched, while the first layer's output already differed in 452 of 1,280 components. At final normalization, the cross-shape RMS difference was 0.00753713, versus approximately 0.00000099 in the full FP32 replay. Numerical precision affected this decision. The experiment does not isolate one earlier kernel, one individual arithmetic operation, or prove full-sequence FP32 parity. The two FP32 runs were bounded, forced-prefix replays.

## Review map and handoff

The next reviewer can compare `run`, `_guard` and `_observe` with upstream `_uocr_generate`, `_uocr_dash_decode_allow` and `_dash_decode_forward`, replay the CPU checks and independently assess the operator's raw artifacts. No additional GPU run was performed by this author. G3, a 60-page replay and deployment were outside the achieved gate. The coordinator owns formal disposition. [Exact engine diff](https://github.com/jackgumpe/eledgercare/compare/1503bc9f1a7bf3de4bfa7426c2be906226992c0c...d9b100a59d689fff3ef495a29991f3d3c768044d)
