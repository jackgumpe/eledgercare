# WP-0008 /001: bounded work-order review and correction design

- Report path: `docs/agent-reports/eld-coordinator/WP-0008/001_2026-11-16_design_eld-coordinator.md`.
- Reservation: WP-0008 /001, INDEX at authority `22b88bc32d053231678aef88e6b7f76d3e61910a`.
- Category / author / publisher: design / eld-coordinator.
- Actual model / effort: not independently exposed. Fresh native R&D sessions explicitly requested xhigh; planned Carbon product roles retain high.
- Environment / timestamp: native Codex tools, Windows PowerShell/Git; 2026-11-16 UTC.
- Repository / branch / worktree: private jackgumpe/eledgercare; coordination/bootstrap; `C:/Users/jackg/Asp.net Projects/eledgercare`.
- Base: `5e1241d6d365d664f12619d415f48ec3d3b7ddca`.
- Frozen deliverable: **`c5b5db3af96abf155c806082583b8a92c687f54d`**.
- Previous reports: WP-0006 /005 and WP-0007 /006, report-only publication `43140c06fd734ec41a43b8ee219950386be55359`.
- Status: ready-for-review. Next owner: independent eld-f3-reviewer /002; application implementation held until design acceptance.

## Objective and acceptance

Jack authorized the reconciled F3 plus diagnosis-led mapping lane. [Authority](../../../coordination/WP-0008-0009-authority.md) and [F3 design](../../../design/F3-review-correction.md) define a local operator comparing an original with five work-order fields, saving corrections/unknowns as separate revisions, explicitly marking a revision reviewed, and reopening it after service/database restart. F3-01..07 require actual browser/source comparison, immutable originals/raw/provenance, revision history, concurrent/idempotent/uncertain save behavior, disabled-OCR reopening, real PostgreSQL migration/privilege/regression checks, and product/research separation.

This is a proposed coordinator-authored design, not independent acceptance or implemented capability. Network-assurance wording is corrected as documentation only: existing library offline flags and local_files_only do not prove enforced outbound network denial. No source/runtime/network settings changed.

## Decisions

Five work-order fields and a conservative exact-label suggestion policy avoid a hidden general-purpose mapper dependency. Unsupported/ambiguous suggestions remain unknown. The suggestion policy, source references and first machine snapshot are versioned; human changes retain distinct origin. Review state and explicit unknown decisions do not replace F2 execution state or imply factual approval. Append-only PostgreSQL revisions plus a small current-head row provide history and optimistic concurrency without a new event platform. Idempotent replay is checked before stale-head rejection, including after later saves.

Original comparison uses a narrow inline-PDF endpoint/native browser viewer, with actual readable Edge evidence required and a visible download fallback. No new renderer dependency is presumed. Existing accepted genuine F2 raw/input/provenance can seed a separate test database with explicit attribution; real F3 API/PG/Edge actions execute on that durable evidence and no fresh OCR is claimed. Any concrete native-viewer limitation returns to review before renderer substitution.

Parallel WP-0009 begins CPU diagnosis and independent sealed fresh-family creation. Selection/implementation/fresh inference remain separately gated. Neither its mapper nor its expected values become a product dependency.

## Complete base-to-deliverable inventory

| Action | Exact path | Purpose |
| --- | --- | --- |
| Modified | AGENTS.md | Record subsequent explicit F3/mapping authority and retained boundaries. |
| Modified | CURRENT.md | Active new lane and confirmed native dispatch; prior completed states retained. |
| Modified | INDEX.md | Reserve all WP-0008/0009 roles, owned branches/worktrees, report sequences and gates. |
| Added | docs/coordination/WP-0008-0009-authority.md | Complete scope, custody, resources and release boundaries. |
| Added | docs/coordination/WP-0008/initial-native-dispatch.json | Actual native startup confirmations; requested xhigh distinguished from exposed backend identity. |
| Added | docs/design/F3-review-correction.md | Proposed five-field product contract and F3-01..07 acceptance. |
| Added | docs/kickoffs/WP-0008-eld-f3-reviewer-design.md | Independent exact-design/README review assignment. |
| Added | docs/kickoffs/WP-0009-eld-mapping-author-diagnosis.md | CPU-only actual saved-output diagnosis and one-change recommendation. |
| Added | docs/kickoffs/WP-0009-eld-eval-custodian.md | Sealed four-family/four-PDF/six-page preparation with public hash reservation. |
| Added | docs/kickoffs/WP-0009-eld-mapping-reviewer.md | Independent protocol/diagnosis/corpus/source/result review boundaries. |
| Modified | workers/local_ocr/README.md | Qualify network assurance to match actual library offline/local-file settings. |

This report is later metadata. Subsequent product dispatch receipts and INDEX/CURRENT updates do not change the frozen design silently. External changes were creation of two new owned Git worktrees/branches and native task dispatch; no service, database, model, runtime environment, firewall or global installation was changed by root. The custodian separately owns newly authorized sealed CPU artifacts, to be independently admitted.

## Verification and review map

| Actual check | Result |
| --- | --- |
| Git status and exact original HEAD before work | Clean at5e1241d6d365d664f12619d415f48ec3d3b7ddca. |
| Read accepted F2 design/source/real raw output and B0 final disposition/mapping | Confirmed current product exposes raw page/block/table views, immutable results and no review workflow; bounded design references actual F01 labels/output. |
| Inspect runner BuildEnvironment and worker load_model | Observed HF_HUB_OFFLINE/TRANSFORMERS_OFFLINE/PIP_NO_INDEX and local_files_only=True; no verified network-denial assertion follows. |
| `git diff --name-status 5e1241d... c5b5db3...` | Exactly the11 paths above. |
| `git diff --check` | Exit0 before design freeze. |
| Normal authority push / `git ls-remote origin refs/heads/coordination/bootstrap` | Exact22b88bc authority confirmed before native dispatch. |
| Native startup confirmations | /root/mapping_author and /root/eval_custodian RUNNING on assigned branches, clean base5e1241d then authority22b88bc; requested xhigh, actual backend identity not independently exposed. |

No application/scorer tests, model calls or network-blocking probes were run: no implementation change was made and the network text makes a narrower assurance. Independent /002 must inspect exact design/current source, identify substantive gaps and distinguish inspection from any newly executed feasibility checks. Root must not accept its own substantive design.

## Handoff

Independent Carbon design reviewer receives exactc5b5db3 deliverable and this subsequent /001 publication, with its own actual starting HEAD/branch/worktree bound at dispatch. It may author only review/evidence paths and canonical /002. No production implementation or GPU execution is released yet. Following acceptance, root binds author implementation and independent review without seeking repeated user permission. This report's publication SHA and exact origin confirmation are recorded afterward, not self-embedded.
