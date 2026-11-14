# Carbon Independent R&D Assessment (WP-0004 / 002)

- **Owner / Stable ID:** `eld-rd-carbon`
- **Branch:** `research/wp-0004-carbon`
- **Base Revision:** `35f6090a9b2e16c7645b56f34b104eb3126d5c90`
- **Canonical Report Reservation:** `docs/agent-reports/eld-rd-carbon/WP-0004/002_2026-11-14_research_eld-rd-carbon.md`
- **Scope Status:** Independent source-based assessment only. No model weights downloaded, no packages installed, no GPU lease acquired, no training or architecture modification performed, and no public candidate admitted.

## Independence Attestation

This assessment was produced independently from primary upstream sources and the repository bootstrap inputs (`AGENTS.md`, `START_HERE.md`, and `docs/inputs/bootstrap-kit/01` through `05`) on owned branch `research/wp-0004-carbon` in `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-rd-carbon`. Neither `research/wp-0004-astra`, its worktree, nor `eld-rd-astra`'s report was inspected prior to publishing this assessment.

## Deliverable Map

1. [01-sources-and-qualification.md](01-sources-and-qualification.md) — Pinned primary-source register (`baidu/Unlimited-OCR-2`, `baidu/Unlimited-OCR`, `Azure-Samples/cognitive-services-REST-api-samples`, PyPI platform/license metadata, and host intake receipt) with applicability limits, plus the strict boundary separating product-enabling local OCR runtime qualification from optional R&D experiments.
2. [02-hypotheses.md](02-hypotheses.md) — Challenge of needless upstream complexity and confounded treatments, followed by three single-variable, falsifiable hypothesis cards (`H-C1`, `H-C2`, `H-C3`) with vanilla baselines, controlled variables, confounders, explicit metrics/denominators, and rejection criteria.
3. [03-corpus-and-candidates.md](03-corpus-and-candidates.md) — Eight-family deterministic source-first synthetic maintenance corpus plan (`F01`–`F08`), exact `Decimal` (`ROUND_HALF_UP`) accounting and two-gate ground-truth verification rules, leak-free family-level `dev`/`eval_holdout` split, provenance manifest schema, and primary-source notice/content/JSON audit of the two unadmitted Microsoft public candidates.

## Boundary with Held Future Work

- **Product Feature 1 (Durable Maintenance-Document Intake, `WP-0002` / `WP-0003`):** Requires known original PDF bytes, cryptographic digests, and honest awaiting-extraction status persistence in PostgreSQL. It does **not** depend on any OCR runtime or R&D experiment.
- **Reconciliation and Corpus Materialization (`WP-0004 / 003` and `WP-0004 / 004`):** Held until both independent initial assessments (`WP-0004 / 001` and `WP-0004 / 002`) are published and `eld-coordinator` binds the single Astra/Carbon exchange and corpus release.
- **Shared Evaluation Promotion (`WP-0004 / 005`):** Requires independent non-author verification by `eld-rd-reviewer` (uninvolved Opus session) before any fixture or ground truth enters accepted `evaluation/` artifacts.
