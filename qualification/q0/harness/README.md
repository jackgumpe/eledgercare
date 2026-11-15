# WP-0005 Q0 unmodified-model qualification harness

Author: `eld-q0-harness` (WP-0005 `/002`). This is a separate research qualification runner. It is **not** production OCR integration, and no product project may reference it. All of its code runs on the Python standard library. torch, transformers, pypdfium2 and the model's remote code are imported only inside the released execution stage.

Status: **frozen for the independent `/011` correction review (bounded `/010` PEP 508 marker-normalization fix for `COORD-Q0-02` on top of accepted `/008` `24a5866b…` and `/004` Stage B stop checkpoint `68855420…`). CPU / read-only wheelhouse verification only; this is not model qualification.**

- `protocol.json`, `locks/dependency-lock.json` and `manifests/model-files.json` remain byte-identical to `/002` (`84cef5ef…`). Both `build_stage_env` and `build_child_env` pin the validated host Git executable in `Q0_GIT_EXECUTABLE` with `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=NUL` and `GIT_TERMINAL_PROMPT=0` (`COORD-Q0-01`), and `locks._req_norm` parses PEP 508 environment markers into a precedence-aware boolean AST so semantically redundant singleton/associative parentheses (`COORD-Q0-02`) compare equal without relaxing real `AND`/`OR` grouping, quoted string contents, operands/operators, specifiers/extras or `Requires-Dist` multiset checks.

- The dependency lock is bound to Astra `/007`'s exact 32-artifact metadata graph: Git blob `ec8c650e…` at `d666c416…`.
  - 31 artifacts are publisher-declared.
  - torchvision is `local-sha256-TOFU; publisher wheel digest unavailable` (`5ae0ff50…`), bound to the independent receipt `ef728495…`.
- Before install, every acquired wheel's own METADATA is checked against the frozen graph.
- No storage root, wheel, model, venv or GPU lease exists for this work.
- `q0.py execute` and the install-stage commands refuse with `EXECUTION_NOT_RELEASED` before creating anything, because no coordinator release record exists.
- Earlier checkpoint records stay immutable and validate only their own revisions:
  - `evidence/002-cpu/`: candidate `50157e6c…`, 53 tests;
  - `evidence/002-checkpoint-2/`: prepared `e228f9d1…`, 68 tests.

## Contents

| Path | Purpose |
| --- | --- |
| [PROTOCOL.md](PROTOCOL.md), [protocol.json](protocol.json) | Frozen protocol: inputs, render contract, native call, sequence, measurements, telemetry, safety, guards |
| [ACQUISITION.md](ACQUISITION.md) | Staged, hash-verified acquisition, install and execution commands (not executed) |
| [manifests/model-files.json](manifests/model-files.json) | 18 pinned runtime objects (16 git-blob, 2 LFS SHA-256) plus the separate model-card notice, derived from the pinned HF tree |
| [locks/dependency-lock.json](locks/dependency-lock.json) | `eldq0-lock/2`: binding to the Astra `/007` metadata Git blob, platform/marker environment, expectations, torchvision hash gap, local-digest records (empty until the receipt) |
| `q0.py` | CLI (see its docstring) |
| `q0harness/` | protocol, fixtures/rasters, model files, static source check, environment, telemetry, log scan, memory, host precheck, writer, locks, release records, render, preflight, session, supervisor, torch backend |
| `tests/` | Stdlib `unittest` CPU checks; `tests/fakemodel/` is a test double mirroring the native call graph |
| `evidence/` | Author CPU-check evidence for this candidate (committed after the candidate) |

## CPU checks

From the worktree root, with any Python ≥ 3.12 (stdlib only):

```
python -I -B -m unittest discover -s qualification/q0/harness/tests -t qualification/q0/harness/tests -v
python -I -B qualification/q0/harness/q0.py verify-snapshots
python -I -B qualification/q0/harness/q0.py derive-rasters --check
python -I -B qualification/q0/harness/q0.py build-model-manifest --check
python -I -B qualification/q0/harness/q0.py check-protocol
python -I -B qualification/q0/harness/q0.py lock-check
python -I -B qualification/q0/harness/q0.py status
python -I -B qualification/q0/harness/q0.py host-precheck --stage initial   # read-only host + nvidia-smi
```

`lock-check` and the lock tests read Astra's metadata through `git cat-file blob ec8c650ed5fbeb0a754e4daee53aad53753a57a3`, so that object must be present in the local repository.

Tests write only under `.scratch/q0-harness-tests/` and remove what they create. The supervisor tests start and terminate only their own child Python processes.
