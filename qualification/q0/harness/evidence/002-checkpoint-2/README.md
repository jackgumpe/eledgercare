# WP-0005 /002 prepared checkpoint 2: author CPU checks (eld-q0-harness)

This is author verification of a **prepared checkpoint**. It is not the final frozen candidate and not an independent review.

| Item | Value |
| --- | --- |
| Checkpoint code | `e228f9d19b64116d3d5894af97d21553d1fe4d10` (parent `1b88bfd7cc22e06bc8fd78193ad4821d1a383cb0`; 25 harness paths changed; prior evidence untouched) |
| Original task/report base | `df9a2b50894f01987d779d7f9ae805794503ce6f` |
| Why not final | The torchvision wheel SHA-256 is a declared gap. The canonical `/002` report stays held until the independent reviewer's local-digest receipt is bound in a new frozen candidate and these checks are re-run against it |

Checkpoint-1 records (`evidence/002-cpu/`, candidate `50157e6c…`, 53 tests) are unchanged. They validate only that candidate.

## Run `e228f9d1/`

Host: Windows 11 10.0.26200, `C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe`, 3.12.10. The executable and version were confirmed before the checks. The runner is [run_checks.py](run_checks.py), started as `python -I -B qualification/q0/harness/evidence/002-checkpoint-2/run_checks.py e228f9d1`. HEAD before and after was `e228f9d1…`, and the tracked diff was empty.

Outputs are raw bytes. This directory is marked `-text`, so the committed files equal the `output_sha256` values in `summary.json`. This avoids the newline caveat documented for checkpoint 1.

| Command | Exit | Result |
| --- | --- | --- |
| unittest discover (stdlib) | 0 | 68 tests, OK, **1 skipped** |
| `verify-snapshots` | 0 | Snapshots equal the pinned HF blobs; static save-path facts unchanged |
| `derive-rasters --check` | 0 | Raster digests identical to `protocol.json` |
| `build-model-manifest --check` | 0 | 18 runtime objects plus 1 notice; identical to the derivation |
| `check-protocol` | 0 | New protocol SHA-256 (see output); fixtures verified |
| `lock-check` | 0 | Bound to Git blob `ec8c650e…`: 32 artifacts, 31 publisher-declared, torchvision missing, `installable: false` |
| `status` | 0 | Lock readiness and code identity reported |
| `host-precheck --stage initial` | 0 | **Read-only host observation.** MSVC runtime DLLs present (14.51.36247.0). LongPathsEnabled=0, known paths ≤ 162 characters. C: free 68,907,061,248 B (≥ 58 GiB floor). Storage root absent. Both split `nvidia-smi` queries returned 0 with the leased UUID, RTX 5070 Ti, compute_cap 12.0, and per-process memory `[N/A]` under WDDM |
| `execute --owner author` | 2 (expected) | BLOCKED: `ACQUISITION_PROVENANCE_PENDING` `["torchvision"]`; nothing created |
| `write-requirements .scratch/never-written.txt` | 2 (expected) | Same refusal; the file was not written |

The skipped test is `test_links_rejected`. Creating a symlink requires a privilege this user does not hold (WinError 1314). The link/reparse-point rejection is therefore **not exercised** here. The code path remains unverified on a real link.

## Not run

- Real `pypdfium2` rendering. The fake renderer replays the committed v1 XObject bytes.
- torch/transformers import or load, `torch.version.cuda`, `get_arch_list`, CUDA allocation and GPU execution.
- Any wheel or model download.
- The torchvision receipt check against a real wheel. Synthetic ZIP fixtures are used instead.
- `backend_torch.py`, which no test imports.
- Venv path-length measurement, which needs an installed venv.

The `nvidia-smi` queries create no CUDA context and do not establish GPU ownership.
