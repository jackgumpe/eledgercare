# WP-0015 / 003 — Scanned packet custody and CPU scorer verification

| Item | Record |
| --- | --- |
| Author and publisher | eld-eval-custodian, fresh native Codex session delegated by eld-coordinator. Concrete served backend and applied effort were unexposed. Fresh Codex preference was xhigh. |
| Reservation and category | [WP-0015 / 003, verification](../../../../INDEX.md#wp-0015-scanned-packet-ocr-architecture-trial) |
| Canonical path | `docs/agent-reports/eld-eval-custodian/WP-0015/003_2026-11-18_verification_eld-eval-custodian.md` |
| Published UTC | 2026-11-18T03:29:53Z |
| Repository, branch and worktree | jackgumpe/eledgercare, `evaluation/wp-0015-packets`, `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/speed-custody` |
| Assignment / product base | `c4d7734d0be6302e667d290698bc671631c71ce9` / `178ce88b80384fc7def703d9e78769427d9b2528` |
| Frozen deliverables | `7598bf4155452c4a1294b7421595009d39ea1bc9`, [base-to-freeze diff](https://github.com/jackgumpe/eledgercare/compare/c4d7734d0be6302e667d290698bc671631c71ce9...7598bf4155452c4a1294b7421595009d39ea1bc9) |
| Prior report | First custody report for this lane. The [assignment](../../../coordination/WP-0015/assignment.md) binds independent author, custody and reviewer roles. |
| Status and next owners | Ready for review. From the exact freeze, eld-coordinator can bind development timing and a subsequent named reviewer lease. Eld-rd-reviewer owns independent model replay. |

## Outcome

The shared dev set contains six fresh pages across short prose, a dense work order and a four-page boundary case. Its actual PDFium rasters, truths and scoring protocol were frozen before the coordinator released trials. Three further synthetic families totaling 124 pages are reserved outside Git behind separate input and scoring keys. The four-page H replay fits well within the planning allowance under historical timing assumptions. Independent Opus model replay remains pending.

The evaluator reports full page-local CER, table-cell counts and source-localized critical errors. Boundaries include the PDF identity, original page number, exact cell position or line box and output order. It charges duplicates, missing pages and extra grid entries, including explicit versus absent empty cells. A claimed whole-document completion also needs a real durable-write receipt from the timing harness.

## Artifacts and effects

All file names in the following rows are relative to [the evaluation directory](../../../evaluation/WP-0015/) unless a different root is shown.

| Added at the freeze | Contents |
| --- | --- |
| `README.md`, `score.py`, `check_score.py` | Prediction format, original-PDF geometry, clock/evidence obligations, per-family scoring, matched delta gates and adversarial control cases. |
| `development.py`, `audit.py` | Deterministic development authoring and independent PDFium characterization of dimensions, text layer, embedded image, blank page, RGB bytes and occupied/empty truth boxes. |
| `dev/{short,dense,boundary}/{source.pdf,truth.json,rasters.json}` | Nine case files covering all combinations. Each control and potential contender gets the same original document. |
| `commitments.json`, `release.ps1`, `cpu-counts.json` | Plaintext and ciphertext digests, separate authenticated stage release, frozen counts and truth-as-prediction CPU positive controls. |
| External `C:/Users/jackg/eLedgerCare-Speed/WP-0015/custody/` | Private generation, sealed AES-256-GCM payloads, CurrentUser DPAPI-wrapped independent keys, wrapped generation seed and layout generator, development replay, CPU receipts. No private raw pages or answers were retained as plaintext following the self-test. |
| After the source commit | This canonical report and [verification.json](../../../evaluation/WP-0015/verification.json), containing the executed control and hash checks. |

## Verification on this host

| Executed check | Result |
| --- | --- |
| Q0 Python 3.12.10 with `-B development.py <empty-dir>` and `-B audit.py <dir> --out <new-file>` for each dev family | All nine resulting PDFs, truth files and raster manifests exactly matched the frozen files. PDFium 159.0.8149.0, pypdfium2 5.15.2, Pillow 13.0.0. The preview showed visible table borders and the late release beyond the blank third boundary page. |
| CPU PDFium audit of all six actual synthetic PDFs before sealing | 130 image-only pages with one image and zero text-layer characters each. All generated ink regions and all deliberately empty cells passed the crop check. The 300-DPI raw RGB hashes are bound in the individual manifests. |
| `python -B docs/evaluation/WP-0015/check_score.py` | 26/26 positive and adversarial controls passed. Rows swapped while page text stayed identical caused two critical errors. A missing blank page failed completion. A foreign page cost full deletions and insertions. A repeated row removal lost cell credit. |
| CPU scorer exact-threshold checks at the frozen revision | +0.010 CER and −0.020 cell accuracy were inclusive. Separately exceeding either limit failed. One-pass perfect grid and direct-span controls agreed on all six families and denominators. An entirely non-tabular family reports null cell accuracy. |
| Existing `local_ocr.pdf_render.read_and_render_pdf` from the unchanged product tree on dev short and dense | Its PDF identity, source ordinal, image dimensions and raw RGB hashes matched the evaluation renderer. Research read the four-page source directly in PDFium because the product entry limits attempts to three pages. No torch import or model call was required. |
| Six custodian-private `release.ps1` executions before candidate timing, then post-freeze ciphertext SHA checks | All six input/scoring bundles authenticated. All nine extracted members matched their separate commitments. All six encrypted hashes revalidated after the freeze. The coordinator and trial authors received only public metadata. |
| `git diff --cached --check`, normal `git push origin HEAD:refs/heads/evaluation/wp-0015-packets`, `git ls-remote origin refs/heads/evaluation/wp-0015-packets` | Clean diff check and exact remote freeze `7598bf4155452c4a1294b7421595009d39ea1bc9` confirmed before report publication. |

During authoring the first PDF audit stopped on the pinned library's unsupported text-page context-manager protocol. The published audit uses explicit close operations. All six audits then passed. The six byte-level validations and CPU scoring controls are custodian checks of custodian-authored material. They establish fixture integrity and scoring behavior rather than model outcomes.

## Review and handoff

[The protocol](../../../evaluation/WP-0015/README.md) specifies how to repeat the checks, the clock and threshold distinction, exact-mode obligations and the named two-stage replay. Predictions must retain original-PDF ordinal and provenance. Reported table-block geometry plus ordinal can trace to the right cell position but supplies no independently measured per-cell rectangle. Use the actual geometry-bearing output when claiming direct span localization.

The historical short/dense timing proxy estimates about 4.6 minutes per matched representative pair, or 9.3 minutes for two pairs. The two 60-page families individually project to 58.4 and 69.6 minutes per pair before overhead. These are scheduling estimates. No GPU, inference, timed prototype, durable OCR trial, product Extract-to-search, reviewer unseal or 60-page inference was executed by this author. The first protected reviewer transfer awaits an exact named coordinator release. The two scale families remain reserved separately. Upstream authors, original briefs and independent reviewer retain their own attributions.
