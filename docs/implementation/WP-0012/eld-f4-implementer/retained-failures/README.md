# Retained Failure Lineage (`WP-0012 / 001` Rehearsal Preparation)

## 1. Initial Helper `dotnet build --locked-mode` CLI Switch Mismatch (`51cf3ecc23a1bb847f8ea7618fb9960b5d18f325`)

- **Artifact:** [51cf3ecc-02-dotnet-build-flag.log](51cf3ecc-02-dotnet-build-flag.log)
- **Cause:** In initial frozen helper commit `51cf3ecc23a1bb847f8ea7618fb9960b5d18f325`, Step `02` of [validate_wp0012_preparation_cpu.py](../helpers/validate_wp0012_preparation_cpu.py) passed `--locked-mode` directly to `dotnet build` (`MSB1001: Unknown switch --locked-mode`) rather than running `dotnet restore --locked-mode` followed by `dotnet build -c Release --no-restore`. No PostgreSQL service, external root, or rehearsal driver changed (`RUNBOOK.md`, `run_wp0012_rehearsal.py`, and `drive_rehearsal_edge.mjs` blobs remained byte-identical).
- **Resolution:** Split Step `02` in [validate_wp0012_preparation_cpu.py](../helpers/validate_wp0012_preparation_cpu.py) into `02a-dotnet-restore-locked` (`dotnet restore ELedgerCare.slnx --locked-mode --configfile .local/nuget/offline.nuget.config`) and `02b-dotnet-build-release` (`dotnet build ELedgerCare.slnx -c Release --no-restore`).
