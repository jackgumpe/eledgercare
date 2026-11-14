# WP-0004 / 002: Independent Carbon R&D source assessment, hypotheses, and corpus plan

- Report path: `docs/agent-reports/eld-rd-carbon/WP-0004/002_2026-11-14_research_eld-rd-carbon.md`
- Sequence reservation: Coordinator `INDEX.md` (`WP-0004 / 002`, inspected on `coordination/bootstrap` @ `11926d7021044450aa44a44a893575d0eb98d442`) and `docs/kickoffs/WP-0004-eld-rd-carbon.md` (@ `e66321dc1c2506d68cb32758d73ee97e78476c61`)
- Category: research
- Author / agent ID: `eld-rd-carbon`
- Actual model / effort: Gemini 4 Carbon (High effort; backend checkpoint ID not exposed)
- Execution environment: CLI (Antigravity CLI on Windows x64 25H2 build `26200.9974`, PowerShell, conversation/session `74513d00-ee88-4e85-a554-120908615b21`; Python `3.12.10` stdlib used read-only for source/PDF/`Decimal` inspection)
- Published by: `eld-rd-carbon` (self-published on owned branch using existing local Git author configuration unchanged)
- Timestamp: 2026-11-14T17:16:00Z
- Repository / branch: `https://github.com/jackgumpe/eledgercare` (`PRIVATE`) / `research/wp-0004-carbon` (owned worktree `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-rd-carbon`)
- Base revision: `35f6090a9b2e16c7645b56f34b104eb3126d5c90`
- Deliverable revision: `39f475c1ce5b51c5b03b024fb39a74632e1a5eba`
- Previous report: none (initial report by `eld-rd-carbon` in `WP-0004`)
- Related or reviewed reports: `WP-0001 / 001` seed (`https://github.com/jackgumpe/eledgercare/blob/287183ceec005195d03e83649a3f91c41ae4fcd1/docs/agent-reports/eld-coordinator/WP-0001/001_2026-11-14_verification_eld-coordinator.md`, deliverable `35f6090a9b2e16c7645b56f34b104eb3126d5c90`). `WP-0004 / 001` (`eld-rd-astra`) was **not read or inspected** prior to publishing this assessment in order to preserve required initial independence.
- Status: ready-for-review
- Next owner: `eld-coordinator`

## Summary

Completed `eld-rd-carbon`'s independent primary-source R&D assessment on `research/wp-0004-carbon` from base `35f6090a9b2e16c7645b56f34b104eb3126d5c90`, freezing deliverable commit `39f475c1ce5b51c5b03b024fb39a74632e1a5eba` prior to authoring this report. All upstream model/code/paper artifacts (`baidu/Unlimited-OCR-2` @ `0480966938291445591f69f08a13b041c073a96a` and bootstrap pin `38d328853c00086837c00308e1cd35dc77bbb96c`; `baidu/Unlimited-OCR` @ `64e6f066023b305ab03860603a9cf358a8b70148`), Windows `win_amd64` PyPI package wheels/licenses, and both Microsoft Form Recognizer public PDF candidates (`4a3c5ca76318feb3f7cfb109e1f79c542eb14d01`) were inspected read-only without downloading `.safetensors` weights, installing packages, starting services, or acquiring a GPU lease.

This report represents **author research and verification only** (`ready-for-review`), not independent acceptance. Directory owner (`eld-rd-carbon`), filename suffix (`eld-rd-carbon`), and author metadata agree, and `eld-rd-carbon` remains distinct from the product reviewer role (`eld-reviewer`). Unfinished packet-level work—specifically the single Astra/Carbon exchange (`WP-0004 / 003`), deterministic synthetic corpus materialization and joint backlog reconciliation (`WP-0004 / 004`), and non-author verification by `eld-rd-reviewer` (`WP-0004 / 005`)—remains held per coordinator routing.

## Objective and acceptance criteria

Per `docs/kickoffs/WP-0004-eld-rd-carbon.md` and `docs/inputs/bootstrap-kit/03-RD-BRIEF.md`:

1. **Preserve initial independence:** Produce Carbon's first assessment without reading `eld-rd-astra`'s branch (`research/wp-0004-astra`), worktree, or report (`WP-0004 / 001`).
2. **Pin primary sources and applicability limits:** Inspect and pin exact commits, Git blob OIDs, SHA-256 digests, licenses, and Windows/RTX 5070 Ti applicability boundaries for `baidu/Unlimited-OCR-2`, `baidu/Unlimited-OCR`, relevant Python runtime dependencies, local preflight intake (`04-ENVIRONMENT-RECEIPT.txt`), and public corpus candidates.
3. **Separate runtime qualification from optional R&D:** Distinguish durable document intake (Feature 1, zero OCR dependency) and vanilla local OCR runtime qualification (Feature 2 engineering prerequisite) from optional R&D improvement hypotheses (`WP-0004`), acknowledging that no accepted local OCR baseline exists yet.
4. **Propose at most three falsifiable single-variable hypotheses:** Challenge needless upstream complexity and confounding, then specify at most three hypothesis cards with vanilla baseline, single change, controlled variables, confounders, explicit metric/denominator, failure signal, and rejection criterion.
5. **Design deterministic 8-family synthetic corpus and audit public candidates:** Define 8 fictional property-maintenance families (`3` single-page work orders, `3` single-page invoices, `2` multi-page documents), exact source-first `Decimal` (`ROUND_HALF_UP`) accounting rules, leak-free family-level `dev`/`eval_holdout` split, provenance manifest schema, and primary-source notice/ground-truth audit of `sample-invoice.pdf` and `Invoice-6.pdf` without admitting public samples or trusting adjacent model JSON as ground truth.
6. **Maintain strict scope and two-step Git publication:** Edit only `research/carbon/**` and this report on `research/wp-0004-carbon`; commit deliverables first (`39f475c1ce5b51c5b03b024fb39a74632e1a5eba`), commit this report separately afterward, push without `--force`, and verify remote refs.

## Change inventory

### Deliverable diff (`35f6090a9b2e16c7645b56f34b104eb3126d5c90..39f475c1ce5b51c5b03b024fb39a74632e1a5eba`)

| Action | Exact path | What changed and why | Relevant symbols / sections |
| --- | --- | --- | --- |
| Added | `research/carbon/README.md` | Added Carbon R&D index, independence attestation, deliverable map, and boundary summary (`2,965` B, Git blob `be1c32c31f25ddbb38b1f311e60d2184f4a7e22e`). | `Independence Attestation`, `Deliverable Map`, `Boundary with Held Future Work` |
| Added | `research/carbon/01-sources-and-qualification.md` | Added pinned primary-source register with full commit/blob/SHA-256 metadata, license/platform applicability limits, and 5-gate separation of local OCR runtime qualification from optional R&D (`17,854` B, Git blob `3b945252e88e5d1c85b065fafe471b2e4d9934b4`). | `§1.1` (`baidu/Unlimited-OCR-2` & `baidu/Unlimited-OCR`), `§1.2` (Azure candidates, PyPI, `04-ENVIRONMENT-RECEIPT.txt`), `§2.1–2.3` (`eval()`, `PyMuPDF` AGPL-3.0, `_forward_dense`, WDDM VRAM, `65.70 GiB` `C:`) |
| Added | `research/carbon/02-hypotheses.md` | Added rejection analysis for SGLang page-windowing, bundled image filters, and pre-baseline training, plus 3 single-variable falsifiable hypothesis cards (`20,217` B, Git blob `f924a5fc4d76faf2d4770bea4eaa0265735a1194`). | `§1` (Rejected complexity), `H-C1` (Born-digital PDF text-layer gate), `H-C2` (`infer` `crop_mode=True` gundam vs `infer_multi` `crop_mode=False`), `H-C3` (Conditional non-binarizing deskew `\|theta_hat\| >= 1.0 deg`) |
| Added | `research/carbon/03-corpus-and-candidates.md` | Added 8-family synthetic maintenance corpus design, source-first `Decimal` (`ROUND_HALF_UP`) accounting invariants, `4 dev / 4 eval_holdout` family split, manifest schema, and byte/font/JSON audit of the two unadmitted Microsoft public candidates (`20,542` B, Git blob `e217b26e56c356aee4b9e15acbd6ebc26ad7a31e`). | `§1` (`F01`–`F08` / `SYN-WO-01..03`, `SYN-INV-01..03`, `SYN-MP-01..02`), `§2` (`ROUND_HALF_UP` & Gates A/B), `§3` (`dev`/`eval_holdout` & manifest schema), `§4` (`sample-invoice.pdf` & `Invoice-6.pdf` audit) |

### Report metadata committed separately after deliverable freeze

- Added `docs/agent-reports/eld-rd-carbon/WP-0004/002_2026-11-14_research_eld-rd-carbon.md` in a separate commit atop `39f475c1ce5b51c5b03b024fb39a74632e1a5eba`. This report records `39f475c1ce5b51c5b03b024fb39a74632e1a5eba` and does not claim to contain its own publication SHA. `INDEX.md` and `CURRENT.md` were not modified.

### External queries and persistence status

- **Read-only HTTPS queries (no external state modified):** Hugging Face API & raw text/code/PDF objects for `baidu/Unlimited-OCR-2` (`38d328853c00086837c00308e1cd35dc77bbb96c` and `0480966938291445591f69f08a13b041c073a96a`; `.safetensors` and `.whl` inspected via tree/LFS metadata only, never downloaded); GitHub API & raw text files for `baidu/Unlimited-OCR` (`64e6f066023b305ab03860603a9cf358a8b70148`) and `Azure-Samples/cognitive-services-REST-api-samples` (`4a3c5ca76318feb3f7cfb109e1f79c542eb14d01`); PyPI JSON metadata (`pypi.org/pypi/<pkg>[/<ver>]/json`).
- **Local scratch persistence:** Small read-only reference files and stdlib inspection scripts (`inspect_sources.py`, `verify_deliverables.py`) were written solely to Antigravity session scratch (`C:\Users\jackg\.gemini\antigravity-cli\brain\74513d00-ee88-4e85-a554-120908615b21\scratch\`) outside all Git repositories. Zero Python packages, system libraries, services, databases, or other worktrees were modified.
- **Remote Git persistence:** Pushed owned branch `research/wp-0004-carbon` to private remote `origin` (`https://github.com/jackgumpe/eledgercare.git`) without `--force`.

## Decisions and rationale

1. **Refresh upstream pin from `38d32885...` to `0480966938291445591f69f08a13b041c073a96a` while preserving provenance:** Tree diffing proved that all `.safetensors` weight shards (`6,688,305,576` B / `6.23 GiB`), `config.json`, and all `.py` modeling files have **identical Git blob OIDs** between `38d32885...` and `04809669...`, whereas `38d32885...`'s `README.md` contained unresolved merge conflict markers (`<<<<<<< HEAD`) repaired in `04809669...` alongside the `Unlimited-OCR-2.pdf` technical report (`arXiv:2610.39308`).
2. **Reject SGLang and cross-chunk KV-reuse (`W=10` pages) for native Windows scope:** Upstream's SGLang setup requires an unreleased fork wheel (`sglang-0.5.20.dev13+g75b9b06b02`), official `sglang` and `triton` publish zero `win_amd64` wheels on PyPI, and server transport relies on Linux `/dev/shm`. Mathematically, Algorithm 1 (`Unlimited-OCR-2.pdf` §3.4) sets chunk count $K=1$ whenever document length $N \le W$ (`W=10`), making page-window scheduling a strict no-op on 1–6 page maintenance paperwork while shrinking $W$ breaks cross-page table merging (`README.md` L176).
3. **Separate five engineering qualification gates from optional R&D (`01-sources-and-qualification.md` §2.2):** Source inspection uncovered five concrete blockers that belong to baseline runtime qualification rather than R&D hypotheses: (a) `65.70 GiB` free space on `C:` vs `~12–16 GiB` model+venv+cache footprint; (b) PyPI `torch==2.13.0` on `win_amd64` (`116.4 MiB`) is CPU-only (`cuda-toolkit` gated to Linux), requiring an explicit Windows CUDA wheel index supporting Blackwell RTX 5070 Ti (`sm_120`); (c) without `triton`, `dash_attention.py` L1208–1260 falls back to chunked SDPA `_forward_dense` (`q_chunk=2048`), whose peak VRAM under 16 GiB WDDM (`1,155 MiB` desktop/IDE baseline) is unmeasured; (d) `_sparse_base_impl.py` carries an `Apache-2.0` header and imports private `transformers==4.52.1` symbols (`_prepare_4d_causal_attention_mask`), requiring pinned `transformers==4.52.1`; and (e) `modeling_unlimitedocr.py` L120 runs unsafe `eval(ref_text[2])` when `save_results=True` (must enforce `save_results=False`) and upstream's `PyMuPDF` (`1.27.2.2`) is **GNU AGPL-3.0** (replace with `pypdfium2` `Apache-2.0/BSD-3-Clause` and `pypdf` `BSD-3-Clause`).
4. **Prioritize three unconfounded, falsifiable hypotheses (`02-hypotheses.md`):**
   - **`H-C1` (Deterministic born-digital PDF text-layer gate):** Routes pure vector PDFs (`0` `U+FFFD`/unmapped glyphs, `<15%` image area) to deterministic CPU coordinate extraction while sending every scan/hybrid page to VLM OCR, recording `source_mode` explicitly so vector pass-through is never conflated with OCR accuracy.
   - **`H-C2` (Multi-page `crop_mode=True` gundam tiling vs. `infer_multi`'s silent `crop_mode=False`):** Exposes and tests a direct upstream discrepancy—`modeling_unlimitedocr.py`'s `infer_multi` (`L1117`) forces `crop_mode=False` (`273` tokens/page, ~93 DPI), whereas Baidu's benchmark script `infer.py` (`L74`) runs multi-page evaluation with `crop_mode=True` (`640x640` local crops)—against the 16 GiB WDDM `_forward_dense` memory ceiling (`14,500 MiB` rejection threshold).
   - **`H-C3` (Conditional non-binarizing deskew gate $|\hat{\theta}| \ge 1.0^\circ$):** Isolates geometric rotation recovery for axis-aligned $640\times640$ gundam tiles without destructive binarization/CLAHE, guaranteeing byte-identical pass-through (`0` pixel diffs) on clean `0.0°` pages.
5. **Keep public candidates unadmitted and enforce source-first `Decimal` ground truth (`03-corpus-and-candidates.md`):** Raw stream and visual inspection proved `sample-invoice-output.json` hallucinates `ServiceStartDate` (`10/14/2019`) and `ServiceEndDate` (`11/14/2019`) absent from `sample-invoice.pdf` (`1e7c93c6...`), omits `Items`, and `sample-invoice.pdf` itself prints `Qty 1 * Unit Price 1 = $100.00`; meanwhile `analyze-result-invoice-6.pdf.json` labels only 6 custom demo fields and omits vendor, date, address, subtotal, `3%` tax, `$10,686.25` total, and line items. Both remain `candidate_unadmitted` pending `WP-0004 / 004` reconciliation.

## Verification

### Executed read-only and pre-commit checks

| Check / exact command or tool operation | Environment and revision | Actual result | Evidence location |
| --- | --- | --- | --- |
| Worktree, branch, and base SHA check (`git status`, `git rev-parse HEAD`, `git branch --show-current`) | Windows x64 PowerShell, `eld-rd-carbon` worktree @ `35f6090a9b2e16c7645b56f34b104eb3126d5c90` | Clean worktree on `research/wp-0004-carbon` at exact base `35f6090a9b2e16c7645b56f34b104eb3126d5c90`. | Session transcript; `research/carbon/README.md` |
| Read-only Hugging Face API & source inspection (`Invoke-RestMethod` on `huggingface.co/api/models/baidu/Unlimited-OCR-2/commits/main`, `/tree/38d32885...`, `/tree/04809669...`, plus text/code/PDF downloads) | Windows x64 PowerShell, `2026-11-14` UTC | Verified identical weight LFS SHA-256 (`4c40b740...`, `9490b82f...`, `6,688,305,576` B) & `.py` OIDs across `38d32885...` and `04809669...`; verified `eval()` at `modeling_unlimitedocr.py:120`, `infer_multi` `crop_mode=False` at `:1117`, `_forward_dense` fallback at `dash_attention.py:1208-1260`, and Apache-2.0 header in `_sparse_base_impl.py:2-19`. | `research/carbon/01-sources-and-qualification.md` §1.1, §2.2 |
| Read-only GitHub API & source fetch for `baidu/Unlimited-OCR` @ `64e6f066023b305ab03860603a9cf358a8b70148` and `Azure-Samples/cognitive-services-REST-api-samples` @ `4a3c5ca76318feb3f7cfb109e1f79c542eb14d01` | Windows x64 PowerShell + `git hash-object` + `Get-FileHash -Algorithm SHA256` | Verified MIT licenses, `infer.py:74` (`crop_mode=True`), `process_unlimitedOCR2.py` `<PAGE><BLOCK>` parser, and exact Git blob OIDs (`1e7c93c6...`, `1c24566e...`, `b5f17c02...`) and SHA-256 digests (`c2ce1edc...`, `aaaffcf6...`, `7bfe2b01...`). | `research/carbon/01-sources-and-qualification.md` §1.1–1.2; `03-corpus-and-candidates.md` §4 |
| Raw PDF stream/font/XMP decompression and visual page audit (`python inspect_sources.py` + `read_file` on both candidate PDFs and adjacent JSONs) | Python `3.12.10` stdlib (`zlib`, `re`, `hashlib`, `json`); note two earlier inline `python -c` attempts failed on PowerShell quote/`<` parsing before moving to `inspect_sources.py` (`exit 0`) | Confirmed embedded Microsoft/Monotype font EULAs, absent `10/14/2019` & `11/14/2019` strings in `sample-invoice.pdf` `BT..ET` stream vs `sample-invoice-output.json`, printed `1 * 1 = $100.00` defect, and 6-field custom schema omissions in `analyze-result-invoice-6.pdf.json`. | `research/carbon/03-corpus-and-candidates.md` §4.1–4.2 |
| PyPI platform/license metadata query (`Invoke-RestMethod https://pypi.org/pypi/<pkg>[/<ver>]/json`) | Windows x64 PowerShell (`2026-11-14` UTC); note raw HTML index probes to `download.pytorch.org/whl/cu128..cu135/torch/` timed out / 403'd and were superseded by deterministic PyPI JSON metadata | Confirmed PyPI `torch==2.13.0` `win_amd64` wheel (`116.4 MiB`) is CPU-only, `sglang==0.5.23` and `triton==3.9.0` have zero `win_amd64` wheels, `PyMuPDF==1.27.2.2` is `GNU AGPL-3.0`, and `pypdfium2==5.15.2` / `pypdf==7.1.0` provide permissive `win_amd64`/pure-Python wheels. | `research/carbon/01-sources-and-qualification.md` §1.2, §2.2 |
| Deterministic `Decimal` (`ROUND_HALF_UP`) invariant & deliverable hash check (`python verify_deliverables.py`) | Python `3.12.10` stdlib (`decimal`, `hashlib`, `subprocess`) against `research/carbon/*.md` | `ALL_CHECKS_PASSED` (`exit 0`): validated mixed-tax, fractional-hour/percentage-discount, negative-credit/non-taxable-fee, `Invoice-6.pdf`, and `sample-invoice.pdf` arithmetic equations plus all 4 deliverable blob OIDs and SHA-256 digests. | `research/carbon/03-corpus-and-candidates.md` §2.2, §4.2 |
| Deliverable commit verification (`git diff --name-status 35f6090a9b2e16c7645b56f34b104eb3126d5c90..39f475c1ce5b51c5b03b024fb39a74632e1a5eba` & `git ls-tree -r -l HEAD research/carbon`) | Git in `eld-rd-carbon` worktree @ `39f475c1ce5b51c5b03b024fb39a74632e1a5eba` | Confirmed exactly 4 added files (`336` insertions) under `research/carbon/`, parent `35f6090a9b2e16c7645b56f34b104eb3126d5c90`, clean working tree. | Git commit `39f475c1ce5b51c5b03b024fb39a74632e1a5eba` |

### Checks not run and why (proposed / future gates)

- **Local `Unlimited-OCR-2` weight download, Python CUDA venv creation, and RTX 5070 Ti GPU execution:** Prohibited by `WP-0004-eld-rd-carbon.md` (`no installations, model downloads, GPU execution, training, architecture changes`). Deferred to a dedicated runtime-qualification assignment after storage placement and GPU lease scheduling are bound.
- **Materialization of synthetic PDFs (`F01`–`F08`) and `evaluation/manifest.json`:** Held by `WP-0004-eld-rd-carbon.md` (`Future sole corpus ownership is reserved as WP-0004 / 004, but materialization and joint backlog reconciliation are held until this assessment and Astra's are both published and the coordinator pins the exchange`).
- **Application `.NET` / Angular / PostgreSQL build and durability tests:** Out of scope for the R&D lane; owned by `WP-0002` / `WP-0003`.

## Review map

Reviewers (`eld-coordinator`, `eld-rd-astra` during `WP-0004 / 003`, and `eld-rd-reviewer` during `WP-0004 / 005`) should inspect the actual deliverable diff `35f6090a9b2e16c7645b56f34b104eb3126d5c90..39f475c1ce5b51c5b03b024fb39a74632e1a5eba` on `research/wp-0004-carbon`:

1. `research/carbon/README.md` (blob `be1c32c31f25ddbb38b1f311e60d2184f4a7e22e`) — Independence attestation and scope boundaries.
2. `research/carbon/01-sources-and-qualification.md` (blob `3b945252e88e5d1c85b065fafe471b2e4d9934b4`) — Verify full SHA-256/blob pins (`§1`) and the 5 Windows/Blackwell/license/code-safety qualification gates (`§2.2`, especially `modeling_unlimitedocr.py` `eval()` at L120, `infer_multi` `crop_mode=False` at L1117, `_sparse_base_impl.py` Apache-2.0 notice & `transformers==4.52.1` coupling, and `PyMuPDF` AGPL-3.0 replacement).
3. `research/carbon/02-hypotheses.md` (blob `f924a5fc4d76faf2d4770bea4eaa0265735a1194`) — Verify SGLang page-windowing rejection (`§1`) and single-variable control/metric/rejection rigor of `H-C1`, `H-C2`, and `H-C3` (`§2`).
4. `research/carbon/03-corpus-and-candidates.md` (blob `e217b26e56c356aee4b9e15acbd6ebc26ad7a31e`) — Verify 8-family coverage (`§1`), `Decimal` `ROUND_HALF_UP` invariants (`§2.2`), leak-free `dev`/`eval_holdout` split and manifest fields (`§3`), and line-level proof disqualifying adjacent Form Recognizer JSON files as ground truth (`§4.2`).

## Risks, disagreements, and unfinished work

- **Unvalidated local GPU/Windows runtime risks:** Native Windows execution of `Unlimited-OCR-2` on RTX 5070 Ti (`sm_120`, `16,303 MiB` WDDM with desktop VRAM contention and `65.70 GiB` free on `C:`) without Linux Triton kernels remains unexecuted. `_forward_dense` SDPA fallback may still trigger WDDM shared-memory paging on multi-page `crop_mode=True` inputs (`H-C2`), and `_sparse_base_impl.py` may require exact `transformers==4.52.1` (and potentially Python `3.10` if `3.12.10` surfaces dependency friction).
- **Public candidate defects:** `sample-invoice.pdf` contains internal row-math inconsistency (`1 * 1 = $100.00`) and stale adjacent JSON (`ServiceStartDate`/`ServiceEndDate` absent from PDF bytes); `Invoice-6.pdf` is out-of-domain corporate training material with embedded Microsoft/Monotype font EULAs. Neither is admitted here.
- **Cross-agent disagreements:** None recorded yet because `WP-0004 / 001` (`eld-rd-astra`) was deliberately unread prior to publishing `WP-0004 / 002`. Any divergence on SGLang page-windowing, preprocessing treatments, multi-page `crop_mode` confounding, or public-sample admission should be surfaced and reconciled in `WP-0004 / 003` and `WP-0004 / 004` with unresolved disagreements preserved explicitly.

## Handoff

- **Next owner:** `eld-coordinator`.
- **Next action:** Record `WP-0004 / 002` publication in `INDEX.md` / `CURRENT.md`, then bind exact base/proposal revisions (`WP-0004 / 001` and `WP-0004 / 002`) to release the single cross-branch exchange (`WP-0004 / 003` on `eld-rd-astra`), followed by `WP-0004 / 004` (`eld-rd-carbon` deterministic corpus materialization in `evaluation/` and reconciled 3-item backlog) and `WP-0004 / 005` (`eld-rd-reviewer` / uninvolved Opus verification).
- **Coordinator index inputs:**
  - **Branch:** `research/wp-0004-carbon`
  - **Base SHA:** `35f6090a9b2e16c7645b56f34b104eb3126d5c90`
  - **Deliverable SHA:** `39f475c1ce5b51c5b03b024fb39a74632e1a5eba`
  - **Exact report path:** `docs/agent-reports/eld-rd-carbon/WP-0004/002_2026-11-14_research_eld-rd-carbon.md`
  - **Publication receipt:** This report is committed immediately atop `39f475c1ce5b51c5b03b024fb39a74632e1a5eba` on `research/wp-0004-carbon` and pushed to `origin` (`https://github.com/jackgumpe/eledgercare.git`). Because a report cannot contain its own commit SHA, remote confirmation (`git ls-remote origin refs/heads/research/wp-0004-carbon`) and the exact **report publication SHA** are verified immediately after committing this file and supplied directly in the handoff message to `eld-coordinator`.
