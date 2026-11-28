# WP-0046 / 004: Closing Evidentiary Right of Reply to Independent Review Findings R-F1 through R-F9

- Report path: `docs/agent-reports/eld-owner-probe/WP-0046/004_2026-11-28_research_eld-owner-probe.md`
- Sequence reservation: `INDEX.md` WP-0046 closing-reply reservation addendum `c20ca9962fc9effe1b5c5cde61fde6c5d6c7b590` (original Stage-0 reservation `281b71d1dbf75b8e121a1ea577c0385ae8683555`)
- Category: `research`
- Author / agent ID: `eld-owner-probe`
- Actual model / effort: Gemini 4 Neon (XHigh) via local `agy` CLI (`xhigh` requested; same local session as `WP-0046 / 001`; backend model variant not separately attested)
- Execution environment: Windows 11 x64, CPython 3.12.10, local `agy` CLI, PowerShell / Git (stdlib-only offline checks)
- Published by: `eld-coordinator` (authored unchanged for normal public branch publication on author's behalf; local-only until coordinator publication)
- Timestamp: `2026-11-28T06:47:00Z`
- Repository / branch: `jackgumpe/eledgercare` / `research/wp-0046-direct-stock`
- Base revision: `dd7982dc7d8a1c468bf90704d8fb01c60e91c7b5` (immutable `WP-0046 / 001` canonical design report)
- Deliverable revision: `376fae7e82f18d64860af6f8b5a7fb85a8c85b2d` (`docs/research/WP-0046/closing-response.md`)
- Previous report: `WP-0046 / 001` (`docs/agent-reports/eld-owner-probe/WP-0046/001_2026-11-28_design_eld-owner-probe.md`, immutable at `dd7982dc7d8a1c468bf90704d8fb01c60e91c7b5`)
- Related or reviewed reports: `WP-0046 / 002` (`docs/agent-reports/eld-rd-reviewer/WP-0046/002_2026-11-28_review_eld-rd-reviewer.md`, `review/wp-0046-direct-stock`, report tip `c9bc4015877224d2d5fe2dfb3cd39bb0dc600b80`; final verification deliverable `324c417a47b8b99bfd10037644a72ec19bbf97ee`; final freeze `9a9f24f0ab4592eaa6599c695a6a5c92866c4749`)
- Status: `ready-for-review` (Stage-0 closing reply complete; **Stage 1 HELD**; escalated to `eld-coordinator`; no further Stage-0 round sought)
- Next owner: `eld-coordinator` (Stage-0 disposition)

---

## Summary

This supplemental report accompanies `eld-owner-probe`'s bounded Stage-0 closing right of reply ([`docs/research/WP-0046/closing-response.md`](../../../research/WP-0046/closing-response.md), commit `376fae7e82f18d64860af6f8b5a7fb85a8c85b2d`) to the nine previously unseen late/open findings (`R-F1`–`R-F9`) in `eld-rd-reviewer`'s final review `WP-0046 / 002` (`c9bc4015877224d2d5fe2dfb3cd39bb0dc600b80`). This is an **author closing evidentiary reply** (not an independent review of owner work); all prior owner deliverables (`r0`/`r1`/`r2`) and `WP-0046 / 001` (`dd7982dc`) remain completely untouched.

- **Dispositions (`R-F1`–`R-F9`):**
  - **`AGREE` (`6`):** `R-F1` (real checker bug in `controls_r2.py:eval_bridge_delta` L463 skipping value predicates on declared deltas, reproduced post-opening on `XB1`), `R-F2` (disclosed custody-scope difference `corrigenda-r1.md` C3 $I \cap E$ vs `controls_r2.py` L329–330 iterating `E`, Retained Disagreement #2), `R-F3` (unexpanded `%SystemRoot%` template in `cpu.env.PATH` under strict equality), `R-F4` (7 relational `os_passthrough_7` keys labelled `bound_static_rule` in `cpu.env.cache_and_os_keys_18`), `R-F5` (`Pi_3` nomenclature including `deferred_stage3` in `hard_unbound_in_scope`: `15` vs `13` by strict `unbound_` prefix; `Pi_0`–`Pi_2` identical), and `R-F6` (legacy aggregate booleans retained in `cpu.import_resolution` beside prose `per_origin_atom_reporting_req9`).
  - **`DEFEND` (`1`, with editorial wording concession):** `R-F7` (`corrigenda-r1.md` C5.4 followed pinned `e43af2e2:docs/research/WP-0043/archive.py#L13-L17`, where `g = 618..622` is the 0-based last consumed index giving `h = ids[:g+1]`, `n = len(h) = g + 1 = 619..623`, `starts = 585..589` summing to `2,935`, `t = 827 + g = 1445..1449`, and `y = ids[g+1] == emission` `5/5`, reproduced identically in peer `d1-check-posthoc.json`; C5.4 wording omitted defining `g` as last consumed index vs `n = g + 1` and should state both in any Paper I successor edition).
  - **`UNRESOLVED` (`2`, escalated):** `R-F8` (preserved conventions `P3` `X_oob`, `L3` empty-view bound, order-integrity return schema — both modes already reproduced identically by both providers; coordinator convention pick at scorer freeze) and `R-F9` (unmeasured prospective runtime hypotheses — real Q0 `@venv` selection, Windows PyTorch 2.13 CPU DLLs, Stage-2 debugger attach/detach, historical `tf32`/`cudnn_tf32`/`deterministic`/`autocast` — decidable only in separately released staged packets).
- **Verdicts unchanged:** Both verdicts from `WP-0046 / 001` stand unchanged and aligned with `WP-0046 / 002`:
  1. **Verdict 1 (Paper I Rev. 1 Mathematics, T1–T8a):** Core theorems sound; zero theorems refuted; targeted amendments consolidated (`AMEND BEFORE STAGE-1 CODE FREEZE`).
  2. **Verdict 2 (Implementation pp. 15–18, Register, Operations):** **`HOLD STAGE 1`** (`0` stages released beyond Stage 0; **`0` prospective target executions**; WP-0037 stays parked).

---

## Objective and acceptance criteria

Authorized scope (reservation addendum `c20ca9962fc9effe1b5c5cde61fde6c5d6c7b590` under Stage-0 `docs/coordination/WP-0046/assignment.md`): deliver a strictly bounded evidentiary closing reply to `eld-rd-reviewer`'s previously unseen `R-F1`–`R-F9` from `/002` (`c9bc4015`), preserving `/001` and all `r0`/`r1`/`r2` files immutable, authoring zero new definitions, tests, or code/register fixes, executing at most normal-entry post-opening verification of existing frozen `controls_r2.py` on existing peer bridge cases (`XB1`–`XB4`), escalating open items to `eld-coordinator` without requesting another round, and recording this supplemental `/004` report in a separate commit. All criteria are met with `hygiene_leaks=0`, `0` target runs, and `0` stock/`torch`/model/device/host-probe operations.

---

## Change inventory

| Action | Exact path or external resource | What changed and why | Relevant symbols |
| --- | --- | --- | --- |
| Added | `docs/research/WP-0046/closing-response.md` (Commit `376fae7e82f18d64860af6f8b5a7fb85a8c85b2d`) | Compact closing evidentiary reply dispositioning `R-F1`–`R-F9` (`AGREE`/`DEFEND`/`UNRESOLVED`), reporting post-opening `XB1`–`XB4` reproduction, and escalating open items to `eld-coordinator` | `R-F1`–`R-F9`, `XB1`–`XB4`, `eval_bridge_delta`, `eval_inventory_r2`, `archive.py#L13-L17` |

- **Report metadata committed separately afterward:** `docs/agent-reports/eld-owner-probe/WP-0046/004_2026-11-28_research_eld-owner-probe.md` (this report).
- **Prior deliverables (`dd7982dc` and earlier):** `0` files modified, deleted, or renamed.
- **External persistent changes:** None. Post-opening normal-entry check wrote solely to a temporary directory outside Git and left no persistent external artifacts.

---

## Decisions and rationale

1. **No late patching in Stage 0:** Rather than introducing unverified `r3` edits that would demand another review cycle, all six accepted implementation/register/checker findings (`R-F1`–`R-F6`) are accepted cleanly on the record and routed to their exact future decision gates (`Rev_1a` / Stage-1a plan, observer, and scorer freeze for `R-F2`–`R-F6`; `Rev_2` / Stage-2 bridge freeze for `R-F1`), with fresh non-author verification required whenever any correction or Stage-1a source is authored.
2. **Evidence-backed defense on `R-F7`:** Inspecting pinned `e43af2e2:docs/research/WP-0043/archive.py#L13-L17` resolves the apparent off-by-one between `g = 618..622` and `n = 619..623`: `archive.py` defines `g` as the 0-based last consumed index (`h = ids[:g+1]`, `len(h) = g + 1 = 619..623`, `starts = len(h) - 34 = 585..589`, total `2,935`, `y = ids[g+1] == actual_emission` `5/5`). Both providers now agree on `2,935` starts, `[2,0,0,1,2]`, and $\mathrm{Ban}_1 = \varnothing$ (`5/5`), while `corrigenda-r1.md` C5.4 wording is noted for clarification in any successor edition.
3. **Clean escalation of `R-F8` and `R-F9`:** Pure convention choices (`R-F8`, both modes already verified identical) and prospective runtime hypotheses (`R-F9`, unobservable in Stage 0) cannot be resolved by further Stage-0 argument and are escalated cleanly to `eld-coordinator`.

---

## Verification

### Executed Post-Opening Offline Checks (Stdlib Only; Zero New Code/Tests)

| Check / exact command or tool operation | Environment and revision | Actual result | Evidence location |
| --- | --- | --- | --- |
| Peer closing manifest integrity check (`manifest.json`, `53` entries, SHA-256) | Win11 x64, Py 3.12.10; peer tip `c9bc4015` | `53/53` files verified exact (`0` mismatches) | `docs/research/WP-0046/closing-response.md` (header) |
| Post-opening normal-entry run: `python -I -B docs/research/WP-0046/controls_r2.py --cases <peer>/final/challenges/final-cases.json --out <tmp>/r2-on-final-4.json` | Win11 x64, Py 3.12.10; frozen `controls_r2.py` at `dd7982dc` (`7131e240`) | Exit `0`; `XB1`: `P [] [] joined=true` (reproduces `R-F1` false pass), `XB2`: `M ['bridge.PYTHONUTF8']`, `XB3`: `U ['bridge.debugger_attachment']`, `XB4`: `P`; **byte-equal (LF)** to peer `final/results/r2-on-final-4.json` | `docs/research/WP-0046/closing-response.md` §1 |
| Post-opening scorer check: `python -I -B <peer>/exchange/tools/compare_peer.py <peer>/final/expectations/final-expected.json <tmp>/r2-on-final-4.json` | Win11 x64, Py 3.12.10; peer `compare_peer.py` at `c9bc4015` | Exit `0`; `required agreement 3/4; prediction agreement 4/4; returned 4` (`XB1 required: DIFFER verdict;must_include_conflicts:bridge.CUDA_VISIBLE_DEVICES`); **byte-equal (LF)** to peer `final/results/compare-r2-final4.txt` | `docs/research/WP-0046/closing-response.md` §1 |
| Read-only Git source check (`git show e43af2e2:docs/research/WP-0043/archive.py`) & `register-r2.json` / `controls_r2.py` / `build_register_r2.py` line-pointer inspection | Win11 x64, Git / Py 3.12.10; `e43af2e2` & `dd7982dc` | Confirmed exact locators for `R-F1`–`R-F7`, including `archive.py#L13-L17` (`g=618..622`, `h=ids[:g+1]`, `len(h)=619..623`, `starts=585..589`, `2,935`) | `docs/research/WP-0046/closing-response.md` §2 |
| Deliverable hygiene check (`closing-response.md` & `/004` report) | Win11 x64, Py 3.12.10; Commit `376fae7e` & `/004` | `hygiene_leaks=0` (zero host paths, usernames, private inputs, transcripts, credentials, or copied PDFs) | Verified before each commit |

### Checks Not Run (and Why)
- **Zero live stock, `torch`, model, GPU, Q0 `@venv`, `worker43.py`, or host-profile runs (`0` target executions):** Prohibited in WP-0046 Stage 0.
- **Zero new test cases or code/register patches:** Prohibited by the closing right-of-reply scope.

---

## Review map

- Closing evidentiary reply (deliverable at `376fae7e82f18d64860af6f8b5a7fb85a8c85b2d`): `docs/research/WP-0046/closing-response.md`
- Immutable prior owner report & frozen `r2` artifacts (`dd7982dc7d8a1c468bf90704d8fb01c60e91c7b5`):
  - `docs/agent-reports/eld-owner-probe/WP-0046/001_2026-11-28_design_eld-owner-probe.md`
  - `docs/research/WP-0046/{controls_r2.py#L328-L339,L441-L473, build_register_r2.py#L221-L233,L411-L413, register-r2.json, corrigenda-r1.md#L64-L66,L96-L111, final-reconciliation.md#L66-L70}`
- Peer closing return inspected (`c9bc4015877224d2d5fe2dfb3cd39bb0dc600b80` / deliverable `324c417a47b8b99bfd10037644a72ec19bbf97ee`):
  - `docs/agent-reports/eld-rd-reviewer/WP-0046/002_2026-11-28_review_eld-rd-reviewer.md`
  - `docs/reviews/WP-0046/final/{verification.md, verification.json, challenges/final-cases.json, expectations/final-expected.json, results/r2-on-final-4.json, results/compare-r2-final4.txt, results/d1-check-posthoc.json, results/recount-r2.json}`
- Pinned archive reference (`e43af2e263f55478d1d551a5a095536b042589c2`): `docs/research/WP-0043/archive.py#L13-L17`

---

## Risks, disagreements, and unfinished work

- **Accepted implementation/register defects holding Stage 1a / Stage 2 (`R-F1`, `R-F3`, `R-F4`, `R-F6`) and minor consistency/nomenclature items (`R-F2`, `R-F5`):** Escalated to `eld-coordinator` for tracking in future Stage-1a (`R-F2`–`R-F6`) and Stage-2 (`R-F1`) packets; all require fresh independent non-author verification once patched.
- **Unresolved conventions (`R-F8`) and prospective runtime hypotheses (`R-F9`):** Escalated to `eld-coordinator` (scorer-freeze convention decision for `R-F8`; separate staged releases for `R-F9`). No further Stage-0 exchange round is sought.
- **Editorial wording (`R-F7`):** Both providers agree on `2,935` starts and $\mathrm{Ban}_1 = \varnothing$ (`5/5`) from Git `e43af2e2`; `g = 618..622` vs `n = len(h) = g + 1 = 619..623` wording note is recorded for any Paper I successor edition.

---

## Handoff

- **Next action:** `eld-coordinator` records Stage-0 disposition (`WP-0046 / 003` or coordinator closeout), keeping **Stage 1 HELD** (`0` stages released beyond Stage 0; `0` target runs) and carrying `R-F1`–`R-F9` into their respective future Stage-1a / Stage-1b / Stage-2 packet gates.
- **Next owner:** `eld-coordinator`
- **Branch:** `research/wp-0046-direct-stock`
- **Base revision:** `dd7982dc7d8a1c468bf90704d8fb01c60e91c7b5`
- **Deliverable SHA:** `376fae7e82f18d64860af6f8b5a7fb85a8c85b2d` (`docs/research/WP-0046/closing-response.md`)
- **Report path:** `docs/agent-reports/eld-owner-probe/WP-0046/004_2026-11-28_research_eld-owner-probe.md` (committed separately immediately after `376fae7e82f18d64860af6f8b5a7fb85a8c85b2d`; report commit SHA is provided in the handoff message and does not appear inside this file)
- **Publication receipt:** Pending. Local commits only; the author has not pushed and has not edited `INDEX.md` or `CURRENT.md`. The coordinator publishes the owned branch unchanged and records remote confirmation.
