# WP-0013 /013: Reject Windows bare-Git shadows before frozen pin verification

- Report path: `docs/agent-reports/eld-mapping-author/WP-0013/013_2026-11-17_implementation_eld-mapping-author.md`
- Sequence reservation: [INDEX.md](../../../../INDEX.md), WP-0013 /013; exact root [kickoff](../../../kickoffs/WP-0013-runtime-correction-013.md)
- Category: implementation
- Author / agent ID: eld-mapping-author, continuing native `/root/mapping_author`
- Actual model / effort: backend/applied effort not exposed; existing requested xhigh
- Execution environment: Windows / PowerShell; real qualified Python312 and Q0 restricted CPU subprocesses
- Published by: author on owned branch
- Timestamp: 2026-11-17T19:11:55Z
- Repository / branch: jackgumpe/eledgercare / `research/wp-0013-vocabulary`
- Owned worktree: `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-vocabulary-author`
- Base / correction authority: `5cbf8ffe9dc8c5b04d5bc2fff43bb63b4fdad916`
- Frozen tested source/helpers: `ae790497f3fdd10573e8179757416bc2d1736250`
- Mapping_v2 tree: `8fd68c96bb18ca0177f227ad9a82505090d997b0`
- Runtime protocol SHA256, unchanged from010: `ef648a3cd52df16ed6ed352e666ffedf789148100d640e2582cf13f76b6f9783`
- Capture helper freeze: `7739b7cefac40badb215557ccad256834ae24630`
- Final inventory helper freeze: `d2bc93bad11e10f49f8ffde572a040f72464368d`
- Deliverable revision: `4782b15e87a48cfc008ab82f3fab39a337461625`
- Inventory / metadata revision: `63468b49a1d8ffce207894036b390746ca1657e8`
- Previous report: [author010](010_2026-11-17_implementation_eld-mapping-author.md), publication `bd59cb57ad8f621ec98762b8bfdd76b3eee26e6f`
- Related evidence: [F011-01](../../../reviews/WP-0013/eld-mapping-reviewer/011/findings/F011-01.md), publication `64a456db726080c124e0188e11b3445c02a1d754`; complete finding packet `7cbb53ede74c2aa79ef9411d388bee61be813d05`
- Status: ready-for-review
- Next owner: independent eld-mapping-reviewer final011; root owns any later recovery012 release

## Summary

F011-01 correctly demonstrated that /010's environment audits did not bind bare
Git selection: an earlier mutable PATH candidate was selected despite a valid
explicit Git binding. This correction fails closed on a mismatched Windows
search candidate and repeats the guard in the actual worker before frozen
`read_release` pin verification. The isolated configuration and every mapper,
protocol, scorer, corpus and model setting remain unchanged.

The frozen candidate passed26 genuine restricted-child controls and61 existing
CPU tests. Old PATH/current-directory shadows reproduced Windows216; corrected
setup and actual worker entry reject them before pin verification. Complete
evidence and preservation checks pass. These are author checks; independent
final011 remains the acceptance gate. No model, renderer, live observer, fresh
scoring or recovery inference ran.

## Objective and acceptance criteria

Resolve the one independently demonstrated runtime lookup defect while retaining
original007 and010, actual Windows resolution behavior, pin/environment guards,
frozen policy/model/corpus and independent review. Root released only this CPU
correction. The implementation, genuine control evidence and complete publication
are ready; no runtime lease or recovery authority is inferred.

## Change inventory

| Path | Change |
| --- | --- |
| [runtime_git.py](../../../../qualification/mapping_v2/runtime_git.py) | New narrow snapshot guard for bare Windows `git.exe` lookup; no executable launch |
| [runtime.py](../../../../qualification/mapping_v2/runtime.py) | Validate lookup after restricted PATH construction and again in actual worker after owned-job join/before `read_release` |
| [test_runtime.py](../../../../qualification/mapping_v2/tests/test_runtime.py) | Use a real validated Git binding in the otherwise synthetic supervisor fixture; worker-body preservation permits exactly the new guard block |

The [complete inventory](../../../research/WP-0013/eld-mapping-author/013/deliverable-inventory.json)
accounts for139 changed paths: two modified existing files and137 additions.
All other4,945 base files retain exact mode/type/Git blob identities. New research
files comprise frozen probes/publication helper, dossier, byte-preserving
attributes and complete evidence under owned013. The inventory and four actual
verification receipts were committed afterward at63468b49, then this report.
Shared routing and prior published author/reviewer evidence are untouched.

External effects are owned ignored CPU scratch and explicitly owned test child
processes/jobs. Invalid-image fixture bytes are retained and archived with
`.fixture-bytes` suffix. No fixture code executed, no executable was installed,
and no live runtime root or other owner's process was changed.

## Decisions and rationale

The new guard enumerates the actual application-image directory, actual caller
current directory, Windows system directories and explicit restricted PATH. The
first existing `git.exe` candidate must equal the normalized absolute audited
Git path. Missing/ambiguous/relative PATH entries and inaccessible locations fail
closed. The guard does not rely on `shutil.which`, PATHEXT or a shell lookup.
This corresponds to the documented non-shell bare-name lookup order in
[Microsoft CreateProcessW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw).

The worker performs the check with its own loaded executable and caller cwd,
before the unchanged frozen verifier. A requested child cwd does not replace
the caller cwd during that selection; real controls cover this distinction.
The guard is a filesystem/environment snapshot, not an atomic lock against
concurrent replacement after validation. Its scope is the qualified Windows
runtime and cooperative owned-worktree/lease boundary. No stronger guarantee is
claimed. The [dossier](../../../research/WP-0013/eld-mapping-author/013/README.md)
records the exact search and test limitations.

No accepted protocol/common helper, release validator, mapper alias/guard/policy,
scorer/normalizer, Q0/B0/v1/coverage, corpus, model or call setting is changed.
Runtime protocol remains exactly010's version with independent report route011.
The remainder of the worker body is unchanged, and no global monkeypatch or
pin-check bypass exists in production.

## Verification

Frozen command:

```text
python -I -B docs/research/WP-0013/eld-mapping-author/013/run_checks.py --out .scratch/wp0013-runtime-shadow/attempt-1
```

Actual run19:06:57.1640092Z–19:07:19.3059598Z, wrapper33676, tool6512/final998211,
exit0. [Capture receipt](../../../research/WP-0013/eld-mapping-author/013/evidence/capture-attempt-1/execution.json)
and original stdout/stderr/tool receipts are retained.

| Control | Actual outcome | Evidence |
| --- | --- | --- |
| Original007 missing bare Git | Expected FileNotFoundError/exit1 reproduced | [All26 results](../../../research/WP-0013/eld-mapping-author/013/evidence/attempt-1/results.json) |
| Corrected real pin verification and full release boundary | Exit0; actual pins/trees/cleanHEAD/hashes/contracts pass, with explicitly synthetic future proof reads | Same full results |
| Old010 earlier PATH/caller cwd/both shadows | Explicit trusted Git exit0; actual frozen verifier raises Windows216 in all3 cases | [Old cwd control](../../../research/WP-0013/eld-mapping-author/013/evidence/attempt-1/owned/old_cwd_shadow/runs/author/probe/probe.json) and sibling cases |
| Corrected setup earlier PATH/caller cwd/both | Expected PermissionError before launching any shadow | Same full results |
| Actual worker clean/earlier PATH/caller cwd/both | Real owned-job joins; clean reaches unchanged stale-release rejection with1 `read_release` call; shadows reject with0 calls | [Worker cwd control](../../../research/WP-0013/eld-mapping-author/013/evidence/attempt-1/owned/worker_cwd_shadow/runs/author/probe/probe.json) and sibling cases |
| Wrong/missing pins, wrong/missing/relative/mutable Git, forbidden environment/config and invalid release bindings | All original guards reject as expected | Same full results |
| Existing affected/public CPU suite |61 passed,0 failures/errors/skips | [Unit results](../../../research/WP-0013/eld-mapping-author/013/evidence/attempt-1/unit-tests.json) |
| Frozen capture and final inventory | Both exit0;126 original copies,433 declared source/corpus input files,12 proof/original-source objects,2 executable hashes; all publication bytes verified | [Copy manifest](../../../research/WP-0013/eld-mapping-author/013/evidence/copy-manifest.json), [inventory receipt](../../../research/WP-0013/eld-mapping-author/013/evidence/publication-inventory/execution.json) |

Every actual child records argv, original/actual environment, launcher/worker
PID and creation identity, times, observed exit and separate streams. Import
blocking prohibits model/renderer/CUDA backend loading. Expected negative exits
are retained; no unexpected CPU control failed or was rerun. Existing CPU job
tests clean their owned children; fake observer tests never query hardware.

Three old-shadow controls extract only the exact immutable010 lookup function
from its Git object and record its source hash. The independently published
parent's193-versus216 assertion failure is retained as a failed reviewer control;
it is not relabeled a pass. New controls accept the documented invalid-image
error class and retain actual216 observations.

The full-release positive overlays exactly three labeled CPU-only future-proof
reads for release/review/unseal, retaining real pin/tree/status/hash/contract
checks and existing authentic proof objects. Four actual-worker controls change
only the test-owned runtime-root configuration and add a delegating release-call
counter; actual owned-job joining, audits, lookup and original release rejection
run. These test-only interceptions are explicit in receipts, not production
patches or runtime authority. No historical/full fresh scoring rerun was needed.

## Publication limitations and preserved failures

Capture7739b7c copied126 originals. The first evidence checkpoint3ff3257 omitted
six copied fixtures beneath ignored `venv` paths from Git staging. Inspection
detected that omission before final inventory/report. Checkpointd2bc93b adds the
exact six owned files and strengthens the frozen inventory helper to require
every copied path/byte in Git. That history is retained. Final verification
passes all126 copies; no model/source test was rerun for packaging.

Original007 still has zero model calls and all12 primary/255 policy opportunities
unavailable. Original010 still records its independently demonstrated selection
defect. Neither is overwritten or replaced by this CPU correction. No claim of
mapping quality, atomic filesystem assurance, hardware exclusivity, recovery
completion or production promotion follows.

## Handoff

Independent final011 should reconcile exact sourceae790497, full tree8fd68c96 and
deliverable4782b15 against this packet and the immutable finding. Root reported
provisional independent controls passing on that source; this report does not
substitute for canonical acceptance. Root separately binds any new unseal proof,
clean executing HEAD, fresh ownership observation and recovery012 lease.
Normal owned publication and exact-origin confirmation follow this report commit;
the full publication SHA is sent to root separately. No inference is released.
