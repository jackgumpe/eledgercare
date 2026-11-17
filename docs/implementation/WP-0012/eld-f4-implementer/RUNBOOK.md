# WP-0012 Complete-Workflow Demonstration Runbook & Rehearsal Contract (`eld-f4-implementer`)

- **Packet / Sequence:** `WP-0012 / 001` (CPU-only preparation & runbook; live runtime `WP-0012 / 003` **NOT RUN — HELD** for independent `/002` acceptance and coordinator sole-GPU lease)
- **Author / Conversation / Model:** `eld-f4-implementer` · continued Antigravity CLI conversation `b7c54417-db09-49bd-8d2b-7cc808f113be` · `Gemini 4 Carbon (High)` (`high` effort)
- **Owned Branch / Worktree:** `rehearsal/wp-0012-product` in `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-f4-implementer`
- **Governing Authority & Kickoff:** [WP-0012-0013-authority.md](../../../coordination/WP-0012-0013-authority.md) and [WP-0012-eld-f4-implementer.md](../../../kickoffs/WP-0012-eld-f4-implementer.md) at `47fbc7612e4a08cf1960ad7ac01bd2843ae645e5` (accepted packet base `73c8d3c4f0a00312e3444328331b6cbd6406e882`, unchanged accepted F4 source `c1fed68020ae67e8b4763bc6ea5473adaa86de2b`)

## 1. Scope, Isolation, & Honesty Boundaries

1. **Unchanged Accepted Product Source:** Zero edits to `src/` (`9760402fa88dcb343c28b14ad4de1bcb2fbafb2e`), `web/` (`50fbbee1f58aace4e6ec36bd64203146d23aa96f`), `tests/` (`25c21310699086acb818549b2a4c0b99469208f1`), `deploy/` (`86e0c73d4b4c07bbdf92ebcd65a0903fc9c039f1`), `workers/local_ocr/` (`dc9b69e480f93db1e73ebdd65719efaa9aeab298`), or [ELedgerCare.slnx](../../../../ELedgerCare.slnx) (`c00c2bc5ef46019fb4452fdf0bba7ca2271fc976`). Default `LocalOcr:Enabled = false` in [appsettings.json](../../../../src/ELedgerCare.Api/appsettings.json) remains unchanged; process-local `LocalOcr__Enabled=true` is passed only to the leased API child during Phase A of `WP-0012 / 003`.
2. **Owned Resources & Preserved Historical State:**
   - Loopback ports: PostgreSQL `18.7` `127.0.0.1:55438`, API `127.0.0.1:5590`, UI `127.0.0.1:4610` (disjoint from reviewer `55439 / 5690 / 4710`).
   - New owned database: **`eledgercare_demo_wp0012_author`** (`0` seeded rows; all data during `/003` originates from live Microsoft Edge browser interactions and the real `workers/local_ocr/run_worker.py` worker). Retained F4 databases `eledgercare_f4_author_seed_f3` (`76e7970b...`) and `eledgercare_f4_author_migrated` (`ad4f44bc...` / `78f0f273...`) remain untouched.
   - External roots: `C:\Users\jackg\eLedgerCare-Q0\WP-0005` (strictly read-only model/venv/notices); `C:\Users\jackg\eLedgerCare-Demo\WP-0012\author` (writable attempt/evidence root for `/003`, preserving any pre-existing contents; untouched during `/001` CPU preparation).
3. **Environmental & Measurement Disclosures:** Worker offline flags (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `PIP_NO_INDEX=1`, etc.) prevent library-initiated downloads; OS-level outbound network denial is not claimed. Elapsed wall/phase times and working-set memory recorded during `/003` are single-host local observations on synthetic 1–3 page documents, not production throughput or accuracy guarantees.

## 2. Pinned Artifact Digests & Finite 2-Attempt Guard Matrix

| Parameter / Artifact | Bound Value |
| --- | --- |
| Fixture #1 ([SYN-WO-01-v1-raster300.pdf](../../../../tests/fixtures/SYN-WO-01-v1-raster300.pdf)) | `1` page · `372,258` bytes · SHA-256 `47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd` |
| Fixture #2 ([SYN-MP-01-v0-clean.pdf](../../../../tests/fixtures/SYN-MP-01-v0-clean.pdf)) | `3` pages · `8,422` bytes · SHA-256 `15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3` |
| Model checkpoint (`baidu/Unlimited-OCR-2`) | Revision `0480966938291445591f69f08a13b041c073a96a` · [model-files.json](../../../../workers/local_ocr/manifests/model-files.json) SHA-256 `0df07bc60abf6937c917040bced32afabd7e4d11bafc0bd99902abca610a81be` |
| Dependency lock ([dependency-lock.json](../../../../workers/local_ocr/manifests/dependency-lock.json)) | SHA-256 `582071bf20eaca1836c3d1cef21d31cbdaa1e1407184033a918a40612c128111` (`torchvision-local-sha256-TOFU` disclosed) |
| Worker source & configs (`workers/local_ocr`) | Source `c1c324c36e27f57c3c4ac4a1462984fbe586ad43ab82af3a2883bb7eac4c0d54` · `1p` `579aad63a9893a58466baf005ea63f87e92540d4c1f71f6b3c399e8b1e6b35ff` · `3p` `ac90459ca4011b5859cfdd0b224d5ea247489b7c01775118736df7c1c9819e86` |
| Finite model-attempt ceiling | **`2` attempts max** (`1` 1-page + `1` 3-page), sequential concurrency `1`, **`0` warmups**, **`0` automatic retries**; first `failed`/`interrupted` attempt stops immediately for evidence preservation and lease return |
| Lease & storage bounds | Active coordinator `WP-0012` sole lease on `GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d`, window `<= 21,600 s` (`6 h`), `>= 300 s` remaining, owner root `<= 4 GiB` (`4,294,967,296` B), disk free floor `>= 20 GiB` (`21,474,836,480` B) |
| Worker & product ceilings | `1,800 s` load · `1,800 s` 1-page call · `3,600 s` 3-page call · `300 s` stall (`5 s` heartbeat) · `16 MiB` raw output · `64 MiB` child logs · `1..3` extraction pages · `10 MiB` / `50`-page intake |

## 3. Coordinator Runtime Release JSON Contract (For Later `WP-0012 / 003`)

[run_wp0012_rehearsal.py](helpers/run_wp0012_rehearsal.py) (`validate_release_contract`) fails closed unless `--release-commit <40-hex> --release-path docs/coordination/WP-0012/...json` supplies an immutable Git blob matching:
- `schema`: `"eledgercare.wp0012-rehearsal-release/1"` (also accepts `"eledgercare.wp0012-runtime-release/1"` or `"eledgercare.demo-runtime-release/1"`)
- `owner`: `"eld-f4-implementer"`, `conversation_id`: `"b7c54417-db09-49bd-8d2b-7cc808f113be"`, `model`: `"gemini-4-carbon-high"`, `effort`: `"high"`
- `source_commit`: `"c1fed68020ae67e8b4763bc6ea5473adaa86de2b"` (or `"73c8d3c4f0a00312e3444328331b6cbd6406e882"`)
- `executing_head`: exact clean `HEAD` SHA at `/003` launch
- `accepted_preparation_review` (or `accepted_review_002` / `independent_review_002` / `accepted_002`): 40-hex commit SHA of `eld-f4-reviewer`'s accepted `WP-0012 / 002` review
- `product_tree_objects`, `pinned_digests`, `lease_id` (must include `"WP-0012"`), `gpu_uuid`, `released_utc`, `expires_utc`, `max_model_attempts: 2`, `readonly_q0_root`, `runtime_root`: `"C:\\Users\\jackg\\eLedgerCare-Demo\\WP-0012\\author"`, `ports`: `{"api": 5590, "ui": 4610, "postgres": 55438}`, `storage_cap_bytes`: `4294967296`, `free_floor_bytes`: `21474836480`, `allow_test_content`: `false`, `torchvision_local_sha256_TOFU_accepted`: `true`, and `observation_files` (`host-before.json`, `processes-before.json`, `model-before.json`).

## 4. Repeatable Human & Browser Demonstration Walkthrough

### Automated Driver Commands
- **CPU-only dry-run & disabled-OCR preflight (safe anytime, zero model/GPU access):**
  ```powershell
  python -B docs/implementation/WP-0012/eld-f4-implementer/helpers/run_wp0012_rehearsal.py --cpu-dry-run --with-disabled-ocr-smoke --output .scratch/cpu-dryrun.json
  ```
- **Leased 2-attempt live execution (ONLY after `/002` acceptance and coordinator `/003` lease commit):**
  ```powershell
  python -B docs/implementation/WP-0012/eld-f4-implementer/helpers/run_wp0012_rehearsal.py --execute-live --release-commit <RELEASE_SHA> --release-path <DOCS_COORDINATION_WP0012_JSON>
  ```

### Step-by-Step Operator Sequence (Mirrored by [drive_rehearsal_edge.mjs](helpers/drive_rehearsal_edge.mjs))

1. **Upload & Extract Document #1 (`SYN-WO-01-v1-raster300.pdf`, 1 page — Attempt 1 of 2):**
   - At `http://127.0.0.1:4610/`, select `tests/fixtures/SYN-WO-01-v1-raster300.pdf` and click **Submit**. Confirm receipt SHA-256 `47b2df6a...` and status `Awaiting extraction` (`0` OCR attempts run at intake).
   - Click **Open document page**, inspect inline PDF Page 1, and click **Extract document**. Observe persisted status transition (`Queued for extraction` -> `Extraction running` with phase & heartbeat -> `Completed (unreviewed)`).
2. **Compare Against Source PDF, Save Grounded Reviewed Revision #1, & Save Distinct Newer Draft #2:**
   - Click **Review as maintenance work order**. Compare left-pane PDF Page 1 against the five fields:
     - Accept valid machine suggestions matching the printed form (`WO-004192`, `Cedar Hollow Apartments`, `Bldg B - Unit 204`, `2026-10-16`).
     - Edit **Issue & Resolution** (retaining Page 1 `consultedSource` provenance) to append the printed stock-parts table verification from Page 1 (`CAP-45-5MFD-440V (Oval Dual Run Capacitor 45/5 uF 440VAC), CONT-24V-2P30A, 0018-TERM-QC` — grounded directly in the printed Parts table, where raw OCR misreads `5MFD` as `SMFD`).
     - Check confirmation and click **Save reviewed revision** (`Revision #1: reviewed`).
     - Edit **Issue & Resolution** again to append the printed bottom sign-off (`Supervisor Review: D. Callahan (Completed 2026-10-16 10:45).`) and click **Save draft revision** (`Revision #2: draft`), keeping head Draft `#2` distinct from active Reviewed `#1`.
3. **Upload & Extract Document #2 (`SYN-MP-01-v0-clean.pdf`, 3 pages — Attempt 2 of 2):**
   - Click **Intake**, upload `tests/fixtures/SYN-MP-01-v0-clean.pdf` (SHA-256 `15e39351...`), open its document page, and click **Extract document**. Verify ordered 3-page extraction (`Page 1 of 3`..`Page 3 of 3`).
4. **Compare 3-Page Statement & Save Grounded Review With Explicit Unknowns (`Revision #1: reviewed · 2 unknown`):**
   - Click **Review as maintenance work order** and inspect Pages `1`–`3` in the PDF toolbar. Because `SYN-MP-01` is consolidated statement `INV-008810` spanning multiple tickets with no single work-order ID or requested date:
     - Mark **Work Order ID** `unknown` (`"Consolidated monthly statement INV-008810 spans multiple work orders across Pages 1-3; no single Work Order ID applies."`).
     - Edit **Property** to printed `BILL TO` name `Maple Ridge Commons Asset Operations`.
     - Edit **Building / Unit** to printed coverage scope `Buildings A, B, C & Clubhouse`.
     - Mark **Requested Date** `unknown` (`"Statement records Statement Date 2026-10-31 and Due Date 2026-11-30 only; no Requested Date is printed."`).
     - Edit **Issue & Resolution** to printed summary `Consolidated Monthly Maintenance Statement INV-008810 (Contract CTR-008840, Billing Period 2026-10-01 through 2026-10-31); Current Invoice Total $1,535.35.`
     - Confirm (`including 2 unknown fields`) and click **Save reviewed revision**.
5. **Search Archive & Reopen Sources (`/archive`), Restart API + PostgreSQL With OCR Disabled, & Re-Verify:**
   - Browse `/archive` (`2` cards; `SYN-WO-01` shows `Reviewed (Revision #1)` + `Newer draft exists (head Revision #2)`).
   - Search `Refrigerator Evaporator` (`Machine extraction only`) -> open `SYN-MP-01` **Page 2** readable PDF preview (`#page=2`) -> **Back to archive search**.
   - Search `CAP-45-5MFD-440V` (`Reviewed values only`) -> open `SYN-WO-01` pinned historical `Revision #1` (showing `current head is Revision #2: draft` and Page 1 provenance) -> **Back to archive search**.
   - Search `Maple Ridge Commons` (`Reviewed values only`) -> open `SYN-MP-01` pinned `Revision #1` (`2 unknown`, `None recorded (no source page coordinates)`, zero fabricated `page=` URL param).
   - Verify `Callahan` (`Reviewed values only`) and `spans multiple work orders` (`Reviewed values only`) return **`0` items** (unapproved Draft `#2` and `unknownReason` never contaminate reviewed search).
   - Stop UI, stop API, verify all worker/launcher PIDs exited, fast-restart PostgreSQL `55438`, restart API `5590` with `LocalOcr__Enabled=false`, and re-execute the `/archive` search & source-reopening checks in Edge, confirming identical saved-query digest, original/raw SHA-256s, and **unchanged `execution_attempts` count = `2`**.
