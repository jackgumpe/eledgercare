# WP-0005 /002 final candidate: author CPU-check evidence (eld-q0-harness)

This is author verification, not an independent review. It covers **CPU harness readiness only**. It is **not** model/runtime qualification.

| Item | Value |
| --- | --- |
| Frozen candidate | `84cef5ef30685ffee46281fefc5fd1356dbc1876` (parent `912f4f4f991977cca83bb40928cff45ac525efaa`; harness tree `b7afcd512d508e43b874cf7b9857b7493359a879`) |
| Original task/report base | `df9a2b50894f01987d779d7f9ae805794503ce6f` |
| `protocol.json` SHA-256 | `dd8a7dc38c2a0c46103f6667f522656a2dddf5882727c18bf7b6b5426c5e2309` |
| `locks/dependency-lock.json` SHA-256 | `d8eeaf0fe838d9df5728f17fcbacc8b504d98b79644a524b4faa705d97c49e6e` |
| `manifests/model-files.json` SHA-256 | `085ac7ba1e25a7300846de18bdac19c7f9612bf417041643beff6a9cab6b8ea8` |

Each of these SHA-256 values was computed over the committed Git blob bytes, and each equals the value the CLI reported from the working tree.

## Run `84cef5ef/`

Started 2026-11-15T16:18:12.404294Z and finished 16:18:45.590321Z. The runner is [run_checks.py](run_checks.py), started as `python -I -B qualification/q0/harness/evidence/002-final/run_checks.py 84cef5ef`. The interpreter was confirmed before the run as `C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe` 3.12.10. HEAD before and after was `84cef5ef…`, and the tracked diff was empty.

Outputs are raw bytes. This directory is `-text`, so the committed files equal the `output_sha256` values in `summary.json`.

| Command | Exit | Result |
| --- | --- | --- |
| unittest discover | 0 | **75 tests, OK, 1 skipped** |
| `verify-snapshots` | 0 | Snapshots equal the pinned HF blobs; static save-path facts unchanged |
| `derive-rasters --check` | 0 | Raster digests identical |
| `build-model-manifest --check` | 0 | 18 runtime objects plus 1 notice, identical |
| `check-protocol` | 0 | Protocol SHA-256 as above; F01/F07 digests verified |
| `lock-check` | 0 | 32 artifacts: 31 publisher-declared plus torchvision `local-sha256-TOFU`. `installable: true`, `required_exceptions: ["torchvision-local-sha256-TOFU"]`. Receipt checks all true; 850 graph requirements; published METADATA digests for torch and torchvision |
| `status` | 0 | Code identity `84cef5ef…` clean; no release |
| `host-precheck --stage initial` | 0 | Read-only. C: free 68,879,597,568 B. MSVC runtime present. LongPathsEnabled=0, known paths ≤ 162. Both `nvidia-smi` queries valid (leased UUID, compute_cap 12.0). Storage root absent |
| `execute --owner author` | 2 (expected) | BLOCKED `EXECUTION_NOT_RELEASED`; nothing created |
| `write-requirements .scratch/never-written.txt` | 2 (expected) | Same refusal; file not written |
| `verify-wheelhouse .scratch` | 2 (expected) | Same refusal before reading anything |

The skipped test is `test_links_rejected`. Creating a symlink needs a privilege this user lacks (WinError 1314), so the link/reparse-point rejection is not exercised on a real link.

What the new tests exercise for N-02 (every-wheel METADATA):

- the real recorded PEP 658 METADATA bodies of torch and torchvision from the bound `cuda-metadata.json` blob, wrapped in synthetic ZIPs. Both pass the graph comparison and their published-digest match;
- graph-derived METADATA for all 30 PyPI artifacts, in both index and raw (parenthesized, single-quoted) forms;
- rejection of a dropped, added or changed requirement, a wrong version, altered METADATA bytes against a published digest, and a duplicate dist-info METADATA;
- a 32-wheel synthetic wheelhouse that passes payload then METADATA checks, and fails once one wheel's METADATA diverges even though its payload hash matches.

Receipt binding is tested both ways. The real receipt is re-read and verified. Forged or altered records are refused, including a receipt rewritten with `pass: false`.

## Not run

- Wheel or model download.
- The real 32-wheel METADATA check. The wheels are not acquired, so synthetic ZIPs are used.
- Installation, `pip check` and venv path lengths.
- Real `pypdfium2` rendering, torch/transformers import or load, tokenizer load, `torch.version.cuda`/`get_arch_list`, CUDA allocation, GPU execution.
- `backend_torch.py`, which no test imports.

The `nvidia-smi` queries create no CUDA context and do not establish GPU ownership.
