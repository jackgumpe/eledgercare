# WP-0025 / 001 — Native H0 process and token receipts

- Report path `docs/agent-reports/eld-repeat-runner/WP-0025/001_2026-11-21_research_eld-repeat-runner.md`
- Reservation [WP-0025 / 001](https://github.com/jackgumpe/eledgercare/blob/842f587e8d223360aaa6058518d999964d304278/INDEX.md#wp-0025-h0-window-repeatability)
- Category research
- Author and publisher eld-repeat-runner, fresh native Codex subagent `/root/repeat25_runner`. Requested effort xhigh. Backend model identifier and effective effort were not exposed.
- Environment Windows, PowerShell, Git, Q0 Python 3.12.10 with `-I -B`
- Timestamp 2026-11-21T20:26:11Z
- Repository `jackgumpe/eledgercare`, branch `research/wp-0025-window-runner`, worktree `eledgercare-worktrees/replay25-runner`
- Base `842f587e8d223360aaa6058518d999964d304278`
- Deliverable `376e82b1fc85a1f28d3f77f505ef9b9891b4446f`
- Decisive execution candidate `43b625bb97d403da99e888966dbf4e781e9674d1`, plans and lease publication `88748016392246031d517efef22c4b3ef48f3057`
- Previous report none in this role. WP-0025 / 002 owns comparative analysis, /003 owns independent execution and review, and /004 owns release and disposition.
- Status ready-for-review. Next owner eld-repeat-reviewer.

## Summary

The non-author operator completed all eight scheduled native B=1 calls. The first call in each cold process matched the historical stock stream through EOS. The other three calls in each process matched the historical hooked stream. Both the stock and hooked modes therefore varied within this eight-call observation. Each valid return contained 284 generated tokens and a separately observed EOS at decision 284. This is an author readback of the runner and receipts. Independent reconstruction and attribution belong to /003 and /004.

## Objective and acceptance criteria

Run the three fixed original PNGs for binder `34054347f091c087a39efe17`, window 1, in two fresh processes under the operator's sole GPU lease. Each process loads the same BF16 model once and executes four calls in the frozen order. Preserve the historical stock terminal recorder in every call and both historical feature hooks in H. Keep exact native output, processed EOS, little-endian uint32 stream, elapsed time, per-process identity and H features. Continue after differences between valid token streams and stop after a binding, safety or receipt failure. [Assignment](https://github.com/jackgumpe/eledgercare/blob/842f587e8d223360aaa6058518d999964d304278/docs/coordination/WP-0025/assignment.md)

## Change inventory

| Action | Path | Purpose |
| --- | --- | --- |
| Added | `docs/research/WP-0025/runner/process.py` | Validates a single process plan against its released SHA-256, calls the frozen sensor, verifies each raw return and seals the slot receipt. |
| Added | `docs/research/WP-0025/runner/preflight.py` | Exercises the runner and abort paths using the archived native returns, original rasters and a CPU resident stand-in. |
| Report metadata, subsequent commit | `docs/agent-reports/eld-repeat-runner/WP-0025/001_2026-11-21_research_eld-repeat-runner.md` | Author report. |

The author pushed only the owned branch. Its deliverable matches the origin query below. CPU test scratch under the runner directory was removed on exit. The model operator wrote the persistent live records under `C:/Users/jackg/eLedgerCare-Speed/WP-0025/review/runs/{p1,p2}`. Only that operator launched either model process. No product code or historical evidence changed in the deliverable.

## Decisions and rationale

`validate_plan` binds all page paths and both PNG/RGB digests to the historical first ordered triple. The worker matches the isolated child environment and interpreter, clean candidate, historical sensor and runtime files, model revision, tokenizer, generation settings, API prompt and 827 expanded prompt IDs. The native cold receipt supplies the observed platform and model/dependency manifests. A single `Native` context contains all four historical `capture.infer` calls; H enables the same two pre-hooks and preserves every hidden row. S records no hidden or pooled state.

Each slot publishes `through-eos.u32le` after reconciling raw and metadata IDs, three page markers, processed selection, step, guard and limits. `receipt.json` follows readback of the binary and validation of all historical artifacts and their hashes. The valid token stream is free to differ from all previous observations. The per-process begin, completion and failure records preserve call ordinal, PID, Win32 CreationTime and clocks. The outer Windows job enforces the hard deadline and resource bounds. The worker checks elapsed time at call boundaries.

## Verification

| Check | Executed result |
| --- | --- |
| `git diff --cached --check` before the source commit | Passed for the two source files. |
| `C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe -I -B docs/research/WP-0025/runner/preflight.py --candidate 376e82b1fc85a1f28d3f77f505ef9b9891b4446f` | Exit 0 on the clean deliverable. The archived S and H streams differ. Both planned orders nevertheless verified 4/4. Altered order, expanded prompt IDs or actual environment failed before load. A changed terminal selection, changed page-count guard, or missing H hidden file stopped after two calls, leaving one verified slot and the second raw return. No torch import or GPU call. |
| `git ls-remote origin refs/heads/research/wp-0025-window-runner` after source push | Matched the full deliverable SHA above. |
| CPU `process.validate_plan` on the two actual released plans, then operator `Q0/venv/Scripts/python.exe -I -B <candidate>/docs/research/WP-0025/runner/process.py <absolute-plan> <sha256>` | Plan SHA-256 P1 `298f2cf3f087da67c6ac967969102a3e7f3c87d5f30f3750a23e1786749e747f`, P2 `80f7e6f28927758bdfb4f989e63b661d36af1e2e8f88857d98b3fc0a7c6301e2`. Both live supervisors recorded exit 0. Release SHA-256 `5509c70ff808edfbe65ab53578c89f0bb9c7e97778cec9317e486789bf6ac74f`. |
| Author read-only Q0 Python readback of both outcome and cold records, every native return, through-EOS file, receipt and hash map | Checked the exact ordered started and verified lists, plan SHA, PID/CreationTime across each receipt, and every artifact SHA against `receipt["artifacts"]`. Each binary equaled `process.validate_return(native, plan)`. All eight passed. |

| Process | Worker PID / Win32 CreationTime | Native load | Worker elapsed | Observed slots and through-EOS stream |
| --- | --- | ---: | ---: | --- |
| P1 | 5132 / 134397659980194392 | 11,498 ms | 170.635 s | P1J1S old stock, P1J2H old hooked, P1J3H old hooked, P1J4S old hooked |
| P2 | 20176 / 134397661708873829 | 10,918 ms | 164.775 s | P2J1H old stock, P2J2S old hooked, P2J3S old hooked, P2J4H old hooked |

The SHA-256 of the 285 little-endian uint32 IDs was `887ff948d9da26e2933d1d2f396dd04c865e43c7efd860aeaf3773bfc6f60705` for the historical stock stream, and `d63703395cdc61e15fb86b3df73f021a56adb823ed563eb8065978023ea1554c` for the historical hooked stream. In every raw return the terminal recorder observed selected ID 1 at the first step after the 284 non-EOS tokens.

## Review map

Review `validate_return`, `verify_artifacts` and `conduct` against the historical capture. Each released process has `sensor/binding.json`, `cold.json`, four `<tag>-begin.json` files, four slot folders and `outcome.json`. H folders include `token_hidden.bf16`, `observed-positions.json`, `pooled.f32` and `capture.json`. Inspect `worker-issued.json` and `process.json` for the separate Windows launcher/supervisor chain. [Author diff](https://github.com/jackgumpe/eledgercare/compare/842f587e8d223360aaa6058518d999964d304278...376e82b1fc85a1f28d3f77f505ef9b9891b4446f) · [Exact plans and release](https://github.com/jackgumpe/eledgercare/tree/88748016392246031d517efef22c4b3ef48f3057/docs/coordination/WP-0025) · [Frozen sensor](https://github.com/jackgumpe/eledgercare/tree/1843cdb7b6279b84b539d3ca1ba7bd0affa1f7dd/docs/research/WP-0024/sensor)

## Risks, disagreements and unfinished work

The observed first-call association is confined to two cold processes on one previously exposed triple. The independent review covers hidden and pool reconstruction, physical source witnesses, guard accounting, cleanup, whole-Q0 preservation and the final classification. The runner author made no model call or independent acceptance claim. No disagreement is outstanding.

## Handoff

eld-repeat-reviewer owns /003 on the exact execution candidate above. eld-coordinator receives the separate report publication SHA and confirmed remote after this report is committed. The established comparison and review sources can consume the sealed slots directly.
