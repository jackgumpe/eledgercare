# WP-0005 /004 Stage A–B.3 fail-closed stop checkpoint (`eld-q0-harness`)

This is a **stage-stop evidence checkpoint** by **Gemini 4 Carbon (High)** author session `bd92ddc3-af60-4096-b683-65386d81b718` (`eld-q0-harness`), not an independent review and not the final canonical `/004` verification report. Original `/002` implementation authorship remains attributed to stopped Opus session `04e0efba-5292-4cae-b922-1517dee7bbed`, and independent review remains separate (`0815536f-045a-4112-8a89-ebf0e0cc782f`, `eld-q0-reviewer`).

| Item | Value |
| --- | --- |
| Executing branch / worktree | `qualification/wp-0005-harness` / `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-harness` |
| Clean continuation / execution `HEAD` throughout commands | `460e1d81de14c6f77ea4a026bc4b3ab36407bdf7` |
| Accepted harness candidate (`0` core edits) | `24a5866b505532fd03e7db62a4e57875e4c5a170` (tree `48ce82ffc8f78d27aa0338d5ec926ab9b1f683a4`) |
| Independent `/009` evidence / report | `6e12e55ce53827f7386889c945c33d524c92658f` / `af81c9c67ddb4fb233cc93525481c4219d244f53` |
| Coordinator runtime kickoff / install release | `4fb0ac86e4ca2f9e9b089bf9ae5647d3f7f53677`; `author-install.json` (`912` B, SHA-256 `3d9a71e4b1526c2103c69cf97c010d88d7fe1b1d8e1fc225dbf5a1198f278aaa`) |
| Storage creation receipt (`C:\Users\jackg\eLedgerCare-Q0\WP-0005`) | `storage-created.json` (`489` B, SHA-256 `dde442f15563b323f5befb77f091f0d3402327d0096eb1b9f1d975a3b980beb8`, created empty at `2026-11-15T18:50:59.2928783Z` after `b20a44554cbf356325ad329c1a66d2fb44b36033`) |
| Unchanged `protocol.json` / `dependency-lock.json` / `model-files.json` SHA-256 | `dd8a7dc38c2a0c46103f6667f522656a2dddf5882727c18bf7b6b5426c5e2309` / `d8eeaf0fe838d9df5728f17fcbacc8b504d98b79644a524b4faa705d97c49e6e` / `085ac7ba1e25a7300846de18bdac19c7f9612bf417041643beff6a9cab6b8ea8` |
| Actual runtime pins | `transformers 4.52.1`, `torch 2.13.0+cu130`, `torchvision 0.28.0+cu130` (`torchvision-local-sha256-TOFU`: `5ae0ff50fcb43a189250a5fdb36a7dc780ea5caff469653cab1e3f32ed5d385c`), `pypdfium2 5.15.2` / PDFium `159.0.8149.0`, NVIDIA GeForce RTX 5070 Ti (`GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d`) |

## Wrapper and Helper Scripts Preserved Byte-for-Byte

This directory sets `* -text` so all committed scripts and raw outputs retain exact execution bytes and SHA-256 digests:

| File | Bytes | SHA-256 | Purpose |
| --- | ---: | --- | --- |
| [run_stages_a_to_d.py](run_stages_a_to_d.py) | 18,974 | `aa113f1467c21ad4b1a96425e2e39f432bceb1bf1503b5fa65eb3ba4d8c771a2` | Small stdlib stage wrapper invoked from `.scratch/004-staging` while `HEAD` stayed clean at `460e1d81…`; aborted immediately at Step `08` (`rc=2`) without retry or source edit |
| [download_wheels_worker.py](download_wheels_worker.py) | 5,759 | `ee609fc14d1e1bf087344835cf49b1967a66448ba6bde7f9791ca495532d2683` | Stage B.2 direct HTTPS fetcher (`stage_network` env) for the exact 32 locked wheel URLs, recording cookie/token-free receipts |
| [inspect_all_32_wheel_metadata_readonly.py](inspect_all_32_wheel_metadata_readonly.py) | 4,452 | `5b373563e1cfb7c2444061dfb65cf6e5ae43c9c6530ffb3808eee180b2587b54` | Read-only post-stop audit across all 32 downloaded wheels calling unchanged `locks.verify_wheel_metadata` |
| [capture_post_stop_state.py](capture_post_stop_state.py) | 5,409 | `dbc5602be968ffaf325ece0d6c8c6653351ac3830a77069651b3dfd86ffad181` | Read-only post-stop `host-precheck --stage during`, `status`, `pip list`, and runtime-root byte/path/reparse inventory |

## Executed Commands and Raw Outputs (`460e1d81/`)

Wrapper run (`2026-11-15T19:02:02.514776Z` to `2026-11-15T19:06:37.723570Z`, recorded in [460e1d81/summary.json](460e1d81/summary.json), `14,662` B, SHA-256 `0af1e13a11ff99490079a4e8bfb2484c0f70832a9408633022ce6dc1ad81b29a`) plus read-only post-stop snapshots (`19:08:39Z`–`19:08:40Z`):

| Output file | Env | Exit | Bytes | Raw SHA-256 | Result |
| --- | --- | ---: | ---: | --- | --- |
| [460e1d81/01-pre-stage-host-precheck-during.txt](460e1d81/01-pre-stage-host-precheck-during.txt) | `host` | 0 | 5,528 | `4ee5f585597f82431bea1413fe38bb9cb7c764a554b5b21d9caa63b575a2dd1e` | `status: "pass"`; `C:\` free `68,231,458,816` B (`>= 62,277,025,792` B initial floor); root empty |
| [460e1d81/02-pre-stage-status.txt](460e1d81/02-pre-stage-status.txt) | `stage_offline` | 0 | 702 | `dc6ddc2324fc694b529c0440d905d2f177c52b4f7c08ac5f15509bc1bf4e4c9c` | `head: 460e1d81de14c6f77ea4a026bc4b3ab36407bdf7`, `harness_clean: true` |
| [460e1d81/03-stage-a-layout.txt](460e1d81/03-stage-a-layout.txt) | stdlib | 0 | 710 | `4bc737c61cedf920c7b2b3944ed66b903c67f01c6487f0c024876bf0a805fbc8` | Created exact 9 owned subdirs from `protocol.json`; `0` reparse points |
| [460e1d81/04-after-stage-a-host-precheck-during.txt](460e1d81/04-after-stage-a-host-precheck-during.txt) | `host` | 0 | 5,528 | `8bf6f4fd6d9d6272376b380f48407f3a4f9dd225fd8555904324b2a4b6d0e750` | `status: "pass"`; `C:\` free `68,230,844,416` B |
| [460e1d81/05-stage-b-venv-create.txt](460e1d81/05-stage-b-venv-create.txt) | `stage_offline` | 0 | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | Created `C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv` with CPython `3.12.10` (`8.187s`) |
| [460e1d81/06-stage-b-bundled-pip-version.txt](460e1d81/06-stage-b-bundled-pip-version.txt) | `stage_offline` | 0 | 97 | `30368030d5d7b03a7b1905b3c3e6c8e42931b78ffa3c9fc0f321e822f880f351` | Bundled `pip 25.0.1` recorded and never upgraded |
| [460e1d81/06b-stage-b-initial-pip-list.txt](460e1d81/06b-stage-b-initial-pip-list.txt) | `stage_offline` | 0 | 40 | `1daa89099b9ac9f9efd85accd1a0bd96e66b37a574559d6e016594672ebba55a` | `[{"name": "pip", "version": "25.0.1"}]` |
| [460e1d81/07-stage-b-download-wheels.txt](460e1d81/07-stage-b-download-wheels.txt) | `stage_network` | 0 | 42,722 | `0c2b306fb0139ca07cbaf2b4f461b9f9498cdef405aef15a5e3eab886bcf339f` | Downloaded exact **32/32 locked wheels** (`1,974,477,651` B, `264.625s`); `all_sizes_and_hashes_match_lock: true`; no cookies/auth headers |
| [460e1d81/08-stage-b-verify-wheelhouse.txt](460e1d81/08-stage-b-verify-wheelhouse.txt) | `stage_offline` | **2** | 1,145 | `347ecb1dc3a3dcb645db36ea93439081a2e6861168137ad93518a80f8e69ef89` | **STOPPED FAIL-CLOSED (`BLOCKED` / `HASH_MISMATCH`)** at `fsspec-2025.10.0-py3-none-any.whl`: `(python_version<"3.14")` in raw wheel `METADATA` vs `python_version<"3.14"` in PyPI JSON graph |
| [460e1d81/08b-readonly-32-wheel-audit.json](460e1d81/08b-readonly-32-wheel-audit.json) | read-only | 0 | 30,682 | `dce3cc91c4047ea714613fc9324c43068a79713a61aaa4952a9e2bef2725bd2b` | All **32/32** wheel filenames, sizes, SHA-256s, and both PEP 658 digests (`torch`, `torchvision`) match; **29/32** pass `verify_wheel_metadata`; **3/32** (`fsspec`, `psutil`, `urllib3`) fail on 5 extra-gated singleton-parenthesized marker atoms |
| [460e1d81/09-post-stop-host-precheck-during.txt](460e1d81/09-post-stop-host-precheck-during.txt) | `host` | 0 | 5,528 | `cfaaf18c6a6fc3e31fac10a3557d2aa682995cd387c6fd82b3de0179985b9375` | `status: "pass"` at `19:08:39Z`; `C:\` free `68,770,099,200` B |
| [460e1d81/10-post-stop-status.txt](460e1d81/10-post-stop-status.txt) | `stage_offline` | 0 | 702 | `dc6ddc2324fc694b529c0440d905d2f177c52b4f7c08ac5f15509bc1bf4e4c9c` | `head: 460e1d81de14c6f77ea4a026bc4b3ab36407bdf7`, `harness_clean: true` |
| [460e1d81/11-post-stop-resource-inventory.json](460e1d81/11-post-stop-resource-inventory.json) | read-only | 0 | 3,892 | `b98374d41c734e1809afb4928c4d839107891273e667393aa90f748f4aa76fb4` | `893` files, `1,986,484,301` B, `0` reparse points, `max_path_len: 144`, `venv` holds only `pip 25.0.1` |

## Blocker Diagnosis (`COORD-Q0-02`)

1. **All 32 wheel payloads match the frozen lock 100%:** Every file in `C:\Users\jackg\eLedgerCare-Q0\WP-0005\wheelhouse` matches its locked filename, byte count (`1,974,477,651` B total), and SHA-256 digest (`31` publisher-declared + `torchvision-0.28.0+cu130` `local-sha256-TOFU` `5ae0ff50fcb43a189250a5fdb36a7dc780ea5caff469653cab1e3f32ed5d385c`). Both CUDA wheels (`torch` and `torchvision`) also match their published PEP 658 `.metadata` SHA-256 digests (`c70f358c…` and `f8e91ee9…`).
2. **Exact representation mismatch in `q0harness/locks.py:_req_norm` (`L261–275`):** `_req_norm` strips parentheses before `;` (`spec`) but retains parentheses inside `marker`. PyPI Warehouse's JSON API (`packaging.markers.Marker` serializer, recorded in Astra `/007` `metadata-lock.json`) strips redundant parentheses around single comparison atoms `(ident op "lit")` while preserving parentheses around compound expressions (such as `(os_name == "nt" and platform_python_implementation != "PyPy")` in `psutil`, which already matched). Across all 32 real wheels (`850` total `Requires-Dist` edges), **29 wheels pass** and **3 publisher-hashed PyPI wheels fail on 5 inactive extra-gated edges**:
   - `fsspec-2025.10.0-py3-none-any.whl` (`1/101` edges): wheel `zstandard; (python_version < '3.14') and extra == 'test-full'` vs graph `zstandard; python_version < "3.14" and extra == "test-full"`
   - `psutil-7.1.3-cp37-abi3-win_amd64.whl` (`2/38` edges): wheel `colorama ; (os_name == "nt") and extra == 'dev'` and `pyreadline ; (os_name == "nt") and extra == 'dev'` vs graph without `(...)` around `os_name == "nt"`
   - `urllib3-2.5.0-py3-none-any.whl` (`2/5` edges): wheel `brotli>=1.0.9; (platform_python_implementation == 'CPython') and extra == 'brotli'` and `brotlicffi>=0.8.0; (platform_python_implementation != 'CPython') and extra == 'brotli'` vs graph without `(...)` around `platform_python_implementation ...`

## Preserved Resource State and Non-Executed Stages

- `C:\Users\jackg\eLedgerCare-Q0\WP-0005` is preserved intact (`1,986,484,301` B across `893` files, `0` reparse points, longest path `144` chars `< 240` with `LongPathsEnabled=0`; `C:\` free `68,770,086,912` B):
  - `wheelhouse`: `32` verified wheel files (`1,974,477,651` B); `requirements.lock.txt` not yet written.
  - `venv`: `861` files (`12,006,650` B); `pip list` contains only bundled `pip 25.0.1`.
  - `hf-home`, `models`, `notices`, `pip-cache`, `runs`, `temp`, `uv-cache`: `0` files (`0` B).
- **Not executed (stopped before Stage B.4):** `write-requirements`, offline `--require-hashes` wheel installation, `pip check`, Stage C model/notice acquisition and verification, Stage D `preflight-cpu` / real `pypdfium2` 4-page render, any `torch`/`transformers` import, or any GPU lease/execution.
