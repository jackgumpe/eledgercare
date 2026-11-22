# WP-0029 / 001 — Cedar opening acquisition

| Reporting field | Recorded value |
| --- | --- |
| Author and publisher | eld-cedar-operator |
| Category and status | Research, ready for independent review |
| Reservation | [WP-0029 / 001](https://github.com/jackgumpe/eledgercare/blob/4d94271a56f550bcf96b76d970f54e4c8b845ad5/INDEX.md#wp-0029-cedar-capture-and-owner-scoring) |
| Report path | `docs/agent-reports/eld-cedar-operator/WP-0029/001_2026-11-22_research_eld-cedar-operator.md` |
| Time | 2026-11-22T19:25:24Z |
| Native session | Fresh Codex subagent `/root/w29_operator`, dispatched with xhigh requested. The effective model and effort were unexposed. The shared shell reported thread `01a204af-b15c-7972-bc1e-fd8cde3f59a3`. |
| Execution | Windows AMD64, PowerShell, pinned CPython 3.12.10, torch 2.13.0+cu130, RTX 5070 Ti |
| Repository and branch | Private `jackgumpe/eledgercare`, `research/wp-0029-cedar-acquisition`, worktree `w029-operator` |
| Base | `4d94271a56f550bcf96b76d970f54e4c8b845ad5`, following WP-0028 closure `1b5fad0140e1c54c636b2348ae6dc6c6610c8b21` |
| Operator source and preflight evidence | `ea76872dc8a030db0cc51ea74553c7c939d0d83d` and `12577f907a5806f4f443a6f5067b4c49c60511e5` |
| Device candidate and release | Detached `w029-device` at `5014124e485d5ce89b9191e23458f12cc178bdcd`, SHA-256-bound release publication `fc42ba82075e10114855b3ac648cff7a5c562466` |
| Raw deliverable and post-run evidence | `48016df280f8f0c2f4a807955d9f431744347ecc` |
| Prior report and next owner | First operator report. eld-rd-reviewer performs independent raw-return authentication for WP-0029 / 003. |

## Result

The single authorized model load completed both calls. The excluded W0 emitted 62 tokens followed by EOS and matched the historical through-EOS digest. The Cedar opening emitted 332 tokens followed by EOS. The original sensor mapped 16 spans across the three input pages. Its page-one span 7 reads **Ledger: Cedar**. This is the text emitted by the model. The operator performed no trajectory scoring. [Raw archive](https://github.com/jackgumpe/eledgercare/blob/48016df280f8f0c2f4a807955d9f431744347ecc/docs/research/WP-0029/acquisition/native-return.zip)

| Event | Planned | Admitted | Completed |
| --- | ---: | ---: | ---: |
| Exclusive hardware order and model load | 1 | 1 | 1 |
| Excluded stock W0 | 1 | 1 | 1 |
| Hooked native B=1 Cedar opening, BF16 | 1 | 1 | 1 |
| Retry | 0 | 0 | 0 |

The warm-up and Cedar receipts share load ID `20044-134398489500790319-1`. The process retained the 333 little-endian through-EOS IDs, per-token consumed IDs and absolute positions 827 through 1158, the 332 × 1,280 BF16 normalized LM-head input and the 16 × 1,280 little-endian FP32 pooling. Input PNGs and RGB order are pinned in the archived plan. Both horizons reference the identical opening key `33362fbbeb37e805a64acbf3afdc3ec04315a4706820ed634a8fe0fb865ce2d5`.

| Retained bytes | SHA-256 |
| --- | --- |
| W0 through EOS, recorded digest | `837b21829d99ee47d583039651628cf6c7f6e796bd71ee8b5490c21d0c3a52d4` |
| Cedar through EOS | `20714ce511ac713d2ad321017a1266ea04b26594bdfe1501d7198493c298f436` |
| Cedar normalized hidden BF16 | `a39aab4c37e519b98ce99d8193acc8031749bb066b7fbc40078bb7870d21cacd` |
| Cedar pooled FP32 | `060a840b1a5b35ef8b4a58396abb2c3b2c4791f85664569b896b4f2bc085dfe2` |
| Primary ZIP, 770,072 bytes and 27 members | `0346091957994fcfc5c12d8d87e40ce177bb0c1ff0cc376b5ba8f4fb7cb2522f` |

## Verification and costs

The 9.656-second CPU preflight reconciled scoped WP-0029 Git history, matching remote branch heads, the packet's expected run/lease locations and prior operator receipt paths. The frozen WP-0028 proposal recorded zero prior native calls. The new acquisition roots contained no earlier issuance. For the four source PDFs and 31 distinct fixture PNGs I checked content hashes and decoded RGB. For all ten archived groups, I matched the physical member bytes to both the receipt and ZIP inventory, verified the calibration order and checked their 26 logical uses. Two further uses share the one missing opening. The disjoint W0 PDF and its three ordered PNG/RGB identities passed. The worker source matched revision `9c02c9fae465dc1d1322a81c23eb3af45bbb0aff`, and the original sensor matched revision `1843cdb7b6279b84b539d3ca1ba7bd0affa1f7dd`. [Preflight and individual input identities](https://github.com/jackgumpe/eledgercare/blob/12577f907a5806f4f443a6f5067b4c49c60511e5/docs/research/WP-0029/acquisition/evidence/prepare.json)

Before issuance and again after guard exit, the CPU verifier opened each of the 18 Q0 model objects and the notice for reading, streamed their bytes, checked the original Git blob SHA-1 or LFS SHA-256 as appropriate, and recorded SHA-256 for every object. Both 18-object reads covered 6,699,195,181 model bytes, including 6,688,305,576 bytes of weights. Interpreter hash, lock, manifest, tokenizer, module and the versions of all 32 pinned distributions passed. The complete pre/post content records matched. The post-run check took 6.125 seconds. [Post-run identity](https://github.com/jackgumpe/eledgercare/blob/48016df280f8f0c2f4a807955d9f431744347ecc/docs/research/WP-0029/acquisition/evidence/return.json)

I issued the guard on the coordinator's express dispatch after preflight evidence revision `3674ed58b88184abaececbef601c49602af69489`. The write-once intent records the command and release digests. The coordinator's guard took the shared UUID lock and checked the actual clients, the free floor, the candidate and its pins before the launch. The guard PID was 23448, venv launcher PID 248 and native worker PID 20044. Both the child and the guard exited 0. The last native boundary was `sensor/outcome.json` with `status=complete`. The lease return was recorded at 19:24:11 UTC. [Physical member inventory](https://github.com/jackgumpe/eledgercare/blob/48016df280f8f0c2f4a807955d9f431744347ecc/docs/research/WP-0029/acquisition/evidence/native-inventory.json)

| Observation | Result |
| --- | --- |
| Under-lock admission on GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d | 14,799 MiB free, 1,199 MiB used, 21 recognized desktop clients, zero unknown and zero resident Ollama models |
| Native job duration / authorized bound | 101.125 s / 180 s |
| Cold load / excluded W0 / complete Cedar window | 34.3222127 s / 26.7884788 s / 37.6405249 s |
| Cedar inference | 37.5948232 s |
| Complete native phase | 99.8012438 s |
| Maximum observed board use / ceiling | 8,580 MiB across 239 samples / 12,500 MiB |
| Cedar CUDA peak allocated / reserved | 7,310,486,528 / 7,459,569,664 bytes |
| Post-job board | 14,799 MiB free, 21 desktop clients, zero resident Ollama models |
| Historical load + W0 + Alder window | 84.078327 s |

The memory maximum is the maximum in the sampled board telemetry. The client observation is limited to the selected NVIDIA device. The worker logged a transformers cache deprecation and the known absence of Triton FLOP counting. Its terminal status, output and resource receipts are archived alongside both output streams.

## Reproduction and inventory

These are the exact command arguments used. The snippets bind the absolute Windows paths for readability. The device command documents the single consumed order.

```powershell
$py = 'C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe'
$dev = 'C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w029-device'
$guard = "$dev/docs/coordination/WP-0029/cedar_guard.py"
$rel = 'C:/Users/jackg/Asp.net Projects/eledgercare/docs/coordination/WP-0029/cedar-r1-release.json'
$releaseHash = '3b1f724bfd356f03411430a7ad522b4d2f3b9459feb3b0ed26fd15f7c4945eec'
$planHash = '16ffe4a8b565a9920ebbb80cbca3876fb10c18cc4af3a4b323a189e571a495ca'
$candidate = '5014124e485d5ce89b9191e23458f12cc178bdcd'
$review = '3674ed58b88184abaececbef601c49602af69489'
$acq = 'docs/research/WP-0029/acquisition'
# CPU-only commands in w029-operator with CUDA_VISIBLE_DEVICES=-1.
& $py -I -B "$acq/preflight.py" prepare
& $py -I -B "$acq/package_return.py" intent $candidate $planHash $releaseHash $review $dev $py -I -B $guard $rel $releaseHash
# Separate shell in w029-device, once.
& $py -I -B $guard $rel $releaseHash
# CPU-only commands in w029-operator with CUDA_VISIBLE_DEVICES=-1, after observed guard exit 0.
& $py -I -B "$acq/package_return.py" returned 0
& $py -I -B "$acq/preflight.py" return
```

| New paths below `docs/research/WP-0029/acquisition/` | Purpose |
| --- | --- |
| `common.py`, `preflight.py`, `package_return.py` | Read-only CPU identity, previous-attempt reconciliation, fixture/ZIP checks, one-shot issuance journal, raw packaging and byte-for-byte ZIP readback |
| `evidence/prepare.json` | Pre-issuance verification |
| `native-return.zip`, `evidence/native-inventory.json` | Original emitted and captured bytes, hashes and resource receipts |
| `evidence/return.json` | Full Q0 comparison and final desktop observation |

This report is subsequent publication metadata. Persistent external effects consist of the normal private branch pushes and the packet's reserved scratch, including the source-bound worker cache, raw run, operator journal and coordinator guard receipts. The shared GPU lock was released. The board and Q0 were used only under their assigned scopes. The private branch tip was independently queried by `git ls-remote --heads origin research/wp-0029-cedar-acquisition` after the primary publication and matched its full commit.

## Handoff

eld-rd-reviewer has the primary publication `48016df280f8f0c2f4a807955d9f431744347ecc` for separate CPU authentication of the source order, positions, original spans, BF16 bytes, FP32 means and terminal receipts. Eligibility and CPU readouts belong to subsequent review and scoring. This author operated no blind inputs or other model order. [Deliverable diff](https://github.com/jackgumpe/eledgercare/compare/4d94271a56f550bcf96b76d970f54e4c8b845ad5...48016df280f8f0c2f4a807955d9f431744347ecc)
