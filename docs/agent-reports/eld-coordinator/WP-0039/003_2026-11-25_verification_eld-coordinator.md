# WP-0039 /003 · Minimum exact cell reads on the WP-0038 candidate ledgers

**Accepted for the frozen synthetic candidate sets.** Of 288 grid observations, 76 already had a single possible ledger, 146 required one exact cell value to identify the ledger, and 66 required two. Two independently written planners agreed on every winning subset and the distance of every queried subset. The independent reviewer also checked the source, concrete collision witnesses and original reports, and reproduced the four scored files byte for byte.

- Author and publisher eld-coordinator, local Codex thread `01a20a53-eec1-72c1-864c-9f8be8f4aff5`, gpt-6.2-astra at xhigh. Verification report on `jackgumpe/eledgercare`, branch `coordination/bootstrap`, primary Windows worktree.
- Published report path `docs/agent-reports/eld-coordinator/WP-0039/003_2026-11-25_verification_eld-coordinator.md`. Prepared 2026-11-25T15:23:23.1031438Z. Base and preceding WP-0038 disposition at `5cd88ed3f38dd23102045cb8c32580b310dc1424`. Reservation `3651d0a5cf0e72c31e28fac1ccd7f5b3ea6672b3`. Integrated deliverable inspected at `89f306b297ce315355d5d14082d313dfb2dd37d5`.
- The author published [WP-0039 /001](https://github.com/jackgumpe/eledgercare/blob/633c4e14f291fc15b841dc337a49cac1bad6b204/docs/agent-reports/eld-owner-probe/WP-0039/001_2026-11-25_research_eld-owner-probe.md). The independent reviewer published [WP-0039 /002](https://github.com/jackgumpe/eledgercare/blob/dd21ad211cb2f2d45ea6c2599402312e3fd292f1/docs/agent-reports/eld-rd-reviewer/WP-0039/002_2026-11-25_review_eld-rd-reviewer.md). The coordinator owns public receipt and final routing.

## Release and provenance

I read all 11 pages of advisory edition 05 (414841 bytes, SHA-256 `138224bbba027155f289db1e18e1ea13f9830376562c3b1c6a05cd516fda755c`). I released the comparison on the amended terms on pages 1–4 under the standing synthetic CPU authority. Pages 5–11 supplied Gemini's proposed proof and examples. Local, serial CPU executions and subsequent witness verification supply the measurements. [Reservation and contract](../../../coordination/WP-0039/assignment.md)

Admission verified the original WP-0038 grid and named bytes against their public receipt and both upstream implementations' complete returned candidates. The driver gave each planner the ordered mutable names, observed integer cents and upstream answer. IDs, truth, injections and expected outputs were absent from the selection interface. Both planners froze before the first release. The distinct sessions used owned worktrees and explicit gpt-6.2-astra/xhigh launch requests. The provider exposed the dispatch settings. Each route froze its raw return before exchange. [Input authentication](../../../coordination/WP-0039/admit.py) · [Source blobs, session IDs, exact argv and serial run receipts](../../../coordination/WP-0039/dispatch.json)

| Role | Frozen source | Frozen raw return | Sum of 310 planner calls | Batch wall time including compressed output |
| --- | --- | --- | ---: | ---: |
| eld-owner-probe, difference supports | `15bc8cb7f1710b03f2f34de5b9a3b1d8b85a70f8` | `845a9ebfe088cd4c893f53e27bec4668e4332239` | 19.2475 ms | 43.8467 ms |
| eld-rd-reviewer, direct projection | `2989d1ad2295089ea325fa0e1d1c392fad2249d3` | `8fd868a70882985e2cdf88603fa068c91916a499` | 165.0155 ms | 193.1530 ms |

Git initially normalized the line endings of the reviewer's runtime receipt. The reviewer restored the original bytes at the raw return SHA above and verified them against scratch without rerunning the planner. Both isolated Python 3.12.10 runs completed with zero planner exceptions. The common shuffled input SHA-256 was `d2f64e31f668cad2aa11a75dab0697b45f61ea2f9d9226dd1c14295b9f16f611`. The measured durations cover one local run per method. [Author runtime](../../../research/WP-0039/evidence/run-01/runtime.json) · [Independent runtime](../../../reviews/WP-0039/evidence/run-01/runtime.json)

## Measurements

| Body rows | Opening | Grid | Single candidate, 0 reads | Multiple finite | Includes an infinite family | 1 read | 2 reads |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | OCR | 23 | 0 | 16 | 7 | 2 | 21 |
| 1 | Trusted | 13 | 1 | 12 | 0 | 12 | 0 |
| 2 | OCR | 52 | 4 | 48 | 0 | 30 | 18 |
| 2 | Trusted | 36 | 9 | 27 | 0 | 24 | 3 |
| 3 | OCR | 93 | 33 | 60 | 0 | 42 | 18 |
| 3 | Trusted | 71 | 29 | 42 | 0 | 36 | 6 |
| **All** | | **288** | **76** | **205** | **7** | **146** | **66** |

All 30 comparison entries agreed with the amended advisory. In the separate 20 calls for 11 named assertions, 6 produced a singleton, 8 needed one read, 4 needed two and 2 were refused before solving. Eleven named calls overlap the grid. Two additional interface checks exercised an admitted empty set and an unrecognized upstream status. Each produced its own no-plan status and null read count. A singleton instead produced exactly one minimum set, the empty query, with read count zero. [Measured stratum deltas and digests](../../../coordination/WP-0039/results/summary.json) · [Interface outcomes](../../../coordination/WP-0039/results/interface.jsonl)

| Per frozen method | Query subsets examined | All tied minimum subsets | Strictly smaller subsets with collisions | All colliding subsets |
| --- | ---: | ---: | ---: | ---: |
| Grid | 37,848 | 1,029 | 605 | 3,658 |
| Named calls | 1,800 | 58 | 32 | 120 |
| Total | 39,648 | 1,087 | 637 | 3,778 |

Both routes supplied two distinct candidate ledgers with the same projection on every colliding subset. That accounts for 7,556 verified witnesses across the two runs, including the 637 strictly smaller subsets per route and another 1,069 same-size losing subsets per route. The per-observation files give mutable-coordinate order, difference supports, every winning subset, distance for every mask, and both routes' witnesses and common readouts for strict minimality. Raw returns retain witnesses on larger and equally sized losing subsets as well. [Grid](../../../coordination/WP-0039/results/grid.jsonl) · [Named](../../../coordination/WP-0039/results/named.jsonl)

## How the alternatives were distinguished

The author computes every finite-pair difference support. Within an affine family, distinct parameters differ on exactly the moving coordinates. Against a fixed candidate, each moving coordinate can agree at only one integral parameter. The author groups coordinates with the same admissible root and retains the generic difference support attained elsewhere. A query must intersect every nonempty support. The reviewer projects the finite points directly and minimizes their disagreement with the projected affine line using the largest group of coordinates that agree at the same allowed parameter. Both methods account for fixed coordinates and every excluded integer. The reviewer independently checked all collision witnesses and recovered each positive distance by deleting one queried coordinate at a time. [Independent audit source](../../../reviews/WP-0039/audit.py) [Support implementation](../../../research/WP-0039/planner.py) · [Projection implementation](../../../reviews/WP-0039/planner.py)

- **C1.** With an OCR opening, either balance distinguishes the clean ledger and every possible nonzero common shift. A consistent trusted opening yields a singleton. The actual conflicting trusted opening is refused before solving.
- **C2.** In the OCR domain, the family of true endpoints is `(106-c, 117-c)` for integer `c` excluding 0 and 6. The two single-endpoint alternatives supply the endpoint tuples at those holes. The separate amount/total alternative has endpoints `(100,117)`. Matching its opening requires `c=6`, and matching its closing requires `c=0`. No one member of the completed line matches both. The five winning pairs are A1+B0, A1+B1, B0+B1, B0+T and B1+T. A1+T leaves every endpoint shift unresolved.
- **C3.** Each OCR singleton has a collision. The eight tied pairs include A1+B0, whose projections are (11,100), (17,100) and (11,106) cents. All eight appear in the named record.
- **C9a.** Five of six pairs separate all five candidates. For A1+T, two ledgers give (11,11) and another two give (17,17). Even using all four mutable cells gives minimum distance two.
- **C9b.** The trusted opening is 100. The triples (A1,B1,T) are (11,111,11), (1,101,1) and (17,117,17). Any of those cells separates all candidates on an exact read. Reading all three gives distance three and tolerates any one wrong returned value within this candidate set.
- **C9c.** The observed opening 110 conflicts with the trusted value 100. Both methods preserved the original pre-solve refusal, null residuals, null read count and absence of candidate queries.

## Interpretation and limits

For at least two candidates, one exact read suffices precisely when some mutable cell differs across every distinct candidate pair. The number of cycles alone does not determine the minimum. Removing a spanning-tree complement gives a general sufficient query of at most `n+1` cells for an OCR opening or `n` for a trusted opening. A balanced difference supported on the remaining tree must vanish by conservation at its leaves. The observed maximum of two belongs to this grid of one to three rows.

For up to `e` arbitrary corrupt returned cells, unique correction within the candidates requires and suffices that the minimum projected Hamming distance be at least `2e+1`. Otherwise a received word can fall in two radius-`e` balls. All 953 minimum sets for the ambiguous grid records have distance one. With all mutable cells included, 23 cases reached distance two, 155 reached three and 34 reached four. Thus 189 of 212 ambiguous grid observations could tolerate one bad return under the model. This assumes the true ledger belongs to the candidates, correct coordinate bindings, and a specified count of bad values. Real reread error rates and correlations remain unknown.

The objective counts simultaneously requested cell values. Choosing a cheapest crop requires a separate cost function for whole query sets, including any cells that share a crop. Confidence alone supplies neither those prices nor an error budget. No paid crops or physical readings were taken. Externally inconsistent candidate records, larger ledgers and multiple interacting affine families have no execution evidence here. The support decoder checks admitted opening status explicitly. The projection decoder relies on authenticated upstream admission for that field. All supplied opening statuses, both pre-solve refusals and the unknown-status control were checked. WP-0037 remains parked; no further lane is released.

## Reproduction, changes and custody

The scorer froze at `eae6b804f2e3220d040d67560d2d82e0be278826` before comparing outputs. The coordinator ran the command below once on the two raw returns. It exited zero with no audit failure. The resulting four files were published at `fc9cec5661056ef93d7e6f631a6f03db559ce8f4`. The independent reviewer regenerated the files in reviewer scratch. [Scoring source](../../../coordination/WP-0039/score.py)

```text
python -I -B docs/coordination/WP-0039/score.py 845a9ebfe088cd4c893f53e27bec4668e4332239 8fd868a70882985e2cdf88603fa068c91916a499 docs/coordination/WP-0039/results
```

The integration used the original role commits and compared every merged blob with its role branch. Prior worktree paths, branches and unrelated working files remained bound. The integrity check covered 110 pre-existing worktrees, 73 local file identities, the dirty primary package SHA-256 and the original stash. The only added worktrees belong to the two reserved roles. [Integrity observations](../../../coordination/WP-0039/integrity.json)

The following inventory covers the accepted predecessor through the integrated deliverable. This report and the two shared ledgers are the subsequent closeout edit. The coordinator then verifies every changed file from its immutable public URL, publishes the byte receipt and original report bindings, and repeats the checks on the final live head. [Public verification procedure](../../../coordination/WP-0039/verify_publication.py)

```text
CURRENT.md
INDEX.md
docs/agent-reports/eld-owner-probe/WP-0039/001_2026-11-25_research_eld-owner-probe.md
docs/agent-reports/eld-rd-reviewer/WP-0039/002_2026-11-25_review_eld-rd-reviewer.md
docs/coordination/WP-0039/admit.py
docs/coordination/WP-0039/assignment.md
docs/coordination/WP-0039/dispatch.json
docs/coordination/WP-0039/integrity.json
docs/coordination/WP-0039/operate.py
docs/coordination/WP-0039/results/grid.jsonl
docs/coordination/WP-0039/results/interface.jsonl
docs/coordination/WP-0039/results/named.jsonl
docs/coordination/WP-0039/results/summary.json
docs/coordination/WP-0039/score.py
docs/coordination/WP-0039/verify_publication.py
docs/research/WP-0039/evidence/run-01/.gitattributes
docs/research/WP-0039/evidence/run-01/outputs.jsonl.gz
docs/research/WP-0039/evidence/run-01/runtime.json
docs/research/WP-0039/planner.py
docs/reviews/WP-0039/audit.py
docs/reviews/WP-0039/evidence/run-01/.gitattributes
docs/reviews/WP-0039/evidence/run-01/outputs.jsonl.gz
docs/reviews/WP-0039/evidence/run-01/runtime.json
docs/reviews/WP-0039/planner.py
```
