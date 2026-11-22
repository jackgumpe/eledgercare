# WP-0027 / 001 — Owner rankings on calibration twins

| Publication metadata | Value |
| --- | --- |
| Report path | `docs/agent-reports/eld-rank-author/WP-0027/001_2026-11-22_research_eld-rank-author.md` |
| Reservation | [WP-0027 / 001](https://github.com/jackgumpe/eledgercare/blob/ce04b773329c3c67cd0ab4b578ddf442690019a0/INDEX.md#wp-0027-twin-binder-cpu-diagnosis) |
| Category and author | Research, `eld-rank-author`, also publisher |
| Actual session | Native Codex subagent `/root/w27_rank`, GPT-6-based environment. Requested xhigh. Exact backend ID, session UUID and realized effort unexposed. |
| Environment | Windows PowerShell, Q0 CPython 3.12.10, PyTorch 2.13.0+cu130, CPU FP32, one thread |
| Timestamp | 2026-11-22T06:28:42Z |
| Repository, branch and worktree | Private `jackgumpe/eledgercare`, `research/wp-0027-owner-ranking`, `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w027-rank` |
| Base | `ce04b773329c3c67cd0ab4b578ddf442690019a0` |
| Frozen source | `aa3ecc3b04dada439529621cdfa93f8f8cf581e5` |
| Source and evidence deliverable | `0573f69c481eea2e815899e00ddd5e68bb4e3c42` |
| Related evidence | [WP-0026 / 003](https://github.com/jackgumpe/eledgercare/blob/e9e24e5ea2730358fb67cfe269049a66a92ce8a5/docs/agent-reports/eld-rd-reviewer/WP-0026/003_2026-11-21_review_eld-rd-reviewer.md). This is the first report by this author. |
| Status and next owner | Ready for review by `eld-rd-reviewer` in WP-0027 / 003 |

## Findings

**Neither arm ranked the correct owner first in both members of any answerable pair.** Each kept the same leader across both twins in all eight pairs. M1 chose Cedar on all four T1/T2 pairs and Alder on all four T3 pairs. M3 chose Alder on all eight. The official selected setting abstained on all 20 binders in each arm and correctly scored both ambiguous pairs, yielding 2/10 correct pairs. All 48 original grid cells reproduced. [Binder and pair evidence](https://github.com/jackgumpe/eledgercare/blob/0573f69c481eea2e815899e00ddd5e68bb4e3c42/docs/research/WP-0027/owners/owner-rankings.json)

| Per-arm outcome | M1 | M3 |
| --- | ---: | ---: |
| Both owner deltas positive | 0/8 | 0/8 |
| Exactly one positive | 8/8 | 8/8 |
| Neither positive | 0/8 | 0/8 |
| Wrong-way final flip | 0/8 | 0/8 |
| Exact top tie, zero owner read, unscorable answerable pair | 0, 0, 0 of 8 | 0, 0, 0 of 8 |
| Correct individual owner leaders | 8/16 | 8/16 |
| Answerable members with one target, both owners available | 16/16 | 16/16 |
| Answerable members with zero or multiple targets or scope-suppressed attempts | 0, 0, 0 of 16 | 0, 0, 0 of 16 |
| Separate ambiguous controls correctly withheld | 2/2 pairs, 4/4 binders | 2/2 pairs, 4/4 binders |

All ten pairs matched on final archived metadata, loaded spans, ordered source RGB commitments and pooled feature bytes. Each answerable target had the same two eligible normalized owner values in both twins. Every pair also had matching final unit, column and subtotal candidate sets. The truth file keys bind each pair to its two binder IDs and their separate target IDs. The evidence records raw candidate spelling, normalized identity, score, top two, tie, gap, actual read norm, selected gates, raw attempt and binder decision. A subtotal appears only on the eight summary targets per arm. [Exact keyed rows](https://github.com/jackgumpe/eledgercare/blob/0573f69c481eea2e815899e00ddd5e68bb4e3c42/docs/research/WP-0027/owners/owner-rankings.json)

For each binder, Δ is its true owner's score minus the best other eligible score. In this two-owner corpus, adding both Δs gives the Alder-minus-Cedar preference on the Alder binder minus that preference on the Cedar binder. This difference was positive on **8/8 pairs in both arms**, ranging from +0.003329 to +0.011484 for M1 and +0.000133 to +0.028647 for M3. Relative preference therefore moved in the expected direction even where the top name stayed fixed. The twins also vary in other earlier cues.

| Pair prefix | Windows, stratum | True owners in displayed binder order | M1 Δ₁, Δ₂ | M3 Δ₁, Δ₂ |
| --- | --- | --- | --- | --- |
| 03fe821e | 4, T2 | Cedar, Alder | +0.070733, −0.064991 | −0.102885, +0.103018 |
| 388abc9b | 4, T1 | Alder, Cedar | −0.062611, +0.073161 | +0.100969, −0.099109 |
| 42fd7bde | 10, T3 | Alder, Cedar | +0.029984, −0.020156 | +0.150287, −0.121640 |
| 48a273e0 | 4, T3 | Alder, Cedar | +0.024622, −0.015331 | +0.152444, −0.126922 |
| 770f5bcd | 10, T1 | Cedar, Alder | +0.054975, −0.047820 | −0.099109, +0.100969 |
| 9b2cde90 | 10, T2 | Alder, Cedar | −0.051352, +0.054681 | +0.103018, −0.102885 |
| e590859b | 4, T3 | Alder, Cedar | +0.020980, −0.009496 | +0.150287, −0.121640 |
| efb10894 | 10, T3 | Alder, Cedar | +0.033439, −0.025268 | +0.152444, −0.126922 |

The displayed order is ascending binder ID within the released pair. Prefixes abbreviate unique full keys in the JSON. Both Δ values were derived by joining the target and true candidate to its score by normalized value.

## How whole postings failed

At the selected similarity of 1.0 and margin of 0.10, all 16 answerable members in each arm reached a single target and returned `below_threshold_owner`, the first field gate. Owner maximum scores ranged from 0.02581 to 0.11092 for M1 and 0.13262 to 0.16392 for M3. The owner margin passed on 0/16 M1 and 14/16 M3. Even every correct owner leader fell below the similarity gate. Examining each field independently, both arms ranked 8/16 units, 8/16 columns and 4/8 applicable subtotal statuses correctly. Each of the eight ordinary postings had an inapplicable subtotal with expected value null. [Raw field decisions](https://github.com/jackgumpe/eledgercare/blob/0573f69c481eea2e815899e00ddd5e68bb4e3c42/docs/research/WP-0027/owners/owner-rankings.json)

| Frozen posting-producing cell | Answerable postings | Full posting correct | Owner errors | Unit errors | Column errors | Subtotal errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| M1 (−0.25, 0) | 16 | 0 | 8 | 8 | 8 | 4 |
| M1 (0, 0) | 8 | 0 | 4 | 4 | 4 | 0 |
| M3 (−0.25, 0) | 16 | 0 | 8 | 8 | 8 | 4 |

Counts overlap across fields. At (−0.25, 0), each arm made **eight silent errors with the correct owner**. Exactly one other field failed in each such posting, with four column, two unit and two subtotal errors. The other eight errors combined wrong owner with wrong column (two), wrong unit (four), or all four wrong fields (two). At M1 (0, 0), two of the four correct-owner errors were column errors and two were unit errors. These are pre-existing grid cells. The selected cuts were unchanged.

Three target-level witnesses at (−0.25, 0) identify how the source cue, controller and original readouts relate. Both field choices were eligible in each example. Further binder and candidate details appear in the [score table](https://github.com/jackgumpe/eledgercare/blob/0573f69c481eea2e815899e00ddd5e68bb4e3c42/docs/research/WP-0027/owners/owner-rankings.json) and [cue trace](https://github.com/jackgumpe/eledgercare/blob/0573f69c481eea2e815899e00ddd5e68bb4e3c42/docs/research/WP-0027/owners/owner-progression.json).

- **Column.** Binder `005b87b4`, target `acb84cd9`, registered the parent header `Item Amount Ref` in W1 and returned to depth 0 in W9. The target `MAINT-SUMMARY 670 670` in W10 needed Amount. M1 scored Amount −0.06705 and Ref +0.13190 with read norm 3.69992. M3 scored −0.14100 and +0.40825 with read norm 2.15449. Both posted Ref alongside correct Alder, Unit3 and UNBALANCED.
- **Unit.** M3 binder `1a1eb21d`, target `e9545ba9`, read `Unit: Unit3` in W1 followed by `Unit amendment: Unit9` at depth 0 in W2. The child closed in W3. At its W4 ordinary target the read norm was 4.55214, Unit3 scored −0.00792 and Unit9 −0.01940. Owner, column and null subtotal were correct. M1 also made a unit-only error on binder `2badf5ea`, which declared Unit9 in W1. At its W10 target M1 scored Unit3 +0.05433 and Unit9 +0.05174.
- **Subtotal.** Binder `222a29c0`, target `c21d2e5d`, had a W9 child subtotal of 670, `Schedule closed` returning to depth 0, and W10 `MAINT-SUMMARY 670 670`. BALANCED was required. M1 scored BALANCED −0.14660 and UNBALANCED −0.14085 with read norm 2.54875. M3 scored +0.16467 and +0.16666 with read norm 2.94668. Both posted UNBALANCED alongside correct Alder, Unit3 and Ref.

## Where the owner rankings diverged from the cues

Each answerable binder had a distinct, correctly recognized parent ledger literal. Each twin registry exposed both names as candidates. The registry stores an unordered set of eligible owners. Its API carries no active-owner value. The controller tracks scope depth, pending closure and faults. The owner association must survive the matrix writes and be expressed by the frozen read and anchor scores. All 16 answerable binders in each arm reached their target at depth 0 with a nonzero actual owner read. [Frozen model and controller](https://github.com/jackgumpe/eledgercare/tree/7db67283a4ffd3e7a20bb8d80499572cc7118c71/docs/research/WP-0024/probe)

The checkpoints apply each binder's own eventual target query to its actual matrices at the recorded scope depth. This retrospective read never updates state. The target measurement is from before the target write and agrees with the original scoring read. The differing states and read vectors below establish numerical sensitivity. Their meaning is tested by the named owner scores. Scores are rounded here, and the machine trace retains the float values and all sampled checkpoints. [Paired numerical progression](https://github.com/jackgumpe/eledgercare/blob/0573f69c481eea2e815899e00ddd5e68bb4e3c42/docs/research/WP-0027/owners/owner-progression.json)

| Witness and frozen read | Immediately after the distinct ledger write | W1 end | Actual final target |
| --- | --- | --- | --- |
| T1 pair `388abc9b`, M1. Binder `366ef9f7` needs Alder and `92222f3f` needs Cedar. | Before the write both favored Alder. Afterward both favored Cedar. Scores (Alder, Cedar) were (−0.04524, +0.01451) and (+0.02743, +0.06537). | Both Cedar. Owner-read L2 difference 0.48476. | After the child closed, scores were (−0.03490, +0.02772) and (−0.04146, +0.03170). Δ −0.06261, +0.07316. Across the twins, owner-column L2 difference 1.06958 and owner-read L2 difference 0.40766. |
| Same T1 pair, M3 | Both favored Alder before the write. Immediately after it, the Alder binder favored Cedar (+0.14161, +0.14292), and the Cedar binder favored Alder (+0.12412, +0.10812). This early flip was wrong in both twins and appeared in all four T1/T2 pairs. | Both Alder. Owner-read L2 difference 0.19198. | Scores (+0.13413, +0.03316) and (+0.13262, +0.03351). Δ +0.10097, −0.09911. Owner-column L2 difference 0.84199 and read L2 difference 0.15220. |
| T3 pair `48a273e0`, M1. Binder `022d55c2` needs Alder and `90906d89` needs Cedar. | Both favored Alder (+0.09217, +0.07501) and (+0.20780, +0.14403). | Both Cedar. | Both Alder at the summary target, after returning to depth 0. Scores (+0.07877, +0.05415), (+0.09334, +0.07801). Δ +0.02462, −0.01533. Owner-read L2 difference 0.79180. |
| Same T3 pair, M3 | Both favored Alder (+0.10542, +0.02255) and (+0.17694, +0.12545). | Both Alder. | Both Alder (+0.14193, −0.01051), (+0.16392, +0.03700). Δ +0.15244, −0.12692. Owner-read L2 difference 0.60332. |

The first sampled read after the distinguishing ledger write already failed to rank both owners correctly on every pair. At W1 end both probes had a common leader within every pair. Distinct cue text, state differences and correctly directed small final score changes coexist with that failure. The checkpoints cannot isolate the causal contribution of owner, unit or schema, or rule out owner information retrievable by another readout.

**Ambiguous controls.** Pairs `57e6cb6c` and `bb6c71d5` all route to final calibration window `k0028`. Both earlier ledger literals were recognized, the directories supplied both names and the child remained open. In the final archive page 2 has a table-kind block at span 2 with an unfinished HTML table, followed by text blocks at spans 3–5 containing Posting, 242 and 852. All eight spans are blocks with empty cell arrays. The frozen grammar emits TARGET only from eligible rows. There was consequently no attempt, target query, scored candidate or field threshold for any of these four members. `single([])` returned `no_target`. These four correct abstentions cannot demonstrate that the probe assessed semantic ambiguity. The final metadata SHA-256 is `6a7d3f94cb9337663644fca8c0356a9c12f6a1c602fab8a86795cf6daa793233`. [Archived physical members](https://github.com/jackgumpe/eledgercare/tree/1f246c71378e973e23ebeabfeb7fda56a8ccca2b/docs/reviews/WP-0026/cal-features-primary)

## Verification, inventory and handoff

The authorized objective was to reproduce the two original calibration grids and distinguish owner rankings, field failures, typing and missing preconditions using calibration alone. The launcher read pinned Git blobs, verified each of 29 physical calibration metadata and pool members against both the inventory and its individual receipt, and routed 140 logical appearances. It loaded the released calibration truth sidecar and exact fitted weight bytes. There was no refit. `run.calibrate` provided the official grid. A second pass compared original and instrumented final matrices, attempts, scores and all 24 decisions per binder. Stable pair, binder, target and normalized candidate keys identify all reported quantities. [Source diff](https://github.com/jackgumpe/eledgercare/compare/ce04b773329c3c67cd0ab4b578ddf442690019a0...aa3ecc3b04dada439529621cdfa93f8f8cf581e5)

The exact decisive command from the owned worktree was:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File docs/research/WP-0027/owners/run.ps1 -Role owners -RunName replay-1
```

The launcher invoked the following process, with per-run TEMP, TMP and cache directories, GPU hidden and offline settings already in its environment:

```powershell
& 'C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe' -I -B 'C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w027-rank/docs/research/WP-0027/owners/replay.py' 'C:/Users/jackg/eLedgerCare-Speed/WP-0027/owners/replay-1'
```

Exit 0. The process reported zero visible CUDA devices and one CPU thread. Both the original and observational passes, including input preparation and table writes, took 7.894 seconds in the replay; the arm-specific portions took 1.287 seconds for M1 and 1.294 for M3. Interpreter SHA-256 `0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14`. The Windows venv launcher reports its venv path in `sys.executable` and its underlying Python path in `sys.orig_argv`. [Runtime receipt](https://github.com/jackgumpe/eledgercare/blob/0573f69c481eea2e815899e00ddd5e68bb4e3c42/docs/research/WP-0027/owners/runtime.json)

| Input or result | SHA-256 |
| --- | --- |
| Archived calibration ZIP | `e708b33aa56fbcb78ceae2e3c59a795482d9a8f09bd6796b5d5291969540b46d` |
| Calibration transport | `7eff4a5909b201d889406fb440a38b3e4e44181a597e0c81ea6fc05f59ced069` |
| Released calibration labels | `a227da1293bcd6f8b0f636ce3349abd12d02a52361a46b47dbf34969cc773ff1` |
| Frozen fit receipt | `e664109765b0482cb7d330c825c4c9dbbe3b8b8c63e17a991fe6ab14f42925b2` |
| M1 / M3 weights | `e2420949c0990992fae61b42280617bedd95dfa7013ce25ff52c8fd760c0f291` / `391b19e5629faf62b2f6ae6614bd18f91ba8e7c112a78dc191cdd6e602d10031` |
| Independent 48-cell reference | `0ed4002a3f0d8a0a761e0ed71a57e7a75feb70fda37bd3c4ea02bfb0e927bdb7` |
| Ranking / progression tables | `c43be2f4e02789743b1f5b02ed91be1d6614cb6d618fd0ce791a9de477e20a5a` / `38d782fb3c57cc009d7d29dd3a8d5fa66f48a191f2657548fc97f5e6fc3cc11c` |
| Runtime receipt | `746ccd90f9878af3df2f63488e0f463232f3f94719f832f2e66578dbbdc80d8f` |

The ranking table's `input_sha256` contains the full original probe blob digests and `physical_windows` contains each of the 29 verified receipts, metadata, pools and ordered source commitments. The original file routes and reference grid are pinned independently. [Weights and transport](https://github.com/jackgumpe/eledgercare/tree/6d79c24364ba10a1d9bfa4c72c837e2f216cf4bc/docs/research/WP-0026/fit) · [48-cell reference](https://github.com/jackgumpe/eledgercare/blob/b0d2dc9efee1ef27cf47e2929c05e8fbfde2fde0/docs/reviews/WP-0026/calibration-independent.json)

| Added path under `docs/research/WP-0027/owners/` | Change |
| --- | --- |
| `run.ps1` | Starts the Q0 Python subprocess with CPU/offline and writable scratch settings |
| `inputs.py` | Reads exact Git objects, validates identities and materializes the calibration-only archive members |
| `observe.py` | Observes calls to the original recurrence and readouts, checks observer parity and pairs numerical checkpoints |
| `ranking.py` | Derives per-field margins, keyed pair outcomes and full typed posting error counts |
| `replay.py` | Runs the published calibration algorithm and the separate observational replay |
| `owner-rankings.json` | Reproducible table of keyed scores, decisions, candidate availability, pair results and input hashes |
| `owner-progression.json` | Original cue stream, checkpoint scores, matrices/readout differences and controller/registry observations |
| `runtime.json` | Candidate, commands, environment, timing and output digests |

The canonical report at the reserved path is the only subsequent metadata file. External writes were the owned `WP-0027/owners/source-check` syntax-check scratch and `WP-0027/owners/replay-1` materializations/caches, plus normal pushes to the owned branch. The author verified the remote evidence head using `git ls-remote origin refs/heads/research/wp-0027-owner-ranking`. No held-out evaluation, OCR, GPU test, donor intervention, training, product check or architectural treatment ran in this calibration assignment.

**Remaining question.** In a separately authorized test, vary only the parent ledger literal while holding directory, unit, schema and suffix fixed. For each pair, compare the frozen Alder-minus-Cedar margin immediately after the cue, at W1 end and at the target. The within-pair mean gives the common preference and the half-difference gives the effect of the controlled owner edit. Persistence of a correctly signed effect smaller than the common preference would locate the failure at the final choice. An early effect disappearing before the target would bound the loss interval for this read. The current observations do not resolve those alternatives.

**Handoff.** `eld-rd-reviewer` should independently reconstruct the pair deltas, verify the controls and grids, and replay the source and decisive progression witnesses. The coordinator records the publication receipt and the independent disposition separately. [Deliverable](https://github.com/jackgumpe/eledgercare/tree/0573f69c481eea2e815899e00ddd5e68bb4e3c42/docs/research/WP-0027/owners)
