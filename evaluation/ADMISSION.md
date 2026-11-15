# Synthetic starter corpus admission

Status: ADMITTED for the bounded WP-0004 research milestone on 2026-11-15 UTC. This is a coordinator decision based on independent review, not permission to run OCR/GPU experiments or use customer documents.

The admitted set contains 26 fictional PDFs /40 pages across eight families, eight original source JSONs, 26 expected JSONs and corpus-manifest.json. Their bytes are frozen at corpus/provenance candidate 29b2000265ae6068d9c86818622c81a40cadd961 and unchanged in final corrected candidate 54c7f6fe062720cbdf92e6bcd7476b697fc4afe1. Author manifests and README retain their historical candidate/pending labels; this separate record establishes current admission without changing independently reviewed data.

| Partition | Families | PDFs | Pages |
| --- | --- | ---: | ---: |
| dev | F01, F02, F04, F07 | 13 | 19 |
| eval_holdout | F03, F05, F06, F08 | 13 | 21 |

This is a fixed, non-blind development/test partition. The set is small, printed-font and synthetic, with no real scans or handwriting. Both public candidates remain unadmitted; no customer or non-fixture PDFs are admitted.

Independent Opus /005 reviewed all 40 pages through 82 views, independently bound source arithmetic to expected/visible values, and reproduced all 53 generated artifacts byte-for-byte in two runs. Its evidence/report are 1787e942412f7a6981c7a6d730c44a83034ad0ef / 8f9a3281fa223d25447677b8ed8b873bf9e5cd01. Independent /009 accepted the bounded corrections at evidence/report a79fb29f3d89fde938ebfe92d7455a441bd5f4a6 / da58038960eb5c4cc83be76e26d917ee378b2f07, with eight separate dev input/sign/no-op checks. These checks validate the corpus and written specification; they provide no OCR accuracy or throughput result.

The [three-card experiment backlog](../research/carbon/reconciliation/02-ranked-experiment-backlog.md) is accepted as falsifiable proposals. Q0 runtime qualification and E1–E3 model experiments remain unperformed and require separate authorization. Model weights, GPU execution, training, production integration and deployment are not released.

Integration commit: 13e3c47afb35e39d9e76054431ee9f23a12c4bb9. [Coordinator disposition and verification](../docs/coordination/WP-0004-final/README.md) records full pins, source/report corrections, exact Git-object preservation and the complete change inventory. Published historical reports remain immutable.
