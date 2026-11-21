# WP-0025 / 002 · Both first calls reproduced the historical stock stream

| Field | Record |
| --- | --- |
| Author, category and status | `eld-repeat-analysis`, research, ready for review |
| Reservation and report path | [INDEX at reservation](https://github.com/jackgumpe/eledgercare/blob/842f587e8d223360aaa6058518d999964d304278/INDEX.md#wp-0025-h0-window-repeatability) · `docs/agent-reports/eld-repeat-analysis/WP-0025/002_2026-11-21_research_eld-repeat-analysis.md` |
| Actual route | Fresh native Codex collaboration session `/root/repeat25_analysis`, requested xhigh. Exact served model and effective effort were not exposed. Published by the author. |
| Environment | Native Windows, PowerShell, Q0 Python 3.12.10, NumPy 2.2.6, tokenizers 0.21.4, pypdfium2 5.15.2, isolated CPU execution |
| UTC timestamp | 2026-11-21T20:29:00Z |
| Repository, branch and worktree | `jackgumpe/eledgercare`, `research/wp-0025-repeat-analysis`, `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/replay25-analysis` |
| Reservation base | `842f587e8d223360aaa6058518d999964d304278` |
| Source frozen before new results | `efcf568373a4745243c084f45f68167cceb89076` |
| Completed source and machine evidence | `a7962d81c3e339f73e30c27eda5ea5bef51e23b3` |
| Model run and release | Execution candidate `43b625bb97d403da99e888966dbf4e781e9674d1`, pinned release and plans at `88748016392246031d517efef22c4b3ef48f3057`. Unmodified Baidu `0480966938291445591f69f08a13b041c073a96a`, historical sensor `1843cdb7b6279b84b539d3ca1ba7bd0affa1f7dd`. |
| Previous / related / next | First report by this role. WP-0025 / 001 covers runner authorship, frozen at [runner source](https://github.com/jackgumpe/eledgercare/tree/376e82b1fc85a1f28d3f77f505ef9b9891b4446f/docs/research/WP-0025/runner). [WP-0024 / 003](https://github.com/jackgumpe/eledgercare/blob/842f587e8d223360aaa6058518d999964d304278/docs/agent-reports/eld-rd-reviewer/WP-0024/003_2026-11-21_review_eld-rd-reviewer.md) records the historical read. Next owner `eld-repeat-reviewer` for /003, followed by `eld-coordinator` for /004. |

## Result

Both stock and hooked modes varied across their four calls. The first call after each of the two cold loads reproduced the historical stock stream. All six later calls reproduced the historical hooked stream. Within P1, the stock calls differed and the hooked calls agreed. Within P2, the stock calls agreed and the hooked calls differed. The first-versus-later pattern describes this fixed order on one exposed three-page input. The observations give no causal estimate for recording, cold state or a particular kernel.

Every slot emitted 284 non-EOS IDs and selected EOS ID 1 at decision 284 after the same 827-token prompt. The terminal event, three page texts and table grids agreed across the two output streams. Each of the four applicable source witnesses bound uniquely in all eight slots. The analyzer received all eight verified slot receipts and both successful process and guard returns. [Machine result](https://github.com/jackgumpe/eledgercare/blob/a7962d81c3e339f73e30c27eda5ea5bef51e23b3/docs/research/WP-0025/analysis/result.json)

### Exact outputs and matched historical streams

`A` below is the original WP-0024 stock stream with little-endian uint32 through-EOS SHA-256 `887ff948d9da26e2933d1d2f396dd04c865e43c7efd860aeaf3773bfc6f60705`. `B` is the original hooked stream, `d63703395cdc61e15fb86b3df73f021a56adb823ed563eb8065978023ea1554c`. The pinned historical ZIP SHA-256 is `37670af4116f543e2d0104b5d3599d88f2e2d06fc092418ee1cf839769430fc6`. The order columns also identify the absolute calls across both processes.

| Absolute call | Slot | Last mode within process | Compared with old stock A | Compared with old hooked B |
| ---: | --- | --- | --- | --- |
| 1 | P1J1S | Fresh load | Exact | First divergence 13 |
| 2 | P1J2H | Switched | First divergence 13 | Exact |
| 3 | P1J3H | Repeated H | First divergence 13 | Exact |
| 4 | P1J4S | Switched | First divergence 13 | Exact |
| 5 | P2J1H | Fresh load | Exact | First divergence 13 |
| 6 | P2J2S | Switched | First divergence 13 | Exact |
| 7 | P2J3S | Repeated S | First divergence 13 | Exact |
| 8 | P2J4H | Switched | First divergence 13 | Exact |

The full agreement and first-divergence matrices share two values in this run. A check mark means exact equality through EOS and first divergence (+∞). The number 13 means unequal streams and first divergence at decision 13 on the shared 13-token prefix. Row and column numbers are the absolute calls above.

| Call | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | ✓ | 13 | 13 | 13 | ✓ | 13 | 13 | 13 |
| 2 | 13 | ✓ | ✓ | ✓ | 13 | ✓ | ✓ | ✓ |
| 3 | 13 | ✓ | ✓ | ✓ | 13 | ✓ | ✓ | ✓ |
| 4 | 13 | ✓ | ✓ | ✓ | 13 | ✓ | ✓ | ✓ |
| 5 | ✓ | 13 | 13 | 13 | ✓ | 13 | 13 | 13 |
| 6 | 13 | ✓ | ✓ | ✓ | 13 | ✓ | ✓ | ✓ |
| 7 | 13 | ✓ | ✓ | ✓ | 13 | ✓ | ✓ | ✓ |
| 8 | 13 | ✓ | ✓ | ✓ | 13 | ✓ | ✓ | ✓ |

Of the 28 distinct comparisons, 3/6 S/S, 3/6 H/H and 10/16 S/H were exact. Those pairs reuse eight observations. Within-process pairs were exact in 6/12 comparisons and between-process pairs in 10/16. At the same within-process ordinal, the two opposite-mode slots agreed in all 4/4 comparisons. The first and fifth absolute calls gave A. Calls 2–4 and 6–8 gave B, encompassing both repeated modes and mode switches, odd and even within-process positions, and both process identities. Same-mode pairs within each process and switches across modes provide no extra independent replicates.

### Literal, geometry and physical source checks

All 12 unequal pairs reproduced the complete four-edit signature, forward or reverse. Among the 16 S/H pairs oriented stock to hooked, three were the original A→B pair, three were the reverse B→A pair and ten had identical final streams. No partial signature occurred. The native emitted character and integer differences in A→B were confined to the following right edges on physical page 1. Other native coordinates, block literals, table cells and visible page text agreed. The later decisions 77, 100 and 146 followed an already different prefix.

| Decision (zero-based) | Printed block | A token → B token | Native right edge A → B | Delta in 0–999 scale |
| ---: | --- | --- | --- | ---: |
| 13 | Portfolio directory | 20375 → 21577 | 399 → 395 | −4 |
| 77 | Schema: Item / Amount / Ref | 21895 → 22476 | 388 → 387 | −1 |
| 100 | Schema: Item / Ref / Amount | 21895 → 22476 | 388 → 387 | −1 |
| 146 | Unit: Unit4 | 939 → 643 | 202 → 201 | −1 |

The bound PDF was `34054347f091c087a39efe17.pdf`, SHA-256 `675367788d2b872511d05b704b98069e8b636d02d07d78095cc4bbeab3e63d5b`. The analyzer re-located the glyph ink of “Ledger: Oak”, “Unit: Unit4”, the header “Item | Amount | Ref” and the row “Service | 180 | 103”. All 32 slot/witness checks had exactly one eligible block or row combining matching words/cells and enclosure of all glyph centers. The active unit declaration retained this binding with both right edges. The separate page-11 window-4 target is outside this input.

### Hooked activations and span means

Each H slot retained 284 observed BF16 rows of width 1,280 following consumption of non-EOS tokens, at absolute positions 827–1110. The analyzer expanded the BF16 bits to IEEE FP32 and accumulated each span's actual member rows in order. All 56 reconstructed FP32 means matched the respective saved bytes. Stock slots have no observed hidden states. EOS has no consumed state.

| H/H pairs | Aligned hidden rows | First differing row | Max absolute hidden difference in FP32 | Aligned pools | First differing span | Max absolute pooled difference in FP32 |
| --- | ---: | --- | ---: | ---: | --- | ---: |
| P1J2H–P1J3H, P1J2H–P2J4H, P1J3H–P2J4H | 284 each | All bit-equal | 0 | 14 each | All bit-equal | 0 |
| P1J2H–P2J1H, P1J3H–P2J1H, P2J1H–P2J4H | 280 each | 0 | 0.890625 | 14 each | 0 | 0.1000976711511612 |

For each of the three H/H comparisons with unequal outputs, all 280 comparable hidden rows and all 14 comparable pools differed. Row 0 held consumed token 128827 at absolute position 827, outside the printed spans. At that row 917 components differed, with maximum absolute difference 0.02734375. Rows 0–12 shared the emitted prefix through the consumed token and had maximum absolute difference 0.09375. The 267 later matches had equal current token IDs, absolute positions and printed-span memberships, with different earlier histories. The four changed coordinate-token positions lacked an identical token at their absolute position and were excluded. Span 0 covered “Portfolio directory” at absolute positions 846–848. It had 1,270 differing components and maximum absolute difference 0.08268231153488159. Every compared pooled span included a row after output divergence. Thus no whole pooled span compares identical generation histories in these three pairs. The per-vector component counts, absolute positions, span memberships and maxima are retained for all six pairs. [Full H/H data](https://github.com/jackgumpe/eledgercare/blob/a7962d81c3e339f73e30c27eda5ea5bef51e23b3/docs/research/WP-0025/analysis/result.json)

## Objective, inventory and verification

The assigned scope was CPU attribution of all slots on b01w01 against both historical streams, with failure-aware matrices, source witnesses, literal and geometry changes, order associations, independent BF16 pool reconstruction and comparable H/H differences. The source froze before receipt of either process's results. The author read only the authorized Q0/public files, historical exposed b01w01 archive records, WP-0025 plans, completed raw returns, and guard evidence needed for this analysis.

| Added path under `docs/research/WP-0025/analysis/` | Purpose |
| --- | --- |
| `README.md` | Frozen definitions, alignment domains, criteria and command |
| `evidence.py` | Historical artifacts, tokenizer/parser reconciliation, glyph checks and independent FP32 pool reconstruction |
| `compare.py` | EOS identity/divergence, directed signature, token/literal/semantic/box edits, H/H feature comparisons and order profiles |
| `analyze.py` | Plan, slot, stop, cold-process and lease verification, matrices and machine result |
| `preflight.py` | Replay of the historical pair, pool-corruption rejection, partial alignment and manufactured decision/undefined checks |
| `result.json` | Complete machine result, 140,773 bytes, SHA-256 `899bf79acdf3d051a99b232bb30a383bfb0f356b9e861c62dbc11cdbc7fceffb` |

The canonical report is the only additional metadata path in the later publication commit. The analysis created short-lived manufactured/preflight and byte-repeat output files inside the owned analysis directory and removed them. It published source and evidence to its owned remote branch. The GPU was operated by /003. No model or GPU process was launched by the analysis author. No blind material, training, causal intervention or memory evaluation was opened or run.

From this worktree, the exact decisive PowerShell command was

```powershell
$env:CUDA_VISIBLE_DEVICES = '-1'
& 'C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe' -I -B docs/research/WP-0025/analysis/analyze.py 'C:/Users/jackg/Asp.net Projects/eledgercare/docs/coordination/WP-0025' 298f2cf3f087da67c6ac967969102a3e7f3c87d5f30f3750a23e1786749e747f 80f7e6f28927758bdfb4f989e63b661d36af1e2e8f88857d98b3fc0a7c6301e2 docs/research/WP-0025/analysis/result.json
```

| Executed check | Result |
| --- | --- |
| `$py -I -B docs/research/WP-0025/analysis/preflight.py` via PowerShell invocation operator, with the same interpreter above | Frozen-source test passed for both old streams, four geometry changes, physical glyph binding, 284 historical hidden rows, 14 old reconstructed means, damaged pool, alignment and seven schedules. |
| Manufactured empty plans/runs and sealed scratch slots, then removal of the P2J2S receipt | Full absent run returned eight undefined slots. The complete manufactured SHHS/HSSH returned all eight. The missing second receipt in P2 preserved five verified slots and left P2J2–P2J4 undefined. Scratch data were deleted. |
| Decisive command above, then the same command with unused destination `result-repeat.tmp` | Both exited 0, eight verified slots, zero issues, identical complete artifact hash. Temporary repeat file deleted after hash comparison. |
| Inspected external `coordination/leases/window-repeat-r1/{p1,p2}-issued.json`, `*-device.jsonl`, `*-returned.json` under WP-0025 and coordinator Q0 receipts | Admission free memory 14,817 / 14,830 MiB. Sampled device-use maxima 8,564 / 8,551 MiB over 83 / 80 samples. Exit 0, empty guard reason in both. Final free memory 14,830 MiB per return. Q0 before and after inventory bytes shared SHA-256 `1999f59e67c5c313d443f6bc72347c52bdd6dac961c21962b5e0920fcc1787f6`. /003 owns the independent resources and cleanup audit. |
| `git diff 842f587e8d223360aaa6058518d999964d304278 HEAD --check`, clean-source branch status and `git ls-remote --heads origin research/wp-0025-repeat-analysis` | An initial staged whitespace check flagged trailing blank lines in the five new sources. They were removed before the definitive source freeze. The frozen diff and result diff passed. Remote source and machine-evidence revisions were confirmed. |

## Review and handoff

The independent reviewer has cross-checked the published machine artifact against raw evidence and reported agreement for all 28 pairs, 16 historical comparisons, processed stops, applicable witnesses and all six H/H numerical comparisons. The reviewer's canonical /003 and coordinator's /004 own formal disposition. The first observed disagreement at decision 13 has no measured logit margin. Neither the later changed boxes nor the differing H/H activations identify which internal component caused the output to change. No memory read or downstream owner outcome was measured. [Frozen source](https://github.com/jackgumpe/eledgercare/tree/efcf568373a4745243c084f45f68167cceb89076/docs/research/WP-0025/analysis) · [Source and result diff](https://github.com/jackgumpe/eledgercare/compare/842f587e8d223360aaa6058518d999964d304278...a7962d81c3e339f73e30c27eda5ea5bef51e23b3)
