# WP-0009 final R&D disposition

**ACCEPTED: the bounded mapping experiment and independent evaluation are complete. No fresh structured-coverage benefit was demonstrated.** One guarded field-association change improves historical regression examples, while both frozen mappers score zero expected fields and table cells on the four reserved fresh families. This is a reproducible downstream mapping result, not a claim that OCR extracted no useful text.

## Exact accepted work

Authorized base: `5e1241d6d365d664f12619d415f48ec3d3b7ddca`. Accepted source: `23e023045b335540d830ce01b75be247552a63f1`; `qualification/mapping_v1` tree `59f66d0d3d9be145a43efcc9258eb260d3ef2f00`; protocol SHA256 `f54214cc42307eb955f44f4c6470311f01ff7cf93887ea21d024feaa08a63e42`.

The sole quality treatment associates a known field label with its immediate right neighbor only when page uniqueness, simple table structure, label-like text and orientation guards pass. B0 vocabulary, parsing, scoring and typed conversion remain unchanged. Failed guards preserve B0 fallback. No new aliases, recognized table headers, normalization/scorer repair, model treatment or production import was added.

Independent diagnosis /002 accepted the selected opportunity. Independent source [review /006](../../../agent-reports/eld-mapping-reviewer/WP-0009/006_2026-11-16_review_eld-mapping-reviewer.md), publication `89a27d8b13b280632f4fc0e6704f8c3bdfe74355`, accepted the corrected source after 31 CPU checks. The independent final [review /008](../../../agent-reports/eld-mapping-reviewer/WP-0009/008_2026-11-16_review_eld-mapping-reviewer.md), publication `187ca27ad2c6deb4a23b5fbecd47434ca286a829`, accepts exact author [fresh /007](../../../agent-reports/eld-mapping-author/WP-0009/007_2026-11-16_implementation_eld-mapping-author.md), publication `73b5c5d3ce123adc33ba0397dcc74029208606c5`. Both were normally integrated through `32a129a2101d365243b43214217f00acbbf9c6dd`.

## Quality result

| Evaluation | B0 printed-field equal-family mean | Mapping v1 mean | Exact correct/expected field counts |
| --- | ---: | ---: | --- |
| Historical development | 73.4983% | 77.3872% | 146/196 to 154/196 |
| Exposed historical holdout, now regression data | 26.2963% | 36.7393% | 47/165 to 66/165 |
| Four reserved fresh families | 0% | 0% | 0/39 for both |

The historical gain is **27 unique fields, zero losses**. Printed and typed gains refer to the same 27 fields, not 54 independent improvements. All 26 primary records remain: 25 original completions and the original failed record; separate recovery stays parse-ineligible. Non-field prediction and score objects remain exact. These results do not improve or redefine the original immutable B0 baseline.

All four fresh documents completed. Both mappers produce identical complete predictions and scores: **0/39 expected fields, 0/90 table cells, 0/15 rows, zero gains/losses**. The new right-neighbor rule has zero accepted associations on these layouts. Physical page counts match all four documents/six pages; semantic page anchors and cross-page links remain unmapped. Four expected-absence slots are unverified. One schema-unmatched field comes from printed text; unmatched/absent signals are not proof about factual invention. Raw text and physical tables are retained, but the frozen label/header vocabulary does not provide expected structured coverage here. Recognition omissions, parsing and typed-unit limitations are not explained away by that coverage bottleneck.

The unchanged SequenceMatcher reference-token error mean is 0.053188206367482234 across the four families. It is neither character error rate nor minimum-edit-distance WER. Four clean digital families provide a limited observation, not a population guarantee or an estimate of performance on raster documents. Fresh material is now exposed regression evidence for any future work; another generalization check would require separately reserved material.

## Protected fresh evaluation and actual reproduction

Public reservation `7513a9a86e6af55a6d8ca7f5a8dc0f80f054ba0b` predates implementation. Independent admission /004 at `3e5d305d0cdcb2666ba56912ba6c06dc19d74c8b` accepted the sealed corpus `559c5d09490b7729be26fb9bf9d872305cae3303`. Root unseal `5685660e0188db1d9832baded7eb8e95085109c7` followed accepted source /006. Exact corpus `c0a702e43efee7bda20b4da0bc2b0cb3f0852e41` and custodian [publication /010](../../../agent-reports/eld-eval-custodian/WP-0009/010_2026-11-16_verification_eld-eval-custodian.md) at `c723df666f9148747ff2d713867590789959b4a9` preserve all 40 admitted files/1,075,820 bytes. All 32 independent admission artifacts were published at `68a2f9458851b8bf60b067b702261f63ff70b900`. Custody was procedural, not OS-enforced. There was no regeneration, tuning or replacement after unsealing.

| Actual finite run | Exact clean executing HEAD | Outcome |
| --- | --- | --- |
| Author `20261116T205320Z-67b42d6e`, authority `6343ded1cd79b7c5b67b34893fe4516dc6845eb9` | `2a3781745cb120f6e3eb22b234c111241ba8d8c9` | Two excluded warmups and all four primary calls completed; 911.344s; actual supervisor/tool and worker exit 0; all 34 observers exit 0; score-run exit 0 |
| Reviewer `20261116T211537Z-074ec88b`, authority `e339bd4c8322a14fbff98d9299acede4b92c911f` | `69f7a79677b43228869d7c35bb5fb6d3e12e9291` | Two excluded warmups and only fixed three-page WP09-F04-v0 completed; 624.703s; actual supervisor/tool and worker exit 0; all 24 observers exit 0; score-run exit 0 |

The sentinel was selected before fresh outputs. It matches the author's **raw bytes, token IDs, both full score objects and rendered raster tuples**. The independent reviewer also reconstructed all four author predictions/scores/family summaries directly from immutable raw evidence. Author denominator four and reviewer inference denominator one remain separate. No runtime or scoring retry occurred. The reviewer sentinel overlapped author packaging only after independently acknowledged author lease return; the fixed source/input/schedule were unchanged, and final acceptance required immutable author evidence.

Both runs reuse the unchanged Baidu checkpoint `0480966938291445591f69f08a13b041c073a96a`, qualified dependencies, native prompt/kwargs, 300dpi rendering and Q0 primitives. Independent checks reconcile all 18 model objects, notice, eight loaded cache-copy hashes, wheel identities and renderer versions. The existing torchvision local-SHA TOFU exception remains explicit. Offline library settings do not establish enforced outbound network denial.

Author fresh model-call times were 56.515159s, 66.388945s, 68.243640s and 167.141574s. The repeated reviewer sentinel took 166.991944s. Reviewer sentinel sampled peak private memory was 10.297222GiB, working set 2.369072GiB, CUDA max allocated 6.808421GiB and reserved 6.966797GiB. These are descriptive retained observations; sampled host peaks are lower bounds. The same raw extraction feeds both mappers, so no model latency/memory improvement follows from this mapping change. Desktop sharing, WDDM unavailable per-process VRAM and parallel product CPU/browser activity remain confounders; sole model-job leases are not hardware exclusivity.

## Preservation and returned resources

Root verified the author publication's 100 additions, 91 exact original-to-published files and 2,272 unchanged input paths, then the reviewer publication's 120 additions, 57 exact complete copies and 2,292 unchanged input paths. Exact remote branches and report-only publication deltas were verified. The original corpus, Q0/B0 source and evidence, prior reports and failed outcomes are unchanged. The final coordinator report binds the complete integrated preservation inventory separately.

Both leases are **RETURNED and independently acknowledged**: [author return](../author-after/lease-return.json) at `70d45a144f44b74e562c1dbe8fdcea16662e970b`, [reviewer return](../reviewer-after/lease-return.json) at `2314a32ca219116de11f2d4120afaf2133a87fec`. Root reverified model/notice bytes, successful post observers, host/storage conditions and bound process absence. No further inference is authorized. Original external runs and their inventoried task-local caches remain retained; unrelated processes and the read-only Q0 environment were not changed.

Failures remain visible: original B0 failure/recovery and unknown historical supervisor exit; initial source-review sentinel-policy defect and reviewer AST-helper defect; author policy/test correction /011; byte-preserving publication whitespace diagnostics; reviewer collection failure from an absent empty-output log, with 48 partial copies preserved and a separately frozen successful collector. The missing log was recorded absent, not synthesized. Root's initial inventory-schema lookup failure is also disclosed in its audit. None was replaced by a successful rerun of inference.

## Scope and handoff

WP-0009 is complete through the accepted bounded neutral evaluation. No promotion of the research mapper into product, additional aliases/treatments, training, new model runs, raster expansion or customer-data work is released. The main unresolved product-level issue is structured coverage across unseen label/header vocabularies. F3 review/correction remains a separate product lane with its own independent acceptance and provenance. Its status is tracked in CURRENT.md and does not change this R&D disposition.
