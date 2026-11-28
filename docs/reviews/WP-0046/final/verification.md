# WP-0046 final non-author verification (eld-rd-reviewer)

I verified eld-owner-probe's final candidate dd7982dc7d8a1c468bf90704d8fb01c60e91c7b5. Its delivered bytes are 23/23 equal to the manifest and to the Git blobs. I also checked the intermediate aca4b43d at 17/17. My earlier records are unchanged: the first freeze 1c9690b9, the exchange ee07ca66, and every file under `challenges/`, `expectations/`, `exchange/`.

The final freeze 9a9f24f0 holds the new label-free bridge cases XB1–XB4, frozen predictions and two tools. It was committed before any execution. All runs are post-opening and none is blind. The machine-readable record is [verification.json](verification.json) and the commands are in [results/commands.md](results/commands.md).

## What now passes (non-author executed or recounted)

| Check | Result | Frozen prediction |
| --- | --- | --- |
| controls_r2 on its own 16 cases | 16/16 | held |
| controls_r2 on my 27 peer-schema cases, required results | 27/27; XC1, XC2, XC3 and XC4 now pass | held |
| controls_r2 running my 49 first challenges | strict mode 49/49; amended mode 47/49, differing on P3 and L3 | held |
| My r1 cases D6r1, D7, D8 | 3/3 | held |
| build_register_r2 --verify | verified, 170 rows | held |
| Register-r2 recount from named fields | every header count reproduces | held |
| Scoped-plan recount Π₀–Π₂ | reproduces | held |
| 31-key allowlist against the worker43 env_for AST | equal | held |
| 18 sys.flags names against prior0 | equal | held |
| exec.env rows at stage 2 | 6 | held |
| native rows with masks moved to reference only | 15/15 | held |
| Ban₁ = ∅ on the 5 archived rows, from three identical e43af2e2 token files | reproduced | aligned post hoc; see the failures below |

## Failures of my own frozen predictions (reported, not rewritten)

**(a) D1 history alignment.** My frozen alignment n = position − 827 aligns 0/5 emissions. A post-hoc offset search finds +1 aligns 5/5. The aligned history lengths are 619–623, which give 585–589 starts for a total of 2,935. That matches the peer's count; my predicted 2,930 was wrong, and the ban sets are empty in both conventions.

**(b) Π₃ hard-unbound recount.** By the binding_status label the count is 13. The peer claims 15, because it also counts the two `deferred_stage3` rows.

## Open findings, each with an owner

| ID | Finding | Discriminator | Owner / decision |
| --- | --- | --- | --- |
| R-F1 | `eval_bridge_delta` exempts declared deltas from the predicates that the register states for them. | XB1: required M, observed P | eld-owner-probe; Rev_2 |
| R-F2 | Corrigenda C3 scopes custody to sealed members; controls_r2 iterates over the schema. | XI1 / ctrl_06 | eld-owner-probe; Stage-1a scorer freeze (author's retained disagreement 2) |
| R-F3 | cpu.env.PATH freezes the `%SystemRoot%` template as a literal value under strict equality. | expanded path vs template | eld-owner-probe; Stage-1a plan |
| R-F4 | The 7 OS pass-through keys are bound relationally to "supervisor value" but labelled `bound_static_rule`. | supervisor environment drift | eld-owner-probe; Stage-1a plan and bridge |
| R-F5 | The Π₃ hard-unbound denominator counts deferred rows. | recount 13 vs 15 | eld-owner-probe; nomenclature |
| R-F6 | cpu.import_resolution keeps aggregate booleans; the per-origin atoms exist only as prose. | one stray module | eld-owner-probe; Stage-1a observer |
| R-F7 | C5.4 labels the rows g = 618..622, but the starts correspond to n = 619..623. | H[position−826] equals the emission 5/5 | eld-owner-probe; wording |
| R-F8 | Preserved conventions: P3 X_oob, the L3 empty view, and the order-integrity return schema. | P3, L3, D7/D8 vs ctrl_16 | eld-coordinator at scorer freeze |
| R-F9 | Prospective runtime hypotheses (venv selection, torch DLLs, debugger, backend flags). | staged observation only | future packets |

The peer has not replied to R-F1 through R-F7. They are late findings and stay open.

## Requests from my exchange (§4)

Verified: 1, 2, 4, 5, 6, 7, 8, 10, 11 and 12. Partial: 3 (R-F1) and 9 (R-F6).

## Certification boundary

Corrigenda C1–C9, the register-r1/r2 bindings and the controls_r2 fixes were formulated by the peer from convergent or reviewer findings. I report only what I executed or recounted. I withhold independent certification of their jointly influenced text.

## Verdicts

Mathematics: **sound core; accept with amendments.** No theorem is refuted.

Implementation, register and operations: **Stage 1a is not ready for release.** It is held by:
- the 4 hard-unbound Π₁ₐ bindings and 5 further pending Π₁ₐ rows;
- the Stage-1a source, which is not yet authored;
- open findings R-F1, R-F3, R-F4 and R-F6;
- Rev_1a and a separate coordinator release.

Released stages beyond Stage 0: **0**.
