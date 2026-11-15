# WP-0005 Q0 unmodified-model qualification harness

Author: `eld-q0-harness` (WP-0005 `/002`). This is a separate research qualification runner. It is **not** production OCR integration, and no product project may reference it. All of its code runs on the Python standard library. torch, transformers, pypdfium2 and the model's remote code are imported only inside the released execution stage.

Status: **prepared for independent `/003` review; not executable.**

- The dependency lock is `PENDING_ASTRA_001`.
- No storage root, wheel, model, venv or GPU lease exists for this work.
- `q0.py execute` refuses before creating anything.

## Contents

| Path | Purpose |
| --- | --- |
| [PROTOCOL.md](PROTOCOL.md), [protocol.json](protocol.json) | Frozen protocol: inputs, render contract, native call, sequence, measurements, telemetry, safety, guards |
| [ACQUISITION.md](ACQUISITION.md) | Staged, hash-verified acquisition, install and execution commands (not executed) |
| [manifests/model-files.json](manifests/model-files.json) | 19 pinned model files with git-blob / LFS SHA-256, derived from the pinned HF tree |
| [locks/dependency-lock.json](locks/dependency-lock.json) | PENDING lock: fixed pins, carried evidence, unresolved items, required final shape |
| `q0.py` | CLI (see its docstring) |
| `q0harness/` | protocol, fixtures/rasters, model files, static source check, environment, telemetry, memory, writer, locks, render, preflight, session, supervisor, torch backend |
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
python -I -B qualification/q0/harness/q0.py status
```

Tests write only under `.scratch/q0-harness-tests/` and remove what they create. The supervisor tests start and terminate only their own child Python processes.
