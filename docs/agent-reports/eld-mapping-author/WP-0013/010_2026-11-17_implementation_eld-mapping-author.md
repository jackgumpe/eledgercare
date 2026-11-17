# WP-0013 /010: Preserve restricted Git isolation while enabling frozen pin checks

- Report path: `docs/agent-reports/eld-mapping-author/WP-0013/010_2026-11-17_implementation_eld-mapping-author.md`
- Sequence reservation: [INDEX.md](../../../../INDEX.md), WP-0013 /010; root authority `61f37aa6bd0e67918f2a1225be8028bf8031ce29`
- Category: implementation
- Author / agent ID: eld-mapping-author; continuing native `/root/mapping_author`
- Actual model / effort: backend/applied effort not exposed; existing requested xhigh
- Execution environment: Windows / PowerShell; qualified Python312, actual restricted Q0 child environment; CPU only
- Published by: author on owned branch
- Timestamp: 2026-11-17T18:43:36Z
- Repository / branch: jackgumpe/eledgercare / `research/wp-0013-vocabulary`
- Owned worktree: `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-vocabulary-author`
- Base revision: `86fe8420ecd4fa57d800ce51f6411627ecd71d05`
- Frozen tested source/helpers: `b60624ac7a0ae23540ab019b63d7a7e904fb1c36`
- Source tree: `1f48ce375ee15cb5a9fca8a9c873e74f4d0e0b6f`
- Runtime protocol SHA256: `ef648a3cd52df16ed6ed352e666ffedf789148100d640e2582cf13f76b6f9783`
- Frozen publication helper: `5b0b2aa7df90e91ba7905140b97e2128b315422c`
- Deliverable revision: `31c435f93f7058da2076d98ee7a25d4166bb316e`
- Inventory / verification metadata revision: `1a6fc0a5ff10e958dabc1805ee21876f34a43858`
- Previous report: [original failed /007](007_2026-11-17_research_eld-mapping-author.md), publication `0d610695c87f3998deee2b6b3d48f7c7d531eddb`
- Related report: [original source /006](../../eld-mapping-reviewer/WP-0013/006_2026-11-17_review_eld-mapping-reviewer.md); new independent /011 remains pending
- Status: ready-for-review
- Next owner: independent eld-mapping-reviewer /011; root binds any later recovery /012

## Summary

The original live /007 failed before any model call because frozen public
protocol pin verification invokes bare `git`, which was absent from Q0's
restricted PATH despite a valid explicit `Q0_GIT_EXECUTABLE` binding. This narrow
runtime correction appends only that audited executable's installation directory
to the existing restricted child PATH. Original environment audits run before
and afterward. No host PATH, mutable-root Git or fallback is introduced.

The frozen source passed16 actual qualified-Python restricted-child probes and
all61 existing CPU tests. The probes reproduce the original failure, pass the
corrected full pin boundary and reject invalid pins/environments/releases.
The [dossier](../../../research/WP-0013/eld-mapping-author/010/README.md) explains
the explicitly synthetic future-proof overlay used for the full-release positive.
That test is not independent acceptance or runtime authority. No model, renderer,
live observer, fresh scoring or inference ran. The original /007 and its twelve
unavailable primary outcomes remain immutable.

## Objective and acceptance criteria

Root's exact [correction kickoff](../../../kickoffs/WP-0013-runtime-correction-010-011.md)
released runtime-only wiring after /007 publication, genuine restricted-child
failure reproduction and guard verification, unchanged mapper/protocol/scorers/
corpus/model settings, complete evidence and independent /011. The author has
completed the implementation and CPU evidence. Independent acceptance and any
later observed sole-model-job lease remain outstanding.

## Change inventory

| Existing path | Exact change |
| --- | --- |
| [runtime.py](../../../../qualification/mapping_v2/runtime.py) | New `enable_pinned_git_lookup` audits the environment, appends the parent of validated `Q0_GIT_EXECUTABLE`, re-audits; `execute` uses it at the existing final environment-audit boundary |
| [runtime_protocol.json](../../../../qualification/mapping_v2/runtime_protocol.json) | Only `source_review_path` changes from /006 to reserved /011 |
| [test_runtime.py](../../../../qualification/mapping_v2/tests/test_runtime.py) | Adds the already mocked Git binding to the existing synthetic supervisor environment fixture |

All other additions are under owned `docs/research/WP-0013/eld-mapping-author/010/`:
two frozen CPU probe helpers, frozen byte-publication helper, dossier, attributes,
original case/capture files and input/copy inventories. The
[complete deliverable inventory](../../../research/WP-0013/eld-mapping-author/010/deliverable-inventory.json)
lists86 changed paths with Git blobs and working/Git byte identities: three
modified and83 added. All4,715 other base paths retain exact mode/type/blob
identities, including /007, original protocol/catalog/mapper/scorers, B0/v1/
coverage/Q0 and complete admitted corpus.

The inventory and five publication-check receipts were committed afterward at
`1a6fc0a5ff10e958dabc1805ee21876f34a43858`; this canonical report follows them.
Shared routing is untouched. External effects comprise owned ignored CPU scratch
and explicitly owned test child processes. No live runtime root or other owner's
resource was changed.

## Decisions and rationale

The unchanged Q0 audit validates an absolute existing Git executable, rejects
mutable-root placement and enforces isolated Git configuration, forbidden
variables and owned caches. The correction applies those guards to the existing
allowlisted environment and changes only PATH by appending the one audited
installation directory. Existing entries retain priority. Frozen bare-Git
verification therefore works without rewriting the accepted protocol, bypassing
pins or changing global subprocess behavior.

The worker body and every runtime-protocol value except the independently
reviewed-source report route remain unchanged. The one synthetic fixture
adjustment reflects its already mocked builder/resolver/audit; the genuine
negative probe still rejects a relative Git executable. There is no production
fallback when the binding is missing or invalid.

## Verification

Decisive command, frozen before execution:

```text
python -I -B docs/research/WP-0013/eld-mapping-author/010/run_checks.py --out .scratch/wp0013-runtime-correction/attempt-1
```

It ran18:38:43.0727602Z–18:39:01.5303922Z, wrapper PID3052/tool8554, actual exit0.
The [capture receipt](../../../research/WP-0013/eld-mapping-author/010/evidence/capture-attempt-1/execution.json)
and original streams/tool receipts preserve the command and result.

| Check | Actual result | Evidence |
| --- | --- | --- |
| Original restricted PATH / unchanged pin verifier | Expected exit1/FileNotFoundError reproduced | [Original child](../../../research/WP-0013/eld-mapping-author/010/evidence/attempt-1/owned-runtime/runs/author/original/probe.json) |
| Corrected restricted PATH / actual frozen pins | Exit0, real Git/source/working checks pass | [Positive pins](../../../research/WP-0013/eld-mapping-author/010/evidence/attempt-1/owned-runtime/runs/author/corrected_pins/probe.json) |
| Actual `read_release` with labeled CPU-only future-proof overlays | Exit0; exact source/tree/cleanHEAD, qualified hashes, existing authentic proofs, all12 contracts/four families pass | [Full boundary](../../../research/WP-0013/eld-mapping-author/010/evidence/attempt-1/owned-runtime/runs/author/full_release/probe.json) |
| Altered/missing source pins, missing/relative/missing-binary/mutable-root Git, forbidden PYTHONPATH/Git config | Eight expected exit1 guard rejections | [Full16-case results](../../../research/WP-0013/eld-mapping-author/010/evidence/attempt-1/results.json) |
| Stale actual authority and altered source/schedule/proof digest/sole lease | Five expected exit1 release rejections | Same full results |
| Existing public/synthetic CPU tests |61 passed;0 failures/errors/skips; no real GPU observer | [Unit results](../../../research/WP-0013/eld-mapping-author/010/evidence/attempt-1/unit-tests.json) |
| Frozen publication capture | Exit0;74 original files,432 declared input-tree identities,2 actual executable hashes | [Copy manifest](../../../research/WP-0013/eld-mapping-author/010/evidence/copy-manifest.json) |
| Frozen publication verification | Exit0;86 changed paths/4,715 unchanged base paths;74 originals and all input hashes reverified | [Inventory receipt](../../../research/WP-0013/eld-mapping-author/010/evidence/publication-inventory/execution.json) |

All16 actual children retain exact argv, original/actual allowlisted environment,
launcher and Python-worker PID/creation identities, timestamps, observed exits,
stdout/stderr and structured outcomes. An import blocker rejects model/renderer
imports. Fourteen exit1 outcomes are expected negative controls; no unexpected
test failure or rerun occurred. The existing owned CPU Windows-job test cleans
its two child processes; its synthetic observer cases do not query hardware.

The full-release positive overlays only three child-local `release.git('show',
...)` reads: synthetic future release envelope, source review and unseal. These
use a labeled all-zero synthetic revision. No pin/tree/status check, corpus/hash
check, existing proof verification or contract validation is patched. No global
monkeypatch or accepted root object is written. The test exercises real release
logic but does not supply the future independent /011, new unseal or real lease.

The [source audit](../../../research/WP-0013/eld-mapping-author/010/evidence/attempt-1/source-audit.json)
confirms preserved source/corpus identities and the single protocol-key change.
Historical full scoring was not repeated because mapper/scorer inputs and code
are unchanged. No fresh result scoring, model import, live process/GPU scan or
inference was needed or performed. The intentionally invalid mutable Git test
bytes are archived with `.fixture-bytes` suffix and exact original identity;
no usable executable was installed.

## Risks and unfinished work

This is an integration correction, not new mapping quality evidence. Original
/007 remains a failed pre-model trial with all12 primaries and255 policy slots
unavailable; no recovery has occurred. Corpus exposure and original failures are
retained. The bounded PATH addition and full guard evidence require independent
/011 review. Real corrected source/unseal/runtime authority and observed sole
lease must be bound by root before any separately reported /012 recovery.

## Handoff

Independent reviewer should reconcile exact source `b60624ac7a0ae23540ab019b63d7a7e904fb1c36`,
tree `1f48ce375ee15cb5a9fca8a9c873e74f4d0e0b6f`, runtime protocol digest above and
complete deliverable `31c435f93f7058da2076d98ee7a25d4166bb316e`. Inspect the real
restricted-child controls, synthetic-proof limitations, full preservation and
immutable initial007 before canonical011. Normal owned push and exact-origin
confirmation follow this report commit; its own publication SHA is sent to root.
No inference or product promotion is released by this report.
