# WP-0017 Engine (`docs/research/WP-0017/engine`)

Granular 6-switch runtime decomposition (`S0`, `S1a`, `S1b`, `S1c`, `S2`, `S3`), serial-decode teacher-forced BPE span-logit probe, CPU verification suite, and isolated supervisor launcher for **WP-0017** over frozen `baidu/Unlimited-OCR-2` (`0480966938291445591f69f08a13b041c073a96a`).

See [CONTRACT.md](CONTRACT.md) for full switch semantics, observer disclosure, probe formulas, and JSON schemas.

## CPU-Only Verification (No GPU / No Timed Model Calls)

```powershell
$env:CUDA_VISIBLE_DEVICES = "-1"
& "C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv\Scripts\python.exe" -I -B `
  docs/research/WP-0017/engine/verify_cpu.py `
  --label wp0017-cpu-preflight `
  --receipt-out docs/research/WP-0017/engine/cpu-preflight-receipt.json
```

## Reproducible Reviewer / Coordinator CLI Commands (Under Signed Coordinator Lease Only)

### Option A — Run Stage A1 Directly Against Frozen `a1-inputs.json` (16-Config Canonical Sweep)

Runs each of the 16 configurations (`native`, `all_off`, `carbon_bf16`, `all_on`, `add_S0..add_S3`, `remove_S0..remove_S3`) in its own fresh isolated child process (`python.exe -I -B`), with 3 untimed 1-page settling warmups, uncontaminated Phase-1 ordinary free-run timing on `window-019` and `window-037`, and Phase-2 serial-decode teacher-forced probes (2 independent `forced_native` passes on endpoints/additions + dual `forced_native`/`free_running` prefixes on `037`):

```powershell
& "C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv\Scripts\python.exe" -I -B `
  docs/research/WP-0017/engine/launch.py `
  --source <FROZEN_40_HEX_COMMIT_SHA> `
  --plan "C:\Users\jackg\eLedgerCare-Speed\WP-0017\coordination\a1-inputs.json" `
  --sha256 e7f47d141972d0e32c53d16e090fcddc237c453ecfc2eaf5d494c6d3426bc8ef `
  --owner review `
  --run a1-primary `
  --seconds 4200 `
  --lease <LEASE_ID> `
  --min-vram-mib 12000
```

*(Optional flags when invoking against `a1-inputs.json`: `--configs remove_S1a_S1c,remove_S1b_S1c` for targeted Stage-A1b pair removals, `--auto-pair-removals` to run admitted pairs automatically in the same run if no single removal restores both IDs, `--warmup-count 3`.)*

### Option B — Emit & Bind an Explicit Stage A1 Plan JSON First

```powershell
& "C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv\Scripts\python.exe" -I -B `
  docs/research/WP-0017/engine/launch.py `
  --emit-a1-plan "C:\Users\jackg\eLedgerCare-Speed\WP-0017\coordination\plans\a1-primary.json" `
  --a1-manifest "C:\Users\jackg\eLedgerCare-Speed\WP-0017\coordination\a1-inputs.json"
```

Then pass `--plan ...\a1-primary.json --sha256 <PLAN_SHA256>` to `launch.py` inside `device_lease.py`.

### Stage A2 / A3 Document Replays (`dev/id_ablation`, `H`, `A`)

Once Stage A1 freezes `surgical.json` (setting `frozen_switch_config` and `frozen_bits`), `launch.py` executes standard `{"requests": [...]}` AB/BA plans across `native`, `carbon_bf16`, and `carbon_surgical` via `doc_trial.py` (reusing original `docs/research/WP-0015/astra/trial.py:document` persisted outputs verbatim).
