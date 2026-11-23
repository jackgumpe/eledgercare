# WP-0031 / 002 — Independent review of declaration swaps at write 8

**Accepted.** With either original prefix held fixed, changing the donor declaration from Cedar to Alder moved the score margin toward Cedar in both probes. Clearing the incoming matrices reversed this donor contrast for M1 and preserved its direction for M3. The independent replay reproduced all 12 cells, including every raw score byte and four complete write-7 snapshots. [Comparison receipt](https://github.com/jackgumpe/eledgercare/blob/6ee777088c7d6121611091556246bb964c5a4227/docs/reviews/WP-0031/evidence/comparison.json)

| Record | Binding |
| --- | --- |
| Report | `docs/agent-reports/eld-rd-reviewer/WP-0031/002_2026-11-23_review_eld-rd-reviewer.md` · review / 002 · [Reservation](https://github.com/jackgumpe/eledgercare/blob/74f23b10d428acc3477db6ce4af7eb663e28d9f4/INDEX.md#wp-0031-bounded-cpu-replay-at-the-write-8-owner-declaration) |
| Author and publisher | `eld-rd-reviewer`, fresh native Codex task `/root/write8_review`, thread `01a20a79-ec05-7850-8af4-f4632b3f20ec`. Dispatcher configured gpt-6.2-astra / xhigh. The session identified itself as GPT-6 and exposed the thread ID. |
| Time / environment | 2026-11-23T22:25:14Z · Windows 11, PowerShell, Python 3.12.10, torch 2.13.0+cpu, NumPy 2.2.6 |
| Repository / branch | `jackgumpe/eledgercare` · `review/wp-0031-write8` in `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w031-review` |
| Base | `74f23b10d428acc3477db6ce4af7eb663e28d9f4` |
| Independent revisions | Preflight `ea731fd4287cbaa997c5cef507e42956c24f7002`, completed replay `6260131f85ec3844acb54326799c7f6d48115323`, comparison code `2a1d1aa16be76fcb40a636b71e6cbe517cde38f3`, evidence deliverable `6ee777088c7d6121611091556246bb964c5a4227` |
| Reviewed revisions | Author source `5e1a464a38ad4213b94b3b25695bd70d9054a6a3`, evidence `8f31cc66c4878ca086fa5da1498c4a73ed6a6306`, canonical report `013499d9fdf5b19e587c91cd93dfd502c0448e04`. [Author /001](https://github.com/jackgumpe/eledgercare/blob/013499d9fdf5b19e587c91cd93dfd502c0448e04/docs/agent-reports/eld-owner-probe/WP-0031/001_2026-11-23_research_eld-owner-probe.md) |
| Independence and status | First review report in this packet. I had no role in the author implementation, run or report. I froze and completed my replay before inspecting any of them. Status accepted. Next owner `eld-coordinator` for /003 disposition. |

## Objective and scope

Reproduce the actual write-8 declarations and both donor swaps on the single shared matched development opening. Gate the crossed reads on both native diagonals, matching fixed query and ordered owner anchors, and the M3 reverse native ranking. Use the second horizon as an archive cross-check. Run the two empty controls only under the specified negative-donor and inclusive 5% condition. [Release assignment](https://github.com/jackgumpe/eledgercare/blob/74f23b10d428acc3477db6ce4af7eb663e28d9f4/docs/coordination/WP-0031/assignment.md)

## Findings

Each cell shows the ordered Alder and Cedar scores, followed by the Alder-minus-Cedar margin and its change from the row's write-7 margin. These tables round to nine decimal places. The evidence retains the score bytes and binary64 arithmetic. AC and CA are retrospective interventions. Every read had both owners eligible and controller depth zero. All 12 fell below both original thresholds. [Independent results](https://github.com/jackgumpe/eledgercare/blob/6ee777088c7d6121611091556246bb964c5a4227/docs/reviews/WP-0031/evidence/replay.json)

### M1

| Incoming prefix and write-7 margin | Alder declaration | Cedar declaration |
| --- | --- | --- |
| Alder +0.025722913 | AA · −0.045244865, +0.014514945<br>Margin −0.059759811 · change −0.085482724 | AC · +0.020283854, +0.060488656<br>Margin −0.040204803 · change −0.065927716 |
| Cedar +0.028679118 | CA · −0.038797334, +0.019131321<br>Margin −0.057928655 · change −0.086607773 | CC · +0.030345000, +0.068099298<br>Margin −0.037754297 · change −0.066433415 |

### M3

| Incoming prefix and write-7 margin | Alder declaration | Cedar declaration |
| --- | --- | --- |
| Alder +0.001149714 | AA · +0.141609833, +0.142920494<br>Margin −0.001310661 · change −0.002460375 | AC · +0.122842640, +0.106935814<br>Margin +0.015906826 · change +0.014757112 |
| Cedar +0.002022058 | CA · +0.142293781, +0.143203959<br>Margin −0.000910178 · change −0.002932236 | CC · +0.123427831, +0.106986046<br>Margin +0.016441785 · change +0.014419727 |

| Probe | DA = AA − AC | DC = CA − CC | PA = AA − CA | PC = AC − CC | Interaction | Native AA − CC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| M1 | −0.01955500803887844 | −0.020174358040094376 | −0.0018311552703380585 | −0.0024505052715539932 | +0.0006193500012159348 | −0.022005513310432434 |
| M3 | −0.0172174870967865 | −0.017351962625980377 | −0.0004004836082458496 | −0.0005349591374397278 | +0.00013447552919387817 | −0.017752446234226227 |

Both interactions equaled DA − DC and PA − PC. The native difference equaled DA + PC and PA + DC in binary64. In each probe both donor contrasts were strictly negative. The absolute interaction was below the 5% limit, 0.0010087179020047189 for M1 and 0.0008675981312990189 for M3. Both empty-state pairs therefore executed.

| Probe and donor | Alder score | Cedar score | Margin |
| --- | ---: | ---: | ---: |
| M1 0A | 0.24972456693649292 | 0.17397233843803406 | +0.07575222849845886 |
| M1 0C | 0.1952122151851654 | 0.17211057245731354 | +0.023101642727851868 |
| M3 0A | 0.09794218838214874 | 0.14458493888378143 | −0.04664275050163269 |
| M3 0C | 0.0666845366358757 | 0.07939017564058304 | −0.012705639004707336 |

M1's initially negative donor contrasts became **D0 = +0.052650585770606995**. This supports inspecting how the retained matrix and the full declaration combine in the frozen write and normalized read. M3's **D0 = −0.033937111496925354** establishes that its wrong-way donor contrast survives clearing every lane. The next supported inspection there is the donor projection and owner readout. The two prefix contrasts in each probe are smaller and nonzero. Equal donor contrasts would still permit an additive prefix effect. This single matched opening cannot identify the contribution of any particular residual term, pooled vector, literal or box coordinate.

## Inspection and execution

- I inspected the pinned frozen model, parser, WP-0030 trace and release order. The page-4 displayed recurrence omits the decay multiplier on the old matrix. The frozen function computes `residual = v - a * (old @ k)` and `updated = a * old + b * torch.outer(residual, k)`. Both implementations call that function on the recipient state. My replay independently checked the resulting active lane byte-for-byte against that expression, with the scalar applied after the outer product. On zero incoming matrices the mathematical update is β·outer(v,k). The four empty reads tested that boundary only. [Frozen write](https://github.com/jackgumpe/eledgercare/blob/7db67283a4ffd3e7a20bb8d80499572cc7118c71/docs/research/WP-0024/probe/matrix.py#L80-L97)
- My archive reader authenticated the opening windows, query window, capture receipts and six member hashes per window, including token bytes and pooled features. I projected the shared final-window target row to recover the eventual query without processing any posting. The author restored the frozen query bytes directly. Query bytes matched all historical bindings. For each probe I generated the live anchors separately in the literal order established by each twin's registry. Both digests matched the WP-0029 anchor record and the WP-0030 run associations at both horizons. [Independent archive reader](https://github.com/jackgumpe/eledgercare/blob/6260131f85ec3844acb54326799c7f6d48115323/docs/reviews/WP-0031/archive.py)
- The seven prior printed literals matched across twins, and all seven pooled rows differed. The snapshot follows write 7 and precedes the declaration event. At (1,1,7), Alder's box is [53,486,339,515] and Cedar's is [53,487,339,515]. Each full-window projection preserved its own pooled vector and ordered event. The write-3 directory registered both owners. A fresh deep copy for every cell preserved both source snapshots, including controller and registry. The write-8 hook ran before the native write, left the controller and registry unchanged and used the column donor's literal. The read followed the write immediately. [Author transition source](https://github.com/jackgumpe/eledgercare/blob/5e1a464a38ad4213b94b3b25695bd70d9054a6a3/docs/research/WP-0031/experiment.py) · [Independent transition source](https://github.com/jackgumpe/eledgercare/blob/6260131f85ec3844acb54326799c7f6d48115323/docs/reviews/WP-0031/replay.py)
- Exact comparison covered all 1,179,648 prefix matrix bytes, four full discrete snapshots, all four projected donor bundles, their envelopes and every executed cell. Checks covered the recipient, unchanged post-event identity, row invariance, residual, post-write matrix and owner-column digests, raw read vector, scores, signs, eligibility, depth, thresholds, binary64 increments, both trigger decisions, D0 and all contrast bytes. Both native diagonals reproduced the archive for each probe. On M3, Cedar ranked first on AA and Alder first on CC. The two lengths reuse the same opening, query and results. [Comparison implementation](https://github.com/jackgumpe/eledgercare/blob/2a1d1aa16be76fcb40a636b71e6cbe517cde38f3/docs/reviews/WP-0031/compare.py)

### Commands and observed outcomes

In the commands below, `$py` is `C:/Users/jackg/eLedgerCare-Speed/WP-0030/runtime/venv/Scripts/python.exe`. The entry point verified the venv's executable SHA-256 `0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14`. The Windows venv launcher reports its backend interpreter in the original argv. Every command ran from the assigned worktree.

| Command or inspection | Outcome |
| --- | --- |
| `git status -sb`, `git rev-parse HEAD`, `Get-FileHash -Algorithm SHA256` on the release PDF, PyPDF reader `pypdf.PdfReader(...).pages` | Clean reservation base. Read all six pages. SHA-256 `2e77963afa6b49730f86957ad85ff6bd8597f264077c665769e3be01b5df4bb1`. |
| `& $py -I -B docs/reviews/WP-0031/replay.py ea731fd4287cbaa997c5cef507e42956c24f7002` | Exit 1 before importing torch. My first admission check incorrectly treated the pre-acquisition WP-0028 flag as current. I corrected the check to the WP-0029 per-probe, per-pair admission and completion counts, froze the correction and restarted from the archival inputs. [Retained failure](https://github.com/jackgumpe/eledgercare/blob/6ee777088c7d6121611091556246bb964c5a4227/docs/reviews/WP-0031/evidence/preflight-failure.txt) |
| `& $py -I -B docs/reviews/WP-0031/replay.py 6260131f85ec3844acb54326799c7f6d48115323` | Exit 0, 25.80 s. Both diagonal and query/anchor gates passed, both zero triggers fired. One intra-op thread and one inter-op thread, deterministic CPU FP32. |
| `git show` of the three author source blobs at the reviewed revision, `git cat-file blob` for author outputs and pinned input blobs, and `& $py -I -B docs/reviews/WP-0031/compare.py 2a1d1aa16be76fcb40a636b71e6cbe517cde38f3` | Exit 0. All 12 cells agreed. Every author payload matched its runtime receipt. Reconstructed bundles included all four projected tensors in native order. |
| `git diff --name-status 8f31cc66c4878ca086fa5da1498c4a73ed6a6306 013499d9fdf5b19e587c91cd93dfd502c0448e04`, `git show` of /001, `git ls-remote origin refs/heads/research/wp-0031-write8 refs/heads/review/wp-0031-write8` | The author added only /001 over the reviewed evidence. Its tables, signs and scope agreed with the reproduced results. Author publication and independent evidence publication returned the expected remote SHAs. |

## Change inventory and handoff

| Added path under `docs/reviews/WP-0031/` | Contents |
| --- | --- |
| `archive.py`, `replay.py` | Pinned archive, qualified runtime and independent replay |
| `compare.py` | Independent mapping and comparison of the author and reviewer evidence |
| `evidence/replay.json`, `evidence/prefixes.zip` | Run configuration, complete reads, source bindings and full write-7 matrix bytes |
| `evidence/preflight-failure.txt`, `evidence/comparison.json` | Failed pre-import check and completed comparison receipt |

The only later metadata addition on this branch is the reserved /002 report above. Scratch remains under `C:/Users/jackg/eLedgerCare-Speed/WP-0031/review/` in directories named after the two frozen replay revisions. The completed run wrote only role-owned evidence, cache directories and parser inputs. No held-out material, write 9, GPU, OCR, new posting, training, model change or product changes were part of this verification.

The owned, non-force SSH push script confirmed the independent evidence SHA `6ee777088c7d6121611091556246bb964c5a4227` on the public review branch. This report's publication SHA returns to `eld-coordinator` after the final push. Independent review found no unresolved discrepancy. Coordinator disposition and the integrated publication receipt are the remaining packet actions. [Independent deliverable diff](https://github.com/jackgumpe/eledgercare/compare/74f23b10d428acc3477db6ce4af7eb663e28d9f4...6ee777088c7d6121611091556246bb964c5a4227)
