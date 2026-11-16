# WP-0006 F2 Corrected Runtime Driver v2 Execution Procedure (`eld-f2-implementer`)

> [!IMPORTANT]
> This procedure prepares **only** the versioned acceptance driver (`v2`) for corrected product source `8a73b7a5dab51e3ccf803aceedded4929529dd35` under coordinator preparation authority `35e2f44d788a99ad1b2d10d1af95536cf1d1981a`. Neither this document nor returned lease `WP-0006-author-runtime-20261116T062318Z` (`717a768994bbbabf75b8ee96b3b1aadca1bc5df3`) authorizes GPU or model execution.

## 1. Preserved Historical Artifacts (Never Overwritten)

- **Original v1 driver & initial pre-model failed-trial bundle**: `docs/implementation/WP-0006/runtime-author/**` (Git tree `72bb71576a88506d486c78d6ce0d3e0b4f66ebf0`)
- **Stage 1 CPU/PostgreSQL/Edge checkpoint**: `docs/implementation/WP-0006/stage1-checkpoint/**` (Git tree `4acac7f102826f445687693190a34098d640bb6c`)
- **Consolidated source/CPU response checkpoint**: `docs/implementation/WP-0006/source-response/**` (Git tree `352d356920a7cc0b2b6c3c40d63ad246db441822`)
- **Initial trial ignored scratch**: `.scratch/stage2-runtime/**` (explicitly blocked from `--scratch-dir` in `v2`)
- **Initial trial PostgreSQL database**: `eledgercare_f2_runtime_author` (explicitly blocked in `v2`; `v2` uses `eledgercare_f2_runtime_author_v2`)
- **Retained external failed run directory**: `C:\Users\jackg\eLedgerCare-F2\WP-0006\author\runs\attempt-01a1e316-879e-737e-b222-cf9ebea58b09` (snapshotted before live execution if `runtime_root` points to `...\author`, excluded from new-attempt delta counts, and verified byte-for-byte unchanged in `finally`)

## 2. Versioned v2 Driver Files & Output Locations

- **Runtime driver**: `docs/implementation/WP-0006/runtime-corrected-preparation/helpers/run_f2_author_runtime_v2.py`
- **Microsoft Edge saved-result verifier**: `docs/implementation/WP-0006/runtime-corrected-preparation/helpers/verify_ui_real_results_v2.mjs`
- **CPU-only preparation validator**: `docs/implementation/WP-0006/runtime-corrected-preparation/helpers/validate_driver_v2_cpu.py`
- **Versioned live scratch output**: `.scratch/stage2-runtime-v2/{plan-and-helper-freeze-v2.json,trial-summary-v2.json,lease-return-v2.json,observations/*}`
- **Future live evidence Git destination**: `docs/implementation/WP-0006/runtime-author-v2/**` (followed by canonical `docs/agent-reports/eld-f2-implementer/WP-0006/003_2026-11-16_implementation_eld-f2-implementer.md`)

## 3. Release & Tree Validation Contract (`validate_release_contract`)

Before any database, API, browser, or model process can start, `run_f2_author_runtime_v2.py` loads `<release_commit>:<release_path>` from immutable Git objects and enforces:

1. **Fresh Authority Only**: Rejects historical/returned/preparation commits (`d106db76...`, `717a7689...`, `2c549274...`, `2ce3366d...`, `35e2f44d...`) and returned lease `WP-0006-author-runtime-20261116T062318Z`.
2. **Exact Identity & Clean Executing HEAD**: Verifies `owner == "eld-f2-implementer"`, `conversation_id == "2b6861af-031b-4e8b-9ce9-2a6d476f9da0"`, `model == "gemini-4-carbon-high"`, `effort == "high"`, `git status --porcelain == ""`, and `git rev-parse HEAD == release["executing_head"]`.
3. **Git Ancestry & Exact Tree Objects (No `HEAD~1 == source_commit` Assumption)**:
   - Verifies `8a73b7a5dab51e3ccf803aceedded4929529dd35` (`source_commit`) and `386d5c30809c3c04d6640d9433eb4263306ac126` (`source-response` checkpoint) are ancestors of `executing_head` via `git merge-base --is-ancestor`.
   - Verifies zero product/test/worker/web/deploy/Q0/research/evaluation/prior-evidence paths changed between `8a73b7a5dab51e3ccf803aceedded4929529dd35` and `executing_head`.
   - Verifies exact Git tree OIDs at both `source_commit` and `executing_head`:
     - `src`: `73d0146b3624ab4928a4d2cda7806d7d6166906e`
     - `workers/local_ocr`: `1ed609368ca4c6bff8b92231362be2d802ae8baf`
     - `workers/ocr`: `493935fad8163ec9242b396232a55564446a52e6`
     - `web`: `f0877a006922818bf731d5f87603a368ed782487`
     - `tests`: `5ad9bd15f41ab24bd5851ca02bfa0d8054dc1453`
     - `deploy`: `dade6a38e165b5cc2ba81ba895bd9d3c572d26f2`
     - Protected trees (`qualification`, `research`, `evaluation`, `stage1-checkpoint`, `runtime-author`, `source-response`) unchanged, and `docs/agent-reports/eld-f2-implementer` absent prior to completion.
4. **Accepted Design & Independent Source-Review Bindings**: Verifies `accepted_design_review == "e2452e1ab3d8937868c07ffb30ce430715b5be78"` and requires a valid accepted independent source-reconciliation commit SHA (rejecting missing bindings or pre-reconciliation `10193e2c904f99cfc23c97367f1e5d881b0630f2`).
5. **Updated Worker Source Digest & Pinned Artifacts**: Verifies both the release JSON and live worktree computations match `worker_source_sha256 = c1c324c36e27f57c3c4ac4a1462984fbe586ad43ab82af3a2883bb7eac4c0d54`, `model_manifest_sha256 = 0df07bc6...`, `dependency_lock_sha256 = 582071bf...`, `worker_config_1p/2p/3p_sha256`, and the 3 admitted PDF fixture SHA-256s.
6. **Active Sole GPU Lease, Ports, Scoped Roots & Finite 4-Attempt Matrix**: Verifies `released_utc <= now < expires_utc` (`>= 300s` remaining before start and non-expired before each of the 4 attempts), `gpu_uuid == "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d"`, `ports == {"api": 5190, "ui": 4210, "postgres": 55434}`, scoped external roots, `max_model_attempts == 4` (`[1, 1, 2, 0]`, zero warmups, zero holdouts), and pre-lease observation blob SHA-256s.

## 4. Future Live Invocation Sequence (Only After Coordinator Runtime Release)

```powershell
Set-Location "C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-f2-implementer"
git fetch origin

# 1. Pure CPU/Git dry-run validation of the supplied future coordinator release:
python -B docs/implementation/WP-0006/runtime-corrected-preparation/helpers/run_f2_author_runtime_v2.py `
  --dry-run-validate `
  --release-commit <FUTURE_COORDINATOR_RELEASE_SHA> `
  --release-path <FUTURE_RELEASE_JSON_PATH> `
  --validation-output .scratch/stage2-runtime-v2/dry-run-validation.json

# 2. Finite 4-model-attempt real runtime execution under active sole GPU lease:
python -B docs/implementation/WP-0006/runtime-corrected-preparation/helpers/run_f2_author_runtime_v2.py `
  --execute-live `
  --release-commit <FUTURE_COORDINATOR_RELEASE_SHA> `
  --release-path <FUTURE_RELEASE_JSON_PATH>
```
