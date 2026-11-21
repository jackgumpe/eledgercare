# WP-0023 / 002. Native singleton controls and gated two-lane trial

| Report metadata | Recorded value |
| --- | --- |
| Report | `docs/agent-reports/eld-batch-trial/WP-0023/002_2026-11-21_research_eld-batch-trial.md` |
| Reservation and category | [WP-0023 /002](https://github.com/jackgumpe/eledgercare/blob/1503bc9f1a7bf3de4bfa7426c2be906226992c0c/INDEX.md#wp-0023-native-baidu-b1-versus-b2-speed-trial), research |
| Author / publisher | `eld-batch-trial`, native Codex session `/root/b23_trial`. Requested xhigh; the backend model version and effective effort were not exposed. Windows PowerShell and Q0 Python 3.12.10. |
| Repository and branch | Private `jackgumpe/eledgercare`, `research/wp-0023-speed-harness`, isolated `eledgercare-worktrees/batch23-trial` |
| Assignment base | `1503bc9f1a7bf3de4bfa7426c2be906226992c0c` |
| Trial deliverable | `99eda4a6af106f0176acd4e0df4b8579e9c1ece1` |
| Integrated candidate operated by /003 | `8682fc7d215c0b063d5c3ef8ccce91a090cff90c`, with /001 wrapper `d9b100a59d689fff3ef495a29991f3d3c768044d` and frozen raster publication `49a66017b92157c622cc2beda17265abc87cca66` |
| Status and next owner | Ready for independent review, `eld-batch-reviewer` /003, then `eld-coordinator` /004. First canonical trial-author report. |

Report timestamp 2026-11-21T09:19:55Z. This is the trial author’s verification of the code and read-only interpretation of the separate reviewer’s device measurements.

## Outcome

Both native singleton controls and the wrapper at B=1 agreed through EOS. At B=2 the short window still agreed in both slots. The long window changed at seven of 665 emitted token positions in both slots. The first change was the 85th decision, with 84 identical preceding tokens. It changes the closing table coordinate from 516 to 518. The exact-parity gate stopped the trial before crossover timing. There is no accepted B=2 speedup or 60-page replay release.

| Three-page window | Native emitted IDs before EOS | Wrapper B=1 | B=2 short,long | B=2 long,short |
| --- | ---: | --- | --- | --- |
| Short, pages 4–6 | 62 | All 63 decisions equal | All 63 equal | All 63 equal |
| Long, pages 7–9 | 665 | All 666 decisions equal | First difference at step 84, seven emitted IDs differ | Same seven differences |

The eight lane outputs from six natural calls used the same per-window 827-token prompts, retained all three page markers and finished at selected EOS ID 1. The stock return omits that token. The stock return monitor observed the actual generator selection at step 62 or 665. Both wrapper permutations executed one [2,827] prefill and 665 [2,1] decoder forwards. Their language-head shape at each step was [2,1,129280].

## First differing decision

The separate stock and singleton-wrapper replays both selected 24254. The stock top-two values tied at 58.00 and torch.argmax selected the lower index. The order reported by torch.topk at an exact tie is distinct from the argmax selection. Both B=2 replays selected 25089. Neither competitor was suppressed by either guard. The long lane had one page marker in its 84-token prefix and its short peer had already stopped.

| Token | Native B=1 BF16 | B=2 BF16 | Signed B=2 − B=1 | B=1 FP32 | B=2 FP32 | FP32 difference |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 24254 | 58.00 | 57.50 | −0.50 | 58.60135651 | 58.60135651 | 0 |
| 25089 | 58.00 | 57.75 | −0.25 | 58.72898102 | 58.72896194 | −0.00001907 |

Raw and post-guard values are identical in this table. Recomputing only the head in FP32 on each shape’s captured BF16 hidden vector also selects 25089 at both widths. The final BF16 decoder hidden vectors differ by at most 0.0390625 across shapes at this position. A full FP32 replay of the first failing order agrees on 25089. It promotes the same frozen coefficients and original BF16 raster-builder values, disables TF32 and autocast, and forces math SDPA. This evidence supports numerical sensitivity at an observed singleton tie. It does not determine which individual BF16 kernel first accounts for the eventual output difference or the causes of all six subsequent substitutions.

## Device evidence and resource scope

The assigned independent reviewer operated the six-page plan on the RTX 5070 Ti under sole lease `dev-r1`. Its plan SHA-256 is `3f941f2fb954fd27462a99d0b73a05bcafe8910e5b76b3964202107c7efd94a9`. The recorded command from `process.json` used the clean integrated worktree.

```powershell
& 'C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe' -I -B 'C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/batch23-review-replay1/docs/research/WP-0023/trial/run.py' --plan 'C:/Users/jackg/Asp.net Projects/eledgercare/docs/coordination/WP-0023/dev-r1-plan.json' --output 'C:/Users/jackg/eLedgerCare-Speed/WP-0023/review/runs/dev-r1'
```

The reviewer child exited zero after 440.25 s. The board guard returned at 09:18:02 UTC. The coordinator confirmed all 37 checkpoint-tree inventory entries unchanged after rehash. The cold pin/verification/load interval was 25.47 s and the loader separately measured 14,062 ms. Of 212 board-wide observations, sampled used-memory peaks were 6,962 MiB during cold verification/load, 8,724 MiB during each natural B=2 arm and 14,849 MiB during the full FP32 two-lane diagnostic. Sampling can miss short peaks. Every completed record retains start/end UTC ns and process CUDA peak allocated/reserved bytes. These untimed-gate records include cold effects; G3 warmups and timed AB/BA pairs were unreleased.

The operator owns `C:/Users/jackg/eLedgerCare-Speed/WP-0023/review/runs/dev-r1` and the retained device/effect receipts under the packet’s `coordination/leases/dev-r1` directory. Primary artifacts include `trial/g1*.json`, both `trial/g2-*.json` lane outputs, stock and B=1/B=2 `trial/diag-*.json` replays, `trial/diagnostic-fp32.json`, `trial/decision.json`, and `process.json`. The reviewer created `docs/reviews/WP-0023/dev-r1.zip` with SHA-256 `9d7b818fab660ef7c25ee98bd5161ea10e7d745516f9bb8ff7b796571571e2ed`. Its per-file inventory and independent disposition belong to /003.

## Source and verification

| Added file under `docs/research/WP-0023/trial/` | Role |
| --- | --- |
| `run.py` | Validates the clean commit, leased Q0 Python, device visibility, six serialized and decoded rasters, pinned dynamic code and offline environment. Uses the existing resident model loader and process-lifetime checkpoint pin. Records each arm after a CUDA barrier, separately from cold load and evidence publication. |
| `stock.py` | Runs the unmodified `infer` path with frozen Q0 parameters. A Python monitoring return callback reads its actual `nxt` and step before disposal. During a requested diagnostic only, two source-bound line callbacks observe logits before any guard and after native greedy selection, then end the replay at that decision. |
| `gates.py` | Compares prompt, full returned IDs, raw text, three-page structure, actual EOS, finish reason and stop cause. Computes signed B=2 minus B=1 scores on the same two IDs, including explicit masked-logit outcomes. |
| `diagnostic.py` | Teacher-forces each original slot's shared prefix, preserving its peer’s observed tokens or earlier EOS. Stores separate stock, wrapper singleton and matching two-lane replays, guard restrictions reconstructed from token history, swap comparisons and one conditional full-FP32 pair. |
| `test_cpu.py` | Exercises real PEP 669 callbacks with CPU tensors, in-place masks, stop-state differences, length eligibility, both gate failure branches, diagnostic score signs, replay reuse and warm AB/BA ordering. |

Only this canonical report is additional metadata on the author branch. The report owner wrote no engine, reviewer code, scheduling, production, coordination or fixture changes. Under the operating plan each warm timed method processes six pages. Two excluded warmups precede the native→batch short,long pair and the batch→native long,short pair. Only four-way parity could admit them.

| Author check | Evidence |
| --- | --- |
| `C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe -I -B docs/research/WP-0023/trial/test_cpu.py` | At the frozen trial SHA, five tests passed in 2.993 s. CPU tensors and synthetic call records, no GPU calls. |
| `C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe -I -B docs/research/WP-0023/trial/run.py --help` | CLI accepted the plan/output interface with no model import. |
| Q0 CPU call to `run.load_images`, comparing each committed PNG and decoded RGB array | Against fixture commit `49a66017b92157c622cc2beda17265abc87cca66`, all six 2550×3301 rasters matched and the manifest SHA-256 was `06abb2ab4cd7bf8d74286741d4ce5da08f6e60fd237050394e2b891ae909058f`. The stock model source digest was `f6df813cef23cc28b1daca40fd8cb20740d05a238e7b9dfa2334531fdcf39f1f`. No torch import in this fixture/environment probe. |
| `git diff --cached --check`, `git ls-remote origin refs/heads/research/wp-0023-speed-harness` | Whitespace passed. Origin confirmed deliverable `99eda4a6af106f0176acd4e0df4b8579e9c1ece1` before report publication. |

The earlier source `e704d5af0f7f92d72cb5b2c2f3c42f3b67ea9546` compared both controls but did not stop on equal or reversed emission lengths. The coordinator identified that omission before device execution. The final candidate records each count excluding EOS and holds G2 unless the short count is strictly lower. No decisive execution used the superseded harness. [Full trial-author diff](https://github.com/jackgumpe/eledgercare/compare/1503bc9f1a7bf3de4bfa7426c2be906226992c0c...99eda4a6af106f0176acd4e0df4b8579e9c1ece1)

## Handoff

The author verified the published source and inspected the separate device records. /003 owns the independent source/evidence audit and /004 owns the final scale disposition. The CPU checks and controlled inference were confined to this research packet and its synthetic inputs. [Pinned operator archive and independent calculations](https://github.com/jackgumpe/eledgercare/tree/b17836281b07f580bf28c96bf5e1ad349496667c/docs/reviews/WP-0023)
