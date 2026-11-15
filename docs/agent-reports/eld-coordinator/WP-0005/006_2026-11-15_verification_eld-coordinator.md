# WP-0005 / 006: Independently reproduced unmodified-model runtime qualification

- Report path: `docs/agent-reports/eld-coordinator/WP-0005/006_2026-11-15_verification_eld-coordinator.md`
- Sequence reservation: WP-0005 /006 in `INDEX.md`, original packet base `df9a2b50894f01987d779d7f9ae805794503ce6f`.
- Category: verification
- Author / agent ID: eld-coordinator, receiving Codex session `01a1d895-c605-7ab2-b7ec-c3159c0634ba`.
- Actual model / effort: not exposed.
- Execution environment: Windows PowerShell, host CPython 3.12.10; actual delegated sessions disclosed below.
- Published by: eld-coordinator.
- Timestamp: 2026-11-15T21:46:24Z
- Repository / branch: private `https://github.com/jackgumpe/eledgercare`, `coordination/bootstrap`.
- Base revision: `df9a2b50894f01987d779d7f9ae805794503ce6f`.
- Deliverable revision: `c5610e306a9af64e75c5501e6cf7a6f7ec4835bb`.
- Preservation evidence revision: `c881352e543949e83747b8cf4c9ea6403ce3ad45`.
- Integration revision: `8bb643ce79f3728fcf90b1ad4e08e9ab87e76982`.
- Previous report: WP-0004 /006, publication `5a7efb16c888dc57fe981460d75160ffbc81eaa7`.
- Related reports: author WP-0005 /004 `72fffbcbfa47f3c93425d9de5f338e511df7da3e`; independent /005 `848fe70bd6d6fce9c958f11b76102d2fdfad77d4`; accepted source-correction /011 `c8daa97c5be6bc67931b215652a7a0f6ced621ef`.
- Status: accepted.
- Next owner: Jack; WP-0005 has no remaining execution or acceptance work.

## Summary

The unmodified `baidu/Unlimited-OCR-2@0480966938291445591f69f08a13b041c073a96a` completed both the author trial and a separate independent reproduction on the pinned Windows/RTX 5070 Ti stack. Each actual run returned `QUALIFIED_RUNTIME_OBSERVATION`: all six checks passed with no failures, all six native calls stopped normally with expected page counts, and both measured repeats matched exactly for each fixture. All four measured outputs also match across the two sessions in token IDs and raw text bytes.

Independent /005 accepted the bounded runtime result on exact published revisions. The coordinator inspected the actual source/evidence, reconciled report-only inaccuracies, integrated the publications normally, and verified preservation. Both GPU leases are returned with every observed model-worker identity absent. The environment and original raw runs are retained; no further model run is pending.

This is runtime qualification on admitted synthetic dev F01/F07 v0-clean fixtures, not OCR accuracy scoring or production readiness. No holdout or expected-value data was accessed. E1-E3, production OCR integration, training, customer data and deployment remain outside this completed packet.

## Objective and acceptance criteria

Carry Jack's authorized trial through staged isolated acquisition, one fixed unmodified author run, a separate full reproduction, explicit concurrency-1 resource ownership/return, independent review, normal GitHub publication and coordinator disposition. Keep the original model, weights, library versions, fixed protocol and fixture bytes unchanged. Preserve existing application/corpus work and historical authorship. Report failures and unobserved limits honestly rather than assigning an accuracy score.

## Exact identities and independence

| Item | Exact identity |
| --- | --- |
| Accepted harness source | `41d6204648e4115ab197507d1a22f6d5c7f3e784`; 42 core files preserved |
| Author execution / runtime evidence / report | `9e73ef86600b5e16f74b056676a6d3a4f1474058` / `6e5f87fe4d0e19338a387bb5870efd083b2b491c` / `72fffbcbfa47f3c93425d9de5f338e511df7da3e` |
| Reviewer execution / evidence / report | `c8daa97c5be6bc67931b215652a7a0f6ced621ef` / `acf2ce43ccb3c22883e9961f2c763a2ece11b54f` / `848fe70bd6d6fce9c958f11b76102d2fdfad77d4` |
| Author identity | `eld-q0-harness`, Carbon `bd92ddc3-af60-4096-b683-65386d81b718`, actual init `gemini-4-carbon-high`, explicit CLI effort high |
| Reviewer identity | `eld-q0-reviewer`, separate Carbon `0815536f-045a-4112-8a89-ebf0e0cc782f`, actual init `gemini-4-carbon-high`, explicit CLI effort high; no harness authorship |
| Original implementation | Opus `/002`, session `04e0efba-5292-4cae-b922-1517dee7bbed`; preserved, not relabeled as Carbon work |
| Protocol / dependency lock | SHA-256 `dd8a7dc38c2a0c46103f6667f522656a2dddf5882727c18bf7b6b5426c5e2309` / `d8eeaf0fe838d9df5728f17fcbacc8b504d98b79644a524b4faa705d97c49e6e` |
| Model manifest | SHA-256 `085ac7ba1e25a7300846de18bdac19c7f9612bf417041643beff6a9cab6b8ea8`, 18 runtime objects and a separate notice |
| Runtime | CPython 3.12.10, torch 2.13.0+cu130, torchvision 0.28.0+cu130, transformers 4.52.1, pypdfium2 5.15.2 / PDFium 159.0.8149.0 |
| GPU | RTX 5070 Ti, `GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d`, driver 621.01, sm_120 |

Jack explicitly permitted existing-credit use or Carbon continuation. Direct Claude remained quota-blocked; the alternate Opus attempt failed for insufficient provider credits before tools. This was not proof of Jack's overall Claude balance. Carbon continued under that authorization without changing accounts, billing or global settings. Distinct author/reviewer sessions and original Opus/Astra attribution were retained. Accepted harness integration/metadata corrections are documented in the immutable /008-/011 chain and coordinator acceptance receipts; they did not patch the model or weights.

## Change inventory

[Exact deliverable inventory](../../../coordination/WP-0005/final-disposition/change-inventory.tsv) accounts for every base-to-deliverable path. The inventory matches all **542 changed paths** (539 additions and three routing modifications) in the committed base-to-deliverable diff. After that deliverable, `c881352e543949e83747b8cf4c9ea6403ce3ad45` adds only `docs/coordination/WP-0005/final-disposition/preservation.json`. Canonical report publication then adds only this report; the subsequent `INDEX.md` and `CURRENT.md` receipt records its publication SHA. These later verification/report/routing files are metadata, separately identified from the frozen deliverable inventory.

| Scope | Change and purpose |
| --- | --- |
| `qualification/q0/**` | Pinned runtime research, harness, protocol/locks/manifests and actual author stage/runtime evidence; original model is external and unmodified |
| `docs/reviews/WP-0005/**` | Separate reviewer's source, CPU and real-runtime verification evidence |
| `docs/coordination/WP-0005/**` | Scoped releases, identity audits, raw observations, report reconciliation, final comparison and disposition |
| `docs/kickoffs/WP-0005-*`, `AGENTS.md`, `CURRENT.md`, `INDEX.md` | Authorized roles, exact worktrees/revisions, dated routing and publication/lease receipts |
| `docs/agent-reports/*/WP-0005/**` | Immutable, separately attributed canonical publications; no duplicate packet sequence |
| External `C:\Users\jackg\eLedgerCare-Q0\WP-0005` | Retained task venv, verified wheelhouse, pinned model/notice and separate author/reviewer runs; no weights/wheels/private agent transcript committed |

## Verification and actual results

[Direct comparison](../../../coordination/WP-0005/final-runtime-observations/run-comparison.json) binds both outcomes/supervisors by SHA-256 and contains per-call timing, tokens, pages, memory, cache/fallback and storage observations. The coordinator checked every recorded native raw text/token digest and compared all four measured outputs across sessions. Independent reviewer evidence separately reproduces the acquisition/model/render checks and full fixed trial.

| Actual check | Result / evidence |
| --- | --- |
| Acquisition/install | 32 hash-locked wheels; offline no-index/no-deps install, unchanged bundled pip 25.0.1, exactly 33 installed distributions, pip check pass, longest installed path 234; author and reviewer actual verification passed |
| Model/render identity | All 18 pinned runtime objects and separate notice verified; actual four CPU rasters match; post-run model and module-cache checks passed |
| Author run `20261115T202627Z-eb5bf7da` | 1235.281s; six checks pass; six calls stop, no truncation/OOM/stall/page-count failure |
| Reviewer run `20261115T210422Z-565e2de9` | 1266.187s; six checks pass; same fixed six-call sequence, independent output directory and process |
| Native runtime path | Expected Triton-import-failed dense fallback, FP32 decode observations and growing DynamicCache, no ring-buffer marker; forbidden save/eval path never entered |
| Repeatability | Both within-session warm repeats match; all four measured author/reviewer token-ID lists and raw text bytes match exactly |
| Lease closure | Author launcher 31816 / worker 30992 absent; reviewer launcher 30436 / worker 30484 absent; no Q0 child or active lease remains; desktop processes untouched |
| Integration preservation | Frozen checker passed: all 322 protected base files and 42 accepted core files retain exact Git mode/type/blob identity; allowed additions only; no duplicate canonical sequence. [Receipt](../../../coordination/WP-0005/final-disposition/preservation.json) |
| Publication | Normal owned pushes and exact remote ref/ancestry checks passed; no force push or history rewrite |

| Fixture | Author measured seconds | Reviewer measured seconds | Output |
| --- | --- | --- | --- |
| F01: one page | 120.231 / 119.508 | 123.832 / 124.947 | 1122 tokens, one page, exact repeat/cross-session match |
| F07: three pages | 273.432 / 278.528 | 286.316 / 282.803 | 2558 tokens, three pages, exact repeat/cross-session match |

The F01 excluded warm-up differs in bounding-box coordinates from its measured outputs; non-coordinate text matches. Warm-ups are excluded by the frozen protocol and this difference is preserved, not hidden. Author /004 prose corrections (native fallback, exact 13/34 evidence grouping, coordinate delta up to 10 native units rather than a claimed 1 pixel, and pre-host Python flags) are recorded in the [publication handoff](../../../coordination/WP-0005/gpu-reviewer-release/author-publication-handoff.md) and independently reconciled. They did not change source or raw outcomes.

Independent /005 also has three prose inaccuracies, reconciled in the [final disposition](../../../coordination/WP-0005/final-disposition/README.md) without altering the report: its own check 14 records **36 paired coordinate tuples**, not 37; the metadata-acceptance receipt was first published at `e0ee634f6a92624c8c305c1c8730f79e95b93647`, not the preceding integration `4317ea99bb85b96983c7dc3a0ed828a0a6a6ed1f`; and desktop WDDM observations do not isolate the cause of timing variance or establish a general zero-effect/determinism claim. The actual matching outputs and independent bounded verdict remain valid.

The coordinator ran `python.exe -I -B docs/coordination/WP-0005/verify-preservation.py --target c5610e306a9af64e75c5501e6cf7a6f7ec4835bb --accepted-harness 41d6204648e4115ab197507d1a22f6d5c7f3e784` using host `C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe`: exit 0, `passed: true`, no protected/core differences, no unexpected additions, ten canonical reports with no duplicate packet sequences before /006. The checker itself is unchanged from `b2ed140405e13211495c2ae64d1ddd6e570243c9`.

`git diff --name-status --no-renames df9a2b50894f01987d779d7f9ae805794503ce6f c5610e306a9af64e75c5501e6cf7a6f7ec4835bb` matched every inventory row. `git diff --name-status acf2ce43ccb3c22883e9961f2c763a2ece11b54f 848fe70bd6d6fce9c958f11b76102d2fdfad77d4` confirmed the single canonical reviewer report addition; actual `git show` bytes match the integration. `git merge-base --is-ancestor` confirmed author, reviewer, evidence and accepted-core ancestry. Normal `git push origin coordination/bootstrap` and `git ls-remote origin refs/heads/coordination/bootstrap` confirmed exact remote `c881352e543949e83747b8cf4c9ea6403ce3ad45` before this report's publication; its own publication confirmation belongs in the final receipt.

Unchanged broad unit suites were not rerun for evidence/report-only changes. Real native execution and independent reproduction are decisive here. No accuracy/ground-truth scoring, holdout evaluation, optional acceleration backend, CPU fallback, E1-E3 treatment or production integration was executed.

## Review map

The [final publication receipt](../../../coordination/WP-0005/final-disposition/reviewer-publication-receipt.json) binds exact author/reviewer origin refs, report bytes and the prior 96-blob audit. Read the [author /004](../../eld-q0-harness/WP-0005/004_2026-11-15_verification_eld-q0-harness.md), [independent /005](../../eld-q0-reviewer/WP-0005/005_2026-11-15_review_eld-q0-reviewer.md), and [independent runtime evidence index](../../../reviews/WP-0005/eld-q0-reviewer/runtime-005/README.md) at the exact revisions above. Raw comparison and final preservation receipts are linked in the verification section.

## Limits and disposition

Desktop WDDM applications remained active; whole-GPU memory/utilization and timings include that confounder, with per-process GPU memory reported N/A. PyTorch allocator metrics are recorded separately. Observer callback timing is a lower bound on instrumentation overhead; no internal CUDA-kernel profiler attribution is claimed. OS/pagefile growth outside the task root is not bounded by its storage budget. The explicit `torchvision-local-sha256-TOFU` exception remains disclosed; no publisher wheel signature is claimed.

These limits are recorded in the accepted bounded baseline. The accepted Q0 deliverable and preservation evidence are **integrated and published** for runtime qualification only. This final report follows in its own publication commit. No unresolved disagreement or remaining WP-0005 execution is carried forward. The two actual run directories and task environment remain available for inspection. Jack owns any later milestone decision; no follow-on treatment or product release is inferred.
