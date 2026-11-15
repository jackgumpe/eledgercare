# WP-0005 /010 candidate `41d62046`: author PEP 508 metadata-normalization and read-only 32-wheel evidence (`eld-q0-harness`)

This is author verification by **Gemini 4 Carbon (High)** session `bd92ddc3-af60-4096-b683-65386d81b718`, not an independent review. It establishes **narrow `COORD-Q0-02` PEP 508 requirement/marker canonicalization and read-only verification of all 32 downloaded wheels** without installing packages, touching `venv`, downloading model files, importing `torch`/`transformers`, or running GPU code. Original `/002` (`04e0efba-5292-4cae-b922-1517dee7bbed`), `/008` (`24a5866b…` / `b70ff45f…` / `460e1d81…`), and `/004` Stage B.3 stop (`68855420b2dece941eb90c42c69de3c80b47aa06`) evidence and authorship remain preserved byte-for-byte.

| Item | Value |
| --- | --- |
| Frozen `/010` candidate | `41d6204648e4115ab197507d1a22f6d5c7f3e784` (harness tree `fb2c704c2c36504d79b5eb30fe2efb35b7b01793`) |
| Continuation base | `68855420b2dece941eb90c42c69de3c80b47aa06` (`/004` Stage B.3 stop checkpoint; prior `/008` report `460e1d81de14c6f77ea4a026bc4b3ab36407bdf7`, accepted `/008` source `24a5866b505532fd03e7db62a4e57875e4c5a170`) |
| Original WP-0005 base | `df9a2b50894f01987d779d7f9ae805794503ce6f` |
| Independent `/011` Phase A diagnosis | `d211741bce3a341df70402679b4342b6aadb0ab3` (helper `60a5e381703a0a723d8bc11b21fd2ed57807c87f`): confirmed all 32 payloads (`1,974,477,651` B), 850 edges, and the exact 3-wheel / 5-edge redundant singleton marker-parenthesis mismatch |
| `protocol.json` SHA-256 (unchanged) | `dd8a7dc38c2a0c46103f6667f522656a2dddf5882727c18bf7b6b5426c5e2309` |
| `locks/dependency-lock.json` SHA-256 (unchanged) | `d8eeaf0fe838d9df5728f17fcbacc8b504d98b79644a524b4faa705d97c49e6e` |
| `manifests/model-files.json` SHA-256 (unchanged) | `085ac7ba1e25a7300846de18bdac19c7f9612bf417041643beff6a9cab6b8ea8` |
| External runtime root (read-only) | `C:\Users\jackg\eLedgerCare-Q0\WP-0005`: `893` files, `1,986,484,301` B, `0` reparse points, `venv` holding only `pip 25.0.1` before and after |

## Decisive Run `41d62046/`

Executed against clean frozen `HEAD` `41d6204648e4115ab197507d1a22f6d5c7f3e784` from `2026-11-15T19:30:56.730638Z` to `2026-11-15T19:31:13.935504Z` via preserved scripts [run_010_checks.py](run_010_checks.py) (`8,965` B, SHA-256 `b10503f5c1a2227d3eaa4a2672c60c649e67161dc43309862359dcdac6635248`) and [verify_32_wheels_readonly.py](verify_32_wheels_readonly.py) (`2,546` B, SHA-256 `d27131365670090af9374d840d2fbe2b88b7c8475cca0aa80a685467cf556b07`).

This directory uses `* -text`, so committed raw bytes match `output_sha256` in [41d62046/summary.json](41d62046/summary.json) (`9,419` B, SHA-256 `e7ad31acb7b7700ac3d6014d1619e364da1ca0592d7f88f146a0d861f585028c`).

| Output file | Env | Exit | Bytes | Raw SHA-256 | Result |
| --- | --- | --- | --- | --- | --- |
| `41d62046/01-unittest-locks-preflight.txt` | `host` (`-I -B`) | 0 | 2,288 | `bea973542a4e03082754dae7982abca1c897c850b9a0ab1cc42b4ea68416e971` | **18/18 lock & preflight unit tests passed** (`5.641s`), including positive/negative marker AST, literal quote/space preservation, real `AND`/`OR` grouping, and multiset guards |
| `41d62046/02-unittest-isolated-git-subprocess.txt` | `host` (`-I -B`) | 0 | 827 | `bf58350cdd19f96e0da5c9fc6ac0234951af740ad468101c4f1238c98749b88c` | **4/4 real isolated-subprocess Git tests passed** (`5.734s`) |
| `41d62046/03-lock-check-stage-offline.txt` | `stage_offline` | 0 | 3,708 | `e1769d403a348e107d262ed12140eb8b6907233348a9b000a40aad590c51ca93` | `q0.py lock-check` passes in task `venv` (`-s -B`): 32 artifacts, 850 edges, all receipt checks `true` |
| `41d62046/04-status-stage-offline.txt` | `stage_offline` | 0 | 702 | `3988188a767979b3235f1e2ac22f0da8963552f908e612d3bf01798e0a563eea` | `q0.py status` passes in task `venv`: `head: 41d62046…`, `harness_clean: true` |
| `41d62046/05-verify-wheelhouse-stale-release-refused.txt` | `stage_offline` | 2 (expected) | 598 | `22e67d5e4f82f32e02130e2a16446397b0987bce7c422f0ae6dd5d2ea6e5d64f` | `q0.py verify-wheelhouse` refuses old `460e1d81`-bound `author-install.json` (`EXECUTION_NOT_RELEASED`, `harness_commit/clean`) |
| `41d62046/06-readonly-32-wheel-verify-stage-offline.txt` | `stage_offline` | 0 | 19,792 | `dd3b6cd069be8c48d87d73949e7178befdf1f91ab4ae343f173c6771fefdf7a9` | Direct `locks.verify_wheelhouse` in task `venv` (`-s -B -P -X utf8`) under `build_stage_env(network=False)`: **`metadata_checked: 32`, `total_payload_bytes: 1974477651`, `all_payloads_ok: true`, `all_metadata_ok: true`, both PEP 658 digests `true`** (`2.094s`) |
| `41d62046/06b-readonly-32-wheel-verify-stdlib-host.txt` | `host` (`-I -B`) | 0 | 19,795 | `aff74a6bda144248ed1c7a785817373e2ea04d471cd138e94a4cc94933b63040` | Direct `locks.verify_wheelhouse` in stdlib-only host CPython `3.12.10` (`-I -B`): **`metadata_checked: 32`, `all_payloads_ok: true`, `all_metadata_ok: true`, both PEP 658 digests `true`** (`2.188s`) |

## Pre-Freeze Development Failure Disclosure

During local authoring before freezing `41d6204648e4115ab197507d1a22f6d5c7f3e784`, the initial pre-freeze run of `test_locks_preflight.py` passed `17/18` tests and failed one subTest (`test_every_pypi_artifact_in_both_forms (n='mpmath', raw=True)`): `mpmath`'s frozen `graph_requires` already stores parenthesized specifiers `(>=4.6)` and `(>=2.1.0a4)`, and the existing `synth_metadata(..., raw_style=True)` test helper wrapped `specs` in `({specs})`, emitting `pytest ((>=4.6))`. The initial draft unwrapped only a single outer pair of specifier parentheses. Resolved before freeze in `locks._req_norm` by unwrapping balanced outer specifier parentheses while rejecting empty `()`, unbalanced `(==1.0` / `==1.0)`, and multi-group `(==1.0)(==2.0)`, then re-verified (`18/18` and `4/4` passed) before committing `41d6204648e4115ab197507d1a22f6d5c7f3e784`.

## Not Run

- Offline wheel installation (`pip install --no-index --require-hashes`), `pip check`, or installed `venv` path-length walk (held for coordinator rebound install release after `/011` acceptance).
- Wheel redownload or `venv` recreation (prohibited; existing verified artifacts are preserved read-only).
- Model-shard downloads, CPU PDF raster preflight, `torch` / `transformers` / model imports, or GPU execution.
