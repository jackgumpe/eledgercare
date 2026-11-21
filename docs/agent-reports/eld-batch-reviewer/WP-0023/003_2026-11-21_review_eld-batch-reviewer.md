# WP-0023 /003. Independent native batching trial

**G1 passed. G2 failed in both lane orders.** The short window reproduced the stock singleton through EOS. Both long-window runs differed at the same seven token positions. The first differing choice changed the lower edge of the first table from 516 to 518. The short window had already finished at that point. The gated runner ended after its diagnostic replays. [Primary records](../../../reviews/WP-0023/dev-r1.zip) · [Independent computations](../../../reviews/WP-0023/dev-r1-audit.json)

| Review record | Value |
| --- | --- |
| Path and category | `docs/agent-reports/eld-batch-reviewer/WP-0023/003_2026-11-21_review_eld-batch-reviewer.md`, review |
| Author and publisher | `eld-batch-reviewer`, native Codex session `/root/b23_review`, xhigh requested. Exact backend identity and applied effort were unexposed. I authored the review tools, exercised the candidate and operated the sole lease. The engine and trial have separate authors. |
| Repository and branch | Private `jackgumpe/eledgercare`, `review/wp-0023-native-batch`, owned worktree `eledgercare-worktrees/batch23-review` |
| Reservation and base | `1503bc9f1a7bf3de4bfa7426c2be906226992c0c`. [Reservation](https://github.com/jackgumpe/eledgercare/blob/1503bc9f1a7bf3de4bfa7426c2be906226992c0c/INDEX.md#wp-0023-native-baidu-b1-versus-b2-speed-trial) |
| Frozen candidate and release | Clean detached `batch23-review-replay1` at `8682fc7d215c0b063d5c3ef8ccce91a090cff90c`. Release publisher `eld-coordinator` at `46c67e2ae04e753e25942f3a044fb244f5d92cc8`. |
| Reviewed revisions | Engine `d9b100a59d689fff3ef495a29991f3d3c768044d`, trial `99eda4a6af106f0176acd4e0df4b8579e9c1ece1`, inputs `49a66017b92157c622cc2beda17265abc87cca66`. [Engine report /001](https://github.com/jackgumpe/eledgercare/blob/9129ef3976fc754e0c41ca225e9922079b12227d/docs/agent-reports/eld-batch-engine/WP-0023/001_2026-11-21_research_eld-batch-engine.md) · [Trial report /002](https://github.com/jackgumpe/eledgercare/blob/e707b3347956d0333a8094b6329fd85c1feb7b0c/docs/agent-reports/eld-batch-trial/WP-0023/002_2026-11-21_research_eld-batch-trial.md) |
| Reviewer deliverable | `b17836281b07f580bf28c96bf5e1ad349496667c`, pushed and verified on origin before this report. Original scientific audit and archiver prepared at `070c61998467c0a145bbb5d87588ed4104f18938`. |
| Status and handoff | Accepted as evidence of failed B=2 token parity. Decision owner `eld-coordinator` /004. First reviewer report for this packet. |
| Timestamp and runtime | 2026-11-21T09:22:16Z. Windows PowerShell, pinned Q0 Python 3.12.10, PyTorch 2.13.0+cu130, CUDA 13.0, RTX 5070 Ti. |

## Execution and independent checks

I compared the pinned checkpoint's native `_uocr_generate`, both guard functions, the image scatter loop, DASH page candidates, incremental RoPE and cache updates against the wrapper and trial. Native `stop` requires observing the selected EOS, which the native returned ID list excludes. The wrapper computes one prefill and one joint decoder forward per step. Finished slots feed inert EOS and keep their own output/guard histories frozen while other slots continue. Native vision still loops over images and pages. The runnable control and candidate both use one native text streamer per lane.

The two native controls came from pages 4–6 and 7–9 of the fixed 12-page development PDF. Independent CPU rendering reproduced all six decoded RGB hashes. The batch-guard CPU challenge used different prompts, marker histories and image-block positions. At five decode steps, RoPE and DASH state for each row matched its own singleton under both orders. Separate n-gram and page bans distinguished the two histories. The engine's frozen CPU checks and all five runner tests also passed on the isolated execution checkout. [Upstream CPU evidence](../../../reviews/WP-0023/upstream-cpu-result.json) · [Input verification](../../../reviews/WP-0023/input-review-before.json)

| Arm | Short window | Long window |
| --- | --- | --- |
| Unmodified B=1 | 62 emitted IDs. Page markers 0, 20, 41. EOS ID 1 on step 62. | 665 emitted IDs. Page markers 0, 222, 444. EOS ID 1 on step 665. |
| Wrapper B=1 | All 63 choices including EOS matched | All 666 choices including EOS matched |
| B=2, short then long | Exact, including terminal state | Seven changed IDs, first at zero-based 84 |
| B=2, long then short | Exact, including terminal state | Identical seven changed IDs, first at 84 |

Both B=2 primary records show decoder input `[2,827]`, first decode input `[2,1]`, decode hidden `[2,1,1280]`, and head output `[2,1,129280]`. All 12 KV layers had prefill shape `[2,10,827,128]`, and all 12 DASH-index and page-RoPE caches had two rows. The short lane's last selected token/step and scanned history stayed at its own EOS after 665 joint decode forwards. Both long emissions retained three pages and ended at their own EOS. The differences at positions 84, 227, 316, 449, 537, 540 and 543 affected a box coordinate, title levels, a heading's capitalization and leading spaces in headers.

## Matched-prefix diagnosis

At token 84, both targets had seen one page marker and 83 subsequent tokens. The peer had finished after 62 emissions plus EOS. The native, wrapper-singleton and dual-lane guard scans agreed. Neither candidate was banned by n-gram or page guards. Both B=2 permutations had the same winner, the same complete streams and the same inspected page mask state and RoPE coordinates as the target singleton. Native `topk` listed the two equal singleton logits in an order that differs from first-index `argmax` tie breaking.

| Candidate | Native and wrapper B=1 BF16 | B=2 BF16, either slot | B=2 minus native | FP32 B=1 | FP32 B=2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 24254, `516` | 58.00 | 57.50 | −0.50 | 58.6013565063 | 58.6013565063 |
| 25089, `518` | 58.00 | 57.75 | −0.25 | 58.7289810181 | 58.7289619446 |

Raw and post-guard scores agreed. Native and wrapper B=1 selected the lower ID at the BF16 tie. Both lane orders selected 25089 at B=2. At the target position the BF16 decoder inputs matched, the first decoder layer outputs differed by up to 0.0009765625 and the final normalized hidden vectors differed by up to 0.0390625. Converting the head calculation alone to FP32 on those BF16 hidden vectors produced 25089 for both widths.

The full-spine FP32 replay covered the first failing order and the shared 84-token prefix. It promoted the same stored checkpoint coefficients and original upstream BF16 raster-builder values, including the native vision, decoder, routed experts and head. Autocast and TF32 were disabled, Triton was absent and PyTorch math SDPA was explicitly selected. Both widths chose 25089. Their final hidden vectors differed by at most 0.0000032783. The evidence supports precision- and shape-sensitive inference at an observed BF16 tie. The FP32 reference also changes SDPA backend selection. Attribution to a particular kernel or to the downstream six differences is unresolved. The trace found no cross-lane history violation in the inspected fields.

## Device, boundaries and replay

Lease `dev-r1` held the physical board lock and Windows kill-on-close job. The independent frozen run exited zero, the guard recorded no fault, and the job returned at 09:18:02.245991 UTC. The order took 440.641 seconds, including controls and diagnostics. After job close the physical board had 14,678 MiB free, 1,320 MiB used and no reported resident model owner. Sampled board peaks were 6,962 MiB during cold qualification/load, 8,724 MiB on the B=2 primary arms and 14,849 MiB on the FP32 replay. The record has 212 samples. Native model loading took 14.062 seconds within a 25.470-second cold initialization. Only a successful G2 could open the excluded warmups and timed AB/BA arms. No warm timing or speedup was measured. The counterexample closes the 60-page advancement gate.

The checkout remained clean. The reviewed integration delta from the reservation consists exclusively of 14 WP-0023 coordination items and seven WP-0023 research-source items. The six selected development rasters and PDF were the only document inputs. Packet B, production, model weights and the queued research study were untouched. Independent post-return verification reproduced the same six page hashes and the complete pre-run inventory of 37 model files, three directories, lengths, SHA-256 values and modification timestamps. All runtime scratch remains within the reviewer and coordinator lease paths. [After-run verification](../../../reviews/WP-0023/input-review-after.json) · [Lease and phase inventory](../../../reviews/WP-0023/dev-r1-inventory.json)

The sole device invocation used this released command.

```powershell
& 'C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe' -I -B 'C:/Users/jackg/Asp.net Projects/eledgercare/docs/coordination/WP-0023/device_lease.py' 'C:/Users/jackg/Asp.net Projects/eledgercare/docs/coordination/WP-0023/dev-r1-release.json' '1607be5580efe5af2b640c2a295bbfdd5cf08f88863a0fce746cfe039c14c2d3'
```

| Verification | Executed method and result |
| --- | --- |
| Inputs and model | Q0 Python `-I -B docs/reviews/WP-0023/verify_inputs.py ../../eledgercare/docs/coordination/WP-0023`, before and after, exit 0. Input receipts are byte-identical. |
| Native CPU guard/position checks | Q0 Python `-I -B docs/reviews/WP-0023/upstream_cpu.py`, exit 0, CUDA uninitialized. |
| Candidate CPU checks | On detached `8682fc7d`, CUDA hidden, ran engine `cpu_checks.py` via isolated Q0 Python with its directory on `sys.path` and the pinned model tree as sole argument. Ran `-I -B docs/research/WP-0023/trial/test_cpu.py`. Both exit 0. |
| Archive and independent replay | `py -I -B docs/reviews/WP-0023/archive_run.py dev-r1 ../../eledgercare/docs/coordination/WP-0023 docs/reviews/WP-0023/dev-r1.zip` and `py -I -B docs/reviews/WP-0023/audit_run.py C:/Users/jackg/eLedgerCare-Speed/WP-0023/review/runs/dev-r1/trial`, exits 0. Verified all 46 archive member hashes, then extracted in new reviewer scratch and reproduced the exact saved audit bytes. An initial comparison of native Python tuples with JSON lists failed at serialization boundaries. Rechecking the serialized bytes passed. |
| Preservation | `git diff --name-only 1503bc9f1a7bf3de4bfa7426c2be906226992c0c 8682fc7d215c0b063d5c3ef8ccce91a090cff90c` and `git status --short --branch` on replay checkout. No production/checkpoint changes and clean detached state. |

## Change inventory and handoff

All review deliverables are under `docs/reviews/WP-0023/`. Source additions are `upstream_cpu.py`, `verify_inputs.py`, `audit_run.py` and `archive_run.py`. The CPU receipts are `upstream-cpu-result.json`, `input-review-before.json` and `input-review-after.json`. The operator records are `dev-r1.zip`, `dev-r1-inventory.json` and `dev-r1-audit.json`. The ZIP contains all stage receipts, primary IDs, diagnostic logits/hidden-state evidence, process logs, plan, release and guard records. It omits run caches. ZIP SHA-256 is `9d7b818fab660ef7c25ee98bd5161ea10e7d745516f9bb8ff7b796571571e2ed`. This canonical report is the sole subsequent metadata file. [Source and evidence tree](https://github.com/jackgumpe/eledgercare/tree/b17836281b07f580bf28c96bf5e1ad349496667c/docs/reviews/WP-0023)

Disposition to `eld-coordinator` /004 is to retain the single-window native reference and close the speed and scale gates on this candidate. No second lease or replay is pending.
