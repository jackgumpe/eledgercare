# WP-0042 / 001 — One-field stock observation and private replay design

- Report path: docs/agent-reports/eld-owner-probe/WP-0042/001_2026-11-26_research_eld-owner-probe.md
- Sequence reservation: [WP-0042 /001 at assignment commit](https://github.com/jackgumpe/eledgercare/blob/a947ddbab8f71df64b5c6640ef94923c32e29cd5/INDEX.md#wp-0042-f07-stock-observer-and-private-replay-qualification-design)
- Category: research
- Author / agent ID: eld-owner-probe, fresh native Codex collaboration session /root/observer_design, CODEX_THREAD_ID 01a216bd-6088-7df2-a5e4-b605cd9cb673
- Actual model / effort: coordinator reports explicit gpt-6.2-astra / xhigh launch configuration and initialized native session. The worker receives a GPT-6 Codex identity and its thread ID; the backend checkpoint and actual deliberation level are not independently exposed to this worker.
- Execution environment: local Windows PowerShell, CPython 3.12.10 x64, CPU. PyPDF 6.16.2 was used only to read Edition 3, independently of the controls' isolated standard-library interpreter.
- Published by: eld-owner-probe on owned branch
- Timestamp: 2026-11-26T07:41:12Z
- Repository / branch / worktree: jackgumpe/eledgercare, research/wp-0042-layer11, C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w042-author
- Base revision: a947ddbab8f71df64b5c6640ef94923c32e29cd5
- Initial design: a1b3978309dde6cc4e4b3477f07a1d528260029a
- Final deliverable revision after non-author clarification: cd563dd06932a2cdecad4932b39d030efbe06699
- Evidence revision: e42ee5ac623b2bc9aedcbd4951ae19221c4ec541
- Previous report: none in this packet. The earlier stable-role analysis is [WP-0041 /002](https://github.com/jackgumpe/eledgercare/blob/f5e68668a5999a12ba399eb0f5103ffa835e4b30/docs/agent-reports/eld-owner-probe/WP-0041/002_2026-11-26_research_eld-owner-probe.md), by the historical source author.
- Related evidence: [WP-0041 independent review /003](https://github.com/jackgumpe/eledgercare/blob/f5e68668a5999a12ba399eb0f5103ffa835e4b30/docs/agent-reports/eld-rd-reviewer/WP-0041/003_2026-11-26_review_eld-rd-reviewer.md) and [coordinator disposition /004](https://github.com/jackgumpe/eledgercare/blob/f5e68668a5999a12ba399eb0f5103ffa835e4b30/docs/agent-reports/eld-coordinator/WP-0041/004_2026-11-26_verification_eld-coordinator.md)
- Status: ready-for-review
- Next owner: eld-rd-reviewer, independent WP-0042 /002; eld-coordinator for disposition

## Summary

All six supplied synthetic controls passed. The source-bound design explains how to ask whether private equal-input calls to block 11 reproduce the stock decision and advance just once. It gives executable cut locations, state/alias restoration rules, scoring denominators, missingness, and a comparator that exposes ordered tokens without a new observation hook. The five archived IDs include the closing delimiter. They still supply zero complete native block-entry snapshots. Field verdict **UNMEASURED**. The next scientific observation is an untouched-versus-instrumented stock comparison on the same permitted document under matched warm-up and source. No new native, private or L2 call was made.

## Objective and acceptance criteria

Prepare an implementable qualification design for the five decision positions t=1445..1449 on F07.warm1, using Edition 3 pp. 1–11 and explicitly attributing pp. 12–21 as Gemini's original Draft 2 review. The design must account for each A1–A5 change and its limits, the actual sparse model and custom generation path, independent and linked same-input controls, single-commit and protected-source continuation, and a finite scorer with decisive failures and missing evidence distinguished. Author verification can establish source identity and behavior on the six constructed examples. Independent review and actual execution admission are separate.

## Change inventory

| Revision | Exact path | Result |
|---|---|---|
| Deliverable | docs/research/WP-0042/design.md | Question, field binding, A1–A5 under corrected assumptions, proofs, boundary cases, controls, falsifiers and scope. |
| Deliverable | docs/research/WP-0042/source-cuts.md | Source locations, activation/fallback predicates, capture order, model/generator state, untouched comparison and source resumption to EOS. |
| Deliverable | docs/research/WP-0042/scoring.md | Independent guard-mask reconstruction, finite atom expansion, 35 scheduled native/private arm rows, 40 paired row comparisons, continuation and resource admission. |
| Evidence | docs/research/WP-0042/evidence/control-receipt.json | Executable, native transport, digest, length, exit and declared LF comparison. |
| Evidence | docs/research/WP-0042/evidence/source-receipt.json | Independently read 21 pages and 14 payloads, verified seven historical Git files and six source file hashes. |
| Evidence | docs/research/WP-0042/evidence/stdout.bin | All 550 native Windows child stdout bytes. |
| Evidence | docs/research/WP-0042/evidence/stderr.bin | Native zero-length stderr. |
| Evidence | docs/research/WP-0042/evidence/.gitattributes | Marks the two binary transport artifacts binary within this evidence directory. |
| Report | docs/agent-reports/eld-owner-probe/WP-0042/001_2026-11-26_research_eld-owner-probe.md | Author report, committed after design and evidence. |

External effects were limited to the assigned scratch directory C:/Users/jackg/eLedgerCare-Speed/WP-0042/author (extracted 14 supplied payloads, readable page text, controls and captured results), this owned worktree's normal Git objects, and ordinary push to the owned remote branch. No private model trace, private fixture or unassigned checkout was opened. Only published model source/config was read from the approved Q0 installation. The supplied PDF and historical sources were read-only. The five evidence files precede the amended final design in Git history and retain the initial design pin they actually checked.

## Decisions and rationale

The scientific comparator can call the stock native infer(return_dict=True) with the exact arguments the historical infer_multi wrapper forwards. The outer wrapper exposes only text and token count, while the inner return exposes ordered prompt/output IDs, terminal reason and page counts. Neither provides raw scores. The design mandates a measured comparison with the historical binding and matched call history, then a separate instrumented run. Each linked P2 selection retains a's entire post-state after checking both independently reconstructed instances. These two design choices are explicit for independent review. Head output, full processed scores, masks and alias evidence are separate obligations. In particular, _uocr_pg updates at model entry before block 11; invoking that updater again while restoring the block would move the declared cut. EOS is tested before append and is absent from the 2558 returned IDs. The all-atom minimum retains missing fields even when a different known defect already makes the field verdict MISMATCH.

The independent reviewer requested three clarifications on the first candidate before /001 publication. The amended design binds the emitted token only to final z, gives a two-score counterexample for the diagnostic raw winner, scores P2b's complete candidate D plus its actual teardown, and enumerates native finally effects. The post-finally reference is the matched stock observer for instrumented fields. The original source leaves router._infer_params in place. Neither the CPU script nor its frozen expected output changed.

## Verification

| Check / operation | Revision and actual result |
|---|---|
| Entry git status --short --branch and git rev-parse HEAD | Owned research/wp-0042-layer11, clean at a947ddbab8f71df64b5c6640ef94923c32e29cd5. |
| Exact execution input bytes | Extracted git show a947ddbab8f71df64b5c6640ef94923c32e29cd5:docs/coordination/WP-0042/six_controls.py and six-results.txt via subprocess.check_output with binary pipes. Both SHA-256 values matched the PDF receipt before execution. Read the entire script. It imports only collections, copy, itertools, math and struct and uses constructed in-process data. |
| Exact child invocation | C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe -I -S -B C:\Users\jackg\eLedgerCare-Speed\WP-0042\author\six_controls.py, cwd the assigned author scratch, timeout 30 s. Parent subprocess.run used stdout=PIPE and stderr=PIPE without text conversion. At 07:25:13 UTC all six finished, exit 0, empty stderr, and the exclusive CPU lane was returned to the coordinator immediately. This ran against the already frozen supplied script; no new tests or source edits were executed before a candidate freeze. |
| Transport comparison | Raw stdout 550 bytes, SHA-256 a09273a5218cbe0d6e80aa267c235bf90309efd434b20c933f81d2c1239a9481. The provided expected transcript is 544 LF bytes and differs from the native bytes. Replacing the six CRLF pairs with LF, preserving all other bytes, produced byte-for-byte equality, SHA-256 2eb71e8c4aa62000388f3df62890e63c4038dbb69e5d157fb329ad8695375d6b. The script is 5714 bytes, SHA-256 f5aaa707d7854dd0db081c23314558c170324530f1e5351266d26112714af131. The interpreter binary hash is 4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a. |
| PDF and source audit | Read the PDF with pypdf.PdfReader, extracted all 21 pages and 14 embedded files, compared each byte length/hash against inputs.json and each of seven historical payloads against git show at f5e68668a5999a12ba399eb0f5103ffa835e4b30. SHA-256 and counts matched. Read the six files in the design's pin table as bytes, compared their hashes to WP-0041 source.json, traced the actual functions, and read Q0 harness session/telemetry/backend/schedule from 9e73ef86600b5e16f74b056676a6d3a4f1474058. No Q0 model/library was imported. |
| Frozen design and evidence | git diff --cached --check passed before design commit. After freeze, validated UTF-8/LF and local links on the three exact design blobs. Initial evidence diff-check flagged six retained CRLF lines as trailing whitespace when the raw file was only marked -text. Marking the two transport files binary fixed their Git diff treatment. Rechecked the exact committed stdout with subprocess.check_output(['git','show','HEAD:docs/research/WP-0042/evidence/stdout.bin']); 550 bytes, six CRLF, correct native hash. |
| Amended candidate | Read the exact three final Git blobs at cd563dd06932a2cdecad4932b39d030efbe06699 as UTF-8, checked local links and the three amended clauses. git diff --check a947ddbab8f71df64b5c6640ef94923c32e29cd5 cd563dd06932a2cdecad4932b39d030efbe06699 passed. This amendment is a design/scoring clarification. The control receipt identifies the immutable external test input. |
| Publication | The coordinator-provided push.ps1 with ExpectedHead e42ee5ac623b2bc9aedcbd4951ae19221c4ec541 pushed normally and confirmed the owned remote branch at the evidence commit. The same helper confirmed final design cd563dd06932a2cdecad4932b39d030efbe06699 on the owned remote branch. The report's publication SHA is supplied separately following its push. |

Source-search attempts during inspection encountered shell argument/glob handling and a path excluded by sparse checkout. Reissued them against explicit names, directory with a glob filter, or exact git show revisions. No failed query was used as evidence that a source file was absent.

## Review map

Review the [research diff](https://github.com/jackgumpe/eledgercare/compare/a947ddbab8f71df64b5c6640ef94923c32e29cd5...cd563dd06932a2cdecad4932b39d030efbe06699), [source cut table](https://github.com/jackgumpe/eledgercare/blob/cd563dd06932a2cdecad4932b39d030efbe06699/docs/research/WP-0042/source-cuts.md), [scorer](https://github.com/jackgumpe/eledgercare/blob/cd563dd06932a2cdecad4932b39d030efbe06699/docs/research/WP-0042/scoring.md) and [evidence bytes](https://github.com/jackgumpe/eledgercare/tree/e42ee5ac623b2bc9aedcbd4951ae19221c4ec541/docs/research/WP-0042/evidence). Reconstruct the actual guard sets, source/generator cut order, active aliases, native stop and denominators when assessing implementation feasibility. Inspect the supplied authoring-policy insertion separately in its reserved coordinator directory; I did not modify AGENTS.md or any ledger.

## Risks, disagreements and unfinished work

Design alone does not establish that the selected Python/CUDA observer will capture every required field, that live object and allocation aliasing can be safely reconstructed, that kernel execution is deterministic, or that a sole device has enough capacity. The six CPU controls pass in their constructed domains. No live arm, private bytes, physical family, latency comparison or model treatment was measured. The actual implementation candidate, disassembly/event proof, environment, ceilings, destinations and device release remain to be bound.

## Handoff

eld-rd-reviewer independently checks cd563dd06932a2cdecad4932b39d030efbe06699 and e42ee5ac623b2bc9aedcbd4951ae19221c4ec541 under WP-0042 /002. If source and controls survive review, the smallest next step is a separately frozen stock observer/scorer and untouched comparator on the bound document. A later private parity proposal depends on that comparison and a second release.
