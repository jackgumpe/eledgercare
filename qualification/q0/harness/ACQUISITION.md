# Q0 artifact and dependency acquisition / verification plan

**Nothing in this file has been executed by the harness author, except the read-only Stage A0 host precheck (see the checkpoint evidence).** Each later stage needs the coordinator release named in its heading. Every command is explicit, isolated under the task root, hash-verified and fail-closed. Nothing writes to global Python, user caches, `TEMP`, or any shared "latest" path.

Stage processes get the environment from `environment.build_stage_env`: an allowlist with no inherited credentials and no pip or HF configuration. It contains:

- `PIP_CONFIG_FILE=NUL`;
- `PIP_CACHE_DIR`, `UV_CACHE_DIR` and `TEMP`/`TMP`/`TMPDIR` under the root;
- `HF_HOME` and `HF_HUB_CACHE` under the root;
- `HF_HUB_DISABLE_XET=1`, so downloads use plain HTTPS; final verification is transport-independent anyway;
- for offline steps, `PIP_NO_INDEX=1` and `HF_HUB_OFFLINE=1`.

The examples are PowerShell. `$Repo` is the owned worktree of the executing owner, and `$Root` is the coordinator-selected root:

```powershell
$Repo = 'C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-harness'
$Root = 'C:\Users\jackg\eLedgerCare-Q0\WP-0005'
$Q0   = Join-Path $Repo 'qualification\q0\harness\q0.py'
$Py   = 'C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe'   # CPython 3.12.10 x64 (lock platform)
```

## Stage A0: read-only host precheck (allowed now; repeat at every stage boundary)

`& $Py -I -B $Q0 host-precheck --stage initial` records and checks:

- System32 `msvcp140.dll`, `vcruntime140.dll` and `vcruntime140_1.dll`: presence, size, SHA-256 and file version;
- `LongPathsEnabled`, and the longest harness-known path, which must be below 240 characters while long paths are disabled;
- paging-file configuration, commit limit and available commit, and physical memory;
- C: free bytes, against **≥ 58 GiB** (`initial`) or **≥ 20 GiB** (`during`);
- that the storage root is absent;
- both frozen read-only `nvidia-smi` queries: one line, the leased UUID, RTX 5070 Ti, compute_cap 12.0.

Exit 4 means a precondition failed; stop. This creates no CUDA context, does not take GPU ownership, and does not bound pagefile growth outside the root.

## Stage A: storage (release: installation/storage stage)

1. Re-run A0 with `--stage initial`. The planned peak, wheels plus model plus venv/cache/temp, is bounded only for task-owned paths; the floor is a stop buffer.
   - wheels: 1,974,477,651 B advertised (lock);
   - model runtime objects: 6,699,195,181 B (manifest);
   - notice: 14,107 B.
2. Create only the owned layout from `protocol.json` `storage.subdirs`:
   - `hf-home`, `models\Unlimited_OCR_2_04809669`, `notices\Unlimited-OCR-2_0480966…`;
   - `wheelhouse`, `venv`, `pip-cache`, `uv-cache`, `temp`;
   - `runs\author` and `runs\reviewer`.

   The root must not pre-exist with foreign content. `check_storage_root` refuses any other root, and any root overlapping the repository, worktrees, TEMP, APPDATA/LOCALAPPDATA or `~/.cache`.

## Stage B: wheels, offline hash-only install (release: `eldq0-release/2` stage `install`)

**Stop gate.** The torchvision wheel has no publisher SHA-256. `q0.py lock-check` reports `installable: false`, and every install-stage command refuses with `ACQUISITION_PROVENANCE_PENDING`. The gate opens only when all three of these hold:

1. **Receipt bound.** The independent reviewer's published local-digest receipt is bound in `locks/dependency-lock.json` as `local_hash_records[0]`, with `hash_kind: local-sha256-TOFU`. The receipt must come from exactly the official URL `https://download-r2.pytorch.org/whl/cu130/torchvision-0.28.0%2Bcu130-cp312-cp312-win_amd64.whl`. Its size must be 9,091,113 B, and its METADATA SHA-256 must equal `f8e91ee987603053e2166e2e4063ddcfb533f266c88bae82b7f79119aadceb59` with `Requires-Dist: torch (==2.13.0)`. The record carries the receipt's commit, path and Git blob.
2. **New candidate reviewed.** That lock revision is frozen in a new harness candidate and reviewed.
3. **Exception accepted.** The install release lists `torchvision-local-sha256-TOFU` in `accepted_provenance_exceptions`.

Then:

1. **Venv.** Create it from the exact interpreter: `& $Py -m venv "$Root\venv"`. Record the bundled pip version and never upgrade it.
2. **Download.** For each of the 32 locked wheels, fetch its locked `url` (`files.pythonhosted.org` or `download-r2.pytorch.org`) into `$Root\wheelhouse` under the network stage environment. Use direct URLs only: no resolver, no extra index, no sdist and no extras. One way is `pip download --no-deps --only-binary=:all: <locked url>`, run with the venv interpreter.
3. **Verify the wheelhouse.** `& "$Root\venv\Scripts\python.exe" -s $Q0 verify-wheelhouse "$Root\wheelhouse" --release <install.json>` checks:
   - exactly the 32 filenames;
   - each locked size and effective SHA-256;
   - for torchvision, its own `dist-info/METADATA` digest and `torch (==2.13.0)` requirement, read from the ZIP with no extraction.
4. **Write requirements.** `& "$Root\venv\Scripts\python.exe" -s $Q0 write-requirements "$Root\wheelhouse\requirements.lock.txt" --release <install.json>` writes 32 lines of the form `name==version --hash=sha256:…`. Torch is `torch==2.13.0+cu130`, never the CPU `torch 2.13.0` (Q0R-08).
5. **Install offline, hash-only (Q0R-08):**
   ```powershell
   & "$Root\venv\Scripts\python.exe" -s -m pip install --no-index --no-deps --only-binary=:all: --require-hashes --find-links "$Root\wheelhouse" -r "$Root\wheelhouse\requirements.lock.txt"
   & "$Root\venv\Scripts\python.exe" -s -m pip check
   ```
6. **Path lengths.** Record the venv's longest installed path (`hostcheck.max_path_under`). With `LongPathsEnabled=0` (observed 2026-11-15T16:00Z), any path ≥ 240 characters stops the stage. No registry change is authorized.

## Stage C: model artifacts (release: model download)

Use the locked `huggingface-hub` from the task venv, under the network stage environment. The download is pinned to the exact revision and the **18 runtime objects** only. The model card goes separately into the notice directory. `.gitattributes`, the paper PDF, `assets/**` and the SGLang `wheel/**` are never fetched:

```powershell
& "$Root\venv\Scripts\python.exe" -s -c "import json,sys; from huggingface_hub import snapshot_download; m=json.load(open(sys.argv[1])); r='0480966938291445591f69f08a13b041c073a96a'; snapshot_download('baidu/Unlimited-OCR-2', revision=r, local_dir=sys.argv[2], allow_patterns=[f['path'] for f in m['files']]); snapshot_download('baidu/Unlimited-OCR-2', revision=r, local_dir=sys.argv[3], allow_patterns=[n['path'] for n in m['notices']])" "$Repo\qualification\q0\harness\manifests\model-files.json" "$Root\models\Unlimited_OCR_2_04809669" "$Root\notices\Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a"
& "$Root\venv\Scripts\python.exe" -s $Q0 verify-model "$Root\models\Unlimited_OCR_2_04809669" --notices "$Root\notices\Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a"
```

`verify-model` checks:

- the normalized identifier-safe path;
- the exact 18-object set: 16 git-blob SHA-1 + size, and 2 LFS SHA-256 + size. xetHash and pointer OIDs are never used;
- no links or reparse points;
- only `.cache/huggingface/**` metadata without `.py` is tolerated;
- the notice digest;
- the static save-path facts on all 10 Python files.

Cached files are never edited. The postprocessor (`utils/process_unlimitedOCR2.py@3de5de31…`) is not executed by Q0.

## Stage D: CPU preflight in the task venv (no GPU lease needed)

```powershell
& "$Root\venv\Scripts\python.exe" -s -P -X utf8 $Q0 preflight-cpu --release <install.json> --model-dir "$Root\models\Unlimited_OCR_2_04809669" --notices "$Root\notices\Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a"
```

This checks:

- that the installed set equals the 32 locked distributions, plus `pip` only;
- that `flash_attn`, `xformers` and `triton` have `find_spec is None`;
- the real `pypdfium2`/PDFium identity;
- that F01 and F07 render byte-exactly to the frozen raster digests;
- the model files, the notice and the static facts again.

torch is not imported. Re-run A0 with `--stage during`.

## Stage E: GPU execution (release: `eldq0-release/2` stage `execute` + observed lease)

The coordinator issues a release JSON with these fields:

- `schema`: `eldq0-release/2`, `packet`: `WP-0005`, `stage`: `execute`;
- `sequence`: `004`, or `005` for the reviewer's reproduction;
- `released_by`: `eld-coordinator`, `release_commit`;
- `harness_commit`: must equal the executing worktree's HEAD, with a clean harness subtree;
- `accepted_review`: `{reviewer: eld-q0-reviewer, report_commit, evidence_commit}`;
- `protocol_sha256`, `lock_sha256`, `accepted_provenance_exceptions`, `storage_root`, `gpu_uuid`, `lease_id`.

`q0.py status` prints the current digests and code identity. Then:

```powershell
& $Py -s -P $Q0 execute --owner author --release <execute.json>
```

The supervisor creates a new run directory, builds the allowlisted child environment and starts `venv\Scripts\python.exe -s -P -X utf8 q0.py child ...`. It enforces the timeouts, stall window, log cap and 20 GiB free-space floor, and runs both observer queries. It preserves the raw stdout/stderr and writes `supervisor.json`, which includes the log-marker scan and the free-space samples. The child writes `evidence\*.json`, the raw outputs and `outcome.json`.

Run evidence stays under `$Root\runs\author\<run>`. Publication into Git is a separate, reviewed step that never includes weights, wheels or private data.
