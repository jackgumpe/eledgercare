# WP-0041 /004 · One field is bound; native Layer 11 parity remains unmeasured

I accept the source, field binding and mathematical feasibility results. I withhold a fresh stock observation and native/P1/P2 replay. The first gate passed on a permitted synthetic development amount. The blocking gate is the absence of a native per-position state and score trace, plus a qualified command that could replay it privately while preserving the document branch. The archive supplied five native target IDs. It supplied zero of the five complete parity observations. There is no measured mismatch or equivalence. [Bound field, gate and next owner](../../../coordination/WP-0041/replay-gate.json)

- Author/publisher eld-coordinator, Windows local Codex thread 01a20a53-eec1-72c1-864c-9f8be8f4aff5, gpt-6.2-astra/xhigh. Verification report `docs/agent-reports/eld-coordinator/WP-0041/004_2026-11-26_verification_eld-coordinator.md`, prepared 2026-11-26T05:43:22.1543226Z. Public jackgumpe/eledgercare, coordination/bootstrap.
- I authenticated all nine pages of the 215820-byte supplied brief, SHA-256 `3f4451dd3a1bd2dc37d50c5ddb720dfd37005f62c1da68a6b2958aa86db14264`. Pages 1–6 govern the earlier handoff on 7–9. The branch and ledger matched the WP-0040 closeout `a0bf6122d082675d483ffd9aeb7f4dbedbfb174c`. WP-0041 reservation `5f73e671ccd2fc12eb0f2d85b2effae713dc867c`. Reviewed integrated deliverable `23aec6eeb14b4ecc32cfa68b4579044d72a04f51`. [Release and frozen eligibility](../../../coordination/WP-0041/assignment.md) · [Independent session identities](../../../coordination/WP-0041/dispatch.json)
- The custodian traced one development field, the research author inspected the sources and checked the claims, and the non-author reviewer independently reconstructed the arguments and verified the field, sources and governance text. The coordinator owns the scope, release decision and ledger. [Custody /001](https://github.com/jackgumpe/eledgercare/blob/76c2bc6963ba52dedcfc357b0489cd0eec93939c/docs/agent-reports/eld-twin-custodian/WP-0041/001_2026-11-26_research_eld-twin-custodian.md) · [Source and mathematics /002](https://github.com/jackgumpe/eledgercare/blob/02852b225250b3efd852f87826fa0a3cf58ced6f/docs/agent-reports/eld-owner-probe/WP-0041/002_2026-11-26_research_eld-owner-probe.md) · [Independent review /003](https://github.com/jackgumpe/eledgercare/blob/9c7e1a30508f490f29a70110debaa66850c04db3/docs/agent-reports/eld-rd-reviewer/WP-0041/003_2026-11-26_review_eld-rd-reviewer.md)

## First gate and historical native evidence

The frozen selection rule admitted a *structural development probe*. The F07 capture does not establish that a ledger-arithmetic trigger selected this cell. WP-0040's physical intake admitted zero families. Here the already permitted WP-0005 F07.warm1 stock generation, run `20261115T202627Z-eb5bf7da`, supplies original contextual IDs and a source page. The target is the first page, second table, second row including the header, fifth column: line L01, Unit Price, `$28.50` (2,850 cents). The native record contains 2,558 generated IDs and 7,617 decoded UTF-8 bytes. The independent spatial check locates the printed amount inside the source PDF cell [344, 504.5, 398, 529.5] in PDF points measured from bottom left; the text origin is (371.44, 519). The adjacent Net Line repeats the amount. The column edges, source text positioning and matching raster identify the intended cell independently of the native table-level box.

| Original piece | Zero-based native output index | ID | Half-open byte interval |
| --- | ---: | ---: | --- |
| `<td>` | 618 | 128821 | [1823,1827) |
| `$` | 619 | 6 | [1827,1828) |
| `28` | 620 | 1449 | [1828,1830) |
| `.` | 621 | 16 | [1830,1831) |
| `50` | 622 | 1328 | [1831,1833) |
| `</td>` | 623 | 128822 | [1833,1838) |

There is a clean boundary on both sides. Decoding the existing generated sequence supplies this evidence. Re-encoding the extracted string alone would lose the generation provenance. The field consumes native generated indices 618–622 to predict 619–623, corresponding to absolute input positions 1445–1449 after the 827-token prefix. One extra block evaluation per target decision would cost **five** extra block calls along this archived tokenization; a changed free-running field may end at a different length. Prefix reconstruction, state capture/transfer, duplicate control and original-branch verification are distinct costs.

## Source and resource decision

The Baidu model revision is `0480966938291445591f69f08a13b041c073a96a`. Its child `cb16b920ec2249c4b280f3aa67942e00b5099122` changed the README alone. The locally inspected configuration constructs twelve ordered decoder blocks of width 1280. The intervention point is the causal language model's `model.layers[11]`, before final normalization and the unchanged head. Config, decoder and tokenizer SHA-256 include `607d130a70d5af5a35329aa237acd68651f45504c62cc7ced981066f4e781126` (config), `24a15dfd47578ab24a7a4d4e977dc5d7a23dfef0a2a4c4bf73fcf3e2ce7acaf2` (decoder routing), `f6df813cef23cc28b1daca40fd8cb20740d05a238e7b9dfa2334531fdcf39f1f` (OCR generation) and `c55c165e32c5a67830362a53e1f548c8930dcc8469efa30ff3252a982799c589` (tokenizer.json). The original run records its dynamic module cache and runtime. The historical pinned environment includes CPython 3.12.10, torch 2.13.0+cu130 and Transformers 4.52.1. These records establish provenance; current live device behavior has no new measurement.

F07 logged 12 dense prefill fallbacks, 30,696 DASH single-token decode calls and 30,696 FP32 decode-attend calls across the twelve blocks, with zero non-DASH attention calls. Its cache grew from 827 to 3,385 positions. These counts describe the run. They do not identify the actual remote-block indices, top-k ties or full native tensor bytes at the five target positions. The selected historical generation used temperature zero, a 35-token no-repeat constraint with window 1024, the page-count guard and `dash_topm=16`. Native code edits the FP32 score vector in place before greedy argmax. A future trace must preserve the raw bytes before mutation and capture the final processed vector, allowed IDs, tie order, chosen ID and active routing at every step.

The WP-0017 teacher-forced probe includes a useful K/V clone with router and rotary state. Its branch runs the whole model and can give the last branch the original cache. A last-hidden-state readout there cannot substitute for the selected layer-10 exit tensor on F07. Required evidence includes pre-token h0, layer K/V, DASH index keys, page/rotary counters, model-level page state, module-local routing mask, token/position inputs and generation history/guards. Verify all influencing writable storage is disjoint, byte-check outputs and committed state for P1 and **both** P2 calls, commit only one update, and show that the original document branch and continuation stay intact. Use representation/dtype, shape and exact bytes, including signed zero, rather than treating max absolute error zero as byte identity.

I did not release a new stock observation because there is no reviewed field-bound observer/private-replay command for this evidence contract. A fresh stock trace would provide a reference only. Reusing an earlier hardware lease or replaying the token list would leave the state and ownership questions unanswered. The next owner is eld-owner-probe for a proposed observer and private-branch harness on this exact field. eld-rd-reviewer verifies the command, nonintrusiveness and isolation before the coordinator decides whether to bind an operator, device, single lease, time/memory limits and storage. No Layer 11 treatment, crop, physical evaluation, training, posting or WP-0037 work was released.

## Three conditional claims and their limits

1. **One committed step.** With a deterministic stock path, identical inputs and private pre-token state S, P1 computes F(h0,S) once. P2 computes that same call twice on independent copies, discards the second result and commits once. A stock append advances the selected layer from t to t+1. Matching raw/processed scores and deterministic selection give the same next token and complete state, so induction applies through the entire delimiter. At 31 cached positions two private calls each finish at 32; reusing one mutable state can reach 33 and advance a rotary/page counter twice. A treatment F(h1,S) can keep length while changing state bytes. Even an equal emitted token does not restore state equality. Identical complete reader inputs and states for two different prints remain indistinguishable under deterministic repeated calls.
2. **When a rival overtakes.** With finite processed scores on a common allowed set and a unique baseline winner a, the new lead over j is m_j − (δ_j − δ_a). A strict overtake requires δ_j − δ_a > m_j. Equality gives a pairwise tie subject to the actual tie order and other rivals. If every movement is bounded by ε, a minimum lead strictly above 2ε protects the winner. In the worked example the 0.40 lead is erased by a relative gain of 0.45, leaving “7” ahead by 0.05. Either recovery or regression is possible depending on print truth. For a fixed linear head after normalization the real-arithmetic raw relative change is (w_j−w_a)·(u₂−u₁), bounded by the product of norms. To certify machine scores one must also account for rounding and any changed processor masks. The local identity cannot certify later branch scores or whole-field accuracy after cache/token divergence.
3. **Compute break-even.** On matched incoming pages, disjoint cost terms give expected loop minus crop time a+p(b−c), where a is overhead per incoming page, p is the trigger fraction and b,c are incremental costs per triggered field. For a≥0 and c>b, strict saving requires p>a/(c−b). Equality is a time tie; if c≤b strict savings are impossible under these assumptions. At 2, 3 and 11 ms the threshold is 25%. At 10% the loop costs 1.2 ms more per page; at 50% it saves 2 ms. Timings and trigger prevalence on a real workload are unmeasured.

For a later declared population, preselect at most one field per independent family and freeze eligibility/parser before treatment or truth. Exact signed-minor-unit recovery and literal string agreement answer different questions. Wrong output, abstention, invalid parse and missing arm output score zero correctness; distinguish wrong and abstaining dispositions in the nine paired transitions. Across all N eligible families the signed change is (R−G)/N. Three newly correct and one formerly correct lost among ten give +20 percentage points. With independent exchangeable discordant directions under the stated null, condition on D=R+G: R follows Binomial(D, 1/2). At D=4 and R=3 the one-sided tail is 5/16. When D=0 there is no directional evidence. N=0 gives an undefined change. This hand-selected feasibility target supplies no physical paired denominator.

Repeated reads of a single C9b amount 11 remain one coordinate: the candidate distances are 0, 1, 1 and all three survive a radius-one decoder. Distance at least three across distinct queried coordinates separates radius-one balls by the triangle inequality, provided truth is in the set and at most one coordinate is wrong. A local attention path and information inherited from earlier layers can still matter when selected remote blocks miss the target. Neither an adverse field result nor a crop win would establish a mechanism or the need for training.

## Local governance and verification

I adopted the exact page-6 rule for future eLedgerCare architecture handoffs and amendments. The reviewer independently compared all six paragraphs with the PDF, the staged wording and the final AGENTS.md. The normalized UTF-8 rule SHA-256 is `f3056867a46caf35543e859dac7da0cbdb36d440b1c3c66e4b0a9856a84b2381`. The agreement blob is `05e96c7f9992c0cb218c4d1b37a30394d4a543dd` at `b249b1becfb7be801016f1c835bd5de7470b83b6`. All prior agreement bytes are retained. This is a local adoption under eLedgerCare ownership. The governance review used the supplied page and eLedgerCare records. Workspace Ledger was neither accessed nor modified, and its PR integration status was left unverified. The source audit separately read public Baidu model revision metadata. [Exact rule](../../../coordination/WP-0041/handoff-rule.md) · [Working agreement](../../../../AGENTS.md)

The author froze check source at `71ad1a2cb2324c2c89485085dedb4e2c3083aac6` and published evidence at `da275f4f036c2f6fb1af28a231157ada70fc1430`. The source checks verified 18 local runtime files, eight historical imported-module copies and 32 pinned package versions. The exact arithmetic covered 22,500 score-movement cases, 729 geometric checks, 512 radius-one triples and 1,375 cost cells. These are CPU examples and enumerations. [Source and runtime inventory](../../../research/WP-0041/source.json) · [Arithmetic outputs](../../../research/WP-0041/math.json)

The custodian's first verifier failed in its historical receipt lookup when an integer token index shadowed the receipt map. The corrected source `091a8e0557c264629612422dd59a6767771ef4c7` passed against all 32 pinned source records. I reran `python -I -B docs/custody/WP-0041/verify.py` in the integration and compared stdout using LF with the published field blob, obtaining SHA-256 `11aa760ae7f87abf21fe89c2dfc6e5dbc42f9f11bb65f6287588bc0d1ecf194a`. I also ran `python -I -B docs/research/WP-0041/math_check.py --out <new coordinator scratch file>` and compared original bytes at the evidence SHA, obtaining `bde02e780cc3e2ba524f813324d08909b257218d0bf062ec5e5dbbebb0719d2c`. Both exited zero. The custody diagnostic concerned evidence indexing and occurred before any model execution. The reviewer used independent proof code and a separate native-ID/PDF geometry reconstruction. Independently executing the frozen author and custodian checkers reproduced all three canonical outputs, including the source record at SHA-256 `41ab0761ebdcbf21f14c148d9c2abd40224c26dbe6a5a9957ede1781e282c72e`. [Independent reconciliation](../../../reviews/WP-0041/reconciliation.json) The reproduced input raster RGB digest was `6d49398a6e94f1ed8d9ee0e7b68678e69dd03d690f955c01edb94c458e29711c`. [Selected field and positions](../../../custody/WP-0041/field.json) · [Custody attempts](../../../custody/WP-0041/verification.json) · [Reviewer's checks](../../../reviews/WP-0041/check.py)

The primary integration retains all original role commits and checks each merged blob against its owner. All 115 earlier worktrees, the existing stash and historical primary package edit were preserved. Below is the inventory from base to the integrated deliverable, followed separately by this disposition, the updated shared ledgers and the public receipt. [Preservation](../../../coordination/WP-0041/integrity.json) · [Public download and lineage verifier](../../../coordination/WP-0041/verify_publication.py)

```text
AGENTS.md
CURRENT.md
INDEX.md
docs/agent-reports/eld-owner-probe/WP-0041/002_2026-11-26_research_eld-owner-probe.md
docs/agent-reports/eld-rd-reviewer/WP-0041/003_2026-11-26_review_eld-rd-reviewer.md
docs/agent-reports/eld-twin-custodian/WP-0041/001_2026-11-26_research_eld-twin-custodian.md
docs/coordination/WP-0041/assignment.md
docs/coordination/WP-0041/dispatch.json
docs/coordination/WP-0041/handoff-rule.md
docs/coordination/WP-0041/integrity.json
docs/coordination/WP-0041/replay-gate.json
docs/coordination/WP-0041/verify_publication.py
docs/custody/WP-0041/field.json
docs/custody/WP-0041/intake.md
docs/custody/WP-0041/verification.json
docs/custody/WP-0041/verify.py
docs/research/WP-0041/analysis.md
docs/research/WP-0041/math.json
docs/research/WP-0041/math_check.py
docs/research/WP-0041/source.json
docs/research/WP-0041/source_check.py
docs/reviews/WP-0041/archive-results.json
docs/reviews/WP-0041/archive.py
docs/reviews/WP-0041/check.py
docs/reviews/WP-0041/derivations.md
docs/reviews/WP-0041/mathematical-results.json
docs/reviews/WP-0041/reconcile.py
docs/reviews/WP-0041/reconciliation.json
```
