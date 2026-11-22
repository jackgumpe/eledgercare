# WP-0030 / 001 — CPU trace of every owner-span write

- Report path `docs/agent-reports/eld-owner-probe/WP-0030/001_2026-11-22_research_eld-owner-probe.md`
- Reservation [WP-0030 / 001](https://github.com/jackgumpe/eledgercare/blob/f19d7fdca840af7b81e6a0bb1edd062d690898de/INDEX.md#wp-0030-cpu-trace-of-every-span-through-the-owner-postings)
- Category research
- Author and publisher `eld-owner-probe`, fresh native Codex subagent `/root/w30_trace`. The session identifies as GPT-6-based Codex. The exact backend variant and effective effort are unexposed. The assignment requested xhigh.
- Environment Windows, PowerShell 7.7.0, Python 3.12.10, PyTorch 2.13.0+cpu, NumPy 2.2.6
- Published 2026-11-22T20:13:00Z
- Repository `jackgumpe/eledgercare`, branch `research/wp-0030-span-trace`, worktree `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w030-trace`
- Base `f19d7fdca840af7b81e6a0bb1edd062d690898de`
- Initial candidate `a8b9c69f6f2dd8430d178341ad3aa91307525e3f`
- Decisive corrected source `447a9e7adc2dbd81933510068742ba1b82bbe84d`
- Evidence deliverable `6c9ecae26aff3b2faa47d90d2f16bcee12b8a191`
- Previous report in this packet none. Historical checkpoint source [WP-0029 / 002](https://github.com/jackgumpe/eledgercare/blob/bb1e075268d06dfa866d46b6a6b9815baa94fe22/docs/agent-reports/eld-owner-probe/WP-0029/002_2026-11-22_research_eld-owner-probe.md).
- Status ready-for-review. Next owner `eld-rd-reviewer`, WP-0030 / 002.

## Findings

Both probes first moved in the favorable direction at **write 1**, a page 1 title reading **Portfolio directory** on both members. The fixed queries on zero matrices gave exact ties and δ = 0. Write 1 produced δ = +0.0006333887577056885 for M1 and +0.0005374550819396973 for M3. Each probe ranked Cedar first on both members. The registry first listed both owner names at write 3. The fixed literal readout captures these earlier responses.

After write 1, each probe reversed sign at the page 1 text block **Schema: Item / Ref / Amount**, write 2. M1 reached −0.007469784468412399 and M3 −0.0004481971263885498. Both stayed negative through write 8, the actual edited printed declaration **Ledger: Alder** or **Ledger: Cedar**. On both horizons their first favorable writes following that declaration were as follows.

| Probe | Previous write and δ | First favorable write after the declaration | δ after the write | Unique leader on both twins |
| --- | --- | --- | ---: | --- |
| M1 | 8, owner declaration, −0.022005513310432434 | 9, page 1 text block `Unit: Unit3`, pointer [1,1,8], DECLARE_UNIT | +0.01377890445291996 | Cedar |
| M3 | 11, header row `Item Amount Ref`, −0.00026670098304748535 | 12, page 1 table row `Service 180 103`, pointer [1,1,11], no parser event | +0.0004915148019790649 | Alder |

**Neither probe ever ranked the correct owner strictly first on both twins at the same observation.** The 12-page traces contain 36 writes and 38 reads per probe. The 30-page traces contain 72 writes and 74 reads per probe. Across all 224 paired reads, the only exact zero responses were the four initial ties. M3 assigned opposite leaders at write 8, with Cedar on the Alder member and Alder on the Cedar member. Their margins were −0.0013106614351272583 and +0.01644178479909897 respectively. Every other nonzero read across the four traces had the same unique leader on both members. None of the 448 member reads reached the frozen top-score cutoff.

The positive sign persisted from write 9 for M1 and write 12 for M3 through the final read. Its magnitude varied. Every transition and attenuation entry includes the preceding and current value, pointer, literal, phase and write count. [Complete transition and ranking records](https://github.com/jackgumpe/eledgercare/blob/6c9ecae26aff3b2faa47d90d2f16bcee12b8a191/docs/research/WP-0030/trace/evidence/findings.json)

| Arm / pages | δ after opening (write 16) | Native pre-target δ | Post-target δ | Strict wins | Decreases in absolute δ | Decreases starting from positive δ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| M1 / 12 | +0.019793041050434113 | +0.009357478469610214 | +0.009533971548080444 | 0/38 | 16 | 14 |
| M1 / 30 | +0.019793041050434113 | +0.006276067346334457 | +0.006367038935422897 | 0/74 | 36 | 34 |
| M3 / 12 | +0.004570405930280685 | +0.0004988275468349457 | +0.0005054101347923279 | 0/38 | 18 | 13 |
| M3 / 30 | +0.004570405930280685 | +0.0004988275468349457 | +0.0005054101347923279 | 0/74 | 34 | 29 |

The two window sequences reuse the same opening. Only the literal of write 8 changed in the archived OCR spans. All 16 opening pooled feature rows differed. Metadata also differed at writes 8–16, including source offsets. From write 17 onward, aligned members shared the same capture, content and features at each write. Source pointers, order and event roles aligned throughout. The first two writes therefore localize a difference in the frozen probe readout before the traversal reaches the changed declaration. The jointly encoded inputs already contain different title features. Causal attribution to a particular operation or broader accuracy would require other evidence.

## Objective and checks

Replay both sides of the four authorized probe/horizon combinations independently from zero. Score the same eventual posting query against both fixed literal anchors after every write and at the separate genuine pre-target attempt. Verify every original checkpoint and typed decision. Localize the first favorable write and enumerate all strict wins, crossings and attenuation.

Each member used the original full-window projection shape in the final window, even though traversal ended immediately after the posting write. The original `matrix.advance` applied the parser events, registry, controller, pops and native posting before calling the observed write. The previous completed write count was 35 for the 12-page native attempt or 71 for the 30-page attempt. A retrospective read followed at count 36 or 72. Each native attempt returned `ABSTAIN / below_threshold_owner`.

| Check or command | Result |
| --- | --- |
| Source parse via Python `ast.parse` for each of the three Python sources and PowerShell `Language.Parser.ParseFile` for run.ps1 | Passed. The staged whitespace check initially found four trailing blank lines, which were removed before the first source freeze. |
| Synthetic signed-margin sequence through `pair_rows` and `summarize` with an initial zero, a pre-eligibility positive micro-response, opposite-sign crossings, a duplicate native observation and a final exact zero | Both first-positive pointers and all seven transition/eligibility counts matched the explicit expectations. |
| `./docs/research/WP-0030/trace/run.ps1 -Candidate a8b9c69f6f2dd8430d178341ad3aa91307525e3f -RunName author-r1` | Exit 1 at the first native posting. The attribute holding fixed owner-anchor tensors shadowed the frozen method used by the native attempt. Only sources.json existed. The two-line correction renamed the attribute and preserved the original method. |
| `./docs/research/WP-0030/trace/run.ps1 -Candidate 447a9e7adc2dbd81933510068742ba1b82bbe84d -RunName author-r2` | Exit 0. All 11 capture routes and fitted tensors authenticated. All four paired traversals completed in 9.15 seconds wall time. |
| `./docs/research/WP-0030/trace/run.ps1 -Candidate 447a9e7adc2dbd81933510068742ba1b82bbe84d -RunName author-r3` | Exit 0. A separate process and scratch directory reproduced all seven deterministic outputs in 9.21 seconds wall time. Direct byte comparisons passed across all seven files. The authenticated sources also matched the first partial run. |
| WP-0029 comparison of four scores and two margins at each of 12 paired boundaries | All 24 member reads matched in score bytes, query SHA-256, matrix/owner-column/read digests, pointer, eligibility, threshold flags and margin bytes. The two independently generated query arrays for each pair matched byte-for-byte. WP-0029 retained reference query digests. The new evidence also preserves the actual 512-byte query per member. |
| Final native parity across two horizons, two arms and both twins | All eight original typed outputs, all field logit hashes, choices and native attempt flags matched. |
| `git diff --cached --check`, normal pushes, then `git ls-remote origin refs/heads/research/wp-0030-span-trace` | Clean final staged checks. Source and evidence commits were visible on origin. Report publication is confirmed to the coordinator after its commit. |

## Change inventory and review map

All items were added under `docs/research/WP-0030/trace/` except the reserved report. [Full source and evidence diff](https://github.com/jackgumpe/eledgercare/compare/f19d7fdca840af7b81e6a0bb1edd062d690898de...6c9ecae26aff3b2faa47d90d2f16bcee12b8a191)

| Paths relative to that directory | Contents |
| --- | --- |
| README.md, run.ps1 | Schema, provenance and packet-scoped CPU launcher |
| inputs30.py | Immutable Git blob admission, runtime guards, raw source metadata and per-row feature identities |
| trace.py | `Readout`, `observe`, `traverse` and historical parity guards |
| findings.py | Source/role alignment, signed arithmetic, sign/attenuation transitions and strict rankings |
| evidence/M1-12.json, evidence/M1-30.json, evidence/M3-12.json, evidence/M3-30.json | All aligned paired observations with per-member score bytes and source identity |
| evidence/sources.json, evidence/parity.json, evidence/findings.json | Archived per-span sources and ordered feature receipts, exact final query/score parity, and both findings for each probe/horizon |
| evidence/runtime.json, evidence/runtime-repeat.json, evidence/replay.json | Two execution receipts, failed observation and direct seven-file byte comparison |
| `docs/agent-reports/eld-owner-probe/WP-0030/001_2026-11-22_research_eld-owner-probe.md` (repo-relative) | This canonical author report, committed after evidence |

The archive authenticated the actual source and token offsets and 1,280 FP32 pooled features per row. The score is the directional owner read of the frozen matrices against the eventual posting query. Native candidate eligibility is a separate field on every row. The hashes and revisions for every source/data blob are in the runtime receipt. [Source catalog](https://github.com/jackgumpe/eledgercare/blob/6c9ecae26aff3b2faa47d90d2f16bcee12b8a191/docs/research/WP-0030/trace/evidence/sources.json) · [Boundary parity](https://github.com/jackgumpe/eledgercare/blob/6c9ecae26aff3b2faa47d90d2f16bcee12b8a191/docs/research/WP-0030/trace/evidence/parity.json) · [Replay receipt](https://github.com/jackgumpe/eledgercare/blob/6c9ecae26aff3b2faa47d90d2f16bcee12b8a191/docs/research/WP-0030/trace/evidence/replay.json)

## Runtime boundary and handoff

The coordinator qualified the isolated CPU environment at `474713bd25e0173cdd239c3715dffd79b02eac8f`. The author processes used single-threaded deterministic CPU FP32 and only the two frozen research probe tensors. Persistent external effects are the three authorized scratch directories under `C:/Users/jackg/eLedgerCare-Speed/WP-0030/trace/` and normal private branch pushes. Native OCR, accelerator calls, new fitting, held-out evaluation and production tests were outside the assignment. Packet B, Q0 and blind inputs stayed sealed.

Independent disposition remains with `eld-rd-reviewer` on the exact source and evidence above. The reviewer received the evidence revision after their independent traversal source froze.
