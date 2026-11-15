# WP-0004 / 001: Independent Astra source assessment and bounded experiment proposal

- Report path: `docs/agent-reports/eld-rd-astra/WP-0004/001_2026-11-14_research_eld-rd-astra.md`
- Sequence reservation: [INDEX at 287183ceec005195d03e83649a3f91c41ae4fcd1](https://github.com/jackgumpe/eledgercare/blob/287183ceec005195d03e83649a3f91c41ae4fcd1/INDEX.md), WP-0004 / 001; [exact kickoff](https://github.com/jackgumpe/eledgercare/blob/287183ceec005195d03e83649a3f91c41ae4fcd1/docs/kickoffs/WP-0004-eld-rd-astra.md).
- Category: research
- Author / agent ID: eld-rd-astra
- Actual model / effort: selected gpt-6-astra / high as exposed by coordinator dispatch; backend checkpoint unknown. This report does not independently establish a backend checkpoint from a requested label.
- Session: `/root/rd_astra`; backend session UUID not exposed.
- Execution environment: Codex tool orchestration with native Windows PowerShell 7.7.0 and Git 2.55.0.windows.1; read-only primary-source HTTPS, GitHub connector and browser queries.
- Published by: author on owned branch; publication confirmation follows in handoff, not a self-referential report SHA.
- Timestamp: 2026-11-14T15:13:38Z
- Repository / branch: private `https://github.com/jackgumpe/eledgercare`; `research/wp-0004-astra`
- Owned worktree: `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-rd-astra`
- Base revision: `35f6090a9b2e16c7645b56f34b104eb3126d5c90`
- Deliverable revision: `1eb6f4af643edc7ccffcd5732a4659da44e7a077`
- Previous report: none
- Related or reviewed reports: no Carbon conclusions or research branches read; no other author's report reviewed.
- Status: ready-for-review (author source assessment; neither independently accepted nor merged)
- Next owner: eld-coordinator; then one exchange only after both initial proposals are published; eventual acceptance reviewer eld-rd-reviewer / uninvolved Opus.

## Summary

Pinned the refreshed Baidu model repository to `0480966938291445591f69f08a13b041c073a96a` and official project source to `64e6f066023b305ab03860603a9cf358a8b70148`. Retained 16 source/metadata snapshots with provenance; verified all snapshot hashes/sizes and 14 upstream Git blobs. Source inspection distinguishes the native reference implementation from the custom serving runtime and preserves missing compatibility evidence.

The native generator uses growing DynamicCache state and sequence-sized decode operations even though attention selects sparse references. The broad efficiency claim therefore cannot be assumed for that path or this host. The current serving recipe uses a different custom SGLang wheel than the kit lead. Its source mapping, dependency lock and local execution remain unverified.

Proposed three single-change comparisons (explicit tiling, conditional deskew, deferred serving page windows) and eight synthetic families with family-level held-out assignments, bounded variants and independent visible-page/arithmetic checks. Both Azure PDFs remain metadata-only candidates. No model, OCR, GPU, corpus generation, production or service execution occurred.

## Objective and acceptance criteria

The released kickoff requested source-only independent research: exact primary-source pins/retrieval evidence; inspected versus unverified architecture/runtime/platform facts; at most three falsifiable hypotheses with controls/metrics/rejection rules/minimal future execution; eight synthetic families and up to two public candidates with admission/split/ground-truth checks. The deliverable supplies those proposals without claiming runtime qualification, accepted ground truth or a joint backlog.

Read AGENTS.md, START_HERE.md, CURRENT.md, reporting README/template, and bootstrap kit 02/03/04/05 in the assigned worktree. Read later authoritative kickoff/INDEX via `git show 287183ceec005195d03e83649a3f91c41ae4fcd1:<path>`; their release supersedes the base's planned-only routing. No other agents were started, and every shell command used the owned worktree explicitly.

## Change inventory

All 22 base-to-deliverable files are added. Source snapshots are inert `.txt`/JSON evidence, not installed research dependencies or production references.

| Action | Exact path | Purpose / relevant symbols |
| --- | --- | --- |
| Added | `research/astra/.gitattributes` | Preserve exact snapshot bytes across Windows checkouts; `sources/** -text` |
| Added | `research/astra/assessment.md` | Pins, inspected facts, source/runtime distinctions and Q0 limits |
| Added | `research/astra/hypotheses.md` | Three single-treatment cards and common scoring protocol |
| Added | `research/astra/corpus-proposal.md` | Eight-family split, admission and independent truth checks |
| Added | `research/astra/source-manifest.json` | Source URLs, revisions, retrieval times/windows, sizes, SHA-256 |
| Added | `research/astra/verify-sources.ps1` | Offline source-integrity verification; never imports upstream code |
| Added | `research/astra/sources/github-LICENSE.txt` | Baidu MIT notice |
| Added | `research/astra/sources/github-README.md.txt` | Pinned project runtime recipe |
| Added | `research/astra/sources/github-infer.py.txt` | Batch-client source, `plan`, `build_payload`, `request_one` |
| Added | `research/astra/sources/github-utils-README.md.txt` | Raw layout/postprocessing documentation |
| Added | `research/astra/sources/hf-README.md.txt` | Refreshed model card |
| Added | `research/astra/sources/hf-_sparse_base_impl.py.txt` | Underlying attention/cache source; selected regions inspected |
| Added | `research/astra/sources/hf-config.json.txt` | Architecture, sparse/page/vision configuration |
| Added | `research/astra/sources/hf-dash_attention.py.txt` | Sparse routing and optional Triton fallback code |
| Added | `research/astra/sources/hf-deepencoder.py.txt` | Vision component source; selected regions inspected |
| Added | `research/astra/sources/hf-generation_config.json.txt` | Generation metadata |
| Added | `research/astra/sources/hf-modeling_deepseekv2.py.txt` | `_dash_decode_forward`, `_decode_attend` |
| Added | `research/astra/sources/hf-modeling_unlimitedocr.py.txt` | `_uocr_build_inputs`, `infer_multi`, `_uocr_generate` |
| Added | `research/astra/sources/hf-sparse_gather_e2e_triton.py.txt` | Optional fused-kernel source; import/path inspection |
| Added | `research/astra/sources/hf-sparse_gather_triton.py.txt` | Kernel dependency text; not executed or fully audited |
| Added | `research/astra/sources/hf-tree.json` | Exact tree/blob/LFS metadata; no weight/wheel bytes |
| Added | `research/astra/sources/public-candidate-metadata.json` | Filtered Azure candidate Git blobs/sizes/URLs |

Post-deliverable metadata: this exact report path only. No INDEX/CURRENT, other author report, product file, fixture, shared staging, installation or service changes. External effects: read-only requests to public primary sources and private repository metadata; normal owned-branch Git publication is authorized and scheduled after report commit. No external messages, cloud OCR or customer-data upload.

## Decisions and rationale

Use the refreshed model pin for a future baseline proposal while preserving the older kit pin as a historical lead. Keep native and custom SGLang baselines separate because image defaults, guards, cache and serving behavior differ. Treat Q0 runtime qualification as a prerequisite independent of optional research success. Do not infer local GPU fit from roughly 6.23 GiB of advertised weight bytes or an A800 test description.

Source snapshots retain upstream whitespace and exact bytes for meaningful hash verification. Git initially warned about line-ending conversion; the scoped attributes file prevents source conversion without changing shared repository policy. Current SGLang documentation is mutable and for newer generic releases; it is contextual evidence, not a pinned dependency requirement for Baidu's wheel. Missing full custom-wheel source mapping and local package/build compatibility stay explicit.

The corpus is proposed, with zero generated/admitted/independently checked items. The two public files have confirmed directory metadata and root-license inspection only. All fixture variants remain in one family/split. The proposed small set supports diagnostics, not statistical/general performance claims.

## Verification

Checks below identify whether they ran before the commit or against frozen deliverable `1eb6f4af643edc7ccffcd5732a4659da44e7a077`. Source integrity and authored-content whitespace checks were rerun against that frozen deliverable. Tool output is summarized honestly; retained evidence is the source manifest/snapshots and reproducible script.

| Check / exact command or tool operation | Environment and revision | Actual result | Evidence |
| --- | --- | --- | --- |
| `git status --short --branch`; `git rev-parse HEAD`; `git remote -v` | Start, assigned worktree | Clean owned branch at exact base, intended origin | Metadata above |
| `git show 287183ceec005195d03e83649a3f91c41ae4fcd1:docs/kickoffs/WP-0004-eld-rd-astra.md` and same revision `:INDEX.md` | Read-only authority check | Exact WP-0004 / 001 release/report reservation read | Pinned links above |
| GitHub `search_commits` + `fetch_file` on Baidu sources; read-only `Invoke-WebRequest -Uri <manifest.origin> -OutFile <manifest.path>` for pinned HF text | Retrieval windows in manifest | Primary text/metadata retrieved without weights, wheel or PDFs | `research/astra/source-manifest.json`; `sources/` |
| Browser open of HF API | Retrieval phase | Tool inaccessible/internal error; direct read-only HTTPS metadata request succeeded | Source limitation in assessment |
| GitHub `fetch_file` for `sgl-project/sglang`, `docs/get_started/install.md` at `999a6fa3dc7cb4f9e10d7be8fab9ce5853ae2d4d` | Retrieval phase | HTTP 404; no fabricated pinned docs source | Assessment source table |
| `& ./research/astra/verify-sources.ps1` | PowerShell 7.7.0; frozen deliverable | PASS: 16 SHA-256/size checks, 14 upstream Git blob matches, 2 candidate metadata records, weight-byte sum 6688305576 | Script + manifest + exact snapshots |
| `git diff --check 35f6090a9b2e16c7645b56f34b104eb3126d5c90 HEAD -- research/astra/.gitattributes research/astra/assessment.md research/astra/hypotheses.md research/astra/corpus-proposal.md research/astra/source-manifest.json research/astra/verify-sources.ps1` | Frozen deliverable | Exit 0, author-created content clean | Git candidate diff |
| `git diff --cached --check -- research/astra/sources` | Precommit, same source snapshot content | Exit 1: upstream trailing whitespace and blank EOF lines; deliberately preserved, not misreported as clean | Source snapshots match upstream Git blobs |
| `git check-attr text -- research/astra/sources/hf-config.json.txt research/astra/sources/public-candidate-metadata.json` | Final precommit attributes | Both `text: unset`, preserving source bytes | Scoped `.gitattributes` |
| `git diff --name-status 35f6090a9b2e16c7645b56f34b104eb3126d5c90 HEAD` | Frozen deliverable | Exactly 22 additions, all `research/astra/**` | Inventory above |
| GitHub `get_repo` for `jackgumpe/eledgercare` | After deliverable commit | Visibility private; intended repository identity confirmed | Publication target metadata |
| `git status --short --branch` | After deliverable checks | Clean `research/wp-0004-astra` | Commit receipt |

Not run: package installation/resolution, Python/model imports, OCR, tests of upstream code, wheel/source-build inspection, PDF rendering or page review, ground-truth calculation, GPU/CUDA/kernel execution, benchmarks, database/application tests, service launch, provider comparison. These are outside this source-only release. No performance, accuracy, runtime compatibility, complete license review or independent acceptance is claimed. The source-integrity script is evidence verification, not a model test suite.

## Review map

[Exact base-to-deliverable diff](https://github.com/jackgumpe/eledgercare/compare/35f6090a9b2e16c7645b56f34b104eb3126d5c90...1eb6f4af643edc7ccffcd5732a4659da44e7a077). Read assessment, hypothesis cards and corpus proposal, then inspect the actual pinned source functions named in the inventory. Run `verify-sources.ps1` on the frozen candidate; it requires no network, packages or GPU. Hash fidelity does not establish semantic correctness or runtime behavior.

## Risks, disagreements, and unfinished work

No cross-agent disagreement has been tested because the first assessments remain independent. Native code inspection limits the transfer of broad efficiency claims, while custom serving implementation remains unknown. Installed Python 3.12.10 and product SDK/Node observations do not resolve that runtime. Storage and GPU ownership are unallocated; no accepted OCR baseline exists. The public candidates' SHA-256, page counts, internal notices, permitted-use decision and checked expected answers remain unknown. Corpus preparation and independent review are future work under separate reservations.

## Handoff

Coordinator receives branch `research/wp-0004-astra`, deliverable `1eb6f4af643edc7ccffcd5732a4659da44e7a077`, and this report path. Keep it independent until Carbon's first proposal is published, then release the single exchange/reconciliation on exact initial revisions. Uninvolved Opus must eventually inspect the joint result and admitted ground truth; this author cannot independently accept it.

Publication receipt at report creation: local deliverable committed; report publication and remote verification pending. After committing this report separately, author will push only the owned branch without force, verify the remote tip and exact report object, and send the publication SHA outside this report. No acceptance or merge is implied by publication.
