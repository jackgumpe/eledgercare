# WP-0043 / 002. Which stock observation did the recorder actually read?

The archive fixes five consecutive decisions in one synthetic F07 document. Can a recorder identify the exact reads on both sides of two in-place guards, and can it preserve the entire native public return on a second cold load? The first question admits constructed CPU controls. The second requires a stock pair on the pinned runtime. The current native return is **U, 0/5 complete native rows and 0/1 matched complete public pairs**. The historical output supplies five indexed public IDs.

## Result and authorship

- **Author and publisher** — eld-owner-probe, Codex CLI child 01a21a88-678f-7ef3-ae76-cc13b78dde43. Launch specified gpt-6.2-astra and xhigh. Windows x64 CPython 3.12.10. This report records author verification.
- **Repository and branch** — jackgumpe/eledgercare, research/wp-0043-stock, w043-author. Base d497bae7db42589bd2ede512f932b0488f6309cd, executable deliverable ef2b44240730fd12e7cdd268d97811176ab23176, CPU scorer 7f573001f8b0a41daabe37c571789f691854c357. The report is a separate publication after execution.
- **Reservation** — WP-0043 / 002, research, docs/agent-reports/eld-owner-probe/WP-0043/002_2026-11-27_research_eld-owner-probe.md. Sole coordinator's INDEX line 1569 at the base revision and the packet assignment bind this author. This is the author's first packet report. Related reports are WP-0043 / 001 (fixture author) and / 003 (non-author reviewer). [Assignment](../../../coordination/WP-0043/assignment.md)
- **Status** — ready-for-review. Next owners are eld-rd-reviewer for independent scope and findings, followed by eld-coordinator for disposition. The coordinator alone owns any future resource decision. The worktree and external scratch are exclusive to this role.
- **UTC publication preparation** — 2026-11-27T01:59:34Z.

## What fixes the native cuts

For row \(k=0,\ldots,4\), the prefix \(H_k=x[0:619+k]\) contains generated tokens only. Its length is \(h=619+k\), the consumed generated index is \(618+k\), the consuming model position is \(t=1445+k\) and the emitted index is \(619+k\). The prompt has 827 IDs. The archived document has 2,558 non-EOS IDs, 7,617 UTF-8 bytes and page markers at generated indices 0, 1145 and 1896. The target cell including its closing delimiter spans bytes [1823,1838). A separate net-line price spans [1880,1886). Both print the same price.

| k | Consumed index | Position t | Emitted ID | History length | Candidate starts | Longest earlier suffix |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 618 | 1445 | 6 | 619 | 585 | 2 |
| 1 | 619 | 1446 | 1449 | 620 | 586 | 0 |
| 2 | 620 | 1447 | 16 | 621 | 587 | 0 |
| 3 | 621 | 1448 | 1328 | 622 | 588 | 1 |
| 4 | 622 | 1449 | 128822 | 623 | 589 | 2 |

For order \(n\), window \(w\), compare every generated start \(i\) from \(\max(0,h-w)\) through \(h-n\), inclusive. A matched prefix of length \(n-1\) bans the successor \(H[i+n-1]\). Here \(n=35,w=1024\). None of the 2,935 starts matches the 34-token suffix. The page cursor advances from \(h-1\) to \(h\), with one marker and \(h-1\) tokens since that marker. With three expected pages and a 20,000-token cap, the page guard excludes only EOS, ID 1.

For a finite FP32 vocabulary vector \(r\), let \(M_A(r)_j\) copy the original four bytes if ID \(j\) belongs to the allowed set \(A\), and write negative infinity otherwise. If \(B\) is the repetition ban set, \(P\) the allowed page set and \(V\) the vocabulary, then C0 is \(r\), C1 is \(M_{V\setminus B}(r)\) and C2 is \(M_{P\cap(V\setminus B)}(r)\). The composition follows by checking whether each ID satisfies both membership tests. On a nonempty finite support, greedy selection returns the first global ID attaining the largest remaining value. An empty intersection followed by an integer argmax violates both nonemptiness and emitted membership.

On these five archive rows C0 and C1 would be equal for every finite raw vector. Reading C1 twice can therefore mimic all score bytes while missing the C0 event. Actual executing code, bytecode offset, frame, receiver, argument, source storage, distinct capture serial and copy-completion ancestry distinguish these observations under recorder custody. Reusing one event breaches strict serial order and unique ownership simultaneously. Erasing independent provenance and substituting an internally indistinguishable complete record leaves a genuine identifiability limit. The executable checker cannot detect an adversary who controls the entire journal and presents exactly the same input to the scorer.

If \(r_1\) is finite, writing negative infinity (little-endian 00 00 80 ff) at EOS must change at least one of lanes 2 and 3 jointly encoding the exponent. The first differing lane can be earlier. For +8.0, 00 00 00 41, the first differing lane is 2, dense byte 6. For -1.0, 00 00 80 bf, it is lane 3. At ID 7, +9.0 versus negative infinity first differs at dense byte 30. A sparse serialization uses \(4s+\ell\) for compact slot \(s\) and lane \(\ell\), and \(4j+\ell\) for global ID \(j\). The archive provides no raw logits to fix a first differing lane. For a retained allowed +0.0 slot changed to -0.0 at C1, the first difference is lane 3. C2 may agree with C1 and still disagree with the composed mask of C0. Both comparisons run independently.

The B cut holds layer 11 inputs, the actual forwarded lower-layer output, the 11-plus-one cache-length signature and live page/router/generator state. D follows the native selection and non-EOS append. The journal binds the actual dispatch, 12 selected layer paths, guard call entries and PY_RETURN, layer-local activation and cache changes, and the resumed generator through terminal EOS and cleanup. A complete candidate requires the full typed, source-qualified dependencies and the complete untouched/observed document. For five abstract row statuses with M preceding U preceding P, exactly 211 of the 243 assignments contain a conflict, 31 contain missingness only and one is complete. Counterexamples and missing evidence are retained independently. No performance hypothesis was tested. Observation overhead, allocation peaks and fidelity generalization remain unmeasured.

The predecessor's operative definitions, state-transition derivations and full worked examples remain applicable to these stock arms. Several typographic characters in the frozen executable README were misencoded during editing. Documentation-only successor 257bbdacf214285de03089b82a16c31bb27ad106 restores the text in the README and leaves all executable bytes unchanged. [Pinned predecessor design](../../../research/WP-0042/design.md) · [Cut definitions](../../../research/WP-0042/source-cuts.md) · [Scoring contract](../../../research/WP-0042/scoring.md) · [Pinned predecessor revision](https://github.com/jackgumpe/eledgercare/tree/cd563dd06932a2cdecad4932b39d030efbe06699/docs/research/WP-0042)

## Candidate and actual operating surface

The proposed stock run uses two isolated cold processes. Each calls the normal delegated stock infer with return_dict=True in this order: F01 warm-up, F07 warm-up, F01 first warm repeat, F07 first warm repeat. Each process continues through actual native EOS or length termination and writes its public return. Only the last observed call installs the probe. Four-call provenance in both processes and the target public projection carry separate obligations. At most two loads and eight calls exist in the fixed parent/worker loops. No automatic retry exists. The offline native scorer reads the one assigned run directory and pinned Git objects. Its CLI does not take a fixture contract or user raw-logit ground truth.

The observed worker captures real interpreter cuts in pinned Python code, including the actual attention return in attn_outputs[0]. Single-thread, default-stream launch receipts bind the score producer, both real guard operators, copy and greedy consumer. The recorder preallocates a 16 MiB pinned arena and completion event. For element width \(e\), shape index \(j\), strides \(s_i\) and storage offset \(o\), logical element \(j\) starts at allocation-relative byte \(e(o+\sum_i j_i s_i)\). It coalesces only contiguous trailing dimensions and issues cudaMemcpyAsync D2H runs on the observed stream. The event must complete before host access and the native next writer can resume. There is no device packed intermediary. The source map, allocator counters, independent event and destination bytes are journaled. For a 2-by-2 view with strides (1,2) and four-byte elements, offsets 0,8,4,12 give the required logical order. Source spans beyond the configured bounds fail qualification. This proves address enumeration given valid tensor metadata. Opaque backend stream behavior and hidden workspace allocations remain conditional. CPU bytes cannot establish actual CUDA ordering.

The constructed continuation exercises both arms' own score programs, executes first-global-ID greedy selection and stops before appending EOS. From the declared prefix, induction on non-EOS steps yields exactly the appended suffix in order. Two runs can agree on the first five tokens and differ on a later ID or stop. A supplied document projection exercises the comparison only. Actual native stop would be determined by the pinned public infer return, append chronology, EOS/cleanup cuts and the complete public pair.

Native read-only plan inputs bind Q0 harness 9e73ef86600b5e16f74b056676a6d3a4f1474058, reader 0480966938291445591f69f08a13b041c073a96a and archive f5e68668a5999a12ba399eb0f5103ffa835e4b30. All original 12-, 13- and 15-page inputs and the prior brief were read by this author under the assigned scratch path. The source resolves 43 bytecode cuts and two guard return maps, without model import. [PDF and attachment digests](../../../coordination/WP-0043/inputs.json) · [Source](../../../research/WP-0043/bindings.py) · [Probe](../../../research/WP-0043/native_observer.py) · [Transfer](../../../research/WP-0043/transfer.py)

Proposed parent argv, one argument per line, in the owned w043-author worktree:

~~~~text
C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv\Scripts\python.exe
-B
-u
C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\w043-author\docs\research\WP-0043\stock.py
run
~~~~

Each child's argv retains the same interpreter, -B and -u, then the sibling native.py, _worker and its arm, untouched or observed. The plan fixture hashes are F01 893d08ddfc87ef6a18f846d9119d9ba68566d7914aef4bcdc47de0f991c7026f and F07 15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3. All four raster digests and exact kwargs travel in the plan's stdout. An actual resource decision must also bind the full plan digest generated by native.bytes_json(native.plan()), independent review revision, qualified runtime and model bytes, present driver, observed device ownership, approved resident PIDs, UUID, live UTC interval, exact candidate tree, fresh destination and exclusive handle. The plan alone supplies no lease. The parent validates 18 model-file and 32 wheel identities during authorized native preflight. This author did not initiate that preflight.

## Resource and stop evidence

The hard host allocation controls are the 15 GiB aggregate committed-memory Windows Job for each worker tree and the single 16 MiB preallocated pinned host pool. The runtime sets the per-process PyTorch allocator ceiling to 10 GiB. The proposed GPU must begin with 11 GiB free and preserve at least 2 GiB free by sampled whole-device observation. Backend workspace outside PyTorch and opaque Windows device attribution remain unqualified. Disk starts above 4 GiB free, with a 1 GiB free reserve, 2.5 GiB output, 512 files, aggregate 32 MiB of logs at completion, 1,792 MiB unique tensor archive, 96 MiB observed journal and 256 KiB timing receipts per child. Ten logical cache captures sum to 978,588,160 bytes and 15 score vectors sum to 7,756,800. The limits allow other measured dependencies to consume remaining space. The historical comparison is 7,480,541,184 B peak GPU reserved, 11,063,623,680 B sampled private process memory and 273.43 s on the prior F07 warm repeat.

A 7,200 s total interval, 900 s per preflight/load interval, 1,200 s per call and 360 s without retained observed forward progress apply. Only every sixteenth genuine observed append resets that clock. Untouched and the uninstrumented warm-ups therefore have an effective 360 s call ceiling. A return from a phase closes its interval and completion requires every closed interval and the final interval to meet its deadline. Polls can delay detection, particularly if a process enters a new phase during a device query. A 1 MiB receipt and one file are reserved at exit. Archive and journal writers check bounded sizes; process census, disk, logs, file totals and GPU free estimates are sampled. The parent retains partial evidence, kills only the owned worker tree and refuses a retry into the existing target.

The earlier supervisor credited an exit between polls despite a completed phase having overrun. The amended supervisor records every transition and progress sample on the Windows cross-process monotonic clock, checks completed phases as well as live deadlines, and validates the complete sequence on exit. Against a 0.25 s test ceiling and 1 s poll, the 0.032 s call completed. The 0.453 s call completed between polls and was rejected at exit for its measured interval. The 2.5 s sleeper was rejected while still active about 1.063 s after process launch. Job membership was true for both launcher PID 23020 and actual interpreter PID 22636. Device telemetry in this harmless timing test was explicitly simulated. This proves the rejection path. It does not bound hardware poll latency. [Supervisor](../../../research/WP-0043/native.py) · [Timing verifier](../../../research/WP-0043/timing.py) · [CPU control](../../../research/WP-0043/check_deadline.py)

## Author verification

All 26 subprocess commands in the final author receipt exited 0. The command sequence was archive, plan, absent native, real Job membership, seven independent constructed capture/score pairs, a real supervisor deadline control, three additional capture/score pairs and a callee control. Each capture used the normal command with a case JSON. Each score reopened its exported evidence and independent contract JSON via the read-only command. A finite decision program executes separate untouched and observed histories in the first seven cases. The last three directly exercise algebraic/provenance predicates. No outputs from the fixture author or reviewer were supplied to this scorer.

| Author case on ef2b4424 | Verdict and first observed divergence | Diagnostic evidence |
|---|---|---|
| Complete two-row active control | P | Two correctly ordered guards and both executed documents identical |
| Arbitrary compact fragment | M at C0 raw | ID 7 read early, complement read late; separate copy receipts and source/payload conflicts |
| Omit entire second row, interrupt at index 1 | U at row 1 entry | Row, history, guard state, phases and selection absent; short public document and terminal remain incomplete |
| Five price IDs then common tail 8 and EOS | P | Independent continuations generate the same prefix, tail and true stop |
| Same five then tail 9 | M at public document | Earliest public ID discrepancy survives the five matched field tokens |
| Same five and tail 8, token limit reached instead of EOS | M at terminal | Same public IDs, different terminal reason |
| Same non-EOS history, observation ends before EOS | U at terminal | Missing terminal without measured contradiction |
| Empty support, integer selected | M at C2 | Both empty support and emitted membership violation retained (observed ID 0, support size 0) |
| Reuse C0 receipt as C1 | M at C0 | Duplicate event and strict-order failure jointly implicate C0 and C1; measured offset 6 in C1 conflicts with its required offset 42 |
| Write -0.0 in an allowed +0.0 slot at C1 | M at C1 | ID 1, lane 3, dense/compact offsets 7/7, 00000000 to 00000080; both C2 comparisons to original C0 and controlled input detect the preserved corruption |

The actual pinned Python page-guard body ran on CPU values under a CPython instruction monitor. It entered at offset 2, returned at offset 520 with the original score object, and advanced its observed (scanned, marker count, page length) from (0,0,0) to (2,1,1) on [2,0]. This process recorded an empty intersection of loaded modules with {torch, transformers, pypdfium2}. Archive, normal plan and native scorer ran without model execution. The source-only resolver found 43 statically bound sites. Native scorer yielded zero complete native rows and zero matched public pairs against the scheduled five and one.

An earlier author run on 20124bc7a68248ab85f0d4e8b9a67d53cb0adb1d exercised seven of the cases, resource membership, real CPU guard return, archive, plan and absent native, and exited 0. Its retained receipt SHA-256 is a24cb320444783008e0da05c0410ea337ab1440e0839acf2b1a015381d8294e8. Final receipt 1e6b6b3190841d63caff43581e4a74fe97d7f93866511e68021e43b5a0597bdc and exact final author driver 720520e4f787080f730d158d094d93d4bd536470640829f34cc29c3e7a1d9b2e are retained under C:/Users/jackg/eLedgerCare-Speed/WP-0043/author/author-checks-ef2b4424. Every input, stdout, stderr and argv was retained in owned scratch. The command and hash appendix records the durable portion needed for reproduction.

## Independent evidence and preserved disagreements

The fixture author froze the oracle and scenarios before comparison, on a separate branch and actual Claude Code session. Its published run on 6101a75dc372fc6e2944b004343fa278d5d98907 admitted 47 of 50 frozen source realizations, kept three explicit unsupported cases, agreed on 46/47 verdicts, matched all 47 admitted byte/state transports and matched 9/9 concrete word pairs. Strict comparison was 37/47 with its frozen semantic comparison, 42/47 after a disclosed field-name fix. The exception was an intentionally moved raw read across an inactive guard. Equal bytes gave the oracle P, while the source-backed capture event at the wrong instruction gave the candidate M. At that revision the supplied F5 document was a projection. The corresponding predecessor result cannot establish executed continuation. Original machine records and the fixture author's interpretation remain separate. [Claude / 001](https://github.com/jackgumpe/eledgercare/blob/f52d6ffe227dcb165299578bf2ad01978e63cb48/docs/agent-reports/eld-fixture-claude/WP-0043/001_2026-11-27_research_eld-fixture-claude.md) · [First integration publication](https://github.com/jackgumpe/eledgercare/tree/379e6af37f4816c62a2d98c4f93203c11ce263a1/docs/fixtures/WP-0043)

According to the coordinator's relay, the independent reviewer subsequently drove 49 producer cases and examined one equivalent artifact. There were 46/47 matching verdicts on the original route, with the same witnessed late-cut disagreement. Two newly realized source cases produced M and U. Six independently executed F5 programs and 84/84 compared phase blobs were covered. Three equivalent artifact pairs received P/P. This is attributed reviewer evidence. It cannot enlarge the native denominator and is separate from the ten author cases above. The reviewer's own /003 governs its exact measurements and scope.

## Source amendments and disposition

| Immutable revision | Observation or correction |
|---|---|
| 59c9a5bb23cdf3d0f5312d9fd4f919932886380c | First executable candidate. Per-tensor device-wide sync and possible device packing did not meet the copy claim. Presence-only validation admitted malformed provenance and shape-only state. A process-launch containment race was demonstrated independently. |
| 6101a75dc372fc6e2944b004343fa278d5d98907 | Corrected D2H addressing, output ownership, source events, mandatory typed evidence, attention result and Windows suspended launch. Independent fixture integration exposed algebraic gaps. Earlier F5 fixture invocation passed a supplied document through capture. |
| c107e5cb986060a7bad42ca8a8291dfb38a33758 | Added independently executed synthetic greedy continuations, actual guard entry and return, global append ordering, retained router-terminal binding and unknown cache-slot handling. |
| 20124bc7a68248ab85f0d4e8b9a67d53cb0adb1d | Added arbitrary early-ID/range fragment schedules and genuine whole-row interruption on the producer. |
| 7f573001f8b0a41daabe37c571789f691854c357 | Added independent strict-order, emitted-membership and composed-C2 predicates. The submitted memo's 4b two-key prediction omits the entailed strict-order failure; both predicates now remain visible. |
| ef2b44240730fd12e7cdd268d97811176ab23176 | Closed the measured sub-poll exit gap with persistent transition/progress timing, replay at exit, offline validation and harmless supervisor controls. This is the tested executable revision. |
| 257bbdacf214285de03089b82a16c31bb27ad106 | Documentation only. Restored mathematical typography and clarified log/progress descriptions in the source README. Git name-status against ef2b lists exactly README.md. All 17 Python files are byte-identical. Admission binds the whole source directory; any future current checkout must match the specifically released tree. |

## Change inventory and custody

All 19 additions under docs/research/WP-0043 from the reservation base to the executable candidate are accounted for below. README.md is the sole additional change in the documentation-only successor. The current report is the sole post-deliverable path added in its publication commit. Git name-status and diff checks ran in w043-author. Prior evidence, fixtures, production, Q0 source and other roles' branches were untouched.

| Files under docs/research/WP-0043 | Function |
|---|---|
| README.md, wire.md | Operative definitions, admission boundaries, capture/scoring interchange and injection operations |
| archive.py, bindings.py | Immutable archive calculation and exact live-code/source/bytecode cut resolution |
| stock.py, native.py | Normal CLI, plan, admission, fixed two-process schedule and real public infer calls |
| capture.py, transfer.py, native_observer.py | CPython monitor and capture ledger, pinned D2H copy spans, native B/C/D and full append/terminal observation |
| scorer.py, native_score.py, native_validation.py | Read-only shared algebra and evidence predicates, pair plus chronological/native graph verification |
| analogue.py, analogue_guards.py, continuation.py | Actual CPU guard bodies, mutable score storage, capture-side schedule and independently executed synthetic continuation |
| limits.py, timing.py, check_resources.py, check_deadline.py | Windows process/handle containment, bounded timing journal, actual two-process membership and sub-poll timeout controls |

The installed Q0 model, wheels and environment remained read-only. No model load, CUDA allocation, accelerator observer, device lease or native arm occurred. No timing, resource usage or native pass rate is inferred from CPU examples. Several quantities need a genuine reviewed device pair, including opaque kernel-stream dependencies, actual storage/alias realizations and unsupported active runtime state. The remaining smallest discriminating experiment is one untouched/observed pair on these exact two inputs and call history, conditional on the sole coordinator's independent source/resource disposition. A missing required witness leaves the affected row or document incomplete. Private arms and production have no execution request here. Normal non-force publications used the assigned coordination/push.ps1 script on this role's own branch only. No credentials or external messages were involved.

## Reproducible author evidence

The owning checkout was at ef2b44240730fd12e7cdd268d97811176ab23176. Working directory, interpreter and command operands are in the receipt below. To reproduce in a fresh owned scratch directory on this host, save the author driver there as author_checks.py and run it with the working directory set to that checkout. It creates a new directory for its revision and uses exclusive creation. Each invocation captures actual stdout and stderr. Object IDs, process IDs and monotonic timestamps can vary in a new execution.

~~~~text
python -B C:/Users/jackg/eLedgerCare-Speed/WP-0043/author/author_checks.py
~~~~

<details>
<summary>Exact author commands and captured hashes</summary>

~~~~json
{"revision":"ef2b44240730fd12e7cdd268d97811176ab23176","python":"3.12.10 (tags/v3.12.10:0cc8128, Apr  8 2025, 12:21:36) [MSC v.1943 64 bit (AMD64)]","commands":[{"name":"archive","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\archive.py"],"exit":0,"stdout":{"bytes":1505,"sha256":"70e538ef63a2e68ace7a7f350eebd6a6d732194f93007bb05c0082ac59a2351e"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"plan","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","plan"],"exit":0,"stdout":{"bytes":6575,"sha256":"a1c26da333a4329bda9d02bc256e6ae892dd817e4de9392d4ffa623f3f1b65a0"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"no-run","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","score-native"],"exit":0,"stdout":{"bytes":91458,"sha256":"3d5d4087b8ee5096a6182c5fa69fa4a8126a56502231d0adb5da86331648c265"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"job","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\check_resources.py"],"exit":0,"stdout":{"bytes":107,"sha256":"3cdf1b37a87d37f0e8a2c4fb9d0b8d6eecc61b1b78ba8c8671f7c525e4be4334"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"complete-capture","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","capture","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\case-complete.json"],"exit":0,"stdout":{"bytes":8703,"sha256":"b3360589fab365682cce77b82e7c507dfb6d8ff318eb0caceaba74ec92811a07"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"complete-score","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","score","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\complete-capture.stdout","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\contract-complete.json"],"exit":0,"stdout":{"bytes":352,"sha256":"5d2f6dc8784592dd6ad2148e2c23931ba13ccc74a3acace9faee48344a388be5"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"two-cut-capture","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","capture","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\case-two-cut.json"],"exit":0,"stdout":{"bytes":9461,"sha256":"8da9fac4f37f58829cb61955d3ad9c985485856a2ae6e65cf23dd5c1b98f836a"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"two-cut-score","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","score","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\two-cut-capture.stdout","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\contract-two-cut.json"],"exit":0,"stdout":{"bytes":1129,"sha256":"b2471b5202e7d6a566900f560fdf3367b94e8eb5ab1332e8b329e52887a2e301"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"interrupted-capture","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","capture","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\case-interrupted.json"],"exit":0,"stdout":{"bytes":4708,"sha256":"8d944859754e4bf5dc48b6440a1fa8eabde19a685e589e4eba3c1984bf2429d4"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"interrupted-score","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","score","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\interrupted-capture.stdout","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\contract-interrupted.json"],"exit":0,"stdout":{"bytes":2837,"sha256":"316061241b33e94afa5cdc4460e0a7b24db64ca42dff45b5df463f28fb0b9138"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"f5-stop-capture","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","capture","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\case-f5-stop.json"],"exit":0,"stdout":{"bytes":21785,"sha256":"93f2038d2cbaf6a467a594b0d2c01ab6701d62a9dd4a31a07fe086c8ac3c8f41"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"f5-stop-score","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","score","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\f5-stop-capture.stdout","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\contract-f5-stop.json"],"exit":0,"stdout":{"bytes":759,"sha256":"f7788112ee429980a4f2a58875e5ab4b3adbb28db1f3f95a2db8b6cd51ac5f99"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"f5-later-id-capture","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","capture","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\case-f5-later-id.json"],"exit":0,"stdout":{"bytes":21785,"sha256":"fa0a4bb55cc359e05c79f678afa62cfea22d70b9229c171ea816ad1e9d7fbd74"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"f5-later-id-score","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","score","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\f5-later-id-capture.stdout","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\contract-f5-later-id.json"],"exit":0,"stdout":{"bytes":995,"sha256":"d190fa81a87ced62dd5af2bf19c42304d53d0a3769c541cbd6f7607fc9ca1120"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"f5-length-capture","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","capture","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\case-f5-length.json"],"exit":0,"stdout":{"bytes":21683,"sha256":"b53a8ed4faa68290cf4f05a7136d8eed9e2d12939768d5841f3780afba1539fc"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"f5-length-score","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","score","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\f5-length-capture.stdout","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\contract-f5-length.json"],"exit":0,"stdout":{"bytes":975,"sha256":"d08640493379a7f135fc8c145109c7502fe12edd48ea23b5ed03e216ab534c8f"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"f5-interrupt-capture","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","capture","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\case-f5-interrupt.json"],"exit":0,"stdout":{"bytes":21640,"sha256":"1c113d2449e001d7ea143774a13863d372791595e06c99877993575243727375"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"f5-interrupt-score","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","score","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\f5-interrupt-capture.stdout","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\contract-f5-interrupt.json"],"exit":0,"stdout":{"bytes":970,"sha256":"cfeaab0b3d07d17813fc23cdb063564e4aaada2747dbba9cf3e7683f19501a35"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"deadline","argv":["C:\\Users\\jackg\\eLedgerCare-Q0\\WP-0005\\venv\\Scripts\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\check_deadline.py","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\clock-control"],"exit":0,"stdout":{"bytes":1012,"sha256":"fb1a5dfbe1eab122ea8e43e0a9e0df38fa418c388eabbe4444bce9be09f52c28"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"membership-capture","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","capture","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\case-membership.json"],"exit":0,"stdout":{"bytes":3905,"sha256":"4c89c0849e5d10cc71799f3ee9ec80493e749765c12f6d3e6aa0aa9a4d125e14"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"membership-score","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","score","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\membership-capture.stdout","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\contract-membership.json"],"exit":0,"stdout":{"bytes":484,"sha256":"dda50e14940462a65d49f0421d42727d326f24c53635c3dde70b7b864d79b281"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"injectivity-capture","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","capture","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\case-injectivity.json"],"exit":0,"stdout":{"bytes":3238,"sha256":"4b6e83bf90eecb5ab61322a40265e3e043a55bf36906167a61e60a3b7b595e2a"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"injectivity-score","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","score","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\injectivity-capture.stdout","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\contract-injectivity.json"],"exit":0,"stdout":{"bytes":643,"sha256":"a2f18ce6217c8249aa9dad54017aee8357f46a11c4802a2c22e426242cb935e4"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"composition-capture","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","capture","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\case-composition.json"],"exit":0,"stdout":{"bytes":3902,"sha256":"5eed7cc470e4432c4be8d359be5e233bf43dbb18f71f93421f567744a78a35a0"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"composition-score","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\stock.py","score","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\composition-capture.stdout","C:\\Users\\jackg\\eLedgerCare-Speed\\WP-0043\\author\\author-checks-ef2b4424\\contract-composition.json"],"exit":0,"stdout":{"bytes":922,"sha256":"f732e85a15e3c1ae4186d781de4789b608ebd4ce8836c0c7a7345a8567516ec9"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}},{"name":"callee","argv":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","-c","import sys,dis,json\nsys.path.insert(0,\"docs/research/WP-0043\")\nfrom capture import InstructionMonitor\nfrom analogue import Scores\nfrom analogue_guards import _uocr_page_count_guard as guard\ncode=guard.__code__\nentry=next(i.offset for i in dis.get_instructions(code) if i.starts_line==code.co_firstlineno+2)\nsrc=Scores([0,1,2],[\"00000000\",\"41000000\",\"40800000\"])\ndef run():\n state={\"scanned\":0,\"marker_cum\":0,\"page_len\":0}\n calls=[]\n def observe(tag,frame,returned=None):\n  calls.append([tag,frame.f_code.co_qualname,frame.f_lasti,frame.f_back.f_code.co_name,\n                frame.f_locals[\"logits\"] is src,returned is src,dict(frame.f_locals[\"st\"])])\n with InstructionMonitor({code:{entry:\"actual_entry\"}},observe,{code:\"actual_return\"}):\n  actual=guard(src,[2,0],2,2,1,20000,state)\n print(json.dumps({\"calls\":calls,\"same_object\":actual is src,\"imports\":sorted({\"torch\",\"transformers\",\"pypdfium2\"}&set(sys.modules))}))\nrun()\n"],"exit":0,"stdout":{"bytes":281,"sha256":"6862f6b3a12546934926a82b4fba3eb2a77cf08a2ffafabee4e3a6604f8bc011"},"stderr":{"bytes":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}}]}
~~~~

</details>

<details>
<summary>Author-only driver and generated controls</summary>

~~~~python
"""Author-only post-freeze receipts. Run once in the bound author checkout."""
from pathlib import Path
import json
import subprocess
import sys
import hashlib

repo=Path.cwd()
own=Path(__file__).resolve().parent
revision=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
out=own/("author-checks-"+revision[:8])
out.mkdir(exist_ok=False)
(out/"author_checks.py").write_bytes(Path(__file__).read_bytes())
code=repo/"docs/research/WP-0043"
receipts=[]
def invoke(name,argv):
    proc=subprocess.run([str(x) for x in argv],capture_output=True,cwd=repo,timeout=90)
    entry={"name":name,"argv":[str(x) for x in argv],"exit":proc.returncode}
    for ext,payload in (("stdout",proc.stdout),("stderr",proc.stderr)):
        (out/(name+"."+ext)).write_bytes(payload)
        entry[ext]={"bytes":len(payload),"sha256":hashlib.sha256(payload).hexdigest()}
    receipts.append(entry)
    return proc.stdout
def jfile(name,data):
    dest=out/(name+".json")
    dest.write_text(json.dumps(data,separators=(",",":")),encoding="utf-8")
    return dest
cmd=[sys.executable,"-B",code/"stock.py"]
invoke("archive",[sys.executable,"-B",code/"archive.py"])
plan=json.loads(invoke("plan",cmd+["plan"]))
native=json.loads(invoke("no-run",cmd+["score-native"]))
job=json.loads(invoke("job",[sys.executable,"-B",code/"check_resources.py"]))
contract={"vocab":[0,1,2,7],"page":2,"eos":1,"order":2,"window":1024,"cap":5,"prompt":[2,2],
          "histories":[[2,0,7,0],[2,0,7,0,2]],"raw_words":[["00000000","41000000","40800000","41100000"]]*2,
          "document":{"ids":[7,2],"terminal":"stop","text":"AB","markers":[1],"output_tokens":2}}
program={"prefix":[],"limit":4,"steps":[{"scores":[[7,"3f800000"]]},{"scores":[[2,"3f800000"]]},
       {"scores":[[1,"3f800000"]]}],"pieces":{"7":"A","2":"B"}}
results={}
for name,ops,obs in (("complete",[],program),("two-cut",[{"row":0,"op":"torn","phase":"C0_raw","at":"C2_post_page","early_ids":[7]}],program),
        ("interrupted",[{"row":1,"op":"omit_row","through_end":True}],{**program,"interrupt_before":1})):
    cpath=jfile("contract-"+name,contract)
    case_path=jfile("case-"+name,{"contract":contract,"injections":ops,
          "continuation":{"untouched":program,"observed":obs}})
    ev=invoke(name+"-capture",cmd+["capture",case_path])
    epath=out/(name+"-capture.stdout")
    res=json.loads(invoke(name+"-score",cmd+["score",epath,cpath]))
    results[name]={k:res[k] for k in ("verdict","first_divergent_phase","conflict_keys","missing_keys","public_source")}
price=[6,1449,16,1328,128822]
vocab=sorted({1,8,9,128821,128827,*price})
prefix=[128827,128821]
def finite_program(tail):
    return {"prefix":prefix,"limit":7,"steps":[{"scores":[[t,"3f800000"]]} for t in [*price,tail,1]]}
reference=finite_program(8)
field={"vocab":vocab,"page":128827,"eos":1,"order":35,"window":1024,"cap":20000,"prompt":[128827]*3,
       "histories":[prefix+price[:i] for i in range(5)],
       "raw_words":[["3f800000" if v==t else "00000000" for v in vocab] for t in price],
       "document":{"ids":prefix+price+[8],"terminal":"stop","output_tokens":8,"markers":[0]}}
for name,obs in (("f5-stop",reference),("f5-later-id",finite_program(9)),("f5-length",{**reference,"limit":6}),
                 ("f5-interrupt",{**reference,"interrupt_before":6})):
    cp=jfile("contract-"+name,field)
    ca=jfile("case-"+name,{"contract":field,"continuation":{"untouched":reference,"observed":obs}})
    invoke(name+"-capture",cmd+["capture",ca])
    res=json.loads(invoke(name+"-score",cmd+["score",out/(name+"-capture.stdout"),cp]))
    results[name]={k:res[k] for k in ("verdict","first_divergent_phase","conflict_keys","missing_keys","public_source")}
job_clock=json.loads(invoke("deadline",[str(Path("C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe")),"-B",code/"check_deadline.py",out/"clock-control"]))
simple={"vocab":[0,1,2,7],"page":2,"eos":1,"order":35,"window":1024,"cap":20000,"prompt":[],
        "histories":[[0]],"raw_words":[["3f800000","00000000","40000000","41000000"]],
        "document":{"ids":[7],"terminal":"stop","output_tokens":1}}
pr=[
    ("membership",{**simple,"order":2,"cap":1,"prompt":[2,2],"histories":[[0,2,0]]},[],{"empty_support","selection_outside_support"}),
    ("injectivity",simple,[{"row":0,"op":"duplicate","from":"C0_raw","to":"C1_post_rep"}],{"phase_cut_binding_mismatch","non_monotonic_capture_seq","duplicate_copy_event_id"}),
    ("composition",simple,[{"row":0,"op":"write","phase":"C1_post_rep","id":1,"value":"80000000"}],{"signed_zero_corrupted","post_page_composed_word_mismatch"})]
predicate_pass=[]
for name,contract,ops,expected in pr:
    cp=jfile("contract-"+name,contract)
    ca=jfile("case-"+name,{"contract":contract,"injections":ops,"document":contract["document"]})
    invoke(name+"-capture",cmd+["capture",ca])
    res=json.loads(invoke(name+"-score",cmd+["score",out/(name+"-capture.stdout"),cp]))
    results[name]={k:res[k] for k in ("verdict","first_divergent_phase","conflicts","conflict_keys","missing_keys")}
    good=expected.issubset(res["conflict_keys"]) and res["verdict"]=="M"
    if name=="composition":
        matches=[x for x in res["conflicts"] if x["key"]=="post_page_composed_word_mismatch" and x["id"]==1]
        good &= {x["comparison"] for x in matches}=={"captured_C0","controlled_input"} and all(
            (x["lane"],x["dense_offset"],x["compact_offset"],x["expected_le"],x["observed_le"])==(3,7,7,"00000000","00000080") for x in matches)
    predicate_pass.append(good)


guard_demo="""import sys,dis,json
sys.path.insert(0,"docs/research/WP-0043")
from capture import InstructionMonitor
from analogue import Scores
from analogue_guards import _uocr_page_count_guard as guard
code=guard.__code__
entry=next(i.offset for i in dis.get_instructions(code) if i.starts_line==code.co_firstlineno+2)
src=Scores([0,1,2],["00000000","41000000","40800000"])
def run():
 state={"scanned":0,"marker_cum":0,"page_len":0}
 calls=[]
 def observe(tag,frame,returned=None):
  calls.append([tag,frame.f_code.co_qualname,frame.f_lasti,frame.f_back.f_code.co_name,
                frame.f_locals["logits"] is src,returned is src,dict(frame.f_locals["st"])])
 with InstructionMonitor({code:{entry:"actual_entry"}},observe,{code:"actual_return"}):
  actual=guard(src,[2,0],2,2,1,20000,state)
 print(json.dumps({"calls":calls,"same_object":actual is src,"imports":sorted({"torch","transformers","pypdfium2"}&set(sys.modules))}))
run()
"""
guard=json.loads(invoke("callee",[sys.executable,"-B","-c",guard_demo]))
report={"revision":revision,"exe":sys.executable,"python":sys.version,"commands":receipts,
        "summary":{"cases":results,"deadline":job_clock,"predicate_pass":predicate_pass,"job":job,"guard":guard,"native":{k:native[k] for k in ("verdict","complete_rows","scheduled_rows","scheduled_pairs","public_pairs_matched")},
                   "sites":sum(len(v) for v in plan["cuts"].values()),"plan_sha256":hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(",",":")).encode()).hexdigest()}}
jfile("receipt",report)
print(json.dumps(report["summary"]))
if not all(predicate_pass) or any(r["exit"] for r in receipts) or [results[k]["verdict"] for k in ("complete","two-cut","interrupted")]!=["P","M","U"] or [results[k]["verdict"] for k in ("f5-stop","f5-later-id","f5-length","f5-interrupt")]!=["P","M","M","U"]:
    raise SystemExit(1)
~~~~

</details>
