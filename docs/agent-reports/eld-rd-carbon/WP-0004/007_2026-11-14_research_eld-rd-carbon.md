# WP-0004 / 007: Correct truncated pypdfium2 wheel SHA-256 in tooling-provenance.json

- Report path: `docs/agent-reports/eld-rd-carbon/WP-0004/007_2026-11-14_research_eld-rd-carbon.md`
- Sequence reservation: Coordinator `INDEX.md` (`WP-0004 / 007` @ `5837877874993df691b51e31dab52195c66aa195`) and `docs/kickoffs/WP-0004-eld-rd-carbon-provenance-correction.md` (@ `5837877874993df691b51e31dab52195c66aa195`)
- Category: research
- Author / agent ID: `eld-rd-carbon`
- Actual model / effort: Gemini 4 Carbon (High effort; backend checkpoint ID not exposed)
- Execution environment: CLI (Antigravity CLI on Windows 11 x64 `10.0.26200`, PowerShell, recovery conversation/session `993d4f08-72d0-479c-9e6c-047280cedf95` continuing `eld-rd-carbon` author lineage from `74513d00-ee88-4e85-a554-120908615b21`; owned `.venv` Python `3.12.10` stdlib `hashlib`/`json`/`subprocess`)
- Published by: `eld-rd-carbon` (self-published on owned branch `research/wp-0004-carbon-recovery`)
- Timestamp: 2026-11-14T21:46:02Z
- Repository / branch: `https://github.com/jackgumpe/eledgercare` (`PRIVATE`) / `research/wp-0004-carbon-recovery` (owned worktree `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-rd-carbon-recovery`)
- Base revision: `fabddf72a80337a98ddb777c901edac11f9163fe` (`WP-0004 / 004` report publication commit)
- Deliverable revision: `29b2000265ae6068d9c86818622c81a40cadd961` (one-field metadata candidate; focused verification receipt committed separately at `85ab359ba3348e6323b531c5f8c2677d6775687e`)
- Previous report: [`WP-0004 / 004`](./004_2026-11-14_research_eld-rd-carbon.md) (@ `fabddf72a80337a98ddb777c901edac11f9163fe`; prior frozen candidate `fca8f16e51359d6895dca27a05fe76af82f58ff4`; prior evidence `1ef33dcddf324a6a48285a6e302af5d1528b3c34`)
- Related or reviewed reports: Coordinator mechanical preflight `docs/coordination/WP-0004-provenance-preflight.md` (@ `5837877874993df691b51e31dab52195c66aa195`); [`WP-0004 / 002`](./002_2026-11-14_research_eld-rd-carbon.md) (@ `fef02d64aca2594e146930e4a0cb3ec18e355ed5`); `WP-0004 / 001` (@ `189d4cb444c5afde059e6e1d2bee37c8294509d0`); `WP-0004 / 003` (@ `c3215f75fc311c2e3c61a8ecc5da7d950f933157`)
- Status: ready-for-review
- Next owner: `eld-coordinator`

## Summary

Completed bounded `WP-0004 / 007` author checksum correction on `research/wp-0004-carbon-recovery` from clean base `fabddf72a80337a98ddb777c901edac11f9163fe`. All three immutable wheel archives in `.scratch/wheels/` were independently rehashed, and the single truncated 55-character `pypdfium2` SHA-256 in [`evaluation/manifests/tooling-provenance.json`](../../../../evaluation/manifests/tooling-provenance.json) (`74d1bace34fb01c660d0b64344d5a4b7c6623c88ab59ea21c5acfbd`) was replaced with its measured 64-character SHA-256 (`74d1bace34fb01c660d0b64344d5a4b7d276942b7c6623c88ab59ea21c5acfbd`), frozen at candidate `29b2000265ae6068d9c86818622c81a40cadd961` prior to committing verification receipt `85ab359ba3348e6323b531c5f8c2677d6775687e`.

This report is **author verification only** (`ready-for-review`), not independent acceptance. All corpus PDFs (`26`), sources (`8`), expected JSONs (`26`), generation/check scripts (`4`), backlog/reconciliation documents (`3`), prior `/004` evidence (`1ef33dcddf324a6a48285a6e302af5d1528b3c34`), and historical reports (`/002`, `/004`) are byte-for-byte unchanged. Independent non-author review and ground-truth admission remain with uninvolved Opus (`eld-rd-reviewer` in `WP-0004 / 005`).

## Objective and acceptance criteria

Per `5837877874993df691b51e31dab52195c66aa195:docs/kickoffs/WP-0004-eld-rd-carbon-provenance-correction.md`:

1. Independently rehash all three owned wheel archives in `.scratch/wheels/` (`pypdfium2`, `Pillow`, `pypdf`) without merging coordinator branches.
2. Correct only the erroneous 55-character `pypdfium2` `sha256` field in `evaluation/manifests/tooling-provenance.json` and commit that one-field metadata candidate first (`29b2000265ae6068d9c86818622c81a40cadd961`).
3. Verify all three wheel sizes and 64-character SHA-256 digests against the corrected candidate and prove via Git tree comparison that all corpus, script, backlog, prior-evidence, and historical-report files remain unchanged without needlessly regenerating or visually re-rendering the unchanged 40-page corpus.
4. Commit compact verification evidence (`evaluation/manifests/provenance-correction-verification.json`) and this concise `/007` report separately (strictly three tracked paths total from `fabddf72a80337a98ddb777c901edac11f9163fe`), normal-push `research/wp-0004-carbon-recovery`, and verify `origin`.

## Change inventory

### 1. Deliverable diff (`fabddf72a80337a98ddb777c901edac11f9163fe..29b2000265ae6068d9c86818622c81a40cadd961` — 1 modified path)

| Action | Exact path | What changed and why | Relevant JSON key |
| --- | --- | --- | --- |
| Modified | `evaluation/manifests/tooling-provenance.json` | Replaced 55-char truncated `pypdfium2` SHA-256 (`74d1bace34fb01c660d0b64344d5a4b7c6623c88ab59ea21c5acfbd`) on line 59 with measured 64-char SHA-256 (`74d1bace34fb01c660d0b64344d5a4b7d276942b7c6623c88ab59ea21c5acfbd`); `1` insertion, `1` deletion (`5,518` B, Git blob `4b521673baf0ee223b340f665763b8d1ced17677`, SHA-256 `5c8bf64d381a76f5a34f51cc5f4da1d211a58bbc49207984342d57ce1767aa46`). | `installed_wheels[0].sha256` |

### 2. Post-candidate evidence and report metadata committed separately (`2` added paths; `3` total paths from `fabddf72a80337a98ddb777c901edac11f9163fe`)

| Commit | Action | Exact path | What changed and why |
| --- | --- | --- | --- |
| `85ab359ba3348e6323b531c5f8c2677d6775687e` | Added | `evaluation/manifests/provenance-correction-verification.json` | Focused verification receipt (`4270` B, Git blob `eefcad526eaffa271e33a9129c3ed0d774b68714`, SHA-256 `e629f4f8f7f5c32cb254f5fe824bce97bf9cb695210573212aae6f7d0de9499e`) recording measured wheel sizes/hashes and Git tree invariance across all `97` other tracked files. |
| Report publication commit (immediately atop `85ab359...`) | Added | `docs/agent-reports/eld-rd-carbon/WP-0004/007_2026-11-14_research_eld-rd-carbon.md` | Concise `WP-0004 / 007` author correction report (records `29b2000265ae6068d9c86818622c81a40cadd961` and `85ab359ba3348e6323b531c5f8c2677d6775687e`; does not claim to contain its own SHA). `INDEX.md` and `CURRENT.md` untouched. |

### 3. External effects

- **Read-only Git fetch & remote push:** Ran `git fetch origin` read-only (no merge) to inspect `5837877874993df691b51e31dab52195c66aa195`, wrote two helper scripts under ignored `.scratch/` (`rehash_wheels_and_patch.py`, `verify_007_provenance.py`), and pushed `research/wp-0004-carbon-recovery` without `--force` to `origin`. Zero package installs, downloads, services, databases, GPU runs, or edits to other worktrees occurred.

## Decisions and rationale

- **Minimal single-field repair:** In `/004`, rewriting `tooling-provenance.json` dropped 9 middle hex characters (`d276942b7`) from the `pypdfium2` wheel digest while `8fb7e3ca537b1710fe231dad0cf5d177c6e5d733:evaluation/manifests/tooling-provenance.json` held the full 64-character value. Repairing strictly that single string preserves every other line and byte of the repository.
- **Honest attribution instead of redundant corpus rerendering:** Because `git ls-tree -r` proves identical Git blob OIDs between `fca8f16e51359d6895dca27a05fe76af82f58ff4` and `29b2000265ae6068d9c86818622c81a40cadd961` across all `26` PDFs, `8` sources, `26` expected JSONs, `4` scripts, `corpus-manifest.json`, and `3` reconciliation/backlog docs, the prior Gate A, Gate B two-run regeneration, clean `autocrlf=true` clone, and `40/40` 300-DPI visual inspection results remain attributed to [`evaluation/manifests/recovery-verification/frozen-candidate-verification.json`](../../../../evaluation/manifests/recovery-verification/frozen-candidate-verification.json) (`1ef33dcddf324a6a48285a6e302af5d1528b3c34`) and [`WP-0004 / 004`](./004_2026-11-14_research_eld-rd-carbon.md) (`fabddf72a80337a98ddb777c901edac11f9163fe`) rather than re-executed.

## Verification

### 1. Observed wheel sizes and SHA-256 digests (`python .scratch/rehash_wheels_and_patch.py` & `.scratch/verify_007_provenance.py`)

| Wheel archive (`.scratch/wheels/`) | Measured bytes | Measured 64-char SHA-256 | Matches `29b2000...` & `8fb7e3c...` |
| --- | --- | --- | --- |
| `pypdfium2-5.15.2-py3-none-win_amd64.whl` | `4,187,589` | `74d1bace34fb01c660d0b64344d5a4b7d276942b7c6623c88ab59ea21c5acfbd` | Yes (repaired from 55-char `74d1bace34fb01c660d0b64344d5a4b7c6623c88ab59ea21c5acfbd`) |
| `pillow-13.0.0-cp312-cp312-win_amd64.whl` | `7,272,166` | `ff3fe9eb621fbb9db4c4be33ab946f6bac5f98ab50ca8d3260503653656c961b` | Yes (unchanged) |
| `pypdf-7.1.0-py3-none-any.whl` | `418,698` | `47cca6b24bdcf4c4d65b5f7b8b972535c61710a061261e737688777cfd9a7bfb` | Yes (unchanged) |

### 2. Executed checks in `WP-0004 / 007` vs. checks not re-run

| Check / exact command | Revision | Actual result | Evidence location |
| --- | --- | --- | --- |
| Wheel rehash & checkpoint comparison (`.\.venv\Scripts\python.exe .scratch/rehash_wheels_and_patch.py`) | Working tree from `fabddf72a80337a98ddb777c901edac11f9163fe` vs `8fb7e3ca537b1710fe231dad0cf5d177c6e5d733` | Measured exact byte sizes and 64-char SHA-256 digests for all 3 wheels; verified `100%` parity with `8fb7e3c`. | [`provenance-correction-verification.json`](../../../../evaluation/manifests/provenance-correction-verification.json) |
| Candidate diff & full Git tree invariance check (`.\.venv\Scripts\python.exe -W error .scratch/verify_007_provenance.py`) | Frozen candidate `29b2000265ae6068d9c86818622c81a40cadd961` vs `fabddf72a80337a98ddb777c901edac11f9163fe` & `fca8f16e51359d6895dca27a05fe76af82f58ff4` | `exit 0`: `git diff --numstat` is `1 1 evaluation/manifests/tooling-provenance.json`; `97/98` tracked files unchanged (`26` PDFs, `8` sources, `26` expected JSONs, `4` scripts, `3` reconciliation docs, `corpus-manifest.json`, `public-candidates.json`, `/004` receipt blob `75ffb6a2320c56daf52135951be0a17c1c64572e`, `/004` report blob `4a34724929d74745bb5d2a93b2a02617538df82a`, `/002` report blob `b424ea69729f0fcc1ec428612bcb2141f5b9416e`). | [`provenance-correction-verification.json`](../../../../evaluation/manifests/provenance-correction-verification.json) |

- **Checks not run in `/007` and why:** Corpus regeneration, arithmetic check, and 40-page 300-DPI visual inspection were intentionally not repeated per kickoff instructions because zero corpus, source, generator, or backlog bytes changed since `fca8f16e51359d6895dca27a05fe76af82f58ff4` (attributed to `/004` receipt `1ef33dcddf324a6a48285a6e302af5d1528b3c34`). Local GPU/model `Q0`/`E1`–`E3` execution and non-author Opus `/005` review remain out of scope.

## Review map

1. `git diff fabddf72a80337a98ddb777c901edac11f9163fe..29b2000265ae6068d9c86818622c81a40cadd961` — Inspect the single-line SHA-256 repair in [`evaluation/manifests/tooling-provenance.json`](../../../../evaluation/manifests/tooling-provenance.json).
2. [`evaluation/manifests/provenance-correction-verification.json`](../../../../evaluation/manifests/provenance-correction-verification.json) (`85ab359ba3348e6323b531c5f8c2677d6775687e`) — Inspect measured wheel hashes and Git blob invariance counts.
3. Full recovered corpus/backlog review for `eld-rd-reviewer` (`/005`): inspect `fef02d64aca2594e146930e4a0cb3ec18e355ed5..29b2000265ae6068d9c86818622c81a40cadd961` alongside unchanged `/004` receipt [`frozen-candidate-verification.json`](../../../../evaluation/manifests/recovery-verification/frozen-candidate-verification.json) (`1ef33dcddf324a6a48285a6e302af5d1528b3c34`) and [`WP-0004 / 004`](./004_2026-11-14_research_eld-rd-carbon.md) (`fabddf72a80337a98ddb777c901edac11f9163fe`).

## Risks, disagreements, and unfinished work

- **No independent R&D acceptance yet:** Uninvolved Opus (`eld-rd-reviewer` in `WP-0004 / 005`) must still independently verify the generator, source `Decimal` arithmetic, PDF/expected fixtures, `.gitattributes` adjustment, and 3-card backlog before any R&D milestone or ground truth is admitted.
- **Remaining technical limits unchanged from `/004`:** Cross-OS/version `PDFium`/`zlib` raster byte sensitivity and unmeasured Windows RTX 5070 Ti (`sm_120`) `Q0`/`E1`–`E3` runtime behavior remain unchanged.

## Handoff

- **Next owner:** `eld-coordinator`.
- **Next action:** Verify remote `research/wp-0004-carbon-recovery`, update `INDEX.md` and `CURRENT.md`, and bind corrected candidate `29b2000265ae6068d9c86818622c81a40cadd961` (with `/007` verification receipt `85ab359ba3348e6323b531c5f8c2677d6775687e`, this `/007` report, and unchanged `/004` lineage `fca8f16...` / `1ef33dc...` / `fabddf7...`) for uninvolved Opus review (`eld-rd-reviewer` in `WP-0004 / 005`).
- **Coordinator index inputs:**
  - **Branch:** `research/wp-0004-carbon-recovery`
  - **Base SHA (`/004` report):** `fabddf72a80337a98ddb777c901edac11f9163fe`
  - **Corrected `/007` candidate SHA:** `29b2000265ae6068d9c86818622c81a40cadd961`
  - **Verification evidence SHA:** `85ab359ba3348e6323b531c5f8c2677d6775687e`
  - **Exact report path:** `docs/agent-reports/eld-rd-carbon/WP-0004/007_2026-11-14_research_eld-rd-carbon.md`
  - **Publication receipt:** Committed immediately atop `85ab359ba3348e6323b531c5f8c2677d6775687e` and normal-pushed to `origin`; exact report publication SHA and `git ls-remote` verification are supplied in the handoff message to `eld-coordinator`.
