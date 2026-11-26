# WP-0042 /003 — F07 stock observer and private replay qualification

| Publication record | Binding |
| --- | --- |
| Owner, author and publisher | eld-coordinator, local thread 01a20a53-eec1-72c1-864c-9f8be8f4aff5 |
| Role and category | Coordinator verification and disposition, packet-wide slot 003 |
| Launch | Local Codex, gpt-6.2-astra and xhigh requested for the bound coordinator and for both newly initialized independent worker sessions. See dispatch.json for the exposed role identities. |
| UTC | 2026-11-26T07:48:04.007657+00:00 |
| Repository and branch | jackgumpe/eledgercare, coordination/bootstrap |
| Base and reservation | f5e68668a5999a12ba399eb0f5103ffa835e4b30 and a947ddbab8f71df64b5c6640ef94923c32e29cd5 |
| Integrated deliverable | 14dc99fb67b3a722dd64c020e4f28ddb7968a68c |
| Author publication | 997ecf5b3041eeb3f90b1902332d7ccbb08b4472 |
| Independent review publication | 29dde86cbc221dd210b690d3489ad8bbf25d8d15 |
| Accepted design | cd563dd06932a2cdecad4932b39d030efbe06699 |
| Previous coordinator record | [WP-0041 /004](../WP-0041/004_2026-11-26_verification_eld-coordinator.md) |
| Status | Accepted for design and constructed CPU controls. Native field verdict UNMEASURED. |
| Next owner | eld-owner-probe for the stock-only implementation proposal, followed by eld-rd-reviewer and the sole coordinator's separate admission decision |

## Disposition

Can a faithful private replay reach the same Unit Price decision as the stock reader while leaving its document intact? The submitted design specifies how to decide that question on F07.warm1. The six small CPU controls reproduced under independent review. Native replay remains **unmeasured**. The exact Edition 3 working rule is adopted for this product.

### What reproduced

| Constructed control | Decisive evidence | Limit on interpretation |
| --- | --- | --- |
| 1. Snapshot sufficiency | A 34-ID suffix ending an earlier 35-gram separates allowed continuations. Removing a redundant seen count preserves the model's outcome fibers. | Repeating the four-piece price is insufficient. The fixture uses 128 history tokens. F07 used 1,024. The toy does not establish a reachable collision with equal native hidden states. |
| 2. Storage and binding isolation | Faithful, split and source-shared copies give private/source reads (99,20), (20,20) and (99,99). A container rebind can change the source while leaving old tensor bytes intact. | A native allocation's offset depends on its actual strides, element width and storage offset. Endpoint digests can miss a transient write. |
| 3. Single-commit rollover | Independent calls from length 31 end at (32,31). Reuse gives (33,32) and a new block record. Trimming the length leaves the wrong counter. | All five F07 positions fall in block 45. The fixture is the only rollover evidence here. |
| 4. Two observation cuts | With native post/next entry (31,31), a local fault gives (32,32), a bridge fault (31,32) and a compensated fault (32,31). | Paired cuts localize the first observed interval. Faults cancelled within one interval and incomplete probes remain possible. |
| 5. Raw bytes and valid scores | Losing logits 3 and 2 are distinguishable before both are masked. Signed zero has unequal bytes. Matching NaNs fail validity. +0 to negative infinity first differs at byte 2 in a little-endian FP32 word. | Byte equality, validity and an independently established allowed set are separate obligations. A finite wrong allowed score can still satisfy the validity predicate. |
| 6. Field verdict | Among 243 five-row assignments the independent oracle counted 211 mismatch, 31 unmeasured and one pass. It retains missing evidence when a measured conflict takes precedence. | Five row statuses alone omit the second P2 call, linked trajectories, untouched stock, protected source and terminal continuation. |

Author and reviewer ran the authenticated 5,714-byte script under Python 3.12.10. Each native Windows pipe emitted 550 bytes with six CRLF endings (SHA-256 `a09273a5218cbe0d6e80aa267c235bf90309efd434b20c933f81d2c1239a9481`). Converting just CRLF to LF gave 544 bytes matching the attached stdout. The reviewer also selected LF in the interpreter before executing the unmodified source. Those raw stdout bytes directly matched `2eb71e8c4aa62000388f3df62890e63c4038dbb69e5d157fb329ad8695375d6b`. Both default runs exited zero with empty stderr.

### Device and scientific disposition

The recorded baseline is one three-page synthetic development document, with one already-correct selected field. At absolute input positions 1445–1449, the native predictions were `6, 1449, 16, 1328, 128822`, including the complete closing delimiter. The original stock decoder stopped at EOS with 2,558 emitted IDs and 7,617 decoded bytes. Its guard checked EOS before appending. The adjacent Net Line contains the same price. Its matching text cannot identify the Unit Price cell.

Native entries with the full comparison record remain 0/5. Anchored P1, P2a and P2b each have 0/5 measured rows. Linked P1/P2, untouched-versus-observed comparisons and paused-source continuations have zero completed trajectories here. No L2 runs or physical-family pairs were evaluated. Recovery, regression, peak capture cost and time savings have no estimate on this evidence.

I withhold stock observation and private device replay. The next owner is **eld-owner-probe** for a versioned stock-observer implementation proposal limited to this field. **eld-rd-reviewer** must inspect its exact executable, source cuts, writable graph, output schema and failure behavior. A future stock decision must bind the unchanged baseline and instrumented arguments and hashes, private storage and size ceiling, validated environment, a current exclusive device lease, stop conditions and output custody. A separate private replay decision depends on an accepted stock comparator and captured state. WP-0037 remains parked.

## Stock comparator and private replay design

The three design files specify where to pause the native call, what bytes and object relationships to keep, how to continue each private branch, and how to score incomplete evidence. At entry, block 10 has returned and block 11 has yet to consume the token. At input position 1445, the source-derived signature is eleven cache lengths of 1446 and one of 1445. Source inspection predicts this signature. A future capture must measure it. The generator must copy all 129,280 promoted FP32 logits before the no-repeat guard can write, preserve the intermediate vector, and observe the page guard and greedy selection in their actual order. Raw bits, the allowed set, validity, maximal ties and selected ID each have an obligation.

The five positions give 35 native/private arm rows and 40 pairwise comparisons in the proposed protocol. Of the 30 private calls, 15 reload native entries and 15 run on linked P1/P2 trajectories. The two P2 calls each start from the same logical input in isolated storage; only one whole survivor advances. Eight linked bridges expose changes between steps. Five fresh protected-source rows and continuation to actual document stop are additional obligations. A matching public result cannot reveal a split internal alias or an earlier write that was later undone.

The F07 comparator needs the effective stock inner call that returns the IDs, the archived input order and matching warm-up history. The outer multi-page wrapper discards the ID list. A future binding must account for F01 warm-up and repeat before F07.warm1, including its resource cost. The sole-device decision belongs to the coordinator. This packet accepted no operator command or lease.

## Independent reconciliation

Reviewer and author examined the same initially frozen design at a1b3978309dde6cc4e4b3477f07a1d528260029a. The independent reviewer identified a valid raw winner that a later guard suppresses, stock cleanup that retains some router state, and an ambiguity about the discarded P2b successor. In the accepted revision, native y must equal the first maximum of final processed z on its independently derived support. With r=(9,4), allowed IDs={1} and z=(−∞,4), the correct ID is 1. The two earlier maxima remain diagnostic. The terminal comparison now follows the stock cleanup assignments, including retained router parameters. P2b produces a candidate post-state and a teardown record. The selected copy alone supplies the committed successor. The non-author checked all three changes against the stock source and the final design. Scientific and custody obligations remain open until measured.

## Amendment and provenance

Edition 3 pages 1–11 govern. Its ten appended pages reproduce Gemini's independent assessment of Draft 2. The reviewer verified all ten original content streams and extracted page texts, all 14 attachment identities and all seven historical Git byte comparisons. The local author and independent reviewer retain authorship of their own work. The agreement change inserts the supplied 1,998 policy bytes plus a separator before the existing mathematics rule. It preserves that rule and all other prior bytes. Independent reconstruction, scratch git apply and public AGENTS.md all yielded blob 548da8813482a2598d437a63501f3c82820c7daa, SHA-256 20b551fa208864e06f5f6c2fe8325290d720c01d8413c68f0aee1a38fee1df0c. A default Windows patch application initially introduced CRLF in scratch. Repeating with command-scoped core.autocrlf=false gave the exact Git representation. No profile or external workspace change was required.

## Verification and inventory

The coordinator verified the live owner/base and absence of a duplicate, extracted the PDF payloads as bytes with pypdf, compared seven inputs with git show, inspected the control source before dispatch, and cross-checked original F07.warm1 observation, ID-array and text blobs. The published source and evidence revisions, executable commands, actual transport, corrections and all six constructed counterexamples are in the author and non-author publications. The coordinator compared the binary author stdout and empty stderr to both the attached output and the independent receipt, checked the review's exhaustive counts, and checked the exact accepted design blobs through both branch integrations. Only normal fast-forward pushes were used. The public verifier reads the immutable URLs for every changed path, compares downloaded bytes with Git and checks report introduction and live heads. Verification of this report and subsequent receipt belongs in the receipt commit and closing handoff.

The scoped integrity check compared 118 existing worktrees and 73 pre-existing modified-file identities with their references. The primary dirty package digest remains 6af72a0583bf4a640633ac17b0cc3e9adc83a5f4df12d09b01ae70dcec0546e0 and stash tip remains bcc4b085be6b5f2c64bca52443f410398db15aa1. Two owned worker worktrees were added. No new model load, GPU, L2, OCR pilot, protected evaluation or production run occurred. A whole-packet git diff --check reports the three unified-diff context blank lines in the supplied patch at lines 4, 6 and 20. Their leading space is part of the authenticated patch. Its exact bytes are retained.

Changes from the research base through the integrated deliverable are listed below. Source, raw evidence and role-specific reports retain their original authors. This report is committed afterward. Coordinator receipt and final ledger publication bindings follow public byte checks.

- `AGENTS.md`
- `CURRENT.md`
- `INDEX.md`
- `docs/agent-reports/eld-owner-probe/WP-0042/001_2026-11-26_research_eld-owner-probe.md`
- `docs/agent-reports/eld-rd-reviewer/WP-0042/002_2026-11-26_review_eld-rd-reviewer.md`
- `docs/coordination/WP-0042/.gitattributes`
- `docs/coordination/WP-0042/AGENTS-research-handoffs.patch`
- `docs/coordination/WP-0042/Research-handoff-authoring-policy.md`
- `docs/coordination/WP-0042/agreement-candidate.json`
- `docs/coordination/WP-0042/assignment.md`
- `docs/coordination/WP-0042/dispatch.json`
- `docs/coordination/WP-0042/disposition.json`
- `docs/coordination/WP-0042/field-baseline.json`
- `docs/coordination/WP-0042/inputs.json`
- `docs/coordination/WP-0042/integrity.json`
- `docs/coordination/WP-0042/six-results.txt`
- `docs/coordination/WP-0042/six_controls.py`
- `docs/coordination/WP-0042/verify_publication.py`
- `docs/research/WP-0042/design.md`
- `docs/research/WP-0042/evidence/.gitattributes`
- `docs/research/WP-0042/evidence/control-receipt.json`
- `docs/research/WP-0042/evidence/source-receipt.json`
- `docs/research/WP-0042/evidence/stderr.bin`
- `docs/research/WP-0042/evidence/stdout.bin`
- `docs/research/WP-0042/scoring.md`
- `docs/research/WP-0042/source-cuts.md`
- `docs/reviews/WP-0042/assessment.md`
- `docs/reviews/WP-0042/controls.json`
- `docs/reviews/WP-0042/controls_review.py`
- `docs/reviews/WP-0042/design-review.md`
- `docs/reviews/WP-0042/inputs.json`
- `docs/reviews/WP-0042/inputs_review.py`
- `docs/reviews/WP-0042/protocol.md`
