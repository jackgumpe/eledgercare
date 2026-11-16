# WP-0007 /009: bounded runtime accounting and supplemental recovery orchestration

- Report path: `docs/agent-reports/eld-rd-astra/WP-0007/009_2026-11-16_implementation_eld-rd-astra.md`.
- Reservation / exact authority: [INDEX](https://github.com/jackgumpe/eledgercare/blob/97e65bed170ad0be705347791a830d860a6a38fe/INDEX.md), kickoff `docs/kickoffs/WP-0007-eld-rd-astra-runtime-correction.md` and runtime-incident disposition at `97e65bed170ad0be705347791a830d860a6a38fe`.
- Category / author / publisher: implementation; eld-rd-astra, same native `/root/rd_astra`.
- Actual model / effort: inherited dispatched gpt-6-astra/high; backend checkpoint and backend session UUID not exposed. Earlier research/Q0/baseline authorship is preserved; no additional agent invocation.
- Environment: native Codex shell tools, Windows PowerShell, registered CPython 3.12.10 AMD64, isolated `-I -B` CPU subprocesses.
- Timestamp: 2026-11-16T06:29:55.395045+00:00.
- Repository / owned branch / worktree: private jackgumpe/eledgercare; `research/wp-0007-vanilla-baseline`; `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-baseline-astra`.
- Exact clean starting base: `69ee8796b9b86e7c0090ae91d9efc27999088a7a`.
- Approved coordinator merge: `f9ac2110ed1c6a9c22d528927320fdf84da7511a`, normal merge of exact release, no source conflict. Imported coordinator/reviewer material remains separately attributed.
- Initial correction source: `441fedcf4961a9ff3ce0010aac058f69d0157eed`; initial failed-check evidence `dcca35cc6fe23dcc82b947ff16e79fe16392f64a`.
- Final source deliverable: `f11fcd1141c08d49ac538858354f3b5d87277038`; baseline tree `21de152f436f76915855421feae486342860ed92`.
- Passing evidence publication: `8e391df0c1b4177c6d25644f8446d8e897ac8513`, same final baseline tree.
- Related immutable inputs: original source `f807e0ac737df4e9e0aeeb96f716afec57f58ff6`, prior /007 `e22c6730d19a6d616f0e7afb00b9416635799c16`, original run evidence `1d6a681f09b0eaf233f838c54465c36a042ec326`, checkpoint `69ee8796b9b86e7c0090ae91d9efc27999088a7a`; independent [diagnosis](https://github.com/jackgumpe/eledgercare/blob/03b9ed908f64e06e86e05397fd60275b7e3d4a10/docs/reviews/WP-0007/eld-baseline-reviewer/runtime-incident/checkpoint.md).
- Status / next owner: ready-for-review; same independent eld-baseline-reviewer, canonical /010. No author self-acceptance; /004 remains held.

## Outcome and boundary

Implemented the released minimum correction: safe live-directory accounting for disappearing enumerated children, structured caught supervisor errors, one exact prior-failure-bound supplemental dev schedule/scoring path, and the canonical /010 acceptance route. All **50 CPU tests pass** on the final freeze (37 applicable accepted tests plus 13 focused tests). Actual unchanged Q0 Heartbeat produced 2,389 writes during 10,584 successful directory scans over three seconds, without scan/writer errors; the owned thread joined.

The original run failure remains unchanged and its cause unproven. Independent diagnosis established a latent heartbeat temporary-file race, not the missing original traceback. This implementation fixes that reproduced defect without attributing the historical interruption conclusively to it. No model/GPU invocation, held-out content access, external runtime read/write, dependency change or new lease occurred.

## Implementation decisions

`runtime.directory_size` performs one no-follow root metadata read, requires a directory and rejects symlink/reparse roots. Each enumerated child receives one no-follow metadata read, reused for type/size. Only FileNotFoundError while reading an enumerated child or opening that already-enumerated child's vanished directory is tolerated. Root disappearance, invalid roots, reparse entries, non-disappearance I/O/permission failures and unsupported entry types still fail. Stable nested subtrees count completely. This is a live snapshot, not atomic accounting; changing temporary files can appear/disappear between observations. Existing caps/floor, call/session guards and process containment are retained.

A caught supervisor error preserves the original `SUPERVISOR_ERROR:` classification and adds `supervisor_error` with exception type, message, filename, errno, traceback and active phase. Existing job close /owned-child kill-and-wait cleanup remains. Pre-run release/root gates still fail before a run exists; this report does not claim persisted run diagnostics for gates that never created a run.

`release.RECOVERY_BINDING` freezes one optional `supplemental_recovery` object: author/dev only, `allow_test_content` false, fixture SYN-MP-01-v2-skew-pos4deg, prior evidence commit `1d6a681f09b0eaf233f838c54465c36a042ec326`, exact prior run-result path and SHA-256 `f6475d1bd2a40222ae2b3408360c7bf73542b164c2a9861c8dd5267b06540d5e`, original authority `a6f8f2a17fc8f3db68e11d2971423f78b2dc7861` and release path `docs/coordination/WP-0007/releases/author-dev.json`. The exact JSON shape is documented in the frozen README.

Validation reads only these immutable Git objects; it checks byte identity, original release equality, source/executing HEAD, complete ordered 15-call matrix, sole selected failed measurement and every other completed call. Completed/unknown/duplicate/heldout/arbitrary subsets, changed or missing prior evidence and mismatched authority reject. No free-form retry API was added.

Parent, worker and scoring orchestration use `released_schedule`: two existing excluded warmups plus exactly the failed fixture for the supplemental release. Ordinary full author split matrices and reviewer sentinels retain their rules. Supplemental scoring selects exactly that one expected document, retains failed/missing denominators and labels the output `supplemental_single_failed_dev` with lineage. Parser/reference/mapping/printed/typed score functions are untouched. Primary original 13 dev results remain immutable, including the failed document's zero credit. Supplemental results must never replace that row or silently change primary aggregates; final primary corpus results combine original dev with a separately released heldout phase and disclose the runtime revision boundary.

New runtime releases must bind `docs/agent-reports/eld-baseline-reviewer/WP-0007/010_2026-11-16_review_eld-baseline-reviewer.md`, a real subsequent review publication, new exact source/tree, clean executing HEAD and a new finite lease. Old /003 cannot authorize the new source; it remains valid for its original source. No future /010 SHA is fabricated. Historical /003 references in the README describe earlier preparation; the /009 section and release constant govern the new runtime route.

## Frozen verification and retained failure

[Final checks](https://github.com/jackgumpe/eledgercare/blob/8e391df0c1b4177c6d25644f8446d8e897ac8513/docs/evidence/WP-0007/eld-rd-astra/runtime-correction/f11fcd11/checks.json) record exact argv, interpreter, exit codes, source and 15 protected identities. All commands used the owned worktree explicitly; temporary tests used newly created ignored `.scratch/runtime-correction/<candidate>/` through subprocess TEMP/TMP/TMPDIR. The focused test blocks torch/transformers/triton/backend imports and imports only unchanged CPU Q0 Heartbeat support.

| Executed command / check | Actual result |
| --- | --- |
| `python -I -B qualification/baseline/tests/run_runtime_checks.py` at 441fedcf4961a9ff3ce0010aac058f69d0157eed | Exit 1. Original 37 tests pass; focused suite 9 pass /4 errors. The mocked scandir object implemented only a context manager, not the iterator interface that real os.scandir also provides. Actual concurrent heartbeat already passed (2,489 writes /10,570 scans). Complete failure stdout/stderr retained. |
| Test-only correction, then same helper at `f11fcd1141c08d49ac538858354f3b5d87277038` | Exit 0. The scandir double now implements both interfaces; runtime/release/scoring orchestration from the initial freeze is unchanged. Full accepted 37 and focused 13 tests pass. |
| Focused filesystem accounting | Stable nested/empty trees count exactly; metadata is read once without following links; disappearance after enumeration and after an actual owned-file removal is tolerated; disappeared child directories skip; missing/non-directory/disappeared roots, reparse metadata, PermissionError and other OSError propagate. |
| Actual Q0 heartbeat overlap | 2,389 beat writes /10,584 successful scans /3.0 seconds, no writer error, joined thread. Accelerated overlap confirms the correction under this CPU workload, not original runtime cause/cadence or exhaustive filesystem race absence. |
| Guards and cleanup | Existing cap/free-floor/time/stall guard tests and actual Windows owned-job child exit pass. Focused supervisor exception injection confirms structured error fields, job close and owned-child kill/wait, preserving 13 ordinary measured denominators. Its child is a test double; it is not a new CUDA worker test. |
| Recovery lineage negatives | Actual original Git binding passes. Changed digest/identity/missing evidence and completed/duplicate/unknown/heldout/mismatched prior records reject. Semantic mutation tests explicitly bypass the independently tested hash gate to exercise subsequent defenses; they do not fabricate accepted evidence. |
| Schedule/score/review binding | Normal author/reviewer schedules unchanged; supplemental has two excluded warmups and one measured fixture; mocked missing-output supplemental score retains exactly one document and all its expected field denominators. Original Git evidence bytes remain identical. Old /003 route rejects. |
| Protected identities | All 15 original tree/blob identities match both candidate checks, including seven immutable score/protocol/reference/job files, Q0, evaluation, product trees, original runtime-dev evidence and earlier author reports. |
| `git diff --check f9ac2110ed1c6a9c22d528927320fdf84da7511a f11fcd1141c08d49ac538858354f3b5d87277038 -- qualification/baseline` | Exit 0. Eight captured stdout/stderr blobs across the two freezes match committed sizes/SHA-256 exactly. |

No further broad testing or runtime execution was performed after the relevant checks passed. No original score was recomputed or changed in this response; unchanged core identities and the focused orchestration test support preservation. Independent /010 must inspect/reproduce the new source and coordinator continuation design.

## Complete inventory and attribution

The approved merge imported **115 coordinator/reviewer paths**, with no author attribution transfer. [Reconciliation inventory](https://github.com/jackgumpe/eledgercare/blob/8e391df0c1b4177c6d25644f8446d8e897ac8513/docs/evidence/WP-0007/eld-rd-astra/runtime-correction/f11fcd11/reconciliation.json) lists every imported path/action from base to merge separately from the seven authored source paths below. Imported review evidence and product coordination documents were not edited by this author.

| Action | Authored source path |
| --- | --- |
| M | `qualification/baseline/README.md` |
| M | `qualification/baseline/baseline.py` |
| M | `qualification/baseline/release.py` |
| M | `qualification/baseline/runtime.py` |
| A | `qualification/baseline/tests/run_runtime_checks.py` |
| M | `qualification/baseline/tests/test_baseline.py` |
| A | `qualification/baseline/tests/test_runtime_correction.py` |

The separate evidence commits add these **11 exact paths** (five initial failure records and six final verification/reconciliation records):

- `docs/evidence/WP-0007/eld-rd-astra/runtime-correction/441fedcf/checks.json`
- `docs/evidence/WP-0007/eld-rd-astra/runtime-correction/441fedcf/test_baseline.py.stderr.txt`
- `docs/evidence/WP-0007/eld-rd-astra/runtime-correction/441fedcf/test_baseline.py.stdout.txt`
- `docs/evidence/WP-0007/eld-rd-astra/runtime-correction/441fedcf/test_runtime_correction.py.stderr.txt`
- `docs/evidence/WP-0007/eld-rd-astra/runtime-correction/441fedcf/test_runtime_correction.py.stdout.txt`
- `docs/evidence/WP-0007/eld-rd-astra/runtime-correction/f11fcd11/checks.json`
- `docs/evidence/WP-0007/eld-rd-astra/runtime-correction/f11fcd11/reconciliation.json`
- `docs/evidence/WP-0007/eld-rd-astra/runtime-correction/f11fcd11/test_baseline.py.stderr.txt`
- `docs/evidence/WP-0007/eld-rd-astra/runtime-correction/f11fcd11/test_baseline.py.stdout.txt`
- `docs/evidence/WP-0007/eld-rd-astra/runtime-correction/f11fcd11/test_runtime_correction.py.stderr.txt`
- `docs/evidence/WP-0007/eld-rd-astra/runtime-correction/f11fcd11/test_runtime_correction.py.stdout.txt`

This canonical /009 report is the only subsequent authored path. No shared INDEX/CURRENT, original canonical report, pure score source, Q0/model/dependency/corpus or product code was edited. All seven source-path changes are within the kickoff's runtime/orchestration/tests/README scope. The complete base-to-evidence inventory is 115 imported paths +7 source paths +11 evidence paths; report metadata follows separately.

## Review map, limits and handoff

Review the [source diff](https://github.com/jackgumpe/eledgercare/compare/f9ac2110ed1c6a9c22d528927320fdf84da7511a...f11fcd1141c08d49ac538858354f3b5d87277038), especially `directory_size`, `supervisor_diagnostic`, `validate_recovery`, `released_schedule` and `score_run`, against the exact coordinator disposition and independent diagnosis. Source tree `21de152f436f76915855421feae486342860ed92` is unchanged by evidence/report publication.

No external original runtime root was touched: original records were accessed through pinned Git evidence. CPU tests create only owned scratch; no installations, GPU query/allocation/inference, heldout content, Q0 source or model/library writes occurred. Filesystem type/reparse rejection includes deterministic metadata test doubles; the real heartbeat concurrency and accepted actual job-child test are identified separately rather than overstated as full runtime qualification.

Next owner is same independent eld-baseline-reviewer /010 for this implementation and coordinator recovery design. New GPU/model runs, heldout access, supplemental execution and final /004 remain held until separate acceptance/release. The returned original lease cannot be reused. A published report is not self-acceptance.

Normal owned-branch push and exact-origin verification follow this report commit. The handoff supplies the report publication SHA and remote-object confirmation separately; this report does not claim its own commit SHA.
