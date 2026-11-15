# WP-0005 /001: Native Windows Q0 runtime and storage preflight

- Report path: `docs/agent-reports/eld-rd-astra/WP-0005/001_2026-11-15_research_eld-rd-astra.md`
- Sequence reservation: [WP-0005 release INDEX](https://github.com/jackgumpe/eledgercare/blob/0029b02dab23a87661acd419cadc5f4266cdeeea/INDEX.md); exact kickoff at the same revision, `docs/kickoffs/WP-0005-eld-rd-astra.md`; actual-start receipt `8cd9b8ff0d81a6ccb427de4db0caaec90295a30d`.
- Category: research
- Author / agent ID: eld-rd-astra; resumed native `/root/rd_astra`
- Actual model / effort: coordinator-dispatched `gpt-6-astra` / `high`; backend checkpoint and backend session UUID not exposed. No substitute session or external model invocation.
- Execution environment: native Codex agent using PowerShell 7.7.0, Git 2.55.0.windows.1, CPython 3.12.10 stdlib, official-source web/HTTP and GitHub reads; Windows 11 Home x64 build 26200.
- Timestamp: 2026-11-15T05:19:53Z
- Repository / branch: private `jackgumpe/eledgercare` / `research/wp-0005-runtime-preflight`
- Owned worktree: `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-astra`
- Base revision: `df9a2b50894f01987d779d7f9ae805794503ce6f`
- Deliverable revision: `95ce0a8df728ae2c41aaf9e09d1b97c7d990fe36`
- Candidate chronology: initial `b8112ca27b8f7d5bcba7171ab0f1bd5907fae1f6`; final candidate changes only the stale Opus connection-status paragraph, preserving initial chronology.
- Previous report: none in WP-0005; author previously participated in WP-0004 source/protocol work.
- Related work: accepted Q0 section 1.2/common input contract in `research/carbon/reconciliation/02-ranked-experiment-backlog.md` and admitted corpus at the full base; pinned model/source `baidu/Unlimited-OCR-2@0480966938291445591f69f08a13b041c073a96a`.
- Status: ready-for-review (author verification; no independent acceptance)
- Next owners: eld-q0-harness, then uninvolved eld-q0-reviewer; coordinator controls subsequent stage release.

## Summary

Proceed to CPU harness/protocol preparation and independent review. Propose CPython 3.12.10 x64, torch 2.13.0+cu130, torchvision 0.28.0+cu130, Transformers 4.52.1, unmodified pinned model from a complete task-owned local directory. Exact official Windows wheel metadata and PyTorch's source matrix support this proposal for capability 12.0; no executed import, CUDA, memory-fit or OCR qualification is claimed.

A concrete source-derived trap exists: Transformers' remote-ID recursive module checker may require Triton from an optional leaf before the model's try/except fallback. The pinned local-directory loader takes a different path; its unmodified-source import remains a later gate. Complete transitive dependency lock and torchvision wheel digest provenance also remain unfinished. This packet author cannot accept this upstream-related proposal/harness.

## Objective and acceptance criteria

Source/metadata-only runtime selection, fresh read-only host inventory, selected-root storage budget, exact pins/unknowns, and actionable harness handoff. No installations, wheel/weight payload downloads, model/library imports, CUDA allocation, runtime execution, fixtures, services or GPU lease changes. All authorized deliverables were committed before final verification.

## Change inventory

All paths below were added; there are no base-to-deliverable modifications outside this directory.

| Exact path | Purpose |
| --- | --- |
| `qualification/q0/preflight/README.md` | Concise proposal, official evidence links, storage budget, loader risk and staged gates |
| `qualification/q0/preflight/host-receipt.json` | Timestamped OS/RAM/interpreter/tools/GPU/C: observations and absent root |
| `qualification/q0/preflight/collect-metadata.py` | Bounded stdlib metadata/index/HEAD collection; never fetches wheel bodies |
| `qualification/q0/preflight/cuda-wheel-metadata.json` | Exact CUDA wheel names/origins, HEAD sizes, published digest or explicit null, PEP 658 metadata/hash evidence |
| `qualification/q0/preflight/package-proposal-metadata.json` | Exact 13 PyPI package versions, requirements, candidate wheel hashes/sizes and notice metadata |
| `qualification/q0/preflight/proposed-artifacts.json` | Compact exact primary artifact proposal, not a complete transitive lock |
| `qualification/q0/preflight/collect-source-audit.py` | Small pinned text retrieval/AST parsing; no model execution |
| `qualification/q0/preflight/source-audit.json` | Seven pinned primary source hashes, byte sizes, Git blob identities and selected line excerpts |
| `qualification/q0/preflight/model-files-proposal.json` | Eighteen required model/code/tokenizer/shard objects and upstream identities/sizes |
| `qualification/q0/preflight/verify-preflight.py` | Offline record/hash/size/budget/helper-syntax consistency check |

Report metadata committed afterward: only this canonical report. No INDEX/CURRENT, production, corpus, earlier WP-0004 output or other worktree edits. External effects: read-only official-source HTTP/GitHub/web access and host queries; normal owned-branch commit/push is the publication action. The selected external storage root remains absent. No authentication/global settings, package installs, caches for model use, ports or processes were changed.

## Decisions and rationale

- Official cu130 CPython 3.12 Windows artifacts retain upstream torch/Transformers versions. Python 3.12 differs from upstream's 3.10 recipe and requires actual import qualification. PyTorch 2.13.0's pinned release matrix includes Windows Blackwell 12.0; driver 621.01 exceeds the official 580.88 CUDA-13 Windows requirement. These are source/metadata statements, not binary execution proof.
- Exact torch wheel published SHA-256 is retained; torchvision's inspected official index/HEAD did not publish a wheel SHA-256. Both small PEP 658 metadata bodies match their declared metadata digests. Metadata hashes and ETags must never stand in for a wheel digest. Local payload hashing is deferred to a released download stage.
- All 13 primary PyPI proposals have explicit compatible non-yanked wheel metadata. Pin Pillow 13.0.0 and pypdfium2 5.15.2 to the admitted corpus/render contract; do not silently use a newer renderer. The README explicitly lists unresolved transitive dependencies and marker resolution.
- Proposed task root is `C:\Users\jackg\eLedgerCare-Q0\WP-0005`. Observed C: free 69,064,572,928 bytes (64.32 GiB). A 38-GiB peak allowance covers model/staging, wheelhouse, venv, temp, caches and evidence; require fresh >=58 GiB free to retain a 20-GiB system floor. Actual extracted size/installer peak, RAM/VRAM fit and writability remain unmeasured.
- Complete 18-object model directory advertises 6,699,195,181 bytes; primary wheels advertise 1,963,004,322 bytes before full closure. Preserve all optional source files and use isolated HF_MODULES_CACHE plus offline local-directory loading; do not install Triton or patch model source to bypass a failure.
- Harness scope is admitted F01 clean one-page and F07 clean three-page only, native infer_multi with explicit crop_mode=False/save_results=False and accepted page/token guards. Freeze renderer hashes, ngram guards and an external non-mutating telemetry method in review. Missing finish telemetry must remain missing evidence, never fabricated success.
- Preserve model Apache source headers alongside repository MIT metadata, wheel/dist-info/dependency notices, PDFium notices and applicable CUDA runtime terms. This is not a complete license audit or redistribution clearance.

## Verification

| Executed check / operation | Revision/environment | Actual result / evidence |
| --- | --- | --- |
| Official PyTorch version/index pages, NVIDIA capability table and pinned PyTorch release matrix | Read-only primary-source retrieval; links in README | Exact Windows cp312 cu130 artifacts observed; sm_120 matrix support is metadata, not local execution |
| `collect-metadata.py` bounded stdlib GET for indexes/PyPI JSON/PEP 658 metadata, HEAD for two wheel payload URLs | CPython 3.12.10; timestamped JSON receipts | Two CUDA metadata bodies checked; 13 explicit PyPI artifact proposals; no wheel payload GET |
| `collect-source-audit.py` pinned source GET/AST parsing and inherited model snapshot inspection | Transformers `945727948c1143a10ac6f7d811aa58bb0d126b5b`; PyTorch `cf30153c4c131c8164ee7798e5022d810682e2cb`; model pin above | Private symbols present and loader branches inspected; source-audit.json records seven full-text hashes/excerpts; no imports |
| Host stdlib metadata/platform/drive queries, `py -0p`, tool version queries, nvidia-smi read-only observation | Host receipt beginning 2026-11-15T05:08:02Z | CPython 3.12.10 x64; six selected library distributions absent; GPU capability 12.0/16303 MiB; no lease inferred |
| `& 'C:\Users\jackg\AppData\Local\Programs\Python\Python312\python.exe' qualification/q0/preflight/verify-preflight.py` | Frozen final candidate `95ce0a8df728ae2c41aaf9e09d1b97c7d990fe36` | Exit 0/PASS: 13 records, 2 metadata hashes, 18 model sizes, 7 source audits, byte sum, 38/20-GiB budget, external root absent, helper AST syntax |
| `git diff --check df9a2b50894f01987d779d7f9ae805794503ce6f 95ce0a8df728ae2c41aaf9e09d1b97c7d990fe36` | Final candidate | Exit 0, no whitespace errors |
| `git diff --name-status` across the same revisions; `git status --porcelain=v1`; branch/top-level checks | Final candidate | Exactly the ten additions above; clean worktree; owned branch/worktree confirmed |

Routine read failures: an initial PowerShell/rg wildcard path and later `_template.md` lookup were invalid; recovered with supported glob syntax and the actual `TEMPLATE.md`. Long source output was narrowed after truncation. No test/runtime failure is hidden by these inspection corrections. Git emitted a CRLF-to-LF normalization notice; final diff check passed.

Not executed: transitive resolver/install/pip check, wheel-body hashing, model download/import, renderer execution, CUDA availability/arch-list/BF16/SDPA checks, model load, OCR, latency/repeatability/RSS/VRAM measurement or GPU lease. These require later reviewed stages; proposed commands and stopping rules are in README.

## Review map

[Exact base-to-candidate diff](https://github.com/jackgumpe/eledgercare/compare/df9a2b50894f01987d779d7f9ae805794503ce6f...95ce0a8df728ae2c41aaf9e09d1b97c7d990fe36). Start with [candidate README](https://github.com/jackgumpe/eledgercare/blob/95ce0a8df728ae2c41aaf9e09d1b97c7d990fe36/qualification/q0/preflight/README.md), then inspect metadata, source excerpts and model-object identities at that same revision. The check script validates internal consistency, not network freshness or actual runtime compatibility.

## Risks and unfinished work

Execution still needs complete transitive version/hash/marker closure; torchvision digest provenance decision; local unmodified class import; reviewed telemetry/timeout harness; fresh storage checks; and an explicit observed GPU lease before CUDA. Native Windows success and 16-GB fit remain unknown. No accuracy-zero substitution for platform/import/OOM/truncation failures.

Connection chronology: initial candidate b8112ca recorded a coordinator-reported HTTP401 dispatch blocker. Before final candidate/report, coordinator reported it resolved through child-process-only omission of an inherited invalid API key using existing login; actual Opus harness author was running at receipt `c314f03650e6c170a7fd56f1588f4282d8b535c8` (release `2b1ecf1fd46c36958ae05007c3ac5c4fa0cc8c53`). This author did not perform or independently reproduce that authentication action. Final README reconciles the update; acceptance is still outstanding.

## Handoff

eld-q0-harness should consume candidate `95ce0a8df728ae2c41aaf9e09d1b97c7d990fe36` for the CPU harness proposal, with special attention to local loader mode, incomplete lock/provenance, four-page renderer contract, raw-output/finish telemetry, and fail-closed stage gates. Uninvolved eld-q0-reviewer must inspect actual pinned artifacts and accept or request changes before the coordinator releases dependencies/model/GPU work. This report grants no execution release.

Publication receipt: remote publication is pending when this report is authored. A separate normal owned-branch push and exact remote verification will be reported to the coordinator with the final report publication SHA; this report will not be rewritten to insert its own SHA.