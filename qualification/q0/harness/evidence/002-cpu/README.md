# WP-0005 /002 author CPU-check evidence (eld-q0-harness)

This is author verification only, not independent review. The frozen candidate under test is `50157e6cbaf0a2fcc29d229781237a05aa95fa92`. Its parent is base `df9a2b50894f01987d779d7f9ae805794503ce6f` and it adds 37 files under `qualification/q0/harness/`.

Host: Windows 11 10.0.26200, Python 3.12.10 (`C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe`), stdlib only. No torch, transformers, pypdfium2, numpy or PIL is installed or imported. There was no network, GPU, service, port or database use.

## Attempt 1: invalid (evidence-runner bug), preserved

The top-level `01-…07-*.txt` and `summary.json` in this directory come from the first run of `run_decisive.py`, at 2026-11-15T05:42:14Z–05:42:15Z on the same candidate.

The runner had a defect: it set `ROOT = HERE.parents[3]`, which resolves to `qualification/` instead of the worktree root. Every command therefore failed to start ("can't open file …\qualification\qualification\q0\harness\q0.py"), and unittest found no start directory. The exit codes were 1/2/2/2/2/2/2. **No candidate code executed.** SHA-256 of that runner version: `37e9fc4e528fe2321a37f410eb1ddd7fd3946f19ed1e494a2ab6eddd7c1b0f18`.

The only functional change in the committed runner is `parents[4]`, plus a root existence assert and output into a named attempt subdirectory. The candidate was not changed.

## Attempt 2: decisive (`attempt-2/`)

Started 2026-11-15T05:42:49Z and finished 05:43:09Z. HEAD before and after was `50157e6c…`, and the tracked diff was empty.

| Command (from worktree root) | Exit | Result |
| --- | --- | --- |
| `python -I -B -m unittest discover -s qualification/q0/harness/tests -t qualification/q0/harness/tests -v` | 0 | 53 tests, OK, 0 skipped |
| `q0.py verify-snapshots` | 0 | 9 hf snapshots match manifest SHA-256 **and** pinned HF tree git-blob oids; static facts: single `eval` L120, unique guard `if save_results and output_path:` L1103, save chain callers exact, `infer_multi` `setdefault('crop_mode', False)`, native return keys present |
| `q0.py derive-rasters --check` | 0 | F01 p1 and F07 p1–p3 inflated v1-raster300 RGB digests identical to `protocol.json` |
| `q0.py build-model-manifest --check` | 0 | committed `manifests/model-files.json` identical to the derivation from `hf-tree.json` |
| `q0.py check-protocol` | 0 | protocol SHA-256 `d94b3d43185360343f01e814340925d61315fe733d192a5bec9b7468102e3881`; F01 3482 B / F07 8422 B digests verified |
| `q0.py status` | 0 | lock `PENDING_ASTRA_001` (lock SHA-256 `62f11ac9cd0e78bb0a22bb34bbfd041cefe242e500b9cc1272a64e435f390eee`); storage root absent; no release |
| `q0.py execute --owner author` | 2 (expected) | `BLOCKED` / `DEPENDENCY_LOCK_PENDING`, `accuracy_score: null`; nothing created |

`summary.json` also records:

- `C:\Users\jackg\eLedgerCare-Q0` absent before and after;
- `.scratch/q0-harness-tests` left empty;
- the per-output SHA-256 values.

The supervisor tests started and killed only their own `python -I` children and verified each PID was gone via `tasklist`.

## Byte identity of the captured outputs

The `output_sha256` values in both `summary.json` files are digests of the raw captured bytes. Those bytes used Windows CRLF newlines from the child processes' text stdout, and `run_decisive.py` wrote `summary.json` itself in text mode, also with CRLF. The repository's `* text=auto` rule stores these `.txt`/`.json` files LF-normalized: `git add` reported CRLF→LF normalization. A committed blob therefore matches its recorded digest only after LF→CRLF conversion, as produced by a Windows `core.autocrlf=true` checkout, or by re-running the commands. No content other than newlines differs.

## Not run

- Real `pypdfium2` rendering and renderer identity: not installed, and installation is not released. A fake renderer replays the committed v1 XObject bytes instead.
- torch/transformers loading, Transformers 4.52.1 dynamic-module behaviour, CUDA and `nvidia-smi`.
- Wheel or model download.
- The real backend `backend_torch.py`: it is never imported by the tests.
- The read-only fetch of upstream `transformers@v4.52.1/dynamic_module_utils.py`, which was denied by the session permission policy.
