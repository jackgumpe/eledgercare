# WP13 /013: reject bare-Git shadows before frozen verification

Independent F011-01 showed that the /010 audits verified the explicit Git path
without binding the executable selected by bare `git`. An earlier mutable
`venv/Scripts/git.exe` passed both environment audits and was selected instead.
The trusted explicit Git succeeded; Windows rejected the invalid-image fixture
with216. The reviewer's parent expected193 and failed separately. Both the
finding and that helper expectation failure remain immutable; /010 is not
retroactively accepted or rewritten.

## Frozen source and scope

- Authority/base: `5cbf8ffe9dc8c5b04d5bc2fff43bb63b4fdad916`,
  `docs/kickoffs/WP-0013-runtime-correction-013.md`.
- Finding: `64a456db726080c124e0188e11b3445c02a1d754`; complete packet
  `7cbb53ede74c2aa79ef9411d388bee61be813d05`.
- Final tested source/helpers: `ae790497f3fdd10573e8179757416bc2d1736250`.
- Mapping_v2 tree: `8fd68c96bb18ca0177f227ad9a82505090d997b0`.
- Runtime protocol SHA256, unchanged from010:
  `ef648a3cd52df16ed6ed352e666ffedf789148100d640e2582cf13f76b6f9783`.
- Original /007 publication: `0d610695c87f3998deee2b6b3d48f7c7d531eddb`;
  /010 publication: `bd59cb57ad8f621ec98762b8bfdd76b3eee26e6f`.

`runtime_git.verify_bare_git_lookup` is a new narrow Windows guard. It inspects
the actual application-image directory, actual caller current directory, system
and Windows directories, then the explicit restricted PATH. It examines the
first existing `git.exe` candidate and requires its normalized absolute path to
equal the audited explicit executable. It rejects missing/ambiguous/relative
PATH entries and propagates inaccessible-location errors rather than treating
them as absence. It neither launches a candidate nor executes fixture code.

This order follows the documented non-shell CreateProcess behavior for a bare
name without extension; it is not a claim about `shutil.which`, PATHEXT,
SearchPath registry modes or shell/App Paths behavior.
[Microsoft CreateProcessW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw)
documents that the caller current directory precedes PATH. A requested child
working directory does not substitute for that caller directory during lookup.
The controls use the actual frozen verifier, not a `which` result, to demonstrate
the old behavior.

The existing audited PATH construction remains restricted. `execute` now checks
lookup after constructing it. The actual worker repeats the unchanged Q0
environment audit and lookup check after joining its owned Windows job and
before `read_release`, which invokes frozen bare-Git pin checks. The rest of
the worker body is unchanged. No global monkeypatch, host PATH inheritance,
mutable-root executable selection, protocol edit or pin bypass is introduced.

This is an observed filesystem/environment snapshot, not an atomic lock against
a concurrent process replacing files after the check. It is scoped to the
qualified Windows runtime and its cooperative owned-worktree/lease boundary.
The guard deliberately rejects an alternate lexical path rather than accepting
an alias merely because it resolves to the same file. No broader executable
discovery or hardware/process scan is performed.

Only existing `runtime.py` and its synthetic runtime test are modified; new
`runtime_git.py` contains the lookup guard. The fixture now uses the real
validated Git path and an absolute Windows PATH entry while its other supervisor
effects remain mocked. Its worker-body comparison permits only the exact new
entry guard. Runtime protocol, complete accepted protocol subtree, mapper/
catalog/policy/scorers/release validators, Q0/B0/v1/coverage, corpus, model and
all prior evidence remain byte-identical to the base.

## Actual frozen checks

```text
python -I -B docs/research/WP-0013/eld-mapping-author/013/run_checks.py --out .scratch/wp0013-runtime-shadow/attempt-1
```

The one decisive run started2026-11-17T19:06:57.1640092Z and completed
19:07:19.3059598Z, actual wrapper/tool exit0, wrapper33676, tool6512,
final chunk998211. [Original capture](evidence/capture-attempt-1/execution.json)
and separate streams/tool receipts remain unchanged.

All26 real restricted qualified-Python children passed their expected outcomes:

| Group | Actual result |
| --- | --- |
| Original007 bare-Git absence | Real FileNotFoundError/exit1 reproduced |
| Corrected pin verification and full release positive | Exit0; actual protected trees, working diffs, hashes and contracts pass |
| Original010 earlier PATH, caller cwd, both shadows | Trusted explicit Git exit0; actual frozen bare-Git verifier raises Windows216 in each case |
| Corrected setup earlier PATH, caller cwd, both | PermissionError before any shadow candidate launch |
| Actual worker entry clean | Real owned-job join and audits; reaches unchanged stale-release rejection, exactly one `read_release` call |
| Actual worker entry earlier PATH, caller cwd, both | Real owned-job join; lookup rejection before `read_release`, zero calls |
| Altered/missing pin and missing/relative/missing-binary/mutable-root Git | Original pin/environment guards reject |
| Forbidden environment/Git config; stale authority and changed source/schedule/proof digest/lease | Original guards reject |

The3 old-shadow tests extract only the immutable010 lookup function from its
exact Git object and record its source hash. They create invalid PE text fixtures
in owned CPU scratch; no fixture code executes. Caller-cwd controls change the
actual Python caller directory while the frozen Git command still requests the
repository working directory. Actual Windows loader failures, not resolution
guesses, establish the old behavior. Expected Windows codes193/216 are admitted
as invalid-image controls; the observed code is216 in all three receipts.

The full-release positive retains010's explicitly labeled three future-proof
overlays for synthetic release/source-review/unseal objects. All real pin/tree/
cleanHEAD checks, existing proofs and admitted artifact/contract checks remain
active. This is CPU integration evidence, never real acceptance or a lease.
Four actual-worker controls alter only the runtime protocol's CPU-owned root
in the test process and wrap `runtime.read_release` with a delegating call counter.
The actual worker function joins a real owned job and executes real audits and
lookup checks. Its unchanged release validator uses the real original authority
and rejects the stale source. No test reaches model/renderer code; an import
blocker enforces that limit. These test-only interceptions are recorded in each
receipt and do not exist in production source.

[Full results](evidence/attempt-1/results.json) retain each actual argv,
environment, launcher/worker PID and creation identity, exit, time, stdout and
stderr. Expected negative exits are retained; no unexpected control failed or
was rerun. All61 existing public/synthetic CPU tests pass with0 failures/errors/
skips, including the owned CPU Windows-job cleanup test. No live GPU observer,
fresh evaluation scoring, model/renderer/CUDA import or inference ran.

## Complete publication and limitations

[Source audit](evidence/attempt-1/source-audit.json) checks exact allowed scope,
zero runtime-protocol changes, unchanged worker remainder and every protected
tree. [Copy manifest](evidence/copy-manifest.json) covers126 original test/capture
files,433 declared source/corpus input-tree identities,12 immutable proof/original
source objects and two actual interpreter/Git executable hashes. Complete input
trees are inventoried conservatively; this does not claim every module imported.
Invalid-image copies use `.fixture-bytes` suffix; original path/bytes/hash remain
bound, and originals are retained in ignored CPU scratch.

Capture helper freeze7739b7cefac40badb215557ccad256834ae24630 copied the complete
original file population successfully. First evidence checkpoint
3ff3257dbcc8de8bfa1f0995e5afaa5686e74111 omitted six copied fixtures under inherited
ignored `venv` paths from Git staging. Packaging inspection detected this before
final inventory/report; d2bc93bad11e10f49f8ffde572a040f72464368d adds those exact
owned fixture copies and freezes a verifier assertion requiring every copied
path and byte sequence in the Git publication. Original helper/checkpoint history
is retained. No CPU test/source change or inference retry followed this packaging
correction. Final inventory records every changed path and checks all other base
objects, original copies, inputs and publication bytes.

Original007 remains a failed trial with all12 primaries/255 policy slots
unavailable, and010 retains the independently demonstrated lookup defect.
Independent final011 must reconcile this exact013 source and packet. Root alone
can bind any new unseal proof and separately observed recovery012 lease. No model
quality, production promotion, hardware exclusivity or atomic filesystem
assurance is claimed here.
