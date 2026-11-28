# WP-0046 / 001: Direct-Stock OCR Qualification Proposal, Obligation Mapping, Peer Exchange, and Final Stage-0 Reconciliation

- Report path: `docs/agent-reports/eld-owner-probe/WP-0046/001_2026-11-28_design_eld-owner-probe.md`
- Sequence reservation: `INDEX.md` WP-0046 Stage 0 reservation commit `281b71d1dbf75b8e121a1ea577c0385ae8683555` (`docs/coordination/WP-0046/assignment.md`)
- Category: `design`
- Author / agent ID: `eld-owner-probe`
- Actual model / effort: Gemini 4 Neon (XHigh) via local `agy` CLI (`xhigh` requested; backend model variant not separately attested)
- Execution environment: Windows 11 x64, CPython 3.12.10, local `agy` CLI, PowerShell / Git (stdlib-only offline checks)
- Published by: `eld-coordinator` (authored unchanged for normal public branch publication on author's behalf; local-only until coordinator publication)
- Timestamp: `2026-11-28T06:28:00Z`
- Repository / branch: `jackgumpe/eledgercare` / `research/wp-0046-direct-stock`
- Base revision: `281b71d1dbf75b8e121a1ea577c0385ae8683555` (WP-0046 reservation; pinned intake base `e43af2e263f55478d1d551a5a095536b042589c2`)
- Deliverable revision: `8f5760c9fb2cc7fa815bb15007861b8004360eeb` (final verification evidence for frozen `r2` candidate `7131e240f45d551535bab35fa3d3a8260bc7554f`; earlier frozen commits retained immutable: Turn-1 `6fa242950ffd4dfd1d19accc9271e88aada2d552` / `84d6934d96c69fd37d6fe2afde2d24dd1c431a24`, Turn-2 `r1` `7ededc5344d896ba82d7a8fa57e58eb7d1bd8652` / `aca4b43de322532b5d12134cca4d7f3d56522332`)
- Previous report: `WP-0045 / 002` (`docs/agent-reports/eld-owner-probe/WP-0045/002_2026-11-27_research_eld-owner-probe.md`)
- Related or reviewed reports: Peer `eld-rd-reviewer` (`WP-0046 / 002` slot, branch `review/wp-0046-direct-stock`: independent first freeze `1c9690b9eab22dfdf0c943815f5440e6563f2350` [expectation freeze `cffc9101e769bc6f7ab11fdb4137401f8f228490`]; post-opening reply `ee07ca660286927ba5017a5592d2f8bed3a8d702` [freeze `e47e0a2b2a4dfad69fb033059a924872857e52c5`])
- Status: `ready-for-review` (Stage 0 complete for owner; **Stage 1 HELD**; newly changed substantive `r1`/`r2` items require targeted non-author verification by `eld-rd-reviewer`)
- Next owner: `eld-rd-reviewer` (targeted non-author verification of frozen `r1`/`r2` deliverables), then `eld-coordinator`

---

## Summary

This report records `eld-owner-probe`'s complete Stage-0 work for WP-0046 across three strictly preserved, immutable phases: (1) independent pre-opening position, proposal, 118-row register, and constructed controls (`6fa24295` / `84d6934d`); (2) post-opening peer exchange, standalone mathematical/instruction corrigenda, and `r1` proposal/register (`7ededc53` / `aca4b43d`); and (3) final non-author verification of `eld-rd-reviewer`'s `ee07ca66` return plus minimal final supplement `r2` (`7131e240` / `8f5760c9`). This report represents **author design/verification** for owner artifacts and **non-author verification** for peer-owned items at `ee07ca66`; it speaks solely as `eld-owner-probe` and withholds independent certification for any co-influenced or newly edited `r1`/`r2` text.

### Two Durable Separate Verdicts

1. **Verdict 1 — Paper I Mathematics (T1 through T8a, Reviewed Revision 1, physical pp. 2–14 / `paper-I-reviewed.pdf` / `src/stock.tex`):**
   **`AMEND BEFORE STAGE-1 CODE FREEZE` (Core Theorems T1–T8a Sound; Zero Theorems Refuted; Targeted Formal/Assumption Amendments Consolidated in `corrigenda-r1.md` and `final-reconciliation.md`).**
   All core conditional theorems (Theorems 1–5, Independent-Target Corollary, and $1+f$ coordinate erasure bound) hold under their stated premises. Both independent first audits converged on five gate/record-changing amendments (`M1`/`M-08` scoped plan $\Pi_s$ & Eq. 11 alignment; `M2`/`M-09` defined $V_{\rm preflight}$ & Stage 1→2 bridge; `M3`/`M-03` three-valued conjunct-wise $B_{\rm arm}$ & physical uniqueness; `M4`/`M-06` determinism premise of Eq. 9 & H3; `M5`/`M-09` $D_s$/$D_j$/$H$/$P$/$b(\cdot)$/$A$ symbol disambiguation), plus `D6` transitive closure, `J3`/`J4` full-tuple `J_5`, `K3` correlated source-loss infeasibility, and `P7` Reading B. Post-opening reconciliation integrated Claude's T1 Corollary typing, T2a derived-not-observed `Q_hash`, T3 `orig_argv[0]` witness, T3a ordered projection (`I6a`/`I6b`), T8a closed bridge delta $\Delta(e_1, e_2)$, and `d_k=0` receipt contract; Claude accepted Gemini's `X_oob` (`XP3`), partial-phase `U`, strict typing, order integrity (`R-01`), empty-view offset bound, and write non-aliasing. Five narrow format/scope distinctions are preserved open (§ Risks).

2. **Verdict 2 — Implementation Instructions (physical pp. 15–18), Register (`register.json`), and Operations (`worker43.py`):**
   **`HOLD STAGE 1 PENDING TARGETED NON-AUTHOR VERIFICATION OF R1/R2, STAGE-1A CODE FREEZE, CLEARANCE OF UNBOUND Pi_1a OBLIGATIONS, AND SEPARATE COORDINATOR RELEASE` (Released Stages Beyond Stage 0: `0`).**
   Unchanged `worker43.py` (`e43af2e2:docs/research/WP-0043/native.py`) cannot execute a CPU Stage-1 cut (`O1`/`O6`/`S-01`/`S-02`). Versioned `proposal-r1.md`, `register-r2.json` (`118` original + `52` extended = `170` obligations), and `controls_r2.py` resolve all `O1`–`O8`, `S-01`–`S-08`, and all 12 numbered peer requests from `ee07ca66`—including splitting Stage 1 into pure-stdlib **Stage 1a** (stopping strictly before `import torch`; `5` scheduled units = `2` decisive + `3` live controls) and separately gated **Stage 1b** (CPU-only `import torch` + DLL origins), keeping all `6` `exec.env.*` rows at Stage 2 while giving Stage 1a its own closed `31`-key `cpu.env.*` allowlist + `18` derived `sys.flags`, fixing all `4` Turn-1 `controls.py` defects (`XC1`–`XC4`, achieving `27/27` required agreement on Claude's `peer-schema-cases.json`), and cleanly separating `binding_status` from `observation_status`. Under $\Pi_{1a}$ (`105` obligations: `96` `bound_static_rule`, `9` pending/unbound including `4` hard-unbound), Stage 1 remains strictly HELD.

### Strictly Separated Evidence Counts
- **Archive (`e43af2e2` + supplied bundle):** `4/4` outer files, `27/27` bundle/ZIP files, `26/26` `SHA256SUMS.txt`, `4/4` nested PDF attachments verified (`plan43.json` 6,574 B trailing `\n` vs Git `plan-canonical.json` 6,573 B distinguished); WP-0045 `4/4` inert cooperative launches (`132/112/110` crosswalk denominators); WP-0043 `2` cold venv loads, `8` calls, `15` score vectors (`7,756,800` B), formal joint verdict `M` (`0/1` pairs, `0/5` rows); Git `e43af2e2` read-only verifications of `32` wheels (`02-verify-wheelhouse.json`), closed `33` dists = `32 + pip 25.0.1` (`03-pip-check-and-venv-inventory.json`), `3` forbidden absent modules (`flash_attn`, `xformers`, `triton` in `05-preflight-cpu.json`), `6` pure-stdlib/ctypes WP-0043 local siblings (including transitive 6th sibling `transfer.py`), `2,935` 34-gram starts in `F07.warm1.token_ids.json` proving $\mathrm{Ban}_1=\varnothing$ in Git (absent from standalone ZIP), and global public absence of WP-0043 historical `tf32`/`cudnn_tf32`/`deterministic`/`autocast` booleans and Q0 `@venv/pyvenv.cfg` / `*.pth` digests.
- **Finite constructed / stdlib offline checks:** `python -I check.py` (exit `0`, `6/6` LF-equal lines; raw CRLF `622` vs `616` B); Turn-1 stdlib CPython 3.12.10 synthetic 2-line `pyvenv.cfg` check (`5` flag configs, zero stock files; labeled peer-observed synthetic only, `0` host probes in Turns 2–3); `controls_r2.py` on `16/16` owner cases, `27/27` peer-schema cases (required agreement via Claude's `compare_peer.py`), `49/49` strict / `47/49` amended-r1 Turn-1 peer cases, `3/3` peer `R-01` order-integrity cases, and `4/4` `bridge_delta` cases; independent re-execution of Claude's `evaluate_r1.py` (`3/3`).
- **Prospective Target $T$:** **`0` executions** (`0/5` Stage-1a units, `0/2` Stage-1b arms, `0/2` Stage-2 loads, `0/8` Stage-2 calls, `0/5` Stage-2 rows, `0/30` Stage-3 private calls, `0/8` linked bridges). WP-0037 stays parked.

---

## Objective and acceptance criteria

Authorized scope (`docs/coordination/WP-0046/assignment.md`): Stage 0 only—independent critique of Paper I rev. 1 mathematics (T1–T8a) and implementation instructions (pp. 15–18), authorship of the named direct-stock proposal and machine-readable obligation register, bounded constructed stdlib offline controls frozen prior to execution, one structured peer exchange, one final non-author verification/reconciliation, and canonical public report `/001`. Completion criteria met: all supplied digests verified; independent first return frozen before peer opening; peer exchange and non-author verification completed on exact pinned commits (`1c9690b9` and `ee07ca66`); versioned `r1`/`r2` supplements frozen before post-opening checks; zero host paths/private inputs/transcripts/copied PDFs in any committed artifact (`hygiene_leaks=0`); zero stock/torch/model/device/private-replay executions; two distinct verdicts and exact Stage-1 hold rationale recorded.

---

## Change inventory

All `22` deliverable and evidence files reside solely under `docs/research/WP-0046/` (base `281b71d1dbf75b8e121a1ea577c0385ae8683555` to deliverable `8f5760c9fb2cc7fa815bb15007861b8004360eeb`); earlier frozen versions remain completely untouched:

| Action | Exact path | Phase / Commit | What changed and why | Relevant symbols / counts |
| --- | --- | --- | --- | --- |
| Added | `docs/research/WP-0046/first.md` | Turn 1 (`6fa24295`) | Independent pre-opening two-verdict critique (`M-01`–`M-09`, `S-01`–`S-08`, `I-01`–`I-03`) | 2 verdicts, 9 math, 8 source, 3 register findings |
| Added | `docs/research/WP-0046/proposal.md` | Turn 1 (`6fa24295`) | Initial prospective direct-stock proposal (`v1`) | `wp0046-direct-stock-v1` |
| Added | `docs/research/WP-0046/build_register.py` | Turn 1 (`6fa24295`) | Deterministic 118-row generator & verifier (`v1`) | `build_manifest`, `check_hygiene` |
| Added | `docs/research/WP-0046/register.json` | Turn 1 (`6fa24295`) | Concrete 118-row direct-stock register (`v1`) | `118` entries (`sha256: 827cb81b...`) |
| Added | `docs/research/WP-0046/controls.py` | Turn 1 (`6fa24295`) | Constructed offline control entry (`v1`) | `eval_startup`, `eval_inventory`, `eval_score_phase`, `eval_assess`, `eval_replay_gate` |
| Added | `docs/research/WP-0046/control_cases.json` | Turn 1 (`6fa24295`) | 16 constructed control cases with full expected returns | `ctrl_01`–`ctrl_16` |
| Added | `docs/research/WP-0046/offline-evidence.json` | Turn 1 (`84d6934d`) | Post-freeze Turn-1 execution results (`16/16`) | `wp0046-control-results/1` |
| Added | `docs/research/WP-0046/offline-verification-receipt.json` | Turn 1 (`84d6934d`) | Turn-1 digest, `check.py`, `register.json`, and hygiene receipt | `hygiene_leaks=0` |
| Added | `docs/research/WP-0046/exchange.md` | Turn 2 (`7ededc53`) | Point-by-point reply to peer `1c9690b9` (`M1`–`M5`, `O1`–`O8`, `49` cases) | `EX-M01`–`EX-M15`, `EX-O01`–`EX-O08` |
| Added | `docs/research/WP-0046/corrigenda-r1.md` | Turn 2 (`7ededc53`) | Standalone mathematical (`C1`–`C9`, `M5` table) & pp. 15–18 corrigenda | `C1`–`C9`, disambiguated symbols |
| Added | `docs/research/WP-0046/proposal-r1.md` | Turn 2 (`7ededc53`) | Revised prospective proposal with Stage 1a/1b split & 31-key closed env | `wp0046-direct-stock-r1` |
| Added | `docs/research/WP-0046/build_register_r1.py` | Turn 2 (`7ededc53`) | Deterministic `r1` register generator (`118+44=162`) | `build_manifest`, `STAGE_ORDER` |
| Added | `docs/research/WP-0046/register-r1.json` | Turn 2 (`7ededc53`) | `r1` machine-readable obligation mapping | `162` obligations (`sha256: 18767671...`) |
| Added | `docs/research/WP-0046/controls_r1.py` | Turn 2 (`7ededc53`) | Independent 10-family evaluator for peer `49` cases + owner `16` | `eval_claude_*`, `run_claude_suite` |
| Added | `docs/research/WP-0046/post-opening-self-controls.json` | Turn 2 (`aca4b43d`) | Post-freeze `r1` owner `16/16` results | `expected_matches=16` |
| Added | `docs/research/WP-0046/post-opening-claude-eval.json` | Turn 2 (`aca4b43d`) | Post-freeze `r1` peer `49`-case evaluation (`49/49` strict, `47/49` amended) | `paper-r1-strict`, `amended-r1` |
| Added | `docs/research/WP-0046/post-opening-verification-receipt.json` | Turn 2 (`aca4b43d`) | Turn-2 `r1` verification & hygiene receipt | `hygiene_leaks=0` |
| Added | `docs/research/WP-0046/final-reconciliation.md` | Turn 3 (`7131e240`) | Non-author verification of peer `ee07ca66` (`34/34` files) & disposition of 12 peer requests | Requests `1`–`12`, `R-01`–`R-06` |
| Added | `docs/research/WP-0046/build_register_r2.py` | Turn 3 (`7131e240`) | Minimal final `r2` register generator (`118+52=170`) | `DERIVED_SYS_FLAGS_18`, `BRIDGE_DELTA_SCHEMA`, `_classify_statuses` |
| Added | `docs/research/WP-0046/register-r2.json` | Turn 3 (`7131e240`) | Final Stage-0 register supplement (`r2`) | `170` obligations (`sha256: 7e430ecd...`) |
| Added | `docs/research/WP-0046/controls_r2.py` | Turn 3 (`7131e240`) | Final control evaluator fixing `XC1`–`XC4` + `eval_bridge_delta` + `R-01` adapter | `eval_startup_r2`, `eval_inventory_r2`, `eval_assess_r2`, `eval_bridge_delta` |
| Added | `docs/research/WP-0046/final-verification-evidence.json` | Turn 3 (`8f5760c9`) | Post-freeze `r2` verification evidence (`27/27` peer-schema, `16/16` owner, `3/3` `R-01`, `49/49` strict, `4/4` bridge) | `hygiene_leaks=0` |

- **Report metadata committed separately afterward:** `docs/agent-reports/eld-owner-probe/WP-0046/001_2026-11-28_design_eld-owner-probe.md` (this report).
- **External persistent changes:** None. All temporary scratch files (cleaned UTF-8 PDF text renderings and Turn-1 synthetic 2-line `pyvenv.cfg` test dir) remained strictly inside role scratch outside Git, and temporary synth test dirs were deleted after Turn 1.

---

## Decisions and rationale

1. **Core theorem preservation vs formal/checker fixes:** Zero core theorems (T1–T8a) were refuted. Required changes split cleanly into (a) formal/assumption corrigenda (`C1`–`C9` in `corrigenda-r1.md`, notably scoped $\Pi_s$, $V_{\rm preflight}$ + closed $\Delta(e_1, e_2)$ bridge, conjunct-wise T3a, determinism premise `M4`, symbol table `M5`, `X_oob`/`P7` Reading B, `K3`, and `d_k=0` receipt rule) and (b) concrete software/register fixes (`amendments.py` bugs, `WP-0043/scorer.py` L304 cumulative mask, `native_score.py` L532–533 finiteness omissions, `transfer.py` L15–16 empty-view offset, `plan43` `infer_multi` vs `worker43.py` L377 `model.infer`, `controls.py` `XC1`–`XC4`, and `register-r2.json` `170` obligations).
2. **Stage-1a / Stage-1b split (`O6`):** Adopting `eld-rd-reviewer`'s recommendation to stop Stage 1a strictly **before `import torch`** (`5` units = `2` decisive + `3` live controls `S1`/`S3`/`I1`; `512 MiB` commit; `0` `torch`/CUDA DLL risk) and gate CPU-only `import torch` + `LOAD_DLL_DEBUG_EVENT` DLL-origin hashing in a separate Stage 1b eliminates unverified Windows PyTorch 2.13 DLL-loading risk from the initial venv/env/custody gate.
3. **Subject separation & exact closed-world bindings (`Requests 1–12`):** Keeping all `6` `exec.env.*` rows at Stage 2 while giving Stage 1a dedicated `cpu.env.*` keys (`13` named + `18` grouped = `31` child keys + `1` launch-only `__PYVENV_LAUNCHER__` + closed-world `ABSENT` rule) prevents Stage-1/Stage-2 conflation. Binding all `18` CPython 3.12.10 `sys.flags` fields (derived-not-observed), per-module/per-DLL origin atoms, live-guard `Ban_1`/`Ban_2` derivation (archive masks reference only), closed $\Delta(e_1, e_2)$ bridge (explicitly covering `CUDA_VISIBLE_DEVICES`, `PATH`, `DEBUG_ONLY_THIS_PROCESS`/PEB/debug-heap/first-chance exceptions, and entry filenames), `@base/Lib/site-packages` Stage-1a inventory (retracting our mistaken Turn-1 `review43` L62 inference), and separate `binding_status` vs `observation_status` across all `170` obligations closes every actionable peer request from `ee07ca66`.
4. **Independence discipline:** Independent pre-opening findings (`IND-G`, `IND-R`), independent pre-opening convergences (`CONV`), read-only Git `e43af2e2` fact checks, and post-opening co-influenced revisions (`POST`) are tagged explicitly throughout `exchange.md` and `final-reconciliation.md`; no post-opening `r1`/`r2` revision is self-certified.

---

## Verification

### Executed Offline Checks (Stdlib Only; Frozen Candidate Before Each Execution)

| Check / exact command | Environment & revision | Actual result | Evidence location |
| --- | --- | --- | --- |
| Input digest & nested PDF attachment audit against `source-pins.json` | Win11 x64, Py 3.12.10; intake `e43af2e2` | `4/4` outer, `27/27` ZIP & extracted bundle, `26/26` `SHA256SUMS.txt`, `4/4` nested PDF attachments exact; `17/18` `bundle/sources/*` match Git blobs (`plan43.json` 6,574 B trailing `\n` vs Git 6,573 B) | `docs/research/WP-0046/offline-verification-receipt.json` |
| `python -I check.py` (read-only inside extracted bundle) | Win11 x64, Py 3.12.10; bundle `45252cb6` | Exit `0`, `6/6` lines LF-equal to `expected.txt` (raw stdout `622` B CRLF vs `616` B LF) | `docs/research/WP-0046/offline-verification-receipt.json` |
| Turn-1 synthetic 2-line `pyvenv.cfg` stdlib flag check (5 configs; zero stock/torch files; peer-observed only) | Win11 x64, Py 3.12.10; Turn 1 (`6fa24295`) | Confirmed `-I` breaks `PYTHONHASHSEED=0`/`PYTHONUTF8=1`; bare `-s -P -B -u` leaks base site-packages; synthetic `__PYVENV_LAUNCHER__` honored and removed from `os.environ` (unverified on real Q0 `@venv`) | `docs/research/WP-0046/first.md#M-01` |
| `python -I -B docs/research/WP-0046/build_register.py --verify` & `controls.py --cases control_cases.json` | Win11 x64, Py 3.12.10; frozen `6fa24295` | Exit `0`; `118` rows verified (`sha256: 827cb81b...`); `16/16` owner cases match; `hygiene_leaks=0` | `docs/research/WP-0046/offline-evidence.json`, `offline-verification-receipt.json` |
| Peer exchange `1c9690b9` (`15/15` manifest) + `build_register_r1.py --verify` + `controls_r1.py` (`16` owner + `49` peer cases) | Win11 x64, Py 3.12.10; frozen `7ededc53` | Exit `0`; `118+44=162` obligations verified (`sha256: 18767671...`); `16/16` owner; peer `49/49` strict, `47/49` amended-r1 (`P3`, `L3`); `hygiene_leaks=0` | `docs/research/WP-0046/post-opening-self-controls.json`, `post-opening-claude-eval.json`, `post-opening-verification-receipt.json` |
| Peer verify `ee07ca66` (`34/34` manifest) + independent re-run of `evaluate_r1.py` (`3/3`) & `compare_peer.py` (`23/27` on Turn 1) | Win11 x64, Py 3.12.10; peer `ee07ca66` | Exit `0`; `evaluate_r1.py` matches `expected-r1.json` and `results/evaluate-r1.json` (`3/3`); `compare_peer.py` matches `compare-peer.txt` (LF) | `docs/research/WP-0046/final-verification-evidence.json` |
| `python -I -B docs/research/WP-0046/build_register_r2.py --verify` | Win11 x64, Py 3.12.10; frozen `7131e240` | Exit `0`; `118+52=170` obligations verified (`sha256: 7e430ecd...`); `hygiene_leaks=0` | `docs/research/WP-0046/final-verification-evidence.json` |
| `controls_r2.py` on owner `16` + peer `27` (`compare_peer.py`) + peer `R-01` `3` + peer `49` + `4` `bridge_delta` controls | Win11 x64, Py 3.12.10; frozen `7131e240` | Exit `0`; owner `16/16`; peer-schema **`27/27` required** (`XC1`–`XC4` fixed!); peer `R-01` `3/3`; peer `49/49` strict (`47/49` amended-r1); `bridge_delta` `4/4` (`G1`/`G2`/`E-I5` `M`, declared-only `P`); `hygiene_leaks=0` | `docs/research/WP-0046/final-verification-evidence.json` |

### Meaningful Failures & Corrections Observed
1. **Turn-1 `controls.py` defects caught by peer (`XC1`–`XC4`):** Turn-1 `controls.py` passed only `23/27` required on Claude's `peer-schema-cases.json` (missing env closure `XC1`, missing-schema custody skip `XC2`, default scope `[0, s]` dropping stage 1 at stage 2 `XC3`, missing ordered projection `XC4`). All four are fixed and verified `27/27` in `controls_r2.py` (`7131e240` / `8f5760c9`).
2. **Turn-1 mistaken `review43` L62 witness (`E-M01`):** Turn-1 `first.md` inferred `pypdf` lived in `@base/Lib/site-packages` from `review43` L62; Claude proved `-I` retains base site-packages so failure indicated user-site. Retracted and replaced with Stage-1a `static.venv.base_site_packages_inventory` in `register-r2.json`.
3. **Windows CRLF vs LF (`check.py`):** Raw stdout (`622` B) differs from `expected.txt` (`616` B) strictly by 6 CRLF line endings; content is 100% LF-identical.
4. **Bundle whitespace normalization:** `bundle/sources/plan43.json` (`6,574` B, trailing `\n`) differs from Git blob `plan-canonical.json` (`6,573` B); JSON parses identically.

### Checks Explicitly Not Run (and Why)
- **Zero live stock, `torch`, model, GPU, or Q0 `@venv` runs (`0` target executions):** Prohibited in WP-0046 Stage 0 (`assignment.md`). `worker43.py` and `WP-0043/stock.py` were inspected via `ast`/read-only text only and never executed.
- **Zero direct calls to `bundle/amendments.py` outside `check.py`:** Restricted by Stage-0 bundle rules; all `8` peer `reference-model-predictions.json` entries were verified by line-by-line source inspection only.
- **Zero host profile probes in Turns 2–3:** Prohibited by Turn-2/Turn-3 exchange instructions; Turn-1 synthetic stdlib check stays labeled peer-observed synthetic only.

---

## Review map

- **Deliverable chain on `research/wp-0046-direct-stock`:**
  - Turn 1 (independent): `6fa242950ffd4dfd1d19accc9271e88aada2d552` + `84d6934d96c69fd37d6fe2afde2d24dd1c431a24`
  - Turn 2 (`r1` exchange): `7ededc5344d896ba82d7a8fa57e58eb7d1bd8652` + `aca4b43de322532b5d12134cca4d7f3d56522332`
  - Turn 3 (`r2` final supplement & verification): `7131e240f45d551535bab35fa3d3a8260bc7554f` + `8f5760c9fb2cc7fa815bb15007861b8004360eeb`
- **Newly changed substantive `r1`/`r2` items requiring targeted non-author verification by `eld-rd-reviewer`:**
  1. `docs/research/WP-0046/controls_r2.py` (`eval_startup_r2`, `eval_inventory_r2`, `eval_assess_r2`, `eval_bridge_delta`, `eval_claude_r1_minimal`) and `final-verification-evidence.json`.
  2. `docs/research/WP-0046/build_register_r2.py` and `register-r2.json` (`118+52=170` obligations, `exec.env.*` vs `cpu.env.*` split, `18` `sys.flags`, closed $\Delta(e_1, e_2)$ bridge, live-guard `D1`/`D2`, `static.venv.base_site_packages_inventory`, per-origin atoms, `binding_status` vs `observation_status`, and 3 named Stage-2 binding keys).
  3. `docs/research/WP-0046/corrigenda-r1.md`, `proposal-r1.md`, `exchange.md`, and `final-reconciliation.md` (not yet seen by `eld-rd-reviewer` at `ee07ca66`).

---

## Risks, disagreements, and unfinished work

- **Retained narrow disagreements / open design choices (`final-reconciliation.md` §3.2):**
  1. Order-integrity return shape (`evaluate_r1.py` `minimal: None, order_integrity: "cyclic"|"reflexive"` vs `controls_r2.py` `order.integrity` in `conflicts` & frontiers).
  2. Omitted-member custody scoping on `XI1`/`I1` (`I ∩ E` vs Turn-1 `ctrl_05`/`ctrl_06` backward-compatible `member.b.record` missingness).
  3. Historical `D1` provenance boundary (standalone ZIP lacks `F07.warm1.token_ids.json`, whereas pinned Git `e43af2e2` derives `D1=[]` over 2,935 starts; both agree live Stage-2 masks derive solely from live bound guard state).
  4. Stage-2 `-P` sibling loading (`spec_from_file_location` / frozen ordered `@source` vs dropping `-P`).
  5. Unverified prospective operational hypotheses: real Q0 `@venv` `__PYVENV_LAUNCHER__` vs `-S` fallback (Stage 1a); Windows PyTorch 2.13 CPU DLL loading (Stage 1b); Stage-2 `DEBUG_ONLY_THIS_PROCESS` attach-vs-detach (`E-I5`) and historical `tf32`/`cudnn_tf32`/`deterministic`/`autocast` values (`S-07`, globally absent from public Git `e43af2e2`).
- **Concrete unresolved row/atom locators (`register-r2.json#/scoped_plan_summary`):**
  - **Stage 1a hold ($\Pi_{1a}$: `9` pending/unbound of `105`):** *4 hard unbound:* `cpu.entry.stage1a_source_pin`, `cpu.entry.coordinator_roots_manifest`, `static.venv.pyvenv_cfg`, `static.venv.pth_inventory`. *5 pending code/review binding:* `cpu.route_rehearsal`, `cpu.original_inventory`, `cpu.import_resolution`, `cpu.controls.stage1a_3_live_controls`, `limits`, plus `pending_rev0_digest_receipt` on all `7` Stage-0 rows.
  - **Stage 1b (`+2`):** `cpu.stage1b.entry_source_pin`, `cpu.stage1b.torch_import_and_dlls`.
  - **Stage 2 (`+50`, incl. `8` hard unbound):** `exec.backend`, `exec.configuration`, `exec.creator`, `exec.device`, `exec.env.CUDA_VISIBLE_DEVICES`, `stage2.binding.infer_entry_resolution`, `stage2.binding.scorer_phase_local_fix`, `stage2.binding.scorer_finiteness_fix`, `gate.stage1_to_stage2_bridge`, 16 `exec.options.*`, 15 `native.1445..1449.*`, 5 `native.1445..1449.support_choice`, `native.support_choice`, `native.snapshot`, `native.storage`, `exec.original`, `exec.original_continuity`.
  - **Stage 3 (`+2` deferred):** `private.plan`, `private.parity`. WP-0037 remains parked.

---

## Handoff

- **Next action & owner:** Route frozen deliverable commit `8f5760c9fb2cc7fa815bb15007861b8004360eeb` (candidate `7131e240f45d551535bab35fa3d3a8260bc7554f`) and this report to `eld-rd-reviewer` for targeted non-author verification of the newly changed `r1`/`r2` items, then to `eld-coordinator` for Stage-0 disposition and ledger update (`INDEX.md` / `CURRENT.md` remain untouched by this role).
- **Proposed next decision:** Keep Stage 1 HELD (`0` stages released beyond Stage 0); after `eld-rd-reviewer` records `Rev_0` on `r1`/`r2`, open a separate bounded Stage-1a implementation-and-review packet (pure stdlib only, stopping strictly before `import torch`) with coordinator disposition of `@venv/pyvenv.cfg` and `*.pth` pins.
- **Publication receipt:** Local-only on owned branch `research/wp-0046-direct-stock`; remote push and normal public branch publication on author's behalf are pending `eld-coordinator` action.
