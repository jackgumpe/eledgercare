# WP-0020 / 001 · Archived visible-label routing

| Report metadata | Value |
| --- | --- |
| Report path | `docs/agent-reports/eld-routing-author/WP-0020/001_2026-11-20_research_eld-routing-author.md` |
| Reservation | [WP-0020 /001 at the reservation revision](https://github.com/jackgumpe/eledgercare/blob/864753428a7afe5996fe1e411d286f58a6413b54/INDEX.md#wp-0020-visible-identifier-labels-and-archived-baidu-routing) |
| Category / author / publisher | research / eld-routing-author / eld-routing-author |
| Session | Native Codex delegated session `/root/route20_author`, thread environment `01a1faaf-66c5-7901-83f9-850e54da21e5`. Astra xhigh requested. Specific backend and applied effort unexposed. |
| Environment | Windows, PowerShell 7.7.0, Python 3.12.10 standard library, Git 2.55.0.windows.1 |
| Timestamp | 2026-11-20T20:46:51Z |
| Repository / branch | Private `jackgumpe/eledgercare`, `research/wp-0020-label-route` |
| Worktree | `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/route20-author` |
| Base / source freeze | `864753428a7afe5996fe1e411d286f58a6413b54` / `b34c046e04ff98ddb0fb021ee8e8dade88a83126` |
| Windows manifests / routed deliverable | `081acd13b7f26b3ea374a8ae3a2de79d71e9b0bf` / `122652984a316c9b8963ec89cf1b61dd994aaf99` |
| Previous and related reports | First report from this author in this packet. /002 and /003 were awaiting independent analysis and review at the prediction freeze. |
| Status / next owner | ready-for-review / eld-routing-reviewer for /003, with eld-routing-analysis for /002 |

## Result and acceptance criteria

The authorized question was whether a visible Windows identifier label could select individual fields from existing ordinary Baidu reads. This author froze a Windows-only manifest and deterministic field binding, executed the route on the selected, coordinator-admitted archives and delivered ordinary-scorer predictions before any H/A outcome join. All 64 pages carried at least one selected field, so all 22 available native windows were requested.

| Family | Fields | Pages | Windows | Bound equal | Bound different | Unresolved |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| H, h-r1-ab | 6 prose | 4/4 | 2/2 | 4 | 2 | 0 |
| A, a-recovery-ab | 120 prose, 48 cells | 60/60 | 20/20 | 75 | 86 | 7 |

H's final single-page window was requested for one field. Each A window had six or ten selected fields. Among A prose, 68 bound values equalled Windows and 45 differed. Five candidate native spans lacked usable single-line text and two original lines had no eligible span. All 48 selected A cells bound, including 41 differing values. Two originally empty Windows cell values on pages 15 and 30 received literal nonempty strings. Whether either was a printed blank requires the scoring role's evidence. No native cell binding yielded an explicit empty string on H/A. Constructed controls exercised the explicit empty case.

## Policy and custody

The selector reads only the three named Windows files per family. The coordinator approved adding an application-visible raw-line count, grid and ordered span-hash projection after confirming saved Windows predictions omit that layout. The source freeze preceded both H/A manifests. The coordinator's Windows-only input admission is `3559d035f0b1a1893413dd30df13c8f64504a69c`. Each rebuilt page reproduced its span sequence, grid values and text before selection. The coordinator admitted only requested native windows after manifest freeze, at `eee71f537433ede641103aeb2aa187e06843c0c2`. The title-adjusted native projection uses the existing parser treatment from `0186467670074761a777602d77b53deff3451300`. Both arms use one observation per H/A page.

The unchanged WP-0019 predicate matched header or non-table line text. A unique geometric match in both directions (IoU ≥ 0.5) bound native tables or prose spans. Matching tables also required identical row-length sequences. The same positional cell supplied its literal value. Prose used the whole native single-line string. A missing observation retained Windows and yielded JSON null in its decision record. Scorer inputs preserve the visible Windows location for a substituted reading. The native region, literal values, eligibility indices and decisions are available per routed field. [Frozen rules](https://github.com/jackgumpe/eledgercare/blob/b34c046e04ff98ddb0fb021ee8e8dade88a83126/docs/research/WP-0020/route/README.md)

## Change inventory and evidence

Every path in the base-to-deliverable diff was added beneath `docs/research/WP-0020/route/`.

| Relative path | Content |
| --- | --- |
| `README.md` | Pre-execution rules, projection, dependencies and CLI |
| `route.py` | Window allowlist, manifest, reciprocal geometric binding, substitution, evidence and output |
| `check_route.py` | Four synthetic controls including frozen scorer line/cell joins, missing and explicit blanks, spacing, predicate identity and ambiguity |
| `evidence/H/manifest.json`, `evidence/A/manifest.json` | Per-field observations, provenance, window membership and original input hashes |
| `evidence/H/decisions.json`, `evidence/A/decisions.json` | Per-field status, reason, value, native witness and consumed native-page byte hashes |
| `evidence/H/prediction.json`, `evidence/A/prediction.json` | Full predictions under the ordinary scorer's schema |

Only this canonical report was added after the routed deliverable. The replay read coordinator-owned Windows and native inputs. Persistent external effects were ordinary pushes to the owned branch. Temporary copies used for the same-author replay were removed by Python's TemporaryDirectory. [Deliverable diff](https://github.com/jackgumpe/eledgercare/compare/864753428a7afe5996fe1e411d286f58a6413b54...122652984a316c9b8963ec89cf1b61dd994aaf99)

| Family | Manifest SHA-256 | Decisions SHA-256 | Prediction SHA-256 |
| --- | --- | --- | --- |
| H | `7bc3c1ca418059ea97c9d1bb80295f2c50574f8d58e99fc3431ce1f103f0af5f` | `d082fcc86de93987f7d32119cae4376d74b5cd73192ec5b8ca3cd0c23115d7c9` | `73bf26cba73372d6b1cad77aaae0e7182ae8f8310bab80fc9bc9591db19957ba` |
| A | `5d2f9b31e43fc03854bca6ac08efac75fc82543311fa9f40b660d072a1d8a74a` | `951f10bb8b292a63d02bfd4f5cf219d3129f87818d4dfb12b0ced5718fdd7c6f` | `9e94e52337b8a6ce2a3f6c85bd978065bde31bbd35fd692c0be12b529a0c0ac3` |

## Verification

`python -B docs/research/WP-0020/route/check_route.py` passed four tests on the frozen candidate. An earlier pre-freeze control errored while traversing a tuple assignment in the source-predicate AST check. Restricting that check to simple assigned names resolved it. A separate pre-freeze read of Windows development outputs (dev-ab-01 warm, short, dense and boundary) reproduced the original layout for seven pages. The only native values seen during development were public development examples and synthetic controls.

The four family commands below exited zero on source `b34c046e04ff98ddb0fb021ee8e8dade88a83126`. Both manifests were committed, pushed and reported to the coordinator before either route command. Re-executing these entry points into fresh temporary directories after the prediction freeze produced byte-identical manifests, decisions and predictions for H and A. The unmodified WP-0015 scorer source used by the synthetic join check has SHA-256 `1ceb36fe922ef63ea8cd9b2dc2ff55b48abe1193bb818430ddb1531f364f4bf7`.

```powershell
python -B docs/research/WP-0020/route/route.py manifest ../wp0020-data/windows H docs/research/WP-0020/route/evidence/H/manifest.json
python -B docs/research/WP-0020/route/route.py manifest ../wp0020-data/windows A docs/research/WP-0020/route/evidence/A/manifest.json
python -B docs/research/WP-0020/route/route.py route ../wp0020-data/windows H docs/research/WP-0020/route/evidence/H/manifest.json 7bc3c1ca418059ea97c9d1bb80295f2c50574f8d58e99fc3431ce1f103f0af5f ../wp0020-data/native docs/research/WP-0020/route/evidence/H
python -B docs/research/WP-0020/route/route.py route ../wp0020-data/windows A docs/research/WP-0020/route/evidence/A/manifest.json 5d2f9b31e43fc03854bca6ac08efac75fc82543311fa9f40b660d072a1d8a74a ../wp0020-data/native docs/research/WP-0020/route/evidence/A
```

The owned remote ref matched the full source, manifest and routed deliverable revisions at their respective freeze checks. Final canonical publication confirmation is supplied after commit to the coordinator.

## Limitations and handoff

This author assessed binding and deterministic replay only. Counts of changed values cannot establish correctness, damage to previously correct spaces or printed blanks, or serial elapsed time. No H/A truth or comparisons were accessed. No OCR engine, GPU or fresh family was used. /002 owns the frozen scorer joins and cost accounting. /003 independently rebuilds both manifests and predictions, checks all selected and nonselected transitions and costs, and reports to the coordinator. The reviewer has the exact input hashes, source, three pre-scoring publication points and all field witnesses.
