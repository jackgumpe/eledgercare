# /005 version 2: exact runtime lineages and supplemental scope

Preparation authority `44f1bb72ad41623f5f7955c61a71838aacee5115`; clean start /010 `b9dc09fa3dc6838c59f519063bb38d2c2a7f44f0`. Independent owner `eld-baseline-reviewer`, actual model/effort not exposed. This prepares CPU/dev-only verification. It grants no access to the active recovery run, heldout content or model/GPU resources.

`reproduce_v2.py` is a new version. Original `reproduce.py` / freeze `b725bedf62fca0f14dc6568dc6fabac524a0788d`, the first procedure, and original completed-dev proof `b87728b5b3c10d4a5633a11ed8c1e1988e32c231` are unchanged. The helper uses the original independent accounting routines and accepted pure prediction/reference/scoring functions. It does not call the author-head-bound runtime/score CLI.

| Supported original runtime lineage | Exact pins and scope |
| --- | --- |
| Original primary dev | Source `f807e0ac737df4e9e0aeeb96f716afec57f58ff6`, tree `df44162c62641596032df04bc834754da38a5f7b`, /003 `8c208273c2524b0253b046159178a9f5e6788049`, executing HEAD `e22c6730d19a6d616f0e7afb00b9416635799c16`. Only its original author/dev primary matrix is supported: two excluded warmups and 13 measurements. |
| Accepted corrected runtime | Source `522f15f1f6e399c36b9c6c107fc08f51862f1fc1`, tree `deae8e826f4770e880374c68e6a56c8c65b6f8a3`, /010 `b9dc09fa3dc6838c59f519063bb38d2c2a7f44f0`. Actual executing HEAD remains separately bound by each immutable release/plan/result and must have this source tree. Ordinary author split matrices contain 13 measurements; the exact failed-dev supplement contains one; fixed reviewer subsets contain one dev or two heldout measurements. Every schedule retains the two excluded warmups. |

The pure parser, scorer, typed conversion, corpus/reference, mapping and protocol Git objects must match both sources and the reviewer worktree. Q0/corpus trees and the pure `prediction` function must also match. The current reviewer worktree retains the new accepted runtime tree; this does not relabel the old run. Fixed sentinel selection remains `a8fb2137e559bfeb453bc184c78fab4989c99ecf`: SYN-WO-02-v3-hybrid-note, SYN-INV-03-v1-raster300 and SYN-MP-02-v0-clean.

After a **separate explicit coordinator assignment binds completed published evidence**, run from a clean owned worktree:

```powershell
python -I -B docs/reviews/WP-0007/eld-baseline-reviewer/005/reproduce_v2.py --verification-authority <exact-reviewer-authority> --original-authority <exact-authority-of-this-run> --release-path <bound-coordinator-release-path> --evidence-commit <exact-completed-publication> --run-prefix <bound-run-prefix> --scores-path <bound-scores-path> --split <dev-or-eval_holdout> --owner <author-or-reviewer> --output <new-owned-output>
```

`--permit-holdout` may be added only under later explicit heldout permission. The pre-read gate refuses heldout content without it; neither this flag nor any metadata test grants authority. All run artifacts are read from immutable Git blobs. Recorded external runtime paths are never opened. Verification authority/HEAD remain distinct from original runtime source/review/executing HEAD and release authority. The original runtime lease may have expired because independently authorized offline reproduction does not execute the runtime.

The complete score envelope must match: every per-document score/diagnostic, aggregate, result digest, and supplemental scope/lineage when applicable. The supplement is fixed to the one originally failed dev fixture and the exact original run-result digest/authority; it never replaces primary scores. Independent checks retain expected-item denominators, credited-detail sums, absence/extra/mapping counts and family/variant means. Full scheduled entries must be present, unique and ordered; missing planned entries are refused as malformed evidence. Failed/unexecuted calls with absent output remain scored with their expected denominators. An unavailable earlier observation may precede later completed records only with the new runtime's matching finalization diagnostic; it is not mistaken for a continued worker execution after a fatal call.

Completed observations must bind fixture/family/pages/kind/exclusion/settings, raw bytes and native text digest, token bytes and native token count/digest, stop reason, exact prompt/context, page-token positions and absence of failure/loss/truncation flags. Timing/memory are preserved archived observations. The helper's equality result is not a fresh performance or process-lifetime measurement. The independent review must separately inspect complete capture inventory, preflight/load/model/cache/input/exit/lease records and finalization status. No missing artifact is fabricated.

Preparation command, after helper freeze:

```powershell
python -I -B docs/reviews/WP-0007/eld-baseline-reviewer/005/prep_bindings_v2.py docs/reviews/WP-0007/eld-baseline-reviewer/005/binding-preparation/checks.json
```

The preparation reads only original immutable dev raw/scores at `1d6a681f09b0eaf233f838c54465c36a042ec326` and the two immutable release metadata records. Recovery metadata at `934d6a204bea0a61eb30c33a395b5c616dd00063:docs/coordination/WP-0007/releases/author-dev-recovery.json` is not new completed evidence. New-lineage result/plan inputs are explicitly CPU test doubles with zero completed recovery outputs. Heldout schedule counts use public metadata only; the content gate is tested by refusal. Canonical /005 remains held for actual completed author reproduction and separately released fixed sentinel runs. Next owner: coordinator for those exact completed bindings.
