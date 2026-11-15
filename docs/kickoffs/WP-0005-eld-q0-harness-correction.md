# WP-0005 /008: bounded harness correction and fresh validation

Authority: Jack's Q0 delegation and subsequent instruction to use available Claude credits or Carbon to continue. The original Claude Pro route still rejects requests at its five-hour limit. The existing secondary agy.exe route successfully returned READY as **claude-opus-5-5-high**, explicit high effort, at 2026-11-15T17:27:03Z (probe 223c23f4-daa4-4cfe-bbca-053db07a82bf, exit 0). Which balance this provider bills is not exposed; no billing settings or credentials changed. A NEW Opus conversation on this available route will execute this assignment and be recorded at init.

## Binding

- Stable author role: **eld-q0-harness**. Original Claude Code author conversation 04e0efba-5292-4cae-b922-1517dee7bbed authored /002 and is stopped. Preserve that authorship; the fresh AGY Opus conversation authors only this correction and its own evidence/report.
- Repository https://github.com/jackgumpe/eledgercare, private; owned branch **qualification/wp-0005-harness**, owned worktree **C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-harness**.
- Full clean correction base **2a52ea58fae2badcb4e9ef47d1cb416c006edca4**. Original WP-0005 base remains df9a2b50894f01987d779d7f9ae805794503ce6f; distinguish these.
- Reviewed initial candidate **84cef5ef30685ffee46281fefc5fd1356dbc1876** and evidence **0331efd71ef17e5485adac5a53d864c6d96e8f4a**. Canonical /002 is immutable.
- Reserved report **docs/agent-reports/eld-q0-harness/WP-0005/008_2026-11-15_implementation_eld-q0-harness.md**.
- Next owner: separate uninvolved Carbon reviewer, role eld-q0-reviewer, for reserved /009 correction review. You cannot accept your own changes.

Read authoritative main-checkout AGENTS.md, active CURRENT/INDEX and this kickoff. Verify branch, full HEAD and cleanliness. This later assignment supersedes the old stop at /003 only for bounded harness source/CPU correction; no runtime or production action is released. No extra agents.

## Confirmed issue and scope

Fix **COORD-Q0-01**, pinned diagnostic helper at **73b5ba98d1e3834cc8c58768ff269730b867ee4c** and published observation under docs/coordination/WP-0005/diagnostics/. In both sanitized install-stage and runtime-child environments, a separately spawned Python process cannot find Git and code_identity raises FileNotFoundError / WinError 2. The builders set PATH to venv Scripts/System32/Windows, but release.py and locks.py invoke bare git for mandatory checks. This stops the documented install/worker path before model qualification.

Choose a minimal explicit, scoped way to make required Git identity/blob operations work in both generated environments. Retain environment isolation, credential stripping and exact source/lock verification. Do not solve this by inheriting the whole user environment or changing global PATH/configuration. Exercise the actual subprocess boundary; a mock or parent-process environment check alone is insufficient. Existing CPython 3.12.10 and Git may be used without installing packages or creating the external runtime root.

Allowed edits: **qualification/q0/harness/**, new author evidence under an /008-specific subdirectory, this worktree's ignored .scratch, and the exact /008 report. Preserve all prior evidence/reports byte-for-byte. Do not edit model/library source, weights, dependency versions/hashes, renderer contract, fixtures, corpus/expected values, product application, coordinator files or another worktree. No heavy download, installation, model import, CUDA/GPU or global settings changes.

The independent Carbon /003 review is finishing on the unchanged 84cef5ef candidate in another worktree. Its final report may add related findings; the coordinator will bind its exact publication here before final /008 publication. You may reproduce and correct COORD-Q0-01 now in parallel. Do not inspect reviewer in-flight files or infer its verdict. Before finalizing, re-read this main-checkout assignment for the exact /003 handoff; if it is still unavailable after your useful correction work, return a prepared checkpoint rather than fabricate a review pin or publish an incomplete final report.

Freeze a new candidate before decisive relevant tests. Re-run affected meaningful tests and include real isolated-child Git/lock/identity checks for both environment builders. Existing 74 passes plus one skip validate only 84cef5ef. Preserve real failures and separate test-helper failures from source defects. Publish evidence after the candidate and /008 report last, with full base/candidate/evidence pins, exact commands, all changed paths and actual new session/model. Normal owned push and exact origin verification are authorized. Stop at independent /009 acceptance.
