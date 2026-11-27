# WP-0043 / 001: Independent CPU challenge suite, oracle and wire-v1 integration against stock candidate 6101a75d

- Report path: `docs/agent-reports/eld-fixture-claude/WP-0043/001_2026-11-27_research_eld-fixture-claude.md`
- Sequence reservation: INDEX.md WP-0043 table, slot 001 (reservation commit `d497bae7db42589bd2ede512f932b0488f6309cd`)
- Category: research
- Author / agent ID: eld-fixture-claude
- Actual model / effort: Claude Code CLI session `1177d67f-9d36-4f5c-b116-177da65cdc8d`. The environment exposes model ID `claude-opus-5-5` (Opus 5.5). The coordinator launch requested `claude-opus-5-5/high`; the effort level is not exposed to the session.
- Execution environment: Claude Code CLI on Windows 11, Git Bash. CPython 3.12.10, standard library only. CPU only.
- Published by: eld-fixture-claude (owned-branch push), unless the coordinator republishes this unchanged file with attribution
- Timestamp: 2026-11-27T01:54:00Z
- Repository / branch: jackgumpe/eledgercare, `research/wp-0043-fixtures` (worktree `w043-fixtures`)
- Base revision: `d497bae7db42589bd2ede512f932b0488f6309cd` (reservation; repository evidence base `e7c7c63fa8db0328881ec6aeb50cf5ecaff08f23`)
- Deliverable revision: `854a9470374301bc13844fb4a037ea265666e546`
- Previous report: none (first report in this packet for this author)
- Related or reviewed reports: candidate under test is eld-owner-probe's source `6101a75dc372fc6e2944b004343fa278d5d98907` (their WP-0043 / 002 has not been read). WP-0042 / 003 disposition and the accepted design `cd563dd06932a2cdecad4932b39d030efbe06699`.
- Status: ready-for-review
- Next owner: eld-rd-reviewer (WP-0043 / 003), then eld-coordinator (WP-0043 / 004)

## Summary

The question was whether an incorrect phase, support, ownership or continuation can pass a stock-observer recorder and its offline scorer. I wrote a 50-case CPU challenge suite and a separately coded oracle, and froze both before any candidate existed. I then froze a generic transport bridge and drove all 50 cases through the candidate's normal `stock.py capture` and `stock.py score` entries.

- 47 cases ran: every invocation exited 0 with empty stderr.
- 3 cases were rejected explicitly, each naming the operation the wire lacks.
- Transport was byte-exact on 47/47 against the frozen reference evidence (captured words per row and phase, selected ID, page states).
- Verdicts agree on 46/47. The one difference is a visibility gain for the candidate, not a candidate error.
- Strict atom-level agreement is 37/47 under the frozen comparer v2, and 42/47 under v2.1. v2.1 is a disclosed post-run fix that maps the candidate's `D_selection` field name.
- All 9 checkable ground word pairs agree in lane, dense offset, compact offset and both words.

This is author verification, not independent review. The CPU lane yields **zero native rows**, and the candidate's CPU capture **copies** the supplied public documents rather than executing a continuation.

## Objective and acceptance criteria

Authorized scope (assignment.md and the coordinator's dispatch to this session):
- Own `docs/fixtures/WP-0043`.
- Build the original six fixtures with all brief subcases, a pristine control, memo 4a/4b and 7a/7b/7c.
- Build an independent stdlib oracle; freeze inputs and oracle source, then freeze expected outputs, before any candidate exposure.
- Then build an integration bridge, freeze it, and run every frozen case through the owner's normal CLI without changing inputs or expectations.

Completion conditions:
- Frozen commits A, A′, B and C precede the run D.
- Every case is run or rejected explicitly.
- Semantic checks cover verdict, first phase or interval, retained missing and conflict atoms, word pairs, lanes, dense/compact offsets and diagnostic keys.
- Differences are classified separately from the agreement counts.

## What was measured

### Integration run on candidate 6101a75d (CPU analogue only)

Each run applies `python -B stock.py capture CASE.json`, then `python -B stock.py score EVIDENCE.json CONTRACT.json`. The commands run serially, with cwd set to a Git-object export of `docs/research/WP-0043/*` at `6101a75d`. The export holds 16 files; their blob IDs and SHA-256 values are in `integration/6101a75d/candidate-export.json`.

The 47 frozen cases yielded 71 rows, 210 phase records and 206 genuine copy events, with `native_rows_completed=0` and domain `cpu_analogue` in every result. Across all 50 invocations (47 frozen + 3 extras), capture time totalled 6.2 s and score time 6.8 s; the maxima were 0.31 s and 0.63 s.

| Outcome | Count |
| --- | --- |
| Verdict pairs, oracle→candidate | M→M 27, P→P 14, U→U 5, P→M 1 |
| First discrepancy | exact 31, within the oracle interval 1 (F4.b), n/a (both P) 14, candidate only 1 (F4.c) |
| Strict semantic agreement, v2 frozen / v2.1 | 37 / 42 of 47 |
| Ground word-pair checks (true word vs captured word) | 9/9 equal in lane, dense and compact offset, and both little-endian words |
| Rejected before execution | 3 |

### Discrimination on the required cases

Byte details give phase, ID, lane, dense offset d = 4·id + lane, compact offset c, and the expected→observed little-endian word.

| Case | Oracle | Candidate | Candidate first (row/phase/key) | Byte detail |
| --- | --- | --- | --- | --- |
| F1 pristine / F6 owned / F7a valid / F7b out, in, prompt / F7c −0 pass | P | P | — | — |
| F1 late raw hook (also native size 129,280) | M | M | 0/C0_raw/phase_cut_binding_mismatch | C0 id 7, lane 2, d 30, c 10, `00001041`→`000080ff` |
| F1 all hooks late | M | M | 0/C0_raw/phase_cut_binding_mismatch | same as above, plus a C1 cut mismatch |
| F2 forced but forbidden | M | M | 0/C2/empty_support | — |
| F3 tie, last maximum | M | M | 0/D_selection/firstmax_tie_violation | selected 8, first max 6 |
| F3 losing-zero sign flip | M | M | 0/C2/signed_zero_corrupted | C2 id 7, lane 3, d 31, c 15, `00000000`→`00000080` |
| F4a inverted ancestry | M | M | 0/C0/phase_cut_binding_mismatch | — |
| F4b duplicate copy | M | M | 0/C0/duplicate_copy_event_id | — |
| F4c late hook, inactive guard | **P** | **M** | 0/C0/phase_cut_binding_mismatch | bytes identical |
| F4e drop zN / F4h false complete / F4i missing + short | U / M / M | U / M / M | C1 phase_missing / C0 complete_length_mismatch / C2 complete_length_mismatch | — |
| F5 later ID / terminal reason / interrupted after field | M / M / U | M / M / U | public_id_mismatch / terminal_mismatch / public_ids_missing | — |
| F6 alias at end of step | M | M | 0/C0/phase_cut_binding_mismatch | C0 id 1 (EOS), lane 2, d 6, c 6, `00000041`→`000080ff` |
| F6 zN alias late | M | M | 0/C1/phase_cut_binding_mismatch | C1 id 1, lane 2, d 6, c 6 |
| F7a cursor reset, recorded | M | M | 1/B1_entry_state/saved_cursor_mismatch | C2 id 1, lane 2, d 6, c 2, `000080ff`→`00001041` |
| F7a cursor reset, unrecorded | M | M | 1/C2/page_state_mismatch (+ missing `saved_cursor_mismatch_missing` at B1) | as above |
| F7a guard re-invocation | M | M | 1/C2/guard_invocation_count | — |
| F7b window −1 / +1 / prompt included | M | M | 0/C1/post_rep_word_mismatch | C1 id 7, lane 2, d 30, c 10 |
| F7c +inf raw | M | M | 0/C0/raw_non_finite_pos_inf | observed `0000807f` |
| F7c −0 canonicalised | M | M | 0/C2/signed_zero_winner_corrupted | C2 id 0, lane 3, d 3, c 3, `00000080`→`00000000` |
| F7c pick last tied zero | M | M | 0/D_selection/firstmax_tie_violation | — |

Full per-case data are in `integration/6101a75d/discrimination.json` and `semantic-v2.1.jsonl`.

### Residuals and their classes (separate from the agreement counts)

1. **F4.c_late_hook_inactive, P→M: visibility.** The moved hook produces a genuine copy event at the C1 instruction offset, and the candidate binds each record to its event offset. The frozen oracle's evidence model carried only self-declared labels, and the bytes are identical, so it scored P. This is the memo's "False Pass A". The candidate's genuine event ledger closes it on the CPU analogue.
2. **F4.b: preserved memo disagreement.**
   - The candidate reports exactly the memo's keys {duplicate_copy_event_id, phase_cut_binding_mismatch}, with first phase C0.
   - The frozen oracle also reports non-strict `event_seq` order (C0 = C1 = 1) and the first interval C0..C1.
   - The candidate's first phase lies inside that interval. The candidate deliberately skips the order test for a single shared copy.
   - The oracle row is unchanged; the extra atom is listed as "oracle atom without candidate counterpart".
3. **F7a.reset_unrecorded: preserved memo disagreement, and candidate agrees with the oracle.** The memo expects the first divergence at the row-1 entry state. With the cursor absent from the record, both the oracle and the candidate report the entry field as missing at B1 and the first conflict at C2 row 1.
4. **F2.forced_banned: candidate omits one atom.** The candidate reports `empty_support` (M), but no y-not-in-support atom when the support is empty. Its check is `elif allowed and y not in allowed`. The verdict is unaffected.
5. **F7b.out_window_minus1 and F7b.prompt_included: oracle extension atom.**
   - The oracle's composition check (z against r on the allowed set, companion Eq. 4.2) fires at C2 slot 7, because z = −inf where r = 9.0.
   - The candidate compares C2 only with C1 while zN is present, and reports `allowed_non_finite` there instead.
   - When zN is absent (F4.j), the candidate does fall back to the raw capture, and agrees.
6. **Plausible extra candidate diagnostics, disclosed and not counted as disagreements.**
   - Event-receipt visibility: 8 extra keys plus 2 extra conflicts, such as `phase_cut_binding_mismatch` on moved hooks, plus `fragmented_capture` and `copy_event_invalid` on F4.g's torn substitution.
   - Raw-reference visibility: 6 `raw_word_mismatch` entries. The candidate scorer receives the true raw words through `contract.raw_words`; the frozen oracle deliberately did not.
   - One extra missing entry: `public_ids_missing` alongside the F5 token conflict.
7. **Unchecked observable details: 17.** These are listed explicitly in v2.1:
   - 7 C0 raw-finiteness lanes, where the oracle had no reference word;
   - 5 C2 allowed-finite lanes, where the oracle had no reference word;
   - 5 C2 `observed_le` values, which the candidate does not report for `allowed_non_finite`.
   - Where the ground word pair exists, the candidate's `raw_word_mismatch` lanes were checked against it instead (9/9).

### Rejected cases (wire-v1 lacks a neutral operation)

The coordinator was notified in `bridge-needs.txt` before the run.

| Case | Oracle | Reason | Needed op |
| --- | --- | --- | --- |
| F6.torn_raw | M | The raw copy reads ID 7 before both writers and every other slot after them. `torn` supports only a byte prefix/suffix split, and EOS slot 1 precedes ID 7 in compact order. | Torn/read by explicit token-ID set or multiple byte ranges (capture-only) |
| F5.interrupt_in_field | U | The run is interrupted after row 2; the wire always captures every contract row. | `omit_row` (capture-only) |
| F1.recompute_forged | P (oracle blind spot) | Native-looking distinct receipts for synthesised bytes. | None: outside the candidate's genuine-event design. Extra variant `X.F1.recompute_raw_ancestry` (synthesised bytes claiming the C0 receipt) scores M with duplicate_copy_event_id, capture_payload_mismatch and phase_cut_binding_mismatch. |

The other extras are not scored against frozen rows:
- `X.F6.alias_end.view` scores M with owned_copy_violation, capture_payload_mismatch, raw_non_finite and raw_word_mismatch.
- `X.F6.zN_alias_late.view` scores M with owned_copy_violation, capture_payload_mismatch and post_rep_word_mismatch.

### Fixture 5 continuation: copied, not executed

Wire v1 places the untouched document in `contract.document` and the observed document in `CASE.document`. The bridge supplies both from the frozen reference recorder's trajectories, and the candidate's CPU capture writes `CASE.document` verbatim into its evidence (verified equal in 5/5 F5 cases). F5 therefore tests the scorer's public/terminal comparison on simulated documents; nothing measures a native continuation. The same holds for every other case's document. The candidate executes only the scheduled rows: head words, both stock guard functions and selection.

## Change inventory

The base-to-deliverable diff `d497bae7..854a9470` contains 245 paths, all under `docs/fixtures/WP-0043/`.

| Action | Path | What and why | Commit |
| --- | --- | --- | --- |
| Added | `.gitattributes`, `README.md` | Exact bytes (`-text`); suite, schema and freeze protocol | A `36aea189e8adf5e5a8c076c0f5aade179c1f4727` |
| Added | `build_fixtures.py` | Generator and reference recorder, mirroring native lines 1166–1182, 583–605 and 608–623 | A |
| Added | `oracle.py` | Independent oracle and evidence-only reference scorer; first-run classification correction in A′ | A, A′ `609d7f06499dfd4de505c8bde61cfae2c907974b` |
| Added | `compare.py` | v1 stable-key comparer (unchanged since A) | A |
| Added | `generated/cases.jsonl`, `generated/manifest.json`, plus 45 `blobs`, 50 `contracts`, 50 `evidence` and 24 `inputs` files | The 50 frozen cases and their bytes; the manifest gives size and SHA-256 per file | A |
| Added | `expected/expected.jsonl`, `facts.json`, `oracle-run.json`, `oracle-stdout.txt`, `oracle-stderr.txt` | Frozen expectations (`bdf3e252…a559b`), run record | B `3f7a53cbf971eb8434507ef3622eb5d089c5de57` |
| Added | `bridge/bridge.py`, `bridge/semantic_compare.py`, `bridge/crosswalk-v1.json`, `bridge/README.md`, `bridge/plan-transport.jsonl` | Wire-v1 transport, v2 comparer, crosswalk, frozen plan | C `772e3d95334dbad4404d0b3e32d1630348dc5b30` |
| Modified | `bridge/semantic_compare.py` | Post-run only: `--version 2.1` (default v2 unchanged) and deterministic ordering of mapped positions | D `854a9470374301bc13844fb4a037ea265666e546` |
| Added | `integration/6101a75d/` (59 files) | transport/run/fidelity records, v2 and v2.1 outputs and summaries, candidate export record, digest manifest of all scratch outputs, discrimination table, 48 non-dense candidate `result.json` files | D |

This report is committed separately, after D. No INDEX.md, CURRENT.md or other owner's path was written.

External effects: pushes of the owned branch to `origin`, without force. Private scratch is `C:/Users/jackg/eLedgerCare-Speed/WP-0043/fixtures/scratch/`; it holds the CASE, contract and evidence files, including about 2–4 MB per dense case, bound by digest in `scratch-outputs-manifest.json`. There were no GPU, model, device, network-service, profile or configuration changes.

## Decisions and rationale

- **Independence.**
  - The oracle shares no code with the generator. The oracle works on integer bit patterns with set-algebra masks; the generator mirrors native code operationally.
  - The bridge never opens `expected/`. Expectations were read only by `semantic_compare.py`, after `run` and `fidelity` had written the candidate outputs.
  - I read the candidate's `wire.md`, `stock.py`, `capture.py`, `analogue.py`, `analogue_guards.py`, `scorer.py` and README at `6101a75d` *after* freeze B and *before* freeze C, to pin wire semantics that the specification leaves implicit. This informed the transport mapping only.
- **Transport rules (generic, by injection type).** Copy schedules map to `capture_at`/`torn` at the real instruction cuts, keeping owned copies and genuine events. No witness flag is ever set. Substitutions are allowed only when the recorded words stay byte-identical, they are disclosed per case, and the post-run fidelity step verifies them (47/47 exact). The three byte-equivalent substitutions:
  - F4.g torn split;
  - identity swap of equal bytes (F4.c swap, F4.d);
  - live write before the final copy in place of a recorder edit (F3.zero_flip, F4.j, F7c canonicalised), with selection verified unchanged.

  Memo 4b's C2 relabel equals the genuine ledger count. The candidate's page-state priming (one stock guard call over the unobserved prefix) gives the same state as the oracle's per-step replay.
- **Comparer versions.** v2 was frozen in C. After the run, v2 turned out to look for the selected ID in field `id`, while the candidate names it `observed` for `D_selection`. v2.1 adds only that mapping and a census of unchecked details. Both runs are published. The default v2 output also changed serialization order between processes, because of set iteration under hash randomization; content was identical after normalisation. The position list is now sorted, and two runs of each version are byte-identical.
- **Byte-lane erratum (for frozen B and v1 `compare.py`).**
  - For a non-finite observed word, the oracle's `dense_token_offset_candidates` [4·id+2, 4·id+3] mark the exponent lanes where any finite word *must* differ.
  - They do not bound the *first* differing lane, which against an unknown finite word can be any of 0–3 (dense 4·id … 4·id+3). v1 `compare.py` wrongly treated them as first-lane candidates.
  - v2 instead checks the candidate's lanes against the frozen ground-truth word pair when one exists, and marks the detail unchecked otherwise. `facts.json` itself states this correctly. Frozen B is unchanged.

## Verification

| Check / exact command | Environment and revision | Result | Evidence |
| --- | --- | --- | --- |
| `python -I build_fixtures.py` twice; `--check` | CPython 3.12.10, A | Identical manifests; 170 files, 0 problems | `generated/manifest.json` |
| `python -I oracle.py expect --native-source <pinned modeling_unlimitedocr.py>` | A (first run) | 50 cases, 0 consistency failures; `F6.owned` misclassified | private scratch run1 (superseded) |
| Same command | A′ | exit 0, empty stderr; M 28, U 6, P 16; 43 claims held, 2 disclosed not held; native SHA-256 `f6df813c…f39f1f` matches the pin (hashed, never imported) | `expected/oracle-run.json` |
| Oracle reference scorer on the frozen reference evidence → `compare.py --strict-detail` | B | 50/50 agree; negative control flagged 2/2 mutations (exit 1) | private scratch selfcheck1 |
| `bridge.py plan` twice, and at run time | C | Deterministic; equal to the frozen `plan-transport.jsonl`; 47 planned, 3 rejected, 3 extras | `bridge/plan-transport.jsonl` |
| `bridge.py run --candidate-dir <export of 6101a75d>` | C bridge, candidate `6101a75d`, CPython 3.12.10 | 50 invocations (47 + 3 extras): all capture and score exit 0, empty stderr | `integration/6101a75d/run.jsonl`, `run-meta.json` |
| `bridge.py fidelity` | same | 47/47 exact (bytes per row/phase, y, before/after states) | `fidelity.jsonl` |
| `semantic_compare.py` (v2), twice | D comparer | verdicts equal 46, semantic agreement 37/47, byte-identical repeats | `semantic-v2*.json*` |
| `semantic_compare.py --version 2.1`, twice | D comparer | semantic agreement 42/47, 17 unchecked details listed, byte-identical repeats | `semantic-v2.1*.json*` |

Not run:
- Any native, GPU or model execution. This is outside the CPU lane; no lease was held.
- The candidate's `plan`, `run` and `score-native` entries, which are out of scope.
- `check_resources.py` and `archive.py`, which are not part of this interface.
- Independent review, which belongs to eld-rd-reviewer.

## Review map

- **Suite and oracle:** `docs/fixtures/WP-0043/README.md`, `build_fixtures.py` (`run_arm`, `page_guard`, `no_repeat`, `catalogue`) and `oracle.py` (`simulate`, `predict`, `RefScorer.score`, `ground`, `claims_for`, `global_facts`).
- **Expectations:** `expected/expected.jsonl` and `facts.json` (memo claims and disagreements in `claims` and `summary.claims.not_held`).
- **Bridge:** `bridge/bridge.py` (`plan_case`, `map_phase`, `EXTRAS`) and `bridge/crosswalk-v1.json`.
- **Comparison:** `bridge/semantic_compare.py` (`compare_case`), and `integration/6101a75d/semantic-v2.1.jsonl` with the per-case `differences`, `conflict_atoms`, `missing_atoms`, `ground_pair_check` and `unchecked_observables`.
- **Candidate outputs:** `integration/6101a75d/results/*.json`. The digests of every scratch file (CASE, contract, evidence, result, stderr) are in `scratch-outputs-manifest.json`.

## Risks, disagreements, and unfinished work

- **Scope of the evidence.**
  - This is a CPU analogue. It establishes behaviour of the candidate's normal CPU capture and scorer on constructed inputs. It establishes nothing about CUDA stream ordering, allocator perturbation, actual native cut offsets, tensor layouts, or the 0/5 native rows and 0/1 matched pairs, all of which remain unmeasured.
  - Continuation and public documents are supplied, not executed.
  - The candidate scorer's access to `contract.raw_words` is fine for a fixture, but there is no counterpart at native admission. The candidate's README says `score-native` does not accept user raw ground truth.
- **Memo disagreements preserved.**
  - 4b: the oracle has three conflicts and the C0..C1 interval. The memo and the candidate have two conflicts with first phase C0.
  - 7a with the cursor absent: the first conflict is at C2, with the B1 entry field missing, not at B1.
- **Open items for the candidate owner.** These are observations, not requests from this role:
  - The y-not-in-support atom is skipped when support is empty (F2).
  - The composition-vs-raw check is not applied while zN is present (F7b out −1 / prompt-included).
  - `allowed_non_finite` omits the observed word.
- **Open items for the coordinator.** Two neutral capture-only ops would let the 2 expressible rejected cases run: a set-based torn read, and `omit_row`.
- **Disclosures.** The oracle's first execution was corrected (A′) before expectations were frozen. Freeze B's commit message was amended once, before push, to correct counts; content was unchanged, and the superseded `ade78fdc` was never published.

## Handoff

Next action: eld-rd-reviewer independently reproduces the run on revision `854a9470374301bc13844fb4a037ea265666e546` with candidate `6101a75dc372fc6e2944b004343fa278d5d98907`, using the commands in `bridge/README.md` and a fresh Git-object export. The reviewer should check the transport rules, the crosswalk and the residual classes, and judge whether the 3 rejections and the visibility classification are acceptable.

For the coordinator:
- Deliverable: `854a9470374301bc13844fb4a037ea265666e546`.
- Branch: `research/wp-0043-fixtures`.
- Report path: as above. Its publication SHA follows in the handoff message.
- Freeze chain: A `36aea189`, A′ `609d7f06`, B `3f7a53cb`, C `772e3d95`, D `854a9470`.

Publication receipt: the branch is pushed without force and the remote head is verified after each push. Remote confirmation of the report commit is given in the handoff message.
