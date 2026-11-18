# WP-0017 Engine (`docs/research/WP-0017/engine`)

Granular 6-switch runtime decomposition (`S0`, `S1a`, `S1b`, `S1c`, `S2`, `S3`), serial-decode teacher-forced BPE span-logit probe, CPU verification suite, and isolated supervisor launcher for **WP-0017** over frozen `baidu/Unlimited-OCR-2` (`0480966938291445591f69f08a13b041c073a96a`).

Incorporates `eld-rd-astra`'s joint peer-review fixes (`carbon-peer-fixes.patch`, SHA-256 `94ff1ca32361ca4b6d05cebe25e8a3bc910b745ef2eaecd4250a4c8ce177c71b`) plus Carbon's 4-endpoint × 2-window + external `check_endpoints.py` causal-attribution gate and standalone two-suborder launcher/analyzer support. See [CONTRACT.md](CONTRACT.md) for full switch semantics, observer disclosure, probe formulas, and JSON schemas.

## CPU-Only Verification (No GPU / No Timed Model Calls)

```powershell
$env:CUDA_VISIBLE_DEVICES = "-1"
& "C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv\Scripts\python.exe" -I -B `
  "C:\Users\jackg\eLedgerCare-Speed\WP-0017\coordination\peer-fixes\check_peer_fixes.py" `
  --source docs/research/WP-0017/engine

& "C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv\Scripts\python.exe" -I -B `
  docs/research/WP-0017/engine/verify_cpu.py `
  --label wp0017-cpu-preflight `
  --receipt-out docs/research/WP-0017/engine/cpu-preflight-receipt.json
```

## Reproducible Coordinator / Reviewer Stage A1 Suborder Commands (Under Signed Lease Only)

### Suborder 1 — Four Anchored Endpoints (`native,all_off,carbon_bf16,all_on`)

```powershell
& "C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv\Scripts\python.exe" -I -B `
  docs/research/WP-0017/engine/launch.py `
  --source <FROZEN_40_HEX_COMMIT_SHA> `
  --owner review `
  --run a1-<tag>-endpoints `
  --lease a1-<tag> `
  --plan "C:\Users\jackg\eLedgerCare-Speed\WP-0017\coordination\a1-inputs.json" `
  --sha256 e7f47d141972d0e32c53d16e090fcddc237c453ecfc2eaf5d494c6d3426bc8ef `
  --seconds 2700 `
  --min-vram-mib 12000 `
  --warmup-count 3 `
  --configs native,all_off,carbon_bf16,all_on
```

Followed immediately by coordinator's 8-window endpoint parity gate (`docs/coordination/WP-0017/check_endpoints.py`) producing `endpoint-check.json`.

### Suborder 2 — Twelve Single-Switch Additions & Removals (No Auto-Pair Wave)

Runs in its own fresh directory without assuming Suborder 1 segments exist in that directory, and never auto-spawns pair removals:

```powershell
& "C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv\Scripts\python.exe" -I -B `
  docs/research/WP-0017/engine/launch.py `
  --source <FROZEN_40_HEX_COMMIT_SHA> `
  --owner review `
  --run a1-<tag>-switches `
  --lease a1-<tag> `
  --plan "C:\Users\jackg\eLedgerCare-Speed\WP-0017\coordination\a1-inputs.json" `
  --sha256 e7f47d141972d0e32c53d16e090fcddc237c453ecfc2eaf5d494c6d3426bc8ef `
  --seconds 7200 `
  --min-vram-mib 12000 `
  --warmup-count 3 `
  --configs add_S0,add_S1a,add_S1b,add_S1c,add_S2,add_S3,remove_S0,remove_S1a,remove_S1b,remove_S1c,remove_S2,remove_S3
```

### Reviewer Raw-Output Combination & Causal Attribution (`a1_analyze.py`)

Combines raw outputs across Suborder 1 and Suborder 2 (plus any later separately bound pair suborder `--configs remove_Sa_Sb,...`), gated on both internal 8/8 endpoint parity and coordinator's external `endpoint-check.json`:

```powershell
& "C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv\Scripts\python.exe" -I -B `
  docs/research/WP-0017/engine/a1_analyze.py `
  --run-dirs `
    "C:\Users\jackg\eLedgerCare-Speed\WP-0017\review\runs\a1-<tag>-endpoints" `
    "C:\Users\jackg\eLedgerCare-Speed\WP-0017\review\runs\a1-<tag>-switches" `
  --endpoint-check "C:\Users\jackg\eLedgerCare-Speed\WP-0017\review\runs\a1-<tag>-endpoints-order\endpoint-check.json" `
  --a1-manifest "C:\Users\jackg\eLedgerCare-Speed\WP-0017\coordination\a1-inputs.json" `
  --a1-manifest-sha256 e7f47d141972d0e32c53d16e090fcddc237c453ecfc2eaf5d494c6d3426bc8ef `
  --out "C:\Users\jackg\eLedgerCare-Speed\WP-0017\review\runs\a1-<tag>-combined-summary.json"
```

### Stage A2 / A3 Document Replays (`dev/id_ablation`, `H`, `A`)

Once Stage A1 freezes a validated 1- or 2-removal target in `surgical.json` (`frozen_switch_config` and `frozen_bits`), `launch.py` executes standard `{"requests": [...]}` AB/BA plans across `native`, `carbon_bf16`, and `carbon_surgical` via `doc_trial.py` (reusing original `docs/research/WP-0015/astra/trial.py:document` persisted outputs verbatim).
