# WP-0005 /007: First preflight review response and metadata/source closure

- Report path: `docs/agent-reports/eld-rd-astra/WP-0005/007_2026-11-15_research_eld-rd-astra.md`
- Sequence reservation / exact kickoff: `273250af1e40cef0c68d18dc0c5792daeae831d8:INDEX.md` and `docs/kickoffs/WP-0005-eld-rd-astra-response.md` at that release.
- Category: research
- Author / agent ID: eld-rd-astra; resumed native `/root/rd_astra`
- Actual model / effort: dispatched `gpt-6-astra` / `high`; backend checkpoint and backend session UUID not exposed. No additional agents or external model invocation.
- Environment: native Codex agent, PowerShell 7.7.0, Git 2.55.0.windows.1, CPython 3.12.10 x64 on Windows 11; existing pip 25.0.1 vendored packaging 24.2 used only for metadata evaluation.
- Timestamp: 2026-11-15T05:49:00Z
- Repository / branch: private `jackgumpe/eledgercare` / `research/wp-0005-runtime-preflight`
- Owned worktree: `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-q0-astra`
- Full base: `2c32dde602b274251043bb216752f5d7fe9593be`
- Deliverable candidate: `d666c4163b8b6bdf5f6c69b455c30f3c377cbdc5`
- Post-verification evidence: `6cb6a258b9652b7becd3fca9c7cf2f04866c3ec3`
- Previous report: WP-0005 /001 at full base, preserved unchanged.
- Reviewed input: interim reviewer checkpoint `b75011da408fed5d2cc4f9025416ead6c5632ceb:docs/reviews/WP-0005/eld-q0-reviewer/pre-execution/README.md`; not a final /003 or acceptance.
- Status: ready-for-review; first bounded author response, not independent acceptance.
- Next owners: eld-q0-harness and the same uninvolved eld-q0-reviewer /003; coordinator retains release authority.

## Summary and scope

Q0R-01 producer attribution is explicitly corrected by fresh, frozen-helper collection; Q0R-02's hf-xet marker evaluates false on the exact `AMD64` environment; Q0R-03's missing sources/config/notice are retained and identity-checked. Static tokenizer follow-through finds no added mandatory package for the pinned fast JSON path. The metadata graph now has 32 exact artifacts, 35 active requirements satisfied, 815 inactive requirements, and zero unresolved active edges. This is a metadata-only proposal: torchvision still lacks a publisher wheel digest, and no installation, imports, runtime fit or GPU success is claimed.

Authorized work was source/metadata research and author corrections only. The independent reviewer's denied Python/network/root operations were not executed on its behalf, and these checks do not count as its reproduction. No fresh free-space/root/GPU/registry/pagefile observations occurred. Original /001 report and evidence remain unchanged.

## Complete change inventory

Paths are relative to the repository root. The candidate changes exactly 22 paths: one navigation notice plus 21 additions.

| Action | Exact path | Purpose |
| --- | --- | --- |
| Modified | `qualification/q0/preflight/README.md` | Link current /007 correction; preserve original discussion |
| Added | `qualification/q0/preflight/response/README.md` | Compact Q0R-01..09 response, corrected provenance, lock limits, source audit and later gates |
| Added | `qualification/q0/preflight/response/collect-response.py` | Frozen bounded metadata/source collector, explicit LF output, payload-GET rejection |
| Added | `qualification/q0/preflight/response/verify-response.py` | Offline author verifier; committed-byte identity, markers, source and prior artifact checks |
| Added | `qualification/q0/preflight/response/collection-receipt.json` | Frozen producer and exact output byte identities/UTC interval |
| Added | `qualification/q0/preflight/response/cuda-metadata.json` | Fresh official CUDA index, small PEP 658 bodies and HEAD receipts |
| Added | `qualification/q0/preflight/response/torchvision-alternate-indexes.json` | Combined/cu130 official index negotiation, absent wheel digest |
| Added | `qualification/q0/preflight/response/pypi-metadata.json` | Thirty exact version metadata records and selected compatible wheels |
| Added | `qualification/q0/preflight/response/metadata-lock.json` | Thirty-two artifacts, all marker results/edges, exact environment and explicit missing torchvision hash |
| Added | `qualification/q0/preflight/response/source-closure.json` | Twelve text receipt/hash/import/class audit entries |
| Added | `qualification/q0/preflight/response/sources/configuration_deepseek_v2.py` | Exact pinned model source bytes, Transformers imports only |
| Added | `qualification/q0/preflight/response/sources/conversation.py` | Exact pinned model source bytes, stdlib imports only |
| Added | `qualification/q0/preflight/response/sources/packing_patch.py` | Exact upstream source bytes, torch import only; no patch applied |
| Added | `qualification/q0/preflight/response/sources/tokenizer_config.json` | Exact pinned LlamaTokenizerFast configuration |
| Added | `qualification/q0/preflight/response/sources/special_tokens_map.json` | Exact pinned token metadata |
| Added | `qualification/q0/preflight/response/sources/model-card.md` | Exact pinned model README notice, separate from 18 runtime objects |
| Added | `qualification/q0/preflight/response/sources/transformers-tokenization_auto.py` | Pinned built-in versus remote tokenizer selection |
| Added | `qualification/q0/preflight/response/sources/transformers-tokenization_llama_fast.py` | Pinned SentencePiece guard and slow-conversion trigger |
| Added | `qualification/q0/preflight/response/sources/transformers-tokenization_utils_fast.py` | Pinned tokenizer.json versus conversion ordering |
| Added | `qualification/q0/preflight/response/sources/transformers-tokenization_utils_base.py` | Pinned file resolution and slow-class construction guard |
| Added | `qualification/q0/preflight/response/sources/transformers-convert_slow_tokenizer.py` | Pinned optional conversion dependency guards |
| Added | `qualification/q0/preflight/response/sources/transformers-ggml.py` | Pinned converter-import follow-through |

Post-candidate evidence: added only `qualification/q0/preflight/response/verification.json` at `6cb6a258b9652b7becd3fca9c7cf2f04866c3ec3`. Report metadata afterward: only this canonical /007 file. No shared INDEX/CURRENT, reviewer/harness files, product/corpus, earlier WP-0004 outputs or other worktrees were edited.

## Decisions and corrections

The original /001 collector-only attribution was inaccurate: retained JSON order/timestamps cannot come solely from that helper. The session did separately replace provisional Pillow 12 with corpus Pillow 13.0.0; PowerShell date roundtrip is consistent with the differing timestamp forms, but the exact intermediate chain is not reconstructable from retained evidence. This report does not invent it. Regeneration supersedes that claim; original evidence remains inspectable.

Producer chronology: helper `13e6921257a17acc078fbc298806e56681f5eedd`, tokenizer-audit extension `7e42f95853d4ca3a24313f001c989c808a6f8d17`, explicit LF serialization `de184699ac633511d01d12249b34ba9be46843c4`. The first frozen candidate `13544cd27df99b1ff85235f3ef2adb2cea0cbe41` failed byte-provenance verification because the working helper still had CRLF despite normalized-unchanged Git restore. Materializing the exact frozen blob with binary write and rerunning the unchanged helper corrected it. Final collection interval was **05:46:57.354313–05:47:06.723600 UTC**, with helper SHA-256 `dab1efc4d175da550b99910b435f3a37c9d7b83903b74646d25a4996c91eba12`, Git blob `9d51b71ce1ec6299c38b39abffde9d7636e07d00`, bound to its identical content at `13544cd27df99b1ff85235f3ef2adb2cea0cbe41`. Corrected collection candidate `26f9d8e767067cf8cad9bb6029774aa78bc92860` passed; final candidate additionally checks every receipt output against committed bytes. No manual output-record mutation followed final collection.

Thirty original/added PyPI pins plus exact torch/torchvision cu130 artifacts advertise **1,974,477,651 bytes**. All 13 original PyPI artifact identities remain identical. hf-xet is excluded because the marker compares lowercase strings to actual `AMD64`; model payload verification remains transport-independent. No extras, implicit sdist, CPU torch or latest versions are selected. This is published metadata closure, not wheel-body metadata equivalence, a security audit or an installable complete hash lock.

Both official torchvision indexes return HTML despite PEP 691 JSON Accept and still omit the wheel SHA-256. A later reviewed official-origin acquisition may record local SHA-256/size and check ZIP METADATA against the published PEP 658 digest, explicitly labeled local-sha256-TOFU. This author proposes the exception; reviewer/coordinator decide it. Until then the artifact hash remains null, with no fabricated install requirements file.

The six model texts exactly match inherited model-tree Git blobs at `0480966938291445591f69f08a13b041c073a96a`. The six additional Transformers texts bind raw pinned source bytes at `945727948c1143a10ac6f7d811aa58bb0d126b5b`; their computed blob identities are not misrepresented as a separate upstream Git-tree reproduction. Tokenizer config has LlamaTokenizerFast, no auto_map/from_slow override, add_prefix_space=null and legacy=true. With the required verified tokenizer.json present and no override, pinned source chooses the fast JSON path; SentencePiece/protobuf/tiktoken conversion helpers are not requested. Actual import/load remains unexecuted.

Q0R-04..09 are accepted as proposal refinements: unmodified non-Triton fallback labeling/raw logs and measured sparse-prefill memory; normalized existing local path plus offline-before-import flags; explicit task-local pip/uv/HF/torch/CUDA/temp caches; later MSVC/LongPathsEnabled/pagefile observations; exact offline hash installation; separate identity-verified model-card notice. The original 38-GiB task budget does not bound system pagefile/driver allocation; fresh >=58 GiB initial and >=20 GiB remaining floors remain proposed stage gates, not freshly observed capacity.

## Verification and limitations

| Actual check | Candidate / result |
| --- | --- |
| Frozen collector via selected `python.exe -I -B qualification/q0/preflight/response/collect-response.py` | Final collection completed with bounded text/index/JSON/PEP658 GET and wheel HEAD only; direct LF writes; no wheel/weight GET |
| `python.exe -I -B qualification/q0/preflight/response/verify-response.py` | Final candidate `d666c4163b8b6bdf5f6c69b455c30f3c377cbdc5`, exit 0/PASS: producer/committed-output bytes, 12 source identities, tokenizer flags, 32 artifacts, markers, unchanged 13 primaries, CUDA metadata hashes and preserved missing torchvision hash |
| Full base-to-candidate `git diff --check` | Exit 2 solely for four upstream model-card trailing-space lines 302/308/312/318; retained to preserve exact source identity |
| Same diff check excluding only that model-card path | Exit 0; no authored whitespace defects |
| `git diff --name-status`; status | Exactly 22 scoped candidate paths; clean worktree before evidence/report |
| `git diff --exit-code` for original /001 report and six original evidence JSON paths | Exit 0, unchanged; overall inventory also confirms all other original files unchanged except README link |

Failed verifier and corrective recollection are preserved above and in verification.json. Author checks use existing metadata tooling; no installation occurred. No independent reviewer reproduction, fresh host checks, external-root access/creation, DLL/registry/pagefile checks, wheel-body hashing, model/tokenizer imports, renderer/OCR, CUDA or GPU execution occurred. The retained model-card whitespace is an explicit identity-preservation exception, not a hidden clean-check claim.

External effects: bounded read-only primary HTTP/web access and normal owned-branch publication only. No global settings/authentication, task model root, services, ports, packages or other resources changed.

## Review map and handoff

[Exact candidate diff](https://github.com/jackgumpe/eledgercare/compare/2c32dde602b274251043bb216752f5d7fe9593be...d666c4163b8b6bdf5f6c69b455c30f3c377cbdc5). Start with [finding response](https://github.com/jackgumpe/eledgercare/blob/d666c4163b8b6bdf5f6c69b455c30f3c377cbdc5/qualification/q0/preflight/response/README.md), inspect actual source/metadata/receipt bytes and the [post-verification receipt](https://github.com/jackgumpe/eledgercare/blob/6cb6a258b9652b7becd3fca9c7cf2f04866c3ec3/qualification/q0/preflight/response/verification.json). Reviewer acceptance must address these changes and the separately frozen harness.

Next decisions: accept/reject metadata pins and source path; decide torchvision provenance exception; freeze harness log/telemetry/local-directory/containment behavior; then separately authorize acquisition/import/host checks. No stage release is granted by this author response. Runtime and GPU stages remain held.

Publication receipt is pending at report authoring. Normal push plus exact remote branch and candidate/evidence/report blob verification will be supplied in the separate handoff; this report will not be rewritten to add its own publication SHA.
