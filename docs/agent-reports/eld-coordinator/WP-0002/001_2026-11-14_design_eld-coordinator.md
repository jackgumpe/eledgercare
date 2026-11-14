# WP-0002 / 001: cohesive F1 model, durability contract and bootstrap pins

- Report path: docs/agent-reports/eld-coordinator/WP-0002/001_2026-11-14_design_eld-coordinator.md.
- Reservation: INDEX.md at 287183ceec005195d03e83649a3f91c41ae4fcd1, WP-0002 / 001.
- Category / author: design / eld-coordinator.
- Actual model / effort: not exposed; requested Astra/High is not backend proof.
- Execution: local Codex on Windows; session 01a1d895-c605-7ab2-b7ec-c3159c0634ba.
- Published by: eld-coordinator.
- Timestamp: 2026-11-14T15:10:33Z.
- Repository / branch: jackgumpe/eledgercare / coordination/bootstrap.
- Full base: 35f6090a9b2e16c7645b56f34b104eb3126d5c90.
- Deliverable: e90c71817bc793dfbfc7576006be3cbf0b4310bf.
- Previous / related report: WP-0001 / 001 at 287183ceec005195d03e83649a3f91c41ae4fcd1.
- Status: ready-for-review; coordinator-authored design, not independently accepted.
- Next owner: eld-reviewer / Carbon, WP-0002 / 002.

## Outcome and criteria

One cohesive design resolves the first slice's storage transaction, upload limits, input profile, stable references, retry/conflict behavior, uncertain responses, interruption recovery and evidence mechanisms. It includes the compact model/feature sequence, dependency observations and isolated resource plan. The supplied contract/profile/design are to be reviewed together before application implementation. No production application code was authored.

The proposed design stores original bytea plus document and awaiting-extraction job in one PostgreSQL transaction and acknowledges only after commit. A UUID retry key identifies the business submission independently of its content digest. Exact same-key retries recover the original receipt; conflicting bytes fail, while different keys can submit identical originals. The browser distinguishes unknown submission outcome from persisted job status.

Admission is a bounded, strict developer-PDF profile with a 10 MiB limit, 50-page cap, parser validation and no client-selected filesystem path. It is not represented as a hostile-content sandbox. Tests must cover actual HTTP, real PostgreSQL, interruption, lost response and application process restart.

## Complete base-to-deliverable inventory

| Action | Exact path | Purpose / attribution |
| --- | --- | --- |
| Modified | CURRENT.md | Earlier 287183c coordination metadata releases design/R&D and records private publication |
| Modified | INDEX.md | Earlier 287183c packet-wide reservations before execution |
| Added | docs/agent-reports/eld-coordinator/WP-0001/001_2026-11-14_verification_eld-coordinator.md | Earlier immutable seed receipt |
| Added | docs/kickoffs/WP-0004-eld-rd-astra.md | Earlier independent Astra assignment |
| Added | docs/kickoffs/WP-0004-eld-rd-carbon.md | Earlier independent Carbon assignment |
| Added | docs/design/F1-durable-intake.md | Cohesive proposed model/design, acceptance/evidence and resource plan |
| Added | docs/design/dependency-metadata-2026-11-14.json | Exact primary registry metadata, target/dependency ranges, upstream commit/integrity where exposed |

Separate post-deliverable metadata: this report; INDEX.md/CURRENT.md routing updates; docs/kickoffs/WP-0002-eld-reviewer.md; docs/kickoffs/WP-0003-eld-implementer.md. These do not silently change the reviewed design candidate.

## Evidence actually obtained

| Check / operation | Revision / result | Evidence location |
| --- | --- | --- |
| Official Angular compatibility and exact npm package metadata | Node 24.18.0 and TypeScript 6.0.3 fit the observed Angular 22 requirements; package metadata exists for listed exact pins | Design source links; dependency-metadata JSON |
| NuGet exact nuspec inspection | EF 10.0.15 targets net10.0; Npgsql EF 10.0.3 requires EF >=10.0.4 and <11; listed test/parser packages and source pins observed | dependency-metadata JSON |
| PdfPig tag/nuspec/source reconciliation | v0.1.16 annotated tag resolves to a7bb35662bbbf405efddad50aedc9bcdcf515afc, matching nuspec; pinned ParsingOptions inspected for strict/depth options | Design source/package references; GitHub API observation |
| PostgreSQL transaction/bytea/WAL and Windows download docs | Inspected primary documentation; chose one-store transaction and proposed scoped Windows archive route | Design linked sources |
| docker version --format '{{json .Server}}' | Failed: dockerDesktopLinuxEngine named pipe absent; no daemon started | Design known setup gap; session output |
| Get-Command postgres,pg_ctl,psql; exact Program Files 17/18 server paths | Not found on checked PATH/paths; no machine-wide search or assertion of global absence | Design known setup gap |
| git diff --cached --check | Passed for the new design/metadata before commit | Session command |
| git push / git ls-remote coordination/bootstrap | e90c71817bc793dfbfc7576006be3cbf0b4310bf published and matching remote ref | Session output / remote |

No package installation, scaffold, build, tests, database startup, PDF parsing execution, OCR, GPU or deployment was performed. Registry metadata and source inspection are not runtime qualification. The metadata also includes inspected test alternatives; the design explicitly selects xunit.v3/MTP and does not blindly adopt every inspected package.

## External effects and parallel work

Read-only network requests to primary documentation/registries/GitHub were performed. The design artifact and metadata were committed/pushed. Separately reserved R&D worktrees were created at the root seed, and a gpt-6-astra/high subagent was actually dispatched as eld-rd-astra under WP-0004 / 001. It has a different branch/worktree and no product write authority. Carbon dispatch remains unavailable. No Opus application session has started. The R&D result is not part of this design's acceptance evidence.

## Review map, risks and handoff

Review [the full candidate](https://github.com/jackgumpe/eledgercare/tree/e90c71817bc793dfbfc7576006be3cbf0b4310bf) and docs/design/F1-durable-intake.md together with the original contract/product brief, working agreement and seed receipt. The selected vendor PostgreSQL build/hash and successful local launch, locked dependency restore/build, parser behavior, MTP runner and all DI checks remain unexecuted. These limits are explicit, not assumed passes.

The reviewer should return accepted or bounded changes-requested for e90c71817bc793dfbfc7576006be3cbf0b4310bf, with source evidence and actual inspection/execution distinguished. The exact Carbon kickoff binds its branch/worktree/report path. Product implementation stays held until that verdict and the coordinator's disposition exist. This report's own publication SHA is communicated after its metadata commit; it is not self-embedded here.
