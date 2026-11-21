# WP-0021 / 003 — Restoring the parent ledger after a page break

- **Report** `docs/agent-reports/eld-coordinator/WP-0021/003_2026-11-21_verification_eld-coordinator.md`, reserved coordinator verification 003. [Assignment](../../../coordination/WP-0021/assignment.md)
- **Author and publisher** `eld-coordinator`, continuously assigned native Codex CLI session on Windows. Actual model and effort unexposed. Fresh author and reviewer sessions requested GPT-6.2 Astra at xhigh.
- **Repository** `jackgumpe/eledgercare`, `coordination/bootstrap`, worktree `C:/Users/jackg/Asp.net Projects/eledgercare`.
- **UTC publication preparation** 2026-11-21T05:32:04Z. Base `caf79c2bff0545454eabb831b33cdf8f003c2bf1`. Decision deliverable `3dae92ed6735b9cdd4e576040335df9a13cab41b`.
- **Status** Accepted for the bounded feasibility question. The standalone grid-only mode failed the supplemental silent-assignment check. Next owner is the coordinator for any fresh observation study.
- **Reports** [Author /001](https://github.com/jackgumpe/eledgercare/blob/24eb1dd1afa6925d07571cd9ff86116c01572537/docs/agent-reports/eld-scope-author/WP-0021/001_2026-11-21_research_eld-scope-author.md) · [Independent review /002](https://github.com/jackgumpe/eledgercare/blob/e4fc9806dea391d649576d68a9f016acc50287a5/docs/agent-reports/eld-scope-reviewer/WP-0021/002_2026-11-21_review_eld-scope-reviewer.md) · [Preceding routing disposition](../WP-0020/004_2026-11-20_verification_eld-coordinator.md).

## Decision

Retain the explicit saved-frame reader with word alignment as the baseline for the next Windows study. It answered a practical question on generated forms. After a contractor table interrupts a ledger, a second page can resume either table without repeating its header. The reader keeps each table's header and printed word positions in memory. It restores the parent when the later row supplies evidence for that choice. On D19, for instance, both scopes print `190.00`. The reader kept the first amount with the contractor row (`p2:L1:W4`) and the later amount with the parent ledger (`p2:L3:W3`). The parent's unit came from the printed first-page banner even though that row had an empty unit cell. [Scored rows](../../../coordination/WP-0021/primary-scores.json) · [D19 page two](../../../coordination/WP-0021/evidence/rasters/D19-p2.png)

| Primary outcome across five two-page development documents | Grid only | Grid and word positions |
| --- | ---: | ---: |
| First-page setup rows correctly bound | 20/20 | 20/20 |
| Distinguishable second-page rows correctly bound | 4/10 | 10/10 |
| Among these, resumed parent rows correctly bound | 2/5 | 5/5 |
| Ambiguous second-page rows flagged | 2/2 | 2/2 |
| Silent incorrect assignments among all second-page targets | 0/12 | 0/12 |
| Second-page amount literals and source pointers preserved | 12/12 | 12/12 |

The grid detector found both multirow tables on D03. On D11, each single-row table had only two horizontal rules. On D19, the two nearby tables shared outer margins and had different internal columns. The detector returned no second-page grid for D11 or D19. Word positions recovered all six assignments. For D27 and D32, the intended scope differed while the complete observations supplied to the reader were byte-identical. Both modes kept the literal and flagged its scope. The underlying rasters differ in shading, so this establishes ambiguity only for the exported input. [Raw grids, words and boxes](../../../coordination/WP-0021/evidence/inputs) · [Non-author reconciliation](../../../reviews/WP-0021/evidence/reconciliation.json)

A separate right-margin check exposed an unsafe assumption. The reviewer moved each of four D03 amount words entirely past the table's right edge and left its vertical position unchanged. The grid-only reader still assigned all four to a ledger because it tests vertical bands without checking horizontal containment. The combined reader flagged all four. The coordinator reran the reviewer's challenge and reproduced those four false assignments. These supplemental cases have their own denominator. [Reviewer prediction replay](../../../reviews/WP-0021/evidence/prediction-replay.json) · [Decision and counts](../../../coordination/WP-0021/decision.json)

## Evidence, changes and verification

The coordinator selected the smaller CPU pilot from the supplied consultation, SHA-256 `0cd9c68cc81866dc9aaaabe148c9b06ded8e972081c7b1ae104a9453ab6e70dc`. Separate sessions owned the reader and the independent review. The coordinator committed the generator digest and scorer before scoring, froze the exact observations, verified the author and coordinator prediction bytes, then opened the committed key. The reviewer rebuilt all five JSON inputs, ten images and the key, executed both modes, and reproduced the complete primary score byte-for-byte. A failed reviewer assertion assumed the two ambiguity rasters had identical threshold masks. They differed at 72 pixels. The corrected checker tests the actual binder input boundary. [Freeze receipts](../../../coordination/WP-0021/prediction-freeze.json) · [Independent command log and correction](../../../reviews/WP-0021/evidence/commands.md)

| Verification | Result |
| --- | --- |
| CPU fixture generation with the original `visual.rule_tables` from `a0e738bc03e515999659dda09c5ee76d08fb37df`, Segoe UI hash in the key, WP-0005 Python, NumPy 2.2.6 and Pillow 13.0.0 | Reproduced 15 input and raster files and the originally committed key digest. |
| Frozen `read_scope.py` at `613a5ff92e9dd6783b8950529fbda76f6c21e9d3`; both modes against each of the five inputs | Ten prediction files independently reproduced. All 32 target amounts and all 125 observed body words in each mode retained their source references. |
| Stock packet scorer at `f7bd181b49c0345a481a7cb7db6b4a848102b2a2`, followed by a separately written non-author checker | Per-row, per-case and aggregate verdicts matched. The stock score SHA-256 is `247b933d8f31fea6a2c70d23809e6b41c5b12eb6bb7bb0d6bc78cbee5c254cc4`. |
| Coordinator replay of `replay_reader.py` from `1181da64488651d91b33b61096c947aee5911118` against the frozen candidate and observable JSON | Both primary outputs and horizontal displacement results matched the independent evidence. |

Reproduction uses a fresh scratch directory and the existing Windows Python with the pinned Pillow, NumPy and font. From the repository root, supply `$py` and an empty scratch directory `$scratch`.

```powershell
$packet = 'docs/coordination/WP-0021'
& $py -I -B "$packet/fixtures.py" . "$scratch/regenerated"
& $py -I -B "$packet/score.py" --inputs "$packet/evidence/inputs" --key "$packet/answers.json" --predictions "$packet/evidence/predictions" --out "$scratch/score.json"
& $py -I -B docs/reviews/WP-0021/replay_reader.py 613a5ff92e9dd6783b8950529fbda76f6c21e9d3 "$packet/evidence/inputs" "$scratch/reader"
```

The coordinator changed `INDEX.md`, `CURRENT.md`, and the assignment, fixture/scoring code, freezes, five observation files, ten rasters, ten predictions, opened key, rebuild receipt, primary scores and decision under `docs/coordination/WP-0021/`. The author supplied the reader, tests, ten predictions and audit under `docs/research/WP-0021/`. The reviewer supplied independent checks and receipts under `docs/reviews/WP-0021/`. Each role published its own report in its reserved location. Publication metadata and ledger closure follow this report. The private remote received normal pushes on the three owned branches. Scratch outputs reside under `eledgercare-worktrees/wp0021-data`. [Base-to-decision change inventory](https://github.com/jackgumpe/eledgercare/compare/caf79c2bff0545454eabb831b33cdf8f003c2bf1...3dae92ed6735b9cdd4e576040335df9a13cab41b)

## Limits and next decision

The detector ran on rendered pixels. The binder's words and boxes came from the renderer, with known headings, left-aligned columns and a required terminal amount. The 10 distinguishable page-two targets cover three constructed layouts. This pilot supplies evidence about assigning existing words to scopes. Recognition quality, elapsed time on the 60-page archive, performance on captured WinRT boxes and the consultation's matrix memory remain unmeasured.

The next bounded comparison should freeze this reader and obtain real WinRT lines and boxes on fresh synthetic nested forms. Include right-aligned amounts, wrapped descriptions, one-row returns and margin notes. Check horizontal containment, preserve literal pointers, and score unflagged wrong bindings, abstentions and how often the source words were available. Comparing actual boxes with ideal positions on the same rows will distinguish lost layout evidence from a failure to remember the parent. A subsequent matched-input matrix comparison becomes informative if the visible layout distinguishes the correct frame and the saved-frame reader still loses it. The consultation's 24-document evaluation remains a separate experiment.
