# Pre-Completion & Pre-Freeze Failure Lineage (`WP-0010 / 003`, `eld-f4-implementer`)

## 1. Prior Preparation Checkpoint (`033d1dabb348b4dd6ba450ae9397c9f901a8b97b`, Immutable)

- Retained pre-freeze interactive setup logs from Turn 1 remain untouched under [`../preparation/retained-failures/`](../preparation/retained-failures/README.md) (`prefreeze-setup-failure-01.txt`, `prefreeze-setup-failure-02.txt`).
- Note on Turn 1 CLI termination: after immutable publication `033d1dabb348b4dd6ba450ae9397c9f901a8b97b` completed and pushed to `origin`, the Antigravity CLI turn encountered a transient provider DNS lookup error (`dial tcp: lookup oauth2.googleapis.com: no such host`, `result: ERROR`, wrapper exit `0`). Coordinator verified all 17 published preparation artifacts, 13 seed assertions, stopped services, and resolved DNS prior to releasing F4 implementation at `7345ef03dfa4d5f039259d0b8b9505685112469d`.

## 2. Pre-Freeze F4 Implementation Development Fixes (Before Candidate Freeze)

All items below were resolved during pre-freeze local verification before any frozen F4 candidate commit was created:

| Stage | Symptom Observed | Root Cause | Pre-Freeze Resolution |
| --- | --- | --- | --- |
| Pre-freeze `Infrastructure.Tests` (`SyntheticFixtureTests`) | `Assert.DoesNotContain("qualification/")` failed on `ArchiveProjectionEntities.cs` | XML doc comment contained prose `(zero qualification/research/evaluation imports)` matching raw substring guard | Reworded XML doc comment to `(zero non-product imports; F4-BIC-02, F4-BIC-05)` |
| Pre-freeze `Domain.Tests` (`ArchiveDomainTests`) | `Assert.Contains("$1,535.35")` failed on `SYN-WO-01` projection | `$1,535.35` is on `SYN-MP-01` Page 3 (`c399ad89...`), whereas `SYN-WO-01` contains `0018-TERM-QC` and `Priority: Urgent [X]` | Moved `$1,535.35` assertion to `mpProj.Units[2]` (Page 3) in `ArchiveDomainTests.cs` |
| Pre-freeze `Acceptance.Tests` (`ArchiveAcceptanceTests`) | `POST /api/documents/{id}/review/revisions` returned `422 UnprocessableEntity` in test helper | Test helper sent `decision = "accepted"` without `value = machineCandidate.value` | Supplied exact suggested values on `decision = "accepted"` fields in `ArchiveAcceptanceTests.cs` and `archive.spec.ts` |
| Pre-freeze `e2e/archive.spec.ts` | Playwright `locator('mark.archive-hit').toHaveText('Refrigerator Evaporator')` hit strict-mode `2 elements` | Two-term query `Refrigerator Evaporator` highlights two separate `<mark>` spans (`['Refrigerator', 'Evaporator']`) inside the deduplicated Page 2 witness | Updated assertion to `.toHaveText(['Refrigerator', 'Evaporator'])` in `web/e2e/archive.spec.ts` |

## 3. Post-Freeze Decisive Candidate Failures

| Frozen Candidate | Retained Original Log | Bytes | SHA-256 | Classification & Root Cause |
| --- | --- | --- | --- | --- |
| `74555395e8ed55020ffd004369b30581bfa7963c` | [`74555395-task-525.log`](74555395-task-525.log) | `983` | `ad2c72daa25be20f3da3e79f448252a42b6b5b86bdac5d15a9a80efad4646c5a` | **Exact original outer task wrapper log.** Steps `01`..`10` of `run_f4_decisive_verification.py` passed (`9/9` worker CPU tests, locked `.NET` restore & Release build, `ng build`, `95/95` `.NET` tests, `5590` demo smoke, `15/15` Playwright Edge E2E specs, real forward migration of cloned `eledgercare_f4_author_seed_f3` -> `eledgercare_f4_author_migrated`, `13/13` `42501` privilege denials, startup backfill of `5` projections / `9` units, `EXPLAIN`, and warm latency probes). Step `11-edge-f4-before-restart` exited `1`, and `finally:` stopped UI, API, and PostgreSQL `55438` cleanly. |
| `74555395e8ed55020ffd004369b30581bfa7963c` | [`74555395-11-edge-f4-before-restart.log`](74555395-11-edge-f4-before-restart.log) | `937` | `fa31c099961ad0a1259fc03ac04a90af5a9427415dcf74863d890f6b46ff2442` | **Exact original Step `11` helper log.** All saved archive queries and excluded-sentinel checks in `verify_f4_restart_edge.mjs` (`L80–145`) succeeded, then `L156` failed because helper constant `EXPECTED_F1_PDF_SHA` had a mistyped tail (`875a2d8ca1ba...` instead of actual `tests/fixtures/F1-SWO-001.pdf` SHA-256 `875a2d8c83c1c1002b38840f8136b60bd5ebcfe8d2df47187bf36454c59497cb`). Resolved in helper `verify_f4_restart_edge.mjs` without any `src/`, `web/`, `tests/`, or `deploy/` product changes, frozen in a new candidate commit, and re-executed end-to-end. |
