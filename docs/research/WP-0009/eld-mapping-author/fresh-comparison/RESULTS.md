# WP-0009 fresh paired comparison: no observed mapping benefit

Author eld-mapping-author, same native Codex /root/mapping_author, requested xhigh; actual backend model/effort not separately exposed. This is author execution and verification, pending independent /008. No source changed after fresh exposure.

Accepted source **23e023045b335540d830ce01b75be247552a63f1**, tree **59f66d0d3d9be145a43efcc9258eb260d3ef2f00**, protocol SHA256 **f54214cc42307eb955f44f4c6470311f01ff7cf93887ea21d024feaa08a63e42**. Independent /006 **89a27d8b13b280632f4fc0e6704f8c3bdfe74355** accepted this source before unsealing. Published corpus **c0a702e43efee7bda20b4da0bc2b0cb3f0852e41** preserves the prior reservation. Exact clean execution/score-run HEAD **2a3781745cb120f6e3eb22b234c111241ba8d8c9**; runtime authority **6343ded1cd79b7c5b67b34893fe4516dc6845eb9**, `docs/coordination/WP-0009/releases/author.json`.

The single run `C:/Users/jackg/eLedgerCare-Mapping/WP-0009/author/runs/author/20261116T205320Z-67b42d6e` completed both historical excluded warmups and all four fresh primary documents. Wrapper started **2026-11-16T20:53:18.6090134Z** and finished **21:08:32.0627217Z**, actual tool session **65622 exit 0**. Supervisor PID32624, worker launcher10172, actual worker23516; PowerShell wrapper19996. Runtime elapsed **911.344s**, child exit0 observed, no failure, no secondary/finalization error. All34 pre/during/post observer commands returned0; the two post captures returned0/0. CPU score-run started21:08:46.9653429Z and completed21:08:49.1801475Z, exit0 at the same unchanged clean HEAD.

## Fresh result and complete denominators

**B0 and mapping v1 have identical complete predictions and scores on every fresh document. Printed and typed field gains0, losses0. The guarded right-neighbor association was accepted zero times.** The new rule therefore shows no benefit on this finite fresh set. The original27 exposed-data gains remain historical regression evidence only.

| Fresh document / family | Pages | Fields B0 = v1 | Cells B0 = v1 | Rows B0 = v1 | Reference token error rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| WP09-F01-v0 / WP09-F01 | 1 | 0/9 | 0/8 | 0/2 | 0.068627451 |
| WP09-F02-v0 / WP09-F02 | 1 | 0/6 | 0/28 | 0/4 | 0.030303030 |
| WP09-F03-v0 / WP09-F03 | 1 | 0/10 | 0/18 | 0/3 | 0.086330935 |
| WP09-F04-v0 / WP09-F04 | 3 | 0/14 | 0/36 | 0/6 | 0.027491409 |

All **4/4 documents completed**, **39 expected fields,90 expected cells and15 expected rows** remain in primary. Printed and typed exact field/cell rates and row rates are all zero, including equal-family means. All39 expected field candidates and all90 expected cell candidates are missing from the mapped representation. Raw text and native table rows are present: missing structured candidates are mapping coverage failures, not evidence that every character was unreadable. The unchanged vocabulary/header recognizer does not supply the expected candidates, so the one association rule never takes effect. No aliases, expected answers, headers or fixture-specific repair were added.

F02 contains one unchanged, schema-unmatched candidate `ticket_disposition = Return visit required`, taken from the printed `Disposition` text. The other documents contain no field candidates. All documents have zero recognized data tables and anchors. There are20,23,20,73 unclassified content records respectively, and3,5,4,9 physical unmapped table rows containing12,35,24,54 physical cells. These include headers and are distinct from the15 expected data-row/90 expected-cell denominators.

Expected absences score **0/4 verified**, with zero mapped violations or surplus candidates: all four are explicitly `verified_absent=false, unmapped=true`. This does not prove absence or freedom from invented content. Unmatched candidates and retained unclassified prose are schema-relative signals, not automatic factual-hallucination labels. Page counts match **4/4 documents / six pages**. The three-page document's semantic page sentinels0/3, adjacency0/2 and cross-page links0/1 remain uncredited; these depend on unmapped anchors and are not equivalent to physical page-count failure.

The equal-family mean reference token error rate is **0.053188206367482234** for both mappers. Individual alignment counts total664 reference tokens,669 prediction tokens,2 substitutions,12 deletions and17 insertions. This frozen metric uses SequenceMatcher with `autojunk=False`; it is not character accuracy, minimum-Levenshtein WER, or a general OCR-quality claim. No inference changed between the paired scores. Typed conversion is unchanged, has no credited candidates here, and retains its numeric-quantity/unit limitations.

## Runtime, resource observations and exclusions

| Call | Included in fresh score? | Synchronized wall seconds | Output tokens | Sampled peak private GiB | Sampled peak working-set GiB | Peak CUDA allocated GiB |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| SYN-WO-01-v0-clean | No, historical warmup | 176.939219 | 1122 | 10.0607 | 2.1672 | 6.7924 |
| SYN-MP-01-v0-clean | No, historical warmup | 345.276452 | 2558 | 10.2712 | 2.3452 | 6.8084 |
| WP09-F01-v0 | Yes | 56.515159 | 501 | 10.1104 | 2.2122 | 6.7924 |
| WP09-F02-v0 | Yes | 66.388945 | 590 | 10.1372 | 2.2252 | 6.7924 |
| WP09-F03-v0 | Yes | 68.243640 | 603 | 10.1371 | 2.2253 | 6.7924 |
| WP09-F04-v0 | Yes | 167.141574 | 1487 | 10.2973 | 2.3709 | 6.8084 |

All six calls stopped natively with `finish_reason=stop`, empty flags, expected page counts and lossless untruncated raw/token artifacts. Native generation/pre-first-token timings, render dimensions and hashes, host samples, CUDA allocated/reserved values and observer overhead are retained for every call. Peak CUDA reserved was6.9668GiB for each call. Host sampling provides window lower bounds; lifetime working-set peaks are separate. Device-wide memory includes desktop/WDDM activity and per-process VRAM remains unavailable. These are observations of one shared desktop host and one cold load, not a mapping latency comparison.

Cold load retained import2.034442500s, tokenizer0.455213900s, CPU from-pretrained7.510429500s and synchronized CUDA transfer4.113057400s. Preflight verified the existing Q0 environment/wheel identities, unmodified18-object model/notice and renderer; all eight imported cached source modules matched model bytes. No install/download/configuration occurred. The accepted no-Triton dense fallback remained unchanged. Stderr retains the Transformers cache deprecation and missing-Triton flop-counter warnings; neither was a failed completion.

Final recorded owned runtime bytes62,891,152 and free disk47,169,728,512 satisfy the4GiB cap/20GiB floor. Source/read-only Q0/model paths remain unchanged. The run remains externally retained. No other-owner process was terminated.

## Lease return, collection and checks

Author observed no remaining release-bound Python process at21:09:05.4110019Z. Root independently acknowledged lease **WP-0009-author-fresh-20261116T2052Z RETURNED** at21:11:07.073502Z, immutable receipt **70d45a144f44b74e562c1dbe8fdcea16662e970b:docs/coordination/WP-0009/author-after/lease-return.json**. Root reverified all18 model objects/notice, host status and bound process absence; idle Ollama remained unchanged. The acknowledgement is cleanup evidence, not independent score acceptance. No more author inference occurred.

After both execute and score-run finished, collection helper **95bc697362463f61dca4ed3b86147fa975bdd642** was committed under this dossier. It performs only CPU/Git/hash collection and bounded inventory verification. The accepted mapping tree is unchanged. Actual commands:

```text
python -I -B qualification/mapping_v1/cli.py execute --authority 6343ded1cd79b7c5b67b34893fe4516dc6845eb9 --release-path docs/coordination/WP-0009/releases/author.json --owner author
python -I -B qualification/mapping_v1/cli.py score-run --authority 6343ded1cd79b7c5b67b34893fe4516dc6845eb9 --release-path docs/coordination/WP-0009/releases/author.json --owner author --run C:/Users/jackg/eLedgerCare-Mapping/WP-0009/author/runs/author/20261116T205320Z-67b42d6e --output .scratch/wp0009-mapping/007-launch/scores.json
python -I -B docs/research/WP-0009/eld-mapping-author/fresh-comparison/collect_evidence.py collect --out docs/evidence/WP-0009/eld-mapping-author/007/attempt-1
```

All exited0. [Full paired scores](../../../../evidence/WP-0009/eld-mapping-author/007/attempt-1/scores.json), [structured analysis](../../../../evidence/WP-0009/eld-mapping-author/007/attempt-1/analysis.json), [collection inventory](../../../../evidence/WP-0009/eld-mapping-author/007/attempt-1/collection.json) and [run result](../../../../evidence/WP-0009/eld-mapping-author/007/attempt-1/run/run-result.json) are retained. `attempt-1/run/` preserves every copied run-relative name for independent reproduction. All call records/raw/token/render files, preflight/load/outcome/heartbeat/events, all34 observer captures, model/module metadata, stdout/stderr, launch/exit/score receipts, cleanup, exact runtime/review/unseal/lease proofs and root after-observations are published. No secret or downloaded weight is copied.

Collection verified **91 copied files /931,820 bytes** exactly and all20 fresh input artifacts against reservation/corpus identities. Separate cache inventory retains **28 files /62,653,533 bytes** externally:15 CUDA-cache files and13 HF-module cache files, with exact paths/bytes/hashes. Five empty cache directories are listed explicitly. The complete base-to-deliverable inventory follows the frozen helper's `verify` mode; it compares base blobs in one Git-tree pass and rechecks published/external bytes without rerunning inference or the CPU suite. Evidence `.gitattributes` disables text normalization so published raw/token/receipt bytes remain exact.

## Limits and next owner

No genuine run, score-run or collection check failed. No retry, replacement, subset selection or source change followed results. Prior CPU/reviewer failures remain immutable historical evidence. Fresh families and this output are now exposed and must not be portrayed as a new blind holdout in future tuning.

Independent **eld-mapping-reviewer /008** must reproduce full paired scores/denominators and inspect all evidence. Its one preselected WP09-F04-v0 sentinel requires a separate root release and observed lease; no independent runtime equality is claimed here. Four clean-digital families and one author run establish this finite neutral outcome only. No next mapping treatment, OCR change, new data or product integration is proposed or released by this report.
