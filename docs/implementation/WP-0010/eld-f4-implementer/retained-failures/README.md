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

- None (`0` post-freeze candidate failures unless appended below with byte-exact original step logs).
