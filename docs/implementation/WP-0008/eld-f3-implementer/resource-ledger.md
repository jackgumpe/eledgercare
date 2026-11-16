# WP-0008 F3 Author Resource & Contract Ledger (`eld-f3-implementer`)

- **Owner / Role**: `eld-f3-implementer` (fresh Google DeepMind Gemini 4 Carbon (High) session `ef53d3f3-ca53-482e-8fa7-a3cc1670564e`, effort `high`)
- **Owned Worktree**: `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-f3-implementer`
- **Owned Branch**: `feature/wp-0008-f3-review`
- **Packet Base / Dispatch Authority**: `5e1241d6d365d664f12619d415f48ec3d3b7ddca` / `715d62533cdf69ee3f144ac8bbf5184bc0d78ad3`
- **Accepted Design & Independent Checkpoints**:
  - Coordinator design: [`docs/design/F3-review-correction.md`](../../../design/F3-review-correction.md) (`c5b5db3af96abf155c806082583b8a92c687f54d`, report `30bb49ed56c32bda61a6907d49bd183e7b292268`)
  - Independent design review: [`docs/reviews/WP-0008/eld-f3-reviewer/design/README.md`](../../../reviews/WP-0008/eld-f3-reviewer/design/README.md) (`bff139bcdf55df77a821b858513b7e6bf5d96b87`, carrying `F3-KR-01` and `F3-BIC-01`..`06`)
  - Implementation kickoff: [`docs/kickoffs/WP-0008-eld-f3-implementer.md`](../../../kickoffs/WP-0008-eld-f3-implementer.md)

## Owned Loopback Resources & Storage

| Resource | Author Binding | Isolation / Notes |
| --- | --- | --- |
| Loopback PostgreSQL 18.7 | `127.0.0.1:55436` | Worktree-owned `.local/postgres-data` & `.local/secrets/pg-local.json` (gitignored); `fsync=on`, `full_page_writes=on`, `synchronous_commit=on`, `scram-sha-256` |
| Loopback API (`ELedgerCare.Api`) | `127.0.0.1:5390` | Default `Api:Port = 5390`; overridable via `Api__Port` / `-ApiPort` / `ELEDGERCARE_API_PORT` (`5490` for independent reviewer) |
| Loopback Angular Dev UI | `127.0.0.1:4410` | Default `4410`; overridable via `-UiPort` / `ELEDGERCARE_UI_PORT` (`4510` for independent reviewer) |
| PostgreSQL 18.7 Binaries | `.local/tools/pgsql-18.7-1` | Official EDB `18.7-1` server subset (`1,597` files, `subset_manifest_sha256 = 47c3deb9c917f79c353b3683b2c2611ee975285ea06226c8f72444c96ce9051f`) |
| GPU / OCR Inference | **Disabled (`LocalOcr:Enabled = false`)** | Zero GPU leases, zero model imports, zero `C:\Users\jackg\eLedgerCare-Q0\WP-0005` writes, zero `WP-0009` sealed-path access |

## Attributed Genuine F2 Acceptance Seeds (Test-Only)

All F3 database seeding occurs exclusively inside test-only helpers (`tests/` and `web/e2e/` / `docs/implementation/WP-0008/eld-f3-implementer/`) using unchanged accepted F2 artifacts:

1. **Single-page raster work order (`SYN-WO-01-v1-raster300.pdf`)**:
   - Input PDF: `tests/fixtures/SYN-WO-01-v1-raster300.pdf` (`372,258` bytes, SHA-256 `47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd`, `1` page)
   - Genuine raw model output: `docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs/attempt-01a1e571-297a-7f0e-a293-e9e1c0851cd4/output/raw_output.utf8.bin` (`3,236` bytes, SHA-256 `7503761ae46afef6adf579881d011764283474354fac3e185598fc7d266aff95`)
   - Genuine worker envelope: `docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs/attempt-01a1e571-297a-7f0e-a293-e9e1c0851cd4/output/envelope.json` (`2,909` bytes, SHA-256 `8e6e5b81c5bc1fb6e102438daef815bf19f4722994ba5acf737b732e703779ee`)
   - Attribution: Product source `8a73b7a5dab51e3ccf803aceedded4929529dd35`, executing revision `b343f6ff78aa41332ecbe957577b6776f8edc22f`, independent runtime evidence `7f0ec3a9338606ce54c4c6d2eeabab8a2c245e2a`, accepted report `c854a1d4c306c3b10d78df42a1a2552a06bb4a98` (also matching author run `attempt-01a1e509-f5d4-7a01-80f1-4f23fe282930` raw SHA-256 `7503761a...` at `48e8896d53fa001bba55276ac244f4adee377587` / `3ece293f4ea9b78f19dbfb7f95472b95d091d79e`).
2. **Three-page maintenance invoice packet (`SYN-MP-01-v0-clean.pdf`)**:
   - Input PDF: `tests/fixtures/SYN-MP-01-v0-clean.pdf` (`8,422` bytes, SHA-256 `15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3`, `3` pages)
   - Genuine raw model output: `docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs/attempt-01a1e573-ca25-733e-b048-44c8ea2ac61d/output/raw_output.utf8.bin` (`7,511` bytes, SHA-256 `c399ad892e257500e2b6a9ac8b0bc3d8a17e9c10041262c4bca6a48fb9b9b639`)
   - Genuine worker envelope: `docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs/attempt-01a1e573-ca25-733e-b048-44c8ea2ac61d/output/envelope.json` (`3,281` bytes, SHA-256 `7fd536919461171d933cb1e8db36a21164db5b7b04bcf364c094cace3c012d96`)
   - Attribution: Same accepted F2 execution `7f0ec3a9338606ce54c4c6d2eeabab8a2c245e2a` / `c854a1d4c306c3b10d78df42a1a2552a06bb4a98` on product source `8a73b7a5dab51e3ccf803aceedded4929529dd35`.
