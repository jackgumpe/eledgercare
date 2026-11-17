# WP-0012 / 002: Independent CPU Review of Author Preparation (`001`) and Reviewer `v3` Guard Reconciliation

- Report path: `docs/agent-reports/eld-f4-reviewer/WP-0012/002_2026-11-17_review_eld-f4-reviewer.md`
- Sequence reservation: [INDEX.md](../../../../INDEX.md) (`WP-0012 / 002`, `eld-f4-reviewer / review`, released under coordinator authority `7af4cd0e2e8ffbcb9176fc78508b6cd601c16fc0` / `docs/kickoffs/WP-0012-eld-f4-reviewer-preparation-review.md`)
- Category: review
- Author / agent ID: `eld-f4-reviewer`
- Actual model / effort: Gemini 4 Carbon (High), high effort (continued Antigravity CLI conversation `61105d43-7706-45f2-9176-69d3256248e0`; backend checkpoint identifier not separately exposed)
- Execution environment: Windows Antigravity CLI in isolated reviewer worktree `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-f4-reviewer`; Python `3.12.10`, Node `v24.13.1`, `.NET 10.0.201`, local PostgreSQL `18.7-1` (`127.0.0.1:55439`, stopped/idle during this CPU review), Microsoft Edge `157.0.4341.60` (validated during initial preparation `7f3f8626489e898a50d275e93ee904660e97fd59`)
- Published by: `eld-f4-reviewer`
- Timestamp: 2026-11-17T15:23:00Z
- Repository / branch: `jackgumpe/eledgercare` (private) / `review/wp-0012-product-rehearsal`
- Base revision: `cb4189aced6f38b269d8a90fa362b92058852bd0` (clean merge of reviewer initial CPU preparation `7f3f8626489e898a50d275e93ee904660e97fd59` on authority `47fbc7612e4a08cf1960ad7ac01bd2843ae645e5` and bound author `/001` publication `165b2421b297bf49181c91af8d05a449ad69e9b5`; read-only coordinator dispatch authority `7af4cd0e2e8ffbcb9176fc78508b6cd601c16fc0` inspected without merging R&D branches)
- Deliverable revision: Reviewed `eld-f4-implementer` candidate `ad5202a029a7a86bea5fa3e3d97760d0a9cc673a` (evidence `32465da577237827c3ac9d8ed5ee608c8e5668cf`, canonical report `165b2421b297bf49181c91af8d05a449ad69e9b5`); frozen reviewer `/002` audit & reconciled `v3` helper `0cabb137e71454d13342148a5652a5034df018ba` (superseding initial freeze `d4bbfec29c201a1c1d3dda7881afc6029cbf88cb` after a Markdown link fix; post-freeze evidence/inventory `8eec97ce301059f81ffacb04fc0144b3c33a248e`; preserved initial reviewer preparation `7f3f8626489e898a50d275e93ee904660e97fd59` / helper `c09cf1aa8282e440e364c6020152dd257355643b`)
- Previous report: [007_2026-11-17_review_eld-f4-reviewer.md](../WP-0010/007_2026-11-17_review_eld-f4-reviewer.md) (`WP-0010 / 007`, closed prior packet)
- Related or reviewed reports: Reviewed `WP-0012 / 001` [001_2026-11-17_implementation_eld-f4-implementer.md](../../eld-f4-implementer/WP-0012/001_2026-11-17_implementation_eld-f4-implementer.md) (`165b2421b297bf49181c91af8d05a449ad69e9b5`); authority [WP-0012-0013-authority.md](../../../coordination/WP-0012-0013-authority.md); reviewer kickoff [WP-0012-eld-f4-reviewer.md](../../../kickoffs/WP-0012-eld-f4-reviewer.md) and `docs/kickoffs/WP-0012-eld-f4-reviewer-preparation-review.md` (`7af4cd0e2e8ffbcb9176fc78508b6cd601c16fc0`)
- Status: changes-requested
- Next owner: `eld-coordinator`

## Summary

This is an **independent non-author CPU review** (`WP-0012 / 002`) by `eld-f4-reviewer` (`Gemini 4 Carbon (High)`, `high` effort, same conversation `61105d43-7706-45f2-9176-69d3256248e0`) of `eld-f4-implementer`'s bound `WP-0012 / 001` demonstration rehearsal preparation (`ad5202a029a7a86bea5fa3e3d97760d0a9cc673a` / `32465da577237827c3ac9d8ed5ee608c8e5668cf` / `165b2421b297bf49181c91af8d05a449ad69e9b5`), combined with the coordinator-directed CPU reconciliation of our own future-`/004` guard helper (`v3`). Prior CLI turns for both `eld-f4-implementer` (`165b2421`) and `eld-f4-reviewer` (`7f3f8626`) ended post-publication with transient provider DNS/`resultERROR` (`OS wrapper 0`) and are never claimed as CLI `SUCCESS`.

1. **Disposition on `eld-f4-implementer` `WP-0012 / 001`: `changes-requested`.**
   - Unchanged accepted production, worker, test, and deploy trees (`73c8d3c4f0a00312e3444328331b6cbd6406e882` / `c1fed68020ae67e8b4763bc6ea5473adaa86de2b`), non-fabricated PDF review edits and unknowns (`SYN-WO-01-v1-raster300.pdf` and `SYN-MP-01-v0-clean.pdf`), preserved F4 databases, runtime role privilege denials (`13/13`), and author's `18` CPU release-contract unit tests all pass independent inspection and re-execution.
   - However, three concrete rehearsal-helper defects in [run_wp0012_rehearsal.py](../../../implementation/WP-0012/eld-f4-implementer/helpers/run_wp0012_rehearsal.py) — **deterministically reproduced on CPU** without touching author ports/DB/roots — require a bounded author helper correction before `eld-coordinator` grants the `/003` GPU lease:
     - **`F12-B1` (Partial-Startup Orphan Process & Open Log Handle Leak):** `start_api_and_ui` (`L846–906`) spawns `api_proc` (`5590`, with `LocalOcr__Enabled=true` in Phase A) and `ui_proc` (`4610`) with no internal `try/except` cleanup; when `api_proc` times out waiting to bind `5590` or `ui_proc` exits early / times out on `4610`, `start_api_and_ui` raises `RuntimeError` before returning process handles to the caller (`api_proc = None` in caller `finally:`), leaving `api_proc` alive and orphaned in the background and `api_fh` leaked open.
     - **`F12-B2` (Stop-on-Failure Bypass of Worker/Port Audits & `owner-lease-return.json`):** In `execute_live_rehearsal` (`L1211–1350`), when `cp_a.returncode != 0` (e.g., Attempt #1 fails and stops immediately as required by `WP-0012`) or `cp_b.returncode != 0`, raising `RuntimeError` jumps to `finally:`, stopping UI/API/PG but bypassing `persisted_attempts` query, `launcher_pid`/`worker_pid` termination checks, `count_ocr_worker_processes() == 0`, `assert_ports_unbound((5590, 4610, 55438))`, log secret scrubbing, and `owner-lease-return.json` emission (and `ev_out_dir.mkdir(exist_ok=True)` at `L1129` does not refuse reusing a non-empty directory).
     - **`F12-B3` (`/001` Handoff Key Rejected by `_extract_independent_review_002_sha`):** Canonical `/001` (`L64, L114`) instructs `eld-coordinator` to bind `"independent_preparation_review_002_sha"`, which `_extract_independent_review_002_sha` (`L406–413`) omits and rejects with `RehearsalGuardError`.
   - Four non-blocking `/001` prose/assertion discrepancies (`F12-D1`..`F12-D4`, including tightening Phase B `workerEnabled === false` in [drive_rehearsal_edge.mjs](../../../implementation/WP-0012/eld-f4-implementer/helpers/drive_rehearsal_edge.mjs)) are also recorded below against immutable `/001`.

2. **Reviewer Future-`/004` Guard Reconciliation (`v3`) vs. Unrun Live Readiness:**
   - Preserving all `30` initial preparation artifacts under [preparation/](../../../reviews/WP-0012/eld-f4-reviewer/preparation/README.md) (`7f3f8626489e898a50d275e93ee904660e97fd59`) untouched, we froze and verified [run_wp0012_reviewer_rehearsal_v3.py](../../../reviews/WP-0012/eld-f4-reviewer/author-001-review/helpers/run_wp0012_reviewer_rehearsal_v3.py) (`0cabb137e71454d13342148a5652a5034df018ba`, `24/24` CPU unit & subprocess tests passing) reconciling all three coordinator findings (`RG-01` exact Git release + clean `HEAD`/helper + accepted `/002` + accepted `/003` + `author_lease_return` + exact GPU UUID + expiry + hashed observations with `synthetic_test_only` isolation; `RG-02` benign WDDM desktop sharing vs. unaccounted competing model ownership aligned with `observe_ownership.ps1` at `6360ed4`; `RG-03` refusing-overwrite brand-new `/004` output destinations + atomic partial-startup cleanup).
   - **Explicit Gate Distinction:** Both author live `/003` and reviewer live `/004` remain **unrun and held**. CPU preparation and guard tests establish fail-closed preflight and cleanup behavior only; they do not establish live OCR model execution or end-to-end demonstration runtime success.

## Objective and acceptance criteria

Under [WP-0012-0013-authority.md](../../../coordination/WP-0012-0013-authority.md), [WP-0012-eld-f4-reviewer.md](../../../kickoffs/WP-0012-eld-f4-reviewer.md), and `docs/kickoffs/WP-0012-eld-f4-reviewer-preparation-review.md` (`7af4cd0e2e8ffbcb9176fc78508b6cd601c16fc0`):
1. Preserve reviewer initial preparation (`7f3f8626489e898a50d275e93ee904660e97fd59`) unchanged, normally merge exact author `/001` (`165b2421b297bf49181c91af8d05a449ad69e9b5`) without merging Root's combined R&D branch, and never touch author ports (`5590/4610/55438`), author DB (`eledgercare_demo_wp0012_author`), or author demo root.
2. Independently inspect author's actual source, `RUNBOOK.md`, and CPU evidence across `WP12-RC-01`..`07`: unchanged production/worker trees, exact release/fixture/config bindings, 2-attempt stop-on-failure semantics, partial-startup and failure-path process cleanup, non-fabricated source-grounded review edits/unknowns/newer-draft isolation/archive search/pinned history reopen, PG+API restart with `LocalOcr:Enabled=false`, preserved databases, disk/time bounds, and `/001` prose vs. executable source accuracy.
3. Reconcile coordinator findings `RG-01`..`03` on our own future-`/004` helper in a separate owned namespace (`docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/`), freeze helpers before decisive `--require-clean` CPU execution, retain any failures verbatim, verify all owned services are stopped (`5690/4710/55439` `0` listeners, `pg_ctl` exit `3`), and publish canonical `/002` in a report-only commit on `origin/review/wp-0012-product-rehearsal`.

## Change inventory

### Merge of Reviewed Author `/001` (`7f3f8626489e898a50d275e93ee904660e97fd59` -> `cb4189aced6f38b269d8a90fa362b92058852bd0`)

Merged `165b2421b297bf49181c91af8d05a449ad69e9b5` (`24` `eld-f4-implementer` `WP-0012` files; `0` production/worker/R&D/shared-ledger files) cleanly onto `7f3f8626489e898a50d275e93ee904660e97fd59`.

### Reviewer Base-to-Deliverable Diff (`cb4189aced6f38b269d8a90fa362b92058852bd0` -> `0cabb137e71454d13342148a5652a5034df018ba`)

| Action | Exact path or external resource | What changed and why | Relevant symbols |
| --- | --- | --- | --- |
| Added | `docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/AUTHOR-001-AUDIT-AND-GUARD-RECONCILIATION.md` | Detailed code-level audit of `eld-f4-implementer` `/001` (`F12-B1`..`B3`, `F12-D1`..`D4`) and reconciliation specification for future-`/004` reviewer helper `v3` (`RG-01`..`03`). | Sections `1.1`–`2` |
| Added | `docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/helpers/run_wp0012_reviewer_rehearsal_v3.py` | Reconciled future-`/004` helper (`sha256_lf == 2b27f9668310a6fd48be579e1137a67be479355aaf0966a62dc731603153f188`): exact Git release + `/002` + `/003` + `author_lease_return` + observation hash checks, WDDM desktop vs. competing model ownership classifier, refusing-overwrite output guard, and atomic partial-startup cleanup. | `validate_reviewer_release_contract`, `evaluate_gpu_and_model_ownership`, `guard_new_non_overwriting_output_targets`, `start_owned_services_atomic` |
| Added | `docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/helpers/verify_author_001_and_reviewer_v3_cpu.py` | Frozen CPU verifier running author's `18` unit tests pinned to `ad5202a0`, deterministic CPU reproductions of `F12-B1`..`B3` & `F12-D1`..`D4`, and `24` `ReviewerV3GuardReconciliationTests`. | `verify_author_001_artifacts_and_run_18_tests`, `reproduce_author_001_findings`, `ReviewerV3GuardReconciliationTests` |
| Added | `docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/helpers/build_wp0012_002_inventory.py` | Complete SHA-256 inventory, preserved-tree check (`3,615` authority + `30` reviewer prep + `24` author `/001`), link/secret scanner, and port/PostgreSQL status verifier. | `main` |
| Added | `docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/retained-failures/README.md` | Index of retained pre-freeze (`pre-freeze-01`) and post-freeze (`post-freeze-01` from initial freeze `d4bbfec29c201a1c1d3dda7881afc6029cbf88cb`) reviewer failures plus reproduced author findings. | N/A |
| Added | `docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/retained-failures/pre-freeze-01-qualification-module-dot-regex.log` | Verbatim pre-freeze `.scratch` failure where `test_13` caught dotted `python -m qualification.mapping_v2.run_eval` syntax and prompted broadening `MODEL_WORKLOAD_TOKEN_RE` to `qualification[/\\.]`. | `MODEL_WORKLOAD_TOKEN_RE` |
| Added | `docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/retained-failures/post-freeze-01-retained-readme-relative-link.log` | Verbatim failure from `build_wp0012_002_inventory.py` against `d4bbfec29c201a1c1d3dda7881afc6029cbf88cb` catching `../preparation/...` vs `../../preparation/...` in `retained-failures/README.md`. | `MD_LINK_RE` |

### Post-Freeze Evidence, Inventory, & Report Metadata (`0cabb137e71454d13342148a5652a5034df018ba` -> `8eec97ce301059f81ffacb04fc0144b3c33a248e` + Report-Only Commit)

- Post-freeze CPU evidence commit `8eec97ce301059f81ffacb04fc0144b3c33a248e` (`5` added files):
  - `docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/README.md`
  - `docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/observations/author-001-and-v3-verification.json`
  - `docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/observations/logs/verify-author-001-and-v3.log`
  - `docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/resource-return.json`
  - `docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/review-002-inventory.json`
- Report-only publication commit (subsequent commit on `review/wp-0012-product-rehearsal`):
  - `docs/agent-reports/eld-f4-reviewer/WP-0012/002_2026-11-17_review_eld-f4-reviewer.md`
- External resources:
  - Reviewer PostgreSQL cluster `.local/postgres-data` (`127.0.0.1:55439`) remained stopped (`pg_ctl status` exit `3`) throughout this turn; retained databases `eledgercare_f4_reviewer_seed_f3` (`841a3c0a...`), `eledgercare_f4_reviewer_migrated` (`0faf93dc...`), and empty ready `eledgercare_demo_wp0012_reviewer` (`0` rows across `10` tables, prepared in `7f3f8626489e898a50d275e93ee904660e97fd59`) remain intact.
  - `C:\Users\jackg\eLedgerCare-Demo\WP-0012\reviewer\runs` remains empty (`0` entries). Author ports (`5590/4610/55438`), author DB, and `C:\Users\jackg\eLedgerCare-Demo\WP-0012\author` were untouched.

## Decisions and rationale

1. **Why `F12-B1`, `F12-B2`, and `F12-B3` Require `changes-requested` Before Author `/003` GPU Lease:**
   - Under `WP-0012` authority, live execution runs on a shared workstation under a strict finite 2-attempt ceiling and serialized GPU ownership. If Angular `ng serve` fails or times out during Phase A startup (`F12-B1`), leaking an alive `dotnet ELedgerCare.Api.dll` supervisor configured with `LocalOcr__Enabled=true` and `LocalOcr__LeasedGpuUuid=GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d` directly violates owned-process hygiene. Similarly, if Attempt #1 fails (`F12-B2`), the stop-on-failure path is the exact path where worker-process exit verification, port-unbound checks, log credential scrubbing, and `owner-lease-return.json` emission are most needed. Finally, `F12-B3` would cause `--execute-live` to fail closed at contract parse time if `eld-coordinator` uses the key name `"independent_preparation_review_002_sha"` requested in `/001` (`L64, L114`). All three fixes are small, localized edits inside `run_wp0012_rehearsal.py` (plus a 2-line `workerEnabled === false` assertion for `F12-D4` in `drive_rehearsal_edge.mjs`), requiring zero production changes.
2. **Recorded `/001` Prose Discrepancies (`F12-D1`..`F12-D3`):**
   - Because published `/001` (`165b2421b297bf49181c91af8d05a449ad69e9b5`) is immutable, we recorded the shorthand flag/mode mismatches (`--release` vs `--release-commit`/`--release-path`; `live-phase1`/`live-phase2` vs `live-phase-a`/`live-phase-b-reopen`) and overstated validation prose (`git merge-base --is-ancestor` on `/002` SHA vs actual `git cat-file -e <sha>^{commit}`; Step `04` dirty-worktree/disk/symlink unit-test descriptions; `archive_document_projections` table name) in [AUTHOR-001-AUDIT-AND-GUARD-RECONCILIATION.md](../../../reviews/WP-0012/eld-f4-reviewer/author-001-review/AUTHOR-001-AUDIT-AND-GUARD-RECONCILIATION.md) (`Section 1.3`). Executable `RUNBOOK.md` (`L32, L49, L51`) already documents the accurate CLI flags and Edge modes.
3. **Reconciling `RG-01`..`03` Without Touching Initial Preparation (`7f3f8626`):**
   - Placing `run_wp0012_reviewer_rehearsal_v3.py` in `author-001-review/helpers/` preserves `c09cf1aa` / `7f3f8626` (`preparation/`) 100% immutable while reusing unchanged `drive_wp0012_edge_workflow.mjs` (`sha256_lf == c8cd73a9...`, bound by committed Git blob identity at runtime) and requiring brand-new non-existing `/004` output destinations (`RG-03`).
   - For `RG-02`, `evaluate_gpu_and_model_ownership` follows `observe_ownership.ps1` (`6360ed4`): Windows desktop/WDDM processes (`dwm.exe`, `msedge.exe`, `explorer.exe`, and pre-lease accounted non-model PIDs) are recorded under `wddm_desktop_sharing_entries` with `"hardware_exclusivity_claimed": false`, while any unaccounted Python OCR/qualification worker, active `ollama ps` runner, local LLM server (`ollama`, `llama-server`, `vllm`, `lmstudio`, `koboldcpp`), or unknown CUDA binary raises `CompetingModelOwnershipError`.

## Verification

### Executed CPU Checks

| Check / exact command or tool operation | Environment and revision | Actual result | Evidence location |
| --- | --- | --- | --- |
| Merge & preservation check (`git merge --no-ff 165b2421b297bf49181c91af8d05a449ad69e9b5`; `git diff` against `47fbc761` & `7f3f8626`) | Reviewer worktree, `cb4189aced6f38b269d8a90fa362b92058852bd0` | Clean merge (`24` author `/001` files added); `3,615` authority-base paths and `30` initial reviewer `preparation/` paths 100% unchanged. | [review-002-inventory.json](../../../reviews/WP-0012/eld-f4-reviewer/author-001-review/review-002-inventory.json) |
| Decisive post-freeze CPU verification: `python -B docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/helpers/verify_author_001_and_reviewer_v3_cpu.py --require-clean` | Clean `HEAD` `0cabb137e71454d13342148a5652a5034df018ba` (CPU-only, `0` services/GPU/author resources started) | Exit `0`: verified `23` author SHA-256s, `86` links, `node --check`, `0` ML/CUDA AST imports; passed `18/18` author `Wp0012PreparationGuardTests` pinned to `ad5202a0`; deterministically reproduced `F12-B1` (Cases A & B), `F12-B2`, `F12-B3`, and `F12-D1`..`D4`; passed `24/24` `ReviewerV3GuardReconciliationTests` (`RG-01`..`03` + atomic partial-startup cleanup). | [author-001-and-v3-verification.json](../../../reviews/WP-0012/eld-f4-reviewer/author-001-review/observations/author-001-and-v3-verification.json), [verify-author-001-and-v3.log](../../../reviews/WP-0012/eld-f4-reviewer/author-001-review/observations/logs/verify-author-001-and-v3.log) |
| Inventory, link, secret, & service-hygiene check: `python -B docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/helpers/build_wp0012_002_inventory.py --frozen-sha 0cabb137e71454d13342148a5652a5034df018ba` (2 passes) | `0cabb137e71454d13342148a5652a5034df018ba` -> `8eec97ce301059f81ffacb04fc0144b3c33a248e` | Exit `0` (`INV_PASS=True`): `11` review files + self manifest verified (`sha256_raw == sha256_lf`), `0` broken links, `0` leaked secrets, `5690/4710/55439` all `0` listeners, `pg_ctl status` exit `3`, `runs/` `0` entries. | [resource-return.json](../../../reviews/WP-0012/eld-f4-reviewer/author-001-review/resource-return.json), [review-002-inventory.json](../../../reviews/WP-0012/eld-f4-reviewer/author-001-review/review-002-inventory.json) |
| Retained reviewer Edge + PostgreSQL CPU preflight from initial `WP-0012` preparation (re-verified untouched, not unnecessarily re-run) | `c09cf1aa8282e440e364c6020152dd257355643b` / `7f3f8626489e898a50d275e93ee904660e97fd59` | `32/32` CPU assertions passed (`5690`/`4710`/`55439`, Edge `157.0.4341.60` `503 extraction_disabled` guard, PG+API restart, empty ready `eledgercare_demo_wp0012_reviewer`). | [preparation/README.md](../../../reviews/WP-0012/eld-f4-reviewer/preparation/README.md), [preparation-inventory.json](../../../reviews/WP-0012/eld-f4-reviewer/preparation/preparation-inventory.json) |

### Checks Not Run and Why

- **Live Local OCR / GPU Rehearsal (`eld-f4-implementer` `/003` and `eld-f4-reviewer` `/004`):** Not run — unreleased in this CPU review turn; requires author correction of `F12-B1`..`B3` / `F12-D4`, accepted preparation review, and separate sequential coordinator sole GPU leases.
- **Unchanged Broad `.NET` / Playwright / Angular Product Suites:** Not re-run — `src/`, `web/`, `tests/`, `deploy/`, and `workers/local_ocr/` are bit-for-bit identical to accepted `73c8d3c4f0a00312e3444328331b6cbd6406e882` (`c1fed68020ae67e8b4763bc6ea5473adaa86de2b`), attributed to `WP-0010 / 004` and `WP-0010 / 007`.

## Review map

- **Dossier Index & Full Technical Audit:** [author-001-review/README.md](../../../reviews/WP-0012/eld-f4-reviewer/author-001-review/README.md) and [AUTHOR-001-AUDIT-AND-GUARD-RECONCILIATION.md](../../../reviews/WP-0012/eld-f4-reviewer/author-001-review/AUTHOR-001-AUDIT-AND-GUARD-RECONCILIATION.md)
- **Reviewed Author `/001` Artifacts (`ad5202a0` / `32465da5` / `165b2421`):**
  - [001_2026-11-17_implementation_eld-f4-implementer.md](../../eld-f4-implementer/WP-0012/001_2026-11-17_implementation_eld-f4-implementer.md)
  - [RUNBOOK.md](../../../implementation/WP-0012/eld-f4-implementer/RUNBOOK.md)
  - [run_wp0012_rehearsal.py](../../../implementation/WP-0012/eld-f4-implementer/helpers/run_wp0012_rehearsal.py) (`start_api_and_ui` `L846–906`, `execute_live_rehearsal` `L1129` & `L1211–1350`, `_extract_independent_review_002_sha` `L406–413`)
  - [drive_rehearsal_edge.mjs](../../../implementation/WP-0012/eld-f4-implementer/helpers/drive_rehearsal_edge.mjs) (`live-phase-a` `L470–640`, `live-phase-b-reopen` `L642–695`)
  - [validate_wp0012_preparation_cpu.py](../../../implementation/WP-0012/eld-f4-implementer/helpers/validate_wp0012_preparation_cpu.py) and [inventory.json](../../../implementation/WP-0012/eld-f4-implementer/inventory.json)
- **Frozen Reviewer `v3` Helper, CPU Verifier, & Retained Failures (`0cabb137e71454d13342148a5652a5034df018ba` / `8eec97ce301059f81ffacb04fc0144b3c33a248e`):**
  - [run_wp0012_reviewer_rehearsal_v3.py](../../../reviews/WP-0012/eld-f4-reviewer/author-001-review/helpers/run_wp0012_reviewer_rehearsal_v3.py)
  - [verify_author_001_and_reviewer_v3_cpu.py](../../../reviews/WP-0012/eld-f4-reviewer/author-001-review/helpers/verify_author_001_and_reviewer_v3_cpu.py)
  - [build_wp0012_002_inventory.py](../../../reviews/WP-0012/eld-f4-reviewer/author-001-review/helpers/build_wp0012_002_inventory.py)
  - [retained-failures/README.md](../../../reviews/WP-0012/eld-f4-reviewer/author-001-review/retained-failures/README.md)

## Risks, disagreements, and unfinished work

- **Retained Reviewer Failures (`2`, both resolved before decisive `v2` verification):**
  1. `pre-freeze-01`: `.scratch` dry-run `test_13` caught `python -m qualification.mapping_v2.run_eval` dotted module syntax not matching `qualification[/\\]`; widened to `qualification[/\\.]` in `v3` before freeze.
  2. `post-freeze-01`: `build_wp0012_002_inventory.py` caught `../preparation/...` vs `../../preparation/...` in `author-001-review/retained-failures/README.md` after `d4bbfec29c201a1c1d3dda7881afc6029cbf88cb`; fixed in forward `v2` freeze `0cabb137e71454d13342148a5652a5034df018ba` (`0` `.py` helper changes) and re-verified cleanly.
- **Bounded Author Helper Correction Required (`F12-B1`..`B3`, `F12-D4`):** Author `eld-f4-implementer` must add internal `try/except` child-process cleanup in `start_api_and_ui`, ensure `execute_live_rehearsal`'s failure path executes worker/port exit checks, log secret scrubbing, non-empty output refusal, and `owner-lease-return.json` emission, accept `"independent_preparation_review_002_sha"` in `_extract_independent_review_002_sha`, and assert `workerEnabled === false` in `live-phase-b-reopen`.
- **Unfinished Packet Gates:** Author corrected helper verification, author live `/003` (2-attempt ceiling under sole GPU lease), reviewer live `/004` (2-attempt ceiling under separate sole GPU lease using `run_wp0012_reviewer_rehearsal_v3.py` and brand-new output paths), and coordinator final `/005` disposition remain ahead. Known Q0 qualification boundary (Python library offline env settings vs. unverified OS-level network egress denial) remains explicit.

## Handoff

- **Next owner:** `eld-coordinator`
- **Recommended next action:** Route bounded CPU helper corrections (`F12-B1`, `F12-B2`, `F12-B3`, and `F12-D4`) in `docs/implementation/WP-0012/eld-f4-implementer/helpers/` to `eld-f4-implementer` before binding any `/003` live GPU lease; once verified, bind sequential sole GPU leases for author `/003` and then independent reviewer `/004` (`run_wp0012_reviewer_rehearsal_v3.py --mode live-leased-rehearsal` with brand-new output destinations).
- **Branch & Revisions:**
  - Branch: `review/wp-0012-product-rehearsal`
  - Merged base SHA: `cb4189aced6f38b269d8a90fa362b92058852bd0`
  - Reviewed author `/001` deliverable / evidence / publication SHAs: `ad5202a029a7a86bea5fa3e3d97760d0a9cc673a` / `32465da577237827c3ac9d8ed5ee608c8e5668cf` / `165b2421b297bf49181c91af8d05a449ad69e9b5`
  - Frozen reviewer `/002` deliverable & `v3` helper SHA: `0cabb137e71454d13342148a5652a5034df018ba` (initial freeze `d4bbfec29c201a1c1d3dda7881afc6029cbf88cb`)
  - Post-freeze `/002` evidence & inventory SHA: `8eec97ce301059f81ffacb04fc0144b3c33a248e`
  - Canonical report path: `docs/agent-reports/eld-f4-reviewer/WP-0012/002_2026-11-17_review_eld-f4-reviewer.md` (report-only publication SHA provided in the handoff message upon remote verification; remote push confirmation is pending at the moment this file is committed).
