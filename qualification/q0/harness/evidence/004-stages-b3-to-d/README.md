# WP-0005 /004 Stage B.3–D staging completion checkpoint (`eld-q0-harness`)

This is a **stage-evidence checkpoint** by **Gemini 4 Carbon (High)** author session `bd92ddc3-af60-4096-b683-65386d81b718` (`eld-q0-harness`), not an independent review and not the final canonical `/004` verification report (`docs/agent-reports/eld-q0-harness/WP-0005/004_2026-11-15_verification_eld-q0-harness.md` remains unfilled pending a separately bound coordinator `execute` release and observed concurrency-1 GPU lease). Original `/002` implementation remains attributed to stopped Opus session `04e0efba-5292-4cae-b922-1517dee7bbed`; historical Stage A–B.3 stop checkpoint `68855420b2dece941eb90c42c69de3c80b47aa06` is preserved untouched; separate Carbon reviewer `0815536f-045a-4112-8a89-ebf0e0cc782f` (`eld-q0-reviewer`) remains independent.

| Item | Value |
| --- | --- |
| Executing branch / worktree | `qualification/wp-0005-harness` / `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-harness` |
| Clean executing `HEAD` throughout commands | `099a2fa74cdc2df6068c437edf3971eb37e9f07d` |
| Accepted harness core (`0` core edits) | `41d6204648e4115ab197507d1a22f6d5c7f3e784` (author `/010` evidence `6dc2d01c84da99d751994cce00a2c82df053c215`) |
| Independent `/011` evidence / report | `37836f6ce816218954a61c7137241790ce8055a2` / `c8daa97c5be6bc67931b215652a7a0f6ced621ef` (integrated `4317ea99bb85b96983c7dc3a0ed828a0a6a6ed1f`; resumption release `12165f3c69f3aa46b79f1acee29427bd5dd9ec37`) |
| Bound install release | `author-install-after-011.json` (`912` B, SHA-256 `501a0c06a2e23aa51ac1c4081ba15e6ac131f17b8d5f365a1fe638c61e7ac91a`, `release_commit` `e0ee634f6a92624c8c305c1c8730f79e95b93647`) |
| Unchanged `protocol.json` / `dependency-lock.json` / `model-files.json` SHA-256 | `dd8a7dc38c2a0c46103f6667f522656a2dddf5882727c18bf7b6b5426c5e2309` / `d8eeaf0fe838d9df5728f17fcbacc8b504d98b79644a524b4faa705d97c49e6e` / `085ac7ba1e25a7300846de18bdac19c7f9612bf417041643beff6a9cab6b8ea8` |
| Actual runtime pins | `transformers 4.52.1`, `torch 2.13.0+cu130`, `torchvision 0.28.0+cu130` (`torchvision-local-sha256-TOFU`: `5ae0ff50fcb43a189250a5fdb36a7dc780ea5caff469653cab1e3f32ed5d385c`), `pypdfium2 5.15.2` / PDFium `159.0.8149.0`, `baidu/Unlimited-OCR-2@0480966938291445591f69f08a13b041c073a96a` (`18` runtime objects + `1` separate notice), RTX 5070 Ti (`GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d`, **not leased/imported yet**) |

## Preserved Continuation Wrapper and Machine Summaries

This directory sets `* -text` so committed scripts and raw outputs retain exact execution bytes and SHA-256 digests:

- [resume_stages_b3_to_d.py](resume_stages_b3_to_d.py): `19,972` B, SHA-256 `825039b2bc74b7a5c0ed81b544a542dabfcac7b1e177f79cc483ccce5ce7d56d` (`git_blob_sha1` `c51a27adac5008f0da57f8f390044da867641799`)
- [099a2fa7/summary.json](099a2fa7/summary.json): `25,808` B, SHA-256 `791e9cdec0e598abcf1d0bccf6153fe8d0f9cbe7cac16d1195d1487b8f29ab21` (`2026-11-15T19:57:32.144712Z` to `2026-11-15T20:16:10.556672Z`)
- [099a2fa7/15-resource-inventory.json](099a2fa7/15-resource-inventory.json): `4,278` B, SHA-256 `63594c2940d7b926c605cab8ad4b6f8f48a6d96cc8accb7585c55d5686541500`

## Executed Steps (`099a2fa7/`)

| Output file | Env | Exit | Bytes | Raw SHA-256 | Result |
| --- | --- | ---: | ---: | --- | --- |
| [099a2fa7/01-pre-resume-host-precheck-during.txt](099a2fa7/01-pre-resume-host-precheck-during.txt) | `host` | 0 | 5,446 | `006473107a703bbca391c015aa9aaf2ebca14115c3513f8b52da4b8516acd08a` | `status: "pass"`; `C:\` free `68,745,740,288` B |
| [099a2fa7/02-pre-resume-status.txt](099a2fa7/02-pre-resume-status.txt) | `stage_offline` | 0 | 702 | `8e15926f1c6ef9dbfdd3a0da3b8eadc24280245e3443d132f15c39f8af6be463` | `head: 099a2fa74cdc2df6068c437edf3971eb37e9f07d`, `harness_clean: true` |
| [099a2fa7/02b-pre-resume-pip-version.txt](099a2fa7/02b-pre-resume-pip-version.txt) | `stage_offline` | 0 | 97 | `30368030d5d7b03a7b1905b3c3e6c8e42931b78ffa3c9fc0f321e822f880f351` | Existing `venv` bundled `pip 25.0.1` confirmed |
| [099a2fa7/02c-pre-resume-pip-list.txt](099a2fa7/02c-pre-resume-pip-list.txt) | `stage_offline` | 0 | 40 | `1daa89099b9ac9f9efd85accd1a0bd96e66b37a574559d6e016594672ebba55a` | `[{"name": "pip", "version": "25.0.1"}]` before install |
| [099a2fa7/03-stage-b3-verify-wheelhouse.txt](099a2fa7/03-stage-b3-verify-wheelhouse.txt) | `stage_offline` | 0 | 18,893 | `9738901be246bab920191056c7738b98f36a550a75d09bb24be2c6a491b6e0e8` | `q0.py verify-wheelhouse` passes all 32 wheels (`1,974,477,651` B, 850 edges, both PEP 658 digests) |
| [099a2fa7/04-stage-b4-write-requirements.txt](099a2fa7/04-stage-b4-write-requirements.txt) | `stage_offline` | 0 | 180 | `1151a0adbe1eeabe0a15d931ba509071874a98342ebad782bb801a3a9b7697a8` | Wrote 32-line `requirements.lock.txt` (`3,079` B, SHA-256 `a1598dca06d4eea486c1bf0e9b8e1ca841e468cd6ad454b0e59f48890d7f9961`) |
| [099a2fa7/05-stage-b5-pip-install-offline.txt](099a2fa7/05-stage-b5-pip-install-offline.txt) | `stage_offline` | 0 | 6,989 | `9f0a7cada4961db8fe3237d64b7eb4f0f92a2cd2dca9e8171723570342cb6b37` | Offline `--no-index --no-deps --only-binary=:all: --require-hashes` installed all 32 locked distributions (`180.485s`) |
| [099a2fa7/06-stage-b5-pip-check.txt](099a2fa7/06-stage-b5-pip-check.txt) | `stage_offline` | 0 | 31 | `672aec65a45bed50e70229c70934a7eebf0462595c459b83023027645d57cccf` | `No broken requirements found.` |
| [099a2fa7/06b-stage-b5-installed-pip-list.txt](099a2fa7/06b-stage-b5-installed-pip-list.txt) | `stage_offline` | 0 | 1,423 | `1f46a793279320d0dd446437e7e15604e9e2ee9aaf309c505731ca0aff87d3d8` | Exact `33` distributions (`32` locked + unchanged `pip 25.0.1`) |
| [099a2fa7/07-stage-b6-venv-max-path-and-set.txt](099a2fa7/07-stage-b6-venv-max-path-and-set.txt) | `stage_offline` | 0 | 722 | `a7f8da709e7b28b7cca419eb198a6dd8644fb9f45a025140ee5b9848296c255a` | `venv` `max_len: 234` (`< 240` with `LongPathsEnabled=0`); `flash_attn`/`xformers`/`triton` `find_spec is None`; `torch`/`transformers` not imported |
| [099a2fa7/08-after-stage-b-host-precheck-during.txt](099a2fa7/08-after-stage-b-host-precheck-during.txt) | `host` | 0 | 5,446 | `e7e69d4767628c5257bf6b5cfeb340102558beb1a0cdcde0152c367ccc7108be` | `status: "pass"`; `C:\` free `65,421,529,088` B |
| [099a2fa7/09-stage-c1-model-and-notice-download.txt](099a2fa7/09-stage-c1-model-and-notice-download.txt) | `stage_network` | 0 | 926 | `1012813666d616c58800dfa97349ec82e8d441a9e631b0e1856796ee0d46a139` | `snapshot_download` fetched exact 18 runtime objects + separate `README.md` at `0480966938291445591f69f08a13b041c073a96a` (`906.719s`; `huggingface_hub`'s built-in stream reader resumed two CDN read timeouts cleanly within the single invocation); `torch`/`transformers` not imported |
| [099a2fa7/10-stage-c2-verify-model.txt](099a2fa7/10-stage-c2-verify-model.txt) | `stage_offline` | 0 | 8,629 | `cca23b62fb8b22599caf77d08b9482fc467a189abf7babcc0ba1fc49fd270dac` | `q0.py verify-model` verified all `18` runtime objects (`16` Git-blob SHA-1 + `2` LFS SHA-256, `6,699,195,181` B), notice `README.md` (`14,107` B), `0` reparse points, and static save-path facts |
| [099a2fa7/11-after-stage-c-host-precheck-during.txt](099a2fa7/11-after-stage-c-host-precheck-during.txt) | `host` | 0 | 5,446 | `0ada9918c64f612f4a1c390a908160d730068e3134b7999ad8c40801f0350bce` | `status: "pass"`; `C:\` free `58,584,940,544` B |
| [099a2fa7/12-stage-d-preflight-cpu.txt](099a2fa7/12-stage-d-preflight-cpu.txt) | `stage_offline` | 0 | 3,692 | `c00bf20be0176b2dc711575dfca9c2196040d5bf9b765989cde767200f1a80c9` | `q0.py preflight-cpu`: `status: "pass"`; `pypdfium2 5.15.2` / PDFium `159.0.8149.0@sourcebuild-toolchained`; `SYN-WO-01-v0-clean` p1 and `SYN-MP-01-v0-clean` p1–p3 RGB rasters byte-exact; 33 distributions + 18 runtime objects + notice + static safety verified |
| [099a2fa7/13-after-stage-d-host-precheck-during.txt](099a2fa7/13-after-stage-d-host-precheck-during.txt) | `host` | 0 | 5,446 | `63e97f7ba65dc9a8070eb0ad69b8acdc76b1d8ad507c31298ef49d89daf96873` | `status: "pass"`; `C:\` free `58,584,862,720` B (`>= 21,474,836,480` B during floor) |
| [099a2fa7/14-post-stage-status.txt](099a2fa7/14-post-stage-status.txt) | `stage_offline` | 0 | 702 | `8e15926f1c6ef9dbfdd3a0da3b8eadc24280245e3443d132f15c39f8af6be463` | `head: 099a2fa74cdc2df6068c437edf3971eb37e9f07d`, `harness_clean: true` throughout |

## Post-Stage Resource State & Non-Executed Boundary

Per [099a2fa7/15-resource-inventory.json](099a2fa7/15-resource-inventory.json):

- `C:\Users\jackg\eLedgerCare-Q0\WP-0005` total: **`27,755` files, `2,927` dirs, `11,930,081,346` B, `0` reparse points, `max_path_len: 234` (`< 240` with `LongPathsEnabled=0`)**; `C:\` free **`58,584,571,904` B**.
  - `venv`: `27,682` files, `2,908` dirs, `3,256,389,308` B, `max_path_len: 234`; `32` locked distributions + bundled `pip 25.0.1`.
  - `wheelhouse`: `33` files (`32` wheels + `requirements.lock.txt`), `1,974,480,730` B, `max_path_len: 99`.
  - `models\Unlimited_OCR_2_04809669`: `37` files (`18` runtime objects `6,699,195,181` B + `19` tolerated `.cache/huggingface/**` metadata files), `6,699,197,096` B, `max_path_len: 139`.
  - `notices\Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a`: `3` files (`README.md` `14,107` B + `2` `.cache/huggingface/**` metadata files), `14,212` B, `max_path_len: 149`.
  - `hf-home`, `pip-cache`, `runs`, `temp`, `uv-cache`: `0` files, `0` B.
- **Not executed (held for Stage E coordinator `execute` release + observed GPU lease):** any `torch`, `transformers`, tokenizer, or custom model import, CUDA context creation, model weight load, or GPU qualification run (`q0.py execute`).
