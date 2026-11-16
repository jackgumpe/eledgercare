# WP-0009 /010: Exact admitted corpus publication after unseal

- Report path: `docs/agent-reports/eld-eval-custodian/WP-0009/010_2026-11-16_verification_eld-eval-custodian.md`
- Sequence reservation: [INDEX.md](../../../../INDEX.md), WP-0009 /010; exact release authority `5685660e0188db1d9832baded7eb8e95085109c7`
- Category: verification
- Author / agent ID: `eld-eval-custodian`
- Actual model / effort: same native Codex session, requested `xhigh`; backend model identity is not exposed in this worker context
- Execution environment: Windows PowerShell; existing Python 3.12.10 CPU environment, pypdf 7.1.0; no dependency changes
- Published by: author
- Timestamp: 2026-11-16T20:49:00Z
- Repository / branch: private `jackgumpe/eledgercare`; `evaluation/wp-0009-fresh-families`
- Owned worktree: `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-eval-custodian`
- Initial continuation HEAD: `d866c70986abc311767e1cb0f152653687a16964`, clean
- Base revision after authorized fast-forward: `5685660e0188db1d9832baded7eb8e95085109c7`
- Frozen publication helper: `4457172b3f47138b94e182ce6223cdd559c66c36`
- Corpus deliverable revision: `c0a702e43efee7bda20b4da0bc2b0cb3f0852e41`
- Publication evidence revision: `c9b0726ea4d9c46fde894c0301aa58ff3ff56cd8`
- Inventory-only revision: `4449d113f7c4c9ade6bb8c7285e0a58bf22a0480`
- Previous report: [WP-0009 /003](003_2026-11-16_verification_eld-eval-custodian.md), publication `d866c70986abc311767e1cb0f152653687a16964`, unchanged
- Related reports: independent [/004 admission](../../eld-mapping-reviewer/WP-0009/004_2026-11-16_review_eld-mapping-reviewer.md) at `3e5d305d0cdcb2666ba56912ba6c06dc19d74c8b`; independent [/006 source/protocol acceptance](../../eld-mapping-reviewer/WP-0009/006_2026-11-16_review_eld-mapping-reviewer.md) at `89a27d8b13b280632f4fc0e6704f8c3bdfe74355`
- Status: ready-for-review — exact publication verified; next root integration/byte-identity verification
- Next owner: `eld-coordinator`; later finite runtime requires a separate exact release and observed lease

## Summary

All **40 admitted files, 1,075,820 bytes**, are published under `evaluation/mapping_v1/`, preserving every sealed relative path and every original Git blob. The four PDFs contain six pages and all 20 originally reserved core artifact hashes match. This publication followed independent admission, accepted mapper/scoring/protocol freeze, and the explicit root unseal object. All **2,171** preexisting tracked files at the release authority retain their exact paths, modes, object types and Git identities.

This is publication verification. The original sealed repository, its history, all historical evidence, reservation files and reports remain unchanged. No content was regenerated, relabeled, repaired, tuned or dropped. No model inference, rendering, GPU, service, dependency or download work occurred during /010.

## Objective and acceptance criteria

The [exact kickoff](../../../kickoffs/WP-0009-eld-eval-custodian-unseal.md) releases publication only of the admitted sealed receipt `559c5d09490b7729be26fb9bf9d872305cae3303`, after accepted corrected source `23e023045b335540d830ce01b75be247552a63f1` and independent /006 acceptance. Verify the explicit [unseal object](../../../coordination/WP-0009/unseal.json), complete original inventory, destination absence, original and published Git bytes, protected repository inputs and chronological custody. Publish evidence and this newly reserved report separately after the corpus deliverable.

All custodian publication criteria passed. Root's independent byte verification and integration remain next. This task does not release tuning or inference.

## Chronological custody

[custody-timeline.json](../../../evaluation/WP-0009/unseal/custody-timeline.json) retains nine exact commit identities and observed UTC timestamps, checked in order:

| Event | UTC time | Exact binding |
| --- | --- | --- |
| Public hash reservation | 2026-11-16 19:28:14 | `7513a9a86e6af55a6d8ca7f5a8dc0f80f054ba0b` |
| Canonical /003 reservation report | 2026-11-16 19:30:44 | `d866c70986abc311767e1cb0f152653687a16964` |
| Independent /004 admission | 2026-11-16 19:46:54 | `3e5d305d0cdcb2666ba56912ba6c06dc19d74c8b` |
| First mapping implementation source | 2026-11-16 20:07:28 | `b95c12d2fd8d71598a1e9c523182cd1a2f3ee121` |
| Corrected mapping/protocol source | 2026-11-16 20:28:33 | `23e023045b335540d830ce01b75be247552a63f1` |
| Independent /006 accepted freeze | 2026-11-16 20:41:06 | `89a27d8b13b280632f4fc0e6704f8c3bdfe74355` |
| Explicit root unseal object issued | 2026-11-16 20:42:55.470156 | Authority `5685660e0188db1d9832baded7eb8e95085109c7` |
| Exact corpus publication commit | 2026-11-16 20:45:54 | `c0a702e43efee7bda20b4da0bc2b0cb3f0852e41` |

The reservation preceded mapper implementation. Admission accepted the original corpus without corrections. The root unseal object binds the accepted source, /006, /004, sealed receipt, exact publication prefix and reservation SHA256 `f1490c428109e94f8b15c62a9f2ef3386039e614eb046a647957f2d0c759bdba`. The publication helper verifies those bindings and ancestry before reading/copying the admitted content. Content publication/read access follows this explicit release; runtime remains held for separate authority.

## Change inventory

The [complete publication inventory](../../../evaluation/WP-0009/unseal/publication-inventory.json) enumerates **52 files, 1,188,992 bytes** at evidence revision `c9b0726ea4d9c46fde894c0301aa58ff3ff56cd8`, with paths, roles, byte counts, SHA256 and Git blob IDs. Its SHA256 is `2c81945d7bd5371f71ef776eb407dedd6b8c8d4a29c43e5c810ddc408bbf6c14`. The inventory itself and this later report are the two subsequent additions, for 54 added paths from release authority through final publication.

| Action / scope | Exact path or mapping | Count / reason |
| --- | --- | --- |
| Added admitted corpus files | `evaluation/mapping_v1/<original sealed relative path>` | Exactly 40, byte-exact; full source/destination mapping in [committed verification receipt](../../../evaluation/WP-0009/unseal/attempts/commit-001/receipt.json) |
| Added frozen helper | `docs/evaluation/WP-0009/unseal/publish.py` | Exact copying and source/disk/index/commit checks |
| Added documentation attribute rule | `docs/evaluation/WP-0009/unseal/.gitattributes` | Preserves raw `attempts/**` evidence bytes; separate from the admitted 40 |
| Added publication documentation | `docs/evaluation/WP-0009/unseal/README.md`, `custody-timeline.json` | Current unseal status and exact chronology |
| Added copy/index/commit receipts | `docs/evaluation/WP-0009/unseal/attempts/{copy-001,index-001,commit-001}/receipt.json` | Three passed exclusive executions, each retaining complete 40-file mappings and bindings |
| Added diagnostic evidence | `docs/evaluation/WP-0009/unseal/attempts/whitespace-001/` | Five files: exact stdout/stderr for both checks and receipt |
| Added after evidence | `docs/evaluation/WP-0009/unseal/publication-inventory.json` | Complete 52-file inventory, committed separately |
| Added after inventory | This canonical /010 | Publication verification and handoff; its own SHA is supplied separately |
| Retained external custody | `C:/Users/jackg/eLedgerCare-Mapping/WP-0009/sealed` | Clean original `sealed/wp-0009` at `559c5d09490b7729be26fb9bf9d872305cae3303`; no remote, content or history change |

Authority changes were imported by fast-forward before author work. No root attributes, shared routing, existing corpus/evaluation paths, Q0, B0, mapper/scorer source, product source, reservation file or historical report was edited. Independent reviewer's private admission evidence publication remains separately owned and coordinated.

## Byte preservation and historical context

The original inventory `inventory/sha256-r1.json`, SHA256 `c2971612374178aaf1194f4b3a48e0c8435d14305b813b290f0e1e2b856ac322`, covers 39 tracked files. Its own admitted bytes are the fortieth file, bound by sealed receipt `559c5d09490b7729be26fb9bf9d872305cae3303`. Each original disk file was compared with its original Git blob before copying, then with destination disk, staged Git bytes and committed Git bytes. No `.git` internals, ignored regeneration scratch or Python caches were copied.

The original admitted `.gitattributes` is copied unchanged as one of the 40 files. Its `* -text` disables text normalization for this namespace, including original CRLF evidence. Every index attribute and all 40 Git blob identities were verified. No additional corpus attributes file was required. The separate documentation attribute rule preserves new attempt receipts without affecting corpus/source paths.

Original README/validation/provenance files preserve historical paths and statements such as admission pending or content sealed. They were not revised to make historical evidence appear current. The later /004 acceptance and this exact unseal/publication record establish current status. Original generation/verification helpers and evidence remain their admitted versions; they were copied and inspected, not executed in /010.

## Verification

The frozen publication helper ran using `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-rd-carbon-recovery/.venv/Scripts/python.exe`, with base command `docs/evaluation/WP-0009/unseal/publish.py` and `--helper-commit 4457172b3f47138b94e182ce6223cdd559c66c36`.

| Exact operation / arguments | Result | Evidence |
| --- | --- | --- |
| `git ls-remote origin refs/heads/coordination/bootstrap`; fast-forward exact authority | Origin matched `5685660e...`; merge succeeded from clean owned continuation HEAD | Tool observations; exact base above |
| `--mode copy --run-id copy-001` | Exit 0; exact gate, helper, clean sealed receipt, all 40 source identities, 20 reserved artifacts and four PDFs/six pages verified; absent destination created exclusively | [copy receipt](../../../evaluation/WP-0009/unseal/attempts/copy-001/receipt.json) |
| `git add evaluation/mapping_v1`; `--mode verify-index --run-id index-001` | Exit 0; staged scope exactly 40 files; every disk/index hash and attribute passed | [index receipt](../../../evaluation/WP-0009/unseal/attempts/index-001/receipt.json) |
| `--mode verify-commit --run-id commit-001 --candidate c0a702e43efee7bda20b4da0bc2b0cb3f0852e41` | Exit 0; all 40 committed blobs equal originals; all 2,171 authority input objects unchanged; sealed custody unchanged | [commit receipt](../../../evaluation/WP-0009/unseal/attempts/commit-001/receipt.json) |
| `git diff --check 4457172b3f47138b94e182ce6223cdd559c66c36 c0a702e43efee7bda20b4da0bc2b0cb3f0852e41` | Exit 2; preserved original CRLF evidence reported as trailing whitespace | [retained diagnostic receipt and raw output](../../../evaluation/WP-0009/unseal/attempts/whitespace-001/receipt.json) |
| Same diff with `git -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol` | Exit 0; CRLF recognized, ordinary whitespace checks retained; no config or content change | Same diagnostic receipt |
| Exact inventory of authority-to-evidence additions from committed blobs, compared to checked-out bytes | 52 files; 40 admitted corpus plus 12 helper/documentation/evidence files; all bytes equal | [complete inventory](../../../evaluation/WP-0009/unseal/publication-inventory.json) |
| Nine-event UTC commit chronology | All ordered; reservation precedes implementation, source acceptance precedes unseal, unseal precedes publication | [custody timeline](../../../evaluation/WP-0009/unseal/custody-timeline.json) |

All three publication helper modes passed on first execution. The initial staged default whitespace check emitted the same preserved-CRLF diagnostic before the corpus commit; the later committed-diff reproduction retains it completely. Original bytes were preserved, and the check's line-ending interpretation was made explicit. No copying, normalization or corpus correction was performed.

Checks not run: regeneration, new rendering, mapper/scorer evaluation, model inference, GPU/runtime or service tests. They are outside this exact-copy publication task. Earlier admission and source acceptance remain the independent evidence for their own scopes.

## Review map and handoff

Root should inspect the exact corpus deliverable `c0a702e43efee7bda20b4da0bc2b0cb3f0852e41`, evidence `c9b0726ea4d9c46fde894c0301aa58ff3ff56cd8`, inventory-only receipt `4449d113f7c4c9ade6bb8c7285e0a58bf22a0480`, full inventory and all 40 mapped original/public blobs. Original sealed receipt and inventory hashes above provide independent comparison anchors. Ground-truth acceptance is supplied by non-author /004; this report verifies publication only.

Normal owned push and exact-origin verification follow this report commit. The publication SHA, verified remote tip, final clean state, report-only final delta, complete inventory hash and corpus/evidence revisions are supplied in the handoff. This report cannot contain its own commit SHA; remote confirmation is pending only at construction. Root next verifies/integrates the publication and separately controls any finite runtime release.
