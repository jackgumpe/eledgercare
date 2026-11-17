# WP13 /007 original execution: pre-model failure retained

The one released author invocation failed before model loading, rendering or any
scheduled call. The child could not launch bare `git` during frozen-pin validation
inside its isolated environment. The supervisor returned
`WORKER_OUTCOME_UNAVAILABLE`, observed child exit 1 and retained all fourteen
scheduled calls as `not_run_after_failure`. No retry occurred. CPU scoring ran
once at the same clean executing HEAD and exited 0; this is successful failure
accounting, not successful evaluation. All twelve primaries remain unavailable.

## Exact execution and provenance

| Binding | Exact identity |
| --- | --- |
| Executing/base HEAD | `da6c91e0168f63843bd8d89ecf060834ccd07b9a` |
| Accepted source | `c0a1af638e807803b6014b3a93ecb7f9946ce6e1` |
| Source tree | `4477104eb2a3c73f496ef451cef9578f54d96518` |
| Runtime authority | `6558c3d7cf12fd336fc277d3406b26ffe125960d` |
| Release path | `docs/coordination/WP-0013/releases/author.json` |
| Corpus commit / tree | `373106d94b56e619e2210308ca3bf237b45affc0` / `af22f632c2b69531f61866ca467c6f04f386df7e` |
| Source /006 review | `bb2a731ef6969a6f87508cad4960ca5dc2bafeb1` |
| Admission /004 | `321afab409989a1eafcb1b43f433d784d2658711` |
| Root unseal | `e5c926890ae8c275a8782c8325a15b7d391f23ec` |
| Root failed-return ACK | `61f37aa6bd0e67918f2a1225be8028bf8031ce29:docs/coordination/WP-0013/author-failed-after/lease-return.json` |
| Frozen collector | `a6b1b878a065e3aaea1838d3fb6926dc1ad672fb` |

Stable author `eld-mapping-author`, native `/root/mapping_author`, existing
requested xhigh session; actual backend/applied effort remain unexposed. Owned
branch `research/wp-0013-vocabulary`, worktree
`C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-vocabulary-author`.
Product ownership returned before root granted the sole model-job lease
`WP-0013-author-vocabulary-20261117T182342Z`. Shared desktop GPU activity remained
explicit; neither hardware exclusivity nor OS outbound blocking is claimed.

Original runtime directory:
`C:/Users/jackg/eLedgerCare-Vocabulary/WP-0013/author/runs/author/20261117T182439Z-8726c2a5`.
The [complete copy manifest](evidence/attempt-1/run-copy-manifest.json) covers all
eight actual files with original relative names, bytes and SHA256. There are zero
cache files; existing empty cache directories are recorded. Missing worker
outcome, model load, raw, tokens and renders are explicitly unavailable, not
fabricated empty successful artifacts. All originals remain retained externally.

## Actual commands and exits

From the clean executing worktree, using host Python
`C:/Users/jackg/AppData/Local/Programs/Python/Python312/python.exe`:

```text
python -I -B qualification/mapping_v2/cli.py execute --authority 6558c3d7cf12fd336fc277d3406b26ffe125960d --release-path docs/coordination/WP-0013/releases/author.json --owner author
python -I -B qualification/mapping_v2/cli.py score-run --authority 6558c3d7cf12fd336fc277d3406b26ffe125960d --release-path docs/coordination/WP-0013/releases/author.json --owner author --run C:/Users/jackg/eLedgerCare-Vocabulary/WP-0013/author/runs/author/20261117T182439Z-8726c2a5 --output .scratch/wp0013-vocabulary-execution/007-attempt-1/scores.json
```

The execute wrapper used `Start-Process -PassThru -WindowStyle Hidden`, separate
stdout/stderr redirection, `WaitForExit` and the observed `Process.ExitCode`.
Launch began at 2026-11-17T18:24:36.4886176Z, ended 18:24:41.2148339Z and exited 1.
Wrapper PID32964, supervisor PID11176 and child launcher PID31684 have original
creation evidence. Tool chunk `ccf50e` independently returned exit1 without an
ongoing session. [Original launch](evidence/attempt-1/launch/launch.json),
[wrapper return](evidence/attempt-1/launch/execute-return.json),
[tool result](evidence/attempt-1/launch/execute-tool.json) and
[child traceback](evidence/attempt-1/run/stderr.txt) are copied byte-for-byte.
The worker identity is unavailable because failure preceded its receipt.

The traceback ends at accepted `protocol/common.py:31`, where `verify_pins`
uses `subprocess.check_output(['git', ...])`. This runs during worker release
validation. The isolated Q0 environment supplies an explicit Git executable;
the older mapping common uses that binding, but the accepted protocol helper
attempts PATH lookup. No repair was made here. The original source, catalog,
protocol, scorers and runtime settings remain immutable.

CPU score-run executed 18:25:31.2211796Z–18:25:35.9051359Z, exit0, tool chunk
`960e2c`. Its [receipt](evidence/attempt-1/launch/score-execution.json) confirms
the same clean HEAD. The [full scores](evidence/attempt-1/scores.json) retain all
three full prediction, original-score and separate policy objects per primary.
This read the admitted expected/reference/policy inputs; later work must retain
the exposure history and cannot characterize recovery as a new blind corpus.

## Denominators and interpretation

Exactly two excluded historical warmups and twelve one-page primaries were
scheduled. Zero completed; every row is preserved in the [original result](evidence/attempt-1/run/run-result.json).
Four families each have supported/conflict/unsupported cases; this is four
independent content families, not twelve independent generalization samples.

All B0/v1/v2 original failure-accounting totals are identical:

| Original metric | Correct / total, each mapper |
| --- | --- |
| Printed fields / historical typed fields | 0 / 87 |
| Printed cells / historical typed cells | 0 / 153 |
| Rows | 0 / 27 |
| Expected absences | 0 / 12 |
| Page count | 0 / 12 |

These preserved zeros, and legacy text error=1 against absent output, do not
measure observed character OCR or mapping quality. Every primary is unavailable.
The separate policy universe has 255 slots: 252 known, 3 ambiguous, 0 unknown.
Eligible slots=0, unavailable slots=255. All 89 required-abstention opportunities
are unavailable. Successful abstentions, observed assignments and violations are
zero with zero eligible denominator; the corresponding conditional rates are
null. All three pairwise comparisons have zero eligible documents and twelve
unavailable documents. Numerical zero gains/losses do not establish neutrality,
mapping equivalence or safe abstention. The [analysis](evidence/attempt-1/analysis.json)
preserves each fixture's denominators, all policy families/cases and this limit.

## Return and accounting checks

All four pre/post observer processes returned0; no finalization error was
recorded. Supervisor elapsed1.234s is a startup-failure duration, not inference
latency. Owned snapshot storage14,834bytes precedes final result writing;
complete current file sizes are in the manifest. Disk free after observation
was40,698,630,144bytes. No model load, inference memory or throughput is available.

Author queried only bound PIDs11176/31684/32964 at18:26:35.8119313Z and found them
absent; [return receipt](evidence/attempt-1/launch/lease-return.json). PowerShell
rendered equivalent local offsets in that derivative identity record; the
original run UTC strings and exact creation FILETIME values remain preserved.
Root separately acknowledged return at18:28:42.293912Z, verified model/notices,
all bound PIDs absent, 25 process candidates,24 desktop GPU rows and idle Ollama
with zero loaded models. Root proof copies are under `evidence/attempt-1/bindings/`;
their Git representations are distinguished from original working captures.

The accounting helper was first committed at40beafb48e59102851c1167d4c7fc4a6d0884374,
then bound to root's actual `author-failed-after` namespace at the final freeze
above before its first run. Collection ran once and passed:41 original/proof
copies,8 runtime files,0 retained cache files,50 scheduled input identities and
309 complete qualification source entries. No scoring rerun or model invocation
occurred. [Collection](evidence/attempt-1/collection.json) and
[source inventory](evidence/attempt-1/source-inventory.json) preserve identities;
collection command/streams/tool receipt are under `collection-execution/`.

Deliverable verification checks every prior path's mode/type/Git object,
all added files, exact evidence Git bytes, external originals, scheduled inputs
and complete run-file coverage. Its inventory is committed after the deliverable.
No repeated source suite or inference is warranted for packaging.

Root has reserved separate runtime-only correction010, independent011 and
possible later recovery012. They are outside this original failed record. No
correction, retry, reviewer inference, promotion or favorable quality result is
claimed in /007. Independent008/root disposition remain outstanding.
