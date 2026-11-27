# WP-0044 / 001: Blinded provenance fixtures and the opened independent oracle

- Report path: `docs/agent-reports/eld-fixture-claude/WP-0044/001_2026-11-27_research_eld-fixture-claude.md`
- Sequence reservation: INDEX.md § "WP-0044 prospective Windows run provenance", row eld-fixture-claude, reservation commit `eb2b09c176cf3793ea9e9f930b913b9769d516e8`
- Category: research
- Author / agent ID: eld-fixture-claude
- Actual model / effort: Claude Code, model `claude-opus-5-5`. The applied effort is not exposed; INDEX requested high.
- Execution environment: Claude Code CLI on Windows 11, ordinary user account, CPython 3.12.10 run with `-I`, standard library only
- Published by: eld-coordinator publishes this branch unchanged
- Timestamp: 2026-11-27T15:11:26Z
- Repository / branch: jackgumpe/eledgercare, `research/wp-0044-fixtures`, worktree `eledgercare-worktrees/w044-fixtures`
- Base revision: `eb2b09c176cf3793ea9e9f930b913b9769d516e8` (parent `13753c13893232a58bc38e5f0ebc5a476fc746bb`)
- Deliverable revision: `4525f03a6396ef413fe76629f93ea6a915d79f32` (opened artifacts). Its ancestors are fixture freeze `40eb491db2330a70fb2203f721ce921f79fa03a9` and commitment `75d1beb4514c7982a4c7b77107d1eedb7365d24d`.
- Previous report: none in WP-0044
- Related or reviewed reports: the author /002 and reviewer /003 are reserved in INDEX. I have not read them.
- Status: ready-for-review
- Next owner: eld-coordinator, for reconciliation against the two committed blind outputs

## Summary

This is the fixture author's own report, not an independent review. I built a challenge suite for the WP-0044 Windows run-provenance contract and froze it before any candidate was exposed. The suite has 16 blinded constructed records, 4 mathematical-control inputs and a versioned 33-row manifest. Separately, I wrote an independent oracle that gives an expected diagnosis for all 33 scheduled rows. It covers the 10 live native rows as ideal-observer models, the 16 constructed rows, the 3 archive rows and the 4 mathematical rows. The oracle code, its self-test and its expected JSON stayed sealed outside Git. Only their SHA-256 commitment was committed.

The coordinator then authorized opening, after both blind outputs were committed (author `f3c59b47…`, reviewer `dae70e25…`). I published the three sealed files byte for byte under `docs/fixtures/WP-0044/opened/` and reproduced them from a clean export of the opened commit:

- the expected JSON digest `42db1f24…`
- 37/37 self-test outcomes
- 33/33 comparator self-agreement

I have not seen either route's results or code, and this report makes no claim about them. Agreement between the routes and these expectations is the coordinator's next comparison. It will need a schema-only crosswalk for each route.

## Objective and acceptance criteria

The objective comes from the assignment, the coordinator handoff and the mathematical handoff, with pins verified as listed in the closing note. It had five parts:

1. Freeze blinded constructed JSON at the neutral interface, carrying no case ID, injection label or expectation.
2. Write an independent executable oracle with frozen expected fields for all 33 rows. Each row needs content and custody subtypes, missing and conflicting keys, the earliest observable point and the witness source.
3. Commit a hiding SHA-256 commitment of the private oracle and expectations before candidate exposure.
4. Open the sealed files only on authorization.
5. Report coverage limits.

Completion conditions:

- every row exists exactly once in schedule order
- the opened bytes equal the committed digests
- a clean rerun reproduces the expected bytes
- every caveat is preserved

All of these were met (see Verification).

## The question each row asks, and the operative mathematics

**Question.** Given one record of observations about a run, can a scorer separate three cases: the requested run's original was scored (P), a contradiction was witnessed (M), or provenance is unresolved (U)? It must also report the reason and keep every unknown. The mathematical handoff (pp. 2–5) gives the model. Below is the projection my oracle implements, so a reader can reconstruct it without the oracle source.

**Atoms.** Let K be the 27 canonical keys, listed in the README. A record supplies an expected map e: K → JSON and an observed map o: K′ → JSON with K′ ⊆ K. A missing key means unobserved. For each k ∈ K:

$$
v_k=\begin{cases}\mathrm U & k\notin K'\\ \mathrm P & o_k\equiv e_k\\ \mathrm M & \text{otherwise}\end{cases}
$$

Here ≡ is type-strict JSON equality: `false ≠ 0`, `null ≠ ""`, list order matters, and object member order does not. So a witnessed absence (`null`) and a witnessed empty value (`""`, `[]`) are values, and only omission is U.

**Coordinates and verdicts.** Order the verdicts M < U < P. For each coordinate X ∈ {L, I, E, A, C, B}, take v_X = min over keys with prefix X of v_k. Then

$$
V_{\rm custody}=\min(v_L,v_I,v_E,v_A,v_B),\qquad V_{\rm joint}=\min(V_{\rm custody},v_C),\qquad V_{\rm content}=v_{\texttt{content.bytes}} .
$$

Proposition 3 of the mathematical handoff follows at once. Any conflict forces joint M. With no conflict, any missing key forces U. Otherwise the joint verdict is P. A conflict on C alone leaves custody P. The oracle asserts this proposition for every provenance row.

**Origin class (B only).**
- verified if v_B = P.
- unresolved if v_B = U.
- wrong_origin if v_B = M with a conflict on `B.direct` or `B.origin`, meaning the scored object is verifiably another run's sealed original.
- integrity for any other witnessed contradiction on B: an invalid seal, an inconsistent member inventory or an unauthorized writer.

Each missing B key adds an unresolved subtype, which is kept even when the class is M. This matches the assignment's rule: wrong B is wrong origin; invalid authentication or inconsistent contents is integrity; detached bytes, a protection gap or unavailable verification are unresolved.

**Earliest point.** Each key has the phase of the observation it represents, on the order launch < image < edge < command < configuration < writer < seal < acquisition < score:

| Phase | Keys |
| --- | --- |
| launch | `E.launcher` |
| image | `L.image`, `I.image` |
| edge | `E.parent`, `E.order`, `E.instance`, `E.job` |
| command | `A.*` |
| configuration | `C.*` |
| writer | `B.writer` |
| seal | `B.seal`, `B.members` |
| acquisition | `B.protection`, `B.direct`, `B.origin` |
| score | `content.bytes` |

If any key conflicts, the earliest diagnosis is the conflict of least phase. Within that phase it is the conflict with the smallest observation `seq`. Missing keys have no event, so if nothing conflicts, every missing key at the least phase is reported together, as incomparable events.

**Worked example (W3.late_missing).** The observed `E.order` is `[launcher.create, launcher.exit, interpreter.create]`, while e expects the interpreter to be created before the launcher exits, and `E.parent` is omitted. So v_{E.order} = M and v_{E.parent} = U, which gives v_E = M, custody M and joint M. The record keeps conflicts {E.order} and missing {E.parent}, and the earliest point is (edge, E.order). This is the handoff's cross-component witness: the lifetime conflict decides the verdict even though the parent receipt is missing.

**Boundary.** Adding a `sources` entry for an unobserved key does not make the key observed. Self-test case 4 checks this on W4.no_I, which stays I = U.

**Decoder controls (mathematical handoff pp. 7–8).** Take a winner y over a support A, with gaps g_j = z_y − z_j, Δ = min_j g_j and perturbation δ.

- The exact unique-winner criterion is δ_j − δ_y < g_j for all j ≠ y.
- The first-index rule relaxes this to ≤ for j > y.
- Two sufficient certificates are ω = max δ − min δ < Δ and 2‖δ‖∞ < Δ.

The oracle evaluates these in exact rationals and asserts that both criteria agree with direct recomputation of the argmax.

**Proved, observed, conditional, open.**
- *Proved:* Proposition 3, by the min-lattice argument. The oracle checks it per row; the pinned `check.py` enumerates all 729 vectors.
- *Observed:* on these fixed inputs, every computed diagnosis equals a hand-written intent table. The archive values below are recomputed from the pinned bytes.
- *Conditional:* the live-row expectations hold only under the ideal-observer models and interpretation choices I1–I6.
- *Open:* whether either route observes those witnesses natively on Windows. This report has no data on that.

## Expected results (opened `expected.json`, sha256 `42db1f24…`)

| Row | Interface | L I E A C B | Custody / joint | Origin class | Conflicts | Missing | Earliest |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W1.A | live | P P P P P P | P / P | verified | – | – | – |
| W1.B | live | P P P P P P | P / P | verified | – | – | – |
| W2.other | live | P P M P P P | M / M | verified | E.launcher | – | launch: E.launcher |
| W4.denied | live | P P P P P P | P / P | verified | – | – | – |
| B1.original | live | P P P P P P | P / P | verified | – | – | – |
| B2.other | live | P P P P P M | M / M | wrong_origin | B.direct, B.origin | – | acquisition: B.direct |
| B3.copy | live | P P P P P U | U / U | unresolved | – | B.direct, B.origin | acquisition: B.direct, B.origin |
| B4.invalid | live | P P P P P M | M / M | integrity | B.seal | B.direct, B.origin | seal: B.seal |
| B4.unavailable | live | P P P P P U | U / U | unresolved | – | B.direct, B.origin, B.seal | seal: B.seal |
| B5.reopen | live | P P P P P U | U / U | unresolved | – | B.protection | acquisition: B.protection |
| W2.helper | constructed | P P M P P P | M / M | verified | E.parent | – | edge: E.parent |
| W3.missing | constructed | P P U P P P | U / U | verified | – | E.parent | edge: E.parent |
| W3.late_missing | constructed | P P M P P P | M / M | verified | E.order | E.parent | edge: E.order |
| W3.reuse | constructed | P P M P P P | M / M | verified | E.instance | – | edge: E.instance |
| W4.bad_I | constructed | P M P P P P | M / M | verified | I.image | – | image: I.image |
| W4.no_I | constructed | P U P P P P | U / U | verified | – | I.image | image: I.image |
| W4.bad_L | constructed | M P P P P P | M / M | verified | L.image | – | image: L.image |
| W5.args | constructed | P P P M P P | M / M | verified | A.args | – | command: A.args |
| W5.script | constructed | P P P M P P | M / M | verified | A.script | – | command: A.script |
| W5.config | constructed | P P P P M P | P / M | verified | C.include_system, C.pyvenv | – | configuration: C.pyvenv |
| W5.empty | constructed | P P P P M P | P / M | verified | C.PYTHONPATH | – | configuration: C.PYTHONPATH |
| W5.unobserved | constructed | P P P P U P | P / U | verified | – | C.PYTHONSAFEPATH | configuration: C.PYTHONSAFEPATH |
| W6.escape | constructed | P P M P P P | M / M | verified | E.job | – | edge: E.job |
| W6.writer | constructed | P P P P P M | M / M | integrity | B.writer | – | writer: B.writer |
| B5.member_missing | constructed | P P P P P M | M / M | integrity | B.members | B.direct | seal: B.members |
| B5.writer_missing | constructed | P P P P P M | M / M | integrity | B.writer | B.direct | writer: B.writer |

Content is P on all 26 provenance rows, because the payload is `46 30 37 0A` throughout. A verifier that checks only bytes would therefore pass every B row. That is the H₂ blind spot, and these rows are built to expose it.

The exact subtype strings are in `opened/expected.json`. Per-key conflict subtypes include `anchor_mismatch` and `other_original`. Missing keys have subtype `unobserved`. The unresolved subtypes are `direct_acquisition_unobserved`, `origin_unbound`, `seal_unverified` and `protection_gap`.

Each conflict also names its witness source:
- for constructed rows, the record's `sources[key].method`
- for live rows, the model's method, for example `process_instance_key` for W2.other and `scorer_handle_identity`/`receipt_mapping` for B2.other

Missing keys have source `null`. The extras are:
- W1.A and W1.B: distinct approved executable roles
- W2.other: two instance pairs retained
- W4.denied: the denial witnessed with no filesystem mutation; the OS error code is to be recorded but not compared

**Archive rows**, recomputed with exact rationals from the pinned `native-evidence.json`:

- **archive.gaps.** The winners are 6, 1449, 16, 1328 and 128822 at positions 1445–1449. The gaps are 10.875, 15.1875, 13.5625, 15.375 and 13.875, each equal to the recorded difference, with raw top-two equal to final top-two. The minimum is 10.875 at row 0, and half of it is 5.4375. The BF16 spacing at 28.0 is 0.125, so the row-0 gap is 87 units of that spacing.
- **archive.support.** The vocabulary is 129,280 (copy bytes ÷ 4). The support is 129,279 on every row, and only ID 1 is excluded, as `000080ff` = −∞. C0 is finite and equals C1 on all rows. On every row the emission equals the final winner.
- **archive.verdict.** The historical result reproduces:
  - Verdict M, first divergent phase `public_document`, conflict key `runtime_contract`, missing key `native_custody_unqualified`.
  - Two argv conflicts (workers `untouched` and `observed`), each differing only at index 0, with equal tails. The expected argv[0] is the venv `Scripts\python.exe` and the observed one is the base `Python312\python.exe`.
  - All five rows are missing at phase B, with row verdicts U×5, 0/5 qualified rows and 0/1 qualified pairs. The F07 target pair matched (1/1), and all five copy triples are complete (5/5).

**Mathematical rows:**
- **math.shift.** A common +10 keeps the winner with ω = 0 and ‖δ‖∞ = 10. The oscillation certificate holds, the ∞-norm certificate fails, and the margin is unchanged. An opposing ±5 shift keeps the winner with ω = 10 < 10.875 and ‖δ‖∞ = 5 < 5.4375. Both certificates hold, and the winner-minus-runner margin falls by 10, which multiplies the odds ratio by e^−10.
- **math.tie.** Raising the runner-up by exactly Δ ties at 28. The first-index winner stays 6, the winner is no longer unique, the strict certificate fails and the first-index criterion holds. The reversed-ID tie (223 vs 128822 at 25) flips the first-index winner to 223.
- **math.signed_zero.** `00000000` and `00000080` are numerically equal and differ in bytes. The first index wins in either order, so the winning word follows position.
- **math.linked.** Stock tokens are [0, 0], reset tokens [0, 0] and linked tokens [0, 1], with linked scores (1, 0) then (−1, 2). The reset trial passes, and the linked trial fails at step 1.

## Interpretation choices for live rows (I1–I6, from the sealed oracle, unchanged)

The handoffs fix the verdicts on the live rows but leave some key sets open. The choices below were frozen before exposure. A route that differs on one of them is an item for coordinator reconciliation, not an error I can adjudicate.

- **I1 (W2.other).** Only the anchor varies, as in `check.py` `anchored_elsewhere`. `E.parent` is judged against the observed launcher, and `E.instance` against the offered pair's own interpreter. The job witness is held fixed, so the conflict set is {E.launcher}. If per-arm jobs also make `E.job` conflict, that is an interpretation delta. It does not change E = M.
- **I2 (B2.other).** The decomposition is B_r = W ∧ S ∧ G ∧ [X = R_r]. Writer exclusivity and seal/protection hold for B's object under its own receipt, while G and the identity check fail. So the conflicts are {B.direct, B.origin}. `B.writer` is treated as exclusivity, not a run-identity comparison. An alternative reading adds `B.writer`.
- **I3 (B3, B4).** Detached bytes are not a sealed original, so `B.direct` and `B.origin` are unobserved. A's original stays exclusively written and protected, and its member inventory matches. An alternative reading also marks `B.writer` and `B.protection` unobserved. That would change the keys, not the verdict.
- **I4 (B5.reopen).** The handle reopened under the same pathname witnesses the same object identity and binding. Only continuity is lost, so the gap alone gives missing {B.protection}.
- **I5 (W4.denied).** A denied incompatible access leaves every genuine witness intact, so all coordinates are P.
- **I6 (phases).** Each key's phase is fixed as listed above. Earliest is decided by phase, then by observation `seq`. A route that assigns B2's identity conflicts at the writer phase, or B5.reopen's gap at the seal phase, differs on `earliest` only.

## Change inventory

The base-to-deliverable diff (`eb2b09c1..4525f03a`) has 29 added paths and no modified or deleted ones.

| Action | Path | What and why |
| --- | --- | --- |
| Added | `docs/fixtures/WP-0044/.gitattributes` | `* -text`, so bytes are committed exactly as hashed. |
| Added | `docs/fixtures/WP-0044/build_fixtures.py` | Deterministic generator with `--check`. Generator digest is bound in the manifest. |
| Added | `docs/fixtures/WP-0044/inputs/constructed/*.json` (16) | Blinded `wp0044.record.v1` records, named by content address. |
| Added | `docs/fixtures/WP-0044/inputs/math/*.json` (4) | Margin, FP32 and linked-cache inputs. |
| Added | `docs/fixtures/WP-0044/manifest.json` | `wp0044.fixtures.v1`, sha256 `1ebfc264…199b212c`, 33 rows. |
| Added | `docs/fixtures/WP-0044/compare.py` | Verdict-free comparator that computes q over the fixed denominator of 33. |
| Added | `docs/fixtures/WP-0044/README.md` | Interface, freeze protocol, coverage matrix and limits. |
| Added | `docs/fixtures/WP-0044/oracle-commitment.json` | Commit B: digests and sizes of the three sealed files. |
| Added | `docs/fixtures/WP-0044/opened/oracle.py` | Opened byte for byte: sha256 `7e177e65…1dc74b`, 30,805 bytes. |
| Added | `docs/fixtures/WP-0044/opened/selftest.py` | Opened byte for byte: sha256 `1758612c…cd8623f`, 3,174 bytes. |
| Added | `docs/fixtures/WP-0044/opened/expected.json` | Opened byte for byte: sha256 `42db1f24…421eff8`, 24,673 bytes. |

This report is committed afterward as report metadata and is not part of the deliverable. I made no INDEX.md or CURRENT.md change and no external change. No push was made by this role, because the coordinator publishes the branch.

## Chronology (commit times UTC)

1. I verified the pinned inputs (see the closing note) and read the assignment, schedule, both handoffs and `reference-checks.zip`.
2. I wrote the generator. A first generation was followed by a realism fix: the interpreter's creation time now follows the launcher's. This happened before the oracle existed.
3. I wrote the oracle and ran the generator. `--check` caught 16 stale first-generation files, which were my own untracked output. I deleted them and regenerated. The oracle's first execution ran on the final bytes and matched intent on all 33 rows.
4. I ran the self-test (37 checks, as stated) and the comparator self-tests. The pinned `check.py` output matched `expected.txt`.
5. **15:05:44Z** Commit A `40eb491d` froze the fixtures. Committed blob bytes equal the manifest digests, with no CRLF.
6. I added interpretation comments I1–I6 to the oracle and a nonce line to the self-test. The expected JSON was byte-identical across all three oracle executions. The sealed files were set read-only.
7. **15:06:47Z** Commit B `75d1beb4` added the commitment. The fixture role made no candidate exposure; whether the routes' exposure came after this commitment is for the coordinator to attest.
8. On the coordinator's authorization, I verified the sealed files against the commitment, copied them and verified the staged blobs. **15:10:49Z** The opening commit `4525f03a` changed nothing in the oracle, self-test or expectations.
9. The clean reproduction from a `git archive` of `4525f03a` passed, as listed below.

## Verification

All commands ran with CPython 3.12.10 and `-I`. "Clean export" means a `git archive` of `4525f03a`, limited to `docs/fixtures/WP-0044`, `docs/coordination/WP-0044/schedule.json` and `docs/coordination/WP-0043/native-evidence.json`, extracted into a fresh private scratch directory.

| Check / command | Revision | Result |
| --- | --- | --- |
| SHA-256 of pinned `coordinator-handoff.md`, `mathematical-handoff.md`, `reference-checks.zip` and `Gemini-Referee-Audit.pdf` | source-pins.json | All four equal their pins. The archive inside the zip equals the repo's `native-evidence.json` (`66eb8bd4…`). |
| Sealed files vs `oracle-commitment.json`, before copying and after staging | `75d1beb4` → `4525f03a` | 3/3 digests and sizes equal. |
| `build_fixtures.py --check` | clean export | 21 checked, 0 mismatched, 0 unexpected. |
| `opened/oracle.py --fixtures … --repo … --out …` | clean export | 33 rows (10/16/3/4). Output is byte-identical to `opened/expected.json` (`42db1f24…`). All intent and archive assertions pass. |
| `opened/selftest.py <fixtures>` | clean export | 37 checks. All 32 required rejections occurred and all 5 classifications held. |
| `compare.py` with the reproduced expectations vs the opened file | clean export | q = 33/33 (live 10/10, constructed 16/16, archive 3/3, mathematical 4/4). |
| Pre-freeze comparator perturbation test | private scratch, before commit A | 31/33. The changed phase and the absent row failed, and the reordered conflict list matched. |
| Pinned `reference-checks.zip` `check.py` | extracted privately | stdout equals `expected.txt` (5 lines); rerun at opening gave the same. |

**Not run.**
- No comparison with either route's output. That needs the coordinator's crosswalk, and this role has no access to those results.
- No native Windows process, file-protection or job operation. That is not in this role's scope.
- No model, GPU or network use.

## Coverage and limits

**Coverage by interface (per route):**
- Native live: 10 rows (W1.A, W1.B, W2.other, W4.denied, B1–B4, B5.reopen).
- Constructed: 16 rows.
- Archive: 3 rows.
- Mathematical: 4 rows.

**Native obligations tested only at the constructed interface:**
- a helper in the direct edge
- a missing parent receipt
- creation after launcher exit
- numeric PID reuse
- a loaded-interpreter image swap
- a removed live image association
- a launcher digest mismatch
- every command or configuration variation
- a job escape
- a same-job unauthorized writer
- an inconsistent sealed member
- an unexpected writer while direct acquisition is missing

A constructed pass cannot satisfy any of these natively.

**Further limits:**
- The live expectations are ideal-observer models, conditional on I1–I6. They bind the diagnosis, not identifiers or timing.
- W5.config changes two keys, because one physical pyvenv.cfg edit moves both the effective value and the file digest.
- The constructed records use synthetic digests and placeholder paths.
- The mathematical rows check exact arithmetic only. They do not estimate any replay, recovery or fault rate.
- The subtype and source vocabularies are this oracle's own and need a separately versioned schema-only crosswalk for each route. A crosswalk cannot change a prediction.

## Risks, disagreements, and unfinished work

- The most likely points of disagreement with either route are the key-level choices I1–I3 and the phase assignment I6. On every live row they leave the coordinate verdicts and the custody/joint/origin classes unchanged. They do change the exact key lists and `earliest`, and so they affect q under the exact-match rule. The coordinator decides whether to reconcile them by one exchange or escalate.
- The `subtype` and `source` strings are oracle vocabulary. Comparing them requires a crosswalk that maps observation methods by meaning, not spelling.
- I did not verify the routes' commit times against my commitment, because that would mean reading their branches.

## Handoff

- Next owner: eld-coordinator.
- Next actions:
  - Build or bind a schema-only crosswalk for each route's blind output (`f3c59b47…` and `dae70e25…`).
  - Run `compare.py --expected docs/fixtures/WP-0044/opened/expected.json` for each route.
  - Reconcile any I1–I6 deltas.
  - Separately confirm that both routes' exposure came after commitment `75d1beb4`.
- Branch: `research/wp-0044-fixtures`. Deliverable `4525f03a6396ef413fe76629f93ea6a915d79f32`. The report publication SHA will be given in the handoff message.
- Publication receipt: remote confirmation is pending, because the coordinator publishes this branch unchanged.

### Closing note: pins, custody, roles

Pins come from `docs/coordination/WP-0044/source-pins.json`:

| File | SHA-256 |
| --- | --- |
| `coordinator-handoff.md` | `1a2025a8…04362e8` |
| `mathematical-handoff.md` | `4118a0ed…efd4b3de` (equal to the copy inside the zip) |
| `reference-checks.zip` | `5dd9e8ce…fd9db9` |

The archive is the repo's `docs/coordination/WP-0043/native-evidence.json` at `13753c13` (`66eb8bd4…`).

Custody:
- The sealed originals remain read-only in the role's private WP-0044 scratch directory, together with `freeze-log.json`, the extracted reference checks and the clean-export reproduction.
- No authentication material exists. The nonce is a commitment-hiding constant only.
- No host path is committed apart from the historical argv strings already published in WP-0043.

Roles: eld-fixture-claude authored all fixture and oracle files and this report. eld-owner-probe and eld-rd-reviewer authored none of them, and I inspected none of their files, branches or results.
