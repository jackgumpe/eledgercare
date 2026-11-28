# WP-0046 first independent position: direct launch to the stock OCR runtime

- Author: eld-rd-reviewer. Local Claude Code session, model claude-opus-5-5 at high effort, as launched. No other identity attestation was exposed. I authored none of Paper I, the handoff, the bundle, the register or the peer proposal.
- Reservation 281b71d1dbf75b8e121a1ea577c0385ae8683555, branch review/wp-0046-direct-stock. Paper and source pins are at e43af2e263f55478d1d551a5a095536b042589c2. All supplied artifacts matched source-pins.json (4/4 outer, 27/27 bundle).
- Expectation freeze commit cffc9101e769bc6f7ab11fdb4137401f8f228490. This file and results/ follow it.
- Status: first position, shareable. This is not the canonical report /002. The peer proposal and register mapping have not been disclosed to me, so I have not read them, and their audit is pending.
- Evidence classes: finite constructed, 49 challenges plus exhaustive small domains; archive, pinned extracts at e43af2e2 with 5 score rows, 118 register entries and the 132/112/110 projections; prospective, **0 target executions**. Nothing here measures stock profile equivalence, private parity, OCR recovery or speed.

## Two verdicts

**Verdict 1. Mathematics, Paper I reviewed revision 1, T1 to T8a: sound core; accept with five required amendments.** Under their stated assumptions, Theorems 1 to 5, the corollary, the erasure bound and the counterexamples are correct. I reproduced them on finite domains: 72/72 and 2048/2048 identification equivalences, 23520/23520 erasure-bound cases, and 160000 phase cases. None of my findings refutes a theorem. Five change a gate or a returned record:
- **M1:** define the scoped plan in T8/(11).
- **M2:** define V_preflight and join it to the stage-2 plan in (12).
- **M3:** evaluate the conjuncts of B_arm and B_m three-valuedly.
- **M4:** state the determinism premise of (9) and H3.
- **M5:** remove the symbol collision between D_s and D_j inside (11)–(12).

The rest are wording or scope corrections.

**Verdict 2. Implementation crosswalk pp. 15–18, register and operations: not ready for a Stage-1 freeze; return to the owner for proposal revision.** I read the pinned stock worker (worker43.py = docs/research/WP-0043/native.py). With that source unchanged, τ = direct-stock with a* = (-s,-P,-B,-u) cannot reach the intended import cut. The register lacks the interpreter identity, the closed environment, typed-ABSENT and closed-world obligations that the stock source itself enforces. The CPU-observable prefix of the stock entry is gated by a device-lease admission. None of this blocks the proposal work. It does define what the owner must bind.

Next owner: eld-owner-probe (proposal revision and the 118-entry mapping), then this reviewer's audit of that actual proposal, then eld-coordinator disposition. No stage is released by this document.

## 1. Question and what would change the decision

The question is which observations bind a future direct-stock execution to the intended interpreter, packages, original files and score phases. Paper I answers it with fibers (Eq. 2–3), a target profile (T2/T2a), creator and custody predicates (Eq. 4–5, T3a), typed diagnostics (Eq. 6–7), phase locality (Eq. 8), capture sufficiency (Eq. 9), measurement design (Eq. 10) and gates (Eq. 11–12). The decision changes if:
- (i) a proved rule returns the wrong verdict on a witness;
- (ii) a gate admits a run the paper intends to exclude;
- (iii) the proposed route cannot produce the observation the gate needs.

Items (i) and (ii) are checked in §3 and §5. Item (iii) is checked in §4.

Symbols follow Paper I. Extra symbols are defined where they are used. ABSENT is measured typed absence, `?` is unobserved, and `{failed}` is a witnessed failure of a required observation.

## 2. Already-adopted amendments (Gemini's archival review, pp. 19–22) and my status

| Gemini finding | Revision-1 text | My status |
| --- | --- | --- |
| F1: -I implies -E, so the seed is ignored; -S suppresses site | T2a implication and a* | **Defend** the CPython semantics (§4 O5). **Change** the premise that a* alone is a launchable stock arm; -P breaks the stock imports (O2). Gemini's "-S disables Windows DLL search-path hooks required by torch" is broader than the paper's narrower adopted wording, which I defend. |
| F2.1 zero dynamic transfer | Corollary, T1 | **Defend**, with a typing tightening (§3 T1). |
| F2.2 inventory completeness | T3a B_arm, omission witness | **Defend** the equation. **Change** its evaluation (M3). |
| F2.3 NTFS continuity | T3a handle-based witness; metadata only corroborates | **Defend** the paper's narrower adoption. Endpoint IDs or timestamps alone cannot exclude a transient write. |
| F3.1 incomparable before unobserved | Eq. 6 order | **Defend.** Minor wording: the cases overlap, so state "first matching case". |
| F3.2 two minimal sets | firstConflict = min X, firstFinding = min(X∪U) | **Defend.** Reproduced in D5 and MIX. The frozen order must be supplied transitively (D6). |
| F4 X_supp, X_choice, storage metadata | T5 prose and T6 layout bound | **Defend.** One wording ambiguity (P7). |
| F5 erasure 1+f | T7 "one missing reading" | **Defend.** Proved and checked on 23520 cases. Correlated source loss can make identification infeasible (K3); the paper's caveat should carry this example. |
| F6.1 static conflict before deferral | ASSESS, TF32 regression | **Defend** (A1, S7). |
| F6.2 stage-3 gate and same-run join | P3, J5 and Eq. 12 | **Defend.** **Change** the definition of V_preflight and add a stage-1→2 join (M2). |
| Strategic: "direct-stock directly inherits WP-0045's proven creator edge" | T2a calls it a candidate; T8 says a rehearsal cannot qualify a later worker | Revision 1 correctly rejects this claim. **Defend the paper against the archival claim.** |

## 3. Mathematics: claim by claim

Each row gives the clause, then the claim or issue, then the witness (C = constructed case id in challenges/cases.json, A = archive, S = source line), then the expected return or smallest discriminator, then the disposition.

**T1, Eq. 2–3, Theorem 1, corollary.** Theorem 1 is correct; the pairwise ∀h1,h2 form reduces to ∀h: P_k = 1. The monotonicity statement is correct when 𝓗 denotes the admissible-history set. The corollary's hypothesis "P_k takes both values on H_T" is ill-typed when P_k depends jointly on (h_D, h_T), as relational bindings do in T2. Its proof pairs one fixed h_D with two target histories. *Change (minor):* require ∃h_D ∈ Ω_D(o_D) with {P_k(h_D,h_T): h_T ∈ H_T} = {0,1}. The conclusion K_k = {0,1} is unchanged. Typed ABSENT versus `?` is exercised in C S6 and D3/D4: ABSENT against "" gives *different*, and ABSENT against ABSENT gives *same*. *Defend.*

**T2a, the startup implication and Q_hash.** The implication -I ⟹ ignoreEnv = 1, so the seed is ignored and randomization is on, is correct CPython 3.12 behaviour. C S1 returns M with X = {ignore_environment, hash_randomization} although the seed string reads back as "0". C S2 returns P and C S3 returns U.

*Fresh, scope:* T2a says "compare the effective flags with their observed stock counterparts". Archive A `prior0.json` records historical `flags` as "full field absent at historical public observation cut". The stock runtime receipt also omits sys.flags (S worker43 L362). The historical counterpart is therefore `?`, and Eq. 6 returns *unobserved* for any relational comparison. *Change:* Q_hash must compare against a frozen absolute expectation. That expectation is derived from the historical argv (-B -u, no -E/-I: S L86–87) and the child environment (PYTHONHASHSEED=0: S L199). It is derived, not observed. Label it so.

**T3, Eq. 4–5, Theorem 2.** Correct. *Fresh archive witness that sharpens Theorem 2:* review43 records the historical worker's sys.orig_argv[0] as the base image, which is the source of the WP-0043 M. It also records sys.executable naming the venv launcher. A direct launch of the same base image would report the same argv[0]. Reported image and argv cannot separate τ = venv from τ = direct-stock, so only the creation join of Eq. 4 can. *Defend.*

**T3a, B_arm, M3 (change).** The conjunction is correct as a predicate. For the verdict, each conjunct must be evaluated separately under Eq. 7, because the paper requires "keep detectable conflicts when another field is missing". Witness C I3: E = ?, I = (a,b), R = (a). Here [b(R) = b(I)] is decidable and false. Expected M with X = {read.missing:b} and U = {schema}. Reading the formula as a single Boolean gives U. Inspection predicts the bundle's `amendments.inventory` returns U (reference-model-predictions.json), so that model is wrong on this input. Also, "unique ... physical object bindings" is not modelled (C I5: two keys bound to one object, expected M). *Change:* write X_arm and U_arm conjunct-wise. C I1 (the omission witness) returns M with X = {omit:b}; C I4 and I6a/b cover multiplicity and the ordered projection.

**T4, Eq. 6–7 and the minima.** Correct. The order ⪯ must be a partial order, i.e. transitive. C D6 supplies a ≺ b ≺ c with events {a,c} and expects {a}. Inspection predicts `amendments.minimal` returns {a,c}, because it uses the supplied pairs without closure. *Change (reference model / guidance):* supply the transitive closure. C D5 is the p. 15 discriminator: an early missing writer receipt (rank 1) and a later wrong device (rank 3) give M, X = {exec.device}, U = {exec.original.writer}, minX = {exec.device} and minXU = {exec.original.writer}.

**T5, Eq. 8 and Theorem 3.** Correct. Exhaustive check: n = 2, z0 ∈ {+0, −0, 1.0, NaN}², z1, z2 ∈ that set ∪ {N}, all mask pairs, 160000 cases. All 256 cases where both transitions pass satisfy the closed form. 6144 cases satisfy the closed form with a failed transition, which is a measured count for "the converse fails". C P1 (the p. 15 T5 row) returns X = {1/2, 2/2} with no winner. C P2 (the Edition A2 example) returns X = {0/1}, although a final-only check would accept emission 0. C P3 to P6 cover supp, choice, the signed-zero tie and a missing emission. *Fresh (wording):* "Missing eligible emission enters U" leaves open whether a row with a score fault still reports the missing emission (C P7). I take reading B, the emission is always a required observation: M with X = {0/1} and U = {emission}. *Unresolved; the paper should state it.*

*Fresh (archive scope):* "Across these five rows D1 = ∅, D2 = {1}". From each row's final_page_guard I derived D2 with the A2 page rule (m = 1 < e = 3, cap 20000 > l ∈ [618, 622], so EOS id 1 is banned). In 5/5 rows it equals the observed c1→c2 effect, with post-page EOS word ff800000 and first dense byte difference 6. D1 cannot be derived, because the no-repeat history is not in the bundle. D1 = ∅ is effect-inferred from c0_identical_c1, and A2 forbids that for witnessing. On these rows X_1 = ∅ is therefore consistency, not a test of Eq. 8. *Change:* label it. *Notation:* Edition A2 uses N and P for permitted support sets, while T5 uses N for the −∞ word and D_p for blocked masks. Add one line of reconciliation.

**T6, Eq. 9 and Theorem 4, M4 (change).** The factorization lemma is correct. It assumes Y_F is a function of s. If a stock kernel is nondeterministic, for example through atomics in a reduction, two runs from one captured state can differ in final words. No g then exists even with perfect capture, and an H3 "linked divergence" could be misattributed to capture insufficiency. *Change:* state determinism of F given s as a premise, or index Y_F by (s, ω), and bind deterministic mode in the trace schema. Bitwise run-to-run determinism is unmeasured; only one content pair matched in WP-0043. The layout bound is correct for nonempty views: C L1 fits, L2 does not (41216 > 40960 bytes), and L3 (a zero-length view) is outside the domain, as the paper says. The two-step counterexample reproduces: C N1 linked gives M, and C N2 reset to the native cache hides it (P).

**T7, Eq. 10 and Theorem 5.** Correct. For C K1, {u,w} at cost 4 is the *unique* minimizer; check.py asserts uniqueness but only computes min (§5). C K2 with f = 1 gives {u,v,w} at cost 7. *Fresh boundary* C K3: if one source carries u and w, then f = 1 source loss is **infeasible** for every selection, because erasing both separates nothing between h0 and h3. The count-bound caveat in the paper is real; add K3 as its example.

**T8, Eq. 11, ASSESS, M1 (change).** "For each mandatory atom in the scoped plan" never defines the scoped plan. Witness C A2a/A2b: every stage-1 atom passes and private.parity (stage 3) has no frozen relation. Literal ASSESS over the whole plan returns U at stage 1, and then V_preflight = P is impossible until P_3 is complete. That contradicts Eq. 12, which carries P_3 as a separate conjunct of the stage-3 gate. Reading only the due stage returns P and lists private.parity as deferred-unbound. Inspection predicts `amendments.assessment` follows the whole-plan reading. *Change:* define Π_s and V^(s) = V(X_static(all) ∪ X_T^(s), (B_T ∩ Π_s) ∪ W_T^(s)). Keep static conflicts plan-wide (A1 and S7 still give M at stage 0), and report B_T \ Π_s visibly. Also say whether the 36 prose `relation` entries count as "frozen comparisons" for B_T. If they do not, B_T has 41 entries now, not 5.

**Eq. 12, M2 (change).** V_preflight is not defined. considerStockCapture = P_2 ∧ [V_preflight = P] ∧ D_2 binds no route, environment schema or source pin between the stage-1 pass and the stage-2 plan. C G1 has a passing preflight under environment schema e1 and a stage-2 plan with e2; G2 passes on direct-stock and plans venv. The literal Eq. 12 returns true for both. T8's prose ("same subject and unbroken scope, or a reviewed bridge") excludes them. *Change:* define V_preflight as V^(1) of the stage-1 plan Π_1, and add [proj(Π_1) = proj(P_2)] on route, environment schema and source pin. This is the stage-1→2 analogue of J5.

**M5 (change, notation).** D_s (deferred set, Eq. 11) and D_j ("design reviewed", Eq. 12) share a letter and an integer subscript on facing pages, so "D_2" in Eq. 12 can be read as the stage-2 deferred set. Other letters are also overloaded:
- H: archive scope, trust class, witnesses H1/H2, the T7 history set, hypotheses H1–H3;
- P: verdict, P_k, the T7 truth, P_j, 𝒫;
- b(·): multiplicity versus byte width;
- A: support set, A_s, A_m.

Rename them in a successor.

**T8a, J5.** Correct, with keys (label, arm, position). C J1 (four rows from r1 and one from another *passing* capture r2) gives J5 false with X = {run:…/1449}. C J2, the duplicate row, fails on multiplicity. *Fresh (reference model):* C J3 and J4 each have five distinct positions from the right run, with one row from F07.warmup or from the untouched arm. The paper requires false. Inspection predicts `amendments.eligible` returns true, because it keys on position only. C J5 is the complete set and returns true. C J6, complete rows with P_3 false, gives considerPrivateReplay = false.

## 4. Implementation, register and operations (source-grounded)

The worker line numbers come from an ast parse; see results/audit_register.json.

**O1. τ = direct-stock is not reachable with the pinned harness unchanged.**
- plan() hardcodes the venv redirector as argv[0] for the supervisor and both workers (L86–87).
- admission() requires Path(sys.executable).resolve() to equal the venv launcher (L117).
- worker() requires the parent's cmdline to end with [stock.py, run] (L323).
- The coordinator release binds plan_sha256 (L102), so any argv change is a new plan digest.

Therefore direct-stock implies a declared change to the supervision layer, even though OCR and model code are untouched, and that change needs its own relation and review. *Required binding:* the owner names the new entry and supervisor source pin and lists every intentional difference.

**O2. a\* = (-s,-P,-B,-u) conflicts with the stock imports.** The worker imports four sibling modules at module scope (L14–17) and later `limits` (L206, L261). The historical argv had no -P (L86–87), so the script directory was sys.path[0]. Under -P these imports fail before any guard runs. C S5 gives M, with a witnessed failed import and later observations U. -s duplicates PYTHONNOUSERSITE=1 (L198) and the venv's include-system-site-packages = false (prior0 `include_system`). *Smallest discriminator:* sys.path[0] and the origin of `timing` in a Stage-1 child. *Recommend:* drop -P, or bind an explicit replacement path entry as an intentional difference.

**O3. The venv selection mechanism is unresolved, and every option carries a semantic risk.** A base start with site enabled selects the base prefix: wrong site-packages, and base distributions become importable. That breaks the triton-ABSENT obligation (L334; source41 triton_distribution_present = false, while the model config has dash_use_triton = true). The options are:
- (a) PYTHONPATH to the venv site-packages: those directories get no .pth processing, sys.prefix stays base, and L117 still fails.
- (b) supplying the launcher variable the venv redirector appears to use: archive review43 shows sys.executable = venv while orig_argv[0] = base. Whether base 3.12.10 honours it on a direct start, and whether it is consumed at startup and is therefore invisible to read-back (the T2a counterexample pattern), is **unverified offline**.
- (c) an explicit bootstrap entry: a new `__main__`.

*Unresolved.* The smallest discriminator is a Stage-1 observation of sys.prefix, base_prefix, executable, _base_executable, the ordered sys.path, site-packages, the effective .pth set and the importlib.metadata distribution set under each option.

**O4. Dropping -E opens every PYTHON\* consumer; the register freezes 6 of the 31 child-environment keys.** The historical child environment is a closed allowlist of 31 keys (L189–199; Popen env= replaces the environment). The register has exec.env.* for only 6 keys and no closure rule. Missing, among others:
- PYTHONUTF8 (utf8_mode);
- PYTHONIOENCODING, PYTHONDONTWRITEBYTECODE, PYTHONUNBUFFERED;
- HF_HOME;
- HF_MODULES_CACHE: dynamic model modules must resolve under it (L359);
- TORCH_HOME, TORCHINDUCTOR_CACHE_DIR, CUDA_CACHE_PATH, XDG_CACHE_HOME, PIP_NO_INDEX;
- PATH, TEMP/TMP/HOME/USERPROFILE, and 7 pass-through system keys.

C S4a passes all 6 register keys while utf8_mode differs (P). C S4b, under the closed schema, returns M with minX = {env.PYTHONUTF8}. *Change:* freeze the full environment as typed presence: every listed key with its value, and every other key ABSENT, including PYTHONPATH, PYTHONHOME, PYTHONSAFEPATH, PYTHONCASEOK and PYTHONWARNINGS (C S6). There are no cpu.env.* keys at all, although T2a gives the CPU rehearsal its own keys.

**O5. Static identity and closed-world obligations missing from the register.** None of the following appears in the register:
- the base interpreter digest. source41 python_sha256 equals windows45's observed image digest, which I verified, so it is cross-source anchored. It is the central subject of direct-stock.
- the venv launcher digest (L125);
- the three runtime_source_sha256 files and the two ACTIVE_RUNTIME files (L42–43, L336–338). All 3 digest literals in the worker are absent from the register.
- triton ABSENT;
- the closed distribution set: 32 pinned plus `pip` (installed_extra_names);
- wheel bytes. The wheel-pin file is not in the bundle.

Under Eq. 11 these belong in B_T until they are bound.

**O6. Stage cuts and side effects in the stock entry.** In worker() the CPU-observable checks come only after:
1. a stdin handshake (L318; EOF raises);
2. admission() (L319), which runs git subprocesses, reads the live coordinator branch's device-release file and requires review, lease and time window. The WP-0043 lease has expired, so a CPU rehearsal fails here as a witnessed failure;
3. a PPID-ancestry handshake (L321–323). This is not a creation witness (Theorem 2);
4. a check that CUDA_VISIBLE_DEVICES equals the device UUID (L326).

Then come the metadata, triton and runtime-source checks (L331–338), `import torch` (L339) and the **first device call at L341**. The module-scope imports of five local modules run before every guard. Their digests are pinned in device43, but their **source is not in the bundle**, so their import side effects are uninspectable here. *Consequence:* the unchanged worker entry cannot be driven to its import cut on CPU. A Stage-1 rehearsal needs a separately reviewed CPU observer entry that replicates the L326–L338 checks and stops before L339. It may stop before L340 only under a separate decision on importing torch, which on Windows is expected, but unverified here for 2.13, to load CUDA runtime images without device initialization. By T8, such a rehearsal qualifies the observer design and the environment. It does not qualify a later worker.

**O7. Continuity of stock outputs.** The stock writer creates each receipt with exclusive-create, writes it and closes (L76–81). The supervisor later hashes it by path (L175–186). No handle is held from seal to read, so under T3a exec.original_continuity is structurally U for the unchanged harness ("endpoint equality alone leaves the interval unobserved") unless an outer observer holds handles. The owner must say where that observer lives.

**O8. Register semantics.** Results of the literal-reference audit:
- 116/116 file tokens and 72/72 JSON pointers resolve; 14 tokens are non-file labels;
- 18/18 model digests agree with both inputs43 and source41;
- 32/32 versions, 2/2 inputs, 16/16 typed options, schedule, device and revision are equal;
- check.py dereferences only 1/118 entries.

Further issues:
- native.support_choice is one key for five rows. X_supp and X_choice are per row, so they need five keys, or the minimal diagnostics lose row identity.
- exec.original, exec.stock_inventory and exec.original_continuity overlap; partition the atoms so one witness does not count twice.
- exec.options.output_path "" and ngram_whitelist_token_ids null correctly keep typed empty and known null apart from `?`.

Directions:
- WP-0045 crosswalk rows compare direct against prior.
- Target atoms compare an observation against a frozen expectation.
- Archive values are references, never target observations (T1).

## 5. Supplied checker: independent verification

I inspected check.py, amendments.py and make_register.py before execution and ran only `python -I check.py` on a private copy. Result: exit 0, 6 lines, stderr empty. The output equals expected.txt after LF normalization; the bytes differ only by 6 CRLF from Windows text-mode stdout, 622 versus 616 bytes. I recomputed every printed quantity with separate code (archive_checks.py):
- 4 genuine launches;
- the denominators 132/112/110, which index different projections, equal across arms;
- 15 copies and 7,756,800 bytes;
- 118/18/32/15;
- 72 identification checks with 72 Theorem-5 agreements;
- 256 compositions;
- 3⁴ = 81 verdict combinations.

Inspection findings, none of which changes a printed number:
1. The "route boundary" loop in `boundary()` is tautological: redirect := s0∧s1, then it checks ¬s1 ⇒ ¬redirect. It tests nothing about Theorem 2.
2. "unique minimum {u,w}" checks only min(); uniqueness is true, and I verified it.
3. The register check dereferences 1/118 pointers and no literal values; O8 covers the rest.
4. The reference models fail I3, I5, D6, J3 and J4 as predicted by inspection (reference-model-predictions.json; not executed, per assignment). The coordinator or the peer can run them on challenges/cases.json.

## 6. Challenge suite

The suite has 49 label-free inputs in challenges/cases.json, with answers frozen separately in expectations/expected.json before execution:
- startup and effective setting S1–S7 (8);
- assessment A1, A2a, A2b (3);
- diagnostics D1–D6 (6);
- inventory I1–I6b (7);
- phase P1–P7 (8);
- five-row join J1–J6 (6);
- gate G1–G2 (2);
- identification K1–K3 (3);
- layout L1–L3 (3);
- linked cache N1–N2 (2);
- one full mixed row.

My evaluator agrees on 49/49 full records. Evaluator and expectations share an author, so this shows internal consistency only, not independent acceptance; I do not review my own fixtures. The suite includes the four commissioned challenges: omitted member (I1, I3), effective setting mismatch (S1, S4b, S5), phase error (P1, P2) and mixed five-row join (J1, J3, J4).

**Full mixed diagnostic row** (case MIX, constructed; the p. 17 minimum return record)

| Field | Value |
| --- | --- |
| Subject / run / arm / stage | constructed CPU rehearsal unit u01 / constructed-r1 / n.a. / s = 1 (no process exists; launch illustrates the T2a hazard) |
| Source revision | challenge tree 281b71d1; reference extracts e43af2e2 |
| Verdict | **M** |
| X (conflicts) | plan.static.sys_executable (T8 static: venv-launcher ∩ base-image = ∅, observed base-image); cpu.hash.ignore_environment (1 vs 0); cpu.hash.hash_randomization (1 vs 0); cpu.import.timing (failed: ModuleNotFoundError); cpu.inventory.members ([a] vs multiset [a,b]) |
| U (missing) | cpu.import.dll_origins (observer did not return); private.parity (no frozen relation; whole-plan reading) |
| firstConflict = min X | {plan.static.sys_executable} (rank 0) |
| firstFinding = min(X ∪ U) | {plan.static.sys_executable, private.parity}; private.parity has no cut rank, so it is co-minimal |
| Deferred | exec.device (stage 2), private.parity (stage 3; unbound) |
| Attribution | eld-rd-reviewer; independent non-author verification pending |

## 7. Smallest discriminating experiment (prospective; proposal only, not released)

Run a Stage-1 CPU rehearsal on a separately reviewed observer entry that stops before `import torch`. Use 2 decisive units under the candidate τ = direct-stock with a frozen closed environment and one named venv-selection mapping. Add 3 control units:
- an isolated start, predicted M as in S1;
- an observer that drops sys.flags, predicted U as in S3;
- a jointly omitted protected member, predicted M as in I1.

Each unit records:
- the WP-0045 creation join and the complete environment (typed);
- sys.flags, prefixes, executables and orig_argv;
- the ordered sys.path, site-packages, the effective .pth set, and sitecustomize/usercustomize (typed ABSENT);
- the distribution set (closed 33), triton ABSENT and the digests of the five local modules and three runtime sources;
- one protected inert member through the scorer read.

Report P, M and U counts over the 5 scheduled units and list unattempted units separately.

Fields that can be specified now are the environment, argv, path mapping, distributions and digests. The device UUID at use, backend, dispatch and stream remain stage 2. Whether torch backend flags are readable after import without device initialization would be a separate stage-1b question. No recovery, accuracy or throughput estimate follows from this experiment.

## 8. Limits and preserved disagreements

- Offline only. The semantics of the venv launcher variable, the DLL loading of torch 2.13 and kernel determinism are unverified hypotheses, and are labelled so.
- I did not inspect the five local import-closure modules, stock.py or the wheel-pin file, because the bundle does not contain them.
- The reference-model predictions are inspection-only.
- One tool path bug was fixed after the freeze (results/commands.md #7–8).
- My frozen byte-equality prediction for check.py was wrong because of CRLF; the content is equal.
- I preserve my disagreement with the archival Gemini claim that direct-stock inherits the WP-0045 creator edge (§2). The peer's new proposal is not yet disclosed, and every disagreement with it remains open until I audit it.
