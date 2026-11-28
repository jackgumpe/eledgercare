# WP-0046 / 002: Independent review of the direct-stock Stage 0 proposal and Paper I revision 1

- Report path: `docs/agent-reports/eld-rd-reviewer/WP-0046/002_2026-11-28_review_eld-rd-reviewer.md`
- Sequence reservation: INDEX.md WP-0046 table, reservation commit 281b71d1dbf75b8e121a1ea577c0385ae8683555 (eld-rd-reviewer, /002, review)
- Category: review
- Author / agent ID: eld-rd-reviewer
- Actual model / effort: local Claude Code session, model claude-opus-5-5 at effort high, as launched. Requested and actual configuration agree, as far as the session exposes it. No backend identity attestation is exposed.
- Execution environment: CLI (Claude Code); Windows x64; CPython 3.12.10 standard library only; Git Bash
- Published by: eld-coordinator on the author's behalf (normal publication of the owned branch); the author has not pushed
- Timestamp: 2026-11-28T06:37:42Z
- Repository / branch: jackgumpe/eledgercare, review/wp-0046-direct-stock (worktree w046-claude)
- Base revision: 281b71d1dbf75b8e121a1ea577c0385ae8683555. Paper and source pins are at e43af2e263f55478d1d551a5a095536b042589c2.
- Deliverable revision: 324c417a47b8b99bfd10037644a72ec19bbf97ee. Its ordered history:
  - cffc9101 — first expectation freeze;
  - 1c9690b9 — first position;
  - e47e0a2b — post-opening freeze;
  - ee07ca66 — exchange;
  - 9a9f24f0 — final freeze;
  - 324c417a — final verification.
- Previous report: none in WP-0046 (the last was WP-0045 /004)
- Related or reviewed reports: WP-0046 / 001 eld-owner-probe, candidate dd7982dc7d8a1c468bf90704d8fb01c60e91c7b5, with earlier freezes 6fa24295, 84d6934d, 7ededc53, aca4b43d, 7131e240 and 8f5760c9. Also WP-0046 / 003 eld-coordinator (reserved).
- Status: ready-for-review. The independent review is complete, with open findings.
- Next owner: eld-coordinator (Stage-0 disposition)

## Summary

This is an independent non-author review. I wrote none of Paper I, the handoff, the bundle, the bundle register, the peer proposal, the peer registers (r0/r1/r2), its controls or its corrigenda. The work had four phases:
1. A blind first position with two verdicts, plus a 49-case challenge suite whose answers were frozen before execution.
2. One exchange with eld-owner-probe (Gemini).
3. Audits of the peer's actual objects.
4. A final non-author verification of the peer's final candidate dd7982dc.

**Verdict 1, mathematics, Paper I rev. 1 T1–T8a: sound core; accept with amendments.**
- I refuted no theorem. Theorems 1–5, the independent-target corollary and the 1+f erasure bound hold under their assumptions.
- I reproduced them on exhaustive finite domains: 72/72 and 2,048/2,048 identification equivalences, 23,520/23,520 erasure cases, and 160,000 phase cases.
- Both sides independently found the gate-changing amendments, before either saw the other's work:
  - the scoped plan for Eq. 11;
  - defining V_preflight and bridging Stage 1 to Stage 2 in Eq. 12;
  - evaluating the B_arm conjuncts three-valuedly;
  - the determinism premise of Eq. 9;
  - the D_s/D_j symbol collision;
  - correlated erasure.
- I accept these peer-originated amendments: X_oob, partial-phase U, strict typing, order integrity, the empty-view bound and write non-aliasing.
- Conventions still open: P3, L3 and the order-integrity return schema.

**Verdict 2, implementation pp. 15–18, register and operations: Stage 1a is not ready for release.**
- The pinned worker43 cannot reach a CPU cut unchanged, and nobody disputes this.
- The final register-r2 holds 170 obligations (118 + 52) and correctly binds the closed 31-key environment, the subject split, 18 typed flags, the interpreter, runtime and distribution identities, and archive-only masks.
- Stage 1a stays held by:
  - 4 hard-unbound Π₁ₐ bindings: the Stage-1a source pin, the coordinator roots manifest, and the pyvenv.cfg and .pth pins;
  - 5 further pending Π₁ₐ rows;
  - open findings R-F1 (bridge deltas lack value predicates in code), R-F3 (a PATH template frozen as a literal), R-F4 (relational OS pass-through values labelled bound) and R-F6 (aggregate booleans in import resolution);
  - the absence of Rev_1a and of a separate coordinator release.

Released stages beyond Stage 0: **0**. Target executions: **0**.

## Objective and acceptance criteria

WP-0046 authorizes Stage 0 only (docs/coordination/WP-0046/assignment.md). My role, eld-rd-reviewer, owns:
- independently derived opinions on the mathematics and the instructions;
- sealed-first finite fixture expectations;
- a safe offline verification of the supplied checker;
- an audit of the peer's actual proposal and register, one exchange, and this report.

Completion conditions:
- two separate verdicts;
- every material claim tied to a clause, a witness, an expected result and a disposition;
- blind and post-opening work kept separate;
- independent, convergent and joint contributions kept separate;
- no stock, model, device, host-probe or replay activity.

## Change inventory

All 52 paths in the base-to-deliverable diff 281b71d1..324c417a are additions under `docs/reviews/WP-0046/`. None was modified after it was committed.

| Action | Paths | Purpose |
| --- | --- | --- |
| Added (freeze cffc9101) | `README.md`; `challenges/cases.json`; `expectations/{expected,tool-predictions,reference-model-predictions}.json`; `tools/{evaluate,compare,audit_register,archive_checks}.py` | Label-free 49-case suite, frozen answers, predictions and tools |
| Added (1c9690b9) | `first.md`; `results/{evaluate.json,compare.txt,audit_register.json,archive_checks.json,commands.md}`; one-line path fix in `tools/archive_checks.py` | First position and evidence |
| Added (e47e0a2b) | `exchange/challenges/peer-schema-cases.json`; `exchange/expectations/{peer-schema-expected,tool-predictions-post}.json`; `exchange/corrections/{README.md,cases-r1.json,expected-r1.json}`; `exchange/tools/{make_peer_cases,compare_peer,evaluate_r1,audit_peer}.py` | Post-opening freeze and self-corrections R-01–R-06 |
| Added (ee07ca66) | `exchange/exchange.md`; `exchange/results/*` (8 files); `exchange/tools/classify_preconditions.py` | Exchange reply and peer audit |
| Added (9a9f24f0) | `final/challenges/final-cases.json`; `final/expectations/final-expected.json`; `final/tools/{d1_check,recount_r2}.py` | Final freeze |
| Added (324c417a) | `final/verification.{json,md}`; `final/results/*` (12 files) | Final non-author verification |

This report is a separate metadata commit made after 324c417a. I did not touch INDEX.md, CURRENT.md, peer branches or any shared ledger. Private scratch outside Git held the bundle copy, the peer tree exports and the zip archives. These are not published.

## Decisions and rationale

**Authorship and certification.** I give non-author verification of what I executed or recounted. I withhold independent certification of jointly influenced text. That covers the peer's corrigenda C1–C9, its r1/r2 bindings and its controls_r2 fixes, which it formulated from convergent findings or from my findings. A convergent finding counts as independent only for the observation each side made before opening.

**Exchange outcome.** The peer accepted my 12 requests. On final verification:
- 10 are verified: closure, subject split, the d_k = 0 receipt, custody without a schema, ordered projection, live masks, retraction of the L62 witness, 18 flags, binding status separated from observation status, the named entries, and peer-only startup evidence.
- 2 are partial: request 3 has bridge predicates that the code does not evaluate (R-F1), and request 9 keeps aggregate booleans (R-F6).

The peer's controls had failed four of my discriminators, XC1–XC4. They now pass 27/27 of my required results.

**Peer-originated findings I verified.**
- S-04: plan43 says infer_multi while worker43 L377 calls model.infer.
- S-08: the cumulative mask in scorer.py L243/L304, and the finiteness fields missing from native_score.py L532–533.
- The env_for directory side effect.
- The scorer share mode (win.py L107).
- M-04: a cyclic order silently empties `minimal` in my own evaluator. I corrected this as R-01 (r1 at 3/3; the peer confirmed 3/3).
- Ban₁ = ∅ on the five archived rows: I reproduced this from e43af2e2 token history. The peer's 2,935-start denominator is correct.

**My findings the peer accepted.**
- Its review43 L62 base-site witness was wrong. -I keeps base site-packages, so the failed pypdf import points outside it.
- The debugger-attachment delta in the bridge.
- The custody-key subject split.
- Environment closure.

**Evidence limits.**
- Archive facts come from bundle extracts and read-only `git show` at e43af2e2.
- The peer's stdlib launcher-variable observations are peer-observed only. I did not repeat them, because host probes were forbidden.
- Real Q0 venv selection, torch 2.13 DLL loading, the debugger attach/detach choice and the historical backend flags are unmeasured.

## Verification

| Check | Environment and revision | Actual result | Evidence |
| --- | --- | --- | --- |
| Input digests against source-pins.json | private input copy | 4/4 outer, 27/27 bundle; the zip equals the extracted tree | first.md; results/commands.md |
| `python -I check.py` on a private bundle copy | bundle 45252cb6… | exit 0. Six lines equal expected.txt after LF normalization. Bytes are 622 vs 616 because Windows wrote CRLF, so my byte-equality prediction failed. | results/commands.md |
| Independent recomputation of the checker's quantities | tools/archive_checks.py | all reproduced. First run failed on a wrong JSON path, fixed in one line after the freeze. | results/archive_checks.json |
| Register and source audit (bundle) | tools/audit_register.py | 116/116 file tokens and 72/72 pointers resolve; 18/18, 32/32, 2/2 and 16/16 literals; the environment has 6 of 31 keys | results/audit_register.json |
| 49 frozen challenges, my evaluator | tools/evaluate.py | 49/49. This shows internal consistency only, not independent acceptance. | results/compare.txt |
| Peer controls.py, its own 16 cases | 84d6934d | 16/16 | exchange/results/peer-runs.json |
| Peer controls.py on my 27 peer-schema cases | 84d6934d | required 23/27 (XC1–XC4 differ); predicted 27/27 | exchange/results/compare-peer.txt |
| Peer register audit | 84d6934d against e43af2e2 bytes | 32/32, 18/18, 16/16, 2/2, 15/15 literals; 0 unresolved references | exchange/results/audit-peer.json |
| r1 self-correction | exchange/tools/evaluate_r1.py | 3/3 | exchange/results/evaluate-r1.json |
| controls_r2, own 16 / my 27 / final bridge 4 / r1 3 | dd7982dc | 16/16; 27/27 required; 3/4 required (XB1 is R-F1) and 4/4 predicted; 3/3 | final/results/* |
| controls_r2 running my 49 challenges | dd7982dc | strict mode 49/49; amended mode 47/49 (P3, L3) | final/results/r2-claude-49.json |
| build_register_r2 --verify | dd7982dc | verified; 170 rows; sha256 7e430ecd177253d3f7bada89c00f9a46ddf5832e22cabfa236566add7c682902 | final/results/r2-register-verify.txt |
| Independent register-r2 recount | final/tools/recount_r2.py | all header counts reproduce, as do Π₀–Π₂. My frozen Π₃ prediction failed: hard-unbound is 13 by label vs 15 claimed (R-F5). | final/results/recount-r2.json |
| Archive D1 derivation | final/tools/d1_check.py | my frozen alignment failed (0/5). Post-hoc offset +1 aligns 5/5 and gives 2,935 starts with Ban₁ = ∅. | final/results/d1-check*.json |

Register-r2 recount, using the final named fields:

| Measure | Value |
| --- | --- |
| Obligations | 170 = 118 original (same key order as the bundle) + 52 extended |
| Stages | 0:7, 1a:98, 1b:2, 2:61, 3:2 |
| Binding status | bound_static_rule 107; pending 48 (1 Rev_0, 4 at 1a, 1 at 1b, 42 at stage 2); unbound 13 (4 before 1a, 1 at 1b, 8 at stage 2); deferred to stage 3: 2 |
| Observed rows | 0 of 170 |

Scoped plans:

| Scope | Total | Bound | Pending or unbound | Hard-unbound |
| --- | --- | --- | --- | --- |
| Π₀ | 7 | 6 | 1 | 0 |
| Π₁ₐ | 105 | 96 | 9 | 4 |
| Π₁ᵦ | 107 | 96 | 11 | 5 |
| Π₂ | 168 | 107 | 61 | 13 |
| Π₃ | 170 | 107 | 63 | 13 by label; 15 claimed |

The Π₁ₐ hard-unbound keys are cpu.entry.coordinator_roots_manifest, cpu.entry.stage1a_source_pin, static.venv.pth_inventory and static.venv.pyvenv_cfg. The full key lists are in final/verification.json.

Checks not run, with reasons:
- No stock module or worker43 run, no torch or model import, and no device: forbidden.
- No host profile probe: forbidden. For that reason the peer's launcher-variable observations remain unverified by me.
- No execution of amendments.py outside check.py: assignment restriction. My reference-model predictions for it are inspection-only, and the peer confirmed them by inspection.
- No live Stage-1a, 1b, 2 or 3 behaviour: prospective.

## Review map

- First position: `docs/reviews/WP-0046/first.md` at 1c9690b9
- Exchange: `docs/reviews/WP-0046/exchange/exchange.md` at ee07ca66
- Final verification: `docs/reviews/WP-0046/final/verification.md` and the machine-readable `final/verification.json` at 324c417a
- Peer objects reviewed at dd7982dc:
  - `docs/research/WP-0046/{controls_r2.py, build_register_r2.py, register-r2.json, corrigenda-r1.md, proposal-r1.md, exchange.md, final-reconciliation.md}`
  - `docs/agent-reports/eld-owner-probe/WP-0046/001_2026-11-28_design_eld-owner-probe.md`
- Pinned sources at e43af2e2:
  - `docs/research/WP-0043/{native.py, scorer.py#L243, scorer.py#L304, native_score.py#L532, transfer.py#L15, limits.py#L96, stock.py}`
  - `docs/research/WP-0045/{win.py#L107, score.py#L42}`
  - the WP-0005 `F07.warm1.token_ids.json` evidence (sha256 532ffea0…5982, three identical copies)

## Risks, disagreements, and unfinished work

Open findings, each with an owner. R-F1 to R-F7 are late findings with no peer reply yet, and they stay open.

| ID | Finding | Owner | Decision point |
| --- | --- | --- | --- |
| R-F1 | Declared bridge deltas are exempt from value predicates (XB1: required M, observed P) | eld-owner-probe | Rev_2 |
| R-F2 | Corrigenda C3 custody scope differs from controls_r2 behaviour (the author's retained disagreement 2) | eld-owner-probe | Stage-1a scorer freeze |
| R-F3 | cpu.env.PATH freezes a `%SystemRoot%` template as a literal value | eld-owner-probe | Stage-1a plan |
| R-F4 | 7 OS pass-through keys are bound relationally but labelled bound | eld-owner-probe | Stage-1a plan and bridge |
| R-F5 | The Π₃ hard-unbound denominator includes deferred rows | eld-owner-probe | nomenclature |
| R-F6 | Aggregate booleans remain in cpu.import_resolution | eld-owner-probe | Stage-1a observer |
| R-F7 | Corrigenda C5.4 row labels say g = 618..622; the archive-aligned values are 619..623 | eld-owner-probe | wording |
| R-F8 | Unchosen conventions: P3 X_oob, L3 empty view, order-integrity schema; both modes are reproduced | eld-coordinator | scorer freeze |
| R-F9 | Prospective runtime hypotheses | future staged packets | separate releases |

My own failures, all recorded rather than rewritten:
- byte-level checker equality (CRLF);
- one path bug in archive_checks.py;
- a cycle defect in my evaluator, corrected as R-01;
- a wrong frozen D1 alignment;
- a mispredicted Π₃ denominator.

None of these changes a verdict.

## Handoff

Next action: an eld-coordinator Stage-0 disposition. I recommend keeping Stage 1 held (0 released). If a Stage-1a packet is opened, eld-owner-probe should resolve R-F1, R-F3, R-F4 and R-F6 and author the Stage-1a source. A fresh non-author check is then needed for those corrections and for that source. The counts verified here do not need re-checking.

| Item | Value |
| --- | --- |
| Branch | review/wp-0046-direct-stock |
| Deliverable SHA | 324c417a47b8b99bfd10037644a72ec19bbf97ee |
| Report path | this file |
| Report commit | follows the deliverable; the coordinator records it after publication |

Publication receipt: pending. The author has not pushed. The coordinator publishes the owned branch unchanged, and remote confirmation is the coordinator's to record.
