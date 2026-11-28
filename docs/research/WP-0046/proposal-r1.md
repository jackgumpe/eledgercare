# WP-0046 Stage 0 — Direct-Stock Qualification Proposal (`wp0046-direct-stock-r1`)

| Field | Value |
| --- | --- |
| Proposal ID / Revision | `wp0046-direct-stock-r1` (**Post-opening Stage-0 revision; prospective only; NOT implemented; Stage 1 HELD**) |
| Sole Proposal Author | `eld-owner-probe` (Gemini 4 Neon (XHigh) via local `agy` CLI; `xhigh` requested) |
| Repository / Branch / Pins | `jackgumpe/eledgercare` / `research/wp-0046-direct-stock` / reservation `281b71d1dbf75b8e121a1ea577c0385ae8683555`; intake `e43af2e263f55478d1d551a5a095536b042589c2` |
| Provenance & Independence | Supersedes Turn-1 [`proposal.md`](proposal.md) (`6fa242950ffd4dfd1d19accc9271e88aada2d552`, retained immutable) to address peer criticisms `M1`–`M5` and `O1`–`O8` (`eld-rd-reviewer` tip `1c9690b9eab22dfdf0c943815f5440e6563f2350`) and read-only Git `e43af2e2` verifications. Because this revision incorporates peer feedback, **it is NOT independently certified** and requires fresh non-author review by `eld-rd-reviewer`. |
| Machine-Readable Companions | [`register-r1.json`](register-r1.json) (`118` original + `44` extended = `162` obligations; SHA-256 `1876767176589dd076151810f3905f2a08a6638823d7aebd4d5565fc2c995c26`), [`build_register_r1.py`](build_register_r1.py), [`corrigenda-r1.md`](corrigenda-r1.md), [`controls_r1.py`](controls_r1.py), [`exchange.md`](exchange.md) |
| Target Execution Status | **0 target runs executed** (`0/5` Stage-1a units, `0/2` Stage-1b arms, `0/2` Stage-2 stock loads, `0/8` Stage-2 calls, `0/5` Stage-2 qualified rows, `0/30` Stage-3 private block calls, `0/8` linked bridges). WP-0037 stays parked. |

---

## 1. Scientific Question, Baseline, and What Changed From `v1` to `r1`

### 1.1 Question and Mechanism Under Study
Can a new, separately authored and independently reviewed ordinary-user Windows supervision layer launch the pinned base CPython 3.12.10 executable (`@base/python.exe`, SHA-256 `4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a`) directly via `CreateProcessW`—eliminating the WP-0043/WP-0044 `@venv/Scripts/python.exe` redirector hop—while reproducing the exact closed 31-key child environment, derived effective `sys.flags`, virtual-environment package isolation (closed 33 distributions, 3 forbidden modules absent, zero `@base/Lib/site-packages` leak), in-coverage module/DLL origins, creation-scoped creator witness $E_{\rm direct}$, and continuous NTFS original-output custody $B_{\rm arm}$ required for the unmodified Q0 stock OCR reader (`Unlimited-OCR-2`, revision `0480966938291445591f69f08a13b041c073a96a`)?

### 1.2 Baseline Evidence (Strictly Separated From Prospective Target)
- **Archive — WP-0043 historical stock (`native43.json`, `disposition.json`):** 2 cold `venv` processes (`untouched`, `observed`), 8 calls through native EOS, 1/1 F07 content match (2,558 non-EOS IDs, 7,617 UTF-8 bytes), 15 FP32 score vectors (7,756,800 bytes), **formal joint verdict `M`** (`0/1` qualified pairs, `0/5` qualified rows: `sys.orig_argv[0]` reported `@base/python.exe` while `plan43.json` expected `@venv/Scripts/python.exe`, withholding 5 custody obligations). Unchanged `worker43.py` (`e43af2e2:docs/research/WP-0043/native.py`, SHA-256 `8245640f9c6a3dccdcc4a4662595ac532c2f45029894a0e8db7d8c2c7969b175`) cannot execute Stage 1 (`O1`, `O6`, `S-01`, `S-02`).
- **Archive — WP-0045 direct CPU (`disposition45.json`, `windows45.json`):** 4/4 genuine cooperative direct launches (`15/15` atoms) on a 4-byte inert `-I -S -B` worker. By Paper I T1 Corollary, this transfers **zero** dynamic evidence to stock flags, venv resolution, package/DLL origins, or GPU execution.
- **Archive — Pinned Git `e43af2e2` verifications added in `r1`:**
  - `03-pip-check-and-venv-inventory.json` (SHA-256 `503dd28f...`): exact closed **33-distribution** set = 32 pinned distributions (PEP 503 normalized) + `pip == 25.0.1`.
  - `05-preflight-cpu.json` (SHA-256 `c00bf20b...`): **3 forbidden absent modules** (`flash_attn`, `xformers`, `triton` via `find_spec(...) is None`).
  - `02-verify-wheelhouse.json` (SHA-256 `9738901b...`): all **32 wheel** filenames, sizes, payload SHA-256s, and metadata SHA-256s.
  - `docs/research/WP-0043/{timing,bindings,capture,transfer,native_observer,limits}.py`: all **6** sibling modules in `worker43.py`'s transitive local import closure match `device43.json#/worktree_executables/*/git_source_sha256` and have **0 third-party top-level imports** (pure stdlib + `ctypes`).
  - `F07.warm1.token_ids.json` (SHA-256 `532ffea0...`) + `F07.warm1.observation.json` (`prompt_len=827`): independently verify $\mathrm{Ban}_1 = \varnothing$ across 2,935 34-gram candidate starts on rows `1445..1449` (absent from standalone ZIP, present in Git `e43af2e2`).
  - Confirmed **globally absent** from public Git `e43af2e2`: WP-0043's historical `exec.backend` booleans (`tf32`, `cudnn_tf32`, `deterministic`, `autocast`) and Q0's `@venv/pyvenv.cfg` SHA-256 / `.pth` file inventory.

### 1.3 Material Amendments From Turn-1 `proposal.md` (`v1`) to `proposal-r1.md` (`r1`)
1. **Stage 1 Split Into Pure-Stdlib Stage 1a and Separate CPU-`torch` Stage 1b (`O6`, §7):** Stage 1a stops strictly **before `import torch`** (zero `torch`/CUDA DLL risk) and runs **5 scheduled units** (`2` decisive direct-stock units + `3` live control units: isolated `-I` $\to \MM$, dropped `sys.flags` $\to \UU$, omitted member $\to \MM$). Importing `torch` + `LOAD_DLL_DEBUG_EVENT` DLL-origin hashing + optional backend-flag readability probing moves to separately gated **Stage 1b**.
2. **Closed 31-Key Child Environment + Closed-World ABSENT Rule + `cpu.env.*` (`O4`):** Freezes the exact 31-key `e_child` allowlist (`7` OS pass-through + `24` explicit) plus `e_launch["__PYVENV_LAUNCHER__"]` $\to$ `e_child` ABSENT, forbids every unlisted key as typed `ABSENT`, and binds explicit `cpu.env.*` keys in `register-r1.json`.
3. **Full Static Identity & Closed-World Bindings (`O5`):** Adds explicit obligations for `@base/python.exe` digest, `@venv/Scripts/python.exe` static digest, 3+2 runtime file digests, 3 forbidden absent modules (`triton`, `flash_attn`, `xformers`), closed 33-distribution set (`32 + pip 25.0.1`), 32 wheel SHA-256s, 6 Git-verified WP-0043 sibling digests, and explicitly marks unarchived `@venv/pyvenv.cfg` digest and `*.pth` list as `unbound_pre_stage1a` hold items inside $B_T \cap \Pi_{1a}$.
4. **Explicit `O2` (`-P` vs Sibling Imports), `O3` (Prospective Venv Selection), `O7` (Outer Handle Holder), `O8` (5 Per-Row `support_choice` Keys), and `M1`–`M5` Corrigenda:** Every mathematical amendment in [`corrigenda-r1.md`](corrigenda-r1.md) (including scoped plan $\Pi_s$ counts, Stage 1→2 bridge $[\mathrm{proj}(\Pi_1)=\mathrm{proj}(\mathrm{Plan}_2)]$, derived-not-observed `Q_hash`, conjunct-wise T3a `M3`, determinism premise `M4`, `P7` Reading B, and `K3`) is bound directly into `proposal-r1.md` and `register-r1.json`.

---

## 2. Symbolic Roots, Trust Boundary, and Operative Mathematics (`#route-selection`, `#trust-writer-and-continuity`)

### 2.1 Symbolic Roots (Zero Host Paths in Public Deliverables)
`@base`, `@venv`, `@q0_root`, `@model`, `@wheelhouse`, `@repo`, `@worktree`, `@source`, `@speed_root`, `@run_root`, `@arm` are defined in [`register-r1.json`](register-r1.json) and resolved solely by a future coordinator-issued private local release manifest (`cpu.entry.coordinator_roots_manifest`).

**Trust boundary:** Ordinary interactive Windows 64-bit user token (`integrity_rid == 8192`, `elevated == 0`, `effective_admin == False`); correct Windows NTFS/Win32 kernel handle semantics; trusted frozen outer recorder/scorer, direct supervisor, and worker entries; `bInheritHandles = False`; cooperative single-writer `CREATE_NEW` + `FILE_SHARE_READ`. Hostile same-user processes, compromised OS/keys, kernel ETW tracing, customer data, E1–E3 OCR treatments, and WP-0037 remain strictly excluded.

### 2.2 Route Selection (`O1`, `O2`, `O3`)
Choose $\tau = \texttt{direct-stock}$ on a **new, separately authored, frozen, and independently reviewed supervision and worker layer** (`worker43.py` is NEVER executed unchanged; model/OCR files remain unmodified):
$$a_* = (\texttt{-s}, \texttt{-P}, \texttt{-B}, \texttt{-u}), \qquad L_* = \fn{CreateProcessW}\bigl(\texttt{@base/python.exe},\; a_* \Vert \mathrm{entry\_argv},\; e_{\rm launch},\; \texttt{0x08000006},\; \mathrm{inherit}=\mathsf{False}\bigr)$$
where `0x08000006` = `CREATE_NO_WINDOW | CREATE_SUSPENDED | DEBUG_ONLY_THIS_PROCESS`.

- **Resolution of `O2` (`-P` vs sibling imports):**
  - *Stage 1a & Stage 1b:* `stage1a_worker.py` and `stage1b_worker.py` are **self-contained single-file workers** with zero sibling imports, so `-P` (`safe_path=True`) prevents accidental CWD/script-dir injection without ever triggering `ModuleNotFoundError` (`S5`). Stage 1a verifies the 6 WP-0043 local closure modules (`timing`, `bindings`, `capture`, `transfer`, `native_observer`, `limits`) on disk by SHA-256 without importing them.
  - *Stage 2 (Primary vs Alternative):* Primary choice retains `-P` and loads any reused pinned sibling modules via digest-verified `importlib.util.spec_from_file_location` after hashing every file in `@source`. Explicit documented alternative drops `-P` (`a_* = (-s, -B, -u)`, matching `worker43.py` L86–87) while binding `sys.path[0] == @source` and auditing `@source` contents. Both choices require `eld-rd-reviewer` sign-off in `Rev_1a`/`Rev_2`.
- **Resolution of `O3` (Venv selection mechanism — explicitly prospective):**
  - *Primary candidate (`direct-stock-launcher-env`):* Pass `e_launch["__PYVENV_LAUNCHER__"] = "@venv/Scripts/python.exe"` with pre-launch `FILE_SHARE_READ` guards on `@venv/pyvenv.cfg` and `@venv/Lib/site-packages/*.pth`, expecting `sys.prefix == sys.exec_prefix == "@venv"`, `sys.executable == "@venv/Scripts/python.exe"`, `sys.orig_argv[0] == "@base/python.exe"`, `e_child["__PYVENV_LAUNCHER__"] == ABSENT`, `@venv/Lib/site-packages in sys.path`, `@base/Lib/site-packages not in sys.path`, and closed 33 distributions.
  - **Honest Epistemic Status:** Turn-1 pure-stdlib testing on a synthetic 2-line `pyvenv.cfg` observed this behavior on CPython 3.12.10, **but under T1 Corollary that synthetic check transfers zero guarantee to the actual Q0 `@venv`** (whose `pyvenv.cfg` digest and `.pth` files are not archived in public Git `e43af2e2`). Actual stock `@venv` selection therefore remains an **unverified prospective hypothesis** whose first empirical test is Stage 1a!
  - *Documented fallback (`direct-stock-nosite`):* Launch with `(-s, -P, -B, -u, -S)` (zero pre-script `.pth` execution), validate `@venv/pyvenv.cfg` and every `.pth` file inside the worker, then bind `sys.prefix = sys.exec_prefix = "@venv"` and `site.addsitedir("@venv/Lib/site-packages")`.
  - *Rejected option:* Setting `PYTHONPATH` to `@venv/Lib/site-packages` (skips `.pth`, leaves `sys.prefix == @base`).

### 2.3 Outer Handle-Holder Placement (`O7`) and Amended T3a Custody (`M3`)
Unchanged `worker43.py` L76–81 closes every file after write and hashes by path at L175–186, making `exec.original_continuity` structurally `U` under T3a. In `direct-stock-r1`, the **cooperative handle-holder chain** spans three frozen roles:
1. **Worker (`stage1a_worker.py` / `stage1b_worker.py` / Stage-2 worker):** Opens every protected output with `CREATE_NEW`, `GENERIC_READ | GENERIC_WRITE`, `FILE_SHARE_READ`, `inherit=False`; writes and calls `FlushFileBuffers`; duplicates a `FILE_GENERIC_READ` handle before closing the sole writer handle; signals the supervisor and keeps its read handle open until the supervisor confirms its own `DuplicateHandle(FILE_GENERIC_READ)` pull.
2. **Direct Supervisor (`stage1a_supervisor.py` / Stage-1b/2 supervisor):** Pulls a `FILE_GENERIC_READ` handle on every member BEFORE sealing the 256-bit HMAC-SHA256 inventory receipt $I_r$, and holds all member read handles open until the outer scorer confirms its own pulled read handles.
3. **Outer Recorder/Scorer (`stage1a_scorer.py` / Stage-1b/2 scorer):** Opens an independent fresh read handle on each member with `OPEN_EXISTING`, `GENERIC_READ`, **`FILE_SHARE_READ` ONLY** (excluding both `FILE_SHARE_WRITE` and `FILE_SHARE_DELETE`, tightening WP-0045 `win.py` L107 so any leaked open writer handle fails with `ERROR_SHARING_VIOLATION`), checks `nNumberOfLinks == 1`, NTFS filesystem, matching `(volume_serial, file_index)` against the held handle, and SHA-256 to EOF.
4. **Three-Valued Evaluation (`M3`):** Evaluates $B_{\rm arm}$ conjunct-wise (`schema`, `omit/extra`, `read.missing/read.extra`, `order` when order-sensitive, per-member custody over $I_r \cap E_r$, and physical-object uniqueness) per [`corrigenda-r1.md`](corrigenda-r1.md) C3 so conflicts never hide behind `U` (`I3`, `I5`, `I6a`, `ctrl_06`).

---

## 3. Exact Closed 31-Key Environment Scrub, Origin Mapping, and Stage Cuts (`#site-pth-and-dll-origin-mapping`, `#future-entries`)

### 3.1 Exact Closed 31-Key Child Environment Schema (`O4`)
No ambient user environment is inherited. Supervisor constructs `lpEnvironment` explicitly from scratch and creates per-unit subdirectories (`tmp`, `home`, etc.) **outside** `env_for()` (eliminating `worker43.py` L200's hidden `mkdir` side effect).

| Group | Exact Keys (Count) | Stage 1a & 1b (`e_launch` → `e_child`) | Stage 2 (`e_launch` → `e_child`) | Notes / Intentional Deltas |
| --- | --- | --- | --- | --- |
| **Launch-only venv selector** | `__PYVENV_LAUNCHER__` (1 launch-only) | `present("@venv/Scripts/python.exe")` → **`absent`** | `present("@venv/Scripts/python.exe")` → **`absent`** | Primary `O3` hypothesis; absent in `e_child` (`-S` fallback leaves absent in both). |
| **Core Python flags/encoding** (6) | `PYTHONHASHSEED="0"`, `PYTHONNOUSERSITE="1"`, `PYTHONDONTWRITEBYTECODE="1"`, `PYTHONUTF8="1"`, `PYTHONIOENCODING="utf-8"`, `PYTHONUNBUFFERED="1"` | Exact `present(...)` → `present(...)` | Identical | Jointly checked with derived 8-tuple `sys.flags` (`C2`, catches `S1`, `S4b`). |
| **Offline posture** (5) | `HF_HUB_OFFLINE="1"`, `TRANSFORMERS_OFFLINE="1"`, `HF_HUB_DISABLE_TELEMETRY="1"`, `HF_HUB_DISABLE_XET="1"`, `PIP_NO_INDEX="1"` | Exact `present("1")` → `present("1")` | Identical | Library offline posture (`Q_offline`); OS outbound firewall remains separately unverified. |
| **CUDA selection** (2) | `CUDA_DEVICE_ORDER="PCI_BUS_ID"`, `CUDA_VISIBLE_DEVICES` | `CUDA_DEVICE_ORDER="PCI_BUS_ID"`, **`CUDA_VISIBLE_DEVICES=""`** | `CUDA_DEVICE_ORDER="PCI_BUS_ID"`, `CUDA_VISIBLE_DEVICES="<leased_UUID>"` | **Explicit intentional Stage-1a/1b delta:** empty string hides GPUs on CPU stages. |
| **Per-unit isolated paths** (10) | `TEMP`, `TMP` (`@arm/tmp`); `HOME`, `USERPROFILE` (`@arm/home`); `HF_HOME` (`@arm/hf`); `HF_MODULES_CACHE` (`@arm/modules`); `CUDA_CACHE_PATH` (`@arm/cuda`); `TORCH_HOME` (`@arm/torch`); `TORCHINDUCTOR_CACHE_DIR` (`@arm/inductor`); `XDG_CACHE_HOME` (`@arm/xdg`) | Exact `@arm/...` subdirs | Identical | Matches `worker43.py` L193–198 (closes `O4` gap on `HF_HOME`, `HF_MODULES_CACHE`, etc.). |
| **Path** (1) | `PATH` | **`%SystemRoot%/System32;%SystemRoot%`** | Bound from Stage-1b DLL check | **Explicit intentional Stage-1a/1b delta** omitting `@venv/Scripts`; verified in Stage 1b. |
| **Windows OS pass-through** (7) | `SystemRoot`, `windir`, `OS`, `ComSpec`, `NUMBER_OF_PROCESSORS`, `PROCESSOR_ARCHITECTURE`, `PATHEXT` | Exact supervisor OS value (or `absent` if absent in supervisor) | Identical | Matches `worker43.py` L190–191 exactly. |
| **Closed-world ABSENT rule** (all other keys) | Every key $\notin \mathcal E_{31}$, explicitly asserting sentinels: `PYTHONPATH`, `PYTHONHOME`, `PYTHONSAFEPATH`, `PYTHONCASEOK`, `PYTHONWARNINGS`, `PYTHONUSERBASE`, `PYTHONSTARTUP`, `VIRTUAL_ENV`, `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `CUBLAS_WORKSPACE_CONFIG`, and child `__PYVENV_LAUNCHER__` | **`absent`** in `e_child` (and `e_launch` except `__PYVENV_LAUNCHER__`) | Identical | `present("") != absent` (`D4`, `S6`); reconciles WP-0045 `OMP/MKL/OPENBLAS` to `worker43.py` `ABSENT`. |

**Exact key arithmetic verified in `build_register_r1.py`:** `6 + 5 + 2 + 10 + 1 + 7 = 31` child keys (`e_child`) + `1` launch-only (`__PYVENV_LAUNCHER__`) = `32` launch keys (`e_launch`).

### 3.2 Stage Cuts and Stop-Before-Effects Boundaries (`O6`, `#stage1a-schedule`, `#stage1b-boundary`)

| Stage | Proposed Future Entry (ALL UNIMPLEMENTED IN STAGE 0) | Exact What Runs | Hard Stop-Before-Effects Boundary |
| --- | --- | --- | --- |
| **Stage 1a** *(Pure-Stdlib Direct-Stock Gate — 5 units)* | Outer: `@base/python.exe -I -S -B @source/stage1a_supervisor.py run --manifest <private_manifest.json>`<br>Worker (`u01`, `u02`): `@base/python.exe -s -P -B -u @source/stage1a_worker.py --unit <id>`<br>Controls (`c01` `-I`, `c02` drop flags, `c03` omit member) | Pre-launch `FILE_SHARE_READ` hashes (`@base/python.exe`, `@venv/Scripts/python.exe`, `@venv/pyvenv.cfg`, `@venv/Lib/site-packages/*.pth`, 18 `@model` files, 32 `@wheelhouse` wheels, 2 dev PDFs, 6 WP-0043 local closure files); direct `CreateProcessW(0x08000006)` creator join $E_{\rm direct}$; full `e_launch`/`e_child` 31-key closed audit; derived 8-flag `sys.flags`; `sys.prefix`/`base_prefix`/`executable`/`_base_executable`/`orig_argv`/`sys.path`/`site.getsitepackages()`/`.pth`/`sitecustomize` ABSENT; closed **33-distribution** `importlib.metadata` check; **3 forbidden absent** `find_spec` (`triton`, `flash_attn`, `xformers`); 5 runtime file disk hashes (`3 + 2`); 1 inert protected payload through cooperative T3/T3a handle-held scorer read. | **STOPS STRICTLY BEFORE `import torch`!** Zero third-party imports (`torch`, `transformers`, `numpy`, `psutil`, `pypdfium2` NOT imported); zero CUDA DLLs loaded; zero `nvidia-smi`; zero GPU leases; zero `.safetensors` reads into memory. |
| **Stage 1b** *(Separately Gated CPU-`torch` & DLL Gate — 2 units)* | Outer: `@base/python.exe -I -S -B @source/stage1b_supervisor.py run --manifest <private_manifest.json>`<br>Worker: `@base/python.exe -s -P -B -u @source/stage1b_worker.py --arm <id>` | Gated on `V^(1a) = P`, `Rev_1b`, and separate Stage-1b release. Re-verifies Stage-1a startup invariants; imports declared CPU packages (`numpy`, `PIL`, `pypdfium2`, `psutil`, `safetensors`, `tokenizers`, `huggingface_hub`, `transformers`, `torch`, `torchvision`) with `CUDA_VISIBLE_DEVICES=""`; checks `sys.modules[m].__file__` root containment; supervisor hashes every `LOAD_DLL_DEBUG_EVENT` image under `@venv`/`@base`; records whether `torch` backend flags (`tf32`, `cudnn_tf32`, `deterministic`, `autocast`) can be read without initializing CUDA. | **NEVER calls `torch.cuda.*`**, NEVER calls `from_pretrained()`, NEVER loads weights, NEVER acquires a GPU lease, NEVER invokes `nvidia-smi`. |
| **Stage 2** *(Stock GPU Capture — 2 arms × 4 calls)* | New Stage-2 direct-stock supervisor/worker + amended Phase-Local Eq. (8) scorer | Gated on `considerStockCapture`: `Plan_2 ∧ Rev_2 ∧ [V_preflight = P] ∧ [proj(Π_1) = proj(Plan_2)]` + sole GPU lease. Two cold arms (`untouched`, `observed`), 4 calls/arm (`F01.w`, `F07.w`, `F01.1`, `F07.1`) via reconciled `model.infer(..., image_file=list(pages), return_dict=True, **kwargs)` (`S-04`), cooperative T3/T3a custody (`O7`), amended scorer (`WP-0043/scorer.py` L304 fix + expanded finiteness + dual minimal sets + 5 per-row `support_choice` keys). | Stops after EOS and offline scoring; NEVER executes Stage-3 private replay. |
| **Stage 3** *(Private Replay — Held)* | Future separately authored Stage-3 runner | Gated on `considerPrivateReplay`: `Plan_3 ∧ Rev_3 ∧ ∃r (V_stock(r)=P ∧ J_5(r, R_cand))` + determinism premise `M4` + separate Stage-3 release. | Out of Stage-0/1/2 scope; WP-0037 stays parked. |

---

## 4. Resource Ceilings, Measurement Model, Scoped Plan Counts, and Hypotheses (`#resource-ceilings-and-scheduling`, `#measurement-and-loss-model`)

### 4.1 Per-Stage Resource Ceilings and Stop Criteria
| Parameter | Stage 1a (Pure Stdlib, 5 Units) | Stage 1b (CPU `torch`, 2 Units) | Stage 2 (Historical WP-0043 Ref Only) |
| --- | --- | --- | --- |
| Units & retries | `5` serial units (`2` decisive + `3` live controls); `0` retries | `2` serial cold arms; `0` retries | `2` cold arms × `4` calls (`8` calls); `0` retries |
| Timeouts | `300 s` wall; `240 s` static preflight hash; `60 s`/unit | `360 s` wall; `120 s`/unit | `7,200 s` wall; `900 s` load; `1,200 s`/call; `360 s` stall; `1 s` poll |
| Host Job commit (`0x0200`) | `512 MiB` (`536,870,912` B) + `KILL_ON_JOB_CLOSE (0x2000)` | `4 GiB` (`4,294,967,296` B) + `0x2000` | `15 GiB` (`16,106,127,360` B) + `0x2000` |
| GPU / CUDA / `torch` | `0` leases, `0` CUDA calls, **`0` `torch` imports** | `0` leases, `0` CUDA calls, CPU `torch` only | `1` sole GPU lease, `10 GiB` allocator, `11/2 GiB` VRAM free |
| Output / logs / files / disk | `32 MiB` out, `4 MiB` logs, `128` files; `2/1 GiB` free disk | `64 MiB` out, `8 MiB` logs, `128` files; `2/1 GiB` free disk | `2,560 MiB` out, `32 MiB` logs, `512` files; `4/1 GiB` free disk |

**Stop criteria:** Halt immediately on any privilege violation (non-8192/elevated/admin), unexpected preflight digest mismatch, ceiling overrun, unhandled child exception, or non-zero exit on a decisive unit (control units record expected `M`/`U` cleanly without aborting remaining scheduled controls). Fence and hash all partial artifacts; zero automatic retries.

### 4.2 Measurement & Loss Model (`T7` + `K3`)
Fail-closed **$f = 0$ erasure model** across all stages: every mandatory witness is required; any missing mandatory witness returns `U`, never `P`, and any witnessed contradiction returns `M`. Correlated failure domains (supervisor/worker crash erasing an entire unit, `K3`) are modeled at the source/unit level rather than assuming coordinate-level redundancy.

### 4.3 Scoped Obligation Accounting (`register-r1.json`, `118` Original + `44` Extended = `162` Total)
| Scoped Plan | Included Stages | Total Obligations | Original 118 | Extended 44 | Bound in Scope | Unbound in Scope ($B_T \cap \Pi_s$) | Deferred Unbound ($B_T \setminus \Pi_s$) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| $\Pi_0$ | `0` | `7` | `7` | `0` | `7` | **`0`** | `12` |
| $\Pi_{1a}$ | `0, 1a` | `104` | `68` | `36` | `100` | **`4`** (`cpu.entry.stage1a_source_pin`, `cpu.entry.coordinator_roots_manifest`, `static.venv.pyvenv_cfg`, `static.venv.pth_inventory`) | `8` |
| $\Pi_{1b}$ | `0, 1a, 1b` | `106` | `68` | `38` | `101` | **`5`** (+ `cpu.stage1b.entry_source_pin`) | `7` |
| $\Pi_2$ | `0, 1a, 1b, 2` | `160` | `116` | `44` | `150` | **`10`** (+ `exec.backend`, `exec.configuration`, `exec.creator`, `exec.device`, `exec.env.CUDA_VISIBLE_DEVICES`) | `2` |
| $\Pi_3$ | `0, 1a, 1b, 2, 3` | `162` | `118` | `44` | `150` | **`12`** (+ `private.plan`, `private.parity`) | `0` |

### 4.4 Prospective Qualification Hypotheses (Separate From Stage-0 Proposal)
- **$\mathsf{Hyp}_{1a}$ (Stage-1a Pure-Stdlib Direct-Stock Gate):** *Comparator:* Derived WP-0043 absolute profile + closed 31-key env + Q0 33-dist/3-forbidden-absent/5-runtime pins + explicit Stage-1a deltas. *Unit & denominator:* `5` scheduled cold units (`2` decisive direct-stock units + `3` live controls); report `P/M/U` and unattempted counts separately. *Decision rule:* $V^{(1a)}(\Pi_{1a}) = \PP$ iff `2/2` decisive units return `P` AND `3/3` controls match predicted verdicts (`M`, `U`, `M`), reproduced independently by `eld-rd-reviewer`. *Falsifier:* Any `M`/`U` on a decisive unit (e.g. `__PYVENV_LAUNCHER__` failing to exclude `@base/Lib/site-packages`, extra distribution beyond 33, `triton` present, or custody gap) or any control returning the wrong verdict. *Unmeasured:* `torch` import, DLL loading, CUDA, model weights, OCR accuracy, latency.
- **$\mathsf{Hyp}_{1b}$ (Stage-1b CPU-`torch` & DLL Gate — Held):** *Unit:* `2` cold CPU arms importing declared packages with `CUDA_VISIBLE_DEVICES=""`. *Falsifier:* Any `torch.cuda` error/side effect, out-of-root module or `LOAD_DLL_DEBUG_EVENT` DLL, or `PATH` failure.
- **$\mathsf{Hyp}_2$ (Stage-2 Stock Capture — Held) & $\mathsf{Hyp}_3$ (Stage-3 Private Replay — Held):** Preserved identically from `proposal.md` §4.3 with explicit `M2` `[proj(Π_1)=proj(Plan_2)]` bridge and `M4` determinism premise.

---

## 5. Stage-1 Hold Rationale & Safe Literal vs Future Commands

**Stage 1 MUST remain HELD** until ALL four mandatory prerequisites are cleared:
1. **Fresh independent non-author review (`Rev_0` / `Rev_1a`):** `eld-rd-reviewer` must independently audit this post-opening `r1` package (`exchange.md`, `corrigenda-r1.md`, `proposal-r1.md`, `register-r1.json`, `controls_r1.py`) and record disposition on `O2` (`-P` primary vs alternative) and `O3` (`__PYVENV_LAUNCHER__` primary vs `-S` fallback).
2. **Clearance of all 4 items in $B_T \cap \Pi_{1a}$:**
   - Author, freeze, hash, and independently review `stage1a_supervisor.py`, `stage1a_worker.py`, `stage1a_scorer.py` (`cpu.entry.stage1a_source_pin`);
   - Issue private coordinator local manifest binding symbolic roots (`cpu.entry.coordinator_roots_manifest`);
   - Disposition the two globally unarchived Q0 venv items (`static.venv.pyvenv_cfg` exact digest and `static.venv.pth_inventory` exact list: either pre-pin read-only in coordinator manifest OR explicitly authorize Stage-1a semantic validation + digest freeze for Stage 1b/2).
3. **Zero unresolved static conflicts (`X_static(all) == empty`)** after Stage-1a code freeze.
4. **Separate local coordinator Stage-1a release** (`separateLocalRelease_1a`).

**Executable commands safe literally now (offline stdlib only):**
- `python -I check.py` (from extracted bundle root)
- `python -I -B docs/research/WP-0046/build_register_r1.py --verify`
- `python -I -B docs/research/WP-0046/controls_r1.py --cases docs/research/WP-0046/control_cases.json`
- `python -I -B docs/research/WP-0046/controls_r1.py --claude-cases <peer_cases.json> --claude-expected <peer_expected.json>`

**Prohibited / unimplemented:** `worker43.py`, `docs/research/WP-0043/stock.py`, `stage1a_*`, `stage1b_*`, Stage-2/3 entries, any `torch`/stock import, or any host profile probe.
