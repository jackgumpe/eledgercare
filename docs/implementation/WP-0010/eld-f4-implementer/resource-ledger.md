# WP-0010 F4 Author Resource & Provenance Ledger (`eld-f4-implementer`)

## 1. Owned Loopback Ports & Disjoint Reservations (`F4-KR-01`, `F4-BIC-08`)

| Resource | Author Default (`eld-f4-implementer` `/003`) | Independent Reviewer Override (`eld-f4-reviewer` `/004`, zero source edits) | Override Mechanism |
| --- | --- | --- | --- |
| `ELedgerCare.Api` | `127.0.0.1:5590` | `127.0.0.1:5690` | `Api__Port`, `-ApiPort`, `ELEDGERCARE_API_PORT` |
| Angular UI (`ng serve`) | `127.0.0.1:4610` | `127.0.0.1:4710` | `-UiPort`, `ELEDGERCARE_UI_PORT`, `--port` |
| PostgreSQL `18.7` | `127.0.0.1:55438` | `127.0.0.1:55439` | `setup-cluster.ps1 -Port`, `.local/secrets/pg-local.json` |

All `24` loopback ports across `F1` (`5180/4200/55432`, `5280/4300/55433`), `F2` (`5190/4210/55434`, `5290/4310/55435`), `F3` (`5390/4410/55436`, `5490/4510/55437`), and `F4` (`5590/4610/55438`, `5690/4710/55439`) are pairwise disjoint.

## 2. Pinned Toolchain & Binary Provenance (Read-Only Offline Reuse)

- **`.NET SDK`**: `10.0.403` (`dotnet-ef 10.0.15` restored from local `.local/nuget/feed`, `53` locked NuGet packages in `.local/nuget/packages`).
- **Node / Angular / Playwright / Browser**: `Node v24.18.0`, `npm 11.16.0`, `@angular/cli 22.2.7` (`@angular/core 22.2.6`), `@playwright/test 1.65.1`, Microsoft Edge `157.0.4341.60` (`msedge` channel).
- **PostgreSQL `18.7` (`127.0.0.1:55438`)**: `1,597` files in `.local/tools/pgsql-18.7-1`, `subset_manifest_sha256 = 47c3deb9c917f79c353b3683b2c2611ee975285ea06226c8f72444c96ce9051f`, official EDB archive `central_directory_sha256 = 3132ca63b424f7ec371eabe50753ad7cd036278d942a6ea465547b17bf90a149`, Authenticode `Valid`.
- **OCR / GPU Isolation**: `LocalOcr:Enabled = false` throughout all preparation and F4 verification runs; `0` GPU queries, `0` model loads, `0` `workers/local_ocr` inference launches, and `0` accesses to `WP-0011` or `WP-0009` sealed R&D paths.

## 3. Retained Pre-F4 Database & Attributed Test-Only F2 Artifacts

- **Retained pre-F4 F3 database (`eledgercare_f4_author_seed_f3`)**:
  - Constructed in verified author preparation publication `033d1dabb348b4dd6ba450ae9397c9f901a8b97b` (`prepare_and_verify_f3_seed.py` at `6e5590be39fd6dbb7eb00c672da5c0a954d9cb2c`).
  - Preserved untouched in `.local/postgres-data` at exact canonical 8-table + 3-migration SHA-256 **`76e7970b50b8fbf968c44e534d6383bdd8251e9f285e2373ea026eeeea157085`**.
  - Cloned via `CREATE DATABASE eledgercare_f4_author_migrated OWNER eledgercare_migrator TEMPLATE eledgercare_f4_author_seed_f3` (verified at `76e7970b50b8fbf968c44e534d6383bdd8251e9f285e2373ea026eeeea157085` prior to migration), forward-migrated with `prepare-database.ps1 -Database eledgercare_f4_author_migrated` (`20261117091519_AddSourceLinkedArchive` + `grant-runtime.sql`), backfilled with `LocalOcr:Enabled=false`, verified in Microsoft Edge before and after API + PostgreSQL `18.7` restart, and retained alongside `eledgercare_f4_author_seed_f3`.
- **Attributed test-only WP-0006 F2 artifacts** (seeded extraction outputs, explicitly distinguished from freshly executed OCR):
  - `SYN-WO-01-v1-raster300.pdf` (`372,258` B, SHA-256 `47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd`) -> raw output `3,236` B, SHA-256 `7503761ae46afef6adf579881d011764283474354fac3e185598fc7d266aff95`.
  - `SYN-MP-01-v0-clean.pdf` (`8,422` B, SHA-256 `15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3`) -> raw output `7,511` B, SHA-256 `c399ad892e257500e2b6a9ac8b0bc3d8a17e9c10041262c4bca6a48fb9b9b639`.
  - Provenance: product source `8a73b7a5dab51e3ccf803aceedded4929529dd35`, independent runtime evidence `7f0ec3a9338606ce54c4c6d2eeabab8a2c245e2a`, accepted report [`WP-0006 / 004`](../../../agent-reports/eld-next-reviewer/WP-0006/004_2026-11-16_review_eld-next-reviewer.md) (`c854a1d4c306c3b10d78df42a1a2552a06bb4a98`).
