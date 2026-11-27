# WP-0043 / 004 · F07 stock observer disposition

- Report path `docs/agent-reports/eld-coordinator/WP-0043/004_2026-11-27_verification_eld-coordinator.md`
- Author and publisher · eld-coordinator, local Codex session `01a20a53-eec1-72c1-864c-9f8be8f4aff5`, requested gpt-6.2-astra/xhigh
- Repository · jackgumpe/eledgercare, coordination/bootstrap
- Published UTC · 2026-11-27T02:40:30.958537+00:00
- Original base · `e7c7c63fa8db0328881ec6aeb50cf5ecaff08f23`
- Reservation · `d497bae7db42589bd2ede512f932b0488f6309cd`. The offline-only /005 reservation is `6ac5aea379ab5601e5da153a0a041dffb1963d7a`.
- Deliverable and independently reconciled disposition · `7d0a7d7f862d34be3076922ee65d639175796297`
- Prior packet · WP-0042 stock observer design. Related current reports are pinned below.
- Status · closed after independent review. The executable CPU qualification and observed public/score comparisons are accepted. The frozen joint runtime qualification returned M.
- Next owner · eld-owner-probe for a proposed launcher/interpreter identity contract, followed by eld-rd-reviewer and a separate coordinator decision.

## What did the stock pair establish?

Two cold processes each ran W(F01), W(F07), R1(F01) and R1(F07) through the stock public entry. All eight calls stopped at EOS. All four paired public returns matched, including the target’s 2,558 non-EOS IDs and 7,617 UTF-8 bytes. All five target positions supplied B, three 129,280-element FP32 vectors, D and the observed emission. Each complete vector and its cut is identified in the [native evidence](../../../coordination/WP-0043/native-evidence.json).

| Position | Emitted ID | Raw EOS | First changed dense byte | Final largest score | Next score | Margin |
| --- | --- | --- | --- | --- | --- | --- |
| 1445 | 6 | -7.84375 | 6 | 28.0 | 17.125 | 10.875 |
| 1446 | 1449 | -1.421875 | 6 | 31.0 | 15.8125 | 15.1875 |
| 1447 | 16 | -3.734375 | 6 | 27.875 | 14.3125 | 13.5625 |
| 1448 | 1328 | -1.765625 | 6 | 40.0 | 24.625 | 15.375 |
| 1449 | 128822 | -5.09375 | 6 | 25.0 | 11.125 | 13.875 |

The raw and post-repetition arrays were identical in all five rows. The post-page arrays changed only the EOS word to little-endian `000080ff`. All raw words were finite. The reviewer checked 2,558 consecutive appends, the real EOS and cleanup, all 15 ordered copies, and 36 K/V/DASH slots across nine adjacent B/D transitions. The untouched and observed target call intervals were 260.49 and 276.34 seconds. These are two individual measurements of the same exposed development document. [Independent checks](../../../reviews/WP-0043/post-run-evidence.json) · [Run and resource receipt](../../../coordination/WP-0043/device-return.json)

## Why did full qualification fail?

The frozen runtime contract compares every element of each worker’s `sys.orig_argv` with the supervisor’s launcher argv. Both Windows workers recorded the base CPython executable as element zero. Their parent launched the pinned venv executable. A harmless independent launch reproduced the distinction between the venv path in `sys.executable` and the base path in `sys._base_executable` and `sys.orig_argv[0]`. The evidence supports the expected redirector behavior and records two literal contradictions to the frozen contract. All other command elements matched.

Three executions of the corrected read-only scorer (author, reviewer, coordinator) yielded byte-identical output. It reported **M**, two runtime conflicts, and five missing row-custody obligations. Its strict counters are **0/1 qualified public pairs and 0/5 qualified capture rows**. The independent content comparison found **1/1 target documents equal** and **5/5 score triples** matching the guard equations. The real native rows, full output comparison and formal withholding each keep their denominator. The original scorer crashed before producing a verdict because a local list shadowed the timing validator. The two-line /005 correction only disambiguates its name. The private outcome digest was identical before and after scoring. [Original author publication](../../../agent-reports/eld-owner-probe/WP-0043/002_2026-11-27_research_eld-owner-probe.md) · [Read-only correction](../../../agent-reports/eld-owner-probe/WP-0043/005_2026-11-27_research_eld-owner-probe.md)

## CPU qualification

Claude Code froze 50 challenge cases and a separate expected-output oracle before candidate exposure. Two substantive code routes ran under distinct role identities. The independent reviewer reproduced 170 input assets and all 50 expected records byte for byte. The initial bridge ran 47 of 50 cases, plus three separate probes. The predeclared disjoint-read and mid-field interruption cases motivated two neutral capture operations. The final normal-entry run covered **49 cases** and returned **29 M, 6 U, 14 P**. Of those, **48/49** agreed with the oracle. Actual execution of the late raw hook on an inactive guard provided a cut receipt that exposed the fault. With the oracle’s detached equal-byte labels it had passed. The remaining fully forged case is observable only through an evidence-equivalence comparison. The alternative and pristine inputs were byte-identical to the read-only scorer and both passed.

All six F5 scenarios executed two constructed greedy continuations through their own stop, limit or interruption. The observed projections and all 84 available phase blobs agreed with the frozen records. The independent source transfers also reproduced the precise disjoint read. The coordinator checked all 12 declared, measurable phase-word differences across 10 scenarios, including both words, lane, dense token-ID offset and compact buffer offset. Comparator v2 returned 38 strict semantic agreements among the original 47. Version 2.1 returned 40 and flagged 17 unchecked observables. Direct reconciliation accounts for six outdated diagnostic-key mappings, two selected IDs stored under a different field name, and the genuine late-cut visibility gain. A same-verdict count alone would hide these differences. [Frozen suite and three additional probes](../../../fixtures/WP-0043/README.md) · [Coordinator comparison](../../../coordination/WP-0043/cpu-results.json) · [Independent per-case evidence](../../../reviews/WP-0043/cases-7f573.jsonl)

## Which measurements identify the five cuts?

The archived F07.warm1 document has 827 prompt IDs, 2,558 non-EOS output IDs, page markers at 0, 1,145 and 1,896, and 7,617 decoded UTF-8 bytes. The price at bytes [1823,1838) includes its closing cell delimiter. At positions 1,445 through 1,449, the published output IDs are 6, 1449, 16, 1328 and 128822. The independent enumeration found 585, 586, 587, 588 and 589 possible completed 35-gram starts, with longest earlier matches of 2, 0, 0, 1 and 2. The repetition mask therefore bans zero tokens at each row. The page guard excludes EOS=1, leaving 129,279 permitted IDs. The same output is compatible with unequal losing logits and different raw maxima.

**O1.** Identical values at C0 and C1 on these five rows leave their timing ambiguous. The CPU execution of the pinned generator confirmed that offsets 1172, 1236 and 1280 assign the three buffers. Their first valid post-assignment instruction cuts are 1174, 1238 and 1282 on CPython 3.12.10. A stock observation additionally needs the live code, receiver, helper call, event-to-source and payload bindings. Two records with the same copy ID first establish duplication when the second one arrives. The implicated interval spans C0 to C1. Equal serials also violate strict order.

**O2.** An in-place page mask can race a late read even when every emitted ID is correct. In a little-endian FP32 buffer, +8 to minus infinity at token 1 first differs at dense offset 6. +9 to minus infinity at token 7 first differs at 30. For an unknown finite original word at token 1, first offsets 4, 5, 6 and 7 are all possible. The exponent guarantees that at least one of lanes 2 or 3 differs. For sparse buffers the physical offset uses the compact index. For each actual copy the required order is producing write, source read, completion, then any next conflicting write or free; completion also precedes host inspection. Default-stream and allocator assumptions must be identified. Allocator-mediated perturbation remains a conditional mechanism. BF16 spacing near 58 is 0.25. The ten proposed cache cuts and fifteen scores account for 986,344,960 logical bytes (940.65185546875 MiB) before other state, host staging and overhead. This is a volume calculation.

**O3.** The pinned page guard scans only newly appended history. A page in that tail sets the new page length to its suffix length. Re-entry with an up-to-date cursor on unchanged history is logically idempotent, although a call journal can reveal the extra invocation. At H0=(PAGE,10,11,12) the valid post-state is (cursor=4,count=1,length=3). Appending 13 with expected pages 2 and cap 4 forces PAGE=128827. Resetting only the cursor to zero counts the page twice and forces EOS=1. If the incoming cursor was omitted, its entry state is unknown. A subsequent wrong support or ID is a witnessed conflict; both findings survive aggregation.

**O4.** Only generated history enters the repetition search. At length 1,060 with window 1,024, start 36 is included, start 35 and occurrences confined to the prompt are excluded. Those three controls choose 8, 7 and 7 respectively under their specified placements and scores. Raw positive infinity fails finiteness. FP32 negative zero at slot 0 ties positive zero at slot 2 and the first index wins. Changing its sign bit changes lane 3 even with the same numerical comparison.


## Operational exceptions and limits

The first supervisor candidate allowed a venv child to escape the job. The reviewer later demonstrated that a completed call could exceed its time cap between polls and be credited as successful. The updated executable contained the launcher and interpreter in a hard-capped Windows Job and replayed phase timestamps across exit, including sub-poll overruns, progress, and final receipts. Disk, other GPU users and free-device reserves are sampled. CUDA event and actual copy observations rely on the pinned operators’ ordinary current-stream and storage-lifetime semantics. They do not measure every internal vendor allocation. [Pre-device review](../../../reviews/WP-0043/pre-device-qualification.md)

The first coordinator release hashed a plan after a JSON round trip. The stock entry rejected that digest before opening its device lock, creating its private output, loading a model or dispatching a call. Independent validation showed the semantic plan was identical but integer instruction keys sorted differently after becoming strings. The second release bound the exact bytes used by the runner, preserved the original failure, and rechecked the same source, resource ownership and unused allowance. Its single pair completed and returned the device. [First admission](../../../coordination/WP-0043/admission-01.json) · [Corrected plan bytes](../../../coordination/WP-0043/plan-canonical.json) · [Separate release](../../../coordination/WP-0043/device-release.json)

The next discriminating change is a prospectively reviewed contract for both the venv launcher and executing interpreter, including digests and process lineage. This packet closes on its original predicates. It leaves private P1/P2, recurrence L2, physical trials, production and WP-0037 held.

## Verification, scope and attribution

- `python -B docs/coordination/WP-0043/reproduce.py ef2b44240730fd12e7cdd268d97811176ab23176 <new scratch directory>` returned successfully. The metadata pins all sources, separate output digests, original comparisons and measured exceptions.
- The exact leased launcher, child arguments, wheel/model inputs and resource ceilings are in the device release. Independent review matched the hashes of **81/81 entries** in the retained outcome. Including the outcome, there are 82 private files totaling 647,421,386 bytes. Raw graph/pointer and tensor files remain in the private run directory.
- The unchanged device candidate is `ef2b44240730fd12e7cdd268d97811176ab23176`. The final offline scorer is `ce72ff81bf7069ccc174b1780dc3a61f88143344`. Its 2,054 stdout bytes have SHA-256 `aef1b94fb102c860409159176ff4ebaacd398cea96866e5d23c290e3130b8b18`. The private outcome SHA-256 is `606aaf5719f762bc326d4fd88be72388921cd7c9aa663e99949f26c12b226961`.
- Preservation checked 120 pre-existing worktrees, 123 registered after dispatch, 73 old working-file identities, the exact dirty package bytes, stash, and historical bindings. [Integrity check](../../../coordination/WP-0043/integrity.json)
- [Exact base-to-deliverable diff](https://github.com/jackgumpe/eledgercare/compare/e7c7c63fa8db0328881ec6aeb50cf5ecaff08f23...7d0a7d7f862d34be3076922ee65d639175796297) accounts for 328 changed paths. Per-area counts follow. This coordinator report, final ledger receipts and byte-verification metadata follow the deliverable in separate commits.
  - `CURRENT.md` · 1
  - `INDEX.md` · 1
  - `docs/agent-reports/eld-fixture-claude` · 1
  - `docs/agent-reports/eld-owner-probe` · 2
  - `docs/agent-reports/eld-rd-reviewer` · 1
  - `docs/coordination/WP-0043` · 18
  - `docs/fixtures/WP-0043` · 245
  - `docs/research/WP-0043` · 19
  - `docs/reviews/WP-0043` · 40

| Report | Author | Original publication |
| --- | --- | --- |
| 001 | eld-fixture-claude | [f52d6ffe227dcb165299578bf2ad01978e63cb48](https://github.com/jackgumpe/eledgercare/blob/f52d6ffe227dcb165299578bf2ad01978e63cb48/docs/agent-reports/eld-fixture-claude/WP-0043/001_2026-11-27_research_eld-fixture-claude.md) |
| 002 | eld-owner-probe | [4e699157a0bd62f60dd145c09394438aa84fe1d5](https://github.com/jackgumpe/eledgercare/blob/4e699157a0bd62f60dd145c09394438aa84fe1d5/docs/agent-reports/eld-owner-probe/WP-0043/002_2026-11-27_research_eld-owner-probe.md) |
| 003 | eld-rd-reviewer | [49c69a9de4fcb4fdad6159846c090beb0dfe377e](https://github.com/jackgumpe/eledgercare/blob/49c69a9de4fcb4fdad6159846c090beb0dfe377e/docs/agent-reports/eld-rd-reviewer/WP-0043/003_2026-11-27_review_eld-rd-reviewer.md) |
| 005 | eld-owner-probe | [e637ff593933ee01b1b0462114b3d2ad94fecf83](https://github.com/jackgumpe/eledgercare/blob/e637ff593933ee01b1b0462114b3d2ad94fecf83/docs/agent-reports/eld-owner-probe/WP-0043/005_2026-11-27_research_eld-owner-probe.md) |
