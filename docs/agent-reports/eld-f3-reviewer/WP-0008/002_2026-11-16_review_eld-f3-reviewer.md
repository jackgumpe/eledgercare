# WP-0008 / 002: Independent review of F3 work-order review/correction design and worker offline-network README wording

- Report path: `docs/agent-reports/eld-f3-reviewer/WP-0008/002_2026-11-16_review_eld-f3-reviewer.md`
- Sequence reservation: `WP-0008 /002` in [INDEX.md](../../../../INDEX.md) at `22b88bc32d053231678aef88e6b7f76d3e61910a` / `c5b5db3af96abf155c806082583b8a92c687f54d`; bound kickoff [WP-0008-eld-f3-reviewer-design.md](../../../kickoffs/WP-0008-eld-f3-reviewer-design.md) (`9663964fe4d8e6a8a0c7398ea07dbc524abdaa11`)
- Category: review
- Author / agent ID: `eld-f3-reviewer`
- Actual model / effort: Gemini 4 Carbon (High), high effort (fresh independent Antigravity CLI conversation `025f1605-d7e3-4fea-8255-907c2b07b55f`; backend checkpoint identifier not separately exposed)
- Execution environment: CLI (`Antigravity CLI` on Windows x64 PowerShell; conversation `025f1605-d7e3-4fea-8255-907c2b07b55f`; Git `2.55.0.windows.1`; CPython `3.12.10`; `.NET SDK 10.0.403`; Node `v24.18.0`)
- Published by: `eld-f3-reviewer`
- Timestamp: 2026-11-16T19:44:00Z
- Repository / branch: private `https://github.com/jackgumpe/eledgercare` / `review/wp-0008-f3` (owned worktree `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-f3-reviewer`)
- Base revision: `30bb49ed56c32bda61a6907d49bd183e7b292268` (clean dispatch `HEAD`; packet base `5e1241d6d365d664f12619d415f48ec3d3b7ddca`; authority `22b88bc32d053231678aef88e6b7f76d3e61910a`)
- Deliverable revision: `367b9fae0c0578d27a86c858b4a3f07c1d2ea284` (frozen review dossier and verification helper; post-freeze verification evidence `81b245481c6c46bb8c8e38f8e0f4a108ddf81f69`); reviewed root design candidate `c5b5db3af96abf155c806082583b8a92c687f54d` (coordinator `/001` publication `30bb49ed56c32bda61a6907d49bd183e7b292268`)
- Previous report: none (first report in fresh independent session `025f1605-d7e3-4fea-8255-907c2b07b55f`; prior accepted F2 review [WP-0006 / 004](../../eld-next-reviewer/WP-0006/004_2026-11-16_review_eld-next-reviewer.md) at `c854a1d4c306c3b10d78df42a1a2552a06bb4a98` referenced as input only)
- Related or reviewed reports: [WP-0008 / 001](../../eld-coordinator/WP-0008/001_2026-11-16_design_eld-coordinator.md) (`30bb49ed56c32bda61a6907d49bd183e7b292268`); [WP-0006 / 004](../../eld-next-reviewer/WP-0006/004_2026-11-16_review_eld-next-reviewer.md) (`c854a1d4c306c3b10d78df42a1a2552a06bb4a98`); [WP-0006 / 005](../../eld-coordinator/WP-0006/005_2026-11-16_verification_eld-coordinator.md) (`43140c06fd734ec41a43b8ee219950386be55359`)
- Status: accepted
- Next owner: `eld-coordinator` (bind and dispatch `WP-0008 /003` `eld-f3-implementer` release incorporating `F3-KR-01` and carrying `F3-BIC-01`..`06` into `/003`–`/004`)

## Summary

Independent non-author design and README review (`WP-0008 / 002`) **ACCEPTS** frozen root candidate **`c5b5db3af96abf155c806082583b8a92c687f54d`** ([F3-review-correction.md](../../../design/F3-review-correction.md), blob `4d6b9770599087534ed11aadbec6510ed10c77c1`; [workers/local_ocr/README.md](../../../../workers/local_ocr/README.md), blob `83ed6624f95c48bfbae4c466201774824f63ef5e`) and coordinator report [WP-0008 / 001](../../eld-coordinator/WP-0008/001_2026-11-16_design_eld-coordinator.md) (`30bb49ed56c32bda61a6907d49bd183e7b292268`).

- **Zero blocking design or documentation defects** were found against accepted F1/F2 product source (`8a73b7a5dab51e3ccf803aceedded4929529dd35`).
- One `/003` kickoff path binding (`F3-KR-01`: `deploy/dev/**` ownership for runtime grants and port-parameterized smoke scripts) and six source-pinned implementation checkpoints (`F3-BIC-01`..`06`, documented in [design/README.md](../../../reviews/WP-0008/eld-f3-reviewer/design/README.md)) are recorded for `WP-0008 /003`–`/004` without altering the reviewed contract.
- **Independence and Non-Access Attestation:** Fresh conversation `025f1605-d7e3-4fea-8255-907c2b07b55f` authored zero files in `c5b5db3a...` or prior packets, modified no product/shared-routing files, started no services or GPU/model processes, made no network downloads, and accessed **zero** `WP-0009` sealed evaluation paths.

## Objective and acceptance criteria

1. Verify Git lineage (`5e1241d6...` -> `22b88bc3...` -> `c5b5db3a...` -> `30bb49ed...`), exact 11-path candidate scope, and byte-exact preservation of accepted product, worker, corpus, qualification, and historical report trees.
2. Audit [F3-review-correction.md](../../../design/F3-review-correction.md) against actual F2 source across five-field `work-order-suggestions/1` extraction, immutable machine/raw vs. human revision state, optimistic concurrency and idempotent replay ordering, forward migration and least-privilege PostgreSQL grants, native PDF `/preview` and readable Edge requirements, in-memory uncertain-save handling, and attributed genuine F2 seed reuse without GPU execution.
3. Audit [workers/local_ocr/README.md](../../../../workers/local_ocr/README.md) against actual `.NET` runner and Python worker isolation code, confirming accurate library-offline wording, absence of unsupported OS network-denial claims, and invariance of `worker_source_sha256`.
4. Freeze the review helper before decisive execution, commit deliverables before this canonical report, push `review/wp-0008-f3` without force, and verify exact `origin` publication.

## Change inventory

### Base-to-Deliverable Diff (`30bb49ed56c32bda61a6907d49bd183e7b292268..367b9fae0c0578d27a86c858b4a3f07c1d2ea284`)

| Action | Exact path or external resource | What changed and why | Relevant symbols / sections |
| --- | --- | --- | --- |
| Added (`367b9fae...`) | [README.md](../../../reviews/WP-0008/eld-f3-reviewer/design/README.md) | Focused primary-source review dossier recording `accepted` dispositions, source feasibility checks, `F3-KR-01`, and `F3-BIC-01`..`06` | Sections 1–3 |
| Added (`367b9fae...`) | [verify_f3_design_and_readme.py](../../../reviews/WP-0008/eld-f3-reviewer/design/verify_f3_design_and_readme.py) | Frozen pure-stdlib verification helper checking Git preservation, worker README/source-digest parity, F2 seed digests, parser/suggestion/concurrency feasibility, port disjointness, sealed-path refusal, and Markdown links | `SafeRepoReader`, `parse_strict_simple_two_cell_rows`, `evaluate_work_order_suggestions`, `ReviewLedgerSimulator`, `main` |

### Post-Deliverable Evidence, Report Metadata, Scratch, and External Effects

- Added (`81b245481c6c46bb8c8e38f8e0f4a108ddf81f69`): [verification-receipt.json](../../../reviews/WP-0008/eld-f3-reviewer/design/verification-receipt.json) — post-freeze verification output generated against clean `HEAD = 367b9fae0c0578d27a86c858b4a3f07c1d2ea284` (`37/37` assertions passed).
- Added (single-file report commit following `81b245481c6c46bb8c8e38f8e0f4a108ddf81f69`): `docs/agent-reports/eld-f3-reviewer/WP-0008/002_2026-11-16_review_eld-f3-reviewer.md`.
- Ignored `.scratch/` files in owned worktree (`.gitignore` L25): `.scratch/pre-freeze-failure-01.txt`, `.scratch/pre-freeze-receipt.json`, `.scratch/report-link-check.json`.
- External effects: normal non-force push of `review/wp-0008-f3` to `origin`; zero database, service, GPU, model, firewall, or global configuration changes.

## Decisions and rationale

Full code-pinned rationale lives in [design/README.md](../../../reviews/WP-0008/eld-f3-reviewer/design/README.md):

1. **Acceptance of `F3-review-correction.md` (`4d6b9770599087534ed11aadbec6510ed10c77c1`):**
   - **Suggestion feasibility (`F3-BIC-01`):** Against accepted F2 `SYN-WO-01-v1-raster300` (`7503761a...`), all five `maintenance-work-order/1` fields map cleanly (`p1:b4`, `p1:b6`, `p1:b8`, `p1:b10`, and `p1:b24` `298` UTF-16 code units after `title` `b23`), while 3-page invoice `SYN-MP-01-v0-clean` (`c399ad89...`) produces five `null` suggestions. Because [SafeNativeDisplayParser.cs](../../../../src/ELedgerCare.Domain/Processing/SafeNativeDisplayParser.cs) (`L173–231`) strips `<td>`/`<th>` attributes in `TableRows`, `WorkOrderReviewSuggestions` must inspect raw `ExtractedBlockView.Text` (`L109`) to reject `colspan`/`rowspan`/nested/unbalanced rows, guard inline `<Label>:` parsing against `Label::` double colons, and keep machine candidate state (`suggested`/`missing`/`ambiguous`/`invalid_or_oversized`) distinct from human `decision` (`unreviewed` at revision `0`).
   - **Least privilege & concurrency (`F3-BIC-02`, `F3-BIC-03`):** Column-scoped `GRANT UPDATE` on review-head pointer columns mirrors [grant-runtime.sql](../../../../deploy/dev/database/grant-runtime.sql) (`L18–41`) so the persisted first-save machine snapshot stays immutable at the PostgreSQL role boundary. Because `eledgercare_app` lacks `UPDATE` on `documents`/`extraction_results` (and PostgreSQL `SELECT ... FOR UPDATE` requires `UPDATE` privilege), `expectedRevision = 0` must serialize via unique head/operation constraints (`23505` rollback + fresh-context reconciliation) and `expectedRevision >= 1` via `FOR UPDATE` on the review-head row. Checking `Idempotency-Key` replay before both stale-head and `128`-revision checks preserves lost-response replay on every revision (`1..128`), and human inputs must fail closed (`400`/`422`) rather than using `DiagnosticTextSanitizer` replacement/truncation.
   - **Native PDF `/preview`, Edge readability, in-memory uncertainty, & F2 seed (`F3-BIC-04`..`06`, `F3-KR-01`):** Inline `Content-Disposition`, `SAMEORIGIN` framing, range support, narrowed `ResourceUrl` binding, visual viewport verification on raster `SYN-WO-01-v1-raster300.pdf` (`text_layer=false`) with explicit escalate-before-renderer-substitution discipline, strictly in-memory pending save retention, and test-only genuine F2 seed setup (`LocalOcr:Enabled=false`, `extraction_fencing_seq` advancement, `5390/4410/55436` vs. `5490/4510/55437`) are fully compatible with existing F1/F2 code.
2. **Acceptance of `workers/local_ocr/README.md` (`83ed6624f95c48bfbae4c466201774824f63ef5e`):**
   - Matches [LocalPythonOcrWorkerRunner.cs](../../../../src/ELedgerCare.Infrastructure/Extraction/LocalPythonOcrWorkerRunner.cs) (`L337–348`), [env_guard.py](../../../../workers/local_ocr/local_ocr/env_guard.py) (`L112–115`), [worker.py](../../../../workers/local_ocr/local_ocr/worker.py) (`L151–158`), and [WindowsJobProcess.cs](../../../../src/ELedgerCare.Infrastructure/Extraction/WindowsJobProcess.cs) (`L99–114`), removes the only unsupported network-denial claim in the product tree, and preserves `worker_source_sha256 = c1c324c36e27f57c3c4ac4a1462984fbe586ad43ab82af3a2883bb7eac4c0d54`.

## Verification

### Inspected vs. Executed Checks

| Check / exact command or operation | Mode, environment, and revision | Actual result | Evidence location |
| --- | --- | --- | --- |
| Primary-source inspection of `F3-review-correction.md`, `workers/local_ocr/README.md`, `WP-0008 /001`, `src/**`, `web/**`, `deploy/**`, `tests/**`, `workers/local_ocr/**`, and accepted F2 `WP-0006` artifacts | **Inspected** (read-only in `eld-f3-reviewer` at `30bb49ed56c32bda61a6907d49bd183e7b292268`) | Confirmed contract feasibility, exact offline-library wording, zero cross-boundary product imports, and identified `F3-KR-01` + `F3-BIC-01`..`06` | [design/README.md](../../../reviews/WP-0008/eld-f3-reviewer/design/README.md) |
| Initial pre-freeze helper dry-run (`python -B docs/reviews/WP-0008/eld-f3-reviewer/design/verify_f3_design_and_readme.py --output .scratch/pre-freeze-receipt.json`) | **Executed** (CPU/Python `3.12.10` pre-freeze draft before `367b9fae...`) | **Exit `1` (preserved failure):** `suggestion_edge_cases` caught naive `startswith("Property:")` treating `"Property::"` as inline value `":"`; guarded before freeze and added to `F3-BIC-01` | `.scratch/pre-freeze-failure-01.txt` (retained in ignored `.scratch/`) |
| Decisive post-freeze verification (`python -B docs/reviews/WP-0008/eld-f3-reviewer/design/verify_f3_design_and_readme.py --require-clean --output docs/reviews/WP-0008/eld-f3-reviewer/design/verification-receipt.json`) | **Executed** (CPU/Git/Python `3.12.10` on clean frozen `HEAD` `367b9fae0c0578d27a86c858b4a3f07c1d2ea284`, helper SHA-256 `72e7826d3d2781dbb44a9fe42a36a039784a7904bad163a860a3e7a0c65d74b1`) | **Exit `0`:** `37 / 37` assertions passed (exact 11-path candidate diff, 12 preserved trees/files, 50 unchanged prior report files, `worker_source_sha256` invariance, F01/F07 seed digests & suggestion probes, `colspan`/surrogate/128-cap invariants, 18 disjoint ports, 26 Markdown links, `0` sealed paths opened) | [verification-receipt.json](../../../reviews/WP-0008/eld-f3-reviewer/design/verification-receipt.json) (`81b245481c6c46bb8c8e38f8e0f4a108ddf81f69`) |
| Canonical report link & whitespace check (`python -B .../verify_f3_design_and_readme.py --extra-md docs/agent-reports/eld-f3-reviewer/WP-0008/002_2026-11-16_review_eld-f3-reviewer.md --output .scratch/report-link-check.json` + `git diff --cached --check`) | **Executed** (CPU/Git/Python `3.12.10` at `81b245481c6c46bb8c8e38f8e0f4a108ddf81f69`) | **Exit `0`:** all report and dossier local links resolved; zero whitespace/conflict issues | `.scratch/report-link-check.json` & Git commit history on `review/wp-0008-f3` |

### Checks Not Run and Why

- **`.NET` build/tests, PostgreSQL `18.7` cluster/migration, Angular `ng serve`, and Playwright Microsoft Edge E2E:** Not run in `/002`; no F3 application code exists yet and starting services is outside `/002` scope (scheduled for independent `WP-0008 /004` on `5490/4510/55437` after `/003` implementation freeze).
- **GPU / model inference or OS firewall/network probes:** Prohibited by [WP-0008-eld-f3-reviewer-design.md](../../../kickoffs/WP-0008-eld-f3-reviewer-design.md); F3 requires zero model runs and the README change narrows unverified network-sandbox claims rather than asserting OS blocking.
- **`WP-0009` diagnosis, mapper, or sealed fresh-family corpus inspection:** Out of product-reviewer scope and procedurally sealed.

## Review map

- Reviewed root candidate (`c5b5db3af96abf155c806082583b8a92c687f54d`): [F3-review-correction.md](../../../design/F3-review-correction.md) (`4d6b9770599087534ed11aadbec6510ed10c77c1`), [workers/local_ocr/README.md](../../../../workers/local_ocr/README.md) (`83ed6624f95c48bfbae4c466201774824f63ef5e`), [WP-0008-eld-f3-reviewer-design.md](../../../kickoffs/WP-0008-eld-f3-reviewer-design.md) (`9663964fe4d8e6a8a0c7398ea07dbc524abdaa11`), and [WP-0008-0009-authority.md](../../../coordination/WP-0008-0009-authority.md).
- Reviewed coordinator `/001` report (`30bb49ed56c32bda61a6907d49bd183e7b292268`): [WP-0008 / 001](../../eld-coordinator/WP-0008/001_2026-11-16_design_eld-coordinator.md).
- Reviewer frozen deliverable (`367b9fae0c0578d27a86c858b4a3f07c1d2ea284`): [design/README.md](../../../reviews/WP-0008/eld-f3-reviewer/design/README.md) and [verify_f3_design_and_readme.py](../../../reviews/WP-0008/eld-f3-reviewer/design/verify_f3_design_and_readme.py).
- Post-freeze verification evidence (`81b245481c6c46bb8c8e38f8e0f4a108ddf81f69`): [verification-receipt.json](../../../reviews/WP-0008/eld-f3-reviewer/design/verification-receipt.json).

## Risks, disagreements, and unfinished work

- **Substantive design or README disagreements:** **None** (`0` blocking defects; no reconciliation round required before `/003`).
- **Carried-forward implementation & acceptance gates (`WP-0008 /003`–`/004`):**
  1. Coordinator binds `deploy/dev/**` path ownership (`F3-KR-01`) in `docs/kickoffs/WP-0008-eld-f3-implementer.md`.
  2. Implementer and independent `/004` reviewer verify `F3-BIC-01`..`06` against real PostgreSQL `18.7` (`5390/4410/55436` author; `5490/4510/55437` reviewer) and actual Microsoft Edge, including visual readability of inline `/preview` alongside the five fields on raster `SYN-WO-01-v1-raster300.pdf` (escalating per `F3-review-correction.md` L52 rather than silently substituting a renderer if Edge automation blocks inline PDF rendering).

## Handoff

- **Disposition:** **`accepted`** on frozen root candidate `c5b5db3af96abf155c806082583b8a92c687f54d` (`F3-review-correction.md` + `workers/local_ocr/README.md`) and `WP-0008 / 001` (`30bb49ed56c32bda61a6907d49bd183e7b292268`).
- **Next owner:** `eld-coordinator` (update `INDEX.md` / `CURRENT.md` and bind/dispatch `WP-0008 /003` `eld-f3-implementer` with `F3-KR-01` and `F3-BIC-01`..`06`).
- **Owned branch:** `review/wp-0008-f3`
- **Base SHA:** `30bb49ed56c32bda61a6907d49bd183e7b292268` (packet base `5e1241d6d365d664f12619d415f48ec3d3b7ddca`, authority `22b88bc32d053231678aef88e6b7f76d3e61910a`)
- **Reviewed design candidate SHA:** `c5b5db3af96abf155c806082583b8a92c687f54d`
- **Frozen review deliverable SHA:** `367b9fae0c0578d27a86c858b4a3f07c1d2ea284`
- **Post-freeze verification evidence SHA:** `81b245481c6c46bb8c8e38f8e0f4a108ddf81f69`
- **Report path:** `docs/agent-reports/eld-f3-reviewer/WP-0008/002_2026-11-16_review_eld-f3-reviewer.md`
- **Publication receipt:** Committed as a single-file report-only commit immediately following `81b245481c6c46bb8c8e38f8e0f4a108ddf81f69`, pushed without force on `review/wp-0008-f3`, verified on `origin` via `git ls-remote`, and its exact publication SHA is returned in the handoff message to `eld-coordinator`.
