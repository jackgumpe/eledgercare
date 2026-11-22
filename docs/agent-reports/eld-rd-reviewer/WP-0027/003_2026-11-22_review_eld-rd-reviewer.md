# WP-0027 /003 · Independent calibration and terminal-reader review

| Publication field | Record |
| --- | --- |
| Report | `docs/agent-reports/eld-rd-reviewer/WP-0027/003_2026-11-22_review_eld-rd-reviewer.md` |
| Author and publisher | `eld-rd-reviewer`, fresh native Codex session `/root/w27_review`, independent of both authors, their source, the coordinator's input constructor and all predecessor work |
| Runtime and model | Windows PowerShell, Q0 CPython 3.12.10, PyTorch 2.13.0+cu130 running on CPU. Session requested xhigh. Exact serving model and effective effort are unexposed. |
| Repository and branch | Private `jackgumpe/eledgercare`, `review/wp-0027-twin-cpu`, worktree `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w027-review` |
| Base and reservation | `ce04b773329c3c67cd0ab4b578ddf442690019a0`. [Independent /003 reservation](https://github.com/jackgumpe/eledgercare/blob/ce04b773329c3c67cd0ab4b578ddf442690019a0/INDEX.md#wp-0027-twin-binder-cpu-diagnosis) |
| Category, previous report and next owner | Independent review. First report of this session. Next owner is `eld-coordinator` for /004. |
| Rank candidate / evidence / author publication | `aa3ecc3b04dada439529621cdfa93f8f8cf581e5` / `0573f69c481eea2e815899e00ddd5e68bb4e3c42` / [WP-0027 /001](https://github.com/jackgumpe/eledgercare/blob/6f62c1196c33689ac7e640b2bb1e769fa106816c/docs/agent-reports/eld-rank-author/WP-0027/001_2026-11-22_research_eld-rank-author.md) |
| Original reader candidate / evidence / author publication | `67e0898e09ee9fc848677990850f9320a7d3cd6f` / `10f64a7e26e2e2477435a05543efbf647cefdff8` / [WP-0027 /002](https://github.com/jackgumpe/eledgercare/blob/20c4b5a6001eeded732dd70f381a4d4186346aa0/docs/agent-reports/eld-reader-author/WP-0027/002_2026-11-22_research_eld-reader-author.md) |
| Corrected reader candidate / evidence / author publication | `8bf8ec2c9eb6eff282366d61711ec1a249f4760a` / `b0a4d3a90a825a9a3f27d334ded2e11759edfd20` / [WP-0027 /005](https://github.com/jackgumpe/eledgercare/blob/8efbb5c6c0ce372fcb0b3a06df7a8461d951535d/docs/agent-reports/eld-reader-author/WP-0027/005_2026-11-22_research_eld-reader-author.md) |
| Reviewer deliverable / evidence | `4caffeff219665a4b28ee79020f3d73f7cd7485a` / `44572822207e10872c2daae4481468f4643b4f57`. [Base-to-deliverable inventory](https://github.com/jackgumpe/eledgercare/compare/ce04b773329c3c67cd0ab4b578ddf442690019a0...4caffeff219665a4b28ee79020f3d73f7cd7485a) |
| Status and time | **Accepted** for this CPU packet. 2026-11-22T06:38:53Z. |

**Independent disposition.** The frozen rank diagnosis reproduced. The first reader contradicted complete ordinary-page coverage on one executable control. The corrected reader withheld that exact record, reproduced k0014 and both archived valid controls, and matched every independent expectation. The held-out memory comparison remains unmeasured. [Same-input correction receipt](https://github.com/jackgumpe/eledgercare/blob/44572822207e10872c2daae4481468f4643b4f57/docs/reviews/WP-0027/correction-result.json)

## Calibration

**Neither probe ranked the correct owner first in both twins of any answerable pair.** Both registered a small relative score change toward the expected owner on all eight pairs. Neither crossed the decision boundary within a pair. M1 favored Cedar in all four T1/T2 pairs and Alder in the four T3 pairs. M3 favored Alder on every answerable binder.

| Independent measure per arm | M1 | M3 |
| --- | ---: | ---: |
| Official grid cells reproduced | 24/24 | 24/24 |
| Correct full pairs at selected similarity 1.0, margin 0.10 | 2/10 | 2/10 |
| Answerable pairs with both / exactly one / neither delta positive | 0 / 8 / 0 | 0 / 8 / 0 |
| Answerable binding or candidate exceptions, exact ties, wrong-way final flips | 0 | 0 |
| Individually correct owner / unit / column | 8/16 each | 8/16 each |
| Correct applicable subtotal, inapplicable subtotal | 4/8, 8 null | 4/8, 8 null |
| Selected answerable / ambiguous decisions | 16 below owner threshold, 4 lacked a target | 16 below owner threshold, 4 lacked a target |
| Increase in Alder-minus-Cedar preference on the true-Alder member | +0.003329 to +0.011484 | +0.000133 to +0.028647 |

I rebuilt every score from the frozen weights and original sensor inputs on CPU. The unique key was the truth pair, binder, target and normalized candidate. A binder's signed delta subtracts the largest rival score from its true owner's score. All ten pairs shared their final ordered source commitments, metadata and pool bytes, as well as their full final candidate sets. Agreement on 64 field records per arm covers the alternative values, nulls and deltas. The independently reproduced whole-posting errors distinguish the initial gate from errors in other fields. At (−0.25, 0), all sixteen answerable records posted incorrectly. Among the eight with a correct owner, exactly one other field failed in each, with four column, two unit and two subtotal errors per arm. M1 also posted eight at (0, 0). Of its four owner-right errors, two failed unit and two failed column. [Keyed independent replay](https://github.com/jackgumpe/eledgercare/blob/309b9cd834a2f91728cbb88f974f589fedb0ff58/docs/reviews/WP-0027/ranks-r1.json) · [Posting-producing grids and initial cue observations](https://github.com/jackgumpe/eledgercare/blob/309b9cd834a2f91728cbb88f974f589fedb0ff58/docs/reviews/WP-0027/comparison-r2.json)

A retrospective read with each binder's own eventual query already failed immediately after the first parent ledger write in every pair. For M1 the same candidate led on both sides throughout this sampled boundary. For M3 four pairs briefly had opposite leaders, each pointing to the other twin's true owner. Both arms had a common within-pair leader in all eight at the end of window one. The target query was identical within each pair, and the returned owner vectors differed in all eight. Four ambiguous binders encountered a malformed table represented as blocks with no eligible target row. The absence of a target explains their four abstentions. The packet identifies where the chosen read first failed and where the posting stopped. The earlier owner, schema and unit cues covary, so attribution to one stored signal remains open. [Field and event summary](https://github.com/jackgumpe/eledgercare/blob/309b9cd834a2f91728cbb88f974f589fedb0ff58/docs/reviews/WP-0027/summary-r1.json)

## Source provenance and reader reconciliation

The native SHA-256 `ce9d03a8d73ecf4366b96bc2dbbf9e129f5a2ca30265876a16b17c07cc20b169` matched the named member in the historical archive. I checked the staged call against its begin record, decoded all original tokens, and reproduced the historical exception `Expected three grounded native pages`. Only physical indices 15, 16 and 17 of the designated blind PDF were opened. Independent 300 dpi renders exactly matched the three ordered call PNGs and their RGB digests. Each of the six exact PDF glyph lines and its measured bounding box matched the signed source record, and each center lay inside its original native span. The 122 emitted IDs contain page markers at 0, 42, 81, 121. The unassigned marker occupies bytes [356, 362), with no payload at all. EOS ID 1 follows at token 122, giving 123 IDs through EOS, SHA-256 `aa252199f6a1b963d5d9b11a32cba39c784dff494fea3db85d702215dc705f26`. [Independent witness](https://github.com/jackgumpe/eledgercare/blob/309b9cd834a2f91728cbb88f974f589fedb0ff58/docs/reviews/WP-0027/witness-r1.json)

I specified 23 independent parser controls before seeing either author candidate. The first reader reproduced all 32 author decisions and reasons. Six deterministic raw/derived files matched its published evidence byte for byte. All 23 original independent cases also passed. Eight further challenges included a simple multirow table, unsupported markup and cross-checks of transcript completeness. One ordinary three-marker record had an additional visible line outside its source transcript rectangles, missing from the supplied transcript and the generated output. The original reader accepted it. The otherwise equivalent four-marker case returned unresolved. [Predeclared cases](https://github.com/jackgumpe/eledgercare/blob/e4cb2f07d8fc04c0ca99f8ea5cac229704ddc40a/docs/reviews/WP-0027/reader_expectations.py) · [Initial 31 case results with reproducer inputs and reasons](https://github.com/jackgumpe/eledgercare/blob/309b9cd834a2f91728cbb88f974f589fedb0ff58/docs/reviews/WP-0027/reader-challenge-r1.json)

The two saved development windows contain six pages. For each one I rendered the signed PDF, recovered the glyph line regions directly and removed all PDF text objects from an in-memory copy. On page 1 the remaining eight axis-aligned path objects explain every one of the 30,470 residual ink pixels. On page 4 seven path objects explain all 24,690. The remaining four pages had zero residual ink. Across all six, the independent path-only rendering matched every original RGB channel outside the glyph regions. It used neither candidate code nor a candidate-supplied mask. [Original PDF geometry and raster checks](https://github.com/jackgumpe/eledgercare/blob/bd06f11681d68e021268eb174fc5a45da39c794e/docs/reviews/WP-0027/h0-residual-r1.json)

The corrected candidate requires a complete account of residual pixels on both shapes. Only the two exact historical development call bindings can use separate PDF vector evidence for those pixels. I inspected the changes and compared the resulting geometry, layer hashes and zero residual discrepancies against the independently rendered PDF objects. All 31 independent fixtures retained identical native bytes, independently supplied binding pins and ordered PNG bytes between editions. The previously accepted incomplete record now yielded `incomplete_source_pixel_coverage`. That was the only decision change. Two required ordinary positives and two terminal positives passed. All **26 strictly unresolved cases** were withheld. One additional ordinary blank-page control explicitly allowed retention in place or withholding, and was withheld. [31 corrected cases with original offsets](https://github.com/jackgumpe/eledgercare/blob/44572822207e10872c2daae4481468f4643b4f57/docs/reviews/WP-0027/reader-challenge-r2.json)

The corrected author's 36 cases all matched, five accepted and 31 unresolved. I compared every per-case field except its clock against the author's published table, and all seven fixed raw/derived witnesses byte for byte. Both complete ordinary H0 projections and all 22 spans selected the exact archived feature positions. The independent positive cases additionally tested multibyte UTF-8, multirow tables, original char and byte ranges, exact token overlap and delimiter exclusion. The six k0014 spans have derived position selections only. Its historical run stopped before producing actual hidden states or a feature return. Both forms still require an independent and complete source transcript for marks inside glyph rectangles, and the special ruling allowance is confined to the two demonstrated bindings. [Fixed replay and digests](https://github.com/jackgumpe/eledgercare/blob/44572822207e10872c2daae4481468f4643b4f57/docs/reviews/WP-0027/publication-corrected.json)

## Verification and inventory

The initial independent calibration and parser expectations preceded inspection of the author source. I then inspected the five rank candidate files, the original reader implementation, fixtures, policy and runners, the five-file correction diff, and all three published author reports. The following PowerShell steps ran with local pinned Q0 under `-I -B`. The Python guards set offline flags and direct temporary/cache writes to the reviewer scratch tree before importing numerical or tokenizer libraries. Frozen author trees were isolated local shared clones with detached heads inside the reviewer scratch, sparse-checking out the required candidate paths. The rank launcher observed zero CUDA devices. The reader launched no model runtime.

```powershell
$q = 'C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe'
$d = 'docs/reviews/WP-0027'
$env:CUDA_VISIBLE_DEVICES = '-1'
& $q -I -B "$d/rank_review.py" ranks-r1.json
& $q -I -B "$d/rank_summary.py" ranks-r1.json summary-r1.json
& $q -I -B "$d/witness.py" 38191ec7191afc58b68aa21461a1b9c785818218f63a2a6a8ce37edba1177e0e 10aea96000abf9bd571f95cee7bf2270d1854b1c3c6341ff8548d2bc9593be32 witness-r1.json
# From the detached rank author source
& ./docs/research/WP-0027/owners/run.ps1 -Role review -RunName rank-author-r1
# From the independent review worktree
& $q -I -B "$d/rank_compare.py" comparison-r2.json
# From the original and corrected detached reader sources, respectively
pwsh -File docs/research/WP-0027/reader/run.ps1 -Run C:/Users/jackg/eLedgerCare-Speed/WP-0027/review/reader-replay-01 -Candidate 67e0898e09ee9fc848677990850f9320a7d3cd6f
pwsh -File docs/research/WP-0027/reader/run.ps1 -Run C:/Users/jackg/eLedgerCare-Speed/WP-0027/review/reader-replay-02 -Candidate 8bf8ec2c9eb6eff282366d61711ec1a249f4760a
# Each challenge used its corresponding candidate checkout
& $q -I -B "$d/reader_challenge.py" reader-challenge-r1.json
& $q -I -B "$d/h0_residual.py" h0-residual-r1.json
& $q -I -B "$d/reader_challenge.py" reader-challenge-r2.json 8bf8ec2c9eb6eff282366d61711ec1a249f4760a reader-replay-02
& $q -I -B "$d/correction_check.py" correction-result.json
& $q -I -B "$d/publication_check.py" 10f64a7e26e2e2477435a05543efbf647cefdff8 reader-replay-01 docs/research/WP-0027/reader/evidence publication-original.json
& $q -I -B "$d/publication_check.py" b0a4d3a90a825a9a3f27d334ded2e11759edfd20 reader-replay-02 docs/research/WP-0027/reader/evidence-r2 publication-corrected.json
```

The independent rank reconstruction took 8.346 seconds, the rank candidate 7.077 seconds and the keyed field/cue reconciliation 4.504 seconds. Independent k0014 authentication took 0.987 seconds and the six-page H0 residual audit 2.608 seconds. Reader candidate replays took 1.587 and 2.717 seconds. Independent parser challenges took 1.726 and 1.575 seconds, respectively. Both author ranking output digests matched the frozen deliverable. [Original replay receipt](https://github.com/jackgumpe/eledgercare/blob/bd06f11681d68e021268eb174fc5a45da39c794e/docs/reviews/WP-0027/publication-original.json) · [Corrected replay receipt](https://github.com/jackgumpe/eledgercare/blob/44572822207e10872c2daae4481468f4643b4f57/docs/reviews/WP-0027/publication-corrected.json)

The first field-comparison script compared lists in serialization order, which differs between sorted reviewer JSON and the original scorer. It stopped at its field-list assertion. Reviewer revision `35f28b6fd4590b31f39da322f6185d2d5fbb809c` compares by field identity and reproduced all actual values. A final formatting check found one extra trailing blank line in each Python script. Reviewer revision `4caffeff219665a4b28ee79020f3d73f7cd7485a` removed those ten blank lines. All eight current reviewer checks were rerun under that revision with fresh scratch output names. Each exited zero. All fields of their JSON records reproduced after excluding elapsed time alone. The final base-to-deliverable `git diff --check` exited zero.

Every added deliverable resides under `docs/reviews/WP-0027/`. External writes were restricted to the local reviewer branch, its normal pushes, and `C:/Users/jackg/eLedgerCare-Speed/WP-0027/review` for isolated checkouts, original probe materializations, scratch outputs and caches. The complete reviewer inventory follows.

| Area | Added files |
| --- | --- |
| CPU isolation and shared Git-object access | `common.py` |
| Calibration source, keyed comparison and summaries | `rank_review.py`, `rank_summary.py`, `rank_compare.py`, `ranks-r1.json`, `summary-r1.json`, `comparison-r2.json` |
| Original stop and development PDF | `witness.py`, `witness-r1.json`, `h0_residual.py`, `h0-residual-r1.json` |
| Independent parser fixtures, outcomes and reconciliation | `reader_expectations.py`, `reader_challenge.py`, `reader-challenge-r1.json`, `reader-challenge-r2.json`, `correction_check.py`, `correction-result.json` |
| Artifact comparison | `publication_check.py`, `publication-original.json`, `publication-corrected.json` |
| Subsequent report metadata | This canonical /003 only |

## Handoff

The rank candidate and corrected reader meet this packet's release criteria. The original ordinary-path finding and original blind stopping decision are preserved. No GPU session, new OCR, fit, donor swap, blind scoring, key access or product check ran. For one future investigation, vary only the parent ledger literal in otherwise matched development inputs and compare the signed owner margin immediately after that write, at first-window end and at the target. This would distinguish an early readout preference from loss over later observations while holding the other earlier cues fixed. That experiment is a proposal. The coordinator has the sole remaining packet disposition in /004.
