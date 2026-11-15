# Q0 artifact and dependency acquisition / verification plan

**Nothing in this file has been executed.** No directory, download, installation, model load or GPU use is released by WP-0005 `/002`. Each stage needs the coordinator release named in its heading. Every command is explicit, isolated under the task root, hash-verified and fail-closed. Nothing writes to global Python, user caches, `TEMP`, or any shared "latest" path. Steps marked **BLOCKED (/001)** wait for the final lock: `locks/dependency-lock.json` must have `status: final`, with provenance pinned to the published `/001` proposal and the `/003` review.

The examples are PowerShell. `$Repo` is the owned worktree of the executing owner, and `$Root` is the coordinator-selected root:

```powershell
$Repo = 'C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-harness'
$Root = 'C:\Users\jackg\eLedgerCare-Q0\WP-0005'
$Q0   = Join-Path $Repo 'qualification\q0\harness\q0.py'
```

## Stage A: storage (release: installation/storage stage)

1. Record the actual free bytes before creating anything: `(Get-PSDrive C).Free`. Compare against the budget:
   - pinned model files 6,699,209,288 B (weights 6,688,305,576 B), from `manifests/model-files.json`;
   - plus wheelhouse, venv and peak temp/cache bytes. These are **BLOCKED (/001)** estimates.
2. Create only the owned layout: `hf-home`, `models\0480966938291445591f69f08a13b041c073a96a`, `wheelhouse`, `venv`, `runs\author`, `runs\reviewer`. The root must not pre-exist with foreign content. `check_storage_root` refuses any root other than the selected one, or one that overlaps the repository, worktrees, TEMP, APPDATA/LOCALAPPDATA or `~/.cache`.

## Stage B: wheels and venv, BLOCKED (/001)

1. Interpreter: the exact Python version in the lock, at an exact path recorded with its SHA-256. The host currently shows only Python 3.12.10 (`C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe`). Whether that is acceptable is a `/001` decision.
2. Download each locked wheel without dependency resolution, from its locked https index only:
   ```powershell
   & $Python -s -m pip download --no-deps --only-binary=:all: --dest "$Root\wheelhouse" --index-url <locked index_url> "<name>==<version>"
   ```
3. `& $Python -s $Q0 verify-wheelhouse "$Root\wheelhouse"`. The wheelhouse must contain exactly the locked filenames, each matching its SHA-256.
4. `& $Python -s $Q0 write-requirements "$Root\wheelhouse\requirements.lock.txt"`. This writes one `name==version --hash=sha256:...` line per wheel.
5. Create the venv and install offline:
   ```powershell
   & $Python -m venv "$Root\venv"
   & "$Root\venv\Scripts\python.exe" -s -m pip install --no-index --no-deps --require-hashes --find-links "$Root\wheelhouse" -r "$Root\wheelhouse\requirements.lock.txt"
   ```
   Set `PIP_CONFIG_FILE=NUL` and `PIP_NO_CACHE_DIR=1` for these processes only. Do not change user/global pip configuration.

## Stage C: model artifacts (release: model download)

Use the locked `huggingface-hub` from the task venv. `HF_HOME` is `$Root\hf-home`, applied for this process only. The download is pinned to the exact revision and the 19-file allowlist, so `.gitattributes`, the paper PDF, `assets/**` and the SGLang `wheel/**` are never fetched:

```powershell
$env:HF_HOME = "$Root\hf-home"; $env:HF_HUB_DISABLE_TELEMETRY = '1'
& "$Root\venv\Scripts\python.exe" -s -c "import json,sys; from huggingface_hub import snapshot_download; m=json.load(open(sys.argv[1])); snapshot_download('baidu/Unlimited-OCR-2', revision='0480966938291445591f69f08a13b041c073a96a', local_dir=sys.argv[2], allow_patterns=[f['path'] for f in m['files']])" "$Repo\qualification\q0\harness\manifests\model-files.json" "$Root\models\0480966938291445591f69f08a13b041c073a96a"
& "$Root\venv\Scripts\python.exe" -s $Q0 verify-model "$Root\models\0480966938291445591f69f08a13b041c073a96a"
```

`verify-model` checks:

- the exact file set;
- git-blob SHA-1 for the 17 non-LFS files and LFS SHA-256 for the 2 shards;
- that only `.cache/huggingface/**` metadata without `.py` exists besides those files;
- that the static save-path facts hold on all 10 Python files, including the three that are not in the committed snapshots.

Cached files are never edited. The postprocessor (`utils/process_unlimitedOCR2.py@3de5de31a7e5c925e84af68ef12b1b8d7db9e24a`) is not executed by Q0. Its acquisition and hashing are deferred to the scoring stage, and the pin is preserved in `protocol.json`.

## Stage D: CPU preflight in the task venv (no GPU lease needed)

```powershell
& "$Root\venv\Scripts\python.exe" -s -P -X utf8 $Q0 preflight-cpu --model-dir "$Root\models\0480966938291445591f69f08a13b041c073a96a"
```

This checks that the installed set equals the lock and that the forbidden backends are absent. It also checks the real `pypdfium2`/PDFium identity, renders F01 and F07, and requires byte-exact equality with the frozen raster digests. Finally it re-verifies the model files and the static facts. torch is not imported.

`preflight-cpu` does **not** check the read-only `nvidia-smi` observer command in `protocol.json` (`gpu.observer_cmd`). Its argument form, which combines `--query-gpu` and `--query-compute-apps` in one call, is unvalidated. Run it once, read-only, at this stage. If it errors, a reviewed protocol amendment must split it before the lease.

## Stage E: GPU execution (release: /004 record + observed lease)

The coordinator issues a release JSON with these fields:

- `schema`: `eldq0-release/1`
- `packet`: `WP-0005`
- `sequence`: `004`, or `005` for the reviewer's reproduction
- `released_by`: `eld-coordinator`
- `release_commit`, `protocol_sha256`, `lock_sha256`, `gpu_uuid`, `lease_id`, `storage_root`

`q0.py status` prints the current protocol and lock digests. Then:

```powershell
& $Python -s -P $Q0 execute --owner author --release <release.json>
```

The supervisor creates a new run directory, builds the allowlisted child environment and starts `venv\Scripts\python.exe -s -P -X utf8 q0.py child ...`. It enforces the guards and writes `supervisor.json`. The child writes `evidence\*.json`, the raw outputs and `outcome.json`. Run evidence stays under `$Root\runs\author\<run>`. Publication into Git is a separate, reviewed step that never includes weights or private data.
