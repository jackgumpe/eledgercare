# WP-0039 / 001 Minimum exact cell readings on the frozen arithmetic candidates

- Report path `docs/agent-reports/eld-owner-probe/WP-0039/001_2026-11-25_research_eld-owner-probe.md`
- Sequence /001 reserved for eld-owner-probe at `3651d0a5cf0e72c31e28fac1ccd7f5b3ea6672b3`
- Category research
- Author eld-owner-probe, Codex CLI collaboration session `01a2130c-e5c9-79f1-ba4e-ccbce37a52ca`
- Model and effort Codex, dispatched for `gpt-6.2-astra` and `xhigh`. The dispatch records the requested configuration. This worker interface did not expose an additional runtime model/effort attestation.
- Timestamp 2026-11-25T15:18:31Z
- Repository `jackgumpe/eledgercare`, branch `research/wp-0039-d55`, worktree `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w039-author`
- Authenticated WP-0038 record pin `5cd88ed3f38dd23102045cb8c32580b310dc1424`
- Base revision `3651d0a5cf0e72c31e28fac1ccd7f5b3ea6672b3`
- Planner deliverable revision `15bc8cb7f1710b03f2f34de5b9a3b1d8b85a70f8`
- Raw evidence revision `845a9ebfe088cd4c893f53e27bec4668e4332239`
- Previous report in this packet — none. Upstream candidate disposition [WP-0038 /003](https://github.com/jackgumpe/eledgercare/blob/5cd88ed3f38dd23102045cb8c32580b310dc1424/docs/agent-reports/eld-coordinator/WP-0038/003_2026-11-25_verification_eld-coordinator.md).
- Status ready for independent review by eld-rd-reviewer /002, followed by eld-coordinator /003.

## Summary

Both independent routes returned the same query minima and projected distances. Across the 288 grid observations, 76 already had a unique ledger, 146 needed one exact cell value, and 66 needed two. Each route tested 37,848 grid query masks and identified the same 1,029 tied minimum sets. Among 20 named invocations there were six singletons, eight one-cell cases, four two-cell cases and two pre-solve opening conflicts. The two protocol-only sentinels returned their intended statuses. These counts preserve the overlaps between named and grid invocations. [Coordinator comparison](https://github.com/jackgumpe/eledgercare/blob/fc9cec5661056ef93d7e6f631a6f03db559ce8f4/docs/coordination/WP-0039/results/summary.json)

## Objective and acceptance criteria

Find every smallest subset of mutable cells whose simultaneous exact readings identify every distinct candidate true ledger for that observation. For each possible subset, report its minimum projected Hamming distance and exhibit two distinct ledger references when their projections collide. Preserve each finite hypothesis and all allowed integer family members. An upstream opening conflict, an admitted empty candidate set and an unsupported representation have separate outcomes. The predeclared corpus comprises 288 grid records, 20 domain-specific named invocations over 11 assertions, and two protocol-only sentinels. [Release and interface](https://github.com/jackgumpe/eledgercare/blob/3651d0a5cf0e72c31e28fac1ccd7f5b3ea6672b3/docs/coordination/WP-0039/assignment.md)

## Change inventory

| Action | Owned path | Purpose |
| --- | --- | --- |
| Added in candidate | `docs/research/WP-0039/planner.py` | Decode admitted sparse signed errors, enumerate exact difference supports with witnesses, and find all minimum hitting sets. |
| Added in evidence commit | `docs/research/WP-0039/evidence/run-01/outputs.jsonl.gz` | Original compressed return for every blinded invocation. |
| Added in evidence commit | `docs/research/WP-0039/evidence/run-01/runtime.json` | Original driver runtime and input, executable, and output identities. |
| Added in evidence commit | `docs/research/WP-0039/evidence/run-01/.gitattributes` | Preserve the two original evidence byte streams in Git. |
| Added after evidence | This /001 report | Author verification and handoff. |

The source and evidence are separate normal commits on the owned branch. The local CPU run wrote to `C:/Users/jackg/eLedgerCare-Speed/WP-0039/author/run-01`. Exact outputs were copied to the paths above. The scoped publication script verified each remote tip against the expected full SHA.

## Decisions and rationale

For finite hypotheses, decode the true ledger as observation minus signed error. Include the clean observation first when admitted. Every pair of finite indices yields a coordinate-difference mask. The family decoder subtracts both the offset and slope of the signed error to obtain a true ledger `a + b*c`, where c ranges over all integers except the provided exclusions. Every pair of distinct family parameters differs on exactly the coordinates with nonzero slope. Two integers above the greatest exclusion witness this mask.

For a fixed finite ledger p, a constant family coordinate always agrees or always differs. A moving coordinate can agree only at the rational root `(p[i] - a[i]) / b[i]`. Integer division with remainder identifies the admissible integral roots exactly, including negative roots and slopes. Group all coordinates sharing a root before clearing their bits from the generic difference mask. Every other admissible integer gives the generic mask. A parameter exceeding every exclusion and retained root witnesses that entire class. These three pair types exhaust the candidate union. A zero mask denotes one true ledger represented twice. For every distinct nonempty mask the code keeps one actual producing pair. This also preserves supports that strictly contain other supports, since they remain part of the complete support collection. [Source, functions `_point_family_masks` and `difference_supports`](https://github.com/jackgumpe/eledgercare/blob/15bc8cb7f1710b03f2f34de5b9a3b1d8b85a70f8/docs/research/WP-0039/planner.py)

For queried mask Q and pairwise difference mask H, their projected Hamming distance equals the number of set bits in `Q & H`. A missing support gives a concrete collision. Taking the minimum intersection size over all supports gives the exact distance. The planner visits every query mask in ascending numeric order and retains all ties at the smallest separating cardinality. The sole finite truth case yields null distances, no collision and the unique empty query of size zero.

For arbitrary n, subtracting two balanced candidates gives an integer circulation. An unqueried spanning tree cannot support a nonzero circulation, by successively applying flow conservation at each leaf. The cotree therefore supplies an upper bound of n+1 cells for an OCR opening or n for a trusted opening. A cycle count alone does not determine the optimum for the restricted candidate set. To correct up to e arbitrarily wrong returned coordinates for at least two candidates, every two projected words must be more than 2e apart. At distance at most 2e, partition their differing coordinates into two groups of size at most e to build an ambiguous readout. At larger distance, triangle inequality rules out overlap of their radius-e balls. The resulting criterion is `d(Q) >= 2*e+1`.

## Verification

The verified 414,841-byte eleven-page advisory had SHA-256 `138224bbba027155f289db1e18e1ea13f9830376562c3b1c6a05cd516fda755c`. I read the amendment and original return through the local Git distribution's `pdftotext.exe -layout -enc UTF-8`. I checked record byte lengths, SHA-256 values and Git blob identities from the pinned WP-0038 tree against its publication receipt. Grid matched on 172,072 bytes, blob `addf3a64cef69e2cfca27eaf377580a12e3e94a4`, SHA-256 `31c7caa313ea4f1d2f559d2df792f50c8790d8821e4345ae45d63ab4b72319eb`. Named matched on 11,248 bytes, blob `cba63668202d9698a750b98928362515cdb15439`, SHA-256 `482719a0dcc129524adb8644fe424cd541a6549921b5fdfc89e7c2a98b1687d8`. [Published input inventory](https://github.com/jackgumpe/eledgercare/blob/5cd88ed3f38dd23102045cb8c32580b310dc1424/docs/coordination/WP-0038/publication-receipt.json)

Before source freeze, syntax compilation with CPython 3.12.10 and `git diff --cached --check` succeeded. The Git blob `159702fe7627402837a6bac1d63f859cf03cee1d` matched the working planner. Both sources were frozen when the coordinator issued the sole CPU release at `94dd849c01a3033e2aadd89202e78b70cd0fe56c`. The complete released command executed from the owned worktree.

```powershell
python -I -B '../../eledgercare/docs/coordination/WP-0039/operate.py' --candidate 15bc8cb7f1710b03f2f34de5b9a3b1d8b85a70f8 --planner docs/research/WP-0039/planner.py --observations C:/Users/jackg/eLedgerCare-Speed/WP-0039/author/inputs.jsonl --input-sha d2f64e31f668cad2aa11a75dab0697b45f61ea2f9d9226dd1c14295b9f16f611 --out C:/Users/jackg/eLedgerCare-Speed/WP-0039/author/run-01
```

This single run exited 0 with 310 calls and zero exceptions. The runtime records 19,247,500 ns summed over calls, 43,846,700 ns batch wall time and 46,875,000 ns process CPU time. The lane was returned at run exit. The measured isolated stdlib interpreter digest was `4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a`. The working planner was `9e6d7e476f845428bfadf9ba6dcaf8bdacb52c4a1cb429df5b35c005282c5e74`. The compressed output was `3b24c26bca5f6aaea630cf7aae7e455fc46e45584391169e035fa7d458730085` and the runtime was `f21028350243db9e78cb52c8256acdcbc44da91bf14e74d57ab590f0c99bdbf1`. I matched SHA-256 from each original to its evidence copy, and matched the staged blobs against `git hash-object --no-filters`. [Frozen observations and runtime](https://github.com/jackgumpe/eledgercare/tree/845a9ebfe088cd4c893f53e27bec4668e4332239/docs/research/WP-0039/evidence/run-01)

### Grid by row count and opening

| Rows | Opening | Inputs | Unique, k=0 | Multiple finite | Infinite | k=1 | k=2 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | OCR | 23 | 0 | 16 | 7 | 2 | 21 |
| 1 | Trusted | 13 | 1 | 12 | 0 | 12 | 0 |
| 2 | OCR | 52 | 4 | 48 | 0 | 30 | 18 |
| 2 | Trusted | 36 | 9 | 27 | 0 | 24 | 3 |
| 3 | OCR | 93 | 33 | 60 | 0 | 42 | 18 |
| 3 | Trusted | 71 | 29 | 42 | 0 | 36 | 6 |
| All | Both | 288 | 76 | 205 | 7 | 146 | 66 |

Every mask has a recorded distance in the original author output. The frozen, keyed grid and named records identify all winning subsets, distances and smaller-mask collisions. Independently summarizing the author output by numeric mask after the run gave 39,648 mask entries in total. The 1,087 winning sets include 1,029 grid and 58 named ties. All 637 smaller masks had collisions (605 grid and 32 named). There were 1,069 more collisions on equally small nonwinning masks and 3,778 colliding masks of all sizes. The coordinator validated both routes' concrete witness pairs. The 13,488 masks on singleton inputs all had null distance. The 11 named assertions cover 20 calls, 11 of which overlap grid observations. [All grid sets and distances](https://github.com/jackgumpe/eledgercare/blob/fc9cec5661056ef93d7e6f631a6f03db559ce8f4/docs/coordination/WP-0039/results/grid.jsonl) · [All named sets and distances](https://github.com/jackgumpe/eledgercare/blob/fc9cec5661056ef93d7e6f631a6f03db559ce8f4/docs/coordination/WP-0039/results/named.jsonl)

### Named checks

- C1 with an OCR opening accepts either endpoint, B0 or B1, as a single read. Each distinguishes the clean observation from every allowed nonzero common shift and all such shifts from each other. The consistent trusted opening yields a singleton. The conflicting opening yields the pre-solve rejection.
- C2 with an OCR opening has five tied pairs (A1+B0, A1+B1, B0+B1, B0+T and B1+T). A1+T leaves the endpoint shifts unresolved. The two single-endpoint repairs supply the ledgers at the excluded parameters 0 and 6. The additional finite amount/total alternative ties on either endpoint alone. Its pair of endpoints, however, lies off the affine line. Each of A1, B1, T suffices in the trusted variant.
- C3 with an OCR opening admits eight minimum pairs (A1+B0, A2+B0, A1+B1, A2+B1, B0+B1, A1+B2, A2+B2 and B1+B2). In amount/opening order, A1+B0 returns three different projections, (11,100), (17,100), (11,106). Each singleton has a collision. With a trusted opening the three one-cell choices are A1, A2 and B1.
- C9a has five separating pairs, exactly those listed for C2 with OCR. On A1+T, two distinct ledgers give (11,11) and two others give (17,17). In C9b the three (A1,B1,T) candidates in cents are (11,111,11), (1,101,1), (17,117,17). Reading any one of these cells suffices with exact return. Reading all three gives distance three and uniquely corrects one arbitrary wrong returned value. The full mutable set in C9a has distance two.
- C9c's opening conflict returns null k, empty masks/checks and upstream null residuals. Each interface sentinel likewise has no proposed reads, with separate statuses for an admitted empty set and an unknown upstream status. [Protocol-only records](https://github.com/jackgumpe/eledgercare/blob/fc9cec5661056ef93d7e6f631a6f03db559ce8f4/docs/coordination/WP-0039/results/interface.jsonl)

## Risks, disagreements, and unfinished work

All 30 numeric comparison cells in the six strata matched advisory pages 1–4. The named checks agree with the examples there. The brief gives examples of minimum sets for C2 and C3. The comparison enumerates all five and eight ties respectively. For single-cycle families one read suffices when that coordinate changes across every distinct pair, including finite alternatives. The maximum of two observed here applies to these fixtures. The cotree bound and the Hamming-distance condition above address larger graphs and erroneous returns under their stated hypotheses.

This synthetic result assumes the true ledger belongs to the full input candidate set and the requested coordinates are bound correctly. Physical rereads, crop costs and correlated OCR error rates were outside the release. The prior Gemini return's lowest-confidence crop suggestion has no supplied cost or reliability model. Hamming distance gives a conditional guarantee for erroneous returned values within a specified budget. It cannot recover an omitted candidate.

## Review map and handoff

Independent eld-rd-reviewer owns /002 and the projection route. The coordinator owns /003 and integration. Reviewers can inspect every output by record, every subset by numeric mask, each zero-distance pair reference and every tied minimum, then compare with the independently frozen projection route. Remote source and raw evidence tips were verified via the owned scoped push script at publication. [Planner diff](https://github.com/jackgumpe/eledgercare/compare/3651d0a5cf0e72c31e28fac1ccd7f5b3ea6672b3...15bc8cb7f1710b03f2f34de5b9a3b1d8b85a70f8)
