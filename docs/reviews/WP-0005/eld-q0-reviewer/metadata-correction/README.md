# WP-0005 /011 Phase A Checkpoint: Independent All-Wheel `METADATA` Diagnosis (`COORD-Q0-02`, `eld-q0-reviewer`)

## Attribution, State, and Phase Boundary

- **Stable review role:** `eld-q0-reviewer`, same uninvolved **Gemini 4 Carbon (High)** conversation **`0815536f-045a-4112-8a89-ebf0e0cc782f`** (`gemini-4-carbon-high`, explicit `high` effort), authorized by `docs/kickoffs/WP-0005-eld-q0-reviewer-metadata-correction.md` at `e43fb4995fb75dc30c4bc6b69601cebfa159113f`.
- **Continuation & candidate pins:** Continuation base **`af81c9c67ddb4fb233cc93525481c4219d244f53`** (original packet base `df9a2b50894f01987d779d7f9ae805794503ce6f`); accepted harness core **`24a5866b505532fd03e7db62a4e57875e4c5a170`** (`protocol.json` `dd8a7dc38c2a0c46103f6667f522656a2dddf5882727c18bf7b6b5426c5e2309`, `locks/dependency-lock.json` `d8eeaf0fe838d9df5728f17fcbacc8b504d98b79644a524b4faa705d97c49e6e`, `manifests/model-files.json` `085ac7ba1e25a7300846de18bdac19c7f9612bf417041643beff6a9cab6b8ea8` — `transformers 4.52.1`, `torch 2.13.0+cu130`, `torchvision 0.28.0+cu130`, `pypdfium2 5.15.2`, RTX 5070 Ti `GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d`). All prior reports (`/003`, `/009`, `/002`, `/008`, `/007`) and Opus predecessor checkpoints (`b75011da…`, `ef728495…`) remain untouched.
- **Current state:** **Phase A read-only diagnostic checkpoint only.** Canonical report `docs/agent-reports/eld-q0-reviewer/WP-0005/011_2026-11-15_review_eld-q0-reviewer.md` and Phase B acceptance remain **HELD** until `eld-coordinator` binds frozen `/010` author correction and publication pins. No wheel was extracted, installed, modified, or imported; no model download, CUDA context, or GPU lease occurred.

## Independent Phase A Findings

Executed on clean frozen helper commit **`60a5e381703a0a723d8bc11b21fd2ed57807c87f`** (`python.exe -I -B docs/reviews/WP-0005/eld-q0-reviewer/metadata-correction/diagnose_wheel_metadata_phase_a.py --out-dir .scratch/phase-a-60a5e381`, `2026-11-15T19:16:09.729671Z` to `19:16:12.851105Z`, exit `0`):

1. **All 32 wheel payloads and PEP 658 `METADATA` digests match the lock (`0` payload drift):**
   - `C:\Users\jackg\eLedgerCare-Q0\WP-0005\wheelhouse` contains exactly the `32` locked `.whl` files totaling **`1,974,477,651` bytes** (`0` missing, `0` extra; pre/post stat fingerprint `d8500b34715662a63fa4d41421a5b922466113b913a6608f43de10fae19b21a8`).
   - All `32/32` wheels match locked byte sizes and `effective_sha256` digests (`31` `publisher-declared` + `1` `local-sha256-TOFU` `torchvision==0.28.0+cu130` `5ae0ff50fcb43a189250a5fdb36a7dc780ea5caff469653cab1e3f32ed5d385c`).
   - All `32/32` wheels contain one top-level `*.dist-info/METADATA` member matching locked `Name` and `Version`, with `850` total `Requires-Dist` lines matching the `850` frozen graph edges in count.
   - Both published PEP 658 index `METADATA` SHA-256 digests match raw ZIP `METADATA` bytes (`torch-2.13.0+cu130`: `c70f358c762d072ea6b9275b08e1af444abc989448dcf6b721f9049313c8e87b`; `torchvision-0.28.0+cu130`: `f8e91ee987603053e2166e2e4063ddcfb533f266c88bae82b7f79119aadceb59`).
   - Task `venv` contains only bootstrap `pip-25.0.1.dist-info`; `models`, `notices`, `runs`, `hf-home`, `pip-cache`, `uv-cache`, and `temp` contain `0` files.
2. **Exact original Stage B failure reproduced in isolated `stage_offline` subprocess:**
   - Calling `locks.verify_wheelhouse` and `q0.py verify-wheelhouse` inside `build_stage_env(network=False)` exits `2` (`BLOCKED`, `accuracy_score: null`, `HASH_MISMATCH`) on wheel #8 (`fsspec-2025.10.0-py3-none-any.whl`, `METADATA` SHA-256 `33de743cbf8933868fff5cc246279b43e94e694ab2f7fe24adad3e76a03cb422`). Captured CLI stdout ([phase-a-60a5e381/01-cli-verify-wheelhouse-reproduction.txt](phase-a-60a5e381/01-cli-verify-wheelhouse-reproduction.txt), `1,145` B, SHA-256 `347ecb1dc3a3dcb645db36ea93439081a2e6861168137ad93518a80f8e69ef89`) is byte-for-byte identical to the author's published Stage B stop log (`68855420b2dece941eb90c42c69de3c80b47aa06:.../08-stage-b-verify-wheelhouse.txt`). Passing `author-install.json` (`harness_commit: 460e1d81…`) on reviewer `HEAD` `60a5e381…` also failed closed as expected (`EXECUTION_NOT_RELEASED`, `["harness_commit/clean"]`).
3. **Complete all-wheel metadata mismatch inventory (`3` wheels / `5` edges out of `32` wheels / `850` edges):**
   - `25` wheels have identical raw `Requires-Dist` strings; `4` wheels (`idna`, `Jinja2`, `safetensors`, `tokenizers`) have raw spacing/quote/specifier-order differences already handled by `24a5866b` `locks._req_norm`.
   - Because `locks.verify_wheelhouse` (`locks.py:335-346`) short-circuits at the first failing wheel alphabetically (#8 `fsspec`), two later wheels were masked in single-run Stage B output. Exhaustive inspection ([phase-a-60a5e381/02-all-32-wheels-inventory.json](phase-a-60a5e381/02-all-32-wheels-inventory.json)) finds **exactly `3` wheels and `5` edges** failing `24a5866b` `locks._req_norm`, all caused by redundant parentheses around a single atomic marker comparison `(lhs op rhs)` before `and extra == "..."`:

| # | Wheel (`METADATA` SHA-256) | Edges | Raw wheel `Requires-Dist` | Frozen graph `Requires-Dist` (`ec8c650e…`) |
| ---: | --- | ---: | --- | --- |
| 8 | `fsspec-2025.10.0-py3-none-any.whl` (`33de743c…`) | `1 / 101` | `zstandard; (python_version < '3.14') and extra == 'test-full'` | `zstandard; python_version < "3.14" and extra == "test-full"` |
| 18 | `psutil-7.1.3-cp37-abi3-win_amd64.whl` (`89db7aca…`) | `2 / 38` | `colorama ; (os_name == "nt") and extra == 'dev'`<br>`pyreadline ; (os_name == "nt") and extra == 'dev'` | `colorama; os_name == "nt" and extra == "dev"`<br>`pyreadline; os_name == "nt" and extra == "dev"` |
| 32 | `urllib3-2.5.0-py3-none-any.whl` (`99a6244c…`) | `2 / 5` | `brotli>=1.0.9; (platform_python_implementation == 'CPython') and extra == 'brotli'`<br>`brotlicffi>=0.8.0; (platform_python_implementation != 'CPython') and extra == 'brotli'` | `brotli>=1.0.9; platform_python_implementation == "CPython" and extra == "brotli"`<br>`brotlicffi>=0.8.0; platform_python_implementation != "CPython" and extra == "brotli"` |

   *(Note: `psutil` is 1-based `#18` / 0-based `17` in sorted wheel filename order; `03-normalization-and-negative-controls.json` prose wrote `#17` using the 0-based offset, while `02-all-32-wheels-inventory.json` records exact 1-based `alphabetical_index_1based: 18`.)*

4. **Representation-only vs semantic assessment (`0` semantic drift):**
   - Build backends wrap a conditional extra dependency's marker `(M)` in parentheses when emitting `.dist-info/METADATA`, whereas PyPI's JSON API (`info.requires_dist` in `metadata-lock.json`) re-serializes via `packaging.markers.Marker`, unwrapping singleton parentheses around atomic comparisons while keeping parentheses around compound sub-expressions (e.g., `psutil`'s three `(os_name == "nt" and platform_python_implementation != "PyPy") and extra == "dev"` edges, which already match).
   - Under a strict stdlib PEP 508 requirement + marker AST parser (`parse_pep508_requirement_strict` in [diagnose_wheel_metadata_phase_a.py](diagnose_wheel_metadata_phase_a.py)) that unwraps only redundant parentheses around a single expression/comparison while preserving exact quoted literal contents, exact comparison operands/operators, exact `and`/`or` precedence and explicit compound sub-grouping, exact canonical extras and specifiers, and multiset multiplicities, **`0` mismatches occur across all `32` wheels and all `850` edges**, and **`0` active-dependency differences** exist under the locked Q0 marker environment (`requested_extras == []`; all `5` edges are inactive extra-gated edges).
5. **Normalization & acquisition-record observations (`locks.py:261-295, 335-347`; published `68855420…`):**
   - **Literal-fidelity note for `/010` & Phase B:** In `24a5866b` `locks.py:273`, `re.sub(r"\s+", "", marker).replace("'", '"')` not only fails on singleton parentheses (`COORD-Q0-02`), it also strips internal spaces inside quoted string literals (`"Windows NT"` == `"WindowsNT"`) and alters single quotes inside double-quoted literals ([phase-a-60a5e381/03-normalization-and-negative-controls.json](phase-a-60a5e381/03-normalization-and-negative-controls.json)). A tokenizing PEP 508 marker parser closes `COORD-Q0-02` across all `3` wheels / `5` edges while *preserving* exact quoted literal contents and rejecting grouping/operator/operand/specifier/extra/malformed-syntax differences.
   - **Published `/004` Stage A–B.3 stop checkpoint (`68855420b2dece941eb90c42c69de3c80b47aa06`):** Read-only Git-blob inspection confirmed `20` scoped evidence additions under `qualification/q0/harness/evidence/004-stage-b-stop/`, `0` harness core changes from `460e1d81…` / `24a5866b…`, exact byte/SHA-256 match on all `9` recorded step logs, `0` HTTP redirects or cookie headers in `07-stage-b-download-wheels.txt`, and identical `3`-wheel / `5`-edge findings in `08b-readonly-32-wheel-audit.json`.

## Committed Phase A File Inventory (`metadata-correction/`)

Captured under `metadata-correction/.gitattributes` (`* -text`):

| Path (relative to `metadata-correction/`) | Bytes | Raw SHA-256 |
| --- | ---: | --- |
| `.gitattributes` | 8 | `705fd4d6451a31d36b3df7de96f83f30ac976c9b4a6d1e51671d8e2f33e2d0da` |
| `diagnose_wheel_metadata_phase_a.py` | 32,086 | `d7cf9f4f4d197291232fa0b20427d794bff050e2292f20bd775e8b3b2a4aa4a1` |
| `phase-a-60a5e381/01-cli-verify-wheelhouse-reproduction.txt` | 1,145 | `347ecb1dc3a3dcb645db36ea93439081a2e6861168137ad93518a80f8e69ef89` |
| `phase-a-60a5e381/02-all-32-wheels-inventory.json` | 30,396 | `d76002c1941c6ceb6da1f6469f8e7fff483a4ad29bcda47075a3e3ec2c72f93a` |
| `phase-a-60a5e381/03-normalization-and-negative-controls.json` | 5,731 | `4ee89d777822f0f02a9b808cd12c8d2f99231666a87a0cfd58213d7c442577aa` |
| `phase-a-60a5e381/summary.json` | 3,185 | `0362d59137725b312fbc5a139a46ca3c7d1e7b764daec0cfb2f3d7beec512df0` |
