# WP-0012 Independent Reviewer Preparation, `/002` Criteria, and `/004` Rehearsal Runbook

- **Reviewer / Session Identity:** `eld-f4-reviewer` — continued independent Google DeepMind Gemini 4 Carbon (High) session in Antigravity CLI conversation `61105d43-7706-45f2-9176-69d3256248e0` (`effort: high`; backend checkpoint identifier not separately exposed; reporting recipient: `eld-coordinator`).
- **Historical `WP-0010` Closure & Prior Turn Disclosure:** Prior `WP-0010` work is closed and integrated into accepted base `73c8d3c4f0a00312e3444328331b6cbd6406e882` ([WP-0012-0013-authority.md](../../../../coordination/WP-0012-0013-authority.md)). Earlier `WP-0010` CLI invocations ended after immutable Git publication with transient provider DNS/`resultERROR` (`OS wrapper 0`) and are never claimed as CLI `SUCCESS`. Zero `WP-0010` reports, dossiers, branches (`review/wp-0010-f4`), or retained databases (`eledgercare_f4_reviewer_seed_f3`, `eledgercare_f4_reviewer_migrated`) are modified.
- **Owned Branch, Worktree, & Authority:** `review/wp-0012-product-rehearsal` in `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-f4-reviewer`, bound at [WP-0012-eld-f4-reviewer.md](../../../../kickoffs/WP-0012-eld-f4-reviewer.md) (`47fbc7612e4a08cf1960ad7ac01bd2843ae645e5`).
- **Gate Status:**
  - **Canonical `WP-0012 / 002` (`002_2026-11-17_review_eld-f4-reviewer.md`):** **HELD** until `eld-coordinator` binds exact published `eld-f4-implementer` `WP-0012 / 001` preparation candidate and report.
  - **Canonical `WP-0012 / 004` (`004_2026-11-17_review_eld-f4-reviewer.md`):** **HELD** until `eld-f4-implementer` publishes `WP-0012 / 003`, returns its GPU lease, and `eld-coordinator` issues a separate sole GPU lease to `eld-f4-reviewer`.
  - **Current Phase Scope:** **CPU-only preparation and guard validation.** Zero model/venv Python execution, zero `torch`/`transformers` imports, zero GPU queries or inference, and zero SQL-seeded extraction results.

---

## 1. Accepted Product Source & Attributed Suite Baseline (`73c8d3c4f0a00312e3444328331b6cbd6406e882`)

All production, worker, test, and deployment trees at `47fbc7612e4a08cf1960ad7ac01bd2843ae645e5` are bit-for-bit identical to accepted product base `73c8d3c4f0a00312e3444328331b6cbd6406e882`:

| Tree / Artifact | Git Tree / Blob OID or SHA-256 | Attribution |
| --- | --- | --- |
| [src](../../../../../src) | `9760402fa88dcb343c28b14ad4de1bcb2fbafb2e` | Accepted in [004_2026-11-17_review_eld-f4-reviewer.md](../../../../agent-reports/eld-f4-reviewer/WP-0010/004_2026-11-17_review_eld-f4-reviewer.md) (`95/95` .NET + PG `18.7` tests) |
| [web](../../../../../web) | `50fbbee1f58aace4e6ec36bd64203146d23aa96f` | Accepted in [007_2026-11-17_review_eld-f4-reviewer.md](../../../../agent-reports/eld-f4-reviewer/WP-0010/007_2026-11-17_review_eld-f4-reviewer.md) (`16/16` Edge E2E + `6/6` navigation probes) |
| [tests](../../../../../tests) | `25c21310699086acb818549b2a4c0b99469208f1` | Attributed to `WP-0010 / 004` & `/007` (not gratuitously rerun) |
| [deploy](../../../../../deploy) | `86e0c73d4b4c07bbdf92ebcd65a0903fc9c039f1` | Attributed to `WP-0010 / 004` |
| [ELedgerCare.slnx](../../../../../ELedgerCare.slnx) | `c00c2bc5ef46019fb4452fdf0bba7ca2271fc976` | Attributed to `WP-0010 / 004` |
| [workers](../../../../../workers) | `9b548ddcc73cfba8e7683d132840b08afa5a67a3` | Worker source SHA-256 `c1c324c36e27f57c3c4ac4a1462984fbe586ad43ab82af3a2883bb7eac4c0d54` (`9/9` worker CPU unit tests attributed) |
| [model-files.json](../../../../../workers/local_ocr/manifests/model-files.json) | SHA-256 `0df07bc60abf6937c917040bced32afabd7e4d11bafc0bd99902abca610a81be` | `baidu/Unlimited-OCR-2` @ `0480966938291445591f69f08a13b041c073a96a` (`18` runtime objects, `6,699,195,181` B + `README.md` `14,107` B) |
| [dependency-lock.json](../../../../../workers/local_ocr/manifests/dependency-lock.json) | SHA-256 `582071bf20eaca1836c3d1cef21d31cbdaa1e1407184033a918a40612c128111` | `32` locked wheels (`pypdfium2==5.15.2`, `torch==2.13.0+cu130`, `torchvision-local-sha256-TOFU`) |
| [SYN-WO-01-v1-raster300.pdf](../../../../../tests/fixtures/SYN-WO-01-v1-raster300.pdf) | SHA-256 `47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd` | `1` page (`372,258` B); worker config SHA-256 `579aad63a9893a58466baf005ea63f87e92540d4c1f71f6b3c399e8b1e6b35ff` |
| [SYN-MP-01-v0-clean.pdf](../../../../../tests/fixtures/SYN-MP-01-v0-clean.pdf) | SHA-256 `15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3` | `3` pages (`8,422` B); worker config SHA-256 `ac90459ca4011b5859cfdd0b224d5ea247489b7c01775118736df7c1c9819e86` |

---

## 2. Independent `/002` Review Criteria for `eld-f4-implementer` `WP-0012 / 001`

When `eld-coordinator` binds exact `eld-f4-implementer` `/001`, independent review `/002` will verify and reproduce CPU validation against these exact criteria:

1. **Unchanged Production Source (`WP12-RC-01`):** `src`, `web`, `tests`, `deploy`, `ELedgerCare.slnx`, `workers`, `research`, `evaluation`, and `qualification` match `73c8d3c4f0a00312e3444328331b6cbd6406e882` with zero production edits unless narrowly released by `eld-coordinator`.
2. **Strict Two-Attempt Live Ceiling & Zero Seed Substitution (`WP12-RC-02`):**
   - Live driver permits **at most `2` extraction requests** (`1` for `SYN-WO-01-v1-raster300.pdf` + `1` for `SYN-MP-01-v0-clean.pdf`; `4` pages total).
   - **Zero** SQL-seeded `extraction_results`, **zero** model warmups, and **zero** automatic or hidden retries.
   - Fails closed before starting any service or model worker unless bound to an explicit coordinator sole-lease JSON (`owner_agent`, `packet_id == "WP-0012"`, `gpu_uuid`, `max_attempts <= 2`, clean frozen `HEAD`).
3. **Immediate Failure Stop, Preservation, & Lease Return (`WP12-RC-03`):** Any upload, extraction, browser, or database failure immediately halts remaining attempts, preserves logs/diagnostics, stops owned services (`5290/4310/55435` for author), and prepares lease-return evidence without retrying.
4. **Genuine Process, Guard, & Read-Only Q0 Binding (`WP12-RC-04`):** Records actual OS `PID` + `StartTimeUtc`/`create_filetime` + exit code for PostgreSQL, API, UI, supervisor, launcher, and worker processes; keeps `C:\Users\jackg\eLedgerCare-Q0\WP-0005` strictly read-only and routes all per-attempt writes to the owner's `C:\Users\jackg\eLedgerCare-Demo\WP-0012\<role>` directory.
5. **Grounded Human Corrections, Explicit `unknown`, & Draft Separation (`WP12-RC-05`):**
   - All human-reviewed values and `unknown` reasons come directly from comparing against the real `SYN-WO-01-v1-raster300.pdf` and `SYN-MP-01-v0-clean.pdf` pages — **zero fabricated synthetic search tokens**.
   - Demonstrates `accepted`, `edited`, and `unknown` decisions, plus a saved `reviewed` revision followed by a newer unapproved `draft` revision on one document so `latestReviewed` vs. `currentReviewHead` (`Newer draft exists`) and draft non-leakage into `source=reviewed` search are proven honestly.
6. **Source `#page` & Pinned History Navigation + Restart Durability (`WP12-RC-06`):**
   - Exercises `/archive` across `machine`, `reviewed`, and `all`; opens a multi-page source PDF target (`#page=2` on `SYN-MP-01`) and a pinned historical reviewed revision (`/review/revisions/1`) without clobbering the newer draft; returns to preserved archive search context.
   - Restarts API and PostgreSQL, reopens with `LocalOcr:Enabled=false`, repeats `/archive` + PDF + review-history verification in real Edge, and verifies `execution_attempts` count remains unchanged (`== 2`) with `0` new worker processes or run directories.
7. **CPU-Prep Honesty, Secret Hygiene, & Resource Return (`WP12-RC-07`):** Author `/001` performs zero model/GPU execution, leaks zero `.local/secrets/pg-local.json` values, preserves prior F4 databases, stops all owned services (`0` listeners), and freezes helpers before CPU validation.

---

## 3. Grounded Source Mapping for Reviewer `/004` Live Rehearsal (Zero Fabricated Tokens)

Visual inspection of [SYN-WO-01-v1-raster300.pdf](../../../../../tests/fixtures/SYN-WO-01-v1-raster300.pdf) (`1` page) and [SYN-MP-01-v0-clean.pdf](../../../../../tests/fixtures/SYN-MP-01-v0-clean.pdf) (`3` pages) establishes 100% source-grounded review actions and archive queries:

### A. Document 1 — `SYN-WO-01-v1-raster300.pdf` (`1` page corrective maintenance work order)
- **Grounded `Reviewed Revision #1` (`status = reviewed`):**
  - `work_order_id`: `accepted` (or grounded `edited` if not suggested) = `WO-004192` (Page 1)
  - `property_name`: `accepted` = `Cedar Hollow Apartments` (Page 1)
  - `building_unit`: `accepted` = `Bldg B - Unit 204` (Page 1)
  - `requested_date`: `accepted` = `2026-10-16` (Page 1)
  - `issue_and_resolution`: `edited` (retaining Page 1 block provenance) = `"Air handler fan running continuously with warm supply air at 79 F setpoint. Inspected condensing unit CHP-B204: dual run capacitor measured 18.2 uF on 45 uF herm leg and contactor points pitted. Replaced capacitor (SKU CAP-45-5MFD-440V) and 2-pole contactor from van stock; verified 19.4 F delta-T across evaporator coil."`
    - *Source grounding:* Row 1 of `INTERNAL MAINTENANCE STOCK PARTS USED` on Page 1 of `SYN-WO-01-v1-raster300.pdf` prints verbatim SKU **`CAP-45-5MFD-440V`** (`45/5 uF`), which raw raster OCR misreads as `CAP-45-SMFD-440V` and omits from the standalone summary paragraph.
- **Grounded Newer `Draft Revision #2` (`status = draft`, unapproved head):**
  - Appends the verbatim sign-off printed at the bottom of Page 1 (`Completed Timestamp: 2026-10-16 10:45`, `Supervisor Review: D. Callahan`) to `issue_and_resolution` and saves as **`draft`**.
  - *Archive proof:* `Callahan` is absent from `Reviewed Revision #1` (so `q=Callahan&source=reviewed` returns **`0` items**, proving Draft `#2` never leaks into `reviewed` search), while `q=Callahan&source=machine` matches Page 1 machine text and displays `[Reviewed (Revision #1)]` + `[Newer draft exists (head Revision #2)]`.

### B. Document 2 — `SYN-MP-01-v0-clean.pdf` (`3` pages consolidated monthly maintenance statement)
- Because `SYN-MP-01-v0-clean.pdf` is a 3-page consolidated invoice (`INV-008810` / `CTR-008840`) spanning 11 work-order line items across Buildings A, B, C & Clubhouse, all five `work-order-suggestions/1` single-work-order candidates are `missing`.
- **Grounded `Reviewed Revision #1` (`status = reviewed`, `2 edited` + `3 unknown`):**
  - `work_order_id`: **`unknown`** — reason: `"Consolidated monthly statement INV-008810 lists multiple work orders across Pages 1-3 (WO-004701 through WO-004759); no single Work Order ID applies."`
  - `property_name`: **`edited`** = `"Maple Ridge Commons Asset Operations"` (printed verbatim under `BILL TO` on Page 1).
  - `building_unit`: **`unknown`** — reason: `"Statement covers Buildings A, B, C & Clubhouse across multiple units; no single Building / Unit applies."`
  - `requested_date`: **`unknown`** — reason: `"Shows Billing Period 2026-10-01 through 2026-10-31 and Statement Date 2026-10-31 rather than a single work-order Requested Date."`
  - `issue_and_resolution`: **`edited`** = `"Consolidated monthly maintenance statement INV-008810 under Master Service Agreement CTR-008840 for Billing Period 2026-10-01 through 2026-10-31; Total Amount Due $1,535.35 across Pages 1-3."` (printed verbatim across Pages 1 & 3; note `2026-10-01` corrects OCR's `2025-10-01` misread on Page 1).
  - *Archive & navigation proof:*
    - `q=WO-004724&source=machine` matches `SYN-MP-01` Page 2 (`L09 | WO-004724 | Unit 11A - Refrigerator Evaporator Fan Motor`), whereas `q=WO-004724&source=reviewed` returns **`0` items** (unknown reasons are never indexed as reviewed values). Clicking `Open source PDF Page 2 & result` opens `/documents/<mpDocId>?page=2&returnQ=WO-004724&returnSource=machine` with readable PDF `#page=2`.
    - `q=2026-10-01&source=reviewed` matches `SYN-MP-01` via `Reviewed Revision #1`.

---

## 4. Repeatable Reviewer Runbook (CPU Preparation vs. Held `/004` Live Rehearsal)

### Phase A — CPU-Only Preparation & Guard Validation (Executed Now, Zero GPU/Model)
```powershell
Set-Location 'C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-f4-reviewer'
python -B docs/reviews/WP-0012/eld-f4-reviewer/preparation/helpers/run_wp0012_reviewer_rehearsal.py `
  --mode cpu-prep-validation `
  --require-clean `
  --summary-output docs/reviews/WP-0012/eld-f4-reviewer/preparation/observations/cpu-prep-validation-summary.json `
  --q0-check-output docs/reviews/WP-0012/eld-f4-reviewer/preparation/observations/q0-readonly-manifest-check.json `
  --resource-return-output docs/reviews/WP-0012/eld-f4-reviewer/preparation/resource-return.json `
  --logs-dir docs/reviews/WP-0012/eld-f4-reviewer/preparation/observations/logs `
  --screenshots-dir docs/reviews/WP-0012/eld-f4-reviewer/preparation/observations/screenshots
```
1. Verifies clean Git `HEAD`, unchanged product/worker/test/deploy trees, pure-stdlib Q0 model/notice/lock manifests (`0` venv/model processes), empty non-reparse `C:\Users\jackg\eLedgerCare-Demo\WP-0012\reviewer\runs`, and `5 / 5` fail-closed lease-refusal self-tests.
2. Starts owned PostgreSQL `18.7` (`127.0.0.1:55439`), confirms historical `eledgercare_f4_reviewer_seed_f3` (`841a3c0a...`) and `eledgercare_f4_reviewer_migrated` (`0faf93dc...`) remain bit-for-bit intact, and prepares empty `eledgercare_demo_wp0012_reviewer` (`4` migrations + `eledgercare_app` least-privilege matrix + SQL mutation denials).
3. Exercises real Microsoft Edge (`msedge`, `127.0.0.1:4710 -> 127.0.0.1:5690`) with `LocalOcr:Enabled=false` on disposable `eledgercare_demo_wp0012_reviewer_cpupreflight` (browser upload -> `extraction-unavailable` disabled guard -> `503 extraction_disabled` -> PG+API restart -> reopen with `0` attempts -> drop scratch DB) and GET-only readiness check on empty `eledgercare_demo_wp0012_reviewer` (`0` rows across all `10` tables, `fencing_seq = (1, false)`).
4. Stops UI `4710`, API `5690`, and PG `55439` and verifies `0` listeners across all 3 owned ports.

### Phase B — Held `/004` Live Demonstration Rehearsal (Execute ONLY After Author `/003` + Coordinator Sole Lease)
```powershell
Set-Location 'C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-f4-reviewer'
python -B docs/reviews/WP-0012/eld-f4-reviewer/preparation/helpers/run_wp0012_reviewer_rehearsal.py `
  --mode live-leased-rehearsal `
  --require-clean `
  --lease-json <coordinator-bound-reviewer-lease.json> `
  --summary-output docs/reviews/WP-0012/eld-f4-reviewer/live-rehearsal/observations/live-rehearsal-summary.json `
  --q0-check-output docs/reviews/WP-0012/eld-f4-reviewer/live-rehearsal/observations/q0-post-rehearsal-check.json `
  --resource-return-output docs/reviews/WP-0012/eld-f4-reviewer/live-rehearsal/resource-return.json `
  --logs-dir docs/reviews/WP-0012/eld-f4-reviewer/live-rehearsal/observations/logs `
  --screenshots-dir docs/reviews/WP-0012/eld-f4-reviewer/live-rehearsal/observations/screenshots
```
1. Validates coordinator sole-lease JSON (`owner_agent == "eld-f4-reviewer"`, `packet_id == "WP-0012"`, `max_attempts == 2`, `gpu_uuid`), observes baseline `nvidia-smi` idle compute state, and verifies `eledgercare_demo_wp0012_reviewer` has `0` rows before starting `ELedgerCare.Api` (`LocalOcr:Enabled=true`, `LeasedGpuUuid=<gpu_uuid>`) and Angular UI (`4710`).
2. Runs [drive_wp0012_edge_workflow.mjs](helpers/drive_wp0012_edge_workflow.mjs) `--mode live-phase1-leased` in real Microsoft Edge: fresh browser upload + 1 extraction attempt on `SYN-WO-01-v1-raster300.pdf` + grounded `Reviewed #1` + newer `Draft #2`; fresh browser upload + 1 extraction attempt on `SYN-MP-01-v0-clean.pdf` + grounded `Reviewed #1` (`2 edited`, `3 unknown`); `/archive` retrieval across `machine`/`reviewed`/`all`, `#page=2` PDF preview reopen, and pinned `/review/revisions/1` reopen. Halts immediately on any error with `0` retries.
3. Stops API `5690` and fast-restarts PostgreSQL `55439`, restarts API `5690` with **`LocalOcr:Enabled=false`**, runs [drive_wp0012_edge_workflow.mjs](helpers/drive_wp0012_edge_workflow.mjs) `--mode live-phase2-post-restart`, verifies `execution_attempts == 2` and `0` new worker runs, stops all owned services (`4710/5690/55439`), re-verifies read-only Q0 immutability + `0` active GPU compute processes, and writes lease-return receipt.
