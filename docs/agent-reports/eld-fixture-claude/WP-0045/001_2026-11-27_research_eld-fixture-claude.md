# WP-0045 / 001: Blind 32-row challenge fixtures and the opened independent oracle

- Report path: `docs/agent-reports/eld-fixture-claude/WP-0045/001_2026-11-27_research_eld-fixture-claude.md`
- Sequence reservation: INDEX.md § "WP-0045 direct-launch witness and targeted-depth Edition 02.1", row eld-fixture-claude, reservation commit `1439d0c944a38d0993283b0485f59daa15b73be4`
- Category: research
- Author / agent ID: eld-fixture-claude
- Actual model / effort: Claude Code, model `claude-opus-5-5`. The applied effort is not exposed; INDEX requested high.
- Execution environment: Claude Code CLI on Windows 11 under an ordinary user account. CPython 3.12.10 ran with `-I` (and `-B` after opening), standard library only.
- Published by: eld-coordinator transports this branch unchanged (authorized)
- Timestamp: 2026-11-27T18:04:24Z
- Repository / branch: jackgumpe/eledgercare, `research/wp-0045-fixtures`, worktree `eledgercare-worktrees/w045-fixtures`
- Base revision: `1439d0c944a38d0993283b0485f59daa15b73be4` (parent `7f9281bd247e312bbce89af9a3021832fca965da`)
- Deliverable revision: `3d8a82ed0cdf21f000c0eb612b3c48c6f6cb0d32` (opened artifacts). Its ancestors are fixture freeze `c9a0402fe815441169eb5bfe2331be7b170526fa` and commitment `261f36893db27ee5ad8627366c3842fa140c8383`.
- Previous report: none in WP-0045
- Related or reviewed reports: author /002, edition /003 and reviewer /004 are reserved in INDEX. I have not read them or any candidate source, output or branch.
- Status: ready-for-review
- Next owner: eld-coordinator, for the per-route full-row comparison against the committed blind results

## Summary

This is the fixture author's own report, not an independent review. I froze 32 label-free challenge inputs, one for each row scheduled in `schedule.json`:

- Q1: 12 rows (2 native live requests, 9 constructed records and 1 archive request)
- A1: 6 rows
- A2: 6 rows
- C1: 8 rows

I froze them in Git before any candidate exposure and committed SHA-256 commitments to a separately sealed executable oracle and its full expected rows. The commitment is hiding: a 256-bit nonce, and no per-row digest is public.

The coordinator then authorized opening. Three blind commits already existed: direct `2514ca6c7d31f417b0617ec230037c688c610e52`, edition `2c9637e465ed0ca6e9ce4d023aba3e5c2be548bf` and review `5f1ce93dc933a52fe8dd5d6c8668b9aa34a374e6`. I published the sealed files byte for byte under `docs/fixtures/WP-0045/opened/`. From a clean export of the opened commit I reproduced the following:

- All three committed digests match.
- All 32 row digests match.
- All 33 oracle outputs match byte for byte.
- 94/94 self-test checks pass.
- The comparator scores the expected rows against themselves at 32/32.

I have not compared any candidate. Q1, A1, A2 and C1 q values for each route are the coordinator's next step.

## Scientific question and what these fixtures can decide

Can two independently written implementations of the WP-0045 wire (`wire.md`) produce the same full typed row as a third independent oracle on inputs none of them saw? The comparison is per scheduled ID. The question covers the Q1 provenance projection, the A1 finite branch/commit realization, the A2 guarded FP32 phase check and the C1 exact/noisy query rule. Each row is an exact equality test, so a single mismatched field, key or array order fails it (Paper III eq. Q1: q = n⁻¹ Σ 1{o_r = o*_r}).

What a match shows: the implementation computes the wire's function on that input. What it cannot show is covered under Limits. In particular, a constructed Q1 match never satisfies a native Windows obligation, and the live expected rows state what an ideal compliant observation must yield, not that any route will qualify.

## Operative definitions (as frozen in the oracle)

**Q1 projection.** Atoms k ∈ K come from schedule.json and number 15. Each atom has a canonical source token s_k and checkpoint t_k. For a constructed record (E, O, V), where O may omit keys:

- v_k = U if k ∉ O. Otherwise v_k = P if canon(O_k) = canon(E_k), and M if not.
- canon is JSON with sorted keys. It keeps bool and int distinct, and list order counts.
- The order is M < U < P. A coordinate g ∈ {L, I, E, A, C, B} is min over the keys with prefix g.
- custody = min(L, I, E, A, B), status = min(custody, C) and content = v_content.bytes.

The finding set is F = {k : v_k ≠ P}.

- If F = ∅, first = null.
- If some k ∈ F has V_k.at = null, first = {at: null, keys: sort(F)}.
- Otherwise first = {at: m, keys: sort{k ∈ F : V_k.at = m}}, where m = min V_k.at.

The reason subtype is:

- unresolved for U
- wrong_origin for M on E.caller, E.child or B.origin
- unauthorized_writer for M on B.writer
- integrity for any other M

*Worked example (Q.mixed).* E.caller differs (M, at 3) and B.writer is omitted (U, at 6). That gives E = M and B = U, so custody = M and status = M, and first = {at: 3, keys: [E.caller]}. *Boundary (Q.unordered).* E.caller is unobserved with at = null, and B.writer is M at 6. Because one finding is unordered, first = {at: null, keys: [B.writer, E.caller]}. No order is manufactured.

**A1.** B(x) = x + 1, and the toy decoder Dec returns h itself.

- Stock: one call [stock, a, a+1].
- Duplicate: two calls on the same a, recorded in disjoint scratch, and both readouts are decoded.
- Literal K: a chain h_j = h_{j−1} + 1 with K+1 calls. Only branch kK is decoded.
- The selected transition is [u:β, h_β, g:β]. commits = 1{commit}.
- An impermissible selection returns {M, invalid_selection, 0, []} before any call.

*Boundary.* A1.invalid is a literal with K = 2 and select = k1, an intermediate branch.

**A2.** Phases raw → repeat → page, with cumulative exclusions X₁ = repeat_block and X₂ = X₁ ∪ page_block. Conflicts are:

- ["raw", i] when raw_i is not finite, meaning its exponent bits are all ones
- ["repeat", i] when repeat_i ≠ (ff800000 if i ∈ X₁ else raw_i), compared bitwise
- ["page", i] when page_i ≠ (ff800000 if i ∈ X₂ else repeat_i)
- ["support", −1] when allowed = [0, n) ∖ X₂ is empty

The order is phase order and then index. status = M if any conflict exists. Otherwise the winner is the smallest i ∈ allowed with maximal value(page_i), where −0 = +0. *Boundary (A2.illegal_repeat).* Lexical sorting would put "page" before "repeat", but the conflicts must read [[repeat,1],[repeat,2],[page,4]]. page₁ copies the defective repeat₁, so it is *not* a page conflict. That is how independent defects coexist.

**C1 noisy.** Exact rationals throughout. For a posterior p and a law L_{y,o}:

G(p, L) = Σ_{o: P(o)>0} P(o) Σ_y p(y|o)² − Σ_y p(y)², where P(o) = Σ_y p_y L_{y,o}.

The evaluation runs in this order:

1. A supplied observation from an unused source is applied, unless its marginal is 0, which returns MODEL_CONFLICT.
2. Budget decreases by one if it is positive, and the source is marked used. An observation from an already-used source is ignored.
3. ACCEPT if max p ≥ threshold.
4. Else UNRESOLVED if budget = 0.
5. Else QUERY the argmax-G unused action with G > 0, with ties going to the smallest id.
6. Else UNRESOLVED.

*Worked example (C1.duplicate).* p = (3/5, 2/5), threshold 9/10, used = {s-old}. The observation comes from s-old and is ignored. If it were applied, the posterior would be (27/29, 2/29) ≥ 9/10, giving ACCEPT. That is the discriminating control. Action 2 has law ((2/3, 1/3), (1/3, 2/3)):

- P(o₀) = 8/15, with posterior (3/4, 1/4) and Σp² = 5/8
- P(o₁) = 7/15, with posterior (3/7, 4/7) and Σp² = 25/49
- E = 1/3 + 5/21 = 4/7, so G = 4/7 − 13/25 = 9/175, giving QUERY 2

*Worked example (C1.informative).* The posterior after the observation is (9/13, 2/13, 2/13). Then G₂ = 11/13 − 89/169 = 54/169 > G₄ = 412/1859 > G₅ = 0.

**C1 exact.** Among fields that vary, the oracle takes the argmin of Σ_v n_v² and breaks ties by the smallest index. An empty F gives CONFLICT and a singleton gives IDENTIFIED. *Example.* With F = [[5,1,1,0],[5,2,1,0],[5,1,1,1],[5,2,2,1]], field 0 is constant and the scores are 8, 10 and 8, so the action is 1.

## Change inventory

The base-to-deliverable diff is 74 added files, all under `docs/fixtures/WP-0045/`.

| Action | Path | What and why |
| --- | --- | --- |
| Added | `build_fixtures.py` | Deterministic generator for the inputs and manifest, with a `--check` mode |
| Added | `inputs/<sha16>.json` (32 files) | Label-free inputs. Each is named by its own digest. |
| Added | `manifest.json` | `wp0045.fixtures.v1`, SHA-256 `2c15a26dd1a4d6c5da68c8c5f57e54f0994f75b5926f09ae24b4b6d9e44c0cc0`. Maps ID → family, clause, path, sha256 and bytes. |
| Added | `compare.py` | Expectation-free exact outer-join comparator. Reports q per Q1, A1, A2 and C1. |
| Added | `README.md` | Interfaces, encodings, construction assumptions C1–C5, interpretation choices I1–I7, freeze protocol and limits |
| Added | `oracle-commitment.json` (commit B) | Digests of the sealed oracle, self-test and expected manifest |
| Added | `opened/oracle.py`, `opened/selftest.py`, `opened/expected-manifest.json`, `opened/expected/<ID>.json` ×32, `opened/freeze-log.json` (commit C) | Byte-exact copies of the sealed files |
| Added | `opened/.gitattributes` | `freeze-log.json -text`. The sealed freeze log was written with CRLF, and this rule preserves its exact bytes. |

The derived `__pycache__/oracle.cpython-312.pyc` sealed file is not published. The self-test's import created it before the freeze, and `freeze-log.json` lists it. It is CPython bytecode of the published `oracle.py` with no independent content. This report is committed afterward as separate metadata.

## Decisions and rationale

- **Encodings.**
  - Inputs are UTF-8 compact JSON in constructed member order, followed by one LF.
  - Expected rows are canonical sorted compact JSON followed by one LF.
  - There are no floats anywhere. Rationals are canonical strings, and FP32 values are 8-hex big-endian words.
- **Hiding.** I published no per-row digest before opening, because most rows are short and guessable. The nonce-bearing expected manifest bound each row instead. The nonce is `43824adb…72d2`, and it is now deliberately open.
- **Silent points.** The construction assumptions C1–C5 and interpretation choices I1–I7 were fixed and committed in the README at freeze (`c9a0402f`). Any route that reads one differently should go to reconciliation and not be silently translated. The choices that most affect outcomes:
  - **I1.** `content.bytes` is counted in conflicts and missing, reason, first and source, but not in status or custody.
  - **I3.** The live rows are the ideal all-P observation.
  - **I5.** In A1 duplicate, both readouts are decoded in call order.
  - **I6.** A2 phases are ordered by phase, not lexically, and `allowed` comes from the masks alone.
  - **I7.** In C1, a repeated-source observation is ignored before the zero-marginal check, and ACCEPT takes precedence over budget exhaustion.
- **Archive (H.old).** The record is derived at run time from the pinned blob `git show 7f9281bd:docs/coordination/WP-0044/disposition.json` (SHA-256 `f0a12601…3a14`). That blob is byte-identical to the copy inside Edition02-source.zip.
- **Independence.** The oracle dispatches on input content and never on the ID. A separate hand-written intent table checked every row (32/32). I had no peer or candidate material, and the Gemini review was read only as an advisory input.

## Verification

All checks ran locally and offline under the current user. No check executed candidate code.

| Check | Revision / input | Result |
| --- | --- | --- |
| Source pins (`source-pins.json` ×6, profile, vectors, `model.tex`, 18 `SHA256SUMS.txt` entries, extracted tree vs zip) | coordinator private inputs | All equal. 0 of 19 zip members differ. |
| `python -I reference.py` (Edition 02 original), at freeze and again at opening | edition02 | Exit 0, 24 finite vectors, 448 checks. stdout equals `expected.txt` after CRLF→LF. Raw Windows stdout transport is CRLF, so the bytes are not equal raw. |
| `build_fixtures.py --check` | worktree at `c9a0402f`; export of `3d8a82ed` | 33 files checked, 0 mismatched, 0 unexpected. *Failure evidence:* my first opening export omitted `docs/coordination/WP-0045/schedule.json`. The generator reads that file, so the check stopped with FileNotFoundError (exit 1). It passed once the file was included. |
| Committed blobs vs manifest | `c9a0402f` | 32/32 inputs and the generator equal. No CR in fixture files. |
| Sealed files vs commitment before copying | private seal | 3/3 committed digests. 32/32 row digests. 36/36 freeze-log entries. No host path in any file. |
| Oracle reproduction | pre-commit bytes, worktree at A, clean export of A (freeze); clean export of A and of C (opening) | Byte-identical on every run. Intent mismatches 0/32. Expected manifest `4e7587eb3fd473449068c4c69416b08e1cf947b340532514f11d2e6df6b312e3`. |
| Published vs sealed | export of `3d8a82ed` | 36/36 files identical. Commitment, row digests and fixture-manifest binding all hold. The nonce is present in all three committed files. |
| `opened/selftest.py` | export of `3d8a82ed`, `-I -B` | 94 checks, 0 failed. They cover typed-equality controls, Q1, A1, A2 and C1 negative controls, an independent G formula, and the Edition 02 vectors A02–A06, C01–C06 and Q01–Q02. |
| `compare.py`, expected vs itself | `3d8a82ed` | Q1 12/12, A1 6/6, A2 6/6, C1 8/8, total 32/32, exit 0. At freeze, a perturbed copy scored 29/32 and the extra ID was flagged. |

**Checks not run.**

- No comparison against any candidate output. I neither read nor ran candidate work.
- No Windows trial, process launch or native case. The live rows were not observed.
- No device, model or network use.

### Expected-row overview (full rows in `opened/expected/`)

| Rows | Status | Distinguishing fields |
| --- | --- | --- |
| N.A, N.B | P | All 15 atoms P, first null, canonical sources |
| Q.other_caller / Q.no_caller | M / U | E.caller, first {at 3} |
| Q.other_writer / Q.no_writer | M / U | B.writer, first {at 6} |
| Q.mixed | M | Conflicts [E.caller], missing [B.writer], first {3, [E.caller]} |
| Q.other_original | M | B.origin wrong_origin, first {8} |
| Q.detached | U | Missing [B.direct, B.origin], first {8, both} |
| Q.bad_seal | M | Conflicts [B.seal], missing [B.direct, B.origin], first {7, [B.seal]} |
| Q.unordered | M | Conflicts [B.writer], missing [E.caller], first {null, [B.writer, E.caller]}, source E.caller = unobserved |
| H.old | n/a | {old_joint U, author_genuine_P 0, reviewer_genuine_P 0, genuine_per_route 2, direct_edge unobserved} |
| A1.stock, duplicate ×3, literal | P | Selected stock, stock, duplicate, duplicate, k3. Commits 1, 1, 0, 1, 1. |
| A1.invalid | M | invalid_selection |
| A2.clean / A2.signed_zero | P | Winner 2 / winner 1 (−0 at the lower ID ties +0) |
| A2.masked_nan / A2.raw_inf | M | [[raw,1],[raw,3]] |
| A2.illegal_repeat | M | [[repeat,1],[repeat,2],[page,4]] |
| A2.empty | M | [[support,−1]] |
| C1 | as listed | exact QUERY 1; uninformative UNRESOLVED; informative QUERY 2, gain 54/169; duplicate QUERY 2, gain 9/175; impossible MODEL_CONFLICT; budget UNRESOLVED (1/4, 3/4); threshold ACCEPT (4/5, 1/5); tie QUERY 4, gain 1/8 |

## Review map

- Freeze: `c9a0402f`, which contains `docs/fixtures/WP-0045/{build_fixtures.py, inputs/, manifest.json, compare.py, README.md}`.
- Commitment: `261f3689`, which contains `oracle-commitment.json`.
- Opening: `3d8a82ed`, which contains `opened/`.
- Key symbols in `opened/oracle.py`: `project_q1`, `q1_constructed`, `q1_live`, `archive_old`, `a1`, `a2`, `gain`, `c1_noisy`, `c1_exact`, `INTENT_Q`, `INTENT_OTHER`.

To reproduce: `python -I -B docs/fixtures/WP-0045/opened/oracle.py --fixtures docs/fixtures/WP-0045 --repo . --out <scratch>`, then compare `<scratch>/expected-manifest.json` against `4e7587eb…`.

## Risks, disagreements, and unfinished work

- The wire is silent on several output conventions, which I fixed as I1–I7. A route that reasonably reads one of them differently fails those rows. The coordinator should treat such a difference as a reconciliation item, not as a computational defect, and should not apply post hoc translation.
- The highest-exposure readings:
  - `content.bytes` inside `conflicts` and `missing` (I1)
  - both duplicate readouts in `decoded` (I5)
  - `allowed` computed independently of conflicts (I6)
  - ignoring a used-source observation before the zero-marginal check (I7)
- The live expected rows (I3) are ideal-observer expectations. A route that honestly returns U on N.A or N.B because a witness is missing fails the full-row match. That does not make the result false. Under the wire, missing live evidence holds the direct claim.
- `build_fixtures.py` depends on `docs/coordination/WP-0045/schedule.json` existing in the same repository tree. A partial export without that file fails.
- The published opened set omits one derived `.pyc` that the freeze log lists.

## Handoff

- **Next owner:** eld-coordinator.
- **Next action:** run `compare.py` for each route on the committed blind results and record q separately for Q1 (12), A1 (6), A2 (6) and C1 (8). Keep the original 24 vectors and 448 checks as a separate historical denominator.
- **Branch:** `research/wp-0045-fixtures`
- **Deliverable revision:** `3d8a82ed0cdf21f000c0eb612b3c48c6f6cb0d32`. Its ancestors are freeze `c9a0402f…` and commitment `261f3689…`.
- **Report path:** this file. Its publication SHA follows in the handoff message.
- **Publication receipt:** remote confirmation is pending. The coordinator transports the branch unchanged, and I have not pushed.
