# WP-0007 /002: Dev-only vanilla baseline scorer, protocol and finite runner

- Report path: `docs/agent-reports/eld-rd-astra/WP-0007/002_2026-11-16_implementation_eld-rd-astra.md`
- Reservation / kickoff: `c08d50e204395e60a88ce25f70e25bd29b97b8c6:INDEX.md` and `docs/kickoffs/WP-0007-eld-rd-astra.md`; root B0 design candidate `efa9cb986711f82a886f917e68142a7a59319bba`.
- Category: implementation
- Author / agent ID: eld-rd-astra, resumed native `/root/rd_astra`; earlier WP-0004/Q0 protocol and preflight authorship retained.
- Actual model / effort: inherited dispatched `gpt-6-astra` / `high`; backend checkpoint and backend session UUID not exposed. No additional agents or external model invocation.
- Execution environment: native Codex; Windows PowerShell 7.7.0, Git 2.55.0.windows.1, registered CPython 3.12.10 x64 with `-I -B`; stdlib CPU checks only.
- Timestamp: 2026-11-16T04:28:00Z
- Repository / branch: private `jackgumpe/eledgercare` / `research/wp-0007-vanilla-baseline`
- Owned worktree: `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-baseline-astra`
- Full dispatch base: `c08d50e204395e60a88ce25f70e25bd29b97b8c6`
- Deliverable candidate: `a998b765f7734453d27ec4a189a2156778f0913d`
- Post-check evidence: `a853ad80a3cb92412c3d4ac0962e6c8e8b252310`
- Previous report: none in WP-0007; WP-0005 /001 and /007 remain immutable.
- Related accepted work: Q0 /005 publication `848fe70bd6d6fce9c958f11b76102d2fdfad77d4`; corpus candidate `29b2000265ae6068d9c86818622c81a40cadd961`, unchanged at dispatch base.
- Status: ready-for-review; author implementation/verification, not independent acceptance.
- Next owner: eld-next-reviewer /003, then coordinator exact dev/test runtime releases. No GPU lease requested or held.

## Outcome and scope

Implemented a deterministic safe native parser, prediction-only label/table mapper, separate expected-value scorer/reference reader, public-metadata 26-document protocol, and finite coordinator-gated runner. Final CPU checks pass all 25 tests. Dev checks bind 13 dev references; only two retained historical Q0 outputs are rescored. A process file-open audit observed 18 synthetic paths, all allowed dev records/PDFs, zero unexpected/holdout paths. This is CPU preparation, not the new vanilla accuracy run or an independent acceptance.

No holdout PDF/source/expected content was accessed. Public manifest IDs/hashes/counts were used for planning. No package installation, runtime-root creation, model/tokenizer import, CUDA allocation, model inference, GPU observation/lease or product/Q0/corpus modification occurred. The CPU job-object test spawned and terminated only its owned sleeping Python child.

## Complete change inventory

All candidate paths below are additions. No existing source/data/report files changed.

| Exact path | Purpose / relevant boundary |
| --- | --- |
| `qualification/baseline/README.md` | Executable scoring/reference/alignment/coverage rules, resource/release contract and limitations |
| `qualification/baseline/native.py` | Bounded native markup/HTML grammar and raw-only prediction extraction; no expected access |
| `qualification/baseline/mapping.json` | Frozen dev labels/header structures and dev provenance; no expected field values used for extraction |
| `qualification/baseline/score.py` | Exact printed field/cell comparison, lexical token errors, omissions/excess/absence/page/link metrics, mapping coverage and family/split/variant summaries |
| `qualification/baseline/corpus.py` | Manifest/hash-bound reads and pre-read holdout gate; separate spatial text-reference construction |
| `qualification/baseline/prepare.py` | Dev-only mapping preparation and public-metadata protocol preparation |
| `qualification/baseline/protocol.json` | All 26 IDs/hashes/pages/splits, fixed order/warm-ups, Q0 identities/settings/guards and sentinel-selection policy |
| `qualification/baseline/release.py` | Exact coordinator Git release, clean executing HEAD, reviewed code tree/hash and test-access bindings |
| `qualification/baseline/runtime.py` | Finite supervised split/subset runner; read-only Q0 primitives/environment/model reuse, first-failure/no-retry accounting |
| `qualification/baseline/winjob.py` | Windows worker ownership before runtime imports; kill-on-supervisor-handle-close |
| `qualification/baseline/baseline.py` | CPU dev-check/plan, released execution/worker/scoring CLI |
| `qualification/baseline/tests/test_baseline.py` | 25 meaningful CPU mutation, mapping, access, release, guard and actual owned-child tests |
| `qualification/baseline/run_checks.py` | Frozen CPU evidence capture, actual file-open audit and output hash inventory |

Post-candidate evidence adds **54 paths**, solely under `docs/evidence/WP-0007/eld-rd-astra/`: `.gitattributes`, README, exact publication inventory, initial `8cd389e9/dev/` records, and the complete prior/final `4461eac2/` and `a998b765/` command stdout/stderr/audit scripts/check manifests/dev prediction/reference/score outputs. [publication-inventory.json](../../../evidence/WP-0007/eld-rd-astra/publication-inventory.json) lists every exact candidate/evidence path with size, SHA-256 and Git blob; it excludes itself and this later report to avoid self-reference. The 54th evidence path is that inventory itself. Local evidence attributes preserve raw subprocess bytes through Git.

Report metadata afterward is only this canonical /002 file. No INDEX/CURRENT, root designs, reviewer/product files, accepted Q0 core/evidence, original model/environment, admitted corpus or other worktree was modified. External persistent action is normal publication of this owned branch; all other effects were scoped CPU files and the owned short-lived test child.

## Scoring decisions and limits

Prediction extraction receives only raw output plus frozen dev label/header rules. Expected values/boxes, known fixture identifiers and source values never locate or repair predictions. Fields align by page/label occurrence; table segments require exact dev headers and align rows by encounter ordinal. Native page/block order is retained. Missing/spurious/duplicated candidates are not deduplicated; malformed/unsupported content remains diagnostic. Only NFC, line endings and outer whitespace are normalized for exact printed-field/cell matches. Leading zeros, signs, grouping, internal whitespace and case remain exact. `normalized_value` is retained in diagnostics, not used to claim unapproved semantic normalization.

The expected schema has no document-text transcript. The separately frozen reference includes every text operator in the hash-verified clean-parent PDF, including furniture, explanatory text and repeated headers, ordered page/y-descending/x-ascending. A hybrid adds both declared raster-only label/body at its source-bound target page/box. The parser supports this admitted writer's bounded PDF grammar, not arbitrary PDF; unsupported reference construction fails instead of silently omitting text. Prediction never reads this reference. Spatial row-major versus native column/block ordering can itself produce sequence errors; no unique human reading order or pure character-error interpretation is claimed.

Whitespace tokenization plus deterministic SequenceMatcher with autojunk=False yields substitution/deletion/insertion counts over reference-token denominator. This is not minimum-Levenshtein WER. Above 12,000 tokens, token alignment is explicitly unsupported with counts retained. Exact fields/cells remain separate. Per-document numerators/denominators precede equal document means within family and equal family means within split/variant. Dev/test remain separate; variants are correlated and this small synthetic set provides no population inference.

A failed or parse-invalid completion retains observed comparisons but receives no exact credit; all expected items/document denominators remain. Explicit mapped blanks alone verify expected absence. Unmatched fields/rows/cells are schema-relative excess signals; unclassified text is retained and cannot be comprehensively judged as invented semantics. Per-document `mapping_coverage` reports candidate/expected counts, unsupported/missing rows, reasons and unclassified content, separating mapper failures from raw lexical text errors.

## Retrospective dev diagnostics, not new B0 results

| Existing Q0 dev output | Exact fields | Exact cells | Mapping interpretation |
| --- | ---: | ---: | --- |
| F01 clean warm1 | 15/15 | 18/19 | All 19 expected cells have candidates; one strict printed-cell mismatch |
| F07 clean warm1 | 13/15 | 72/180 | Only 72/180 cells map; 12 expected rows remain unsupported/missing because later native headers differ from exact dev headers; 50 content records remain unclassified |

Both raw files come from accepted run `20261115T202627Z-eb5bf7da`; their source paths/digests are recorded in score files. F07's uncredited cells are **not asserted character-reading errors**. Its two field mismatches include conservative structural mapping limitations. These diagnostics exercise the scorer and remain separate from the later one-call/document baseline. Previous dev outputs are retained unchanged and rescored consistently after the final mapping-coverage addition.

## Runtime readiness and independent gates

The runner preserves original Q0 call settings/renderer, model/object/notice/module-cache verification, wheel/installed lock, native observer and timing/memory primitives without editing them. It uses separate task/run-local caches and 4-GiB root /20-GiB free floor. Session/load/call/stall/raw/log guards remain no weaker than Q0; Windows actual worker joins its supervisor's kill-on-close job before runtime imports. First failure stops later calls; missing planned completions remain explicit rather than being retried or removed.

Coordinator release must bind exact clean executing HEAD, accepted source commit/tree, unchanged Q0 primitive tree and protocol/lock/model-manifest hashes, mapping hash, actual independent /003 report, split/test access, root/owner, fresh observed sole lease/GPU/expiry, torchvision TOFU exception, and reviewer-chosen sentinels. Reviewer selects one-page, multipage and raster/skew/hybrid coverage before B0 measured results. Dev/test may have separate leases; any dev-driven scorer correction must be independently refrozen before test access. No acceptance reference is needed to create this CPU candidate.

Actual CUDA execution of the new finite runner remains untested and unreleased. CPU guard/job tests do not establish model/runtime success. One measured call/document with fixed excluded warm-ups gives descriptive latency/memory, not Q0 pooled repeats, paired-performance evidence or E1-E3 execution.

## Executed verification

| Check | Exact revision / actual result |
| --- | --- |
| Selected CPython `-I -B qualification/baseline/tests/test_baseline.py -v` | Initial 8cd389e9: 25 pass, tool-observed; final a998b765: 25 pass, captured stdout/stderr. Includes identifiers/money, omission/duplication/invention, unsafe/malformed markup, strict headers, failed denominators, no expected-value extraction dependence, holdout pre-read refusal, release/timeout/storage refusal and actual owned Windows job-child exit |
| `-I -B qualification/baseline/run_checks.py` | Frozen `a998b765f7734453d27ec4a189a2156778f0913d`, exit 0; all final subprocess checks pass, prior 4461eac2 result also retained |
| Dev check and independent audit-hook execution | 13 dev reference records, two historical Q0 outputs; 18 distinct synthetic paths opened (13 dev expected, four dev clean PDFs, one dev hybrid source), zero unexpected/holdout. Audit covers these executed scoring checks; preparation separately uses explicit dev filters |
| `git diff --check c08d50e... a998b765...` | Exit 0; 13 allowed candidate additions |
| Same base/candidate `git diff --exit-code -- evaluation qualification/q0 src INDEX.md CURRENT.md` | Exit 0; protected corpus/Q0/product/routing unchanged |
| Post-evidence Git-object audit | All 66 enumerated candidate/evidence entries match committed size/SHA-256/Git blob; both retained check manifests' artifact hashes match committed evidence bytes |

No substantive CPU test failed. An initial file search named nonexistent `docs/evidence/WP-0005`; source discovery was corrected to accepted `qualification/q0/harness/evidence/**`. Inspection output was narrowed after truncation. Git CRLF normalization notices for authored source were routine; evidence uses byte-preserving attributes. No denied runtime action was retried or bypassed.

Not run: new model inference, GPU/host observation, CPU PDFium rendering in the reused venv, full 26-document accuracy measurement, test source/expected/PDF inspection, or independent reviewer reproduction. Text reference reads are hash-bound stdlib parsing of admitted dev clean PDFs, not model-input rendering.

## Review map and handoff

Review [exact source diff](https://github.com/jackgumpe/eledgercare/compare/c08d50e204395e60a88ce25f70e25bd29b97b8c6...a998b765f7734453d27ec4a189a2156778f0913d), especially prediction/reference separation, conservative mapping coverage, full-text reference ordering/inclusion, failure denominators and runtime release/ownership boundaries. Final evidence is `docs/evidence/WP-0007/eld-rd-astra/a998b765/checks.json` at `a853ad80a3cb92412c3d4ac0962e6c8e8b252310`.

eld-next-reviewer /003 should inspect and reproduce the frozen CPU candidate and select sentinels before results. This author is ready for that review and subsequent exact runtime release, not self-acceptance. Source changes after test results remain prohibited in this packet absent defect disposition.

Publication is pending at report authoring. The separate handoff will supply the canonical report publication SHA and exact remote verification after a normal owned-branch push; this report contains no claim to its own publication SHA.
