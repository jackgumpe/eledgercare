# WP-0006 / 002: Phase 1 independent design review of F2 local extraction and provisional B0 baseline contract

- Report path: `docs/agent-reports/eld-next-reviewer/WP-0006/002_2026-11-16_review_eld-next-reviewer.md`
- Sequence reservation: `WP-0006 /002` in [INDEX.md](../../../../INDEX.md) at `efa9cb986711f82a886f917e68142a7a59319bba` (blob `8efb26f947b9bedf8f44af864c8887cc223b56ce`); bound kickoff [WP-0006-0007-eld-next-reviewer.md](../../../kickoffs/WP-0006-0007-eld-next-reviewer.md) (blob `8e7f252d8428956b2cd6cf5c60b00d612ed7733e`)
- Category: review
- Author / agent ID: `eld-next-reviewer`
- Actual model / effort: Google DeepMind Gemini 4 Carbon (High), high effort (new independent Antigravity conversation `101b19cf-3133-4ead-91cb-9ca6068e3e72`; raw backend checkpoint identifier not separately exposed)
- Execution environment: CLI (`Antigravity CLI` on Windows x64 PowerShell; new session `101b19cf-3133-4ead-91cb-9ca6068e3e72`; Git `2.55.0.windows.1`; CPython `3.12.10`)
- Published by: `eld-next-reviewer` (using the existing configured Git author identity, unchanged)
- Timestamp: 2026-11-16T04:36:30Z
- Repository / branch: private `https://github.com/jackgumpe/eledgercare` / `review/wp-0006-0007-next-tracks` (worktree `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-next-reviewer`)
- Base revision: `c08d50e204395e60a88ce25f70e25bd29b97b8c6` (dispatch `HEAD`; packet base `8e80a42c29c0fc27a4af6348cfb1ec22cab3764d`)
- Deliverable revision: `7eae6de27d21bd41558611f95116e13cbd0f6b92` (own-branch frozen Phase 1 dossier and verification helper; post-freeze verification evidence `dc296f3a3bc8041bc2eb62377c440a3879d1bcc8`); reviewed root design candidate `efa9cb986711f82a886f917e68142a7a59319bba` (coordinator `/001` report publication `c08d50e204395e60a88ce25f70e25bd29b97b8c6`)
- Previous report: none (initial report in new independent reviewer conversation `101b19cf-3133-4ead-91cb-9ca6068e3e72`)
- Related or reviewed reports: [WP-0006 /001](../../eld-coordinator/WP-0006/001_2026-11-16_design_eld-coordinator.md) and [WP-0007 /001](../../eld-coordinator/WP-0007/001_2026-11-16_design_eld-coordinator.md) at `c08d50e204395e60a88ce25f70e25bd29b97b8c6`; [WP-0005 /006](../../eld-coordinator/WP-0005/006_2026-11-15_verification_eld-coordinator.md) at `8d9334147040e994ca007536bf61974f7de07a61`
- Status: accepted
- Next owner: `eld-coordinator` (`WP-0006 /003` product implementation release binding incorporating `F2-KR-01`; `eld-rd-astra` continues `WP-0007 /002` `dev`-only CPU work toward canonical `WP-0007 /003` scorer/protocol/runner gate)

## Summary

Independent non-author Phase 1 design review (`WP-0006 /002`) of root design candidate `efa9cb986711f82a886f917e68142a7a59319bba` and paired coordinator `/001` design reports at `c08d50e204395e60a88ce25f70e25bd29b97b8c6`, evaluated directly against accepted `F1` source/schema (`e3117ec2aa11a78359a754cfe52ef3ece6c1733f`), accepted `WP-0004` `corpus-manifest.json` and `dev`-only metadata (`29b2000265ae6068d9c86818622c81a40cadd961`), and accepted `WP-0005` `Q0` harness core/runtime observations (`41d6204648e4115ab197507d1a22f6d5c7f3e784` / `848fe70bd6d6fce9c958f11b76102d2fdfad77d4`).

- **Canonical `WP-0006 /002` F2 Design Disposition:** **`accepted`** on `efa9cb986711f82a886f917e68142a7a59319bba` ([F2-local-extraction.md](../../../design/F2-local-extraction.md), blob `8ce0c854baa889ea090d5b941d6aba0de34a5bde`), with one coordinator `/003` release-kickoff path binding (`F2-KR-01`) and four bounded implementation checkpoints (`F2-BIC-01`..`04`) carried forward to `WP-0006 /003`–`/004`.
- **Provisional `WP-0007 /001` B0 Design Disposition:** **`provisional-accepted`** on `efa9cb986711f82a886f917e68142a7a59319bba` ([B0-vanilla-accuracy-baseline.md](../../../design/B0-vanilla-accuracy-baseline.md), blob `05c9ff231ae250ca96488132c53bdaf218f200f6`). Written contract semantics, corpus/runtime pins, and partition boundaries are sound; final `B0` design + source closure occurs in canonical `WP-0007 /003` against `eld-rd-astra`'s actual parser, schema mapper, scorer, protocol JSON, and runner (`B0-PBIC-01`..`04`) before any holdout read or GPU lease.

**Independence and Holdout Non-Access Attestation:** Conversation `101b19cf-3133-4ead-91cb-9ca6068e3e72` authored zero files in `F1`, `WP-0004`, `WP-0005`, or `efa9cb98...`, edited no product/design/scorer source or shared `INDEX.md`/`CURRENT.md`, executed no GPU/application/PostgreSQL/scorer runtime, and opened **zero** holdout (`F03`, `F05`, `F06`, `F08` / `SYN-WO-03`, `SYN-INV-02`, `SYN-INV-03`, `SYN-MP-02`) PDFs, `sources/`, `expected/` JSONs, or corpus generator scripts.

## Objective and acceptance criteria

1. Verify lineage, scope, and exact preservation of accepted `F1`, `WP-0004` corpus, and `WP-0005` `Q0` harness core trees at `8e80a42c29c0fc27a4af6348cfb1ec22cab3764d`, `efa9cb986711f82a886f917e68142a7a59319bba`, and `c08d50e204395e60a88ce25f70e25bd29b97b8c6`.
2. Audit `F2-local-extraction.md` and `WP-0006-eld-f2-implementer.md` against actual `F1` domain/persistence/HTTP/admission/UI/privilege code and `Q0` runtime pins across durable attempt/result state, late-worker fencing, Windows child cleanup, bounded native worker/provenance, honest escaped display, caller-replay vs. retry semantics, forward migration/privileges, and product/research separation.
3. Audit `B0-vanilla-accuracy-baseline.md` and `WP-0007-eld-rd-astra.md` against `corpus-manifest.json`, `dev`-only (`F01`, `F02`, `F04`, `F07`) `expected`/`source` JSONs, `02-ranked-experiment-backlog.md`, and `Q0` raw outputs/timings across ground-truth-independent predictions, holdout freeze, failed-item denominators, and descriptive timing limits, without reading test-family contents.
4. Freeze deliverable before decisive verification, commit post-freeze evidence and canonical report separately, push `review/wp-0006-0007-next-tracks` without force, and confirm exact `origin` ref.

## Change inventory

| Action | Exact path or external resource | What changed and why | Relevant symbols / sections |
| --- | --- | --- | --- |
| Added (deliverable `7eae6de27d21bd41558611f95116e13cbd0f6b92`) | [README.md](../../../reviews/WP-0006/eld-next-reviewer/design/README.md) | Combined Phase 1 review dossier recording exact `F2` verdict, provisional `B0` verdict, primary-source findings, and `F2-KR-01` / `F2-BIC-01..04` / `B0-PBIC-01..04` | Sections 1–3 |
| Added (deliverable `7eae6de27d21bd41558611f95116e13cbd0f6b92`) | [verify_design_contracts.py](../../../reviews/WP-0006/eld-next-reviewer/design/verify_design_contracts.py) | Deterministic stdlib audit script checking Git tree preservation, `F1` structural PDF admission on `F2` dev targets, `Q0`/`F2`/`B0` pins, `dev`-only schema properties, Markdown links, and hard holdout path refusal | `SafeRepoReader`, `check_f1_pdf_structural_profile`, `main` |

Post-deliverable evidence and report metadata committed separately on `review/wp-0006-0007-next-tracks`:

- Added (`dc296f3a3bc8041bc2eb62377c440a3879d1bcc8`): [verification-receipt.json](../../../reviews/WP-0006/eld-next-reviewer/design/verification-receipt.json) — post-freeze JSON receipt produced by executing frozen `verify_design_contracts.py` at `HEAD` `7eae6de27d21bd41558611f95116e13cbd0f6b92`.
- Added (this commit): `docs/agent-reports/eld-next-reviewer/WP-0006/002_2026-11-16_review_eld-next-reviewer.md` — canonical `WP-0006 /002` review report (its own publication SHA is verified on `origin` after push and returned in handoff).
- Ignored scratch file in owned worktree: `.scratch/pre-freeze-check.json` (untracked, `.gitignore` L25).
- External effects: normal non-force push of `review/wp-0006-0007-next-tracks` to `origin`; zero database, GPU, network-download, or global configuration changes.

## Decisions and rationale

Full source-pinned rationale is recorded in [README.md](../../../reviews/WP-0006/eld-next-reviewer/design/README.md) Sections 2–3:

1. **Why `F2-local-extraction.md` is `accepted` without a design-rewrite roundtrip:**
   Every blocking architectural, durability, security, process-supervision, and provenance invariant is explicitly and Soundly specified in `F2-local-extraction.md`: distinct `ProcessingJob` vs. `ExecutionAttempt` with monotonic fencing tokens and a unique accepted-result boundary (`L19`), short Read Committed transactions never spanning OCR (`L23`), Windows child + CUDA worker tracking/cleanup before post-restart `interrupted` retryability (`L23`), read-only reuse of `C:\Users\jackg\eLedgerCare-Q0\WP-0005` with exact 18-object + notice + 32-wheel + `torchvision-local-sha256-TOFU` verification and `infer_multi` kwargs (`L29–31`), strict HTML/script escaping without `eval` (`L9, L31`), forward migration + least-privilege runtime grants (`L25, F2-07`), and disjoint loopback/storage resources (`L37–39`). Direct byte checks confirm both named `dev` acceptance fixtures (`SYN-WO-01-v1-raster300.pdf` and `SYN-MP-01-v0-clean.pdf`) pass `PdfPigAdmission.cs` structural preconditions (`%PDF-1.4`, valid `startxref -> xref`, `%%EOF`).
2. **Consolidated `F2` release action & implementation checkpoints (`F2-KR-01`, `F2-BIC-01`..`04`):**
   - `F2-KR-01`: In accepted `F1`, `PostgresFixture.cs` (L56) and `prepare-database.ps1` (L57) execute `deploy/dev/database/grant-runtime.sql`, and `workers/ocr/README.md` (L1–12) still describes `F2` as unimplemented. Because `WP-0006-eld-f2-implementer.md` (L7) currently lists `workers/local_ocr/` without `deploy/dev/**` or `workers/ocr/README.md`, `eld-coordinator` should include `deploy/dev/**` and `workers/ocr/README.md` when binding the `WP-0006 /003` implementation release (keeping `extraction_results` `SELECT, INSERT` only for `eledgercare_app`).
   - `F2-BIC-01`..`04`: Remove `evaluation/product-smoke/` references and `5180`/`4200` hardcoding in `web/e2e/owned-api.ts` and `web/playwright.config.ts`; embed self-contained resolved 32-package + 18-object manifests in `workers/local_ocr/` (avoiding `dependency-lock.json`'s `git cat-file blob` indirection into `qualification/`); capture `finish_reason`, `num_pages_out`, `expected_pages`, `prompt_token_ids`, forward-step progress, and save/eval tripwires via Python 3.12 `sys.monitoring` around `infer` (since `infer_multi` returns only `(text, len(token_ids))` and `eval_mode=False` streams to `stdout`), bound `page_count == 2` timeout (`<= 3600s`), and enable `1..3` pages by default; separate initial `POST .../extraction` replay from explicit `failed`/`interrupted` retry and bind a Windows Job Object (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`) plus `(pid, startTimeUtc)` tracking for both venv launcher and worker; and enforce escaped text-only rendering of native `<PAGE><BLOCK>...<FORK>` and `<table>` strings.
3. **Why `B0-vanilla-accuracy-baseline.md` is `provisional-accepted` pending `WP-0007 /003` (`B0-PBIC-01`..`04`):**
   Corpus counts (`26` PDFs / `40` pages; `13/19` `dev`; `13/21` `eval_holdout`; page-count categories `{1, 3}`), Q0 runtime/guard parity (`~4,838s` projected single-session ceiling vs. `21,600s` cap), denominator rules, and non-equivalence to `E1`–`E3` paired timing match accepted `WP-0004`/`WP-0005`. Canonical `WP-0007 /003` will verify that `eld-rd-astra`'s Stage A implementation resolves four concrete `dev`-schema realities before test access: (`B0-PBIC-01`) separating HTML `<table>` entity decoding and deterministic ground-truth-independent type canonicalization (`boolean_mark`, `currency_usd`, `decimal_2` `qty_unit`, `rate_percent`, 3-line address blocks) from NFC/whitespace comparison; (`B0-PBIC-02`) extracting candidate predictions without `expected`/`source` inputs and aligning to `label_printed`/table headers without inspecting `expected.printed_text`/`normalized_value` (handling cross-family label variations); (`B0-PBIC-03`) freezing a deterministic reading-order text reference and boilerplate boundary given that `expected/*_expected.json` has no top-level `document_text` key (keeping holdout `sources/*.json` unread until `/003` freeze); and (`B0-PBIC-04`) requiring both excluded `dev` warm-ups (`1p` and `3p`) after every cold load and predeclaring reviewer sentinels before Stage B runs.

## Verification

| Check / exact command or tool operation | Environment and revision | Actual result | Evidence location |
| --- | --- | --- | --- |
| `git status --short --branch`, `git rev-parse HEAD`, `git show --stat efa9cb98... c08d50e2...`, `git ls-tree efa9cb98... ...` | `eld-next-reviewer` worktree on `review/wp-0006-0007-next-tracks` at `c08d50e204395e60a88ce25f70e25bd29b97b8c6` | Clean branch confirmed; exact 8-path `efa9cb98...` candidate and 2-path `c08d50e2...` `/001` report commits verified | [verification-receipt.json](../../../reviews/WP-0006/eld-next-reviewer/design/verification-receipt.json) |
| Direct primary-source inspection of `src/**`, `web/**`, `tests/**`, `deploy/**`, `workers/ocr/README.md`, `qualification/q0/harness/**`, `hf-modeling_unlimitedocr.py.txt`, `corpus-manifest.json`, `02-ranked-experiment-backlog.md`, and `dev` (`F01,F02,F04,F07`) records | Read-only file inspection in `eld-next-reviewer` worktree at `c08d50e204395e60a88ce25f70e25bd29b97b8c6` | Confirmed `F1`/`Q0`/corpus invariants, identified `F2-KR-01`, `F2-BIC-01..04`, and `B0-PBIC-01..04`, zero holdout files read | [README.md](../../../reviews/WP-0006/eld-next-reviewer/design/README.md) |
| `python "...\docs\reviews\WP-0006\eld-next-reviewer\design\verify_design_contracts.py" --output "...\docs\reviews\WP-0006\eld-next-reviewer\design\verification-receipt.json"` | CPython `3.12.10` against frozen deliverable `HEAD` `7eae6de27d21bd41558611f95116e13cbd0f6b92` (helper SHA-256 `c240a63edfd5c997ee1e54ceee21b8f4fa45bf9764c152ab4b6cd511571f2e02`) | Exit `0`; `all_assertions_passed=true` (`15/15` assertions, `13` `dev` expected + `4` `dev` source JSONs audited, `0` holdout paths opened, `14/14` local Markdown links resolved) | [verification-receipt.json](../../../reviews/WP-0006/eld-next-reviewer/design/verification-receipt.json) |
| `git diff --cached --check` on deliverable `7eae6de2...`, evidence `dc296f3a...`, and this canonical `/002` report | Git `2.55.0.windows.1` on `review/wp-0006-0007-next-tracks` | Exit `0`, zero whitespace or line-ending warnings | Git commit history on `review/wp-0006-0007-next-tracks` |

Checks **not** run and why (prohibited in Phase 1 by [WP-0006-0007-eld-next-reviewer.md](../../../kickoffs/WP-0006-0007-eld-next-reviewer.md)):

- No `.NET` build/test, Angular/Playwright execution, or PostgreSQL cluster launch/migration (scheduled for `WP-0006 /004` on `5290/4310/55435` after `/003` candidate freeze).
- No `B0` scorer/runner CPU execution or sentinel selection (`eld-rd-astra` `/002` candidate not yet published; scheduled for `WP-0007 /003`).
- No holdout (`F03`, `F05`, `F06`, `F08`) PDF/source/expected inspection (strictly forbidden before `/003` scorer freeze).
- No GPU lease, model load, or Python venv execution.

## Review map

- Reviewed root design candidate: `efa9cb986711f82a886f917e68142a7a59319bba` ([F2-local-extraction.md](../../../design/F2-local-extraction.md) blob `8ce0c854baa889ea090d5b941d6aba0de34a5bde`; [B0-vanilla-accuracy-baseline.md](../../../design/B0-vanilla-accuracy-baseline.md) blob `05c9ff231ae250ca96488132c53bdaf218f200f6`; [WP-0006-eld-f2-implementer.md](../../../kickoffs/WP-0006-eld-f2-implementer.md) blob `918ff5e2f762fa4a9e114252bf1eb29e134106db`; [WP-0007-eld-rd-astra.md](../../../kickoffs/WP-0007-eld-rd-astra.md) blob `56757732e5c3ce2521c213b8496f7276d40e13ef`)
- Reviewed coordinator `/001` reports (`c08d50e204395e60a88ce25f70e25bd29b97b8c6`): [WP-0006 /001](../../eld-coordinator/WP-0006/001_2026-11-16_design_eld-coordinator.md) and [WP-0007 /001](../../eld-coordinator/WP-0007/001_2026-11-16_design_eld-coordinator.md)
- Phase 1 review deliverable (`7eae6de27d21bd41558611f95116e13cbd0f6b92`): [README.md](../../../reviews/WP-0006/eld-next-reviewer/design/README.md) and [verify_design_contracts.py](../../../reviews/WP-0006/eld-next-reviewer/design/verify_design_contracts.py)
- Post-freeze verification evidence (`dc296f3a3bc8041bc2eb62377c440a3879d1bcc8`): [verification-receipt.json](../../../reviews/WP-0006/eld-next-reviewer/design/verification-receipt.json)

## Risks, disagreements, and unfinished work

- **Substantive contract disagreements:** None (`0` blocking design defects; no escalation required).
- **Outstanding phase gates:**
  1. `eld-coordinator` binds `WP-0006 /003` product implementation release (including `F2-KR-01` path ownership for `deploy/dev/**` and `workers/ocr/README.md`); GPU runtime remains unreleased until exact `F2` candidate and exclusive lease binding, followed by independent `WP-0006 /004` verification.
  2. `B0` remains **provisionally** accepted at contract level only; holdout (`F03`, `F05`, `F06`, `F08`) data and all GPU model runs remain held until `eld-rd-astra` publishes `WP-0007 /002` and `eld-next-reviewer` completes canonical `WP-0007 /003` source/CPU review (`B0-PBIC-01`..`04`) and predeclares sentinels.

## Handoff

- **Disposition:** `WP-0006 /002` F2 design **`accepted`** (`efa9cb986711f82a886f917e68142a7a59319bba`); `WP-0007 /001` B0 design **`provisional-accepted`** pending canonical `WP-0007 /003` scorer/protocol/runner gate.
- **Next owner:** `eld-coordinator` (update `INDEX.md`/`CURRENT.md`, bind `WP-0006 /003` implementation release with `F2-KR-01`, and route `B0-PBIC-01`..`04` to `WP-0007 /002`–`/003`).
- **Branch:** `review/wp-0006-0007-next-tracks`
- **Base SHA:** `c08d50e204395e60a88ce25f70e25bd29b97b8c6` (packet base `8e80a42c29c0fc27a4af6348cfb1ec22cab3764d`)
- **Reviewed design candidate SHA:** `efa9cb986711f82a886f917e68142a7a59319bba`
- **Deliverable SHA:** `7eae6de27d21bd41558611f95116e13cbd0f6b92`
- **Post-freeze verification evidence SHA:** `dc296f3a3bc8041bc2eb62377c440a3879d1bcc8`
- **Report path:** `docs/agent-reports/eld-next-reviewer/WP-0006/002_2026-11-16_review_eld-next-reviewer.md`
- **Publication receipt:** Committed as a separate single-file metadata commit after `dc296f3a3bc8041bc2eb62377c440a3879d1bcc8`, pushed without force on `review/wp-0006-0007-next-tracks`, verified against `origin/review/wp-0006-0007-next-tracks` via `git ls-remote`, and its full publication SHA is supplied in the handoff response to `eld-coordinator`.
