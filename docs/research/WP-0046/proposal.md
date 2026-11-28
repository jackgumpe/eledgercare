# WP-0046 Stage 0 — Direct-Stock Qualification Proposal (`wp0046-direct-stock-v1`)

| Field | Value |
| --- | --- |
| Proposal ID / Version | `wp0046-direct-stock-v1` (Stage 0 proposal only; **not implemented for live execution, not released**) |
| Sole Proposal Author | `eld-owner-probe` (Gemini 4 Neon (XHigh) via local `agy` CLI) |
| Repository / Branch / Reservation | `jackgumpe/eledgercare` / `research/wp-0046-direct-stock` / `281b71d1dbf75b8e121a1ea577c0385ae8683555` (intake reference `e43af2e263f55478d1d551a5a095536b042589c2`) |
| Machine-Readable Companion | [`register.json`](register.json) (118 obligation rows), [`build_register.py`](build_register.py), [`controls.py`](controls.py), [`control_cases.json`](control_cases.json) |
| Governing Mathematics | Paper I reviewed revision 1 (T1–T8a) with targeted Stage-0 amendments `M-01`–`M-09` documented in [`first.md`](first.md) |
| Target Execution Status | **0 target runs executed.** Stage 1 (CPU), Stage 2 (stock GPU), and Stage 3 (private replay) all remain unreleased. WP-0037 stays parked. |

---

## 1. Scientific Question, Baseline, and Operating Assumptions

### 1.1 Question and Mechanism Under Study
Can an ordinary-user direct Windows creation of the pinned base CPython 3.12.10 interpreter (`@base/python.exe`)—eliminating the WP-0043/WP-0044 `venv/Scripts/python.exe` redirector hop—reproduce the exact effective Python startup state, virtual-environment package resolution, offline flags, and in-coverage DLL/module origins required by the unmodified Q0 stock OCR reader (`Unlimited-OCR-2`, revision `0480966938291445591f69f08a13b041c073a96a`), while preserving WP-0045's creation-scoped creator witness and continuous NTFS original-output custody?

### 1.2 Baseline and Motivating Evidence
- **Historical stock baseline $H$ (WP-0043):** Two cold `venv` processes (`untouched`, `observed`) completed all 8 calls through native EOS (`F01.warmup`, `F07.warmup`, `F01.warm1`, `F07.warm1`). F07 content matched `1/1` (2,558 non-EOS IDs, 7,617 UTF-8 bytes) and all 15 dense FP32 score vectors (7,756,800 bytes) satisfied the archived transitions. However, `worker43.py` launched `@venv/Scripts/python.exe`, whose Windows redirector spawned `@base/python.exe`, causing `sys.orig_argv[0]` to conflict with `plan43.json#/worker_argv`. Formal WP-0043 joint verdict remains **`M`** (`0/1` qualified pairs, `0/5` qualified rows).
- **Direct-launch CPU baseline $D$ (WP-0045):** Two independent implementations qualified `4/4` genuine ordinary-user cooperative direct launches (`15/15` passing atoms each) using `@base/python.exe -I -S -B` on a 4-byte inert worker. By Paper I Theorem 1 Corollary, $D$ qualifies the cooperative direct-launch mechanism on inert workers only—it transfers zero live-module, hash-seed, package-path, or GPU identity evidence to a stock process.
- **Stdlib CPython 3.12.10 discovery motivating `direct-stock` activation (`M-01`):** Pure-stdlib testing on Windows CPython 3.12.10 confirmed two critical mechanisms:
  1. Passing `-I` (WP-0045) forces `ignore_environment = 1`, `hash_randomization = 1` (defeating `PYTHONHASHSEED=0`), and `utf8_mode = 0` (defeating `PYTHONUTF8=1`).
  2. Passing bare `-s -P -B -u` (without `__PYVENV_LAUNCHER__` and without `-S`) executes `site.main()` against `@base`, **contaminating `sys.path` with `@base/Lib/site-packages`** and violating the Q0 venv's `include-system-site-packages = false`.
  3. Passing `-s -P -B -u` together with `e_launch["__PYVENV_LAUNCHER__"] = "@venv/Scripts/python.exe"` causes CPython 3.12.10's C startup to set `sys.executable = "@venv/Scripts/python.exe"`, `sys.orig_argv[0] = "@base/python.exe"`, `sys.prefix = sys.exec_prefix = "@venv"`, exclude `@base/Lib/site-packages`, include `@venv/Lib/site-packages`, preserve `ignore_environment = 0`, `hash_randomization = 0`, `utf8_mode = 1`, `safe_path = True`, and **erase `__PYVENV_LAUNCHER__` from child `os.environ` before user code runs**.

### 1.3 Operating Assumptions and Symbolic Roots (No Host Paths)
All paths in public WP-0046 deliverables use symbolic root tokens resolved exclusively by a future coordinator-published release manifest:

| Token | Logical Meaning (Pinned Identity Where Static) |
| --- | --- |
| `@base` | Pinned CPython 3.12.10 x64 base directory; `@base/python.exe` SHA-256 `4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a` |
| `@venv` | Pinned Q0 venv root (`pyvenv.cfg` with `include-system-site-packages = false`; `@venv/Scripts/python.exe` SHA-256 `0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14`—verified statically, **not executed** as a redirector) |
| `@q0_root` | Read-only Q0 root containing `@venv`, `@model`, `@wheelhouse` |
| `@model` | Unmodified `Unlimited-OCR-2` rev `0480966938291445591f69f08a13b041c073a96a` (18 pinned files) |
| `@wheelhouse` | 32 verified Q0 wheels (`02-verify-wheelhouse.json`) |
| `@repo` / `@worktree` | `jackgumpe/eledgercare` at bound commit / assigned isolated role worktree |
| `@speed_root` / `@run_root` / `@arm` | Private local-only uncommitted output root / per-run folder / exclusive-create per-arm folder |

**Trust boundary:** Correct Windows 64-bit OS kernel/NTFS/Win32 handle semantics; ordinary interactive user token (`integrity_rid == 8192`, `elevated == 0`, `effective_admin == False`); trusted frozen outer recorder/scorer, direct supervisor, and worker binaries; no inherited handles (`bInheritHandles = False`); cooperative single-writer file creation (`CREATE_NEW`, `FILE_SHARE_READ`). Independent hostile same-user processes, compromised signing keys, kernel ETW attribution, customer data, E1–E3 OCR treatments, and WP-0037 are strictly outside scope.

---

## 2. Operative Mathematical Model (Amended Baseline → Direct-Stock)

### 2.1 Symbols, Types, and Tagged Observation Domain
- **Stages:** $s \in \{0, 1, 2, 3\}$ ($0$: design/profile review; $1$: ordinary-user CPU stock-route qualification; $2$: separately released stock GPU capture; $3$: separately released private replay).
- **Tagged values:** Every observed scalar/env/object field carries an explicit state tag in $\{\mathsf{present}(v), \mathsf{absent}, \mathsf{unobserved}\}$. JSON `null` is $\mathsf{present}(\texttt{null})$, strictly distinct from $\mathsf{absent}$ (key absent from `os.environ` or attribute absent) and $\mathsf{unobserved}$ ($\unk$). Strict typed equality enforces $\mathrm{type}(a) = \mathrm{type}(b)$ (`bool` $\neq$ `int`, so `False` $\neq 0$, `True` $\neq 1$).
- **Verdict lattice & conflict classes:** $V(X, U) = \MM$ if $X \neq \varnothing$, else $\UU$ if $U \neq \varnothing$, else $\PP$ ($\MM < \UU < \PP$). Each conflict element in $X$ carries an explicit class in $\{\MM_{\rm field}, \MM_{\rm integrity}, \MM_{\rm static\_plan}\}$ (preserving T1 Eq. 2's $\MM_{\rm integrity}$ distinction).
- **Dual minimal frontiers:** Given a validated **strict** partial order $\prec$ (irreflexive, acyclic; transitive closure computed over direct causal edges),
  $$\fn{firstConflict}(X) = \min_{\prec} X, \qquad \fn{firstFinding}(X, U) = \min_{\prec}(X \cup U).$$
  Any reflexive or cyclic order edge is rejected as $\MM_{\rm integrity}$ (`order.integrity`) rather than returning an empty frontier.

### 2.2 Launch Route Selection (`#route-selection`) and Amended Stage-1 Predicate $Q_{\rm cpu}$
Choose $\tau = \texttt{direct-stock}$:
$$a_* = (\texttt{-s}, \texttt{-P}, \texttt{-B}, \texttt{-u}), \qquad L_* = \fn{CreateProcessW}\bigl(\texttt{@base/python.exe},\; a_* \Vert \mathrm{entry\_argv},\; e_{\rm launch},\; \texttt{0x08000006},\; \mathrm{inherit}=\mathsf{False}\bigr)$$
where `0x08000006` = `CREATE_NO_WINDOW | CREATE_SUSPENDED | DEBUG_ONLY_THIS_PROCESS`.

**Amended Stage-1 qualification predicate:**
$$Q_{\rm startup} = \bigl[e_{\rm launch}[\texttt{PYTHONHASHSEED}]=\mathsf{present}(\texttt{"0"})\bigr] \land \bigl[e_{\rm child}[\texttt{PYTHONHASHSEED}]=\mathsf{present}(\texttt{"0"})\bigr] \land \bigwedge_{f \in \mathcal F_{\rm star}} \bigl[\texttt{sys.flags.}f =_{\rm strict} f^*\bigr]$$
where $\mathcal F_{\rm star}$ fixes exact CPython 3.12.10 types: `isolated=0 (int)`, `ignore_environment=0 (int)`, `hash_randomization=0 (int)`, `no_site=0 (int)`, `no_user_site=1 (int)`, `dont_write_bytecode=1 (int)`, `safe_path=True (bool)`, `utf8_mode=1 (int)`.
$$Q_{\rm env} = \Bigl(\bigwedge_{k \in \mathcal E_{\rm launch}} [e_{\rm launch}[k] =_{\rm strict} e_{\rm launch}^*[k]]\Bigr) \land \Bigl(\bigwedge_{k \in \mathcal E_{\rm child}} [e_{\rm child}[k] =_{\rm strict} e_{\rm child}^*[k]]\Bigr)$$
explicitly recording $e_{\rm launch}[\texttt{\_\_PYVENV\_LAUNCHER\_\_}] = \mathsf{present}(\texttt{"@venv/Scripts/python.exe"})$ and $e_{\rm child}[\texttt{\_\_PYVENV\_LAUNCHER\_\_}] = \mathsf{absent}$.
$$Q_{\rm import} = \bigl[(\texttt{sys.orig\_argv[0]}, \texttt{sys.executable}, \texttt{sys.prefix}, \texttt{sys.exec\_prefix}, \texttt{sys.path}, \texttt{pyvenv.cfg}, \mathrm{pth}, \mathrm{sitecustomize}, \mathrm{modules}, \mathrm{dlls}) \sim m_{\rm import}\bigr]$$
$$Q_{\rm cpu} = E_{\rm direct}^{\rm CPU} \land Q_{\rm startup} \land Q_{\rm import} \land Q_{\rm offline} \land Q_{\rm env} \land B_{\rm arm}^{\rm CPU}.$$

- **Guarantee & proof sketch:** Under `CreateProcessW` with `DEBUG_ONLY_THIS_PROCESS`, the OS delivers `CREATE_PROCESS_DEBUG_EVENT` with kernel `hProcess` and `hFile` for `@base/python.exe`; `CompareObjectHandles(hProcess_ret, hProcess_evt) == True` joins caller $S$ to child $i_{\rm base}$ ($E_{\rm direct}$). Pre-launch read-only guards (`FILE_SHARE_READ`) on `@venv/pyvenv.cfg`, `@venv/Lib/site-packages/*.pth`, and verified absence of `sitecustomize.py`/`usercustomize.py`, combined with `e_launch["__PYVENV_LAUNCHER__"]` and Cut 1A/1B child receipts, ensure `@base/Lib/site-packages` is excluded (`include-system-site-packages = false`) and all imported packages/DLLs within declared coverage originate from `@venv`, `@base`, `@source`, `built-in`, or `frozen`.
- **Worked counterexamples:** (1) Passing `-I` with `PYTHONHASHSEED="0"` flips `isolated=1, ignore_environment=1, hash_randomization=1, utf8_mode=0` $\Rightarrow \MM$ (`ctrl_02`). (2) Omitting `__PYVENV_LAUNCHER__` on bare `-s -P -B -u` flips `sys.prefix=@base`, `base_site_packages_in_sys_path=True`, `venv_site_packages_in_sys_path=False` $\Rightarrow \MM$ (`ctrl_03`).
- **Explicit documented alternative (`direct-stock-nosite`):** Launch with `(-s, -P, -B, -u, -S)` (no `__PYVENV_LAUNCHER__` needed at startup, `no_site=1` initially), then validate `@venv/pyvenv.cfg` and every `.pth` file inside the entry script before explicitly setting `sys.prefix = sys.exec_prefix = @venv` and invoking `site.addsitedir("@venv/Lib/site-packages")`. This avoids any pre-script `.pth` execution at the cost of intentionally diverging from Paper I T2a's $a_* = (-s, -P, -B, -u)$ and native `site.venv()`. Retained as an explicit alternative if `eld-rd-reviewer` prefers zero pre-script site execution.

### 2.3 Amended Inventory Completeness $B_{\rm arm}$ and Continuity (`#trust-writer-and-continuity`)
For run $r$, dynamic expansion $E_r = F_r(q_r)$ over authenticated schedule data $q_r$, sealed inventory $I_r$, and scorer read sequence $R_r$:
$$B_{\rm arm} = \mathrm{auth}(q_r) \land B_{\rm inventory} \land \bigl[\forall k: b(E_r)(k) \le 1\bigr] \land \bigl[b(I_r)=b(E_r)\bigr] \land \bigl[b(R_r)=b(I_r)\bigr] \land \mathrm{physUnique}(E_r) \land \bigwedge_{k \in E_r} B_{m(k)}$$
evaluated under strict $M < U < P$ aggregation so any observed omission in $I_r$ or custody failure in $B_{m(k)}$ yields $\MM$ even if $R_r$ is unobserved (`ctrl_06`), fixing `amendments.py:inventory()`.

For each member $m$, `continuous(m)` requires:
1. Worker opens `m` with `CREATE_NEW`, `GENERIC_READ | GENERIC_WRITE`, `FILE_SHARE_READ`, `inherit=False`, flushes (`FlushFileBuffers`), duplicates a `FILE_GENERIC_READ` view before closing the sole writer handle, and holds that view until supervisor acknowledges its own `DuplicateHandle(FILE_GENERIC_READ)` pull.
2. Supervisor signs the 256-bit HMAC-SHA256 inventory receipt only after writer close, and holds its read view until outer scorer acknowledges its pulled read view.
3. Scorer opens a separate fresh handle with `OPEN_EXISTING`, `GENERIC_READ`, **`FILE_SHARE_READ` ONLY** (tightening WP-0045 `win.py` L107's `SHARE_R | SHARE_W` so any leaked open writer causes `ERROR_SHARING_VIOLATION`), checks `nNumberOfLinks == 1`, NTFS filesystem, matching `(volume_serial, file_index)` against the held guard, and SHA-256 to EOF (`ctrl_07`).

### 2.4 Amended Phase-Local Score Rule (Stage 2), Static-Before-Deferral `ASSESS`, and Replay Gate
- **T5 Eq. (8) amended:** Retain phase-local $\widehat z^p_j$ on supplied predecessor $z^{p-1}_j$ (`D_2` only at `C2_post_page`, fixing `WP-0043/scorer.py` L304's cumulative-mask bug; `ctrl_08`). Add unconditional $X_{\rm oob} = \{\text{emitted\_outside\_support} : y_{\rm obs} \text{ observed} \land y_{\rm obs} \notin A\}$ (`ctrl_09`), and formalize partial-phase missingness $U_{\rm phase}$ while retaining all decidable faults (`ctrl_10`). Signed zeros (`80000000` vs `00000000`) tie numerically toward least ID while remaining bitwise distinct (`ctrl_11`).
- **T6 empty-view bound:** Require $0 \le b \cdot o \le B_{\rm storage}$ for empty views ($\prod n_i = 0$) in addition to $b(1 + o + \sum_i (n_i - 1) s_i) \le B_{\rm storage}$ for nonempty views, plus explicit read-bound vs write-non-aliasing distinction.
- **T8 Eq. (11) amended:**
  $$X_T^{(s)} = \{k : X_{k,\rm static} \neq \varnothing\} \cup \{k \in A_s : X_{k,\rm due} \neq \varnothing\}, \qquad W_T^{(s)} = B_T^{\rm req}(\mathcal M_{\rm scope}) \cup \{k \in A_s : U_{k,\rm due} \neq \varnothing\}$$
  so Stage-0/1 `ASSESS` detects Stage-2 static $\oplus$-conflicts before deferral (`ctrl_15`) while scoping `B_required` to the proposed stage's plan $P_j$ (deferring Stage-3 `private.plan` until Stage 3 is proposed).
- **T8a Eq. (12) amended (symbol collision resolved):** Let $\mathrm{Rev}_j$ denote independent design review for stage $j$:
  $$\mathsf{eligible}_1 = P_1 \land \mathrm{Rev}_1, \qquad \mathsf{eligible}_2 = P_2 \land \mathrm{Rev}_2 \land \bigl[V_{\rm preflight}(\tau, \mathrm{rev}_1, M_{\rm static}) = \PP\bigr],$$
  $$\mathsf{eligible}_3 = P_3 \land \mathrm{Rev}_3 \land \exists r : \bigl(V_{\rm stock}(r) = \PP \land J_5(r, R_{\rm cand})\bigr), \qquad \mathsf{execute}_j = \mathsf{eligible}_j \land \mathsf{separateLocalRelease}_j$$
  where $J_5(r, R_{\rm cand})$ checks unique 5-key bijection with $K = \{(\texttt{observed}, \texttt{F07.warm1}, p) : p \in 1445..1449\}$, same-run join $\mathrm{run}(t)=r$, `originalBound(r,t)`, and `restorable(t)` (`ctrl_12`–`ctrl_14`).

---

## 3. Exact Environment Scrub, `site`/`.pth`/DLL Origin Mapping, and Stage Cuts

### 3.1 Environment Allowlist (`e_launch` vs `e_child`)
No ambient user environment is inherited. Supervisor passes an explicit allowlisted `lpEnvironment` dictionary to `CreateProcessW`:

| Variable | Historical `worker43.py` | WP-0045 Direct | Stage 1 CPU (`e_launch` → `e_child`) | Stage 2 Stock (`e_launch` → `e_child`) | Rationale / Difference Binding |
| --- | --- | --- | --- | --- | --- |
| `__PYVENV_LAUNCHER__` | Set internally by `venvlauncher.exe` | `ABSENT` | `present(@venv/Scripts/python.exe)` → `absent` | `present(@venv/Scripts/python.exe)` → `absent` | Triggers native CPython 3.12 `site.venv()` without redirector; erased by CPython C startup. |
| `PYTHONHASHSEED` | `"0"` | `ABSENT` | `present("0")` → `present("0")` | `present("0")` → `present("0")` | Verified jointly with `ignore_environment=0`, `hash_randomization=0`. |
| `PYTHONNOUSERSITE` | `"1"` | `ABSENT` | `present("1")` → `present("1")` | `present("1")` → `present("1")` | Redundant guard paired with `-s` (`no_user_site=1`). |
| `PYTHONDONTWRITEBYTECODE` | `"1"` | `ABSENT` | `present("1")` → `present("1")` | `present("1")` → `present("1")` | Paired with `-B` (`dont_write_bytecode=1`). |
| `PYTHONUTF8` | `"1"` | `ABSENT` | `present("1")` → `present("1")` | `present("1")` → `present("1")` | Verified via `sys.flags.utf8_mode == 1`. |
| `PYTHONIOENCODING` | `"utf-8"` | `ABSENT` | `present("utf-8")` → `present("utf-8")` | `present("utf-8")` → `present("utf-8")` | Matches `worker43.py` L199. |
| `PYTHONUNBUFFERED` | `"1"` | `ABSENT` | `present("1")` → `present("1")` | `present("1")` → `present("1")` | Paired with `-u`. |
| `HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE`, `HF_HUB_DISABLE_TELEMETRY`, `HF_HUB_DISABLE_XET`, `PIP_NO_INDEX` | `"1"` (all 5) | `ABSENT` | `present("1")` → `present("1")` | `present("1")` → `present("1")` | Offline library posture (`Q_offline`); OS outbound firewall remains separately unverified. |
| `CUDA_VISIBLE_DEVICES` | `<UUID>` | `ABSENT` | **`present("")` → `present("")`** | `present(<leased_UUID>)` → `present(<leased_UUID>)` | **Intentional Stage-1 difference:** empty string hides CUDA devices during CPU imports. |
| `CUDA_DEVICE_ORDER` | `"PCI_BUS_ID"` | `ABSENT` | `present("PCI_BUS_ID")` → `present("PCI_BUS_ID")` | `present("PCI_BUS_ID")` → `present("PCI_BUS_ID")` | Preserved identically across Stage 1 and Stage 2. |
| `TEMP`, `TMP`, `HOME`, `USERPROFILE`, `HF_HOME`, `HF_MODULES_CACHE`, `CUDA_CACHE_PATH`, `TORCH_HOME`, `TORCHINDUCTOR_CACHE_DIR`, `XDG_CACHE_HOME` | Arm-local subdirs under `@arm` | `ABSENT` | Arm-local subdirs under `@arm` (created by supervisor outside `env_for`) | Arm-local subdirs under `@arm` | Isolates caches per arm; eliminates `worker43.py` L200 hidden mkdir side effect. |
| `PATH` | `@venv/Scripts;%SystemRoot%/System32;%SystemRoot%` | `ABSENT` | `%SystemRoot%/System32;%SystemRoot%` (exact scrubbed system dirs; `@venv/Scripts` omitted at Stage 1 unless required by DLL check) | Bound explicitly from Stage-1 DLL audit | Avoids accidental PATH-based exe lookup; `torch` uses `os.add_dll_directory()` on Windows. |
| `SystemRoot`, `windir`, `OS`, `ComSpec`, `NUMBER_OF_PROCESSORS`, `PROCESSOR_ARCHITECTURE`, `PATHEXT` | Copied from host | `SystemRoot` only | Exact OS baseline allowlist | Exact OS baseline allowlist | Required by Windows Win32/CRT/subprocess loaders. |
| `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `CUBLAS_WORKSPACE_CONFIG` | **`ABSENT`** | `"1"`, `"1"`, `"1"`, `ABSENT` | **`absent` → `absent`** | **`absent` → `absent`** | Reconciled to `worker43.py` (`ABSENT`) so CPU/OpenMP threading does not silently diverge from historical WP-0043. |
| `PYTHONHOME`, `PYTHONPATH`, `PYTHONUSERBASE`, `PYTHONSTARTUP`, `PYTHONWARNINGS`, `VIRTUAL_ENV` | `ABSENT` | `ABSENT` | **`absent` → `absent`** | **`absent` → `absent`** | Explicitly verified `ABSENT` in both `e_launch` and `e_child` to prevent ambient path injection. |

### 3.2 `site`, `.pth`, and Windows DLL Origin Mapping (`#site-pth-and-dll-origin-mapping`)
1. **Pre-launch supervisor read-guards (Cut 1S):** Before calling `CreateProcessW`, the supervisor opens `FILE_SHARE_READ`-only handles on `@base/python.exe`, `@venv/pyvenv.cfg`, and every `*.pth` file in `@venv/Lib/site-packages`, hashes each, parses `pyvenv.cfg` verifying `include-system-site-packages = false`, and verifies absence of `sitecustomize.py` and `usercustomize.py` in `@venv`, `@venv/Lib/site-packages`, `@base`, and `@base/Lib/site-packages`.
2. **Post-startup `sys.path` check (Cut 1A):** With `-P` (`safe_path=True`), the script directory is NOT auto-prepended to `sys.path`. The Stage-1 probe verifies ordered `sys.path` contains `@venv/Lib/site-packages` and `@base/{python312.zip,DLLs,Lib}` and **does NOT contain `@base/Lib/site-packages` or user-site**. Only after hashing its own sibling probe module(s) does it insert `@source` explicitly if needed.
3. **CPU stock imports & OS DLL origin check (Cut 1B):** With `CUDA_VISIBLE_DEVICES=""` and zero `torch.cuda.*` calls, the child verifies all 32 `importlib.metadata` versions, `importlib.util.find_spec("triton") is None`, and the 5 pinned runtime files (`transformers/cache_utils.py`, `torch/_torch_docs.py`, `torch/version.py`, `torch/lib/cudart64_13.dll`, `torch/cuda/streams.py`). It imports the declared CPU package set (`numpy`, `PIL`, `pypdfium2`, `psutil`, `safetensors`, `tokenizers`, `huggingface_hub`, `transformers`, `torch`, `torchvision`), verifies `torch.__version__ == "2.13.0+cu130"`, `torch.version.cuda == "13.0"`, `transformers.__version__ == "4.52.1"`, and hashes every in-coverage `sys.modules[m].__file__` while asserting root containment in `{@venv/Lib/site-packages, @base/Lib, @base/DLLs, @source, built-in, frozen}`. Simultaneously, the supervisor captures `LOAD_DLL_DEBUG_EVENT` (`kind == 6`) kernel `hFile` handles, maps their paths via `GetFinalPathNameByHandleW`, and hashes every loaded DLL under `@venv` or `@base` (verifying `python312.dll`, `c10.dll`, `torch_cpu.dll`, `cudart64_13.dll` when loaded, and zero DLLs from `@base/Lib/site-packages` or user-site). Device-only DLLs (e.g. lazy cuBLAS/cuDNN kernels not loaded without CUDA calls) stay explicitly deferred to Stage 2.

### 3.3 Exact Future Entry, Argv, and Stop-Before-Effects Boundaries (PROPOSED / UNIMPLEMENTED)
- **Stage 1 future entry (UNIMPLEMENTED — requires separate Stage-1 source freeze & review):**
  - Outer ordinary-user invocation (via coordinator limited-user wrapper analogous to WP-0045 `limited.ps1`):
    `@base/python.exe -I -S -B @worktree/docs/research/WP-0046/stage1_direct_probe.py run --plan <private_plan.json>`
  - Supervisor spawns each cold arm (`arm-0`, `arm-1`, serially) via direct `_winapi.CreateProcess` with:
    `argv = ["@base/python.exe", "-s", "-P", "-B", "-u", "@worktree/docs/research/WP-0046/stage1_worker.py", "--arm", "<arm_id>"]`
  - **STOP BEFORE EFFECTS (Hard Stage-1 Boundary):** `stage1_worker.py` stops and exits `0` immediately after Cut 1B member write/flush/read-view handoff. It **NEVER** calls `torch.cuda.*`, **NEVER** imports or reads `.safetensors` weights into memory, **NEVER** calls `AutoModel`/`AutoTokenizer.from_pretrained()`, **NEVER** invokes `nvidia-smi`, and **NEVER** acquires any GPU lock.
- **Stage 2 future entry (UNIMPLEMENTED — gated on `eligible_2` & separate sole GPU lease):**
  - Reuses the exact Stage-1 direct supervisor and `-s -P -B -u` + `__PYVENV_LAUNCHER__` launch contract, adds `CUDA_VISIBLE_DEVICES=<leased_UUID>`, runs two cold serial arms (`untouched`, `observed`) over the preserved 4-call schedule (`F01.warmup`, `F07.warmup`, `F01.warm1`, `F07.warm1`) using reconciled `model.infer(tok, prompt=PROMPT, image_file=list(pages), return_dict=True, **kwargs)`, captures multi-member T3/T3a custody, and scores offline using the **amended** Phase-Local Eq. (8) + `X_oob` + expanded-finiteness + dual-minimal-set scorer.

---

## 4. Resource Ceilings, Scheduling, Measurement/Loss Model, and Freeze/Stop Criteria

### 4.1 Resource Ceilings and Scheduling (`#resource-ceilings-and-scheduling`)

| Parameter | Stage 1 CPU Proposal (New) | Stage 2 Stock (Historical WP-0043 Reference Only — Rebind Pre-Stage-2) |
| --- | --- | --- |
| Cold arms & schedule | 2 serial cold arms (`arm-0`, `arm-1`); 0 retries | 2 serial cold arms (`untouched`, `observed`) × 4 calls (`F01.w`, `F07.w`, `F01.1`, `F07.1`); 0 retries |
| Wall / phase timeouts | 600 s total wall; 300 s static preflight hashing (8 MiB chunk guard); 120 s per arm | 7,200 s wall; 900 s load; 1,200 s per call; 360 s stall; 1 s poll |
| Host job memory commit (`0x0200`) | 4 GiB (`4,294,967,296` bytes) + `KILL_ON_JOB_CLOSE (0x2000)` | 15 GiB (`16,106,127,360` bytes) + `KILL_ON_JOB_CLOSE (0x2000)` |
| Device / GPU lease | **0 leases, 0 CUDA calls, 0 VRAM** | 1 sole GPU lease; 10 GiB Torch allocator; 11 GiB initial / 2 GiB during free VRAM; 16 MiB pinned host pool |
| Output / logs / files / disk | 64 MiB output, 8 MiB logs, 128 files; 2 GiB initial / 1 GiB during free disk | 2,560 MiB output, 32 MiB logs, 512 files, 1,792 MiB tensor pack, 96 MiB journal; 4 GiB initial / 1 GiB during free disk |

**Stop criteria:** Stop immediately on any preflight digest mismatch, privilege mismatch (non-8192/elevated/admin), ceiling breach, missing expected file, unhandled child exception, or non-zero exit. Fence and preserve partial artifacts with SHA-256 receipts; zero automatic retries; release owned handles/jobs cleanly.

### 4.2 Measurement & Loss Model (`#measurement-and-loss-model`)
Stage 1 declares a **fail-closed $f = 0$ erasure model**: every mandatory Cut 1S, Cut 1A, Cut 1B, creator, and custody witness is required; any missing witness returns `U` (never `P`), and any witnessed contradiction returns `M` (dominating `U`). Correlated multi-coordinate failures (e.g., supervisor crash erasing an entire arm) are accounted at the arm/process failure-domain level rather than claiming coordinate-erasure redundancy.

### 4.3 Qualification Hypotheses (Separate From Stage-0 Proposal)
- **H1 (Stage-1 Direct-Stock CPU Qualification):** *Comparator:* historical WP-0043 pinned profile + declared direct-stock intentional-difference mapping. *Unit:* 1 cold direct-stock CPU arm ($N = 2$ scheduled arms: `arm-0`, `arm-1`, distinct processes & distinct original objects). *Metric & denominator:* count of full-field `P` arms out of 2 scheduled arms (unattempted arms reported separately; `P/M/U` counts retained). *Decision rule:* $V_{\rm preflight} = \PP$ iff `2/2` arms pass $Q_{\rm cpu}$ with `0` conflicts, `0` missing keys, and independent `eld-rd-reviewer` reproduction. *Falsifier:* any `M` on effective startup flags, base `site-packages` leak, unapproved module/DLL root, creator edge, or custody continuity on either arm. *Unmeasured:* GPU numerics, model weights execution, private replay, OCR accuracy, throughput.
- **H2 (Stage-2 Stock Capture Qualification — Held):** *Unit:* 1 cold untouched/observed pair (`2` loads, `8` calls) and `5` dependent F07.warm1 decision rows (`1445..1449`). *Falsifier:* any public parity conflict, any phase-local Eq. (8) / `X_oob` conflict, any missing expanded-finiteness check, or any runtime/custody `M`/`U`.
- **H3 (Stage-3 Private Replay — Held):** *Unit:* WP-0042 conditional counts (`35` rows, `30` private calls, `40` comparisons, `10` selections, `8` linked bridges, `5` protected source rows + continuation to EOS). *Falsifier:* any linked divergence $Y_F(\mathcal R(C(s))) \neq Y_F(s)$ or source write-leak.

---

## 5. Safe Literal Commands vs Future Unimplemented Probes & Peer Control Entry

| Command | Category | Safe to Run Literally Now? | Purpose |
| --- | --- | --- | --- |
| `python -I check.py` (in extracted `stock-transfer-source.zip` root) | Bundled offline checker | **YES (Safe literally)** | Reproduces Paper I's 6 expected stdout lines (stdlib only). |
| `python -I -B docs/research/WP-0046/build_register.py --verify` | Authored Stage-0 register verifier | **YES (Safe literally)** | Deterministically verifies all 118 rows of `docs/research/WP-0046/register.json` against pinned repo JSONs + zero host-path check. |
| `python -I -B docs/research/WP-0046/controls.py --cases docs/research/WP-0046/control_cases.json` | Authored Stage-0 finite control entry | **YES (Safe literally)** | Executes all 16 constructed proposal control cases (startup, inventory/omission, continuity, phase-local T5, mixed-run replay gate, static-before-deferral `ASSESS`, crosswalk/cycle integrity) and checks full-field expected returns. |
| `python -I -B docs/research/WP-0046/controls.py --case <single_case.json>` | Peer single-case normal entry | **YES (Safe literally)** | Lets `eld-rd-reviewer` feed any newly constructed JSON case (omitted member, startup mismatch, phase error, mixed run, etc.) and inspect full p. 17 return fields. |
| `worker43.py` / `docs/research/WP-0043/stock.py run` | Historical WP-0043 GPU runner | **NO (Prohibited in Stage 0)** | Hardcodes WP-0043 host paths, GPU lock, `nvidia-smi`, model load, and `venv` Python. Never run. |
| `stage1_direct_probe.py` / `stage1_worker.py` | Proposed Stage-1 CPU probe | **NO (Unimplemented future probe)** | Does not exist in Stage 0; requires Stage-0 acceptance, separate Stage-1 implementation freeze, independent review, and coordinator release. |
| Stage-2 direct-stock GPU runner / Stage-3 private replay runner | Proposed Stages 2–3 | **NO (Unimplemented / Unreleased)** | Gated by Eq. (12) `eligible_2`, `eligible_3`, and separate coordinator local releases. |

### Constructed Peer-Checkable Control Suite (`control_cases.json`, 16 Cases)
All 16 cases in [`control_cases.json`](control_cases.json) carry full input-conditional expected return objects conforming to Paper I p. 17's minimum return record (`case_id`, `subject`, `run`, `arm`, `stage`, `clause`, `cut`, `source_revision`, `verdict`, `conflict_classes`, `conflict_keys`, `missing_keys`, `conflicts`, `missing`, `first_conflict`, `first_finding`, `deferred`, `details`, `prospective_status`):
- **Effective startup controls (`ctrl_01`–`ctrl_04`):** Direct-stock `-s -P -B -u` + `__PYVENV_LAUNCHER__` pass (`P`); `-I` effective mismatch despite `PYTHONHASHSEED="0"` (`M`); bare `-s -P -B -u` base `site-packages` leak (`M`); unobserved `hash_randomization` (`U`).
- **Omitted member & continuity controls (`ctrl_05`–`ctrl_07`):** Joint inventory/read omission caught by $E_r$ (`M`); omitted sealed member with unobserved read proving `M` dominates `U` (`M`, fixing `amendments.py:inventory()`); endpoint-match with handle gap and `FILE_SHARE_WRITE` scorer open (`M`).
- **Phase-error & score controls (`ctrl_08`–`ctrl_11`):** Disputed WP-0045 $j=2 \in D_1 \setminus D_2$ reporting BOTH `rep.2` and `page.2` (`M`); empty support with native emitted integer reporting BOTH `empty_support` and `emitted_outside_support` (`M`); partial-phase missing `page` vector preserving `rep.1` fault (`M`); signed-zero `-0.0`/`+0.0` tie choosing ID `0` while preserving exact bits (`P`).
- **Mixed-run & replay-gate controls (`ctrl_12`–`ctrl_14`):** 4 rows from `r_pass` + 1 borrowed row from `r_other` failing $J_5$ (`M`); historical WP-0043 `M` + duplicated position `1448` failing both `V_stock` and multiplicity (`M`); 5 distinct same-run passing rows yielding `consider_private_replay = True` while `execute_stage3 = False` (`P`).
- **Static-before-deferral & crosswalk/order controls (`ctrl_15`–`ctrl_16`):** Stage-0 `ASSESS` catching Stage-2 `tf32` static conflict before deferral with distinct `first_conflict = ["exec.backend.tf32"]` vs `first_finding = ["route.design"]` (`M`); Eq. (6) `J_k=0 -> incomparable` precedence before `?`, `ABSENT != null`, `0 != false`, and cyclic edge detection yielding `M_integrity` (`M`).
