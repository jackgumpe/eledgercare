# Final independent runtime correction reconciliation

Accept the bounded runtime correction at source
`ae790497f3fdd10573e8179757416bc2d1736250`, mapping_v2 tree
`8fd68c96bb18ca0177f227ad9a82505090d997b0`. F011-01 is resolved on this
candidate. Source `b60624ac7a0ae23540ab019b63d7a7e904fb1c36` remains the
earlier rejected candidate; no old evidence or finding is rewritten.

The accepted setup gate and actual worker entry independently check the Windows
bare-Git lookup order against the audited explicit executable. Earlier PATH,
current-directory and combined shadows are rejected before subprocess pin
verification. The clean controls complete real frozen pin verification. This is
a snapshot check in the qualified Windows environment, not an atomic filesystem
lock or a guarantee against concurrent hostile filesystem changes.

## Exact review and helper identities

- Authority: `5cbf8ffe9dc8c5b04d5bc2fff43bb63b4fdad916`.
- Final candidate merge: `fed86dc398eb7d9d1c8d270d17fbdb6e7b117b74`, actual
  2026-11-17T19:07:05.1753309Z, tool `ba5a27`.
- Final author publication: `10a635d2b9292944a54221e72f4c82566bcb464b`;
  deliverable `4782b15e87a48cfc008ab82f3fab39a337461625`;
  inventory `63468b49a1d8ffce207894036b390746ca1657e8`.
- Publication merge: `c599e019908f6ff1c14bce02680ef6f1196650da`, tool `496527`.
- Selection probes frozen at `8be8176432e2c43f359b803145bc7ed40d506ee7`.
- Final standard/worker probes frozen at `0ee395d7fb1df1a036a974dd890babc3d619c9c3`.
- Source audit and recovery binding controls frozen at
  `76741706e58467fedfa6bc142551c1c1264388e0`.
- Final publication audit and exact collector frozen at
  `20a65e5465d7e8dc4e2c27b48efd0f011518a293`.

## Independently executed checks

Complete commands and tool outcomes are in
[tool-receipts.json](../final-evidence/attempt-1/tool-receipts.json). All final
checks passed on their first execution; expected child failures remain explicit.

| Check | Actual result | Full evidence |
| --- | --- | --- |
| Four real lookup-selection children | Clean pins complete; three shadows reject before a pin subprocess. | [Selection summary](../final-evidence/attempt-1/selection/summary.json) |
| Twelve real restricted-environment release/pin children | Original missing Git reproduced; clean corrected pins/release boundary succeed; wrong/missing/relative Git, forbidden environment, outside cache, Git configuration and altered/missing pin controls reject. | [Standard summary](../final-evidence/attempt-1/standard/summary.json) |
| Four actual worker-entry children in real named Windows jobs | Clean reaches read_release once and genuine pins; path/cwd/both reject before read_release. Fixtures are introduced after the parent snapshot, so the worker recheck is exercised. | [Worker summary](../final-evidence/attempt-1/worker/summary.json) |
| Exact source audit and three affected existing unit methods | Only four authorized qualification paths differ; worker/model body otherwise unchanged; all three affected methods pass. | [Source result](../final-evidence/attempt-1/source/result.json) |
| Four recovery-helper binding/path tests | Exact three source constants and owner-specific routes only; old helpers unchanged; allowed paths accepted and wrong owners/old007/other attempts/descendants/unsafe paths rejected. | [Binding execution](../final-evidence/attempt-1/recovery-binding/execution.json) |
| Immutable final013 publication audit | 139 artifacts, 4,945 protected paths, 126 copy hashes, 433 tree inputs, 12 proof objects and two executable hashes verified; 16 report links resolve in the integrated reviewer worktree. | [Publication result](../final-evidence/attempt-1/publication/result.json) |

The total final independent child count is 20. The twelve standard and four
worker checks use only narrow CPU release-object/storage overlays and stop after
genuine frozen pins; future unseal, corpus, host and lease proofs are not invented
or accepted. Real qualified Python, Q0 child environment, process creation
identities and Windows job join/cleanup are exercised. Model/renderer/backend
imports are denied by the CPU probes. These checks create no actual research
runtime root and perform no live GPU/model/process observation.

The author's 26 real children and 61 tests are authenticated and inspected as
author evidence, not relabeled reviewer execution. Three affected methods were
independently rerun; unchanged mapping/scoring suites were not repeated.
The optional root final-preservation helper at
`e8da1aab18628a666506242035a179a7151b0439` was inspected read-only, not executed.

## Preservation, failures and comparison preparation

The complete protocol subtree, bare-Git helper, mapper, policy/scorer,
normalization, release validator, Q0/B0/v1/coverage and admitted corpus remain
unchanged. Runtime protocol SHA256 is
`ef648a3cd52df16ed6ed352e666ffedf789148100d640e2582cf13f76b6f9783`; its only
change from original source is the accepted review route to /011.

The original missing-Git /007 run and its twelve unavailable primary packets
remain separate. Its completed CPU comparison is published at
`7f8cf7db29156c6e5f22a2d1ac320debacdf2d50`; no observed extraction quality,
gains, losses or successful policy abstention follows from absent model outputs.

F011-01's earlier shadow probe is retained at
`64a456db726080c124e0188e11b3445c02a1d754`. Its real pin call selected the
mutable shadow and Windows returned 216; the reviewer's parent expected 193
and exited 1. That expectation error is a failed reviewer check, separate from
the demonstrated lookup defect. No missing parent execution receipt was
fabricated. The original preparation, complete finding packet and final
selection-preparation publications remain unchanged. Earlier packaging incidents
and their corrections stay in their respective evidence namespaces.

The original and original007-v2 comparison helpers are immutable. New
`008/compare_published_recovery012.py` was frozen at
`76741706e58467fedfa6bc142551c1c1264388e0`, before any recovery model output.
All comparison/scoring logic remains identical. The only changes bind the final
source/tree/runtime protocol and exact author012/reviewer run routes. Future
immutable release/spec/return objects remain required. No recovery comparison
has run and no sentinel lease is granted by this review.

The collector preserved all 120 original final CPU files (248,689 bytes),
including fixture bytes, exact stdout/stderr and original descriptors. Executable
fixtures are invalid data, copied with `.fixture-bytes` suffixes; no fixture code
ran. The existing owned `-text` attributes preserve raw bytes in Git. The
[collection](../final-evidence/attempt-1/collection.json) accounts for every file,
with no retained-only original. The final inventory separately accounts for
helpers frozen before the merged publication base and all subsequent additions.

Author013's own packaging correction (initially omitted ignored fixture copies)
is retained in its report/evidence. Its full final inventory and all 126 copies
were verified. The cross-publication finding link exists at its immutable reviewer
revision and resolves after normal integration; its absence in the author's
isolated tree is not represented as an absent finding or repaired historical report.

The Windows lookup rationale is consistent with Microsoft's
[CreateProcessW documentation](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw).
Application directory, parent current directory and system locations precede
PATH. The worker snapshot supplements the pre-launch snapshot; neither locks
those locations against future mutations.
