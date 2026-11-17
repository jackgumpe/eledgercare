# Retained Failure Lineage (`WP-0012 / 001` Rehearsal Preparation)

## 1. Initial Helper `dotnet build --locked-mode` CLI Switch Mismatch (`51cf3ecc23a1bb847f8ea7618fb9960b5d18f325`)

- **Artifact:** [51cf3ecc-02-dotnet-build-flag.log](51cf3ecc-02-dotnet-build-flag.log)
- **Cause:** In initial frozen helper commit `51cf3ecc23a1bb847f8ea7618fb9960b5d18f325`, Step `02` of [validate_wp0012_preparation_cpu.py](../helpers/validate_wp0012_preparation_cpu.py) passed `--locked-mode` directly to `dotnet build` (`MSB1001: Unknown switch --locked-mode`) rather than running `dotnet restore --locked-mode` followed by `dotnet build -c Release --no-restore`. No PostgreSQL service, external root, or rehearsal driver changed (`RUNBOOK.md`, `run_wp0012_rehearsal.py`, and `drive_rehearsal_edge.mjs` blobs remained byte-identical).
- **Resolution:** Split Step `02` in [validate_wp0012_preparation_cpu.py](../helpers/validate_wp0012_preparation_cpu.py) into `02a-dotnet-restore-locked` (`dotnet restore ELedgerCare.slnx --locked-mode --configfile .local/nuget/offline.nuget.config`) and `02b-dotnet-build-release` (`dotnet build ELedgerCare.slnx -c Release --no-restore`).

## 2. Helper `model-files.json` Field Name Mismatch (`7a1bdea970d84df297a07593a50184b32f766255`)

- **Artifact:** [7a1bdea9-07-model-manifest-size-key.log](7a1bdea9-07-model-manifest-size-key.log)
- **Cause:** In helper commit `7a1bdea970d84df297a07593a50184b32f766255`, Steps `01`–`06` passed (`node --check`, offline `dotnet restore` & `Release` build, `ng build`, `18/18` guard unit tests, PostgreSQL `55438` startup, and `eledgercare_demo_wp0012_author` migration), and Step `07` failed in `inspect_readonly_q0_and_demo_roots_cpu` with `ERROR: 'size_bytes'` because [model-files.json](../../../../../workers/local_ocr/manifests/model-files.json) uses `"size"` (plus `"git_blob_sha1"` on non-LFS files and `"sha256"` on LFS weight files; `finally:` stopped PostgreSQL `55438` cleanly).
- **Resolution:** Updated `inspect_readonly_q0_and_demo_roots_cpu` in [run_wp0012_rehearsal.py](../helpers/run_wp0012_rehearsal.py) to read `entry["size"]` for fast stat checks and delegate full digest/notice/AST checks directly to production-owned `normalize_and_verify_model_dir` + `verify_model_sources_ast_safety` in [verify_runtime.py](../../../../../workers/local_ocr/local_ocr/verify_runtime.py).

