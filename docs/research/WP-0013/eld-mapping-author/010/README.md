# WP13 /010: explicit Git lookup in the restricted runtime child

The original /007 stopped before all14 planned calls because frozen protocol
verification invokes bare `git`, while Q0 deliberately supplies an explicit
`Q0_GIT_EXECUTABLE` without its installation directory on the restricted PATH.
This correction lets that unchanged verifier find the already audited Git binary.
It does not change extraction, policy, scoring, corpus or model behavior.

## Frozen candidate

- Root correction authority: `61f37aa6bd0e67918f2a1225be8028bf8031ce29`,
  `docs/kickoffs/WP-0013-runtime-correction-010-011.md`.
- Clean merged base: `86fe8420ecd4fa57d800ce51f6411627ecd71d05`.
- Original failed /007 publication: `0d610695c87f3998deee2b6b3d48f7c7d531eddb`.
- Tested source and CPU helpers: `b60624ac7a0ae23540ab019b63d7a7e904fb1c36`.
- Mapping_v2 tree: `1f48ce375ee15cb5a9fca8a9c873e74f4d0e0b6f`.
- Runtime protocol SHA256:
  `ef648a3cd52df16ed6ed352e666ffedf789148100d640e2582cf13f76b6f9783`.
- Publication helper freeze: `5b0b2aa7df90e91ba7905140b97e2128b315422c`.
- Early source/evidence checkpoint: `e8384ae891a05fa658b8432cf593a5d37d313835`.

The production change is `runtime.enable_pinned_git_lookup`: audit the existing
allowlisted child environment, append only the parent directory of its explicit
validated Git executable, then repeat the unchanged audit. Existing PATH entries
remain first and unchanged. No host PATH is inherited, no Git configuration is
altered, no executable is copied into mutable runtime storage, and missing or
invalid pins fail rather than falling back. The integration call replaces the
existing final environment audit after cache-path construction in `execute`.

The entire worker body remains byte-identical as decoded Python source. The
accepted public protocol subtree, including its bare-Git helper, stays unchanged.
No production monkeypatch, alternative verifier or skipped pin check is added.
Appending the one audited directory is the bounded compatibility adjustment;
rewriting the accepted protocol or widening PATH to the host would change a
larger boundary.

The only other existing source edits are:

1. `runtime_protocol.json.source_review_path` points to new independent /011.
   Every other key/value and every call/guard/model setting is unchanged.
2. The existing synthetic supervisor fixture now includes its already mocked
   `Q0_GIT_EXECUTABLE='git'` binding. Its environment builder, Git resolver and
   audit are mocked together. This is test-fixture metadata, never a production
   fallback or proof that a relative Git pin is accepted by the real audit.

## Genuine restricted-child evidence

One frozen command ran18:38:43.0727602Z–18:39:01.5303922Z and exited0:

```text
python -I -B docs/research/WP-0013/eld-mapping-author/010/run_checks.py --out .scratch/wp0013-runtime-correction/attempt-1
```

The [run receipt](evidence/capture-attempt-1/execution.json),
[tool start](evidence/capture-attempt-1/tool-initial.json) and
[tool completion](evidence/capture-attempt-1/tool-final.json) preserve wrapper
PID3052, tool session8554 and final chunk591d26. All16 subprocesses use the actual
qualified `C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe`, real
Q0 environment construction/audits and real Git. No model, renderer or CUDA
backend is imported; an import blocker enforces that boundary. Each child retains
its exact argv, original/actual environment, launcher PID/creation, actual Python
worker PID/creation, exit, timestamps, stdout, stderr and structured result.

| Actual child cases | Observed result |
| --- | --- |
| `original` | Exit1, FileNotFoundError reproduces the unchanged bare-Git failure under the original restricted PATH |
| `corrected_pins` | Exit0, actual frozen mapper/protocol/source pins and working diffs pass |
| `full_release` | Exit0, unchanged actual `read_release` validates source/tree/cleanHEAD, configured hashes, authentic existing proof objects, all12 corpus contracts and four family contracts; future proof reads are explicitly synthetic as described below |
| `altered_pin`, `missing_pin` | Exit1, respectively ValueError and real Git CalledProcessError; pin verification is active |
| `missing_git`, `relative_git`, `missing_binary`, `mutable_git` | Exit1, real Q0Failure; no usable fallback or mutable-root Git execution |
| `forbidden_env`, `git_config` | Exit1, real Q0Failure on PYTHONPATH and inherited Git configuration |
| `stale_actual_release` | Exit1, real old authority rejected against corrected exact source |
| `release_source`, `release_schedule`, `release_digest`, `release_lease` | Exit1, unchanged release checks reject altered source tree, truncated schedule, bad proof digest and missing sole lease |

The14 exit1 cases are expected negative controls, not discarded failed attempts.
All16 controls passed their exact exit/type criteria on the first run. Full
results are in [results.json](evidence/attempt-1/results.json); original traceback
and positive pin evidence remain under `owned-runtime/runs/author/`.

The full-release positive cannot authenticate a future independent /011 or new
root unseal/runtime release before they exist. Its child-local test binding
overlays exactly three `release.git('show', ...)` reads: a synthetic pending
release envelope, synthetic source-review bytes and synthetic unseal bytes.
They use the all-zero synthetic revision, are clearly labeled CPU-only, and are
never committed as root authority or used to invoke runtime. No global subprocess
hook or production patch exists. Actual Git tree/status/pin reads, actual
source/corpus/qualified hashes, existing admission/lease observations, all
artifact bytes and all contract validators remain enforced. The exact intercepted
keys are retained. This proves integration through `read_release`; it does not
establish independent acceptance, a real corrected lease or permission to infer.

The existing61 unit tests also pass with0 failures/errors/skips. They cover public
mapper/policy/release controls, synthetic supervisor finalization/failure
accounting and an owned CPU Windows-job test. Their fake GPU observations never
query hardware. Two owned job-test children are cleaned by that existing test.
No fresh scoring or historical inference/scoring rerun occurs.

## Preservation and publication

[Source audit](evidence/attempt-1/source-audit.json) checks the only changed
protocol key, unchanged worker body, exactly three allowed existing paths, and
unchanged original mapper/protocol/scorer/release/B0/v1/coverage/Q0/corpus trees.
The publication inventory verifies every other base path, including immutable
/007, against complete Git mode/type/object identities.

[Copy manifest](evidence/copy-manifest.json) accounts for74 original test/capture
files,432 complete declared source/corpus input-tree files with both Git and
working SHA256, and two actual interpreter/Git executable hashes. This inventory
does not claim every inventoried module was imported. The intentionally invalid
mutable-root `git.exe` test bytes are archived with `.fixture-bytes` appended to
the copy name; exact original path/bytes/hash remain recorded. All other case
paths and original streams remain unchanged. Publication command receipts are
under `evidence/publication-capture/`.

The original /007 still has zero completed model calls and all12 primaries/255
policy slots unavailable. No old failure is relabeled or replaced. No corpus,
alias/catalog, mapper guard, policy, scoring/normalization, model, Q0 or live
runtime record was changed. Root will bind independent /011 and any new unseal
proof before separately releasing recovery /012. This CPU candidate grants no
inference or promotion; exact acceptance and observed sole lease remain pending.
