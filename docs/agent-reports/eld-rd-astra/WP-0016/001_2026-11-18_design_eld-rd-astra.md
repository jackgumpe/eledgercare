# WP-0016 / 001 — Token grammar, four-window decode and gate design

| Publication field | Value |
| --- | --- |
| Author and publisher | eld-rd-astra |
| Category and status | Design, ready for independent review |
| UTC | 2026-11-18T13:40:36Z |
| Role and environment | Fresh native Codex team session, local Windows PowerShell and read-only Q0 Python 3.12.10. Coordinator confirms explicit dispatch with `gpt-6.2-astra`, reasoning effort `xhigh`. The backend provides no separate execution attestation. |
| Repository | jackgumpe/eledgercare, branch `research/wp-0016-design`, worktree `eledgercare-worktrees/gates-astra` |
| Engine base | `61bec47689dcdf272a525185013f2dce6335fa24` |
| Frozen design and CPU source | `20d5336ed651d8e260c77149eac3085230020fb0` |
| Subsequent CPU evidence | `59734add4d91bc033e9fcef053280ea02801e6b3` |
| Canonical report path | `docs/agent-reports/eld-rd-astra/WP-0016/001_2026-11-18_design_eld-rd-astra.md` |
| Reservation and assignment | [INDEX /001](https://github.com/jackgumpe/eledgercare/blob/9522d7d181958eb87636a94a5e8588388cf537fb/INDEX.md#wp-0016-grammar-and-cuda-graphed-multi-window-trial) · [Packet assignment](https://github.com/jackgumpe/eledgercare/blob/9522d7d181958eb87636a94a5e8588388cf537fb/docs/coordination/WP-0016/assignment.md) |
| Previous report | First report in this packet |
| Next owners | eld-rd-reviewer for independent review, eld-coordinator for gate disposition and ledger publication |

## Findings

All **129,280 model-output columns** were checked against a real-token grammar. The tokenizer has 128,831 addressable IDs. Four coordinate counters, literal prefixes and UTF-8 label decoding produce 367 reachable states including rejection. There are 341 distinct token transformations. Exact compressed lookup, completion distances and four int32 lane states occupy **509,604 bytes** by CPU layout. The original proposed eleven-row dense M/T already requires 8,532,480 bytes. The full dense construction would require 284,674,560 bytes. Physical GPU residency and scratch remain unmeasured. [Grammar and proof](../../../research/WP-0016/design/grammar.md) · [Full CPU receipt](../../../research/WP-0016/design/evidence/token-proof.json)

Token 70962 spells `]<`. It closes the fourth coordinate and consumes the first byte of the mandatory fork, leaving `F` as the next required byte. At all four coordinate positions, after four digits the only legal immediate next byte is the separator or closing bracket for that position. The greatest minimum distance from a live state to complete prose is 13 generated tokens. Reserving this completion distance up to page/output deadlines prevents a partial header when finite legal choices continue to exist. Empty guard intersections must fail visibly. A legal coordinate string may still encode the wrong geometry or invent a table.

B4 at the supported generation ceiling needs 24,832 block-aligned positions and **6,420.1875 MiB** for K/V, router keys and block summaries in the specified static layout. Independent traces must establish grouped prefill with zero fallback, capture/replay, zero host-blocking synchronization in the claimed decode path, stable storage and suppressed writes after EOS. The original Carbon code's single-row sparse path, dynamic growth and burst readbacks do not supply these properties. [Batch invariants and gates](../../../research/WP-0016/design/batch-and-gates.md)

Both immutable G0 plans passed CPU checks. Each order has six excluded warm-up model windows plus 44 scored model windows. Each arm runs three warm-ups, H (two windows) and A (twenty windows) in its own fresh process. The frozen design also specifies independent full-page score comparisons, Windows-only and neural-only critical correctness, signed recovery per extra neural second, margins and table disagreements as telemetry. [Gate contract](../../../research/WP-0016/design/gate-contract.json) · [Plan and lane receipt](../../../research/WP-0016/design/evidence/protocol-controls.json)

## Objective and criteria

Supply an independently reviewable reference automaton over the real loaded vocabulary, including composite tokens and finite-digit termination. Bind the unchanged baseline, both paired order plans, timing, memory and quality thresholds, parser sensitivity and full-field-of-view design. Describe static per-row KV/cache, guard, graph and EOS invariants for the next gate. CPU corroboration establishes design feasibility for the defined grammar and numerical layout. Actual G0/G1/G2 hardware, quality and performance results belong to the reviewer and coordinator. [Frozen G0 plan receipt](https://github.com/jackgumpe/eledgercare/blob/be8c7f1ea16b99662e614d6eb4a2e4c8923114fa/docs/coordination/WP-0016/g0-plans.json)

## Change inventory

All directory-relative paths in this table are under `docs/research/WP-0016/design/`. The five source deliverables precede evidence and report metadata. [Frozen source diff](https://github.com/jackgumpe/eledgercare/compare/61bec47689dcdf272a525185013f2dce6335fa24...20d5336ed651d8e260c77149eac3085230020fb0)

| Added path | Purpose |
| --- | --- |
| [grammar.md](../../../research/WP-0016/design/grammar.md) | Defines the real-token language, transition proofs, completion rule, inequalities and device representation. |
| [token_proof.py](../../../research/WP-0016/design/token_proof.py) | Builds the byte and token automata, computes equivalence classes and shortest completion distances, and runs real-vocabulary controls. |
| [batch-and-gates.md](../../../research/WP-0016/design/batch-and-gates.md) | Binds batch memory, liveness, capture, evidence, gates and Windows-relative analysis. |
| [gate-contract.json](../../../research/WP-0016/design/gate-contract.json) | Machine-readable thresholds and immutable plan references. Its SHA-256 is `c0122396cbd7d197fb8c006a593018a7a543111c9daea90eeaaaba36425ffff5`. |
| [protocol_controls.py](../../../research/WP-0016/design/protocol_controls.py) | Checks actual plan bytes and synthetic lane, cache-capacity and directional critical-error cases. |
| [evidence/token-proof.json](../../../research/WP-0016/design/evidence/token-proof.json) | Post-freeze CPU stdout as canonical UTF-8 JSON with LF. |
| [evidence/protocol-controls.json](../../../research/WP-0016/design/evidence/protocol-controls.json) | Post-freeze plan and synthetic protocol stdout in the same format. |

The sole subsequent report is the canonical /001 path above. Local diagnostics and canonical receipt copies also reside under `C:/Users/jackg/eLedgerCare-Speed/WP-0016/astra/`. Git effects are ordinary commits and push of the owned branch. No model weights, product code, shared ledger or inference output changed in this work.

## Verification

Run from the owned worktree on the design SHA. Set `$py = 'C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe'`. The commands below only read tokenizer/configuration or plan metadata and use synthetic arrays.

```powershell
& $py -I -B docs/research/WP-0016/design/token_proof.py C:/Users/jackg/eLedgerCare-Q0/WP-0005/models/Unlimited_OCR_2_04809669
& $py -I -B docs/research/WP-0016/design/protocol_controls.py C:/Users/jackg/eLedgerCare-Speed/WP-0016/coordination/plans
```

Both commands exited 0 on the unchanged design SHA. Tokenizers 0.21.4, NumPy 2.2.6, Unicode 15.0.0. The proof checked 47,445,760 table entries against their re-expanded class representation, all singleton byte transitions, real-digit transitions at all 20 coordinate/count states, forced delimiters, reachability and finite structural distance. Canonical token-major, little-endian uint16 transition SHA-256 is `a958eb39797ed1de73eb3fcefadfa325c65a1dc6a0a4e02f4c6dfddcafdbf118`. The saved receipt SHA-256 is `cd7d7d925474549b3d7208e17ce158d1dbcdde946cc6104dc3622939e0a44458`.

Protocol controls preserved the two AB/BA plan hashes and matched original RGB inventories across all arms, without opening the packet PDFs, truth or predictions. The permuted toy cache, immediate/mid-burst EOS, all-dummy case and unchanged sentinels agreed with serial traces. The synthetic four-way matrix had one repair, one regression, zero net, and two novel/changed unflagged errors. Receipt SHA-256 is `58beeed14889089f497d0abda5372467e384b373cb04e3a39f53c8300b3b40b3`. A separate offline tokenizer-wrapper check identified `LlamaTokenizerFast`, 128,831 IDs and disabled cleanup. Selected wrapper decodes matched the Rust backend with torch unimported.

An initial ad hoc tokenizer probe ended with a CP1252 console encoding error while printing a Unicode special-token spelling. Subsequent ASCII-safe output and the frozen exhaustive proof completed normally. An initial staged whitespace check found trailing blank lines and the pre-freeze correction passed `git diff --cached --check`. The source push was independently read back from origin via `git ls-remote --heads` at the full design SHA.

## Limits and handoff

The grammar treats the serialization’s literal block marker as structural. The 449 unaddressable head IDs are ineligible for G1 even in prose. The title-level label extension is admitted by the sensitivity parser while its official-parser effect remains measurable. No synthetic control establishes that the checkpoint will produce acceptable tables, identifiers or speed. Device allocation sizes, graph stability, replay, synchronization, output quality, timing spread and Windows-relative recovery require the released live evidence.

The reviewer can replay the two CPU commands now. The coordinator binds and disposes each finite live gate separately. Further G1/G2 engine implementation remains contingent on the preceding independent gate result. The compressed layout is an implementable reference design with its exact table hash. Captures, CUDA tests, reads of packet truth, private evaluation outputs and family B, and scoring of real predictions were outside this author's assignment.
