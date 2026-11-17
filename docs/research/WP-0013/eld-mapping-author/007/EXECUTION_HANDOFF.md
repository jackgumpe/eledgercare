# WP13 /007 execution handoff preparation

Preparation only under root authority
`e5c926890ae8c275a8782c8325a15b7d391f23ec`. No invocation, live observer,
renderer/model import, fresh artifact read, helper addition or CPU rerun occurs
in this preparation. Canonical /007 remains held until actual execution and its
truthful outcomes. Product rehearsal retains first GPU slots.

## Fixed identities and remaining release inputs

- Accepted implementation: `c0a1af638e807803b6014b3a93ecb7f9946ce6e1`;
  mapping_v2 tree `4477104eb2a3c73f496ef451cef9578f54d96518`.
- Independent source /006: `bb2a731ef6969a6f87508cad4960ca5dc2bafeb1`.
- Runtime protocol SHA256:
  `46a0d3e7bec0f14a3911eb7365385b7d132db8e8a72c8edb3f030aeeda124ec2`.
- Accepted public protocol SHA256:
  `aa0d8f183f9f0161c6e47b56a6f2cd844d6ad3f31e772b9761aa0ad618f6a372`;
  catalog SHA256:
  `35a99a213b80476747c7a136a4109ac45bc7944c77b0a3dcf0f348f107dd37a2`.
- Public reservation: `b50b2a3bc22927890c8f391943f2a3fe9168d0da`,
  `docs/evaluation/WP-0013/reservation/reservation.json`, SHA256
  `533f4be35fb89efd9e288c0470201457b5ab32373eab3112ae283b42febcfea5`.
- Independent admission /004: `321afab409989a1eafcb1b43f433d784d2658711`.
- Root unseal object: `e5c926890ae8c275a8782c8325a15b7d391f23ec:docs/coordination/WP-0013/unseal.json`.
  It explicitly sets runtime_authorized=false; it is not the runtime lease.

Still required from root: the audited public corpus commit/tree and exact
preparation authority to merge; confirmation of the author's resulting clean
executing HEAD; then a separately committed runtime authority containing
`docs/coordination/WP-0013/releases/author.json`. That release must bind source,
tree, HEAD, runtime and accepted-contract digests, unchanged comparator/core
trees, corpus/reservation, accepted source/admission proof objects, unseal proof,
owned root, exact schedule, issue/expiry times and fresh observed sole-model-job
lease/owner/GPU evidence. The existing release validator already checks these
fields. No extra user approval or source change is needed to supply them.

The author will retain the exact clean executing HEAD through both execute and
CPU score-run. Runtime authority can be fetched/read as an immutable Git object;
it must not be merged after root binds the executing HEAD.

## Exact commands after separate runtime release

Run from the owned `eld-vocabulary-author` worktree. `$runtimeAuthority` below
means the full future root-supplied runtime commit, not the preparation/unseal
commit. `$actualRun` means the actual directory produced by that one invocation.

```powershell
python -I -B qualification/mapping_v2/cli.py execute --authority $runtimeAuthority --release-path docs/coordination/WP-0013/releases/author.json --owner author
```

Use the already exercised WP11 capture pattern: resolve the host Python
executable, invoke the exact argument vector through `Start-Process -PassThru
-WindowStyle Hidden` with the owned worktree as WorkingDirectory, and redirect
stdout/stderr separately into a new ignored
`.scratch/wp0013-vocabulary-execution/007-attempt-1/` directory. Preserve the
wrapper PID, supervisor PID, command vector, Python path, UTC start, clean HEAD,
runtime authority/release path/lease ID and subsequent tool session/chunk IDs.
Write the launch receipt immediately and send root actual start/PID/run details.
The wrapper waits for the actual supervisor and records its observed exit code
and UTC end without substituting success for unknown state. The runtime itself
retains plan, supervisor/launcher/worker creation identities, all per-call
observations, worker outcome, actual exits and finalization errors.

The sole invocation is exactly two excluded historical warmups followed by the
twelve frozen primaries, family-major supported/conflict/unsupported. First
unexpected failure stops, no retry/substitution. Preserve all planned outcomes
and not-run rows. Any rejected or malformed packet is retained and escalated to
root; do not repair source or rerun the model to obtain a passing result.

At the same bound clean HEAD, perform the one accepted CPU score-run:

```powershell
python -I -B qualification/mapping_v2/cli.py score-run --authority $runtimeAuthority --release-path docs/coordination/WP-0013/releases/author.json --owner author --run $actualRun --output .scratch/wp0013-vocabulary-execution/007-attempt-1/scores.json
```

Retain score stdout/stderr separately and record its exact command, start/end,
HEAD/status, authority and actual exit. No source or helper commit occurs before
execute and score-run finish. The source can score legitimate failed/not-run
populations; an invalid history is not silently repaired.

## Return, evidence and report

Notify root promptly when execution/cleanup completes. Retain actual owned PID
and creation identities from the run and observe only the bound owned processes
as permitted by the later release. Return the sole model-job lease explicitly;
root independently observes post host/model/process ownership and records the
return. Elapsed expiry or low memory is never treated as lease transfer. Do not
wait for prose packaging before sending completion/return evidence.

Proposed immutable packet prefix within this owned namespace is
`docs/research/WP-0013/eld-mapping-author/007/evidence/attempt-1/` unless root's
execution kickoff fixes another owned prefix. Keep runtime files under `run/`
with their original run-relative names; original launch/score/tool/cleanup
receipts under `launch/`; exact authority/review/admission/unseal/root-return
proof copies under `bindings/`; and the original full `scores.json` unchanged.

The complete run-copy manifest must cover every actual external run file:
relative path, byte count, SHA256 and copied versus retained-only disposition.
Cache entries remain retained-only with their identities; weights/secrets and
unrelated files are never copied. Preserve original bytes and distinguish Git
proof-object representations from original working captures. Inventory all
actual source/input/proof/evidence files, including the failed or unavailable
outcomes, original raw/token/render identities, logs and resource observations.
Use Git tree/object checks for unchanged source and old records; no repeat model
or CPU suite is justified merely for packaging.

No new collector is added now. If the actual packet needs a bounded schema/path
adaptation of the prior collection pattern, freeze that accounting helper only
after execute and score-run complete, before its decisive copy/identity checks.
It must not redefine scoring or alter raw evidence. Commit complete deliverables,
then inventory/evidence metadata, then the reserved canonical
`docs/agent-reports/eld-mapping-author/WP-0013/007_2026-11-17_research_eld-mapping-author.md`.
Root reconciles the UTC date before publication if needed. Push the owned branch
normally and return exact origin, clean state and full revision identities.

Report all twelve primaries/four families separately from warmups and the later
one-document reviewer sentinel. Keep B0/v1/v2 full original scores, separate
policy coverage/assignment/abstention violations, unknown/ambiguous/unavailable
counts, gains, losses, neutral cases, timing/resource provenance and limitations.
No outcome is promised; abstention is not an exact value and an absence is not
verified merely because no value was emitted. No fresh-result-driven tuning or
automatic product promotion follows. Independent /008 remains separate work.

Prior capture references inspected for this preparation:
`docs/evidence/WP-0011/eld-mapping-author/005/attempt-1/launch/{launch.json,score-execution.json}`
and its published /005 execution dossier. Their actual receipts stay immutable.
