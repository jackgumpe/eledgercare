# WP-0021 / 001 — Saved-frame ledger reader

- Report path `docs/agent-reports/eld-scope-author/WP-0021/001_2026-11-21_research_eld-scope-author.md`
- Reserved sequence 001, research, author and publisher `eld-scope-author`. [Packet reservation](https://github.com/jackgumpe/eledgercare/blob/7a8b0a8b0ffbf2b6670584eff768a0513074c1dd/INDEX.md#wp-0021-windows-ledger-scope-feasibility)
- Session `/root/scope21_stack`, native Codex agent on Windows with PowerShell and Python 3.12.10 (standard library). Requested GPT-6.2 Astra, xhigh. Actual backend and applied effort unexposed to this author.
- Timestamp 2026-11-21T05:29:39Z
- Repository `jackgumpe/eledgercare`, branch `research/wp-0021-scope-baseline`, worktree `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/scope21-author`.
- Base revision `7a8b0a8b0ffbf2b6670584eff768a0513074c1dd`
- Deliverable revision `613a5ff92e9dd6783b8950529fbda76f6c21e9d3`
- Released observations from coordinator fixture freeze `7a430d242d0c1eab168281f3865e9976f9ae6f02`
- Prediction freeze `263f7263d654faedb17be096699c47d6050315ab`. Provenance audit and digests `5981615085aa2a7955c553e1e41643b821702505`.
- First author report in this packet. Status **ready-for-review**. Next owner `eld-scope-reviewer` for WP-0021 / 002.

## Summary

Of 12 second-page amount rows across five constructed documents, grid-only bound 4 and flagged 8. Adding observed word alignment bound 10 and flagged 2. Each mode retained all 12 second-page amount literals and pointers along with all 45 observed cell words. Each output repeated byte-for-byte. These counts describe emitted predictions and source fidelity. Semantic scoring belongs to the coordinator and independent reviewer.

After prediction freeze, the coordinator's primary scoring found all 4 grid-only assignments and all 10 combined assignments exact, with zero silently wrong scopes in either mode on the 12 preregistered targets. In a separate non-author probe reported by the coordinator, right-margin decoy lines produced four false grid-only assignments and zero combined assignments. The grid-only mode uses vertical bands and can mistake an off-table line at a matching height for a table row. The decoy probe is outside the primary denominator. [Coordinator primary scores](https://github.com/jackgumpe/eledgercare/blob/66e9cb7da495f8d65bf6eecb4db7b2b8be3e7579/docs/coordination/WP-0021/primary-scores.json)

| Input | Page-two body words | Grid output in reading order | Grid and word output in reading order |
| --- | ---: | --- | --- |
| D03 | 15 | child, child, parent, parent | child, child, parent, parent |
| D11 | 7 | 2 flagged | child, parent |
| D19 | 15 | 4 flagged | child, child, parent, parent |
| D27 | 4 | 1 flagged | 1 flagged |
| D32 | 4 | 1 flagged | 1 flagged |

D03 supplied a matching full detected grid for each second-page row. The other eight rows lacked a covering grid band. Six of them had word starts compatible with exactly one open frame. D27 and D32 supplied byte-identical inputs. Their final rows aligned equally well with both open frames, and each retained both frames and the literal amount for review. The model receives no document name. Digests and per-input counts are in the [audit record](https://github.com/jackgumpe/eledgercare/blob/5981615085aa2a7955c553e1e41643b821702505/docs/research/WP-0021/evidence/checks.json).

## Objective and criteria

Test whether an explicit saved parent and a shadowing child can bind a continued or resumed ledger row through a page break. Compare the same reader with and without word alignment. Freeze source before reading the released documents, preserve source words and pointers, flag missing or tied evidence, and freeze both outputs before answer-key release. Any silently wrong attribution is a packet failure. The reviewer checks that last criterion against independent scoring.

## Change inventory and review map

All paths below were added. The candidate contains three files. [Base-to-candidate diff](https://github.com/jackgumpe/eledgercare/compare/7a8b0a8b0ffbf2b6670584eff768a0513074c1dd...613a5ff92e9dd6783b8950529fbda76f6c21e9d3)

| Path | Action |
| --- | --- |
| `docs/research/WP-0021/read_scope.py` | `Frame`, `observed_grid`, `grid_evidence`, `word_evidence`, `decide` and `read` implement the streaming decision and preserve audit traces. |
| `docs/research/WP-0021/test_read_scope.py` | Nine author-constructed checks exercise restoration, incomplete and contradictory evidence, shared layouts and pointer retention. |
| `docs/research/WP-0021/README.md` | States the input contract, thresholds, state changes, CLI and limits. |

After the source freeze, the ten output paths were `docs/research/WP-0021/predictions/{grid,grid-words}/{D03,D11,D19,D27,D32}.json` (all ten combinations). The evidence commit adds `docs/research/WP-0021/evidence/check_predictions.py` and `docs/research/WP-0021/evidence/checks.json`. This report is separate publication metadata. [Frozen predictions](https://github.com/jackgumpe/eledgercare/tree/263f7263d654faedb17be096699c47d6050315ab/docs/research/WP-0021/predictions) · [Audit code](https://github.com/jackgumpe/eledgercare/blob/5981615085aa2a7955c553e1e41643b821702505/docs/research/WP-0021/evidence/check_predictions.py)

## Decisions and rationale

The reader learns each frame's four column anchors from a typed header below a visible section heading. It also learns a five-rule signature when the detector supplies a complete grid. A match to the same explicitly headed grid is page-local. Later grid matches require all five rules to agree within 2 points. Word alignment permits 3 points of horizontal deviation and accounts for a blank by leaving its column unoccupied. Both thresholds were selected before observation release. Cell text never selects a scope.

A unique parent match pops the child and reuses the parent's saved schema and source references. A tie or unresolved observation keeps the stack intact. The reader preserves banner values and original word references in either case. The combined mode flags a fully matching grid contradicted by word positions. In an author-constructed example with a deliberately misleading complete grid, grid-only followed the misleading grid. This illustrates a possible silent error on other inputs. [Candidate rules and tests](https://github.com/jackgumpe/eledgercare/tree/613a5ff92e9dd6783b8950529fbda76f6c21e9d3/docs/research/WP-0021)

## Verification

`python -B docs/research/WP-0021/test_read_scope.py -v` passed all nine author-constructed tests on the frozen candidate. The author waited for the coordinator's five named observation paths before prediction. For each mode (`grid`, `grid-words`) and each ID (`D03`, `D11`, `D19`, `D27`, `D32`), the exact primary CLI was:

```powershell
python -B docs/research/WP-0021/read_scope.py --mode $mode "../wp0021-data/inputs/$id.json" "docs/research/WP-0021/predictions/$mode/$id.json"
```

All ten calls exited 0. The candidate contained no fixture generation, key, file-list discovery, OCR or scoring dependency. The author committed the predictions and notified the coordinator before outcome release. Scratch reruns used the following input and output bindings for the same ten `$mode` and `$id` combinations.

```powershell
$inputFile = "../wp0021-data/inputs/$id.json"
$repeat = "../wp0021-data/author-replay/$mode/$id.json"
python -B docs/research/WP-0021/read_scope.py --mode $mode $inputFile $repeat
```

Each rerun exited 0 and its SHA-256 matched its frozen primary. The audit also compared bytes directly. It checked all 32 amount pointers and all 125 observed body word/pointer pairs per mode across both pages. All emitted rows resolved both banner labels and their complete value word lists. Bound rows referenced the printed heading and amount header. Flagged rows kept a null scope and column role and left the stack unchanged. Under the released contract, page two consists entirely of body lines, so the audit also checked page-two line coverage against the input. The auditor command exited 0.

```powershell
python -B docs/research/WP-0021/evidence/check_predictions.py ../wp0021-data/inputs docs/research/WP-0021/predictions ../wp0021-data/author-replay docs/research/WP-0021/evidence/checks.json D03 D11 D19 D27 D32
```

A second audit on the committed checker wrote `../wp0021-data/author-replay/checks.json`. It reproduced audit SHA-256 `b30bfaec02f4e0571d43a8012f4cbafb564b5693d1e29071a79d5101d48084ff`. The ten repeat files and this second audit remain in the author-owned sibling scratch directory. The only remote effects were normal pushes on the owned research branch. `git ls-remote --exit-code origin refs/heads/research/wp-0021-scope-baseline` confirmed both the initial candidate and the later prediction publication at their respective heads.

## Limitations and handoff

The source-fidelity audit compares observed tokens with their input pointers. Idealized boxes, fixed left alignment, a required final amount token, two known frame types, fixed page coordinates and synthetic inputs constrain these results. The author saw the coordinator's score after committing the predictions. Raster detector execution, independent scoring, OCR, GPU execution, customer material and product changes were outside the author run. Source and predictions remain frozen. The reviewer owns independent generation, detector replay, key-based attribution and disposition. The report publication SHA and remote receipt follow in the author handoff.
